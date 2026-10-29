"""How plain PyVRP scales from 1,000 to 10,000 customers with time windows.

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.

Preparation for CVRPLib's VRPTW BKS Challenge, whose XLTW instances (1,000 to
10,000 customers) keep the depot and customer locations of the XL set and add
time windows. The official windows are not public yet, so this probe uses the
real locations and demands of XL-n10001-k1570 (CVRPLib id 379) with SYNTHETIC
windows. It measures what does not depend on how the windows are drawn: peak
memory, build time, and whether one CPU reaches a feasible solution in time.

Each size runs in its own child process, so ru_maxrss is that size's peak.
ProblemData is built directly with one int64 matrix used for both distance and
duration (DIMACS convention: arcs in tenths, truncated; time = distance), which
avoids the n x n x 2 float temporaries of vrplib/pyvrp.read. All times, windows
and service durations are integer tenths.
"""
import argparse
import json
import math
import os
import random
import resource
import subprocess
import sys
import time
import urllib.request
from importlib.metadata import version

BASE = "https://galgos.inf.puc-rio.br/cvrplib/en/download"
UA = "CVRPLib XLTW scale probe - MV2 of Munim, Inc. (mv2@munimtech.com)"
SERVICE = 100  # 10.0 time units per customer, as in the Homberger R and RC sets


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


def parse_vrplib(text):
    """Return (name, capacity, xs, ys, demands); index 0 is the depot (file node 1)."""
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
            coords[int(parts[0]) - 1] = (int(parts[1]), int(parts[2]))
        elif section == "DEMAND_SECTION":
            demands[int(parts[0]) - 1] = int(parts[1])
        elif section == "DEPOT_SECTION":
            if int(parts[0]) != -1:
                depots.append(int(parts[0]))
    if depots != [1]:
        raise ValueError("expected a single depot at node 1, got %r" % depots)
    if dim is None or len(coords) != dim or len(demands) != dim:
        raise ValueError("DIMENSION does not match the sections")
    xs = [coords[i][0] for i in range(dim)]
    ys = [coords[i][1] for i in range(dim)]
    return name, cap, xs, ys, [demands[i] for i in range(dim)]


def dist10(x1, y1, x2, y2):
    """Euclidean distance in tenths, truncated (DIMACS), exact for integer coordinates."""
    dx, dy = x1 - x2, y1 - y2
    return math.isqrt(100 * (dx * dx + dy * dy))


def dist_matrix(xs, ys, chunk=256):
    """n x n int64 matrix of dist10, built in row chunks to keep temporaries small."""
    import numpy as np

    x = np.asarray(xs, dtype=np.int64)
    y = np.asarray(ys, dtype=np.int64)
    n = len(x)
    out = np.empty((n, n), dtype=np.int64)
    for s in range(0, n, chunk):
        dx = x[s:s + chunk, None] - x[None, :]
        dy = y[s:s + chunk, None] - y[None, :]
        q = 100 * (dx * dx + dy * dy)
        v = np.floor(np.sqrt(q.astype(np.float64))).astype(np.int64)
        v -= (v * v > q).astype(np.int64)
        v += ((v + 1) * (v + 1) <= q).astype(np.int64)
        out[s:s + chunk] = v
    return out


def make_windows(xs, ys, seed, width_frac=0.125, slack_frac=1.0):
    """Synthetic windows (tenths). Returns (horizon, [(early, late)] with depot first).

    Every customer is reachable on its own: early >= d0, and serving at late
    still gets back by the horizon (late + SERVICE + d0 <= horizon).
    """
    rng = random.Random(seed)
    d0 = [dist10(xs[0], ys[0], xs[i], ys[i]) for i in range(len(xs))]
    far = max(d0)
    horizon = 2 * far + SERVICE + int(slack_frac * far)
    width = int(width_frac * horizon)
    tws = [(0, horizon)]
    for i in range(1, len(xs)):
        lo, hi = d0[i], horizon - SERVICE - d0[i]
        if hi - lo <= width:
            tws.append((lo, hi))
        else:
            a = lo + rng.randrange(hi - lo - width + 1)
            tws.append((a, a + width))
    return horizon, tws


def check(routes, xs, ys, demands, cap, tws, horizon):
    """Independent feasibility check; routes hold customer numbers 1..n. Returns (ok, reason, cost)."""
    n = len(xs) - 1
    seen, total = set(), 0
    for r in routes:
        if not r:
            return False, "empty route", None
        t, load, prev = 0, 0, 0
        for c in r:
            if c in seen or not 1 <= c <= n:
                return False, "bad or repeated customer %d" % c, None
            seen.add(c)
            load += demands[c]
            d = dist10(xs[prev], ys[prev], xs[c], ys[c])
            total += d
            t += d
            if t > tws[c][1]:
                return False, "late at customer %d" % c, None
            t = max(t, tws[c][0]) + SERVICE
            prev = c
        d = dist10(xs[prev], ys[prev], xs[0], ys[0])
        total += d
        if t + d > horizon:
            return False, "late back at depot", None
        if load > cap:
            return False, "route over capacity %d > %d" % (load, cap), None
    if len(seen) != n:
        return False, "%d customers not visited" % (n - len(seen)), None
    return True, "", total


