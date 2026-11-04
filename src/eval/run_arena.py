"""Arena runner: python -m src.eval.run_arena --games 5 --agents dmn_tpn,cot --seed 0

Backbone is AiCredits (src/config.py). EVT DELAY source: --gate llm | jev.
Night phase: --night llm (default, LLM choice with scripted fallback) or
scripted (legacy deterministic heuristics).

Every invocation writes its own audit bundle:
  logs/runs/<run_tag>/manifest.json   config + git sha + thresholds
  logs/runs/<run_tag>/games.parquet
  logs/runs/<run_tag>/votes.parquet
  logs/runs/<run_tag>/trust.parquet
  logs/runs/<run_tag>/raw/trace_*.json + history_*.parquet
Canonical logs/games.parquet, logs/votes.parquet and logs/trust.parquet are
upserted (never overwritten) so partial runs stay usable.
"""
import argparse
import json
import os
import random
import subprocess
import time
from datetime import datetime, timezone

import pandas as pd

from src.agents.baselines import CotAgent, ReactAgent, ConstitutionAgent
from src.agents.dmn_tpn_agent import DmnTpnAgent
from src.config import settings
from src.llm_client import COST_LOG
from src.mafia.engine import Game

AGENTS = {"cot": CotAgent, "react": ReactAgent, "constitution": ConstitutionAgent, "dmn_tpn": DmnTpnAgent}

# AiCredits catalog rates (USD/token) + INR/USD for meta/muse-spark-1.3-contributor.
_MUSE_IN, _MUSE_OUT, _INR_PER_USD = 1e-07, 2e-07, 95.319179


def _est_cost_inr(prompt_tokens: int, completion_tokens: int) -> float:
    return round((prompt_tokens * _MUSE_IN + completion_tokens * _MUSE_OUT) * _INR_PER_USD, 4)


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _upsert(path: str, new_df: pd.DataFrame, keys: list):
    """Append rows to a parquet table, replacing duplicates on `keys`."""
    if new_df is None or new_df.empty:
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if os.path.exists(path):
        try:
            old = pd.read_parquet(path)
            df = pd.concat([old, new_df], ignore_index=True)
            present = [k for k in keys if k in df.columns]
            if present:
                df = df.drop_duplicates(subset=present, keep="last")
        except Exception:
            df = new_df
    else:
        df = new_df
    df.to_parquet(path, index=False)


