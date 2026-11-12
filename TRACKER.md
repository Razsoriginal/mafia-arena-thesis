# TRACKER — Mafia Arena Thesis

## Agent state (update at every milestone; read this first after a context reset)

- **Phase:** Phase 0 nearly done. The re-smoke passed (0 JSON failures in 10 games; resume starts nothing). Next: bridge smoke, freeze, then calibration.
- **Ledger:** `logs/spend_ledger.jsonl`, Rs.71.70 after smoke-team-02. Check it with `.venv/bin/python -c "from src.eval import run_arena as r; print(r._ledger_total(r._ledger_path(None)))"`.
- **In-flight jobs:** none.
- **Last decision:** `docs/decisions/2026-11-12-rescope.md` chose Option B, a Mafia primary plus the IrrevOps bridge. Pre-reg v2 is committed (`d1a5eef`); v1 is tagged `prereg-v1`.
- **Next 3 actions:**
  1. Bridge smoke (at most Rs.5) and `bridge-freeze-v1`.
  2. Primary freeze: fill the freeze block, commit, tag `freeze-v2`, dry-run `--confirmatory`.
  3. Calibration: trios 0..19 with nulls, `--workers 4 --call-threads 4 --trio-window 2`, seed 5000.

**Last updated:** 2026-11-12
**Branch:** `prereg-mvp` (pre-reg implementation through `bc80015`; smoke evidence committed after it)
**Status:** Pre-registered team-design MVP implemented and covered by **116 passing unit tests**. The first live team-design smoke ran on 2026-11-11 (`smoke-team-01`): 10 games, 2 of 3 planned trios, Rs.19.50. It proved the pipeline end to end but surfaced **15 JSON failures in 10 games (1.5/game)**, which must be triaged before the 20-trio calibration batch. No confirmatory game has run. The freeze block is still `PENDING`, so `--confirmatory` refuses to start.
**Budget:** Rs.2,000 hard cap (**assumed**); Rs.400 reserve; Rs.1,600 usable. Measured spend to date **Rs.50.42** (Rs.30.92 canonical pilot + Rs.19.50 smoke). Remaining usable **Rs.1,549.58** (**derived**).

This is the live status file. `ROADMAP.md` is the plan; this file records what is
actually done, what the logs prove, and what to do next.

---

## 1. Snapshot

| Item | Value |
|---|---|
| Backbone (all agents) | `meta/muse-spark-1.3-contributor` via AiCredits |
| Gate | `--gate llm` (default); Jev gate implemented, not yet live-tested |
| Night actions | `--night llm` |
| `TAU_DELAY` | **0.35** (adopted after sweep) |
| `EVT_THRESHOLD` | 0.6 |
| `LLM_MAX_TOKENS` | 2500 |
| Temperature | 0.3 dialogue / 0.0 reasoning+night+probe / 0.7 every vote sample |
| Design | `--design team`: 5 village seats play the arm agent, 2 mafia seats always CoT |
| Confirmatory arms | `dmn_village`, `cot_village`, `cotx3_village`; planned 184 trios, n re-decided after calibration |
| Null arms | `random_village`, `majority_village` (no village LLM calls) |
| Pre-registration | `docs/PREREGISTRATION.md` (2026-11-06); freeze block `runpath_sha256` / `freeze_git_sha` / `freeze_tag` still `PENDING` |
| Canonical dataset | `logs/games.parquet` — **14 games** (`pilot-clean-02` 8 + `pilot-clean-03` 6), unchanged |
| Canonical votes / trust | `logs/votes.parquet` (229 rows) / `logs/trust.parquet` (41 rows) |
| Latest live run | `smoke-team-01` — 10 games, 2/3 trios, seeds 9000/9100, 5 arms/seed, `--no-canonical` |
| Latest run cost | **Rs.19.4964** billed, all 10 ledger rows `kept`, no estimate fallback |
| Total measured spend | **Rs.50.42** (pilot Rs.30.92 + smoke Rs.19.50) |
| Canonical tokens | 910,130 prompt + 966,837 completion |
| JSON failures | Canonical pilot 1/14 (0.07/game); smoke **15/10 (1.5/game)** |
| Unit tests | **116 tests, OK** (`python -m unittest discover -s tests`) |

Config is a `.env` switch only; no secrets are committed.

---

## 2. What is done (with evidence)

