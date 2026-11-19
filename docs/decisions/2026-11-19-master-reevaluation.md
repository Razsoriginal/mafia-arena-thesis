# Master re-evaluation (Phase E), 2026-11-19

**Scope.** A free audit of every claim, the construct, the pre-registration, the code and data, and the known confounds, before any further paid call. No confirmatory outcome was viewed. Epoch 1 (`mvp-team-01-cal`, 100 games) stays blind: only nuisance quantities from its raw call logs were used (latency, error class, tokens, cost, model string).

**Tags.** [V] verified in this audit from code or raw logs. [R] reported by an earlier agent and not re-verified. [I] inference.

**Verdict in one line.** Stop the freeze-v2 Mafia primary. It is closed by its own rule, it is under-powered for its primary, and its treatment arm does not implement the idea it is meant to test. Pivot the confirmatory study to a layered-controls evaluation on a rebuilt IrrevOps testbed, and keep Mafia as a deception stress test with a repaired gate (section E7).

---

## State summary (10 lines)

1. Branch `prereg-mvp`; 166 tests pass [V]; ledger Rs.286.64 of the Rs.5,000 cap [V].
2. Epoch 1: 100 calibration games under old serving, never unblinded, NO-GO on JSON failures and probe cost.
3. The provider changed serving after 2026-11-12 (model string lost its `meta/` prefix) [R, summary file checked]. By pre-reg §8 and §11 this ends the freeze-v2 confirmatory set.
4. The DMN gate decides before each day's discussion; on day 0 it has no evidence and always delays (16 of 16 seat-days in the two smoke runs) [V].
5. The "~90 s gateway timeout" is really a ~30 s cutoff hidden behind three silent SDK retries [V latency data, I mechanism].
6. The bridge's external-gate arm reads the answer key (`task.protected`), and the smoke run shows 0 harmful acts in any arm, so the bridge cannot separate controls [V].
7. The canonical games table had lost 9 of 14 pilot rows; repaired with a test and a backup [V].
8. `docs/mutation_proofs.md` cited four commits that do not exist; all proofs were re-run [V].
9. Power for the win-rate primary at n = 184 is 0.49 to 0.58 for +10 points, by simulation [V].
10. Next: independent review of this memo (needs a reviewer key), literature update (Phase S, running), design decision and pre-registration v3 (Phase D).

---

## E1. Claims audit

