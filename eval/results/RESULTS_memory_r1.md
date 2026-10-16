# ScamBench-MY results (20261016-183554)

n = 20 messages. mock=False

| config | f1 | precision | recall | false_positive_rate | fpr_hard_negatives | family_accuracy_on_scams | median_latency_ms | cost_usd_per_1000 | escalations | tool_hits | mock |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fast | 0.909 | 0.833 | 1.0 | 0.2 | 0.2 | 0.3 | 10371 | 0.21 | 0 | 0 | False |
| plan | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0.4 | 16708 | 2.37 | 0 | 2 | False |
| plan_no_ledger | 0.909 | 0.833 | 1.0 | 0.2 | 0.2 | 0.5 | 18158 | 2.43 | 0 | 5 | False |


**F1 by language**

| config | en | manglish | ms |
|---|---|---|---|
| fast | 0.857 | 1.0 | 0.909 |
| plan | 1.0 | 1.0 | 1.0 |
| plan_no_ledger | 0.75 | 1.0 | 1.0 |


**Recall by scam family**

| config | impersonation | investment |
|---|---|---|
| fast | 1.0 | 1.0 |
| plan | 1.0 | 1.0 |
| plan_no_ledger | 1.0 | 1.0 |
