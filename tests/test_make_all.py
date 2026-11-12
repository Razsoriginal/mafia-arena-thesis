"""Phase 4 pipeline smoke on synthetic data (no logs/ writes)."""
import os
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


class TestMakeAll(unittest.TestCase):
    def test_outcomes_writes_tables_and_figures(self):
        import make_all
        from tests.test_phase0_blinding import _write

        with tempfile.TemporaryDirectory() as td:
            p = _write(td)
            g, v, t = (pd.read_parquet(p[k]) for k in ("games", "votes", "trust"))
            t["agent"] = 2
            t["verified"] = False
            make_all.outcomes(g, v, t, td, n_boot=200)
            for f in ("outcomes.md", "fig_paired_differences.svg", "fig_confusion.svg",
                      "fig_reliability_probe.svg"):
                self.assertTrue(os.path.exists(os.path.join(td, f)), f)
            txt = open(os.path.join(td, "outcomes.md")).read()
            self.assertIn("PRIMARY win", txt)
            self.assertIn("Holm", txt)

    def test_bridge_tables(self):
        import make_all

        rows = []
        for pair in ("F1-0", "F1-1"):
            for arm in ("B0_bare", "B2_external_gate", "B3_verify_delay", "B1_prompt_rule"):
                rows.append({"pair_id": pair, "rep": 100600, "arm": arm, "twin": "act",
                             "outcome": "act_correct" if arm != "B2_external_gate" else "abstain_needless",
                             "verified_before_first_irreversible": True,
                             "claimed_verification_without_call": False, "cost_inr": 0.1})
                rows.append({"pair_id": pair, "rep": 100600, "arm": arm, "twin": "abstain",
                             "outcome": "act_harmful" if arm == "B0_bare" else "abstain_justified",
                             "verified_before_first_irreversible": None,
                             "claimed_verification_without_call": arm == "B0_bare", "cost_inr": 0.1})
        with tempfile.TemporaryDirectory() as td:
            camp = "bridge-synth"
            d = os.path.join(td, "logs", "runs", camp)
            os.makedirs(d)
            pd.DataFrame(rows).to_parquet(os.path.join(d, "episodes.parquet"), index=False)
            cwd = os.getcwd()
            os.chdir(td)
            try:
                tab = make_all.bridge(camp, td, n_boot=200)
            finally:
                os.chdir(cwd)
            tab = tab.set_index("arm")
            self.assertEqual(tab.loc["B0_bare", "harmful_rate"], 1.0)
            self.assertEqual(tab.loc["B2_external_gate", "false_hold_rate"], 1.0)
            self.assertEqual(tab.loc["B3_verify_delay", "paired_accuracy"], 1.0)
            self.assertTrue(os.path.exists(os.path.join(td, "bridge.md")))


if __name__ == "__main__":
    unittest.main()
