"""Fewest vehicles first, in double precision: plain PyVRP against SINTEF's 1,000-customer VRPTW records.

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.

CVRPLib's VRPTW BKS Challenge ranks solutions by vehicles first, then distance, the same order as the
long-standing hierarchical records on SINTEF's TOP pages, which are kept in double precision (no truncation,
travel time = distance). CVRPLib's own VRPTW BKSs minimise distance only, so their route counts say nothing
about the vehicle objective. This script asks, for all 60 Gehring-Homberger instances with 1,000 customers, how
close plain PyVRP 0.14.1 on one CPU gets to SINTEF's vehicle count: pyvrp.minimise_fleet for half the budget, then
pyvrp.solve with that fleet for the other half, on a "safe" integer copy of the instance (every number x1,000,
rounded UP, as in vrptwd4/), so anything on time in the copy is on time in double precision. Every result is
re-checked by an independent double-precision checker before it counts. Predictions: expectations.md, scored by
score_l() below.
"""
import argparse
import json
import math
import os
import re
import statistics
import time
import traceback
import urllib.request
from concurrent.futures import ProcessPoolExecutor

BASE = "https://galgos.inf.puc-rio.br/cvrplib/en/download"
SINTEF_URL = "https://www.sintef.no/projectweb/top/vrptw/1000-customers/"
UA = "CVRPLib VRPTW fleet baseline - MV2 of Munim, Inc. (mv2@munimtech.com)"
SCALE = 1000
EPS = 1e-6
EXPECTED = 60
FAMILIES = ("C1", "C2", "R1", "R2", "RC1", "RC2")
T0 = time.time()

