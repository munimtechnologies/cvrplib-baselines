"""Tests for xltwtest.py (no network). MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0."""
import json
import os
import tempfile
import unittest

import xltwlb as X
import xltwtest as T


def make_archive(d, files):
    import py7zr
    src = os.path.join(d, "src")
    for rel, text in files.items():
        p = os.path.join(src, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
    arch = os.path.join(d, "t.7z")
    with py7zr.SevenZipFile(arch, "w") as z:
        for rel in files:
            z.write(os.path.join(src, rel), arcname=rel)
    return arch


def fake(path, kc, kb, kt_round, kt_double, unservable=None, round_none=False):
    def conv(kt):
        return {"kt": kt, "k": max(kb, kt), "verified": True, "unservable": unservable or []}
    return {"path": path, "instance": path,
            "bounds": {"kc": kc, "kb": kb, "customers": 10, "capacity": 5,
                       "round": None if round_none else conv(kt_round), "double": conv(kt_double),
                       "dimacs": conv(kt_double)}}


class ArchiveTest(unittest.TestCase):
    def test_end_to_end(self):
        big = X.write_vrplib(X.synthetic(80, seed=3)).replace("NAME : SYN-n80", "NAME : XLTWT-n80")
        small = X.write_vrplib(X.synthetic(40, seed=4)).replace("NAME : SYN-n40", "NAME : XLTWT-n40")
        bad = "NAME : BAD\nTYPE : VRPTW\nCAPACITY : 10\nNODE_COORD_SECTION\n1 0 0\nWEIRD_SECTION\n1 2\nEOF\n"
        with tempfile.TemporaryDirectory() as d:
            arch = make_archive(d, {"XLTW-Test/XLTWT-n80.vrp": big, "XLTW-Test/XLTWT-n40.vrp": small,
                                    "XLTW-Test/README.txt": "Test set for development only.\n",
                                    "XLTW-Test/BAD.vrp": bad})
            root = T.extract(arch, os.path.join(d, "x"))
            insts, manifest, errors = T.scan(root)
            self.assertEqual([i[1]["name"] for i in insts], ["XLTWT-n40", "XLTWT-n80"])  # smallest first
            self.assertEqual(errors, ["XLTW-Test/BAD.vrp"])
            kinds = {m["path"]: m["kind"] for m in manifest}
            self.assertEqual(kinds["XLTW-Test/README.txt"], "other")
            self.assertEqual(kinds["XLTW-Test/BAD.vrp"], "instance_unparsed")
            m80 = [m for m in manifest if m["path"].endswith("n80.vrp")][0]
            self.assertIn("TIME_WINDOW_SECTION", m80["sections"])
            self.assertEqual(m80["values"]["TYPE"], "VRPTW")
            self.assertEqual(m80["stats"]["customers"], 80)
            self.assertEqual(len(m80["sha256"]), 64)
            prog = os.path.join(d, "p.jsonl")
            recs, cliques, secs = T.bound_all(insts, T.CONVS, prog)
            self.assertEqual(len(recs), 2)
            self.assertFalse(any(r.get("error") for r in recs))
            for r in recs:
                for c in T.CONVS:
                    self.assertTrue(r["bounds"][c]["verified"], c)
                    self.assertGreaterEqual(r["bounds"][c]["k"], r["bounds"]["kc"])
            self.assertEqual(set(cliques), {"XLTWT-n40", "XLTWT-n80"})
            with open(prog, encoding="utf-8") as f:
                self.assertEqual(len([json.loads(x) for x in f]), 2)
            t = T.tally(recs, errors, 0.1, secs)
            self.assertEqual(t["predictions"]["P1"], "did not hold")  # the unparsed BAD.vrp counts as an error
            t2 = T.tally(recs, [], 0.1, secs)
            self.assertEqual(t2["predictions"]["P1"], "held")
            T.write_md(os.path.join(d, "r.md"), {"url": "u", "bytes": 1, "sha256": "x"}, manifest, recs, t)


class TallyTest(unittest.TestCase):
    def test_verdicts(self):
        recs = [fake("a", 10, 10, 3, 3), fake("b", 10, 11, 3, 3), fake("c", 10, 10, 12, 12),
                fake("d", 10, 10, 9, 11)]
        t = T.tally(recs, [], 0.5, 60.0)
        p = t["predictions"]
        self.assertEqual(p["P1"], "held")
        self.assertEqual(p["P2"], "held")          # b: KB 11 > KC 10
        self.assertEqual(p["P3"], "held")          # KT > KB in round on 1 of 4 (c)
        self.assertEqual(p["P4"], "held")          # K round = K double on 3 of 4 (d differs: 10 vs 11)
        self.assertEqual(t["k_conv_eq_double"], 3)

    def test_misses(self):
        recs = [fake("a", 10, 10, 12, 12), fake("b", 10, 10, 13, 14), fake("c", 10, 10, 3, 12, unservable=[5])]
        p = T.tally(recs, [], 1.5, 60.0)["predictions"]
        self.assertEqual(p["P1"], "did not hold")  # unservable customer, and 1.5 GB
        self.assertEqual(p["P2"], "did not hold")
        self.assertEqual(p["P3"], "did not hold")  # 2 of 3 bind
        self.assertEqual(p["P4"], "did not hold")  # 1 of 3 equal

    def test_time_limit_and_unbounded(self):
        recs = [fake("a", 10, 10, 3, 3), fake("b", 10, 10, 3, 3, round_none=True)]
        t = T.tally(recs, [], 0.2, 60.0)
        self.assertEqual(t["unbounded"], ["b"])
        self.assertEqual(t["predictions"]["P1"], "did not hold")
        self.assertEqual(t["bounded_in_conv"], 1)
        self.assertEqual(T.tally([fake("a", 10, 10, 3, 3)], [], 0.2, 2000.0)["predictions"]["P1"], "did not hold")

    def test_nothing_found(self):
        self.assertEqual(set(T.tally([], [], 0.1, 1.0)["predictions"].values()), {"untestable"})

    def test_describe(self):
        keys, secs, vals = T.describe("NAME : A\nTYPE: VRPTW\nVEHICLES : 7\nNODE_COORD_SECTION\n1 0 0\nEOF\n")
        self.assertEqual(keys, ["NAME", "TYPE", "VEHICLES"])
        self.assertEqual(secs, ["NODE_COORD_SECTION"])
        self.assertEqual(vals, {"TYPE": "VRPTW", "VEHICLES": "7"})


if __name__ == "__main__":
    unittest.main()
