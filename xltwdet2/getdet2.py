"""Setup for the xltwdet2 job (network on).

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

1. Fetch the packaging files exactly as `xltwdet/` used them (cvrplib-baselines commit 19c7eb6, xltwpkg/: build,
   lock, conformance, tests) and xltwfull's harness (commit 876bd94). solver.py is NOT fetched from there: the local
   solver.py is xltw-solver 0.2.0, the version under test.
2. Make every local text file LF-only (the package's own test refuses CR bytes).
3. Wait (at most 90 min) until xltw-solver 0.2.0 is public: solver.py and test_budget.py on
   munimtechnologies/xltw-solver main must be byte-identical to the local copies, so the run tests what is published.
4. Wait until xltwdet2/PREREG.md on cvrplib-baselines main is byte-identical to the local PREREG.md.
Every file's SHA-256 goes to det2-manifest.json.
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
B = "https://raw.githubusercontent.com/munimtechnologies/cvrplib-baselines/"
S = "https://raw.githubusercontent.com/munimtechnologies/xltw-solver/main/"
PKG_COMMIT = "19c7eb668dc1e8e87d3d99ccc11186a5723eb1a9"
PKG_FILES = ["README.md", "Makefile", "build.sh", "lock.py", "test_pkg.py", "conformance.py", "fetch_helpers.py",
             "addendum-2026-11-06.md"]
FULL_COMMIT = "876bd94bcf1f8aacc6b158d220b9286bdac1a886"
FULL_FILES = ["fullrun.py", "test_fullrun.py"]
LOCAL_TEXT = ["solver.py", "test_budget.py", "det2run.py", "test_det2run.py", "PREREG.md"]
PUBLISHED = ["solver.py", "test_budget.py"]
UA = "xltwdet2 job - MV2 of Munim, Inc. (mv2@munimtech.com)"
WAIT = 90 * 60


def get(url, timeout=120, tries=4, wait=30.0):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except (urllib.error.URLError, OSError) as e:
            if i == tries - 1:
                raise
            print("retrying %s after %s" % (url, e), flush=True)
            time.sleep(wait)
    raise AssertionError("unreachable")


def norm(b):
    return b.replace(b"\r\n", b"\n")


def lf_only(names, dest=HERE):
    for name in names:
        p = os.path.join(dest, name)
        with open(p, "rb") as f:
            body = f.read()
        if b"\r" in body:
            with open(p, "wb") as f:
                f.write(norm(body).replace(b"\r", b"\n"))
            print("%s: made LF-only" % name, flush=True)


def sha_file(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def wait_identical(url, local_path, what, deadline, getter=get, sleep=time.sleep):
    with open(local_path, "rb") as f:
        local = norm(f.read())
    while True:
        try:
            body = norm(getter(url + "?nocache=%d" % int(time.time()), tries=1))
            if body == local:
                print("%s public and identical, sha256 %s" % (what, hashlib.sha256(local).hexdigest()), flush=True)
                return hashlib.sha256(local).hexdigest()
            print("%s on main differs from the local copy; waiting" % what, flush=True)
        except (urllib.error.URLError, OSError) as e:
            print("waiting for %s (%s)" % (what, e), flush=True)
        if time.time() > deadline:
            sys.exit("%s never became public as expected: not running" % what)
        sleep(60)


def main():
    manifest = {"package_commit": PKG_COMMIT, "harness_commit": FULL_COMMIT, "files": {}}
    for commit, folder, names in ((PKG_COMMIT, "xltwpkg", PKG_FILES), (FULL_COMMIT, "xltwfull", FULL_FILES)):
        for name in names:
            body = get(B + commit + "/" + folder + "/" + name)
            with open(os.path.join(HERE, name), "wb") as f:
                f.write(body)
            manifest["files"][folder + "/" + name] = hashlib.sha256(body).hexdigest()
            print("%s/%s %d bytes sha256 %s" % (folder, name, len(body), manifest["files"][folder + "/" + name]),
                  flush=True)
    os.chmod(os.path.join(HERE, "build.sh"), 0o755)
    lf_only(LOCAL_TEXT)
    deadline = time.time() + WAIT
    for name in PUBLISHED:
        manifest["files"]["xltw-solver/" + name] = wait_identical(S + name, os.path.join(HERE, name),
                                                                  "xltw-solver " + name, deadline)
    manifest["files"]["xltwdet2/PREREG.md"] = wait_identical(B + "main/xltwdet2/PREREG.md",
                                                             os.path.join(HERE, "PREREG.md"), "xltwdet2/PREREG.md",
                                                             deadline)
    for name in LOCAL_TEXT:
        manifest["files"]["local/" + name] = sha_file(os.path.join(HERE, name))
    with open(os.path.join(HERE, "det2-manifest.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=1)


if __name__ == "__main__":
    main()
