"""Tests for stfleet.py (numpy and scipy needed; mstfleet.py 0.1.0 must sit next to it, xltwlb.py is not needed).
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
import stfleet as S  # noqa: E402


def rint(d):
    """The challenge's travel time: nearest integer, ties up."""
    return math.floor(d + 0.5)


def make(rows, cap=10 ** 9, name="T"):
    return {"name": name, "capacity": cap, "rows": [tuple(r) for r in rows]}


def planted(K, per_route, seed, slack=(0, 30), span=100, service=(1, 6), wait=(0, 8), extra=(0, 40)):
    """An instance that K routes serve by construction (official rounding, waiting allowed): min fleet <= K."""
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
    _, _, _, a0, b0, s0 = rows[0]

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


def random_small(rng, n, H, span=60, width=60, smax=15):
    rows = [(30, 30, 0, 0, H, 0)]
    for _ in range(n):
        x, y = rng.randint(0, span), rng.randint(0, span)
        t0 = rint(math.hypot(x - 30, y - 30))
        s = rng.randint(1, smax)
        lo, hi = t0, H - s - t0
        if hi < lo:
            return None
        a = rng.randint(lo, hi)
        b = min(hi, a + rng.randint(0, width))
        rows.append((x, y, 1, a, b, s))
    return make(rows)


def every_interval_bound(test, I, K, lam_iters=15):
    """Every grid interval, both sides, several mu, with and without lam: never above K, certificates verify."""
    T1 = M.grid_points(I.e, 6, [I.D0])
    T2 = M.grid_points(I.f, 6, [I.B0])
    for a in T1:
        for b in T2:
            if b <= a:
                continue
            for side in S.SIDES:
                sub = S.Sub(I, a, b, side)
                if sub.m == 0:
                    continue
                for r in (0.2, 0.5, 1.0, 1.5, 3.0):
                    mu = max(1, int(round(sub.mu0 * r)))
                    ev = S.evaluate(sub, mu)
                    test.assertLessEqual(ev["K"], K, "bound above the fleet (side %s, mu %d)" % (side, mu))
                    c = {"t1": a, "t2": b, "side": side, "mu": mu, "lam": None, "K": ev["K"]}
                    test.assertTrue(S.verify(I, c))
                    c["K"] = ev["K"] + 1
                    test.assertFalse(S.verify(I, c))
                k2, lam, its = S.hk(sub, sub.mu0, 1, deadline=float("inf"), iters=lam_iters)
                test.assertLessEqual(k2, K, "Lagrangian bound above the fleet (%s)" % side)
                if lam is not None:
                    c = {"t1": a, "t2": b, "side": side, "mu": sub.mu0, "lam": lam, "K": k2}
                    test.assertTrue(S.verify(I, c))


class TestPrim(unittest.TestCase):
    def dense(self, sub, mu, lam):
        """Independent weight matrix (python loops, official rounding) and scipy's MST."""
        from scipy.sparse.csgraph import minimum_spanning_tree
        m = sub.m
        N = m + 1
        W = np.zeros((N, N))
        for i in range(m):
            for j in range(m):
                if i == j:
                    continue
                t = rint(math.hypot(sub.xy[i, 0] - sub.xy[j, 0], sub.xy[i, 1] - sub.xy[j, 1]))
                dij = max(t, sub.e[j] - sub.f[i]) if sub.e[i] + sub.s[i] + t <= sub.l[j] else S.BIG
                dji = max(t, sub.e[i] - sub.f[j]) if sub.e[j] + sub.s[j] + t <= sub.l[i] else S.BIG
                W[i, j] = min(dij, dji) + lam[i] + lam[j]
            W[i, m] = W[m, i] = sub.c[i] + mu + lam[i]
        shift = 1.0 - min(0.0, float(W.min()))
        D = W + shift
        np.fill_diagonal(D, 0.0)
        T = minimum_spanning_tree(D)
        return int(round(float(T.sum()) - shift * (N - 1)))

    def test_against_scipy(self):
        rng = random.Random(3)
        done = 0
        for trial in range(40):
            inst = random_small(rng, rng.randint(2, 18), rng.randint(120, 400), width=rng.choice([5, 40, 300]))
            if inst is None:
                continue
            I = M.Inst(inst)
            if I.unservable:
                continue
            t1 = float(I.D0) if trial % 3 else float(np.median(I.e))
            t2 = float(I.B0)
            for side in S.SIDES:
                sub = S.Sub(I, t1, t2, side)
                if sub.m < 2:
                    continue
                lam = np.array([rng.randint(0, 5) if trial % 2 else 0 for _ in range(sub.m)], dtype=float)
                for mu in (1, sub.mu0, 3 * sub.mu0 + 7):
                    tot, rd, deg = S.st_prim(sub, mu, lam)
                    self.assertEqual(tot, self.dense(sub, mu, lam))
                    self.assertGreaterEqual(rd, 1)
                    self.assertEqual(int(deg.sum()), 2 * sub.m - rd)
                done += 1
        self.assertGreaterEqual(done, 20)

    def test_fleet_from(self):
        self.assertEqual(S.fleet_from(10, 5), 2)
        self.assertEqual(S.fleet_from(11, 5), 3)
        self.assertEqual(S.fleet_from(-4, 5), 1)
        self.assertEqual(S.fleet_from(0, 5), 1)


