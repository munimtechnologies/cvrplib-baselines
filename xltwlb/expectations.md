# Expectations written before xltwlb-xcheck-v1 ran (2026-10-31 ~07:00 UTC)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.

**Why.** `xltwlb.py` is the version of the `vrptwlb/` fleet-bound code rewritten for CVRPLib's XLTW-Test set
(1,000 to 10,000 customers, VRPLIB or Solomon files). It builds the incompatibility matrix in row blocks, adds the
Martello-Toth L2 bin-packing bound (KB), treats two customers whose demands together exceed the capacity as
incompatible, and adds a third travel-time convention, 'round' (nearest integer, CVRPLib's CVRP rule). Before it is
trusted on instances nobody has bounded, it should give the known answer where there is one. This job runs it on the
same 356 CVRPLib VRPTW instances as `vrptwlb-bounds-v1` and compares it with the published `vrptwlb/` results
(bounds.csv, cliques.json). It is a regression check, not a new result. The round-convention bounds are new numbers,
but only a side product.

**Method.** `compare.py` imports `xltwlb.py`, reads instances 380 to 735 from the cached CVRPLib copies (downloads
any that are missing, 2 s apart), and runs `bound_one` in all three conventions. Then it downloads the published
`vrptwlb/bounds.csv` and `vrptwlb/cliques.json` from munimtechnologies/cvrplib-baselines (retrying while they are not
there yet) and compares. The unit tests of both scripts run first.

**Predictions** (scored by `score_c()` in `compare.py`):

| | Prediction | Basis | Our odds |
|---|---|---|---|
| C0 | All 356 instances computed with no errors in all three conventions, every clique confirmed by the exact check, no unservable customer. | `vrptwlb-bounds-v1` did this in double and DIMACS; every service time is at least 10, so 'round' is computed too. | 85% |
| C1 | KC, KT (double) and KT (DIMACS) equal the published values on all 356, and the double and DIMACS cliques are the same customer lists. | Same incompatibility test and the same clique search with the same seed. Demands in these sets are small next to the capacity, so no pair is incompatible on capacity alone, and the matrices should be identical. | 85% |
| C2 | KB = KC on all 356. | L2 can exceed KC only when some demands are above half the capacity. | 95% |
| C3 | The 'round' K differs from the double-precision K on at most 10 of 356 instances. | Rounding moves each arc by at most 0.5 either way, so it should matter only on the tightest windows, as DIMACS did (6 instances). | 65% |
| C4 | The whole bound computation takes under 20 minutes and peaks under 0.5 GB. | `vrptwlb-bounds-v1` took 65 s for two conventions. | 85% |

Only reported, not predicted: the round-convention K per instance and how it compares with double and DIMACS.

**If C1 fails,** `xltwlb.py` is not used on XLTW-Test until the difference is explained. **Limits:** passing shows
agreement with `vrptwlb/` on these instances only. The capacity-pair rule and KB are not exercised by these sets
(their unit tests cover them).
