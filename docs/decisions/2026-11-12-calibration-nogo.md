# Calibration decision: NO-GO pending a decision (2026-11-12)

**Campaign:** `mvp-team-01`. **Run tag:** `mvp-team-01-cal`. **Seeds:** 5000–6900, 20 trios, all 5 arms (100 games, 0 discarded).
**Inputs:** `logs/calibration_report.json` (nuisance only) and the raw logs under `logs/runs/mvp-team-01-cal/raw/`. No outcome by arm was computed or viewed.
**Status:** The primary is **paused**. `logs/calibration_go.json` has **not** been written.

## 1. The five v2 GO conditions (PREREGISTRATION §9)

| # | Condition | Measured | Result |
|---|---|---|---|
| 1 | Pooled JSON failures ≤ 0.20 per game | **0.31** (31 in 100 games) | **FAIL** |
| 2 | Mean length ≥ 1.5 days | 3.10 | pass |
| 3 | Probe cost ≤ Rs.0.35 per probed game | **Rs.0.446** (60 LLM-arm games) | **FAIL** |
| 4 | v2 n rule gives n ≥ 171 | n = 184 (projection below) | pass |
| 5 | No change since `freeze-v2` | `verify_campaign_identity.py`: IDENTITY OK (1 sha); `git diff freeze-v2` on `src/` touches only `src/bridge/` and `src/explore/` (off the run path) | pass |

The v2 GO rule needs all five, so no GO may be written. As §9 requires, the analyst stops here.

**n-rule projection** (condition 4; **derived** from calibration costs only):
- Ledger at decision, L = Rs.281.52. The reconcile dry run found a gap of Rs.0.00.
- Kept trio cost, T = 3.434 + 2.641 + 3.026 = Rs.9.10. Discard share d = 0.
- Null arms N0 = 60 remaining seeds × Rs.1.126 = Rs.67.5.
- L + 164·T + N0 + 60 = Rs.1,902 ≤ 2,000, so n = 184, with about Rs.98 of slack before headroom.

## 2. Triage of the JSON failures (nuisance data only)

The source is `llm_raw.jsonl` across all 100 task directories.

- **All 31 failures were calls that used up all 8 attempts on provider HTTP 500.** These are the ~90 s gateway timeout of D-002. One was an empty-content response on the final attempt.
- **Zero were unparseable JSON**: no failure reached the repair step and still failed.
- **By purpose:**
  - night action: 21;
  - DMN reasoning: 7 (4 `dmn_reason`, 3 `tpn_reason`);
  - CoT-x3 vote: 2;
  - probe: 1.
- **Per arm** (failures per game): DMN 0.85, CoT 0.35, CoT-x3 0.30, random 0.05, majority 0.00.
- Retry exposure follows generation length. The share of first attempts that needed a retry was 42.9% for `tpn_reason`, 26.7% for `dmn_reason`, 12–21% for night actions, and under 1% for speech.

**Reading.**
- The failure mode is the provider timing out long reasoning generations. It is not the model's JSON behaviour.
- P0-R1 and P0-R2 cut the failure rate per game from 1.5 (smoke-team-01) to 0.31. That is still above the threshold, which was set against the pilot's 0.07.
- Each failure falls back to the safe default (DELAY, or a default night action). The DMN arm takes more fallbacks, because its reasoning calls are the longest.
- In 7 of 382 DMN reasoning calls (1.8%), the fallback was a forced delay rather than a decision. This is a treatment-side asymmetry that the analysis must disclose.

**Probe cost.**
- Rs.0.446 per probed game against the Rs.0.35 limit. The smoke run had already flagged this risk (Rs.0.41).
- §9's probe rule says to "reduce n if the budget requires it". The n rule above shows it does not.

## 3. Options (decision required before any resume)

**A. No correction; count the calibration games under the recorded rule.** (Analyst recommendation.)
- §9 provides for this case: "If no correction is made, games may count after approval under the recorded rule."
- The run continues at trio 20 with the frozen code, and n = 184 is projected inside the cap.
- Two deviations are recorded before any outcome is seen:
  - **D8.** JSON failures were 0.31 per game against the 0.20 threshold, caused by provider timeouts. Probe cost was Rs.0.446 against Rs.0.35, with no reduction in n because the budget allows it.
  - **A pre-specified sensitivity analysis.** The primary and the S1–S3 contrasts are repeated excluding seed-trios in which any LLM-arm game had a fallback. The per-arm fallback count is reported next to every outcome table.
- Risk: the DMN arm's extra forced delays bias it toward holding. This is disclosed rather than corrected.

**B. Correct the run path, then discard calibration and restart the seed list.**
- Possible corrections: a longer client timeout or more attempts for reasoning purposes only, or a lower `max_tokens` for night and TPN calls. Either changes the run path, so the change needs a new freeze and a new calibration batch.
- Projection (**derived**): restarting from L = Rs.281.52 with 80 null seeds gives n ≈ 172, including the new calibration. Any added cost from the fix, its smoke test or a higher reasoning budget pushes n below 171, and the primary becomes estimation-only.
- A timeout of the gateway, not the client, may not be fixable from our side. D-002 found that streaming sends nothing while the model reasons.

**C. Stop the Mafia primary as confirmatory and run it estimation-only.** Not recommended while A remains admissible under §9.

## 4. Next steps after the decision

- **If A:**
  1. Add D8 and the sensitivity analysis to §15 of the pre-registration and commit them.
  2. Write `logs/calibration_go.json` with the campaign, `calibration_report_sha256`, `created_at` and `approved_by`.
  3. Resume from trio 20. The command is in `TRACKER.md`.
- **If B:** open a fix branch, write a failing test first with a mutation proof, then smoke-test and re-freeze as `freeze-v3` with a new campaign id.
