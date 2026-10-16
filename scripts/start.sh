#!/usr/bin/env sh
# Container entrypoint for hosted deployments (Hugging Face Spaces / Render / any Docker host).
# Seeds the demo household on a fresh disk, starts the Telegram gateway if a token is set,
# then serves the dashboard on $PORT (default 7860 for HF Spaces).
set -e
mkdir -p "$(dirname "${JAGA_DB:-/app/data/jaga.sqlite3}")"
python scripts/seed_demo.py || echo "seed skipped (credits or network) — dashboard still starts"
if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
  python -m jaga.bot &
fi
exec uvicorn jaga.dashboard.app:app --host 0.0.0.0 --port "${PORT:-7860}"
