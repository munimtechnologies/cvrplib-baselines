"""Setup for the nbrm job (network on): fetch the two checking modules of cvrplib-baselines v0.3.7, make sure the
XLTW-Test instances are in the data volume, clone Astronomax's route minimiser at commit 89d4c05 (MIT), apply the
one pre-registered change (nearest-integer arc lengths), build it, and wait until this study's pre-registration is
public on `main` and byte-identical to the local prereg.md.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.
"""
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
B = "https://raw.githubusercontent.com/munimtechnologies/cvrplib-baselines/"
HELPERS = [(B + "v0.3.7/xltwbase/xltwbase.py", "xltwbase.py"), (B + "v0.3.7/xltwlb/xltwlb.py", "xltwlb.py")]
PREREG_URL = B + "main/nbrm/expectations.md"
PREREG_LOCAL = "prereg.md"
NB_REPO = "https://github.com/Astronomax/vrptw-powerful-route-minimization-heuristic.git"
NB_COMMIT = "89d4c05"
XLTW = "https://galgos.inf.puc-rio.br/cvrplib/uploads/files/vrptw_challenge/XLTW-Test.7z"
XLTW_SHA256 = "9635b9fa813ea34ff3f35842f80a40ce6764d14c27cf2e13e5fbf1de623f4631"
UA = "nbrm job - MV2 of Munim, Inc. (mv2@munimtech.com)"
WAIT = 50 * 60
PATCH_RE = re.compile(r"sqrt\(\s*dx\s*\*\s*dx\s*\+\s*dy\s*\*\s*dy\s*\)")
PATCH_TO = "floor(sqrt(dx * dx + dy * dy) + 0.5)"


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


def patch_source(text):
    """Return (patched text, number of matches). The study requires exactly one match."""
    return PATCH_RE.subn(PATCH_TO, text)


def sh(cmd, cwd=None):
    print("$ " + " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=cwd).returncode


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


def build_nb():
    info = {"repo": NB_REPO, "commit_asked": NB_COMMIT, "built": False}
    src = os.path.join(HERE, "nb")
    if os.path.exists(src):
        shutil.rmtree(src)
    if sh(["git", "clone", "--quiet", NB_REPO, src]) or sh(["git", "checkout", "--quiet", NB_COMMIT], cwd=src) \
            or sh(["git", "submodule", "update", "--init", "--recursive", "--quiet"], cwd=src):
        info["error"] = "clone/checkout failed"
        return info
    info["commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=src, text=True).strip()
    info["submodules"] = subprocess.check_output(["git", "submodule", "status", "--recursive"], cwd=src,
                                                 text=True).strip()
    pc = os.path.join(src, "src", "problem.c")
    with open(pc, encoding="utf-8") as f:
        text = f.read()
    new, k = patch_source(text)
    info["patch_matches"] = k
    if k != 1:
        info["error"] = "patch matched %d times" % k
        return info
    with open(pc, "w", encoding="utf-8", newline="\n") as f:
        f.write(new)
    info["problem_c_sha256_patched"] = hashlib.sha256(new.encode("utf-8")).hexdigest()
    for flags in (["-DENABLE_MARCH_NATIVE=OFF"], []):
        bdir = os.path.join(src, "build")
        if os.path.exists(bdir):
            shutil.rmtree(bdir)
        if sh(["cmake", "-S", src, "-B", bdir, "-DCMAKE_BUILD_TYPE=Release"] + flags) == 0 and \
                sh(["cmake", "--build", bdir, "--target", "routes", "-j", "2"]) == 0:
            hits = [p for p in glob.glob(os.path.join(bdir, "**", "routes"), recursive=True)
                    if os.path.isfile(p) and os.access(p, os.X_OK)]
            if hits:
                shutil.copy2(hits[0], os.path.join(HERE, "routes"))
                info.update({"built": True, "flags": ["-DCMAKE_BUILD_TYPE=Release"] + flags})
                with open(os.path.join(HERE, "routes"), "rb") as f:
                    info["binary_sha256"] = hashlib.sha256(f.read()).hexdigest()
                break
        print("build with %s failed" % (flags or "default flags"), flush=True)
    return info


def wait_prereg(local_path, getter=get, deadline=None, sleep=time.sleep):
    with open(local_path, "rb") as f:
        local = norm(f.read())
    deadline = deadline if deadline is not None else time.time() + WAIT
    while True:
        try:
            body = norm(getter(PREREG_URL + "?nocache=%d" % int(time.time()), tries=1))
            if body == local:
                h = hashlib.sha256(local).hexdigest()
                print("pre-registration public and identical, sha256 %s" % h, flush=True)
                return h
            print("nbrm/expectations.md on main differs from prereg.md; waiting", flush=True)
        except (urllib.error.URLError, OSError) as e:
            print("waiting for nbrm/expectations.md (%s)" % e, flush=True)
        if time.time() > deadline:
            sys.exit("the pre-registration never became public as expected: not running")
        sleep(60)


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "/data"
    for url, name in HELPERS:
        body = get(url)
        with open(os.path.join(HERE, name), "wb") as f:
            f.write(body)
        print("%s %d bytes sha256 %s" % (name, len(body), hashlib.sha256(body).hexdigest()), flush=True)
    ensure_data(data_dir)
    info = build_nb()
    info["prereg_sha256"] = wait_prereg(os.path.join(HERE, PREREG_LOCAL))
    with open(os.path.join(HERE, "nb-build.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(info, f, indent=1)
    print(json.dumps(info), flush=True)
    if not info.get("built"):
        sys.exit("route minimiser not built: %s" % info.get("error"))


if __name__ == "__main__":
    main()
