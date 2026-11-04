"""Run `solver.py` on CVRPLib's XLTW-Test set the way the VRPTW BKS Challenge runs algorithms, with the time limit
scaled down, and check every counted solution exactly.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

Protocol (from the challenge's rules, read 2026-11-02 and 2026-11-04): `solver INSTANCE SECONDS SEED`; one logical
CPU per run; at the time limit SIGTERM, then SIGKILL five seconds later; solutions on stdout in CVRPLib format
(`Route #k: ...`, `Cost: ...`), customers numbered 1..n; only the last complete, feasible solution printed before the
limit counts; if the printed cost differs from the routes' cost, the routes' cost counts. T(n) = 1,800 s x n / 1,000.

This harness launches one solver process per instance (at most `--workers` at a time, and only while the estimated
memory of the running ones fits `--mem-gb`), timestamps every stdout line as it arrives, sends SIGTERM at the limit
and SIGKILL five seconds later if needed, takes the last solution whose `Cost` line arrived before the limit and is
on time in exact 50-digit arithmetic under nearest-integer rounding (`xltwbase.check_exact`, convention 'round'),
and records the vehicles, distance, the fleet bound K from `xltwtest/` and the peak memory of the process.
"""
import argparse
import glob
import hashlib
import json
import os
import signal
import statistics
import subprocess
import sys
import threading
import time
import traceback
import urllib.request

import xltwbase as B
import xltwlb as X

URL = "https://galgos.inf.puc-rio.br/cvrplib/uploads/files/vrptw_challenge/XLTW-Test.7z"
SHA256 = "9635b9fa813ea34ff3f35842f80a40ce6764d14c27cf2e13e5fbf1de623f4631"
UA = "CVRPLib XLTW-Test runs - MV2 of Munim, Inc. (mv2@munimtech.com)"
SEED = 20261104
GRACE = 5.0
HERE = os.path.dirname(os.path.abspath(__file__))
T0 = time.time()

# From xltwtest/results.md (xltw-test-bounds-v1, 2026-11-02): instance, customers, KC, K in 'round'.
_BOUNDS = """
n1048 1047 1 3|n1094 1093 92 92|n1141 1140 33 33|n1188 1187 32 32|n1234 1233 1 7|n1281 1280 90 132|n1328 1327 65 65
n1374 1373 24 24|n1421 1420 1 16|n1468 1467 40 40|n1514 1513 1 16|n1561 1560 56 56|n1608 1607 1 7|n1654 1653 69 69
n1701 1700 33 33|n1748 1747 143 143|n1794 1793 180 180|n1841 1840 1 4|n1888 1887 32 32|n1934 1933 1 3
n1981 1980 71 71|n2028 2027 1 8|n2074 2073 53 53|n2121 2120 17 17|n2168 2167 68 68|n2214 2213 1 13|n2261 2260 60 60
n2307 2306 41 41|n2354 2353 65 65|n2401 2400 1 111|n2447 2446 131 131|n2494 2493 37 43|n2541 2540 1 91
n2587 2586 41 41|n2634 2633 74 74|n2681 2680 1 17|n2727 2726 64 64|n2774 2773 208 208|n2821 2820 1 84|n2867 2866 1 4
n2914 2913 157 157|n2961 2960 80 80|n3007 3006 1 158|n3054 3053 112 112|n3101 3100 52 52|n3147 3146 1 1
n3194 3193 413 413|n3241 3240 137 151|n3287 3286 43 43|n3334 3333 83 83|n3408 3407 1 41|n3484 3483 80 80
n3561 3560 62 62|n3640 3639 1 243|n3721 3720 218 218|n3804 3803 1 10|n3888 3887 204 460|n3975 3974 70 70
n4063 4062 137 137|n4153 4152 1 5|n4245 4244 133 133|n4340 4339 1 4|n4436 4435 54 54|n4535 4534 1 16
n4635 4634 198 201|n4738 4737 101 101|n4844 4843 182 182|n4951 4950 213 213|n5061 5060 1 38|n5174 5173 39 39
n5288 5287 1 77|n5406 5405 136 136|n5526 5525 346 346|n5649 5648 265 265|n5774 5773 1 3|n5902 5901 1 3
n6034 6033 104 104|n6168 6167 148 148|n6305 6304 1 79|n6445 6444 452 452|n6588 6587 87 87|n6734 6733 163 163
n6884 6883 1 16|n7037 7036 587 587|n7193 7192 52 52|n7353 7352 85 85|n7516 7515 1 4|n7683 7682 269 269
n7854 7853 1 4|n8028 8027 803 803|n8207 8206 251 251|n8389 8388 162 162|n8575 8574 1 11|n8766 8765 432 432
n8960 8959 1 5|n9160 9159 244 244|n9363 9362 209 253|n9571 9570 181 181|n9784 9783 1 8|n10001 10000 260 260
"""
BOUNDS = {}
for _cell in _BOUNDS.replace("\n", "|").split("|"):
    if _cell.strip():
        _name, _n, _kc, _k = _cell.split()
        BOUNDS["XLTW-Test-" + _name] = {"customers": int(_n), "kc": int(_kc), "k": int(_k)}


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def t_of(n):
    """The challenge's time limit for n customers, in seconds."""
    return 1800.0 * n / 1000.0


