"""Tests for xltwrm.py (no network). MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0."""
import math
import os
import tempfile
import unittest

import xltwbase as B
import xltwrm as R


def inst_of(rows, capacity, vehicles=None, name="T"):
    return {"name": name, "vehicles": vehicles, "capacity": capacity, "rows": rows,
            "raw": [tuple(str(v) for v in r) for r in rows]}


def star():
    # six customers around the depot, demand 1 each, capacity 3: at least 2 vehicles
    pts = [(10, 0), (0, 10), (-10, 0), (0, -10), (5, 5), (-5, -5)]
    return inst_of([(0, 0, 0, 0, 1000, 0)] + [(x, y, 1, 0, 1000, 1) for x, y in pts], 3, 6, "STAR")


def ring():
    # twelve customers on a ring, demand 1, capacity 4, wide windows: K = 3, header fleet 12
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
        r = R.run_one((vp, "double", arm, seconds, 1, k, R.base_prize(inst, "double")))
    return k, R.assess(r, inst)


class PrizeTest(unittest.TestCase):
    def test_base_prize(self):
        self.assertEqual(R.base_prize(star(), "double"), math.ceil(2 * math.hypot(20, 20) * 1000) + 1)
        self.assertEqual(R.base_prize(star(), "round"), math.ceil(2 * math.hypot(20, 20)) + 1)

    def test_optional_copy_keeps_fields(self):
        import pyvrp
        with tempfile.TemporaryDirectory() as d:
            vp = os.path.join(d, "S.vrp")
            with open(vp, "w", encoding="utf-8") as f:
                f.write(B.to_vrplib(star()))
            data = pyvrp.read(vp, round_func=B.rf_double)
        opt = R.optional_copy(data, [7, 8, 9, 10, 11, 12])
        self.assertEqual(opt.num_clients, data.num_clients)
        for a, b, p in zip(data.clients(), opt.clients(), [7, 8, 9, 10, 11, 12]):
            self.assertTrue(a.required)
            self.assertFalse(b.required)
            self.assertEqual(b.prize, p)
            self.assertEqual((a.location, list(a.delivery), a.service_duration, a.tw_early, a.tw_late),
                             (b.location, list(b.delivery), b.service_duration, b.tw_early, b.tw_late))


class ArmTest(unittest.TestCase):
    def test_every_arm_reaches_the_bound(self):
        for inst in (star(), ring()):
            for arm in R.ARMS:
                k, r = run(inst, arm)
                msg = "%s/%s" % (inst["name"], arm)
                self.assertTrue(r["exact_ok"], msg)
                self.assertFalse(r["below_bound"], msg)
                self.assertEqual(r["vehicles"], k, msg)
                self.assertTrue(r["trace"], msg)
                self.assertEqual(r["trace"][-1][1], k, msg)

    def test_already_at_bound(self):
        for arm in R.ARMS:
            k, r = run(tight(), arm, seconds=3)
            self.assertEqual(k, 4)
            self.assertTrue(r["exact_ok"], arm)
            self.assertEqual(r["vehicles"], 4, arm)

    def test_eject_counts_rounds(self):
        _, r = run(ring(), "eject")
        self.assertGreaterEqual(r["stats"]["levels"], 0)
        self.assertGreaterEqual(r["stats"]["rounds"], r["stats"]["levels"])


def recs_of(veh, err=None):
    out = []
    for name, (_, sintef, vrptwl) in R.MISSES.items():
        for arm in R.ARMS:
            v = veh(name, arm, sintef, vrptwl)
            rec = {"instance": name, "arm": arm, "bound": {"k": 90}}
            if err and (name, arm) == err:
                rec["error"] = "boom"
            else:
                rec["run"] = {"exact_ok": True, "vehicles": v, "below_bound": v < (90 if name.startswith(
                    ("C1", "RC1")) else 18)}
            out.append(rec)
    return out


class TallyTest(unittest.TestCase):
    def test_all_held(self):
        def veh(name, arm, sintef, vrptwl):
            return {"fleet": vrptwl, "warm": max(sintef, vrptwl - 1), "eject": sintef}[arm]
        t = R.tally(recs_of(veh))
        self.assertEqual(t["runs_expected"], 39)
        self.assertEqual(t["eject_saved_vehicles"], 21)
        self.assertEqual(t["eject_lt_warm"], 4)
        self.assertEqual(set(t["predictions"].values()), {"held"}, t["predictions"])

    def test_failures(self):
        def veh(name, arm, sintef, vrptwl):
            if name == "C1_10_2" and arm == "eject":
                return 89
            return vrptwl
        p = R.tally(recs_of(veh, err=("RC2_10_5", "warm")))["predictions"]
        self.assertEqual(p["M0"], "did not hold")
        self.assertEqual(p["M1"], "held")
        for k in ("M2", "M3", "M4", "M5", "M6", "M7"):
            self.assertEqual(p[k], "did not hold", k)

    def test_untestable_with_few_pairs(self):
        def veh(name, arm, sintef, vrptwl):
            return sintef
        recs = [r for r in recs_of(veh) if r["instance"] in ("C1_10_2", "C1_10_6", "C2_10_6")]
        p = R.tally(recs)["predictions"]
        self.assertEqual(p["M0"], "did not hold")
        for k in ("M1", "M2", "M3", "M4", "M6", "M7"):
            self.assertEqual(p[k], "untestable", k)
        self.assertEqual(p["M5"], "held")

    def test_table(self):
        self.assertEqual(len(R.MISSES), 13)
        self.assertEqual(sum(v - s for _, s, v in R.MISSES.values()), 21)


if __name__ == "__main__":
    unittest.main()
