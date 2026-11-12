"""P0-S1: intra-game call concurrency changes timing only.

A deterministic mock keyed on the exact prompt (so any change in what an
agent sees changes its answer) with random per-call delays (so threads
finish out of order). Histories, vote rows, trust rows and token/cost
totals must be identical at MAFIA_CALL_THREADS=1 and 8.
"""
import hashlib
import json
import math
import os
import random
import re
import tempfile
import time as _time
import unittest
from unittest.mock import MagicMock, patch

from src import llm_client


def _h(*parts) -> int:
    return int(hashlib.sha256("\x1f".join(parts).encode()).hexdigest(), 16)


def _alive(user):
    m = re.search(r"Alive(?: others)?: \[([^\]]*)\]", user)
    if not m:
        return [str(i) for i in range(7)]
    return [x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()]


def _content(system, user):
    h = _h(system, user)
    alive = _alive(user)
    if "imaginative mind" in system:
        return json.dumps({"hypotheses": [{"suspect": alive[h % len(alive)], "motive": "m",
                                           "exformation": ["a", "b"], "confidence": (h % 100) / 100}]})
    if "verifier mind" in system:
        m = re.search(r"'suspect': '(\d+)'", user)
        s = m.group(1) if m else "1"
        return json.dumps({"verified": [{"suspect": s, "evidence_spans": [0],
                                         "contradiction_found": bool(h % 2),
                                         "revised_confidence": ((h >> 8) % 100) / 100}]})
    if "Output trust scores" in system:
        return json.dumps({"trust": {a: ((h >> (3 * i)) % 100) / 100 for i, a in enumerate(alive)}})
    if "night action" in system:
        opts = re.search(r"Choose exactly one target from \[([^\]]*)\]", user)
        o = [x.strip().strip("'\"") for x in opts.group(1).split(",")] if opts else alive
        key = "kill" if "kill" in user.split("Night action:")[-1][:40] else (
            "save" if "protect" in user else "check")
        return json.dumps({key: o[h % len(o)], "reason": "r"})
    if "vote" in system.lower():
        choices = alive + ["no-lynch"]
        return json.dumps({"vote": choices[h % len(choices)], "reason": f"t{h % 5} shows it"})
    return f"line-{h % 10**8}"


def _fake_create(**kw):
    system = kw["messages"][0]["content"]
    user = kw["messages"][1]["content"]
    _time.sleep(random.uniform(0, 0.004))  # scramble completion order
    m = MagicMock()
    m.choices[0].message.content = _content(system, user)
    m.choices[0].message.reasoning_content = ""
    m.choices[0].message.reasoning = ""
    m.model = "meta/muse-spark-1.3-contributor"
    m.usage.prompt_tokens = len(user) % 997
    m.usage.completion_tokens = _h(user) % 503
    m.usage.cost = round((len(user) % 997) * 1e-5 + (_h(user) % 503) * 2e-5, 6)
    return m


def _run(arm, threads, seed=100300):
    from src.eval import run_arena

    old = os.environ.get("MAFIA_CALL_THREADS")
    os.environ["MAFIA_CALL_THREADS"] = str(threads)
    raw = tempfile.mkdtemp(prefix="mafia-conc-raw-")
    old_raw = os.environ.get("MAFIA_RAW_DIR")
    os.environ["MAFIA_RAW_DIR"] = raw
    try:
        mark = dict(llm_client.COST_LOG)
        with patch.object(llm_client, "get_client") as gc, \
                patch.object(run_arena, "_log_progress", lambda *a, **k: None):
            gc.return_value.chat.completions.create.side_effect = _fake_create
            g = run_arena.play_one(seed, design="team", arm=arm, run_dir=tempfile.mkdtemp(),
                                   max_days=5, run_tag="t", campaign="t")
        cost = {k: round(llm_client.COST_LOG[k] - mark.get(k, 0), 6)
                for k in ("calls", "prompt_tokens", "completion_tokens", "cost_inr")}
    finally:
        for k, v in (("MAFIA_CALL_THREADS", old), ("MAFIA_RAW_DIR", old_raw)):
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def norm(rows):
        return json.dumps(rows, sort_keys=True, default=lambda x: None if isinstance(x, float) and math.isnan(x) else str(x))

    return {"history": json.dumps(g.history, default=str), "votes": norm(g._vote_rows),
            "trust": norm(g._trust_rows), "winner": g.winner, "day": g.day, "cost": cost}


class TestConcurrencyEquivalence(unittest.TestCase):
    def test_threads_change_nothing_but_timing(self):
        for arm in ("dmn_village", "cotx3_village", "cot_village"):
            a = _run(arm, 1)
            b = _run(arm, 8)
            self.assertEqual(a["history"], b["history"], arm)
            self.assertEqual(a["votes"], b["votes"], arm)
            self.assertEqual(a["trust"], b["trust"], arm)
            self.assertEqual(a["winner"], b["winner"], arm)
            self.assertEqual(a["cost"], b["cost"], arm)
            self.assertGreater(a["cost"]["calls"], 10, arm)

    def test_threaded_matches_pre_concurrency_golden(self):
        """Golden = the sequential code before P0-S1 (generated at commit
        prior to the change, same mock). Threads must reproduce it exactly,
        so a semantic change that is identical at 1 and 8 threads (e.g.
        speakers sharing one snapshot) is still caught."""
        path = os.path.join(os.path.dirname(__file__), "fixtures", "concurrency_golden.json")
        with open(path, encoding="utf-8") as f:
            golden = json.load(f)
        for arm, ref in golden.items():
            got = json.loads(json.dumps(_run(arm, 8), sort_keys=True))
            for k in ("history", "trust", "winner", "day"):
                self.assertEqual(got[k], ref[k], f"{arm}:{k}")
            # Vote rows: compare on the golden's columns. Later additive
            # schema fields (v2 lynched / lynched_is_mafia /
            # vote_target_is_mafia) are covered by their own tests.
            ref_votes, got_votes = json.loads(ref["votes"]), json.loads(got["votes"])
            self.assertEqual(len(got_votes), len(ref_votes), arm)
            for gv, rv in zip(got_votes, ref_votes):
                self.assertEqual({k: gv.get(k) for k in rv}, rv, f"{arm}:votes")
            for k, v in ref["cost"].items():
                self.assertAlmostEqual(got["cost"][k], v, places=5, msg=f"{arm}:cost:{k}")

    def test_threads_are_actually_used(self):
        from src.eval import run_arena

        old = os.environ.get("MAFIA_CALL_THREADS")
        os.environ["MAFIA_CALL_THREADS"] = "8"
        try:
            self.assertEqual(run_arena._call_threads(), 8)
            seen = set()
            import threading

            def f(x):
                seen.add(threading.get_ident())
                _time.sleep(0.01)
                return x * 2

            self.assertEqual(run_arena._pmap(f, list(range(8))), [x * 2 for x in range(8)])
            self.assertGreater(len(seen), 1)
        finally:
            if old is None:
                os.environ.pop("MAFIA_CALL_THREADS", None)
            else:
                os.environ["MAFIA_CALL_THREADS"] = old


if __name__ == "__main__":
    unittest.main()