def mem_est(n):
    """Planning estimate of a solver process's peak memory (GB); the run records the real peak."""
    return 0.15 + 4.0 * (n / 10000.0) ** 2


def parse_stdout(lines):
    """lines: [(seconds since start, text)]. Returns (blocks [(seconds, routes, reported cost)], other lines).
    A block is the Route lines before a Cost line; a malformed line breaks the block it is in."""
    blocks, cur, other = [], [], 0
    for t, text in lines:
        s = text.strip()
        if not s:
            continue
        if s.startswith("Route #"):
            _, sep, rest = s.partition(":")
            try:
                if not sep:
                    raise ValueError(s)
                cur.append([int(x) for x in rest.split()])
            except ValueError:
                other += 1
                cur = []
        elif s.startswith("Cost"):
            try:
                cost = float(s[4:].strip().lstrip(":").strip())
            except ValueError:
                other += 1
                cur = []
                continue
            if cur:
                blocks.append((t, cur, cost))
            cur = []
        else:
            other += 1
    return blocks, other


def counted(blocks, limit, inst, check=B.check_exact):
    """The last block before the limit that is on time in 'round'. Returns (block, check, blocks after the limit)."""
    on_time = [b for b in blocks if b[0] <= limit]
    for b in reversed(on_time):
        chk = check(b[1], inst, "round")
        if chk["ok"]:
            return b, chk, len(blocks) - len(on_time)
    return None, None, len(blocks) - len(on_time)


def _vmhwm_gb(pid):
    try:
        with open("/proc/%d/status" % pid, encoding="utf-8") as f:
            for line in f:
                if line.startswith("VmHWM:"):
                    return int(line.split()[1]) / 1024.0 / 1024.0
    except (OSError, ValueError):
        return None
    return None


