# Expectations written before vrptwlb-bounds-v1 ran (2026-10-30 ~20:30 UTC)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.

**Why.** CVRPLib's VRPTW BKS Challenge ranks by vehicles first. [`vrptwl/`](../vrptwl/score.md) found that PyVRP's
`minimise_fleet` returned early on 41 of the 60 1,000-customer instances, and all 41 results use exactly SINTEF's
vehicle count. In PyVRP 0.14.1's source, an early return happens only when the fleet reaches the capacity bound
ceil(total demand / capacity). If so, those 41 records cannot use fewer vehicles, and the vehicle objective is
settled there. This job checks that directly and extends it to all 356 CVRPLib VRPTW instances (56 Solomon, 300
Gehring-Homberger). It adds the classic time-window bound: customers that no single route can serve together, in
either order, each need their own vehicle.

**Prior art.** Both bounds are textbook. The capacity bound is the bin-packing bound used in many papers and in
PyVRP itself. The time-window (incompatibility clique) bound goes back to Kontoravdis and Bard (1995), who reported
it per Solomon instance. We found no open per-instance table that sets both bounds against SINTEF's current
fewest-vehicles records for all 300 Gehring-Homberger instances, separately in double precision and under DIMACS.
That table, and the list of instances where the vehicle count is still open, is what this job adds. It is a
calibration and planning aid, not a new method.

**Method.** `bounds.py` reads each instance and CVRPLib BKS (ids 380 to 735, cached copies) and SINTEF's six record
pages (100 to 1,000 customers), re-read during the run. For each instance:

- KC = ceil(total demand / capacity).
- Two customers are *incompatible* if neither order works on one route: starting at the earliest possible time at
  the first (its ready time, or the direct trip from the depot), the second cannot be reached by its due time with
  enough time left to get back to the depot. Tolerance 1e-6, as in our checkers, which can only weaken the bound.
- KT = size of a clique of mutually incompatible customers, found by greedy search (3 fixed orders, 64 shuffles and
  32 degree-guided starts, seed 20261031). Every customer in it needs its own route, so any such clique is a valid
  bound. The search is not exact, so KT may be below the largest such clique.
- K = max(KC, KT), computed twice: in double precision (travel time = Euclidean distance) and under DIMACS (each arc
  truncated to 0.1; only when every service time is at least 0.2, so that the direct arc is the quickest way
  between two customers). Every clique is re-checked pair by pair in exact 50-digit decimal arithmetic from the
  file's own numbers.
- K is compared with SINTEF's record (double precision), CVRPLib's BKS route count (DIMACS) and `vrptwl/`'s PyVRP
  results (double precision).

**Predictions** (scored by `score_b()` in `bounds.py`, written before the run):

| | Prediction | Basis | Our odds |
|---|---|---|---|
| B0 | 356 instances read with no errors, a SINTEF record found for every one, every clique confirmed by the exact check, no customer that cannot be served at all. | Hygiene; SINTEF's pages have footnote letters and one broken link name, so parsing is the main risk. | 80% |
| B1 | No SINTEF record uses fewer vehicles than its double-precision K, no CVRPLib BKS fewer routes than its DIMACS K, and no `vrptwl/` result fewer vehicles than K. | A failure would mean a bug in the bound (or an infeasible record). | 97% |
| B2 | For all 41 instances where `minimise_fleet` returned before its 300 s limit, KC equals the fleet it returned. | PyVRP 0.14.1's `minimise_fleet` source. | 95% |
| B3 | At 1,000 customers, KT exceeds KC on at most 5 of 60 instances. | With 1,000 customers and capacity 200 (C1, R1, RC1), KC is about 90, far above the cliques we expect from time windows alone. | 60% |
| B4 | On Solomon's R101 (SINTEF record 19 vehicles), KT exceeds KC. | R101's windows are 10 units wide, and the capacity bound is only about 8. | 75% |
| B5 | Across all 356 instances, SINTEF's vehicle count equals K for between 40% and 70%. | Solomon C1/C2 records equal KC (17 of 56); at 1,000 customers at least 41 of 60 should. The other sizes are a guess. | 50% |

Only reported, not predicted: K by convention, where the time-window bound is the binding one, the total gap
(SINTEF minus K) by size and family, and the list of 1,000-customer instances where the record is above K, which
is where fleet reduction can still matter.

**Limits stated in advance.** K is a lower bound, not the optimum. Where SINTEF's record is above K, the record may
still be optimal; a stronger bound or an exact method would be needed to show it. The greedy clique search may miss
larger cliques. SINTEF's records are taken as published; they are not re-checked here. Results will be reported in
full, including predictions that fail.
