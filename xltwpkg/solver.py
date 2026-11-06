#!/usr/bin/env python3
"""xltw-solver 0.1.0: a vehicles-first PyVRP solver packaged for CVRPLib's VRPTW Challenge (algorithm track).

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.
Uses PyVRP 0.14.1 (MIT) for the search. The method is the `xltwrun/solver.py` baseline of
munimtechnologies/cvrplib-baselines (commit ba1eec8), unchanged; this file only adds what an offline,
protocol-exact package needs:

- It finds its own code and its unpacked dependencies (`lib/`, made by build.sh) without pip, a venv or a network.
- Its stdout carries solutions only. At start it keeps a private copy of file descriptor 1 for solutions and points
  fd 1 and `sys.stdout` at stderr, so library logging (PyVRP attaches a log handler to stdout), stray prints and
  C-level writes all land on stderr.
- A watchdog thread ends the process on time even if the search is stuck inside one long C++ call (see Watchdog):
  at a hard deadline just before the limit, or at once on SIGTERM, it prints any held better solution and exits 0.

Usage (as the challenge runs algorithms): ./solver INSTANCE SECONDS SEED

- Reads a VRPLIB VRPTW instance (one depot). Distances and travel times are Euclidean, rounded to the nearest
  integer per arc, floor(d + 0.5), as the challenge's rules say.
- Fleet lower bound K = max(Martello-Toth L2, time-window clique) from `xltwlb.py`, given at most 10% of the limit;
  if that is not enough, the capacity bound ceil(total demand / capacity) is used instead.
- Fleet phase, half of the time left: PyVRP's minimise_fleet loop (one vehicle fewer, solve to the first feasible
  solution, shrink to the routes used, repeat), stopped at K.
- Distance phase, the rest: PyVRP's `solve` with that fleet, started from the fleet phase's solution.
- Every better solution (fewer routes first, then shorter) is printed in CVRPLib format, at most once per
  max(1 s, 1% of the limit); the best one is always printed before the solver stops. Nothing else goes to stdout.
- The solver stops by itself shortly before the limit (1.5 s + 0.2% of the limit, at most 30 s early); the
  watchdog's hard deadline is half that margin before the limit, and SIGTERM ends the process at once.

Single-threaded: PyVRP's search runs on one thread, and BLAS thread pools are pinned to one thread. Runs are
seeded, but they stop on the wall clock, so two runs with the same seed can end at different solutions.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "lib")):  # lib/ ends up first, ahead of any system site-packages
    if _p not in sys.path:
        sys.path.insert(0, _p)
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import json  # noqa: E402
import math  # noqa: E402
import select  # noqa: E402
import signal  # noqa: E402
import tempfile  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402

START = time.monotonic()
VERSION = "0.1.0"
CONV = "round"
BOUND_FRAC = float(os.environ.get("XLTW_BOUND_FRAC", "0.10"))
FLEET_FRAC = 0.5
TERM = {"flag": False}
OUT = None  # the real stdout once claim_stdout() has run
B = None    # xltwbase, loaded by load_helpers()
X = None    # xltwlb


def claim_stdout():
    """Keep fd 1 for solutions only. Returns a text stream on a private copy of the original stdout; afterwards
    fd 1 and sys.stdout both point at stderr."""
    global OUT
    sys.stdout.flush()
    fd = os.dup(1)
    os.dup2(2, 1)
    OUT = os.fdopen(fd, "w", encoding="ascii", newline="\n")
    sys.stdout = sys.stderr
    return OUT


def load_helpers():
    global B, X
    if B is None:
        import xltwbase
        import xltwlb
        B, X = xltwbase, xltwlb
    return B, X


def margin(limit):
    """How long before the limit the solver stops by itself."""
    return min(1.5 + 0.002 * limit, 30.0)


def log(msg):
    sys.stderr.write("[%8.1fs] %s\n" % (time.monotonic() - START, msg))
    sys.stderr.flush()


def _on_term(signum, frame):  # noqa: ARG001
    TERM["flag"] = True


class Until:
    """PyVRP stopping criterion: an absolute monotonic deadline, or SIGTERM."""

    def __init__(self, deadline):
        self.deadline = deadline

    def __call__(self, best_cost):  # noqa: ARG002
        return TERM["flag"] or time.monotonic() >= self.deadline


class _Timeout(BaseException):
    """Raised by SIGALRM inside the bound. BaseException, so no `except Exception` in the bound code catches it."""


def capacity_bound(inst):
    total = sum(r[2] for r in inst["rows"][1:])
    return max(1, int(math.ceil(total / float(inst["capacity"]))))


def bound(inst, cap_seconds):
    """K in the challenge's convention with a time cap. Falls back to the capacity bound if the cap is hit."""
    kc = capacity_bound(inst)
    out = {"kc": kc, "kb": None, "kt": None, "k": kc, "timed_out": False, "seconds": 0.0}
    if cap_seconds <= 0:
        out["timed_out"] = True
        return out

    def _alarm(signum, frame):  # noqa: ARG001
        raise _Timeout()

    old = signal.signal(signal.SIGALRM, _alarm)
    t = time.monotonic()
    signal.setitimer(signal.ITIMER_REAL, cap_seconds)
    try:
        b = B.lower_bound(inst, CONV)
        k = b["k"] if b.get("clique_verified") is not False else b["kb"]
        out.update(kb=b["kb"], kt=b["kt"], k=max(int(k), kc))
    except _Timeout:
        out["timed_out"] = True
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)
    out["seconds"] = round(time.monotonic() - t, 2)
    return out


