"""Second, independently written check of vrptw-double-v1 (cvrplib-baselines/vrptwd).

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.

vrptwd/double_check.py found that 8 of CVRPLib's 56 Solomon VRPTW best known solutions (and two of six
1,000-customer ones) arrive late somewhere when travel times are computed in double precision instead of
DIMACS's truncated tenths. Before that is described anywhere, this script re-tests every row by a different
route: files are parsed with the vrplib package (not our own parser), every distance and time is exact
50-digit Decimal arithmetic (no floats), and every late visit is listed with its arrival and due time.
It then compares each row with the first check's published figures (reference.csv).
"""
import argparse
import csv
import json
import os
import time
import urllib.request
from decimal import Decimal, getcontext

getcontext().prec = 50

BASE = "https://galgos.inf.puc-rio.br/cvrplib/en/download"
RAW = ("https://raw.githubusercontent.com/munimtechnologies/cvrplib-baselines/main/"
       "vrptwd/sols/")
UA = "CVRPLib VRPTW convention check - MV2 of Munim, Inc. (mv2@munimtech.com)"
TOL = Decimal("1e-6")   # same lateness tolerance as the first check
ARC_LOSS = Decimal("0.1")  # truncation to tenths shortens one arc by less than this
IDS = [str(i) for i in range(380, 436)] + ["676", "686", "696", "706", "716", "726"]
SOLS = ["R101", "R102", "R104", "R105", "R108", "R109", "R111", "R112", "R1_10_1", "R201", "R202",
        "R203", "R205", "R206", "R208", "R209", "RC101", "RC102", "RC106", "RC107", "RC108", "RC202",
        "RC204", "RC205"]


def fetch(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        body = r.read()
    with open(path, "wb") as f:
        f.write(body)
    time.sleep(1)
    return path


def dec(v):
    return Decimal(str(v))


def from_vrplib(d):
    """Instance dict from vrplib.read_instance(..., instance_format='solomon')."""
    return {"name": str(d.get("name", "")).strip().upper(),
            "capacity": int(d["capacity"]),
            "coords": [(dec(x), dec(y)) for x, y in d["node_coord"].tolist()],
            "demand": [int(q) for q in d["demand"].tolist()],
            "tw": [(dec(a), dec(b)) for a, b in d["time_window"].tolist()],
            "service": [dec(s) for s in d["service_time"].tolist()]}


def load_instance(path):
    import vrplib
    inst = from_vrplib(vrplib.read_instance(path, instance_format="solomon"))
    if not inst["name"]:
        with open(path, encoding="utf-8") as f:
            inst["name"] = next(line for line in f if line.strip()).split()[0].upper()
    return inst


def load_routes(path):
    import vrplib
    return [[int(c) for c in r] for r in vrplib.read_solution(path)["routes"]]


def dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2).sqrt()


def check(routes, inst):
    """Exact double-precision-convention check: time = distance, waiting allowed, late if
    arrival > due + TOL. Every late visit is listed. Distance is summed even when late."""
    n = len(inst["coords"]) - 1
    seen = set()
    for r in routes:
        if sum(inst["demand"][c] for c in r) > inst["capacity"]:
            return {"ok": False, "reason": "over capacity"}
        for c in r:
            if c in seen or not 1 <= c <= n:
                return {"ok": False, "reason": "bad or repeated customer %d" % c}
            seen.add(c)
    if len(seen) != n:
        return {"ok": False, "reason": "%d customers not visited" % (n - len(seen))}

    xy, tw, service = inst["coords"], inst["tw"], inst["service"]
    total, min_slack, late = Decimal(0), None, []
    late_routes = 0
    for k, r in enumerate(routes, 1):
        t, prev, arcs, route_late = tw[0][0], 0, 0, False
        for c in list(r) + [0]:
            d = dist(xy[prev], xy[c])
            total += d
            t += d
            arcs += 1
            slack = tw[c][1] - t
            min_slack = slack if min_slack is None else min(min_slack, slack)
            if -slack > TOL:
                route_late = True
                late.append({"route": k, "customer": c if c else "depot", "arrival": t,
                             "due": tw[c][1], "late_by": -slack, "arcs": arcs,
                             "within_truncation_bound": -slack <= ARC_LOSS * arcs})
            if c:
                t = max(t, tw[c][0]) + service[c]
            prev = c
        late_routes += route_late
    return {"ok": not late, "reason": "" if not late else "%d late arrivals" % len(late),
            "distance": total, "late": late, "late_routes": late_routes, "min_slack": min_slack}


def compare(res, ref):
    """Agreement of one exact result with one reference.csv row."""
    if "distance" not in res:
        return {"feasibility": False, "late_count": False, "max_late": False, "distance": False}
    max_late = max([v["late_by"] for v in res["late"]], default=Decimal(0))
    return {
        "feasibility": res["ok"] == (ref["double_ok"] == "True"),
        "late_count": len(res["late"]) == int(ref["late"]),
        "max_late": abs(max_late - dec(ref["max_late"])) <= Decimal("0.0001"),
        "distance": abs(res["distance"] - dec(ref["double_distance"])) <= Decimal("0.006"),
    }


