"""E4-U2: _upsert must not collapse rows whose key columns are missing.

Legacy focal-pilot rows have no campaign/requested_seed/arm. When team rows
were upserted on those keys, every legacy row compared equal (NaN keys) and
drop_duplicates kept only the last one per write, so the canonical games
table lost 9 of the 14 pilot rows. A row with a missing key value has no
identity under that key and must never be deduplicated."""
import os
import tempfile
import unittest

import pandas as pd

from src.eval import run_arena


class TestUpsertNullKeys(unittest.TestCase):
    def test_legacy_rows_without_keys_survive_a_team_upsert(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "games.parquet")
            legacy = pd.DataFrame([{"run_tag": "pilot", "game_id": f"g{i}", "winner": "mafia"}
                                   for i in range(4)])
            legacy.to_parquet(p, index=False)
            keys = ["campaign", "requested_seed", "arm"]
            for seed in (5000, 5100):
                run_arena._upsert(p, pd.DataFrame([{
                    "run_tag": "cal", "game_id": f"c-{seed}", "winner": "village",
                    "campaign": "c", "requested_seed": seed, "arm": "cot_village"}]), keys)
            df = pd.read_parquet(p)
            self.assertEqual(int(df["campaign"].isna().sum()), 4)
            self.assertEqual(len(df), 6)

    def test_keyed_rows_still_replace(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "games.parquet")
            pd.DataFrame([{"run_tag": "pilot", "game_id": "g0", "winner": "mafia"}]).to_parquet(p, index=False)
            keys = ["campaign", "requested_seed", "arm"]
            for w in ("mafia", "village"):
                run_arena._upsert(p, pd.DataFrame([{
                    "run_tag": "cal", "game_id": "c-1", "winner": w,
                    "campaign": "c", "requested_seed": 5000, "arm": "cot_village"}]), keys)
            df = pd.read_parquet(p)
            self.assertEqual(len(df), 2)
            self.assertEqual(df[df["campaign"] == "c"]["winner"].tolist(), ["village"])


if __name__ == "__main__":
    unittest.main()
