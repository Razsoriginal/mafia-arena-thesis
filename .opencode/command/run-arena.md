---
description: Smoke-run the Mafia arena and evaluate.
agent: build
---

Run arena smoke test and summarize:

1. `python -m py_compile src/eval/run_arena.py src/mafia/engine.py src/agents/dmn_tpn_agent.py`
2. `python -m src.eval.run_arena --games $ARGUMENTS --seed 0` (default 5 if $ARGUMENTS empty, use `--games 5`)
3. `python -m src.eval.evaluate --input logs/games.parquet`

Report: rows saved, winners by focal agent, any JSON fallback rate. Keep short. Backbone: `muse-spark-1.3-contributor` via `.env`.
