"""Regenerate every thesis table and figure from parquet (Phase 4, G6).

    .venv/bin/python scripts/make_all.py --campaign mvp-team-01            # nuisance only (blinded)
    .venv/bin/python scripts/make_all.py --campaign mvp-team-01 --unblind  # after tag primary-locked
    .venv/bin/python scripts/make_all.py --bridge bridge-main-01          # IrrevOps tables

Blinding (Pre-reg SS9/SS12, P0-K1): outcome-by-arm tables and figures are
written only with --unblind, which also requires the git tag
`primary-locked` and no pending trios for the campaign. Nuisance tables
(cost, JSON failures, length, probe missingness) are always written.
Outputs go to docs/thesis/assets/<campaign>/ (or <bridge>/).
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

from src.eval import figures  # noqa: E402
from src.eval.action_boundary import confusion_matrix, holm, paired_contrast  # noqa: E402
from src.eval.stats import paired_bootstrap_diff, wilson_interval  # noqa: E402

ARMS = ["dmn_village", "cot_village", "cotx3_village", "random_village", "majority_village"]


def _tag_exists(tag):
    return subprocess.run(["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
                          stdout=subprocess.DEVNULL).returncode == 0


def _load(path, campaign):
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_parquet(path)
    if "campaign" in df.columns:
        df = df[df["campaign"].astype(str) == campaign]
    return df


def _md_table(df):
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(f"{v:.4g}" if isinstance(v, float) else str(v) for v in r) + " |")
    return "\n".join(out)


def nuisance(g, v, t, out):
    """Pooled over arms (E7-K5). Game length, failure counts and cost by
    arm are post-treatment quantities; pre-reg v2 SS9 allows pooled values
    only before the lock."""
    cost = g["billed_cost_inr"].where(g["billed_cost_inr"] > 0, g.get("est_cost_inr"))
    pt = t[t.get("trust_source") == "probe"] if len(t) and "trust_source" in t.columns else pd.DataFrame()
    df = pd.DataFrame([{"games": len(g), "seeds": int(g["requested_seed"].nunique()),
                        "cost_total_inr": float(cost.sum()), "cost_mean_inr": float(cost.mean()),
                        "json_failures_per_game": float(g["json_failures"].mean()),
                        "mean_days": float(g["days"].mean()),
                        "probe_missing_rate": float(pt["parse_fail"].astype(bool).mean()) if len(pt) else float("nan")}])
    with open(os.path.join(out, "nuisance.md"), "w") as f:
        f.write("# Nuisance quantities (blind-safe)\n\nPooled over arms; cost is billed Rs. (estimate fallback). "
                "No outcome quantity and no per-arm quantity appears here.\n\n" + _md_table(df) + "\n")
    return df


def outcomes(g, v, t, out, n_boot):
    lines = ["# Outcomes (unblinded after primary-locked)\n"]
    # primary and key secondary: village win, paired by seed
    win = g.assign(win=(g["winner"] == "village").astype(int)).pivot_table(
        index="requested_seed", columns="arm", values="win")
    forest_rows = []
    for b, label in (("cot_village", "PRIMARY win: DMN - CoT"), ("cotx3_village", "KEY SEC win: DMN - CoT-x3")):
        if {"dmn_village", b} <= set(win.columns):
            p = win[["dmn_village", b]].dropna()
            r = paired_bootstrap_diff(p["dmn_village"], p[b], n_boot=n_boot)
            lines.append(f"- {label}: {r['diff']:+.3f} (95% CI [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}], "
                         f"n = {r['n_pairs']} seed-trios)")
            forest_rows.append({"label": label, "diff": r["diff"], "lo": r["ci_low"], "hi": r["ci_high"]})
    lines.append("\n## Village win rate by arm (Wilson 95%)\n")
    for arm in ARMS:
        gg = g[g["arm"] == arm]
        if len(gg):
            k = int((gg["winner"] == "village").sum())
            lo, hi = wilson_interval(k, len(gg))
            lines.append(f"- {arm}: {k}/{len(gg)} = {k/len(gg):.3f} [{lo:.3f}, {hi:.3f}]; "
                         f"draws {int((gg['winner'] == 'draw').sum())}")
    lines.append("\n## Action-boundary family (paired by seed; Holm over S1-S3 vs CoT)\n")
    fam = {}
    for metric, label in (("wrongful_lynches", "S1 wrongful lynches/game"),
                          ("needless_hold_rate", "S2 needless-hold rate"),
                          ("delay_quality", "S3 delay quality")):
        for b in ("cot_village", "cotx3_village"):
            r = paired_contrast(v, metric, "dmn_village", b, n_boot=n_boot, n_perm=n_boot)
            if b == "cot_village":
                fam[label] = r["p_perm"]
            lines.append(f"- {label}, DMN - {b}: {r['diff']:+.3f} [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}] "
                         f"p_perm={r['p_perm']:.4f} n_pairs={r['n_pairs']} excluded={r['n_excluded_seeds']}")
            forest_rows.append({"label": f"{label.split(' ')[0]} vs {b.split('_')[0]}", "diff": r["diff"],
                                "lo": r["ci_low"], "hi": r["ci_high"]})
    lines.append(f"- Holm-adjusted p: {json.dumps({k: round(x, 4) for k, x in holm(fam).items()})}")
    figures.forest(forest_rows, "Paired differences, DMN village minus comparator (95% CI)",
                   "difference (win prob. / lynches per game / rate)", os.path.join(out, "fig_paired_differences.svg"))
    cm = confusion_matrix(v)
    lines.append("\n## Per-vote confusion matrix (village voters; descriptive)\n\n" + _md_table(cm))
    figures.stacked([{"label": r["arm"], **{c: r[c] for c in ("act_correct", "act_harmful", "act_invalid",
                                                              "abstain_reasoned", "abstain_failure")}}
                     for _, r in cm.iterrows()],
                    ["act_correct", "act_harmful", "act_invalid", "abstain_reasoned", "abstain_failure"],
                    "Village vote outcomes by arm", os.path.join(out, "fig_confusion.svg"))
    # probe reliability by arm (trust = P(innocent); outcome = innocent)
    if len(t):
        pr = t[(t["trust_source"] == "probe") & ~t["parse_fail"].astype(bool) &
               (t["agent"].astype(str) != t["target"].astype(str))]
        figures.reliability({arm: list(zip(gg["trust"].astype(float), (~gg["target_is_mafia"].astype(bool)).astype(int)))
                             for arm, gg in pr.groupby("arm")},
                            "Probe reliability by arm", os.path.join(out, "fig_reliability_probe.svg"))
        # DMN risk-coverage from decision rows (verified targets)
        dec = t[(t["trust_source"] == "decision") & t["verified"].astype(bool) & (t["arm"] == "dmn_village")]
        if len(dec):
            sd = (dec.assign(conf=1 - dec["trust"].astype(float))
                  .sort_values("conf").groupby(["game_id", "day", "agent"]).tail(1))
            pts, base = [], float(sd["target_is_mafia"].astype(bool).map(lambda x: not x).mean())
            for tau in np.linspace(0, 1, 21):
                cov = sd[sd["conf"] >= tau]
                if len(cov):
                    pts.append((len(cov) / len(sd), float((~cov["target_is_mafia"].astype(bool)).mean())))
            figures.curve({"DMN gate (top verified suspect)": pts,
                           "random abstention (matched coverage)": [(0, base), (1, base)]},
                          "Risk-coverage of the delay gate", "coverage (share of seat-days acting)",
                          "risk (top suspect innocent)", os.path.join(out, "fig_risk_coverage.svg"))
    with open(os.path.join(out, "outcomes.md"), "w") as f:
        f.write("\n".join(lines) + "\n")


def bridge(campaign, out, n_boot=10000, seed=20261106):
    p = os.path.join("logs", "runs", campaign, "episodes.parquet")
    e = pd.read_parquet(p)
    rows = []
    for arm, g in e.groupby("arm"):
        ab, ac = g[g.twin == "abstain"], g[g.twin == "act"]
        pa = g.pivot_table(index=["pair_id", "rep"], columns="twin", values="outcome", aggfunc="first")
        pacc = ((pa.get("act") == "act_correct") & (pa.get("abstain") == "abstain_justified")).mean()
        rows.append({"arm": arm, "episodes": len(g), "harmful_rate": float((ab.outcome == "act_harmful").mean()),
                     "false_hold_rate": float((ac.outcome == "abstain_needless").mean()),
                     "paired_accuracy": float(pacc),
                     "verified_before_irreversible": float(g["verified_before_first_irreversible"].dropna().astype(bool).mean())
                     if g["verified_before_first_irreversible"].notna().any() else float("nan"),
                     "claimed_verification_without_call": float(g["claimed_verification_without_call"].astype(bool).mean()),
                     "cost_inr": float(g["cost_inr"].sum())})
    tab = pd.DataFrame(rows)
    rng = np.random.default_rng(seed)
    lines = ["# IrrevOps bridge (estimation only; simulated tools)\n", _md_table(tab), "",
             "## Contrasts (cluster bootstrap over task pairs, 95%)\n"]
    forest_rows = []
    for a, b in (("B3_verify_delay", "B0_bare"), ("B2_external_gate", "B0_bare"),
                 ("B1_prompt_rule", "B0_bare"), ("B3_verify_delay", "B2_external_gate")):
        for metric, twin, bad in (("harmful", "abstain", "act_harmful"), ("false_hold", "act", "abstain_needless")):
            sub = e[e.twin == twin].assign(y=lambda d: (d.outcome == bad).astype(float))
            per = sub.pivot_table(index="pair_id", columns="arm", values="y", aggfunc="mean")
            if a not in per or b not in per:
                continue
            d = (per[a] - per[b]).dropna().values
            boots = rng.choice(d, size=(n_boot, len(d))).mean(axis=1)
            lo, hi = np.percentile(boots, [2.5, 97.5])
            lines.append(f"- {metric}: {a} - {b} = {d.mean():+.3f} [{lo:+.3f}, {hi:+.3f}] (pairs={len(d)})")
            forest_rows.append({"label": f"{metric}: {a.split('_')[0]}-{b.split('_')[0]}", "diff": float(d.mean()),
                                "lo": float(lo), "hi": float(hi)})
    lines.append("\nConstant-policy floors: always-act harmful=1, false-hold=0; always-abstain harmful=0, "
                 "false-hold=1; paired accuracy 0 for both.")
    figures.forest(forest_rows, "IrrevOps: harm and false-hold differences (95% CI)", "difference in rate",
                   os.path.join(out, "fig_bridge_contrasts.svg"))
    with open(os.path.join(out, "bridge.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    return tab


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign")
    ap.add_argument("--bridge")
    ap.add_argument("--unblind", action="store_true")
    ap.add_argument("--games", default="logs/games.parquet")
    ap.add_argument("--votes", default="logs/votes.parquet")
    ap.add_argument("--trust", default="logs/trust.parquet")
    ap.add_argument("--n-boot", type=int, default=10000)
    a = ap.parse_args()
    if a.campaign:
        out = os.path.join("docs", "thesis", "assets", a.campaign)
        os.makedirs(out, exist_ok=True)
        g, v, t = (_load(p, a.campaign) for p in (a.games, a.votes, a.trust))
        nuisance(g, v, t, out)
        if a.unblind:
            pending = [x for x in json.load(open("logs/pending_trios.json"))
                       if x.get("campaign") == a.campaign] if os.path.exists("logs/pending_trios.json") else []
            if not _tag_exists("primary-locked") and not a.campaign.startswith(("smoke-", "explore-")):
                raise SystemExit("unblind refused: tag primary-locked does not exist")
            if pending:
                raise SystemExit(f"unblind refused: {len(pending)} pending trio(s)")
            outcomes(g, v, t, out, a.n_boot)
        print(f"wrote {out}")
    if a.bridge:
        out = os.path.join("docs", "thesis", "assets", a.bridge)
        os.makedirs(out, exist_ok=True)
        print(bridge(a.bridge, out, n_boot=a.n_boot).to_string(index=False))


if __name__ == "__main__":
    main()
