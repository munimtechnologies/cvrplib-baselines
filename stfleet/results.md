# stfleet (mstfleet 0.2) on XLTW-Test: space-time spanning-tree fleet bounds

Pre-registered in PREREG.md. Solver 0.2.0. Certificates in cert/.

Tally: `{"instances_done": 33, "errors": [], "unverified": [], "above_ub": [], "above_kstar": ["XLTW-Test-n1048", "XLTW-Test-n1234", "XLTW-Test-n1421", "XLTW-Test-n1514", "XLTW-Test-n1608", "XLTW-Test-n1841", "XLTW-Test-n2867", "XLTW-Test-n3804", "XLTW-Test-n4340", "XLTW-Test-n4535", "XLTW-Test-n5774", "XLTW-Test-n5902", "XLTW-Test-n6305", "XLTW-Test-n6884", "XLTW-Test-n7854", "XLTW-Test-n8575", "XLTW-Test-n8960"], "service1_above_kstar": ["XLTW-Test-n1048", "XLTW-Test-n1514", "XLTW-Test-n2867", "XLTW-Test-n5902"], "proved": [], "hk_gain": ["XLTW-Test-n1234", "XLTW-Test-n1421", "XLTW-Test-n1514", "XLTW-Test-n1608", "XLTW-Test-n2401", "XLTW-Test-n2541", "XLTW-Test-n2681", "XLTW-Test-n2821", "XLTW-Test-n2867", "XLTW-Test-n3007", "XLTW-Test-n3408", "XLTW-Test-n3640", "XLTW-Test-n3804", "XLTW-Test-n4340", "XLTW-Test-n4535", "XLTW-Test-n5061", "XLTW-Test-n5288", "XLTW-Test-n5774", "XLTW-Test-n5902", "XLTW-Test-n6305", "XLTW-Test-n6884", "XLTW-Test-n8575", "XLTW-Test-n8960"], "above_v01_whole_day": ["XLTW-Test-n1048", "XLTW-Test-n1234", "XLTW-Test-n1421", "XLTW-Test-n1514", "XLTW-Test-n1608", "XLTW-Test-n1841", "XLTW-Test-n1934", "XLTW-Test-n2028", "XLTW-Test-n2214", "XLTW-Test-n2401", "XLTW-Test-n2541", "XLTW-Test-n2681", "XLTW-Test-n2821", "XLTW-Test-n2867", "XLTW-Test-n3007", "XLTW-Test-n3147", "XLTW-Test-n3408", "XLTW-Test-n3640", "XLTW-Test-n3804", "XLTW-Test-n4153", "XLTW-Test-n4340", "XLTW-Test-n4535", "XLTW-Test-n5061", "XLTW-Test-n5288", "XLTW-Test-n5774", "XLTW-Test-n5902", "XLTW-Test-n6305", "XLTW-Test-n6884", "XLTW-Test-n7516", "XLTW-Test-n7854", "XLTW-Test-n8575", "XLTW-Test-n8960", "XLTW-Test-n9784"], "best_not_whole_day": ["XLTW-Test-n1048", "XLTW-Test-n1234", "XLTW-Test-n1421", "XLTW-Test-n1514", "XLTW-Test-n1608", "XLTW-Test-n1841", "XLTW-Test-n1934", "XLTW-Test-n2028", "XLTW-Test-n2214", "XLTW-Test-n2401", "XLTW-Test-n2541", "XLTW-Test-n2681", "XLTW-Test-n2821", "XLTW-Test-n2867", "XLTW-Test-n3007", "XLTW-Test-n3147", "XLTW-Test-n3408", "XLTW-Test-n3640", "XLTW-Test-n3804", "XLTW-Test-n4153", "XLTW-Test-n4340", "XLTW-Test-n4535", "XLTW-Test-n5061", "XLTW-Test-n5288", "XLTW-Test-n5774", "XLTW-Test-n5902", "XLTW-Test-n6305", "XLTW-Test-n6884", "XLTW-Test-n7516", "XLTW-Test-n7854", "XLTW-Test-n8575", "XLTW-Test-n8960", "XLTW-Test-n9784"], "best_side_end": ["XLTW-Test-n1048", "XLTW-Test-n1234", "XLTW-Test-n1421", "XLTW-Test-n1514", "XLTW-Test-n1934", "XLTW-Test-n2028", "XLTW-Test-n2821", "XLTW-Test-n3804", "XLTW-Test-n4153", "XLTW-Test-n4340"], "n1048_bound": 4, "sum_kstar": 3275, "sum_max": 3330, "sum_v01_whole_day": 2358, "sum_bound": 2953, "peak_gb": 0.052}`

