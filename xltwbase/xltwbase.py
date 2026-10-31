"""Vehicles first, then distance, with the fleet search stopped at a proven lower bound: a PyVRP baseline for
CVRPLib's XLTW-Test set (1,000 to 10,000 customers), checked first on Gehring-Homberger 1,000-customer instances.

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.

CVRPLib's VRPTW BKS Challenge ranks by vehicles, then distance. Our `vrptwl/` baseline gave PyVRP 0.14.1's
`minimise_fleet` half of the budget and `solve` the other half. `minimise_fleet` stops early once the fleet reaches
its own lower bound, ceil(total demand / capacity), but the unused half was then thrown away; and where time windows
force more vehicles than that (R1_10_1: 100 in double precision, capacity bound 91) it spends its whole half trying
fleets that cannot exist. This script:

- computes K = max(Martello-Toth L2, time-window clique) with `xltwlb.py` (cvrplib-baselines v0.3.3) in the
  travel-time convention of the run;
- runs `minimise_fleet`'s own loop (fleet - 1, solve until the first feasible solution, repeat), but stops it at K;
- gives `solve` everything the fleet phase did not use;
- re-checks every result in exact decimal arithmetic, from the file's own tokens, in the run's convention.

Conventions: 'double' (Euclidean; PyVRP sees every number x1,000 rounded up, as in `vrptwl/`), 'dimacs' (each arc
truncated to 0.1; x10, exact) and 'round' (each arc rounded to the nearest integer; exact). `--study` runs the
pre-registered check in expectations.md against `vrptwl-fleet-v1`; `--files` runs any instance files.
"""
import argparse
import glob
import json
import os
import statistics
import time
import traceback
import urllib.request
from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal

import numpy as np

import xltwlb as X

BASE = "https://galgos.inf.puc-rio.br/cvrplib/en/download"
UA = "CVRPLib VRPTW lex baseline - MV2 of Munim, Inc. (mv2@munimtech.com)"
SEED = 20261030
TOL = {"double": Decimal("0.000001"), "dimacs": Decimal(0), "round": Decimal(0)}
T0 = time.time()

# vrptwl-fleet-v1 (2026-10-30, cvrplib-baselines v0.3.1): id, vehicles, double distance, fleet seconds, solve
# iterations. Same PyVRP, seed, scaling and VRPLIB copy as here; solve had 300 s.
VRPTWL = {
    "R1_10_4": (699, 91, 47113.26, 4.9, 25349), "R1_10_6": (701, 91, 59175.64, 9.5, 18130),
    "R1_10_8": (703, 91, 46241.94, 4.1, 32803), "RC1_10_3": (718, 90, 45185.2, 4.9, 28929),
    "RC1_10_10": (725, 90, 48753.8, 3.6, 19412), "R2_10_4": (709, 19, 18299.05, 7.7, 104765),
    "RC2_10_9": (734, 18, 23889.87, 11.5, 159557), "C1_10_4": (679, 90, 39674.89, 9.8, 60039),
    "R1_10_1": (696, 100, 56499.94, 301.1, 30396),
    "C1_10_1": (676, 100, 42481.34, 300.6, 76737), "C1_10_7": (682, 99, 42718.88, 300.5, 40124),
    "C2_10_6": (691, 30, 16348.45, 300.6, 80503), "RC2_10_1": (726, 21, 29744.99, 300.6, 83211),
}
# E: minimise_fleet reached the capacity bound within 12 s; T: the time-window bound is above the capacity bound;
# F: minimise_fleet used its whole 300 s (controls).
GROUPS = {"E": ["R1_10_4", "R1_10_6", "R1_10_8", "RC1_10_3", "RC1_10_10", "R2_10_4", "RC2_10_9", "C1_10_4"],
          "T": ["R1_10_1"], "F": ["C1_10_1", "C1_10_7", "C2_10_6", "RC2_10_1"]}
