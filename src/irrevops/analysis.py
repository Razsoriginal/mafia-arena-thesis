"""IrrevOps v3 analysis (pre-registration v3 SS5-SS7). Analysis only.

    .venv/bin/python -m src.irrevops.analysis --campaign explore-ops-01
    .venv/bin/python -m src.irrevops.analysis --campaign ops-A-01 --unblind   # after the lock tag

Unit of analysis: the task. Rollouts are averaged within (task, arm) and
are never treated as independent. Intervals: two-level bootstrap, templates
then instances within template. Tests: sign-flip permutation on template
means of the paired task differences.

Blinding: for a confirmatory campaign (prefix ops-) outcome tables are
written only with --unblind and only if the git tag `locked-<campaign>`
exists. Without that, only nuisance quantities pooled over arms appear.
"""
import argparse
import os
import subprocess

import numpy as np
import pandas as pd

SEED = 20261119
NONCONFIRMATORY = ("explore-", "pilot-", "smoke-")
METRICS = ("harm", "false_hold", "escalated", "residual_harm")


def task_level(ep: pd.DataFrame) -> pd.DataFrame:
    """One row per (task, arm): the mean over rollouts of each outcome."""
    keys = ["task_id", "template_id", "pair_id", "twin", "decidable", "arm"]
    g = ep.groupby(keys, dropna=False)
    out = g[list(METRICS)].mean().reset_index()
    out["n_rollouts"] = g.size().values
    return out


def _population(metric: str, tl: pd.DataFrame) -> pd.DataFrame:
    """Tasks a metric is defined on: harm on risky twins, false hold on
    act twins, escalation on all."""
    if metric in ("harm", "residual_harm"):
        return tl[tl["twin"] != "act"]
    if metric == "false_hold":
        return tl[tl["twin"] == "act"]
    return tl


def _two_level_boot(values_by_template: dict, n_boot: int, rng) -> np.ndarray:
    """Bootstrap the mean over tasks: resample templates, then tasks within
    each drawn template (a fresh inner resample for every draw of a
    template). `values_by_template`: template -> 1-d array. Vectorised
    over replicates: template multiplicities are multinomial, and each
    multiplicity level gets its own inner resample."""
    arrs = [np.asarray(v, dtype=float) for v in values_by_template.values()]
    k = len(arrs)
    counts = rng.multinomial(k, np.full(k, 1.0 / k), size=n_boot)      # n_boot x k
    tot = np.zeros(n_boot)
    cnt = np.zeros(n_boot)
    for j, a in enumerate(arrs):
        n = len(a)
        cj = counts[:, j]
        for m in range(1, int(cj.max()) + 1):
            rows = np.nonzero(cj >= m)[0]
            if len(rows) == 0:
                break
            draw = a[rng.integers(0, n, size=(len(rows), n))]
            tot[rows] += draw.sum(axis=1)
            cnt[rows] += n
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(cnt > 0, tot / cnt, np.nan)


def arm_rate(tl: pd.DataFrame, arm: str, metric: str, stratum=None, n_boot: int = 10000, seed: int = SEED) -> dict:
    d = _population(metric, tl[tl["arm"] == arm])
    if stratum is not None:
        d = d[d["decidable"] == stratum]
    if d.empty:
        return {"arm": arm, "metric": metric, "rate": float("nan"), "n_tasks": 0, "n_templates": 0,
                "ci_low": float("nan"), "ci_high": float("nan")}
    by_t = {t: g[metric].values for t, g in d.groupby("template_id")}
    boots = _two_level_boot(by_t, n_boot, np.random.default_rng(seed))
    return {"arm": arm, "metric": metric, "rate": float(d[metric].mean()), "n_tasks": int(len(d)),
            "n_templates": len(by_t), "ci_low": float(np.nanpercentile(boots, 2.5)),
            "ci_high": float(np.nanpercentile(boots, 97.5))}


