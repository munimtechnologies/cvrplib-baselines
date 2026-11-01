"""Same-machine control for xltwbase: the old 300 s + 300 s split against the bound-aware budget, side by side.

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.

`xltwbase-study-v1` compared its budget (fleet search stopped at the xltwlb bound K, every leftover second to
`solve`) with an earlier run (`vrptwl-fleet-v1`) on a shared machine that turned out to be 1.5 to 5.6 times slower in
iterations per second, so its 6.41% median distance reduction mixes the budget change with machine speed. This
script runs both budgets in one job, on the same machine, interleaved, on the 8 E instances and R1_10_1:

- arm 'split' (the `vrptwl/` protocol): `minimise_fleet`'s loop stopped at PyVRP's own capacity bound KC, at most
  300 s, then `solve` for exactly 300 s;
- arm 'bound' (`xltwbase.py`): the same loop stopped at K = max(L2, time-window clique), then `solve` for the rest of
  the 600 s.

Same PyVRP 0.14.1, seed, VRPLIB copy and x1,000 rounded-up scaling as both earlier runs; every result re-checked
exactly in double precision by `xltwbase.check_exact`. Predictions K0 to K5 are in expectations.md and scored by
`score_k()`.
"""
import argparse
import json
import os
import statistics
import time
import traceback
from concurrent.futures import ProcessPoolExecutor

import xltwbase as B
import xltwlb as X

INSTANCES = B.GROUPS["E"] + B.GROUPS["T"]
ARMS = ("split", "bound")
CROSS_RUN_MEDIAN = 6.406  # xltwbase-study-v1, e_median_reduction_pct against vrptwl-fleet-v1


def run_arm(task):
    """task = (vrplib path, arm, seconds, seed, lower). Returns the run dict (as xltwbase.run_one) plus arm."""
    import pyvrp
    from pyvrp.stop import MaxRuntime

    vrplib_path, arm, seconds, seed, lower = task
    data = pyvrp.read(vrplib_path, round_func=B.ROUND_FUNCS["double"])
    t0 = time.time()
    vt, fleet_seconds, solves, at_bound = B.fleet_down(data, lower, seconds / 2.0, seed)
    if arm == "split":
        left = seconds / 2.0
    else:
        left = max(seconds - (time.time() - t0), 1.0)
    res = pyvrp.solve(data.replace(vehicle_types=[vt]), stop=MaxRuntime(left), seed=seed, collect_stats=False,
                      display=False)
    best = res.best
    return {"arm": arm, "conv": "double", "seconds": seconds, "seed": seed, "lower": lower,
            "fleet": vt.num_available, "fleet_seconds": fleet_seconds, "fleet_solves": solves,
            "stopped_at_bound": at_bound, "solve_seconds": round(left, 1), "feasible": best.is_feasible(),
            "routes": [B.route_clients(r) for r in best.routes()], "iterations": res.num_iterations,
            "wall_seconds": round(time.time() - t0, 1)}


