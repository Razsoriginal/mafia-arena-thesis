import unittest

import pandas as pd


def _votes():
    rows = []
    # game g1 day0 wrong plurality 5 (innocent), village voters: 0 resists, 1 follows, 2 abstains
    rows += [
        {"run_tag": "t", "game_id": "g1", "day": 0, "voter": 0, "vote": "3", "majority_vote": "5", "majority_correct": False, "is_village": True, "arm": "dmn_village", "delay_cause": None},
        {"run_tag": "t", "game_id": "g1", "day": 0, "voter": 1, "vote": "5", "majority_vote": "5", "majority_correct": False, "is_village": True, "arm": "dmn_village", "delay_cause": None},
        {"run_tag": "t", "game_id": "g1", "day": 0, "voter": 2, "vote": "no-lynch", "majority_vote": "5", "majority_correct": False, "is_village": True, "arm": "dmn_village", "delay_cause": "low_confidence"},
        {"run_tag": "t", "game_id": "g1", "day": 0, "voter": 5, "vote": "5", "majority_vote": "5", "majority_correct": False, "is_village": False, "arm": "dmn_village", "delay_cause": None},
    ]
    return pd.DataFrame(rows)


class TestTeamMetrics(unittest.TestCase):
    def test_team_cascade_excludes_abstain_and_mafia(self):
        from src.eval.metrics import team_cascade_resistance

        # village non-abstain on wrong plurality: voter0 resisted, voter1 followed -> 0.5
        self.assertAlmostEqual(team_cascade_resistance(_votes()), 0.5)

    def test_team_delay_quality_once_per_game_day(self):
        from src.eval.metrics import team_delay_quality

        # one game-day with a village delay, plurality innocent -> 1.0 counted once
        self.assertAlmostEqual(team_delay_quality(_votes()), 1.0)

    def test_team_delay_excludes_json_failure(self):
        from src.eval.metrics import team_delay_quality

        df = _votes()
        df.loc[df["voter"] == 2, "delay_cause"] = "json_failure"
        self.assertTrue(pd.isna(team_delay_quality(df)))

    def test_old_focal_metrics_unchanged_signature(self):
        from src.eval.metrics import cascade_resistance, delay_quality

        df = _votes()
        df["is_focal"] = df["voter"] == 0
        self.assertAlmostEqual(cascade_resistance(df), 1.0)


class TestStats(unittest.TestCase):
    def test_wilson_contains_point(self):
        from src.eval.stats import wilson_interval

        lo, hi = wilson_interval(50, 100)
        self.assertLess(lo, 0.5)
        self.assertGreater(hi, 0.5)
        self.assertGreater(lo, 0.0)

    def test_paired_bootstrap_identical_is_zero(self):
        from src.eval.stats import paired_bootstrap_diff

        out = paired_bootstrap_diff([1, 0, 1, 1], [1, 0, 1, 1], n_boot=200, seed=1)
        self.assertEqual(out["diff"], 0.0)
        self.assertEqual(out["ci_low"], 0.0)
        self.assertEqual(out["ci_high"], 0.0)

    def test_paired_bootstrap_positive(self):
        from src.eval.stats import paired_bootstrap_diff

        out = paired_bootstrap_diff([1] * 20, [0] * 20, n_boot=200, seed=1)
        self.assertEqual(out["diff"], 1.0)

    def test_mcnemar_no_discordant(self):
        from src.eval.stats import mcnemar_exact

        out = mcnemar_exact([1, 0, 1], [1, 0, 1])
        self.assertEqual(out["b"], 0)
        self.assertEqual(out["c"], 0)
        self.assertEqual(out["p_value"], 1.0)

    def test_mcnemar_discordant_counts(self):
        from src.eval.stats import mcnemar_exact

        out = mcnemar_exact([1, 1, 0], [0, 0, 0])
        self.assertEqual(out["b"], 2)
        self.assertEqual(out["c"], 0)
        self.assertLess(out["p_value"], 1.0)

    def test_cluster_bootstrap_games(self):
        from src.eval.stats import cluster_bootstrap_mean

        df = pd.DataFrame({"game_id": ["a", "a", "b", "b"], "x": [1.0, 1.0, 0.0, 0.0]})
        out = cluster_bootstrap_mean(df, "x", "game_id", n_boot=200, seed=2)
        self.assertAlmostEqual(out["mean"], 0.5)
        self.assertIn("ci_low", out)


if __name__ == "__main__":
    unittest.main()
