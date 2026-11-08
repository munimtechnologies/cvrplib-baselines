# xltwff: xltw-solver with a 0.8 fleet phase at the full limit T(n), four capacity-free XLTW-Test instances

Seed 20261104. Fleet fraction 0.8 (0.5 in xltw-solver 0.1.0). Network reachable during the runs: False. Build: cp312, Python 3.12.15; pins ok: True; solver.py patched: True.

Predictions (expectations.md): `{"H0": "did not hold", "H1": "untestable (H0 failed)", "H2": "untestable (H0 failed)", "H3": "untestable (H0 failed)", "H4": "untestable (H0 failed)", "H5": "untestable (H0 failed)"}`

| run | instance | n | limit s | vehicles | K* | final count first printed at s | distance | fleet s | fleet solves | self-stopped | slack s | peak GB | frozen | valid |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | XLTW-Test-n1234 | 1233 | 2219.4 | 33 | 27 | 1203.16 | 84722 | 1770.5 | 22 | True | 5.885 | 0.164 | False | True |
| H2 | XLTW-Test-n1421 | 1420 | 2556.0 | 65 | 47 | 1309.43 | 130271 | 2039.1 | 25 | True | 6.55 | 0.213 | False | True |
| H3 | XLTW-Test-n1608 | 1607 | 2892.6 | 108 | 81 | 1192.98 | 112903 | 2307.8 | 15 | True | 7.204 | 0.239 | False | True |
| H4 | XLTW-Test-n1841 | 1840 | 3312.0 | 25 | 18 | 228.85 | 84744 | 2642.4 | 28 | True | 8.034 | 0.271 | False | True |

Against xltwfull (same instances, seed and harness; fleet fraction 0.5):

| run | instance | K* | vehicles 0.8 | vehicles 0.5 | distance 0.8 | distance 0.5 | fleet s 0.8 | fleet s 0.5 | final count first at 0.8 | at 0.5 |
|---|---|---|---|---|---|---|---|---|---|---|
| H1 | XLTW-Test-n1234 | 27 | 33 | 34 | 84722 | 83690 | 1770.5 | 1106.4 | 1203.16 | 86.36 |
| H2 | XLTW-Test-n1421 | 47 | 65 | 65 | 130271 | 130249 | 2039.1 | None | 1309.43 | 1041.85 |
| H3 | XLTW-Test-n1608 | 81 | 108 | 108 | 112903 | 112655 | 2307.8 | 1442.3 | 1192.98 | 1123.98 |
| H4 | XLTW-Test-n1841 | 18 | 25 | 25 | 84744 | 84464 | 2642.4 | 1651.5 | 228.85 | 191.67 |
