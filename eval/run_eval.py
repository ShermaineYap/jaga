"""ScamBench-MY evaluation harness.

Runs the Jaga pipeline over eval/data/scambench_my.jsonl under several
configurations and reports, per configuration:
  * precision / recall / F1 on scam-vs-legit
  * per-family recall and per-language F1
  * FALSE-POSITIVE RATE on legitimate messages (the number that decides whether
    a family keeps using it), split into easy vs hard negatives
  * median latency and USD cost per 1,000 messages (from real Token Factory usage)

Configurations (ablations):
  fast        Lightning only (triage → verdict, thinking off)
  plan        Lightning + Super (plan, verify, verdict)
  full        + Ultra escalation on hard cases
  no_tavily   full, but verification tools disabled
  no_ledger   full, but household memory disabled
  rules       mock heuristics only (transparent baseline, no model)

Usage:
  python eval/run_eval.py --configs fast,plan,full,no_tavily,no_ledger --limit 300
  python eval/run_eval.py --mock              # offline, uses heuristics for every config
  python eval/run_eval.py --batch-prepare     # write a Token Factory Batch API file for the triage step
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaga import config  # noqa: E402
from jaga.config import RunOptions  # noqa: E402
from jaga.ledger import Ledger  # noqa: E402
from jaga.llm import TokenFactory  # noqa: E402
from jaga.pipeline import Jaga  # noqa: E402
from jaga.tavily_tools import Tavily  # noqa: E402

DATA = ROOT / "eval" / "data" / "scambench_my.jsonl"
OUT = ROOT / "eval" / "results"

CONFIGS = {
    "rules":     dict(tier="fast", use_tavily=False, use_ledger=False, mock=True),
    "fast":      dict(tier="fast", use_tavily=False, use_ledger=True),
    "plan":      dict(tier="plan", use_tavily=True, use_ledger=True),
    "full":      dict(tier="full", use_tavily=True, use_ledger=True),
    "no_tavily": dict(tier="full", use_tavily=False, use_ledger=True),
    "no_ledger": dict(tier="full", use_tavily=True, use_ledger=False),
}

# Trusted contacts seeded into the eval household so hard negatives from known
# agents can be resolved by memory (mirrors the demo household).
SEED_CONTACTS = [
    ("Encik Faizal", "012-345 6789", "Prudential", "insurance agent"),
    ("Siti", "013-222 3344", "", "daughter"),
    ("Dr Lim", "03-7777 8888", "Klinik Lim", "family doctor"),
    ("Puan Rohani", "019-555 6677", "Public Mutual", "unit trust agent"),
]


def load(limit: int | None, data: Path = DATA) -> list[dict]:
    rows = [json.loads(l) for l in data.read_text().splitlines() if l.strip()]
    return rows[:limit] if limit else rows


def is_flagged(risk: str) -> bool:
    return risk in ("high", "medium")


def metrics(rows: list[dict], preds: list[dict]) -> dict:
    tp = fp = fn = tn = 0
    fam_tot, fam_hit = defaultdict(int), defaultdict(int)
    lang = defaultdict(lambda: [0, 0, 0, 0])  # tp fp fn tn
    hard_fp = hard_n = easy_fp = easy_n = 0
    fam_correct = 0
    for r, p in zip(rows, preds):
        flagged = is_flagged(p["risk"])
        scam = r["label"] == "scam"
        L = lang[r["lang"]]
        if scam and flagged:
            tp += 1; L[0] += 1; fam_hit[r["family"]] += 1
        elif not scam and flagged:
            fp += 1; L[1] += 1
        elif scam and not flagged:
            fn += 1; L[2] += 1
        else:
            tn += 1; L[3] += 1
        if scam:
            fam_tot[r["family"]] += 1
            if p["family"] == r["family"]:
                fam_correct += 1
        else:
            if r.get("hard_negative"):
                hard_n += 1; hard_fp += flagged
            else:
                easy_n += 1; easy_fp += flagged
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0

    def lf1(v):
        p_ = v[0] / (v[0] + v[1]) if v[0] + v[1] else 0
        r_ = v[0] / (v[0] + v[2]) if v[0] + v[2] else 0
        return round(2 * p_ * r_ / (p_ + r_), 3) if p_ + r_ else 0.0

    lat = [p["latency_ms"] for p in preds]
    cost = sum(p["cost_usd"] for p in preds)
    return {
        "n": len(rows), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3),
        "false_positive_rate": round(fp / (fp + tn), 3) if fp + tn else 0.0,
        "fpr_hard_negatives": round(hard_fp / hard_n, 3) if hard_n else None,
        "fpr_easy_negatives": round(easy_fp / easy_n, 3) if easy_n else None,
        "family_accuracy_on_scams": round(fam_correct / max(1, sum(fam_tot.values())), 3),
        "recall_by_family": {f: round(fam_hit[f] / fam_tot[f], 3) for f in sorted(fam_tot)},
        "f1_by_language": {k: lf1(v) for k, v in sorted(lang.items())},
        "median_latency_ms": int(statistics.median(lat)) if lat else 0,
        "p90_latency_ms": int(sorted(lat)[int(0.9 * len(lat)) - 1]) if lat else 0,
        "cost_usd_total": round(cost, 4),
        "cost_usd_per_1000": round(cost / max(1, len(rows)) * 1000, 2),
        "escalations": sum(1 for p in preds if p.get("escalated")),
        "tool_hits": sum(1 for p in preds if p.get("tool_hit")),
        "tool_errors": sum(p.get("tool_errors", 0) for p in preds),
    }


def run_config(name: str, rows: list[dict], force_mock: bool) -> tuple[dict, list[dict]]:
    cfg = dict(CONFIGS[name])
    mock = force_mock or cfg.pop("mock", False)
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False).name
    ledger = Ledger(tmp)
    hh = "eval-household"
    ledger.ensure_household(hh)
    for n, ph, org, rel in SEED_CONTACTS:
        ledger.add_contact(hh, n, ph, org, rel)
    jaga = Jaga(TokenFactory(mock=mock), Tavily(mock=mock or not config.TAVILY_API_KEY, db_path=tmp), ledger)
    from concurrent.futures import ThreadPoolExecutor
    t0 = time.time()
    done = [0]

    def one(r):
        opts = RunOptions(tier=cfg["tier"], use_tavily=cfg["use_tavily"], use_ledger=cfg["use_ledger"], household_id=hh, notify=False)
        for attempt in range(3):
            try:
                t_case = time.time()
                res = jaga.run_case(r["text"], opts, channel=r.get("channel", "whatsapp"))
                out = {"id": r["id"], "risk": res.verdict.risk, "family": res.verdict.family, "latency_ms": res.latency_ms,
                       "cost_usd": res.cost_usd, "escalated": res.escalation is not None,
                       "tool_hit": any(e.kind in ("official_alert", "news") and e.source_url for e in res.verdict.evidence),
                       "models": res.models_used,
                       "tool_errors": sum(1 for e in jaga.ledger.audit_events(hh, 60)
                                          if e["activity"] == "tool.call" and e["outcome"] == "error" and e["ts"] >= t_case)}
                break
            except Exception as e:  # noqa: BLE001
                out = {"id": r["id"], "risk": "unknown", "family": "legit", "latency_ms": 0, "cost_usd": 0.0, "error": str(e)[:300]}
                time.sleep(3 * (attempt + 1))
        done[0] += 1
        if done[0] % 25 == 0:
            print(f"  [{name}] {done[0]}/{len(rows)}  ({time.time()-t0:.0f}s)", flush=True)
        return out

    workers = 1 if mock else int(os.environ.get("JAGA_EVAL_WORKERS", "6"))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        preds = list(ex.map(one, rows))
    m = metrics(rows, preds)
    m["config"] = name
    m["mock"] = mock
    m["errors"] = sum(1 for p in preds if p.get("error"))
    os.unlink(tmp)
    return m, preds


def to_markdown(results: list[dict]) -> str:
    cols = ["config", "f1", "precision", "recall", "false_positive_rate", "fpr_hard_negatives",
            "family_accuracy_on_scams", "median_latency_ms", "cost_usd_per_1000", "escalations", "tool_hits", "mock"]
    head = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    body = "".join("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |\n" for r in results)
    langs = "\n\n**F1 by language**\n\n| config | " + " | ".join(sorted(results[0]["f1_by_language"])) + " |\n|---|" + "---|" * len(results[0]["f1_by_language"]) + "\n"
    langs += "".join("| " + r["config"] + " | " + " | ".join(str(r["f1_by_language"].get(k, "")) for k in sorted(results[0]["f1_by_language"])) + " |\n" for r in results)
    fams = "\n\n**Recall by scam family**\n\n| config | " + " | ".join(sorted(results[0]["recall_by_family"])) + " |\n|---|" + "---|" * len(results[0]["recall_by_family"]) + "\n"
    fams += "".join("| " + r["config"] + " | " + " | ".join(str(r["recall_by_family"].get(k, "")) for k in sorted(results[0]["recall_by_family"])) + " |\n" for r in results)
    return head + body + langs + fams


def batch_prepare(rows: list[dict]) -> Path:
    """Write a Token Factory Batch API input file (one chat-completion request per
    line) for the triage step. Submit with scripts/batch_submit.py."""
    from jaga.prompts import TRIAGE_SYSTEM, TRIAGE_USER
    from jaga.schemas import Triage
    out = OUT / "batch_triage_input.jsonl"
    with out.open("w") as f:
        for r in rows:
            f.write(json.dumps({"custom_id": r["id"], "method": "POST", "url": "/v1/chat/completions", "body": {
                "model": config.MODEL_FAST[0],
                "messages": [{"role": "system", "content": TRIAGE_SYSTEM},
                             {"role": "user", "content": TRIAGE_USER.format(channel=r.get("channel", "whatsapp"), text=r["text"])}],
                "response_format": {"type": "json_schema", "json_schema": {"name": "Triage", "schema": Triage.model_json_schema()}},
                "temperature": 0.1, "max_tokens": 1200,
                "chat_template_kwargs": {"enable_thinking": False}}}) + "\n")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", default="rules,fast,plan,full,no_tavily,no_ledger")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--mock", action="store_true", help="force heuristics for every config (offline)")
    ap.add_argument("--batch-prepare", action="store_true")
    ap.add_argument("--data", default=str(DATA), help="JSONL dataset (default ScamBench-MY)")
    ap.add_argument("--tag", default="", help="suffix for result files, e.g. 'memory'")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rows = load(args.limit, Path(args.data))
    if args.batch_prepare:
        print("wrote", batch_prepare(rows))
        return
    results, all_preds = [], {}
    for name in args.configs.split(","):
        print(f"== {name} ({len(rows)} messages)")
        m, preds = run_config(name, rows, args.mock)
        results.append(m)
        all_preds[name] = preds
        print(json.dumps({k: m[k] for k in ("f1", "precision", "recall", "false_positive_rate", "cost_usd_per_1000", "median_latency_ms")}))
    stamp = time.strftime("%Y%m%d-%H%M%S")
    sfx = f"_{args.tag}" if args.tag else ""
    (OUT / f"results_{stamp}{sfx}.json").write_text(json.dumps({"results": results, "predictions": all_preds}, indent=1))
    (OUT / f"latest{sfx}.json").write_text(json.dumps({"results": results, "predictions": all_preds}, indent=1))
    (OUT / f"RESULTS{sfx}.md").write_text(f"# ScamBench-MY results ({stamp})\n\nn = {len(rows)} messages. "
                                    f"mock={args.mock}\n\n" + to_markdown(results))
    print("\n" + to_markdown(results))
    print(f"\nwritten to {OUT}")


if __name__ == "__main__":
    main()
