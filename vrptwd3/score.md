# Scoring of vrptwd3-homberger (all 300 Homberger BKSs in double precision)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.

The predictions were written before the run: [expectations.md](expectations.md) (2026-10-30, about 01:00 UTC).
The job `vrptwd3-homberger-v1` ran on 2026-10-30 from 01:45 to 02:12 UTC on one CPU: 6 unit tests passed, then
`homberger_check.py --ids 436-735` downloaded each instance and best known solution (BKS) from CVRPLib, 2 s apart,
and checked them with the unchanged `vrptwd/double_check.py`. The verdicts below are the ones `score_h()` computed in
the job (`results.json`, `tally.predictions`); nothing was re-scored by hand.

**A counting error in the expectations.** The Homberger set has six families (C1, C2, R1, R2, RC1, RC2), each with
10 instances at 200, 400, 600, 800 and 1,000 customers. That is 100 C1/C2 BKSs and 200 R1/R2/RC1/RC2 BKSs, not the
120 and 180 the expectations state. The code counted the groups from the instance names, so the verdicts are
unaffected: H1 predicts none late (20 are), and H2's band of 20 to 140 contains the 62 found whichever denominator is
used. The error is in the text only, and it is left there as written.

| | Prediction (as written) | Result | Verdict |
|---|---|---|---|
| H0 | All 300 BKSs are feasible under DIMACS and their DIMACS cost equals the file's `Cost` line. | 300 of 300 | **held** |
| H1 | None of the 120 C1/C2 BKSs is late in double precision. | 20 of the 100 C1/C2 BKSs are late | **did not hold** |
| H2 | Between 20 and 140 of the 180 R1/R2/RC1/RC2 BKSs are late in double precision. | 62 of 200 (31.0%) | **held** |
| H3 | The late share among R/RC BKSs at 1,000 customers is at least the share at 200. | 30.0% (12 of 40) at 1,000 against 27.5% (11 of 40) at 200 | **held**, by one instance |
| H4 | Every late arrival is at most 0.1 x the arcs driven on its route up to that point. | 169 late arrivals, all within the bound | **held** |

**Overall.** 82 of the 300 Homberger BKSs (27.3%) arrive late at least once when travel times are not truncated;
218 are feasible in double precision. The largest lateness per late instance ranges from 0.0028 (C2_10_4) to 1.27
time units (C2_8_3, whose route 24 returns to the depot 1.27 late after 38 arcs). 36 of the feasible ones come within 0.1 time units of a
due time somewhere, and 12 within 0.01. The six 1,000-customer instances that `vrptwd/` had already checked give
the same verdicts, counts and lateness here.

| customers | C1 | C2 | R1 | R2 | RC1 | RC2 | late of 60 |
|---|---|---|---|---|---|---|---|
| 200 | 1 | 0 | 5 | 4 | 0 | 2 | 12 |
| 400 | 0 | 2 | 3 | 3 | 4 | 2 | 14 |
| 600 | 1 | 1 | 3 | 3 | 1 | 3 | 12 |
| 800 | 1 | 5 | 3 | 2 | 5 | 7 | 23 |
| 1,000 | 2 | 7 | 1 | 2 | 3 | 6 | 21 |
| all sizes (of 50) | 5 | 15 | 15 | 14 | 13 | 20 | 82 |

**Why H1 failed.** H1 rested on 19 C instances (17 Solomon, 2 Homberger), none of them late. The larger C2
instances are where lateness concentrates: 12 of the 20 C2 BKSs with 800 or 1,000 customers are late, against 2 of
the 20 C2 BKSs with 200 or 400, and the five largest per-instance lateness values (0.78 to 1.27) are C2 instances with
600 to 1,000 customers. C1 has only 5 late BKSs in all. Route length alone does not explain it: C2 BKSs carry about
29 customers per route at 200 and about 33 at 800 and 1,000. We have not found the reason and do not guess one here.

**H3 is weak.** It held by one instance, and the R/RC late share does not rise steadily with size: 27.5%, 30.0%,
25.0%, 42.5% and 30.0% at 200 to 1,000 customers. Taking all six families, the late share is 20 to 23% at 200 to
600 customers and 35 to 38% at 800 and 1,000.

**Hand checks** against [late_visits.csv](late_visits.csv): C2_8_3 has two late arrivals on route 24 (customer 607
by 1.231992 after 37 arcs, then the depot by 1.265880 after 38), matching `2 (1)` and 1.2659 in results.md; R2_6_5
has one, customer 396 by 0.003534 after 21 arcs, matching `1 (1)` and 0.0035; C1_10_7 has 20 late arrivals on 5
routes, the largest 0.391233, matching `20 (5)` and 0.3912.

**How sure this is.** `vrptwd2/` re-checked the 86 solutions of `vrptwd/` with a separately written method (exact
decimal arithmetic, vrplib's parser) and agreed on every one ([vrptwd2/score.md](../vrptwd2/score.md)). This run
uses the same `double_check.py` that was confirmed there, on 294 instances it had not seen. The 300 rows themselves
have been checked once.

**Limits.** This checks published solutions under a convention they were not built for. A late arrival in double
precision is not an error in CVRPLib or in the solution, which is feasible under the DIMACS rules it was found with.
The point is practical: a solver or checker that works in double precision cannot start from, or compare with, about
a quarter of these BKSs as they stand. Both conventions are well documented (DIMACS 2021 rules; SINTEF's records);
what is new here is the per-instance list.

Files: [results.json](results.json) (one row per instance, with the tally), [results.md](results.md),
[late_visits.csv](late_visits.csv) (one row per late arrival, with the arcs driven before it),
[homberger_check.py](homberger_check.py), [test_homberger_check.py](test_homberger_check.py).