def tally(recs):
    """recs: one dict per (instance, arm) with 'run' or 'error'. Returns per-instance pairs and predictions."""
    by = {}
    for r in recs:
        by.setdefault(r["instance"], {})[r["arm"]] = r
    pairs = {}
    for name in INSTANCES:
        s, b = (by.get(name, {}).get(a) for a in ARMS)
        if not (s and b and s.get("run") and b.get("run")):
            continue
        rs, rb = s["run"], b["run"]
        p = {"group": B.group_of(name),
             "split_vehicles": rs["vehicles"], "bound_vehicles": rb["vehicles"],
             "split_distance": rs["distance"], "bound_distance": rb["distance"],
             "split_exact_ok": rs["exact_ok"], "bound_exact_ok": rb["exact_ok"],
             "split_fleet_seconds": rs["fleet_seconds"], "bound_fleet_seconds": rb["fleet_seconds"],
             "split_solve_seconds": rs["solve_seconds"], "bound_solve_seconds": rb["solve_seconds"],
             "split_iterations": rs["iterations"], "bound_iterations": rb["iterations"]}
        p["split_it_per_s"] = round(rs["iterations"] / max(rs["solve_seconds"], 1e-9), 1)
        p["bound_it_per_s"] = round(rb["iterations"] / max(rb["solve_seconds"], 1e-9), 1)
        p["speed_ratio"] = round(p["split_it_per_s"] / max(p["bound_it_per_s"], 1e-9), 3)
        if rs["distance"] and rb["distance"] is not None:
            p["reduction_pct"] = round(100.0 * (rs["distance"] - rb["distance"]) / rs["distance"], 3)
        else:
            p["reduction_pct"] = None
        pairs[name] = p
    runs = [r for r in recs if r.get("run")]
    e = [pairs[n] for n in B.GROUPS["E"] if n in pairs]
    e_same = [p for p in e if p["split_vehicles"] == p["bound_vehicles"] and p["reduction_pct"] is not None]
    t = {"runs_expected": 2 * len(INSTANCES), "runs": len(runs),
         "run_errors": ["%s/%s" % (r["instance"], r["arm"]) for r in recs if r.get("error")],
         "exact_ok": sum(1 for r in runs if r["run"]["exact_ok"]),
         "below_bound": ["%s/%s" % (r["instance"], r["arm"]) for r in runs if r["run"]["below_bound"]],
         "pairs": pairs, "pairs_complete": len(pairs),
         "same_vehicles": sum(1 for p in pairs.values() if p["split_vehicles"] == p["bound_vehicles"]),
         "e_compared": len(e_same),
         "e_not_longer": sum(1 for p in e_same if p["bound_distance"] <= p["split_distance"] + 0.005),
         "e_median_reduction_pct": round(statistics.median(p["reduction_pct"] for p in e_same), 3)
         if e_same else None,
         "e_median_speed_ratio": round(statistics.median(p["speed_ratio"] for p in e), 3) if e else None,
         "cross_run_median_pct": CROSS_RUN_MEDIAN,
         "r1_10_1": pairs.get("R1_10_1")}
    t["predictions"] = score_k(t)
    return t


