# Jaga — 3-minute demo video script (target 2:45, hard stop 2:55)

Record in **your own voice** (judges penalise AI voiceovers). Screen-record the phone (Telegram)
and the dashboard; keep your face on camera for the open and close if you can. Say "Nemotron",
"Nebius Token Factory" and "Tavily" **out loud** as they fire — judges are told to listen for it.

| Time | On screen | Say |
|---|---|---|
| 0:00–0:08 | You on camera | "Hi, I'm Shermaine. This is Jaga — *jaga* means 'to guard' in Malay." |
| 0:08–0:22 | Phone: two incoming messages — 'Golden Harvest Capital, 30% a month, SC-licensed'; 'Pos Laju: parcel held by customs, pay RM48' | "Malaysians lost 2.97 billion ringgit to scams last year. In one year 1,916 elderly victims lost over 250 million. These messages land on a phone nobody else sees — so the guardian has to live there, and it has to be private." |
| 0:22–0:40 | Phone: Auntie forwards the investment message to Jaga. Dashboard case page opens. | "Auntie Aminah forwards it to Jaga. First, **Nemotron 3.5 Lightning on Nebius Token Factory** triages it in under a second — thinking off, strict JSON: investment pattern, a phone number, a scheme name, 'guaranteed'." |
| 0:40–1:00 | Dashboard: verification plan + Tavily calls appear | "Then **Nemotron 3 Super**, reasoning on, decides what to verify. It doesn't guess — it asks **Tavily** to search only the Securities Commission alert list and PDRM's Semak Mule for that scheme and that number." |
| 1:00–1:15 | Verdict card: red, BM headline, evidence link to SC page, 'Call NSRC 997' | "Here's the verdict — in Bahasa for Auntie, in English for her daughter — and every line cites the actual authority page. Jaga never says 'safe'. It says what it found, or that it found nothing." |
| 1:15–1:30 | Phone: daughter Siti's Telegram — summary only | "Siti gets a summary: risk, headline, what to do. Never the original message. That's policy enforced in code, not a promise in a prompt." |
| 1:30–1:45 | Phone: Mum's real insurance agent's message → green card with 'matches trusted contact Encik Faizal' | "And here's the part that matters for trust: Mum's real insurance agent messages about her premium. Jaga's **household ledger** knows him — so it clears it. A guardian that cries wolf gets switched off." |
| 1:45–2:10 | Chart: F1 + false-positive rate per tier and ablations | "We measured it. ScamBench-MY: 300 labelled Malay, English and Manglish messages. Full pipeline F1 **[fill]**, false positives on legitimate messages **[fill]** — and you can see what Tavily verification and household memory each contribute. The three-tier design costs **[fill] dollars per thousand messages**." |
| 2:10–2:30 | Policy page: OpenShell YAML + audit timeline | "Jaga runs as **Hermes Agent inside NVIDIA OpenShell**, onboarded with NemoClaw: default-deny network, three hosts, API keys never inside the sandbox, every action in an audit log the family can read, export or delete. Open models on independent infrastructure are what make a private guardian possible at all." |
| 2:30–2:45 | You on camera | "Next: voice notes when a speech model returns to Token Factory serverless, a Jetson at home for fully local triage, and a pilot with a KL residents' association. Jaga: it verifies before it warns." |
| 2:45 | End card: repo URL, 'Built on Nebius Token Factory · NVIDIA Nemotron · Tavily' | — |

## Recording checklist
- [ ] `python scripts/seed_demo.py` so the dashboard opens with the three cases
- [ ] Phone in light mode, text size large (seniors' phones look like that)
- [ ] Hide your real phone number / tokens; use the demo household
- [ ] Record each segment separately; cut to 2:45; no copyrighted music
- [ ] Export 1080p; upload to YouTube **public** (not unlisted); add the repo link in the description
- [ ] Two friends watch it cold: can they say what Jaga does in one sentence?
