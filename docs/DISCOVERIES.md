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
