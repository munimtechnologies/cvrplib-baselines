"""Tests for xtwfleet.py. Need mstfleet.py, stfleet.py, cgfleet.py, tmatch.py and xltwlb.py next to this file (the
job's setup fetches them). MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0."""
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

import tmatch as TM  # noqa: E402
import xtwfleet as XF  # noqa: E402


def make(rows, cap, name="XTW-n7"):
    return {"name": name, "vehicles": None, "capacity": cap, "rows": [tuple(r) for r in rows],
            "raw": [tuple(str(v) for v in r) for r in rows]}


def rint(d):
    return math.floor(d + 0.5)


def random_cap_instance(n, seed, width=(10, 60), service=(1, 8), horizon=200, span=40, name=None):
    rng = random.Random(seed)
    c = span // 2
    rows = [(c, c, 0, 0, horizon, 0)]
    for _ in range(n):
        x, y = rng.randint(0, span), rng.randint(0, span)
        t0 = rint(math.hypot(x - c, y - c))
        s = rng.randint(*service)
        w = rng.randint(*width)
        a = rng.randint(t0, horizon - s - t0 - w)
        rows.append((x, y, rng.randint(1, 10), a, a + w, s))
    tot = sum(r[2] for r in rows[1:])
    cap = rng.randint(max(r[2] for r in rows[1:]), tot)
    return make(rows, cap, name or "XTW-n%d" % (n + 1))


def feasible_order(inst, order):
    """Plain simulation of one route with capacity (independent of the code under test)."""
    rows = inst["rows"]
    if sum(rows[c][2] for c in order) > inst["capacity"]:
        return False
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


def route_table(inst):
    n = len(inst["rows"]) - 1
    ok = [False] * (1 << n)
    for mask in range(1, 1 << n):
        members = [i + 1 for i in range(n) if mask >> i & 1]
        ok[mask] = any(feasible_order(inst, p) for p in itertools.permutations(members))
    return ok


def brute_min_fleet(inst, ok=None):
    n = len(inst["rows"]) - 1
    ok = ok or route_table(inst)
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


def best_route_profit(inst, pi, ok):
    n = len(inst["rows"]) - 1
    return max([sum(pi[i] for i in range(n) if mask >> i & 1) for mask in range(1, 1 << n) if ok[mask]] or [0])


def write_vrp(path, inst):
    rows = inst["rows"]
    text = ["NAME : %s" % inst["name"], "COMMENT : test", "TYPE : VRPTW", "DIMENSION : %d" % len(rows),
            "EDGE_WEIGHT_TYPE : EUC_2D", "CAPACITY : %d" % inst["capacity"], "NODE_COORD_SECTION"]
    text += ["%d %d %d" % (i + 1, r[0], r[1]) for i, r in enumerate(rows)]
    text += ["DEMAND_SECTION"] + ["%d %d" % (i + 1, r[2]) for i, r in enumerate(rows)]
    text += ["SERVICE_TIME_SECTION"] + ["%d %d" % (i + 1, r[5]) for i, r in enumerate(rows)]
    text += ["TIME_WINDOW_SECTION"] + ["%d %d %d" % (i + 1, r[3], r[4]) for i, r in enumerate(rows)]
    text += ["DEPOT_SECTION", "1", "-1", "EOF"]
    with open(path, "w") as f:
        f.write("\n".join(text) + "\n")


