"""Re-check VRPTW solutions found under CVRPLib's DIMACS convention in double precision.

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.

CVRPLib's VRPTW best known solutions (BKS) use the DIMACS convention: every arc is
truncated to one decimal and travel time = that distance. The long-standing
hierarchical records on SINTEF's TOP pages (fewest vehicles, then distance) use
double precision. A solution found under one convention can look better than a
record kept under the other without being so. This script checks every given
solution in both conventions and compares it with the SINTEF record:
  dimacs: arcs truncated to 0.1, kept as integer tenths;
  double: math.hypot, time = distance, waiting allowed, late if arrival > due + EPS.
In double precision every lateness is counted (not only the first) so the size of
the violation is visible.
"""
import argparse
import json
import math
import os
import time
import urllib.request

BASE = "https://galgos.inf.puc-rio.br/cvrplib/en/download"
UA = "CVRPLib VRPTW convention check - MV2 of Munim, Inc. (mv2@munimtech.com)"
EPS = 1e-6

# SINTEF TOP hierarchical records (vehicles, distance), double precision, read 2026-10-29 from
# https://www.sintef.no/projectweb/top/vrptw/100-customers/ and .../1000-customers/
SINTEF = {
    "C101": (10, 828.94), "C102": (10, 828.94), "C103": (10, 828.06), "C104": (10, 824.78),
    "C105": (10, 828.94), "C106": (10, 828.94), "C107": (10, 828.94), "C108": (10, 828.94),
    "C109": (10, 828.94),
    "C201": (3, 591.56), "C202": (3, 591.56), "C203": (3, 591.17), "C204": (3, 590.60),
    "C205": (3, 588.88), "C206": (3, 588.49), "C207": (3, 588.29), "C208": (3, 588.32),
    "R101": (19, 1650.80), "R102": (17, 1486.12), "R103": (13, 1292.68), "R104": (9, 1007.31),
    "R105": (14, 1377.11), "R106": (12, 1252.03), "R107": (10, 1104.66), "R108": (9, 960.88),
    "R109": (11, 1194.73), "R110": (10, 1118.84), "R111": (10, 1096.73), "R112": (9, 982.14),
    "R201": (4, 1252.37), "R202": (3, 1191.70), "R203": (3, 939.50), "R204": (2, 825.52),
    "R205": (3, 994.43), "R206": (3, 906.14), "R207": (2, 890.61), "R208": (2, 726.82),
    "R209": (3, 909.16), "R210": (3, 939.37), "R211": (2, 885.71),
    "RC101": (14, 1696.95), "RC102": (12, 1554.75), "RC103": (11, 1261.67), "RC104": (10, 1135.48),
    "RC105": (13, 1629.44), "RC106": (11, 1424.73), "RC107": (11, 1230.48), "RC108": (10, 1139.82),
    "RC201": (4, 1406.94), "RC202": (3, 1365.65), "RC203": (3, 1049.62), "RC204": (3, 798.46),
    "RC205": (4, 1297.65), "RC206": (3, 1146.32), "RC207": (3, 1061.14), "RC208": (3, 828.14),
    "C1_10_1": (100, 42478.95), "C2_10_1": (30, 16879.24), "R1_10_1": (100, 53380.18),
    "R2_10_1": (19, 42182.57), "RC1_10_1": (90, 45830.62), "RC2_10_1": (20, 30276.27),
}


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
    """'380-382,676' -> ['380', '381', '382', '676']"""
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


def sol_instance(filename):
    """'R1_10_1-lex.sol' -> 'R1_10_1'"""
    return os.path.basename(filename).rsplit("-", 1)[0].upper()


def dist10(a, b):
    """Euclidean distance in tenths, truncated (DIMACS convention)."""
    dx, dy = a[0] - b[0], a[1] - b[1]
    if all(isinstance(v, int) for v in (dx, dy)):
        return math.isqrt(100 * (dx * dx + dy * dy))
    return int(math.floor(10 * math.hypot(dx, dy)))


