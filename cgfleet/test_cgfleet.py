"""Tests for cgfleet.py. Need tmatch.py and xltwlb.py next to this file (the job's setup fetches both).
MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0."""
import functools
import itertools
import json
import math
import os
import random
import shutil
import sys
import tempfile
import time
import unittest
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

import cgfleet as G  # noqa: E402
import tmatch as TM  # noqa: E402


def make(rows, cap=10 ** 6, name="T"):
    return {"name": name, "vehicles": None, "capacity": cap, "rows": [tuple(r) for r in rows],
            "raw": [tuple(str(v) for v in r) for r in rows]}


def rint(d):
    return math.floor(d + 0.5)


def random_instance(n, seed, width=(10, 40), service=(5, 10), horizon=160, span=40):
    rng = random.Random(seed)
    c = span // 2
    rows = [(c, c, 0, 0, horizon, 0)]
    for _ in range(n):
        x, y = rng.randint(0, span), rng.randint(0, span)
        t0 = rint(math.hypot(x - c, y - c))
        s = rng.randint(*service)
        w = rng.randint(*width)
        a = rng.randint(t0, horizon - s - t0 - w)
        rows.append((x, y, 0, a, a + w, s))
    return make(rows)


def feasible_order(inst, order):
    """Plain simulation of one route from the raw rows (independent of tmatch and cgfleet)."""
    rows = inst["rows"]
    x0, y0, _, a0, b0, s0 = rows[0]
    t, prev, sp = a0, 0, s0
    for c in order:
        d = rint(math.hypot(rows[prev][0] - rows[c][0], rows[prev][1] - rows[c][1]))
        t = max(t + sp + d, rows[c][3])
        if t > rows[c][4]:
            return False
        prev, sp = c, rows[c][5]
    d = rint(math.hypot(rows[prev][0] - x0, rows[prev][1] - y0))
    return t + sp + d <= b0


def elementary_best(inst, pi):
    """Max of sum pi over every feasible elementary route (all customers, all orders). pi indexed 0..n-1."""
    n = len(inst["rows"]) - 1
    best = 0
    for size in range(1, n + 1):
        for sub in itertools.combinations(range(1, n + 1), size):
            val = sum(pi[c - 1] for c in sub)
            if val <= best:
                continue
            if any(feasible_order(inst, p) for p in itertools.permutations(sub)):
                best = val
    return best


def brute_min_fleet(inst):
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


def brute_r2(C, e, l, pi):
    """Max profit over R2 walks on customers with pi >= 1, by memoised search over (previous, current, time)."""
    S = [i for i in range(len(pi)) if pi[i] >= 1]

    @functools.lru_cache(maxsize=None)
    def more(prev, cur, t):
        best = 0
        for j in S:
            if j == cur or j == prev:
                continue
            tt = max(t + float(C[cur, j]), float(e[j]))
            if tt <= l[j] + 1e-9:
                best = max(best, pi[j] + more(cur, j, tt))
        return best

    best = 0
    for j in S:
        if e[j] <= l[j] + 1e-9:
            best = max(best, pi[j] + more(-1, j, float(e[j])))
    return best


class TestPricing(unittest.TestCase):
    def test_exact_against_memoised_search(self):
        for seed in range(1, 26):
            inst = random_instance(6, seed)
            I = TM.Inst(inst)
            rng = random.Random(100 + seed)
            pi = [rng.randint(0, 5) for _ in range(I.n)]
            r = G.price(I.C, I.e, I.l, np.array(pi), L_max=500)
            self.assertFalse(r["capped"])
            self.assertEqual(r["pstar"], brute_r2(I.C, I.e, I.l, pi), seed)

    def test_never_below_any_real_route(self):
        """Validity: zero-profit customers may be skipped and P* is at least every elementary route's profit."""
        for seed in range(30, 50):
            inst = random_instance(6, seed, width=(20, 60))
            I = TM.Inst(inst)
            rng = random.Random(seed)
            pi = [rng.choice([0, 0, 1, 2, 3, 7]) for _ in range(I.n)]
            r = G.price(I.C, I.e, I.l, np.array(pi), L_max=500)
            self.assertGreaterEqual(r["pstar"], elementary_best(inst, pi), seed)

    def test_walks_are_feasible_and_best_first(self):
        for seed in range(60, 72):
            inst = random_instance(8, seed, width=(20, 70))
            I = TM.Inst(inst)
            pi = np.array([1 + (seed * 7 + i * 3) % 4 for i in range(I.n)])
            r = G.price(I.C, I.e, I.l, pi, L_max=500)
            self.assertTrue(r["walks"])
            for w in r["walks"]:
                self.assertTrue(G.walk_ok(I.C, I.e, I.l, w), (seed, w))
            self.assertEqual(int(pi[r["walks"][0]].sum()), r["pstar"])
            self.assertEqual(len(set(map(tuple, r["walks"]))), len(r["walks"]))

    def test_cap_and_empty(self):
        inst = random_instance(6, 3)
        I = TM.Inst(inst)
        r = G.price(I.C, I.e, I.l, np.full(I.n, 50), L_max=10)
        self.assertIsNone(r["pstar"])
        self.assertTrue(r["capped"])
        self.assertTrue(r["walks"])
        r0 = G.price(I.C, I.e, I.l, np.zeros(I.n, dtype=np.int64), L_max=10)
        self.assertEqual(r0["pstar"], 0)

    def test_no_immediate_repeat_or_two_cycle(self):
        """One customer with a very wide window next to another: without the R2 rules the walk would bounce."""
        inst = make([(0, 0, 0, 0, 1000, 0), (10, 0, 0, 0, 900, 1), (11, 0, 0, 0, 900, 1)])
        I = TM.Inst(inst)
        r = G.price(I.C, I.e, I.l, np.array([1, 1]), L_max=100)
        self.assertEqual(r["pstar"], 2)
        inst3 = make([(0, 0, 0, 0, 1000, 0), (10, 0, 0, 0, 900, 1), (11, 0, 0, 0, 900, 1), (10, 1, 0, 0, 900, 1)])
        I3 = TM.Inst(inst3)
        r3 = G.price(I3.C, I3.e, I3.l, np.array([1, 1, 1]), L_max=1000)
        # i-j-k-i cycles are allowed (that is the relaxation), so the walk can be long; it is still R2 and on time
        self.assertGreater(r3["pstar"], 3)
        self.assertTrue(G.walk_ok(I3.C, I3.e, I3.l, r3["walks"][0]))


