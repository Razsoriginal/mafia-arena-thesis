# Roadmap — Mafia Arena Thesis (MSc AI Part-2)

Backbone: `AiCredits_Model` (default `meta/muse-spark-1.3-contributor`) via AiCredits `https://aicredits.in/v1` (System-2 DMN/TPN). Jev gate: OpenRouter only — `OpenRouterJevAPIKey` + `OpenRouterJevModel` (`typesafe/jev-1.14`) — `--gate llm|jev`. Night actions: `--night llm|scripted` (default llm).
Rule: one variable per iteration. Every claim needs `logs/*.parquet` evidence.

## Current position (2026-11-06)
**Pilot complete. Pre-registered team-design MVP implemented, awaiting smoke approval.**
- Design 3 is confirmatory: village team vs fixed CoT mafia. See [docs/PREREGISTRATION.md](./docs/PREREGISTRATION.md).
- Confirmatory arms: `dmn_village`, `cot_village`, `cotx3_village` (184 seed-trios planned, n re-decided after 20-trio calibration). Null arms: `random_village`, `majority_village`.
- Budget: Rs.2,000 hard cap (**assumed**), Rs.400 reserve, Rs.1,600 usable. Costs stay **assumed** until the calibration batch measures them.
- Vote samples in every arm run at 0.7. Reasoning, night actions, and the trust probe run at 0.0. Tau frozen at 0.35.
- Clean canonical pilot dataset remains: **14 games** (`logs/runs/pilot-clean-02/` + `pilot-clean-03/`),
  1 JSON failure, Rs.30.92 (~Rs.2.2/game), **measured**.
- Calibration: **ECE 0.105 / Brier 0.193** (n=41); say-do gap 0.0 (n=3 focal lynch votes).
- Win-rate superiority is **not established** at n=14. Focal-seat results are appendix history.
- Track live status and evidence in [`TRACKER.md`](./TRACKER.md).

## Phase 0 — Start (Week 1)
1. `pip install -r requirements.txt`
2. `Copy-Item .env.example .env` → set `Aicredits_API_Key` (AiCredits) + `OpenRouterJevAPIKey` (OpenRouter).
3. `python -m src.eval.probe` → both providers must return content/typed output.
4. `python -m src.eval.run_arena --games 2 --focal-role villager` → must produce `logs/games.parquet`, `logs/votes.parquet`, `logs/trust.parquet`, `logs/runs/<run_tag>/`, `logs/progress.jsonl`.
5. Read 2 failures in `logs/raw/`. Tune one line in `src/mafia/prompts.py` only (done 2026-10-14: vote delays only without standout suspect).
Exit: 5 clean games, JSON failures fall back to `no-lynch`, timeouts recorded as `"draw"`, no crashes.

## Phase 1 — MVP (pre-registered, team design)
- Smoke (needs approval): Rs.40 pipeline smoke from `docs/PREREGISTRATION.md`, then the 20-trio calibration batch.
- Confirmatory command shape: `python -m src.eval.run_arena --design team --arms dmn_village,cot_village,cotx3_village --games 184 --seed 5000 --tau 0.35 --confirmatory --budget-cap 1600 --workers 6`
  Games run seed-major in trios. Cumulative billed cost aborts after the current trio.
- Null benchmarks: `random_village` and `majority_village` on the first 80 seeds. No LLM calls from village seats.
- Same backbone for all (`meta/muse-spark-1.3-contributor`). Engine frozen during confirmatory games.
- **Status:** implementation and mocked tests complete on `prereg-mvp`. No confirmatory or smoke game has run in Phase 4.
Exit: locked primary dataset, primary estimate/test under the pre-registered wording, calibration batch report.

