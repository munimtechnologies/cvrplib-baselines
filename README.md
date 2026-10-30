# cvrplib-baselines

Open, reproducible baselines of plain [PyVRP](https://github.com/PyVRP/PyVRP) (MIT) on
[CVRPLib](https://galgos.inf.puc-rio.br/cvrplib/) benchmark instances. For each run, the expected outcome was
written down *before* it ran and the run was scored afterwards, including where the expectation was wrong.

By MV2 of Munim, Inc. (mv2@munimtech.com). The code, runs and write-ups were made with AI agents
working in MV2's name. Licence: Apache-2.0 (code); results and text CC BY 4.0.

Why: CVRPLib's VRPTW Best Known Solution Challenge (1,000 to 10,000 customers with time windows; official
instances on 2027-02-24, ending 2027-03-26) asks what a method can do on very large instances. These runs
measure what an off-the-shelf solver on one CPU does, as a floor to compare against. They are calibrations,
not new results.

## vrp/: warm and cold PyVRP on the three smallest XL instances

`vrp_probe.py` downloads each instance and its best known solution (BKS) from CVRPLib and checks the BKS
with its own cost function (TSPLIB nint-Euclidean). It then runs PyVRP 0.14.1 for 30 minutes starting from the
BKS (warm) and 15 minutes from scratch (cold), and checks every result again with its own function.
A result better than the BKS would be written out in CVRPLib format; none was.

| instance | BKS | warm, 30 min | cold, 15 min | cold gap |
|---|---|---|---|---|
| XL-n1048-k237 | 380,090 | 380,090 | 387,650 | 1.99% |
| XL-n1094-k157 | 112,431 | 112,431 | 112,637 | 0.18% |
| XL-n1141-k112 | 95,638 | 95,638 | 96,259 | 0.65% |

Pre-registered expectations: [vrp/expectations.md](vrp/expectations.md). Scoring:
[vrp/score.md](vrp/score.md): E1 (BKS check) and E2 (no warm improvement) held. E3 (every cold gap
between 0.5% and 3%) failed on XL-n1094-k157, which came within 0.18%.
Raw output: [vrp/results.json](vrp/results.json), [vrp/results.md](vrp/results.md).

## vrptw/: all 56 Solomon instances and six 1,000-customer Homberger instances

`vrptw_baseline.py` checks every CVRPLib VRPTW BKS under the DIMACS convention (each arc truncated to
0.1, travel time = distance). It runs PyVRP in two modes: *dist* (distance only, the file's fleet) and
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
convention of SINTEF's long-standing hierarchical records: no truncation, time = distance). It compares each
with the SINTEF record (fewest vehicles, then distance).

| | result |
|---|---|
| Solomon BKSs feasible in double precision | 48 of 56; late somewhere: R102, R105, R107, R108, R112, R211, RC101, RC105 (one late arrival each, 0.07 to 0.40 time units) |
| 1,000-customer BKSs feasible in double precision | 4 of 6; R1_10_1 (95 routes; 7 late arrivals) and RC2_10_1 (2) are not |
| R1_10_1 | CVRPLib's BKS uses 95 routes, SINTEF's record 100: the 95-route solution is feasible only with truncated travel times |
| 23 PyVRP results that looked shorter than SINTEF's records under DIMACS | in double precision 5 are infeasible, 10 equal the record, 8 are longer; none is better |

Scoring: [vrptwd/score.md](vrptwd/score.md): D0 to D3 held. D4 (at least 50 of 56 Solomon BKSs
feasible in double precision) failed with 48. Raw output: [vrptwd/results.json](vrptwd/results.json),
[vrptwd/results.md](vrptwd/results.md). Neither convention is wrong; both are documented and in use. The
point is that a vehicle count or distance from one convention cannot be compared with a record kept under the
other.

## vrptwd2/: the same 86 solutions, checked a second way

`exact_check.py` is a separately written check of every `vrptwd/` row. It parses the instances with the `vrplib`
package (2.2.0) instead of our own parser, computes in exact 50-digit decimal arithmetic, and lists every late
arrival. All four pre-registered expectations held ([vrptwd2/score.md](vrptwd2/score.md)). The two checks agree on
feasibility, route counts, late arrivals, the largest lateness (within 0.0001) and distance (within 0.006) for all
86 solutions, so the `vrptwd/` lists above are checked twice. Two BKSs (RC201, RC1_10_1) reach a customer exactly
at its due time. Raw output: [vrptwd2/results.json](vrptwd2/results.json), [vrptwd2/results.md](vrptwd2/results.md),
[vrptwd2/late_visits.csv](vrptwd2/late_visits.csv). (Its first run, on 2026-10-29, was stopped by the host before it
wrote any output. The second run used the same code plus progress logging.)

## vrptwd3/: all 300 Homberger BKSs in double precision

`homberger_check.py` runs the unchanged `vrptwd/double_check.py` on every Homberger instance on CVRPLib (200, 400,
600, 800 and 1,000 customers; six families of 10 at each size). It lists every late arrival with the number of arcs
driven before it.

| | result |
|---|---|
| DIMACS check | 300 of 300 BKSs feasible, cost equal to the file |
| late in double precision | **82 of 300 (27.3%)**: 20 of 100 C1/C2, 62 of 200 R1/R2/RC1/RC2 |
| by size (all families) | 12, 14, 12, 23 and 21 of 60 at 200, 400, 600, 800 and 1,000 customers |
| C2 at 800 and 1,000 customers | 12 of 20 late; the five largest lateness values (0.78 to 1.27) are all C2 |
| late arrivals | 169, each within what truncation can remove (0.1 per arc driven) |
| feasible but close | 36 of 218 feasible BKSs come within 0.1 of a due time, 12 within 0.01 |

Scoring: [vrptwd3/score.md](vrptwd3/score.md). H0, H2, H3 and H4 held. H1 (no C1/C2 BKS late) did not hold:
20 are. H3 held by one instance only. The expectations miscount the groups (120 C and 180 R/RC instead of 100 and
200). The code counted them from the names, so no verdict changes; the score explains this. Raw output:
[vrptwd3/results.json](vrptwd3/results.json), [vrptwd3/results.md](vrptwd3/results.md),
[vrptwd3/late_visits.csv](vrptwd3/late_visits.csv).

What this is for: a solver or checker that works in double precision cannot start from, or compare with, about a
quarter of the Homberger BKSs as published. The per-instance lists in `vrptwd/` and `vrptwd3/` say which ones. They are not errors
in CVRPLib: every one is feasible under the DIMACS rules it was found with.

## vrptwd4/: 87 of the 90 late BKSs repaired without an extra route

`repair.py` starts PyVRP from each of the 90 BKSs that are late in double precision, with the fleet capped at the
BKS's route count, on a copy of the instance where every number is multiplied by 1,000 and rounded **up**. Travel
times then never undercut the exact ones, so anything on time in the copy is on time in double precision; every
result is re-checked by `vrptwd/double_check.py` anyway. One seed, 60 s to 300 s per instance.

| | result |
|---|---|
| repaired (on time in double precision, no more routes than the BKS) | **87 of 90**; all 50 in C2/R2/RC2, 37 of 40 in C1/R1/RC1 |
| not repaired in the budget | R1_6_1, R1_8_1, R1_10_1 (95 routes; SINTEF's double-precision record uses 100) |
| distance against the BKS's own double-precision distance | median +0.43%; +0.19% in C2/R2/RC2, +1.38% in C1/R1/RC1; largest +12.85% (RC1_10_5) |
| one route fewer than the BKS | R2_2_1, R2_2_2, R2_6_5, at 0.47% to 0.96% more distance: not an improvement under either convention |
| against SINTEF's records (where `double_check.py` has them) | all 9 comparable repairs use more vehicles; none is better |

Scoring: [vrptwd4/score.md](vrptwd4/score.md): all seven pre-registered expectations (R0 to R6) held; R3 (median
change 0% to +0.5%) only because the wide-horizon repairs dominate. Repaired solutions: [vrptwd4/sols/](vrptwd4/sols/)
(CVRPLib format, `Cost` = double-precision distance). Raw output: [vrptwd4/results.json](vrptwd4/results.json),
[vrptwd4/results.md](vrptwd4/results.md). A BKS that was not repaired is not shown to be impossible at its route
count; a repair is not a new record.

## vrptwd4x/: the 87 repaired solutions, checked a second way (pre-registered, running)

`exact_repair_check.py` re-checks every solution in `vrptwd4/sols/` with the `vrplib` parser and exact 50-digit
decimal arithmetic, under both conventions, and takes each BKS's route count from the BKS file itself. The
predictions (X0 to X4) were written before the run: [vrptwd4x/expectations.md](vrptwd4x/expectations.md). Its first
run read no data (the `vrptwd4/` files had not reached this repository yet); the same code is running again. Results
and scoring will be added here.

## vrptwd5/: where on their routes the late BKSs turn late

`anatomy.py` follows every route of the 356 BKSs under both conventions at once. In double precision a route drifts
later by up to 0.1 per arc until the vehicle waits for a window to open, so a visit can only turn late if its DIMACS
slack is below 0.1 times the arcs driven since the last wait (it is *exposed*).

| | result |
|---|---|
| late routes | 141 on the 90 late BKSs; every late visit is exposed, as the arithmetic requires |
| C2 route late rate | 3.33% at 800 and 1,000 customers against 1.08% at 200 to 600 (3.1 times) |
| late C2 routes | 15 of 22 never wait, the other 7 wait once; only 6 run up against the depot's closing time |
| first late visit | at the depot on 4 of 141 late routes; at a customer reached exactly at its due time under DIMACS on 84 |
| exposed visits as a signal | separate late from on-time BKSs with AUC 0.865 |

Scoring: [vrptwd5/score.md](vrptwd5/score.md): A0, A3, A4 and A5 held. A1 (C2 late rate at most doubles with
size) and A2 (most late C2 routes run up against the depot's closing time) did not hold. Late C2 routes are long
chains with no wait to reset the drift. Why this happens more often at 800 and 1,000 customers is only partly
explained (more no-wait routes), and the score says so. Raw output: [vrptwd5/results.json](vrptwd5/results.json),
[vrptwd5/results.md](vrptwd5/results.md), [vrptwd5/routes.csv](vrptwd5/routes.csv) (one row per route of all 356
BKSs).

## vrptwl/: fewest vehicles first, in double precision, against SINTEF's records (pre-registered, running)

The challenge ranks by vehicles first. CVRPLib's VRPTW BKSs minimise distance only; the hierarchical records for the
same instances are SINTEF's, kept in double precision. `fleet_double.py` runs PyVRP's `minimise_fleet` (300 s) and
then `solve` with that fleet (300 s) on all 60 Gehring-Homberger 1,000-customer instances, with travel times x1,000
rounded up so that results are on time in double precision, and compares each result with SINTEF's record. The
predictions (L0 to L6) were written before the run: [vrptwl/expectations.md](vrptwl/expectations.md). Results and
scoring will be added here.

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

- vrptwd4x/ and vrptwl/ results and scoring (above).
- XLTW-Test (due from CVRPLib; announced for 2026-10-31): plain PyVRP under the challenge's own convention, with
  expectations written first. If the challenge uses double precision, `vrptwd/` to `vrptwd5/` say which DIMACS
  BKSs a solver cannot start from as published, and `vrptwd4/sols/` gives double-precision starts for 87 of them.

Reproduce (Python 3.12):

```
pip install pyvrp==0.14.1 vrplib==2.2.0
cd vrp
python -m unittest -v test_vrp_probe
python vrp_probe.py --ids 280,281,282 --warm-seconds 1800 --cold-seconds 900 --workers 2 --data-dir data --out-dir out
cd ../vrptw
python -m unittest -v test_vrptw_baseline
python vrptw_baseline.py --ids 380-435,676,686,696,706,716,726 --small-seconds 30 --large-seconds 300 --workers 2 --data-dir data --out-dir out
cd ../vrptwd
python -m unittest -v test_double_check
python double_check.py --ids 380-435,676,686,696,706,716,726 --sols sols --data-dir data --out-dir out
cd ../vrptwd2
python -m unittest -v test_exact_check
python exact_check.py --reference reference.csv --data-dir data --out-dir out
cd ../vrptwd3
python -m unittest -v test_homberger_check
python homberger_check.py --ids 436-735 --data-dir data --out-dir out
cd ../vrptwd4
python -m unittest -v test_repair
python repair.py --ids 380-735 --workers 3 --data-dir data --out-dir out
cd ../vrptwd4x
python -m unittest -v test_exact_repair_check
python exact_repair_check.py --data-dir data --out-dir out
cd ../vrptwd5
python -m unittest -v test_anatomy
python anatomy.py --ids 380-735 --data-dir data --out-dir out
cd ../vrptwl
python -m unittest -v test_fleet_double
python fleet_double.py --ids 676-735 --seconds 600 --workers 3 --data-dir data --out-dir out
cd ../xl
python -m unittest -v test_xl_scale
python xl_scale.py --id 379 --sizes 1000,2500,5000,10000 --seconds 300,600,900,1800 --data-dir data --out-dir out
```

Limits: one seed, one CPU per run, wall-clock budgets (results vary with machine speed). The results files
say "PyVRP unknown" because 0.14.1 has no `__version__`; the version was pinned as above.

Data: instances and best known solutions are downloaded from CVRPLib at run time and are not redistributed here.
SINTEF's record table in `vrptwl/fleet_double.py` is quoted (vehicles and distance only) with its source URL.