| # | Workstream | Status | Evidence |
|---|---|---|---|
| 1 | Deterministic 7-player Mafia engine (night / discuss / trust / vote / win-check) | Done | `src/mafia/engine.py`, `src/mafia/models.py` |
| 2 | LLM backbone client with retry, JSON repair, cost ledger, raw logging | Done | `src/llm_client.py`, `logs/runs/*/raw/llm_raw.jsonl` |
| 3 | DMN → TPN → EVT agent with exformation + evidence spans | Done | `src/agents/dmn_tpn_agent.py`, `src/mafia/prompts.py` |
| 4 | Three baselines on the same backbone (CoT, ReAct, Constitution) | Done | `src/agents/baselines.py` |
| 5 | Trust calibration: base-rate prior instead of flat 0.5 | Done | `logs/runs/trust-prior-02/`; ECE 0.220 → 0.125 |
| 6 | Tau sweep, adopted 0.35 | Done | `logs/runs/tau-sweep-02-prior/` (n=5/cell) |
| 7 | Reliability: 5-attempt retry + token-budget escalation on empty content | Done | JSON failures 15/20 → 1/14 games |
| 8 | Parallel arena workers | Done | `src/eval/run_arena.py --workers 6`; `pilot-clean-02/03` |
| 9 | Ablations: `--ablate exformation,tpn,evt` | Implemented + smoke-tested | `logs/runs/ablate-smoke/` (1 game, 1 day, 0 JSON failures) |
| 10 | Jev System-One gate (`choice` / `score` / `noul`, OpenRouter only) | Implemented; live ablation pending | `src/agents/jev_gate.py`, `src/safety/gate.py`, `--gate jev` |
| 11 | Safety framework (`SafetyGate`, `guard_tool`, parquet audit) | Built, not run on real data | `src/safety/`, `docs/enterprise_integration.md` |
| 12 | Logging: per-run bundles, canonical upsert, per-run billed INR, raw traces | Done | `logs/runs/<run_tag>/`, `logs/progress.jsonl` |
| 13 | Streamlit dashboard | Built; verify against latest schema | `src/eval/dashboard.py` |
| 14 | Docs: synopsis, design, roadmap, related work, enterprise guide | Done; refreshed 2026-11-04 | root `*.md`, `docs/` |
| 15 | Team design, CoT-x3, null arms, trust probe for every arm | Implemented; live smoke ran | `src/eval/run_arena.py`, `src/agents/baselines.py`, `src/agents/null_agents.py`, `src/agents/base.py`, `logs/runs/smoke-team-01/` |
| 16 | Team metrics, paired/cluster stats, arm evaluation, blinded judge builder | Implemented; 116 tests | `src/eval/metrics.py`, `src/eval/stats.py`, `src/eval/evaluate.py`, `src/eval/judge_delay.py` |
| 17 | Pre-registration and confirmatory runtime gate | Written and enforced; freeze still `PENDING` | `docs/PREREGISTRATION.md`, `src/eval/run_arena.py` (`--confirmatory`) |
| 18 | Unit test suite | **116 tests, OK** | `tests/` (`python -m unittest discover -s tests`) |
| 19 | Pre-reg review hardening: row provenance, audit rows, ledger, scoped gate, campaign keys | Done | commits `24b3ba2`…`bc80015`; `tests/test_round2_*.py`, `tests/test_*integrity.py` |
| 20 | Append-only spend ledger, idempotent trios, resume/campaign scoping, pending-trio state | Done | `logs/spend_ledger.jsonl`, `logs/pending_trios.json`, `src/eval/run_arena.py` |
| 21 | First live team-design smoke | Done but **blocked for calibration** by JSON-failure rate | `logs/runs/smoke-team-01/` (10 games, Rs.19.50) |

---

## 3. Current metrics (canonical 14 games)

Village win-rate by focal agent, restricted to games where the focal agent is not mafia:

| Focal agent | Games | Village wins | Non-mafia n | Non-mafia village win-rate | Cost |
|---|---:|---:|---:|---:|---:|
| `dmn_tpn` | 4 | 2 | 4 | **0.50** | Rs 8.71 |
| `cot` | 4 | 3 | 3 | **0.67** | Rs 7.80 |
| `constitution` | 2 | 1 | 2 | **0.50** | Rs 5.57 |
| `react` | 4 | 0 | 3 | **0.00** | Rs 8.84 |

Overall system metrics:

