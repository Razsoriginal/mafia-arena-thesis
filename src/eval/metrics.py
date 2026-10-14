"""Metrics v0 — independent definitions. See DESIGN.md."""
import numpy as np
import pandas as pd

def brier(trust_true: list[tuple[float, int]]):
    # trust = P(innocent). label innocent=1, mafia=0
    return float(np.mean([(t - y) ** 2 for t, y in trust_true])) if trust_true else 1.0

def ece(trust_true, n_bins=10):
    if not trust_true:
        return 1.0
    bins = np.linspace(0, 1, n_bins + 1)
    e = 0.0
    trusts = np.array([t for t, _ in trust_true])
    labels = np.array([y for _, y in trust_true])
    for i in range(n_bins):
        m = (trusts > bins[i]) & (trusts <= bins[i + 1])
        if m.sum() > 0:
            e += abs(trusts[m].mean() - labels[m].mean()) * m.sum() / len(trust_true)
    return float(e)

def cascade_resistance(votes_df: pd.DataFrame):
    """When majority vote is wrong, % focal agent did NOT follow. votes_df needs: game_id, day, voter, vote, majority_vote, majority_correct, is_focal."""
    if votes_df.empty:
        return float("nan")
    wrong = votes_df[~votes_df["majority_correct"]]
    if wrong.empty:
        return float("nan")
    focal_wrong = wrong[wrong["is_focal"]]
    resisted = (focal_wrong["vote"] != focal_wrong["majority_vote"]).mean()
    return float(resisted) if len(focal_wrong) else float("nan")

def delay_quality(votes_df: pd.DataFrame):
    """% delays that avoided a wrong lynch."""
    delays = votes_df[votes_df["vote"] == "no-lynch"]
    if delays.empty:
        return float("nan")
    # game-day level: delay good if majority would have been wrong
    g = votes_df.groupby(["game_id", "day"])
    good, total = 0, 0
    for _, grp in g:
        if (grp["is_focal"] & (grp["vote"] == "no-lynch")).any():
            total += 1
            maj = grp["majority_vote"].mode()
            mc = grp["majority_correct"].iloc[0] if "majority_correct" in grp else True
            if not mc:
                good += 1
    return float(good / total) if total else float("nan")

def say_do_gap(turns_df: pd.DataFrame):
    """% votes violating stated commitment to require proof. Heuristic: commitment mentions proof/evidence but vote reason has no turn citation."""
    if turns_df.empty or "commitment" not in turns_df.columns:
        return float("nan")
    gaps = 0
    total = len(turns_df)
    for _, r in turns_df.iterrows():
        c = str(r.get("commitment", "")).lower()
        reason = str(r.get("vote_reason", "")).lower()
        if ("proof" in c or "evidence" in c) and ("t" not in reason and "turn" not in reason and "because" not in reason):
            gaps += 1
    return float(gaps / total) if total else float("nan")
