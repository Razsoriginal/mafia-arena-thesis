"""Option-B feasibility probes: paired single-attempt calls on rebuilt prompts.

Step 1 (contexts, assumed completion of truncated spec): the 4
longest-history night-action prompts + the 4 longest-history dmn_reason
prompts, each from a distinct (game, day), rebuilt by rebuild_prompts.py.

Conditions (single change vs frozen; single attempt each, no retries):
  A baseline : response_format=json_object, temp=0.0, max_tokens=2500 (frozen)
  B plainflag: NO response_format flag, suffix text kept, temp=0.0, 2500
               (exact P0-R2 retry semantics, tested as a first attempt)
  C temp07   : json_object, temp=0.7, max_tokens=2500
  D max1000  : json_object, temp=0.0, max_tokens=1000

8 contexts x 4 conditions x 2 reps = 64 calls, seeded-shuffled so all
conditions share provider windows. Concurrency <= 4. Every paid call is
ledgered (campaign retest-b1, source retry-test) to the shared absolute
ledger (MAFIA_SPEND_LEDGER). Hard stop: projected spend > Rs.6, realised
model mismatch, or ledger cap breach.

Usage:
  .venv/bin/python scripts/run_probes.py --select-only   # offline: contexts + estimate
  MAFIA_SPEND_LEDGER=/abs/main/logs/spend_ledger.jsonl \
    .venv/bin/python scripts/run_probes.py --run          # online: 64 calls
"""
import argparse
import glob
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.normpath(os.path.dirname(os.path.abspath(__file__))))

from rebuild_prompts import (  # noqa: E402
    RAW, JSON_SUFFIX, proxy_tokens, rebuild_night, rebuild_dmn,
    day_of_each_row, load_raw,
)
from src.config import settings  # noqa: E402
from src.eval import run_arena as ra  # noqa: E402
from src.llm_client import get_client, _est_cost_inr, _parse_json, _error_class  # noqa: E402

CAMPAIGN = "retest-b1"
SOURCE = "retry-test"
FROZEN_MODEL = "meta/muse-spark-1.3-contributor"
FROZEN_BASE = "https://aicredits.in/v1"
# Realised-model gate: defaults to frozen; override only on an explicit
# human/master decision (2026-11-17: provider returned the string without
# the meta/ prefix; run stopped per hard rule 5).
EXPECT_MODEL = os.getenv("RETEST_EXPECT_MODEL", FROZEN_MODEL)
SPEND_CAP = 6.0
PER_CALL_BOUND = 0.09  # above every per-call cost observed in calibration
MAX_INFLIGHT = 4
SHUFFLE_SEED = 7
REPS = 2

CONDS = {
    "A-baseline": {"fmt": "json", "temp": 0.0, "max_tokens": 2500, "suffix": True},
    "B-plainflag": {"fmt": "plain", "temp": 0.0, "max_tokens": 2500, "suffix": True},
    "C-temp07": {"fmt": "json", "temp": 0.7, "max_tokens": 2500, "suffix": True},
    "D-max1000": {"fmt": "json", "temp": 0.0, "max_tokens": 1000, "suffix": True},
}

OUT = "logs/retest-b1"

# measured calibration means (verify_calibration_claims.py) for the estimate
MEAN_COST = {"night": 0.0350, "dmn_reason": 0.0511}


def all_game_ids():
    return sorted(os.path.basename(p)[len("history_"):-len(".parquet")]
                  for p in glob.glob(os.path.join(RAW, "history_*.parquet")))


def select_contexts():
    """Return (nights, dmns): 4 longest distinct-(game,day) each."""
    night_cands, dmn_cands = [], []
    for gid in all_game_ids():
        nights, nmeta = rebuild_night(gid)
        rows, days = nmeta["rows"], nmeta["row_days"]
        ran_night = {}
        for r, d in zip(rows, days):
            if r.get("purpose") == "night":
                ran_night[d] = True
        for day, jobs in nights.items():
            if day not in ran_night:
                continue
            for j in jobs:
                if not j["is_llm"]:
                    continue
                night_cands.append({
                    "kind": "night", "game_id": gid, "day": day,
                    "action": j["action"], "pid": j["pid"], "role": j["role"],
                    "system": j["system"], "user": j["user"],
                    "prefix_rows": j["prefix_rows"],
                    "proxy": proxy_tokens(j["system"], j["user"]),
                })
        dmns, dmeta = rebuild_dmn(gid)
        if not dmns:
            continue
        drows, ddays = dmeta["rows"], dmeta["row_days"]
        ran_dmn = set()
        for r, d in zip(drows, ddays):
            if r.get("purpose") == "dmn_reason":
                ran_dmn.add(d)
        for day, seats in dmns.items():
            if day not in ran_dmn:
                continue
            for s in seats:
                dmn_cands.append({
                    "kind": "dmn_reason", "game_id": gid, "day": day,
                    "action": None, "pid": s["pid"], "role": s["role"],
                    "system": s["system"], "user": s["user"],
                    "prefix_rows": s["prefix_rows"],
                    "proxy": proxy_tokens(s["system"], s["user"]),
                })
    night_cands.sort(key=lambda c: (-c["prefix_rows"], -c["proxy"]))
    dmn_cands.sort(key=lambda c: (-c["prefix_rows"], -c["proxy"]))

    def top4_distinct(cands):
        out, seen = [], set()
        for c in cands:
            if (c["game_id"], c["day"]) in seen:
                continue
            seen.add((c["game_id"], c["day"]))
            out.append(c)
            if len(out) == 4:
                break
        return out

    return top4_distinct(night_cands), top4_distinct(dmn_cands)


