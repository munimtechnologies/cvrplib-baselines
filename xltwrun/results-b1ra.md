# xltwrun: solver.py on XLTW-Test under the challenge's protocol, limits divided by 30

One run per instance, seed 20261104, one CPU per run, nearest-integer rounding; every counted solution re-checked exactly. K = the fleet lower bound from xltwtest/ (not a known optimum).

Predictions: `{"G0": "untestable", "G1": "untestable", "G2": "untestable", "G3": "untestable", "G4": "untestable", "G5": "untestable"}`

Vehicles 459 against K 179 in total; at K on 0 runs (0 of 1 with KC = 1, 0 of 1 others); median (vehicles - K) / K 7.8482.

| instance | n | limit s | KC | K | vehicles | distance | last at s | solutions printed | fleet s | bound cut | iterations | SIGTERM | peak GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| XLTW-Test-n6734 | 6733 | 404.0 | 163 | 163 | 195 | 321448 | 401.98 | 15 | 195.5 | False | 30256 | False | 2.255 |
| XLTW-Test-n6884 | 6883 | 413.0 | 1 | 16 | 264 | 344762 | 411.42 | 30 | 214.0 | False | 24929 | False | 2.24 |
