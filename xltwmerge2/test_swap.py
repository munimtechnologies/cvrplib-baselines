"""Tests for swap.py. MV2 of Munim, Inc. Apache-2.0."""
import json
import os
import tempfile
import unittest

import swap


def rec(name, vehicles, sigterm=None, ok=True, seed=20261104):
    return {"instance": name, "vehicles": vehicles, "distance": 10 * vehicles, "limit": 100.0, "seed": seed,
            "sigterm_at": sigterm, "sigkill_at": None, "exact_ok": ok, "cost_line_ok": ok,
            "other_stdout_lines": 0}


class Swap(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.inp = os.path.join(self.d, "in")
        self.flt = os.path.join(self.d, "flt")
        self.out = os.path.join(self.d, "out")
        for p in (self.inp, self.flt, os.path.join(self.inp, "rerun-v1"), os.path.join(self.inp, "rerun-v2")):
            os.makedirs(p, exist_ok=True)
        parts = {name: [] for _, name in swap.V1_PARTS}
        parts["results-a.json"] = [rec("XLTW-Test-n10", 5), rec("XLTW-Test-n20", 6)]
        parts["results-b1f.json"] = [rec("XLTW-Test-n30", 7)]
        parts["results-b2r.json"] = [rec("XLTW-Test-n40", 9, sigterm=101.0)]
        for where, name in swap.V1_PARTS:
            d = self.inp if where == "in" else self.flt
            with open(os.path.join(d, name), "w") as f:
                json.dump({"scale": 30.0, "runs": parts[name]}, f)
        self.clean = {"XLTW-Test-n20": "rerun-v1/results-r20.json", "XLTW-Test-n40": "rerun-v2/results-r40.json"}
        self.write_rerun("rerun-v1/results-r20.json", [rec("XLTW-Test-n20", 4)])
        self.write_rerun("rerun-v2/results-r40.json", [rec("XLTW-Test-n40", 8)])

    def write_rerun(self, rel, runs, scale=30.0):
        with open(os.path.join(self.inp, rel), "w") as f:
            json.dump({"scale": scale, "runs": runs}, f)

    def instances(self, name):
        with open(os.path.join(self.out, name)) as f:
            return [r["instance"] for r in json.load(f)["runs"]]

    def test_replaces_each_once(self):
        rep = swap.swap(self.inp, self.flt, self.out, clean=self.clean)
        self.assertEqual(self.instances("results-a.json"), ["XLTW-Test-n10"])
        self.assertEqual(self.instances("results-b1f.json"), ["XLTW-Test-n30"])
        self.assertEqual(self.instances("results-b2r.json"), [])
        self.assertEqual(self.instances("results-r20.json"), ["XLTW-Test-n20"])
        self.assertEqual(self.instances("results-r40.json"), ["XLTW-Test-n40"])
        by = {r["instance"]: r for r in rep["replaced"]}
        self.assertEqual((by["XLTW-Test-n20"]["old_vehicles"], by["XLTW-Test-n20"]["new_vehicles"]), (6, 4))
        self.assertEqual(by["XLTW-Test-n40"]["old_part"], "results-b2r.json")
        self.assertEqual(len(rep["merge_list"]), len(swap.V1_PARTS) + 2)
        names = []
        for p in rep["merge_list"]:
            with open(p) as f:
                names += [r["instance"] for r in json.load(f)["runs"]]
        self.assertEqual(sorted(names), ["XLTW-Test-n10", "XLTW-Test-n20", "XLTW-Test-n30", "XLTW-Test-n40"])
        with open(os.path.join(self.out, "merge-list.txt")) as f:
            self.assertEqual(f.read().split(","), rep["merge_list"])

    def test_invalid_rerun_refused(self):
        self.write_rerun("rerun-v2/results-r40.json", [rec("XLTW-Test-n40", 8, sigterm=101.0)])
        with self.assertRaises(SystemExit):
            swap.swap(self.inp, self.flt, self.out, clean=self.clean)

    def test_wrong_seed_or_scale_refused(self):
        self.write_rerun("rerun-v2/results-r40.json", [rec("XLTW-Test-n40", 8, seed=1)])
        with self.assertRaises(SystemExit):
            swap.swap(self.inp, self.flt, self.out, clean=self.clean)
        self.write_rerun("rerun-v2/results-r40.json", [rec("XLTW-Test-n40", 8)], scale=10.0)
        with self.assertRaises(SystemExit):
            swap.swap(self.inp, self.flt, self.out, clean=self.clean)

    def test_missing_old_record_refused(self):
        clean = dict(self.clean)
        clean["XLTW-Test-n99"] = "rerun-v1/results-r20.json"
        with self.assertRaises(SystemExit):
            swap.swap(self.inp, self.flt, self.out, clean=clean)

    def test_real_table_has_the_seven(self):
        self.assertEqual(sorted(int(k.rsplit("n", 1)[1]) for k in swap.CLEAN),
                         [7037, 8389, 8575, 9160, 9363, 9571, 10001])


if __name__ == "__main__":
    unittest.main()
