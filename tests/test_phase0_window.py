"""P0-S2: seed-trio window. Trios stay atomic, at most --trio-window are
in flight, the cap projection counts in-flight trios, and the trio index
comes from the seed so --resume cannot bypass the calibration GO gate."""
import os
import threading
import time
import unittest

import pandas as pd

from src.eval import run_arena
from tests.round2_support import _RunEnv, _team_row


class TestTrioWindow(_RunEnv):
    def setUp(self):
        super().setUp()
        self._old_exec = os.environ.get("MAFIA_GAME_EXECUTOR")
        os.environ["MAFIA_GAME_EXECUTOR"] = "thread"
        os.environ["MAFIA_CALIBRATION_GO"] = os.path.join(self._td, "go.json")
        os.environ["MAFIA_CALIBRATION_REPORT"] = os.path.join(self._td, "cal.json")

    def tearDown(self):
        if self._old_exec is None:
            os.environ.pop("MAFIA_GAME_EXECUTOR", None)
        else:
            os.environ["MAFIA_GAME_EXECUTOR"] = self._old_exec
        os.environ.pop("MAFIA_CALIBRATION_GO", None)
        os.environ.pop("MAFIA_CALIBRATION_REPORT", None)
        super().tearDown()

    def test_window_limits_trios_in_flight_and_keeps_them_atomic(self):
        live, peak, lock = set(), [0], threading.Lock()

        def slow(task):
            with lock:
                live.add(task["requested_seed"])
                peak[0] = max(peak[0], len(live))
            time.sleep(0.05)
            row = _team_row(task)
            with lock:
                # a seed leaves "live" only when its last arm finishes
                done = sum(1 for c in self.calls if str(task["requested_seed"]) in c)
                if done >= 3:
                    live.discard(task["requested_seed"])
            return row

        self._run(self._base("camp-w", "w1", trios=4, workers=6, trio_window=2), runner=slow)
        df = pd.read_parquet(self.out)
        self.assertEqual(len(df), 12)
        self.assertEqual(sorted(df.requested_seed.unique()), [9000, 9100, 9200, 9300])
        self.assertLessEqual(peak[0], 2)
        self.assertGreaterEqual(peak[0], 2)

    def test_cap_projection_counts_in_flight_trios(self):
        # planned Rs.10/trio, cap Rs.25: two trios fit (10 + 10), a third does not.
        self._run(self._base("camp-c", "c1", trios=5, workers=6, trio_window=3,
                             planned_trio_cost=10, budget_cap=25))
        df = pd.read_parquet(self.out)
        self.assertEqual(sorted(df.requested_seed.unique()), [9000, 9100])

    def test_resume_cannot_bypass_calibration_gate(self):
        # Calibration batch: 20 trios, then the pause writes the report.
        self._run(self._base("camp-g", "g1", trios=20, workers=1))
        self.assertTrue(os.path.exists(os.environ["MAFIA_CALIBRATION_REPORT"]))
        n_before = len(self.calls)
        # Resume asking for 21 trios: only trio index 20 (seed 11000) is
        # missing, and it must be refused without a GO.
        self._run(self._base("camp-g", "g2", trios=21, workers=1) + ["--resume"])
        self.assertEqual(len(self.calls), n_before, "trio 20 ran without a GO")
        df = pd.read_parquet(self.out)
        self.assertNotIn(11000, set(df.requested_seed))


if __name__ == "__main__":
    unittest.main()
