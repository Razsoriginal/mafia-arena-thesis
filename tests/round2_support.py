import os
import tempfile
import unittest
from unittest.mock import patch

from src.eval import run_arena


def _row(arm="cot_village", seed=9000, campaign="camp", cost=5.0, gid=None):
    return {"run_tag": "t", "campaign": campaign,
            "game_id": gid or f"{campaign}-{seed}-{arm}",
            "requested_seed": seed, "arm": arm, "focal": arm,
            "billed_cost_inr": cost, "est_cost_inr": cost,
            "winner": "village", "days": 2, "focal_role": "villager",
            "focal_pid": 0, "json_failures": 0, "design": "team"}


def _team_row(task, cost=0.01):
    arm = task["arm"]
    return {
        "run_tag": task["run_tag"], "campaign": task["campaign"],
        "game_id": task["run_id"], "requested_seed": task["requested_seed"],
        "arm": arm, "focal": arm, "village_arm": arm, "mafia_arm": "cot",
        "billed_cost_inr": cost, "est_cost_inr": cost, "winner": "village",
        "days": 2, "focal_role": "villager", "focal_pid": 0,
        "json_failures": 0, "design": "team", "provider": "aicredits",
        "model": "meta/muse-spark-1.3-contributor", "gate": "llm",
        "night_mode": "llm", "seed": task["requested_seed"],
    }


def _with_rows(task):
    row = _team_row(task)
    vote = {"run_tag": task["run_tag"], "campaign": task["campaign"],
            "game_id": task["run_id"], "day": 0, "voter": 0,
            "vote": "no-lynch", "arm": task["arm"]}
    trust = {"run_tag": task["run_tag"], "campaign": task["campaign"],
             "game_id": task["run_id"], "day": 0, "agent": 0, "target": "1",
             "trust": 0.5, "trust_source": "probe", "arm": task["arm"],
             "target_is_mafia": False}
    return {"row": row, "votes": [vote], "trust": [trust]}


class _RunEnv(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.mkdtemp(prefix="mafia-r2-")
        self._env = {}
        for k, v in {
            "MAFIA_SPEND_LEDGER": os.path.join(self._td, "ledger.jsonl"),
            "MAFIA_PENDING_FILE": os.path.join(self._td, "pending.json"),
            "MAFIA_RUNS_DIR": os.path.join(self._td, "runs"),
            "MAFIA_RAW_DIR": os.path.join(self._td, "raw"),
        }.items():
            self._env[k] = os.environ.get(k)
            os.environ[k] = v
        self.out = os.path.join(self._td, "games.parquet")
        self.calls = []

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _run(self, argv, runner=_team_row):
        import sys

        calls = self.calls

        def fake(task):
            calls.append(task["run_id"])
            res = runner(task)
            return res if isinstance(res, dict) and "row" in res else {
                "row": res, "votes": [], "trust": []}

        with patch.object(sys, "argv", ["run_arena"] + argv), patch.object(
            run_arena, "_run_task_once", side_effect=fake
        ), patch.object(run_arena, "_log_progress", lambda *a, **k: None):
            run_arena.main()

    def _base(self, campaign, tag, **over):
        args = ["--design", "team",
                "--arms", "dmn_village,cot_village,cotx3_village",
                "--seed", "9000", "--workers", "1", "--tau", "0.35",
                "--campaign", campaign, "--run-tag", tag, "--out", self.out]
        for k, v in over.items():
            args += [f"--{k.replace('_', '-')}", str(v)]
        return args
