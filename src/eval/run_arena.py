"""Arena runner MVP: python -m src.eval.run_arena --games 5 --agents dmn_tpn,cot --seed 0
All roles use same backbone (meta/muse-spark-1.3-contributor via AiCredits) unless --focal-only.
EVT DELAY source: --gate llm (tau/evt heuristics) | jev (BeatAI SystemOne noul).
"""
import argparse, os, json, time, pandas as pd
from src.mafia.engine import Game
from src.agents.baselines import CotAgent, ReactAgent, ConstitutionAgent
from src.agents.dmn_tpn_agent import DmnTpnAgent
from src.llm_client import COST_LOG

AGENTS = {"cot": CotAgent, "react": ReactAgent, "constitution": ConstitutionAgent, "dmn_tpn": DmnTpnAgent}

# AiCredits catalog rates 2026-10-14 for meta/muse-spark-1.3-contributor (USD/token) + INR/USD.
_MUSE_IN, _MUSE_OUT, _INR_PER_USD = 1e-07, 2e-07, 95.319179


def _log_progress(run_id, seed, focal, gate, day, alive, winner):
    os.makedirs("logs", exist_ok=True)
    with open("logs/progress.jsonl", "a") as f:
        f.write(json.dumps({"ts": time.time(), "run_id": run_id, "seed": seed,
                            "focal": focal, "gate": gate, "day": day,
                            "alive": alive, "winner": winner}) + "\n")

def _make_game(seed, focal_role="random"):
    """Role-balanced game: re-seed (bounded) until pid 0 has focal_role. Engine untouched."""
    if focal_role == "random":
        return Game(seed=seed), seed
    for k in range(50):
        s = seed + k * 1000
        g = Game(seed=s)
        if g.players[0].role == focal_role:
            return g, s
    return Game(seed=seed), seed  # fallback: record actual role


