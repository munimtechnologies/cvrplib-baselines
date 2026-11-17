"""Tests for mstfleet.py (numpy and scipy needed; xltwlb.py is not needed here).
MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0."""
import json
import math
import os
import random
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

import mstfleet as M  # noqa: E402


def rint(d):
    """The challenge's travel time: nearest integer, ties up."""
    return math.floor(d + 0.5)


def make(rows, cap=10 ** 9, name="T"):
    return {"name": name, "capacity": cap, "rows": [tuple(r) for r in rows]}


def planted(K, per_route, seed, slack=(0, 30), span=100, service=(1, 6), wait=(0, 8), extra=(0, 40)):
    """An instance that K routes serve by construction (official rounding, waiting allowed), so its minimum fleet
    is at most K. Returns (inst, K)."""
    rng = random.Random(seed)
    c = span // 2
    rows = [None]
    ends = []
    for _ in range(K):
        t, px, py, sp = 0, c, c, 0
        for _ in range(per_route):
            x, y = rng.randint(0, span), rng.randint(0, span)
            t = t + sp + rint(math.hypot(x - px, y - py)) + rng.randint(*wait)
            s = rng.randint(*service)
            a = max(0, t - rng.randint(*slack))
            b = t + rng.randint(*slack)
            rows.append((x, y, 1, a, b, s))
            px, py, sp = x, y, s
        ends.append(t + sp + rint(math.hypot(px - c, py - c)))
    H = max(ends) + rng.randint(*extra)
    rows[0] = (c, c, 0, 0, H, 0)
    return make(rows), K


def exact_fleet(inst):
    """Minimum fleet by subset dynamic programming (tiny instances only), with the official travel times."""
    rows = inst["rows"]
    n = len(rows) - 1
    x0, y0, _, a0, b0, s0 = rows[0]

    def d(i, j):
        return rint(math.hypot(rows[i][0] - rows[j][0], rows[i][1] - rows[j][1]))

    INF = float("inf")
    E = [[INF] * (n + 1) for _ in range(1 << n)]
    for j in range(1, n + 1):
        t = max(rows[j][3], a0 + s0 + d(0, j))
        if t <= rows[j][4]:
            E[1 << (j - 1)][j] = t
    for mask in range(1, 1 << n):
        for j in range(1, n + 1):
            t = E[mask][j]
            if t == INF:
                continue
            for k in range(1, n + 1):
                if mask & (1 << (k - 1)):
                    continue
                u = max(rows[k][3], t + rows[j][5] + d(j, k))
                if u <= rows[k][4]:
                    m2 = mask | (1 << (k - 1))
                    if u < E[m2][k]:
                        E[m2][k] = u
    ok = [False] * (1 << n)
    for mask in range(1, 1 << n):
        ok[mask] = any(E[mask][j] + rows[j][5] + d(j, 0) <= b0 for j in range(1, n + 1) if E[mask][j] < INF)
    f = [INF] * (1 << n)
    f[0] = 0
    for mask in range(1, 1 << n):
        low = mask & -mask
        sub = mask
        while sub:
            if (sub & low) and ok[sub] and f[mask ^ sub] + 1 < f[mask]:
                f[mask] = f[mask ^ sub] + 1
            sub = (sub - 1) & mask
    return f[(1 << n) - 1]


