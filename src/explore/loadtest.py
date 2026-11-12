"""EXPLORATORY provider load test (P0-S3): latency / timeout rate vs
concurrency, to choose --workers x --call-threads. Single-attempt calls
(no retries) on realistic night/DMN prompts at JSON t=0.0. Campaign
loadtest-conc-01; ledgered; lane cap enforced before every call.
Usage: python -m src.explore.loadtest --levels 1 4 8 16 --per-level 16 --lane-cap 3
"""
import argparse, json, os, threading, time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from src.eval import run_arena as ra
from src.llm_client import _est_cost_inr
from src.explore.diag_500 import build_prompts, one_call
from src.config import settings

CAMPAIGN = "loadtest-conc-01"
_lock = threading.Lock()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", type=int, nargs="+", default=[1, 4, 8, 16])
    ap.add_argument("--per-level", type=int, default=16)
    ap.add_argument("--lane-cap", type=float, default=3.0)
    ap.add_argument("--out", default="logs/runs/loadtest-conc-01")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    ledger = ra._ledger_path(None)
    prompts = build_prompts(max(a.per_level, max(a.levels)), seed=100777)
    bound = _est_cost_inr(3000, 2600)  # realistic worst case at max_tokens 2500
    spent = {"v": 0.0, "stop": False}

    def call(args):
        level, i = args
        with _lock:
            if spent["stop"] or spent["v"] + bound * level > a.lane_cap or \
                    ra._ledger_total(ledger) + bound * level > ra.PREREG_BUDGET_CAP:
                spent["stop"] = True
                return None
        purpose, s, u = prompts[i]
        r = one_call(s, u, "json", 0.0, settings.max_tokens)
        r.update({"level": level, "i": i, "purpose": purpose, "ts": time.time()})
        with _lock:
            spent["v"] += r["cost_inr"]
            with open(os.path.join(a.out, "calls.jsonl"), "a") as f:
                f.write(json.dumps(r) + "\n")
            if r["cost_inr"] > 0:
                ra._append_ledger(ledger, {"run_tag": CAMPAIGN, "game_id": f"{CAMPAIGN}-c{level}-{i}",
                                           "billed_cost_inr": r["cost_inr"] if r["billed"] else 0.0,
                                           "est_cost_inr": r["cost_inr"]}, campaign=CAMPAIGN, source="loadtest")
        return r

    summary = []
    for level in a.levels:
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=level) as ex:
            res = [r for r in ex.map(call, [(level, i) for i in range(max(a.per_level, level))]) if r]
        wall = time.time() - t0
        if not res:
            print("lane cap reached"); break
        df = pd.DataFrame(res)
        s = {"level": level, "n": len(df), "ok": int(df.ok.sum()),
             "timeouts_500": int(df.error.fillna("").str.contains("500").sum()),
             "lat_med": round(df.latency_s.median(), 1), "lat_p90": round(df.latency_s.quantile(0.9), 1),
             "wall_s": round(wall, 1), "calls_per_min": round(60 * len(df) / wall, 2),
             "spent": round(df.cost_inr.sum(), 4)}
        summary.append(s); print(json.dumps(s), flush=True)
        if spent["stop"]:
            print("lane cap reached"); break
    with open(os.path.join(a.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
