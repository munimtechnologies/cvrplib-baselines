"""xltwdet: is the work-budget solver (detsolver.py) deterministic for its seed, and what does it cost?

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

Three XLTW-Test instances, one seed, a 120 s limit. On each instance, in this order:

  W1  work budget (detsolver.py), alone
  T1  wall clock (the package's ./solver, solver 0.1.0), alone
  W2  work budget, alone again
  W3  work budget, while a CPU hog (busy 10 ms of every 50 ms) shares the job's one CPU
  T2  wall clock, with the same hog

Every run goes through xltwfull's harness as published (cvrplib-baselines commit 876bd94, `run_one`, imported
unchanged): one process per run, SIGTERM at the limit, SIGKILL 5 s later, the last complete solution printed before
the limit counts and is re-checked exactly. A frozen run (harness poll gap above 1 s) is re-run until it is not
frozen, at most 3 attempts in all. Each counted solution is kept in sols/<run>/ with its SHA-256. Predictions D0-D6
are in expectations.md, published before any run; this script scores them at the end of the same job.

  python detrun.py --data-dir /data --out-dir /out
"""
import argparse
import contextlib
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import fullrun as FR  # noqa: E402  xltwfull/fullrun.py at commit 876bd94

SEED = 20261107
LIMIT = 120.0
INSTANCES = [("A", "XLTW-Test-n1048"), ("B", "XLTW-Test-n1094"), ("C", "XLTW-Test-n1234")]
PLAN = [("W1", "work", False), ("T1", "time", False), ("W2", "work", False), ("W3", "work", True),
        ("T2", "time", True)]
MAX_ATTEMPTS = 3
D3_RANGE = (0.30, 0.85)

HOG = ("import time\n"
       "while True:\n"
       "    t = time.perf_counter()\n"
       "    while time.perf_counter() - t < 0.010:\n"
       "        pass\n"
       "    time.sleep(0.040)\n")

LAUNCHER = """#!/usr/bin/env bash
# xltwdet launcher: runs detsolver.py the way build.sh's ./solver runs solver.py. Usage: solver INSTANCE SECONDS SEED
unset PYTHONPATH PYTHONHOME PYTHONSTARTUP PYTHONUSERBASE PYTHONINSPECT PYTHONWARNINGS PYTHONSAFEPATH
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0 PYTHONNOUSERSITE=1
exec "%s" -s -P "%s" "$@"
"""


def make_launcher(py, here=HERE):
    d = os.path.join(here, "detbin")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "solver")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(LAUNCHER % (py, os.path.join(here, "detsolver.py")))
    os.chmod(path, 0o755)
    return d


def reexec_under_build_python():
    import lock
    exe = lock.build_python(HERE)
    if not exe or os.environ.get("XLTW_DETRUN_REEXEC"):
        return
    if os.path.realpath(exe) == os.path.realpath(sys.executable):
        return
    print("detrun.py: re-running under the build's interpreter %s (was %s)" % (exe, sys.executable), flush=True)
    os.environ["XLTW_DETRUN_REEXEC"] = "1"
    os.execv(exe, [exe, os.path.abspath(__file__)] + sys.argv[1:])


@contextlib.contextmanager
def hog(on):
    if not on:
        yield None
        return
    p = subprocess.Popen([sys.executable, "-c", HOG])
    try:
        yield p
    finally:
        p.kill()
        p.wait(timeout=30)


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


def solution_sha(sol_dir, instance):
    path = os.path.join(sol_dir, "%s.sol" % instance)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def stopped_on_clock(r):
    st = r.get("solver_stats") or {}
    return bool(st.get("clock_stop")) or bool(st.get("term_stop"))


def verdict(ok):
    return "held" if ok else "did not hold"


def score(build, net, recs):
    """D0-D6 of expectations.md."""
    by = {r["id"]: r for r in recs}
    ids = ["%s-%s" % (i, w) for i, _ in INSTANCES for w, _, _ in PLAN]
    gate = (all(i in by for i in ids) and not net and build.get("tag") is not None and build.get("pins_ok") is True
            and all(FR.valid(by[i]) for i in ids))
    p = {"D0": verdict(gate)}
    if not gate:
        for k in ("D1", "D2", "D3", "D4", "D5", "D6"):
            p[k] = "untestable (D0 failed)"
        return p
    keys = [i for i, _ in INSTANCES]
    work = [by["%s-%s" % (k, w)] for k in keys for w in ("W1", "W2", "W3")]
    p["D1"] = verdict(all(
        by[k + "-W1"]["solution_sha256"] is not None
        and by[k + "-W1"]["solution_sha256"] == by[k + "-W2"]["solution_sha256"] == by[k + "-W3"]["solution_sha256"]
        for k in keys))
    p["D2"] = verdict(not any(stopped_on_clock(r) for r in work))
    lo, hi = D3_RANGE
    alone = [by["%s-%s" % (k, w)] for k in keys for w in ("W1", "W2")]
    p["D3"] = verdict(all(r.get("solver_stats") and lo * r["limit"] <= r["solver_stats"]["elapsed"] <= hi * r["limit"]
                          for r in alone))
    p["D4"] = verdict(sum(1 for k in keys if by[k + "-T1"]["solution_sha256"] != by[k + "-T2"]["solution_sha256"])
                      >= 1)
    p["D5"] = verdict(sum(by[k + "-W1"]["vehicles"] for k in keys) <= sum(by[k + "-T1"]["vehicles"] for k in keys) + 1)
    p["D6"] = verdict(all(by[i]["peak_gb"] is not None and by[i]["peak_gb"] <= 0.6 and not by[i].get("watchdog")
                          for i in ids))
    return p


