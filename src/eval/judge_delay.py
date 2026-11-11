"""Blinded delay judge sample (Part A A6).

Builds a blinded sample of game-days from locked arena outputs.
The judge sees history truncated before the vote. It never sees
arm, outcome, roles, actual votes, or plurality correctness.

Human judge is primary. An LLM fallback must use a different
model family from the backbone; validate_judge_model enforces it.

Usage:
  python -m src.eval.judge_delay --votes logs/votes.parquet \
      --histories logs/runs/<tag>/raw --out judge_sample.jsonl
This module makes no LLM calls itself.
"""
import argparse
import json
import os
import random

import pandas as pd

from src.config import settings


def truncate_before_vote(history, day=None):
    """History up to (not including) the sampled day's vote (F14).

    With day=None the old first-vote behaviour is kept for callers that
    only have day-0 histories. With a day, earlier days' votes/results
    stay visible (they happened before) and truncation stops at that
    day's vote/result.
    """
    out = []
    for h in history:
        phase = str(h.get("phase", ""))
        if day is None:
            if phase.startswith("vote-") or phase.startswith("result-"):
                break
        else:
            if phase in (f"vote-{day}", f"result-{day}"):
                break
        out.append({"turn": h.get("turn"), "speaker": h.get("speaker"),
                    "text": h.get("text"), "phase": phase})
    return out


def _was_lynched(grp) -> bool:
    """True when the plurality target was actually lynched (F15).

    The engine lynches only on a strict majority of alive voters, so a
    plurality without a majority is not a lynch.
    """
    majority = str(grp["majority_vote"].iloc[0])
    if majority == "no-lynch" or len(grp) == 0:
        return False
    n_for = int((grp["vote"].astype(str) == majority).sum())
    return n_for > len(grp) / 2


def _anonymise(history):
    return [{"turn": h["turn"], "speaker": f"P{h['speaker']}" if str(h["speaker"]).isdigit() else "engine",
             "text": h["text"], "phase": h["phase"]} for h in history]


def build_sample(votes_df, histories, n_delay=60, n_lynch=60, seed=20261106):
    """histories: list of {game_id, history:[...]}. Returns blinded dicts."""
    hist_by_game = {h["game_id"]: h["history"] for h in histories}
    keys = [c for c in ("campaign", "run_tag", "game_id", "day") if c in votes_df.columns]
    delay_days, lynch_days = [], []
    for key, grp in votes_df.groupby(keys):
        gid = str(grp["game_id"].iloc[0])
        day = int(grp["day"].iloc[0])
        village = grp[grp["is_village"].astype(bool)] if "is_village" in grp.columns else grp
        is_delay = bool((village["vote"].astype(str) == "no-lynch").any())
        majority = str(grp["majority_vote"].iloc[0])
        item = {"game_id": str(gid), "day": int(day)}
        if is_delay and majority != "no-lynch":
            cause = village["delay_cause"].fillna("").astype(str) if "delay_cause" in village.columns else ""
            if not (cause == "json_failure").all():
                delay_days.append(item)
                continue
        if _was_lynched(grp):
            lynch_days.append(item)
    rng = random.Random(seed)
    rng.shuffle(delay_days)
    rng.shuffle(lynch_days)
    if n_delay >= 30 and "arm" in votes_df.columns:
        by_arm = {}
        arm_by_day = {}
        for key, grp in votes_df.groupby(keys):
            arm_by_day[(str(grp["game_id"].iloc[0]), int(grp["day"].iloc[0]))] = str(grp["arm"].iloc[0])
        for item in delay_days:
            by_arm.setdefault(arm_by_day.get((item["game_id"], item["day"]), "?"), []).append(item)
        arms = sorted(by_arm)
        quota = max(1, n_delay // max(1, len(arms)))
        chosen_delay = []
        for a in arms:
            chosen_delay.extend(by_arm[a][:quota])
        chosen_delay = chosen_delay[:n_delay]
    else:
        chosen_delay = delay_days[:n_delay]
    chosen = chosen_delay + lynch_days[:n_lynch]
    rng.shuffle(chosen)
    sample = []
    for i, item in enumerate(chosen):
        hist = hist_by_game.get(item["game_id"])
        if not hist:
            continue
        truncated = _anonymise(truncate_before_vote(hist, day=item["day"]))
        if not truncated:
            continue
        sample.append({"blind_id": f"blind-{i:03d}", "history": truncated,
                       "judge_top_suspect": None, "evidence_sufficient": None,
                       "delay_recommended": None, "judge_cited_turns": []})
    return sample


def validate_judge_model(judge_model: str):
    backbone = (settings.model or "").lower()
    jm = (judge_model or "").lower()
    if not jm:
        raise ValueError("judge model required for LLM fallback")
    backbone_family = backbone.split("/")[0] if "/" in backbone else backbone
    judge_family = jm.split("/")[0] if "/" in jm else jm
    if jm == backbone or judge_family == backbone_family:
        raise ValueError(
            f"LLM judge must be a different model family from backbone {settings.model}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--votes", default="logs/votes.parquet")
    ap.add_argument("--histories", required=True,
                    help="directory containing history_*.parquet files")
    ap.add_argument("--out", default="judge_sample.jsonl")
    ap.add_argument("--n-delay", type=int, default=60)
    ap.add_argument("--n-lynch", type=int, default=60)
    ap.add_argument("--seed", type=int, default=20261106)
    ap.add_argument("--judge-model", default=None,
                    help="only validates family separation; no calls are made")
    args = ap.parse_args()
    if args.judge_model:
        validate_judge_model(args.judge_model)
    vdf = pd.read_parquet(args.votes)
    histories = []
    if os.path.isdir(args.histories):
        for name in sorted(os.listdir(args.histories)):
            if name.startswith("history_") and name.endswith(".parquet"):
                hdf = pd.read_parquet(os.path.join(args.histories, name))
                gid = name[len("history_"):-len(".parquet")]
                histories.append({"game_id": gid,
                                  "history": hdf.to_dict("records")})
    sample = build_sample(vdf, histories, n_delay=args.n_delay,
                          n_lynch=args.n_lynch, seed=args.seed)
    with open(args.out, "w", encoding="utf-8") as f:
        for item in sample:
            f.write(json.dumps(item) + "\n")
    print(f"Wrote {len(sample)} blinded game-days to {args.out}")


if __name__ == "__main__":
    main()
