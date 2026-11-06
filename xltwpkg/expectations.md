# xltwpkg: an offline, protocol-exact package of the XLTW baseline solver (pre-registered 2026-11-06)

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.

## Why

CVRPLib's VRPTW Challenge (algorithm track; registration and submissions open 2026-12-16, deadline 2027-01-16)
asks for a solver that builds with only `make` or a `build.sh` at the repository root, runs on Linux x86-64
**without Internet access or root**, is called as `./solver INSTANCE SECONDS SEED`, prints nothing on stdout but
`Route #k: ...` / `Cost: ...` blocks, and is single-threaded. MV2's baseline (`xltwrun/solver.py`, PyVRP 0.14.1)
so far ran only inside a container where pip had installed PyVRP from the network.

Two things stood in the way of an offline build, both found while preparing this package:

1. PyVRP 0.14.1 needs CPython 3.11 or newer (`requires_python >=3.11`), and it depends on matplotlib, numpy, tqdm
   and vrplib. matplotlib is used only for plotting.
2. `import pyvrp` attaches a logging handler that writes to **stdout** (`pyvrp/__init__.py`). With
   `display=False`, as the baseline calls it, PyVRP's `solve` logs nothing, so this has not caused a stray line so
   far (part a: none in 80 runs); it is a latent hazard, closed here anyway.

A third problem showed up in the baseline's own XLTW-Test run on 2026-11-06 (part b2, limits T(n)/30): on
**XLTW-Test-n8575** the harness sent SIGTERM on time (0.19 s after the 514.4 s limit), but the solver had not
stopped by itself and did not react within 5 s, so it was SIGKILLed. Its stderr ends after the bound line, and its
last solution came at 64.5 s: one PyVRP call ran for more than 450 s without returning to Python, where both the
solver's own stopping check and its SIGTERM handler live. The counted solution (printed at 64.5 s) still counts,
but the run breaks the protocol's "stop when told" expectation and wastes most of its time.

Separately, five other part-b runs (n6734, n6884, n7193 in b1; n8028, n8207 in b2) were frozen part-way by the
host: the whole container was paused (about 45 minutes in total), so the harness sent SIGTERM 388-930 s late and
SIGKILL 0.2 s after it. Those five are not valid runs of the protocol; they are being re-run unchanged (job
`xltwrun-b1r-v1`, parts b1ra, b1rb and b2r), and the originals stay published.

## What the package does (files in this folder)

- `lock.py` (standard library only) resolves pinned wheels on PyPI's JSON API (pyvrp 0.14.1, numpy 2.3.4, vrplib
  2.2.0, tqdm 4.67.1; one manylinux x86_64 wheel per CPython 3.11/3.12/3.13 where needed), records PyPI's sha256 for
  each in `wheels.lock`, downloads them into `vendor/wheels/`, and unpacks the ones for the running Python into
  `lib/` after checking every hash. No pip, no venv, and with `--offline` no network at all. matplotlib is left out.
- `build.sh` (and `make`) picks CPython 3.11-3.13, runs the unpacking, writes the `./solver` launcher (`exec`s
  Python with `-s -P`, no outside `PYTHON*` settings, one BLAS thread) and checks that pyvrp and numpy import from
  `lib/`.
