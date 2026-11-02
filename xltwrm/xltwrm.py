"""Fewer vehicles first: three route-minimisation loops on top of PyVRP 0.14.1, run side by side in one job, for
CVRPLib's VRPTW BKS Challenge (vehicles first, then distance).

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.

`vrptwl/` (cvrplib-baselines v0.3.1) used more vehicles than SINTEF's hierarchical record on 13 of the 60
Gehring-Homberger 1,000-customer instances (21 vehicles in total). Its fleet search is PyVRP's `minimise_fleet` loop:
one vehicle fewer, solve from a random start until the first feasible solution, repeat. Each attempt starts from
scratch. This script compares, on those 13 instances, in the same job and with the same 300 s fleet budget:

- A `fleet`: the `minimise_fleet` loop as in `xltwbase.py` (stopped at the proven bound K), as the reference;
- C `warm`: the same loop, but each attempt starts from the last feasible solution with its smallest route removed
  (PyVRP must re-insert the removed customers, because they are required);
- B `eject`: the smallest route is removed and every customer becomes optional with a prize far above any detour, so
  the search keeps time windows and capacity and leaves out as few customers as it can; customers still left out
  after a short round get a higher prize (a counter, as in the ejection pool of Nagata and Braysy, 2009), and rounds
  repeat until every customer is served with one route fewer. Penalties are fixed at 20 times the largest prize, so
  a late arrival or an overload never pays for a prize: customers are left out instead.

All three stop at K = max(Martello-Toth L2, time-window clique) from `xltwlb.py` and every result is re-checked in
50-digit decimals by `xltwbase.check_exact`. The idea of B is old (ejection pools, prize-collecting relaxation); what
is measured here is whether a thin layer of it over PyVRP's search helps at 1,000 customers. Double precision only
(PyVRP sees every number x1,000 rounded up, as in `vrptwl/`).
"""
import argparse
import json
import math
import os
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed

import xltwbase as B
import xltwlb as X

SEED = 20261102
ARMS = ("fleet", "warm", "eject")
SCALE = {"double": 1000, "dimacs": 10, "round": 1}
PENALTY_FACTOR = 20
# The 13 instances where vrptwl/ used more vehicles than SINTEF's record (vrptwl/results.md):
# name -> (CVRPLib id, SINTEF vehicles, vrptwl vehicles)
MISSES = {
    "C1_10_2": (677, 90, 94), "C1_10_6": (681, 99, 100), "C1_10_7": (682, 97, 99), "C1_10_8": (683, 92, 96),
    "C1_10_9": (684, 90, 91), "C2_10_6": (691, 29, 30), "C2_10_7": (692, 29, 30), "C2_10_8": (693, 28, 29),
    "C2_10_9": (694, 28, 29), "RC1_10_1": (716, 90, 91), "RC2_10_1": (726, 20, 21), "RC2_10_2": (727, 18, 20),
    "RC2_10_5": (730, 18, 19),
}
T0 = time.time()


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def visits0(route):
    """0-based PyVRP client indices of a route (customer number - 1)."""
    return [c - 1 for c in B.route_clients(route)]


def base_prize(inst, conv):
    """A prize above any insertion detour: twice the bounding-box diagonal, in PyVRP's scaled units, plus one."""
    xs = [float(r[0]) for r in inst["rows"]]
    ys = [float(r[1]) for r in inst["rows"]]
    diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
    return int(math.ceil(2 * diag * SCALE[conv])) + 1


def optional_copy(data, prizes):
    """The same instance with every client optional and the given prizes (all other client fields kept)."""
    from pyvrp import Client
    cl = []
    for c, p in zip(data.clients(), prizes):
        cl.append(Client(location=c.location, delivery=list(c.delivery), pickup=list(c.pickup),
                         service_duration=c.service_duration, tw_early=c.tw_early, tw_late=c.tw_late,
                         release_time=c.release_time, prize=int(p), required=False, group=c.group, name=c.name))
    return data.replace(clients=cl)


def _left(t0, seconds):
    return seconds - (time.time() - t0)


def _first_feasible(data, seconds, seed, initial=None):
    from pyvrp import solve
    from pyvrp.stop import FirstFeasible, MaxRuntime, MultipleCriteria
    return solve(data, stop=MultipleCriteria([FirstFeasible(), MaxRuntime(max(seconds, 0.1))]), seed=seed,
                 collect_stats=False, display=False, initial_solution=initial)


def _smallest_dropped(sol):
    routes = [visits0(r) for r in sol.routes()]
    drop = min(range(len(routes)), key=lambda i: (len(routes[i]), i))
    return [r for i, r in enumerate(routes) if i != drop and r], len(routes[drop])


