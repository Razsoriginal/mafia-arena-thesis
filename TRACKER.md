# TRACKER — Mafia Arena Thesis

**Last updated:** 2026-11-04
**Branch:** `feature/parallel-arena-tau-sweep` (merge into `main`)
**Status:** Pilot validated → ready for the 200-game MVP
**Budget:** increased; ~Rs.2.2/game measured, ~Rs.440 for 200 games

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
| Temperature | 0.3 dialogue / 0.0 JSON |
| Canonical dataset | `logs/games.parquet` — **14 games** (`pilot-clean-02` 8 + `pilot-clean-03` 6) |
| Canonical votes / trust | `logs/votes.parquet` (229 rows) / `logs/trust.parquet` (41 rows) |
| Total measured cost | **Rs.30.92** billed, **Rs.2.21/game** |
| Tokens | 910,130 prompt + 966,837 completion |
| JSON failure rate | 1 / 14 games (0.07/game) |

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

---

## 5. Open issues / risks

| Issue | Impact | Mitigation |
|---|---|---|
| n=14; very wide CIs (e.g. 2/4 ≈ 0.15–0.85 Wilson) | Cannot claim win-rate superiority | Run 200 games (50 seeds × 4 agents) |
| Only 3 focal lynch votes in say-do-gap | Metric is not yet meaningful | Longer games + balanced roles + report n |
| Baselines never emit `commitment`, so `citation_valid` is asymmetric | Say-do-gap is dmn-only by design; must be labeled as such | State it in thesis; optionally add commitment to baselines |
| Jev gate not live-tested | Phase 3 claim unsupported | 10-game `--gate jev` ablation |
| Games average 2.1 days (cap 5) | Short games reduce vote/trust signal | Keep cap; report length; maybe raise to 7 in a separate cell |
| No unit/integration test suite | Regressions caught only by smoke runs | Add minimal pytest for engine + metrics + JSON repair |
| Canonical run completed at `git_sha=f729c57`; default tau change is `12c434d` | Repro metadata is correct but code moved | Record `git_sha` per row (already done); re-run MVP on frozen commit |
| Manifest lacks run-level totals (`cost`, `completed`, `games`) | Harder to audit a bundle | Add aggregate fields to `manifest.json` |
| Dashboard not re-verified against latest columns | Possible stale UI | Run `streamlit run src/eval/dashboard.py` before demo |

---

## 6. Next steps (ordered)

### Immediate — freeze and checkpoint
1. Freeze code at this commit; tag `pilot-v0.2`.
2. Archive the 14-game canonical set:
   ```bash
   mkdir -p logs/archive/pilot-clean-14
   mv logs/games.parquet logs/votes.parquet logs/trust.parquet logs/archive/pilot-clean-14/
   ```
3. Optional fast checkpoint: `--games 10` (40 games, ~Rs.90) to confirm the pipeline at scale.

### MVP — 200 games
```bash
python -m src.eval.run_arena \
  --games 50 --agents dmn_tpn,cot,react,constitution \
  --seed 0 --workers 6 --tau 0.35 --run-tag mvp-clean-01
python -m src.eval.evaluate --input logs/games.parquet
```
Expected: ~8–10 h on 6 workers, ~Rs.440. Do not change prompts or engine during the run.

### Ablations — 3 × 20 games
```bash
python -m src.eval.run_arena --games 20 --agents dmn_tpn --ablate exformation --run-tag abl-no-exformation
python -m src.eval.run_arena --games 20 --agents dmn_tpn --ablate tpn        --run-tag abl-no-tpn
python -m src.eval.run_arena --games 20 --agents dmn_tpn --ablate evt        --run-tag abl-no-evt
```

### Jev — 10 games
```bash
python -m src.eval.run_arena --games 10 --agents dmn_tpn --gate jev --run-tag jev-01
```
Compare ECE, latency, cost, JSON/stub rate against the LLM gate.

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
- Add a minimal `pytest` suite: engine win-check, role assignment, JSON repair, metric
  edge cases (no plurality, all no-lynch, zero commitments).
- Add run-level totals to `manifest.json` (`games`, `cost_inr`, `completed`, `abort_reason`).
- Add a `--resume` path or idempotent shard runner for long MVP runs.
- Re-verify the Streamlit dashboard against the current parquet schema.
- Add CI: `py_compile` + `pytest` + a 1-game mocked smoke test (no API spend).
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
| Raw LLM traces / errors | `logs/runs/<run_tag>/raw/llm_raw.jsonl`, `llm_errors.jsonl` |
| Live progress | `logs/progress.jsonl` |
| Safety audit schema | `logs/safety_audit.parquet` |

---

## 9. Command reference

```bash
# compile check
.venv/bin/python -m py_compile src/*.py src/agents/*.py src/eval/*.py src/mafia/*.py src/safety/*.py

# one-game smoke (no canonical write)
.venv/bin/python -m src.eval.run_arena --games 1 --agents dmn_tpn --max-days 1 --workers 1 --no-canonical

# evaluate canonical dataset
.venv/bin/python -m src.eval.evaluate --input logs/games.parquet

# dashboard
streamlit run src/eval/dashboard.py
```
