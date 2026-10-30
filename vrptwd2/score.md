# Scoring of vrptwd2-exact (second, independent check of every vrptwd/ row)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.

The expectations were written before the run: [expectations.md](expectations.md) (2026-10-29, about 22:40 UTC).
The first run (`vrptwd2-exact-v1`, 2026-10-29) was stopped by the host after 16 minutes, before it wrote any
output (exit 143, the host's stop signal, not an error in the code). It was queued again with the same code plus
progress logging (`vrptwd2-exact-v2`) and ran on 2026-10-30 from 01:08 to 01:14 UTC: its 7 unit tests passed and
the check took 191 s on one CPU.

**What it checks.** The same 86 solutions as [`vrptwd/`](../vrptwd/score.md): the 62 CVRPLib best known
solutions (56 Solomon, six 1,000-customer Homberger) and 24 PyVRP lex solutions. Instances are parsed with the
`vrplib` package (2.2.0), not our own parser, and every distance, arrival and slack is computed in 50-digit
`Decimal` arithmetic with no floating point. The timing rules are the same as `vrptwd/`: travel time = Euclidean
distance, waiting allowed, late if arrival > due + 1e-6, the depot's due time applies to the return.
`reference.csv` holds the `vrptwd/` figures it is compared with.

| | Expectation (as written) | Result | Verdict |
|---|---|---|---|
| S1 | Feasibility verdicts and route counts agree for all 86 solutions. | 86 of 86 agree (no feasibility or route-count disagreement) | **held** |
| S2 | Late-arrival counts agree, and the largest lateness agrees within 0.0001. | 0 disagreements | **held** |
| S3 | Total distance agrees within 0.006 of the earlier two-decimal figure. | 0 disagreements | **held** |
| S4 | Every late arrival is at most 0.1 x the arcs driven up to it. | 30 late arrivals, all within the bound | **held** |

**What it means.** Two separately written checks, one in double precision with our own parser and one in exact
decimal arithmetic with vrplib's parser, give the same answer for every one of the 86 solutions. The `vrptwd/`
findings therefore stand as checked twice: in double precision, 8 of the 56 Solomon BKSs (R102, R105, R107, R108,
R112, R211, RC101, RC105) and 2 of the six 1,000-customer BKSs (R1_10_1 with 7 late arrivals, RC2_10_1 with 2)
arrive late somewhere, by 0.014 to 0.40 time units; 6 of the 24 PyVRP lex solutions (R102, R105, R112, R1_10_1,
R202, RC202) do too. In total 70 of 86 solutions are feasible and 16 are not.

Reported, not predicted: 11 of the 70 feasible solutions come within 0.1 time units of a due time somewhere, and
4 within 0.01. Two BKSs (RC201 and RC1_10_1) reach a customer exactly at its due time in exact arithmetic (slack
0.000000), so a checker with a slightly negative tolerance would call them late.

**Limits.** Both checks apply the same timing rules, so they confirm the arithmetic and the reading of the files,
not the choice of convention. Neither convention is wrong: a solution late in double precision is feasible under
the DIMACS rules it was found with, and these results say nothing against CVRPLib or the solutions' authors.

Files: [results.json](results.json), [results.md](results.md), [late_visits.csv](late_visits.csv) (one row per
late arrival), [exact_check.py](exact_check.py), [test_exact_check.py](test_exact_check.py).
