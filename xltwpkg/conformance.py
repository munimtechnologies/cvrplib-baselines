"""Protocol conformance check of the built xltw-solver package, with the network off.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

Runs `./solver INSTANCE SECONDS SEED` exactly as CVRPLib's VRPTW Challenge says it runs algorithms (one process per
run, SIGTERM at the limit, SIGKILL five seconds later, stdout read as it arrives) on a few of the smallest XLTW-Test
instances, and scores the pre-registered predictions C0-C8 of expectations.md. Every counted solution is checked
exactly (xltwbase.check_exact, nearest-integer rounding), and every stdout line is checked against the format.

0.1.1: if the build recorded a different interpreter (lib/XLTW_BUILD.json "executable"), this script re-runs itself
under that one first, because it imports numpy from lib/ to check the counted solutions. Nothing else changed.
"""
import argparse
import glob
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

GRACE = 5.0
RUNS = [  # id, instance, limit (s), seed
    ("R1", "XLTW-Test-n1048", 60.0, 1),
    ("R2", "XLTW-Test-n1094", 60.0, 1),
    ("R3", "XLTW-Test-n1141", 60.0, 1),
    ("R4", "XLTW-Test-n1094", 60.0, 7),
    ("R5", "XLTW-Test-n1094", 60.0, 7),
    ("R6", "XLTW-Test-n1234", 120.0, 3),
]
RUNSETS = {
    "main": RUNS,
    # The b2 run that a stuck PyVRP call kept past its limit: same instance, seed and limit (T(n)/30).
    "n8575": [("W1", "XLTW-Test-n8575", 514.44, 20261104)],
}
ROUTE = re.compile(r"^Route #([1-9][0-9]*): ?([0-9]+( [0-9]+)*)?$")
COST = re.compile(r"^Cost: ?(-?[0-9]+(\.[0-9]+)?)$")
SHIP = ["README.md", "Makefile", "build.sh", "lock.py", "wheels.lock", "solver.py", "xltwbase.py", "xltwlb.py",
        "test_pkg.py", "conformance.py", "fetch_helpers.py", "expectations.md", "addendum-2026-11-06.md"]


def network_reachable():
    try:
        socket.create_connection(("pypi.org", 443), timeout=5).close()
        return True
    except OSError:
        return False


def find(data_dir, name):
    for p in glob.glob(os.path.join(data_dir, "xltw-test", "x-*", "**", "*.vrp"), recursive=True):
        if os.path.splitext(os.path.basename(p))[0] == name:
            return p
    return None


def vmhwm_gb(pid):
    try:
        with open("/proc/%d/status" % pid, encoding="utf-8") as f:
            for line in f:
                if line.startswith("VmHWM:"):
                    return int(line.split()[1]) / 1024.0 / 1024.0
    except (OSError, ValueError):
        return None
    return None


def parse(lines):
    """lines: [(t, text)]. Returns blocks [(t of Cost line, routes, cost)], bad lines, numbering errors."""
    blocks, cur, bad, numbering = [], [], [], 0
    for t, raw in lines:
        s = raw.rstrip("\n")
        m = ROUTE.match(s)
        if m:
            if int(m.group(1)) != len(cur) + 1:
                numbering += 1
            cur.append([int(x) for x in (m.group(2) or "").split()])
            continue
        m = COST.match(s)
        if m:
            if cur:
                blocks.append((t, cur, float(m.group(1))))
            else:
                bad.append(s[:80])
            cur = []
            continue
        bad.append(s[:80])
    return blocks, bad, numbering


