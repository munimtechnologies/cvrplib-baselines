"""Tests for stcheck (independent re-check of the stfleet fleet bounds).

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.
"""
import itertools
import math
import random
import unittest

import numpy as np

import stcheck as C


def exact_fleet(rows):
    """Exact minimum number of routes (capacity-free VRPTW, rounded Euclidean times, time = distance), by subset DP
    over the raw (untightened) data: depart the depot at a0 + s0, wait for each window, return by b0."""
    n = len(rows) - 1
    x0, y0, _, a0, b0, s0 = rows[0]

    def tt(i, j):
        return C.rtravel1(rows[i][0] - rows[j][0], rows[i][1] - rows[j][1])

    D0, B0 = a0 + s0, b0
    full = 1 << n
    BIG = float("inf")
    dp = [[BIG] * n for _ in range(full)]
    for j in range(n):
        st = max(D0 + tt(0, j + 1), rows[j + 1][3])
        if st <= rows[j + 1][4]:
            dp[1 << j][j] = st + rows[j + 1][5]
    for mask in range(1, full):
        for j in range(n):
            v = dp[mask][j]
            if v == BIG:
                continue
            for k in range(n):
                if mask >> k & 1:
                    continue
                st = max(v + tt(j + 1, k + 1), rows[k + 1][3])
                if st <= rows[k + 1][4]:
                    nm = mask | (1 << k)
                    if st + rows[k + 1][5] < dp[nm][k]:
                        dp[nm][k] = st + rows[k + 1][5]
    feas = [False] * full
    for mask in range(1, full):
        feas[mask] = any(dp[mask][j] + tt(j + 1, 0) <= B0 for j in range(n) if mask >> j & 1)
    best = [BIG] * full
    best[0] = 0
    for mask in range(1, full):
        low = mask & -mask
        sub = mask
        while sub:
            if sub & low and feas[sub] and best[mask ^ sub] + 1 < best[mask]:
                best[mask] = best[mask ^ sub] + 1
            sub = (sub - 1) & mask
    return best[full - 1]


def random_rows(rng, n, H=400):
    """A random servable tiny instance: depot (50, 50) open [0, H], service 1..12, windows of random width."""
    while True:
        rows = [(50, 50, 0, 0, H, 0)]
        for _ in range(n):
            x, y = rng.randint(0, 100), rng.randint(0, 100)
            s = rng.randint(1, 12)
            t0 = C.rtravel1(x - 50, y - 50)
            lo, hi = t0, H - s - t0
            if hi <= lo:
                continue
            a = rng.randint(lo, hi)
            width = rng.choice([0, 5, 20, 60, 150, 400])
            b = min(hi, a + width)
            rows.append((x, y, 1, a, b, s))
        if len(rows) == n + 1:
            try:
                C.Inst(rows)
                return rows
            except ValueError:
                continue


def kruskal_total(I, S, t1, t2, side, mu, lam):
    """Brute-force MST over S + root from an explicitly built edge list (pure python)."""
    m = len(S)
    e = [int(I.e[i]) for i in S]
    l = [int(I.l[i]) for i in S]
    s = [int(I.s[i]) for i in S]
    f = [int(I.f[i]) for i in S]
    xs = [int(I.x[i]) for i in S]
    ys = [int(I.y[i]) for i in S]
    L = t2 - t1
    a = [ei - t1 for ei in e]
    b = [t2 - fi for fi in f]
    edges = []
    for i in range(m):
        root = (a[i] + min(b) - L) if side == "start" else (b[i] + min(a) - L)
        edges.append((root + mu + lam[i], i, m))
        for j in range(i + 1, m):
            t = C.rtravel1(xs[i] - xs[j], ys[i] - ys[j])
            opts = []
            if e[i] + s[i] + t <= l[j]:
                opts.append(max(t, e[j] - f[i]))
            if e[j] + s[j] + t <= l[i]:
                opts.append(max(t, e[i] - f[j]))
            if opts:
                edges.append((min(opts) + lam[i] + lam[j], i, j))
    par = list(range(m + 1))

    def find(u):
        while par[u] != u:
            par[u] = par[par[u]]
            u = par[u]
        return u

    total = 0
    for w, u, v in sorted(edges):
        ru, rv = find(u), find(v)
        if ru != rv:
            par[ru] = rv
            total += w
    return total


class TravelTest(unittest.TestCase):
    def test_exact_rounding(self):
        rng = random.Random(1)
        dx = [rng.randint(-(1 << 23), 1 << 23) for _ in range(3000)] + [0, 1, 3, 7, 1000]
        dy = [rng.randint(-(1 << 23), 1 << 23) for _ in range(3000)] + [0, 1, 4, 24, 0]
        r = C.rtravel(np.array(dx), np.array(dy))
        for i in range(len(dx)):
            D4 = 4 * (dx[i] ** 2 + dy[i] ** 2)
            ri = int(r[i])
            self.assertLessEqual((2 * ri - 1) ** 2, D4) if ri > 0 else None
            self.assertLess(D4, (2 * ri + 1) ** 2)
            self.assertEqual(ri, C.rtravel1(dx[i], dy[i]))
        self.assertEqual([int(v) for v in r[-5:]], [0, 1, 5, 25, 1000])

    def test_matches_float_rounding_small(self):
        for dx in range(0, 60):
            for dy in range(0, 60):
                self.assertEqual(C.rtravel1(dx, dy), math.floor(math.hypot(dx, dy) + 0.5))


