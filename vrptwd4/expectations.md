# Expectations written before vrptwd4-repair-v1 ran (2026-10-30 ~07:00 UTC)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.

**Background.** CVRPLib's VRPTW best known solutions (BKSs) use the DIMACS convention: every arc is truncated
to one decimal. [`vrptwd/`](../vrptwd/score.md) and [`vrptwd3/`](../vrptwd3/score.md) (checked a second way in
[`vrptwd2/`](../vrptwd2/score.md)) found 90 of the 356 Solomon and Homberger BKSs that arrive late somewhere when
travel times are computed in double precision: 8 of 56 Solomon, 82 of 300 Homberger. Each late arrival is small
(at most 1.27 time units). The open question is whether these are only a convention artefact that a small change
of order fixes, or whether some BKSs use fewer routes than double precision allows. A prior-art search on
2026-10-30 found no published repair of them; SINTEF's double-precision records use the hierarchical objective
(fewest vehicles first), so they are not distance-only references at the BKS's route count.

**Method.** `repair.py` reads all 356 instances and BKSs from CVRPLib (ids 380 to 735; cached copies from the
earlier runs) and re-runs the unchanged `vrptwd/double_check.py`. For each BKS that is late in double precision,
PyVRP 0.14.1 starts from the BKS with the fleet capped at the BKS's route count, on a scaled instance in which
every number is multiplied by 1,000 and rounded **up**. Instance data are integers, so only travel times change,
each by less than 0.001 and never downwards: a solution on time in the scaled instance is on time in double
precision. Budget: 60 s per instance up to 200 customers, then 0.3 s per customer (300 s at 1,000), one CPU each,
seed 20261030. A result counts as **repaired** only if `double_check.py` finds it on time everywhere with no more
routes than the BKS. Repaired solutions are written to `sols/` (Cost = double-precision distance, 2 decimals).

**Predictions** (scored by `score_r()` in `repair.py`, written before the run):

| | Prediction | Basis |
|---|---|---|
| R0 | 356 BKSs read, exactly 90 late (as published in v0.2.1), every DIMACS cost equals the file, no run errors, and no result that PyVRP calls feasible fails `double_check.py`. | Hygiene. A failure means a file, parser or rounding problem, not a finding. |
| R1 | At least 70 of the 90 are repaired. | Late arrivals are small, usually one per route, so a local reorder should often fix them. Some short-horizon BKSs may need an extra route. |
| R2 | At least 45 of the 50 late BKSs in the wide-horizon families (C2, R2, RC2) are repaired. | Few, long routes with slack in time; an extra route is rarely needed. |
| R3 | The median distance change of repaired solutions against the BKS's own double-precision distance is between 0% and +0.5%. | The BKS is a strong distance optimum; the repair should cost a little distance and rarely find a shorter one in minutes. |
| R4 | R1_10_1 (95 routes; SINTEF's double-precision record uses 100 vehicles) is **not** repaired. | A 95-route double-feasible solution would beat a long-standing hierarchical record by 5 vehicles. |
| R5 | The repair rate among wide-horizon BKSs (C2, R2, RC2) is at least the rate among short-horizon ones (C1, R1, RC1). | Short horizons leave less slack per route. |
| R6 | No repaired solution beats a SINTEF record (fewest vehicles, then distance) where `double_check.py` has one (the 56 Solomon and six 1,000-customer instances). | Those records are long-standing and in double precision. |

Only reported, not predicted: repairs per family, solutions that need fewer routes than the BKS, the largest and
smallest distance change, and whether every repaired solution is also DIMACS-feasible (it must be, since
truncation only shortens arcs).

**Limits stated in advance.** One seed, a few minutes per instance, one solver. A BKS that is not repaired is
*not* shown to be impossible at its route count; it only was not repaired in this budget. A repaired solution is
a double-precision solution at the BKS's route count, not a new record under either convention, and it says
nothing against the BKS, which is feasible under the rules it was found with. Results will be reported in full,
including predictions that fail.
