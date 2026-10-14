---
name: thesis-writing
description: Use when writing or editing SYNOPSIS.md, thesis chapters, AIWILD 4-page paper, metrics interpretation, or literature review. Triggers on synopsis, thesis, dissertation, AIWILD paper, exformation writeup.
---

# Thesis Writing Skill

Mumbai University MSc AI Part-2 + AIWILD workshop standard.

## Sources of truth
- `SYNOPSIS.md` — approved scope, objectives, timeline.
- `DESIGN.md` — architecture, metrics definitions (win_rate, ECE/Brier, cascade_resistance, delay_quality, say_do_gap).
- `docs/related_work.md` — Ch.2 evidence table (crowded vs gaps); use for all literature claims.
- `docs/enterprise_integration.md` — safety framework + recalibration checklist; use for transfer/appendix claims.
- `logs/games.parquet` + `logs/safety_audit.parquet` — only numbers that may be reported.

## Rules
1. Every empirical claim cites a log file + n (e.g. `logs/games.parquet, n=50`). No log = no claim.
2. Novelty frame: (a) exformation operationalization, (b) EVT-gated delay (LLM vs Jev System-One), (c) say-do-gap metric, (d) Mafia->Avalon/enterprise transfer with `src/safety/` audit.
3. Cite AIWILD 2026 CFP + ICLR/ICML AIWILD (OS-Sentinel, AgentHallu) + SBSC, Fathom-DeepResearch, TRISHUL + AvalonBench/WOLF + Jev docs as in `docs/related_work.md`. Mark Cerebral AIWILD paper as `under review / forthcoming Dec 2026`, independent replication.
4. Structure: Abstract, Intro (say-do gap), Related, Method (DMN/TPN/EVT+Jev), Experiments (50 seeds x 4 agents), Ablations (no-exformation, no-EVT, tau sweep, LLM-gate vs Jev-gate), Transfer, Limitations, References.
5. Keep language short, factual, no hype. Past tense for results.
