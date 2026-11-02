# xltwctl merged: v1 (interrupted) pairs + v2 pairs, scored once

Predictions: `{"K0": "held", "K1": "held", "K2": "held", "K3": "did not hold", "K4": "did not hold", "K5": "held"}`

E median reduction (bound vs split): 3.44% (cross-run figure in xltwbase/: 6.406%); E median speed ratio split/bound: 0.859

| instance | group | job | vehicles split | vehicles bound | distance split | distance bound | reduction % | it/s split | it/s bound | speed ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| R1_10_4 | E | v1 | 91 | 91 | 46542.62 | 44492.51 | 4.405 | 106.3 | 151.5 | 0.702 |
| R1_10_6 | E | v1 | 91 | 91 | 59175.64 | 55711.88 | 5.853 | 67.1 | 78.4 | 0.856 |
| R1_10_8 | E | v1 | 91 | 91 | 46032.37 | 44418.8 | 3.505 | 119.5 | 142.6 | 0.838 |
| RC1_10_3 | E | v1 | 90 | 90 | 45685.48 | 44143.77 | 3.375 | 85.3 | 91.3 | 0.934 |
| RC1_10_10 | E | v1 | 90 | 90 | 49147.01 | 47134.95 | 4.094 | 53.1 | 60.2 | 0.882 |
| R2_10_4 | E | v1 | 19 | 19 | 18299.05 | 18299.05 | 0.0 | 299.9 | 348.9 | 0.86 |
| RC2_10_9 | E | v1 | 18 | 18 | 23932.43 | 23832.66 | 0.417 | 309.3 | 331.9 | 0.932 |
| C1_10_4 | E | v2 | 90 | 90 | 39590.96 | 39585.73 | 0.013 | 393.2 | 457.8 | 0.859 |
| R1_10_1 | T | v2 | 100 | 100 | 55077.8 | 54334.58 | 1.349 | 257.3 | 334.1 | 0.77 |
