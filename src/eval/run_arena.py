"""Arena runner: python -m src.eval.run_arena --games 5 --agents dmn_tpn,cot --seed 0

Backbone is AiCredits (src/config.py). EVT DELAY source: --gate llm | jev.
Night phase: --night llm (default, LLM choice with scripted fallback) or
scripted (legacy deterministic heuristics).
Parallelism: --workers N (default 4) runs N games in separate processes.
Each worker writes only its own raw files; the parent owns every parquet
write, so parallel runs cannot corrupt the canonical tables.

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
import re
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone

import pandas as pd

from src.agents.baselines import CotAgent, CotX3Agent, ReactAgent, ConstitutionAgent
from src.agents.dmn_tpn_agent import DmnTpnAgent
from src.agents.null_agents import MajorityFollowerAgent, RandomVoterAgent
from src.config import settings
from src.llm_client import COST_LOG, BillingExhausted
from src.llm_client import call_threads as _call_threads, pmap as _pmap
from src.mafia.engine import Game

AGENTS = {"cot": CotAgent, "react": ReactAgent, "constitution": ConstitutionAgent,
          "dmn_tpn": DmnTpnAgent, "cotx3": CotX3Agent,
          "random_voter": RandomVoterAgent, "majority_follower": MajorityFollowerAgent}

TEAM_ARMS = {
    "dmn_village": {"village": "dmn_tpn", "mafia": "cot"},
    "cot_village": {"village": "cot", "mafia": "cot"},
    "cotx3_village": {"village": "cotx3", "mafia": "cot"},
    "random_village": {"village": "random_voter", "mafia": "cot"},
    "majority_village": {"village": "majority_follower", "mafia": "cot"},
}

# AiCredits catalog rates (USD/token) + INR/USD for meta/muse-spark-1.3-contributor.
# Billing adds a 10% markup on the listed token rates (verified against usage.cost).
_MUSE_IN, _MUSE_OUT, _INR_PER_USD = 1e-07, 2e-07, 94.834253
_BILLING_MARKUP = 1.10
_TURN_ID = re.compile(r"\bt(\d+)\b", re.IGNORECASE)


def _est_cost_inr(prompt_tokens: int, completion_tokens: int) -> float:
    return round((prompt_tokens * _MUSE_IN + completion_tokens * _MUSE_OUT)
                 * _INR_PER_USD * _BILLING_MARKUP, 4)


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


PREREG_MODEL = "meta/muse-spark-1.3-contributor"
PREREG_TAU = 0.35
PREREG_MAX_TOKENS = 2500
PREREG_TEMP_DIALOGUE = 0.3
PREREG_TEMP_JSON = 0.0
PREREG_VOTE_TEMPERATURE = 0.7
PREREG_PROVIDER = "aicredits"
PREREG_BASE_URL = "https://aicredits.in/v1"
PREREG_EVT_THRESHOLD = 0.6
PREREG_NIGHT = "llm"
PREREG_MAX_DAYS = 5
PREREG_BUDGET_CAP = 2000.0  # Pre-reg v2 SS9: hard cap, no locked reserve
PRIMARY_ARMS = ("dmn_village", "cot_village", "cotx3_village")
NULL_ARMS = ("random_village", "majority_village")
CONFIRMATORY_SEED_BASE = 5000
CALIBRATION_TRIOS = 20


def _prompt_hash() -> str:
    import hashlib
    p = os.path.join(os.path.dirname(__file__), "..", "mafia", "prompts.py")
    with open(os.path.normpath(p), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _runpath_files():
    """Files whose change alters what a game does (freeze identity, G10).

    Recursive under src/agents and src/mafia so a new submodule is
    hashed. Analysis-only files (evaluate/stats/judge/dashboard/tests)
    are excluded so analysis commits do not force a re-freeze.
    """
    root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    rels = []
    for sub in ("agents", "mafia"):
        d = os.path.join(root, sub)
        for dirpath, _dirs, files in os.walk(d):
            for name in sorted(files):
                if name.endswith(".py"):
                    rels.append(os.path.relpath(os.path.join(dirpath, name), root))
    rels += ["llm_client.py", "config.py", os.path.join("eval", "run_arena.py")]
    return [os.path.join(root, r) for r in sorted(rels)]


def _runpath_relpaths():
    root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    return [os.path.relpath(p, os.path.join(root, "..")).replace(os.sep, "/")
            for p in _runpath_files()]


def _git_status_summary() -> dict:
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain"], text=True)
        lines = [x for x in out.splitlines() if x.strip()]
        return {"n_dirty": len(lines), "entries": lines[:50]}
    except Exception as e:
        return {"n_dirty": None, "entries": [], "error": str(e)}


def _dirty_runpath_files() -> list:
    """Dirty files inside the freeze scope only (G6).

    Run artifacts under logs/ never block; an edit to a run-path file
    or to the pre-registration does.
    """
    scope = set(_runpath_relpaths()) | {"docs/PREREGISTRATION.md"}
    dirty = []
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain"], text=True)
    except Exception:
        return dirty
    for line in out.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip().split(" -> ")[-1]
        if path in scope:
            dirty.append(path)
    return dirty


def _freeze_tag_ancestor(tag: str) -> bool:
    if not tag:
        return False
    try:
        r = subprocess.run(["git", "merge-base", "--is-ancestor", tag, "HEAD"])
        return r.returncode == 0
    except Exception:
        return False


def _runpath_sha256() -> str:
    import hashlib
    h = hashlib.sha256()
    root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    for path in _runpath_files():
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        h.update(rel.encode())
        h.update(b"\0")
        try:
            with open(path, "rb") as f:
                h.update(f.read())
        except Exception:
            h.update(b"<missing>")
        h.update(b"\0")
    return h.hexdigest()


def _prereg_expected():
    path = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "PREREGISTRATION.md")
    path = os.path.normpath(path)
    out = {}
    if not os.path.exists(path):
        return out
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return out
    out["freeze"] = _parse_freeze_block(text)
    out["has_pending"] = not out["freeze"]["valid"]
    fh = out["freeze"]["fields"]
    if fh.get("prompts_sha256"):
        out["prompt_hash"] = fh["prompts_sha256"]
    if fh.get("runpath_sha256"):
        out["runpath_sha256"] = fh["runpath_sha256"]
    if fh.get("freeze_git_sha"):
        out["git_sha"] = fh["freeze_git_sha"]
    out["raw_text"] = text
    return out


def _parse_freeze_block(text: str) -> dict:
    """Machine-readable freeze block (G9). No substring PENDING check.

    Expected, between <!-- freeze and --> lines, one key per line:
    prompts_sha256 / runpath_sha256 (64 hex), freeze_git_sha (hex),
    freeze_tag (non-empty). Blank, missing or malformed all refuse.
    """
    import re as _re
    fields, errors = {}, []
    m = _re.search(r"<!--\s*freeze(.*?)-->", text or "", _re.S)
    body = m.group(1) if m else ""
    for line in body.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip()
    def need(key, pat, label):
        v = fields.get(key, "")
        if not v:
            errors.append(f"freeze {label} missing/blank")
        elif not _re.fullmatch(pat, v):
            errors.append(f"freeze {label} malformed")
    need("prompts_sha256", r"[0-9a-f]{64}", "prompts_sha256")
    need("runpath_sha256", r"[0-9a-f]{64}", "runpath_sha256")
    need("freeze_git_sha", r"[0-9a-f]{7,40}", "freeze_git_sha")
    tag = fields.get("freeze_tag", "")
    if not tag or tag.upper() == "PENDING":
        errors.append("freeze freeze_tag missing/blank")
    return {"fields": fields, "valid": not errors, "errors": errors}


def _assert_confirmatory(args):
    if not getattr(args, "confirmatory", False):
        return
    errors = []
    if getattr(args, "design", None) != "team":
        errors.append("confirmatory requires --design team")
    if getattr(args, "gate", None) != "llm":
        errors.append("confirmatory requires --gate llm")
    if getattr(args, "night", PREREG_NIGHT) != PREREG_NIGHT:
        errors.append(f"confirmatory requires --night {PREREG_NIGHT} (F22)")
    if int(getattr(args, "max_days", PREREG_MAX_DAYS) or 0) != PREREG_MAX_DAYS:
        errors.append(f"confirmatory requires --max-days {PREREG_MAX_DAYS} (F21)")
    if getattr(args, "ablate", ""):
        errors.append("confirmatory requires empty --ablate")
    if getattr(args, "tau", None) is None or float(args.tau) != PREREG_TAU:
        errors.append(f"confirmatory requires --tau {PREREG_TAU} passed explicitly")
    # arm set: primary trio required, nulls only as a complete pair (F23)
    arms_raw = getattr(args, "arms", "") or ""
    arm_set = {a.strip() for a in str(arms_raw).split(",") if a.strip()}
    if not set(PRIMARY_ARMS).issubset(arm_set):
        errors.append(f"confirmatory requires primary arms {list(PRIMARY_ARMS)} (F23)")
    extra = arm_set - set(PRIMARY_ARMS) - set(NULL_ARMS)
    if extra:
        errors.append(f"confirmatory arms include unallowed {sorted(extra)} (F23)")
    null_present = arm_set & set(NULL_ARMS)
    if null_present and null_present != set(NULL_ARMS):
        errors.append("confirmatory null arms must be both or neither (F23)")
    # seed series (F19/F20): base 5000, step 100, via --start-trio offset
    seed_val = getattr(args, "seed", None)
    if seed_val is None or int(seed_val) != CONFIRMATORY_SEED_BASE:
        errors.append(f"confirmatory requires --seed {CONFIRMATORY_SEED_BASE} series (F20)")
    # budget cap at/below usable budget (F26)
    cap = getattr(args, "budget_cap", None)
    if cap is None or float(cap) > PREREG_BUDGET_CAP:
        errors.append(f"confirmatory requires --budget-cap <= {PREREG_BUDGET_CAP} (F26)")
    # planned trios 120-184 (F24 is per-campaign, not per-invocation)
    planned = getattr(args, "planned_trios", None)
    if planned is not None and not (120 <= int(planned) <= 184):
        errors.append("confirmatory --planned-trios must be 120-184 (Tier 2)")
    if not getattr(args, "campaign", None):
        errors.append("confirmatory requires --campaign (F2)")
    if settings.provider != PREREG_PROVIDER:
        errors.append(f"provider {settings.provider} != pre-registered {PREREG_PROVIDER} (F7)")
    if settings.base_url != PREREG_BASE_URL:
        errors.append(f"base_url {settings.base_url} != pre-registered {PREREG_BASE_URL} (F7)")
    if settings.model != PREREG_MODEL:
        errors.append(f"model {settings.model} != pre-registered {PREREG_MODEL}")
    if settings.max_tokens != PREREG_MAX_TOKENS:
        errors.append(f"max_tokens {settings.max_tokens} != {PREREG_MAX_TOKENS}")
    if settings.temp_dialogue != PREREG_TEMP_DIALOGUE:
        errors.append(f"temp_dialogue {settings.temp_dialogue} != {PREREG_TEMP_DIALOGUE}")
    if settings.temp_json != PREREG_TEMP_JSON:
        errors.append(f"temp_json {settings.temp_json} != {PREREG_TEMP_JSON}")
    if settings.vote_temperature != PREREG_VOTE_TEMPERATURE:
        errors.append(f"vote_temperature {settings.vote_temperature} != {PREREG_VOTE_TEMPERATURE}")
    if float(settings.evt_threshold) != PREREG_EVT_THRESHOLD:
        errors.append(f"EVT_THRESHOLD {settings.evt_threshold} != {PREREG_EVT_THRESHOLD} (F25)")
    # Scoped dirty check (G6): logs/ artifacts never block; run-path
    # or pre-registration edits do. Freeze identity is the tag ancestor
    # plus runpath hash, not HEAD equality.
    if getattr(args, "_skip_dirty_check", False) is not True:
        dirty_scope = _dirty_runpath_files()
        if dirty_scope:
            errors.append(f"confirmatory requires clean run-path files: {dirty_scope} (G6)")
    expected = _prereg_expected()
    freeze = expected.get("freeze") or {}
    if not freeze.get("valid"):
        errors.append("confirmatory refused: freeze block invalid: "
                      + "; ".join(freeze.get("errors", ["missing"])) + " (G9)")
    else:
        fields = freeze["fields"]
        if _prompt_hash() != fields.get("prompts_sha256"):
            errors.append("prompt hash differs from pre-registration")
        if _runpath_sha256() != fields.get("runpath_sha256"):
            errors.append("runpath hash differs from pre-registration freeze (G6)")
        if not _freeze_tag_ancestor(fields.get("freeze_tag", "")):
            errors.append("freeze tag is not an ancestor of HEAD (G6)")
    if errors:
        raise SystemExit("Confirmatory pre-registration check failed: " + "; ".join(errors))


def _write_manifest(path: str, args, run_tag: str, git_sha: str):
    manifest = {
        "run_tag": run_tag,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha,
        "args": vars(args),
        "design": getattr(args, "design", "focal"),
        "arm_map": TEAM_ARMS if getattr(args, "design", "focal") == "team" else {},
        "arms": getattr(args, "arms", None),
        "probe_enabled": getattr(args, "design", "focal") == "team",
        "prompt_hash": _prompt_hash(),
        "prompts_sha256": _prompt_hash(),
        "runpath_sha256": _runpath_sha256(),
        "campaign": getattr(args, "campaign", None),
        "planned_trios": getattr(args, "planned_trios", None),
        "start_trio": getattr(args, "start_trio", 0),
        "trios": getattr(args, "trios", None),
        "spend_ledger": _ledger_path(args),
        "budget_cap_inr": getattr(args, "budget_cap", PREREG_BUDGET_CAP),
        "planned_trio_cost_inr": getattr(args, "planned_trio_cost", 8.13),
        "effective_tau": getattr(args, "tau", None) if getattr(args, "tau", None) is not None else settings.tau_delay,
        "git_status_summary": _git_status_summary(),
        "dirty_runpath": _dirty_runpath_files(),
        "calibration_trios": getattr(args, "calibration_trios", 20),
        "trio_window": getattr(args, "trio_window", 1),
        "call_threads": int(os.getenv("MAFIA_CALL_THREADS", "1") or 1),
        "confirmatory": bool(getattr(args, "confirmatory", False)),
        "llm": {
            "provider": settings.provider,
            "base_url": settings.base_url,
            "model": settings.model,
            "max_tokens": settings.max_tokens,
            "temperature_dialogue": settings.temp_dialogue,
            "temperature_json": settings.temp_json,
            "vote_temperature": settings.vote_temperature,
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


def _log_progress(run_tag, run_id, seed, requested_seed, focal, focal_pid,
                  gate, night_mode, day, alive, winner):
    os.makedirs("logs", exist_ok=True)
    with open("logs/progress.jsonl", "a") as f:
        f.write(json.dumps({
            "ts": time.time(), "run_tag": run_tag, "run_id": run_id,
            "seed": seed, "requested_seed": requested_seed,
            "focal": focal, "focal_pid": focal_pid,
            "gate": gate, "night_mode": night_mode,
            "provider": settings.provider, "model": settings.model,
            "day": day, "alive": alive, "winner": winner,
        }) + "\n")


def _focal_pid_for_seed(seed) -> int:
    """Deterministic focal seat, so the focal agent is not always Player 0.

    Seat 0 was being killed first in most games, which destroyed the trust
    sample. Rotating the seat removes that structural bias.
    """
    return random.Random(seed ^ 0x5EED).randrange(7)


def _make_game(seed, focal_role="random", focal_pid=None):
    """Role-balanced game: re-seed (bounded) until focal_pid has focal_role."""
    if focal_pid is None:
        focal_pid = _focal_pid_for_seed(seed)
    if focal_role == "random":
        return Game(seed=seed), seed, focal_pid
    for k in range(50):
        s = seed + k * 1000
        g = Game(seed=s)
        if g.players[focal_pid].role == focal_role:
            return g, s, focal_pid
    return Game(seed=seed), seed, focal_pid  # fallback: record actual role


def _private_note(game, pid, det_info):
    """Per-agent private info appended to that agent's view only (never shared history)."""
    role = game.players[pid].role
    notes = []
    if role == "mafia":
        partners = [p.pid for p in game.players if p.role == "mafia" and p.pid != pid]
        notes.append(f"You are MAFIA. Your partners: {partners}. Coordinate subtly, do not expose each other.")
    if role == "detective" and pid in det_info:
        results = det_info[pid]
        if isinstance(results, tuple):  # legacy single-result form
            results = [results]
        for chk, chk_role in results:
            if chk is not None:
                notes.append(f"Private detective result: Player {chk} is {chk_role}. Do not reveal it unless you choose to.")
    if not notes:
        return ""
    return "\n[private: only you see this]\n" + "\n".join(notes)


