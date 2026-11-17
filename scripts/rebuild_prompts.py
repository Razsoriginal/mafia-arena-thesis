"""Rebuild production night/dm-reason prompts from calibration histories.

Step 0 (fidelity): rebuild prompts with the production builders
(src/mafia/prompts.py night_user/dm n_user + system prompts) from stored game
histories and compare proxy token counts against logged prompt_tokens.

Read-only imports from src/; no network; no ledger writes.
Usage: .venv/bin/python scripts/rebuild_prompts.py [--fidelity]
"""
import glob
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import tiktoken

from src.eval.run_arena import _shuffled, _private_note
from src.mafia import prompts as P
from src.mafia.engine import Game

RAW = "logs/runs/mvp-team-01-cal/raw"
JSON_SUFFIX = "\nReply with valid JSON only."  # appended by chat_json
NULL_VILLAGE = {"random_village", "majority_village"}

ENC = tiktoken.get_encoding("cl100k_base")


def proxy_tokens(system: str, user: str) -> int:
    """cl100k proxy for provider prompt tokens (message texts only)."""
    return len(ENC.encode(system, disallowed_special=())) + len(ENC.encode(user, disallowed_special=()))


def parse_task(task: str):
    """task-mvp-team-01-5000-dmn_village -> (seed, arm)."""
    m = re.match(r"task-(.+)-(\d+)-([a-z0-9_]+)$", task)
    if not m:
        raise ValueError(task)
    return int(m.group(2)), m.group(3)


def load_history(game_id: str):
    h = pd.read_parquet(os.path.join(RAW, f"history_{game_id}.parquet"))
    h = h.sort_values("turn").reset_index(drop=True)
    return h.to_dict("records")


