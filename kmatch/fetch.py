"""Setup for the kmatch pilot (network on): fetch xltwlb.py (cvrplib-baselines v0.3.7) and xltwen/results.json (the
published K* values), and make sure the XLTW-Test instances are in the data volume.

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
FILES = [(B + "v0.3.7/xltwlb/xltwlb.py", "xltwlb.py"), (B + "main/xltwen/results.json", "xltwen-results.json")]
XLTW = "https://galgos.inf.puc-rio.br/cvrplib/uploads/files/vrptw_challenge/XLTW-Test.7z"
XLTW_SHA256 = "9635b9fa813ea34ff3f35842f80a40ce6764d14c27cf2e13e5fbf1de623f4631"
UA = "kmatch pilot - MV2 of Munim, Inc. (mv2@munimtech.com)"
HERE = os.path.dirname(os.path.abspath(__file__))


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


if __name__ == "__main__":
    main()
