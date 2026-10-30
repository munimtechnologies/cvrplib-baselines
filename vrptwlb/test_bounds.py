"""Tests for bounds.py (no network). MV2 of Munim, Inc. Apache-2.0."""
import json
import unittest

import numpy as np

import bounds as bd


def inst_from(rows, capacity=100, vehicles=10, name="TOY"):
    """rows: (x, y, demand, ready, due, service), depot first."""
    return {"name": name, "vehicles": vehicles, "capacity": capacity, "rows": [tuple(r) for r in rows],
            "raw": [tuple(str(v) for v in r) for r in rows]}


def two_far():
    # customers 1 and 2 at opposite sides, both must start at 100-101: no route serves both; 3 fits with either
    return inst_from([(0, 0, 0, 0, 1000, 0), (10, 0, 5, 100, 101, 10), (-10, 0, 5, 100, 101, 10),
                      (0, 10, 5, 0, 1000, 10)])


def trunc_pair():
    # 1 -> 2 is 1.05 long: late by 0.05 in double precision, on time under DIMACS (1.0); 2 -> 1 is never on time
    return inst_from([(0, 0, 0, 0, 1000, 0), (10, 0, 5, 100, 100, 10), (10, 1.05, 5, 111, 111, 10)])


class ParseTest(unittest.TestCase):
    def test_sintef(self):
        html = ("<tr><td>c101</td><td>10</td><td>828.94</td><td>RT</td></tr>"
                "<tr><td>r205b</td><td>3</td><td>954.16</td></tr>"
                "<tr><td><a href='x/r1_4_1-10372.11.txt'>r1_4_1</a></td><td>40</td><td>10372.31</td></tr>"
                "<tr><td><a>c1_8_5</a><sup>q</sup></td><td>72</td><td>25138.60</td></tr>"
                "<tr><td><a>r2_8_\n1</a></td><td>15</td><td>24963.08</td></tr>"
                "<tr><td>rc2_10_10</td><td>18</td><td>21834.94</td><td>SCR</td></tr>"
                "<p>NB! C1_8_1 earlier 80 25184.38</p>")
        got = bd.parse_sintef(html)
        self.assertEqual(got["C101"], (10, 828.94))
        self.assertEqual(got["R205"], (3, 954.16))
        self.assertEqual(got["R1_4_1"], (40, 10372.31))
        self.assertEqual(got["C1_8_5"], (72, 25138.60))
        self.assertEqual(got["R2_8_1"], (15, 24963.08))
        self.assertEqual(got["RC2_10_10"], (18, 21834.94))
        self.assertEqual(len(got), 6)  # the NB line has a word between name and numbers, so it is not a row

    def test_family_and_ids(self):
        self.assertEqual(bd.family("RC101"), "RC1")
        self.assertEqual(bd.family("C205"), "C2")
        self.assertEqual(bd.family("R1_10_1"), "R1")
        self.assertEqual(bd.parse_ids("380-382,700"), ["380", "381", "382", "700"])

    def test_solomon(self):
        text = ("C101\n\nVEHICLE\nNUMBER CAPACITY\n 25 200\n\nCUSTOMER\nCUST NO. XCOORD. YCOORD. DEMAND "
                "READY TIME DUE DATE SERVICE TIME\n\n 0 40 50 0 0 1236 0\n 1 45 68 10 912 967 90\n"
                " 2 45 70 30 825 870 90\n")
        inst = bd.parse_solomon(text)
        self.assertEqual(inst["name"], "C101")
        self.assertEqual(inst["capacity"], 200)
        self.assertEqual(inst["rows"][1], (45, 68, 10, 912, 967, 90))
        self.assertEqual(inst["raw"][2], ("45", "70", "30", "825", "870", "90"))


