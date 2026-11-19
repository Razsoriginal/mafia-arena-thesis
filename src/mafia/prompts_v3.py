"""Prompts for the exploratory Mafia stress test (pre-reg v3 SS12.5).

Kept out of prompts.py on purpose: that file's sha256 is the freeze-v2
prompt identity recorded in old manifests and in docs/PREREGISTRATION.md,
so it must stay byte-identical. This module is inside the run-path hash
(src/mafia is walked recursively).

Both stress-test arms vote with `vote_neutral_user`: no "endless delay
also loses games" pressure and no citation commitment, so the only
difference between the arms is the verification call that precedes the
vote in the gated arm.
"""
from .prompts import VOTE_SYSTEM  # noqa: F401  (same system line as the baseline)


def vote_neutral_user(player_id, role, history):
    return f"""You are Player {player_id} ({role}).
History:
{history}
Vote for one alive player id, or "no-lynch".
JSON: {{"vote": "3", "reason": "..."}}"""


GATE_VERIFY_SYSTEM = ("You check the evidence before a lynch vote in Mafia. A lynch cannot be undone. "
                      "Use only what is written in the history. Reply JSON only.")


def gate_verify_user(player_id, role, history, others):
    return f"""You are Player {player_id} ({role}). Alive others: {others}.
History:
{history}
Task: name the single most suspicious player among the alive others, the history turn ids that are your evidence (numbers only, e.g. 12 for t12; an empty list if there is none), and your confidence from 0 to 1 that this player is mafia.
JSON: {{"suspect": "3", "evidence_turns": [12, 27], "confidence": 0.5}}"""
