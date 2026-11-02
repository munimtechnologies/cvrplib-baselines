"""Fewer vehicles first, part 2: PyVRP's minimise_fleet loop with a longer budget, and the same loop with capped,
restarted attempts, run side by side in one job on the 13 Gehring-Homberger 1,000-customer instances where `vrptwl/`
used more vehicles than SINTEF's records.

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.

`xltwrm/` found that the plain loop (one vehicle fewer, solve from a random start until the first feasible solution,
repeat) beat a warm-started loop and a thin prize-collecting ejection loop on all 13 instances. The plain loop spends
all remaining time on the first level it cannot reach. This script compares, with a 900 s fleet budget each:

- `fleet`: the loop exactly as in `xltwrm.arm_fleet` (the reference);
- `restart`: the same loop, but each attempt is capped at max(30 s, 2 x the time the last successful attempt took)
  and a failed attempt is retried at the same fleet size with a new seed, until the budget is spent.

Both stop at K = max(Martello-Toth L2, time-window clique) from `xltwlb.py`; every result is re-checked in 50-digit
decimals by `xltwbase.check_exact`. Restarting heavy-tailed searches is an old idea (Gomes, Selman and Kautz, 1998);
nothing here is a new method. Double precision only (PyVRP sees every number x1,000 rounded up, as in `vrptwl/`).
"""
import argparse
import json
import os
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed

import xltwbase as B
import xltwrm as R

SEED = 20261102  # the seed of xltwrm/, so the fleet arm's first 300 s can be set beside xltwrm's fleet arm
ARMS = ("fleet", "restart")
MIN_CAP = 30.0
FACTOR = 2.0
CHECKPOINTS = (300, 600, 900)
MISSES = R.MISSES
T0 = time.time()


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def at(trace, t):
    """Vehicles of the last trace point reached at or before t seconds (None if none yet)."""
    v = None
    for s, k in trace:
        if s <= t:
            v = k
    return v


def attempt_cap(last_success, min_cap=MIN_CAP, factor=FACTOR):
    return min_cap if last_success is None else max(min_cap, factor * last_success)


def arm_restart(data, lower, seconds, seed, min_cap=MIN_CAP, factor=FACTOR):
    """minimise_fleet's loop with capped attempts: a failed attempt is retried at the same fleet size with a new
    seed. Returns (solution or None, trace [(s, vehicles)], stats)."""
    t0 = time.time()
    feas = data.vehicle_type(0)
    best, trace, solves, fails, last = None, [], 0, 0, None
    while feas.num_available > lower:
        left = R._left(t0, seconds)
        if left <= 0:
            break
        fleet = feas.replace(num_available=feas.num_available - 1)
        ts = time.time()
        res = R._first_feasible(data.replace(vehicle_types=[fleet]), min(attempt_cap(last, min_cap, factor), left),
                                seed + solves)
        solves += 1
        if res.best.is_feasible():
            best = res.best
            feas = fleet.replace(num_available=min(fleet.num_available, best.num_routes()))
            trace.append((round(time.time() - t0, 1), best.num_routes()))
            last = time.time() - ts
        else:
            fails += 1
    if best is None:  # already at the bound or nothing found: one solve with the full fleet, as arm_fleet does
        res = R._first_feasible(data, max(R._left(t0, seconds), 1.0), seed)
        if res.best.is_feasible():
            best = res.best
            trace.append((round(time.time() - t0, 1), best.num_routes()))
    return best, trace, {"solves": solves, "fails": fails}


def run_one(task):
    """task: (vrplib path, conv, arm, seconds, seed, lower). Runs in a worker process."""
    import pyvrp
    vp, conv, arm, seconds, seed, lower = task
    data = pyvrp.read(vp, round_func=B.ROUND_FUNCS[conv])
    t0 = time.time()
    if arm == "fleet":
        sol, trace, stats = R.arm_fleet(data, lower, seconds, seed)
    else:
        sol, trace, stats = arm_restart(data, lower, seconds, seed)
    return {"arm": arm, "conv": conv, "seconds": seconds, "seed": seed, "lower": lower,
            "pyvrp_feasible": bool(sol is not None and sol.is_feasible()),
            "routes": [B.route_clients(r) for r in sol.routes()] if sol is not None else None,
            "trace": trace, "stats": stats, "wall_seconds": round(time.time() - t0, 1)}