class BoundTest(unittest.TestCase):
    def test_capacity(self):
        inst = two_far()
        self.assertEqual(bd.capacity_bound(inst), 1)
        inst["capacity"] = 7
        self.assertEqual(bd.capacity_bound(inst), 3)
        inst["capacity"] = 5
        self.assertEqual(bd.capacity_bound(inst), 3)

    def test_incompatible(self):
        inc, unservable = bd.incompatible(two_far(), "double")
        self.assertEqual(unservable, [])
        self.assertTrue(inc[0, 1] and inc[1, 0])
        self.assertFalse(inc[0, 2] or inc[1, 2] or inc[0, 0])
        r = bd.bound_one(two_far())
        self.assertEqual(r["double"]["kt"], 2)
        self.assertEqual(r["double"]["clique"], [1, 2])
        self.assertTrue(r["double"]["verified"])
        self.assertEqual(r["double"]["k"], 2)

    def test_conventions(self):
        r = bd.bound_one(trunc_pair())
        self.assertEqual(r["double"]["kt"], 2)
        self.assertTrue(r["double"]["verified"])
        self.assertEqual(r["dimacs"]["kt"], 1)
        self.assertTrue(r["dimacs"]["verified"])

    def test_dimacs_skipped_without_service(self):
        rows = [list(x) for x in trunc_pair()["rows"]]
        rows[1][5] = 0.1
        r = bd.bound_one(inst_from(rows))
        self.assertIsNone(r["dimacs"])
        self.assertIsNotNone(r["double"])

    def test_verify_catches_wrong_clique(self):
        ok, bad = bd.verify_clique_exact(two_far(), [1, 3], "double")
        self.assertFalse(ok)
        self.assertEqual(bad, [1, 3])

    def test_clique_search(self):
        n = 40
        rng = np.random.default_rng(1)
        adj = rng.random((n, n)) < 0.2
        adj = adj | adj.T
        planted = [3, 7, 11, 19, 23, 31, 37]
        for i in planted:
            for j in planted:
                adj[i, j] = True
        np.fill_diagonal(adj, False)
        rows = [(0, 0, 0, 0, 1, 0)] + [(0, 0, 0, i, i, 0) for i in range(n)]
        c = bd.best_clique(adj, rows)
        self.assertGreaterEqual(len(c), len(planted))
        for i in c:
            for j in c:
                if i != j:
                    self.assertTrue(adj[i - 1, j - 1])

    def test_empty_graph(self):
        adj = np.zeros((3, 3), dtype=bool)
        self.assertEqual(bd.best_clique(adj, [(0,) * 6] * 4), [1])


class ScoreTest(unittest.TestCase):
    def rec(self, name, size, kc, kt, sintef, bks, vrptwl=None):
        return {"instance": name, "family": bd.family(name), "customers": size, "bks_routes": bks,
                "sintef": [sintef, 1.0], "vrptwl": vrptwl,
                "bounds": {"kc": kc,
                           "double": {"kt": kt, "k": max(kc, kt), "verified": True, "unservable": []},
                           "dimacs": {"kt": kt, "k": max(kc, kt), "verified": True, "unservable": []}}}

    def test_held(self):
        fleets = {"_source": "x", "R1_10_2": [91, 202.6, 91], "C1_10_1": [101, 300.6, 100]}
        recs = [self.rec("R101", 100, 8, 12, 19, 19), self.rec("R1_10_2", 1000, 91, 20, 91, 91, [91, 202.6, 91]),
                self.rec("C1_10_1", 1000, 90, 95, 100, 100, [101, 300.6, 100])]
        recs += [self.rec("C1_2_%d" % k, 200, 18, 3, 18, 20) for k in range(1, 354)]
        t = bd.tally_recs(recs, fleets)
        self.assertEqual(t["instances"], 356)
        self.assertEqual(t["vrptwl_early"], ["R1_10_2"])
        self.assertEqual(t["tw_above_kc_1000"], 1)
        self.assertEqual(t["open_1000"], [["C1_10_1", 5]])
        self.assertEqual(t["sintef_at_bound"], 354)
        self.assertEqual(t["predictions"]["B5"], "did not hold")
        for k in ("B0", "B1", "B2", "B3", "B4"):
            self.assertEqual(t["predictions"][k], "held", k)
        json.dumps(t)

    def test_failures(self):
        fleets = {"R1_10_2": [92, 202.6, 92]}
        recs = [self.rec("R101", 100, 8, 8, 19, 19), self.rec("R1_10_2", 1000, 91, 20, 90, 91, [92, 202.6, 92]),
                self.rec("C101", 100, 10, 3, 10, 9)]
        recs[2]["bounds"]["dimacs"]["verified"] = False
        t = bd.tally_recs(recs, fleets)
        p = t["predictions"]
        self.assertEqual(p["B0"], "did not hold")
        self.assertEqual(t["sintef_below_bound"], ["R1_10_2"])
        self.assertEqual(t["bks_below_bound"], ["C101"])
        self.assertEqual(p["B1"], "did not hold")
        self.assertEqual(p["B2"], "did not hold")
        self.assertEqual(p["B4"], "did not hold")
        self.assertEqual(t["clique_unverified"], ["C101/dimacs"])


if __name__ == "__main__":
    unittest.main()