class TestBound(unittest.TestCase):
    def test_incompatible_customers(self):
        inst = make([(50, 50, 0, 0, 1000, 0), (0, 50, 0, 100, 105, 5), (100, 50, 0, 100, 105, 5),
                     (50, 0, 0, 100, 105, 5)])
        I = TM.Inst(inst)
        now = time.monotonic()
        res = G.cg_bound(I.C, I.e, I.l, I.n, now + 20, now + 40, say=lambda m: None)
        self.assertEqual(res["lb_int"], 3)
        self.assertGreater(float(res["lb"]), 2.99)
        self.assertLessEqual(res["lb"], Fraction(3))

    def test_never_above_the_true_minimum(self):
        for seed in range(80, 92):
            inst = random_instance(6, seed, width=(10, 50))
            I = TM.Inst(inst)
            now = time.monotonic()
            res = G.cg_bound(I.C, I.e, I.l, I.n, now + 15, now + 30, say=lambda m: None)
            opt = brute_min_fleet(inst)
            self.assertGreaterEqual(res["lb_int"], 1)
            self.assertLessEqual(res["lb_int"], opt, seed)
            self.assertLessEqual(float(res["lb"]), res["z_rmp"] + 1e-6)
            c = res["cert"]
            r = G.price(I.C, I.e, I.l, np.array(c["pi_int"]), L_max=20000)
            self.assertEqual(r["pstar"], c["pstar"])
            self.assertEqual(Fraction(sum(c["pi_int"]), r["pstar"]), res["lb"])

    def test_fceil(self):
        self.assertEqual(G.fceil(Fraction(7, 2)), 4)
        self.assertEqual(G.fceil(Fraction(6, 2)), 3)
        self.assertEqual(G.fceil(Fraction(1, 1000)), 1)


class TestHarness(unittest.TestCase):
    def test_one_end_to_end(self):
        inst = random_instance(20, 7, width=(20, 60), horizon=300)
        rows = inst["rows"]
        text = ["NAME : XLTW-Test-n21", "TYPE : VRPTW", "DIMENSION : %d" % len(rows), "EDGE_WEIGHT_TYPE : EUC_2D",
                "CAPACITY : %d" % inst["capacity"], "NODE_COORD_SECTION"]
        text += ["%d %d %d" % (i + 1, r[0], r[1]) for i, r in enumerate(rows)]
        text += ["DEMAND_SECTION"] + ["%d %d" % (i + 1, r[2]) for i, r in enumerate(rows)]
        text += ["TIME_WINDOW_SECTION"] + ["%d %d %d" % (i + 1, r[3], r[4]) for i, r in enumerate(rows)]
        text += ["SERVICE_TIME_SECTION"] + ["%d %d" % (i + 1, r[5]) for i, r in enumerate(rows)]
        text += ["DEPOT_SECTION", "1", "-1", "EOF"]
        d = tempfile.mkdtemp()
        try:
            p = os.path.join(d, "XLTW-Test-n21.vrp")
            with open(p, "w") as f:
                f.write("\n".join(text) + "\n")
            ref = {"XLTW-Test-n21": {"kc": 1, "kstar": 1, "vehicles_a": 20}}
            r = G.one(p, "XLTW-Test-n21", ref, os.path.join(d, "cert"), per_1000=1000.0, final_extra=20.0)
            self.assertNotIn("error", r)
            self.assertGreaterEqual(r["lb_int"], 1)
            self.assertLessEqual(r["lb_int"], 20)
            self.assertFalse(r["above_ub"])
            with open(os.path.join(d, "cert", "XLTW-Test-n21.json")) as f:
                c = json.load(f)
            self.assertEqual(c["fleet_at_least"], r["lb_int"])
            t = G.tally([r, {"instance": "x", "error": "e"}])
            self.assertEqual(t["errors"], ["x"])
            self.assertEqual(t["sum_lb"], r["lb_int"])
            res = {"instances": [r], "tally": t}
            G.write_md(os.path.join(d, "r.md"), res)
        finally:
            shutil.rmtree(d)

    def test_load_ref(self):
        d = tempfile.mkdtemp()
        try:
            p = os.path.join(d, "en.json")
            with open(p, "w") as f:
                json.dump({"instances": [{"instance": "A", "kc": 1, "k": 3, "e": 9, "vehicles_a": 20},
                                         {"instance": "B", "kc": 1, "k": 4, "e": None, "vehicles_a": None}]}, f)
            ref = G.load_ref(p)
            self.assertEqual(ref["A"]["kstar"], 9)
            self.assertEqual(ref["B"]["kstar"], 4)
            self.assertEqual(G.load_ref(os.path.join(d, "none.json")), {})
        finally:
            shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
