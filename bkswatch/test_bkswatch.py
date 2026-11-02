"""Tests for bkswatch.py (MV2 of Munim, Inc.; made with AI agents working in MV2's name; Apache-2.0)."""
import csv
import json
import os
import tempfile
import unittest

import bkswatch as B
import double_check as dc


def row(name, routes, cost, double_ok=True, i="1"):
    return {"id": i, "instance": name, "routes": routes, "file_cost": cost, "dimacs_ok": True,
            "dimacs_matches_file": True, "double_ok": double_ok, "double_late": 0 if double_ok else 3,
            "double_late_routes": 0 if double_ok else 2, "double_max_late": 0.0, "double_distance": cost + 40}


REF = {"C1_10_9": {"instance": "C1_10_9", "routes": 90, "dimacs_cost": 40282.2, "double_ok": True},
       "R1_10_1": {"instance": "R1_10_1", "routes": 95, "dimacs_cost": 53026.1, "double_ok": False},
       "R1_10_5": {"instance": "R1_10_5", "routes": 92, "dimacs_cost": 50388.5, "double_ok": True},
       "R1_10_9": {"instance": "R1_10_9", "routes": 91, "dimacs_cost": 49140.6, "double_ok": True},
       "R101": {"instance": "R101", "routes": 20, "dimacs_cost": 1637.7, "double_ok": True}}
BOUNDS = {"R1_10_1": {"K_double": 100, "K_dimacs": 91}, "R101": {"K_double": 19, "K_dimacs": 19}}


def full(rows):
    """Pad to 356 unchanged rows so W0/W5 can be tested."""
    pad = [dict(row("X%d" % k, 10, 100.0), changed=False) for k in range(B.EXPECTED_ROWS - len(rows))]
    return rows + pad


class TestCollect(unittest.TestCase):
    def test_only_bks_rows_first_wins(self):
        data = {"rows": [{"instance": "R101", "source": "pyvrp-lex", "routes": 19, "dimacs_cost": 1646.0},
                         {"instance": "R101", "source": "cvrplib-bks", "routes": 20, "dimacs_cost": 1637.7},
                         {"instance": "C101", "routes": 10, "dimacs_cost": 828.9}],
                "tally": {"x": 1}}
        got = B.collect_bks_rows(data)
        self.assertEqual(got["R101"]["routes"], 20)
        self.assertIn("C101", got)

    def test_load_reference_order(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, "a.json"), os.path.join(d, "b.json")
            with open(a, "w") as f:
                json.dump({"rows": [{"instance": "R101", "routes": 20, "dimacs_cost": 1.0}]}, f)
            with open(b, "w") as f:
                json.dump({"rows": [{"instance": "R101", "routes": 21, "dimacs_cost": 2.0},
                                    {"instance": "R102", "routes": 18, "dimacs_cost": 3.0}]}, f)
            ref = B.load_reference([a, b])
        self.assertEqual(ref["R101"]["routes"], 20)
        self.assertEqual(ref["R102"]["routes"], 18)

    def test_load_bounds(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "bounds.csv")
            with open(p, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["id", "instance", "customers", "KC", "KT_double", "K_double", "KT_dimacs", "K_dimacs"])
                w.writerow(["696", "R1_10_1", "1000", "91", "100", "100", "91", "91"])
            got = B.load_bounds(p)
        self.assertEqual(got["R1_10_1"], {"K_double": 100, "K_dimacs": 91})


class TestCompare(unittest.TestCase):
    def test_unchanged(self):
        r = B.compare(row("R101", 20, 1637.7), REF, BOUNDS)
        self.assertFalse(r["changed"])
        self.assertFalse(r["below_K_double"])

    def test_cost_change_and_below_bound(self):
        r = B.compare(row("R1_10_1", 95, 52982.0, double_ok=False), REF, BOUNDS)
        self.assertTrue(r["changed"])
        self.assertTrue(r["below_K_double"])
        self.assertEqual(r["ref_cost"], 53026.1)

    def test_route_change_only(self):
        self.assertTrue(B.compare(row("R101", 19, 1637.7), REF, BOUNDS)["changed"])

    def test_no_reference(self):
        r = B.compare(row("ZZ", 5, 1.0), REF, BOUNDS)
        self.assertIsNone(r["changed"])
        self.assertIsNone(r["K_double"])