class TestValidity(unittest.TestCase):
    def test_against_exact(self):
        rng = random.Random(11)
        done = 0
        for seed in range(90):
            n = rng.randint(3, 7)
            inst = random_small(rng, n, rng.randint(80, 220), width=rng.choice([0, 10, 60, 200]))
            if inst is None:
                continue
            I = M.Inst(inst)
            if I.unservable:
                continue
            opt = exact_fleet(inst)
            every_interval_bound(self, I, opt, lam_iters=10)
            res = S.bound_instance(I, budget=1.0, grid=8, say=lambda *_: None)
            self.assertLessEqual(res["best_K"], opt, "bound %d above the exact fleet %d" % (res["best_K"], opt))
            self.assertTrue(res["verified"])
            done += 1
        self.assertGreaterEqual(done, 40)

    def test_planted_narrow(self):
        for seed in range(8):
            inst, K = planted(3, 6, seed, slack=(0, 4))
            I = M.Inst(inst)
            every_interval_bound(self, I, K)
            res = S.bound_instance(I, budget=2.0, grid=8, say=lambda *_: None)
            self.assertLessEqual(res["best_K"], K)
            self.assertTrue(res["verified"])

    def test_planted_wide(self):
        for seed in range(8):
            inst, K = planted(2, 8, 100 + seed, slack=(10, 200))
            I = M.Inst(inst)
            every_interval_bound(self, I, K)
            res = S.bound_instance(I, budget=2.0, grid=8, say=lambda *_: None)
            self.assertLessEqual(res["best_K"], K)

    def test_planted_tight_zero_wait(self):
        hits = 0
        for seed in range(8):
            inst, K = planted(4, 5, 200 + seed, slack=(0, 0), wait=(0, 0), extra=(0, 0), service=(1, 1))
            I = M.Inst(inst)
            every_interval_bound(self, I, K)
            res = S.bound_instance(I, budget=2.0, grid=8, say=lambda *_: None)
            self.assertLessEqual(res["best_K"], K)
            hits += res["best_K"] >= 2
        self.assertGreaterEqual(hits, 1)

    def test_waiting_proves_four_corners(self):
        # four customers at the corners of a 100 x 100 square, all to be served exactly at time 80: four vehicles
        # are needed. Plain travel cannot show it; the order rule (neither order fits) does.
        rows = [(50, 50, 0, 0, 200, 0)] + [(x, y, 1, 80, 80, 1) for x in (0, 100) for y in (0, 100)]
        inst = make(rows)
        self.assertEqual(exact_fleet(inst), 4)
        I = M.Inst(inst)
        sub = S.Sub(I, I.D0, I.B0, "start")
        for mu in (1, 5, sub.mu0, 1000):
            self.assertEqual(S.evaluate(sub, mu)["K"], 4)
        res = S.bound_instance(I, budget=1.0, grid=4, say=lambda *_: None)
        self.assertEqual(res["best_K"], 4)
        self.assertTrue(res["verified"])
        self.assertLess(S.v01_whole_day(I), 4)

    def test_waiting_same_place(self):
        # five customers at one point, windows 40 apart: one vehicle serves them all, but its day is mostly waiting.
        # With a day just long enough for one vehicle the bound must stay at 1, and with the whole wait it is exact.
        rows = [(50, 50, 0, 0, 260, 0)] + [(60, 50, 1, 20 + 40 * k, 20 + 40 * k, 1) for k in range(5)]
        inst = make(rows)
        self.assertEqual(exact_fleet(inst), 1)
        I = M.Inst(inst)
        res = S.bound_instance(I, budget=1.0, grid=6, say=lambda *_: None)
        self.assertEqual(res["best_K"], 1)
        every_interval_bound(self, I, 1)

    def test_dominates_v01_whole_day_rooted(self):
        rng = random.Random(5)
        done = 0
        for seed in range(40):
            inst = random_small(rng, rng.randint(5, 40), rng.randint(150, 400), width=rng.choice([10, 80, 400]))
            if inst is None:
                continue
            I = M.Inst(inst)
            if I.unservable:
                continue
            Sset = M.interval_set(I, I.D0, I.B0)
            L = I.B0 - I.D0
            Wv = float(I.s[Sset].sum())
            tot0, _, _, _ = M.prim(I.xy[Sset], root=I.depot)
            r = float(I.t0[Sset].min())
            if L <= r:
                continue
            k_full = math.ceil((Wv + tot0) / (L - r) - 1e-9)
            sub = S.Sub(I, I.D0, I.B0, "start")
            self.assertGreaterEqual(S.evaluate(sub, sub.mu0)["K"], k_full)
            done += 1
        self.assertGreaterEqual(done, 20)

    def test_verify_rejects_bad_certificates(self):
        inst, K = planted(3, 6, 5, slack=(0, 4))
        I = M.Inst(inst)
        sub = S.Sub(I, I.D0, I.B0, "start")
        good = {"t1": I.D0, "t2": I.B0, "side": "start", "mu": sub.mu0, "lam": None, "K": 1}
        self.assertTrue(S.verify(I, good))
        self.assertFalse(S.verify(I, dict(good, K=K + 5)))
        self.assertFalse(S.verify(I, dict(good, K=2, mu=0)))
        self.assertFalse(S.verify(I, dict(good, K=2, mu=2.5)))
        self.assertFalse(S.verify(I, dict(good, K=2, side="middle")))
        self.assertFalse(S.verify(I, dict(good, K=2, lam=[-1] * sub.m)))
        self.assertFalse(S.verify(I, dict(good, K=2, lam=[0] * (sub.m + 1))))
        with self.assertRaises(ValueError):
            S.Sub(I, I.D0, I.B0, "middle")


