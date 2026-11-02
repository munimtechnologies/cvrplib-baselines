# xltwctl: scoring of the same-machine control (v1 interrupted, completed by v2)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.

Predictions: [expectations.md](expectations.md), written and published before `xltwctl-v1` ran, with an addendum
written before `xltwctl-v2` ran. Merged table: [merged.md](merged.md), [merged.json](merged.json). v2's own output:
[results-v2.md](results-v2.md), [results-v2.json](results-v2.json). v1's log: [v1_log.txt](v1_log.txt). Solutions:
[sols/](sols/) (CVRPLib format, `Cost` = double-precision distance). Written 2026-11-02 ~04:30 UTC.

## What ran

- **`xltwctl-v1`** (2026-11-01, 12:04 to 13:00 UTC): stopped from outside after 56 minutes (exit 143, SIGTERM; its
  120-minute limit was not reached; peak memory 0.34 GB). Both arms had finished and been logged on 7 of the 9
  instances. It asked for 3 CPUs, got 2, and ran 3 runs at a time, so its runs shared CPUs; both arms of each pair
  shared them the same way.
- **`xltwctl-v2`** (2026-11-01, 19:27 to 19:49 UTC, a different machine): both arms of C1_10_4 and R1_10_1, two runs
  at a time on two CPUs, same code, seed and 600 s budget. Tests passed first. Peak memory 0.22 GB.
- **`merge_ctl.py`** (in the v2 job) took v1's 7 finished pairs from its log, dropped v1's lone C1_10_4 split run,
  added v2's 4 runs and scored K0 to K5 once with the unchanged `score_k()`. Each split/bound pair comes from one job;
  different pairs come from different jobs and machines, which is why the pairs, not the jobs, are compared.

## Verdicts

Every number below was re-checked by hand from the two logs.

| | Prediction | Result | Verdict |
|---|---|---|---|
| K0 | All 18 runs finish, on time in exact arithmetic, none below its bound, same vehicles in both arms on all 9 | 18 of 18; all `exact_ok`; vehicles equal in all 9 pairs (91, 91, 91, 90, 90, 19, 18, 90; R1_10_1 100) | **held** |
| K1 | Bound arm no longer than split on all 8 E instances | 8 of 8 (R2_10_4 equal) | **held** |
| K2 | Median E reduction at least 1.0% | 3.44% | **held** |
| K3 | That median below 3.2% (less than half the cross-run 6.41%) | 3.44% | **did not hold** |
| K4 | R1_10_1: bound arm at least 2.0% shorter | 1.35% (55,077.80 to 54,334.58) | **did not hold** |
| K5 | Median E speed ratio (split/bound iterations per second) between 0.8 and 1.25 | 0.859 | **held** |

Four of six held. **Disclosed:** K2, K3 and K5 were nearly settled by v1's 7 pairs before v2 ran, as the addendum says;
only K0, K1 (on C1_10_4) and K4 were still open. No prediction, threshold or odds was changed.

## Per pair

| instance | job | vehicles | split | bound | reduction |
|---|---|---|---|---|---|
| R1_10_4 | v1 | 91 | 46,542.62 | 44,492.51 | 4.405% |
| R1_10_6 | v1 | 91 | 59,175.64 | 55,711.88 | 5.853% |
| R1_10_8 | v1 | 91 | 46,032.37 | 44,418.80 | 3.505% |
| RC1_10_3 | v1 | 90 | 45,685.48 | 44,143.77 | 3.375% |
| RC1_10_10 | v1 | 90 | 49,147.01 | 47,134.95 | 4.094% |
| R2_10_4 | v1 | 19 | 18,299.05 | 18,299.05 | 0.000% |
| RC2_10_9 | v1 | 18 | 23,932.43 | 23,832.66 | 0.417% |
| C1_10_4 | v2 | 90 | 39,590.96 | 39,585.73 | 0.013% |
| R1_10_1 (T) | v2 | 100 | 55,077.80 | 54,334.58 | 1.349% |

## What it shows

- **The budget change alone is worth about half of the confounded figure.** On the same machine, in the same job,
  giving `solve` the time the fleet phase did not use shortened the 8 E instances by a median of **3.44%**, against
  6.41% in `xltwbase/`, where a faster machine also contributed. So roughly 54% of the earlier figure is the budget
  change and the rest is machine speed. This is the figure to quote for the budget change.
- **The gain is all in the tight-window families.** R1 and RC1 (5 instances) gained 3.4% to 5.9%; R2, RC2 and the
  clustered C1_10_4 gained 0% to 0.42%. The tight-window results were far from converged after 300 s (in `vrptwl/`
  their median distances were 22% (R1) and 13% (RC1) above SINTEF's records), so twice the time helps; the others had little left to find in 600 s.
- **R1_10_1 gained less than predicted.** Stopping the fleet search at the double-precision bound (100) saved 243 s
  (57.5 s instead of 300.7 s), but the extra `solve` time shortened the route set by only 1.35%. Our 60% odds on a
  2% gain were too high. Both arms reached 100 vehicles: the split arm's 300 s spent trying 99 found nothing, as the
  bound says it cannot.
- **Iterations per second rise during a run.** In all 9 pairs the longer (bound) arm made more iterations per second
  than the split arm (ratio 0.70 to 0.93), on both machines. K5's band allowed for this, so it held, but the direction
  was the same every time. We did not predict this and do not explain it here.
- **Same seed, more iterations, different answer.** v1's C1_10_4 split run (shared CPUs, 57,006 iterations) ended at
  39,699.48; v2's (117,966 iterations) at 39,590.96. With a wall-clock budget the result depends on machine load, as
  stated in the limits.
- **A reproduction.** v2's R1_10_1 bound arm ended at exactly 54,334.58, the same value as `xltwbase/`'s run of the
  same arm on 2026-11-01 (about 181,000 and 183,000 iterations).

## Consequences

- `xltwbase.py` stays the baseline for XLTW-Test: on the same machine it is never worse here and it is 3.4% to 5.9%
  shorter on tight-window instances.
- K4 failed, so we will **not** propose an optional lower bound for PyVRP's `minimise_fleet` upstream on the strength
  of this run: the saving on R1_10_1 is time in the fleet phase, and its effect on distance was small here.

## Limits

One seed, one CPU per run, 9 instances, two machines shared with other jobs (pairs never span machines). With one
seed the reduction on an instance is one draw. This measures an obvious engineering change, not a new method. None
of these results is a record, and none is compared with SINTEF's records here.
