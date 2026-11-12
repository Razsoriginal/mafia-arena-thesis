"""P0-K1: without --unblind, evaluate.py prints no outcome-by-arm quantity
for team data (no win rate, cascade, delay quality, abstention, S1/S2,
calibration by arm). With --unblind it prints the v2 action-boundary family."""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd


def _write(td):
    games, votes, trust = [], [], []
    for seed in (5000, 5100, 5200):
        for arm in ("dmn_village", "cot_village", "cotx3_village"):
            gid = f"c-{seed}-{arm}"
            games.append({"design": "team", "campaign": "c", "arm": arm, "requested_seed": seed,
                          "game_id": gid, "winner": "village" if arm == "dmn_village" else "mafia",
                          "days": 2, "json_failures": 0})
            for day in (0, 1):
                votes.append({"campaign": "c", "game_id": gid, "arm": arm, "requested_seed": seed,
                              "day": day, "voter": 2, "vote": "3", "majority_vote": "3",
                              "majority_correct": day == 0, "is_village": True, "plurality_tied": False,
                              "parse_fail": False, "delay_cause": None, "commitment": "",
                              "lynched": "3" if day == 0 else None, "lynched_is_mafia": True if day == 0 else None,
                              "vote_target_is_mafia": day == 0})
            trust.append({"campaign": "c", "game_id": gid, "arm": arm, "day": 0, "agent": 2,
                          "target": "3", "trust": 0.3, "target_is_mafia": True,
                          "trust_source": "probe", "parse_fail": False})
    paths = {}
    for name, rows in (("games", games), ("votes", votes), ("trust", trust)):
        paths[name] = os.path.join(td, f"{name}.parquet")
        pd.DataFrame(rows).to_parquet(paths[name], index=False)
    return paths


def _run(argv):
    from src.eval import evaluate
    buf = io.StringIO()
    with patch.object(sys, "argv", ["evaluate"] + argv), contextlib.redirect_stdout(buf):
        evaluate.main()
    return buf.getvalue()


class TestBlinding(unittest.TestCase):
    def test_blinded_output_has_no_arm_outcomes(self):
        with tempfile.TemporaryDirectory() as td:
            p = _write(td)
            out = _run(["--input", p["games"], "--votes", p["votes"], "--trust", p["trust"],
                        "--campaign", "c", "--pending-file", os.path.join(td, "none.json"), "--n-boot", "100"])
        low = out.lower()
        for banned in ("win-rate", "cascade", "delay_quality", "delay game-cluster", "abstention",
                       "ece", "brier", "auc", "wrongful", "needless", "s1", "s2"):
            self.assertNotIn(banned, low, f"blinded output leaked '{banned}'")
        self.assertIn("blinded", low)

    def test_unblinded_output_has_action_boundary_family(self):
        with tempfile.TemporaryDirectory() as td:
            p = _write(td)
            out = _run(["--input", p["games"], "--votes", p["votes"], "--trust", p["trust"],
                        "--campaign", "c", "--unblind", "--pending-file", os.path.join(td, "none.json"),
                        "--n-boot", "100"])
        self.assertIn("S1 wrongful_lynches", out)
        self.assertIn("S2 needless_hold_rate", out)
        self.assertIn("Holm", out)



class TestRunnerConsoleBlinding(unittest.TestCase):
    def test_team_game_line_has_no_winner(self):
        from src.eval import run_arena

        args = type("A", (), {"no_canonical": True, "out": "x"})()
        with tempfile.TemporaryDirectory() as td:
            row = {"run_tag": "t", "game_id": "c-5000-dmn_village", "winner": "village", "days": 3,
                   "focal_role": "villager", "json_failures": 0, "design": "team", "arm": "dmn_village",
                   "campaign": "c", "requested_seed": 5000}
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                run_arena._record_result({"row": row, "votes": [], "trust": []}, args, td, [],
                                         canonical=False, ledger_path=None)
        out = buf.getvalue().lower()
        self.assertNotIn("village in", out)
        self.assertNotIn("winner", out)
        self.assertIn("3 days", out)

    def test_team_run_end_summary_has_no_winner_table(self):
        import inspect
        from src.eval import run_arena
        src = inspect.getsource(run_arena.main)
        self.assertIn("_print_end_summary(df, args)", src)
        df = pd.DataFrame([{"focal": "dmn_village", "winner": "village", "focal_role": "doctor", "design": "team"}])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_arena._print_end_summary(df, type("A", (), {"calibration": False, "design": "team"})())
        self.assertNotIn("village", buf.getvalue().replace("dmn_village", ""))


if __name__ == "__main__":
    unittest.main()
