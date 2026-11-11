import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from src import llm_client
from src.eval import run_arena

from tests.round2_support import _team_row  # noqa: F401  (shared fixture)


def _fake_resp(payload):
    m = MagicMock()
    m.choices[0].message.content = json.dumps(payload)
    m.choices[0].message.reasoning_content = ""
    m.choices[0].message.reasoning = ""
    m.model = "meta/muse-spark-1.3-contributor"
    m.usage.prompt_tokens = 10
    m.usage.completion_tokens = 5
    m.usage.cost = 0.01
    return m


GENERIC_JSON = {
    "vote": "no-lynch", "reason": "r", "hypotheses": [], "verified": [],
    "trust": {}, "kill": "", "save": "", "check": "",
    "commitment": "", "delay_cause": None,
}


def _task(arm, run_dir, run_id="mock-9000", seed=9000):
    return {"requested_seed": seed, "focal": arm, "arm": arm,
            "design": "team", "run_id": run_id, "campaign": "mock",
            "gate": "llm", "focal_role": "random", "night_mode": "llm",
            "run_tag": "mock", "run_dir": run_dir, "max_days": 5,
            "tau": 0.35, "ablate": [], "git_sha": "abc123"}


class TestMockedGameG1G2V4(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.mkdtemp(prefix="mafia-mock-")
        for k in llm_client.COST_LOG:
            llm_client.COST_LOG[k] = 0.0 if k == "cost_inr" else 0

    def _play(self, arm, run_id):
        with patch.object(llm_client, "get_client") as gc, patch.object(
            run_arena, "_log_progress", lambda *a, **k: None
        ):
            gc.return_value.chat.completions.create.return_value = _fake_resp(
                GENERIC_JSON)
            return run_arena._run_task_once(_task(arm, self._td, run_id))

    def _raw(self, run_id):
        p = os.path.join(self._td, "raw", f"task-{run_id}", "llm_raw.jsonl")
        with open(p, encoding="utf-8") as f:
            return [json.loads(x) for x in f]

    def test_per_call_costs_match_game_billed_and_probe_cost(self):
        res = self._play("dmn_village", "mock-dmn")
        raw = self._raw("mock-dmn")
        row = res["row"]
        self.assertGreater(len(raw), 0)
        self.assertAlmostEqual(sum(r["cost_inr"] for r in raw),
                               row["billed_cost_inr"], places=4)
        self.assertEqual(len(raw), llm_client.COST_LOG["calls"])
        self.assertTrue(all(r["realised_model"] for r in raw))
        self.assertTrue(all(r["purpose"] in llm_client.PURPOSES for r in raw))
        self.assertTrue(all("prompt_tokens" in r and "completion_tokens" in r
                            for r in raw))
        purposes = {r["purpose"] for r in raw}
        self.assertTrue({"dmn_reason", "tpn_reason", "vote", "probe"}
                        .issubset(purposes), purposes)
        probe_rows = [r for r in raw if r["purpose"] == "probe"]
        self.assertGreater(len(probe_rows), 0)
        self.assertGreater(sum(r["cost_inr"] for r in probe_rows), 0)

    def test_probe_targets_exclude_mafia_and_self(self):
        res = self._play("cot_village", "mock-cot")
        probe = [t for t in res["trust"] if t.get("trust_source") == "probe"]
        self.assertTrue(probe)
        self.assertFalse(any(t["voter_role"] == "mafia" for t in probe))
        self.assertTrue(all(t["elicited"] and not t["verified"] for t in probe))
        alive_by_day = {}
        for v in res["votes"]:
            alive_by_day.setdefault(int(v["day"]), set()).add(int(v["voter"]))
        for t in probe:
            day = int(t["day"])
            self.assertIn(int(t["target"]), alive_by_day[day])
            self.assertNotEqual(str(t["agent"]), str(t["target"]))
        df = pd.DataFrame(probe)
        for (day, agent), grp in df.groupby(["day", "agent"]):
            expected = {str(a) for a in alive_by_day[int(day)]
                        if str(a) != str(agent)}
            self.assertEqual(set(grp["target"].astype(str)), expected)

    def test_null_arm_has_no_probe(self):
        res = self._play("random_village", "mock-null")
        self.assertEqual([t for t in res["trust"]
                          if t.get("trust_source") == "probe"], [])
        raw = self._raw("mock-null")
        self.assertFalse(any(r["purpose"] == "probe" for r in raw))
        self.assertTrue(res["votes"])


class TestTieV7(unittest.TestCase):
    def test_none_plus_two_different_gives_first_valid(self):
        from src.agents.baselines import CotX3Agent

        votes = [None, "4", "5"]
        state = {"n": 0}

        def fake(system, user, meta=None, temperature=None, **kw):
            v = votes[state["n"]]
            state["n"] += 1
            if meta is not None:
                meta.update({"parse_fail": v is None})
            return {"vote": v, "reason": "r"} if v is not None else {}

        with patch("src.agents.baselines.llm.chat_json", side_effect=fake):
            vote, info = CotX3Agent(pid=1).vote("villager", "hist", {})
        self.assertEqual(vote, "4")
        self.assertTrue(info["tie_all_different"])
        self.assertEqual(info["n_sample_parse_fails"], 1)


if __name__ == "__main__":
    unittest.main()
