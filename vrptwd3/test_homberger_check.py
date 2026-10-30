import unittest

import homberger_check as hc


def toy(due2=5.9):
    """Depot at (0,0); customer 1 at (3,4) due 5 (reached at exactly 5); customer 2 at (3,5)."""
    return {"name": "T", "vehicles": 3, "capacity": 10,
            "rows": [(0, 0, 0, 0, 100, 0), (3, 4, 1, 0, 5, 0), (3, 5, 1, 0, due2, 0),
                     (1, 1, 1, 0, 100, 10)]}


def row(name, customers, ok, slack=1.0, hygiene=True):
    return {"id": "0", "instance": name, "expected_name": name, "family": name.split("_")[0],
            "customers": customers, "double_ok": ok, "dimacs_matches_file": hygiene,
            "double_late": 0 if ok else 1, "late_visits": 0 if ok else 1, "min_slack": slack}


class HombergerCheck(unittest.TestCase):
    def test_expected_name(self):
        self.assertEqual(hc.expected_name("436"), "C1_2_1")
        self.assertEqual(hc.expected_name("495"), "RC2_2_10")
        self.assertEqual(hc.expected_name("496"), "C1_4_1")
        self.assertEqual(hc.expected_name("676"), "C1_10_1")
        self.assertEqual(hc.expected_name("686"), "C2_10_1")
        self.assertEqual(hc.expected_name("696"), "R1_10_1")
        self.assertEqual(hc.expected_name("726"), "RC2_10_1")
        self.assertEqual(hc.expected_name("735"), "RC2_10_10")

    def test_late_visits_listed_with_arcs(self):
        visits, min_slack = hc.late_visits([[1, 2], [3]], toy())
        self.assertEqual(len(visits), 1)
        v = visits[0]
        self.assertEqual((v["route"], v["customer"], v["arcs"]), (1, 2, 2))
        self.assertAlmostEqual(v["late_by"], 0.1, places=9)
        self.assertTrue(v["within_truncation_bound"])
        self.assertAlmostEqual(min_slack, -0.1, places=9)

    def test_on_time_and_agrees_with_double_check(self):
        inst = toy(due2=6)
        visits, min_slack = hc.late_visits([[1, 2], [3]], inst)
        self.assertEqual(visits, [])
        self.assertAlmostEqual(min_slack, 0.0, places=12)
        self.assertTrue(hc.dc.check_double([[1, 2], [3]], inst)["ok"])
        late = hc.dc.check_double([[1, 2], [3]], toy())
        self.assertEqual(late["late"], len(hc.late_visits([[1, 2], [3]], toy())[0]))

    def test_outside_bound_flagged(self):
        visits, _ = hc.late_visits([[1, 2], [3]], toy(due2=5.5))
        self.assertEqual(len(visits), 1)
        self.assertFalse(visits[0]["within_truncation_bound"])  # 0.5 late after 2 arcs > 0.2

    def test_tally_and_predictions(self):
        rows = [row("C1_2_1", 200, True), row("R1_2_1", 200, False), row("R2_2_1", 200, True),
                row("R1_10_1", 1000, False), row("RC2_10_1", 1000, True, slack=0.05)]
        visits = [{"instance": "R1_2_1", "late_by": 0.1, "within_truncation_bound": True},
                  {"instance": "R1_10_1", "late_by": 0.2, "within_truncation_bound": True}]
        t = hc.tally_rows(rows, visits)
        self.assertEqual(t["rows"], 5)
        self.assertEqual(t["c_late"], [])
        self.assertEqual(t["rrc_rows"], 4)
        self.assertEqual(t["rrc_late"], 2)
        self.assertEqual(t["rrc_late_share_200"], 0.5)
        self.assertEqual(t["rrc_late_share_1000"], 0.5)
        self.assertEqual(t["by_family_size"]["R1/200"], [1, 1])
        self.assertEqual(t["feasible_min_slack_below_0.1"], 1)
        self.assertEqual(t["late_count_mismatch"], [])
        p = t["predictions"]
        self.assertEqual(p["H0"], "did not hold")  # 5 rows, not 300
        self.assertEqual(p["H1"], "held")
        self.assertEqual(p["H2"], "did not hold")  # 2 < 20
        self.assertEqual(p["H3"], "held")  # 0.5 >= 0.5
        self.assertEqual(p["H4"], "held")

    def test_score_h_edges(self):
        base = {"rows": 300, "dimacs_hygiene_fail": [], "c_late": ["C1_2_1"], "rrc_late": 140,
                "rrc_late_share_200": None, "rrc_late_share_1000": 0.3,
                "outside_truncation_bound": ["R1_2_1"]}
        p = hc.score_h(base)
        self.assertEqual(p, {"H0": "held", "H1": "did not hold", "H2": "held",
                             "H3": "untestable", "H4": "did not hold"})


if __name__ == "__main__":
    unittest.main()
