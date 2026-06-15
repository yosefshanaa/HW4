# HW4 run report

## Findings
8 hypotheses (GOD_NODE: 7, TRACE_GAP: 1); validation trail in results/FINDINGS.md.

## Fix loop
1 iteration(s); stop reason: **NO_SAFE_ACTION**.

## Token experiment
Overall input-token savings: **89.8%** (target ≥70%).

| Q | tier | in-tokens A | in-tokens B | savings | trunc A |
|---|---|---|---|---|---|
| Q-01 | locate | 30080 | 3856 | 87.2% | yes |
| Q-02 | locate | 33514 | 2840 | 91.5% | yes |
| Q-03 | locate | 33504 | 2650 | 92.1% | yes |
| Q-04 | path | 29646 | 3394 | 88.5% | yes |
| Q-05 | path | 29536 | 3246 | 89.0% | yes |
| Q-06 | path | 33492 | 2680 | 92.0% | yes |
| Q-07 | path | 29444 | 2628 | 91.1% | yes |
| Q-08 | impact | 32146 | 2720 | 91.5% | yes |
| Q-09 | impact | 30088 | 5292 | 82.4% | yes |
| Q-10 | impact | 31990 | 2680 | 91.6% | yes |
| **total** | | **313440** | **31986** | **89.8%** | |

## Cost
109 gated calls; 515912 in / 18270 out tokens; **$0.0883** total.
