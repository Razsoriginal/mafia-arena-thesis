# Mafia Arena — Independent Thesis Repo
Independent clean-room replication inspired by Fractal Cerebral AIWILD 2026 announcement. No proprietary code.

## Quickstart
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# edit .env with your key, keep LLM_MODEL=muse-spark-1.3-contributor
python -m src.eval.run_arena --games 5 --agents dmn_tpn,cot --seed 0
python -m src.eval.evaluate --input logs/games.parquet
```

## Structure
* `SYNOPSIS.md` — university synopsis. `DESIGN.md` — architecture + EVT/Jev. `ROADMAP.md` — phases + exit criteria.
* `docs/related_work.md` — Ch.2 evidence table (crowded vs gaps). `docs/enterprise_integration.md` — safety framework + recalibration. `docs/guide_slide.*` — 1-slide.
* `src/mafia/` engine, `src/agents/` DMN/TPN + baselines + `jev_gate.py`, `src/safety/` drop-in gate (`gate.py`, `middleware.py`, `audit.py`), `src/eval/` arena + metrics.

## Model config
Primary: `muse-spark-1.3-contributor` via OpenAI-compatible endpoint (System-2 DMN/TPN reasoning).
Jev gate (Phase 2): `typesafe/jev-1.13` System-One — choice/score/noul for calibrated DELAY, 70-500ms. Toggle `--gate llm|jev`.
Comparative later: gpt-4o-mini, qwen3-8b, Fathom-R1-14B — just change `.env`, no code change.

## Logs
`logs/games.parquet` + `logs/safety_audit.parquet` + `logs/raw/` — every LLM/gate call saved for thesis audit.
