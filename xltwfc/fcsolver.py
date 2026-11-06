#!/usr/bin/env python3
"""xltwfc: xltw-solver with a fixed-cost fleet phase instead of the minimise_fleet loop (a pre-registered variant).

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.
Uses PyVRP 0.14.1 (MIT) for the search, and the published xltw-solver package (munimtechnologies/cvrplib-baselines,
xltwpkg/ at commit 19c7eb6: solver 0.1.0) for everything except the fleet phase: instance reading in the challenge's
convention, the fleet bound K, the stdout discipline, the throttled printer, the watchdog and the distance phase are
the package's own code, imported from its solver.py and not changed.

What differs, and only this (the fleet phase, half of the time left after the bound, as in the package):

1. One solve with the instance's own fleet until the first feasible solution (the package's loop starts the same
   way, with one vehicle fewer). Its route count is k0 and its distance d0.
2. Then ONE PyVRP solve, started from that solution, on a copy of the instance where every vehicle carries a fixed
   cost F = FACTOR x ceil(d0 / k0) (ten times the mean route length of the first solution) and at most k0 vehicles
   are available. PyVRP's iterated local search accepts moves on the penalised cost, so it may pass through
   solutions that are late somewhere with fewer routes; its best solution is always feasible. Every feasible best
   is offered to the printer (fewer routes first, then distance). It stops at the fleet deadline, on SIGTERM, or
   when a printed solution reaches K.

The package's loop instead removes one vehicle and searches from scratch for the first feasible solution, again and
again. In xltwfull/ part a (full limit), that search stalled: on n1234 the last count (34) was printed at 86 s and
the next attempt ran for the rest of the fleet phase (about 1,020 s) without success; on n1608 each step took about
twice as long as the one before (112 vehicles at 80 s, 111 at 151 s, 110 at 303 s, 109 at 586 s, 108 at 1,124 s).

Usage (as the challenge runs algorithms): fcsolver.py INSTANCE SECONDS SEED
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "lib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import json  # noqa: E402
import math  # noqa: E402
import signal  # noqa: E402
import time  # noqa: E402

import solver as S  # noqa: E402  the package's solver.py (0.1.0); S.START is the process start

VERSION = "0.1.0-fc1"
FACTOR = 10


def fixed_cost_for(distance, routes, factor=FACTOR):
    """F = factor x ceil(distance / routes): ten mean route lengths of the first feasible solution, at least 1."""
    if routes <= 0:
        raise ValueError("routes must be positive")
    return max(1, int(factor) * int(math.ceil(float(distance) / float(routes))))


def better(a, b):
    """True if solution key a = (routes, distance) beats b (None loses to anything)."""
    return b is None or a < b


def visits(sol):
    """Each route's client indices as PyVRP numbers them (depot 0), for Solution(data, routes)."""
    return [list(r.visits()) for r in sol.routes()]


class Holder:
    """The best feasible solution seen so far (fewest routes, then shortest), kept for the next phase."""

    def __init__(self):
        self.sol, self.key = None, None

    def offer(self, sol):
        if not sol.is_feasible():
            return False
        key = (int(sol.num_routes()), int(round(sol.distance())))
        if better(key, self.key):
            self.sol, self.key = sol, key
            return True
        return False


