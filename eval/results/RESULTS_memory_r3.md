# ScamBench-MY results (20261016-184031)

n = 20 messages. mock=False

| config | f1 | precision | recall | false_positive_rate | fpr_hard_negatives | family_accuracy_on_scams | median_latency_ms | cost_usd_per_1000 | escalations | tool_hits | mock |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fast | 0.909 | 0.833 | 1.0 | 0.2 | 0.2 | 0.3 | 9775 | 0.2 | 0 | 0 | False |
| plan | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0.3 | 15406 | 2.27 | 0 | 3 | False |
| plan_no_ledger | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0.5 | 16127 | 2.43 | 0 | 2 | False |


**F1 by language**

| config | en | manglish | ms |
|---|---|---|---|
| fast | 0.857 | 1.0 | 0.909 |
| plan | 1.0 | 1.0 | 1.0 |
| plan_no_ledger | 1.0 | 1.0 | 1.0 |


**Recall by scam family**

| config | impersonation | investment |
|---|---|---|
| fast | 1.0 | 1.0 |
| plan | 1.0 | 1.0 |
| plan_no_ledger | 1.0 | 1.0 |