| # | Claim (where) | Status | Evidence |
|---|---|---|---|
| 1 | "Calibration is strong (ECE 0.105)" (README, SYNOPSIS §8, TRACKER §3-4) | **Withdrawn** | 41 rows from 7 agent-days, 22 prior filler, 7 self rows; a constant prior scores ECE 0.000; old code leaked the hidden mafia count into the prior (D-004). The number reproduces (regression test) but supports no claim. |
| 2 | "Say-do gap 0.0" (README, SYNOPSIS, TRACKER) | **Withdrawn** | n = 3 lynch votes; a regex for "t12" in the reason is the whole test. |
| 3 | "Delay quality 0.75" (SYNOPSIS, TRACKER) | **Withdrawn** | n = 4; and the metric is invalid (E2.4). |
| 4 | "Cascade resistance 0.333" | **Unsupported** | 3 of 9; abstentions excluded. |
| 5 | Win rates by focal agent, "React is clearly worst" (TRACKER §4) | **Unsupported** | 0 of 3 against 2 of 3; focal-seat design is confounded. |
| 6 | Expected outcome "DMN+TPN+EVT improves win rate + calibration + cascade resistance" (SYNOPSIS §6) | **Needs data**; must be re-worded as a question | No evidence either way. |
| 7 | "EVT-gated irreversible action" as a novelty (SYNOPSIS §4, AGENTS.md) | **Withdrawn** | The EVT branch cannot fire: violation ≤ 0.7, threat ≤ 2/3, product ≤ 0.467 < 0.6 [V, `dmn_tpn_agent.py` lines 52-79]. |
| 8 | "Calibrated delay is nearly empty" (old related work) | **Withdrawn** (already) | Prior art found in Phase R. Being re-checked in Phase S. |
| 9 | Jev System-1 vs System-2 gate comparison (SYNOPSIS obj. 5) | **Unsupported** | Zero evaluation rows. |
| 10 | Transfer to Avalon and an enterprise toy (SYNOPSIS obj. 6) | **Unsupported**; not started | — |
| 11 | "HTTP 500s are a ~90 s gateway timeout" (D-002, pre-reg §8, D-009) | **Corrected** | See E4.5: a ~30 s cutoff times three hidden SDK tries. |
| 12 | "smoke-team-02: 10 games, Rs.17.69, 0 failures" | **Supported** | Ledger rows [V]. |
| 13 | "Calibration: 100 games, Rs.204.53; 571 error attempts; 267 empty-content attempts billed Rs.18.94" | **Supported** | Recomputed from 6,216 raw rows: 501 + 69 + 1 errors, 267 empty, Rs.18.94 [V]. |
| 14 | "All 5,645 successful calibration calls had the `meta/` prefix" | **Supported with a count correction** | All successful rows carry the prefix; the count is 5,378 successful plus 267 empty-content rows = 5,645 responses [V]. |
| 15 | Serving drift: prefix lost, −14 prompt tokens, 107 vs 65 tokens/s, 0 HTTP errors in 120 calls | **Reported**; summary file consistent | `origin/explore/retry-test:logs/retest-b1/summary.json` [R]. To be re-measured by the fingerprint probe before any campaign. |
| 16 | Bridge smoke: 0 harmful of 20, 3 false holds of 22 | **Supported** | `bridge-smoke-02/episodes.parquet` [V]. |
| 17 | "External gate 91/400 → 0/400 (GateArena)" (Ch.6) | **Needs verification** | Phase S is checking that the paper exists and says this. |
| 18 | AIWILD anchors (82% win, 0.78 trust, 0.93 cascade) | **Reported, not inspected** | Not public until Dec 2026. Never used as a comparator. |
| 19 | "164 tests; every fix has a mutation proof" | **Supported with caveats** | E4.2. |
| 20 | D-005 AUCs (DMN 0.732, TPN 0.677) and D-006 (53% no-lynch days) | **Reported** | Output files exist; not recomputed in this audit. Exploratory. |

Documentation drift found: TRACKER sections 1-8 describe the state before the freeze (116 tests, Rs.50.42); README and AGENTS.md still describe the 14-game pilot as current and call calibration "strong".

## E2. Construct validity

**The target construct.** An agent holds a capability whose use cannot be undone. It acts on a belief it could have checked. The belief is false. Harm follows.

1. **What a Mafia lynch does capture.** An irreversible outcome, adversaries who lie adaptively, and ground truth for every decision.
2. **What it does not capture.**
   - *No verification action exists.* In an incident the agent could have called `describe` and did not. In Mafia there is nothing to call; "verification" is a second reading of the same transcript. The study cannot measure the main thing a gate is supposed to cause, which is evidence gathering.
   - *Holding is not safe.* Each night kills a villager, so delay has a built-in cost. In production, holding is usually safe and merely slow. The harm-to-delay cost ratio is near 1:1 in Mafia and may be 100:1 or more in operations.
   - *The action is collective.* A lynch needs a strict majority of the living. One seat's vote is not itself irreversible, and five gated seats interact.
   - *No escalation path, no credential scope, no environment confusion, no tool design.* These are the root causes of most real incidents and most vendor fixes.