CONV_RUNS = [("R1_10_1", "dimacs"), ("R1_10_1", "round"), ("RC2_10_9", "dimacs"), ("RC2_10_9", "round")]


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def rf_double(vals):
    return np.ceil(1000 * np.asarray(vals, dtype=np.float64)).astype(np.int64)


def rf_dimacs(vals):
    return np.floor(10 * np.asarray(vals, dtype=np.float64)).astype(np.int64)


def rf_round(vals):
    return np.floor(np.asarray(vals, dtype=np.float64) + 0.5).astype(np.int64)


ROUND_FUNCS = {"double": rf_double, "dimacs": rf_dimacs, "round": rf_round}


def to_vrplib(inst):
    """VRPLIB text for pyvrp.read (as vrptwl/fleet_double.py); customer i of `rows` is VRPLIB node i + 1."""
    rows = inst["rows"]
    lines = ["NAME : %s" % inst["name"], "TYPE : VRPTW",
             "DIMENSION : %d" % len(rows), "VEHICLES : %d" % (inst["vehicles"] or len(rows) - 1),
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


def lower_bound(inst, conv):
    """K in `conv` (vehicles), with KC, KB and KT for the record."""
    b = X.bound_one(inst, [conv])
    c = b[conv]
    k = c["k"] if c else b["kb"]
    return {"kc": b["kc"], "kb": b["kb"], "kt": c["kt"] if c else None, "k": k,
            "clique_verified": c["verified"] if c else None}


def check_exact(routes, inst, conv):
    """Independent check in 50-digit decimals from the file's tokens: coverage, capacity, every arrival (depot
    return included) against its due time in `conv`. Returns ok, reason, distance (summed even when late), late."""
    raw = inst["raw"]
    n = len(raw) - 1
    x, y, q, a, b, s = ([Decimal(r[k]) for r in raw] for k in range(6))
    cap = Decimal(str(inst["capacity"]))
    seen = set()
    for r in routes:
        if not r:
            return {"ok": False, "reason": "empty route", "distance": None, "late": None}
        for c in r:
            if c in seen or not 1 <= c <= n:
                return {"ok": False, "reason": "bad or repeated customer %d" % c, "distance": None, "late": None}
            seen.add(c)
        if sum(q[c] for c in r) > cap:
            return {"ok": False, "reason": "over capacity", "distance": None, "late": None}
    if len(seen) != n:
        return {"ok": False, "reason": "%d customers not visited" % (n - len(seen)), "distance": None,
                "late": None}
    total, late = Decimal(0), 0
    for r in routes:
        t, prev = a[0], 0
        for c in list(r) + [0]:
            d = X.exact_time(x[prev], y[prev], x[c], y[c], conv)
            total += d
            t += d
            late += t > b[c] + TOL[conv]
            if c:
                t = max(t, a[c]) + s[c]
            prev = c
    return {"ok": late == 0, "reason": "" if not late else "%d late arrivals" % late, "distance": float(total),
            "late": late}


def _value(attr):
    return attr() if callable(attr) else attr


def route_clients(route):
    """Customer numbers (client index + 1) of a PyVRP 0.14 route, as in vrptwl/fleet_double.py."""
    return [_value(a.idx) + 1 for a in route.schedule() if _value(a.is_client)]


def fleet_down(data, lower, seconds, seed):
    """minimise_fleet's loop from PyVRP 0.14.1 (one vehicle fewer, solve to the first feasible solution, shrink to
    the routes used), stopped at `lower` instead of PyVRP's capacity bound, on its own clock.
    Returns (vehicle type, seconds used, solves, stopped_at_bound)."""
    from pyvrp import solve
    from pyvrp.stop import FirstFeasible, MaxRuntime, MultipleCriteria

    t0 = time.time()
    feas = data.vehicle_type(0)
    solves = 0
    while feas.num_available > lower:
        left = seconds - (time.time() - t0)
        if left <= 0:
            break
        fleet = feas.replace(num_available=feas.num_available - 1)
        res = solve(data.replace(vehicle_types=[fleet]), stop=MultipleCriteria([FirstFeasible(), MaxRuntime(left)]),
                    seed=seed, collect_stats=False, display=False)
        solves += 1
        if not res.best.is_feasible():
            break
        feas = fleet.replace(num_available=min(fleet.num_available, res.best.num_routes()))
    return feas, round(time.time() - t0, 1), solves, feas.num_available <= lower


def run_one(task):
    import pyvrp
    from pyvrp.stop import MaxRuntime

    vrplib_path, conv, seconds, seed, lower = task
    data = pyvrp.read(vrplib_path, round_func=ROUND_FUNCS[conv])
    t0 = time.time()
    vt, fleet_seconds, solves, at_bound = fleet_down(data, lower, seconds / 2.0, seed)
    left = max(seconds - (time.time() - t0), 1.0)
    res = pyvrp.solve(data.replace(vehicle_types=[vt]), stop=MaxRuntime(left), seed=seed, collect_stats=False,
                      display=False)
    best = res.best
    return {"conv": conv, "seconds": seconds, "seed": seed, "lower": lower, "fleet": vt.num_available,
            "fleet_seconds": fleet_seconds, "fleet_solves": solves, "stopped_at_bound": at_bound,
            "solve_seconds": round(left, 1), "feasible": best.is_feasible(), "routes": [route_clients(r) for r in
                                                                                       best.routes()],
            "iterations": res.num_iterations, "wall_seconds": round(time.time() - t0, 1)}


def assess(r, inst):
    chk = check_exact(r["routes"], inst, r["conv"])
    r.update({"vehicles": len(r["routes"]), "exact_ok": chk["ok"], "exact_reason": chk["reason"],
              "distance": None if chk["distance"] is None else round(chk["distance"], 2),
              "structure_ok": chk["late"] is not None, "pyvrp_agrees": chk["ok"] or not r["feasible"]})
    r["below_bound"] = chk["ok"] and r["vehicles"] < r["lower"]
    return r


def write_sol(routes, distance):
    lines = ["Route #%d: %s" % (i + 1, " ".join(map(str, rt))) for i, rt in enumerate(routes)]
    lines.append("Cost %.2f" % distance)
    return "\n".join(lines) + "\n"


def group_of(name):
    for g, names in GROUPS.items():
        if name in names:
            return g
    return None


def tally_study(recs):
    """recs: one dict per run with instance, conv, run (or error). Adds the comparisons the verdicts read."""
    runs = [r for r in recs if r.get("run")]
    dbl = {r["instance"]: r["run"] for r in runs if r["conv"] == "double"}
    cmp = {}
    for name, (_, veh, dist, fsec, it) in VRPTWL.items():
        x = dbl.get(name)
        if not x or not x["exact_ok"]:
            continue
        cmp[name] = {"group": group_of(name), "vehicles": x["vehicles"], "vrptwl_vehicles": veh,
                     "distance": x["distance"], "vrptwl_distance": dist,
                     "distance_change_pct": round(100.0 * (x["distance"] - dist) / dist, 3),
                     "fleet_seconds": x["fleet_seconds"], "vrptwl_fleet_seconds": fsec,
                     "iterations_per_s": round(x["iterations"] / max(x["solve_seconds"], 1e-9), 1),
                     "vrptwl_iterations_per_s": round(it / 300.0, 1)}
    e = [cmp[n] for n in GROUPS["E"] if n in cmp]
    e_same = [c for c in e if c["vehicles"] == c["vrptwl_vehicles"]]
    t = {
        "runs_expected": len(VRPTWL) + len(CONV_RUNS), "runs": len(recs),
        "run_errors": ["%s/%s" % (r["instance"], r["conv"]) for r in recs if r.get("error")],
        "structure_fail": ["%s/%s" % (r["instance"], r["conv"]) for r in runs if not r["run"]["structure_ok"]],
        "pyvrp_disagreements": ["%s/%s" % (r["instance"], r["conv"]) for r in runs if not r["run"]["pyvrp_agrees"]],
        "below_bound": ["%s/%s" % (r["instance"], r["conv"]) for r in runs if r["run"]["below_bound"]],
        "unverified_cliques": ["%s/%s" % (r["instance"], r["conv"]) for r in recs
                               if r.get("bound") and r["bound"]["clique_verified"] is False],
        "exact_ok": sum(1 for r in runs if r["run"]["exact_ok"]),
        "e_compared": len(e), "e_same_vehicles": len(e_same),
        "e_shorter": sum(1 for c in e_same if c["distance"] < c["vrptwl_distance"] - 0.005),
        "e_median_reduction_pct": round(-statistics.median(c["distance_change_pct"] for c in e_same), 3)
        if e_same else None,
        "r1_10_1": cmp.get("R1_10_1"),
        "comparison": cmp,
        "conv_runs": {"%s/%s" % (r["instance"], r["conv"]): {k: r["run"][k] for k in
                                                             ("vehicles", "lower", "exact_ok", "distance",
                                                              "fleet_seconds", "stopped_at_bound")}
                      for r in runs if r["conv"] != "double"},
    }
    t["predictions"] = score_q(t)
    return t


def score_q(t):
    """Verdicts for Q0-Q5 (expectations.md)."""
    def verdict(ok):
        return "untestable" if ok is None else ("held" if ok else "did not hold")
    r1 = t["r1_10_1"]
    return {
        "Q0": verdict(t["runs"] == t["runs_expected"] and not t["run_errors"] and not t["structure_fail"]
                      and not t["pyvrp_disagreements"] and not t["below_bound"] and not t["unverified_cliques"]),
        "Q1": verdict(t["exact_ok"] == t["runs_expected"]),
        "Q2": verdict(t["e_compared"] == len(GROUPS["E"]) and t["e_same_vehicles"] == len(GROUPS["E"])),
        "Q3": verdict(t["e_shorter"] >= 7),
        "Q4": verdict(None if t["e_median_reduction_pct"] is None else t["e_median_reduction_pct"] >= 1.5),
        "Q5": verdict(None if r1 is None else (r1["vehicles"] == 100 and r1["fleet_seconds"] < 120)),
    }


def solve_all(jobs, workers, out):
    """jobs: list of (rec, inst, conv, seconds). Writes VRPLIB copies, runs, checks, saves on-time solutions."""
    conv_dir, sols = os.path.join(out, "vrplib"), os.path.join(out, "sols")
    for d in (conv_dir, sols):
        os.makedirs(d, exist_ok=True)
    tasks = []
    for rec, inst, conv, seconds in jobs:
        try:
            rec["bound"] = lower_bound(inst, conv)
        except Exception:
            rec["error"] = traceback.format_exc()
            continue
        vp = os.path.join(conv_dir, "%s.vrp" % inst["name"])
        with open(vp, "w", encoding="utf-8") as f:
            f.write(to_vrplib(inst))
        tasks.append((rec, inst, (vp, conv, seconds, SEED, rec["bound"]["k"])))
        log("%s/%s: bound %s" % (inst["name"], conv, json.dumps(rec["bound"])))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [(rec, inst, pool.submit(run_one, t)) for rec, inst, t in tasks]
        for rec, inst, fut in futures:
            try:
                r = assess(fut.result(), inst)
            except Exception:
                rec["error"] = traceback.format_exc()
                log("%s/%s ERROR %s" % (rec["instance"], rec["conv"], rec["error"]))
                continue
            if r["exact_ok"]:
                with open(os.path.join(sols, "%s.%s.sol" % (inst["name"], r["conv"])), "w", encoding="utf-8") as f:
                    f.write(write_sol(r["routes"], r["distance"]))
            del r["routes"]
            rec["run"] = r
            log("%s/%s: K %d, %d vehicles, exact_ok=%s, distance %s, fleet %.1f s (%d solves, at bound %s), "
                "%d it" % (rec["instance"], r["conv"], r["lower"], r["vehicles"], r["exact_ok"], r["distance"],
                           r["fleet_seconds"], r["fleet_solves"], r["stopped_at_bound"], r["iterations"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", action="store_true", help="the pre-registered check in expectations.md")
    ap.add_argument("--files", default="", help="glob of instance files (VRPLIB or Solomon)")
    ap.add_argument("--conv", default="double", choices=sorted(ROUND_FUNCS))
    ap.add_argument("--seconds", type=int, default=600)
    ap.add_argument("--conv-seconds", type=int, default=120)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    args = ap.parse_args()
    out = os.path.join(args.out_dir, "xltwbase")
    os.makedirs(out, exist_ok=True)

    jobs, recs = [], []
    if args.study:
        src = os.path.join(args.data_dir, "cvrplib-vrptw")
        os.makedirs(src, exist_ok=True)
        insts = {}
        for name, (i, *_rest) in VRPTWL.items():
            p = fetch("%s/instance/%s" % (BASE, i), os.path.join(src, "%d.txt" % i))
            with open(p, encoding="utf-8") as f:
                insts[name] = X.parse_any(f.read())
            if insts[name]["name"] != name:
                raise SystemExit("id %d is %s, not %s" % (i, insts[name]["name"], name))
        for name in VRPTWL:
            jobs.append(({"instance": name, "conv": "double", "group": group_of(name)}, insts[name], "double",
                         args.seconds))
        for name, conv in CONV_RUNS:
            jobs.append(({"instance": name, "conv": conv, "group": "conv"}, insts[name], conv, args.conv_seconds))
    for p in sorted(glob.glob(args.files)) if args.files else []:
        with open(p, encoding="utf-8") as f:
            inst = X.parse_any(f.read())
        jobs.append(({"instance": inst["name"], "conv": args.conv, "source": p}, inst, args.conv, args.seconds))
    recs = [j[0] for j in jobs]
    log("runs: %d" % len(jobs))
    solve_all(jobs, args.workers, out)

    res = {"pyvrp": "0.14.1 (pinned)", "seed": SEED, "seconds": args.seconds, "conv_seconds": args.conv_seconds,
           "runs": recs}
    if args.study:
        res["tally"] = tally_study(recs)
        print(json.dumps(res["tally"]["predictions"]), flush=True)
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    lines = ["# xltwbase: vehicles first, fleet search stopped at a proven bound, leftover time to distance", "",
             "PyVRP 0.14.1, one CPU per run, seed %d. Every result re-checked exactly in its own convention." % SEED,
             ""]
    if args.study:
        lines += ["Predictions: `%s`" % json.dumps(res["tally"]["predictions"]), ""]
    lines += ["| instance | group | conv | KC | K | vehicles | exact ok | distance | fleet s | solves | at bound "
              "| solve s | iterations | vrptwl vehicles | vrptwl distance | change % |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    cmp = res.get("tally", {}).get("comparison", {})
    for r in recs:
        x, b = r.get("run"), r.get("bound") or {}
        c = cmp.get(r["instance"]) if r["conv"] == "double" else None
        if not x:
            lines.append("| %s | %s | %s | %s | %s | error | | | | | | | | | | |" % (
                r["instance"], r.get("group", ""), r["conv"], b.get("kc"), b.get("k")))
            continue
        lines.append("| %s | %s | %s | %s | %s | %d | %s | %s | %s | %d | %s | %s | %d | %s | %s | %s |" % (
            r["instance"], r.get("group", ""), r["conv"], b["kc"], b["k"], x["vehicles"], x["exact_ok"],
            x["distance"], x["fleet_seconds"], x["fleet_solves"], x["stopped_at_bound"], x["solve_seconds"],
            x["iterations"], c["vrptwl_vehicles"] if c else "", c["vrptwl_distance"] if c else "",
            c["distance_change_pct"] if c else ""))
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    if any(r.get("error") for r in recs):
        raise SystemExit("%d run(s) failed" % sum(1 for r in recs if r.get("error")))


if __name__ == "__main__":
    main()
