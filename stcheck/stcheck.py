"""stcheck: an independent re-check of the stfleet (mstfleet 0.2) fleet lower-bound certificates on XLTW-Test.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

Why. stfleet 0.2.0 (../stfleet/) published 33 fleet lower bounds for the capacity-free XLTW-Test instances, each with
a certificate {t1, t2, side, mu, lam, K}, and re-checked them with its own verify(). A bound that is wrong by one
vehicle would be worse than no bound, so this script re-checks every certificate WITHOUT sharing any code with
stfleet.py, mstfleet.py or xltwlb.py. It was written from the statement of the bound only (stfleet/PREREG.md and the
certificate's "rule"):

  * its own VRPLIB parser, which refuses any non-integral number;
  * exact integer travel times: round(d) = (isqrt(4 D) + 1) // 2 with D = dx^2 + dy^2 (no floating point; for integer
    D a distance is never within 1e-9 of a half-integer below 1.25e8, so this equals every rounding convention used);
  * windows tightened by the depot's hours: e_i = max(a_i, a_0 + s_0 + t_0i), l_i = min(b_i, b_0 - s_i - t_0i);
  * S = customers with e_i >= t1 and f_i = l_i + s_i <= t2;
  * its own Prim from the root over S + root with weights
      customer-customer  min over the feasible orders (i -> j feasible iff e_i + s_i + t_ij <= l_j) of
                         max(t_ij, e_j - f_i), plus lam_i + lam_j;
      root-customer      side start: (e_i - t1) + min_j (t2 - f_j) - L + mu + lam_i
                         side end:   (t2 - f_i) + min_j (e_j - t1) - L + mu + lam_i;
  * N = MST - 2 sum lam + total service of S, and fleet >= K is confirmed iff K <= 1 or (K - 1) * mu < N.

The tests (test_stcheck.py) check the travel step against exact arithmetic, the Prim against brute-force Kruskal, and
the whole bound against the exact minimum fleet (subset dynamic programming) on random tiny instances, for many
intervals, both sides, many mu and random lam: an independent check of the theorem, not only of the arithmetic.

  python stcheck.py --data-dir /data --out-dir /out
"""
import argparse
import glob
import hashlib
import json
import math
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation

import numpy as np

VERSION = "0.1.0"
RAW = "https://raw.githubusercontent.com/munimtechnologies/cvrplib-baselines/main/stfleet/"
XLTW = "https://galgos.inf.puc-rio.br/cvrplib/uploads/files/vrptw_challenge/XLTW-Test.7z"
XLTW_SHA256 = "9635b9fa813ea34ff3f35842f80a40ce6764d14c27cf2e13e5fbf1de623f4631"
UA = "stcheck study - MV2 of Munim, Inc. (mv2@munimtech.com)"
INF = 1 << 60
WAIT_S = 150 * 60
T0 = time.time()


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


# ---------------------------------------------------------------- parsing (exact integers only)

def as_int(tok):
    d = Decimal(str(tok))
    if not d.is_finite() or d != d.to_integral_value():
        raise ValueError("non-integral value %r" % (tok,))
    return int(d)


def is_num(tok):
    try:
        return Decimal(tok).is_finite()
    except (InvalidOperation, ValueError):
        return False


SECS = ("NODE_COORD_SECTION", "DEMAND_SECTION", "TIME_WINDOW_SECTION", "SERVICE_TIME_SECTION")


