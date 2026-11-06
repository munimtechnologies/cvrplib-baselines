"""Tests for xltwff: the solver patch (getff.py) and the scoring of H0-H5 (ffrun.py), on synthetic records.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.
"""
import copy
import json
import os
import tempfile
import unittest

import ffrun
import getff

SRC = (b'START = 0\nVERSION = "0.1.0"\nCONV = "round"\nFLEET_FRAC = 0.5\nTERM = {}\n'
       b"    fleet_deadline = t_fleet + FLEET_FRAC * max(deadline - t_fleet, 0.0)\n")


def rec(rid, vehicles, distance, peak=0.2, **kw):
    r = {"id": rid, "instance": ffrun.BY_ID.get(rid, (None, None, "x"))[2] if rid in ffrun.BY_ID else "x",
         "customers": 1000, "limit": 1800.0, "harness_frozen": False, "self_stopped": True, "exit": 0,
         "feasible": True, "cost_line_ok": True, "bad_line_count": 0, "numbering_errors": 0,
         "vehicles": vehicles, "distance": distance, "peak_gb": peak, "watchdog": None, "slack": 5.0,
         "solver_stats": {"fleet_seconds": 100.0, "fleet_solves": 5}, "trajectory": []}
    r.update(kw)
    return r


BUILD = {"tag": "cp312", "python": "3.12.15", "pins_ok": True}
REF = {"runs": [rec("F1", 34, 83690), rec("F2", 70, 139000), rec("F3", 108, 112655), rec("F4", 28, 85000)]}


def hs(v1=34, v2=70, v3=108, v4=28, d1=84000, d2=139500, d3=113000, d4=85500):
    return [rec("H1", v1, d1), rec("H2", v2, d2), rec("H3", v3, d3), rec("H4", v4, d4)]