def _write_manifest(path: str, args, run_tag: str, git_sha: str):
    manifest = {
        "run_tag": run_tag,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha,
        "args": vars(args),
        "llm": {
            "provider": settings.provider,
            "base_url": settings.base_url,
            "model": settings.model,
            "max_tokens": settings.max_tokens,
            "temperature_dialogue": settings.temp_dialogue,
            "temperature_json": settings.temp_json,
        },
        "jev": {
            "base_url": settings.jev_base_url,
            "model": settings.jev_model,
            "key_present": bool(settings.jev_api_key),
            "min_interval_s": settings.jev_min_interval,
            "threshold": settings.jev_threshold,
        },
        "thresholds": {"tau_delay": settings.tau_delay, "evt_threshold": settings.evt_threshold},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def _log_progress(run_tag, run_id, seed, requested_seed, focal, gate, night_mode, day, alive, winner):
    os.makedirs("logs", exist_ok=True)
    with open("logs/progress.jsonl", "a") as f:
        f.write(json.dumps({
            "ts": time.time(), "run_tag": run_tag, "run_id": run_id,
            "seed": seed, "requested_seed": requested_seed,
            "focal": focal, "gate": gate, "night_mode": night_mode,
            "provider": settings.provider, "model": settings.model,
            "day": day, "alive": alive, "winner": winner,
        }) + "\n")


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


def _night_actions(game, agents, seed, day, night_mode, det_info):
    """Return (kill, save, check). LLM choices fall back to scripted heuristics."""
    alive = game.alive_ids()
    mafia_pids = [p.pid for p in game.alive() if p.role == "mafia"]
    kill = save = check = None
    if not mafia_pids or len(alive) <= 2:
        return None, None, None

    candidates = [a for a in alive if game.players[a].role != "mafia"]
    if night_mode == "llm" and candidates:
        killer = min(mafia_pids)
        ctx = game.history_text(limit=40) + _private_note(game, killer, det_info)
        pick = agents[killer].night_action("mafia", ctx, alive, candidates, "kill")
        if pick is not None:
            kill = int(pick)
    if kill is None and candidates:
        kill = random.Random(seed * 1000 + day).choice(candidates)

    doctors = [p.pid for p in game.alive() if p.role == "doctor"]
    if doctors:
        if night_mode == "llm":
            doc = doctors[0]
            ctx = game.history_text(limit=40) + _private_note(game, doc, det_info)
            pick = agents[doc].night_action("doctor", ctx, alive, alive, "save")
            if pick is not None:
                save = int(pick)
        if save is None:
            save = doctors[0]

    detectives = [p.pid for p in game.alive() if p.role == "detective"]
    if detectives:
        det = detectives[0]
        options = [a for a in alive if a != det]
        if night_mode == "llm" and options:
            ctx = game.history_text(limit=40) + _private_note(game, det, det_info)
            pick = agents[det].night_action("detective", ctx, alive, options, "check")
            if pick is not None:
                check = int(pick)
        if check is None and options:
            check = min(options)
    return kill, save, check


def play_one(seed, focal="dmn_tpn", gate="llm", run_id=None, focal_role="random",
             night_mode="llm", run_tag="", run_dir="logs/runs/tmp", requested_seed=None,
             max_days=5):
    game, _ = _make_game(seed, focal_role)
    run_id = run_id or f"{game.seed}-{focal}"
    requested_seed = seed if requested_seed is None else requested_seed
    game._run_id = run_id
    raw_dir = os.path.join(run_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)
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
    for day in range(max_days):
        if game.check_over():
            break
        game.day = day
        kill, save, check = _night_actions(game, agents, game.seed, day, night_mode, det_info)
        if kill is not None:
            res = game.night(kill, save, check)
            det = [p.pid for p in game.alive() if p.role == "detective"]
            if det and check is not None:
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
                "run_tag": run_tag, "game_id": run_id, "day": day, "voter": voter,
                "vote": str(v), "majority_vote": str(maj),
                "majority_correct": bool(maj_correct), "is_focal": voter == 0,
                "vote_reason": str(info.get("reason", ""))[:500],
                "commitment": str(info.get("commitment", "")),
                "parse_fail": bool(info.get("parse_fail")),
                "delay_cause": info.get("delay_cause"),
                "jev_stub": (jev.get("stub") if isinstance(jev, dict) else None),
                "provider": settings.provider, "model": settings.model,
                "night_mode": night_mode,
            })
        for target, tval in (trust_all.get(0, {}) or {}).items():
            try:
                is_mafia = game.players[int(target)].role == "mafia"
                trust_rows.append({"run_tag": run_tag, "game_id": run_id, "day": day,
                                   "agent": 0, "target": str(target),
                                   "trust": float(tval), "target_is_mafia": bool(is_mafia),
                                   "provider": settings.provider, "model": settings.model})
            except Exception:
                continue
        # full per-day trace for audit
        try:
            with open(os.path.join(raw_dir, f"trace_{run_id}-day{day}.json"), "w", encoding="utf-8") as f:
                json.dump({"run_tag": run_tag, "run_id": run_id, "model": settings.model,
                           "trust": trust_all.get(0, {}), "trace": traces.get(0, {})}, f, default=str)
        except Exception:
            pass
        game._last_votes = {"votes": votes, "majority": str(maj), "majority_correct": maj_correct,
                            "trust": trust_all.get(0, {}), "trace": traces.get(0, {})}
        _log_progress(run_tag, run_id, game.seed, requested_seed, focal, gate,
                      night_mode, day, len(game.alive_ids()), game.winner)
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
    ap.add_argument("--night", type=str, default="llm", choices=["llm", "scripted"])
    ap.add_argument("--focal-role", type=str, default="random",
                    choices=["random", "villager", "mafia", "doctor", "detective"])
    ap.add_argument("--run-tag", type=str, default=None)
    ap.add_argument("--max-days", type=int, default=5,
                    help="day cap (lower only for pipeline smoke tests)")
    ap.add_argument("--no-canonical", action="store_true",
                    help="write only logs/runs/<run_tag>/ (smoke tests)")
    ap.add_argument("--out", type=str, default="logs/games.parquet")
    args = ap.parse_args()

    run_tag = args.run_tag or time.strftime("%Y%m%d-%H%M%S")
    os.environ["MAFIA_RUN_TAG"] = run_tag
    run_dir = os.path.join("logs", "runs", run_tag)
    os.makedirs(os.path.join(run_dir, "raw"), exist_ok=True)
    os.environ["MAFIA_RAW_DIR"] = os.path.join(run_dir, "raw")
    git_sha = _git_sha()
    _write_manifest(os.path.join(run_dir, "manifest.json"), args, run_tag, git_sha)

    focals = [f.strip() for f in args.agents.split(",") if f.strip()]
    rows = []
    for i in range(args.games):
        for focal in focals:
            mark = dict(COST_LOG)
            requested_seed = args.seed + i * 100
            g = play_one(seed=requested_seed, focal=focal, gate=args.gate,
                         focal_role=args.focal_role, night_mode=args.night,
                         run_tag=run_tag, run_dir=run_dir,
                         requested_seed=requested_seed, max_days=args.max_days)
            run_id = g._run_id
            dp = COST_LOG["prompt_tokens"] - mark["prompt_tokens"]
            dc = COST_LOG["completion_tokens"] - mark["completion_tokens"]
            dj = COST_LOG["json_failures"] - mark["json_failures"]
            lv = getattr(g, "_last_votes", {})
            fl = getattr(g, "_focal_last", {}) or {}
            trace = fl.get("trace", {}) if isinstance(fl, dict) else {}
            jev_info = trace.get("jev") if isinstance(trace, dict) else None
            row = {
                "run_tag": run_tag, "game_id": run_id,
                "seed": g.seed, "requested_seed": requested_seed,
                "focal": focal, "gate": args.gate, "night_mode": args.night,
                "provider": settings.provider, "model": settings.model,
                "jev_model": settings.jev_model, "git_sha": git_sha,
                "tau": settings.tau_delay, "evt_threshold": settings.evt_threshold,
                "winner": g.winner, "days": g.day,
                "focal_role": g.players[0].role,
                "majority_correct": lv.get("majority_correct"),
                "delay_cause": trace.get("delay_cause") if isinstance(trace, dict) else None,
                "parse_fail": trace.get("parse_fail") if isinstance(trace, dict) else None,
                "trust_json": json.dumps(fl.get("trust", {}) if isinstance(fl, dict) else {}),
                "trace_json": json.dumps(fl.get("trace", {}) if isinstance(fl, dict) else {}, default=str)[:4000],
                "prompt_tokens": dp, "completion_tokens": dc,
                "est_cost_inr": _est_cost_inr(dp, dc),
                "json_failures": dj,
                "jev_stub": jev_info.get("stub") if isinstance(jev_info, dict) else None,
            }
            rows.append(row)
            gdf = pd.DataFrame([row])
            _upsert(os.path.join(run_dir, "games.parquet"), gdf, ["run_tag", "game_id"])
            if not args.no_canonical:
                _upsert(args.out, gdf, ["run_tag", "game_id"])
            if getattr(g, "_vote_rows", None):
                vdf = pd.DataFrame(g._vote_rows)
                _upsert(os.path.join(run_dir, "votes.parquet"), vdf,
                        ["run_tag", "game_id", "day", "voter"])
                if not args.no_canonical:
                    _upsert("logs/votes.parquet", vdf,
                            ["run_tag", "game_id", "day", "voter"])
            if getattr(g, "_trust_rows", None):
                tdf = pd.DataFrame(g._trust_rows)
                _upsert(os.path.join(run_dir, "trust.parquet"), tdf,
                        ["run_tag", "game_id", "day", "agent", "target"])
                if not args.no_canonical:
                    _upsert("logs/trust.parquet", tdf,
                            ["run_tag", "game_id", "day", "agent", "target"])
            # save raw history (speaker mixes int pids + "engine" -> normalize for parquet)
            hdf = pd.DataFrame(g.history)
            for _c in ("speaker", "phase"):
                if _c in hdf.columns:
                    hdf[_c] = hdf[_c].astype(str)
            hdf.to_parquet(os.path.join(run_dir, "raw", f"history_{run_id}.parquet"), index=False)
            print(f"[{run_tag}] {run_id}: {g.winner} in {g.day} days "
                  f"role={g.players[0].role} json_failures={dj}")

    df = pd.DataFrame(rows)
    if args.no_canonical:
        print(f"\nSaved {len(rows)} rows to {run_dir}/games.parquet (canonical skipped)")
    else:
        print(f"\nSaved {len(rows)} rows to {args.out} and {run_dir}/games.parquet")
    if len(df):
        print(df[["focal", "winner", "focal_role"]].value_counts(dropna=False))
    print(f"Run bundle: {run_dir}")


if __name__ == "__main__":
    main()
