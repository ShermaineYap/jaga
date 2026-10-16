# ScamBench-MY results (20261016-183848)

n = 20 messages. mock=False

| config | f1 | precision | recall | false_positive_rate | fpr_hard_negatives | family_accuracy_on_scams | median_latency_ms | cost_usd_per_1000 | escalations | tool_hits | mock |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fast | 0.909 | 0.833 | 1.0 | 0.2 | 0.2 | 0.4 | 11010 | 0.21 | 0 | 0 | False |
| plan | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0.6 | 14971 | 2.2 | 0 | 3 | False |
| plan_no_ledger | 0.857 | 0.818 | 0.9 | 0.2 | 0.2 | 0.3 | 19004 | 2.52 | 0 | 3 | False |


**F1 by language**

| config | en | manglish | ms |
|---|---|---|---|
| fast | 0.857 | 1.0 | 0.909 |
| plan | 1.0 | 1.0 | 1.0 |
| plan_no_ledger | 0.571 | 1.0 | 1.0 |


**Recall by scam family**

| config | impersonation | investment |
|---|---|---|
| fast | 1.0 | 1.0 |
| plan | 1.0 | 1.0 |
| plan_no_ledger | 0.875 | 1.0 |
