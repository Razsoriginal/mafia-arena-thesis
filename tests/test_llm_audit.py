import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from src import llm_client


def _resp(content, model="meta/muse-spark-1.3-contributor"):
    m = MagicMock()
    m.choices[0].message.content = content
    m.choices[0].message.reasoning_content = ""
    m.choices[0].message.reasoning = ""
    m.model = model
    m.usage.prompt_tokens = 10
    m.usage.completion_tokens = 5
    m.usage.cost = 0.1
    return m


class TestLlmAudit(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.mkdtemp(prefix="mafia-audit-")
        self._old = os.environ.get("MAFIA_RAW_DIR")
        os.environ["MAFIA_RAW_DIR"] = self._td
        llm_client._client = None

    def tearDown(self):
        if self._old is None:
            os.environ.pop("MAFIA_RAW_DIR", None)
        else:
            os.environ["MAFIA_RAW_DIR"] = self._old
        llm_client._client = None

    def _raw_rows(self):
        p = os.path.join(self._td, "llm_raw.jsonl")
        if not os.path.exists(p):
            return []
        with open(p, encoding="utf-8") as f:
            return [json.loads(x) for x in f]

    def test_raw_log_records_temperature_max_tokens_and_realised_model(self):
        with patch.object(llm_client, "get_client") as gc:
            gc.return_value.chat.completions.create.return_value = _resp('{"vote":"1"}')
            out = llm_client.chat_text("s", "u", temperature=0.7)
        self.assertEqual(out, '{"vote":"1"}')
        rows = [r for r in self._raw_rows() if r.get("fn") == "chat_text"]
        self.assertTrue(rows)
        r = rows[-1]
        self.assertEqual(r["temperature"], 0.7)
        self.assertEqual(r["max_tokens"], 2500)
        self.assertEqual(r["attempt"], 0)
        self.assertEqual(r["realised_model"], "meta/muse-spark-1.3-contributor")
        self.assertEqual(r["resp_model"], r["realised_model"])
        self.assertEqual(r["requested_model"], r["model"])

    def test_empty_content_escalation_is_logged(self):
        calls = []

        def fake_create(**kw):
            calls.append(kw["max_tokens"])
            return _resp("") if len(calls) == 1 else _resp("hello")

        with patch.object(llm_client, "get_client") as gc, patch.object(
            llm_client.time, "sleep", lambda s: None
        ):
            gc.return_value.chat.completions.create.side_effect = fake_create
            out = llm_client.chat_text("s", "u", temperature=0.7)
        self.assertEqual(out, "hello")
        self.assertEqual(calls, [2500, 3500])
        rows = [r for r in self._raw_rows() if r.get("fn") == "chat_text"]
        self.assertTrue(rows[-1]["escalated"])
        self.assertEqual(rows[-1]["max_tokens"], 3500)

    def test_repair_pass_is_flagged_at_zero(self):
        temps = []

        def fake_create(**kw):
            temps.append(kw["temperature"])
            return _resp("not json") if len(temps) == 1 else _resp('{"vote":"2"}')

        with patch.object(llm_client, "get_client") as gc, patch.object(
            llm_client.time, "sleep", lambda s: None
        ):
            gc.return_value.chat.completions.create.side_effect = fake_create
            out = llm_client.chat_json("sys", "user", temperature=0.7)
        self.assertEqual(out, {"vote": "2"})
        self.assertEqual(temps, [0.7, 0.0])
        rows = [r for r in self._raw_rows() if r.get("repair")]
        self.assertTrue(rows)
        self.assertTrue(rows[-1]["repair"])
        self.assertEqual(rows[-1]["temperature"], 0.0)
        self.assertEqual(rows[-1]["purpose"], "repair")
        self.assertIsNotNone(rows[-1]["realised_model"])


class TestChatJsonEndToEnd(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.mkdtemp(prefix="mafia-audit-e2e-")
        self._old = os.environ.get("MAFIA_RAW_DIR")
        os.environ["MAFIA_RAW_DIR"] = self._td
        llm_client._client = None

    def tearDown(self):
        if self._old is None:
            os.environ.pop("MAFIA_RAW_DIR", None)
        else:
            os.environ["MAFIA_RAW_DIR"] = self._old
        llm_client._client = None

    def _rows(self):
        p = os.path.join(self._td, "llm_raw.jsonl")
        if not os.path.exists(p):
            return []
        with open(p, encoding="utf-8") as f:
            return [json.loads(x) for x in f]

    def test_escalation_and_repair_through_chat_json(self):
        # empty (escalate 2500->3500) -> non-JSON -> repair JSON
        contents = ["", "not json", '{"vote":"2"}']
        state = {"n": 0, "max_tokens": [], "temps": []}

        def fake_create(**kw):
            state["max_tokens"].append(kw["max_tokens"])
            state["temps"].append(kw["temperature"])
            c = contents[state["n"]]
            state["n"] += 1
            return _resp(c)

        with patch.object(llm_client, "get_client") as gc, patch.object(
            llm_client.time, "sleep", lambda s: None
        ):
            gc.return_value.chat.completions.create.side_effect = fake_create
            out = llm_client.chat_json("sys", "user", temperature=0.7, purpose="vote")
        self.assertEqual(out, {"vote": "2"})
        rows = self._rows()
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r["realised_model"] for r in rows))
        self.assertEqual([r["max_tokens"] for r in rows], [2500, 3500, 2500])
        self.assertEqual(rows[0]["temperature"], 0.7)
        self.assertFalse(rows[0]["escalated"])
        self.assertTrue(rows[1]["escalated"])
        self.assertEqual(rows[2]["purpose"], "repair")
        self.assertTrue(rows[2]["repair"])
        self.assertTrue(all(r["purpose"] in llm_client.PURPOSES for r in rows))
        self.assertTrue(all("prompt_tokens" in r and "cost_inr" in r for r in rows))

    def test_cost_fallback_is_estimated_and_flagged(self):
        def fake_create(**kw):
            r = _resp('{"vote":"1"}')
            r.usage.cost = None
            return r

        with patch.object(llm_client, "get_client") as gc:
            gc.return_value.chat.completions.create.side_effect = fake_create
            llm_client.chat_json("sys", "user", temperature=0.7, purpose="vote")
        rows = self._rows()
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["cost_estimated"])
        self.assertGreater(rows[0]["cost_inr"], 0)


if __name__ == "__main__":
    unittest.main()
