# Expectations written before xltw-scale-v1 ran (2026-10-29 ~03:00Z)

MV2 of Munim, Inc. Made with AI agents working in MV2's name.

Purpose: CVRPLib's VRPTW BKS Challenge will use XLTW instances of 1,000 to 10,000 customers (XL locations
plus time windows; XLTW-Test due 2026-10-31, official set 2027-02-24). MV2's jobs run on a shared machine
where a 1-2 GB job starts within minutes and bigger asks wait, capped at 6 GB. Before the real instances
arrive, measure how plain PyVRP 0.14.1 scales on one CPU: memory, build time, feasibility within a budget.
Calibration, not a claim. The time windows are SYNTHETIC (make_windows in xl_scale.py), so route counts
and costs here say nothing about XLTW difficulty; only memory and speed carry over.

Setup: real locations and demands of XL-n10001-k1570 (CVRPLib id 379), first n customers, n = 1,000 /
2,500 / 5,000 / 10,000 with 300 / 600 / 900 / 1,800 s. ProblemData built directly from one int64 matrix
(DIMACS tenths, truncated) passed as both distance and duration. Fleet = n. Seed 20261029. Each size in its
own child process; peak = ru_maxrss of that child. Scored from out/xl/results.json.

Arithmetic behind X1: one 10,001 x 10,001 int64 matrix is 763 MiB; if PyVRP copies it into separate
distance and duration matrices, numpy + 2 copies = about 2,290 MiB at the build peak.

- X1 (memory): at n = 10,000, build_peak_mb is between 1,500 and 2,600, and peak_mb after the solve is
  below 3,000. (If the child is killed instead, X1 fails and the exit code is recorded.)
- X2: n = 1,000 and n = 2,500 both end feasible, with check_ok and pyvrp_matches_check true.
- X3: n = 10,000 ends feasible within its 1,800 s budget (check_ok true).
- X4: iterations_per_s at n = 10,000 is at least 10% of iterations_per_s at n = 1,000.
- Hygiene: pyvrp_matches_check is true on every size that finishes; unit tests pass (including the real
  PyVRP tests).

What follows: X1 holds -> XLTW jobs ask 3 GB at 10,000 customers and 1 GB up to 2,500. X1 fails -> the
memory ask is set from the measured peak (never above 6 GB). X3 fails -> plain PyVRP is not enough at
10,000 on one CPU in 30 min; look at longer runs or decomposition before February.
