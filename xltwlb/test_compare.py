"""Tests for compare.py. MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0."""
import json
import unittest

import compare as C
import xltwlb as X

CSV = ("id,instance,customers,KC,KT_double,K_double,KT_dimacs,K_dimacs,SINTEF_vehicles,SINTEF_minus_K,"
       "CVRPLib_BKS_routes,PyVRP_vrptwl,density_double\n"
       "380,C101,100,10,10,10,10,10,10,0,10,,0.1295\n"
       "397,R101,100,8,18,18,18,18,19,1,20,,0.3875\n")
CLIQUES = json.dumps({"C101": {"double": [1, 2], "dimacs": [1, 2]}, "R101": {"double": [3, 6], "dimacs": [3, 6]}})


def rec(name, kc, kb, kts, verified=True):
    bounds = {"customers": 100, "capacity": 200, "kc": kc, "kb": kb}
    for c, kt in zip(X.CONVS, kts):
        bounds[c] = {"kt": kt, "k": max(kb, kt), "verified": verified, "bad_pair": None, "unservable": [],
                     "density": 0.1, "seconds": [0.1, 0.1, 0.1]}
    return {"instance": name, "bounds": bounds, "peak_gb": 0.1}


class PublishedTest(unittest.TestCase):
    def test_parse(self):
        rows, cliques = C.parse_published(CSV, CLIQUES)
        self.assertEqual(rows["R101"], {"kc": 8, "kt_double": 18, "kt_dimacs": 18, "k_double": 18, "k_dimacs": 18})
        self.assertEqual(cliques["C101"]["double"], [1, 2])


class CompareTest(unittest.TestCase):
    def setUp(self):
        self.pub, self.pub_cliques = C.parse_published(CSV, CLIQUES)

    def test_agreement(self):
        recs = [rec("C101", 10, 10, [10, 10, 10]), rec("R101", 8, 8, [18, 18, 17])]
        cliques = {"C101": {"double": [1, 2], "dimacs": [1, 2], "round": [1]},
                   "R101": {"double": [3, 6], "dimacs": [3, 6], "round": [3]}}
        t = C.compare(recs, cliques, self.pub, self.pub_cliques)
        self.assertEqual(t["kt_diff"], [])
        self.assertEqual(t["clique_diff"], [])
        self.assertEqual(t["round_vs_double"], [["R101", 18, 17]])
        self.assertEqual(t["predictions"]["C1"], "held")
        self.assertEqual(t["predictions"]["C0"], "did not hold")  # only 2 of 356 instances

    def test_differences_found(self):
        recs = [rec("C101", 10, 11, [9, 10, 10], verified=False), rec("R101", 8, 8, [18, 18, 18])]
        cliques = {"C101": {"double": [1], "dimacs": [1, 2]}, "R101": {"double": [3, 6], "dimacs": [6, 3]}}
        t = C.compare(recs, cliques, self.pub, self.pub_cliques)
        self.assertEqual(t["kt_diff"], [["C101", "double", 10, 9]])
        self.assertEqual(t["clique_diff"], [["C101", "double"], ["R101", "dimacs"]])
        self.assertEqual(t["kb_above_kc"], [["C101", 10, 11]])
        self.assertEqual(t["clique_unverified"], ["C101/double", "C101/dimacs", "C101/round"])
        p = t["predictions"]
        self.assertEqual((p["C1"], p["C2"]), ("did not hold", "did not hold"))

    def test_unpublished_is_untestable(self):
        t = C.compare([rec("C101", 10, 10, [10, 10, 10])], {}, {}, {})
        self.assertEqual(t["predictions"]["C1"], "untestable")

    def test_errors_counted(self):
        t = C.compare([{"instance": "id400", "error": "boom", "peak_gb": None}], {}, self.pub, self.pub_cliques)
        self.assertEqual(t["run_errors"], ["id400"])
        self.assertEqual(t["predictions"]["C0"], "did not hold")


if __name__ == "__main__":
    unittest.main()
