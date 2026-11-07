# xltwff: xltw-solver with a 0.8 fleet phase at the full limit T(n), four capacity-free XLTW-Test instances

Seed 20261104. Fleet fraction 0.8 (0.5 in xltw-solver 0.1.0). Network reachable during the runs: False. Build: cp312, Python 3.12.15; pins ok: True; solver.py patched: True.

Predictions (expectations.md): `null`

| run | instance | n | limit s | vehicles | K* | final count first printed at s | distance | fleet s | fleet solves | self-stopped | slack s | peak GB | frozen | valid |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | XLTW-Test-n1234 | 1233 | 2219.4 | 33 | 27 | 1203.16 | 84722 | 1770.5 | 22 | True | 5.885 | 0.164 | False | True |
| H3 | XLTW-Test-n1608 | 1607 | 2892.6 | 108 | 81 | 1192.98 | 112903 | 2307.8 | 15 | True | 7.204 | 0.239 | False | True |
