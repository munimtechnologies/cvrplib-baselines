"""xltwff: does a longer fleet phase buy vehicles at the full limit? xltw-solver 0.1.0 with one change (the fleet
phase gets 0.8 of the time left instead of 0.5), run exactly as xltwfull ran the unchanged solver, on the same four
capacity-free XLTW-Test instances with the same seed.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

Every run uses xltwfull's own harness (`fullrun.run_one`, cvrplib-baselines commit 876bd94): one process per run,
`./solver INSTANCE T(n) SEED`, SIGTERM at the limit, SIGKILL 5 s later, the last complete solution printed before the
limit counts and is re-checked exactly. Predictions H0-H5 are in expectations.md, fixed and published before any run.

  python ffrun.py --part a --runs H1,H3 --data-dir /data --out-dir /out
  python ffrun.py --merge results-a.json,results-b.json --ref xltwfull-results.json --out-dir /out   # scores H0-H5
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

SEED = 20261104
FLEET_FRAC = 0.8
# id, xltwfull id, instance, customers, K, K* (xltwen/results.json)
RUNS = [
    ("H1", "F1", "XLTW-Test-n1234", 1233, 7, 27),
    ("H2", "F2", "XLTW-Test-n1421", 1420, 16, 47),
    ("H3", "F3", "XLTW-Test-n1608", 1607, 7, 81),
    ("H4", "F4", "XLTW-Test-n1841", 1840, 4, 18),
]
BY_ID = {r[0]: r for r in RUNS}
DIST_TOL = 0.01      # H4: at most 1% longer where the vehicle counts are equal
SAVE_MAX = 4         # H3: the four together save at most 4 vehicles
PEAK_GB = 0.6        # H5


def limit_for(customers):
    """T(n) = 1,800 x n / 1,000 s, n = number of customers (as in xltwfull)."""
    return round(1.8 * customers, 1)


def reexec_under_build_python():
    import lock
    exe = lock.build_python(HERE)
    if not exe or os.environ.get("XLTW_FFRUN_REEXEC"):
        return
    if os.path.realpath(exe) == os.path.realpath(sys.executable):
        return
    print("ffrun.py: re-running under the build's interpreter %s (was %s)" % (exe, sys.executable), flush=True)
    os.environ["XLTW_FFRUN_REEXEC"] = "1"
    os.execv(exe, [exe, os.path.abspath(__file__)] + sys.argv[1:])


def valid(r):
    """A valid protocol run, exactly xltwfull's rule: not frozen, stopped by itself with exit 0, counted solution
    exact and clean stdout."""
    return bool(r is not None and not r.get("error") and not r.get("harness_frozen", True) and r.get("self_stopped")
                and r.get("exit") == 0 and r.get("feasible") and r.get("cost_line_ok")
                and r.get("bad_line_count") == 0 and r.get("numbering_errors") == 0)


def verdict(ok):
    return "held" if ok else "did not hold"


def pairs(recs, ref_runs):
    """[(H record, F record)] in H1..H4 order; a missing record is None."""
    by = {r["id"]: r for r in recs}
    ref = {r["id"]: r for r in ref_runs}
    return [(by.get(h), ref.get(f)) for h, f, *_ in RUNS]


def score(build, net, recs, ref, patched):
    """H0-H5 of expectations.md. `ref` is xltwfull's merged results.json (the unchanged solver)."""
    ps = pairs(recs, ref.get("runs", []))
    gate = (patched is True and not net and build.get("tag") is not None and build.get("pins_ok") is True
            and all(valid(h) for h, _ in ps) and all(valid(f) for _, f in ps))
    p = {"H0": verdict(gate)}
    if not gate:
        for k in ("H1", "H2", "H3", "H4", "H5"):
            p[k] = "untestable (H0 failed)"
        return p
    sh = sum(h["vehicles"] for h, _ in ps)
    sf = sum(f["vehicles"] for _, f in ps)
    p["H1"] = verdict(sh <= sf)
    p["H2"] = verdict(any(h["vehicles"] < f["vehicles"] for h, f in ps))
    p["H3"] = verdict(sh >= sf - SAVE_MAX)
    eq = [(h, f) for h, f in ps if h["vehicles"] == f["vehicles"]]
    if not eq:
        p["H4"] = "untestable (no instance with equal vehicle counts)"
    else:
        p["H4"] = verdict(all(h["distance"] <= (1.0 + DIST_TOL) * f["distance"] for h, f in eq))
    p["H5"] = verdict(all(h.get("peak_gb") is not None and h["peak_gb"] <= PEAK_GB and not h.get("watchdog")
                          for h, _ in ps))
    return p


