# xltwfc: scored (2026-11-07). The fixed-cost fleet search lost to the plain loop

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Text CC BY 4.0.

Pre-registration: [expectations.md](expectations.md) (S0-S5, fixed on 2026-11-06 before any run), with
[addendum-2026-11-07.md](addendum-2026-11-07.md) (fix of the PyVRP 0.14 route call that crashed the first jobs' smoke
run; re-run rule). Raw outputs: [results-a.json](results-a.json) / [results-a.md](results-a.md) (F1, F3; job
`xltwfc-a-v2`) and [results-b.json](results-b.json) / [results-b.md](results-b.md) (F2, F4; job `xltwfc-b-v2`), plus
`logs-a/`, `logs-b/`, `logs-smoke/`, `smoke-*.json`, `sols/`. Both jobs ran on the Blade on 2026-11-07 (10:45-12:28
UTC), and the runner's log has no pause for either (ids 499abb8c65db, 240c2fa8b60f). These verdicts were first
written out by hand from those files.

**Merge reproduced (2026-11-08).** The pre-registered merge (`fcrun.py --merge results-a.json,results-b.json --full
../xltwfull/results.json`) ran as job `xltwscore-v1` (Blade, 2026-11-07 21:20-21:22 UTC) on the files fetched from
`main`, and printed exactly the verdicts below: `{"S0": "held", "S1": "did not hold", "S2": "did not hold", "S3":
"held", "S4": "held", "S5": "held"}`. Its output is [results.json](results.json) and [results.md](results.md).

## Verdicts

| | prediction (verbatim) | verdict |
|---|---|---|
| S0 | (gate) Offline build with the pinned wheels, network unreachable during the runs, and each of F1-F4 has a valid run (not frozen, stopped by itself with exit 0, counted solution feasible in exact arithmetic, `Cost` line equal to its distance, nothing else on stdout) in which the fixed-cost solve ran (F set, at least one iteration). If S0 fails, S1-S5 are untestable. | **held**: all four valid on the first attempt, F = 19,250 / 17,670 / 10,200 / 19,480, and 468,668-592,458 fixed-cost iterations each |
| S1 | On the instances where xltwfull also has a valid run (at least 3 of the 4, otherwise S1 and S2 are untestable), the fixed-cost phase uses at most as many vehicles in total as xltwfull. | **did not hold**: 170 against 167 (n1234, n1608, n1841) |
| S2 | On those instances, it uses strictly fewer vehicles than xltwfull on at least 2. | **did not hold**: on none (34 = 34, 110 > 108, 26 > 25) |
| S3 | The four together still use at least 199 vehicles (at least 15% above their total K* of 173). | **held**: 237 |
| S4 | None of the four ends at its K*. | **held** |
| S5 | Every run's peak memory is at most 0.6 GB, and the watchdog never fires. | **held**: 0.17-0.28 GB; watchdog never fired |

## Table

| instance | T(n) s | k0 (first feasible) | fixed-cost | plain loop (xltwfull) | 0.8 loop (xltwff) | K* | fixed-cost final count first printed at s | distance |
|---|---|---|---|---|---|---|---|---|
| n1234 | 2,219.4 | 63 | 34 | 34 | 33 | 27 | 531.8 | 82,856 |
| n1421 | 2,556.0 | 114 | 67 | 65 (invalid: paused) | 65 | 47 | 1,970.7 | 131,617 |
| n1608 | 2,892.6 | 124 | 110 | 108 | 108 | 81 | 1,162.1 | 112,789 |
| n1841 | 3,312.0 | 78 | 26 | 25 | 25 | 18 | 620.2 | 82,826 |

## What it means

A clean negative result. One long search that charges each vehicle ten mean route lengths, and is never
restarted, ends with as many or more vehicles than PyVRP's restart loop (drop one vehicle, search again from
scratch) on every instance. It is 2 behind on n1421 and n1608. It is the third fleet variant to lose to the plain
loop, after warm starts and thin ejection (`xltwrm/`) and capped restarts (`xltwrs/`). The penalised search
does pass through solutions with fewer routes, but a fixed cost per vehicle is not enough pressure to empty a route
when the time windows are tight. That is what route-elimination methods built for this (ejection pools, squeeze;
Nagata & Bräysy 2009) target; the pre-registered test of one is [../nbrm/expectations.md](../nbrm/expectations.md).
On n1234, at the same 34 vehicles, the fixed-cost run's distance (82,856) is 1.0% shorter than the plain loop's
(83,690). That is a by-product: the fixed-cost search also shortens routes during the fleet phase, which the restart
loop does not. It is not a fleet gain.

Limits: one seed, four instances, one value of F chosen before any run and not tuned. K* is a lower bound, not a
known optimum.