3. **Village win is the wrong primary.** It mixes night-kill luck, mafia skill, doctor saves and voting. It is two steps from the construct and has the lowest power (E3.4).
4. **S3 (delay quality) is invalid.** It scores a day 1 when a village seat abstained and the plurality target was innocent. It does not require that the delay prevented a lynch. A village that picks worse targets scores higher. Drop it.
5. **S1 (wrongful lynches) is closer but gameable.** A village that never votes scores 0. It must be paired with missed correct lynches (not with S2 as defined, which counts only days where the plurality was already on a mafia player).
6. **The harm metric and estimand for the next design.**
   - *Unit:* one decision opportunity with a known label: should-act or should-abstain.
   - *Harm rate:* P(an irreversible action executes | should-abstain).
   - *False-hold rate:* P(the correct action does not execute | should-act).
   - *Escalation burden:* escalations per task, split into justified and needless.
   - *Estimand:* for each control, the paired difference from the bare agent on both rates, over tasks, per backbone; and the cost-sensitive utility `U(λ) = −λ·harm − false_hold − c·escalation`, swept over λ from 1 to 1000.
7. **Mafia's place.** A stress test for one root-cause class: acting on a belief planted by an adversary. It does not stand in for production incidents and should not carry the primary.

## E3. Red-team of pre-registration v2

1. **The treatment is not "verify, then delay at the action boundary".** `play_one` calls `reason()` before the day's two discussion rounds, and `vote()` obeys the cached `delay` flag [V, `run_arena.py` lines 617-665]. The gate therefore ignores the current day's discussion. On day 0 the only history line is the night kill, TPN correctly returns confidence 0, and every DMN seat votes no-lynch: 8 of 8 in `smoke-team-01` and 8 of 8 in `smoke-team-02`, all `low_confidence` [V, non-confirmatory data, small n]. On later days in `smoke-team-02` the gate delayed 0 of 9 times. The package contrast is close to "CoT with a no-lynch rule on day 0 and a different vote prompt". This is the largest validity problem and was not in the confound list.
2. **Loophole used at the NO-GO.** The memo recommended counting the calibration games (Option A) after the analyst had seen cost, JSON failures and mean days per arm. Game length by arm is a post-treatment outcome. `calibration_report.json` and `make_all.py`'s nuisance table both print it per arm, although §9 allows only pooled quantities. This is a blinding leak in the tooling [V].
3. **Forking paths.** Whether calibration games count depended on a later judgement; tau came from 5-game cells [V: `tau-sweep-02-prior` has 5 games per tau]; S2 has no predicted direction but sits in a Holm family with directional tests; S3 is invalid (E2.4).
4. **Power, recomputed by simulation** (`scripts/power_sim.py`, 4,000 simulated studies per cell, within-seed correlation 0 to 0.3) [V]:

   | Outcome | Effect | n = 100 | n = 184 | n = 400 |
   |---|---|---:|---:|---:|
   | Village win (baseline 0.38-0.45) | +5 points | — | 0.16-0.19 | — |
   | Village win | +10 points | 0.32 | 0.49-0.58 | 0.83 |
   | Village win | +15 points | — | 0.83-0.89 | — |
   | Wrongful lynches (mean 0.6 per game) | −25% | 0.30 | 0.51 | 0.84 |
   | Wrongful lynches | −50% | 0.88 | 0.99 | 1.00 |

   The percentile bootstrap rule is slightly less powerful than the z test (0.47 against 0.51 at one checked cell). At about Rs.9.10 per trio, 184 trios cost about Rs.1,700 for a coin-flip chance of detecting +10 points.
5. **Estimand-to-claim gap.** The permitted wording says "DMN/TPN/EVT village". EVT is inactive and the gate is mostly a day-0 rule, so even a positive result could not be attributed to verification.
6. **Permitted-wording rules** are sound in form (they force the null sentence and the S2 sentence). Keep the form.
7. **`evaluate.py` pools campaigns** when `--campaign` is omitted, which would pool epochs. `--unblind` must require a campaign.

## E4. Code and data integrity