class TestHarness(unittest.TestCase):
    def test_tally_and_md(self):
        recs = [{"instance": "XLTW-Test-n1048", "customers": 5, "kstar": 3, "bound": 5, "K_before_lam": 4, "ub": 9,
                 "source": "hk", "verified": True, "above_kstar": True, "above_ub": False, "proved": False,
                 "above_v01_whole_day": True, "v01_whole_day": 3, "best_is_whole_day": False,
                 "best_side": "end", "gap_closed": 0.3333, "seconds": 1.0, "peak_gb": 0.1,
                 "cert": {"t1": 0.0, "t2": 9.0, "side": "end", "mu": 7, "m": 5},
                 "profile": {"width_q10_25_50_75_90": [0, 0, 0.3, 0, 0]}},
                {"instance": "XLTW-Test-n1234", "error": "x"}]
        t = S.tally(recs)
        self.assertEqual(t["above_kstar"], ["XLTW-Test-n1048"])
        self.assertEqual(t["service1_above_kstar"], ["XLTW-Test-n1048"])
        self.assertEqual(t["hk_gain"], ["XLTW-Test-n1048"])
        self.assertEqual(t["above_v01_whole_day"], ["XLTW-Test-n1048"])
        self.assertEqual(t["best_not_whole_day"], ["XLTW-Test-n1048"])
        self.assertEqual(t["best_side_end"], ["XLTW-Test-n1048"])
        self.assertEqual(t["n1048_bound"], 5)
        self.assertEqual(t["sum_max"], 5)
        self.assertEqual(t["sum_v01_whole_day"], 3)
        self.assertEqual(t["errors"], ["XLTW-Test-n1234"])
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.md")
            S.write_md(p, {"tally": t, "instances": recs})
            with open(p, encoding="utf-8") as fh:
                self.assertIn("XLTW-Test-n1048", fh.read())
        json.dumps(t)


if __name__ == "__main__":
    unittest.main()
