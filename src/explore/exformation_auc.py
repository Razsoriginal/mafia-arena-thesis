"""EXPLORATORY (D-005): do DMN/TPN fields predict mafia? Non-confirmatory
traces only (pilot, sweeps, smoke-team-01). Village (non-mafia) reasoning
agents only; label = hypothesised suspect is mafia; AUC with a
game-clustered bootstrap CI. Usage: python -m src.explore.exformation_auc
"""
import glob, json, os
import numpy as np, pandas as pd
from src.mafia.engine import Game
from src.eval.stats import auc_score

rows = []
for run in sorted(glob.glob("logs/runs/*/")) + sorted(glob.glob("logs/archive/*/")):
    gp = os.path.join(run, "games.parquet")
    if not os.path.exists(gp):
        continue
    g = pd.read_parquet(gp)
    seed_of = dict(zip(g["game_id"].astype(str), g["seed"]))
    camp = os.path.basename(run.rstrip("/"))
    if camp.startswith(("smoke-team-02",)) or "confirm" in camp:
        continue
    for f in glob.glob(os.path.join(run, "raw", "trace_*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        rid = str(d.get("run_id", ""))
        if rid not in seed_of:
            continue
        roles = [p.role for p in Game(seed=int(seed_of[rid])).players]
        traces = d.get("traces_all") or {}
        if not traces and d.get("trace"):
            traces = {str(d.get("focal_pid")): d["trace"]}
        for pid, t in traces.items():
            if not isinstance(t, dict) or roles[int(pid)] == "mafia":
                continue
            ver = {str(v.get("suspect")): v for v in ((t.get("tpn") or {}).get("verified") or []) if isinstance(v, dict)}
            for h in ((t.get("dmn") or {}).get("hypotheses") or []):
                if not isinstance(h, dict):
                    continue
                try:
                    s = int(str(h.get("suspect")).strip().lstrip("Pp"))
                    conf = float(h.get("confidence"))
                except Exception:
                    continue
                if not 0 <= s < 7 or s == int(pid):
                    continue
                v = ver.get(str(s), {})
                rows.append({"campaign": camp, "game": f"{camp}/{rid}", "agent": int(pid), "suspect": s,
                             "is_mafia": int(roles[s] == "mafia"), "dmn_conf": conf,
                             "tpn_conf": float(v["revised_confidence"]) if "revised_confidence" in v else np.nan,
                             "contradiction": float(bool(v.get("contradiction_found"))) if v else np.nan,
                             "n_exformation": len(h.get("exformation") or []),
                             "exf_chars": sum(len(str(x)) for x in (h.get("exformation") or []))})
df = pd.DataFrame(rows).drop_duplicates()


def cluster_auc(sub, col, n_boot=2000, seed=20261106):
    sub = sub.dropna(subset=[col])
    if sub.is_mafia.nunique() < 2:
        return None
    base = auc_score(sub[col], 1 - sub.is_mafia)  # stats.auc expects P(innocent) with innocent=1
    auc = 1 - base  # higher score -> mafia
    games = sub.game.unique(); rng = np.random.default_rng(seed); boots = []
    by = {gname: grp for gname, grp in sub.groupby("game")}
    for _ in range(n_boot):
        s = pd.concat([by[x] for x in rng.choice(games, len(games))])
        if s.is_mafia.nunique() == 2:
            boots.append(1 - auc_score(s[col], 1 - s.is_mafia))
    return {"feature": col, "auc": round(auc, 3), "ci": [round(np.percentile(boots, 2.5), 3), round(np.percentile(boots, 97.5), 3)],
            "n_rows": len(sub), "n_games": len(games), "base_rate_mafia": round(sub.is_mafia.mean(), 3)}


out = {"n_rows": len(df), "n_games": df.game.nunique(), "campaigns": df.campaign.value_counts().to_dict()}
out["results"] = [cluster_auc(df, c) for c in ("dmn_conf", "tpn_conf", "contradiction", "n_exformation", "exf_chars")]
os.makedirs("logs/explore", exist_ok=True)
json.dump(out, open("logs/explore/d005_exformation_auc.json", "w"), indent=2, default=str)
print(json.dumps(out, indent=2, default=str))


def paired_auc_diff(sub, a="dmn_conf", b="tpn_conf", n_boot=2000, seed=20261106):
    sub = sub.dropna(subset=[a, b])
    f = lambda s: (1 - auc_score(s[a], 1 - s.is_mafia)) - (1 - auc_score(s[b], 1 - s.is_mafia))
    games = sub.game.unique(); rng = np.random.default_rng(seed)
    by = {g: grp for g, grp in sub.groupby("game")}; boots = []
    for _ in range(n_boot):
        s = pd.concat([by[x] for x in rng.choice(games, len(games))])
        if s.is_mafia.nunique() == 2:
            boots.append(f(s))
    return {"diff": round(f(sub), 3), "ci": [round(np.percentile(boots, 2.5), 3), round(np.percentile(boots, 97.5), 3)],
            "n_rows": len(sub), "n_games": len(games)}


out["paired_dmn_minus_tpn_auc"] = paired_auc_diff(df)
out["mean_shift_tpn_minus_dmn"] = {k: round(float((g.tpn_conf - g.dmn_conf).mean()), 3)
                                   for k, g in df.dropna(subset=["tpn_conf"]).groupby("is_mafia")}
json.dump(out, open("logs/explore/d005_exformation_auc.json", "w"), indent=2, default=str)
print("PAIRED", out["paired_dmn_minus_tpn_auc"], "SHIFT by is_mafia", out["mean_shift_tpn_minus_dmn"])
