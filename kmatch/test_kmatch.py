"""Tests for kmatch.py (no data or network needed). MV2 of Munim, Inc. Made with AI agents working in MV2's name.
Apache-2.0."""
import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

import kmatch as K  # noqa: E402


def make(rows):
    return {"name": "T", "vehicles": None, "capacity": 100, "rows": rows,
            "raw": [tuple(str(v) for v in r) for r in rows]}


# depot (0,0) open 0-1000. c1 must start at 10, c2 and c3 (same place) at 21. Only 1->2 and 1->3 are possible.
CHAIN = make([(0, 0, 0, 0, 1000, 0), (10, 0, 1, 10, 10, 1), (20, 0, 1, 21, 21, 1), (20, 0, 1, 21, 21, 1)])
# two customers at the same place with wide windows: both orders possible, so the matching closes a 2-cycle.
TWO = make([(0, 0, 0, 0, 1000, 0), (10, 0, 1, 0, 500, 1), (10, 0, 1, 0, 500, 1)])


def rint(d):
    return math.floor(d + 0.5)


def random_instance(n, seed):
    rng = random.Random(seed)
    rows = [(50, 50, 0, 0, 1000, 0)]
    for _ in range(n):
        x, y = rng.randint(0, 100), rng.randint(0, 100)
        a = rng.randint(80, 700)
        rows.append((x, y, 1, a, a + rng.randint(20, 200), 1))
    return make(rows)


def brute_arcs(inst):
    rows = inst["rows"]
    n = len(rows) - 1
    x0, y0, _, a0, b0, _ = rows[0]
    e, lat = [None] * (n + 1), [None] * (n + 1)
    for i in range(1, n + 1):
        x, y, _, a, b, s = rows[i]
        t0 = rint(math.hypot(x - x0, y - y0))
        e[i], lat[i] = max(a, a0 + t0), min(b, b0 - s - t0)
    out = np.zeros((n, n), dtype=bool)
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            if i != j:
                t = rint(math.hypot(rows[i][0] - rows[j][0], rows[i][1] - rows[j][1]))
                out[i - 1, j - 1] = max(rows[j][3], e[i] + rows[i][5] + t) <= lat[j] + 1e-6
    return out


def kuhn(adj):
    """Plain augmenting-path maximum matching, as an independent check of scipy's."""
    n = len(adj)
    match_col = [-1] * n

    def try_row(i, seen):
        for j in np.flatnonzero(adj[i]):
            j = int(j)
            if not seen[j]:
                seen[j] = True
                if match_col[j] < 0 or try_row(match_col[j], seen):
                    match_col[j] = i
                    return True
        return False

    return sum(1 for i in range(n) if try_row(i, [False] * n))


def greedy_routes(inst):
    """Feasible routes built by simulation with real start times (customers by ready time, first route that fits)."""
    rows = inst["rows"]
    x0, y0, _, a0, b0, _ = rows[0]

    def t(i, j):
        return rint(math.hypot(rows[i][0] - rows[j][0], rows[i][1] - rows[j][1]))

    routes, state = [], []  # state: (last customer, its start time)
    for c in sorted(range(1, len(rows)), key=lambda k: rows[k][3]):
        a, b, s = rows[c][3], rows[c][4], rows[c][5]
        placed = False
        for k, (last, start) in enumerate(state):
            S = max(a, start + rows[last][5] + t(last, c))
            if S <= b and S + s + t(c, 0) <= b0:
                routes[k].append(c)
                state[k] = (c, S)
                placed = True
                break
        if not placed:
            S = max(a, a0 + t(0, c))
            assert S <= b and S + s + t(c, 0) <= b0
            routes.append([c])
            state.append((c, S))
    return routes


class TestArcs(unittest.TestCase):
    def test_chain_arcs(self):
        G = K.arc_matrix(CHAIN)
        self.assertEqual(sorted((int(i), int(j)) for i, j in zip(*G.nonzero())), [(0, 1), (0, 2)])
        self.assertTrue(K.has_arc(G, 0, 1))
        self.assertTrue(K.has_arc(G, 0, 2))
        self.assertFalse(K.has_arc(G, 1, 0))
        self.assertFalse(K.has_arc(G, 1, 2))
        self.assertFalse(K.has_arc(G, 0, 0))

    def test_matches_brute_force_and_blocks(self):
        inst = random_instance(40, 7)
        G1 = K.arc_matrix(inst)
        G2 = K.arc_matrix(inst, block=7)
        ref = brute_arcs(inst)
        self.assertTrue(np.array_equal(G1.toarray() > 0, ref))
        self.assertTrue(np.array_equal(G2.toarray() > 0, ref))
        self.assertGreater(int(ref.sum()), 0)

    def test_integer_coords_and_unservable(self):
        self.assertTrue(K.integer_coords(CHAIN))
        frac = make([(0, 0, 0, 0, 1000, 0), (1.5, 0, 1, 0, 100, 1)])
        self.assertFalse(K.integer_coords(frac))
        self.assertEqual(K.unservable(CHAIN), 0)
        late = make([(0, 0, 0, 0, 1000, 0), (100, 0, 1, 0, 50, 1)])  # cannot be reached before 50
        self.assertEqual(K.unservable(late), 1)


