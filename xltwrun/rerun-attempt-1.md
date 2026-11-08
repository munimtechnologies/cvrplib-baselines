# xltwrun: re-run attempt 1 (job xltwrerun-v1): pause audit; attempt 2 is job xltwrerun-v2

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. CC BY 4.0.

Rule: [rerun-2026-11-08.md](rerun-2026-11-08.md), fixed before attempt 1 ran. Raw output of attempt 1:
[rerun-v1/](rerun-v1/) (per-instance `results-r*.json/.md`, `progress-r*.jsonl`, solver stderr and `.sol` files).

## Pause audit (method of [pause-audit.md](pause-audit.md))

Job `xltwrerun-v1` ran on the Blade on 2026-11-08, one instance per run step. Each step's start and end come from
the runner's `run.exits` (Unix seconds). Pauses come from the runner's log for container `c2305d2cde35`: four
pauses, each started because the host's Windows memory was low (0.53-0.99 GB free).

| part | step window (UTC) | pause(s) inside | clean | vehicles (attempt 1) | earlier counted run (merge v1) |
|---|---|---|---|---|---|
| r7037 | 18:17:27-18:24:32 | none (first pause 18:25:24) | **yes** | 645 | 647 |
| r8389 | 18:24:32-18:34:05 | 18:25:24-18:34:03 | no | (534, SIGTERM) | 404 |
| r8575 | 18:34:05-18:42:45 | 18:37:35-18:38:59 | no | (105) | 156 |
| r9160 | 18:42:45-18:51:57 | 18:47:05-18:48:47 | no | (365) | 394 |
| r9363 | 18:51:57-19:01:22 | 18:57:36-18:58:59 | no | (463) | 484 |
| r9571 | 19:01:22-19:10:58 | none | **yes** | 309 | 315 |
| r10001 | 19:10:58-19:21:02 | none | **yes** | 267 | 281 |

Numbers in brackets are from runs that are **not clean** and do not count. They are published only so nothing is
hidden. (r8389 shows what a pause does to this harness: the pause began about 50 s into the run, the solver printed
its last solution at 31 s, and SIGTERM came at 568 s against a 503 s limit.)

## What happens next (as the rule says)

- **Clean, attempt 1:** n7037, n9571, n10001. Their re-runs replace the old results in the second merge.
- **Attempt 2:** n8389, n8575, n9160, n9363 run again, unchanged (same commit `ba1eec8`, seed 20261104, T(n)/30,
  `--workers 1`, 1 CPU, 5 GB), in job **`xltwrerun-v2`**. Any of them still not clean gets attempt 3 (job
  `xltwrerun-v3`), the last.
- The second scoring of G0-G5 runs only after every instance is clean or has used its 3 attempts. G0-G5 are not
  scored from attempt 1 alone.

Note: the job's own unit-test step printed a G0-G5 line, and each part printed "untestable". Neither is a score;
those lines come from the harness's fixtures and single-instance parts.
