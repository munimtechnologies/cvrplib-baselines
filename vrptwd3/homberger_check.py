"""Double-precision re-check of all 300 Gehring & Homberger VRPTW best known solutions on CVRPLib.

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.

vrptwd/ checked the 56 Solomon BKSs and six of the 300 Homberger ones (1,000 customers, first instance of
each family): 10 of those 62 arrive late somewhere when travel times are computed in double precision
instead of the DIMACS convention CVRPLib uses (arcs truncated to 0.1). This script runs the same, published
checks (vrptwd/double_check.py, unchanged) on every Homberger instance, 200 to 1,000 customers, and lists
every late arrival with the number of arcs driven before it, so each lateness can be compared with the most
that truncation can remove (under 0.1 per arc). Predictions: expectations.md, scored by score_h() below.
"""
import argparse
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "vrptwd"))  # in the repository; in a job it sits beside this file
import double_check as dc  # noqa: E402

FAMILIES = ["C1", "C2", "R1", "R2", "RC1", "RC2"]
SIZES = [200, 400, 600, 800, 1000]
FIRST_ID = 436
EXPECTED_ROWS = 300
T0 = time.time()


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def expected_name(i):
    """CVRPLib id -> Homberger name, assuming blocks of 60 per size and 10 per family (436 = C1_2_1)."""
    k = int(i) - FIRST_ID
    return "%s_%d_%d" % (FAMILIES[(k % 60) // 10], SIZES[k // 60] // 100, k % 10 + 1)


def late_visits(routes, inst):
    """Same rules as dc.check_double; every late arrival with the arcs driven on its route so far.
    Returns (visits, min_slack)."""
    rows = inst["rows"]
    depot = rows[0]
    visits, min_slack = [], None
    for k, r in enumerate(routes, 1):
        t, prev, arcs = float(depot[3]), 0, 0
        for c in list(r) + [0]:
            t += math.hypot(rows[prev][0] - rows[c][0], rows[prev][1] - rows[c][1])
            arcs += 1
            over = t - rows[c][4]
            min_slack = -over if min_slack is None else min(min_slack, -over)
            if over > dc.EPS:
                visits.append({"route": k, "customer": c if c else "depot", "late_by": over,
                               "arcs": arcs, "within_truncation_bound": over <= 0.1 * arcs + 1e-9})
            if c:
                t = max(t, float(rows[c][3])) + rows[c][5]
            prev = c
    return visits, min_slack


def share(group):
    return None if not group else sum(1 for r in group if not r["double_ok"]) / len(group)


def score_h(t):
    """Verdicts for H0-H4 (expectations.md) from the tally."""
    def verdict(ok):
        return "untestable" if ok is None else ("held" if ok else "did not hold")
    s200, s1000 = t["rrc_late_share_200"], t["rrc_late_share_1000"]
    return {
        "H0": verdict(t["rows"] == EXPECTED_ROWS and not t["dimacs_hygiene_fail"]),
        "H1": verdict(len(t["c_late"]) == 0),
        "H2": verdict(20 <= t["rrc_late"] <= 140),
        "H3": verdict(None if s200 is None or s1000 is None else s1000 >= s200),
        "H4": verdict(not t["outside_truncation_bound"]),
    }


def tally_rows(rows, visits):
    rrc = [r for r in rows if r["family"] in ("R1", "R2", "RC1", "RC2")]
    groups = {}
    for r in rows:
        g = groups.setdefault("%s/%d" % (r["family"], r["customers"]), [0, 0])
        g[0] += 1
        g[1] += 0 if r["double_ok"] else 1
    feasible = [r for r in rows if r["double_ok"] and r["min_slack"] is not None]
    t = {
        "rows": len(rows),
        "name_mismatch": [r["id"] + ":" + r["instance"] for r in rows if r["instance"] != r["expected_name"]],
        "dimacs_hygiene_fail": [r["instance"] for r in rows if not r["dimacs_matches_file"]],
        "late_count_mismatch": [r["instance"] for r in rows
                                if r["double_late"] is not None and r["double_late"] != r["late_visits"]],
        "double_late": [r["instance"] for r in rows if not r["double_ok"]],
        "c_late": [r["instance"] for r in rows if r["family"] in ("C1", "C2") and not r["double_ok"]],
        "rrc_rows": len(rrc),
        "rrc_late": sum(1 for r in rrc if not r["double_ok"]),
        "rrc_late_share_200": share([r for r in rrc if r["customers"] == 200]),
        "rrc_late_share_1000": share([r for r in rrc if r["customers"] == 1000]),
        "by_family_size": {k: groups[k] for k in sorted(groups)},
        "late_visits": len(visits),
        "max_late": max([v["late_by"] for v in visits], default=0.0),
        "outside_truncation_bound": [v["instance"] for v in visits if not v["within_truncation_bound"]],
        "feasible_min_slack_below_0.1": sum(1 for r in feasible if r["min_slack"] < 0.1),
        "feasible_min_slack_below_0.01": sum(1 for r in feasible if r["min_slack"] < 0.01),
        "feasible": len(feasible),
    }
    t["predictions"] = score_h(t)
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="436-735")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    args = ap.parse_args()

    src = os.path.join(args.data_dir, "cvrplib-vrptw")
    out = os.path.join(args.out_dir, "vrptwd3")
    os.makedirs(src, exist_ok=True)
    os.makedirs(out, exist_ok=True)
    log("cached files in data volume: %d" % len(os.listdir(src)))

    rows, visits = [], []
    for i in dc.parse_ids(args.ids):
        p = dc.fetch("%s/instance/%s" % (dc.BASE, i), os.path.join(src, "%s.txt" % i))
        s = dc.fetch("%s/bks/%s" % (dc.BASE, i), os.path.join(src, "%s.sol" % i))
        with open(p, encoding="utf-8") as f:
            inst = dc.parse_solomon(f.read())
        with open(s, encoding="utf-8") as f:
            routes, cost = dc.parse_sol(f.read())
        row = dc.evaluate("cvrplib-bks", routes, cost, inst)
        lv, slack = late_visits(routes, inst) if not dc._structure(routes, inst) else ([], None)
        row.update({"id": i, "expected_name": expected_name(i), "family": inst["name"].split("_")[0],
                    "customers": len(inst["rows"]) - 1, "late_visits": len(lv),
                    "min_slack": None if slack is None else round(slack, 6)})
        for k in ("sintef_vehicles", "sintef_distance", "dimacs_vs_sintef", "double_vs_sintef"):
            row.pop(k, None)
        rows.append(row)
        for v in lv:
            visits.append(dict(v, instance=inst["name"], late_by=round(v["late_by"], 6)))
        log("%s %s: %d routes, dimacs_ok=%s, double_ok=%s, late=%d" % (
            i, inst["name"], len(routes), row["dimacs_ok"], row["double_ok"], len(lv)))

    tally = tally_rows(rows, visits)
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump({"eps": dc.EPS, "tally": tally, "rows": rows}, f, indent=1)
    with open(os.path.join(out, "late_visits.csv"), "w", encoding="utf-8") as f:
        f.write("instance,route,customer,late_by,arcs_so_far,within_truncation_bound\n")
        for v in visits:
            f.write("%s,%d,%s,%.6f,%d,%s\n" % (v["instance"], v["route"], v["customer"], v["late_by"],
                                               v["arcs"], v["within_truncation_bound"]))
    lines = ["# DIMACS vs double precision on all 300 Homberger VRPTW BKSs (CVRPLib)", "",
             "Predictions: `%s`" % json.dumps(tally["predictions"]), "",
             "Tally: `%s`" % json.dumps({k: v for k, v in tally.items() if k != "predictions"}), "",
             "| family | customers | BKSs | late in double |", "|---|---|---|---|"]
    for k, (n, late) in tally["by_family_size"].items():
        fam, size = k.split("/")
        lines.append("| %s | %s | %d | %d |" % (fam, size, n, late))
    lines += ["", "| id | instance | routes | DIMACS cost | double ok | double distance | late (routes) | max late | min slack |",
              "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append("| %s | %s | %d | %s | %s | %s | %s (%s) | %s | %s |" % (
            r["id"], r["instance"], r["routes"], r["dimacs_cost"], r["double_ok"], r["double_distance"],
            r["double_late"], r["double_late_routes"], r["double_max_late"], r["min_slack"]))
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps(tally), flush=True)


if __name__ == "__main__":
    main()
