"""Tests for vrp_probe.py. MV2 of Munim, Inc. Apache-2.0.

The PyVRP tests run only where pyvrp is installed (the compete job installs it).
"""
import os
import tempfile
import unittest

from vrp_probe import (check, dist, parse_sol, parse_vrp, route_clients,
                       to_pyvrp_routes, write_sol)

try:
    import pyvrp
except ImportError:
    pyvrp = None

TINY = """NAME : T
COMMENT : "tiny test: one depot, three clients"
TYPE : CVRP
DIMENSION : 4
EDGE_WEIGHT_TYPE : EUC_2D
CAPACITY : 10
NODE_COORD_SECTION
1 0 0
2 3 4
3 6 8
4 0 5
DEMAND_SECTION
1 0
2 4
3 4
4 5
DEPOT_SECTION
1
-1
EOF
"""


class ProbeTest(unittest.TestCase):
    def setUp(self):
        self.name, self.cap, self.coords, self.demands = parse_vrp(TINY)

    def test_parse_vrp(self):
        self.assertEqual(self.name, "T")
        self.assertEqual(self.cap, 10)
        self.assertEqual(self.coords[0], (0.0, 0.0))
        self.assertEqual(self.coords[3], (0.0, 5.0))
        self.assertEqual(self.demands[2], 4)

    def test_dist_rounds_to_nearest(self):
        self.assertEqual(dist((0, 0), (1, 1)), 1)   # 1.414
        self.assertEqual(dist((0, 0), (1, 2)), 2)   # 2.236
        self.assertEqual(dist((0, 0), (2, 3)), 4)   # 3.606
        self.assertEqual(dist((3, 4), (6, 8)), 5)

    def test_check_feasible_cost(self):
        ok, reason, cost = check([[1, 2], [3]], self.cap, self.coords, self.demands)
        self.assertTrue(ok, reason)
        self.assertEqual(cost, 30)

    def test_check_over_capacity(self):
        ok, reason, _ = check([[1, 2, 3]], self.cap, self.coords, self.demands)
        self.assertFalse(ok)
        self.assertIn("capacity", reason)

    def test_check_missing_client(self):
        ok, _, _ = check([[1, 2]], self.cap, self.coords, self.demands)
        self.assertFalse(ok)

    def test_check_repeated_client(self):
        ok, _, _ = check([[1, 2], [3, 1]], self.cap, self.coords, self.demands)
        self.assertFalse(ok)

    def test_check_depot_in_route(self):
        ok, _, _ = check([[1, 2], [0, 3]], self.cap, self.coords, self.demands)
        self.assertFalse(ok)

    def test_sol_round_trip(self):
        text = write_sol([[1, 2], [3]], 30)
        self.assertEqual(text, "Route #1: 1 2\nRoute #2: 3\nCost 30\n")
        routes, cost = parse_sol(text)
        self.assertEqual(routes, [[1, 2], [3]])
        self.assertEqual(cost, 30)

    def test_bad_depot(self):
        with self.assertRaises(ValueError):
            parse_vrp(TINY.replace("DEPOT_SECTION\n1\n", "DEPOT_SECTION\n2\n"))

    def test_to_pyvrp_routes(self):
        self.assertEqual(to_pyvrp_routes([[1, 2], [3]]), [[0, 1], [2]])


@unittest.skipIf(pyvrp is None, "pyvrp not installed")
class PyVRPMappingTest(unittest.TestCase):
    """CVRPLib ids -> PyVRP and back must be the identity, and costs must agree."""

    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".vrp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(TINY)
        self.data = pyvrp.read(self.path, round_func="round")
        _, self.cap, self.coords, self.demands = parse_vrp(TINY)

    def tearDown(self):
        os.remove(self.path)

    def test_round_trip_and_cost(self):
        ids = [[1, 2], [3]]
        sol = pyvrp.Solution(self.data, to_pyvrp_routes(ids))
        back = sorted(route_clients(r) for r in sol.routes())
        self.assertEqual(back, ids)
        ok, reason, cost = check(back, self.cap, self.coords, self.demands)
        self.assertTrue(ok, reason)
        self.assertEqual(sol.distance(), cost)
        self.assertTrue(sol.is_feasible())

    def test_solve_output_checks(self):
        from pyvrp.stop import MaxIterations
        res = pyvrp.solve(self.data, stop=MaxIterations(200), seed=1,
                          collect_stats=False, display=False)
        routes = [route_clients(r) for r in res.best.routes()]
        ok, reason, cost = check(routes, self.cap, self.coords, self.demands)
        self.assertTrue(ok, reason)
        self.assertEqual(res.best.distance(), cost)


if __name__ == "__main__":
    unittest.main()
