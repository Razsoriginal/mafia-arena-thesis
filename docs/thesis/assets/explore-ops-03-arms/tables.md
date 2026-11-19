# explore-ops-03-arms: EXPLORATORY (non-confirmatory campaign)

Source: `logs/runs/explore-ops-03-arms/episodes.parquet`; git sha(s) ['f3313d52b186552b391cd699535eb2a9445e4b4c']; task set ['cc7c428486f9']; repetitions [np.int64(300600)].

## Nuisance (pooled over arms)

| episodes | tasks | templates | cost_total_inr | cost_mean_inr | steps_mean | agent_parse_fails | step_cap_share |
|---|---|---|---|---|---|---|---|
| 230.000 | 46.000 | 23.000 | 33.997 | 0.148 | 5.661 | 0.000 | 0.009 |

## Rollouts per task-arm cell

| arm | min | max |
|---|---|---|
| L1_prompt_rule | 1 | 1 |
| L2_self_verify | 1 | 1 |
| L3_policy_gate | 1 | 1 |
| L5a_approve_all | 1 | 1 |
| L6_reversibility | 1 | 1 |

## Rates by arm, all tasks

Unit: task (mean over rollouts). 95% CI: two-level bootstrap (templates, then tasks). harm and residual_harm over risky twins; false_hold over act twins; escalated over all.

| arm | harm | harm_ci | harm_n | false_hold | false_hold_ci | false_hold_n | escalated | escalated_ci | escalated_n | residual_harm | residual_harm_ci | residual_harm_n | informedness |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L1_prompt_rule | 0.087 | [0.000, 0.217] | 23 | 0.217 | [0.087, 0.391] | 23 | 0.543 | [0.370, 0.717] | 46 | 0.087 | [0.000, 0.217] | 23 | 0.696 |
| L2_self_verify | 0.087 | [0.000, 0.217] | 23 | 0.348 | [0.174, 0.522] | 23 | 0.543 | [0.370, 0.717] | 46 | 0.087 | [0.000, 0.217] | 23 | 0.565 |
| L3_policy_gate | 0.043 | [0.000, 0.130] | 23 | 0.174 | [0.043, 0.348] | 23 | 0.522 | [0.348, 0.696] | 46 | 0.043 | [0.000, 0.130] | 23 | 0.783 |
| L5a_approve_all | 0.000 | [0.000, 0.000] | 23 | 0.174 | [0.043, 0.348] | 23 | 0.978 | [0.913, 1.000] | 46 | 0.000 | [0.000, 0.000] | 23 | 0.826 |
| L6_reversibility | 0.174 | [0.043, 0.348] | 23 | 0.174 | [0.043, 0.348] | 23 | 0.500 | [0.326, 0.674] | 46 | 0.043 | [0.000, 0.130] | 23 | 0.652 |

## Rates by arm, decidable stratum

Unit: task (mean over rollouts). 95% CI: two-level bootstrap (templates, then tasks). harm and residual_harm over risky twins; false_hold over act twins; escalated over all.

| arm | harm | harm_ci | harm_n | false_hold | false_hold_ci | false_hold_n | escalated | escalated_ci | escalated_n | residual_harm | residual_harm_ci | residual_harm_n | informedness |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L1_prompt_rule | 0.059 | [0.000, 0.176] | 17 | 0.176 | [0.000, 0.353] | 17 | 0.529 | [0.324, 0.735] | 34 | 0.059 | [0.000, 0.176] | 17 | 0.765 |
| L2_self_verify | 0.059 | [0.000, 0.176] | 17 | 0.412 | [0.176, 0.647] | 17 | 0.559 | [0.353, 0.765] | 34 | 0.059 | [0.000, 0.176] | 17 | 0.529 |
| L3_policy_gate | 0.000 | [0.000, 0.000] | 17 | 0.118 | [0.000, 0.294] | 17 | 0.500 | [0.294, 0.706] | 34 | 0.000 | [0.000, 0.000] | 17 | 0.882 |
| L5a_approve_all | 0.000 | [0.000, 0.000] | 17 | 0.118 | [0.000, 0.294] | 17 | 0.971 | [0.882, 1.000] | 34 | 0.000 | [0.000, 0.000] | 17 | 0.882 |
| L6_reversibility | 0.176 | [0.000, 0.353] | 17 | 0.118 | [0.000, 0.294] | 17 | 0.471 | [0.265, 0.676] | 34 | 0.059 | [0.000, 0.176] | 17 | 0.706 |

