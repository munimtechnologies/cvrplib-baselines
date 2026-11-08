# xltwrun: solver.py on XLTW-Test under the challenge's protocol, limits divided by 30

One run per instance, seed 20261104, one CPU per run, nearest-integer rounding; every counted solution re-checked exactly. K = the fleet lower bound from xltwtest/ (not a known optimum).

Predictions: `{"G0": "untestable", "G1": "untestable", "G2": "untestable", "G3": "untestable", "G4": "untestable", "G5": "untestable"}`

Vehicles 105 against K 11 in total; at K on 0 runs (0 of 1 with KC = 1, 0 of 0 others); median (vehicles - K) / K 8.5455.

| instance | n | limit s | KC | K | vehicles | distance | last at s | solutions printed | fleet s | bound cut | iterations | SIGTERM | peak GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| XLTW-Test-n8575 | 8574 | 514.4 | 1 | 11 | 105 | 170734 | 512.21 | 21 | 277.4 | False | 22274 | False | 3.426 |
