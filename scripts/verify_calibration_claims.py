"""Verify the Option-B task's claimed calibration facts from raw logs (read-only).

Reads logs/runs/mvp-team-01-cal/raw/task-*/llm_raw.jsonl. Prints measured
numbers for each claim. No network, no ledger writes.
Usage: python scripts/verify_calibration_claims.py
"""
import glob
import json
import os
import statistics
import sys

RAW = "logs/runs/mvp-team-01-cal/raw"


def load():
    rows = []
    for fn in sorted(glob.glob(os.path.join(RAW, "task-*", "llm_raw.jsonl"))):
        task = os.path.basename(os.path.dirname(fn))
        with open(fn, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                r["_task"] = task
                rows.append(r)
    return rows


def failed(r):
    return r.get("error") is not None or r.get("error_class") == "empty_content"


def pct(a, b):
    return 100.0 * a / b if b else float("nan")


def main():
    rows = load()
    print(f"measured total raw rows (attempts): {len(rows)}")
    print(f"measured task dirs: {len({r['_task'] for r in rows})}")
    fails = [r for r in rows if failed(r)]
    print(f"measured failed attempts: {len(fails)} ({pct(len(fails), len(rows)):.1f}%)")

    # Q2: error classes + latency of http_500 failures
    print("\n-- failed attempts by error_class --")
    by_class = {}
    for r in fails:
        by_class[r.get("error_class")] = by_class.get(r.get("error_class"), 0) + 1
    for k, v in sorted(by_class.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v} ({pct(v, len(fails)):.1f}% of failed)")
    h500 = [r for r in fails if r.get("error_class") == "http_500"]
    lat = sorted(r["latency_s"] for r in h500 if r.get("latency_s") is not None)
    if lat:
        in_win = sum(1 for x in lat if 85 <= x <= 100)
        print(f"measured http_500 failed: {len(h500)}; latency median={statistics.median(lat):.1f}s "
              f"min={lat[0]:.1f} max={lat[-1]:.1f}; in [85,100]s: {in_win} ({pct(in_win, len(lat)):.1f}%)")
    lat_all = sorted(r["latency_s"] for r in fails if r.get("latency_s") is not None)
    in_win_all = sum(1 for x in lat_all if 85 <= x <= 100)
    print(f"measured ALL failed with latency: {len(lat_all)}; in [85,100]s: {in_win_all} "
          f"({pct(in_win_all, len(lat_all)):.1f}%); median={statistics.median(lat_all):.1f}s")

    # Q3: first-attempt failure rate by purpose
    print("\n-- attempt==0 failure rate by purpose --")
    first = [r for r in rows if r.get("attempt") == 0]
    purps = sorted({r.get("purpose") for r in first})
    for p in purps:
        sub = [r for r in first if r.get("purpose") == p]
        f = sum(1 for r in sub if failed(r))
        print(f"  {p}: {f}/{len(sub)} = {pct(f, len(sub)):.1f}%")

    # Q4: failure rate by attempt number
    print("\n-- failure rate by attempt number --")
    for a in range(8):
        sub = [r for r in rows if r.get("attempt") == a]
        f = sum(1 for r in sub if failed(r))
        print(f"  attempt {a}: {f}/{len(sub)} = {pct(f, len(sub)):.1f}%")

    # Q5: escalated vs not (retries)
    print("\n-- retry failure by escalated flag --")
    for att_min, label in ((1, "attempt>=1"), (0, "all")):
        sub = [r for r in rows if r.get("attempt", 0) >= att_min]
        for esc in (False, True):
            s2 = [r for r in sub if bool(r.get("escalated")) == esc]
            f = sum(1 for r in s2 if failed(r))
            print(f"  {label} escalated={esc}: {f}/{len(s2)} = {pct(f, len(s2)):.1f}%")

    # Q6: concurrency vs failure (global in-flight at attempt start)
    print("\n-- failure rate by global in-flight concurrency --")
    ev = []
    for r in rows:
        ts, la = r.get("ts"), r.get("latency_s")
        if ts is None or la is None:
            continue
        ev.append((ts - la, 1, r))
        ev.append((ts, -1, r))
    ev.sort(key=lambda e: (e[0], e[1]))
    inflight = {}
    cur = 0
    for t, d, r in ev:
        if d == 1:
            inflight[id(r)] = cur
            cur += 1
        else:
            cur -= 1
    bins = [(0, 2), (3, 5), (6, 9), (10, 100)]
    for lo, hi in bins:
        sub = [r for r in rows if id(r) in inflight and lo <= inflight[id(r)] <= hi]
        f = sum(1 for r in sub if failed(r))
        print(f"  in-flight {lo}-{hi}: {f}/{len(sub)} = {pct(f, len(sub)):.1f}%")
    sub0 = [r for r in rows if r.get("attempt") == 0 and id(r) in inflight]
    for lo, hi in bins:
        s2 = [r for r in sub0 if lo <= inflight[id(r)] <= hi]
        f = sum(1 for r in s2 if failed(r))
        print(f"  first-attempt only, in-flight {lo}-{hi}: {f}/{len(s2)} = {pct(f, len(s2)):.1f}%")

    # Q7: exhausted calls (attempt==7 and failed)
    print("\n-- attempt==7 rows --")
    last = [r for r in rows if r.get("attempt") == 7]
    last_fail = [r for r in last if failed(r)]
    print(f"measured attempt==7 rows: {len(last)}; failed: {len(last_fail)}")
    by_p = {}
    for r in last_fail:
        by_p[r.get("purpose")] = by_p.get(r.get("purpose"), 0) + 1
    print(f"  exhausted-failed by purpose: {by_p}")
    print(f"  exhausted-failed by class: "
          f"{ {c: sum(1 for r in last_fail if r.get('error_class')==c) for c in {r.get('error_class') for r in last_fail}} }")

    # Q8: model/temp/max_tokens/json_mode audit
    print("\n-- config audit --")
    print(f"  distinct realised_model (success): "
          f"{sorted({r.get('realised_model') for r in rows if not failed(r)})}")
    print(f"  distinct requested_model: {sorted({r.get('requested_model') for r in rows})}")
    print(f"  distinct base_url: {sorted({r.get('base_url') for r in rows})}")
    for p in purps:
        sub = [r for r in first if r.get("purpose") == p]
        print(f"  {p}: temp={sorted({r.get('temperature') for r in sub})} "
              f"max_tokens={sorted({r.get('max_tokens') for r in sub})} "
              f"json_mode={sorted({r.get('json_mode') for r in sub})}")
    print("  json_mode=false share by attempt:",
          {a: round(sum(1 for r in rows if r.get('attempt') == a and r.get('json_mode') is False)
                    / max(1, sum(1 for r in rows if r.get('attempt') == a)), 3) for a in range(8)})

    # Q9: costs by purpose (successful rows) + failure cost check
    print("\n-- cost stats (successful rows) by purpose --")
    ok = [r for r in rows if not failed(r)]
    for p in sorted({r.get("purpose") for r in ok}):
        sub = [r for r in ok if r.get("purpose") == p]
        costs = [r.get("cost_inr") or 0 for r in sub]
        est = sum(1 for r in sub if r.get("cost_estimated"))
        print(f"  {p}: n={len(sub)} mean_rs={statistics.mean(costs):.4f} "
              f"median_rs={statistics.median(costs):.4f} max_rs={max(costs):.4f} estimated={est}")
    fcost = [r.get("cost_inr") or 0 for r in fails]
    print(f"  failed rows with cost>0: {sum(1 for c in fcost if c > 0)}/{len(fcost)}; "
          f"total failed-row cost Rs.{sum(fcost):.4f}")
    print(f"  total raw cost Rs.{sum(r.get('cost_inr') or 0 for r in rows):.2f}")

    # Q10: prompt/completion tokens by purpose (success) — sizes for probe design
    print("\n-- token sizes (successful rows) by purpose --")
    for p in sorted({r.get("purpose") for r in ok}):
        sub = [r for r in ok if r.get("purpose") == p]
        pt = sorted(r.get("prompt_tokens") or 0 for r in sub)
        ct = sorted(r.get("completion_tokens") or 0 for r in sub)
        print(f"  {p}: n={len(sub)} pt_med={statistics.median(pt):.0f} pt_max={pt[-1]} "
              f"ct_med={statistics.median(ct):.0f} ct_max={ct[-1]}")


if __name__ == "__main__":
    sys.exit(main())
