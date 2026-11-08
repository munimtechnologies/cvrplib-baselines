"""Tests for nbrun.py and getnb.py (no network). The end-to-end test runs the built route minimiser when the job's
setup has placed it next to this file, and is skipped otherwise.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.
"""
import hashlib
import os
import tempfile
import unittest

import getnb
import nbrun

HERE = os.path.dirname(os.path.abspath(__file__))


class Patch(unittest.TestCase):
    def test_once(self):
        src = "static double coord_distance(...) {\n\tdouble dx = xs[i] - xs[j];\n\treturn sqrt(dx * dx + dy * dy);\n}\n"
        new, k = getnb.patch_source(src)
        self.assertEqual(k, 1)
        self.assertIn("return floor(sqrt(dx * dx + dy * dy) + 0.5);", new)

    def test_none(self):
        self.assertEqual(getnb.patch_source("return hypot(dx, dy);")[1], 0)


class Prereg(unittest.TestCase):
    def test_hash_gate(self):
        body = b"# nbrm: expectations\n"
        h = hashlib.sha256(body).hexdigest()
        got = getnb.wait_prereg("unused", getter=lambda url, tries=1: body, deadline=0, sleep=lambda s: None,
                                expected=h)
        self.assertEqual(got, h)
        with self.assertRaises(SystemExit):
            getnb.wait_prereg("unused", getter=lambda url, tries=1: body + b"x", deadline=0, sleep=lambda s: None,
                              expected=h)

    def test_crlf_normalised(self):
        body = b"a\nb\n"
        h = hashlib.sha256(body).hexdigest()
        self.assertEqual(getnb.wait_prereg("unused", getter=lambda url, tries=1: b"a\r\nb\r\n", deadline=0,
                                           sleep=lambda s: None, expected=h), h)

    def test_addendum(self):
        ok = b"# nbrm addendum\nnbrm-v2 ...\n"
        self.assertEqual(getnb.wait_addendum(getter=lambda url, tries=1: ok, deadline=0, sleep=lambda s: None),
                         hashlib.sha256(ok).hexdigest())
        with self.assertRaises(SystemExit):
            getnb.wait_addendum(getter=lambda url, tries=1: b"other", deadline=0, sleep=lambda s: None)


class Limits(unittest.TestCase):
    def test_values(self):
        self.assertEqual([nbrun.fleet_limit(r[2]) for r in nbrun.RUNS], [1109, 1278, 1446, 1656])
        self.assertEqual([nbrun.limit_for(r[2]) for r in nbrun.RUNS], [2219.4, 2556.0, 2892.6, 3312.0])
        self.assertEqual(sum(r[4] for r in nbrun.RUNS), 231)
        self.assertEqual(sum(r[3] for r in nbrun.RUNS), 173)


class Format(unittest.TestCase):
    def test_homberger_roundtrip(self):
        import xltwlb as X
        inst = nbrun.synthetic(40)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.txt")
            nbrun.write_homberger(inst, p)
            with open(p, encoding="ascii") as f:
                text = f.read()
        back = X.parse_solomon(text)
        self.assertEqual(back["rows"], inst["rows"])
        self.assertEqual(back["capacity"], inst["capacity"])
        self.assertIn("CUST NO.  XCOORD.   YCOORD.    DEMAND   READY TIME  DUE DATE   SERVICE   TIME", text)
        self.assertEqual(text.splitlines()[0], inst["name"])

    def test_parse_sol(self):
        text = "0 0 3 12.5 1 30 0 48.2\n0 0 2 7 0 20\n\n"
        self.assertEqual(nbrun.parse_sol(text), [[3, 1], [2]])
        with self.assertRaises(ValueError):
            nbrun.parse_sol("0 0 3\n")

    def test_incumbents(self):
        out = "\x1b[35mincumbent_ms: 0 n_routes: 60\x1b[0m\nroutes number: 59\nincumbent_ms: 1520 n_routes: 59\n"
        incs = nbrun.incumbents(out)
        self.assertEqual(incs, [(0, 60), (1520, 59)])
        self.assertEqual(nbrun.first_ms_at(incs, 59), 1520)
        self.assertIsNone(nbrun.first_ms_at(incs, 58))

    def test_check_uses_round(self):
        inst = nbrun.synthetic(12)
        one_each = [[c] for c in range(1, 13)]
        chk = nbrun.check(one_each, inst)
        self.assertTrue(chk["feasible"], chk)
        self.assertFalse(nbrun.check(one_each[:-1], inst)["feasible"])


