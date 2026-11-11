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
    "cost_inr": 0.0,
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


PURPOSES = {"speak", "dmn_reason", "tpn_reason", "night", "vote",
            "probe", "repair", "judge"}
# AiCredits catalog rates (USD/token) + INR/USD, billing markup 1.10.
# Duplicated from run_arena so per-call estimates do not need an import.
_MUSE_IN, _MUSE_OUT, _INR_PER_USD, _BILLING_MARKUP = 1e-07, 2e-07, 94.834253, 1.10


def _est_cost_inr(prompt_tokens, completion_tokens) -> float:
    try:
        return round((int(prompt_tokens or 0) * _MUSE_IN
                      + int(completion_tokens or 0) * _MUSE_OUT)
                     * _INR_PER_USD * _BILLING_MARKUP, 6)
    except Exception:
        return 0.0


def _log_raw(fn: str, raw: str, temperature=None, max_tokens=None,
             attempt=None, repair: bool = False, escalated: bool = False,
             realised_model=None, purpose=None, prompt_tokens=0,
             completion_tokens=0, cost_inr=0.0, cost_estimated: bool = False,
             error=None):
    _log_jsonl("llm_raw.jsonl", {
        "ts": time.time(),
        "run_tag": os.getenv("MAFIA_RUN_TAG", ""),
        "fn": fn,
        "provider": settings.provider,
        "model": settings.model,
        "requested_model": settings.model,
        "realised_model": realised_model,
        "resp_model": realised_model,
        "base_url": settings.base_url,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "attempt": attempt,
        "repair": bool(repair),
        "escalated": bool(escalated),
        "purpose": purpose if purpose in PURPOSES else "speak",
        "prompt_tokens": int(prompt_tokens or 0),
        "completion_tokens": int(completion_tokens or 0),
        "cost_inr": float(cost_inr or 0.0),
        "cost_estimated": bool(cost_estimated),
        "error": (str(error)[:300] if error else None),
        "raw": (raw or "")[:4000],
    })


def _log_error(fn: str, error, raw: str = "", temperature=None,
               max_tokens=None, attempt=None):
    _log_jsonl("llm_errors.jsonl", {
        "ts": time.time(),
        "run_tag": os.getenv("MAFIA_RUN_TAG", ""),
        "fn": fn,
        "provider": settings.provider,
        "model": settings.model,
        "requested_model": settings.model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "attempt": attempt,
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
              log: bool = True, response_format: dict | None = None,
              purpose: str | None = None, repair: bool = False) -> str:
    # `log` is kept for call compatibility only: every attempt always
    # writes its own raw row (G1). There is no silent log=False path.
    client = get_client()
    temp = settings.temp_dialogue if temperature is None else temperature
    use_format = response_format
    max_tokens = settings.max_tokens
    initial_max_tokens = max_tokens
    resolved_purpose = "repair" if repair else (purpose or "speak")
    # 5 attempts: long games hit transient connection errors often enough
    # that 3 attempts silently turns a vote into a fallback delay.
    # Retry/repair/escalation behaviour is pilot-consistent and is logged
    # per call (see _log_raw); it is not part of the first-attempt
    # temperature contract. See docs/PREREGISTRATION.md §8.
    for attempt in range(5):
        escalated = max_tokens != initial_max_tokens
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
            pt = ct = 0
            billed = None
            try:
                pt = int(resp.usage.prompt_tokens or 0)
                ct = int(resp.usage.completion_tokens or 0)
                COST_LOG["prompt_tokens"] += pt
                COST_LOG["completion_tokens"] += ct
                billed = getattr(resp.usage, "cost", None)
                if billed is not None:
                    COST_LOG["cost_inr"] += float(billed)
            except Exception:
                pass
            realised = getattr(resp, "model", None)
            if billed is not None:
                call_cost, cost_est = float(billed), False
            else:
                call_cost, cost_est = _est_cost_inr(pt, ct), True
            text = _content(resp)
            # One raw row per underlying attempt, written even when the
            # content is empty and the attempt will be retried (G1).
            _log_raw("chat_text", text, temperature=temp,
                     max_tokens=max_tokens, attempt=attempt, repair=repair,
                     escalated=escalated, realised_model=realised,
                     purpose=resolved_purpose, prompt_tokens=pt,
                     completion_tokens=ct, cost_inr=call_cost,
                     cost_estimated=cost_est)
            if not text:
                raise ValueError(f"empty content (max_tokens={max_tokens})")
            return text
        except Exception as e:
            if "empty content" not in str(e):
                _log_raw("chat_text", "", temperature=temp,
                         max_tokens=max_tokens, attempt=attempt, repair=repair,
                         escalated=escalated, realised_model=None,
                         purpose=resolved_purpose, error=e)
            _log_error("chat_text", e, temperature=temp,
                       max_tokens=max_tokens, attempt=attempt)
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
                # Logged via escalated=True on the next attempt's raw record.
                max_tokens = min(4000, max_tokens + 1000)
                COST_LOG["escalations"] = COST_LOG.get("escalations", 0) + 1
                continue
            if attempt == 4:
                return ""
            time.sleep(min(16, 2 ** (attempt + 1)))
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


def chat_json(system: str, user: str, meta: dict | None = None,
              temperature: float | None = None,
              purpose: str | None = None) -> dict:
    """JSON mode with one repair pass. Falls back to {} (safe DELAY).

    meta receives parse_fail / repaired / empty_raw / error so callers can
    separate a genuine decision from a parse failure.
    """
    if meta is not None:
        meta.clear()
        meta.update({"parse_fail": False, "repaired": False,
                     "empty_raw": False, "error": None, "raw_len": 0})

    json_format = {"type": "json_object"}
    first_temp = settings.temp_json if temperature is None else temperature
    # No wrapper row: the underlying chat_text attempt rows are the audit
    # record (actual realised model, tokens, cost, purpose) (G1/G2).
    raw = chat_text(system + "\nReply with valid JSON only.", user,
                    temperature=first_temp, response_format=json_format,
                    purpose=purpose)
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
    # Repair pass stays at 0.0 (pilot-consistent). It is a repair of a
    # failed first attempt, logged with repair=True, not a fresh
    # vote-sample; see PREREGISTRATION.md §8 amendment.
    COST_LOG["repairs"] = COST_LOG.get("repairs", 0) + 1
    fix = chat_text(fix_system, fix_user, temperature=0.0,
                    response_format=json_format, purpose="repair", repair=True)
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
