"""Merge the interrupted xltwctl-v1 log with xltwctl-v2's results and score K0-K5 once, unchanged.

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.

`xltwctl-v1` was stopped from outside after 56 minutes (exit 143, SIGTERM; its 120-minute limit was not reached). By
then 7 of the 9 instances had both arms finished and logged. `xltwctl-v2` runs both arms of the two missing instances
(C1_10_4, R1_10_1) in one job, interleaved, exactly as v1 did. This script takes v1's finished pairs from its log
(`v1_log.txt`, copied verbatim from v1's stdout), drops every v1 record of an instance that v2 re-ran, adds v2's runs
from its results.json, and scores the predictions with the same `xltwctl.tally()` / `score_k()`.

Each pair (split against bound on one instance) comes from one job; different pairs may come from different jobs.
"""
import argparse
import json
import os
import re

import xltwctl as C

LINE = re.compile(r"\]\s+(\S+)/(split|bound): lower (\d+), (\d+) vehicles, exact_ok=(True|False), distance (\S+), "
                  r"fleet ([\d.]+) s, solve ([\d.]+) s, (\d+) it\s*$")


def parse_log(text):
    """One record per finished run line in an xltwctl log, in the shape tally() reads."""
    recs = []
    for line in text.splitlines():
        m = LINE.search(line)
        if not m:
            continue
        name, arm, lower, veh, ok, dist, fleet, solve, it = m.groups()
        lower, veh, ok = int(lower), int(veh), ok == "True"
        run = {"lower": lower, "vehicles": veh, "exact_ok": ok,
               "distance": None if dist == "None" else float(dist),
               "fleet_seconds": float(fleet), "solve_seconds": float(solve), "iterations": int(it),
               "below_bound": ok and veh < lower}
        recs.append({"instance": name, "arm": arm, "run": run, "source": "v1"})
    return recs


def merge(prior, later):
    """Records of `later` replace every `prior` record of the same instance."""
    redone = {r["instance"] for r in later}
    out = [r for r in prior if r["instance"] not in redone]
    for r in later:
        r = dict(r)
        r.setdefault("source", "v2")
        out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prior", default="v1_log.txt")
    ap.add_argument("--results", default="/out/xltwctl/results.json")
    ap.add_argument("--out-dir", default="/out/xltwctl")
    args = ap.parse_args()
    with open(args.prior, encoding="utf-8") as f:
        prior = parse_log(f.read())
    with open(args.results, encoding="utf-8") as f:
        later = json.load(f)["runs"]
    recs = merge(prior, later)
    t = C.tally(recs)
    src = {}
    for r in recs:
        src.setdefault(r["instance"], set()).add(r.get("source", "v2"))
    for name, p in t["pairs"].items():
        p["source"] = "+".join(sorted(src[name]))
    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "merged.json"), "w", encoding="utf-8") as f:
        json.dump({"note": "v1 pairs from its log; v2 pairs from its results.json", "runs": recs, "tally": t}, f,
                  indent=1)
    lines = ["# xltwctl merged: v1 (interrupted) pairs + v2 pairs, scored once", "",
             "Predictions: `%s`" % json.dumps(t["predictions"]), "",
             "E median reduction (bound vs split): %s%% (cross-run figure in xltwbase/: %s%%); "
             "E median speed ratio split/bound: %s" % (t["e_median_reduction_pct"], C.CROSS_RUN_MEDIAN,
                                                     t["e_median_speed_ratio"]), "",
             "| instance | group | job | vehicles split | vehicles bound | distance split | distance bound "
             "| reduction % | it/s split | it/s bound | speed ratio |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name in C.INSTANCES:
        p = t["pairs"].get(name)
        if not p:
            lines.append("| %s | | missing | | | | | | | | |" % name)
            continue
        lines.append("| %s | %s | %s | %d | %d | %s | %s | %s | %s | %s | %s |" % (
            name, p["group"], p["source"], p["split_vehicles"], p["bound_vehicles"], p["split_distance"],
            p["bound_distance"], p["reduction_pct"], p["split_it_per_s"], p["bound_it_per_s"], p["speed_ratio"]))
    with open(os.path.join(args.out_dir, "merged.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("MERGED " + json.dumps(t["predictions"]), flush=True)
    print("E median reduction %s%%, speed ratio %s, pairs %d" % (
        t["e_median_reduction_pct"], t["e_median_speed_ratio"], t["pairs_complete"]), flush=True)


if __name__ == "__main__":
    main()
