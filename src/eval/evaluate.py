"""Quick evaluate: python -m src.eval.evaluate --input logs/games.parquet

Reads logs/votes.parquet + logs/trust.parquet when present and reports the
five thesis metrics with n. Also reports JSON-failure and forced-delay rates
so a fallback is never mistaken for a reasoning result.

Team-design files are filtered to design == team (and to --campaign when
given), grouped by arm, with the pre-registered paired/clustered CIs from
stats.py. Probe and decision-linked calibration are always reported in
separate tables, decision tables grouped by arm. Outcome-by-arm output
requires --unblind and is refused while the campaign has pending trios.
Legacy focal files keep the old focal report.
"""
import argparse
import json
import os

import pandas as pd

from .metrics import (brier, cascade_resistance, delay_quality, ece,
                      say_do_gap, team_cascade_resistance, team_delay_quality)
from .stats import (auc_score, cluster_bootstrap_mean, mcnemar_exact,
                    paired_bootstrap_diff, wilson_interval)


def _pairs(tdf, drop_self=True):
    """(pairs, n_self_dropped, n_missing_dropped). Missing = parse_fail/NaN."""
    df = tdf
    n_self = 0
    if drop_self and "agent" in df.columns and "target" in df.columns:
        mask = df["agent"].astype(str) != df["target"].astype(str)
        n_self = int((~mask).sum())
        df = df[mask]
    n_missing = 0
    if "parse_fail" in df.columns:
        pmask = ~df["parse_fail"].fillna(False).astype(bool)
        n_missing += int((~pmask).sum())
        df = df[pmask]
    pairs = []
    for t, m in zip(df["trust"], df["target_is_mafia"]):
        try:
            tv = float(t)
        except Exception:
            n_missing += 1
            continue
        if tv != tv:  # NaN
            n_missing += 1
            continue
        pairs.append((tv, 0 if bool(m) else 1))  # trust = P(innocent)
    return pairs, n_self, n_missing


def _report_trust_table(label, tdf):
    if tdf is None or len(tdf) == 0:
        print(f"{label}: no rows")
        return
    pairs, n_self, n_missing = _pairs(tdf)
    print(f"{label}: self-rows dropped={n_self}, missing/parse-fail dropped={n_missing}")
    if not pairs:
        print(f"{label}: no rows after self/missing exclusion")
        return
    auc = auc_score([p[0] for p in pairs], [p[1] for p in pairs])
    print(f"{label}: ECE {ece(pairs):.3f} Brier {brier(pairs):.3f} "
          f"AUC {auc:.3f} (n={len(pairs)}, self-rows excluded)")


def _filter_team(df, campaign=None):
    """Team rows only (F27), optionally one campaign."""
    out = df
    if "design" in out.columns:
        out = out[out["design"].astype(str) == "team"]
    if campaign and "campaign" in out.columns:
        out = out[out["campaign"].astype(str) == str(campaign)]
    return out


