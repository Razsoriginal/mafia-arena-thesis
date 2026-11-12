# Bridge freeze (IrrevOps, task set v2)

- **Tag:** `bridge-freeze-v1`. It covers `src/bridge/`, `src/safety/` and the bridge prompts in `src/bridge/agent.py`.
- **Task set:** `build_tasks(seed=100500)`, version 2. sha256 `d0c22d4549f2323c1bdb32e75c8ae8fc1d0cfc52fdc3aed91d8cea08848d7750`. Contents: 60 tasks, 30 pairs, 6 families.
- **Arms:** B0_bare, B1_prompt_rule, B2_external_gate (PolicyGate), B3_verify_delay (SafetyGate, threshold 0.5).
- **Run settings:** max 6 steps; agent temperature 0.7, verifier temperature 0.0; repetitions 100600 and 100700.
- **Smoke spend:** Rs.4.43 against the Rs.5 cap (bridge-smoke-01 Rs.0.93, bridge-smoke-02 Rs.3.50).
- **Pre-freeze changes:** deviation D7 (subtler cues).
- **Pooled smoke result** (D-008): harm at a floor, false holds 13.6%. No tuning toward harm.
- **Full cell:** 480 episodes, about Rs.40 (**derived**). It runs only from the budget left after the primary's projected completion (pre-reg §10 v2), as secondary cell 0.