def play_one(seed, focal="dmn_tpn", gate="llm", run_id=None, focal_role="random"):
    run_id = run_id or f"{seed}-{focal}"
    game, seed = _make_game(seed, focal_role)
    # assign: focal agent controls pid 0 (villager side forced for fair win-rate: rotate role by re-seeding until pid0 not mafia? MVP: keep random, record)
    agents = {}
    for p in game.players:
        cls = AGENTS[focal] if p.pid == 0 else AGENTS["cot"]
        ag = cls(pid=p.pid)
        if isinstance(ag, DmnTpnAgent):
            ag.backend = gate
        agents[p.pid] = ag
    max_days = 5
    for day in range(max_days):
        if game.check_over():
            break
        game.day = day
        # night (simple heuristics: mafia kills lowest pid non-mafia, doctor saves self/random, detective checks random)
        alive = game.alive_ids()
        mafia_pids = [p.pid for p in game.alive() if p.role == "mafia"]
        if mafia_pids and len(alive) > 2:
            kill = min([a for a in alive if game.players[a].role != "mafia"])
            save = None
            doc = [p.pid for p in game.alive() if p.role == "doctor"]
            if doc:
                save = doc[0]  # self-save MVP
            det = [p.pid for p in game.alive() if p.role == "detective"]
            chk = min([a for a in alive if a not in det]) if det else None
            res = game.night(kill, save, chk)
            if res["killed"] is not None:
                game.add("engine", f"Night: Player {res['killed']} was killed.", f"night-{day}")
            else:
                game.add("engine", "Night: No one died (saved).", f"night-{day}")
        # day discuss 2 rounds
        for rnd in range(2):
            for p in list(game.alive()):
                ag = agents[p.pid]
                utt = ag.speak(p.role if p.pid != 0 else p.role, game.history_text())
                game.add(p.pid, utt, f"day-{day}-r{rnd}")
        # trust + EVT for focal
        votes = {}
        trust_all, traces = {}, {}
        for p in list(game.alive()):
            ag = agents[p.pid]
            if isinstance(ag, DmnTpnAgent):
                trust, trace, delay = ag.reason(p.role, game.history_text(), game.facts_text(), game.alive_ids())
                trust_all[p.pid] = trust
                traces[p.pid] = trace
            else:
                trust_all[p.pid] = {}
        for p in list(game.alive()):
            ag = agents[p.pid]
            if isinstance(ag, DmnTpnAgent):
                v, info = ag.vote(p.role, game.history_text(), trust_all[p.pid], traces[p.pid])
            else:
                v, info = ag.vote(p.role, game.history_text(), {})
            votes[p.pid] = v
            game.add(p.pid, f"votes {v} ({info.get('reason','')[:120]})", f"vote-{day}")
        # record majority for metrics
        from collections import Counter
        c = Counter([v for v in votes.values() if v != "no-lynch"])
        maj = c.most_common(1)[0][0] if c else "no-lynch"
        # majority correct? true mafia?
        maj_correct = True
        if maj != "no-lynch":
            try:
                maj_correct = game.players[int(maj)].role == "mafia"
            except Exception:
                maj_correct = False
        lynched = game.vote(votes)
        if lynched is not None:
            game.add("engine", f"Day {day}: Player {lynched} lynched.", f"result-{day}")
        else:
            game.add("engine", f"Day {day}: No lynch (delay).", f"result-{day}")
        game.check_over()
        # stash per-day votes for parquet (simplified: store last day only in MVP, full in v1)
        game._last_votes = {"votes": votes, "majority": str(maj), "majority_correct": maj_correct,
                            "trust": trust_all.get(0, {}), "trace": traces.get(0, {})}
        _log_progress(run_id, seed, focal, gate, day, len(game.alive_ids()), game.winner)
    game.check_over()
    if game.winner is None:
        game.winner = "draw"  # max_days reached with no elimination (MVP timeout)
    return game

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=5)
    ap.add_argument("--agents", type=str, default="dmn_tpn,cot")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--gate", type=str, default="llm", choices=["llm", "jev"])
    ap.add_argument("--focal-role", type=str, default="random",
                    choices=["random", "villager", "mafia", "doctor", "detective"])
    ap.add_argument("--out", type=str, default="logs/games.parquet")
    args = ap.parse_args()
    focals = args.agents.split(",")
    rows = []
    for i in range(args.games):
        for focal in focals:
            focal = focal.strip()
            run_id = f"{args.seed+i}-{focal}"
            mark = dict(COST_LOG)
            g = play_one(seed=args.seed + i * 100, focal=focal, gate=args.gate,
                         run_id=run_id, focal_role=args.focal_role)
            dp = COST_LOG["prompt_tokens"] - mark["prompt_tokens"]
            dc = COST_LOG["completion_tokens"] - mark["completion_tokens"]
            lv = getattr(g, "_last_votes", {})
            trace = lv.get("trace", {}) if isinstance(lv, dict) else {}
            jev_info = trace.get("jev") if isinstance(trace, dict) else None
            rows.append({
                "game_id": run_id, "seed": args.seed + i, "focal": focal,
                "gate": args.gate,
                "winner": g.winner, "days": g.day,
                "focal_role": g.players[0].role, "majority_correct": lv.get("majority_correct"),
                "trust_json": json.dumps(lv.get("trust", {})), "trace_json": json.dumps(lv.get("trace", {}), default=str)[:4000],
                "prompt_tokens": dp, "completion_tokens": dc,
                "est_cost_inr": round((dp * _MUSE_IN + dc * _MUSE_OUT) * _INR_PER_USD, 4),
                "jev_stub": jev_info.get("stub") if isinstance(jev_info, dict) else None,
            })
            # save raw history (speaker mixes int pids + "engine" -> normalize for parquet)
            os.makedirs("logs/raw", exist_ok=True)
            hdf = pd.DataFrame(g.history)
            for _c in ("speaker", "phase"):
                if _c in hdf.columns:
                    hdf[_c] = hdf[_c].astype(str)
            hdf.to_parquet(f"logs/raw/history_{args.seed+i}-{focal}.parquet", index=False)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    pd.DataFrame(rows).to_parquet(args.out, index=False)
    print(f"Saved {len(rows)} rows to {args.out}")
    print(pd.DataFrame(rows)[["focal", "winner", "focal_role"]].value_counts(dropna=False))

if __name__ == "__main__":
    main()
