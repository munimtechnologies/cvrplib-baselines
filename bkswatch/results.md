# CVRPLib VRPTW BKSs re-read and re-checked (DIMACS and double precision)

Predictions: `{"W0": "did not hold", "W1": "held", "W2": "held", "W3": "held", "W4": "did not hold", "W5": "untestable"}`

Tally: `{"rows": 356, "errors": [], "dimacs_fail": ["R1_10_6"], "double_late": 92, "below_K_double": ["R1_6_1", "R1_10_1"], "no_reference": [], "changed": ["C1_10_9", "R1_10_1", "R1_10_5", "R1_10_6", "R1_10_9"], "changed_double_late": ["R1_10_1", "R1_10_6", "R1_10_9"], "changed_route_count": ["C1_10_9", "R1_10_1", "R1_10_6", "R1_10_9"]}`

## BKSs that differ from the 2026-10-30 reference

| id | instance | routes (was) | DIMACS cost (was) | double ok (was) | late (routes) | max late | double distance | K double |
|---|---|---|---|---|---|---|---|---|
| 684 | C1_10_9 | 91 (90) | 40278.7 (40282.2) | True (True) | 0 (0) | 0.0 | 40314.66 | 90 |
| 696 | R1_10_1 | 94 (95) | 52982.0 (53026.1) | False (False) | 8 (8) | 0.1056 | 53028.11 | 100 |
| 700 | R1_10_5 | 92 (92) | 50365.5 (50388.5) | True (True) | 0 (0) | 0.0 | 50410.19 | 91 |
| 701 | R1_10_6 | 92 (91) | 468603.0 (46883.6) | False (True) | 1 (1) | 0.0549 | 46904.5 | 91 |
| 704 | R1_10_9 | 92 (91) | 49088.1 (49140.6) | False (True) | 1 (1) | 0.1691 | 49133.92 | 91 |
