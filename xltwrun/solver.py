#!/usr/bin/env python3
"""xltw-solver: a vehicles-first PyVRP solver that follows the run protocol of CVRPLib's VRPTW BKS Challenge.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.
Uses PyVRP 0.14.1 (MIT) for the search. Nothing here is a new method: it is the `xltwbase.py` baseline of
cvrplib-baselines, wrapped so that it can be run exactly as the challenge runs algorithms.

Usage: python solver.py INSTANCE SECONDS SEED

- Reads a VRPLIB VRPTW instance (one depot). Distances and travel times are Euclidean, rounded to the nearest
  integer per arc, floor(d + 0.5), as the challenge's rules say (TSPLIB EUC_2D, travel time = distance).
- Fleet lower bound K = max(Martello-Toth L2, time-window clique) from `xltwlb.py`, given at most 10% of the time
  limit; if that is not enough, the capacity bound ceil(total demand / capacity) is used instead.
- Fleet phase, half of the time left: PyVRP 0.14.1's `minimise_fleet` loop (one vehicle fewer, solve to the first
  feasible solution, shrink to the routes used, repeat), stopped at K.
- Distance phase, the rest: PyVRP's `solve` with that fleet, started from the fleet phase's solution.
- Every better solution (fewer routes first, then shorter) is printed to stdout in CVRPLib format, at most once per
  max(1 s, 1% of the limit); the best one is always printed before the solver stops. Customers are numbered 1..n in
  file order after the depot. Nothing else is written to stdout; a one-line summary goes to stderr.
- The solver stops by itself shortly before the limit (1.5 s + 0.2% of the limit, at most 30 s early), and as soon
  as it can after SIGTERM.

Single-threaded: PyVRP's search runs on one thread, and BLAS thread pools are pinned to one thread below. Runs are
seeded, but they stop on the wall clock, so two runs with the same seed can differ on machines of different speed.
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import json  # noqa: E402
import math  # noqa: E402
import signal  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402

START = time.monotonic()

import xltwbase as B  # noqa: E402
import xltwlb as X  # noqa: E402

CONV = "round"
BOUND_FRAC = float(os.environ.get("XLTW_BOUND_FRAC", "0.10"))
FLEET_FRAC = 0.5
TERM = {"flag": False}


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
    """Customer numbers 1..n of every route of a PyVRP 0.14 solution (as xltwbase.route_clients)."""
    return [B.route_clients(r) for r in sol.routes()]


class Printer:
    """Prints strictly better solutions (fewer routes, then lower cost), throttled to one print per `gap` seconds.
    A better solution that arrives within the gap is held and printed at the next chance or at `flush(True)`."""

    def __init__(self, limit, out=None, convert=solution_routes, clock=time.monotonic):
        self.gap = max(1.0, 0.01 * limit)
        self.out = out or sys.stdout
        self.convert = convert
        self.clock = clock
        self.key = None       # (routes, cost) of the last printed solution
        self.pending = None   # (key, solution) better than the last printed one, not printed yet
        self.last = None
        self.prints = 0

    def best_key(self):
        return self.pending[0] if self.pending else self.key

    def offer(self, sol):
        if not sol.is_feasible():
            return False
        key = (int(sol.num_routes()), int(round(sol.distance())))
        best = self.best_key()
        if best is not None and key >= best:
            return False
        self.pending = (key, sol)
        self.flush(False)
        return True

    def flush(self, force):
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


def run(path, limit, seed, out=None):
    """Solve one instance under the protocol. Returns the stats dict (also logged to stderr)."""
    from pyvrp import IteratedLocalSearchCallbacks, IteratedLocalSearchParams, Solution, SolveParams, solve
    from pyvrp.stop import FirstFeasible, MultipleCriteria

    deadline = START + limit - margin(limit)
    seed = int(seed) % (2 ** 31)
    with open(path, encoding="utf-8") as f:
        inst = X.parse_any(f.read())
    n = len(inst["rows"]) - 1
    pr = Printer(limit, out=out)
    b = bound(inst, BOUND_FRAC * limit)
    log("bound %s" % json.dumps(b))
    data = read_data(inst)
    stats = {"instance": inst["name"], "customers": n, "limit": limit, "seed": seed, "bound": b,
             "fleet_solves": 0, "iterations": 0}

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
        sys.stderr.write("usage: solver.py INSTANCE SECONDS SEED\n")
        return 2
    signal.signal(signal.SIGTERM, _on_term)
    run(argv[1], float(argv[2]), int(argv[3]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
