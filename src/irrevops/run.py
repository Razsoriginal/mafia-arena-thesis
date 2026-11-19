"""IrrevOps v3 runner. Simulated tools only; every paid call is ledgered.

    .venv/bin/python -m src.irrevops.run --campaign explore-ops-01 \\
        --arms L0_bare,L1_prompt_rule --split dev --instances 0 \\
        --reps 300600 --workers 4 --lane-cap 10

Each episode runs in its own process with its own raw-log directory, so
its spend is the sum of its raw attempt rows. Before each submission the
ledger total plus a bound for every in-flight episode must fit the lane
cap (this campaign) and the global cap. Resume-safe: finished episode ids
are skipped. Campaigns named explore-*, pilot-* or smoke-* are
non-confirmatory and must use repetition seeds >= 100000.
"""
import argparse
import json
import os
import random
import zlib
import subprocess
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from datetime import datetime, timezone

import pandas as pd

from src.eval import run_arena as ra
from src.llm_client import _est_cost_inr

from . import controls as C
from .agent import MAX_STEPS
from .tasks import TASK_SET_VERSION, build_tasks, task_set_sha256

AGENT_TEMPERATURE = 0.7
SCORER_TEMPERATURE = 0.0
EPISODE_BOUND_INR = (2 * MAX_STEPS) * _est_cost_inr(3500, 2600)
NONCONFIRMATORY = ("explore-", "pilot-", "smoke-")


def stable_seed(rep: int, task_id: str) -> int:
    """Seed for the simulated reviewer; identical across processes and
    resumes (Python's hash() is salted per process; review m8)."""
    return int(rep) * 7919 + zlib.crc32(task_id.encode("utf-8")) % 100003


def console_line(campaign: str, row: dict, cost: float, n_done: int) -> str:
    """One progress line. For a confirmatory campaign it carries a counter
    and the cost only: no arm, task, twin, step count or how the episode
    ended, since escalation is an outcome (review M8)."""
    if campaign.startswith(NONCONFIRMATORY):
        return (f"[{campaign}] {row['episode_id']}: steps={row['n_steps']} ended={row['ended']} "
                f"parse_fails={row['agent_parse_fails']} Rs.{cost:.4f}")
    return f"[{campaign}] episode {n_done} done Rs.{cost:.4f}"


