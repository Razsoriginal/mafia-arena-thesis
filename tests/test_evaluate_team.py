import unittest

import pandas as pd


class TestEvaluateTeam(unittest.TestCase):
    def test_filter_team_and_campaign(self):
        from src.eval.evaluate import _filter_team

        df = pd.DataFrame([
            {"design": "team", "campaign": "a", "arm": "dmn_village"},
            {"design": "team", "campaign": "b", "arm": "dmn_village"},
            {"design": "focal", "campaign": "a", "arm": "dmn_tpn"},
        ])
        self.assertEqual(len(_filter_team(df)), 2)
        self.assertEqual(len(_filter_team(df, "a")), 1)

    def test_pairs_reports_self_and_missing_drops(self):
        from src.eval.evaluate import _pairs

        df = pd.DataFrame([
            {"agent": "1", "target": "1", "trust": 0.5, "target_is_mafia": False},
            {"agent": "1", "target": "2", "trust": 0.8, "target_is_mafia": False},
            {"agent": "1", "target": "3", "trust": float("nan"),
             "target_is_mafia": True, "parse_fail": True},
        ])
        pairs, n_self, n_missing = _pairs(df)
        self.assertEqual(n_self, 1)
        self.assertEqual(n_missing, 1)
        self.assertEqual(pairs, [(0.8, 1)])

    def test_paired_outcomes_align_by_seed(self):
        from src.eval.evaluate import _paired_outcomes

        df = pd.DataFrame([
            {"arm": "dmn_village", "requested_seed": 5000, "winner": "village"},
            {"arm": "dmn_village", "requested_seed": 5100, "winner": "mafia"},
            {"arm": "cot_village", "requested_seed": 5000, "winner": "mafia"},
            {"arm": "cot_village", "requested_seed": 5100, "winner": "mafia"},
        ])
        av, bv, common = _paired_outcomes(df)
        self.assertEqual(av, [1, 0])
        self.assertEqual(bv, [0, 0])
        self.assertEqual(common, [5000, 5100])

    def test_pending_blocks_unblind_listing(self):
        import json
        import os
        import tempfile

        from src.eval.evaluate import _pending_for_campaign

        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "pending.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump([{"campaign": "camp-a", "requested_seed": 5000}], f)
            self.assertEqual(len(_pending_for_campaign(p, "camp-a")), 1)
            self.assertEqual(len(_pending_for_campaign(p, "camp-b")), 0)


if __name__ == "__main__":
    unittest.main()
