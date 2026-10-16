# ScamBench-MY results (20261016-081148)

n = 30 messages. mock=True

| config | f1 | precision | recall | false_positive_rate | fpr_hard_negatives | family_accuracy_on_scams | median_latency_ms | cost_usd_per_1000 | escalations | tool_hits | mock |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rules | 0.815 | 0.917 | 0.733 | 0.067 | 0.167 | 0.667 | 3 | 0.3 | 0 | 0 | True |


**F1 by language**

| config | en | manglish | ms |
|---|---|---|---|
| rules | 0.5 | 0.857 | 0.889 |


**Recall by scam family**

| config | impersonation | investment | love | mule | parcel | phishing_otp |
|---|---|---|---|---|---|---|
| rules | 1.0 | 1.0 | 0.667 | 0.0 | 0.5 | 1.0 |