def run(path, limit, seed, out=None, watch=True, factor=FACTOR):
    S.load_helpers()
    X = S.X
    from pyvrp import IteratedLocalSearchCallbacks, IteratedLocalSearchParams, Solution, SolveParams, solve
    from pyvrp.stop import FirstFeasible, MultipleCriteria

    deadline = S.START + limit - S.margin(limit)
    seed = int(seed) % (2 ** 31)
    with open(path, encoding="utf-8") as f:
        inst = X.parse_any(f.read())
    n = len(inst["rows"]) - 1
    pr = S.Printer(limit, out=out)
    if watch:
        S.Watchdog(pr, S.START + limit - S.margin(limit) / 2.0, pr.out).start()
    b = S.bound(inst, S.BOUND_FRAC * limit)
    S.log("bound %s" % json.dumps(b))
    data = S.read_data(inst)
    stats = {"solver": "xltw-solver-fc " + VERSION, "instance": inst["name"], "customers": n, "limit": limit,
             "seed": seed, "bound": b, "fleet_solves": 0, "iterations": 0, "factor": factor, "fixed_cost": None,
             "first_vehicles": None, "first_seconds": None, "fc_iterations": 0, "fc_seconds": None}
    hold = Holder()

    def offer(sol):
        hold.offer(sol)
        pr.offer(sol)

    class OnBest(IteratedLocalSearchCallbacks):
        def on_best(self, sol):
            offer(sol)

    t_fleet = time.monotonic()
    fleet_deadline = t_fleet + S.FLEET_FRAC * max(deadline - t_fleet, 0.0)
    vt = data.vehicle_type(0)

    # 1. First feasible solution with the instance's own fleet.
    res = solve(data, stop=MultipleCriteria([FirstFeasible(), S.Until(fleet_deadline)]), seed=seed,
                collect_stats=False, display=False)
    stats["fleet_solves"] += 1
    offer(res.best)
    stats["first_seconds"] = round(time.monotonic() - t_fleet, 2)
    if hold.sol is None and not S.TERM["flag"]:  # nothing feasible in the fleet phase: keep trying to the deadline
        res = solve(data, stop=MultipleCriteria([FirstFeasible(), S.Until(deadline)]), seed=seed,
                    collect_stats=False, display=False)
        stats["fleet_solves"] += 1
        offer(res.best)
    pr.flush(True)

    # 2. One fixed-cost solve from that solution, to the fleet deadline (or K).
    if hold.sol is not None and not S.TERM["flag"] and time.monotonic() < fleet_deadline:
        k0, d0 = hold.key
        F = fixed_cost_for(d0, k0, factor)
        stats.update(first_vehicles=k0, fixed_cost=F)
        S.log("fixed-cost phase: k0 %d, d0 %d, F %d" % (k0, d0, F))
        dfc = data.replace(vehicle_types=[vt.replace(num_available=k0, fixed_cost=F)])
        t_fc = time.monotonic()

        def stop_fc(best_cost):  # noqa: ARG001
            if S.TERM["flag"] or time.monotonic() >= fleet_deadline:
                return True
            return hold.key is not None and hold.key[0] <= b["k"]

        params = SolveParams(ils=IteratedLocalSearchParams(callbacks=OnBest()))
        res = solve(dfc, stop=stop_fc, seed=seed, collect_stats=False, display=False, params=params,
                    initial_solution=Solution(dfc, visits(hold.sol)))
        stats["fleet_solves"] += 1
        stats["fc_iterations"] = int(res.num_iterations)
        stats["fc_seconds"] = round(time.monotonic() - t_fc, 1)
        offer(res.best)
        del dfc
    pr.flush(True)
    stats["fleet_seconds"] = round(time.monotonic() - t_fleet, 1)
    stats["fleet_vehicles"] = None if hold.key is None else hold.key[0]

    # 3. Distance phase, as in the package: that fleet, no fixed cost, from the best solution so far.
    if hold.sol is not None and not S.TERM["flag"] and time.monotonic() < deadline:
        d2 = data.replace(vehicle_types=[vt.replace(num_available=hold.key[0])])
        init = Solution(d2, visits(hold.sol))
        del data
        params = SolveParams(ils=IteratedLocalSearchParams(callbacks=OnBest()))
        res = solve(d2, stop=S.Until(deadline), seed=seed, collect_stats=False, display=False, params=params,
                    initial_solution=init)
        stats["iterations"] = int(res.num_iterations)
        offer(res.best)
    pr.flush(True)
    stats.update({"printed": pr.prints, "vehicles": None if pr.key is None else pr.key[0],
                  "cost": None if pr.key is None else pr.key[1], "sigterm": S.TERM["flag"],
                  "elapsed": round(time.monotonic() - S.START, 2)})
    sys.stderr.write("XLTW_SOLVER_STATS %s\n" % json.dumps(stats))
    sys.stderr.flush()
    return stats


def main(argv):
    if len(argv) != 4:
        sys.stderr.write("usage: fcsolver INSTANCE SECONDS SEED\n")
        return 2
    try:
        limit, seed = float(argv[2]), int(argv[3])
    except ValueError:
        sys.stderr.write("fcsolver: SECONDS must be a number and SEED an integer\n")
        return 2
    if not limit > 0:
        sys.stderr.write("fcsolver: SECONDS must be positive\n")
        return 2
    signal.signal(signal.SIGTERM, S._on_term)
    out = S.claim_stdout()
    run(argv[1], limit, seed, out=out)
    out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
