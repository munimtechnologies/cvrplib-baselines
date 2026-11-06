# xltw-solver (draft package)

An offline, protocol-exact package of MV2's vehicles-first PyVRP baseline for CVRPLib's VRPTW Challenge
(algorithm track). MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name.
Code Apache-2.0; PyVRP 0.14.1 (MIT), numpy (BSD-3-Clause), vrplib (MIT) and tqdm (MPL-2.0 and MIT) keep their own
licences.

Status: draft, package 0.1.1 (solver 0.1.0). Its conformance test is pre-registered in `expectations.md`. The first
jobs scored nothing: the build picked a different Python from the tests in the python:3.12 image, and a DNS failure
stopped the 3.11 job. What happened and what was fixed is in `addendum-2026-11-06.md`; `score-v1.md` records the
v1 jobs. Results of the v2 jobs will appear next to them.

## Build and run

```
bash build.sh            # or: make     (add --offline / `make offline` to forbid any download)
./solver INSTANCE SECONDS SEED
```

Needs Linux x86-64 (glibc 2.28 or newer), bash and CPython 3.11, 3.12 or 3.13. No pip, no venv, no root.
`build.sh` uses `XLTW_PYTHON` if set, else the default `python3`, and records the interpreter it used in
`lib/XLTW_BUILD.json`; `./solver` always runs that one.
`lock.py` unpacks pinned wheels, each checked against the sha256 PyPI publishes for it, into `lib/`.
With every wheel in `vendor/wheels/` (`python3 lock.py --resolve --fetch` fills it once, with Internet access),
the build and the solver need no network at all.

## What the solver does

Nearest-integer Euclidean arcs (the challenge's convention); a fleet lower bound from `xltwlb.py`; PyVRP's
fleet-reduction loop down to that bound in the first half of the time; distance search with that fleet in the rest.
Better solutions (fewer vehicles first, then shorter) are printed in CVRPLib format; stdout carries nothing else
(library logging is moved to stderr). It stops by itself shortly before the limit, and at once on SIGTERM; a
watchdog thread ends it on time even when PyVRP is stuck inside one long C++ call.
Single-threaded. Runs are seeded but stop on the wall clock, so a seed does not pin the result.

Source of the method and earlier results: https://github.com/munimtechnologies/cvrplib-baselines