def compare_rows(recs, ref_runs):
    rows = []
    for h, f in pairs(recs, ref_runs):
        if h is None:
            continue
        row = {"id": h["id"], "instance": h.get("instance"), "h_vehicles": h.get("vehicles"),
               "f_vehicles": None if f is None else f.get("vehicles"), "h_distance": h.get("distance"),
               "f_distance": None if f is None else f.get("distance"), "k_star": BY_ID[h["id"]][5]}
        st = h.get("solver_stats") or {}
        row.update({"h_fleet_seconds": st.get("fleet_seconds"), "h_fleet_solves": st.get("fleet_solves"),
                    "h_final_first_at": h.get("final_vehicles_first_at")})
        if f is not None:
            fs = f.get("solver_stats") or {}
            row.update({"f_fleet_seconds": fs.get("fleet_seconds"), "f_fleet_solves": fs.get("fleet_solves"),
                        "f_final_first_at": f.get("final_vehicles_first_at")})
        rows.append(row)
    return rows


def first_time_at(traj, vehicles):
    for p in traj:
        if p["vehicles"] == vehicles:
            return p["t"]
    return None


def write_md(path, res):
    L = ["# xltwff: xltw-solver with a 0.8 fleet phase at the full limit T(n), four capacity-free XLTW-Test instances",
         "",
         "Seed %d. Fleet fraction %.1f (0.5 in xltw-solver 0.1.0). Network reachable during the runs: %s. Build: %s, "
         "Python %s; pins ok: %s; solver.py patched: %s." % (
             SEED, FLEET_FRAC, res["network_reachable"], res["build"].get("tag"), res["build"].get("python"),
             res["build"].get("pins_ok"), res.get("patched")), "",
         "Predictions (expectations.md): `%s`" % json.dumps(res.get("predictions")), "",
         "| run | instance | n | limit s | vehicles | K* | final count first printed at s | distance | fleet s | "
         "fleet solves | self-stopped | slack s | peak GB | frozen | valid |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["runs"]:
        if r.get("error"):
            L.append("| %s | %s | | | error: %s | | | | | | | | | | |" % (r["id"], r.get("instance"), r["error"]))
            continue
        st = r.get("solver_stats") or {}
        L.append("| %s | %s | %d | %.1f | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["id"], r["instance"], r["customers"], r["limit"], r["vehicles"], BY_ID[r["id"]][5],
            r.get("final_vehicles_first_at"), r["distance"], st.get("fleet_seconds"), st.get("fleet_solves"),
            r["self_stopped"], r["slack"], r["peak_gb"], r["harness_frozen"], valid(r)))
    if res.get("compare"):
        L += ["", "Against xltwfull (same instances, seed and harness; fleet fraction 0.5):", "",
              "| run | instance | K* | vehicles 0.8 | vehicles 0.5 | distance 0.8 | distance 0.5 | fleet s 0.8 | "
              "fleet s 0.5 | final count first at 0.8 | at 0.5 |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for c in res["compare"]:
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                c["id"], c["instance"], c["k_star"], c["h_vehicles"], c.get("f_vehicles"), c["h_distance"],
                c.get("f_distance"), c.get("h_fleet_seconds"), c.get("f_fleet_seconds"), c.get("h_final_first_at"),
                c.get("f_final_first_at")))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


def read_patched():
    try:
        with open(os.path.join(HERE, "pkg-manifest.json"), encoding="utf-8") as f:
            return json.load(f).get("patched") is True
    except (OSError, ValueError):
        return False


