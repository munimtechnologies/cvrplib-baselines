# xltwpkg: the v1 jobs (2026-11-06) scored nothing

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. CC BY 4.0.

| job | image | where it stopped | C0 | C1-C6 | C7-C8 |
|---|---|---|---|---|---|
| `xltwpkg-py312-v1` | python:3.12 | unit tests (2 of 20 failed) | not scored | not scored | - |
| `xltwpkg-py311-v1` | python:3.11 | setup: DNS failure fetching XLTW-Test | not scored | not scored | - |
| `xltwpkg-n8575-v1` | python:3.12 | replaced by v2 before it ran | - | - | not scored |

**py312.** The offline build passed with the network off (`build.sh: ok, pyvrp 0.14.1 and numpy 2.3.4 from lib/`),
but it built for `/usr/bin/python3.13`, not the image's default Python 3.12. 18 of 20 unit tests passed, among
them both watchdog tests (`test_hard_deadline_ends_a_stuck_call`, `test_sigterm_ends_a_stuck_call_at_once`) and
the stdout test. The two that failed import `lib/` in a subprocess under the tests' Python 3.12, where numpy's
cp313 extension cannot load. The run stopped there, so no conformance run took place. We do not count C0 as held
from the build's own self-check: C0 was meant to be scored by `conformance.py`, and it never ran.

**py311.** `fetch_helpers.py` fetched both helpers and confirmed the pre-registration (SHA-256 296c734b...), then
failed to resolve `galgos.inf.puc-rio.br` on its single try at the XLTW-Test archive.

Cause, fix and the jobs that replace these: [addendum-2026-11-06.md](addendum-2026-11-06.md). Raw summaries of the
v1 jobs are not committed. The logs quoted here are the jobs' own step logs.
