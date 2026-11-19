"""Simulated power for the pre-registration v3 tests (SS8). Free.

    .venv/bin/python scripts/power_sim_v3.py [--sims 600]

Design simulated: T templates x 4 test instances, one task of the relevant
twin type per instance, 3 rollouts; two arms on the same tasks. Each
template has its own base rate (logit-normal), each task its own
deviation; rollouts are Bernoulli. Rows are labelled by MARGINAL rates:
the logit intercepts are solved so that the simulated mean rate of each
arm equals the label (the earlier version labelled medians; review M5).
The test is the registered one: sign-flip permutation on template sums of
paired task differences. Power is given at alpha 0.05 and at 0.0125, the
first Holm step for a family of four.

Variance components (template SD 1.0, task SD 0.5 on the logit scale) are
ASSUMED until the calibration split is run. C3 (informedness) is not
simulated here.
"""
import argparse
import json

import numpy as np


def _expit(x):
    return 1 / (1 + np.exp(-x))


def intercept_for(rate, sd_t, sd_k, rng):
    """Logit intercept whose marginal mean rate is `rate`."""
    z = rng.normal(0, np.sqrt(sd_t ** 2 + sd_k ** 2), size=200000)
    lo, hi = -15.0, 15.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if _expit(mid + z).mean() < rate:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def power(templates, p_b, p_a, sd_t=1.0, sd_k=0.5, instances=4, rollouts=3, sims=600, n_perm=800, seed=1):
    """Arm B at marginal rate p_b, arm A at p_a, same tasks. Returns
    (power at 0.05, power at 0.0125, simulated mean rates)."""
    rng = np.random.default_rng(seed)
    ib, ia = intercept_for(p_b, sd_t, sd_k, rng), intercept_for(p_a, sd_t, sd_k, rng)
    hits5 = hits1 = 0
    mb = ma = 0.0
    for _ in range(sims):
        eff = rng.normal(0, sd_t, size=(templates, 1)) + rng.normal(0, sd_k, size=(templates, instances))
        ya = rng.binomial(rollouts, _expit(ia + eff)) / rollouts
        yb = rng.binomial(rollouts, _expit(ib + eff)) / rollouts
        ma += ya.mean()
        mb += yb.mean()
        sums = (ya - yb).sum(axis=1)
        obs = abs(sums.sum())
        signs = rng.choice([-1.0, 1.0], size=(n_perm, templates))
        p = (np.sum(np.abs((signs * sums).sum(axis=1)) >= obs - 1e-12) + 1) / (n_perm + 1)
        hits5 += p < 0.05
        hits1 += p < 0.0125
    return round(hits5 / sims, 3), round(hits1 / sims, 3), round(mb / sims, 3), round(ma / sims, 3)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=600)
    a = ap.parse_args()
    grid = [
        # test, templates in the stratum, rate arm B -> rate arm A
        ("C1 gate vs prompt rule, harm, decidable", 18, 0.20, 0.05),
        ("C1 gate vs prompt rule, harm, decidable", 18, 0.20, 0.10),
        ("C2 monitor vs bare, harm, undecidable", 17, 0.30, 0.15),
        ("C2 monitor vs bare, harm, undecidable", 17, 0.15, 0.05),
        ("C2 monitor vs bare, harm, undecidable", 17, 0.15, 0.075),
        ("C2 monitor vs bare, harm, undecidable", 17, 0.08, 0.04),
        ("C4 prompt rule vs bare, false hold, all", 35, 0.10, 0.20),
        ("C4 prompt rule vs bare, false hold, all", 35, 0.10, 0.15),
    ]
    out = []
    for name, t, pb, pa in grid:
        p5, p1, mb, ma = power(t, pb, pa, sims=a.sims)
        out.append({"test": name, "templates": t, "rate_b": pb, "rate_a": pa, "simulated_mean_b": mb,
                    "simulated_mean_a": ma, "power_alpha_0.05": p5, "power_alpha_0.0125": p1})
    null = [power(t, 0.15, 0.15, sims=a.sims, seed=7)[:2] for t in (17, 18, 35)]
    print(json.dumps({"sims": a.sims, "sd_template": 1.0, "sd_task": 0.5,
                      "type_I_at_0.05_and_0.0125_for_17_18_35_templates": null, "grid": out}, indent=1))
