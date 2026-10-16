# ScamBench-MY results (20261016-181237)

n = 300 messages. mock=False

| config | f1 | precision | recall | false_positive_rate | fpr_hard_negatives | family_accuracy_on_scams | median_latency_ms | cost_usd_per_1000 | escalations | tool_hits | mock |
|---|---|---|---|---|---|---|---|---|---|---|---|
| plan | 0.946 | 0.908 | 0.987 | 0.1 | 0.231 | 0.907 | 16660 | 2.17 | 0 | 62 | False |
| fast | 0.887 | 0.801 | 0.993 | 0.247 | 0.481 | 0.8 | 8570 | 0.18 | 0 | 0 | False |


**F1 by language**

| config | en | manglish | ms |
|---|---|---|---|
| plan | 0.955 | 0.978 | 0.909 |
| fast | 0.869 | 0.939 | 0.862 |


**Recall by scam family**

| config | impersonation | investment | love | mule | parcel | phishing_otp |
|---|---|---|---|---|---|---|
| plan | 1.0 | 1.0 | 0.92 | 1.0 | 1.0 | 1.0 |
| fast | 1.0 | 1.0 | 0.96 | 1.0 | 1.0 | 1.0 |
