"""Hermes Agent tool definitions for Jaga.

Hermes discovers Python tools in ~/.hermes/tools. Each function below is a
tool the agent can call; the heavy lifting stays in the `jaga` package so the
standalone bot, the dashboard and the Hermes deployment share one pipeline.
"""
from __future__ import annotations

import json

from jaga import config, notify
from jaga.config import RunOptions
from jaga.pipeline import Jaga

_jaga = Jaga()


def jaga_check(text: str, channel: str = "telegram", household_id: str = config.DEMO_HOUSEHOLD) -> str:
    """Run the full Jaga verification loop on a forwarded message and return the reply card.
    Also records the case in the household ledger and notifies guardians (summary only)."""
    res = _jaga.run_case(text, RunOptions(household_id=household_id), channel=channel)
    return notify.card_for_sender(res)


def jaga_trust(name: str, phone: str = "", org: str = "", relation: str = "", household_id: str = config.DEMO_HOUSEHOLD) -> str:
    """Add a trusted contact to household memory. Only call this on a guardian's instruction."""
    _jaga.ledger.add_contact(household_id, name, phone, org, relation, trusted=True, added_by="hermes")
    return f"Remembered {name} ({phone}, {org or relation}) as trusted."


def jaga_memory(household_id: str = config.DEMO_HOUSEHOLD) -> str:
    """Summarise what Jaga remembers for this household (trusted contacts, payees, recent cases)."""
    c = [x for x in _jaga.ledger.contacts(household_id) if x["trusted"]]
    cases = _jaga.ledger.recent_cases(household_id, 10)
    return json.dumps({"trusted_contacts": [f"{x['name']} {x['phone']} {x['org']}" for x in c],
                       "payees_seen": len(_jaga.ledger.payees(household_id)),
                       "recent_cases": [{"risk": k["risk"], "family": k["family"]} for k in cases]}, ensure_ascii=False)


def jaga_refresh_alert_cache() -> str:
    """Nightly: Tavily Map → Extract of official alert lists into the local cache."""
    n = _jaga.tavily.refresh_alert_cache()
    _jaga.ledger.audit(config.DEMO_HOUSEHOLD, "cron.alert_refresh", detail={"pages": n})
    return f"cached {n} alert pages"


def jaga_weekly_digest(household_id: str = config.DEMO_HOUSEHOLD) -> str:
    """Weekly: one summary message to guardians."""
    cases = _jaga.ledger.recent_cases(household_id, 200)
    by_risk: dict[str, int] = {}
    for k in cases:
        by_risk[k["risk"]] = by_risk.get(k["risk"], 0) + 1
    text = "📬 Jaga weekly: " + ", ".join(f"{r}: {n}" for r, n in sorted(by_risk.items())) + " cases checked."
    for g in _jaga.ledger.guardians(household_id):
        if g.get("telegram_chat_id"):
            notify.send_telegram(g["telegram_chat_id"], text)
    return text
