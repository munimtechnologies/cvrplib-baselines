# xltwrun: solver.py on XLTW-Test under the challenge's protocol, limits divided by 30

One run per instance, seed 20261104, one CPU per run, nearest-integer rounding; every counted solution re-checked exactly. K = the fleet lower bound from xltwtest/ (not a known optimum).

Predictions: `{"G0": "untestable", "G1": "untestable", "G2": "untestable", "G3": "untestable", "G4": "untestable", "G5": "untestable"}`

Vehicles 1104 against K 1054 in total; at K on 0 runs (0 of 0 with KC = 1, 0 of 2 others); median (vehicles - K) / K 0.0325.

| instance | n | limit s | KC | K | vehicles | distance | last at s | solutions printed | fleet s | bound cut | iterations | SIGTERM | peak GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| XLTW-Test-n8028 | 8027 | 481.6 | 803 | 803 | 852 | 829022 | 479.47 | 15 | 250.4 | False | 7602 | False | 3.017 |
| XLTW-Test-n8207 | 8206 | 492.4 | 251 | 251 | 252 | 262920 | 432.41 | 17 | 245.3 | False | 31490 | False | 3.281 |
