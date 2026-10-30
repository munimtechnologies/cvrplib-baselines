# Scoring of vrptwd5-anatomy (where on their routes the VRPTW BKSs turn late in double precision)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.

The predictions were written before the run: [expectations.md](expectations.md) (2026-10-30, about 08:50 UTC).
The job `vrptwd5-anatomy-v1` ran on 2026-10-30 from 10:19 to 10:45 UTC on one CPU (peak memory 0.02 GB): the unit
tests passed, then `anatomy.py --ids 380-735` read all 356 Solomon and Homberger instances and best known solutions
(BKSs) from CVRPLib, ran the unchanged `vrptwd/double_check.py` on each, and followed every route under both
conventions at once. The verdicts below are the ones `score_a()` computed in the job (`results.json`,
`tally.predictions`); nothing was re-scored by hand.

Terms (from the expectations): a visit is **exposed** if its DIMACS slack, in tenths, is smaller than the number of
arcs driven since the vehicle last waited, the only way it can turn late in double precision. A route is
**horizon-bound** if it returns to the depot within 1.0 of the depot's closing time under DIMACS. A route's
**wait share** is the share of its customers where the vehicle waits under DIMACS.

| | Prediction (as written) | Result | Verdict |
|---|---|---|---|
| A0 | 356 BKSs read, DIMACS costs equal the files, exactly 90 late, late counts per instance and route equal `double_check.py`'s, every late visit exposed. | 356 rows, no DIMACS or count mismatch, 90 late BKSs with 141 late routes, 0 late visits unexposed | **held** |
| A1 | In Homberger C2, the route late rate at 800 and 1,000 customers is at most twice the rate at 200 to 600. | 3.33% (18 of 540 routes) against 1.08% (4 of 369): 3.1 times | **did not hold** |
| A2 | At least 75% of the late C2 routes are horizon-bound. | 6 of 22 (27%) | **did not hold** |
| A3 | The horizon-bound share among late R1 and RC1 routes is lower than among late C2 routes. | 4.8% (3 of 62) against 27% | **held** |
| A4 | Among Homberger C2 routes, late routes have a lower mean wait share than the other routes. | 0.9% against 4.8% | **held** |
| A5 | The number of exposed visits separates late from on-time BKSs with an AUC of at least 0.80. | AUC 0.865 | **held** |

**The C2 question, answered as far as these data go.** `vrptwd3/` asked why lateness concentrates in C2 at 800 and
1,000 customers. A1 shows the concentration is real at the route level too: it is not just that larger instances
have more routes. A2's idea, that C2 routes turn late because they run up against the depot's closing time, is
mostly wrong: only 6 of the 22 late C2 routes are horizon-bound, and across all 141 late routes only 4 turn late
first at the depot. What the late C2 routes share is that they almost never wait. 15 of the 22 never wait at all,
and the other 7 wait once. Their first late visit comes after a median of 28.5 arcs without a wait (range 7 to 38),
so the up-to-0.1-per-arc drift between the two conventions builds up over most of the route. That is also why C2 has
the largest lateness values (0.69 to 1.27 time units after 25 to 37 arcs). R and RC routes wait, on average, at 21% to
50% of their customers (by family and size), so their drift keeps resetting.

**What this does not explain (exploratory, not pre-registered).** Counting from `routes.csv`, C2 routes that never
wait are more common at the larger sizes: 43%, 32%, 47%, 46% and 52% of routes at 200, 400, 600, 800 and 1,000
customers. That accounts for only part of A1. The late rate rises at 800 and 1,000 customers both among routes that
never wait (2.0%, 3 of 152, at 200 to 600 against 4.5%, 12 of 268) and among routes that wait (0.5%, 1 of 217,
against 2.2%, 6 of 272). We have not found the rest of the reason and do not guess one. A natural next measure,
which should be pre-registered first, is how close DIMACS arrivals sit to due times at C2 visits, by size.

**Another pattern (reported, not predicted).** On 84 of the 141 late routes (60%), the first late visit is a
customer that the BKS reaches exactly at its due time under DIMACS (zero slack). Distance-optimised routes often press
visits against the closing time, and in double precision any drift at such a visit makes it late.

**Hand checks** against [`vrptwd3/late_visits.csv`](../vrptwd3/late_visits.csv): C2_8_3 route 24 has 37 customers
and no waits; in `routes.csv` it first turns late at customer 607 (the last one), after 37 arcs with zero DIMACS
slack, late by 1.231992, with a depot slack of 0 (horizon-bound). `late_visits.csv` lists 607 late by 1.231992 after
37 arcs and the depot late after 38. R2_6_5 route 6 first turns late at customer 396, 2 tenths of slack after 4 arcs
since its last wait, late by 0.003534. `late_visits.csv` lists 396 late by 0.003534 after 21 arcs on the route, and
4 arcs since the last wait is consistent with that.

**Limits.** This describes published solutions under a convention they were not built for. A late arrival in double
precision is not an error in CVRPLib or in the solution, which is feasible under the DIMACS rules it was found with.
The patterns above describe these 356 solutions, not how the solvers that found them work. The C2 counts by waiting
were made after the results were seen and should be read as a lead, not a test.

Files: [results.json](results.json) (per-instance rows and the tally), [results.md](results.md) (per family and
size), [routes.csv](routes.csv) (one row per route of all 356 BKSs: waits, longest no-wait chain, zero-slack and
exposed visits, depot slack, first late visit), [anatomy.py](anatomy.py), [test_anatomy.py](test_anatomy.py).
