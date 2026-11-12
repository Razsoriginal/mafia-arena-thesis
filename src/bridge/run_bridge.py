"""IrrevOps runner (Pre-reg v2 SS16). Simulated tools only.

python -m src.bridge.run_bridge --campaign bridge-smoke-01 --arms all \
    --tasks F1-0,F5-0 --reps 100600 --workers 4 --lane-cap 5

Each episode runs in its own process with its own raw-log directory, so
its spend is the sum of its raw attempt rows; every episode is ledgered
(campaign bridge-*). Before each submission the ledger total plus a
conservative bound for every in-flight episode must fit both the lane cap
(spend of this campaign) and the global cap. Resume-safe: finished
episode ids are skipped.
"""
import argparse
import json
import os
import subprocess
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from datetime import datetime, timezone

import pandas as pd

from src.eval import run_arena as ra
from src.llm_client import _est_cost_inr

from .agent import ARMS, MAX_STEPS
from .tasks import build_tasks, task_set_sha256

EPISODE_BOUND_INR = (MAX_STEPS + 1) * _est_cost_inr(3000, 2600)  # steps + one verifier call


def _episode_worker(job):
    from src.safety import AuditLogger
    from .agent import run_episode
    from .tasks import build_tasks as _bt

    os.environ["MAFIA_RUN_TAG"] = job["campaign"]
    os.environ["MAFIA_RAW_DIR"] = job["raw_dir"]
    os.makedirs(job["raw_dir"], exist_ok=True)
    task = {t.task_id: t for t in _bt()}[job["task_id"]]
    audit = AuditLogger(path=os.path.join(job["raw_dir"], "safety_audit.parquet"))
    t0 = time.time()
    row = run_episode(task, job["arm"], job["rep"], job["episode_id"], audit=audit)
    audit.flush()
    row["wall_s"] = round(time.time() - t0, 2)
    return row


def _git_sha():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", required=True)
    ap.add_argument("--arms", default="all")
    ap.add_argument("--tasks", default="all", help="comma list of pair ids (F1-0) or task ids, or all")
    ap.add_argument("--reps", default="100600,100700")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--lane-cap", type=float, required=True, help="max Rs. for this campaign")
    a = ap.parse_args()
    if not a.campaign.startswith(("bridge-", "smoke-", "explore-")):
        ap.error("campaign must be prefixed bridge-/smoke-/explore-")
    arms = list(ARMS) if a.arms == "all" else [x.strip() for x in a.arms.split(",")]
    tasks = build_tasks()
    if a.tasks != "all":
        want = {x.strip() for x in a.tasks.split(",")}
        tasks = [t for t in tasks if t.pair_id in want or t.task_id in want]
    reps = [int(x) for x in a.reps.split(",")]
    for r in reps:
        if r < 100000:
            ap.error("bridge reps must use seeds >= 100000")
    out_dir = os.path.join("logs", "runs", a.campaign)
    os.makedirs(out_dir, exist_ok=True)
    ep_path = os.path.join(out_dir, "episodes.parquet")
    done = set(pd.read_parquet(ep_path)["episode_id"]) if os.path.exists(ep_path) else set()
    manifest = {"campaign": a.campaign, "started_at": datetime.now(timezone.utc).isoformat(),
                "git_sha": _git_sha(), "task_set_sha256": task_set_sha256(), "arms": arms,
                "reps": reps, "n_tasks": len(tasks), "lane_cap_inr": a.lane_cap,
                "episode_bound_inr": EPISODE_BOUND_INR, "max_steps": MAX_STEPS}
    with open(os.path.join(out_dir, f"manifest-{int(time.time())}.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    ledger = ra._ledger_path(None)
    jobs = []
    for rep in reps:
        for t in tasks:
            for arm in arms:
                eid = f"{a.campaign}-{t.task_id}-{arm}-r{rep}"
                if eid in done:
                    continue
                jobs.append({"campaign": a.campaign, "task_id": t.task_id, "arm": arm, "rep": rep,
                             "episode_id": eid, "raw_dir": os.path.join(out_dir, "raw", eid)})

    def campaign_spend():
        return sum(float(e.get("cost_inr") or 0) for e in ra._ledger_entries(ledger)
                   if e.get("campaign") == a.campaign)

    rows, inflight, stop = [], {}, False
    ex = ProcessPoolExecutor(max_workers=max(1, a.workers))
    try:
        while (jobs and not stop) or inflight:
            while jobs and not stop and len(inflight) < a.workers:
                need = EPISODE_BOUND_INR * (len(inflight) + 1)
                if campaign_spend() + need > a.lane_cap or ra._ledger_total(ledger) + need > ra.PREREG_BUDGET_CAP:
                    print(f"[{a.campaign}] cap projection reached; no new episodes.")
                    stop = True
                    break
                job = jobs.pop(0)
                inflight[ex.submit(_episode_worker, job)] = job
            if not inflight:
                break
            fin, _ = wait(list(inflight), return_when=FIRST_COMPLETED)
            for f in fin:
                job = inflight.pop(f)
                status = "kept"
                try:
                    row = f.result()
                except ra.BillingExhausted as e:
                    print(f"[{a.campaign}] BILLING EXHAUSTED at {job['episode_id']}: {e}")
                    row, status, stop = None, "discarded", True
                except Exception as e:
                    print(f"[{a.campaign}] episode failed {job['episode_id']}: {type(e).__name__}: {e}")
                    row, status = None, "discarded"
                cost = ra._raw_spend(job["raw_dir"])
                ra._append_ledger(ledger, {"run_tag": a.campaign, "campaign": a.campaign,
                                           "game_id": job["episode_id"], "requested_seed": job["rep"],
                                           "arm": job["arm"], "billed_cost_inr": cost, "est_cost_inr": cost},
                                  campaign=a.campaign, status=status, source="bridge")
                if row is None:
                    continue
                row.update({"campaign": a.campaign, "cost_inr": round(cost, 6), "git_sha": manifest["git_sha"],
                            "task_set_sha256": manifest["task_set_sha256"]})
                rows.append(row)
                ra._upsert(ep_path, pd.DataFrame([row]), ["episode_id"])
                ap_path = os.path.join(job["raw_dir"], "safety_audit.parquet")
                if os.path.exists(ap_path):
                    ra._upsert(os.path.join("logs", "safety_audit.parquet"),
                               pd.read_parquet(ap_path).astype({"step": "int64"}, errors="ignore"),
                               ["episode_id", "step", "ts"])
                print(f"[{a.campaign}] {row['episode_id']}: {row['outcome']} steps={row['n_steps']} "
                      f"Rs.{cost:.4f}", flush=True)
    finally:
        ex.shutdown(wait=True, cancel_futures=True)
    print(f"[{a.campaign}] {len(rows)} episodes this run; campaign spend Rs.{campaign_spend():.4f}")


if __name__ == "__main__":
    main()
