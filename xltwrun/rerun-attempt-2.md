# xltwrun: re-run attempt 2 (job xltwrerun-v2): pause audit; all four clean

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. CC BY 4.0.

Rule: [rerun-2026-11-08.md](rerun-2026-11-08.md), fixed before attempt 1 ran. Attempt 1: [rerun-attempt-1.md](rerun-attempt-1.md).
Raw output of attempt 2: [rerun-v2/](rerun-v2/) (per-instance `results-r*.json/.md`, `progress-r*.jsonl`, solver
stderr and `.sol` files).

## Pause audit (method of [pause-audit.md](pause-audit.md))

Job `xltwrerun-v2` (runner id `894e644efc59`) ran on the Blade on 2026-11-09: setup started 10:40:04 UTC, run
steps 10:41:53-11:17:45 UTC, one instance per run step, same commit `ba1eec8`, seed 20261104, T(n)/30,
`--workers 1`, 1 CPU, 5 GB. Step windows come from the runner's `run.exits` (Unix seconds). The runner log has
**no** pause or resume line for `894e644efc59`, and no pause or resume line for any container between 10:00 and
11:53 UTC on that day (the first one after the job is 11:53:29, for a different job, 36 minutes after it ended).
The unit-test step passed (exit 0).

| part | step window (UTC) | pause(s) inside | harness valid | SIGTERM | clean | vehicles (attempt 2) | counted in merge v1 |
|---|---|---|---|---|---|---|---|
| r8389 | 10:42:05-10:50:30 | none | yes | no | **yes** | 393 | 404 |
| r8575 | 10:50:30-10:59:08 | none | yes | no | **yes** | 103 | 156 (SIGTERM) |
| r9160 | 10:59:08-11:08:20 | none | yes | no | **yes** | 365 | 394 (SIGTERM) |
| r9363 | 11:08:20-11:17:45 | none | yes | no | **yes** | 458 | 484 |

"Harness valid" = `exact_ok`, `cost_line_ok`, no other stdout lines, no SIGTERM or SIGKILL, in each
`results-r*.json`. Each solver printed its last solution 2.2-2.3 s before its limit.

## All seven paused instances now have a clean re-run

| instance | clean attempt | vehicles (clean re-run) | counted in merge v1 | change |
|---|---|---|---|---|
| n7037 | 1 | 645 | 647 | -2 |
| n8389 | 2 | 393 | 404 | -11 |
| n8575 | 2 | 103 | 156 | -53 |
| n9160 | 2 | 365 | 394 | -29 |
| n9363 | 2 | 458 | 484 | -26 |
| n9571 | 1 | 309 | 315 | -6 |
| n10001 | 1 | 267 | 281 | -14 |
| total | | 2,540 | 2,681 | -141 |

No attempt 3 is needed. Every clean re-run used fewer vehicles than the paused run it replaces, which is what a
pause that steals CPU time from a time-limited search should do; it is one seed per instance, so the size of each
change also includes ordinary run-to-run variation.

## What happens next (as the rule says)

The second scoring runs the same pinned `xltwrun.py --merge` (commit `ba1eec8`) on the xltwmerge-v1 parts with the
seven clean re-runs in place of the old records, in job **`xltwmerge2-v1`** (code: [../xltwmerge2/](../xltwmerge2/);
`swap.py` refuses to run if a re-run is invalid or does not replace exactly one old record). The first scoring
([score.md](score.md)) stays as published; both are shown side by side when the second one is done, and G0-G5 are
not reworded.

What the rule file expected before attempt 1: G0 and G1 hold, G2, G4 and G5 still fail, G3 still holds. From the
numbers above (not yet the merge output): the fleet total should drop from 18,529 to 18,388 against the same lower
bounds (K total 11,298); none of the seven reached its bound, so the count of runs at K stays 6.
