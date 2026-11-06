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
