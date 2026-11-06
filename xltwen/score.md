# xltwen: scored (time-based fleet lower bounds on XLTW-Test)

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. CC BY 4.0.

Pre-registration: [expectations.md](expectations.md) (published 2026-11-06 before the job ran, commit d330737).
Job `xltwen-v1` ran on 2026-11-06 from 08:31 to 08:40 UTC (one CPU, python:3.12, PyVRP 0.14.1 only for reading).
Raw output: [results.json](results.json), [results.md](results.md) (one row per instance), [progress.jsonl](progress.jsonl).
`xltwen.py` SHA-256 `74f1b9f0a9c8625ccfeedef03f2fb720d9ab752ec8f4c2453be6ebe44a1f6345`.

## Predictions

| | Prediction (verbatim) | Result | |
|---|---|---|---|
| E0 | (gate) All 100 instances bounded without error; all inputs integral and every service time >= 1; no unservable customer; every winning interval verified in int64; E <= the part-a vehicles on all 80; all 80 part-a solutions downloaded, simulated on time, cover every customer once, have the published number of routes, and pass the busy-period check in all three variants. | 100 bounded, 0 errors, 0 non-integral or zero-service, 0 unservable, 0 unverified intervals, 0 instances with E above the vehicles used, 80 of 80 solutions checked, 0 bad, 0 missing | **held** |
| E1 | E > K on at least 10 of the 33 instances with KC = 1. | 26 of 33 | **held** |
| E2 | E > K on at most 10 of the 67 instances with KC > 1. | 9 of 67 | **held** (one short of the limit) |
| E3 | On n3147 (K = 1, part a used 84 vehicles), E >= 20. | E = 68 | **held** |
| E4 | Over the 27 part-a instances with KC = 1, the median of vehicles / K* is at most 3.0 (against K it is 6.1). | 1.46 (against K: 6.08) | **held** |
| E5 | On at least 5 instances, the winning variant's best bound comes from an interval shorter than the whole horizon and is strictly larger than both its duration and its compulsory-part bound. | 91 instances | **held** |
| E6 | The whole job (100 instances, three variants, 80 solution checks) takes at most 60 minutes on one CPU, with peak memory at most 1.5 GB. | 336.7 s for the bounds and checks (538 s for the whole job with setup); peak 0.52 GB inside the script, 0.45 GB by the runner | **held** |

All seven held. E1, E3, E4 and E5 held by wide margins, which says the predictions were cautious, not that the
result is surprising for this kind of bound: Afifi, Guibadj & Moukrim (CPAIOR 2014) already showed that energetic
reasoning beats clique bounds on time-window-tight instances. E2 came within one instance of failing.

## Reported, not predicted

- **The bound moves a lot where capacity never binds.** Over all 100 instances the sum of fleet lower bounds rises
  from 11,298 (K) to 13,961 (K*), +23.6%. Over the 80 part-a instances, from 7,421 to 9,050. Examples (K, then K*,
  then the vehicles in the baseline's run): n1608 7 -> 81 (113); n3147 1 -> 68 (84); n4153 5 -> 200 (238); n5774
  3 -> 98 (126); n9784 8 -> 388 (522, part b3).
- **Part a's measured gap shrinks, and no new run reaches its bound.** The median of (vehicles - bound) / bound
  over the 80 part-a runs goes from 0.474 against K to 0.303 against K*. The six runs at K are the six at K*:
  where E is higher, the runs were above it too.
- **Where the bound stays weak.** Seven capacity-free instances are not helped by E: n1048 (K* 3, 9 vehicles),
  n1514 (16, 44), n2541 (91, 133), n2867 (4, 29), n3007 (158, 190), n3640 (243, 310), n5288 (77, 144). Others
  are helped only a little: n5902 3 -> 5 (45 vehicles), n7854 4 -> 17 (62), n8575 11 -> 15 (156). On these,
  either the run is far from optimal or no simple time bound captures what limits the fleet. This study cannot
  tell which.
- **Variants.** The `in` variant (travel time charged before service) gives the best bound on 73 instances, `out`
  on 21 and `half` on 6.
- **Part b (exploratory).** E is at or below the vehicles of every part-b run too, including the frozen ones, so no
  contradiction was found there either.

## What this says and does not say

K* is a valid lower bound under the challenge's nearest-integer convention, checked against 80 exactly verified
solutions. It shrinks the measured gap of MV2's baseline on capacity-free instances from about 6 times the bound to
about 1.5 times. That makes the baseline look much less weak there, but it proves nothing about how many vehicles
are achievable. Only better solutions can close a gap from above. The interval search is heuristic, so E can only
be too low. The bounding method is published prior art (Kontoravdis & Bard 1995; Afifi, Guibadj & Moukrim 2014).
What is new is only these numbers on XLTW-Test, released 2026-11-02. Nothing here is a claim about CVRPLib's data.

## Next

- Use K* as the fleet loop's stopping point in the packaged solver (pre-register first). The loop stops at its bound,
  and K is far below anything reachable on capacity-free instances.
- Report gaps against both K and K* in the XLTW-Test report.