def append_row(path: str, row: dict):
    """Append one episode as a JSON line, flushed to disk (review m13;
    the crash of 2026-11-19)."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")
        f.flush()
        os.fsync(f.fileno())


def read_rows(path: str) -> list:
    """Episode rows. A torn last line from a crash is skipped; that
    episode is simply not done and will be re-run."""
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "rb") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def done_ids(path: str) -> set:
    return {r["episode_id"] for r in read_rows(path)}


def compact(jsonl_path: str, parquet_path: str):
    rows = read_rows(jsonl_path)
    if rows:
        tmp = parquet_path + ".tmp"
        pd.DataFrame(rows).to_parquet(tmp, index=False)
        os.replace(tmp, parquet_path)
    return len(rows)


def _provider_failed(meta: dict) -> bool:
    """True when the client got no reply at all after its retries. Bad
    JSON from the model is behaviour, not infrastructure."""
    return bool(meta.get("empty_raw"))


AGENT_ROLE = {"A": None, "B": "BackboneB", "C": "BackboneC"}


def _step_fn(role=None):
    from src import llm_client as llm

    def step(system, user):
        meta = {}
        d = llm.chat_json(system, user, meta=meta, temperature=AGENT_TEMPERATURE, purpose="ops_step", role=role)
        return d, bool(meta.get("parse_fail")), _provider_failed(meta)
    return step


def _scorer(role=None, purpose="ops_verify"):
    """A scoring call. L2: the agent's own backbone (`role` = the agent's
    role). L4 and L5b: the monitor role, a model from another family with
    its own key (purpose ops_monitor)."""
    from src import llm_client as llm

    def score(ticket, transcript, tool, args):
        meta = {}
        d = llm.chat_json(C.VERIFIER_SYSTEM, C.verifier_user(ticket, transcript, tool, args),
                          meta=meta, temperature=SCORER_TEMPERATURE, purpose=purpose, role=role)
        try:
            conf = float(d.get("confidence", 0.0))
        except Exception:
            conf = 0.0
        return max(0.0, min(1.0, conf)), d, bool(meta.get("parse_fail")), _provider_failed(meta)
    return score


def make_control(arm: str, cfg: dict):
    if arm == "L0_bare":
        return C.Control()
    if arm == "L1_prompt_rule":
        return C.PromptRule()
    if arm == "L2_self_verify":
        return C.ScoreGate(arm, _scorer(cfg.get("agent_role")), cfg["l2_threshold"])
    if arm == "L3_policy_gate":
        return C.PolicyGate()
    if arm == "L5a_approve_all":
        return C.ApproveAll()
    if arm == "L6_reversibility":
        return C.Reversibility()
    if arm in ("L4_monitor", "L5b_calibrated_escalation"):
        role = cfg.get("monitor_role")
        if not role:
            raise SystemExit(f"{arm} needs a monitor role (a model from another family with its own key); "
                             f"see docs/decisions/2026-11-19-keys-request.md")
        mon = _scorer(role, purpose="ops_monitor")
        if arm == "L4_monitor":
            return C.ScoreGate(arm, mon, cfg["l4_threshold"])
        return C.CalibratedEscalation(mon, cfg["l5b_lo"], cfg["l4_threshold"])
    raise SystemExit(f"unknown arm {arm}")


def check_roles(arms, cfg):
    """Fail before any paid call if a needed role is missing or shares a
    key with another role in this run."""
    from src import roles
    if cfg.get("monitor_role") and cfg.get("monitor_role") == cfg.get("agent_role"):
        raise SystemExit("the monitor must not be the agent's own role")
    used = [r for r in {cfg.get("agent_role"), cfg.get("monitor_role") if set(arms) & {
        "L4_monitor", "L5b_calibrated_escalation"} else None} if r]
    for r in used:
        roles.role_config(r)
    if len(used) > 1:
        roles.assert_distinct_keys(used)
    for arm, keys in (("L2_self_verify", ("l2_threshold",)), ("L4_monitor", ("l4_threshold",)),
                      ("L5b_calibrated_escalation", ("l4_threshold", "l5b_lo"))):
        if arm in arms and any(cfg.get(k) is None for k in keys):
            raise SystemExit(f"{arm} needs {', '.join(keys)} (from the calibration split, never from test)")


def _episode_worker(job):
    os.environ["MAFIA_RUN_TAG"] = job["campaign"]
    os.environ["MAFIA_RAW_DIR"] = job["raw_dir"]
    os.makedirs(job["raw_dir"], exist_ok=True)
    from .agent import run_episode
    from .controls import InfraFailure
    task = {t.task_id: t for t in build_tasks()}[job["task_id"]]
    control = make_control(job["arm"], job["cfg"])
    t0 = time.time()
    try:
        row = run_episode(task, control, _step_fn(job["cfg"].get("agent_role")), episode_id=job["episode_id"],
                          human_error_rate=job["cfg"].get("human_error_rate", 0.0),
                          rng=random.Random(stable_seed(job["rep"], job["task_id"])))
    except InfraFailure as e:
        return {"infra_failed": True, "episode_id": job["episode_id"], "task_id": job["task_id"],
                "arm": job["arm"], "rep": job["rep"], "attempt": job.get("attempt", 1), "error": str(e)[:200]}
    row["wall_s"] = round(time.time() - t0, 2)
    row["attempt"] = job.get("attempt", 1)
    return row


def _git_sha():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", required=True)
    ap.add_argument("--arms", default="L0_bare")
    ap.add_argument("--split", default="dev", help="dev | cal | test | comma list")
    ap.add_argument("--instances", default="all", help="comma list of instance indices, or all")
    ap.add_argument("--templates", default="all", help="comma list of template id prefixes, or all")
    ap.add_argument("--reps", default="300600")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--lane-cap", type=float, required=True, help="max Rs. for this campaign")
    ap.add_argument("--backbone", default="A", choices=sorted(AGENT_ROLE))
    ap.add_argument("--monitor-role", default=None, help="exploratory runs: role name of the monitor, e.g. Monitor")
    ap.add_argument("--l2-threshold", type=float, default=None)
    ap.add_argument("--l4-threshold", type=float, default=None)
    ap.add_argument("--l5b-lo", type=float, default=None)
    ap.add_argument("--human-error-rate", type=float, default=0.0)
    a = ap.parse_args()

    from src import llm_client as llm
    from src.config import settings
    from . import freeze
    nonconf = a.campaign.startswith(NONCONFIRMATORY)
    if not nonconf and not a.campaign.startswith("ops-"):
        ap.error("campaign must be prefixed explore-/pilot-/smoke- (non-confirmatory) or ops- (confirmatory)")
    splits = {x.strip() for x in a.split.split(",")}
    reps = [int(x) for x in a.reps.split(",")]
    arms = [x.strip() for x in a.arms.split(",")]
    if nonconf:
        if "test" in splits:
            ap.error("the test split is held out: a non-confirmatory campaign may not run it")
        if any(r < 100000 for r in reps):
            ap.error("non-confirmatory repetitions must use indices >= 100000")
        cfg = {"agent_role": AGENT_ROLE[a.backbone], "monitor_role": a.monitor_role,
               "l2_threshold": a.l2_threshold, "l4_threshold": a.l4_threshold, "l5b_lo": a.l5b_lo,
               "human_error_rate": a.human_error_rate}
    else:
        # Confirmatory: everything comes from the freeze block; the command
        # line may only name the campaign and the backbone.
        probs = freeze.problems(a.campaign, a.backbone, arms, reps, splits, llm.reasoning_effort())
        if a.human_error_rate or a.instances != "all" or a.templates != "all" or any(
                v is not None for v in (a.l2_threshold, a.l4_threshold, a.l5b_lo, a.monitor_role)):
            probs.append("thresholds, monitor, filters and reviewer error are fixed by the freeze block")
        if probs:
            ap.error("confirmatory campaign refused: " + "; ".join(probs))
        bb = freeze.backbone_config(a.backbone)
        cfg = {"agent_role": bb["agent_role"], "monitor_role": bb["monitor_role"], "l2_threshold": bb["t2"],
               "l4_threshold": bb["t4"], "l5b_lo": bb["l5b_lo"], "human_error_rate": 0.0}
        # Serving guard is mandatory: the frozen realised strings.
        os.environ["MAFIA_EXPECT_REALISED_MODEL" + (f"_{bb['agent_role'].upper()}" if bb["agent_role"] else "")] = \
            bb["realised_model"]
        os.environ[f"MAFIA_EXPECT_REALISED_MODEL_{bb['monitor_role'].upper()}"] = bb["monitor_realised_model"]
    check_roles(arms, cfg)

    tasks = [t for t in build_tasks() if t.split in splits]
    if a.instances != "all":
        want = {f"-{int(x)}" for x in a.instances.split(",")}
        tasks = [t for t in tasks if any(t.pair_id.endswith(w) for w in want)]
    if a.templates != "all":
        pre = tuple(x.strip() for x in a.templates.split(","))
        tasks = [t for t in tasks if t.template_id.startswith(pre)]

    out_dir = os.path.join("logs", "runs", a.campaign)
    os.makedirs(out_dir, exist_ok=True)
    ep_path = os.path.join(out_dir, "episodes.parquet")
    jl_path = os.path.join(out_dir, "episodes.jsonl")
    infra_path = os.path.join(out_dir, "infra_failures.jsonl")
    if os.path.exists(ep_path) and not os.path.exists(jl_path):   # a bundle written before the JSONL format
        for r in pd.read_parquet(ep_path).to_dict("records"):
            append_row(jl_path, r)
    done = done_ids(jl_path)
    gave_up = {r["episode_id"] for r in read_rows(infra_path) if r.get("attempt", 1) >= 2}
    manifest = {"campaign": a.campaign, "started_at": datetime.now(timezone.utc).isoformat(),
                "git_sha": _git_sha(), "task_set_version": TASK_SET_VERSION,
                "task_set_sha256": task_set_sha256(), "arms": arms, "splits": sorted(splits),
                "reps": reps, "n_tasks": len(tasks), "lane_cap_inr": a.lane_cap,
                "episode_bound_inr": EPISODE_BOUND_INR, "max_steps": MAX_STEPS,
                "requested_model": settings.model, "base_url": settings.base_url,
                "max_tokens": settings.max_tokens, "agent_temperature": AGENT_TEMPERATURE,
                "scorer_temperature": SCORER_TEMPERATURE, "reasoning_effort": llm.reasoning_effort(),
                "sdk_max_retries": llm.SDK_MAX_RETRIES, "http_timeout_s": llm.HTTP_TIMEOUT_S,
                "client_max_attempts": llm.MAX_ATTEMPTS,
                "expected_realised_model": llm.expected_realised_model(cfg.get("agent_role")),
                "expected_monitor_model": (llm.expected_realised_model(cfg["monitor_role"])
                                           if cfg.get("monitor_role") else None),
                "backbone": a.backbone, "cfg": cfg, "confirmatory": not nonconf,
                "runpath_sha256": freeze.runpath_sha256(), "prompts_sha256": freeze.prompts_sha256()}
    with open(os.path.join(out_dir, f"manifest-{int(time.time())}.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    ledger = ra._ledger_path(None)
    jobs = []
    for rep in reps:
        for t in tasks:
            for arm in arms:
                eid = f"{a.campaign}-{t.task_id}-{arm}-r{rep}"
                if eid not in done and eid not in gave_up:
                    jobs.append({"campaign": a.campaign, "task_id": t.task_id, "arm": arm, "rep": rep,
                                 "episode_id": eid, "cfg": cfg, "attempt": 1,
                                 "raw_dir": os.path.join(out_dir, "raw", eid)})

    def campaign_spend():
        return sum(float(e.get("cost_inr") or 0) for e in ra._ledger_entries(ledger)
                   if e.get("campaign") == a.campaign)

    print(f"[{a.campaign}] {len(jobs)} episodes to run ({len(done)} done); ledger Rs.{ra._ledger_total(ledger):.2f}",
          flush=True)
    n_ok, inflight, stop = 0, {}, False
    ex = ProcessPoolExecutor(max_workers=max(1, a.workers))
    try:
        while (jobs and not stop) or inflight:
            while jobs and not stop and len(inflight) < a.workers:
                need = EPISODE_BOUND_INR * (len(inflight) + 1)
                if campaign_spend() + need > a.lane_cap or ra._ledger_total(ledger) + need > ra.PREREG_BUDGET_CAP:
                    print(f"[{a.campaign}] cap projection reached; no new episodes.", flush=True)
                    stop = True
                    break
                job = jobs.pop(0)
                inflight[ex.submit(_episode_worker, job)] = job
            if not inflight:
                break
            fin, _ = wait(list(inflight), return_when=FIRST_COMPLETED)
            for f in fin:
                job = inflight.pop(f)
                status, row = "kept", None
                try:
                    row = f.result()
                except Exception as e:  # billing, serving drift, crash: spend is still ledgered
                    kind = type(e).__name__
                    print(f"[{a.campaign}] episode failed {job['episode_id']}: {kind}: {str(e)[:200]}", flush=True)
                    status = "discarded"
                    if kind in ("BillingExhausted", "ServingDrift"):
                        stop = True
                cost = ra._raw_spend(job["raw_dir"])
                ra._append_ledger(ledger, {"run_tag": a.campaign, "campaign": a.campaign,
                                           "game_id": job["episode_id"], "requested_seed": job["rep"],
                                           "arm": job["arm"], "billed_cost_inr": cost, "est_cost_inr": cost},
                                  campaign=a.campaign, status=status, source="irrevops")
                if row is None:
                    continue
                if row.get("infra_failed"):
                    # Pre-reg v3 SS7: re-run once in a fresh raw directory;
                    # a second failure leaves the cell missing and listed.
                    append_row(infra_path, row)
                    if job.get("attempt", 1) < 2 and not stop:
                        jobs.append(dict(job, attempt=2, raw_dir=job["raw_dir"] + "-a2"))
                    continue
                row.update({"campaign": a.campaign, "rep": job["rep"], "cost_inr": round(cost, 6),
                            "git_sha": manifest["git_sha"], "task_set_sha256": manifest["task_set_sha256"],
                            "requested_model": settings.model, "reasoning_effort": manifest["reasoning_effort"]})
                append_row(jl_path, row)
                n_ok += 1
                print(console_line(a.campaign, row, cost, len(done) + n_ok), flush=True)
    finally:
        ex.shutdown(wait=True, cancel_futures=True)
        compact(jl_path, ep_path)
    print(f"[{a.campaign}] {n_ok} episodes this run; campaign spend Rs.{campaign_spend():.4f}; "
          f"ledger Rs.{ra._ledger_total(ledger):.2f}")


if __name__ == "__main__":
    main()
