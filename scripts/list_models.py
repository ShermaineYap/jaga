"""Day-one check: which Nemotron model IDs exist on Token Factory right now, and
do the configured chains resolve?   python scripts/list_models.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from openai import OpenAI  # noqa: E402

from jaga import config  # noqa: E402

if not config.NEBIUS_API_KEY:
    raise SystemExit("Set NEBIUS_API_KEY in .env first")

client = OpenAI(api_key=config.NEBIUS_API_KEY, base_url=config.NEBIUS_BASE_URL)
models = client.models.list().data
ids = sorted(m.id for m in models)
print(f"{len(ids)} models on {config.NEBIUS_BASE_URL}\n")
nv = [i for i in ids if i.lower().startswith("nvidia/")]
print("NVIDIA models:")
for i in nv:
    print("  ", i)
print("\nConfigured chains:")
for role, chain in {"fast": config.MODEL_FAST, "plan": config.MODEL_PLAN, "escalate": config.MODEL_ESCALATE}.items():
    ok = next((m for m in chain if m in ids), None)
    print(f"  {role:9s} -> {ok or 'NONE OF ' + str(chain)}")
print("\nIf a chain shows NONE, copy the correct ID from the NVIDIA list into .env (JAGA_MODEL_FAST etc.).")
