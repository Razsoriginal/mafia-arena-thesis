# Pre-Registration — Mafia Arena Thesis MVP

**Date:** 2026-11-06
**Status:** Draft, approved Phase 3 as amended by Part A and the vote-temperature amendment. Freeze tag is left to a later step.
**Branch at writing:** `prereg-mvp`
**Starting sha:** `305e9898547be3af621006f1e1c66fc687235dda`

prompts_sha256: d36b31402d91200761ab5b10e42b2b30ecc29452ab31b554dc76d5bf72962efc
freeze_git_sha: PENDING

Figures are tagged **measured**, **derived**, or **assumed**.

## 1. Estimand

Under a fixed 7-player Mafia protocol with 2 mafia, 1 doctor, 1 detective, and 3 villagers, mafia seats always play CoT, and the same requested seed fixes the seat-to-role map in every arm, the estimand is the paired difference in village win probability when all five village seats play DMN/TPN/EVT versus when all five village seats play CoT, and versus when all five village seats play compute-matched CoT-x3, on the `meta/muse-spark-1.3-contributor` backbone. The primary summary is the paired risk difference with a 95% paired-by-seed bootstrap CI. This design lets me claim a village-team effect of the DMN/TPN/EVT architecture against a fixed CoT opponent, and not a single-agent effect, a mafia-side effect, or an effect versus ReAct or Constitution.

Design 3 (village team vs fixed CoT mafia) is the primary confirmatory design. Design 1 (focal seat) is retired as pilot history. Design 2 (homogeneous self-play) is the named alternative in Limitations. The mafia mirror is out of the MVP, as a limitation plus an optional exploratory cell in §10.

## 2. Arms

| Arm label | Village seats (5) | Mafia seats (2) |
|---|---|---|
| `dmn_village` | DmnTpnAgent | CotAgent |
| `cot_village` | CotAgent | CotAgent |
| `cotx3_village` | CotAgent, 3-sample vote | CotAgent |
| `random_village` | RandomVoterAgent | CotAgent |
| `majority_village` | MajorityFollowerAgent | CotAgent |

Confirmatory arms are `dmn_village`, `cot_village`, and `cotx3_village`. Null arms are benchmark arms in §7.

## 3. Roles and seed pairing

Roles per game are 2 mafia, 1 doctor, 1 detective, and 3 villagers. The village condition always covers exactly one doctor, one detective, and three villagers. Mafia is fixed CoT in every confirmatory arm.

Requested seeds are pre-listed as `5000 + i*100`. The same requested seed runs in all confirmatory arms before the next seed, so a seed-trio is the pairing unit. `--focal-role random` is frozen, and the focal re-seeding path must not be used. Analysis keys on `requested_seed`. Intent-to-treat: every completed seed-trio counts, including night-0 village deaths and day-cap draws. No conditioning on survival.

Planned n is 184 seed-trios. It is a CLI argument and will be re-decided after the calibration batch under §9. No secondary cell may draw on the reserve.

## 4. Primary and secondary metrics

Primary: village win-rate difference, paired by seed. Outcome is village win versus not, with a day-cap draw counted as not-a-village-win. The primary contrast is DMN village minus CoT village. DMN versus CoT-x3 is the single key secondary contrast.

Success for the primary at the planned n is completion at target precision and, under the confirmatory rule in §5, the paired test. Draw rate is reported separately.

Secondaries are never pooled across arm labels. Their denominators are per condition: delay quality once per game-day, cascade resistance over village voters on wrong-plurality days excluding abstentions, abstention rate over village votes, calibration by trust source in §6, say-do gap for DMN only with its n, JSON failure rate per game, game length in days, and cost per game in billed Rs.

Cascade and delay CIs are clustered by game. Trust CIs are clustered by game. No CI is computed over vote rows, trust rows, or seat-days as if independent.

## 5. Hypotheses and confirmatory rule

Directional hypotheses: DMN village wins more than CoT village; DMN village wins more than CoT-x3 village; DMN delay quality is higher; DMN cascade resistance is higher; DMN probe ECE is lower and AUC is higher than CoT probe; DMN say-do gap is near zero as an absolute property; DMN abstention is higher as a mechanism descriptor only.

