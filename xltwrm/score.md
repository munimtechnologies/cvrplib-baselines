# xltwrm: scored. The plain `minimise_fleet` loop beat both alternatives

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Scored on 2026-11-02 (UTC) from the job's own tally. No verdict was changed by hand.

Expectations: [expectations.md](expectations.md), committed in `09058b4` at 10:51:00 UTC on 2026-11-02, before
the job started at 10:52:22 UTC. Job `xltwrm-v1`: PyVRP 0.14.1, 3 CPUs (one per run), 2 GB, seed 20261102,
300 s fleet budget per arm. It ran 3,695 s and peaked at 0.39 GB. The unit tests passed first. Raw output:
[results.md](results.md), [results.json](results.json), [progress.jsonl](progress.jsonl) (one line per finished
run, with the full trace), solutions in [sols/](sols/) (CVRPLib format, `Cost` = double-precision distance).

## Verdicts

| | Prediction | Result | Verdict |
|---|---|---|---|
| M0 | all 39 runs finish, on time in exact arithmetic, none below K | 39 of 39, all on time, none below K | **held** |
| M1 | eject uses no more vehicles than fleet on at least 12 of 13 | 5 of 13 | did not hold |
| M2 | eject uses fewer vehicles than fleet on at least 6 of 13 | 0 of 13 | did not hold |
| M3 | eject matches SINTEF's vehicle count on at least 4 of 13 | 1 of 13 (RC2_10_5) | did not hold |
| M4 | eject uses at least 8 fewer vehicles than fleet in total | 21 **more** (764 against 743) | did not hold |
| M5 | no run of any arm below SINTEF's record | none below | **held** |
| M6 | warm uses fewer vehicles than fleet on at least 4 of 13 | 0 of 13 (more on 9, equal on 4) | did not hold |
| M7 | eject fewer than warm on at least 4, more on at most 1 | fewer on 4, more on 5 | did not hold |

All 13 instances could be compared for every pair of arms, so no prediction was untestable.

## Per instance

Vehicles (K = fleet bound from `xltwlb.py`; SINTEF = hierarchical record; vrptwl = the earlier 300 s run), and the
time at which each arm reached its final count.

| instance | K | SINTEF | vrptwl | fleet | warm | eject | fleet s | warm s | eject s |
|---|---|---|---|---|---|---|---|---|---|
| C1_10_2 | 90 | 90 | 94 | **93** | 96 | 97 | 272.9 | 125.3 | 227.1 |
| C1_10_6 | 90 | 99 | 100 | **100** | 101 | **100** | 16.4 | 4.4 | 29.9 |
| C1_10_7 | 90 | 97 | 99 | **100** | **100** | **100** | 26.3 | 10.0 | 8.8 |
| C1_10_8 | 90 | 92 | 96 | **94** | 98 | 100 | 262.9 | 57.4 | 11.0 |
| C1_10_9 | 90 | 90 | 91 | **91** | 94 | 95 | 233.9 | 140.3 | 289.4 |
| C2_10_6 | 28 | 29 | 30 | **30** | **30** | **30** | 24.0 | 8.2 | 66.1 |
| C2_10_7 | 28 | 29 | 30 | **30** | 31 | **30** | 29.0 | 75.0 | 300.1 |
| C2_10_8 | 28 | 28 | 29 | **29** | 30 | 30 | 22.1 | 5.0 | 127.5 |
| C2_10_9 | 28 | 28 | 29 | **29** | 31 | 30 | 33.7 | 4.1 | 198.1 |
| RC1_10_1 | 90 | 90 | 91 | **90** | 91 | 93 | 166.3 | 11.8 | 79.3 |
| RC2_10_1 | 18 | 20 | 21 | **20** | 22 | 21 | 46.0 | 9.8 | 179.2 |
| RC2_10_2 | 18 | 18 | 20 | **19** | **19** | 20 | 213.8 | 9.6 | 160.7 |
| RC2_10_5 | 18 | 18 | 19 | **18** | **18** | **18** | 22.3 | 14.8 | 174.2 |
| total | | 728 | 749 | **743** | 761 | 764 | | | |

Bold = fewest vehicles among the three arms. Over SINTEF's records in total: fleet +15, warm +33, eject +36.

## What the misses show

**Both new loops lost to the reference, and they lost in different ways.**

- **warm stalls early.** It drops one route at a time very quickly (about 0.15 s per level at the start), but on
  8 of the 13 instances it reached its final count, still above K, within 15 s and then spent the rest of the
  300 s on one failed attempt. Starting from a good solution with one route removed seems to leave PyVRP's
  search in a basin it cannot leave, while the reference's fresh random start at every level keeps getting further.
  Like the reference, warm spends all remaining time on the first level it cannot reach, so one stall ends the run.
- **eject is slow per level and its counters barely moved.** It ran 48 to 97 rounds of at most 5 s over 7 to 41
  levels, and the largest counter reached only 2 to 11, so the prizes of hard customers rose at most twelvefold.
  At 1,000 customers a 5 s round is a short search, and each round is a new `solve` call. Its levels near the end
  took tens of seconds each (C2_10_7 reached 30 vehicles at 300.1 s, the end of its budget). The penalties were
  fixed far above any prize, so the search could never pass through late or overloaded states. That passage is the
  "squeeze" step of Nagata and Bräysy (2009). Our thin version left it out, and it may be the part that matters.

So the pre-registered guess that a warm start would help where the gap is one or two vehicles was wrong. A warm
start hurt. The plain loop, which restarts from scratch at every level, used the fewest vehicles (alone or tied) on
all 13 instances.

## Observed, not predicted

- **eject's route plans were the shortest on all 13 instances**, also on the 5 where it used the same number of
  vehicles as fleet (for example C2_10_6: 16,525 against 18,964 at 30 vehicles). This is expected from how the arms
  work, not a finding: fleet and warm stop at the first feasible solution of each level, while each eject round runs
  PyVRP's full search, which keeps shortening routes. The expectations said distances would not be compared, and no
  arm had a distance phase.
- **The reference did better here than in `vrptwl/`** on 6 of the 13 instances and worse on 1 (C1_10_7, 100 against
  99), 743 vehicles against 749. Two reasons are likely and we cannot separate them: the 13 instances were picked
  because `vrptwl/` did badly on them, so some regression to the mean is expected, and this job ran on a different
  day of the shared machine (`xltwbase/` found speed differences of 1.5 to 5.6 times between jobs).
- **The reference was still improving at the end on C1_10_2, C1_10_8 and C1_10_9** (one vehicle every 72 to 95 s
  near 300 s). The challenge's time limit is 1,800 s per 1,000 customers, six times this budget.

## What this changes

`xltwbase.py` keeps PyVRP's `minimise_fleet` loop for its fleet phase. Neither alternative is adopted. The next test,
[`xltwrs/`](../xltwrs/expectations.md), keeps the reference and asks two things it can answer on the same
instances: how much more the reference gets from a 900 s fleet budget, and whether capping each attempt and
restarting with a new seed beats one long attempt at the first level that fails.

## Limits

One seed and one 300 s budget per run on a shared machine. 13 instances chosen where the reference had done badly.
Each new loop is a thin layer over PyVRP's search with no new operators. A full ejection-pool method with a squeeze
step could do much better, so this result says nothing about ejection pools in general, only about this version.
Route minimisation by ejection pools is well known (Lim and Zhang 2007; Nagata and Bräysy 2009); nothing here is
a new method.