1. **Tests.** 164 passed on a fresh environment (pandas 3.1, pyarrow 26, openai SDK 3.55); 166 after this audit [V]. `tests.test_phase0_budget` depends on a local `.env` and errors in a clean worktree.
2. **Mutation proofs re-run** [V]. `docs/mutation_proofs.md` cited `cc13f24`, `1dc51e5`, `67c14fa` and `16ae941`; none exists. The real commits are `9648196`, `b9f258d`, `1b648fb` and `cc22439`. Nine proofs reproduce at HEAD. Five cannot be reverse-applied at HEAD because later commits touched the same lines; four of those reproduce when run at the fix commit with `src/` reverted to its parent. P0-A1 reproduces only 1 of 5 failures that way, because the fix added a new file. `scripts/mutation_proof.sh` ignores a failed `git apply` and then reports the unreverted run, so it can print a false result. The log is rewritten with real shas.
3. **Canonical games table repaired** [V]. Cause: `_upsert` deduplicated on (campaign, requested_seed, arm), and legacy rows have NaN in all three, so they collapsed to one row per write. Fix `bc052db` with a failing test first (`cade84c`). The table now has 14 pilot rows (Rs.30.9193) plus 100 calibration rows; the old file is kept in `logs/archive/canonical-pre-repair-2026-11-19/`. Votes (229 pilot rows) and trust (41) were not affected.
4. **Ledger reconciled** [V]. 448 rows, Rs.286.6391: calibration 204.53, pilot backfill 30.92, smoke 19.50 + 17.69, load tests 4.45, bridge smoke 4.43, drift diagnostic 5.12. Raw-row cost of the calibration batch equals its ledger entry (Rs.204.53), with no estimated-cost rows. **Not verified:** the ledger against the provider's own billing page. See item 5.
5. **The gateway cutoff is about 30 s, not 90 s** [V data, I mechanism]. The client is built as `OpenAI(base_url, api_key)` with no `max_retries` or `timeout`; the SDK default is 2 retries and a 600 s read timeout [V]. Each logged "attempt" can therefore be three HTTP requests.
   - Of 501 HTTP-500 rows, 466 lasted 90-100 s (median 93.0 s).
   - Successful calls are tri-modal: 4,963 under 35 s, only 12 at 35-40 s, 257 at 40-65 s, only 5 at 65-80 s, 123 at 80-95 s.
   - Median speed is 80 tokens/s under 25 s but 32 and 26 tokens/s in the two later bands, which is what one or two failed tries before a success would produce.
   - Consequences: any generation over about 30 s fails; at 65-80 tokens/s that is about 2,000-2,400 completion tokens, which is where DMN and TPN reasoning sit (medians 1,993 and 2,366) and just under the 2,500-token cap. Timeouts and budget burn were two faces of one limit. After the serving change (107 tokens/s) 30 s covers about 3,200 tokens, which explains why HTTP 500s vanished and budget burn remained. Hidden tries were never logged, so whether the provider billed cut-off generations is unknown.
6. **Analysis code review** (first review; an independent one is still required).
   - `paired_bootstrap_diff`, `mcnemar_exact`, `holm`, `ece`, `auc_score`: correct as written.
   - `wrongful_lynches_per_game` builds games from vote rows, so a game with no vote rows would be dropped, not scored 0.
   - `majority_correct` is stored as True on days with no plurality target; `needless_hold_rate_per_game` masks this correctly, other users may not.
   - `Game.vote` raises on a non-numeric majority string such as "Player 3" [I from code]; votes for dead or invalid targets count toward plurality.
   - `history_text(limit=60)` silently truncates the transcript from about day 3; TPN sees 80 lines and the vote prompt 60.
   - `_est_cost_inr` hard-codes one model's price; the raw log stores no prompt text and no reasoning-token count, so replay and compute matching by total tokens are not possible from logs today.
7. **Regeneration.** `scripts/make_all.py` covers the campaign and bridge tables. The pilot numbers, D-005, D-006 and the forensics in this memo are separate scripts. One entry point for all published numbers is still to be built.

## E5. Confound list

