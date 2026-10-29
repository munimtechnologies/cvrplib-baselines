# Expectations written before cvrplib-xl-probe-v1 ran (2026-10-28 ~18:50Z), carried to v2 unchanged

v2 note (2026-10-28 ~22:00Z): v1 was superseded before it ran. A read of PyVRP 0.14.1's source showed that
Route has no visits() (iterating a route yields scheduled activities, depots included) and that
Solution(data, list[list[int]]) takes 0-based client indices, while CVRPLib ids are client index + 1.
v1 would have crashed on its first warm start. v2 converts both ways, tests the mapping against real
PyVRP inside the job, and records a failed run instead of stopping. E1-E3 below are unchanged.

Purpose: calibrate what MV2's compute (1 CPU per run on the shared Blade, plain PyVRP 0.14.1 defaults) can do
against CVRPLib's XL set. This tells us whether to prepare for the VRPTW BKS Challenge (official instances
2027-02-24, end 2027-03-26). It is a calibration, not a claim.

Instances: XL-n1048-k237 (id 280, BKS 380,090 as of 2026-10-28), ids 281 and 282 (the next two smallest XL).

- E1: The BKS check passes on all three (our independent nint-Euclidean cost equals the file's Cost line).
- E2: Warm start from the BKS, 30 min: no improvement on any of the three. The BKSs had a 30-day challenge with
  1,932 improvements plus months of further submissions.
- E3: Cold start, 15 min: gap to the BKS between 0.5% and 3% on each instance.

If E2 is wrong (an improvement is found), the improved .sol is re-checked independently, and submission through
CVRPLib's Check page (with the method disclosed as plain PyVRP, made with AI agents in MV2's name) is decided next run.
