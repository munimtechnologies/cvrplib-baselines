# Exact (50-digit) re-check of CVRPLib VRPTW solutions in double-precision convention

Tally: `{"rows": 86, "reference_rows": 86, "missing_reference": [], "routes_mismatch": [], "S1_feasibility_disagree": [], "S2_late_disagree": [], "S3_distance_disagree": [], "S4_outside_truncation_bound": [], "infeasible": ["R102/cvrplib-bks", "R105/cvrplib-bks", "R107/cvrplib-bks", "R108/cvrplib-bks", "R112/cvrplib-bks", "R211/cvrplib-bks", "RC101/cvrplib-bks", "RC105/cvrplib-bks", "R1_10_1/cvrplib-bks", "RC2_10_1/cvrplib-bks", "R102/pyvrp-lex", "R105/pyvrp-lex", "R112/pyvrp-lex", "R1_10_1/pyvrp-lex", "R202/pyvrp-lex", "RC202/pyvrp-lex"], "late_visits": 30, "feasible_min_slack_below_0.1": 11, "feasible_min_slack_below_0.01": 4, "feasible": 70}`

| instance | source | routes | feasible | distance | late (routes) | max late | min slack | agrees with vrptwd |
|---|---|---|---|---|---|---|---|---|
| C101 | cvrplib-bks | 10 | True | 828.936867 | 0 (0) | 0.000000 | 0.220282 | yes |
| C102 | cvrplib-bks | 10 | True | 828.936867 | 0 (0) | 0.000000 | 0.220282 | yes |
| C103 | cvrplib-bks | 10 | True | 828.064882 | 0 (0) | 0.000000 | 0.220282 | yes |
| C104 | cvrplib-bks | 10 | True | 824.776708 | 0 (0) | 0.000000 | 0.220282 | yes |
| C105 | cvrplib-bks | 10 | True | 828.936867 | 0 (0) | 0.000000 | 0.220282 | yes |
| C106 | cvrplib-bks | 10 | True | 828.936867 | 0 (0) | 0.000000 | 0.220282 | yes |
| C107 | cvrplib-bks | 10 | True | 828.936867 | 0 (0) | 0.000000 | 0.220282 | yes |
| C108 | cvrplib-bks | 10 | True | 828.936867 | 0 (0) | 0.000000 | 0.220282 | yes |
| C109 | cvrplib-bks | 10 | True | 828.936867 | 0 (0) | 0.000000 | 0.220282 | yes |
| C201 | cvrplib-bks | 3 | True | 591.556557 | 0 (0) | 0.000000 | 1.407120 | yes |
| C202 | cvrplib-bks | 3 | True | 591.556557 | 0 (0) | 0.000000 | 1.407120 | yes |
| C203 | cvrplib-bks | 3 | True | 591.173443 | 0 (0) | 0.000000 | 1.407120 | yes |
| C204 | cvrplib-bks | 3 | True | 590.598746 | 0 (0) | 0.000000 | 1.407120 | yes |
| C205 | cvrplib-bks | 3 | True | 588.875963 | 0 (0) | 0.000000 | 4.087714 | yes |
| C206 | cvrplib-bks | 3 | True | 588.492849 | 0 (0) | 0.000000 | 0.936304 | yes |
| C207 | cvrplib-bks | 3 | True | 588.286321 | 0 (0) | 0.000000 | 4.087714 | yes |
| C208 | cvrplib-bks | 3 | True | 588.323801 | 0 (0) | 0.000000 | 4.087714 | yes |
| R101 | cvrplib-bks | 20 | True | 1642.876875 | 0 (0) | 0.000000 | 0.462795 | yes |
| R102 | cvrplib-bks | 18 | False | 1471.745684 | 1 (1) | 0.070719 | -0.070719 | yes |
| R103 | cvrplib-bks | 14 | True | 1213.623943 | 0 (0) | 0.000000 | 0.171573 | yes |
| R104 | cvrplib-bks | 11 | True | 976.693248 | 0 (0) | 0.000000 | 0.171573 | yes |
| R105 | cvrplib-bks | 15 | False | 1360.120328 | 1 (1) | 0.103852 | -0.103852 | yes |
| R106 | cvrplib-bks | 13 | True | 1239.371883 | 0 (0) | 0.000000 | 0.036767 | yes |
| R107 | cvrplib-bks | 11 | False | 1069.094652 | 1 (1) | 0.136817 | -0.136817 | yes |
| R108 | cvrplib-bks | 10 | False | 936.689123 | 1 (1) | 0.371709 | -0.371709 | yes |
| R109 | cvrplib-bks | 13 | True | 1151.911715 | 0 (0) | 0.000000 | 0.055728 | yes |
| R110 | cvrplib-bks | 12 | True | 1072.477218 | 0 (0) | 0.000000 | 0.016442 | yes |
| R111 | cvrplib-bks | 12 | True | 1053.495774 | 0 (0) | 0.000000 | 0.055728 | yes |
| R112 | cvrplib-bks | 10 | False | 953.439185 | 1 (1) | 0.400162 | -0.400162 | yes |
| R201 | cvrplib-bks | 8 | True | 1147.820306 | 0 (0) | 0.000000 | 3.958405 | yes |
| R202 | cvrplib-bks | 8 | True | 1034.347225 | 0 (0) | 0.000000 | 0.694035 | yes |
| R203 | cvrplib-bks | 6 | True | 874.868867 | 0 (0) | 0.000000 | 0.337893 | yes |
| R204 | cvrplib-bks | 5 | True | 735.861285 | 0 (0) | 0.000000 | 5.107556 | yes |
| R205 | cvrplib-bks | 5 | True | 954.161676 | 0 (0) | 0.000000 | 1.699437 | yes |
| R206 | cvrplib-bks | 5 | True | 879.893394 | 0 (0) | 0.000000 | 2.236252 | yes |
| R207 | cvrplib-bks | 4 | True | 798.083529 | 0 (0) | 0.000000 | 2.754391 | yes |
| R208 | cvrplib-bks | 4 | True | 705.331200 | 0 (0) | 0.000000 | 4.233831 | yes |
| R209 | cvrplib-bks | 5 | True | 859.390363 | 0 (0) | 0.000000 | 0.119172 | yes |
| R210 | cvrplib-bks | 6 | True | 904.807320 | 0 (0) | 0.000000 | 0.459747 | yes |
| R211 | cvrplib-bks | 4 | False | 751.293321 | 1 (1) | 0.341171 | -0.341171 | yes |
| RC101 | cvrplib-bks | 15 | False | 1623.557104 | 1 (1) | 0.070329 | -0.070329 | yes |
| RC102 | cvrplib-bks | 14 | True | 1461.334134 | 0 (0) | 0.000000 | 0.149079 | yes |
| RC103 | cvrplib-bks | 11 | True | 1261.671856 | 0 (0) | 0.000000 | 0.348232 | yes |
| RC104 | cvrplib-bks | 10 | True | 1135.479396 | 0 (0) | 0.000000 | 0.348232 | yes |
| RC105 | cvrplib-bks | 15 | False | 1517.929825 | 1 (1) | 0.097245 | -0.097245 | yes |
| RC106 | cvrplib-bks | 12 | True | 1376.255960 | 0 (0) | 0.000000 | 1.036995 | yes |
| RC107 | cvrplib-bks | 12 | True | 1211.125832 | 0 (0) | 0.000000 | 0.247011 | yes |
| RC108 | cvrplib-bks | 11 | True | 1117.526462 | 0 (0) | 0.000000 | 0.795363 | yes |
| RC201 | cvrplib-bks | 9 | True | 1265.556278 | 0 (0) | 0.000000 | 0.000000 | yes |
| RC202 | cvrplib-bks | 8 | True | 1095.643862 | 0 (0) | 0.000000 | 0.408740 | yes |
| RC203 | cvrplib-bks | 5 | True | 926.898709 | 0 (0) | 0.000000 | 0.639320 | yes |
| RC204 | cvrplib-bks | 4 | True | 786.538866 | 0 (0) | 0.000000 | 0.200274 | yes |
| RC205 | cvrplib-bks | 7 | True | 1157.664814 | 0 (0) | 0.000000 | 2.397675 | yes |
| RC206 | cvrplib-bks | 7 | True | 1054.605671 | 0 (0) | 0.000000 | 11.971009 | yes |
| RC207 | cvrplib-bks | 6 | True | 966.372359 | 0 (0) | 0.000000 | 0.394449 | yes |
| RC208 | cvrplib-bks | 4 | True | 778.925640 | 0 (0) | 0.000000 | 0.095701 | yes |
| C1_10_1 | cvrplib-bks | 100 | True | 42479.078024 | 0 (0) | 0.000000 | 0.944963 | yes |
| C2_10_1 | cvrplib-bks | 30 | True | 16879.295400 | 0 (0) | 0.000000 | 5.060180 | yes |
| R1_10_1 | cvrplib-bks | 95 | False | 53072.011193 | 7 (7) | 0.124531 | -0.124531 | yes |
| R2_10_1 | cvrplib-bks | 37 | True | 36926.646580 | 0 (0) | 0.000000 | 0.675061 | yes |
| RC1_10_1 | cvrplib-bks | 90 | True | 45830.639705 | 0 (0) | 0.000000 | 0.000000 | yes |
| RC2_10_1 | cvrplib-bks | 29 | False | 28161.282729 | 2 (2) | 0.082763 | -0.082763 | yes |
| R101 | pyvrp-lex | 19 | True | 1651.103785 | 0 (0) | 0.000000 | 0.455900 | yes |
| R102 | pyvrp-lex | 17 | False | 1485.050224 | 1 (1) | 0.070719 | -0.070719 | yes |
| R104 | pyvrp-lex | 9 | True | 1007.310577 | 0 (0) | 0.000000 | 0.171573 | yes |
| R105 | pyvrp-lex | 14 | False | 1372.182565 | 1 (1) | 0.103852 | -0.103852 | yes |
| R108 | pyvrp-lex | 9 | True | 960.875779 | 0 (0) | 0.000000 | 0.071060 | yes |
| R109 | pyvrp-lex | 11 | True | 1197.419866 | 0 (0) | 0.000000 | 0.866802 | yes |
| R111 | pyvrp-lex | 10 | True | 1096.735385 | 0 (0) | 0.000000 | 0.055728 | yes |
| R112 | pyvrp-lex | 9 | False | 980.965594 | 1 (1) | 0.104552 | -0.104552 | yes |
| R1_10_1 | pyvrp-lex | 94 | False | 59570.884066 | 8 (8) | 0.105608 | -0.105608 | yes |
| R201 | pyvrp-lex | 4 | True | 1252.387755 | 0 (0) | 0.000000 | 0.372946 | yes |
| R202 | pyvrp-lex | 3 | False | 1190.776372 | 1 (1) | 0.048779 | -0.048779 | yes |
| R203 | pyvrp-lex | 3 | True | 941.407839 | 0 (0) | 0.000000 | 0.668348 | yes |
| R205 | pyvrp-lex | 3 | True | 994.427657 | 0 (0) | 0.000000 | 0.615450 | yes |
| R206 | pyvrp-lex | 3 | True | 906.142079 | 0 (0) | 0.000000 | 0.384227 | yes |
| R208 | pyvrp-lex | 2 | True | 726.822786 | 0 (0) | 0.000000 | 2.363215 | yes |
| R209 | pyvrp-lex | 3 | True | 909.656561 | 0 (0) | 0.000000 | 0.105871 | yes |
| RC101 | pyvrp-lex | 14 | True | 1696.949157 | 0 (0) | 0.000000 | 0.000000 | yes |
| RC102 | pyvrp-lex | 12 | True | 1554.837336 | 0 (0) | 0.000000 | 0.000000 | yes |
| RC106 | pyvrp-lex | 11 | True | 1424.733684 | 0 (0) | 0.000000 | 0.217547 | yes |
| RC107 | pyvrp-lex | 11 | True | 1232.207574 | 0 (0) | 0.000000 | 0.492429 | yes |
| RC108 | pyvrp-lex | 10 | True | 1139.821433 | 0 (0) | 0.000000 | 0.686293 | yes |
| RC202 | pyvrp-lex | 3 | False | 1335.936405 | 1 (1) | 0.087479 | -0.087479 | yes |
| RC204 | pyvrp-lex | 3 | True | 798.463581 | 0 (0) | 0.000000 | 0.200274 | yes |
| RC205 | pyvrp-lex | 4 | True | 1297.647746 | 0 (0) | 0.000000 | 0.203928 | yes |

