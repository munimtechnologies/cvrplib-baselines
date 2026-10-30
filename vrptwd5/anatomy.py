"""Where on their routes the CVRPLib VRPTW best known solutions turn late in double precision, and why.

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.

vrptwd/ and vrptwd3/ found that 90 of the 356 VRPTW BKSs on CVRPLib (8 of 56 Solomon, 82 of 300 Homberger)
arrive late somewhere when travel times are not truncated to 0.1, the DIMACS convention they were found under,
and that lateness concentrates in C2 at 800 and 1,000 customers. This script looks at every route. Each arc is
up to 0.1 shorter under DIMACS than in double precision, so a route drifts later in double precision until the
vehicle waits for a window to open, which resets the drift to zero. A visit can therefore only turn late if its
DIMACS slack (due time minus arrival, in tenths) is smaller than the number of arcs driven since the last such
wait; such a visit is called "exposed". A route is "horizon-bound" if it returns to the depot within 1.0 time
unit of the depot's due time under DIMACS. Predictions: expectations.md, scored by score_a() below.
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

EXPECTED_ROWS = 356
EXPECTED_LATE = 90
HORIZON_TENTHS = 10
T0 = time.time()


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def tenths(x):
    return int(round(10 * x))


def family(name):
    """'C101' -> 'C1', 'RC208' -> 'RC2', 'C2_8_3' -> 'C2'."""
    return name.split("_")[0] if "_" in name else name[:-2]


def route_anatomy(route, rows):
    """One route under both conventions. Visits are its customers, then the return to the depot."""
    depot = rows[0]
    t_d, t_x, prev, chain = tenths(depot[3]), float(depot[3]), 0, 0
    out = {"customers": len(route), "waits": 0, "zero_slack": 0, "exposed": 0, "late": 0,
           "late_unexposed": 0, "max_chain": 0, "first_late": None, "depot_slack": None}
    stops = list(route) + [0]
    for k, c in enumerate(stops):
        t_d += dc.dist10(rows[prev], rows[c])
        t_x += math.hypot(rows[prev][0] - rows[c][0], rows[prev][1] - rows[c][1])
        chain += 1
        out["max_chain"] = max(out["max_chain"], chain)
        slack = tenths(rows[c][4]) - t_d
        exposed = slack < chain
        out["zero_slack"] += slack == 0
        out["exposed"] += exposed
        over = t_x - rows[c][4]
        if over > dc.EPS:
            out["late"] += 1
            out["late_unexposed"] += not exposed
            if out["first_late"] is None:
                out["first_late"] = {"stop": c if c else "depot", "from_end": len(stops) - 1 - k,
                                     "chain": chain, "slack": slack, "late_by": round(over, 6)}
        if c:
            ready = rows[c][3]
            out["waits"] += t_d < tenths(ready)
            if t_x < ready:
                chain = 0
            t_d = max(t_d, tenths(ready)) + tenths(rows[c][5])
            t_x = max(t_x, float(ready)) + rows[c][5]
        else:
            out["depot_slack"] = slack
        prev = c
    out["horizon_bound"] = out["depot_slack"] <= HORIZON_TENTHS
    out["wait_share"] = round(out["waits"] / out["customers"], 4)
    return out


def instance_anatomy(routes, inst):
    """Per-route anatomies and their instance totals."""
    per = [route_anatomy(r, inst["rows"]) for r in routes]
    customers = sum(p["customers"] for p in per)
    return per, {
        "late": sum(p["late"] for p in per),
        "late_routes": sum(1 for p in per if p["late"]),
        "late_unexposed": sum(p["late_unexposed"] for p in per),
        "exposed": sum(p["exposed"] for p in per),
        "zero_slack": sum(p["zero_slack"] for p in per),
        "wait_share": round(sum(p["waits"] for p in per) / customers, 4) if customers else None,
        "horizon_bound_routes": sum(1 for p in per if p["horizon_bound"]),
        "max_chain": max((p["max_chain"] for p in per), default=0),
    }


def auc(pos, neg):
    """Probability that a random value from pos exceeds one from neg (ties count half)."""
    if not pos or not neg:
        return None
    wins = 0.0
    for p in pos:
        for q in neg:
            wins += 1.0 if p > q else 0.5 if p == q else 0.0
    return wins / (len(pos) * len(neg))


def mean(xs):
    return None if not xs else sum(xs) / len(xs)


def route_rate(rows):
    n = sum(r["routes"] for r in rows)
    return None if not n else sum(r["late_routes"] or 0 for r in rows) / n


def horizon_share(routes):
    return None if not routes else sum(1 for p in routes if p["horizon_bound"]) / len(routes)


def score_a(t):
    """Verdicts for A0-A5 (expectations.md) from the tally."""
    def verdict(ok):
        return "untestable" if ok is None else ("held" if ok else "did not hold")
    small, large = t["c2_route_late_rate_200_600"], t["c2_route_late_rate_800_1000"]
    hc, hr = t["c2_late_horizon_share"], t["r1rc1_late_horizon_share"]
    wl, wo = t["c2_wait_share_late_routes"], t["c2_wait_share_other_routes"]
    a = t["auc_exposed"]
    return {
        "A0": verdict(t["rows"] == EXPECTED_ROWS and not t["dimacs_fail"] and not t["count_mismatch"]
                      and t["late_unexposed"] == 0 and t["late_instances"] == EXPECTED_LATE),
        "A1": verdict(None if not small or large is None else large <= 2 * small),
        "A2": verdict(None if hc is None else hc >= 0.75),
        "A3": verdict(None if hc is None or hr is None else hr < hc),
        "A4": verdict(None if wl is None or wo is None else wl < wo),
        "A5": verdict(None if a is None else a >= 0.80),
    }


def tally_rows(rows, routes):
    c2 = [r for r in rows if r["family"] == "C2" and r["set"] == "homberger"]
    late = [p for p in routes if p["late"]]
    c2_routes = [p for p in routes if p["family"] == "C2" and p["set"] == "homberger"]
    c2_late = [p for p in late if p["family"] == "C2"]
    r1rc1_late = [p for p in late if p["family"] in ("R1", "RC1")]
    groups = {}
    for r in rows:
        g = groups.setdefault("%s/%d" % (r["family"], r["customers"]),
                              {"instances": 0, "late_instances": 0, "routes": 0, "late_routes": 0})
        g["instances"] += 1
        g["late_instances"] += 0 if r["double_ok"] else 1
        g["routes"] += r["routes"]
        g["late_routes"] += r["late_routes"] or 0
    for key, g in groups.items():
        fam, size = key.split("/")
        mine = [p for p in routes if p["family"] == fam and p["customers_total"] == int(size)]
        g["route_late_rate"] = round(g["late_routes"] / g["routes"], 4) if g["routes"] else None
        g["mean_wait_share"] = None if not mine else round(mean([p["wait_share"] for p in mine]), 4)
        g["horizon_bound_routes"] = sum(1 for p in mine if p["horizon_bound"])
        g["late_horizon_bound"] = sum(1 for p in mine if p["late"] and p["horizon_bound"])
        g["exposed_per_route"] = None if not mine else round(mean([p["exposed"] for p in mine]), 3)
    t = {
        "rows": len(rows),
        "dimacs_fail": [r["instance"] for r in rows if not (r["dimacs_ok"] and r["dimacs_matches_file"])],
        "count_mismatch": [r["instance"] for r in rows if r["late"] != r["double_late"]
                           or r["late_routes"] != r["double_late_routes"]],
        "late_instances": sum(1 for r in rows if not r["double_ok"]),
        "late_routes": len(late),
        "late_unexposed": sum(r["late_unexposed"] for r in rows),
        "c2_route_late_rate_200_600": route_rate([r for r in c2 if r["customers"] <= 600]),
        "c2_route_late_rate_800_1000": route_rate([r for r in c2 if r["customers"] >= 800]),
        "c2_late_routes": len(c2_late),
        "c2_late_horizon_share": horizon_share(c2_late),
        "r1rc1_late_routes": len(r1rc1_late),
        "r1rc1_late_horizon_share": horizon_share(r1rc1_late),
        "c2_wait_share_late_routes": mean([p["wait_share"] for p in c2_routes if p["late"]]),
        "c2_wait_share_other_routes": mean([p["wait_share"] for p in c2_routes if not p["late"]]),
        "auc_exposed": auc([r["exposed"] for r in rows if not r["double_ok"] and r["exposed"] is not None],
                           [r["exposed"] for r in rows if r["double_ok"]]),
        "first_late_at_depot": sum(1 for p in late if p["first_late"]["stop"] == "depot"),
        "first_late_zero_slack": sum(1 for p in late if p["first_late"]["slack"] == 0),
        "by_family_size": {k: groups[k] for k in sorted(groups)},
    }
    t["predictions"] = score_a(t)
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="380-735")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    args = ap.parse_args()

    src = os.path.join(args.data_dir, "cvrplib-vrptw")
    out = os.path.join(args.out_dir, "vrptwd5")
    os.makedirs(src, exist_ok=True)
    os.makedirs(out, exist_ok=True)
    log("cached files in data volume: %d" % len(os.listdir(src)))

    rows, routes = [], []
    for i in dc.parse_ids(args.ids):
        p = dc.fetch("%s/instance/%s" % (dc.BASE, i), os.path.join(src, "%s.txt" % i))
        s = dc.fetch("%s/bks/%s" % (dc.BASE, i), os.path.join(src, "%s.sol" % i))
        with open(p, encoding="utf-8") as f:
            inst = dc.parse_solomon(f.read())
        with open(s, encoding="utf-8") as f:
            sol_routes, cost = dc.parse_sol(f.read())
        row = dc.evaluate("cvrplib-bks", sol_routes, cost, inst)
        for k in ("source", "sintef_vehicles", "sintef_distance", "dimacs_vs_sintef", "double_vs_sintef"):
            row.pop(k, None)
        fam, n = family(inst["name"]), len(inst["rows"]) - 1
        row.update({"id": i, "family": fam, "customers": n,
                    "set": "homberger" if "_" in inst["name"] else "solomon"})
        if dc._structure(sol_routes, inst):
            row.update({"late": None, "late_routes": None, "late_unexposed": 0, "exposed": None})
        else:
            per, totals = instance_anatomy(sol_routes, inst)
            row.update(totals)
            for k, p in enumerate(per, 1):
                routes.append(dict(p, instance=inst["name"], route=k, family=fam, customers_total=n,
                                   set=row["set"]))
        rows.append(row)
        log("%s %s: %d routes, double_ok=%s, late routes=%s, exposed=%s, horizon-bound=%s" % (
            i, inst["name"], len(sol_routes), row["double_ok"], row["late_routes"], row["exposed"],
            row.get("horizon_bound_routes")))

    tally = tally_rows(rows, routes)
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump({"eps": dc.EPS, "horizon_tenths": HORIZON_TENTHS, "tally": tally, "rows": rows}, f, indent=1)
    with open(os.path.join(out, "routes.csv"), "w", encoding="utf-8") as f:
        f.write("instance,route,family,customers_total,customers,waits,wait_share,max_chain,zero_slack,"
                "exposed,depot_slack_tenths,horizon_bound,late,first_late_stop,first_late_from_end,"
                "first_late_chain,first_late_slack_tenths,first_late_by\n")
        for p in routes:
            fl = p["first_late"] or {}
            f.write("%s,%d,%s,%d,%d,%d,%.4f,%d,%d,%d,%d,%s,%d,%s,%s,%s,%s,%s\n" % (
                p["instance"], p["route"], p["family"], p["customers_total"], p["customers"], p["waits"],
                p["wait_share"], p["max_chain"], p["zero_slack"], p["exposed"], p["depot_slack"],
                p["horizon_bound"], p["late"], fl.get("stop", ""), fl.get("from_end", ""),
                fl.get("chain", ""), fl.get("slack", ""), fl.get("late_by", "")))
    lines = ["# Route anatomy of the 356 CVRPLib VRPTW BKSs, DIMACS vs double precision", "",
             "Predictions: `%s`" % json.dumps(tally["predictions"]), "",
             "Tally: `%s`" % json.dumps({k: v for k, v in tally.items()
                                         if k not in ("predictions", "by_family_size")}), "",
             "| family | customers | BKSs | late BKSs | routes | late routes | route late rate | mean wait share "
             "| horizon-bound routes | late and horizon-bound | exposed visits per route |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, g in tally["by_family_size"].items():
        fam, size = k.split("/")
        lines.append("| %s | %s | %d | %d | %d | %d | %s | %s | %d | %d | %s |" % (
            fam, size, g["instances"], g["late_instances"], g["routes"], g["late_routes"],
            g["route_late_rate"], g["mean_wait_share"], g["horizon_bound_routes"], g["late_horizon_bound"],
            g["exposed_per_route"]))
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps(tally["predictions"]), flush=True)


if __name__ == "__main__":
    main()
