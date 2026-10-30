"""Tests for exact_repair_check.py (no network). MV2 of Munim, Inc. Apache-2.0."""
import os
import tempfile
import unittest
from decimal import Decimal

import exact_repair_check as x


def toy():
    # depot (0,0); customer 1 at (3,4): 5.0 away; customer 2 at (1,1): 1.41421... away, 1.4 under DIMACS
    return {"capacity": 10,
            "coords": [(Decimal(0), Decimal(0)), (Decimal(3), Decimal(4)), (Decimal(1), Decimal(1))],
            "demand": [0, 3, 3],
            "tw": [(Decimal(0), Decimal(100)), (Decimal(0), Decimal(50)), (Decimal(0), Decimal("1.4"))],
            "service": [Decimal(0), Decimal(10), Decimal(10)]}


class ArcTest(unittest.TestCase):
    def test_truncation(self):
        a, b, c = toy()["coords"]
        self.assertEqual(x.arc(a, b, True), Decimal(5))
        self.assertEqual(x.arc(a, c, True), Decimal("1.4"))
        self.assertGreater(x.arc(a, c, False), Decimal("1.4142"))


class CheckTest(unittest.TestCase):
    def test_on_time_both(self):
        inst = toy()
        inst["tw"][2] = (Decimal(0), Decimal(2))
        for dimacs in (False, True):
            self.assertTrue(x.check([[1], [2]], inst, dimacs)["ok"])

    def test_late_only_in_double(self):
        inst = toy()
        dbl, dim = x.check([[1], [2]], inst), x.check([[1], [2]], inst, dimacs=True)
        self.assertFalse(dbl["ok"])
        self.assertEqual(dbl["late"][0]["customer"], 2)
        self.assertLess(dbl["late"][0]["late_by"], Decimal("0.1"))
        self.assertTrue(dim["ok"])
        self.assertEqual(dim["distance"], Decimal("12.8"))  # 5 + 5 + 1.4 + 1.4
        self.assertEqual(dim["min_slack"], Decimal(0))

    def test_structure(self):
        inst = toy()
        self.assertIn("not visited", x.check([[1]], inst)["reason"])
        self.assertIn("repeated", x.check([[1], [1, 2]], inst)["reason"])
        inst["capacity"] = 5
        self.assertEqual(x.check([[1, 2]], inst)["reason"], "over capacity")


class FileTest(unittest.TestCase):
    def test_cost_line_and_cache(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.sol")
            with open(p, "w", encoding="utf-8") as f:
                f.write("Route #1: 1\nRoute #2: 2\nCost 12.83\n")
            self.assertEqual(x.cost_line(p), Decimal("12.83"))
            self.assertEqual(x.fetch("https://invalid.example/never", p), p)  # cached: no network


class ScoreTest(unittest.TestCase):
    def row(self, name, routes=5, bks=5, ok=True):
        return {"instance": name, "routes": routes, "bks_routes": bks, "published_routes": routes,
                "double_ok": ok, "double_reason": "" if ok else "1 late arrivals", "dimacs_ok": True,
                "distance_agrees": True, "dimacs_cost_agrees": True, "double_min_slack": "0.500000"}

    def test_all_held(self):
        rows = [self.row("I%d" % k) for k in range(84)]
        rows += [self.row("R2_2_1", 12, 13), self.row("R2_2_2", 10, 11), self.row("R2_6_5", 21, 22)]
        t = x.tally_rows(rows, 87)
        self.assertEqual(set(t["predictions"].values()), {"held"})
        self.assertEqual(t["fewer_routes_than_bks"], ["R2_2_1", "R2_2_2", "R2_6_5"])

    def test_failures(self):
        rows = [self.row("I%d" % k) for k in range(85)] + [self.row("R2_2_1", 12, 13), self.row("Z", ok=False)]
        rows[0]["routes"] = 6
        t = x.tally_rows(rows, 87)
        p = t["predictions"]
        self.assertEqual(p["X0"], "did not hold")   # routes mismatch and more routes than BKS
        self.assertEqual(p["X1"], "did not hold")
        self.assertEqual(p["X2"], "held")
        self.assertEqual(p["X4"], "did not hold")
        self.assertEqual(t["structure_fail"], [])


if __name__ == "__main__":
    unittest.main()
