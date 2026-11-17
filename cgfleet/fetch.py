"""Setup for the cgfleet study (network on): fetch tmatch.py (instance arrays and the starting routes; cvrplib-baselines
main/tmatch/), xltwlb.py (cvrplib-baselines v0.3.7, the parser kmatch/ and tmatch/ use) and xltwen/results.json (K*
and the PyVRP part-a fleets), make sure the XLTW-Test instances are in the data volume, and wait until
cgfleet/PREREG.md is public on `main` and identical to the local copy.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.
"""
import glob
import hashlib
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

B = "https://raw.githubusercontent.com/munimtechnologies/cvrplib-baselines/"
FILES = [(B + "main/tmatch/tmatch.py", "tmatch.py"), (B + "v0.3.7/xltwlb/xltwlb.py", "xltwlb.py"),
         (B + "main/xltwen/results.json", "xltwen-results.json")]
XLTW = "https://galgos.inf.puc-rio.br/cvrplib/uploads/files/vrptw_challenge/XLTW-Test.7z"
XLTW_SHA256 = "9635b9fa813ea34ff3f35842f80a40ce6764d14c27cf2e13e5fbf1de623f4631"
UA = "cgfleet study - MV2 of Munim, Inc. (mv2@munimtech.com)"
HERE = os.path.dirname(os.path.abspath(__file__))
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


def ensure_data(data_dir):
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
        sys.exit("XLTW-Test.7z sha256 %s, expected %s" % (digest, XLTW_SHA256))
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "py7zr"])
    import py7zr
    with py7zr.SevenZipFile(arch, mode="r") as z:
        z.extractall(path=os.path.join(data_dir, "xltw-test", "x-" + digest[:12]))
    print("extracted XLTW-Test", flush=True)


def wait_prereg(local_path, getter=get, deadline=None, sleep=time.sleep):
    with open(local_path, "rb") as f:
        local = norm(f.read())
    deadline = deadline if deadline is not None else time.time() + WAIT
    while True:
        try:
            body = norm(getter(B + "main/cgfleet/PREREG.md?nocache=%d" % int(time.time()), tries=1))
            if body == local:
                h = hashlib.sha256(local).hexdigest()
                print("PREREG.md public on main and identical, sha256 %s" % h, flush=True)
                return h
            print("cgfleet/PREREG.md on main differs from the local copy; waiting", flush=True)
        except (urllib.error.URLError, OSError) as e:
            print("waiting for cgfleet/PREREG.md (%s)" % e, flush=True)
        if time.time() > deadline:
            sys.exit("cgfleet/PREREG.md never became public as expected: not running")
        sleep(60)


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "/data"
    for url, name in FILES:
        body = get(url)
        with open(os.path.join(HERE, name), "wb") as f:
            f.write(body)
        print("%s %d bytes sha256 %s" % (name, len(body), hashlib.sha256(body).hexdigest()), flush=True)
    ensure_data(data_dir)
    n = len(glob.glob(os.path.join(data_dir, "xltw-test", "x-*", "**", "*.vrp"), recursive=True))
    print("instance files: %d" % n, flush=True)
    wait_prereg(os.path.join(HERE, "PREREG.md"))


if __name__ == "__main__":
    main()