def arm_fleet(data, lower, seconds, seed):
    """xltwbase.fleet_down's loop (PyVRP 0.14.1 minimise_fleet stopped at `lower`), keeping the last feasible
    solution. Returns (solution or None, trace [(s, vehicles)], stats)."""
    t0 = time.time()
    feas = data.vehicle_type(0)
    best, trace, solves = None, [], 0
    while feas.num_available > lower:
        left = _left(t0, seconds)
        if left <= 0:
            break
        fleet = feas.replace(num_available=feas.num_available - 1)
        res = _first_feasible(data.replace(vehicle_types=[fleet]), left, seed)
        solves += 1
        if not res.best.is_feasible():
            break
        best = res.best
        feas = fleet.replace(num_available=min(fleet.num_available, best.num_routes()))
        trace.append((round(time.time() - t0, 1), best.num_routes()))
    if best is None:  # already at the bound or the first attempt failed: one solve with the full fleet
        res = _first_feasible(data, max(_left(t0, seconds), 1.0), seed)
        if res.best.is_feasible():
            best = res.best
            trace.append((round(time.time() - t0, 1), best.num_routes()))
    return best, trace, {"solves": solves}


def arm_warm(data, lower, seconds, seed):
    """Like arm_fleet, but each attempt starts from the last feasible solution without its smallest route."""
    from pyvrp import Solution
    t0 = time.time()
    res = _first_feasible(data, _left(t0, seconds), seed)
    if not res.best.is_feasible():
        return None, [], {"solves": 1}
    best, solves = res.best, 1
    trace = [(round(time.time() - t0, 1), best.num_routes())]
    vt = data.vehicle_type(0)
    while best.num_routes() > lower and _left(t0, seconds) > 0:
        partial, _ = _smallest_dropped(best)
        d = data.replace(vehicle_types=[vt.replace(num_available=len(partial))])
        res = _first_feasible(d, _left(t0, seconds), seed + solves, initial=Solution(d, partial))
        solves += 1
        if not res.best.is_feasible() or res.best.num_clients() != data.num_clients:
            break
        best = Solution(data, [visits0(r) for r in res.best.routes()])
        trace.append((round(time.time() - t0, 1), best.num_routes()))
    return best, trace, {"solves": solves}


class _Flag:
    """Stopping criterion that fires once a callback has seen every client served."""

    def __init__(self):
        self.done = False

    def __call__(self, best_cost):
        return self.done


def arm_eject(data, lower, seconds, seed, prize, round_seconds=5.0):
    """Prize-collecting ejection loop (see module docstring). Returns (solution or None, trace, stats)."""
    from pyvrp import (IteratedLocalSearchCallbacks, IteratedLocalSearchParams, PenaltyParams, Solution,
                       SolveParams, solve)
    from pyvrp.stop import MaxRuntime, MultipleCriteria

    n = data.num_clients

    class Seen(IteratedLocalSearchCallbacks):
        def __init__(self, flag):
            self.flag = flag

        def on_best(self, best):
            if best.num_clients() == n and best.is_feasible():
                self.flag.done = True

    t0 = time.time()
    res = _first_feasible(data, _left(t0, seconds), seed)
    if not res.best.is_feasible():
        return None, [], {"rounds": 0, "levels": 0, "max_count": 0}
    best = res.best
    trace = [(round(time.time() - t0, 1), best.num_routes())]
    counts = [0] * n
    rounds = levels = 0
    vt = data.vehicle_type(0)
    while best.num_routes() > lower and _left(t0, seconds) > 0:
        partial, _ = _smallest_dropped(best)
        m = len(partial)
        levels += 1
        done = False
        while _left(t0, seconds) > 0:
            d = optional_copy(data, [prize * (1 + c) for c in counts]).replace(
                vehicle_types=[vt.replace(num_available=m)])
            flag = _Flag()
            # Penalties fixed far above any prize: a time-window or load violation never pays for a prize, so the
            # search leaves customers out instead of serving them late (PyVRP's default cap is 100,000 per unit).
            pen = float(PENALTY_FACTOR * prize * (1 + max(counts)))
            params = SolveParams(ils=IteratedLocalSearchParams(callbacks=Seen(flag)),
                                 penalty=PenaltyParams(min_penalty=pen, max_penalty=pen))
            r = solve(d, stop=MultipleCriteria([flag, MaxRuntime(max(min(round_seconds, _left(t0, seconds)), 0.1))]),
                      seed=seed + rounds, collect_stats=False, display=False, params=params,
                      initial_solution=Solution(d, partial))
            rounds += 1
            got = [visits0(rt) for rt in r.best.routes()]
            seen = {c for rt in got for c in rt}
            if len(seen) == n and r.best.is_feasible():
                cand = Solution(data, [rt for rt in got if rt])
                if cand.is_feasible():
                    best, done = cand, True
                    trace.append((round(time.time() - t0, 1), best.num_routes()))
                    break
            for c in range(n):
                if c not in seen:
                    counts[c] += 1
            partial = [rt for rt in got if rt]
        if not done:
            break
    return best, trace, {"rounds": rounds, "levels": levels, "max_count": max(counts) if counts else 0}


