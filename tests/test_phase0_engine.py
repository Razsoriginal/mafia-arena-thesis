"""Phase 0 engine/agent fixes found in the 2026-11-12 review.

E1: a night kill that reaches parity ends the game before the day.
E2: DMN prior/threat use public information only (alive count), never the
    hidden number of living mafia.
E3: the detective's private note keeps every past check, not only the last.
"""
import tempfile
import unittest
from unittest.mock import patch

from src import llm_client
from tests.test_row_integrity import _fake_chat_json, _fake_chat_text


class TestParityAfterNightE1(unittest.TestCase):
    def test_parity_night_kill_ends_game_before_day(self):
        from src.eval import run_arena
        from src.mafia.engine import Game

        g = Game(seed=5000)
        others = [p.pid for p in g.players if p.role != "mafia"]
        for pid in others[:2]:
            g.players[pid].alive = False  # 2 mafia vs 3 others alive
        target = others[2]
        speaks = []

        def _speak(system, user, **kw):
            speaks.append(1)
            return "line"

        with patch.object(run_arena, "_make_game", lambda seed, focal_role="random": (g, seed, 0)), \
                patch.object(run_arena, "_night_actions", lambda *a, **k: (target, None, None)), \
                patch.object(llm_client, "chat_text", side_effect=_speak), \
                patch.object(llm_client, "chat_json", side_effect=_fake_chat_json), \
                patch.object(run_arena, "_log_progress", lambda *a, **k: None):
            out = run_arena.play_one(5000, design="team", arm="cot_village",
                                     run_dir=tempfile.mkdtemp(), max_days=5)
        self.assertEqual(out.winner, "mafia")
        self.assertEqual(speaks, [], "no day discussion after a parity night kill")
        self.assertFalse(any(str(h["phase"]).startswith("day-") for h in out.history))
        self.assertEqual(out._vote_rows, [])


class TestPublicInfoPriorE2(unittest.TestCase):
    def _reason(self, alive_roles):
        from src.agents.dmn_tpn_agent import DmnTpnAgent

        ag = DmnTpnAgent(pid=3)
        alive = sorted(alive_roles)
        with patch.object(llm_client, "chat_json", side_effect=_fake_chat_json):
            trust, trace, _ = ag.reason("villager", "h", "f", alive, None, alive_roles)
        return trust, trace

    def test_hidden_mafia_count_does_not_change_prior_or_threat(self):
        both = {0: "mafia", 1: "mafia", 3: "villager", 4: "doctor", 5: "villager"}
        one = {0: "mafia", 1: "villager", 3: "villager", 4: "doctor", 5: "villager"}
        t_both, tr_both = self._reason(both)
        t_one, tr_one = self._reason(one)
        self.assertEqual(tr_both["prior_innocent"], tr_one["prior_innocent"])
        self.assertEqual(tr_both["threat"], tr_one["threat"])
        self.assertEqual(t_both, t_one)

    def test_public_estimate_values(self):
        # 5 alive, game not over => at most 2 mafia alive (public bound)
        _, tr = self._reason({0: "mafia", 1: "villager", 3: "villager", 4: "doctor", 5: "villager"})
        self.assertAlmostEqual(tr["prior_innocent"], round(3 / 5, 3))
        self.assertAlmostEqual(tr["threat"], round(2 / 3, 6), places=5)
        # 4 alive, game not over => at most 1 mafia alive
        _, tr4 = self._reason({0: "mafia", 3: "villager", 4: "doctor", 5: "villager"})
        self.assertAlmostEqual(tr4["prior_innocent"], round(3 / 4, 3))
        self.assertAlmostEqual(tr4["threat"], round(1 / 3, 6), places=5)


class TestDetectiveMemoryE3(unittest.TestCase):
    def test_private_note_lists_all_checks(self):
        from src.eval import run_arena
        from src.mafia.engine import Game

        g = Game(seed=5000)
        det = [p.pid for p in g.players if p.role == "detective"][0]
        det_info = {}
        run_arena._record_detective_result(det_info, det, (1, "villager"))
        run_arena._record_detective_result(det_info, det, (2, "mafia"))
        note = run_arena._private_note(g, det, det_info)
        self.assertIn("Player 1 is villager", note)
        self.assertIn("Player 2 is mafia", note)


if __name__ == "__main__":
    unittest.main()
