"""Setup for xltwmerge2: fetch the pinned harnesses, the xltwmerge-v1 raw parts and the clean re-run files.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

Harness code comes from the same pinned commits as xltwmerge-v1; raw results from `main`. The attempt-2 re-run
files (xltwrun/rerun-v2/) are published right after the run that filed this job, so this waits (up to 50 minutes)
until they are public.
"""
import os
import sys
import time
import urllib.request

REPO = "https://raw.githubusercontent.com/munimtechnologies/cvrplib-baselines/"
PINNED = [
    ("ba1eec829de01be15050feef8cf55ace5d9f032e/xltwrun/xltwrun.py", "xltwrun.py"),
    ("ba1eec829de01be15050feef8cf55ace5d9f032e/xltwrun/solver.py", "solver.py"),
    ("v0.3.7/xltwbase/xltwbase.py", "xltwbase.py"),
    ("v0.3.7/xltwlb/xltwlb.py", "xltwlb.py"),
]
MAIN = [
    "xltwrun/results-a.json", "xltwrun/results-b1.json", "xltwrun/results-b2.json", "xltwrun/results-b3.json",
    "xltwrun/results-b1ra.json", "xltwrun/results-b1rb.json", "xltwrun/results-b2r.json",
    "xltwrun/results-b3ra.json", "xltwrun/results-b3rb.json",
    "xltwrun/rerun-v1/results-r7037.json", "xltwrun/rerun-v1/results-r9571.json",
    "xltwrun/rerun-v1/results-r10001.json",
    "xltwrun/rerun-v2/results-r8389.json", "xltwrun/rerun-v2/results-r8575.json",
    "xltwrun/rerun-v2/results-r9160.json", "xltwrun/rerun-v2/results-r9363.json",
]


def get(url, dest, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
            with open(dest, "wb") as f:
                f.write(data)
            return True
        except Exception as e:  # noqa: BLE001 - retried, then reported
            last = e
            time.sleep(5 * (i + 1))
    print("could not fetch %s: %r" % (url, last), flush=True)
    return False


def main():
    for path, dest in PINNED:
        if not get(REPO + path, dest):
            return 1
    deadline = time.time() + 50 * 60
    missing = list(MAIN)
    while missing and time.time() < deadline:
        for p in list(missing):
            if get(REPO + "main/" + p + "?t=%d" % int(time.time()), os.path.join("in", p), tries=1):
                missing.remove(p)
        if missing:
            print("waiting for %s" % missing, flush=True)
            time.sleep(120)
    if missing:
        print("not public after 50 minutes: %s" % missing, flush=True)
        return 1
    print("fetched %d pinned files and %d result files" % (len(PINNED), len(MAIN)), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
