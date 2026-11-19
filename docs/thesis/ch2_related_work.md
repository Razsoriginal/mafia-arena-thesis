# Chapter 2: Related work (draft v3, 2026-11-19)

> Status: draft. Sources: `docs/research/prior_art_update_2026-11-19.md`, `docs/research/citation_spotcheck_2026-11-19.md` and section D of `docs/research/incidents_update_2026-11-19.md`. A number or quotation with no tag was confirmed against the source text in the spot-check. The tag "(reported, not re-checked)" marks a number taken from an abstract-level reading and covers every number in its sentence or table cell. All numbers are author-reported, and most 2026 items are preprints. This chapter replaces the draft of 2026-11-12.

## 2.1 Scope and terms

This chapter reviews work on stopping an AI agent from executing an irreversible action that it should not execute. It is organised by the question each body of work answers. Four terms are used throughout. A control is any mechanism meant to stop such an action. Harm is a harmful irreversible action that was executed. Over-blocking is a safe, requested action that was not executed because the agent or a control held it; the sources call this over-refusal, false alarm, false denial or needless blocking. A paired task is two tasks with the same request, one in which acting is correct and one in which holding back is correct.

## 2.2 Whether agents hold back when they should

The reference benchmark is AgentAbstain (Liu et al. 2026, arXiv:2607.10059; listed by NeurIPS 2026 as an oral). It has 263 paired tasks in 42 sandbox environments and evaluates 17 models with four agent harnesses. Paired accuracy, the share of pairs with both twins correct, ranges from 33.0% to 59.5%, with a mean of 45.7%. These headline figures are averaged over eight task categories and come from one run per task. The tasks are single-turn, and the authors place adversarial prompt injection outside their scope.

Other benchmarks agree that both error types occur. AURA-Eval (Shang et al. 2026, arXiv:2609.06783) pairs scenarios that differ in whether a safe path exists. SteerBench-Work (Serdar and Mertayak 2026, arXiv:2608.12654) finds that models used as proceed-or-hold judges wrongly hold 28.1% of authorised actions and wrongly allow 1.0% of unsafe ones (reported, not re-checked).

The paired design and the joint reporting of harm and over-blocking are therefore established. This thesis adopts both.

## 2.3 Whether prompt rules work

A prompt rule is an instruction in the system prompt that tells the agent to verify, ask or refuse before acting.

The most direct evidence is in version 2 of AgentAbstain, posted on 2026-11-18, which appends a restraint clause to the system prompt of three models. Under the strong clause, Gemini 3 Flash rises from 40.1% to 62.9% paired accuracy and DeepSeek V4 Pro from 36.9% to 58.2%. Claude Opus 4.7 falls from 59.1% to 51.2%: its act accuracy drops by 19.7 points and its false-alarm rate rises from 18.8% to 40.7%, while its discrimination index d' stays flat (1.73 to 1.77). The paper prints the Opus baseline as 59.4% in its main table and 59.1% in Table 24, which is the row used here. The Gemini baseline may have run on a different serving stack.

The reading is that a prompt rule changes how often a model acts and adds little ability to tell safe cases from harmful ones. SentryBench (Yusuf et al. 2026, arXiv:2610.34535) reports that a refuse-more prompt drove over-blocking to 100% on two of three models (reported, not re-checked). Zheng et al. (2026, arXiv:2609.29522) report that a cautionary prompt left the unsafe rate essentially unchanged; this finding was not among the passages re-checked. Compliance with the same rule also varies widely across models (Okamoto et al. 2026, arXiv:2608.12323; McCauley et al. 2026, arXiv:2607.25987).

## 2.4 Enforcement outside the model

A policy gate is a deterministic check, in the tool handler or the platform, that blocks an action when a rule over visible state says so.

GateArena (Jiang, Quinzan and Bhatt, NeurIPS 2026 workshop, not on arXiv) holds the instruction and tools fixed and moves a confirmation check into the handler. Its abstract reports protocol-violating executions falling from 91 of 400 to 0 of 400, and, across three models and 1,880 episodes, irreversible harm of 37.5% to 60% without the gate against 2.5% with it. Only the abstract was read.

Designing for Doubt (Ojewale and Venkatasubramanian 2026, arXiv:2606.02965, AIES 2026) compares no policy, a prompt-only policy and a runtime enforcement layer on 144 simulated scenarios. With enforcement, seven models from four vendors block 87.5% to 91% of hazardous actions at 75% to 92% usability on authorised scenarios. The authors call the evaluation preliminary.

