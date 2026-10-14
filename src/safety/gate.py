"""SafetyGate: pre-action EVT check. LLM-gate MVP + Jev System-One option."""
import time
from src.config import settings
from .types import ProposedAction, GateResult

class SafetyGate:
    def __init__(self, tau_delay: float | None = None, evt_threshold: float | None = None,
                 backend: str = "llm", jev_threshold: float = 0.6):
        self.tau = tau_delay if tau_delay is not None else settings.tau_delay
        self.evt_threshold = evt_threshold if evt_threshold is not None else settings.evt_threshold
        self.backend = backend  # llm | jev | heuristic
        self.jev_threshold = jev_threshold

    def check(self, action: ProposedAction, trust: float = 0.5,
              violation: float = 0.0, threat: float | None = None) -> GateResult:
        """Deterministic core. LLM/Jev only supply (trust, violation, threat); gating is code."""
        t0 = time.time()
        threat = 1.0 if action.reversible else (threat if threat is not None else 3.0)
        threat_norm = min(max((threat - 1) / 4.0, 0.0), 1.0)  # 1-5 -> 0-1
        evt = violation * threat_norm if action.reversible is False else violation * threat_norm
        delay = (trust < self.tau) or (evt > self.evt_threshold)
        decision = "DELAY" if delay and not action.reversible else ("ALLOW" if not delay else "ESCALATE")
        if action.reversible and delay:
            decision = "DELAY"  # ask-info, still reversible
        return GateResult(
            decision=decision, should_delay_noul=round(evt, 3),
            threat_score=round(threat, 2), confidence=round(trust, 3),
            reason=f"trust {trust:.2f} < tau {self.tau} or evt {evt:.2f} > {self.evt_threshold}",
            latency_ms=int((time.time() - t0) * 1000), backend="heuristic-core",
        )

    def check_with_jev(self, action: ProposedAction, jev_out: dict) -> GateResult:
        """Use Jev noul/choice/score directly. jev_out from src/agents/jev_gate.jev_decide()."""
        t0 = time.time()
        noul = float(jev_out.get("should_delay_noul", 0.0))
        threat = float(jev_out.get("threat_score", 2.5))
        conf = float(jev_out.get("confidence", 0.0))
        delay = noul >= self.jev_threshold
        decision = "DELAY" if delay else "ALLOW"
        if delay and not action.reversible:
            decision = "ESCALATE"
        return GateResult(
            decision=decision, should_delay_noul=noul, threat_score=threat,
            confidence=conf, reason=f"jev noul {noul:.2f} vs {self.jev_threshold}",
            latency_ms=int((time.time() - t0) * 1000), backend="jev",
        )