## Phase 2 — Measure + Improve (Weeks 7-10)
Loop: `/eval` → hypothesis → one edit → 5-game retest → keep/revert.
1. Calibration: `TAU_DELAY` sweep 0.30/0.35/0.45 (`--tau-sweep 0.30,0.35,0.45`). Report ECE/Brier via `src/eval/metrics.py`.
   - Pilot 2026-11-04 (`logs/runs/tau-sweep-01/`, n=4/cell, dmn_tpn): tau 0.45 → 3/3 village wins, 0 JSON failures; 0.55 → 0/3; 0.65 → 1/3.
   - With base-rate trust prior (`logs/runs/tau-sweep-02-prior/`, n=5/cell): tau 0.35 → 4/5 village, 3/3 non-mafia, ECE 0.154; 0.45 → 2/5, ECE 0.128; 0.30 → 2/5, ECE 0.175. Adopt 0.35.
   - 20-game all-agent pilot at 0.35 (`logs/runs/pilot-prior-tau035/`, n=5/focal): dmn_tpn 2/4 non-mafia village wins vs 1/4 for cot/react/constitution; ECE 0.126; say_do_gap 0.0 (4/4 valid citations). Noisy: 15 JSON failures/20 from provider connection/empty errors.
   - Clean 14-game set (`logs/runs/pilot-clean-02/` + `pilot-clean-03/`, 5-attempt retry): 1 JSON failure; dmn_tpn 2/4 non-mafia village wins vs cot 2/3, constitution 1/2, react 0/3; ECE 0.105; Brier 0.193; say_do_gap 0.0 (3/3 valid citations). Win-rate advantage over cot is not established at n=14; the 200-game MVP is needed.
2. Ablations (implemented: `--ablate exformation,tpn,evt`): no-exformation, no-TPN, no-EVT (never delay).
   - Smoke-verified in `logs/runs/ablate-smoke/` (1 game, 1 day, citations valid, 0 JSON failures). Confirmatory runs forbid ablations; exploratory cells run after the primary under the pre-registered priority list.
3. Say-do-gap: count commitment violations in `vote_reason`; fix top pattern with one constraint.
   - Current clean set: 0.0 gap, but only 7 commitment rows / 3 focal lynch votes. Scale n and label baselines consistently before claiming this.
Exit: Thesis Ch.4-5 table — win-rate, ECE, cascade-resistance, delay-quality, say-do-gap per agent.

## Phase 3 — Jev Brake (exploratory, after primary)
- Keep DMN/TPN on muse-spark. Gate via `src/agents/jev_gate.py` + `src/safety/gate.py` (`--gate jev`).
- Jev `choice`=vote, `score`=threat 1-5, `noul`=should-delay. Threshold `noul>JEV_THRESHOLD (0.6)` → DELAY. OpenRouter-only: `OpenRouterJevAPIKey` + `OpenRouterJevModel`; every stub/error logged per call (`jev_stub`).
- Compare LLM-gate vs Jev-gate: calibration delta, latency, cost, JSON error rate.
- **Status:** gate code + OpenRouter-only config are implemented; all current canonical rows are `gate=llm`. The pre-registered exploratory Jev cell is 30 village-team games after the primary, funded only from measured underspend. Confirmatory games refuse `gate != llm`.
Exit: Hybrid System-2+1 result. Thesis Ch.6. See `docs/enterprise_integration.md`.

## Phase 4 — Transfer (Weeks 14-18)
- Same agent, no retraining: Avalon 5-player (30 games) + vendor-negotiation toy (30 cases).
- Recalibrate per domain with 30 labels (procedure in `docs/enterprise_integration.md`).
- Pilot `src/safety/` (`guard_tool`, `AuditLogger` → `logs/safety_audit.parquet`).
Exit: generalisation claim + audit sample.

## Phase 5 — Complete (Weeks 19-36)
- Thesis: Intro, Related (AIWILD, SBSC, TRISHUL, Fathom, AvalonBench, Jev), Method, Experiments, Ablations, Transfer, Limitations.
- Every number cites log path + n. Release repo + dataset.
- Optional comparative: 10 seeds each on gpt-4o-mini / qwen3-8b / Fathom-R1-14B via `.env` swap only (`/compare`).
- Share with Cerebral team post-submission: 1-slide (`docs/guide_slide.pptx`) + audit sample.
Done = thesis submitted + 4-page AIWILD-style draft + reproducible logs.
