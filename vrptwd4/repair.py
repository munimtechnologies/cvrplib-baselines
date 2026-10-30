"""Repair the CVRPLib VRPTW BKSs that arrive late in double precision, with no more routes than the BKS.

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.

vrptwd/ and vrptwd3/ found 90 of CVRPLib's 356 Solomon and Homberger best known solutions (BKSs) that are
feasible under the DIMACS convention (arcs truncated to 0.1) but arrive late somewhere when travel times are
computed in double precision: 8 of 56 Solomon, 82 of 300 Homberger. This script asks whether each can be
made double-feasible without adding a route. For every BKS that the unchanged vrptwd/double_check.py finds
late, PyVRP 0.14.1 starts from the BKS with the fleet capped at the BKS's route count, on a "safe" integer
version of the instance: every number is multiplied by 1,000 and rounded UP. Instance data are integers, so
only travel times change, each by less than 0.001, and never downwards; a schedule that is on time in the
scaled instance is therefore on time in double precision. Every result is re-checked by double_check.py
(and under DIMACS) before it counts. A failure to repair within the time budget is not a proof that no
repair exists. Predictions: expectations.md, scored by score_r() below.
"""
import argparse
import json
import os
import statistics
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "vrptwd"))  # in the repository; in a job it sits beside this file
import double_check as dc  # noqa: E402

SCALE = 1000
EXPECTED_LATE = 90
TIGHT = ("C1", "R1", "RC1")  # short horizon, many routes
T0 = time.time()


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def ceil_scaled(vals):
    """PyVRP round_func: x 1,000, rounded up, so scaled travel times never undercut the exact ones."""
    import numpy as np
    return np.ceil(SCALE * np.asarray(vals, dtype=np.float64)).astype(np.int64)


def family(name):
    """'RC1_10_1' -> 'RC1'; 'RC105' -> 'RC1'; 'R211' -> 'R2'."""
    if "_" in name:
        return name.split("_")[0]
    head = name.rstrip("0123456789")
    return head + name[len(head)]


def budget(customers):
    """Wall-clock seconds per instance: 60 s up to 200 customers, then 0.3 s per customer."""
    return max(60, int(0.3 * customers))