Baseline village win-rate for power arithmetic is 0.45, **assumed**, close to the pilot village share of 6/14, **measured**. Power at 184 per arm is 0.49 / 0.83 / 0.98, **derived**, for +10 / +15 / +20 points, **assumed** effects. Unpaired power of 0.80 for +15 points needs 171 per arm, **derived**. For +10 points it needs 389 per arm, **derived**.

The primary is a confirmatory two-sided test at alpha 0.05 only if the final n stays at or above 171. That n is re-decided on cost and nuisance grounds only, never on an arm difference. If the final n falls below 171, the primary reverts to estimation-only.

Permitted wording if the paired 95% CI excludes zero: "In village-team games against a fixed CoT mafia on the frozen backbone and protocol, the DMN/TPN/EVT village won [X] percentage points more often than the CoT village (paired difference [X], 95% CI [a, b], n = [N] seed-trios). This supports a village detection advantage against this opponent. It does not establish an advantage against DMN mafia, ReAct, or Constitution, and it establishes no mafia-side effect."

Permitted wording if the paired 95% CI includes zero: "The estimated village win-rate difference was [X] percentage points (95% CI [a, b], n = [N] seed-trios). The study does not establish a village win-rate advantage for the DMN/TPN/EVT village against a fixed CoT mafia. Effects between [a] and [b] remain compatible with the data."

## 6. Trust probe

Option (i) is adopted: probe every arm, including DMN, on identical targets, and compare probe to probe. DMN decision-linked trust is reported separately and is never compared head-to-head with another arm's probe trust.

The probe runs after the day's votes, using the same pre-vote public history snapshot plus that seat's private note. It includes no DMN confidence, trust, or trace. Its output never enters game history, later speech, or any vote, and never feeds back into decisions. Targets are every alive non-self player that day, for every alive village seat in an LLM arm. Null arms are not probed, because probing would require an LLM call and would break their definition.

Probe inputs and outputs are recorded with `trust_source = "probe"`. DMN decision-linked rows are recorded with `trust_source = "decision"`. The two sources are reported in separate calibration tables and never merged into one ECE, Brier, or AUC number.

DMN decision-linked trust uses verified rows for its headline descriptive calibration. Decision trust for TPN-verified targets is derived from revised confidences, and unverified players receive the base-rate innocent prior. Prior-filler rows are reported separately with a prior-only null. Self rows are excluded in every calibration analysis, and the dropped count is reported.

Costs: the probe is Rs.0.25 per probed game, **derived/assumed**, until measured in the calibration batch.

Frozen probe wording: "Calibration comparisons use post-vote elicited trust, collected with an identical prompt, on identical alive non-self targets, in every arm including DMN. DMN decision-linked trust, derived from TPN-verified confidences with a base-rate prior for unverified players, is reported separately as a mechanistic descriptor and is never compared head-to-head with another arm's probe trust."

## 7. Null arms

Random-voter village speaks the fixed line "I am watching and waiting for evidence." It votes uniformly at random over alive non-self players plus `no-lynch`, using a seeded generator keyed by requested seed, day, and player id. Its doctor saves itself. Its detective checks the lowest-numbered alive non-self player and ignores the result.

Majority-follower village speaks the same fixed line. It votes `no-lynch` on day 0, and after that copies the previous day's plurality target when that player is alive and is not itself, otherwise `no-lynch`. Previous plurality is passed explicitly to its vote call, never parsed from history text. Doctor and detective night rules are identical to the random arm, so voting is the only difference between the nulls.

Null village seats make no LLM calls. Games still cost money because mafia seats are CoT. Cost per null game is Rs.0.60, **derived/assumed**, with planning total Rs.96, **derived/assumed**, for both nulls on the first 80 primary requested seeds. Runtime per null game is 30% to 50% of an all-CoT game, **assumed**, until the first null games are timed.

Win rate, game length, cost, and abstention apply to nulls. Mechanical cascade for the random arm and mechanical delay quality may be reported as labelled exploratory floors. Majority-follower cascade near zero is a manipulation check. ECE, Brier, AUC, and say-do gap do not apply because nulls emit no trust and no commitment.

