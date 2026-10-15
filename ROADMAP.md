# Roadmap — Mafia Arena Thesis (MSc AI Part-2)

Backbone: `meta/muse-spark-1.3-contributor` via AiCredits (System-2 DMN/TPN). Jev `jev-1.13-free` via BeatAI SystemOne (System-1 gate, live — `--gate llm|jev`).
Rule: one variable per iteration. Every claim needs `logs/*.parquet` evidence.

## Phase 0 — Start (Week 1)
1. `pip install -r requirements.txt`
2. `Copy-Item .env.example .env` → set `LLM_API_KEY` (AiCredits) + `JEV_API_KEY` (BeatAI).
3. `python -m src.eval.run_arena --games 2 --focal-role villager` → must produce `logs/games.parquet` + `logs/raw/` + `logs/progress.jsonl`.
4. Read 2 failures in `logs/raw/`. Tune one line in `src/mafia/prompts.py` only (done 2026-10-14: vote delays only without standout suspect).
Exit: 5 clean games, JSON failures fall back to `no-lynch`, timeouts recorded as `"draw"`, no crashes.

## Phase 1 — MVP (Weeks 2-6)
- `python -m src.eval.run_arena --games 50 --agents dmn_tpn,cot,react,constitution --seed 0`
- Same backbone for all (`meta/muse-spark-1.3-contributor`). Freeze `src/mafia/engine.py`. Tune DMN exformation (2 unsaid points) + TPN evidence spans only.
- Files: `src/agents/dmn_tpn_agent.py`, `src/mafia/prompts.py`, `logs/games.parquet`.
Exit: 200 games. dmn_tpn beats baselines on win + delay-when-uncertain.

## Phase 2 — Measure + Improve (Weeks 7-10)
Loop: `/eval` → hypothesis → one edit → 5-game retest → keep/revert.
1. Calibration: `TAU_DELAY` sweep 0.55/0.65/0.75. Report ECE/Brier via `src/eval/metrics.py`.
2. Ablations: no-exformation, no-EVT (never delay), no-TPN.
3. Say-do-gap: count commitment violations in `vote_reason`; fix top pattern with one constraint.
Exit: Thesis Ch.4-5 table — win-rate, ECE, cascade-resistance, delay-quality, say-do-gap per agent.

## Phase 3 — Jev Brake (Weeks 11-13, 10 games)
- Keep DMN/TPN on muse-spark. Gate via `src/agents/jev_gate.py` + `src/safety/gate.py` (`--gate jev`).
- Jev `choice`=vote, `score`=threat 1-5, `noul`=should-delay. Threshold `noul>0.6` → DELAY. Free tier ~1 success/min (guarded, stub logged in `jev_stub`).
- Compare LLM-gate vs Jev-gate: calibration delta, latency, cost, JSON error rate.
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
