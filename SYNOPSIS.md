# MSc AI Part-2 Research Synopsis
## Mumbai University

**Student:** Raza Sayyed (Data Engineer, Fractal Analytics)  
**Tentative Title:** Exformation-Aware Dual-Process Agents for Deception-Resistant Decision-Making: From Mafia Arena to Enterprise Safety  
**Inspired by:** Fractal Cerebral team paper accepted at Agents in the Wild Workshop (AIWILD), NeurIPS 2026  
**Mode:** Independent clean-room replication + extension (no proprietary code/data used)

---

### 1. Introduction
AI agents are moving from chatbots to actors that reason, use tools, and coordinate in open-ended environments (Claude Code, Codex, OpenClaw). Unlike LLMs, they take irreversible actions with real consequences. A central failure is the **say-do gap**: agents state rules/constitutions then violate them under manipulation, follow misleading consensus (influence cascades), and act on weak evidence.

The Fractal Cerebral AIWILD 2026 paper explores a neuroscience-inspired defence tested in the Mafia game: Default Mode Network (DMN)-inspired imaginative reasoning about motives + Task Positive Network (TPN)-inspired verification against observable behaviour, using **exformation** (explicitly discarded / implied / contextual information) and an Expectation-Violation-Threat (EVT) scan. Reported: 82% win rate over 50 games, calibrated trust 0.78, cascade resistance 0.93, delayed action 0.87.

This thesis independently re-implements this idea from public description, formalises metrics, and tests generalisation beyond Mafia.

### 2. Objectives
1. Build an open 7-player text Mafia arena with full logging (utterances, claims, votes, kills, trust scores).
2. Implement DMN+TPN+EVT agent using `meta/muse-spark-1.3-contributor` via AiCredits as primary backbone (System-2 reasoning).
3. Compare against 3 baselines on same backbone: CoT-vote, ReAct, Constitution-only.
4. Define and measure: win rate, calibrated trust (ECE/Brier), cascade resistance, delay quality, say-do gap.
5. Add Jev System-One gate ablation (OpenRouter `OpenRouterJevModel`, `typesafe/jev-1.14`): muse-spark DMN/TPN + Jev choice/score/noul for calibrated DELAY; compare LLM-gate vs Jev-gate on latency, cost, calibration.
6. Test transfer to Avalon (5-player) + 1 enterprise toy scenario (vendor negotiation with hidden incentive) without retraining.
7. Release benchmark logs (≥50 games x 4 conditions = 200 games + 10-game Jev ablation) + evaluation code.

### 3. Scope
* In-scope: text-only social deduction, single backbone for MVP, offline evaluation.
* Out-of-scope: training/fine-tuning, vision/audio, real enterprise deployment.
* Independent work: no Fractal internal code/data. Cite AIWILD paper once public (Dec 2026).

### 4. Literature Gap
* Agent safety in the wild (AIWILD ICLR/ICML/NeurIPS 2026), VerifAI.
* Theory-of-Mind in LLMs, AvalonBench, Werewolf agents, AgentHallu.
* Social deduction as deception benchmark; influence cascades; calibration and abstention.
* Gap: exformation operationalised for agents + EVT-gated irreversible action + say-do gap metric is missing.

### 5. Methodology
**Phase 1 - Arena:** 7 players (2 Mafia, 1 Doctor, 1 Detective, 3 Villagers), phases: night -> day-discuss (2 rounds) -> vote-lynch. Deterministic engine, LLM only for dialogue/vote/trust.

**Phase 2 - Agent (Hybrid System-2 + System-1):**
```
Dialogue history -> DMN (muse-spark via AiCredits): hypothesise motives + exformation (implied/unsaid, who benefits) [JSON]
-> TPN (muse-spark): verify vs votes/kills/contradictions with evidence spans [JSON]
-> EVT: Expectation (predicted vote) vs Violation (deviation) vs Threat (cost of wrong lynch)
   - LLM-gate (MVP): trust 0-1 + DELAY if max trust < tau
   - Jev-gate (ablation): choice=vote target, score=threat 1-5, noul=should-delay 0-1 (70-500ms, calibrated)
-> action: ACCUSE / DEFEND / DELAY / VOTE
```

**Phase 3 - Eval:** 50 seeds x 4 agents, fixed role assignment rotation. Metrics computed from logs.

### 6. Expected Outcomes
* Open repo + 200-game dataset + thesis (100-120 pages).
* Result: DMN+TPN+EVT improves win rate + calibration + cascade resistance vs baselines, with cost analysis.
* Target: 4-page short paper to AIWILD / VerifAI-style workshop 2027 + internal share-out to Cerebral team.

### 7. Timeline (9 months, Part-2)
* M1: Arena + logging + 5 smoke games
* M2-3: DMN/TPN agent on muse-spark-1.3 + baselines, 50-game MVP
* M4: Metrics + ablations (no-exformation, no-EVT, tau sweep) + Jev-gate 10-game ablation (latency/cost/calibration)
* M5: Transfer to Avalon + enterprise toy
* M6: Full 200-game run + analysis + thesis writing
* M7-9: Buffer, guide review, publication draft

### 8. References (starter)
* AIWILD NeurIPS 2026 CFP; ICLR 2026 AIWILD proceedings (OS-Sentinel, AgentHallu).
* SBSC (Singh et al. ICLR 2025), No Stress No Gain (VerifAI 2025), Fathom-DeepResearch (2509.24107), TRISHUL (2502.08226).
* Jev: OpenRouter-hosted `typesafe/jev-1.14` (choice/score/noul); TypeSafe AI System-One model family (RLCD calibration).
* AvalonBench, Werewolf LLM papers, ToM in LLMs, calibration (ECE/Brier), abstention.
* Neuroscience: DMN/TPN, exformation (Nørretranders), expectancy-violation theory; Kahneman System-1/2.

**Guide sign-off: _____________ Date: _______**
/