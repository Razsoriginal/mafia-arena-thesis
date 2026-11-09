import re
import tempfile
import unittest
from unittest.mock import patch

from src import llm_client


def _fake_chat_text(system, user, temperature=None, log=True, response_format=None):
    return "I am watching the discussion."


def _fake_chat_json_cite_future(system, user, meta=None, temperature=None):
    if meta is not None:
        meta.update({"parse_fail": False, "repaired": False, "empty_raw": False, "error": None, "raw_len": 1})
    if "imaginative mind" in system:
        return {"hypotheses": [{"suspect": "1", "motive": "quiet", "confidence": 0.8}]}
    if "verifier mind" in system:
        return {"verified": [{"suspect": "1", "evidence_spans": [0], "contradiction_found": False, "revised_confidence": 0.8}]}
    if "Output trust scores" in system:
        return {"trust": {str(i): 0.6 for i in range(7)}}
    if "night" in system.lower() or "You choose a night action" in system:
        return {"kill": "0", "save": "0", "check": "1"}
    if "must justify" in system:
        turns = [int(x) for x in re.findall(r"\[t(\d+)", user)]
        future = (max(turns) + 1) if turns else 999
        return {"vote": "1", "reason": f"t{future} shows a claim"}
    return {"vote": "1", "reason": "suspect"}


def _fake_chat_json(system, user, meta=None, temperature=None):
    if meta is not None:
        meta.update({"parse_fail": False, "repaired": False, "empty_raw": False, "error": None, "raw_len": 1})
    if "imaginative mind" in system:
        return {"hypotheses": [{"suspect": "1", "motive": "quiet", "confidence": 0.8}]}
    if "verifier mind" in system:
        return {"verified": [{"suspect": "1", "evidence_spans": [0], "contradiction_found": False, "revised_confidence": 0.8}]}
    if "Output trust scores" in system:
        return {"trust": {str(i): 0.6 for i in range(7)}}
    if "night" in system.lower() or "You choose a night action" in system:
        return {"kill": "0", "save": "0", "check": "1"}
    if "must justify" in system:
        return {"vote": "1", "reason": "t0 shows a claim"}
    return {"vote": "1", "reason": "suspect"}


class TestVerifiedSemantics(unittest.TestCase):
    def test_dmn_only_suspects_are_not_verified(self):
        from src.eval.run_arena import _verified_suspects

        trace = {"tpn": {"verified": []},
                 "dmn": {"hypotheses": [{"suspect": "2"}, {"suspect": "3"}]}}
        self.assertEqual(_verified_suspects(trace), set())

    def test_tpn_verified_targets_are_verified(self):
        from src.eval.run_arena import _verified_suspects

        trace = {"tpn": {"verified": [{"suspect": "2"}]},
                 "dmn": {"hypotheses": [{"suspect": "3"}]}}
        self.assertEqual(_verified_suspects(trace), {"2"})


class TestCitationSnapshot(unittest.TestCase):
    def test_future_turn_citation_is_invalid(self):
        from src.eval import run_arena
        from src.eval.run_arena import play_one

        with tempfile.TemporaryDirectory() as td, patch.object(
            llm_client, "chat_text", side_effect=_fake_chat_text
        ), patch.object(llm_client, "chat_json", side_effect=_fake_chat_json_cite_future), patch.object(
            run_arena, "_log_progress", lambda *a, **k: None
        ):
            game = play_one(seed=5000, design="team", arm="dmn_village",
                            run_id="5000-dmn_village", requested_seed=5000,
                            max_days=1, run_dir=td, run_tag="mock")
        dmn_votes = [v for v in game._vote_rows if v["commitment"]]
        self.assertTrue(dmn_votes)
        for v in dmn_votes:
            self.assertEqual(v["cited_turns"], [])
            self.assertFalse(v["citation_valid"])


