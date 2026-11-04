from src import llm_client as llm
from src.mafia import prompts as P


class BaseAgent:
    name = "base"
    def __init__(self, pid):
        self.pid = pid
    def speak(self, role, history) -> str:
        return "I am watching and waiting for evidence."
    def vote(self, role, history, trust) -> tuple[str, dict]:
        return "no-lynch", {}
    def night_action(self, role, history, alive, options, action):
        """LLM night choice: 'kill' | 'save' | 'check'. None = engine fallback."""
        meta = {}
        d = llm.chat_json(
            P.NIGHT_SYSTEM,
            P.night_user(self.pid, role, alive, history, action, options),
            meta=meta,
        )
        pick = str(d.get(action, ""))
        valid = {str(o) for o in options}
        return pick if pick in valid else None
