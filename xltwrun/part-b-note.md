# xltwrun part b (instances with more than 6,444 customers): first two thirds, and what went wrong

> **Correction (2026-11-06, later the same day).** The section "One real failure: XLTW-Test-n8575 did not stop"
> below is wrong. The job runner's log shows this container was paused by the host from about 76 s to about 515 s
> into the n8575 run; the pause ended at the limit, so the late-SIGTERM rule did not catch it. It was not a stuck
> PyVRP call. Two runs in the table below that the rule counted as valid (n7037 and n8389) were also paused for
> about 184 s each. See [pause-audit.md](pause-audit.md) for every affected run and how it was checked.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. CC BY 4.0.
Written 2026-11-06 ~05:30 UTC. Raw outputs: `results-b1.*`, `progress-b1.jsonl`, `results-b2.*`, `progress-b2.jsonl`,
`sols/` (every counted solution, exact-checked). Pre-registration: `expectations.md` (G0-G5, scored only on all
100 instances, after part b3 and the re-runs below).

Jobs `xltwrun-b1-v1` (8 instances, 6,587-7,682 customers) and `xltwrun-b2-v1` (6 instances, 7,853-8,765) ran the
pinned baseline (`solver.py` at ba1eec8, PyVRP 0.14.1) one instance at a time at T(n)/30, seed 20261104, from
02:35 to 04:47 UTC on 2026-11-06.

## Five runs were frozen by the host, not by the solver

Both containers were paused by the host for about 45 minutes in total while they ran. A paused container freezes
the harness as well as the solver, and the clock keeps going. In five runs the harness's first poll after the
pause was long past the limit: it sent SIGTERM 388-930 s late and SIGKILL 0.2 s after it.

| part | instance | limit s | SIGTERM sent at s | vehicles | K |
|---|---|---|---|---|---|
| b1 | XLTW-Test-n6734 | 404.0 | 978.5 | 222 | 163 |
| b1 | XLTW-Test-n6884 | 413.0 | 1343.3 | 296 | 16 |
| b1 | XLTW-Test-n7193 | 431.5 | 819.1 | 114 | 52 |
| b2 | XLTW-Test-n8028 | 481.6 | 977.9 | 902 | 803 |
| b2 | XLTW-Test-n8207 | 492.4 | 1254.8 | 257 | 251 |

These are not valid runs of the protocol. Rule, set before any re-run result is known: a run whose SIGTERM was sent
more than 1 s after its limit (the harness polls every 0.2 s) is invalid and is re-run once, unchanged (job
`xltwrun-b1r-v1`: parts b1ra, b1rb, b2r). The final score uses the re-runs; these originals stay here.

## One real failure: XLTW-Test-n8575 did not stop (WRONG, see the correction at the top)

On n8575 (8,574 customers, capacity non-binding, K = 11) the harness was on time: SIGTERM 0.19 s after the
514.4 s limit. The solver had not stopped by itself and did not react within 5 s, so it was SIGKILLed. Its stderr
ends after the bound line, and its last solution (156 vehicles) was printed at 64.5 s. One PyVRP call ran for more
than 450 s without returning to Python, where both the solver's stopping check and its SIGTERM handler run. The
counted solution still counts under the rules (it was printed before the limit), but this breaks pre-registered
G0 ("no SIGKILL") whatever the remaining runs show, and the run wasted most of its time.

The fix is being tested in `xltwpkg/` (pre-registered): a watchdog thread that ends the process on time even when
the main thread is stuck inside PyVRP's local search, which releases the GIL. The baseline in this folder stays
as pinned; the fix goes into the packaged solver.

## The valid runs so far

| part | instance | n | KC | K | vehicles | distance | vehicles / K |
|---|---|---|---|---|---|---|---|
| b1 | XLTW-Test-n6588 | 6587 | 87 | 87 | 172 | 156235 | 1.98 |
| b1 | XLTW-Test-n7037 | 7036 | 587 | 587 | 647 | 574297 | 1.10 |
| b1 | XLTW-Test-n7353 | 7352 | 85 | 85 | 99 | 169545 | 1.16 |
| b1 | XLTW-Test-n7516 | 7515 | 1 | 4 | 235 | 190662 | 58.8 |
| b1 | XLTW-Test-n7683 | 7682 | 269 | 269 | 409 | 553215 | 1.52 |
| b2 | XLTW-Test-n7854 | 7853 | 1 | 4 | 62 | 129631 | 15.5 |
| b2 | XLTW-Test-n8389 | 8388 | 162 | 162 | 404 | 731276 | 2.49 |
| b2 | XLTW-Test-n8575 | 8574 | 1 | 11 | 156 | 207870 | 14.2 (SIGKILLed, see above) |
| b2 | XLTW-Test-n8766 | 8765 | 432 | 432 | 447 | 456857 | 1.03 |

None of the nine reached K. K is a lower bound, not a known optimum; for the capacity-free (KC = 1) instances it
is very weak (the energetic-reasoning bounds pre-registered in `xltwen/` will say how weak).
Peak memory per solver process: 2.14-3.74 GB.
