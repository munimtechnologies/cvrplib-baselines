# kmatch pilot readout: the path-cover fleet bound never beats K* on XLTW-Test

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.

Pilot plan and guesses: [pilot.md](pilot.md) (published before the job ran, commit `df95fd8`). Raw output:
[results.json](results.json), [results.md](results.md). Job `kmatch-pilot-v1`, 2026-11-09 11:24-11:32 UTC on the
Blade, 1 CPU, peak 0.17 GB container memory; unit tests passed before the run (exit 0).

## Result in one line

On all 100 XLTW-Test instances the assignment (path-cover) bound KM = max(n - M, 1) is **at or below** the existing
fleet lower bound K* = max(clique bound, energetic bound). It never moves K*, so the 7-28 vehicle gaps between MV2's
best fleets and K* on the four capacity-free test instances are not explained by a K* that this relaxation could
tighten. This is a negative result for this bound, not a statement about how tight K* is.

## Validity first

- 100 of 100 instances done, no errors, all coordinates integer (rounded travel times exact in float64), no
  customer unservable.
- All 80 exactly checked part-a solutions were checked: every consecutive customer pair of every route is an arc of
  the graph, and KM never exceeds any solution's route count. No instance was flagged invalid.

## The guesses (calibration only; this was a pilot, not a pre-registered study)

| | guess | how sure | outcome |
|---|---|---|---|
| g1 | KM <= K* on all four nbrm instances | 0.60 | **held** (KM = 1 on all four; K* 27, 47, 81, 18) |
| g2 | KM > K* on at least one of the 33 capacity-free instances | 0.35 | **did not hold** (0 of 33) |
| g3 | no validity flag on any of the 80 solutions | 0.95 | **held** |
| g4 | the matching closes at least one cycle on at least 50 of 100 instances | 0.70 | **held** (100 of 100) |

Mean Brier score 0.094 over the four guesses.

## What the numbers show

- **Cycles kill the bound when windows are wide.** On 60 instances KM = 1 (the maximum matching leaves at most one
  customer without a successor); on all 100 it closes cycles. Where customer i may precede j and j may precede i, the assignment
  relaxation pairs them in a loop that no route can use.
- **It beats the clique bound, but not the energetic bound.** KM is larger than the clique bound KC on 10 instances:
  nine capacity-free ones where KC = 1 (n2401 95, n2541 81, n3640 85, n5288 68, n2821 52, n3007 34, n6305 30,
  n3408 24, n5061 8) and n3888 (KM 458 against KC 204). On every one of them the energetic busy-period bound in K*
  was already higher (for example n3888: K* 460; n2401: K* 119).
- **Closest calls:** n1748 (KM 142, K* 143) and n3888 (KM 458, K* 460). Both have narrow windows, few cycles (14
  and 33) and low arc density.
- Total: sum of K* = 13,961; sum of max(K*, KM) = 13,961.

## What this means for the VRPTW Challenge work

The pilot said: if KM never beats K*, look elsewhere. So:

- No pre-registered kmatch2 study. A cycle-free strengthening (for example adding subtour cuts to the assignment
  problem) is possible, but on the instances where KM is far from 1 the energetic bound is already ahead, and on the
  capacity-free instances with wide windows a cycle-breaking bound would have to recover dozens of vehicles from
  KM = 1. That is a research project, not a quick step, and nothing here suggests it would pay off.
- The four capacity-free test instances' gaps (best fleets 33, 65, 108, 25 against K* 27, 47, 81, 18) remain open:
  either the search or K* is loose, and this pilot only rules out one cheap way of tightening K*.

Method prior art: Dantzig & Fulkerson (1954), minimum fleet for fixed schedules; the assignment relaxation for VRPTW
fleet size is classical. K* follows Kontoravdis & Bard (1995) and Afifi, Guibadj & Moukrim (2014). What is new here is
only the per-instance numbers on XLTW-Test (released by CVRPLib on 2026-11-02).
