"""Tests for fleet_double.py (no network). MV2 of Munim, Inc. Apache-2.0."""
import os
import tempfile
import unittest

import fleet_double as fd


def toy():
    # depot (0,0); customer 1 at (3,4): 5.0 away; customer 2 at (1,1): 1.41421... away
    return {"name": "TOY", "vehicles": 3, "capacity": 10,
            "rows": [(0, 0, 0, 0, 100, 0), (3, 4, 3, 0, 50, 10), (1, 1, 3, 0, 1.4, 10)]}


def star():
    # six customers around the depot, demand 1 each, capacity 3: at least 2 vehicles
    pts = [(10, 0), (0, 10), (-10, 0), (0, -10), (5, 5), (-5, -5)]
    rows = [(0, 0, 0, 0, 1000, 0)] + [(x, y, 1, 0, 1000, 1) for x, y in pts]
    return {"name": "STAR", "vehicles": 6, "capacity": 3, "rows": rows}


class TableTest(unittest.TestCase):
    def test_sintef_table(self):
        self.assertEqual(len(fd.SINTEF), 60)
        self.assertEqual(fd.SINTEF["C1_10_1"], (100, 42478.95))
        self.assertEqual(fd.SINTEF["RC2_10_10"], (18, 21834.94))
        self.assertEqual(fd.SINTEF["R1_10_1"], (100, 53380.18))
        self.assertEqual(fd.family("RC1_10_7"), "RC1")

    def test_parse_sintef(self):
        html = ("<tr><td>c1_10_1<sup>q</sup></td><td>100</td><td>42478.95</td><td>GH</td></tr>"
                "<tr><td>rc2_10_10</td><td>18</td><td>21834.94</td><td>SCR</td></tr>")
        self.assertEqual(fd.parse_sintef(html), {"C1_10_1": (100, 42478.95), "RC2_10_10": (18, 21834.94)})

    def test_parse_ids(self):
        self.assertEqual(fd.parse_ids("676-678,700"), ["676", "677", "678", "700"])


class CheckTest(unittest.TestCase):
    def test_late_in_double(self):
        r = fd.check_double([[1], [2]], toy())
        self.assertFalse(r["ok"])
        self.assertEqual(r["late"], 1)
        self.assertAlmostEqual(r["distance"], 10 + 2 * 2 ** 0.5, places=9)

    def test_on_time(self):
        inst = toy()
        inst["rows"][2] = (1, 1, 3, 0, 2, 10)
        self.assertTrue(fd.check_double([[1], [2]], inst)["ok"])

    def test_structure(self):
        inst = toy()
        self.assertIn("not visited", fd.check_double([[1]], inst)["reason"])
        self.assertIn("repeated", fd.check_double([[1], [1, 2]], inst)["reason"])
        inst["capacity"] = 5
        self.assertEqual(fd.check_double([[1, 2]], inst)["reason"], "over capacity")

    def test_versus(self):
        self.assertEqual(fd.versus_sintef(19, 100.0, (20, 50.0)), "better")
        self.assertEqual(fd.versus_sintef(20, 50.001, (20, 50.0)), "equal")
        self.assertEqual(fd.versus_sintef(20, 50.2, (20, 50.0)), "worse")
        self.assertEqual(fd.versus_sintef(21, 10.0, (20, 50.0)), "worse")

    def test_ceil(self):
        self.assertEqual(list(fd.ceil_scaled([1.41421356, 2.0])), [1415, 2000])


class SolveTest(unittest.TestCase):
    def test_run_one_tiny(self):
        inst = star()
        with tempfile.TemporaryDirectory() as d:
            vp = os.path.join(d, "STAR.vrp")
            with open(vp, "w", encoding="utf-8") as f:
                f.write(fd.to_vrplib(inst))
            r = fd.run_one((vp, 4, 1))
        self.assertTrue(r["feasible"])
        self.assertEqual(sorted(c for route in r["routes"] for c in route), [1, 2, 3, 4, 5, 6])
        self.assertGreaterEqual(len(r["routes"]), 2)
        self.assertLessEqual(len(r["routes"]), r["fleet"])
        self.assertTrue(fd.check_double(r["routes"], inst)["ok"])
        rec = {"sintef": (2, 1.0)}
        a = fd.assess(rec, dict(r), inst)
        self.assertTrue(a["pyvrp_agrees"])
        self.assertEqual(a["vehicles_over_sintef"], len(r["routes"]) - 2)


class ScoreTest(unittest.TestCase):
    def rec(self, name, over=0, gap=1.0, ok=True):
        fam = fd.family(name)
        v = fd.SINTEF[name][0]
        return {"instance": name, "family": fam, "bks_routes": v + 5, "sintef": list(fd.SINTEF[name]),
                "run": {"feasible": ok, "double_ok": ok, "structure_ok": True, "pyvrp_agrees": True,
                        "vehicles": v + over, "vehicles_over_sintef": over if ok else None,
                        "distance_over_sintef_pct": gap if ok and over == 0 else None,
                        "vs_sintef": None if not ok else ("worse" if over >= 0 else "better")}}

    def test_held(self):
        recs = []
        for name in sorted(fd.SINTEF):
            fam = fd.family(name)
            over = 1 if fam in ("R1", "RC1") else 0
            recs.append(self.rec(name, over))
        t = fd.tally_recs(recs)
        self.assertEqual(t["match_vehicles"], 40)
        self.assertEqual(set(t["predictions"].values()), {"held"})
        self.assertEqual(len(t["fewer_routes_than_cvrplib_bks"]), 60)

    def test_failures(self):
        recs = [self.rec(name, 2) for name in sorted(fd.SINTEF)]
        recs[0] = self.rec(recs[0]["instance"], -1)
        recs[1] = self.rec(recs[1]["instance"], ok=False)
        t = fd.tally_recs(recs)
        p = t["predictions"]
        self.assertEqual(p["L1"], "did not hold")
        self.assertEqual(p["L2"], "did not hold")
        self.assertEqual(p["L3"], "did not hold")
        self.assertEqual(p["L4"], "did not hold")
        self.assertEqual(p["L5"], "held")
        self.assertEqual(p["L6"], "untestable")
        self.assertEqual(t["beats_sintef"], [recs[0]["instance"]])


if __name__ == "__main__":
    unittest.main()
