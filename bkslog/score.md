# bkslog: scoring of `cvrplib-bkslog-v1` (CVRPLib's updates page read 2026-11-01 08:00 UTC)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Code Apache-2.0, text and data CC BY 4.0.

Predictions: [expectations.md](expectations.md), published before pages 2 to 7 were read. Numbers below are taken
from [summary.json](summary.json) (written by `bkslog.py`) and from counting rows of [log_raw.csv](log_raw.csv).
This is an open, machine-readable copy of a public announcement log, not a judgement of anyone's work.

## What was read

All 7 pages of https://galgos.inf.puc-rio.br/cvrplib/en/updates/ (125 dated entries; the parser found entries on
every page, so the layout was read). 469 `instance (value)` pairs for X and XL CVRP instances, 453 after merging
repeats of the same instance and value; 170 of them on 82 distinct XL instances. Dates run from 2015-01-05 to
2026-10-31.

## Verdicts

| | Prediction | Result | Verdict |
|---|---|---|---|
| B1 | For each XL instance, at least 95% of consecutive reported values (in date order, same-date pairs skipped) go down | 83 of 83 pairs go down (100%) | held |
| B2 | At least 25 distinct XL instances have a report dated 2026-02-12 to 2026-09-30 | 75 | held |
| B3 | At least 60% of the XL reports in that period are on instances with 5,000 or more customers | 31 of 78 (39.7%) | **did not hold** |

## What the log shows, and a caveat on B2

- **Timing.** The log has no XL report between the end of the CVRP BKS Challenge (2026-02-11) and 2026-07-04, and no
  report of any kind between 2025-06-21 and 2026-07-04. XL reports by month: 1 in July, 77 in September and 92 in
  October 2026. Improvements made during the challenge itself appear to have been tracked on the challenge's own
  score pages instead (not checked here).
- **B2 rests on one entry.** 70 of the 78 XL reports dated 2026-02-12 to 2026-09-30 come from a single entry of
  2026-09-11 (credited to the Famou Agent Team, Baidu AI Cloud), which lists new values for 70 XL instances at once.
  The other 8 reports in the period are on 8 instances. Without that entry B2 would not have held. The prediction is
  scored as written.
- **Sizes.** Over all dates, XL reports per size band (reports / distinct instances): 1,000 to 2,499 customers 39 / 20;
  2,500 to 4,999 58 / 31; 5,000 to 7,499 33 / 17; 7,500 to 10,001 40 / 14. New values keep coming at every size, not
  mainly at the largest ones, which is why B3 failed.
- **Since 2026-10-28** CVRPLib publishes verified submissions automatically in a daily digest (its own announcement on
  the same page), so October's count is not comparable with earlier months.

## Limits

Only what the page announces in the form `name (value)` is counted. A credit is the last "reported by" in the same
dated entry; 138 of the 469 pairs (including all 4 dated 2026-07-04) have no credit in that form and are left blank. Values are as
printed and were not re-checked against solution files. The raw HTML pages are kept in the job's output and are not
redistributed here.

## Why this was done

CVRPLib's VRPTW challenge on XLTW instances (same locations as XL, 1,000 to 10,000 customers) runs from 2027-02-24 to
2027-03-26. The XL log suggests that after a challenge ends, best known values keep falling at every size and that
large batches can arrive in one entry, so a best known solution at any XLTW size should be expected to be contested.
