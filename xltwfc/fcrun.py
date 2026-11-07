"""xltwfc: the fixed-cost fleet phase (fcsolver.py) at the full limit T(n) on the four xltwfull/ instances.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

The harness is xltwfull/fullrun.py as published (cvrplib-baselines commit 876bd94), imported unchanged: one process
per run, SIGTERM at the limit and SIGKILL 5 s later, the last complete solution printed before the limit counts and is
re-checked exactly, a run whose harness went more than 1 s between two polls is frozen (invalid). The only change is
which program it starts: a launcher in fcbin/ that runs fcsolver.py with the package's interpreter.
Predictions S0-S5 are in expectations.md, fixed and published before any run; addendum-2026-11-07.md (published
before any study run) fixes fcsolver's route conversion and changes the frozen rule from "re-run once" to "re-run
until valid, at most 3 attempts in all".

  python fcrun.py --smoke --data-dir /data --out-dir /out                  # 40 s on n1048; exit 1 unless valid
  python fcrun.py --part a --runs F1,F3 --data-dir /data --out-dir /out
  python fcrun.py --merge results-a.json,results-b.json --full xltwfull-results.json --out-dir /out   # S0-S5
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import fullrun as FR  # noqa: E402  xltwfull/fullrun.py at commit 876bd94

SEED = FR.SEED
IDS = [r[0] for r in FR.RUNS]
KSTAR_TOTAL = sum(r[6] for r in FR.RUNS)  # 173
S3_FLOOR = 199                            # ceil(1.15 x 173)
SMOKE = ("S0smoke", "XLTW-Test-n1048", 40.0)
MAX_ATTEMPTS = 3                          # addendum-2026-11-07: re-run a frozen run until valid, at most 3 in all

LAUNCHER = """#!/usr/bin/env bash
# xltwfc launcher: runs fcsolver.py the way build.sh's ./solver runs solver.py. Usage: solver INSTANCE SECONDS SEED
unset PYTHONPATH PYTHONHOME PYTHONSTARTUP PYTHONUSERBASE PYTHONINSPECT PYTHONWARNINGS PYTHONSAFEPATH
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0 PYTHONNOUSERSITE=1
exec "%s" -s -P "%s" "$@"
"""


def make_launcher(py, here=HERE):
    d = os.path.join(here, "fcbin")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "solver")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(LAUNCHER % (py, os.path.join(here, "fcsolver.py")))
    os.chmod(path, 0o755)
    return d


def use_fc_solver():
    """Point the unchanged harness at fcbin/solver (run_one starts HERE/solver with cwd HERE)."""
    import lock
    py = lock.build_python(HERE)
    if not py:
        raise SystemExit("fcrun.py: no build (lib/XLTW_BUILD.json missing): run build.sh first")
    FR.HERE = make_launcher(py)
    return py


def reexec_under_build_python():
    import lock
    exe = lock.build_python(HERE)
    if not exe or os.environ.get("XLTW_FCRUN_REEXEC"):
        return
    if os.path.realpath(exe) == os.path.realpath(sys.executable):
        return
    print("fcrun.py: re-running under the build's interpreter %s (was %s)" % (exe, sys.executable), flush=True)
    os.environ["XLTW_FCRUN_REEXEC"] = "1"
    os.execv(exe, [exe, os.path.abspath(__file__)] + sys.argv[1:])


def fc_ran(rec):
    st = rec.get("solver_stats") or {}
    return st.get("fixed_cost") is not None and (st.get("fc_iterations") or 0) > 0


def run_until_unfrozen(run, attempts=MAX_ATTEMPTS):
    """Call run() until its record is not frozen, at most `attempts` times; earlier frozen tries are kept."""
    tries = []
    rec = run()
    while rec.get("harness_frozen") and len(tries) + 1 < attempts:
        tries.append(rec)
        rec = run()
    if tries:
        rec["frozen_tries"] = tries
    rec["attempts"] = len(tries) + 1
    return rec


def smoke(a):
    import conformance as C
    out = os.path.join(a.out_dir, "xltwfc")
    os.makedirs(os.path.join(out, "logs-smoke"), exist_ok=True)
    use_fc_solver()
    rid, name, limit = SMOKE
    path = C.find(a.data_dir, name)
    if path is None:
        raise SystemExit("smoke: %s not found under %s" % (name, a.data_dir))
    rec = run_until_unfrozen(lambda: FR.run_one(rid, path, limit, SEED, os.path.join(out, "logs-smoke"),
                                                os.path.join(out, "smoke-sols")))
    ok = FR.valid(rec) and fc_ran(rec)
    rec["smoke_ok"] = ok
    with open(os.path.join(out, "smoke.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(rec, f, indent=1)
    print(json.dumps({k: rec.get(k) for k in ("id", "instance", "vehicles", "distance", "self_stopped", "exit",
                                             "feasible", "cost_line_ok", "attempts", "smoke_ok")}), flush=True)
    print("solver stats: %s" % json.dumps(rec.get("solver_stats")), flush=True)
    if not ok:
        raise SystemExit("smoke run not valid or the fixed-cost phase did not run: not starting the study")


def run_part(a):
    import conformance as C
    out = os.path.join(a.out_dir, "xltwfc")
    logs = os.path.join(out, "logs-%s" % a.part)
    sols = os.path.join(out, "sols")
    os.makedirs(logs, exist_ok=True)
    use_fc_solver()
    net = C.network_reachable()
    build = C.build_info()
    print("network reachable: %s; build: %s" % (net, json.dumps(build)), flush=True)
    res = {"part": a.part, "network_reachable": net, "build": build, "runs": [], "python": sys.version.split()[0],
           "executable": sys.executable, "solver": "fcsolver.py"}
    res_path = os.path.join(out, "results-%s.json" % a.part)
    for rid in [s.strip() for s in a.runs.split(",") if s.strip()]:
        _, name, customers, *_ = FR.BY_ID[rid]
        limit = FR.limit_for(customers)
        path = C.find(a.data_dir, name)
        if path is None:
            rec = {"id": rid, "instance": name, "error": "instance file not found"}
        elif net or not build.get("pins_ok"):
            rec = {"id": rid, "instance": name, "error": "not run: network reachable or build pins not ok"}
        else:
            try:
                rec = run_until_unfrozen(lambda: FR.run_one(rid, path, limit, SEED, logs, sols))
                FR.attach_reference(rec)
            except Exception as e:  # noqa: BLE001 - recorded
                rec = {"id": rid, "instance": name, "error": repr(e)}
        res["runs"].append(rec)
        with open(res_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(res, f, indent=1)
        st = rec.get("solver_stats") or {}
        print(json.dumps({"id": rid, "instance": name, "vehicles": rec.get("vehicles"), "k_star": rec.get("k_star"),
                          "first_vehicles": st.get("first_vehicles"), "fixed_cost": st.get("fixed_cost"),
                          "distance": rec.get("distance"), "self_stopped": rec.get("self_stopped"),
                          "harness_frozen": rec.get("harness_frozen"), "attempts": rec.get("attempts"),
                          "peak_gb": rec.get("peak_gb"), "watchdog": rec.get("watchdog"),
                          "error": rec.get("error")}), flush=True)
    write_md(os.path.join(out, "results-%s.md" % a.part), res)


def verdict(ok):
    return "held" if ok else "did not hold"


def score(build, net, recs, full_recs):
    """S0-S5 of expectations.md. recs: this study's counted runs; full_recs: xltwfull's merged runs."""
    by = {r["id"]: r for r in recs}
    vs = [by[i] for i in IDS if i in by]
    gate = (all(i in by for i in IDS) and not net and build.get("tag") is not None and build.get("pins_ok") is True
            and all(FR.valid(r) and fc_ran(r) for r in vs))
    p = {"S0": verdict(gate)}
    if not gate:
        for k in ("S1", "S2", "S3", "S4", "S5"):
            p[k] = "untestable (S0 failed)"
        return p
    fb = {r["id"]: r for r in full_recs if FR.valid(r)}
    common = [i for i in IDS if i in fb]
    if len(common) >= 3:
        fc_tot = sum(by[i]["vehicles"] for i in common)
        full_tot = sum(fb[i]["vehicles"] for i in common)
        p["S1"] = verdict(fc_tot <= full_tot)
        p["S2"] = verdict(sum(1 for i in common if by[i]["vehicles"] < fb[i]["vehicles"]) >= 2)
    else:
        p["S1"] = p["S2"] = "untestable (xltwfull has a valid run on fewer than 3 of the 4)"
    p["S3"] = verdict(sum(r["vehicles"] for r in vs) >= S3_FLOOR)
    p["S4"] = verdict(not any(r["vehicles"] == r["k_star"] for r in vs))
    p["S5"] = verdict(all(r["peak_gb"] is not None and r["peak_gb"] <= 0.6 and not r.get("watchdog") for r in vs))
    return p


def write_md(path, res, full=None):
    full = full or {}
    L = ["# xltwfc: fixed-cost fleet phase at the full limit T(n) on the four xltwfull/ instances", "",
         "Seed %d. Network reachable during the runs: %s. Build: %s, Python %s; pins ok: %s." % (
             SEED, res["network_reachable"], res["build"].get("tag"), res["build"].get("python"),
             res["build"].get("pins_ok")), "",
         "Predictions (expectations.md): `%s`" % json.dumps(res.get("predictions")), "",
         "| run | instance | n | limit s | vehicles | xltwfull vehicles | part a (T/30) | K* | first feasible | F | "
         "final count first printed at s | distance | xltwfull distance | slack s | peak GB | attempts | valid |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["runs"]:
        if r.get("error"):
            L.append("| %s | %s | | | error: %s | | | | | | | | | | | | |" % (r["id"], r.get("instance"), r["error"]))
            continue
        st = r.get("solver_stats") or {}
        f = full.get(r["id"]) or {}
        L.append("| %s | %s | %d | %.1f | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["id"], r["instance"], r["customers"], r["limit"], r["vehicles"], f.get("vehicles"),
            r.get("part_a_vehicles"), r.get("k_star"), st.get("first_vehicles"), st.get("fixed_cost"),
            r.get("final_vehicles_first_at"), r["distance"], f.get("distance"), r["slack"], r["peak_gb"],
            r.get("attempts", 1), FR.valid(r) and fc_ran(r)))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


def merge(a):
    recs, nets, builds = [], [], []
    for p in a.merge.split(","):
        with open(p, encoding="utf-8") as f:
            doc = json.load(f)
        nets.append(doc["network_reachable"])
        builds.append(doc["build"])
        recs.extend(doc["runs"])
    ids = [r["id"] for r in recs]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate run ids across parts: %s" % ids)
    with open(a.full, encoding="utf-8") as f:
        full_recs = json.load(f)["runs"]
    build = dict(builds[0])
    build["pins_ok"] = all(b.get("pins_ok") is True for b in builds)
    res = {"part": "merged", "network_reachable": any(nets), "build": build,
           "runs": sorted(recs, key=lambda r: r["id"]), "parts": a.merge.split(","), "full": a.full}
    res["predictions"] = score(build, res["network_reachable"], res["runs"], full_recs)
    out = os.path.join(a.out_dir, "xltwfc")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1)
    write_md(os.path.join(out, "results.md"), res, {r["id"]: r for r in full_recs})
    print(json.dumps(res["predictions"]), flush=True)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--part", default="a")
    ap.add_argument("--runs", default="F1,F2,F3,F4")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--merge", default="")
    ap.add_argument("--full", default="xltwfull-results.json")
    a = ap.parse_args()
    if a.merge:
        merge(a)
        return
    reexec_under_build_python()
    if a.smoke:
        smoke(a)
        return
    run_part(a)


if __name__ == "__main__":
    main()
