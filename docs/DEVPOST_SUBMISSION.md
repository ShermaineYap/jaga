# Devpost submission text — Jaga

> Paste into the Devpost form. Keep the template headings ("Inspiration", "What it does", …) —
> judges look for them. Replace `<DEMO_URL>`, `<REPO_URL>`, `<VIDEO_URL>` and the numbers marked
> `[fill from eval/results/RESULTS.md]` after the live eval run.

**Project name:** Jaga — a private guardian that verifies before it warns
**Tagline:** An always-on, private scam-shield for Malaysian seniors: NVIDIA Nemotron on Nebius Token Factory checks every forwarded message against official alert lists via Tavily, remembers who the family really deals with, and tells the right person — with evidence.
**Track:** Personal AI · **Bonus:** Best Use of Tavily
**Built with:** Nebius Token Factory, NVIDIA Nemotron 3.5 Lightning, NVIDIA Nemotron 3 Super, NVIDIA Nemotron 3 Ultra, NVIDIA OpenShell, NVIDIA NemoClaw, Hermes Agent, Tavily, Python, FastAPI, SQLite, Telegram

---

## Inspiration

Malaysians lost RM2.97 billion to online fraud in 2025. Bukit Aman counted 1,916 elderly victims losing over RM250 million in a single year, and NHMS 2025 found ~770,800 Malaysians over 60 now live alone. The scam arrives as a WhatsApp or SMS on a phone nobody else sees. We wanted a guardian that lives on that phone, is genuinely private, and — unlike a chatbot — *checks* before it speaks.

## What it does

Forward any suspicious message to Jaga on Telegram. Jaga:
1. **Triages** it with Nemotron 3.5 Lightning (scam family, entities, urgency cues, what the sender asks for) — JSON-schema structured output, thinking off.
2. **Consults household memory** — a structured ledger of trusted contacts and payees — and computes novelty flags like *"payee never seen before"*.
3. **Plans verification** with Nemotron 3 Super (reasoning on, budgeted): which entity needs which check.
4. **Verifies via Tavily** against official Malaysian sources only (Securities Commission investor alert list, PDRM Semak Mule, Bank Negara, MCMC, NSRC) plus recent Malaysian news, with a nightly Map→Extract cache of the alert lists.
5. **Writes a verdict** where every claim cites a URL or household memory — or says plainly that nothing was found. Never "safe".
6. **Escalates** to Nemotron 3 Ultra only when money is involved and evidence is thin.
7. **Notifies guardians with a summary only** (risk, headline, action) — never the original message — and records everything to an audit timeline the family can read, export or delete.

## How we built it

Hermes Agent runs inside an NVIDIA OpenShell sandbox (onboarded with NemoClaw's `nemohermes`), with a default-deny network policy allowing exactly three hosts: Nebius Token Factory, Tavily, Telegram. OpenShell's inference routing means the API key never enters the sandbox. All three Nemotron tiers are called through Token Factory's OpenAI-compatible API with JSON-schema structured output and `chat_template_kwargs.enable_thinking`. Tavily Search (`include_domains`), Extract and Map are deterministic tools the planner chooses; a result only counts as evidence if the entity itself appears in it. The household ledger is SQLite with deterministic writes after every case. The evaluation sweep runs through Token Factory's Batch API.

## Results

ScamBench-MY: 300 labelled Bahasa Malaysia / English / Manglish messages (150 scam across 6 families, 150 legitimate incl. hard negatives).
- F1 (full pipeline): **[fill]** · false-positive rate on legitimate messages: **[fill]** (hard negatives: **[fill]**)
- Ablations: −Tavily F1 **[fill]**, −memory FPR **[fill]**, Lightning-only F1 **[fill]**, rules-only **[fill]**
- Cost: **$[fill] per 1,000 messages** at list prices; median latency **[fill] s**
- MalayMMLU 500-question subset: Lightning **[fill]%**, Super **[fill]%** (reported as tool feedback)

## Challenges we ran into

- Nebius removed NVIDIA's multimodal models (Nemotron 3 Nano Omni, Cosmos Reasoner) from Token Factory serverless on 31 Aug 2026, and Token Factory has no speech product, so voice notes became a documented next step rather than a feature. We treated it as a design input: Jaga spends its novelty on verification, memory and visible privacy.
- Nemotron is not in Token Factory's fine-tuning base-model list, so we did not fine-tune; we measured Malay capability instead.
- NemoClaw/OpenShell is an early preview — see FEEDBACK for every rough edge.

## Accomplishments that we're proud of

A complete loop a senior can use with zero setup; verdicts that cite the authority page; a memory design that fixes a documented gap in open personal agents; privacy enforced in code and policy; and numbers, not just a demo.

## What we learned

Verification beats classification for trust. Structured memory beats "the agent decides what to remember". The cheapest Nemotron tier on every message plus the strongest on the rare hard case is both cheaper and more accurate than one model for everything — and we can show the curve.

## What's next for Jaga

Voice notes when an NVIDIA speech/omni model returns to Token Factory serverless (or Cosmos Reason 2 on a Nebius Serverless Endpoint for screenshots); a Jetson Orin Nano at the family home running Nemotron Bolt for fully local triage; NSRC 997 hand-off; pilot with a KL residents' association.

---

**Demo URL:** `<DEMO_URL>` (test credentials in the private notes field)
**Video:** `<VIDEO_URL>`
**Repo:** `<REPO_URL>` (MIT)

### Feedback on Nebius Token Factory, AI Cloud and NVIDIA tools
See `docs/FEEDBACK.md` in the repo — paste its contents into the Devpost feedback field.
