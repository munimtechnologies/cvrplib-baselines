# xltwbase: expectations written before `xltwbase-study-v1` ran (2026-10-31 ~13:00 UTC)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.

**Why.** CVRPLib's VRPTW BKS Challenge (1,000 to 10,000 customers) ranks by vehicles first, then distance. Our
`vrptwl/` baseline (v0.3.1) gave PyVRP 0.14.1's `minimise_fleet` 300 s and `solve` 300 s on each 1,000-customer
instance. Its `results.json` shows two kinds of waste:

- On 41 of 60 instances `minimise_fleet` reached its own lower bound (the capacity bound) within seconds (R1_10_4:
  4.9 s), and the unused part of its 300 s was thrown away; `solve` still got only 300 s.
- On R1_10_1 it ran the full 300 s and returned 100 vehicles. Our `vrptwlb/` bound says 100 is the minimum in double
  precision (a clique of 100 customers no route can share), so that whole half was spent on fleets that cannot exist.
  PyVRP's own code leaves this open (a TODO in `minimise_fleet` mentions tighter bounds, such as ones based on time).

`xltwbase.py` runs the same loop as `minimise_fleet`, stops it at K = max(Martello-Toth L2, time-window clique) from
`xltwlb.py` (v0.3.3), and gives `solve` everything the fleet phase did not use. It is the baseline we plan to run on
XLTW-Test once CVRPLib publishes it, in the challenge's own travel-time convention. This check makes sure it works
and measures what the budget change is worth. It is plain engineering, not a new method.

**Method.** The 13 Gehring-Homberger 1,000-customer instances below, read from the same cached CVRPLib files as
`vrptwl/`. The VRPLIB copy, the x1,000 rounded-up scaling, the seed (20261030), PyVRP 0.14.1 and the 600 s total per
instance are all as in `vrptwl-fleet-v1`; three runs at a time, one CPU each. With the same fleet, PyVRP's search with
the same seed follows the same path, so a longer `solve` can only continue it, unless this machine runs slower.

- **E** (8): `minimise_fleet` reached the capacity bound within 12 s: R1_10_4, R1_10_6, R1_10_8, RC1_10_3, RC1_10_10,
  R2_10_4, RC2_10_9, C1_10_4.
- **T** (1): the time-window bound is above the capacity bound and equals the record: R1_10_1 (K 100, KC 91).
- **F** (4, controls): `minimise_fleet` used its full 300 s: C1_10_1, C1_10_7, C2_10_6, RC2_10_1.
- **Conventions** (4 runs, 120 s each): R1_10_1 and RC2_10_9 under 'dimacs' (arcs truncated to 0.1, scaled x10) and
  'round' (nearest integer), with K computed in that convention.

Every result is re-checked by `check_exact()`: coverage, capacity and every arrival, including the return to the
depot, in 50-digit decimals from the file's own tokens, in the run's convention (tolerance 1e-6 for double, none for
the others). The baseline numbers are copied into the script from `vrptwl/results.json`.

**Predictions** (scored by `score_q()` in `xltwbase.py`):

| | Prediction | Basis | Our odds |
|---|---|---|---|
| Q0 | All 17 runs finish; every result visits each customer once within capacity; none that PyVRP calls feasible fails the exact check; no on-time result uses fewer vehicles than its K; every clique is confirmed exactly. | Hygiene; the parts were each tested before. | 85% |
| Q1 | All 17 results are on time in their own convention. | All 60 `vrptwl/` results were. | 90% |
| Q2 | On all 8 E instances the vehicle count equals `vrptwl/`'s. | Same loop, same seed, and the bound equals PyVRP's own there. | 90% |
| Q3 | On at least 7 of the 8 E instances the distance is shorter than `vrptwl/`'s. | `solve` gets about 590 s instead of 300 s on the same search path. | 85% |
| Q4 | The median distance reduction on the E instances is at least 1.5%. | `vrptwl/` was 10% to 37% above SINTEF on R1/RC1 and 1% to 4% on R2/RC2; how much of that a second 300 s recovers is unknown. | 55% |
| Q5 | On R1_10_1 the fleet phase ends with 100 vehicles in under 120 s (`vrptwl/`: 301 s). | The loop stops at K = 100 as soon as it gets there; how long that takes is unknown. | 70% |

Only reported, not predicted: the F controls (vehicles and distance against `vrptwl/`), R1_10_1's distance, iterations
per second against `vrptwl-fleet-v1` (a check on machine speed), the convention runs' vehicles against their K, and
any comparison with SINTEF's records.

**Limits stated in advance.** One seed, one CPU, 600 s, 13 instances; the comparison is with one earlier run on a
shared machine, so a slower machine would weaken Q3 and Q4 (the iterations-per-second line shows it). Giving unused
time to the second phase is an obvious change; the point is to have a checked baseline ready for XLTW-Test. No result
here is a record; if one looked like one, it would be re-checked by a separately written checker before any claim.
