"""Seed the demo household used in the video: Puan Aminah (protected), her
daughter Siti (guardian), and Mum's real insurance agent as a trusted contact.
Then run the three demo messages so the dashboard opens with cases.

  python scripts/seed_demo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jaga import config  # noqa: E402
from jaga.config import RunOptions  # noqa: E402
from jaga.pipeline import Jaga  # noqa: E402

DEMO_MESSAGES = [
    # RRJ Pro was added to the SC Investor Alert List on 15 Oct 2026 ("Potential Clone Entity").
    # The message itself is a demo script written for this project.
    ("telegram", "Salam Puan Aminah. Platform pelaburan RRJ Pro tawarkan pulangan 30% sebulan DIJAMIN. "
                 "Ramai pesara dah untung. Modal minima RM5,000, peluang terhad hari ini sahaja. WhatsApp 011-9999 0123."),
    ("whatsapp", "Pos Laju: Bungkusan anda ditahan di kastam. Sila bayar yuran RM48 di poslaju-kastam.xyz dalam 24 jam untuk pelepasan."),
    ("whatsapp", "Puan, ini Faizal dari Prudential. Premium polis puan jatuh tempo 20 Okt, boleh saya call esok pagi untuk sahkan? 012-345 6789"),
]


def main() -> None:
    j = Jaga()
    hh = config.DEMO_HOUSEHOLD
    j.ledger.ensure_household(hh, "Keluarga Aminah")
    if not j.ledger.members(hh):
        j.ledger.add_member(hh, "Puan Aminah", "protected", "")
        j.ledger.add_member(hh, "Siti (daughter)", "guardian", "", "summary")
    if not any(c["name"] == "Encik Faizal" for c in j.ledger.contacts(hh)):
        j.ledger.add_contact(hh, "Encik Faizal", "012-345 6789", "Prudential", "insurance agent", trusted=True, added_by="Siti")
    for ch, text in DEMO_MESSAGES:
        r = j.run_case(text, RunOptions(household_id=hh, notify=False), channel=ch)
        print(f"[{r.verdict.risk:7s}] {r.verdict.family:13s} {r.verdict.headline_en}  (${r.cost_usd:.4f}, {r.latency_ms} ms)")
    print("\nSeeded. Start the dashboard:  uvicorn jaga.dashboard.app:app --port 8000")


if __name__ == "__main__":
    main()
