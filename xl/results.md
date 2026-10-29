# Plain PyVRP on XL locations with synthetic time windows

CVRPLib id 379, seed 20261029, one CPU, DIMACS tenths. Windows are synthetic, not XLTW.

| n | s | build s | build peak MB | peak MB | iterations/s | feasible | routes | route LB | cost (tenths) | check |
|---|---|---|---|---|---|---|---|---|---|---|
| 1000 | 300 | 0.0 | 68.9 | 104.9 | 336.74 | True | 161 | 159 | 2427233 | True |
| 2500 | 600 | 0.2 | 189.5 | 252.5 | 185.13 | True | 402 | 395 | 6092307 | True |
| 5000 | 900 | 1.2 | 620.8 | 637.5 | 99.55 | True | 799 | 785 | 12064928 | True |
| 10000 | 1800 | 4.8 | 2361.1 | 2361.1 | 44.12 | True | 1600 | 1570 | 24036358 | True |
