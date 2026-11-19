"""Mafia stress test with a repaired gate (pre-reg v3 SS12.5; master
re-evaluation E2.5, E3.1, E7.5).

The gate runs at the action boundary: after the day's discussion, on the
snapshot the vote uses, with vote wording identical across arms. All model
calls are mocked; no network.
"""
import hashlib
import os
import re
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from src import llm_client
from src.config import settings

from tests.round2_support import _RunEnv, _team_row

SEED = 100300
V3_PAIR = ("gated_village_v3", "cot_village_v3")


def _h(*parts) -> int:
    return int(hashlib.sha256("\x1f".join(parts).encode()).hexdigest(), 16)


def _pid(user):
    m = re.match(r"You are Player (\d+)", user)
    return int(m.group(1)) if m else None


def _history_block(user):
    """The history text embedded in a v3 vote or verification prompt."""
    m = re.search(r"History:\n(.*)\n(?:Vote for|Task:)", user, re.S)
    return m.group(1) if m else None


class _Model:
    """Deterministic fake keyed on the exact prompt, recording every call."""

    def __init__(self, confidence=0.9, verify=None):
        self.confidence = confidence
        self.verify = verify
        self.calls = []

    def _rec(self, kind, system, user, temperature, purpose):
        self.calls.append({"kind": kind, "system": system, "user": user,
                           "temperature": temperature, "purpose": purpose,
                           "pid": _pid(user)})

    def text(self, system, user, temperature=None, purpose=None, **kw):
        self._rec("text", system, user, temperature, purpose)
        return f"line-{_h(system, user) % 10**8}"

    def json(self, system, user, meta=None, temperature=None, purpose=None, **kw):
        from src.mafia import prompts_v3 as P3

        self._rec("json", system, user, temperature, purpose)
        if meta is not None:
            meta.clear()
            meta.update({"parse_fail": False})
        h = _h(system, user)
        if system == P3.GATE_VERIFY_SYSTEM:
            if self.verify is not None:
                return self.verify(system, user, meta)
            m = re.search(r"Alive others: \[([^\]]*)\]", user)
            others = [x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()]
            return {"suspect": others[h % len(others)], "evidence_turns": [0],
                    "confidence": self.confidence}
        if "night action" in system:
            opts = re.search(r"Choose exactly one target from \[([^\]]*)\]", user)
            o = [x.strip() for x in opts.group(1).split(",")]
            key = "kill" if "kill" in user.split("Night action:")[-1][:40] else (
                "save" if "protect" in user else "check")
            return {key: o[h % len(o)], "reason": "r"}
        if "Output trust scores" in system:
            return {"trust": {}}
        return {"vote": str(h % 7), "reason": f"t{h % 5} shows it"}

    def of(self, purpose=None, pids=None):
        return [c for c in self.calls
                if (purpose is None or c["purpose"] == purpose)
                and (pids is None or c["pid"] in pids)]


def _play(arm, model, max_days=1, seed=SEED, tau=0.35):
    from src.eval import run_arena

    old_tau, old_threads = settings.tau_delay, os.environ.get("MAFIA_CALL_THREADS")
    settings.tau_delay = tau
    os.environ["MAFIA_CALL_THREADS"] = "1"
    try:
        with tempfile.TemporaryDirectory() as td, \
                patch.object(llm_client, "chat_text", side_effect=model.text), \
                patch.object(llm_client, "chat_json", side_effect=model.json), \
                patch.object(run_arena, "_log_progress", lambda *a, **k: None):
            return run_arena.play_one(seed=seed, design="team", arm=arm,
                                      run_id=f"{seed}-{arm}", requested_seed=seed,
                                      max_days=max_days, run_dir=td, run_tag="mock",
                                      campaign="smoke-mock")
    finally:
        settings.tau_delay = old_tau
        if old_threads is None:
            os.environ.pop("MAFIA_CALL_THREADS", None)
        else:
            os.environ["MAFIA_CALL_THREADS"] = old_threads


def _roles(game):
    mafia = {p.pid for p in game.players if p.role == "mafia"}
    return mafia, {p.pid for p in game.players} - mafia


