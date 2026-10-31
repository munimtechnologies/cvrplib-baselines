"""Tests for xltwbase.py (no network). MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0."""
import os
import tempfile
import unittest

import xltwbase as B
import xltwlb as X


def inst_of(rows, capacity, vehicles=None, name="T"):
    return {"name": name, "vehicles": vehicles, "capacity": capacity, "rows": rows,
            "raw": [tuple(str(v) for v in r) for r in rows]}


def toy():
    # depot (0,0); customer 1 at (3,4): 5.0 away; customer 2 at (1,1): 1.41421... away, due 1.4 (late in double)
    return inst_of([(0, 0, 0, 0, 100, 0), (3, 4, 3, 0, 50, 10), (1, 1, 3, 0, 1.4, 10)], 10, 3, "TOY")


def star():
    # six customers around the depot, demand 1 each, capacity 3: at least 2 vehicles
    pts = [(10, 0), (0, 10), (-10, 0), (0, -10), (5, 5), (-5, -5)]
    return inst_of([(0, 0, 0, 0, 1000, 0)] + [(x, y, 1, 0, 1000, 1) for x, y in pts], 3, 6, "STAR")


class RoundTest(unittest.TestCase):
    def test_funcs(self):
        self.assertEqual(list(B.rf_double([1.41421356, 2.0])), [1415, 2000])
        self.assertEqual(list(B.rf_dimacs([1.41421356, 2.0, 12.3, 0.7])), [14, 20, 123, 7])
        self.assertEqual(list(B.rf_round([2.5, 2.49, 3.0, 0.5])), [3, 2, 3, 1])

    def test_vrplib_copy(self):
        inst = star()
        back = X.parse_vrplib(B.to_vrplib(inst))
        self.assertEqual(back["rows"], inst["rows"])
        self.assertEqual((back["vehicles"], back["capacity"]), (6, 3))
        inst["vehicles"] = None
        self.assertIn("VEHICLES : 6", B.to_vrplib(inst))


class CheckTest(unittest.TestCase):
    def test_late_in_double_on_time_truncated(self):
        inst = toy()
        r = B.check_exact([[1], [2]], inst, "double")
        self.assertFalse(r["ok"])
        self.assertEqual(r["late"], 1)
        self.assertAlmostEqual(r["distance"], 10 + 2 * 2 ** 0.5, places=9)
        r = B.check_exact([[1], [2]], inst, "dimacs")  # 1.41421 -> 1.4: arrives exactly at 1.4
        self.assertTrue(r["ok"])
        self.assertAlmostEqual(r["distance"], 12.8, places=9)
        r = B.check_exact([[1], [2]], inst, "round")
        self.assertTrue(r["ok"])
        self.assertAlmostEqual(r["distance"], 12.0, places=9)

    def test_depot_return_late(self):
        inst = toy()
        rows = list(inst["rows"])
        rows[0] = (0, 0, 0, 0, 14, 0)  # customer 1: arrive 5, serve 10, back at 20 > 14
        inst = inst_of(rows, 10, 3)
        r = B.check_exact([[1], [2]], inst, "round")
        self.assertFalse(r["ok"])
        self.assertEqual(r["late"], 1)

    def test_structure(self):
        inst = toy()
        self.assertIn("not visited", B.check_exact([[1]], inst, "double")["reason"])
        self.assertIn("repeated", B.check_exact([[1], [1, 2]], inst, "double")["reason"])
        inst["capacity"] = 5
        self.assertEqual(B.check_exact([[1, 2]], inst, "double")["reason"], "over capacity")

    def test_agrees_with_double_checker_style(self):
        inst = toy()
        rows = list(inst["rows"])
        rows[2] = (1, 1, 3, 0, 2, 10)
        inst = inst_of(rows, 10, 3)
        self.assertTrue(B.check_exact([[1], [2]], inst, "double")["ok"])


class BoundTest(unittest.TestCase):
    def test_star_bound(self):
        b = B.lower_bound(star(), "double")
        self.assertEqual((b["kc"], b["kb"]), (2, 2))
        self.assertEqual(b["k"], max(b["kb"], b["kt"]))
        self.assertTrue(b["clique_verified"])

    def test_tight_windows_raise_bound(self):
        # four customers far apart, each due soon after the earliest arrival: one route each
        rows = [(0, 0, 0, 0, 1000, 0)] + [(x, y, 1, 100, 101, 10) for x, y in
                                          [(50, 0), (0, 50), (-50, 0), (0, -50)]]
        b = B.lower_bound(inst_of(rows, 100), "double")
        self.assertEqual(b["kc"], 1)
        self.assertEqual(b["k"], 4)


