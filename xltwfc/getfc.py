"""Setup for the xltwfc jobs (network on): fetch the xltw-solver package as published (cvrplib-baselines commit
19c7eb6, package 0.1.1, solver 0.1.0) and the xltwfull harness (commit 876bd94, xltwfull/fullrun.py) into this
folder, record every file's SHA-256, fetch this study's pre-registration as committed in d19acfd (prereg.md), and
wait until `main` still carries it unchanged and also carries the addendum (fc-addendum.md, published as
xltwfc/addendum-2026-11-07.md) byte-identical to the local copy.

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
PREREG_COMMIT = "d19acfdf0e60f6ad326c267f1b213bcd74982483"  # the commit that pre-registered xltwfc
PUBLIC = [(B + "main/xltwfc/expectations.md", "prereg.md"),
          (B + "main/xltwfc/addendum-2026-11-07.md", "fc-addendum.md")]
UA = "xltwfc job - MV2 of Munim, Inc. (mv2@munimtech.com)"
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
    manifest = {"package_commit": PKG_COMMIT, "harness_commit": FULL_COMMIT, "files": {}}
    for commit, folder, names in ((PKG_COMMIT, "xltwpkg", PKG_FILES), (FULL_COMMIT, "xltwfull", FULL_FILES)):
        for name in names:
            body = getter(B + commit + "/" + folder + "/" + name)
            with open(os.path.join(dest, name), "wb") as f:
                f.write(body)
            manifest["files"][folder + "/" + name] = hashlib.sha256(body).hexdigest()
            print("%s/%s %d bytes sha256 %s" % (folder, name, len(body), manifest["files"][folder + "/" + name]),
                  flush=True)
    os.chmod(os.path.join(dest, "build.sh"), 0o755)
    with open(os.path.join(dest, "fc-manifest.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=1)
    return manifest


def wait_public(url, local_path, getter=get, deadline=None, sleep=time.sleep):
    with open(local_path, "rb") as f:
        local = norm(f.read())
    deadline = deadline if deadline is not None else time.time() + WAIT
    while True:
        try:
            body = norm(getter(url + "?nocache=%d" % int(time.time()), tries=1))
            if body == local:
                print("%s public and identical, sha256 %s" % (url, hashlib.sha256(local).hexdigest()), flush=True)
                return hashlib.sha256(local).hexdigest()
            print("%s differs from %s; waiting" % (url, os.path.basename(local_path)), flush=True)
        except (urllib.error.URLError, OSError) as e:
            print("waiting for %s (%s)" % (url, e), flush=True)
        if time.time() > deadline:
            sys.exit("%s never became public as expected: not running" % url)
        sleep(60)


def main():
    fetch()
    # prereg.md is the pre-registration exactly as committed in PREREG_COMMIT; main must still carry it unchanged.
    body = get(B + PREREG_COMMIT + "/xltwfc/expectations.md")
    with open(os.path.join(HERE, "prereg.md"), "wb") as f:
        f.write(body)
    print("pre-registration at %s: sha256 %s" % (PREREG_COMMIT[:7], hashlib.sha256(norm(body)).hexdigest()),
          flush=True)
    deadline = time.time() + WAIT
    for url, local in PUBLIC:
        wait_public(url, os.path.join(HERE, local), deadline=deadline)


if __name__ == "__main__":
    main()
