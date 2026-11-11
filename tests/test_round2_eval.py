import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from src.eval import run_arena


class TestEvaluateMainV5(unittest.TestCase):
    def _fixture(self, td):
        seeds = [5000, 5100]
        arms = ["dmn_village", "cot_village", "cotx3_village"]
        games, votes, trust = [], [], []
        for seed in seeds:
            for i, arm in enumerate(arms):
                gid = f"camp-e2e-{seed}-{arm}"
                games.append({
                    "design": "team", "campaign": "camp-e2e", "arm": arm,
                    "requested_seed": seed, "game_id": gid,
                    "winner": "village" if (seed + i) % 2 else "mafia",
                    "days": 2, "json_failures": 0, "provider": "aicredits",
                    "model": "m", "gate": "llm", "night_mode": "llm",
                })
                votes += [
                    {"run_tag": "e2e", "campaign": "camp-e2e", "game_id": gid,
                     "day": 0, "voter": 0, "vote": "no-lynch",
                     "majority_vote": "3", "majority_correct": False,
                     "is_village": True, "delay_cause": None,
                     "commitment": "", "arm": arm},
                    {"run_tag": "e2e", "campaign": "camp-e2e", "game_id": gid,
                     "day": 0, "voter": 1, "vote": "no-lynch",
                     "majority_vote": "3", "majority_correct": False,
                     "is_village": True, "delay_cause": None,
                     "commitment": "", "arm": arm},
                    {"run_tag": "e2e", "campaign": "camp-e2e", "game_id": gid,
                     "day": 1, "voter": 0, "vote": "4",
                     "majority_vote": "3", "majority_correct": False,
                     "is_village": True, "delay_cause": None,
                     "commitment": "", "arm": arm},
                ]
                trust += [
                    {"campaign": "camp-e2e", "game_id": gid, "arm": arm,
                     "trust_source": "probe", "agent": 0, "target": "1",
                     "trust": 0.6, "target_is_mafia": False,
                     "parse_fail": False, "verified": False},
                    {"campaign": "camp-e2e", "game_id": gid, "arm": arm,
                     "trust_source": "probe", "agent": 0, "target": "2",
                     "trust": 0.4, "target_is_mafia": True,
                     "parse_fail": False, "verified": False},
                    {"campaign": "camp-e2e", "game_id": gid, "arm": arm,
                     "trust_source": "decision", "agent": 0, "target": "1",
                     "trust": 0.7, "target_is_mafia": False,
                     "parse_fail": False, "verified": True},
                ]
        paths = {k: os.path.join(td, f"{k}.parquet")
                 for k in ("games", "votes", "trust")}
        pd.DataFrame(games).to_parquet(paths["games"], index=False)
        pd.DataFrame(votes).to_parquet(paths["votes"], index=False)
        pd.DataFrame(trust).to_parquet(paths["trust"], index=False)
        return paths

    def _run_eval(self, paths, extra):
        from src.eval import evaluate

        argv = ["evaluate", "--input", paths["games"],
                "--votes", paths["votes"], "--trust", paths["trust"],
                "--campaign", "camp-e2e", "--n-boot", "50",
                "--pending-file", os.path.join(os.path.dirname(paths["games"]),
                                               "pending.json")] + extra
        out = io.StringIO()
        with patch.object(sys, "argv", argv), contextlib.redirect_stdout(out):
            evaluate.main()
        return out.getvalue()

    def test_blinded_default_hides_outcomes(self):
        with tempfile.TemporaryDirectory() as td:
            out = self._run_eval(self._fixture(td), [])
        self.assertIn("outcomes blinded", out)
        self.assertNotIn("PRIMARY dmn-cot", out)

    def test_unblind_reports_paired_and_clustered(self):
        with tempfile.TemporaryDirectory() as td:
            out = self._run_eval(self._fixture(td), ["--unblind"])
        self.assertIn("PRIMARY dmn-cot paired diff", out)
        self.assertIn("KEY SECONDARY dmn-cotx3 paired diff", out)
        self.assertIn("cascade game-cluster 95% CI", out)
        self.assertIn("delay game-cluster 95% CI", out)
        self.assertIn("Probe calibration", out)
        self.assertIn("Decision-linked calibration", out)

    def test_pending_campaign_blocks_unblind(self):
        with tempfile.TemporaryDirectory() as td:
            paths = self._fixture(td)
            with open(os.path.join(td, "pending.json"), "w",
                      encoding="utf-8") as f:
                json.dump([{"campaign": "camp-e2e", "requested_seed": 5000}], f)
            with self.assertRaises(SystemExit):
                self._run_eval(paths, ["--unblind"])


class TestCalibrationWhitelistV8(unittest.TestCase):
    def test_report_keys_are_exactly_the_whitelist(self):
        rep = run_arena._calibration_report([], [], [], probe_cost_per_game=None)
        self.assertEqual(set(rep), run_arena.CALIBRATION_KEYS)
        bad = dict(rep, winner="village")
        self.assertNotEqual(set(bad), run_arena.CALIBRATION_KEYS)


if __name__ == "__main__":
    unittest.main()
