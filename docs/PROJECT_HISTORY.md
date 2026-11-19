# PROJECT HISTORY: what we tried, what we found, where we are (as of 2026-11-17)

Provenance tags: [V] verified from raw logs or code by a reviewer; [R] reported by an agent, unverified; [I] inference. Verify everything before relying on it.

## 1. Origin
- MSc AI thesis. Original title: "Exformation-Aware Dual-Process Agents for Deception-Resistant Decision-Making: From Mafia Arena to Enterprise Safety". Clean-room extension of a not-yet-public Fractal Cerebral (AIWILD) design: DMN-style imagined motives plus "exformation", TPN-style verification against cited evidence, an EVT delay gate, and an optional Jev System-One gate. Reported anchors from that paper (82% win, 0.78 trust, 0.93 cascade) are not inspectable until Dec 2026.
- Backbone: `meta/muse-spark-1.3-contributor` via AiCredits (OpenAI-compatible, `api.aicredits.in/v1`); list price about $0.10 / $0.20 per million tokens (a reasoning model).
- Stack: Python engine (`src/mafia/`), agents (`src/agents/`), evaluation (`src/eval/`), safety gate (`src/safety/`), IrrevOps bridge (`src/bridge/`).

## 2. Timeline
1. **Pilot.** 14 clean focal-seat games, Rs.30.92; baselines CoT, ReAct, Constitution. Retired to appendix history.
2. **Audit (Phase 1)** [V unless noted]. Focal-seat design compared one swapped seat against six CoT clones; a focal agent killed on night 0 gave zero data (2 of 4 DMN games). Trust calibration: ECE 0.105 rested on 41 rows from 7 agent-days; 22/41 rows were prior filler, 7/41 the agent rating itself; AUC 0.647 with 95% CI [0.444, 0.830]; a constant-prior null scored ECE 0.000. Cascade was 3/9 (0.625 if abstention counts); delay quality 6/8 pooled but DMN-only 0.50 vs CoT 1.00; abstention was not DMN-specific (Constitution 75%, DMN 57%, CoT 50%, ReAct 20%); EVT fired once in 404 traces; tau 0.35 came from 5-game cells; Jev had no evaluation rows (2 smoke rows only).
3. **Estimand decision.** Chose Design 3: village team vs fixed CoT mafia, paired seeds. Retired the focal-seat design; kept homogeneous self-play as a named alternative; mafia mirror out of scope. Power: at 80/arm unpaired, 0.24 / 0.48 / 0.74 for +10 / +15 / +20 points; 171/arm gives 0.80 for +15 (baseline about 0.45).
4. **Pre-registration v1** (tag `prereg-v1`). Arms `dmn_village`, `cot_village`, `cotx3_village` (compute-matched CoT with 3 vote samples); null floors `random_village`, `majority_village`; a trust probe in every arm; vote temperature 0.7 in every arm; seeds 5000+100*i; 184 planned trios; 20-trio calibration batch with GO/NO-GO rules; Rs.2,000 budget.
5. **Implementation and independent review.** A different-family reviewer (DeepSeek V4.1 Flash, read-only) found 46 issues in round 1 (per-invocation budget cap, non-atomic trios, gate gaps, audit-log gaps) and mutation-tested the fixes in round 2 (vacuous tests, calibration-pause bypass, campaign-scoped keys missing). All fixed with failing-test-first plus mutation proofs. `smoke-team-01`: 10 games, Rs.19.50, 15 JSON failures. `smoke-team-02` [R]: 10 games, Rs.17.69, 0 failures.
6. **Autonomous research agent (Opus 5.5), Phase R + 0** [R]. Survey and re-scope (Option B: keep Mafia as primary, add action-boundary secondaries S1 to S3, add the IrrevOps bridge). Withdrew "calibrated delay is nearly empty" after finding AgentAbstain, SteerBench-Work, CORA and SentryBench. Found the EVT branch structurally unreachable [V by arithmetic: 0.7 x 2/3 < 0.6]. Found D-004: the old DMN counted living mafia from the hidden role map, so the pilot's ECE 0.105 is not comparable. 52 commits, 164 tests; `freeze-v2` (prompts_sha256 d36b3140…, runpath_sha256 3fca1ecb…, freeze_git_sha ebfa6a1…).
7. **IrrevOps bridge** [R]. 60 incident-derived tasks (6 families x 5 pairs); arms B0 bare, B1 prompt rule, B2 external PolicyGate, B3 verify-delay. Smoke 1 hit a ceiling, so cues were made subtler (D7). Smoke 2 (42/48 episodes): 0 harmful acts of 20 should-abstain, 3 false holds of 22 should-act (13.6%). Full 480-episode cell about Rs.40. Tag `bridge-freeze-v1`. Single-step decisions only.
8. **Calibration `mvp-team-01-cal`.** 20 trios, seeds 5000 to 6900, 100 games, Rs.204.53, about 7.5 h. Outcomes were never viewed. NO-GO: JSON failures 0.31 per game vs limit 0.20 (DMN 0.85, CoT 0.35, x3 0.30, null arms near 0); probe cost Rs.0.446 vs limit 0.35. Mean length 3.10 days.
9. **Failure forensics** [V from 6,216 raw attempts]. 571 error attempts (501 HTTP 500, 69 HTTP 429, 1 connection); 93% of the HTTP 500s ended 85 to 100 s after sending (median 93.0 s), a gateway cutoff. A separate mode: 267 empty-content attempts (the model burned the 2,500-token budget on reasoning) were billed, Rs.18.94. First-attempt failure by purpose: dmn_reason 19.9%, night 9.8%, vote 2.8%, tpn 2.6%, speak 0.2%. After one failure, retries fail more (30.9, 50.7, 64.0, 78.0, 85.1%). Not tied to concurrency, not one outage window; token escalation was not the cause (escalated and non-escalated retries both fail about 50%). A first count of "768 HTTP 500s" came from `llm_errors.jsonl` and does not reconcile with raw rows: use raw rows.
10. **Serving-drift diagnostic** (branch `explore/retry-test`, d01345f, Rs.5.12) [R]. After Nov 12 the reply's model string lost the `meta/` prefix (all 120 probe calls; all 5,645 successful calibration calls had the prefix [V]); prompt tokens are uniformly -14 on identical text; tokens/s 107.5 vs 64.8; 0 HTTP errors in 120 calls. Behaviour looks like the same weights (night-0 action agreement new vs Nov 12 logged 13/18, vs itself 6/9; small n). The remaining failure on the 8 longest contexts: budget burn, 10/16 single attempts. Reasoning effort "minimal" gave 16/16 valid with about 90% less reasoning (a different regime). JSON mode off and temperature 0.3 did not help. Variants with a 1,500-token cap and a brief-thinking prompt are untested. The gateway's prompt cost looked super-linear in prompt tokens (unverified).
11. **Exploratory discoveries** [R]. D-005: DMN confidence AUC 0.732, TPN revised 0.677, paired difference +0.052; `contradiction_found` and exformation volume carried no signal. D-006: 53% of days end in no-lynch, games are short because the village rarely reaches a strict majority, and a 7-day cap would affect about 3% of games. D-009: the calibration failure analysis.