def format_solution(routes, cost):
    lines = ["Route #%d: %s" % (i + 1, " ".join(map(str, r))) for i, r in enumerate(routes)]
    lines.append("Cost: %d" % cost)
    return "\n".join(lines) + "\n"


def solution_routes(sol):
    """Customer numbers 1..n of every route of a PyVRP 0.14 solution."""
    return [B.route_clients(r) for r in sol.routes()]


class Printer:
    """Prints strictly better solutions (fewer routes, then lower cost), throttled to one print per `gap` seconds.
    A better solution that arrives within the gap is held and printed at the next chance or at `flush(True)`."""

    def __init__(self, limit, out=None, convert=solution_routes, clock=time.monotonic):
        self.gap = max(1.0, 0.01 * limit)
        self.out = out if out is not None else (OUT if OUT is not None else sys.stdout)
        self.convert = convert
        self.clock = clock
        self.key = None       # (routes, cost) of the last printed solution
        self.pending = None   # (key, solution) better than the last printed one, not printed yet
        self.last = None
        self.prints = 0
        self.lock = threading.RLock()  # the watchdog thread may flush too

    def best_key(self):
        return self.pending[0] if self.pending else self.key

    def offer(self, sol):
        if not sol.is_feasible():
            return False
        key = (int(sol.num_routes()), int(round(sol.distance())))
        with self.lock:
            best = self.best_key()
            if best is not None and key >= best:
                return False
            self.pending = (key, sol)
            self.flush(False)
        return True

    def flush(self, force):
        with self.lock:
            if self.pending is None:
                return False
            now = self.clock()
            if not force and self.last is not None and now - self.last < self.gap:
                return False
            key, sol = self.pending
            self.out.write(format_solution(self.convert(sol), key[1]))
            self.out.flush()
            self.key, self.pending, self.last = key, None, now
            self.prints += 1
            return True


class Watchdog:
    """Ends the process on time even when the search is stuck inside one long C++ call.

    Seen on XLTW-Test-n8575 at T/30 (cvrplib-baselines xltwrun part b2): after 64 s one PyVRP call ran past the
    limit, the solver never reached its own stopping check, and SIGTERM could not help, because a Python signal
    handler only runs when the main thread returns to Python. PyVRP's local search and perturbation release the
    GIL, so this thread still runs then. It wakes at `hard_deadline` (after the solver's own stopping point, before
    the limit) or as soon as SIGTERM arrives (through signal.set_wakeup_fd, whose byte is written by the C-level
    handler at once), prints any held better solution, flushes stdout and exits with code 0."""

    def __init__(self, printer, hard_deadline, out):
        self.printer, self.hard, self.out = printer, hard_deadline, out
        self.r, self.w = os.pipe()
        os.set_blocking(self.r, False)
        os.set_blocking(self.w, False)
        signal.set_wakeup_fd(self.w)  # main thread only
        self.thread = threading.Thread(target=self._loop, name="xltw-watchdog", daemon=True)

    def start(self):
        self.thread.start()
        return self

    def _loop(self):
        why = "deadline"
        while True:
            left = self.hard - time.monotonic()
            if left <= 0:
                break
            ready, _, _ = select.select([self.r], [], [], min(left, 0.5))
            if ready:
                try:
                    data = os.read(self.r, 512)
                except (BlockingIOError, InterruptedError):
                    data = b""
                if int(signal.SIGTERM) in data:
                    why = "sigterm"
                    break
        self.fire(why)

    def fire(self, why):
        try:
            with self.printer.lock:
                self.printer.flush(True)
                self.out.flush()
        finally:
            sys.stderr.write("XLTW_WATCHDOG %s at %.2fs, prints %d\n" % (why, time.monotonic() - START,
                                                                          self.printer.prints))
            sys.stderr.flush()
            os._exit(0)


