# Confidence intervals — memory

Paired bootstrap, 2000 resamples of n = 20 messages.

| config | F1 | 95% CI | false-positive rate | 95% CI |
|---|---|---|---|---|
| fast | 0.909 | 0.750–1.000 | 20.0% | 0.0%–50.0% |
| full | 1.000 | 1.000–1.000 | 0.0% | 0.0%–0.0% |
| no_ledger | 0.870 | 0.667–1.000 | 30.0% | 0.0%–60.0% |

**Paired differences (A − B).** Significant if the 95% CI excludes 0.

| comparison | ΔF1 | 95% CI | ΔFPR | 95% CI |
|---|---|---|---|---|
| full − no_ledger | +0.130 | +0.000…+0.333 | -30.0% | -60.0%…+0.0% |
