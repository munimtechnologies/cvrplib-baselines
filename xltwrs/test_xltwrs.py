"""Tests for xltwrs.py (no network). MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0."""
import math
import os
import tempfile
import unittest

import xltwbase as B
import xltwrs as S


def inst_of(rows, capacity, vehicles=None, name="T"):
    return {"name": name, "vehicles": vehicles, "capacity": capacity, "rows": rows,
            "raw": [tuple(str(v) for v in r) for r in rows]}


def star():
    pts = [(10, 0), (0, 10), (-10, 0), (0, -10), (5, 5), (-5, -5)]
    return inst_of([(0, 0, 0, 0, 1000, 0)] + [(x, y, 1, 0, 1000, 1) for x, y in pts], 3, 6, "STAR")


def ring():
    pts = [(round(30 * math.cos(2 * math.pi * k / 12), 3), round(30 * math.sin(2 * math.pi * k / 12), 3))
           for k in range(12)]
    return inst_of([(0, 0, 0, 0, 5000, 0)] + [(x, y, 1, 0, 5000, 2) for x, y in pts], 4, 12, "RING")


def tight():
    rows = [(0, 0, 0, 0, 1000, 0)] + [(x, y, 1, 100, 101, 10) for x, y in [(50, 0), (0, 50), (-50, 0), (0, -50)]]
    return inst_of(rows, 100, 4, "TIGHT")


def run(inst, arm, seconds=6):
    k = B.lower_bound(inst, "double")["k"]
    with tempfile.TemporaryDirectory() as d:
        vp = os.path.join(d, "%s.vrp" % inst["name"])
        with open(vp, "w", encoding="utf-8") as f:
            f.write(B.to_vrplib(inst))
        r = S.run_one((vp, "double", arm, seconds, 1, k))
    return k, S.R.assess(r, inst)


class HelperTest(unittest.TestCase):
    def test_at(self):
        tr = [(0.5, 50), (10.0, 40), (299.9, 31), (300.0, 30), (650.0, 29)]
        self.assertIsNone(S.at(tr, 0.4))
        self.assertEqual(S.at(tr, 0.5), 50)
        self.assertEqual(S.at(tr, 299.95), 31)
        self.assertEqual(S.at(tr, 300), 30)
        self.assertEqual(S.at(tr, 600), 30)
        self.assertEqual(S.at(tr, 900), 29)
        self.assertIsNone(S.at([], 900))

    def test_cap(self):
        self.assertEqual(S.attempt_cap(None), 30.0)
        self.assertEqual(S.attempt_cap(5.0), 30.0)
        self.assertEqual(S.attempt_cap(40.0), 80.0)


class ArmTest(unittest.TestCase):
    def test_both_arms_reach_the_bound(self):
        for inst in (star(), ring()):
            for arm in S.ARMS:
                k, r = run(inst, arm)
                msg = "%s/%s" % (inst["name"], arm)
                self.assertTrue(r["exact_ok"], msg)
                self.assertFalse(r["below_bound"], msg)
                self.assertEqual(r["vehicles"], k, msg)
                self.assertEqual(r["trace"][-1][1], k, msg)

    def test_already_at_bound(self):
        for arm in S.ARMS:
            k, r = run(tight(), arm, seconds=3)
            self.assertEqual(k, 4)
            self.assertTrue(r["exact_ok"], arm)
            self.assertEqual(r["vehicles"], 4, arm)

    def test_restart_counts(self):
        _, r = run(ring(), "restart")
        self.assertGreaterEqual(r["stats"]["solves"], 1)
        self.assertGreaterEqual(r["stats"]["solves"], r["stats"]["fails"])


def recs_of(final, at300=None, err=None):
    """final(name, arm, sintef, vrptwl) -> vehicles at the end; at300 likewise for the trace point at 300 s."""
    out = []
    for name, (_, sintef, vrptwl) in S.MISSES.items():
        for arm in S.ARMS:
            v = final(name, arm, sintef, vrptwl)
            v300 = at300(name, arm, sintef, vrptwl) if at300 else v
            rec = {"instance": name, "arm": arm, "bound": {"k": 18}}
            if err and (name, arm) == err:
                rec["error"] = "boom"
            else:
                rec["run"] = {"exact_ok": True, "vehicles": v, "below_bound": False,
                              "trace": [(1.0, v + 5), (299.0, v300), (850.0, v)]}
            out.append(rec)
    return out


class TallyTest(unittest.TestCase):
    def test_all_held(self):
        names = list(S.MISSES)
        better = set(names[:4])  # restart one fewer on 4 instances, never more

        def final(name, arm, sintef, vrptwl):
            if arm == "fleet":
                return sintef + (1 if name in names[:8] else 0)  # 8 over SINTEF in total
            return sintef + (1 if name in names[:8] else 0) - (1 if name in better else 0)

        def at300(name, arm, sintef, vrptwl):
            return final(name, arm, sintef, vrptwl) + (1 if name in names[:5] else 0)

        t = S.tally(recs_of(final, at300))
        self.assertEqual(t["runs_expected"], 26)
        self.assertEqual(t["fleet_gained_after_300"], 5)
        self.assertEqual(t["fleet_over_sintef"], 8)
        self.assertEqual(t["restart_lt_fleet"], 4)
        self.assertEqual(t["restart_le_fleet"], 13)
        self.assertEqual(t["pairs"][names[0]]["fleet_300"], t["pairs"][names[0]]["fleet"] + 1)
        self.assertEqual(set(t["predictions"].values()), {"held"}, t["predictions"])

    def test_failures(self):
        def final(name, arm, sintef, vrptwl):
            if arm == "restart":
                return vrptwl + 1 if name != "C1_10_2" else sintef - 1
            return vrptwl

        p = S.tally(recs_of(final, err=("RC2_10_5", "fleet")))["predictions"]
        self.assertEqual(p["R0"], "did not hold")
        self.assertEqual(p["R1"], "did not hold")   # no gain after 300 s
        self.assertEqual(p["R2"], "untestable")     # one fleet run missing
        self.assertEqual(p["R3"], "did not hold")
        self.assertEqual(p["R4"], "did not hold")
        self.assertEqual(p["R5"], "did not hold")   # C1_10_2 below SINTEF

    def test_untestable_with_few_pairs(self):
        recs = [r for r in recs_of(lambda n, a, s, v: s) if r["instance"] in ("C1_10_2", "C2_10_6")]
        p = S.tally(recs)["predictions"]
        self.assertEqual(p["R0"], "did not hold")
        for k in ("R1", "R2", "R3", "R4"):
            self.assertEqual(p[k], "untestable", k)
        self.assertEqual(p["R5"], "held")


if __name__ == "__main__":
    unittest.main()