class TestScore(unittest.TestCase):
    def announced(self, r1_routes=95, r1_ok=False, oks=(True, True, True), routes=(90, 92, 91)):
        rows = [row("R1_10_1", r1_routes, 52982.0, r1_ok)]
        for n, ok, k in zip(B.OTHERS, oks, routes):
            rows.append(row(n, k, B.ANNOUNCED[n], ok))
        return [B.compare(r, REF, BOUNDS) for r in rows]

    def test_all_held(self):
        p = B.score_w(full(self.announced()))
        self.assertEqual(set(p.values()), {"held"})

    def test_w2_fails_when_on_time_or_100_routes(self):
        self.assertEqual(B.score_w(full(self.announced(r1_routes=100, r1_ok=True)))["W2"], "did not hold")
        self.assertEqual(B.score_w(full(self.announced(r1_ok=True)))["W2"], "did not hold")

    def test_w3_w4(self):
        p = B.score_w(full(self.announced(oks=(True, False, False), routes=(90, 91, 91))))
        self.assertEqual(p["W3"], "did not hold")
        self.assertEqual(p["W4"], "did not hold")

    def test_w1_later_lower_value_still_holds(self):
        rows = self.announced()
        rows[0]["file_cost"] = 52900.0
        self.assertEqual(B.score_w(full(rows))["W1"], "held")

    def test_w1_unchanged_fails(self):
        rows = self.announced()
        rows[1] = B.compare(row("C1_10_9", 90, 40282.2), REF, BOUNDS)
        self.assertEqual(B.score_w(full(rows))["W1"], "did not hold")

    def test_w0_error_and_w5(self):
        rows = full(self.announced())
        rows[-1] = {"id": "735", "instance": None, "error": "URLError: x"}
        p = B.score_w(rows)
        self.assertEqual(p["W0"], "did not hold")
        self.assertEqual(p["W5"], "untestable")
        rows = full(self.announced())
        for r in rows[4:8]:
            r["changed"] = True
        self.assertEqual(B.score_w(rows)["W5"], "did not hold")

    def test_missing_announced_untestable(self):
        p = B.score_w(full([]))
        self.assertEqual(p["W1"], "untestable")
        self.assertEqual(p["W2"], "untestable")


class TestOutputs(unittest.TestCase):
    def test_write(self):
        rows = full(TestScore().announced())
        with tempfile.TemporaryDirectory() as d:
            t = B.write_outputs(rows, d)
            self.assertEqual(len(t["changed"]), 4)
            with open(os.path.join(d, "results.md"), encoding="utf-8") as f:
                md = f.read()
            self.assertIn("| R1_10_1 | 95 (95) | 52982.0 (53026.1)", md.replace("| 1 | ", "| "))
            with open(os.path.join(d, "bks.csv"), encoding="utf-8") as f:
                self.assertEqual(len(list(csv.DictReader(f))), B.EXPECTED_ROWS)


class TestDoubleCheckModule(unittest.TestCase):
    """The unchanged vrptwd/double_check.py is importable and has what bkswatch uses."""

    def test_api(self):
        for name in ("BASE", "fetch", "parse_ids", "parse_solomon", "parse_sol", "evaluate"):
            self.assertTrue(hasattr(dc, name), name)
        self.assertEqual(dc.parse_ids("380-382,696"), ["380", "381", "382", "696"])
        routes, cost = dc.parse_sol("Route #1: 1 2\nRoute #2: 3\nCost 12.5\n")
        self.assertEqual(routes, [[1, 2], [3]])
        self.assertEqual(cost, 12.5)


if __name__ == "__main__":
    unittest.main()
