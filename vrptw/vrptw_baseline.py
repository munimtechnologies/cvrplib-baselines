"""Plain-PyVRP baseline on CVRPLib's VRPTW sets (Solomon, Homberger).

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.

Preparation for CVRPLib's VRPTW BKS Challenge (objective: fewest vehicles, then
distance). For each instance: download the Solomon-format file and its best
known solution (BKS) from CVRPLib, check the BKS with an independent checker
under the DIMACS convention (every arc truncated to one decimal, travel time =
distance), convert the instance to VRPLIB and solve it with PyVRP twice:
  dist: distance only, fleet as given in the file;
  lex:  minimise_fleet for half the time, then distance with that fleet.
Every PyVRP solution is re-checked by the independent checker before it counts.
Costs are kept as integer tenths.
"""
import argparse
import json
import math
import os
import time
import traceback
import urllib.request
from concurrent.futures import ProcessPoolExecutor

BASE = "https://galgos.inf.puc-rio.br/cvrplib/en/download"
UA = "CVRPLib VRPTW baseline - MV2 of Munim, Inc. (mv2@munimtech.com)"


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
            name = parts[0]
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


def dist10(a, b):
    """Euclidean distance in tenths, truncated (DIMACS convention)."""
    dx, dy = a[0] - b[0], a[1] - b[1]
    if all(isinstance(v, int) for v in (dx, dy)):
        return math.isqrt(100 * (dx * dx + dy * dy))
    return int(math.floor(10 * math.hypot(dx, dy)))


def tenths(v):
    return int(round(10 * v))


def fmt(t):
    return None if t is None else "%d.%d" % divmod(t, 10)


def parse_sol(text):
    """Return (routes, cost in tenths) from a CVRPLib solution file."""
    routes, cost = [], None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("Route #"):
            routes.append([int(x) for x in line.split(":", 1)[1].split()])
        elif line.startswith("Cost"):
            cost = tenths(float(line.split()[1]))
    return routes, cost


def write_sol(routes, cost):
    lines = ["Route #%d: %s" % (i + 1, " ".join(map(str, r)))
             for i, r in enumerate(routes)]
    lines.append("Cost %s" % fmt(cost))
    return "\n".join(lines) + "\n"


def check_tw(routes, inst):
    """Independent VRPTW check. Returns (ok, reason, cost in tenths)."""
    rows = inst["rows"]
    n = len(rows) - 1
    depot = rows[0]
    if len(routes) > inst["vehicles"]:
        return False, "%d routes > %d vehicles" % (len(routes), inst["vehicles"]), None
    seen, total = set(), 0
    for r in routes:
        if not r:
            return False, "empty route", None
        load = 0
        t = tenths(depot[3])
        prev = 0
        for c in r:
            if c in seen or not 1 <= c <= n:
                return False, "bad or repeated customer %d" % c, None
            seen.add(c)
            row = rows[c]
            load += row[2]
            d = dist10(rows[prev], row)
            total += d
            t += d
            if t > tenths(row[4]):
                return False, "late at customer %d (%s > %s)" % (c, fmt(t), row[4]), None
            t = max(t, tenths(row[3])) + tenths(row[5])
            prev = c
        d = dist10(rows[prev], depot)
        total += d
        t += d
        if t > tenths(depot[4]):
            return False, "late back at depot (%s > %s)" % (fmt(t), depot[4]), None
        if load > inst["capacity"]:
            return False, "route over capacity %s > %s" % (load, inst["capacity"]), None
    if len(seen) != n:
        return False, "%d customers not visited" % (n - len(seen)), None
    return True, "", total


def _value(attr):
    return attr() if callable(attr) else attr


def route_clients(route):
    """Solomon customer numbers (client index + 1) of a PyVRP 0.14 route."""
    return [_value(a.idx) + 1 for a in route.schedule() if _value(a.is_client)]