def _record_detective_result(det_info, det_pid, result):
    """Append one night's check; the detective keeps every result (P0-E3)."""
    prev = det_info.get(det_pid, [])
    if isinstance(prev, tuple):
        prev = [prev]
    det_info[det_pid] = list(prev) + [tuple(result)]


def _shuffled(items, seed, day, salt):
    """Stable shuffle for prompt options; avoids first-option bias."""
    out = list(items)
    random.Random(seed * 1000 + day * 37 + salt).shuffle(out)
    return out


def _night_actions(game, agents, seed, day, night_mode, det_info):
    """Return (kill, save, check). LLM choices fall back to scripted heuristics."""
    alive = game.alive_ids()
    mafia_pids = [p.pid for p in game.alive() if p.role == "mafia"]
    kill = save = check = None
    if not mafia_pids or len(alive) <= 2:
        return None, None, None

    prompt_alive = _shuffled(alive, seed, day, 9)
    candidates = [a for a in alive if game.players[a].role != "mafia"]
    doctors = [p.pid for p in game.alive() if p.role == "doctor"]
    detectives = [p.pid for p in game.alive() if p.role == "detective"]
    det = detectives[0] if detectives else None
    det_options = [a for a in alive if a != det] if det is not None else []
    # The three night choices read the same pre-night state and never see
    # each other, so they run concurrently (P0-S1); fallbacks unchanged.
    jobs = []
    if night_mode == "llm":
        if candidates:
            killer = min(mafia_pids)
            jobs.append(("kill", killer, "mafia", _shuffled(candidates, seed, day, 1)))
        if doctors:
            jobs.append(("save", doctors[0], "doctor", _shuffled(alive, seed, day, 2)))
        if det is not None and det_options:
            jobs.append(("check", det, "detective", _shuffled(det_options, seed, day, 3)))

    def _ask(job):
        action, pid, role, options = job
        ctx = game.history_text(limit=40) + _private_note(game, pid, det_info)
        return action, agents[pid].night_action(role, ctx, prompt_alive, options, action)

    picks = dict(_pmap(_ask, jobs))
    if picks.get("kill") is not None:
        kill = int(picks["kill"])
    if kill is None and candidates:
        kill = random.Random(seed * 1000 + day).choice(candidates)
    if doctors:
        if picks.get("save") is not None:
            save = int(picks["save"])
        if save is None:
            save = doctors[0]
    if det is not None:
        if picks.get("check") is not None:
            check = int(picks["check"])
        if check is None and det_options:
            check = min(det_options)
    return kill, save, check