def parse(text):
    """VRPLIB text -> {"name", "capacity", "rows"}; rows[i] = (x, y, demand, a, b, s) as ints, depot first, then the
    customers in increasing id order."""
    head, sec, depots = {}, None, []
    data = {k: {} for k in SECS}
    for line in text.splitlines():
        p = line.split()
        if not p:
            continue
        w = p[0].rstrip(":").upper()
        if w == "EOF":
            break
        if not is_num(p[0]):
            if w.endswith("_SECTION"):
                sec = w
            elif ":" in line:
                k, v = line.split(":", 1)
                head[k.strip().upper()] = v.strip()
                sec = None
            continue
        if sec == "DEPOT_SECTION":
            if as_int(p[0]) >= 0:
                depots.append(as_int(p[0]))
        elif sec in data:
            data[sec][as_int(p[0])] = p[1:]
        else:
            raise ValueError("data line outside a known section (%s)" % sec)
    coords, tw = data["NODE_COORD_SECTION"], data["TIME_WINDOW_SECTION"]
    if not coords or not tw:
        raise ValueError("needs NODE_COORD_SECTION and TIME_WINDOW_SECTION")
    if len(depots) > 1:
        raise ValueError("more than one depot")
    ids = sorted(coords)
    depot = depots[0] if depots else ids[0]
    dflt = head.get("SERVICE_TIME", "0")
    rows = []
    for i in [depot] + [i for i in ids if i != depot]:
        rows.append((as_int(coords[i][0]), as_int(coords[i][1]),
                     as_int(data["DEMAND_SECTION"].get(i, ["0"])[0]),
                     as_int(tw[i][0]), as_int(tw[i][1]),
                     as_int(data["SERVICE_TIME_SECTION"].get(i, [dflt])[0])))
    return {"name": head.get("NAME", "?"), "capacity": as_int(head.get("CAPACITY", "0")), "rows": rows}


# ---------------------------------------------------------------- exact travel

def rtravel(dx, dy):
    """Nearest-integer Euclidean distance, exactly: (isqrt(4 D) + 1) // 2, vectorised on int64 (|coords| < 2^24)."""
    dx = np.asarray(dx, dtype=np.int64)
    dy = np.asarray(dy, dtype=np.int64)
    d4 = 4 * (dx * dx + dy * dy)
    r = np.floor(np.sqrt(d4.astype(np.float64))).astype(np.int64)
    for _ in range(2):
        r = np.where(r * r > d4, r - 1, r)
    for _ in range(2):
        r = np.where((r + 1) * (r + 1) <= d4, r + 1, r)
    return (r + 1) // 2


def rtravel1(dx, dy):
    """Scalar reference with math.isqrt."""
    return (math.isqrt(4 * (dx * dx + dy * dy)) + 1) // 2


# ---------------------------------------------------------------- instance

class Inst:
    def __init__(self, rows):
        A = np.array(rows, dtype=np.int64)
        if A.ndim != 2 or A.shape[1] != 6 or len(A) < 2:
            raise ValueError("rows must be (x, y, q, a, b, s), depot first, at least one customer")
        if int(np.abs(A[:, :2]).max()) >= (1 << 24):
            raise ValueError("coordinates too large for the exact travel step")
        self.n = len(A) - 1
        self.x, self.y = A[1:, 0].copy(), A[1:, 1].copy()
        a, b, s = A[:, 3], A[:, 4], A[:, 5]
        self.s = s[1:].copy()
        if int(self.s.min()) < 1:
            raise ValueError("a service time below 1: the via-customer step needs every service >= 1")
        t0 = rtravel(self.x - A[0, 0], self.y - A[0, 1])
        self.D0 = int(a[0] + s[0])
        self.B0 = int(b[0])
        self.e = np.maximum(a[1:], self.D0 + t0)
        self.l = np.minimum(b[1:], self.B0 - self.s - t0)
        self.f = self.l + self.s
        if bool(np.any(self.e > self.l)):
            raise ValueError("a customer no route can serve")


def subset(I, t1, t2):
    return np.flatnonzero((I.e >= t1) & (I.f <= t2))


