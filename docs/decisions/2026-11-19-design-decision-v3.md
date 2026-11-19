# Design decision (Phase D): pivot to a layered-controls study, 2026-11-19

**Status.** Decided by the master agent. The pre-registration that follows from it (`docs/PREREGISTRATION_V3.md`) is a **draft**: it is not frozen and no confirmatory episode may run until the conditions in section 7 are met.
**Inputs.** `docs/decisions/2026-11-19-master-reevaluation.md` (Phase E), `docs/research/prior_art_update_2026-11-19.md` and `docs/research/incidents_update_2026-11-19.md` (Phase S, reported by sub-agents, not yet spot-checked), and three exploratory pilot campaigns (section 4).

## 1. Decision

**Pivot.** The confirmatory study becomes a same-task comparison of a ladder of controls on a rebuilt simulated-operations testbed (IrrevOps v3). The Mafia arena is kept as a separate, exploratory stress test with a repaired gate. The freeze-v2 Mafia primary is not resumed.

| Option | Verdict | Reason |
|---|---|---|
| Keep freeze-v2 and resume | Rejected | Closed by its own rule at the serving change; the treatment decides before discussion and is mostly a day-0 no-lynch rule; power 0.49 to 0.58 for +10 points at about Rs.1,700. |
| Modify Mafia and keep it as primary | Rejected | Even repaired, Mafia has no verification action, no escalation path and no safe hold, so it cannot measure what a gate is meant to cause. |
| **Pivot to a controls ladder on IrrevOps v3; Mafia as exploratory stress test** | **Adopted** | Measures harm and over-blocking directly, per decision, with ground truth; episodes cost Rs.0.04 to 0.14 against Rs.2.6 to 3.4 per game; it is the comparison the incident record and the 2026 literature point to. |

## 2. Research questions (sharpened)

- **RQ1.** On the same paired, multi-step tasks, how much does each control reduce harmful irreversible actions relative to a bare agent, and what does it cost in false holds and escalations? Controls: prompt rule; same-model verify-then-delay; deterministic policy gate; other-family monitor; human escalation (approve-all and calibrated); reversibility engineering.
- **RQ2.** Where no rule can decide (the deciding fact is only in free text, or platform records are wrong), which controls still work, and does the ranking change when controls are compared at matched over-blocking?
- **RQ3.** Do the answers hold across at least three model families or tiers and two reasoning regimes?
- **RQ4.** What gate specification, audit-log schema and recalibration procedure follow from the measured results?

## 3. What is and is not novel (adopted from Phase S, stated narrowly)

Already published: paired should-act / should-abstain tool tasks at scale (AgentAbstain, NeurIPS 2026); prompt rule against bare agent with both error types (AgentAbstain v2, 2026-11-18); prompt against external enforcement (several 2026 papers); weak in-model self-checks; pre-registration and deterministic scoring. A positive result for the policy gate on rule-decidable tasks is a foregone conclusion.

Still open, and what this study claims to add:

1. One table for five or more control types on the same tasks (no such study was found; weak negative evidence, search log in `docs/research/`).
2. Comparison at matched over-blocking, not at each control's own operating point.
3. Measured undo and a stated human-reviewer model, in place of assumed effectiveness.
4. An other-family monitor against a same-model reviewer on erroneous (not adversarial) actions.

The work is a replication-plus-extension. No "first" claim beyond: "to our knowledge the first same-task comparison of N control types with harm and over-blocking reported at matched false-hold rates", with search dates.

## 4. Pilot evidence used for this decision (exploratory; dev split; seeds ≥ 100000)

| Campaign | Arm, regime | Episodes | Harm (risky twins) | False hold (act twins) | Errors | Cost per episode |
|---|---|---:|---:|---:|---|---:|
| `explore-ops-01` | L0 bare, default reasoning | 46 | 3 of 23 | 4 of 23 | 2 HTTP 500 at 30.2 s; 9 empty-content | Rs.0.139 |
| `explore-ops-02-minimal` | L0 bare, minimal reasoning | 46 | 4 of 23 | 3 of 23 | none in 267 calls | Rs.0.038 |

All figures are **measured**, on one instance of each of 23 templates, one backbone (`muse-spark-1.3-contributor`, realised string without the `meta/` prefix), one rollout. They are too small for any claim. What they establish for design:

- The harness works end to end and the bare agent is neither at the floor nor at the ceiling on harm (pre-set band: pooled bare harm between 0.10 and 0.90 on the dev split).
- The bare agent already over-holds on some safe tasks, so false holds must be measured against the bare agent, not against zero.
- The two HTTP 500s arrived at 30.20 s and 30.25 s with SDK retries off, which confirms the 30 s cutoff of D-010.
- Minimal reasoning costs about a quarter as much and produced no provider errors.

