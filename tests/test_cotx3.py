import unittest
from unittest.mock import patch


def _fake_factory(votes):
    calls = {"n": 0, "temps": []}

    def fake(system, user, meta=None, temperature=None, **kw):
        calls["temps"].append(temperature)
        v = votes[calls["n"]]
        calls["n"] += 1
        if meta is not None:
            meta.update({"parse_fail": v is None})
        return {"vote": v, "reason": f"r{calls['n']}"} if v is not None else {}

    return fake, calls


class TestCotX3(unittest.TestCase):
    def test_majority_wins_and_records_all_samples(self):
        from src.agents.baselines import CotX3Agent

        fake, calls = _fake_factory(["3", "3", "5"])
        with patch("src.agents.baselines.llm.chat_json", side_effect=fake):
            vote, info = CotX3Agent(pid=1).vote("villager", "hist", {})
        self.assertEqual(vote, "3")
        self.assertEqual(info["samples"], ["3", "3", "5"])
        self.assertEqual(calls["n"], 3)
        self.assertEqual(calls["temps"], [0.7, 0.7, 0.7])
        self.assertEqual(info["vote_temperature"], 0.7)

    def test_all_different_falls_back_to_first(self):
        from src.agents.baselines import CotX3Agent

        fake, _ = _fake_factory(["5", "3", "no-lynch"])
        with patch("src.agents.baselines.llm.chat_json", side_effect=fake):
            vote, info = CotX3Agent(pid=1).vote("villager", "hist", {})
        self.assertEqual(vote, "5")
        self.assertTrue(info["tie_all_different"])

    def test_parse_failed_sample_recorded_not_counted(self):
        from src.agents.baselines import CotX3Agent

        fake, _ = _fake_factory([None, "4", "4"])
        with patch("src.agents.baselines.llm.chat_json", side_effect=fake):
            vote, info = CotX3Agent(pid=1).vote("villager", "hist", {})
        self.assertEqual(vote, "4")
        self.assertEqual(info["samples"], [None, "4", "4"])
        self.assertEqual(info["sample_parse_fails"], [True, False, False])

    def test_speak_is_single_call_like_cot(self):
        from src.agents.baselines import CotX3Agent

        with patch("src.agents.baselines.llm.chat_text", return_value="hello") as ct:
            out = CotX3Agent(pid=1).speak("villager", "hist")
        self.assertEqual(out, "hello")
        self.assertEqual(ct.call_count, 1)


if __name__ == "__main__":
    unittest.main()
