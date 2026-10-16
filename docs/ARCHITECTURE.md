# Jaga architecture

```
 Senior / adult child
   │  forwards message text via Telegram (Hermes gateway)
   ▼
┌──────────────────────── OpenShell sandbox (nemohermes) ────────────────────────┐
│  Network policy: default-deny; allow only                                       │
│    api.tokenfactory.nebius.com · api.tavily.com · api.telegram.org              │
│  Credentials never enter the sandbox (OpenShell inference routing)              │
│                                                                                 │
│  Hermes Agent  ──► inference.local/v1 ──► Nebius Token Factory                   │
│    │                                   ├─ Nemotron 3.5 Lightning (triage,      │
│    │                                   │   entity extraction, JSON, thinking OFF)│
│    │                                   ├─ Nemotron 3 Super (verification plan + │
│    │                                   │   verdict synthesis, thinking ON,       │
│    │                                   │   client-side budget)                   │
│    │                                   └─ Nemotron 3 Ultra (only for "escalate" │
│    │                                       grade: money + ambiguous evidence)    │
│    ├─ tool: household_ledger (SQLite: members, contacts, payees, cases,         │
│    │        audit) — deterministic write after EVERY case                       │
│    ├─ tool: tavily_search_official (include_domains = SC Investor Alert List,   │
│    │        PDRM Semak Mule, BNM consumer alerts, MCMC, NSRC)                    │
│    ├─ tool: tavily_search_news (topic=news, days=90, Malaysian outlets)         │
│    ├─ tool: tavily_extract (pull the exact alert page as evidence)              │
│    ├─ tool: alert_cache (nightly Tavily Map→Extract of alert lists, Hermes cron)│
│    ├─ tool: notify_family (Telegram message to guardians; summary only)         │
│    └─ skill: jaga_case_protocol (hermes/SKILL.md, versioned in repo)            │
│                                                                                 │
│  OCSF audit log ──► "What Jaga did with your data" page                         │
└─────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
 Family dashboard (FastAPI): verdict cards with cited evidence · memory viewer ·
 policy screen (who is told what + OpenShell policy) · audit timeline · export / delete-all
```

## The case loop (`jaga/pipeline.py`)

| # | Step | Model / tool | Thinking | Output |
|---|---|---|---|---|
| 1 | Triage | Nemotron 3.5 Lightning | off | `Triage` JSON: family, confidence, language, urgency cues, asks_for, entities |
| 2 | Memory context | `Ledger.context_for` | — | trusted matches, novelty flags, recent families (small + structured; no raw history goes to the model) |
| 3 | Verification plan | Nemotron 3 Super | on, budget 2.5k | `VerificationPlan`: ≤6 checks, each entity → tool → query |
| 4 | Execute checks | Tavily / cache / ledger | — | evidence-or-nothing per check; a result only counts if the entity appears in it |
| 5 | Verdict | Nemotron 3 Super | on, budget 2.5k | `Verdict`: risk, BM + EN headlines, cited evidence, action, notify/escalate flags |
| 6 | Second opinion | Nemotron 3 Ultra | on, budget 6k | only if `verdict.escalate` |
| 7 | Record | `Ledger.record_case` | — | case row + every phone/account becomes a contact/payee row + audit events |
| 8 | Notify | Telegram | — | guardians: risk + headline + action (+ one evidence link). Never the message. |

Every switch (`tier`, `use_tavily`, `use_ledger`) is a `RunOptions` field so the evaluation
harness can ablate it and report what each component contributes.

## Why three tiers

* Lightning runs on **every** message: $0.06/$0.24 per 1M tokens, so 1,000 messages cost cents.
* Super runs the two judgment steps with reasoning on, under a budget, so cost is bounded.
* Ultra is reserved for the rare escalation. In the eval it is the difference between a
  "flashier" single-model demo and a reported cost/accuracy trade-off.

## Why the ledger is not a MEMORY.md

OpenClaw- and Hermes-style agents keep memory as agent-curated plaintext: the agent decides what
to save, facts are lost at context compaction, and recall is keyword search. For a guardian that
must know *Mum's real insurance agent* and *this payee has never been seen before*, capture cannot
be optional. The ledger writes structured rows deterministically after every case, models two
subjects (protected person + guardians) as first-class, and is exportable/deletable by the family.

## Failure handling

* Model IDs in `.env`; each role has a fallback chain; `/health` resolves them against `/v1/models`.
* 402 → dashboard shows "paused"; cached verdicts still serve. 429 → one backoff then next model.
* Tools are deterministic and testable without a model; tool rounds are capped.
* `JAGA_MOCK=1` is a complete offline path (tests, CI, recorded-run fallback during judging).
