"""The Jaga case loop.

  text ──► Lightning triage (thinking off, JSON)
       ──► ledger context (structured memory)
       ──► Super plan (thinking on, budgeted)       [skipped in tier='fast']
       ──► execute checks via Tavily / cache        [skipped if use_tavily=False]
       ──► Super verdict with cited evidence
       ──► Ultra second opinion if verdict.escalate  [tier='full' only]
       ──► ledger.record_case (deterministic memory write + audit)
       ──► notify guardians (summary only)

Every switch is a RunOptions field so the eval harness can ablate it.
"""
from __future__ import annotations

import json
import logging
import time
import uuid

from . import config, notify
from .config import RunOptions
from .ledger import Ledger
from .llm import TokenFactory, Usage
from .prompts import (ESCALATE_SYSTEM, ESCALATE_USER, PLAN_SYSTEM, PLAN_USER, TRIAGE_SYSTEM,
                      TRIAGE_USER, VERDICT_SYSTEM, VERDICT_USER)
from .schemas import CaseResult, EscalationOpinion, Triage, Verdict, VerificationPlan
from .tavily_tools import Tavily

log = logging.getLogger("jaga.pipeline")


def _backstop_entities(triage: Triage, text: str) -> None:
    """Deterministic floor under the model: phone numbers, links and account numbers found by
    regex are always added, so a missed extraction can never silently skip verification."""
    from .mock import ACCT_RE, PHONE_RE, URL_RE
    e = triage.entities
    for found, bucket in ((PHONE_RE.findall(text), e.phones), (URL_RE.findall(text), e.urls)):
        norm = {x.replace(" ", "").replace("-", "") for x in bucket}
        for f in found:
            if f.replace(" ", "").replace("-", "") not in norm and len(bucket) < 5:
                bucket.append(f.strip())
    for a in ACCT_RE.findall(text):
        if a not in e.bank_accounts and a.replace(" ", "") not in "".join(e.phones).replace(" ", "").replace("-", "") and len(e.bank_accounts) < 4:
            e.bank_accounts.append(a)


def _plan_floor(plan: VerificationPlan, triage: Triage) -> None:
    """If the message looks like a scam and names something checkable, at least one official
    lookup per named org / phone / link happens — even if the planner chose none."""
    from .schemas import Check
    if triage.family == "legit" or plan.ledger_answers_it:
        return
    have = {c.entity.lower() for c in plan.checks}
    adds = [(o, "tavily_search_official", f"{o} investor alert scam") for o in triage.entities.orgs[:2]] + \
           [(p_, "tavily_search_official", f"{p_} semak mule penipuan") for p_ in triage.entities.phones[:2]] + \
           [(u, "tavily_search_news", f"{u} phishing scam Malaysia") for u in triage.entities.urls[:1]]
    for ent, tool, q in adds:
        if ent.lower() not in have and len(plan.checks) < 6:
            plan.checks.append(Check(entity=ent, tool=tool, query=q, reason="policy floor: named entity in a scam-pattern message"))
    plan.needs_live_check = bool(plan.checks)


def _enforce_policy(verdict: Verdict, ledger_ctx: dict, tool_results: list[dict]) -> None:
    """Rules that must hold whatever the model wrote. Enforced in code, not by prompt."""
    from .schemas import Evidence
    # 1. Evidence may only cite URLs that a tool actually returned (no invented sources).
    real_urls = {r.get("url") for r in tool_results if r.get("url")}
    for r in tool_results:
        for x in r.get("results", []):
            real_urls.add(x.get("url"))
    verdict.evidence = [e for e in verdict.evidence if not e.source_url or e.source_url in real_urls]
    # 2. Household memory that cleared a case is always shown.
    if ledger_ctx.get("trusted_matches") and not any(e.kind == "ledger" for e in verdict.evidence):
        verdict.evidence.insert(0, Evidence(claim=f"Sender matches a trusted household contact: {ledger_ctx['trusted_matches'][0]}",
                                            source_url="", quote="", kind="ledger"))
    # 3. Official hits found by tools are always cited, even if the model forgot.
    cited = {e.source_url for e in verdict.evidence}
    for r in tool_results:
        if r.get("hit") and r.get("url") and r["url"] not in cited and r.get("kind") != "ledger":
            verdict.evidence.append(Evidence(claim=r["claim"], source_url=r["url"], quote=r.get("quote", "")[:240],
                                             kind="official_alert" if r.get("kind") == "official_alert" else "news"))
    # 4. No blank claims; "none found" only when there is nothing else.
    verdict.evidence = [e for e in verdict.evidence if e.claim.strip()]
    if any(e.kind != "none_found" for e in verdict.evidence):
        verdict.evidence = [e for e in verdict.evidence if e.kind != "none_found"]
    # Never an empty evidence list: say plainly that nothing was found.
    if not verdict.evidence:
        verdict.evidence.append(Evidence(claim="No official alert found for the names, numbers or links in this message",
                                         source_url="", quote="", kind="none_found"))
    # 5. High risk always points to the National Scam Response Centre.
    if verdict.risk == "high" and "997" not in verdict.recommended_action:
        verdict.recommended_action = verdict.recommended_action.rstrip(". ") + ". Jika wang sudah dihantar, hubungi NSRC 997 segera / If money was sent, call NSRC 997 now."
    # 6. Never say "safe".
    for f in ("headline_ms", "headline_en", "explanation"):
        val = getattr(verdict, f)
        setattr(verdict, f, val.replace(" is safe", " has no official alert").replace("selamat untuk", "tiada amaran rasmi untuk"))
    defaults = {"high": ("Amaran: mesej ini kelihatan seperti penipuan.", "Warning: this looks like a scam."),
                "medium": ("Berhati-hati: ada tanda-tanda penipuan.", "Caution: this message has scam signals."),
                "low": ("Tiada amaran rasmi ditemui untuk mesej ini.", "No official alert found for this message."),
                "unknown": ("Jaga tidak pasti — sila semak dengan keluarga.", "Jaga is unsure — please check with family.")}
    if not verdict.headline_ms.strip():
        verdict.headline_ms = defaults[verdict.risk][0]
    if not verdict.headline_en.strip():
        verdict.headline_en = defaults[verdict.risk][1]
    verdict.notify_family = verdict.risk in ("high", "medium")


