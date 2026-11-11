import fcntl
import json
import os
import tempfile
import threading
import time
import unittest

from src.eval import run_arena

from tests.round2_support import _row, _RunEnv


class TestLedgerG3G5(unittest.TestCase):
    def test_truncated_last_line_is_fatal(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "ledger.jsonl")
            with open(p, "w", encoding="utf-8") as f:
                f.write(json.dumps({"cost_inr": 10.0}) + "\n")
                f.write(json.dumps({"cost_inr": 5.0}) + "\n")
                f.write('{"cost_inr": 99')
            with self.assertRaises(RuntimeError):
                run_arena._ledger_total(p)

    def test_concurrent_appends_do_not_interleave(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "ledger.jsonl")

            def worker(n):
                for _ in range(25):
                    run_arena._append_ledger(
                        p, _row(seed=9000 + n, cost=1.0), campaign="c")

            threads = [threading.Thread(target=worker, args=(n,)) for n in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            self.assertEqual(len(run_arena._ledger_entries(p)), 100)
            self.assertAlmostEqual(run_arena._ledger_total(p), 100.0)

    def test_append_blocks_while_lock_is_held(self):
        """Deterministic lock proof: a held lock must block the append."""
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "ledger.jsonl")
            with open(p + ".lock", "a+", encoding="utf-8") as lf:
                fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                t = threading.Thread(target=run_arena._append_ledger,
                                     args=(p, _row(cost=1.0)),
                                     kwargs={"campaign": "c"})
                t.start()
                time.sleep(0.3)
                self.assertTrue(t.is_alive(),
                                "append did not wait for the ledger lock")
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
                t.join(timeout=5)
                self.assertFalse(t.is_alive())
            self.assertEqual(len(run_arena._ledger_entries(p)), 1)

    def test_rerun_spend_is_kept_not_deduplicated(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "ledger.jsonl")
            run_arena._append_ledger(p, _row(cost=5.0), campaign="c",
                                     status="discarded")
            run_arena._append_ledger(p, _row(cost=5.0), campaign="c",
                                     status="kept")
            entries = run_arena._ledger_entries(p)
            self.assertEqual(len(entries), 2)
            self.assertAlmostEqual(run_arena._ledger_total(p), 10.0)
            self.assertEqual([e["attempt"] for e in entries], [1, 2])
            self.assertEqual([e["status"] for e in entries],
                             ["discarded", "kept"])
            rep = run_arena._calibration_report(
                [dict(_row(cost=5.0), ledger_status="discarded"),
                 dict(_row(cost=5.0), ledger_status="kept")], [], [],
                probe_cost_per_game=0.1)
            self.assertEqual(set(rep), run_arena.CALIBRATION_KEYS)
            self.assertEqual(rep["n_games"], 1)
            self.assertEqual(rep["discarded_spend_inr"], 5.0)
            self.assertEqual(rep["probe_cost_per_game_inr"], 0.1)


class TestInFlightProjectionG4(_RunEnv):
    def test_fresh_ledger_cap_5_runs_zero_trios(self):
        self._run(self._base("g4", "g4", trios=1) + ["--budget-cap", "5"])
        self.assertEqual(self.calls, [])
        self.assertFalse(os.path.exists(self.out))

    def test_projection_uses_measured_mean_when_higher(self):
        rows = [{"requested_seed": 9000, "billed_cost_inr": 12.0},
                {"requested_seed": 9000, "billed_cost_inr": 12.0},
                {"requested_seed": 9000, "billed_cost_inr": 12.0}]
        self.assertAlmostEqual(run_arena._projected_trio_cost(rows, 8.13), 36.0)
        self.assertAlmostEqual(run_arena._projected_trio_cost([], 8.13), 8.13)


if __name__ == "__main__":
    unittest.main()
