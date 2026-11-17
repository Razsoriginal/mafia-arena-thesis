# retest-b1: Option-B feasibility diagnostic under the post-change string

Status: COMPLETE 2026-11-17. Pre-registration (§0+§1, committed as 59aff26
BEFORE any Part 1/2 paid call) is preserved verbatim below; results were
placeholders at that commit. Phase-1 verification + fidelity + stoppage:
`logs/retest-b1/REPORT.json` (commit 0756fda). All Part 1/2 results are
"under the post-change string". Raw calls: `logs/retest-b1/part1b.jsonl`,
`part2_accept.jsonl`, `part2.jsonl`, `part2_persist.jsonl`,
`part1a_small.json`, `models_list.json` on branch `explore/retry-test`.

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

## 2. Ten-line summary

1. Spend Rs.5.12 vs Rs.6 cap (Part 1 Rs.0.42/Rs.1; Part 2 Rs.4.70/Rs.5; phase-1 Rs.0.00 + 1 lost call ~Rs.0.05 assumed).
2. Realised string: `muse-spark-1.3-contributor` on all 120 recorded paid calls (0 flips); requested stayed `meta/muse-spark-1.3-contributor`.
3. Part 1a: gateway still lists `meta/muse-spark-1.3-contributor` (436 models); responses carry the unprefixed string; usage exposes reasoning split; `x-aicredits-provider: meta`.
4. Part 1b: new-vs-new 6/9, new-vs-logged 13/18; ct med 887 vs 928; tok/s 107.5 vs 64.8; prompt tokens uniformly -14 on identical text.
5. Part 1 verdict: behaviour consistent with same model per pre-reading (13/18 ~= 6/9); serving changed (string, -14 counting, faster).
6. Decision-rule outcome: NO CHEAP FIX FOUND. V4 passes failure (0/16) and validity (16/16) but fails the ct leg (446 < 1444).
7. V0 under new string: HTTP errors 0/16 (night 0/8 vs cal 9.8%, dmn 0/8 vs cal 19.9%); total failure 10/16 — mode flipped to budget-burn.
8. Best variant vs V0: V4 (reasoning-minimal): 16/16 valid, reasoning med 259 vs 2410, lat ~2-9 s vs ~20 s; quality effect unmeasured.
9. V4 effort setting: both spellings accepted-200 with effect (ct 959 -> ~170 on the probe prompt); kwarg used for the arm.
10. V1/V2 null (8/16 valid each, CIs overlap V0); V3/V5 dropped by pre-registered cap guard (0 calls); persistence: failures stick to contexts, V2 ~= V0 (8/17 vs 6/17 valid).

## 3. Part 1a: gateway listing and response schema

Measured. `GET {base_url}/models` returns 436 entries; the frozen id
`meta/muse-spark-1.3-contributor` is present (`owned_by=aicredits`,
`created=1700000000` — a stub, identical for every entry, uninformative).
Full listing saved in `logs/retest-b1/models_list.json`.

One small call (trivial JSON prompt, max_tokens=64, saved in
`logs/retest-b1/part1a_small.json`): realised
`muse-spark-1.3-contributor`, pt=27, ct=64 (cap hit), cost Rs.0.0017
billed. The call itself is an empty-content specimen: 62 of 64 completion
tokens are `usage.completion_tokens_details.reasoning_tokens`, message
content null. `system_fingerprint` null, `service_tier: default`.
Usage keys: completion/prompt/total_tokens, completion_tokens_details
(reasoning_tokens present), prompt_tokens_details, cost, cost_details
(prompt/completion split in INR), latency_ms. Response keys add id,
created, metadata, moderation, object, service_tier, system_fingerprint
to what calibration logged. Success headers include
`x-aicredits-provider: meta`, `x-aicredits-cost-inr`, `x-request-id`,
`server: cloudflare`; no `x-should-retry` on success.

