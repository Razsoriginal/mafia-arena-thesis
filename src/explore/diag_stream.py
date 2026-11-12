"""EXPLORATORY: does streaming avoid the ~90s gateway 500 on long
generations? Replays diag_500 prompts with stream=True (same model,
temperature, max_tokens, messages). Ledgered under loadtest-500diag.
Usage: python -m src.explore.diag_stream --idx 2 --fmt plain --temp 0.0
"""
import argparse, json, os, time
from src.config import settings
from src.eval import run_arena as ra
from src.llm_client import get_client, _est_cost_inr
from src.explore.diag_500 import build_prompts, CAMPAIGN


def stream_call(system, user, fmt, temp, max_tokens):
    kw = {"model": settings.model, "temperature": temp, "max_tokens": max_tokens, "stream": True,
          "stream_options": {"include_usage": True},
          "messages": [{"role": "system", "content": system + ("\nReply with valid JSON only." if fmt == "json" else "")},
                       {"role": "user", "content": user}]}
    if fmt == "json":
        kw["response_format"] = {"type": "json_object"}
    t0 = time.time(); parts = []; usage = None; model = None; first = None
    try:
        for ch in get_client().chat.completions.create(**kw):
            model = getattr(ch, "model", model)
            if getattr(ch, "usage", None):
                usage = ch.usage
            if ch.choices:
                d = ch.choices[0].delta
                piece = getattr(d, "content", None)
                if piece:
                    first = first or (time.time() - t0)
                    parts.append(piece)
        text = "".join(parts).strip()
        pt = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
        ct = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
        billed = getattr(usage, "cost", None) if usage else None
        cost = float(billed) if billed is not None else _est_cost_inr(pt, ct)
        return {"ok": bool(text), "error": None if text else "empty", "latency_s": time.time() - t0,
                "first_content_s": first, "pt": pt, "ct": ct, "cost_inr": cost, "billed": billed is not None,
                "usage_present": usage is not None, "model": model, "content_len": len(text)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "latency_s": time.time() - t0, "pt": 0, "ct": 0,
                "cost_inr": 0.0, "billed": False, "usage_present": False, "content_len": 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--idx", type=int, nargs="+", default=[2])
    ap.add_argument("--fmt", default="plain"); ap.add_argument("--temp", type=float, default=0.0)
    ap.add_argument("--out", default="logs/runs/loadtest-500diag")
    a = ap.parse_args()
    ledger = ra._ledger_path(None)
    prompts = build_prompts(12)
    for i in a.idx:
        if ra._ledger_total(ledger) + _est_cost_inr(4000, 4000) > ra.PREREG_BUDGET_CAP:
            print("global cap"); return
        purpose, s, u = prompts[i]
        r = stream_call(s, u, a.fmt, a.temp, settings.max_tokens)
        r.update({"i": i, "purpose": purpose, "fmt": a.fmt, "temp": a.temp, "stream": True, "ts": time.time()})
        with open(os.path.join(a.out, "stream_calls.jsonl"), "a") as f:
            f.write(json.dumps(r, default=str) + "\n")
        if r["cost_inr"] > 0:
            ra._append_ledger(ledger, {"run_tag": CAMPAIGN, "game_id": f"{CAMPAIGN}-stream-{i}-{a.fmt}-{a.temp}",
                                       "requested_seed": None, "arm": None,
                                       "billed_cost_inr": r["cost_inr"] if r["billed"] else 0.0,
                                       "est_cost_inr": r["cost_inr"]}, campaign=CAMPAIGN, status="kept", source="loadtest")
        print(json.dumps(r, default=str))


if __name__ == "__main__":
    main()
