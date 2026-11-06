# xltwfc: expectations (pre-registered)

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. CC BY 4.0.
Written and published on 2026-11-06, before any run of this study. The jobs wait until this file is public on `main`
and byte-identical to their own copy before they run anything.

## Question

The packaged solver's fleet phase is PyVRP's minimise_fleet loop: drop one vehicle, search from scratch for the first
feasible solution, repeat. In `xltwfull/` part a (full limit T(n), seed 20261104; raw results and
`xltwfull/part-a.md` published, F0-F5 not yet scored), that loop stalled. On n1234 it printed its last count (34) at 86 s and spent the rest of its fleet phase,
about 1,020 s, on one attempt at 33 that never succeeded. On n1608 each step took about twice as long as the one before
(112 vehicles at 80 s, 111 at 151 s, 110 at 303 s, 109 at 586 s, 108 at 1,124 s). Both stayed far above the time-based
fleet bound K* (34 against 27; 108 against 81).

Does a different fleet phase, ONE search that charges a fixed cost per vehicle and is never restarted from scratch,
use fewer vehicles in the same time? This is the obvious weighted-objective alternative that PyVRP supports
(`VehicleType.fixed_cost`), not a new method. Earlier fleet variants (`xltwrm/`: warm start, thin ejection; `xltwrs/`:
capped restarts) lost to the plain loop on Gehring-Homberger instances, so the plain loop is the baseline to beat.
`xltwff/`, pre-registered earlier the same day, keeps the loop and gives it 0.8 of the time instead of 0.5; this
study keeps the 0.5 split and changes the search. Both are scored against the same xltwfull runs, separately.

## What runs

`fcsolver.py` (solver 0.1.0-fc1). Everything except the fleet phase is the published package (`xltwpkg/` at commit
19c7eb6: package 0.1.1, solver 0.1.0, PyVRP 0.14.1), imported from its `solver.py` and not changed: reading in the
challenge's convention, the bound K, stdout discipline, printer, watchdog, the split of time (fleet phase: half of the
time left after the bound) and the distance phase. The fleet phase is:

1. one solve with the instance's own fleet until the first feasible solution (k0 routes, distance d0);
2. one PyVRP solve from that solution, with at most k0 vehicles, each with fixed cost F = 10 x ceil(d0 / k0) (ten mean
   route lengths), until the fleet deadline, SIGTERM, or a solution at K. Every feasible new best is printed under the
   usual rule (fewer routes first, then distance). PyVRP's late-acceptance search moves on the penalised cost, so it
   can pass through late solutions with fewer routes; its best is always feasible.

The distance phase then runs as in the package with the fewest routes found, no fixed cost, from the best solution.

The harness is `xltwfull/fullrun.py` as published (commit 876bd94), imported unchanged; only the program it starts
differs (`fcbin/solver`, a launcher for `fcsolver.py` under the package's interpreter). Same four instances, same seed
20261104, full limits T(n) = 1,800 x n / 1,000 s, network off, SIGTERM at the limit, SIGKILL 5 s later, the last
complete solution printed before the limit counts and is re-checked exactly. Frozen runs (harness poll gap above 1 s)
are invalid and re-run once; a frozen re-run means no valid run for that instance.

| run | instance | n | T(n) s | xltwfull (full limit) | K* |
|---|---|---|---|---|---|
| F1 | XLTW-Test-n1234 | 1,233 | 2,219.4 | 34 | 27 |
| F2 | XLTW-Test-n1421 | 1,420 | 2,556.0 | not run yet | 47 |
| F3 | XLTW-Test-n1608 | 1,607 | 2,892.6 | 108 | 81 |
| F4 | XLTW-Test-n1841 | 1,840 | 3,312.0 | not run yet | 18 |

Each job first runs the unit tests and a 40 s smoke run on XLTW-Test-n1048 (it must be a valid run in which the
fixed-cost solve ran, or the job stops). Then `xltwfc-a-v1` runs F1 and F3, `xltwfc-b-v1` F2 and F4 (1 CPU, 1 GB
each). A later job runs `fcrun.py --merge results-a.json,results-b.json --full <xltwfull/results.json>` once both this
study and xltwfull's merge exist; it alone scores S0-S5.

## Predictions

- **S0 (gate).** Offline build with the pinned wheels, network unreachable during the runs, and each of F1-F4 has a
  valid run (not frozen, stopped by itself with exit 0, counted solution feasible in exact arithmetic, `Cost` line equal
  to its distance, nothing else on stdout) in which the fixed-cost solve ran (F set, at least one iteration). If S0
  fails, S1-S5 are untestable.
- **S1.** On the instances where xltwfull also has a valid run (at least 3 of the 4, otherwise S1 and S2 are
  untestable), the fixed-cost phase uses at most as many vehicles in total as xltwfull.
- **S2.** On those instances, it uses strictly fewer vehicles than xltwfull on at least 2.
- **S3.** The four together still use at least 199 vehicles (at least 15% above their total K* of 173).
- **S4.** None of the four ends at its K*.
- **S5.** Every run's peak memory is at most 0.6 GB, and the watchdog never fires.

S1 and S2 say the one-search fleet phase beats the restart loop on these capacity-free instances; S3 and S4 say most
of the gap to K* stays either way.

## Reported, not predicted

F, k0 and when it was found, when the final count was first printed, iterations of the fixed-cost solve, distances
against xltwfull (not comparable when the vehicle counts differ), and every counted solution in `sols/`. One seed and
four instances: a calibration for the algorithm-track entry, not a general result. F was chosen once, before any run,
and is not tuned. K* is a lower bound, not a known optimum.
