"""v2 action-boundary metrics (Pre-reg v2 SS4, SS12.22-12.25)."""
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from src import llm_client
from tests.test_row_integrity import _fake_chat_json, _fake_chat_text


def _v(game, seed, arm, day, voter, vote, maj, maj_correct, lynched=None, lynched_is_mafia=None,
       target_is_mafia=None, is_village=True, parse_fail=False, delay_cause=None):
    return {"game_id": game, "requested_seed": seed, "arm": arm, "day": day, "voter": voter,
            "vote": vote, "majority_vote": maj, "majority_correct": maj_correct,
            "lynched": lynched, "lynched_is_mafia": lynched_is_mafia,
            "vote_target_is_mafia": target_is_mafia, "is_village": is_village,
            "parse_fail": parse_fail, "delay_cause": delay_cause}


class TestRowsCarryLynchAndTargetRole(unittest.TestCase):
    def test_vote_rows_have_lynch_and_target_fields(self):
        from src.eval import run_arena

        with patch.object(llm_client, "chat_text", side_effect=_fake_chat_text), \
                patch.object(llm_client, "chat_json", side_effect=_fake_chat_json), \
                patch.object(run_arena, "_log_progress", lambda *a, **k: None):
            g = run_arena.play_one(100900, design="team", arm="cot_village",
                                   run_dir=tempfile.mkdtemp(), max_days=2)
        rows = g._vote_rows
        self.assertTrue(rows)
        roles = {p.pid: p.role for p in g.players}
        for r in rows:
            self.assertIn("lynched", r)
            self.assertIn("lynched_is_mafia", r)
            self.assertIn("vote_target_is_mafia", r)
            if r["vote"] != "no-lynch":
                self.assertEqual(r["vote_target_is_mafia"], roles[int(r["vote"])] == "mafia")
            else:
                self.assertIsNone(r["vote_target_is_mafia"])
            if r["lynched"] is not None:
                self.assertEqual(r["lynched_is_mafia"], roles[int(r["lynched"])] == "mafia")
        # lynch field agrees with the engine history
        lynch_lines = [h for h in g.history if str(h["phase"]).startswith("result-") and "lynched" in h["text"]]
        days_with_lynch = {int(str(h["phase"]).split("-")[1]) for h in lynch_lines}
        self.assertEqual(days_with_lynch, {r["day"] for r in rows if r["lynched"] is not None})


class TestS1S2Confusion(unittest.TestCase):
    def _df(self):
        rows = []
        # seed 1: dmn: day0 lynch innocent, day1 mafia plurality held (needless)
        rows += [_v("d1", 1, "dmn_village", 0, 0, "3", "3", False, lynched="3", lynched_is_mafia=False, target_is_mafia=False),
                 _v("d1", 1, "dmn_village", 1, 0, "no-lynch", "5", True, delay_cause="low_confidence")]
        # seed 1: cot: day0 lynch mafia, day1 innocent lynched
        rows += [_v("c1", 1, "cot_village", 0, 0, "5", "5", True, lynched="5", lynched_is_mafia=True, target_is_mafia=True),
                 _v("c1", 1, "cot_village", 1, 0, "4", "4", False, lynched="4", lynched_is_mafia=False, target_is_mafia=False)]
        # seed 2: dmn: no plurality target at all (all abstain)
        rows += [_v("d2", 2, "dmn_village", 0, 0, "no-lynch", "no-lynch", True, parse_fail=True, delay_cause="json_failure")]
        rows += [_v("c2", 2, "cot_village", 0, 0, "6", "6", True, lynched="6", lynched_is_mafia=True, target_is_mafia=True)]
        return pd.DataFrame(rows)

    def test_s1_wrongful_lynches_per_game(self):
        from src.eval.action_boundary import wrongful_lynches_per_game
        s1 = wrongful_lynches_per_game(self._df())
        self.assertEqual(s1.set_index("game_id")["wrongful_lynches"].to_dict(),
                         {"d1": 1, "c1": 1, "d2": 0, "c2": 0})

    def test_s2_needless_hold_rate(self):
        from src.eval.action_boundary import needless_hold_rate_per_game
        s2 = needless_hold_rate_per_game(self._df()).set_index("game_id")
        self.assertAlmostEqual(s2.loc["d1", "needless_hold_rate"], 0.5)
        self.assertAlmostEqual(s2.loc["c1", "needless_hold_rate"], 0.0)
        self.assertTrue(pd.isna(s2.loc["d2", "needless_hold_rate"]))  # no plurality day

    def test_paired_contrast_excludes_seeds_without_s2_denominator(self):
        from src.eval.action_boundary import paired_contrast
        out = paired_contrast(self._df(), "needless_hold_rate", n_boot=200, n_perm=200)
        self.assertEqual(out["n_pairs"], 1)
        self.assertEqual(out["n_excluded_seeds"], 1)
        out1 = paired_contrast(self._df(), "wrongful_lynches", n_boot=200, n_perm=200)
        self.assertEqual(out1["n_pairs"], 2)
        self.assertAlmostEqual(out1["diff"], 0.0)

    def test_confusion_matrix_cells(self):
        from src.eval.action_boundary import confusion_matrix
        cm = confusion_matrix(self._df()).set_index("arm")
        self.assertEqual(int(cm.loc["dmn_village", "act_harmful"]), 1)
        self.assertEqual(int(cm.loc["dmn_village", "abstain_reasoned"]), 1)
        self.assertEqual(int(cm.loc["dmn_village", "abstain_failure"]), 1)
        self.assertEqual(int(cm.loc["cot_village", "act_correct"]), 2)



class TestS3Paired(unittest.TestCase):
    def test_delay_quality_per_game(self):
        from src.eval.action_boundary import delay_quality_per_game
        rows = [_v("d", 1, "dmn_village", 0, 0, "no-lynch", "3", False, delay_cause="low_confidence"),
                _v("d", 1, "dmn_village", 1, 0, "no-lynch", "5", True, delay_cause="low_confidence"),
                _v("d", 1, "dmn_village", 2, 0, "no-lynch", "4", False, parse_fail=True, delay_cause="json_failure")]
        out = delay_quality_per_game(pd.DataFrame(rows)).iloc[0]
        self.assertEqual(out["qualifying_days"], 2)  # JSON-failure day excluded
        self.assertAlmostEqual(out["delay_quality"], 0.5)


if __name__ == "__main__":
    unittest.main()
