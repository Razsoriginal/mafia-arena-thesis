---
name: mafia-arena
description: Use when editing Mafia game engine, DMN/TPN/EVT prompts, baselines, run_arena, metrics, or logs. Triggers on mafia, DMN, TPN, EVT, exformation, run_arena, arena.
---

# Mafia Arena Skill

Independent Mafia arena for AIWILD-style deception research.

## Files
- `src/mafia/engine.py` — deterministic state machine, no LLM inside.
- `src/mafia/prompts.py` — DMN, TPN, dialogue, vote, trust prompts (v0).
- `src/agents/dmn_tpn_agent.py` — DMN->TPN->EVT with DELAY gate (`TAU_DELAY`, `EVT_THRESHOLD` in `.env`).
- `src/agents/jev_gate.py` — System-One gate (live): Jev noul/choice/score via OpenRouter (`OpenRouterJevAPIKey`/`OpenRouterJevModel`), `--gate llm|jev`.
- `src/agents/baselines.py` — cot, react, constitution, same backbone.
- `src/eval/run_arena.py` — `--games --agents --seed --workers --out --gate --night --max-days --no-canonical --focal-role`. Saves `logs/games.parquet` (tokens, `est_cost_inr`, `jev_stub`) + `logs/progress.jsonl` + `logs/raw/history_*.parquet`.
- `src/eval/metrics.py` — brier, ece, cascade_resistance, delay_quality, say_do_gap.

## Rules
1. Engine stays LLM-free. All LLM via `src/llm_client.py` (`chat_text`, `chat_json`); Jev via `src/agents/jev_gate.py` (choice/score/noul).
2. Prompts output strict JSON. Repair + fallback to `no-lynch` (safe DELAY). Jev outputs are typed by construction.
3. Keep 7-player default (2 mafia, doctor, detective, 3 villagers). 2 discuss rounds, max_tokens 2500 (reasoning model).
4. After edits: `python -m py_compile <files>` then `python -m src.eval.run_arena --games 2` smoke test.
5. Log everything: turns, votes, dmn/tpn traces (+ jev responses) in `logs/runs/<run_tag>/raw/`. Never claim improvement without parquet evidence.
6. Backbone is config-only (`AiCredits_Model=meta/muse-spark-1.3-contributor` via `AiCredits_Base_Url=https://aicredits.in/v1` in `.env`; Jev `OpenRouterJevModel=typesafe/jev-1.14` via OpenRouter). Never hardcode model names or keys.
7. MVP first (LLM-gate only). Jev-gate is a 10-game ablation: LLM-gate vs Jev-gate on calibration, latency, cost.