@unittest.skipUnless(os.path.exists(os.path.join(HERE, "routes")), "route minimiser not built here")
class EndToEnd(unittest.TestCase):
    def test_smoke_with_real_binary(self):
        """The real binary on the smoke instance, exactly as main() runs it: stops by itself, writes a solution
        that the exact check accepts."""
        with tempfile.TemporaryDirectory() as d:
            rec = nbrun.one(os.path.join(HERE, "routes"), "e2e", nbrun.synthetic(60), 3, 0, 1, d, 120.0)
        self.assertIsNone(rec["killed_at"], rec)
        self.assertEqual(rec["exit"], 0, rec)
        self.assertIsNotNone(rec["vehicles"], rec)
        self.assertTrue(rec["feasible"], rec)
        self.assertTrue(rec["valid"], rec)
        self.assertGreater(rec["incumbents"], 0, rec)


def rec(rid, veh, cpu=100.0, peak=0.1, ok=True):
    r = dict(zip(("id", "instance", "customers", "k_star"), nbrun.BY_ID[rid][:4]))
    r.update({"exit": 0, "killed_at": None, "vehicles": veh, "feasible": ok, "cpu": cpu, "peak_gb": peak,
              "t_max": nbrun.fleet_limit(r["customers"])})
    return r


class Score(unittest.TestCase):
    def res(self, veh, **kw):
        return {"build": {"patch_matches": 1, "built": True}, "smoke": {"exit": 0, "killed_at": None, "vehicles": 7,
                                                                        "feasible": True},
                "runs": [rec(i, v, **kw) for i, v in zip(("N1", "N2", "N3", "N4"), veh)]}

    def test_all_held(self):
        p = nbrun.score(self.res([30, 58, 100, 22]))
        self.assertEqual(set(p.values()), {"held"}, p)

    def test_gate(self):
        r = self.res([30, 58, 100, 22])
        r["runs"][2]["feasible"] = False
        p = nbrun.score(r)
        self.assertEqual(p["N0"], "did not hold")
        self.assertTrue(p["N3"].startswith("untestable"))
        r = self.res([30, 58, 100, 22])
        r["build"]["patch_matches"] = 2
        self.assertEqual(nbrun.score(r)["N0"], "did not hold")
        r = self.res([30, 58, 100, 22])
        r["smoke"]["feasible"] = False
        self.assertEqual(nbrun.score(r)["N0"], "did not hold")

    def test_thresholds(self):
        p = nbrun.score(self.res([33, 65, 107, 25]))  # one fewer only, total 230
        self.assertEqual((p["N1"], p["N2"], p["N3"]), ("held", "did not hold", "did not hold"))
        p = nbrun.score(self.res([34, 60, 100, 20]))
        self.assertEqual((p["N1"], p["N2"], p["N3"]), ("did not hold", "held", "held"))
        p = nbrun.score(self.res([30, 58, 100, 33]))  # total 221 exactly: N3 holds
        self.assertEqual(p["N3"], "held")
        p = nbrun.score(self.res([30, 58, 100, 34]))  # total 222
        self.assertEqual(p["N3"], "did not hold")
        p = nbrun.score(self.res([27, 47, 100, 22]))
        self.assertEqual(p["N4"], "did not hold")
        p = nbrun.score(self.res([30, 58, 100, 22], cpu=1109 + 61))
        self.assertEqual(p["N5"], "did not hold")
        p = nbrun.score(self.res([30, 58, 100, 22], peak=0.51))
        self.assertEqual(p["N5"], "did not hold")


if __name__ == "__main__":
    unittest.main()
