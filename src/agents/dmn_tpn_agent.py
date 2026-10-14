"""Our agent: DMN (imagine + exformation) -> TPN (verify) -> EVT gate (delay if risky)."""
from src import llm_client as llm
from src.mafia import prompts as P
from src.config import settings
from .base import BaseAgent

class DmnTpnAgent(BaseAgent):
    name = "dmn_tpn"
    def __init__(self, pid, backend: str = "llm"):
        super().__init__(pid)
        self.backend = backend  # llm | jev (EVT DELAY source)
        self._alive: list = []
    def speak(self, role, history):
        # Speak from verification-corrected plan (lightweight: 1 DMN call cached per day by caller)
        return llm.chat_text(P.DIALOGUE_SYSTEM, P.dialogue_user(self.pid, role, history))

    def reason(self, role, history, facts, alive):
        self._alive = list(alive)
        dmn = llm.chat_json(P.DMN_SYSTEM, P.dmn_user(self.pid, role, history, alive))
        tpn = llm.chat_json(P.TPN_SYSTEM, P.tpn_user(dmn.get("hypotheses", []), facts))
        verified = tpn.get("verified", [])
        # EVT scores
        max_conf = max([v.get("revised_confidence", 0) for v in verified], default=0)
        # violation proxy: disagreement between top hypothesis and recent majority (computed by caller; simplified here)
        violation = 1 - max_conf
        threat = 0.8  # lynch is irreversible; caller can override
        evt = violation * threat
        delay = (max_conf < settings.tau_delay) or (evt > settings.evt_threshold)
        trust = {}
        for v in verified:
            # trust innocent = 1 - mafia confidence
            try:
                trust[str(v["suspect"])] = round(1 - float(v.get("revised_confidence", 0)), 3)
            except Exception:
                pass
        trace = {"dmn": dmn, "tpn": tpn, "max_conf": max_conf, "evt": evt, "delay": delay}
        return trust, trace, delay

    def vote(self, role, history, trust, trace=None):
        if trace and trace.get("delay"):
            return "no-lynch", {"reason": "EVT delay: insufficient calibrated evidence", "trace": trace}
        if self.backend == "jev":
            from .jev_gate import jev_decide, should_delay

            alive = self._alive or [str(t) for t in (trust or {})]
            state = f"role={role} history<<<{history[-3000:]}>>>"
            jev_out = jev_decide(state, alive)
            if should_delay(jev_out, settings.evt_threshold):
                return "no-lynch", {"reason": f"Jev DELAY: noul {jev_out['should_delay_noul']:.2f}", "trace": trace or {}, "jev": jev_out}
            (trace or {})["jev"] = {k: v for k, v in jev_out.items() if k != "vote_probs"}
        d = llm.chat_json(P.VOTE_SYSTEM, P.vote_user(self.pid, role, history, trust))
        return str(d.get("vote", "no-lynch")), {"reason": d.get("reason", ""), "trace": trace or {}}
