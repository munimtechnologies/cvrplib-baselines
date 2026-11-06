# xltwpkg: conformance of the packaged solver (xltwpkg-py311-v2)

Network reachable during the run steps: False. Built offline for cp311 with Python 3.11.18 (/usr/local/bin/python3); pins ok: True.

Predictions (expectations.md): `{"C0": "held", "C1": "held", "C2": "held", "C3": "held", "C4": "held", "C5a": "held", "C5b": "held", "C6": "held"}`

| run | instance | n | limit s | seed | vehicles | distance | feasible | cost line ok | bad stdout lines | self-stopped | last Cost at s | slack s | peak GB | watchdog |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | XLTW-Test-n1048 | 1047 | 60.00 | 1 | 9 | 49906 | True | True | 0 | True | 58.207 | 1.793 | 0.126 |  |
| R2 | XLTW-Test-n1094 | 1093 | 60.00 | 1 | 94 | 80471 | True | True | 0 | True | 55.741 | 4.259 | 0.142 |  |
| R3 | XLTW-Test-n1141 | 1140 | 60.00 | 1 | 49 | 57154 | True | True | 0 | True | 56.69 | 3.31 | 0.142 |  |
| R4 | XLTW-Test-n1094 | 1093 | 60.00 | 7 | 94 | 80305 | True | True | 0 | True | 58.438 | 1.562 | 0.151 |  |
| R5 | XLTW-Test-n1094 | 1093 | 60.00 | 7 | 94 | 79908 | True | True | 0 | True | 58.481 | 1.519 | 0.151 |  |
| R6 | XLTW-Test-n1234 | 1233 | 120.00 | 3 | 35 | 87110 | True | True | 0 | True | 118.334 | 1.666 | 0.162 |  |
