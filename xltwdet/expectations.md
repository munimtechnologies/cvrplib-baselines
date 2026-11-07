# xltwdet: expectations (pre-registered)

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. CC BY 4.0.
Written and published on 2026-11-07, before any run of this study. The job waits until this file is public on `main`
and byte-identical to its own copy before it runs anything.

## Question

The rules of CVRPLib's VRPTW Challenge (algorithm track) say: "Each execution must be deterministic for a given
seed, which will be randomly selected and provided by the organizers." MV2's packaged solver (`xltwpkg/`, solver
0.1.0) is seeded, but both of its phases stop on the wall clock, so the same seed can end at a different solution on
a faster, slower or busier machine. Its own conformance test showed this (`xltwpkg/score.md`, C5b: two runs with
seed 7 on XLTW-Test-n1094 did 9,021 and 9,879 iterations).

Can the solver be made deterministic for its seed by stopping on a number of iterations fixed in advance, with the
wall clock kept only as a safety net, and what does that cost in vehicles and in unused time? Stopping on an
iteration budget is a standard technique, not a new method; what this study measures is whether this solver,
packaged for this protocol, then gives the same answer under timing noise, and how well a budget set from n and
the limit alone fits the time allowed.

## What runs

`detsolver.py` (solver 0.1.0-det1). Everything except the stopping rule is the published package (`xltwpkg/` at
commit 19c7eb6: package 0.1.1, solver 0.1.0, PyVRP 0.14.1), imported from its `solver.py` and not changed: reading,
bound K, stdout discipline, printer, watchdog, the fleet loop (minimise_fleet's, stopped at K) and the distance
phase from its solution. The stopping rule:

    budget(n, T) = floor(0.6 x 300 x (n / 1000) ** -0.5 x (T - margin(T)))   PyVRP iterations in all

where margin(T) = min(1.5 + 0.002 T, 30) s is the package's own stopping margin. The fleet phase may use half the
budget, counted over all its solves; the distance phase gets the rest. 300 x (n / 1000) ** -0.5 iterations per
second is a deliberately low fit to earlier runs' logs (about 250-450 it/s at n of 1,000-1,800, about 120 it/s at
n = 8,574), and 0.6 leaves room for slower machines. If a phase reaches the package's usual wall-clock stopping
point before its budget is spent, it stops there and the run is flagged `clock_stop`.

The harness is `xltwfull/fullrun.py` as published (commit 876bd94, `run_one`), imported unchanged: one process per
run, SIGTERM at the limit, SIGKILL 5 s later, the last complete solution printed before the limit counts and is
re-checked exactly (nearest-integer arcs). Network off, 1 CPU, 1 GB, seed 20261107, limit 120 s for every run.

On each of three XLTW-Test instances, XLTW-Test-n1048 (A), XLTW-Test-n1094 (B, the C5b instance) and
XLTW-Test-n1234 (C), five runs in this order:

| run | solver | stops on | CPU hog |
|---|---|---|---|
| W1 | detsolver.py | budget | no |
| T1 | the package's ./solver (0.1.0) | wall clock | no |
| W2 | detsolver.py | budget | no |
| W3 | detsolver.py | budget | yes |
| T2 | the package's ./solver (0.1.0) | wall clock | yes |

The CPU hog is a second process in the same one-CPU container that spins for 10 ms of every 50 ms, so the solver
gets roughly 80-90% of the CPU it gets alone. A frozen run (harness poll gap above 1 s, as when the host pauses the
container) is re-run, unchanged, until it is not frozen, at most 3 attempts in all; frozen attempts are kept.
Each counted solution is saved with its SHA-256. The same job scores D0-D6 at the end.

## Predictions

- **D0 (gate).** Offline build with the pinned wheels, network unreachable during the runs, and all 15 runs valid
  (not frozen, stopped by itself with exit 0, counted solution feasible in exact arithmetic, `Cost` line equal to
  its distance, nothing else on stdout). If D0 fails, D1-D6 are untestable.
- **D1.** On each of the three instances, W1, W2 and W3 end at the identical solution (same routes in the same order,
  same cost: equal SHA-256).
- **D2.** None of the nine budget runs stops on the wall clock or on SIGTERM.
- **D3.** Each of the six budget runs without the hog (W1, W2) ends between 30% and 85% of the limit (36-102 s).
- **D4.** On at least one of the three instances, T1 and T2 end at different solutions (the wall-clock solver is not
  deterministic for its seed under this much timing noise).
- **D5.** Together, the three W1 runs use at most one vehicle more than the three T1 runs.
- **D6.** Every run's peak memory is at most 0.6 GB, and the watchdog never fires.

D1 and D2 say the budget makes the solver deterministic for its seed on our machines, even when it is slowed; D3
says a budget set from n and the limit alone fits the time allowed; D5 says the time it leaves unused costs at most
one vehicle here.

## Reported, not predicted

Each run's budget, fleet and distance iterations, elapsed time and iterations per second, vehicles and distance for
every run, and the distance cost of the budget against T1. One seed, three instances, a 120 s limit (not T(n)):
this checks determinism and calibrates the budget; it does not measure solution quality at the challenge's limits.
Determinism here means the same machine image and the same build; identical results on other CPUs are expected
(PyVRP's search uses integer costs and its own seeded generator) but this study does not test them. If D3 fails,
the budget formula is recalibrated in a new pre-registered study, not adjusted here.
