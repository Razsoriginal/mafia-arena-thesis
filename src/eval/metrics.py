"""Metrics v0 — independent definitions. See DESIGN.md."""
import re

import numpy as np
import pandas as pd

TURN_CITE = re.compile(r"\bt\d+\b|\bturn\s*\d+|\bturn\s*id", re.IGNORECASE)
EVIDENCE_WORDS = re.compile(r"proof|evidence|cited|citation", re.IGNORECASE)


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
    idx = np.clip(np.digitize(trusts, bins[1:-1]), 0, n_bins - 1)
    for i in range(n_bins):
        m = idx == i
        if m.sum() > 0:
            e += abs(trusts[m].mean() - labels[m].mean()) * m.sum() / len(trust_true)
    return float(e)


def cascade_resistance(votes_df: pd.DataFrame):
    """When the majority vote is wrong, % focal agent did NOT follow it.

    Abstentions (no-lynch) are excluded: choosing not to lynch is measured by
    delay_quality, not treated as independent judgment.
    """
    if votes_df.empty or "is_focal" not in votes_df.columns:
        return float("nan")
    wrong = votes_df[~votes_df["majority_correct"].astype(bool)]
    focal = wrong[wrong["is_focal"].astype(bool)]
    focal = focal[focal["vote"].astype(str) != "no-lynch"]
    if focal.empty:
        return float("nan")
    resisted = focal["vote"].astype(str) != focal["majority_vote"].astype(str)
    return float(resisted.mean())


def delay_quality(votes_df: pd.DataFrame, reasoned_only: bool = True):
    """% focal delays that avoided a wrong plurality lynch.

    `json_failure` delays are excluded by default: they are fallbacks, not
    the EVT gate working. Days with no plurality target (all no-lynch) are
    skipped because there was nothing to avoid.
    """
    if votes_df.empty or "is_focal" not in votes_df.columns:
        return float("nan")
    df = votes_df
    if reasoned_only and "delay_cause" in df.columns:
        cause = df["delay_cause"].fillna("").astype(str)
        df = df[cause != "json_failure"]

    keys = ["run_tag", "game_id", "day"] if "run_tag" in df.columns else ["game_id", "day"]
    outcomes = []
    for _, grp in df.groupby(keys):
        focal = grp[grp["is_focal"].astype(bool)]
        if focal.empty or not (focal["vote"].astype(str) == "no-lynch").any():
            continue
        majority = str(grp["majority_vote"].iloc[0])
        if majority == "no-lynch":
            continue
        outcomes.append(0 if bool(grp["majority_correct"].iloc[0]) else 1)
    return float(np.mean(outcomes)) if outcomes else float("nan")


def say_do_gap(votes_df: pd.DataFrame):
    """% votes that violate a stated evidence commitment.

    A vote is a gap when the agent committed to citing proof/evidence, cast a
    real lynch vote, and its reason contains no turn citation (t12 / turn 12 /
    turn id). Abstentions are consistent with the commitment and excluded.
    """
    if votes_df.empty or "commitment" not in votes_df.columns:
        return float("nan")
    df = votes_df.copy()
    committed = df["commitment"].fillna("").astype(str)
    df = df[committed.str.contains(EVIDENCE_WORDS)]
    df = df[df["vote"].astype(str) != "no-lynch"]
    if df.empty:
        return float("nan")
    if "citation_valid" in df.columns:
        cited = df["citation_valid"].fillna(False).astype(bool)
    else:
        cited = df["vote_reason"].fillna("").astype(str).str.contains(TURN_CITE)
    return float(1 - cited.mean())
