"""Jev System-One gate via OpenRouter (decisions endpoint).

Jev is a decisions model, not a chat model: it takes `model`, `state`,
`questions` and returns typed answers (choice / score / noul). Config is
OpenRouter-only: OpenRouterJevAPIKey + OpenRouterJevModel, with the
endpoint derived from OpenRouterJevBaseUrl as /api/alpha/decisions
(override with OpenRouterJevDecisionsUrl). Without the key the gate returns
a logged stub (no delay) so the arena still runs and `jev_stub` records why
no real call was made.
"""
import json
import os
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from src.config import settings

_LAST_OK_TS = 0.0


def _min_interval() -> float:
    return settings.jev_min_interval


def _jev_key() -> str:
    return settings.jev_api_key or ""


def _decisions_url() -> str:
    explicit = os.getenv("OpenRouterJevDecisionsUrl", "").strip()
    if explicit:
        return explicit
    parts = urlsplit(settings.jev_base_url)
    return f"{parts.scheme}://{parts.netloc}/api/alpha/decisions"


def _stub(reason: str = "", model: str | None = None) -> dict:
    out = {
        "should_delay_noul": 0.0,
        "vote_choice": "no-lynch",
        "vote_probs": {},
        "threat_score": 2.5,
        "confidence": 0.0,
        "stub": True,
        "backend": "openrouter-decisions",
        "model": model or settings.jev_model,
    }
    if reason:
        out["error"] = reason[:200]
    return out


def _decisions_decide(state: str, options: list, use_model: str, key: str) -> dict:
    criteria = {str(o): f"player {o}" if str(o) != "no-lynch" else "delay the lynch"
                for o in options}
    payload = {
        "model": use_model,
        "state": state,
        "questions": {
            "should_delay": {
                "type": "noul",
                "instructions": ("Should the town delay the lynch (no-lynch) due to "
                                 "high uncertainty? True means delay."),
            },
            "vote": {
                "type": "choice",
                "instructions": "Who should town vote? Pick the most suspicious, else no-lynch.",
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
        _decisions_url(),
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:200]}")

    answers = data.get("answers", {})
    noul = float(answers.get("should_delay", {}).get("noul", 0.0))
    noul = max(0.0, min(1.0, noul))
    vote_ans = answers.get("vote", {})
    vote = str(vote_ans.get("choice", "no-lynch"))
    if vote not in {str(o) for o in options}:
        vote = "no-lynch"
    # score is 0-based over the legend; convert to the 1-5 threat scale.
    try:
        threat = float(answers.get("threat", {}).get("score", 1.5)) + 1.0
    except (TypeError, ValueError):
        threat = 2.5
    threat = max(1.0, min(5.0, threat))
    try:
        conf = float(vote_ans.get("confidence", 0.5))
    except (TypeError, ValueError):
        conf = 0.5
    return {
        "should_delay_noul": noul,
        "vote_choice": vote,
        "vote_probs": vote_ans.get("probabilities", {}),
        "threat_score": threat,
        "confidence": conf,
        "stub": False,
        "backend": "openrouter-decisions",
        "model": data.get("model", use_model),
        "usage": data.get("usage", {}),
    }


def jev_decide(state: str, alive_ids: list, model: str | None = None) -> dict:
    """One OpenRouter decisions call returning noul / choice / score.

    Returns: {"should_delay_noul": 0.0-1.0, "vote_choice": pid|no-lynch,
              "vote_probs": {}, "threat_score": 1-5, "confidence": 0-1}
    """
    use_model = model or settings.jev_model
    key = _jev_key()
    if not key:
        return _stub("missing OpenRouterJevAPIKey", use_model)
    global _LAST_OK_TS
    now = time.time()
    if _min_interval() > 0 and _LAST_OK_TS and now - _LAST_OK_TS < _min_interval():
        return _stub(f"rate-limit guard: last ok {now - _LAST_OK_TS:.0f}s ago", use_model)
    try:
        options = [str(a) for a in alive_ids] + ["no-lynch"]
        out = _decisions_decide(state, options, use_model, key)
        _LAST_OK_TS = time.time()
        return out
    except Exception as e:
        return _stub(f"{type(e).__name__}: {e}", use_model)


def should_delay(jev_out: dict, threshold: float = 0.6) -> bool:
    return float(jev_out.get("should_delay_noul", 0.0)) >= threshold