def paired_contrast(tl: pd.DataFrame, arm_a: str, arm_b: str, metric: str, stratum=None,
                    n_boot: int = 10000, n_perm: int = 10000, seed: int = SEED) -> dict:
    """arm_a - arm_b on `metric`, paired by task. Tasks missing in either
    arm are excluded and counted."""
    pop = _population(metric, tl)
    if stratum is not None:
        pop = pop[pop["decidable"] == stratum]
    a = pop[pop["arm"] == arm_a].set_index("task_id")
    b = pop[pop["arm"] == arm_b].set_index("task_id")
    common = sorted(set(a.index) & set(b.index))
    res = {"metric": metric, "arm_a": arm_a, "arm_b": arm_b, "stratum": stratum,
           "n_tasks": len(common), "n_unpaired": len(set(a.index) ^ set(b.index))}
    if not common:
        res.update({"diff": float("nan"), "ci_low": float("nan"), "ci_high": float("nan"),
                    "p_perm": float("nan"), "n_templates": 0})
        return res
    d = pd.DataFrame({"template_id": a.loc[common, "template_id"].values,
                      "diff": a.loc[common, metric].values - b.loc[common, metric].values})
    by_t = {t: g["diff"].values for t, g in d.groupby("template_id")}
    rng = np.random.default_rng(seed)
    boots = _two_level_boot(by_t, n_boot, rng)
    # Permutation at the template level: flip the sign of whole templates.
    sums = np.array([v.sum() for v in by_t.values()])
    n = len(common)
    obs = abs(sums.sum() / n)
    signs = rng.choice([-1.0, 1.0], size=(n_perm, len(sums)))
    perm = np.abs((signs * sums).sum(axis=1) / n)
    res.update({"diff": float(d["diff"].mean()), "n_templates": len(by_t),
                "ci_low": float(np.nanpercentile(boots, 2.5)), "ci_high": float(np.nanpercentile(boots, 97.5)),
                "p_perm": float((np.sum(perm >= obs - 1e-12) + 1) / (n_perm + 1))})
    return res


def informedness_contrast(tl, arm_a, arm_b, stratum=None, n_boot=10000, n_perm=10000, seed=SEED) -> dict:
    """J = (1 - harm rate) - false-hold rate. Per template: J_t = catch_t -
    hold_t from that template's risky and act tasks; the contrast is the
    mean over templates of J_t(a) - J_t(b). Bootstrap and permutation over
    templates (a template's twins share their tickets)."""
    def per_template(arm):
        d = tl[tl["arm"] == arm]
        if stratum is not None:
            d = d[d["decidable"] == stratum]
        risky = d[d["twin"] != "act"].groupby("template_id")["harm"].mean()
        act = d[d["twin"] == "act"].groupby("template_id")["false_hold"].mean()
        return ((1 - risky) - act).dropna()
    ja, jb = per_template(arm_a), per_template(arm_b)
    common = sorted(set(ja.index) & set(jb.index))
    if not common:
        return {"metric": "informedness", "arm_a": arm_a, "arm_b": arm_b, "diff": float("nan"),
                "n_templates": 0, "ci_low": float("nan"), "ci_high": float("nan"), "p_perm": float("nan")}
    d = (ja[common] - jb[common]).values
    rng = np.random.default_rng(seed)
    boots = rng.choice(d, size=(n_boot, len(d))).mean(axis=1)
    signs = rng.choice([-1.0, 1.0], size=(n_perm, len(d)))
    perm = np.abs((signs * d).mean(axis=1))
    return {"metric": "informedness", "arm_a": arm_a, "arm_b": arm_b, "stratum": stratum,
            "diff": float(d.mean()), "n_templates": len(d),
            "ci_low": float(np.percentile(boots, 2.5)), "ci_high": float(np.percentile(boots, 97.5)),
            "p_perm": float((np.sum(perm >= abs(d.mean()) - 1e-12) + 1) / (n_perm + 1))}


def holm(pvals: dict) -> dict:
    items = sorted(((p, k) for k, p in pvals.items() if p == p), key=lambda x: x[0])
    adj, running, m = {}, 0.0, len(items)
    for i, (p, k) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        adj[k] = running
    for k in pvals:
        adj.setdefault(k, float("nan"))
    return adj


def utility_table(tl: pd.DataFrame, lambdas=(1, 3, 10, 30, 100, 300, 1000), costs=(0.1, 0.3, 1.0)) -> pd.DataFrame:
    """U = -lambda*harm - false_hold - c*escalation, per arm, from rates."""
    rows = []
    for arm in sorted(tl["arm"].unique()):
        d = tl[tl["arm"] == arm]
        harm = _population("harm", d)["harm"].mean()
        hold = _population("false_hold", d)["false_hold"].mean()
        esc = d["escalated"].mean()
        for lam in lambdas:
            for c in costs:
                rows.append({"arm": arm, "lambda": lam, "c_escalation": c,
                             "utility": float(-lam * harm - hold - c * esc)})
    return pd.DataFrame(rows)


def summary_table(tl: pd.DataFrame, stratum=None, n_boot: int = 10000) -> pd.DataFrame:
    rows = []
    for arm in sorted(tl["arm"].unique()):
        row = {"arm": arm}
        for m in METRICS:
            r = arm_rate(tl, arm, m, stratum, n_boot=n_boot)
            row[m] = r["rate"]
            row[f"{m}_ci"] = f"[{r['ci_low']:.3f}, {r['ci_high']:.3f}]"
            row[f"{m}_n"] = r["n_tasks"]
        row["informedness"] = (1 - row["harm"]) - row["false_hold"]
        rows.append(row)
    return pd.DataFrame(rows)


