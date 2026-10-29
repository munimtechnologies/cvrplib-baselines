import os
import tempfile
import unittest
from decimal import Decimal

import exact_check as ec

try:
    import vrplib  # noqa: F401
    HAVE_VRPLIB = True
except ImportError:
    HAVE_VRPLIB = False


def toy(due2="6"):
    """Depot at (0,0); customer 1 at (3,4) due 5; customer 2 at (3,5)."""
    D = Decimal
    return {"name": "TOY", "capacity": 10,
            "coords": [(D(0), D(0)), (D(3), D(4)), (D(3), D(5)), (D(1), D(1))],
            "demand": [0, 1, 1, 1],
            "tw": [(D(0), D(100)), (D(0), D(5)), (D(0), D(due2)), (D(0), D(100))],
            "service": [D(0), D(0), D(0), D(0)]}


SOLOMON = """TEST1

VEHICLE
NUMBER     CAPACITY
  3         10

CUSTOMER
CUST NO.  XCOORD.   YCOORD.    DEMAND   READY TIME  DUE DATE   SERVICE   TIME

    0      0          0          0          0        100          0
    1      3          4          1          0          5          0
    2      3          5          1          0          6          0
    3      1          1          1          0        100         10
"""


class ExactCheck(unittest.TestCase):
    def test_on_time_route_with_zero_slack(self):
        res = ec.check([[1, 2], [3]], toy())
        self.assertTrue(res["ok"])
        self.assertEqual(res["late"], [])
        self.assertEqual(res["min_slack"], 0)
        expect = 5 + 1 + Decimal(34).sqrt() + 2 * Decimal(2).sqrt()
        self.assertLess(abs(res["distance"] - expect), Decimal("1e-40"))

    def test_late_visit_listed_and_bounded(self):
        res = ec.check([[1, 2], [3]], toy(due2="5.9"))
        self.assertFalse(res["ok"])
        self.assertEqual(len(res["late"]), 1)
        v = res["late"][0]
        self.assertEqual((v["route"], v["customer"], v["arcs"]), (1, 2, 2))
        self.assertEqual(v["late_by"], Decimal("0.1"))
        self.assertTrue(v["within_truncation_bound"])
        self.assertEqual(res["late_routes"], 1)

    def test_exact_lateness_against_truncated_due(self):
        # sqrt(2) = 1.41421..., due 1.4: late only without truncation (DIMACS arc = 1.4)
        inst = toy()
        inst["tw"][3] = (Decimal(0), Decimal("1.4"))
        res = ec.check([[3], [1, 2]], inst)
        self.assertFalse(res["ok"])
        self.assertEqual(res["late"][0]["late_by"], Decimal(2).sqrt() - Decimal("1.4"))

    def test_structure(self):
        self.assertFalse(ec.check([[1, 1], [2, 3]], toy())["ok"])
        self.assertIn("not visited", ec.check([[1, 2]], toy())["reason"])
        inst = toy()
        inst["capacity"] = 1
        self.assertIn("capacity", ec.check([[1, 2], [3]], inst)["reason"])

    def test_compare(self):
        res = ec.check([[1, 2], [3]], toy(due2="5.9"))
        ref = {"double_ok": "False", "late": "1", "max_late": "0.1",
               "double_distance": str(round(float(res["distance"]), 2))}
        self.assertEqual(set(ec.compare(res, ref).values()), {True})
        ref["double_ok"] = "True"
        self.assertFalse(ec.compare(res, ref)["feasibility"])

    def test_reference_file(self):
        here = os.path.dirname(os.path.abspath(__file__))
        import csv
        with open(os.path.join(here, "reference.csv"), encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 86)
        self.assertEqual(sum(1 for r in rows if r["source"] == "pyvrp-lex"), len(ec.SOLS))
        bks_bad = [r["instance"] for r in rows
                   if r["source"] == "cvrplib-bks" and r["double_ok"] == "False"]
        self.assertEqual(len(bks_bad), 10)

    @unittest.skipUnless(HAVE_VRPLIB, "vrplib not installed")
    def test_vrplib_parse(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.txt")
            s = os.path.join(d, "t.sol")
            with open(p, "w") as f:
                f.write(SOLOMON)
            with open(s, "w") as f:
                f.write("Route #1: 1 2\nRoute #2: 3\nCost 14.6\n")
            inst = ec.load_instance(p)
            routes = ec.load_routes(s)
        self.assertEqual(routes, [[1, 2], [3]])
        self.assertEqual(inst["capacity"], 10)
        self.assertEqual(len(inst["coords"]), 4)
        self.assertEqual(inst["tw"][1][1], 5)
        self.assertEqual(inst["service"][3], 10)
        self.assertTrue(ec.check(routes, inst)["ok"])


if __name__ == "__main__":
    unittest.main()
