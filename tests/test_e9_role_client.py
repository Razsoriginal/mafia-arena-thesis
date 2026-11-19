"""E9: the client can call a second provider under a named role, with its
own key, model and expected realised model string. The primary backbone
path is unchanged. No fallback between roles."""
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from src import llm_client
from tests.test_llm_audit import _resp

ENV = {"Monitor_Base_Url": "https://monitor.example/v1", "Monitor_API_Key": "k-monitor", "Monitor_Model": "famB/mon-1"}


class TestRoleClient(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.mkdtemp(prefix="mafia-e9-")
        self._p = patch.dict(os.environ, dict(ENV, MAFIA_RAW_DIR=self._td))
        self._p.start()
        llm_client._client = None
        llm_client._role_clients.clear()

    def tearDown(self):
        self._p.stop()
        llm_client._client = None
        llm_client._role_clients.clear()

    def _rows(self):
        with open(os.path.join(self._td, "llm_raw.jsonl"), encoding="utf-8") as f:
            return [json.loads(x) for x in f]

    def test_role_call_uses_its_own_endpoint_key_and_model(self):
        made = {}

        def ctor(**kw):
            made.update(kw)
            c = MagicMock()
            c.chat.completions.create.return_value = _resp("ok", model="famB/mon-1")
            made["client"] = c
            return c
        with patch.object(llm_client, "OpenAI", side_effect=ctor):
            out = llm_client.chat_text("s", "u", temperature=0.0, role="Monitor", purpose="ops_monitor")
        self.assertEqual(out, "ok")
        self.assertEqual((made["base_url"], made["api_key"], made["max_retries"]), ("https://monitor.example/v1", "k-monitor", 0))
        self.assertEqual(made["client"].chat.completions.create.call_args.kwargs["model"], "famB/mon-1")
        r = self._rows()[-1]
        self.assertEqual((r["role"], r["requested_model"], r["base_url"]), ("Monitor", "famB/mon-1", "https://monitor.example/v1"))
        self.assertNotIn("k-monitor", json.dumps(r))

    def test_primary_rows_are_tagged_backbone_a(self):
        with patch.object(llm_client, "get_client") as gc:
            gc.return_value.chat.completions.create.return_value = _resp("ok")
            llm_client.chat_text("s", "u", temperature=0.0)
        self.assertEqual(self._rows()[-1]["role"], "BackboneA")

    def test_unconfigured_role_raises_and_never_falls_back(self):
        from src.roles import RoleNotConfigured
        with patch.object(llm_client, "get_client") as gc:
            with self.assertRaises(RoleNotConfigured):
                llm_client.chat_text("s", "u", role="BackboneB")
            gc.assert_not_called()

    def test_role_has_its_own_expected_model_guard(self):
        c = MagicMock()
        c.chat.completions.create.return_value = _resp("ok", model="famB/mon-2")
        with patch.object(llm_client, "OpenAI", return_value=c), \
                patch.dict(os.environ, {"MAFIA_EXPECT_REALISED_MODEL_MONITOR": "famB/mon-1"}):
            with self.assertRaises(llm_client.ServingDrift):
                llm_client.chat_text("s", "u", role="Monitor")

    def test_unbilled_role_call_is_estimated_high_and_flagged(self):
        resp = _resp("ok", model="famB/mon-1")
        resp.usage.cost = None
        resp.usage.prompt_tokens, resp.usage.completion_tokens = 1000, 1000
        c = MagicMock()
        c.chat.completions.create.return_value = resp
        with patch.object(llm_client, "OpenAI", return_value=c):
            llm_client.chat_text("s", "u", role="Monitor")
        r = self._rows()[-1]
        self.assertTrue(r["cost_estimated"])
        self.assertGreater(r["cost_inr"], llm_client._est_cost_inr(1000, 1000))   # never under the cheap model's rate

    def test_chat_json_passes_the_role_to_first_call_and_repair(self):
        c = MagicMock()
        c.chat.completions.create.side_effect = [_resp("not json", model="famB/mon-1"),
                                                 _resp('{"confidence": 0.7}', model="famB/mon-1")]
        with patch.object(llm_client, "OpenAI", return_value=c):
            d = llm_client.chat_json("s", "u", role="Monitor", purpose="ops_monitor")
        self.assertEqual(d, {"confidence": 0.7})
        self.assertEqual([r["role"] for r in self._rows()], ["Monitor", "Monitor"])


if __name__ == "__main__":
    unittest.main()
