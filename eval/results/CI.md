# Confidence intervals

Paired bootstrap, 2000 resamples of n = 300 messages.

| config | F1 | 95% CI | false-positive rate | 95% CI |
|---|---|---|---|---|
| rules | 0.763 | 0.705–0.813 | 23.3% | 17.0%–30.2% |
| fast | 0.887 | 0.846–0.918 | 24.7% | 18.4%–31.9% |
| plan | 0.939 | 0.909–0.964 | 10.7% | 5.9%–15.8% |
| plan_no_ledger | 0.940 | 0.910–0.964 | 11.3% | 6.5%–16.6% |
| full | 0.936 | 0.904–0.962 | 10.7% | 6.0%–16.0% |
| no_tavily | 0.955 | 0.928–0.977 | 8.0% | 3.9%–12.8% |

**Paired differences (A − B).** Significant if the 95% CI excludes 0.

| comparison | ΔF1 | 95% CI | ΔFPR | 95% CI |
|---|---|---|---|---|
| plan − fast | +0.052 ✱ | +0.021…+0.086 | -14.0% ✱ | -21.2%…-7.1% |
| plan − rules | +0.177 ✱ | +0.126…+0.232 | -12.7% ✱ | -20.3%…-5.1% |
| plan − plan_no_ledger | -0.000 | -0.024…+0.024 | -0.7% | -5.8%…+4.3% |
| full − plan | -0.003 | -0.027…+0.019 | +0.0% | -4.8%…+5.0% |
| full − no_tavily | -0.019 | -0.042…+0.003 | +2.7% | -2.0%…+7.5% |
