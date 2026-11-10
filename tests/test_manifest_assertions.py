import unittest
from unittest.mock import patch


def _args(**over):
    base = dict(design="team", arms="dmn_village,cot_village,cotx3_village",
                gate="llm", night="llm", max_days=5, ablate="", tau=0.35,
                confirmatory=True, budget_cap=1600.0, games=184, seed=5000,
                campaign="mvp-team-01", planned_trios=184, start_trio=0,
                trios=None, calibration=False, resume=False,
                spend_ledger=None, pending_file=None, calibration_go=None,
                calibration_trios=20)
    base.update(over)
    return type("A", (), base)()


def _frozen(run_arena):
    """Simulate the frozen state: matching hashes, clean tree, no PENDING."""
    return patch.multiple(
        run_arena,
        _prereg_expected=lambda: {
            "prompt_hash": run_arena._prompt_hash(),
            "runpath_sha256": run_arena._runpath_sha256(),
            "git_sha": run_arena._git_sha(),
            "has_pending": False,
        },
        _is_dirty=lambda: False,
    )


class TestConfirmatoryAssertions(unittest.TestCase):
    def test_valid_confirmatory_passes(self):
        from src.eval import run_arena

        with _frozen(run_arena):
            run_arena._assert_confirmatory(_args())  # no raise

    def test_pending_freeze_refuses(self):
        from src.eval import run_arena

        with patch.object(run_arena, "_is_dirty", lambda: False), patch.object(
            run_arena, "_prereg_expected",
            lambda: {"prompt_hash": run_arena._prompt_hash(), "has_pending": True},
        ):
            with self.assertRaises(SystemExit):
                run_arena._assert_confirmatory(_args())

    def test_dirty_tree_refuses(self):
        from src.eval import run_arena

        with patch.object(run_arena, "_is_dirty", lambda: True), patch.object(
            run_arena, "_prereg_expected",
            lambda: {"prompt_hash": run_arena._prompt_hash(), "has_pending": False},
        ):
            with self.assertRaises(SystemExit):
                run_arena._assert_confirmatory(_args())

    def test_tau_must_be_explicit_035(self):
        from src.eval import run_arena

        with _frozen(run_arena):
            with self.assertRaises(SystemExit):
                run_arena._assert_confirmatory(_args(tau=None))
            with self.assertRaises(SystemExit):
                run_arena._assert_confirmatory(_args(tau=0.45))

    def test_gate_and_ablate_and_design(self):
        from src.eval import run_arena

        with _frozen(run_arena):
            with self.assertRaises(SystemExit):
                run_arena._assert_confirmatory(_args(gate="jev"))
            with self.assertRaises(SystemExit):
                run_arena._assert_confirmatory(_args(ablate="evt"))
            with self.assertRaises(SystemExit):
                run_arena._assert_confirmatory(_args(design="focal"))

    def test_night_maxdays_arms_seed_cap_all_checked(self):
        from src.eval import run_arena

        with _frozen(run_arena):
            for over in (dict(night="scripted"), dict(max_days=3),
                         dict(arms="dmn_village"), dict(seed=0),
                         dict(budget_cap=5000.0), dict(planned_trios=5),
                         dict(campaign=None)):
                with self.assertRaises(SystemExit, msg=str(over)):
                    run_arena._assert_confirmatory(_args(**over))

    def test_provider_base_url_evt_checked(self):
        from src.config import settings
        from src.eval import run_arena

        old = (settings.provider, settings.base_url, settings.evt_threshold)
        try:
            with _frozen(run_arena):
                settings.base_url = "https://example.com/v1"
                with self.assertRaises(SystemExit):
                    run_arena._assert_confirmatory(_args())
                settings.base_url = old[1]
                settings.provider = "openai"
                with self.assertRaises(SystemExit):
                    run_arena._assert_confirmatory(_args())
                settings.provider = old[0]
                settings.evt_threshold = 0.9
                with self.assertRaises(SystemExit):
                    run_arena._assert_confirmatory(_args())
        finally:
            settings.provider, settings.base_url, settings.evt_threshold = old

    def test_non_confirmatory_skips(self):
        from src.eval.run_arena import _assert_confirmatory

        _assert_confirmatory(_args(confirmatory=False, tau=None, gate="jev"))

    def test_prompt_hash_matches_preregistration(self):
        from src.eval.run_arena import _prereg_expected, _prompt_hash

        expected = _prereg_expected()
        self.assertIn("prompt_hash", expected)
        self.assertEqual(_prompt_hash(), expected["prompt_hash"])

    def test_manifest_contains_prereg_fields(self):
        import json
        import tempfile
        import os

        from src.eval.run_arena import _write_manifest

        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "manifest.json")
            _write_manifest(path, _args(), "test-tag", "abc123")
            with open(path, encoding="utf-8") as f:
                m = json.load(f)
        self.assertIn("prompt_hash", m)
        self.assertIn("runpath_sha256", m)
        self.assertIn("campaign", m)
        self.assertIn("planned_trios", m)
        self.assertIn("design", m)
        self.assertIn("arm_map", m)
        self.assertEqual(m["llm"]["vote_temperature"], 0.7)
        self.assertTrue(m["probe_enabled"])
        self.assertIn("budget_cap_inr", m)


if __name__ == "__main__":
    unittest.main()
