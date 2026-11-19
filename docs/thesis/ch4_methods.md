# Chapter 4 — Methods (draft v1, 2026-11-19)

> Binding design: `docs/PREREGISTRATION_V3.md`, which is still a **draft**. This chapter explains the design and will be brought into line with the frozen text. Where they differ, the pre-registration wins. No confirmatory result exists yet.

## 4.1 How the design got here

The project began as a study of one agent architecture in the game of Mafia: an agent that imagines motives, verifies them against the record, and delays its lynch vote when unsure. That design was pre-registered and frozen (`freeze-v2`), and a 100-game calibration batch was run. Before any outcome was looked at, the design was audited and closed, for five reasons (`docs/decisions/2026-11-19-master-reevaluation.md`).

1. **The treatment did not test its own idea.** The gate decided before each day's discussion. On the first day it had nothing to verify and always delayed; in the smoke runs it then never delayed again.
2. **The primary outcome was far from the construct.** A village's win depends on night kills, on the opponents and on five voters at once. It is not a measure of one agent avoiding one harmful action.
3. **Power was low.** By simulation, 184 paired games gave about a one-in-two chance of detecting a ten-point difference in win rate.
4. **The provider changed how it served the model**, which by the pre-registration's own rule ended the confirmatory set.
5. **A second testbed built to connect the game to operations work could not separate controls**: its external gate was handed the answer, and no arm did any harm in its smoke run.

The 100 calibration games remain unopened. They are reported at the end as a closed epoch and are pooled with nothing.

Two engineering findings from that period shaped the new harness. The provider's gateway cut any request at about 30 seconds, and the client library had been retrying silently, so that one logged attempt hid up to three requests. And a deduplication bug had quietly removed nine pilot rows from the main results table. Both were found by recomputing from raw logs, and both now have tests.

## 4.2 Testbed

**A simulated cloud account with two layers.** The *metadata* layer is what tools return and what a platform records: tags, attachments, traffic counters, backup lists, a policy text, an approval registry. The *truth* layer is what is actually the case: whether a resource is really in use, whether a backup is really usable, whether a payment is really approved. Agents, gates and monitors see only metadata. Truth is used for two things only: scoring harm, and simulating a human reviewer.

**Tools.** Eight read-only tools, two reversible ones, and five irreversible ones: delete a resource, delete everything matching a pattern, force-push a branch, send a payment, revoke access. The tool descriptions say what each does and do not label any of them as dangerous.

**Episodes** run for up to twelve steps. An episode continues after an irreversible action has executed, so an agent can do several things in one task, some right and some wrong.

**Harm is scored at the moment of execution**, from the truth layer and the state of the world at that moment. An agent that takes a new snapshot before deleting the only backup has made the deletion safe, and it is scored as safe.

## 4.3 Tasks

Tasks come in **pairs that share their ticket text**. In the *act* twin the requested action is safe and should be done. In the *abstain* twin the same action is harmful and nothing should be done. A few *mixed* tasks require some actions and make another one harmful. An agent that always acts fails every abstain twin; one that never acts fails every act twin.

There are 35 templates in ten families taken from the incident taxonomy of Chapter 3: environment confusion, backups, destructive workarounds when blocked, injected instructions, false authority over payments, freezes and history rewrites, access removal, dependency cascades, over-cautious metadata, and target resolution. Each template has eight instances with different names and numbers, split by instance number into development (2), calibration (2) and test (4). The unit for inference is the template, because instances of one template are not independent.

**Decidable and undecidable templates.** A template is *undecidable* when the same action, in a world whose platform records are identical, is safe in one twin and harmful in the other. The deciding fact is then in a ticket comment, a runbook, a chat thread or policy prose. No rule over the records can be right in both twins. Seventeen templates are undecidable and eighteen decidable; an automated test checks every label against this definition. On decidable templates a deterministic gate should win by construction, and that stratum serves as a check that the harness works. The claims of the thesis rest on the undecidable stratum.

**Limits of the task set**, stated here because they bound every result. The templates were written by a language model, then paraphrased by a second model and audited blind by a person **[to be done before the freeze]**. They are few. They contain no shell, so the commonest real mechanism of file loss is represented only by the pattern-delete tool.

## 4.4 Controls