def run_one(task):
    """task: (vrplib path, conv, arm, seconds, seed, lower, prize). Runs in a worker process."""
    import pyvrp
    vp, conv, arm, seconds, seed, lower, prize = task
    data = pyvrp.read(vp, round_func=B.ROUND_FUNCS[conv])
    t0 = time.time()
    if arm == "fleet":
        sol, trace, stats = arm_fleet(data, lower, seconds, seed)
    elif arm == "warm":
        sol, trace, stats = arm_warm(data, lower, seconds, seed)
    else:
        sol, trace, stats = arm_eject(data, lower, seconds, seed, prize)
    return {"arm": arm, "conv": conv, "seconds": seconds, "seed": seed, "lower": lower,
            "pyvrp_feasible": bool(sol is not None and sol.is_feasible()),
            "routes": [B.route_clients(r) for r in sol.routes()] if sol is not None else None,
            "trace": trace, "stats": stats, "wall_seconds": round(time.time() - t0, 1)}


def assess(r, inst):
    if not r["routes"]:
        r.update({"vehicles": None, "exact_ok": False, "exact_reason": "no solution", "distance": None,
                  "below_bound": False})
        return r
    chk = B.check_exact(r["routes"], inst, r["conv"])
    r.update({"vehicles": len(r["routes"]), "exact_ok": chk["ok"], "exact_reason": chk["reason"],
              "distance": None if chk["distance"] is None else round(chk["distance"], 2)})
    r["below_bound"] = chk["ok"] and r["vehicles"] < r["lower"]
    r["reached_final_s"] = r["trace"][-1][0] if r["trace"] else None
    return r


def verdict(ok):
    return "untestable" if ok is None else ("held" if ok else "did not hold")


def tally(recs, misses=MISSES):
    """recs: one dict per (instance, arm) with 'run' (assessed) or 'error'. Scores M0-M6 independently."""
    runs = {}
    for r in recs:
        if r.get("run") and r["run"]["exact_ok"]:
            runs.setdefault(r["instance"], {})[r["arm"]] = r["run"]["vehicles"]
    expected = len(misses) * len(ARMS)
    pairs = {}
    for name, (_, sintef, vrptwl) in misses.items():
        v = runs.get(name, {})
        pairs[name] = {"sintef": sintef, "vrptwl": vrptwl, **{a: v.get(a) for a in ARMS}}

    def both(a, b):
        return [p for p in pairs.values() if p[a] is not None and p[b] is not None]

    fe, fw, we = both("fleet", "eject"), both("fleet", "warm"), both("warm", "eject")
    t = {
        "runs_expected": expected, "runs": len(recs),
        "errors": ["%s/%s" % (r["instance"], r["arm"]) for r in recs if r.get("error")],
        "not_exact": ["%s/%s" % (r["instance"], r["arm"]) for r in recs if r.get("run") and not r["run"]["exact_ok"]],
        "below_bound": ["%s/%s" % (r["instance"], r["arm"]) for r in recs if r.get("run") and r["run"]["below_bound"]],
        "below_sintef": ["%s/%s" % (n, a) for n, p in pairs.items() for a in ARMS
                         if p[a] is not None and p[a] < p["sintef"]],
        "pairs_fleet_eject": len(fe),
        "eject_le_fleet": sum(1 for p in fe if p["eject"] <= p["fleet"]),
        "eject_lt_fleet": sum(1 for p in fe if p["eject"] < p["fleet"]),
        "eject_saved_vehicles": sum(p["fleet"] - p["eject"] for p in fe),
        "eject_eq_sintef": sum(1 for p in pairs.values() if p["eject"] is not None and p["eject"] == p["sintef"]),
        "pairs_fleet_warm": len(fw), "warm_lt_fleet": sum(1 for p in fw if p["warm"] < p["fleet"]),
        "pairs_warm_eject": len(we), "eject_lt_warm": sum(1 for p in we if p["eject"] < p["warm"]),
        "eject_gt_warm": sum(1 for p in we if p["eject"] > p["warm"]),
        "totals": {a: sum(p[a] for p in pairs.values() if p[a] is not None) for a in ARMS},
        "pairs": pairs,
    }
    enough = lambda k: t[k] >= 10  # noqa: E731  (scored on at least 10 compared instances, else untestable)
    t["predictions"] = {
        "M0": verdict(t["runs"] == expected and not t["errors"] and not t["not_exact"] and not t["below_bound"]),
        "M1": verdict(t["eject_le_fleet"] >= 12 if enough("pairs_fleet_eject") else None),
        "M2": verdict(t["eject_lt_fleet"] >= 6 if enough("pairs_fleet_eject") else None),
        "M3": verdict(t["eject_eq_sintef"] >= 4 if enough("pairs_fleet_eject") else None),
        "M4": verdict(t["eject_saved_vehicles"] >= 8 if enough("pairs_fleet_eject") else None),
        "M5": verdict(not t["below_sintef"]),
        "M6": verdict(t["warm_lt_fleet"] >= 4 if enough("pairs_fleet_warm") else None),
        "M7": verdict(t["eject_lt_warm"] >= 4 and t["eject_gt_warm"] <= 1 if enough("pairs_warm_eject") else None),
    }
    return t


