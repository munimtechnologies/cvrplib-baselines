# xltwrun: solver.py on XLTW-Test under the challenge's protocol, limits divided by 30

One run per instance, seed 20261104, one CPU per run, nearest-integer rounding; every counted solution re-checked exactly. K = the fleet lower bound from xltwtest/ (not a known optimum).

Predictions: `{"G0": "untestable", "G1": "untestable", "G2": "untestable", "G3": "untestable", "G4": "untestable", "G5": "untestable"}`

Vehicles 2194 against K 1263 in total; at K on 0 runs (0 of 2 with KC = 1, 0 of 6 others); median (vehicles - K) / K 0.7487.

| instance | n | limit s | KC | K | vehicles | distance | last at s | solutions printed | fleet s | bound cut | iterations | SIGTERM | peak GB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| XLTW-Test-n6588 | 6587 | 395.2 | 87 | 87 | 172 | 156235 | 359.78 | 16 | 194.6 | False | 18321 | False | 2.165 |
| XLTW-Test-n6734 | 6733 | 404.0 | 163 | 163 | 222 | 355928 | 61.91 | 3 | 962.8 | False | 0 | True | 2.139 |
| XLTW-Test-n6884 | 6883 | 413.0 | 1 | 16 | 296 | 391766 | 131.61 | 9 | None | None | None | True | 2.239 |
| XLTW-Test-n7037 | 7036 | 422.2 | 587 | 587 | 647 | 574297 | 420.08 | 7 | 351.6 | True | 1283 | False | 2.513 |
| XLTW-Test-n7193 | 7192 | 431.5 | 52 | 52 | 114 | 269014 | 378.09 | 37 | 216.4 | False | 10479 | True | 2.444 |
| XLTW-Test-n7353 | 7352 | 441.1 | 85 | 85 | 99 | 169545 | 389.88 | 20 | 220.0 | False | 21722 | False | 2.66 |
| XLTW-Test-n7516 | 7515 | 450.9 | 1 | 4 | 235 | 190662 | 448.85 | 21 | 225.5 | False | 22513 | False | 2.655 |
| XLTW-Test-n7683 | 7682 | 460.9 | 269 | 269 | 409 | 553215 | 458.73 | 12 | 206.1 | False | 20516 | False | 2.921 |
