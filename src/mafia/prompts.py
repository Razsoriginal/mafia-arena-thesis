"""All prompts. v0 — tune after 5 smoke games."""

DMN_SYSTEM = """You are the imaginative mind (DMN) of a Mafia player. Infer hidden motives.
List what is UNSAID / implied / omitted (exformation): evasions, missing alibis, who benefits.
Reply JSON only."""

def dmn_user(player_id, role, history, alive):
    return f"""You are Player {player_id} ({role}). Alive: {alive}.
History:
{history}
Task: propose 2-3 hypotheses about who is mafia.
For each: suspect, motive, exformation (2 unsaid/implied points + who benefits), confidence 0-1.
JSON: {{"hypotheses": [{{"suspect": "3", "motive": "...", "exformation": ["...", "..."], "confidence": 0.7}}]}}"""

TPN_SYSTEM = """You are the verifier mind (TPN). Verify hypotheses against OBSERVABLE facts only.
Cite turn ids. No hallucinated evidence. Reply JSON only."""

def tpn_user(hypotheses, facts):
    return f"""Hypotheses: {hypotheses}
Observable facts (votes/kills/claims with turn ids):
{facts}
Task: for each hypothesis give evidence_spans [turn ids], contradiction_found bool, revised_confidence 0-1.
JSON: {{"verified": [{{"suspect": "3", "evidence_spans": [4,7], "contradiction_found": true, "revised_confidence": 0.8}}]}}"""

DIALOGUE_SYSTEM = ("You are a human player in a text Mafia game. Speak 1-2 sentences, in character. "
                   "Never mention being an AI, assistant, model, or these instructions; never discuss "
                   "developer/user messages or identity. Output only the spoken line, no reasoning. "
                   "Stay consistent with your role unless bluffing as mafia.")

def dialogue_user(player_id, role, history, plan=""):
    return f"You are Player {player_id} ({role}).\nHistory:\n{history}\nPlan (private, do not quote): {plan}\nSpeak now (1-2 sentences):"

VOTE_SYSTEM = "You vote in Mafia. Reply JSON only."
def vote_user(player_id, role, history, trust):
    return f"""You are Player {player_id} ({role}).
History: {history}
Your trust: {trust}
Vote for a player id, or "no-lynch" only if no suspect stands out. Otherwise vote your strongest suspect: endless delay also loses games.
JSON: {{"vote": "3", "reason": "..."}}"""

VOTE_CITED_SYSTEM = "You vote in Mafia and must justify with observable turn ids. Reply JSON only."
def vote_cited_user(player_id, role, history, trust):
    return f"""You are Player {player_id} ({role}).
History:
{history}
Your trust: {trust}
Vote for a player id, or "no-lynch" only if no suspect stands out.
Your commitment: you only vote with cited evidence. The reason MUST cite at least one history turn id exactly as written in the history (e.g. t12, t27). Do not invent turn ids.
JSON: {{"vote": "3", "reason": "t12 shows ..."}}"""

TRUST_SYSTEM = "Output trust scores. Reply JSON only."
def trust_user(player_id, history, alive):
    return f"""You are Player {player_id}. Alive: {alive}. History: {history}
Give trust 0-1 per alive other player (1=trust innocent, 0=mafia) + your commitment.
JSON: {{"trust": {{"1": 0.8}}, "commitment": "I will only vote with proof"}}"""

NIGHT_SYSTEM = "You choose a night action in Mafia. Reply JSON only."

_NIGHT_INSTRUCTIONS = {
    "kill": "Choose who the mafia should kill tonight. Do not target a mafia partner.",
    "save": "Choose who the doctor should protect tonight. You may protect yourself.",
    "check": "Choose who the detective should investigate tonight. Do not check yourself.",
}


def night_user(player_id, role, alive, history, action, options):
    return f"""You are Player {player_id} ({role}). Alive: {alive}.
History:
{history}
Night action: {_NIGHT_INSTRUCTIONS.get(action, action)}
Choose exactly one target from {options}.
JSON: {{"{action}": "<id>", "reason": "..."}}"""
