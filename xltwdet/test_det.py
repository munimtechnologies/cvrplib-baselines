"""Tests for xltwdet (detsolver.py, detrun.py). Standard library only; needs the files getdet.py and fetch_helpers.py
fetch (solver.py, lock.py, fullrun.py, conformance.py, xltwbase.py, xltwlb.py) in this folder, and the build (lib/)
for the end-to-end test, which runs detsolver.py three times on one synthetic instance and seed (once with a CPU
hog) and requires the same final solution each time.

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

import detrun  # noqa: E402
import detsolver  # noqa: E402
import lock  # noqa: E402
import solver as S  # noqa: E402

PY = lock.build_python(HERE) or sys.executable
HAVE_BUILD = lock.build_python(HERE) is not None


class BudgetFormula(unittest.TestCase):
    def test_constants(self):
        self.assertEqual((detsolver.RATE0, detsolver.RATE_EXP, detsolver.SAFETY), (300.0, 0.5, 0.6))
        self.assertEqual(detsolver.VERSION, "0.1.0-det1")

    def test_value(self):
        # n = 1,047, T = 120 s: 0.6 x 300 / sqrt(1.047) x (120 - 1.74) = about 20,803
        self.assertTrue(20700 <= detsolver.iteration_budget(1047, 120.0) <= 20900)

    def test_depends_on_n_and_limit_only(self):
        self.assertEqual(detsolver.iteration_budget(1233, 2219.4), detsolver.iteration_budget(1233, 2219.4))
        self.assertLess(detsolver.iteration_budget(4000, 120.0), detsolver.iteration_budget(1000, 120.0))
        self.assertLess(detsolver.iteration_budget(1000, 60.0), detsolver.iteration_budget(1000, 120.0))
        self.assertGreater(detsolver.iteration_budget(8574, 1.8 * 8574), 0)
        self.assertEqual(detsolver.iteration_budget(1000, 0.5), 0)


class BudgetCriterion(unittest.TestCase):
    def test_counts_down(self):
        b = detsolver.Budget(3, deadline=1e18)
        self.assertEqual([b(0.0) for _ in range(5)], [False, False, False, True, True])
        self.assertEqual((b.used, b.left, b.clock_stop, b.exhausted()), (3, 0, False, True))

    def test_clock_safety_net(self):
        t = [0.0]
        b = detsolver.Budget(100, deadline=10.0, clock=lambda: t[0])
        self.assertFalse(b(0.0))
        t[0] = 10.0
        self.assertTrue(b(0.0))
        self.assertTrue(b.clock_stop)
        self.assertEqual(b.used, 1)

    def test_sigterm(self):
        b = detsolver.Budget(100, deadline=1e18)
        S.TERM["flag"] = True
        try:
            self.assertTrue(b(0.0))
            self.assertTrue(b.term_stop)
        finally:
            S.TERM["flag"] = False


def rec(rid, vehicles=10, sha="x", elapsed=60.0, clock=False, peak=0.2, **kw):
    r = {"id": rid, "instance": "I", "limit": 120.0, "vehicles": vehicles, "distance": 1000, "solution_sha256": sha,
         "harness_frozen": False, "self_stopped": True, "exit": 0, "feasible": True, "cost_line_ok": True,
         "bad_line_count": 0, "numbering_errors": 0, "peak_gb": peak, "watchdog": None,
         "solver_stats": {"elapsed": elapsed, "clock_stop": clock, "term_stop": False}}
    r.update(kw)
    return r


BUILD = {"tag": "cp312", "pins_ok": True}


def all_recs(t2_same=False):
    out = []
    for k, _ in detrun.INSTANCES:
        out += [rec(k + "-W1", sha="w" + k), rec(k + "-T1", sha="t" + k), rec(k + "-W2", sha="w" + k),
                rec(k + "-W3", sha="w" + k, elapsed=80.0), rec(k + "-T2", sha=("t" if t2_same else "u") + k)]
    return out


class Score(unittest.TestCase):
    def by(self, recs):
        return {r["id"]: r for r in recs}

    def test_all_held(self):
        self.assertEqual(set(detrun.score(BUILD, False, all_recs()).values()), {"held"})

    def test_d1_and_d2(self):
        recs = all_recs()
        self.by(recs)["B-W3"]["solution_sha256"] = "other"
        self.by(recs)["C-W3"]["solver_stats"]["clock_stop"] = "distance"
        p = detrun.score(BUILD, False, recs)
        self.assertEqual((p["D1"], p["D2"]), ("did not hold", "did not hold"))

    def test_d3_range(self):
        recs = all_recs()
        self.by(recs)["A-W2"]["solver_stats"]["elapsed"] = 30.0  # below 0.30 x 120 = 36
        self.assertEqual(detrun.score(BUILD, False, recs)["D3"], "did not hold")
        recs = all_recs()
        self.by(recs)["A-W3"]["solver_stats"]["elapsed"] = 110.0  # W3 (hog) is not in D3
        self.assertEqual(detrun.score(BUILD, False, recs)["D3"], "held")

    def test_d4_d5_d6(self):
        recs = all_recs(t2_same=True)
        self.by(recs)["A-W1"]["vehicles"] = 12  # 32 against 30 + 1
        self.by(recs)["B-T2"]["peak_gb"] = 0.7
        p = detrun.score(BUILD, False, recs)
        self.assertEqual((p["D4"], p["D5"], p["D6"]), ("did not hold", "did not hold", "did not hold"))

    def test_gate(self):
        recs = all_recs()
        self.by(recs)["C-T2"]["harness_frozen"] = True
        p = detrun.score(BUILD, False, recs)
        self.assertEqual(p["D0"], "did not hold")
        self.assertTrue(p["D1"].startswith("untestable"))
        self.assertEqual(detrun.score(BUILD, True, all_recs())["D0"], "did not hold")
        self.assertEqual(detrun.score(BUILD, False, all_recs()[:-1])["D0"], "did not hold")


class RunUntil(unittest.TestCase):
    def test_at_most_three(self):
        calls = []

        def run():
            calls.append(1)
            return {"harness_frozen": True}
        rec_ = detrun.run_until_unfrozen(run)
        self.assertEqual((len(calls), rec_["attempts"]), (3, 3))

    def test_second_try(self):
        seq = iter([{"harness_frozen": True}, {"harness_frozen": False, "n": 2}])
        rec_ = detrun.run_until_unfrozen(lambda: dict(next(seq)))
        self.assertEqual((rec_["n"], rec_["attempts"]), (2, 2))


class Launcher(unittest.TestCase):
    @unittest.skipIf(os.name != "posix", "the launcher is a bash script")
    def test_launcher(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(detrun.make_launcher("/usr/bin/python-x", here=d), "solver")
            self.assertTrue(os.access(path, os.X_OK))
            with open(path, encoding="utf-8") as f:
                body = f.read()
            self.assertIn('exec "/usr/bin/python-x" -s -P "%s"' % os.path.join(d, "detsolver.py"), body)

    def test_usage(self):
        p = subprocess.run([PY, "-s", os.path.join(HERE, "detsolver.py")], capture_output=True, text=True,
                           timeout=120)
        self.assertEqual((p.returncode, p.stdout), (2, ""))


def last_solution(stdout):
    lines = [x for x in stdout.splitlines() if x.strip()]
    ends = [i for i, x in enumerate(lines) if x.startswith("Cost: ")]
    if not ends:
        return None
    start = ends[-2] + 1 if len(ends) > 1 else 0
    return "\n".join(lines[start:ends[-1] + 1])


@unittest.skipUnless(HAVE_BUILD, "needs the offline build (lib/) for PyVRP")
class EndToEnd(unittest.TestCase):
    def test_same_seed_same_solution(self):
        with tempfile.TemporaryDirectory() as d:
            inst = os.path.join(d, "SYN80.vrp")
            code = ("import sys; sys.path[:0] = [%r, %r]; import xltwlb as X; "
                    "open(%r, 'w').write(X.write_vrplib(X.synthetic(80)))" % (HERE, os.path.join(HERE, "lib"), inst))
            subprocess.run([PY, "-s", "-c", code], check=True, timeout=120)
            sols, stats = [], []
            for with_hog in (False, False, True):
                with detrun.hog(with_hog):
                    p = subprocess.run([PY, "-s", os.path.join(HERE, "detsolver.py"), inst, "10", "3"],
                                       capture_output=True, text=True, timeout=120)
                self.assertEqual(p.returncode, 0, p.stderr[-2000:])
                sols.append(last_solution(p.stdout))
                line = [x for x in p.stderr.splitlines() if x.startswith("XLTW_SOLVER_STATS ")]
                self.assertEqual(len(line), 1, p.stderr[-2000:])
                stats.append(json.loads(line[0][len("XLTW_SOLVER_STATS "):]))
            self.assertIsNotNone(sols[0])
            self.assertEqual(sols[0], sols[1])
            self.assertEqual(sols[0], sols[2])
            for st in stats:
                self.assertFalse(st["clock_stop"], st)
                self.assertGreater(st["fleet_iterations"] + st["iterations"], 0)
                self.assertLessEqual(st["fleet_iterations"], st["fleet_budget"])


if __name__ == "__main__":
    unittest.main()
