"""Simulated power for the pre-registration v3 design (SS8). Free.

    .venv/bin/python scripts/power_sim_v3.py

Design simulated: T templates x I test instances, one risky task per
instance, R rollouts; two arms on the same tasks. Each template has its
own base harm probability (logit-normal around the planning value), each
task its own deviation, and the treatment multiplies the odds of harm.
Rollouts are Bernoulli draws. The test is the pre-registered one: a
sign-flip permutation on template sums of the paired task differences.

Planning inputs are arguments. Defaults come from the dev pilot
(bare harm about 0.15; D-013) and are assumed for the rest.
"""
import argparse
import json

import numpy as np


def _logit(p):
    return np.log(p / (1 - p))


def _expit(x):
    return 1 / (1 + np.exp(-x))


def power(templates, instances, rollouts, p0, p1, sd_template=1.0, sd_task=0.5,
          sims=600, n_perm=400, seed=1):
    rng = np.random.default_rng(seed)
    shift = _logit(p1) - _logit(p0)
    hits = 0
    for _ in range(sims):
        t_eff = rng.normal(0, sd_template, size=(templates, 1))
        k_eff = rng.normal(0, sd_task, size=(templates, instances))
        base = _logit(p0) + t_eff + k_eff
        ya = rng.binomial(rollouts, _expit(base + shift)) / rollouts
        yb = rng.binomial(rollouts, _expit(base)) / rollouts
        sums = (ya - yb).sum(axis=1)
        obs = abs(sums.sum())
        signs = rng.choice([-1.0, 1.0], size=(n_perm, templates))
        perm = np.abs((signs * sums).sum(axis=1))
        p = (np.sum(perm >= obs - 1e-12) + 1) / (n_perm + 1)
        hits += p < 0.05
    return hits / sims


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=600)
    a = ap.parse_args()
    out = []
    for p0, p1 in ((0.15, 0.05), (0.15, 0.02), (0.30, 0.15), (0.30, 0.10), (0.50, 0.30)):
        for templates in (6, 12, 17, 23, 30):
            for sd_t in (0.5, 1.0, 1.5):
                out.append({"p0": p0, "p1": p1, "templates": templates, "instances": 4, "rollouts": 3,
                            "sd_template": sd_t,
                            "power": round(power(templates, 4, 3, p0, p1, sd_template=sd_t, sims=a.sims), 3)})
    lvl = round(power(12, 4, 3, 0.15, 0.15, sims=a.sims), 3)
    print(json.dumps({"type_I_check_12_templates": lvl, "grid": out}, indent=1))
