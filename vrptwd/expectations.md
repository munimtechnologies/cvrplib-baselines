# Expectations written before vrptw-double-v1 ran (2026-10-29 ~19:30Z)

MV2 of Munim, Inc. Made with AI agents working in MV2's name.

Background. vrptw-baseline-v1 (plain PyVRP 0.14.1, one CPU) ran under CVRPLib's DIMACS convention
(each arc truncated to 0.1, travel time = that distance). Its "lex" runs (fewest vehicles first) used
exactly as many vehicles as the long-standing hierarchical records on SINTEF's TOP pages on every
Solomon instance, and on 23 of them the DIMACS distance is *below* the SINTEF record. On R1_10_1 it used
94 routes, and CVRPLib's own BKS uses 95, while SINTEF's record is 100 vehicles. SINTEF computes distance
and time in double precision. Truncation shortens every arc (by 0.05 on average), so on a 100-customer
instance the DIMACS distance is about 5-6 units lower, and it also makes time windows easier to meet.
So these "better than the record" results are probably artefacts of the convention. This job checks that
directly: every CVRPLib BKS (62) and the 24 PyVRP solutions are re-checked in double precision
(math.hypot, time = distance, waiting allowed, late if arrival > due + 1e-6; every late arrival counted).

The 24 PyVRP solutions are the 23 Solomon lex results whose DIMACS distance is below the SINTEF record
(R101 R102 R104 R105 R108 R109 R111 R112 R201 R202 R203 R205 R206 R208 R209 RC101 RC102 RC106 RC107 RC108
RC202 RC204 RC205) plus R1_10_1-lex (94 routes). Copied unchanged from vrptw-baseline-v1/out/vrptw/improved/.

- D0 (hygiene): every one of the 86 solutions is DIMACS-feasible and reproduces its file's Cost line
  (tally.dimacs_hygiene_fail is empty).
- D1: none of the 23 Solomon PyVRP solutions is better than the SINTEF record in double precision
  (each is either infeasible in double precision or has the same vehicles and a distance >= the record
  minus 0.005). tally.pyvrp_double_better_than_sintef has no Solomon instance.
- D2: at least 12 of those 23 are still feasible in double precision
  (tally.pyvrp_solomon_looks_better_double_feasible >= 12).
- D3: on R1_10_1 both CVRPLib's 95-route BKS and PyVRP's 94-route solution are infeasible in double
  precision (that is what would reconcile 94-95 routes with SINTEF's 100).
- D4: at least 50 of the 56 Solomon CVRPLib BKSs are feasible in double precision
  (tally.solomon_bks_double_feasible >= 50).

Whatever happens, no result will be described as a new record unless it is feasible in the record's
own convention and checked again by a second, independent route.
What follows: the README of cvrplib-baselines says which convention every number uses; when CVRPLib
publishes the challenge rules (due 2026-10-31) the challenge's convention is the one MV2's runs use.