| Arm | Control | Where it sits |
|---|---|---|
| L0 | none | — |
| L1 | a restraint clause in the system prompt (the published AgentAbstain clause, verbatim) | in the model's instructions |
| L2 | the same model scores each pending irreversible action; it runs only above a threshold | a second call to the same model |
| L3 | deterministic rules over platform metadata | the tool handler |
| L4 | a model from another family scores each pending action | a separate model with its own key |
| L5a | every irreversible action waits for a human | the tool handler, then a person |
| L5b | the monitor's score decides: run, block, or ask a human | as L4, then a person when unsure |
| L6 | no gate; deletes are recoverable and the agent's identity has no rights on restricted targets | the platform |

The agent's prompt is the same in every arm except for the L1 clause. A blocked action returns a short message and the episode goes on.

**The human reviewer is simulated.** It approves exactly the safe actions. Since real reviewers approve most of what they are shown, every escalation result is also given under reviewer slip rates of 0.1, 0.3 and 0.5.

**Recovery is executed.** Under L6 the simulator restores each soft-deleted resource and compares it with its initial state. Residual harm is what recovery did not undo. Payments, pushes and access removal are never recoverable.

**Matched over-blocking.** For the scoring controls, thresholds are chosen on the calibration split so that each control spends the same budget of needless holds: at most five percentage points. Controls are then compared at that budget, not each at its own most flattering point.

## 4.5 Outcomes and analysis

Per episode: **harm** (an executed action was harmful), **false hold** (a required action did not run), **escalation**, **residual harm**, and what the agent did after a block. Each task is run three times per arm; a task's value is the mean of its runs.

Contrasts are paired by task. Intervals come from a two-level bootstrap that resamples templates and then tasks within them. Tests are sign-flip permutations at the template level. Four contrasts are confirmatory on each model, with Holm adjustment over the four:

- **C1**, a replication: policy gate against prompt rule, harm rate, decidable tasks.
- **C2**, the open question: other-family monitor against the bare agent, harm rate, undecidable tasks.
- **C3**: other-family monitor against same-model verifier, on informedness (harm caught minus safe tasks failed), all tasks.
- **C4**, a replication: prompt rule against the bare agent, false-hold rate.

Two results are fixed by construction and are reported without a test. On undecidable tasks the policy gate sees the same records in both twins, so it blocks both or allows both. And soft delete restores deleted data by definition, while a payment, a push or an access removal is never recovered. An independent review of the design pointed out that testing either would be testing the simulator.

Where the bare agent's harm rate on a stratum is below 0.10 on the calibration split, the harm contrast on that stratum is reported as an estimate only. A control cannot be shown to reduce harm that does not occur.

Every harm result is reported beside the matching result for false holds, escalations and collateral harm. A cost-sensitive utility is tabulated for harm-to-delay cost ratios from 1 to 1000; it charges needless escalations and not justified ones.

Simulated power, with assumed between-template variation and at the first Holm step, is about 0.64 at seventeen templates for a control that cuts a harm rate of 0.15 to 0.05, and 0.28 for a halving (`scripts/power_sim_v3.py`). The design detects large effects only. It will be recomputed from calibration data before the freeze.

## 4.6 Models and regimes

The ladder is run on at least three model families or price tiers **[two still to be chosen and priced]**, each with a monitor from a different family. Default reasoning effort is the confirmatory regime. Minimal reasoning is a planned robustness replication. Reasoning tokens and visible tokens are logged for every call.

## 4.7 Integrity controls

- **Pre-registration with a machine-readable freeze**: hashes of the code path, prompts and task set; requested and realised model strings; thresholds.
- **Held-out test split**: the runner refuses to run it before the freeze.
- **Blinding**: the runner prints no outcomes; confirmatory tables need a lock tag and are produced once.
- **Serving guard**: a changed model string stops the campaign. In a pilot the provider switched serving paths for twelve seconds in the middle of a run.
- **Spend ledger**: append-only, flushed to disk after each row, with a hard cap. A machine crash during a pilot damaged the ledger once; the repair is documented and was approved by the project owner.
- **One log row per request**, with client retries switched off.
- **Tests first**: each fix has a test that failed before it. Task labels are checked by scripted agents that need no model.
- **Independent review** of the pre-registration and the analysis code by a model from another family **[pending a reviewer key]**.

## 4.8 The Mafia arena, kept as a stress test

The game is retained for one purpose: acting on a belief planted by an adversary who adapts. The gate is to be repaired so that it decides after discussion, on the same information as the vote. The arms will share their vote wording. Outcomes are wrongful lynches and missed correct lynches per game. It is exploratory, and nothing from it is offered as evidence about tool-using agents.
