# Mafia Arena — Independent Thesis Repo
Independent clean-room replication inspired by Fractal Cerebral AIWILD 2026 announcement. No proprietary code.

## Quickstart
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# edit .env with your keys, keep LLM_MODEL=meta/muse-spark-1.3-contributor
python -m src.eval.run_arena --games 5 --agents dmn_tpn,cot --seed 0
python -m src.eval.evaluate --input logs/games.parquet
streamlit run src/eval/dashboard.py  # live status, costs, docs
```

## Structure
* `SYNOPSIS.md` — university synopsis. `DESIGN.md` — architecture + EVT/Jev. `ROADMAP.md` — phases + exit criteria.
* `docs/related_work.md` — Ch.2 evidence table (crowded vs gaps). `docs/enterprise_integration.md` — safety framework + recalibration. `docs/guide_slide.*` — 1-slide.
* `src/mafia/` engine, `src/agents/` DMN/TPN + baselines + `jev_gate.py`, `src/safety/` drop-in gate (`gate.py`, `middleware.py`, `audit.py`), `src/eval/` arena + metrics + `dashboard.py` (Streamlit status/cost/docs).

## Model config
Primary: `meta/muse-spark-1.3-contributor` via AiCredits (`https://api.aicredits.in/v1`, System-2 DMN/TPN reasoning; needs `LLM_MAX_TOKENS=1500`, reasoning-heavy).
Jev gate: `jev-1.13-free` via BeatAI SystemOne (`https://api.beatapi.io/v1/systemone`) — choice/score/noul for calibrated DELAY. Toggle `--gate llm|jev`. Free tier: ~1 successful call/min (code has a 61s guard with auditable stub fallback).
Comparative later: gpt-4o-mini, qwen3-8b, Fathom-R1-14B — just change `.env`, no code change.

## Logs
`logs/games.parquet` (per-game: tokens, `est_cost_inr`, `jev_stub`) + `logs/progress.jsonl` (per-day live status) + `logs/safety_audit.parquet` + `logs/raw/` — every LLM/gate call saved for thesis audit. Measured 2026-10-14: ~Rs.2.7 per 5-day game.
