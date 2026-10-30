# Expectations written before vrptwl-fleet-v1 ran (2026-10-30 ~16:10 UTC)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.

**Why.** CVRPLib's VRPTW BKS Challenge (1,000 to 10,000 customers; official instances on 2027-02-24) ranks solutions
by **vehicles first**, then distance. CVRPLib's own VRPTW BKSs minimise distance only, so they say nothing about the
vehicle objective. The long-standing hierarchical records for the same instances are on SINTEF's TOP pages and are
kept in double precision (no truncation). Several were improved in September and October 2026. Our earlier
`vrptw/` run used PyVRP's `minimise_fleet` for 150 s on six 1,000-customer instances under DIMACS truncation. This
run asks how close plain PyVRP gets to SINTEF's vehicle counts on all 60 Gehring-Homberger 1,000-customer instances,
in the records' own convention. It is a calibration of an off-the-shelf solver, not an attempt at a record.

**Method.** `fleet_double.py` reads each instance and CVRPLib BKS (ids 676 to 735, cached copies) and writes a
VRPLIB copy with the file's fleet. PyVRP 0.14.1 reads it with every number multiplied by 1,000 and rounded **up**
(as in `vrptwd4/`), so a schedule that is on time in the copy is on time in double precision. Per instance: one CPU,
600 s, seed 20261030; `pyvrp.minimise_fleet` for 300 s, then `pyvrp.solve` with that fleet for 300 s. Three
instances run at a time. Every result is re-checked by an independent double-precision checker in the same file
(coverage, capacity, every arrival, tolerance 1e-6) and compared with SINTEF's record (vehicles, distance), read on
2026-10-30. The job also re-reads the SINTEF page and reports any difference from the table in the code.

**Predictions** (scored by `score_l()` in `fleet_double.py`, written before the run):

| | Prediction | Basis | Our odds |
|---|---|---|---|
| L0 | 60 instances read, every name in the SINTEF table, no run errors, every result visits each customer once within capacity, and no result PyVRP calls feasible fails the double-precision check. | Hygiene; the safe rounding was tested in `vrptwd4/`. | 95% |
| L1 | All 60 results are on time in double precision. | A feasible solution at some fleet size is easy at this budget. | 90% |
| L2 | No result beats a SINTEF record (fewer vehicles, or the same vehicles and a shorter distance). | Records come from many hours of specialised search. | 97% |
| L3 | At least 30 of 60 results use exactly SINTEF's vehicle count. | Under DIMACS at 150 s, `vrptw/` matched the record's count on C1_10_1, C2_10_1, R2_10_1 and RC2_10_1, missed RC1_10_1 by one. | 55% |
| L4 | In R2 and RC2 (long horizon), at least 15 of 20 match. | 19 and 18 vehicles look like capacity bounds; `vrptw/` matched R2_10_1 and RC2_10_1. | 65% |
| L5 | In R1 and RC1 (short horizon), at most 6 of 20 match. | 91 and 90 are hard-won; `vrptw/` missed RC1_10_1 by one. | 70% |
| L6 | Where the count matches, the median distance is at most 3% above SINTEF's. | `vrptw/` lex results were within about 1.3% on matched wide-horizon instances. | 65% |

Only reported, not predicted: vehicles over the record per family, distances, iterations, and which results use
fewer routes than CVRPLib's distance-only BKS (expected for most, and **not** an improvement on that BKS).

**Limits stated in advance.** One seed, one CPU, 600 s per instance; a miss does not show that PyVRP cannot reach the
record with more time or other settings. SINTEF's table is copied as read on 2026-10-30. If any result appears to
beat a SINTEF record, it is not claimed: it would first be re-checked in exact arithmetic by a separately written
checker, as `vrptwd2/` and `vrptwd4x/` do. Results will be reported in full, including predictions that fail.
