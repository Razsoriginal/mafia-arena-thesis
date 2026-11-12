"""Ledger any raw-logged spend of an interrupted run (pause/kill/crash).

The runner reconciles a trio's raw spend when the trio finalises; a killed
process leaves in-flight games' spend in raw logs only. This appends the
gap for every task dir of the run tag as status=discarded,
source=raw-reconcile (same function the runner uses; never rewrites).

    .venv/bin/python scripts/reconcile_ledger.py mvp-team-01-cal            # dry run
    .venv/bin/python scripts/reconcile_ledger.py mvp-team-01-cal --apply
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))
from src.eval import run_arena as ra  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_tag")
    ap.add_argument("--campaign", default=None)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    ledger = ra._ledger_path(None)
    entries = ra._ledger_entries(ledger)
    total = 0.0
    for d in sorted(glob.glob(os.path.join("logs", "runs", a.run_tag, "raw", "task-*"))):
        gid = os.path.basename(d)[len("task-"):]
        raw = ra._raw_spend(d)
        led = sum(float(e.get("cost_inr") or 0) for e in entries
                  if e.get("run_tag") == a.run_tag and e.get("game_id") == gid)
        gap = round(raw - led, 6)
        if gap > 1e-6:
            total += gap
            print(f"{gid}: raw Rs.{raw:.4f} ledgered Rs.{led:.4f} gap Rs.{gap:.4f}")
            if a.apply:
                parts = gid.rsplit("-", 2)
                seed = int(parts[-2]) if len(parts) >= 3 and parts[-2].isdigit() else None
                ra._reconcile_task_spend(ledger, raw_dir=d, run_tag=a.run_tag,
                                         campaign=a.campaign or gid.rsplit("-", 2)[0],
                                         game_id=gid, requested_seed=seed, arm=parts[-1])
    print(f"unledgered spend: Rs.{total:.4f} ({'appended' if a.apply else 'dry run'})")


if __name__ == "__main__":
    main()
