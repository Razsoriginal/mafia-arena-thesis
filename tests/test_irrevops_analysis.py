"""IrrevOps v3 analysis: task-level unit, two-level bootstrap, template
permutation test, blinding."""
import unittest

import numpy as np
import pandas as pd

from src.irrevops import analysis as A


def _episodes(n_templates=12, n_inst=4, rollouts=3, harm_a=0.5, harm_b=0.5, hold_a=0.1, hold_b=0.1,
              template_sd=0.0, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for t in range(n_templates):
        shift = rng.normal(0, template_sd)
        for i in range(n_inst):
            for twin in ("act", "abstain"):
                for arm, harm, hold in (("A", harm_a, hold_a), ("B", harm_b, hold_b)):
                    for r in range(rollouts):
                        risky = twin != "act"
                        rows.append({"task_id": f"T{t}-{i}-{twin}", "template_id": f"T{t}", "pair_id": f"T{t}-{i}",
                                     "twin": twin, "decidable": t % 2 == 0, "arm": arm, "rep": r,
                                     "harm": bool(risky and rng.random() < min(1, max(0, harm + shift))),
                                     "false_hold": bool((not risky) and rng.random() < hold),
                                     "escalated": bool(rng.random() < 0.3), "residual_harm": False, "completed": not risky,
                                     "cost_inr": 0.1, "n_steps": 5, "agent_parse_fails": 0, "ended": "finish"})
    return pd.DataFrame(rows)


class TestAnalysis(unittest.TestCase):
    def test_task_is_the_unit_and_rollouts_are_averaged(self):
        ep = _episodes(n_templates=3, n_inst=2, rollouts=3)
        tl = A.task_level(ep)
        self.assertEqual(len(tl), 3 * 2 * 2 * 2)
        self.assertTrue((tl["n_rollouts"] == 3).all())
        r = A.arm_rate(tl, "A", "harm", n_boot=200)
        self.assertEqual(r["n_tasks"], 6)        # risky twins only
        self.assertEqual(A.arm_rate(tl, "A", "false_hold", n_boot=200)["n_tasks"], 6)

    def test_a_large_effect_is_detected_with_the_right_sign(self):
        tl = A.task_level(_episodes(harm_a=0.1, harm_b=0.6, seed=1))
        r = A.paired_contrast(tl, "A", "B", "harm", n_boot=2000, n_perm=2000)
        self.assertLess(r["diff"], -0.3)
        self.assertLess(r["ci_high"], 0)
        self.assertLess(r["p_perm"], 0.01)
        self.assertEqual(r["n_templates"], 12)

    def test_permutation_test_holds_its_level_under_template_clustering(self):
        """No arm effect, strong template effects: the template-level test
        must not reject much more than 5% of the time."""
        rej = 0
        sims = 120
        for s in range(sims):
            tl = A.task_level(_episodes(template_sd=0.25, seed=100 + s))
            if A.paired_contrast(tl, "A", "B", "harm", n_boot=50, n_perm=400, seed=s)["p_perm"] < 0.05:
                rej += 1
        self.assertLessEqual(rej / sims, 0.12)

    def test_stratum_filter_and_unpaired_tasks(self):
        ep = _episodes(seed=2)
        ep = ep[~((ep["arm"] == "B") & (ep["template_id"] == "T0"))]
        tl = A.task_level(ep)
        r = A.paired_contrast(tl, "A", "B", "harm", stratum=True, n_boot=200, n_perm=200)
        self.assertEqual(r["n_templates"], 5)    # 6 decidable templates, one lost in arm B
        self.assertGreater(A.paired_contrast(tl, "A", "B", "harm", n_boot=200, n_perm=200)["n_unpaired"], 0)

    def test_informedness_and_utility(self):
        tl = A.task_level(_episodes(harm_a=0.1, harm_b=0.6, hold_a=0.3, hold_b=0.05, seed=3))
        j = A.informedness_contrast(tl, "A", "B", n_boot=1000, n_perm=1000)
        self.assertGreater(j["diff"], 0.1)       # catches 0.5 more, holds 0.25 more
        u = A.utility_table(tl)
        best = u.loc[u.groupby(["lambda", "c_escalation"])["utility"].idxmax()].set_index(["lambda", "c_escalation"])
        self.assertEqual(best.loc[(1000, 0.1), "arm"], "A")   # harm dominates
        self.assertEqual(best.loc[(1, 0.1), "arm"], "A")
        u2 = A.utility_table(A.task_level(_episodes(harm_a=0.10, harm_b=0.12, hold_a=0.6, hold_b=0.05, seed=4)))
        best2 = u2.loc[u2.groupby(["lambda", "c_escalation"])["utility"].idxmax()].set_index(["lambda", "c_escalation"])
        self.assertEqual(best2.loc[(1, 0.1), "arm"], "B")     # over-blocking dominates at low lambda

    def test_holm(self):
        adj = A.holm({"a": 0.01, "b": 0.04, "c": 0.03})
        self.assertAlmostEqual(adj["a"], 0.03)
        self.assertAlmostEqual(adj["c"], 0.06)
        self.assertAlmostEqual(adj["b"], 0.06)
        with self.assertRaises(ValueError):          # a missing test may not shrink the family
            A.holm({"a": 0.01, "d": float("nan")})

    def test_confirmatory_campaigns_stay_blind_without_the_lock_tag(self):
        self.assertTrue(A.may_unblind("explore-ops-01", False))
        self.assertFalse(A.may_unblind("ops-A-01", False))
        self.assertFalse(A.may_unblind("ops-no-such-campaign", True))   # no lock tag

    def test_nuisance_table_has_no_arm_or_outcome_column(self):
        cols = set(A.nuisance_table(_episodes(n_templates=2)).columns)
        self.assertFalse(cols & {"arm", "harm", "false_hold", "escalated", "residual_harm"})


if __name__ == "__main__":
    unittest.main()
