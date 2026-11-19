"""Which run folders exploratory scripts may read.

Confirmatory campaigns stay blind until they are locked and unblinded once
through the pre-registered analysis. Exploratory scripts glob logs/runs/,
so they must skip those folders. Epoch 1 (`mvp-team-01-cal`) is never
unblinded for design decisions.
"""
import os

CONFIRMATORY_PREFIXES = ("mvp-", "ops-")


def is_blind_run(path_or_name: str) -> bool:
    name = os.path.basename(str(path_or_name).rstrip("/"))
    return name.startswith(CONFIRMATORY_PREFIXES)
