"""Part 2: V0-V5 probes + persistence under the post-change string.

V0 frozen (JSON, t=0.0, 2500); V1 JSON flag off (suffix kept), t=0.0, 2500;
V2 JSON on, t=0.3, 2500; V3 JSON on, t=0.0, max_tokens=1500;
V4 V0 + reasoning-effort minimal (acceptance pre-probe picks the spelling);
V5 V0 + one brief-deliberation line (prompt-level, flagged).
8 contexts x variants x 2 reps, seeded-shuffled, max_retries=0, timeout=150.
Persistence: up to 6 V0-failed contexts x (3x V0 + 3x V2).

Budgets: Part 2 <= Rs.5 (drop V5, then V3, when near); grand total <= Rs.6.
Every paid call ledgered (campaign retest-b1, source retry-test).
Amended rule 5: record realised string, never stop on it.

Usage: MAFIA_SPEND_LEDGER=/abs/main/logs/spend_ledger.jsonl \
         .venv/bin/python scripts/run_part2.py --run
"""
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.normpath(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI, APITimeoutError  # noqa: E402

from rebuild_prompts import rebuild_night  # noqa: E402
from run_part1 import _exc_headers, _usage_cost, raw_create  # noqa: E402
from run_probes import select_contexts  # noqa: E402
from src.config import settings  # noqa: E402
from src.eval import run_arena as ra  # noqa: E402
from src.llm_client import _error_class, _parse_json  # noqa: E402

CAMPAIGN = "retest-b1"
SOURCE = "retry-test"
FROZEN_MODEL = "meta/muse-spark-1.3-contributor"
FROZEN_BASE = "https://aicredits.in/v1"
P2_CAP = 5.0
TOTAL_CAP = 6.0
BOUND = 0.12  # above every per-call cost observed in calibration (max 0.0946)
MAX_INFLIGHT = 4
SHUFFLE_SEED = 11
OUT = "logs/retest-b1"
V5_LINE = "\nDeliberate briefly (a few key points only) before answering."

CONDS = {
    "V0": {"fmt": "json", "temp": 0.0, "max_tokens": 2500},
    "V1": {"fmt": "plain", "temp": 0.0, "max_tokens": 2500},
    "V2": {"fmt": "json", "temp": 0.3, "max_tokens": 2500},
    "V3": {"fmt": "json", "temp": 0.0, "max_tokens": 1500},
    "V5": {"fmt": "json", "temp": 0.0, "max_tokens": 2500, "v5_line": True},
}
CORE = ["V0", "V1", "V2", "V4"]  # never dropped (V4 appended after acceptance)


def build_kw(ctx, cond):
    kw = {"model": settings.model, "temperature": cond["temp"],
          "max_tokens": cond["max_tokens"],
          "messages": [{"role": "system", "content": ctx["system"]},
                       {"role": "user", "content": ctx["user"] +
                        (V5_LINE if cond.get("v5_line") else "")}]}
    if cond["fmt"] == "json":
        kw["response_format"] = {"type": "json_object"}
    if cond.get("effort") == "kwarg":
        kw["reasoning_effort"] = "minimal"
    elif cond.get("effort") == "extra_body":
        kw["extra_body"] = {"reasoning": {"effort": "minimal"}}
    return kw


def one_call(client, ctx, cond_name, cond, rep, tag):
    kw = build_kw(ctx, cond)
    label = f"{ctx['kind']}/{ctx['game_id']}/day{ctx['day']}/{ctx['action'] or ctx['pid']}"
    rec = {"phase": tag, "ctx": label, "kind": ctx["kind"], "cond": cond_name,
           "rep": rep, "ts": time.time(), "requested_model": settings.model,
           "params": {"fmt": cond["fmt"], "temp": cond["temp"],
                      "max_tokens": cond["max_tokens"],
                      "effort": cond.get("effort"), "v5_line": bool(cond.get("v5_line"))}}
    t0 = time.time()
    try:
        parsed, headers, exc = raw_create(client, kw)
    except TypeError as e:
        # client-side kwarg rejection (e.g. reasoning_effort unsupported)
        return {**rec, "ok": False, "error": f"TypeError: {e}"[:300],
                "error_class": "client_type_error", "http_status": None,
                "headers": {}, "latency_s": round(time.time() - t0, 3),
                "realised_model": None, "pt": 0, "ct": 0, "cost_inr": 0.0,
                "transport": "rejected-client"}
    dt = time.time() - t0
    rec["latency_s"] = round(dt, 3)
    rec["headers"] = headers
    if exc is not None:
        body = ""
        try:
            r = getattr(exc, "response", None)
            if r is not None:
                body = r.text[:2000]
        except Exception:
            pass
        rec.update({"ok": False, "error": str(exc)[:300],
                    "error_class": _error_class(exc),
                    "is_timeout": isinstance(exc, APITimeoutError),
                    "http_status": getattr(exc, "status_code", None),
                    "error_body": body, "realised_model": None,
                    "pt": 0, "ct": 0, "cost_inr": 0.0, "transport": "http-error"})
        return rec
    pt, ct, cost, billed, usage = _usage_cost(parsed.usage)
    text = (parsed.choices[0].message.content or "").strip()
    p = _parse_json(text)
    target = None
    if isinstance(p, dict) and ctx["kind"] == "night" and ctx["action"] in p:
        target = str(p[ctx["action"]])
    rec.update({"ok": True, "error": None, "error_class": None,
                "realised_model": getattr(parsed, "model", None),
                "resp_id": getattr(parsed, "id", None),
                "fingerprint": getattr(parsed, "system_fingerprint", None),
                "pt": pt, "ct": ct, "usage": usage, "cost_inr": cost,
                "billed": billed, "content_len": len(text),
                "empty": not bool(text), "parse_ok": p is not None,
                "target": target, "toks": round(ct / dt, 1) if dt > 0 else None,
                "transport": "ok", "raw": text[:4000]})
    return rec


class Runner:
    def __init__(self, ledger, base_spent):
        self.ledger = ledger
        self.base = base_spent
        self.spent = 0.0
        self.done = 0
        self.total_jobs = 0
        self.paths = {t: os.path.join(OUT, f"{t}.jsonl")
                      for t in ("part2_accept", "part2", "part2_persist")}

    def handle(self, rec, tag):
        path = self.paths[tag]
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        if rec["cost_inr"] > 0:
            self.spent += rec["cost_inr"]
            ra._append_ledger(
                self.ledger, {"run_tag": CAMPAIGN,
                              "game_id": f"{CAMPAIGN}-{tag}-{rec['ctx']}-{rec['cond']}-r{rec['rep']}",
                              "requested_seed": None, "arm": None,
                              "billed_cost_inr": rec["cost_inr"] if rec["billed"] else 0.0,
                              "est_cost_inr": rec["cost_inr"]},
                campaign=CAMPAIGN, status="kept", source=SOURCE)
        self.done += 1
        print(f"[{self.done}/{self.total_jobs}] {tag} {rec['ctx']} {rec['cond']} "
              f"ok={rec['ok']} err={rec['error_class']} lat={rec['latency_s']} "
              f"ct={rec['ct']} cost={rec['cost_inr']:.4f} p2spent={self.spent:.4f} "
              f"model={rec['realised_model']}", flush=True)

    def over_p2(self, inflight=0):
        return self.spent + BOUND * (inflight + 1) > P2_CAP

    def over_total(self, inflight=0):
        return self.base + self.spent + BOUND * (inflight + 1) > TOTAL_CAP


def run_window(ex, jobs, handle, halt):
    """Sliding window (<=4 in flight); halt() checked before each submit;
    pending always drained + handled (completed work is ledgered)."""
    pending, it = {}, iter(jobs)
    exhausted = False
    while True:
        while len(pending) < MAX_INFLIGHT and not exhausted:
            if halt(len(pending)):
                exhausted = True
                break
            try:
                job = next(it)
            except StopIteration:
                exhausted = True
                break
            fut = ex.submit(job[0], *job[1:])
            pending[fut] = job
        if not pending:
            return
        done, _ = wait(set(pending), return_when=FIRST_COMPLETED)
        for fut in done:
            pending.pop(fut)
            handle(fut.result())


def acceptance(client, ru):
    """V4 spelling probe on one cheap context + V0 reference. Sequential."""
    nights, _ = rebuild_night("mvp-team-01-5000-dmn_village")
    save = [b for b in nights[0] if b["action"] == "save"][0]
    ctx = {"kind": "night", "game_id": "mvp-team-01-5000-dmn_village",
           "day": 0, "action": "save", "pid": save["pid"],
           "system": save["system"], "user": save["user"]}
    v0 = dict(CONDS["V0"])
    recs = [one_call(client, ctx, "V0-ref", v0, 0, "part2_accept")]
    ru.handle(recs[0], "part2_accept")
    va = dict(CONDS["V0"], effort="kwarg")
    recs.append(one_call(client, ctx, "V4a-kwarg", va, 0, "part2_accept"))
    ru.handle(recs[1], "part2_accept")
    vb = dict(CONDS["V0"], effort="extra_body")
    recs.append(one_call(client, ctx, "V4b-extrabody", vb, 0, "part2_accept"))
    ru.handle(recs[2], "part2_accept")
    verdict = {}
    for r in recs[1:]:
        if r["error_class"] == "client_type_error":
            verdict[r["cond"]] = "rejected-client"
        elif not r["ok"] and r["http_status"] == 400:
            verdict[r["cond"]] = "rejected-server-400"
        elif r["ok"]:
            verdict[r["cond"]] = "accepted-200"
        else:
            verdict[r["cond"]] = f"inconclusive-{r['error_class']}"
    print(f"V4 acceptance: {verdict}")
    return verdict


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", required=True)
    ap.parse_args()
    assert settings.model == FROZEN_MODEL, settings.model
    assert settings.base_url == FROZEN_BASE, settings.base_url
    assert settings.api_key, "no API key in environment"
    ledger = ra._ledger_path(None)
    assert os.path.isabs(ledger) and "mafia-arena-thesis" in ledger, ledger
    os.makedirs(OUT, exist_ok=True)
    for t in ("part2_accept", "part2", "part2_persist"):
        p = os.path.join(OUT, f"{t}.jsonl")
        if os.path.exists(p):
            raise SystemExit(f"{p} exists; refusing to append (re-run safety)")

    contexts = select_contexts()
    flat = [c for grp in contexts for c in grp]
    assert len(flat) == 8, len(flat)
    old = json.load(open(os.path.join(OUT, "contexts.json"), encoding="utf-8"))["contexts"]
    assert [(c["kind"], c["game_id"], c["day"]) for c in flat] == \
           [(c["kind"], c["game_id"], c["day"]) for c in old], "context drift!"
    print("8 contexts identical to phase 1 (verified).")
    with open(os.path.join(OUT, "part2_contexts.json"), "w", encoding="utf-8") as f:
        json.dump({"contexts": flat}, f)

    base = sum(float(r.get("cost_inr") or 0)
               for r in ra._ledger_entries(ledger) if r.get("campaign") == CAMPAIGN)
    print(f"model={settings.model} base={settings.base_url}")
    print(f"shared ledger total Rs.{ra._ledger_total(ledger):.2f}; "
          f"retest-b1 so far Rs.{base:.4f}; P2 cap Rs.{P2_CAP}, total cap Rs.{TOTAL_CAP}")
    ru = Runner(ledger, base)
    client = OpenAI(api_key=settings.api_key, base_url=settings.base_url,
                    max_retries=0, timeout=150.0)

    verdict = acceptance(client, ru)
    conds = dict(CONDS)
    if verdict.get("V4a-kwarg") == "accepted-200":
        conds["V4"] = dict(CONDS["V0"], effort="kwarg")
    elif verdict.get("V4b-extrabody") == "accepted-200":
        conds["V4"] = dict(CONDS["V0"], effort="extra_body")
    else:
        print("V4 skipped: neither spelling accepted.")
    order = [c for c in ["V0", "V1", "V2", "V3", "V4", "V5"] if c in conds]
    plan = [(ci, cn, rep) for ci in range(8) for cn in order for rep in range(2)]
    random.Random(SHUFFLE_SEED).shuffle(plan)
    ru.total_jobs = len(plan) + 3 + 36  # main + acceptance + persistence max
    print(f"main plan: {len(plan)} calls ({' '.join(order)}); "
          f"est Rs.{sum(0.035 if flat[ci]['kind']=='night' else 0.051 for ci,_,_ in plan):.2f}")

    drop_v5 = drop_v3 = False
    ex = ThreadPoolExecutor(max_workers=MAX_INFLIGHT)

    def jobs():
        nonlocal drop_v5, drop_v3
        for idx, (ci, cn, rep) in enumerate(plan):
            rest = plan[idx + 1:]
            if cn == "V5" and not drop_v5:
                core_left = sum(1 for _, c, _ in rest if c in ("V0", "V1", "V2", "V3", "V4"))
                if ru.spent + BOUND * (core_left + 1) > P2_CAP:
                    drop_v5 = True
                    print("near cap: dropping V5 from here on")
            if cn == "V3" and not drop_v3:
                core_left = sum(1 for _, c, _ in rest if c in ("V0", "V1", "V2", "V4"))
                if ru.spent + BOUND * (core_left + 1) > P2_CAP:
                    drop_v3 = True
                    print("near cap: dropping V3 from here on")
            if (cn == "V5" and drop_v5) or (cn == "V3" and drop_v3):
                ru.total_jobs -= 1
                continue
            yield (one_call, client, flat[ci], cn, conds[cn], rep, "part2")

    run_window(ex, jobs(),
               lambda r: ru.handle(r, "part2"),
               lambda inf: ru.over_p2(inf) or ru.over_total(inf))
    print(f"main done: p2spent Rs.{ru.spent:.4f} (V5 dropped: {drop_v5}, V3 dropped: {drop_v3})")

    # persistence: up to 6 V0-failed contexts x (3x V0 + 3x V2)
    v0recs = {}
    with open(ru.paths["part2"], encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r["cond"] == "V0":
                v0recs.setdefault(r["ctx"], []).append(r)
    scored = []
    for ctx, rs in v0recs.items():
        http = sum(1 for r in rs if not r["ok"])
        empty = sum(1 for r in rs if r["ok"] and r["empty"])
        bad = sum(1 for r in rs if r["ok"] and not r["empty"] and not r["parse_ok"])
        if http + empty + bad > 0:
            scored.append((http, empty, bad, ctx))
    scored.sort(key=lambda t: (-t[0], -t[1], -t[2]))
    targets = [ctx for _, _, _, ctx in scored[:6]]
    print(f"persistence targets ({len(targets)}): {targets}")
    pj = []
    for ctx in targets:
        c = next(c for c in flat
                 if f"{c['kind']}/{c['game_id']}/day{c['day']}/{c['action'] or c['pid']}" == ctx)
        seq = ["V0", "V2"] * 3
        random.Random(13).shuffle(seq)
        for k, cn in enumerate(seq):
            pj.append((one_call, client, c, cn, conds[cn], k, "part2_persist"))
    ru.total_jobs = ru.done + len(pj)
    run_window(ex, iter(pj),
               lambda r: ru.handle(r, "part2_persist"),
               lambda inf: ru.over_p2(inf) or ru.over_total(inf))
    ex.shutdown()
    print(f"\nPart 2 done: p2spent Rs.{ru.spent:.4f}; "
          f"retest-b1 total Rs.{base + ru.spent:.4f}; "
          f"ledger total Rs.{ra._ledger_total(ledger):.2f}")


if __name__ == "__main__":
    main()
