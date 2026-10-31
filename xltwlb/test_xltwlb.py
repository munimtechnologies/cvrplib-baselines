"""Tests for xltwlb.py. MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0."""
import math
import random
import unittest

import numpy as np

import xltwlb as X

VRPLIB = """NAME : TINY-n3
COMMENT : test
TYPE : VRPTW
DIMENSION : 4
EDGE_WEIGHT_TYPE : EUC_2D
CAPACITY : 10
NODE_COORD_SECTION
1 0 0
2 0 10
3 0 -10
4 10 0
DEMAND_SECTION
1 0
2 3
3 3
4 3
TIME_WINDOW_SECTION
1 0 1000
2 0 20
3 0 20
4 0 1000
SERVICE_TIME_SECTION
1 0
2 10
3 10
4 10
DEPOT_SECTION
1
-1
EOF
"""

SOLOMON = """C101

VEHICLE
NUMBER     CAPACITY
  25         200

CUSTOMER
CUST NO.  XCOORD.   YCOORD.    DEMAND   READY TIME  DUE DATE   SERVICE   TIME

    0      40         50          0          0       1236          0
    1      45         68         10        912        967         90
    2      45         70         30        825        870         90
"""


def brute_inc(inst, conv):
    """Pairwise incompatibility in plain Python floats, one pair at a time."""
    rows = inst["rows"]

    def tt(i, j):
        d = math.hypot(rows[i][0] - rows[j][0], rows[i][1] - rows[j][1])
        if conv == "dimacs":
            return math.floor(d * 10.0) / 10.0
        if conv == "round":
            return math.floor(d + 0.5)
        return d

    def e(i):
        return max(rows[i][3], rows[0][3] + tt(0, i))

    def lat(i):
        return min(rows[i][4], rows[0][4] - rows[i][5] - tt(i, 0))

    def can(i, j):
        return max(rows[j][3], e(i) + rows[i][5] + tt(i, j)) <= lat(j) + X.EPS

    n = len(rows) - 1
    out = np.zeros((n, n), dtype=bool)
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            if i != j:
                cap_bad = rows[i][2] + rows[j][2] > inst["capacity"] + X.EPS
                out[i - 1, j - 1] = cap_bad or not (can(i, j) or can(j, i))
    return out


def random_inst(n, seed, service=10):
    rnd = random.Random(seed)
    rows = [(50, 50, 0, 0, 1000, 0)]
    for _ in range(n):
        c = rnd.randint(120, 860)
        w = rnd.choice([10, 40, 300])
        rows.append((rnd.randint(0, 100), rnd.randint(0, 100), rnd.randint(1, 60), c - w, c + w, service))
    return {"name": "R", "vehicles": None, "capacity": 100, "rows": rows,
            "raw": [tuple(str(v) for v in r) for r in rows]}


class ParseTest(unittest.TestCase):
    def test_vrplib(self):
        inst = X.parse_any(VRPLIB)
        self.assertEqual(inst["name"], "TINY-n3")
        self.assertEqual(inst["capacity"], 10)
        self.assertEqual(inst["rows"][0], (0, 0, 0, 0, 1000, 0))
        self.assertEqual(inst["rows"][2], (0, -10, 3, 0, 20, 10))
        self.assertEqual(inst["raw"][3], ("10", "0", "3", "0", "1000", "10"))

    def test_vrplib_depot_not_first(self):
        text = VRPLIB.replace("DEPOT_SECTION\n1\n", "DEPOT_SECTION\n4\n")
        inst = X.parse_vrplib(text)
        self.assertEqual(inst["rows"][0][:2], (10, 0))
        self.assertEqual([r[:2] for r in inst["rows"][1:]], [(0, 0), (0, 10), (0, -10)])

    def test_explicit_matrix_refused(self):
        text = VRPLIB.replace("DEPOT_SECTION", "EDGE_WEIGHT_SECTION\n0 1 2\nDEPOT_SECTION")
        with self.assertRaises(ValueError):
            X.parse_vrplib(text)

    def test_solomon(self):
        inst = X.parse_any(SOLOMON)
        self.assertEqual(inst["name"], "C101")
        self.assertEqual((inst["vehicles"], inst["capacity"]), (25, 200))
        self.assertEqual(inst["rows"][2], (45, 70, 30, 825, 870, 90))

    def test_round_trip(self):
        inst = X.synthetic(50, seed=7)
        back = X.parse_vrplib(X.write_vrplib(inst))
        self.assertEqual(back["rows"], inst["rows"])
        self.assertEqual(back["capacity"], inst["capacity"])


