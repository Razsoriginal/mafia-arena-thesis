"""Budget cap: Rs.5,000 hard cap set by the user on 2026-11-17 (master
brief SS8); it replaces the Rs.2,000 cap of pre-reg v2 SS9. The cap is
never raised by the analyst."""
import unittest

from tests.test_manifest_assertions import _args, _frozen


class TestBudgetCapV2(unittest.TestCase):
    def test_gate_accepts_cap_5000(self):
        from src.eval import run_arena

        with _frozen(run_arena):
            run_arena._assert_confirmatory(_args(budget_cap=5000.0))

    def test_gate_refuses_cap_above_5000(self):
        from src.eval import run_arena

        with _frozen(run_arena):
            with self.assertRaises(SystemExit):
                run_arena._assert_confirmatory(_args(budget_cap=5000.01))

    def test_constant_and_cli_default_are_5000(self):
        import sys
        from unittest.mock import patch
        from src.eval import run_arena

        self.assertEqual(run_arena.PREREG_BUDGET_CAP, 5000.0)
        seen = {}

        def _stop(args):
            seen["cap"] = args.budget_cap
            raise SystemExit(0)

        with patch.object(sys, "argv", ["run_arena", "--design", "team", "--tau", "0.35"]), \
                patch.object(run_arena, "_assert_confirmatory", _stop):
            with self.assertRaises(SystemExit):
                run_arena.main()
        self.assertEqual(seen["cap"], 5000.0)


if __name__ == "__main__":
    unittest.main()
