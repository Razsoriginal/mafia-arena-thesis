"""Our agent: DMN (imagine + exformation) -> TPN (verify) -> EVT gate (delay if risky)."""
from src import llm_client as llm
from src.mafia import prompts as P
from src.config import settings
from .base import BaseAgent

COMMITMENT = "I will only vote with cited evidence (turn ids)."


class DmnTpnAgent(BaseAgent):
    name = "dmn_tpn"
    def __init__(self, pid, backend: str = "llm"):
        super().__init__(pid)
        self.backend = backend  # llm | jev (EVT DELAY source)
        self._alive: list = []
        self._plan: str = ""  # cached by reason(), used by speak() same day

    def speak(self, role, history):
        # Speak from the verification-corrected plan cached by reason().
        return llm.chat_text(P.DIALOGUE_SYSTEM, P.dialogue_user(self.pid, role, history, plan=self._plan))

    def reason(self, role, history, facts, alive, prev_majority=None, alive_roles=None):
        self._alive = list(alive)
        dmn_meta, tpn_meta = {}, {}
        dmn = llm.chat_json(P.DMN_SYSTEM, P.dmn_user(self.pid, role, history, alive),
                            meta=dmn_meta)
        tpn = llm.chat_json(P.TPN_SYSTEM, P.tpn_user(dmn.get("hypotheses", []), facts),
                            meta=tpn_meta)
        parse_fail = bool(dmn_meta.get("parse_fail") or tpn_meta.get("parse_fail"))
        verified = tpn.get("verified", [])
        conf_by_suspect = {}
        for v in verified:
            try:
                conf_by_suspect[str(v["suspect"])] = float(v.get("revised_confidence", 0))
            except Exception:
                pass
        max_conf = max(conf_by_suspect.values(), default=0)
        top_suspect = max(conf_by_suspect, key=conf_by_suspect.get, default=None)
        # EVT: expectation (yesterday's majority) vs violation (deviation).
        if prev_majority is None or top_suspect is None:
            violation = 0.5
        else:
            violation = 0.2 if str(top_suspect) == str(prev_majority) else 0.7
        # Threat: wrong-lynch cost grows as village approaches parity.
        if alive_roles:
            m = sum(1 for r in alive_roles.values() if r == "mafia")
            o = max(1, len(alive_roles) - m)
            threat = min(1.0, m / o)
            prior_innocent = round(o / len(alive_roles), 3)
        else:
            threat = 0.8  # legacy fallback when role counts unavailable
            prior_innocent = 0.5
        evt = violation * threat
        if parse_fail:
            delay_cause = "json_failure"
        elif max_conf < settings.tau_delay:
            delay_cause = "low_confidence"
        elif evt > settings.evt_threshold:
            delay_cause = "evt_threshold"
        else:
            delay_cause = None
        delay = delay_cause is not None
        # Trust for EVERY alive player (1 = innocent); unverified = base rate.
        trust = {}
        for pid in alive:
            if str(pid) in conf_by_suspect:
                trust[str(pid)] = round(1 - conf_by_suspect[str(pid)], 3)
            else:
                # Base-rate prior instead of a flat 0.5: with 5/7 innocents,
                # an unverified player is more likely innocent than not.
                trust[str(pid)] = prior_innocent
        self._plan = (f"Top suspect: {top_suspect} (confidence {max_conf:.2f}). "
                      f"Delay={'yes' if delay else 'no'} (evt {evt:.2f}).")
        trace = {"dmn": dmn, "tpn": tpn, "max_conf": max_conf,
                 "top_suspect": top_suspect, "prev_majority": prev_majority,
                 "violation": violation, "threat": threat, "evt": evt,
                 "prior_innocent": prior_innocent,
                 "delay": delay, "delay_cause": delay_cause,
                 "parse_fail": parse_fail,
                 "dmn_meta": dmn_meta, "tpn_meta": tpn_meta,
                 "commitment": COMMITMENT,
                 "reason_cached_before_discussion": True}
        return trust, trace, delay

    def vote(self, role, history, trust, trace=None):
        trace = trace if isinstance(trace, dict) else {}
        jev_out = None
        if self.backend == "jev":
            # Jev is the DELAY source: consult it even when the LLM EVT
            # heuristic already favours delay.
            from .jev_gate import jev_decide, should_delay

            alive = self._alive or [str(t) for t in (trust or {})]
            state = f"role={role} history<<<{history[-3000:]}>>>"
            jev_out = jev_decide(state, alive)
            trace["jev"] = {k: v for k, v in jev_out.items() if k != "vote_probs"}
            if should_delay(jev_out, settings.jev_threshold):
                return "no-lynch", {"reason": f"Jev DELAY: noul {jev_out['should_delay_noul']:.2f}",
                                    "trace": trace, "jev": jev_out,
                                    "commitment": trace.get("commitment", COMMITMENT),
                                    "parse_fail": False, "delay_cause": "jev"}
        elif trace.get("delay"):
            return "no-lynch", {"reason": "EVT delay: insufficient calibrated evidence",
                                "trace": trace, "commitment": trace.get("commitment", COMMITMENT),
                                "parse_fail": bool(trace.get("parse_fail")),
                                "delay_cause": trace.get("delay_cause")}
        meta = {}
        d = llm.chat_json(P.VOTE_CITED_SYSTEM,
                          P.vote_cited_user(self.pid, role, history, trust), meta=meta)
        return str(d.get("vote", "no-lynch")), {
            "reason": d.get("reason", ""), "trace": trace, "jev": jev_out,
            "commitment": trace.get("commitment", COMMITMENT),
            "parse_fail": bool(meta.get("parse_fail")),
            "delay_cause": "json_failure" if meta.get("parse_fail") else None,
        }
