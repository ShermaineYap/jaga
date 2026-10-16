"""Family notification. Policy: guardians receive a SUMMARY only — risk,
headline, recommended action — never the raw message. The policy is enforced
here in code, not by prompt."""
from __future__ import annotations

import logging

import httpx

from . import config
from .schemas import CaseResult

log = logging.getLogger("jaga.notify")

RISK_EMOJI = {"high": "🔴", "medium": "🟠", "low": "🟢", "unknown": "⚪"}


def summary_for_guardian(result: CaseResult, protected_name: str = "") -> str:
    v = result.verdict
    who = f" ({protected_name})" if protected_name else ""
    lines = [f"{RISK_EMOJI[v.risk]} Jaga{who}: {v.headline_en}",
             f"Jenis / type: {v.family}",
             f"Tindakan / action: {v.recommended_action}"]
    if v.evidence and v.evidence[0].source_url:
        lines.append(f"Bukti / evidence: {v.evidence[0].source_url}")
    lines.append("(Summary only — the original message stays on the sender's phone.)")
    return "\n".join(lines)


def card_for_sender(result: CaseResult) -> str:
    v = result.verdict
    ev = "\n".join(f"  {i+1}. {e.claim}" + (f" — {e.source_url}" if e.source_url else "")
                   for i, e in enumerate(v.evidence[:3]))
    return (f"{RISK_EMOJI[v.risk]} {v.headline_ms}\n{v.headline_en}\n\n"
            f"{v.explanation}\n\nBukti / Evidence:\n{ev}\n\n➡️ {v.recommended_action}"
            + (f"\n\n🧠 {'; '.join(v.novelty_flags)}" if v.novelty_flags else ""))


def send_telegram(chat_id: str, text: str, mock: bool | None = None) -> bool:
    mock = (config.MOCK or not config.TELEGRAM_BOT_TOKEN) if mock is None else mock
    if mock:
        log.info("[mock telegram → %s] %s", chat_id, text.replace("\n", " | ")[:200])
        return True
    r = httpx.post(f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
                   json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True}, timeout=20)
    return r.status_code == 200
