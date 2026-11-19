import json, glob, os, pandas as pd
tot = dict(ep=0, act_harm=0, noop=0, empty_tgt=0, dm=0, pay=0, dup_pay=0, stepcap=0, invalid=0, snap=0)
for p in sorted(glob.glob("logs/runs/explore-ops-*/episodes.parquet")):
    ep = pd.read_parquet(p); c = os.path.basename(os.path.dirname(p))
    n = dict.fromkeys(tot, 0); n["ep"] = len(ep)
    for _, e in ep.iterrows():
        ex = json.loads(e["executed"])
        if e["twin"] == "act" and e["harm"]: n["act_harm"] += 1; print("  act-twin harm:", c, e["task_id"], e["arm"], [(x["tool"], x["target"], x["harm_reason"]) for x in ex if x["harmful"]], "completed", e["completed"])
        n["noop"] += sum(1 for x in ex if "no such target" in x["harm_reason"])
        n["empty_tgt"] += sum(1 for x in ex if x["target"] in ("", ":"))
        pays = [x for x in ex if x["tool"] == "send_payment"]; n["pay"] += len(pays); n["dup_pay"] += max(0, len(pays) - 1)
        n["stepcap"] += e["ended"] == "step_cap"
        try:
            st = json.loads(e["steps"])
            n["invalid"] += sum(1 for s in st if "invalid reply" in s["output"])
            n["dm"] += sum(1 for s in st if s["tool"] == "delete_matching")
            n["snap"] += sum(1 for s in st if s["tool"] == "create_snapshot")
        except Exception as err: print("  steps unparsable", c, e["task_id"], err)
    print(c, n, "arms", sorted(ep["arm"].unique()), "splits", sorted(ep["split"].unique()), "reps", sorted(ep["rep"].unique()))
    for k in tot: tot[k] += n[k]
print("TOTAL", tot)
