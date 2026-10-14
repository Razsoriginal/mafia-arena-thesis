"""Deterministic Mafia engine. No LLM inside — agents inject utterances/votes."""
import random
from .models import Player

ROLES_7 = ["mafia", "mafia", "doctor", "detective", "villager", "villager", "villager"]

class Game:
    def __init__(self, seed=0, roles=None):
        self.rng = random.Random(seed)
        self.seed = seed
        roles = roles or ROLES_7[:]
        self.rng.shuffle(roles)
        self.players = [Player(pid=i, role=r) for i, r in enumerate(roles)]
        self.day = 0
        self.history = []  # list of dicts {turn, speaker, text, phase}
        self.turn = 0
        self.over = False
        self.winner = None

    def alive(self):
        return [p for p in self.players if p.alive]

    def alive_ids(self):
        return [p.pid for p in self.alive()]

    def add(self, speaker, text, phase):
        self.history.append({"turn": self.turn, "speaker": speaker, "text": text, "phase": phase})
        self.turn += 1

    def history_text(self, viewer=None, limit=60):
        lines = []
        for h in self.history[-limit:]:
            lines.append(f"[t{h['turn']} {h['phase']} P{h['speaker']}]: {h['text']}")
        return "\n".join(lines)

    def facts_text(self):
        # observable facts for TPN: votes + kills + claims (all history is observable in MVP)
        return self.history_text(limit=80)

    def night(self, mafia_kill, doctor_save, detective_check):
        # mafia_kill: pid, doctor_save: pid, detective_check: pid
        killed = None
        if mafia_kill is not None and mafia_kill != doctor_save:
            for p in self.players:
                if p.pid == mafia_kill and p.alive:
                    p.alive = False
                    killed = mafia_kill
        det_role = None
        if detective_check is not None:
            for p in self.players:
                if p.pid == detective_check:
                    det_role = p.role
        # private info returned; public death announced
        return {"killed": killed, "detective_info": (detective_check, det_role)}

    def vote(self, votes: dict):
        # votes: voter_pid -> target ("no-lynch" or pid)
        from collections import Counter
        c = Counter([v for v in votes.values() if v != "no-lynch"])
        if not c:
            return None
        top, cnt = c.most_common(1)[0]
        # majority of alive needed
        if cnt > len(self.alive()) / 2:
            for p in self.players:
                if str(p.pid) == str(top) and p.alive:
                    p.alive = False
                    return p.pid
            # numeric compare
            for p in self.players:
                if p.pid == int(top) and p.alive:
                    p.alive = False
                    return p.pid
        return None

    def check_over(self):
        mafia = sum(1 for p in self.alive() if p.role == "mafia")
        others = sum(1 for p in self.alive() if p.role != "mafia")
        if mafia == 0:
            self.over, self.winner = True, "village"
        elif mafia >= others:
            self.over, self.winner = True, "mafia"
        return self.over
