# Chapter 2 — Related Work (draft v1, 2026-11-12)

> Source of truth: `docs/research/prior_art.md` and its two matrices. **[V]** marks a citation whose primary page was re-checked in the adversarial spot-check of 2026-11-12. **[A]** marks one read at abstract or partial-HTML level only, which must be re-read before submission. Numbers are author-reported. Items from 2026 are preprints unless a venue is given.

## 2.1 The problem: irreversible actions taken on unverified beliefs

Agents with tool access now take actions that cannot be undone, and the public record of failures is growing. Two cases frame this study.

- **Railway volume deletion (April 2026) [V].** Railway's own post-mortem and changelog describe an AI agent that used a long-lived, account-scoped token to call a legacy `volumeDelete` on a production volume. The call ran without delay. Railway recovered the data, and API deletes are now soft-deleted for 48 hours. Railway does not name the customer, the agent product or the model. The Register [V] reports the customer (PocketOS), the product (Cursor) and the model (Claude Opus 4.6), quoting the founder's account. According to that account, the agent said it "guessed" that a staging delete would be scoped to staging.
- **Replit / SaaStr (July 2025) [A, secondary-multiple].** A production database was deleted during an explicit code freeze, and the agent then misreported whether rollback was possible.

Our taxonomy has 20 incidents, 12 of them primary-sourced (`docs/research/incidents.csv`). Missing confirmation is the dominant root-cause class (15 of 20). In about 8 of the 16 real-system incidents, the decisive error was epistemic: the agent acted irreversibly on a belief it could have checked. Most vendor remediations, however, were blast-radius controls: soft delete, token scoping, dev/prod separation and peer review. A model-level gate addresses the first problem and not the second. This thesis studies the first and uses the IrrevOps bridge to probe the boundary between the two.

## 2.2 Should the agent act? Abstention and deferral benchmarks

- **AgentAbstain** (arXiv:2607.10059, preprint) [V] is the closest benchmark to our framing.
  - It has 263 paired should-act / should-abstain tool tasks in 42 sandboxes, some with explicitly irreversible tools, run on 17 models.
  - Paired accuracy, where both twins are correct, ranges from 33.0% to 59.5%.
  - "Post-hoc abstention", where the agent acts and then claims it abstained, appears in 2.6% of qualifying abstain runs.
  - It runs each task once and puts prompt injection explicitly out of scope.
- **SteerBench-Work** (arXiv:2608.12654) [V] covers 106 workplace scenarios drawn from public incidents, including evidence-reversed mirrors. Models wrongly hold authorised work 28.1% of the time and wrongly allow unsafe work only 1.0%. Over-caution is therefore the dominant failure at action boundaries.
- **Designing for Doubt** (arXiv:2606.02965; AIES 2026) [V] names *compliance bias*, which shows up in both directions: some models proceed, others over-block. With runtime enforcement, the hazard-block rate is 87.5–91% at 75–92% usability (144 scenarios).
- **SentryBench** (arXiv:2610.34535) [V] shows that prompting agents to "refuse more" drives over-refusal to 100% on 2 of 3 models while changing attack success by at most 3.7 points. A trust gate had the lowest harm on every model.

Together these works establish that harm and over-blocking must be measured jointly. We adopt their conventions: a per-decision act/abstain confusion matrix, a false-hold rate, and constant-policy floors. Harm alone is uninformative, because always abstaining scores perfectly on it.

## 2.3 Calibration, selective prediction and confidence-gated action

- **Confidence-gated asking.** KnowNo (CoRL 2023) [A] uses conformal prediction sets to decide when a robot planner should ask for help. UALA (ACL Findings 2024) [A] switches tool use on and off by an uncertainty threshold.
- **Conformal action gates (2026).** CORA (arXiv:2604.09155) [V] places a conformal execute/abstain boundary on risky mobile GUI actions, including irreversible ones. Its injection-defence results are not reported separately. Conformal Selective Acting (arXiv:2605.20270) [A] adds anytime-valid act/abstain guarantees.
- **The exchangeability problem.** These methods assume exchangeable calibration data. A strategic deceiver violates that assumption by design, which is one reason this study evaluates a plain threshold gate empirically under adversarial play rather than claiming coverage guarantees.
- **Reliability metrics.** Rabanser et al. (arXiv:2602.16666; ICML 2026) [V] propose 12 agent-reliability metrics, including ECE, AUROC and Brier, on GAIA and τ-bench. They find reliability improving more slowly than accuracy.
- **Trajectory-level calibration.** Trajectory-checkpoint calibration work (arXiv:2609.07395) [A] cautions that step-level calibration does not imply trajectory-level calibration. We therefore report calibration per game-day as well as pooled.

