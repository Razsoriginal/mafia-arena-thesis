# Mafia Arena — Independent Thesis Repo
Independent clean-room replication inspired by Fractal Cerebral AIWILD 2026 announcement. No proprietary code.

## Quickstart
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# edit .env with your keys, keep AiCredits_Model=meta/muse-spark-1.3-contributor
python -m src.eval.probe   # one call each to AiCredits + OpenRouter Jev
python -m src.eval.run_arena --games 5 --agents dmn_tpn,cot --seed 0
python -m src.eval.evaluate --input logs/games.parquet
streamlit run src/eval/dashboard.py  # live status, costs, docs
```

## Structure
* `SYNOPSIS.md` — university synopsis. `DESIGN.md` — architecture + EVT/Jev. `ROADMAP.md` — phases + exit criteria.
* `docs/related_work.md` — Ch.2 evidence table (crowded vs gaps). `docs/enterprise_integration.md` — safety framework + recalibration. `docs/guide_slide.*` — 1-slide.
* `src/mafia/` engine, `src/agents/` DMN/TPN + baselines + `jev_gate.py`, `src/safety/` drop-in gate (`gate.py`, `middleware.py`, `audit.py`), `src/eval/` arena + metrics + `dashboard.py` (Streamlit status/cost/docs).

## Model config
Primary: `AiCredits_Model` (default `meta/muse-spark-1.3-contributor`) via `AiCredits_Base_Url` (`https://aicredits.in/v1`, System-2 DMN/TPN reasoning; needs `LLM_MAX_TOKENS=2500` recommended, reasoning-heavy). Key: `Aicredits_API_Key`.
Jev gate: OpenRouter only — `OpenRouterJevAPIKey` + `OpenRouterJevModel` (`typesafe/jev-1.14`) on `https://openrouter.ai/api/v1`; choice/score/noul for calibrated DELAY. Toggle `--gate llm|jev`. Without the key the gate logs a stub and does not delay.
Comparative later: gpt-4o-mini, qwen3-8b, Fathom-R1-14B — change `AiCredits_Model`, no code change.

## Logs
`logs/games.parquet` (per-game: tokens, `est_cost_inr`, `jev_stub`, model, git sha) + `logs/runs/<run_tag>/` (manifest, games, votes, trust, raw traces/history, llm_raw/llm_errors) + `logs/progress.jsonl` (per-day live status) + `logs/safety_audit.parquet` + `logs/raw/` — every LLM/gate call saved for thesis audit. Canonical parquet tables are upserted, never overwritten. Measured 2026-11-03: ~Rs.2.0 for a 2-day game with LLM night actions (budget ~Rs.5 per 5-day game).
