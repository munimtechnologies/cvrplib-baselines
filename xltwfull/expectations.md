# xltwfull: expectations (pre-registered)

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. CC BY 4.0.
Written and published on 2026-11-06, before any run of this study. The jobs wait until this file is public on `main`
and byte-identical to their own copy before they run anything.

## Question

On the 27 capacity-free XLTW-Test instances of part a (`xltwrun/`, limits T(n)/30), the baseline used 1.46 times the
time-based fleet bound K* (median; `xltwen/`), and none of the runs ended at K*. Is that gap mostly an effect of the
short limit? The fleet phase is PyVRP's minimise_fleet loop, stopped at the bound K, and it gets half the time; at
T(n)/30 every one of these runs was still in that loop when its half ran out.

## What runs

The packaged solver as published (`xltwpkg/` at commit 19c7eb6: package 0.1.1, solver 0.1.0, PyVRP 0.14.1), built
offline with `build.sh --offline`, its own 21 unit tests first. Each run exactly as the challenge runs algorithms:
`./solver INSTANCE T(n) 20261104` (the seed of part a), T(n) = 1,800 x n / 1,000 s with n customers, network off,
SIGTERM at the limit, SIGKILL 5 s later, the last complete solution printed before the limit counts and is re-checked
exactly (nearest-integer arcs, `xltwbase.check_exact`). One solver at a time per job. No change to the solver.

The four smallest capacity-free instances where K* is above K:

| run | instance | n | T(n) s | part a vehicles (T/30) | K | K* |
|---|---|---|---|---|---|---|
| F1 | XLTW-Test-n1234 | 1,233 | 2,219.4 | 35 | 7 | 27 |
| F2 | XLTW-Test-n1421 | 1,420 | 2,556.0 | 72 | 16 | 47 |
| F3 | XLTW-Test-n1608 | 1,607 | 2,892.6 | 113 | 7 | 81 |
| F4 | XLTW-Test-n1841 | 1,840 | 3,312.0 | 29 | 4 | 18 |
| | total | | 10,980 | 249 | 34 | 173 |

Two jobs: `xltwfull-a-v1` runs F1 and F3, `xltwfull-b-v1` runs F2 and F4 (1 CPU, 1 GB each; they may run at the same
time). A third job, after both, runs `fullrun.py --merge results-a.json,results-b.json`, which alone scores F0-F5.

Frozen runs (the host can pause a container, which freezes the harness too): a run whose harness went more than 1 s
between two polls is invalid and is re-run once, unchanged; if the re-run is frozen too, that instance has no valid
run. This is the rule already used in `xltwrun/`.

## Predictions

- **F0 (gate).** The build is offline with the pinned wheels, the network is unreachable during the runs, and each of
  F1-F4 has a valid run: not frozen, stopped by itself with exit code 0, and its counted solution is feasible in exact
  arithmetic, with a `Cost` line equal to its distance and no other line on stdout. If F0 fails, F1-F5 are untestable.
- **F1.** On every one of the four, the full-limit run uses at most as many vehicles as part a did (35, 72, 113, 29).
- **F2.** The four together use at most 224 vehicles: at least 10% fewer than part a's 249.
- **F3.** The four together use at least 208 vehicles: still at least 20% above their total K* of 173.
- **F4.** At most one of the four ends at its K*.
- **F5.** Every run's peak memory is at most 0.6 GB, and the watchdog never fires (the solver stops by itself).

F2 and F3 together say: thirty times the time helps, but most of the gap to K* stays. If F3 fails, the gap was mostly a
time effect; if F2 fails, more time barely helps this fleet search.

## Reported, not predicted

Each run's printed vehicle counts over time (when the final count was first printed), fleet solves, distance against
part a (not comparable when the vehicles differ), and every solution in `sols/`. One seed and four instances: this
is a calibration for the algorithm-track entry, not a general result. K* is a lower bound, not a known optimum, so a
gap to K* may be the bound's as much as the solver's.
