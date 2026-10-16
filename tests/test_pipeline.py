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


def test_misattributed_web_evidence_is_dropped():
    """A model claim citing a real URL for an entity that page does not contain must not survive."""
    from jaga.pipeline import _enforce_policy
    from jaga.schemas import Evidence, Verdict
    v = Verdict(risk="high", family="investment", headline_ms="x", headline_en="x", explanation="x",
                evidence=[Evidence(claim="011-9999 0123 appears in BNM list", source_url="https://bnm.gov.my/x",
                                   quote="", kind="official_alert")],
                recommended_action="Do not pay.", notify_family=True, escalate=False)
    results = [{"tool": "tavily_search_official", "entity": "011-9999 0123", "hit": False, "url": "", "kind": "none_found",
                "claim": "No alert", "quote": "", "results": [{"url": "https://bnm.gov.my/x"}]},
               {"tool": "tavily_search_official", "entity": "RRJ Pro", "hit": True, "url": "https://sc.com.my/a",
                "kind": "official_alert", "claim": "'RRJ Pro' appears in SC list", "quote": "1. Potential Clone Entity - RRJ Pro"}]
    _enforce_policy(v, {"trusted_matches": []}, results)
    urls = [e.source_url for e in v.evidence]
    assert "https://bnm.gov.my/x" not in urls
    assert "https://sc.com.my/a" in urls
    assert "997" in v.recommended_action


def test_name_from_new_number_is_not_trusted():
    """'Mum, it's Siti, new number' must not be cleared by household memory."""
    j = make()
    j.ledger.add_contact(HH, "Siti", "013-222 3344", "", "daughter")
    from jaga.schemas import Entities, Triage
    tri = Triage(family="impersonation", confidence=0.9, language="en", urgency_cues=[], asks_for=["transfer"],
                 entities=Entities(phones=["011-9999 0461"], persons=["Siti"], bank_accounts=["5566778899001"]),
                 one_line="Siti asks for RM900 from a new number")
    ctx = j.ledger.context_for(HH, tri)
    assert ctx["trusted_matches"] == []
    assert any("claims to be Siti" in f for f in ctx["novelty_flags"])
    real = tri.model_copy(deep=True)
    real.entities.phones = ["013-222 3344"]
    assert j.ledger.context_for(HH, real)["trusted_matches"]


def test_generic_word_is_not_a_verifiable_entity():
    """A check on the word 'phone' must be re-mapped to the real number or dropped."""
    from jaga.pipeline import _concrete_entity
    from jaga.schemas import Check, Entities, Triage
    tri = Triage(family="mule", confidence=0.9, language="ms", urgency_cues=[], asks_for=[],
                 entities=Entities(phones=["011-9999 0461"], bank_accounts=["5566778899001"]), one_line="x")
    assert _concrete_entity(Check(entity="phone", tool="tavily_search_official", query="011-9999 0461 semak mule", reason=""), tri) == "011-9999 0461"
    assert _concrete_entity(Check(entity="phone", tool="tavily_search_official", query="phone scam", reason=""), tri) is None


def test_headline_cannot_claim_unverified_list_match():
    from jaga.pipeline import _enforce_policy
    from jaga.schemas import Verdict
    v = Verdict(risk="high", family="mule", headline_ms="Nombor ini dalam senarai penipuan", headline_en="Number appears on scam list",
                explanation="", evidence=[], recommended_action="", notify_family=True, escalate=False)
    _enforce_policy(v, {"trusted_matches": [], "novelty_flags": ["first message from 011"]}, [])
    assert "senarai" not in v.headline_ms.lower() and "list" not in v.headline_en.lower()
    assert v.recommended_action.startswith("Jangan") and "997" in v.recommended_action
    assert v.explanation


def test_impersonation_of_saved_contact_asking_money_is_high():
    from jaga.pipeline import _enforce_policy
    from jaga.schemas import Entities, Triage, Verdict
    tri = Triage(family="legit", confidence=0.6, language="en", urgency_cues=[], asks_for=["transfer"],
                 entities=Entities(phones=["011-9999 0461"], bank_accounts=["5566778899001"], amounts=["RM900"]), one_line="x")
    v = Verdict(risk="low", family="legit", headline_ms="ok", headline_en="ok", explanation="x", evidence=[],
                recommended_action="Proceed.", notify_family=False, escalate=False)
    _enforce_policy(v, {"trusted_matches": [], "novelty_flags": ["claims to be Siti but uses a number not saved for them"]}, [], tri)
    assert v.risk == "high" and v.family == "impersonation" and "Siti" in v.headline_en and "997" in v.recommended_action
