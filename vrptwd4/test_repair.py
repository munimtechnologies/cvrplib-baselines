import os
import tempfile
import unittest

import repair as rp

try:
    import pyvrp  # noqa: F401
    HAVE_PYVRP = True
except ImportError:
    HAVE_PYVRP = False


LATE_BKS = [[2, 1], [3, 4]]
NEVER_BKS = [[1], [2, 3, 4]]


def toy_repairable():
    """Route [2, 1] reaches customer 1 at 1.4142 + 4.1231 = 5.5373 > 5.5 (DIMACS: 1.4 + 4.1 = 5.5, on time).
    Route [1, 2] is on time in both conventions and has the same length."""
    return {"name": "T1", "vehicles": 2, "capacity": 10,
            "rows": [(0, 0, 0, 0, 100, 0), (5, 0, 1, 0, 5.5, 0), (1, 1, 1, 0, 100, 0),
                     (0, 5, 1, 0, 100, 0), (0, 6, 1, 0, 100, 0)]}


def toy_unrepairable():
    """Customer 1 at (5, 1) is due at 5: DIMACS 5.0 is on time, the exact 5.099 never is."""
    return {"name": "T2", "vehicles": 2, "capacity": 10,
            "rows": [(0, 0, 0, 0, 100, 0), (5, 1, 1, 0, 5, 0), (0, 5, 1, 0, 100, 0),
                     (0, 6, 1, 0, 100, 0), (1, 6, 1, 0, 100, 0)]}


def rec(name, ok, run=None, routes=10, matches=True):
    r = {"id": "0", "instance": name, "family": rp.family(name), "customers": 200, "bks_routes": routes,
         "bks_dimacs_matches_file": matches, "bks_double_ok": ok, "bks_double_distance": 100.0}
    if run is not None:
        r["run"] = run
    return r


def run(repaired, delta=0.1, routes=10, vs=None, agrees=True, dimacs_ok=True):
    return {"repaired": repaired, "delta_pct": delta if repaired else None, "num_routes": routes,
            "vs_sintef": vs, "pyvrp_agrees": agrees, "dimacs_ok": dimacs_ok}


class Helpers(unittest.TestCase):
    def test_family(self):
        self.assertEqual(rp.family("C101"), "C1")
        self.assertEqual(rp.family("R211"), "R2")
        self.assertEqual(rp.family("RC105"), "RC1")
        self.assertEqual(rp.family("RC2_10_1"), "RC2")
        self.assertEqual(rp.family("C1_2_5"), "C1")

    def test_budget(self):
        self.assertEqual(rp.budget(100), 60)
        self.assertEqual(rp.budget(200), 60)
        self.assertEqual(rp.budget(400), 120)
        self.assertEqual(rp.budget(1000), 300)

    def test_ceil_scaled_never_undercuts(self):
        vals = [0.0, 5.0, 5.5, 2 ** 0.5, 17 ** 0.5, 100.0]
        got = list(rp.ceil_scaled(vals))
        self.assertEqual(got, [0, 5000, 5500, 1415, 4124, 100000])
        for v, g in zip(vals, got):
            self.assertGreaterEqual(g, 1000 * v)
            self.assertLess(g - 1000 * v, 1)

    def test_vrplib_fleet_cap(self):
        text = rp.to_vrplib(toy_repairable(), 7)
        self.assertIn("VEHICLES : 7\n", text)
        self.assertIn("2 5 0\n", text)
        self.assertIn("TIME_WINDOW_SECTION\n1 0 100\n2 0 5.5\n", text)

    def test_toys_as_described(self):
        a = toy_repairable()
        self.assertTrue(rp.dc.check_dimacs(LATE_BKS, a)[0])
        self.assertFalse(rp.dc.check_double(LATE_BKS, a)["ok"])
        self.assertTrue(rp.dc.check_double([[1, 2], [3, 4]], a)["ok"])
        b = toy_unrepairable()
        self.assertTrue(rp.dc.check_dimacs(NEVER_BKS, b)[0])
        self.assertFalse(rp.dc.check_double(NEVER_BKS, b)["ok"])

    def test_write_sol(self):
        self.assertEqual(rp.write_sol([[1, 2], [3]], 12.345), "Route #1: 1 2\nRoute #2: 3\nCost 12.35\n")


