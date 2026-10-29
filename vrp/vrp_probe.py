"""Warm-start probe on CVRPLib XL instances.

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.

For each instance: download the .vrp file and its current best known solution
(BKS) from CVRPLib, check the BKS with an independent cost function, then run
PyVRP once from the BKS (warm) and once from scratch (cold) and report the
costs. A solution better than the BKS is written in CVRPLib format and checked
again with the independent cost function before it is kept.

v2: PyVRP 0.14.1 routes are lists of scheduled activities (depots included),
and Solution(data, list[list[int]]) takes 0-based client indices. CVRPLib
solution ids are 1-based (client index + 1), so convert both ways.
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
UA = "CVRPLib probe - MV2 of Munim, Inc. (mv2@munimtech.com)"


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


def parse_vrp(text):
    """Return (name, capacity, coords, demands); index 0 is the depot (file node 1)."""
    name, cap, dim, section = None, None, None, None
    coords, demands, depots = {}, {}, []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line == "EOF":
            continue
        if line.endswith("_SECTION"):
            section = line
            continue
        if ":" in line:
            key, val = (s.strip() for s in line.split(":", 1))
            if key == "NAME":
                name = val
            elif key == "DIMENSION":
                dim = int(val)
            elif key == "CAPACITY":
                cap = int(val)
            elif key == "EDGE_WEIGHT_TYPE" and val != "EUC_2D":
                raise ValueError("unsupported EDGE_WEIGHT_TYPE " + val)
            section = None
            continue
        parts = line.split()
        if section == "NODE_COORD_SECTION":
            coords[int(parts[0]) - 1] = (float(parts[1]), float(parts[2]))
        elif section == "DEMAND_SECTION":
            demands[int(parts[0]) - 1] = int(parts[1])
        elif section == "DEPOT_SECTION":
            if int(parts[0]) != -1:
                depots.append(int(parts[0]))
    if depots != [1]:
        raise ValueError("expected a single depot at node 1, got %r" % depots)
    if dim is None or len(coords) != dim or len(demands) != dim:
        raise ValueError("DIMENSION does not match the sections")
    return name, cap, coords, demands


def parse_sol(text):
    """Return (routes, cost) from a CVRPLib solution file."""
    routes, cost = [], None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("Route #"):
            ids = line.split(":", 1)[1].split()
            routes.append([int(x) for x in ids])
        elif line.startswith("Cost"):
            cost = float(line.split()[1])
    return routes, cost


def write_sol(routes, cost):
    lines = ["Route #%d: %s" % (i + 1, " ".join(map(str, r)))
             for i, r in enumerate(routes)]
    lines.append("Cost %d" % cost)
    return "\n".join(lines) + "\n"


def dist(a, b):
    # TSPLIB nint: Euclidean distance rounded to the nearest integer
    return int(math.floor(math.hypot(a[0] - b[0], a[1] - b[1]) + 0.5))


def check(routes, cap, coords, demands):
    """Independent feasibility and cost check. Returns (ok, reason, cost)."""
    seen, total = set(), 0
    for r in routes:
        if not r:
            return False, "empty route", None
        load = sum(demands[c] for c in r)
        if load > cap:
            return False, "route over capacity %d > %d" % (load, cap), None
        prev = 0
        for c in r:
            if c in seen or c == 0 or c not in coords:
                return False, "bad or repeated client %d" % c, None
            seen.add(c)
            total += dist(coords[prev], coords[c])
            prev = c
        total += dist(coords[prev], coords[0])
    if seen != set(range(1, len(coords))):
        return False, "%d clients not visited" % (len(coords) - 1 - len(seen)), None
    return True, "", total


def _value(attr):
    return attr() if callable(attr) else attr


def route_clients(route):
    """CVRPLib ids (client index + 1) of a PyVRP 0.14 route, depots dropped."""
    return [_value(a.idx) + 1 for a in route.schedule() if _value(a.is_client)]


def to_pyvrp_routes(routes):
    """CVRPLib ids -> 0-based PyVRP client indices."""
    return [[c - 1 for c in r] for r in routes]


def run_one(task):
    import pyvrp
    from pyvrp.stop import MaxRuntime

    vrp_path, sol_path, mode, seconds, seed = task
    data = pyvrp.read(vrp_path, round_func="round")
    with open(sol_path, encoding="utf-8") as f:
        bks_routes, bks_cost = parse_sol(f.read())
    init, init_cost = None, None
    if mode == "warm":
        init = pyvrp.Solution(data, to_pyvrp_routes(bks_routes))
        init_cost = init.distance()
    t0 = time.time()
    res = pyvrp.solve(data, stop=MaxRuntime(seconds), seed=seed,
                      collect_stats=False, display=False, initial_solution=init)
    best = res.best
    return {
        "mode": mode, "seconds": seconds, "seed": seed,
        "pyvrp_init_distance": init_cost,
        "feasible": best.is_feasible(),
        "distance": best.distance(),
        "routes": [route_clients(r) for r in best.routes()],
        "iterations": res.num_iterations,
        "wall_seconds": round(time.time() - t0, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="280,281,282")
    ap.add_argument("--warm-seconds", type=int, default=1800)
    ap.add_argument("--cold-seconds", type=int, default=900)
    ap.add_argument("--seed", type=int, default=20261028)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    args = ap.parse_args()

    src = os.path.join(args.data_dir, "cvrplib")
    out = os.path.join(args.out_dir, "vrp")
    os.makedirs(src, exist_ok=True)
    os.makedirs(os.path.join(out, "improved"), exist_ok=True)

    instances, tasks = {}, []
    for i in args.ids.split(","):
        vrp_path = fetch("%s/instance/%s" % (BASE, i), os.path.join(src, "%s.vrp" % i))
        sol_path = fetch("%s/bks/%s" % (BASE, i), os.path.join(src, "%s.sol" % i))
        with open(vrp_path, encoding="utf-8") as f:
            name, cap, coords, demands = parse_vrp(f.read())
        with open(sol_path, encoding="utf-8") as f:
            routes, cost = parse_sol(f.read())
        ok, reason, ours = check(routes, cap, coords, demands)
        instances[i] = {"name": name, "clients": len(coords) - 1, "capacity": cap,
                        "bks_cost": cost, "bks_routes": len(routes),
                        "bks_check_ok": ok, "bks_check_reason": reason,
                        "bks_check_cost": ours, "runs": []}
        if not ok or ours != cost:
            raise SystemExit("BKS check failed for %s: %s %r vs %r" % (name, reason, ours, cost))
        instances[i]["_model"] = (cap, coords, demands)
        tasks.append((i, (vrp_path, sol_path, "warm", args.warm_seconds, args.seed)))
        tasks.append((i, (vrp_path, sol_path, "cold", args.cold_seconds, args.seed)))

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [(i, t, pool.submit(run_one, t)) for i, t in tasks]
        for i, t, fut in futures:
            inst = instances[i]
            try:
                r = fut.result()
            except Exception:
                err = traceback.format_exc()
                print(inst["name"], t[2], "ERROR", err, flush=True)
                inst["runs"].append({"mode": t[2], "seconds": t[3], "error": err,
                                     "check_cost": None, "gap_vs_bks_pct": None,
                                     "num_routes": 0, "improves_bks": False})
                continue
            cap, coords, demands = inst["_model"]
            ok, reason, ours = check(r["routes"], cap, coords, demands)
            r["check_ok"], r["check_reason"], r["check_cost"] = ok, reason, ours
            r["pyvrp_matches_check"] = bool(ok and ours == r["distance"])
            r["gap_vs_bks_pct"] = (round(100.0 * (ours - inst["bks_cost"]) / inst["bks_cost"], 4)
                                   if ok else None)
            r["improves_bks"] = bool(ok and ours < inst["bks_cost"])
            if r["improves_bks"]:
                path = os.path.join(out, "improved", "%s-%s.sol" % (inst["name"], r["mode"]))
                with open(path, "w", encoding="utf-8") as f:
                    f.write(write_sol(r["routes"], ours))
            r["num_routes"] = len(r["routes"])
            del r["routes"]
            inst["runs"].append(r)
            print(inst["name"], r["mode"], ours, inst["bks_cost"], r["gap_vs_bks_pct"], flush=True)

    for inst in instances.values():
        del inst["_model"]
    try:
        import pyvrp
        version = pyvrp.__version__
    except Exception:
        version = "unknown"
    result = {"pyvrp_version": version, "seed": args.seed,
              "warm_seconds": args.warm_seconds, "cold_seconds": args.cold_seconds,
              "instances": list(instances.values())}
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)

    lines = ["# CVRPLib XL warm-start probe", "",
             "PyVRP %s, one CPU per run, seed %d." % (version, args.seed), "",
             "| instance | clients | BKS | mode | seconds | cost | gap % | routes | improves |",
             "|---|---|---|---|---|---|---|---|---|"]
    for inst in instances.values():
        for r in inst["runs"]:
            lines.append("| %s | %d | %d | %s | %d | %s | %s | %d | %s |" % (
                inst["name"], inst["clients"], inst["bks_cost"], r["mode"], r["seconds"],
                r["check_cost"], r["gap_vs_bks_pct"], r["num_routes"], r["improves_bks"]))
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