class TestPrim(unittest.TestCase):
    def brute(self, P, lam):
        from scipy.sparse.csgraph import minimum_spanning_tree
        N = len(P)
        D = np.floor(np.hypot(P[:, None, 0] - P[None, :, 0], P[:, None, 1] - P[None, :, 1]) + 0.5 - 1e-9)
        D = D + lam[:, None] + lam[None, :]
        # scipy drops zero entries: shift every weight by 1 and take it off again
        D1 = D + 1.0
        np.fill_diagonal(D1, 0.0)
        T = minimum_spanning_tree(D1)
        return int(round(T.sum())) - (N - 1)

    def test_against_scipy(self):
        rng = np.random.default_rng(1)
        for trial in range(12):
            m = int(rng.integers(2, 45))
            xy = rng.integers(0, 60, size=(m, 2)).astype(float)
            lam = rng.integers(0, 6, size=m).astype(float) if trial % 2 else np.zeros(m)
            tot, child, parent, w = M.prim(xy, lam=lam)
            self.assertEqual(tot, self.brute(xy, lam))
            self.assertEqual(len(child), m - 1)
            root = np.array([30.0, 30.0])
            tot0, c0, p0, w0 = M.prim(xy, lam=lam, root=root)
            self.assertEqual(tot0, self.brute(np.vstack([xy, root[None, :]]), np.concatenate([lam, [0.0]])))
            self.assertEqual(len(c0), m)
            deg = M.degrees(m + 1, c0, p0)
            self.assertEqual(int(deg.sum()), 2 * m)

    def test_travel_lb_never_above_official(self):
        rng = np.random.default_rng(2)
        dx = rng.uniform(-500, 500, 2000)
        dy = rng.uniform(-500, 500, 2000)
        lb = M.travel_lb(dx, dy)
        off = np.array([rint(math.hypot(a, b)) for a, b in zip(dx, dy)])
        self.assertTrue(np.all(lb <= off))
        self.assertTrue(np.all(lb >= off - 1))
        # integer coordinates: identical
        ix, iy = rng.integers(-300, 300, 2000), rng.integers(-300, 300, 2000)
        self.assertTrue(np.array_equal(M.travel_lb(ix.astype(float), iy.astype(float)),
                                       np.array([rint(math.hypot(a, b)) for a, b in zip(ix, iy)], dtype=float)))

    def test_forest_and_k_free(self):
        w = np.array([5.0, 1.0, 9.0, 3.0])
        self.assertEqual(sorted(M.forest_drop(w, 3).tolist()), [0, 2])
        self.assertEqual(len(M.forest_drop(w, 1)), 0)
        # L = 10, W = 4, edges 9, 5, 3, 1 (F = 18): K = 1 -> 10 < 22; K = 2 -> 20 >= 4 + 9 = 13
        self.assertEqual(M.k_free(10, 4, [9, 5, 3, 1], 18), 2)
        self.assertEqual(M.k_free(100, 4, [9, 5, 3, 1], 18), 1)
        # tiny L: one vehicle per customer at most
        self.assertEqual(M.k_free(1, 5, [9, 5, 3, 1], 18), 5)


