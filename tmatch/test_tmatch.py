"""Tests for tmatch.py (no instance data or network needed, except that test_one_end_to_end needs xltwlb.py, which
the job's setup fetches). MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0."""
import itertools
import json
import math
import os
import random
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

import tmatch as T  # noqa: E402


def make(rows, cap=10 ** 6, name="T"):
    return {"name": name, "vehicles": None, "capacity": cap, "rows": [tuple(r) for r in rows],
            "raw": [tuple(str(v) for v in r) for r in rows]}


def rint(d):
    return math.floor(d + 0.5)


def feasible_order(inst, order):
    """Plain simulation of one route (independent of tmatch)."""
    rows = inst["rows"]
    x0, y0, _, a0, b0, s0 = rows[0]
    t, prev, sp, load = a0, 0, s0, 0
    for c in order:
        d = rint(math.hypot(rows[prev][0] - rows[c][0], rows[prev][1] - rows[c][1]))
        t = max(t + sp + d, rows[c][3])
        if t > rows[c][4]:
            return False
        prev, sp = c, rows[c][5]
        load += rows[c][2]
    d = rint(math.hypot(rows[prev][0] - x0, rows[prev][1] - y0))
    return t + sp + d <= b0 and load <= inst["capacity"]


def brute_min_fleet(inst):
    """Exact fewest routes for a tiny instance: feasibility of every subset by all orders, then a set-partition DP."""
    n = len(inst["rows"]) - 1
    ok = [False] * (1 << n)
    for mask in range(1, 1 << n):
        members = [i + 1 for i in range(n) if mask >> i & 1]
        ok[mask] = any(feasible_order(inst, p) for p in itertools.permutations(members))
    f = [10 ** 9] * (1 << n)
    f[0] = 0
    for mask in range(1, 1 << n):
        low = mask & -mask
        sub = mask
        while sub:
            if sub & low and ok[sub] and f[mask ^ sub] + 1 < f[mask]:
                f[mask] = f[mask ^ sub] + 1
            sub = (sub - 1) & mask
    return f[(1 << n) - 1]


def random_instance(n, seed, width=(20, 200), service=5, horizon=400, demand=0, cap=10 ** 6):
    rng = random.Random(seed)
    rows = [(50, 50, 0, 0, horizon, 0)]
    for _ in range(n):
        x, y = rng.randint(0, 100), rng.randint(0, 100)
        t0 = rint(math.hypot(x - 50, y - 50))
        w = rng.randint(*width)
        a = rng.randint(t0, horizon - service - t0 - w)
        rows.append((x, y, demand, a, a + w, service))
    return make(rows, cap=cap)


def zero_width_instance(n, seed, service=5, horizon=400):
    rng = random.Random(seed)
    rows = [(50, 50, 0, 0, horizon, 0)]
    for _ in range(n):
        x, y = rng.randint(0, 100), rng.randint(0, 100)
        t0 = rint(math.hypot(x - 50, y - 50))
        a = rng.randint(t0, horizon - service - t0)
        rows.append((x, y, 0, a, a, service))
    return make(rows)


def run(inst, max_iter, seed=1, lb=None):
    I = T.Inst(inst)
    routes, traj, st = T.solve(I, deadline=float("inf"), seed=seed, lb=lb, max_iter=max_iter)
    return I, [[v + 1 for v in r] for r in routes], traj, st


