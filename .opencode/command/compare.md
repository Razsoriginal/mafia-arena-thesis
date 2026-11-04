---
description: Plan 10-seed comparative rerun across backbones (no code change).
agent: build
---

Comparative layer plan — config swap only, no prompt changes:

1. Confirm MVP on `muse-spark-1.3-contributor` (50 games in `logs/`).
2. For each model in [gpt-4o-mini, qwen3-8b, FractalAIResearch/Fathom-R1-14B]: set `AiCredits_Model` in `.env`, run `python -m src.eval.run_arena --games 10 --seed 100`.
3. Summarize win-rate delta vs backbone cost. Output table for DESIGN.md §7.

Do NOT edit prompts for specific models. Report backbone-dependence only.