def fmt(x, places=6):
    return None if x is None else str(x.quantize(Decimal(1).scaleb(-places)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", default="reference.csv")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    args = ap.parse_args()

    src = os.path.join(args.data_dir, "cvrplib-vrptw")
    sols = os.path.join(args.data_dir, "cvrplib-baselines-sols")
    out = os.path.join(args.out_dir, "vrptwd2")
    for d in (src, sols, out):
        os.makedirs(d, exist_ok=True)
    with open(args.reference, encoding="utf-8") as f:
        ref = {(r["instance"], r["source"]): r for r in csv.DictReader(f)}

    insts, todo = {}, []
    for i in IDS:
        inst = load_instance(fetch("%s/instance/%s" % (BASE, i), os.path.join(src, "%s.txt" % i)))
        insts[inst["name"]] = inst
        todo.append((inst["name"], "cvrplib-bks",
                     fetch("%s/bks/%s" % (BASE, i), os.path.join(src, "%s.sol" % i))))
    for name in SOLS:
        todo.append((name, "pyvrp-lex",
                     fetch(RAW + "%s-lex.sol" % name, os.path.join(sols, "%s-lex.sol" % name))))

    rows, visits = [], []
    for name, source, path in todo:
        routes = load_routes(path)
        res = check(routes, insts[name])
        r = ref.get((name, source))
        agree = compare(res, r) if r else None
        rows.append({"instance": name, "source": source, "routes": len(routes),
                     "routes_match_reference": bool(r and int(r["routes"]) == len(routes)),
                     "ok": res["ok"], "reason": res["reason"],
                     "distance": fmt(res.get("distance")),
                     "late": len(res.get("late", [])), "late_routes": res.get("late_routes"),
                     "max_late": fmt(max([v["late_by"] for v in res.get("late", [])], default=None)
                                     if res.get("late") else Decimal(0)),
                     "min_slack": fmt(res.get("min_slack")),
                     "agree": agree})
        for v in res.get("late", []):
            visits.append({"instance": name, "source": source, "route": v["route"],
                           "customer": v["customer"], "arrival": fmt(v["arrival"]),
                           "due": fmt(v["due"], 1), "late_by": fmt(v["late_by"]),
                           "arcs_so_far": v["arcs"],
                           "within_truncation_bound": v["within_truncation_bound"]})

    feasible = [r for r in rows if r["ok"]]
    tally = {
        "rows": len(rows), "reference_rows": len(ref),
        "missing_reference": [r["instance"] + "/" + r["source"] for r in rows if r["agree"] is None],
        "routes_mismatch": [r["instance"] + "/" + r["source"] for r in rows
                            if not r["routes_match_reference"]],
        "S1_feasibility_disagree": [r["instance"] + "/" + r["source"] for r in rows
                                    if not (r["agree"] and r["agree"]["feasibility"])],
        "S2_late_disagree": [r["instance"] + "/" + r["source"] for r in rows
                             if not (r["agree"] and r["agree"]["late_count"]
                                     and r["agree"]["max_late"])],
        "S3_distance_disagree": [r["instance"] + "/" + r["source"] for r in rows
                                 if not (r["agree"] and r["agree"]["distance"])],
        "S4_outside_truncation_bound": [v["instance"] + "/" + v["source"] for v in visits
                                        if not v["within_truncation_bound"]],
        "infeasible": [r["instance"] + "/" + r["source"] for r in rows if not r["ok"]],
        "late_visits": len(visits),
        "feasible_min_slack_below_0.1": sum(1 for r in feasible if Decimal(r["min_slack"]) < Decimal("0.1")),
        "feasible_min_slack_below_0.01": sum(1 for r in feasible if Decimal(r["min_slack"]) < Decimal("0.01")),
        "feasible": len(feasible),
    }
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump({"precision_digits": getcontext().prec, "tolerance": str(TOL),
                   "tally": tally, "rows": rows}, f, indent=1)
    with open(os.path.join(out, "late_visits.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["instance", "source", "route", "customer", "arrival", "due",
                                          "late_by", "arcs_so_far", "within_truncation_bound"])
        w.writeheader()
        w.writerows(visits)
    lines = ["# Exact (50-digit) re-check of CVRPLib VRPTW solutions in double-precision convention", "",
             "Tally: `%s`" % json.dumps(tally), "",
             "| instance | source | routes | feasible | distance | late (routes) | max late | min slack | agrees with vrptwd |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        a = r["agree"]
        lines.append("| %s | %s | %d | %s | %s | %d (%s) | %s | %s | %s |" % (
            r["instance"], r["source"], r["routes"], r["ok"], r["distance"], r["late"],
            r["late_routes"], r["max_late"], r["min_slack"],
            "n/a" if a is None else ("yes" if all(a.values()) else
                                     "NO: " + ", ".join(k for k, v in a.items() if not v))))
    lines += ["", "## Late visits", "",
              "| instance | source | route | customer | arrival | due | late by | arcs so far |",
              "|---|---|---|---|---|---|---|---|"]
    for v in visits:
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            v["instance"], v["source"], v["route"], v["customer"], v["arrival"], v["due"],
            v["late_by"], v["arcs_so_far"]))
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps(tally), flush=True)


if __name__ == "__main__":
    main()
