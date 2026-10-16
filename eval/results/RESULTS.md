# ScamBench-MY results

n = 300 messages.

> Live on Nebius Token Factory, 16 Oct 2026. `rules` = keyword baseline (no model). `fast` = Nemotron 3.5 Lightning only. **`plan` = the default tier** (Lightning triage + Nemotron 3 Super plan/verdict + Tavily + household memory). `plan_no_ledger` = default without memory. These four rows are the final build. `full` (+ Nemotron 3 Ultra second opinion) and `no_tavily` (`full` without Tavily) were measured on an earlier build the same day.

| config | f1 | precision | recall | false_positive_rate | fpr_hard_negatives | family_accuracy_on_scams | median_latency_ms | cost_usd_per_1000 | escalations | tool_hits | mock |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rules | 0.763 | 0.765 | 0.76 | 0.233 | 0.5 | 0.647 | 1 | 0.12 | 0 | 0 | True |
| fast | 0.887 | 0.801 | 0.993 | 0.247 | 0.481 | 0.8 | 8570 | 0.18 | 0 | 0 | False |
| plan | 0.939 | 0.902 | 0.98 | 0.107 | 0.212 | 0.88 | 16873 | 2.2 | 0 | 63 | False |
| plan_no_ledger | 0.94 | 0.897 | 0.987 | 0.113 | 0.192 | 0.9 | 16330 | 2.1 | 0 | 53 | False |
| full | 0.936 | 0.901 | 0.973 | 0.107 | 0.192 | 0.9 | 16242 | 2.51 | 40 | 67 | False |
| no_tavily | 0.955 | 0.925 | 0.987 | 0.08 | 0.192 | 0.907 | 14236 | 2.55 | 59 | 0 | False |


**F1 by language**

| config | en | manglish | ms |
|---|---|---|---|
| rules | 0.755 | 0.776 | 0.759 |
| fast | 0.869 | 0.939 | 0.862 |
| plan | 0.937 | 0.978 | 0.909 |
| plan_no_ledger | 0.929 | 0.968 | 0.926 |
| full | 0.937 | 0.968 | 0.907 |
| no_tavily | 0.964 | 0.978 | 0.926 |


**Recall by scam family**

| config | impersonation | investment | love | mule | parcel | phishing_otp |
|---|---|---|---|---|---|---|
| rules | 0.96 | 0.76 | 0.64 | 0.4 | 0.92 | 0.88 |
| fast | 1.0 | 1.0 | 0.96 | 1.0 | 1.0 | 1.0 |
| plan | 1.0 | 1.0 | 0.88 | 1.0 | 1.0 | 1.0 |
| plan_no_ledger | 1.0 | 1.0 | 0.92 | 1.0 | 1.0 | 1.0 |
| full | 1.0 | 1.0 | 0.84 | 1.0 | 1.0 | 1.0 |
| no_tavily | 1.0 | 1.0 | 0.92 | 1.0 | 1.0 | 1.0 |
