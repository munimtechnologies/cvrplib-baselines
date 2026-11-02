# xltwctl: 300 s + 300 s split against the bound-aware budget, same machine, same job

PyVRP 0.14.1, one CPU per run, seed 20261030, 600 s per run, 2 runs at a time.

Predictions: `{"K0": "did not hold", "K1": "untestable", "K2": "untestable", "K3": "untestable", "K4": "did not hold", "K5": "held"}`

E median reduction (bound vs split): 0.013% (cross-run figure in xltwbase/: 6.406%); E median speed ratio split/bound: 0.859

| instance | group | vehicles split | vehicles bound | distance split | distance bound | reduction % | fleet s split | fleet s bound | solve s split | solve s bound | it/s split | it/s bound |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1_10_4 | E | 90 | 90 | 39590.96 | 39585.73 | 0.013 | 6.0 | 6.0 | 300.0 | 594.0 | 393.2 | 457.8 |
| R1_10_1 | T | 100 | 100 | 55077.8 | 54334.58 | 1.349 | 300.7 | 57.5 | 300.0 | 542.5 | 257.3 | 334.1 |
