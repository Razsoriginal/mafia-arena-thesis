import time, json, sys
from src.config import settings
from src.eval import run_arena as ra
from src.llm_client import get_client, _est_cost_inr
from src.explore.diag_500 import build_prompts, CAMPAIGN
purpose, s, u = build_prompts(12)[int(sys.argv[1])]
mt = int(sys.argv[2])
kw = {"model": settings.model, "temperature": 0.0, "max_tokens": mt, "stream": True,
      "stream_options": {"include_usage": True},
      "messages": [{"role": "system", "content": s}, {"role": "user", "content": u}]}
t0 = time.time(); n = 0; n_reason = 0; first_any = None; first_content = None; usage = None; err = None
try:
    for ch in get_client().chat.completions.create(**kw):
        n += 1; first_any = first_any or time.time() - t0
        if getattr(ch, "usage", None): usage = ch.usage
        if ch.choices:
            d = ch.choices[0].delta
            if getattr(d, "content", None): first_content = first_content or time.time() - t0
            if getattr(d, "reasoning", None) or getattr(d, "reasoning_content", None): n_reason += 1
except Exception as e:
    err = str(e)[:200]
pt = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
ct = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
billed = getattr(usage, "cost", None) if usage else None
cost = float(billed) if billed is not None else _est_cost_inr(pt, ct)
out = {"idx": sys.argv[1], "max_tokens": mt, "latency": round(time.time() - t0, 1), "chunks": n, "reasoning_chunks": n_reason,
       "first_any_s": first_any, "first_content_s": first_content, "pt": pt, "ct": ct, "cost": cost, "err": err}
print(json.dumps(out))
open("logs/runs/loadtest-500diag/stream_probe.jsonl", "a").write(json.dumps(out) + "\n")
if cost > 0:
    ra._append_ledger(ra._ledger_path(None), {"run_tag": CAMPAIGN, "game_id": f"{CAMPAIGN}-probe-{sys.argv[1]}-{mt}",
        "billed_cost_inr": cost if billed is not None else 0.0, "est_cost_inr": cost}, campaign=CAMPAIGN, source="loadtest")
