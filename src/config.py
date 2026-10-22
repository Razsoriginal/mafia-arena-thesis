import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

def _llm_config() -> tuple[str, str, str, str]:
    """(provider, base_url, api_key, model). OpenRouter wins when set.

    Current primary (2026-10-22): OpenRouter via .env OpenRouterAPIKey /
    OpenRouterModel (e.g. minimax/minimax-m3.1-flash:free). Falls back to
    the previous AiCredits LLM_* vars so old runs stay reproducible.
    """
    or_key = os.getenv("OpenRouterAPIKey", "").strip()
    or_model = os.getenv("OpenRouterModel", "").strip()
    if or_key and or_model:
        return (
            "openrouter",
            os.getenv("OpenRouterBaseUrl", "https://openrouter.ai/api/v1"),
            or_key,
            or_model,
        )
    return (
        "aicredits",
        os.getenv("LLM_BASE_URL", "https://api.aicredits.in/v1"),
        os.getenv("LLM_API_KEY", ""),
        os.getenv("LLM_MODEL", "meta/muse-spark-1.3-contributor"),
    )


_PROVIDER, _BASE_URL, _API_KEY, _MODEL = _llm_config()

def _jev_config() -> tuple[str, str, str, float, float]:
    """(base_url, api_key, model, min_interval_s, threshold).

    Key precedence: OpenRouterJevAPIKey > JEV_API_KEY > LLM_API_KEY.
    Endpoint default stays BeatAI SystemOne (probe Step 0 decides); set
    OpenRouterJevBaseUrl=https://openrouter.ai/api/v1 if the new key only
    works via OpenRouter (the existing chat fallback then handles it).
    The old 61s BeatAI free-tier guard is off when the new key is present;
    JEV_MIN_INTERVAL_S overrides either way.
    """
    key = (
        os.getenv("OpenRouterJevAPIKey", "").strip()
        or os.getenv("JEV_API_KEY", "")
        or os.getenv("LLM_API_KEY", "")
    )
    base_url = (
        os.getenv("OpenRouterJevBaseUrl", "").strip()
        or os.getenv("JEV_BASE_URL", "https://api.beatapi.io/v1/systemone")
    )
    model = (
        os.getenv("OpenRouterJevModel", "").strip()
        or os.getenv("JEV_MODEL", "jev-1.13-free")
    )
    has_new_key = bool(os.getenv("OpenRouterJevAPIKey", "").strip())
    try:
        min_interval = float(os.getenv(
            "JEV_MIN_INTERVAL_S", "0.0" if has_new_key else "61.0"))
    except ValueError:
        min_interval = 0.0 if has_new_key else 61.0
    try:
        threshold = float(os.getenv("JEV_THRESHOLD", "0.6"))
    except ValueError:
        threshold = 0.6
    return base_url, key, model, min_interval, threshold


_JEV_BASE_URL, _JEV_API_KEY, _JEV_MODEL, _JEV_MIN_INTERVAL, _JEV_THRESHOLD = _jev_config()

@dataclass
class Settings:
    provider: str = field(default=_PROVIDER)
    base_url: str = field(default=_BASE_URL)
    api_key: str = field(default=_API_KEY)
    model: str = field(default=_MODEL)
    jev_base_url: str = field(default=_JEV_BASE_URL)
    jev_api_key: str = field(default=_JEV_API_KEY)
    jev_model: str = field(default=_JEV_MODEL)
    jev_min_interval: float = field(default=_JEV_MIN_INTERVAL)
    jev_threshold: float = field(default=_JEV_THRESHOLD)
    temp_dialogue: float = float(os.getenv("LLM_TEMPERATURE_DIALOGUE", "0.3"))
    temp_json: float = float(os.getenv("LLM_TEMPERATURE_JSON", "0.0"))
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "1500"))
    tau_delay: float = float(os.getenv("TAU_DELAY", "0.65"))
    evt_threshold: float = float(os.getenv("EVT_THRESHOLD", "0.6"))

settings = Settings()