Null claim wording: "Against the same fixed CoT mafia, a village voting uniformly at random won [X]% (95% CI [...]) and a village following the previous plurality won [Y]% (95% CI [...]). All LLM village effects are interpreted relative to these floors, not relative to zero."

## 8. Temperatures and frozen parameters

Vote-temperature amendment: every vote-sample call in every arm runs at 0.7, including the DMN cited vote. DMN and TPN reasoning, night actions, and the probe run at 0.0. CoT-x3 takes 3 samples at 0.7 and uses majority voting. If all three samples differ, the first sample stands. Its extra samples do not re-sample after a tie.

Speak and dialogue run at 0.3 in every arm. All other frozen parameters are:

- Backbone `meta/muse-spark-1.3-contributor` through AiCredits. A realised model-string change stops the confirmatory set.
- `TAU_DELAY = 0.35`, passed explicitly as `--tau 0.35`, because the code default is 0.65. This is a **judgement call** frozen from the pilot sweep. The alternative 0.45 is named in Limitations and is not substituted after seeing data.
- `EVT_THRESHOLD = 0.6`.
- Jev threshold 0.6 for the later exploratory Jev cell only.
- `LLM_MAX_TOKENS = 2500`.
- Day cap 5, night mode `llm`, gate `llm`, no ablations in confirmatory games.
- One frozen git commit for the confirmatory run, recorded per row. Two distinct git shas in one confirmatory set is a protocol deviation.

Confirmatory CoT means CoT-single at vote temperature 0.7. Pilot CoT at vote temperature 0.0 is not directly comparable, and the thesis states that.

## 9. Budget, calibration batch, stopping

Hard cap is Rs.2,000, **assumed**. Reserve is Rs.400, **derived**, and is never used by primary or secondary cells. Usable budget is Rs.1,600, **derived**.

Settled cost inputs until measured: CoT village Rs.1.95 per game, **measured** on 4 games; DMN village Rs.2.59 per game, **derived/assumed**; CoT-x3 village Rs.2.84 per game, **derived/assumed**. With probe every arm, the planning trio cost is Rs.8.13, **derived/assumed**. The planned primary spend at 184 trios is Rs.1,496, **derived/assumed**, and with nulls Rs.1,592, **derived/assumed**.

The calibration batch is the first 20 seed-trios, or 60 games, **derived** allocation. Allowed interim quantities are cost, JSON failure rate, game length, probe cost, within-seed correlation, and CoT-x3 sample diversity, pooled. Arm win rates and arm differences are prohibited interim quantities. The analyst may report correlation and projected paired width only.

Calibration go and no-go rules:

- Cost: if projected spend exceeds Rs.1,600, reduce equal n by the budget formula. Below 171, the primary becomes estimation-only. Below 120, **assumed** floor, stop and seek approval.
- JSON failures: pooled calibration failures above 0.20 per game, **assumed** threshold, pause the run. A code or prompt correction discards the calibration games and restarts the seed list. If no correction is made, games may count after approval under the recorded rule.
- Length: pooled mean days below 1.5, **assumed** threshold, demotes delay quality and cascade resistance to descriptive. The day cap is not raised inside the confirmatory design.
- Probe cost: if measured probe cost exceeds Rs.0.35 per game, **assumed** threshold, reduce n if the budget requires it. Probe coverage and identical targets are not cut.
- Correlation: pairing is retained regardless of its value. Confirmatory status depends on final n alone.
- CoT-x3 diversity: report the proportion of non-unanimous three-sample votes. Low diversity is reported and does not authorise a mid-study temperature change.
- Billing errors and 402: the current trio is pending, not failed. It is rerun on the same requested seeds after top-up. Remaining trios stop until the funding decision is made.
- Other worker failures: rerun the exact task once. A second failure leaves that seed-trio pending and is reported.

No interim efficacy stopping is allowed. Games are run seed-major, as complete trios. Cumulative billed cost is checked after each trio against the usable Rs.1,600. If the cap is exceeded after a completed trio, remaining trios stop. Completed trios are analysed as recorded, expensive and long games are never trimmed, and seeds are never replaced after observing a failure.

