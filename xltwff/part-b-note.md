# xltwff part b: raw results

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. CC BY 4.0.

Job `xltwff-b-v1` (id a9c760e61eff) ran H2 and H4 of `expectations.md` on the Blade on 2026-11-07 (02:09-04:44 UTC,
one CPU, 1 GB): the packaged solver with its fleet phase given 0.8 of the time, at the full limit T(n), seed
20261104, through xltwfull's harness. Raw results: `results-b.json`, `results-b.md`, `logs-b/`, `sols/`.

| run | instance | limit s | vehicles | final count first printed at s | distance | fleet s | fleet solves | slack s | peak GB | max poll gap s |
|---|---|---|---|---|---|---|---|---|---|---|
| H2 | XLTW-Test-n1421 | 2,556.0 | 65 | 1,309.43 | 130,271 | 2,039.1 | 25 | 6.55 | 0.213 | 0.053 |
| H4 | XLTW-Test-n1841 | 3,312.0 | 25 | 228.85 | 84,744 | 2,642.4 | 28 | 8.03 | 0.271 | 0.055 |

Both counted runs stopped by themselves with exit 0, and their solutions are feasible in exact arithmetic.

**Pause audit.** The runner's log has one pause for this job: 03:35:13 to 03:36:46 UTC (logged about 4 s after it
took effect). The run step began at 02:10:46 and ended at 04:43:24 UTC, 9,158 s, while the two counted runs took
5,853.5 s. So H2 ran 02:10:46-02:53:16, H4's first try ran 02:53:16-03:48:20 and contained the pause, and the
counted H4 is the harness's re-run (03:48:20-04:43:24), which had no pause. `results-b.json` keeps only counted runs,
so the discarded try is inferred from these times, not recorded in the file.

Scored in [score.md](score.md).
