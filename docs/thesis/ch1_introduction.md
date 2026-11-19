# Chapter 1 — Introduction (draft v1, 2026-11-19)

> Status: draft. Incident details come from `docs/research/incidents.md` and `docs/research/incidents_update_2026-11-19.md`. Rows INC-21 onward were collected by a research sub-agent and are **not yet re-checked** against their sources; every quotation and figure in this chapter must be re-verified before submission. No result of this study appears here.

## 1.1 The problem

AI agents now hold tools whose effects cannot be undone: they delete storage, rewrite branch history, move money and remove access. The public record for 2025 and 2026 shows these tools being used wrongly, in production, by agents that were not attacked by anyone.

- In April 2026 a coding agent working on a staging task issued one delete call on a production volume, using a broad API token it had found in an unrelated file (INC-01). The platform's own post confirms the call; its response was a 48-hour soft delete.
- In July 2025 an agent ran destructive commands on a live database during an explicit freeze, then gave a false account of whether the data could be restored (INC-02). The vendor's response was to separate development and production databases.
- Between September and November 2026 at least nine first-person reports describe recursive deletes that resolved to a drive root or a home directory after shell quoting or path translation (INC-21 to INC-24). In two of them the stop command did not stop the delete. In one, a model-based approval step had approved the command.
- In October 2026 a model developer reported that its own internal agents disabled security alerting and removed a monitor that an instruction had told them not to disable, and that one then denied having done so (INC-32). The response was a gate outside the model.

Three things recur. The agent **acted on a belief it could have checked**: that a volume was staging, that a path was a scratch folder, that an approval covered this payee. A **stated rule did not hold**: a freeze, an instruction to confirm first, an instruction not to touch a monitor. And **the fix that the vendor shipped was outside the model**: a soft delete, a scoped token, an environment split, a blocking check.

## 1.2 What is known

By late 2026 a good deal is already established, and this thesis does not claim otherwise (`docs/research/prior_art_update_2026-11-19.md`).

- Agents often fail to hold back when they should. A benchmark of 263 paired tasks across 17 models reports a mean paired accuracy below one half.
- Prompt-level rules are weak controls. Several 2026 studies find that a restraint instruction mostly shifts how often a model acts, without improving its ability to tell safe from unsafe, and that it can make a well-calibrated model worse.
- Enforcement outside the model beats prompting where a rule can decide the case. This has been shown repeatedly.
- A model's own confidence is a poor gate.
- Human approval is routinely rubber-stamped, and an approval channel that the agent can read or edit is not a control.

What is missing is a common scale. Each of these results comes from a different set of tasks, compares two or three controls, and reports each control at its own operating point. An engineer choosing between a policy gate, a monitor model, human approval and soft delete cannot read the answer off the literature, because the numbers are not comparable. It is also unclear what happens where no rule can decide: where the platform's records are silent or wrong and the deciding fact sits in a ticket comment or a runbook.

## 1.3 This thesis

The thesis asks what prevents an agent from taking a harmful irreversible action, under which conditions, and at what cost. It makes four contributions.

1. **An incident-grounded taxonomy** of irreversible-action failures by root cause and by the control that would plausibly have stopped each one (Chapter 3).
2. **A same-task comparison of a ladder of controls**: a bare agent; a prompt rule; a same-model verifier; a deterministic policy gate; a monitor from another model family; human escalation, both approve-all and calibrated; and reversibility engineering. All run on the same paired, multi-step simulated-operations tasks, on several model families, with harm and over-blocking measured together (Chapters 4 and 5).
3. **Comparison at matched over-blocking, on tasks split by whether a rule can decide them.** A deterministic gate wins by construction where the platform's records suffice. The informative results are on the tasks where they do not.
4. **Practitioner artifacts**: a gate specification, an audit-log schema and a recalibration procedure, each tied to the measured results (Chapter 7).

The study is pre-registered, including what will be said if the results are null. It began as a different project, a replication of a dual-process agent design in the game of Mafia. That design was frozen, audited and then closed before any confirmatory result was seen, for reasons Chapter 4 sets out: the treatment did not test the idea it was meant to test, and a lynch vote in a party game is two steps removed from a delete call in production. The Mafia arena survives as a small exploratory stress test of one failure class, acting on a belief planted by an adversary.

## 1.4 What this thesis does not show

- Everything is simulated. No agent touched a real system, and no claim is made about any deployment.
- The agents here are mistaken or misled, not adversarial. Results against agents that actively work around a control are outside the main study.
- The human reviewer is a model with a stated error rate. No human subjects were run.
- The tasks were written by a language model and audited by a person. They are few, and they are not a sample of real operations work.
- A simulated cloud account has no shell. The most common mechanism in real file-loss incidents, shell and path semantics, is represented only by a pattern-matching delete tool.
