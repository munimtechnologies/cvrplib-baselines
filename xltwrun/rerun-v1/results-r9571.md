# xltwrun: solver.py on XLTW-Test under the challenge's protocol, limits divided by 30

One run per instance, seed 20261104, one CPU per run, nearest-integer rounding; every counted solution re-checked exactly. K = the fleet lower bound from xltwtest/ (not a known optimum).

Predictions: `{"G0": "untestable", "G1": "untestable", "G2": "untestable", "G3": "untestable", "G4": "untestable", "G5": "untestable"}`

Vehicles 309 against K 181 in total; at K on 0 runs (0 of 0 with KC = 1, 0 of 1 others); median (vehicles - K) / K 0.7072.

| instance | n | limit s | KC | K | vehicles | distance | last at s | solutions printed | fleet s | bound cut | iterations | SIGTERM | peak GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| XLTW-Test-n9571 | 9570 | 574.2 | 181 | 181 | 309 | 424767 | 556.22 | 24 | 300.4 | False | 21577 | False | 4.242 |
