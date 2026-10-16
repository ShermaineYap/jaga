## Inspiration

Malaysians lost **RM2.97 billion** to online fraud in 2025, and in a single year **1,916 seniors lost over RM250 million**. The scam doesn't arrive through a bank or a website — it arrives as a WhatsApp or SMS on a phone that nobody else sees, often of someone living alone. I wanted a guardian that lives exactly there, that is genuinely private, and that — unlike a chatbot — **checks before it speaks**.

## What it does

A senior (or their adult child) forwards a suspicious message **or screenshot** to Jaga on Telegram. Jaga:

1. **Reads it.** Nemotron 3.5 Super VL transcribes screenshots and notes visual red flags (it spotted "Maybank Customer Care" on a personal +60 11 number unprompted). Nemotron 3.5 Lightning triages every message — scam family, scheme names, phones, links, accounts, urgency cues — with thinking off and a strict JSON schema.
2. **Remembers the household.** A structured ledger knows Mum's real insurance agent and her daughter's real number. Trust is earned by a *saved phone number*, never a typed name.
3. **Plans what to verify.** Nemotron 3 Super, reasoning on with a budget, decides which entity to check where.
4. **Verifies with Tavily** — searches restricted to the Securities Commission, PDRM, Bank Negara, MCMC and NSRC — and **code confirms the entity is literally on the page** before anything is cited.
5. **Answers** in Bahasa Malaysia and English, with the authority page and the exact sentence it found — or says plainly that nothing was found. It never says "safe", and always points high-risk cases to **NSRC 997**.
6. **Tells the family a summary, never the message**, and writes everything to an audit timeline they can read, export or delete.

**The moment that sums it up:** on 15 October 2026 the SC added *"RRJ Pro"* to its Investor Alert List. The next day a message pitching "RRJ Pro, 30% a month, guaranteed" was forwarded to Jaga, and it answered *"Waspada! RRJ Pro dalam senarai amaran SC"*, quoting the SC page. No model's training data contains that fact; a verifying agent finds it.

## How I built it

- **Nebius Token Factory** serves four NVIDIA Nemotron models through one OpenAI-compatible client: **3.5 Lightning** (triage), **3 Super** (planning + verdict), **3.5 Super VL** (screenshots), **3 Ultra** (optional second opinion). Every call uses JSON-schema structured output and `chat_template_kwargs.enable_thinking`, with fallback chains and cost accounting.
- **Tavily** search with `include_domains` + `include_raw_content`, news search, extract, and a nightly map→extract cache of the alert lists; a 24-hour response cache keeps credits low.
- **NVIDIA OpenShell 0.1.4:** Jaga's pipeline ran inside an OpenShell sandbox with a **default-deny egress policy** (only Token Factory, Tavily, Telegram). The Nebius and Tavily keys stay in the gateway — inside the sandbox they are `openshell:resolve:env:…` placeholders, `example.com` is refused, and the OCSF log shows each allowed call matched to its provider policy.
- Python, FastAPI dashboard, SQLite ledger, Telegram Bot API, deployed on Render; 11 tests; Playwright for the demo recordings.

## Results

**ScamBench-MY** — 300 hand-written messages (150 scams across 6 families, 150 legitimate including 52 look-alike "hard negatives"; 40% Bahasa Malaysia, 35% English, 25% Manglish), all run live on Token Factory:

| | F1 | Scams caught | False alarms | USD / 1k msgs |
|---|---|---|---|---|
| Keyword rules | 0.763 | 76.0% | 23.3% | — |
| Lightning only | 0.892 | 98.7% | 22.7% | $0.18 |
| **Lightning + Super + Tavily + memory (default)** | **0.946** | **98.7%** | **10.0%** | **$2.18** |
| … + Ultra second opinion | 0.936 | 97.3% | 10.7% | $2.51 |

Super's planning and verdict **halve false alarms** versus Lightning alone (significant on a paired bootstrap). Ultra added no measurable accuracy at +15% cost, so it's opt-in.

**Memory test** (10 genuine messages from saved contacts + 10 impersonations of the same people from new numbers): with memory, **10/10 impersonations caught and 0/10 genuine messages flagged**; without memory, 3/10 genuine messages were flagged.

## Challenges I ran into

Live testing found bugs a demo would have hidden — each is now fixed in code and most have a test:
- Nemotron's guided decoding **silently skipped optional schema fields**, so triage returned no entities and nothing got verified. Fix: every field `required`, lists bounded.
- The verdict model once **cited a real Bank Negara page for a phone number that isn't on it**. Fix: web evidence is rebuilt only from deterministic tool hits.
- Memory originally trusted a contact's **name**, which cleared "Mum, it's Siti, new number". Fix: trust only the saved number; a saved name from a new number is a red flag.
- Nemotron 3 Nano Omni left serverless on 31 Aug, but Nemotron 3.5 Super VL arrived — screenshots made it in; voice notes didn't (no speech model on Token Factory yet).

## Accomplishments that I'm proud of

A complete loop a senior can use with zero setup; citations that are verified, not generated; a measured, honest evaluation including results that *didn't* favour my design; and the privacy story running for real inside NVIDIA OpenShell rather than on a slide.

## What I learned

Verification beats classification for trust. Putting a stronger model on the judgment step halved false alarms compared with the cheap model alone, at a cost a household would never notice — and the bigger model on top (Ultra) added nothing measurable. You only know these things if you measure them. And "the model will cite its sources" is not a safety property until code checks the source.

## What's next for Jaga

Voice notes when a speech model lands on Token Factory; running the full Hermes Agent onboarding inside OpenShell once NemoClaw is published; a Jetson at home for fully local triage; NSRC 997 hand-off; and a pilot with a Kuala Lumpur residents' association.

**Try it:** https://jaga-q6pu.onrender.com · Telegram [@Jaga_my_demo_bot](https://t.me/Jaga_my_demo_bot) · Code (MIT): https://github.com/ShermaineYap/jaga
