"""Tests for xltwfc (fcsolver.py, fcrun.py). Standard library only; needs the files getfc.py and fetch_helpers.py
fetch (solver.py, lock.py, fullrun.py, conformance.py, xltwbase.py, xltwlb.py) in this folder, and the build (lib/)
for the end-to-end test, which runs fcsolver.py under the package's interpreter on a small synthetic instance.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fcrun  # noqa: E402
import fcsolver  # noqa: E402
import lock  # noqa: E402

PY = lock.build_python(HERE) or sys.executable
HAVE_BUILD = lock.build_python(HERE) is not None


class FakeSol:
    def __init__(self, routes, dist, feasible=True):
        self.r, self.d, self.f = routes, dist, feasible

    def is_feasible(self):
        return self.f

    def num_routes(self):
        return self.r

    def distance(self):
        return self.d


class FixedCost(unittest.TestCase):
    def test_ten_mean_route_lengths(self):
        self.assertEqual(fcsolver.fixed_cost_for(100000, 64), 10 * 1563)
        self.assertEqual(fcsolver.fixed_cost_for(640, 64), 100)
        self.assertEqual(fcsolver.fixed_cost_for(0, 3), 1)
        self.assertEqual(fcsolver.fixed_cost_for(10, 3, factor=2), 8)

    def test_routes_must_be_positive(self):
        with self.assertRaises(ValueError):
            fcsolver.fixed_cost_for(10, 0)

    def test_version(self):
        self.assertEqual(fcsolver.VERSION, "0.1.0-fc2")


class HolderTests(unittest.TestCase):
    def test_fewer_routes_first_then_distance(self):
        h = fcsolver.Holder()
        self.assertFalse(h.offer(FakeSol(3, 50, feasible=False)))
        self.assertTrue(h.offer(FakeSol(5, 100)))
        self.assertFalse(h.offer(FakeSol(5, 100)))
        self.assertTrue(h.offer(FakeSol(5, 90.4)))
        self.assertEqual(h.key, (5, 90))
        self.assertTrue(h.offer(FakeSol(4, 500)))
        self.assertFalse(h.offer(FakeSol(5, 1)))
        self.assertEqual(h.key, (4, 500))


class Visits(unittest.TestCase):
    """fc1 called Route.visits(), which PyVRP 0.14 does not have. fc2 uses the package's own conversion."""

    def test_uses_package_conversion(self):
        class Act:
            def __init__(self, idx, client):
                self.idx, self.is_client = idx, client

        class R:
            def __init__(self, idxs):
                self.idxs = idxs

            def schedule(self):
                return [Act(0, False)] + [Act(i, True) for i in self.idxs] + [Act(0, False)]

        class Sol:
            def routes(self):
                return [R([3, 1]), R([2])]

        import solver as S
        S.load_helpers()
        self.assertEqual(fcsolver.visits(Sol()), [[3, 1], [2]])


class RunUntil(unittest.TestCase):
    def test_stops_at_first_unfrozen(self):
        seq = iter([{"harness_frozen": True, "n": 1}, {"harness_frozen": False, "n": 2},
                    {"harness_frozen": False, "n": 3}])
        rec = fcrun.run_until_unfrozen(lambda: dict(next(seq)))
        self.assertEqual((rec["n"], rec["attempts"], len(rec["frozen_tries"])), (2, 2, 1))

    def test_at_most_three(self):
        calls = []

        def run():
            calls.append(1)
            return {"harness_frozen": True}
        rec = fcrun.run_until_unfrozen(run)
        self.assertEqual((len(calls), rec["attempts"], rec["harness_frozen"]), (3, 3, True))

    def test_clean_first_try(self):
        rec = fcrun.run_until_unfrozen(lambda: {"harness_frozen": False})
        self.assertEqual(rec["attempts"], 1)
        self.assertNotIn("frozen_tries", rec)


def rec(rid, vehicles, k_star, peak=0.3, fc=True, **kw):
    r = {"id": rid, "vehicles": vehicles, "k_star": k_star, "harness_frozen": False, "self_stopped": True, "exit": 0,
         "feasible": True, "cost_line_ok": True, "bad_line_count": 0, "numbering_errors": 0, "peak_gb": peak,
         "watchdog": None, "solver_stats": {"fixed_cost": 1000 if fc else None, "fc_iterations": 5 if fc else 0}}
    r.update(kw)
    return r


BUILD = {"tag": "cp312", "pins_ok": True}
KS = {"F1": 27, "F2": 47, "F3": 81, "F4": 18}


