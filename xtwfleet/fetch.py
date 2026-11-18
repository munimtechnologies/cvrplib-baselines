"""Setup for the xtwfleet study (network on).

1. Fetch the bound code it reuses from cvrplib-baselines `main` (mstfleet, stfleet, cgfleet, tmatch and the tests of
   stfleet and cgfleet) and the instance parser xltwlb.py (v0.3.7). Their sha256 go into manifest.json.
2. Download CVRPLib's XTW set (instances, set 24) once into the data volume, and the CURRENT best known solutions of
   the set fresh on every run (they change daily), each with its sha256 and UTC download time.
3. Download, politely (one page every 2 s), the public bound-history page of each XTW instance (ids 736-835) and the
   VRPTW instance list (for CVRPLib's "Opt" column). Raw pages are kept; xtwfleet.py parses them.
4. Wait until xtwfleet/PREREG.md is public on `main` and identical to the local copy.

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
FILES = [(B + "main/mstfleet/mstfleet.py", "mstfleet.py"), (B + "main/stfleet/stfleet.py", "stfleet.py"),
         (B + "main/stfleet/test_stfleet.py", "test_stfleet.py"), (B + "main/cgfleet/cgfleet.py", "cgfleet.py"),
         (B + "main/cgfleet/test_cgfleet.py", "test_cgfleet.py"), (B + "main/tmatch/tmatch.py", "tmatch.py"),
         (B + "v0.3.7/xltwlb/xltwlb.py", "xltwlb.py")]
SITE = "https://galgos.inf.puc-rio.br/cvrplib/index.php/en/"
SET_URL = SITE + "download/instance-set/24"
BKS_URL = SITE + "download/instance-set-bks/24"
LIST_URL = SITE + "vrptw/instances"
IDS = list(range(736, 836))
UA = "xtwfleet study - MV2 of Munim, Inc. (mv2@munimtech.com)"
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
    """Extract a 7z, zip or tar archive (detected by its first bytes) into dest."""
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
    """Download url into folder (reusing an earlier copy if reuse) and extract it; returns a manifest entry."""
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


def fetch_pages(folder, ids=IDS, pause=2.0):
    os.makedirs(folder, exist_ok=True)
    out = {"downloaded_utc": utc(), "dir": folder, "bounds": {}, "list": None, "failed": []}
    try:
        body = get(LIST_URL, tries=3)
        p = os.path.join(folder, "vrptw-instances.html")
        with open(p, "wb") as f:
            f.write(body)
        out["list"] = p
    except (urllib.error.URLError, OSError) as e:
        out["failed"].append(["list", str(e)])
    for i in ids:
        time.sleep(pause)
        try:
            body = get(SITE + "bounds/%d" % i, tries=2, wait=10.0)
        except (urllib.error.URLError, OSError) as e:
            out["failed"].append([i, str(e)])
            continue
        p = os.path.join(folder, "bounds-%d.html" % i)
        with open(p, "wb") as f:
            f.write(body)
        out["bounds"][str(i)] = p
    print("pages: list %s, bounds %d, failed %d" % (bool(out["list"]), len(out["bounds"]), len(out["failed"])),
          flush=True)
    return out


def wait_prereg(local_path, getter=get, deadline=None, sleep=time.sleep):
    with open(local_path, "rb") as f:
        local = norm(f.read())
    deadline = deadline if deadline is not None else time.time() + WAIT
    while True:
        try:
            body = norm(getter(B + "main/xtwfleet/PREREG.md?nocache=%d" % int(time.time()), tries=1))
            if body == local:
                h = sha(local)
                print("PREREG.md public on main and identical, sha256 %s" % h, flush=True)
                return h
            print("xtwfleet/PREREG.md on main differs from the local copy; waiting", flush=True)
        except (urllib.error.URLError, OSError) as e:
            print("waiting for xtwfleet/PREREG.md (%s)" % e, flush=True)
        if time.time() > deadline:
            sys.exit("xtwfleet/PREREG.md never became public as expected: not running")
        sleep(60)


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
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    man["pages"] = fetch_pages(os.path.join(root, "pages-" + stamp))
    man["prereg_sha256"] = wait_prereg(os.path.join(HERE, "PREREG.md"))
    with open(os.path.join(HERE, "manifest.json"), "w") as f:
        json.dump(man, f, indent=1)
    print("manifest written", flush=True)


if __name__ == "__main__":
    main()
