# Discoveries (non-confirmatory data only until the primary is locked)

Each entry gives the question, data and n, method, result, confidence, caveats, and whether a paid replication is needed. Figures are tagged **measured**, **derived** or **assumed**.

---

## D-001. The EVT delay branch is structurally unreachable

- **Question.** Do any delays come from the EVT (expectation-violation × threat) branch, as opposed to low confidence?
- **Data.** Every trace on disk: `logs/**/trace_*.json`, 186 DMN traces (pilot, sweeps, smoke).
- **Method.**
  - Count the logged `delay_cause` values.
  - Bound the formula analytically.
    - `violation` is in {0.2, 0.5, 0.7}.
    - Before the fix, `threat` was `m/o` computed from the hidden roles. Under the public bound used from P0-E2 on, it is `min(2, (n−1)//2) / (n − m)`.
    - With 2 mafia in a live game, threat is at most 2/3.
    - So `evt ≤ 0.7 × 2/3 = 0.467`, which is below `EVT_THRESHOLD = 0.6`.
- **Result** (**measured**): low_confidence 99, None 68, json_failure 17, evt_threshold **2**. Both EVT firings had threat = 1.0. That value only occurs in a post-parity state that the engine should already have ended, the bug fixed in P0-E1.
- **Confidence.** Certain (analytic bound, matched by the logs).
- **Consequence.**
  - Under the frozen constants, the confirmatory gate is a verified-confidence threshold gate.
  - The pre-reg v2 §8 discloses this, and the constants are not changed.
  - An "EVT-live" variant (for example a threshold of 0.4, or threat on a 0–1 scale reaching 1 at m = o − 1) is exploratory only.
- **Paid replication needed?** No for the finding itself. An exploratory EVT-live cell (seeds ≥ 100000) would test whether a working expectation model changes delay behaviour; it is a discovery-lane candidate.

## D-002. The provider "HTTP 500s" are a ~90 s gateway timeout, not JSON-mode failures

- **Question.** What drove 15 JSON failures in 10 smoke games, against 0.07 per game in the pilot?
- **Data.**
  - `logs/runs/smoke-team-01/raw/task-*/llm_raw.jsonl`: 666 attempt rows, 134 error rows.
  - `logs/runs/loadtest-500diag/calls.jsonl`: 36 single-attempt calls on 12 paired prompts.
  - Stream probes in the same folder.
- **Method.**
  - Group attempts into calls.
  - Estimate attempt duration from timestamp gaps minus the logged backoff.
  - Paired diagnostic across JSON at 0.0, plain at 0.0 and JSON at 0.7, plus streaming replays.
- **Result** (**measured**).
  - All 116 "Error code: 500" attempts in the smoke run lasted at least 91.7 s (median 95.3 s, n = 82 measurable). Successful first attempts had a median gap of 14 s.
  - All 15 JSON failures were calls with five consecutive 500s.
  - 500s never hit plain-text speech calls (0 of 234), which are shorter generations.
  - In the diagnostic, all 4 failures were 500s at 92.2–93.0 s and occurred in all three conditions.
  - JSON at 0.0 was slower than plain at 0.0 on 9 of 12 paired prompts (median +11 s).
  - Streaming sends no bytes while the model reasons: first chunk at 39 s, only 2 reasoning chunks. So streaming cannot keep the connection alive.
- **Confidence.** High for "gateway timeout on slow generations". Low, at n = 12, for the size of the JSON-mode slowdown.
- **Consequence.**
  - P0-R1: 8 attempts with 10–120 s jittered backoff.
  - P0-R2: drop JSON mode on the retry after a timeout.
  - The JSON-failure threshold of 0.20 per game is unchanged. The re-smoke tests whether the fix suffices.
- **Paid replication needed?** Only the re-smoke, which is already planned.

## D-003. A resume could bypass the calibration GO gate (old loop)

- **Question.** Is the GO gate enforced on every path?
- **Method.** An integration test with a mocked runner.
- **Result.** In the pre-P0-S2 loop, `--trios 21 --resume` after a 20-trio calibration batch ran trio 20 without a GO. The trio index was the position in the resume-filtered list, so it came out as 0. This is confirmed by the mutation proof of `tests/test_phase0_window.py`. Fixed with seed-derived indices.
- **Confidence.** Certain. No confirmatory data was affected, since no confirmatory game had run.

## D-004. Ground-truth leak to the DMN arm (v1 code)

- **Question.** Does any agent see hidden state?
- **Method.** Code review.
- **Result.** `DmnTpnAgent.reason()` counted living mafia from the role map. That count set the base-rate prior in DMN trust, which was fed into the cited-vote prompt, and the EVT threat. The pilot and smoke DMN trust values therefore carried hidden information; for example, the prior changed when a mafia player died. Fixed in P0-E2 using the public bound.
- **Consequence.** The pilot decision-trust calibration (ECE 0.105) is not comparable to v2 and may be optimistic. The thesis must say so.
- **Confidence.** Certain about the leak. Its size is not measured.

## D-005. TPN "verification" lowers discrimination slightly and shrinks confidence almost uniformly (exploratory)