| Metric | Value | n | Read |
|---|---:|---:|---|
| ECE (calibrated trust) | **0.105** | 41 | Good for a pilot |
| Brier | **0.193** | 41 | Good for a pilot |
| Cascade resistance | **0.333** | 229 vote rows / 14 games | Weak; dmn abstains often |
| Delay quality (reasoned delays) | **0.750** | 4 delays | Promising but tiny n |
| Say-do gap | **0.000** | 7 commitments / 3 focal lynch votes | Perfect but tiny n |
| JSON failures | 1 | 14 games | Fixed by retry |
| Delay causes | 4 low-confidence, 1 JSON failure | — | Fallbacks excluded from delay quality |
| Game length | mean 2.14 days | 14 games | Short; cap is 5 |
| Winners | village 6 / mafia 8 | 14 games | Balanced-ish |

### 3b. First live team-design smoke — `smoke-team-01` (not canonical)

Run on code `bc80015`, 2026-11-11, `--design team --no-canonical --workers 3`.
Two of three requested trios completed (seeds 9000 and 9100; seed 9200 never started).
Each trio ran all five arms, so 10 games total.

| Item | Value |
|---|---|
| Games / trios | 10 / 2 of 3 (seed series 9000, 9100) |
| Billed cost | **Rs.19.4964**, all ledger rows `kept`, no estimate fallback |
| Mean cost / game | Rs.1.95 (range Rs.0.36–5.99) |
| Cost by arm | `dmn_village` Rs.8.39, `cotx3_village` Rs.5.27, `cot_village` Rs.3.79, `random_village` Rs.1.15, `majority_village` Rs.0.90 |
| Pooled outcomes | mafia 8 / village 1 / draw 1 (per-arm outcomes deliberately not reported) |
| Game length | mean 3.0 days; one 5-day cap draw |
| Focal seat role | mafia in both seeds (focal pids 0 and 3) — zero villager-focal games |
| JSON failures | **15 in 5 of 10 games (1.5/game)** |
| Retry events | 134: **116 HTTP 500**, 18 empty content at `max_tokens=2500`; retries 0–4 |
| Probe / trust / votes | 76 probe calls; 375 trust rows; 152 vote rows |
| Canonical impact | none (`--no-canonical`); canonical dataset remains the 14-game pilot |

The pipeline itself ran end to end: team role assignment, all five arms, vote sampling,
trust probes, per-attempt raw logs, campaign-scoped ids, and the spend ledger all produced
rows. The run is **not** an efficacy sample.

---

## 4. Honest read

1. **Calibration and say-do compliance look strong.** ECE 0.105 and 0.0 say-do gap are
   the cleanest signals, but both rest on small n (41 trust labels, 3 focal lynch votes).
2. **The win-rate advantage is not established.** `dmn_tpn` is 2/4 (0.50) on non-mafia
   focal games while `cot` is 2/3 (0.67). At n=14 the confidence intervals overlap almost
   completely; the 200-game MVP is required before claiming a win-rate win.
3. **React is clearly worst** (0/3 non-mafia village wins), which is a useful sanity check
   that the arena discriminates between agents.
4. **The agent abstains a lot.** 86 of 229 votes are `no-lynch`; cascade resistance is only
   0.333 because most focal votes never enter the "wrong majority" set. Report abstention
   and delay quality together, not separately.
5. **Role balance is incomplete.** The clean set has no mafia-focal `dmn_tpn` game. Use
   `--focal-role` balancing in the MVP so each agent gets both sides.
6. **Jev exists but has no live evidence yet.** All canonical rows are `gate=llm`, so the
   System-1 vs System-2 claim is still unimplemented *in results*.
7. **The smoke proves plumbing, not efficacy.** Ten games, two seeds, all focal seats mafia,
   one village win and one cap draw. No arm comparison should be read from it.
8. **The smoke's JSON-failure rate is a calibration blocker.** 1.5 failures/game is ~21×
   the clean pilot (0.07) and ~7.5× the pre-registered 0.20 pause threshold. The 116 HTTP
   500s are provider-side, but 18 empty-content calls at `max_tokens=2500` need a code,
   prompt, or token-budget diagnosis before spending on 20 trios.
9. **Focal-role coverage in the smoke is one-sided.** Both seeds made the focal seat mafia,
   so probe/trust rows from this run are mafia-focal only. The team design still varies the
   five village seats per arm; this is a coverage limitation, not an arm-assignment bug.

---

## 5. Open issues / risks