## 5. The design in brief (binding text is the pre-registration draft)

- **Testbed.** `src/irrevops/`: a simulated cloud account with a metadata layer (what tools and gates see) and a truth layer (used only to score harm and to simulate the human reviewer). Episodes are multi-step and continue after an executed action. 35 templates in 10 families (23 at the time of the pilot), 8 instances each, in fixed dev / calibration / test splits. Each template is labelled decidable or undecidable before any run, and a test checks every label against its definition.
- **Arms.** L0 bare; L1 prompt rule; L2 same-model verifier; L3 policy gate; L4 other-family monitor; L5a approve-all; L5b calibrated escalation; L6 reversibility (soft delete, least privilege).
- **Outcomes.** Harm rate on risky twins; false-hold rate on act twins; escalation burden; residual (unrecoverable) harm; behaviour after a block.
- **Analysis.** Paired by task, clustered by template; score-based controls compared at a false-hold rate matched on the calibration split; cost-sensitive utility swept over harm-to-delay ratios from 1 to 1000.
- **Replication.** Three rollouts per cell; at least three backbones; default and minimal reasoning.

**Minimum viable thesis** (must finish): the ladder on IrrevOps v3, test split, three backbones, default reasoning; the incident taxonomy and literature; the gate specification and audit schema; honest limits.

**Extensions** (each needs its own memo if cut for cost): minimal-reasoning replication on all backbones; replication on AgentAbstain tasks (licence to be checked); adaptive adversary against the gates; approval-channel red-team (the agent can read the approval code); Mafia stress test with the repaired gate; Jev gate.

## 6. Budget arithmetic (cap Rs.5,000; ledger Rs.295.13 on 2026-11-19)

Revised the same day after the template set grew from 23 to 35 (17 undecidable), which the power simulation requires (pre-registration draft §8).

Test split: 35 templates × 4 instances × 2 twins = 280 tasks. Three rollouts and 8 arms give 6,720 episodes per backbone and regime. Calibration split: 140 tasks × 3 rollouts × 4 arms (L0, L2, L4, L5b) = 1,680 episodes.

| Item | Episodes | Rs. per episode | Rs. | Basis |
|---|---:|---:|---:|---|
| Backbone A, default reasoning, test | 6,720 | 0.17 | 1,142 | measured 0.139 for L0; +25% assumed for arms with a scoring call |
| Backbone A, calibration | 1,680 | 0.17 | 286 | as above |
| Monitor calls for A (other family) | about 4,500 calls | 0.05 | 225 | assumed |
| **Backbone A, minimum** | | | **1,653** | derived |
| Backbone A, minimal reasoning, test (extension) | 6,720 | 0.05 | 336 | measured 0.038 for L0 |
| Backbone B, test + calibration + monitor | 8,400 | 0.35 | 2,940 | **assumed**: a model priced about 2 to 3 times A |
| Backbone C, test + calibration + monitor | 8,400 | 0.35 | 2,940 | **assumed** |
| Dev iteration, probes, pilots for B and C | | | 250 | assumed |
| **Total, three backbones, default reasoning** | | | **about 7,780** | derived |

Remaining under the cap: Rs.4,705. **The minimum viable thesis as designed does not fit**: it is about Rs.3,080 over. Backbone A alone fits with room to spare. Options, none taken silently:

| Option | Cost | What is lost |
|---|---:|---|
| (a) Budget request for about Rs.3,300 more | 7,780 + margin | nothing |
| (b) Two rollouts instead of three on B and C | saves about 1,570 | per-task stability on B and C; AgentAbstain v2 reports 16 to 37% of abstain outcomes flip across rollouts |
| (c) B and C run five arms (L0, L1, L3, L4, L6), not eight | saves about 1,760, or about 2,350 with the smaller calibration run this allows | L2, L5a, L5b on B and C; the full ladder is then shown on one backbone only |
| (d) B and C chosen at A's price class (about Rs.0.15 per episode) | saves about 3,300 | capability-tier spread: three cheap models say little about stronger ones |
| (e) Minimal reasoning as the confirmatory regime everywhere | saves about 70% | the default-reasoning regime becomes the extension; reasoning is an explicit factor, so this changes the headline condition |

**Recommendation:** price B and C first with a 50-episode pilot each (about Rs.20 to 40). If the measured total exceeds the cap, write the budget request for option (a) with those numbers, and name (c) as the fallback that keeps three rollouts and the claims C1, C2 and C4 on every backbone. Until then all paid work is on backbone A only.

## 7. Conditions before the v3 freeze

