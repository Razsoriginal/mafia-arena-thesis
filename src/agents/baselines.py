"""Baselines — all use the same AiCredits backbone for a fair comparison."""
from src import llm_client as llm
from src.mafia import prompts as P
from .base import BaseAgent


def _vote_info(d: dict, meta: dict) -> dict:
    parse_fail = bool(meta.get("parse_fail"))
    return {
        "reason": d.get("reason", ""),
        "commitment": "",
        "parse_fail": parse_fail,
        "delay_cause": "json_failure" if parse_fail else None,
    }


class CotAgent(BaseAgent):
    name = "cot"
    def speak(self, role, history):
        return llm.chat_text(P.DIALOGUE_SYSTEM, P.dialogue_user(self.pid, role, history))
    def vote(self, role, history, trust):
        meta = {}
        d = llm.chat_json(P.VOTE_SYSTEM, P.vote_user(self.pid, role, history, trust), meta=meta)
        return str(d.get("vote", "no-lynch")), _vote_info(d, meta)

class ReactAgent(BaseAgent):
    name = "react"
    def speak(self, role, history):
        thought = llm.chat_text("Think step by step: Thought, Action, Observation. Reply briefly.",
            f"Role {role}. History:\n{history}\nThought?")
        return llm.chat_text(P.DIALOGUE_SYSTEM, P.dialogue_user(self.pid, role, history, plan=thought))
    def vote(self, role, history, trust):
        meta = {}
        d = llm.chat_json(P.VOTE_SYSTEM, P.vote_user(self.pid, role, history, trust), meta=meta)
        return str(d.get("vote", "no-lynch")), _vote_info(d, meta)

class ConstitutionAgent(BaseAgent):
    name = "constitution"
    CONSTITUTION = "Follow rules: 1) Never vote without quoted evidence. 2) Never follow majority blindly. 3) Always state commitment."
    def speak(self, role, history):
        return llm.chat_text(P.DIALOGUE_SYSTEM + " Constitution: " + self.CONSTITUTION,
            P.dialogue_user(self.pid, role, history))
    def vote(self, role, history, trust):
        meta = {}
        d = llm.chat_json(P.VOTE_SYSTEM + " Constitution: " + self.CONSTITUTION,
            P.vote_user(self.pid, role, history, trust), meta=meta)
        return str(d.get("vote", "no-lynch")), _vote_info(d, meta)