def _pending_for_campaign(pending_path, campaign):
    if not pending_path or not os.path.exists(pending_path):
        return []
    try:
        with open(pending_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    if not campaign:
        return data
    return [it for it in data if str(it.get("campaign", "")) == str(campaign)]


def _paired_outcomes(df, arm_a="dmn_village", arm_b="cot_village"):
    """Aligned village-win (0/1) arrays by requested_seed, or None."""
    if "requested_seed" not in df.columns or "arm" not in df.columns:
        return None
    a = df[df["arm"].astype(str) == arm_a].set_index("requested_seed")["winner"]
    b = df[df["arm"].astype(str) == arm_b].set_index("requested_seed")["winner"]
    common = sorted(set(a.index) & set(b.index))
    if not common:
        return None
    av = [1 if a.loc[s] == "village" else 0 for s in common]
    bv = [1 if b.loc[s] == "village" else 0 for s in common]
    return av, bv, common


def _cascade_cluster_rows(vdf):
    wrong = vdf[~vdf["majority_correct"].astype(bool)]
    village = wrong[wrong["is_village"].astype(bool)]
    village = village[village["vote"].astype(str) != "no-lynch"]
    if village.empty:
        return village
    out = village[["game_id"]].copy()
    out["value"] = (village["vote"].astype(str) != village["majority_vote"].astype(str)).astype(float)
    return out


def _delay_cluster_rows(vdf):
    df = vdf
    if "delay_cause" in df.columns:
        df = df[df["delay_cause"].fillna("").astype(str) != "json_failure"]
    keys = ["run_tag", "game_id", "day"] if "run_tag" in df.columns else ["game_id", "day"]
    rows = []
    for key, grp in df.groupby(keys):
        gid = key[1] if len(key) > 1 else key[0]
        village = grp[grp["is_village"].astype(bool)] if "is_village" in grp.columns else grp
        if village.empty or not (village["vote"].astype(str) == "no-lynch").any():
            continue
        majority = str(grp["majority_vote"].iloc[0])
        if majority == "no-lynch":
            continue
        rows.append({"game_id": str(gid),
                     "value": 0.0 if bool(grp["majority_correct"].iloc[0]) else 1.0})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="logs/games.parquet")
    ap.add_argument("--votes", default="logs/votes.parquet")
    ap.add_argument("--trust", default="logs/trust.parquet")
    ap.add_argument("--campaign", default=None,
                    help="restrict team report to one campaign")
    ap.add_argument("--unblind", action="store_true",
                    help="allow outcome-by-arm output (refused while pending)")
    ap.add_argument("--pending-file", default=None,
                    help="pending trios file (default logs/pending_trios.json)")
    ap.add_argument("--n-boot", type=int, default=10000)
    args = ap.parse_args()
    df_all = pd.read_parquet(args.input)
    print(f"Games: {len(df_all)} rows")
    for col in ("provider", "model", "gate", "night_mode"):
        if col in df_all.columns:
            print(f"{col}: {df_all[col].value_counts(dropna=False).to_dict()}")
    print()
    is_team = ("design" in df_all.columns
               and df_all["design"].astype(str).eq("team").any())
    df = _filter_team(df_all, args.campaign) if is_team else df_all
    if is_team:
        print(f"Team rows after design/campaign filter: {len(df)} "
              f"(campaign={args.campaign or 'all'})")
        pending_path = args.pending_file or os.getenv(
            "MAFIA_PENDING_FILE", "logs/pending_trios.json")
        pending = _pending_for_campaign(pending_path, args.campaign)
        if not args.unblind:
            for arm, g in df.groupby("arm"):
                print(f"{arm}: games={len(g)} (outcomes blinded; pass --unblind)")
            print("Outcome-by-arm output withheld: pass --unblind after lock.")
        else:
            if pending:
                raise SystemExit(
                    f"Unblind refused: {len(pending)} trio(s) still pending "
                    f"for campaign {args.campaign or 'all'} (incomplete).")
            for arm, g in df.groupby("arm"):
                wr = (g["winner"] == "village").mean()
                k = int((g["winner"] == "village").sum())
                lo, hi = wilson_interval(k, len(g))
                print(f"{arm}: village win-rate (n={len(g)}): {wr:.3f} "
                      f"Wilson95 [{lo:.3f}, {hi:.3f}] "
                      f"draws={(g['winner'] == 'draw').sum()} mean_days={g['days'].mean():.2f}")
            paired = _paired_outcomes(df)
            if paired is not None:
                av, bv, common = paired
                boot = paired_bootstrap_diff(av, bv, n_boot=args.n_boot, seed=20261106)
                mc = mcnemar_exact(av, bv)
                print(f"PRIMARY dmn-cot paired diff: {boot['diff']:.3f} "
                      f"95% CI [{boot['ci_low']:.3f}, {boot['ci_high']:.3f}] "
                      f"(n_pairs={boot['n_pairs']}, boot={boot['n_boot']}, seed={boot['seed']})")
                print(f"McNemar exact (sensitivity): b={mc['b']} c={mc['c']} p={mc['p_value']:.4f}")
            paired3 = _paired_outcomes(df, "dmn_village", "cotx3_village")
            if paired3 is not None:
                av, bv, _c = paired3
                boot = paired_bootstrap_diff(av, bv, n_boot=args.n_boot, seed=20261106)
                print(f"KEY SECONDARY dmn-cotx3 paired diff: {boot['diff']:.3f} "
                      f"95% CI [{boot['ci_low']:.3f}, {boot['ci_high']:.3f}] "
                      f"(n_pairs={boot['n_pairs']})")
    else:
        print(df.groupby("focal")["winner"].value_counts(normalize=True).round(3))
        for focal, g in df.groupby("focal"):
            sub = g[~g["focal_role"].isin(["mafia"])]
            if len(sub):
                wr = (sub["winner"] == "village").mean()
                print(f"{focal}: village win-rate (focal non-mafia, n={len(sub)}): {wr:.2f}")
    if "json_failures" in df.columns and len(df):
        print(f"JSON failures: {int(df['json_failures'].sum())} over "
              f"{len(df)} games ({df['json_failures'].mean():.2f}/game)")

    blind = is_team and not args.unblind
    if blind:
        # P0-K1: every secondary (cascade, delay, abstention, S1/S2, say-do,
        # calibration) is an outcome by arm. Nothing below is printed for
        # team data until --unblind after lock.
        print("Secondary outcomes by arm are blinded (votes and trust tables not summarised); "
              "pass --unblind after lock.")
        return

    if os.path.exists(args.votes):
        vdf_all = pd.read_parquet(args.votes)
        vdf = vdf_all
        if is_team and "game_id" in vdf.columns and "game_id" in df.columns:
            vdf = vdf[vdf["game_id"].astype(str).isin(set(df["game_id"].astype(str)))]
            if args.campaign and "campaign" in vdf.columns:
                vdf = vdf[vdf["campaign"].astype(str) == str(args.campaign)]
        if is_team and {"lynched", "majority_vote"} <= set(vdf.columns):
            from .action_boundary import confusion_matrix, holm, paired_contrast
            fam = {}
            for metric, label in (("wrongful_lynches", "S1 wrongful_lynches"),
                                  ("needless_hold_rate", "S2 needless_hold_rate"),
                                  ("delay_quality", "S3 delay_quality")):
                for arm_b in ("cot_village", "cotx3_village"):
                    res = paired_contrast(vdf, metric, "dmn_village", arm_b,
                                          n_boot=args.n_boot, n_perm=args.n_boot)
                    if arm_b == "cot_village":
                        fam[label] = res["p_perm"]
                    print(f"{label} dmn-{arm_b.split('_')[0]}: diff {res['diff']:.3f} "
                          f"95% CI [{res['ci_low']:.3f}, {res['ci_high']:.3f}] "
                          f"p_perm {res['p_perm']:.4f} (n_pairs={res['n_pairs']}, "
                          f"excluded_seeds={res['n_excluded_seeds']})")
            print(f"Holm-adjusted p (S1-S3, dmn vs cot): {holm(fam)}")
            print("Confusion matrix (village votes):")
            print(confusion_matrix(vdf).to_string(index=False))
        if is_team and "is_village" in vdf.columns:
            for arm, g in vdf.groupby("arm"):
                line = (f"\n[{arm}] team_cascade_resistance: {team_cascade_resistance(g):.3f} "
                        f"team_delay_quality: {team_delay_quality(g):.3f} "
                        f"abstention: {(g[g['is_village'].astype(bool)]['vote'].astype(str) == 'no-lynch').mean():.3f} "
                        f"(games={g['game_id'].nunique()}, rows={len(g)})")
                print(line)
                try:
                    crow = _cascade_cluster_rows(g)
                    if len(crow):
                        cb = cluster_bootstrap_mean(crow, "value", "game_id",
                                                    n_boot=2000, seed=20261106)
                        print(f"[{arm}] cascade game-cluster 95% CI "
                              f"[{cb['ci_low']:.3f}, {cb['ci_high']:.3f}] "
                              f"(clusters={cb['n_clusters']})")
                    drow = _delay_cluster_rows(g)
                    if len(drow):
                        db = cluster_bootstrap_mean(drow, "value", "game_id",
                                                    n_boot=2000, seed=20261106)
                        print(f"[{arm}] delay game-cluster 95% CI "
                              f"[{db['ci_low']:.3f}, {db['ci_high']:.3f}] "
                              f"(clusters={db['n_clusters']})")
                except Exception as e:
                    print(f"[{arm}] cluster CI unavailable: {e}")
        else:
            print(f"\ncascade_resistance: {cascade_resistance(vdf):.3f} "
                  f"(games={vdf['game_id'].nunique()}, rows={len(vdf)})")
            print(f"delay_quality (reasoned delays only): {delay_quality(vdf):.3f}")
        if "delay_cause" in vdf.columns:
            causes = vdf[vdf["delay_cause"].notna()]["delay_cause"].value_counts().to_dict()
            print(f"delay causes: {causes}")
        committed = vdf[vdf["commitment"].fillna("").astype(str) != ""]
        print(f"say_do_gap: {say_do_gap(committed):.3f} "
              f"(commitment rows={len(committed)} of {len(vdf)}, n_lynch_votes="
              f"{len(committed[committed['vote'].astype(str) != 'no-lynch'])})")
    else:
        print(f"\nNo {args.votes} yet — run run_arena first (per-day vote rows).")

    if os.path.exists(args.trust):
        tdf_all = pd.read_parquet(args.trust)
        tdf = tdf_all
        if is_team and "game_id" in tdf.columns and "game_id" in df.columns:
            tdf = tdf[tdf["game_id"].astype(str).isin(set(df["game_id"].astype(str)))]
            if args.campaign and "campaign" in tdf.columns:
                tdf = tdf[tdf["campaign"].astype(str) == str(args.campaign)]
        if "trust_source" in tdf.columns:
            print("\n--- Probe calibration (elicited, all arms) ---")
            probe = tdf[tdf["trust_source"].astype(str) == "probe"]
            if "arm" in probe.columns and len(probe):
                for arm, g in probe.groupby("arm"):
                    _report_trust_table(f"probe[{arm}]", g)
                    if "parse_fail" in g.columns:
                        miss = int(g["parse_fail"].fillna(False).astype(bool).sum())
                        print(f"probe[{arm}] missingness: {miss}/{len(g)} "
                              f"({(miss / len(g) if len(g) else 0):.3f})")
            else:
                _report_trust_table("probe", probe)
            print("\n--- Decision-linked calibration (descriptive, by arm) ---")
            dec = tdf[tdf["trust_source"].astype(str) == "decision"]
            if "arm" in dec.columns and len(dec):
                for arm, g in dec.groupby("arm"):
                    if "verified" in g.columns:
                        _report_trust_table(f"decision[{arm}][verified-only]",
                                            g[g["verified"].astype(bool)])
                        _report_trust_table(f"decision[{arm}][prior-filler]",
                                            g[~g["verified"].astype(bool)])
                    else:
                        _report_trust_table(f"decision[{arm}]", g)
            elif "verified" in dec.columns:
                _report_trust_table("decision[verified-only]", dec[dec["verified"].astype(bool)])
                _report_trust_table("decision[prior-filler]", dec[~dec["verified"].astype(bool)])
            else:
                _report_trust_table("decision", dec)
        else:
            pairs = [(float(t), 0 if bool(m) else 1)  # trust = P(innocent)
                     for t, m in zip(tdf["trust"], tdf["target_is_mafia"])]
            print(f"ECE: {ece(pairs):.3f} Brier: {brier(pairs):.3f} (n={len(pairs)})")
    else:
        print(f"No {args.trust} yet — run run_arena first (per-day trust rows).")


if __name__ == "__main__":
    main()