def read_data(inst):
    """PyVRP data in the challenge's convention, from the parsed instance (depot first)."""
    import pyvrp
    fd, path = tempfile.mkstemp(suffix=".vrp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(B.to_vrplib(inst))
        return pyvrp.read(path, round_func=B.rf_round)
    finally:
        os.remove(path)


def run(path, limit, seed, out=None, watch=True):
    """Solve one instance under the protocol. Returns the stats dict (also logged to stderr)."""
    load_helpers()
    from pyvrp import IteratedLocalSearchCallbacks, IteratedLocalSearchParams, Solution, SolveParams, solve
    from pyvrp.stop import FirstFeasible, MultipleCriteria

    deadline = START + limit - margin(limit)
    seed = int(seed) % (2 ** 31)
    with open(path, encoding="utf-8") as f:
        inst = X.parse_any(f.read())
    n = len(inst["rows"]) - 1
    pr = Printer(limit, out=out)
    if watch:
        Watchdog(pr, START + limit - margin(limit) / 2.0, pr.out).start()
    b = bound(inst, BOUND_FRAC * limit)
    log("bound %s" % json.dumps(b))
    data = read_data(inst)
    stats = {"solver": "xltw-solver " + VERSION, "instance": inst["name"], "customers": n, "limit": limit,
             "seed": seed, "bound": b, "fleet_solves": 0, "iterations": 0}

    # Fleet phase: minimise_fleet's loop, stopped at K. `cur` always holds the data with the last feasible fleet,
    # so at most two copies of the matrices exist at a time.
    t_fleet = time.monotonic()
    fleet_deadline = t_fleet + FLEET_FRAC * max(deadline - t_fleet, 0.0)
    cur, feas, best = data, data.vehicle_type(0), None
    del data
    while feas.num_available > b["k"] and not TERM["flag"] and time.monotonic() < fleet_deadline:
        fleet = feas.replace(num_available=feas.num_available - 1)
        trial = cur.replace(vehicle_types=[fleet])
        res = solve(trial, stop=MultipleCriteria([FirstFeasible(), Until(fleet_deadline)]), seed=seed,
                    collect_stats=False, display=False)
        stats["fleet_solves"] += 1
        if not res.best.is_feasible():
            del trial
            break
        best = res.best
        pr.offer(best)
        feas = fleet.replace(num_available=min(fleet.num_available, best.num_routes()))
        cur = trial
    if best is None and not TERM["flag"]:  # already at K, or the first attempt failed: one solve, full fleet
        res = solve(cur, stop=MultipleCriteria([FirstFeasible(), Until(deadline)]), seed=seed, collect_stats=False,
                    display=False)
        stats["fleet_solves"] += 1
        if res.best.is_feasible():
            best = res.best
            pr.offer(best)
            feas = feas.replace(num_available=best.num_routes())
    pr.flush(True)
    stats["fleet_seconds"] = round(time.monotonic() - t_fleet, 1)
    stats["fleet_vehicles"] = None if best is None else int(best.num_routes())

    # Distance phase: solve with the fleet found, from the fleet phase's solution.
    if best is not None and not TERM["flag"] and time.monotonic() < deadline:
        routes0 = [[c - 1 for c in r] for r in solution_routes(best)]
        d2 = cur.replace(vehicle_types=[feas])
        del cur

        class OnBest(IteratedLocalSearchCallbacks):
            def on_best(self, sol):
                pr.offer(sol)

        params = SolveParams(ils=IteratedLocalSearchParams(callbacks=OnBest()))
        res = solve(d2, stop=Until(deadline), seed=seed, collect_stats=False, display=False, params=params,
                    initial_solution=Solution(d2, routes0))
        stats["iterations"] = int(res.num_iterations)
        pr.offer(res.best)
    pr.flush(True)
    stats.update({"printed": pr.prints, "vehicles": None if pr.key is None else pr.key[0],
                  "cost": None if pr.key is None else pr.key[1], "sigterm": TERM["flag"],
                  "elapsed": round(time.monotonic() - START, 2)})
    sys.stderr.write("XLTW_SOLVER_STATS %s\n" % json.dumps(stats))
    sys.stderr.flush()
    return stats


def main(argv):
    if len(argv) != 4:
        sys.stderr.write("usage: solver INSTANCE SECONDS SEED\n")
        return 2
    try:
        limit, seed = float(argv[2]), int(argv[3])
    except ValueError:
        sys.stderr.write("solver: SECONDS must be a number and SEED an integer\n")
        return 2
    if not limit > 0:
        sys.stderr.write("solver: SECONDS must be positive\n")
        return 2
    signal.signal(signal.SIGTERM, _on_term)
    out = claim_stdout()
    run(argv[1], limit, seed, out=out)
    out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
