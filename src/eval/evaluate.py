"""Quick evaluate: python -m src.eval.evaluate --input logs/games.parquet

Reads logs/votes.parquet + logs/trust.parquet when present and reports the
five thesis metrics with n. Also reports JSON-failure and forced-delay rates
so a fallback is never mistaken for a reasoning result.
"""
import argparse
import os

import pandas as pd

from .metrics import brier, cascade_resistance, delay_quality, ece, say_do_gap


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
        pairs = [(float(t), 0 if bool(m) else 1)  # trust = P(innocent)
                 for t, m in zip(tdf["trust"], tdf["target_is_mafia"])]
        print(f"ECE: {ece(pairs):.3f} Brier: {brier(pairs):.3f} (n={len(pairs)})")
    else:
        print(f"No {args.trust} yet — run run_arena first (per-day trust rows).")


if __name__ == "__main__":
    main()
