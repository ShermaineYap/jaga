"""Offline tests (mock mode). Run:  make test"""
from __future__ import annotations

import os
import tempfile

os.environ["JAGA_MOCK"] = "1"
os.environ.setdefault("JAGA_DB", tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False).name)

from jaga.config import RunOptions  # noqa: E402
from jaga.ledger import Ledger  # noqa: E402
from jaga.llm import TokenFactory  # noqa: E402
from jaga.pipeline import Jaga  # noqa: E402
from jaga.schemas import Triage  # noqa: E402
from jaga.tavily_tools import Tavily, _relevant_hit  # noqa: E402

HH = "test-household"


def make() -> Jaga:
    db = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False).name
    j = Jaga(TokenFactory(mock=True), Tavily(mock=True, db_path=db), Ledger(db))
    j.ledger.ensure_household(HH)
    j.ledger.add_member(HH, "Puan Aminah", "protected", "1")
    j.ledger.add_member(HH, "Siti", "guardian", "2")
    j.ledger.add_contact(HH, "Encik Faizal", "012-345 6789", "Prudential", "insurance agent")
    return j


def test_phishing_is_high_with_evidence():
    r = make().run_case("SEGERA: Akaun Maybank anda disekat. Sahkan TAC di maybank2u-secure-verify.xyz", RunOptions(household_id=HH, notify=False))
    assert r.verdict.risk == "high"
    assert r.verdict.family == "phishing_otp"
    assert any(e.source_url for e in r.verdict.evidence)
    assert "997" in r.verdict.recommended_action


def test_trusted_contact_clears_legit_followup():
    r = make().run_case("Puan, ini Faizal dari Prudential. Premium jatuh tempo 20 Okt, boleh saya call? 012-345 6789", RunOptions(household_id=HH, notify=False))
    assert r.verdict.risk == "low"
    assert any(e.kind == "ledger" for e in r.verdict.evidence)


def test_memory_is_written_deterministically():
    j = make()
    j.run_case("Golden Harvest Capital 30% return guaranteed, call 011-9999 0123, deposit to 1234567890123", RunOptions(household_id=HH, notify=False))
    phones = {c["phone"] for c in j.ledger.contacts(HH)}
    assert "01199990123" in phones
    assert any(p["account"] == "1234567890123" for p in j.ledger.payees(HH))
    acts = {e["activity"] for e in j.ledger.audit_events(HH)}
    assert {"case.received", "case.record", "tool.call"} <= acts


def test_novelty_flags_fire_for_unknown_payee():
    j = make()
    r = j.run_case("Transfer RM3,000 to account 9876543210987 for your parcel fee", RunOptions(household_id=HH, notify=False))
    assert any("never seen before" in f for f in r.verdict.novelty_flags)


def test_ablations_change_behaviour():
    j = make()
    text = "Golden Harvest Capital guaranteed 30% monthly, SC licensed, call 011-9999 0123"
    full = j.run_case(text, RunOptions(household_id=HH, notify=False, tier="full"))
    no_tav = j.run_case(text, RunOptions(household_id=HH, notify=False, use_tavily=False))
    assert any(e.source_url for e in full.verdict.evidence)
    assert not any(e.kind == "official_alert" for e in no_tav.verdict.evidence)


def test_guardian_summary_never_contains_original_text():
    from jaga import notify
    j = make()
    secret = "Transfer RM5,000 to account 1111222233334444 by today"
    r = j.run_case(secret, RunOptions(household_id=HH, notify=False))
    s = notify.summary_for_guardian(r, "Puan Aminah")
    assert "1111222233334444" not in s and "RM5,000" not in s


def test_relevant_hit_requires_entity_in_result():
    assert _relevant_hit([{"url": "u", "title": "SC alert: Foo Capital", "snippet": "", "raw": ""}], "Foo Capital")
    assert _relevant_hit([{"url": "u", "title": "SC alert: Bar", "snippet": "", "raw": ""}], "Foo Capital") is None


def test_export_and_delete():
    j = make()
    j.run_case("hello mum", RunOptions(household_id=HH, notify=False))
    assert j.ledger.export(HH)["cases"]
    j.ledger.delete_all(HH)
    assert not j.ledger.recent_cases(HH)


def test_triage_schema_is_valid_json_schema():
    s = Triage.model_json_schema()
    assert "family" in s["properties"]
