---
description: Summarize metrics from logs/games.parquet for thesis.
agent: build
---

1. Read `logs/games.parquet` via `python -m src.eval.evaluate --input logs/games.parquet`.
2. If turns/votes parquet exist, compute ECE/Brier, cascade_resistance, delay_quality via `src/eval/metrics.py`.
3. Report in thesis style: n, win-rate per agent, calibration, delays. Cite log paths. Flag missing evidence. No hype.