class TestNeutralPrompt(unittest.TestCase):
    def test_neutral_vote_prompt_has_no_pressure_and_no_commitment(self):
        from src.mafia import prompts_v3 as P3

        text = P3.vote_neutral_user(2, "villager", "[t0 night-0 Pengine]: x")
        self.assertNotIn("endless delay", text)
        self.assertNotIn("loses games", text)
        self.assertNotIn("commitment", text.lower())
        self.assertNotIn("cite", text.lower())
        self.assertIn('"no-lynch"', text)
        self.assertIn("[t0 night-0 Pengine]: x", text)

    def test_existing_vote_prompts_are_unchanged(self):
        from src.mafia import prompts as P

        self.assertIn("endless delay also loses games", P.vote_user(1, "villager", "h", {}))
        self.assertIn("Your commitment", P.vote_cited_user(1, "villager", "h", {}))


class TestGatedCotAgentUnit(unittest.TestCase):
    HIST = "[t0 night-0 Pengine]: Night: Player 6 was killed.\n[t1 day-0-r0 P1]: hello"
    ALIVE = [0, 1, 2, 3, 4, 5]

    def _vote(self, verify, tau=0.35, alive=None):
        from src.agents.gated_agent import GatedCotAgent

        model = _Model(verify=verify)
        old = settings.tau_delay
        settings.tau_delay = tau
        try:
            with patch.object(llm_client, "chat_json", side_effect=model.json), \
                    patch.object(llm_client, "chat_text", side_effect=model.text):
                v, info = GatedCotAgent(pid=2).vote(
                    "villager", self.HIST, {}, prev_majority=None, seed=1, day=0,
                    alive=self.ALIVE if alive is None else alive)
        finally:
            settings.tau_delay = old
        return v, info, model

    def test_high_confidence_verifies_then_votes_with_the_baseline_prompt(self):
        from src.agents.baselines import CotNeutralAgent
        from src.mafia import prompts_v3 as P3

        v, info, model = self._vote(lambda s, u, m: {
            "suspect": "4", "evidence_turns": [1], "confidence": 0.8})
        self.assertEqual([c["purpose"] for c in model.calls], ["tpn_reason", "vote"])
        verify, vote = model.calls
        self.assertEqual(verify["temperature"], 0)
        self.assertEqual(verify["system"], P3.GATE_VERIFY_SYSTEM)
        self.assertIn(self.HIST, verify["user"])
        self.assertEqual(vote["temperature"], settings.vote_temperature)
        self.assertEqual(v, str(_h(vote["system"], vote["user"]) % 7))
        self.assertIsNone(info["delay_cause"])
        self.assertFalse(info["parse_fail"])
        self.assertEqual(info["gate_confidence"], 0.8)
        self.assertEqual(info["gate_suspect"], "4")

        base = _Model()
        with patch.object(llm_client, "chat_json", side_effect=base.json):
            CotNeutralAgent(pid=2).vote("villager", self.HIST, {}, prev_majority=None,
                                        seed=1, day=0, alive=self.ALIVE)
        self.assertEqual(len(base.calls), 1)
        for k in ("system", "user", "temperature", "purpose"):
            self.assertEqual(vote[k], base.calls[0][k], k)
        self.assertEqual(vote["user"].encode(),
                         P3.vote_neutral_user(2, "villager", self.HIST).encode())

    def test_low_confidence_holds_without_a_vote_call(self):
        v, info, model = self._vote(lambda s, u, m: {
            "suspect": "4", "evidence_turns": [], "confidence": 0.2})
        self.assertEqual(v, "no-lynch")
        self.assertEqual(info["delay_cause"], "low_confidence")
        self.assertFalse(info["parse_fail"])
        self.assertEqual(info["gate_confidence"], 0.2)
        self.assertEqual([c["purpose"] for c in model.calls], ["tpn_reason"])

    def test_confidence_equal_to_tau_votes(self):
        v, info, model = self._vote(lambda s, u, m: {
            "suspect": "4", "evidence_turns": [1], "confidence": 0.35}, tau=0.35)
        self.assertIsNone(info["delay_cause"])
        self.assertEqual(len(model.of("vote")), 1)

    def test_parse_failure_holds_as_json_failure(self):
        def broken(system, user, meta):
            meta["parse_fail"] = True
            return {}

        v, info, model = self._vote(broken)
        self.assertEqual(v, "no-lynch")
        self.assertEqual(info["delay_cause"], "json_failure")
        self.assertTrue(info["parse_fail"])
        self.assertIsNone(info["gate_confidence"])
        self.assertEqual([c["purpose"] for c in model.calls], ["tpn_reason"])

    def test_malformed_verification_is_a_json_failure(self):
        bad = [
            {"suspect": "4", "evidence_turns": [1]},                       # no confidence
            {"suspect": "4", "evidence_turns": [1], "confidence": "high"},  # not a number
            {"suspect": "4", "evidence_turns": [1], "confidence": 85},      # outside 0-1
            {"suspect": "4", "evidence_turns": [1], "confidence": float("nan")},
            {"suspect": "2", "evidence_turns": [1], "confidence": 0.9},     # self
            {"suspect": "6", "evidence_turns": [1], "confidence": 0.9},     # dead
            {"evidence_turns": [1], "confidence": 0.9},                     # no suspect
            ["not", "an", "object"],
        ]
        for payload in bad:
            v, info, model = self._vote(lambda s, u, m, p=payload: p)
            self.assertEqual(v, "no-lynch", payload)
            self.assertEqual(info["delay_cause"], "json_failure", payload)
            self.assertTrue(info["parse_fail"], payload)
            self.assertEqual(len(model.of("vote")), 0, payload)

    def test_speaks_exactly_like_cot(self):
        from src.agents.baselines import CotAgent
        from src.agents.gated_agent import GatedCotAgent

        a, b = _Model(), _Model()
        with patch.object(llm_client, "chat_text", side_effect=a.text):
            out_a = GatedCotAgent(pid=3).speak("doctor", self.HIST)
        with patch.object(llm_client, "chat_text", side_effect=b.text):
            out_b = CotAgent(pid=3).speak("doctor", self.HIST)
        self.assertEqual(out_a, out_b)
        self.assertEqual(a.calls, b.calls)

    def test_has_no_pre_discussion_reasoning(self):
        from src.agents.gated_agent import GatedCotAgent

        self.assertFalse(hasattr(GatedCotAgent(pid=0), "reason"))


