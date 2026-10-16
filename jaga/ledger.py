"""Household ledger: Jaga's structured, two-subject memory.

Why this exists: OpenClaw- and Hermes-style agents keep memory as agent-curated
plaintext that is lost at context compaction and searched by keyword. Jaga
instead writes structured rows deterministically after EVERY case — contacts,
payees, verdicts, escalations — so capture never depends on the model "deciding
to remember", and the planner receives explicit novelty features ("payee never
seen before", "first message from this number") that are themselves scam
signals. The protected person (e.g. Mum) and the guardian (e.g. daughter) are
both first-class subjects.

Every write also appends an OCSF-style audit event, which the dashboard renders
as "What Jaga did with your data".
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
import uuid
from typing import Any

from . import config
from .schemas import CaseResult, Triage

SCHEMA = """
CREATE TABLE IF NOT EXISTS households (
    id TEXT PRIMARY KEY, name TEXT, language TEXT DEFAULT 'ms', created_at REAL);
CREATE TABLE IF NOT EXISTS members (
    id TEXT PRIMARY KEY, household_id TEXT, name TEXT, role TEXT,  -- 'protected' | 'guardian'
    telegram_chat_id TEXT, notify_policy TEXT DEFAULT 'summary',   -- 'summary' | 'none'
    created_at REAL);
CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY, household_id TEXT, name TEXT, phone TEXT, org TEXT, relation TEXT,
    trusted INTEGER DEFAULT 1, added_by TEXT, first_seen REAL, last_seen REAL, times_seen INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS payees (
    id TEXT PRIMARY KEY, household_id TEXT, label TEXT, account TEXT, org TEXT,
    trusted INTEGER DEFAULT 0, first_seen REAL, last_seen REAL, times_seen INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY, household_id TEXT, ts REAL, text_hash TEXT, text TEXT,
    family TEXT, risk TEXT, triage_json TEXT, plan_json TEXT, verdict_json TEXT, escalation_json TEXT,
    models_json TEXT, cost_usd REAL, latency_ms INTEGER, tool_calls_json TEXT, notified INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, household_id TEXT, class_uid INTEGER, activity TEXT,
    actor TEXT, target TEXT, outcome TEXT, detail TEXT);
