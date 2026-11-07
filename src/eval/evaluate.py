"""Quick evaluate: python -m src.eval.evaluate --input logs/games.parquet

Reads logs/votes.parquet + logs/trust.parquet when present and reports the
five thesis metrics with n. Also reports JSON-failure and forced-delay rates
so a fallback is never mistaken for a reasoning result.

Team-design files (with `arm`) are grouped by arm. Probe and
decision-linked calibration are always reported in separate tables.
Legacy focal files keep the old focal report.
"""
import argparse
import os

import pandas as pd

from .metrics import (brier, cascade_resistance, delay_quality, ece,
                      say_do_gap, team_cascade_resistance, team_delay_quality)
from .stats import auc_score


def _pairs(tdf, drop_self=True):
    df = tdf
    if drop_self and "agent" in df.columns and "target" in df.columns:
        df = df[df["agent"].astype(str) != df["target"].astype(str)]
    return [(float(t), 0 if bool(m) else 1)  # trust = P(innocent)
            for t, m in zip(df["trust"], df["target_is_mafia"])]


def _report_trust_table(label, tdf):
    if tdf is None or len(tdf) == 0:
        print(f"{label}: no rows")
        return
    pairs = _pairs(tdf)
    if not pairs:
        print(f"{label}: no rows after self-exclusion")
        return
    auc = auc_score([p[0] for p in pairs], [p[1] for p in pairs])
    print(f"{label}: ECE {ece(pairs):.3f} Brier {brier(pairs):.3f} "
          f"AUC {auc:.3f} (n={len(pairs)}, self-rows excluded)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="logs/games.parquet")
    ap.add_argument("--votes", default="logs/votes.parquet")
    ap.add_argument("--trust", default="logs/trust.parquet")
    args = ap.parse_args()
    df = pd.read_parquet(args.input)
    print(f"Games: {len(df)} rows")
    for col in ("provider", "model", "gate", "night_mode"):
        if col in df.columns:
            print(f"{col}: {df[col].value_counts(dropna=False).to_dict()}")
    print()
    is_team = "arm" in df.columns and df.get("design", pd.Series(dtype=str)).astype(str).eq("team").any() \
        if "design" in df.columns else "arm" in df.columns
    if is_team:
        print(df.groupby("arm")["winner"].value_counts(normalize=True).round(3))
        for arm, g in df.groupby("arm"):
            wr = (g["winner"] == "village").mean()
            print(f"{arm}: village win-rate (n={len(g)}): {wr:.3f} "
                  f"draws={(g['winner'] == 'draw').sum()} mean_days={g['days'].mean():.2f}")
    else:
        print(df.groupby("focal")["winner"].value_counts(normalize=True).round(3))
        for focal, g in df.groupby("focal"):
            sub = g[~g["focal_role"].isin(["mafia"])]
            if len(sub):
                wr = (sub["winner"] == "village").mean()
                print(f"{focal}: village win-rate (focal non-mafia, n={len(sub)}): {wr:.2f}")
    if "json_failures" in df.columns:
        print(f"JSON failures: {int(df['json_failures'].sum())} over "
              f"{len(df)} games ({df['json_failures'].mean():.2f}/game)")

    if os.path.exists(args.votes):
        vdf = pd.read_parquet(args.votes)
        if is_team and "is_village" in vdf.columns:
            for arm, g in vdf.groupby("arm"):
                print(f"\n[{arm}] team_cascade_resistance: {team_cascade_resistance(g):.3f} "
                      f"team_delay_quality: {team_delay_quality(g):.3f} "
                      f"abstention: {(g[g['is_village'].astype(bool)]['vote'].astype(str) == 'no-lynch').mean():.3f} "
                      f"(games={g['game_id'].nunique()}, rows={len(g)})")
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
        tdf = pd.read_parquet(args.trust)
        if "trust_source" in tdf.columns:
            print("\n--- Probe calibration (elicited, all arms) ---")
            probe = tdf[tdf["trust_source"].astype(str) == "probe"]
            if "arm" in probe.columns and len(probe):
                for arm, g in probe.groupby("arm"):
                    _report_trust_table(f"probe[{arm}]", g)
            else:
                _report_trust_table("probe", probe)
            print("\n--- Decision-linked calibration (DMN only, descriptive) ---")
            dec = tdf[tdf["trust_source"].astype(str) == "decision"]
            if "verified" in dec.columns:
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
