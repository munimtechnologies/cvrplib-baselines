# Scoring of vrptwd (double-precision re-check), against expectations written before the run

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Scored 2026-10-29 ~22:20Z from job
`vrptw-double-v1` (ran 2026-10-29 18:57-19:01Z, exit 0, unit tests passed). Raw output:
[results.json](results.json), [results.md](results.md). Expectations: [expectations.md](expectations.md).

| | expectation (as written) | outcome | verdict |
|---|---|---|---|
| D0 | every one of the 86 solutions is DIMACS-feasible and reproduces its file's Cost line (`tally.dimacs_hygiene_fail` is empty) | `dimacs_hygiene_fail` = [] | **holds** |
| D1 | none of the 23 Solomon PyVRP solutions is better than the SINTEF record in double precision; `tally.pyvrp_double_better_than_sintef` has no Solomon instance | `pyvrp_double_better_than_sintef` = [] | **holds** |
| D2 | at least 12 of those 23 are still feasible in double precision (`pyvrp_solomon_looks_better_double_feasible` >= 12) | 18 | **holds** |
| D3 | on R1_10_1 both CVRPLib's 95-route BKS and PyVRP's 94-route solution are infeasible in double precision | BKS: 7 late arrivals on 7 routes (max 0.1245); PyVRP: 8 late arrivals on 8 routes (max 0.1056) | **holds** |
| D4 | at least 50 of the 56 Solomon CVRPLib BKSs are feasible in double precision (`solomon_bks_double_feasible` >= 50) | 48 | **fails** |

## What it shows

- **The convention decides feasibility, not just decimals.** CVRPLib's VRPTW best known solutions are kept
  under the DIMACS convention (each arc truncated to 0.1, travel time = that distance). Re-checked in double
  precision, 8 of the 56 Solomon BKSs arrive late somewhere (R102, R105, R107, R108, R112, R211, RC101,
  RC105; one late arrival each, 0.07 to 0.40 time units), and so do two of the six 1,000-customer BKSs
  (R1_10_1: 7 late arrivals; RC2_10_1: 2). D4 failed because 8 is more than the 6 allowed.
- **R1_10_1.** CVRPLib's BKS uses 95 routes and SINTEF's hierarchical record uses 100. The 95-route
  solution is feasible only with truncated travel times. So the five-vehicle difference is a difference of
  convention, not a better solution under SINTEF's rules (PyVRP's 94-route solution is the same case).
- **The 23 PyVRP results that looked shorter than SINTEF's records under DIMACS** are not: 5 are infeasible
  in double precision, 10 equal the record (to 0.005) and 8 are longer. None is better (D1).
- Where a CVRPLib Solomon BKS is feasible in double precision, it never beats SINTEF's record: either it uses
  more vehicles (CVRPLib's BKSs minimise distance only) or it equals the record (all 17 C instances, RC103,
  RC104). On three 1,000-customer instances (C1_10_1, C2_10_1, RC1_10_1) the BKS has the record's number of
  vehicles and is 0.02 to 0.13 longer in double precision: a different solution, not a better one.

## Not claimed

None of this is an error by CVRPLib, DIMACS or SINTEF. The two conventions are documented and both are in use
(the 12th DIMACS Implementation Challenge specifies truncation; SINTEF's pages use double precision). That
the conventions differ is well known; what this adds is the per-instance list of which published DIMACS BKSs
fail in double precision, and by how much. Before it is described anywhere else, a second, independently
written check (exact 50-digit arithmetic, separate parser) re-tests every row: see `vrptwd2/` in this
repository.

Limits: lateness is counted with a tolerance of 1e-6; service times and time windows are taken from the
instance files as published on CVRPLib; distances are reported to 2 decimals; SINTEF figures were read from
its pages on 2026-10-29 and are embedded in `double_check.py`.
