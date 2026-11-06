# xltwrun part b3 (the six largest XLTW-Test instances): raw results, two frozen runs, one more stuck call

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. CC BY 4.0.
Written 2026-11-06 ~13:30 UTC. Raw outputs: `results-b3.*`, `progress-b3.jsonl`, `logs-b3/`, and the counted
solutions in `sols/` (every one exact-checked). Pre-registration: `expectations.md` (G0-G5, scored only on all
100 instances, after the re-runs). Earlier parts: `part-a.md`, `part-b-note.md`.

Job `xltwrun-b3-v1` ran the pinned baseline (`solver.py` at ba1eec8, PyVRP 0.14.1) one instance at a time at
T(n)/30, seed 20261104, from 04:47 to 06:43 UTC on 2026-11-06.

## Two runs frozen by the host (re-run under the published rule)

| instance | limit s | SIGTERM sent at s | vehicles | K |
|---|---|---|---|---|
| XLTW-Test-n9160 | 549.5 | 761.8 | 401 | 244 |
| XLTW-Test-n9571 | 574.2 | 3667.4 | 352 | 181 |

As with the five in `part-b-note.md`, the container was paused and the harness with it, so SIGTERM came long after
the limit and SIGKILL 0.2 s later. By the rule in that note, both are invalid and are re-run once, unchanged (job
`xltwrun-b3r-v1`). Added before any re-run result is known: a re-run that is itself frozen is not re-run again; that
instance is reported as having no valid run.

## A second real failure: XLTW-Test-n10001 did not stop

On n10001 (10,000 customers, capacity-bound, KC = K = 260) the harness was on time: SIGTERM at 600.09 s for a 600 s
limit. The solver had printed its last solution (281 vehicles, distance 505,302) at 592.95 s. It did not stop at
its own stopping point (597.3 s), did not react to SIGTERM within 5 s, and was SIGKILLed at 605.1 s. Its stderr has
only the bound line, because the statistics line is written at the end. The counted solution is valid, but this is
a second break of pre-registered G0 ("no SIGKILL"), which already failed on n8575.

It differs from n8575. That instance was capacity-free and its last solution came at 64.5 s, so one call ran for
more than 450 s. Here the solver was still printing solutions 7 s before the limit. It ran at least 7.8 s past
its own stopping point, near the end of the distance phase on the largest instance, before it was killed. We cannot
tell how much longer it would have run. Both are what the packaged solver's watchdog (`xltwpkg/`) is for: it ends the process at a hard deadline
before the limit, even inside a long C++ call.

## The valid runs

| instance | n | KC | K | K* (`xltwen/`) | vehicles | distance | vehicles / K* |
|---|---|---|---|---|---|---|---|
| XLTW-Test-n8960 | 8959 | 1 | 5 | 154 | 265 | 370881 | 1.72 |
| XLTW-Test-n9363 | 9362 | 209 | 253 | 253 | 484 | 513639 | 1.91 |
| XLTW-Test-n9784 | 9783 | 1 | 8 | 388 | 522 | 858289 | 1.35 |
| XLTW-Test-n10001 | 10000 | 260 | 260 | 260 | 281 | 505302 | 1.08 (SIGKILLed, see above) |

None reached its bound. Peak memory per solver process: 3.73-4.62 GB.
