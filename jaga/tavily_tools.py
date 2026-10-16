"""Tavily tools: domain-restricted search, extract, and a nightly map→extract
cache of the official alert lists.

Design rule (from Tavily's own guidance for this hackathon): the model decides
when to search; nothing is hard-coded. These functions are deterministic and
testable without a model. A "clean nothing-found" is a valid result and is
returned as such — never fabricated.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import time
from typing import Any

import httpx

from . import config

log = logging.getLogger("jaga.tavily")


class Tavily:
    def __init__(self, mock: bool | None = None, db_path=None) -> None:
        self.mock = (config.MOCK or not config.TAVILY_API_KEY) if mock is None else mock
        self.db_path = str(db_path or config.DB_PATH)
        # The search cache can be shared across eval runs (JAGA_SEARCH_CACHE) to save credits.
        import os
        self.cache_db = os.environ.get("JAGA_SEARCH_CACHE") or self.db_path
        self._init_cache()
        self.calls: list[dict[str, Any]] = []

    # --------------------------------------------------------------- cache db
    def _init_cache(self) -> None:
        with sqlite3.connect(self.db_path, timeout=30) as con:
            con.execute("""CREATE TABLE IF NOT EXISTS alert_cache (
                url TEXT PRIMARY KEY, title TEXT, content TEXT, fetched_at REAL)""")
            con.execute("""CREATE TABLE IF NOT EXISTS search_cache (
                key TEXT PRIMARY KEY, response TEXT, fetched_at REAL)""")

    def cache_lookup(self, term: str) -> list[dict[str, Any]]:
        term_l = term.lower().strip()
        if len(term_l) < 4:
            return []
        with sqlite3.connect(self.db_path, timeout=30) as con:
            rows = con.execute("SELECT url, title, content, fetched_at FROM alert_cache").fetchall()
        out = []
        for url, title, content, ts in rows:
            if term_l in (content or "").lower():
                i = content.lower().find(term_l)
                out.append({"url": url, "title": title, "snippet": content[max(0, i - 120): i + 160],
                            "fetched_at": ts, "kind": "official_alert"})
        return out

    def refresh_alert_cache(self, urls: list[str] | None = None) -> int:
        """Nightly cron: Map each alert-list root, then Extract the pages into
        the local cache. Common lookups become instant and free."""
        urls = urls or config.ALERT_LIST_URLS
        n = 0
        for root in urls:
            pages = [root] + self.map(root, max_depth=1)[:20]
            for page in self.extract(pages):
                with sqlite3.connect(self.db_path, timeout=30) as con:
                    con.execute("INSERT OR REPLACE INTO alert_cache VALUES (?,?,?,?)",
                                (page["url"], page.get("title", ""), page.get("raw_content", ""), time.time()))
                n += 1
        return n

    # ------------------------------------------------------------- endpoints
    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST to Tavily with a 24h response cache: identical lookups (the same scheme name
        checked twice in a day) cost zero credits and return instantly."""
        key = path + json.dumps(payload, sort_keys=True)
        with sqlite3.connect(self.cache_db, timeout=30) as con:
            row = con.execute("SELECT response, fetched_at FROM search_cache WHERE key=?", (key,)).fetchone()
        if row and time.time() - row[1] < 86400:
            self.calls.append({"endpoint": path, "ms": 0, "cached": True, "query": payload.get("query") or payload.get("url")})
            return json.loads(row[0])
        data = self._post_live(path, payload)
        with sqlite3.connect(self.cache_db, timeout=30) as con:
            con.execute("INSERT OR REPLACE INTO search_cache VALUES (?,?,?)", (key, json.dumps(data), time.time()))
        return data

    def _post_live(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        t0 = time.time()
        r = httpx.post(f"{config.TAVILY_BASE_URL}{path}", json=payload,
                       headers={"Authorization": f"Bearer {config.TAVILY_API_KEY}"}, timeout=30)
        r.raise_for_status()
        self.calls.append({"endpoint": path, "ms": int((time.time() - t0) * 1000), "query": payload.get("query") or payload.get("url")})
        return r.json()

    def search_official(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """Search restricted to official Malaysian alert domains."""
        if self.mock:
            return _mock_search(query, official=True)
        data = self._post("/search", {
            "query": query, "search_depth": "advanced", "max_results": max_results,
            "include_domains": config.OFFICIAL_DOMAINS, "include_raw_content": "markdown",
        })
        return [{"url": r["url"], "title": r.get("title", ""), "snippet": r.get("content", ""),
                 "raw": (r.get("raw_content") or "")[:40000], "score": r.get("score", 0), "kind": "official_alert"}
                for r in data.get("results", [])]

    def search_news(self, query: str, days: int = 90, max_results: int = 5) -> list[dict[str, Any]]:
        """Recent news reports (scam scripts, new schemes)."""
        if self.mock:
            return _mock_search(query, official=False)
        data = self._post("/search", {
            "query": query, "topic": "news", "days": days, "max_results": max_results,
            "include_domains": config.NEWS_DOMAINS, "search_depth": "basic",
        })
        return [{"url": r["url"], "title": r.get("title", ""), "snippet": r.get("content", ""),
                 "published": r.get("published_date"), "score": r.get("score", 0), "kind": "news"}
                for r in data.get("results", [])]

    def extract(self, urls: list[str]) -> list[dict[str, Any]]:
        """Pull the full page so the planner reads the actual alert, not a snippet."""
        if not urls:
            return []
        if self.mock:
            return [{"url": u, "title": "Alert list (mock)", "raw_content": f"Mock content for {u}"} for u in urls]
        out: list[dict[str, Any]] = []
        for i in range(0, len(urls), 5):  # Tavily bills extract per 5 URLs
            data = self._post("/extract", {"urls": urls[i:i + 5], "format": "markdown"})
            out.extend({"url": r["url"], "raw_content": r.get("raw_content", ""), "title": r.get("title", "")}
                       for r in data.get("results", []))
        return out

    def map(self, url: str, max_depth: int = 1) -> list[str]:
        if self.mock:
            return []
        data = self._post("/map", {"url": url, "max_depth": max_depth, "limit": 50})
        return list(data.get("results", []))

    def run_check(self, tool: str, query: str, entity: str) -> dict[str, Any]:
        """Execute one planner check and summarise it as evidence-or-nothing.
        For official lookups the model's query is paired with one canonical query per entity,
        so verification never depends on the wording the planner happened to choose."""
        if tool == "alert_cache":
            results = self.cache_lookup(entity)
        elif tool == "tavily_search_official":
            results = self.cache_lookup(entity)
            if not _relevant_hit(results, entity):
                results += self.search_official(query)
                if not _relevant_hit(results, entity):
                    canonical = f'"{entity}" investor alert list' if not any(ch.isdigit() for ch in entity) else f'"{entity}" semak mule scam'
                    if canonical.lower() != query.lower():
                        results += self.search_official(canonical)
        elif tool == "tavily_search_news":
            results = self.search_news(query)
        else:
            results = []
        hit = _relevant_hit(results, entity)
        return {"tool": tool, "query": query, "entity": entity,
                "results": [{k: v for k, v in r.items() if k != "raw"} for r in results[:5]],
                "hit": bool(hit), "url": hit["url"] if hit else "", "kind": hit["kind"] if hit else "none_found",
                "quote": hit.get("_quote", "") if hit else "",
                "claim": f"'{entity}' appears in {hit['title'] or hit['url']}" if hit else f"No alert found for '{entity}'"}


def _relevant_hit(results: list[dict[str, Any]], entity: str) -> dict[str, Any] | None:
    """A result only counts if the entity itself appears in it (title, snippet or full page).
    This is the guard against the model treating any search result as proof. The matching
    sentence is kept as the quote shown to the family."""
    key = re.sub(r"[\s\-+\"']", "", entity.lower())
    if len(key) < 3:
        return None
    for r in results:
        text = (r.get("title", "") + " \n " + r.get("snippet", "") + " \n " + r.get("raw", ""))
        flat = re.sub(r"[\s\-+\"']", "", text.lower())
        if key in flat:
            m = re.search(re.escape(entity.strip().strip('"')), text, re.I)
            if m:
                quote = text[max(0, m.start() - 120): m.end() + 80]
            else:
                quote = r.get("snippet", "")[:200]
            r["_quote"] = re.sub(r"\s+", " ", quote).strip()[:240]
            return r
    return None


# ----------------------------------------------------------------- mock Tavily
_MOCK_ALERTS = {
    # Fictional entities that the mock "official lists" know about.
    "gold": "SC Investor Alert List: unlicensed entity offering gold investment",
    "invest": "SC Investor Alert List: unlicensed investment scheme",
    "capital": "SC Investor Alert List: unlicensed entity",
    "fx": "SC Investor Alert List: unlicensed forex platform",
    "crypto": "SC Investor Alert List: unlicensed digital asset platform",
    "011-9999": "PDRM Semak Mule: phone number reported for scam calls",
    "0119999": "PDRM Semak Mule: phone number reported for scam calls",
    "011-0000": "PDRM Semak Mule: phone number reported",
    "0110000": "PDRM Semak Mule: phone number reported",
    ".xyz": "MCMC: phishing domain reported",
    ".top": "MCMC: phishing domain reported",
    "-secure-": "BNM Financial Consumer Alert: fake bank portal",
}


def _mock_search(query: str, official: bool) -> list[dict[str, Any]]:
    q = re.sub(r"[\s\-+]", "", query.lower())
    out = []
    for key, title in _MOCK_ALERTS.items():
        k = re.sub(r"[\s\-+]", "", key.lower())
        if k in q and (official or True):
            ent = query.split(" scam")[0].split(" semak")[0].split(" phishing")[0]
            out.append({"url": f"https://www.sc.com.my/investor-alert-list#{k}" if "SC" in title else
                        f"https://semakmule.rmp.gov.my/?q={k}" if "PDRM" in title else f"https://www.mcmc.gov.my/alerts#{k}",
                        "title": title, "snippet": f"{title}. Entity: {ent}", "raw": "", "score": 0.9,
                        "kind": "official_alert" if official else "news"})
    return out
