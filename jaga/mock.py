"""Deterministic stand-ins for Nemotron (and, in tavily_tools, for Tavily).

These are intentionally simple keyword heuristics. They exist so that:
  * tests and the dashboard run with no API keys;
  * the eval harness has a transparent baseline ("rules only") to compare
    Nemotron against — the gap between this file and the real models is
    itself a reported number;
  * the demo has a recorded-run fallback if credits are exhausted.
"""
from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel

from .schemas import (EscalationOpinion, Entities, Evidence, Triage, VerificationPlan,
                      Check, Verdict)

PHONE_RE = re.compile(r"(?:\+?6?0?1[0-9][\s-]?\d{3,4}[\s-]?\d{4})")
URL_RE = re.compile(r"(?:https?://|www\.)[^\s]+|\b[a-z0-9-]+\.(?:xyz|top|club|site|online|info|icu|buzz|cc|me|link|shop)\b", re.I)
AMOUNT_RE = re.compile(r"RM\s?\d[\d,]*(?:\.\d+)?|\d[\d,]*\s?(?:ringgit)", re.I)
ACCT_RE = re.compile(r"\b\d{10,16}\b")

FAMILY_CUES: dict[str, list[str]] = {
    "impersonation": ["polis", "police", "pdrm", "mahkamah", "court", "lhdn", "bank negara", "bnm",
                      "waran", "warrant", "kes", "pegawai", "officer", "pengubahan wang", "money laundering",
                      "macau", "saman", "tangkap", "arrest", "jabatan", "kastam"],
    "investment": ["pelaburan", "invest", "return", "pulangan", "keuntungan", "profit", "jamin", "guaranteed",
                   "forex", "crypto", "bitcoin", "emas", "gold", "saham", "sc licensed", "modal", "roi", "dividen"],
    "love": ["sayang", "darling", "honey", "lonely", "cinta", "hadiah", "gift", "parcel for you", "my love",
             "sugar", "kekasih", "rindu", "dear"],
    "mule": ["sewa akaun", "rent your account", "akaun bank anda", "sewa sim", "pinjam akaun", "komisen",
             "commission", "guna akaun", "bank account rental", "buat duit mudah", "easy money"],
    "parcel": ["parcel", "bungkusan", "kastam", "customs", "pos laju", "poslaju", "j&t", "dhl", "fedex",
               "ditahan", "held", "yuran", "fee", "tracking", "penghantaran"],
    "phishing_otp": ["tac", "otp", "verify", "sahkan", "kemaskini", "update your", "akaun anda akan",
                     "suspended", "disekat", "blocked", "login", "log masuk", "klik", "click", "password",
                     "kata laluan", "pin"],
}
URGENCY = ["segera", "immediately", "now", "sekarang", "within 24", "dalam 24 jam", "last chance",
           "peluang terakhir", "hari ini", "today", "jangan beritahu", "do not tell", "rahsia", "confidential",
           "urgent", "cepat", "terhad", "limited"]
ASKS = {"TAC": ["tac", "otp", "kod"], "transfer": ["transfer", "pindah", "bayar", "pay", "deposit", "masukkan"],
        "click link": ["klik", "click", "http", "www.", "link", "pautan"],
        "personal data": ["ic", "kad pengenalan", "nombor akaun", "account number", "password", "kata laluan"]}

LEGIT_HINTS = ["jangan kongsi", "never share", "do not share", "tidak akan meminta", "will never ask",
               "rujukan", "appointment", "temujanji", "mesyuarat", "meeting", "sekolah", "school",
               "terima kasih", "thank you", "resit", "receipt", "makan", "dinner", "lunch"]


def _lang(text: str) -> str:
    ms = sum(w in text.lower() for w in ["anda", "akaun", "sila", "segera", "terima kasih", "untuk", "dengan", "ini", "yang", "saya"])
    en = sum(w in text.lower() for w in ["your", "please", "account", "the ", "you", "this", "with", "for "])
    if ms and en:
        return "manglish"
    if ms:
        return "ms"
    if "lah" in text.lower() or "lor" in text.lower():
        return "manglish"
    return "en"


def triage(text: str) -> Triage:
    t = text.lower()
    scores = {fam: sum(1 for cue in cues if cue in t) for fam, cues in FAMILY_CUES.items()}
    fam, best = max(scores.items(), key=lambda kv: kv[1])
    asks = [k for k, cues in ASKS.items() if any(c in t for c in cues)] or ["nothing"]
    urgency = [u for u in URGENCY if u in t]
    legit_hint = sum(1 for h in LEGIT_HINTS if h in t)
    risky = best + len(urgency) + (len(asks) if asks != ["nothing"] else 0)
    if best == 0 or (legit_hint >= 1 and risky <= 2) or (asks == ["nothing"] and not urgency and best <= 1):
        fam, conf = "legit", 0.6 + 0.1 * min(legit_hint, 3)
    else:
        conf = min(0.5 + 0.1 * risky, 0.95)
    ents = Entities(
        phones=PHONE_RE.findall(text),
        urls=URL_RE.findall(text),
        orgs=[o for o in ["Maybank", "CIMB", "Bank Negara", "PDRM", "LHDN", "Pos Laju", "J&T", "Shopee", "SC",
                          "Public Bank", "TNB", "EPF", "KWSP", "JPJ"] if o.lower() in t],
        bank_accounts=ACCT_RE.findall(text),
        amounts=AMOUNT_RE.findall(text),
    )
    return Triage(family=fam, confidence=round(conf, 2), language=_lang(text), urgency_cues=urgency[:4],
                  asks_for=asks, entities=ents, one_line=f"Message that looks like: {fam}")