"""


def _norm_phone(p: str) -> str:
    d = re.sub(r"\D", "", p)
    if d.startswith("60"):
        d = "0" + d[2:]
    return d


class Ledger:
    def __init__(self, db_path=None) -> None:
        self.db_path = str(db_path or config.DB_PATH)
        with self._con() as con:
            con.executescript(SCHEMA)

    def _con(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path, timeout=30)
        con.row_factory = sqlite3.Row
        return con

    # ---------------------------------------------------------------- audit
    def audit(self, household_id: str, activity: str, target: str = "", outcome: str = "success",
              detail: dict | None = None, actor: str = "jaga-agent", class_uid: int = 6003) -> None:
        """class_uid 6003 = OCSF 'API Activity'; 3005 = 'Account Change'; 6001 = 'Web Resources'."""
        with self._con() as con:
            con.execute("INSERT INTO audit (ts,household_id,class_uid,activity,actor,target,outcome,detail) VALUES (?,?,?,?,?,?,?,?)",
                        (time.time(), household_id, class_uid, activity, actor, target, outcome, json.dumps(detail or {})))

    def audit_events(self, household_id: str, limit: int = 200) -> list[dict[str, Any]]:
        with self._con() as con:
            rows = con.execute("SELECT * FROM audit WHERE household_id=? ORDER BY ts DESC LIMIT ?", (household_id, limit)).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------ households
    def ensure_household(self, household_id: str, name: str = "", language: str = "ms") -> None:
        with self._con() as con:
            con.execute("INSERT OR IGNORE INTO households VALUES (?,?,?,?)", (household_id, name or household_id, language, time.time()))

    def add_member(self, household_id: str, name: str, role: str, telegram_chat_id: str = "",
                   notify_policy: str = "summary") -> str:
        mid = str(uuid.uuid4())[:8]
        with self._con() as con:
            con.execute("INSERT INTO members VALUES (?,?,?,?,?,?,?)",
                        (mid, household_id, name, role, telegram_chat_id, notify_policy, time.time()))
        self.audit(household_id, "member.add", name, detail={"role": role, "policy": notify_policy}, class_uid=3005)
        return mid

    def guardians(self, household_id: str) -> list[dict[str, Any]]:
        with self._con() as con:
            return [dict(r) for r in con.execute("SELECT * FROM members WHERE household_id=? AND role='guardian'", (household_id,))]

    def members(self, household_id: str) -> list[dict[str, Any]]:
        with self._con() as con:
            return [dict(r) for r in con.execute("SELECT * FROM members WHERE household_id=?", (household_id,))]

    def household_for_chat(self, chat_id: str) -> str | None:
        with self._con() as con:
            r = con.execute("SELECT household_id FROM members WHERE telegram_chat_id=?", (str(chat_id),)).fetchone()
        return r["household_id"] if r else None

    # -------------------------------------------------------------- contacts
    def add_contact(self, household_id: str, name: str, phone: str = "", org: str = "", relation: str = "",
                    trusted: bool = True, added_by: str = "guardian") -> str:
        cid = str(uuid.uuid4())[:8]
        now = time.time()
        with self._con() as con:
            con.execute("INSERT INTO contacts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (cid, household_id, name, _norm_phone(phone), org, relation, int(trusted), added_by, now, now, 0))
        self.audit(household_id, "contact.add", name, detail={"trusted": trusted, "org": org}, class_uid=3005)
        return cid

    def contacts(self, household_id: str) -> list[dict[str, Any]]:
        with self._con() as con:
            return [dict(r) for r in con.execute("SELECT * FROM contacts WHERE household_id=? ORDER BY last_seen DESC", (household_id,))]

    def payees(self, household_id: str) -> list[dict[str, Any]]:
        with self._con() as con:
            return [dict(r) for r in con.execute("SELECT * FROM payees WHERE household_id=? ORDER BY last_seen DESC", (household_id,))]

    # --------------------------------------------------------------- context
    def context_for(self, household_id: str, triage: Triage) -> dict[str, Any]:
        """What the planner gets to see: trusted matches + novelty flags.
        Deliberately small and structured — no raw history is sent to the model."""
        contacts = self.contacts(household_id)
        payees = self.payees(household_id)
        phones = {_norm_phone(p) for p in triage.entities.phones}
        orgs = {o.lower() for o in triage.entities.orgs}
        persons = {p.lower() for p in triage.entities.persons}
        trusted, flags = [], []
        for c in contacts:
            if c["trusted"] and ((c["phone"] and c["phone"] in phones) or
                                 (c["org"] and c["org"].lower() in orgs) or
                                 (c["name"] and c["name"].lower() in persons)):
                trusted.append(f"{c['name']} ({c['relation'] or c['org']})")
        known_accts = {p["account"] for p in payees}
        for a in triage.entities.bank_accounts:
            if a not in known_accts:
                flags.append(f"payee account {a} never seen before")
        known_phones = {c["phone"] for c in contacts}
        for p in phones:
            if p not in known_phones:
                flags.append(f"first message from {p}")
        for o in triage.entities.orgs:
            if o.lower() not in {c["org"].lower() for c in contacts if c["org"]}:
                flags.append(f"{o} is not a known household relationship")
        recent = self.recent_cases(household_id, limit=5)
        return {"trusted_matches": trusted, "novelty_flags": flags[:5],
                "recent_families": [r["family"] for r in recent],
                "contacts_known": len(contacts), "payees_known": len(payees)}

    # ----------------------------------------------------------------- cases
    def record_case(self, result: CaseResult) -> None:
        now = time.time()
        with self._con() as con:
            con.execute("INSERT OR REPLACE INTO cases VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                result.case_id, result.household_id, now,
                hashlib.sha256(result.text.encode()).hexdigest()[:16], result.text,
                result.verdict.family, result.verdict.risk,
                result.triage.model_dump_json(), result.plan.model_dump_json() if result.plan else None,
                result.verdict.model_dump_json(), result.escalation.model_dump_json() if result.escalation else None,
                json.dumps(result.models_used), result.cost_usd, result.latency_ms, json.dumps(result.tool_calls), 0))
            # Deterministic capture: every phone / account seen becomes a row.
            for p in result.triage.entities.phones:
                np_ = _norm_phone(p)
                r = con.execute("SELECT id FROM contacts WHERE household_id=? AND phone=?", (result.household_id, np_)).fetchone()
                if r:
                    con.execute("UPDATE contacts SET last_seen=?, times_seen=times_seen+1 WHERE id=?", (now, r["id"]))
                else:
                    con.execute("INSERT INTO contacts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                (str(uuid.uuid4())[:8], result.household_id, "", np_, "", "unknown sender", 0, "jaga", now, now, 1))
            for a in result.triage.entities.bank_accounts:
                r = con.execute("SELECT id FROM payees WHERE household_id=? AND account=?", (result.household_id, a)).fetchone()
                if r:
                    con.execute("UPDATE payees SET last_seen=?, times_seen=times_seen+1 WHERE id=?", (now, r["id"]))
                else:
                    con.execute("INSERT INTO payees VALUES (?,?,?,?,?,?,?,?,?)",
                                (str(uuid.uuid4())[:8], result.household_id, "", a, "", 0, now, now, 1))
        self.audit(result.household_id, "case.record", result.case_id,
                   detail={"risk": result.verdict.risk, "family": result.verdict.family, "cost_usd": round(result.cost_usd, 5)})

    def mark_notified(self, case_id: str) -> None:
        with self._con() as con:
            con.execute("UPDATE cases SET notified=1 WHERE id=?", (case_id,))

    def recent_cases(self, household_id: str, limit: int = 50) -> list[dict[str, Any]]:
        with self._con() as con:
            rows = con.execute("SELECT * FROM cases WHERE household_id=? ORDER BY ts DESC LIMIT ?", (household_id, limit)).fetchall()
        return [dict(r) for r in rows]

    def case(self, case_id: str) -> dict[str, Any] | None:
        with self._con() as con:
            r = con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        return dict(r) if r else None

    # ------------------------------------------------------- user data rights
    def export(self, household_id: str) -> dict[str, Any]:
        self.audit(household_id, "data.export", household_id, class_uid=6001)
        return {"household": household_id, "members": self.members(household_id), "contacts": self.contacts(household_id),
                "payees": self.payees(household_id), "cases": self.recent_cases(household_id, 10_000),
                "audit": self.audit_events(household_id, 10_000)}

    def delete_all(self, household_id: str) -> None:
        with self._con() as con:
            for t in ("members", "contacts", "payees", "cases"):
                con.execute(f"DELETE FROM {t} WHERE household_id=?", (household_id,))
            con.execute("DELETE FROM households WHERE id=?", (household_id,))
        self.audit(household_id, "data.delete_all", household_id, class_uid=3005)
