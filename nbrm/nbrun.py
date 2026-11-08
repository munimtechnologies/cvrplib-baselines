"""nbrm: Nagata & Braysy's route-minimisation heuristic (Astronomax's C implementation, MIT) on the four capacity-free
XLTW-Test instances of xltwfull/, under the VRPTW Challenge's nearest-integer distance rule.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0 (this wrapper; the
route minimiser it runs is MIT-licensed and is not part of this file).

Predictions N0-N5 are in expectations.md, fixed and published before any run.

  python nbrun.py --data-dir /data --out-dir /out            # smoke run, N1-N4, scoring
  python nbrun.py --score results.json                       # re-score a results file
"""
import argparse
import glob
import json
import math
import os
import re
import resource
import signal
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

SEED = 20261104
GUARD = 300.0
MAX_N = 2000
# id, instance, customers, K*, best valid PyVRP vehicles at T(n), where from
RUNS = [
    ("N1", "XLTW-Test-n1234", 1233, 27, 33, "xltwff H1"),
    ("N2", "XLTW-Test-n1421", 1420, 47, 65, "xltwff H2"),
    ("N3", "XLTW-Test-n1608", 1607, 81, 108, "xltwfull F3 / xltwff H3"),
    ("N4", "XLTW-Test-n1841", 1840, 18, 25, "xltwfull F4 / xltwff H4"),
]
BY_ID = {r[0]: r for r in RUNS}
INCUMBENT = re.compile(r"incumbent_ms:\s*(\d+)\s+n_routes:\s*(\d+)")
HEADER = ("CUST NO.  XCOORD.   YCOORD.    DEMAND   READY TIME  DUE DATE   SERVICE   TIME")


def limit_for(customers):
    """T(n) = 1,800 x n / 1,000 s, n = number of customers (as in xltwfull/fullrun.py)."""
    return round(1.8 * customers, 1)


def fleet_limit(customers):
    """L = floor(T(n) / 2) whole seconds (the route minimiser takes an integer --t_max)."""
    return int(math.floor(limit_for(customers) / 2))


def write_homberger(inst, path):
    """Gehring & Homberger text format from the instance's own tokens; customer numbers 0..n, depot 0."""
    raw = inst["raw"]
    L = [inst["name"], "", "VEHICLE", "NUMBER     CAPACITY", "  %d      %s" % (len(raw) - 1, inst["capacity"]), "",
         "CUSTOMER", HEADER, ""]
    for i, r in enumerate(raw):
        L.append("%5d %s" % (i, " ".join("%10s" % t for t in r)))
    with open(path, "w", encoding="ascii", newline="\n") as f:
        f.write("\n".join(L) + "\n")


def parse_sol(text):
    """Solution file of the route minimiser: one line per route, 'id time id time ...' with the depot (0) at both
    ends. Returns the routes as lists of customer numbers (depot dropped)."""
    routes = []
    for line in text.splitlines():
        tok = line.split()
        if not tok:
            continue
        if len(tok) % 2:
            raise ValueError("odd number of tokens on a route line: %r" % line[:80])
        ids = [int(float(t)) for t in tok[0::2]]
        r = [c for c in ids if c != 0]
        if r:
            routes.append(r)
    return routes


def incumbents(text):
    """[(cpu_ms, n_routes)] of every incumbent line (colour codes ignored)."""
    return [(int(a), int(b)) for a, b in INCUMBENT.findall(text)]


def first_ms_at(incs, routes):
    for ms, n in incs:
        if n == routes:
            return ms
    return None


def vmhwm_gb(pid):
    try:
        with open("/proc/%d/status" % pid, encoding="ascii") as f:
            for line in f:
                if line.startswith("VmHWM:"):
                    return int(line.split()[1]) / 1024.0 / 1024.0
    except (OSError, ValueError):
        return None
    return None


def children_cpu():
    ru = resource.getrusage(resource.RUSAGE_CHILDREN)
    return ru.ru_utime + ru.ru_stime


