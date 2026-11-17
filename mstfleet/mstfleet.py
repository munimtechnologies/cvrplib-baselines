"""mstfleet: interval spanning-forest lower bounds on the number of vehicles for the VRPTW (XLTW-Test).

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

Why. On the capacity-free XLTW-Test instances the fleets we can find are 1.3 to 9 times the best lower bound we have
(K*, energetic reasoning, `xltwen/`). Most of these instances have very wide time windows (kmatch/: 33-93% of ordered
customer pairs are time-compatible) and many have service time 1, so travel, not service, fills the vehicles' day.
K* charges each customer only its nearest feasible neighbour's travel time. That is the right order of magnitude
when every customer may be served next to its nearest neighbour, but not when the customers that must be served in a
given stretch of time are sparse in space.

Bound. Take any time interval [t1, t2] and let S be the customers whose whole service must fall inside it
(earliest start e_i >= t1 and latest end l_i + s_i <= t2, after the usual tightening by the depot's hours). Each vehicle
that serves customers of S visits them in some order between t1 and t2, so its time inside the interval is at least
their service plus the travel between consecutive S-customers on its route (going via other customers is never
shorter: rounded travel times satisfy t_ik + t_kj >= t_ij - 1, and every service time is at least 1, which is checked).
Those consecutive pairs form vertex-disjoint paths, one per vehicle, i.e. a spanning forest of S with at most K trees.
Hence

    K (t2 - t1)  >=  sum_{i in S} s_i  +  MSF_K(S),

where MSF_K(S) is the minimum spanning forest of S with at most K trees = the MST of S minus its K - 1 heaviest edges.
At the ends of the day the vehicles' paths are rooted at the depot ("start": t1 = depot opening, "end": t2 = depot
closing; then the forest becomes a spanning tree of S plus the depot), and over the whole day each route also has a
return edge ("full"). Every customer has degree at most 2 on these paths, so Held-Karp-style Lagrangian weights
lambda_i >= 0 (on t_ij + lambda_i + lambda_j, minus 2 sum lambda) give a stronger valid bound for any lambda; we search
lambda by subgradient steps on the most promising intervals ("hk").

All travel times used are LOWER bounds of the challenge's rounded Euclidean times (floor(d + 0.5 - 1e-9)), all window
tightening is done with them, and lambda is integral, so the forest weights are exact integers.

The ingredients are classical (energetic reasoning on time intervals, minimum spanning trees / Fisher's K-trees,
Held and Karp's Lagrangian). A search on 2026-11-17 found no fleet bound that uses the spanning forest of the
customers whose windows lie inside a time interval; that may only mean we did not find it.

  python mstfleet.py --data-dir /data --out-dir /out
"""
import argparse
import glob
import json
import math
import os
import sys
import time
import traceback
from fractions import Fraction

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

VERSION = "0.1.0"
GRID = 32            # interval end points per side in the coarse scan
REFINE = 9           # points per side in the local refinement around the best intervals
REFINE_TOP = 3
HK_TOP = 4           # intervals refined with Lagrangian weights
HK_ITERS = 120
PER_1000 = 40.0      # seconds per 1,000 customers per instance
BASE_S = 40.0
CAP_S = 420.0
T0 = time.time()


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def travel_lb(dx, dy):
    """A lower bound of the challenge's travel time floor(d + 0.5) that never rounds a tie up."""
    return np.floor(np.hypot(dx, dy) + 0.5 - 1e-9)


# ---------------------------------------------------------------- instance arrays

class Inst:
    """Customers 0..n-1 (file customer i + 1). e / l: earliest / latest service start, tightened with lower-bound
    travel from and to the depot (so they are at most / at least the true tightened values: the bound stays valid)."""

    def __init__(self, inst):
        rows = inst["rows"]
        self.name = inst.get("name", "")
        self.n = len(rows) - 1
        xy = np.array([(r[0], r[1]) for r in rows], dtype=np.float64)
        a = np.array([r[3] for r in rows], dtype=np.float64)
        b = np.array([r[4] for r in rows], dtype=np.float64)
        s = np.array([r[5] for r in rows], dtype=np.float64)
        q = np.array([r[2] for r in rows], dtype=np.float64)
        self.capfree = bool(q[1:].sum() <= float(inst["capacity"]) + 1e-9)
        self.depot = xy[0].copy()
        self.xy = xy[1:].copy()
        t0 = travel_lb(self.xy[:, 0] - xy[0, 0], self.xy[:, 1] - xy[0, 1])
        self.t0 = t0
        self.D0 = float(a[0] + s[0])      # earliest departure from the depot
        self.B0 = float(b[0])             # latest return to the depot
        self.s = s[1:].copy()
        self.e = np.maximum(a[1:], self.D0 + t0)
        self.l = np.minimum(b[1:], self.B0 - self.s - t0)
        self.f = self.l + self.s          # latest service end
        self.unservable = int((self.e > self.l + 1e-9).sum())
        self.service_min = float(self.s.min()) if self.n else 0.0
        self.integral = bool(all(float(v).is_integer() for v in np.concatenate([a, b, s, xy.ravel()])))


