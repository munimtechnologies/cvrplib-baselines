# xltwff: expectations (pre-registered)

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. CC BY 4.0.
Written and published on 2026-11-06, before any run of this study. The jobs wait until this file is public on `main`
and byte-identical to their own copy before they run anything.

## Question

The VRPTW challenge ranks solutions by vehicles first; distance only breaks ties. xltw-solver 0.1.0 gives its fleet
phase (PyVRP's minimise_fleet loop, stopped at the bound K) half of the time and the distance phase the rest. Would
it do better on vehicles, at little cost in distance, if the fleet phase got 0.8 of the time?

What we knew when writing this: part a of `xltwfull/` (F1 and F3, the unchanged solver at the full limit; raw
results in `xltwfull/results-a.json`). Part b (F2, F4) had not run yet.

- F1 (n1234): 34 vehicles, first printed at 86.4 s. The fleet phase ended at about 1,107 s, so one attempt at 33
  vehicles ran for about 1,020 s (46% of the limit) and failed. The distance phase took the distance from 91,405
  to 83,690; it was at 83,851 by 1,494 s, so its last 720 s gained 0.2%.
- F3 (n1608): 108 vehicles. The fleet loop was still finding vehicles when its half ran out: 111 at 151 s, 110 at
  303 s, 109 at 586 s, 108 at 1,124 s; the attempt at 107 was cut at about 1,443 s. The distance went from 113,877
  to 112,655, and was at 112,900 by 2,030 s.

## What runs

The packaged solver as published (`xltwpkg/` at commit 19c7eb6: package 0.1.1, solver 0.1.0, PyVRP 0.14.1) with
exactly one change, applied by `getff.py` before the build: in `solver.py` the line `FLEET_FRAC = 0.5` becomes
`FLEET_FRAC = 0.8` (and `VERSION` becomes `0.1.0+ff08`). Each old line must occur exactly once, or the job stops.
Nothing else changes: same bound, same loop, same distance phase, same printer and watchdog.

Each run uses xltwfull's own harness unchanged (`xltwfull/fullrun.py` at commit 876bd94, `run_one`): built offline
with `build.sh --offline`, the package's 21 unit tests first, then `./solver INSTANCE T(n) 20261104`, T(n) = 1,800 x
n / 1,000 s, network off, SIGTERM at the limit, SIGKILL 5 s later, the last complete solution printed before the
limit counts and is re-checked exactly (nearest-integer arcs). One solver at a time per job.

| run | instance | n | T(n) s | compared with | K | K* |
|---|---|---|---|---|---|---|
| H1 | XLTW-Test-n1234 | 1,233 | 2,219.4 | xltwfull F1 | 7 | 27 |
| H2 | XLTW-Test-n1421 | 1,420 | 2,556.0 | xltwfull F2 | 16 | 47 |
| H3 | XLTW-Test-n1608 | 1,607 | 2,892.6 | xltwfull F3 | 7 | 81 |
| H4 | XLTW-Test-n1841 | 1,840 | 3,312.0 | xltwfull F4 | 4 | 18 |

Two jobs: `xltwff-a-v1` runs H1 and H3, `xltwff-b-v1` runs H2 and H4 (1 CPU, 1 GB each). After both, and after
xltwfull's merge, a third job runs `ffrun.py --merge results-a.json,results-b.json --ref <xltwfull results.json>`,
which alone scores H0-H5. Frozen runs follow xltwfull's rule: a run whose harness went more than 1 s between two
polls is invalid and is re-run once, unchanged; if the re-run is frozen too, that instance has no valid run.

## Predictions

- **H0 (gate).** The patch applied (both lines exactly once), the build is offline with the pinned wheels, the
  network is unreachable during the runs, and each of H1-H4 and each of xltwfull's F1-F4 has a valid run (xltwfull's
  definition). If H0 fails, H1-H5 are untestable.
- **H1 (85%).** The four 0.8 runs together use at most as many vehicles as the four 0.5 runs.
- **H2 (50%).** At least one of the four 0.8 runs uses fewer vehicles than its 0.5 run.
- **H3 (80%).** The four together save at most 4 vehicles against the 0.5 runs: the extra 30% of the time buys
  little against the gap to K*.
- **H4 (85%).** On every instance where both use the same number of vehicles, the 0.8 run's distance is at most 1%
  longer. (If no instance has equal counts, H4 is untestable.)
- **H5 (90%).** Every 0.8 run's peak memory is at most 0.6 GB, and the watchdog never fires.

If H2 and H4 hold, 0.8 is the better default for the algorithm-track entry: more vehicles found, almost no distance
lost. If H2 fails, the fleet loop's late attempts are the bottleneck, not its share of the time, and the next fleet
idea must change the search, not the split.

## Reported, not predicted

Each run's fleet seconds, fleet solves, when its final count was first printed, and its distance against the 0.5
run; every solution in `sols/`. The runs stop on the wall clock, and the 0.5 and 0.8 runs may run on different
machines, so equal seeds do not guarantee equal fleet trajectories up to the 0.5 point. One seed and four
instances: a calibration for the entry, not a general result. K* is a lower bound, not a known optimum.
