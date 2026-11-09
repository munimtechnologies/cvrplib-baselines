"""Tests for filt.py. MV2 of Munim, Inc. Apache-2.0."""
import json
import os
import tempfile
import unittest

import filt


def rec(name, limit, sigterm):
    return {"instance": name, "limit": limit, "sigterm_at": sigterm}


class Filter(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.o = os.path.join(self.d, "out")
        files = {
            "b1": [rec("A", 100.0, None), rec("B", 100.0, 400.0)],
            "b2": [rec("C", 100.0, 100.3)],
            "b3": [rec("D", 100.0, 900.0)],
            "b1ra": [rec("B", 100.0, None)], "b1rb": [], "b2r": [],
            "b3ra": [rec("D", 100.0, 300.0)], "b3rb": [],
        }
        for k, runs in files.items():
            with open(os.path.join(self.d, "results-%s.json" % k), "w") as f:
                json.dump({"scale": 30.0, "runs": runs}, f)

    def test_replaces_and_reports(self):
        rep = filt.filt(self.d, self.o)
        with open(os.path.join(self.o, "results-b1f.json")) as f:
            self.assertEqual([r["instance"] for r in json.load(f)["runs"]], ["A"])
        with open(os.path.join(self.o, "results-b2f.json")) as f:
            self.assertEqual([r["instance"] for r in json.load(f)["runs"]], ["C"])
        with open(os.path.join(self.o, "results-b3f.json")) as f:
            self.assertEqual(json.load(f)["runs"], [])
        self.assertEqual(sorted(r["instance"] for r in rep["replaced"]), ["B", "D"])
        self.assertEqual([r["instance"] for r in rep["kept_frozen_by_rule"]], ["D"])

    def test_late_without_rerun_is_an_error(self):
        with open(os.path.join(self.d, "results-b1ra.json"), "w") as f:
            json.dump({"scale": 30.0, "runs": []}, f)
        with self.assertRaises(SystemExit):
            filt.filt(self.d, self.o)


if __name__ == "__main__":
    unittest.main()
