# Mutation proofs (Phase 0 and later)

A proof passes when the named tests FAIL with the fix reverted. Re-run in full on 2026-11-19 (Phase E4); an earlier version of this file cited four commit ids that do not exist (`cc13f24`, `1dc51e5`, `67c14fa`, `16ae941`).

Two methods:

- **At HEAD:** a throwaway worktree at HEAD with the fix commit's `src/` hunks reverse-applied (`scripts/mutation_proof.sh`).
- **At the fix commit:** used when later commits changed the same lines and the reverse patch no longer applies. A worktree at the fix commit, with `src/` checked out from its parent, so the tests are the fix commit's and the code is the pre-fix code.

`scripts/mutation_proof.sh` does not stop when `git apply -R` fails; it then runs the tests on unreverted code. Check for "patch failed" in its output before trusting a result.

| Fix | Fix commit | Tests | Method | Result with fix reverted (2026-11-19) |
|---|---|---|---|---|
| P0-L1 shared ledger, raw reconcile | `9648196` | tests.test_phase0_ledger | at fix commit | 6 of 6 fail (1 failure, 5 errors) |
| P0-B1 cap Rs.2,000 | `68f30b8` | tests.test_phase0_budget | at fix commit | 2 of 3 fail. One of the three errors even with the fix when no `.env` is present (environment-dependent test) |
| P0-E1 parity after night | `da79319` | TestParityAfterNightE1 | at HEAD | 1 of 1 fails |
| P0-E2 public-information prior | `77b401d` | TestPublicInfoPriorE2 | at HEAD | 2 of 2 fail |
| P0-E3 detective memory | `3259ca2` | TestDetectiveMemoryE3 | at HEAD | 1 of 1 errors |
| P0-R1 retry and timing | `b9f258d` | tests.test_phase0_retry | at fix commit | 3 of 4 fail (402-never-retried passes either way, as designed) |
| P0-S1 intra-game concurrency | `1b648fb` | tests.test_phase0_concurrency | at HEAD | 1 of 3 errors (`_pmap`); golden and 1-vs-8 pass on sequential code, as designed |
| P0-S2 trio window | `957aa51` | tests.test_phase0_window | at fix commit | 3 of 3 fail |
| P0-U1 `_upsert` never drops rows | `3b634e0` | tests.test_phase0_upsert | at HEAD | 2 of 3 fail |
| P0-R2 drop JSON mode after timeout | `3e1daeb` | TestTimeoutDropsJsonMode | at HEAD | 1 of 1 fails |
| P0-P1 probe cost per probed game | `ba7993b` | tests.test_phase0_probe_cost | at HEAD | 1 of 1 errors |
| P0-A1 action-boundary fields | `0cfef87` | tests.test_phase0_action_boundary | at fix commit | **weak:** 1 of 5 fails. The fix added `src/eval/action_boundary.py` as a new file, which the parent checkout does not remove |
| P0-K1 blinding in evaluate.py | `415295e` | tests.test_phase0_blinding | at HEAD | 2 of 4 fail |
| P0-K2 console prints no outcomes | `7a24649` | tests.test_phase0_blinding | at HEAD | 2 of 4 fail |
| E4-U2 `_upsert` keeps rows with missing keys | `bc052db` | tests.test_e4_upsert_null_keys | failing test committed first (`cade84c`) | 1 of 2 fails before the fix (keyed-replace passes either way, as designed) |

**Negative control for P0-S1** (reported by the earlier agent, not re-run): a deliberately wrong parallelisation, in which the speakers of a discussion round share one history snapshot, fails `test_threaded_matches_pre_concurrency_golden` while the 1-vs-8 test still passes. The golden fixture was generated from the sequential code at `b9f258d`, the parent of `cc22439` (`test(P0-S1)`).