class TestHelpers(unittest.TestCase):
    def test_rint_sqrt(self):
        for d2 in range(0, 30000):
            self.assertEqual(T.rint_sqrt(d2), math.floor(math.sqrt(d2) + 0.5), d2)
        self.assertEqual(T.rint_sqrt(2), 1)   # 1.414
        self.assertEqual(T.rint_sqrt(3), 2)   # 1.732
        self.assertEqual(T.rint_sqrt(6), 2)   # k^2 + k = 6: sqrt 2.449 -> 2
        self.assertEqual(T.rint_sqrt(7), 3)   # 2.646 -> 3

    def test_inst_arrays(self):
        inst = make([(0, 0, 0, 0, 100, 0), (3, 4, 1, 0, 50, 2), (6, 8, 1, 30, 40, 1)])
        I = T.Inst(inst)
        self.assertEqual(I.n, 2)
        self.assertEqual(list(I.e), [5.0, 30.0])            # depot leg 5 and 10
        self.assertEqual(list(I.l), [50.0, 40.0])           # min(b, 100 - s - t0)
        self.assertEqual(int(I.C[0, 1]), 2 + 5)             # s_1 + t_12
        self.assertEqual(int(I.C[1, 0]), 1 + 5)
        self.assertTrue(I.capfree)
        self.assertEqual(I.unservable, 0)
        self.assertEqual(I.C.dtype, np.int32)

    def test_chains_from(self):
        self.assertEqual(T.chains_from(np.array([2, -1, 1, -1])), [[0, 2, 1], [3]])
        with self.assertRaises(RuntimeError):
            T.chains_from(np.array([1, 0, -1]))

    def test_schedule_by_hand(self):
        # depot (0,0) 0-100; c1 at (10,0) [0,50] s=5; c2 at (20,0) [0,60] s=5. C12 = 5 + 10.
        inst = make([(0, 0, 0, 0, 100, 0), (10, 0, 0, 0, 50, 5), (20, 0, 0, 0, 60, 5)])
        I = T.Inst(inst)
        E, L = T.schedule(I, [0, 1])
        self.assertEqual(E, [10.0, 25.0])
        self.assertEqual(L, [45.0, 60.0])   # l2 = min(60, 100 - 5 - 20) = 60; l1 = min(50, 60 - 15) = 45

    def test_sol_text(self):
        self.assertEqual(T.sol_text([[1, 2], [3]], 42), "Route #1: 1 2\nRoute #2: 3\nCost: 42\n")


class TestExactCheck(unittest.TestCase):
    INST = make([(0, 0, 0, 0, 100, 0), (10, 0, 3, 0, 15, 5), (20, 0, 3, 0, 30, 5), (0, 30, 3, 0, 100, 5)], cap=6)

    def test_good(self):
        c = T.exact_check(self.INST, [[1, 2], [3]])
        self.assertTrue(c["ok"], c)
        self.assertEqual(c["distance"], 10 + 10 + 20 + 30 + 30)

    def test_detects_each_problem(self):
        self.assertFalse(T.exact_check(self.INST, [[2, 1], [3]])["ok"])           # c1 due 15, reached at 35
        self.assertFalse(T.exact_check(self.INST, [[1, 2]])["ok"])                # c3 missing
        self.assertEqual(T.exact_check(self.INST, [[1, 2]])["missing"], 1)
        self.assertEqual(T.exact_check(self.INST, [[1, 2], [3, 1]])["duplicates"], 1)
        self.assertFalse(T.exact_check(self.INST, [[1, 2, 3]])["ok"])             # load 9 > 6
        self.assertFalse(T.exact_check(self.INST, [[1], [2], [3], []])["ok"])     # empty route
        self.assertFalse(T.exact_check(self.INST, [[1], [2], [9]])["ok"])         # no customer 9
        late_depot = make([(0, 0, 0, 0, 40, 0), (10, 0, 0, 0, 40, 25)])
        self.assertFalse(T.exact_check(late_depot, [[1]])["ok"])                  # back at 10 + 25 + 10 = 45 > 40