| instance | n | K* | stfleet | source | 0.1 whole day | side | interval | customers in it | mu | best known fleet | gap closed | s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| XLTW-Test-n1048 | 1047 | 3 | 4 | scan | 2 | end | [1438.0, 4376.0] | 189 | 2938 | 9 | 0.1667 | 33.5 |
| XLTW-Test-n1234 | 1233 | 27 | 28 | hk | 26 | end | [377.0, 8081.0] | 1148 | 7641 | 33 | 0.1667 | 73.9 |
| XLTW-Test-n1421 | 1420 | 47 | 49 | hk | 35 | end | [703.0, 2948.0] | 1237 | 2205 | 65 | 0.1111 | 80.5 |
| XLTW-Test-n1514 | 1513 | 16 | 18 | hk | 10 | end | [1674.0, 2538.0] | 547 | 887 | 44 | 0.0714 | 54.1 |
| XLTW-Test-n1608 | 1607 | 81 | 82 | hk | 68 | start | [324.0, 1943.0] | 1371 | 1582 | 108 | 0.037 | 90.1 |
| XLTW-Test-n1841 | 1840 | 18 | 19 | scan | 18 | start | [115.0, 8416.0] | 1840 | 8130 | 25 | 0.1429 | 127.0 |
| XLTW-Test-n1934 | 1933 | 43 | 43 | mu | 42 | end | [52.0, 5491.0] | 1933 | 5289 | 54 | 0.0 | 118.4 |
| XLTW-Test-n2028 | 2027 | 84 | 82 | hk | 78 | end | [260.0, 3941.0] | 1855 | 3622 | 103 | 0.0 | 118.5 |
| XLTW-Test-n2214 | 2213 | 53 | 52 | hk | 48 | start | [442.0, 5445.0] | 2037 | 4966 | 77 | 0.0 | 127.7 |
| XLTW-Test-n2401 | 2400 | 119 | 84 | hk | 46 | start | [318.0, 1040.0] | 432 | 704 | 190 | 0.0 | 89.2 |
| XLTW-Test-n2541 | 2540 | 91 | 48 | hk | 31 | start | [188.0, 948.0] | 257 | 762 | 133 | 0.0 | 87.5 |
| XLTW-Test-n2681 | 2680 | 100 | 96 | hk | 55 | start | [837.0, 3244.0] | 1267 | 2203 | 141 | 0.0 | 122.7 |
| XLTW-Test-n2821 | 2820 | 136 | 126 | hk | 110 | end | [239.0, 2987.0] | 2652 | 2668 | 236 | 0.0 | 181.5 |
| XLTW-Test-n2867 | 2866 | 4 | 7 | hk | 3 | start | [2550.0, 5628.0] | 1078 | 3108 | 29 | 0.12 | 115.7 |
| XLTW-Test-n3007 | 3006 | 158 | 72 | hk | 18 | start | [310.0, 553.0] | 252 | 259 | 190 | 0.0 | 101.6 |
| XLTW-Test-n3147 | 3146 | 68 | 68 | mu | 67 | start | [5.0, 8245.0] | 3146 | 8131 | 84 | 0.0 | 197.7 |
| XLTW-Test-n3408 | 3407 | 157 | 154 | hk | 130 | start | [458.0, 3239.0] | 2995 | 2729 | 221 | 0.0 | 210.9 |
| XLTW-Test-n3640 | 3639 | 243 | 102 | hk | 22 | start | [309.0, 581.0] | 538 | 271 | 310 | 0.0 | 120.1 |
| XLTW-Test-n3804 | 3803 | 88 | 89 | hk | 82 | end | [408.0, 5522.0] | 3540 | 4935 | 126 | 0.0263 | 230.9 |
| XLTW-Test-n4153 | 4152 | 200 | 193 | mu | 158 | end | [469.0, 3089.0] | 3830 | 2585 | 238 | 0.0 | 248.3 |
| XLTW-Test-n4340 | 4339 | 38 | 40 | hk | 37 | end | [41.0, 11210.0] | 4339 | 10962 | 84 | 0.0435 | 258.0 |
| XLTW-Test-n4535 | 4534 | 91 | 95 | hk | 78 | start | [681.0, 2518.0] | 2692 | 1786 | 179 | 0.0455 | 267.4 |
| XLTW-Test-n5061 | 5060 | 151 | 151 | hk | 116 | start | [260.0, 1476.0] | 4586 | 1201 | 231 | 0.0 | 294.3 |
| XLTW-Test-n5288 | 5287 | 77 | 55 | hk | 49 | start | [362.0, 5212.0] | 4982 | 4828 | 144 | 0.0 | 305.9 |
| XLTW-Test-n5774 | 5773 | 98 | 99 | hk | 96 | start | [13.0, 5633.0] | 5773 | 5469 | 126 | 0.0357 | 329.9 |
| XLTW-Test-n5902 | 5901 | 5 | 7 | hk | 5 | start | [457.0, 8143.0] | 2801 | 7693 | 45 | 0.05 | 285.0 |
| XLTW-Test-n6305 | 6304 | 207 | 215 | hk | 138 | start | [694.0, 2031.0] | 4213 | 1281 | 353 | 0.0548 | 356.6 |
| XLTW-Test-n6884 | 6883 | 138 | 145 | hk | 115 | start | [531.0, 2812.0] | 5529 | 2234 | None | None | 386.3 |
| XLTW-Test-n7516 | 7515 | 160 | 155 | mu | 151 | start | [23.0, 5332.0] | 7515 | 5188 | None | None | 417.7 |
| XLTW-Test-n7854 | 7853 | 17 | 22 | scan | 13 | start | [808.0, 2136.0] | 7050 | 1328 | None | None | 434.8 |
| XLTW-Test-n8575 | 8574 | 15 | 27 | hk | 14 | start | [570.0, 2067.0] | 2236 | 1509 | None | None | 328.7 |
| XLTW-Test-n8960 | 8959 | 154 | 156 | hk | 143 | start | [427.0, 5055.0] | 8009 | 4542 | None | None | 482.3 |
| XLTW-Test-n9784 | 9783 | 388 | 370 | mu | 354 | start | [307.0, 4907.0] | 8967 | 4514 | None | None | 483.6 |
