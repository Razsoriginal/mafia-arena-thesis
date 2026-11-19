"""Simulated power for paired-by-seed designs (Phase E3). Free; no data use
beyond pooled non-confirmatory nuisance inputs passed as arguments.

    .venv/bin/python scripts/power_sim.py

Binary outcome (village win): pairs drawn from a Gaussian copula with
within-seed correlation rho; test = percentile paired bootstrap CI
excluding 0 (the pre-registered rule), approximated by the paired z test
(checked against the bootstrap at one grid point). Count outcome (wrongful
lynches per game): Poisson-binomial draws.
"""
import json

import numpy as np
from scipy.stats import norm


def power_binary(p0, delta, n, rho, sims=4000, seed=1):
    rng = np.random.default_rng(seed)
    cov = np.array([[1, rho], [rho, 1]])
    z = rng.multivariate_normal([0, 0], cov, size=(sims, n))
    a = (z[..., 0] < norm.ppf(p0 + delta)).astype(float)
    b = (z[..., 1] < norm.ppf(p0)).astype(float)
    d = a - b
    m, s = d.mean(1), d.std(1, ddof=1)
    return float(np.mean(np.abs(m) / (s / np.sqrt(n) + 1e-12) > 1.959964))


def power_bootstrap(p0, delta, n, rho, sims=400, n_boot=2000, seed=2):
    rng = np.random.default_rng(seed)
    cov = np.array([[1, rho], [rho, 1]])
    hit = 0
    for _ in range(sims):
        z = rng.multivariate_normal([0, 0], cov, size=n)
        d = (z[:, 0] < norm.ppf(p0 + delta)).astype(float) - (z[:, 1] < norm.ppf(p0)).astype(float)
        boots = rng.choice(d, size=(n_boot, n)).mean(1)
        lo, hi = np.percentile(boots, [2.5, 97.5])
        hit += (lo > 0) or (hi < 0)
    return hit / sims


def power_count(mu0, ratio, n, sims=4000, seed=3):
    """Wrongful lynches per game ~ Poisson(mu); treatment multiplies by ratio."""
    rng = np.random.default_rng(seed)
    d = rng.poisson(mu0 * ratio, (sims, n)) - rng.poisson(mu0, (sims, n))
    m, s = d.mean(1), d.std(1, ddof=1)
    return float(np.mean(np.abs(m) / (s / np.sqrt(n) + 1e-12) > 1.959964))


if __name__ == "__main__":
    out = {"binary": [], "count": []}
    for p0 in (0.38, 0.45):
        for rho in (0.0, 0.1, 0.3):
            for delta in (0.05, 0.10, 0.15):
                for n in (100, 184, 400):
                    out["binary"].append({"p0": p0, "rho": rho, "delta": delta, "n": n,
                                          "power": round(power_binary(p0, delta, n, rho), 3)})
    out["bootstrap_check"] = {"p0": 0.45, "rho": 0.1, "delta": 0.10, "n": 184,
                              "z": power_binary(0.45, 0.10, 184, 0.1),
                              "bootstrap": power_bootstrap(0.45, 0.10, 184, 0.1)}
    for mu0 in (0.4, 0.6):
        for ratio in (0.75, 0.5):
            for n in (100, 184, 400):
                out["count"].append({"mu0": mu0, "ratio": ratio, "n": n,
                                     "power": round(power_count(mu0, ratio, n), 3)})
    print(json.dumps(out, indent=1))
