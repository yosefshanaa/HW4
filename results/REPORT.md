# HW4 run report

## Findings
8 hypotheses (GOD_NODE: 7, TRACE_GAP: 1); validation trail in results/FINDINGS.md.

## Fix loop
1 iteration(s); stop reason: **NO_SAFE_ACTION**.

## Token experiment
Overall input-token savings: **58.7%** (target ≥70%).

| Q | tier | in-tokens A | in-tokens B | savings | trunc A |
|---|---|---|---|---|---|
| Q-01 | locate | 30080 | 10588 | 64.8% | yes |
| Q-02 | locate | 33514 | 16952 | 49.4% | yes |
| Q-03 | locate | 33504 | 12770 | 61.9% | yes |
| Q-04 | path | 29646 | 14260 | 51.9% | yes |
| Q-05 | path | 29536 | 11764 | 60.2% | yes |
| Q-06 | path | 33492 | 6414 | 80.8% | yes |
| Q-07 | path | 29444 | 10562 | 64.1% | yes |
| Q-08 | impact | 32146 | 12766 | 60.3% | yes |
| Q-09 | impact | 30088 | 18792 | 37.5% | yes |
| Q-10 | impact | 31990 | 14668 | 54.1% | yes |
| **total** | | **313440** | **129536** | **58.7%** | |

## Cost
89 gated calls; 483926 in / 16738 out tokens; **$0.0826** total.
