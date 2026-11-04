"""One-call provider probe: python -m src.eval.probe [--skip-jev]

Verifies the AiCredits backbone returns text and parseable JSON, and that
the OpenRouter Jev gate returns a typed decision. Never prints secrets.
"""
import argparse
import time

from src import llm_client as llm
from src.config import settings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-jev", action="store_true")
    args = ap.parse_args()

    print(f"LLM provider={settings.provider} model={settings.model} "
          f"base_url={settings.base_url} max_tokens={settings.max_tokens}")

    t0 = time.time()
    text = llm.chat_text("Reply with exactly: BACKBONE_OK", "ping", temperature=0.0)
    print(f"chat_text ok={bool(text)} latency={time.time()-t0:.2f}s text={text[:80]!r}")

    meta = {}
    t0 = time.time()
    data = llm.chat_json("Return JSON only.", 'Return {"ok": true} as JSON.', meta=meta)
    print(f"chat_json ok={bool(data)} latency={time.time()-t0:.2f}s "
          f"data={data} meta={meta}")

    if args.skip_jev:
        return
    if not settings.jev_api_key:
        print("jev: OpenRouterJevAPIKey missing — gate will log a stub")
        return
    from src.agents.jev_gate import jev_decide

    t0 = time.time()
    out = jev_decide("Probe: 4 alive, one suspected mafia, no votes yet.",
                     ["1", "2", "3", "no-lynch"])
    print(f"jev base_url={settings.jev_base_url} model={settings.jev_model} "
          f"latency={time.time()-t0:.2f}s stub={out.get('stub')} "
          f"noul={out.get('should_delay_noul')} choice={out.get('vote_choice')} "
          f"error={out.get('error')}")


if __name__ == "__main__":
    main()
