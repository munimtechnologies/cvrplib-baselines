# kmatch: a path-cover fleet bound on XLTW-Test (exploratory pilot)

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.

**This is a pilot, not a pre-registered study.** It is written down before the job runs so the guesses below can be
checked against what comes out, but nothing here is scored as a prediction. A study is pre-registered only after this
pilot, if the pilot shows the bound is worth testing.

## Why

On the four capacity-free XLTW-Test instances, MV2's best valid fleets (33, 65, 108, 25) sit 7 to 28 vehicles above
the lower bounds K* (27, 47, 81, 18), and a dedicated route minimiser (nbrm/) ended one vehicle *above* the PyVRP
loop. Either the search is still weak or K* is loose. K* = max(clique bound, energetic busy-period bound) after
Kontoravdis & Bard (1995) and Afifi, Guibadj & Moukrim (2014) (xltwlb/, xltwen/). This pilot computes a bound of a
different kind, to see if it moves K* anywhere.

## The bound

Customer j may directly follow customer i only if `max(a_j, e_i + s_i + t_ij) <= lat_j`, with e the earliest start
reachable from the depot, lat the latest start that still meets the due time and the trip back, and t the
challenge's nearest-integer travel time (the same e and lat as `xltwlb.py`). Each route is a path in this arc graph,
so the fleet is at least the minimum number of vertex-disjoint paths that cover all customers, which is at least
KM = max(n - M, 1), M = a maximum bipartite matching (Hopcroft-Karp, SciPy). This is the classical assignment
relaxation of fleet sizing (Dantzig & Fulkerson, tanker scheduling, 1954). It ignores capacity, and the matching may
close cycles (i before j and j before i both allowed), which weakens it when windows are wide. Nothing about the
method is new; only its numbers on XLTW-Test would be.

## Checks built in

- Every consecutive pair of every route of the 80 exactly checked part-a solutions (`xltwrun/sols`, commit
  56b4e6e) must be an arc of the graph, and KM must not exceed their route counts or the best fleets above.
  Any failure flags the instance as invalid.
- Arcs are cross-checked against a brute-force double loop and the matching size against a plain augmenting-path
  matching in the unit tests. With integer coordinates the rounded travel times are exact in float64 (recorded per
  instance).

## Guesses written before the run (calibration only)

| | guess | how sure |
|---|---|---|
| g1 | KM <= K* on all four nbrm instances (n1234, n1421, n1608, n1841) | 0.60 |
| g2 | KM > K* on at least one of the 33 capacity-free instances | 0.35 |
| g3 | no validity flag on any of the 80 solutions | 0.95 |
| g4 | the maximum matching closes at least one cycle on at least 50 of the 100 instances | 0.70 |

If KM beats K* somewhere, the next step is a pre-registered study of a cycle-free strengthening on those instances.
If it does not, that is evidence the K* gap is mostly not about this relaxation, and the next pilot looks elsewhere.
