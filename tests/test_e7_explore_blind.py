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


if __name__ == "__main__":
    unittest.main()
