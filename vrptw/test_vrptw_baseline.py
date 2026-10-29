"""Tests for vrptw_baseline.py. MV2 of Munim, Inc. Apache-2.0.

The PyVRP tests run only where pyvrp is installed (the compete job installs it).
"""
import os
import tempfile
import unittest

from vrptw_baseline import (check_tw, dist10, fmt, parse_ids, parse_sol,
                            parse_solomon, route_clients, run_one, to_vrplib,
                            write_sol)

try:
    import pyvrp
except ImportError:
    pyvrp = None

# Same layout as CVRPLib's Solomon files (trailing spaces, a line with one space).
TINY = """TINY

VEHICLE
NUMBER     CAPACITY
  2         10

CUSTOMER
CUST NO.  XCOORD.   YCOORD.    DEMAND   READY TIME  DUE DATE   SERVICE   TIME

    0      0          0          0          0        100          0
    1      3          4          4          0         12          1
    2      6          8          4          0         30          1
    3      1          1          5         10         50          2
"""


class ParseTest(unittest.TestCase):
    def setUp(self):
        self.inst = parse_solomon(TINY)

    def test_parse_solomon(self):
        self.assertEqual(self.inst["name"], "TINY")
        self.assertEqual(self.inst["vehicles"], 2)
        self.assertEqual(self.inst["capacity"], 10)
        self.assertEqual(len(self.inst["rows"]), 4)
        self.assertEqual(self.inst["rows"][0], (0, 0, 0, 0, 100, 0))
        self.assertEqual(self.inst["rows"][3], (1, 1, 5, 10, 50, 2))

    def test_bad_numbering(self):
        with self.assertRaises(ValueError):
            parse_solomon(TINY.replace("    3      1 ", "    4      1 "))

    def test_parse_ids(self):
        self.assertEqual(parse_ids("380-382,676"), ["380", "381", "382", "676"])

    def test_to_vrplib(self):
        text = to_vrplib(self.inst)
        self.assertIn("DIMENSION : 4\n", text)
        self.assertIn("VEHICLES : 2\n", text)
        self.assertIn("CAPACITY : 10\n", text)
        self.assertIn("NODE_COORD_SECTION\n1 0 0\n2 3 4\n", text)
        self.assertIn("TIME_WINDOW_SECTION\n1 0 100\n2 0 12\n", text)
        self.assertIn("SERVICE_TIME_SECTION\n1 0\n2 1\n", text)
        self.assertTrue(text.endswith("DEPOT_SECTION\n1\n-1\nEOF\n"))

    def test_dist10_truncates(self):
        self.assertEqual(dist10((0, 0), (1, 1)), 14)    # 1.414 -> 1.4
        self.assertEqual(dist10((0, 0), (3, 4)), 50)
        self.assertEqual(dist10((6, 8), (1, 1)), 86)    # 8.602 -> 8.6
        self.assertEqual(dist10((0.5, 0), (0, 0)), 5)

    def test_fmt_and_sol(self):
        self.assertEqual(fmt(228), "22.8")
        self.assertEqual(fmt(5), "0.5")
        text = write_sol([[1, 2], [3]], 228)
        self.assertEqual(text, "Route #1: 1 2\nRoute #2: 3\nCost 22.8\n")
        self.assertEqual(parse_sol(text), ([[1, 2], [3]], 228))


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.inst = parse_solomon(TINY)

    def test_feasible_cost_with_waiting(self):
        ok, reason, cost = check_tw([[1, 2], [3]], self.inst)
        self.assertTrue(ok, reason)
        self.assertEqual(cost, 228)

    def test_late_customer(self):
        ok, reason, _ = check_tw([[2, 1], [3]], self.inst)
        self.assertFalse(ok)
        self.assertIn("customer 1", reason)

    def test_capacity(self):
        ok, reason, _ = check_tw([[1, 2, 3]], self.inst)
        self.assertFalse(ok)
        self.assertIn("capacity", reason)

    def test_too_many_routes(self):
        ok, reason, _ = check_tw([[1], [2], [3]], self.inst)
        self.assertFalse(ok)
        self.assertIn("vehicles", reason)

    def test_missing_and_repeated(self):
        self.assertFalse(check_tw([[1, 2]], self.inst)[0])
        self.assertFalse(check_tw([[1, 2], [3, 1]], self.inst)[0])
        self.assertFalse(check_tw([[1, 2], [0, 3]], self.inst)[0])

    def test_late_at_depot(self):
        rows = list(self.inst["rows"])
        rows[0] = (0, 0, 0, 0, 13, 0)
        ok, reason, _ = check_tw([[1, 2], [3]], dict(self.inst, rows=rows))
        self.assertFalse(ok)
        self.assertIn("depot", reason)


@unittest.skipIf(pyvrp is None, "pyvrp not installed")
class PyVRPTest(unittest.TestCase):
    """PyVRP with round_func='dimacs' must agree with the independent checker."""

    def setUp(self):
        self.inst = parse_solomon(TINY)
        fd, self.path = tempfile.mkstemp(suffix=".vrp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(to_vrplib(self.inst))
        self.data = pyvrp.read(self.path, round_func="dimacs")

    def tearDown(self):
        os.remove(self.path)

    def test_mapping_and_cost(self):
        sol = pyvrp.Solution(self.data, [[0, 1], [2]])
        self.assertEqual(sorted(route_clients(r) for r in sol.routes()), [[1, 2], [3]])
        self.assertEqual(sol.distance(), 228)
        self.assertTrue(sol.is_feasible())

    def test_time_warp_is_infeasible(self):
        sol = pyvrp.Solution(self.data, [[1, 0], [2]])
        self.assertFalse(sol.is_feasible())

    def test_run_one_both_modes(self):
        for mode in ("dist", "lex"):
            r = run_one((self.path, mode, 2, 1))
            ok, reason, cost = check_tw(r["routes"], self.inst)
            self.assertTrue(ok, "%s: %s" % (mode, reason))
            self.assertEqual(r["distance"], cost)
            self.assertTrue(r["feasible"])


if __name__ == "__main__":
    unittest.main()
