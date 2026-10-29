# Expectations written before vrptwd2-exact-v1 ran (2026-10-29 ~22:40Z)

MV2 of Munim, Inc. Made with AI agents working in MV2's name.

Background. `vrptwd/` (job vrptw-double-v1, scored in [../vrptwd/score.md](../vrptwd/score.md)) found that,
in double precision, 8 of the 56 Solomon VRPTW best known solutions on CVRPLib and 2 of the six
1,000-customer ones (R1_10_1, RC2_10_1) arrive late at one or more customers; they are feasible under the
DIMACS convention CVRPLib uses (arcs truncated to 0.1). Before this is described anywhere outside this
repository, `exact_check.py` re-tests all 86 solutions by a second, separately written route:

- files are parsed by the `vrplib` package (2.2.0), not by our own parser;
- every distance, arrival and slack is exact 50-digit Decimal arithmetic, with no floating point;
- the same rules: travel time = Euclidean distance, waiting allowed, late if arrival > due + 1e-6,
  service time added after the visit starts, the depot's due time applies to the return;
- the 24 PyVRP solutions are downloaded from this repository (`vrptwd/sols/`), the 62 BKSs from CVRPLib;
- each row is compared with the first check's figures, copied into `reference.csv` from `vrptwd/results.md`.

- S1: the exact check agrees with vrptw-double-v1 on feasible / infeasible for all 86 solutions, and every
  solution has the number of routes recorded in reference.csv (`S1_feasibility_disagree` and
  `routes_mismatch` both empty).
- S2: for all 86, the number of late arrivals is the same and the largest lateness agrees within 0.0001
  (`S2_late_disagree` empty).
- S3: for all 86, the total distance agrees with the first check's 2-decimal figure within 0.006
  (`S3_distance_disagree` empty).
- S4: every late arrival is at most 0.1 x the number of arcs driven on that route up to that arrival
  (`S4_outside_truncation_bound` empty). This is a consistency check rather than a prediction: a
  DIMACS-feasible route can only be late in double precision by what truncation removed, under 0.1 per arc.
  A failure would mean the time windows or service times were read differently from the first check.

Not predicted, only reported: how many of the double-precision-feasible solutions come within 0.1 and
within 0.01 time units of a due time (`feasible_min_slack_below_0.1`, `..._0.01`).

If S1 to S3 hold, the per-instance list (which published DIMACS BKSs are late in double precision, where,
and by how much) is published as checked twice. If any fails, the disagreement is investigated and written
up before anything else is said about these solutions.
