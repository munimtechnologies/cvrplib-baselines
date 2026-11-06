# xltwpkg: conformance of the packaged solver (xltwpkg-py312-v2)

Network reachable during the run steps: False. Built offline for cp312 with Python 3.12.15 (/usr/local/bin/python3); pins ok: True.

Predictions (expectations.md): `{"C0": "held", "C1": "held", "C2": "held", "C3": "held", "C4": "held", "C5a": "held", "C5b": "did not hold", "C6": "held"}`

| run | instance | n | limit s | seed | vehicles | distance | feasible | cost line ok | bad stdout lines | self-stopped | last Cost at s | slack s | peak GB | watchdog |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | XLTW-Test-n1048 | 1047 | 60.00 | 1 | 9 | 49647 | True | True | 0 | True | 58.479 | 1.521 | 0.127 |  |
| R2 | XLTW-Test-n1094 | 1093 | 60.00 | 1 | 94 | 79895 | True | True | 0 | True | 54.882 | 5.118 | 0.151 |  |
| R3 | XLTW-Test-n1141 | 1140 | 60.00 | 1 | 49 | 57104 | True | True | 0 | True | 58.121 | 1.879 | 0.152 |  |
| R4 | XLTW-Test-n1094 | 1093 | 60.00 | 7 | 94 | 79908 | True | True | 0 | True | 58.45 | 1.55 | 0.15 |  |
| R5 | XLTW-Test-n1094 | 1093 | 60.00 | 7 | 94 | 79908 | True | True | 0 | True | 58.458 | 1.542 | 0.142 |  |
| R6 | XLTW-Test-n1234 | 1233 | 120.00 | 3 | 35 | 86522 | True | True | 0 | True | 117.436 | 2.564 | 0.163 |  |
