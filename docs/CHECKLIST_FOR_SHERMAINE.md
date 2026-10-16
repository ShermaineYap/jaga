# What only you can do — in order

Everything in this repo runs offline today (`make test`, `make eval-mock`, `make demo`,
`make dashboard`). The steps below need your identity, your card, or your voice.
Deadline: **Oct 30, 10:00 PDT = Oct 31, 01:00 Malaysia time.** Submit on Oct 29.

## Day 1 — accounts (≈ 45 min)
1. **Nebius Token Factory**: sign up, add a card, redeem `NEBIUS-DEVPOST-GLOBAL26` via the promo form
   (link on the Devpost Resources page). Create an API key → `NEBIUS_API_KEY` in `.env`.
2. **Nebius Builders Program** (dev.nebius.com/builders): join for the second $25 + Tavily credit.
3. **Tavily**: create an account at tavily.com, apply code `BBDEVPOST` if the form accepts it →
   `TAVILY_API_KEY`.
4. **Telegram bot**: message @BotFather → `/newbot` → `TELEGRAM_BOT_TOKEN`. Create a second Telegram
   account (or use a friend's) to play the "daughter".
5. **Join the Nebius Discord** (link on Devpost Resources) — that is where billing/credit issues get fixed.
6. **GitHub**: create a public repo `jaga`, push this folder (`git init && git add -A && git commit
   -m "Jaga" && git push`). Confirm the MIT license shows in the repo's About box.
7. On Devpost: **Start a submission** now (you can edit until the deadline).

## Day 1 — ten-minute checks
```bash
pip install -r requirements.txt
python scripts/list_models.py     # do the three Nemotron IDs resolve? If not, fix .env
python scripts/malay_smoke.py     # does Nemotron handle BM? decides the demo language
python scripts/seed_demo.py       # three live cases
uvicorn jaga.dashboard.app:app --port 8000
```
Then run the full eval (≈ $1–3): `make eval && make charts`. Paste the numbers into
`README.md`, `docs/DEVPOST_SUBMISSION.md` and `docs/FEEDBACK.md` where it says `[fill]`.

## Days 2–8 — the OpenShell deployment (budget two days for friction)
- A Linux VM with Docker. Cheapest honest options: a Nebius AI Cloud CPU VM (needs the $25 AI
  Cloud top-up — then the README can say "runs end to end on Nebius"), or any small VPS, or WSL2.
- `bash hermes/setup_nemohermes.sh`. **Write down every error** in `docs/FEEDBACK.md` — that is
  the Most Valuable Feedback prize.
- If NemoClaw won't cooperate after two days: run `python -m jaga.bot` + the dashboard with
  `docker compose up -d`, and describe honestly in the README that the OpenShell layer is
  configured but was not the deployed path. Judges reward honesty over a broken claim.

## Days 9–12 — demo + polish
- Keep the dashboard reachable **until Dec 15** (judging). Put $5–10 of real balance on Token
  Factory for the judging window; credits may expire before then.
- Ask two or three seniors/family members to try it; put one real quote in the README.
- `python scripts/malaymmlu_subset.py --n 500` (needs `pip install datasets`).

## Day 13 — video
- Follow `docs/VIDEO_SCRIPT.md`. Your voice. Under 2:55. Public YouTube.
- Make a 30-second GIF of the forward → verdict → guardian summary for the README (`docs/demo.gif`).

## Day 14 — submit (Oct 29)
- Devpost: paste `docs/DEVPOST_SUBMISSION.md`; choose track **Personal AI**; paste `docs/FEEDBACK.md`
  into the feedback field; demo URL + test credentials in private notes; video link; repo link.
- Have two friends read the README and watch the video cold. Fix what confused them.
- Submit. Oct 30 is buffer only.
