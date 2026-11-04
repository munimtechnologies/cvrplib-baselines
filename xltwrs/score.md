# xltwrs: scored

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0.
Scored on 2026-11-04 (UTC) from the job `xltwrs-v1` (2026-11-02 19:34 to 21:08 UTC, 4 CPUs, one per run, peak
0.46 GB), against [expectations.md](expectations.md), committed before the run. The verdicts are the ones the code
computed.

## Verdicts

| | Prediction | Odds | Verdict |
|---|---|---|---|
| R0 | All 26 runs finish without error, every result on time in exact arithmetic, none below K | 90% | **held** |
| R1 | The fleet arm holds fewer vehicles at 900 s than at 300 s on at least 4 of 13 | 55% | **held**: 5 of 13 (C1_10_2 93 to 91, C1_10_7 100 to 99, C1_10_9 91 to 90, C2_10_6 30 to 29, C2_10_8 29 to 28) |
| R2 | The fleet arm is at most 10 vehicles over SINTEF's records in total at 900 s | 40% | **held**: 737 against 728, 9 over |
| R3 | restart uses no more vehicles than fleet on at least 11 of 13 | 60% | **did not hold**: 8 of 13 |
| R4 | restart uses fewer vehicles than fleet on at least 3 of 13 | 35% | **did not hold**: none |
| R5 | No run below SINTEF's record | 95% | **held** |

## What it says

**A longer fleet budget helps a little; capping and restarting attempts does not.**

| | 300 s | 600 s | 900 s |
|---|---|---|---|
| fleet arm, vehicles on the 13 instances (SINTEF: 728) | 743 | 739 | 737 |
| restart arm | 746 | 743 | 742 |

- The plain loop kept finding vehicles after 300 s: 4 between 300 s and 600 s and 2 more by 900 s. Its last
  improvements came at 564.9 s (C2_10_8), 586.4 s (C2_10_6), 643.1 s (C1_10_2) and 758.5 s (C1_10_7). The
  challenge's time limit is 1,800 s per 1,000 customers, so a fleet phase of half of it is not wasted.
- restart never used fewer vehicles than the plain loop and used one more on 5 instances (C1_10_7, C1_10_9, C2_10_6,
  C2_10_8, RC1_10_1). Where the plain loop's late gains came from a single long attempt (C1_10_7 found 99 vehicles
  after 758 s), the cap cut that attempt off and the restarts at the same size kept failing: on the C2 instances 28
  of about 44 attempts failed. At 1,000 customers the time to the first feasible solution at the next smaller fleet
  is not heavy-tailed in a way a 30 s cap can use.
- **The fleet arm's first 300 s repeat `xltwrm/`:** same code and seed, total 743 at 300 s in both jobs.

`xltwbase.py` keeps the plain loop. The next fleet idea worth testing is a different one (penalised infeasible
insertion, the "squeeze" of Nagata and Bräysy, 2009), after a prior-art check.

## Limits

One seed per arm and instance on a shared machine; 13 instances chosen because the baseline did badly on them;
double precision, not the challenge's nearest-integer convention. The cap rule (30 s, factor 2) was not tuned; a
different cap could behave differently. Restarting heavy-tailed searches is an old idea (Gomes, Selman and Kautz,
1998); nothing here is a new method.

Raw output: [results.md](results.md), [results.json](results.json), [progress.jsonl](progress.jsonl) (every run's
trace); solutions in [sols/](sols/) (CVRPLib format, `Cost` = double-precision distance). None is a record.
