# stfleet (mstfleet 0.2) on XLTW-Test: graded against its pre-registration

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Text CC BY 4.0.
Graded 2026-11-24 from `results.json` in this folder (job `xltw-stfleet-v1`, run 2026-11-23 09:03-11:09 UTC on one CPU,
peak memory 0.05 GB; all 11 unit tests passed). Predictions: `PREREG.md` (published 2026-11-17, before any run).

## Predictions and outcomes

| id | prediction | p | outcome | value |
|---|---|---|---|---|
| S0 | gate: tests pass, >= 30 of 33 finish, `unverified` and `above_ub` empty | 0.75 | **true** | 33 of 33 finished; 0 unverified; 0 above a known fleet |
| S1 | above K* on at least 1 instance | 0.55 | **true** | 17 instances |
| S2 | above K* on at least 5 instances | 0.30 | **true** | 17 instances |
| S3 | above K* on one of n1048, n1514, n2867, n5902 | 0.35 | **true** | all four |
| S4 | above 0.1's whole-day bound on at least 10 instances | 0.50 | **true** | all 33 |
| S5 | the Lagrangian lam raises the bound on at least 3 instances | 0.35 | **true** | 23 instances |
| S6 | best stretch is not the whole day on at least half | 0.45 | **true** | 33 of 33 |
| S7 | n1048's bound at least 4 | 0.20 | **true** | 4 |
| S8 | sum of max(K*, bound) >= 1.02 x sum of K* | 0.25 | **false** | 3,330 vs 3,275 (x1.0168) |
| S9 | peak memory at most 0.8 GB | 0.90 | **true** | 0.052 GB |
| S10 | a known fleet proven minimal | 0.04 | **false** | none |

Brier score (mean of (p - outcome)^2 over the 11 predictions): **0.261** (always guessing 0.5 would score 0.250).
We were too pessimistic: nine of eleven came true, including four we gave 35% or less.

## What it means

- **The bound is real and new on these instances.** It is above our earlier best lower bound K* (our implementation
  of the classical clique, capacity and energetic-reasoning bounds, `xltwen/`) on 17 of 33 instances, by 1 to 12
  vehicles. Every one of the 17 increases comes with a certificate in `cert/`. The largest are n8575 (15 to 27),
  n6305 (207 to 215), n6884 (138 to 145), n7854 (17 to 22) and n4535 (91 to 95).
- **It closes little of the gap.** On the 27 instances where we know a fleet, the new bound closes at most 1/6 of
  the gap between K* and the fleet (n1048: 3 to 4 against 9; n1234: 27 to 28 against 33). The median is 0. Counted
  by hand from `results.json`: the 27 known fleets total 3,578 vehicles, K* totals 2,403 and max(K*, bound) totals
  2,432, so 29 of the 1,175-vehicle gap (2.5%) is closed. n2867 is still 7 against 29 and n5902 7 against 45.
- **So waiting and idle time do not explain the gap.** Forced waiting between customers and idle time at the ends of
  a stretch were charged on top of plain travel, and the gap barely moved. Either the searches are far from
  optimal, or the missing piece is something this family of bounds cannot see. Route-based LP bounds
  (`cgfleet/`, `ngfleet/`) and the fleet search `tmatch/` are queued to tell these apart.
- **The best stretch is never the whole day** (33 of 33): the binding part of every instance is a busy part of the
  day. The best side is the start of the day on 23 instances and the end on 10.

## Independent check

`stcheck/` (queued as `xltw-stcheck-v1`) re-checks all 33 certificates with code that shares nothing with
`stfleet.py`. It has its own parser, exact integer travel times and its own Prim. Its tests also check the bound
against exact minimum fleets on tiny instances. Until it reports, the bounds are confirmed only by stfleet's own
`verify()` and its 11 tests.
