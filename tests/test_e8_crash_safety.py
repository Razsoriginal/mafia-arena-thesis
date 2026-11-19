"""E8: crash safety after the 2026-11-19 machine crash left 870 null bytes
at the end of the spend ledger. Appends are flushed to disk, and a
null-filled tail is reported as such (and never repaired silently)."""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from src import llm_client
from src.eval import run_arena as ra


class TestCrashSafety(unittest.TestCase):
    def test_ledger_append_is_fsynced(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "ledger.jsonl")
            with patch.object(ra.os, "fsync") as fs:
                ra._append_ledger(p, {"run_tag": "t", "game_id": "g", "requested_seed": 1, "arm": "a",
                                      "billed_cost_inr": 1.0, "est_cost_inr": 1.0}, campaign="c")
            self.assertGreaterEqual(fs.call_count, 1)
            self.assertEqual(len(ra._ledger_entries(p)), 1)

    def test_raw_log_append_is_fsynced(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {"MAFIA_RAW_DIR": td}), patch.object(llm_client.os, "fsync") as fs:
                llm_client._log_jsonl("llm_raw.jsonl", {"a": 1})
            self.assertGreaterEqual(fs.call_count, 1)

    def test_null_tail_is_named_and_not_repaired(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "ledger.jsonl")
            good = json.dumps({"cost_inr": 2.5}) + "\n"
            with open(p, "wb") as f:
                f.write(good.encode() + b"\x00" * 64)
            before = open(p, "rb").read()
            with self.assertRaises(RuntimeError) as cm:
                ra._ledger_total(p)
            msg = str(cm.exception)
            self.assertIn("null bytes", msg)
            self.assertIn("1 valid", msg)
            self.assertEqual(open(p, "rb").read(), before)


if __name__ == "__main__":
    unittest.main()
