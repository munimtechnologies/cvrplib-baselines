# xltwrun: part a done (80 of 100 instances), not scored yet

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0.
Written on 2026-11-05 (UTC), after part a and **before part b ran**. G0 to G5 in [expectations.md](expectations.md) are
scored only on all 100 runs together, so nothing below is a verdict. Raw output: [results-a.md](results-a.md),
[results-a.json](results-a.json), [progress-a.jsonl](progress-a.jsonl); solutions in [sols/](sols/) (CVRPLib format,
customers 1..n, `Cost` = nearest-integer distance).

## What ran

Job `xltwrun-a-v1`, 2026-11-04: the pre-registered code (commit ba1eec8), its unit tests first (passed), then
`xltwrun.py --scale 30 --workers 4 --mem-gb 3.3 --max-n 6500 --part a` on the 80 XLTW-Test instances with up to 6,444
customers. Seed 20261104, limits T(n)/30 (62.8 s to 386.6 s), up to four single-threaded solver processes at a time
(mostly two, because of the memory budget), 4,480 s in all.

## What part a shows

| | part a (80 runs) |
|---|---|
| runs with a counted solution (last one before the limit, on time in exact arithmetic) | **80 of 80** |
| `Cost` line equal to the routes' cost; other lines on stdout | 80 of 80; none |
| SIGTERM needed (the solver did not stop by itself); SIGKILL needed | none; none |
| solutions below the fleet bound K | none |
| runs ending at K | **6 of 80**: 0 of the 27 with KC = 1, 6 of the 53 others |
| vehicles against K, all 80 | 11,963 against 7,421 |
| median (vehicles - K) / K | **47.4%** (all 80); 30.0% on the 53 with KC > 1 |
| KC = 1 instances, vehicles / K | median 6.1; from 1.20 (n3007, 190 against 158) to 84 (n3147, 84 against 1) |
| solver's own bound cut short (10% of the limit) | 3 (n3194, n3640, n5526) |
| peak memory above the planning estimate `mem_est` | 47 of 80; largest 2.117 GB at 6,444 customers (estimate 1.81) |

The two medians by group and the vehicles/K ratios were worked out by hand from [results-a.md](results-a.md); the other
rows are the harness's own tally (`tally_this_part` in results-a.json).

Reading it plainly:

- **The protocol side works.** Every run printed valid solutions, stopped on its own before the limit, and its last
  solution counted. That is what G0 and G1 are about.
- **The vehicle counts are far from the bound.** At 60 s per 1,000 customers the baseline ends at K on 6 of 80
  instances. On the 27 instances where capacity never binds, K is the time-window clique bound, which ignores route
  length, so these gaps say as much about the bound as about the solver. Where capacity binds, the median gap is still
  30%, much more than on the 1,000-customer Gehring-Homberger instances (`vrptwl/`, where the fleet search reached
  the capacity bound on 41 of 60, mostly within about 12 s). Either XLTW-Test is much harder for this fleet search, or
  1/30 of the limit is far too short, or both; part a cannot separate the two.
- **Memory:** peaks fit 0.17 GB + 4.7 GB x (n / 10,000)^2 closely from 3,000 customers up, about 17% above `mem_est`
  at the largest sizes. This is how part b is sized (below).

## Already decided by part a, whatever part b does

- **G5** (every peak at or below `mem_est`) cannot hold: 47 runs are already above it.
- **G4** (median gap at most 10%) cannot hold: only 17 of the 80 part-a runs are within 10% of K, so even if all 20
  part-b runs were, 37 of 100 would be, fewer than half.
- **G2** (20 to 55 runs at K) can hold only if all 14 part-b instances with KC > 1 end at K.

They will still be scored formally, with the others, by `xltwrun.py --merge` once part b is done.

## Part b: how it runs (decided now, before it runs)

The expectations say part b runs "in a later job sized from part a's measured memory". From part a, the largest
part-b instance (10,000 customers) should peak near 4.9 GB, so two at a time would not fit the 6 GB a job can get.
Part b is therefore split into three jobs, each running **one solver at a time** (`--workers 1`), with the same code
(downloaded from commit ba1eec8), the same scale (30) and the same seed:

| job | part name | customers | instances | memory asked |
|---|---|---|---|---|
| xltwrun-b1-v1 | b1 | 6,587 to 7,682 | 8 | 3.5 GB |
| xltwrun-b2-v1 | b2 | 7,853 to 8,765 | 6 | 4.5 GB |
| xltwrun-b3-v1 | b3 | 8,959 to 10,000 | 6 | 6 GB |

The difference from part a: part-b solvers run one per job instead of up to four per job (the three jobs may still
share the machine with each other and with other work). With wall-clock limits, less sharing should mean equal or more
iterations, so if it changes anything it should favour part b slightly; the merged score will say so. The merged score will be
`xltwrun.py --merge results-a.json,results-b1.json,results-b2.json,results-b3.json`.
