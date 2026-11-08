# nbrm: expectations (pre-registered)

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. CC BY 4.0.
Written and published on 2026-11-08, before any run of this study. The job waits until this file is public on `main`
and byte-identical to its own copy before it runs anything.

## Question

On the four capacity-free XLTW-Test instances of `xltwfull/` (where only the time windows decide the fleet), MV2's
PyVRP-based fleet search ends 30-40% above the fleet lower bound K*, and three variants of it lost to the plain loop
(`xltwff/`, `xltwfc/`, `xltwrm/`, `xltwrs/`). Is the gap the search or the instances? This study runs a method built
only to remove routes, the route-minimisation heuristic of Nagata & Bräysy (Operations Research Letters 37, 2009),
in the open C implementation by Astronomax (https://github.com/Astronomax/vrptw-powerful-route-minimization-heuristic,
MIT licence; its README reports 3,423 routes on the 60 Gehring & Homberger 1,000-customer instances in 10 minutes,
against a best-known total of 3,416). We did not write this method or its code; we measure it on a new benchmark,
under the VRPTW Challenge's distance rule, against our own published runs.

## What runs

- **Code:** the repository at commit `89d4c05` ("squeeze: add --squeeze ...", 2026-10-01), with its submodule
  `src/lib/small`, cloned in the job's setup. One change, applied by `getnb.py` and required to match exactly once
  in `src/problem.c`: `sqrt(dx * dx + dy * dy)` becomes `floor(sqrt(dx * dx + dy * dy) + 0.5)`, so every arc's
  travel time is its Euclidean length rounded to the nearest integer, the challenge's rule (the code otherwise uses
  unrounded lengths). Release build (`cmake -DCMAKE_BUILD_TYPE=Release`) with `-DENABLE_MARCH_NATIVE=OFF`; if that
  build fails, the default flags are used and the job records it. Its `MAX_N_CUSTOMERS` is 2,000; all four
  instances are below it.
- **Input:** each XLTW-Test `.vrp` file is rewritten in Gehring & Homberger's text format with its own tokens
  (customer numbers 0..n in the file's order, depot 0).
- **Command:** `./routes INSTANCE.txt OUT.sol --t_max L --lower_bound K* --seed 20261104 --log_level normal`, with
  every other option at its default (`n_near` 100, `k_max` 5, `i_rand` 1000, `squeeze` near, no beta correction).
  L = floor(T(n) / 2) seconds, T(n) = 1,800 x n / 1,000 s, n = customers: the share of the limit that the plain
  loop's fleet phase gets in `xltwfull/`. The code measures its limit in process CPU time (`clock()`), so a host
  pause does not shorten it. A wall-clock guard kills a run at T(n) + 300 s; a run killed by it is re-run once,
  unchanged, and both attempts are kept.
- **Check:** each written solution is re-checked by `xltwbase.check_exact` (cvrplib-baselines v0.3.7) in 50-digit
  decimals from the instance file's tokens under the `round` convention: every customer exactly once, capacity, and
  every arrival (depot return included) by its due time.
- **Smoke run first:** a 60-customer synthetic instance (`xltwbase.synthetic(60)`), `--t_max 3 --seed 1`; its
  solution must pass the same check.
- One process at a time, 1 CPU, 1 GB, network off during the runs.

| run | instance | n | T(n) s | L s | K* | best valid PyVRP run at T(n) (vehicles) |
|---|---|---|---|---|---|---|
| N1 | XLTW-Test-n1234 | 1,233 | 2,219.4 | 1,109 | 27 | 33 (`xltwff` H1; plain loop 34) |
| N2 | XLTW-Test-n1421 | 1,420 | 2,556.0 | 1,278 | 47 | 65 (`xltwff` H2) |
| N3 | XLTW-Test-n1608 | 1,607 | 2,892.6 | 1,446 | 81 | 108 (`xltwfull` F3, `xltwff` H3) |
| N4 | XLTW-Test-n1841 | 1,840 | 3,312.0 | 1,656 | 18 | 25 (`xltwfull` F4, `xltwff` H4) |

The PyVRP runs had the whole limit T(n) (fleet phase 0.5 or 0.8 of it); the route minimiser gets half of it and
does no distance search. The total of the four PyVRP references is 231; the total of K* is 173.

## Predictions

- **N0 (gate).** The patch matched exactly once, the build succeeded, the smoke run's solution passes the check, and
  each of N1-N4 ended by itself (exit 0, before the wall guard) with a written solution that passes the check. If
  N0 fails, N1-N5 are untestable.
- **N1.** On each of the four instances, the route minimiser uses at most as many vehicles as the best valid PyVRP
  run in the table.
- **N2.** It uses strictly fewer on at least three of the four.
- **N3.** Its four solutions together use at most 221 vehicles (at least 10 fewer than 231).
- **N4.** At most one of the four reaches its K*.
- **N5.** Every run uses at most L + 60 s of CPU time and at most 0.5 GB of peak memory.

N1-N3 say the PyVRP loop's gap is mostly the search, not the instances. N4 says K* is still not tight. N5 says the
method fits half of the challenge's limit, leaving the other half for a distance phase.

## Reported, not predicted

For every run: vehicles, the CPU time at which the final count was first reached (`incumbent_ms` lines), CPU and
wall time, peak memory, the solution's rounded distance (the method does not shorten routes, so this is not
comparable with the PyVRP distances), and the build flags used. One seed, four instances, one machine. This is a
fleet-phase study, not a challenge run: the code writes its solution only when it ends, so it does not follow the
challenge's print-as-you-go protocol, and its CPU-time limit is not the challenge's wall clock. A hybrid entry (this
fleet phase, then a PyVRP distance phase from its routes) would be a later, separately pre-registered study.
