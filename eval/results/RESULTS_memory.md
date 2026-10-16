# ScamBench-MY results (20261016-174326)

n = 20 messages. mock=False

| config | f1 | precision | recall | false_positive_rate | fpr_hard_negatives | family_accuracy_on_scams | median_latency_ms | cost_usd_per_1000 | escalations | tool_hits | mock |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fast | 0.909 | 0.833 | 1.0 | 0.2 | 0.2 | 0.3 | 11132 | 0.2 | 0 | 0 | False |
| full | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0.2 | 16934 | 2.75 | 2 | 4 | False |
| no_ledger | 0.87 | 0.769 | 1.0 | 0.3 | 0.3 | 0.2 | 21906 | 2.73 | 1 | 12 | False |


**F1 by language**

| config | en | manglish | ms |
|---|---|---|---|
| fast | 0.857 | 1.0 | 0.909 |
| full | 1.0 | 1.0 | 1.0 |
| no_ledger | 0.857 | 1.0 | 0.833 |


**Recall by scam family**

| config | impersonation | investment |
|---|---|---|
| fast | 1.0 | 1.0 |
| full | 1.0 | 1.0 |
| no_ledger | 1.0 | 1.0 |
