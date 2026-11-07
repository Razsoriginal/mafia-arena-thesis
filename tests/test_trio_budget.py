import unittest

from src.llm_client import BillingExhausted


class TestTrioBudget(unittest.TestCase):
    def test_group_trios_preserves_seed_order(self):
        from src.eval.run_arena import _group_trios

        tasks = [{"requested_seed": 5000, "arm": a} for a in ("dmn_village", "cot_village", "cotx3_village")]
        tasks += [{"requested_seed": 5100, "arm": a} for a in ("dmn_village", "cot_village")]
        groups = _group_trios(tasks)
        self.assertEqual([g[0]["requested_seed"] for g in groups], [5000, 5100])
        self.assertEqual(len(groups[0]), 3)
        self.assertEqual(len(groups[1]), 2)

    def test_cumulative_and_budget(self):
        from src.eval.run_arena import _budget_exceeded, _cumulative_cost

        rows = [{"billed_cost_inr": 10.0}, {"billed_cost_inr": 5.5}, {}]
        self.assertAlmostEqual(_cumulative_cost(rows), 15.5)
        self.assertTrue(_budget_exceeded(rows, 15.0))
        self.assertFalse(_budget_exceeded(rows, 16.0))

    def test_retry_once_on_worker_failure(self):
        from src.eval.run_arena import _run_one_with_retry

        calls = {"n": 0}

        def flaky(task):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("boom")
            return {"row": {"game_id": task["run_id"]}}

        out = _run_one_with_retry({"run_id": "x"}, runner=flaky)
        self.assertEqual(out["row"]["game_id"], "x")
        self.assertEqual(calls["n"], 2)

    def test_billing_exhausted_never_retried(self):
        from src.eval.run_arena import _run_one_with_retry

        calls = {"n": 0}

        def broke(task):
            calls["n"] += 1
            raise BillingExhausted("402")

        with self.assertRaises(BillingExhausted):
            _run_one_with_retry({"run_id": "x"}, runner=broke)
        self.assertEqual(calls["n"], 1)

    def test_second_failure_propagates(self):
        from src.eval.run_arena import _run_one_with_retry

        def always_fail(task):
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            _run_one_with_retry({"run_id": "x"}, runner=always_fail)


if __name__ == "__main__":
    unittest.main()