def nuisance_table(ep: pd.DataFrame) -> pd.DataFrame:
    """Pooled over arms on purpose: no outcome and no per-arm quantity."""
    return pd.DataFrame([{"episodes": len(ep), "tasks": ep["task_id"].nunique(),
                          "templates": ep["template_id"].nunique(),
                          "cost_total_inr": float(ep["cost_inr"].sum()),
                          "cost_mean_inr": float(ep["cost_inr"].mean()),
                          "steps_mean": float(ep["n_steps"].mean()),
                          "agent_parse_fails": int(ep["agent_parse_fails"].sum()),
                          "step_cap_share": float((ep["ended"] == "step_cap").mean())}])


def _tag_exists(tag: str) -> bool:
    return subprocess.run(["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
                          stdout=subprocess.DEVNULL).returncode == 0


def may_unblind(campaign: str, unblind: bool) -> bool:
    if campaign.startswith(NONCONFIRMATORY):
        return True
    return bool(unblind and _tag_exists(f"locked-{campaign}"))


def _md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(f"{v:.3f}" if isinstance(v, float) else str(v) for v in r) + " |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", required=True)
    ap.add_argument("--unblind", action="store_true")
    ap.add_argument("--n-boot", type=int, default=10000)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    marker = os.path.join("logs", "runs", a.campaign, "DO_NOT_ANALYSE")
    if os.path.exists(marker):
        raise SystemExit(f"refused: {a.campaign} is marked DO_NOT_ANALYSE: {open(marker).read().strip()}")
    ep = pd.read_parquet(os.path.join("logs", "runs", a.campaign, "episodes.parquet"))
    out_dir = a.out or os.path.join("docs", "thesis", "assets", a.campaign)
    os.makedirs(out_dir, exist_ok=True)
    label = "EXPLORATORY (non-confirmatory campaign)" if a.campaign.startswith(NONCONFIRMATORY) else "CONFIRMATORY"
    lines = [f"# {a.campaign}: {label}", "",
             f"Source: `logs/runs/{a.campaign}/episodes.parquet`; git sha(s) {sorted(ep['git_sha'].unique())}; "
             f"task set {sorted(ep['task_set_sha256'].str[:12].unique())}; repetitions {sorted(ep['rep'].unique())}.",
             "", "## Nuisance (pooled over arms)", "", _md(nuisance_table(ep)), ""]
    if not may_unblind(a.campaign, a.unblind):
        lines += ["Outcomes are blinded: this is a confirmatory campaign and it is not unblinded "
                  f"(needs --unblind and the tag `locked-{a.campaign}`)."]
    else:
        tl = task_level(ep)
        cell = tl.groupby("arm")["n_rollouts"].agg(["min", "max"]).reset_index()
        lines += ["## Rollouts per task-arm cell", "", _md(cell), ""]
        for name, st in (("all tasks", None), ("decidable stratum", True), ("undecidable stratum", False)):
            lines += [f"## Rates by arm, {name}", "",
                      "Unit: task (mean over rollouts). 95% CI: two-level bootstrap (templates, then tasks). "
                      "harm and residual_harm over risky twins; false_hold over act twins; escalated over all.", "",
                      _md(summary_table(tl, st, n_boot=a.n_boot)), ""]
        if "L0_bare" in set(tl["arm"]):
            rows = []
            for arm in sorted(set(tl["arm"]) - {"L0_bare"}):
                for m in ("harm", "false_hold", "escalated"):
                    r = paired_contrast(tl, arm, "L0_bare", m, n_boot=a.n_boot, n_perm=a.n_boot)
                    rows.append({"contrast": f"{arm} - L0", "metric": m, "diff": r["diff"],
                                 "ci": f"[{r['ci_low']:.3f}, {r['ci_high']:.3f}]", "p_perm": r["p_perm"],
                                 "tasks": r["n_tasks"], "templates": r["n_templates"]})
            lines += ["## Paired contrasts against the bare agent (all tasks)", "", _md(pd.DataFrame(rows)), ""]
        u = utility_table(tl).dropna(subset=["utility"])   # an arm without both twin types has no utility
        best = u.loc[u.groupby(["lambda", "c_escalation"])["utility"].idxmax()] if len(u) else u
        lines += ["## Highest-utility arm by harm-to-delay ratio (descriptive)", "", _md(best), ""]
    path = os.path.join(out_dir, "tables.md")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
