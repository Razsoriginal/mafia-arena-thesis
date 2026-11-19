"""E7-K3: --unblind without --campaign would pool every team campaign in
the table, and so pool epochs. It must be refused."""
import os
import tempfile
import unittest

from tests.test_phase0_blinding import _run, _write


class TestUnblindNeedsCampaign(unittest.TestCase):
    def test_unblind_without_campaign_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            p = _write(td)
            with self.assertRaises(SystemExit) as cm:
                _run(["--input", p["games"], "--votes", p["votes"], "--trust", p["trust"],
                      "--unblind", "--pending-file", os.path.join(td, "none.json"), "--n-boot", "100"])
            self.assertIn("campaign", str(cm.exception).lower())

    def test_unblind_with_campaign_still_works(self):
        with tempfile.TemporaryDirectory() as td:
            p = _write(td)
            out = _run(["--input", p["games"], "--votes", p["votes"], "--trust", p["trust"], "--campaign", "c",
                        "--unblind", "--pending-file", os.path.join(td, "none.json"), "--n-boot", "100"])
            self.assertIn("PRIMARY", out)


if __name__ == "__main__":
    unittest.main()
