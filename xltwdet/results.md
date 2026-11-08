# xltwdet: work budget vs wall clock, three XLTW-Test instances, seed 20261107, limit 120 s

Network reachable during the runs: False. Build: cp312, Python 3.12.15; pins ok: True.

Predictions (expectations.md): `{"D0": "held", "D1": "held", "D2": "did not hold", "D3": "held", "D4": "held", "D5": "held", "D6": "held"}`

| run | instance | mode | hog | vehicles | distance | solution sha256 (first 12) | elapsed s | budget | fleet it | distance it | clock stop | peak GB | attempts | valid |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A-W1 | XLTW-Test-n1048 | work | False | 8 | 52156 | fd076fda191b | 84.26 | 20803 | 10401 | 10402 | False | 0.134 | 1 | True |
| A-T1 | XLTW-Test-n1048 | time | False | 8 | 50561 | 159ddb0f8dae | 118.27 | None | None | 29977 | None | 0.134 | 1 | True |
| A-W2 | XLTW-Test-n1048 | work | False | 8 | 52156 | fd076fda191b | 78.95 | 20803 | 10401 | 10402 | False | 0.134 | 1 | True |
| A-W3 | XLTW-Test-n1048 | work | True | 8 | 52156 | fd076fda191b | 103.51 | 20803 | 10401 | 10402 | False | 0.126 | 1 | True |
| A-T2 | XLTW-Test-n1048 | time | True | 8 | 50983 | 26e8aabf306e | 118.27 | None | None | 18395 | None | 0.134 | 1 | True |
| B-W1 | XLTW-Test-n1094 | work | False | 93 | 81456 | 71c7bdf5b1af | 69.62 | 20361 | 10180 | 10181 | False | 0.15 | 1 | True |
| B-T1 | XLTW-Test-n1094 | time | False | 93 | 78960 | e203319b7d8a | 118.27 | None | None | 26376 | None | 0.159 | 1 | True |
| B-W2 | XLTW-Test-n1094 | work | False | 93 | 81456 | 71c7bdf5b1af | 51.4 | 20361 | 10180 | 10181 | False | 0.15 | 1 | True |
| B-W3 | XLTW-Test-n1094 | work | True | 93 | 81456 | 71c7bdf5b1af | 67.46 | 20361 | 10180 | 10181 | False | 0.149 | 1 | True |
| B-T2 | XLTW-Test-n1094 | time | True | 93 | 79467 | c34458ad7a88 | 118.29 | None | None | 19451 | None | 0.15 | 1 | True |
| C-W1 | XLTW-Test-n1234 | work | False | 35 | 88231 | 24e227d46898 | 101.35 | 19170 | 9585 | 9585 | False | 0.157 | 1 | True |
| C-T1 | XLTW-Test-n1234 | time | False | 35 | 85752 | 5c68f4a68712 | 118.27 | None | None | 23625 | None | 0.158 | 1 | True |
| C-W2 | XLTW-Test-n1234 | work | False | 35 | 88231 | 24e227d46898 | 97.5 | 19170 | 9585 | 9585 | False | 0.157 | 1 | True |
| C-W3 | XLTW-Test-n1234 | work | True | 35 | 88231 | 24e227d46898 | 118.27 | 19170 | 9585 | 8961 | distance | 0.152 | 1 | True |
| C-T2 | XLTW-Test-n1234 | time | True | 35 | 86400 | f43466816d85 | 118.27 | None | None | 19164 | None | 0.159 | 1 | True |
