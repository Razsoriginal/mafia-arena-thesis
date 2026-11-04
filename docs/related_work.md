# Related Work — Thesis Ch.2 (evidence table)

Use for synopsis Ch.2 + AIWILD 4-pager Related. Every row = must-cite baseline or gap.

## A. Social-deduction benchmarks (crowded: ~15-20 papers — win-rate alone insufficient)

| Paper | Year / Venue | Scale | Key result | Gap vs ours |
|---|---|---|---|---|
| AvalonBench (Light et al.) | 2023 arXiv, 131 cites | Avalon vs rule bots | GPT-3.5 good 22.2% vs 38.2% base, evil 66.7% vs 61.8%; LLMs lose to simple bots | No calibration / delay / say-do metric; we add EVT gate + same-backbone baselines |
| ReCon (Avalon thoughts) | 2023 arXiv | Avalon | 1st+2nd-order perspective planning | No exformation field, no ablation |
| DeepRole (Serrino et al.) | NeurIPS19 | Avalon, no chat | CFR + deduction beats humans | No language; we test language deception |
| WOLF Werewolf | Dec 2025 arXiv | 100 games, LangGraph, A100 21 GPU-h | Deceive well, detect poorly; suspicion 50-59%, final 62% vs 45% | No safety gate; we add delay + audit |
| Multi-round Avalon (Ellawela) | Apr 2026 arXiv | 188 games, memory | Reputation emerges; high-effort evil passes early 75% vs 36% | Single-game focus; we test cross-game + transfer |
| ParliamentBench Secret Hitler | Jul 2026 arXiv | 16 LLMs x 1600 matches | Deception retention <50%; 3 metrics (deduction/reasoning/consistency) | No calibrated abstention; we add ECE + delay-quality |
| Among Us LLM | 2026 arXiv | 1100 games, 1M tokens | Dialogue-scale benchmark | No EVT / Jev comparison |
| Mafia SciRep / NAACL22 | Dec 2024 / 2022 | Mafia dataset + BERT | GPT-3.5 lowest mafia detection; linguistic cues matter | Classification only; we test agentic action |
| Traitors (Curvo 2025) | 2025 arXiv | Trust simulations | Trust dynamics | No enterprise transfer |

## B. Deception / safety (hot — motivates problem)

| Paper | Scale | Result | Use |
|---|---|---|---|
| Secret Collusion (Motwani et al., NeurIPS24) | Steganography eval | LLMs collude undetectably despite bans; RLHF monitoring fails | Cite threat model |
| Upward Deceivers (Dec 2025) | 11 LLMs x 200 tasks | Action-deception (guess/simulate/fabricate); prompt fixes fail | Proves need for gating, not prompting |
| Intentional Deception (Mar 2026) | 36 profiles | 88.5% misdirection not fabrication; fact-check misses most | Proves verification > fact-check; motivates TPN evidence spans |
| Evolving Deception | Self-evolving agents | Competition drifts to deception | Motivates cascade-resistance metric |
| Moltbook in-the-wild (Feb 2026) | 27k agents, 137k posts | Social engineering 31.9% >> prompt injection 3.7%; 6x engagement | Real-world proof; cite AIWILD relevance |
| AI deception survey (Cell 2024) | Survey | Deception learned, destabilises discourse | Intro citation |

## C. Agents-in-the-Wild safety layer (our venue — fit proof)

| Venue / Paper | Numbers | Why cite |
|---|---|---|
| AIWILD ICLR26 / ICML26 / NeurIPS26 | 237 / 327 subs, ~100+ posters | Target venue; safety/security/beyond scope |
| OS-Sentinel (AIWILD ICLR26) | Mobile GUI + hybrid validation | Closest prior: safety validator for agents; we do same for social deduction + enterprise tools |
| AgentHallu | 693 trajectories, 13 models; best 41.1% localisation, tool-use 11.6% | Shows detection hard; motivates delay-when-uncertain |
| VerifAI ICLR25 (No Stress No Gain) | USACO 246/307 (+17) | Verification > majority vote; sister method to EVT |

## D. Fractal baselines (our starting point)

SBSC (ICLR25, +10.7% AMC/+8% AIME) — multi-turn code; No Stress No Gain (VerifAI25) — stress-test filtering; Fathom-DeepResearch (2509.24107, SOTA open 4B) — small+search wins; TRISHUL (CVPR25) — training-free structure wins; PiEvolve (>60% MLE-Bench) — DAG search wins.

## E. Our gaps (almost empty — novelty)

1. **Exformation:** 1 paper only — Lissack & Meagher Oct 2025 SSRN (philosophy, no implementation) + Nørretranders origin. Zero agent operationalizations. We implement as JSON field + ablate.
2. **Jev System-One gate:** TypeSafe AI Sep 2026 model family; `typesafe/jev-1.14` served through OpenRouter (`OpenRouterJevAPIKey` + `OpenRouterJevModel`) with choice/score/noul. Zero papers. We compare LLM-gate vs Jev-gate on ECE/latency/cost.
3. **Say-do-gap + EVT delay + `src/safety/` audit:** no benchmark combines calibration + cascade-resistance + delay-quality + transfer to enterprise tool with parquet audit.

## F. Methods / theory to cite

DMN/TPN neuroscience; Kahneman System-1/2; expectancy-violation theory; calibration (ECE/Brier), abstention/selective prediction; ToM in LLMs.

**Thesis line:** crowded on win-rate, empty on calibrated delay with exformation + System-One gate + audit. That is the contribution.
