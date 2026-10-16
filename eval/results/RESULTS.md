# ScamBench-MY results

n = 300 messages.

> All rows run live on Nebius Token Factory on 16 Oct 2026, on the same code (commit 197133f+), except `rules` (keyword baseline, no model). `plan` is the **default** tier (Lightning triage + Super plan/verdict + Tavily + memory). `full` adds a Nemotron 3 Ultra second opinion. `no_tavily` and `no_ledger` are ablations of `full`.

| config | f1 | precision | recall | false_positive_rate | fpr_hard_negatives | family_accuracy_on_scams | median_latency_ms | cost_usd_per_1000 | escalations | tool_hits | mock |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rules | 0.763 | 0.765 | 0.76 | 0.233 | 0.5 | 0.647 | 1 | 0.12 | 0 | 0 | True |
| fast | 0.892 | 0.813 | 0.987 | 0.227 | 0.423 | 0.807 | 8112 | 0.18 | 0 | 0 | False |
| plan | 0.946 | 0.908 | 0.987 | 0.1 | 0.231 | 0.913 | 16479 | 2.18 | 0 | 77 | False |
| full | 0.936 | 0.901 | 0.973 | 0.107 | 0.192 | 0.9 | 16242 | 2.51 | 40 | 67 | False |
| no_tavily | 0.955 | 0.925 | 0.987 | 0.08 | 0.192 | 0.907 | 14236 | 2.55 | 59 | 0 | False |
| no_ledger | 0.955 | 0.92 | 0.993 | 0.087 | 0.192 | 0.907 | 18015 | 2.51 | 50 | 80 | False |


**F1 by language**

| config | en | manglish | ms |
|---|---|---|---|
| rules | 0.755 | 0.776 | 0.759 |
| fast | 0.881 | 0.92 | 0.877 |
| plan | 0.938 | 0.978 | 0.926 |
| full | 0.937 | 0.968 | 0.907 |
| no_tavily | 0.964 | 0.978 | 0.926 |
| no_ledger | 0.946 | 0.989 | 0.935 |


**Recall by scam family**

| config | impersonation | investment | love | mule | parcel | phishing_otp |
|---|---|---|---|---|---|---|
| rules | 0.96 | 0.76 | 0.64 | 0.4 | 0.92 | 0.88 |
| fast | 1.0 | 1.0 | 0.92 | 1.0 | 1.0 | 1.0 |
| plan | 1.0 | 1.0 | 0.92 | 1.0 | 1.0 | 1.0 |
| full | 1.0 | 1.0 | 0.84 | 1.0 | 1.0 | 1.0 |
| no_tavily | 1.0 | 1.0 | 0.92 | 1.0 | 1.0 | 1.0 |
| no_ledger | 1.0 | 1.0 | 0.96 | 1.0 | 1.0 | 1.0 |
