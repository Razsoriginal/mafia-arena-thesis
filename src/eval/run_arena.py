"""Arena runner: python -m src.eval.run_arena --games 5 --agents dmn_tpn,cot --seed 0
All roles use the backbone from src/config.py (OpenRouter when configured,
else AiCredits). EVT DELAY source: --gate llm (tau/evt heuristics) | jev.
Per-day metric tables: logs/votes.parquet + logs/trust.parquet (+ game rows
in --out, default logs/games.parquet). Per-day traces: logs/raw/trace_*.json.
"""
import argparse, os, json, random, time, pandas as pd
from src.mafia.engine import Game
from src.agents.baselines import CotAgent, ReactAgent, ConstitutionAgent
from src.agents.dmn_tpn_agent import DmnTpnAgent
from src.llm_client import COST_LOG
from src.config import settings

AGENTS = {"cot": CotAgent, "react": ReactAgent, "constitution": ConstitutionAgent, "dmn_tpn": DmnTpnAgent}

# AiCredits catalog rates 2026-10-14 for meta/muse-spark-1.3-contributor (USD/token) + INR/USD.
# OpenRouter :free models cost 0; other OpenRouter models: token counts are
# logged, set a rate here before quoting cost for a paid model.
_MUSE_IN, _MUSE_OUT, _INR_PER_USD = 1e-07, 2e-07, 95.319179


def _est_cost_inr(prompt_tokens: int, completion_tokens: int) -> float:
    if settings.provider == "openrouter":
        return 0.0  # :free = 0; paid OpenRouter rate not configured yet
    return round((prompt_tokens * _MUSE_IN + completion_tokens * _MUSE_OUT) * _INR_PER_USD, 4)


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


def _private_note(game, pid, det_info):
    """Per-agent private info appended to that agent's view only (never shared history)."""
    role = game.players[pid].role
    notes = []
    if role == "mafia":
        partners = [p.pid for p in game.players if p.role == "mafia" and p.pid != pid]
        notes.append(f"You are MAFIA. Your partners: {partners}. Coordinate subtly, do not expose each other.")
    if role == "detective" and pid in det_info:
        chk, chk_role = det_info[pid]
        if chk is not None:
            notes.append(f"Private detective result: Player {chk} is {chk_role}. Do not reveal it unless you choose to.")
    if not notes:
        return ""
    return "\n[private: only you see this]\n" + "\n".join(notes)


