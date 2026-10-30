"""Independent exact re-check of the vrptwd4 repaired solutions (cvrplib-baselines/vrptwd4x).

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.

vrptwd4/repair.py published 87 solutions that repair CVRPLib VRPTW best known solutions (BKSs) which are late in
double precision, each with no more routes than the BKS. Inside that job they were checked only by
vrptwd/double_check.py. Before they are described anywhere else, this script re-tests every one by a different
route, as vrptwd2/exact_check.py did for vrptwd/: the vrplib package parses the instance, BKS and solution files
(not our own parser), every distance is exact 50-digit Decimal arithmetic (no floats), and each solution is checked
under both conventions: double precision, and DIMACS (every arc truncated to one decimal).
"""
import argparse
import json
import os
import socket
import time
import urllib.error
import urllib.request
from decimal import ROUND_FLOOR, Decimal, getcontext

getcontext().prec = 50
socket.setdefaulttimeout(120)

BASE = "https://galgos.inf.puc-rio.br/cvrplib/en/download"
RAW = "https://raw.githubusercontent.com/munimtechnologies/cvrplib-baselines/main/vrptwd4/"
UA = "CVRPLib VRPTW convention check - MV2 of Munim, Inc. (mv2@munimtech.com)"
TOL = Decimal("1e-6")   # same lateness tolerance as vrptwd/ and vrptwd2/
FEWER = {"R2_2_1": (12, 13), "R2_2_2": (10, 11), "R2_6_5": (21, 22)}  # (repair, BKS) routes per vrptwd4
T0 = time.time()


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def fetch(url, path, tries=1, wait=0):
    """Download url to path, keeping a cached copy. Retries on 404 cover the minutes between this job being
    filed and the vrptwd4 commit reaching the repository."""
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    t = time.time()
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code != 404 or k == tries - 1:
                raise
            log("%s not there yet (404), waiting %d s" % (url, wait))
            time.sleep(wait)
    with open(path, "wb") as f:
        f.write(body)
    log("fetched %s (%d bytes, %.1fs)" % (url, len(body), time.time() - t))
    time.sleep(1)
    return path


def dec(v):
    return Decimal(str(v))


def from_vrplib(d):
    """Instance dict from vrplib.read_instance(..., instance_format='solomon')."""
    return {"capacity": int(d["capacity"]),
            "coords": [(dec(x), dec(y)) for x, y in d["node_coord"].tolist()],
            "demand": [int(q) for q in d["demand"].tolist()],
            "tw": [(dec(a), dec(b)) for a, b in d["time_window"].tolist()],
            "service": [dec(s) for s in d["service_time"].tolist()]}


def load_instance(path):
    import vrplib
    return from_vrplib(vrplib.read_instance(path, instance_format="solomon"))


def load_routes(path):
    import vrplib
    return [[int(c) for c in r] for r in vrplib.read_solution(path)["routes"]]


def cost_line(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.lower().startswith("cost"):
                return dec(line.split()[1])
    return None


def arc(a, b, dimacs):
    d = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2).sqrt()
    return (d * 10).to_integral_value(rounding=ROUND_FLOOR) / 10 if dimacs else d


def check(routes, inst, dimacs=False):
    """Exact check: time = distance, waiting allowed, late if arrival > due + TOL. With dimacs=True every arc
    is truncated to one decimal first. Every late visit is listed; distance is summed even when late."""
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
    for k, r in enumerate(routes, 1):
        t, prev = tw[0][0], 0
        for c in list(r) + [0]:
            d = arc(xy[prev], xy[c], dimacs)
            total += d
            t += d
            slack = tw[c][1] - t
            min_slack = slack if min_slack is None else min(min_slack, slack)
            if -slack > TOL:
                late.append({"route": k, "customer": c if c else "depot", "late_by": -slack})
            if c:
                t = max(t, tw[c][0]) + service[c]
            prev = c
    return {"ok": not late, "reason": "" if not late else "%d late arrivals" % len(late),
            "distance": total, "late": late, "min_slack": min_slack}


def score_x(t):
    """Verdicts for the predictions in expectations.md, from the tally only."""
    def verdict(ok):
        return "held" if ok else "did not hold"
    return {
        "X0": verdict(t["checked"] == t["published_repaired"] == 87 and not t["structure_fail"]
                      and not t["routes_mismatch"] and not t["more_routes_than_bks"]),
        "X1": verdict(t["double_ok"] == 87),
        "X2": verdict(not t["distance_disagree"]),
        "X3": verdict(t["dimacs_ok"] == 87 and not t["dimacs_cost_disagree"]),
        "X4": verdict(t["fewer_routes_confirmed"] == sorted(FEWER)),
    }


