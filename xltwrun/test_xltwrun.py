"""Tests for solver.py and xltwrun.py (no network). MV2 of Munim, Inc. Made with AI agents working in MV2's name.
Apache-2.0."""
import io
import json
import os
import sys
import tempfile
import textwrap
import time
import unittest

import solver as S
import xltwlb as X
import xltwrun as R


def write_instance(d, n, seed, name=None):
    inst = X.synthetic(n, seed=seed)
    text = X.write_vrplib(inst)
    if name:
        text = text.replace("NAME : SYN-n%d" % n, "NAME : %s" % name)
    p = os.path.join(d, "%s.vrp" % (name or "syn%d" % n))
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p, X.parse_any(text)


FAKE_STUBBORN = textwrap.dedent("""
    import signal, sys, time
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    n, sec = 0, None
    for line in open(sys.argv[1]):
        w = line.split()
        if not w:
            continue
        if w[0].endswith("_SECTION"):
            sec = w[0]
        elif sec == "DEMAND_SECTION":
            n += 1
    n -= 1  # the depot
    sys.stdout.write("".join("Route #%d: %d\\n" % (i, i) for i in range(1, n + 1)) + "Cost: 1\\n")
    sys.stdout.flush()
    time.sleep(60)
""")

FAKE_LATE = textwrap.dedent("""
    import sys, time
    print("hello", flush=True)
    time.sleep(3)
    print("Route #1: 1", flush=True)
    print("Cost: 5", flush=True)
""")


class Sol:
    """Stand-in for a PyVRP solution."""

    def __init__(self, routes, dist, feasible=True):
        self._routes, self._dist, self._feas = routes, dist, feasible

    def is_feasible(self):
        return self._feas

    def num_routes(self):
        return len(self._routes)

    def distance(self):
        return self._dist


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class ParseTest(unittest.TestCase):
    def test_blocks_and_other_lines(self):
        lines = [(0.1, "Route #1: 1 2\n"), (0.1, "Route #2: 3\n"), (0.1, "Cost: 10\n"), (0.5, "\n"),
                 (0.9, "log line\n"), (1.0, "Route #1: 1 2 3\n"), (1.0, "Cost 7.5\n"), (2.0, "Route #1: 1\n")]
        blocks, other = R.parse_stdout(lines)
        self.assertEqual(other, 1)
        self.assertEqual([(b[0], b[1], b[2]) for b in blocks], [(0.1, [[1, 2], [3]], 10.0), (1.0, [[1, 2, 3]], 7.5)])

    def test_malformed_route_breaks_block(self):
        blocks, other = R.parse_stdout([(0, "Route #1: 1 x\n"), (0, "Route #2: 2\n"), (0, "Cost: 3\n")])
        self.assertEqual(other, 1)
        self.assertEqual(blocks, [(0, [[2]], 3.0)])

    def test_counted_takes_last_feasible_before_limit(self):
        blocks = [(1.0, [[1]], 5.0), (2.0, [[2]], 4.0), (3.0, [[3]], 3.0), (9.0, [[4]], 1.0)]
        ok = {1: True, 2: True, 3: False, 4: True}
        check = lambda routes, inst, conv: {"ok": ok[routes[0][0]], "distance": 0.0}  # noqa: E731
        blk, chk, late = R.counted(blocks, 5.0, None, check=check)
        self.assertEqual(blk[1], [[2]])
        self.assertEqual(late, 1)
        self.assertEqual(R.counted([(6.0, [[1]], 1.0)], 5.0, None, check=check)[0], None)


class BoundsTableTest(unittest.TestCase):
    def test_table(self):
        self.assertEqual(len(R.BOUNDS), 100)
        self.assertEqual(sum(b["customers"] for b in R.BOUNDS.values()), 416241)
        self.assertEqual(sum(1 for b in R.BOUNDS.values() if b["kc"] == 1), 33)
        self.assertEqual(sum(1 for b in R.BOUNDS.values() if b["k"] > b["kc"]), 38)
        self.assertEqual(R.BOUNDS["XLTW-Test-n9363"], {"customers": 9362, "kc": 209, "k": 253})
        self.assertAlmostEqual(R.t_of(1000), 1800.0)