class ParseTest(unittest.TestCase):
    TEXT = """NAME : tiny
TYPE : VRPTW
DIMENSION : 3
CAPACITY : 10
EDGE_WEIGHT_TYPE : EUC_2D
NODE_COORD_SECTION
1 0 0
2 3 4
3 6 8
DEMAND_SECTION
1 0
2 1
3 2
TIME_WINDOW_SECTION
1 0 100
2 10 20
3 5 50
SERVICE_TIME_SECTION
1 0
2 2
3 3
DEPOT_SECTION
1
-1
EOF
"""

    def test_parse(self):
        p = C.parse(self.TEXT)
        self.assertEqual(p["capacity"], 10)
        self.assertEqual(p["rows"], [(0, 0, 0, 0, 100, 0), (3, 4, 1, 10, 20, 2), (6, 8, 2, 5, 50, 3)])
        I = C.Inst(p["rows"])
        self.assertEqual([int(v) for v in I.e], [10, 10])   # max(10, 0 + 5); max(5, 0 + 10)
        self.assertEqual([int(v) for v in I.l], [20, 50])   # min(20, 100 - 2 - 5); min(50, 100 - 3 - 10)
        self.assertEqual([int(v) for v in I.f], [22, 53])

    def test_refuses_non_integral(self):
        with self.assertRaises(ValueError):
            C.parse(self.TEXT.replace("2 3 4", "2 3.5 4"))

    def test_refuses_zero_service(self):
        rows = C.parse(self.TEXT)["rows"]
        rows[1] = rows[1][:5] + (0,)
        with self.assertRaises(ValueError):
            C.Inst(rows)


def grid_params(I, rng):
    t1s = sorted({I.D0} | {int(v) for v in I.e})
    t2s = sorted({I.B0} | {int(v) for v in I.f})
    for t1 in t1s:
        for t2 in t2s:
            if t2 <= t1:
                continue
            S = C.subset(I, t1, t2)
            if len(S) == 0:
                continue
            L = t2 - t1
            for side in ("start", "end"):
                for mu in sorted({1, 2, 3, 5, 8, 13, 21, 40, max(1, L // 3), max(1, L // 2), L, L + 7,
                                  10 ** 3, 10 ** 4, 10 ** 6}):
                    yield t1, t2, side, mu, S, [0] * len(S)
                    yield t1, t2, side, mu, S, [rng.randint(0, 4) for _ in S]


class BoundTest(unittest.TestCase):
    def test_prim_equals_kruskal(self):
        rng = random.Random(7)
        cases = 0
        for _ in range(25):
            I = C.Inst(random_rows(rng, rng.randint(2, 7)))
            for t1, t2, side, mu, S, lam in itertools.islice(grid_params(I, rng), 0, None, 7):
                N = C.n_value(I, S, t1, t2, side, mu, lam)
                kt = kruskal_total(I, S, t1, t2, side, mu, lam)
                self.assertEqual(N, kt - 2 * sum(lam) + int(I.s[S].sum()))
                cases += 1
        self.assertGreater(cases, 200)

    def test_never_above_exact_fleet(self):
        rng = random.Random(11)
        checked, tight = 0, 0
        for it in range(70):
            n = rng.randint(3, 7)
            rows = random_rows(rng, n, H=rng.choice([150, 250, 400]))
            I = C.Inst(rows)
            opt = exact_fleet(rows)
            self.assertLess(opt, float("inf"))
            for t1, t2, side, mu, S, lam in grid_params(I, rng):
                N = C.n_value(I, S, t1, t2, side, mu, lam)
                k = C.proves(N, mu)
                self.assertLessEqual(k, opt, (rows, t1, t2, side, mu, lam, N, k, opt))
                checked += 1
                tight += (k == opt and opt > 1)
        self.assertGreater(checked, 3000)
        self.assertGreater(tight, 0)   # the bound is not vacuous on these tiny instances

    def test_certificate_check(self):
        rng = random.Random(3)
        for _ in range(20):
            I = C.Inst(random_rows(rng, 6))
            t1, t2 = I.D0, I.B0
            S = C.subset(I, t1, t2)
            mu = max(1, (t2 - t1) // 2)
            lam = [rng.randint(0, 3) for _ in S]
            N = C.n_value(I, S, t1, t2, "start", mu, lam)
            k = C.proves(N, mu)
            ok = C.check(I, {"t1": float(t1), "t2": float(t2), "side": "start", "mu": mu, "lam": lam, "K": k})
            self.assertTrue(ok["confirmed"], ok)
            bad = C.check(I, {"t1": t1, "t2": t2, "side": "start", "mu": mu, "lam": lam, "K": k + 1})
            self.assertFalse(bad["confirmed"], bad)
            self.assertFalse(C.check(I, {"t1": t1, "t2": t2, "side": "start", "mu": 1.5, "lam": lam,
                                         "K": 1})["confirmed"])
            self.assertFalse(C.check(I, {"t1": t1, "t2": t2, "side": "start", "mu": mu, "lam": lam + [0],
                                         "K": 1})["confirmed"])
            neg = list(lam)
            neg[0] = -1
            self.assertFalse(C.check(I, {"t1": t1, "t2": t2, "side": "start", "mu": mu, "lam": neg,
                                         "K": 1})["confirmed"])
            self.assertFalse(C.check(I, {"t1": t1, "t2": t2, "side": "middle", "mu": mu, "lam": lam,
                                         "K": 1})["confirmed"])


if __name__ == "__main__":
    unittest.main()
