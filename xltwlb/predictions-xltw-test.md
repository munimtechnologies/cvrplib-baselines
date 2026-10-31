# Predictions for fleet lower bounds on XLTW-Test (fixed 2026-10-31 ~11:20 UTC, before the instances are out)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0.

CVRPLib announced its XLTW-Test instances (1,000 to 10,000 customers with time windows, built on the XL depot and
customer locations) for 2026-10-31. At about 10:55 UTC that day neither the instances nor the detailed rules were on
CVRPLib's overview, updates or VRPTW instances pages, so these predictions are written without having seen any
XLTW-Test file. The git commit that adds this file dates them.

**Run planned.** Once XLTW-Test is published, `xltwlb.py` (checked against `vrptwlb/`, see [score.md](score.md))
computes KC, KB, KT and K = max(KB, KT) for every test instance, in the challenge's own travel-time convention if the
rules name one, and in all three conventions it knows ('double', 'dimacs', 'round'). Files are downloaded one at a
time, at least 2 s apart. If the files are in neither VRPLIB nor Solomon format, the parser is extended and tested
first. The challenge's convention below means the one in its rules; if the rules name none, 'double'.

| | Prediction | Basis | Our odds |
|---|---|---|---|
| P1 | Every XLTW-Test instance is bounded in the challenge's convention and in 'double' with no error and no unservable customer, using at most 1 GB and 30 minutes in total. | 10,000 synthetic customers took 26 s and 0.30 GB; the risk is the file format. | 70% |
| P2 | KB > KC on at least one instance. | XL was generated with the X-set scheme (arXiv 2601.11467), whose demand types include SL (mostly small demands, a few large) with very short routes, for example XL-n1048-k237 (Q = 128, about 4.7 customers per route); L2 can then exceed KC. Whether XLTW keeps XL's demands and capacities is not yet known. | 45% |
| P3 | In the challenge's convention, KT > KB (the time-window bound binds) on at most a quarter of the instances. | On the classic sets it binds on 14 of 356 (double), only on the tightest windows. | 75% |
| P4 | K in the challenge's convention equals K in 'double' on at least three quarters of the instances. | On the classic sets they differ on 7 of 356 at most ([score.md](score.md)). | 75% |

Only reported, not predicted: the distribution of K / KC, which instances have KT > KB, and the bounds in the
conventions the rules do not use.

**Limits.** These are classical lower bounds (Kontoravdis and Bard, 1995; Martello and Toth, 1990; Afifi, Guibadj and
Moukrim, CPAIOR 2014, give stronger ones), found by greedy clique search, so they may be weaker than the true minimum.
A bound says nothing about distance, the challenge's second objective. If XLTW-Test is not released, or released in a
form the predictions do not fit (for example without capacities), that is recorded and nothing is scored.
