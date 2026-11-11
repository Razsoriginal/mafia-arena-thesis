import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from src import llm_client
from src.eval import run_arena


def _synthetic(cost_by_arm, fail_arm=None, billing_arm=None):
    def fake(task):
        arm = task["arm"]
        if billing_arm and arm == billing_arm:
            raise llm_client.BillingExhausted("402 insufficient balance")
        if fail_arm and arm == fail_arm:
            raise RuntimeError("boom twice")
        cost = cost_by_arm.get(arm, 1.0)
        row = {
            "run_tag": task["run_tag"], "game_id": task["run_id"],
            "seed": task["requested_seed"], "requested_seed": task["requested_seed"],
            "focal": arm, "focal_pid": 0, "gate": "llm", "night_mode": "llm",
            "provider": "aicredits", "model": "meta/muse-spark-1.3-contributor",
            "jev_model": "x", "git_sha": "abc123", "tau": 0.35,
            "evt_threshold": 0.6, "ablate": "", "winner": "village", "days": 2,
            "focal_role": "villager", "majority_correct": True,
            "delay_cause": None, "parse_fail": False, "trust_json": "{}",
            "trace_json": "{}", "prompt_tokens": 10, "completion_tokens": 5,
            "est_cost_inr": cost, "billed_cost_inr": cost, "json_failures": 0,
            "jev_stub": None, "design": "team",
            "campaign": task.get("campaign", ""), "arm": arm,
            "village_arm": arm, "mafia_arm": "cot",
        }
        return {"row": row, "votes": [], "trust": []}
    return fake


class _MainEnv(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.mkdtemp(prefix="mafia-run-")
        self._env = {}
        for k, v in {
            "MAFIA_SPEND_LEDGER": os.path.join(self._td, "ledger.jsonl"),
            "MAFIA_PENDING_FILE": os.path.join(self._td, "pending.json"),
            "MAFIA_RUNS_DIR": os.path.join(self._td, "runs"),
            "MAFIA_RAW_DIR": os.path.join(self._td, "raw"),
        }.items():
            self._env[k] = os.environ.get(k)
            os.environ[k] = v
        self.out = os.path.join(self._td, "games.parquet")

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _run_main(self, argv, fake):
        with patch.object(sys, "argv", ["run_arena"] + argv), patch.object(
            run_arena, "_run_task_once", side_effect=fake
        ), patch.object(run_arena, "_log_progress", lambda *a, **k: None):
            run_arena.main()

    def _ledger(self):
        p = os.environ["MAFIA_SPEND_LEDGER"]
        if not os.path.exists(p):
            return []
        with open(p, encoding="utf-8") as f:
            return [json.loads(x) for x in f if x.strip()]


class TestCumulativeLedger(_MainEnv):
    ARGS = ["--design", "team", "--arms", "dmn_village,cot_village,cotx3_village",
            "--seed", "9000", "--workers", "1", "--tau", "0.35", "--budget-cap", "35"]

    def test_second_invocation_sees_first_invocations_spend(self):
        fake = _synthetic({"dmn_village": 10.0, "cot_village": 10.0, "cotx3_village": 10.0})
        self._run_main(self.ARGS + ["--campaign", "camp-a", "--run-tag", "r1",
                                    "--trios", "1", "--out", self.out], fake)
        self.assertAlmostEqual(run_arena._ledger_total(os.environ["MAFIA_SPEND_LEDGER"]), 30.0)
        self.assertEqual(len(pd.read_parquet(self.out)), 3)
        # Second invocation asks for 2 more trios; in-flight projection
        # (ledger 30 + projected trio > cap 35) must start zero (G4).
        self._run_main(self.ARGS + ["--campaign", "camp-a", "--run-tag", "r2",
                                    "--seed", "9000", "--start-trio", "1",
                                    "--trios", "2", "--out", self.out,
                                    "--resume"], fake)
        self.assertEqual(len(pd.read_parquet(self.out)), 3)
        self.assertAlmostEqual(run_arena._ledger_total(os.environ["MAFIA_SPEND_LEDGER"]), 30.0)
        df = pd.read_parquet(self.out)
        self.assertEqual(df.duplicated(subset=["campaign", "requested_seed", "arm"]).sum(), 0)

    def test_billed_missing_falls_back_to_estimate(self):
        row = {"billed_cost_inr": 0, "est_cost_inr": 2.5}
        self.assertEqual(run_arena._effective_cost(row), 2.5)
        self.assertEqual(run_arena._cumulative_cost([row]), 2.5)


class TestAtomicTrio(_MainEnv):
    ARGS = ["--design", "team", "--arms", "dmn_village,cot_village,cotx3_village",
            "--seed", "9000", "--workers", "1", "--tau", "0.35", "--budget-cap", "1600"]

    def test_402_mid_trio_is_pending_and_resume_is_idempotent(self):
        costs = {"dmn_village": 5.0, "cot_village": 5.0, "cotx3_village": 5.0}
        flaky = _synthetic(costs, billing_arm="cot_village")
        self._run_main(self.ARGS + ["--campaign", "camp-b", "--run-tag", "b1",
                                    "--trios", "1", "--out", self.out], flaky)
        # No canonical rows for the incomplete trio; spend still ledgered.
        self.assertFalse(os.path.exists(self.out))
        self.assertEqual(len(self._ledger()), 1)
        pending = run_arena._load_pending(os.environ["MAFIA_PENDING_FILE"])
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["requested_seed"], 9000)
        good = _synthetic(costs)
        self._run_main(self.ARGS + ["--campaign", "camp-b", "--run-tag", "b2",
                                    "--trios", "1", "--out", self.out, "--resume"], good)
        df = pd.read_parquet(self.out)
        self.assertEqual(len(df), 3)
        self.assertEqual(df.duplicated(subset=["campaign", "requested_seed", "arm"]).sum(), 0)
        self.assertEqual(run_arena._load_pending(os.environ["MAFIA_PENDING_FILE"]), [])

    def test_second_worker_failure_leaves_trio_pending(self):
        costs = {"dmn_village": 5.0, "cot_village": 5.0, "cotx3_village": 5.0}
        failing = _synthetic(costs, fail_arm="cotx3_village")
        self._run_main(self.ARGS + ["--campaign", "camp-c", "--run-tag", "c1",
                                    "--trios", "1", "--out", self.out], failing)
        self.assertFalse(os.path.exists(self.out))
        pending = run_arena._load_pending(os.environ["MAFIA_PENDING_FILE"])
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["reason"], "worker_failure")


class TestCalibrationReport(unittest.TestCase):
    def test_report_has_no_arm_outcomes(self):
        rows = [{"arm": "dmn_village", "billed_cost_inr": 2.0, "est_cost_inr": 2.0,
                 "days": 2, "json_failures": 0, "requested_seed": 5000, "winner": "village"},
                {"arm": "cot_village", "billed_cost_inr": 1.0, "est_cost_inr": 1.0,
                 "days": 3, "json_failures": 1, "requested_seed": 5000, "winner": "mafia"}]
        rep = run_arena._calibration_report(rows, [], [])
        self.assertNotIn("winner", json.dumps(rep).lower().replace("winners", ""))
        self.assertIn("cost_per_arm_inr", rep)
        self.assertIn("within_seed_days_correlation", rep)
        self.assertIn("cotx3_nonunanimity_share", rep)


if __name__ == "__main__":
    unittest.main()