class SolveTest(unittest.TestCase):
    def run_star(self, conv):
        inst = star()
        lower = B.lower_bound(inst, conv)["k"]
        with tempfile.TemporaryDirectory() as d:
            vp = os.path.join(d, "STAR.vrp")
            with open(vp, "w", encoding="utf-8") as f:
                f.write(B.to_vrplib(inst))
            r = B.run_one((vp, conv, 4, 1, lower))
        return inst, B.assess(r, inst)

    def test_run_one_each_convention(self):
        for conv in ("double", "dimacs", "round"):
            inst, r = self.run_star(conv)
            self.assertTrue(r["feasible"], conv)
            self.assertTrue(r["exact_ok"], conv)
            self.assertTrue(r["pyvrp_agrees"], conv)
            self.assertFalse(r["below_bound"], conv)
            self.assertEqual(r["vehicles"], 2, conv)
            self.assertTrue(r["stopped_at_bound"], conv)
            self.assertLessEqual(r["fleet_seconds"], 2.0 + 0.5, conv)  # at most half the budget
            self.assertGreater(r["solve_seconds"], 1.5, conv)  # the rest went to distance

    def test_tight_windows_stop_fleet_search(self):
        rows = [(0, 0, 0, 0, 1000, 0)] + [(x, y, 1, 100, 101, 10) for x, y in
                                          [(50, 0), (0, 50), (-50, 0), (0, -50)]]
        inst = inst_of(rows, 100, 4, "TIGHT")
        with tempfile.TemporaryDirectory() as d:
            vp = os.path.join(d, "TIGHT.vrp")
            with open(vp, "w", encoding="utf-8") as f:
                f.write(B.to_vrplib(inst))
            r = B.assess(B.run_one((vp, "double", 4, 1, 4)), inst)
        self.assertEqual(r["fleet_solves"], 0)  # already at K = 4: no fleet search at all
        self.assertTrue(r["exact_ok"])
        self.assertEqual(r["vehicles"], 4)


class ScoreTest(unittest.TestCase):
    def recs(self, shift=-0.02, veh=0, err=False):
        out = []
        for name, (i, v, dist, fsec, it) in B.VRPTWL.items():
            run = {"conv": "double", "vehicles": v + veh, "lower": v, "exact_ok": True, "structure_ok": True,
                   "pyvrp_agrees": True, "below_bound": False, "distance": round(dist * (1 + shift), 2),
                   "fleet_seconds": 30.0 if name == "R1_10_1" else fsec, "fleet_solves": 3,
                   "stopped_at_bound": True, "solve_seconds": 570.0, "iterations": 2 * it}
            out.append({"instance": name, "conv": "double", "group": B.group_of(name),
                        "bound": {"kc": v, "kb": v, "kt": 1, "k": v, "clique_verified": True}, "run": run})
        for name, conv in B.CONV_RUNS:
            out.append({"instance": name, "conv": conv, "group": "conv",
                        "bound": {"kc": 90, "kb": 90, "kt": 1, "k": 90, "clique_verified": True},
                        "run": {"conv": conv, "vehicles": 95, "lower": 90, "exact_ok": True, "structure_ok": True,
                                "pyvrp_agrees": True, "below_bound": False, "distance": 1.0, "fleet_seconds": 9.0,
                                "fleet_solves": 2, "stopped_at_bound": False, "solve_seconds": 111.0,
                                "iterations": 10}})
        if err:
            del out[-1]["run"]
            out[-1]["error"] = "boom"
        return out

    def test_all_held(self):
        t = B.tally_study(self.recs())
        self.assertEqual(t["runs_expected"], 17)
        self.assertEqual(t["e_shorter"], 8)
        self.assertAlmostEqual(t["e_median_reduction_pct"], 2.0, places=1)
        self.assertEqual(set(t["predictions"].values()), {"held"})
        self.assertEqual(len(t["conv_runs"]), 4)

    def test_failures(self):
        t = B.tally_study(self.recs(shift=0.01, veh=1, err=True))
        p = t["predictions"]
        self.assertEqual(p["Q0"], "did not hold")
        self.assertEqual(p["Q1"], "did not hold")
        self.assertEqual(p["Q2"], "did not hold")
        self.assertEqual(p["Q3"], "did not hold")
        self.assertEqual(p["Q4"], "untestable")
        self.assertEqual(p["Q5"], "did not hold")

    def test_groups_cover_table(self):
        names = [n for g in B.GROUPS.values() for n in g]
        self.assertEqual(sorted(names), sorted(B.VRPTWL))
        self.assertEqual(len(names), 13)


if __name__ == "__main__":
    unittest.main()
