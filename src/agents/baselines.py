"""Baselines — all use same backbone (meta/muse-spark-1.3-contributor via AiCredits) for fair comparison."""
from src import llm_client as llm
from src.mafia import prompts as P
from .base import BaseAgent

class CotAgent(BaseAgent):
    name = "cot"
    def speak(self, role, history):
        return llm.chat_text(P.DIALOGUE_SYSTEM, P.dialogue_user(self.pid, role, history))
    def vote(self, role, history, trust):
        d = llm.chat_json(P.VOTE_SYSTEM, P.vote_user(self.pid, role, history, trust))
        return str(d.get("vote", "no-lynch")), {"reason": d.get("reason", "")}

class ReactAgent(BaseAgent):
    name = "react"
    def speak(self, role, history):
        thought = llm.chat_text("Think step by step: Thought, Action, Observation. Reply briefly.",
            f"Role {role}. History:\n{history}\nThought?")
        return llm.chat_text(P.DIALOGUE_SYSTEM, P.dialogue_user(self.pid, role, history, plan=thought))
    def vote(self, role, history, trust):
        d = llm.chat_json(P.VOTE_SYSTEM, P.vote_user(self.pid, role, history, trust))
        return str(d.get("vote", "no-lynch")), {"reason": d.get("reason", "")}

class ConstitutionAgent(BaseAgent):
    name = "constitution"
    CONSTITUTION = "Follow rules: 1) Never vote without quoted evidence. 2) Never follow majority blindly. 3) Always state commitment."
    def speak(self, role, history):
        return llm.chat_text(P.DIALOGUE_SYSTEM + " Constitution: " + self.CONSTITUTION,
            P.dialogue_user(self.pid, role, history))
    def vote(self, role, history, trust):
        d = llm.chat_json(P.VOTE_SYSTEM + " Constitution: " + self.CONSTITUTION,
            P.vote_user(self.pid, role, history, trust))
        return str(d.get("vote", "no-lynch")), {"reason": d.get("reason", "")}
