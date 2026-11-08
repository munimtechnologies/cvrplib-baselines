# xltwdet: scored (2026-11-08). The work budget makes the solver repeat itself, but the budget is too tight for a slowed machine

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Text CC BY 4.0.

Pre-registration: [expectations.md](expectations.md) (D0-D6, fixed on 2026-11-07 before any run), with
[addendum-2026-11-07.md](addendum-2026-11-07.md) (det2: unit-test-only safety override; the first job stopped in its
own end-to-end test before any study run). Raw outputs: [results.json](results.json), [results.md](results.md),
[logs/](logs/) (one stderr file per run, with the solver's stats line) and [sols/](sols/) (every counted solution).
Job `xltwdet-v2`, Blade, 2026-11-07 21:22-21:49 UTC (runner id f41ba19da2c2; the runner's log shows no pause during
it, and every run's harness poll gap stayed under 1 s). The verdicts below were computed by the job's own scorer
(`detrun.py` at commit b7b7755) and checked by hand against the table.

Before the study runs, the new end-to-end test passed: the PyVRP-only control (same data, seed 3, exactly 400
iterations, twice) gave identical results (`CONTROL {"a": [15163, 400], "b": [15163, 400]}`), and three detsolver runs
with no clock stop ended at the same solution. Every study run's stats line records safety 0.6.

## Verdicts

| | prediction (verbatim) | verdict |
|---|---|---|
| D0 | (gate) Offline build with the pinned wheels, network unreachable during the runs, and all 15 runs valid (not frozen, stopped by itself with exit 0, counted solution feasible in exact arithmetic, `Cost` line equal to its distance, nothing else on stdout). If D0 fails, D1-D6 are untestable. | **held**: all 15 valid on the first attempt |
| D1 | On each of the three instances, W1, W2 and W3 end at the identical solution (same routes in the same order, same cost: equal SHA-256). | **held**: fd076fda191b (n1048), 71c7bdf5b1af (n1094), 24e227d46898 (n1234) |
| D2 | None of the nine budget runs stops on the wall clock or on SIGTERM. | **did not hold**: C-W3 (n1234, under the CPU hog) reached the wall-clock safety net in its distance phase after 8,961 of 9,585 distance iterations |
| D3 | Each of the six budget runs without the hog (W1, W2) ends between 30% and 85% of the limit (36-102 s). | **held**: 51.4-101.4 s (C-W1 at 101.35 s, just inside) |
| D4 | On at least one of the three instances, T1 and T2 end at different solutions. | **held**: on all three |
| D5 | Together, the three W1 runs use at most one vehicle more than the three T1 runs. | **held**: 136 = 136 |
| D6 | Every run's peak memory is at most 0.6 GB, and the watchdog never fires. | **held**: 0.126-0.159 GB; watchdog never fired |

## Table

| instance | budget (it) | W1 s | W2 s | W3 s (hog) | it/s W1 / W2 / W3 | model it/s | W vehicles / distance | T1 distance | T2 distance (hog) |
|---|---|---|---|---|---|---|---|---|---|
| n1048 | 20,803 | 84.3 | 79.0 | 103.5 | 247 / 263 / 201 | 293 | 8 / 52,156 | 50,561 | 50,983 |
| n1094 | 20,361 | 69.6 | 51.4 | 67.5 | 292 / 396 / 302 | 287 | 93 / 81,456 | 78,960 | 79,467 |
| n1234 | 19,170 | 101.4 | 97.5 | 118.3 (clock) | 189 / 197 / 157 | 270 | 35 / 88,231 | 85,752 | 86,400 |

it/s = budget / elapsed (C-W3: the 18,546 iterations it did). The model rate is 300 x (n / 1000) ** -0.5, and the
budget is 0.6 x model x (limit - margin). Limit 120 s for every run; the wall-clock runs T1 and T2 used it all.

## What it means

- **Determinism, yes.** Stopping on an iteration count fixed from n and the limit made the solver end at the same
  solution three times out of three on each instance, including under a CPU hog, while the wall-clock solver ended
  at a different solution on every instance when the hog ran. The challenge requires each run to be "deterministic for
  a given seed", and this is how the solver can meet it.
- **But the budget is too tight for slow machines at n = 1,234.** There the solver did only 0.70-0.73 of the model's
  rate alone and 0.58 of it under the hog. The safety factor 0.6 therefore left 15% of the limit unused when alone and
  was not enough under the hog. C-W3 still ended at the same solution as W1 and W2, because the distance search had
  found its final solution before iteration 8,961; that is luck, not the rule working. The other two instances ran at
  0.69-1.38 of the model.
- **Why n = 1,234 is slow:** its fleet phase is the expensive part. 20 fleet solves used 9,585 iterations in
  65-83 s (116-147 it/s), while the distance phase did its 9,585 iterations in 25-32 s alone (297-386 it/s). A single rate per instance size cannot describe both phases. The next budget should count the two phases
  separately or be measured on the target machine.
- **What the budget costs:** the same vehicles (136 = 136) and 2.9-3.2% more distance than the wall-clock T1 runs on
  all three instances, because the budget runs without the hog stopped after 43-84% of the limit and their distance
  phase got fewer iterations (9,585-10,402 against 23,625-29,977 for T1).

## What next

Pre-registered rule from expectations.md: the budget formula is not adjusted here. A recalibration goes into a new
pre-registered study: per-phase rates fitted on these logs and on `xltwrun/` (n = 1,047-10,000), checked at the
challenge's full limits, with a cap for small n (addendum). The determinism mode is not yet the default in
xltw-solver.

Limits: one seed, three instances, a 120 s limit (not T(n)), one machine image. Identical results on other CPUs are
expected but not tested.
