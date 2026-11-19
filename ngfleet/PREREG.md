# ngfleet: does ng-route pricing make fleet lower bounds bite on CVRPLib's XTW leaderboard?

Pre-registration, written 2026-11-19 before any run. MV2 of Munim, Inc. (mv2@munimtech.com). The code, the tests and
this text were made with AI agents working in MV2's name; no human expert has checked them yet. Apache-2.0.

## Question

CVRPLib's XTW set (added 2026-11-02; 100 VRPTW instances with 100-1,000 customers, same generator family as the
XLTW challenge set) is ranked by fewest vehicles first. Strong teams improve its best known solutions (BKS) daily,
CVRPLib marks 22 of them proven optimal, and it publishes no fleet lower bounds for the rest. A fleet is proven minimal
only when a lower bound reaches it.

Our column-generation bound (`cgfleet/`) prices **R2 walks**: walks that may revisit customers, only never twice in a
row and never as i -> j -> i. With wide time windows a walk can circle a cluster of close customers, which inflates
the best route profit P* and weakens Farley's bound sum(pi) / P*. **ngfleet** prices **ng-routes** (Baldacci, Mingozzi
and Roberti 2011) with the same 2-cycle rule instead: a partial route remembers which visited customers are still among
the g = 8 nearest of where it is, and may not go back to them.

Does the stronger route relaxation raise the fleet bound on XTW, and does it prove more BKS fleets minimal? The wow, if
it works: proven-minimum fleets on a live leaderboard set where none are published, by an open and re-checkable method.

## Method (fixed before the run)

* `ngfleet.py` 0.1.0. Exact pricing by a dynamic programme over integer profit levels; per (level, customer) a Pareto
  front of at most B = 4 labels (time, memory bitmask, predecessor outside the neighbourhood). A label that does not
  fit is merged into the front label with the most shared memory (earliest time, intersection of memories,
  predecessor kept only if equal).
* Validity (also tested by brute force in `test_ngfleet.py`): for every ng-route prefix with profit c ending at j, and
  every level k <= c, there is a label at (k, j) whose time is no later and whose forbidden set (memory, j, kept
  predecessor) is contained in the prefix's. Start labels give this for k <= p_j; one extension step keeps it because
  the route's next customer is not forbidden for the prefix, hence not for the label, and the new memory
  ((M + {i}) & N(j)) is contained in the prefix's; dominance and merging only keep labels at least as permissive. So the
  computed P* is at least the profit of every ng-route, and every elementary route is an ng-route. Customers with
  pi = 0 are skipped (safe because service times are >= 1 and travel times are nearest-integer Euclidean, so
  t_ik + s_k + t_kj >= t_ij).
* Column generation (`cg_two_phase`): cgfleet's R2 pricing for 35% of the instance budget (or until it converges),
  then the columns are cut to elementary routes and column generation continues with ng pricing; then finer final ng
  evaluations (1,500 profit levels) at the stability centre, the last RMP duals and the R2 certificate's duals.
  Capacity is ignored (a relaxation). Started from the BKS routes. Budget per instance min(200, 40 + 0.4 n) s plus 60 s
  final; global 3 h; instances with n <= 400, smallest first.
* Every certificate is re-run once (`recheck`) and checked against every BKS route (no real route may earn more than
  P*). A bound counts only if both pass. bound = max(ceil(total demand / capacity), R2 bound, ng bound).
  proved = the BKS passes xtwfleet's exact checker (with its stated cost) and bound == BKS fleet.
* Data: CVRPLib XTW instance set (set 24) and the BKS set downloaded fresh at run time, sha256 in the manifest.

## Predictions (graded from `out/ngfleet/results.json`, key `tally`; p = our probability that it holds)

| id | prediction | p |
|---|---|---|
| P0 | sanity: stdout has no NGFLEET-TESTS-FAILED, `numba` true, `done` >= 20, `unverified` == [], `above_bks` == [] | .75 |
| P1 | `lp_ratio_median` >= 1.02 (ng LP bound at least 2% above the R2 bound, median) | .55 |
| P2 | len(`ng_int_gain`) >= 0.25 * `both` (ng raises the integer bound on a quarter of the instances) | .35 |
| P3 | len(`proved`) >= 8 | .50 |
| P4 | len(`ng_only_proof`) >= 1 (a BKS fleet proved minimal only by the ng bound) | .30 |
| P5 | `sum_bound` >= 0.9 * `sum_bks` | .35 |
| P6 | `peak_gb` <= 1.2 | .85 |

Diagnostics, no prediction: `ng_stalled` (ng phase stopped because recovered routes no longer priced out), `ng_int_loss`
(should be rare; ng and R2 bounds come from different duals).

Grading: each prediction scored 1/0; Brier score over P0-P6 written to `ngfleet/score.md`. If P0 fails on tests or
re-checks, no bound from this run is reported as a result; the bug is fixed and the run repeated as -v2.

## What each outcome means

* P1 and P2 hold: the R2 relaxation was the weak point on wide windows; ngfleet becomes the bound for xtwfleet and for
  the XLTW-Test fleet study (n up to 10,000 after a speed pass).
* P1 fails: on XTW the R2 walks were not the problem; the gap to the BKS fleets is the LP itself (integrality), and the
  next step is cuts (e.g. subset-row cuts) or branching, not a stronger pricing.
* Any `proved` instance not marked optimal on CVRPLib is a new proof of a minimum fleet; its certificate is published
  in `cert/` so anyone can re-check it with one pricing run.
