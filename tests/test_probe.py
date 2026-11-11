import unittest
from unittest.mock import patch


class TestProbe(unittest.TestCase):
    def test_probe_prompt_has_no_commitment(self):
        from src.mafia import prompts as P

        self.assertTrue(hasattr(P, "TRUST_PROBE_SYSTEM"))
        self.assertTrue(hasattr(P, "trust_probe_user"))
        text = P.trust_probe_user(1, "hist", [0, 1, 2])
        self.assertNotIn("commitment", text.lower())
        self.assertIn('"trust"', text)

    def test_probe_method_calls_at_zero_and_drops_self(self):
        from src.agents.baselines import CotAgent

        seen = {}

        def fake(system, user, meta=None, temperature=None, **kw):
            seen["temperature"] = temperature
            seen["system"] = system
            if meta is not None:
                meta.update({"parse_fail": False})
            return {"trust": {"0": 0.2, "1": 0.9, "2": 0.4}}

        with patch("src.agents.base.llm.chat_json", side_effect=fake):
            trust, info = CotAgent(pid=1).elicit_trust_probe("villager", "public hist", [0, 1, 2])
        self.assertEqual(seen["temperature"], 0.0)
        self.assertNotIn("1", trust)
        self.assertEqual(trust, {"0": 0.2, "2": 0.4})
        self.assertTrue(info["probe"])
        self.assertFalse(info["parse_fail"])

    def test_probe_on_dmn_agent_same_method(self):
        from src.agents.dmn_tpn_agent import DmnTpnAgent

        def fake(system, user, meta=None, temperature=None, **kw):
            self.assertEqual(temperature, 0.0)
            if meta is not None:
                meta.update({"parse_fail": False})
            return {"trust": {"0": 0.5, "2": 0.7}}

        with patch("src.agents.base.llm.chat_json", side_effect=fake):
            trust, info = DmnTpnAgent(pid=0).elicit_trust_probe("villager", "h", [0, 2])
        self.assertEqual(trust, {"2": 0.7})
        self.assertTrue(info["probe"])

    def test_probe_parse_fail_returns_empty(self):
        from src.agents.baselines import CotAgent

        def fake(system, user, meta=None, temperature=None, **kw):
            if meta is not None:
                meta.update({"parse_fail": True})
            return {}

        with patch("src.agents.base.llm.chat_json", side_effect=fake):
            trust, info = CotAgent(pid=1).elicit_trust_probe("villager", "h", [0, 1])
        self.assertEqual(trust, {})
        self.assertTrue(info["parse_fail"])


if __name__ == "__main__":
    unittest.main()
