# xltwrun: solver.py on XLTW-Test under the challenge's protocol, limits divided by 30

One run per instance, seed 20261104, one CPU per run, nearest-integer rounding; every counted solution re-checked exactly. K = the fleet lower bound from xltwtest/ (not a known optimum).

Predictions: `{"G0": "untestable", "G1": "untestable", "G2": "untestable", "G3": "untestable", "G4": "untestable", "G5": "untestable"}`

Vehicles 2228 against K 1663 in total; at K on 0 runs (0 of 2 with KC = 1, 0 of 4 others); median (vehicles - K) / K 0.8085.

| instance | n | limit s | KC | K | vehicles | distance | last at s | solutions printed | fleet s | bound cut | iterations | SIGTERM | peak GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| XLTW-Test-n7854 | 7853 | 471.2 | 1 | 4 | 62 | 129631 | 468.99 | 34 | 243.4 | False | 24774 | False | 2.897 |
| XLTW-Test-n8028 | 8027 | 481.6 | 803 | 803 | 902 | 824040 | 74.01 | 3 | None | None | None | True | 3.009 |
| XLTW-Test-n8207 | 8206 | 492.4 | 251 | 251 | 257 | 280808 | 45.07 | 2 | None | None | None | True | 3.141 |
| XLTW-Test-n8389 | 8388 | 503.3 | 162 | 162 | 404 | 731276 | 489.72 | 16 | 388.5 | False | 7600 | False | 3.281 |
| XLTW-Test-n8575 | 8574 | 514.4 | 1 | 11 | 156 | 207870 | 64.52 | 3 | None | None | None | True | 3.422 |
| XLTW-Test-n8766 | 8765 | 525.9 | 432 | 432 | 447 | 456857 | 371.75 | 7 | 245.3 | False | 20608 | False | 3.74 |
