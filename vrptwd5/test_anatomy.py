"""Tests for anatomy.py on hand-made instances (values worked out by hand in the comments).

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.
"""
import unittest

import anatomy as an
import double_check as dc

# rows: (x, y, demand, ready, due, service)
ROWS = [
    (0, 0, 0, 0, 1000, 0),   # depot
    (1, 3, 1, 0, 10, 0),     # 0 -> 1: sqrt(10) = 3.1623, DIMACS 31 tenths
    (2, 6, 1, 0, 6.2, 0),    # 1 -> 2: sqrt(10), DIMACS 31; arrives at 6.2 (DIMACS) vs 6.3246 (double)
    (0, 10, 1, 50, 90, 0),   # 0 -> 3: exactly 10.0; must wait until 50
]
INST = {"name": "TEST1", "vehicles": 5, "capacity": 100, "rows": ROWS}

# depot due 6.2: route [1] returns at 6.2 under DIMACS (31 + 31 tenths) and 6.3246 in double precision
TIGHT = {"name": "TEST2", "vehicles": 5, "capacity": 100,
         "rows": [(0, 0, 0, 0, 6.2, 0), (1, 3, 1, 0, 100, 0)]}


class RouteAnatomy(unittest.TestCase):
    def test_late_at_zero_slack_customer(self):
        a = an.route_anatomy([1, 2], ROWS)
        self.assertEqual(a["late"], 1)
        self.assertEqual(a["late_unexposed"], 0)
        self.assertEqual(a["zero_slack"], 1)
        self.assertEqual(a["exposed"], 1)
        self.assertEqual(a["waits"], 0)
        self.assertEqual(a["max_chain"], 3)
        self.assertEqual(a["first_late"]["stop"], 2)
        self.assertEqual(a["first_late"]["from_end"], 1)
        self.assertEqual(a["first_late"]["chain"], 2)
        self.assertEqual(a["first_late"]["slack"], 0)
        self.assertAlmostEqual(a["first_late"]["late_by"], 2 * 10 ** 0.5 - 6.2, places=5)
        self.assertEqual(a["depot_slack"], 10000 - 125)  # back after 31 + 31 + 63 tenths
        self.assertFalse(a["horizon_bound"])
        self.assertEqual(a["wait_share"], 0.0)

    def test_wait_resets_chain(self):
        a = an.route_anatomy([3], ROWS)
        self.assertEqual(a["waits"], 1)
        self.assertEqual(a["wait_share"], 1.0)
        self.assertEqual(a["max_chain"], 1)  # would be 2 without the reset at customer 3
        self.assertEqual(a["late"], 0)
        self.assertIsNone(a["first_late"])
        self.assertEqual(a["depot_slack"], 10000 - 600)  # wait until 50, back at 60

    def test_horizon_bound_late_at_depot(self):
        a = an.route_anatomy([1], TIGHT["rows"])
        self.assertTrue(a["horizon_bound"])
        self.assertEqual(a["depot_slack"], 0)
        self.assertEqual(a["late"], 1)
        self.assertEqual(a["first_late"]["stop"], "depot")
        self.assertEqual(a["first_late"]["from_end"], 0)
        self.assertEqual(a["first_late"]["chain"], 2)


class InstanceAnatomy(unittest.TestCase):
    def test_counts_match_double_check(self):
        routes = [[1, 2], [3]]
        ok, reason, cost = dc.check_dimacs(routes, INST)
        self.assertTrue(ok, reason)
        dbl = dc.check_double(routes, INST)
        per, t = an.instance_anatomy(routes, INST)
        self.assertEqual(len(per), 2)
        self.assertEqual(t["late"], dbl["late"])
        self.assertEqual(t["late_routes"], dbl["late_routes"])
        self.assertEqual(t["late_routes"], 1)
        self.assertEqual(t["wait_share"], round(1 / 3, 4))
        self.assertEqual(t["horizon_bound_routes"], 0)
        self.assertEqual(t["max_chain"], 3)

    def test_family(self):
        self.assertEqual(an.family("C101"), "C1")
        self.assertEqual(an.family("RC208"), "RC2")
        self.assertEqual(an.family("C2_8_3"), "C2")
        self.assertEqual(an.family("R1_10_1"), "R1")

    def test_auc(self):
        self.assertAlmostEqual(an.auc([3, 2], [1, 2]), 3.5 / 4)
        self.assertIsNone(an.auc([], [1]))


class Scoring(unittest.TestCase):
    def tally(self, **kw):
        t = {"rows": 356, "dimacs_fail": [], "count_mismatch": [], "late_unexposed": 0, "late_instances": 90,
             "c2_route_late_rate_200_600": 0.01, "c2_route_late_rate_800_1000": 0.015,
             "c2_late_horizon_share": 0.9, "r1rc1_late_horizon_share": 0.2,
             "c2_wait_share_late_routes": 0.01, "c2_wait_share_other_routes": 0.05, "auc_exposed": 0.9}
        t.update(kw)
        return t

    def test_all_hold(self):
        self.assertEqual(set(an.score_a(self.tally()).values()), {"held"})

    def test_failures_and_untestable(self):
        s = an.score_a(self.tally(late_instances=89, c2_route_late_rate_800_1000=0.03,
                                  c2_late_horizon_share=0.5, auc_exposed=0.7,
                                  c2_wait_share_late_routes=None))
        self.assertEqual(s["A0"], "did not hold")
        self.assertEqual(s["A1"], "did not hold")
        self.assertEqual(s["A2"], "did not hold")
        self.assertEqual(s["A3"], "held")
        self.assertEqual(s["A4"], "untestable")
        self.assertEqual(s["A5"], "did not hold")
        self.assertEqual(an.score_a(self.tally(c2_route_late_rate_200_600=0.0))["A1"], "untestable")


if __name__ == "__main__":
    unittest.main()
