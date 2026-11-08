# xltwrun: solver.py on XLTW-Test under the challenge's protocol, limits divided by 30

One run per instance, seed 20261104, one CPU per run, nearest-integer rounding; every counted solution re-checked exactly. K = the fleet lower bound from xltwtest/ (not a known optimum).

Predictions: `{"G0": "untestable", "G1": "untestable", "G2": "untestable", "G3": "untestable", "G4": "untestable", "G5": "untestable"}`

Vehicles 534 against K 162 in total; at K on 0 runs (0 of 0 with KC = 1, 0 of 1 others); median (vehicles - K) / K 2.2963.

| instance | n | limit s | KC | K | vehicles | distance | last at s | solutions printed | fleet s | bound cut | iterations | SIGTERM | peak GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| XLTW-Test-n8389 | 8388 | 503.3 | 162 | 162 | 534 | 948605 | 31.05 | 1 | None | None | None | True | 3.276 |
