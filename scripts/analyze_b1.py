"""Offline analysis for retest-b1 (no network, no ledger writes).

Reads logs/retest-b1/part1b.jsonl + part2*.jsonl + calibration raws.
Prints Part-1 verdict, per-variant tables with Wilson 95% CIs, decision-rule
evaluation, V0-vs-calibration, persistence, error-header summary.
Writes logs/retest-b1/summary.json.

Usage: .venv/bin/python scripts/analyze_b1.py
"""
import glob
import json
import math
import os
import statistics
import sys

OUT = "logs/retest-b1"
CAL = "logs/runs/mvp-team-01-cal/raw"


def wilson(x, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = x / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - m) / d), min(1.0, (c + m) / d))


def load(name):
    p = os.path.join(OUT, name)
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def reasoning_of(r):
    try:
        return r.get("usage", {}).get("completion_tokens_details", {}).get("reasoning_tokens")
    except Exception:
        return None


def main():
    summary = {}
    # ---- Part 1b ----
    b = load("part1b.jsonl")
    if b:
        by_ctx = {}
        for r in b:
            by_ctx.setdefault(r["ctx"], []).append(r)
        agree_new = sum(1 for rs in by_ctx.values()
                        if len(rs) == 2 and rs[0].get("target") is not None
                        and rs[0]["target"] == rs[1]["target"])
        n_pairs = sum(1 for rs in by_ctx.values() if len(rs) == 2)
        agree_log = sum(1 for r in b if r.get("agree_logged"))
        n_log = sum(1 for r in b if r.get("ok"))
        new_ct = sorted(r["ct"] for r in b if r.get("ok"))
        new_ts = sorted(r["toks"] for r in b if r.get("ok") and r.get("toks"))
        log_ct = sorted(r["logged"]["ct"] for r in b if r.get("ok"))
        log_ts = sorted(round(r["logged"]["ct"] / r["logged"]["lat"], 1)
                        for r in b if r.get("ok") and r["logged"]["lat"] > 0)
        print("== Part 1b fingerprint (raw counts) ==")
        print(f"new-vs-new action agreement: {agree_new}/{n_pairs}")
        print(f"new-vs-Nov12 action agreement: {agree_log}/{n_log}")
        print(f"new ct median {statistics.median(new_ct):.0f} (n={len(new_ct)}); "
              f"logged ct median {statistics.median(log_ct):.0f}")
        print(f"new tok/s median {statistics.median(new_ts):.1f}; "
              f"logged tok/s median {statistics.median(log_ts):.1f}")
        summary["part1b"] = {"agree_new": [agree_new, n_pairs],
                             "agree_logged": [agree_log, n_log],
                             "new_ct_med": statistics.median(new_ct),
                             "logged_ct_med": statistics.median(log_ct),
                             "new_toks_med": statistics.median(new_ts),
                             "logged_toks_med": statistics.median(log_ts)}
    # ---- Part 2 ----
    p2 = load("part2.jsonl")
    if p2:
        def fail(r):
            return (not r["ok"]) or r["empty"] or (not r["parse_ok"])
        conds = sorted({r["cond"] for r in p2})
        print("\n== Part 2 per-variant (all completed calls) ==")
        print("cond n http empty badjson valid fail_rate[95CI] valid_rate[95CI] ct_med")
        stats = {}
        for cn in conds:
            sub = [r for r in p2 if r["cond"] == cn]
            n = len(sub)
            http = sum(1 for r in sub if not r["ok"])
            empty = sum(1 for r in sub if r["ok"] and r["empty"])
            bad = sum(1 for r in sub if r["ok"] and not r["empty"] and not r["parse_ok"])
            valid = n - http - empty - bad
            fl, fh = wilson(http + empty + bad, n)
            vl, vh = wilson(valid, n)
            cts = sorted(r["ct"] for r in sub if r["ok"] and not r["empty"])
            med = statistics.median(cts) if cts else 0
            stats[cn] = {"n": n, "http": http, "empty": empty, "badjson": bad,
                         "valid": valid, "fail_ci": [fl, fh], "valid_ci": [vl, vh],
                         "ct_med": med}
            print(f"{cn} {n} {http} {empty} {bad} {valid} "
                  f"{(http+empty+bad)/n:.3f}[{fl:.3f},{fh:.3f}] "
                  f"{valid/n:.3f}[{vl:.3f},{vh:.3f}] {med:.0f}")
        summary["variants"] = stats
        v0 = stats.get("V0", {})
        v0f = (v0.get("http", 0) + v0.get("empty", 0) + v0.get("badjson", 0)) / max(1, v0.get("n", 1))
        print(f"\nV0 total failure: {v0f:.3f} (n={v0.get('n')})")
        print("decision rule: fail <= min(V0/3, 0.05); valid >= 0.95; ct_med >= 0.6*V0")
        cheap = []
        for cn, s in stats.items():
            if cn == "V0":
                continue
            f = (s["http"] + s["empty"] + s["badjson"]) / s["n"]
            v = s["valid"] / s["n"]
            ok = (f <= v0f / 3) and (f <= 0.05) and (v >= 0.95) and \
                 (s["ct_med"] >= 0.6 * v0.get("ct_med", 0))
            print(f"  {cn}: fail={f:.3f} valid={v:.3f} ct_med={s['ct_med']:.0f} "
                  f"-> {'CHEAP FIX' if ok else 'no'}")
            if ok:
                cheap.append(cn)
        summary["cheap_fix"] = cheap
        # V0 vs calibration by kind (HTTP-error rate)
        print("\n== V0 HTTP-error under new string vs calibration ==")
        for kind, cal in (("night", 0.098), ("dmn_reason", 0.199)):
            sub = [r for r in p2 if r["cond"] == "V0" and r["kind"] == kind]
            h = sum(1 for r in sub if not r["ok"])
            lo, hi = wilson(h, len(sub))
            print(f"{kind}: V0 {h}/{len(sub)}={h/max(1,len(sub)):.3f} [{lo:.3f},{hi:.3f}] "
                  f"vs cal {cal:.3f}")
            summary[f"v0_vs_cal_{kind}"] = {"h": h, "n": len(sub), "ci": [lo, hi], "cal": cal}
        # realised strings
        from collections import Counter
        print("\nrealised strings:", dict(Counter(r.get("realised_model") for r in p2 if r.get("ok"))))
        summary["realised"] = dict(Counter(r.get("realised_model") for r in p2 if r.get("ok")))
        # error headers
        print("\n== error headers ==")
        for r in p2:
            if not r["ok"]:
                h = r.get("headers", {}) or {}
                want = {k: h.get(k) for k in ("x-should-retry", "retry-after",
                                              "x-request-id", "server") if k in h}
                print(f"{r['cond']} {r['ctx']} status={r.get('http_status')} "
                      f"class={r['error_class']} timeout={r.get('is_timeout')} "
                      f"hdrs={want} body={r.get('error_body','')[:160]!r}")
    pa = load("part2_accept.jsonl")
    if pa:
        print("\n== V4 acceptance ==")
        for r in pa:
            u = r.get("usage", {}) or {}
            print(f"{r['cond']}: ok={r['ok']} class={r.get('error_class')} "
                  f"ct={r.get('ct')} reasoning={reasoning_of(r)} "
                  f"usage_keys={sorted(u.keys())}")
        summary["accept"] = [{k: r.get(k) for k in ("cond", "ok", "error_class", "ct", "cost_inr")} for r in pa]
    if p2:
        print("\n== reasoning tokens median by cond (ok rows) ==")
        for cn in sorted({r["cond"] for r in p2}):
            vals = sorted(reasoning_of(r) for r in p2
                          if r["cond"] == cn and r.get("ok") and reasoning_of(r) is not None)
            if vals:
                print(f"{cn}: med={statistics.median(vals):.0f} n={len(vals)}")
        summary["reasoning_med"] = {
            cn: statistics.median(sorted(reasoning_of(r) for r in p2
                                  if r["cond"] == cn and r.get("ok") and reasoning_of(r) is not None))
            for cn in sorted({r["cond"] for r in p2})
            if any(r["cond"] == cn and r.get("ok") and reasoning_of(r) is not None for r in p2)}
    pp = load("part2_persist.jsonl")
    if pp:
        print("\n== persistence ==")
        from collections import Counter
        c = Counter((r["ctx"], r["cond"], r["ok"], r.get("error_class")) for r in pp)
        for k in sorted(c):
            print(f"{k}: {c[k]}")
        summary["persist_n"] = len(pp)
    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1)
    print("\nwrote summary.json")


if __name__ == "__main__":
    sys.exit(main())