class PrinterTest(unittest.TestCase):
    def test_lexicographic_and_throttled(self):
        out, clock = io.StringIO(), Clock()
        p = S.Printer(50.0, out=out, convert=lambda s: s._routes, clock=clock)  # gap 1 s
        self.assertTrue(p.offer(Sol([[1, 2], [3]], 10)))
        self.assertEqual(out.getvalue(), "Route #1: 1 2\nRoute #2: 3\nCost: 10\n")
        self.assertFalse(p.offer(Sol([[1, 2], [3]], 10)))          # not better
        self.assertFalse(p.offer(Sol([[1], [2], [3]], 5)))         # more routes, even if shorter
        self.assertFalse(p.offer(Sol([[1, 2, 3]], 1, feasible=False)))
        self.assertTrue(p.offer(Sol([[1, 2, 3]], 12)))             # fewer routes: better, but within the gap
        self.assertEqual(p.prints, 1)
        self.assertTrue(p.offer(Sol([[3, 2, 1]], 11)))             # better than the pending one
        clock.t = 2.0
        self.assertFalse(p.offer(Sol([[1, 2, 3]], 11)))            # equal to the pending one
        self.assertTrue(p.flush(False))
        self.assertTrue(out.getvalue().endswith("Route #1: 3 2 1\nCost: 11\n"))
        self.assertEqual(p.prints, 2)
        self.assertFalse(p.flush(True))                            # nothing pending

    def test_margin(self):
        self.assertAlmostEqual(S.margin(100.0), 1.7)
        self.assertEqual(S.margin(18000.0), 30.0)


class SolverTest(unittest.TestCase):
    def test_bound_cap(self):
        with tempfile.TemporaryDirectory() as d:
            _, inst = write_instance(d, 60, 7)
            kc = S.capacity_bound(inst)
            cut = S.bound(inst, 0)
            self.assertTrue(cut["timed_out"])
            self.assertEqual(cut["k"], kc)
            full = S.bound(inst, 60.0)
            self.assertFalse(full["timed_out"])
            self.assertGreaterEqual(full["k"], kc)

    def test_usage(self):
        self.assertEqual(S.main(["solver.py"]), 2)

    def test_end_to_end_under_protocol(self):
        with tempfile.TemporaryDirectory() as d:
            path, inst = write_instance(d, 40, 11, name="XLTWT-n41")
            run = R.Run(path, inst, 8.0, 3, os.path.join(R.HERE, "solver.py"), d).start()
            while not run.poll():
                time.sleep(0.1)
            rec = run.finish()
            self.assertTrue(rec["exact_ok"], rec)
            self.assertEqual(rec["other_stdout_lines"], 0)
            self.assertIsNone(rec["sigterm_at"], rec)                 # stopped by itself
            self.assertTrue(rec["cost_line_ok"])
            self.assertTrue(rec["last_block_counted"])
            self.assertGreaterEqual(rec["vehicles"], S.capacity_bound(inst))
            self.assertLess(rec["at_s"], 8.0)
            self.assertEqual(rec["solver"]["customers"], 40)
            self.assertEqual(rec["solver"]["vehicles"], rec["vehicles"])
            self.assertEqual(sorted(c for r in run.routes for c in r), list(range(1, 41)))


