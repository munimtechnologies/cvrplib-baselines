# tmatch: pre-registration (written 2026-11-17, before any run)

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Code Apache-2.0, text CC BY 4.0.

## Question

CVRPLib's VRPTW BKS Challenge ranks solutions by **fewest vehicles first**. On the 33 XLTW-Test instances where
capacity never binds (the fleet is decided by time windows alone), our PyVRP baseline is far above the best lower
bound we have: at the full limit T(n), 33 / 65 / 108 / 25 vehicles on n1234 / n1421 / n1608 / n1841 against K* = 27 / 47
/ 81 / 18. Three PyVRP fleet-search variants and a published route minimiser (Nagata and Bräysy 2009) all did
no better (`xltwrm/`, `xltwrs/`, `xltwfc/`, `nbrm/`). So either K* is loose or the searches are missing something.

**Does a fleet search built around an exact sub-problem find fewer vehicles than PyVRP at the same time budget?**

## Method (tmatch.py, version 0.1.0)

If every customer's service start time is fixed, the fewest routes with no capacity limit is n - M, with M a maximum
bipartite matching in the acyclic graph "j can follow i at these times" (fleet sizing for fixed schedules, Dantzig
and Fulkerson 1954). tmatch alternates: (1) exact maximum matching on the current times (scipy Hopcroft-Karp,
customers in a random order); (2) for each route found, its earliest and latest feasible schedules E and L, and new
times E + lam (L - E), lam = 0 / 1 / uniform with probability 0.4 / 0.4 / 0.2, per route. Every old route stays a path
under its new times, so on capacity-free instances the count never goes up (a unit test checks this). Three starts:
all earliest, all latest, midpoints. Where capacity binds, routes are cut into consecutive pieces within capacity. It
stops at the time budget or at the lower bound lb = max(K*, KM, 1), where K* is `xltwen/` and KM is `kmatch/`.

The matching itself is classical; re-timing whole routes between matchings is our heuristic. A web search on
2026-11-17 found no description of this loop for the VRPTW. That does not mean none exists.

## Instances, budget, comparison

- **Main set (27):** every capacity-free XLTW-Test instance with a part-a PyVRP result in `xltwen/results.json`
  (`kc` = 1 and `vehicles_a` not null): n1048 to n6305. Run order: n1234, n1421, n1608, n1841, then the rest by size.
- **Extra (2, described, not in the main comparison):** n1748 and n3888, narrow windows with capacity, where
  `kmatch/` found the matching bound within 1-2 vehicles of K* (142 vs 143, 458 vs 460).
- **Budget:** T(n)/30 = 60 s per 1,000 customers, wall clock from the start of reading the file, one CPU, seed
  20261117. This is the budget of the PyVRP part-a runs (`xltwrun/`, `vehicles_a`). Those ran on 2026-11-04/05,
  maybe on a different machine, and their clock also covered Python start-up and the bound K; the comparison is
  approximate in time, exact in what is counted.
- **What counts:** a solution counts only if `exact_check()` passes: fractions from the file's own tokens, every
  customer exactly once, no service after its due time, back at the depot before it closes, within capacity,
  nearest-integer travel times. It shares no code with the search. A count below lb would mean a bug or a wrong
  bound and is reported as such.
- Job: one run, 1 CPU, 2 GB, data volume `xltw-test`. Tests (`test_tmatch.py`) run first; a test failure is
  reported but does not stop the study, since every counted solution is checked exactly anyway.

## Predictions (probabilities are our honest guesses)

| id | prediction | p |
|---|---|---|
| T0 | gate: all 29 instances finish without error, every solution passes the exact check, none is below lb | 0.85 |
| T1 | tmatch uses fewer vehicles than PyVRP part a on at least 5 of the 27 | 0.55 |
| T2 | tmatch's total over the 27 is below PyVRP part a's total | 0.35 |
| T3 | total at least 10% below PyVRP part a's (tmatch / PyVRP <= 0.90) | 0.15 |
| T4 | on at least one of n1234, n1421, n1608, n1841, tmatch at T(n)/30 is at or below PyVRP's best at the full T(n) (33, 65, 108, 25) | 0.25 |
| T5 | tmatch reaches lb (a proven-minimum fleet) on at least one of the 29 instances | 0.20 |
| T6 | narrower windows favour tmatch: Spearman correlation between median window width / horizon and (PyVRP - tmatch) / PyVRP over the 27 is at most -0.3 | 0.60 |
| T7 | resources: peak memory at most 1.5 GB, and no instance's search runs more than 30 s past its budget | 0.80 |

Scored from `results.json` `tally` (`invalid`, `below_lb`, `errors`, `wins`, `sum_tmatch`, `sum_pyvrp_a`,
`ratio_tmatch_to_pyvrp_a`, `named`, `at_lb`, `spearman_window_vs_advantage`, `peak_gb`, `over_budget_30s`), with a
Brier score. T1-T7 are scored only if T0 holds; if T0 fails we report what ran.

## What follows from the result

- If tmatch wins on some instances (T1): it becomes a second fleet phase in xltw-solver (run both, keep fewer
  vehicles, give the routes to PyVRP for distance), pre-registered separately, before the algorithm track closes on
  2027-01-16.
- If it reaches lb anywhere (T5): that instance's minimum fleet is proven, and the same check is worth running on the
  official XLTW instances when they are released on 2027-02-24.
- If it loses everywhere: reported as a negative result, like `nbrm/`.
