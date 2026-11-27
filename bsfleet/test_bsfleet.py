"""Tests for bsfleet: every stretch bound must stay at or below the exact minimum fleet of the whole instance.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.
"""
import math
import random
import unittest

import numpy as np

import bsfleet as BS
import mstfleet as M
import ngfleet as N

FAST = dict(budget_fn=lambda m: 4.0, final_s=3.0)


def tt(p, q):
    """The challenge's travel time: nearest integer of the Euclidean distance (ties up)."""
    return math.floor(math.hypot(p[0] - q[0], p[1] - q[1]) + 0.5)


def exact_fleet(rows):
    """Exact minimum number of vehicles (capacity ignored) by DP over subsets, rows[0] = depot (x, y, q, a, b, s)."""
    n = len(rows) - 1
    dep = rows[0]
    D0, B0 = dep[3] + dep[5], dep[4]
    INF = float("inf")
    full = 1 << n
    fin = [[INF] * n for _ in range(full)]
    for j in range(n):
        c = rows[j + 1]
        st = max(D0 + tt(dep, c), c[3])
        if st <= c[4]:
            fin[1 << j][j] = st + c[5]
    for mask in range(1, full):
        for i in range(n):
            f = fin[mask][i]
            if f == INF:
                continue
            for j in range(n):
                if mask >> j & 1:
                    continue
                c = rows[j + 1]
                st = max(f + tt(rows[i + 1], c), c[3])
                if st <= c[4] and st + c[5] < fin[mask | 1 << j][j]:
                    fin[mask | 1 << j][j] = st + c[5]
    ok = [False] * full
    for mask in range(1, full):
        ok[mask] = any(fin[mask][i] + tt(rows[i + 1], dep) <= B0 for i in range(n) if fin[mask][i] < INF)
    best = [INF] * full
    best[0] = 0
    for mask in range(1, full):
        low = mask & -mask
        sub = mask
        while sub:
            if sub & low and ok[sub] and best[mask ^ sub] + 1 < best[mask]:
                best[mask] = best[mask ^ sub] + 1
            sub = (sub - 1) & mask
    return best[full - 1]


def rand_rows(rng, n, horizon=160):
    rows = [(15, 15, 0, 0, horizon, 0)]
    for _ in range(n):
        x, y = rng.randint(0, 30), rng.randint(0, 30)
        a = rng.randint(0, 70)
        w = rng.choice([0, 3, 8, 20, 60])
        rows.append((x, y, 1, a, a + w, rng.randint(1, 6)))
    return rows


def inst_of(rows):
    return M.Inst({"rows": rows, "capacity": 10 ** 6, "name": "t"})


