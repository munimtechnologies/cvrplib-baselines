# xltwtest: scored

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0.
Scored on 2026-11-04 (UTC) from the job `xltw-test-bounds-v1` (run 2026-11-02 19:35 to 20:21 UTC, one CPU, 1.5 GB
limit), against [../xltwlb/predictions-xltw-test.md](../xltwlb/predictions-xltw-test.md), which was fixed on
2026-10-31, before CVRPLib released XLTW-Test. The verdicts below are the ones the code computed; nothing was
re-scored by hand.

## What was read

| | |
|---|---|
| archive | `XLTW-Test.7z` from the challenge page, 3,754,859 bytes, SHA-256 `9635b9fa...4f631`, Last-Modified 2026-11-02 17:40:09 GMT, downloaded 2026-11-02 19:37 UTC |
| files | 100, all instances, none unparsed |
| sizes | `XLTW-Test-n1048` to `XLTW-Test-n10001`: 1,047 to 10,000 customers, the same 100 sizes as CVRPLib's XL set; 416,241 customers in total |
| format | VRPLIB: `NAME`, `COMMENT`, `TYPE : VRPTW`, `DIMENSION`, `EDGE_WEIGHT_TYPE : EUC_2D`, `CAPACITY`; sections `NODE_COORD_SECTION`, `DEMAND_SECTION`, `SERVICE_TIME_SECTION`, `TIME_WINDOW_SECTION`, `DEPOT_SECTION`; no `VEHICLES` line; integer coordinates in all 100 |

The file list with sizes and hashes, and per-instance statistics (capacity, total demand, horizon, service times,
window widths), are in [manifest.json](manifest.json). No instance data is copied into this repository.

## Verdicts

| | Prediction (fixed 2026-10-31) | Odds | Verdict |
|---|---|---|---|
| P1 | Every instance bounded in the challenge's convention and in 'double', no error, no unservable customer, within 1 GB and 30 minutes in total | 70% | **did not hold**: no error and no unservable customer, peak 0.54 GB, but bounding took 2,562 s (all three conventions), over the 1,800 s limit |
| P2 | KB > KC (the bin-packing bound beats the capacity bound) on at least one instance | 45% | **did not hold**: KB = KC on all 100 |
| P3 | In 'round', KT > KB (the time-window bound binds) on at most a quarter of the instances | 75% | **did not hold**: it binds on **38 of 100** |
| P4 | K in 'round' equals K in 'double' on at least three quarters of the instances | 75% | **held**: 89 of 100 |

Every clique was confirmed in exact arithmetic (`unverified_cliques` is empty).

## What the misses say

**P1.** The time was spent on a few instances with dense time-window conflicts. `XLTW-Test-n9363` alone took about
706 s for the three conventions (its incompatibility matrix is dense and the greedy clique search is long), and
n5526, n7037 and n3640 took 255 s, 172 s and 144 s. The synthetic 10,000-customer instance used to set the 30-minute
expectation had sparse conflicts. In one convention only (what a solver needs) the whole set takes roughly a third of
the time.

**P3 is the interesting one.** On CVRPLib's classic VRPTW sets the time-window bound binds on 14 of 356 instances, all
with the tightest windows. On XLTW-Test it binds on 38 of 100:

- **33 of the 100 instances have capacity that never binds**: in every one of them the capacity equals the total
  demand exactly, so one vehicle could carry everything (KC = 1). Some have unit demands and a capacity of exactly
  the number of customers (n2214, n2541, n4535). For these 33 the fleet
  is decided by time alone. On 32 of them the clique bound is above 1 (from 3 to 243 vehicles under 'round'); on
  n3147 it is 1, so no useful bound is known.
- On 6 instances with KC > 1 the time-window bound is still higher: n1281 (KC 90, K 132), n2494 (37, 43), n3241
  (137, 151), n3888 (204, 460), n4635 (198, 201) and n9363 (209, 253).

So about a third of the test set are pure time-window fleet problems, where a vehicles-first solver gets no help from
capacity, and where the classical clique bound may be far below the true minimum (it ignores route length).

**P4 held, but the 11 exceptions are large.** Where 'round' and 'double' disagree, 'round' is always lower, and by a
lot: n9363 253 against 408, n3640 243 against 333, n1281 132 against 195, n3007 158 against 186, n5406 136 against
168. Integer data with nearest-integer arcs (the challenge's rule) lets many more pairs of customers share a route
than exact Euclidean times do. A solver or checker that works in double precision on these instances would be
solving a much harder problem than the one the challenge scores; on n9363 its fleet could not go below 408 vehicles
while 'round' allows 253. DIMACS truncation (one decimal) sits in between (n9363: 363).

## Reported, not predicted

| | |
|---|---|
| K / KC, all 100 ('round') | K = KC on 62; K > KC on 38 (the 32 time-bound KC = 1 instances, n3147 aside, plus the 6 above) |
| largest K | n3888: 460 vehicles ('round'), 507 ('double') |
| smallest K | n3147: 1 (a bound, not a fleet) |
| 'round' K below 'dimacs' K | the same 11 instances |
| customers whose window spans the whole horizon | 0%, 20% or 40% per instance (three levels, as the share in `manifest.json` shows) |
| largest demand | 1, 10 or 100 per instance |
| time in 'round' only | about a third of the 2,562 s; n9363 about 235 s |

## Limits

These are classical bounds (Martello-Toth L2 for capacity; a greedy clique of pairwise incompatible customers, after
Kontoravdis and Bard, 1995). A larger clique may exist, and both bounds ignore route duration, so the true minimum
fleet can be well above K, most likely on the 33 instances where capacity never binds. XLTW-Test is a development set
that the organisers will drop when the challenge starts; the official XLTW instances may differ.

Raw output: [results.md](results.md), [results.json](results.json), [manifest.json](manifest.json),
[cliques.json](cliques.json) (every clique, by instance and convention).