def run_one(rid, path, limit, seed, log_dir):
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
            h = vmhwm_gb(p.pid)
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
    blocks, bad, numbering = parse(lines)
    on_time = [b for b in blocks if b[0] <= limit]
    rec = {"id": rid, "instance": inst["name"], "customers": len(inst["rows"]) - 1, "limit": limit, "seed": seed,
           "exit": p.returncode, "wall": round(wall, 3), "self_stopped": termed is None,
           "sigterm_at": None if termed is None else round(termed, 3),
           "sigkill_at": None if killed is None else round(killed, 3),
           "exit_after_sigterm": None if termed is None else round(wall - termed, 3),
           "stdout_lines": len(lines), "bad_lines": bad[:5], "bad_line_count": len(bad),
           "numbering_errors": numbering, "blocks": len(blocks), "blocks_after_limit": len(blocks) - len(on_time),
           "first_line_at": round(lines[0][0], 3) if lines else None,
           "last_cost_at": round(on_time[-1][0], 3) if on_time else None,
           "slack": round(limit - on_time[-1][0], 3) if on_time else None,
           "peak_gb": None if peak is None else round(peak, 3)}
    stats, watchdog = None, None
    with open(err_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("XLTW_SOLVER_STATS "):
                stats = json.loads(line[len("XLTW_SOLVER_STATS "):])
            elif line.startswith("XLTW_WATCHDOG "):
                watchdog = line.strip()
    rec["solver_stats"] = stats
    rec["watchdog"] = watchdog
    # The harness polls every 0.05 s: a gap of more than 1 s between two polls means the harness itself was frozen
    # (the container paused by the host), and the run is not a valid run of the protocol.
    rec["max_poll_gap"] = round(max_gap, 3)
    rec["harness_frozen"] = max_gap > 1.0
    if on_time:
        t, routes, cost = on_time[-1]
        chk = B.check_exact(routes, inst, "round")
        rec.update({"feasible": bool(chk["ok"]), "reason": chk["reason"], "vehicles": len(routes),
                    "distance": None if chk["distance"] is None else int(round(chk["distance"])),
                    "cost_line": cost,
                    "cost_line_ok": chk["distance"] is not None and abs(cost - chk["distance"]) < 1e-6})
    else:
        rec.update({"feasible": False, "reason": "no solution before the limit", "vehicles": None, "distance": None,
                    "cost_line": None, "cost_line_ok": False})
    return rec


def verdict(ok):
    return "held" if ok else "did not hold"


def score(build, net, recs, runset="main"):
    by = {r["id"]: r for r in recs}
    done = len(recs) == len(RUNSETS[runset]) and all(not r.get("error") for r in recs)
    ok = [r for r in recs if not r.get("error")]
    c0 = (not net) and build.get("tag") is not None and build.get("pins_ok") is True
    p = {"C0": verdict(c0)}
    if runset == "n8575":
        w = by.get("W1")
        if not c0:
            p["C7"] = p["C8"] = "untestable (C0 failed)"
        elif not done or w is None:
            p["C7"] = p["C8"] = "untestable (W1 did not run)"
        else:
            p["C7"] = verdict(w["self_stopped"] and w["exit"] == 0 and w["feasible"] and w["cost_line_ok"]
                              and w["bad_line_count"] == 0 and w["numbering_errors"] == 0)
            p["C8"] = verdict(bool(w.get("watchdog")) and "deadline" in w["watchdog"])
        return p
    if not c0:
        for k in ("C1", "C2", "C3", "C4", "C5", "C6"):
            p[k] = "untestable (C0 failed)"
        return p
    p["C1"] = verdict(done and all(r["bad_line_count"] == 0 and r["numbering_errors"] == 0 for r in ok))
    p["C2"] = verdict(done and all(r["feasible"] and r["cost_line_ok"] for r in ok))
    p["C3"] = verdict(done and all(r["self_stopped"] and r["exit"] == 0 for r in ok))
    p["C4"] = verdict(done and all(r["slack"] is not None and r["slack"] >= 0.5 for r in ok))
    r4, r5 = by.get("R4"), by.get("R5")
    if r4 and r5 and r4.get("vehicles") is not None and r5.get("vehicles") is not None:
        p["C5a"] = verdict(r4["vehicles"] == r5["vehicles"])
        p["C5b"] = verdict(r4["distance"] != r5["distance"])
    else:
        p["C5a"] = p["C5b"] = "untestable (R4 or R5 has no solution)"
    p["C6"] = verdict(done and all(r["peak_gb"] is not None and r["peak_gb"] <= 0.6 for r in ok))
    return p


def build_info():
    try:
        with open(os.path.join(HERE, "lib", "XLTW_BUILD.json"), encoding="utf-8") as f:
            info = json.load(f)
    except (OSError, ValueError) as e:
        return {"tag": None, "error": str(e)}
    import lock
    info["pins_ok"] = {w["name"]: w["version"] for w in info["wheels"]} == dict(lock.PINS)
    info["checked_by"] = sys.executable
    try:
        import numpy
        import pyvrp
        info["numpy_from_lib"] = numpy.__file__.startswith(os.path.join(HERE, "lib"))
        info["pyvrp_from_lib"] = pyvrp.__file__.startswith(os.path.join(HERE, "lib"))
        info["pins_ok"] = info["pins_ok"] and info["numpy_from_lib"] and info["pyvrp_from_lib"]
    except ImportError as e:
        info["pins_ok"] = False
        info["import_error"] = str(e)
    return info


def write_md(path, build, net, recs, preds, job):
    L = ["# xltwpkg: conformance of the packaged solver (%s)" % job, "",
         "Network reachable during the run steps: %s. Built offline for %s with Python %s (%s); pins ok: %s." % (
             net, build.get("tag"), build.get("python"), build.get("executable"), build.get("pins_ok")), "",
         "Predictions (expectations.md): `%s`" % json.dumps(preds), "",
         "| run | instance | n | limit s | seed | vehicles | distance | feasible | cost line ok | bad stdout lines | "
         "self-stopped | last Cost at s | slack s | peak GB | watchdog |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in recs:
        if r.get("error"):
            L.append("| %s | %s | | | | error | | | | | | | | | |" % (r["id"], r.get("instance")))
            continue
        L.append("| %s | %s | %d | %.2f | %d | %s | %s | %s | %s | %d | %s | %s | %s | %s | %s |" % (
            r["id"], r["instance"], r["customers"], r["limit"], r["seed"], r["vehicles"], r["distance"],
            r["feasible"], r["cost_line_ok"], r["bad_line_count"], r["self_stopped"], r["last_cost_at"], r["slack"],
            r["peak_gb"], r.get("watchdog") or ""))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


def reexec_under_build_python():
    """Run this script under the interpreter the build recorded, if that is not the one running now."""
    import lock
    exe = lock.build_python(HERE)
    if not exe or os.environ.get("XLTW_CONFORMANCE_REEXEC"):
        return
    if os.path.realpath(exe) == os.path.realpath(sys.executable):
        return
    print("conformance.py: re-running under the build's interpreter %s (was %s)" % (exe, sys.executable),
          flush=True)
    os.environ["XLTW_CONFORMANCE_REEXEC"] = "1"
    os.execv(exe, [exe, os.path.abspath(__file__)] + sys.argv[1:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--job", default="xltwpkg")
    ap.add_argument("--runs", default="main", choices=sorted(RUNSETS))
    a = ap.parse_args()
    reexec_under_build_python()
    out = os.path.join(a.out_dir, "xltwpkg")
    logs = os.path.join(out, "logs")
    os.makedirs(logs, exist_ok=True)
    net = network_reachable()
    build = build_info()
    print("network reachable: %s; build: %s" % (net, json.dumps(build)), flush=True)
    recs = []
    if not net and build.get("pins_ok"):
        for rid, name, limit, seed in RUNSETS[a.runs]:
            path = find(a.data_dir, name)
            if path is None:
                recs.append({"id": rid, "instance": name, "error": "instance file not found"})
                continue
            try:
                rec = run_one(rid, path, limit, seed, logs)
                if rec["harness_frozen"]:  # pre-registered: re-run once, unchanged; keep the frozen one on record
                    first = rec
                    rec = run_one(rid, path, limit, seed, logs)
                    rec["frozen_first_try"] = first
            except Exception as e:  # noqa: BLE001 - recorded
                rec = {"id": rid, "instance": name, "error": repr(e)}
            recs.append(rec)
            print(json.dumps({k: rec.get(k) for k in ("id", "instance", "vehicles", "distance", "feasible",
                                                     "bad_line_count", "self_stopped", "slack", "peak_gb",
                                                     "watchdog", "error")}), flush=True)
    preds = score(build, net, recs, a.runs)
    res = {"job": a.job, "runs_set": a.runs, "network_reachable": net, "build": build, "runs": recs, "predictions": preds,
           "python": sys.version.split()[0], "executable": sys.executable}
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1)
    write_md(os.path.join(out, "results.md"), build, net, recs, preds, a.job)
    pkg = os.path.join(out, "pkg")
    os.makedirs(pkg, exist_ok=True)
    for name in SHIP:
        if os.path.exists(os.path.join(HERE, name)):
            shutil.copy2(os.path.join(HERE, name), os.path.join(pkg, name))
    print(json.dumps(preds), flush=True)


if __name__ == "__main__":
    main()
