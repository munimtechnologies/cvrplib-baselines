"""Setup for the xltwdet job, second attempt (network on): fetch the xltw-solver package as published
(cvrplib-baselines commit 19c7eb6, package 0.1.1, solver 0.1.0), the xltwfull harness (commit 876bd94) and
detrun.py as pre-registered (commit b7b7755) into this folder, record every file's SHA-256, check that the
pre-registration on `main` is byte-identical to its first published version (commit b7b7755), and wait until the
addendum is public on `main` and identical to the local addendum-2026-11-07.md.

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
FULL_COMMIT = "876bd94bcf1f8aacc6b158d220b9286bdac1a886"
FULL_FILES = ["fullrun.py", "test_fullrun.py"]
DET_COMMIT = "b7b77554c7b2581b4f00368e6db12b2f8cd97d63"
DET_FILES = ["detrun.py"]
ADDENDUM = "addendum-2026-11-07.md"
UA = "xltwdet job - MV2 of Munim, Inc. (mv2@munimtech.com)"
WAIT = 50 * 60


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


def fetch(dest=HERE, getter=get):
    manifest = {"package_commit": PKG_COMMIT, "harness_commit": FULL_COMMIT, "detrun_commit": DET_COMMIT,
                "files": {}}
    for commit, folder, names in ((PKG_COMMIT, "xltwpkg", PKG_FILES), (FULL_COMMIT, "xltwfull", FULL_FILES),
                                  (DET_COMMIT, "xltwdet", DET_FILES)):
        for name in names:
            body = getter(B + commit + "/" + folder + "/" + name)
            with open(os.path.join(dest, name), "wb") as f:
                f.write(body)
            manifest["files"][folder + "/" + name] = hashlib.sha256(body).hexdigest()
            print("%s/%s %d bytes sha256 %s" % (folder, name, len(body), manifest["files"][folder + "/" + name]),
                  flush=True)
    os.chmod(os.path.join(dest, "build.sh"), 0o755)
    with open(os.path.join(dest, "det-manifest.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=1)
    return manifest


def prereg_unchanged(getter=get):
    first = norm(getter(B + DET_COMMIT + "/xltwdet/expectations.md"))
    now = norm(getter(B + "main/xltwdet/expectations.md?nocache=%d" % int(time.time())))
    if first != now:
        sys.exit("xltwdet/expectations.md on main differs from its pre-registered version: not running")
    h = hashlib.sha256(first).hexdigest()
    print("pre-registration unchanged since %s, sha256 %s" % (DET_COMMIT[:7], h), flush=True)
    return h


def wait_addendum(local_path, getter=get, deadline=None, sleep=time.sleep):
    with open(local_path, "rb") as f:
        local = norm(f.read())
    deadline = deadline if deadline is not None else time.time() + WAIT
    while True:
        try:
            body = norm(getter(B + "main/xltwdet/" + ADDENDUM + "?nocache=%d" % int(time.time()), tries=1))
            if body == local:
                print("addendum public and identical, sha256 %s" % hashlib.sha256(local).hexdigest(), flush=True)
                return hashlib.sha256(local).hexdigest()
            print("xltwdet/%s on main differs from the local copy; waiting" % ADDENDUM, flush=True)
        except (urllib.error.URLError, OSError) as e:
            print("waiting for xltwdet/%s (%s)" % (ADDENDUM, e), flush=True)
        if time.time() > deadline:
            sys.exit("the addendum never became public as expected: not running")
        sleep(60)


def main():
    fetch()
    prereg_unchanged()
    wait_addendum(os.path.join(HERE, ADDENDUM))


if __name__ == "__main__":
    main()
