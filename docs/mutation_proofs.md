# Mutation proofs (Phase 0)

Method: `scripts/mutation_proof.sh <fix-commit> <tests>` checks out HEAD in a throwaway worktree, reverse-applies the fix commit's `src/` hunks, and runs the named tests. A proof passes when the tests FAIL with the fix reverted. Each test was also seen failing before its fix was written (test commit precedes fix commit).

| Fix | Fix commit | Tests | Result with fix reverted |
|---|---|---|---|
| P0-L1 shared ledger, raw reconcile, scoped projection | 377eba2 | tests.test_phase0_ledger | 6/6 fail (1 failure, 5 errors) |
| P0-B1 cap Rs.2,000 | `fix(P0-B1)` commit | tests.test_phase0_budget | 2/3 fail (refuse-above-cap passes either way, as designed) |
| P0-E1 parity after night ends game | `fix(P0-E1)` commit | TestParityAfterNightE1 | 1/1 fail |
| P0-E2 public-information DMN prior | `fix(P0-E2)` commit | TestPublicInfoPriorE2 | 2/2 fail |
| P0-E3 detective memory | `fix(P0-E3)` commit | TestDetectiveMemoryE3 | 1/1 error |
| P0-R1 retry/backoff + timing | 464f33c | tests.test_phase0_retry | 3/4 fail (402-never-retried passes either way, as designed) |
| P0-S1 intra-game concurrency | 9f4f1af | tests.test_phase0_concurrency | `_pmap` test errors; golden + 1-vs-8 tests pass on the reverted (sequential) code, as designed |

| P0-S2 trio window, seed-derived index | `fix(P0-S2)` commit | tests.test_phase0_window | 3/3 fail; the resume-vs-GO test FAILS on the old loop, confirming the old G7 bypass |

**Negative control for P0-S1.** A deliberately wrong parallelisation was injected in a throwaway worktree: the speakers in a discussion round all share one history snapshot. `test_threaded_matches_pre_concurrency_golden` FAILS on it, while the 1-vs-8 test still passes. So the golden comparison is what guards semantics. The golden fixture (`tests/fixtures/concurrency_golden.json`) was generated from the sequential code at 464f33c, the parent of a1a2530; that commit message's "2a?" is a typo for this sha.