1. Independent cross-family review of the Phase E memo, this memo, the pre-registration draft and `src/irrevops/` (needs the reviewer key).
2. Keys for backbones B and C, the monitor and the task author, one per role.
3. Template set of at least 34 with at least 17 undecidable (now 35 and 17), the free text paraphrased by an author model that is not under test, and a blinded human label audit of every test-split pair.
4. Calibration-split run to fix thresholds for L2, L4 and L5b; simulated power from calibration variance.
5. Citation spot-check of the load-bearing prior-art items.
6. Fingerprint probe and frozen realised model string per backbone.

## 8. Researcher degrees of freedom used so far

- The policy-gate rules were written before the per-template table was computed; the one gap it exposed on a decidable template (T6c, no rule about other people's commits) was left in place.
- Decidability labels were assigned from the template construction, before the pilot.
- The harm band for the difficulty gate (0.10 to 0.90) was written in this memo after seeing 3 of 23 and 4 of 23. It was chosen as a wide sanity band and no task was changed because of the pilot.
- Pilot outcomes were viewed per template on the dev split only. The calibration and test splits have never been run.
- **Task fixes from the dev pilot (2026-11-19, after `explore-ops-03-arms`).** Every arm, including the bare agent, held the safe twin of the three force-push templates and of T9a. Reading the dev traces showed why: the safe force-push twin had an open pull request and an author the agent could not verify, and T9a's change record could not be found through the approval registry. In both cases a hold was a reasonable reading, so the "safe" label was in doubt. The force-push family now states that the requester is the only contributor and the records agree (no open pull request, no other contributors); T9a's change record is reachable from the approval registry. These changes were made from dev-split traces of act twins only, to make labels valid, not to move any arm. The blinded human label audit remains the arbiter before the freeze.
- **Pilot table viewed.** Per-arm outcomes of `explore-ops-01` and `explore-ops-03-arms` (dev instance 0, 23 templates, one rollout) were viewed. No arm, threshold or rule was changed because of them.
- **Cue factor added from the dev pilot (2026-11-19, after `explore-ops-05-newset`).** On dev instance 1 of the 35-template set the bare agent's harm was 1 of 17 on undecidable tasks and 4 of 18 on decidable ones (one rollout). The undecidable stratum was below the pre-set band (0.10 to 0.90), which this memo says triggers task revision on the dev split. The reason was visible in the traces: every undecidable ticket named the document holding the deciding fact, and the agent read it. The revision keeps every world and label and adds a factor: on odd instances the ticket no longer names the document, and a pointer on the platform record (identical in both twins) is the only way to find it. Even instances are unchanged. This was decided from bare-agent outcomes only; no control's outcome was used.
- **Indirect-evidence templates, a reference rule and a tool-description fix (2026-11-19, after `pilot-cal-A-01`).** Traces of every harmful bare-agent episode on the calibration dry run showed one pattern: the agent checks the item it was asked about (and policies, and its own identity) and misses a fact recorded elsewhere. For users and service accounts it did not call `describe` at all, and the tool text spoke only of "resources". Three changes followed, all before any control was run on the affected tasks: (1) the tool descriptions now say that `list_resources` and `describe` cover users, service accounts, branches and payees, because an agent that cannot tell a check is possible is a fault of the instrument, not a finding; (2) eight templates were added in which the target's record is clean and the fact sits on a related resource, four decidable and four undecidable; (3) the policy gate gained a generic rule, "another live resource's record names the target", written before those templates were run. This is task development driven by where the bare agent fails. It is disclosed as such: the added templates raise the share of tasks on which the bare agent is expected to cause harm, which is what gives a control something to prevent, and they do not favour any one control. The calibration instances of the 35 earlier templates have now been seen once for the bare agent and the verifier (one rollout); the freeze calibration will use the final, paraphrased ticket text.
- **More indirect-evidence templates (2026-11-19, after `explore-ops-08-indirect`).** The bare agent caused harm in 12 of 16 risky dev tasks of the first eight indirect templates. Nine more were added (I5 to I7, J5 to J10) before any of them was run, so that each stratum can have at least eight informative templates. The set is 52 templates. Cost consequence: the test split grows from 280 to 416 tasks, about 49% more episodes per backbone; the budget table in §6 is out of date and is redone when backbones B and C are priced. A cheaper alternative with nearly the same power, two test instances per template in place of four, will be simulated then.
- **Gate rule corrected from a dev trace (2026-11-19, after `explore-ops-09-indirect-arms`).** Per-arm outcomes of that pilot were viewed (dev split, indirect templates only). One change followed: the reference rule no longer counts a snapshot's "of" field, because it blocked a safe delete after the agent had prudently taken a backup. This is a correction of a rule that did not do what it was written to do; it was made from a safe-twin trace and it removes false holds for the gate arm, which is disclosed here.