class TestBound(unittest.TestCase):
    def test_chain_bound(self):
        pc = K.path_cover_bound(K.arc_matrix(CHAIN))
        self.assertEqual(pc["km"], 2)
        self.assertEqual(pc["matched"], 1)
        self.assertEqual(pc["paths"], 2)
        self.assertEqual(pc["cycles"], 0)
        self.assertEqual(pc["cycle_vertices"], 0)
        self.assertTrue(pc["matching_arcs_ok"])

    def test_cycle_still_needs_one_vehicle(self):
        pc = K.path_cover_bound(K.arc_matrix(TWO))
        self.assertEqual(pc["matched"], 2)
        self.assertEqual(pc["km"], 1)
        self.assertEqual(pc["paths"], 0)
        self.assertEqual(pc["cycles"], 1)
        self.assertEqual(pc["cycle_vertices"], 2)

    def test_matching_size_against_kuhn(self):
        for seed in (1, 2, 3):
            inst = random_instance(40, seed)
            G = K.arc_matrix(inst)
            pc = K.path_cover_bound(G)
            self.assertEqual(pc["matched"], kuhn(G.toarray() > 0))
            self.assertEqual(pc["paths"], 40 - pc["matched"])

    def test_bound_never_above_a_feasible_solution(self):
        for seed in (11, 12, 13, 14):
            inst = random_instance(60, seed)
            G = K.arc_matrix(inst)
            routes = greedy_routes(inst)
            rc = K.route_check(routes, G)
            self.assertEqual(rc["missing_arcs"], 0)
            self.assertTrue(rc["covers_each_once"])
            self.assertLessEqual(K.path_cover_bound(G)["km"], len(routes))


class TestRoutesAndHelpers(unittest.TestCase):
    def test_route_check(self):
        G = K.arc_matrix(CHAIN)
        rc = K.route_check([[1, 2], [3]], G)
        self.assertEqual((rc["routes"], rc["pairs"], rc["missing_arcs"], rc["covers_each_once"]), (2, 1, 0, True))
        bad = K.route_check([[2, 1], [3]], G)
        self.assertEqual(bad["missing_arcs"], 1)
        self.assertEqual(bad["examples"], [[2, 1]])
        self.assertFalse(K.route_check([[1, 2]], G)["covers_each_once"])
        self.assertFalse(K.route_check([[1, 2], [3, 9]], G)["covers_each_once"])

    def test_parse_sol(self):
        self.assertEqual(K.parse_sol("Route #1: 1 2\nRoute #2: 3\nCost 123\n"), [[1, 2], [3]])

    def test_order(self):
        names = ["XLTW-Test-n5000", "XLTW-Test-n1841", "XLTW-Test-n3000", "XLTW-Test-n2000", "XLTW-Test-n1234"]
        ref = {"XLTW-Test-n3000": {"kc": 1}, "XLTW-Test-n2000": {"kc": 5}}
        self.assertEqual(K.order(names, ref), ["XLTW-Test-n1234", "XLTW-Test-n1841", "XLTW-Test-n3000",
                                               "XLTW-Test-n2000", "XLTW-Test-n5000"])

    def test_tally_and_invalid(self):
        good = {"instance": "a", "customers": 3, "kc": 1, "kstar": 2, "km": 3, "matched": 0, "paths": 3,
                "cycles": 0, "integer_coords": True, "unservable": 0, "matching_arcs_ok": True,
                "sol": {"routes": 3, "missing_arcs": 0, "covers_each_once": True, "km_le_routes": True}}
        bad = dict(good, instance="b", sol={"routes": 2, "missing_arcs": 1, "covers_each_once": True,
                                            "km_le_routes": False})
        t = K.tally([good, bad, {"instance": "c", "error": "x"}])
        self.assertEqual(t["km_above_kstar"], [["a", 2, 3], ["b", 2, 3]])
        self.assertEqual(t["km_above_kstar_capacity_free"], 2)
        self.assertEqual(t["invalid"], ["b"])
        self.assertEqual(t["errors"], ["c"])
        self.assertEqual(t["sum_kstar"], 4)
        self.assertEqual(t["sum_max_kstar_km"], 6)


if __name__ == "__main__":
    unittest.main()