Side finding (measured): at fixed ct=2500, completion_cost_inr is
identical (0.05426) while prompt_cost_inr rises much faster than linearly
(pt 1033 -> Rs.0.0005, pt 2265 -> Rs.0.0246). Long prompts are
disproportionately expensive on this gateway.

## 4. Part 1b: fingerprint replay

Measured, 18/18 transport-ok, 0 HTTP errors, 0 empties, Rs.0.4183:

- (i) new-vs-new action agreement: 6/9.
- (ii) new-vs-Nov-12 logged action agreement: 13/18 (72%).
- (iii) completion tokens median 887 new vs 928 logged; tokens/s median
  107.5 new vs 64.8 logged.
- Prompt tokens on identical text: uniformly -14 (18/18, zero variance):
  131->117, 133->119, 160->146. A constant shift, not a scaling one:
  chat-template/counting change, not a new tokenizer (derived reading).
- Realised string 18/18 post-change; fingerprints all null.

Verdict per pre-specified reading: (ii) about equal to (i) -> consistent
with the same model. Caveats (all measured): temperature 0.0 is itself
non-deterministic here (6/9 self-agreement); serving is faster than Nov 12
(+66% tok/s); prompt counting changed (-14). Behaviour consistent,
serving changed.

## 5. Part 1c: gateway-changelog questions for the user

I cannot access the gateway account/changelog. Please check, for
~Nov 12-17 2026: (1) was `meta/muse-spark-1.3-contributor` renamed to
`muse-spark-1.3-contributor` in response `model` fields, and do both ids
route to identical weights? (2) did prompt-token counting change (-14 per
2-message call)? (3) any incident/resolution matching calibration's ~93 s
HTTP-500 window on Nov 12? (4) are `reasoning_effort` levels
(default/minimal/xhigh) documented, and did the default change?
(5) on HTTP 500s, does the gateway send `x-should-retry: false` (no 500
occurred in 120 probe calls, so this is unobserved)?

## 6. Part 2: variant probes

Measured, 64 main calls (V0/V1/V2/V4 x 16; V3/V5 0 calls, dropped — see
N1), all transport-ok, all post-change string:

| cond | n | http | empty | badjson | valid | fail [95% CI] | valid [95% CI] | ct_med | reas_med |
|------|---|------|-------|---------|-------|---------------|----------------|--------|----------|
| V0 | 16 | 0 | 6 | 4 | 6 | 0.625 [0.386,0.815] | 0.375 [0.185,0.614] | 2406 | 2410 |
| V1 | 16 | 0 | 6 | 2 | 8 | 0.500 [0.280,0.720] | 0.500 [0.280,0.720] | 1913 | 2179 |
| V2 | 16 | 0 | 7 | 1 | 8 | 0.500 [0.280,0.720] | 0.500 [0.280,0.720] | 1432 | 1956 |
| V4 | 16 | 0 | 0 | 0 | 16 | 0.000 [0.000,0.194] | 1.000 [0.806,1.000] | 446 | 259 |

V0 by kind: night 5 valid/3 empty; dmn 1 valid/4 badjson/3 empty.
Every non-transport failure (19 empty + 7 badjson, all conds) has
ct=2500 exactly: the failure mode on long contexts under the new string
is max-tokens exhaustion (budget burned on reasoning -> empty; truncation
-> invalid JSON). V0 valid-only ct median is 1337.

Decision-rule evaluation (point estimates; n=16 each, directional):
V0 fail 0.625, bar min(V0/3, 0.05)=0.05. V1 fail 0.500 -> no. V2 fail
0.500 -> no. V4 fail 0.000 (<=0.05 ok), valid 1.000 (>=0.95 ok), ct_med
446 vs 0.6*2406=1444 -> FAILS the ct leg (also fails vs valid-only
0.6*1337=802). Outcome: NO CHEAP FIX FOUND. V4 eliminates failures via
~90% reasoning reduction (259 vs 2410); whether decisions stay good is
unmeasured and unmeasurable in this diagnostic (no game outcomes).

