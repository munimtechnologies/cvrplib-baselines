# Scoring of vrptwd4-repair (repairing the 90 VRPTW BKSs that are late in double precision)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.

The predictions were written before the run: [expectations.md](expectations.md) (2026-10-30, about 07:00 UTC).
The job `vrptwd4-repair-v1` ran on 2026-10-30 from 08:04 to 09:43 UTC (3 workers, peak memory 0.31 GB): the unit
tests passed, then `repair.py --ids 380-735` read all 356 Solomon and Homberger instances and best known solutions
(BKSs) from CVRPLib, re-ran the unchanged `vrptwd/double_check.py`, and started PyVRP 0.14.1 from each of the 90
late BKSs with the fleet capped at the BKS's route count, on a copy of the instance with every number multiplied by
1,000 and rounded up (seed 20261030; 60 s per instance up to 200 customers, then 0.3 s per customer). The verdicts
below are the ones `score_r()` computed in the job (`results.json`, `tally.predictions`); nothing was re-scored by
hand.

| | Prediction (as written) | Result | Verdict |
|---|---|---|---|
| R0 | 356 BKSs read, exactly 90 late, every DIMACS cost equals the file, no run errors, no PyVRP-feasible result fails `double_check.py`. | 356 read, 90 late (8 Solomon, 82 Homberger), no hygiene failures, no errors, no disagreements | **held** |
| R1 | At least 70 of the 90 are repaired. | 87 of 90 | **held** |
| R2 | At least 45 of the 50 late wide-horizon BKSs (C2, R2, RC2) are repaired. | 50 of 50 | **held** |
| R3 | Median distance change of repaired solutions against the BKS's own double-precision distance is between 0% and +0.5%. | +0.43% (range +0.0015% to +12.85%) | **held**, near the top of the band |
| R4 | R1_10_1 (95 routes) is not repaired. | not repaired | **held** |
| R5 | Repair rate among wide-horizon BKSs is at least the rate among short-horizon ones (C1, R1, RC1). | 100% (50 of 50) against 92.5% (37 of 40) | **held** |
| R6 | No repaired solution beats a SINTEF record (fewest vehicles, then distance) where `double_check.py` has one. | all 9 comparable repairs (8 Solomon and RC2_10_1) use more vehicles than SINTEF's record | **held** |

**Overall.** 87 of the 90 BKSs that arrive late in double precision can be made feasible in double precision with no
more routes than the BKS, usually at a small cost in distance. The three that were not repaired are R1_6_1 (58
routes), R1_8_1 (80) and R1_10_1 (95): the first R1 instance at each of the three largest sizes, which in the
Solomon/Homberger design has the narrowest windows of the family. For each of them PyVRP found no solution on time in
the rounded-up copy within its budget. That is not a proof that none exists at that route count (see Limits).

| | C1 | C2 | R1 | R2 | RC1 | RC2 | wide (C2, R2, RC2) | short (C1, R1, RC1) |
|---|---|---|---|---|---|---|---|---|
| late BKSs | 5 | 15 | 20 | 15 | 15 | 20 | 50 | 40 |
| repaired | 5 | 15 | 17 | 15 | 15 | 20 | 50 | 37 |
| median distance change | | | | | | | +0.19% | +1.38% |

**R3 held because the wide-horizon repairs dominate.** Their median is +0.19%, and none exceeds +2%. In the
short-horizon families the median repair costs +1.38%, and eight exceed +3% (largest: RC1_10_5 at +12.85%, RC1_8_9 at +8.97%, RC1_4_9 at
+8.63%). With a few minutes per instance these figures are upper bounds on what a repair costs, not estimates of it.
RC101 was repaired at exactly the BKS's DIMACS cost (1,619.8), so a solution as short as the BKS under DIMACS that is
also on time in double precision exists there.

**Fewer routes than the BKS (reported, not predicted).** Three repairs use one route fewer than their BKS: R2_2_1
(12 against 13), R2_2_2 (10 against 11) and R2_6_5 (21 against 22). CVRPLib's VRPTW BKSs minimise distance only, so
the fleet cap was an upper limit, and these solutions are 0.47% to 0.96% longer than their BKSs. They are not
improvements under either convention, and hierarchical records (fewest vehicles first) for these instances use far
fewer vehicles. They are being re-checked independently (`vrptwd4x/`, below) before anything else is said about them.

**Hand checks.** `sols/R2_2_1.sol` has 12 routes and `Cost 3509.78`, matching the table; `sols/RC101.sol` has 15
routes visiting 100 customers, `Cost 1623.58`; `sols/R2_6_5.sol` has 21 routes, `Cost 13882.02`. All 87 repaired
solutions are also feasible under DIMACS (`repaired_also_dimacs_ok`: 87), as they must be, since truncation only
shortens arcs.

**How sure this is.** Every repaired solution was checked by `double_check.py`, which `vrptwd2/` confirmed on 86
solutions with a separately written exact method. The 87 solutions themselves have been checked once. A second,
independent exact check of all 87 under both conventions, with its own predictions (X0 to X4), was written before it
ran: [../vrptwd4x/expectations.md](../vrptwd4x/expectations.md).

**Limits.** One seed, one solver, minutes per instance. A BKS that was not repaired is *not* shown to be infeasible
in double precision at its route count. A repaired solution is a double-precision solution at the BKS's route count,
not a new record under either convention, and it says nothing against the BKS, which is feasible under the DIMACS
rules it was found with.

Files: [results.json](results.json) (one row per late BKS, with the run and the tally), [results.md](results.md),
[sols/](sols/) (87 repaired solutions in CVRPLib format; `Cost` = double-precision distance, two decimals),
[repair.py](repair.py), [test_repair.py](test_repair.py).