- `solver.py` is `xltwrun/solver.py` (commit ba1eec8) with the same search, plus: it finds `lib/` itself, and before
  importing anything heavy it keeps a private copy of file descriptor 1 for solutions and points fd 1 and
  `sys.stdout` at stderr. Library logging, stray prints and C-level writes can then only reach stderr.
  And a **watchdog thread**: PyVRP's local search and perturbation release the GIL (`py::call_guard<
  py::gil_scoped_release>` in `pyvrp/cpp/search/bindings.cpp`, v0.14.1), so a Python thread still runs while
  the main thread is stuck in them. The watchdog wakes at a hard deadline (half the solver's stopping margin before
  the limit) or as soon as SIGTERM arrives (via `signal.set_wakeup_fd`, written by the C-level handler at once),
  prints any held better solution, flushes stdout and exits 0. `test_pkg.py` checks both paths with a main thread
  blocked in a GIL-releasing call.

## The test (job `xltwpkg-py312-v1`, image python:3.12; and `xltwpkg-py311-v1`, image python:3.11)

Setup (network on): fetch `xltwbase.py` and `xltwlb.py` at tag v0.3.7; wait until this file is public on `main` and
byte-identical to the job's copy (else stop); `lock.py --resolve --fetch`.
Run steps (**network off**): `bash build.sh --offline`; `python -m unittest -v test_pkg`; `python conformance.py`.

`conformance.py` launches `./solver` as the challenge does (SIGTERM at the limit, SIGKILL 5 s later, stdout read
line by line with arrival times) on six runs, one at a time:

| run | instance | limit s | seed |
|---|---|---|---|
| R1 | XLTW-Test-n1048 | 60 | 1 |
| R2 | XLTW-Test-n1094 | 60 | 1 |
| R3 | XLTW-Test-n1141 | 60 | 1 |
| R4 | XLTW-Test-n1094 | 60 | 7 |
| R5 | XLTW-Test-n1094 | 60 | 7 |
| R6 | XLTW-Test-n1234 | 120 | 3 |

The counted solution of a run is the last complete block whose `Cost` line arrived before the limit; it is
re-checked exactly (50-digit decimals, nearest-integer arcs, every arrival including the depot return).
Frozen-harness rule (fixed now): the harness polls every 0.05 s; if two polls are more than 1 s apart, the
container was paused and the run is re-run once, unchanged; the frozen try stays in results.json.

## Predictions (C0-C6 scored separately for each of the two jobs above)

- **C0 (gate):** pypi.org is unreachable during the run steps, `build.sh --offline` succeeds, and `lib/` holds
  exactly the four pinned versions, with pyvrp and numpy imported from `lib/`. If C0 fails, C1-C6 are not scored.
- **C1:** in all six runs every stdout line is a `Route #k:` line (numbered 1, 2, ... in each block) or a `Cost:`
  line: zero other lines.
- **C2:** all six runs have a counted solution that is feasible in the exact check, and its `Cost` line equals
  the recomputed distance.
- **C3:** all six runs end by themselves before the limit with exit code 0 (no SIGTERM, no SIGKILL).
- **C4:** in all six runs the counted `Cost` line arrives at least 0.5 s before the limit.
- **C5a:** R4 and R5 (same instance, seed and limit) end with the same number of vehicles.
- **C5b:** R4 and R5 end with **different** distances (the search stops on the wall clock, so a seed does not
  pin the result; this is what we expect, and it matters because the challenge asks for runs that are
  deterministic for their seed).
- **C6:** every run's peak resident memory is at most 0.6 GB.

A third job, `xltwpkg-n8575-v1` (python:3.12, 4 GB), builds the same way and runs only W1: XLTW-Test-n8575 with
the b2 run's seed (20261104) and limit (514.44 s = T(n)/30). Its C0 is the same gate.

- **C7:** W1 ends by itself before the limit with exit code 0 (watchdog or own stop; no SIGTERM, no SIGKILL),
  its counted solution is feasible in the exact check with a correct `Cost` line, and stdout has no other lines.
- **C8:** in W1 the watchdog fires at its hard deadline, i.e. the stuck call recurs with the same seed (the fleet
  loop's first minute does not depend on the clock, so we expect it to).

## Limits, said in advance

This checks packaging and protocol conformance on six small instances at short limits, not solution quality.
The six runs are not expected to trigger the watchdog; it is tested by the unit tests, and on the instance that
needed it (n8575) only by a later run. A run that the watchdog ends counts as self-stopped in C3. Two Docker images are not every Linux; the organisers' machine, Python and glibc are unknown.
A held C3/C4 at 60-120 s says nothing certain about 30-300 minute limits.

Prior art: PyVRP (Wouda, Lan & Kool, INFORMS J. Computing 2024; MIT) does the search. Unpacking wheels without pip
is standard (wheels are zip archives, PEP 427). Nothing here is a new method; what is new is a checked, offline
package of a public VRPTW baseline under this challenge's run protocol.
