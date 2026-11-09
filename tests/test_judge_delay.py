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


def _histories_two_day():
    return [{"game_id": "g-two", "history": [
        {"turn": 0, "speaker": "engine", "text": "Night: x", "phase": "night-0"},
        {"turn": 1, "speaker": 0, "text": "d0 talk", "phase": "day-0-r0"},
        {"turn": 2, "speaker": 0, "text": "votes 3", "phase": "vote-0"},
        {"turn": 3, "speaker": "engine", "text": "Day 0 result", "phase": "result-0"},
        {"turn": 4, "speaker": "engine", "text": "Night: y", "phase": "night-1"},
        {"turn": 5, "speaker": 1, "text": "d1 talk", "phase": "day-1-r0"},
        {"turn": 6, "speaker": 1, "text": "votes 4", "phase": "vote-1"},
        {"turn": 7, "speaker": "engine", "text": "Day 1 result", "phase": "result-1"},
    ]}]


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

    def test_truncate_before_sampled_days_vote(self):
        from src.eval.judge_delay import truncate_before_vote

        hist = _histories_two_day()[0]["history"]
        out = truncate_before_vote(hist, day=1)
        # day-0 vote/result stay visible; day-1 discussion kept; vote-1 cut
        self.assertEqual([t["turn"] for t in out], [0, 1, 2, 3, 4, 5])
        out0 = truncate_before_vote(hist, day=0)
        self.assertEqual([t["turn"] for t in out0], [0, 1])

    def test_lynch_stratum_requires_actual_lynch(self):
        from src.eval.judge_delay import build_sample

        # 7 voters, plurality 3 with only 3 votes (3 vs 2/2): NOT lynched
        rows = []
        for voter, vote in enumerate(["3", "3", "3", "4", "4", "5", "5"]):
            rows.append({"run_tag": "t", "game_id": "g-two", "day": 0, "voter": voter,
                         "vote": vote, "majority_vote": "3", "majority_correct": False,
                         "is_village": True, "arm": "cot_village", "delay_cause": None})
        sample = build_sample(pd.DataFrame(rows), _histories_two_day(),
                              n_delay=0, n_lynch=10, seed=1)
        self.assertEqual(len(sample), 0)
        # 4 votes for the plurality target IS a strict-majority lynch
        rows2 = []
        for voter, vote in enumerate(["3", "3", "3", "3", "4", "4", "5"]):
            rows2.append({"run_tag": "t", "game_id": "g-two", "day": 0, "voter": voter,
                          "vote": vote, "majority_vote": "3", "majority_correct": False,
                          "is_village": True, "arm": "cot_village", "delay_cause": None})
        sample2 = build_sample(pd.DataFrame(rows2), _histories_two_day(),
                               n_delay=0, n_lynch=10, seed=1)
        self.assertEqual(len(sample2), 1)

    def test_deterministic_sampling(self):
        from src.eval.judge_delay import build_sample

        a = build_sample(_votes(), _histories(), n_delay=1, n_lynch=0, seed=42)
        b = build_sample(_votes(), _histories(), n_delay=1, n_lynch=0, seed=42)
        self.assertEqual([x["blind_id"] for x in a], [x["blind_id"] for x in b])


if __name__ == "__main__":
    unittest.main()