def tally_rows(rows, published_repaired):
    t = {
        "published_repaired": published_repaired,
        "checked": len(rows),
        "structure_fail": [r["instance"] for r in rows if r["double_reason"] and "late" not in r["double_reason"]],
        "routes_mismatch": [r["instance"] for r in rows if r["routes"] != r["published_routes"]],
        "more_routes_than_bks": [r["instance"] for r in rows if r["routes"] > r["bks_routes"]],
        "double_ok": sum(1 for r in rows if r["double_ok"]),
        "dimacs_ok": sum(1 for r in rows if r["dimacs_ok"]),
        "distance_disagree": [r["instance"] for r in rows if not r["distance_agrees"]],
        "dimacs_cost_disagree": [r["instance"] for r in rows if not r["dimacs_cost_agrees"]],
        "fewer_routes_than_bks": sorted(r["instance"] for r in rows if r["routes"] < r["bks_routes"]),
        "fewer_routes_confirmed": sorted(r["instance"] for r in rows if r["instance"] in FEWER
                                         and (r["routes"], r["bks_routes"]) == FEWER[r["instance"]]
                                         and r["double_ok"]),
        "min_double_slack": min((Decimal(r["double_min_slack"]) for r in rows if r["double_ok"]), default=None),
        "double_slack_below_0.01": sum(1 for r in rows if r["double_ok"]
                                       and Decimal(r["double_min_slack"]) < Decimal("0.01")),
    }
    if t["min_double_slack"] is not None:
        t["min_double_slack"] = fmt(t["min_double_slack"])
    t["predictions"] = score_x(t)
    return t


def fmt(x, places=6):
    return None if x is None else str(x.quantize(Decimal(1).scaleb(-places)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--tries", type=int, default=36)
    ap.add_argument("--wait", type=int, default=300)
    args = ap.parse_args()

    src = os.path.join(args.data_dir, "cvrplib-vrptw")
    pub = os.path.join(args.data_dir, "cvrplib-baselines-vrptwd4")
    out = os.path.join(args.out_dir, "vrptwd4x")
    for d in (src, pub, out):
        os.makedirs(d, exist_ok=True)

    with open(fetch(RAW + "results.json", os.path.join(pub, "results.json"), args.tries, args.wait),
              encoding="utf-8") as f:
        published = json.load(f)
    repaired = [r for r in published["late"] if r["run"].get("repaired")]
    log("vrptwd4/results.json: %d late BKSs, %d repaired" % (len(published["late"]), len(repaired)))

    rows = []
    for rec in repaired:
        name, i = rec["instance"], rec["id"]
        inst = load_instance(fetch("%s/instance/%s" % (BASE, i), os.path.join(src, "%s.txt" % i)))
        bks = load_routes(fetch("%s/bks/%s" % (BASE, i), os.path.join(src, "%s.sol" % i)))
        path = fetch(RAW + "sols/%s.sol" % name, os.path.join(pub, "%s.sol" % name), args.tries, args.wait)
        routes = load_routes(path)
        dbl, dim = check(routes, inst), check(routes, inst, dimacs=True)
        cost = cost_line(path)
        row = {"id": i, "instance": name, "bks_routes": len(bks), "routes": len(routes),
               "published_routes": rec["run"]["num_routes"],
               "double_ok": dbl["ok"], "double_reason": dbl["reason"],
               "double_distance": fmt(dbl.get("distance")), "double_min_slack": fmt(dbl.get("min_slack")),
               "double_late": len(dbl.get("late", [])),
               "cost_line": None if cost is None else str(cost),
               "published_double_distance": rec["run"]["double_distance"],
               "dimacs_ok": dim["ok"], "dimacs_cost": fmt(dim.get("distance"), 1),
               "published_dimacs_cost": rec["run"]["dimacs_cost"]}
        row["distance_agrees"] = bool(
            "distance" in dbl and cost is not None
            and abs(dbl["distance"] - cost) <= Decimal("0.006")
            and abs(dbl["distance"] - dec(rec["run"]["double_distance"])) <= Decimal("0.006"))
        row["dimacs_cost_agrees"] = bool(
            "distance" in dim and abs(dim["distance"] - dec(rec["run"]["dimacs_cost"])) <= Decimal("0.05"))
        rows.append(row)
        log("checked %s: routes %d (BKS %d), double ok=%s, DIMACS ok=%s" % (
            name, len(routes), len(bks), dbl["ok"], dim["ok"]))

    tally = tally_rows(rows, len(repaired))
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump({"precision_digits": getcontext().prec, "tolerance": str(TOL), "tally": tally, "rows": rows},
                  f, indent=1)
    lines = ["# Exact (50-digit) re-check of the vrptwd4 repaired solutions, both conventions", "",
             "Predictions: `%s`" % json.dumps(tally["predictions"]), "",
             "Tally: `%s`" % json.dumps(tally), "",
             "| instance | BKS routes | routes | double ok | double distance | Cost line | min slack | "
             "DIMACS ok | DIMACS cost | agrees with vrptwd4 |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        agree = r["distance_agrees"] and r["dimacs_cost_agrees"] and r["routes"] == r["published_routes"]
        lines.append("| %s | %d | %d | %s | %s | %s | %s | %s | %s | %s |" % (
            r["instance"], r["bks_routes"], r["routes"], r["double_ok"], r["double_distance"], r["cost_line"],
            r["double_min_slack"], r["dimacs_ok"], r["dimacs_cost"], "yes" if agree else "NO"))
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps(tally), flush=True)


if __name__ == "__main__":
    main()
