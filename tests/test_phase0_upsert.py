"""P0-U1: _upsert must never drop existing rows. An unreadable table or a
failed concat raises and leaves the file untouched (logs/ is append-only)."""
import os
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from src.eval import run_arena


class TestUpsertNeverDrops(unittest.TestCase):
    def test_unreadable_table_raises_and_is_untouched(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "games.parquet")
            with open(p, "wb") as f:
                f.write(b"not a parquet file")
            before = open(p, "rb").read()
            with self.assertRaises(RuntimeError):
                run_arena._upsert(p, pd.DataFrame([{"a": 1}]), ["a"])
            self.assertEqual(open(p, "rb").read(), before)

    def test_concat_failure_raises_and_keeps_old_rows(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "games.parquet")
            pd.DataFrame([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]).to_parquet(p, index=False)
            with patch.object(run_arena.pd, "concat", side_effect=ValueError("schema")):
                with self.assertRaises(RuntimeError):
                    run_arena._upsert(p, pd.DataFrame([{"a": 3, "b": "z"}]), ["a"])
            self.assertEqual(len(pd.read_parquet(p)), 2)

    def test_normal_upsert_replaces_on_keys(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "g.parquet")
            run_arena._upsert(p, pd.DataFrame([{"k": 1, "v": "a"}, {"k": 2, "v": "b"}]), ["k"])
            run_arena._upsert(p, pd.DataFrame([{"k": 2, "v": "c"}]), ["k"])
            df = pd.read_parquet(p).sort_values("k")
            self.assertEqual(df["v"].tolist(), ["a", "c"])


if __name__ == "__main__":
    unittest.main()