def run_routes(binary, inst_txt, sol_path, t_max, lower, seed, log_path, guard):
    """One process; returns exit, wall, cpu, peak, killed, max poll gap, stdout text."""
    if os.path.exists(sol_path):
        os.remove(sol_path)
    cmd = [binary, inst_txt, sol_path, "--t_max", str(t_max), "--lower_bound", str(lower), "--seed", str(seed),
           "--log_level", "normal"]
    cpu0 = children_cpu()
    with open(log_path, "w", encoding="utf-8", errors="replace") as log:
        t0 = time.monotonic()
        p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
        peak, killed, prev, gap = None, None, 0.0, 0.0
        while p.poll() is None:
            el = time.monotonic() - t0
            gap, prev = max(gap, el - prev), el
            h = vmhwm_gb(p.pid)
            if h is not None:
                peak = max(peak or 0.0, h)
            if killed is None and el >= guard:
                p.kill()
                killed = el
            time.sleep(0.2)
        wall = time.monotonic() - t0
    cpu = children_cpu() - cpu0
    with open(log_path, encoding="utf-8", errors="replace") as f:
        out = f.read()
    return {"cmd": cmd[1:], "exit": p.returncode, "wall": round(wall, 2), "cpu": round(cpu, 2),
            "peak_gb": None if peak is None else round(peak, 3), "killed_at": None if killed is None else round(killed, 2),
            "max_poll_gap": round(gap, 2)}, out


def check(routes, inst):
    import xltwbase as B
    chk = B.check_exact(routes, inst, "round")
    return {"feasible": bool(chk["ok"]), "reason": chk["reason"],
            "distance": None if chk["distance"] is None else int(round(chk["distance"]))}


def one(binary, rid, inst, t_max, lower, seed, work, guard):
    txt = os.path.join(work, "%s.txt" % rid)
    sol = os.path.join(work, "%s.sol" % rid)
    write_homberger(inst, txt)
    rec, out = run_routes(binary, txt, sol, t_max, lower, seed, os.path.join(work, "%s.log.txt" % rid), guard)
    rec.update({"id": rid, "instance": inst["name"], "customers": len(inst["raw"]) - 1, "t_max": t_max,
                "lower_bound": lower, "seed": seed})
    incs = incumbents(out)
    rec["incumbents"] = len(incs)
    if os.path.exists(sol):
        with open(sol, encoding="ascii", errors="replace") as f:
            routes = parse_sol(f.read())
        rec["vehicles"] = len(routes)
        rec.update(check(routes, inst))
        rec["final_count_first_cpu_s"] = None
        ms = first_ms_at(incs, len(routes))
        if ms is not None:
            rec["final_count_first_cpu_s"] = round(ms / 1000.0, 2)
        rec["trajectory"] = [[ms, n] for ms, n in incs if n <= len(routes) + 10]
    else:
        rec.update({"vehicles": None, "feasible": False, "reason": "no solution file", "distance": None})
    rec["valid"] = valid(rec)
    return rec


def valid(r):
    return (r is not None and not r.get("error") and r.get("exit") == 0 and r.get("killed_at") is None
            and r.get("vehicles") is not None and r.get("feasible") is True)


def verdict(ok):
    return "held" if ok else "did not hold"


def score(res):
    """N0-N5 of expectations.md."""
    b = res.get("build") or {}
    runs = {r["id"]: r for r in res.get("runs", [])}
    vs = [runs.get(i) for i in BY_ID]
    smoke = res.get("smoke") or {}
    gate = (b.get("patch_matches") == 1 and b.get("built") is True and valid(smoke)
            and all(valid(r) for r in vs))
    p = {"N0": verdict(gate)}
    if not gate:
        for k in ("N1", "N2", "N3", "N4", "N5"):
            p[k] = "untestable (N0 failed)"
        return p
    ref = [BY_ID[r["id"]][4] for r in vs]
    veh = [r["vehicles"] for r in vs]
    kst = [BY_ID[r["id"]][3] for r in vs]
    p["N1"] = verdict(all(v <= q for v, q in zip(veh, ref)))
    p["N2"] = verdict(sum(1 for v, q in zip(veh, ref) if v < q) >= 3)
    p["N3"] = verdict(sum(veh) <= 221)
    p["N4"] = verdict(sum(1 for v, k in zip(veh, kst) if v <= k) <= 1)
    p["N5"] = verdict(all(r["cpu"] <= r["t_max"] + 60 and r["peak_gb"] is not None and r["peak_gb"] <= 0.5
                          for r in vs))
    return p


