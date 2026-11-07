import tempfile
import unittest
from unittest.mock import patch

from src import llm_client


def _fake_chat_text(system, user, temperature=None, log=True, response_format=None):
    return "I am watching the discussion."


def _fake_chat_json(system, user, meta=None, temperature=None):
    if meta is not None:
        meta.update({"parse_fail": False, "repaired": False, "empty_raw": False, "error": None, "raw_len": 1})
    if "imaginative mind" in system:
        return {"hypotheses": [{"suspect": "1", "motive": "quiet", "confidence": 0.8}]}
    if "verifier mind" in system:
        return {"verified": [{"suspect": "1", "evidence_spans": [0], "contradiction_found": False, "revised_confidence": 0.8}]}
    if "Output trust scores" in system:
        return {"trust": {str(i): 0.6 for i in range(7)}}
    if "night" in system.lower() or "You choose a night action" in system:
        return {"kill": "0", "save": "0", "check": "1"}
    if "must justify" in system:
        return {"vote": "1", "reason": "t0 shows a claim"}
    return {"vote": "1", "reason": "suspect"}


class TestSchema(unittest.TestCase):
    def test_plurality_tied_helper(self):
        from src.eval.run_arena import _plurality_info

        maj, tied = _plurality_info({"0": "1", "1": "2", "2": "1", "3": "2"})
        self.assertTrue(tied)
        maj2, tied2 = _plurality_info({"0": "1", "1": "1", "2": "2"})
        self.assertEqual(maj2, "1")
        self.assertFalse(tied2)
        maj3, tied3 = _plurality_info({"0": "no-lynch", "1": "no-lynch"})
        self.assertEqual(maj3, "no-lynch")
        self.assertFalse(tied3)

    def test_team_game_rows_have_new_schema(self):
        from src.eval import run_arena
        from src.eval.run_arena import play_one

        with tempfile.TemporaryDirectory() as td, patch.object(
            llm_client, "chat_text", side_effect=_fake_chat_text
        ), patch.object(llm_client, "chat_json", side_effect=_fake_chat_json), patch.object(
            run_arena, "_log_progress", lambda *a, **k: None
        ):
            game = play_one(seed=5000, design="team", arm="dmn_village",
                            run_id="5000-dmn_village", requested_seed=5000,
                            max_days=1, run_dir=td, run_tag="mock")
        votes = game._vote_rows
        trust = game._trust_rows
        self.assertTrue(votes)
        self.assertTrue(all(v["arm"] == "dmn_village" for v in votes))
        self.assertTrue(all(v["design"] == "team" for v in votes))
        self.assertTrue(all("plurality_tied" in v for v in votes))
        self.assertTrue(all("voter_role" in v and "is_village" in v for v in votes))
        sources = {t["trust_source"] for t in trust}
        self.assertIn("decision", sources)
        self.assertIn("probe", sources)
        self.assertTrue(all(t["arm"] == "dmn_village" for t in trust))
        probe_rows = [t for t in trust if t["trust_source"] == "probe"]
        self.assertTrue(probe_rows)
        self.assertTrue(all(str(t["agent"]) != str(t["target"]) for t in probe_rows))
        self.assertTrue(all(t["probe"] for t in probe_rows))

    def test_focal_game_rows_backcompat(self):
        from src.eval import run_arena
        from src.eval.run_arena import play_one

        with tempfile.TemporaryDirectory() as td, patch.object(
            llm_client, "chat_text", side_effect=_fake_chat_text
        ), patch.object(llm_client, "chat_json", side_effect=_fake_chat_json), patch.object(
            run_arena, "_log_progress", lambda *a, **k: None
        ):
            game = play_one(seed=5000, focal="dmn_tpn", run_id="5000-dmn_tpn",
                            requested_seed=5000, max_days=1, run_dir=td, run_tag="mock")
        self.assertTrue(all(v["design"] == "focal" for v in game._vote_rows))
        self.assertTrue(all(t["trust_source"] == "decision" for t in game._trust_rows))
        self.assertFalse(any(t["trust_source"] == "probe" for t in game._trust_rows))


if __name__ == "__main__":
    unittest.main()
