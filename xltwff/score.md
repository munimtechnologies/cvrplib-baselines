# xltwff: scored (2026-11-07). Gate failed, so H1-H5 are untestable

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Text CC BY 4.0.

Pre-registration: [expectations.md](expectations.md) (H0-H5, fixed on 2026-11-06 before any run). Raw outputs: part a
([part-a-note.md](part-a-note.md), [results-a.json](results-a.json); job `xltwff-a-v1`, Blade, no pauses) and part b
([part-b-note.md](part-b-note.md), [results-b.json](results-b.json), [results-b.md](results-b.md), [logs-b/](logs-b/),
[sols/](sols/); job `xltwff-b-v1`, Blade). These verdicts are written out by hand from those files. The
pre-registered merge (`ffrun.py --merge results-a.json,results-b.json --ref ../xltwfull/results.json`) is queued as
job `xltwscore-v1`, and its output will be added here.

## Verdicts

| | prediction (verbatim) | verdict |
|---|---|---|
| H0 | (gate) The patch applied (both lines exactly once), the build is offline with the pinned wheels, the network is unreachable during the runs, and each of H1-H4 and each of xltwfull's F1-F4 has a valid run (xltwfull's definition). If H0 fails, H1-H5 are untestable. | **did not hold**: all four 0.8 runs are valid, but xltwfull's F2 is not (both of its tries were frozen by host pauses; [../xltwfull/score.md](../xltwfull/score.md)) |
| H1 | The four 0.8 runs together use at most as many vehicles as the four 0.5 runs. | untestable |
| H2 | At least one of the four 0.8 runs uses fewer vehicles than its 0.5 run. | untestable |
| H3 | The four together save at most 4 vehicles against the 0.5 runs. | untestable |
| H4 | On every instance where both use the same number of vehicles, the 0.8 run's distance is at most 1% longer. | untestable |
| H5 | Every 0.8 run's peak memory is at most 0.6 GB, and the watchdog never fires. | untestable |

We wrote the gate to need all of xltwfull's runs, so one paused baseline run voids the whole comparison. We leave
it that way.

## What the runs show anyway (descriptive, not verdicts)

| instance | T(n) s | 0.5 (xltwfull) | 0.8 (xltwff) | distance 0.5 | distance 0.8 | K* | 0.8 final count first printed at s |
|---|---|---|---|---|---|---|---|
| n1234 | 2,219.4 | 34 | **33** | 83,690 | 84,722 | 27 | 1,203.2 |
| n1421 | 2,556.0 | 65 (invalid: paused) | 65 | 130,249 | 130,271 | 47 | 1,309.4 |
| n1608 | 2,892.6 | 108 | 108 | 112,655 | 112,903 (+0.22%) | 81 | 1,193.0 |
| n1841 | 3,312.0 | 25 | 25 | 84,464 | 84,744 (+0.33%) | 18 | 228.9 |

- On the three instances where both runs are valid, the 0.8 split used 166 vehicles against 167: one fewer, on
  n1234, at 1.2% more distance. Where the counts are equal, the distance is at most 0.33% longer. Peak memory was
  0.16-0.27 GB, and the watchdog never fired. Had the gate passed, H1-H5 would all have held on these numbers.
- But the effect is small. Thirty more percent of the time bought 1 vehicle out of 166, against a gap of 40 to
  K* (126). The split is not what limits this fleet search.
- **The re-run rule worked as designed.** The host paused `xltwff-b-v1` for about 93 s (03:35:09-03:36:42 UTC, from
  the runner's log) during H4's first try. The harness saw the gap, discarded that try and ran H4 again from the
  start (03:48-04:43 UTC, no pauses). The step's wall time (9,158 s, against 5,853 s for the two counted runs) shows
  the extra try. The counted H4 run never went more than 0.055 s between polls.

## What next

Keep 0.8 as a candidate default (it never cost more than 0.33% distance here), but the next fleet idea must change
the search itself. The fixed-cost search tried in parallel did worse ([../xltwfc/score.md](../xltwfc/score.md)).
Route-elimination moves aimed at the fleet (ejection pools, Nagata & Braysy 2009) are next.

Limits: one seed, four instances, stopped on the wall clock on a shared machine. K* is a lower bound, not a known
optimum.