# ---------------------------------------------------------------- spanning trees

def prim(xy, lam=None, root=None):
    """MST over the points xy (m x 2), plus the point `root` (index m, weight offset 0) if given.
    Edge weight = travel_lb + lam_i + lam_j (lam integral, >= 0). Returns (total, child, parent, w) with python-int
    total and one edge (child, parent, weight) per non-start vertex; the start is the root if given, else vertex 0."""
    P = xy if root is None else np.vstack([xy, np.asarray(root, dtype=np.float64)[None, :]])
    N = len(P)
    if N <= 1:
        return 0, np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64), np.zeros(0)
    lv = np.zeros(N) if lam is None else np.concatenate([np.asarray(lam, dtype=np.float64),
                                                         np.zeros(N - len(lam))])
    px, py = P[:, 0], P[:, 1]
    start = N - 1 if root is not None else 0
    key = np.full(N, np.inf)
    par = np.full(N, -1, dtype=np.int64)
    done = np.zeros(N, dtype=bool)
    u = start
    done[u] = True
    for _ in range(N - 1):
        d = travel_lb(px - px[u], py - py[u]) + lv + lv[u]
        better = d < key
        better &= ~done
        key[better] = d[better]
        par[better] = u
        kk = np.where(done, np.inf, key)
        u = int(np.argmin(kk))
        done[u] = True
    child = np.flatnonzero(np.arange(N) != start)
    w = key[child]
    total = int(round(float(w.sum())))
    return total, child, par[child], w


def degrees(N, child, parent):
    deg = np.zeros(N, dtype=np.int64)
    np.add.at(deg, child, 1)
    np.add.at(deg, parent, 1)
    return deg


def forest_drop(w, k):
    """Indices of the k - 1 heaviest edges (dropped to get the best forest with at most k trees)."""
    if k <= 1 or len(w) == 0:
        return np.zeros(0, dtype=np.int64)
    return np.argsort(-w, kind="stable")[:k - 1]


def k_free(L, W, w_sorted_desc, F):
    """Smallest K >= 1 with K * L >= W + (F minus the K - 1 heaviest edges). Plain numbers (exact for integers)."""
    K = 1
    while K * L < W + F:
        if K - 1 < len(w_sorted_desc):
            F -= w_sorted_desc[K - 1]
        K += 1
    return K


# ---------------------------------------------------------------- one interval

def interval_set(I, t1, t2):
    return np.flatnonzero((I.e >= t1 - 1e-9) & (I.f <= t2 + 1e-9))


def variant_of(I, t1, t2):
    st = t1 <= I.D0 + 1e-9
    en = t2 >= I.B0 - 1e-9
    return "full" if (st and en) else "start" if st else "end" if en else "free"


def plain_bound(I, t1, t2, S=None):
    """Plain (lambda = 0) bound of one interval; returns dict with the needed fleet K and its ingredients."""
    if S is None:
        S = interval_set(I, t1, t2)
    m = len(S)
    if m == 0:
        return None
    L = t2 - t1
    W = float(I.s[S].sum())
    var = variant_of(I, t1, t2)
    tot, _, _, w = prim(I.xy[S])
    wd = sorted([int(round(x)) for x in w], reverse=True)
    K = k_free(L, W, wd, tot)
    out = {"t1": t1, "t2": t2, "m": int(m), "W": W, "L": L, "variant": "free", "K": int(K), "forest": tot}
    if var != "free":
        tot0, _, _, _ = prim(I.xy[S], root=I.depot)
        if var == "full":
            r = float(I.t0[S].min())
            Kr = math.ceil((W + tot0) / (L - r) - 1e-9) if L > r else None
        else:
            Kr = math.ceil((W + tot0) / L - 1e-9)
        if Kr is not None and Kr > K:
            out.update({"variant": var, "K": int(Kr), "forest": tot0})
    return out


