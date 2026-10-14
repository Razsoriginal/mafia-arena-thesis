"""Middleware: wrap any tool/function with one line."""
import functools
from .types import ProposedAction
from .audit import AuditLogger

def guard(gate, action_fn=None, logger: AuditLogger | None = None):
    """Decorator: @guard(gate, action_fn=lambda *a, **k: ProposedAction(...)).
    If gate says DELAY/ESCALATE, tool is NOT executed; result with gate info returned.
    """
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            pa = action_fn(*args, **kwargs) if action_fn else ProposedAction(action=fn.__name__)
            res = gate.check(pa)
            if logger:
                logger.log(pa, res)
            if res.decision in ("DELAY", "ESCALATE"):
                return {"status": res.decision, "gate": res.__dict__,
                        "message": "Blocked by safety gate: insufficient calibrated evidence. Escalated for review."}
            out = fn(*args, **kwargs)
            if logger:
                logger.log(pa, res, outcome=str(out)[:200])
            return out
        return wrapper
    return deco

def guard_tool(gate, action: ProposedAction, fn, logger: AuditLogger | None = None, **gw):
    """Imperative form for LangChain / OpenAI tool calls:
    out = guard_tool(gate, ProposedAction(action='refund', ...), lambda: refund(order_id))
    """
    from .gate import SafetyGate
    assert isinstance(gate, SafetyGate)
    # allow caller-supplied trust/violation/threat via gw
    res = gate.check(action, trust=gw.get("trust", 0.5),
                     violation=gw.get("violation", 0.0), threat=gw.get("threat"))
    if logger:
        logger.log(action, res)
    if res.decision in ("DELAY", "ESCALATE"):
        return {"status": res.decision, "gate": res.__dict__}
    return {"status": "ALLOW", "gate": res.__dict__, "result": fn()}
