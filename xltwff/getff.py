"""Setup for the xltwff jobs (network on): fetch the xltw-solver package as published (cvrplib-baselines commit
19c7eb6, package 0.1.1, solver 0.1.0) and the xltwfull harness (commit 876bd94, xltwfull/fullrun.py) into this
folder, apply the one pre-registered change to solver.py (the fleet phase gets 0.8 of the time left instead of 0.5),
record every file's SHA-256, and wait until this study's pre-registration is public on `main` and byte-identical to
the local copy (prereg.md).

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.
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
PKG_COMMIT = "19c7eb668dc1e8e87d3d99ccc11186a5723eb1a9"
PKG_FILES = ["README.md", "Makefile", "build.sh", "lock.py", "solver.py", "test_pkg.py", "conformance.py",
             "fetch_helpers.py", "addendum-2026-11-06.md"]
HARNESS_COMMIT = "876bd94bcf1f8aacc6b158d220b9286bdac1a886"
HARNESS_FILES = ["fullrun.py"]
PREREG_URL = B + "main/xltwff/expectations.md"
PREREG_LOCAL = "prereg.md"
UA = "xltwff job - MV2 of Munim, Inc. (mv2@munimtech.com)"
WAIT = 50 * 60

# The one change. Each old line must occur exactly once in solver.py 0.1.0.
PATCHES = [
    (b"FLEET_FRAC = 0.5\n", b"FLEET_FRAC = 0.8  # xltwff: 0.5 in xltw-solver 0.1.0\n"),
    (b'VERSION = "0.1.0"\n', b'VERSION = "0.1.0+ff08"\n'),
]


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


def patch_source(body, patches=PATCHES):
    """Apply each (old, new) line replacement; every old line must occur exactly once. Returns the new bytes."""
    for old, new in patches:
        n = body.count(old)
        if n != 1:
            raise ValueError("expected exactly one %r in solver.py, found %d" % (old, n))
        body = body.replace(old, new)
    return body


def fetch(dest=HERE, getter=get):
    manifest = {"package_commit": PKG_COMMIT, "harness_commit": HARNESS_COMMIT, "files": {}, "patched": False}
    for prefix, commit, names in (("xltwpkg/", PKG_COMMIT, PKG_FILES), ("xltwfull/", HARNESS_COMMIT, HARNESS_FILES)):
        for name in names:
            body = getter(B + commit + "/" + prefix + name)
            manifest["files"][name] = hashlib.sha256(body).hexdigest()
            if name == "solver.py":
                patched = patch_source(body)
                manifest["solver_py_patched_sha256"] = hashlib.sha256(patched).hexdigest()
                manifest["patched"] = True
                body = patched
            with open(os.path.join(dest, name), "wb") as f:
                f.write(body)
            print("%s%s %d bytes sha256 %s" % (prefix, name, len(body), manifest["files"][name]), flush=True)
    os.chmod(os.path.join(dest, "build.sh"), 0o755)
    with open(os.path.join(dest, "pkg-manifest.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=1)
    return manifest


def wait_prereg(local_path, getter=get, deadline=None, sleep=time.sleep):
    with open(local_path, "rb") as f:
        local = norm(f.read())
    deadline = deadline if deadline is not None else time.time() + WAIT
    while True:
        try:
            body = norm(getter(PREREG_URL + "?nocache=%d" % int(time.time()), tries=1))
            if body == local:
                print("pre-registration public and identical, sha256 %s" % hashlib.sha256(local).hexdigest(),
                      flush=True)
                return hashlib.sha256(local).hexdigest()
            print("expectations.md on main differs from prereg.md; waiting", flush=True)
        except (urllib.error.URLError, OSError) as e:
            print("waiting for expectations.md (%s)" % e, flush=True)
        if time.time() > deadline:
            sys.exit("the pre-registration never became public as expected: not running")
        sleep(60)


def main():
    fetch()
    wait_prereg(os.path.join(HERE, PREREG_LOCAL))


if __name__ == "__main__":
    main()
