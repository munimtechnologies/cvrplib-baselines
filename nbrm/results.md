# nbrm: Nagata & Braysy route minimiser (Astronomax, MIT) on four capacity-free XLTW-Test instances

Job nbrm-v2. Seed 20261104. Build: {"repo": "https://github.com/Astronomax/vrptw-powerful-route-minimization-heuristic.git", "commit_asked": "89d4c05", "built": true, "commit": "89d4c050e9f68ed9470114b5043c9cd8dc56f00a", "submodules": "0192daa14787481d6328ba9f4449f6ded88224ca src/lib/small (1.1-170-g0192daa)", "patch_matches": 1, "problem_c_sha256_patched": "88f34dbdbd81f68832ea103cc450f249e354438fa751d33fedcc93aec363bc3d", "flags": ["-DCMAKE_BUILD_TYPE=Release", "-DENABLE_MARCH_NATIVE=OFF"], "binary_sha256": "44f954556d38546a27f91e969d3707001effebae85f0949c77ce795e93f667da", "prereg_sha256": "c528421c28342757003e3d70662337571cab5995a8e8bb0e49e0eec0b2ef5108", "addendum_sha256": "ca23d9daf3a3837c2e8027244c18dab529ef726f0fc953e307cbba091e95c292"}. Network reachable during the runs: False.

Predictions (expectations.md): `{"N0": "held", "N1": "did not hold", "N2": "did not hold", "N3": "did not hold", "N4": "held", "N5": "held"}`

Smoke run: `{"vehicles": 6, "feasible": true, "reason": "", "exit": 0, "cpu": 0.02}`

| run | instance | n | L s | K* | PyVRP best | vehicles | final count first at CPU s | CPU s | wall s | peak GB | distance (round) | exit | killed | feasible | valid |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| N1 | XLTW-Test-n1234 | 1233 | 1109 | 27 | 33 | 34 | 131.7 | 1109.02 | 1112.08 | 0.043 | 95444 | 0 | None | True | True |
| N2 | XLTW-Test-n1421 | 1420 | 1278 | 47 | 65 | 66 | 109.82 | 1278.05 | 1280.7 | 0.053 | 140789 | 0 | None | True | True |
| N3 | XLTW-Test-n1608 | 1607 | 1446 | 81 | 108 | 109 | 1116.39 | 1446.08 | 2153.54 | 0.063 | 117814 | 0 | None | True | True |
| N4 | XLTW-Test-n1841 | 1840 | 1656 | 18 | 25 | 26 | 342.5 | 1656.17 | 1743.02 | 0.066 | 102392 | 0 | None | True | True |
