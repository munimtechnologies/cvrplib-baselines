"""Tests for det2run.py's scoring (no solver runs). Needs fullrun.py next to it (fetched by getdet2.py).

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import det2run as D  # noqa: E402


def rec(rid, limit, vehicles, sha="a" * 64, elapsed=None, clock=False, det=True, peak=0.3, fit=150.0, fs=1000.0,
        dit=60000, ds=250.0, mf=81.05, md=180.1):
    st = {"solver": "xltw-solver 0.2.0", "elapsed": elapsed if elapsed is not None else 0.6 * limit,
          "clock_stop": clock, "term_stop": False, "deterministic": det, "fleet_iterations": int(fit * fs),
          "fleet_seconds": fs, "distance_iterations": dit, "distance_seconds": ds, "model_fleet_rate": mf,
          "model_distance_rate": md}
    r = {"id": rid, "instance": "x", "limit": limit, "harness_frozen": False, "self_stopped": True, "exit": 0,
         "feasible": True, "cost_line_ok": True, "bad_line_count": 0, "numbering_errors": 0, "vehicles": vehicles,
         "peak_gb": peak, "watchdog": None, "solver_stats": st, "solution_sha256": sha}
    r["rates"] = D.rates(r)
    return r


BUILD = {"tag": "cp312", "pins_ok": True}


def good():
    return [rec("A-X1", 2219.4, 33), rec("A-X2", 2219.4, 33), rec("B-X1", 3648.6, 90, sha="b" * 64),
            rec("B-X2", 3648.6, 90, sha="b" * 64)]


class Score(unittest.TestCase):
    def test_limits(self):
        self.assertEqual(D.limit_for(1233), 2219.4)
        self.assertEqual(D.limit_for(2027), 3648.6)

    def test_all_hold(self):
        p = D.score(BUILD, False, good())
        self.assertEqual(set(p.values()), {"held"}, p)

    def test_gate(self):
        runs = good()
        runs[1]["self_stopped"] = False
        p = D.score(BUILD, False, runs)
        self.assertEqual(p["G0"], "did not hold")
        self.assertTrue(p["G1"].startswith("untestable"))
        self.assertEqual(D.score(BUILD, True, good())["G0"], "did not hold")       # network reachable
        self.assertEqual(D.score(BUILD, False, good()[:3])["G0"], "did not hold")  # a run missing
        runs = good()
        runs[0]["solver_stats"]["solver"] = "xltw-solver 0.1.0"
        self.assertEqual(D.score(BUILD, False, runs)["G0"], "did not hold")

    def test_each_prediction_can_fail(self):
        runs = good()
        runs[1]["solution_sha256"] = "c" * 64
        self.assertEqual(D.score(BUILD, False, runs)["G1"], "did not hold")
        runs = good()
        runs[2]["solver_stats"]["clock_stop"] = "distance"
        self.assertEqual(D.score(BUILD, False, runs)["G2"], "did not hold")
        runs = good()
        runs[3]["solver_stats"]["elapsed"] = 0.9 * 3648.6
        self.assertEqual(D.score(BUILD, False, runs)["G3"], "did not hold")
        runs = good()
        runs[0]["vehicles"] = 35
        self.assertEqual(D.score(BUILD, False, runs)["G4"], "did not hold")
        runs = good()
        runs[2]["vehicles"] = 103
        self.assertEqual(D.score(BUILD, False, runs)["G5"], "did not hold")
        runs = good()
        runs[0]["peak_gb"] = 0.7
        self.assertEqual(D.score(BUILD, False, runs)["G6"], "did not hold")
        runs = good()
        runs[0] = rec("A-X1", 2219.4, 33, fit=90.0)  # 90 / 81.05 = 1.11 < 1.2
        self.assertEqual(D.score(BUILD, False, runs)["G7"], "did not hold")

    def test_rates(self):
        r = rec("A-X1", 2219.4, 33)
        self.assertEqual(r["rates"]["fleet"], 150.0)
        self.assertEqual(r["rates"]["distance"], 240.0)
        self.assertAlmostEqual(r["rates"]["fleet_headroom"], round(150.0 / 81.05, 3))
        self.assertIsNone(D.rates({"solver_stats": None})["fleet"])


if __name__ == "__main__":
    unittest.main()
