#!/usr/bin/env bash
# Onboard Jaga into Hermes Agent inside NVIDIA OpenShell via NemoClaw.
# Tested shape as of Oct 2026 (NemoClaw early preview) — expect rough edges;
# log every one in docs/FEEDBACK.md, that is part of the submission.
#
# Prereqs: Linux VM with Docker (a small Nebius AI Cloud CPU VM, or any VPS),
#          NEBIUS_API_KEY, TAVILY_API_KEY, TELEGRAM_BOT_TOKEN exported.
set -euo pipefail

echo "== 1. NemoClaw + OpenShell"
# Install per https://docs.nvidia.com/nemoclaw/  (CLI name: nemohermes for the Hermes path)
command -v nemohermes >/dev/null || { echo "install nemoclaw/nemohermes first (see NVIDIA docs)"; exit 1; }
command -v openshell  >/dev/null || { echo "install openshell first (github.com/NVIDIA/OpenShell)"; exit 1; }

echo "== 2. Onboard Hermes Agent into a sandbox named 'jaga'"
nemohermes onboard --name jaga --yes

echo "== 3. Route inference to Nebius Token Factory (key stays outside the sandbox)"
nemohermes inference set \
  --provider openai-compatible \
  --base-url "https://api.tokenfactory.nebius.com/v1" \
  --api-key "$NEBIUS_API_KEY" \
  --model "nvidia/nemotron-3-super-120b-a12b"

echo "== 4. Apply the default-deny network policy"
openshell policy apply hermes/openshell-policy.yaml --sandbox jaga

echo "== 5. Install the Jaga skill + tools into Hermes"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
mkdir -p "$HERMES_HOME/skills/jaga_case_protocol" "$HERMES_HOME/tools"
cp hermes/SKILL.md "$HERMES_HOME/skills/jaga_case_protocol/SKILL.md"
cp hermes/jaga_tools.py "$HERMES_HOME/tools/jaga_tools.py"

echo "== 6. Telegram gateway + cron"
hermes gateway add telegram --token "$TELEGRAM_BOT_TOKEN" || true
hermes cron add "0 3 * * *" "jaga_refresh_alert_cache" || true
hermes cron add "0 9 * * 1" "jaga_weekly_digest" || true

echo "== 7. Start"
nemohermes start jaga
echo "Jaga is running inside OpenShell. Dashboard: uvicorn jaga.dashboard.app:app --port 8000"
