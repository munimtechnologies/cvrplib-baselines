# Scoring of V1-V4 (vrptw-baseline-v1)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Scored 2026-10-29 from
`results.json` in this folder, against `expectations.md` (written before the job ran).

The job ran on 2026-10-29 from 12:52 to 13:56 UTC: two worker processes, one CPU each, PyVRP 0.14.1
(pinned with `pip install pyvrp==0.14.1`; the results files say "unknown" because 0.14.1 has no
`__version__`). Peak memory was 0.25 GB. Convention: DIMACS (each arc truncated to 0.1, travel time =
distance). Solomon runs had 30 s per mode, the six 1,000-customer runs 300 s per mode.

| | expectation | outcome | verdict |
|---|---|---|---|
| V1 | the DIMACS check reproduces every BKS Cost line | 62 of 62 | **holds** |
| V2 | dist mode reaches the BKS on at least 40 of 56 Solomon, largest gap at most 1.0% | 40 of 56 at the BKS, but largest gap **1.642%** (RC108); R210 (1.344%) and RC102 (1.105%) also above 1% | **fails** (second half) |
| V3 | dist mode on the six 1,000-customer instances: every gap between 0.3% and 5.0% | C1_10_1 **0.005%**, C2_10_1 0.818%, R1_10_1 1.919%, R2_10_1 0.469%, RC1_10_1 1.660%, RC2_10_1 **0.208%** | **fails** (4 of 6 in the band) |
| V4 | CVRPLib's Solomon BKSs minimise distance only, so lex mode uses fewer routes than the BKS on at least 10 of 56 | fewer routes on 36 of 56 (11 of 12 R1, all but R103; all 11 R2; 6 of 8 RC1, all 8 RC2; none of C) | **holds** |

Hygiene: no run errors, and PyVRP's distance equals the independent checker's on all 124 runs.

Why V2 and V3 failed: the band was set too tight for V2 and too pessimistic at the low end for V3.
30 s on one CPU misses the distance-only optimum by more than 1% on three tight-window Solomon instances,
while on the clustered C1_10_1 and the wide-window RC2_10_1 five minutes came within 0.21%.

What V4 means. CVRPLib's VRPTW best known solutions for Solomon are the distance-only optima (for
example R101: 20 routes, 1637.7). The `results.json` field `beats_bks_lex` compares (routes, distance)
against those files, so it flags 41 runs (all fewer routes, more distance). **None of those 41 is an
improvement on anything**: a distance-only optimum cannot be beaten on distance, and fewer routes is a
different objective. The `improved/` files the job wrote are kept out of this repository for that reason.

A second comparison is more interesting. Lex mode used exactly as many vehicles as the long-standing
hierarchical records (fewest vehicles, then distance) on SINTEF's TOP pages on 55 of 56 Solomon
instances (R103: 14 against 13), and on 23 of them its DIMACS distance is *below* the record. SINTEF
computes in double precision, so this is very likely the convention, not the solver: truncation shortens
every arc and loosens every time window. On R1_10_1, lex used 94 routes and CVRPLib's BKS uses 95,
while SINTEF's record is 100 vehicles. A follow-up job re-checks all 62 BKSs and those 24 solutions in
double precision, with its expectations written first: [../vrptwd/expectations.md](../vrptwd/expectations.md).

For the VRPTW BKS Challenge (objective: vehicles first, then distance), the lesson is that the
challenge's distance and time convention decides vehicle counts, not just the last decimals. MV2's runs
will use the convention in the challenge's rules (due 2026-10-31) and nothing else.
