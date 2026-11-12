# Draft: revised SYNOPSIS title, motive and objectives (on file, not yet applied)

Follows from `2026-11-12-rescope.md` (Option B). Applying it to `SYNOPSIS.md` is the student's call. Nothing in the study waits on it.

**Tentative title:** *Verify, Then Wait: Calibrated Delay for Irreversible Agent Actions under Deception. A Pre-registered Mafia Study with a Production-like Bridge*

**Motive (replaces §1 opening):** AI agents now take irreversible actions in production systems, and public incident reports show the damage when they act on unverified beliefs. Railway has publicly described an AI agent deleting a production volume through a single API call (blog post and 2026-05-01 changelog). The affected founder, as reported by The Register (2026-04-27), says the agent had guessed rather than verified the scope of the call. In the Replit/SaaStr case (July 2025), a production database was deleted during a code freeze. The recurring pattern is an irreversible act on weak evidence, a rule stated but not followed (a say-do gap), and an acknowledgement only after the fact. This thesis asks when an agent should act irreversibly and when it should delay, verify or escalate. It tests whether a verify-then-calibrated-delay gate reduces wrongful irreversible actions under deception without making the agent uselessly cautious.

## Objectives (replaces §2)

1. **Controlled adversarial testbed.** Build an open 7-player text Mafia arena. The lynch vote is the irreversible action, deception is strategic, ground truth is known for every decision, and every call is logged.
2. **Agent design.** Implement a DMN → TPN → delay-gate agent. DMN imagines motives and exformation, meaning what is left unsaid. TPN verifies against cited turn ids. The gate delays when verified confidence falls below tau. All of this runs on one backbone (`meta/muse-spark-1.3-contributor`). The EVT term is reported as inactive under the frozen constants.
3. **Pre-registered confirmatory comparison.** Compare a DMN village with a CoT village (primary) and with a compute-matched CoT-x3 village (key secondary). Mafia is fixed as CoT. Random-voter and majority-follower villages serve as null floors. The analysis is paired by seed, with a fixed n rule and blinding.
4. **Security-framed metrics.** Measure harm and over-blocking together: wrongful lynches per game, needless holds, delay quality and a per-decision act/abstain confusion matrix. Also report calibrated trust (ECE, Brier, AUROC from an identical probe in every arm) and a say-do gap scoped to the evidence-citation commitment.
5. **Production-like bridge (IrrevOps).** Build paired should-act / should-abstain tasks with simulated irreversible tools (delete volume, drop database, force-push, send payment) under adversarial pressure from injected instructions and false authority. The tasks are derived from a verified incident taxonomy. On the same tasks, compare a bare agent, a prompt-rule agent, an externally enforced gate (`src/safety/guard_tool` with an audit log) and the verify-then-delay gate.
6. **System-One gate (secondary, budget permitting).** Compare an LLM gate with a Jev gate (`typesafe/jev-1.14` via OpenRouter) on latency, cost, stub rate and delay behaviour.
7. **Practitioner artifact.** Release the gate, the audit log, a recalibration checklist and all logs and analysis code. One command regenerates every table and figure.

**Changes against the original synopsis:**
- The Avalon transfer and the vendor-negotiation toy are replaced by the IrrevOps bridge, which maps directly onto real incident classes.
- The ReAct and Constitution comparisons become exploratory appendix cells.
- "Exformation: 1 paper" and "Jev: 0 papers" are withdrawn and replaced by the evidence-backed statements in `docs/research/prior_art.md`.
- The expected outcome is no longer "DMN improves win rate". It is now a powered, pre-registered estimate with permitted wording for both a positive and a null result.
