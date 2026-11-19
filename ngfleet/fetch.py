"""Setup for the ngfleet XTW probe (network on).

1. Fetch the code it reuses from cvrplib-baselines (cgfleet + its tests, tmatch, xtwfleet from `main`; the instance
   parser xltwlb.py from v0.3.7), with sha256 in manifest.json.
2. CVRPLib's XTW instance set (set 24) once into the data volume (shared with xtwfleet, same layout), and the CURRENT
   best known solutions fresh on every run, each with sha256 and UTC download time.
3. Wait until ngfleet/PREREG.md is public on `main` and identical to the local copy.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.
"""
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

B = "https://raw.githubusercontent.com/munimtechnologies/cvrplib-baselines/"
FILES = [(B + "main/cgfleet/cgfleet.py", "cgfleet.py"), (B + "main/cgfleet/test_cgfleet.py", "test_cgfleet.py"),
         (B + "main/tmatch/tmatch.py", "tmatch.py"), (B + "main/xtwfleet/xtwfleet.py", "xtwfleet.py"),
         (B + "v0.3.7/xltwlb/xltwlb.py", "xltwlb.py")]
SITE = "https://galgos.inf.puc-rio.br/cvrplib/index.php/en/"
SET_URL = SITE + "download/instance-set/24"
BKS_URL = SITE + "download/instance-set-bks/24"
UA = "ngfleet study - MV2 of Munim, Inc. (mv2@munimtech.com)"
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


def sha(b):
    return hashlib.sha256(b).hexdigest()


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def extract(arch, dest):
    with open(arch, "rb") as f:
        head = f.read(8)
    os.makedirs(dest, exist_ok=True)
    if head.startswith(b"7z\xbc\xaf\x27\x1c"):
        try:
            import py7zr  # noqa: F401
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "py7zr"])
        import py7zr
        with py7zr.SevenZipFile(arch, mode="r") as z:
            z.extractall(path=dest)
        return "7z"
    if head.startswith(b"PK"):
        shutil.unpack_archive(arch, dest, "zip")
        return "zip"
    try:
        shutil.unpack_archive(arch, dest, "gztar" if head.startswith(b"\x1f\x8b") else "tar")
        return "tar"
    except (shutil.ReadError, ValueError) as e:
        raise ValueError("unknown archive format %r: %s" % (head, e))


def fetch_archive(url, folder, prefix, reuse):
    os.makedirs(folder, exist_ok=True)
    if reuse:
        old = sorted(glob.glob(os.path.join(folder, prefix + "-*.json")))
        if old:
            with open(old[-1]) as f:
                ent = json.load(f)
            if os.path.isdir(ent["dir"]):
                print("%s already in the data volume (%s)" % (prefix, ent["sha256"][:12]), flush=True)
                return ent
    body = get(url, timeout=600)
    h = sha(body)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    arch = os.path.join(folder, "%s-%s-%s.bin" % (prefix, stamp, h[:12]))
    with open(arch, "wb") as f:
        f.write(body)
    dest = os.path.join(folder, "%s-%s-%s" % (prefix, stamp, h[:12]))
    fmt = extract(arch, dest)
    ent = {"url": url, "sha256": h, "bytes": len(body), "format": fmt, "downloaded_utc": utc(), "dir": dest}
    with open(os.path.join(folder, "%s-%s.json" % (prefix, stamp)), "w") as f:
        json.dump(ent, f)
    print("%s: %d bytes, %s, sha256 %s" % (prefix, len(body), fmt, h), flush=True)
    return ent


def wait_prereg(local_path, deadline=None):
    with open(local_path, "rb") as f:
        local = norm(f.read())
    deadline = deadline if deadline is not None else time.time() + WAIT
    while True:
        try:
            body = norm(get(B + "main/ngfleet/PREREG.md?nocache=%d" % int(time.time()), tries=1))
            if body == local:
                h = sha(local)
                print("PREREG.md public on main and identical, sha256 %s" % h, flush=True)
                return h
            print("ngfleet/PREREG.md on main differs from the local copy; waiting", flush=True)
        except (urllib.error.URLError, OSError) as e:
            print("waiting for ngfleet/PREREG.md (%s)" % e, flush=True)
        if time.time() > deadline:
            sys.exit("ngfleet/PREREG.md never became public as expected: not running")
        time.sleep(60)


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "/data"
    man = {"code": {}}
    for url, name in FILES:
        body = get(url)
        with open(os.path.join(HERE, name), "wb") as f:
            f.write(body)
        man["code"][name] = {"url": url, "sha256": sha(body), "bytes": len(body)}
        print("%s %d bytes sha256 %s" % (name, len(body), sha(body)), flush=True)
    root = os.path.join(data_dir, "xtw")
    man["instances"] = fetch_archive(SET_URL, os.path.join(root, "inst"), "xtw-set", reuse=True)
    man["bks"] = fetch_archive(BKS_URL, os.path.join(root, "bks"), "xtw-bks", reuse=False)
    man["prereg_sha256"] = wait_prereg(os.path.join(HERE, "PREREG.md"))
    with open(os.path.join(HERE, "manifest.json"), "w") as f:
        json.dump(man, f, indent=1)
    print("manifest written", flush=True)


if __name__ == "__main__":
    main()
