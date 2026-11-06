# xltwfull part a: raw results (not scored yet)

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Text CC BY 4.0.

The job `xltwfull-a-v1` ran F1 and F3 of [expectations.md](expectations.md) on 2026-11-06 (16:34 to 18:26 UTC,
1 CPU, peak 0.28 GB for the whole job). F0-F5 are scored only by the merge, once part b (F2, F4) has run; nothing
here is a verdict. Raw output: [results-a.json](results-a.json), [results-a.md](results-a.md),
[logs-a/](logs-a/), and the counted solutions in [sols/](sols/).

| run | instance | limit s | vehicles | part a of xltwrun (T/30) | K* | distance | fleet solves | stopped by itself, slack | peak GB |
|---|---|---|---|---|---|---|---|---|---|
| F1 | XLTW-Test-n1234 | 2,219.4 | 34 | 35 | 27 | 83,690 | 21 | yes, 5.9 s | 0.164 |
| F3 | XLTW-Test-n1608 | 2,892.6 | 108 | 113 | 81 | 112,655 | 15 | yes, 57.0 s | 0.240 |

Both runs: offline build with the pinned wheels (Python 3.12.15), network unreachable during the runs, exit code 0,
no frozen harness (largest poll gap 0.063 s), no watchdog, no stray stdout line, and the counted solution is
feasible in exact nearest-integer arithmetic with a `Cost` line equal to its distance.

## What the printed solutions show

The solver prints every better solution, at most once per 1% of the limit, so the times below are when a count was
printed; a count found between prints shows up at the next print.

- **F1 (n1234) stalled early.** 64 vehicles at 1.4 s, 35 at 29.1 s, 34 at 86.4 s. The fleet phase (half of the
  time) ended at about 1,107 s, so its last attempt, at 33 vehicles, ran for about 1,020 s, 46% of the limit, and
  never found a feasible solution. The distance phase then took 34 vehicles from 91,405 to 83,690; by 1,494 s it was
  at 83,851, so its last 720 s gained 0.2%.
- **F3 (n1608) was still improving when its half ran out.** 124 vehicles at 1.4 s, 113 at 49.5 s, then 111 at
  151 s, 110 at 303 s, 109 at 586 s and 108 at 1,124 s: each step took about twice as long as the one before. The
  attempt at 107 was cut at about 1,443 s. The distance phase went from 113,877 to 112,655 and was at 112,900 by
  2,030 s (0.2% above its final value).

So at the full limit the two halves are not equally useful: the distance phase gains little in its second half,
while the fleet phase either sits in one long failed attempt (F1) or is cut off while still finding vehicles
(F3). Since the challenge ranks vehicles first, the next study, [xltwff](../xltwff/expectations.md), gives the
fleet phase 0.8 of the time, with predictions fixed before it runs.

Limits: one seed, two instances, one machine; the gap to K* (27 and 81) is to a lower bound, not to a known
optimum. Distances of runs with different vehicle counts are not comparable.
