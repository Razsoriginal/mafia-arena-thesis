from src import llm_client as llm
from src.mafia import prompts as P


class BaseAgent:
    name = "base"
    def __init__(self, pid):
        self.pid = pid
    def speak(self, role, history) -> str:
        return "I am watching and waiting for evidence."
    def vote(self, role, history, trust, prev_majority=None, seed=None,
             day=None, alive=None) -> tuple[str, dict]:
        return "no-lynch", {}
    def elicit_trust_probe(self, role, history, alive):
        """Post-vote shadow probe at 0.0. Never fed back into play.

        Targets are restricted to alive non-self players (F32): a dead or
        hallucinated target is dropped, never recorded.
        """
        meta = {}
        d = llm.chat_json(P.TRUST_PROBE_SYSTEM,
                          P.trust_probe_user(self.pid, history, alive),
                          meta=meta, temperature=0.0)
        raw = d.get("trust", {}) if isinstance(d, dict) else {}
        allowed = {str(a) for a in (alive or []) if str(a) != str(self.pid)}
        trust = {}
        for k, v in (raw or {}).items():
            if str(k) == str(self.pid) or str(k) not in allowed:
                continue
            try:
                trust[str(k)] = round(float(v), 3)
            except Exception:
                continue
        return trust, {"probe": True, "parse_fail": bool(meta.get("parse_fail"))}
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
