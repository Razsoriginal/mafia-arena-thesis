"""Phase 0 ledger fixes: shared absolute path, raw-reconciled spend,
campaign-scoped trio projection, source field (Pre-reg SS9, SS15)."""
import json
import os
import subprocess
import tempfile
import unittest

from src.eval import run_arena


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class TestSharedLedgerPath(unittest.TestCase):
    def test_default_ledger_resolves_to_main_repo_from_worktree(self):
        with tempfile.TemporaryDirectory() as td:
            main = os.path.join(td, "main")
            os.makedirs(main)
            _git(main, "init", "-q")
            _git(main, "config", "user.email", "t@t")
            _git(main, "config", "user.name", "t")
            with open(os.path.join(main, "f"), "w") as f:
                f.write("x")
            _git(main, "add", "-A")
            _git(main, "commit", "-qm", "i")
            wt = os.path.join(td, "wt")
            _git(main, "worktree", "add", "-q", wt)
            old = os.environ.pop("MAFIA_SPEND_LEDGER", None)
            try:
                p_main = run_arena._default_ledger_path(start=main)
                p_wt = run_arena._default_ledger_path(start=wt)
            finally:
                if old is not None:
                    os.environ["MAFIA_SPEND_LEDGER"] = old
            self.assertTrue(os.path.isabs(p_wt))
            self.assertEqual(os.path.realpath(p_main), os.path.realpath(p_wt))
            self.assertEqual(os.path.realpath(p_wt),
                             os.path.realpath(os.path.join(main, "logs", "spend_ledger.jsonl")))

    def test_env_override_is_made_absolute(self):
        old = os.environ.get("MAFIA_SPEND_LEDGER")
        os.environ["MAFIA_SPEND_LEDGER"] = "rel/ledger.jsonl"
        try:
            p = run_arena._ledger_path(None)
        finally:
            if old is None:
                os.environ.pop("MAFIA_SPEND_LEDGER", None)
            else:
                os.environ["MAFIA_SPEND_LEDGER"] = old
        self.assertTrue(os.path.isabs(p))


class TestRawReconcile(unittest.TestCase):
    def _raw(self, d, costs):
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "llm_raw.jsonl"), "a") as f:
            for c in costs:
                f.write(json.dumps({"cost_inr": c, "purpose": "speak"}) + "\n")

    def test_unledgered_raw_spend_is_appended_as_discarded(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = os.path.join(td, "ledger.jsonl")
            raw = os.path.join(td, "raw", "task-c-9000-dmn_village")
            # first in-worker attempt crashed after Rs.1.0; retry cost Rs.2.0
            self._raw(raw, [0.4, 0.6, 1.5, 0.5])
            row = {"run_tag": "r", "campaign": "c", "game_id": "c-9000-dmn_village",
                   "requested_seed": 9000, "arm": "dmn_village",
                   "billed_cost_inr": 2.0, "est_cost_inr": 2.0}
            run_arena._append_ledger(ledger, row, campaign="c", status="kept")
            added = run_arena._reconcile_task_spend(
                ledger, raw_dir=raw, run_tag="r", campaign="c",
                game_id="c-9000-dmn_village", requested_seed=9000,
                arm="dmn_village")
            self.assertAlmostEqual(added, 1.0, places=6)
            self.assertAlmostEqual(run_arena._ledger_total(ledger), 3.0, places=6)
            ent = run_arena._ledger_entries(ledger)
            self.assertEqual(ent[-1]["status"], "discarded")
            self.assertEqual(ent[-1]["source"], "raw-reconcile")
            # idempotent: nothing new on a second reconcile
            again = run_arena._reconcile_task_spend(
                ledger, raw_dir=raw, run_tag="r", campaign="c",
                game_id="c-9000-dmn_village", requested_seed=9000,
                arm="dmn_village")
            self.assertAlmostEqual(again, 0.0, places=6)

    def test_failed_task_with_no_row_is_fully_ledgered(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = os.path.join(td, "ledger.jsonl")
            raw = os.path.join(td, "raw", "task-c-9000-cot_village")
            self._raw(raw, [0.25, 0.25])
            added = run_arena._reconcile_task_spend(
                ledger, raw_dir=raw, run_tag="r", campaign="c",
                game_id="c-9000-cot_village", requested_seed=9000,
                arm="cot_village")
            self.assertAlmostEqual(added, 0.5, places=6)
            self.assertAlmostEqual(run_arena._ledger_total(ledger), 0.5, places=6)


class TestProjectionScope(unittest.TestCase):
    def test_projection_ignores_other_campaigns_and_seedless_rows(self):
        hist = [
            {"campaign": "pilot-backfill", "requested_seed": None,
             "billed_cost_inr": 30.92, "ledger_status": "kept"},
            {"campaign": "smoke-team-01", "requested_seed": 9000,
             "billed_cost_inr": 12.0, "ledger_status": "kept"},
            {"campaign": "camp", "requested_seed": 5000,
             "billed_cost_inr": 9.0, "ledger_status": "kept"},
        ]
        got = run_arena._projected_trio_cost(hist, 8.13, campaign="camp")
        self.assertAlmostEqual(got, 9.0)
        # no rows for this campaign yet -> planned cost
        got2 = run_arena._projected_trio_cost(hist, 8.13, campaign="new")
        self.assertAlmostEqual(got2, 8.13)


class TestLedgerSource(unittest.TestCase):
    def test_append_records_source(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = os.path.join(td, "l.jsonl")
            run_arena._append_ledger(ledger, {"billed_cost_inr": 1.0,
                                              "game_id": "g"}, campaign="c")
            self.assertEqual(run_arena._ledger_entries(ledger)[0]["source"], "run_arena")


if __name__ == "__main__":
    unittest.main()
