"""One command for every published number that does not need unblinding.

    .venv/bin/python scripts/reproduce_all.py            # free, a few minutes
    .venv/bin/python scripts/reproduce_all.py --quick    # skip the simulations

Runs, in order, and stops at the first failure:
  1. the unit tests (which include the pilot regression numbers);
  2. the ledger total and its breakdown by campaign;
  3. D-005, D-006 and D-010/D-013 exploratory analyses from raw logs;
  4. the power simulations (pre-reg v2 primary, pre-reg v3 design);
  5. nuisance tables for the Mafia campaign (blinded);
  6. IrrevOps v3 tables for every campaign under logs/runs/ that has an
     episodes.parquet with v3 columns (exploratory campaigns: outcomes;
     confirmatory campaigns: nuisance only unless locked and --unblind).
Outputs go to logs/explore/ and docs/thesis/assets/. Epoch 1 outcomes are
never computed here.
"""
import argparse
import glob
import json
import os
import subprocess
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
PY = sys.executable


def run(cmd, out=None):
    print("$", " ".join(cmd), flush=True)
    res = subprocess.run(cmd, cwd=ROOT, capture_output=bool(out), text=True)
    if res.returncode != 0:
        if out:
            print(res.stdout[-2000:], res.stderr[-2000:])
        raise SystemExit(f"FAILED: {' '.join(cmd)}")
    if out:
        os.makedirs(os.path.dirname(os.path.join(ROOT, out)), exist_ok=True)
        with open(os.path.join(ROOT, out), "w") as f:
            f.write(res.stdout)


def ledger():
    sys.path.insert(0, ROOT)
    from src.eval import run_arena as ra
    path = os.path.join(ROOT, "logs", "spend_ledger.jsonl")
    by = {}
    for e in ra._ledger_entries(path):
        k = str(e.get("campaign") or e.get("run_tag"))
        by[k] = round(by.get(k, 0.0) + float(e.get("cost_inr") or 0), 4)
    total = round(sum(by.values()), 4)
    os.makedirs(os.path.join(ROOT, "logs", "explore"), exist_ok=True)
    with open(os.path.join(ROOT, "logs", "explore", "ledger_summary.json"), "w") as f:
        json.dump({"total_inr": total, "cap_inr": ra.PREREG_BUDGET_CAP, "by_campaign": by}, f, indent=1)
    print(f"ledger total Rs.{total} of cap Rs.{ra.PREREG_BUDGET_CAP}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    run([PY, "-m", "unittest", "discover", "-s", "tests"], out="logs/explore/unittest_last.txt")
    ledger()
    run([PY, "-m", "src.explore.exformation_auc"])
    run([PY, "-m", "src.explore.game_length"])
    run([PY, "-m", "src.explore.latency_forensics"])
    if not a.quick:
        run([PY, "scripts/power_sim.py"], out="logs/explore/power_sim_v2.json")
        run([PY, "scripts/power_sim_v3.py"], out="logs/explore/power_sim_v3.json")
    run([PY, "scripts/make_all.py", "--campaign", "mvp-team-01"])
    for ep in sorted(glob.glob(os.path.join(ROOT, "logs", "runs", "*", "episodes.parquet"))):
        camp = os.path.basename(os.path.dirname(ep))
        if camp.startswith("bridge-"):
            continue  # v2 bridge: closed design, different schema
        run([PY, "-m", "src.irrevops.analysis", "--campaign", camp])
    print("all regenerated")


if __name__ == "__main__":
    main()
