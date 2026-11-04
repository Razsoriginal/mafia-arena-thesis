# Enterprise Integration — Safety-Gate Framework
Drop-in pre-action check for agentic workflows. No training. Audit-ready.

## 1. What you get
`src/safety/`: `SafetyGate` + `guard`/`guard_tool` + `AuditLogger` + typed `ProposedAction`/`GateResult`.
Pattern: agent proposes irreversible action → gate scores (trust/violation/threat or Jev noul) → ALLOW / DELAY / ESCALATE + parquet audit.

## 2. Integrate in 10 lines
```python
from src.safety import SafetyGate, guard_tool, AuditLogger
from src.safety.types import ProposedAction

gate = SafetyGate(backend="llm")  # or backend="jev" with OpenRouterJevModel=typesafe/jev-1.14 (OpenRouter)
audit = AuditLogger("logs/safety_audit.parquet")

def refund_order(order_id, amount):
    action = ProposedAction(action="refund", target=order_id, context=f"amount={amount}", reversible=False, actor="support-agent")
    # trust/violation/threat come from your DMN/TPN or Jev; heuristics shown
    return guard_tool(gate, action, lambda: stripe_refund(order_id, amount),
                      logger=audit, trust=0.55, violation=0.7, threat=4.0)

print(refund_order("ord_123", 4999))
audit.flush()  # -> logs/safety_audit.parquet
```

Decorator form for existing tools:
```python
from src.safety import guard
@guard(gate, action_fn=lambda oid, amt: ProposedAction(action="refund", target=oid, reversible=False), logger=audit)
def refund(oid, amt): ...
```

Jev mode (fast brake, 70-500ms):
```python
from src.agents.jev_gate import jev_decide
out = jev_decide(state="customer claims duplicate charge, no receipt", alive_ids=[])
res = gate.check_with_jev(ProposedAction(action="refund", reversible=False), out)
```

## 3. Recalibration checklist (per app — required)
1. Label 30-50 past cases (should-delay yes/no). Fit `TAU_DELAY`, `EVT_THRESHOLD` / Jev `noul` threshold to maximise delay-quality, not accuracy.
2. Define reversibility per tool (refund/lynch/deploy = irreversible → ESCALATE; search/draft = reversible → DELAY+ask-info).
3. Set threat rubric 1-5 with owners (e.g. 5 = money movement, PHI, prod deploy).
4. Log 2 weeks to `safety_audit.parquet`; report ECE, cascade-resistance, say-do-gap. Re-tune quarterly.
5. Human path: every DELAY/ESCALATE needs an owner + SLA, else gate becomes denial-of-service.

## 4. Limits
Not a formal proof. Empirical risk reduction only; thresholds are domain-specific. Jev is hosted (not open-source), text-only. Keep LLM-gate fallback.

## 5. Thesis mapping
Mafia vote = refund/deploy proxy. `logs/games.parquet` → `logs/safety_audit.parquet` same schema family. Appendix: include audit sample + threshold ROC.