## Late visits

| instance | source | route | customer | arrival | due | late by | arcs so far |
|---|---|---|---|---|---|---|---|
| R102 | cvrplib-bks | 18 | 14 | 42.070719 | 42.0 | 0.070719 | 2 |
| R105 | cvrplib-bks | 2 | 83 | 64.103852 | 64.0 | 0.103852 | 3 |
| R107 | cvrplib-bks | 1 | 74 | 169.136817 | 169.0 | 0.136817 | 9 |
| R108 | cvrplib-bks | 8 | 28 | 213.371709 | 213.0 | 0.371709 | 11 |
| R112 | cvrplib-bks | 8 | 5 | 167.400162 | 167.0 | 0.400162 | 10 |
| R211 | cvrplib-bks | 3 | 94 | 656.341171 | 656.0 | 0.341171 | 29 |
| RC101 | cvrplib-bks | 4 | 46 | 143.070329 | 143.0 | 0.070329 | 6 |
| RC105 | cvrplib-bks | 1 | 6 | 123.097245 | 123.0 | 0.097245 | 7 |
| R1_10_1 | cvrplib-bks | 4 | 885 | 200.044637 | 200.0 | 0.044637 | 2 |
| R1_10_1 | cvrplib-bks | 17 | 544 | 184.105608 | 184.0 | 0.105608 | 2 |
| R1_10_1 | cvrplib-bks | 49 | 433 | 192.013750 | 192.0 | 0.013750 | 2 |
| R1_10_1 | cvrplib-bks | 58 | 515 | 164.085790 | 164.0 | 0.085790 | 2 |
| R1_10_1 | cvrplib-bks | 61 | 1000 | 94.062358 | 94.0 | 0.062358 | 2 |
| R1_10_1 | cvrplib-bks | 79 | 736 | 554.041595 | 554.0 | 0.041595 | 5 |
| R1_10_1 | cvrplib-bks | 87 | 28 | 65.124531 | 65.0 | 0.124531 | 2 |
| RC2_10_1 | cvrplib-bks | 12 | 782 | 1571.063352 | 1571.0 | 0.063352 | 17 |
| RC2_10_1 | cvrplib-bks | 20 | 443 | 1479.082763 | 1479.0 | 0.082763 | 20 |
| R102 | pyvrp-lex | 2 | 14 | 42.070719 | 42.0 | 0.070719 | 2 |
| R105 | pyvrp-lex | 12 | 83 | 64.103852 | 64.0 | 0.103852 | 3 |
| R112 | pyvrp-lex | 1 | 23 | 155.104552 | 155.0 | 0.104552 | 8 |
| R1_10_1 | pyvrp-lex | 35 | 656 | 124.070240 | 124.0 | 0.070240 | 2 |
| R1_10_1 | pyvrp-lex | 42 | 1000 | 94.062358 | 94.0 | 0.062358 | 2 |
| R1_10_1 | pyvrp-lex | 44 | 544 | 184.105608 | 184.0 | 0.105608 | 2 |
| R1_10_1 | pyvrp-lex | 50 | 848 | 179.083269 | 179.0 | 0.083269 | 2 |
| R1_10_1 | pyvrp-lex | 66 | 736 | 554.041595 | 554.0 | 0.041595 | 4 |
| R1_10_1 | pyvrp-lex | 70 | 433 | 192.013750 | 192.0 | 0.013750 | 2 |
| R1_10_1 | pyvrp-lex | 73 | 515 | 164.085790 | 164.0 | 0.085790 | 2 |
| R1_10_1 | pyvrp-lex | 80 | 885 | 200.044637 | 200.0 | 0.044637 | 2 |
| R202 | pyvrp-lex | 3 | 55 | 739.048779 | 739.0 | 0.048779 | 24 |
| RC202 | pyvrp-lex | 2 | 9 | 491.087479 | 491.0 | 0.087479 | 19 |
