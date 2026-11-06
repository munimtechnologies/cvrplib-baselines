# xltwpkg: scored (2026-11-06)

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Text CC BY 4.0.

Pre-registration: `expectations.md` (unchanged since the v1 jobs) and `addendum-2026-11-06.md` (published before any
v2 job ran). This file scores C0-C8 on the three v2 jobs, which ran package 0.1.1 (`solver.py` 0.1.0, byte-for-byte
the pre-registered one). Raw outputs: `results-py312.*`, `results-py311.*`, `results-n8575.*`, `logs-py312/`,
`logs-py311/`, `logs-n8575/`.

| job | image | host | ran (UTC) | peak memory of the job |
|---|---|---|---|---|
| `xltwpkg-py312-v2` | python:3.12 (CPython 3.12.15) | Dell | 18:57-19:10 | 0.16 GB |
| `xltwpkg-py311-v2` | python:3.11 (CPython 3.11.18) | Dell | 18:40-18:49 | 0.17 GB |
| `xltwpkg-n8575-v2` | python:3.12 (CPython 3.12.15) | Blade | 18:33-18:55 | 2.9 GB |

All three: network off during the run steps (checked: pypi.org unreachable), `bash build.sh --offline` passed, the
four pins in `lib/` and pyvrp/numpy imported from `lib/`, 21 unit tests passed (including the two watchdog tests and
the stdout-discipline test). No counted run was frozen by the host (largest gap between harness polls: 0.058 s).
W1's first try was frozen (a 534 s gap) and was re-run once, unchanged, as pre-registered; the frozen try stays in
`results-n8575.json` under `frozen_first_try`.

## Predictions, verbatim, and verdicts

| | prediction (from `expectations.md`) | py312 | py311 |
|---|---|---|---|
| C0 | (gate) pypi.org is unreachable during the run steps, `build.sh --offline` succeeds, and `lib/` holds exactly the four pinned versions, with pyvrp and numpy imported from `lib/`. | held | held |
| C1 | in all six runs every stdout line is a `Route #k:` line (numbered 1, 2, ... in each block) or a `Cost:` line: zero other lines. | held | held |
| C2 | all six runs have a counted solution that is feasible in the exact check, and its `Cost` line equals the recomputed distance. | held | held |
| C3 | all six runs end by themselves before the limit with exit code 0 (no SIGTERM, no SIGKILL). | held | held |
| C4 | in all six runs the counted `Cost` line arrives at least 0.5 s before the limit. | held (smallest slack 1.52 s) | held (smallest slack 1.52 s) |
| C5a | R4 and R5 (same instance, seed and limit) end with the same number of vehicles. | held (94, 94) | held (94, 94) |
| C5b | R4 and R5 end with **different** distances. | **did not hold** (79,908 and 79,908) | held (80,305 and 79,908) |
| C6 | every run's peak resident memory is at most 0.6 GB. | held (max 0.163) | held (max 0.162) |

| | prediction | n8575 job |
|---|---|---|
| C0 | the same gate | held |
| C7 | W1 ends by itself before the limit with exit code 0 (watchdog or own stop; no SIGTERM, no SIGKILL), its counted solution is feasible in the exact check with a correct `Cost` line, and stdout has no other lines. | held |
| C8 | in W1 the watchdog fires at its hard deadline, i.e. the stuck call recurs with the same seed. | **did not hold** |

Two of the seventeen verdicts failed. Both were predictions about the solver's *behaviour*, not about the package
working, and both failures are informative.

## The runs

| run | instance | limit s | seed | py312 vehicles / distance | py311 vehicles / distance |
|---|---|---|---|---|---|
| R1 | XLTW-Test-n1048 | 60 | 1 | 9 / 49,647 | 9 / 49,906 |
| R2 | XLTW-Test-n1094 | 60 | 1 | 94 / 79,895 | 94 / 80,471 |
| R3 | XLTW-Test-n1141 | 60 | 1 | 49 / 57,104 | 49 / 57,154 |
| R4 | XLTW-Test-n1094 | 60 | 7 | 94 / 79,908 | 94 / 80,305 |
| R5 | XLTW-Test-n1094 | 60 | 7 | 94 / 79,908 | 94 / 79,908 |
| R6 | XLTW-Test-n1234 | 120 | 3 | 35 / 86,522 | 35 / 87,110 |

W1 (XLTW-Test-n8575, 8,574 customers, limit 514.44 s = T(n)/30, seed 20261104): 101 vehicles, distance 166,466,
feasible, ended by itself at 511.96 s with 2.38 s of slack, 25 solutions printed, 11 fleet solves in 257.2 s, peak
3.43 GB for the solver process. The watchdog did not fire.

## What the two misses say

**C5b (py312 R4 = R5).** The search stops on the wall clock, so we expected the same seed to give different
distances. On py312 it did not: R4 and R5 both ended at 94 vehicles and 79,908, although their iteration counts
differed (9,021 and 9,879). On py311 the same pair differed (80,305 and 79,908). So a seed does **not** pin the
result (py311 shows it, and py312's iteration counts show the runs took different paths), but two runs can still
land on the same answer. C5b was worded too strongly; the point it was meant to support, that the solver is not
deterministic for its seed as the challenge asks, stands. Making it deterministic (an iteration budget calibrated to
the limit instead of a clock stop) is open work before submission.

**C8 (n8575 stall not repeated), and why.** In the baseline's part b2 run (`xltwrun-b2-v1`, on the Blade, same
seed, limit and search code) n8575 printed nothing after 64.5 s and was SIGKILLed with 156 vehicles. We called that
a stuck PyVRP call. **It was not.** W1's own first try shows what happened: this job's container was paused by the
host from 18:36:39 to 18:45:33 UTC (the job runner pauses containers when the machine runs short of memory), the
harness saw a 534 s gap between polls, marked the try frozen and re-ran it unchanged, as pre-registered. The
frozen try looks exactly like the b2 "stall": last solution at 90.5 s (147 vehicles), then nothing until the kill.
The runner's log shows the b2 container was paused from 03:06:11 to 03:13:30 UTC, which is about 76 s to 515 s into
the b2 n8575 run: the pause ended within a second or so of the limit, so the old harness's rule (SIGTERM more than
1 s late = frozen) did not catch it. The valid re-run here ran 11 fleet solves without a stall and ended with **101**
vehicles. The n10001 case in the addendum also had a 6-minute pause (about 195-558 s of its 600 s). Details and
every other affected run: `../xltwrun/pause-audit.md`. So C8 failed because its premise was wrong: there is no
field evidence of a PyVRP call that ignores the clock. The watchdog stays (the unit tests show it ends a
GIL-releasing call on time, and a run thawed just before its limit still needs to stop within the 5 s grace), but
the reason given for it in `expectations.md` is withdrawn.

## Decision

C0-C4 held on both Pythons and C7 held. As pre-registered in the run plan, that is the bar for publishing the package
as MV2's entry repository for the challenge's algorithm track: https://github.com/munimtechnologies/xltw-solver
(release v0.1.0, the files of this folder minus the job-only `fetch_helpers.py`; no vendored wheels). Before the
submission window opens on 2026-12-16 it still needs: a seed-deterministic stop (C5b), a decision on shipping the
wheels in the repository (the challenge build has no Internet), and a method note.

## Limits

Six short runs on small instances and one long run say nothing certain about 30-300 minute limits. Two Docker images
are not the organisers' machine. Solution quality is not tested here.
