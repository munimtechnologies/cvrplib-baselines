# nbrm: addendum for job nbrm-v2 (2026-11-08)

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. CC BY 4.0.
Published before nbrm-v2 runs anything. `expectations.md` is unchanged (sha256
`c528421c28342757003e3d70662337571cab5995a8e8bb0e49e0eec0b2ef5108`); the job checks that hash before it starts.

## What happened in nbrm-v1

nbrm-v1 ran on 2026-11-08 from 12:16 to 12:19 UTC. Its setup did everything the pre-registration asks:

- cloned the route minimiser at `89d4c050e9f68ed9470114b5043c9cd8dc56f00a` (submodule `src/lib/small` at `0192daa`);
- the distance patch matched exactly once in `src/problem.c`;
- the Release build with `-DENABLE_MARCH_NATIVE=OFF` succeeded (GCC 14.2, flags `-fno-plt -Ofast -flto`; binary
  sha256 `44f954556d38546a27f91e969d3707001effebae85f0949c77ce795e93f667da`);
- the pre-registration was public and identical.

Then its unit tests failed (8 passed, 2 errors) and nothing was run: the tests, and the wrapper's smoke step, called
`xltwbase.synthetic`, but in cvrplib-baselines v0.3.7 that function lives in `xltwlb` (`xltwlb.synthetic`).
`expectations.md` also names it `xltwbase.synthetic(60)`; it means `xltwlb.synthetic(60)`, the same 60-customer
synthetic instance. No route-minimiser run took place, so no result was seen before this fix.

## What nbrm-v2 changes

- `nbrun.py`: the smoke instance now comes from `xltwlb.synthetic(60)`. Nothing else in the runs, limits, seed,
  checks or scoring changes.
- `test_nbrun.py`: the two failing tests use the same function. A new end-to-end test runs the built binary on the
  smoke instance exactly as the study will (3 s, seed 1) and requires a written solution that passes the exact
  check, so a format mismatch stops the job before the long runs instead of after them. Tests for the setup's
  pre-registration and addendum checks were added.
- `getnb.py`: instead of comparing the public `expectations.md` with a local copy, it checks the public file's
  sha256 against the value nbrm-v1 recorded, and it waits for this addendum to be public on `main`.

Predictions N0-N5 are unchanged. If the end-to-end test fails, N0 is scored "did not hold" from the job's own logs.
