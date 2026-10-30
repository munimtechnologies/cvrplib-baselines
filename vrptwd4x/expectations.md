# Expectations written before vrptwd4-exact-v1 ran (2026-10-30 ~14:00 UTC)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.

**Background.** [`vrptwd4/`](../vrptwd4/score.md) repaired 87 of the 90 CVRPLib VRPTW best known solutions (BKSs)
that are late in double precision, each with no more routes than the BKS, and published them in `vrptwd4/sols/`.
Inside that job every repaired solution was checked by `vrptwd/double_check.py` only. Three of them use one route
fewer than the BKS (R2_2_1: 12 against 13, R2_2_2: 10 against 11, R2_6_5: 21 against 22). Before these solutions
are described anywhere else, they are checked a second way, as `vrptwd2/` did for `vrptwd/`.

**Method.** `exact_repair_check.py` downloads `vrptwd4/results.json` and the 87 solutions from this repository
(after they are committed), and each instance and BKS from CVRPLib (cached copies). It parses every file with the
`vrplib` package (2.2.0), not our own parser, and computes in exact 50-digit decimal arithmetic. Each solution is
checked under both conventions: double precision (time = Euclidean distance) and DIMACS (each arc truncated to one
decimal). The route count of each BKS is taken from the BKS file itself, not from `vrptwd4/`.

**Predictions** (scored by `score_x()` in `exact_repair_check.py`, written before the run):

| | Prediction | Basis | Our odds |
|---|---|---|---|
| X0 | All 87 solutions download and parse; each visits every customer once within capacity, has the route count `vrptwd4/results.json` states, and no more routes than its BKS file. | Hygiene; a failure means a file or publishing problem. | 95% |
| X1 | All 87 are on time everywhere in exact double-precision arithmetic (tolerance 1e-6, as before). | The repair worked on travel times rounded up to 0.001, and `double_check.py` agreed. | 95% |
| X2 | For all 87, the exact double-precision distance is within 0.006 of both the solution file's `Cost` line and `vrptwd4/results.json`. | Two-decimal rounding of the same sum. | 95% |
| X3 | All 87 are also on time under DIMACS, with an exact DIMACS cost within 0.05 of `vrptwd4/results.json`. | Truncation only shortens arcs, so on time in double precision means on time under DIMACS. | 95% |
| X4 | R2_2_1, R2_2_2 and R2_6_5 are on time in double precision with 12, 10 and 21 routes, against 13, 11 and 22 in their BKS files. | As reported by `vrptwd4/`. | 95% |

Only reported, not predicted: the smallest double-precision slack per solution and how many come within 0.01 of a
due time.

**Limits stated in advance.** This checks the published files, not how they were found. Fewer routes than a BKS
that minimises distance only is not an improvement under either convention: the three solutions are longer than
their BKSs, and hierarchical records (fewest vehicles first) for these instances use far fewer vehicles. Results
will be reported in full, including predictions that fail.

**Note added 2026-10-30 ~16:00 UTC, before any data was read.** The first run (`vrptwd4-exact-v1`) read nothing:
the `vrptwd4/` files had not reached this repository, so it waited two hours for `vrptwd4/results.json` and stopped
on the 404. The code and predictions above are unchanged; the same code runs again as `vrptwd4-exact-v2` with a
longer wait.
