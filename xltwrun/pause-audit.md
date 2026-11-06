# xltwrun: which timed runs were paused by the host (audit and correction, 2026-11-06)

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. CC BY 4.0.

## Correction first

`part-b-note.md` (2026-11-06 ~05:30 UTC) called the n8575 run in part b2 "one real failure": a PyVRP call that ran for
more than 450 s without returning to Python. **That was wrong.** The container was paused by the host for about
439 s of that run (from about 76 s to about 515 s; the limit was 514.4 s). The same goes for the n10001 case noted in
`../xltwpkg/addendum-2026-11-06.md`. We have no field evidence of a PyVRP call that ignores the clock. A public
claim built on the n8575 case ("a PyVRP baseline can overrun the VRPTW Challenge's stop signal on large
capacity-free instances") is withdrawn.

## How we found it

The jobs run in containers on two shared machines. When a machine runs short of memory, the job runner pauses the
whole container (`docker pause`) and resumes it later; it logs every pause and resume. A pause freezes both the
solver and the harness, but the clock keeps going. The solver's own clock check then sees less real search time
than its limit, and if the limit passes during the pause the harness wakes up late.

The harness used for `xltwrun` (commit ba1eec8) only caught the second case, with a rule fixed before the re-runs:
SIGTERM sent more than 1 s after the limit = frozen. The newer harness (`xltwpkg/`, `xltwfull/`) measures the gap
between its own polls (every 0.05 s; a gap over 1 s = frozen). On 2026-11-06 the newer harness flagged a 534 s gap in
`xltwpkg-n8575-v2`; the runner's log shows that container paused from 18:36:39 to 18:45:33 UTC (534 s). It also
flagged an 84.6 s gap in `xltwfull-b-v1` (F4), matching a logged pause from 20:01:35 to 20:03:00 (85 s). So the
runner's log is a reliable record, and we checked every `xltwrun` job against it.

Method: each job ran its instances one after another (`--workers 1`). The run step's start time (from the job's
`run.exits`) plus the wall time of each run in completion order gives each run's start and end; we intersected
these with the logged pause intervals for that job's container. Logged times are when the runner's command
returned, a few seconds after the pause took effect, so the figures below are good to about ±10 s.

## Result

Part a (80 runs, Blade, 2026-11-04) and the re-run part b1r (Dell) had no pauses. In part b and the b3 re-runs:

| part | instance | limit s | paused (s into the run) | old rule said | what it means |
|---|---|---|---|---|---|
| b1 | n7193 | 431.5 | ~384 to past the limit | frozen | re-run in b1rb (clean) |
| b1 | **n7037** | 422.2 | **~216 to ~400 (184 s)** | **valid** | counted run had 44% less search time |
| b1 | n6884 | 413.0 | ~146 to past the limit | frozen | re-run in b1ra (clean) |
| b1 | n6734 | 404.0 | ~97 to past the limit | frozen | re-run in b1ra (clean) |
| b2 | **n8575** | 514.4 | **~76 to ~515 (439 s)** | **valid, SIGKILL** | not a stuck call; thawed at the limit |
| b2 | **n8389** | 503.3 | **~208 to ~392 (184 s)** | **valid** | 37% less search time |
| b2 | n8207 | 492.4 | ~57 to past the limit | frozen | re-run in b2r (clean) |
| b2 | n8028 | 481.6 | ~97 to past the limit | frozen | re-run in b2r (clean) |
| b3 | **n10001** | 600.0 | **~195 to ~558 (363 s)** | **valid, SIGKILL** | thawed 42 s before the limit, missed the 5 s grace |
| b3 | n9571 | 574.2 | ~173 to past the limit | frozen | re-run in b3rb, paused again (next row) |
| b3 | **n9363** | 561.7 | **~203 to ~476 (273 s)** | **valid** | 49% less search time |
| b3 | n9160 | 549.5 | ~127 to past the limit | frozen | re-run in b3ra, frozen again |
| b3ra | n9160 | 549.5 | ~185 to past the limit | frozen | no valid run left under the rule |
| b3rb | **n9571** | 574.2 | **~113 to ~212 (99 s)** | **valid** | 17% less search time |

Clean in part b: n6588, n7353, n7516, n7683 (b1), n7854, n8766 (b2), n8960, n9784 (b3).

So, of the 20 part-b instances, the old rule correctly caught 8 frozen runs (7 first runs and the n9160 re-run), but 6 counted
runs were also paused: four silently shortened (n7037, n8389, n9363 and the n9571 re-run) and two (n8575, n10001)
that we had blamed on the solver. Only 13 of the 20 part-b instances have a clean counted run: the four b1 and
two b2 clean runs and n8960, n9784 above, plus the clean re-runs of n6734, n6884, n7193, n8028 and n8207.

## What changes

- The XLTW-Test report scores G0-G5 exactly as pre-registered (the late-SIGTERM rule, one re-run). Its text will
  list the six paused counted runs and n9160 next to the score, so nobody reads them as solver results.
- G0 fails either way: n8575 and n10001 were SIGKILLed, and so was the frozen n9160 re-run.
- Every timed harness from now on detects pauses by poll gaps (as `xltwpkg/` and `xltwfull/` already do), and
  every scored run is also checked against the runner's pause log.
- The seven affected instances (n7037, n8389, n8575, n9160, n9363, n9571, n10001) need a clean run before the
  report's numbers are used as baselines. That waits until timed jobs can run without pauses.

## Why this matters beyond us

Anyone benchmarking a wall-clock-limited solver in containers on a shared machine (cloud spot instances, CI
runners, a laptop that swaps) can get runs that look valid but had much less search time, or a "solver ignored
SIGTERM" failure that is really a thaw just before the limit. A late-signal check misses most of them; a poll-gap
check inside the harness, or the host's pause log, catches them.