def to_vrplib(inst, vehicles):
    """VRPLIB text for pyvrp.read with the fleet capped; Solomon customer i is VRPLIB node i + 1."""
    rows = inst["rows"]
    lines = ["NAME : %s" % inst["name"], "TYPE : VRPTW",
             "DIMENSION : %d" % len(rows), "VEHICLES : %d" % vehicles,
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


def _value(attr):
    return attr() if callable(attr) else attr


def route_clients(route):
    """Solomon customer numbers (client index + 1) of a PyVRP 0.14 route."""
    return [_value(a.idx) + 1 for a in route.schedule() if _value(a.is_client)]


def run_one(task):
    import pyvrp
    from pyvrp.stop import MaxRuntime

    vrplib_path, routes, seconds, seed = task
    data = pyvrp.read(vrplib_path, round_func=ceil_scaled)
    init = pyvrp.Solution(data, [[c - 1 for c in r] for r in routes])
    t0 = time.time()
    res = pyvrp.solve(data, stop=MaxRuntime(seconds), seed=seed, collect_stats=False,
                      display=False, initial_solution=init)
    best = res.best
    return {"seconds": seconds, "seed": seed,
            "init_feasible": init.is_feasible(), "init_time_warp": _value(getattr(init, "time_warp", None)),
            "feasible": best.is_feasible(), "scaled_distance": best.distance(),
            "routes": [route_clients(r) for r in best.routes()],
            "iterations": res.num_iterations, "wall_seconds": round(time.time() - t0, 1)}


def assess(rec, r, inst):
    """Independent checks of one PyVRP result; adds the fields the tally reads."""
    dbl = dc.check_double(r["routes"], inst)
    ok_d, _, cost_d = dc.check_dimacs(r["routes"], inst)
    n = len(r["routes"])
    r.update({"num_routes": n, "double_ok": dbl["ok"], "double_reason": dbl["reason"],
              "double_distance": None if dbl["distance"] is None else round(dbl["distance"], 2),
              "dimacs_ok": ok_d, "dimacs_cost": None if cost_d is None else cost_d / 10.0,
              "pyvrp_agrees": r["feasible"] == dbl["ok"] or not r["feasible"]})
    r["repaired"] = bool(dbl["ok"] and n <= rec["bks_routes"])
    r["delta_pct"] = (round(100.0 * (dbl["distance"] - rec["bks_double_distance"]) / rec["bks_double_distance"], 4)
                      if r["repaired"] else None)
    rec_s = dc.SINTEF.get(rec["instance"])
    r["sintef"] = list(rec_s) if rec_s else None
    r["vs_sintef"] = dc.versus_sintef(n, dbl["distance"], rec_s) if r["repaired"] and rec_s else None
    return r


def score_r(t):
    """Verdicts for R0-R6 (expectations.md) from the tally."""
    def verdict(ok):
        return "untestable" if ok is None else ("held" if ok else "did not hold")
    med = t["median_delta_pct"]
    rate_w = t["repaired_wide"] / t["late_wide"] if t["late_wide"] else None
    rate_t = t["repaired_tight"] / t["late_tight"] if t["late_tight"] else None
    return {
        "R0": verdict(t["bks"] == 356 and t["late"] == EXPECTED_LATE and not t["dimacs_hygiene_fail"]
                      and not t["run_errors"] and not t["pyvrp_disagreements"]),
        "R1": verdict(t["repaired"] >= 70),
        "R2": verdict(t["repaired_wide"] >= 45),
        "R3": verdict(None if med is None else 0.0 <= med <= 0.5),
        "R4": verdict(None if t["r1_10_1_late"] is None else not t["r1_10_1_repaired"]),
        "R5": verdict(None if rate_w is None or rate_t is None else rate_w >= rate_t),
        "R6": verdict(None if not t["sintef_compared"] else not t["beats_sintef"]),
    }


def tally_recs(recs):
    late = [r for r in recs if not r["bks_double_ok"]]
    runs = [r for r in late if r.get("run")]
    rep = [r for r in runs if r["run"]["repaired"]]
    wide = [r for r in late if r["family"] not in TIGHT]
    tight = [r for r in late if r["family"] in TIGHT]
    deltas = [r["run"]["delta_pct"] for r in rep]
    r1 = [r for r in late if r["instance"] == "R1_10_1"]
    t = {
        "bks": len(recs),
        "dimacs_hygiene_fail": [r["instance"] for r in recs if not r["bks_dimacs_matches_file"]],
        "late": len(late),
        "late_solomon": sum(1 for r in late if "_" not in r["instance"]),
        "late_homberger": sum(1 for r in late if "_" in r["instance"]),
        "run_errors": [r["instance"] for r in late if r.get("error")],
        "pyvrp_disagreements": [r["instance"] for r in runs if not r["run"]["pyvrp_agrees"]],
        "repaired": len(rep),
        "repaired_fewer_routes": [r["instance"] for r in rep if r["run"]["num_routes"] < r["bks_routes"]],
        "not_repaired": [r["instance"] for r in late if not (r.get("run") and r["run"]["repaired"])],
        "late_wide": len(wide), "repaired_wide": sum(1 for r in wide if r.get("run") and r["run"]["repaired"]),
        "late_tight": len(tight), "repaired_tight": sum(1 for r in tight if r.get("run") and r["run"]["repaired"]),
        "median_delta_pct": round(statistics.median(deltas), 4) if deltas else None,
        "max_delta_pct": max(deltas) if deltas else None,
        "min_delta_pct": min(deltas) if deltas else None,
        "repaired_also_dimacs_ok": sum(1 for r in rep if r["run"]["dimacs_ok"]),
        "r1_10_1_late": True if r1 else None,
        "r1_10_1_repaired": bool(r1 and r1[0].get("run") and r1[0]["run"]["repaired"]),
        "sintef_compared": {r["instance"]: r["run"]["vs_sintef"] for r in rep if r["run"]["vs_sintef"]},
        "beats_sintef": [r["instance"] for r in rep if r["run"]["vs_sintef"] == "better"],
    }
    by = {}
    for r in late:
        g = by.setdefault(r["family"], [0, 0])
        g[0] += 1
        g[1] += 1 if r.get("run") and r["run"]["repaired"] else 0
    t["by_family"] = {k: by[k] for k in sorted(by)}
    t["predictions"] = score_r(t)
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="380-735")
    ap.add_argument("--seed", type=int, default=20261030)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--max-seconds", type=int, default=0, help="cap per instance (tests only)")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    args = ap.parse_args()

    src = os.path.join(args.data_dir, "cvrplib-vrptw")
    conv = os.path.join(args.data_dir, "vrplib-fleetcap")
    out = os.path.join(args.out_dir, "vrptwd4")
    sols = os.path.join(out, "sols")
    for d in (src, conv, sols):
        os.makedirs(d, exist_ok=True)
    log("cached files in data volume: %d" % len(os.listdir(src)))

    recs, insts, tasks = [], {}, []
    for i in dc.parse_ids(args.ids):
        p = dc.fetch("%s/instance/%s" % (dc.BASE, i), os.path.join(src, "%s.txt" % i))
        s = dc.fetch("%s/bks/%s" % (dc.BASE, i), os.path.join(src, "%s.sol" % i))
        with open(p, encoding="utf-8") as f:
            inst = dc.parse_solomon(f.read())
        with open(s, encoding="utf-8") as f:
            routes, cost = dc.parse_sol(f.read())
        row = dc.evaluate("cvrplib-bks", routes, cost, inst)
        n = len(inst["rows"]) - 1
        rec = {"id": i, "instance": inst["name"], "family": family(inst["name"]), "customers": n,
               "bks_routes": len(routes), "bks_dimacs_cost": row["dimacs_cost"],
               "bks_dimacs_matches_file": row["dimacs_matches_file"], "bks_double_ok": row["double_ok"],
               "bks_double_distance": row["double_distance"], "bks_double_late": row["double_late"],
               "bks_double_max_late": row["double_max_late"]}
        recs.append(rec)
        insts[i] = inst
        if not row["double_ok"]:
            vp = os.path.join(conv, "%s.vrp" % inst["name"])
            with open(vp, "w", encoding="utf-8") as f:
                f.write(to_vrplib(inst, len(routes)))
            secs = budget(n) if not args.max_seconds else min(budget(n), args.max_seconds)
            tasks.append((rec, (vp, routes, secs, args.seed)))
    log("BKSs read: %d; late in double precision: %d" % (len(recs), len(tasks)))

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
            if r["repaired"]:
                with open(os.path.join(sols, "%s.sol" % rec["instance"]), "w", encoding="utf-8") as f:
                    f.write(write_sol(r["routes"], r["double_distance"]))
            del r["routes"]
            rec["run"] = r
            log("%s: BKS %d routes, late %d; PyVRP feasible=%s, %d routes, double_ok=%s, %s (%s%%), %d it" % (
                rec["instance"], rec["bks_routes"], rec["bks_double_late"], r["feasible"], r["num_routes"],
                r["double_ok"], r["double_distance"], r["delta_pct"], r["iterations"]))

    tally = tally_recs(recs)
    late = [r for r in recs if not r["bks_double_ok"]]
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump({"scale": SCALE, "rounding": "ceil", "eps": dc.EPS, "seed": args.seed,
                   "pyvrp": "0.14.1 (pinned)", "tally": tally, "late": late}, f, indent=1)
    lines = ["# Repairing the CVRPLib VRPTW BKSs that are late in double precision", "",
             "PyVRP 0.14.1 from the BKS, fleet capped at the BKS's routes, travel times x1,000 rounded up, "
             "seed %d. Every result re-checked by vrptwd/double_check.py." % args.seed, "",
             "Predictions: `%s`" % json.dumps(tally["predictions"]), "",
             "Tally: `%s`" % json.dumps({k: v for k, v in tally.items() if k != "predictions"}), "",
             "| id | instance | customers | BKS routes | BKS DIMACS cost | BKS double distance | late | max late "
             "| s | routes | double ok | double distance | vs BKS double % | SINTEF | vs SINTEF |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in late:
        x = r.get("run")
        if not x:
            lines.append("| %s | %s | %d | %d | %s | %s | %s | %s | error | | | | | | |" % (
                r["id"], r["instance"], r["customers"], r["bks_routes"], r["bks_dimacs_cost"],
                r["bks_double_distance"], r["bks_double_late"], r["bks_double_max_late"]))
            continue
        lines.append("| %s | %s | %d | %d | %s | %s | %s | %s | %d | %d | %s | %s | %s | %s | %s |" % (
            r["id"], r["instance"], r["customers"], r["bks_routes"], r["bks_dimacs_cost"],
            r["bks_double_distance"], r["bks_double_late"], r["bks_double_max_late"], x["seconds"],
            x["num_routes"], x["double_ok"], x["double_distance"], x["delta_pct"],
            "" if not x["sintef"] else "%d / %s" % tuple(x["sintef"]), x["vs_sintef"] or ""))
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps(tally), flush=True)


if __name__ == "__main__":
    main()
