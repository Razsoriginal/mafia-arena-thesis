import os
import tempfile
import unittest
from unittest.mock import patch

os.environ["MAFIA_RAW_DIR"] = tempfile.mkdtemp(prefix="mafia-test-raw-")

from src import llm_client
from src.config import settings


class TestTemperaturePlumbing(unittest.TestCase):
    def test_vote_temperature_setting_default(self):
        self.assertEqual(settings.vote_temperature, 0.7)

    def test_chat_json_forwards_explicit_temperature(self):
        seen = {}

        def fake_chat_text(system, user, temperature=None, log=True, response_format=None):
            seen["temperature"] = temperature
            return '{"vote": "1"}'

        with patch.object(llm_client, "chat_text", side_effect=fake_chat_text):
            out = llm_client.chat_json("sys", "user", temperature=0.7)
        self.assertEqual(out, {"vote": "1"})
        self.assertEqual(seen["temperature"], 0.7)

    def test_chat_json_default_is_json_temperature(self):
        seen = {}

        def fake_chat_text(system, user, temperature=None, log=True, response_format=None):
            seen["temperature"] = temperature
            return '{"vote": "1"}'

        with patch.object(llm_client, "chat_text", side_effect=fake_chat_text):
            llm_client.chat_json("sys", "user")
        self.assertEqual(seen["temperature"], settings.temp_json)
        self.assertEqual(seen["temperature"], 0.0)

    def test_cot_vote_uses_vote_temperature(self):
        from src.agents.baselines import CotAgent

        seen = {}

        def fake_chat_json(system, user, meta=None, temperature=None):
            seen["temperature"] = temperature
            if meta is not None:
                meta.update({"parse_fail": False})
            return {"vote": "2", "reason": "x"}

        with patch("src.agents.baselines.llm.chat_json", side_effect=fake_chat_json):
            vote, _info = CotAgent(pid=1).vote("villager", "hist", {})
        self.assertEqual(vote, "2")
        self.assertEqual(seen["temperature"], 0.7)

    def test_dmn_cited_vote_uses_vote_temperature(self):
        from src.agents.dmn_tpn_agent import DmnTpnAgent

        seen = {}

        def fake_chat_json(system, user, meta=None, temperature=None):
            seen["temperature"] = temperature
            if meta is not None:
                meta.update({"parse_fail": False})
            return {"vote": "3", "reason": "t1 shows x"}

        agent = DmnTpnAgent(pid=1)
        with patch("src.agents.dmn_tpn_agent.llm.chat_json", side_effect=fake_chat_json):
            vote, _info = agent.vote("villager", "hist", {}, trace={"delay": False})
        self.assertEqual(vote, "3")
        self.assertEqual(seen["temperature"], 0.7)


if __name__ == "__main__":
    unittest.main()
