# xltwfull: scored (2026-11-06) - the gate failed, so F1-F5 are untestable

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Text CC BY 4.0.

Pre-registration: [expectations.md](expectations.md) (F0-F5, fixed before any run). Raw outputs:
[results-a.json](results-a.json) / [part-a.md](part-a.md) (F1, F3; job `xltwfull-a-v1`, Dell, no pauses) and
[results-b.json](results-b.json) / [results-b.md](results-b.md) / [logs-b/](logs-b/) (F2, F4; job `xltwfull-b-v1`,
Blade, 18:31-21:49 UTC). The merged scoring is mechanical (`fullrun.py --merge`, commit 876bd94); it is written out
here by hand from those two files and will be reproduced by the merge job.

## Verdicts

| | prediction (verbatim) | verdict |
|---|---|---|
| F0 | (gate) The build is offline with the pinned wheels, the network is unreachable during the runs, and each of F1-F4 has a valid run: not frozen, stopped by itself with exit code 0, and its counted solution is feasible in exact arithmetic, with a `Cost` line equal to its distance and no other line on stdout. If F0 fails, F1-F5 are untestable. | **did not hold**: F2 has no valid run |
| F1 | On every one of the four, the full-limit run uses at most as many vehicles as part a did (35, 72, 113, 29). | untestable |
| F2 | The four together use at most 224 vehicles: at least 10% fewer than part a's 249. | untestable |
| F3 | The four together use at least 208 vehicles: still at least 20% above their total K* of 173. | untestable |
| F4 | At most one of the four ends at its K*. | untestable |
| F5 | Every run's peak memory is at most 0.6 GB, and the watchdog never fires (the solver stops by itself). | untestable |

**Why F2 has no valid run.** The job runner paused the `xltwfull-b-v1` container three times when the Blade ran
short of memory (18:36:40-18:45:37, 19:51:15-19:59:25 and 20:01:35-20:03:00 UTC, from the runner's log). The
harness saw each pause as a gap between its polls (536 s, 489 s, 84.6 s). F2's first try was frozen for 536 s; its
one pre-registered re-run was frozen for 489 s. The limit passed during that pause, so the harness sent SIGTERM
55.7 s late, and the solver's watchdog ended the run at once with exit code 0. F4's first try was frozen for 85 s;
its re-run was clean and valid.

## What the runs show anyway (descriptive, not a verdict)

| run | instance | T(n) s | part a (T/30) | full limit | K* | valid? |
|---|---|---|---|---|---|---|
| F1 | n1234 | 2,219.4 | 35 | 34 | 27 | yes |
| F2 | n1421 | 2,556.0 | 72 | 66 (first try), 65 (re-run) | 47 | no: both tries paused for 489-536 s |
| F3 | n1608 | 2,892.6 | 113 | 108 | 81 | yes |
| F4 | n1841 | 3,312.0 | 29 | 25 | 18 | yes |

- Every run used fewer vehicles than at T(n)/30, but not many fewer: the three valid runs went from 177 to 167
  vehicles (-5.6%). With F2's paused 65 or 66, the four total 232 or 233, against 249 at T/30 and a total lower bound
  K* of 173. Had F2 been valid, F2 (at most 224) would have failed and F3 (at least 208) would have held: thirty
  times the time barely moves this fleet search. That is a reading of invalid data, recorded for what it is worth.
- F4 found its 25 vehicles by 192 s and never improved on that in the remaining 3,120 s.
- First field evidence for the watchdog's SIGTERM path: in F2's re-run the harness's SIGTERM arrived while the
  solver was in its search, and the solver printed nothing more and exited 0 within 0.1 s
  (`XLTW_WATCHDOG sigterm at 2611.68s`). This was a late SIGTERM after a thaw, not a stuck call.

## What next

- The fleet phase, not the time, is the bottleneck: `xltwff` (0.8 of the time for fleet) and `xltwfc` (fixed-cost
  fleet search) are pre-registered on the same four instances and queued.
- Timed runs on the shared machines need either no pauses or pause-proof scoring; see
  [../xltwrun/pause-audit.md](../xltwrun/pause-audit.md).

Limits: one seed, four instances, two machines; K* is a lower bound, not a known optimum.