class TestV3Arms(unittest.TestCase):
    def test_arm_map_and_seat_classes(self):
        from src.agents.baselines import CotAgent, CotNeutralAgent
        from src.agents.dmn_tpn_agent import DmnTpnAgent
        from src.agents.gated_agent import GatedCotAgent
        from src.agents.null_agents import NoLynchAgent
        from src.eval.run_arena import TEAM_ARMS, _build_agents
        from src.mafia.engine import Game

        self.assertEqual(TEAM_ARMS["gated_village_v3"]["mafia"],
                         TEAM_ARMS["cot_village_v3"]["mafia"])
        self.assertEqual(TEAM_ARMS["gated_village_v3"]["mafia"],
                         TEAM_ARMS["nolynch_village_v3"]["mafia"])
        game = Game(seed=SEED)
        for arm, village_cls in (("gated_village_v3", GatedCotAgent),
                                 ("cot_village_v3", CotNeutralAgent),
                                 ("nolynch_village_v3", NoLynchAgent)):
            agents = _build_agents(game, focal_pid=0, design="team", arm=arm)
            for p in game.players:
                ag = agents[p.pid]
                self.assertNotIsInstance(ag, DmnTpnAgent, arm)
                if p.role == "mafia":
                    self.assertIs(type(ag), CotNeutralAgent, arm)
                    self.assertIsInstance(ag, CotAgent, arm)
                else:
                    self.assertIs(type(ag), village_cls, arm)

    def test_gate_runs_after_discussion_on_the_vote_snapshot(self):
        from src.mafia import prompts_v3 as P3

        model = _Model(confidence=0.9)
        game = _play("gated_village_v3", model)
        mafia, village = _roles(game)
        said = [h for h in game.history if str(h["phase"]).startswith("day-0-r")]
        self.assertGreaterEqual(len(said), 10)  # two rounds, every living seat
        verifies = model.of("tpn_reason")
        self.assertTrue(verifies)
        self.assertEqual({c["pid"] for c in verifies},
                         {v["voter"] for v in game._vote_rows if v["is_village"]})
        self.assertFalse(model.of("dmn_reason"))  # no pre-discussion reasoning
        for c in verifies:
            self.assertEqual(c["system"], P3.GATE_VERIFY_SYSTEM)
            self.assertEqual(c["temperature"], 0)
            self.assertIn(c["pid"], village)
            for h in said:
                self.assertIn(f"[t{h['turn']} {h['phase']} P{h['speaker']}]: {h['text']}",
                              c["user"])
            # same snapshot as the vote: the history block of the seat's
            # verification prompt equals the one in its vote prompt, and no
            # vote line of the day is in it.
            (vote,) = model.of("vote", pids={c["pid"]})
            self.assertIsNotNone(_history_block(c["user"]))
            self.assertEqual(_history_block(c["user"]), _history_block(vote["user"]))
            self.assertNotIn("vote-0", c["user"])
        # every verification call comes after the last speech of the day
        last_speak = max(i for i, c in enumerate(model.calls) if c["purpose"] == "speak")
        first_verify = min(i for i, c in enumerate(model.calls) if c["purpose"] == "tpn_reason")
        self.assertGreater(first_verify, last_speak)

    def test_day0_is_not_a_forced_abstention(self):
        model = _Model(confidence=0.9)
        game = _play("gated_village_v3", model)
        rows = [v for v in game._vote_rows if v["day"] == 0 and v["is_village"]]
        self.assertGreaterEqual(len(rows), 4)
        for v in rows:
            self.assertNotEqual(v["vote"], "no-lynch")
            self.assertIsNone(v["delay_cause"])
            self.assertFalse(v["parse_fail"])
            self.assertEqual(v["gate_confidence"], 0.9)
            self.assertIsNotNone(v["gate_suspect"])

    def test_vote_rows_record_cause_parse_fail_and_confidence(self):
        model = _Model(confidence=0.1)
        game = _play("gated_village_v3", model)
        mafia, village = _roles(game)
        for v in game._vote_rows:
            for k in ("delay_cause", "parse_fail", "gate_confidence", "gate_suspect"):
                self.assertIn(k, v)
            if v["is_village"]:
                self.assertEqual(v["vote"], "no-lynch")
                self.assertEqual(v["delay_cause"], "low_confidence")
                self.assertFalse(v["parse_fail"])
                self.assertEqual(v["gate_confidence"], 0.1)
            else:
                self.assertIsNone(v["gate_confidence"])
        self.assertFalse(model.of("vote", pids=village))  # held seats make no vote call
        self.assertTrue(model.of("vote", pids=mafia))

        def broken(system, user, meta):
            meta["parse_fail"] = True
            return {}

        game2 = _play("gated_village_v3", _Model(verify=broken))
        for v in game2._vote_rows:
            if v["is_village"]:
                self.assertEqual((v["vote"], v["delay_cause"], v["parse_fail"]),
                                 ("no-lynch", "json_failure", True))
                self.assertIsNone(v["gate_confidence"])

    def test_baseline_arm_has_no_gate_fields_set(self):
        model = _Model()
        game = _play("cot_village_v3", model)
        self.assertFalse(model.of("tpn_reason"))
        self.assertFalse(model.of("dmn_reason"))
        for v in game._vote_rows:
            self.assertIsNone(v["gate_confidence"])
            self.assertIsNone(v["delay_cause"])

    def test_vote_prompt_is_byte_identical_between_v3_arms(self):
        from src.mafia import prompts as P
        from src.mafia import prompts_v3 as P3

        runs = {arm: _Model(confidence=0.9) for arm in V3_PAIR}
        games = {arm: _play(arm, m, max_days=3) for arm, m in runs.items()}
        votes = {arm: [(c["pid"], c["system"].encode(), c["user"].encode(), c["temperature"])
                       for c in m.of("vote")] for arm, m in runs.items()}
        self.assertGreaterEqual(len(votes["cot_village_v3"]), 6)
        self.assertEqual(votes["gated_village_v3"], votes["cot_village_v3"])
        # and it is the neutral prompt, for village and mafia seats alike
        g = games["cot_village_v3"]
        for c in runs["cot_village_v3"].of("vote"):
            self.assertEqual(c["system"], P.VOTE_SYSTEM)
            hist = _history_block(c["user"])
            self.assertEqual(
                c["user"], P3.vote_neutral_user(c["pid"], g.players[c["pid"]].role, hist))
            self.assertNotIn("endless delay", c["user"])
        self.assertEqual(games["gated_village_v3"].history, g.history)

    def test_mafia_seats_get_identical_prompts_until_play_diverges(self):
        def trail(model, pids):
            return {pid: [(c["kind"], c["system"], c["user"], c["temperature"], c["purpose"])
                          for c in model.of(pids={pid})] for pid in pids}

        # (a) verifier confident on every seat-day: play never diverges, so
        # every mafia-seat call of the whole game is identical.
        runs = {arm: _Model(confidence=0.9) for arm in V3_PAIR}
        games = {arm: _play(arm, m, max_days=3) for arm, m in runs.items()}
        mafia, _ = _roles(games["cot_village_v3"])
        self.assertEqual(_roles(games["gated_village_v3"])[0], mafia)
        a = trail(runs["gated_village_v3"], mafia)
        b = trail(runs["cot_village_v3"], mafia)
        self.assertEqual(a, b)
        self.assertTrue(all(len(v) >= 3 for v in b.values()))
        self.assertFalse([c for c in runs["gated_village_v3"].of("tpn_reason")
                          if c["pid"] in mafia])

        # (b) verifier never confident: the village holds on day 0, which is
        # the first divergence. Up to and including each mafia seat's day-0
        # vote call, its prompts are identical.
        low = _Model(confidence=0.0)
        g_low = _play("gated_village_v3", low, max_days=3)
        c = trail(low, mafia)
        for pid in mafia:
            first_vote = next(i for i, x in enumerate(b[pid]) if x[4] == "vote")
            self.assertEqual(c[pid][:first_vote + 1], b[pid][:first_vote + 1], pid)
        self.assertNotEqual(g_low.history, games["cot_village_v3"].history)

    def test_nolynch_reference_arm_makes_no_village_calls(self):
        from src.agents.null_agents import NoLynchAgent

        with patch("src.llm_client.chat_json", side_effect=AssertionError("llm called")), \
                patch("src.llm_client.chat_text", side_effect=AssertionError("llm called")):
            ag = NoLynchAgent(pid=1)
            self.assertEqual(ag.speak("villager", "h"), "I am watching and waiting for evidence.")
            for prev in (None, "3"):
                v, info = ag.vote("villager", "h", {}, prev_majority=prev, seed=3, day=1,
                                  alive=[0, 1, 3])
                self.assertEqual(v, "no-lynch")
                self.assertEqual(info["null_kind"], "nolynch")
                self.assertFalse(info["parse_fail"])
                self.assertIsNone(info["delay_cause"])
            self.assertEqual(ag.night_action("doctor", "h", [0, 1], [0, 1], "save"), "1")
            self.assertEqual(ag.night_action("detective", "h", [0, 1, 2], [0, 2], "check"), "0")
            self.assertEqual(ag.elicit_trust_probe("villager", "h", [0, 1])[0], {})

        model = _Model()
        game = _play("nolynch_village_v3", model, max_days=3)
        mafia, village = _roles(game)
        self.assertTrue(model.calls)
        self.assertEqual({c["pid"] for c in model.calls} - mafia, set())
        self.assertFalse(model.of("probe"))
        self.assertFalse(game._trust_rows)
        for v in game._vote_rows:
            if v["is_village"]:
                self.assertEqual(v["vote"], "no-lynch")
            self.assertIsNone(v["lynched"])


