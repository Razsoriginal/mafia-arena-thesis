# AGENTS.md — Mafia Arena Thesis Project

## About project
MSc AI Part-2 thesis (Mumbai University) + Fractal data engineer side-project.
Independent clean-room replication inspired by Fractal Cerebral AIWILD 2026 paper (DMN+TPN+EVT, Mafia game, exformation).
No proprietary code/data. Primary backbone: `muse-spark-1.3-contributor` (cheap, high-intelligence, System-2). Jev System-One gate (`typesafe/jev-1.13`): choice/score/noul for calibrated DELAY. Comparative later: gpt-4o-mini, qwen3-8b, Fathom-R1-14B.

Docs: `SYNOPSIS.md` (university synopsis), `DESIGN.md` (architecture), `README.md` (quickstart), `ROADMAP.md` (phases), `docs/related_work.md` (Ch.2), `docs/enterprise_integration.md` (safety framework), `docs/guide_slide.*` (1-slide).
Code: `src/mafia/` engine, `src/agents/` DMN/TPN + baselines + `jev_gate.py`, `src/safety/` gate/middleware/audit, `src/eval/` arena runner + metrics. Logs: `logs/games.parquet` + `logs/safety_audit.parquet` + `logs/raw/`.

## How to work in opencode terminal
- Default model is muse-spark-1.3-contributor-free. Keep responses short, factual, no emojis unless asked.
- Prefer editing existing files over creating new ones. Never create *.md docs unless asked.
- Use specialized tools: read > cat, edit > sed, write only for new files, bash only for python/pytest/git.
- Always verify: `python -m py_compile` changed files, run `python -m src.eval.run_arena --games 2` smoke test before claiming done.
- Keep exactly one todowrite in_progress. Mark completed immediately after verification.
- LLM calls go via `src/llm_client.py` only. Never hardcode API keys. Model is config switch via `.env` (`LLM_MODEL`).
- JSON outputs must be repair-tolerant; fallback to safe DELAY (`no-lynch`) on parse failure.
- Thesis standard: every claim needs log evidence in `logs/`. Save raw LLM responses.

## Skills — when to use
- `mafia-arena`: game engine, DMN/TPN/EVT prompts, baselines, run_arena changes.
- `thesis-writing`: synopsis, thesis chapters, AIWILD-style 4-page paper, metrics interpretation.

## Commands
- `/run-arena --games 5` → smoke run + evaluate
- `/eval` → metrics summary from `logs/games.parquet`
- `/compare` → 10-seed rerun plan for comparative models (no code change, .env swap only)

## Guardrails
- Do not contact Biju/Cerebral team, do not use internal Fractal data. Clean-room only.
- Do not commit secrets (`.env`). Use `.env.example` pattern.
- Mumbai Univ thesis: novelty = exformation operationalization + EVT gate (LLM vs Jev System-One) + say-do-gap metric + transfer to Avalon/enterprise toy.
