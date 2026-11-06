"""Deterministic null village agents: no LLM calls (Part A A2)."""
import random

from .base import BaseAgent


class RandomVoterAgent(BaseAgent):
    name = "random_voter"

    def vote(self, role, history, trust, prev_majority=None, seed=None,
             day=None, alive=None):
        alive = list(alive) if alive is not None else []
        options = [str(a) for a in alive if int(a) != self.pid] + ["no-lynch"]
        rng = random.Random((seed or 0) * 1000003 + (day or 0) * 1009 + self.pid * 101)
        return rng.choice(options), {"reason": "null random vote", "commitment": "",
                                      "parse_fail": False, "delay_cause": None,
                                      "null_kind": "random"}

    def night_action(self, role, history, alive, options, action):
        opts = [o for o in options]
        if action == "save":
            return str(self.pid) if self.pid in opts else (str(opts[0]) if opts else None)
        if action == "check":
            cand = [o for o in opts if int(o) != self.pid]
            return str(min(cand)) if cand else None
        return str(opts[0]) if opts else None


class MajorityFollowerAgent(BaseAgent):
    name = "majority_follower"

    def vote(self, role, history, trust, prev_majority=None, seed=None,
             day=None, alive=None):
        alive_str = {str(a) for a in (alive or [])}
        v = "no-lynch"
        if prev_majority is not None and str(prev_majority) != "no-lynch":
            if str(prev_majority) in alive_str and str(prev_majority) != str(self.pid):
                v = str(prev_majority)
        return v, {"reason": "null majority-follow vote", "commitment": "",
                   "parse_fail": False, "delay_cause": None,
                   "null_kind": "majority"}

    def night_action(self, role, history, alive, options, action):
        opts = [o for o in options]
        if action == "save":
            return str(self.pid) if self.pid in opts else (str(opts[0]) if opts else None)
        if action == "check":
            cand = [o for o in opts if int(o) != self.pid]
            return str(min(cand)) if cand else None
        return str(opts[0]) if opts else None
