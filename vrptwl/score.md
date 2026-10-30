# vrptwl: scoring (written 2026-10-30 ~20:00 UTC, after `vrptwl-fleet-v1` finished)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0.

Run: `vrptwl-fleet-v1`, 2026-10-30 16:50 to 19:15 UTC. PyVRP 0.14.1, one CPU per instance, three at a time,
600 s per instance (`minimise_fleet` 300 s, then `solve` with that fleet 300 s), seed 20261030, every number x1,000
rounded up. All 60 Gehring-Homberger 1,000-customer instances (CVRPLib ids 676 to 735). Peak memory 0.41 GB.
Predictions: [expectations.md](expectations.md). Raw output: [results.json](results.json), [results.md](results.md),
solutions in [sols/](sols/) (CVRPLib format, `Cost` = double-precision distance).

The job re-read SINTEF's 1,000-customer page during the run: 60 rows, no difference from the table in
`fleet_double.py`, none missing.

## Verdicts

| | Prediction | Our odds | Verdict | What happened |
|---|---|---|---|---|
| L0 | 60 read, all names known, no run errors, structure OK, no PyVRP/checker disagreement. | 95% | **held** | All clean. |
| L1 | All 60 on time in double precision. | 90% | **held** | 60 of 60. |
| L2 | None beats a SINTEF record. | 97% | **held** | None. C2_10_1 equals its record (30 vehicles, 16,879.24); the other 59 are worse. |
| L3 | At least 30 of 60 match SINTEF's vehicle count. | 55% | **held** | 47 of 60. |
| L4 | At least 15 of 20 match in R2 and RC2. | 65% | **held** | 17 (R2 10 of 10, RC2 7 of 10). |
| L5 | At most 6 of 20 match in R1 and RC1. | 70% | **did not hold** | 19 of 20 (R1 10 of 10, RC1 9 of 10). |
| L6 | Median distance where the count matches at most 3% above SINTEF. | 65% | **did not hold** | 4.18% (47 instances). |

Five of seven held. Both misses come from the same wrong picture of the short-horizon families (R1, RC1), which we
expected to be hard on vehicles and easy on distance. It was the other way round.

## Results by family

| family | match SINTEF's vehicles | vehicles over (misses) | median distance over SINTEF where matched | `minimise_fleet` finished before 300 s |
|---|---|---|---|---|
| C1 | 5 of 10 | +1, +1, +2, +4, +4 | 0.52% | 3 of 10 |
| C2 | 6 of 10 | +1, +1, +1, +1 | 2.01% | 3 of 10 |
| R1 | 10 of 10 | none | 21.95% | 9 of 10 |
| R2 | 10 of 10 | none | 1.68% | 10 of 10 |
| RC1 | 9 of 10 | +1 | 12.90% | 9 of 10 |
| RC2 | 7 of 10 | +1, +1, +2 | 3.80% | 7 of 10 |
| all | **47 of 60** | 21 vehicles in total (3,437 against 3,416) | 4.18% | 41 of 60 |

## What the misses say

**Where PyVRP stopped early, it hit a bound.** In PyVRP 0.14.1, `minimise_fleet` keeps removing one vehicle while
its time lasts. It returns before its time limit only when the fleet reaches its built-in lower bound,
ceil(total demand / vehicle capacity) (see `pyvrp/minimise_fleet.py` at v0.14.1). In 41 of 60 instances it returned
early (after 3.6 s to 235 s), and all 41 results use exactly SINTEF's vehicle count. So, by this reading of the
code, in those 41 instances the record's vehicle count equals the capacity bound and cannot be lowered. The vehicle
part of the objective is settled there, and only distance is left to compete on. This is an inference from the
code, not yet checked against the instance files. The pre-registered `vrptwlb/` job computes the bounds directly.

**The other 19 ran out of time.** These are 7 C1, 7 C2, R1_10_1, RC1_10_1 and 3 RC2 instances. Six of them still
matched SINTEF's count: C1_10_1 and C1_10_5 (100), C2_10_1, C2_10_2 and C2_10_5 (30, 29, 30), and R1_10_1 (100).
In C1_10_1, `minimise_fleet` stopped at 101 and `solve` then used 100. All 13 misses are among these 19. More time
or a dedicated route-elimination step might close them. This run cannot tell which.

**Short horizon: vehicles easy, distance hard.** In R1 and RC1, 18 of the 19 matches came from the capacity bound
(17 of them within 42 s, R1_10_2 after 203 s). But at that tight fleet, 300 s of `solve` left the distance far
above SINTEF's (median +21.95% in R1, +12.90% in RC1; largest +36.84%, R1_10_5). For comparison, `vrptw/`
(distance only, the file's fleet, 300 s, DIMACS) came within 1.92% and 1.66% of CVRPLib's distance-only BKSs on
R1_10_1 and RC1_10_1, using more vehicles. The ranking puts vehicles first, so
at 1,000 customers a method needs most of its time for distance at the minimum fleet in R1/RC1, and for fleet
reduction in C1/C2/RC2.

**Hand checks.** The route lines in the 60 solution files add up to 3,437, as in the tally. C2_10_1 has 30 routes
and `Cost 16879.24`, equal to SINTEF's record. C2_10_5 (30 vehicles, 16,585.02) has the same distance as the
`vrptwd4/` repair of its BKS, found separately from a different start.

**Fewer routes than CVRPLib's BKS (27 instances).** This is expected and is **not** an improvement: CVRPLib's VRPTW
BKSs minimise distance only.

## Limits

One seed, one CPU, 600 s per instance. A miss does not show that PyVRP cannot reach the record with more time or
other settings. SINTEF's records were copied on 2026-10-30. The bound reading above depends on PyVRP's source and is
being checked directly.
