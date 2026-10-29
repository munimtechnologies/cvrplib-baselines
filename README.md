# cvrplib-baselines

Open, reproducible baselines of plain [PyVRP](https://github.com/PyVRP/PyVRP) (MIT) on
[CVRPLib](https://galgos.inf.puc-rio.br/cvrplib/) benchmark instances, each run with its expected
outcome written down *before* it ran and scored afterwards, including where the expectation was wrong.

By MV2 of Munim, Inc. (mv2@munimtech.com). The code, runs and write-ups were made with AI agents
working in MV2's name. Licence: Apache-2.0 (code); results and text CC BY 4.0.

Why: CVRPLib's VRPTW Best Known Solution Challenge (1,000 to 10,000 customers with time windows; official
instances on 2027-02-24, ending 2027-03-26) asks what a method can do on very large instances. These runs
measure what an off-the-shelf solver on one CPU does, as a floor to compare against. They are calibrations,
not new results.

## vrp/: warm and cold PyVRP on the three smallest XL instances

`vrp_probe.py` downloads each instance and its best known solution (BKS) from CVRPLib, checks the BKS
with its own cost function (TSPLIB nint-Euclidean), runs PyVRP 0.14.1 for 30 minutes starting from the
BKS (warm) and 15 minutes from scratch (cold), and checks every result again with its own function.
A result better than the BKS would be written out in CVRPLib format; none was.

| instance | BKS | warm, 30 min | cold, 15 min | cold gap |
|---|---|---|---|---|
| XL-n1048-k237 | 380,090 | 380,090 | 387,650 | 1.99% |
| XL-n1094-k157 | 112,431 | 112,431 | 112,637 | 0.18% |
| XL-n1141-k112 | 95,638 | 95,638 | 96,259 | 0.65% |

Pre-registered expectations: [vrp/expectations.md](vrp/expectations.md). Scoring:
[vrp/score.md](vrp/score.md): E1 (BKS check) and E2 (no warm improvement) held; E3 (every cold gap
between 0.5% and 3%) failed on XL-n1094-k157, which came within 0.18%.
Raw output: [vrp/results.json](vrp/results.json), [vrp/results.md](vrp/results.md).

## vrptw/: all 56 Solomon instances and six 1,000-customer Homberger instances

`vrptw_baseline.py` checks every CVRPLib VRPTW BKS under the DIMACS convention (each arc truncated to
0.1, travel time = distance) and runs PyVRP in two modes: *dist* (distance only, the file's fleet) and
*lex* (fewest vehicles for half the time, then distance). 30 s per mode on Solomon, 300 s on Homberger.

| | result |
|---|---|
| BKS check (DIMACS) | 62 of 62 reproduce their Cost line |
| dist, Solomon | BKS reached on 40 of 56; largest gap 1.64% (RC108) |
| dist, 1,000 customers | gaps 0.005% (C1_10_1), 0.82% (C2), 1.92% (R1), 0.47% (R2), 1.66% (RC1), 0.21% (RC2) |
| lex, Solomon | fewer routes than CVRPLib's BKS on 36 of 56, because those BKSs minimise distance only |

Scoring: [vrptw/score.md](vrptw/score.md): V1 and V4 held, V2 and V3 failed (bands set too tight).
Raw output: [vrptw/results.json](vrptw/results.json), [vrptw/results.md](vrptw/results.md).
The `beats_bks_lex` flags in the results are fewer-route solutions compared with distance-only optima.
They are not improvements, and they are not published as such.

## vrptwd/: the same solutions in double precision

`double_check.py` re-checks the 62 CVRPLib BKSs and 24 PyVRP lex solutions in double precision (the
convention of SINTEF's long-standing hierarchical records: no truncation, time = distance) and compares each
with the SINTEF record (fewest vehicles, then distance).

| | result |
|---|---|
| Solomon BKSs feasible in double precision | 48 of 56; late somewhere: R102, R105, R107, R108, R112, R211, RC101, RC105 (one late arrival each, 0.07 to 0.40 time units) |
| 1,000-customer BKSs feasible in double precision | 4 of 6; R1_10_1 (95 routes; 7 late arrivals) and RC2_10_1 (2) are not |
| R1_10_1 | CVRPLib's BKS uses 95 routes, SINTEF's record 100: the 95-route solution is feasible only with truncated travel times |
| 23 PyVRP results that looked shorter than SINTEF's records under DIMACS | in double precision 5 are infeasible, 10 equal the record, 8 are longer; none is better |

Scoring: [vrptwd/score.md](vrptwd/score.md): D0 to D3 held; D4 (at least 50 of 56 Solomon BKSs
feasible in double precision) failed with 48. Raw output: [vrptwd/results.json](vrptwd/results.json),
[vrptwd/results.md](vrptwd/results.md). Neither convention is wrong; both are documented and in use. The
point is that a vehicle count or distance from one convention cannot be compared with a record kept under the
other.

## xl/: memory and speed at 1,000 to 10,000 customers

`xl_scale.py` builds instances from the first n customers of XL-n10001-k1570 with **synthetic** time
windows and solves them on one CPU, to size jobs for the XLTW instances.

| n | budget | peak memory | iterations/s | feasible |
|---|---|---|---|---|
| 1,000 | 300 s | 105 MB | 336.7 | yes |
| 2,500 | 600 s | 253 MB | 185.1 | yes |
| 5,000 | 900 s | 638 MB | 99.6 | yes |
| 10,000 | 1,800 s | 2,361 MB | 44.1 | yes |

Scoring: [xl/score.md](xl/score.md): X1-X4 all held.

## Coming next

- `vrptwd2/`: a second, separately written check of every `vrptwd/` row (vrplib's parser, exact 50-digit
  arithmetic, every late visit listed). Expectations: [vrptwd2/expectations.md](vrptwd2/expectations.md).
- XLTW-Test (due from CVRPLib on 2026-10-31): plain PyVRP under the challenge's own convention.

Reproduce (Python 3.12):

```
pip install pyvrp==0.14.1
cd vrp
python -m unittest -v test_vrp_probe
python vrp_probe.py --ids 280,281,282 --warm-seconds 1800 --cold-seconds 900 --workers 2 --data-dir data --out-dir out
cd ../vrptw
python -m unittest -v test_vrptw_baseline
python vrptw_baseline.py --ids 380-435,676,686,696,706,716,726 --small-seconds 30 --large-seconds 300 --workers 2 --data-dir data --out-dir out
cd ../vrptwd
python -m unittest -v test_double_check
python double_check.py --ids 380-435,676,686,696,706,716,726 --sols sols --data-dir data --out-dir out
cd ../xl
python -m unittest -v test_xl_scale
python xl_scale.py --id 379 --sizes 1000,2500,5000,10000 --seconds 300,600,900,1800 --data-dir data --out-dir out
```

Limits: one seed, one CPU per run, wall-clock budgets (results vary with machine speed). The results files
say "PyVRP unknown" because 0.14.1 has no `__version__`; the version was pinned as above.

Data: instances and best known solutions are downloaded from CVRPLib at run time and are not redistributed here.
