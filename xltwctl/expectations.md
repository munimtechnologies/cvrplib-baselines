# xltwctl: expectations written before `xltwctl-v1` ran (2026-11-01 ~11:30 UTC)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.

**Why.** `xltwbase-study-v1` ([../xltwbase/score.md](../xltwbase/score.md)) found a 6.41% median distance reduction on
8 Gehring-Homberger 1,000-customer instances when the fleet search stops at a proven bound and `solve` gets the
leftover time. But it was compared with an earlier run on a shared machine that made 1.5 to 5.6 times fewer
iterations per second, so that figure mixes the budget change with machine speed. This control runs both budgets in
one job, interleaved, on the same machine, so the budget change can be measured alone.

**Method.** `xltwctl.py`, on the 8 E instances (R1_10_4, R1_10_6, R1_10_8, RC1_10_3, RC1_10_10, R2_10_4, RC2_10_9,
C1_10_4) and R1_10_1, in double precision (x1,000 rounded up, as before), PyVRP 0.14.1, seed 20261030, 600 s per run,
three runs at a time, one CPU each, both arms of an instance submitted one after the other:

- **split** (the `vrptwl/` protocol): the fleet loop stopped at PyVRP's own capacity bound KC, at most 300 s, then
  `solve` for exactly 300 s;
- **bound** (`xltwbase.py`): the same loop stopped at K = max(L2, time-window clique), then `solve` for whatever is
  left of the 600 s.

On the 8 E instances K equals KC, so both arms run the same fleet search and, with the same seed, the same `solve`
path; the bound arm simply runs it about twice as long. On R1_10_1 the split arm spends its whole 300 s trying 99
vehicles (ruled out by the bound in double precision); the bound arm stops at 100.

**Predictions** (scored by `score_k()` in `xltwctl.py`):

| | Prediction | Basis | Our odds |
|---|---|---|---|
| K0 | All 18 runs finish and are on time in exact arithmetic; none is below its bound; both arms use the same number of vehicles on all 9 instances. | Same loop, same seed; both earlier runs did this. | 85% |
| K1 | On all 8 E instances the bound arm's distance is no longer than the split arm's. | Same search path, run longer; the best solution can only improve. | 95% |
| K2 | The median E distance reduction (bound against split) is at least 1.0%. | Unknown: the cross-run 6.41% had 3 to 11 times the iterations, here it is about 2 times. | 50% |
| K3 | That median is less than half the cross-run figure, i.e. below 3.2%. | We expect most of the 6.41% to have come from machine speed. | 60% |
| K4 | On R1_10_1 the bound arm is at least 2.0% shorter than the split arm. | Its `solve` gets about 555 s instead of 300 s on a hard instance. | 60% |
| K5 | The median ratio of iterations per second (split / bound) on the E instances is between 0.8 and 1.25. | Same machine, interleaved; checks that the two arms really ran under the same conditions. | 75% |

**Limits stated in advance.** One seed, one CPU, 9 instances, one machine shared with other jobs. With one seed the
reduction on an instance is one draw, not an average. This measures an obvious engineering change, not a new method;
nothing here is a record. If K5 fails, K2 to K4 are reported but not interpreted.

## Addendum (2026-11-01 ~14:50 UTC, before `xltwctl-v2` ran): v1 was interrupted

`xltwctl-v1` ran on the Dell from 12:04 to 13:00 UTC and was stopped from outside after 56 minutes (exit 143, a
SIGTERM; its 120-minute limit was not reached, and its peak memory was 0.34 GB). By then both arms had finished and
been logged for 7 of the 9 instances (R1_10_4, R1_10_6, R1_10_8, RC1_10_3, RC1_10_10, R2_10_4, RC2_10_9), plus the
split arm of C1_10_4. No results.json was written, so those 7 pairs are taken from v1's log, copied verbatim into
`v1_log.txt`.

`xltwctl-v2` runs both arms of C1_10_4 and R1_10_1 (`--only C1_10_4,R1_10_1`), interleaved in one job as before, with
two runs at a time on two CPUs. `merge_ctl.py` drops every v1 record of those two instances, adds v2's runs and scores
K0 to K5 with the same unchanged `score_k()`. Each split/bound pair still comes from one job; different pairs may come
from different jobs.

**Disclosed:** this addendum was written after reading v1's 7 finished pairs. Their E reductions are 0.000, 0.417,
3.375, 3.505, 4.094, 4.405 and 5.853%, so whatever C1_10_4 gives, the E median of 8 lies between 3.44% and 3.80%:
K2 (at least 1.0%) will hold and K3 (below 3.2%) will not, unless C1_10_4's two arms use different numbers of
vehicles (then both are untestable). Their E speed ratios (split/bound) are 0.702 to 0.934, median 0.86, so K5 is
also nearly settled. K0, K1 (on C1_10_4) and K4 are still open. No prediction, threshold or odds was changed. Also, v1 asked
for 3 CPUs but its container got 2 while running 3 runs at a time, so its runs shared CPUs; both arms of each pair
shared them the same way.
