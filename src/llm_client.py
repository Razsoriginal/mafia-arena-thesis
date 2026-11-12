"""Unified OpenAI-compatible client for the AiCredits backbone.

Every response is logged to logs/raw/llm_raw.jsonl; retries and parse
failures go to logs/raw/llm_errors.jsonl so an empty response is auditable
instead of silently becoming a safe default.
"""
import json
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor

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


_LOCK = threading.Lock()  # COST_LOG, raw-log appends, client init (P0-S1)


def _bump(key: str, value=1):
    with _LOCK:
        COST_LOG[key] = COST_LOG.get(key, 0) + value


def call_threads() -> int:
    """Intra-game call concurrency (P0-S1). Timing only; see
    tests/test_phase0_concurrency.py for the equivalence proof."""
    try:
        return max(1, int(os.getenv("MAFIA_CALL_THREADS", "1")))
    except ValueError:
        return 1


def pmap(fn, items):
    """Order-preserving map over independent calls. Sequential at 1
    thread; the first exception (e.g. BillingExhausted) propagates."""
    items = list(items)
    n = min(call_threads(), len(items))
    if n <= 1:
        return [fn(x) for x in items]
    with ThreadPoolExecutor(max_workers=n) as ex:
        return list(ex.map(fn, items))


def _raw_dir() -> str:
    return os.getenv("MAFIA_RAW_DIR", "logs/raw")


def _log_jsonl(name: str, payload: dict):
    try:
        line = json.dumps(payload, default=str) + "\n"
        with _LOCK:
            os.makedirs(_raw_dir(), exist_ok=True)
            with open(os.path.join(_raw_dir(), name), "a", encoding="utf-8") as f:
                f.write(line)
    except Exception:
        pass


PURPOSES = {"speak", "dmn_reason", "tpn_reason", "night", "vote",
            "probe", "repair", "judge", "bridge_step", "bridge_verify"}
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


MAX_ATTEMPTS = 8
BACKOFF_BASE_S = 10.0
BACKOFF_CAP_S = 120.0
_JITTER = random.Random()  # private RNG: never touches game randomness


def _error_class(err) -> str:
    """Coarse class of one failed attempt (P0-R1)."""
    t = str(err or "").lower()
    if "empty content" in t:
        return "empty_content"
    if "402" in t or "insufficient balance" in t:
        return "http_402"
    if "error code: 500" in t:
        return "http_500"
    if "error code: 429" in t or "rate limit" in t:
        return "http_429"
    if "error code: 5" in t:
        return "http_5xx"
    if "connection" in t or "timed out" in t or "timeout" in t:
        return "connection"
    if "response_format" in t:
        return "response_format"
    return "other"


def _backoff_s(attempt: int) -> float:
    """Sleep before attempt `attempt + 1`: exponential from 10 s, cap 120 s,
    jittered in [0.5, 1.0] of the nominal value. The smoke 500s were a
    ~90 s gateway timeout during slow provider windows; the old 2-16 s
    backoff re-entered the same window."""
    nominal = min(BACKOFF_CAP_S, BACKOFF_BASE_S * (2 ** attempt))
    return round(nominal * _JITTER.uniform(0.5, 1.0), 3)


def _log_raw(fn: str, raw: str, temperature=None, max_tokens=None,
             attempt=None, repair: bool = False, escalated: bool = False,
             realised_model=None, purpose=None, prompt_tokens=0,
             completion_tokens=0, cost_inr=0.0, cost_estimated: bool = False,
             error=None, latency_s=None, backoff_s=0.0, error_class=None,
             json_mode=None):
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
        "error_class": error_class,
        "json_mode": json_mode,
        "latency_s": (round(float(latency_s), 3) if latency_s is not None else None),
        "backoff_s": float(backoff_s or 0.0),
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
        with _LOCK:
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
    # P0-R1: up to MAX_ATTEMPTS; transient errors back off 10 s * 2^k
    # (cap 120 s, jittered); every attempt row records latency, the
    # backoff slept before it, and its error class.
    backoff = 0.0
    for attempt in range(MAX_ATTEMPTS):
        escalated = max_tokens != initial_max_tokens
        t0 = time.time()
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
            _bump("calls")
            pt = ct = 0
            billed = None
            try:
                pt = int(resp.usage.prompt_tokens or 0)
                ct = int(resp.usage.completion_tokens or 0)
                _bump("prompt_tokens", pt)
                _bump("completion_tokens", ct)
                billed = getattr(resp.usage, "cost", None)
                if billed is not None:
                    _bump("cost_inr", float(billed))
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
                     cost_estimated=cost_est, latency_s=time.time() - t0,
                     backoff_s=backoff, json_mode=bool(use_format),
                     error_class=None if text else "empty_content")
            if not text:
                raise ValueError(f"empty content (max_tokens={max_tokens})")
            return text
        except Exception as e:
            eclass = _error_class(e)
            if eclass != "empty_content":
                _log_raw("chat_text", "", temperature=temp,
                         max_tokens=max_tokens, attempt=attempt, repair=repair,
                         escalated=escalated, realised_model=None,
                         purpose=resolved_purpose, error=e,
                         latency_s=time.time() - t0, backoff_s=backoff,
                         error_class=eclass, json_mode=bool(use_format))
            _log_error("chat_text", e, temperature=temp,
                       max_tokens=max_tokens, attempt=attempt)
            if eclass == "http_402":
                # Never retry a payment failure: it silently turns every
                # remaining game into a fallback-delay draw.
                raise BillingExhausted(str(e)) from e
            if use_format and eclass == "response_format":
                use_format = None  # provider without JSON mode: retry plain
                backoff = 0.0
                continue
            if eclass == "empty_content" and max_tokens < 4000:
                # Reasoning models can spend the whole budget before answering.
                # Logged via escalated=True on the next attempt's raw record.
                max_tokens = min(4000, max_tokens + 1000)
                _bump("escalations")
                backoff = 0.0
                continue
            if attempt == MAX_ATTEMPTS - 1:
                return ""
            if eclass == "http_500" and use_format:
                # P0-R2: gateway timeout on a slow generation; JSON mode at
                # t=0 was slower than plain on 9/12 paired prompts. Retry the
                # same prompt and temperature without response_format; the
                # parser is repair-tolerant.
                use_format = None
            backoff = _backoff_s(attempt)
            time.sleep(backoff)
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
        _bump("json_failures")
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
    _bump("repairs")
    fix = chat_text(fix_system, fix_user, temperature=0.0,
                    response_format=json_format, purpose="repair", repair=True)
    parsed = _parse_json(fix)
    if parsed is not None:
        if meta is not None:
            meta["repaired"] = True
        return parsed

    _bump("json_failures")
    _log_error("chat_json", "unparseable JSON", raw)
    if meta is not None:
        meta.update({"parse_fail": True, "error": "unparseable JSON"})
    return {}
