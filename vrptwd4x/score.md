# vrptwd4x: scoring (written 2026-10-30 ~19:50 UTC, after `vrptwd4-exact-v2` finished)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0.

Run: `vrptwd4-exact-v2`, 2026-10-30 15:47 to 15:56 UTC, one CPU, `vrplib` 2.2.0, exact 50-digit decimal arithmetic.
It downloaded `vrptwd4/results.json` and all 87 files in `vrptwd4/sols/` from this repository and each instance and
BKS from CVRPLib (cached copies). Predictions: [expectations.md](expectations.md). Raw output:
[results.json](results.json), [results.md](results.md).

## Verdicts

| | Prediction | Verdict | What happened |
|---|---|---|---|
| X0 | All 87 parse; each visits every customer once within capacity, has the stated route count and no more routes than its BKS file. | **held** | 87 checked, no structure failure, no route-count mismatch, none with more routes than its BKS. |
| X1 | All 87 are on time in exact double-precision arithmetic. | **held** | 87 of 87 on time (tolerance 1e-6). |
| X2 | Exact distance within 0.006 of the `Cost` line and of `vrptwd4/results.json`. | **held** | No disagreement. |
| X3 | All 87 on time under DIMACS too, with exact DIMACS cost within 0.05 of `vrptwd4/results.json`. | **held** | 87 of 87 on time under DIMACS; no cost disagreement. |
| X4 | R2_2_1, R2_2_2, R2_6_5 on time with 12, 10, 21 routes (BKS files: 13, 11, 22). | **held** | All three confirmed: 12/13, 10/11, 21/22 routes, on time in double precision. |

All five held. The `vrptwd4/` repairs are now checked twice, by two separately written checkers with different
parsers and different arithmetic.

## Reported, not predicted

- **Smallest double-precision slack:** 0.000000 (to six decimals). 14 of the 87 solutions come within 0.01 of a due
  time somewhere. 13 show a slack of 0.000000 to six decimals: R1_2_1, R1_2_2, R1_2_4, RC2_2_1, R1_4_2, RC1_4_1,
  RC1_4_4, RC2_6_1, RC1_8_1, RC2_10_1, RC2_10_2, RC2_10_3 and RC2_10_5 (see the `min slack` column). An arrival at
  the due time is on time under both conventions. These solutions have no room to spare, though, so a checker that
  adds rounding of its own (for example, travel times rounded up) could reject them.
- **Hand checks:** R2_2_1 (12 routes, slack 2.000000), R2_2_2 (10 routes, slack 2.000000) and R2_6_5 (21 routes,
  slack 1.735807) match the `vrptwd4/` figures. C2_10_5's repaired distance (16,585.02) is the same distance that
  the separate `vrptwl/` run reached from scratch with 30 vehicles (16,585.02), which suggests that the two
  searches found the same or an equally short solution.

## What this does and does not show

It shows that the 87 published files are on time in double precision and under DIMACS, with the stated route counts.
It does not show how good they are. Each is a little longer than the BKS it came from (median +0.43%, see
`vrptwd4/`). The three with one route fewer than their BKS are **not** improvements: CVRPLib's VRPTW BKSs minimise
distance only, so fewer routes at a longer distance beats them under neither convention. The hierarchical records
on SINTEF's pages (fewest vehicles first) use fewer vehicles still.
