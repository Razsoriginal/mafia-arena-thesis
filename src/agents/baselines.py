"""Baselines — all use the same AiCredits backbone for a fair comparison."""
from src import llm_client as llm
from src.config import settings
from src.mafia import prompts as P
from src.mafia import prompts_v3 as P3
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
        return llm.chat_text(P.DIALOGUE_SYSTEM, P.dialogue_user(self.pid, role, history), purpose="speak")
    def vote(self, role, history, trust, prev_majority=None, seed=None, day=None, alive=None):
        meta = {}
        d = llm.chat_json(P.VOTE_SYSTEM, P.vote_user(self.pid, role, history, trust), meta=meta, temperature=settings.vote_temperature, purpose="vote")
        return str(d.get("vote", "no-lynch")), _vote_info(d, meta)

class CotNeutralAgent(CotAgent):
    """CoT with the neutral vote prompt (Mafia stress test, pre-reg v3 SS12.5).

    Used for the village seats of cot_village_v3 and for the mafia seats of
    every v3 arm. Speech, night action and probe are CotAgent's.
    """
    name = "cot_neutral"
    def vote(self, role, history, trust, prev_majority=None, seed=None, day=None, alive=None):
        meta = {}
        d = llm.chat_json(P3.VOTE_SYSTEM, P3.vote_neutral_user(self.pid, role, history), meta=meta,
                          temperature=settings.vote_temperature, purpose="vote")
        return str(d.get("vote", "no-lynch")), _vote_info(d, meta)

class CotX3Agent(BaseAgent):
    name = "cotx3"
    def speak(self, role, history):
        return llm.chat_text(P.DIALOGUE_SYSTEM, P.dialogue_user(self.pid, role, history), purpose="speak")
    def vote(self, role, history, trust, prev_majority=None, seed=None, day=None, alive=None):
        samples, fails, reasons = [], [], []

        # The 3 samples are independent draws on the same prompt:
        # concurrent (P0-S1), results kept in sample order.
        def _sample(_i):
            meta = {}
            d = llm.chat_json(P.VOTE_SYSTEM, P.vote_user(self.pid, role, history, trust),
                              meta=meta, temperature=settings.vote_temperature, purpose="vote")
            return d, meta

        for d, meta in llm.pmap(_sample, range(3)):
            fails.append(bool(meta.get("parse_fail")))
            samples.append(str(d["vote"]) if d.get("vote") is not None else None)
            reasons.append(str(d.get("reason", "")))
        counted = [s for s in samples if s is not None]
        tie = False
        if not counted:
            chosen = "no-lynch"
        else:
            from collections import Counter
            top, cnt = Counter(counted).most_common(1)[0]
            tie = cnt == 1 and len(counted) > 1
            chosen = counted[0] if tie else top
        info = _vote_info({"reason": reasons[0] if reasons else ""},
                          {"parse_fail": all(fails)})
        info.update({"samples": samples, "sample_parse_fails": fails,
                     "n_sample_parse_fails": int(sum(1 for f in fails if f)),
                     "tie_all_different": bool(tie),
                     "vote_temperature": settings.vote_temperature})
        return chosen, info

class ReactAgent(BaseAgent):
    name = "react"
    def speak(self, role, history):
        thought = llm.chat_text("Think step by step: Thought, Action, Observation. Reply briefly.",
            f"Role {role}. History:\n{history}\nThought?", purpose="speak")
        return llm.chat_text(P.DIALOGUE_SYSTEM, P.dialogue_user(self.pid, role, history, plan=thought), purpose="speak")
    def vote(self, role, history, trust, prev_majority=None, seed=None, day=None, alive=None):
        meta = {}
        d = llm.chat_json(P.VOTE_SYSTEM, P.vote_user(self.pid, role, history, trust), meta=meta, temperature=settings.vote_temperature, purpose="vote")
        return str(d.get("vote", "no-lynch")), _vote_info(d, meta)

class ConstitutionAgent(BaseAgent):
    name = "constitution"
    CONSTITUTION = "Follow rules: 1) Never vote without quoted evidence. 2) Never follow majority blindly. 3) Always state commitment."
    def speak(self, role, history):
        return llm.chat_text(P.DIALOGUE_SYSTEM + " Constitution: " + self.CONSTITUTION,
            P.dialogue_user(self.pid, role, history), purpose="speak")
    def vote(self, role, history, trust, prev_majority=None, seed=None, day=None, alive=None):
        meta = {}
        d = llm.chat_json(P.VOTE_SYSTEM + " Constitution: " + self.CONSTITUTION,
            P.vote_user(self.pid, role, history, trust), meta=meta, temperature=settings.vote_temperature, purpose="vote")
        return str(d.get("vote", "no-lynch")), _vote_info(d, meta)
