# Expectations written before vrptwd3-homberger-v1 ran (2026-10-30 ~01:00 UTC)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.

**Background.** CVRPLib's VRPTW best known solutions (BKSs) use the DIMACS convention: every arc is truncated
to one decimal. [`vrptwd/`](../vrptwd/score.md) re-checked 62 of them in double precision (time = exact
Euclidean distance) and found 10 that arrive late somewhere: 8 of the 56 Solomon BKSs and 2 of the six
1,000-customer Homberger BKSs it looked at (R1_10_1 with 7 late arrivals, RC2_10_1 with 2). That says
nothing yet about the other 294 Homberger instances (200, 400, 600, 800 and 1,000 customers, 10 per family),
which are the closest public relatives of the 1,000 to 10,000-customer instances in CVRPLib's VRPTW BKS
Challenge (February to March 2027). Both conventions are well known (DIMACS 2021 rules, SINTEF's records);
what is new here is only the per-instance list.

**Method.** `homberger_check.py` runs the published, unchanged checks of `vrptwd/double_check.py` on CVRPLib
ids 436 to 735 (instance and BKS files from CVRPLib's download pages, 2 s apart) and additionally lists every
late arrival with the number of arcs driven on its route before it. Rules as before: waiting allowed,
service starts at max(arrival, ready time), late if arrival > due + 1e-6, the depot's due time applies to
the return. A second, independent check of the method (exact Decimal arithmetic, `vrptwd2/`) is queued
separately; these results will say whether it has confirmed the first.

**Predictions** (scored by `score_h()` in `homberger_check.py`, written before the run):

| | Prediction | Basis |
|---|---|---|
| H0 | All 300 BKSs are feasible under DIMACS and their DIMACS cost equals the file's `Cost` line. | 62 of 62 did in vrptwd (D0). A failure means a file or parser problem, not a finding. |
| H1 | None of the 120 C1/C2 BKSs is late in double precision. | 0 of 17 Solomon C and 0 of 2 Homberger C BKSs were. |
| H2 | Between 20 and 140 of the 180 R1/R2/RC1/RC2 BKSs are late in double precision. | 8 of 39 Solomon R/RC (21%) and 2 of 4 Homberger 1,000 R/RC were. The band is deliberately wide: only four R/RC Homberger instances have been checked. |
| H3 | The late share among R/RC BKSs at 1,000 customers is at least the share at 200 customers. | Longer routes have more arcs, so truncation leaves more room to arrive "on time" only under DIMACS. |
| H4 | Every late arrival is at most 0.1 x the arcs driven on its route up to that point. | A DIMACS-feasible route can only lose under 0.1 per arc to truncation. A failure means the files were read differently from DIMACS. |

Only reported, not predicted: late arrivals per family and size, the largest lateness, and how many
double-feasible BKSs come within 0.1 and 0.01 time units of a due time.

**Limits stated in advance.** This checks published solutions under a convention they were not built for;
a late arrival in double precision is not an error in CVRPLib or in the solution, which is feasible under
the rules it was found with. Results will be reported in full, including predictions that fail.
