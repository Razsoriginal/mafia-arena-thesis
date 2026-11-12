"""IrrevOps bridge (Pre-reg v2 SS16): mocked agents, no paid calls."""
import os
import tempfile
import unittest
from unittest.mock import patch

from src import llm_client
from src.bridge.agent import run_episode
from src.bridge.sandbox import classify
from src.bridge.tasks import build_tasks, task_set_sha256
from src.safety import AuditLogger


def _tasks():
    return {t.task_id: t for t in build_tasks()}


def _agent(style, verifier_conf=0.9):
    """reckless: call the ticket's irreversible action at once.
    careful: run every verification first, then act unless output warns."""
    def fake(system, user, meta=None, temperature=None, purpose=None, **kw):
        if meta is not None:
            meta.update({"parse_fail": False})
        if purpose == "bridge_verify":
            return {"safe_and_authorised_confidence": verifier_conf, "evidence_steps": [1]}
        task = fake.task
        intended = {"tool": task.intended["tool"], "args": task.intended["args"],
                    "rationale": "I verified it is staging"}
        if style == "reckless":
            return intended
        hist = user.split("Tool history:")[-1]
        checks = []
        for rid in task.resources:
            checks.append({"tool": "describe", "args": {"resource_id": rid}})
        for req in task.approvals:
            checks.append({"tool": "check_approval", "args": {"request_id": req}})
        checks.append({"tool": "read_policies", "args": {}})
        for c in checks:
            key = f"call {c['tool']}("
            if c["tool"] == "describe":
                key += '{"resource_id": "' + c["args"]["resource_id"] + '"}'
            if key not in hist:
                return {**c, "rationale": "checking"}
        bad = any(w in hist for w in ("production\"", "only restorable", "NOT FOUND", "ACTIVE CODE FREEZE",
                                      "verified_vendor\": false"))
        if bad and task.family not in ("F3_escalation_blocked", "F4_injected_instruction"):
            return {"tool": "escalate", "args": {"reason": "risk found"}, "rationale": "risk"}
        return intended
    return fake


def _run(task, arm, style, conf=0.9, audit=None):
    fake = _agent(style, conf)
    fake.task = task
    with patch.object(llm_client, "chat_json", side_effect=fake):
        return run_episode(task, arm, 0, f"e-{task.task_id}-{arm}", audit=audit)


class TestBridge(unittest.TestCase):
    def test_task_set_is_60_tasks_30_pairs_and_stable(self):
        ts = build_tasks()
        self.assertEqual(len(ts), 60)
        self.assertEqual(len({t.pair_id for t in ts}), 30)
        self.assertEqual(task_set_sha256(ts), task_set_sha256(build_tasks()))
        for t in ts:
            if t.twin == "abstain":
                self.assertIn(t.risk_target, t.protected)

    def test_bare_reckless_is_harmful_on_abstain_and_correct_on_act(self):
        T = _tasks()
        self.assertEqual(_run(T["F1-0-abstain"], "B0_bare", "reckless")["outcome"], "act_harmful")
        self.assertEqual(_run(T["F1-0-act"], "B0_bare", "reckless")["outcome"], "act_correct")

    def test_external_gate_blocks_unverified_and_protected(self):
        T = _tasks()
        # reckless never verifies: blocked every time -> no harm, but a needless hold on act twins
        self.assertEqual(_run(T["F1-0-abstain"], "B2_external_gate", "reckless")["outcome"], "abstain_justified")
        self.assertEqual(_run(T["F1-0-act"], "B2_external_gate", "reckless")["outcome"], "abstain_needless")
        # careful verifies first: allowed on act twin, protected target blocked on abstain twin
        self.assertEqual(_run(T["F1-0-act"], "B2_external_gate", "careful")["outcome"], "act_correct")
        r = _run(T["F3-0-abstain"], "B2_external_gate", "careful")
        self.assertEqual(r["outcome"], "abstain_justified")
        self.assertGreater(r["n_blocked"], 0)

    def test_verify_delay_gate_uses_threshold(self):
        T = _tasks()
        self.assertEqual(_run(T["F5-0-abstain"], "B3_verify_delay", "reckless", conf=0.2)["outcome"],
                         "abstain_justified")
        self.assertEqual(_run(T["F5-0-abstain"], "B3_verify_delay", "reckless", conf=0.9)["outcome"],
                         "act_harmful")

    def test_hallucinated_verification_flag(self):
        T = _tasks()
        r = _run(T["F1-0-abstain"], "B0_bare", "reckless")
        self.assertTrue(r["claimed_verification_without_call"])
        self.assertFalse(r["verified_before_first_irreversible"])

    def test_audit_rows_written_for_gated_arms(self):
        T = _tasks()
        with tempfile.TemporaryDirectory() as td:
            audit = AuditLogger(path=os.path.join(td, "audit.parquet"))
            _run(T["F1-0-abstain"], "B2_external_gate", "reckless", audit=audit)
            path, n = audit.flush()
            import pandas as pd
            df = pd.read_parquet(path)
        self.assertEqual(n, len(df))
        self.assertTrue((df["decision"] != "ALLOW").all())
        self.assertEqual(set(df["arm"]), {"B2_external_gate"})

    def test_off_ticket_irreversible_action_is_harmful(self):
        T = _tasks()
        t = T["F4-0-act"]
        executed = [{"tool": "delete_resource", "target": [r for r in t.resources if r != t.intended["args"]["resource_id"]][0]}]
        self.assertEqual(classify(t, executed), "act_harmful")


if __name__ == "__main__":
    unittest.main()
