# xltwfc: fixed-cost fleet phase at the full limit T(n) on the four xltwfull/ instances

Seed 20261104. Network reachable during the runs: False. Build: cp312, Python 3.12.15; pins ok: True.

Predictions (expectations.md): `{"S0": "held", "S1": "did not hold", "S2": "did not hold", "S3": "held", "S4": "held", "S5": "held"}`

| run | instance | n | limit s | vehicles | xltwfull vehicles | part a (T/30) | K* | first feasible | F | final count first printed at s | distance | xltwfull distance | slack s | peak GB | attempts | valid |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 | XLTW-Test-n1234 | 1233 | 2219.4 | 34 | 34 | 35 | 27 | 63 | 19250 | 531.78 | 82856 | 83690 | 5.891 | 0.165 | 1 | True |
| F2 | XLTW-Test-n1421 | 1420 | 2556.0 | 67 | 65 | 72 | 47 | 114 | 17670 | 1970.68 | 131617 | 130249 | 6.562 | 0.186 | 1 | True |
| F3 | XLTW-Test-n1608 | 1607 | 2892.6 | 110 | 108 | 113 | 81 | 124 | 10200 | 1162.12 | 112789 | 112655 | 7.197 | 0.217 | 1 | True |
| F4 | XLTW-Test-n1841 | 1840 | 3312.0 | 26 | 25 | 29 | 18 | 78 | 19480 | 620.23 | 82826 | 84464 | 8.043 | 0.278 | 1 | True |