class TestSolutions(unittest.TestCase):
    def test_rint_dist(self):
        self.assertEqual(XF.rint_dist(0, 0, 3, 4), 5)
        self.assertEqual(XF.rint_dist(0, 0, 1, 1), 1)
        self.assertEqual(XF.rint_dist(0, 0, 1, 2), 2)
        self.assertEqual(XF.rint_dist(0, 0, 2, 3), 4)
        rng = random.Random(5)
        for _ in range(3000):
            a = [rng.randint(-1000, 1000) for _ in range(4)]
            self.assertEqual(XF.rint_dist(*a), rint(math.hypot(a[0] - a[2], a[1] - a[3])))

    def test_parse_sol(self):
        r, c = XF.parse_sol("Route #1: 1 2\nRoute #2: 3\nRoute #3:\nCost 123\n")
        self.assertEqual(r, [[1, 2], [3]])
        self.assertEqual(c, 123.0)
        r, c = XF.parse_sol("Route #1: 4\n")
        self.assertEqual((r, c), ([[4]], None))

    def test_check_sol(self):
        rows = [(0, 0, 0, 0, 100, 0), (3, 4, 2, 0, 50, 1), (6, 8, 3, 10, 20, 1)]
        inst = make(rows, 5)
        ok = XF.check_sol(inst, [[1, 2]])
        self.assertTrue(ok["ok"], ok)
        self.assertEqual(ok["cost"], 20)
        self.assertEqual(ok["vehicles"], 1)
        self.assertFalse(XF.check_sol(make(rows, 4), [[1, 2]])["ok"])
        self.assertTrue(XF.check_sol(inst, [[2, 1]])["ok"])
        late = make([(0, 0, 0, 0, 100, 0), (3, 4, 2, 0, 50, 1), (6, 8, 3, 0, 10, 1)], 5)
        self.assertFalse(XF.check_sol(late, [[1, 2]])["ok"])
        self.assertTrue(XF.check_sol(late, [[2, 1]])["ok"])
        self.assertFalse(XF.check_sol(inst, [[1]])["ok"])
        self.assertFalse(XF.check_sol(inst, [[1, 2], [2]])["ok"])
        self.assertFalse(XF.check_sol(inst, [[1, 2, 3]])["ok"])
        short = make([(0, 0, 0, 0, 21, 0), (3, 4, 2, 0, 50, 1), (6, 8, 3, 10, 20, 1)], 5)
        self.assertFalse(XF.check_sol(short, [[1, 2]])["ok"])  # back at 22 after 21

    def test_brute_routes_match_checker(self):
        for seed in range(6):
            inst = random_cap_instance(5, seed)
            for p in itertools.permutations(range(1, 6), 3):
                rest = [[c] for c in range(1, 6) if c not in p]
                self.assertEqual(XF.check_sol(inst, [list(p)] + rest)["ok"],
                                 feasible_order(inst, p) and all(feasible_order(inst, r) for r in rest))


