# vrptwlb: scoring (written 2026-10-31 ~06:40 UTC, after `vrptwlb-bounds-v1` finished)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0.

Run: `vrptwlb-bounds-v1`, 2026-10-31 03:45 to 03:51 UTC, one CPU, 1 GB. All 356 CVRPLib VRPTW instances (ids 380 to
735: 56 Solomon, 300 Gehring-Homberger). The 12 unit tests passed first. Predictions: [expectations.md](expectations.md),
written before the run. Prior art: [prior-art-addendum.md](prior-art-addendum.md). These are the classical bounds.
Afifi, Guibadj and Moukrim (CPAIOR 2014, doi:10.1007/978-3-319-07046-9_30) give stronger ones and report the minimum
fleet for 339 of 468 standard instances. So this is a reproduction and a calibration aid. It is not a new bound and
not the first proof of any minimum. Raw output: [results.json](results.json), [results.md](results.md),
[bounds.csv](bounds.csv), [cliques.json](cliques.json) (every clique, both conventions).

KC = ceil(total demand / capacity). KT = size of a clique of customers that no single route can serve together (in
either order), found by greedy search and re-checked pair by pair in exact 50-digit decimals. K = max(KC, KT).
"double" = travel time is the Euclidean distance (SINTEF's convention); "DIMACS" = each arc truncated to 0.1
(CVRPLib's BKS convention).

## Verdicts

| | Prediction | Our odds | Verdict | What happened |
|---|---|---|---|---|
| B0 | 356 read, a SINTEF record for each, every clique confirmed exactly, no unservable customer. | 80% | **held** | All clean; DIMACS computed for all 356 (every service time is at least 0.2). |
| B1 | No SINTEF record below its double K, no CVRPLib BKS below its DIMACS K, no `vrptwl/` result below K. | 97% | **held** | None. |
| B2 | Where `minimise_fleet` returned early (41 instances), KC equals the fleet it returned. | 95% | **held** | 41 of 41. The inference in `vrptwl/score.md` is now checked against the files. |
| B3 | At 1,000 customers, KT > KC on at most 5 of 60. | 60% | **held** | 2 (C1_10_1: 99 vs 90; R1_10_1: 100 vs 91). |
| B4 | On R101, KT > KC. | 75% | **held** | KT 18, KC 8, SINTEF 19. |
| B5 | SINTEF's vehicle count equals K on 40% to 70% of all 356. | 50% | **did not hold** | 270 of 356 (75.8%). |

Five of six held. B5 missed high: outside Solomon the capacity bound alone settles most records (247 of 300
Gehring-Homberger instances at K, against 23 of 56 Solomon).

## Results

| size | SINTEF record = K | | family | SINTEF record = K |
|---|---|---|---|---|
| 100 (Solomon) | 23 of 56 | | C1 | 39 of 59 |
| 200 | 54 of 60 | | C2 | 34 of 58 |
| 400 | 48 of 60 | | R1 | 52 of 62 |
| 600 | 51 of 60 | | R2 | 54 of 61 |
| 800 | 45 of 60 | | RC1 | 50 of 58 |
| 1,000 | 49 of 60 | | RC2 | 41 of 58 |

- **Where the record equals K (270 instances),** its vehicle count cannot be lowered in double precision, by these
  bounds alone. On the other 86 the record is 180 vehicles above K in total. These are open only against the
  classical bounds; Afifi et al.'s stronger bounds may close many of them.
- **The time-window bound is the binding one on 14 instances,** all with the tightest windows: R101, R102, R103,
  RC105 and the `_1` instance of C1 and R1 at every Gehring-Homberger size (C1_2_1 ... C1_10_1, R1_2_1 ... R1_10_1).
  Everywhere else K = KC.
- **At 1,000 customers 11 records sit above K** (38 vehicles in total): C1_10_5 (+10), C1_10_6 (+9), C1_10_7 (+7),
  C1_10_8, C2_10_1, C2_10_5 and RC2_10_1 (+2 each), C1_10_1, C2_10_2, C2_10_6 and C2_10_7 (+1 each). These are
  the only 1,000-customer instances where fleet reduction might still beat a record. They overlap with the families
  where `vrptwl/` missed SINTEF's count (C1, C2, RC2).

## Found on the way (reported, not predicted)

**The convention changes the minimum fleet.** The double-precision K is above the DIMACS K on 6 instances, all
tight-window R1: R102 (17 vs 16), R1_2_1 (20 vs 19), R1_4_1 (40 vs 36), R1_6_1 (59 vs 56), R1_8_1 (80 vs 75) and
R1_10_1 (100 vs 91). Truncation shortens every arc a little, which makes some pairs of customers compatible.

**Two DIMACS BKSs use fewer routes than any double-precision solution can.** CVRPLib's BKS for R1_6_1 has 58 routes,
below its double-precision K of 59; R1_10_1's has 95, below 100. So no solution that is on time in double precision
exists with those route counts, and these two cannot be repaired without extra routes. This explains two of the three
BKSs that `vrptwd4/` could not repair in its budget. The third, R1_8_1 (80 routes, K = 80), is not ruled out by this
bound. In both cases SINTEF's double-precision record equals K (59 and 100 vehicles), so for R1_10_1 the fewest
vehicles is 100 in double precision, while the DIMACS BKS shows that 95 suffice with truncated times. Neither
convention is wrong; this is why vehicle counts from one cannot be compared with records kept under the other.

**What it means for CVRPLib's XLTW challenge,** which ranks by vehicles first: on instances with wide windows the
capacity bound is likely to settle the fleet, and the contest is about distance; on the tightest windows the
challenge's distance and time convention can move the minimum fleet by several vehicles.

## Hand checks

- R101: total demand 1,458, capacity 200, KC = 8. C101: 1,810 / 200, KC = 10. Both as in the table.
- Three pairs of R101's clique (customers 3, 6, 10, 20), from the instance file: customer 3 (55, 45), window
  [116, 126]; 6 (25, 30), [99, 109]; 10 (30, 60), [124, 134]; 20 (45, 65), [126, 136]; service 10 each.
  3 then 6: 116 + 10 + 33.54 = 159.5 > 109; 6 then 3: 99 + 10 + 33.54 = 142.5 > 126. 10 then 20: 124 + 10 + 15.81 =
  149.8 > 136; 20 then 10: 151.8 > 134. 3 then 20: 148.4 > 136; 20 then 3: 158.4 > 126. All three pairs are
  incompatible, as the code says.
- R1_10_4: KC 91 equals the fleet `minimise_fleet` returned early and SINTEF's 91.

## Limits

K is a lower bound, not the optimum. The greedy clique search may miss larger cliques, so KT may be too low (never
too high: every clique is checked exactly). SINTEF's records were read on 2026-10-31 and are taken as published. The
incompatibility test uses a tolerance of 1e-6, which can only weaken the bound.
