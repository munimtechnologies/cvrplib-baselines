# mstfleet: pre-registration (written 2026-11-17, before any run)

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Code Apache-2.0, text CC BY 4.0.

## Question

CVRPLib's VRPTW BKS Challenge ranks solutions by **fewest vehicles first**. On the 33 capacity-free XLTW-Test instances
(capacity is at least the total demand, so time alone decides the fleet), the fleets that PyVRP and our other searches
find are 1.3 to 9 times the best lower bound we have, K* (energetic reasoning, `xltwen/`): n1048 needs 9 vehicles
against K* = 3, n2867 29 against 4. **Is the gap in the searches or in the bounds?** Two bounds that are already
queued (`cgfleet/`, a column-generation LP over relaxed routes) and one search (`tmatch/`) attack it. This study adds a
third, cheap, different bound aimed at exactly the instances where the gap is largest.

Why a new bound. `kmatch/` found that on these instances 33-93% of ordered customer pairs are time-compatible
(81% on n1048, 82% on n2867): the windows are wide. Several big-gap instances have service time 1 (n1048, n1514, n2867, n5902), so
what fills a vehicle's day is driving. K* charges each customer only the travel time from its nearest feasible
neighbour. But the customers that must be served inside a given stretch of the day are a sparse subset, and serving a
sparse subset costs much more driving per customer than nearest-neighbour distances suggest. A relaxation over routes
that may revisit customers (like `cgfleet/`'s) can also be weak when windows are wide.

## Method (mstfleet.py, version 0.1.0)

- **Bound.** For a time interval [t1, t2], let S be the customers whose whole service must lie inside it (earliest
  start >= t1 and latest end <= t2, windows tightened by the depot's hours). Each vehicle serving customers of S visits
  them in order inside the interval, so K (t2 - t1) >= (service of S) + (travel along K vertex-disjoint paths covering
  S) >= (service of S) + MSF_K(S), the minimum spanning forest of S with at most K trees (the MST minus its K - 1 heaviest
  edges). Going via other customers is never shorter: rounded travel times satisfy t_ik + t_kj >= t_ij - 1 and every
  service time is at least 1 (checked per instance). At the start or end of the day the paths are rooted at the depot
  (a spanning tree of S plus the depot), and over the whole day each route also needs a return leg.
- **Lagrangian step.** On every such path a customer has degree at most 2, so for any integer lambda >= 0 the forest
  on weights t_ij + lambda_i + lambda_j, minus 2 sum lambda, is still a valid lower bound (Held and Karp's idea). We
  search lambda by subgradient steps on the 4 most promising intervals of each instance.
- **Search over intervals.** A 32 x 32 grid of interval start points (quantiles of the earliest starts) and end points
  (quantiles of the latest ends), the whole day, and a local refinement around the best 3 intervals. Budget per
  instance: 40 s + 40 s per 1,000 customers (at most 420 s); 1 CPU, 1 GB.
- **Exactness.** Travel times are lower bounds of the challenge's rounded Euclidean times (floor(d + 0.5 - 1e-9)),
  lambda is integral and forest weights are exact integers. Every reported bound comes with a certificate (interval,
  variant, lambda) and is re-checked by `verify()` with exact fractions; a bound that fails the re-check is not
  reported (it falls back to the plain bound, and the instance is listed as `unverified`).
- **Tests** (`test_mstfleet.py`) compare the bound with the exact minimum fleet (subset dynamic programming) on 30+
  tiny random instances, and with planted fleets on instances built from K known feasible routes (narrow, wide and
  zero-slack windows), check the spanning trees against scipy's, and check that over-claimed certificates are refused.
- **Prior art.** Energetic reasoning for the VRPTW fleet (Afifi, Guibadj and Moukrim 2014), precedence-graph fleet
  bounds for the m-TSPTW (Mitrovic-Minic and Krishnamurti 2006), Fisher's K-trees and the Held-Karp bound are
  classical. A search on 2026-11-17 found no fleet bound that uses the spanning forest of the customers whose windows
  lie inside a time interval; that may only mean we did not find it. What is certainly new is the numbers on
  XLTW-Test (released 2026-11-02).

## Instances

All capacity-free XLTW-Test instances, i.e. every row with kc = 1 in `xltwen/results.json` on `main` (33 instances,
1,047 to 9,783 customers), smallest first. K* = max(k, e) of that file; the known fleet (ub) is the smaller of
PyVRP part a at T(n)/30 (`vehicles_a`) and the best valid run at the full T(n) (n1234 33, n1421 65, n1608 108,
n1841 25). The job also writes a profile of each instance's time windows (window width as a share of the day).

## Predictions (our honest probabilities)

Scored from `results.json` `tally` with a Brier score; M1-M10 only if M0 holds, otherwise we report what ran.

| id | prediction | p |
|---|---|---|
| M0 | gate: the tests pass (no MSTFLEET-TESTS-FAILED in stdout), at least 30 of 33 instances finish without error, `unverified` is empty, and no bound is above a known fleet (`above_ub` empty; that would be a bug) | 0.80 |
| M1 | the bound is above K* on at least one instance (`above_kstar` non-empty) | 0.45 |
| M2 | ... on at least 5 instances | 0.20 |
| M3 | it is above K* on at least one of the service-time-1 big-gap instances n1048, n1514, n2867, n5902 (`service1_above_kstar`) | 0.30 |
| M4 | the Lagrangian step raises the bound over the plain forest bound on at least 3 instances (`hk_gain`) | 0.35 |
| M5 | the best plain bound comes from an interior ("free") interval, not the start, end or whole day, on at least half of the finished instances (`plain_best_is_free`) | 0.45 |
| M6 | n1048's bound is at least 4 (`n1048_bound`) | 0.15 |
| M7 | sum over instances of max(K*, bound) >= 1.02 x sum of K* (`sum_max`, `sum_kstar`) | 0.15 |
| M8 | peak memory at most 0.8 GB (`peak_gb`) | 0.90 |
| M9 | the median, over instances, of the median window width is at least 20% of the day (`median_width_median` >= 0.2) | 0.55 |
| M10 | it proves a known fleet minimal on at least one instance (`proved`) | 0.03 |

## What follows

- **Above K* on the big-gap instances:** the gap is partly the bound's; the new bound becomes the reference in
  `cvrplib-baselines`, and v0.2 adds windows that only partly overlap an interval (their compulsory part) and
  Held-Karp-style 1-trees for the paths.
- **Never above K*:** an honest negative result: sparse-subset travel does not explain the fleet gap, which then
  points to the searches (`tmatch/`) or to stronger LP bounds (`cgfleet/`). Reported as such.
- Whatever happens, the window profile tells us which relaxation `cgfleet/` v0.2 needs (wide windows make
  revisiting relaxations weak; ng-routes would then come first).