## 3. Frozen design (freeze-v2) and bridge (bridge-freeze-v1)
Three confirmatory arms plus two null floors; mafia fixed CoT; vote temperature 0.7 on first-attempt vote samples (DMN/TPN reasoning, night and probe at 0.0; speak 0.3); tau 0.35; max tokens 2500; paired seeds; trust probe after votes in every arm; confirmatory secondaries S1 (wrongful lynches), S2, S3 with Holm; intent-to-treat. Rule (PREREGISTRATION.md lines 179 and 265 [V]): a realised model-string change ends the confirmatory set and later games form a separate set. The code does not enforce it.

## 4. Where we are
- Ledger about Rs.286.64 of Rs.2,000 [R]; the budget cap is now a user-set value (see master brief).
- No confirmatory outcome has been viewed. The calibration games are "epoch 1" (old serving). The NO-GO is moot because the cause (timeouts) did not reappear in the diagnostic.
- The master agent decides: epoch boundary, re-freeze, new design (pre-registration v3).

## 5. Open issues
1. The canonical `logs/games.parquet` reportedly holds 100 calibration rows plus only 5 of the 14 pilot rows [R]. Mechanism reproduced by simulation [V]: `_upsert` dedupes on campaign/seed/arm, which are NaN for legacy rows. The `_upsert` code is in the frozen run path.
2. TRACKER.md sections 1 to 8 are stale; docs/mutation_proofs.md cites commits that do not exist; the DMN vs CoT vote-prompt wording is asymmetric [R].
3. Production client sets no explicit `max_retries` or `timeout` (SDK defaults 2 / 600 s) [R]; there is no runtime guard on the realised model string.
4. IrrevOps tasks are LLM-authored, single-step and few; Jev has never been evaluated; the analysis code has had no independent review.

