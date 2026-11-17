"""Part 1: identity evidence under the post-change string.

1a: GET {base_url}/models (+headers); one small call with full response
    object + all headers; SDK version + production-client defaults.
1b: fingerprint replay: 9 exact night-0 rebuilds x 2 reps (t=0.0,
    max_tokens=2500, JSON on, max_retries=0, timeout=600).

Budget: Part 1 <= Rs.1 (hard stop). Every paid call ledgered
(campaign retest-b1, source retry-test) to MAFIA_SPEND_LEDGER.

Usage:
  .venv/bin/python scripts/run_part1.py --phase 1a   # listing + small call
  .venv/bin/python scripts/run_part1.py --phase 1b   # 18-call replay
"""
import argparse
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.normpath(os.path.dirname(os.path.abspath(__file__))))

import openai  # noqa: E402
from openai import OpenAI  # noqa: E402

from rebuild_prompts import (  # noqa: E402
    JSON_SUFFIX, _success_rows_night0, proxy_tokens, rebuild_night,
)
from src.config import settings  # noqa: E402
from src.eval import run_arena as ra  # noqa: E402
from src.llm_client import (  # noqa: E402
    _error_class, _est_cost_inr, _parse_json, get_client,
)
from src.mafia import prompts as P  # noqa: E402

CAMPAIGN = "retest-b1"
SOURCE = "retry-test"
FROZEN_MODEL = "meta/muse-spark-1.3-contributor"
FROZEN_BASE = "https://aicredits.in/v1"
P1_CAP = 1.0
BOUND = 0.12  # above every per-call cost observed in calibration (max 0.0946)
MAX_INFLIGHT = 4
OUT = "logs/retest-b1"

FP_GAMES = ["mvp-team-01-5000-dmn_village", "mvp-team-01-5200-dmn_village",
            "mvp-team-01-5600-dmn_village"]


def _client(max_retries=0, timeout=150.0):
    return OpenAI(api_key=settings.api_key, base_url=settings.base_url,
                  max_retries=max_retries, timeout=timeout)


def _ledger(ledger, game_id, cost, billed):
    ra._append_ledger(
        ledger, {"run_tag": CAMPAIGN, "game_id": game_id,
                 "requested_seed": None, "arm": None,
                 "billed_cost_inr": cost if billed else 0.0,
                 "est_cost_inr": cost},
        campaign=CAMPAIGN, status="kept", source=SOURCE)


def raw_create(client, kw):
    """(parsed_or_None, headers_dict, exc_or_None) via raw response."""
    try:
        resp = client.chat.completions.with_raw_response.create(**kw)
    except Exception as e:
        return None, _exc_headers(e), e
    try:
        parsed = resp.parse()
    except Exception as e:
        return None, dict(resp.headers), e
    return parsed, dict(resp.headers), None


def _exc_headers(e):
    try:
        r = getattr(e, "response", None)
        if r is not None:
            return dict(r.headers)
    except Exception:
        pass
    return {}


def _usage_cost(usage):
    if usage is None:
        return 0, 0, 0.0, False, {}
    try:
        dump = usage.model_dump()
    except Exception:
        dump = {}
    pt = int(getattr(usage, "prompt_tokens", 0) or 0)
    ct = int(getattr(usage, "completion_tokens", 0) or 0)
    billed = getattr(usage, "cost", None)
    if billed is not None:
        return pt, ct, float(billed), True, dump
    return pt, ct, _est_cost_inr(pt, ct), False, dump


