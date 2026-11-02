# xltwrm: expectations, written before the run

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Fixed on 2026-11-02 (UTC) before `xltwrm.py` was run on any instance.

## Why

CVRPLib's VRPTW BKS Challenge ranks solutions by the number of vehicles first and distance second. The fleet
search in our baselines (`vrptwl/`, `xltwbase/`, `xltwctl/`) is PyVRP 0.14.1's `minimise_fleet` loop: one vehicle
fewer, solve from a random start until the first feasible solution, repeat. In `vrptwl/` (300 s of fleet search)
it used more vehicles than SINTEF's hierarchical record on 13 of the 60 Gehring-Homberger 1,000-customer
instances, 21 vehicles in total (C1 12, C2 4, RC1 1, RC2 4). Under the challenge's ranking, those vehicles matter
more than any distance gain, so the fleet search is the weakest part of the baseline.

## What runs

`xltwrm.py` runs three fleet searches on each of those 13 instances, in the same job, interleaved, one CPU per
run, double precision (PyVRP sees every number x1,000 rounded up, as in `vrptwl/`), seed 20261102, a 300 s fleet
budget per run, all stopped at K = max(L2, time-window clique) from `xltwlb.py`:

- **fleet** (reference): the `minimise_fleet` loop exactly as in `xltwbase.fleet_down`, keeping the last feasible
  solution.
- **warm**: the same loop, but every attempt starts from the last feasible solution with its smallest route removed.
  PyVRP's search must put the removed customers back, because they are required.
- **eject**: the smallest route is removed and every customer becomes optional, with a prize of
  `p * (1 + c)`, where `p` is twice the bounding-box diagonal (above any insertion detour) and `c` is how many earlier
  rounds ended with that customer left out. Each round is at most 5 s of PyVRP's search, starting from the previous
  round's best solution. It ends early once every customer is served on time with one route fewer. The counters are
  kept across levels. PyVRP's time-window and load penalties are fixed at 20 times the largest prize of the round
  (its default cap, 100,000 per unit, is far below the prizes), so a violation never pays for a prize and the search
  leaves customers out instead of serving them late. This is the ejection-pool idea of Nagata and Braysy (2009, *Operations Research Letters*
  37(5):333-338, doi:10.1016/j.orl.2009.04.006) in its simplest form, a prize-collecting relaxation, layered over
  PyVRP's search with no new operators.

Every result is re-checked in 50-digit decimal arithmetic by `xltwbase.check_exact` (every customer once, capacity,
every arrival including the depot return). SINTEF's vehicle counts are the ones quoted in `vrptwl/`.

**Prior art and what is new.** Route minimisation by ejection pools and the prize-collecting view of it are well
known (Lim and Zhang 2007; Nagata and Braysy 2009). Nothing here is a new method. What is measured is whether a thin
version of the idea, written over an off-the-shelf solver, closes the vehicle gap at 1,000 customers. It is a
calibration for the challenge baseline, not a contribution to route minimisation.

## Predictions (each scored on its own; none depends on another)

M1 to M4 are scored on the instances where both compared arms returned an on-time solution. If fewer than 10
instances can be compared, they are "untestable".

- **M0 (integrity):** all 39 runs finish without error, every result is on time in exact arithmetic with every
  customer served once, and none uses fewer vehicles than K.
- **M1:** eject uses no more vehicles than fleet on at least 12 of 13 instances.
- **M2:** eject uses fewer vehicles than fleet on at least 6 of 13 instances.
- **M3:** eject matches SINTEF's vehicle count on at least 4 of 13 instances.
- **M4:** summed over the compared instances, eject uses at least 8 fewer vehicles than fleet.
- **M5:** no run of any arm uses fewer vehicles than SINTEF's record. A result below a record would be checked a
  second way before anything is said about it.
- **M6:** warm uses fewer vehicles than fleet on at least 4 of 13 instances.
- **M7:** eject uses fewer vehicles than warm on at least 4 instances and more on at most 1 (the prizes add
  something beyond the warm start).

Why these numbers: `minimise_fleet` restarts from a random solution at every fleet size and gives up at the first
size it cannot reach in the time left, so a warm start should help where the gap is one or two vehicles. The C1
instances with a gap of four (C1_10_2, C1_10_8) and the two whose records sit far above the capacity bound
(C1_10_6, C1_10_7) are the hardest, so I do not expect any arm to reach every record in 300 s. These are guesses;
the score will say where they were wrong.

## Limits

One seed and one 300 s budget per run on a shared machine. The three arms of an instance run close together in
time, so machine speed affects all three alike, but not exactly alike. 13 instances chosen because the reference
did badly on them, so a gain here may be smaller on instances where it already does well. Distances are reported
but not compared: a run with fewer vehicles usually has a longer route plan, and no arm gets a distance phase.