class TestCapacityBound(unittest.TestCase):
    def test_cap_lb(self):
        self.assertEqual(XF.cap_lb(make([(0, 0, 0, 0, 9, 0), (1, 1, 2, 0, 9, 1), (2, 2, 3, 0, 9, 1)], 4)), 2)
        self.assertEqual(XF.cap_lb(make([(0, 0, 0, 0, 9, 0), (1, 1, 2, 0, 9, 1), (2, 2, 3, 0, 9, 1)], 5)), 1)

    def test_knap_max_brute(self):
        rng = random.Random(11)
        for _ in range(200):
            m = rng.randint(1, 8)
            p = [rng.randint(0, 9) for _ in range(m)]
            w = [rng.randint(0, 12) for _ in range(m)]
            cap = rng.randint(0, 30)
            best = 0
            for mask in range(1 << m):
                if sum(w[i] for i in range(m) if mask >> i & 1) <= cap:
                    best = max(best, sum(p[i] for i in range(m) if mask >> i & 1))
            self.assertEqual(XF.knap_max(p, w, cap), best)
            self.assertGreaterEqual(XF.frac_knap(np.array(p, float), np.array(w, float), cap) + 1e-9, best)

    def test_core_inequality(self):
        """min(P_time, P_knap) is at least the profit of every feasible (capacity + time) elementary route."""
        for seed in range(20):
            inst = random_cap_instance(6, 300 + seed)
            ok = route_table(inst)
            TI = TM.Inst(inst)
            rng = random.Random(seed)
            pi = [rng.choice([0, 1, 2, 3, 5, 8]) for _ in range(TI.n)]
            lb, P, pk, capped, timeout = XF.cap_eval(TI, pi)
            if lb is None:
                continue
            self.assertFalse(timeout)
            self.assertGreaterEqual(P, best_route_profit(inst, pi, ok), seed)
            self.assertLessEqual(XF.fceil(lb), brute_min_fleet(inst, ok), seed)

    def test_cap_bound_never_above_minimum(self):
        for seed in range(14):
            inst = random_cap_instance(6, 500 + seed)
            ok = route_table(inst)
            opt = brute_min_fleet(inst, ok)
            TI = TM.Inst(inst)
            rng = random.Random(seed)
            u = [rng.randint(0, 9) for _ in range(TI.n)]
            best, cert, rows = XF.cap_bound(TI, u, time.monotonic() + 30)
            self.assertLessEqual(XF.fceil(best) if best > 0 else 0, opt, seed)
            self.assertGreaterEqual(XF.fceil(best) if best > 0 else 0, 1)
            if cert:
                self.assertTrue(XF.cap_verify(TI, cert))
                bad = dict(cert)
                bad["p"] = cert["p"] - 1
                self.assertFalse(XF.cap_verify(TI, bad))
            best0, _, _ = XF.cap_bound(TI, None, time.monotonic() + 30)  # demands only
            self.assertLessEqual(XF.fceil(best0) if best0 > 0 else 0, opt, seed)

    def test_knapsack_side_proves_capacity(self):
        """Four co-located customers that each fill a vehicle: time alone allows one walk through all of them; the
        knapsack side caps a route at one customer, so the bound is exactly 4 (the true minimum)."""
        rows = [(0, 0, 0, 0, 1000, 0)] + [(1, 1, 5, 0, 900, 1)] * 4
        inst = make(rows, 5)
        TI = TM.Inst(inst)
        lb, P, pk, capped, timeout = XF.cap_eval(TI, [1, 1, 1, 1])
        self.assertTrue(capped)
        self.assertEqual((P, pk), (1, 1))
        self.assertEqual(lb, Fraction(4))
        self.assertEqual(brute_min_fleet(inst), 4)


class TestPages(unittest.TestCase):
    def test_parse_history(self):
        h = ("<h1>XTW-n1001</h1><table><tr><td>36&nbsp;/&nbsp;79,104</td><td>2026/11/16 19:27:59</td></tr>"
             "<tr><td>37 / 79,650</td><td>2026/11/05 11:09:39</td></tr>"
             "<tr><td>39 / 80,803</td><td>2026/11/02 17:40:48</td></tr></table>")
        r = XF.parse_history(h)
        self.assertEqual(r["name"], "XTW-n1001")
        self.assertEqual(r["pairs"], 3)
        self.assertEqual(r["newest"], [36, 79104.0])
        self.assertEqual(r["oldest"], [39, 80803.0])
        self.assertEqual(r["fleets"], [36, 37, 39])

    def test_parse_opt_table(self):
        h = ('<tr><td><a title="XTW-n101" href="/x">XTW-n101</a></td><td>100</td><td>634</td><td>9 / 14,427</td>'
             '<td>yes</td></tr><tr><td>XTW-n106</td><td>105</td><td>No</td></tr><tr><td>XLTW-Test-n1048</td></tr>'
             '<tr><td>XTW-n110</td></tr>')
        self.assertEqual(XF.parse_opt_table(h), {"XTW-n101": True, "XTW-n106": False, "XTW-n110": None})