class BinPackingTest(unittest.TestCase):
    def test_three_big_items(self):
        self.assertEqual(X.bin_packing_bound([6, 6, 6], 10), 3)

    def test_no_overcount(self):
        self.assertEqual(X.bin_packing_bound([6, 6, 4, 4], 10), 2)

    def test_at_least_capacity_bound(self):
        rnd = random.Random(3)
        for _ in range(50):
            w = [rnd.randint(1, 70) for _ in range(rnd.randint(1, 40))]
            kc = math.ceil(sum(w) / 100)
            kb = X.bin_packing_bound(w, 100)
            self.assertGreaterEqual(kb, kc)
            self.assertLessEqual(kb, len(w))

    def test_valid_against_first_fit_decreasing(self):
        rnd = random.Random(5)
        for _ in range(50):
            w = sorted((rnd.randint(1, 100) for _ in range(rnd.randint(1, 30))), reverse=True)
            bins = []
            for x in w:
                for k, used in enumerate(bins):
                    if used + x <= 100:
                        bins[k] += x
                        break
                else:
                    bins.append(x)
            self.assertLessEqual(X.bin_packing_bound(w, 100), len(bins))


class IncompatibleTest(unittest.TestCase):
    def test_tiny_case(self):
        inst = X.parse_vrplib(VRPLIB)
        res = X.bound_one(inst)
        for conv in X.CONVS:
            self.assertEqual(res[conv]["kt"], 2, conv)
            self.assertEqual(res[conv]["k"], 2, conv)
            self.assertTrue(res[conv]["verified"], conv)
        self.assertEqual((res["kc"], res["kb"]), (1, 1))

    def test_blocks_match_brute_force(self):
        for seed in (1, 2, 3):
            inst = random_inst(60, seed)
            for conv in X.CONVS:
                inc, _ = X.incompatible(inst, conv, block=7)
                self.assertTrue(np.array_equal(inc, brute_inc(inst, conv)), (seed, conv))

    def test_capacity_pairs(self):
        inst = random_inst(10, 4)
        rows = [list(r) for r in inst["rows"]]
        for i in (1, 2, 3):
            rows[i][2], rows[i][3], rows[i][4] = 60, 0, 1000  # wide windows, demands too large to share
        inst["rows"] = [tuple(r) for r in rows]
        inst["raw"] = [tuple(str(v) for v in r) for r in rows]
        inc, _ = X.incompatible(inst, "double")
        self.assertTrue(inc[0, 1] and inc[0, 2] and inc[1, 2])
        self.assertGreaterEqual(X.bin_packing_bound([r[2] for r in rows[1:]], 100), 3)

    def test_cliques_verify(self):
        for seed in (1, 2):
            inst = random_inst(80, seed)
            res = X.bound_one(inst)
            for conv in X.CONVS:
                r = res[conv]
                self.assertTrue(r["verified"], (seed, conv, r["bad_pair"]))
                self.assertEqual(r["k"], max(res["kb"], r["kt"]))
                self.assertGreaterEqual(r["kt"], 1)

    def test_exact_check_rejects_compatible_pair(self):
        inst = X.parse_vrplib(VRPLIB)
        ok, bad = X.verify_clique_exact(inst, [1, 3], "double")
        self.assertFalse(ok)
        self.assertEqual(bad, [1, 3])

    def test_slack_rule(self):
        inst = random_inst(20, 9, service=0)
        res = X.bound_one(inst)
        self.assertIsNotNone(res["double"])
        self.assertIsNone(res["dimacs"])
        self.assertIsNone(res["round"])

    def test_synthetic_servable(self):
        inst = X.synthetic(300, seed=11)
        _, unservable = X.incompatible(inst, "double")
        self.assertEqual(unservable, [])


if __name__ == "__main__":
    unittest.main()
