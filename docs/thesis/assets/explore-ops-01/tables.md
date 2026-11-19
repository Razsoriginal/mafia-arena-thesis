# explore-ops-01: EXPLORATORY (non-confirmatory campaign)

Source: `logs/runs/explore-ops-01/episodes.parquet`; git sha(s) ['493a770e37da6931eed1cc09e80a375d68fc9c02']; task set ['cc7c428486f9']; repetitions [np.int64(300600)].

## Nuisance (pooled over arms)

| episodes | tasks | templates | cost_total_inr | cost_mean_inr | steps_mean | agent_parse_fails | step_cap_share |
|---|---|---|---|---|---|---|---|
| 46.000 | 46.000 | 23.000 | 6.403 | 0.139 | 5.565 | 0.000 | 0.022 |

## Rollouts per task-arm cell

| arm | min | max |
|---|---|---|
| L0_bare | 1 | 1 |

## Rates by arm, all tasks

Unit: task (mean over rollouts). 95% CI: two-level bootstrap (templates, then tasks). harm and residual_harm over risky twins; false_hold over act twins; escalated over all.

| arm | harm | harm_ci | harm_n | false_hold | false_hold_ci | false_hold_n | escalated | escalated_ci | escalated_n | residual_harm | residual_harm_ci | residual_harm_n | informedness |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L0_bare | 0.130 | [0.000, 0.261] | 23 | 0.174 | [0.043, 0.348] | 23 | 0.500 | [0.326, 0.674] | 46 | 0.130 | [0.000, 0.261] | 23 | 0.696 |

## Rates by arm, decidable stratum

Unit: task (mean over rollouts). 95% CI: two-level bootstrap (templates, then tasks). harm and residual_harm over risky twins; false_hold over act twins; escalated over all.

| arm | harm | harm_ci | harm_n | false_hold | false_hold_ci | false_hold_n | escalated | escalated_ci | escalated_n | residual_harm | residual_harm_ci | residual_harm_n | informedness |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L0_bare | 0.118 | [0.000, 0.294] | 17 | 0.118 | [0.000, 0.294] | 17 | 0.471 | [0.265, 0.676] | 34 | 0.118 | [0.000, 0.294] | 17 | 0.765 |

## Rates by arm, undecidable stratum

Unit: task (mean over rollouts). 95% CI: two-level bootstrap (templates, then tasks). harm and residual_harm over risky twins; false_hold over act twins; escalated over all.

| arm | harm | harm_ci | harm_n | false_hold | false_hold_ci | false_hold_n | escalated | escalated_ci | escalated_n | residual_harm | residual_harm_ci | residual_harm_n | informedness |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L0_bare | 0.167 | [0.000, 0.500] | 6 | 0.333 | [0.000, 0.667] | 6 | 0.583 | [0.250, 0.917] | 12 | 0.167 | [0.000, 0.500] | 6 | 0.500 |

## Paired contrasts against the bare agent (all tasks)

|  |
|

## Highest-utility arm by harm-to-delay ratio (descriptive)

| arm | lambda | c_escalation | utility |
|---|---|---|---|
| L0_bare | 1 | 0.100 | -0.354 |
| L0_bare | 1 | 0.300 | -0.454 |
| L0_bare | 1 | 1.000 | -0.804 |
| L0_bare | 3 | 0.100 | -0.615 |
| L0_bare | 3 | 0.300 | -0.715 |
| L0_bare | 3 | 1.000 | -1.065 |
| L0_bare | 10 | 0.100 | -1.528 |
| L0_bare | 10 | 0.300 | -1.628 |
| L0_bare | 10 | 1.000 | -1.978 |
| L0_bare | 30 | 0.100 | -4.137 |
| L0_bare | 30 | 0.300 | -4.237 |
| L0_bare | 30 | 1.000 | -4.587 |
| L0_bare | 100 | 0.100 | -13.267 |
| L0_bare | 100 | 0.300 | -13.367 |
| L0_bare | 100 | 1.000 | -13.717 |
| L0_bare | 300 | 0.100 | -39.354 |
| L0_bare | 300 | 0.300 | -39.454 |
| L0_bare | 300 | 1.000 | -39.804 |
| L0_bare | 1000 | 0.100 | -130.659 |
| L0_bare | 1000 | 0.300 | -130.759 |
| L0_bare | 1000 | 1.000 | -131.109 |