Further 2026 studies find the same (Qin et al., arXiv:2605.28914; Shi et al., arXiv:2606.04306; Jing, arXiv:2609.38224), and rule languages for such gates exist (AgentSpec, arXiv:2503.18666). The direction of this result is no longer open.

Two limits matter more. First, a policy gate can over-block badly. Zheng et al. find that guards based on data freshness needlessly block 92% to 95% of benign cases and forfeit up to 43% of safe completions, while a guard with the complete predicate blocks none. Second, a policy gate decides only what its rules can compute. Hong et al. (2026, arXiv:2604.15579) estimate that 74% of benchmark requirements can be enforced symbolically (reported, not re-checked). The rest need another control, and agents often fail to recover after a block (Sah et al. 2026, arXiv:2603.19328).

## 2.5 Model-based reviewers and monitors

A reviewer here is a second call to the same model that judges a pending action. A monitor is a separate model that does the same.

Evidence on same-model signals is mixed. Zheng et al. find verbal confidence miscalibrated (expected calibration error of about 0.37) and agreement between repeated actions no better than a random gate, on three small local models. Huyut (2026, arXiv:2611.06116), in a pre-registered study of 3,120 two-turn episodes on four open-weight models, finds that a same-model reviewer cut violations from 9.6% to 6.4% while over-blocking stayed at 1.6% and 1.4%.

The AI-control literature studies monitors against an agent that is assumed to be working against its overseers (Greenblatt et al. 2023, arXiv:2312.06942; Bhatt et al. 2025, arXiv:2504.10374). Its 2026 results show that measured safety falls when the attacker adapts (Terekhov et al., arXiv:2510.09462; Ge-Wang et al., arXiv:2606.06529).

Two results concern monitor lineage and are easy to misread. Pinto (2026, arXiv:2607.06596) finds that a monitor calibrated on transcripts of one untrusted-policy family catches 19% of attacks from another family, against 41% for the family it was calibrated on, at a 1% audit budget. The variable is the calibration data. The paper does not compare monitor models from different vendors. Jha (2026, arXiv:2608.16190) finds that panels mixing monitor pretraining lineages detect no better at matched capability (p = 0.13), which is a null result on code-backdoor data and uses lineage in a different sense. Neither paper tests a monitor from another model family on an agent that is mistaken instead of adversarial. No such result was found.

One deployed monitor has public figures. Anthropic reports for its Claude Code permission classifier a false-positive rate of 0.4% on 10,000 internal tool calls and a false-negative rate of 17% on 52 real overeager actions.

## 2.6 Human approval and its limits

Human approval is the control that standards recommend most often. The main evidence on its limits is that reviewers approve nearly everything: the same Anthropic post states that "in practice users accept 93% of them", referring to permission prompts.

Turan (2026, arXiv:2606.08919) models a reviewer who tires and finds that realised safety first rises and then falls as more actions are escalated. Yang et al. (2026, arXiv:2610.22987) show agents obtaining dangerously broad standing approvals.

None of the comparisons in Table 2.1 scores a human approver with a stated error model on the same tasks as the other controls.

## 2.7 Reversibility and rollback

Reversibility engineering changes the platform so that an action can be undone: soft delete, snapshots, compensating actions, narrow privileges. GoEX (Patil et al. 2024, arXiv:2404.06921) argues for undo so that humans can validate after the fact. Planarian (Guo et al. 2026, arXiv:2609.35366) and AgentRewind (Zhuang et al. 2026, arXiv:2608.14380) build rollback systems.

These are systems, not comparisons against other controls. CASEL (Zhang et al. 2026, arXiv:2610.36570) does route actions among execution, verification, sandboxing, approval and abstention, but in simulation only, and its authors state that the effectiveness of each intervention is assumed. Wang and Qi (2026, arXiv:2610.27465) find that whether an undo restores behaviour must itself be measured.

## 2.8 Hidden-role games as deception tests

Hidden-role games such as Werewolf, Mafia and Avalon give ground truth for every statement and vote. They are used to measure deception, detection and belief accuracy (Agarwal et al. 2025, arXiv:2512.09187; Karpov et al. 2026, arXiv:2607.10645; Yuan et al. 2026, arXiv:2605.27068). Gao et al. (2026, arXiv:2607.10814) count irreversible in-game errors under a belief intervention. Huang and Xiao (2026, arXiv:2610.05041) solve the random-vote game exactly, which supplies a null baseline.

