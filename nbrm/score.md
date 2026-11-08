# nbrm: score (job nbrm-v2, 2026-11-08)

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. CC BY 4.0.

Pre-registration: [expectations.md](expectations.md) (sha256 `c528421c…5108`, checked by the job before it ran).
Addendum: [addendum-v2.md](addendum-v2.md). Raw output: [results.json](results.json), [results.md](results.md),
`runs/N1-N4.log.txt` (every `incumbent_ms` line the route minimiser printed) and `runs/N1-N4.sol` (the written
solutions). The method and its code are not ours: Nagata & Bräysy's route-minimisation heuristic (Operations Research
Letters 37, 2009), open C implementation by Astronomax (MIT), commit `89d4c05`, with one patch, the challenge's
nearest-integer rounding of each arc.

## Verdict

**2 of the 5 scored predictions held (N4, N5), and the gate N0 held. N1, N2 and N3 did not hold.** On all four
capacity-free XLTW-Test instances, the route minimiser ended **exactly one vehicle above** MV2's best valid PyVRP
run (34/66/109/26 vs 33/65/108/25; 235 vs 231 in total, against K* = 173). The pre-registered reading of N1-N3
was "the PyVRP loop's gap to K* is mostly the search, not the instances". This run does not support that. A
method built only to remove routes did not get below the PyVRP loop on any of the four instances.

| run | instance | n | K* | PyVRP best (whole T(n)) | route minimiser (T(n)/2 CPU) | final count first reached at CPU s | share of T(n) | CPU s | wall s | peak GB | valid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| N1 | XLTW-Test-n1234 | 1,233 | 27 | 33 | **34** | 131.7 | 5.9% | 1,109.0 | 1,112.1 | 0.043 | yes |
| N2 | XLTW-Test-n1421 | 1,420 | 47 | 65 | **66** | 109.8 | 4.3% | 1,278.1 | 1,280.7 | 0.053 | yes |
| N3 | XLTW-Test-n1608 | 1,607 | 81 | 108 | **109** | 1,116.4 | 38.6% | 1,446.1 | 2,153.5 | 0.063 | yes |
| N4 | XLTW-Test-n1841 | 1,840 | 18 | 25 | **26** | 342.5 | 10.3% | 1,656.2 | 1,743.0 | 0.066 | yes |
| total | | | 173 | 231 | **235** | | | | | | |

| prediction | text (verbatim, short) | result |
|---|---|---|
| N0 (gate) | patch once, build, smoke passes, N1-N4 end by themselves with valid solutions | **held** (patch matched 1×; Release build; smoke 6 vehicles, valid; all four exit 0, all valid under `check_exact` "round") |
| N1 | at most as many vehicles as the best valid PyVRP run, on each of the four | **did not hold** (+1 on all four) |
| N2 | strictly fewer on at least three of the four | **did not hold** (0 of 4) |
| N3 | the four together use at most 221 | **did not hold** (235) |
| N4 | at most one of the four reaches its K* | **held** (none does; gaps 7, 19, 28, 8) |
| N5 | every run ≤ L + 60 s CPU and ≤ 0.5 GB peak | **held** (CPU within 0.2 s of L; peak ≤ 0.066 GB) |

## What else the run shows (reported, not predicted)

- **Fast early, then stuck.** On N1 and N2 the route minimiser reached its final count after about 2 minutes of CPU
  (5.9% and 4.3% of T(n)) and then found nothing better in the remaining ~16-19 minutes. On N1 it was at 37 routes
  after 8.3 s. The PyVRP loop needed its whole fleet phase to get one vehicle further. With the default settings
  (`k_max` 5, `n_near` 100, `i_rand` 1000), the ejection search seems to stall one route above what PyVRP's
  penalty-based search finds on these instances. We did not test other settings, and this is one seed.
- **Distances are not comparable.** The method does not shorten routes (rounded distances 95,444 / 140,789 / 117,814
  / 102,392), so its solutions would need a separate distance phase in any entry.
- **Host pauses did not matter here.** The Blade paused the job's container four times (18:25-18:34, 18:37-18:39,
  18:47-18:49 and 18:57-18:59 UTC on 2026-11-08, about 13 minutes in all, each on low Windows memory). Three fell in
  N3 (wall − CPU = 707 s) and one in N4 (87 s). The code stops on process CPU time (`clock()`), so each run still got
  its full L. The pre-registration chose that rule for this reason.

## What this changes

- The Nagata-Bräysy hybrid planned for `xltw-solver` 0.2.0 (route minimiser for the fleet, then PyVRP for distance)
  is **dropped as pre-registered**. On these instances it would start one vehicle behind.
- It does not show that the K* bounds are tight. Both methods stop 7-28 vehicles above them. Closing that gap is
  still open; the next fleet study should test a different idea rather than re-tune this one.
- Limits: one seed, four instances, default parameters, one machine. This is a fleet-phase study, not a challenge
  run (the code writes its solution only at the end).