| Issue | Impact | Mitigation |
|---|---|---|
| **Smoke JSON failures 15/10 (1.5/game)** | Above the pre-registered 0.20 pause threshold; calibration would be unsafe | Triage 500s vs empty content; fix code/prompt/token budget; rerun a short smoke before 20 trios |
| Pre-reg freeze block still `PENDING` | `--confirmatory` refuses to start | Approved freeze step: fill `runpath_sha256`, `freeze_git_sha`, `freeze_tag`, commit, tag |
| Spend ledger starts at the smoke (Rs.19.50); the Rs.30.92 pilot predates it | The code's cap check understates cumulative spend by Rs.30.92 | Backfill a prior-spend ledger row, or set the campaign cap to remaining usable; decide before calibration |
| Third smoke trio (seed 9200) never started | Smoke is 2 trios, not the requested 3 | Decide and record as a deviation; calibration uses its own seed list |
| All smoke focal seats mafia | No villager-focal probe/trust evidence from the smoke | Covered by calibration/confirmatory seed coverage; `--focal-role` balancing where applicable |
| n=14 canonical; very wide CIs (e.g. 2/4 ≈ 0.15–0.85 Wilson) | Cannot claim win-rate superiority | Run the pre-registered 184 trios |
| Only 3 focal lynch votes in say-do-gap | Metric is not yet meaningful | Longer games + balanced roles + report n |
| Baselines never emit `commitment`, so `citation_valid` is asymmetric | Say-do-gap is dmn-only by design; must be labeled as such | State it in thesis; optionally add commitment to baselines |
| Jev gate not live-tested | Phase 3 claim unsupported | 10-game `--gate jev` ablation |
| Games average 2.1 days canonical / 3.0 smoke (cap 5) | Short games reduce vote/trust signal | Keep cap; report length; maybe raise to 7 in a separate cell |
| Manifest lacks run-level totals (`cost`, `completed`, `games`, `abort_reason`) | Harder to audit a bundle; smoke has no end summary | Add aggregate fields to `manifest.json` |
| Dashboard not re-verified against latest columns | Possible stale UI | Run `streamlit run src/eval/dashboard.py` before demo |

---

## 6. Next steps (ordered)

### Immediate — triage, freeze, then calibration
1. **Triage the smoke JSON failures (no spend).** Separate the 116 HTTP 500s from the 18
   empty-content calls; check whether team prompts hit the 2500-token budget, whether the
   retry/escalation path is still effective, and whether the provider outage window is
   enough to explain the rate. Record the decision in `docs/PREREGISTRATION.md` §15.
2. **Short re-smoke after the fix** (1 trio, 5 games, ~Rs.10 at smoke-measured cost). Accept
   only if pooled JSON failures are ≤0.20/game; otherwise fix again. This stays inside the
   Rs.40 smoke allocation and needs approval before spending.
3. **Freeze step (no spend).** Fill `runpath_sha256`, `freeze_git_sha`, and `freeze_tag` in
   the freeze block, commit, and tag. Confirmatory runs refuse to start until this exists.
4. **Calibration batch: first 20 seed-trios (60 games).** Report only the allowed nuisance
   quantities: cost, JSON failure rate, length, probe cost, within-seed correlation, and
   CoT-x3 diversity. Never arm outcomes. Measured projection is **Rs.163–175**
   (`Rs.8.13` planned/trio; `Rs.8.73` smoke-measured/trio, n=2, one cap draw).
5. **Human GO**, then re-decide n from measured costs (`docs/PREREGISTRATION.md` §9). Null
   arms on the first 80 seeds add roughly Rs.82 (**derived** from the smoke). Flag the budget
   interaction: Rs.1,592 planned primary+nulls plus Rs.50.42 already spent exceeds the
   Rs.1,600 usable by ~Rs.42, so apply the §9 reduction formula rather than silently using
   the reserve.

### MVP — pre-registered team design
```bash
python -m src.eval.run_arena \
  --design team --arms dmn_village,cot_village,cotx3_village \
  --games 184 --seed 5000 --tau 0.35 --confirmatory \
  --budget-cap 1600 --workers 6 --run-tag mvp-team-01
python -m src.eval.evaluate --input logs/games.parquet
```
Planning spend at 184 trios is Rs.1,496, and Rs.1,592 with nulls (**derived/assumed**).
Add the Rs.50.42 already spent and the total is ~Rs.1,642, which is ~Rs.42 over the Rs.1,600
usable budget. Apply the §9 budget reduction formula at calibration; do not use the Rs.400 reserve.

### After the primary — priority order (pre-registered §10)
1. Jev village-team cell (30 games, exploratory).
2. Ablations: no-EVT, no-exformation, no-TPN (20 DMN-village games each, exploratory).
3. Mafia mirror cells (40 seed-sets, exploratory).
4. Constitution village, then ReAct village (40 games each, exploratory).
Each starts only if measured underspend covers the full cell. No partial cells.