class TestSearch(unittest.TestCase):
    def test_zero_width_windows_are_solved_exactly(self):
        """With a = b every time is forced, so the first matching is the exact fewest routes."""
        for seed in (1, 2, 3, 4):
            inst = zero_width_instance(7, seed)
            _, routes, _, st = run(inst, max_iter=0)
            self.assertTrue(T.exact_check(inst, routes)["ok"])
            self.assertEqual(len(routes), brute_min_fleet(inst), seed)

    def test_never_below_optimum_and_always_feasible(self):
        for seed in (11, 12, 13, 14, 15, 16):
            inst = random_instance(6, seed)
            _, routes, traj, st = run(inst, max_iter=40, seed=seed)
            c = T.exact_check(inst, routes)
            self.assertTrue(c["ok"], c)
            self.assertGreaterEqual(len(routes), brute_min_fleet(inst))

    def test_retiming_merges_two_routes(self):
        """Both customers want the same early slot, so no fixed start puts them on one route; only re-timing
        (one route early, the other late) does."""
        inst = make([(0, 0, 0, 0, 300, 0), (10, 0, 0, 10, 100, 5), (10, 10, 0, 10, 100, 5)])
        self.assertEqual(brute_min_fleet(inst), 1)
        I = T.Inst(inst)
        self.assertEqual(len(T.routes_of(I, T.match_chains(I, I.e.copy(), np.arange(2))[0])), 2)
        _, routes, traj, st = run(inst, max_iter=60, seed=3, lb=1)
        self.assertEqual(len(routes), 1)
        self.assertEqual(st["stop"], "bound")
        self.assertTrue(T.exact_check(inst, routes)["ok"])

    def test_capacity_free_rounds_never_get_worse(self):
        """Every old route stays a path under its new times, so with no capacity and no zero-cost arcs no round can
        need more routes: none may be rejected, and the count only goes down."""
        for seed in (21, 22):
            inst = random_instance(60, seed, width=(30, 250))
            _, routes, traj, st = run(inst, max_iter=60, seed=seed)
            self.assertEqual(st["rejected"], 0, st)
            self.assertEqual(st["accepted"], 60)
            counts = [x[1] for x in traj]
            self.assertEqual(counts, sorted(counts, reverse=True))
            self.assertEqual(len(set(counts)), len(counts))
            self.assertEqual(counts[-1], len(routes))
            self.assertTrue(T.exact_check(inst, routes)["ok"])

    def test_capacity_is_respected(self):
        inst = random_instance(40, 31, width=(50, 200), demand=7, cap=30)
        I, routes, traj, st = run(inst, max_iter=20, seed=31)
        self.assertFalse(I.capfree)
        c = T.exact_check(inst, routes)
        self.assertTrue(c["ok"], c)
        self.assertGreaterEqual(len(routes), math.ceil(40 * 7 / 30.0))
        for r in routes:
            self.assertLessEqual(7 * len(r), 30)

    def test_zero_cost_ties_make_no_cycle(self):
        """Three customers at one place, service 0, all at the same instant: the tie rule orders them."""
        inst = make([(0, 0, 0, 0, 100, 0), (10, 0, 0, 10, 10, 0), (10, 0, 0, 10, 10, 0), (10, 0, 0, 10, 10, 0)])
        _, routes, _, st = run(inst, max_iter=5)
        self.assertEqual(len(routes), 1)
        self.assertTrue(T.exact_check(inst, routes)["ok"])

    def test_deterministic_for_a_seed(self):
        inst = random_instance(50, 41, width=(30, 250))
        a = run(inst, max_iter=15, seed=5)[1]
        b = run(inst, max_iter=15, seed=5)[1]
        self.assertEqual(a, b)


