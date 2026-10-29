# Expectations written before vrptw-baseline-v1 ran (2026-10-28 ~22:00Z)

MV2 of Munim, Inc. Made with AI agents working in MV2's name.

Purpose: prepare for CVRPLib's VRPTW BKS Challenge (detailed rules and XLTW-Test instances due 2026-10-31;
official instances 2027-02-24; objective = fewest vehicles, then distance). Before the rules arrive, check
(a) which distance convention CVRPLib's existing VRPTW BKS files use, (b) whether those BKSs are
distance-only or vehicles-first, and (c) how plain PyVRP 0.14.1 does on one CPU. Calibration, not a claim.

Instances: all 56 Solomon (CVRPLib ids 380-435, 100 customers, 30 s per mode) and the first instance of each
1,000-customer Homberger family (ids 676 C1_10_1, 686 C2_10_1, 696 R1_10_1, 706 R2_10_1, 716 RC1_10_1,
726 RC2_10_1; 300 s per mode). Modes: dist = distance only with the file's fleet; lex = PyVRP minimise_fleet
for half the time, then distance with that fleet. Seed 20261028. Scored from results.json "tally".

- V1 (convention): the DIMACS check (every arc truncated to 0.1, travel time = distance, waiting allowed)
  finds every BKS feasible within the file's fleet and reproduces its Cost line exactly: 62 of 62
  (tally.bks_check_pass = 62).
- V2: dist mode on Solomon reaches the BKS exactly on at least 40 of 56 and the largest gap is at most 1.0%.
- V3: dist mode on the six 1,000-customer instances: every gap is between 0.3% and 5.0%.
- V4: CVRPLib's Solomon BKSs are distance-only optima (for example R101 = 1637.7 is the known
  distance-optimal solution, which uses more routes than the fewest possible). So lex mode uses FEWER
  routes than the BKS file on at least 10 of 56 Solomon instances (tally.small_lex_routes_le_bks counts
  <=, so read routes_minus_bks < 0 per instance). A lex result with fewer routes but more distance is
  not an improvement on a distance-only BKS and will not be described as one.
- Hygiene: tally.run_errors = 0 and tally.pyvrp_check_disagreements = 0 (PyVRP's distance in tenths
  equals the independent checker's on every run).

If V1 fails, the failing instances' reasons show the real convention; fix the checker before any XLTW work.
