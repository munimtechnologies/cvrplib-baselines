# stcheck: independent re-check of the stfleet fleet lower bounds

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Code Apache-2.0, text CC BY 4.0.

`stfleet/` (stfleet 0.2.0) published fleet lower bounds for the 33 capacity-free XLTW-Test instances of CVRPLib's
VRPTW BKS Challenge, each with a certificate (interval [t1, t2], side, Lagrangian weights mu and lam, claimed K). Its
own `verify()` confirmed all 33. A fleet lower bound that is off by one vehicle is worse than none, so `stcheck.py`
re-checks every published certificate with code written separately from the statement of the bound, sharing nothing
with `stfleet.py`, `mstfleet.py` or `xltwlb.py`:

- its own VRPLIB parser, refusing any non-integral number;
- exact integer travel times, round(d) = (isqrt(4D) + 1) // 2, with no floating point;
- its own Prim minimum spanning tree over the interval's customers plus a root;
- confirmation iff (K - 1) * mu < N, with N = MST - 2 sum(lam) + service.

`test_stcheck.py` also tests the bound itself, not only the arithmetic. On thousands of interval, side, mu and lam
choices, on 70 random tiny instances, the bound must never exceed the exact minimum fleet, which is computed by
subset dynamic programming over the raw (untightened) data. The Prim must also match a brute-force Kruskal.

What counts: the check passes if all 33 certificates are confirmed (`tally.confirmed == 33`, `refused`, `errors`,
`claim_mismatch` empty) and the tests pass. Any refusal is reported as it is and the affected bound is withdrawn from
`stfleet/` until it is explained.

    python stcheck.py --data-dir /data --out-dir /out
