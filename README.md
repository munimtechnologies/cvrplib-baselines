# cvrplib-baselines

Open, reproducible baselines of plain [PyVRP](https://github.com/PyVRP/PyVRP) (MIT) on
[CVRPLib](https://galgos.inf.puc-rio.br/cvrplib/) benchmark instances. For each run, the expected outcome was
written down *before* it ran and the run was scored afterwards, including where the expectation was wrong.

By MV2 of Munim, Inc. (mv2@munimtech.com). The code, runs and write-ups were made with AI agents
working in MV2's name. Licence: Apache-2.0 (code); results and text CC BY 4.0.

Why: CVRPLib's VRPTW Best Known Solution Challenge (1,000 to 10,000 customers with time windows; official
instances on 2027-02-24, ending 2027-03-26) asks what a method can do on very large instances. These runs
measure what an off-the-shelf solver on one CPU does, as a floor to compare against. They are calibrations,
not new results. The challenge's rules were published on 2026-11-02 (summary below).

**Status (2026-11-06).** The baseline has run on all 100 XLTW-Test instances under the challenge's protocol at 1/30 of
the time limit (`xltwrun/`, scoring waits for three re-runs of host-frozen runs). Time-based fleet bounds K* are
scored (`xltwen/`). The offline, protocol-exact package of the solver is being tested (`xltwpkg/`), and a
pre-registered run at the full time limit is queued (`xltwfull/`).

## The challenge's rules (published 2026-11-02, summarised)

From the [challenge page](https://galgos.inf.puc-rio.br/cvrplib/en/challenges/vrptw/overview), read on 2026-11-02
and again on 2026-11-04 (no change). This is our summary; the page is the authority.

| | rule |
|---|---|
| objective | fewest routes first, then total distance; no fleet limit |
| distance and time | TSPLIB EUC_2D: each arc rounded to the nearest integer, floor(d + 0.5); travel time = distance |
| instances | XLTW: 1,000 to 10,000 customers, XL's depot, customer locations and demands with new time windows, service times and capacity; confidential until 2027-02-24 15:00 GMT. XLTW-Test (for development, dropped when the challenge starts) is a download on the page now |
| scoring | days holding a BKS during the 30 days, +5 for each final BKS, at most 35 per instance (as in the CVRP challenge); certificates to the overall winner and to every team with at least one final BKS |
| algorithm track | registration and submissions 2026-12-16 to 2027-01-16; public code with a README, or a paper or report, or documented commercial software; a short report on XLTW-Test is mandatory |
| how algorithms run | Linux x86-64, builds with `make` or `build.sh`, no Internet, no root; single-threaded, one logical CPU; `./solver instance.vrp <seconds> <seed>`; at the limit SIGTERM, then SIGKILL 5 s later; solutions printed to stdout in CVRPLib format (`Route #k: ...`, `Cost: ...`, customers numbered 1..n, nothing else on stdout), the last complete feasible one before the limit counts; T(n) = 1,800 x n / 1,000 s (30 min per 1,000 customers); 20 runs per instance, deterministic per seed |

What this means for the work below: the challenge uses neither double precision nor DIMACS truncation but
nearest-integer rounding, which `xltwlb.py` already calls 'round'. The double/DIMACS findings (`vrptwd/` to
`vrptwd5/`) are about CVRPLib's existing VRPTW sets and SINTEF's records, not about the challenge's scoring. Under
'round' the time-window bound of the R1 `_1` instances no longer binds (`xltwlb/`). The time limit for algorithm
runs is 1,800 s per 1,000 customers, six times the 300 s fleet budgets used so far.

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
| R1_10_1 | CVRPLib's BKS uses 95 routes, SINTEF's record 100: the 95-route solution is feasible only with truncated travel times (and `vrptwlb/` shows that no 95-route solution is on time in double precision) |
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

The check includes the 13 VRPTW improvements CVRPLib published on 2026-10-23 (Takahashi, Kumamoto, Shin, Nomura and
Ono, Institute of Science Tokyo; C1/R1/RC1 at 1,000 customers): all 13 are on time in double precision, and each
uses exactly the capacity bound's number of routes ([xltwlb/score.md](xltwlb/score.md)).

What this is for: a solver or checker that works in double precision cannot start from, or compare with, about a
quarter of the Homberger BKSs as published. The per-instance lists in `vrptwd/` and `vrptwd3/` say which ones. They are not errors
in CVRPLib: every one is feasible under the DIMACS rules it was found with. (These counts are for the files read on
2026-10-30; `bkswatch/` below re-reads them.)

## vrptwd4/: 87 of the 90 late BKSs repaired without an extra route

`repair.py` starts PyVRP from each of the 90 BKSs that are late in double precision, with the fleet capped at the
BKS's route count, on a copy of the instance where every number is multiplied by 1,000 and rounded **up**. Travel
times then never undercut the exact ones, so anything on time in the copy is on time in double precision; every
result is re-checked by `vrptwd/double_check.py` anyway. One seed, 60 s to 300 s per instance.

| | result |
|---|---|
| repaired (on time in double precision, no more routes than the BKS) | **87 of 90**; all 50 in C2/R2/RC2, 37 of 40 in C1/R1/RC1 |
| not repaired in the budget | R1_6_1, R1_8_1, R1_10_1 (95 routes; SINTEF's double-precision record uses 100). `vrptwlb/` later showed that R1_6_1 (58 routes) and R1_10_1 cannot be repaired at their route count: both are below the double-precision fleet bound (59 and 100). R1_8_1 is not ruled out. |
| distance against the BKS's own double-precision distance | median +0.43%; +0.19% in C2/R2/RC2, +1.38% in C1/R1/RC1; largest +12.85% (RC1_10_5) |
| one route fewer than the BKS | R2_2_1, R2_2_2, R2_6_5, at 0.47% to 0.96% more distance: not an improvement under either convention |
| against SINTEF's records (where `double_check.py` has them) | all 9 comparable repairs use more vehicles; none is better |

Scoring: [vrptwd4/score.md](vrptwd4/score.md): all seven pre-registered expectations (R0 to R6) held; R3 (median
change 0% to +0.5%) only because the wide-horizon repairs dominate. Repaired solutions: [vrptwd4/sols/](vrptwd4/sols/)
(CVRPLib format, `Cost` = double-precision distance). Raw output: [vrptwd4/results.json](vrptwd4/results.json),
[vrptwd4/results.md](vrptwd4/results.md). Apart from the two cases above, a BKS that was not repaired is not shown to
be impossible at its route count; a repair is not a new record.

## vrptwd4x/: the 87 repaired solutions, checked a second way

`exact_repair_check.py` re-checks every solution in `vrptwd4/sols/`, downloaded from this repository, with the
`vrplib` parser and exact 50-digit decimal arithmetic, under both conventions. It takes each BKS's route count from
the BKS file itself.

| | result |
|---|---|
| on time in exact double-precision arithmetic | **87 of 87** |
| on time under DIMACS | 87 of 87 |
| distance and DIMACS cost against `vrptwd4/` | no disagreement |
| one route fewer than the BKS file | R2_2_1 (12/13), R2_2_2 (10/11), R2_6_5 (21/22) confirmed |
| no room to spare | 14 solutions come within 0.01 of a due time; 13 show 0.000000 slack to six decimals |

Scoring: [vrptwd4x/score.md](vrptwd4x/score.md): all five pre-registered expectations (X0 to X4) held
([vrptwd4x/expectations.md](vrptwd4x/expectations.md)). Raw output: [vrptwd4x/results.json](vrptwd4x/results.json),
[vrptwd4x/results.md](vrptwd4x/results.md). Its first run read no data, because the `vrptwd4/` files had not reached
this repository yet. The second run used the same code.

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

## vrptwl/: fewest vehicles first, in double precision, against SINTEF's records

The challenge ranks by vehicles first. CVRPLib's VRPTW BKSs minimise distance only; the hierarchical records for the
same instances are SINTEF's, kept in double precision. `fleet_double.py` ran PyVRP's `minimise_fleet` (300 s) and
then `solve` with that fleet (300 s) on all 60 Gehring-Homberger 1,000-customer instances, with travel times x1,000
rounded up so that results are on time in double precision, and compared each result with SINTEF's record.

| family | match SINTEF's vehicles | vehicles over (misses) | median distance over SINTEF where matched |
|---|---|---|---|
| C1 | 5 of 10 | +1, +1, +2, +4, +4 | 0.52% |
| C2 | 6 of 10 | +1, +1, +1, +1 | 2.01% |
| R1 | 10 of 10 | none | 21.95% |
| R2 | 10 of 10 | none | 1.68% |
| RC1 | 9 of 10 | +1 | 12.90% |
| RC2 | 7 of 10 | +1, +1, +2 | 3.80% |
| all | **47 of 60** | 21 vehicles (3,437 against 3,416) | 4.18% |

All 60 results are on time in double precision. None beats a SINTEF record; C2_10_1 equals its record. In 41
instances `minimise_fleet` returned before its time limit. By PyVRP's source, that happens only at its capacity
bound, and all 41 match SINTEF's count (`vrptwlb/` confirms KC equals the returned fleet in all 41). The 13 misses
all ran out of time. In the short-horizon families (R1, RC1), the vehicle count was easy and distance was the hard
part.

Scoring: [vrptwl/score.md](vrptwl/score.md): L0 to L4 held. L5 (at most 6 of 20 match in R1/RC1) and L6 (median
distance where matched at most 3% above SINTEF) did not hold: 19 of 20 matched, and the median was 4.18%.
Expectations: [vrptwl/expectations.md](vrptwl/expectations.md). Raw output: [vrptwl/results.json](vrptwl/results.json),
[vrptwl/results.md](vrptwl/results.md); solutions in [vrptwl/sols/](vrptwl/sols/) (CVRPLib format, `Cost` =
double-precision distance). None is a record. SINTEF's record table in `fleet_double.py` (vehicles and distance
only) is quoted with its source URL; the job re-read the page and found no difference.

## vrptwlb/: classical fleet lower bounds against SINTEF's records

`bounds.py` computes two classical lower bounds on the number of vehicles for all 356 CVRPLib VRPTW instances: the
capacity bound KC and a time-window bound KT (a clique of customers that no single route can serve together, after
Kontoravdis and Bard, 1995). It computes them in double precision and under DIMACS, re-checks every clique in exact
arithmetic, and compares K = max(KC, KT) with SINTEF's records, CVRPLib's BKS route counts and `vrptwl/`. These are
the bounds that Afifi, Guibadj and Moukrim (CPAIOR 2014) improved on; they report the minimum fleet for 339 of 468
standard instances ([vrptwlb/prior-art-addendum.md](vrptwlb/prior-art-addendum.md)). This is a reproduction and
calibration aid, not a new bound.

| | result |
|---|---|
| SINTEF's record equals K (cannot use fewer vehicles) | **270 of 356**: 23 of 56 Solomon, 247 of 300 Gehring-Homberger, 49 of 60 at 1,000 customers |
| records above K | 86 instances, 180 vehicles in total; at 1,000 customers 11 (C1_10_5 +10, C1_10_6 +9, C1_10_7 +7, then C1/C2/RC2 at +1 or +2) |
| time-window bound binding | 14 instances, all tightest-window: R101, R102, R103, RC105 and C1/R1 `_1` at every Gehring-Homberger size |
| double-precision K above DIMACS K | 6 tight-window R1 instances, up to 9 vehicles (R1_10_1: 100 vs 91) |
| DIMACS BKS below the double-precision K | R1_6_1 (58 vs 59) and R1_10_1 (95 vs 100): no solution with that many routes is on time in double precision |

Scoring: [vrptwlb/score.md](vrptwlb/score.md): B0 to B4 held; B5 (record equals K on 40% to 70%) did not hold, with
75.8%. Expectations: [vrptwlb/expectations.md](vrptwlb/expectations.md). Raw output:
[vrptwlb/results.json](vrptwlb/results.json), [vrptwlb/results.md](vrptwlb/results.md),
[vrptwlb/bounds.csv](vrptwlb/bounds.csv), [vrptwlb/cliques.json](vrptwlb/cliques.json). A record above K may still be
optimal; the greedy clique search may miss larger cliques.

## xltwlb/: the fleet bounds rewritten for 10,000 customers, checked against vrptwlb/

`xltwlb.py` is the `vrptwlb/` code rewritten for CVRPLib's XLTW-Test set. It reads VRPLIB or Solomon files, builds
the incompatibility matrix in row blocks (10,000 customers in 26 s and 0.30 GB on synthetic instances), adds the
Martello-Toth L2 bin-packing bound (KB), counts two customers whose demands together exceed the capacity as
incompatible, and adds a third travel-time convention, 'round' (nearest integer, CVRPLib's CVRP rule, and since
2026-11-02 known to be the VRPTW challenge's rule too). `compare.py` ran it on all 356 instances and compared it with
the published `vrptwlb/` files.

| | result |
|---|---|
| KC, KT (double, DIMACS) and the cliques against `vrptwlb/` | identical on all 356 |
| KB above KC | none (demands in these sets are small next to the capacity) |
| K under 'round' | differs from double on 7 instances and from DIMACS on 4, all tightest-window R1, always lower |
| R1 `_1` instances under 'round' | the time-window bound no longer binds at any Gehring-Homberger size; K falls to KC (R1_10_1: 91, against 100 in double) |
| time and memory | 49 s for all 356 in three conventions, peak 0.06 GB |

Scoring: [xltwlb/score.md](xltwlb/score.md): all five pre-registered expectations (C0 to C4) held
([xltwlb/expectations.md](xltwlb/expectations.md)). Raw output: [xltwlb/results.md](xltwlb/results.md),
[xltwlb/results.json](xltwlb/results.json), [xltwlb/tally.json](xltwlb/tally.json),
[xltwlb/cliques.json](xltwlb/cliques.json). Predictions for XLTW-Test, fixed before its release:
[xltwlb/predictions-xltw-test.md](xltwlb/predictions-xltw-test.md), scored in `xltwtest/` below.

## xltwtest/: fleet bounds on CVRPLib's XLTW-Test set (released 2026-11-02)

`xltwtest.py` downloaded XLTW-Test on 2026-11-02 (100 VRPLIB instances, 1,047 to 10,000 customers, the same sizes as
XL), recorded every file's size, hash and format, and ran the unchanged `xltwlb.py` on each instance in 'round' (the
challenge's convention), 'double' and 'dimacs'. All 100 parsed and were bounded; every clique was confirmed in exact
arithmetic.

| | result |
|---|---|
| capacity never binds | **33 of 100**: the capacity equals the total demand exactly, so KC = 1 and the fleet is decided by time alone |
| time-window bound binds in 'round' (KT > KB) | **38 of 100** (32 of the 33 above, plus n1281, n2494, n3241, n3888, n4635, n9363), against 14 of 356 on the classic sets |
| bin-packing bound above the capacity bound | none |
| K in 'round' against K in 'double' | equal on 89; on the other 11, 'round' is always lower and often by a lot (n9363: 253 against 408; n3640: 243 against 333; n1281: 132 against 195) |
| time and memory | 2,562 s for all 100 in three conventions, peak 0.54 GB; n9363 alone about 706 s |

So about a third of the test set are pure time-window fleet problems, where a vehicles-first solver gets no help from
capacity and the classical clique bound (which ignores route length) may be far below the true minimum. And a solver
or checker working in double precision would face a much harder problem than the one the challenge scores.

Scoring: [xltwtest/score.md](xltwtest/score.md): P4 held; P1 (within 30 minutes: it took 43), P2 (KB > KC somewhere)
and P3 (time-window bound binds on at most a quarter) did not
([xltwlb/predictions-xltw-test.md](xltwlb/predictions-xltw-test.md), fixed 2026-10-31). Raw output:
[xltwtest/results.md](xltwtest/results.md), [xltwtest/results.json](xltwtest/results.json),
[xltwtest/manifest.json](xltwtest/manifest.json) (files, hashes, per-instance statistics),
[xltwtest/cliques.json](xltwtest/cliques.json). No instance data is copied into this repository.

## xltwen/: time-based fleet bounds K* on XLTW-Test (energetic reasoning)

`xltwen.py` adds busy-period bounds after Afifi, Guibadj and Moukrim (CPAIOR 2014): over many time intervals, the
customers that must be served inside an interval (fully, or by their compulsory part) need at least so many vehicles
working there. E is the best such bound over three ways of charging travel time; K* = max(K, E). Every winning
interval is verified in exact integer arithmetic, and E is checked against the 80 exactly verified part-a solutions of
`xltwrun/` (it must never exceed them). One CPU, 337 s for all 100 instances, peak 0.52 GB.

| | result |
|---|---|
| E above K, capacity-free instances (KC = 1) | **26 of 33**; e.g. n3147 1 -> 68 (baseline 84 vehicles), n4153 5 -> 200 (238), n1608 7 -> 81 (113) |
| E above K, the other 67 | 9 |
| sum of fleet bounds over all 100 | 11,298 (K) -> 13,961 (K*), +23.6% |
| part a, median (vehicles - bound) / bound | 0.474 against K -> **0.303 against K*** |
| part a, capacity-free, median vehicles / bound | 6.08 against K -> **1.46 against K*** |
| E above any verified solution | never (80 of 80 checked) |
| still weak where capacity never binds | n1048, n1514, n2541, n2867, n3007, n3640, n5288 (E not above K); n5902, n7854, n8575 only a little |

Scoring: [xltwen/score.md](xltwen/score.md): all seven pre-registered expectations (E0 to E6) held
([xltwen/expectations.md](xltwen/expectations.md)); E2 by one instance. Raw output:
[xltwen/results.md](xltwen/results.md), [xltwen/results.json](xltwen/results.json),
[xltwen/progress.jsonl](xltwen/progress.jsonl). The bounding method is published prior art; what is new is only these
numbers on XLTW-Test. K* is a lower bound, so it says how far the baseline *might* be from the best fleet, not how
many vehicles are achievable.

## xltwbase/: vehicles first, fleet search stopped at the bound, leftover time to distance

`xltwbase.py` is the baseline we plan to run on XLTW-Test. It runs `minimise_fleet`'s own loop but stops it at
K = max(L2, time-window clique) from `xltwlb.py`, gives `solve` every second the fleet phase did not use, and
re-checks every result in 50-digit decimals in the run's own convention (double, DIMACS or nearest-integer). It was
checked on 13 Gehring-Homberger 1,000-customer instances (600 s each) and 4 convention runs (120 s), against the
earlier `vrptwl/` run. This is an obvious engineering change, not a new method.

| | result |
|---|---|
| runs on time in their own convention | 17 of 17; no result below its bound; every clique confirmed exactly |
| vehicles on the 8 instances where the fleet search reached the capacity bound quickly | same as `vrptwl/` on all 8 |
| distance on those 8 | shorter on all 8; median 6.41% shorter, **but see below** |
| R1_10_1 fleet phase | stopped at 100 vehicles (the double-precision bound) after 44.6 s, instead of 301 s spent trying 99 |
| C2_10_6 (control) | 29 vehicles instead of 30 |
| R1_10_1 under DIMACS / nearest-integer rounding (120 s) | 95 / 93 vehicles (bound 91 in both) |

**The distance comparison is confounded.** This run's machine made 1.5 to 5.6 times as many iterations per second as
the `vrptwl/` run's, on every instance including the controls, so the 6.41% mixes the budget change with machine
speed and must not be quoted as the gain from the budget change. The same-machine control `xltwctl/` (below) measured
the budget change alone: a median of **3.44%** on the same 8 instances, about half of the 6.41%.

Scoring: [xltwbase/score.md](xltwbase/score.md): all six pre-registered expectations (Q0 to Q5) held as written
([xltwbase/expectations.md](xltwbase/expectations.md)); the score explains the speed confound with a per-instance
table. Raw output: [xltwbase/results.md](xltwbase/results.md), [xltwbase/results.json](xltwbase/results.json);
solutions in [xltwbase/sols/](xltwbase/sols/) (CVRPLib format, `Cost` = distance in the run's own convention). None is a
record.

## xltwctl/: the same-machine control for xltwbase/

`xltwctl.py` runs both budgets on the same instance in the same job, one after the other: the `vrptwl/` split (fleet
search to PyVRP's capacity bound for at most 300 s, then `solve` for 300 s) and the `xltwbase.py` budget (fleet
search stopped at the bound, `solve` gets the rest of 600 s). 9 Gehring-Homberger 1,000-customer instances, double
precision, one seed, one CPU per run. The first job was stopped from outside after 7 of 9 pairs; a second job ran the
other 2 pairs, and `merge_ctl.py` scored all 9 once (an addendum, written before the second job, discloses that three
predictions were nearly settled by then).

| | result |
|---|---|
| runs on time in exact arithmetic, same vehicles in both arms | 18 of 18; 9 of 9 pairs |
| bound arm shorter, 8 instances where both arms run the same fleet search | 7 of 8 shorter, 1 equal; **median 3.44%** |
| by family | R1/RC1 3.4% to 5.9%; R2, RC2, C1 0% to 0.42% |
| R1_10_1 (fleet search stopped at 100 after 57.5 s instead of 300.7 s) | 1.35% shorter (predicted at least 2%) |
| iterations per second, split / bound | median 0.859; the longer arm was faster per iteration in all 9 pairs |

Scoring: [xltwctl/score.md](xltwctl/score.md): K0, K1, K2 and K5 held; K3 (median below 3.2%) and K4 (R1_10_1 at
least 2% shorter) did not ([xltwctl/expectations.md](xltwctl/expectations.md)). Merged table:
[xltwctl/merged.md](xltwctl/merged.md), [xltwctl/merged.json](xltwctl/merged.json); second job's output:
[xltwctl/results-v2.md](xltwctl/results-v2.md), [xltwctl/results-v2.json](xltwctl/results-v2.json); first job's
log: [xltwctl/v1_log.txt](xltwctl/v1_log.txt); solutions in [xltwctl/sols/](xltwctl/sols/). None is a record.

## xltwrm/: three fleet searches compared; the plain loop won

The challenge ranks vehicles first, and the fleet search is the weakest part of the baseline: `vrptwl/` used more
vehicles than SINTEF's records on 13 of the 60 1,000-customer instances. `xltwrm.py` ran three fleet searches on
those 13, in one job, 300 s each, double precision, one seed: **fleet** (PyVRP's `minimise_fleet` loop as in
`xltwbase.py`), **warm** (the same loop, each attempt starting from the last solution with its smallest route
removed) and **eject** (a thin prize-collecting ejection loop after Nagata and Bräysy, 2009: the smallest route
removed, every customer optional with a prize that grows each time it is left out, penalties fixed far above the
prizes).

| | fleet | warm | eject |
|---|---|---|---|
| vehicles, 13 instances (SINTEF: 728) | **743** | 761 | 764 |
| fewest vehicles (alone or tied) | 13 of 13 | 4 of 13 | 5 of 13 |
| equal to SINTEF's record | 3 | 1 | 1 |

All 39 runs were on time in exact arithmetic and none was below K or below a record. warm drops routes fast and then
stalls: on 8 instances it reached its final count, still above K, within 15 s and spent the rest on one failed
attempt. eject's rounds were short (5 s at 1,000 customers) and its counters reached only 2 to 11. Its fixed
penalties also ruled out the infeasible "squeeze" moves that Nagata and Bräysy rely on. This says nothing about full
ejection-pool methods, only about this thin version. eject's route plans were the shortest on all 13 instances,
because each of its rounds runs PyVRP's full search while the other two stop at the first feasible solution. That was
not predicted and not compared.

Scoring: [xltwrm/score.md](xltwrm/score.md): M0 and M5 held; M1 to M4, M6 and M7 did not
([xltwrm/expectations.md](xltwrm/expectations.md)). Raw output: [xltwrm/results.md](xltwrm/results.md),
[xltwrm/results.json](xltwrm/results.json), [xltwrm/progress.jsonl](xltwrm/progress.jsonl) (with every run's trace);
solutions in [xltwrm/sols/](xltwrm/sols/). None is a record. `xltwbase.py` keeps the plain loop.

## xltwrs/: a longer fleet budget helps a little; capped restarts do not

`xltwrs.py` ran the plain loop with a 900 s fleet budget (half the challenge's time per 1,000 customers) against the
same loop with each attempt capped at max(30 s, 2 x the last successful attempt) and retried with a new seed, on the
same 13 instances, double precision, one seed, one CPU per run.

| vehicles on the 13 instances (SINTEF: 728) | 300 s | 600 s | 900 s |
|---|---|---|---|
| plain loop | 743 | 739 | **737** |
| capped restarts | 746 | 743 | 742 |

The plain loop kept finding vehicles after 300 s on 5 of 13 instances (last at 758.5 s, C1_10_7). The restarts never
used fewer vehicles than the plain loop and used one more on 5: capping cut off the long attempts that found the late
gains, and at the same fleet size the new attempts kept failing (28 of about 44 on the C2 instances). The plain loop's
first 300 s repeated `xltwrm/` exactly (743). All 26 runs were on time in exact arithmetic; none was below K or a
record.

Scoring: [xltwrs/score.md](xltwrs/score.md): R0, R1, R2 and R5 held; R3 (restart no worse on at least 11 of 13) and
R4 (restart better on at least 3) did not ([xltwrs/expectations.md](xltwrs/expectations.md)). Raw output:
[xltwrs/results.md](xltwrs/results.md), [xltwrs/results.json](xltwrs/results.json),
[xltwrs/progress.jsonl](xltwrs/progress.jsonl); solutions in [xltwrs/sols/](xltwrs/sols/). None is a record.

## xltwrun/: the baseline as a stand-alone solver, run on all of XLTW-Test under the challenge's protocol (pre-registered)

[`xltwrun/solver.py`](xltwrun/solver.py) is the `xltwbase.py` baseline (plain fleet loop stopped at K, the rest of
the time to distance) as a program that follows the algorithm track's rules: `python solver.py instance seconds seed`,
nearest-integer rounding, one thread, every better solution printed to stdout in CVRPLib format (throttled), and a
clean stop before the limit or on SIGTERM. [`xltwrun/xltwrun.py`](xltwrun/xltwrun.py) runs it the way the organisers
will: one process per instance, SIGTERM at the limit and SIGKILL five seconds later, only the last solution printed
before the limit counted, and that solution re-checked in exact arithmetic. All 100 XLTW-Test instances, limits
divided by 30 (60 s per 1,000 customers), seed 20261104. Predictions G0 to G5 are fixed in
[xltwrun/expectations.md](xltwrun/expectations.md) and are scored only on all 100 together. It is PyVRP with a
wrapper, not a new method.

| | so far (not yet scored) |
|---|---|
| part a, 80 instances up to 6,444 customers ([part-a.md](xltwrun/part-a.md)) | **80 of 80** counted and stopped on time by themselves; 6 at K (0 of the 27 capacity-free) |
| part b, 20 instances from 6,587 customers ([part-b-note.md](xltwrun/part-b-note.md), [part-b3-note.md](xltwrun/part-b3-note.md)) | 13 valid runs; 7 runs frozen when the host paused the container (invalid, re-run once under a rule set before any re-run) |
| solver did not stop (SIGKILL) | **2**: n8575 (one PyVRP call ran for more than 450 s) and n10001 (still running at least 7.8 s past its own stopping point). Pre-registered G0 ("no SIGKILL") therefore fails |
| largest peak memory per solver process | 4.62 GB (10,000 customers); peaks fit 0.17 GB + 4.7 GB x (n / 10,000)^2 |

The two SIGKILLs are why the packaged solver (`xltwpkg/`) has a watchdog thread. The baseline in `xltwrun/` stays
as pinned. Raw output: `results-a.*`, `results-b1.*`, `results-b2.*`, `results-b3.*`, the progress files, `logs-b3/`,
and every counted solution in [xltwrun/sols/](xltwrun/sols/) (exact-checked; none is a record). When the re-runs are in,
`xltwrun.py --merge` scores G0 to G5 once, against both K and K*; that is the first version of the XLTW-Test report.

## xltwpkg/: the solver packaged for the algorithm track (offline build, protocol-exact; pre-registered)

The challenge builds entries with `make` or `build.sh`, without Internet or root, and runs `./solver INSTANCE SECONDS
SEED`. [`xltwpkg/`](xltwpkg/) packages the same method (solver 0.1.0, unchanged search) so that it does: `lock.py`
pins PyVRP 0.14.1 and its dependencies to wheels checked against the SHA-256 that PyPI publishes, `build.sh` unpacks
them into `lib/` with no network, and the solver keeps stdout for solutions only (library logging goes to stderr).
A watchdog thread ends the process on time even when PyVRP is stuck inside one long C++ call, which a Python signal
handler cannot do (see the two SIGKILLs above).

The conformance test (C0 to C8) is pre-registered in [xltwpkg/expectations.md](xltwpkg/expectations.md). The first
jobs scored nothing: in the python:3.12 image, `build.sh` picked the image's other interpreter (3.13) and two tests
failed on an import, and a DNS failure stopped the 3.11 job ([xltwpkg/score-v1.md](xltwpkg/score-v1.md)). Package 0.1.1
records and uses the build's interpreter everywhere; what changed is in
[xltwpkg/addendum-2026-11-06.md](xltwpkg/addendum-2026-11-06.md). The v2 jobs (Python 3.12, Python 3.11, and the
n8575 run that got stuck) are queued.

## xltwfull/: the packaged solver at the full time limit (pre-registered, queued)

Part a ran at 1/30 of the limit. [`xltwfull/`](xltwfull/) runs the published package at the full limit T(n) on the
four smallest capacity-free instances where K* is above K (n1234, n1421, n1608, n1841; 10,980 s in all), same seed,
exactly under the protocol, to see whether the vehicle gap to K* is mostly a time effect. Predictions F0 to F5, fixed
before any run: [xltwfull/expectations.md](xltwfull/expectations.md).

## bkslog/: CVRPLib's best-known-solution announcements as a table

`bkslog.py` reads every page of CVRPLib's [updates page](https://galgos.inf.puc-rio.br/cvrplib/en/updates/) once
(2 s apart) and writes one row per announced `instance (value)` pair for X and XL CVRP instances. It is an open,
machine-readable copy of a public log, read on 2026-11-01: 469 pairs from 2015-01-05 to 2026-10-31, 170 of them on
82 XL instances.

| | result |
|---|---|
| reported values for the same XL instance over time | always lower (83 of 83 consecutive pairs) |
| XL instances with a report between the CVRP challenge's end (2026-02-11) and 2026-09-30 | 75, but 70 of the 78 reports come from one entry of 2026-09-11 |
| XL reports by month | none from February to June 2026; 1 in July, 77 in September, 92 in October |
| share of those reports on instances with 5,000 or more customers | 39.7% (reports at every size) |

Scoring: [bkslog/score.md](bkslog/score.md): B1 and B2 held, B3 (at least 60% on 5,000+ customers) did not
([bkslog/expectations.md](bkslog/expectations.md)). Data: [bkslog/log_raw.csv](bkslog/log_raw.csv) (every pair as
printed, with date and credit), [bkslog/log.csv](bkslog/log.csv) (one row per instance and value),
[bkslog/per_instance.csv](bkslog/per_instance.csv), [bkslog/summary.json](bkslog/summary.json). Values are as
announced and not re-checked; the raw HTML is not redistributed.

## bkswatch/: the VRPTW BKSs re-read after CVRPLib's switch to automatic publishing

Since 2026-10-28 CVRPLib verifies new best known solutions on submission and publishes them in a daily digest.
`bkswatch.py` downloaded all 356 VRPTW BKS files again on 2026-11-02 (fresh, 2 s apart), checked each with the
unchanged `vrptwd/double_check.py` under DIMACS and in double precision, and compared them with the files read on
2026-10-30 and with the `vrptwlb/` fleet bounds.

| | result |
|---|---|
| files read and feasible under DIMACS | 356 of 356 |
| cost line equal to the cost of the file's own routes | 355 of 356. R1_10_6's file says `Cost 468603`; its routes give 46,860.3, the value in CVRPLib's instance table |
| BKSs changed since 2026-10-30 | 5: the four announced on 2026-11-01 (C1_10_9, R1_10_1, R1_10_5, R1_10_9) and R1_10_6, not yet announced when read |
| changed BKSs with one route more than the solution they replaced | 3 of 5 (C1_10_9 90 to 91, R1_10_6 91 to 92, R1_10_9 91 to 92); R1_10_1 went from 95 to 94 |
| changed BKSs late in double precision | 3 of 5 (R1_10_1, R1_10_6, R1_10_9); before, 1 of the 5 (R1_10_1) |
| all BKSs late in double precision | 92 of 356, up from 90 |

CVRPLib's VRPTW BKSs are ranked by distance only, so a shorter solution with an extra route is an improvement there.
The VRPTW BKS Challenge ranks vehicles first. Under that rule, the three solutions with an extra route would rank
below the ones they replaced. None of this is an error by CVRPLib, and its instance table has the right value for
R1_10_6. The only slip is the cost line in that one downloadable file.

Scoring: [bkswatch/score.md](bkswatch/score.md): W1, W2 and W3 held; W0 (every cost line matches) and W4 (route
counts unchanged) did not; W5 was untestable as coded, because it is scored only when W0 holds
([bkswatch/expectations.md](bkswatch/expectations.md)). Raw output: [bkswatch/results.md](bkswatch/results.md),
[bkswatch/results.json](bkswatch/results.json), [bkswatch/bks.csv](bkswatch/bks.csv) (one row per instance). Five
changed BKSs are too few to call this a trend.

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

- Score `xltwpkg/` (C0 to C8) from the v2 jobs. If the package passes, publish it as its own repository for the
  algorithm track.
- Score `xltwrun/` (G0 to G5) once the re-runs are in, against both K and K*: the first version of the XLTW-Test
  report.
- Score `xltwfull/` (F0 to F5).
- Fleet ideas for the capacity-free instances, each pre-registered: stop the fleet loop at K* instead of K, cap the
  time of one fleet attempt, and a penalised "squeeze" step (Nagata and Bräysy, 2009), after a prior-art check.
- `bkswatch/` again about once a week while new VRPTW BKSs keep arriving, using the 2026-11-02 read as the reference.

Reproduce (Python 3.12):

```
pip install pyvrp==0.14.1 vrplib==2.2.0 numpy==2.1.3
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
python exact_repair_check.py --tries 44 --wait 300 --data-dir data --out-dir out
cd ../vrptwd5
python -m unittest -v test_anatomy
python anatomy.py --ids 380-735 --data-dir data --out-dir out
cd ../vrptwl
python -m unittest -v test_fleet_double
python fleet_double.py --ids 676-735 --seconds 600 --workers 3 --data-dir data --out-dir out
cd ../vrptwlb
python -m unittest -v test_bounds
python bounds.py --ids 380-735 --fleets vrptwl_fleets.json --data-dir data --out-dir out
cd ../xltwlb
python -m unittest -v test_xltwlb test_compare
python compare.py --ids 380-735 --data-dir data --out-dir out
python xltwlb.py --synthetic 1000,5000,10000 --out-dir out
cd ../xltwbase
cp ../xltwlb/xltwlb.py .
python -m unittest -v test_xltwbase
python xltwbase.py --study --seconds 600 --conv-seconds 120 --workers 3 --data-dir data --out-dir out
cd ../xltwctl
cp ../xltwlb/xltwlb.py ../xltwbase/xltwbase.py .
python -m unittest -v test_xltwctl test_merge_ctl
python xltwctl.py --seconds 600 --workers 2 --data-dir data --out-dir out
# as published: the first job's 7 pairs are in v1_log.txt; the second job ran
#   python xltwctl.py --seconds 600 --workers 2 --only C1_10_4,R1_10_1 --data-dir data --out-dir out
#   python merge_ctl.py --prior v1_log.txt --results out/xltwctl/results.json --out-dir out/xltwctl
cd ../xltwrm
cp ../xltwlb/xltwlb.py ../xltwbase/xltwbase.py .
python -m unittest -v test_xltwrm
python xltwrm.py --seconds 300 --workers 3 --data-dir data --out-dir out
cd ../xltwrs
cp ../xltwlb/xltwlb.py ../xltwbase/xltwbase.py ../xltwrm/xltwrm.py .
python -m unittest -v test_xltwrs
python xltwrs.py --seconds 900 --workers 4 --data-dir data --out-dir out
cd ../xltwtest
pip install py7zr
cp ../xltwlb/xltwlb.py .
python -m unittest -v test_xltwtest
python xltwtest.py --data-dir data --out-dir out
cd ../xltwrun
cp ../xltwlb/xltwlb.py ../xltwbase/xltwbase.py .
python -m unittest -v test_xltwrun
python xltwrun.py --scale 30 --workers 4 --mem-gb 3.3 --max-n 6500 --part a --data-dir data --out-dir out
# part b ran as parts b1, b2, b3 with --workers 1 and --min-n/--max-n per part (see part-a.md);
# frozen runs are re-run as parts b1ra, b1rb, b2r, b3ra, b3rb
# one instance, exactly as the challenge runs it (here at the full limit for 1,047 customers):
python solver.py data/xltw-test/x-9635b9fa813e/XLTW-Test-n1048.vrp 1884.6 1234 > n1048.sol
cd ../xltwpkg
python fetch_helpers.py data && python lock.py --resolve --fetch    # with Internet, once
bash build.sh --offline && python -m unittest -v test_pkg
./solver data/xltw-test/x-9635b9fa813e/XLTW-Test-n1048.vrp 1884.6 1234 > n1048.sol
cd ../bkslog
python -m unittest -v test_bkslog
python bkslog.py --out out/bkslog --max-pages 30 --pause 2.0
cd ../bkswatch
cp ../vrptwd/double_check.py .
cp ../vrptwd3/results.json vrptwd3_results.json
cp ../vrptwd/results.json vrptwd_results.json
cp ../vrptwlb/bounds.csv .
python -m unittest -v test_bkswatch
python bkswatch.py --ids 380-735 --stamp 20261102 --data-dir data --out-dir out
cd ../xl
python -m unittest -v test_xl_scale
python xl_scale.py --id 379 --sizes 1000,2500,5000,10000 --seconds 300,600,900,1800 --data-dir data --out-dir out
```

Limits: one seed, one CPU per run, wall-clock budgets (results vary with machine speed, as `xltwbase/` and
`xltwctl/` show). The results files say "PyVRP unknown" because 0.14.1 has no `__version__`; the version was pinned
as above. `bkswatch/` reads CVRPLib's files as they are on the day it runs, so a re-run on a later day can differ.
`xltwrun/solver.py` needs Python and PyVRP installed; the offline package in `xltwpkg/` is not scored yet.
Runs on a shared machine can be paused by the host; such runs are marked invalid and re-run once, never counted.

Data: instances and best known solutions are downloaded from CVRPLib at run time and are not redistributed here.
SINTEF's record table in `vrptwl/fleet_double.py` is quoted (vehicles and distance only) with its source URL;
`vrptwlb/` reads SINTEF's pages at run time and stores only the vehicle counts and distances it compares.
`bkslog/` keeps the announced instance names, values, dates and credits only. `bkswatch/` keeps one row per BKS
(route count, costs, check results), not the solutions. `xltwtest/` keeps file names, sizes, hashes, header and
section names, summary statistics and bounds, not the instances. `xltwrun/`, `xltwen/` and `xltwfull/` keep per-run
results and the solver's solutions, not the instances.
