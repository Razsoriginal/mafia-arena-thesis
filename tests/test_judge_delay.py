import unittest

import pandas as pd


def _votes():
    rows = []
    for arm in ("dmn_village", "cot_village"):
        rows.append({"run_tag": "t", "game_id": f"{arm}-g1", "day": 0, "voter": 0,
                     "vote": "no-lynch", "majority_vote": "3", "majority_correct": False,
                     "is_village": True, "arm": arm, "delay_cause": "low_confidence"})
        rows.append({"run_tag": "t", "game_id": f"{arm}-g1", "day": 0, "voter": 1,
                     "vote": "3", "majority_vote": "3", "majority_correct": False,
                     "is_village": True, "arm": arm, "delay_cause": None})
    return pd.DataFrame(rows)


def _histories():
    h = []
    for gid in ("dmn_village-g1", "cot_village-g1"):
        h.append({"game_id": gid, "history": [
            {"turn": 0, "speaker": "engine", "text": "Night: x", "phase": "night-0"},
            {"turn": 1, "speaker": 0, "text": "discuss", "phase": "day-0-r0"},
            {"turn": 2, "speaker": 0, "text": "votes 3", "phase": "vote-0"},
        ]})
    return h


class TestJudgeDelay(unittest.TestCase):
    def test_sample_is_blinded_and_truncated(self):
        from src.eval.judge_delay import build_sample

        sample = build_sample(_votes(), _histories(), n_delay=10, n_lynch=0, seed=20261106)
        self.assertEqual(len(sample), 2)
        for item in sample:
            self.assertNotIn("arm", item)
            self.assertNotIn("majority_correct", item)
            self.assertNotIn("winner", item)
            self.assertIn("blind_id", item)
            # vote-phase turns removed
            self.assertTrue(all("vote" not in str(t.get("phase", "")) for t in item["history"]))
            self.assertTrue(item["history"])

    def test_truncate_before_vote(self):
        from src.eval.judge_delay import truncate_before_vote

        hist = _histories()[0]["history"]
        out = truncate_before_vote(hist)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[-1]["phase"], "day-0-r0")

    def test_llm_fallback_refuses_backbone_family(self):
        from src.config import settings
        from src.eval.judge_delay import validate_judge_model

        with self.assertRaises(ValueError):
            validate_judge_model(settings.model)
        # different family passes
        validate_judge_model("openai/gpt-4o-mini")

    def test_deterministic_sampling(self):
        from src.eval.judge_delay import build_sample

        a = build_sample(_votes(), _histories(), n_delay=1, n_lynch=0, seed=42)
        b = build_sample(_votes(), _histories(), n_delay=1, n_lynch=0, seed=42)
        self.assertEqual([x["blind_id"] for x in a], [x["blind_id"] for x in b])


if __name__ == "__main__":
    unittest.main()
