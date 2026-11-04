"""Unified OpenAI-compatible client for the AiCredits backbone.

Every response is logged to logs/raw/llm_raw.jsonl; retries and parse
failures go to logs/raw/llm_errors.jsonl so an empty response is auditable
instead of silently becoming a safe default.
"""
import json
import os
import time

from openai import OpenAI

from .config import settings

class BillingExhausted(RuntimeError):
    """Raised when the provider reports 402 / insufficient balance."""


_client = None
COST_LOG = {
    "calls": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "json_failures": 0,
}


def _raw_dir() -> str:
    return os.getenv("MAFIA_RAW_DIR", "logs/raw")


def _log_jsonl(name: str, payload: dict):
    try:
        os.makedirs(_raw_dir(), exist_ok=True)
        with open(os.path.join(_raw_dir(), name), "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, default=str) + "\n")
    except Exception:
        pass


def _log_raw(fn: str, raw: str):
    _log_jsonl("llm_raw.jsonl", {
        "ts": time.time(),
        "run_tag": os.getenv("MAFIA_RUN_TAG", ""),
        "fn": fn,
        "provider": settings.provider,
        "model": settings.model,
        "base_url": settings.base_url,
        "raw": (raw or "")[:4000],
    })


def _log_error(fn: str, error, raw: str = ""):
    _log_jsonl("llm_errors.jsonl", {
        "ts": time.time(),
        "run_tag": os.getenv("MAFIA_RUN_TAG", ""),
        "fn": fn,
        "provider": settings.provider,
        "model": settings.model,
        "error": str(error)[:500],
        "raw": (raw or "")[:2000],
    })


def _content(resp) -> str:
    """The assistant's answer. Reasoning text is never a usable answer."""
    msg = resp.choices[0].message
    return (getattr(msg, "content", None) or "").strip()


def _reasoning(resp) -> str:
    msg = resp.choices[0].message
    for attr in ("reasoning_content", "reasoning"):
        alt = getattr(msg, attr, None)
        if isinstance(alt, str) and alt.strip():
            return alt.strip()
    return ""


def get_client():
    global _client
    if _client is None:
        _client = OpenAI(base_url=settings.base_url, api_key=settings.api_key)
    return _client


def chat_text(system: str, user: str, temperature: float | None = None,
              log: bool = True, response_format: dict | None = None) -> str:
    client = get_client()
    temp = settings.temp_dialogue if temperature is None else temperature
    use_format = response_format
    max_tokens = settings.max_tokens
    for attempt in range(3):
        try:
            kwargs = {
                "model": settings.model,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}],
                "temperature": temp,
                "max_tokens": max_tokens,
            }
            if use_format:
                kwargs["response_format"] = use_format
            resp = client.chat.completions.create(**kwargs)
            COST_LOG["calls"] += 1
            try:
                COST_LOG["prompt_tokens"] += resp.usage.prompt_tokens
                COST_LOG["completion_tokens"] += resp.usage.completion_tokens
            except Exception:
                pass
            reasoning = _reasoning(resp)
            if reasoning:
                # Audit only: reasoning is never used as the answer.
                _log_raw("reasoning", reasoning)
            text = _content(resp)
            if not text:
                raise ValueError(f"empty content (max_tokens={max_tokens})")
            if log:
                _log_raw("chat_text", text)
            return text
        except Exception as e:
            _log_error("chat_text", e)
            text_err = str(e).lower()
            if "402" in text_err or "insufficient balance" in text_err:
                # Never retry a payment failure: it silently turns every
                # remaining game into a fallback-delay draw.
                raise BillingExhausted(str(e)) from e
            if use_format and "response_format" in text_err:
                use_format = None  # provider without JSON mode: retry plain
                continue
            if "empty content" in str(e) and max_tokens < 4000:
                # Reasoning models can spend the whole budget before answering.
                max_tokens = min(4000, max_tokens + 1000)
                continue
            if attempt == 2:
                return ""
            time.sleep(2 * (attempt + 1))
    return ""


def _parse_json(raw: str):
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    if "```" in text:
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        text = text.lstrip()
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except Exception:
        return None


def chat_json(system: str, user: str, meta: dict | None = None) -> dict:
    """JSON mode with one repair pass. Falls back to {} (safe DELAY).

    meta receives parse_fail / repaired / empty_raw / error so callers can
    separate a genuine decision from a parse failure.
    """
    if meta is not None:
        meta.clear()
        meta.update({"parse_fail": False, "repaired": False,
                     "empty_raw": False, "error": None, "raw_len": 0})

    json_format = {"type": "json_object"}
    raw = chat_text(system + "\nReply with valid JSON only.", user,
                    temperature=settings.temp_json, log=False,
                    response_format=json_format)
    _log_raw("chat_json", raw)
    if meta is not None:
        meta["raw_len"] = len(raw)
    if not raw.strip():
        COST_LOG["json_failures"] += 1
        if meta is not None:
            meta.update({"parse_fail": True, "empty_raw": True,
                         "error": "empty content"})
        return {}

    parsed = _parse_json(raw)
    if parsed is not None:
        return parsed

    fix_system = (system + "\nReturn ONLY a JSON object matching the requested schema. "
                  "No prose, no reasoning, no markdown.")
    fix_user = (f"{user}\n\nYour previous reply was not valid JSON:\n{raw[:1200]}\n\n"
                "Return the correct JSON object now.")
    fix = chat_text(fix_system, fix_user, temperature=0.0, log=False,
                    response_format=json_format)
    _log_raw("chat_json_repair", fix)
    parsed = _parse_json(fix)
    if parsed is not None:
        if meta is not None:
            meta["repaired"] = True
        return parsed

    COST_LOG["json_failures"] += 1
    _log_error("chat_json", "unparseable JSON", raw)
    if meta is not None:
        meta.update({"parse_fail": True, "error": "unparseable JSON"})
    return {}
