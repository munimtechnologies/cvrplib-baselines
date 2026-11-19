"""Tests for ngfleet.py. Need cgfleet.py, test_cgfleet.py, tmatch.py and xltwlb.py next to this file (fetch.py gets
them from cvrplib-baselines). MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0."""
import os
import random
import sys
import time
import unittest
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

import cgfleet as G  # noqa: E402
import ngfleet as N  # noqa: E402
import test_cgfleet as TC  # noqa: E402  (brute-force helpers only)
import tmatch as TM  # noqa: E402

JITS = [False, True] if N.HAVE_NUMBA else [False]


def rand_pi(n, seed, choices=(0, 1, 1, 2, 3, 5)):
    rng = random.Random(seed)
    return [rng.choice(choices) for _ in range(n)]


class TestPricing(unittest.TestCase):
    def test_full_neighbourhood_is_exactly_elementary(self):
        """g = m - 1 and a front large enough that nothing is merged: the DP is the exact elementary optimum."""
        for jit in JITS:
            for seed in range(1, 21):
                inst = TC.random_instance(6, seed, width=(20, 70))
                I = TM.Inst(inst)
                pi = rand_pi(I.n, 500 + seed)
                r = N.price_ng(I.C, I.e, I.l, np.array(pi), L_max=500, ng=5, B=64, use_jit=jit)
                self.assertFalse(r["capped"])
                self.assertEqual(r["pstar"], TC.elementary_best(inst, pi), (jit, seed))
                for w in r["walks"]:
                    self.assertTrue(N.walk_time_ok(I.C, I.e, I.l, w), (seed, w))
                    self.assertEqual(len(set(w)), len(w), (seed, w))
                if r["walks"]:
                    self.assertGreaterEqual(int(np.array(pi)[r["walks"][0]].sum()), r["pstar"])

    def test_merging_never_cuts_a_real_route(self):
        """Validity with heavy merging (front of 1 or 2 labels, small neighbourhoods)."""
        for jit in JITS:
            for seed in range(30, 50):
                inst = TC.random_instance(6, seed, width=(20, 80))
                I = TM.Inst(inst)
                pi = rand_pi(I.n, seed)
                best = TC.elementary_best(inst, pi)
                for g in (1, 2, 3):
                    for B in (1, 2):
                        r = N.price_ng(I.C, I.e, I.l, np.array(pi), L_max=500, ng=g, B=B, use_jit=jit)
                        self.assertGreaterEqual(r["pstar"], best, (jit, seed, g, B))
                        for w in r["walks"]:
                            self.assertTrue(N.walk_time_ok(I.C, I.e, I.l, w), (seed, g, B, w))

    def test_between_elementary_and_r2_without_merging(self):
        """ng-routes with the 2-cycle rule are a subset of R2 walks and a superset of elementary routes."""
        for jit in JITS:
            for seed in range(60, 80):
                inst = TC.random_instance(7, seed, width=(30, 100), horizon=200)
                I = TM.Inst(inst)
                pi = rand_pi(I.n, seed, choices=(1, 1, 2, 3))
                r2 = G.price(I.C, I.e, I.l, np.array(pi), L_max=2000)
                rn = N.price_ng(I.C, I.e, I.l, np.array(pi), L_max=2000, ng=2, B=64, use_jit=jit)
                self.assertLessEqual(rn["pstar"], r2["pstar"], (jit, seed))
                self.assertGreaterEqual(rn["pstar"], TC.elementary_best(inst, pi), (jit, seed))

    def test_cluster_cycling_is_cut(self):
        """Three close customers with whole-day windows: R2 walks circle round them, ng-routes cannot."""
        inst = TC.make([(0, 0, 0, 0, 1000, 0), (10, 0, 0, 0, 900, 1), (11, 0, 0, 0, 900, 1), (10, 1, 0, 0, 900, 1)])
        I = TM.Inst(inst)
        pi = np.array([1, 1, 1])
        r2 = G.price(I.C, I.e, I.l, pi, L_max=1000)
        self.assertGreater(r2["pstar"], 3)
        for jit in JITS:
            rn = N.price_ng(I.C, I.e, I.l, pi, L_max=1000, ng=2, B=4, use_jit=jit)
            self.assertEqual(rn["pstar"], 3, jit)

    def test_jit_matches_python(self):
        if not N.HAVE_NUMBA:
            self.skipTest("numba not installed")
        for seed in range(90, 110):
            inst = TC.random_instance(8, seed, width=(20, 90), horizon=220)
            I = TM.Inst(inst)
            pi = rand_pi(I.n, seed)
            a = N.price_ng(I.C, I.e, I.l, np.array(pi), L_max=800, ng=3, B=2, use_jit=False)
            b = N.price_ng(I.C, I.e, I.l, np.array(pi), L_max=800, ng=3, B=2, use_jit=True)
            self.assertEqual(a["pstar"], b["pstar"], seed)
            self.assertEqual(a["walks"], b["walks"], seed)

    def test_cap_growth_and_empty(self):
        inst = TC.random_instance(6, 3, width=(30, 90))
        I = TM.Inst(inst)
        for jit in JITS:
            r = N.price_ng(I.C, I.e, I.l, np.full(I.n, 50), L_max=10, use_jit=jit)
            self.assertIsNone(r["pstar"])
            self.assertTrue(r["capped"])
            r0 = N.price_ng(I.C, I.e, I.l, np.zeros(I.n, dtype=np.int64), L_max=10, use_jit=jit)
            self.assertEqual(r0["pstar"], 0)
            # level storage grows in chunks: a tiny chunk must give the same answer
            pi = np.array(rand_pi(I.n, 7, choices=(3, 5, 8)))
            a = N.price_ng(I.C, I.e, I.l, pi, L_max=3000, chunk=2, use_jit=jit)
            b = N.price_ng(I.C, I.e, I.l, pi, L_max=3000, chunk=4096, use_jit=jit)
            self.assertEqual(a["pstar"], b["pstar"])
            self.assertEqual(a["walks"], b["walks"])

    def test_deadline(self):
        inst = TC.random_instance(6, 4, width=(30, 90))
        I = TM.Inst(inst)
        ticks = iter(range(10 ** 6))
        r = N.price_ng(I.C, I.e, I.l, np.full(I.n, 40), L_max=10 ** 5, deadline=5, clock=lambda: next(ticks),
                       use_jit=False)
        self.assertTrue(r["timeout"])
        self.assertIsNone(r["pstar"])

    def test_neighbourhoods(self):
        C = np.array([[0, 1, 9, 5], [1, 0, 2, 9], [9, 2, 0, 3], [5, 9, 3, 0]], dtype=np.float64)
        NB, posin = N.neighbourhoods(C, 2)
        self.assertEqual(NB.shape, (4, 2))
        for j in range(4):
            self.assertNotIn(j, NB[j].tolist())
            for q, u in enumerate(NB[j].tolist()):
                self.assertEqual(posin[j, u], q)
            self.assertEqual(posin[j, j], -1)
        self.assertEqual(NB[0].tolist(), [1, 3])
        NB0, posin0 = N.neighbourhoods(C, 0)
        self.assertEqual(NB0.shape, (4, 0))

    def test_elementary_and_walk_check(self):
        self.assertEqual(N.elementary([3, 1, 3, 2, 1]), [3, 1, 2])
        C = np.array([[0, 5], [5, 0]], dtype=np.float64)
        self.assertTrue(N.walk_time_ok(C, [0, 0], [10, 10], [0, 1]))
        self.assertFalse(N.walk_time_ok(C, [0, 0], [10, 4], [0, 1]))
        self.assertFalse(N.walk_time_ok(C, [0, 0], [10, 10], [0, 0]))


