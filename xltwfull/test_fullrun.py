"""Tests for xltwfull (fullrun.py, getpkg.py). Standard library only; no network, no solver.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fullrun as F  # noqa: E402
import getpkg as G  # noqa: E402


def rec(rid, vehicles, **kw):
    _, name, n, va, da, k, ks = F.BY_ID[rid]
    r = {"id": rid, "instance": name, "customers": n, "limit": F.limit_for(n), "exit": 0, "self_stopped": True,
         "harness_frozen": False, "feasible": True, "cost_line_ok": True, "bad_line_count": 0,
         "numbering_errors": 0, "vehicles": vehicles, "distance": 1, "peak_gb": 0.3, "watchdog": None,
         "slack": 20.0, "trajectory": [{"t": 5.0, "vehicles": vehicles, "cost": 1}], "solver_stats": {}}
    r.update(kw)
    return F.attach_reference(r)


BUILD = {"tag": "cp312", "pins_ok": True, "python": "3.12"}


class Basics(unittest.TestCase):
    def test_limits_are_the_challenge_rule(self):
        self.assertEqual([F.limit_for(r[2]) for r in F.RUNS], [2219.4, 2556.0, 2892.6, 3312.0])

    def test_reference_numbers(self):
        self.assertEqual(sum(r[3] for r in F.RUNS), 249)   # part-a vehicles
        self.assertEqual(sum(r[6] for r in F.RUNS), 173)   # K*

    def test_trajectory_and_first_time(self):
        tr = F.trajectory([(1.234, [[1], [2], [3]], 30.0), (9.0, [[1, 2], [3]], 25.0), (20.0, [[1, 2], [3]], 24.0)])
        self.assertEqual([p["vehicles"] for p in tr], [3, 2, 2])
        self.assertEqual(tr[0]["t"], 1.23)
        self.assertEqual(F.first_time_at(tr, 2), 9.0)
        self.assertIsNone(F.first_time_at(tr, 1))

    def test_valid(self):
        self.assertTrue(F.valid(rec("F1", 30)))
        for bad in ({"harness_frozen": True}, {"self_stopped": False}, {"exit": -9}, {"feasible": False},
                    {"cost_line_ok": False}, {"bad_line_count": 1}, {"numbering_errors": 2}):
            self.assertFalse(F.valid(rec("F1", 30, **bad)), bad)
        self.assertFalse(F.valid({"id": "F1", "error": "x"}))


class Scoring(unittest.TestCase):
    def test_all_hold(self):
        recs = [rec("F1", 30), rec("F2", 60), rec("F3", 100), rec("F4", 25)]  # 215
        p = F.score(BUILD, False, recs)
        self.assertEqual(set(p.values()), {"held"}, p)

    def test_band_edges(self):
        p = F.score(BUILD, False, [rec("F1", 35), rec("F2", 72), rec("F3", 92), rec("F4", 25)])  # 224
        self.assertEqual((p["F2"], p["F3"]), ("held", "held"))
        p = F.score(BUILD, False, [rec("F1", 35), rec("F2", 72), rec("F3", 93), rec("F4", 25)])  # 225
        self.assertEqual(p["F2"], "did not hold")
        p = F.score(BUILD, False, [rec("F1", 27), rec("F2", 60), rec("F3", 100), rec("F4", 21)])  # 208
        self.assertEqual(p["F3"], "held")
        p = F.score(BUILD, False, [rec("F1", 27), rec("F2", 60), rec("F3", 100), rec("F4", 20)])  # 207
        self.assertEqual(p["F3"], "did not hold")

    def test_f1_f4_f5(self):
        p = F.score(BUILD, False, [rec("F1", 36), rec("F2", 60), rec("F3", 100), rec("F4", 25)])
        self.assertEqual(p["F1"], "did not hold")
        p = F.score(BUILD, False, [rec("F1", 27), rec("F2", 47), rec("F3", 100), rec("F4", 25)])
        self.assertEqual(p["F4"], "did not hold")
        p = F.score(BUILD, False, [rec("F1", 27), rec("F2", 60), rec("F3", 100), rec("F4", 25)])
        self.assertEqual(p["F4"], "held")
        p = F.score(BUILD, False, [rec("F1", 30), rec("F2", 60), rec("F3", 100, peak_gb=0.61), rec("F4", 25)])
        self.assertEqual(p["F5"], "did not hold")
        p = F.score(BUILD, False, [rec("F1", 30, watchdog="XLTW_WATCHDOG deadline at 2210.0s, prints 9"),
                                   rec("F2", 60), rec("F3", 100), rec("F4", 25)])
        self.assertEqual(p["F5"], "did not hold")

    def test_gate(self):
        ok = [rec("F1", 30), rec("F2", 60), rec("F3", 100), rec("F4", 25)]
        self.assertEqual(F.score(BUILD, True, ok)["F0"], "did not hold")
        self.assertEqual(F.score(dict(BUILD, pins_ok=False), False, ok)["F0"], "did not hold")
        p = F.score(BUILD, False, ok[:3])
        self.assertEqual(p["F0"], "did not hold")
        self.assertTrue(p["F2"].startswith("untestable"))
        p = F.score(BUILD, False, ok[:3] + [rec("F4", 25, harness_frozen=True)])
        self.assertEqual(p["F0"], "did not hold")


class Merge(unittest.TestCase):
    def _part(self, d, name, runs, net=False):
        path = os.path.join(d, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"network_reachable": net, "build": BUILD, "runs": runs}, f)
        return path

    def test_merge_scores_once(self):
        with tempfile.TemporaryDirectory() as d:
            a = self._part(d, "a.json", [rec("F1", 30), rec("F3", 100)])
            b = self._part(d, "b.json", [rec("F2", 60), rec("F4", 25)])
            ns = type("A", (), {"merge": a + "," + b, "out_dir": d})()
            res = F.merge(ns)
            self.assertEqual([r["id"] for r in res["runs"]], ["F1", "F2", "F3", "F4"])
            self.assertEqual(set(res["predictions"].values()), {"held"})
            self.assertTrue(os.path.exists(os.path.join(d, "xltwfull", "results.md")))

    def test_merge_refuses_duplicates(self):
        with tempfile.TemporaryDirectory() as d:
            a = self._part(d, "a.json", [rec("F1", 30)])
            b = self._part(d, "b.json", [rec("F1", 31)])
            ns = type("A", (), {"merge": a + "," + b, "out_dir": d})()
            with self.assertRaises(ValueError):
                F.merge(ns)


class GetPkg(unittest.TestCase):
    def test_fetch_package_records_hashes(self):
        with tempfile.TemporaryDirectory() as d:
            seen = []

            def fake(url, **kw):
                seen.append(url)
                return ("#!/bin/sh\n" if url.endswith("build.sh") else "x\n").encode()
            m = G.fetch_package(d, getter=fake)
            self.assertEqual(sorted(m["files"]), sorted(G.PKG_FILES))
            self.assertTrue(all("/" + G.COMMIT + "/xltwpkg/" in u for u in seen))
            self.assertTrue(os.access(os.path.join(d, "build.sh"), os.X_OK) or os.name != "posix")
            with open(os.path.join(d, "pkg-manifest.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f)["commit"], G.COMMIT)

    def test_wait_prereg(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "prereg.md")
            with open(p, "wb") as f:
                f.write(b"line one\r\nline two\n")
            calls = []

            def fake(url, **kw):
                calls.append(url)
                return b"old" if len(calls) < 3 else b"line one\nline two\n"
            sha = G.wait_prereg(p, getter=fake, deadline=10 ** 12, sleep=lambda s: None)
            self.assertEqual(len(calls), 3)
            self.assertEqual(len(sha), 64)

    def test_wait_prereg_gives_up(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "prereg.md")
            with open(p, "wb") as f:
                f.write(b"x")
            with self.assertRaises(SystemExit):
                G.wait_prereg(p, getter=lambda url, **kw: b"y", deadline=0, sleep=lambda s: None)

    def test_prereg_present(self):
        # prereg.md in the job's folder; expectations.md in the repository
        self.assertTrue(any(os.path.exists(os.path.join(HERE, n)) for n in (G.PREREG_LOCAL, "expectations.md")))


if __name__ == "__main__":
    unittest.main()
