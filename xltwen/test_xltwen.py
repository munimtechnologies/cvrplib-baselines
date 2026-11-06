"""Tests for xltwen.py. MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.

The key test brute-forces the minimum fleet of small random VRPTW instances (nearest-integer travel times) and checks
that no bound computed here ever exceeds it, and that every busy-period variant fits the optimal routes."""
import itertools
import math
import random
import unittest

import numpy as np

import xltwen as E


def inst_of(rows, name="t"):
    return {"name": name, "vehicles": len(rows), "capacity": 10 ** 6, "rows": rows, "raw": None}


def rt(a, b):
    return int(math.floor(math.hypot(a[0] - b[0], a[1] - b[1]) + 0.5))


def route_ok(rows, route):
    d = rows[0]
    t, prev = d[3], d
    for c in route:
        r = rows[c]
        t = max(t + rt(prev, r), r[3])
        if t > r[4]:
            return False
        t, prev = t + r[5], r
    return t + rt(prev, d) <= d[4]


def feasible_order(rows, subset):
    for perm in itertools.permutations(subset):
        if route_ok(rows, perm):
            return list(perm)
    return None


def min_fleet(rows):
    n = len(rows) - 1
    order = {}
    for m in range(1, 1 << n):
        sub = [i + 1 for i in range(n) if m >> i & 1]
        o = feasible_order(rows, sub)
        if o is not None:
            order[m] = o
    INF = 10 ** 9
    g, choice = [INF] * (1 << n), [None] * (1 << n)
    g[0] = 0
    for m in range(1, 1 << n):
        low = m & -m
        sub = m
        while sub:
            if sub & low and sub in order and g[m ^ sub] + 1 < g[m]:
                g[m], choice[m] = g[m ^ sub] + 1, sub
            sub = (sub - 1) & m
    routes, m = [], (1 << n) - 1
    while m:
        routes.append(order[choice[m]])
        m ^= choice[m]
    return g[(1 << n) - 1], routes


def random_rows(rng, n):
    H = rng.randint(150, 400)
    rows = [(25, 25, 0, 0, H, 0)]
    while len(rows) < n + 1:
        x, y = rng.randint(0, 50), rng.randint(0, 50)
        s = rng.randint(1, 60)
        a = rng.randint(0, H)
        b = min(H, a + rng.randint(0, 200))
        t0 = rt((x, y), rows[0])
        if max(a, t0) <= min(b, H - s - t0):
            rows.append((x, y, 0, a, b, s))
    return rows


class Travel(unittest.TestCase):
    def test_round_exact(self):
        cases = {0: 0, 1: 1, 2: 1, 3: 2, 6: 2, 7: 3, 12: 3, 13: 4, 100: 10, 110: 10, 111: 11,
                 10 ** 8: 10 ** 4, 10 ** 8 + 10 ** 4: 10 ** 4, 10 ** 8 + 10 ** 4 + 1: 10 ** 4 + 1}
        # an integer point at squared distance d2 where one exists (a^2 + b^2 = d2)
        for d2, want in cases.items():
            pt = next(((a, b) for a in range(int(math.isqrt(d2)) + 1) for b in [math.isqrt(d2 - a * a)]
                       if a * a + b * b == d2), None)
            if pt is None:
                continue
            self.assertEqual(int(E.travel(0, 0, pt[0], pt[1])), want, d2)
            self.assertEqual(int(E.travel(0, 0, pt[0], pt[1])), int(math.floor(math.sqrt(d2) + 0.5)), d2)

    def test_matches_float_on_grid(self):
        xs = np.arange(-40, 41)
        X, Y = np.meshgrid(xs, xs)
        got = E.travel(0, 0, X, Y)
        want = np.floor(np.hypot(X, Y) + 0.5)
        self.assertTrue(np.array_equal(got, want))


