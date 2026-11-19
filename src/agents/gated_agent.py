"""Repaired minimal gate for the Mafia stress test (pre-reg v3 SS12.5).

GatedCotAgent = the neutral-prompt CoT baseline plus ONE verification call
at the action boundary. The call is made inside vote(), so it reads the
same post-discussion, pre-vote snapshot the baseline vote reads. There is
no reason() step: nothing runs before the day's discussion, and speech is
the plain CoT speech.

Hold rule: unparseable verification -> "no-lynch" (json_failure);
confidence < settings.tau_delay -> "no-lynch" (low_confidence); otherwise
the baseline's vote call is made unchanged (same prompt, same temperature).
"""
import math

from src import llm_client as llm
from src.config import settings
from src.mafia import prompts_v3 as P3
from .baselines import CotNeutralAgent


def _parse_verification(d, meta, allowed):
    """Return (suspect, evidence_turns, confidence) or None if unusable.

    Unusable: the client reported a parse failure, the reply is not an
    object, the suspect is missing or not an alive non-self player, or the
    confidence is not a finite number in [0, 1].
    """
    if bool((meta or {}).get("parse_fail")) or not isinstance(d, dict):
        return None
    suspect = d.get("suspect")
    conf = d.get("confidence")
    if suspect is None or conf is None or isinstance(conf, bool):
        return None
    suspect = str(suspect).strip()
    if suspect.upper().startswith("P"):
        suspect = suspect[1:]
    if allowed is not None and suspect not in allowed:
        return None
    try:
        conf = float(conf)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(conf) or conf < 0.0 or conf > 1.0:
        return None
    turns = []
    raw_turns = d.get("evidence_turns")
    for t in raw_turns if isinstance(raw_turns, (list, tuple)) else []:
        try:
            turns.append(int(str(t).strip().lstrip("tT")))
        except (TypeError, ValueError):
            continue
    return suspect, turns, conf


class GatedCotAgent(CotNeutralAgent):
    name = "gated_cot"

    def vote(self, role, history, trust, prev_majority=None, seed=None, day=None, alive=None):
        others = [str(a) for a in (alive or []) if str(a) != str(self.pid)]
        meta = {}
        d = llm.chat_json(P3.GATE_VERIFY_SYSTEM,
                          P3.gate_verify_user(self.pid, role, history, others),
                          meta=meta, temperature=0.0, purpose="tpn_reason")
        parsed = _parse_verification(d, meta, set(others) if alive is not None else None)
        gate = {"gate_tau": settings.tau_delay, "gate_suspect": None,
                "gate_evidence_turns": [], "gate_confidence": None}
        if parsed is None:
            return "no-lynch", {"reason": "", "commitment": "", "parse_fail": True,
                                "delay_cause": "json_failure", **gate}
        suspect, turns, conf = parsed
        gate.update({"gate_suspect": suspect, "gate_evidence_turns": turns,
                     "gate_confidence": conf})
        if conf < settings.tau_delay:
            return "no-lynch", {"reason": "no suspect verified with enough confidence",
                                "commitment": "", "parse_fail": False,
                                "delay_cause": "low_confidence", **gate}
        v, info = super().vote(role, history, trust, prev_majority=prev_majority,
                               seed=seed, day=day, alive=alive)
        info.update(gate)
        return v, info