def hk_bound(I, t1, t2, k_start, deadline, variant=None, iters=HK_ITERS, clock=time.monotonic):
    """Lagrangian (degree <= 2) refinement of one interval. Tries to prove K >= k_start + 1, k_start + 2, ...
    `variant` "free" is valid for every interval; a rooted variant only where variant_of() allows it.
    Returns (K proven, lambda (python ints) of the last proof or None, iterations, history)."""
    S = interval_set(I, t1, t2)
    m = len(S)
    L = t2 - t1
    W = float(I.s[S].sum())
    var = variant or variant_of(I, t1, t2)
    if var != "free" and var != variant_of(I, t1, t2):
        raise ValueError("variant %s not valid for this interval" % var)
    rooted = var != "free"
    xy = I.xy[S]
    lam = np.zeros(m)
    K = int(k_start)
    best_lam, it, hist = None, 0, []
    theta, best_gap, stall = 1.0, None, 0
    r_full = I.t0[S]
    while it < iters and clock() < deadline:
        it += 1
        li = np.rint(lam)
        if rooted:
            tot, child, parent, w = prim(xy, lam=li, root=I.depot)
            LB = tot - 2 * int(li.sum())
            if var == "full":
                r = float((r_full + li).min())
                if L <= r:
                    break
                K_now = math.ceil((W + LB) / (L - r) - 1e-9)
                need = (L - r) * K - W     # LB must exceed this to prove K + 1
            else:
                K_now = math.ceil((W + LB) / L - 1e-9)
                need = L * K - W
            deg = degrees(m + 1, child, parent)[:m]
        else:
            tot, child, parent, w = prim(xy, lam=li)
            drop = forest_drop(w, K)
            keep = np.ones(len(w), dtype=bool)
            keep[drop] = False
            F = tot - int(round(float(w[drop].sum())))
            LB = F - 2 * int(li.sum())
            need = L * K - W
            K_now = K + 1 if LB > need else K
            deg = degrees(m, child[keep], parent[keep])
        hist.append([it, int(LB), float(need), int(K_now)])
        if K_now > K:
            K = int(K_now) if rooted else K + 1
            best_lam = [int(x) for x in li]
            best_gap, stall = None, 0
            continue
        gap = need - LB
        if best_gap is None or gap < best_gap - 1e-9:
            best_gap, stall = gap, 0
        else:
            stall += 1
            if stall >= 8:
                theta, stall = theta / 2.0, 0
                if theta < 1e-3:
                    break
        g = (deg - 2).astype(np.float64)
        g[(lam <= 0) & (g < 0)] = 0.0
        nrm = float((g * g).sum())
        if nrm == 0:
            break
        lam = np.maximum(0.0, lam + theta * (gap + 1.0) / nrm * g)
    return K, best_lam, it, hist


def verify(I, t1, t2, K, lam, variant):
    """Exact re-check of one certificate: the interval, set, variant, lambda and the claimed fleet K.
    Uses Fractions for the time arithmetic (the floats of the file are exact binary numbers) and integer forest
    weights. Returns True if K is proven."""
    S = interval_set(I, t1, t2)
    m = len(S)
    if m == 0:
        return K <= 0
    var = variant
    if var != "free" and var != variant_of(I, t1, t2):
        return False
    li = np.zeros(m) if lam is None else np.asarray(lam, dtype=np.float64)
    if np.any(li < 0) or np.any(li != np.rint(li)):
        return False
    L = Fraction(t2) - Fraction(t1)
    W = sum(Fraction(float(x)) for x in I.s[S])
    Kp = K - 1   # we must show that Kp vehicles cannot do it
    if Kp <= 0:
        return True
    if var == "free":
        tot, child, parent, w = prim(I.xy[S], lam=li)
        drop = forest_drop(w, Kp)
        F = tot - int(round(float(w[drop].sum())))
        LB = F - 2 * int(li.sum())
        return Kp * L < W + LB
    tot, child, parent, w = prim(I.xy[S], lam=li, root=I.depot)
    LB = tot - 2 * int(li.sum())
    if var == "full":
        r = min(Fraction(float(x)) + int(y) for x, y in zip(I.t0[S], li))
        if L <= r:
            return False
        return Kp * (L - r) < W + LB
    return Kp * L < W + LB


# ---------------------------------------------------------------- whole instance

def grid_points(vals, G, extra):
    v = np.unique(vals)
    if len(v) == 0:
        return sorted(set(extra))
    idx = np.unique(np.rint(np.linspace(0, len(v) - 1, min(G, len(v)))).astype(np.int64))
    return sorted(set([float(x) for x in v[idx]] + [float(x) for x in extra]))