def run_one(task):
    import pyvrp
    from pyvrp.stop import MaxRuntime

    vrplib_path, mode, seconds, seed = task
    data = pyvrp.read(vrplib_path, round_func="dimacs")
    t0 = time.time()
    fleet = data.vehicle_type(0).num_available
    if mode == "lex":
        vt = pyvrp.minimise_fleet(data, MaxRuntime(seconds / 2.0), seed=seed)
        fleet = vt.num_available
        data = data.replace(vehicle_types=[vt])
        seconds = seconds / 2.0
    res = pyvrp.solve(data, stop=MaxRuntime(seconds), seed=seed,
                      collect_stats=False, display=False)
    best = res.best
    return {
        "mode": mode, "seed": seed, "fleet_allowed": fleet,
        "feasible": best.is_feasible(),
        "distance": best.distance(),
        "routes": [route_clients(r) for r in best.routes()],
        "iterations": res.num_iterations,
        "wall_seconds": round(time.time() - t0, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="380-435")
    ap.add_argument("--small-seconds", type=int, default=30)
    ap.add_argument("--large-seconds", type=int, default=300)
    ap.add_argument("--small-max-clients", type=int, default=200)
    ap.add_argument("--modes", default="dist,lex")
    ap.add_argument("--seed", type=int, default=20261028)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    args = ap.parse_args()

    src = os.path.join(args.data_dir, "cvrplib-vrptw")
    conv = os.path.join(args.data_dir, "vrplib")
    out = os.path.join(args.out_dir, "vrptw")
    for d in (src, conv, os.path.join(out, "improved")):
        os.makedirs(d, exist_ok=True)

    instances, tasks = {}, []
    for i in parse_ids(args.ids):
        try:
            p = fetch("%s/instance/%s" % (BASE, i), os.path.join(src, "%s.txt" % i))
            s = fetch("%s/bks/%s" % (BASE, i), os.path.join(src, "%s.sol" % i))
            with open(p, encoding="utf-8") as f:
                inst = parse_solomon(f.read())
            with open(s, encoding="utf-8") as f:
                bks_routes, bks_cost = parse_sol(f.read())
        except Exception as e:
            print("skip", i, repr(e), flush=True)
            instances[i] = {"id": i, "error": repr(e), "runs": []}
            continue
        ok, reason, ours = check_tw(bks_routes, inst)
        n = len(inst["rows"]) - 1
        instances[i] = {"id": i, "name": inst["name"], "clients": n,
                        "vehicles": inst["vehicles"], "capacity": inst["capacity"],
                        "bks_cost": fmt(bks_cost), "bks_routes": len(bks_routes),
                        "bks_check_ok": ok, "bks_check_reason": reason,
                        "bks_check_cost": fmt(ours),
                        "bks_cost_matches": bool(ok and ours == bks_cost),
                        "runs": [], "_inst": inst, "_bks": bks_cost}
        vp = os.path.join(conv, "%s.vrp" % i)
        with open(vp, "w", encoding="utf-8") as f:
            f.write(to_vrplib(inst))
        secs = args.small_seconds if n <= args.small_max_clients else args.large_seconds
        for mode in args.modes.split(","):
            tasks.append((i, (vp, mode, secs, args.seed)))

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [(i, t, pool.submit(run_one, t)) for i, t in tasks]
        for i, t, fut in futures:
            rec = instances[i]
            try:
                r = fut.result()
            except Exception:
                err = traceback.format_exc()
                print(rec["name"], t[1], "ERROR", err, flush=True)
                rec["runs"].append({"mode": t[1], "seconds": t[2], "error": err})
                continue
            ok, reason, ours = check_tw(r["routes"], rec["_inst"])
            bks = rec["_bks"]
            r["seconds"] = t[2]
            r["check_ok"], r["check_reason"], r["check_cost"] = ok, reason, fmt(ours)
            r["pyvrp_matches_check"] = bool(ok and ours == r["distance"])
            r["num_routes"] = len(r["routes"])
            r["routes_minus_bks"] = r["num_routes"] - rec["bks_routes"]
            r["gap_vs_bks_pct"] = (round(100.0 * (ours - bks) / bks, 3)
                                   if ok and bks else None)
            # vehicles first, then distance
            r["beats_bks_lex"] = bool(ok and bks is not None
                                      and (r["num_routes"], ours) < (rec["bks_routes"], bks))
            if r["beats_bks_lex"]:
                path = os.path.join(out, "improved", "%s-%s.sol" % (rec["name"], r["mode"]))
                with open(path, "w", encoding="utf-8") as f:
                    f.write(write_sol(r["routes"], ours))
            r["distance"] = fmt(r["distance"])
            del r["routes"]
            rec["runs"].append(r)
            print(rec["name"], r["mode"], r["num_routes"], fmt(ours), rec["bks_routes"],
                  rec["bks_cost"], r["gap_vs_bks_pct"], flush=True)

    for rec in instances.values():
        rec.pop("_inst", None)
        rec.pop("_bks", None)
    try:
        import pyvrp
        version = pyvrp.__version__
    except Exception:
        version = "unknown"

    recs = [r for r in instances.values() if "error" not in r]
    def runs(mode, small):
        return [(rec, x) for rec in recs for x in rec["runs"]
                if x.get("mode") == mode and "error" not in x
                and (rec["clients"] <= args.small_max_clients) == small]
    small_dist = runs("dist", True)
    small_lex = runs("lex", True)
    large_dist = runs("dist", False)
    tally = {
        "instances": len(instances), "fetched": len(recs),
        "bks_check_pass": sum(1 for r in recs if r["bks_cost_matches"]),
        "run_errors": sum(1 for rec in instances.values() for x in rec["runs"] if "error" in x),
        "pyvrp_check_disagreements": sum(1 for rec in recs for x in rec["runs"]
                                         if "error" not in x and not x["pyvrp_matches_check"]),
        "small_dist_runs": len(small_dist),
        "small_dist_at_bks": sum(1 for _, x in small_dist
                                 if x["check_ok"] and x["gap_vs_bks_pct"] is not None
                                 and x["gap_vs_bks_pct"] <= 0),
        "small_dist_max_gap_pct": max([x["gap_vs_bks_pct"] for _, x in small_dist
                                       if x["gap_vs_bks_pct"] is not None], default=None),
        "small_lex_runs": len(small_lex),
        "small_lex_routes_le_bks": sum(1 for _, x in small_lex
                                       if x["check_ok"] and x["routes_minus_bks"] <= 0),
        "large_dist_gaps_pct": {rec["name"]: x["gap_vs_bks_pct"] for rec, x in large_dist},
        "beats_bks_lex": sorted("%s-%s" % (rec["name"], x["mode"]) for rec in recs
                                for x in rec["runs"] if x.get("beats_bks_lex")),
    }
    result = {"pyvrp_version": version, "seed": args.seed, "convention": "DIMACS: arcs truncated to 0.1, time = distance",
              "small_seconds": args.small_seconds, "large_seconds": args.large_seconds,
              "tally": tally, "instances": list(instances.values())}
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)

    lines = ["# CVRPLib VRPTW baseline (plain PyVRP)", "",
             "PyVRP %s, one CPU per run, seed %d. DIMACS convention (arcs truncated to 0.1)." % (version, args.seed),
             "", "Tally: `%s`" % json.dumps(tally, ensure_ascii=False), "",
             "| instance | clients | BKS routes | BKS cost | BKS check | mode | s | routes | cost | gap % | beats BKS (lex) |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for rec in recs:
        for x in rec["runs"]:
            if "error" in x:
                lines.append("| %s | %d | %d | %s | %s | %s | %s | error | | | |" % (
                    rec["name"], rec["clients"], rec["bks_routes"], rec["bks_cost"],
                    rec["bks_cost_matches"], x["mode"], x["seconds"]))
                continue
            lines.append("| %s | %d | %d | %s | %s | %s | %s | %d | %s | %s | %s |" % (
                rec["name"], rec["clients"], rec["bks_routes"], rec["bks_cost"],
                rec["bks_cost_matches"], x["mode"], x["seconds"], x["num_routes"],
                x["check_cost"], x["gap_vs_bks_pct"], x["beats_bks_lex"]))
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps(tally), flush=True)


if __name__ == "__main__":
    main()
