import os
import unittest

import pandas as pd

from src.eval import run_arena

from tests.round2_support import _RunEnv, _team_row, _with_rows


class TestCampaignRowsG8V1V2(_RunEnv):
    def test_two_campaigns_same_seed_arm_keep_distinct_rows(self):
        for camp in ("camp-a", "camp-b"):
            self._run(self._base(camp, camp, trios=1) + ["--no-canonical"],
                      runner=_with_rows)
        # --no-canonical keeps only per-run bundles; write canonical instead.
        self._run(self._base("camp-a", "camp-a-2", trios=1), runner=_with_rows)
        self._run(self._base("camp-b", "camp-b-2", trios=1), runner=_with_rows)
        games = pd.read_parquet(self.out)
        self.assertEqual(len(games), 6)
        self.assertEqual(set(games["campaign"]), {"camp-a", "camp-b"})
        votes = pd.read_parquet(os.path.join(self._td, "votes.parquet"))
        trust = pd.read_parquet(os.path.join(self._td, "trust.parquet"))
        self.assertEqual(len(votes), 6)
        self.assertEqual(len(trust), 6)
        self.assertEqual(votes.groupby("campaign").size().to_dict(),
                         {"camp-a": 3, "camp-b": 3})
        self.assertEqual(trust.groupby("campaign").size().to_dict(),
                         {"camp-a": 3, "camp-b": 3})
        self.assertEqual(votes.duplicated(
            subset=["campaign", "game_id", "day", "voter"]).sum(), 0)
        self.assertEqual(trust.duplicated(
            subset=["campaign", "game_id", "day", "agent", "target",
                    "trust_source"]).sum(), 0)

    def test_canonical_team_key_is_campaign_seed_arm(self):
        args = type("A", (), {"out": self.out, "no_canonical": False})()
        run_dir = os.path.join(self._td, "runs", "v1")
        os.makedirs(run_dir, exist_ok=True)
        row_a = _team_row({"run_tag": "a", "campaign": "c",
                           "arm": "dmn_village",
                           "run_id": "c-9000-dmn_village",
                           "requested_seed": 9000})
        row_b = dict(row_a, run_tag="b", game_id="c-9000-dmn_village-again")
        rows = []
        run_arena._record_result({"row": row_a, "votes": [], "trust": []},
                                 args, run_dir, rows, canonical=True)
        run_arena._record_result({"row": row_b, "votes": [], "trust": []},
                                 args, run_dir, rows, canonical=True)
        df = pd.read_parquet(self.out)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["run_tag"], "b")
        # A different campaign is a distinct key.
        row_c = dict(row_b, campaign="c2")
        run_arena._record_result({"row": row_c, "votes": [], "trust": []},
                                 args, run_dir, rows, canonical=True)
        self.assertEqual(len(pd.read_parquet(self.out)), 2)

    def test_completed_keys_and_resume(self):
        args = self._base("dup", "dup", trios=1)
        self._run(args)
        self.assertEqual(len(self.calls), 3)
        keys = run_arena._completed_keys(self.out, "dup")
        self.assertEqual(keys, {("dup", 9000, a) for a in
                                ("dmn_village", "cot_village",
                                 "cotx3_village")})
        # duplicate-run refusal without --resume
        with self.assertRaises(SystemExit):
            self._run(args)
        self.assertEqual(len(self.calls), 3)
        # resume with nothing missing runs zero new games
        self._run(args + ["--resume"])
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(len(pd.read_parquet(self.out)), 3)
        # resume starting at a completed seed still filters it out
        self._run(self._base("dup", "dup2", trios=1, start_trio=1)
                  + ["--resume"])
        self.assertEqual(len(self.calls), 6)
        self.assertEqual(set(pd.read_parquet(self.out)["requested_seed"]),
                         {9000, 9100})


if __name__ == "__main__":
    unittest.main()