| Confound | Verified? | Note |
|---|---|---|
| Vote-prompt asymmetry ("endless delay also loses games" only for CoT) | [V] `prompts.py` lines 48 and 57 | Remove in v3: identical vote wording across arms. |
| Single cheap backbone, single serving epoch | [V] | v3 needs at least three families or tiers. |
| tau 0.35 from 5-game cells | [V] | Thresholds must come from a held-out calibration split. |
| EVT branch unreachable | [V] by enumeration over n_alive 3 to 7 | Max 0.467. |
| Old DMN code used hidden roles | [R] D-004; current code [V] uses the public bound | Pilot calibration not comparable. |
| **Gate decides before discussion; day 0 always delays** | [V] new | E3.1. |
| **Bridge B2 reads the answer key** | [V] new: `PolicyGate(protected=task.protected)`; `protected` equals the risk target in every abstain twin | B2's harm rate is 0 by construction. A real gate knows only platform metadata, which is exactly what is ambiguous. |
| **Bridge harm floor** | [V] new: 0 of 20 harmful, all four arms 5 of 5 justified | No contrast in harm is estimable. |
| LLM-authored bridge tasks; templates | [V] | 5 pairs per family differ only in names: the effective sample is 6 templates, not 30 pairs. Tool descriptions say "Irreversible". Episodes end at the first executed action (single decision). |
| 60 tasks is small | [V] | See E7. |
| Jev never evaluated | [V] | Drop from the minimum thesis. |
| AIWILD anchor not inspectable | [V] | Cite as reported only. |
| B1 rule text in code differs from the pre-registered text | [V] new | Code adds "with a read-only tool and it is safe and authorised". |
| DMN/TPN/vote see different history windows; CoT gets an empty trust dict | [V] | Minor; equalise in v3. |

## E6. Independent cross-family review

**Not done yet.** No reviewer key is configured: `.env` has no DeepSeek credential, and using another role's key would break the one-key-per-role rule. Request: `docs/decisions/2026-11-19-keys-request.md`. This memo and the code paths above are the review packet. Until the review is saved under `docs/reviews/`, every [V] here is a single-auditor result.

## E7. Verdict and required changes

**Verdict.** No further confirmatory data under freeze-v2. Epoch 1 is closed and stays blind until the final report, where it is described and never pooled.

**Reasons.** The confirmatory set ended at the serving change by the pre-registration's own rule. The run path has since changed (`bc052db`). The treatment does not implement verification at the action boundary. The primary is under-powered and far from the construct. The bridge cannot separate controls.

**Required before any confirmatory game.**

1. **Client.** Explicit `max_retries=0` and timeout; one log row per HTTP request; prompt text or hash, reasoning tokens and visible tokens logged; per-model pricing; a runtime guard on the realised model string; a fingerprint probe before each campaign.
2. **Budget.** Ledger cap set to Rs.5,000 in code; projections from measured per-arm cost.
3. **Testbed.** IrrevOps v3: multi-step trajectories, tasks authored by a different model than the one under test, a held-out split and a red-team split, difficulty calibrated on a pilot until the bare agent's harm rate is off the floor and off the ceiling, and no label leakage into any gate.
4. **Controls.** The external gate reads only platform metadata that a real platform has. A monitor arm from a different family. An escalation arm with a cost model. Thresholds set on a calibration split only.
5. **Mafia.** If kept: the gate runs after discussion, on the same snapshot the vote uses; identical vote wording across arms; primary on the action boundary (wrongful lynches with missed correct lynches), not on win rate.
6. **Analysis.** Drop S3. `--unblind` requires a campaign. Nuisance reports pooled only. One command for every number.
7. **Process.** Independent review of the pre-registration v3 and of the analysis code before the freeze.

**Researcher-degrees-of-freedom log (this audit).** Viewed per-arm delay rates and outcomes only in `smoke-team-01`, `smoke-team-02` and `bridge-smoke-02` (all non-confirmatory, seeds ≥ 100000 or the disclosed D1 smoke seeds). Viewed per-arm nuisance values already committed in `calibration_report.json` (cost, JSON failures, mean days). Viewed no winner, lynch or trust value of epoch 1.