def _structure(routes, inst):
    """Coverage, repeats and capacity; returns a reason or ''."""
    n = len(inst["rows"]) - 1
    seen = set()
    for r in routes:
        if not r:
            return "empty route"
        load = 0
        for c in r:
            if c in seen or not 1 <= c <= n:
                return "bad or repeated customer %d" % c
            seen.add(c)
            load += inst["rows"][c][2]
        if load > inst["capacity"]:
            return "route over capacity %s > %s" % (load, inst["capacity"])
    if len(seen) != n:
        return "%d customers not visited" % (n - len(seen))
    return ""


def check_dimacs(routes, inst):
    """(ok, reason, cost in tenths). Stops at the first violation."""
    reason = _structure(routes, inst)
    if reason:
        return False, reason, None
    rows = inst["rows"]
    depot = rows[0]
    total = 0
    for r in routes:
        t, prev = 10 * depot[3], 0
        for c in r:
            d = dist10(rows[prev], rows[c])
            total += d
            t += d
            if t > 10 * rows[c][4]:
                return False, "late at customer %d" % c, None
            t = max(t, 10 * rows[c][3]) + 10 * rows[c][5]
            prev = c
        d = dist10(rows[prev], depot)
        total += d
        t += d
        if t > 10 * depot[4]:
            return False, "late back at depot", None
    return True, "", total


def check_double(routes, inst):
    """Double precision. Returns dict: ok, reason, distance, late (count incl. depot returns),
    max_late, late_routes. Distance is reported even when time windows fail."""
    reason = _structure(routes, inst)
    if reason:
        return {"ok": False, "reason": reason, "distance": None, "late": None,
                "max_late": None, "late_routes": None}
    rows = inst["rows"]
    depot = rows[0]
    total, late, max_late, late_routes = 0.0, 0, 0.0, 0
    for r in routes:
        t, prev, route_late = float(depot[3]), 0, False
        for c in r:
            d = math.hypot(rows[prev][0] - rows[c][0], rows[prev][1] - rows[c][1])
            total += d
            t += d
            over = t - rows[c][4]
            if over > EPS:
                late += 1
                route_late = True
                max_late = max(max_late, over)
            t = max(t, float(rows[c][3])) + rows[c][5]
            prev = c
        d = math.hypot(rows[prev][0] - depot[0], rows[prev][1] - depot[1])
        total += d
        t += d
        over = t - depot[4]
        if over > EPS:
            late += 1
            route_late = True
            max_late = max(max_late, over)
        late_routes += route_late
    ok = late == 0
    return {"ok": ok, "reason": "" if ok else "%d late arrivals" % late,
            "distance": total, "late": late, "max_late": round(max_late, 4),
            "late_routes": late_routes}


def versus_sintef(num_routes, distance, record):
    """'better' / 'equal' / 'worse' in the hierarchical order, distance rounded to 2 decimals."""
    veh, rec = record
    ours = round(distance, 2)
    if num_routes != veh:
        return "better" if num_routes < veh else "worse"
    if abs(ours - rec) < 0.005:
        return "equal"
    return "better" if ours < rec else "worse"