def solver_has_patch():
    with open(os.path.join(HERE, "solver.py"), encoding="utf-8") as f:
        src = f.read()
    return "FLEET_FRAC = 0.8  # xltwff" in src and "\nFLEET_FRAC = 0.5\n" not in src


def run_part(a):
    import conformance as C
    import fullrun  # xltwfull's harness at commit 876bd94, unchanged
    out = os.path.join(a.out_dir, "xltwff")
    logs = os.path.join(out, "logs-%s" % a.part)
    sols = os.path.join(out, "sols")
    os.makedirs(logs, exist_ok=True)
    net = C.network_reachable()
    build = C.build_info()
    patched = read_patched() and solver_has_patch()
    print("network reachable: %s; patched: %s; build: %s" % (net, patched, json.dumps(build)), flush=True)
    res = {"part": a.part, "network_reachable": net, "build": build, "patched": patched, "runs": [],
           "python": sys.version.split()[0], "executable": sys.executable}
    res_path = os.path.join(out, "results-%s.json" % a.part)
    ids = [s.strip() for s in a.runs.split(",") if s.strip()]
    for rid in ids:
        _, _, name, customers, _, _ = BY_ID[rid]
        limit = limit_for(customers)
        path = C.find(a.data_dir, name)
        if path is None:
            rec = {"id": rid, "instance": name, "error": "instance file not found"}
        elif net or not build.get("pins_ok") or not patched:
            rec = {"id": rid, "instance": name, "error": "not run: network reachable, build pins not ok or not patched"}
        else:
            try:
                rec = fullrun.run_one(rid, path, limit, SEED, logs, sols)
                if rec["harness_frozen"]:  # pre-registered: re-run once, unchanged; a frozen re-run is no valid run
                    first = rec
                    rec = fullrun.run_one(rid, path, limit, SEED, logs, sols)
                    rec["frozen_first_try"] = first
                if rec.get("vehicles") is not None:
                    rec["final_vehicles_first_at"] = first_time_at(rec["trajectory"], rec["vehicles"])
            except Exception as e:  # noqa: BLE001 - recorded
                rec = {"id": rid, "instance": name, "error": repr(e)}
        res["runs"].append(rec)
        with open(res_path, "w", encoding="utf-8", newline="\n") as f:  # after every run, so a timeout keeps the rest
            json.dump(res, f, indent=1)
        print(json.dumps({k: rec.get(k) for k in ("id", "instance", "vehicles", "distance", "self_stopped",
                                                 "harness_frozen", "peak_gb", "watchdog", "error")}), flush=True)
    write_md(os.path.join(out, "results-%s.md" % a.part), res)


def merge(a):
    recs, nets, builds, patched = [], [], [], []
    for p in a.merge.split(","):
        with open(p, encoding="utf-8") as f:
            doc = json.load(f)
        nets.append(doc["network_reachable"])
        builds.append(doc["build"])
        patched.append(doc.get("patched") is True)
        recs.extend(doc["runs"])
    ids = [r["id"] for r in recs]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate run ids across parts: %s" % ids)
    with open(a.ref, encoding="utf-8") as f:
        ref = json.load(f)
    build = dict(builds[0])
    build["pins_ok"] = all(b.get("pins_ok") is True for b in builds)
    res = {"part": "merged", "network_reachable": any(nets), "build": build, "patched": all(patched),
           "runs": sorted(recs, key=lambda r: r["id"]), "parts": a.merge.split(","), "ref": a.ref}
    res["predictions"] = score(build, res["network_reachable"], res["runs"], ref, res["patched"])
    res["compare"] = compare_rows(res["runs"], ref.get("runs", []))
    out = os.path.join(a.out_dir, "xltwff")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1)
    write_md(os.path.join(out, "results.md"), res)
    print(json.dumps(res["predictions"]), flush=True)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--part", default="a")
    ap.add_argument("--runs", default="H1,H2,H3,H4")
    ap.add_argument("--merge", default="")
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    if a.merge:
        if not a.ref:
            ap.error("--merge needs --ref (xltwfull's merged results.json)")
        merge(a)
        return
    reexec_under_build_python()
    run_part(a)


if __name__ == "__main__":
    main()
