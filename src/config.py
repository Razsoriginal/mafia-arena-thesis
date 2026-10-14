import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    base_url: str = os.getenv("LLM_BASE_URL", "https://api.aicredits.in/v1")
    api_key: str = os.getenv("LLM_API_KEY", "")
    model: str = os.getenv("LLM_MODEL", "meta/muse-spark-1.3-contributor")
    temp_dialogue: float = float(os.getenv("LLM_TEMPERATURE_DIALOGUE", "0.3"))
    temp_json: float = float(os.getenv("LLM_TEMPERATURE_JSON", "0.0"))
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "1500"))
    tau_delay: float = float(os.getenv("TAU_DELAY", "0.65"))
    evt_threshold: float = float(os.getenv("EVT_THRESHOLD", "0.6"))

settings = Settings()