def historical_baseline(ctx):
    """Attempt-0 outcomes of the matching historical call(s). Free context."""
    rows = load_raw(f"task-{ctx['game_id']}")
    days = day_of_each_row(rows)
    if ctx["kind"] == "night":
        sub = [r for r, d in zip(rows, days)
               if d == ctx["day"] and r.get("purpose") == "night" and r.get("attempt") == 0]
        mine = []
        for r in sub:
            if r.get("error") is not None:
                mine.append(("http-error", r.get("error_class")))
                continue
            try:
                raw = json.loads(r.get("raw") or "")
            except Exception:
                raw = {}
            if isinstance(raw, dict) and ctx["action"] in raw:
                cls = r.get("error_class") or "ok"
                mine.append(("action-match", cls))
        return {"attempt0_night_rows": len(sub), "matched": mine}
    sub = [r for r, d in zip(rows, days)
           if d == ctx["day"] and r.get("purpose") == "dmn_reason" and r.get("attempt") == 0]
    return {"attempt0_dmn_rows": len(sub),
            "outcomes": [(r.get("error_class") or "ok") for r in sub]}


def one_call(ctx, cond_name, cond, rep):
    system = ctx["system"]
    if not cond["suffix"]:
        system = system.removesuffix(JSON_SUFFIX)
    kw = {"model": settings.model, "temperature": cond["temp"],
          "max_tokens": cond["max_tokens"],
          "messages": [{"role": "system", "content": system},
                       {"role": "user", "content": ctx["user"]}]}
    if cond["fmt"] == "json":
        kw["response_format"] = {"type": "json_object"}
    rec = {"ctx": f"{ctx['kind']}/{ctx['game_id']}/day{ctx['day']}"
                   f"/{ctx['action'] or ctx['pid']}",
           "kind": ctx["kind"], "cond": cond_name, "rep": rep,
           "ts": time.time(), "requested_model": settings.model}
    t0 = time.time()
    try:
        r = get_client().chat.completions.create(**kw)
        dt = time.time() - t0
        pt = int(r.usage.prompt_tokens or 0)
        ct = int(r.usage.completion_tokens or 0)
        billed = getattr(r.usage, "cost", None)
        cost = float(billed) if billed is not None else _est_cost_inr(pt, ct)
        text = (r.choices[0].message.content or "").strip()
        rec.update({"ok": True, "error": None, "error_class": None,
                    "latency_s": round(dt, 3), "pt": pt, "ct": ct,
                    "cost_inr": cost, "billed": billed is not None,
                    "realised_model": getattr(r, "model", None),
                    "content_len": len(text), "empty": not bool(text),
                    "parse_ok": _parse_json(text) is not None,
                    "raw": text[:4000]})
    except Exception as e:
        dt = time.time() - t0
        rec.update({"ok": False, "error": str(e)[:200],
                    "error_class": _error_class(e), "latency_s": round(dt, 3),
                    "pt": 0, "ct": 0, "cost_inr": 0.0, "billed": False,
                    "realised_model": None, "content_len": 0,
                    "empty": None, "parse_ok": False, "raw": ""})
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--select-only", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if not (a.select_only or a.run):
        ap.error("pass --select-only or --run")

    nights, dmns = select_contexts()
    contexts = nights + dmns
    assert len(contexts) == 8, len(contexts)
    print("selected contexts (ranked by history length):")
    for c in contexts:
        print(f"  {c['kind']:10s} {c['game_id']} day={c['day']} "
              f"{c['action'] or ('pid' + str(c['pid']))} prefix_rows={c['prefix_rows']} "
              f"proxy={c['proxy']}")
    print("\nhistorical attempt-0 outcomes for these exact calls (measured, free):")
    for c in contexts:
        print(f"  {c['kind']}/{c['game_id']}/day{c['day']}/{c['action'] or c['pid']}: "
              f"{historical_baseline(c)}")

    n_calls = len(contexts) * len(CONDS) * REPS
    est = sum(MEAN_COST[c["kind"]] for c in contexts) * len(CONDS) * REPS
    print(f"\nplan: {len(contexts)} contexts x {len(CONDS)} conds x {REPS} reps = "
          f"{n_calls} calls")
    print(f"cost estimate (measured purpose means): Rs.{est:.2f}; "
          f"worst-case bound {n_calls} x Rs.{PER_CALL_BOUND} = Rs.{n_calls * PER_CALL_BOUND:.2f} "
          f"(cap Rs.{SPEND_CAP})")
    if a.select_only and not a.run:
        return

    # ---- online phase ----
    assert settings.model == FROZEN_MODEL, f"model {settings.model} != frozen"
    assert settings.base_url == FROZEN_BASE, f"base {settings.base_url} != frozen"
    assert not settings.model.endswith("free"), "free-tier model?"
    assert settings.api_key, "no API key in environment (source main .env)"
    ledger = ra._ledger_path(None)
    assert os.path.isabs(ledger) and "mafia-arena-thesis" in ledger, ledger
    print(f"model={settings.model} base={settings.base_url} expect_realised={EXPECT_MODEL}")
    print(f"shared ledger: {ledger}")
    print(f"ledger total before: Rs.{ra._ledger_total(ledger):.2f} "
          f"(cap Rs.{ra.PREREG_BUDGET_CAP:.0f})")
    assert ra._ledger_total(ledger) + SPEND_CAP <= ra.PREREG_BUDGET_CAP

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "contexts.json"), "w", encoding="utf-8") as f:
        json.dump({"conds": CONDS, "contexts": contexts,
                   "shuffle_seed": SHUFFLE_SEED, "reps": REPS}, f)
    plan = [(ci, cn, rep) for ci in range(len(contexts))
            for cn in CONDS for rep in range(REPS)]
    random.Random(SHUFFLE_SEED).shuffle(plan)
    spent, done = 0.0, 0
    calls_path = os.path.join(OUT, "calls.jsonl")
    if os.path.exists(calls_path):
        raise SystemExit(f"{calls_path} exists; refusing to append (re-run safety)")

    def run_one(job):
        ci, cn, rep = job
        return one_call(contexts[ci], cn, CONDS[cn], rep)

    def handle(rec):
        nonlocal spent, done
        with open(calls_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        if rec["cost_inr"] > 0:
            spent += rec["cost_inr"]
            ra._append_ledger(
                ledger, {"run_tag": CAMPAIGN,
                         "game_id": f"{CAMPAIGN}-{rec['ctx']}-{rec['cond']}-r{rec['rep']}",
                         "requested_seed": None, "arm": None,
                         "billed_cost_inr": rec["cost_inr"] if rec["billed"] else 0.0,
                         "est_cost_inr": rec["cost_inr"]},
                campaign=CAMPAIGN, status="kept", source=SOURCE)
        done += 1
        print(f"[{done}/{len(plan)}] {rec['ctx']} {rec['cond']} "
              f"ok={rec['ok']} err={rec['error_class']} lat={rec['latency_s']} "
              f"ct={rec['ct']} cost={rec['cost_inr']:.4f} spent={spent:.4f}", flush=True)
        # record-then-raise: a mismatching call is still evidence and spend
        if rec["realised_model"] is not None and rec["realised_model"] != EXPECT_MODEL:
            raise SystemExit(f"REALISED MODEL MISMATCH: {rec['realised_model']} "
                             f"(expected {EXPECT_MODEL})")
        if spent + MAX_INFLIGHT * PER_CALL_BOUND > SPEND_CAP:
            raise SystemExit(f"spend cap guard: spent Rs.{spent:.2f}; stopping")

    # first call synchronous: realised-model gate before any parallelism
    handle(run_one(plan[0]))
    with ThreadPoolExecutor(max_workers=MAX_INFLIGHT) as ex:
        for rec in ex.map(run_one, plan[1:]):
            handle(rec)
    print(f"\ndone: {done} calls, probe spend Rs.{spent:.4f}")
    print(f"ledger total after: Rs.{ra._ledger_total(ledger):.2f}")


if __name__ == "__main__":
    main()