class TestHarness(unittest.TestCase):
    def test_loaders_and_plan(self):
        d = tempfile.mkdtemp()
        try:
            en = {"instances": [
                {"instance": "XLTW-Test-n3000", "kc": 1, "k": 5, "e": 40, "vehicles_a": 50, "customers": 2999},
                {"instance": "XLTW-Test-n1841", "kc": 1, "k": 4, "e": 18, "vehicles_a": 29, "customers": 1840},
                {"instance": "XLTW-Test-n2000", "kc": 7, "k": 7, "e": 3, "vehicles_a": 9, "customers": 1999},
                {"instance": "XLTW-Test-n9000", "kc": 1, "k": 4, "e": None, "vehicles_a": None, "customers": 8999},
                {"instance": "XLTW-Test-n1234", "kc": 1, "k": 7, "e": 27, "vehicles_a": 35, "customers": 1233}]}
            p = os.path.join(d, "en.json")
            with open(p, "w") as f:
                json.dump(en, f)
            ref = T.load_xltwen(p)
            self.assertEqual(ref["XLTW-Test-n3000"]["kstar"], 40)
            self.assertEqual(ref["XLTW-Test-n9000"]["kstar"], 4)
            self.assertEqual(T.plan(ref), ["XLTW-Test-n1234", "XLTW-Test-n1841", "XLTW-Test-n3000"] + T.EXTRA)
            k = os.path.join(d, "km.json")
            with open(k, "w") as f:
                json.dump({"instances": [{"instance": "A", "km": 3}, {"instance": "B", "km": None}]}, f)
            self.assertEqual(T.load_kmatch(k), {"A": 3})
            self.assertEqual(T.load_xltwen(os.path.join(d, "nothing.json")), {})
        finally:
            shutil.rmtree(d)

    def test_tally(self):
        def rec(name, routes, va, lb, w, ok=True, cf=True):
            return {"instance": name, "customers": 100, "capfree": cf, "routes": routes, "vehicles_a": va, "lb": lb,
                    "best_full": T.BEST.get(name), "window_median_rel": w, "exact": {"ok": ok},
                    "seconds_search": 10.0, "budget_s": 6.0, "peak_gb": 0.1, "at_lb": routes == lb}
        recs = [rec("XLTW-Test-n1234", 30, 35, 27, 0.1), rec("b", 50, 40, 20, 0.5), rec("c", 20, 20, 20, 0.3),
                rec("XLTW-Test-n1748", 143, 150, 143, 0.01, cf=False), {"instance": "d", "error": "x"}]
        t = T.tally(recs)
        self.assertEqual(t["wins"], ["XLTW-Test-n1234"])
        self.assertEqual(t["losses"], ["b"])
        self.assertEqual(t["ties"], ["c"])
        self.assertEqual((t["sum_tmatch"], t["sum_pyvrp_a"], t["sum_lb"]), (100, 95, 67))
        self.assertEqual(t["at_lb"], ["c", "XLTW-Test-n1748"])
        self.assertEqual(t["named"], {"XLTW-Test-n1234": [30, 33]})
        self.assertEqual(t["extra"], {"XLTW-Test-n1748": [143, 143, 150]})
        self.assertEqual(t["errors"], ["d"])
        self.assertEqual(t["invalid"], [])
        self.assertEqual(len(t["over_budget_30s"]), 0)
        self.assertEqual(t["spearman_window_vs_advantage"], -1.0)

    def test_one_end_to_end(self):
        """A small instance written as a VRPLIB file, read by xltwlb.parse_any, solved and checked by one()."""
        inst = random_instance(30, 51, width=(30, 250))
        rows = inst["rows"]
        text = ["NAME : XLTW-Test-n31", "TYPE : VRPTW", "DIMENSION : %d" % len(rows), "EDGE_WEIGHT_TYPE : EUC_2D",
                "CAPACITY : %d" % inst["capacity"], "NODE_COORD_SECTION"]
        text += ["%d %d %d" % (i + 1, r[0], r[1]) for i, r in enumerate(rows)]
        text += ["DEMAND_SECTION"] + ["%d %d" % (i + 1, r[2]) for i, r in enumerate(rows)]
        text += ["TIME_WINDOW_SECTION"] + ["%d %d %d" % (i + 1, r[3], r[4]) for i, r in enumerate(rows)]
        text += ["SERVICE_TIME_SECTION"] + ["%d %d" % (i + 1, r[5]) for i, r in enumerate(rows)]
        text += ["DEPOT_SECTION", "1", "-1", "EOF"]
        d = tempfile.mkdtemp()
        try:
            p = os.path.join(d, "XLTW-Test-n31.vrp")
            with open(p, "w") as f:
                f.write("\n".join(text) + "\n")
            ref = {"XLTW-Test-n31": {"kc": 1, "kstar": 1, "vehicles_a": 30}}
            r = T.one(p, "XLTW-Test-n31", ref, {}, os.path.join(d, "sols"), per_1000=100.0)
            self.assertTrue(r["exact"]["ok"], r["exact"])
            self.assertEqual(r["customers"], 30)
            self.assertGreaterEqual(r["routes"], 1)
            self.assertLessEqual(r["routes"], 30)
            self.assertLessEqual(r["seconds_search"], r["budget_s"] + 5)
            with open(os.path.join(d, "sols", "XLTW-Test-n31.sol")) as f:
                body = f.read()
            self.assertTrue(body.startswith("Route #1: "))
            self.assertIn("Cost: %d" % r["exact"]["distance"], body)
            self.assertEqual(body.count("Route #"), r["routes"])
        finally:
            shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
