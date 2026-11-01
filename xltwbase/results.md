# xltwbase: vehicles first, fleet search stopped at a proven bound, leftover time to distance

PyVRP 0.14.1, one CPU per run, seed 20261030. Every result re-checked exactly in its own convention.

Predictions: `{"Q0": "held", "Q1": "held", "Q2": "held", "Q3": "held", "Q4": "held", "Q5": "held"}`

| instance | group | conv | KC | K | vehicles | exact ok | distance | fleet s | solves | at bound | solve s | iterations | vrptwl vehicles | vrptwl distance | change % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1_10_4 | E | double | 91 | 91 | 91 | True | 43062.5 | 2.2 | 4 | True | 597.8 | 281807 | 91 | 47113.26 | -8.598 |
| R1_10_6 | E | double | 91 | 91 | 91 | True | 51061.4 | 4.0 | 8 | True | 596.0 | 132638 | 91 | 59175.64 | -13.712 |
| R1_10_8 | E | double | 91 | 91 | 91 | True | 42818.75 | 2.2 | 4 | True | 597.8 | 298578 | 91 | 46241.94 | -7.403 |
| RC1_10_3 | E | double | 90 | 90 | 90 | True | 42741.2 | 3.8 | 5 | True | 596.2 | 210614 | 90 | 45185.2 | -5.409 |
| RC1_10_10 | E | double | 90 | 90 | 90 | True | 44942.45 | 2.8 | 5 | True | 597.2 | 120569 | 90 | 48753.8 | -7.818 |
| R2_10_4 | E | double | 19 | 19 | 19 | True | 18296.54 | 4.8 | 9 | True | 595.2 | 489892 | 19 | 18299.05 | -0.014 |
| RC2_10_9 | E | double | 18 | 18 | 18 | True | 23640.44 | 7.4 | 13 | True | 592.6 | 476898 | 18 | 23889.87 | -1.044 |
| C1_10_4 | E | double | 90 | 90 | 90 | True | 39585.73 | 6.6 | 9 | True | 593.4 | 296791 | 90 | 39674.89 | -0.225 |
| R1_10_1 | T | double | 91 | 100 | 100 | True | 54334.58 | 44.6 | 7 | True | 555.4 | 182748 | 100 | 56499.94 | -3.832 |
| C1_10_1 | F | double | 90 | 99 | 100 | True | 42482.61 | 300.6 | 7 | False | 299.4 | 146555 | 100 | 42481.34 | 0.003 |
| C1_10_7 | F | double | 90 | 90 | 99 | True | 42718.88 | 300.7 | 8 | False | 299.3 | 100623 | 99 | 42718.88 | 0.0 |
| C2_10_6 | F | double | 28 | 28 | 29 | True | 17322.69 | 301.1 | 17 | False | 298.9 | 138573 | 30 | 16348.45 | 5.959 |
| RC2_10_1 | F | double | 18 | 18 | 21 | True | 29704.82 | 300.9 | 25 | False | 299.1 | 251916 | 21 | 29744.99 | -0.135 |
| R1_10_1 | conv | dimacs | 91 | 91 | 95 | True | 58140.8 | 60.6 | 11 | False | 59.4 | 13946 |  |  |  |
| R1_10_1 | conv | round | 91 | 91 | 93 | True | 60602.0 | 60.7 | 11 | False | 59.3 | 12267 |  |  |  |
| RC2_10_9 | conv | dimacs | 18 | 18 | 18 | True | 23768.7 | 6.9 | 16 | True | 113.1 | 85037 |  |  |  |
| RC2_10_9 | conv | round | 18 | 18 | 18 | True | 23986.0 | 6.1 | 15 | True | 113.9 | 88299 |  |  |  |