def _stats_line(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            last = None
            for line in f:
                if line.startswith("XLTW_SOLVER_STATS "):
                    last = line
        return json.loads(last[len("XLTW_SOLVER_STATS "):]) if last else None
    except (OSError, ValueError):
        return None


class Run:
    """One solver process under the protocol."""

    def __init__(self, path, inst, limit, seed, solver, log_dir, grace=GRACE):
        self.path, self.inst, self.limit, self.seed = path, inst, limit, seed
        self.solver, self.grace = solver, grace
        self.name = inst["name"]
        self.n = len(inst["rows"]) - 1
        self.err_path = os.path.join(log_dir, "%s.stderr.txt" % self.name)
        self.lines, self.termed, self.killed, self.peak = [], None, None, None

    def start(self):
        env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                   PYTHONUNBUFFERED="1")
        self.err = open(self.err_path, "w", encoding="utf-8")
        self.t0 = time.monotonic()
        self.p = subprocess.Popen([sys.executable, self.solver, self.path, "%.3f" % self.limit, str(self.seed)],
                                  stdout=subprocess.PIPE, stderr=self.err, text=True, bufsize=1, env=env)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        return self

    def _read(self):
        for line in self.p.stdout:
            self.lines.append((time.monotonic() - self.t0, line))

    def poll(self):
        """True once the process has ended. Sends SIGTERM at the limit and SIGKILL `grace` seconds later."""
        el = time.monotonic() - self.t0
        hwm = _vmhwm_gb(self.p.pid)
        if hwm is not None:
            self.peak = max(self.peak or 0.0, hwm)
        if self.p.poll() is not None:
            return True
        if self.termed is None and el >= self.limit:
            self.p.send_signal(signal.SIGTERM)
            self.termed = round(el, 2)
        elif self.termed is not None and self.killed is None and el >= self.limit + self.grace:
            self.p.kill()
            self.killed = round(el, 2)
        return False

    def finish(self):
        self.p.wait()
        wall = time.monotonic() - self.t0
        self.reader.join(timeout=30)
        self.err.close()
        blocks, other = parse_stdout(self.lines)
        blk, chk, late_blocks = counted(blocks, self.limit, self.inst)
        b = BOUNDS.get(self.name, {})
        rec = {"instance": self.name, "customers": self.n, "limit": round(self.limit, 3), "seed": self.seed,
               "exit": self.p.returncode, "wall": round(wall, 2), "sigterm_at": self.termed,
               "sigkill_at": self.killed, "blocks": len(blocks), "blocks_after_limit": late_blocks,
               "other_stdout_lines": other, "peak_gb": None if self.peak is None else round(self.peak, 3),
               "mem_est_gb": round(mem_est(self.n), 3), "kc": b.get("kc"), "k": b.get("k"),
               "solver": _stats_line(self.err_path)}
        if blk is None:
            rec.update({"vehicles": None, "distance": None, "exact_ok": False, "at_s": None})
        else:
            t, routes, cost = blk
            dist = int(round(chk["distance"]))
            rec.update({"vehicles": len(routes), "distance": dist, "exact_ok": True, "at_s": round(t, 2),
                        "cost_line": cost, "cost_line_ok": abs(cost - chk["distance"]) < 1e-6,
                        "last_block_counted": blk is blocks[len(blocks) - 1 - late_blocks]})
            self.routes = routes
        k = rec["k"]
        rec["at_k"] = rec["vehicles"] is not None and k is not None and rec["vehicles"] == k
        rec["below_k"] = rec["vehicles"] is not None and k is not None and rec["vehicles"] < k
        rec["gap_k"] = None if rec["vehicles"] is None or not k else round((rec["vehicles"] - k) / float(k), 4)
        return rec


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_instances(data_dir):
    """XLTW-Test .vrp files from the shared data volume (extracted by xltwtest.py), downloading once if absent."""
    found = sorted(glob.glob(os.path.join(data_dir, "xltw-test", "x-*", "**", "*.vrp"), recursive=True))
    if found:
        return found, None
    arch = os.path.join(data_dir, "xltw-test", "XLTW-Test.7z")
    if not os.path.exists(arch):
        os.makedirs(os.path.dirname(arch), exist_ok=True)
        req = urllib.request.Request(URL, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=300) as r, open(arch + ".part", "wb") as f:
            f.write(r.read())
        os.replace(arch + ".part", arch)
    digest = sha256(arch)
    import py7zr
    dest = os.path.join(data_dir, "xltw-test", "x-" + digest[:12])
    with py7zr.SevenZipFile(arch, mode="r") as z:
        z.extractall(path=dest)
    return sorted(glob.glob(os.path.join(dest, "**", "*.vrp"), recursive=True)), digest


def schedule(runs, workers, mem_gb, on_done, poll=0.2):
    """Largest first; start any waiting run that fits next to the running ones (always at least one)."""
    waiting = sorted(runs, key=lambda r: -r.n)
    running = []
    while waiting or running:
        used = sum(mem_est(r.n) for r in running)
        for r in list(waiting):
            if len(running) >= workers:
                break
            if not running or used + mem_est(r.n) <= mem_gb:
                waiting.remove(r)
                running.append(r.start())
                used += mem_est(r.n)
                log("start %s (n %d, limit %.1f s, est %.2f GB)" % (r.name, r.n, r.limit, mem_est(r.n)))
        time.sleep(poll)
        for r in list(running):
            if r.poll():
                running.remove(r)
                on_done(r)


def verdict(ok):
    return "untestable" if ok is None else ("held" if ok else "did not hold")


