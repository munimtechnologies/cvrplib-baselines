"""Tests for merge_ctl.py (no network). MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0."""
import json
import os
import tempfile
import unittest

import merge_ctl as M

HERE = os.path.dirname(os.path.abspath(__file__))


def v1():
    with open(os.path.join(HERE, "v1_log.txt"), encoding="utf-8") as f:
        return M.parse_log(f.read())


def v2_runs():
    runs = []
    for name, ds, db in (("C1_10_4", 100.0, 99.0), ("R1_10_1", 200.0, 190.0)):
        veh, lower = (90, 90) if name == "C1_10_4" else (100, 100)
        for arm, d, it, s in (("split", ds, 30000, 300.0), ("bound", db, 59000, 590.0)):
            runs.append({"instance": name, "arm": arm, "run": {
                "lower": lower, "vehicles": veh, "distance": d, "exact_ok": True, "below_bound": False,
                "fleet_seconds": 5.0, "solve_seconds": s, "iterations": it}})
    return runs


class ParseTest(unittest.TestCase):
    def test_v1_log(self):
        recs = v1()
        self.assertEqual(len(recs), 15)  # 7 pairs + the C1_10_4 split that finished before the stop
        first = recs[0]
        self.assertEqual((first["instance"], first["arm"]), ("R1_10_4", "split"))
        self.assertEqual(first["run"]["distance"], 46542.62)
        self.assertEqual(first["run"]["iterations"], 31902)
        self.assertFalse(any(r["run"]["below_bound"] for r in recs))
        self.assertTrue(all(r["run"]["exact_ok"] for r in recs))

    def test_none_distance(self):
        r = M.parse_log("[ 1.0s] R1_10_1/split: lower 91, 99 vehicles, exact_ok=False, distance None, "
                        "fleet 300.0 s, solve 300.0 s, 5 it")[0]
        self.assertIsNone(r["run"]["distance"])
        self.assertFalse(r["run"]["below_bound"])


class MergeTest(unittest.TestCase):
    def test_merge_replaces_redone_instances(self):
        recs = M.merge(v1(), v2_runs())
        self.assertEqual(len(recs), 18)
        c1 = [r for r in recs if r["instance"] == "C1_10_4"]
        self.assertEqual({r["source"] for r in c1}, {"v2"})
        self.assertEqual(len(c1), 2)

    def test_scores(self):
        t = M.C.tally(M.merge(v1(), v2_runs()))
        self.assertEqual(t["pairs_complete"], 9)
        self.assertEqual(t["runs"], 18)
        self.assertAlmostEqual(t["e_median_reduction_pct"], 3.44, places=2)
        self.assertAlmostEqual(t["e_median_speed_ratio"], 0.871, places=2)
        p = t["predictions"]
        self.assertEqual(p, {"K0": "held", "K1": "held", "K2": "held", "K3": "did not hold", "K4": "held",
                             "K5": "held"})

    def test_main_writes_files(self):
        with tempfile.TemporaryDirectory() as d:
            res = os.path.join(d, "results.json")
            with open(res, "w", encoding="utf-8") as f:
                json.dump({"runs": v2_runs()}, f)
            import sys
            argv = sys.argv
            sys.argv = ["merge_ctl.py", "--prior", os.path.join(HERE, "v1_log.txt"), "--results", res,
                        "--out-dir", d]
            try:
                M.main()
            finally:
                sys.argv = argv
            with open(os.path.join(d, "merged.md"), encoding="utf-8") as f:
                md = f.read()
            self.assertIn("| C1_10_4 | E | v2 |", md)
            self.assertIn("| R1_10_4 | E | v1 |", md)
            self.assertNotIn("missing", md)


if __name__ == "__main__":
    unittest.main()
