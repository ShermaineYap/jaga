"""Honest Bahasa Malaysia capability number for the feedback section.

Runs a 500-question subset of MalayMMLU (YTL AI Labs, Hugging Face
`UMxYTL-AI-Labs/MalayMMLU`) through the fast and plan tiers with thinking off
and reports accuracy per subject group. Nemotron's documented languages do not
include Malay, so this is exactly the kind of feedback the organizers asked for.

  pip install datasets
  python scripts/malaymmlu_subset.py --n 500
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pydantic import BaseModel  # noqa: E402

from jaga.llm import TokenFactory, Usage  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "eval" / "results"


class Choice(BaseModel):
    answer: str  # "A" | "B" | "C" | "D" | "E"


SYSTEM = "Jawab soalan aneka pilihan ini. Balas dengan huruf pilihan sahaja dalam JSON: {\"answer\": \"A\"}."


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    try:
        from datasets import load_dataset
    except ImportError:
        raise SystemExit("pip install datasets")
    ds = load_dataset("UMxYTL-AI-Labs/MalayMMLU", split="test")
    rows = list(ds)
    random.Random(args.seed).shuffle(rows)
    rows = rows[: args.n]
    tf = TokenFactory()
    if tf.mock:
        raise SystemExit("needs a real NEBIUS_API_KEY")
    report = {}
    for role in ("fast", "plan"):
        usage = Usage()
        correct, by_cat = 0, defaultdict(lambda: [0, 0])
        for r in rows:
            opts = "\n".join(f"{k}. {v}" for k, v in zip("ABCDE", r.get("choices") or [r.get(f"option_{c}") for c in "ABCDE" if r.get(f"option_{c}")]))
            q = f"{r['question']}\n{opts}"
            try:
                a = tf.structured(role, SYSTEM, q, Choice, thinking=False, usage=usage).answer.strip().upper()[:1]
            except Exception:  # noqa: BLE001
                a = ""
            gold = str(r.get("answer") or r.get("key") or "").strip().upper()[:1]
            cat = r.get("category") or r.get("subject") or "all"
            by_cat[cat][1] += 1
            if a == gold:
                correct += 1
                by_cat[cat][0] += 1
        report[role] = {"accuracy": round(correct / len(rows), 3), "n": len(rows),
                        "by_category": {c: round(v[0] / v[1], 3) for c, v in by_cat.items()},
                        "cost_usd": round(usage.cost_usd, 4), "model": usage.models_used.get(role)}
        print(role, json.dumps(report[role]))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "malaymmlu_subset.json").write_text(json.dumps(report, indent=1))
    print("wrote", OUT / "malaymmlu_subset.json")


if __name__ == "__main__":
    main()
