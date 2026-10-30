# Expectations written before vrptwd5-anatomy-v1 ran (2026-10-30 ~08:50 UTC)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.

**Background.** CVRPLib's VRPTW best known solutions (BKSs) use the DIMACS convention: every arc is truncated to
one decimal. [`vrptwd/`](../vrptwd/score.md) and [`vrptwd3/`](../vrptwd3/score.md) (checked a second way in
[`vrptwd2/`](../vrptwd2/score.md)) found 90 of the 356 Solomon and Homberger BKSs that arrive late somewhere in
double precision. `vrptwd3/` left one question open: why lateness concentrates in C2 at 800 and 1,000 customers
(12 of those 20 BKSs are late, against 3 of the 30 C2 BKSs with 200 to 600 customers). A search on 2026-10-30
found no earlier route-level analysis of these BKSs (waiting, slack, drift); SINTEF's pages and the DIMACS rules
document the two conventions, not where solutions found under one fail under the other.

**What we already know, and what we do not.** The counts of late BKSs per family and size above are published and
were known when these predictions were written. Route counts of late routes, waiting, slack and depot return times
had not been computed or looked at.

**Method.** `anatomy.py` reads all 356 instances and BKSs (CVRPLib ids 380 to 735; cached copies from the earlier
runs) and runs the unchanged `vrptwd/double_check.py` on each. It then follows every route under both conventions
at once. In double precision a route drifts later than under DIMACS by up to 0.1 per arc, until the vehicle waits
for a window to open, which resets the drift to zero. So a visit can only be late in double precision if its DIMACS
slack (due time minus DIMACS arrival, in tenths) is smaller than the number of arcs driven since the last such
wait: the visit is **exposed**. A route is **horizon-bound** if it returns to the depot within 1.0 time unit of the
depot's due time under DIMACS. The **wait share** of a route is the share of its customers where the vehicle
waits under DIMACS.

**Predictions** (scored by `score_a()` in `anatomy.py`, written before the run):

| | Prediction | Basis | Our odds |
|---|---|---|---|
| A0 | 356 BKSs read, every DIMACS cost equals the file, exactly 90 late in double precision, the late counts per instance and per route equal `double_check.py`'s, and every late visit is exposed. | Hygiene. The last part follows from the arithmetic above, so a failure means a bug. | 95% |
| A1 | In the Homberger C2 family, the share of routes that are late at 800 and 1,000 customers is at most twice the share at 200 to 600. | If each route had about the same small chance of being late, larger instances would be late more often just because they have more routes (about 6 routes at 200 customers, about 30 at 1,000). | 45% |
| A2 | At least 75% of the late C2 routes are horizon-bound. | C2 has wide windows and 90-unit service times; a distance-optimal route fills the working day and never waits, so drift builds up until the depot's closing time. The one late C2 route we have looked at (C2_8_3, route 24) is late at its last customer and at the depot. | 70% |
| A3 | The horizon-bound share among late R1 and RC1 routes is lower than among late C2 routes. | R1 and RC1 have narrow windows, so a route should turn late at a customer whose window closes, not at the depot. | 65% |
| A4 | Among Homberger C2 routes, late routes have a lower mean wait share than the other routes. | Waiting resets the drift. | 60% |
| A5 | Across all 356 BKSs, the number of exposed visits separates late from on-time BKSs with an AUC of at least 0.80. | Exposure is necessary for lateness. It is a raw count, so it also grows with instance size, which helps and blurs at once. | 75% |

Only reported, not predicted: per family and size, the route late rate, mean wait share, horizon-bound routes and
exposed visits per route; how many first late visits are the depot return, and how many sit exactly at a due time
under DIMACS (zero slack).

**Limits stated in advance.** This describes published solutions under a convention they were not built for. A
late arrival in double precision is not an error in CVRPLib or in the solution, which is feasible under the DIMACS
rules it was found with. Whatever A1 to A5 show is a description of these 356 solutions, not a claim about how the
solvers that found them work. Results will be reported in full, including predictions that fail.
