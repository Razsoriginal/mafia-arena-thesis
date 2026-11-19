# Ledger damaged by a machine crash (2026-11-19): paid work stopped, decision needed

**Status.** **Resolved on 2026-11-19.** The user approved the proposed repair. The null bytes were removed by restoring the committed ledger (sha256 `da4c83fe…`, 774 rows, Rs.329.1248) and one row was appended through the normal append function: campaign `explore-ops-04-newset`, status `discarded`, source `crash-reconcile`, Rs.1.00. Ledger total: **Rs.330.12**. Paid work may resume. The text below is the memo as written before the decision.

## What happened

- At 10:12 UTC the exploratory campaign `explore-ops-04-newset` started (bare agent and policy gate, dev split, instance 1 of the 35-template set, 140 episodes planned, lane cap Rs.45).
- The machine went down seconds later and came back at about 11:34 UTC (`uptime` showed 2 minutes at 11:36). No project process survived.
- Files being written at that moment were damaged in the usual way for an unclean shutdown: their length was extended but the data was never flushed, leaving null bytes.

## Damage found (all measured)

| File | State |
|---|---|
| `logs/spend_ledger.jsonl` | 774 valid lines, then 870 null bytes. The first 313,299 bytes are byte-identical to the committed ledger (sha256 `da4c83fe…` for both). Valid total: **Rs.329.1248**. |
| `logs/runs/explore-ops-04-newset/raw/*/llm_raw.jsonl` | 9 files; 13 readable call rows, 11 unreadable (null-filled). Readable spend: Rs.0.2026. |
| `logs/runs/explore-ops-04-newset/episodes.parquet` | readable, 2 episodes (their console lines show Rs.0.0811 and Rs.0.0955). |
| `docs/DISCOVERIES.md` (working copy) | tail overwritten with blanks; the committed version was intact and has been restored from git. |
| Git repository | `git fsck` reports no problem. Everything committed before the crash is intact and was already pushed. |

The two ledger rows for the two finished episodes were among the lost bytes, so **the ledger is short by the real spend of this campaign**.

## Unledgered spend

- Lower bound: Rs.0.2026 (the call rows that can still be read).
- Upper bound (**assumed**): Rs.1.00. Ten episodes had started; two had finished for Rs.0.18 together; the other eight had been running for well under a minute at about Rs.0.01 to 0.04 per call.
- The provider's own usage page would settle it. This adds to the billing check already requested in `2026-11-19-keys-request.md`.

## Proposed repair (needs your go-ahead, because it touches the ledger)

1. Keep the damaged file as evidence: already copied to `logs/archive/crash-2026-11-19/spend_ledger.jsonl.damaged`.
2. Remove only the 870 null bytes, which restores the file to exactly the committed ledger (`git checkout -- logs/spend_ledger.jsonl`). No valid row is changed or removed.
3. Append one row through the normal append function: campaign `explore-ops-04-newset`, status `discarded`, source `crash-reconcile`, amount **Rs.1.00** (the upper bound, so the ledger can only over-state spend), with a pointer to this memo.
4. Leave the damaged `explore-ops-04-newset` bundle in place, never analyse it, and re-run that pilot under a new campaign name.

Alternative: you edit or approve the ledger yourself, or tell me a different amount after checking the provider's usage page.

## Prevention (free, being done now)

- The ledger append and the per-call raw log will `fsync` after each write, so a crash can lose at most the row in flight and cannot leave a null-filled tail.
- The ledger reader will name this failure mode explicitly (null bytes after the last valid row) and point to the repair procedure, without ever repairing by itself.
