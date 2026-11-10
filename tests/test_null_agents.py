import unittest
from unittest.mock import patch


class TestNullAgents(unittest.TestCase):
    def test_random_deterministic_same_context(self):
        from src.agents.null_agents import RandomVoterAgent

        ag = RandomVoterAgent(pid=2)
        v1, _ = ag.vote("villager", "hist", {}, prev_majority=None, seed=5000, day=1, alive=[0, 1, 2, 3])
        v2, _ = RandomVoterAgent(pid=2).vote("villager", "hist", {}, prev_majority=None, seed=5000, day=1, alive=[0, 1, 2, 3])
        self.assertEqual(v1, v2)
        self.assertIn(v1, ["0", "1", "3", "no-lynch"])

    def test_random_never_votes_self(self):
        from src.agents.null_agents import RandomVoterAgent

        for day in range(8):
            v, _ = RandomVoterAgent(pid=2).vote("villager", "h", {}, seed=100 + day, day=day, alive=[0, 2, 4])
            self.assertNotEqual(v, "2")

    def test_majority_day0_is_no_lynch(self):
        from src.agents.null_agents import MajorityFollowerAgent

        v, _ = MajorityFollowerAgent(pid=1).vote("villager", "h", {}, prev_majority=None, seed=1, day=0, alive=[0, 1, 2])
        self.assertEqual(v, "no-lynch")

    def test_majority_copies_previous_plurality(self):
        from src.agents.null_agents import MajorityFollowerAgent

        v, _ = MajorityFollowerAgent(pid=1).vote("villager", "h", {}, prev_majority="4", seed=1, day=2, alive=[0, 1, 4])
        self.assertEqual(v, "4")

    def test_majority_dead_or_self_target_is_no_lynch(self):
        from src.agents.null_agents import MajorityFollowerAgent

        v, _ = MajorityFollowerAgent(pid=4).vote("villager", "h", {}, prev_majority="4", seed=1, day=2, alive=[0, 4])
        self.assertEqual(v, "no-lynch")
        v2, _ = MajorityFollowerAgent(pid=1).vote("villager", "h", {}, prev_majority="6", seed=1, day=2, alive=[0, 1])
        self.assertEqual(v2, "no-lynch")

    def test_no_llm_calls(self):
        # Patch the client module itself (every import path), and include
        # the probe: a direct llm_client import in a null agent must fail
        # this test (F44).
        from src.agents.null_agents import MajorityFollowerAgent, RandomVoterAgent

        with patch("src.llm_client.chat_json", side_effect=AssertionError("llm called")) as cj, patch(
            "src.llm_client.chat_text", side_effect=AssertionError("llm called")
        ) as ct, patch(
            "src.agents.base.llm.chat_json", side_effect=AssertionError("llm called")
        ), patch(
            "src.agents.base.llm.chat_text", side_effect=AssertionError("llm called")
        ):
            for ag in (RandomVoterAgent(pid=0), MajorityFollowerAgent(pid=0)):
                self.assertEqual(ag.speak("villager", "h"), "I am watching and waiting for evidence.")
                ag.vote("doctor", "h", {}, prev_majority="1", seed=3, day=1, alive=[0, 1, 2])
                self.assertEqual(ag.night_action("doctor", "h", [0, 1], [0, 1], "save"), "0")
                self.assertEqual(ag.night_action("detective", "h", [0, 1, 2], [1, 2], "check"), "1")
                trust, info = ag.elicit_trust_probe("villager", "h", [0, 1, 2])
                self.assertEqual(trust, {})
                self.assertFalse(info["probe"])
        self.assertEqual(cj.call_count, 0)
        self.assertEqual(ct.call_count, 0)

    def test_doctor_saves_self_detective_checks_min(self):
        from src.agents.null_agents import RandomVoterAgent

        ag = RandomVoterAgent(pid=3)
        self.assertEqual(ag.night_action("doctor", "h", [1, 3], [1, 3], "save"), "3")
        self.assertEqual(ag.night_action("detective", "h", [1, 3, 5], [1, 5], "check"), "1")


if __name__ == "__main__":
    unittest.main()
