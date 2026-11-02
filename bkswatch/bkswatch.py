"""Re-check every CVRPLib VRPTW best known solution as published today, against the 2026-10-30 reference.

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.

CVRPLib switched to automatic BKS publishing on 2026-10-28 (solutions are verified on submission and announced in
a daily digest). `vrptwd/` and `vrptwd3/` checked every VRPTW BKS once, under DIMACS (arcs truncated to 0.1) and in
double precision. This script downloads all 356 BKS files again (fresh, never from a cache), checks each with the
unchanged `vrptwd/double_check.py`, compares it with the published reference rows (`vrptwd3/results.json` for the
300 Homberger instances, `vrptwd/results.json` for the 56 Solomon ones) and with the double-precision fleet bound
from `vrptwlb/bounds.csv`, and scores the predictions in expectations.md with score_w().
"""
import argparse
import csv
import json
import os
import time

import double_check as dc

ANNOUNCED = {  # CVRPLib updates page, entry of 2026-11-01 (read 2026-11-02 ~04:15 UTC)
    "C1_10_9": 40278.7,  # Arhan Canli (Quantavane)
    "R1_10_1": 52982.0,  # Jean-Michel Landry (UQAM)
    "R1_10_5": 50365.5,  # Jean-Michel Landry (UQAM)
    "R1_10_9": 49088.1,  # Jean-Michel Landry (UQAM)
}
OTHERS = ["C1_10_9", "R1_10_5", "R1_10_9"]
EXPECTED_ROWS = 356
T0 = time.time()


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def collect_bks_rows(obj, out=None):
    """Every dict in a results.json that describes a CVRPLib BKS check (has instance, routes, dimacs_cost)."""
    if out is None:
        out = {}
    if isinstance(obj, dict):
        if {"instance", "routes", "dimacs_cost"} <= set(obj) and obj.get("source", "cvrplib-bks") == "cvrplib-bks":
            out.setdefault(obj["instance"], obj)
        for v in obj.values():
            collect_bks_rows(v, out)
    elif isinstance(obj, list):
        for v in obj:
            collect_bks_rows(v, out)
    return out


def load_reference(paths):
    """Name -> reference row. Earlier paths win (vrptwd3 before vrptwd)."""
    ref = {}
    for p in paths:
        with open(p, encoding="utf-8") as f:
            rows = collect_bks_rows(json.load(f))
        for k, v in rows.items():
            ref.setdefault(k, v)
    return ref


def load_bounds(path):
    with open(path, encoding="utf-8") as f:
        return {r["instance"]: {"K_double": int(r["K_double"]), "K_dimacs": int(r["K_dimacs"])}
                for r in csv.DictReader(f)}


def compare(row, ref, bounds):
    """Add reference and bound columns to a checked row; `changed` = route count or file cost differs."""
    r = ref.get(row["instance"])
    b = bounds.get(row["instance"], {})
    row["ref_routes"] = r["routes"] if r else None
    row["ref_cost"] = r["dimacs_cost"] if r else None
    row["ref_double_ok"] = r.get("double_ok") if r else None
    row["K_double"] = b.get("K_double")
    row["K_dimacs"] = b.get("K_dimacs")
    row["below_K_double"] = None if row["K_double"] is None or row.get("routes") is None else \
        row["routes"] < row["K_double"]
    if r is None or row.get("file_cost") is None:
        row["changed"] = None
    else:
        row["changed"] = (row["routes"] != r["routes"]) or abs(row["file_cost"] - r["dimacs_cost"]) > 1e-6
    return row


def score_w(rows):
    """Verdicts for W0-W5 (expectations.md)."""
    def verdict(ok):
        return "untestable" if ok is None else ("held" if ok else "did not hold")
    by = {r["instance"]: r for r in rows if r.get("instance")}
    ok_rows = [r for r in rows if not r.get("error")]
    w0 = (len(rows) == EXPECTED_ROWS and len(ok_rows) == EXPECTED_ROWS
          and all(r["dimacs_ok"] and r["dimacs_matches_file"] for r in ok_rows))
    have = all(n in by and not by[n].get("error") for n in ANNOUNCED)
    w1 = None if not have else all(by[n]["changed"] and by[n]["file_cost"] <= ANNOUNCED[n] + 1e-6 for n in ANNOUNCED)
    r1 = by.get("R1_10_1")
    w2 = None if not r1 or r1.get("error") else (r1["routes"] < 100 and not r1["double_ok"])
    w3 = None if not have else sum(1 for n in OTHERS if by[n]["double_ok"]) >= 2
    w4 = None if not have else all(by[n]["routes"] == by[n]["ref_routes"] for n in ANNOUNCED)
    others = [r["instance"] for r in ok_rows if r.get("changed") and r["instance"] not in ANNOUNCED]
    w5 = None if not w0 else len(others) <= 3
    return {"W0": verdict(w0), "W1": verdict(w1), "W2": verdict(w2), "W3": verdict(w3),
            "W4": verdict(w4), "W5": verdict(w5)}