class TestBsfleet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # compile the numba kernel once, so the short test budgets are not spent compiling
        I = inst_of(rand_rows(random.Random(0), 5))
        C, e, l = BS.sub_arrays(I, np.arange(I.n))
        N.price_ng(C, e, l, np.ones(I.n, dtype=np.int64), L_max=10)
    def test_sub_arrays(self):
        rows = rand_rows(random.Random(1), 6)
        I = inst_of(rows)
        S = np.array([0, 2, 5])
        C, e, l = BS.sub_arrays(I, S)
        for a, i in enumerate(S):
            for b, j in enumerate(S):
                if a != b:
                    want = rows[i + 1][5] + math.floor(math.hypot(rows[i + 1][0] - rows[j + 1][0],
                                                                  rows[i + 1][1] - rows[j + 1][1]) + 0.5 - 1e-9)
                    self.assertEqual(C[a, b], want)
            self.assertEqual(e[a], I.e[i])
            self.assertEqual(l[a], I.l[i])

    def test_greedy_is_a_cover(self):
        rng = random.Random(2)
        for _ in range(20):
            I = inst_of(rand_rows(rng, 9))
            if I.unservable:
                continue
            S = np.arange(I.n)
            C, e, l = BS.sub_arrays(I, S)
            routes = BS.greedy_routes(C, e, l)
            self.assertEqual(sorted(x for r in routes for x in r), list(range(I.n)))
            for r in routes:
                self.assertTrue(N.walk_time_ok(C, e, l, r))

    def test_incompatible_customers(self):
        # four customers that must all start at exactly t = 50: no vehicle can serve two of them
        rows = [(0, 0, 0, 0, 200, 0)] + [(x, y, 1, 50, 50, 1) for x, y in ((10, 0), (0, 10), (-10, 0), (0, -10))]
        I = inst_of(rows)
        self.assertEqual(exact_fleet(rows), 4)
        rec, cert = BS.bound_stretch(I, I.D0, I.B0, **FAST)
        self.assertEqual(rec["bound"], 4)
        self.assertTrue(rec["solved"])
        self.assertFalse(rec["unverified"])
        self.assertEqual(cert["fleet_at_least"], 4)
        self.assertEqual(cert["customers_1based"], [1, 2, 3, 4])

    def test_never_above_exact_fleet(self):
        rng = random.Random(20261127)
        checked = 0
        tight = 0
        for trial in range(14):
            rows = rand_rows(rng, rng.randint(5, 8))
            I = inst_of(rows)
            if I.unservable or I.service_min < 1:
                continue
            k = exact_fleet(rows)
            if k == math.inf:
                continue
            vals = sorted(set(I.e.tolist()) | set(I.f.tolist()))
            cand = [(I.D0, I.B0)]
            for _ in range(3):
                a, b = sorted(rng.sample(vals, 2)) if len(vals) >= 2 else (I.D0, I.B0)
                cand.append((a, b))
            for t1, t2 in cand:
                if len(M.interval_set(I, t1, t2)) < 2:
                    continue
                rec, cert = BS.bound_stretch(I, t1, t2, **FAST)
                self.assertFalse(rec["unverified"], (trial, t1, t2, rec))
                self.assertTrue(rec["greedy_ok"])
                self.assertIsNotNone(rec["bound"])
                self.assertLessEqual(rec["bound"], k, (trial, t1, t2, rec, rows))
                self.assertLessEqual(rec["bound"], rec["greedy"])
                checked += 1
                tight += int(rec["bound"] == k)
        self.assertGreaterEqual(checked, 15)
        self.assertGreaterEqual(tight, 1)

    def test_stretches_and_plan(self):
        rows = rand_rows(random.Random(3), 6)
        I = inst_of(rows)
        rec = {"instance": "A", "customers": 6, "bound": 3,
               "cert": {"t1": 1.0, "t2": 9.0, "m": 4},
               "refined": [{"t1": 1.0, "t2": 9.0, "m": 4, "K_scan": 2, "K_mu": 3, "K_hk": 3},
                           {"t1": 2.0, "t2": 8.0, "m": 3, "K_scan": 2, "K_mu": 2, "K_hk": None},
                           {"t1": 0.0, "t2": 99.0, "m": 5000, "K_scan": 9, "K_mu": 9, "K_hk": 9}],
               "whole_day": [{"K": 1}, {"K": 2}]}
        s = BS.stretches(rec, I, m_max=1500, k=3)
        self.assertEqual([(x["t1"], x["t2"], x["from"]) for x in s],
                         [(1.0, 9.0, "cert"), (I.D0, I.B0, "whole_day"), (2.0, 8.0, "refined")])
        self.assertEqual(s[0]["K_stfleet"], 3)
        self.assertEqual(s[1]["K_stfleet"], 2)
        self.assertEqual(s[2]["K_stfleet"], 2)
        self.assertEqual(len(BS.stretches(rec, I)), 2)
        big = {"instance": "B", "customers": 9000, "cert": {"t1": 0, "t2": 5, "m": 4000}, "refined": []}
        err = {"instance": "C", "error": "x"}
        self.assertEqual(BS.plan({"instances": [big, rec, err]}), ["A"])


if __name__ == "__main__":
    unittest.main()