class ProtocolTest(unittest.TestCase):
    def fake(self, d, text):
        p = os.path.join(d, "fake_%d.py" % len(os.listdir(d)))
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return p

    def test_sigterm_then_sigkill(self):
        with tempfile.TemporaryDirectory() as d:
            path, inst = write_instance(d, 12, 5)
            run = R.Run(path, inst, 3.0, 1, self.fake(d, FAKE_STUBBORN), d, grace=1.0).start()
            while not run.poll():
                time.sleep(0.1)
            rec = run.finish()
            self.assertIsNotNone(rec["sigterm_at"])
            self.assertIsNotNone(rec["sigkill_at"])
            self.assertTrue(rec["exact_ok"])
            self.assertEqual(rec["vehicles"], 12)
            self.assertFalse(rec["cost_line_ok"])                     # 'Cost: 1' is wrong; the routes' cost counts

    def test_nothing_before_the_limit(self):
        with tempfile.TemporaryDirectory() as d:
            path, inst = write_instance(d, 5, 5)
            run = R.Run(path, inst, 1.0, 1, self.fake(d, FAKE_LATE), d, grace=1.0).start()
            while not run.poll():
                time.sleep(0.1)
            rec = run.finish()
            self.assertIsNotNone(rec["sigterm_at"])
            self.assertFalse(rec["exact_ok"])
            self.assertEqual(rec["other_stdout_lines"], 1)


def fake_rec(i, kc, k, vehicles, **kw):
    r = {"instance": "I%d" % i, "customers": 1000 + i, "limit": 60.0, "kc": kc, "k": k, "vehicles": vehicles,
         "distance": 100, "exact_ok": vehicles is not None, "cost_line_ok": True, "other_stdout_lines": 0,
         "sigterm_at": None, "sigkill_at": None, "peak_gb": 0.2, "mem_est_gb": 0.3, "at_s": 50.0, "blocks": 3,
         "at_k": vehicles == k, "below_k": vehicles is not None and vehicles < k,
         "gap_k": None if vehicles is None else (vehicles - k) / float(k), "solver": {"bound": {"timed_out": False}}}
    r.update(kw)
    return r


class TallyTest(unittest.TestCase):
    def test_all_held(self):
        recs = [fake_rec(i, 1, 10, 12) for i in range(33)]                     # KC = 1, none at K
        recs += [fake_rec(100 + i, 50, 50, 50 if i < 30 else 52) for i in range(67)]
        t = R.tally(recs)
        self.assertEqual(t["at_k"], 30)
        self.assertEqual(t["at_k_kc1"], 0)
        self.assertEqual(set(t["predictions"].values()), {"held"}, t["predictions"])

    def test_misses(self):
        recs = [fake_rec(i, 1, 10, 10) for i in range(33)]                     # all KC = 1 at K: G3 fails
        recs += [fake_rec(100 + i, 50, 50, 60) for i in range(66)]             # median gap 20%: G4 fails
        recs.append(fake_rec(999, 50, 50, 49, sigterm_at=60.0, peak_gb=0.5))   # below K, SIGTERM, over the estimate
        p = R.tally(recs)["predictions"]
        self.assertEqual(p, {"G0": "did not hold", "G1": "did not hold", "G2": "held", "G3": "did not hold",
                             "G4": "did not hold", "G5": "did not hold"})

    def test_part_is_untestable(self):
        p = R.tally([fake_rec(1, 1, 3, 3)])["predictions"]
        self.assertEqual(set(p.values()), {"untestable"})

    def test_merge(self):
        recs = [fake_rec(i, 1, 10, 12) for i in range(33)] + [fake_rec(100 + i, 50, 50, 50) for i in range(67)]
        with tempfile.TemporaryDirectory() as d:
            paths = []
            for part, chunk in (("a", recs[:60]), ("b", recs[60:])):
                p = os.path.join(d, "results-%s.json" % part)
                with open(p, "w", encoding="utf-8") as f:
                    json.dump({"scale": 30.0, "runs": chunk}, f)
                paths.append(p)
            t = R.merge(paths, os.path.join(d, "out"))
            self.assertEqual(t["runs"], 100)
            self.assertEqual(t["predictions"]["G2"], "did not hold")             # 67 at K
            self.assertTrue(os.path.exists(os.path.join(d, "out", "results.md")))
            with self.assertRaises(SystemExit):
                R.merge([paths[0], paths[0]], os.path.join(d, "out2"))


if __name__ == "__main__":
    unittest.main()