def evaluate(source, routes, file_cost, inst):
    ok_d, reason_d, cost_d = check_dimacs(routes, inst)
    dbl = check_double(routes, inst)
    rec = SINTEF.get(inst["name"])
    row = {"instance": inst["name"], "source": source, "routes": len(routes),
           "file_cost": file_cost,
           "dimacs_ok": ok_d, "dimacs_reason": reason_d,
           "dimacs_cost": None if cost_d is None else cost_d / 10.0,
           "dimacs_matches_file": bool(ok_d and file_cost is not None
                                       and cost_d == int(round(10 * file_cost))),
           "double_ok": dbl["ok"], "double_reason": dbl["reason"],
           "double_distance": None if dbl["distance"] is None else round(dbl["distance"], 2),
           "double_late": dbl["late"], "double_max_late": dbl["max_late"],
           "double_late_routes": dbl["late_routes"],
           "sintef_vehicles": rec[0] if rec else None,
           "sintef_distance": rec[1] if rec else None}
    row["dimacs_vs_sintef"] = (versus_sintef(len(routes), cost_d / 10.0, rec)
                               if ok_d and rec else None)
    row["double_vs_sintef"] = (versus_sintef(len(routes), dbl["distance"], rec)
                               if dbl["ok"] and rec else None)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="380-435,676,686,696,706,716,726")
    ap.add_argument("--sols", default="sols")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    args = ap.parse_args()

    src = os.path.join(args.data_dir, "cvrplib-vrptw")
    out = os.path.join(args.out_dir, "vrptwd")
    os.makedirs(src, exist_ok=True)
    os.makedirs(out, exist_ok=True)

    insts, rows = {}, []
    for i in parse_ids(args.ids):
        p = fetch("%s/instance/%s" % (BASE, i), os.path.join(src, "%s.txt" % i))
        s = fetch("%s/bks/%s" % (BASE, i), os.path.join(src, "%s.sol" % i))
        with open(p, encoding="utf-8") as f:
            inst = parse_solomon(f.read())
        with open(s, encoding="utf-8") as f:
            routes, cost = parse_sol(f.read())
        inst["id"] = i
        insts[inst["name"]] = inst
        rows.append(evaluate("cvrplib-bks", routes, cost, inst))

    for fn in sorted(os.listdir(args.sols)):
        if not fn.endswith(".sol"):
            continue
        name = sol_instance(fn)
        if name not in insts:
            print("no instance for", fn, flush=True)
            continue
        with open(os.path.join(args.sols, fn), encoding="utf-8") as f:
            routes, cost = parse_sol(f.read())
        rows.append(evaluate("pyvrp-" + fn[:-4].rsplit("-", 1)[1], routes, cost, insts[name]))

    bks = [r for r in rows if r["source"] == "cvrplib-bks"]
    py = [r for r in rows if r["source"] != "cvrplib-bks"]
    solomon = [r for r in bks if "_" not in r["instance"]]
    py_solomon = [r for r in py if "_" not in r["instance"]]
    looks_better = [r for r in py_solomon if r["dimacs_vs_sintef"] == "better"]
    tally = {
        "bks_rows": len(bks), "pyvrp_rows": len(py),
        "dimacs_hygiene_fail": [r["instance"] + "/" + r["source"] for r in rows
                                if not r["dimacs_matches_file"]],
        "solomon_bks_double_feasible": sum(1 for r in solomon if r["double_ok"]),
        "solomon_bks_double_infeasible": [r["instance"] for r in solomon if not r["double_ok"]],
        "pyvrp_solomon_looks_better_dimacs": [r["instance"] for r in looks_better],
        "pyvrp_solomon_looks_better_double_feasible": sum(1 for r in looks_better if r["double_ok"]),
        "pyvrp_solomon_double_vs_sintef": {r["instance"]: r["double_vs_sintef"] for r in looks_better},
        "pyvrp_double_better_than_sintef": [r["instance"] for r in py if r["double_vs_sintef"] == "better"],
        "bks_double_better_than_sintef": [r["instance"] for r in bks if r["double_vs_sintef"] == "better"],
        "homberger": {r["instance"] + "/" + r["source"]: [r["routes"], r["double_ok"], r["double_late"],
                                                          r["double_late_routes"]]
                      for r in rows if "_" in r["instance"]},
    }
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump({"eps": EPS, "tally": tally, "rows": rows}, f, indent=1)

    lines = ["# DIMACS vs double precision on CVRPLib VRPTW solutions", "",
             "Tally: `%s`" % json.dumps(tally, ensure_ascii=False), "",
             "| instance | source | routes | DIMACS cost | double ok | double distance | late (routes) | max late | SINTEF | vs SINTEF (DIMACS) | vs SINTEF (double) |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append("| %s | %s | %d | %s | %s | %s | %s (%s) | %s | %s / %s | %s | %s |" % (
            r["instance"], r["source"], r["routes"], r["dimacs_cost"], r["double_ok"],
            r["double_distance"], r["double_late"], r["double_late_routes"], r["double_max_late"],
            r["sintef_vehicles"], r["sintef_distance"], r["dimacs_vs_sintef"], r["double_vs_sintef"]))
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps(tally), flush=True)


if __name__ == "__main__":
    main()