def n_value(I, S, t1, t2, side, mu, lam):
    """N = MST(S + root) - 2 sum lam + service(S), exact python int."""
    m = len(S)
    if m == 0:
        return 0
    x, y, e, l, s, f = I.x[S], I.y[S], I.e[S], I.l[S], I.s[S], I.f[S]
    lam = np.asarray(lam, dtype=np.int64)
    L = t2 - t1
    a, b = e - t1, t2 - f
    if side == "start":
        c = a + int(b.min()) - L
    elif side == "end":
        c = b + int(a.min()) - L
    else:
        raise ValueError("side must be start or end")
    es = e + s
    key = c + int(mu) + lam
    done = np.zeros(m, dtype=bool)
    total = 0
    for _ in range(m):
        u = int(np.argmin(np.where(done, INF, key)))
        total += int(key[u])
        done[u] = True
        t = rtravel(x - x[u], y - y[u])
        fwd = np.where(es[u] + t <= l, np.maximum(t, e - f[u]), INF)      # u first, then v
        bwd = np.where(es + t <= l[u], np.maximum(t, e[u] - f), INF)      # v first, then u
        w = np.minimum(fwd, bwd) + lam + lam[u]
        upd = (~done) & (w < key)
        key = np.where(upd, w, key)
    return total - 2 * int(lam.sum()) + int(s.sum())


