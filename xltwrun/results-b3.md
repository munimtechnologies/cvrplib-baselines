# xltwrun: solver.py on XLTW-Test under the challenge's protocol, limits divided by 30

One run per instance, seed 20261104, one CPU per run, nearest-integer rounding; every counted solution re-checked exactly. K = the fleet lower bound from xltwtest/ (not a known optimum).

Predictions: `{"G0": "untestable", "G1": "untestable", "G2": "untestable", "G3": "untestable", "G4": "untestable", "G5": "untestable"}`

Vehicles 2305 against K 951 in total; at K on 0 runs (0 of 2 with KC = 1, 0 of 4 others); median (vehicles - K) / K 0.9289.

| instance | n | limit s | KC | K | vehicles | distance | last at s | solutions printed | fleet s | bound cut | iterations | SIGTERM | peak GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| XLTW-Test-n8960 | 8959 | 537.5 | 1 | 5 | 265 | 370881 | 535.29 | 23 | 288.3 | False | 13364 | False | 3.73 |
| XLTW-Test-n9160 | 9159 | 549.5 | 244 | 244 | 401 | 381900 | 382.44 | 7 | 322.0 | False | 4788 | True | 3.89 |
| XLTW-Test-n9363 | 9362 | 561.7 | 209 | 253 | 484 | 513639 | 559.65 | 8 | 437.3 | True | 1777 | False | 4.234 |
| XLTW-Test-n9571 | 9570 | 574.2 | 181 | 181 | 352 | 493050 | 153.7 | 5 | None | None | None | True | 4.237 |
| XLTW-Test-n9784 | 9783 | 587.0 | 1 | 8 | 522 | 858289 | 582.46 | 16 | 318.5 | False | 12885 | False | 4.623 |
| XLTW-Test-n10001 | 10000 | 600.0 | 260 | 260 | 281 | 505302 | 592.95 | 6 | None | None | None | True | 4.622 |
