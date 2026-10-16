"""Render the two charts used in the README and the demo video from
eval/results/latest.json.

  python eval/charts.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "eval" / "results"
INK, MUTED, LINE = "#1f1a14", "#6b6257", "#e8dfd2"
PALETTE = {"rules": "#9a9188", "fast": "#5b8def", "plan": "#0f6e56", "full": "#5f8f80", "no_tavily": "#c9a46a", "no_ledger": "#c98b86"}
LABELS = {"rules": "keyword\nrules", "fast": "Lightning\nonly", "plan": "DEFAULT\nLightning\n+ Super", "full": "default\n+ Ultra",
          "no_tavily": "+ Ultra\n− Tavily", "no_ledger": "+ Ultra\n− memory"}


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(LINE)
    ax.tick_params(colors=MUTED, labelsize=10)
    ax.yaxis.grid(True, color=LINE, linewidth=0.8)
    ax.set_axisbelow(True)


def main() -> None:
    data = json.loads((OUT / "latest.json").read_text())
    res = data["results"]
    names = [r["config"] for r in res]
    x = range(len(names))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), dpi=160)
    ax = axes[0]
    ax.bar(x, [r["f1"] for r in res], color=[PALETTE.get(n, "#888") for n in names], width=0.62)
    for i, r in enumerate(res):
        ax.text(i, r["f1"] + 0.015, f"{r['f1']:.2f}", ha="center", color=INK, fontsize=10, fontweight="bold")
    ax.set_ylim(0, 1.08)
    ax.set_xticks(list(x), [LABELS.get(n, n) for n in names])
    ax.set_title("Scam detection F1 (ScamBench-MY, n=%d)" % res[0]["n"], loc="left", color=INK, fontsize=12, fontweight="bold")
    style(ax)

    ax = axes[1]
    fpr = [r["false_positive_rate"] for r in res]
    hard = [r.get("fpr_hard_negatives") or 0 for r in res]
    w = 0.38
    ax.bar([i - w / 2 for i in x], fpr, width=w, color=[PALETTE.get(n, "#888") for n in names], label="all legit messages")
    ax.bar([i + w / 2 for i in x], hard, width=w, color=[PALETTE.get(n, "#888") for n in names], alpha=0.45, hatch="//", label="hard negatives")
    for i in x:
        ax.text(i - w / 2, fpr[i] + 0.01, f"{fpr[i]:.0%}", ha="center", fontsize=9, color=INK)
        ax.text(i + w / 2, hard[i] + 0.01, f"{hard[i]:.0%}", ha="center", fontsize=9, color=MUTED)
    ax.set_ylim(0, max(0.3, max(fpr + hard) + 0.08))
    ax.set_xticks(list(x), [LABELS.get(n, n) for n in names])
    ax.set_title("False-positive rate on legitimate messages (lower is better)", loc="left", color=INK, fontsize=12, fontweight="bold")
    ax.legend(frameon=False, fontsize=9, loc="upper center", ncol=2, bbox_to_anchor=(0.5, -0.26))
    style(ax)
    if all(r.get("mock") for r in res):
        fig.text(0.5, -0.04, "OFFLINE BASELINE: every config ran on the deterministic stand-ins (JAGA_MOCK=1). Re-run `make eval` with Token Factory keys for Nemotron numbers.",
                 ha="center", fontsize=9, color="#b3261e")
    fig.tight_layout()
    fig.savefig(OUT / "chart_f1_fpr.png", bbox_inches="tight", facecolor="white")

    fig, ax = plt.subplots(figsize=(6.5, 4), dpi=160)
    cost = [r["cost_usd_per_1000"] for r in res]
    lat = [r["median_latency_ms"] / 1000 for r in res]
    for i, n in enumerate(names):
        ax.scatter(cost[i], lat[i], s=90 + 400 * res[i]["f1"], color=PALETTE.get(n, "#888"), alpha=0.9, edgecolor="white")
        ax.annotate(f"{n}\nF1 {res[i]['f1']:.2f}", (cost[i], lat[i]), textcoords="offset points", xytext=(8, 6), fontsize=9, color=INK)
    ax.set_xlabel("USD per 1,000 messages (Token Factory list prices)", color=MUTED)
    ax.set_ylabel("median latency (s)", color=MUTED)
    ax.set_title("Cost vs latency per tier (bubble size = F1)", loc="left", color=INK, fontsize=12, fontweight="bold")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT / "chart_cost_latency.png", bbox_inches="tight", facecolor="white")
    print("wrote", OUT / "chart_f1_fpr.png", OUT / "chart_cost_latency.png")


if __name__ == "__main__":
    sys.exit(main())
