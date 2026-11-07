#!/usr/bin/env python3
"""xltwdet: xltw-solver with a work budget instead of the wall clock, so that a run is deterministic for its seed.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.
Uses PyVRP 0.14.1 (MIT) for the search, and the published xltw-solver package (munimtechnologies/cvrplib-baselines,
xltwpkg/ at commit 19c7eb6: solver 0.1.0) for everything else: instance reading in the challenge's convention, the
fleet bound K, the stdout discipline, the throttled printer, the watchdog and the method (minimise_fleet's loop
stopped at K, then the distance phase from its solution) are the package's own code or the same steps, unchanged.

Why. The VRPTW Challenge's rules say "Each execution must be deterministic for a given seed". Solver 0.1.0 stops
both phases on the wall clock, so the same seed can end at different solutions on a faster or slower or busier
machine (its conformance test C5b: two runs with seed 7 on n1094 did 9,021 and 9,879 iterations).

What differs, and only this: each phase stops on a number of PyVRP iterations fixed in advance from the two
inputs that are the same on every machine, the number of customers n and the time limit T:

    budget(n, T) = floor(SAFETY x RATE0 x (n / 1000) ** -RATE_EXP x (T - margin(T)))

RATE0 x (n / 1000) ** -RATE_EXP is a deliberately low estimate of PyVRP 0.14.1's iterations per second on our hosts
(fitted on earlier runs' logs: about 250-450 it/s at n of 1,000-1,800 and about 120 it/s at n = 8,574), and SAFETY
leaves room for slower machines. The fleet phase may use FLEET_FRAC of the budget (counted over all its solves,
each to its first feasible solution), the distance phase the rest. The wall clock stays only as a safety net: if a
phase reaches the solver's usual stopping point first, it stops there, as 0.1.0 does, and the run is flagged
(`clock_stop` in the stats line), because from that point on it is no longer deterministic.

0.1.0-det2 (2026-11-07, xltwdet/addendum-2026-11-07.md) differs from det1 only in that the environment variable
XLTW_DET_SAFETY, if set, replaces SAFETY. It exists for the unit test only: the rate model, fitted at n >= 1,047,
overestimates PyVRP's speed on the test's 80-customer instance, so det1's own end-to-end test fell back to the clock.
The study's runs never set it, and every stats line records the safety used.

Usage (as the challenge runs algorithms): detsolver.py INSTANCE SECONDS SEED
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

VERSION = "0.1.0-det2"
RATE0 = 300.0      # iterations per second at n = 1,000 (a low estimate)
RATE_EXP = 0.5     # rate ~ n ** -0.5
SAFETY = 0.6       # share of the estimated iterations actually budgeted
SAFETY_ENV = "XLTW_DET_SAFETY"  # unit tests only


def safety_from_env(env=None):
    env = os.environ if env is None else env
    v = env.get(SAFETY_ENV, "")
    if not v:
        return SAFETY
    s = float(v)
    if not 0.0 < s <= 1.0:
        raise ValueError("%s must be in (0, 1]" % SAFETY_ENV)
    return s


def iteration_budget(n, limit, safety=SAFETY):
    """Total PyVRP iterations for a run on n customers with time limit `limit` (seconds). Depends on n and the
    limit only, never on the machine."""
    n = max(int(n), 1)
    usable = max(float(limit) - S.margin(float(limit)), 0.0)
    rate = RATE0 * (n / 1000.0) ** (-RATE_EXP)
    return int(math.floor(safety * rate * usable))


class Budget:
    """PyVRP stopping criterion that counts iterations: stops when `left` reaches 0 (deterministic), and as a
    safety net at the wall-clock `deadline` or on SIGTERM (then `clock_stop` / `term_stop` is set)."""

    def __init__(self, left, deadline, clock=time.monotonic):
        self.left, self.used, self.deadline, self.clock = int(left), 0, deadline, clock
        self.clock_stop = self.term_stop = False

    def __call__(self, best_cost):  # noqa: ARG002
        if S.TERM["flag"]:
            self.term_stop = True
            return True
        if self.clock() >= self.deadline:
            self.clock_stop = True
            return True
        if self.left <= 0:
            return True
        self.left -= 1
        self.used += 1
        return False

    def exhausted(self):
        return self.left <= 0 or self.clock_stop or self.term_stop


def run(path, limit, seed, out=None, watch=True, safety=SAFETY):
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
    total = iteration_budget(n, limit, safety)
    fleet_budget = int(math.floor(S.FLEET_FRAC * total))
    S.log("work budget: %d iterations (fleet phase up to %d)" % (total, fleet_budget))
    stats = {"solver": "xltw-solver-det " + VERSION, "instance": inst["name"], "customers": n, "limit": limit,
             "seed": seed, "bound": b, "mode": "work", "budget": total, "fleet_budget": fleet_budget,
             "safety": safety, "fleet_solves": 0, "fleet_iterations": 0, "iterations": 0, "clock_stop": None}

    # Fleet phase: minimise_fleet's loop as in the package, stopped at K or when the fleet budget is spent.
    t_fleet = time.monotonic()
    fb = Budget(fleet_budget, deadline)
    cur, feas, best = data, data.vehicle_type(0), None
    del data
    while feas.num_available > b["k"] and not S.TERM["flag"] and not fb.exhausted():
        fleet = feas.replace(num_available=feas.num_available - 1)
        trial = cur.replace(vehicle_types=[fleet])
        res = solve(trial, stop=MultipleCriteria([fb, FirstFeasible()]), seed=seed, collect_stats=False,
                    display=False)
        stats["fleet_solves"] += 1
        if not res.best.is_feasible():
            del trial
            break
        best = res.best
        pr.offer(best)
        feas = fleet.replace(num_available=min(fleet.num_available, best.num_routes()))
        cur = trial
    rest = Budget(total - fb.used, deadline)
    if best is None and not S.TERM["flag"]:  # already at K, or the first attempt failed: one solve, full fleet
        res = solve(cur, stop=MultipleCriteria([rest, FirstFeasible()]), seed=seed, collect_stats=False,
                    display=False)
        stats["fleet_solves"] += 1
        if res.best.is_feasible():
            best = res.best
            pr.offer(best)
            feas = feas.replace(num_available=best.num_routes())
    pr.flush(True)
    stats["fleet_iterations"] = fb.used
    stats["fleet_seconds"] = round(time.monotonic() - t_fleet, 1)
    stats["fleet_vehicles"] = None if best is None else int(best.num_routes())

    # Distance phase: the fleet found, from the fleet phase's solution, with the rest of the budget.
    if best is not None and not S.TERM["flag"] and not rest.exhausted():
        routes0 = [[c - 1 for c in r] for r in S.solution_routes(best)]
        d2 = cur.replace(vehicle_types=[feas])
        del cur

        class OnBest(IteratedLocalSearchCallbacks):
            def on_best(self, sol):
                pr.offer(sol)

        params = SolveParams(ils=IteratedLocalSearchParams(callbacks=OnBest()))
        res = solve(d2, stop=rest, seed=seed, collect_stats=False, display=False, params=params,
                    initial_solution=Solution(d2, routes0))
        stats["iterations"] = int(res.num_iterations)
        pr.offer(res.best)
    pr.flush(True)
    stats["distance_budget_used"] = rest.used
    stats["clock_stop"] = "fleet" if fb.clock_stop else ("distance" if rest.clock_stop else False)
    stats["term_stop"] = fb.term_stop or rest.term_stop
    stats.update({"printed": pr.prints, "vehicles": None if pr.key is None else pr.key[0],
                  "cost": None if pr.key is None else pr.key[1], "sigterm": S.TERM["flag"],
                  "elapsed": round(time.monotonic() - S.START, 2)})
    sys.stderr.write("XLTW_SOLVER_STATS %s\n" % json.dumps(stats))
    sys.stderr.flush()
    return stats


def main(argv):
    if len(argv) != 4:
        sys.stderr.write("usage: detsolver INSTANCE SECONDS SEED\n")
        return 2
    try:
        limit, seed = float(argv[2]), int(argv[3])
        safety = safety_from_env()
    except ValueError as e:
        sys.stderr.write("detsolver: SECONDS must be a number and SEED an integer (%s)\n" % e)
        return 2
    if not limit > 0:
        sys.stderr.write("detsolver: SECONDS must be positive\n")
        return 2
    signal.signal(signal.SIGTERM, S._on_term)
    out = S.claim_stdout()
    run(argv[1], limit, seed, out=out, safety=safety)
    out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