V0 vs calibration (HTTP-error): night 0/8 [0,0.324] vs 9.8%; dmn 0/8
vs 19.9%. HTTP errors collapsed to zero (0/120 paid calls overall);
total failure on these hard contexts is 62.5% vs ~36% historical
attempt-0 failure on the same contexts (5/14: 4 http + 1 empty) — the
mode flipped from gateway-timeout to budget-burn. V4 acceptance: both
spellings accepted-200 WITH effect (probe prompt ct 959 -> 178/168,
reasoning 925 -> 141/130); kwarg used for the arm per A8.

## 7. Persistence probe

Measured, 34/36 planned calls (last context cut to 2+2 by the cap halt;
all transport-ok). Valid/total by context:

| context | V0 | V2 |
|---------|----|----|
| 6500 dmn | 0/3 | 0/3 |
| 6300 night | 1/3 | 2/3 |
| 5600 dmn | 0/3 | 0/3 |
| 6600 night | 2/3 | 2/3 |
| 5200 dmn | 3/3 | 3/3 |
| 6100 dmn | 0/2 | 1/2 |

Totals: V0 6/17 valid, V2 8/17 valid — no V2 advantage (small n,
overlapping). Failures stick to contexts (5600/6500 dmn 0/6 across
resends) except 5200 dmn, which failed in main but went 6/6 here (flaky,
not sticky). All persistence failures are ct=2500 budget-burn, same mode.

## 8. Error headers and bodies

No HTTP errors occurred in any of the 120 recorded paid calls (plus 0 in
the acceptance set — same set), so there are no error bodies or error
headers to report; `x-should-retry`/`retry-after` behaviour on 500s is
unobserved. `timeout=150` never triggered (max latency 24.8 s);
`max_retries=0` was moot. Success-header inventory (from §3): request id,
provider, cost, rate-limit triple, Cloudflare markers. Comparability
caveat (derived): production runs SDK-default `max_retries=2`, so
calibration attempt latencies may include hidden SDK sub-retries; probe
latencies cannot (max_retries=0).

## 9. SDK and production-client settings

Measured: `openai` 3.44.0. Production `src/llm_client.py:get_client`
sets neither `max_retries` nor `timeout` (constructs
`OpenAI(base_url, api_key)`); effective SDK defaults are `max_retries=2`,
`timeout=Timeout(connect=5.0, read=600, write=600, pool=600)`. Probes used
a dedicated client (`max_retries=0`, timeout 600 for 1b, 150 for Part 2).

## 10. Raw tables

Spend (ledgered, campaign `retest-b1`, all provider-billed): phase-1
Rs.0.0000 (0 calls) + 1 lost call ~Rs.0.05 assumed; 1a Rs.0.0017 (1);
1b Rs.0.4183 (18); P2 acceptance Rs.0.0310 (3); P2 main Rs.2.8522 (64);
persistence Rs.1.8141 (34). Part 1 Rs.0.4200/Rs.1; Part 2 Rs.4.6973/Rs.5;
retest-b1 total Rs.5.1173/Rs.6. Ledger 281.52 -> 286.64. Reconcile dry
run gap Rs.0.0000 (no task dirs; expected); manual gap = the 1 lost call.

Fingerprint (1b) per prompt (new rep0/rep1 target vs logged): 6/9 pairs
agree; 13/18 reps match logged; details in `part1b.jsonl`. Variant table:
§6. Persistence table: §7. Machine-readable: `summary.json`.

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
- N1 (outcome of pre-registered §1 guard, not a deviation): the
  remaining-plan reserve used worst-case bound Rs.0.12/call, so V5 then V3
  dropped at plan start (0 calls each); realised mean was ~Rs.0.046. A
  mean-based guard would have kept V3 over full persistence; kept as
  executed per §1. V3 (max1500) and V5 (prompt line) are untested.
- N2: persistence ran 34/36 (6100 dmn 2+2) — submission halted by the
  Rs.5 Part-2 guard; pending calls drained and ledgered.
