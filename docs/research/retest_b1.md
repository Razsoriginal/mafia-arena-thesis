# retest-b1: Option-B feasibility diagnostic under the post-change string

Status: PRE-REGISTERED — decision rule and design frozen here BEFORE any
Part 1/2 paid call. (Phase-1 verification + fidelity + stoppage already ran;
see `logs/retest-b1/REPORT.json`. Commit timestamp of this section is the
pre-registration proof; results sections below were placeholders at commit.)

## 0. Decision rule (frozen)

A variant is a "cheap fix" only if, on the same contexts: total failure
rate (HTTP error + empty + invalid JSON) is at most one third of V0's and
at most 5% absolute; valid JSON is at least 95%; median completion tokens
are at least 60% of V0's. Otherwise: "no cheap fix found".

Also reported: V0's failure rate under the new string versus calibration
(night 9.8%, dmn 19.9% first-attempt HTTP-error): a large drop or rise is
itself evidence of a route change. Counts with Wilson 95% CIs; directional
only. n is small; raw counts are primary.

## 1. Design (frozen)

- Contexts: same 8 as phase 1 (4 longest-history night + 4 longest-history
  dmn_reason, distinct game-days; `logs/retest-b1/contexts.json`).
- Part 1a (free + 1 small call): GET `{base_url}/models`; save full response
  object + all headers of one small call; compare field set vs calibration.
- Part 1b (18 calls): 9 exact night-0 rebuilds x 2 reps, t=0.0,
  max_tokens=2500, JSON on, `max_retries=0`, timeout=600 (derived choice:
  production-identical transport; 600 s exceeds all but one calibration
  latency). Metrics: (i) new-vs-new action agreement, (ii) new-vs-Nov-12
  logged action agreement, (iii) completion tokens + tokens/s vs logged.
  Pre-specified reading: (ii) ~= (i) consistent with same model;
  (ii) clearly < (i) means behaviour differs. Raw counts only.
- Part 2 (main): V0 frozen (JSON, t=0.0, 2500); V1 JSON off, t=0.0, 2500
  (suffix text kept — exact P0-R2 retry semantics as first attempt);
  V2 JSON on, t=0.3, 2500; V3 JSON on, t=0.0, max_tokens=1500;
  V4 V0 + reasoning-effort minimal (acceptance pre-probe: `reasoning_effort`
  kwarg vs `extra_body={"reasoning":{"effort":"minimal"}}` on one cheap
  context + one V0 reference; arm uses accepted spelling, kwarg preferred
  on ties; skipped with record if both rejected);
  V5 V0 + one appended user line (prompt-level change, flagged):
  `Deliberate briefly (a few key points only) before answering.`
  Each context x variant x 2 reps, seeded-shuffled interleave,
  `max_retries=0`, `timeout=150`. Per-call records: realised string, id,
  fingerprint, usage incl. reasoning split if exposed, error status/body/
  headers (`x-should-retry`, `retry-after`, `x-request-id`, `server`).
- Persistence: up to 6 V0-failed contexts x (3x V0 + 3x V2), budget permitting.
- Budgets (hard): Part 1 <= Rs.1, Part 2 <= Rs.5, total <= Rs.6 (all phases
  incl. phase-1 Rs.0.00 ledgered). Drop order when near cap: V5, then V3;
  persistence only from remaining budget. Skip logic is pre-shuffle aware
  (remaining-plan reserve), so completed calls stay interleaved.
- Transport: dedicated `OpenAI(base_url, api_key, max_retries=0,
  timeout=...)` client; production `get_client()` untouched. SDK version and
  production-client defaults (`max_retries`, `timeout`) reported from
  measurement. At most 4 in flight. Every paid call ledgered
  (campaign `retest-b1`, source `retry-test`) to the shared absolute ledger.
- Labels: all Part 1/2 results are "under the post-change string".

## 2. Ten-line summary (PENDING at pre-registration)

1. Spend Rs.? vs Rs.6 cap (Part 1 Rs.? / Rs.1, Part 2 Rs.? / Rs.5).
2. Realised string(s): ? (counts ?).
3. Part 1a models listing: ?.
4. Part 1b agreement: new-vs-new ?/9, new-vs-logged ?/18.
5. Part 1 verdict: ?.
6. Decision-rule outcome: ?.
7. V0 failure under new string vs calibration: ?.
8. Best variant vs V0: ?.
9. V4 effort setting: ?.
10. Artifacts: calls + this report on branch `explore/retry-test`.

## 3. Part 1a: gateway listing and response schema (PENDING)

## 4. Part 1b: fingerprint replay (PENDING)

## 5. Part 1c: gateway-changelog questions for the user (PENDING)

## 6. Part 2: variant probes (PENDING)

## 7. Persistence probe (PENDING)

## 8. Error headers and bodies (PENDING)

## 9. SDK and production-client settings (PENDING)

## 10. Raw tables (PENDING)

## 11. Assumptions and deviations (pre-registered)

- A1 (phase 1): truncated spec completed as 4 night + 4 dmn contexts.
- A2 (phase 1): phase-1 conditions superseded by V0-V5; phase-1 plan kept in
  git history and `logs/retest-b1/REPORT.json`.
- A6: 1b timeout=600 (spec silent; production-identical transport otherwise).
- A7: V1 keeps the JSON suffix text (isolates the response_format flag;
  exact P0-R2 retry semantics as a first attempt).
- A8: V4 acceptance pre-probe (3 cheap calls) before the arm; kwarg
  preferred on ties; arm skipped with record if both spellings rejected.
- A9: "6 (context) pairs" read as up to 6 V0-failed contexts; HTTP-error
  contexts first, then empty-content; budget permitting.
- A10: V5 line (exact): `Deliberate briefly (a few key points only) before
  answering.` appended to the user prompt.
