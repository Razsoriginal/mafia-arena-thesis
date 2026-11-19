"""E7-C1: client hardening after the master re-evaluation (D-010).

1. The SDK must not retry silently: max_retries=0 and an explicit timeout.
2. Every attempt row records the SDK settings, a prompt hash, and reasoning
   tokens separately from visible tokens.
3. A realised model string that differs from the frozen one raises
   ServingDrift and is never retried."""
import hashlib
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from src import llm_client
from tests.test_llm_audit import _resp


class TestClientHardening(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.mkdtemp(prefix="mafia-e7-")
        self._old = {k: os.environ.get(k) for k in ("MAFIA_RAW_DIR", "MAFIA_EXPECT_REALISED_MODEL")}
        os.environ["MAFIA_RAW_DIR"] = self._td
        os.environ.pop("MAFIA_EXPECT_REALISED_MODEL", None)
        llm_client._client = None

    def tearDown(self):
        for k, v in self._old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        llm_client._client = None

    def _rows(self):
        with open(os.path.join(self._td, "llm_raw.jsonl"), encoding="utf-8") as f:
            return [json.loads(x) for x in f]

    def test_sdk_never_retries_silently(self):
        with patch.object(llm_client, "OpenAI") as ctor:
            llm_client.get_client()
        kw = ctor.call_args.kwargs
        self.assertEqual(kw.get("max_retries"), 0)
        self.assertEqual(kw.get("timeout"), llm_client.HTTP_TIMEOUT_S)
        self.assertGreater(llm_client.HTTP_TIMEOUT_S, 0)

    def test_row_has_prompt_hash_reasoning_tokens_and_sdk_settings(self):
        resp = _resp("ok")
        resp.usage.completion_tokens = 50
        resp.usage.completion_tokens_details.reasoning_tokens = 40
        with patch.object(llm_client, "get_client") as gc:
            gc.return_value.chat.completions.create.return_value = resp
            llm_client.chat_text("sys", "user", temperature=0.0)
        r = self._rows()[-1]
        self.assertEqual(r["prompt_sha256"], hashlib.sha256(b"sys\x00user").hexdigest())
        self.assertEqual(r["reasoning_tokens"], 40)
        self.assertEqual(r["visible_tokens"], 10)
        self.assertEqual(r["sdk_max_retries"], 0)
        self.assertEqual(r["http_timeout_s"], llm_client.HTTP_TIMEOUT_S)

    def test_missing_reasoning_detail_is_null_not_zero(self):
        resp = _resp("ok")
        resp.usage.completion_tokens_details = None
        with patch.object(llm_client, "get_client") as gc:
            gc.return_value.chat.completions.create.return_value = resp
            llm_client.chat_text("s", "u", temperature=0.0)
        r = self._rows()[-1]
        self.assertIsNone(r["reasoning_tokens"])
        self.assertIsNone(r["visible_tokens"])

    def test_realised_model_mismatch_raises_and_is_not_retried(self):
        os.environ["MAFIA_EXPECT_REALISED_MODEL"] = "meta/muse-spark-1.3-contributor"
        calls = []

        def create(**kw):
            calls.append(1)
            return _resp("ok", model="muse-spark-1.3-contributor")

        with patch.object(llm_client, "get_client") as gc, \
                patch.object(llm_client.time, "sleep", lambda s: None):
            gc.return_value.chat.completions.create.side_effect = create
            with self.assertRaises(llm_client.ServingDrift):
                llm_client.chat_text("s", "u", temperature=0.0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self._rows()[-1]["error_class"], "serving_drift")

    def test_matching_model_passes(self):
        os.environ["MAFIA_EXPECT_REALISED_MODEL"] = "meta/muse-spark-1.3-contributor"
        with patch.object(llm_client, "get_client") as gc:
            gc.return_value.chat.completions.create.return_value = _resp("ok")
            self.assertEqual(llm_client.chat_text("s", "u", temperature=0.0), "ok")


if __name__ == "__main__":
    unittest.main()
