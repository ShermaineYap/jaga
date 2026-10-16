# Jaga — 3-minute demo video (target 2:45, hard stop 2:55)

Record the voice-over in **your own voice** (judges discount AI voiceovers). Say "Nemotron",
"Nebius Token Factory" and "Tavily" out loud when they fire — the organisers said judges listen for it.

**Footage already recorded for you** (real Nemotron + Tavily, 1280×800):
`video_footage/01_rrj_pro_scam_caught.mp4`, `02_trusted_agent_cleared.mp4`,
`03_screenshot_phishing.mp4`, `04_memory_policy_audit.mp4`, chart `eval/results/chart_f1_fpr.png`.
**You record:** 0:00 intro on camera (phone is fine), and a 15-second phone screen recording of
forwarding a message to @Jaga_my_demo_bot and getting the card back (iPhone: Control Centre → Screen
Recording). Edit in CapCut / iMovie: cut the clips to the timings below.

| Time | On screen | Say (edit freely — keep it in your own words) |
|---|---|---|
| 0:00–0:12 | You on camera | "Hi, I'm Shermaine from APU in KL. This is Jaga — *jaga* means 'to guard'. It's a private scam guardian for my parents' generation." |
| 0:12–0:27 | Text on screen: **RM2.97 billion lost to online scams in Malaysia in 2025** · **1,916 seniors lost RM250 million in one year** | "Those scams arrive on a phone nobody else sees. So the guardian has to live on that phone — and it has to be private." |
| 0:27–0:42 | Phone recording: forward a message to @Jaga_my_demo_bot → card comes back | "Auntie forwards a suspicious message to Jaga on Telegram, and seconds later she gets an answer in Bahasa Malaysia." |
| 0:42–1:05 | `01_rrj_pro` — typing, "Checking…" overlay, verdict | "Under the hood: **Nemotron 3.5 Lightning on Nebius Token Factory** reads it and pulls out the scheme name — RRJ Pro — and the phone number. **Nemotron 3 Super**, reasoning on, decides what to verify, and **Tavily** searches only official sources: the Securities Commission, PDRM, Bank Negara." |
| 1:05–1:20 | `01_rrj_pro` — evidence card with SC link + quote (zoom on it) | "And here's the point: RRJ Pro was added to the SC Investor Alert List **yesterday**. No model's training data knows that. Jaga found the page and quotes it. Every piece of evidence is checked in code — the model can't invent a source." |
| 1:20–1:35 | `03_screenshot` — upload, verdict, visual cues | "Most seniors forward screenshots, so **Nemotron 3.5 Super VL** reads them — and it noticed on its own that 'Maybank Customer Care' was using a personal mobile number." |
| 1:35–1:50 | `02_trusted` — Faizal message → green, "known insurance agent in household memory" | "A guardian that cries wolf gets switched off. Mum's real insurance agent is in Jaga's household memory, so his reminder is cleared — with advice to call back on the saved number." |
| 1:50–2:15 | `eval/results/chart_f1_fpr.png` (full screen) | "We measured it on ScamBench-MY: 300 Malay, English and Manglish messages we labelled. Lightning alone catches [fill]% of scams but wrongly flags [fill]% of real messages. Adding Super's planning and Tavily verification brings false alarms down to [fill]%, at about [fill] US cents per thousand messages." |
| 2:15–2:35 | `04_memory_policy_audit` — policy, audit timeline | "Privacy is enforced, not promised: the family gets a summary, never the message. Every model call, search and notification is in an audit log they can read, export or delete. The private deployment runs as Hermes Agent inside **NVIDIA OpenShell** with a default-deny network." |
| 2:35–2:50 | You on camera | "Next: voice notes, a Jetson at home for fully local triage, and a pilot with a residents' association. Jaga — it verifies before it warns." |
| 2:50 | End card: `github.com/ShermaineYap/jaga` · "NVIDIA Nemotron · Nebius Token Factory · Tavily" | — |

### Checklist
- [ ] Replace every [fill] with the numbers in `eval/results/RESULTS.md` (or keep the sentence general)
- [ ] Mention OpenShell only as described in `hermes/OPENSHELL_RUN.md` (what actually ran)
- [ ] No copyrighted music (YouTube Audio Library is fine); no real people's phone numbers on screen
- [ ] Under 2:55; 1080p; upload to YouTube as **Public**; repo link in the description
- [ ] Two friends watch it cold: can they say what Jaga does in one sentence?
