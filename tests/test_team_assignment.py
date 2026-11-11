import unittest


class TestTeamAssignment(unittest.TestCase):
    def test_same_seed_same_role_map(self):
        from src.mafia.engine import Game

        a = [(p.pid, p.role) for p in Game(seed=5000).players]
        b = [(p.pid, p.role) for p in Game(seed=5000).players]
        self.assertEqual(a, b)

    def test_team_agents_mafia_always_cot(self):
        from src.agents.baselines import CotAgent, CotX3Agent
        from src.agents.dmn_tpn_agent import DmnTpnAgent
        from src.eval.run_arena import _build_agents
        from src.mafia.engine import Game

        game = Game(seed=5000)
        for arm, village_cls in [("dmn_village", DmnTpnAgent), ("cot_village", CotAgent), ("cotx3_village", CotX3Agent)]:
            agents = _build_agents(game, focal_pid=0, design="team", arm=arm, gate="llm")
            self.assertEqual(len(agents), 7)
            for p in game.players:
                if p.role == "mafia":
                    self.assertIsInstance(agents[p.pid], CotAgent, arm)
                    self.assertNotIsInstance(agents[p.pid], DmnTpnAgent, arm)
                else:
                    self.assertIsInstance(agents[p.pid], village_cls, arm)

    def test_null_team_agents(self):
        from src.agents.baselines import CotAgent
        from src.agents.null_agents import MajorityFollowerAgent, RandomVoterAgent
        from src.eval.run_arena import _build_agents
        from src.mafia.engine import Game

        game = Game(seed=5001)
        agents = _build_agents(game, focal_pid=0, design="team", arm="random_village")
        for p in game.players:
            self.assertIsInstance(agents[p.pid], RandomVoterAgent if p.role != "mafia" else CotAgent)
        agents2 = _build_agents(game, focal_pid=0, design="team", arm="majority_village")
        for p in game.players:
            self.assertIsInstance(agents2[p.pid], MajorityFollowerAgent if p.role != "mafia" else CotAgent)

    def test_focal_assignment_unchanged(self):
        from src.agents.baselines import CotAgent
        from src.agents.dmn_tpn_agent import DmnTpnAgent
        from src.eval.run_arena import _build_agents
        from src.mafia.engine import Game

        game = Game(seed=5000)
        agents = _build_agents(game, focal_pid=3, focal="dmn_tpn", design="focal")
        self.assertIsInstance(agents[3], DmnTpnAgent)
        for pid, ag in agents.items():
            if pid != 3:
                self.assertIsInstance(ag, CotAgent)

    def test_play_one_uses_requested_seed_for_every_arm(self):
        # Through play_one (F46): same requested seed, same role map,
        # arm recorded on the game and on every row.
        import tempfile
        from unittest.mock import patch

        from src import llm_client
        from src.eval import run_arena
        from src.eval.run_arena import play_one

        def fake_text(system, user, temperature=None, log=True, response_format=None, **kw):
            return "I am watching the discussion."

        def fake_json(system, user, meta=None, temperature=None, **kw):
            if meta is not None:
                meta.update({"parse_fail": False})
            if "imaginative mind" in system:
                return {"hypotheses": [{"suspect": "1", "motive": "quiet", "confidence": 0.8}]}
            if "verifier mind" in system:
                return {"verified": [{"suspect": "1", "evidence_spans": [0],
                                      "contradiction_found": False, "revised_confidence": 0.8}]}
            if "Output trust scores" in system:
                return {"trust": {str(i): 0.6 for i in range(7)}}
            if "night" in system.lower() or "You choose a night action" in system:
                return {"kill": "0", "save": "0", "check": "1"}
            if "must justify" in system:
                return {"vote": "1", "reason": "t0 shows a claim"}
            return {"vote": "1", "reason": "suspect"}

        role_maps = {}
        for arm in ("dmn_village", "cot_village", "cotx3_village"):
            with tempfile.TemporaryDirectory() as td, patch.object(
                llm_client, "chat_text", side_effect=fake_text
            ), patch.object(llm_client, "chat_json", side_effect=fake_json), patch.object(
                run_arena, "_log_progress", lambda *a, **k: None
            ):
                game = play_one(seed=5000, design="team", arm=arm,
                                run_id=f"5000-{arm}", requested_seed=5000,
                                max_days=1, run_dir=td, run_tag="mock")
            self.assertEqual(game.seed, 5000)
            self.assertEqual(game._arm, arm)
            self.assertTrue(all(v["arm"] == arm for v in game._vote_rows))
            role_maps[arm] = [(p.pid, p.role) for p in game.players]
        self.assertEqual(role_maps["dmn_village"], role_maps["cot_village"])
        self.assertEqual(role_maps["dmn_village"], role_maps["cotx3_village"])

    def test_seed_major_task_order(self):
        from src.eval.run_arena import build_tasks

        class A:  # minimal args stub
            design = "team"
            arms = "dmn_village,cot_village,cotx3_village"
            games = 2
            seed = 5000
            gate = "llm"
            night = "llm"
            max_days = 5
            tau_sweep = None

        tasks = build_tasks(A(), run_tag="t", run_dir="logs/runs/t", git_sha="abc")
        self.assertEqual([t["requested_seed"] for t in tasks], [5000, 5000, 5000, 5100, 5100, 5100])
        self.assertEqual([t["arm"] for t in tasks[:3]], ["dmn_village", "cot_village", "cotx3_village"])
        self.assertTrue(all(t["design"] == "team" for t in tasks))
        self.assertTrue(all(t["focal_role"] == "random" for t in tasks))


if __name__ == "__main__":
    unittest.main()