def network_reachable():
    import socket
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=3).close()
        return True
    except OSError:
        return False


def find(data_dir, name):
    hits = sorted(glob.glob(os.path.join(data_dir, "xltw-test", "x-*", "**", name + ".vrp"), recursive=True))
    return hits[0] if hits else None


def write_md(path, res):
    L = ["# nbrm: Nagata & Braysy route minimiser (Astronomax, MIT) on four capacity-free XLTW-Test instances", "",
         "Seed %d. Build: %s. Network reachable during the runs: %s." % (
             SEED, json.dumps(res.get("build")), res.get("network_reachable")), "",
         "Predictions (expectations.md): `%s`" % json.dumps(res.get("predictions")), "",
         "Smoke run: `%s`" % json.dumps({k: (res.get("smoke") or {}).get(k) for k in
                                          ("vehicles", "feasible", "reason", "exit", "cpu")}), "",
         "| run | instance | n | L s | K* | PyVRP best | vehicles | final count first at CPU s | CPU s | wall s | "
         "peak GB | distance (round) | exit | killed | feasible | valid |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res.get("runs", []):
        if r.get("error"):
            L.append("| %s | %s | error: %s |||||||||||||||" % (r["id"], r.get("instance"), r["error"]))
            continue
        L.append("| %s | %s | %d | %d | %d | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["id"], r["instance"], r["customers"], r["t_max"], r["lower_bound"], BY_ID[r["id"]][4], r["vehicles"],
            r.get("final_count_first_cpu_s"), r["cpu"], r["wall"], r["peak_gb"], r["distance"], r["exit"],
            r["killed_at"], r["feasible"], r["valid"]))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--binary", default=os.path.join(HERE, "routes"))
    ap.add_argument("--score", default="")
    a = ap.parse_args()
    if a.score:
        with open(a.score, encoding="utf-8") as f:
            res = json.load(f)
        print(json.dumps(score(res)))
        return
    import xltwbase as B
    import xltwlb as X
    out = os.path.join(a.out_dir, "nbrm")
    work = os.path.join(out, "runs")
    os.makedirs(work, exist_ok=True)
    build = {}
    bpath = os.path.join(HERE, "nb-build.json")
    if os.path.exists(bpath):
        with open(bpath, encoding="utf-8") as f:
            build = json.load(f)
    res = {"build": build, "network_reachable": network_reachable(), "python": sys.version.split()[0], "runs": []}
    res_path = os.path.join(out, "results.json")

    def save():
        with open(res_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(res, f, indent=1)

    syn = B.synthetic(60)
    res["smoke"] = one(a.binary, "smoke", syn, 3, 0, 1, work, 120.0)
    print(json.dumps({k: res["smoke"].get(k) for k in ("vehicles", "feasible", "reason", "exit", "cpu")}),
          flush=True)
    save()
    for rid, name, customers, kstar, _, _ in RUNS:
        path = find(a.data_dir, name)
        if path is None:
            rec = {"id": rid, "instance": name, "error": "instance file not found"}
        else:
            try:
                with open(path, encoding="utf-8") as f:
                    inst = X.parse_any(f.read())
                n = len(inst["raw"]) - 1
                if n != customers or n > MAX_N:
                    raise ValueError("unexpected size %d" % n)
                t_max = fleet_limit(customers)
                guard = limit_for(customers) + GUARD
                rec = one(a.binary, rid, inst, t_max, kstar, SEED, work, guard)
                if rec.get("killed_at") is not None:  # pre-registered: re-run once, unchanged; both kept
                    first = rec
                    rec = one(a.binary, rid, inst, t_max, kstar, SEED, work, guard)
                    rec["killed_first_try"] = first
            except Exception as e:  # noqa: BLE001 - recorded
                rec = {"id": rid, "instance": name, "error": repr(e)}
        res["runs"].append(rec)
        save()
        print(json.dumps({k: rec.get(k) for k in ("id", "instance", "vehicles", "lower_bound", "feasible",
                                                 "reason", "cpu", "wall", "peak_gb", "final_count_first_cpu_s",
                                                 "error")}), flush=True)
    res["predictions"] = score(res)
    save()
    write_md(os.path.join(out, "results.md"), res)
    print(json.dumps(res["predictions"]), flush=True)


if __name__ == "__main__":
    main()
