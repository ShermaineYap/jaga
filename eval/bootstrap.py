"""95% bootstrap confidence intervals for F1 and false-positive rate, plus paired
comparisons between configurations, from eval/results/latest*.json.

  python eval/bootstrap.py                 # ScamBench-MY
  python eval/bootstrap.py --tag memory    # targeted memory set

Paired bootstrap: the same resampled message indices are used for every config, so
"full vs no_tavily" compares the two systems on identical message sets.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "eval" / "results"


def f1_fpr(labels, flags):
    tp = sum(1 for l, f in zip(labels, flags) if l and f)
    fp = sum(1 for l, f in zip(labels, flags) if not l and f)
    fn = sum(1 for l, f in zip(labels, flags) if l and not f)
    tn = sum(1 for l, f in zip(labels, flags) if not l and not f)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    return f1, fpr


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="")
    ap.add_argument("--data", default=str(ROOT / "eval" / "data" / "scambench_my.jsonl"))
    ap.add_argument("--n", type=int, default=2000)
    args = ap.parse_args()
    sfx = f"_{args.tag}" if args.tag else ""
    res = json.loads((OUT / f"latest{sfx}.json").read_text())
    rows = {json.loads(l)["id"]: json.loads(l) for l in Path(args.data).read_text().splitlines() if l.strip()}
    preds = res["predictions"]
    configs = [r["config"] for r in res["results"]]
    ids = [p["id"] for p in preds[configs[0]]]
    labels = [rows[i]["label"] == "scam" for i in ids]
    flags = {c: [p["risk"] in ("high", "medium") for p in preds[c]] for c in configs}
    rng = random.Random(7)
    boots = {c: [] for c in configs}
    idx_sets = [[rng.randrange(len(ids)) for _ in ids] for _ in range(args.n)]
    for idx in idx_sets:
        lb = [labels[i] for i in idx]
        for c in configs:
            boots[c].append(f1_fpr(lb, [flags[c][i] for i in idx]))

    def ci(vals):
        v = sorted(vals)
        return v[int(0.025 * len(v))], v[int(0.975 * len(v)) - 1]

    lines = [f"# Confidence intervals{(' — ' + args.tag) if args.tag else ''}\n",
             f"Paired bootstrap, {args.n} resamples of n = {len(ids)} messages.\n",
             "| config | F1 | 95% CI | false-positive rate | 95% CI |", "|---|---|---|---|---|"]
    for c in configs:
        f1, fpr = f1_fpr(labels, flags[c])
        (a, b), (x, y) = ci([t[0] for t in boots[c]]), ci([t[1] for t in boots[c]])
        lines.append(f"| {c} | {f1:.3f} | {a:.3f}–{b:.3f} | {fpr:.1%} | {x:.1%}–{y:.1%} |")
    pairs = [("plan", "fast"), ("plan", "rules"), ("full", "plan"), ("full", "no_tavily"), ("full", "no_ledger")]
    lines += ["", "**Paired differences (A − B).** Significant if the 95% CI excludes 0.", "",
              "| comparison | ΔF1 | 95% CI | ΔFPR | 95% CI |", "|---|---|---|---|---|"]
    for a_, b_ in pairs:
        if a_ in boots and b_ in boots:
            d1 = [boots[a_][k][0] - boots[b_][k][0] for k in range(args.n)]
            d2 = [boots[a_][k][1] - boots[b_][k][1] for k in range(args.n)]
            f_a, r_a = f1_fpr(labels, flags[a_]); f_b, r_b = f1_fpr(labels, flags[b_])
            (l1, h1), (l2, h2) = ci(d1), ci(d2)
            sig1 = " ✱" if l1 > 0 or h1 < 0 else ""
            sig2 = " ✱" if l2 > 0 or h2 < 0 else ""
            lines.append(f"| {a_} − {b_} | {f_a - f_b:+.3f}{sig1} | {l1:+.3f}…{h1:+.3f} | {r_a - r_b:+.1%}{sig2} | {l2:+.1%}…{h2:+.1%} |")
    text = "\n".join(lines) + "\n"
    (OUT / f"CI{sfx}.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