def load_raw(task: str):
    rows = []
    with open(os.path.join(RAW, task, "llm_raw.jsonl"), encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def roles_of(seed: int):
    """Pid -> role. Team design uses Game(seed) directly (focal_role=random)."""
    g = Game(seed=seed)
    return {p.pid: p.role for p in g.players}


def deaths_in(prefix_rows) -> set:
    dead = set()
    for r in prefix_rows:
        m = re.search(r"Player (\d+) (was killed|lynched)", str(r.get("text", "")))
        if m:
            dead.add(int(m.group(1)))
    return dead


def night_prefix(all_rows, day: int):
    """History rows visible to night-day calls (before the night-day row)."""
    for i, r in enumerate(all_rows):
        if r.get("phase") == f"night-{day}":
            return all_rows[:i]
    return None  # game ended before this night


def day_prefix(all_rows, day: int):
    """History rows visible to day-day reason calls (through night-day row)."""
    for i, r in enumerate(all_rows):
        if r.get("phase") == f"night-{day}":
            return all_rows[:i + 1]
    return None


def history_text(prefix_rows, limit: int) -> str:
    g = Game(seed=0)
    g.history = [{"turn": r["turn"], "speaker": r["speaker"],
                  "text": r["text"], "phase": r["phase"]} for r in prefix_rows]
    return g.history_text(limit=limit)


def day_of_each_row(rows):
    """Day index per row. Phases are sequential (_pmap blocks per phase), so
    position disambiguates: pre-discussion rows (night/dm/tpn) precede their
    day's speak block; vote/probe rows follow it. s(i) = speak-block starts
    strictly before row i; night/dmn/tpn/speak -> day s(i), vote/probe ->
    day s(i)-1, repair -> day of nearest preceding non-repair row."""
    starts = set()
    prev = None
    for i, r in enumerate(rows):
        if r.get("purpose") == "speak" and prev != "speak":
            starts.add(i)
        prev = r.get("purpose")
    s_before = []
    n = 0
    for i in range(len(rows)):
        s_before.append(n)
        if i in starts:
            n += 1
    out = []
    for i, r in enumerate(rows):
        p = r.get("purpose")
        if p in ("vote", "probe"):
            out.append(s_before[i] - 1)
        elif p == "repair":
            j = i - 1
            while j >= 0 and rows[j].get("purpose") == "repair":
                j -= 1
            out.append(s_before[j] if j < 0 or rows[j].get("purpose") != "vote" else s_before[j] - 1)
            if j >= 0 and rows[j].get("purpose") == "probe":
                out[-1] = s_before[j] - 1
        else:
            out.append(s_before[i])
    return out


def check_target(game_rows, seed: int, roles: dict, day: int, row_days, det: int,
                 det_options: list):
    """Reconstruct the detective target used on `day` (success pick else the
    scripted fallback), mirroring _night_actions + night_action fallback."""
    # direct check success in this night's block
    for r, d in zip(game_rows, row_days):
        if d != day or r.get("purpose") != "night" or r.get("error") is not None:
            continue
        try:
            raw = json.loads(r.get("raw") or "")
        except Exception:
            continue
        if isinstance(raw, dict) and "check" in raw and str(raw["check"]) in {str(o) for o in det_options}:
            return int(raw["check"]), "success"
    # repair pass inside the same night block
    for r, d in zip(game_rows, row_days):
        if d != day or r.get("purpose") != "repair" or r.get("error") is not None:
            continue
        try:
            raw = json.loads(r.get("raw") or "")
        except Exception:
            continue
        if isinstance(raw, dict) and "check" in raw and str(raw["check"]) in {str(o) for o in det_options}:
            return int(raw["check"]), "repair"
    # fallback: min(det_options) when the call returned nothing usable
    if det_options:
        return min(det_options), "fallback"
    return None, "none"


def det_info_through(game_id, seed, roles, all_rows, game_rows, row_days, last_night: int):
    """det_info dict as the engine held it after night `last_night` resolved."""
    det_info = {}
    dets = [pid for pid, role in roles.items() if role == "detective"]
    det = dets[0] if dets else None
    if det is None:
        return det_info
    for d in range(last_night + 1):
        pre = night_prefix(all_rows, d)
        if pre is None:
            break
        alive = [p for p in range(7) if p not in deaths_in(pre)]
        if det not in alive:
            continue
        det_options = [a for a in alive if a != det]
        tgt, _ = check_target(game_rows, seed, roles, d, row_days, det, det_options)
        if tgt is not None:
            det_info.setdefault(det, []).append((tgt, roles[tgt]))
    return det_info


def rebuild_night(game_id: str):
    """{day: [(action, pid, role, system, user)]} mirroring _night_actions."""
    task = f"task-{game_id}"
    seed, arm = parse_task(task)
    roles = roles_of(seed)
    all_rows = load_history(game_id)
    game_rows = load_raw(task)
    row_days = day_of_each_row(game_rows)
    g = Game(seed=seed)
    out = {}
    day = 0
    while True:
        pre = night_prefix(all_rows, day)
        if pre is None:
            break
        alive = [p for p in range(7) if p not in deaths_in(pre)]
        mafia_pids = [p for p in alive if roles[p] == "mafia"]
        if not mafia_pids or len(alive) <= 2:
            break
        prompt_alive = _shuffled(alive, seed, day, 9)
        candidates = [a for a in alive if roles[a] != "mafia"]
        doctors = [p for p in alive if roles[p] == "doctor"]
        dets = [p for p in alive if roles[p] == "detective"]
        det = dets[0] if dets else None
        det_options = [a for a in alive if a != det] if det is not None else []
        det_info = det_info_through(game_id, seed, roles, all_rows, game_rows, row_days, day - 1)
        jobs = []
        if candidates:
            jobs.append(("kill", min(mafia_pids), "mafia",
                         _shuffled(candidates, seed, day, 1), True))
        if doctors:
            jobs.append(("save", doctors[0], "doctor",
                         _shuffled(alive, seed, day, 2), arm not in NULL_VILLAGE))
        if det is not None and det_options:
            jobs.append(("check", det, "detective",
                         _shuffled(det_options, seed, day, 3), arm not in NULL_VILLAGE))
        ctx_base = history_text(pre, 40)
        rebuilt = []
        for action, pid, role, options, is_llm in jobs:
            ctx = ctx_base + _private_note(g, pid, det_info)
            system = P.NIGHT_SYSTEM + JSON_SUFFIX
            user = P.night_user(pid, role, prompt_alive, ctx, action, options)
            rebuilt.append({"action": action, "pid": pid, "role": role,
                            "system": system, "user": user, "is_llm": is_llm,
                            "prefix_rows": len(pre)})
        out[day] = rebuilt
        day += 1
    return out, {"seed": seed, "arm": arm, "rows": game_rows, "row_days": row_days}


def rebuild_dmn(game_id: str):
    """{day: [(pid, role, system, user)]} mirroring the play_one reason block."""
    task = f"task-{game_id}"
    seed, arm = parse_task(task)
    if arm != "dmn_village":
        return {}, {"seed": seed, "arm": arm}
    roles = roles_of(seed)
    all_rows = load_history(game_id)
    game_rows = load_raw(task)
    row_days = day_of_each_row(game_rows)
    g = Game(seed=seed)
    out = {}
    day = 0
    while True:
        pre = day_prefix(all_rows, day)
        if pre is None:
            break
        alive = [p for p in range(7) if p not in deaths_in(pre)]
        if len(alive) <= 2:
            break
        det_info = det_info_through(game_id, seed, roles, all_rows, game_rows, row_days, day)
        shared = history_text(pre, 60)
        rebuilt = []
        for pid in alive:
            if roles[pid] == "mafia":
                continue
            role = roles[pid]
            view = shared + _private_note(g, pid, det_info)
            system = P.DMN_SYSTEM + JSON_SUFFIX
            user = P.dmn_user(pid, role, view, alive, exformation=True)
            rebuilt.append({"pid": pid, "role": role, "system": system,
                            "user": user, "prefix_rows": len(pre)})
        out[day] = rebuilt
        day += 1
    return out, {"seed": seed, "arm": arm, "rows": game_rows, "row_days": row_days}


def _success_rows_night0(game_id: str):
    """Successful night-0 rows keyed by action (from raw JSON key)."""
    task = f"task-{game_id}"
    rows, days = load_raw(task), day_of_each_row(load_raw(task))
    found = {}
    for r, d in zip(rows, days):
        if d != 0 or r.get("purpose") != "night" or r.get("error") is not None:
            continue
        try:
            raw = json.loads(r.get("raw") or "")
        except Exception:
            continue
        for a in ("kill", "save", "check"):
            if isinstance(raw, dict) and a in raw and a not in found:
                found[a] = r
    return found


def fidelity():
    print("Step 0 fidelity: rebuilt proxy tokens vs logged prompt_tokens")
    print("(proxy = cl100k over system+user texts; provider overhead fitted)\n")
    checks = []
    games = ["mvp-team-01-5000-dmn_village", "mvp-team-01-5200-dmn_village",
             "mvp-team-01-5600-dmn_village"]
    for gid in games:
        nights, _ = rebuild_night(gid)
        ok = _success_rows_night0(gid)
        for action, r in sorted(ok.items()):
            rb = [b for b in nights[0] if b["action"] == action][0]
            checks.append({"ctx": f"{gid} night0/{action}", "pid": rb["pid"],
                           "logged": r["prompt_tokens"], "attempt": r["attempt"],
                           "proxy": proxy_tokens(rb["system"], rb["user"])})
    # day-0 dmn rows: pid unknown from raw; match nearest candidate
    for gid in games:
        dmns, meta = rebuild_dmn(gid)
        rows, days = meta["rows"], meta["row_days"]
        cands = dmns[0]
        prox = [proxy_tokens(c["system"], c["user"]) for c in cands]
        for r, d in zip(rows, days):
            if d != 0 or r.get("purpose") != "dmn_reason" or r.get("error") is not None:
                continue
            checks.append({"ctx": f"{gid} dmn0/row", "pid": "?",
                           "logged": r["prompt_tokens"], "attempt": r["attempt"],
                           "proxy": prox[0], "prox_all": prox})
    # late-game nights (longest history): successful rows, any game
    late = []
    for task in sorted(glob.glob(os.path.join(RAW, "task-*dmn_village"))):
        gid = os.path.basename(task)[len("task-"):]
        nights, _ = rebuild_night(gid)
        if not nights:
            continue
        last = max(nights)
        if nights[last][0]["prefix_rows"] >= 30:
            late.append((gid, last, nights[last][0]["prefix_rows"]))
    late.sort(key=lambda t: -t[2])
    for gid, day, _ in late[:2]:
        nights, meta = rebuild_night(gid)
        rows, days = meta["rows"], meta["row_days"]
        for r, d in zip(rows, days):
            if d != day or r.get("purpose") != "night" or r.get("error") is not None:
                continue
            try:
                raw = json.loads(r.get("raw") or "")
            except Exception:
                continue
            acts = [a for a in ("kill", "save", "check") if isinstance(raw, dict) and a in raw]
            if not acts:
                continue
            rb = [b for b in nights[day] if b["action"] == acts[0]][0]
            checks.append({"ctx": f"{gid} night{day}/{acts[0]}", "pid": rb["pid"],
                           "logged": r["prompt_tokens"], "attempt": r["attempt"],
                           "proxy": proxy_tokens(rb["system"], rb["user"])})
            break
    night = [c for c in checks if "night" in c["ctx"]]
    ovh = statistics.median(c["logged"] - c["proxy"] for c in night)
    print(f"fitted provider/chat overhead: {ovh:.0f} tokens "
          f"(median over unambiguous night matches, n={len(night)})\n")
    # re-match dmn rows overhead-aware (pid is not logged; candidates differ
    # by role/private-note, e.g. detective +26 for the night-0 result note)
    for c in checks:
        if "dmn0" in c["ctx"]:
            c["proxy"] = min(c["prox_all"], key=lambda p: abs(p + ovh - c["logged"]))
    worst = 0.0
    for c in checks:
        resid = abs(c["logged"] - (c["proxy"] + ovh)) / c["logged"] * 100
        worst = max(worst, resid)
        flag = "OK " if resid <= 5 else "FAIL"
        print(f"{flag} {c['ctx']:45s} pid={c['pid']} att={c['attempt']} "
              f"logged={c['logged']:5d} proxy={c['proxy']:5d} err={resid:4.1f}%")
    xs = [c["proxy"] for c in checks]
    ys = [c["logged"] for c in checks]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    print(f"\nsupplementary OLS fit logged = {slope:.4f} * proxy + {my - slope * mx:.1f}")
    print(f"worst residual: {worst:.1f}% (tolerance 5%) -> "
          f"{'PASS' if worst <= 5 else 'FAIL'}")
    return worst <= 5


if __name__ == "__main__":
    ok = fidelity()
    sys.exit(0 if ok else 1)
