import os
import unittest

import pandas as pd


class TestPilotRegression(unittest.TestCase):
    def test_pilot_metrics_unchanged(self):
        if not (os.path.exists("logs/games.parquet") and os.path.exists("logs/votes.parquet")
                and os.path.exists("logs/trust.parquet")):
            self.fail("canonical pilot parquet missing; regression cannot run")
        from src.eval.metrics import brier, cascade_resistance, delay_quality, ece

        tdf = pd.read_parquet("logs/trust.parquet")
        vdf = pd.read_parquet("logs/votes.parquet")
        pairs = [(float(t), 0 if bool(m) else 1) for t, m in zip(tdf["trust"], tdf["target_is_mafia"])]
        self.assertEqual(len(pairs), 41)
        self.assertAlmostEqual(ece(pairs), 0.105, places=3)
        self.assertAlmostEqual(brier(pairs), 0.193, places=3)
        self.assertAlmostEqual(cascade_resistance(vdf), 0.333, places=3)
        self.assertAlmostEqual(delay_quality(vdf), 0.75, places=3)


if __name__ == "__main__":
    unittest.main()
