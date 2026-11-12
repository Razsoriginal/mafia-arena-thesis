"""Phase 0 retry/timing (P0-R1): the smoke 'HTTP 500s' are a ~90 s
provider gateway timeout on slow generations (every 500 attempt lasted
>= 91.7 s), and 2-16 s backoff over 5 attempts re-hit the same slow
window. Per-attempt rows now carry latency, backoff and error class;
transient errors get up to 8 attempts with 10 s base exponential backoff
(cap 120 s, jittered). 402 is still never retried."""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from src import llm_client
from tests.test_llm_audit import _resp


class _Err(Exception):
    pass


class TestRetryTiming(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.mkdtemp(prefix="mafia-retry-")
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
        with open(p, encoding="utf-8") as f:
            return [json.loads(x) for x in f]

    def test_500_retries_with_long_backoff_then_succeeds(self):
        n = {"k": 0}
        sleeps = []

        def create(**kw):
            n["k"] += 1
            if n["k"] <= 5:
                raise _Err("Error code: 500")
            return _resp("ok")

        with patch.object(llm_client, "get_client") as gc, \
                patch.object(llm_client.time, "sleep", lambda s: sleeps.append(s)):
            gc.return_value.chat.completions.create.side_effect = create
            out = llm_client.chat_text("s", "u", temperature=0.0)
        self.assertEqual(out, "ok")  # 6th attempt; old policy gave up at 5
        self.assertEqual(len(sleeps), 5)
        self.assertGreaterEqual(min(sleeps), 5.0)  # jittered 10 s base
        self.assertLessEqual(max(sleeps), 120.0)
        rows = self._rows()
        self.assertEqual([r["error_class"] for r in rows[:5]], ["http_500"] * 5)
        self.assertIsNone(rows[-1]["error_class"])
        for r in rows:
            self.assertIn("latency_s", r)
            self.assertIn("backoff_s", r)
        self.assertGreater(rows[1]["backoff_s"], 0)

    def test_persistent_500_gives_up_after_8_attempts(self):
        calls = []

        def create(**kw):
            calls.append(1)
            raise _Err("Error code: 500")

        with patch.object(llm_client, "get_client") as gc, \
                patch.object(llm_client.time, "sleep", lambda s: None):
            gc.return_value.chat.completions.create.side_effect = create
            out = llm_client.chat_text("s", "u", temperature=0.0)
        self.assertEqual(out, "")
        self.assertEqual(len(calls), 8)

    def test_402_is_never_retried(self):
        calls = []

        def create(**kw):
            calls.append(1)
            raise _Err("Error code: 402 insufficient balance")

        with patch.object(llm_client, "get_client") as gc, \
                patch.object(llm_client.time, "sleep", lambda s: None):
            gc.return_value.chat.completions.create.side_effect = create
            with self.assertRaises(llm_client.BillingExhausted):
                llm_client.chat_text("s", "u")
        self.assertEqual(len(calls), 1)

    def test_error_classes(self):
        c = llm_client._error_class
        self.assertEqual(c("Error code: 500"), "http_500")
        self.assertEqual(c("Error code: 502 bad gateway"), "http_5xx")
        self.assertEqual(c("Error code: 429 rate limit"), "http_429")
        self.assertEqual(c("Connection error."), "connection")
        self.assertEqual(c("empty content (max_tokens=2500)"), "empty_content")


if __name__ == "__main__":
    unittest.main()
