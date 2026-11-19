# Chapter 3 — Threat Model and Method (draft v1, 2026-11-12)

> **Superseded on 2026-11-19:** the method sections describe the closed freeze-v2 design; the current method is `ch4_methods.md`. The threat model in §3.1 still applies and will be merged into the taxonomy chapter.

> Binding design: `docs/PREREGISTRATION.md` v2. This chapter explains the design. It does not alter it. Any conflict is resolved in favour of the pre-registration.

## 3.1 Threat model (incident-grounded)

**Asset.** Any state that one tool call can destroy or commit: a production volume, a sole backup, branch history, money, or a player's life in Mafia.

**Adversary and pressure.** We model three sources of pressure that recur in the incident record (`docs/research/incidents.md`):

1. **Deceptive or wrong claims** in the agent's context. Examples are "this is a staging volume", "the CTO approved this", and a Mafia player's misdirection.
2. **Injected instructions** in tool outputs, such as a hidden note in an issue that asks for a destructive action.
3. **Task pressure:** "it's blocking the deploy", "urgent", or "endless delay also loses games".

**Failure of interest.** An *irreversible action taken on an unverified belief*. The agent could have checked, it acted anyway, and the belief was false. It is often accompanied by a stated rule that was not followed (a say-do gap) and by acknowledgement only after the fact.

**Defences compared.**

| Defence | Where it sits | Example in this thesis |
|---|---|---|
| None | — | B0; CoT village |
| In-model restraint | Prompt rules | B1 prompt rule; CoT-x3 (more sampling) |
| Model-side verify-then-delay | Agent architecture, with a gate implemented in code | DMN → TPN → delay gate (Mafia); B3 (bridge) |
| Externally enforced policy | Platform / tool handler | B2 `PolicyGate` via `src/safety/guard_tool` |

**Out of scope, stated explicitly.** These are blast-radius controls: credential scoping, environment separation, soft delete, backup isolation and tool-semantics hazards such as `~` expansion. They were the main vendor fixes in the incident record. Our Mafia arena does not model them. The bridge models only their *metadata* side, namely protected flags that the platform knows. Results on model-side gates must not be read as a substitute for these controls.

## 3.2 Testbed 1: the Mafia arena (confirmatory)

- **Setup.** 7 players: 2 mafia, 1 doctor, 1 detective, 3 villagers.
- **Phases.** Night actions, then two rounds of discussion, then a simultaneous vote. A strict majority of living players is needed to lynch. A `no-lynch` vote is the delay action. The game ends at parity, which is checked after the night kill as well (fix P0-E1), or after a 5-day cap.
- **Why Mafia.** A lynch is irreversible, the mafia deceive strategically and adaptively, and ground truth exists for every decision.
- **Arms.** The 5 village seats play the arm agent. The 2 mafia seats always play CoT, so every arm faces the same opponent.

| Arm | Village agent | Role in the analysis |
|---|---|---|
| `dmn_village` | DMN → TPN → delay gate | treatment |
| `cot_village` | CoT, single vote sample at 0.7 | primary comparator |
| `cotx3_village` | CoT, 3 vote samples at 0.7, majority | compute/sampling control |
| `random_village` | uniform random vote, no LLM | null floor |
| `majority_village` | copies yesterday's plurality, no LLM | null floor (cascade check) |

**The DMN agent, as built and frozen.**

1. **DMN** proposes 2–3 suspects. Each comes with a motive, *exformation* (what is left unsaid or implied, and who benefits) and a confidence.
2. **TPN** verifies those hypotheses against the observable record. It cites turn ids and returns revised confidences.
3. **The gate** delays (votes `no-lynch`) when parsing fails or when the top revised confidence is below tau = 0.35.
   - The EVT term (expectation-violation × threat) is computed and logged.
   - Under the frozen constants it can never exceed its threshold: it is at most 0.467 against 0.6 (Discovery D-001).
   - We therefore call the tested gate a **verified-confidence delay gate**.
