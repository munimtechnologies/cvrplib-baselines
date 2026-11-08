# xltwrun: solver.py on XLTW-Test under the challenge's protocol, limits divided by 30

One run per instance, seed 20261104, one CPU per run, nearest-integer rounding; every counted solution re-checked exactly. K = the fleet lower bound from xltwtest/ (not a known optimum).

Predictions: `{"G0": "untestable", "G1": "untestable", "G2": "untestable", "G3": "untestable", "G4": "untestable", "G5": "untestable"}`

Vehicles 267 against K 260 in total; at K on 0 runs (0 of 0 with KC = 1, 0 of 1 others); median (vehicles - K) / K 0.0269.

| instance | n | limit s | KC | K | vehicles | distance | last at s | solutions printed | fleet s | bound cut | iterations | SIGTERM | peak GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| XLTW-Test-n10001 | 10000 | 600.0 | 260 | 260 | 267 | 465017 | 597.67 | 16 | 309.3 | False | 27420 | False | 4.623 |
