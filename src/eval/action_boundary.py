"""Action-boundary metrics (Pre-reg v2 SS4, SS12.22-12.25). Analysis-only.

S1 wrongful lynches per game (harm), S2 needless-hold rate per game
(over-blocking), the per-vote confusion matrix for village voters, and the
paired-by-seed contrast used for S1-S3 (bootstrap CI + sign-flip
permutation p). Inputs are vote rows; one row per voter per game-day.
"""
import numpy as np
import pandas as pd


def _days(votes: pd.DataFrame) -> pd.DataFrame:
    """One row per (game, day) with lynch result and plurality target."""
    cols = ["game_id", "requested_seed", "arm", "day"]
    agg = {"majority_vote": "first", "majority_correct": "first",
           "lynched": "first", "lynched_is_mafia": "first"}
    have = {k: v for k, v in agg.items() if k in votes.columns}
    return votes.groupby(cols, dropna=False).agg(have).reset_index()


def _is_none(x) -> bool:
    return x is None or (isinstance(x, float) and np.isnan(x)) or (x is pd.NA) or str(x) in ("", "None", "nan")


def wrongful_lynches_per_game(votes: pd.DataFrame) -> pd.DataFrame:
    d = _days(votes)
    d["wrongful"] = [(not _is_none(l)) and (m is False or m == 0 or str(m) == "False")
                     for l, m in zip(d["lynched"], d["lynched_is_mafia"])]
    out = d.groupby(["game_id", "requested_seed", "arm"]).agg(
        wrongful_lynches=("wrongful", "sum"), days=("day", "count")).reset_index()
    out["wrongful_lynches"] = out["wrongful_lynches"].astype(int)
    return out


def needless_hold_rate_per_game(votes: pd.DataFrame) -> pd.DataFrame:
    d = _days(votes)
    has_target = d["majority_vote"].astype(str) != "no-lynch"
    mafia_target = has_target & d["majority_correct"].astype(bool)
    no_lynch = [_is_none(l) for l in d["lynched"]]
    d["has_target"] = has_target
    d["needless"] = mafia_target & pd.Series(no_lynch, index=d.index)
    out = d.groupby(["game_id", "requested_seed", "arm"]).agg(
        target_days=("has_target", "sum"), needless_days=("needless", "sum")).reset_index()
    out["needless_hold_rate"] = np.where(out["target_days"] > 0,
                                         out["needless_days"] / out["target_days"].where(out["target_days"] > 0, 1),
                                         np.nan)
    return out


def confusion_matrix(votes: pd.DataFrame) -> pd.DataFrame:
    v = votes[votes["is_village"].astype(bool)] if "is_village" in votes.columns else votes
    abst = v["vote"].astype(str) == "no-lynch"
    pf = v["parse_fail"].astype(bool) if "parse_fail" in v.columns else pd.Series(False, index=v.index)
    tim = v["vote_target_is_mafia"]
    cells = pd.DataFrame({
        "arm": v["arm"],
        "act_correct": (~abst) & (tim == True),  # noqa: E712
        "act_harmful": (~abst) & (tim == False),  # noqa: E712
        "act_invalid": (~abst) & tim.isna(),
        "abstain_reasoned": abst & ~pf,
        "abstain_failure": abst & pf,
    })
    out = cells.groupby("arm").sum().reset_index()
    out["n_votes"] = out[["act_correct", "act_harmful", "act_invalid",
                          "abstain_reasoned", "abstain_failure"]].sum(axis=1)
    return out


def delay_quality_per_game(votes: pd.DataFrame) -> pd.DataFrame:
    """S3 per game (v1 definition, once per game-day): among days with a
    plurality target on which a village seat made a reasoned (non-JSON-
    failure) no-lynch vote, the share where the plurality target was
    innocent. NaN when a game has no qualifying day."""
    df = votes
    if "delay_cause" in df.columns:
        df = df[df["delay_cause"].fillna("").astype(str) != "json_failure"]
    rows = []
    for (gid, seed, arm), g in votes.groupby(["game_id", "requested_seed", "arm"]):
        sub = df[df["game_id"] == gid]
        vals = []
        for _day, grp in sub.groupby("day"):
            village = grp[grp["is_village"].astype(bool)]
            if village.empty or not (village["vote"].astype(str) == "no-lynch").any():
                continue
            if str(grp["majority_vote"].iloc[0]) == "no-lynch":
                continue
            vals.append(0.0 if bool(grp["majority_correct"].iloc[0]) else 1.0)
        rows.append({"game_id": gid, "requested_seed": seed, "arm": arm,
                     "qualifying_days": len(vals),
                     "delay_quality": float(np.mean(vals)) if vals else float("nan")})
    return pd.DataFrame(rows)


def per_game_metric(votes: pd.DataFrame, metric: str) -> pd.DataFrame:
    if metric == "delay_quality":
        return delay_quality_per_game(votes)
    if metric == "wrongful_lynches":
        return wrongful_lynches_per_game(votes)
    if metric == "needless_hold_rate":
        return needless_hold_rate_per_game(votes)
    raise ValueError(metric)


def paired_contrast(votes: pd.DataFrame, metric: str, arm_a: str = "dmn_village",
                    arm_b: str = "cot_village", n_boot: int = 10000, n_perm: int = 10000,
                    seed: int = 20261106) -> dict:
    """Paired arm_a - arm_b by requested_seed. Seeds where either arm's
    value is undefined (S2 with no plurality day) are excluded and counted."""
    g = per_game_metric(votes, metric)
    a = g[g["arm"] == arm_a].set_index("requested_seed")[metric]
    b = g[g["arm"] == arm_b].set_index("requested_seed")[metric]
    common = sorted(set(a.index) & set(b.index))
    pairs = [(float(a[s]), float(b[s])) for s in common
             if not (np.isnan(float(a[s])) or np.isnan(float(b[s])))]
    excluded = len(common) - len(pairs)
    if not pairs:
        return {"metric": metric, "diff": float("nan"), "n_pairs": 0,
                "n_excluded_seeds": excluded, "ci_low": float("nan"),
                "ci_high": float("nan"), "p_perm": float("nan")}
    d = np.array([x - y for x, y in pairs])
    rng = np.random.default_rng(seed)
    boots = rng.choice(d, size=(n_boot, len(d)), replace=True).mean(axis=1)
    obs = abs(d.mean())
    signs = rng.choice([-1.0, 1.0], size=(n_perm, len(d)))
    perm = np.abs((signs * d).mean(axis=1))
    p = float((np.sum(perm >= obs - 1e-12) + 1) / (n_perm + 1))
    return {"metric": metric, "arm_a": arm_a, "arm_b": arm_b,
            "diff": float(d.mean()), "n_pairs": int(len(d)), "n_excluded_seeds": int(excluded),
            "ci_low": float(np.percentile(boots, 2.5)), "ci_high": float(np.percentile(boots, 97.5)),
            "p_perm": p, "n_boot": int(n_boot), "n_perm": int(n_perm), "seed": int(seed)}


def holm(pvals: dict) -> dict:
    """Holm step-down adjusted p-values for a family {name: p}."""
    items = sorted(((p, k) for k, p in pvals.items() if p == p), key=lambda x: x[0])
    m = len(items)
    adj, running = {}, 0.0
    for i, (p, k) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        adj[k] = running
    for k, p in pvals.items():
        adj.setdefault(k, float("nan"))
    return adj
