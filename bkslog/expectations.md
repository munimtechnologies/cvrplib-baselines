# CVRPLib BKS log: predictions fixed before the log is read (2026-10-31 ~19:30 UTC)

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Code Apache-2.0, text CC BY 4.0.

**What.** CVRPLib's [updates page](https://galgos.inf.puc-rio.br/cvrplib/en/updates/) is where new best known
solutions (BKS) for its instances are announced, with the date and the credit of whoever reported them. It is
paginated (seven pages at the time of writing) and has no machine-readable form that we found. `bkslog.py` reads
every page once, at least 2 s apart, keeps the raw HTML, and writes one row per reported `<instance> (<value>)`
pair for X and XL CVRP instances: `log_raw.csv` (every pair as printed), `log.csv` (one row per instance and value,
earliest date) and `per_instance.csv`, plus `summary.json` with reports by month and by size band.

**Why.** The XL CVRP challenge ended on 2026-02-11. CVRPLib's VRPTW challenge on XLTW (same depot and customer
locations as XL, 1,000 to 10,000 customers) runs from 2027-02-24 to 2027-03-26. How often, and on which sizes, XL
BKSs kept falling after the CVRP challenge tells us which XLTW sizes are likely to stay contested. This is a
description of a public announcement log, not a judgement of anyone's work.

**Seen before writing.** Only page 1 (entries from 2026-10-01 to 2026-10-30, read through a summarising fetch
tool) and one search snippet mentioning an XL-n2354-k631 entry dated 2026-09-10. Nothing else from pages 2-7 was
read. The predictions below concern 2026-02-12 to 2026-09-30, which page 1 does not cover.

| | Prediction | Our odds |
|---|---|---|
| B1 | For each XL instance, taking its reported values in date order (pairs on the same date skipped), at least 95% of consecutive pairs go down. | 85% |
| B2 | At least 25 distinct XL instances have a report dated 2026-02-12 to 2026-09-30. | 55% |
| B3 | Of the XL reports dated 2026-02-12 to 2026-09-30 (after merging repeats of the same instance and value), at least 60% are on instances with 5,000 or more customers. | 60% |

Scored by `predictions()` in `bkslog.py` exactly as written above; the scores are in `summary.json`.

**Limits.** The log holds only what the page announces: a BKS found but not announced there, or announced in a
form other than `name (value)`, is missed. A credit is the last "reported by ...:" in the same dated entry, so a
paragraph without its own credit inherits the previous one. Values are as printed; nothing is re-checked against
solution files. If the page layout defeats the parser (no dated entries found), that is recorded and nothing is
scored.