def _plurality_info(votes):
    """Return (plurality_target, tied) excluding no-lynch votes."""
    from collections import Counter
    c = Counter([str(v) for v in votes.values() if str(v) != "no-lynch"])
    if not c:
        return "no-lynch", False
    ranked = c.most_common()
    tied = len(ranked) > 1 and ranked[0][1] == ranked[1][1]
    return str(ranked[0][0]), bool(tied)


def _verified_suspects(trace):
    """Targets TPN actually verified. DMN hypotheses alone are NOT verified.

    The old fallback marked DMN-only suspects verified=True even though
    their trust value is the base-rate prior, which let prior-filler rows
    enter decision[verified-only] (F10). Unverified targets now stay
    verified=False and are reported as prior-filler.
    """
    trace = trace if isinstance(trace, dict) else {}
    out = set()
    tpn = trace.get("tpn") or {}
    for v in tpn.get("verified", []) or []:
        try:
            out.add(str(v["suspect"]))
        except Exception:
            continue
    return out


def _build_agents(game, focal_pid, focal="dmn_tpn", gate="llm", ablate=None,
                  design="focal", arm=None):
    agents = {}
    for p in game.players:
        if design == "team":
            if arm not in TEAM_ARMS:
                raise ValueError(f"unknown team arm: {arm}")
            key = TEAM_ARMS[arm]["mafia" if p.role == "mafia" else "village"]
            cls = AGENTS[key]
        else:
            cls = AGENTS[focal] if p.pid == focal_pid else AGENTS["cot"]
        ag = cls(pid=p.pid, ablate=ablate) if cls is DmnTpnAgent else cls(pid=p.pid)
        if isinstance(ag, DmnTpnAgent):
            ag.backend = gate
        agents[p.pid] = ag
    return agents