def phase_1a(ledger):
    print(f"sdk openai-python version: {openai.__version__} (measured)")
    prod = get_client()
    print(f"production get_client(): max_retries={prod.max_retries} "
          f"timeout={prod.timeout} (measured; src/llm_client.py sets neither "
          f"explicitly — OpenAI(base_url, api_key) only)")
    c = _client(max_retries=0, timeout=60.0)
    # models listing (free)
    mresp = c.models.with_raw_response.list()
    mparsed, mheaders = mresp.parse(), dict(mresp.headers)
    mdata = mparsed.model_dump()
    with open(os.path.join(OUT, "models_list.json"), "w", encoding="utf-8") as f:
        json.dump({"headers": mheaders, "data": mdata}, f)
    entries = mdata.get("data", [])
    print(f"models listed: {len(entries)} (measured)")
    for e in entries:
        eid = e.get("id", "")
        if "muse-spark" in eid or "muse" in eid:
            print(f"  id={eid} owned_by={e.get('owned_by')} created={e.get('created')}")
    # one small call with full object + headers
    kw = {"model": settings.model, "temperature": 0.0, "max_tokens": 64,
          "messages": [{"role": "system", "content": "Reply with exactly this JSON and nothing else: {\"ok\": true}"},
                       {"role": "user", "content": "hi"}],
          "response_format": {"type": "json_object"}}
    t0 = time.time()
    parsed, headers, exc = raw_create(_client(max_retries=0, timeout=150.0), kw)
    dt = time.time() - t0
    rec = {"request": {"model": settings.model, "temperature": 0.0,
                       "max_tokens": 64, "response_format": {"type": "json_object"}},
           "latency_s": round(dt, 3), "headers": headers}
    if exc is not None:
        rec.update({"ok": False, "error": str(exc)[:500],
                    "error_class": _error_class(exc),
                    "http_status": getattr(exc, "status_code", None)})
        print(f"small call FAILED: {rec['error_class']} {rec['error'][:120]}")
    else:
        pt, ct, cost, billed, usage = _usage_cost(parsed.usage)
        rec.update({"ok": True, "response": parsed.model_dump(),
                    "res": {"model": getattr(parsed, "model", None),
                            "id": getattr(parsed, "id", None),
                            "created": getattr(parsed, "created", None),
                            "system_fingerprint": getattr(parsed, "system_fingerprint", None)},
                    "pt": pt, "ct": ct, "cost_inr": cost, "billed": billed})
        print(f"small call ok: realised={rec['res']['model']} pt={pt} ct={ct} "
              f"cost={cost:.4f} billed={billed}")
        print(f"  usage keys: {sorted(usage.keys())}")
        print(f"  response keys: {sorted(rec['response'].keys())}")
        _ledger(ledger, f"{CAMPAIGN}-p1a-small", cost, billed)
    with open(os.path.join(OUT, "part1a_small.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f)
    cal_keys = ["ts", "run_tag", "fn", "provider", "model", "requested_model",
                "realised_model", "resp_model", "base_url", "temperature",
                "max_tokens", "attempt", "repair", "escalated", "purpose",
                "prompt_tokens", "completion_tokens", "cost_inr",
                "cost_estimated", "error", "error_class", "json_mode",
                "latency_s", "backoff_s", "raw"]
    print(f"calibration row field set ({len(cal_keys)}): {cal_keys}")
    print("NEW fields captured now (not in calibration rows): response id, "
          "created, system_fingerprint, full usage dump (incl. any reasoning "
          "split), full response headers.")


def fp_contexts():
    """9 exact night-0 rebuilds + their Nov-12 logged outcomes."""
    out = []
    for gid in FP_GAMES:
        nights, _ = rebuild_night(gid)
        logged = _success_rows_night0(gid)
        for action, rb in sorted(((b["action"], b) for b in nights[0])):
            r = logged[action]
            raw = json.loads(r["raw"])
            out.append({"game_id": gid, "action": action, "pid": rb["pid"],
                        "role": rb["role"], "system": rb["system"],
                        "user": rb["user"],
                        "logged_target": str(raw[action]),
                        "logged_ct": r["completion_tokens"],
                        "logged_lat": r["latency_s"], "logged_pt": r["prompt_tokens"]})
    assert len(out) == 9, len(out)
    return out


def phase_1b(ledger):
    ctxs = fp_contexts()
    client = _client(max_retries=0, timeout=600.0)
    plan = [(ci, rep) for ci in range(9) for rep in range(2)]
    random.Random(3).shuffle(plan)
    path = os.path.join(OUT, "part1b.jsonl")
    if os.path.exists(path):
        raise SystemExit(f"{path} exists; refusing to append (re-run safety)")
    spent = 0.0

    def run_one(job):
        ci, rep = job
        ctx = ctxs[ci]
        kw = {"model": settings.model, "temperature": 0.0, "max_tokens": 2500,
              "messages": [{"role": "system", "content": ctx["system"]},
                           {"role": "user", "content": ctx["user"]}],
              "response_format": {"type": "json_object"}}
        rec = {"phase": "1b", "ctx": f"{ctx['game_id']}/{ctx['action']}",
               "rep": rep, "ts": time.time(),
               "requested_model": settings.model}
        t0 = time.time()
        parsed, headers, exc = raw_create(client, kw)
        dt = time.time() - t0
        rec["latency_s"] = round(dt, 3)
        if exc is not None:
            rec.update({"ok": False, "error": str(exc)[:300],
                        "error_class": _error_class(exc),
                        "http_status": getattr(exc, "status_code", None),
                        "headers": headers, "realised_model": None,
                        "pt": 0, "ct": 0, "cost_inr": 0.0})
        else:
            pt, ct, cost, billed, usage = _usage_cost(parsed.usage)
            text = (parsed.choices[0].message.content or "").strip()
            target = None
            p = _parse_json(text)
            if isinstance(p, dict) and ctx["action"] in p:
                target = str(p[ctx["action"]])
            rec.update({"ok": True, "error": None, "error_class": None,
                        "realised_model": getattr(parsed, "model", None),
                        "resp_id": getattr(parsed, "id", None),
                        "fingerprint": getattr(parsed, "system_fingerprint", None),
                        "pt": pt, "ct": ct, "usage": usage, "cost_inr": cost,
                        "billed": billed, "content_len": len(text),
                        "empty": not bool(text), "target": target,
                        "agree_logged": target == ctx["logged_target"],
                        "toks": round(ct / dt, 1) if dt > 0 else None,
                        "raw": text[:4000]})
        rec["logged"] = {"target": ctx["logged_target"], "ct": ctx["logged_ct"],
                         "lat": ctx["logged_lat"], "pt": ctx["logged_pt"]}
        return rec

    done = 0
    with ThreadPoolExecutor(max_workers=MAX_INFLIGHT) as ex:
        for rec in ex.map(run_one, plan):
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
            if rec["cost_inr"] > 0:
                spent += rec["cost_inr"]
                _ledger(ledger, f"{CAMPAIGN}-fp-{rec['ctx']}-r{rec['rep']}",
                        rec["cost_inr"], rec["billed"])
            done += 1
            print(f"[{done}/{len(plan)}] {rec['ctx']} r{rec['rep']} "
                  f"ok={rec['ok']} tgt={rec.get('target')} "
                  f"agree={rec.get('agree_logged')} ct={rec.get('ct')} "
                  f"lat={rec['latency_s']} cost={rec['cost_inr']:.4f} "
                  f"spent={spent:.4f}", flush=True)
            if spent + BOUND > P1_CAP:
                raise SystemExit(f"Part-1 cap guard: spent Rs.{spent:.2f}; stopping")
    print(f"done: {done} calls, Part-1 spend Rs.{spent:.4f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["1a", "1b"], required=True)
    a = ap.parse_args()
    assert settings.model == FROZEN_MODEL, settings.model
    assert settings.base_url == FROZEN_BASE, settings.base_url
    assert settings.api_key, "no API key in environment"
    ledger = ra._ledger_path(None)
    assert os.path.isabs(ledger) and "mafia-arena-thesis" in ledger, ledger
    print(f"model={settings.model} base={settings.base_url}")
    print(f"shared ledger: {ledger} total Rs.{ra._ledger_total(ledger):.2f}")
    os.makedirs(OUT, exist_ok=True)
    if a.phase == "1a":
        phase_1a(ledger)
    else:
        phase_1b(ledger)


if __name__ == "__main__":
    main()