def write_md(path, res):
    L = ["# xltwdet: work budget vs wall clock, three XLTW-Test instances, seed %d, limit %.0f s" % (SEED, LIMIT), "",
         "Network reachable during the runs: %s. Build: %s, Python %s; pins ok: %s." % (
             res["network_reachable"], res["build"].get("tag"), res["build"].get("python"),
             res["build"].get("pins_ok")), "",
         "Predictions (expectations.md): `%s`" % json.dumps(res.get("predictions")), "",
         "| run | instance | mode | hog | vehicles | distance | solution sha256 (first 12) | elapsed s | budget | "
         "fleet it | distance it | clock stop | peak GB | attempts | valid |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["runs"]:
        if r.get("error"):
            L.append("| %s | %s | | | error: %s | | | | | | | | | | |" % (r["id"], r.get("instance"), r["error"]))
            continue
        st = r.get("solver_stats") or {}
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["id"], r["instance"], r["mode"], r["hog"], r["vehicles"], r["distance"],
            (r.get("solution_sha256") or "")[:12], st.get("elapsed"), st.get("budget"), st.get("fleet_iterations"),
            st.get("iterations"), st.get("clock_stop"), r["peak_gb"], r.get("attempts"), FR.valid(r)))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


def main():
    import conformance as C
    import lock
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--only", default="", help="comma-separated instance keys (A,B,C); for trials only")
    a = ap.parse_args()
    reexec_under_build_python()
    py = lock.build_python(HERE)
    if not py:
        raise SystemExit("detrun.py: no build (lib/XLTW_BUILD.json missing): run build.sh first")
    work_dir = make_launcher(py)
    time_dir = HERE  # build.sh's ./solver: the package as published
    out = os.path.join(a.out_dir, "xltwdet")
    logs = os.path.join(out, "logs")
    os.makedirs(logs, exist_ok=True)
    net = C.network_reachable()
    build = C.build_info()
    print("network reachable: %s; build: %s" % (net, json.dumps(build)), flush=True)
    res = {"seed": SEED, "limit": LIMIT, "network_reachable": net, "build": build, "runs": [],
           "python": sys.version.split()[0], "executable": sys.executable}
    only = set(s.strip() for s in a.only.split(",") if s.strip())
    for key, name in INSTANCES:
        if only and key not in only:
            continue
        path = C.find(a.data_dir, name)
        for wid, mode, with_hog in PLAN:
            rid = "%s-%s" % (key, wid)
            sol_dir = os.path.join(out, "sols", rid)
            if path is None:
                rec = {"id": rid, "instance": name, "error": "instance file not found"}
            elif net or not build.get("pins_ok"):
                rec = {"id": rid, "instance": name, "error": "not run: network reachable or build pins not ok"}
            else:
                FR.HERE = work_dir if mode == "work" else time_dir
                try:
                    with hog(with_hog):
                        rec = run_until_unfrozen(lambda: FR.run_one(rid, path, LIMIT, SEED, logs, sol_dir))
                    rec.update(mode=mode, hog=with_hog, solution_sha256=solution_sha(sol_dir, name))
                except Exception as e:  # noqa: BLE001 - recorded
                    rec = {"id": rid, "instance": name, "error": repr(e)}
            res["runs"].append(rec)
            with open(os.path.join(out, "results.json"), "w", encoding="utf-8", newline="\n") as f:
                json.dump(res, f, indent=1)
            st = rec.get("solver_stats") or {}
            print(json.dumps({"id": rid, "vehicles": rec.get("vehicles"), "distance": rec.get("distance"),
                              "sha": (rec.get("solution_sha256") or "")[:12], "elapsed": st.get("elapsed"),
                              "budget": st.get("budget"), "clock_stop": st.get("clock_stop"),
                              "frozen": rec.get("harness_frozen"), "attempts": rec.get("attempts"),
                              "error": rec.get("error")}), flush=True)
    res["predictions"] = score(build, net, res["runs"]) if not only else "not scored (--only)"
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1)
    write_md(os.path.join(out, "results.md"), res)
    print(json.dumps(res["predictions"]), flush=True)


if __name__ == "__main__":
    main()