def build_data(xs, ys, demands, cap, tws, horizon, fleet):
    import pyvrp

    mat = dist_matrix(xs, ys)
    locations = [pyvrp.Location(x=float(x), y=float(y)) for x, y in zip(xs, ys)]
    clients = [pyvrp.Client(location=i, delivery=[demands[i]], service_duration=SERVICE,
                            tw_early=tws[i][0], tw_late=tws[i][1])
               for i in range(1, len(xs))]
    depots = [pyvrp.Depot(location=0)]
    vt = pyvrp.VehicleType(num_available=fleet, capacity=[cap], tw_early=0, tw_late=horizon)
    data = pyvrp.ProblemData(locations=locations, clients=clients, depots=depots,
                             vehicle_types=[vt], distance_matrices=[mat],
                             duration_matrices=[mat])
    del mat
    return data


def _value(attr):
    return attr() if callable(attr) else attr


def route_clients(route):
    """Customer numbers (client index + 1) of a PyVRP 0.14 route, depots dropped."""
    return [_value(a.idx) + 1 for a in route.schedule() if _value(a.is_client)]


def peak_mb():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)


def run_size(path, n, seconds, seed):
    """Child process: build and solve the first n customers of the file."""
    import pyvrp
    from pyvrp.stop import MaxRuntime

    with open(path, encoding="utf-8") as f:
        name, cap, xs, ys, demands = parse_vrplib(f.read())
    xs, ys, demands = xs[:n + 1], ys[:n + 1], demands[:n + 1]
    horizon, tws = make_windows(xs, ys, seed)
    rec = {"instance": name, "n": n, "capacity": cap, "horizon": horizon,
           "route_lower_bound": -(-sum(demands[1:]) // cap),
           "pyvrp_version": version("pyvrp"), "seconds": seconds, "seed": seed}
    t0 = time.time()
    data = build_data(xs, ys, demands, cap, tws, horizon, fleet=n)
    rec["build_seconds"] = round(time.time() - t0, 1)
    rec["build_peak_mb"] = peak_mb()
    t1 = time.time()
    res = pyvrp.solve(data, stop=MaxRuntime(seconds), seed=seed,
                      collect_stats=False, display=False)
    rec["solve_wall_seconds"] = round(time.time() - t1, 1)
    rec["loop_runtime"] = round(res.runtime, 1)
    rec["iterations"] = res.num_iterations
    rec["iterations_per_s"] = round(res.num_iterations / max(res.runtime, 1e-9), 2)
    best = res.best
    rec["feasible"] = best.is_feasible()
    rec["num_routes"] = best.num_routes()
    rec["pyvrp_distance"] = best.distance()
    ok, reason, cost = check([route_clients(r) for r in best.routes()],
                             xs, ys, demands, cap, tws, horizon)
    rec["check_ok"], rec["check_reason"], rec["check_cost"] = ok, reason, cost
    rec["pyvrp_matches_check"] = bool(ok and cost == best.distance())
    rec["peak_mb"] = peak_mb()
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", default="379")
    ap.add_argument("--sizes", default="1000,2500,5000,10000")
    ap.add_argument("--seconds", default="300,600,900,1800")
    ap.add_argument("--seed", type=int, default=20261029)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--one", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--n", type=int, help=argparse.SUPPRESS)
    ap.add_argument("--secs", type=int, help=argparse.SUPPRESS)
    ap.add_argument("--path", help=argparse.SUPPRESS)
    ap.add_argument("--json", help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.one:
        rec = run_size(args.path, args.n, args.secs, args.seed)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=1)
        return

    src = os.path.join(args.data_dir, "cvrplib")
    out = os.path.join(args.out_dir, "xl")
    os.makedirs(src, exist_ok=True)
    os.makedirs(out, exist_ok=True)
    path = fetch("%s/instance/%s" % (BASE, args.id), os.path.join(src, "%s.vrp" % args.id))

    sizes = [int(s) for s in args.sizes.split(",")]
    secs = [int(s) for s in args.seconds.split(",")]
    recs = []
    for n, s in zip(sizes, secs):
        js = os.path.join(out, "n%d.json" % n)
        cmd = [sys.executable, os.path.abspath(__file__), "--one", "--n", str(n),
               "--secs", str(s), "--path", path, "--json", js, "--seed", str(args.seed)]
        t0 = time.time()
        try:
            p = subprocess.run(cmd, timeout=3 * s + 900)
            code = p.returncode
        except subprocess.TimeoutExpired:
            code = "timeout"
        if code == 0 and os.path.exists(js):
            with open(js, encoding="utf-8") as f:
                rec = json.load(f)
        else:
            # -9 is usually the container's memory limit
            rec = {"n": n, "seconds": s, "error": "child exit %s" % code}
        rec["child_wall_seconds"] = round(time.time() - t0, 1)
        recs.append(rec)
        print(json.dumps(rec), flush=True)

    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump({"id": args.id, "seed": args.seed, "windows": "synthetic, see make_windows",
                   "runs": recs}, f, indent=1)
    lines = ["# Plain PyVRP on XL locations with synthetic time windows", "",
             "CVRPLib id %s, seed %d, one CPU, DIMACS tenths. Windows are synthetic, not XLTW." % (args.id, args.seed),
             "", "| n | s | build s | build peak MB | peak MB | iterations/s | feasible | routes | route LB | cost (tenths) | check |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in recs:
        if "error" in r:
            lines.append("| %d | %d | %s | | | | | | | | |" % (r["n"], r["seconds"], r["error"]))
            continue
        lines.append("| %d | %d | %s | %s | %s | %s | %s | %d | %d | %s | %s |" % (
            r["n"], r["seconds"], r["build_seconds"], r["build_peak_mb"], r["peak_mb"],
            r["iterations_per_s"], r["feasible"], r["num_routes"], r["route_lower_bound"],
            r["check_cost"], r["check_ok"] and r["pyvrp_matches_check"]))
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
