from dataclasses import dataclass, field

@dataclass
class Player:
    pid: int
    role: str  # mafia | doctor | detective | villager
    alive: bool = True

@dataclass
class Action:
    utterance: str = ""
    vote: str = "no-lynch"  # pid as str or "no-lynch"
    trust: dict = field(default_factory=dict)  # pid -> 0..1
    commitment: str = ""
    trace: dict = field(default_factory=dict)  # DMN/TPN/EVT debug