class Score(unittest.TestCase):
    def full(self, v):
        return [rec(i, v[i], KS[i]) for i in fcrun.IDS]

    def test_constants(self):
        self.assertEqual(fcrun.IDS, ["F1", "F2", "F3", "F4"])
        self.assertEqual(fcrun.KSTAR_TOTAL, 173)
        self.assertEqual(fcrun.S3_FLOOR, 199)
        self.assertEqual(fcrun.SEED, 20261104)
        self.assertEqual(fcrun.MAX_ATTEMPTS, 3)

    def test_all_held(self):
        fc = [rec("F1", 33, 27), rec("F2", 60, 47), rec("F3", 100, 81), rec("F4", 25, 18)]
        p = fcrun.score(BUILD, False, fc, self.full({"F1": 34, "F2": 66, "F3": 108, "F4": 27}))
        self.assertEqual(set(p.values()), {"held"})

    def test_worse_total(self):
        fc = [rec("F1", 36, 27), rec("F2", 70, 47), rec("F3", 110, 81), rec("F4", 26, 18)]
        p = fcrun.score(BUILD, False, fc, self.full({"F1": 34, "F2": 66, "F3": 108, "F4": 27}))
        self.assertEqual(p["S1"], "did not hold")
        self.assertEqual(p["S2"], "did not hold")   # fewer on one only (F4)

    def test_gate(self):
        fc = [rec("F1", 33, 27), rec("F2", 60, 47), rec("F3", 100, 81), rec("F4", 25, 18, fc=False)]
        p = fcrun.score(BUILD, False, fc, self.full({"F1": 34, "F2": 66, "F3": 108, "F4": 27}))
        self.assertEqual(p["S0"], "did not hold")
        self.assertTrue(p["S5"].startswith("untestable"))
        fc[3] = rec("F4", 25, 18, harness_frozen=True)
        self.assertEqual(fcrun.score(BUILD, False, fc, [])["S0"], "did not hold")
        fc[3] = rec("F4", 25, 18)
        self.assertEqual(fcrun.score(BUILD, True, fc, [])["S0"], "did not hold")   # network reachable

    def test_too_few_baseline_runs(self):
        fc = [rec("F1", 33, 27), rec("F2", 60, 47), rec("F3", 100, 81), rec("F4", 25, 18)]
        full = self.full({"F1": 34, "F2": 66, "F3": 108, "F4": 27})
        full[1]["harness_frozen"] = True
        full[3]["self_stopped"] = False
        p = fcrun.score(BUILD, False, fc, full)
        self.assertTrue(p["S1"].startswith("untestable"))
        self.assertEqual(p["S3"], "held")           # 33 + 60 + 100 + 25 = 218 >= 199

    def test_s3_s4_s5(self):
        fc = [rec("F1", 27, 27), rec("F2", 50, 47), rec("F3", 100, 81), rec("F4", 20, 18, peak=0.7)]
        p = fcrun.score(BUILD, False, fc, self.full({"F1": 34, "F2": 66, "F3": 108, "F4": 27}))
        self.assertEqual(p["S3"], "did not hold")   # 197 < 199
        self.assertEqual(p["S4"], "did not hold")   # F1 at K*
        self.assertEqual(p["S5"], "did not hold")   # peak 0.7


class Launcher(unittest.TestCase):
    @unittest.skipIf(os.name != "posix", "the launcher is a bash script")
    def test_launcher(self):
        with tempfile.TemporaryDirectory() as d:
            bindir = fcrun.make_launcher("/usr/bin/python-x", here=d)
            path = os.path.join(bindir, "solver")
            self.assertTrue(os.access(path, os.X_OK))
            with open(path, encoding="utf-8") as f:
                body = f.read()
            self.assertIn('exec "/usr/bin/python-x" -s -P "%s"' % os.path.join(d, "fcsolver.py"), body)
            self.assertNotIn("\r", body)

    def test_usage(self):
        p = subprocess.run([PY, "-s", os.path.join(HERE, "fcsolver.py")], capture_output=True, text=True, timeout=120)
        self.assertEqual((p.returncode, p.stdout), (2, ""))
        self.assertIn("usage", p.stderr)
        p = subprocess.run([PY, "-s", os.path.join(HERE, "fcsolver.py"), "x.vrp", "0", "1"], capture_output=True,
                           text=True, timeout=120)
        self.assertEqual((p.returncode, p.stdout), (2, ""))


@unittest.skipUnless(HAVE_BUILD, "needs the offline build (lib/) for PyVRP")
class EndToEnd(unittest.TestCase):
    """The whole fcsolver run (both fleet steps and the distance phase) on a synthetic 80-customer instance."""

    def test_small_instance(self):
        with tempfile.TemporaryDirectory() as d:
            inst = os.path.join(d, "SYN80.vrp")
            code = ("import sys; sys.path[:0] = [%r, %r]; import xltwlb as X; "
                    "open(%r, 'w').write(X.write_vrplib(X.synthetic(80)))" % (HERE, os.path.join(HERE, "lib"), inst))
            subprocess.run([PY, "-s", "-c", code], check=True, timeout=120)
            p = subprocess.run([PY, "-s", os.path.join(HERE, "fcsolver.py"), inst, "12", "1"], capture_output=True,
                               text=True, timeout=120)
            self.assertEqual(p.returncode, 0, p.stderr[-2000:])
            lines = [x for x in p.stdout.splitlines() if x.strip()]
            self.assertTrue(lines and lines[-1].startswith("Cost: "), p.stdout[-500:])
            self.assertTrue(all(x.startswith("Route #") or x.startswith("Cost: ") for x in lines))
            stats = [x for x in p.stderr.splitlines() if x.startswith("XLTW_SOLVER_STATS ")]
            self.assertEqual(len(stats), 1, p.stderr[-2000:])
            st = json.loads(stats[0][len("XLTW_SOLVER_STATS "):])
            self.assertEqual(st["solver"], "xltw-solver-fc 0.1.0-fc2")
            self.assertIsNotNone(st["first_vehicles"])
            if st["first_vehicles"] > st["bound"]["k"]:
                self.assertIsNotNone(st["fixed_cost"])
                self.assertGreater(st["fc_iterations"], 0)
            self.assertGreater(st["iterations"], 0)


if __name__ == "__main__":
    unittest.main()
