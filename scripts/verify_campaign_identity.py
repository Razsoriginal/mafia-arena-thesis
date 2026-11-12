"""At-lock identity check for a confirmatory campaign (Pre-reg v2 SS15 D6).

Every manifest of the campaign records the frozen runpath/prompt hashes,
and every row's git_sha descends from the freeze tag with no run-path diff.
Usage: .venv/bin/python scripts/verify_campaign_identity.py mvp-team-01
"""
import glob, json, os, subprocess, sys
import pandas as pd
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))
from src.eval import run_arena as ra  # noqa: E402

camp = sys.argv[1]
freeze = ra._parse_freeze_block(open("docs/PREREGISTRATION.md").read())["fields"]
tag = freeze["freeze_tag"]
bad = []
mans = [m for m in glob.glob("logs/runs/*/manifest.json") if json.load(open(m)).get("campaign") == camp]
for m in mans:
    d = json.load(open(m))
    if d.get("runpath_sha256") != freeze["runpath_sha256"] or d.get("prompts_sha256") != freeze["prompts_sha256"]:
        bad.append(f"manifest hash mismatch: {m}")
g = pd.read_parquet("logs/games.parquet")
g = g[g["campaign"].astype(str) == camp]
rel = ra._runpath_relpaths()
for sha in sorted(set(g["git_sha"].astype(str))):
    if subprocess.run(["git", "merge-base", "--is-ancestor", tag, sha]).returncode != 0:
        bad.append(f"{sha} does not descend from {tag}")
        continue
    diff = subprocess.run(["git", "diff", "--name-only", tag, sha, "--"] + rel, capture_output=True, text=True).stdout.strip()
    if diff:
        bad.append(f"{sha} changes run-path files: {diff}")
print(f"campaign {camp}: {len(mans)} manifests, {len(g)} rows, {g['git_sha'].nunique()} shas")
print("IDENTITY OK" if not bad else "IDENTITY FAILED:\n" + "\n".join(bad))
sys.exit(1 if bad else 0)
