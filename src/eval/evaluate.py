"""Quick evaluate: python -m src.eval.evaluate --input logs/games.parquet"""
import argparse, pandas as pd

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="logs/games.parquet")
    args = ap.parse_args()
    df = pd.read_parquet(args.input)
    print(df.groupby("focal")["winner"].value_counts(normalize=True))
    # village win-rate when focal is villager-side
    for focal, g in df.groupby("focal"):
        sub = g[~g["focal_role"].isin(["mafia"])]
        if len(sub):
            wr = (sub["winner"] == "village").mean()
            print(f"{focal}: village win-rate (focal non-mafia, n={len(sub)}): {wr:.2f}")

if __name__ == "__main__":
    main()
