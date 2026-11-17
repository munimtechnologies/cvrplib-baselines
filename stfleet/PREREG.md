# stfleet (mstfleet 0.2): pre-registration (written 2026-11-17, before any run of it or of mstfleet 0.1)

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Code Apache-2.0, text CC BY 4.0.

## Question

CVRPLib's VRPTW BKS Challenge ranks solutions by **fewest vehicles first**. On the 33 capacity-free XLTW-Test
instances the fleets we can find are 1.3 to 9 times the best lower bound we have, K* (n1048: 9 against 3; n2867: 29
against 4). **Is the gap in the searches or in the bounds?** `mstfleet/` 0.1 (queued, not yet run) bounds the fleet
with the travel the vehicles need between the customers whose windows lie inside a stretch of the day. This version
also charges what 0.1 ignores and every route pays for:

1. **forced waiting** between two customers (if i's latest end is before j's earliest start, the gap is at least the
   difference, even at the same address), and pairs that no route can serve one after the other in either order;
2. **idle time at the ends of the stretch**: before a vehicle's first customer there (at least that customer's earliest
   start minus the stretch's start), and after its last one.

## Method (stfleet.py 0.2.0; full statement in its docstring)

For a stretch [t1, t2] of length L, every vehicle's time in it splits exactly into idle-before + service + gaps +
idle-after, and each part has a lower bound. Joining each vehicle's first customer to a root gives a spanning tree of
the customers plus the root, with root degree = number of vehicles (at most K) and customer degree at most 2. With a
Lagrangian weight mu on the root degree and integer weights lam on the customer degrees:

    fleet >= ceil(N / mu),   N = MST(customers + root) - 2 sum lam + total service,

where customer-customer edges cost min over the feasible orders of max(travel, forced wait) (+ lam), and root edges
cost (idle-before bound) + (smallest idle-after bound) - L + mu (+ lam); the time-reversed form is also used. This
contains all of 0.1's bounds (a test checks the whole-day case on random instances). Travel times are lower bounds of
the challenge's rounded Euclidean times, every service time must be at least 1 (checked), data must be integral
(checked), and every reported bound is re-checked exactly by `verify()` from its certificate (stretch, side, mu, lam).

Search: a 16 x 16 grid of stretches plus the whole day, both sides, 4 values of mu each; then on the best 4 a ternary
search on mu (N / mu is quasi-concave in mu) and subgradient steps on lam. Budget 40 s + 50 s per 1,000 customers
(at most 480 s) per instance, 1 CPU, 1 GB. For comparison the job also computes 0.1's whole-day bound.

Tests (`test_stfleet.py`): the spanning tree against scipy's on an independently built weight matrix; the bound never
above the exact minimum fleet (subset dynamic programming) on 40+ tiny random instances, on every stretch, side and
several mu, with and without lam; never above planted fleets (narrow, wide, zero-slack); a 4-corner instance where only
the order rule proves the true fleet of 4 (0.1 gets 3); a same-address instance whose single vehicle's day is exactly
full (the bound must give exactly 1: an off-by-one would give 2); refusal of over-claimed or malformed certificates.

Prior art: energetic reasoning for the VRPTW fleet (Afifi, Guibadj and Moukrim 2014), Fisher's K-trees, Held and
Karp's Lagrangian, degree-constrained spanning trees, and time-window "waiting" arguments in TSPTW lower bounds are
classical. We did not find a fleet bound that combines them over the customers of a stretch of the day as above; that
may only mean we did not find it. What is certainly new is the numbers on XLTW-Test (released 2026-11-02).

## Instances

As in `mstfleet/PREREG.md`: every capacity-free row (kc = 1) of `xltwen/results.json` on `main`, 33 instances,
1,047 to 9,783 customers, smallest first. K* = max(k, e) there; the known fleet (ub) is the smaller of PyVRP part a
(`vehicles_a`) and the best valid full-T(n) run (n1234 33, n1421 65, n1608 108, n1841 25).

## Predictions (our honest probabilities)

Scored from `results.json` `tally` with a Brier score; S1-S10 only if S0 holds, otherwise we report what ran.

| id | prediction | p |
|---|---|---|
| S0 | gate: the tests pass (no STFLEET-TESTS-FAILED in stdout), at least 30 of 33 instances finish without error, `unverified` is empty, and `above_ub` is empty (a bound above a known fleet would be a bug) | 0.75 |
| S1 | the bound is above K* on at least one instance (`above_kstar` non-empty) | 0.55 |
| S2 | ... on at least 5 instances | 0.30 |
| S3 | it is above K* on at least one of n1048, n1514, n2867, n5902 (`service1_above_kstar`) | 0.35 |
| S4 | it is above 0.1's whole-day bound on at least 10 instances (`above_v01_whole_day`) | 0.50 |
| S5 | the Lagrangian lam raises the bound on at least 3 instances (`hk_gain`) | 0.35 |
| S6 | the best stretch is not the whole day on at least half of the finished instances (`best_not_whole_day`) | 0.45 |
| S7 | n1048's bound is at least 4 (`n1048_bound`) | 0.20 |
| S8 | sum over instances of max(K*, bound) >= 1.02 x sum of K* (`sum_max`, `sum_kstar`) | 0.25 |
| S9 | peak memory at most 0.8 GB (`peak_gb`) | 0.90 |
| S10 | it proves a known fleet minimal on at least one instance (`proved`) | 0.04 |

## What follows

- **Above K* on the big-gap instances:** part of the gap was the bound's. The bound becomes the reference in
  `cvrplib-baselines`; where it meets a known fleet, that fleet is proven minimal (certificate published).
- **About equal to 0.1 and K*:** waiting and idle time do not explain the gap either; with `cgfleet/` (an LP over
  relaxed routes) this would point firmly at the searches (`tmatch/`), and is reported as a negative result.
- Either way the job writes which stretch and side gave each bound, which tells the next version where to look.
