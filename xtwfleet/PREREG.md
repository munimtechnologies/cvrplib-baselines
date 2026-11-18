# xtwfleet: are the best known fleets of CVRPLib's XTW set minimal? (pre-registration, 2026-11-18)

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name; no human expert has checked this
plan. Code Apache-2.0, text CC BY 4.0. Written before any run of this study.

## Question

On 2026-11-02 CVRPLib added **XTW**: 100 VRPTW instances with 100 to 1,000 customers, from the authors (Uchoa,
Malheiros, Queiroga, Martinelli and Subramanian, 2026) and the generator family of the XLTW sets of the VRPTW BKS
Challenge. Solutions rank by **fewest vehicles first**, then distance. Several strong teams have improved XTW's best
known solutions (BKS) every day since (CVRPLib updates page, 2026-11-03 to 11-17). Example: on XTW-n1001 the fleet went
39 (initial solution) -> 37 -> 36, and it has stayed at 36 since 2026-11-07 through about 20 more improvements in
distance. CVRPLib marks 22 XTW solutions as proven optimal; its bound-history pages show no fleet lower bound for the
others.

1. **Are the live BKS fleets minimal?** Where a valid lower bound reaches a BKS fleet, that fleet is proven minimal
   (the race on that instance is then about distance only).
2. **Search or bound?** On the capacity-free instances of the related XLTW-Test set, the fleets we can find are
   1.3 to 9 times the best bound we have, and we cannot tell which side is weak. On XTW the fleets come from many strong,
   independent searches. If our bounds come close to them, the bounds are good on this family and the XLTW-Test gap is
   mostly our searches'. If not, the bounds are the weak side.

## Method (`xtwfleet.py` 0.1.0; reuses code already public in this repository)

Every bound below ignores some constraint of the real problem, so each is a valid lower bound on the fleet:

- **cap**: ceil(total demand / capacity).
- **stfleet** (`stfleet/`): space-time spanning-tree bound, capacity ignored; every value re-checked exactly.
  10 s + 30 s per 1,000 customers.
- **cgfleet** (`cgfleet/`): Farley bound of the covering LP over 2-cycle-free walks, capacity ignored, column
  generation started from the BKS routes; the certificate is re-checked by one more exact pricing run.
  min(170, 20 + 150 n / 1000) s + 40 s for the final bound. Run, smallest instances first, only on instances that cap
  and stfleet have not already settled, until 4.5 h after the study starts.
- **cgcap** (new here; instances where capacity can bind): for integer duals pi >= 0 every feasible route has profit
  at most P_time(pi) (cgfleet's exact walk pricing) and at most P_knap(pi) (0/1 knapsack of pi under the capacity), so
  fleet >= sum(pi) / min(P_time, P_knap). Duals: mixes lam x (cgfleet duals) + (1 - lam) x (demands), lam in
  {1, 0.75, 0.5, 0.25, 0}; 45 s per instance; re-checked exactly.

The bound is the largest of these. **A BKS fleet counts as proven minimal only if our own exact checker accepts the
BKS solution** (each customer once, capacity, windows with waiting, return to the depot in time, nearest-integer
Euclidean travel = time) **and its stated cost**, and the bound equals its fleet. A bound above a checked BKS fleet would
be a bug in our code and fails the gate. A BKS our checker rejects is reported as a disagreement with our checker,
nothing more.

Data, downloaded by the job: the XTW set and its current BKS file (CVRPLib set 24, sha256 and UTC time recorded),
CVRPLib's VRPTW instance list (for its "Opt" column) and the 100 bound-history pages (ids 736-835, one page every 2 s;
raw pages kept), which give each instance's first and current fleet. 1 CPU, 1.5 GB.

Tests (`test_xtwfleet.py`, plus the existing `test_stfleet.py` and `test_cgfleet.py`): exact nint distances; the
solution checker against an independent route simulation; the 0/1 knapsack against brute force; the cgcap inequality
min(P_time, P_knap) >= every feasible route's profit and cgcap <= the exact minimum fleet (subset dynamic programming)
on random capacitated instances; four co-located customers that each fill a vehicle (time alone allows one route, the
bound must be exactly 4); the page parsers; and the whole harness end to end on tiny instances against brute force.

Prior art: fleet minimisation by set-covering LPs and column generation (Desrosiers, Soumis and Desrochers 1984;
Kontoravdis and Bard 1995), Farley's (1990) bound, energetic reasoning for the fleet (Afifi, Guibadj and Moukrim 2014),
exact branch-cut-and-price for the VRPTW (Pecin, Contardo, Desaulniers and Uchoa 2017), with which the 22 XTW optima
were presumably proved. Combining the time pricing and a knapsack over the same duals is a simple observation that we
did not find stated; that may only mean we did not find it. New for certain: fleet bounds for XTW, which no source we
found reports.

## Predictions (our honest probabilities)

Scored from `results.json` `tally` with a Brier score. X1-X11 only if X0 holds; otherwise we report what ran.
Predictions that use CVRPLib's Opt column are void if fewer than 15 instances parse as "yes" (`opt_marked`); the
history prediction is void if fewer than 80 history pages parse (`history_rows`).

| id | prediction | p |
|---|---|---|
| X0 | gate: no STFLEET-/CGFLEET-/XTWFLEET-TESTS-FAILED in stdout, at least 95 instances `done` without error, `bks_ok` >= 90, `above_bks` and `unverified` empty | 0.60 |
| X1 | at least 25 instances are capacity-free (`capfree`) | 0.55 |
| X2 | the bound proves at least 10 BKS fleets minimal (`proved`) | 0.40 |
| X3 | at least one proof needs a time-window bound: cap alone is below the fleet (`proved_tw_needed`) | 0.40 |
| X4 | at least one proved fleet is on an instance CVRPLib does not mark optimal (`proved_not_opt`) | 0.45 |
| X5 | on at least half of the instances CVRPLib marks optimal, the bound equals the optimal fleet (`opt_bound_equal` >= `opt_marked` / 2) | 0.40 |
| X6 | on the capacity-free instances, the median of BKS fleet / bound is at most 1.25 (`capfree_ratio_median`) | 0.30 |
| X7 | cgfleet >= stfleet on at least 70% of the instances where both ran (`cg_ge_st` >= 0.7 `cg_and_st`) | 0.65 |
| X8 | cgcap is strictly above every other bound on at least one instance (`cgcap_gain`) | 0.45 |
| X9 | sum of bounds >= 0.85 x sum of BKS fleets over checked instances (`sum_final_good`, `sum_bks_good`) | 0.40 |
| X10 | the leaderboard has cut the first published fleet on at least 50 instances (`history_fleet_cut`) | 0.55 |
| X11 | peak memory at most 1.2 GB (`peak_gb`) | 0.85 |

## What follows

- **Proofs (X2/X4):** each proved fleet is published with its certificate, as "the XTW BKS fleet on instance N is
  the minimum" (distance stays open). Certificates can be re-checked with the published code.
- **X6 holds:** the bounds are good on this family, so the 1.3-9x gap on XLTW-Test is mostly our searches'; the XLTW
  work then moves to search (`tmatch/`, then a stronger fleet phase). **X6 fails:** the bounds are the weak side on
  wide-window instances; next is a stronger relaxation (ng-routes or elementary pricing on the small instances), and
  the XLTW gap question stays open. Either way the result is reported, including as a negative result.
- Nothing here is framed as an error of CVRPLib or of any team.