def proves(N, mu):
    """Largest K with (K - 1) * mu < N (at least 1)."""
    return max(1, -(-int(N) // int(mu)))


def check(I, cert):
    """Re-check one certificate. Returns a dict with confirmed (bool) and the numbers."""
    out = {"confirmed": False}
    try:
        K = as_int(cert["K"])
        t1, t2 = as_int(cert["t1"]), as_int(cert["t2"])
        side = cert["side"]
        mu = cert["mu"]
        if isinstance(mu, bool) or not isinstance(mu, int) or mu < 1:
            out["why"] = "mu must be a positive integer"
            return out
        S = subset(I, t1, t2)
        m = len(S)
        lam = cert.get("lam")
        lam = np.zeros(m, dtype=np.int64) if lam is None else np.array([as_int(v) for v in lam], dtype=np.int64)
        out.update({"K": K, "t1": t1, "t2": t2, "side": side, "mu": mu, "m": m, "m_cert": cert.get("m")})
        if lam.shape != (m,) or bool(np.any(lam < 0)):
            out["why"] = "lam has the wrong length or a negative entry"
            return out
        if m == 0:
            out["why"] = "empty interval"
            out["confirmed"] = K <= 1
            return out
        N = n_value(I, S, t1, t2, side, mu, lam)
        out.update({"N": N, "proves": proves(N, mu), "confirmed": bool(K <= 1 or (K - 1) * mu < N)})
        if not out["confirmed"]:
            out["why"] = "(K - 1) * mu >= N"
        return out
    except (KeyError, ValueError, TypeError) as ex:
        out["why"] = "malformed: %s" % ex
        return out


# ---------------------------------------------------------------- job

def get(url, timeout=120, tries=4, wait=30.0):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except (urllib.error.URLError, OSError) as ex:
            if i == tries - 1:
                raise
            log("retrying %s after %s" % (url, ex))
            time.sleep(wait)
    raise AssertionError("unreachable")


def wait_results():
    deadline = time.time() + WAIT_S
    while True:
        try:
            body = get(RAW + "results.json?nocache=%d" % int(time.time()), tries=1)
            res = json.loads(body)
            if res.get("instances"):
                log("stfleet/results.json public, sha256 %s" % hashlib.sha256(body).hexdigest())
                return res, hashlib.sha256(body).hexdigest()
        except (urllib.error.URLError, OSError, ValueError) as ex:
            log("waiting for stfleet/results.json (%s)" % ex)
        if time.time() > deadline:
            sys.exit("stfleet/results.json never became public: not running")
        time.sleep(60)


def vrp_files(root):
    out = {}
    for p in glob.glob(os.path.join(root, "**", "*"), recursive=True):
        if os.path.isfile(p) and p.lower().endswith(".vrp"):
            out[os.path.splitext(os.path.basename(p))[0]] = p
    return out


def ensure_data(data_dir):
    root = os.path.join(data_dir, "xltw-test")
    if vrp_files(root):
        log("XLTW-Test instances already in the data volume")
        return root
    arch = os.path.join(root, "XLTW-Test.7z")
    os.makedirs(root, exist_ok=True)
    if not os.path.exists(arch):
        body = get(XLTW, timeout=600)
        with open(arch + ".part", "wb") as fh:
            fh.write(body)
        os.replace(arch + ".part", arch)
    with open(arch, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    if digest != XLTW_SHA256:
        os.remove(arch)
        sys.exit("XLTW-Test.7z sha256 %s, expected %s" % (digest, XLTW_SHA256))
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "py7zr"])
    import py7zr
    with py7zr.SevenZipFile(arch, mode="r") as z:
        z.extractall(path=os.path.join(root, "x-" + digest[:12]))
    return root


def tally(recs):
    ok = [r for r in recs if not r.get("error")]
    known = [r for r in ok if r.get("kstar") is not None and r.get("ub") is not None and r["confirmed"]]
    return {
        "certificates": len(recs),
        "confirmed": sum(1 for r in ok if r["confirmed"]),
        "refused": [r["instance"] for r in ok if not r["confirmed"]],
        "errors": [r["instance"] for r in recs if r.get("error")],
        "claim_mismatch": [r["instance"] for r in ok if r.get("claimed") != r.get("K")],
        "m_mismatch": [r["instance"] for r in ok if r.get("m_cert") is not None and r.get("m_cert") != r.get("m")],
        "proves_more": [r["instance"] for r in ok if r["confirmed"] and r.get("proves", 0) > r.get("K", 0)],
        "above_kstar_confirmed": [r["instance"] for r in ok if r["confirmed"] and r.get("kstar") is not None
                                  and r["K"] > r["kstar"]],
        "sum_kstar": sum(r["kstar"] for r in ok if r.get("kstar") is not None),
        "sum_max_confirmed": sum(max(r["kstar"], r["K"] if r["confirmed"] else 0) for r in ok
                                 if r.get("kstar") is not None),
        "with_known_fleet": len(known),
        "known_sum_ub": sum(r["ub"] for r in known),
        "known_sum_kstar": sum(r["kstar"] for r in known),
        "known_sum_max": sum(max(r["kstar"], r["K"]) for r in known),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    out = os.path.join(args.out_dir, "stcheck")
    os.makedirs(out, exist_ok=True)
    root = ensure_data(args.data_dir)
    files = vrp_files(root)
    log("instance files: %d" % len(files))
    st, st_sha = wait_results()
    recs = []
    for r in st["instances"]:
        name = r.get("instance")
        if r.get("error") or r.get("bound") is None:
            continue
        rec = {"instance": name, "claimed": r.get("bound"), "kstar": r.get("kstar"), "ub": r.get("ub")}
        t = time.time()
        try:
            body = get(RAW + "cert/%s.json" % name)
            rec["cert_sha256"] = hashlib.sha256(body).hexdigest()
            cert = json.loads(body)
            if name not in files:
                raise ValueError("instance file not found")
            with open(files[name], encoding="utf-8") as fh:
                I = Inst(parse(fh.read())["rows"])
            rec.update(check(I, cert))
        except Exception as ex:  # noqa: BLE001 - recorded
            rec["error"] = "%s: %s" % (type(ex).__name__, ex)
        rec["seconds"] = round(time.time() - t, 2)
        recs.append(rec)
        log(json.dumps({k: rec.get(k) for k in ("instance", "claimed", "K", "m", "N", "mu", "proves", "confirmed",
                                               "why", "error", "seconds")}))
    res = {"checker": "stcheck " + VERSION, "python": sys.version.split()[0], "numpy": np.__version__,
           "stfleet_results_sha256": st_sha, "instances": recs, "tally": tally(recs)}
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(res, fh, indent=1)
    lines = ["# stcheck: independent re-check of the stfleet certificates", "",
             "Checker %s; shares no code with stfleet.py. Tally: `%s`" % (VERSION, json.dumps(res["tally"])), "",
             "| instance | claimed | K* | known fleet | customers in interval | mu | N | proves | confirmed |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in recs:
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["instance"], r.get("claimed"), r.get("kstar"), r.get("ub"), r.get("m"), r.get("mu"), r.get("N"),
            r.get("proves"), r.get("error") or r.get("confirmed")))
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    log("TALLY " + json.dumps(res["tally"]))


if __name__ == "__main__":
    main()