Calibration games count towards the confirmatory set only if the calibration decision is GO with no code, prompt, temperature, model, or protocol change. If a change occurs, they are excluded and the seed list restarts. This is a **judgement call**; the alternative is to always exclude the calibration batch and spend its cost as burn-in.

## 10. Secondary cells after the primary

Secondary cells start only after the primary dataset is complete and locked, and only when actual cumulative spend plus the full cell cost stays within Rs.1,600 with Rs.400 reserve intact. Partial cells below the stated n are prohibited. No secondary cell may use the reserve.

Priority order:

1. Jev village-team cell: 30 DMN-village games with `--gate jev`, compared with matched primary DMN-village games. Total planning cost is Rs.90, **derived/assumed**. No-go if the first 5 games show a stub rate above 10%, **assumed** threshold. Descriptive claim only for latency, cost, stub rate, and delay behaviour.
2. Ablations: no-EVT, no-exformation, and no-TPN, in that order, at 20 DMN-village games each. Cost is Rs.57 per cell and Rs.170 for all three, **derived/assumed**. Comparators are reused from primary games on matched seeds.
3. Mafia mirror cells: CoT village against DMN mafia and DMN village against DMN mafia, for 40 seed-sets. Cost is Rs.222, **derived/assumed**. Exploratory deception and interaction claim only.
4. Constitution village: 40 games against CoT mafia. Cost is Rs.88, **derived/assumed**. Exploratory appendix claim only.
5. ReAct village: 40 games against CoT mafia. Cost is Rs.106, **derived/assumed**. Any result must state that ReAct spends additional compute on speech and is not compute-matched.

Jev, ablations, mirror, Constitution, and ReAct are not confirmatory cells under this version. Under planning costs, they normally activate only on measured underspend.

## 11. Exclusions and special outcomes

There are no game-level exclusions from the primary win-rate analysis. Every completed game counts.

- JSON failures remain in win rate. A DMN game delayed because of a JSON failure leaves the reasoned delay-quality denominator but stays in abstention calculations as a real abstention. It does not inflate cascade resistance because abstentions are excluded there.
- Provider errors, including 402, do not create a game row. The affected seed-trio is pending under the funding rule rather than being a loss or exclusion.
- Night-0 village deaths remain in all applicable analyses. A dead village seat contributes no later-day trust, vote, cascade, or delay rows for days when it is not alive. Night-0 death rate is reported by arm as a balance check. Conditioning on survival is prohibited.
- Day-cap draws count as not-a-village-win in the primary. Their days contribute to delay, cascade, abstention, and trust where applicable. Cap-hit rate is reported by arm, and any draw-excluded analysis is a labelled sensitivity only.
- A village seat's same-day trust from before a lynch remains a pre-lynch observation when the seat subsequently dies that day. Such rows are retained.
- Any `gate` other than `llm`, a Jev stub in confirmatory rows, a realised model-string change, a git-sha break, or a prompt/protocol change ends the confirmatory set at the boundary. Later games form a separate set.

## 12. Locked analysis decisions

