"""Phase 0 budget amendment: hard cap Rs.2,000, no locked reserve
(Pre-reg v2 SS9). The confirmatory gate accepts a cap up to 2,000."""
import unittest

from tests.test_manifest_assertions import _args, _frozen


class TestBudgetCapV2(unittest.TestCase):
    def test_gate_accepts_cap_2000(self):
        from src.eval import run_arena

        with _frozen(run_arena):
            run_arena._assert_confirmatory(_args(budget_cap=2000.0))

    def test_gate_refuses_cap_above_2000(self):
        from src.eval import run_arena

        with _frozen(run_arena):
            with self.assertRaises(SystemExit):
                run_arena._assert_confirmatory(_args(budget_cap=2000.01))

    def test_constant_and_cli_default_are_2000(self):
        import sys
        from unittest.mock import patch
        from src.eval import run_arena

        self.assertEqual(run_arena.PREREG_BUDGET_CAP, 2000.0)
        seen = {}

        def _stop(args):
            seen["cap"] = args.budget_cap
            raise SystemExit(0)

        with patch.object(sys, "argv", ["run_arena", "--design", "team", "--tau", "0.35"]), \
                patch.object(run_arena, "_assert_confirmatory", _stop):
            with self.assertRaises(SystemExit):
                run_arena.main()
        self.assertEqual(seen["cap"], 2000.0)


if __name__ == "__main__":
    unittest.main()
