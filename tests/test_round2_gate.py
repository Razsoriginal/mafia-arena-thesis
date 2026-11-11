import ast
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from src.eval import run_arena

from tests.round2_support import _RunEnv


class TestFreezeBlockG9(unittest.TestCase):
    GOOD = ("<!-- freeze\n"
            "prompts_sha256: " + "a" * 64 + "\n"
            "runpath_sha256: " + "b" * 64 + "\n"
            "freeze_git_sha: abc1234\n"
            "freeze_tag: freeze-v1\n-->\n")

    def test_good_block_valid(self):
        out = run_arena._parse_freeze_block(self.GOOD)
        self.assertTrue(out["valid"], out)

    def test_blank_missing_malformed_all_refuse(self):
        for text in ("", "no block here",
                     self.GOOD.replace("a" * 64, ""),
                     self.GOOD.replace("a" * 64, "xyz"),
                     self.GOOD.replace("freeze-v1", "PENDING"),
                     self.GOOD.replace("freeze_tag: freeze-v1\n", "")):
            out = run_arena._parse_freeze_block(text)
            self.assertFalse(out["valid"], text[:40])


class TestRunpathG10(unittest.TestCase):
    def test_import_closure_is_hashed(self):
        root = os.path.normpath(os.path.join(os.path.dirname(run_arena.__file__), ".."))
        hashed = {os.path.relpath(p, root).replace(os.sep, "/")
                  for p in run_arena._runpath_files()}
        entry = os.path.join(root, "eval", "run_arena.py")
        with open(entry, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mods.add(node.module)
            elif isinstance(node, ast.Import):
                mods.update(a.name for a in node.names)
        for mod in sorted(m for m in mods if m.startswith("src.")):
            rel = mod[len("src."):].replace(".", "/") + ".py"
            self.assertIn(rel, hashed, mod)

    def test_new_subpackage_module_changes_hash(self):
        sub = os.path.join(os.path.dirname(run_arena.__file__), "..",
                           "mafia", "_tmp_sub")
        sub = os.path.normpath(sub)
        os.makedirs(sub, exist_ok=True)
        target = os.path.join(sub, "mod_tmp.py")
        try:
            before = run_arena._runpath_sha256()
            with open(target, "w", encoding="utf-8") as f:
                f.write("X = 1\n")
            self.assertNotEqual(run_arena._runpath_sha256(), before)
        finally:
            if os.path.exists(target):
                os.remove(target)
            if os.path.isdir(sub) and not os.listdir(sub):
                os.rmdir(sub)


class TestScopedDirtyG6(unittest.TestCase):
    def test_logs_artifact_does_not_block_but_runpath_edit_does(self):
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["git", "init", "-q"], cwd=td, check=True)
            subprocess.run(["git", "config", "user.email", "t@t"], cwd=td,
                           check=True)
            subprocess.run(["git", "config", "user.name", "t"], cwd=td,
                           check=True)
            os.makedirs(os.path.join(td, "src", "agents"))
            os.makedirs(os.path.join(td, "logs"))
            with open(os.path.join(td, "src", "agents", "x.py"), "w") as f:
                f.write("X=1\n")
            subprocess.run(["git", "add", "-A"], cwd=td, check=True)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=td, check=True)
            subprocess.run(["git", "tag", "freeze-v1"], cwd=td, check=True)
            with open(os.path.join(td, "later.txt"), "w") as f:
                f.write("x\n")
            subprocess.run(["git", "add", "-A"], cwd=td, check=True)
            subprocess.run(["git", "commit", "-qm", "later"], cwd=td, check=True)
            old = os.getcwd()
            try:
                os.chdir(td)
                with patch.object(run_arena, "_runpath_relpaths",
                                  lambda: ["src/agents/x.py"]):
                    # a logs/ artifact is dirty but out of scope
                    with open(os.path.join(td, "logs", "spend_ledger.jsonl"),
                              "w") as f:
                        f.write("{}\n")
                    self.assertEqual(run_arena._dirty_runpath_files(), [])
                    self.assertTrue(run_arena._freeze_tag_ancestor("freeze-v1"))
                    with open(os.path.join(td, "src", "agents", "x.py"),
                              "a") as f:
                        f.write("Y=2\n")
                    self.assertEqual(run_arena._dirty_runpath_files(),
                                     ["src/agents/x.py"])
            finally:
                os.chdir(old)


class TestCalibrationGoG7(_RunEnv):
    def _paths(self):
        return (os.path.join(self._td, "calibration_go.json"),
                os.path.join(self._td, "calibration_report.json"))

    def _report(self, payload=None):
        _, rep = self._paths()
        with open(rep, "w", encoding="utf-8") as f:
            json.dump(payload if payload is not None else {"ok": 1}, f)
        with open(rep, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def _go(self, campaign, report_sha=None, empty=False):
        go, _ = self._paths()
        if empty:
            open(go, "w").close()
            return
        with open(go, "w", encoding="utf-8") as f:
            json.dump({"campaign": campaign,
                       "calibration_report_sha256": report_sha or "0" * 64,
                       "created_at": "2026-11-11T00:00:00Z",
                       "approved_by": "tester"}, f)

    def _argv(self, extra):
        go, rep = self._paths()
        return (self._base("g7", "g7", **{"calibration-go": go,
                                          "calibration-report": rep})
                + extra)

    def test_trios_184_straight_pauses_after_20(self):
        self._run(self._argv(["--trios", "184"]))
        self.assertEqual(len(self.calls), 60)

    def test_calibration_flag_cannot_bypass_start_at_20(self):
        with self.assertRaises(SystemExit):
            self._run(self._argv(["--calibration", "--start-trio", "20",
                                  "--trios", "1"]))
        self.assertEqual(self.calls, [])

    def test_empty_go_refuses(self):
        self._go("g7", empty=True)
        with self.assertRaises(SystemExit):
            self._run(self._argv(["--start-trio", "20", "--trios", "1"]))
        self.assertEqual(self.calls, [])

    def test_other_campaign_go_refuses(self):
        sha = self._report()
        self._go("other-campaign", report_sha=sha)
        with self.assertRaises(SystemExit):
            self._run(self._argv(["--start-trio", "20", "--trios", "1"]))
        self.assertEqual(self.calls, [])

    def test_stale_report_hash_refuses(self):
        self._report()
        self._go("g7")  # all-zero hash, real report differs
        with self.assertRaises(SystemExit):
            self._run(self._argv(["--start-trio", "20", "--trios", "1"]))
        self.assertEqual(self.calls, [])

    def test_valid_go_allows_start_at_20(self):
        sha = self._report()
        self._go("g7", report_sha=sha)
        self._run(self._argv(["--start-trio", "20", "--trios", "1"]))
        self.assertEqual(len(self.calls), 3)


class TestRequiredTauG11(_RunEnv):
    def test_team_run_without_tau_refuses(self):
        argv = ["--design", "team",
                "--arms", "dmn_village,cot_village,cotx3_village",
                "--seed", "9000", "--trios", "1", "--campaign", "notau",
                "--run-tag", "notau", "--out", self.out]
        with self.assertRaises(SystemExit):
            self._run(argv)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
