"""Audit logger: every gate decision -> parquet for compliance/thesis."""
import os, pandas as pd
from .types import ProposedAction, GateResult

class AuditLogger:
    def __init__(self, path="logs/safety_audit.parquet"):
        self.path = path
        self.rows = []

    def log(self, action: ProposedAction, result: GateResult, outcome: str = ""):
        self.rows.append({
            "action": action.action, "target": action.target, "actor": action.actor,
            "reversible": action.reversible, "decision": result.decision,
            "noul": result.should_delay_noul, "threat": result.threat_score,
            "confidence": result.confidence, "backend": result.backend,
            "reason": result.reason[:300], "outcome": outcome[:300],
        })

    def flush(self):
        if not self.rows:
            return None
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        df = pd.DataFrame(self.rows)
        if os.path.exists(self.path):
            old = pd.read_parquet(self.path)
            df = pd.concat([old, df], ignore_index=True)
        df.to_parquet(self.path, index=False)
        n = len(self.rows)
        self.rows = []
        return self.path, n