class Hand(unittest.TestCase):
    def test_three_long_jobs_need_two(self):
        rows = [(0, 0, 0, 0, 100, 0)] + [(10, 0, 0, 0, 100, 40)] * 3
        res, P = E.bound_instance(inst_of(rows), grid=64, refine=256)
        self.assertEqual(min_fleet(rows)[0], 2)
        self.assertEqual(res["e"], 2)
        self.assertTrue(all(res[v]["verified"] for v in E.VARIANTS))
        self.assertEqual(list(P["tau"]), [0, 0, 0])

    def test_compulsory_parts(self):
        # four customers that must all be served during [50, 60): each needs four vehicles
        rows = [(0, 0, 0, 0, 200, 0)] + [(5, 0, 0, 50, 50, 10)] * 4
        res, _ = E.bound_instance(inst_of(rows), grid=64, refine=256)
        self.assertEqual(min_fleet(rows)[0], 4)
        self.assertEqual(res["e"], 4)
        self.assertEqual(max(res[v]["compulsory"] for v in E.VARIANTS), 4)

    def test_compulsory_sweep(self):
        r = np.array([0.0, 0, 10])
        p = np.array([10.0, 10, 5])
        d = np.array([10.0, 10, 15])
        self.assertEqual(E.compulsory(r, p, d)[0], 2)  # [10, 15) of job 3 does not overlap [0, 10)

    def test_energy_exact_matches_scan(self):
        rng = np.random.default_rng(1)
        r = rng.integers(0, 100, 50).astype(float)
        p = rng.integers(1, 30, 50).astype(float)
        d = r + p + rng.integers(0, 60, 50)
        b, t1, t2 = E.energy_scan(r, p, d, np.unique(r), np.unique(d))
        self.assertEqual(E.energy_exact(r, p, d, t1, t2)[0], b)


class Validity(unittest.TestCase):
    def test_never_above_brute_force(self):
        rng = random.Random(20261106)
        tight = 0
        for k in range(150):
            rows = random_rows(rng, rng.randint(3, 6))
            opt, routes = min_fleet(rows)
            res, P = E.bound_instance(inst_of(rows, "r%d" % k), grid=64, refine=256)
            self.assertLessEqual(res["e"], opt, (k, rows, res))
            for v in E.VARIANTS:
                self.assertLessEqual(res[v]["bound"], opt)
                self.assertTrue(res[v]["verified"])
            chk = E.check_routes(routes, P)
            self.assertTrue(chk["sim_ok"], (k, chk))
            self.assertTrue(all(chk["busy_ok"].values()), (k, chk, rows, routes))
            self.assertEqual(chk["customers_seen"], len(rows) - 1)
            self.assertEqual(chk["visits"], len(rows) - 1)
            tight += res["e"] == opt
        self.assertGreater(tight, 10)  # reported in the log; a loose sanity floor only

    def test_check_routes_flags_a_late_route(self):
        rows = [(0, 0, 0, 0, 100, 0), (10, 0, 0, 0, 20, 5), (20, 0, 0, 0, 22, 5)]
        _, P = E.bound_instance(inst_of(rows), grid=16, refine=32)
        self.assertFalse(E.check_routes([[1, 2]], P)["sim_ok"])
        self.assertTrue(E.check_routes([[1], [2]], P)["sim_ok"])


class Tally(unittest.TestCase):
    def rec(self, name, kc, k, e, veh=None, ok=True):
        r = {"instance": name, "kc": kc, "k": k, "e": e, "vehicles_a": veh, "customers": 10, "exact_inputs": True,
             "service_ok": True, "unservable": 0, "best_variant": "in", "inner_interval_wins": False}
        for v in E.VARIANTS:
            r[v] = {"verified": True, "bound": e}
        if veh is not None:
            r["sol_check"] = {"sim_ok": ok, "busy_ok": {v: True for v in E.VARIANTS}, "routes": veh,
                              "customers_seen": 10, "visits": 10}
        return r

    def test_gate(self):
        recs = [self.rec("XLTW-Test-n%d" % i, 1, 1, 5, 9) for i in range(4)]
        t = E.tally(recs, 0.5, 10.0, expected=4, expected_sols=4)
        self.assertEqual(t["predictions"]["E0"], "held")
        recs[0]["e"] = 10  # above a verified solution: a bug, so nothing else is scored
        t = E.tally(recs, 0.5, 10.0, expected=4, expected_sols=4)
        self.assertEqual(t["predictions"]["E0"], "did not hold")
        self.assertEqual(t["predictions"]["E1"], "not scored (E0)")

    def test_partial_is_untestable(self):
        t = E.tally([self.rec("a", 1, 1, 2)], 0.5, 1.0, expected=2, expected_sols=0)
        self.assertEqual(t["predictions"]["E0"], "untestable")


if __name__ == "__main__":
    unittest.main()