1. ECE uses 10 equal-width bins on [0, 1]. Empty bins contribute zero. A 5-bin version is appendix-only and exploratory.
2. Probe calibration and decision-linked calibration are separate tables. Probe rows are explicitly elicited on identical targets. Decision-linked headline rows are TPN-verified rows, with prior-filler rows and a prior-only null reported separately.
3. Self rows are excluded for all calibration comparisons, with the dropped count printed.
4. AUC uses trust as P(innocent), innocent labelled 1 and mafia labelled 0, with Mann-Whitney ties scored 0.5. The CI is clustered by game.
5. Brier uses the same row set as ECE in the same table.
6. One primary contrast is tested: DMN village versus CoT village. DMN village versus CoT-x3 village is the single key secondary. The mechanism family is delay quality, cascade resistance, and abstention. The calibration family is ECE and AUC, with Brier as an unadjusted companion. Holm adjustment is reported within each secondary family. Exploratory analyses have descriptive CIs and are labelled exploratory.
7. The primary CI is paired-by-seed bootstrap, using 10,000 replicates, **assumed** bootstrap count, with random seed 20261106 and percentile intervals. Per-arm Wilson intervals and an unpaired difference interval are conservative references. An exact McNemar test on discordant pairs is sensitivity only.
8. Day-cap draws are not village wins in the headline analysis. A separate descriptive village, mafia, and draw breakdown is secondary.
9. Cascade and delay use the recorded plurality target and its correctness, not the engine's strict-majority lynch outcome. A plurality tie is flagged. Tied game-days remain in the primary secondary analysis and are removed only in a labelled tie sensitivity.
10. Cascade uses wrong-plurality days, village voters only, and excludes abstentions. Abstention is reported jointly and never counts as resistance.
11. Delay quality is counted once per game-day, not once per delaying village seat. A day qualifies when a village seat makes a reasoned delay and a plurality target exists. JSON-failure delays are excluded.
12. Say-do gap is DMN-only, because only DMN emits the fixed cited-evidence commitment. It uses commitment rows, lynch votes only, and excludes abstentions. Recorded valid citations determine whether a vote complies.
13. Missing probe trust is complete-case within the relevant calibration analysis, with missingness reported by arm. Probe rows are never imputed from a prior.
14. Cost is reported as mean and total per arm, with no trimming of expensive or long games.
15. Game length is not adjusted for in the primary. It is a post-treatment outcome, a balance and reporting measure, and a calibration nuisance quantity only.
16. Night-0 death rate is a balance check, not a covariate.
17. Analysis keys on `requested_seed`. A realised-seed mismatch is flagged and retained.
18. Prompt, engine, temperature, token-budget, model, or protocol drift ends the current confirmatory set. Later games cannot be pooled across a drift boundary.
19. No ablation is allowed inside a confirmatory run.
20. Jev rows in confirmatory games are prohibited. A `jev_stub` value is a protocol deviation to be reported rather than a game exclusion from the record.
21. Every reported value is traceable to run tag, git sha, and requested-seed range, with a denominator and clustering unit stated with each table.

## 13. Blinded delay judge

Mechanical delay quality counts a delay as good when the plurality target is innocent. It is an honest outcome measure, but a village that delays randomly may receive credit for lucky avoidance. A blinded validation sample is therefore required.

The sample is 120 game-days, **assumed** design: 60 reasoned delay game-days, stratified as 20 per primary arm where available, and 60 game-days where a plurality target was actually lynched, sampled with seed 20261106 after the primary dataset is locked. If an arm has fewer than 20 eligible delay days, all are taken and the shortfall is reported rather than silently reallocated. The judge receives history truncated at the end of discussion before the vote. Arm, role, winner, actual votes, plurality correctness, delay cause, and post-vote history are removed. Speakers are renamed. The judge reports the most suspicious player, whether evidence justified lynching that player, whether delay was recommended, and turn ids relied on.

A human annotator who did not run the games is the first choice. Their cost is Rs.0 cash and 2 to 4 hours, **assumed**. If an LLM fallback is required, it must be from a different model family from the backbone. This family-separation requirement supersedes any earlier same-backbone fallback. Estimated fallback cost is Rs.5 to Rs.6, **derived/assumed**, for 120 calls. A human audit of at least 20% of the LLM-judged sample is required if the LLM judge is used.

Judge-rated delay appropriateness is an exploratory validation secondary and never replaces mechanical delay quality. The two are presented together with the explanation that mechanical scoring uses the outcome while judge scoring uses only evidence available before the vote.

## 14. Claim wording

Confirmatory claim wording for the primary appears in §5. Calibrated claim wording appears in §6. The baseline claim is restricted to the following sentence:

"In confirmatory village-team games with mafia fixed as CoT, the DMN/TPN/EVT village was compared with a CoT village and with a compute-matched CoT-x3 village. No confirmatory claim is made against ReAct or Constitution. Focal-seat pilot results for CoT, ReAct, and Constitution are reported in the appendix as exploratory and are not used to support any superiority claim."

Any use of the plural word "baselines" to describe a confirmatory result is a wording error under this pre-registration.

## 15. Deviations and audit

Every deviation from this document is logged with run tag, git sha, requested seeds, reason, and whether the affected games remain confirmatory. Cost inputs remain **assumed** until measured in the calibration batch. The freeze tag remains pending and will be created only in a later approved step.
