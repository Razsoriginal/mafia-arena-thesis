"""Unified OpenAI-compatible client. Backbone = config switch.
Primary: meta/muse-spark-1.3-contributor via AiCredits. Comparative later: gpt-4o-mini, qwen3-8b, Fathom-R1-14B.
"""
import json
import time
from openai import OpenAI
from .config import settings

_client = None
COST_LOG = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}

def get_client():
    global _client
    if _client is None:
        _client = OpenAI(base_url=settings.base_url, api_key=settings.api_key)
    return _client

def chat_text(system: str, user: str, temperature: float | None = None) -> str:
    client = get_client()
    temp = settings.temp_dialogue if temperature is None else temperature
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=settings.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=temp,
                max_tokens=settings.max_tokens,
            )
            COST_LOG["calls"] += 1
            try:
                COST_LOG["prompt_tokens"] += resp.usage.prompt_tokens
                COST_LOG["completion_tokens"] += resp.usage.completion_tokens
            except Exception:
                pass
            content = resp.choices[0].message.content or ""
            text = content.strip()
            if not text:
                raise ValueError("empty content (reasoning model needs higher max_tokens)")
            return text
        except Exception:
            if attempt == 2:
                return ""
            time.sleep(2 * (attempt + 1))
    return ""

def chat_json(system: str, user: str) -> dict:
    """JSON mode with repair. Falls back to safe DELAY default."""
    raw = chat_text(system + "\nReply with valid JSON only.", user, temperature=settings.temp_json)
    try:
        # strip markdown fences
        if "```" in raw:
            raw = raw.split("```")[1]
            raw = raw.replace("json", "", 1).strip()
        return json.loads(raw[raw.find("{"):raw.rfind("}")+1])
    except Exception:
        # repair pass with same backbone
        try:
            fix = chat_text("Fix to valid JSON. Reply JSON only.", raw, temperature=0.0)
            return json.loads(fix[fix.find("{"):fix.rfind("}")+1])
        except Exception:
            return {}
