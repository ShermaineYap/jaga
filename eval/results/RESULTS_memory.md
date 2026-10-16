# ScamBench-MY results (20261016-181502)

n = 20 messages. mock=False

| config | f1 | precision | recall | false_positive_rate | fpr_hard_negatives | family_accuracy_on_scams | median_latency_ms | cost_usd_per_1000 | escalations | tool_hits | mock |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fast | 0.87 | 0.769 | 1.0 | 0.3 | 0.3 | 0.3 | 10354 | 0.2 | 0 | 0 | False |
| plan | 0.947 | 1.0 | 0.9 | 0.0 | 0.0 | 0.3 | 30489 | 2.4 | 0 | 2 | False |
| no_ledger | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0.4 | 20080 | 3.0 | 4 | 5 | False |


**F1 by language**

| config | en | manglish | ms |
|---|---|---|---|
| fast | 0.857 | 1.0 | 0.833 |
| plan | 0.8 | 1.0 | 1.0 |
| no_ledger | 1.0 | 1.0 | 1.0 |


**Recall by scam family**

| config | impersonation | investment |
|---|---|---|
| fast | 1.0 | 1.0 |
| plan | 0.875 | 1.0 |
| no_ledger | 1.0 | 1.0 |
