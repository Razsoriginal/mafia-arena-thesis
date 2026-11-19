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


def _freeze_text(run_arena, prompts=None, runpath=None, tag="HEAD"):
    """A real freeze block built from the live tree (V3)."""
    return ("<!-- freeze\n"
            f"prompts_sha256: {prompts or run_arena._prompt_hash()}\n"
            f"runpath_sha256: {runpath or run_arena._runpath_sha256()}\n"
            f"freeze_git_sha: {run_arena._git_sha()}\n"
            f"freeze_tag: {tag}\n-->\n")


def _frozen(run_arena, prompts=None, runpath=None, tag="HEAD", dirty=None):
    """Patch only the document location and git-status read.

    The compared hashes and the tag-ancestor check are the real ones, so a
    tampered field or a non-ancestor tag must still refuse.
    """
    text = _freeze_text(run_arena, prompts=prompts, runpath=runpath, tag=tag)
    return patch.multiple(
        run_arena,
        _prereg_expected=lambda: {
            "freeze": run_arena._parse_freeze_block(text),
            "has_pending": False,
        },
        _dirty_runpath_files=lambda: list(dirty or []),
    )


class TestConfirmatoryAssertions(unittest.TestCase):
    def test_valid_confirmatory_passes(self):
        from src.eval import run_arena

        with _frozen(run_arena):
            run_arena._assert_confirmatory(_args())  # no raise

    def test_pending_freeze_refuses(self):
        from src.eval import run_arena

        with _frozen(run_arena, tag="PENDING"):
            with self.assertRaises(SystemExit):
                run_arena._assert_confirmatory(_args())

    def test_dirty_runpath_refuses_but_logs_artifact_does_not(self):
        from src.eval import run_arena

        with _frozen(run_arena):
            run_arena._assert_confirmatory(_args())  # clean run path
        with _frozen(run_arena, dirty=["src/eval/run_arena.py"]):
            with self.assertRaises(SystemExit):
                run_arena._assert_confirmatory(_args())

    def test_prompt_hash_mismatch_refuses(self):
        from src.eval import run_arena

        with _frozen(run_arena, prompts="a" * 64):
            with self.assertRaises(SystemExit):
                run_arena._assert_confirmatory(_args())

    def test_runpath_hash_mismatch_refuses(self):
        from src.eval import run_arena

        with _frozen(run_arena, runpath="b" * 64):
            with self.assertRaises(SystemExit):
                run_arena._assert_confirmatory(_args())

    def test_freeze_tag_must_be_ancestor(self):
        from src.eval import run_arena

        with _frozen(run_arena, tag="no-such-tag-for-g6"):
            self.assertFalse(run_arena._freeze_tag_ancestor("no-such-tag-for-g6"))
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
                         dict(budget_cap=5000.01), dict(planned_trios=5),
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
        self.assertEqual(m["effective_tau"], 0.35)
        self.assertEqual(m["planned_trio_cost_inr"], 8.13)
        self.assertIn("git_status_summary", m)


if __name__ == "__main__":
    unittest.main()