def play_one(seed, focal="dmn_tpn", gate="llm", run_id=None, focal_role="random",
             night_mode="llm", run_tag="", run_dir="logs/runs/tmp", requested_seed=None,
             max_days=5, ablate=None, design="focal", arm=None, campaign=None):
    if design == "team":
        focal_role = "random"
    game, _, focal_pid = _make_game(seed, focal_role)
    run_id = run_id or f"{game.seed}-{arm or focal}"
    requested_seed = seed if requested_seed is None else requested_seed
    game._run_id = run_id
    campaign = campaign or run_tag
    game._focal_pid = focal_pid
    game._design = design
    game._arm = arm
    raw_dir = os.path.join(run_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    agents = _build_agents(game, focal_pid, focal=focal, gate=gate,
                           ablate=ablate, design=design, arm=arm)
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
                _record_detective_result(det_info, det[0], res["detective_info"])
            if res["killed"] is not None:
                game.add("engine", f"Night: Player {res['killed']} was killed.", f"night-{day}")
            else:
                game.add("engine", "Night: No one died (saved).", f"night-{day}")
        # A night kill that reaches parity ends the game immediately (P0-E1):
        # standard Mafia rules, and no wasted day of calls or rows.
        if game.check_over():
            break
        # reason BEFORE discussion: the DMN/TPN plan (cached per day) informs speech
        alive = game.alive_ids()
        alive_roles = {p.pid: p.role for p in game.alive()}
        shared, facts = game.history_text(), game.facts_text()
        trust_all, traces = {}, {}
        alive_players = list(game.alive())
        # Per-seat DMN/TPN reasoning reads the same pre-discussion snapshot
        # and never sees another seat's result: concurrent (P0-S1).
        reasoners = [p for p in alive_players if isinstance(agents[p.pid], DmnTpnAgent)]

        def _reason(p):
            return agents[p.pid].reason(
                p.role, shared + _private_note(game, p.pid, det_info),
                facts, alive, prev_majority, alive_roles)

        reasoned = dict(zip([p.pid for p in reasoners], _pmap(_reason, reasoners)))
        for p in alive_players:
            if p.pid in reasoned:
                trust, trace, delay = reasoned[p.pid]
                trust_all[p.pid] = trust
                traces[p.pid] = trace
                if p.pid == focal_pid:
                    # keep the focal agent's last reasoning even if it dies later
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
        # Citation validity is judged against turns that existed BEFORE
        # any vote line or lynch result from this day was appended (F11).
        valid_turns_at_vote = {h["turn"] for h in game.history}
        voters = list(game.alive())
        alive_ids_at_vote = game.alive_ids()

        # Every vote reads the same pre-vote snapshot `full`; vote lines are
        # appended afterwards in seat order, so votes are independent and
        # run concurrently (P0-S1) with an unchanged history.
        def _vote(p):
            ag = agents[p.pid]
            view = full + _private_note(game, p.pid, det_info)
            if isinstance(ag, DmnTpnAgent):
                return ag.vote(p.role, view, trust_all[p.pid], traces[p.pid])
            return ag.vote(p.role, view, {}, prev_majority=prev_majority,
                           seed=game.seed, day=day, alive=alive_ids_at_vote)

        for p, (v, info) in zip(voters, _pmap(_vote, voters)):
            votes[p.pid] = v
            infos[p.pid] = info if isinstance(info, dict) else {}
            game.add(p.pid, f"votes {v} ({infos[p.pid].get('reason','')[:120]})", f"vote-{day}")
        # shadow probe (team only): post-vote, pre-vote snapshot, no feedback
        probe_trust = {}
        if design == "team":
            probed = [p for p in list(game.alive())
                      if game.players[p.pid].role != "mafia"
                      and not isinstance(agents[p.pid], (RandomVoterAgent, MajorityFollowerAgent))]

            def _probe(p):
                view = full + _private_note(game, p.pid, det_info)
                return agents[p.pid].elicit_trust_probe(p.role, view, alive)

            for p, res in zip(probed, _pmap(_probe, probed)):
                probe_trust[p.pid] = res
        # record majority for metrics
        maj, plurality_tied = _plurality_info(votes)
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
        # v2 action-boundary fields (Pre-reg v2 SS12.22-12.24): the engine's
        # lynch result for the day and the true role of each vote target.
        lynched_str = str(lynched) if lynched is not None else None
        lynched_is_mafia = (game.players[int(lynched)].role == "mafia") if lynched is not None else None

        def _target_is_mafia(v):
            try:
                pid = int(str(v))
            except Exception:
                return None
            if 0 <= pid < len(game.players):
                return game.players[pid].role == "mafia"
            return None

        # per-day metric rows (ALL voters, not just focal)
        for voter, v in votes.items():
            info = infos.get(voter, {})
            jev = info.get("jev") if isinstance(info, dict) else None
            reason = str(info.get("reason", ""))
            cited_turns = sorted({int(m) for m in _TURN_ID.findall(reason)} & valid_turns_at_vote)
            voter_role = game.players[voter].role
            vote_rows.append({
                "run_tag": run_tag, "campaign": campaign, "game_id": run_id, "day": day, "voter": voter,
                "vote": str(v), "majority_vote": str(maj),
                "majority_correct": bool(maj_correct), "is_focal": voter == focal_pid,
                "focal_pid": focal_pid,
                "vote_reason": reason[:500],
                "cited_turns": cited_turns,
                "citation_valid": bool(cited_turns),
                "commitment": str(info.get("commitment", "")),
                "parse_fail": bool(info.get("parse_fail")),
                "delay_cause": info.get("delay_cause"),
                "jev_stub": (jev.get("stub") if isinstance(jev, dict) else None),
                "provider": settings.provider, "model": settings.model,
                "night_mode": night_mode,
                "design": design, "arm": arm or focal,
                "voter_role": voter_role, "is_village": voter_role != "mafia",
                "plurality_tied": bool(plurality_tied),
                "lynched": lynched_str, "lynched_is_mafia": lynched_is_mafia,
                "vote_target_is_mafia": _target_is_mafia(v),
                "samples": info.get("samples"), "sample_parse_fails": info.get("sample_parse_fails"),
                "n_sample_parse_fails": info.get("n_sample_parse_fails"),
            })
        _arm_label = arm or focal
        if design == "team":
            decision_pids = [pid for pid, ag in agents.items()
                             if isinstance(ag, DmnTpnAgent)
                             and game.players[pid].role != "mafia" and pid in trust_all]
        else:
            decision_pids = [focal_pid] if trust_all.get(focal_pid) else []
        for _pid in decision_pids:
            _verified = _verified_suspects(traces.get(_pid, {}))
            for target, tval in (trust_all.get(_pid, {}) or {}).items():
                try:
                    is_mafia = game.players[int(target)].role == "mafia"
                    trust_rows.append({"run_tag": run_tag, "campaign": campaign, "game_id": run_id, "day": day,
                                       "agent": _pid, "focal_pid": focal_pid,
                                       "target": str(target),
                                       "trust": float(tval), "target_is_mafia": bool(is_mafia),
                                       "provider": settings.provider, "model": settings.model,
                                       "design": design, "arm": _arm_label,
                                       "voter_role": game.players[_pid].role,
                                       "probe": False, "trust_source": "decision",
                                       "verified": str(target) in _verified,
                                       "elicited": False,
                                       "parse_fail": bool((traces.get(_pid, {}) or {}).get("parse_fail"))})
                except Exception:
                    continue
        for _pid, (_ptrust, _pinfo) in probe_trust.items():
            # One row per expected target (alive non-self at that seat-day)
            # so probe missingness is computable by arm (F33). Missing or
            # unparseable targets get trust=NaN + parse_fail=True (F34:
            # probe rows are elicited, never TPN-verified).
            _pinfo = _pinfo if isinstance(_pinfo, dict) else {}
            _pfail = bool(_pinfo.get("parse_fail"))
            _expected = [str(a) for a in alive if str(a) != str(_pid)]
            for target in _expected:
                try:
                    is_mafia = game.players[int(target)].role == "mafia"
                    if target in (_ptrust or {}):
                        trust_rows.append({"run_tag": run_tag, "campaign": campaign, "game_id": run_id, "day": day,
                                           "agent": _pid, "focal_pid": focal_pid,
                                           "target": str(target),
                                           "trust": float(_ptrust[target]),
                                           "target_is_mafia": bool(is_mafia),
                                           "provider": settings.provider, "model": settings.model,
                                           "design": design, "arm": _arm_label,
                                           "voter_role": game.players[_pid].role,
                                           "probe": True, "trust_source": "probe",
                                           "verified": False, "elicited": True,
                                           "parse_fail": False})
                    else:
                        trust_rows.append({"run_tag": run_tag, "campaign": campaign, "game_id": run_id, "day": day,
                                           "agent": _pid, "focal_pid": focal_pid,
                                           "target": str(target),
                                           "trust": float("nan"),
                                           "target_is_mafia": bool(is_mafia),
                                           "provider": settings.provider, "model": settings.model,
                                           "design": design, "arm": _arm_label,
                                           "voter_role": game.players[_pid].role,
                                           "probe": True, "trust_source": "probe",
                                           "verified": False, "elicited": True,
                                           "parse_fail": True})
                except Exception:
                    continue
        # full per-day trace for audit
        try:
            with open(os.path.join(raw_dir, f"trace_{run_id}-day{day}.json"), "w", encoding="utf-8") as f:
                json.dump({"run_tag": run_tag, "run_id": run_id, "model": settings.model,
                           "focal_pid": focal_pid, "design": design, "arm": arm,
                           "trust": trust_all.get(focal_pid, {}),
                           "trace": traces.get(focal_pid, {}),
                           "trust_all": trust_all, "traces_all": traces,
                           "probe_trust": {str(k): v[0] for k, v in probe_trust.items()},
                           "probe_info": {str(k): v[1] for k, v in probe_trust.items()}},
                          f, default=str)
        except Exception:
            pass
        game._last_votes = {"votes": votes, "majority": str(maj), "majority_correct": maj_correct,
                            "trust": trust_all.get(focal_pid, {}),
                            "trace": traces.get(focal_pid, {})}
        _log_progress(run_tag, run_id, game.seed, requested_seed, focal, focal_pid,
                      gate, night_mode, day, len(game.alive_ids()), game.winner)
        prev_majority = str(maj)
    game.check_over()
    if game.winner is None:
        game.winner = "draw"  # max_days reached with no elimination (timeout)
    game._vote_rows = vote_rows
    game._trust_rows = trust_rows
    hdf = pd.DataFrame(game.history)
    for _c in ("speaker", "phase"):
        if _c in hdf.columns:
            hdf[_c] = hdf[_c].astype(str)
    hdf.to_parquet(os.path.join(raw_dir, f"history_{run_id}.parquet"), index=False)
    return game


def _group_trios(tasks):
    groups, seen = [], {}
    for t in tasks:
        key = t["requested_seed"]
        if key not in seen:
            seen[key] = []
            groups.append(seen[key])
        seen[key].append(t)
    return groups


def _effective_cost(row) -> float:
    """Billed cost, falling back to the estimate when billing is absent (F18)."""
    try:
        billed = float(row.get("billed_cost_inr") or 0)
    except Exception:
        billed = 0.0
    if billed > 0:
        return billed
    try:
        return float(row.get("est_cost_inr") or 0)
    except Exception:
        return 0.0


def _cumulative_cost(rows) -> float:
    return float(sum(_effective_cost(r) for r in rows))


def _budget_exceeded(rows, cap) -> bool:
    return cap is not None and _cumulative_cost(rows) > float(cap)


def _default_ledger_path(start=None) -> str:
    """One absolute ledger shared by every worktree of this repository.

    Resolves the main checkout through git's common dir, so a run from a
    worktree spends against the same ledger as a run from the main tree
    (Pre-reg SS9 amendment v2). Falls back to the repo containing this
    file when git is unavailable.
    """
    start = start or os.path.dirname(os.path.abspath(__file__))
    root = None
    try:
        common = subprocess.check_output(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=start, text=True, stderr=subprocess.DEVNULL).strip()
        if common:
            root = os.path.dirname(os.path.normpath(common))
    except Exception:
        root = None
    if not root:
        root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    return os.path.join(root, "logs", "spend_ledger.jsonl")


def _ledger_path(args=None) -> str:
    if args is not None and getattr(args, "spend_ledger", None):
        return os.path.abspath(args.spend_ledger)
    env = os.getenv("MAFIA_SPEND_LEDGER", "").strip()
    if env:
        return os.path.abspath(env)
    return _default_ledger_path()


def _pending_path(args=None) -> str:
    if args is not None and getattr(args, "pending_file", None):
        return args.pending_file
    return os.getenv("MAFIA_PENDING_FILE", "logs/pending_trios.json")


def _calibration_go_path(args=None) -> str:
    if args is not None and getattr(args, "calibration_go", None):
        return args.calibration_go
    return os.getenv("MAFIA_CALIBRATION_GO", "logs/calibration_go.json")


def _calibration_report_path(args=None) -> str:
    if args is not None and getattr(args, "calibration_report", None):
        return args.calibration_report
    return os.getenv("MAFIA_CALIBRATION_REPORT", "logs/calibration_report.json")


def _file_sha256(path: str):
    import hashlib
    if not path or not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _validate_calibration_go(go_path: str, campaign: str, report_path: str):
    """(ok, reason). GO must bind campaign + current report hash (G7)."""
    if not go_path or not os.path.exists(go_path):
        return False, "GO file missing"
    try:
        with open(go_path, encoding="utf-8") as f:
            text = f.read()
        if not text.strip():
            return False, "GO file empty"
        go = json.loads(text)
    except Exception as e:
        return False, f"GO file unparseable: {e}"
    if not isinstance(go, dict):
        return False, "GO file is not a JSON object"
    if str(go.get("campaign", "")) != str(campaign):
        return False, "GO campaign mismatch"
    if not str(go.get("approved_by", "")).strip():
        return False, "GO approved_by missing"
    if not str(go.get("created_at", "")).strip():
        return False, "GO created_at missing"
    current = _file_sha256(report_path)
    if current is None:
        return False, "calibration report missing"
    if str(go.get("calibration_report_sha256", "")) != current:
        return False, "GO report hash stale/mismatch"
    return True, "ok"


import contextlib as _ctxlib
import fcntl as _fcntl


@_ctxlib.contextmanager
def _ledger_lock(path: str):
    """Exclusive file lock so concurrent invocations cannot interleave (G3)."""
    lock_path = (path or "ledger") + ".lock"
    d = os.path.dirname(lock_path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(lock_path, "a+", encoding="utf-8") as lf:
        _fcntl.flock(lf.fileno(), _fcntl.LOCK_EX)
        try:
            yield
        finally:
            _fcntl.flock(lf.fileno(), _fcntl.LOCK_UN)


def _ledger_entries(path: str) -> list:
    """All ledger records. Any unparseable non-empty line is fatal (G3)."""
    if not path or not os.path.exists(path):
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except Exception as e:
                raise RuntimeError(
                    f"spend ledger corrupt at {path}:{i}: unparseable line; "
                    f"refusing to continue (fix or archive the ledger): {e}") from e
    return entries


def _ledger_total(path: str) -> float:
    if not path or not os.path.exists(path):
        return 0.0
    with _ledger_lock(path):
        return float(sum(float(r.get("cost_inr") or 0) for r in _ledger_entries(path)))


def _append_ledger(path: str, row: dict, campaign: str = "", status: str = "kept",
                   source: str = "run_arena"):
    """Append one completed game's spend (F1/G5). Never rewrites history.

    A billed game that is re-run after an interrupted trio is real spend
    twice: both entries stay, the discarded partial is status=discarded
    and the kept re-run is status=kept with a higher attempt number.
    """
    if not path:
        return
    billed = row.get("billed_cost_inr")
    try:
        billed_f = float(billed or 0)
    except Exception:
        billed_f = 0.0
    used_fallback = billed_f <= 0
    camp = campaign or row.get("campaign", "")
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with _ledger_lock(path):
        prior = [r for r in _ledger_entries(path)
                 if r.get("campaign") == camp
                 and r.get("requested_seed") == row.get("requested_seed")
                 and r.get("arm") == row.get("arm")]
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "run_tag": row.get("run_tag", ""),
            "campaign": camp,
            "requested_seed": row.get("requested_seed"),
            "arm": row.get("arm"),
            "game_id": row.get("game_id", ""),
            "billed_cost_inr": billed_f,
            "est_cost_inr": row.get("est_cost_inr"),
            "cost_inr": _effective_cost(row),
            "cost_fallback_est": bool(used_fallback),
            "status": status,
            "attempt": len(prior) + 1,
            "source": source,
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")


def _raw_spend(raw_dir: str) -> float:
    """Every billed (or estimated) attempt in a task's raw log, in Rs.

    llm_client writes one raw row per underlying attempt, including the
    attempts of a game that later crashed or was retried in the worker,
    so this is the most complete spend record for a task.
    """
    total = 0.0
    if not raw_dir or not os.path.isdir(raw_dir):
        return 0.0
    for dirpath, _dirs, files in os.walk(raw_dir):
        for name in files:
            if name != "llm_raw.jsonl":
                continue
            with open(os.path.join(dirpath, name), encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        total += float(json.loads(line).get("cost_inr") or 0)
                    except Exception:
                        continue
    return total


def _reconcile_task_spend(path: str, raw_dir: str, run_tag: str, campaign: str,
                          game_id: str, requested_seed=None, arm=None) -> float:
    """Ledger any raw-logged spend for this task that no ledger row covers.

    Covers a game that crashed (no row), the first attempt of an
    in-worker retry, and a partial game cut by a 402. The difference is
    appended as status=discarded, source=raw-reconcile. Never negative,
    never rewrites. Returns the Rs. added.
    """
    if not path:
        return 0.0
    raw_total = _raw_spend(raw_dir)
    with _ledger_lock(path):
        ledgered = sum(float(r.get("cost_inr") or 0) for r in _ledger_entries(path)
                       if r.get("run_tag") == run_tag and r.get("game_id") == game_id)
    gap = round(raw_total - ledgered, 6)
    if gap <= 1e-6:
        return 0.0
    _append_ledger(path, {"run_tag": run_tag, "campaign": campaign,
                          "game_id": game_id, "requested_seed": requested_seed,
                          "arm": arm, "billed_cost_inr": gap, "est_cost_inr": gap},
                   campaign=campaign, status="discarded", source="raw-reconcile")
    return gap


def _load_pending(path: str) -> list:
    if not path or not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_pending(path: str, items: list):
    if not path:
        return
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)


def _mark_pending(path: str, campaign: str, requested_seed, arms, reason: str):
    items = _load_pending(path)
    key = (campaign, requested_seed)
    items = [it for it in items
             if not (it.get("campaign") == key[0] and it.get("requested_seed") == key[1])]
    items.append({"campaign": campaign, "requested_seed": requested_seed,
                  "arms": list(arms), "reason": reason,
                  "ts": datetime.now(timezone.utc).isoformat()})
    _save_pending(path, items)


def _clear_pending(path: str, campaign: str, requested_seed):
    items = [it for it in _load_pending(path)
             if not (it.get("campaign") == campaign
                     and it.get("requested_seed") == requested_seed)]
    _save_pending(path, items)


def _completed_keys(out_path: str, campaign: str = "") -> set:
    """(campaign, requested_seed, arm) already in canonical games (F2/F19)."""
    keys = set()
    if not out_path or not os.path.exists(out_path):
        return keys
    try:
        df = pd.read_parquet(out_path)
    except Exception:
        return keys
    if df.empty:
        return keys
    for _, r in df.iterrows():
        camp = str(r.get("campaign", "")) if "campaign" in df.columns else ""
        if campaign and camp and camp != campaign:
            continue
        try:
            seed = int(r.get("requested_seed"))
        except Exception:
            continue
        keys.add((camp or campaign, seed, str(r.get("arm", ""))))
    return keys


CALIBRATION_KEYS = {
    "n_games", "n_discarded_games", "discarded_spend_inr", "kept_spend_inr",
    "cost_per_arm_inr", "mean_cost_per_game_inr", "json_failures_per_game",
    "json_per_arm", "mean_days", "mean_days_per_arm",
    "within_seed_days_correlation", "cotx3_nonunanimity_share",
    "cotx3_votes_with_samples", "probe_missingness_by_arm",
    "probe_cost_per_game_inr",
}


def _probe_cost_from_raw(raw_root: str, n_games: int):
    """Probe cost per game from purpose=probe raw rows (G2)."""
    if not raw_root or not n_games:
        return None
    total, found = 0.0, False
    for dirpath, _dirs, files in os.walk(raw_root):
        for name in files:
            if name != "llm_raw.jsonl":
                continue
            with open(os.path.join(dirpath, name), encoding="utf-8") as f:
                for line in f:
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    if rec.get("purpose") == "probe":
                        total += float(rec.get("cost_inr") or 0)
                        found = True
    return round(total / n_games, 6) if found else None


def _projected_trio_cost(kept_rows, planned_trio_cost: float, campaign=None) -> float:
    """max(planned, mean measured kept trio cost so far) (G4).

    Scoped to one campaign when given, and seedless rows (backfills) never
    count, so pilot or smoke trios with other arm sets cannot distort the
    projection.
    """
    seeds = {}
    for r in kept_rows or []:
        if r.get("ledger_status") == "discarded":
            continue
        if r.get("requested_seed") is None:
            continue
        if campaign is not None and r.get("campaign") not in (None, campaign):
            continue
        seeds.setdefault(r.get("requested_seed"), 0.0)
        seeds[r.get("requested_seed")] += _effective_cost(r)
    if not seeds:
        return float(planned_trio_cost)
    mean_trio = sum(seeds.values()) / len(seeds)
    return max(float(planned_trio_cost), float(mean_trio))


def _calibration_report(rows, votes_rows, trust_rows,
                        probe_cost_per_game=None) -> dict:
    """Nuisance-only calibration summary (F26/V8). No arm outcomes, ever."""
    import numpy as _np
    discarded = [r for r in rows if r.get("ledger_status") == "discarded"]
    rows = [r for r in rows if r.get("ledger_status") != "discarded"]
    by_arm_cost, by_arm_days, by_arm_json = {}, {}, {}
    for r in rows:
        arm = str(r.get("arm", ""))
        by_arm_cost.setdefault(arm, []).append(_effective_cost(r))
        try:
            by_arm_days.setdefault(arm, []).append(float(r.get("days") or 0))
        except Exception:
            pass
        try:
            by_arm_json.setdefault(arm, []).append(float(r.get("json_failures") or 0))
        except Exception:
            pass
    # within-seed length correlation (dmn vs cot paired by requested_seed)
    days_by = {}
    for r in rows:
        days_by.setdefault(r.get("requested_seed"), {})[str(r.get("arm", ""))] = r.get("days")
    pairs = [(float(v["dmn_village"]), float(v["cot_village"]))
             for v in days_by.values()
             if "dmn_village" in v and "cot_village" in v
             and v["dmn_village"] is not None and v["cot_village"] is not None]
    rho = None
    if len(pairs) >= 3:
        a = _np.array([p[0] for p in pairs], dtype=float)
        b = _np.array([p[1] for p in pairs], dtype=float)
        if a.std() > 0 and b.std() > 0:
            rho = float(_np.corrcoef(a, b)[0, 1])
    # CoT-x3 non-unanimity share from recorded vote samples
    x3_total, x3_nonunan = 0, 0
    for v in votes_rows or []:
        if str(v.get("arm", "")) != "cotx3_village":
            continue
        samples = v.get("samples")
        if isinstance(samples, (list, tuple)) and len(samples) >= 2:
            counted = [str(s) for s in samples if s is not None]
            if counted:
                x3_total += 1
                if len(set(counted)) > 1:
                    x3_nonunan += 1
    # probe missingness by arm (rows with parse_fail / all probe rows)
    probe_miss = {}
    for t in trust_rows or []:
        if str(t.get("trust_source", "")) != "probe":
            continue
        arm = str(t.get("arm", ""))
        tot, miss = probe_miss.get(arm, (0, 0))
        probe_miss[arm] = (tot + 1, miss + (1 if t.get("parse_fail") else 0))
    return {
        "n_games": len(rows),
        "n_discarded_games": len(discarded),
        "discarded_spend_inr": round(float(sum(_effective_cost(r) for r in discarded)), 4),
        "kept_spend_inr": round(float(sum(_effective_cost(r) for r in rows)), 4),
        "cost_per_arm_inr": {k: round(float(sum(v)), 4) for k, v in by_arm_cost.items()},
        "mean_cost_per_game_inr": {k: round(float(sum(v) / len(v)), 4)
                                   for k, v in by_arm_cost.items() if v},
        "json_failures_per_game": (float(sum(float(r.get("json_failures") or 0) for r in rows) / len(rows))
                                   if rows else None),
        "json_per_arm": {k: round(float(sum(v) / len(v)), 4) for k, v in by_arm_json.items() if v},
        "mean_days": (float(sum(float(r.get("days") or 0) for r in rows) / len(rows)) if rows else None),
        "mean_days_per_arm": {k: round(float(sum(v) / len(v)), 4) for k, v in by_arm_days.items() if v},
        "within_seed_days_correlation": rho,
        "cotx3_nonunanimity_share": (x3_nonunan / x3_total) if x3_total else None,
        "cotx3_votes_with_samples": x3_total,
        "probe_missingness_by_arm": {k: {"missing": m, "total": t,
                                         "rate": (m / t if t else None)}
                                     for k, (t, m) in probe_miss.items()},
        "probe_cost_per_game_inr": probe_cost_per_game,
    }


def _reconcile_trio(trio, ledger_path, run_dir, campaign):
    """Raw-reconcile every task of a trio, finished or not (Pre-reg SS9 v2)."""
    for t in trio:
        try:
            _reconcile_task_spend(
                ledger_path, raw_dir=os.path.join(run_dir, "raw", f"task-{t['run_id']}"),
                run_tag=t["run_tag"], campaign=campaign, game_id=t["run_id"],
                requested_seed=t.get("requested_seed"), arm=t.get("arm"))
        except RuntimeError:
            raise  # corrupt ledger is fatal
        except Exception as e:
            print(f"[{t.get('run_tag')}] spend reconcile failed for {t['run_id']}: {e}")


class _InlineExecutor:
    """Sequential stand-in for a pool (workers=1): runs at submit time."""

    def submit(self, fn, *a, **k):
        from concurrent.futures import Future
        f = Future()
        try:
            f.set_result(fn(*a, **k))
        except BaseException as e:  # noqa: BLE001 - delivered via result()
            f.set_exception(e)
        return f

    def shutdown(self, wait=True, cancel_futures=False):
        return None


def _game_executor(workers: int):
    if int(workers or 1) <= 1:
        return _InlineExecutor()
    if os.getenv("MAFIA_GAME_EXECUTOR", "") == "thread":  # tests only: in-process mocks
        from concurrent.futures import ThreadPoolExecutor
        return ThreadPoolExecutor(max_workers=int(workers))
    return ProcessPoolExecutor(max_workers=int(workers))


def _write_calibration_report(args, run_dir, campaign, report_path, rows, all_votes, all_trust):
    """Nuisance-only report over the campaign's first CALIBRATION_TRIOS trios.

    Uses canonical campaign rows when canonical writes are on, so a
    calibration batch split over several --resume invocations is reported
    whole; otherwise this invocation's rows.
    """
    cal_seeds = {int(args.seed) + i * 100 for i in range(CALIBRATION_TRIOS)}
    g_rows, v_rows, t_rows = rows, all_votes, all_trust
    if not getattr(args, "no_canonical", False):
        base = os.path.dirname(args.out) or "."
        def _load(name):
            p = os.path.join(base, name)
            if not os.path.exists(p):
                return []
            df = pd.read_parquet(p)
            if "campaign" in df.columns:
                df = df[df["campaign"].astype(str) == str(campaign)]
            return df.to_dict("records")
        g_rows = [r for r in _load(os.path.basename(args.out))
                  if int(r.get("requested_seed") or -1) in cal_seeds] or rows
        gids = {r.get("game_id") for r in g_rows}
        v_rows = [r for r in _load("votes.parquet") if r.get("game_id") in gids] or all_votes
        t_rows = [r for r in _load("trust.parquet") if r.get("game_id") in gids] or all_trust
    runs_root = os.path.dirname(run_dir) or "."
    total, found = 0.0, False
    gids = {r.get("game_id") for r in g_rows}
    for rd in (os.listdir(runs_root) if os.path.isdir(runs_root) else []):
        raw = os.path.join(runs_root, rd, "raw")
        if not os.path.isdir(raw):
            continue
        for td in os.listdir(raw):
            if td.startswith("task-") and td[5:] in gids:
                p = os.path.join(raw, td, "llm_raw.jsonl")
                if os.path.exists(p):
                    with open(p, encoding="utf-8") as f:
                        for line in f:
                            try:
                                rec = json.loads(line)
                            except Exception:
                                continue
                            if rec.get("purpose") == "probe":
                                total += float(rec.get("cost_inr") or 0)
                                found = True
    pcost = round(total / len(g_rows), 6) if (found and g_rows) else None
    report = _calibration_report(g_rows, v_rows, t_rows, probe_cost_per_game=pcost)
    for dest in (os.path.join(run_dir, "calibration_report.json"), report_path):
        d = os.path.dirname(dest)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
    return report


def _run_team_window(args, tasks, run_tag, run_dir, campaign, ledger_path,
                     pending_path, go_path, report_path, rows, all_votes, all_trust):
    """Seed-trio window (P0-S2): up to --trio-window trios in flight.

    Each trio stays atomic: it reaches canonical only when all its games
    finished. Before a trio is launched, ledger + projected cost of every
    in-flight trio + this one must fit the cap. Trio index >= 20 needs a
    valid GO; the calibration report is written once trios 0..19 are all
    finalised (completion order does not matter).
    """
    from concurrent.futures import FIRST_COMPLETED, wait

    cap = float(getattr(args, "budget_cap", PREREG_BUDGET_CAP))
    window = max(1, int(getattr(args, "trio_window", 1) or 1))
    start_trio = int(getattr(args, "start_trio", 0) or 0)
    # Trio index from the seed, not the queue position: --resume removes
    # completed trios, which shifted positions in the old loop (P0-S2).
    queue = [((int(trio[0]["requested_seed"]) - int(args.seed)) // 100, trio)
             for trio in _group_trios(tasks)]
    ex = _game_executor(getattr(args, "workers", 1))
    inflight = {}  # trio_index -> {"trio", "futs": {fut: task}, "results", "billing", "failed"}
    fut_owner = {}
    stop_launch = False
    billing_abort = False
    # Calibration trios not queued here were completed earlier or precede
    # --start-trio; the report fires only when trio 19 finalises in this
    # invocation (as before) and all of 0..19 are done.
    cal_done = {i for i in range(CALIBRATION_TRIOS)} - {i for i, _ in queue}
    finalised_here = set()
    cal_reported = False

    def _projected():
        hist = [{"requested_seed": e.get("requested_seed"), "campaign": e.get("campaign"),
                 "billed_cost_inr": e.get("cost_inr"), "ledger_status": e.get("status")}
                for e in _ledger_entries(ledger_path)]
        return _projected_trio_cost(hist, getattr(args, "planned_trio_cost", 8.13), campaign=campaign)

    def _launch():
        nonlocal stop_launch
        while queue and not stop_launch and len(inflight) < window:
            idx, trio = queue[0]
            if idx >= CALIBRATION_TRIOS:
                ok, reason = _validate_calibration_go(go_path, campaign, report_path)
                if not ok:
                    if not inflight:
                        print(f"[{run_tag}] calibration pause before trio {idx}: {reason}.")
                        stop_launch = True
                    return  # wait for calibration trios to finish first
            proj = _projected()
            ledger_now = _ledger_total(ledger_path)
            need = ledger_now + proj * (len(inflight) + 1)
            if need > cap:
                print(f"[{run_tag}] BUDGET projection Rs.{ledger_now:.2f} + "
                      f"{len(inflight) + 1} x Rs.{proj:.2f} exceeds cap Rs.{cap}; "
                      "trio not started.")
                stop_launch = True
                return
            queue.pop(0)
            st = {"trio": trio, "futs": {}, "results": [], "billing": False, "failed": False}
            for t in trio:
                f = ex.submit(_run_task, t)
                st["futs"][f] = t
                fut_owner[f] = idx
                # Never start another game after a 402 (inline executor
                # runs at submit time; pool futures finish fast on 402).
                if f.done() and isinstance(f.exception(), BillingExhausted):
                    stop_launch = True
                    break
            inflight[idx] = st

    def _finalise(idx):
        nonlocal stop_launch, billing_abort
        st = inflight.pop(idx)
        trio, results = st["trio"], st["results"]
        seed0 = trio[0]["requested_seed"] if trio else None
        arm_names = [t["arm"] for t in trio]
        for r in results:
            all_votes.extend(r.get("votes") or [])
            all_trust.extend(r.get("trust") or [])
        if st["billing"] or st["failed"] or len(results) != len(trio):
            # Atomicity (F2/F16/F17): partial trio stays in the bundle
            # only, spend is still ledgered, trio marked pending.
            for r in results:
                _record_result(r, args, run_dir, rows, canonical=False,
                               ledger_path=ledger_path, campaign=campaign)
            _reconcile_trio(trio, ledger_path, run_dir, campaign)
            _mark_pending(pending_path, campaign, seed0, arm_names,
                          "billing_exhausted" if st["billing"] else "worker_failure")
            print(f"[{run_tag}] trio {seed0} pending "
                  f"({'billing' if st['billing'] else 'worker failure'}); "
                  "rerun with --resume on the same seeds.")
            if st["billing"]:
                billing_abort = True
                stop_launch = True
            return
        # Keep the trio's games in task (arm) order for deterministic rows.
        order = {t["run_id"]: i for i, t in enumerate(trio)}
        results.sort(key=lambda r: order.get(r["row"].get("game_id"), 0))
        for r in results:
            _record_result(r, args, run_dir, rows, canonical=True,
                           ledger_path=ledger_path, campaign=campaign)
        _reconcile_trio(trio, ledger_path, run_dir, campaign)
        _clear_pending(pending_path, campaign, seed0)
        finalised_here.add(idx)
        if idx < CALIBRATION_TRIOS:
            cal_done.add(idx)
        if _ledger_total(ledger_path) > cap:
            print(f"[{run_tag}] BUDGET CAP Rs.{cap} exceeded "
                  f"(ledger Rs.{_ledger_total(ledger_path):.2f}); aborting remaining trios.")
            stop_launch = True

    try:
        _launch()
        while inflight:
            pending_futs = [f for st in inflight.values() for f in st["futs"] if not f.done()]
            if pending_futs:
                wait(pending_futs, return_when=FIRST_COMPLETED)
            for idx in list(inflight):
                st = inflight[idx]
                for f, t in list(st["futs"].items()):
                    if not f.done() or f in st.get("_seen", set()):
                        continue
                    st.setdefault("_seen", set()).add(f)
                    try:
                        st["results"].append(f.result())
                    except BillingExhausted as e:
                        print(f"\n[{run_tag}] BILLING EXHAUSTED at {t['run_id']}: {e}")
                        st["billing"] = True
                        stop_launch = True
                    except Exception as e:
                        print(f"[{run_tag}] worker failed for {t['run_id']}: "
                              f"{type(e).__name__}: {e}")
                        st["failed"] = True
                if all(f.done() for f in st["futs"]):
                    _finalise(idx)
            if (not cal_reported and (CALIBRATION_TRIOS - 1) in finalised_here
                    and len(cal_done) >= CALIBRATION_TRIOS
                    and not any(i < CALIBRATION_TRIOS for i in inflight)):
                ok, _r = _validate_calibration_go(go_path, campaign, report_path)
                if not ok:
                    _write_calibration_report(args, run_dir, campaign, report_path,
                                              rows, all_votes, all_trust)
                    cal_reported = True
                    print(f"[{run_tag}] calibration pause after {CALIBRATION_TRIOS} trios; "
                          f"report in {report_path}. Create a valid GO in {go_path} to continue.")
                    stop_launch = True
            _launch()
    finally:
        ex.shutdown(wait=True, cancel_futures=True)


def _run_one_with_retry(task, runner=None):
    runner = runner or _run_task_once
    try:
        return runner(task)
    except BillingExhausted:
        raise
    except Exception:
        return runner(task)


def _run_task(task: dict) -> dict:
    return _run_one_with_retry(task, runner=_run_task_once)


def _run_task_once(task: dict) -> dict:
    """Run one game in a worker process.

    Workers write only their own raw files (per-task LLM log dir + unique
    trace/history filenames). Parquet tables are written by the parent.
    """
    os.environ["MAFIA_RUN_TAG"] = task["run_tag"]
    os.environ["MAFIA_RAW_DIR"] = os.path.join(task["run_dir"], "raw", f"task-{task['run_id']}")
    if task.get("tau") is not None:
        settings.tau_delay = task["tau"]
    mark = dict(COST_LOG)
    g = play_one(
        seed=task["requested_seed"], focal=task["focal"], gate=task["gate"],
        run_id=task["run_id"], focal_role=task["focal_role"],
        night_mode=task["night_mode"], run_tag=task["run_tag"],
        run_dir=task["run_dir"], requested_seed=task["requested_seed"],
        max_days=task["max_days"], ablate=task.get("ablate"),
        design=task.get("design", "focal"), arm=task.get("arm"),
        campaign=task.get("campaign"),
    )
    dp = COST_LOG["prompt_tokens"] - mark["prompt_tokens"]
    dc = COST_LOG["completion_tokens"] - mark["completion_tokens"]
    dj = COST_LOG["json_failures"] - mark["json_failures"]
    dc_inr = COST_LOG["cost_inr"] - mark["cost_inr"]
    lv = getattr(g, "_last_votes", {})
    fl = getattr(g, "_focal_last", {}) or {}
    trace = fl.get("trace", {}) if isinstance(fl, dict) else {}
    jev_info = trace.get("jev") if isinstance(trace, dict) else None
    focal_pid = getattr(g, "_focal_pid", 0)
    row = {
        "run_tag": task["run_tag"], "game_id": task["run_id"],
        "seed": g.seed, "requested_seed": task["requested_seed"],
        "focal": task["focal"], "focal_pid": focal_pid,
        "gate": task["gate"], "night_mode": task["night_mode"],
        "provider": settings.provider, "model": settings.model,
        "jev_model": settings.jev_model, "git_sha": task["git_sha"],
        "tau": settings.tau_delay, "evt_threshold": settings.evt_threshold,
        "ablate": ",".join(task.get("ablate") or []),
        # days = number of days played (day-count). Pilot parquet stored
        # the zero-based last-day index (g.day); a first-day game recorded
        # 0 there. New rows store the count (F12), so a game ending on
        # day 0 records 1 and a 5-day cap records 5. The calibration
        # length rule (mean days < 1.5) uses this count convention.
        "winner": g.winner, "days": int(g.day) + 1,
        "focal_role": g.players[focal_pid].role,
        "majority_correct": lv.get("majority_correct"),
        "delay_cause": trace.get("delay_cause") if isinstance(trace, dict) else None,
        "parse_fail": trace.get("parse_fail") if isinstance(trace, dict) else None,
        "trust_json": json.dumps(fl.get("trust", {}) if isinstance(fl, dict) else {}),
        "trace_json": json.dumps(fl.get("trace", {}) if isinstance(fl, dict) else {}, default=str)[:4000],
        "prompt_tokens": dp, "completion_tokens": dc,
        "est_cost_inr": round(dc_inr, 4) if dc_inr > 0 else _est_cost_inr(dp, dc),
        "billed_cost_inr": round(dc_inr, 4),
        "json_failures": dj,
        "jev_stub": jev_info.get("stub") if isinstance(jev_info, dict) else None,
        "design": task.get("design", "focal"),
        "campaign": task.get("campaign") or task["run_tag"],
        "arm": task.get("arm") or task["focal"],
        "village_arm": (TEAM_ARMS[task["arm"]]["village"] if task.get("arm") in TEAM_ARMS else task["focal"]),
        "mafia_arm": (TEAM_ARMS[task["arm"]]["mafia"] if task.get("arm") in TEAM_ARMS else "cot"),
    }
    return {"row": row,
            "votes": getattr(g, "_vote_rows", []) or [],
            "trust": getattr(g, "_trust_rows", []) or []}


def _record_result(result: dict, args, run_dir: str, rows: list,
                   canonical: bool = True, ledger_path: str = None,
                   campaign: str = "", status: str = None):
    row = result["row"]
    if status is None:
        status = "kept" if canonical else "discarded"
    row["ledger_status"] = status
    rows.append(row)
    if ledger_path:
        _append_ledger(ledger_path, row, campaign=campaign, status=status)
    gdf = pd.DataFrame([row])
    _upsert(os.path.join(run_dir, "games.parquet"), gdf, ["run_tag", "game_id"])
    is_team = str(row.get("design", "")) == "team"
    if canonical and not getattr(args, "no_canonical", False):
        # Team canonical rows are idempotent on the campaign key (F2);
        # focal rows keep the historical run_tag key.
        gkeys = ["campaign", "requested_seed", "arm"] if is_team else ["run_tag", "game_id"]
        _upsert(args.out, gdf, gkeys)
    if result["votes"]:
        vdf = pd.DataFrame(result["votes"])
        _upsert(os.path.join(run_dir, "votes.parquet"), vdf,
                ["run_tag", "game_id", "day", "voter"])
        if canonical and not getattr(args, "no_canonical", False):
            vkeys = (["campaign", "game_id", "day", "voter"] if is_team
                     else ["run_tag", "game_id", "day", "voter"])
            _upsert(os.path.join(os.path.dirname(args.out) or ".", "votes.parquet"), vdf, vkeys)
    if result["trust"]:
        tdf = pd.DataFrame(result["trust"])
        _tkeys = ["run_tag", "game_id", "day", "agent", "target"]
        if "trust_source" in tdf.columns:
            _tkeys = _tkeys + ["trust_source"]
        _upsert(os.path.join(run_dir, "trust.parquet"), tdf, _tkeys)
        if canonical and not getattr(args, "no_canonical", False):
            tkeys = (["campaign", "game_id", "day", "agent", "target", "trust_source"]
                     if is_team and "trust_source" in tdf.columns else _tkeys)
            _upsert(os.path.join(os.path.dirname(args.out) or ".", "trust.parquet"), tdf, tkeys)
    print(f"[{row['run_tag']}] {row['game_id']}: {row['winner']} in {row['days']} days "
          f"role={row['focal_role']} json_failures={row['json_failures']}")


def build_tasks(args, run_tag, run_dir, git_sha, ablations=None):
    ablations = ablations or []
    design = getattr(args, "design", "focal")
    if design == "team":
        arms = [a.strip() for a in args.arms.split(",") if a.strip()]
        for a in arms:
            if a not in TEAM_ARMS:
                raise ValueError(f"unknown team arm: {a}")
        n_trios = getattr(args, "trios", None)
        n_trios = int(n_trios) if n_trios is not None else int(args.games)
        start_trio = int(getattr(args, "start_trio", 0) or 0)
        campaign = getattr(args, "campaign", None) or run_tag
        tasks = []
        for i in range(n_trios):
            requested_seed = args.seed + (start_trio + i) * 100
            for arm in arms:
                tasks.append({
                    "requested_seed": requested_seed, "focal": arm, "arm": arm,
                    "design": "team", "run_id": f"{campaign}-{requested_seed}-{arm}",
                    "campaign": campaign,
                    "gate": args.gate, "focal_role": "random",
                    "night_mode": args.night, "run_tag": run_tag,
                    "run_dir": run_dir, "max_days": args.max_days,
                    "tau": getattr(args, "tau", None), "ablate": ablations,
                    "git_sha": git_sha,
                })
        return tasks
    focals = [f.strip() for f in args.agents.split(",") if f.strip()]
    taus = [settings.tau_delay]
    if getattr(args, "tau_sweep", None):
        taus = [float(x) for x in args.tau_sweep.split(",") if x.strip()]
    tau_val = getattr(args, "tau", None)
    tasks = []
    for tau in taus:
        for i in range(args.games):
            for focal in focals:
                requested_seed = args.seed + i * 100
                run_id = f"{requested_seed}-{focal}"
                if getattr(args, "tau_sweep", None):
                    run_id += f"-tau{tau:g}"
                tasks.append({
                    "requested_seed": requested_seed, "focal": focal, "arm": None,
                    "design": "focal", "run_id": run_id, "gate": args.gate,
                    "focal_role": args.focal_role, "night_mode": args.night,
                    "run_tag": run_tag, "run_dir": run_dir,
                    "max_days": args.max_days,
                    "tau": tau_val if tau_val is not None else tau,
                    "ablate": ablations, "git_sha": git_sha,
                })
    return tasks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=5)
    ap.add_argument("--agents", type=str, default="dmn_tpn,cot")
    ap.add_argument("--design", type=str, default="focal", choices=["focal", "team"])
    ap.add_argument("--arms", type=str, default="dmn_village,cot_village,cotx3_village")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--gate", type=str, default="llm", choices=["llm", "jev"])
    ap.add_argument("--night", type=str, default="llm", choices=["llm", "scripted"])
    ap.add_argument("--focal-role", type=str, default="random",
                    choices=["random", "villager", "mafia", "doctor", "detective"])
    ap.add_argument("--run-tag", type=str, default=None)
    ap.add_argument("--max-days", type=int, default=5,
                    help="day cap (lower only for pipeline smoke tests)")
    ap.add_argument("--trio-window", type=int, default=1,
                    help="seed-trios in flight at once (P0-S2); each trio stays atomic")
    ap.add_argument("--call-threads", type=int, default=None,
                    help="intra-game concurrent calls (P0-S1); sets MAFIA_CALL_THREADS")
    ap.add_argument("--workers", type=int, default=4,
                    help="parallel game processes (default 4; 1 = sequential)")
    ap.add_argument("--tau", type=float, default=None,
                    help="override TAU_DELAY for this run")
    ap.add_argument("--tau-sweep", type=str, default=None,
                    help="comma-separated TAU_DELAY values; repeats the dmn_tpn cells per tau")
    ap.add_argument("--ablate", type=str, default="",
                    help="comma-separated dmn_tpn ablations: exformation,tpn,evt")
    ap.add_argument("--budget-cap", type=float, default=PREREG_BUDGET_CAP,
                    help="cumulative billed Rs. cap; abort after current trio")
    ap.add_argument("--calibration-trios", type=int, default=20)
    ap.add_argument("--campaign", type=str, default=None,
                    help="fixed campaign tag for confirmatory/idempotent runs (F2)")
    ap.add_argument("--start-trio", type=int, default=0,
                    help="first trio index in the seed series (seed=5000+100*index)")
    ap.add_argument("--trios", type=int, default=None,
                    help="number of seed-trios to run (team design; default --games)")
    ap.add_argument("--planned-trios", type=int, default=184,
                    help="planned campaign size recorded in the manifest (120-184)")
    ap.add_argument("--resume", action="store_true",
                    help="rerun only pending or missing trios on the same seeds")
    ap.add_argument("--calibration", action="store_true",
                    help="calibration batch: nuisance-only report, no outcomes")
    ap.add_argument("--spend-ledger", type=str, default=None,
                    help="append-only spend ledger (default logs/spend_ledger.jsonl)")
    ap.add_argument("--pending-file", type=str, default=None,
                    help="pending trios file (default logs/pending_trios.json)")
    ap.add_argument("--calibration-go", type=str, default=None,
                    help="human GO file required past calibration (default logs/calibration_go.json)")
    ap.add_argument("--calibration-report", type=str, default=None,
                    help="canonical calibration report the GO binds to (default logs/calibration_report.json)")
    ap.add_argument("--planned-trio-cost", type=float, default=8.13,
                    help="assumed Rs. per trio for in-flight projection (G4)")
    ap.add_argument("--confirmatory", action="store_true",
                    help="enforce pre-registration checks before starting")
    ap.add_argument("--no-canonical", action="store_true",
                    help="write only logs/runs/<run_tag>/ (smoke tests)")
    ap.add_argument("--out", type=str, default="logs/games.parquet")
    args = ap.parse_args()
    if getattr(args, "call_threads", None):
        os.environ["MAFIA_CALL_THREADS"] = str(int(args.call_threads))
    if getattr(args, "design", None) == "team" and getattr(args, "tau", None) is None:
        ap.error("--tau is required for --design team (G11): pass --tau 0.35 explicitly")
    if args.tau is not None:
        settings.tau_delay = args.tau
    ablations = sorted({x.strip() for x in args.ablate.split(",") if x.strip()})
    unknown = set(ablations) - {"exformation", "tpn", "evt"}
    if unknown:
        ap.error(f"unknown ablation(s): {', '.join(sorted(unknown))}")
    _assert_confirmatory(args)

    run_tag = args.run_tag or getattr(args, "campaign", None) or time.strftime("%Y%m%d-%H%M%S")
    campaign = getattr(args, "campaign", None) or run_tag
    os.environ["MAFIA_RUN_TAG"] = run_tag
    runs_root = os.getenv("MAFIA_RUNS_DIR", os.path.join("logs", "runs"))
    run_dir = os.path.join(runs_root, run_tag)
    os.makedirs(os.path.join(run_dir, "raw"), exist_ok=True)
    os.environ["MAFIA_RAW_DIR"] = os.path.join(run_dir, "raw")
    git_sha = _git_sha()
    _write_manifest(os.path.join(run_dir, "manifest.json"), args, run_tag, git_sha)
    ledger_path = _ledger_path(args)
    pending_path = _pending_path(args)
    go_path = _calibration_go_path(args)
    report_path = _calibration_report_path(args)
    # Calibration gate (G7): campaign state, not flags. Any trio index
    # at or beyond 20 needs a valid GO, whatever flags were passed.
    if getattr(args, "design", None) == "team":
        if int(getattr(args, "start_trio", 0) or 0) >= CALIBRATION_TRIOS:
            ok, reason = _validate_calibration_go(go_path, campaign, report_path)
            if not ok:
                raise SystemExit(
                    f"Continuation refused at trio {args.start_trio}: {reason}. "
                    f"GO must be JSON with campaign, calibration_report_sha256, "
                    f"created_at and approved_by in {go_path}.")
    if (_ledger_total(ledger_path) > float(getattr(args, "budget_cap", PREREG_BUDGET_CAP))
            and getattr(args, "budget_cap", None) is not None):
        print(f"[{run_tag}] BUDGET CAP Rs.{args.budget_cap} already exceeded "
              f"(ledger Rs.{_ledger_total(ledger_path):.2f}); no games started.")
        print(f"Run bundle: {run_dir}")
        return

    tasks = build_tasks(args, run_tag, run_dir, git_sha, ablations=ablations)
    if getattr(args, "design", "focal") == "team" and not args.no_canonical:
        completed = _completed_keys(args.out, campaign)
        dup = [t for t in tasks
               if (campaign, t["requested_seed"], t["arm"]) in completed]
        if dup and not getattr(args, "resume", False):
            raise SystemExit(
                f"{len(dup)} task(s) already completed for campaign {campaign}; "
                "use --resume to rerun only pending/missing trios (F2/F19).")
        if getattr(args, "resume", False):
            tasks = [t for t in tasks
                     if (campaign, t["requested_seed"], t["arm"]) not in completed]

    rows = []
    all_votes, all_trust = [], []
    if getattr(args, "design", "focal") == "team":
        _run_team_window(args, tasks, run_tag, run_dir, campaign, ledger_path,
                         pending_path, go_path, report_path, rows, all_votes, all_trust)
    elif args.workers > 1 and len(tasks) > 1:
        ex = ProcessPoolExecutor(max_workers=min(args.workers, len(tasks)))
        futures = {ex.submit(_run_task, t): t for t in tasks}
        try:
            for fut in as_completed(futures):
                try:
                    result = fut.result()
                except BillingExhausted as e:
                    t = futures[fut]
                    print(f"\n[{run_tag}] BILLING EXHAUSTED at {t['run_id']}: {e}")
                    print(f"[{run_tag}] cancelling remaining games; top up AiCredits and rerun.")
                    break
                except Exception as e:
                    t = futures[fut]
                    print(f"[{run_tag}] worker failed for {t['run_id']}: "
                          f"{type(e).__name__}: {e}")
                    continue
                _record_result(result, args, run_dir, rows,
                               ledger_path=ledger_path, campaign=campaign)
        finally:
            for f in futures:
                f.cancel()
            ex.shutdown(wait=True, cancel_futures=True)
    else:
        for t in tasks:
            try:
                result = _run_task(t)
            except BillingExhausted as e:
                print(f"\n[{run_tag}] BILLING EXHAUSTED at {t['run_id']}: {e}")
                print(f"[{run_tag}] stopping; top up AiCredits and rerun.")
                break
            _record_result(result, args, run_dir, rows,
                           ledger_path=ledger_path, campaign=campaign)

    if getattr(args, "calibration", False):
        pcost = _probe_cost_from_raw(os.path.join(run_dir, "raw"), len(rows))
        report = _calibration_report(rows, all_votes, all_trust,
                                     probe_cost_per_game=pcost)
        for dest in (os.path.join(run_dir, "calibration_report.json"), report_path):
            d = os.path.dirname(dest)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
        print(f"Calibration report (nuisance only): {report_path}")
    df = pd.DataFrame(rows)
    if args.no_canonical:
        print(f"\nSaved {len(rows)} rows to {run_dir}/games.parquet (canonical skipped)")
    else:
        print(f"\nSaved {len(rows)} rows to {args.out} and {run_dir}/games.parquet")
    if len(df) and not getattr(args, "calibration", False):
        print(df[["focal", "winner", "focal_role"]].value_counts(dropna=False))
    print(f"Run bundle: {run_dir}")


if __name__ == "__main__":
    main()
