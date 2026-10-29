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

Reproduce (Python 3.12):

```
pip install pyvrp==0.14.1
cd vrp
python -m unittest -v test_vrp_probe
python vrp_probe.py --ids 280,281,282 --warm-seconds 1800 --cold-seconds 900 --workers 2 --data-dir data --out-dir out
```

Limits: one seed, one CPU per run, wall-clock budgets (results vary with machine speed). The results files
say "PyVRP unknown" because 0.14.1 has no `__version__`; the version was pinned as above.

## Coming next

- `vrptw/`: PyVRP on all 56 Solomon instances and six 1,000-customer Homberger instances, checking
  CVRPLib's VRPTW distance convention and whether its BKSs minimise vehicles or distance.
- `xl/`: memory and speed of PyVRP at 1,000 to 10,000 customers, to size runs for the XLTW instances.

Data: instances and best known solutions are downloaded from CVRPLib at run time and are not redistributed here.
