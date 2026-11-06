# xltwen: time-based fleet lower bounds on XLTW-Test (pre-registered)

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Code Apache-2.0; text CC BY 4.0.

Written 2026-11-06 (UTC) before any of these bounds was computed. The job that computes them downloads `xltwen.py`,
`test_xltwen.py` and this file from this repository's `main` branch, so it can only run after they are public, and it
records the SHA-256 of the `xltwen.py` it ran.

## Why

Part a of `xltwrun/` (80 of the 100 XLTW-Test instances, limits T(n)/30) ended with a median gap of 47.4% between the
vehicles used and the fleet lower bound K from `xltwtest/`, and with 0 of 27 runs at K on instances where capacity
never binds (KC = 1). On those instances K comes only from a clique of pairwise-incompatible customers, and it can be
very weak: n3147 has K = 1 and the run used 84 vehicles. So part of the gap may be the bound, not the solver. This
study measures how much, with a bound that uses time and travel, not only pairwise conflicts.

## Method (prior art, applied here)

Energetic reasoning for the VRPTW fleet is published: S. Afifi, R. N. Guibadj, A. Moukrim, *New Lower Bounds on the
Number of Vehicles for the Vehicle Routing Problem with Time Windows*, CPAIOR 2014, LNCS 8451, pp. 422-437
(doi:10.1007/978-3-319-07046-9_30). Time-window fleet bounds go back to Kontoravdis & Bard (1995). We claim no new
bounding method. What is new is only: these bounds on XLTW-Test (released 2026-11-02), in the challenge's
nearest-integer convention with exact integer arithmetic, each checked against exactly verified solutions.

Each vehicle is a machine; each customer i is a job that keeps its vehicle busy over [S_i - pre_i, S_i + s_i + post_i]
(S_i = service start, s_i = service time). tau_i is the shortest arc into i from the depot or from any customer that
can precede i in a time-feasible route; sig_i the shortest arc out of i to the depot or to any customer that can follow
it. Variants: `in` (pre = tau, post = 0), `out` (pre = 0, post = sig), `half` (pre = tau/2, post = sig/2). For an arc
i -> j in any feasible solution, post_i + pre_j <= t_ij, so one vehicle's busy periods never overlap. With
e_i = max(ready_i, open + t_0i) and lat_i = min(due_i, close - s_i - t_i0) (as in `xltwlb`), job i has release
e_i - pre_i, length pre_i + s_i + post_i and deadline lat_i + s_i + post_i. For each variant we compute:

- the **compulsory-part** bound: the most jobs whose latest start is at or before some instant t and whose earliest
  end is after t (exact sweep);
- the **duration** bound: total job length over the whole horizon, rounded up;
- the **energetic** bound: max over intervals [t1, t2] of ceil(sum_i W_i / (t2 - t1)), W_i the mandatory overlap.
  Intervals: a 128 x 128 grid of candidate start and end points, then two rounds of coordinate refinement over up to
  2,048 candidates each. This is a search; a better interval may exist, so E can only be too low, never too high.

E = the largest of these over the three variants; K* = max(K, E). The winning interval of each variant is recomputed
in int64 arithmetic. Travel times are floor(d + 0.5), computed exactly from integer coordinates; direct depot arcs are
valid because every service time is at least 1 (the same condition `xltwlb` checks).

## Checks against real solutions

For every part-a instance the job downloads the published solution (`xltwrun/sols/`, commit 56b4e6e), re-simulates
each route (earliest service starts), and checks for all three variants that every busy period lies inside its
customer's [release, deadline] and that consecutive ones on a route do not overlap. A single failure means the
relaxation or the code is wrong.

## Predictions

Counts use the K and KC values in `xltwrun.py` (from `xltwtest/`): 33 instances have KC = 1, 67 do not. "Part a" means
the 80 instances with at most 6,444 customers and the vehicles in `xltwrun/results-a.md`.

- **E0 (gate).** All 100 instances bounded without error; all inputs integral and every service time >= 1; no
  unservable customer; every winning interval verified in int64; E <= the part-a vehicles on all 80; all 80 part-a
  solutions downloaded, simulated on time, cover every customer once, have the published number of routes, and pass
  the busy-period check in all three variants. If E0 fails, E1-E6 are not scored and the failure is reported.
- **E1.** E > K on at least 10 of the 33 instances with KC = 1.
- **E2.** E > K on at most 10 of the 67 instances with KC > 1.
- **E3.** On n3147 (K = 1, part a used 84 vehicles), E >= 20.
- **E4.** Over the 27 part-a instances with KC = 1, the median of vehicles / K* is at most 3.0 (against K it is 6.1).
- **E5.** On at least 5 instances, the winning variant's best bound comes from an interval shorter than the whole
  horizon and is strictly larger than both its duration and its compulsory-part bound.
- **E6.** The whole job (100 instances, three variants, 80 solution checks) takes at most 60 minutes on one CPU, with
  peak memory at most 1.5 GB.

Reported but not predicted: part a's median (vehicles - K*)/K* and number of runs at K*; which variant wins how often;
the sum of K* against the sum of K.

## What this does and does not say

A higher lower bound shrinks the measured gap but proves nothing about what is achievable; only a better solution can
close a gap from above. E is a heuristic search over intervals, so E1-E5 can fail because the search is too coarse,
not only because the bound is weak. Nothing here says anything about CVRPLib's data, which we read as published.