class TestBound(unittest.TestCase):
    def test_never_above_the_true_minimum_and_certificates_recheck(self):
        for seed in range(120, 130):
            inst = TC.random_instance(6, seed, width=(15, 60))
            I = TM.Inst(inst)
            now = time.monotonic()
            res = N.cg_two_phase(I.C, I.e, I.l, I.n, now + 8, now + 20, now + 30, q_price=60, q_final=200,
                                 say=lambda m: None)
            opt = TC.brute_min_fleet(inst)
            self.assertGreaterEqual(res["lb_int"], 1)
            self.assertLessEqual(res["lb_int"], opt, seed)
            self.assertEqual(res["lb"], max(res["lb_r2"], res["lb_ng"]))
            for ph in ("r2", "ng"):
                c = res["cert"][ph]
                if c is None:
                    continue
                self.assertTrue(N.recheck(I.C, I.e, I.l, c), (seed, ph))
                self.assertEqual(Fraction(c["sum"], c["pstar"]), res["lb_" + ph])
                ok = N.route_profit_ok(c, [[i] for i in range(I.n)])
                self.assertTrue(ok["ok"])
            self.assertIsNotNone(res["cert"]["ng"], seed)

    def test_incompatible_customers(self):
        inst = TC.make([(50, 50, 0, 0, 1000, 0), (0, 50, 0, 100, 105, 5), (100, 50, 0, 100, 105, 5),
                        (50, 0, 0, 100, 105, 5)])
        I = TM.Inst(inst)
        now = time.monotonic()
        res = N.cg_two_phase(I.C, I.e, I.l, I.n, now + 5, now + 15, now + 25, q_price=60, q_final=200,
                             say=lambda m: None)
        self.assertEqual(res["lb_int"], 3)

    def test_ub_stops_early(self):
        inst = TC.random_instance(6, 5, width=(10, 30))
        I = TM.Inst(inst)
        now = time.monotonic()
        res = N.cg_two_phase(I.C, I.e, I.l, I.n, now + 8, now + 20, now + 30, ub=1, q_price=60, q_final=200,
                             say=lambda m: None)
        self.assertIn("proved", res["stop"].values())

    def test_route_profit_check(self):
        c = {"pi_int": [1, 2, 3], "pstar": 4}
        self.assertTrue(N.route_profit_ok(c, [[0, 2], [1]])["ok"])
        self.assertFalse(N.route_profit_ok(c, [[1, 2]])["ok"])
        self.assertIsNone(N.route_profit_ok(None, [[0]]))