## 6. Tried and rejected, or not helpful
- Focal-seat design (confounded). Homogeneous self-play as primary (DMN as mafia and as villager cancel).
- Pooling the old calibration games as if nothing changed. Options "A: keep frozen and count calibration" vs "B: fix and restart" as originally posed (superseded by the drift finding).
- Dropping JSON mode on retry (flagless retries still failed about 50%), temperature 0.3 retries, streaming (the gateway sends nothing while the model reasons), more attempts (failures persist per prompt).
- Minimal reasoning effort as the primary regime (it removes the baseline's reasoning, which weakens attribution); kept as a possible robustness regime.

## 7. Process lessons
- Long prompts were truncated by one harness: keep specs short or in files.
- Tests that cannot fail (vacuous) were common: require mutation proofs.
- Per-invocation budget caps leak: use a shared append-only ledger.
- Never trust self-reports: use independent cross-family reviewers and recompute from raw logs.
- Smoke seeds 9000 and 9100 were suggested by mistake inside the confirmatory series (5000 + 100*i); record it as a deviation and use seeds >= 100000 for all non-confirmatory runs.
- Provider behaviour drifts without notice: log realised model strings and fingerprint before each campaign.

## 8. Candidate backbones and tools (verify pricing and access)
Muse Wonder (about $4 / $20 per million tokens), DeepSeek V4.1 Flash (about $0.15 / $0.60), Muse Spark Contributor ($0.10 / $0.20), Claude models. Agent roster so far: a planner model for judgement phases, an executor model for mechanical work, DeepSeek V4.1 Flash as a read-only cross-family reviewer, Opus 5.5 as the autonomous researcher, and now the master agent.

## 9. Master agent log (append-only, from 2026-11-19)

- **2026-11-19, Phase E.** Free audit; memo `docs/decisions/2026-11-19-master-reevaluation.md`. No confirmatory outcome viewed.
  - [V] 164 tests pass on a fresh environment; 166 after the audit.
  - [V] Mutation proofs re-run with real commit ids (`docs/mutation_proofs.md`); the P0-A1 proof is weak and the script ignores a failed reverse patch.
  - [V] Canonical games table repaired to 14 pilot + 100 calibration rows (`cade84c`, `bc052db`, `675bdc1`). This changes the run path, so the tree no longer matches `freeze-v2`.
  - [V] Ledger Rs.286.6391 reconciles with raw rows. Not yet compared with the provider's billing page.
  - [V/I] D-010: the gateway cutoff is about 30 s; silent SDK retries made it look like 90 s.
  - [V] D-011: the DMN gate decides before discussion and always delays on day 0.
  - [V] D-012: bridge arm B2 reads the answer key; harm is at the floor in every arm.
  - [V] Power for the win-rate primary at n = 184 is 0.49-0.58 for +10 points (`scripts/power_sim.py`).
- **Decision (2026-11-19).** freeze-v2 is closed: the serving change ended its confirmatory set under pre-reg §8 and §11, and the audit found the treatment does not test the stated idea. Epoch 1 stays blind. The confirmatory study moves to a layered-controls design on a rebuilt IrrevOps testbed; Mafia is kept as a stress test with a repaired gate. Pre-registration v3 follows the literature update (Phase S) and an independent review.
- **Open requests.** Reviewer and backbone keys, and one billing check: `docs/decisions/2026-11-19-keys-request.md`.
