"""Typed contracts. Framework returns these, never free text."""
from dataclasses import dataclass, field

@dataclass
class ProposedAction:
    action: str  # e.g. "refund", "delete_record", "deploy", "lynch_vote"
    target: str = ""  # e.g. order_id, player_id
    context: str = ""  # state summary / dialogue tail (truncated by caller)
    reversible: bool = False
    actor: str = ""  # agent id

@dataclass
class GateResult:
    decision: str  # ALLOW | DELAY | ESCALATE
    should_delay_noul: float = 0.0
    threat_score: float = 1.0  # 1-5
    confidence: float = 0.0
    reason: str = ""
    evidence_spans: list = field(default_factory=list)
    latency_ms: int = 0
    backend: str = "llm"  # llm | jev | heuristic