class TestHarness(unittest.TestCase):
    def test_finish(self):
        r = XF.finish({"instance": "a", "cap_lb": 3, "bks_vehicles": 3, "bks_ok": True})
        self.assertTrue(r["proved"])
        self.assertFalse(r["tw_needed"])
        self.assertFalse(r["above_bks"])
        r = XF.finish({"instance": "b", "cap_lb": 2, "st": {"bound": 4, "verified": True}, "bks_vehicles": 3,
                       "bks_ok": True})
        self.assertTrue(r["above_bks"])
        self.assertTrue(r["tw_needed"])
        r = XF.finish({"instance": "c", "cap_lb": 2, "cg": {"bound": 3, "recheck": True}, "bks_vehicles": 3,
                       "bks_ok": False})
        self.assertFalse(r["proved"])
        self.assertEqual(r["final"], 3)
        r = XF.finish({"instance": "d", "cap_lb": 2, "cg": {"bound": None, "recheck": False}, "bks_vehicles": 3,
                       "bks_ok": True})
        self.assertTrue(r["unverified"])

    def test_end_to_end(self):
        d = tempfile.mkdtemp()
        try:
            idir, bdir, pdir = (os.path.join(d, x) for x in ("inst", "bks", "pages"))
            for x in (idir, bdir, pdir):
                os.makedirs(x)
            insts = [random_cap_instance(6, 901, name="XTW-n7"), random_cap_instance(7, 902, name="XTW-n8")]
            # a capacity-free one with wide windows (only time bounds can say anything)
            free = random_cap_instance(6, 903, width=(80, 120), name="XTW-n9")
            free["capacity"] = sum(r[2] for r in free["rows"][1:])
            insts.append(free)
            opts = {}
            for inst in insts:
                write_vrp(os.path.join(idir, inst["name"] + ".vrp"), inst)
                n = len(inst["rows"]) - 1
                routes = [[c] for c in range(1, n + 1)]
                chk = XF.check_sol(inst, routes)
                self.assertTrue(chk["ok"], chk)
                with open(os.path.join(bdir, inst["name"] + ".sol"), "w") as f:
                    f.write("\n".join("Route #%d: %d" % (i + 1, r[0]) for i, r in enumerate(routes)))
                    f.write("\nCost %d\n" % chk["cost"])
                opts[inst["name"]] = brute_min_fleet(inst)
            with open(os.path.join(pdir, "list.html"), "w") as f:
                f.write("<tr><td>XTW-n7</td><td>yes</td></tr><tr><td>XTW-n8</td><td>no</td></tr>")
            with open(os.path.join(pdir, "bounds-1.html"), "w") as f:
                f.write("<h1>XTW-n8</h1><td>7 / 500</td><td>8 / 600</td>")
            man = {"code": {}, "instances": {"dir": idir, "sha256": "x"}, "bks": {"dir": bdir, "sha256": "y"},
                   "pages": {"list": os.path.join(pdir, "list.html"),
                             "bounds": {"1": os.path.join(pdir, "bounds-1.html")}}}
            out = os.path.join(d, "out")
            res = XF.run_all(man, out, global_s=120, st_fn=lambda n: 3.0, cg_fn=lambda n: 6.0, cap_s=6.0,
                             final_s=3.0)
            t = res["tally"]
            self.assertEqual(t["errors"], [])
            self.assertEqual(t["bks_ok"], 3)
            self.assertEqual(t["above_bks"], [])
            self.assertEqual(t["unverified"], [])
            for r in res["instances"]:
                self.assertLessEqual(r["final"], opts[r["instance"]], r["instance"])
                self.assertLessEqual(r["final"], r["bks_vehicles"])
                self.assertIsNotNone((r.get("st") or {}).get("bound"), r["instance"])
            by = {r["instance"]: r for r in res["instances"]}
            self.assertIs(by["XTW-n7"]["opt"], True)
            self.assertIs(by["XTW-n8"]["opt"], False)
            self.assertEqual(by["XTW-n8"]["history"]["oldest"], [8, 600.0])
            self.assertTrue(by["XTW-n9"]["capfree"])
            self.assertTrue(os.path.exists(os.path.join(out, "xtwfleet", "results.md")))
            with open(os.path.join(out, "xtwfleet", "results.json")) as f:
                self.assertEqual(json.load(f)["tally"]["instances"], 3)
            self.assertTrue(os.path.exists(os.path.join(out, "xtwfleet", "pages", "list.html")))
        finally:
            shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