No study was found that places a delay or abstain gate on an elimination vote; that search covered titles and abstracts only. Nothing in the literature read shows that results in a game predict results on tool tasks. This thesis therefore keeps its Mafia arena as a separate exploratory stress test and draws no tool-task claim from it.

## 2.9 Standards and guidance

The guidance asks for human approval and least privilege and does not enforce either. The Model Context Protocol specification of 2026-07-28 says there "SHOULD always be a human in the loop with the ability to deny tool invocations", and that clients "MUST consider tool annotations to be untrusted unless they come from trusted servers". Confirmation is a recommendation only.

Under the EU AI Act as amended by Regulation (EU) 2026/1744, Chapter III, Sections 1 to 3, "with the exception of Article 6(5)", apply from 2 December 2027 for Annex III high-risk systems and from 2 August 2028 for Annex I systems. Article 14 on human oversight falls in that chapter by this project's reading, and it binds high-risk systems only, so for a general operations agent it is an analogy.

The OWASP and Five Eyes guidance on agentic AI recommends the same measures; the primary texts were not read in full and are not quoted. No NIST profile specific to agents was found.

## 2.10 The closest comparisons

Table 2.1. The closest prior studies that compare two or more control types on the same tasks.

| **Study** | **Tasks** | **Controls compared** | **Harm and over-blocking both reported** | **Models** | **What it leaves open** |
|---|---|---|---|---|---|
| AgentAbstain v2 (arXiv:2607.10059) | 263 paired tool tasks, single-turn | Bare agent; prompt rule (mild, strong) | Yes | 17 for the benchmark; 3 for the prompt rule | Every control outside the prompt |
| Designing for Doubt (arXiv:2606.02965) | 144 simulated HR and DevOps scenarios, not paired | Bare agent; prompt rule; runtime enforcement | Yes | 7 models, 4 vendors | Human approval, reversibility; few safe scenarios |
| GateArena (NeurIPS 2026 workshop) | Irreversible actions needing confirmation, 1,880 episodes | Prompt rule; handler-enforced confirmation | Harm yes; over-blocking not in the abstract | 3 | Abstract only read; no monitor or reversibility |
| Stale Does Not Mean Unsafe (arXiv:2609.29522) | 16 infrastructure tasks, one hazard class | Prompt rule; model-side confidence and agreement; three policy gates | Yes | 3 small local models | Separate monitor, human approval, rollback |
| The Harness Is the Model (arXiv:2611.06116) | 156 banking-conduct cases, two turns | Harness variants, one with a same-model reviewer | Yes | 4 open-weight | Policy gate, human approval, reversibility |
| SentryBench (arXiv:2610.34535) | 840 episodes, injection-driven (reported, not re-checked) | Prompt rule; trust-gating wrapper | Yes | 3 (reported, not re-checked) | Tasks are attacks, not paired; two controls |
| Separation of Duties (arXiv:2609.38224) | 313 attack cases (reported, not re-checked) | Prompt rule; policy gate; auditor; sandbox | Yes | 3 hosted (reported, not re-checked) | Attack cases, not paired; no human approval |
| The Agent Knew (arXiv:2610.17301) | Matched authorised and unauthorised tasks | Activation probe gate; reasoning monitor; escalation to a person | Violations and completion | 4 open-weight (reported, not re-checked) | Needs model internals; no policy gate or reversibility |
| CASEL (arXiv:2610.36570) | Simulated action stream, no real agent | Routing among verification, sandboxing, approval, abstention | Harm and approval load | None | Effectiveness assumed, not measured |

## 2.11 What is missing

The following are already published: paired tasks at scale; a prompt rule against a bare agent with both error types; a prompt rule against outside enforcement; weak in-model self-checks; and pre-registration with deterministic scoring. A positive result for a policy gate on tasks that a rule can decide is a foregone conclusion.

Four things remain open, and they are what this thesis sets out to add.

1. One table for five or more control types on the same tasks. No such study was found.
2. Comparison at matched over-blocking, in place of each control at its own operating point.
3. Measured undo and a stated human-reviewer model, in place of assumed effectiveness.
4. A monitor from another model family against a same-model reviewer on erroneous, not adversarial, actions.

The first item rests on arXiv and web searches run on 2026-11-19. They found no study that compares five or more control types on the same paired tasks with both error types. That is weak negative evidence.

The thesis is therefore a replication with an extension. Its only priority claim is that it is, to the author's knowledge, the first same-task comparison of this many control types with harm and over-blocking reported at matched over-blocking rates.