def tally(recs, expected=100):
    """Scores G0-G5 (expectations.md) on the runs given. All six need all `expected` runs, else untestable."""
    done = [r for r in recs if not r.get("error")]
    full = len(done) == expected
    ok = [r for r in done if r["exact_ok"]]
    kc1 = [r for r in done if r.get("kc") == 1]
    other = [r for r in done if r.get("kc") not in (None, 1)]
    at_k = [r for r in ok if r["at_k"]]
    gaps = [r["gap_k"] for r in ok if r["gap_k"] is not None]
    t = {"runs": len(recs), "errors": [r["instance"] for r in recs if r.get("error")],
         "counted": len(ok), "no_solution": [r["instance"] for r in done if not r["exact_ok"]],
         "cost_line_wrong": [r["instance"] for r in ok if not r.get("cost_line_ok")],
         "other_stdout": [r["instance"] for r in done if r["other_stdout_lines"]],
         "sigterm": [r["instance"] for r in done if r["sigterm_at"] is not None],
         "sigkill": [r["instance"] for r in done if r["sigkill_at"] is not None],
         "below_k": [r["instance"] for r in ok if r["below_k"]],
         "at_k": len(at_k), "at_k_kc1": sum(1 for r in kc1 if r["exact_ok"] and r["at_k"]), "kc1": len(kc1),
         "at_k_other": sum(1 for r in other if r["exact_ok"] and r["at_k"]), "other": len(other),
         "median_gap_k": round(statistics.median(gaps), 4) if gaps else None,
         "over_mem_est": [r["instance"] for r in done if r["peak_gb"] is not None and r["peak_gb"] > r["mem_est_gb"]],
         "no_peak": [r["instance"] for r in done if r["peak_gb"] is None],
         "bound_timed_out": [r["instance"] for r in done if (r.get("solver") or {}).get("bound", {}).get("timed_out")],
         "vehicles": sum(r["vehicles"] for r in ok), "k_total": sum(r["k"] for r in ok if r["k"])}
    g = lambda cond: verdict(cond if full else None)  # noqa: E731
    t["predictions"] = {
        "G0": g(len(ok) == expected and not t["cost_line_wrong"] and not t["other_stdout"] and not t["sigkill"]
                and not t["below_k"]),
        "G1": g(not t["sigterm"]),
        "G2": g(20 <= t["at_k"] <= 55),
        "G3": g(t["at_k_kc1"] <= 5),
        "G4": g(t["median_gap_k"] is not None and t["median_gap_k"] <= 0.10),
        "G5": g(not t["over_mem_est"] and not t["no_peak"]),
    }
    return t


