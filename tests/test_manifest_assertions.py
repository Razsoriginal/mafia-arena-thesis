import unittest


def _args(**over):
    base = dict(design="team", arms="dmn_village,cot_village,cotx3_village",
                gate="llm", ablate="", tau=0.35, confirmatory=True,
                budget_cap=1600.0, games=184, seed=5000)
    base.update(over)
    return type("A", (), base)()


class TestConfirmatoryAssertions(unittest.TestCase):
    def test_valid_confirmatory_passes(self):
        from src.eval.run_arena import _assert_confirmatory

        _assert_confirmatory(_args())  # no raise

    def test_tau_must_be_explicit_035(self):
        from src.eval.run_arena import _assert_confirmatory

        with self.assertRaises(SystemExit):
            _assert_confirmatory(_args(tau=None))
        with self.assertRaises(SystemExit):
            _assert_confirmatory(_args(tau=0.45))

    def test_gate_and_ablate_and_design(self):
        from src.eval.run_arena import _assert_confirmatory

        with self.assertRaises(SystemExit):
            _assert_confirmatory(_args(gate="jev"))
        with self.assertRaises(SystemExit):
            _assert_confirmatory(_args(ablate="evt"))
        with self.assertRaises(SystemExit):
            _assert_confirmatory(_args(design="focal"))

    def test_non_confirmatory_skips(self):
        from src.eval.run_arena import _assert_confirmatory

        _assert_confirmatory(_args(confirmatory=False, tau=None, gate="jev"))

    def test_prompt_hash_is_sha256_hex(self):
        from src.eval.run_arena import _prompt_hash

        h = _prompt_hash()
        self.assertEqual(len(h), 64)
        int(h, 16)

    def test_manifest_contains_prereg_fields(self):
        import json
        import tempfile
        import os

        from src.eval.run_arena import _write_manifest

        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "manifest.json")
            _write_manifest(path, _args(), "test-tag", "abc123")
            m = json.load(open(path))
        self.assertIn("prompt_hash", m)
        self.assertIn("design", m)
        self.assertIn("arm_map", m)
        self.assertEqual(m["llm"]["vote_temperature"], 0.7)
        self.assertTrue(m["probe_enabled"])
        self.assertIn("budget_cap_inr", m)


if __name__ == "__main__":
    unittest.main()
