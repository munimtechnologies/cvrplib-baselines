# xltwff part a: raw results (not scored yet)

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. CC BY 4.0.

Job `xltwff-a-v1` ran H1 and H3 of `expectations.md` on 2026-11-07 (00:41-02:09 UTC, one CPU, 1 GB): the packaged
solver with its fleet phase given 0.8 of the time instead of 0.5, at the full limit T(n), seed 20261104, through
xltwfull's harness. Raw results: `results-a.json`, `results-a.md`, `logs-a/`, `sols/`.

| run | instance | limit s | vehicles (0.8) | xltwfull part a (0.5) | final count first printed at s | distance (0.8) | xltwfull distance | fleet solves | slack s | peak GB |
|---|---|---|---|---|---|---|---|---|---|---|
| H1 | XLTW-Test-n1234 | 2,219.4 | 33 | 34 | 1,203.2 | 84,722 | 83,690 | 22 | 5.9 | 0.164 |
| H3 | XLTW-Test-n1608 | 2,892.6 | 108 | 108 | 1,193.0 | 112,903 | 112,655 | 15 | 7.2 | 0.239 |

Both runs stopped by themselves with exit 0, their counted solutions are feasible in exact arithmetic, and the
harness never went more than 1 s between polls (not frozen).

**Pause audit.** The host's compete log has no `paused` entry for this job (id 6a000ca968cf), so neither run was
paused, including pauses short enough to slip between two harness polls.

**Not scored yet.** H0-H5 are scored once, on all four runs, after part b (H2, H4) and xltwfull's merge, by the
merge step the pre-registration names. Part b is running; its job was paused by the host for about 93 s at
03:35 UTC, during H4, so the harness's frozen-run rule (re-run once) will apply there. Two observations here are
descriptive only: on n1234 the longer fleet phase found one vehicle fewer (33 against 34) at a distance 1.2%
longer; on n1608 it found the same 108 vehicles at a distance 0.2% longer. (The 0.5 figures are from xltwfull part
a, whose run on n1608 was valid; xltwfull as a whole failed its gate because of F2.)