## 2.4 External enforcement versus in-model restraint

- **GateArena** (Jiang, Quinzan and Bhatt; NeurIPS 2026 workshop *Agents in the Wild*; not on arXiv) [V] is the most direct prior evidence.
  - Agents told by prompt to wait for confirmation still attempted the withheld confirmation tool in 38%, 48% and under 1% of episodes on three backbones.
  - An in-handler check reduced protocol-violating executions from 91/400 to 0/400.
  - At a 60% request-deviation rate, irreversible harm fell from 37.5–60% ungated to 2.5% gated.
- **Text safety versus tool calls.** Mind the GAP (arXiv:2602.16943) [V] finds 219 cases in which a model refused in text but the harmful tool call still executed, and these persist under safety-reinforced system prompts.
- **Policy enforcement systems.** Progent, CaMeL and LlamaFirewall [A] report large drops in attack success under enforced policies at modest utility cost.

Two consequences follow for this thesis:

1. "External gates beat prompt rules" is an established claim. Our IrrevOps contrast between B1 (prompt rule) and B2 (external gate) is a replication in a new setting, not a discovery.
2. The open question is whether a *model-side* verify-then-delay gate (B3) recovers part of the external gate's harm reduction when no authoritative platform metadata exists, and at what false-hold cost.

## 2.5 Social deduction as a deception testbed

- **WOLF** (arXiv:2512.09187; NeurIPS 2025 workshop) [A] measures deception and detection in Werewolf, with types including **omission**.
- **MafiaScope** (arXiv:2607.10645) [A] probes private beliefs against engine truth.
- **Werewolf Arena and AvalonBench** [A] measure win rates and reasoning.

None of the social-deduction benchmarks we checked gates the vote, evaluates a calibrated no-lynch delay, compute-matches its baselines, or pre-registers null floors. Mafia gives what production logs rarely do: an irreversible action under *strategic* deception, with ground truth for every decision.

## 2.6 Say-do gap, exformation and System-One gates

- **Say-do gap.** Stated-versus-executed divergence is already measured by Mind the GAP, LITMUS (arXiv:2605.10779) [A] and AgentAbstain's post-hoc abstention. Our say-do metric is novel only in scope: an evidence-citation commitment in an adversarial vote.
- **Exformation.** No indexed AI paper uses the term (search of 2026-11-12). The concept is studied as deception by omission (arXiv:2610.11351) [A] and as WOLF's omission category. We operationalise exformation as an explicit field of hypothesis generation. Our exploratory analysis (D-005) finds that its volume carries no signal about who is mafia (AUC 0.51–0.55).
- **System-One gates.** Jev (TypeSafe, September 2026) already has a small literature. One paper evaluates System-One models for agent security decisions (arXiv:2609.33401) [A]; another reports that Jev's choice outputs omit an implicit "unknown" mass (arXiv:2609.35342) [A]. Our Jev cell is a descriptive comparison, not a first use.

## 2.7 Standards and frameworks

OWASP's "Excessive Agency" risk and its 2026 agentic Top 10, NIST AI 600-1 and the AI RMF, the EU AI Act's human-oversight article (Art. 14), and joint CISA / Five Eyes guidance on AI agents all call for least privilege and human approval of high-impact actions. **Status: the primary texts are not yet read in full** (`prior_art_safety.md`). Before any quotation is used, each must be read in full, with quotes kept under 15 words.

## 2.8 Positioning

The novelty of this thesis lies in the **combination**:

1. A verify-then-delay gate on an irreversible group action under strategic deception, with hidden ground truth.
2. A pre-registered, paired-by-seed design with a compute-matched sampling baseline (CoT-x3) and random and majority null floors.
3. Harm and over-blocking measured together through the v2 action-boundary family.
4. A bridge to simulated production tools that places the same gate beside a prompt rule and an externally enforced policy.

No single component is claimed as new. The contribution is a decisive, honest estimate of what such a gate buys and costs under deception, whatever its sign.