def play_one(seed, focal="dmn_tpn", gate="llm", run_id=None, focal_role="random"):
    run_id = run_id or f"{seed}-{focal}"
    game, seed = _make_game(seed, focal_role)
    # assign: focal agent class controls pid 0, baselines elsewhere
    agents = {}
    for p in game.players:
        cls = AGENTS[focal] if p.pid == 0 else AGENTS["cot"]
        ag = cls(pid=p.pid)
        if isinstance(ag, DmnTpnAgent):
            ag.backend = gate
        agents[p.pid] = ag
    game._focal_last = {}
    det_info = {}  # detective pid -> (checked_pid, role): private, never shared
    prev_majority = None
    vote_rows, trust_rows = [], []
    max_days = 5
    for day in range(max_days):
        if game.check_over():
            break
        game.day = day
        # night (simple heuristics: seeded-random kill, doctor self-save, detective checks lowest alive non-self)
        alive = game.alive_ids()
        mafia_pids = [p.pid for p in game.alive() if p.role == "mafia"]
        if mafia_pids and len(alive) > 2:
            rr = random.Random(seed * 1000 + day)
            candidates = [a for a in alive if game.players[a].role != "mafia"]
            kill = rr.choice(candidates) if candidates else None
            save = None
            doc = [p.pid for p in game.alive() if p.role == "doctor"]
            if doc:
                save = doc[0]  # self-save MVP
            det = [p.pid for p in game.alive() if p.role == "detective"]
            chk = min([a for a in alive if a not in det]) if det else None
            res = game.night(kill, save, chk)
            if det and chk is not None:
                det_info[det[0]] = res["detective_info"]
            if res["killed"] is not None:
                game.add("engine", f"Night: Player {res['killed']} was killed.", f"night-{day}")
            else:
                game.add("engine", "Night: No one died (saved).", f"night-{day}")
        # reason BEFORE discussion: the DMN/TPN plan (cached per day) informs speech
        alive = game.alive_ids()
        alive_roles = {p.pid: p.role for p in game.alive()}
        shared, facts = game.history_text(), game.facts_text()
        trust_all, traces = {}, {}
        for p in list(game.alive()):
            ag = agents[p.pid]
            if isinstance(ag, DmnTpnAgent):
                trust, trace, delay = ag.reason(
                    p.role, shared + _private_note(game, p.pid, det_info),
                    facts, alive, prev_majority, alive_roles)
                trust_all[p.pid] = trust
                traces[p.pid] = trace
                if p.pid == 0:
                    # pid 0 is the focal agent: keep its last reasoning even if it dies later
                    game._focal_last = {"trust": trust, "trace": trace}
            else:
                trust_all[p.pid] = {}
        # day discuss 2 rounds (each agent sees shared history + own private note)
        for rnd in range(2):
            for p in list(game.alive()):
                ag = agents[p.pid]
                utt = ag.speak(p.role, game.history_text() + _private_note(game, p.pid, det_info))
                game.add(p.pid, utt, f"day-{day}-r{rnd}")
        # vote (Jev is consulted inside DmnTpnAgent.vote when gate=jev)
        votes, infos = {}, {}
        full = game.history_text()
        for p in list(game.alive()):
            ag = agents[p.pid]
            view = full + _private_note(game, p.pid, det_info)
            if isinstance(ag, DmnTpnAgent):
                v, info = ag.vote(p.role, view, trust_all[p.pid], traces[p.pid])
            else:
                v, info = ag.vote(p.role, view, {})
            votes[p.pid] = v
            infos[p.pid] = info if isinstance(info, dict) else {}
            game.add(p.pid, f"votes {v} ({infos[p.pid].get('reason','')[:120]})", f"vote-{day}")
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
        # per-day metric rows (ALL voters, not just focal)
        for voter, v in votes.items():
            info = infos.get(voter, {})
            jev = info.get("jev") if isinstance(info, dict) else None
            vote_rows.append({
                "game_id": run_id, "day": day, "voter": voter, "vote": str(v),
                "majority_vote": str(maj), "majority_correct": bool(maj_correct),
                "is_focal": voter == 0,
                "vote_reason": str(info.get("reason", ""))[:500],
                "commitment": str(info.get("commitment", "")),
                "jev_stub": (jev.get("stub") if isinstance(jev, dict) else None),
            })
        for target, tval in (trust_all.get(0, {}) or {}).items():
            try:
                is_mafia = game.players[int(target)].role == "mafia"
                trust_rows.append({"game_id": run_id, "day": day, "agent": 0,
                                  "target": str(target), "trust": float(tval),
                                  "target_is_mafia": bool(is_mafia)})
            except Exception:
                continue
        # full per-day trace for audit
        try:
            os.makedirs("logs/raw", exist_ok=True)
            with open(f"logs/raw/trace_{run_id}-day{day}.json", "w", encoding="utf-8") as f:
                json.dump({"trust": trust_all.get(0, {}), "trace": traces.get(0, {})}, f, default=str)
        except Exception:
            pass
        # last-day summary (games.parquet, dashboard-compatible)
        game._last_votes = {"votes": votes, "majority": str(maj), "majority_correct": maj_correct,
                            "trust": trust_all.get(0, {}), "trace": traces.get(0, {})}
        _log_progress(run_id, seed, focal, gate, day, len(game.alive_ids()), game.winner)
        prev_majority = str(maj)
    game.check_over()
    if game.winner is None:
        game.winner = "draw"  # max_days reached with no elimination (timeout)
    game._vote_rows = vote_rows
    game._trust_rows = trust_rows
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
    rows, all_votes, all_trust = [], [], []
    for i in range(args.games):
        for focal in focals:
            focal = focal.strip()
            run_id = f"{args.seed+i}-{focal}"
            mark = dict(COST_LOG)
            g = play_one(seed=args.seed + i * 100, focal=focal, gate=args.gate,
                         run_id=run_id, focal_role=args.focal_role)
            all_votes.extend(getattr(g, "_vote_rows", []))
            all_trust.extend(getattr(g, "_trust_rows", []))
            dp = COST_LOG["prompt_tokens"] - mark["prompt_tokens"]
            dc = COST_LOG["completion_tokens"] - mark["completion_tokens"]
            lv = getattr(g, "_last_votes", {})
            fl = getattr(g, "_focal_last", {}) or {}
            trace = fl.get("trace", {}) if isinstance(fl, dict) else {}
            jev_info = trace.get("jev") if isinstance(trace, dict) else None
            rows.append({
                "game_id": run_id, "seed": args.seed + i, "focal": focal,
                "gate": args.gate, "tau": settings.tau_delay,
                "winner": g.winner, "days": g.day,
                "focal_role": g.players[0].role, "majority_correct": lv.get("majority_correct"),
                "trust_json": json.dumps(fl.get("trust", {}) if isinstance(fl, dict) else {}), "trace_json": json.dumps(fl.get("trace", {}) if isinstance(fl, dict) else {}, default=str)[:4000],
                "prompt_tokens": dp, "completion_tokens": dc,
                "est_cost_inr": _est_cost_inr(dp, dc),
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
    if all_votes:
        pd.DataFrame(all_votes).to_parquet("logs/votes.parquet", index=False)
        print(f"Saved {len(all_votes)} per-day vote rows to logs/votes.parquet")
    if all_trust:
        pd.DataFrame(all_trust).to_parquet("logs/trust.parquet", index=False)
        print(f"Saved {len(all_trust)} per-day trust rows to logs/trust.parquet")

if __name__ == "__main__":
    main()
