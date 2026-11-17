# cgfleet: pre-registration (written 2026-11-17, before any run)

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Code Apache-2.0, text CC BY 4.0.

## Question

CVRPLib's VRPTW BKS Challenge ranks solutions by **fewest vehicles first**. On the 33 capacity-free XLTW-Test instances
(capacity equals total demand, so time windows alone decide the fleet), the fleets we can find are far above the best
lower bound we have, K* (energetic reasoning after Afifi, Guibadj and Moukrim 2014, `xltwen/`): n1048 needs 9 vehicles
against K* = 3, n1514 44 against 13, n2867 29 against 4. Longer runs, three PyVRP fleet variants and a published route
minimiser (Nagata and Bräysy) did not close this (`xltwfull/`, `xltwfc/`, `nbrm/`), and a path-cover bound never beat
K* (`kmatch/`). **Is the gap in the searches or in the bound?** A much stronger bound answers this either way; where it
meets a known fleet, that fleet is proven minimal, which is rare at 1,000+ customers.

## Method (cgfleet.py, version 0.1.0)

- **Bound.** The fleet is at least the LP min sum x_r, sum_r a_ir x_r >= 1, over any route set that contains every
  feasible route. For any integer duals pi >= 0, fleet >= ceil(sum pi / P*(pi)) (Farley's bound), where P* is the most
  dual profit one route can collect. We compute P* **exactly** over a relaxed route set R2: walks over customers with
  pi >= 1 that never repeat a customer twice in a row or as i -> j -> i (longer cycles are allowed; that is the
  relaxation). Dropping zero-dual customers is safe because travel times are nearest-integer Euclidean
  (t_ik + t_kj >= t_ij - 1) and every service time is at least 1 (checked per instance; otherwise it is skipped).
- **P*** by a dynamic programme over integer profit levels: T[k][j] = earliest service start at j of an R2 walk ending
  at j with profit >= k, keeping the best and second-best predecessor (2-cycle elimination). Tests compare it with a
  memoised exhaustive search on small instances and check that it is never below the best real route.
- **Duals** from column generation: restricted master LP in HiGHS (scipy), new columns = the walks the DP finds,
  Wentges smoothing (weight 0.5), 300 profit levels per unit while pricing, then one final bound at 1,500 levels at the
  stability centre and at the last LP duals. Starting columns: singletons and the fixed-time matching routes of
  `tmatch/` (earliest and latest times).
- **Budget:** 450 s per 1,000 customers (at most 1,500 s), 75% for column generation and the rest plus 300 s for the
  final bound; 1 CPU, 2 GB. Each bound is written with its certificate (integer duals and P*) to `cert/`, so it can be
  re-checked with one DP run.
- The method is classical (set-covering LP for fleet minimisation, column generation, Farley 1990, 2-cycle
  elimination). A search on 2026-11-17 found no column-generation fleet bounds published for XLTW-Test (released
  2026-11-02). What is new is only the numbers.

## Instances (10, fixed)

| instance | n | K* | best known fleet (ub) |
|---|---|---|---|
| XLTW-Test-n1048 | 1047 | 3 | 9 |
| XLTW-Test-n1234 | 1233 | 27 | 33 |
| XLTW-Test-n1421 | 1420 | 47 | 65 |
| XLTW-Test-n1514 | 1513 | 13 | 44 |
| XLTW-Test-n1608 | 1607 | 81 | 108 |
| XLTW-Test-n1841 | 1840 | 18 | 25 |
| XLTW-Test-n1934 | 1933 | 43 | 54 |
| XLTW-Test-n2028 | 2027 | 84 | 103 |
| XLTW-Test-n2214 | 2213 | 53 | 77 |
| XLTW-Test-n2867 | 2866 | 4 | 29 |

ub = the smaller of PyVRP part a at T(n)/30 (`xltwen/results.json` `vehicles_a`) and the best valid PyVRP run at the
full T(n) (`xltwfull/`, `nbrm/`: n1234 33, n1421 65, n1608 108, n1841 25). The capacity-free instances above 3,000
customers are left out for memory and time.

## Predictions (our honest probabilities)

| id | prediction | p |
|---|---|---|
| C0 | gate: tests pass, at least 8 of 10 instances finish without error, and no bound is above its known fleet (`above_ub` empty; a bound above a feasible fleet would be a bug) | 0.80 |
| C1 | the bound is above K* on at least one instance (`above_kstar` non-empty) | 0.60 |
| C2 | ... on at least 4 instances | 0.35 |
| C3 | it closes at least half of the gap from K* to the known fleet on at least one instance (`half_gap`) | 0.25 |
| C4 | it proves a known fleet minimal on at least one instance (`proved`) | 0.07 |
| C5 | it is above K* on at least one of the three service-time-1 instances n1048, n1514, n2867 (`service1_above_kstar`) | 0.35 |
| C6 | column generation closes (bound = ceil of the master LP value) on at least one instance (`converged`) | 0.30 |
| C7 | sum of bounds over finished instances >= 1.10 x sum of their K* (`sum_lb`, `sum_kstar`) | 0.25 |
| C8 | peak memory at most 1.5 GB (`peak_gb`) | 0.85 |

Scored from `results.json` `tally` with a Brier score; C1-C8 only if C0 holds, otherwise we report what ran.

## What follows

- **Bound well above K*** (C1-C3): the fleet gap is largely K*'s, and the solvers are closer to optimal than K* says.
  The bound becomes the reference in `cvrplib-baselines`, and the same code is run on the official XLTW instances
  when they are released on 2027-02-24.
- **A fleet proven minimal** (C4): written up as such, with the certificate.
- **Bound stays at K*** (C1 fails): the LP over R2 walks is no stronger than energetic reasoning here, so either the
  searches are weak (the gap is real and worth attacking with new fleet methods) or a stronger relaxation is needed
  (ng-routes, cuts). Reported as a negative result, like `kmatch/`.
