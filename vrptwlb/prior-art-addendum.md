# Prior-art addendum to vrptwlb (written 2026-10-30 ~21:45 UTC, before any result was seen)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0.

[`expectations.md`](expectations.md) names Kontoravdis and Bard (1995) as the source of the time-window clique
bound. After it was written, we found closer prior work that it should have cited:

- S. Afifi, R. N. Guibadj and A. Moukrim, "New Lower Bounds on the Number of Vehicles for the Vehicle Routing
  Problem with Time Windows", CPAIOR 2014, LNCS 8451, pp. 422-437,
  [doi:10.1007/978-3-319-07046-9_30](https://doi.org/10.1007/978-3-319-07046-9_30), open copy on HAL:
  [hal-00992081](https://hal.science/hal-00992081v1).

Its abstract says it analyses lower bounds on the fleet built from customer incompatibility and vehicle capacity
(the two bounds this job computes), adds stronger ones (energetic reasoning over time intervals, combined with the
incompatibility graph and bin-packing models), and that these give the minimum number of vehicles for 339 of 468
standard instances. We could not open the full text in this run, so we have not confirmed which 468 instances
those are, which records they were compared with, or whether a per-instance table is given. A likely split is
Solomon's 56 instances at 25, 50 and 100 customers (168) plus the 300 Gehring-Homberger instances, but we have
not checked it.

What this changes:

- The bounds in `bounds.py` are the classical ones that Afifi et al. improve on. Where our K is below SINTEF's
  record, their stronger bounds may already close the gap. So our "open" list is open only for the classical
  bounds, not in the literature.
- The claim in `expectations.md` that we found "no open per-instance table" stands only in a narrow sense: an
  open, re-runnable table, with code and verified cliques, against SINTEF's records as read during the run,
  separately in double precision and under DIMACS truncation. It is a reproduction and a calibration aid for
  the CVRPLib VRPTW BKS Challenge, not a new bound and not a first proof of any minimum.
- The predictions (B0-B5) and the code are unchanged. The results will be scored exactly as pre-registered.