### After evidence lands
1. Write thesis Ch.4–5 tables from `logs/`.
2. Transfer phase: Avalon 5-player + enterprise vendor-negotiation toy.
3. 4-page AIWILD-style draft + 1-slide share-out.
4. Release repo + dataset (no secrets, no proprietary data).

---

## 7. Scope of improvement

### Research
- **Statistical power:** move from 14 to ≥200 games, with Wilson/bootstrap CIs on every
  win-rate and calibration number.
- **Role balance:** equal mafia/non-mafia focal games per agent; `--focal-role` re-seeding.
- **Metric depth:** report say-do gap only with its n; add abstention rate and
  delay-quality-by-cause; add calibration curves, not just ECE/Brier.
- **Longer horizons:** test a 7-day cap as a robustness cell; current games end early.
- **Fair baseline protocol:** give baselines the same commitment instruction so say-do-gap
  is comparable, or explicitly scope it to the DMN agent.
- **Jev live ablation:** the System-1 vs System-2 claim needs real rows, not a stub.
- **Transfer:** Avalon + enterprise toy must reuse the same agent without retraining.
- **Model robustness:** 10-seed reruns on gpt-4o-mini / qwen3-8b / Fathom-R1-14B via `.env`
  swap only.

### Engineering
- Add run-level totals to `manifest.json` (`games`, `cost_inr`, `completed`, `abort_reason`);
  the smoke manifest has no end-of-run summary.
- Document the existing `--resume` / campaign-scoped shard workflow for long MVP runs.
- Re-verify the Streamlit dashboard against the current parquet schema.
- Add CI: `py_compile` + the 116-test `unittest` suite + a 1-game mocked smoke test (no API spend).
- Add a regression test for the smoke's empty-content path at `max_tokens=2500` once triaged.
- Keep raw traces out of git if size grows; archive per run under `logs/archive/`.

### Thesis claims to protect
- Never report win-rate alone; always pair with ECE/Brier, cascade resistance,
  delay quality, say-do gap, and n.
- Every table row must cite `run_tag` + `git_sha` + seed range.
- Treat pilot numbers as directional until the 200-game table is complete.

---

## 8. Evidence map

| Claim | Path |
|---|---|
| Canonical games / votes / trust | `logs/games.parquet`, `logs/votes.parquet`, `logs/trust.parquet` |
| Trust prior gain (ECE 0.220 → 0.125) | `logs/runs/trust-prior-02/` |
| Tau sweep + adopted 0.35 | `logs/runs/tau-sweep-02-prior/` |
| Clean 14-game pilot | `logs/runs/pilot-clean-02/`, `logs/runs/pilot-clean-03/` |
| Noisy pre-fix pilot (15 JSON failures) | `logs/archive/pilot-prior-tau035-noisy/`, `logs/runs/pilot-prior-tau035/` |
| Ablation smoke | `logs/runs/ablate-smoke/` |
| First live team smoke (10 games, Rs.19.50) | `logs/runs/smoke-team-01/` (`games.parquet`, `votes.parquet`, `trust.parquet`, `manifest.json`) |
| Smoke retry/error evidence | `logs/runs/smoke-team-01/raw/*/llm_errors.jsonl`, `llm_raw.jsonl` |
| Append-only spend ledger (smoke only; pilot predates it) | `logs/spend_ledger.jsonl` |
| Pending-trio state | `logs/pending_trios.json` |
| Unit tests | `tests/` (116 tests) |
| Raw LLM traces / errors | `logs/runs/<run_tag>/raw/llm_raw.jsonl`, `llm_errors.jsonl` |
| Live progress | `logs/progress.jsonl` |
| Safety audit schema | `logs/safety_audit.parquet` |

---

## 9. Command reference

```bash
# compile check
.venv/bin/python -m py_compile src/*.py src/agents/*.py src/eval/*.py src/mafia/*.py src/safety/*.py

# unit tests (116)
.venv/bin/python -m unittest discover -s tests

# one-game smoke (no canonical write)
.venv/bin/python -m src.eval.run_arena --games 1 --agents dmn_tpn --max-days 1 --workers 1 --no-canonical

# team smoke used for smoke-team-01 (2 completed trios shown; seed 9200 did not start)
.venv/bin/python -m src.eval.run_arena --design team \
  --arms dmn_village,cot_village,cotx3_village,random_village,majority_village \
  --games 5 --trios 3 --seed 9000 --campaign smoke-team-01 \
  --tau 0.35 --budget-cap 35 --workers 3 --no-canonical --run-tag smoke-team-01

# evaluate canonical dataset
.venv/bin/python -m src.eval.evaluate --input logs/games.parquet

# dashboard
streamlit run src/eval/dashboard.py
```