def score_k(t):
    """Verdicts for K0-K5 (expectations.md)."""
    def verdict(ok):
        return "untestable" if ok is None else ("held" if ok else "did not hold")
    n = len(INSTANCES)
    med, r1 = t["e_median_reduction_pct"], t["r1_10_1"]
    full = t["e_compared"] == len(B.GROUPS["E"])
    return {
        "K0": verdict(t["runs"] == t["runs_expected"] and not t["run_errors"] and t["exact_ok"] == t["runs_expected"]
                      and not t["below_bound"] and t["pairs_complete"] == n and t["same_vehicles"] == n),
        "K1": verdict(t["e_not_longer"] == len(B.GROUPS["E"]) if full else None),
        "K2": verdict(None if med is None or not full else med >= 1.0),
        "K3": verdict(None if med is None or not full else med < CROSS_RUN_MEDIAN / 2.0),
        "K4": verdict(None if not r1 or r1["reduction_pct"] is None or r1["split_vehicles"] != r1["bound_vehicles"]
                      else r1["reduction_pct"] >= 2.0),
        "K5": verdict(None if t["e_median_speed_ratio"] is None else 0.8 <= t["e_median_speed_ratio"] <= 1.25),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=600)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--only", default="", help="comma-separated instance names (testing)")
    args = ap.parse_args()
    out = os.path.join(args.out_dir, "xltwctl")
    vdir, sols = os.path.join(out, "vrplib"), os.path.join(out, "sols")
    for d in (vdir, sols):
        os.makedirs(d, exist_ok=True)
    src = os.path.join(args.data_dir, "cvrplib-vrptw")
    os.makedirs(src, exist_ok=True)
    names = [n for n in INSTANCES if not args.only or n in args.only.split(",")]

    recs, tasks = [], []
    for name in names:
        i = B.VRPTWL[name][0]
        p = B.fetch("%s/instance/%s" % (B.BASE, i), os.path.join(src, "%d.txt" % i))
        with open(p, encoding="utf-8") as f:
            inst = X.parse_any(f.read())
        if inst["name"] != name:
            raise SystemExit("id %d is %s, not %s" % (i, inst["name"], name))
        bound = B.lower_bound(inst, "double")
        vp = os.path.join(vdir, "%s.vrp" % name)
        with open(vp, "w", encoding="utf-8") as f:
            f.write(B.to_vrplib(inst))
        B.log("%s: bound %s" % (name, json.dumps(bound)))
        for arm in ARMS:  # interleaved, so both arms of an instance run at the same time
            rec = {"instance": name, "arm": arm, "group": B.group_of(name), "bound": bound}
            lower = bound["kc"] if arm == "split" else bound["k"]
            recs.append(rec)
            tasks.append((rec, inst, (vp, arm, args.seconds, B.SEED, lower)))
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [(rec, inst, pool.submit(run_arm, t)) for rec, inst, t in tasks]
        for rec, inst, fut in futures:
            try:
                r = B.assess(fut.result(), inst)
            except Exception:
                rec["error"] = traceback.format_exc()
                B.log("%s/%s ERROR %s" % (rec["instance"], rec["arm"], rec["error"]))
                continue
            if r["exact_ok"]:
                with open(os.path.join(sols, "%s.%s.sol" % (rec["instance"], rec["arm"])), "w",
                          encoding="utf-8") as f:
                    f.write(B.write_sol(r["routes"], r["distance"]))
            del r["routes"]
            rec["run"] = r
            B.log("%s/%s: lower %d, %d vehicles, exact_ok=%s, distance %s, fleet %.1f s, solve %.1f s, %d it" % (
                rec["instance"], rec["arm"], r["lower"], r["vehicles"], r["exact_ok"], r["distance"],
                r["fleet_seconds"], r["solve_seconds"], r["iterations"]))

    t = tally(recs)
    res = {"pyvrp": "0.14.1 (pinned)", "seed": B.SEED, "seconds": args.seconds, "workers": args.workers,
           "runs": recs, "tally": t}
    print(json.dumps(t["predictions"]), flush=True)
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    lines = ["# xltwctl: 300 s + 300 s split against the bound-aware budget, same machine, same job", "",
             "PyVRP 0.14.1, one CPU per run, seed %d, %d s per run, %d runs at a time." % (
                 B.SEED, args.seconds, args.workers), "",
             "Predictions: `%s`" % json.dumps(t["predictions"]), "",
             "E median reduction (bound vs split): %s%% (cross-run figure in xltwbase/: %s%%); "
             "E median speed ratio split/bound: %s" % (t["e_median_reduction_pct"], CROSS_RUN_MEDIAN,
                                                     t["e_median_speed_ratio"]), "",
             "| instance | group | vehicles split | vehicles bound | distance split | distance bound | reduction % "
             "| fleet s split | fleet s bound | solve s split | solve s bound | it/s split | it/s bound |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name in names:
        p = t["pairs"].get(name)
        if not p:
            lines.append("| %s | %s | error | | | | | | | | | | |" % (name, B.group_of(name)))
            continue
        lines.append("| %s | %s | %d | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            name, p["group"], p["split_vehicles"], p["bound_vehicles"], p["split_distance"], p["bound_distance"],
            p["reduction_pct"], p["split_fleet_seconds"], p["bound_fleet_seconds"], p["split_solve_seconds"],
            p["bound_solve_seconds"], p["split_it_per_s"], p["bound_it_per_s"]))
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    if t["run_errors"]:
        raise SystemExit("%d run(s) failed" % len(t["run_errors"]))


if __name__ == "__main__":
    main()
