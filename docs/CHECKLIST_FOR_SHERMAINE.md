# What's left — only the things that need you

Deadline: **Oct 30, 10:00 PDT = Oct 31, 01:00 Malaysia time.** Aim to submit on **Oct 29**.

Everything else is done: code on GitHub (14 tests), live demo on Render, Telegram bot live, 300-message
evaluation + 3× memory test on real Nemotron, OpenShell sandbox verified, Devpost draft filled up to the
Submit page (story, tags, links, 6 captioned images, 16 factual answers).

**Try these on the live demo / bot before recording:**
- `Salam Puan Aminah. Platform pelaburan RRJ Pro tawarkan pulangan 30% sebulan DIJAMIN. Modal minima RM5,000. WhatsApp 011-9999 0123.` → high, cites the SC alert list
- `Mak, Siti ni. Nombor baru 011-9999 0461, phone lama hilang. Tolong transfer RM900 ke akaun 5566778899001.` → high, "claims to be Siti but …"
- `Puan, ini Faizal dari Prudential. Premium polis puan jatuh tempo 20 Okt, boleh saya call esok pagi untuk sahkan? 012-345 6789` → low, known agent

## 1. Record the video (≈ 1–2 hours)
- Script: `docs/VIDEO_SCRIPT.md` (timings + lines, numbers already filled in).
- Footage already recorded for you: `NEBIUS X NVIDIA/video_footage/` (4 clips, real models).
- You record: a 10-second intro and outro on camera, and a 15-second phone screen recording of
  forwarding a message to **@Jaga_my_demo_bot** (use `video_footage/demo_scam_screenshot_to_forward.jpg`,
  or any real scam SMS you've received).
- Voice-over in **your own voice**. Under 2:55. Edit in CapCut or iMovie.
- Upload to YouTube as **Public**; put `https://github.com/ShermaineYap/jaga` in the description.

## 2. Finish the Devpost draft (≈ 10 minutes)
Open devpost.com → My projects → *Jaga: a scam guardian that verifies before it warns* → Edit.
- **Project details:** paste the YouTube link into *Demo video URL*.
- **Additional info** — these are yours to answer (I filled everything factual):
  - the three 1–10 ratings (Nemotron output quality; likelihood to recommend; experience vs other
    environments) — your honest opinion;
  - *Did you attend Builders & Brews?* (only if you went to the KL event on 12 Sep);
  - *level of learning* and *AI value for your career*;
  - the two declarations: you're at least 18, and not an employee/agent of Nebius, NVIDIA, Tavily or Devpost.
- **Submit page:** read the Official Rules, tick the terms box, click **Submit project**.
  You can still edit after submitting, until the deadline.

## 3. Keep the demo alive until Dec 15 (judging)
- Token Factory: $25 balance; the build and all evaluations used roughly $7 (the usage page lags by
  several hours). Check it once in December. A full re-run of the evaluation costs about $3.
- The free Render instance sleeps when idle; the first visit takes ~50 s. That's fine for judges.
- Render does **not** auto-deploy on push. After any code change: dashboard.render.com → jaga →
  **Manual Deploy → Deploy latest commit**.
- Tavily: 3,184 of 9,000 credits used on 16 Oct (≈ 5,800 left).

## 4. Housekeeping
- The GitHub access token `jaga-hackathon-push` (expires Nov 15) is no longer needed; you can
  revoke it at github.com/settings/personal-access-tokens.
- Optional: ask 2–3 seniors or family members to try the Telegram bot and add one real quote to the README.
