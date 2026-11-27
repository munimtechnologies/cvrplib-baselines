# bsfleet: route-level fleet lower bounds on the busy stretches of XLTW-Test

By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name; no human expert has checked it
yet. Apache-2.0.

stfleet (`../stfleet/`) found that on every capacity-free XLTW-Test instance the binding part of the day is a busy
stretch, never the whole day. bsfleet takes the customers whose whole service must fall inside such a stretch and
bounds the number of vehicles they need with column generation over whole routes (ngfleet's exact ng-route pricing;
Farley's bound `fleet >= sum(pi) / P*`). Cutting every vehicle's route down to those customers keeps it feasible
(nearest-integer travel times, service times >= 1), so the bound holds for the whole instance.

* `bsfleet.py`: the study (`python bsfleet.py --data-dir /data --out-dir /out`).
* `test_bsfleet.py`: compares every bound with the exact minimum fleet of small random instances (brute force), and
  checks the greedy covers and the stretch selection.
* `fetch.py`: fetches mstfleet, ngfleet, cgfleet, xltwlb and stfleet/results.json, and the XLTW-Test instances.
* `PREREG.md`: the method and the predictions, fixed before the run.

Each certificate in `cert/` lists the stretch, its customers (1-based), the integer duals `pi_int` and `pstar`; one
run of `ngfleet.price_ng` (or `cgfleet.price` for route_set `r2`) on those customers re-checks it.
