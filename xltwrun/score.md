# xltwrun: scored (2026-11-07). 1 of 6 predictions held

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Text CC BY 4.0.

Pre-registration: [expectations.md](expectations.md) (G0-G5, fixed on 2026-11-04 before any run). The merged scoring
is mechanical: job `xltwmerge-v1` (Blade, 2026-11-07 09:03-09:06 UTC) ran the pre-registered
`xltwrun.py --merge` on part a and the filtered part b files (`filt.py`, rule in [part-b-note.md](part-b-note.md);
what it replaced is in [filter-report.json](filter-report.json)). Output: [results.json](results.json),
[results.md](results.md) (all 100 instances).

## Verdicts

| | prediction (verbatim) | verdict |
|---|---|---|
| G0 | Every run counts: each prints at least one complete solution before its limit, the last one before the limit is on time in exact arithmetic and its `Cost` line matches its routes, nothing else appears on stdout, no run needs SIGKILL, and no counted solution uses fewer vehicles than K. | **did not hold**: 3 runs needed SIGKILL (n8575, n10001, and n9160, whose only usable attempt was frozen by a host pause and kept by the filter rule). No counted solution is flagged infeasible in the exact re-check, and none is below K. |
| G1 | The solver stops by itself before the limit on all 100 runs (the harness never sends SIGTERM). | **did not hold**: SIGTERM on the same 3 runs; 97 stopped by themselves |
| G2 | Between 20 and 55 of the 100 runs end with exactly K vehicles. | **did not hold**: 6 |
| G3 | Of the 33 instances where capacity never binds (KC = 1), at most 5 end at K. | **held**: 0 |
| G4 | The median of (vehicles - K) / K over the 100 runs is at most 10%. | **did not hold**: 51.5% |
| G5 | Every run's peak memory (VmHWM) is at or below `mem_est` for its size. | **did not hold**: 67 of 100 above it, by at most 17% (n6445: 2.117 GB against 1.811 GB) |

## What it means

- **The fleet search is the weak spot, not the bound alone.** 18,529 vehicles in total against K = 11,298. Only 6
  runs end at K (n1654, n1888, n2307, n3287, n3334, n4738), all with KC > 1. We expected 20-55 because PyVRP's loop
  reached the capacity bound quickly on 1,000-customer Gehring-Homberger instances. XLTW-Test's larger
  instances, at a thirtieth of the time, are a different matter. Against the stronger time-window bounds K*
  ([../xltwen/score.md](../xltwen/score.md), total 13,961) the total is 33% above the bound. On the 33 capacity-free
  instances the gap is about 1.5 times K*.
- **The 3 SIGKILLs come from the host, not the solver's logic.** All 3 are among the 7 instances the pause audit
  flagged ([pause-audit.md](pause-audit.md)): the job runner paused part b's containers when the Blade was short of
  memory, and a paused process cannot answer SIGTERM. The packaged solver (`xltwpkg/`) has since added a watchdog,
  and full-limit runs are now checked against the runner's pause log before scoring. Those 7 instances get clean
  single-instance re-runs.
- **Memory.** The pre-registered estimate 0.15 + 4 x (n / 10,000)^2 GB was too low on two-thirds of the runs. The
  fit we have used since part a, 0.17 + 4.7 x (n / 10,000)^2 GB, covers all 100 peaks (largest: n10001, 4.62 GB).

Limits: limits divided by 30, one seed, one run per instance, up to 4 runs at a time on shared machines. K is a lower
bound, not a known optimum.

## Where the full-limit studies stand (same day)

- `xltwfull/` (the packaged solver at the full limit T(n), four capacity-free instances): gate failed (one run
  paused), see [../xltwfull/score.md](../xltwfull/score.md). The merged [../xltwfull/results.json](../xltwfull/results.json)
  is now public.
- `xltwff/` (0.8 of the time to the fleet search) and `xltwfc/` (one fixed-cost fleet search): scored by hand in
  [../xltwff/score.md](../xltwff/score.md) and [../xltwfc/score.md](../xltwfc/score.md).
- `xltwdet/` (stopping on an iteration budget so a seed gives one answer): its first job stopped in its own unit
  test, before any study run; see [../xltwdet/addendum-2026-11-07.md](../xltwdet/addendum-2026-11-07.md).