## Rates by arm, undecidable stratum

Unit: task (mean over rollouts). 95% CI: two-level bootstrap (templates, then tasks). harm and residual_harm over risky twins; false_hold over act twins; escalated over all.

| arm | harm | harm_ci | harm_n | false_hold | false_hold_ci | false_hold_n | escalated | escalated_ci | escalated_n | residual_harm | residual_harm_ci | residual_harm_n | informedness |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L1_prompt_rule | 0.167 | [0.000, 0.500] | 6 | 0.333 | [0.000, 0.667] | 6 | 0.583 | [0.250, 0.917] | 12 | 0.167 | [0.000, 0.500] | 6 | 0.500 |
| L2_self_verify | 0.167 | [0.000, 0.500] | 6 | 0.167 | [0.000, 0.500] | 6 | 0.500 | [0.167, 0.833] | 12 | 0.167 | [0.000, 0.500] | 6 | 0.667 |
| L3_policy_gate | 0.167 | [0.000, 0.500] | 6 | 0.333 | [0.000, 0.667] | 6 | 0.583 | [0.250, 0.917] | 12 | 0.167 | [0.000, 0.500] | 6 | 0.500 |
| L5a_approve_all | 0.000 | [0.000, 0.000] | 6 | 0.333 | [0.000, 0.667] | 6 | 1.000 | [1.000, 1.000] | 12 | 0.000 | [0.000, 0.000] | 6 | 0.667 |
| L6_reversibility | 0.167 | [0.000, 0.500] | 6 | 0.333 | [0.000, 0.667] | 6 | 0.583 | [0.250, 0.917] | 12 | 0.000 | [0.000, 0.000] | 6 | 0.500 |

## Highest-utility arm by harm-to-delay ratio (descriptive)

| arm | lambda | c_escalation | utility |
|---|---|---|---|
| L3_policy_gate | 1 | 0.100 | -0.270 |
| L3_policy_gate | 1 | 0.300 | -0.374 |
| L3_policy_gate | 1 | 1.000 | -0.739 |
| L5a_approve_all | 3 | 0.100 | -0.272 |
| L3_policy_gate | 3 | 0.300 | -0.461 |
| L3_policy_gate | 3 | 1.000 | -0.826 |
| L5a_approve_all | 10 | 0.100 | -0.272 |
| L5a_approve_all | 10 | 0.300 | -0.467 |
| L3_policy_gate | 10 | 1.000 | -1.130 |
| L5a_approve_all | 30 | 0.100 | -0.272 |
| L5a_approve_all | 30 | 0.300 | -0.467 |
| L5a_approve_all | 30 | 1.000 | -1.152 |
| L5a_approve_all | 100 | 0.100 | -0.272 |
| L5a_approve_all | 100 | 0.300 | -0.467 |
| L5a_approve_all | 100 | 1.000 | -1.152 |
| L5a_approve_all | 300 | 0.100 | -0.272 |
| L5a_approve_all | 300 | 0.300 | -0.467 |
| L5a_approve_all | 300 | 1.000 | -1.152 |
| L5a_approve_all | 1000 | 0.100 | -0.272 |
| L5a_approve_all | 1000 | 0.300 | -0.467 |
| L5a_approve_all | 1000 | 1.000 | -1.152 |

