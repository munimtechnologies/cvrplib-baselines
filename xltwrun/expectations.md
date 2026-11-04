# xltwrun: expectations, written before the run

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Fixed on 2026-11-04 (UTC) before `solver.py` was run on any XLTW-Test instance. The git commit that adds this file
dates it.

## Why

CVRPLib's VRPTW BKS Challenge has an algorithm track (registration and submissions 2026-12-16 to 2027-01-16). The
organisers run each submitted solver themselves: `./solver instance.vrp <seconds> <seed>`, one logical CPU,
SIGTERM at the time limit T(n) = 1,800 s x n / 1,000 and SIGKILL five seconds later; only the last complete feasible
solution printed to stdout before the limit counts. A short report on the XLTW-Test set is mandatory.

Everything in this repository so far called PyVRP from inside one Python job. [`solver.py`](solver.py) is the
`xltwbase.py` baseline (fleet search stopped at the bound K, the rest of the time to distance, from
[`xltwbase/`](../xltwbase/), with the plain fleet loop that [`xltwrm/`](../xltwrm/score.md) and
[`xltwrs/`](../xltwrs/score.md) kept) wrapped as a stand-alone program that follows that protocol.
[`xltwrun.py`](xltwrun.py) runs it the way the organisers will and checks what it prints. This is the first run of
both on the real test set, and the start of the XLTW-Test report.

## What runs

- All 100 XLTW-Test instances (archive SHA-256 `9635b9fa...4f631`, the copy read on 2026-11-02), one run each,
  seed 20261104, nearest-integer rounding (the challenge's rule).
- **Time limits divided by 30**: T(n)/30 = 60 s per 1,000 customers (56.5 s at 1,047 customers, 600 s at 10,000),
  because 100 full-length runs would take 208 CPU-hours. Results at T(n)/30 are a floor, not what the solver does at
  the real limit.
- One solver process per instance, each single-threaded, up to 4 at a time on a shared machine, and only as many as
  an estimated memory budget allows (`mem_est`: 0.15 GB + 4 GB x (n / 10,000)^2).
- In two parts: part **a**, the 80 instances up to 6,444 customers, now (4 CPUs, 4 GB); part **b**, the 20 largest
  (6,587 to 10,000 customers), in a later job sized from part a's measured memory. Both parts run the same code with
  the same settings; `xltwrun.py --merge` scores them together once both are done.
- Every counted solution is re-checked in 50-digit decimal arithmetic (`xltwbase.check_exact`, 'round').
- K is the fleet lower bound from [`xltwtest/`](../xltwtest/score.md) (computed without a time cap). The solver
  computes its own bound with at most 10% of its limit and falls back to the capacity bound when that is not enough;
  at these short limits that will happen on the instances whose bound is slow.

## Predictions (each scored on its own, all on the 100 runs together; untestable if any run is missing)

| | Prediction | Our odds |
|---|---|---|
| G0 | Every run counts: each prints at least one complete solution before its limit, the last one before the limit is on time in exact arithmetic and its `Cost` line matches its routes, nothing else appears on stdout, no run needs SIGKILL, and no counted solution uses fewer vehicles than K. | 85% |
| G1 | The solver stops by itself before the limit on all 100 runs (the harness never sends SIGTERM). | 80% |
| G2 | Between 20 and 55 of the 100 runs end with exactly K vehicles. | 55% |
| G3 | Of the 33 instances where capacity never binds (KC = 1), at most 5 end at K. | 70% |
| G4 | The median of (vehicles - K) / K over the 100 runs is at most 10%. | 55% |
| G5 | Every run's peak memory (VmHWM) is at or below `mem_est` for its size. | 60% |

Why: on CVRPLib's 1,000-customer Gehring-Homberger instances PyVRP's fleet loop reached the capacity bound within
12 s on most instances where it is reachable ([`vrptwl/`](../vrptwl/score.md)), so many of the 67 KC > 1 instances
should end at K even at 60 s per 1,000 customers. On the 33 KC = 1 instances K is a greedy clique bound that ignores
route length, so we expect it to be far below what any solver reaches. The memory estimate assumes up to two copies
of PyVRP's distance and duration matrices; we have not measured that.

**Reported, not predicted:** vehicles, distance, time of the last improvement and number of printed solutions per
instance; on how many instances the solver's own bound was cut short; fleet-phase time; PyVRP iterations; peak
memory by size.

## Limits

One seed, one run per instance, limits divided by 30, a shared machine with up to 4 runs at a time. K is a lower
bound, not a known optimum, so "at K" proves the fleet is minimal but "above K" proves nothing. The solver's code
runs on Python 3.12 with PyVRP 0.14.1 installed from PyPI; a submission must build offline, which is not tested
here. Wall-clock stopping makes runs depend on machine speed even with a fixed seed.