def verdict(ok):
    return "untestable" if ok is None else ("held" if ok else "did not hold")


def tally(recs, misses=MISSES, seconds=900):
    """recs: one dict per (instance, arm) with 'run' (assessed by xltwrm.assess) or 'error'. Scores R0-R5, each on
    its own."""
    runs = {}
    for r in recs:
        if r.get("run") and r["run"]["exact_ok"]:
            runs.setdefault(r["instance"], {})[r["arm"]] = r["run"]
    pairs = {}
    for name, (_, sintef, vrptwl) in misses.items():
        v = runs.get(name, {})
        p = {"sintef": sintef, "vrptwl": vrptwl}
        for a in ARMS:
            p[a] = v[a]["vehicles"] if a in v else None
            for c in CHECKPOINTS:
                p["%s_%d" % (a, c)] = at(v[a]["trace"], c) if a in v else None
        pairs[name] = p
    both = [p for p in pairs.values() if p["fleet"] is not None and p["restart"] is not None]
    longer = [p for p in pairs.values() if p["fleet"] is not None and p["fleet_300"] is not None]
    t = {
        "runs_expected": len(misses) * len(ARMS), "runs": len(recs),
        "errors": ["%s/%s" % (r["instance"], r["arm"]) for r in recs if r.get("error")],
        "not_exact": ["%s/%s" % (r["instance"], r["arm"]) for r in recs if r.get("run") and not r["run"]["exact_ok"]],
        "below_bound": ["%s/%s" % (r["instance"], r["arm"]) for r in recs if r.get("run") and r["run"]["below_bound"]],
        "below_sintef": ["%s/%s" % (n, a) for n, p in pairs.items() for a in ARMS
                         if p[a] is not None and p[a] < p["sintef"]],
        "pairs_fleet_300": len(longer),
        "fleet_gained_after_300": sum(1 for p in longer if p["fleet"] < p["fleet_300"]),
        "fleet_all": sum(1 for p in pairs.values() if p["fleet"] is not None),
        "fleet_over_sintef": sum(p["fleet"] - p["sintef"] for p in pairs.values() if p["fleet"] is not None),
        "pairs_fleet_restart": len(both),
        "restart_le_fleet": sum(1 for p in both if p["restart"] <= p["fleet"]),
        "restart_lt_fleet": sum(1 for p in both if p["restart"] < p["fleet"]),
        "restart_gt_fleet": sum(1 for p in both if p["restart"] > p["fleet"]),
        "totals": {a: sum(p[a] for p in pairs.values() if p[a] is not None) for a in ARMS},
        "pairs": pairs,
    }
    n = len(misses)
    t["predictions"] = {
        "R0": verdict(t["runs"] == t["runs_expected"] and not t["errors"] and not t["not_exact"]
                      and not t["below_bound"]),
        "R1": verdict(t["fleet_gained_after_300"] >= 4 if t["pairs_fleet_300"] >= 10 else None),
        "R2": verdict(t["fleet_over_sintef"] <= 10 if t["fleet_all"] == n else None),
        "R3": verdict(t["restart_le_fleet"] >= 11 if t["pairs_fleet_restart"] >= 10 else None),
        "R4": verdict(t["restart_lt_fleet"] >= 3 if t["pairs_fleet_restart"] >= 10 else None),
        "R5": verdict(not t["below_sintef"]),
    }
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=900, help="fleet budget per arm and instance")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", default="", help="comma-separated instance names (default: all 13)")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    args = ap.parse_args()
    out = os.path.join(args.out_dir, "xltwrs")
    sols, vdir = os.path.join(out, "sols"), os.path.join(out, "vrplib")
    for d in (out, sols, vdir):
        os.makedirs(d, exist_ok=True)
    names = [n for n in MISSES if not args.only or n in args.only.split(",")]
    src = os.path.join(args.data_dir, "cvrplib-vrptw")
    os.makedirs(src, exist_ok=True)

    insts, recs, tasks = {}, [], []
    for name in names:
        i = MISSES[name][0]
        p = B.fetch("%s/instance/%s" % (B.BASE, i), os.path.join(src, "%d.txt" % i))
        with open(p, encoding="utf-8") as f:
            inst = R.X.parse_any(f.read())
        if inst["name"] != name:
            raise SystemExit("id %d is %s, not %s" % (i, inst["name"], name))
        insts[name] = inst
        bound = B.lower_bound(inst, "double")
        vp = os.path.join(vdir, "%s.vrp" % name)
        with open(vp, "w", encoding="utf-8") as f:
            f.write(B.to_vrplib(inst))
        log("%s: K %d (KC %d, KT %s, clique verified %s)" % (name, bound["k"], bound["kc"], bound["kt"],
                                                              bound["clique_verified"]))
        for arm in ARMS:  # interleaved: both arms of an instance run close together in time
            rec = {"instance": name, "arm": arm, "bound": bound}
            recs.append(rec)
            tasks.append((rec, (vp, "double", arm, args.seconds, SEED, bound["k"])))

    progress = open(os.path.join(out, "progress.jsonl"), "a", encoding="utf-8")
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(run_one, t): rec for rec, t in tasks}
        for fut in as_completed(futs):
            rec = futs[fut]
            try:
                r = R.assess(fut.result(), insts[rec["instance"]])
            except Exception:
                rec["error"] = traceback.format_exc()
                log("%s/%s ERROR %s" % (rec["instance"], rec["arm"], rec["error"]))
                progress.write(json.dumps({"instance": rec["instance"], "arm": rec["arm"], "error": rec["error"]})
                               + "\n")
                progress.flush()
                continue
            if r["exact_ok"]:
                with open(os.path.join(sols, "%s.%s.sol" % (rec["instance"], rec["arm"])), "w",
                          encoding="utf-8") as f:
                    f.write(B.write_sol(r["routes"], r["distance"]))
            del r["routes"]
            rec["run"] = r
            line = {"instance": rec["instance"], "arm": rec["arm"], "K": rec["bound"]["k"],
                    "sintef": MISSES[rec["instance"]][1], "vehicles": r["vehicles"], "exact_ok": r["exact_ok"],
                    "distance": r["distance"], "reached_final_s": r.get("reached_final_s"), "stats": r["stats"],
                    "trace": r["trace"]}
            progress.write(json.dumps(line) + "\n")
            progress.flush()
            log("DONE %s" % json.dumps(line))
    progress.close()

    t = tally(recs, {n: MISSES[n] for n in names}, args.seconds)
    res = {"pyvrp": "0.14.1 (pinned)", "seed": SEED, "seconds": args.seconds, "conv": "double",
           "min_cap": MIN_CAP, "factor": FACTOR, "runs": recs, "tally": t}
    print(json.dumps(t["predictions"]), flush=True)
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    lines = ["# xltwrs: the fleet loop at 900 s, and with capped restarted attempts", "",
             "PyVRP 0.14.1, double precision, %d s fleet budget per arm, one CPU per run, seed %d. Every result "
             "re-checked exactly." % (args.seconds, SEED), "",
             "Predictions: `%s`" % json.dumps(t["predictions"]), "",
             "Totals (vehicles, instances with an on-time result): `%s`" % json.dumps(t["totals"]), "",
             "| instance | K | SINTEF | vrptwl | fleet 300 s | fleet 600 s | fleet | restart 300 s | restart 600 s |"
             " restart | fleet s | restart s | restart solves | restart fails |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    by = {(r["instance"], r["arm"]): r for r in recs}
    for name in names:
        p = t["pairs"][name]
        row = [name, str(by[(name, "fleet")]["bound"]["k"]), str(p["sintef"]), str(p["vrptwl"])]
        for a in ARMS:
            row += [str(p["%s_300" % a]), str(p["%s_600" % a]), str(p[a])]
        runs = [by[(name, a)].get("run") for a in ARMS]
        row += [str(x.get("reached_final_s")) if x else "" for x in runs]
        rs = runs[1]["stats"] if runs[1] else {}
        row += [str(rs.get("solves", "")), str(rs.get("fails", ""))]
        lines.append("| " + " | ".join(row) + " |")
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    if any(r.get("error") for r in recs):
        raise SystemExit("%d run(s) failed" % sum(1 for r in recs if r.get("error")))


if __name__ == "__main__":
    main()