def write_md(path, recs, t, scale):
    lines = ["# xltwrun: solver.py on XLTW-Test under the challenge's protocol, limits divided by %g" % scale, "",
             "One run per instance, seed %d, one CPU per run, nearest-integer rounding; every counted solution "
             "re-checked exactly. K = the fleet lower bound from xltwtest/ (not a known optimum)." % SEED, "",
             "Predictions: `%s`" % json.dumps(t["predictions"]), "",
             "Vehicles %d against K %d in total; at K on %d runs (%d of %d with KC = 1, %d of %d others); median "
             "(vehicles - K) / K %s." % (t["vehicles"], t["k_total"], t["at_k"], t["at_k_kc1"], t["kc1"],
                                         t["at_k_other"], t["other"], t["median_gap_k"]), "",
             "| instance | n | limit s | KC | K | vehicles | distance | last at s | solutions printed | fleet s | "
             "bound cut | iterations | SIGTERM | peak GB |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(recs, key=lambda r: r.get("customers", 0)):
        if r.get("error"):
            lines.append("| %s | | | | | error | | | | | | | | |" % r["instance"])
            continue
        s = r.get("solver") or {}
        lines.append("| %s | %d | %.1f | %s | %s | %s | %s | %s | %d | %s | %s | %s | %s | %s |" % (
            r["instance"], r["customers"], r["limit"], r["kc"], r["k"], r["vehicles"], r["distance"], r["at_s"],
            r["blocks"], s.get("fleet_seconds"), (s.get("bound") or {}).get("timed_out"), s.get("iterations"),
            r["sigterm_at"] is not None, r["peak_gb"]))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def write_sol(routes, distance):
    lines = ["Route #%d: %s" % (i + 1, " ".join(map(str, rt))) for i, rt in enumerate(routes)]
    lines.append("Cost: %d" % distance)
    return "\n".join(lines) + "\n"


def merge(paths, out):
    """Score the parts together (one record per instance; a duplicate instance is an error)."""
    recs, scale, seen = [], None, set()
    for p in paths:
        with open(p, encoding="utf-8") as f:
            res = json.load(f)
        scale = res["scale"] if scale is None else scale
        if res["scale"] != scale:
            raise SystemExit("parts were run with different scales")
        for r in res["runs"]:
            if r["instance"] in seen:
                raise SystemExit("instance %s appears twice" % r["instance"])
            seen.add(r["instance"])
            recs.append(r)
    t = tally(recs)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump({"parts": [os.path.basename(p) for p in paths], "scale": scale, "runs": recs, "tally": t}, f,
                  indent=1)
    write_md(os.path.join(out, "results.md"), recs, t, scale)
    print(json.dumps(t["predictions"]), flush=True)
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, default=30.0, help="divide the challenge's limit T(n) by this")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--mem-gb", type=float, default=3.3, help="memory budget for the running solver processes")
    ap.add_argument("--min-n", type=int, default=0, help="only instances with at least this many customers")
    ap.add_argument("--max-n", type=int, default=10 ** 9, help="only instances with at most this many customers")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--part", default="all", help="name of this part, for the output files")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--merge", default="", help="comma-separated results-<part>.json files: score them together")
    args = ap.parse_args()
    out = os.path.join(args.out_dir, "xltwrun")
    if args.merge:
        merge(args.merge.split(","), out)
        return
    logs, sols = os.path.join(out, "logs-" + args.part), os.path.join(out, "sols")
    for d in (out, logs, sols):
        os.makedirs(d, exist_ok=True)
    paths, digest = find_instances(args.data_dir)
    log("%d instance files%s" % (len(paths), "" if digest is None else ", archive sha256 %s" % digest))
    runs = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            inst = X.parse_any(f.read())
        n = len(inst["rows"]) - 1
        if args.min_n <= n <= args.max_n:
            runs.append(Run(p, inst, t_of(n) / args.scale, args.seed, os.path.join(HERE, "solver.py"), logs))
    log("%d runs, %.0f CPU-seconds of limits" % (len(runs), sum(r.limit for r in runs)))
    recs = []
    prog = open(os.path.join(out, "progress-%s.jsonl" % args.part), "a", encoding="utf-8")

    def on_done(r):
        try:
            rec = r.finish()
            if rec["exact_ok"]:
                with open(os.path.join(sols, "%s.sol" % r.name), "w", encoding="utf-8") as f:
                    f.write(write_sol(r.routes, rec["distance"]))
        except Exception:  # noqa: BLE001 - recorded
            rec = {"instance": r.name, "customers": r.n, "error": traceback.format_exc()}
        recs.append(rec)
        prog.write(json.dumps(rec) + "\n")
        prog.flush()
        log("done %s" % json.dumps({k: rec.get(k) for k in ("instance", "vehicles", "k", "distance", "at_s",
                                                             "sigterm_at", "peak_gb", "error")}))

    schedule(runs, args.workers, args.mem_gb, on_done)
    prog.close()
    t = tally(recs)  # G0-G5 are about all 100 instances: a part alone scores "untestable"
    res = {"pyvrp": "0.14.1 (pinned)", "scale": args.scale, "seed": args.seed, "part": args.part,
           "min_n": args.min_n, "max_n": args.max_n, "workers": args.workers, "mem_gb": args.mem_gb,
           "archive_sha256_expected": SHA256, "runs": recs, "tally_this_part": t}
    with open(os.path.join(out, "results-%s.json" % args.part), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    write_md(os.path.join(out, "results-%s.md" % args.part), recs, t, args.scale)
    print(json.dumps(t["predictions"]), flush=True)
    if t["errors"]:
        raise SystemExit("%d run(s) failed" % len(t["errors"]))


if __name__ == "__main__":
    main()