4. **The cited vote.** When the gate does not delay, the agent votes under an explicit commitment to cite turn ids.

**Pairing and n.**
- Requested seed 5000 + 100·i fixes the role map in every arm. A seed-trio is the unit of analysis.
- The planned n is 184 trios, re-decided once at calibration by the v2 n rule, with a floor of 171 for confirmatory status.
- Null arms run on the first 80 seeds.

## 3.3 Outcomes

- **Primary.** Village win (draws count as non-wins). The contrast is DMN − CoT, paired by seed, with a 10,000-replicate bootstrap CI.
- **Key secondary.** DMN − CoT-x3.
- **Action-boundary family** (Holm within the family):
  - **S1:** wrongful lynches per game (harm).
  - **S2:** needless-hold rate (over-blocking).
  - **S3:** delay quality.
  - S1 is never reported without S2 and win rate, because an always-abstaining village minimises S1 and loses.
- **Calibration.** A trust probe with identical wording and targets runs in every LLM arm. It is never fed back into play. ECE, Brier and AUC are reported per game-day and pooled. DMN decision-linked trust is reported separately.
- **Descriptive measures.** A per-vote confusion matrix; cascade resistance; abstention; a say-do gap scoped to the DMN citation commitment; cost; JSON failures; game length.

## 3.4 Testbed 2: the IrrevOps bridge (estimation only)

- **Tasks.** 60 simulated tasks: 6 incident-derived families × 5 pairs. Each pair is a should-act twin and a should-abstain twin that share the same ticket. Only hidden state differs, and a read-only tool can reveal it.
- **Arms.** B0 bare, B1 prompt rule, B2 external `PolicyGate`, B3 verify-then-delay (verifier confidence ≥ 0.5).
- **Outcomes.** Harmful-act rate, false-hold rate, paired accuracy, the full confusion matrix, verification-before-action rate, and "claimed verification without a call" (a hallucinated-verification proxy).
- **Analysis.** Paired differences with 95% CIs clustered by task pair. There is no confirmatory test.
- **Isolation.** All tools are in-memory simulations. No real system is ever touched.

## 3.5 Integrity controls

The following controls apply throughout:

- **Pre-registration.**
  - v1 is tagged `prereg-v1`; v2 is amended before the freeze, with a changelog.
  - The machine-readable freeze block binds the prompt hash, the run-path hash and the freeze tag.
  - `--confirmatory` refuses to run on any mismatch.
- **Blinding.**
  - No outcome by arm is computed until the campaign is complete and tagged `primary-locked`.
  - `evaluate.py` and `make_all.py` refuse outcome output without `--unblind`, and refuse it while trios are pending.
- **Spend ledger.**
  - One append-only ledger for every paid call, reconciled against per-attempt raw logs.
  - A hard cap of Rs.2,000, with projections that include in-flight trios.
- **Reproducibility.** Every row carries the campaign, the requested seed and the git sha. One command (`scripts/make_all.py`) regenerates every table and figure.
- **Engineering.**
  - Each fix ships with a failing test first and a mutation proof (`docs/mutation_proofs.md`).
  - Concurrency is proven to change timing only, against a pre-change golden fixture.

## 3.6 Validity notes carried into the results chapter

- **Package contrast.** The DMN arm differs from CoT in architecture *and* in its vote prompt: the CoT prompt ends "endless delay also loses games". Attributing an effect to the gate itself requires the ablation cells.
- **Approximate compute match.** In the smoke run, DMN cost about Rs.4.2 per game against Rs.2.6 for CoT-x3 (n = 2). CoT-x3 matches sampling, not total tokens. Calibration measures this properly.
- **One backbone, one opponent.** Claims are limited to `meta/muse-spark-1.3-contributor`, with CoT mafia.
- **Data not comparable across protocol changes.** Pilot and smoke-team-01 predate the protocol fixes P0-E1 to P0-E3, including the hidden-information leak in the DMN prior (D-004). They are never pooled with confirmatory data.