def plan(triage_: Triage, ctx: dict[str, Any]) -> VerificationPlan:
    ledger = ctx.get("ledger", {})
    trusted = ledger.get("trusted_matches", [])
    if trusted and triage_.family in ("legit", "investment") and triage_.confidence < 0.8:
        return VerificationPlan(needs_live_check=False, checks=[], ledger_answers_it=True,
                                rationale=f"Sender matches trusted household contact {trusted[0]}.")
    checks: list[Check] = []
    for org in triage_.entities.orgs[:2]:
        checks.append(Check(entity=org, tool="tavily_search_official", query=f"{org} scam alert",
                            reason="Named institution — check official alert lists"))
    for ph in triage_.entities.phones[:2]:
        checks.append(Check(entity=ph, tool="tavily_search_official", query=f"{ph} semak mule",
                            reason="Phone number — check PDRM Semak Mule"))
    for url in triage_.entities.urls[:1]:
        checks.append(Check(entity=url, tool="tavily_search_news", query=f"{url} phishing scam",
                            reason="Link — look for recent reports"))
    if not checks and triage_.family != "legit":
        checks.append(Check(entity=triage_.family, tool="tavily_search_news",
                            query=f"{triage_.family} scam Malaysia 2026", reason="Pattern check against recent reports"))
    return VerificationPlan(needs_live_check=bool(checks), checks=checks[:6], ledger_answers_it=False,
                            rationale="Entities present; verify against official sources before warning.")


def verdict(triage_: Triage, ctx: dict[str, Any]) -> Verdict:
    results = ctx.get("tool_results", [])
    ledger = ctx.get("ledger", {})
    hits = [r for r in results if r.get("hit")]
    evidence: list[Evidence] = []
    for h in hits[:3]:
        evidence.append(Evidence(claim=h["claim"], source_url=h["url"], quote=h.get("quote", ""), kind=h.get("kind", "official_alert")))
    if ledger.get("trusted_matches"):
        evidence.append(Evidence(claim=f"Sender matches trusted contact {ledger['trusted_matches'][0]}",
                                 source_url="", quote="", kind="ledger"))
    novelty = ledger.get("novelty_flags", [])
    fam = triage_.family
    if fam == "legit" and not hits:
        risk = "low"
    elif hits:
        risk = "high"
    elif triage_.confidence >= 0.8 or ("TAC" in triage_.asks_for) or (fam in ("impersonation", "mule")):
        risk = "high"
    elif fam != "legit":
        risk = "medium"
    else:
        risk = "unknown"
    if ledger.get("trusted_matches") and not hits and fam in ("legit", "investment"):
        risk = "low"
    if not evidence:
        evidence.append(Evidence(claim="No official alert found for the named entities", source_url="", quote="", kind="none_found"))
    big = any(a for a in triage_.entities.amounts)
    escalate = risk in ("medium", "unknown") and big
    actions = {
        "high": "Jangan hantar wang atau kongsi TAC. Hubungi NSRC 997. / Do not transfer or share any code. Call NSRC 997.",
        "medium": "Berhenti dan sahkan dengan keluarga dahulu. / Pause and verify with family first.",
        "low": "Tiada amaran rasmi ditemui. Teruskan dengan berhati-hati. / No official alert found. Proceed with normal care.",
        "unknown": "Maklumat tidak mencukupi — tanya keluarga sebelum bertindak. / Not enough information — ask family before acting.",
    }
    return Verdict(
        risk=risk, family=fam,
        headline_ms={"high": "Amaran: ini kelihatan seperti penipuan.", "medium": "Berhati-hati: ada tanda-tanda penipuan.",
                     "low": "Tiada amaran rasmi ditemui untuk mesej ini.", "unknown": "Jaga tidak pasti — sila semak dengan keluarga."}[risk],
        headline_en={"high": "Warning: this looks like a scam.", "medium": "Caution: this has scam signals.",
                     "low": "No official alert found for this message.", "unknown": "Jaga is unsure — please check with family."}[risk],
        explanation=f"Triage classed this as '{fam}' (confidence {triage_.confidence}). "
                    f"{len(hits)} official/news hit(s) found. " + ("; ".join(novelty) if novelty else ""),
        evidence=evidence, recommended_action=actions[risk],
        notify_family=risk in ("high", "medium"), escalate=escalate, novelty_flags=novelty,
    )


def escalation(ctx: dict[str, Any]) -> EscalationOpinion:
    v = ctx.get("verdict")
    return EscalationOpinion(agree_with_verdict=True, risk=v.risk if v else "unknown",
                             reasoning_summary="Second opinion (mock): evidence consistent with the first verdict.",
                             additional_action="Confirm the payee by calling a known number, not the one in the message.")


def answer(role: str, schema: type[BaseModel], user: str, ctx: dict[str, Any]) -> BaseModel:
    name = schema.__name__
    if name == "Triage":
        return triage(ctx.get("text", user))
    if name == "VerificationPlan":
        return plan(ctx["triage"], ctx)
    if name == "Verdict":
        return verdict(ctx["triage"], ctx)
    if name == "EscalationOpinion":
        return escalation(ctx)
    raise ValueError(f"mock has no answer for schema {name}")
