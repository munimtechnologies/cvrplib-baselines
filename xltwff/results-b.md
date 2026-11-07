# xltwff: xltw-solver with a 0.8 fleet phase at the full limit T(n), four capacity-free XLTW-Test instances

Seed 20261104. Fleet fraction 0.8 (0.5 in xltw-solver 0.1.0). Network reachable during the runs: False. Build: cp312, Python 3.12.15; pins ok: True; solver.py patched: True.

Predictions (expectations.md): `null`

| run | instance | n | limit s | vehicles | K* | final count first printed at s | distance | fleet s | fleet solves | self-stopped | slack s | peak GB | frozen | valid |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H2 | XLTW-Test-n1421 | 1420 | 2556.0 | 65 | 47 | 1309.43 | 130271 | 2039.1 | 25 | True | 6.55 | 0.213 | False | True |
| H4 | XLTW-Test-n1841 | 1840 | 3312.0 | 25 | 18 | 228.85 | 84744 | 2642.4 | 28 | True | 8.034 | 0.271 | False | True |
