# xltwbase: scoring of `xltwbase-study-v1` (run 2026-11-01 05:29 to 06:23 UTC)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.

Predictions: [expectations.md](expectations.md), written and published before the run. Raw output:
[results.md](results.md), [results.json](results.json); on-time solutions in [sols/](sols/) (CVRPLib format, `Cost` =
distance in the run's own convention). PyVRP 0.14.1, seed 20261030, 600 s per instance (120 s for the convention
runs), three runs at a time, one CPU each; peak memory 0.35 GB for the whole job.

## Verdicts

All six predictions held as written. `score_q()` in `xltwbase.py` printed them, and each was re-checked by hand
from `results.json`.

| | Prediction | Result | Verdict |
|---|---|---|---|
| Q0 | All 17 runs finish; structure, exact check, bound and cliques clean | 17 of 17 runs; no structure failure, no PyVRP disagreement, no result below its K, every clique confirmed exactly | held |
| Q1 | All 17 results on time in their own convention | 17 of 17 | held |
| Q2 | Same vehicle count as `vrptwl/` on all 8 E instances | 8 of 8 (91, 91, 91, 90, 90, 19, 18, 90) | held |
| Q3 | Shorter than `vrptwl/` on at least 7 of 8 E instances | 8 of 8 | held |
| Q4 | Median E distance reduction at least 1.5% | 6.41% (from 0.01% on R2_10_4 to 13.71% on R1_10_6) | held |
| Q5 | R1_10_1: fleet phase ends at 100 vehicles in under 120 s | 100 vehicles after 44.6 s (`vrptwl/`: 301.1 s) | held |

## The comparison is confounded by machine speed

The expectations named one risk: the comparison is with an earlier run (`vrptwl-fleet-v1`, 2026-10-30) on a shared
machine, so a *slower* machine would weaken Q3 and Q4. The opposite happened. In this run PyVRP's `solve` made far
more iterations per second than in `vrptwl-fleet-v1` on every instance, including the four F controls, whose
`solve` had about the same 300 s in both runs:

| group | instance | iterations/s now | iterations/s in `vrptwl/` | ratio |
|---|---|---|---|---|
| E | R1_10_4 | 471.4 | 84.5 | 5.6 |
| E | R1_10_6 | 222.5 | 60.4 | 3.7 |
| E | R1_10_8 | 499.5 | 109.3 | 4.6 |
| E | RC1_10_3 | 353.3 | 96.4 | 3.7 |
| E | RC1_10_10 | 201.9 | 64.7 | 3.1 |
| E | R2_10_4 | 823.1 | 349.2 | 2.4 |
| E | RC2_10_9 | 804.8 | 531.9 | 1.5 |
| E | C1_10_4 | 500.2 | 200.1 | 2.5 |
| T | R1_10_1 | 329.0 | 101.3 | 3.2 |
| F | C1_10_1 | 489.5 | 255.8 | 1.9 |
| F | C1_10_7 | 336.2 | 133.7 | 2.5 |
| F | C2_10_6 | 463.6 | 268.3 | 1.7 |
| F | RC2_10_1 | 842.2 | 277.4 | 3.0 |

(`vrptwl/` iterations per second = its `solve` iterations / 300 s; here = iterations / the `solve` seconds of this
run.) So the E instances got roughly twice the `solve` time **and** 1.5 to 5.6 times the speed: between about 3 and
11 times as many iterations. The 6.41% median reduction measures both together. It does not show how much of it the
budget change alone is worth, and it must not be quoted as that.

What does not depend on machine speed:

- **The fleet phase stops at the bound.** On R1_10_1, `vrptwl/` spent its whole 300 s trying 99 vehicles, which the
  time-window bound rules out in double precision. Here the loop stopped at 100 after 44.6 s and 7 solves, and the
  other 555 s went to distance. On the 8 E instances the fleet phase took 2.2 to 7.4 s, as before.
- **Vehicle counts.** All 8 E instances and R1_10_1 kept `vrptwl/`'s vehicle count, as Q2 predicted.
- **Exactness.** All 17 results are on time when re-checked in 50-digit decimals in their own convention.

## Reported, not predicted

- **F controls** (fleet phase used its full 300 s in both runs): C1_10_1 100 vehicles (same), +0.003% distance;
  C1_10_7 99 (same), same distance; RC2_10_1 21 (same), -0.14%; C2_10_6 **29 vehicles instead of 30**, with 5.96% more
  distance. One fewer vehicle ranks first in the challenge's order. The faster machine is the likely reason the fleet
  search got one step further in the same 300 s.
- **R1_10_1** (T): 100 vehicles, 54,334.58, 3.83% shorter than `vrptwl/` (confounded the same way).
- **Convention runs** (120 s): R1_10_1 under DIMACS truncation 95 vehicles (K 91), the same count as CVRPLib's DIMACS
  best known solution; under nearest-integer rounding 93 vehicles (K 91). RC2_10_9 18 vehicles in both (K 18). The
  conventions give different minimum fleets on this instance (100 in double precision against 91 in the other two by
  the bound), so their counts must not be compared with each other or with records kept in another convention.
- PyVRP printed `PenaltyBoundWarning` on some runs (a penalty reached its maximum while looking for a feasible fleet).
  Every final result was feasible and passed the exact check.

## What comes next

A same-machine control (`xltwctl/`, pre-registered separately before it runs) runs the old 300 s + 300 s split and
this budget side by side in one job, on the same 9 instances, so the gain from the budget change alone can be
measured. Until then, the only claims from this run are the ones in the section above.

None of these results is a record. No result here is compared with SINTEF's records.
