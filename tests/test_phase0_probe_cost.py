"""Probe cost per probed (LLM-arm) game; null-arm games are not in the
denominator (Pre-reg v2 SS9 GO condition 3, clarified)."""
import json
import os
import tempfile
import unittest

from src.eval import run_arena


class TestProbeCostDenominator(unittest.TestCase):
    def test_nulls_excluded_from_denominator(self):
        with tempfile.TemporaryDirectory() as td:
            raw = os.path.join(td, "raw")
            for gid, cost in (("c-5000-dmn_village", 0.6), ("c-5000-cot_village", 0.3),
                              ("c-5000-cotx3_village", 0.3), ("c-5000-random_village", 0.0),
                              ("c-5000-majority_village", 0.0)):
                d = os.path.join(raw, f"task-{gid}")
                os.makedirs(d)
                with open(os.path.join(d, "llm_raw.jsonl"), "w") as f:
                    if cost:
                        f.write(json.dumps({"purpose": "probe", "cost_inr": cost}) + "\n")
                    f.write(json.dumps({"purpose": "speak", "cost_inr": 1.0}) + "\n")
            rows = [{"arm": a} for a in ("dmn_village", "cot_village", "cotx3_village",
                                          "random_village", "majority_village")]
            got = run_arena._probe_cost_per_probed_game(raw, rows)
        self.assertAlmostEqual(got, 1.2 / 3)


if __name__ == "__main__":
    unittest.main()
