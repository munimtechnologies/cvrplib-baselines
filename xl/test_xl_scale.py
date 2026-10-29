"""Tests for xl_scale.py. MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0."""
import os
import random
import tempfile
import unittest

import xl_scale as xs

try:
    import numpy  # noqa: F401
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False

try:
    import pyvrp  # noqa: F401
    HAVE_PYVRP = True
except ImportError:
    HAVE_PYVRP = False

TINY = """NAME : tiny-n4
COMMENT : "made for a test: not a real instance"
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
3 5
4 3
DEPOT_SECTION
1
-1
EOF
"""


def random_file(n, seed):
    rng = random.Random(seed)
    lines = ["NAME : rand-n%d" % (n + 1), "TYPE : CVRP", "DIMENSION : %d" % (n + 1),
             "EDGE_WEIGHT_TYPE : EUC_2D", "CAPACITY : 50", "NODE_COORD_SECTION", "1 0 0"]
    lines += ["%d %d %d" % (i + 2, rng.randrange(1001), rng.randrange(1001)) for i in range(n)]
    lines += ["DEMAND_SECTION", "1 0"]
    lines += ["%d %d" % (i + 2, rng.randrange(1, 11)) for i in range(n)]
    lines += ["DEPOT_SECTION", "1", "-1", "EOF"]
    return "\n".join(lines) + "\n"


class TestParse(unittest.TestCase):
    def test_tiny(self):
        name, cap, x, y, d = xs.parse_vrplib(TINY)
        self.assertEqual(name, "tiny-n4")
        self.assertEqual(cap, 10)
        self.assertEqual(x, [0, 3, 6, 0])
        self.assertEqual(y, [0, 4, 8, 5])
        self.assertEqual(d, [0, 4, 5, 3])

    def test_bad_depot(self):
        with self.assertRaises(ValueError):
            xs.parse_vrplib(TINY.replace("DEPOT_SECTION\n1\n", "DEPOT_SECTION\n2\n"))


class TestDistance(unittest.TestCase):
    def test_dist10(self):
        self.assertEqual(xs.dist10(0, 0, 3, 4), 50)
        self.assertEqual(xs.dist10(0, 0, 1, 1), 14)  # 14.142... truncated
        self.assertEqual(xs.dist10(5, 5, 5, 5), 0)
        self.assertEqual(xs.dist10(0, 0, 1000, 1000), 14142)

    @unittest.skipIf(not HAVE_NUMPY, "numpy not installed")
    def test_matrix_matches_dist10(self):
        rng = random.Random(1)
        x = [rng.randrange(1001) for _ in range(300)]
        y = [rng.randrange(1001) for _ in range(300)]
        m = xs.dist_matrix(x, y, chunk=64)
        self.assertEqual(m.shape, (300, 300))
        for i in range(300):
            for j in range(300):
                self.assertEqual(int(m[i, j]), xs.dist10(x[i], y[i], x[j], y[j]))


class TestWindows(unittest.TestCase):
    def test_each_customer_reachable(self):
        _, _, x, y, _ = xs.parse_vrplib(random_file(500, 2))
        horizon, tws = xs.make_windows(x, y, seed=7)
        self.assertEqual(tws[0], (0, horizon))
        self.assertEqual(len(tws), 501)
        for i in range(1, 501):
            d0 = xs.dist10(x[0], y[0], x[i], y[i])
            early, late = tws[i]
            self.assertLessEqual(d0, early)
            self.assertLessEqual(early, late)
            self.assertLessEqual(late + xs.SERVICE + d0, horizon)

    def test_deterministic(self):
        _, _, x, y, _ = xs.parse_vrplib(random_file(50, 3))
        self.assertEqual(xs.make_windows(x, y, 9), xs.make_windows(x, y, 9))
        self.assertNotEqual(xs.make_windows(x, y, 9)[1], xs.make_windows(x, y, 10)[1])


class TestCheck(unittest.TestCase):
    # depot (0,0); 1 = (3,4); 2 = (6,8): 0-1 50, 1-2 50, 0-2 100 tenths
    X, Y, D = [0, 3, 6], [0, 4, 8], [0, 4, 5]

    def test_ok(self):
        tws = [(0, 1000), (0, 1000), (0, 1000)]
        self.assertEqual(xs.check([[1, 2]], self.X, self.Y, self.D, 10, tws, 1000), (True, "", 200))

    def test_late(self):
        tws = [(0, 1000), (0, 1000), (0, 140)]
        ok, reason, _ = xs.check([[1, 2]], self.X, self.Y, self.D, 10, tws, 1000)
        self.assertFalse(ok)
        self.assertIn("late at customer 2", reason)
        # the other order arrives at 2 at 100, serves until 200, reaches 1 at 250, depot at 400
        self.assertEqual(xs.check([[2, 1]], self.X, self.Y, self.D, 10, tws, 1000), (True, "", 200))
        self.assertFalse(xs.check([[2, 1]], self.X, self.Y, self.D, 10, tws, 399)[0])

    def test_capacity_missing_repeat(self):
        tws = [(0, 1000)] * 3
        self.assertIn("capacity", xs.check([[1, 2]], self.X, self.Y, self.D, 8, tws, 1000)[1])
        self.assertIn("not visited", xs.check([[1]], self.X, self.Y, self.D, 10, tws, 1000)[1])
        self.assertIn("repeated", xs.check([[1], [1, 2]], self.X, self.Y, self.D, 10, tws, 1000)[1])


@unittest.skipIf(not HAVE_PYVRP, "pyvrp not installed")
class TestRealPyVRP(unittest.TestCase):
    def test_build_solve_check(self):
        import pyvrp
        from pyvrp.stop import MaxRuntime

        _, cap, x, y, d = xs.parse_vrplib(random_file(30, 4))
        horizon, tws = xs.make_windows(x, y, seed=5)
        data = xs.build_data(x, y, d, cap, tws, horizon, fleet=30)
        self.assertEqual(len(data.clients()), 30)
        res = pyvrp.solve(data, stop=MaxRuntime(1), seed=1, collect_stats=False, display=False)
        self.assertTrue(res.best.is_feasible())
        routes = [xs.route_clients(r) for r in res.best.routes()]
        self.assertEqual(sorted(c for r in routes for c in r), list(range(1, 31)))
        ok, reason, cost = xs.check(routes, x, y, d, cap, tws, horizon)
        self.assertTrue(ok, reason)
        self.assertEqual(cost, res.best.distance())

    def test_run_size_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.vrp")
            with open(path, "w", encoding="utf-8") as f:
                f.write(random_file(40, 6))
            rec = xs.run_size(path, 20, 1, 3)
        self.assertEqual(rec["n"], 20)
        self.assertTrue(rec["feasible"])
        self.assertTrue(rec["check_ok"], rec["check_reason"])
        self.assertTrue(rec["pyvrp_matches_check"])
        self.assertGreater(rec["peak_mb"], 0)
        self.assertGreaterEqual(rec["num_routes"], rec["route_lower_bound"])


if __name__ == "__main__":
    unittest.main()
