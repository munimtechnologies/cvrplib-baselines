"""xltwfull: the packaged xltw-solver at the challenge's full time limit T(n) on four capacity-free XLTW-Test instances.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

Question: is the baseline's large vehicle gap on capacity-free instances (part a of `xltwrun/`, limits T(n)/30) mostly
an effect of the short limit? This runs the published package (cvrplib-baselines commit 19c7eb6; solver 0.1.0, the
same method as `xltwrun/solver.py`) exactly as the challenge runs algorithms: one process per run, `./solver INSTANCE
T(n) SEED`, SIGTERM at the limit, SIGKILL 5 s later, the last complete solution printed before the limit counts and is
re-checked exactly (nearest-integer arcs). Same seed as part a. Predictions F0-F5 are in expectations.md, fixed and
published before any run.

  python fullrun.py --part a --runs F1,F3 --data-dir /data --out-dir /out
  python fullrun.py --merge results-a.json,results-b.json --out-dir /out      # scores F0-F5 once, on all four
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

SEED = 20261104
GRACE = 5.0
# id, instance, customers, part-a vehicles, part-a distance, K, K* (xltwen/results.json)
RUNS = [
    ("F1", "XLTW-Test-n1234", 1233, 35, 89250, 7, 27),
    ("F2", "XLTW-Test-n1421", 1420, 72, 139809, 16, 47),
    ("F3", "XLTW-Test-n1608", 1607, 113, 118365, 7, 81),
    ("F4", "XLTW-Test-n1841", 1840, 29, 85369, 4, 18),
]
BY_ID = {r[0]: r for r in RUNS}


def limit_for(customers):
    """T(n) = 1,800 x n / 1,000 s, n = number of customers."""
    return round(1.8 * customers, 1)


def reexec_under_build_python():
    import lock
    exe = lock.build_python(HERE)
    if not exe or os.environ.get("XLTW_FULLRUN_REEXEC"):
        return
    if os.path.realpath(exe) == os.path.realpath(sys.executable):
        return
    print("fullrun.py: re-running under the build's interpreter %s (was %s)" % (exe, sys.executable), flush=True)
    os.environ["XLTW_FULLRUN_REEXEC"] = "1"
    os.execv(exe, [exe, os.path.abspath(__file__)] + sys.argv[1:])


def trajectory(blocks):
    """[(t, routes, cost)] -> [{t, vehicles, cost}] of every printed solution."""
    return [{"t": round(t, 2), "vehicles": len(routes), "cost": cost} for t, routes, cost in blocks]


def first_time_at(traj, vehicles):
    for p in traj:
        if p["vehicles"] == vehicles:
            return p["t"]
    return None


def run_one(rid, path, limit, seed, log_dir, sol_dir):
    import conformance as C
    import xltwbase as B
    import xltwlb as X
    with open(path, encoding="utf-8") as f:
        inst = X.parse_any(f.read())
    err_path = os.path.join(log_dir, "%s.stderr.txt" % rid)
    lines = []
    with open(err_path, "w", encoding="utf-8") as err:
        t0 = time.monotonic()
        p = subprocess.Popen([os.path.join(HERE, "solver"), path, "%.1f" % limit, str(seed)], cwd=HERE,
                             stdout=subprocess.PIPE, stderr=err, text=True, bufsize=1)

        def reader():
            for line in p.stdout:
                lines.append((time.monotonic() - t0, line))
        th = threading.Thread(target=reader, daemon=True)
        th.start()
        termed = killed = None
        peak = None
        prev, max_gap = 0.0, 0.0
        while p.poll() is None:
            el = time.monotonic() - t0
            max_gap, prev = max(max_gap, el - prev), el
            h = C.vmhwm_gb(p.pid)
            if h is not None:
                peak = max(peak or 0.0, h)
            if termed is None and el >= limit:
                p.send_signal(signal.SIGTERM)
                termed = el
            elif termed is not None and killed is None and el >= limit + GRACE:
                p.kill()
                killed = el
            time.sleep(0.05)
        wall = time.monotonic() - t0
        th.join(timeout=30)
    blocks, bad, numbering = C.parse(lines)
    on_time = [b for b in blocks if b[0] <= limit]
    rec = {"id": rid, "instance": inst["name"], "customers": len(inst["rows"]) - 1, "limit": limit, "seed": seed,
           "exit": p.returncode, "wall": round(wall, 3), "self_stopped": termed is None,
           "sigterm_at": None if termed is None else round(termed, 3),
           "sigkill_at": None if killed is None else round(killed, 3),
           "stdout_lines": len(lines), "bad_lines": bad[:5], "bad_line_count": len(bad),
           "numbering_errors": numbering, "blocks": len(blocks), "blocks_after_limit": len(blocks) - len(on_time),
           "last_cost_at": round(on_time[-1][0], 3) if on_time else None,
           "slack": round(limit - on_time[-1][0], 3) if on_time else None,
           "peak_gb": None if peak is None else round(peak, 3),
           "max_poll_gap": round(max_gap, 3), "harness_frozen": max_gap > 1.0,
           "trajectory": trajectory(on_time)}
    stats, watchdog = None, None
    with open(err_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("XLTW_SOLVER_STATS "):
                stats = json.loads(line[len("XLTW_SOLVER_STATS "):])
            elif line.startswith("XLTW_WATCHDOG "):
                watchdog = line.strip()
    rec["solver_stats"] = stats
    rec["watchdog"] = watchdog
    if on_time:
        t, routes, cost = on_time[-1]
        chk = B.check_exact(routes, inst, "round")
        rec.update({"feasible": bool(chk["ok"]), "reason": chk["reason"], "vehicles": len(routes),
                    "distance": None if chk["distance"] is None else int(round(chk["distance"])),
                    "cost_line": cost,
                    "cost_line_ok": chk["distance"] is not None and abs(cost - chk["distance"]) < 1e-6})
        os.makedirs(sol_dir, exist_ok=True)
        with open(os.path.join(sol_dir, "%s.sol" % inst["name"]), "w", encoding="ascii", newline="\n") as f:
            f.write("".join("Route #%d: %s\n" % (i + 1, " ".join(map(str, r))) for i, r in enumerate(routes)))
            f.write("Cost: %d\n" % int(round(cost)))
    else:
        rec.update({"feasible": False, "reason": "no solution before the limit", "vehicles": None, "distance": None,
                    "cost_line": None, "cost_line_ok": False})
    return rec


def valid(r):
    """A valid protocol run: not frozen, stopped by itself with exit 0, counted solution exact and clean stdout."""
    return (r is not None and not r.get("error") and not r["harness_frozen"] and r["self_stopped"]
            and r["exit"] == 0 and r["feasible"] and r["cost_line_ok"] and r["bad_line_count"] == 0
            and r["numbering_errors"] == 0)


def attach_reference(rec):
    _, _, _, va, da, k, ks = BY_ID[rec["id"]]
    rec.update({"part_a_vehicles": va, "part_a_distance": da, "k": k, "k_star": ks})
    if rec.get("vehicles") is not None:
        rec["final_vehicles_first_at"] = first_time_at(rec["trajectory"], rec["vehicles"])
    return rec


def verdict(ok):
    return "held" if ok else "did not hold"


def score(build, net, recs):
    """F0-F5 of expectations.md, on the counted record of each of F1-F4 (a re-run replaces a frozen first try)."""
    by = {r["id"]: r for r in recs}
    have = all(i in by for i in BY_ID)
    vs = [by[i] for i in BY_ID if i in by]
    gate = (have and not net and build.get("tag") is not None and build.get("pins_ok") is True
            and all(valid(r) for r in vs))
    p = {"F0": verdict(gate)}
    if not gate:
        for k in ("F1", "F2", "F3", "F4", "F5"):
            p[k] = "untestable (F0 failed)"
        return p
    tot = sum(r["vehicles"] for r in vs)
    p["F1"] = verdict(all(r["vehicles"] <= r["part_a_vehicles"] for r in vs))
    p["F2"] = verdict(tot <= 224)
    p["F3"] = verdict(tot >= 208)
    p["F4"] = verdict(sum(1 for r in vs if r["vehicles"] == r["k_star"]) <= 1)
    p["F5"] = verdict(all(r["peak_gb"] is not None and r["peak_gb"] <= 0.6 and not r.get("watchdog") for r in vs))
    return p


def write_md(path, res):
    L = ["# xltwfull: xltw-solver at the full limit T(n) on four capacity-free XLTW-Test instances", "",
         "Seed %d. Network reachable during the runs: %s. Build: %s, Python %s; pins ok: %s." % (
             SEED, res["network_reachable"], res["build"].get("tag"), res["build"].get("python"),
             res["build"].get("pins_ok")), "",
         "Predictions (expectations.md): `%s`" % json.dumps(res.get("predictions")), "",
         "| run | instance | n | limit s | vehicles | part a (T/30) | K | K* | final count first printed at s | "
         "distance | part a distance | fleet solves | self-stopped | slack s | peak GB | frozen | valid |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["runs"]:
        if r.get("error"):
            L.append("| %s | %s | | | error: %s | | | | | | | | | | | | |" % (r["id"], r.get("instance"), r["error"]))
            continue
        st = r.get("solver_stats") or {}
        L.append("| %s | %s | %d | %.1f | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["id"], r["instance"], r["customers"], r["limit"], r["vehicles"], r["part_a_vehicles"], r["k"],
            r["k_star"], r.get("final_vehicles_first_at"), r["distance"], r["part_a_distance"],
            st.get("fleet_solves"), r["self_stopped"], r["slack"], r["peak_gb"], r["harness_frozen"], valid(r)))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


def run_part(a):
    import conformance as C
    out = os.path.join(a.out_dir, "xltwfull")
    logs = os.path.join(out, "logs-%s" % a.part)
    sols = os.path.join(out, "sols")
    os.makedirs(logs, exist_ok=True)
    net = C.network_reachable()
    build = C.build_info()
    print("network reachable: %s; build: %s" % (net, json.dumps(build)), flush=True)
    res = {"part": a.part, "network_reachable": net, "build": build, "runs": [], "python": sys.version.split()[0],
           "executable": sys.executable}
    res_path = os.path.join(out, "results-%s.json" % a.part)
    ids = [s.strip() for s in a.runs.split(",") if s.strip()]
    for rid in ids:
        _, name, customers, *_ = BY_ID[rid]
        limit = limit_for(customers)
        path = C.find(a.data_dir, name)
        if path is None:
            rec = {"id": rid, "instance": name, "error": "instance file not found"}
        elif net or not build.get("pins_ok"):
            rec = {"id": rid, "instance": name, "error": "not run: network reachable or build pins not ok"}
        else:
            try:
                rec = run_one(rid, path, limit, SEED, logs, sols)
                if rec["harness_frozen"]:  # pre-registered: re-run once, unchanged; a frozen re-run is no valid run
                    first = rec
                    rec = run_one(rid, path, limit, SEED, logs, sols)
                    rec["frozen_first_try"] = first
                attach_reference(rec)
            except Exception as e:  # noqa: BLE001 - recorded
                rec = {"id": rid, "instance": name, "error": repr(e)}
        res["runs"].append(rec)
        with open(res_path, "w", encoding="utf-8", newline="\n") as f:  # after every run, so a timeout keeps the rest
            json.dump(res, f, indent=1)
        print(json.dumps({k: rec.get(k) for k in ("id", "instance", "vehicles", "part_a_vehicles", "k_star",
                                                 "distance", "self_stopped", "harness_frozen", "peak_gb",
                                                 "watchdog", "error")}), flush=True)
    write_md(os.path.join(out, "results-%s.md" % a.part), res)


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
    build = dict(builds[0])
    build["pins_ok"] = all(b.get("pins_ok") is True for b in builds)
    res = {"part": "merged", "network_reachable": any(nets), "build": build,
           "runs": sorted(recs, key=lambda r: r["id"]), "parts": a.merge.split(",")}
    res["predictions"] = score(build, res["network_reachable"], res["runs"])
    out = os.path.join(a.out_dir, "xltwfull")
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
    ap.add_argument("--runs", default="F1,F2,F3,F4")
    ap.add_argument("--merge", default="")
    a = ap.parse_args()
    if a.merge:
        merge(a)
        return
    reexec_under_build_python()
    run_part(a)


if __name__ == "__main__":
    main()
