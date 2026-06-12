# HW4 run report

## Findings
15 hypotheses (GOD_NODE: 3, SPOF: 1, TRACE_GAP: 11); validation trail in results/FINDINGS.md.

## Fix loop
1 iteration(s); stop reason: **NO_SAFE_ACTION**.

## Token experiment
Overall input-token savings: **85.6%** (target ≥70%).

| Q | tier | in-tokens A | in-tokens B | savings | trunc A |
|---|---|---|---|---|---|
| Q-01 | locate | 27510 | 4390 | 84.0% | yes |
| Q-02 | locate | 27520 | 3184 | 88.4% | yes |
| Q-03 | locate | 27506 | 2524 | 90.8% | yes |
| Q-04 | path | 27512 | 3526 | 87.2% | yes |
| Q-05 | path | 27512 | 2386 | 91.3% | yes |
| Q-06 | path | 27512 | 4462 | 83.8% | yes |
| Q-07 | path | 27506 | 2680 | 90.3% | yes |
| Q-08 | impact | 27506 | 10188 | 63.0% | yes |
| Q-09 | impact | 27516 | 3616 | 86.9% | yes |
| Q-10 | impact | 27512 | 2562 | 90.7% | yes |
| **total** | | **275112** | **39518** | **85.6%** | |

## Cost
109 gated calls; 665449 in / 26025 out tokens; **$0.6332** total.
