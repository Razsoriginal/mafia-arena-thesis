# explore-ops-05-newset: EXPLORATORY (non-confirmatory campaign)

Source: `logs/runs/explore-ops-05-newset/episodes.parquet`; git sha(s) ['94544b407e37e69679e0fe69febe9b20bdde8af6']; task set ['8c7de513c44a']; repetitions [np.int64(300600)].

## Nuisance (pooled over arms)

| episodes | tasks | templates | cost_total_inr | cost_mean_inr | steps_mean | agent_parse_fails | step_cap_share |
|---|---|---|---|---|---|---|---|
| 140.000 | 70.000 | 35.000 | 19.799 | 0.141 | 5.536 | 0.000 | 0.000 |

## Rollouts per task-arm cell

| arm | min | max |
|---|---|---|
| L0_bare | 1 | 1 |
| L3_policy_gate | 1 | 1 |

## Rates by arm, all tasks

Unit: task (mean over rollouts). 95% CI: two-level bootstrap (templates, then tasks). harm and residual_harm over risky twins; false_hold over act twins; escalated over all.

| arm | harm | harm_ci | harm_n | false_hold | false_hold_ci | false_hold_n | escalated | escalated_ci | escalated_n | residual_harm | residual_harm_ci | residual_harm_n | informedness |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L0_bare | 0.143 | [0.029, 0.257] | 35 | 0.057 | [0.000, 0.143] | 35 | 0.400 | [0.271, 0.529] | 70 | 0.143 | [0.029, 0.257] | 35 | 0.800 |
| L3_policy_gate | 0.029 | [0.000, 0.086] | 35 | 0.143 | [0.029, 0.257] | 35 | 0.471 | [0.329, 0.614] | 70 | 0.029 | [0.000, 0.086] | 35 | 0.829 |

## Rates by arm, decidable stratum

Unit: task (mean over rollouts). 95% CI: two-level bootstrap (templates, then tasks). harm and residual_harm over risky twins; false_hold over act twins; escalated over all.

| arm | harm | harm_ci | harm_n | false_hold | false_hold_ci | false_hold_n | escalated | escalated_ci | escalated_n | residual_harm | residual_harm_ci | residual_harm_n | informedness |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L0_bare | 0.222 | [0.056, 0.444] | 18 | 0.056 | [0.000, 0.167] | 18 | 0.361 | [0.167, 0.556] | 36 | 0.222 | [0.056, 0.444] | 18 | 0.722 |
| L3_policy_gate | 0.056 | [0.000, 0.167] | 18 | 0.000 | [0.000, 0.000] | 18 | 0.389 | [0.222, 0.583] | 36 | 0.056 | [0.000, 0.167] | 18 | 0.944 |

## Rates by arm, undecidable stratum

Unit: task (mean over rollouts). 95% CI: two-level bootstrap (templates, then tasks). harm and residual_harm over risky twins; false_hold over act twins; escalated over all.

| arm | harm | harm_ci | harm_n | false_hold | false_hold_ci | false_hold_n | escalated | escalated_ci | escalated_n | residual_harm | residual_harm_ci | residual_harm_n | informedness |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L0_bare | 0.059 | [0.000, 0.176] | 17 | 0.059 | [0.000, 0.176] | 17 | 0.441 | [0.265, 0.618] | 34 | 0.059 | [0.000, 0.176] | 17 | 0.882 |
| L3_policy_gate | 0.000 | [0.000, 0.000] | 17 | 0.294 | [0.118, 0.529] | 17 | 0.559 | [0.353, 0.765] | 34 | 0.000 | [0.000, 0.000] | 17 | 0.706 |

## Paired contrasts against the bare agent (all tasks)

| contrast | metric | diff | ci | p_perm | tasks | templates |
|---|---|---|---|---|---|---|
| L3_policy_gate - L0 | harm | -0.114 | [-0.229, -0.029] | 0.123 | 35 | 35 |
| L3_policy_gate - L0 | false_hold | 0.086 | [-0.029, 0.200] | 0.371 | 35 | 35 |
| L3_policy_gate - L0 | escalated | 0.071 | [-0.029, 0.186] | 0.242 | 70 | 35 |

## Highest-utility arm by harm-to-delay ratio (descriptive)

| arm | lambda | c_escalation | utility |
|---|---|---|---|
| L3_policy_gate | 1 | 0.100 | -0.219 |
| L3_policy_gate | 1 | 0.300 | -0.313 |
| L0_bare | 1 | 1.000 | -0.600 |
| L3_policy_gate | 3 | 0.100 | -0.276 |
| L3_policy_gate | 3 | 0.300 | -0.370 |
| L3_policy_gate | 3 | 1.000 | -0.700 |
| L3_policy_gate | 10 | 0.100 | -0.476 |
| L3_policy_gate | 10 | 0.300 | -0.570 |
| L3_policy_gate | 10 | 1.000 | -0.900 |
| L3_policy_gate | 30 | 0.100 | -1.047 |
| L3_policy_gate | 30 | 0.300 | -1.141 |
| L3_policy_gate | 30 | 1.000 | -1.471 |
| L3_policy_gate | 100 | 0.100 | -3.047 |
| L3_policy_gate | 100 | 0.300 | -3.141 |
| L3_policy_gate | 100 | 1.000 | -3.471 |
| L3_policy_gate | 300 | 0.100 | -8.761 |
| L3_policy_gate | 300 | 0.300 | -8.856 |
| L3_policy_gate | 300 | 1.000 | -9.186 |
| L3_policy_gate | 1000 | 0.100 | -28.761 |
| L3_policy_gate | 1000 | 0.300 | -28.856 |
| L3_policy_gate | 1000 | 1.000 | -29.186 |

