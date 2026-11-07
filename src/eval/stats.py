"""Paired and clustered statistics for the team design (Pre-reg SS12)."""
import math

import numpy as np
import pandas as pd

Z95 = 1.959964


def wilson_interval(successes: int, n: int, z: float = Z95):
    if n <= 0:
        return (float("nan"), float("nan"))
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def paired_bootstrap_diff(a, b, n_boot: int = 10000, seed: int = 20261106):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if len(a) != len(b) or len(a) == 0:
        raise ValueError("paired arrays must be equal and non-empty")
    diffs = a - b
    rng = np.random.default_rng(seed)
    n = len(diffs)
    boots = rng.choice(diffs, size=(n_boot, n), replace=True).mean(axis=1)
    return {"diff": float(diffs.mean()), "n_pairs": int(n),
            "ci_low": float(np.percentile(boots, 2.5)),
            "ci_high": float(np.percentile(boots, 97.5)),
            "n_boot": int(n_boot), "seed": int(seed)}


def mcnemar_exact(a, b):
    a = np.asarray(a, dtype=int)
    b = np.asarray(b, dtype=int)
    bb = int(np.sum((a == 1) & (b == 0)))
    cc = int(np.sum((a == 0) & (b == 1)))
    n = bb + cc
    if n == 0:
        return {"b": 0, "c": 0, "p_value": 1.0}
    k = min(bb, cc)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return {"b": bb, "c": cc, "p_value": float(min(1.0, 2 * tail))}


def cluster_bootstrap_mean(df: pd.DataFrame, value_col: str, cluster_col: str,
                           n_boot: int = 10000, seed: int = 20261106):
    clusters = [g[value_col].astype(float).values for _, g in df.groupby(cluster_col)]
    if not clusters:
        raise ValueError("no clusters")
    all_vals = df[value_col].astype(float).values
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(clusters), size=len(clusters))
        sample = np.concatenate([clusters[i] for i in idx]) if len(clusters) else np.array([])
        boots.append(float(np.mean(sample)) if len(sample) else float("nan"))
    return {"mean": float(np.mean(all_vals)), "n_clusters": int(len(clusters)),
            "ci_low": float(np.nanpercentile(boots, 2.5)),
            "ci_high": float(np.nanpercentile(boots, 97.5)),
            "n_boot": int(n_boot), "seed": int(seed)}


def auc_score(trust, labels):
    """Mann-Whitney AUC, ties 0.5. trust=P(innocent), labels innocent=1."""
    trust = np.asarray(trust, dtype=float)
    labels = np.asarray(labels, dtype=int)
    pos, neg = trust[labels == 1], trust[labels == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    wins = 0.0
    for p in pos:
        wins += float(np.sum(p > neg)) + 0.5 * float(np.sum(p == neg))
    return float(wins / (len(pos) * len(neg)))