class TestDaysCount(unittest.TestCase):
    def test_first_day_game_records_one_day(self):
        from src.eval import run_arena

        task = {"run_tag": "mock", "run_dir": tempfile.mkdtemp(),
                "requested_seed": 5000, "focal": "dmn_village", "arm": "dmn_village",
                "design": "team", "gate": "llm", "focal_role": "random",
                "night_mode": "llm", "max_days": 1, "tau": None,
                "ablate": [], "git_sha": "abc123", "run_id": "5000-dmn_village"}
        with patch.object(llm_client, "chat_text", side_effect=_fake_chat_text), patch.object(
            llm_client, "chat_json", side_effect=_fake_chat_json
        ), patch.object(run_arena, "_log_progress", lambda *a, **k: None):
            out = run_arena._run_task_once(task)
        self.assertEqual(out["row"]["days"], 1)


class TestProbeFields(unittest.TestCase):
    def test_probe_rows_are_elicited_not_verified(self):
        from src.eval import run_arena
        from src.eval.run_arena import play_one

        with tempfile.TemporaryDirectory() as td, patch.object(
            llm_client, "chat_text", side_effect=_fake_chat_text
        ), patch.object(llm_client, "chat_json", side_effect=_fake_chat_json), patch.object(
            run_arena, "_log_progress", lambda *a, **k: None
        ):
            game = play_one(seed=5000, design="team", arm="cot_village",
                            run_id="5000-cot_village", requested_seed=5000,
                            max_days=1, run_dir=td, run_tag="mock")
        probe = [t for t in game._trust_rows if t["trust_source"] == "probe"]
        self.assertTrue(probe)
        for t in probe:
            self.assertTrue(t["elicited"])
            self.assertFalse(t["verified"])
            self.assertIn("parse_fail", t)

    def test_probe_parse_failure_records_missingness(self):
        from src.eval import run_arena
        from src.eval.run_arena import play_one

        def fail_probe(system, user, meta=None, temperature=None):
            if "Output trust scores" in system:
                if meta is not None:
                    meta.update({"parse_fail": True})
                return {}
            return _fake_chat_json(system, user, meta=meta, temperature=temperature)

        with tempfile.TemporaryDirectory() as td, patch.object(
            llm_client, "chat_text", side_effect=_fake_chat_text
        ), patch.object(llm_client, "chat_json", side_effect=fail_probe), patch.object(
            run_arena, "_log_progress", lambda *a, **k: None
        ):
            game = play_one(seed=5000, design="team", arm="cot_village",
                            run_id="5000-cot_village", requested_seed=5000,
                            max_days=1, run_dir=td, run_tag="mock")
        probe = [t for t in game._trust_rows if t["trust_source"] == "probe"]
        self.assertTrue(probe)
        self.assertTrue(all(t["parse_fail"] for t in probe))

    def test_probe_drops_dead_or_hallucinated_targets(self):
        from src.agents.baselines import CotAgent

        def fake(system, user, meta=None, temperature=None):
            if meta is not None:
                meta.update({"parse_fail": False})
            return {"trust": {"0": 0.2, "1": 0.9, "6": 0.1, "99": 0.5}}

        with patch("src.agents.base.llm.chat_json", side_effect=fake):
            trust, _info = CotAgent(pid=1).elicit_trust_probe("villager", "h", [0, 1, 2])
        self.assertEqual(trust, {"0": 0.2})


class TestCotX3ParseCounts(unittest.TestCase):
    def test_n_sample_parse_fails_counted(self):
        from src.agents.baselines import CotX3Agent

        votes = [None, "4", "4"]
        state = {"n": 0}

        def fake(system, user, meta=None, temperature=None):
            v = votes[state["n"]]
            state["n"] += 1
            if meta is not None:
                meta.update({"parse_fail": v is None})
            return {"vote": v, "reason": "r"} if v is not None else {}

        with patch("src.agents.baselines.llm.chat_json", side_effect=fake):
            _vote, info = CotX3Agent(pid=1).vote("villager", "hist", {})
        self.assertEqual(info["n_sample_parse_fails"], 1)
        self.assertEqual(info["sample_parse_fails"], [True, False, False])
        self.assertFalse(info["parse_fail"])  # unchanged: all() semantics kept


if __name__ == "__main__":
    unittest.main()
