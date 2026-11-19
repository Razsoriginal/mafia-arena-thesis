"""E7-K4: exploratory scripts glob logs/runs/ and would now sweep in the
blind calibration epoch. They must skip confirmatory run folders."""
import re
import unittest

from src.explore.blind import is_blind_run


class TestExploreBlind(unittest.TestCase):
    def test_confirmatory_folders_are_blind(self):
        for name in ("mvp-team-01-cal", "logs/runs/mvp-team-01-cal/", "ops-A-01"):
            self.assertTrue(is_blind_run(name), name)
        for name in ("smoke-team-02", "pilot-clean-02", "explore-ops-01", "tau-sweep-01", "bridge-smoke-02"):
            self.assertFalse(is_blind_run(name), name)

    def test_every_globbing_explore_script_uses_the_guard(self):
        for mod in ("exformation_auc", "game_length"):
            src = open(f"src/explore/{mod}.py", encoding="utf-8").read()
            self.assertTrue(re.search(r"glob\.glob\(\"logs/runs", src), mod)
            self.assertIn("is_blind_run", src, f"{mod} reads logs/runs/* without the blind guard")


class TestNuisancePooled(unittest.TestCase):
    def test_mafia_nuisance_table_is_pooled_over_arms(self):
        """Game length and failure counts by arm are post-treatment
        outcomes (pre-reg v2 SS9 allows pooled values only)."""
        import importlib.util
        import tempfile

        import pandas as pd
        spec = importlib.util.spec_from_file_location("make_all", "scripts/make_all.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        g = pd.DataFrame([{"arm": a, "billed_cost_inr": 1.0 + i, "est_cost_inr": 1.0, "json_failures": i,
                           "days": 2 + i, "requested_seed": 5000} for i, a in enumerate(("dmn_village", "cot_village"))])
        t = pd.DataFrame([{"arm": "dmn_village", "trust_source": "probe", "parse_fail": False}])
        with tempfile.TemporaryDirectory() as td:
            df = m.nuisance(g, pd.DataFrame(), t, td)
            text = open(f"{td}/nuisance.md").read()
        self.assertNotIn("arm", df.columns)
        self.assertEqual(len(df), 1)
        self.assertEqual(int(df.loc[0, "games"]), 2)
        for arm in ("dmn_village", "cot_village"):
            self.assertNotIn(arm, text)


if __name__ == "__main__":
    unittest.main()