# SINTEF TOP hierarchical records (vehicles, distance), double precision, read 2026-10-30 from SINTEF_URL.
_RECORDS = {
    "C1": [(100, 42478.95), (90, 42222.96), (90, 40101.36), (90, 39468.60), (100, 42469.18),
           (99, 43830.21), (97, 43341.77), (92, 42629.91), (90, 40318.03), (90, 39852.44)],
    "C2": [(30, 16879.24), (29, 17126.39), (28, 16829.47), (28, 15607.48), (30, 16561.29),
           (29, 16863.71), (29, 17602.84), (28, 16512.43), (28, 17809.34), (28, 15937.45)],
    "R1": [(100, 53380.18), (91, 48232.67), (91, 44689.19), (91, 42463.74), (91, 50442.31),
           (91, 46928.44), (91, 43969.48), (91, 42288.04), (91, 49186.22), (91, 47403.83)],
    "R2": [(19, 42182.57), (19, 33411.21), (19, 24916.88), (19, 17851.96), (19, 36216.05),
           (19, 29978.02), (19, 23219.61), (19, 17442.29), (19, 32995.71), (19, 30207.49)],
    "RC1": [(90, 45830.62), (90, 43718.84), (90, 42145.32), (90, 41391.18), (90, 45069.37),
            (90, 44936.35), (90, 44456.67), (90, 43956.91), (90, 43897.21), (90, 43551.69)],
    "RC2": [(20, 30276.27), (18, 26104.09), (18, 19911.48), (18, 15693.28), (18, 27067.04),
            (18, 26741.27), (18, 24999.66), (18, 23595.33), (18, 22919.42), (18, 21834.94)],
}
SINTEF = {"%s_10_%d" % (fam, k + 1): rec for fam, recs in _RECORDS.items() for k, rec in enumerate(recs)}


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def fetch(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        body = r.read()
    with open(path, "wb") as f:
        f.write(body)
    time.sleep(2)
    return path


def parse_ids(spec):
    """'676-678,700' -> ['676', '677', '678', '700']"""
    out = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            out.extend(str(i) for i in range(int(a), int(b) + 1))
        elif part:
            out.append(part)
    return out


def _num(tok):
    v = float(tok)
    return int(v) if v.is_integer() else v


def parse_solomon(text):
    """Return {name, vehicles, capacity, rows}; rows[i] = (x, y, demand, ready, due, service)."""
    name, vehicles, capacity, rows = None, None, None, {}
    for raw in text.splitlines():
        parts = raw.split()
        if not parts:
            continue
        if name is None:
            name = parts[0].upper()
            continue
        try:
            nums = [_num(p) for p in parts]
        except ValueError:
            continue
        if len(nums) == 2 and vehicles is None:
            vehicles, capacity = nums
        elif len(nums) == 7:
            rows[int(nums[0])] = tuple(nums[1:])
    if vehicles is None or not rows:
        raise ValueError("not a Solomon-format file")
    if sorted(rows) != list(range(len(rows))):
        raise ValueError("customer numbers are not 0..n")
    return {"name": name, "vehicles": vehicles, "capacity": capacity,
            "rows": [rows[i] for i in range(len(rows))]}


def parse_sol(text):
    """Return (routes, cost as float or None) from a CVRPLib solution file."""
    routes, cost = [], None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("Route #"):
            routes.append([int(x) for x in line.split(":", 1)[1].split()])
        elif line.startswith("Cost"):
            cost = float(line.split()[1])
    return routes, cost


def parse_sintef(html):
    """{name: (vehicles, distance)} from the SINTEF 1,000-customer page, to check the table above."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;|\s+", " ", text)
    out = {}
    for m in re.finditer(r"\b((?:rc|c|r)[12]_10_\d{1,2})\s+(?:[a-z]\s+)?(\d{1,3})\s+(\d+\.\d+)", text, re.I):
        out.setdefault(m.group(1).upper(), (int(m.group(2)), float(m.group(3))))
    return out


def family(name):
    """'RC1_10_1' -> 'RC1'."""
    return name.split("_")[0]


def ceil_scaled(vals):
    """PyVRP round_func: x 1,000, rounded up, so scaled travel times never undercut the exact ones."""
    import numpy as np
    return np.ceil(SCALE * np.asarray(vals, dtype=np.float64)).astype(np.int64)


def to_vrplib(inst):
    """VRPLIB text for pyvrp.read; Solomon customer i is VRPLIB node i + 1."""
    rows = inst["rows"]
    lines = ["NAME : %s" % inst["name"], "TYPE : VRPTW",
             "DIMENSION : %d" % len(rows), "VEHICLES : %d" % inst["vehicles"],
             "CAPACITY : %s" % inst["capacity"], "EDGE_WEIGHT_TYPE : EUC_2D",
             "NODE_COORD_SECTION"]
    lines += ["%d %s %s" % (i + 1, r[0], r[1]) for i, r in enumerate(rows)]
    lines.append("DEMAND_SECTION")
    lines += ["%d %s" % (i + 1, r[2]) for i, r in enumerate(rows)]
    lines.append("TIME_WINDOW_SECTION")
    lines += ["%d %s %s" % (i + 1, r[3], r[4]) for i, r in enumerate(rows)]
    lines.append("SERVICE_TIME_SECTION")
    lines += ["%d %s" % (i + 1, r[5]) for i, r in enumerate(rows)]
    lines += ["DEPOT_SECTION", "1", "-1", "EOF"]
    return "\n".join(lines) + "\n"


def write_sol(routes, distance):
    lines = ["Route #%d: %s" % (i + 1, " ".join(map(str, r))) for i, r in enumerate(routes)]
    lines.append("Cost %.2f" % distance)
    return "\n".join(lines) + "\n"


def check_double(routes, inst):
    """Independent double-precision check: time = distance, waiting allowed, late if arrival > due + EPS.
    Returns ok, reason, distance (summed even when late), late (count, depot returns included)."""
    rows = inst["rows"]
    n = len(rows) - 1
    seen = set()
    for r in routes:
        if not r:
            return {"ok": False, "reason": "empty route", "distance": None, "late": None}
        if sum(rows[c][2] for c in r if 1 <= c <= n) > inst["capacity"]:
            return {"ok": False, "reason": "over capacity", "distance": None, "late": None}
        for c in r:
            if c in seen or not 1 <= c <= n:
                return {"ok": False, "reason": "bad or repeated customer %d" % c, "distance": None, "late": None}
            seen.add(c)
    if len(seen) != n:
        return {"ok": False, "reason": "%d customers not visited" % (n - len(seen)), "distance": None,
                "late": None}
    total, late = 0.0, 0
    for r in routes:
        t, prev = float(rows[0][3]), 0
        for c in list(r) + [0]:
            d = math.hypot(rows[prev][0] - rows[c][0], rows[prev][1] - rows[c][1])
            total += d
            t += d
            late += t - rows[c][4] > EPS
            if c:
                t = max(t, float(rows[c][3])) + rows[c][5]
            prev = c
    return {"ok": late == 0, "reason": "" if not late else "%d late arrivals" % late, "distance": total,
            "late": late}


def versus_sintef(vehicles, distance, record):
    """'better' / 'equal' / 'worse' in the hierarchical order, distance rounded to 2 decimals."""
    veh, rec = record
    if vehicles != veh:
        return "better" if vehicles < veh else "worse"
    ours = round(distance, 2)
    if abs(ours - rec) < 0.005:
        return "equal"
    return "better" if ours < rec else "worse"


def _value(attr):
    return attr() if callable(attr) else attr


def route_clients(route):
    """Solomon customer numbers (client index + 1) of a PyVRP 0.14 route."""
    return [_value(a.idx) + 1 for a in route.schedule() if _value(a.is_client)]


def run_one(task):
    import pyvrp
    from pyvrp.stop import MaxRuntime

    vrplib_path, seconds, seed = task
    data = pyvrp.read(vrplib_path, round_func=ceil_scaled)
    t0 = time.time()
    vt = pyvrp.minimise_fleet(data, MaxRuntime(seconds / 2.0), seed=seed)
    fleet_seconds = round(time.time() - t0, 1)
    data = data.replace(vehicle_types=[vt])
    res = pyvrp.solve(data, stop=MaxRuntime(seconds / 2.0), seed=seed, collect_stats=False, display=False)
    best = res.best
    return {"seconds": seconds, "seed": seed, "fleet": vt.num_available, "fleet_seconds": fleet_seconds,
            "feasible": best.is_feasible(), "scaled_distance": best.distance(),
            "routes": [route_clients(r) for r in best.routes()],
            "iterations": res.num_iterations, "wall_seconds": round(time.time() - t0, 1)}


def assess(rec, r, inst):
    """Independent check of one PyVRP result; adds the fields the tally reads."""
    dbl = check_double(r["routes"], inst)
    n = len(r["routes"])
    veh, dist = rec["sintef"]
    r.update({"vehicles": n, "double_ok": dbl["ok"], "double_reason": dbl["reason"],
              "double_distance": None if dbl["distance"] is None else round(dbl["distance"], 2),
              "pyvrp_agrees": dbl["ok"] or not r["feasible"],
              "structure_ok": dbl["late"] is not None})
    r["vehicles_over_sintef"] = n - veh if dbl["ok"] else None
    r["distance_over_sintef_pct"] = (round(100.0 * (dbl["distance"] - dist) / dist, 3)
                                     if dbl["ok"] and n == veh else None)
    r["vs_sintef"] = versus_sintef(n, dbl["distance"], rec["sintef"]) if dbl["ok"] else None
    return r


def score_l(t):
    """Verdicts for L0-L6 (expectations.md) from the tally."""
    def verdict(ok):
        return "untestable" if ok is None else ("held" if ok else "did not hold")
    med = t["median_distance_over_sintef_pct"]
    return {
        "L0": verdict(t["instances"] == EXPECTED and not t["unknown_names"] and not t["run_errors"]
                      and not t["structure_fail"] and not t["pyvrp_disagreements"]),
        "L1": verdict(t["double_ok"] == EXPECTED),
        "L2": verdict(not t["beats_sintef"]),
        "L3": verdict(t["match_vehicles"] >= 30),
        "L4": verdict(t["match_by_family"].get("R2", 0) + t["match_by_family"].get("RC2", 0) >= 15),
        "L5": verdict(t["match_by_family"].get("R1", 0) + t["match_by_family"].get("RC1", 0) <= 6),
        "L6": verdict(None if med is None else med <= 3.0),
    }


def tally_recs(recs):
    runs = [r for r in recs if r.get("run")]
    ok = [r for r in runs if r["run"]["double_ok"]]
    match = [r for r in ok if r["run"]["vehicles_over_sintef"] == 0]
    gaps = [r["run"]["distance_over_sintef_pct"] for r in match]
    t = {
        "instances": len(recs),
        "unknown_names": [r["instance"] for r in recs if r["instance"] not in SINTEF],
        "run_errors": [r["instance"] for r in recs if r.get("error")],
        "structure_fail": [r["instance"] for r in runs if not r["run"]["structure_ok"]],
        "pyvrp_disagreements": [r["instance"] for r in runs if not r["run"]["pyvrp_agrees"]],
        "pyvrp_infeasible": [r["instance"] for r in runs if not r["run"]["feasible"]],
        "double_ok": len(ok),
        "match_vehicles": len(match),
        "match_by_family": {f: sum(1 for r in match if r["family"] == f) for f in FAMILIES},
        "vehicles_over_by_family": {f: sorted(r["run"]["vehicles_over_sintef"] for r in ok if r["family"] == f)
                                    for f in FAMILIES},
        "total_vehicles": sum(r["run"]["vehicles"] for r in ok),
        "total_sintef_vehicles": sum(r["sintef"][0] for r in ok),
        "beats_sintef": [r["instance"] for r in ok if r["run"]["vs_sintef"] == "better"],
        "equals_sintef": [r["instance"] for r in ok if r["run"]["vs_sintef"] == "equal"],
        "median_distance_over_sintef_pct": round(statistics.median(gaps), 3) if gaps else None,
        "max_distance_over_sintef_pct": max(gaps) if gaps else None,
        "fewer_routes_than_cvrplib_bks": [r["instance"] for r in ok if r["run"]["vehicles"] < r["bks_routes"]],
    }
    t["predictions"] = score_l(t)
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="676-735")
    ap.add_argument("--seconds", type=int, default=600)
    ap.add_argument("--seed", type=int, default=20261030)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    args = ap.parse_args()

    src = os.path.join(args.data_dir, "cvrplib-vrptw")
    conv = os.path.join(args.data_dir, "vrplib-fleet-double")
    out = os.path.join(args.out_dir, "vrptwl")
    sols = os.path.join(out, "sols")
    for d in (src, conv, sols):
        os.makedirs(d, exist_ok=True)
    log("cached files in data volume: %d" % len(os.listdir(src)))

    try:
        req = urllib.request.Request(SINTEF_URL, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as r:
            page = parse_sintef(r.read().decode("utf-8", "replace"))
        page_check = {"rows_read": len(page),
                      "mismatches": {k: [list(SINTEF[k]), list(v)] for k, v in sorted(page.items())
                                     if k in SINTEF and (v[0] != SINTEF[k][0] or abs(v[1] - SINTEF[k][1]) > 0.005)},
                      "missing": sorted(k for k in SINTEF if k not in page)}
    except Exception as e:
        page_check = {"error": repr(e)}
    log("SINTEF page check: %s" % json.dumps(page_check))

    recs, insts, tasks = [], {}, []
    for i in parse_ids(args.ids):
        p = fetch("%s/instance/%s" % (BASE, i), os.path.join(src, "%s.txt" % i))
        s = fetch("%s/bks/%s" % (BASE, i), os.path.join(src, "%s.sol" % i))
        with open(p, encoding="utf-8") as f:
            inst = parse_solomon(f.read())
        with open(s, encoding="utf-8") as f:
            bks_routes, bks_cost = parse_sol(f.read())
        name = inst["name"]
        rec = {"id": i, "instance": name, "family": family(name), "customers": len(inst["rows"]) - 1,
               "file_vehicles": inst["vehicles"], "bks_routes": len(bks_routes), "bks_dimacs_cost": bks_cost,
               "sintef": list(SINTEF[name]) if name in SINTEF else None}
        recs.append(rec)
        insts[i] = inst
        if rec["sintef"]:
            vp = os.path.join(conv, "%s.vrp" % name)
            with open(vp, "w", encoding="utf-8") as f:
                f.write(to_vrplib(inst))
            tasks.append((rec, (vp, args.seconds, args.seed)))
    log("instances read: %d; runs: %d" % (len(recs), len(tasks)))

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [(rec, pool.submit(run_one, t)) for rec, t in tasks]
        for rec, fut in futures:
            try:
                r = fut.result()
            except Exception:
                rec["error"] = traceback.format_exc()
                log("%s ERROR %s" % (rec["instance"], rec["error"]))
                continue
            r = assess(rec, r, insts[rec["id"]])
            if r["double_ok"]:
                with open(os.path.join(sols, "%s.sol" % rec["instance"]), "w", encoding="utf-8") as f:
                    f.write(write_sol(r["routes"], r["double_distance"]))
            del r["routes"]
            rec["run"] = r
            log("%s: SINTEF %d / %s; PyVRP fleet %d, %d routes, double_ok=%s, %s (%s%%), %s, %d it" % (
                rec["instance"], rec["sintef"][0], rec["sintef"][1], r["fleet"], r["vehicles"], r["double_ok"],
                r["double_distance"], r["distance_over_sintef_pct"], r["vs_sintef"], r["iterations"]))

    tally = tally_recs(recs)
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump({"scale": SCALE, "rounding": "ceil", "eps": EPS, "seed": args.seed, "seconds": args.seconds,
                   "pyvrp": "0.14.1 (pinned)", "sintef_url": SINTEF_URL, "sintef_page_check": page_check,
                   "tally": tally, "instances": recs}, f, indent=1)
    lines = ["# Fewest vehicles first, double precision: PyVRP vs SINTEF's 1,000-customer records", "",
             "PyVRP 0.14.1, one CPU per instance, %d s (minimise_fleet half, solve half), seed %d, travel times "
             "x1,000 rounded up. Every result re-checked in double precision." % (args.seconds, args.seed), "",
             "Predictions: `%s`" % json.dumps(tally["predictions"]), "",
             "Tally: `%s`" % json.dumps({k: v for k, v in tally.items() if k != "predictions"}), "",
             "| id | instance | CVRPLib BKS routes | SINTEF vehicles | SINTEF distance | PyVRP vehicles | double ok "
             "| double distance | vehicles over | distance over % | vs SINTEF | iterations |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in recs:
        x = r.get("run")
        sv, sd = r["sintef"] or (None, None)
        if not x:
            lines.append("| %s | %s | %d | %s | %s | error | | | | | | |" % (
                r["id"], r["instance"], r["bks_routes"], sv, sd))
            continue
        lines.append("| %s | %s | %d | %s | %s | %d | %s | %s | %s | %s | %s | %d |" % (
            r["id"], r["instance"], r["bks_routes"], sv, sd, x["vehicles"], x["double_ok"], x["double_distance"],
            x["vehicles_over_sintef"], x["distance_over_sintef_pct"], x["vs_sintef"], x["iterations"]))
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps(tally), flush=True)


if __name__ == "__main__":
    main()