- **Question.** Do the DMN/TPN fields predict mafia? Fields: DMN confidence, TPN revised confidence, `contradiction_found`, exformation volume.
- **Data.** All non-confirmatory DMN traces on disk that join to a games table: 11 campaigns, 35 games, 332 hypotheses. Pilot, sweeps, trust-prior runs and smoke-team-01 are included. Only village (non-mafia) reasoning agents are counted, and self-suspicion is excluded. Output: `logs/explore/d005_exformation_auc.json`. Code: `src/explore/exformation_auc.py`.
- **Method.** AUC with the score treated as P(mafia). The label is that the hypothesised suspect is mafia. CIs come from a 2,000-replicate bootstrap clustered by game. The DMN−TPN difference is paired on the same hypotheses.
- **Result** (**measured**):

  | Feature | AUC | 95% CI (game-clustered) | n rows / games |
  |---|---:|---|---|
  | DMN confidence | 0.732 | [0.647, 0.791] | 332 / 35 |
  | TPN revised confidence | 0.677 | [0.623, 0.721] | 326 / 34 |
  | TPN `contradiction_found` | 0.499 | [0.458, 0.539] | 326 / 34 |
  | number of exformation items | 0.514 | [0.478, 0.548] | 332 / 35 |
  | exformation characters | 0.548 | [0.490, 0.601] | 332 / 35 |

  - Paired DMN−TPN AUC: **+0.052 [0.009, 0.095]**.
  - TPN − DMN mean confidence shift: −0.209 for true mafia and −0.247 for innocents.
- **Reading.**
  - Verification moves confidence down by about the same amount for guilty and innocent suspects, and it slightly worsens ranking.
  - Since the gate delays when the top revised confidence is below 0.35, much of the DMN arm's delaying plausibly comes from this near-uniform shrinkage, not from selective doubt.
  - `contradiction_found` and exformation volume carry no signal at this n.
- **Confidence.** Moderate for the AUC levels. Low to moderate for the paired difference, whose lower bound is near zero.
- **Caveats.**
  - Mixed code versions (pilot, focal and team designs).
  - The suspects were pre-selected by DMN (base rate 0.47 against a 2/6 prior).
  - The hidden-role leak (D-004) affected the trust prior, not these fields.
  - A "contradiction" may cut either way.
- **Paid replication needed?** No new run. The confirmatory DMN traces will contain the same fields. A pre-specified within-DMN replication (the same AUCs and the paired difference) is added to the post-lock exploratory plan. It is run only after `primary-locked`, because it uses the outcome labels of confirmatory games.

## D-006. Games are short because most days fail to reach a strict majority while nights keep killing. The day cap rarely binds.

- **Question.** Why are games short, and would a cell with a 7-day cap help?
- **Data.** Histories of 106 non-confirmatory games across 11 campaigns (`logs/runs/*/raw/history_*.parquet`), pooled with no arm comparison. Output: `logs/explore/d006_game_length.json`. Code: `src/explore/game_length.py`.
- **Result** (**measured**, pooled):

  | Quantity | Value |
  |---|---|
  | Mean day-votes per game | 2.95 |
  | Days ending in no lynch | 53% |
  | Lynches per game | 1.39 |
  | Lynches that hit an innocent | 44% |
  | Games with a night-0 kill | 80% |
  | Doctor save rate per night | 33% |
  | Winners | mafia 59%, village 38%, draw 3% |
  | Games that hit the 5-day cap | 3 of 106 |

- **Reading.**
  - With both mafia alive, three innocent removals (night kills plus wrongful lynches) end the game.
  - Lynching needs 4 of 6 or 7 votes, and the mafia supply 2 of them, so the village must coordinate 4 of its 5 seats. On most days it does not.
  - The cap is almost never binding. **A 7-day-cap cell is not recommended:** it would change at most about 3% of games.
  - The pilot's "2.14 days" in TRACKER is a zero-based index. The count convention gives about 3.
- **Confidence.** High for the pooled mechanics. Code versions are mixed (the pre-P0-E1 parity day inflates length slightly).
- **Paid replication needed?** No.

## D-007. The provider enforces about 20 concurrent requests per key; latency does not degrade below that

- **Data.**
  - `logs/runs/loadtest-conc-01/` (levels 1, 4, 8, 16; 46 calls; Rs.2.85).
  - `logs/runs/loadtest-conc-02/` (level 32; 32 calls; Rs.0.85).
- **Result** (**measured**).
  - Median latency was 22–28 s at levels 1 to 32.
  - Timeouts (~92 s 500s) occurred in 4–10% of calls at every level, with no trend.
  - At level 32, exactly 20 requests were accepted. The other 12 returned `429 Concurrency Limit Exceeded` within about 5 s.
- **Decision.** Primary runs use `--workers 6 --call-threads 3 --trio-window 2`. Speech is sequential, so most of the time each game has one request in flight. The worst-case peak is 18 if every game is in a parallel phase at once. Any 429 is retried with backoff under P0-R1. Concurrency is a timing parameter only (P0-S1 equivalence proof).
- **Confidence.** High for the limit (an explicit error message). Moderate for "no degradation", given small n per level.

## D-008. In the IrrevOps sandbox the backbone rarely acts harmfully but often over-holds (pooled smoke; exploratory)

- **Data.** `logs/runs/bridge-smoke-02/episodes.parquet`: task set v2, one pair per family, 4 arms, 1 repetition. 42 of 48 episodes ran before the lane cap (Rs.3.50).
- **Result** (**measured**, pooled over arms): harmful actions 0 of 20 should-abstain episodes; false holds 3 of 22 should-act episodes (13.6%); 0 parse failures. Per-arm results were not examined.
- **Reading.** Even with subtle cues, the agent tends to verify and escalate. This matches SteerBench-Work, where over-holding dominates over over-allowing.
  - The bridge's harm contrasts are expected to sit at a floor.
  - Its informative quantity is therefore the **false-hold cost** of each gate. Paired accuracy and the verification rate are also informative.
  - The tasks were *not* tuned further to provoke harm, because that would tune toward an effect.
- **Consequence.** The bridge was frozen at task set v2 (`bridge-freeze-v1`). The thesis must report the harm floor as a finding about this backbone and task framing, not as evidence that any gate works.
- **Cost.** About Rs.0.083 per episode (**measured**, n = 42), so the full cell of 480 episodes is about Rs.40 (**derived**).
