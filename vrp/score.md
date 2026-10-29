# Scoring of E1-E3 (cvrplib-xl-probe-v2)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Scored 2026-10-29 from
`results.json` in this folder, against `expectations.md` (written before the job ran).

The job ran on 2026-10-29 from 04:02 to 05:21 UTC: two worker processes, one CPU each, PyVRP 0.14.1
(pinned with `pip install pyvrp==0.14.1`; the script's version lookup used `pyvrp.__version__`, which
0.14.1 does not have, so the results files say "unknown"). Peak memory was 0.3 GB.

| | expectation | outcome | verdict |
|---|---|---|---|
| E1 | the independent nint-Euclidean check reproduces each BKS Cost line | 380,090 / 112,431 / 95,638: all three equal | **holds** (3 of 3) |
| E2 | 30 min of PyVRP warm-started from the BKS finds no improvement | final cost = BKS on all three (484k, 661k and 1.04M iterations) | **holds** (3 of 3) |
| E3 | 15 min cold start: gap to the BKS between 0.5% and 3% on each | 1.989%, **0.183%**, 0.649% | **fails** (2 of 3) |

Why E3 failed: XL-n1094-k157 has capacity 7, so its routes are short and the number of vehicles (157) is
fixed by the demand; cold PyVRP reached that fleet size and came within 0.18% of the BKS in 15 minutes.
The expectation set one band for three very different instances; it was too pessimistic for a short-route
instance. The other two (238 and 113 routes in the BKS) landed inside the band, with 7 and 1 extra routes.

Hygiene: every run ended feasible, and PyVRP's own distance equals the independent checker's on all 6 runs.

What this means: one CPU of plain PyVRP for 30 minutes does not improve an XL best-known solution
(as expected: these BKSs went through CVRPLib's 30-day CVRP BKS Challenge and later submissions). Any attempt at a VRPTW BKS in
February-March 2027 needs either much longer runs or a better method, not just the default solver.