class Patch(unittest.TestCase):
    def test_patch_changes_exactly_the_two_lines(self):
        out = getff.patch_source(SRC)
        self.assertIn(b"FLEET_FRAC = 0.8  # xltwff", out)
        self.assertNotIn(b"\nFLEET_FRAC = 0.5\n", out)
        self.assertIn(b'VERSION = "0.1.0+ff08"\n', out)
        self.assertIn(b"FLEET_FRAC * max(deadline", out)
        self.assertEqual(len(out.splitlines()), len(SRC.splitlines()))

    def test_patch_refuses_missing_or_duplicate(self):
        with self.assertRaises(ValueError):
            getff.patch_source(SRC.replace(b"FLEET_FRAC = 0.5\n", b"FLEET_FRAC = 0.6\n"))
        with self.assertRaises(ValueError):
            getff.patch_source(SRC + b"FLEET_FRAC = 0.5\n")

    def test_patched_module_value(self):
        ns = {}
        exec(getff.patch_source(SRC).split(b"    fleet_deadline")[0].decode(), ns)  # noqa: S102 - test only
        self.assertEqual(ns["FLEET_FRAC"], 0.8)

    def test_fetch_with_fake_getter(self):
        def getter(url):
            name = url.rsplit("/", 1)[1]
            return SRC if name == "solver.py" else ("# %s\n" % name).encode()
        with tempfile.TemporaryDirectory() as d:
            m = getff.fetch(dest=d, getter=getter)
            self.assertTrue(m["patched"])
            with open(os.path.join(d, "solver.py"), "rb") as f:
                self.assertIn(b"FLEET_FRAC = 0.8", f.read())
            for name in getff.PKG_FILES + getff.HARNESS_FILES:
                self.assertTrue(os.path.exists(os.path.join(d, name)), name)
            with open(os.path.join(d, "pkg-manifest.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f)["harness_commit"], getff.HARNESS_COMMIT)

    def test_wait_prereg_identical_and_crlf(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "prereg.md")
            with open(p, "wb") as f:
                f.write(b"a\r\nb\n")
            self.assertTrue(getff.wait_prereg(p, getter=lambda u, tries=1: b"a\nb\n", sleep=lambda s: None))

    def test_wait_prereg_gives_up(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "prereg.md")
            with open(p, "wb") as f:
                f.write(b"x\n")
            with self.assertRaises(SystemExit):
                getff.wait_prereg(p, getter=lambda u, tries=1: b"y\n", deadline=0, sleep=lambda s: None)


class Score(unittest.TestCase):
    def test_all_equal(self):
        p = ffrun.score(BUILD, False, hs(), REF, True)
        self.assertEqual(p["H0"], "held")
        self.assertEqual(p["H1"], "held")
        self.assertEqual(p["H2"], "did not hold")
        self.assertEqual(p["H3"], "held")
        self.assertEqual(p["H4"], "held")      # every distance within 1%
        self.assertEqual(p["H5"], "held")

    def test_one_fewer(self):
        p = ffrun.score(BUILD, False, hs(v3=107), REF, True)
        self.assertEqual((p["H1"], p["H2"], p["H3"]), ("held", "held", "held"))

    def test_big_saving_breaks_h3(self):
        p = ffrun.score(BUILD, False, hs(v1=32, v3=105), REF, True)  # 5 fewer
        self.assertEqual(p["H3"], "did not hold")
        p = ffrun.score(BUILD, False, hs(v1=32, v3=106), REF, True)  # exactly 4 fewer
        self.assertEqual(p["H3"], "held")

    def test_more_vehicles_breaks_h1(self):
        p = ffrun.score(BUILD, False, hs(v2=71), REF, True)
        self.assertEqual(p["H1"], "did not hold")
        p = ffrun.score(BUILD, False, hs(v2=71, v3=107), REF, True)  # one more, one fewer: sums equal
        self.assertEqual((p["H1"], p["H2"]), ("held", "held"))

    def test_h4_distance(self):
        p = ffrun.score(BUILD, False, hs(d1=int(83690 * 1.0101)), REF, True)
        self.assertEqual(p["H4"], "did not hold")
        p = ffrun.score(BUILD, False, hs(d1=int(83690 * 1.0099)), REF, True)
        self.assertEqual(p["H4"], "held")
        # only instances with equal vehicle counts are compared
        p = ffrun.score(BUILD, False, hs(v1=33, d1=99999), REF, True)
        self.assertEqual(p["H4"], "held")

    def test_h4_untestable_when_none_equal(self):
        p = ffrun.score(BUILD, False, hs(v1=33, v2=69, v3=107, v4=27), REF, True)
        self.assertTrue(p["H4"].startswith("untestable"))

    def test_h5(self):
        h = hs()
        h[2]["peak_gb"] = 0.61
        self.assertEqual(ffrun.score(BUILD, False, h, REF, True)["H5"], "did not hold")
        h = hs()
        h[0]["watchdog"] = "XLTW_WATCHDOG deadline at 2217.0s, prints 30"
        self.assertEqual(ffrun.score(BUILD, False, h, REF, True)["H5"], "did not hold")

    def test_gate(self):
        for args in ((BUILD, True, hs(), REF, True), (BUILD, False, hs(), REF, False),
                     (dict(BUILD, pins_ok=False), False, hs(), REF, True), (BUILD, False, hs()[:3], REF, True)):
            p = ffrun.score(*args)
            self.assertEqual(p["H0"], "did not hold")
            self.assertTrue(p["H1"].startswith("untestable"))
        h = hs()
        h[1]["harness_frozen"] = True
        self.assertEqual(ffrun.score(BUILD, False, h, REF, True)["H0"], "did not hold")
        ref = copy.deepcopy(REF)
        ref["runs"][3]["self_stopped"] = False
        self.assertEqual(ffrun.score(BUILD, False, hs(), ref, True)["H0"], "did not hold")

    def test_compare_rows_and_md(self):
        rows = ffrun.compare_rows(hs(v3=107), REF["runs"])
        self.assertEqual([r["id"] for r in rows], ["H1", "H2", "H3", "H4"])
        self.assertEqual((rows[2]["h_vehicles"], rows[2]["f_vehicles"], rows[2]["k_star"]), (107, 108, 81))
        res = {"network_reachable": False, "build": BUILD, "patched": True, "runs": hs(), "compare": rows,
               "predictions": ffrun.score(BUILD, False, hs(), REF, True)}
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.md")
            ffrun.write_md(p, res)
            with open(p, encoding="utf-8") as f:
                txt = f.read()
            self.assertIn("| H3 | XLTW-Test-n1608 | 81 | 107 | 108 |", txt)

    def test_limits_and_runs(self):
        self.assertEqual([ffrun.limit_for(r[3]) for r in ffrun.RUNS], [2219.4, 2556.0, 2892.6, 3312.0])
        self.assertEqual([r[1] for r in ffrun.RUNS], ["F1", "F2", "F3", "F4"])


if __name__ == "__main__":
    unittest.main()