class TestV3ArmGates(_RunEnv):
    def _conf_args(self, arms):
        from tests.test_manifest_assertions import _args

        return _args(arms=arms)

    def test_confirmatory_gate_refuses_v3_arms(self):
        from src.eval import run_arena
        from tests.test_manifest_assertions import _frozen

        with _frozen(run_arena):
            run_arena._assert_confirmatory(
                self._conf_args("dmn_village,cot_village,cotx3_village"))  # control: passes
            for arm in ("gated_village_v3", "cot_village_v3", "nolynch_village_v3"):
                for arms in (arm, f"dmn_village,cot_village,cotx3_village,{arm}"):
                    with self.assertRaises(SystemExit) as cm:
                        run_arena._assert_confirmatory(self._conf_args(arms))
                    self.assertIn("exploratory stress-test arms", str(cm.exception), arms)
                    self.assertIn(arm, str(cm.exception), arms)

    def test_confirmatory_flag_refuses_v3_arms_through_main(self):
        with self.assertRaises(SystemExit) as cm:
            self._run(["--design", "team", "--arms", "gated_village_v3,cot_village_v3",
                       "--seed", "100000", "--workers", "1", "--tau", "0.35",
                       "--campaign", "explore-mafia-v3", "--run-tag", "r", "--out", self.out,
                       "--confirmatory"])
        self.assertIn("exploratory stress-test arms", str(cm.exception))
        self.assertEqual(self.calls, [])

    def _v3(self, campaign, seed, arms="gated_village_v3,cot_village_v3,nolynch_village_v3",
            **over):
        args = ["--design", "team", "--arms", arms, "--seed", str(seed), "--workers", "1",
                "--tau", "0.35", "--run-tag", "r", "--out", self.out, "--trios", "1"]
        if campaign is not None:
            args += ["--campaign", campaign]
        for k, v in over.items():
            args += [f"--{k.replace('_', '-')}", str(v)]
        return args

    def test_v3_arms_need_an_exploratory_campaign_prefix(self):
        for campaign in ("mvp-team-02", "ops-A-01", "mafia-v3", "xexplore-1", None):
            with self.assertRaises(SystemExit) as cm:
                self._run(self._v3(campaign, 100000))
            self.assertIn("explore-", str(cm.exception), campaign)
        for arm in ("gated_village_v3", "cot_village_v3", "nolynch_village_v3"):
            with self.assertRaises(SystemExit):
                self._run(self._v3("mvp-team-02", 100000, arms=arm))
        self.assertEqual(self.calls, [])

    def test_v3_arms_need_seeds_at_or_above_100000(self):
        for seed in (0, 5000, 99999):
            with self.assertRaises(SystemExit) as cm:
                self._run(self._v3("explore-mafia-v3", seed))
            self.assertIn("100000", str(cm.exception), seed)
        self.assertEqual(self.calls, [])

    def test_v3_arms_run_with_prefix_and_high_seed(self):
        for i, campaign in enumerate(("explore-mafia-v3", "pilot-mafia-v3", "smoke-mafia-v3")):
            self.calls.clear()
            self._run(self._v3(campaign, 100000 + 1000 * i))
            self.assertEqual(len(self.calls), 3, campaign)
            self.assertTrue(all(c.startswith(campaign) for c in self.calls))

    def test_old_arms_are_not_affected_by_the_v3_rule(self):
        self._run(self._base("camp", "r", trios=1), runner=_team_row)
        self.assertEqual(len(self.calls), 3)

    def test_nolynch_arm_is_not_counted_as_probed(self):
        from src.eval import run_arena

        rows = [{"arm": a} for a in ("gated_village_v3", "cot_village_v3",
                                     "nolynch_village_v3", "random_village")]
        self.assertEqual(run_arena._probed_games(rows), 2)


