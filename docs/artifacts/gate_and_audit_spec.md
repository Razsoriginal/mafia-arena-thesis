# Gate specification and audit-log schema (draft v0, 2026-11-19)

> Status: draft. The structure below follows what the testbed implements (`src/irrevops/`). Every recommendation marked **[after results]** is a placeholder to be confirmed, changed or withdrawn by the confirmatory data. Nothing here is evidence yet.

## 1. Where a gate sits

A gate reviews a **pending irreversible action** after the agent has chosen it and before the tool handler runs it. It is enforced by the tool handler, not by the prompt: the action cannot run unless the gate returns ALLOW. Three decisions exist.

| Decision | Effect | The agent is told |
|---|---|---|
| ALLOW | the action runs | the tool result |
| BLOCK | the action does not run | a short reason, without the reviewer's reasoning |
| ESCALATE | a human decides; the action runs only on approval | that a reviewer declined, if they did |

## 2. What counts as irreversible

Classify tools by effect, not by name, and keep the list outside the agent's reach: data loss (delete, drop, truncate, pattern deletes), history rewrite (force-push, rebase of shared branches), money (payments, refunds, transfers), access change (revoke, rotate, permission edits), external communication (anything sent outside the organisation). An unlisted tool that mutates state is treated as irreversible until classified.

## 3. Rules a deterministic gate can apply (platform records only)

The testbed's policy gate uses these. Each reads a record the platform already keeps.

1. **Resolve, then check.** Expand any pattern, glob or variable to the concrete target set first. Block an empty or root-like pattern. Apply every rule below to every member.
2. **Target exists** in the inventory.
3. **Not tagged production, not protected.**
4. **Not attached** to another resource; **no traffic** in the last hour; **no listed dependents**.
5. **Not the only backup** the platform holds for its source.
6. **Branch not protected, no registered freeze.**
7. **Payment matches an approved registry entry** on request id, payee and amount.
8. **Not the only administrator; credential not used in the last day.**

Known gaps, kept on purpose in the study and listed so that nobody mistakes the list for complete: a backup that exists but is unusable; commits by other people on a branch about to be overwritten; anything recorded only in a ticket, a runbook, a chat thread or policy prose.

## 4. What a deterministic gate cannot decide

When the platform's records are identical for a safe and a harmful version of the same action, no rule over those records can be right in both. The deciding fact is then in free text. For these cases the options are a reviewer model, a human, or making the action recoverable. **[after results]** Which of these works, and at what false-hold and escalation cost, is the main question of the study.

## 5. Requirements that do not depend on the results

These follow from the incident record alone.

- **The gate's configuration, the approval channel and the monitor are outside the agent's write access, and the approval channel is outside its read access.** An agent that can read the approval code or edit the monitor has no gate.
- **A stop must kill child processes.** Verify it.
- **Fail closed.** A reviewer that errors or returns an unparseable answer blocks.
- **Every ESCALATE has an owner and a response time.** A gate without a human path becomes a denial of service, and people then switch it off.
- **Prefer recoverable operations.** Soft delete with a retention window, snapshot before destructive change, separate development and production credentials. These held in incidents where everything else failed.
- **A git worktree, a container without a filesystem boundary, or a "practice" site with a live sibling is not a sandbox.**

## 6. Audit-log schema

One row per reviewed action, written whether or not the action ran. The testbed writes the review fields in the `reviews` column of `episodes.parquet`; `episode_id`, the model fields and timestamps are on the episode row and in the per-call log (`llm_raw.jsonl`).

| Field | Type | Meaning |
|---|---|---|
| `episode_id`, `step` | string, int | where in the session |
| `tool`, `target`, `key` | string | the pending action, with the **resolved** target |
| `resolved_targets` | list | for pattern actions: every concrete target |
| `gate` | string | which control reviewed it |
| `gate_decision` | ALLOW / BLOCK / ESCALATE | the control's own decision |
| `final_decision` | ALLOW / BLOCK | after any human review |
| `rules` | list | the rule or rules that fired |
| `confidence` | float or null | a scoring control's score |
| `gate_parse_fail` | bool | the reviewer's answer could not be read (blocked) |
| `human` | object or null | reviewer id, decision, latency |
| `target_read_before` | bool | did the session read the target before trying to change it |
| `reattempt` | bool | the same target was blocked earlier in the session |
| `model`, `realised_model`, `prompt_sha256` | string | what produced the action |
| `ts` | timestamp | |

Episode level: executed irreversible actions with their resolved targets; denied attempts; whether the session ended by finishing, escalating or hitting a limit; the agent's final summary, so that a summary which denies an executed action can be detected.

Two fields exist only in a testbed and never in production: whether the action was truly harmful, and whether recovery restored the state. They are what make the rates in §7 computable.

## 7. Recalibration procedure

1. Build paired tasks from your own incident history and near misses: the same request, once safe and once harmful. Mark each pair by whether your platform's records separate the two versions.
2. Hold out a test set. Never tune anything on it.
3. Run the bare agent first. Its harm rate and its false-hold rate are the baseline for everything else. **[after results]** In this study's pilot the bare agent already held back on some safe tasks.
4. For a scoring control, choose the threshold on a calibration set at a fixed false-hold budget, then measure on the test set. Compare controls at the same budget.
5. Report harm, false holds and escalations together, with intervals that respect the pairing and the fact that tasks from one template are not independent. Never report harm alone.
6. Repeat each task at least three times. Outcomes on single tasks flip between runs.
7. Re-run after any change to the model, its serving, the prompt or the tools. Record the model string the provider actually returned: in this project it changed without notice.
