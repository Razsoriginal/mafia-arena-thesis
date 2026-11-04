import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

# .env is the project's source of truth; a stale shell export must not win.
load_dotenv(override=True)

AICREDITS_DEFAULT_BASE_URL = "https://aicredits.in/v1"
OPENROUTER_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


def _llm_config() -> tuple[str, str, str, str]:
    """(provider, base_url, api_key, model) for the main LLM backbone.

    AiCredits is the only backbone. Reads AiCredits_Base_Url /
    Aicredits_API_Key / AiCredits_Model (the casing used in .env), falling
    back to the older LLM_* names so existing setups keep working.
    """
    base_url = (
        os.getenv("AiCredits_Base_Url", "").strip()
        or os.getenv("AICREDITS_BASE_URL", "").strip()
        or AICREDITS_DEFAULT_BASE_URL
    )
    api_key = (
        os.getenv("Aicredits_API_Key", "").strip()
        or os.getenv("AiCredits_API_Key", "").strip()
        or os.getenv("LLM_API_KEY", "").strip()
    )
    model = (
        os.getenv("AiCredits_Model", "").strip()
        or os.getenv("LLM_MODEL", "").strip()
        or "meta/muse-spark-1.3-contributor"
    )
    return "aicredits", base_url, api_key, model


_PROVIDER, _BASE_URL, _API_KEY, _MODEL = _llm_config()

def _jev_config() -> tuple[str, str, str, float, float]:
    """(base_url, api_key, model, min_interval_s, threshold) for the Jev gate.

    Jev is called through OpenRouter only: OpenRouterJevAPIKey +
    OpenRouterJevModel on an OpenAI-compatible endpoint. No BeatAI/systemone
    fallback and no key borrowing. Without OpenRouterJevAPIKey the gate
    returns a logged stub (no delay) instead of silently using another key.
    """
    base_url = (
        os.getenv("OpenRouterJevBaseUrl", "").strip()
        or OPENROUTER_DEFAULT_BASE_URL
    )
    api_key = os.getenv("OpenRouterJevAPIKey", "").strip()
    model = (
        os.getenv("OpenRouterJevModel", "").strip()
        or "typesafe/jev-1.14"
    )
    try:
        min_interval = float(os.getenv("JEV_MIN_INTERVAL_S", "0"))
    except ValueError:
        min_interval = 0.0
    try:
        threshold = float(os.getenv("JEV_THRESHOLD", "0.6"))
    except ValueError:
        threshold = 0.6
    return base_url, api_key, model, min_interval, threshold


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
