"""Tests for xltwctl.py (no network). MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0."""
import os
import tempfile
import unittest

import xltwbase as B
import xltwctl as C


def star():
    pts = [(10, 0), (0, 10), (-10, 0), (0, -10), (5, 5), (-5, -5)]
    rows = [(0, 0, 0, 0, 1000, 0)] + [(x, y, 1, 0, 1000, 1) for x, y in pts]
    return {"name": "STAR", "vehicles": 6, "capacity": 3, "rows": rows,
            "raw": [tuple(str(v) for v in r) for r in rows]}


class ArmTest(unittest.TestCase):
    def run_arm(self, arm):
        inst = star()
        b = B.lower_bound(inst, "double")
        lower = b["kc"] if arm == "split" else b["k"]
        with tempfile.TemporaryDirectory() as d:
            vp = os.path.join(d, "STAR.vrp")
            with open(vp, "w", encoding="utf-8") as f:
                f.write(B.to_vrplib(inst))
            r = C.run_arm((vp, arm, 4, 1, lower))
        return B.assess(r, inst)

    def test_split_solves_exactly_half(self):
        r = self.run_arm("split")
        self.assertEqual(r["arm"], "split")
        self.assertTrue(r["exact_ok"])
        self.assertEqual(r["vehicles"], 2)
        self.assertEqual(r["solve_seconds"], 2.0)

    def test_bound_gets_the_rest(self):
        r = self.run_arm("bound")
        self.assertTrue(r["exact_ok"])
        self.assertEqual(r["vehicles"], 2)
        self.assertGreater(r["solve_seconds"], 2.0)
        self.assertLessEqual(r["solve_seconds"], 4.0)


def fake(dist_split=100.0, dist_bound=98.0, veh=(90, 90), it=(30000, 59000), err=None):
    recs = []
    for name in C.INSTANCES:
        for arm, d, v, n, s in (("split", dist_split, veh[0], it[0], 300.0), ("bound", dist_bound, veh[1], it[1],
                                                                            590.0)):
            if name == "R1_10_1":
                d = d * 1.0 if arm == "split" else d * 0.97 / 0.98
            run = {"vehicles": v, "distance": d, "exact_ok": True, "below_bound": False, "fleet_seconds": 5.0,
                   "solve_seconds": s, "iterations": n}
            rec = {"instance": name, "arm": arm, "run": run}
            if err == (name, arm):
                del rec["run"]
                rec["error"] = "boom"
            recs.append(rec)
    return recs


class ScoreTest(unittest.TestCase):
    def test_all_held(self):
        t = C.tally(fake())
        self.assertEqual(t["runs_expected"], 18)
        self.assertEqual(t["e_compared"], 8)
        self.assertAlmostEqual(t["e_median_reduction_pct"], 2.0, places=3)
        self.assertAlmostEqual(t["r1_10_1"]["reduction_pct"], 3.0, places=3)
        self.assertAlmostEqual(t["e_median_speed_ratio"], 100.0 / 100.0, places=1)
        self.assertEqual(set(t["predictions"].values()), {"held"})

    def test_small_gain_and_speed_gap(self):
        t = C.tally(fake(dist_bound=99.5, it=(45000, 59000)))
        p = t["predictions"]
        self.assertEqual(p["K2"], "did not hold")  # 0.5% < 1.0%
        self.assertEqual(p["K3"], "held")
        self.assertEqual(p["K4"], "did not hold")  # R1_10_1 about 1.5%
        self.assertEqual(p["K5"], "did not hold")  # 150 / 100 it/s

    def test_large_gain_fails_k3_and_longer_fails_k1(self):
        self.assertEqual(C.tally(fake(dist_bound=90.0))["predictions"]["K3"], "did not hold")
        self.assertEqual(C.tally(fake(dist_bound=100.5))["predictions"]["K1"], "did not hold")

    def test_error_and_vehicle_mismatch(self):
        t = C.tally(fake(err=("R1_10_4", "bound")))
        self.assertEqual(t["predictions"]["K0"], "did not hold")
        self.assertEqual(t["predictions"]["K1"], "untestable")
        t = C.tally(fake(veh=(91, 90)))
        self.assertEqual(t["predictions"]["K0"], "did not hold")
        self.assertEqual(t["predictions"]["K2"], "untestable")

    def test_instances(self):
        self.assertEqual(len(C.INSTANCES), 9)
        self.assertIn("R1_10_1", C.INSTANCES)


if __name__ == "__main__":
    unittest.main()
