# bkswatch: expectations written before `bkswatch-v1` ran (2026-11-02 ~04:40 UTC)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.

**Why.** On 2026-10-28 CVRPLib switched to automatic best-known-solution (BKS) publishing: solutions are verified on
submission and announced in a daily digest. CVRPLib's VRPTW BKSs are kept under the DIMACS convention (each arc
truncated to 0.1). `vrptwd3/` found that 82 of the 300 Gehring-Homberger BKSs, as read on 2026-10-30, arrive late
somewhere when travel times are computed in double precision, and `vrptwlb/` showed that the R1_10_1 BKS (95 routes)
uses fewer routes than any double-precision solution can (bound 100). The digest of 2026-11-01 announced the first
VRPTW improvements since then: C1_10_9 (40,278.7, Arhan Canli, Quantavane), R1_10_1 (52,982.0), R1_10_5 (50,365.5)
and R1_10_9 (49,088.1) (all three Jean-Michel Landry, UQAM). This run asks whether new BKSs keep the same pattern.

**Method.** `bkswatch.py` downloads all 356 VRPTW BKS files again (2 s apart, into a fresh folder, never from a cache)
and checks each with the unchanged `vrptwd/double_check.py` from tag v0.3.4, under DIMACS and in double precision.
It compares each with the reference rows published in `vrptwd3/results.json` (Homberger, read 2026-10-30) and
`vrptwd/results.json` (Solomon), and with the double-precision fleet bound K in `vrptwlb/bounds.csv`. A BKS has
*changed* if its route count or its file cost differs from the reference. Before writing this we read only the
announcement text (names and values); no new BKS file was opened.

**Predictions** (scored by `score_w()` in `bkswatch.py`):

| | Prediction | Basis | Our odds |
|---|---|---|---|
| W0 | All 356 files download and parse; every BKS is feasible under DIMACS with the cost in its file. | Every earlier read did this; CVRPLib now verifies on submission. | 90% |
| W1 | C1_10_9, R1_10_1, R1_10_5 and R1_10_9 have changed, each to its announced value or lower. | The announcement. | 90% |
| W2 | The new R1_10_1 BKS uses fewer than 100 routes and is late somewhere in double precision. | Its predecessor used 95 routes, below the double-precision bound of 100; a distance-only DIMACS search has no reason to add routes. | 85% |
| W3 | At least 2 of the new C1_10_9, R1_10_5 and R1_10_9 BKSs are on time in double precision. | All three predecessors were (R1_10_5 with zero slack); all 13 improvements of 2026-10-23 were. | 70% |
| W4 | Each of the four new BKSs uses the same number of routes as the one it replaced (90, 95, 92, 91). | Improvements found by re-optimising parts of the old solution usually keep its routes. | 60% |
| W5 | Apart from these four, at most 3 other BKSs differ from the reference. | The update entries we read (2026-10-27 to 2026-11-01) announce no other VRPTW change; a new digest may add a few. | 80% |

**Reported, not predicted:** for every changed BKS, its late arrivals and largest lateness in double precision, its
double-precision distance, whether it is below K, and, where `double_check.py` has SINTEF's record, how it compares.

**Limits stated in advance.** One read of each file. DIMACS-feasible and late in double precision is not an error:
CVRPLib's VRPTW BKSs are defined under DIMACS. Comparisons with SINTEF's records are only meaningful in double
precision. Values from the announcement are as printed; the files are what is checked.
