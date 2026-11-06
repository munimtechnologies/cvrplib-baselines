"""Setup for the xltwpkg conformance jobs (network on): fetch the solver's two helper modules at the pinned tag, make
sure the pre-registration (expectations.md, unchanged since 2026-11-06 05:00 UTC) and its addendum are public on
`main`, and make sure the XLTW-Test instances are in the data volume.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

0.1.1: expectations.md is fetched from `main` and must have the SHA-256 recorded by the v1 jobs (so it cannot have
changed); addendum-2026-11-06.md must be public and identical to the local copy; every download is retried.
"""
import glob
import hashlib
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
B = "https://raw.githubusercontent.com/munimtechnologies/cvrplib-baselines/"
HELPERS = [(B + "v0.3.7/xltwbase/xltwbase.py", "xltwbase.py"), (B + "v0.3.7/xltwlb/xltwlb.py", "xltwlb.py")]
PREREG = B + "main/xltwpkg/expectations.md"
PREREG_SHA256 = "296c734b2742ac53061de997b51cad02f0d83acc3df13bed8a910c06bd3a217a"  # as published 2026-11-06
ADDENDUM = "addendum-2026-11-06.md"
XLTW = "https://galgos.inf.puc-rio.br/cvrplib/uploads/files/vrptw_challenge/XLTW-Test.7z"
XLTW_SHA256 = "9635b9fa813ea34ff3f35842f80a40ce6764d14c27cf2e13e5fbf1de623f4631"
UA = "xltwpkg job - MV2 of Munim, Inc. (mv2@munimtech.com)"
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


def wait_public(url, ok, what, deadline):
    """Poll `url` until ok(body) is true; exit if the deadline passes. Returns the body."""
    while True:
        try:
            body = norm(get(url + "?nocache=%d" % int(time.time()), tries=1))
            if ok(body):
                return body
            print("%s on main is not the expected file yet; waiting" % what, flush=True)
        except (urllib.error.URLError, OSError) as e:
            print("waiting for %s (%s)" % (what, e), flush=True)
        if time.time() > deadline:
            sys.exit("%s never became public as expected: not running" % what)
        time.sleep(60)


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "/data"
    deadline = time.time() + WAIT
    for url, name in HELPERS:
        body = get(url)
        with open(os.path.join(HERE, name), "wb") as f:
            f.write(body)
        print("%s %d bytes sha256 %s" % (name, len(body), hashlib.sha256(body).hexdigest()), flush=True)
    pre = wait_public(PREREG, lambda b: hashlib.sha256(b).hexdigest() == PREREG_SHA256, "expectations.md", deadline)
    with open(os.path.join(HERE, "expectations.md"), "wb") as f:
        f.write(pre)
    print("pre-registration public and unchanged, sha256 %s" % PREREG_SHA256, flush=True)
    with open(os.path.join(HERE, ADDENDUM), "rb") as f:
        local = norm(f.read())
    wait_public(B + "main/xltwpkg/" + ADDENDUM, lambda b: b == local, ADDENDUM, deadline)
    print("addendum public and identical, sha256 %s" % hashlib.sha256(local).hexdigest(), flush=True)
    if glob.glob(os.path.join(data_dir, "xltw-test", "x-*", "**", "*.vrp"), recursive=True):
        print("XLTW-Test instances already in the data volume", flush=True)
        return
    arch = os.path.join(data_dir, "xltw-test", "XLTW-Test.7z")
    os.makedirs(os.path.dirname(arch), exist_ok=True)
    if not os.path.exists(arch):
        body = get(XLTW, timeout=600)
        with open(arch + ".part", "wb") as f:
            f.write(body)
        os.replace(arch + ".part", arch)
    with open(arch, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    if digest != XLTW_SHA256:
        os.remove(arch)
        sys.exit("XLTW-Test.7z sha256 %s, expected %s (removed; re-run to download again)" % (digest, XLTW_SHA256))
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "py7zr"])
    import py7zr
    with py7zr.SevenZipFile(arch, mode="r") as z:
        z.extractall(path=os.path.join(data_dir, "xltw-test", "x-" + digest[:12]))
    print("extracted XLTW-Test", flush=True)


if __name__ == "__main__":
    main()
