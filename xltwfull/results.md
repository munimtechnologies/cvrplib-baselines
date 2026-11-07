# xltwfull: xltw-solver at the full limit T(n) on four capacity-free XLTW-Test instances

Seed 20261104. Network reachable during the runs: False. Build: cp312, Python 3.12.15; pins ok: True.

Predictions (expectations.md): `{"F0": "did not hold", "F1": "untestable (F0 failed)", "F2": "untestable (F0 failed)", "F3": "untestable (F0 failed)", "F4": "untestable (F0 failed)", "F5": "untestable (F0 failed)"}`

| run | instance | n | limit s | vehicles | part a (T/30) | K | K* | final count first printed at s | distance | part a distance | fleet solves | self-stopped | slack s | peak GB | frozen | valid |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 | XLTW-Test-n1234 | 1233 | 2219.4 | 34 | 35 | 7 | 27 | 86.36 | 83690 | 89250 | 21 | True | 5.874 | 0.164 | False | True |
| F2 | XLTW-Test-n1421 | 1420 | 2556.0 | 65 | 72 | 16 | 47 | 1041.85 | 130249 | 139809 | None | False | 438.288 | 0.212 | True | False |
| F3 | XLTW-Test-n1608 | 1607 | 2892.6 | 108 | 113 | 7 | 81 | 1123.98 | 112655 | 118365 | 15 | True | 56.981 | 0.24 | False | True |
| F4 | XLTW-Test-n1841 | 1840 | 3312.0 | 25 | 29 | 4 | 18 | 191.67 | 84464 | 85369 | 28 | True | 8.03 | 0.273 | False | True |
