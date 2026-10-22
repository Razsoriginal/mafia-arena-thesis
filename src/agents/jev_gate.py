"""Jev System-One gate (TypeSafe AI).
Jev returns typed decisions, not text: choice / score / noul in 70-500ms.
Use for EVT DELAY: noul=should-delay, choice=vote target, score=threat.

Setup: key precedence OpenRouterJevAPIKey > JEV_API_KEY > LLM_API_KEY;
endpoint OpenRouterJevBaseUrl > JEV_BASE_URL (default BeatAI SystemOne);
model OpenRouterJevModel > JEV_MODEL (default jev-1.13-free).
Toggle: --gate llm|jev. Falls back to neutral stub (no delay) on any error
so arena runs without key. The old BeatAI ~1 req/min guard is off when
OpenRouterJevAPIKey is set; JEV_MIN_INTERVAL_S overrides either way.
"""
import json
import time

from src.config import settings

# Re-exported for backward compatibility; source of truth is settings.
JEV_MODEL = settings.jev_model
JEV_BASE_URL = settings.jev_base_url

_LAST_OK_TS = 0.0


def _min_interval() -> float:
    return settings.jev_min_interval


def _jev_key() -> str:
    return settings.jev_api_key or ""


def _stub(reason: str = "", model: str | None = None) -> dict:
    out = {
        "should_delay_noul": 0.0,
        "vote_choice": "no-lynch",
        "vote_probs": {},
        "threat_score": 2.5,
        "confidence": 0.0,
        "stub": True,
        "model": model or JEV_MODEL,
    }
    if reason:
        out["error"] = reason[:200]
    return out

def _systemone_decide(state: str, options: list, use_model: str, key: str) -> dict:
    """Native TypeSafe SystemOne call: noul + choice + score in one round trip."""
    import urllib.request

    criteria = {pid: f"player {pid}" for pid in options}
    payload = {
        "model": use_model,
        "state": state,
        "questions": {
            "should_delay": {
                "type": "noul",
                "instructions": "Should the town delay the lynch (no-lynch) due to high uncertainty? True means delay.",
            },
            "vote": {
                "type": "choice",
                "instructions": "Who should town vote? Pick most suspicious, else no-lynch.",
                "criteria": criteria,
            },
            "threat": {
                "type": "score",
                "instructions": "How threatening is the current state for town?",
                "criteria": ["Safe", "Uneasy", "Risky", "Dangerous", "Critical"],
            },
        },
    }
    req = urllib.request.Request(
        JEV_BASE_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + key,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) mafia-arena/1.0",
            "Accept": "application/json",
        },
        method="POST",
    )
    import urllib.error

    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:150]}")
    answers = data.get("answers", {})
    noul = float(answers.get("should_delay", {}).get("noul", 0.0))
    noul = max(0.0, min(1.0, noul))
    vote_ans = answers.get("vote", {})
    vote = str(vote_ans.get("choice", "no-lynch"))
    if vote not in options:
        vote = "no-lynch"
    threat_ans = answers.get("threat", {})
    threat = float(threat_ans.get("score", 1.5)) + 1.0  # 0-based legend -> 1-5
    threat = max(1.0, min(5.0, threat))
    conf = vote_ans.get("confidence", 0.5)
    try:
        conf = float(conf)
    except (TypeError, ValueError):
        conf = 0.5
    return {
        "should_delay_noul": noul,
        "vote_choice": vote,
        "vote_probs": vote_ans.get("probabilities", {}),
        "threat_score": threat,
        "confidence": conf,
        "stub": False,
        "model": data.get("model", use_model),
    }


def jev_decide(state: str, alive_ids: list, model: str | None = None) -> dict:
    """SystemOne call when JEV_BASE_URL is a systemone endpoint,
    else OpenAI-compatible JSON chat call.

    Returns: {"should_delay_noul": 0.0-1.0, "vote_choice": pid|no-lynch,
              "vote_probs": {}, "threat_score": 1-5, "confidence": 0-1}
    MVP fallback: return neutral (no delay) so arena runs without key.
    """
    use_model = model or JEV_MODEL
    key = _jev_key()
    if not key:
        return _stub("missing JEV_API_KEY/LLM_API_KEY", use_model)
    global _LAST_OK_TS
    now = time.time()
    if _min_interval() > 0 and _LAST_OK_TS and now - _LAST_OK_TS < _min_interval():
        return _stub(f"rate-limit guard: last ok {now - _LAST_OK_TS:.0f}s ago", use_model)
    try:
        options = list(alive_ids) + ["no-lynch"]
        if "systemone" in JEV_BASE_URL:
            out = _systemone_decide(state, options, use_model, key)
        else:
            out = _chat_decide(state, options, use_model, key)
        _LAST_OK_TS = time.time()
        return out
    except Exception as e:
        return _stub(f"{type(e).__name__}: {e}", use_model)
def _chat_decide(state: str, options: list, use_model: str, key: str) -> dict:
    """OpenAI-compatible JSON chat fallback for non-systemone endpoints."""
    from openai import OpenAI

    client = OpenAI(base_url=JEV_BASE_URL, api_key=key)
    system = (
        "You are a fast game-theory gate. Reply with valid JSON only: "
        '{"should_delay_noul": 0.0-1.0, "vote_choice": "<id>", "threat_score": 1-5}.'
    )
    user = f"State: {state}\nAlive options (must pick one): {options}\nPick vote_choice from options only."
    resp = client.chat.completions.create(
        model=use_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.0,
        max_tokens=150,
    )
    raw = (resp.choices[0].message.content or "").strip()
    if "```" in raw:
        raw = raw.split("```")[1].replace("json", "", 1).strip()
    data = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    vote = str(data.get("vote_choice", "no-lynch"))
    if vote not in options:
        vote = "no-lynch"
    try:
        noul = float(data.get("should_delay_noul", 0.0))
    except (TypeError, ValueError):
        noul = 0.0
    noul = max(0.0, min(1.0, noul))
    try:
        threat = float(data.get("threat_score", 2.5))
    except (TypeError, ValueError):
        threat = 2.5
    threat = max(1.0, min(5.0, threat))
    return {
        "should_delay_noul": noul,
        "vote_choice": vote,
        "vote_probs": {},
        "threat_score": threat,
        "confidence": 0.5,
        "stub": False,
        "model": use_model,
    }

def should_delay(jev_out: dict, threshold: float = 0.6) -> bool:
    return float(jev_out.get("should_delay_noul", 0.0)) >= threshold
