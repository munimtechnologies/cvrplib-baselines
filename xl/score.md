# Scoring of X1-X4 (xltw-scale-v1)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Scored 2026-10-29 from
`results.json` in this folder, against `expectations.md` (written before the job ran).

The job ran on 2026-10-29 from 14:06 to 15:09 UTC on one CPU with a 3 GB limit, PyVRP 0.14.1. Locations
and demands are the first n customers of XL-n10001-k1570 (CVRPLib id 379); the time windows are
**synthetic**, so route counts and costs say nothing about XLTW difficulty. Only memory and speed carry over.

| | expectation | outcome | verdict |
|---|---|---|---|
| X1 | at n = 10,000: build peak 1,500-2,600 MB, peak after solve below 3,000 MB | 2,361 MB and 2,361 MB | **holds** |
| X2 | n = 1,000 and 2,500 end feasible, checked, PyVRP = checker | both feasible (161 and 402 routes), both checks pass and match | **holds** |
| X3 | n = 10,000 ends feasible within 1,800 s | feasible, 1,600 routes (lower bound 1,570), loop stopped at 1,800.1 s | **holds** |
| X4 | iterations/s at 10,000 is at least 10% of that at 1,000 | 44.1 vs 336.7 per second = 13.1% | **holds** |

Hygiene: the unit tests passed, and PyVRP's distance equals the independent checker's at every size.

| n | budget | build peak MB | iterations/s | routes | route lower bound |
|---|---|---|---|---|---|
| 1,000 | 300 s | 69 | 336.7 | 161 | 159 |
| 2,500 | 600 s | 190 | 185.1 | 402 | 395 |
| 5,000 | 900 s | 621 | 99.6 | 799 | 785 |
| 10,000 | 1,800 s | 2,361 | 44.1 | 1,600 | 1,570 |

What follows: memory is dominated by one dense int64 matrix copied once (763 MiB per copy at 10,001
nodes), so a 10,000-customer XLTW job asks 3 GB and jobs up to 2,500 customers ask 1 GB. Speed falls
roughly in proportion to n, so 30 minutes at 10,000 customers is about 80,000 iterations: enough to stay
feasible, not enough to compete. Matching vehicle counts at that size will need longer runs, several
seeds in parallel, or a decomposition method.