def _vrow(game, day, voter, vote, is_village, target_is_mafia, lynched, arm="gated_village_v3",
          seed=100000):
    return {"game_id": game, "requested_seed": seed, "arm": arm, "day": day, "voter": voter,
            "vote": str(vote), "is_village": is_village,
            "vote_target_is_mafia": target_is_mafia,
            "lynched": lynched, "lynched_is_mafia": None if lynched is None else (lynched == "3"),
            "majority_vote": "x", "majority_correct": False, "parse_fail": False}


def _day(game, day, village, mafia, lynched, **kw):
    """village/mafia: lists of vote targets. Players 3 and 6 are mafia."""
    rows = []
    for i, v in enumerate(village):
        tim = None if v == "no-lynch" else (str(v) in ("3", "6"))
        rows.append(_vrow(game, day, i, v, True, tim, lynched, **kw))
    for j, v in enumerate(mafia):
        tim = None if v == "no-lynch" else (str(v) in ("3", "6"))
        rows.append(_vrow(game, day, 100 + j, v, False, tim, lynched, **kw))
    return rows


class TestMissedCorrectLynches(unittest.TestCase):
    def _table(self):
        rows = []
        # Game A.
        # day 0: village plurality on mafia 3 (2 of 5); mafia voters pile on
        # innocent 5, so the all-voter plurality is 5. No lynch -> MISSED.
        rows += _day("A", 0, ["3", "3", "5", "no-lynch", "no-lynch"], ["5", "5"], None)
        # day 1: village plurality on mafia 3 and the lynch happens -> not missed.
        rows += _day("A", 1, ["3", "3", "3", "5"], ["5", "3"], "3")
        # day 2: village plurality on innocent 5, no lynch -> not missed.
        rows += _day("A", 2, ["5", "5", "3", "no-lynch"], ["5"], None)
        # day 3: village tied between mafia 3 and innocent 5 -> no plurality target.
        rows += _day("A", 3, ["3", "5", "no-lynch"], ["no-lynch"], None)
        # day 4: village plurality on mafia 6 only through village votes;
        # mafia votes for 6 are ignored, village has 1 for 6 and 1 for 5 -> tie.
        rows += _day("A", 4, ["6", "5"], ["6"], None)
        # Game B (always no-lynch village): nothing to miss, row still present.
        rows += _day("B", 0, ["no-lynch"] * 5, ["1", "1"], None, arm="nolynch_village_v3")
        rows += _day("B", 1, ["no-lynch"] * 4, ["1", "1"], None, arm="nolynch_village_v3")
        # Game C: two missed days, one of them with every mafia voter abstaining.
        rows += _day("C", 0, ["6", "6", "6", "1", "no-lynch"], ["1", "1"], None,
                     arm="cot_village_v3")
        rows += _day("C", 1, ["3", "no-lynch", "no-lynch", "no-lynch"], ["no-lynch"], None,
                     arm="cot_village_v3")
        return pd.DataFrame(rows)

    def test_hand_built_table(self):
        from src.eval.action_boundary import missed_correct_lynches_per_game

        out = missed_correct_lynches_per_game(self._table()).set_index("game_id")
        self.assertEqual(sorted(out.index), ["A", "B", "C"])
        self.assertEqual(int(out.loc["A", "missed_correct_lynches"]), 1)
        self.assertEqual(int(out.loc["B", "missed_correct_lynches"]), 0)
        self.assertEqual(int(out.loc["C", "missed_correct_lynches"]), 2)
        self.assertEqual(int(out.loc["A", "days"]), 5)
        self.assertEqual(out.loc["C", "arm"], "cot_village_v3")
        self.assertEqual(int(out.loc["A", "requested_seed"]), 100000)

    def test_a_lynch_of_someone_else_is_not_a_missed_day(self):
        from src.eval.action_boundary import missed_correct_lynches_per_game

        # village plurality on mafia 3, but mafia votes carry a lynch of 5
        rows = _day("D", 0, ["3", "3", "5", "5"], ["5", "5"], "5")
        out = missed_correct_lynches_per_game(pd.DataFrame(rows))
        self.assertEqual(int(out.loc[0, "missed_correct_lynches"]), 0)

    def test_available_through_per_game_metric_and_existing_metrics_unchanged(self):
        from src.eval import action_boundary as ab

        t = self._table()
        got = ab.per_game_metric(t, "missed_correct_lynches")
        self.assertEqual(got["missed_correct_lynches"].sum(), 3)
        w = ab.wrongful_lynches_per_game(t).set_index("game_id")
        self.assertEqual(int(w.loc["A", "wrongful_lynches"]), 0)
        self.assertEqual(list(ab.needless_hold_rate_per_game(t).columns),
                         ["game_id", "requested_seed", "arm", "target_days",
                          "needless_days", "needless_hold_rate"])

    def test_parquet_round_trip_types(self):
        from src.eval.action_boundary import missed_correct_lynches_per_game

        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "v.parquet")
            self._table().to_parquet(p, index=False)
            out = missed_correct_lynches_per_game(pd.read_parquet(p)).set_index("game_id")
        self.assertEqual([int(out.loc[g, "missed_correct_lynches"]) for g in "ABC"], [1, 0, 2])


if __name__ == "__main__":
    unittest.main()
