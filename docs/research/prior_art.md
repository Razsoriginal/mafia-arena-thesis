# Prior-art synthesis (Phase R, 2026-11-12)

Detailed matrices: [`prior_art_abstention.md`](prior_art_abstention.md) (abstention, deferral, calibration, Jev, exformation, say-do) and [`prior_art_safety.md`](prior_art_safety.md) (agent-safety benchmarks, runtime guardrails, social deduction, standards). Search log: [`search_log.md`](search_log.md). Incidents: [`incidents.csv`](incidents.csv), [`incidents.md`](incidents.md).

**Evidence level.** Most 2026 items were read at abstract level. A few were read at partial-HTML level: AgentAbstain, Designing for Doubt, Rabanser et al., CORA and AbstentionBench. Ten load-bearing items were re-fetched in an adversarial check (end of `search_log.md`); the corrections are applied in the matrices. Numbers are author-reported. Items marked secondary or unverified in the matrices must not be cited without re-reading.

## 1. Closest prior work, by our contribution

| Our component | Closest prior art (verified) | What it already shows | What it does not do (our gap) |
|---|---|---|---|
| Should-act / should-abstain decision on irreversible actions | **AgentAbstain**, arXiv:2607.10059 (preprint). 263 paired tool tasks. | Paired accuracy is 33.0–59.5% across 17 models. Post-hoc abstention appears in 2.6% of abstain runs. | No adversary (prompt injection is explicitly out of scope). No gate or intervention. One run per task. |
| Over-caution versus over-compliance | **SteerBench-Work**, arXiv:2608.12654. **Designing for Doubt**, arXiv:2606.02965 (AIES 2026). **SentryBench**, arXiv:2610.34535. | Models wrongly hold safe work 28.1% of the time but wrongly allow only 1.0%. "Compliance bias" goes both ways. Runtime enforcement blocks 87.5–91% of hazards at 75–92% usability. Prompting to refuse more drives over-refusal to 100% for at most 3.7 points of ASR change. | Single-step or injection-only settings, no strategic multi-agent deception, no calibrated-delay mechanism, no null floors. |
| Calibrated / conformal act-or-abstain gate | **CORA**, arXiv:2604.09155; KnowNo (CoRL 2023); UALA (ACL Findings 2024); Conformal Selective Acting, arXiv:2605.20270. | Execute/abstain boundaries with risk control. Asking for help at a target coverage. | Assume exchangeable calibration data and non-strategic risk, which strategic deceivers violate. |
| Externally enforced gate versus in-model restraint | **GateArena** (NeurIPS 2026 workshop, Agents in the Wild; not on arXiv). Progent; CaMeL; LlamaFirewall. **Mind the GAP**, arXiv:2602.16943. | With only a prompt instruction, agents still called a withheld confirm tool in 38%/48%/<1% of episodes; an in-handler check cut violations from 91/400 to 0/400. Text refusal does not transfer to tool calls (219 cases persist under safety prompts). | Same-task head-to-head comparisons are rare. No study gates a group decision under deception. GateArena covers only two action types with no adversarial input. |
| Social deduction as a testbed | **WOLF**, arXiv:2512.09187; MafiaScope, arXiv:2607.10645; Werewolf Arena; AvalonBench. | Deception and suspicion calibration measured against ground truth. WOLF types omission as a form of deception. | None gates the vote, offers or evaluates a calibrated no-lynch delay, compute-matches baselines, or pre-registers null floors. |
| Say-do gap | **Mind the GAP**; LITMUS, arXiv:2605.10779; AgentAbstain's post-hoc abstention; arXiv:2611.10628. | Stated policy and executed action diverge, including under safety prompts. | Not measured as a committed evidence-citation rule in an adversarial vote. |
| Exformation (reasoning about what is unsaid) | No AI paper uses the term (arXiv full-text search on 2026-11-12; Semantic Scholar was rate-limited). The concept appears as deception by omission (arXiv:2610.11351), omission-aware detection (arXiv:2512.01728) and WOLF's omission category. | Omission is a measurable deception channel. | No work uses omission hypotheses as evidence for an action gate. |
| System-One gate (Jev) | At least 8 preprints from Sept–Oct 2026, e.g. arXiv:2609.33401 (System-One models for agent security decisions) and arXiv:2609.35342 (the missing "unknown" mass in Jev choice outputs). | Jev is already studied as a security and selective-automation gate. Its choice outputs may omit an implicit P(unknown). | Not used as a delay gate on an irreversible decision in an adversarial multi-agent game. |

## 2. Re-test of the claims in `docs/related_work.md`

| Old claim | Verdict | Evidence-backed replacement |
|---|---|---|
| "Calibrated delay is nearly empty." | **False** for 2026. | Confidence-gated abstention for agent actions became an active area in 2026 (AgentAbstain arXiv:2607.10059; SteerBench-Work arXiv:2608.12654; CORA arXiv:2604.09155; Designing for Doubt arXiv:2606.02965). These works use non-adversarial or injection-only settings. We found no study of calibrated delay for an irreversible group decision under strategic deception. |
| "Exformation: 1 paper." | **Not reproducible**: 0 papers use the term. | We found no indexed AI paper using "exformation" (search of 2026-11-12). The term comes from Nørretranders (1991). The closest work studies omission as deception (arXiv:2610.11351; WOLF arXiv:2512.09187) without using omissions as gate evidence. |
| "Jev: 0 papers." | **False.** | Jev, a System-One calibrated-decision model released in September 2026, has a small preprint literature on calibration and gating (e.g. arXiv:2609.29429, 2609.33401, 2609.35342). None tests it as a delay gate in an adversarial game. |

## 3. What remains novel (honest scoping)

1. **The combination is novel; most components are not.** No verified work evaluates a verify-then-delay gate on a single irreversible group action under strategic deception, with hidden ground truth, a compute-matched sampling baseline (CoT-x3), and pre-registered random and majority null floors.
2. **Delay under adversarial pressure.** Prior benchmarks with a "hold" action are benign (AgentAbstain, SteerBench-Work) or injection-only (CORA, SentryBench). Our deceivers are strategic and adapt within the game.
3. **Say-do gap.** Novel only in scope (an evidence-citation commitment in social deduction), not as a general metric.
4. **External gate vs in-model restraint.** GateArena already makes the general point. Replicating it on a production-like sandbox is a confirmation, not a discovery.
5. **A plain paired should-act / should-abstain sandbox would largely duplicate AgentAbstain.** A bridge testbed adds value only if it adds adversarial pressure (deceptive tickets or injected content), compares the gate with a prompt rule, uses repeated seeds and pre-registers its analysis.

## 4. Metric conventions adopted (see `prior_art_abstention.md` §3)

- **Per-decision act/abstain confusion matrix**: act-correct / act-harmful / abstain, with abstain split into justified or needless where a ground-truth "should-act" label exists. Used by AgentAbstain and Designing for Doubt.
- **Over-caution and over-compliance**: false-hold rate (SteerBench-Work's "wrongly hold") and harmful-act rate, always reported together.
- **Constant-policy floors**: always-act and always-abstain, as in AgentAbstain. In Mafia these are our majority and random nulls plus an always-no-lynch reference.
- **Risk-coverage curve and AURC**, with a matched-coverage random-abstention control (exploratory).
- **Calibration** (ECE, Brier, AUROC) reported per game-day as well as pooled (TC-ECE caution, arXiv:2609.07395).
