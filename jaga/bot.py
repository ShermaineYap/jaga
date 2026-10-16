"""Telegram gateway for Jaga (long polling, no webhook needed).

Usage:  python -m jaga.bot
Commands:
  /start                     – register this chat; first chat becomes the protected member
  /guardian <name>           – register this chat as a guardian (receives summaries only)
  /trust <name> | <phone> | <org/relation>   – add a trusted contact to household memory
  /memory                    – show what Jaga remembers (contacts / payees)
  /policy                    – show who gets told what
  any other text             – treated as a forwarded message and checked

When Jaga runs inside Hermes Agent (see hermes/), Hermes' own Telegram gateway
replaces this file; this standalone bot exists so the demo works without it.
"""
from __future__ import annotations

import logging
import time

import httpx

from . import config, notify
from .config import RunOptions
from .pipeline import Jaga

log = logging.getLogger("jaga.bot")
API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


def handle(jaga: Jaga, chat_id: str, text: str, from_name: str) -> str:
    hh = jaga.ledger.household_for_chat(chat_id) or config.DEMO_HOUSEHOLD
    jaga.ledger.ensure_household(hh)
    if text.startswith("/start"):
        if not jaga.ledger.household_for_chat(chat_id):
            role = "protected" if not any(m["role"] == "protected" for m in jaga.ledger.members(hh)) else "guardian"
            jaga.ledger.add_member(hh, from_name, role, chat_id)
        return ("Salam! Saya Jaga 🛡️\nHantar (forward) mana-mana mesej yang mencurigakan kepada saya dan saya akan semak "
                "dengan senarai amaran rasmi (SC, PDRM, BNM).\n\nHi! Forward any suspicious message to me and I'll check it "
                "against official alert lists. Use /guardian <name> on a family member's phone so they get a summary.")
    if text.startswith("/guardian"):
        name = text.partition(" ")[2].strip() or from_name
        jaga.ledger.add_member(hh, name, "guardian", chat_id)
        return f"OK — {name} will receive summary-only alerts (never the original message)."
    if text.startswith("/trust"):
        parts = [p.strip() for p in text.partition(" ")[2].split("|")]
        if len(parts) < 2:
            return "Format: /trust Name | phone | org or relation"
        name, phone = parts[0], parts[1]
        org = parts[2] if len(parts) > 2 else ""
        jaga.ledger.add_contact(hh, name, phone, org, org, trusted=True, added_by=from_name)
        return f"Remembered: {name} ({phone}, {org}) is a trusted contact for this household."
    if text.startswith("/memory"):
        cs = [c for c in jaga.ledger.contacts(hh) if c["trusted"]]
        ps = jaga.ledger.payees(hh)
        return ("Trusted contacts:\n" + "\n".join(f"• {c['name']} {c['phone']} {c['org']}" for c in cs) +
                f"\n\nPayees seen: {len(ps)}\nCases checked: {len(jaga.ledger.recent_cases(hh, 1000))}") or "Nothing yet."
    if text.startswith("/policy"):
        gs = jaga.ledger.guardians(hh)
        return ("Policy: guardians receive risk + headline + action only. Original messages never leave this sandbox.\n"
                "Network: only Token Factory, Tavily and Telegram are reachable.\nGuardians: " +
                (", ".join(g["name"] for g in gs) or "none yet"))
    result = jaga.run_case(text, RunOptions(household_id=hh), channel="telegram")
    return notify.card_for_sender(result)


def handle_photo(jaga: Jaga, chat_id: str, file_id: str) -> str:
    """Download the largest photo size and run it through Nemotron 3.5 Super VL → the case loop."""
    hh = jaga.ledger.household_for_chat(chat_id) or config.DEMO_HOUSEHOLD
    info = httpx.get(f"{API}/getFile", params={"file_id": file_id}, timeout=20).json()
    path = info["result"]["file_path"]
    img = httpx.get(f"https://api.telegram.org/file/bot{config.TELEGRAM_BOT_TOKEN}/{path}", timeout=30).content
    result = jaga.run_screenshot(img, "image/jpeg", RunOptions(household_id=hh))
    return notify.card_for_sender(result)


def poll_forever() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set")
    jaga = Jaga()
    offset = 0
    log.info("Jaga bot polling… (mock=%s)", jaga.tf.mock)
    while True:
        try:
            r = httpx.get(f"{API}/getUpdates", params={"timeout": 30, "offset": offset}, timeout=40).json()
            for upd in r.get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message") or {}
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text = msg.get("text") or msg.get("caption") or ""
                if msg.get("photo"):
                    reply = handle_photo(jaga, chat_id, msg["photo"][-1]["file_id"])
                elif text:
                    reply = handle(jaga, chat_id, text, msg.get("from", {}).get("first_name", "user"))
                else:
                    continue
                httpx.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": reply, "disable_web_page_preview": True}, timeout=20)
        except Exception as e:  # noqa: BLE001
            log.error("poll error: %s", e)
            time.sleep(3)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # httpx logs full request URLs at INFO, and Telegram URLs contain the bot token.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    poll_forever()
