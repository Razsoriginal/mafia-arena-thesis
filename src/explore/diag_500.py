"""EXPLORATORY diagnostic (not on the run path): which request features
trigger AiCredits HTTP 500? Paired single-attempt calls on identical
prompts under (json_object, t=0.0), (plain, t=0.0), (json_object, t=0.7).

Campaign loadtest-500diag; every attempt is raw-logged and ledgered; a
lane cap stops the script before it can exceed Rs.3.
Usage: python -m src.explore.diag_500 --n 12 --lane-cap 3.0
"""
import argparse
import json
import os
import random
import time

import pandas as pd

from src.config import settings
from src.eval import run_arena as ra
from src.llm_client import get_client, _est_cost_inr
from src.mafia import prompts as P

CAMPAIGN = "loadtest-500diag"
CONDS = [("json", 0.0), ("plain", 0.0), ("json", 0.7)]


def _history_text(rows):
    return "\n".join(f"[t{r.turn} {r.phase} P{r.speaker}]: {r.text}" for r in rows.itertuples())


def build_prompts(n, seed=100123):
    rng = random.Random(seed)
    files = sorted(f for f in os.listdir("logs/runs/smoke-team-01/raw") if f.startswith("history_"))
    cands = []
    for fn in files:
        h = pd.read_parquet(os.path.join("logs/runs/smoke-team-01/raw", fn))
        for day in range(5):
            idx = h.index[h.phase == f"vote-{day}"]
            if len(idx) == 0:
                continue
            pre = h.loc[: idx[0] - 1]
            hist = _history_text(pre.tail(60))
            alive = list(range(7))
            cands.append(("dmn_reason", P.DMN_SYSTEM, P.dmn_user(3, "villager", hist, alive)))
            cands.append(("night", P.NIGHT_SYSTEM,
                          P.night_user(2, "doctor", alive, _history_text(pre.tail(40)), "save",
                                       [str(a) for a in alive])))
    rng.shuffle(cands)
    return cands[:n]


def one_call(system, user, fmt, temp, max_tokens):
    kw = {"model": settings.model, "temperature": temp, "max_tokens": max_tokens,
          "messages": [{"role": "system", "content": system + ("\nReply with valid JSON only." if fmt == "json" else "")},
                       {"role": "user", "content": user}]}
    if fmt == "json":
        kw["response_format"] = {"type": "json_object"}
    t0 = time.time()
    try:
        r = get_client().chat.completions.create(**kw)
        dt = time.time() - t0
        pt, ct = int(r.usage.prompt_tokens or 0), int(r.usage.completion_tokens or 0)
        billed = getattr(r.usage, "cost", None)
        cost = float(billed) if billed is not None else _est_cost_inr(pt, ct)
        text = (r.choices[0].message.content or "").strip()
        return {"ok": bool(text), "error": None if text else "empty", "latency_s": dt,
                "pt": pt, "ct": ct, "cost_inr": cost, "billed": billed is not None,
                "content_len": len(text)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "latency_s": time.time() - t0,
                "pt": 0, "ct": 0, "cost_inr": 0.0, "billed": False, "content_len": 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--lane-cap", type=float, default=3.0)
    ap.add_argument("--out", default="logs/runs/loadtest-500diag")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    ledger = ra._ledger_path(None)
    prompts = build_prompts(a.n)
    rows, spent = [], 0.0
    per_call_bound = _est_cost_inr(4000, 4000)  # conservative per-call bound
    for i, (purpose, sysm, user) in enumerate(prompts):
        for fmt, temp in CONDS:
            if spent + per_call_bound > a.lane_cap or ra._ledger_total(ledger) + per_call_bound > ra.PREREG_BUDGET_CAP:
                print("lane/global cap reached; stopping"); break
            r = one_call(sysm, user, fmt, temp, settings.max_tokens)
            r.update({"i": i, "purpose": purpose, "fmt": fmt, "temp": temp, "ts": time.time()})
            rows.append(r)
            with open(os.path.join(a.out, "calls.jsonl"), "a") as f:
                f.write(json.dumps(r) + "\n")
            if r["cost_inr"] > 0:
                spent += r["cost_inr"]
                ra._append_ledger(ledger, {"run_tag": CAMPAIGN, "game_id": f"{CAMPAIGN}-{i}-{fmt}-{temp}",
                                           "requested_seed": None, "arm": None,
                                           "billed_cost_inr": r["cost_inr"] if r["billed"] else 0.0,
                                           "est_cost_inr": r["cost_inr"]},
                                  campaign=CAMPAIGN, status="kept", source="loadtest")
            print(i, purpose, fmt, temp, r["ok"], r["error"], round(r["latency_s"], 1), r["ct"])
    df = pd.DataFrame(rows)
    print(df.groupby(["fmt", "temp"]).agg(n=("ok", "size"), ok=("ok", "sum"),
                                         lat=("latency_s", "median"), ct=("ct", "median")))
    print("spent", round(spent, 4))


if __name__ == "__main__":
    main()