class Tally(unittest.TestCase):
    def test_tally_and_predictions(self):
        recs = [rec("C101", True), rec("R102", False, run(True, 0.2, vs="worse")),
                rec("R211", False, run(True, 0.4, routes=9)), rec("C2_8_3", False, run(False)),
                rec("RC2_10_1", False, run(True, -0.1)), rec("R1_10_1", False, run(False), routes=95)]
        t = rp.tally_recs(recs)
        self.assertEqual(t["bks"], 6)
        self.assertEqual(t["late"], 5)
        self.assertEqual((t["late_solomon"], t["late_homberger"]), (2, 3))
        self.assertEqual(t["repaired"], 3)
        self.assertEqual(t["repaired_fewer_routes"], ["R211"])
        self.assertEqual(t["not_repaired"], ["C2_8_3", "R1_10_1"])
        self.assertEqual((t["late_wide"], t["repaired_wide"]), (3, 2))
        self.assertEqual((t["late_tight"], t["repaired_tight"]), (2, 1))
        self.assertEqual(t["median_delta_pct"], 0.2)
        self.assertEqual(t["by_family"], {"C2": [1, 0], "R1": [2, 1], "R2": [1, 1], "RC2": [1, 1]})
        self.assertEqual(t["sintef_compared"], {"R102": "worse"})
        p = t["predictions"]
        self.assertEqual(p["R0"], "did not hold")  # 6 BKSs, not 356
        self.assertEqual(p["R1"], "did not hold")
        self.assertEqual(p["R2"], "did not hold")
        self.assertEqual(p["R3"], "held")
        self.assertEqual(p["R4"], "held")
        self.assertEqual(p["R5"], "held")  # 2/3 >= 1/2
        self.assertEqual(p["R6"], "held")

    def test_score_edges(self):
        t = {"bks": 356, "late": 90, "dimacs_hygiene_fail": [], "run_errors": [], "pyvrp_disagreements": [],
             "repaired": 70, "repaired_wide": 44, "late_wide": 50, "repaired_tight": 26, "late_tight": 40,
             "median_delta_pct": 0.51, "r1_10_1_late": None, "r1_10_1_repaired": False,
             "sintef_compared": {}, "beats_sintef": []}
        self.assertEqual(rp.score_r(t), {"R0": "held", "R1": "held", "R2": "did not hold",
                                         "R3": "did not hold", "R4": "untestable", "R5": "held",
                                         "R6": "untestable"})
        t.update({"pyvrp_disagreements": ["X"], "r1_10_1_late": True, "r1_10_1_repaired": True,
                  "sintef_compared": {"R102": "better"}, "beats_sintef": ["R102"], "median_delta_pct": -0.01})
        p = rp.score_r(t)
        self.assertEqual((p["R0"], p["R3"], p["R4"], p["R6"]),
                         ("did not hold", "did not hold", "did not hold", "did not hold"))


@unittest.skipUnless(HAVE_PYVRP, "pyvrp not installed")
class WithPyVRP(unittest.TestCase):
    def solve(self, inst, routes):
        d = tempfile.mkdtemp()
        vp = os.path.join(d, inst["name"] + ".vrp")
        with open(vp, "w", encoding="utf-8") as f:
            f.write(rp.to_vrplib(inst, len(routes)))
        r = rp.run_one((vp, routes, 2, 1))
        dbl = rp.dc.check_double(routes, inst)
        bks = {"instance": inst["name"], "bks_routes": len(routes), "bks_double_distance": round(dbl["distance"], 2)}
        return r, rp.assess(bks, r, inst)

    def test_repairs_late_order(self):
        raw, r = self.solve(toy_repairable(), LATE_BKS)
        self.assertFalse(raw["init_feasible"])
        self.assertTrue(raw["feasible"])
        self.assertEqual(sorted(c for route in raw["routes"] for c in route), [1, 2, 3, 4])
        self.assertTrue(r["double_ok"])
        self.assertTrue(r["dimacs_ok"])
        self.assertTrue(r["repaired"])
        self.assertTrue(r["pyvrp_agrees"])
        self.assertLessEqual(r["num_routes"], 2)

    def test_cannot_repair_what_is_never_on_time(self):
        raw, r = self.solve(toy_unrepairable(), NEVER_BKS)
        self.assertFalse(raw["feasible"])
        self.assertFalse(r["double_ok"])
        self.assertFalse(r["repaired"])
        self.assertTrue(r["pyvrp_agrees"])


if __name__ == "__main__":
    unittest.main()
