"""Tests for double_check.py. MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0."""
import json
import os
import sys
import tempfile
import unittest

import double_check as dc

# Five customers on a line of sqrt(5) hops: DIMACS arrives at customer 5 at exactly 11.0
# (due 11), double precision at 11.18, so the route is feasible only under DIMACS.
TOY = """TOY

VEHICLE
NUMBER     CAPACITY
  2          100

CUSTOMER
CUST NO.  XCOORD.   YCOORD.    DEMAND   READY TIME  DUE DATE   SERVICE   TIME
    0      0          0          0          0        100          0
    1      1          2          10         0        100          0
    2      2          4          10         0        100          0
    3      3          6          10         0        100          0
    4      4          8          10         0        100          0
    5      5          10         10         0        11           0
"""
SOL = "Route #1: 1 2 3 4 5\nCost 22.1\n"


class TestDoubleCheck(unittest.TestCase):
    def setUp(self):
        self.inst = dc.parse_solomon(TOY)

    def test_parse(self):
        self.assertEqual(self.inst["name"], "TOY")
        self.assertEqual((self.inst["vehicles"], self.inst["capacity"]), (2, 100))
        self.assertEqual(len(self.inst["rows"]), 6)
        routes, cost = dc.parse_sol(SOL)
        self.assertEqual(routes, [[1, 2, 3, 4, 5]])
        self.assertAlmostEqual(cost, 22.1)

    def test_dimacs_feasible(self):
        ok, reason, cost = dc.check_dimacs([[1, 2, 3, 4, 5]], self.inst)
        self.assertTrue(ok, reason)
        self.assertEqual(cost, 221)

    def test_double_late(self):
        r = dc.check_double([[1, 2, 3, 4, 5]], self.inst)
        self.assertFalse(r["ok"])
        self.assertEqual(r["late"], 1)
        self.assertEqual(r["late_routes"], 1)
        self.assertAlmostEqual(r["max_late"], 5 * 5 ** 0.5 - 11, places=3)
        self.assertAlmostEqual(r["distance"], 22.36068, places=4)

    def test_double_direct_still_late(self):
        # customer 5 is collinear with the depot, so even a direct trip arrives at 11.18
        r = dc.check_double([[1, 2, 3, 4], [5]], self.inst)
        self.assertFalse(r["ok"])
        self.assertEqual((r["late"], r["late_routes"]), (1, 1))

    def test_double_feasible_with_looser_window(self):
        inst = dc.parse_solomon(TOY)
        x, y, q, ready, due, service = inst["rows"][5]
        inst["rows"][5] = (x, y, q, ready, 12, service)
        r = dc.check_double([[1, 2, 3, 4, 5]], inst)
        self.assertTrue(r["ok"], r["reason"])
        self.assertEqual(r["late"], 0)

    def test_structure(self):
        ok, reason, _ = dc.check_dimacs([[1, 2, 2, 4, 5]], self.inst)
        self.assertFalse(ok)
        self.assertIn("repeated", reason)
        self.assertFalse(dc.check_double([[1, 2, 3, 4]], self.inst)["ok"])

    def test_versus_sintef(self):
        self.assertEqual(dc.versus_sintef(3, 100.0, (3, 100.004)), "equal")
        self.assertEqual(dc.versus_sintef(2, 200.0, (3, 100.0)), "better")
        self.assertEqual(dc.versus_sintef(3, 99.0, (3, 100.0)), "better")
        self.assertEqual(dc.versus_sintef(4, 1.0, (3, 100.0)), "worse")
        self.assertEqual(dc.versus_sintef(3, 100.02, (3, 100.0)), "worse")

    def test_sol_instance(self):
        self.assertEqual(dc.sol_instance("R1_10_1-lex.sol"), "R1_10_1")
        self.assertEqual(dc.sol_instance("sols/rc202-lex.sol"), "RC202")

    def test_sintef_table(self):
        self.assertEqual(len(dc.SINTEF), 62)
        self.assertEqual(dc.SINTEF["R101"], (19, 1650.80))
        self.assertEqual(dc.SINTEF["R1_10_1"], (100, 53380.18))

    def test_sols_shipped(self):
        here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sols")
        names = [f for f in os.listdir(here) if f.endswith(".sol")]
        self.assertEqual(len(names), 24)
        for f in names:
            self.assertIn(dc.sol_instance(f), dc.SINTEF)

    def test_main_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "data", "cvrplib-vrptw")
            sols = os.path.join(d, "sols")
            os.makedirs(src)
            os.makedirs(sols)
            with open(os.path.join(src, "900.txt"), "w", encoding="utf-8") as f:
                f.write(TOY)
            with open(os.path.join(src, "900.sol"), "w", encoding="utf-8") as f:
                f.write(SOL)
            with open(os.path.join(sols, "TOY-lex.sol"), "w", encoding="utf-8") as f:
                f.write(SOL)
            argv = sys.argv
            sys.argv = ["double_check.py", "--ids", "900", "--sols", sols,
                        "--data-dir", os.path.join(d, "data"), "--out-dir", os.path.join(d, "out")]
            try:
                dc.main()
            finally:
                sys.argv = argv
            with open(os.path.join(d, "out", "vrptwd", "results.json"), encoding="utf-8") as f:
                res = json.load(f)
            rows = res["rows"]
            self.assertEqual([r["source"] for r in rows], ["cvrplib-bks", "pyvrp-lex"])
            self.assertTrue(rows[0]["dimacs_ok"])
            self.assertFalse(rows[0]["double_ok"])
            self.assertFalse(rows[1]["double_ok"])
            self.assertEqual(res["tally"]["dimacs_hygiene_fail"], [])
            self.assertIsNone(rows[0]["double_vs_sintef"])
            self.assertTrue(os.path.exists(os.path.join(d, "out", "vrptwd", "results.md")))


if __name__ == "__main__":
    unittest.main()