class Jaga:
    def __init__(self, tf: TokenFactory | None = None, tavily: Tavily | None = None,
                 ledger: Ledger | None = None) -> None:
        self.tf = tf or TokenFactory()
        self.tavily = tavily or Tavily()
        self.ledger = ledger or Ledger()

    def run_case(self, text: str, opts: RunOptions | None = None, channel: str = "whatsapp") -> CaseResult:
        opts = opts or RunOptions()
        usage = Usage()
        t0 = time.time()
        case_id = str(uuid.uuid4())[:8]
        self.ledger.ensure_household(opts.household_id)
        self.ledger.audit(opts.household_id, "case.received", case_id, detail={"channel": channel, "chars": len(text)})

        # 1. Fast triage
        triage: Triage = self.tf.structured(
            "fast", TRIAGE_SYSTEM, TRIAGE_USER.format(channel=channel, text=text), Triage,
            thinking=False, usage=usage, context={"text": text})

        _backstop_entities(triage, text)

        # 2. Structured memory
        ledger_ctx = self.ledger.context_for(opts.household_id, triage) if opts.use_ledger else \
            {"trusted_matches": [], "novelty_flags": [], "recent_families": [], "contacts_known": 0, "payees_known": 0}

        plan: VerificationPlan | None = None
        tool_results: list[dict] = []
        if opts.tier in ("plan", "full"):
            # 3. Plan verification
            plan = self.tf.structured(
                "plan", PLAN_SYSTEM, PLAN_USER.format(text=text, triage_json=triage.model_dump_json(indent=1),
                                                      ledger_json=json.dumps(ledger_ctx, indent=1)),
                VerificationPlan, thinking=True, budget=config.PLAN_REASONING_BUDGET, usage=usage,
                context={"triage": triage, "ledger": ledger_ctx})
            _plan_floor(plan, triage)
            # 4. Execute checks (deterministic tools, capped)
            if plan.needs_live_check and not plan.ledger_answers_it:
                import re as _re
                from concurrent.futures import ThreadPoolExecutor
                checks = []
                for chk in plan.checks[: config.MAX_TOOL_ROUNDS * 2]:
                    chk.query = _re.sub(r"\s+", " ", chk.query).strip().strip('"')[:200] or chk.entity
                    chk.entity = _re.sub(r"\s+", " ", chk.entity).strip()[:120]
                    checks.append(chk)

                def _run(chk):
                    if chk.tool == "ledger_lookup":
                        return {"tool": "ledger_lookup", "entity": chk.entity, "query": chk.query,
                                "hit": bool(ledger_ctx["trusted_matches"]), "url": "", "kind": "ledger",
                                "quote": "", "claim": "; ".join(ledger_ctx["trusted_matches"]) or "not a known contact",
                                "results": []}
                    if not opts.use_tavily and chk.tool != "alert_cache":
                        return None
                    try:
                        return self.tavily.run_check(chk.tool, chk.query, chk.entity)
                    except Exception as e:  # noqa: BLE001  (one failed search never sinks the case)
                        return {"tool": chk.tool, "query": chk.query, "entity": chk.entity, "hit": False, "url": "",
                                "kind": "none_found", "quote": "", "claim": f"search failed: {str(e)[:80]}", "results": []}

                with ThreadPoolExecutor(max_workers=6) as ex:
                    for res in ex.map(_run, checks):
                        if res is None:
                            continue
                        tool_results.append(res)
                        if res["tool"] != "ledger_lookup":
                            self.ledger.audit(opts.household_id, "tool.call", res["tool"], outcome="hit" if res["hit"] else "none",
                                              detail={"query": res["query"], "entity": res["entity"], "url": res["url"]})

        # 5. Verdict
        slim_results = [{k: v for k, v in r.items() if k != "results"} | {"top_results": r.get("results", [])[:2]}
                        for r in tool_results]
        verdict: Verdict = self.tf.structured(
            "plan", VERDICT_SYSTEM, VERDICT_USER.format(
                triage_json=triage.model_dump_json(indent=1),
                plan_json=plan.model_dump_json(indent=1) if plan else "(fast tier: no plan)",
                results_json=json.dumps(slim_results, indent=1, default=str),
                ledger_json=json.dumps(ledger_ctx, indent=1)),
            Verdict, thinking=opts.tier != "fast", budget=config.PLAN_REASONING_BUDGET, usage=usage,
            context={"triage": triage, "ledger": ledger_ctx, "tool_results": tool_results})
        if not opts.use_ledger:
            verdict.novelty_flags = []
        _enforce_policy(verdict, ledger_ctx, tool_results)

        # 6. Escalation
        escalation: EscalationOpinion | None = None
        if opts.tier == "full" and verdict.escalate:
            escalation = self.tf.structured(
                "escalate", ESCALATE_SYSTEM, ESCALATE_USER.format(
                    text=text, triage_json=triage.model_dump_json(), verdict_json=verdict.model_dump_json(),
                    results_json=json.dumps(slim_results, default=str)),
                EscalationOpinion, thinking=True, budget=config.ESCALATE_REASONING_BUDGET, usage=usage,
                context={"verdict": verdict})
            if not escalation.agree_with_verdict:
                verdict.risk = escalation.risk
                verdict.explanation += f" Second opinion (Nemotron 3 Ultra): {escalation.reasoning_summary}"
            if escalation.additional_action:
                verdict.recommended_action += f" {escalation.additional_action}"

        result = CaseResult(case_id=case_id, household_id=opts.household_id, text=text, triage=triage, plan=plan,
                            verdict=verdict, escalation=escalation, models_used=usage.models_used,
                            usage=usage.as_dict(), cost_usd=round(usage.cost_usd, 6),
                            latency_ms=int((time.time() - t0) * 1000), tool_calls=usage.calls + self.tavily.calls[-len(tool_results):] if tool_results else usage.calls)

        # 7. Memory + audit (deterministic, every case)
        if opts.use_ledger:
            self.ledger.record_case(result)

        # 8. Family notification (summary only)
        if opts.notify and verdict.notify_family:
            protected = next((m["name"] for m in self.ledger.members(opts.household_id) if m["role"] == "protected"), "")
            for g in self.ledger.guardians(opts.household_id):
                if g.get("notify_policy") == "none" or not g.get("telegram_chat_id"):
                    continue
                ok = notify.send_telegram(g["telegram_chat_id"], notify.summary_for_guardian(result, protected))
                self.ledger.audit(opts.household_id, "notify.guardian", g["name"], outcome="success" if ok else "failure",
                                  detail={"policy": "summary_only", "case": case_id})
            self.ledger.mark_notified(case_id)
        return result

    def run_screenshot(self, image: bytes, mime: str = "image/jpeg", opts: RunOptions | None = None) -> CaseResult:
        """Screenshot → Nemotron 3.5 Super VL transcription → the normal case loop."""
        opts = opts or RunOptions()
        vusage = Usage()
        reading = self.tf.read_screenshot(image, mime, usage=vusage)
        self.ledger.ensure_household(opts.household_id)
        self.ledger.audit(opts.household_id, "vision.read", reading.app,
                          detail={"legible": reading.legible, "cues": reading.visual_cues, "bytes": len(image)})
        text = reading.message_text
        if reading.sender_shown:
            text = f"[Sender shown: {reading.sender_shown}]\n" + text
        if reading.visual_cues:
            text += "\n[Visual cues in screenshot: " + "; ".join(reading.visual_cues) + "]"
        res = self.run_case(text, opts, channel=f"screenshot:{reading.app}")
        res.models_used = {"vision": vusage.models_used.get("vision", ""), **res.models_used}
        res.cost_usd = round(res.cost_usd + vusage.cost_usd, 6)
        res.tool_calls = vusage.calls + res.tool_calls
        if not reading.legible:
            res.verdict.risk = "unknown"
            res.verdict.headline_ms = "Gambar kurang jelas — sila hantar semula atau salin teksnya."
            res.verdict.headline_en = "The screenshot is hard to read — please resend or paste the text."
        if opts.use_ledger:
            self.ledger.record_case(res)
        return res