def profile(I):
    H = I.B0 - I.D0
    wid = (I.l - I.e) / H if H > 0 else np.zeros(I.n)
    q = np.quantile(wid, [0.1, 0.25, 0.5, 0.75, 0.9]) if I.n else [0] * 5
    return {"horizon": H, "width_q10_25_50_75_90": [round(float(x), 4) for x in q],
            "share_width_ge_half": round(float((wid >= 0.5).mean()), 4),
            "share_width_le_5pct": round(float((wid <= 0.05).mean()), 4),
            "service_mean": round(float(I.s.mean()), 3), "service_min": I.service_min,
            "bbox": [round(float(x), 1) for x in (I.xy[:, 0].min(), I.xy[:, 1].min(), I.xy[:, 0].max(),
                                                  I.xy[:, 1].max())]}


def bound_instance(I, budget, grid=GRID, clock=time.monotonic, say=log):
    t_start = clock()
    dl_scan = t_start + 0.45 * budget
    dl_ref = t_start + 0.6 * budget
    dl_all = t_start + budget
    T1 = grid_points(I.e, grid, [I.D0])
    T2 = grid_points(I.f, grid, [I.B0])
    pairs = [(a, b) for a in T1 for b in T2 if b > a]
    seen, res = set(), []
    scanned, cut = 0, False

    def run(a, b):
        key = (a, b)
        if key in seen:
            return
        seen.add(key)
        r = plain_bound(I, a, b)
        if r is not None:
            res.append(r)

    # whole day first, then the coarse grid in a fixed shuffled order (a time cut then still samples everywhere)
    run(I.D0, I.B0)
    order = np.random.default_rng(20261117).permutation(len(pairs)) if pairs else []
    for j in order:
        a, b = pairs[int(j)]
        if clock() > dl_scan:
            cut = True
            break
        run(a, b)
        scanned += 1
    # local refinement around the best intervals
    res.sort(key=lambda r: (-r["K"], -(r["W"] + r["forest"]) / r["L"]))
    ev, fv = np.unique(I.e), np.unique(I.f)
    for r in res[:REFINE_TOP]:
        ia = int(np.searchsorted(ev, r["t1"] - 1e-9))
        ib = int(np.searchsorted(fv, r["t2"] - 1e-9))
        span_a = max(1, len(ev) // max(grid, 1))
        span_b = max(1, len(fv) // max(grid, 1))
        A = np.unique(np.clip(np.rint(np.linspace(ia - span_a, ia + span_a, REFINE)), 0, len(ev) - 1).astype(int))
        B = np.unique(np.clip(np.rint(np.linspace(ib - span_b, ib + span_b, REFINE)), 0, len(fv) - 1).astype(int))
        for x in A:
            for y in B:
                if clock() > dl_ref:
                    break
                a, b = float(ev[x]), float(fv[y])
                if b > a:
                    run(a, b)
    res.sort(key=lambda r: (-r["K"], -(r["W"] + r["forest"]) / r["L"]))
    plain = res[0] if res else None
    out = {"intervals": len(res), "scan_cut": cut, "plain": plain, "hk": None, "best_K": plain["K"] if plain else 0,
           "best_source": "plain", "cert": None}
    if plain is not None:
        out["cert"] = {"t1": plain["t1"], "t2": plain["t2"], "variant": plain["variant"], "m": plain["m"],
                       "K": plain["K"], "lam": None}
    # Lagrangian refinement on the top intervals, sharing the remaining time
    hk_rows = []
    tops = res[:HK_TOP]
    for j, r in enumerate(tops):
        now = clock()
        if now > dl_all:
            break
        share = (dl_all - now) / float(len(tops) - j)
        K, lam, its, hist = hk_bound(I, r["t1"], r["t2"], r["K"], now + share, variant=r["variant"], clock=clock)
        hk_rows.append({"t1": r["t1"], "t2": r["t2"], "variant": r["variant"], "m": r["m"], "K_plain": r["K"],
                        "K_hk": K, "iterations": its, "last": hist[-1] if hist else None})
        if K > out["best_K"] and lam is not None:
            out["best_K"], out["best_source"] = K, "hk"
            out["cert"] = {"t1": r["t1"], "t2": r["t2"], "variant": r["variant"], "m": r["m"], "K": K, "lam": lam}
    out["hk"] = hk_rows
    if out["cert"] is not None:
        c = out["cert"]
        out["verified"] = bool(verify(I, c["t1"], c["t2"], c["K"], c["lam"], c["variant"]))
        if not out["verified"]:
            # never report what the exact re-check does not confirm
            ok_plain = verify(I, plain["t1"], plain["t2"], plain["K"], None, plain["variant"])
            out["best_K"], out["best_source"] = (plain["K"] if ok_plain else 1), "plain-after-failed-check"
            out["failed_cert"] = c
            out["cert"] = {"t1": plain["t1"], "t2": plain["t2"], "variant": plain["variant"], "m": plain["m"],
                           "K": out["best_K"], "lam": None}
    out["seconds"] = round(clock() - t_start, 1)
    say("%s: best %s (%s), plain %s, intervals %d%s" % (
        I.name, out["best_K"], out["best_source"], plain["K"] if plain else None, len(res),
        " (scan cut)" if cut else ""))
    return out


# ---------------------------------------------------------------- study harness

def load_ref(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    out = {}
    for r in data.get("instances", []):
        vals = [x for x in (r.get("k"), r.get("e")) if x is not None]
        out[r["instance"]] = {"kc": r.get("kc"), "kstar": max(vals) if vals else None,
                              "vehicles_a": r.get("vehicles_a")}
    return out


def find_files(data_dir):
    by_name = {}
    for p in sorted(glob.glob(os.path.join(data_dir, "xltw-test", "x-*", "**", "*.vrp"), recursive=True)):
        by_name.setdefault(os.path.splitext(os.path.basename(p))[0], p)
    return by_name


def peak_gb():
    try:
        import resource
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0 / 1024.0, 3)
    except Exception:  # noqa: BLE001 - not on Linux
        return None


BEST = {"XLTW-Test-n1234": 33, "XLTW-Test-n1421": 65, "XLTW-Test-n1608": 108, "XLTW-Test-n1841": 25}
SERVICE1_GAP = ("XLTW-Test-n1048", "XLTW-Test-n1514", "XLTW-Test-n2867", "XLTW-Test-n5902")


def one(path, name, ref, cert_dir):
    import xltwlb as X
    with open(path, encoding="utf-8") as f:
        inst = X.parse_any(f.read())
    inst.setdefault("name", name)
    I = Inst(inst)
    I.name = name
    rf = ref.get(name) or {}
    ubs = [x for x in (rf.get("vehicles_a"), BEST.get(name)) if x is not None]
    ub = min(ubs) if ubs else None
    rec = {"instance": name, "customers": I.n, "capfree": I.capfree, "kstar": rf.get("kstar"), "ub": ub,
           "integral": I.integral, "unservable": I.unservable, "profile": profile(I)}
    if I.unservable:
        rec["error"] = "instance has customers no route can serve"
        return rec
    if I.service_min < 1:
        rec["error"] = "a service time is below 1: the via-customer step is not proven"
        return rec
    budget = min(CAP_S, BASE_S + PER_1000 * I.n / 1000.0)
    res = bound_instance(I, budget)
    rec.update({"budget_s": round(budget, 1), "bound": int(res["best_K"]), "source": res["best_source"],
                "verified": res.get("verified"), "plain": res["plain"], "hk": res["hk"], "intervals": res["intervals"],
                "scan_cut": res["scan_cut"], "seconds": res["seconds"]})
    rec["plain_K"] = res["plain"]["K"] if res["plain"] else None
    k = rec["kstar"]
    rec["above_kstar"] = bool(k is not None and rec["bound"] > k)
    rec["above_ub"] = bool(ub is not None and rec["bound"] > ub)
    rec["proved"] = bool(ub is not None and rec["bound"] >= ub)
    rec["gap_closed"] = (round((max(rec["bound"], k) - k) / float(ub - k), 4)
                         if (k is not None and ub is not None and ub > k) else None)
    if res["cert"] is not None:
        os.makedirs(cert_dir, exist_ok=True)
        c = dict(res["cert"])
        c.update({"instance": name, "fleet_at_least": rec["bound"], "verified": rec["verified"],
                  "rule": "K (t2 - t1) >= sum s(S) + min forest of S with <= K trees (free), or rooted at the depot "
                          "(start/end/full); weights floor(d + 0.5 - 1e-9) + lam_i + lam_j, minus 2 sum lam",
                  "solver": "mstfleet " + VERSION})
        with open(os.path.join(cert_dir, name + ".json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(c, f)
    rec["peak_gb"] = peak_gb()
    return rec


def tally(recs):
    ok = [r for r in recs if not r.get("error")]
    hk_gain = [r["instance"] for r in ok if r.get("plain_K") is not None and r["bound"] > r["plain_K"]]
    free_best = [r["instance"] for r in ok if (r.get("plain") or {}).get("variant") == "free"]
    sk = [r for r in ok if r.get("kstar") is not None]
    return {
        "instances_done": len(ok),
        "errors": [r["instance"] for r in recs if r.get("error")],
        "unverified": [r["instance"] for r in ok if r.get("verified") is False],
        "above_ub": [r["instance"] for r in ok if r.get("above_ub")],
        "above_kstar": [r["instance"] for r in ok if r.get("above_kstar")],
        "service1_above_kstar": [r["instance"] for r in ok if r.get("above_kstar") and r["instance"] in SERVICE1_GAP],
        "proved": [r["instance"] for r in ok if r.get("proved")],
        "hk_gain": hk_gain,
        "plain_best_is_free": free_best,
        "n1048_bound": next((r["bound"] for r in ok if r["instance"] == "XLTW-Test-n1048"), None),
        "median_width_median": (round(float(np.median([r["profile"]["width_q10_25_50_75_90"][2] for r in ok])), 4)
                                if ok else None),
        "sum_kstar": sum(r["kstar"] for r in sk),
        "sum_max": sum(max(r["kstar"], r["bound"]) for r in sk),
        "peak_gb": max([r["peak_gb"] for r in ok if r.get("peak_gb") is not None] or [None]) if ok else None,
    }


def write_md(path, res):
    t = res["tally"]
    L = ["# mstfleet on XLTW-Test: interval spanning-forest fleet bounds", "",
         "Pre-registered in PREREG.md. Solver %s. Certificates in cert/." % VERSION, "",
         "Tally: `%s`" % json.dumps(t), "",
         "| instance | n | K* | mstfleet | source | plain | variant | interval | customers in it | best known fleet | "
         "gap closed | median width / day | s |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["instances"]:
        if r.get("error"):
            L.append("| %s | error: %s ||||||||||||" % (r["instance"], r["error"].strip().splitlines()[-1]))
            continue
        p = r.get("plain") or {}
        L.append("| %s | %d | %s | %d | %s | %s | %s | [%s, %s] | %s | %s | %s | %s | %s |" % (
            r["instance"], r["customers"], r["kstar"], r["bound"], r["source"], r.get("plain_K"), p.get("variant"),
            p.get("t1"), p.get("t2"), p.get("m"), r["ub"], r["gap_closed"],
            r["profile"]["width_q10_25_50_75_90"][2], r["seconds"]))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


def plan(ref, files):
    names = [k for k, v in ref.items() if v.get("kc") == 1 and k in files]
    return sorted(names, key=lambda k: int(k.rsplit("n", 1)[-1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    out = os.path.join(a.out_dir, "mstfleet")
    os.makedirs(out, exist_ok=True)
    ref = load_ref(os.path.join(HERE, "xltwen-results.json"))
    files = find_files(a.data_dir)
    names = [x for x in a.only.split(",") if x] or plan(ref, files)
    res = {"solver": "mstfleet " + VERSION, "python": sys.version.split()[0], "numpy": np.__version__,
           "settings": {"grid": GRID, "refine": REFINE, "refine_top": REFINE_TOP, "hk_top": HK_TOP,
                        "hk_iters": HK_ITERS, "per_1000": PER_1000, "base_s": BASE_S, "cap_s": CAP_S},
           "ref_instances": len(ref), "files_found": len(files), "plan": names, "instances": []}
    log("plan: %d instances, %d files, %d reference rows" % (len(names), len(files), len(ref)))
    res_path = os.path.join(out, "results.json")
    for name in names:
        if name not in files:
            rec = {"instance": name, "error": "instance file not found"}
        else:
            try:
                rec = one(files[name], name, ref, os.path.join(out, "cert"))
            except Exception:  # noqa: BLE001 - recorded
                rec = {"instance": name, "error": traceback.format_exc()}
        res["instances"].append(rec)
        res["tally"] = tally(res["instances"])
        with open(res_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(res, f, indent=1)
        log(json.dumps({k: rec.get(k) for k in ("instance", "customers", "kstar", "bound", "source", "plain_K", "ub",
                                               "seconds", "peak_gb", "error")}))
    res["tally"] = tally(res["instances"])
    with open(res_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1)
    write_md(os.path.join(out, "results.md"), res)
    log("TALLY " + json.dumps(res["tally"]))


if __name__ == "__main__":
    main()