class TestProbe(unittest.TestCase):
    def test_run_all_end_to_end(self):
        import json
        import shutil
        import tempfile
        import xtwfleet as XW
        import xtwprobe as P
        inst = TC.random_instance(14, 11, width=(20, 60), horizon=300)
        rows = inst["rows"]
        text = ["NAME : XTW-n15", "TYPE : VRPTW", "DIMENSION : %d" % len(rows), "EDGE_WEIGHT_TYPE : EUC_2D",
                "CAPACITY : %d" % inst["capacity"], "NODE_COORD_SECTION"]
        text += ["%d %d %d" % (i + 1, r[0], r[1]) for i, r in enumerate(rows)]
        text += ["DEMAND_SECTION"] + ["%d %d" % (i + 1, r[2]) for i, r in enumerate(rows)]
        text += ["TIME_WINDOW_SECTION"] + ["%d %d %d" % (i + 1, r[3], r[4]) for i, r in enumerate(rows)]
        text += ["SERVICE_TIME_SECTION"] + ["%d %d" % (i + 1, r[5]) for i, r in enumerate(rows)]
        text += ["DEPOT_SECTION", "1", "-1", "EOF"]
        d = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(d, "inst"))
            os.makedirs(os.path.join(d, "bks"))
            with open(os.path.join(d, "inst", "XTW-n15.vrp"), "w") as f:
                f.write("\n".join(text) + "\n")
            routes = [[c] for c in range(1, 15)]
            chk = XW.check_sol(XW_parse(text), routes)
            self.assertTrue(chk["ok"], chk)
            with open(os.path.join(d, "bks", "XTW-n15.sol"), "w") as f:
                f.write("\n".join("Route #%d: %d" % (k + 1, r[0]) for k, r in enumerate(routes)))
                f.write("\nCost %d\n" % chk["cost"])
            man = {"instances": {"dir": os.path.join(d, "inst"), "sha256": "x"},
                   "bks": {"dir": os.path.join(d, "bks"), "sha256": "y", "downloaded_utc": "now"}}
            res = P.run_all(man, os.path.join(d, "out"), budget_fn=lambda n: 10.0, final_s=10.0, q_price=60,
                            q_final=200)
            r = res["instances"][0]
            self.assertNotIn("error", r)
            self.assertTrue(r["bks_ok"])
            self.assertEqual(r["bks_vehicles"], 14)
            self.assertFalse(r["above_bks"])
            self.assertFalse(r["unverified"])
            self.assertGreaterEqual(r["bound"], 1)
            self.assertLessEqual(r["bound"], 14)
            self.assertIsNotNone(r["bound_ng"])
            self.assertEqual(res["tally"]["done"], 1)
            with open(os.path.join(d, "out", "ngfleet", "results.json")) as f:
                self.assertEqual(json.load(f)["tally"]["done"], 1)
            self.assertTrue(os.path.exists(os.path.join(d, "out", "ngfleet", "results.md")))
            self.assertTrue(os.path.exists(os.path.join(d, "out", "ngfleet", "cert", "XTW-n15.ng.json")))
        finally:
            shutil.rmtree(d)


def XW_parse(text_lines):
    import xltwlb as X
    return X.parse_any("\n".join(text_lines) + "\n")


if __name__ == "__main__":
    unittest.main()