def write_sol(routes, distance):
    return B.write_sol(routes, distance)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=300, help="fleet budget per arm and instance")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--only", default="", help="comma-separated instance names (default: all 13)")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    args = ap.parse_args()
    out = os.path.join(args.out_dir, "xltwrm")
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
            inst = X.parse_any(f.read())
        if inst["name"] != name:
            raise SystemExit("id %d is %s, not %s" % (i, inst["name"], name))
        insts[name] = inst
        bound = B.lower_bound(inst, "double")
        vp = os.path.join(vdir, "%s.vrp" % name)
        with open(vp, "w", encoding="utf-8") as f:
            f.write(B.to_vrplib(inst))
        prize = base_prize(inst, "double")
        log("%s: K %d (KC %d, KT %s, clique verified %s), prize %d" % (
            name, bound["k"], bound["kc"], bound["kt"], bound["clique_verified"], prize))
        for arm in ARMS:  # interleaved: the three arms of an instance run close together in time
            rec = {"instance": name, "arm": arm, "bound": bound}
            recs.append(rec)
            tasks.append((rec, (vp, "double", arm, args.seconds, SEED, bound["k"], prize)))

    progress = open(os.path.join(out, "progress.jsonl"), "a", encoding="utf-8")
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(run_one, t): rec for rec, t in tasks}
        for fut in as_completed(futs):
            rec = futs[fut]
            try:
                r = assess(fut.result(), insts[rec["instance"]])
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
                    f.write(write_sol(r["routes"], r["distance"]))
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

    t = tally(recs) if not args.only else tally(recs, {n: MISSES[n] for n in names})
    res = {"pyvrp": "0.14.1 (pinned)", "seed": SEED, "seconds": args.seconds, "conv": "double", "runs": recs,
           "tally": t}
    print(json.dumps(t["predictions"]), flush=True)
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    lines = ["# xltwrm: three route-minimisation loops on the 13 vrptwl/ misses", "",
             "PyVRP 0.14.1, double precision, %d s fleet budget per arm, one CPU per run, seed %d. Every result "
             "re-checked exactly." % (args.seconds, SEED), "",
             "Predictions: `%s`" % json.dumps(t["predictions"]), "",
             "Totals (vehicles, instances with an on-time result): `%s`" % json.dumps(t["totals"]), "",
             "| instance | K | SINTEF | vrptwl | fleet | warm | eject | fleet s | warm s | eject s | eject rounds |"
             " fleet dist | warm dist | eject dist |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    by = {(r["instance"], r["arm"]): r for r in recs}
    for name in names:
        row = [name, str(by[(name, "fleet")]["bound"]["k"]), str(MISSES[name][1]), str(MISSES[name][2])]
        runs = [by[(name, a)].get("run") for a in ARMS]
        row += [str(x["vehicles"]) if x and x["exact_ok"] else ("error" if not x else "not ok") for x in runs]
        row += [str(x.get("reached_final_s")) if x else "" for x in runs]
        e = runs[2]
        row.append(str(e["stats"].get("rounds")) if e else "")
        row += [str(x["distance"]) if x and x["exact_ok"] else "" for x in runs]
        lines.append("| " + " | ".join(row) + " |")
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    if any(r.get("error") for r in recs):
        raise SystemExit("%d run(s) failed" % sum(1 for r in recs if r.get("error")))


if __name__ == "__main__":
    main()
