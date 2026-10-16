"""Central configuration for Jaga.

Everything that can change between now and the judging window (model IDs,
endpoints, prices) lives here and is overridable from the environment, so a
model rename on Token Factory is a config change, never a code change.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name)
    if not raw:
        return default
    return [x.strip() for x in raw.split(",") if x.strip()]


# --- Nebius Token Factory -------------------------------------------------
# Verify the base URL and model IDs on day one with:  python scripts/list_models.py
NEBIUS_API_KEY = _env("NEBIUS_API_KEY", "")
NEBIUS_BASE_URL = _env("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1")

# Three Nemotron tiers. Each role has an ordered fallback chain: if the first
# model ID is missing (404) or the account is paused (402), the next is tried.
MODEL_FAST = _env_list("JAGA_MODEL_FAST", [
    "nvidia/Nemotron-3_5-Lightning",
    "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
])
MODEL_PLAN = _env_list("JAGA_MODEL_PLAN", [
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/Nemotron-3_5-Lightning",
])
MODEL_ESCALATE = _env_list("JAGA_MODEL_ESCALATE", [
    "nvidia/Nemotron-3-Ultra-550b-a55b",
    "nvidia/nemotron-3-super-120b-a12b",
])

# Vision: reads forwarded screenshots (WhatsApp/SMS/email) into text + visual cues.
MODEL_VISION = _env_list("JAGA_MODEL_VISION", [
    "nvidia/Nemotron-3.5-Super-VL",
])

# USD per 1M tokens (input, output) — from Nebius pricing, Oct 2026. Used only
# for the cost report; update if pricing changes.
PRICES_PER_M = {
    "nvidia/Nemotron-3_5-Lightning": (0.06, 0.24),
    "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B": (0.06, 0.24),
    "nvidia/nemotron-3-super-120b-a12b": (0.30, 0.90),
    "nvidia/Nemotron-3.5-Super-VL": (0.30, 0.90),
    "nvidia/Nemotron-3-Ultra-550b-a55b": (1.00, 3.00),
}

# Client-side reasoning budget (max output tokens) for thinking-on calls.
PLAN_REASONING_BUDGET = int(_env("JAGA_PLAN_BUDGET", "2500"))
ESCALATE_REASONING_BUDGET = int(_env("JAGA_ESCALATE_BUDGET", "6000"))

# --- Tavily -----------------------------------------------------------------
TAVILY_API_KEY = _env("TAVILY_API_KEY", "")
TAVILY_BASE_URL = _env("TAVILY_BASE_URL", "https://api.tavily.com")

# Official Malaysian alert sources. Searches are restricted to these domains
# so a verdict can only ever cite an authority, never a random blog.
OFFICIAL_DOMAINS = _env_list("JAGA_OFFICIAL_DOMAINS", [
    "sc.com.my",            # Securities Commission investor alert list
    "semakmule.rmp.gov.my",  # PDRM Semak Mule (mule accounts / phone numbers)
    "ccid.rmp.gov.my",      # PDRM Commercial Crime Investigation Department
    "bnm.gov.my",           # Bank Negara Malaysia consumer alerts
    "mcmc.gov.my",          # MCMC
    "nsrc.gov.my",          # National Scam Response Centre (997)
])
NEWS_DOMAINS = _env_list("JAGA_NEWS_DOMAINS", [
    "bernama.com", "thestar.com.my", "malaymail.com", "nst.com.my",
    "harianmetro.com.my", "bharian.com.my", "freemalaysiatoday.com",
])
# Pages the nightly cron maps + extracts into the local alert cache.
ALERT_LIST_URLS = _env_list("JAGA_ALERT_LIST_URLS", [
    "https://www.sc.com.my/investor-alert-list",
    "https://www.bnm.gov.my/financial-consumer-alert-list",
])
MAX_TOOL_ROUNDS = int(_env("JAGA_MAX_TOOL_ROUNDS", "3"))

# --- Telegram ---------------------------------------------------------------
TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN", "")

# --- Runtime ----------------------------------------------------------------
# Mock mode runs the whole system with deterministic stand-ins for Nemotron and
# Tavily. It exists so tests, the dashboard and the eval harness run offline and
# so the demo has a recorded-run fallback if credits are exhausted.
MOCK = _env("JAGA_MOCK", "0") == "1" or not NEBIUS_API_KEY
DB_PATH = Path(_env("JAGA_DB", str(ROOT / "data" / "jaga.sqlite3")))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DEMO_HOUSEHOLD = _env("JAGA_DEMO_HOUSEHOLD", "demo-household")
# "openshell" when running inside the NVIDIA OpenShell sandbox (hermes/), else "hosted".
DEPLOYMENT = _env("JAGA_DEPLOYMENT", "hosted")
DASHBOARD_RATE_LIMIT_PER_MIN = int(_env("JAGA_RATE_LIMIT", "10"))


@dataclass
class RunOptions:
    """Per-case switches. The eval harness flips these for ablations."""
    use_tavily: bool = True
    use_ledger: bool = True
    # Default tier chosen from ScamBench-MY: "plan" (Lightning triage + Super plan/verdict +
    # Tavily + memory) matched "full" (+ Nemotron 3 Ultra second opinion) on accuracy at
    # ~15% lower cost, so Ultra is opt-in via JAGA_TIER=full.
    tier: str = field(default_factory=lambda: os.environ.get("JAGA_TIER", "plan"))  # "fast" | "plan" | "full"
    household_id: str = DEMO_HOUSEHOLD
    notify: bool = True
    extra: dict = field(default_factory=dict)


SCAM_FAMILIES = [
    "impersonation",   # Macau scam: police / court / LHDN / bank officer
    "investment",      # guaranteed returns, gold, forex, crypto, "SC-licensed"
    "love",            # romance / parcel-gift / sugar
    "mule",            # "sewa akaun", rent your bank account / SIM
    "parcel",          # customs / Pos Laju / J&T holding fee
    "phishing_otp",    # TAC / OTP / fake bank links
    "legit",
]
