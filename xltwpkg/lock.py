"""Pinned third-party wheels for xltw-solver: resolve them on PyPI, fetch them, check them, unpack them.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.
Standard library only, so the build needs neither pip nor a venv.

  python lock.py --resolve                       write wheels.lock from PyPI's JSON API (needs Internet)
  python lock.py --fetch                         download every wheel in wheels.lock into vendor/wheels/
  python lock.py --install --tag cp312 --dest lib [--offline]
                                                 unpack the wheels for one CPython version into lib/

Every wheel is checked against the sha256 that PyPI publishes for it before it is used. --offline never touches the
network: a wheel missing from vendor/wheels/ is an error. matplotlib (a dependency of PyVRP that is used only for
plotting) is left out on purpose; the solver never imports it.

0.1.1: lib/XLTW_BUILD.json also records the interpreter that ran the install ("executable"), so tests and the
conformance check use the same one; downloads are retried up to three times.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PINS = [("pyvrp", "0.14.1"), ("numpy", "2.3.4"), ("vrplib", "2.2.0"), ("tqdm", "4.67.1")]
TAGS = ("cp311", "cp312", "cp313")
LOCK = os.path.join(HERE, "wheels.lock")
VENDOR = os.path.join(HERE, "vendor", "wheels")
UA = "xltw-solver build - MV2 of Munim, Inc. (mv2@munimtech.com)"


class LockError(Exception):
    pass


def pick(name, version, files, tags=TAGS):
    """files: the 'urls' list of PyPI's JSON for one release. Returns wheel records: the py3-none-any wheel if there
    is one, else one manylinux x86_64 wheel per CPython tag (free-threaded and musllinux builds excluded)."""
    wheels = [f for f in files if f.get("packagetype") == "bdist_wheel" and not f.get("yanked")]
    rec = lambda tag, f: {"name": name, "version": version, "tag": tag, "filename": f["filename"],  # noqa: E731
                          "sha256": f["digests"]["sha256"], "url": f["url"]}
    pure = sorted((f for f in wheels if f["filename"].endswith("-py3-none-any.whl")), key=lambda f: f["filename"])
    if pure:
        return [rec("any", pure[0])]
    out = []
    for tag in tags:
        cands = sorted((f for f in wheels if "-%s-%s-" % (tag, tag) in f["filename"]
                        and "manylinux" in f["filename"] and f["filename"].endswith("x86_64.whl")),
                       key=lambda f: f["filename"])
        if not cands:
            raise LockError("no manylinux x86_64 wheel of %s %s for %s" % (name, version, tag))
        out.append(rec(tag, cands[0]))
    return out


def get(url, timeout=120, tries=3, wait=20.0):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except (urllib.error.URLError, OSError):
            if i == tries - 1:
                raise
            time.sleep(wait)
    raise AssertionError("unreachable")


def resolve(lock=LOCK):
    wheels = []
    for name, version in PINS:
        meta = json.loads(get("https://pypi.org/pypi/%s/%s/json" % (name, version)).decode("utf-8"))
        wheels += pick(name, version, meta["urls"])
    doc = {"note": "Wheels for xltw-solver, from https://pypi.org/pypi/<name>/<version>/json; sha256 as PyPI "
                   "publishes it. Written by lock.py --resolve.",
           "pins": [{"name": n, "version": v} for n, v in PINS], "wheels": wheels}
    with open(lock, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, indent=1)
        f.write("\n")
    return doc


def load(lock=LOCK):
    if not os.path.exists(lock):
        raise LockError("%s is missing: run `python lock.py --resolve` with Internet access" % lock)
    with open(lock, encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_one(w, offline, vendor=VENDOR, getter=get):
    """Path of the checked wheel in `vendor`, downloading it first unless offline."""
    path = os.path.join(vendor, w["filename"])
    if os.path.exists(path):
        got = sha256_file(path)
        if got != w["sha256"]:
            raise LockError("%s has sha256 %s, expected %s" % (path, got, w["sha256"]))
        return path
    if offline:
        raise LockError("%s is not in %s and --offline forbids downloading it" % (w["filename"], vendor))
    os.makedirs(vendor, exist_ok=True)
    body = getter(w["url"])
    got = hashlib.sha256(body).hexdigest()
    if got != w["sha256"]:
        raise LockError("download of %s has sha256 %s, expected %s" % (w["filename"], got, w["sha256"]))
    with open(path + ".part", "wb") as f:
        f.write(body)
    os.replace(path + ".part", path)
    return path


def safe_extract(wheel, dest):
    """Unzip a wheel into dest, refusing members that would land outside it; keeps the Unix permission bits."""
    root = os.path.realpath(dest)
    with zipfile.ZipFile(wheel) as z:
        for info in z.infolist():
            target = os.path.realpath(os.path.join(root, info.filename))
            if target != root and not target.startswith(root + os.sep):
                raise LockError("%s: member %r would land outside %s" % (wheel, info.filename, dest))
            z.extract(info, root)
            mode = (info.external_attr >> 16) & 0o777
            if mode and not info.is_dir():
                os.chmod(target, mode)


def select(doc, tag):
    """The wheels for one CPython tag: exactly one per pin."""
    if tag not in TAGS:
        raise LockError("Python tag %s is not supported (need one of %s)" % (tag, ", ".join(TAGS)))
    chosen = [w for w in doc["wheels"] if w["tag"] in (tag, "any")]
    for p in doc["pins"]:
        k = sum(1 for w in chosen if w["name"] == p["name"])
        if k != 1:
            raise LockError("%d wheels of %s for %s in the lock (expected 1)" % (k, p["name"], tag))
    return chosen


def install(tag, dest, offline, lock=LOCK, vendor=VENDOR):
    doc = load(lock)
    chosen = select(doc, tag)
    running = "cp%d%d" % sys.version_info[:2]
    if tag != running:
        raise LockError("--tag %s does not match the interpreter running the install (%s, %s); run lock.py with "
                        "the Python the solver will use" % (tag, running, sys.executable))
    paths = [fetch_one(w, offline, vendor) for w in chosen]
    dest = os.path.abspath(dest)
    if os.path.commonpath([dest, HERE]) != HERE or dest == HERE:
        raise LockError("refusing to install outside the package folder: %s" % dest)
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    for p in paths:
        safe_extract(p, dest)
    info = {"tag": tag, "python": sys.version.split()[0], "executable": sys.executable, "offline": offline,
            "wheels": [{k: w[k] for k in ("name", "version", "filename", "sha256")} for w in chosen]}
    with open(os.path.join(dest, "XLTW_BUILD.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(info, f, indent=1)
    return info


def build_python(here=HERE):
    """The interpreter recorded by the last build (lib/XLTW_BUILD.json), or None if there is no build."""
    try:
        with open(os.path.join(here, "lib", "XLTW_BUILD.json"), encoding="utf-8") as f:
            return json.load(f).get("executable")
    except (OSError, ValueError):
        return None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--resolve", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--tag", default="cp%d%d" % sys.version_info[:2])
    ap.add_argument("--dest", default=os.path.join(HERE, "lib"))
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.resolve:
            doc = resolve()
            print("wheels.lock: %d wheels" % len(doc["wheels"]))
        if a.fetch:
            for w in load()["wheels"]:
                print("%s ok" % os.path.basename(fetch_one(w, a.offline)))
        if a.install:
            info = install(a.tag, a.dest, a.offline)
            print("installed %s for %s into %s" % (", ".join("%s %s" % (w["name"], w["version"])
                                                            for w in info["wheels"]), a.tag, a.dest))
    except LockError as e:
        sys.stderr.write("lock.py: %s\n" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
