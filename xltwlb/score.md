# xltwlb: scoring of the regression check (written 2026-10-31 ~11:20 UTC, after `xltwlb-xcheck-v1` finished)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0.

Run: `xltwlb-xcheck-v1`, 2026-10-31 09:08 to 09:12 UTC, one CPU, 1 GB. `xltwlb.py` is the `vrptwlb/` fleet-bound code
rewritten for CVRPLib's XLTW-Test set (1,000 to 10,000 customers): the incompatibility matrix is built in row blocks,
the Martello-Toth L2 bin-packing bound (KB) is added, two customers whose demands together exceed the capacity count
as incompatible, and a third travel-time convention, 'round' (nearest integer, CVRPLib's CVRP rule), is added.
`compare.py` ran it on the same 356 CVRPLib VRPTW instances as `vrptwlb/` and compared it with the published
`vrptwlb/bounds.csv` and `vrptwlb/cliques.json`, read from this repository. The unit tests of both scripts passed first.
Predictions: [expectations.md](expectations.md), written before the run. Raw output: [results.md](results.md),
[results.json](results.json), [tally.json](tally.json), [cliques.json](cliques.json).

These are classical bounds (Kontoravdis and Bard, 1995; L2 from Martello and Toth, 1990). Afifi, Guibadj and Moukrim
(CPAIOR 2014) give stronger ones. This check shows that the rewrite gives the same answers as before; it is not a new
result.

## Verdicts

| | Prediction | Our odds | Verdict | What happened |
|---|---|---|---|---|
| C0 | All 356 computed in all three conventions with no errors, every clique confirmed exactly, no unservable customer. | 85% | **held** | No run error, no missing convention, no unverified clique, no unservable customer. |
| C1 | KC, KT (double) and KT (DIMACS) equal the published values on all 356, and the double and DIMACS cliques are the same customer lists. | 85% | **held** | 0 differences in KC, in KT and in the clique lists. |
| C2 | KB = KC on all 356. | 95% | **held** | KB above KC on none. |
| C3 | The 'round' K differs from the double-precision K on at most 10 of 356. | 65% | **held** | 7. |
| C4 | Under 20 minutes, peak under 0.5 GB. | 85% | **held** | Bounds 49.1 s in total (whole step 76 s); peak 0.061 GB. |

All five held. `xltwlb.py` can be used on XLTW-Test once it is published.

Sizing, from the earlier `xltwlb-tests-v1` run (synthetic instances, all three conventions): 10,000 customers took
26 s with a peak of 0.30 GB, 5,000 customers 4 s and 0.15 GB.

## Found on the way (reported, not predicted)

**Under 'round' the time-window bound stops binding on the large tight-window instances.** The round K differs from
the double-precision K on 7 instances and from the DIMACS K on 4. Every one is a tightest-window R1 instance, and in
every case the round K is lower:

| instance | K double | K DIMACS | K round | KC |
|---|---|---|---|---|
| R101 | 18 | 18 | 17 | 8 |
| R102 | 17 | 16 | 16 | 8 |
| R1_2_1 | 20 | 19 | 18 | 18 |
| R1_4_1 | 40 | 36 | 36 | 36 |
| R1_6_1 | 59 | 56 | 54 | 54 |
| R1_8_1 | 80 | 75 | 72 | 72 |
| R1_10_1 | 100 | 91 | 91 | 91 |

At every Gehring-Homberger size, R1's `_1` instance falls back to the capacity bound under 'round' (on R1_10_1 the
time-window clique shrinks from 100 customers in double precision to 62). Rounding to the nearest integer can shorten
an arc by up to 0.5, against 0.1 for DIMACS truncation, so more pairs of customers become compatible. On some other
instances the round KT is a little higher than the double one (RC1_10_6: 29 against 27), because rounding can also
lengthen an arc, but there it stays below KC and does not change K.

What this suggests for the challenge, which ranks by vehicles first: if XLTW uses nearest-integer rounding, the
time-window bound will matter on fewer instances than in double precision, and the capacity bound will settle the
fleet more often. That is an inference from the classic sets, not a forecast for XLTW, whose windows are new.

**The 13 VRPTW improvements CVRPLib published on 2026-10-23** (Takahashi, Kumamoto, Shin, Nomura and Ono, Institute
of Science Tokyo: C1_10_9, R1_10_2 to R1_10_4, R1_10_6 to R1_10_10, RC1_10_3, RC1_10_4, RC1_10_6, RC1_10_10) are
among the BKSs that `vrptwd3/` checked: all 13 are on time in double precision, and each uses exactly KC routes (91
for R1, 90 for C1 and RC1), so none can use fewer vehicles. Their tightest slack is 0.04 (C1_10_9).

## Hand checks

- KC for R1_10_1 is 91 and its DIMACS BKS uses 95 routes, so the round K (91) does not contradict any published
  solution; nor does any other round K (all are at or below the DIMACS K).
- `tally.json` lists no instance where the round K is above either other convention's K.
- The 13 improvements: costs in `vrptwd3/results.md` match the values on CVRPLib's updates page (for example R1_10_2,
  48,189.8; RC1_10_10, 43,518.8).

## Limits

Agreement with `vrptwlb/` on these 356 instances only. The capacity-pair rule and KB are not exercised by these sets,
whose demands are small next to the capacity; their unit tests cover them. K is a lower bound found by greedy clique
search, never too high (every clique is re-checked exactly) but possibly too low.
