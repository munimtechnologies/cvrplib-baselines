# xltwrs: expectations, written before the run

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Fixed on 2026-11-02 (UTC) before `xltwrs.py` was run on any instance. The git commit that adds this file dates it.

## Why

CVRPLib's VRPTW BKS Challenge ranks by vehicles first. [`xltwrm/`](../xltwrm/score.md) tested two alternatives to
PyVRP 0.14.1's `minimise_fleet` loop on the 13 Gehring-Homberger 1,000-customer instances where `vrptwl/` used more
vehicles than SINTEF's records, and both lost on every instance. The plain loop (one vehicle fewer, solve from a
random start until the first feasible solution, repeat) stays. Two questions are left that the same instances can
answer:

1. The loop was still finding a vehicle every 72 to 95 s near the end of its 300 s on three C1 instances. The
   challenge's rules (published 2026-11-02) give 1,800 s per 1,000 customers for fleet and distance together. How
   much does the loop gain with a 900 s fleet budget, half of that?
2. The loop spends all remaining time on the first fleet size it cannot reach (for example 270 s on one failed
   attempt at 29 vehicles on C2_10_6). Is it better to cap each attempt and retry with a new seed?

## What runs

`xltwrs.py`, in one job, on the same 13 instances, 4 CPUs (one per run), double precision (PyVRP sees every number
x1,000 rounded up, as in `vrptwl/`), seed 20261102 (the seed of `xltwrm/`), a **900 s** fleet budget per run, both arms
stopped at K = max(L2, time-window clique) from `xltwlb.py`. The two arms of an instance are queued next to each other.

- **fleet** (reference): `xltwrm.arm_fleet`, unchanged (imported from commit `09058b4`).
- **restart**: the same loop, but each attempt is capped at max(30 s, 2 x the time the last successful attempt took)
  and a failed attempt is retried at the same fleet size with the next seed, until the budget is spent. The first
  attempt has the same seed as the reference.

Each run logs a trace (time, vehicles) at every success, so the vehicles held at 300 s and 600 s are read from the
same run. Every result is re-checked in 50-digit decimals by `xltwbase.check_exact`.

**Prior art.** Restarting a search whose run time is heavy-tailed is an old idea (Gomes, Selman and Kautz, AAAI 1998).
Nothing here is a new method; it is a calibration of the challenge baseline's fleet phase.

## Predictions (each scored on its own; none depends on another)

R1, R3 and R4 are "untestable" if fewer than 10 instances can be compared; R2 is "untestable" unless all 13 fleet
runs return an on-time result.

| | Prediction | Our odds |
|---|---|---|
| R0 | All 26 runs finish without error, every result is on time in exact arithmetic, and none uses fewer vehicles than K. | 90% |
| R1 | The fleet arm holds fewer vehicles at 900 s than at 300 s (same run) on at least 4 of 13 instances. | 55% |
| R2 | The fleet arm's total over SINTEF's records at 900 s is at most 10 vehicles (`xltwrm/`'s 300 s run: 15). | 40% |
| R3 | restart uses no more vehicles than fleet on at least 11 of 13 instances. | 60% |
| R4 | restart uses fewer vehicles than fleet on at least 3 of 13 instances. | 35% |
| R5 | No run uses fewer vehicles than SINTEF's record. A result below a record would be checked a second way before anything is said about it. | 95% |

Why these numbers: at 300 s the loop was still descending on C1_10_2, C1_10_8 and C1_10_9 and had last improved at
214 s on RC2_10_2; the C2 instances stopped improving after 22 to 34 s, and RC1_10_1 and RC2_10_5 had already reached
K. A cap helps only if a fresh start finds a solution sooner than continuing does, which we do not know for PyVRP at
1,000 customers. PyVRP's penalties also grow towards their cap during a long failed attempt (the `xltwrm/` log shows
`PenaltyBoundWarning`), and a restart resets them, which may help. These are guesses; the score will say where they
were wrong.

**Reported, not predicted:** both arms at 300 s and 600 s; restart's number of attempts and failed attempts; whether the
fleet arm's trace up to 300 s repeats `xltwrm/`'s fleet trace (same code and seed; only the machine's speed differs).

## Limits

One seed per arm and instance on a shared machine. 13 instances chosen because the reference did badly on them in
`vrptwl/`. Double precision, not the challenge's own nearest-integer convention, because SINTEF's records are kept in
double precision. The cap rule (30 s, factor 2) was chosen without tuning. Distances are reported but not compared: no
arm has a distance phase.
