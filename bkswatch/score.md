# bkswatch: scored

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.

Job `bkswatch-v1` ran on 2026-11-02 from 04:30 to 04:47 UTC (one CPU, peak 0.02 GB). It downloaded all 356 CVRPLib
VRPTW BKS files again into a fresh folder and checked each with the unchanged `vrptwd/double_check.py` (tag v0.3.4).
The predictions are in [expectations.md](expectations.md). They were written and committed (a1aef33) before any new
BKS file was opened, and `score_w()` in [bkswatch.py](bkswatch.py) scored them unchanged. Raw output:
[results.md](results.md), [results.json](results.json), [bks.csv](bks.csv) (one row per instance).

## Verdicts

| | Prediction | Verdict | What the files show |
|---|---|---|---|
| W0 | All 356 files download and parse, and every BKS is feasible under DIMACS with the cost in its file | **did not hold** | All 356 files downloaded and parsed, and all 356 are feasible under DIMACS. 355 of 356 cost lines match the routes. The exception is R1_10_6 (id 701), whose file says `Cost 468603`, while its routes give 46,860.3 (see below). |
| W1 | C1_10_9, R1_10_1, R1_10_5 and R1_10_9 changed, each to its announced value or lower | **held** | All four changed, and each file's cost equals the announced value: 40,278.7, 52,982.0, 50,365.5 and 49,088.1. |
| W2 | The new R1_10_1 uses fewer than 100 routes and is late somewhere in double precision | **held** | It uses 94 routes (95 before), with 8 late arrivals on 8 routes (largest 0.1056). Its double-precision fleet bound is 100. |
| W3 | At least 2 of the new C1_10_9, R1_10_5 and R1_10_9 are on time in double precision | **held** | C1_10_9 and R1_10_5 are on time. R1_10_9 is not: 1 late arrival of 0.1691. |
| W4 | Each of the four new BKSs keeps its predecessor's route count | **did not hold** | Only R1_10_5 did (92). C1_10_9 went from 90 to 91 routes, R1_10_1 from 95 to 94 and R1_10_9 from 91 to 92. |
| W5 | Apart from the four, at most 3 other BKSs differ from the reference | **untestable** | `score_w()` scores W5 only if W0 holds, so W5 is untestable as coded. One other BKS did differ (R1_10_6). Reading the prediction by its text alone, W5 would have held, but we do not count it, because the scoring rule was fixed in advance. |

In all: W1, W2 and W3 held; W0 and W4 did not; W5 was untestable.

## The five changed BKSs

Reference: the files read on 2026-10-30 (`vrptwd3/`). K = the double-precision fleet lower bound from `vrptwlb/`.

| id | instance | routes (was) | DIMACS cost from the routes (was) | late in double precision (was) | late arrivals, largest | double-precision distance | K |
|---|---|---|---|---|---|---|---|
| 684 | C1_10_9 | 91 (90) | 40,278.7 (40,282.2) | no (no) | 0 | 40,314.66 | 90 |
| 696 | R1_10_1 | 94 (95) | 52,982.0 (53,026.1) | yes (yes) | 8, 0.1056 | 53,028.11 | 100 |
| 700 | R1_10_5 | 92 (92) | 50,365.5 (50,388.5) | no (no) | 0 | 50,410.19 | 91 |
| 701 | R1_10_6 | 92 (91) | 46,860.3 (46,883.6) | yes (no) | 1, 0.0549 | 46,904.50 | 91 |
| 704 | R1_10_9 | 92 (91) | 49,088.1 (49,140.6) | yes (no) | 1, 0.1691 | 49,133.92 | 91 |

What changed:

- **R1_10_6 was not announced.** At 05:35 UTC on 2026-11-02 the newest entry on CVRPLib's updates page was dated
  2026-11-01, and it does not mention R1_10_6. CVRPLib's instance table already lists R1_10_6 at 46,860.3, so this is
  probably part of a daily digest that has not been posted yet.
- **The R1_10_6 file's cost line is 10 times the cost of its routes.** The routes are feasible under DIMACS and add up to
  46,860.3, the value in CVRPLib's instance table. The file's only non-route line is `Cost 468603`, the same digits with
  the decimal point missing. We read the file again directly at about 05:40 UTC (92 routes, `Cost 468603`). A tool
  that takes the BKS value from the file's cost line would read 468,603. The other 355 cost lines match their routes,
  including the four announced on 2026-11-01. This looks like a formatting slip in one file, not a wrong BKS.
- **Three of the five new BKSs use one route more than the solution they replaced** (C1_10_9, R1_10_6, R1_10_9).
  CVRPLib's VRPTW BKSs are ranked by distance only (the DIMACS 2021 rule), so a shorter solution with more routes is
  an improvement there. CVRPLib's VRPTW BKS Challenge ranks by vehicles first and distance second. Under that rule
  these three would rank below the solutions they replaced, which are no longer the published files.
- **Two BKSs that were on time in double precision no longer are** (R1_10_6, R1_10_9). Late BKSs went from 90 to 92
  of 356 (84 of the 300 Gehring-Homberger, 8 of the 56 Solomon). The new R1_10_1 still uses fewer routes (94) than
  any solution can that is on time in double precision (bound 100). The below-bound list is unchanged: R1_6_1 and
  R1_10_1.
- The other 351 BKSs are as they were on 2026-10-30.

## Limits

- This is one read of each file, five changed BKSs in all, too few to call it a trend.
- A BKS that is late in double precision is not an error. CVRPLib's VRPTW BKSs are defined under DIMACS (each arc
  truncated to 0.1), and every one of the 356 is feasible under that rule.
- Route-count changes are reported against our own 2026-10-30 read, not against any CVRPLib history.
- The R1_10_6 cost line is a mismatch between a file and its own routes. CVRPLib's table value is right. We do not
  know whether the slip comes from the submitted file or from the publishing step.
- None of the solutions here is ours, and none of this is a record by us.
