"""Quick evaluate: python -m src.eval.evaluate --input logs/games.parquet
Also reads logs/votes.parquet + logs/trust.parquet when present and reports
all five thesis metrics (win-rate, ECE/Brier, cascade-resistance,
delay-quality, say-do-gap) with n.
"""
import argparse, os
import pandas as pd
from .metrics import brier, cascade_resistance, delay_quality, ece, say_do_gap

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="logs/games.parquet")
    ap.add_argument("--votes", default="logs/votes.parquet")
    ap.add_argument("--trust", default="logs/trust.parquet")
    args = ap.parse_args()
    df = pd.read_parquet(args.input)
    print(df.groupby("focal")["winner"].value_counts(normalize=True))
    # village win-rate when focal is villager-side
    for focal, g in df.groupby("focal"):
        sub = g[~g["focal_role"].isin(["mafia"])]
        if len(sub):
            wr = (sub["winner"] == "village").mean()
            print(f"{focal}: village win-rate (focal non-mafia, n={len(sub)}): {wr:.2f}")
    if os.path.exists(args.votes):
        vdf = pd.read_parquet(args.votes)
        print(f"cascade_resistance: {cascade_resistance(vdf):.3f} "
              f"(games={vdf['game_id'].nunique()}, rows={len(vdf)})")
        print(f"delay_quality: {delay_quality(vdf):.3f}")
        committed = vdf[vdf["commitment"].fillna("") != ""]
        print(f"say_do_gap: {say_do_gap(committed):.3f} "
              f"(commitment rows={len(committed)} of {len(vdf)})")
    else:
        print(f"No {args.votes} yet — run run_arena first (per-day vote rows).")
    if os.path.exists(args.trust):
        tdf = pd.read_parquet(args.trust)
        pairs = [(float(t), 0 if bool(m) else 1)  # trust = P(innocent)
                 for t, m in zip(tdf["trust"], tdf["target_is_mafia"])]
        print(f"ECE: {ece(pairs):.3f} Brier: {brier(pairs):.3f} (n={len(pairs)})")
    else:
        print(f"No {args.trust} yet — run run_arena first (per-day trust rows).")

if __name__ == "__main__":
    main()
