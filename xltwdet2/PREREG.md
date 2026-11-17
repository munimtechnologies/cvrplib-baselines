# xltwdet2: pre-registration (written 2026-11-17, before any run)

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Code Apache-2.0, text CC BY 4.0.

## Question

The rules of CVRPLib's VRPTW Challenge (algorithm track, submissions 2026-12-16 to 2027-01-16) say "Each execution
must be deterministic for a given seed", and the organisers run every algorithm 20 times per instance at the full limit
T(n) = 1,800 s per 1,000 customers. `xltwdet/` (scored 2026-11-08) showed that stopping on an iteration budget makes
the same seed end at the identical solution, but its single budget for both phases was too tight for the slow fleet
phase of n1234 (one run under a CPU hog fell back to the wall clock), and it was only tested at 120 s.

[xltw-solver 0.2.0](https://github.com/munimtechnologies/xltw-solver) makes the work budget the default, with
**separate budgets for the two phases**, fixed in advance from n and T only:

    usable = T - margin(T);  g(n) = (n / 1000) ** -0.5
    fleet budget    = floor(90 x g(n) x 0.8 x usable)
    distance budget = floor(200 x g(n) x 0.2 x usable) + floor(unused fleet iterations x 200 / 90)

90 and 200 it/s at n = 1,000 are about 0.65-0.70 of the slowest per-phase rates `xltwdet/` measured (fleet 129,
distance 278 it/s after scaling by g(n), n1234 under the hog). The fleet share rises from 0.5 to 0.8 because
`xltwff/` found that it saves a vehicle at almost no distance cost. The wall clock remains only as a safety net and
is flagged when it acts.

**Does 0.2.0 give the identical solution for the same seed at the full limit, with two copies running side by side,
without ever falling back to the clock, and without wasting most of the limit?**

## Method (det2run.py)

- Build exactly as `xltwdet/` did: packaging files from cvrplib-baselines commit 19c7eb6 (`xltwpkg/`), pinned wheels
  (`lock.py --resolve --fetch`), `bash build.sh --offline`; the solver is xltw-solver 0.2.0's `solver.py`, which
  `getdet2.py` checks is byte-identical to the published file on xltw-solver `main` before anything runs. Network
  is unreachable during the runs (`poc` job). Tests first: `test_pkg` (the package's), `test_budget` (0.2.0's),
  `test_det2run` (this scorer).
- Smoke runs on XLTW-Test-n1234: S1 work mode, 60 s; S2 clock mode (`XLTW_MODE=clock`), 30 s. If S1 is not a valid
  run, the study runs are skipped and G0 fails.
- Study: XLTW-Test-n1234 (1,233 customers, T = 2,219.4 s) and XLTW-Test-n2028 (2,027 customers, T = 3,648.6 s),
  seed 20261104 (the seed of `xltwfull/`). On each instance, runs X1 and X2 start together and run side by side on
  the job's two CPUs, each through `xltwfull/`'s harness (commit 876bd94, `run_one`, unchanged): SIGTERM at the limit,
  SIGKILL 5 s later, the last complete solution before the limit counts and is re-checked exactly (nearest-integer
  arcs). If either run of a pair is frozen (harness poll gap above 1 s), the pair is re-run once and the re-run counts.
- Resources: 2 CPUs, 2 GB, data volume `xltw-test`.

## Predictions (our honest probabilities)

| id | prediction | p |
|---|---|---|
| G0 | gate: offline build with pinned wheels, network unreachable, all four study runs valid (stopped by themselves with exit 0, not frozen, counted solution feasible in exact arithmetic, `Cost` line equal to its distance, clean stdout) and each reports solver `xltw-solver 0.2.0` | 0.80 |
| G1 | on both instances, X1 and X2 end at the identical solution (equal SHA-256 of the counted solution) | 0.85 |
| G2 | none of the four runs stops on the wall clock or SIGTERM, and each stats line says `deterministic: true` | 0.80 |
| G3 | every run ends between 35% and 85% of its limit (solver's own `elapsed`) | 0.70 |
| G4 | on n1234 both runs use at most 34 vehicles (0.1.0 at the full T(n), same seed: 34 in `xltwfull/` F1; 33 with 0.8 of the limit for the fleet in `xltwff/`) | 0.75 |
| G5 | on n2028 both runs use fewer than 103 vehicles (0.1.0 at T(n)/30, `xltwen/` vehicles_a) | 0.90 |
| G6 | every run peaks at most 0.6 GB and the watchdog never fires | 0.90 |
| G7 | headroom: in every run, the measured fleet and distance rates (iterations / phase seconds) are at least 1.2 times the model's (90 x g(n) and 200 x g(n)) | 0.65 |

G1-G7 are scored only if G0 holds, from `results.json` `predictions` (computed by `det2run.score`, checked by hand),
with a Brier score.

## What follows

- G0-G2 hold: 0.2.0 is the algorithm-track entry's stopping rule; its README says determinism was tested at the full
  limit on two instances, with two runs side by side. Identical results on the organisers' CPUs are expected (same
  binary wheels, same iteration counts) but not tested.
- G2 or G7 fails: the rates are lowered from the measured per-phase minima (and from the share of the limit used) in
  0.2.1, pre-registered again.
- G1 fails while G2 holds: something other than the stopping rule is not deterministic (for example the bound's time
  cap); found from the logs before any change.
- G4 and G5 are about vehicles, not determinism; they say what the budget costs against the wall-clock solver.
