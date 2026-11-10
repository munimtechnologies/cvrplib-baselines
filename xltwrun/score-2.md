# xltwrun: re-scored after the clean re-runs (merge 2). Three of six predictions held

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0.

Scored 2026-11-10. The predictions G0-G5 are the ones pre-registered in [expectations.md](expectations.md) on
2026-11-04 and first scored in [score.md](score.md); their wording is unchanged. Merge 2 differs from merge 1 in one
way, fixed before the re-runs were read ([rerun-attempt-2.md](rerun-attempt-2.md)): the seven instances flagged for
container pauses (n7037, n8389, n8575, n9160, n9363, n9571, n10001) were replaced by clean re-runs of the same solver,
seed and limit, and each replacement was made whether the re-run came out better or worse. Job `xltwmerge2-v1` ran
`xltwrun.py --merge` mechanically; files in [merge2/](merge2/).

| | prediction (short) | merge 1 ([score.md](score.md)) | merge 2 |
|---|---|---|---|
| G0 | every run counts (complete, on time, matching Cost line, no SIGKILL, none below K) | did not hold (3 SIGKILLs) | **held** (100 of 100 counted, no SIGKILL, none below K) |
| G1 | the solver stops by itself on all 100 runs (no SIGTERM) | did not hold (3 SIGTERMs) | **held** (0 SIGTERMs) |
| G2 | 20-55 of the 100 runs end at exactly K vehicles | did not hold (6) | did not hold (6) |
| G3 | at most 5 of the 33 KC = 1 instances end at K | held (0) | held (0) |
| G4 | median (vehicles - K) / K at most 10% | did not hold (51.5%) | did not hold (50.5%) |
| G5 | every run's peak memory at or below mem_est | did not hold (67 over) | did not hold (67 over) |

## What changed and what did not

- **The three SIGKILLs and SIGTERMs were the host, as diagnosed.** With clean re-runs of the paused instances,
  every one of the 100 runs stopped by itself and counted. G0 and G1 now hold.
- **Fleet:** 18,529 -> 18,388 vehicles in total (-141), against K = 11,298 and the stronger bound K* = 13,961
  (31.7% above K*). All seven re-runs used fewer vehicles than the paused runs they replaced: n8575 156 -> 103,
  n9160 394 -> 365, n9363 484 -> 458, n10001 281 -> 267, n8389 404 -> 393, n9571 315 -> 309, n7037 647 -> 645. So
  pauses cost fleet, not only time.
- **The main weakness is unchanged:** fleet search. Still only 6 runs reach K, all with KC > 1, and the median run
  is about 50% above K. On the 33 instances where capacity never binds, the gap to the bounds is large.
- **Memory estimate:** unchanged (67 runs over the pre-registered estimate). The refit 0.17 + 4.7 (n/10,000)^2 GB
  from score.md still covers every peak.

Limits as before: time limits divided by 30, one seed, one run per instance, shared machines. K is a lower bound, not
a known optimum. "Held" means held as the pre-registered sentence reads; merge 2 is a second, declared reading of the
same study, not a new pre-registration.