class TestValidity(unittest.TestCase):
    def check_inst(self, inst, K):
        I = M.Inst(inst)
        self.assertEqual(I.unservable, 0)
        res = M.bound_instance(I, budget=3.0, grid=8, say=lambda *_: None)
        self.assertLessEqual(res["best_K"], K, "bound above a planted fleet")
        self.assertTrue(res["verified"])
        # every scanned interval separately, plain and Lagrangian, with every valid variant
        T1 = M.grid_points(I.e, 6, [I.D0])
        T2 = M.grid_points(I.f, 6, [I.B0])
        for a in T1:
            for b in T2:
                if b <= a:
                    continue
                r = M.plain_bound(I, a, b)
                if r is None:
                    continue
                self.assertLessEqual(r["K"], K)
                self.assertTrue(M.verify(I, a, b, r["K"], None, r["variant"]))
                for var in {"free", M.variant_of(I, a, b)}:
                    k2, lam, its, hist = M.hk_bound(I, a, b, 1, deadline=float("inf"), variant=var, iters=25)
                    self.assertLessEqual(k2, K, "Lagrangian bound above a planted fleet (%s)" % var)
                    if lam is not None:
                        self.assertTrue(M.verify(I, a, b, k2, lam, var))
                        self.assertFalse(M.verify(I, a, b, K + 1, lam, var))
        return res

    def test_planted_narrow(self):
        for seed in range(10):
            inst, K = planted(3, 6, seed, slack=(0, 4))
            self.check_inst(inst, K)

    def test_planted_wide(self):
        for seed in range(10):
            inst, K = planted(2, 8, 100 + seed, slack=(10, 200))
            self.check_inst(inst, K)

    def test_planted_tight_day(self):
        # no waiting, no slack, the day ends with the last return: the bound should usually reach K
        hits = 0
        for seed in range(10):
            inst, K = planted(4, 5, 200 + seed, slack=(0, 0), wait=(0, 0), extra=(0, 0), service=(1, 1))
            res = self.check_inst(inst, K)
            hits += res["best_K"] >= 2
        self.assertGreaterEqual(hits, 1)

    def test_against_exact(self):
        rng = random.Random(7)
        done = 0
        for seed in range(60):
            n = rng.randint(3, 7)
            span = 60
            H = rng.randint(80, 220)
            rows = [(30, 30, 0, 0, H, 0)]
            for _ in range(n):
                x, y = rng.randint(0, span), rng.randint(0, span)
                t0 = rint(math.hypot(x - 30, y - 30))
                s = rng.randint(1, 15)
                lo, hi = t0, H - s - t0
                if hi < lo:
                    break
                a = rng.randint(lo, hi)
                b = min(hi, a + rng.randint(0, 60))
                rows.append((x, y, 1, a, b, s))
            if len(rows) != n + 1:
                continue
            inst = make(rows)
            opt = exact_fleet(inst)
            I = M.Inst(inst)
            res = M.bound_instance(I, budget=1.0, grid=8, say=lambda *_: None)
            self.assertLessEqual(res["best_K"], opt, "bound %d above the exact fleet %d" % (res["best_K"], opt))
            done += 1
        self.assertGreaterEqual(done, 30)

    def test_verify_rejects_overclaim_and_bad_variant(self):
        inst, K = planted(3, 6, 5, slack=(0, 4))
        I = M.Inst(inst)
        self.assertFalse(M.verify(I, I.D0, I.B0, K + 3, None, "full"))
        mid = float(np.median(I.e))
        t2 = float(I.f.max())
        if t2 > mid and M.variant_of(I, mid, t2) == "free":
            self.assertFalse(M.verify(I, mid, t2, 2, None, "start"))
            with self.assertRaises(ValueError):
                M.hk_bound(I, mid, t2, 1, float("inf"), variant="start")
        self.assertFalse(M.verify(I, I.D0, I.B0, 2, [-1] * I.n, "full"))


class TestHarness(unittest.TestCase):
    def test_tally_and_md(self):
        recs = [{"instance": "XLTW-Test-n1048", "customers": 5, "kstar": 3, "bound": 4, "plain_K": 3, "ub": 9,
                 "source": "hk", "verified": True, "above_kstar": True, "above_ub": False, "proved": False,
                 "gap_closed": 0.1667, "seconds": 1.0, "peak_gb": 0.1,
                 "plain": {"t1": 0.0, "t2": 9.0, "m": 5, "variant": "free", "K": 3},
                 "profile": {"width_q10_25_50_75_90": [0, 0, 0.3, 0, 0]}},
                {"instance": "XLTW-Test-n1234", "error": "x"}]
        t = M.tally(recs)
        self.assertEqual(t["above_kstar"], ["XLTW-Test-n1048"])
        self.assertEqual(t["service1_above_kstar"], ["XLTW-Test-n1048"])
        self.assertEqual(t["hk_gain"], ["XLTW-Test-n1048"])
        self.assertEqual(t["n1048_bound"], 4)
        self.assertEqual(t["sum_max"], 4)
        self.assertEqual(t["median_width_median"], 0.3)
        self.assertEqual(t["errors"], ["XLTW-Test-n1234"])
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.md")
            M.write_md(p, {"tally": t, "instances": recs})
            with open(p, encoding="utf-8") as f:
                self.assertIn("XLTW-Test-n1048", f.read())
        json.dumps(t)

    def test_profile(self):
        inst, K = planted(2, 5, 3)
        p = M.profile(M.Inst(inst))
        self.assertEqual(len(p["width_q10_25_50_75_90"]), 5)
        self.assertGreater(p["horizon"], 0)


if __name__ == "__main__":
    unittest.main()
