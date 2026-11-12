"""EXPLORATORY (D-006): why are games short? Pooled mechanics only on
non-confirmatory histories (no arm comparison). Usage:
python -m src.explore.game_length"""
import glob, json, os, re
import pandas as pd
from src.mafia.engine import Game

rows = []
for run in sorted(glob.glob("logs/runs/*/")):
    camp = os.path.basename(run.rstrip("/"))
    if camp.startswith("smoke-team-02"):
        continue
    gp = os.path.join(run, "games.parquet")
    if not os.path.exists(gp):
        continue
    g = pd.read_parquet(gp)
    for r in g.itertuples():
        hp = os.path.join(run, "raw", f"history_{r.game_id}.parquet")
        if not os.path.exists(hp):
            continue
        h = pd.read_parquet(hp)
        roles = [p.role for p in Game(seed=int(r.seed)).players]
        nights = h[h.phase.astype(str).str.startswith("night")]
        results = h[h.phase.astype(str).str.startswith("result")]
        kills = [int(m.group(1)) for m in (re.search(r"Player (\d+) was killed", t) for t in nights.text) if m]
        lynches = [int(m.group(1)) for m in (re.search(r"Player (\d+) lynched", t) for t in results.text) if m]
        rows.append({"campaign": camp, "game": r.game_id, "winner": r.winner,
                     "day_votes": len(results), "night_kills": len(kills), "saves": int(nights.text.str.contains("saved").sum()),
                     "lynches": len(lynches), "no_lynch_days": len(results) - len(lynches),
                     "mafia_lynched": sum(roles[x] == "mafia" for x in lynches),
                     "innocent_lynched": sum(roles[x] != "mafia" for x in lynches),
                     "night0_kill": int(any("night-0" == p for p in nights.phase.astype(str)) and
                                        nights[nights.phase.astype(str) == "night-0"].text.str.contains("killed").any())})
df = pd.DataFrame(rows)
s = {"n_games": len(df), "campaigns": df.campaign.nunique(),
     "mean_day_votes": round(df.day_votes.mean(), 2),
     "share_no_lynch_days": round(df.no_lynch_days.sum() / df.day_votes.sum(), 3),
     "lynches_per_game": round(df.lynches.mean(), 2),
     "innocent_share_of_lynches": round(df.innocent_lynched.sum() / max(1, df.lynches.sum()), 3),
     "night0_kill_rate": round(df.night0_kill.mean(), 3),
     "save_rate_per_night": round(df.saves.sum() / max(1, (df.saves + df.night_kills).sum()), 3),
     "winner_share": df.winner.value_counts(normalize=True).round(3).to_dict(),
     "games_ended_by_cap": int((df.winner == "draw").sum())}
# arithmetic of the engine: 7 players, 2 mafia. Each night kill removes one innocent unless saved;
# a mafia win needs mafia >= others, i.e. 3 innocent removals (5 -> 2) with both mafia alive.
s["note"] = ("With both mafia alive, mafia win after 3 innocent removals (night kills + wrongful lynches). "
             "A strict-majority lynch needs 4 of 7 (or 4 of 6) votes; mafia supply 2.")
os.makedirs("logs/explore", exist_ok=True)
json.dump({"summary": s, "rows": rows}, open("logs/explore/d006_game_length.json", "w"), indent=1, default=str)
print(json.dumps(s, indent=1, default=str))