def tally(rows):
    ok_rows = [r for r in rows if not r.get("error")]
    changed = [r for r in ok_rows if r.get("changed")]
    return {
        "rows": len(rows),
        "errors": [r["id"] for r in rows if r.get("error")],
        "dimacs_fail": [r["instance"] for r in ok_rows if not (r["dimacs_ok"] and r["dimacs_matches_file"])],
        "double_late": len([r for r in ok_rows if not r["double_ok"]]),
        "below_K_double": [r["instance"] for r in ok_rows if r.get("below_K_double")],
        "no_reference": [r["instance"] for r in ok_rows if r.get("ref_cost") is None],
        "changed": [r["instance"] for r in changed],
        "changed_double_late": [r["instance"] for r in changed if not r["double_ok"]],
        "changed_route_count": [r["instance"] for r in changed if r["routes"] != r["ref_routes"]],
        "predictions": score_w(rows),
    }


COLS = ["id", "instance", "routes", "file_cost", "dimacs_ok", "dimacs_matches_file", "double_ok", "double_late",
        "double_late_routes", "double_max_late", "double_distance", "K_double", "K_dimacs", "below_K_double",
        "ref_routes", "ref_cost", "ref_double_ok", "changed", "sintef_vehicles", "sintef_distance",
        "double_vs_sintef", "error"]


def write_outputs(rows, out):
    t = tally(rows)
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump({"announced": ANNOUNCED, "tally": t, "rows": rows}, f, indent=1)
    with open(os.path.join(out, "bks.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    lines = ["# CVRPLib VRPTW BKSs re-read and re-checked (DIMACS and double precision)", "",
             "Predictions: `%s`" % json.dumps(t["predictions"]), "",
             "Tally: `%s`" % json.dumps({k: v for k, v in t.items() if k != "predictions"}), "",
             "## BKSs that differ from the 2026-10-30 reference", "",
             "| id | instance | routes (was) | DIMACS cost (was) | double ok (was) | late (routes) | max late | "
             "double distance | K double |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r.get("changed"):
            lines.append("| %s | %s | %s (%s) | %s (%s) | %s (%s) | %s (%s) | %s | %s | %s |" % (
                r["id"], r["instance"], r["routes"], r["ref_routes"], r["file_cost"], r["ref_cost"], r["double_ok"],
                r["ref_double_ok"], r["double_late"], r["double_late_routes"], r["double_max_late"],
                r["double_distance"], r["K_double"]))
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="380-735")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--stamp", required=True, help="folder name for this read of the BKS files, e.g. 20261102")
    ap.add_argument("--ref", nargs="+", default=["vrptwd3_results.json", "vrptwd_results.json"])
    ap.add_argument("--bounds", default="bounds.csv")
    ap.add_argument("--out-dir", default="out")
    args = ap.parse_args()

    src = os.path.join(args.data_dir, "cvrplib-vrptw")
    fresh = os.path.join(src, "bks-" + args.stamp)
    out = os.path.join(args.out_dir, "bkswatch")
    for d in (src, fresh, out):
        os.makedirs(d, exist_ok=True)
    ref = load_reference(args.ref)
    bounds = load_bounds(args.bounds)
    log("reference rows %d, bounds %d, cached files %d" % (len(ref), len(bounds), len(os.listdir(src))))

    rows = []
    for i in dc.parse_ids(args.ids):
        try:
            p = dc.fetch("%s/instance/%s" % (dc.BASE, i), os.path.join(src, "%s.txt" % i))
            s = dc.fetch("%s/bks/%s" % (dc.BASE, i), os.path.join(fresh, "%s.sol" % i))
            with open(p, encoding="utf-8") as f:
                inst = dc.parse_solomon(f.read())
            with open(s, encoding="utf-8") as f:
                routes, cost = dc.parse_sol(f.read())
            row = dc.evaluate("cvrplib-bks-" + args.stamp, routes, cost, inst)
            row["id"] = i
            compare(row, ref, bounds)
        except Exception as e:  # keep going; W0 fails on any error
            row = {"id": i, "instance": None, "error": "%s: %s" % (type(e).__name__, e)}
        rows.append(row)
        log("%s %s: %s routes, cost %s, double_ok=%s, changed=%s%s" % (
            i, row.get("instance"), row.get("routes"), row.get("file_cost"), row.get("double_ok"),
            row.get("changed"), " ERROR " + row["error"] if row.get("error") else ""))

    t = write_outputs(rows, out)
    print("BKSWATCH " + json.dumps(t["predictions"]), flush=True)
    print(json.dumps({k: v for k, v in t.items() if k != "predictions"}), flush=True)


if __name__ == "__main__":
    main()
