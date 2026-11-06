"""Setup for the xltwpkg conformance job (network on): fetch the solver's two helper modules at the pinned tag, make
sure the pre-registration (expectations.md) is public and identical to the local copy, and make sure the XLTW-Test
instances are in the data volume.

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

HERE = os.path.dirname(os.path.abspath(__file__))
B = "https://raw.githubusercontent.com/munimtechnologies/cvrplib-baselines/"
HELPERS = [(B + "v0.3.7/xltwbase/xltwbase.py", "xltwbase.py"), (B + "v0.3.7/xltwlb/xltwlb.py", "xltwlb.py")]
PREREG = B + "main/xltwpkg/expectations.md"
XLTW = "https://galgos.inf.puc-rio.br/cvrplib/uploads/files/vrptw_challenge/XLTW-Test.7z"
XLTW_SHA256 = "9635b9fa813ea34ff3f35842f80a40ce6764d14c27cf2e13e5fbf1de623f4631"
UA = "xltwpkg job - MV2 of Munim, Inc. (mv2@munimtech.com)"
WAIT = 50 * 60


def get(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def norm(b):
    return b.replace(b"\r\n", b"\n")


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "/data"
    deadline = time.time() + WAIT
    for url, name in HELPERS:
        body = get(url)
        with open(os.path.join(HERE, name), "wb") as f:
            f.write(body)
        print("%s %d bytes sha256 %s" % (name, len(body), hashlib.sha256(body).hexdigest()), flush=True)
    with open(os.path.join(HERE, "expectations.md"), "rb") as f:
        local = norm(f.read())
    while True:
        try:
            public = norm(get(PREREG + "?nocache=%d" % int(time.time())))
            if public == local:
                print("pre-registration public and identical, sha256 %s" % hashlib.sha256(local).hexdigest(),
                      flush=True)
                break
            print("public expectations.md differs from the local copy; waiting", flush=True)
        except (urllib.error.URLError, OSError) as e:
            print("waiting for the pre-registration (%s)" % e, flush=True)
        if time.time() > deadline:
            sys.exit("the pre-registration never became public: not running")
        time.sleep(60)
    if glob.glob(os.path.join(data_dir, "xltw-test", "x-*", "**", "*.vrp"), recursive=True):
        print("XLTW-Test instances already in the data volume", flush=True)
        return
    arch = os.path.join(data_dir, "xltw-test", "XLTW-Test.7z")
    os.makedirs(os.path.dirname(arch), exist_ok=True)
    if not os.path.exists(arch):
        body = get(XLTW, timeout=600)
        with open(arch, "wb") as f:
            f.write(body)
    digest = hashlib.sha256(open(arch, "rb").read()).hexdigest()
    if digest != XLTW_SHA256:
        sys.exit("XLTW-Test.7z sha256 %s, expected %s" % (digest, XLTW_SHA256))
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "py7zr"])
    import py7zr
    with py7zr.SevenZipFile(arch, mode="r") as z:
        z.extractall(path=os.path.join(data_dir, "xltw-test", "x-" + digest[:12]))
    print("extracted XLTW-Test", flush=True)


if __name__ == "__main__":
    main()
