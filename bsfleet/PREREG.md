# bsfleet: do route-level bounds on the busy stretches close the XLTW-Test fleet gap?

Pre-registration, written 2026-11-27 before any run. MV2 of Munim, Inc. (mv2@munimtech.com). The code, the tests and
this text were made with AI agents working in MV2's name; no human expert has checked them yet. Apache-2.0.

## Question

CVRPLib's VRPTW challenge ranks solutions by fewest vehicles first. On the 33 capacity-free XLTW-Test instances the
best fleets we know are 1.3 to 9 times the best lower bounds we can prove. Our graded stfleet study
([score.md](../stfleet/score.md)) raised the bounds on 17 of 33 instances but closed at most 1/6 of any gap. It also
showed that the binding part of the day is always a busy stretch [t1, t2], never the whole day. Its bound is a
spanning-tree argument: it charges travel, forced waiting and idle time, but not the fact that a vehicle's customers
must form one time-feasible route.

Route-level bounds (set-covering LP over whole feasible routes, column generation) capture exactly that, but their
dense pricing does not fit 1,000-10,000 customers. **bsfleet** runs them only on the customers of a busy stretch.
That is still a valid lower bound on the whole instance's fleet (proof in `bsfleet.py`'s docstring). Does it beat
stfleet on the same stretch, and does it move the best known bounds towards the fleets? The wow, if it works:
bounds that close a real share of the gap, or prove one of these 1,000+ customer fleets minimal, on the set
the 2027 challenge's instances come from.

## Method (fixed before the run)

* `bsfleet.py` 0.1.0 on ngfleet 0.1.0 (R2 walks, then ng-routes with g = 8 and a front of B = 4 labels; exact pricing
  over integer profit levels) and cgfleet 0.1.0, fetched from `main` with sha256 in the manifest.
* Instances: the stfleet records (stfleet/results.json on `main`) with a candidate stretch of at most 1,500
  customers, smallest stretch first. Per instance at most 2 stretches, in this order: stfleet's certificate
  stretch, the whole day (only if n <= 1,500), then stfleet's other refined stretches, largest first.
* Per stretch: S = customers with e_i >= t1 and l_i + s_i <= t2 (stfleet's rule); a greedy cover of S by feasible
  routes (start columns, and an upper bound for the S-problem); column generation for min(900, 60 + 0.5 m) s (35% R2)
  plus 120 s of final finer evaluations. Global budget 4.5 h.
* Every certificate is re-run once (`ngfleet.recheck`) and checked against the greedy routes (no real route may earn
  more than P*). A bound counts only if both pass. Instance bound bs = max over its stretches; best_after =
  max(K*, stfleet, bs); proved = best_after >= the best known fleet (`ub` in stfleet/results.json).

## Predictions (graded from `out/bsfleet/results.json`, key `tally`; p = our probability that it holds)

| id | prediction | p |
|---|---|---|
| Q0 | sanity: stdout has no BSFLEET-TESTS-FAILED; `numba` true; `done` >= 8; `unverified`, `greedy_bad`, `above_greedy`, `above_ub`, `m_mismatch` all == [] | .70 |
| Q1 | `stretch_above_stfleet` >= 0.5 * `stretches_done` (the route LP beats stfleet's K on the same stretch on at least half) | .70 |
| Q2 | len(`above_best`) >= 3 (the best known bound rises on at least 3 instances) | .55 |
| Q3 | `sum_after` - `sum_before` >= 0.10 * (`sum_ub` - `sum_before`) (a tenth of the summed gap closed on the instances run) | .30 |
| Q4 | len(`proved`) >= 1 | .10 |
| Q5 | `stretch_solved` >= 1 (on some stretch the bound equals the greedy cover: that S-problem is solved) | .45 |
| Q6 | `n1048_bs` >= 5 (stfleet 4, best known fleet 9) | .45 |
| Q7 | `peak_gb` <= 1.8 | .80 |
| Q8 | `gap_closed_max` >= 0.34 (twice stfleet's best share on one instance) | .35 |

Diagnostics, no prediction: `ng_int_gain`, `stretch_errors`, per-stretch `z_rmp` (whether column generation converged).

Grading: each prediction scored 1/0; Brier score over Q0-Q8 written to `bsfleet/score.md`. If Q0 fails on tests or
re-checks, no bound from this run is reported as a result; the bug is fixed and the run repeated as -v2.

## What each outcome means

* Q2 and Q3 hold: a large part of the fleet gap was the bound. Next: route-level bounds on larger stretches (sparse
  pricing) and an update of the stfleet article.
* Q1 holds, Q2 fails: the route LP is stronger locally, but stfleet's stretches are not where it bites; next, choose
  stretches by the LP itself.
* Q1 fails: on busy stretches whole-route reasoning adds little to the tree bound, so the gap is mostly in the
  searches; next, fleet search (xltw-solver), not bounds.
* A stretch with bound == greedy cover below the best known fleet: that customer set is exhausted, and a better
  bound must use other customers.
