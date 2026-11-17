"""stfleet (mstfleet 0.2): space-time spanning-tree lower bounds on the number of vehicles for the VRPTW (XLTW-Test).

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

Why. mstfleet 0.1 (../mstfleet/) charges the vehicles that serve the customers of a time interval only their service
and the plain travel between them. It ignores two things every route pays for: waiting forced by the time windows,
and the idle stretch of the interval before a vehicle's first and after its last customer there. This version
charges both, in one formula that contains all four 0.1 variants (free, start, end, whole day).

Bound. Fix an interval [t1, t2], L = t2 - t1, and let S be the customers whose whole service must lie inside it
(earliest start e_i >= t1 and latest end f_i = l_i + s_i <= t2, windows tightened by the depot's hours as in 0.1).
Take one vehicle that serves p >= 1 customers of S, in the order i_1, ..., i_p. Its interval splits EXACTLY into

    L = (start(i_1) - t1) + sum of their services + sum_k (start(i_k+1) - end(i_k)) + (t2 - end(i_p)),

and every part has a lower bound:
  * before the first:  start(i_1) - t1 >= a_i := e_i - t1;
  * after the last:    t2 - end(i_p)   >= b_i := t2 - f_i;
  * from i to the next S-customer j: start(j) - end(i) >= d_ij := max(t_ij, e_j - f_i), and the order i -> j is
    impossible when e_i + s_i + t_ij > l_j. Going through other customers is never faster: rounded travel times
    satisfy t_ik + t_kj >= t_ij - 1 and every service time is at least 1 (checked per instance). Unordered weight
    w_ij = min(d_ij, d_ji) (BIG when neither order is possible).
Join each serving vehicle's first customer to a root R. Its consecutive pairs plus these root edges form a spanning
tree of S + R with root degree p <= K and every customer of degree <= 2. With root-edge weight
c_i = a_i + beta - L (beta = min_i b_i), summing over the p serving vehicles gives 0 >= W + w_c(tree), W = total
service of S. A Lagrangian weight mu >= 0 on the root degree (<= K) and integer lam_i >= 0 on the customer degrees
(<= 2) then give, for every K:

    K vehicles are impossible if  N(mu, lam) - mu K > 0,   N = MST(S + R; w + lam_i + lam_j, c + mu + lam_i) - 2 sum lam + W

i.e. fleet >= ceil(N / mu). The time-reversed form (root edges b_i + min a) is valid too; both are tried ("side").
With a = b = 0 and plain travel this is 0.1's free forest bound (mu - L between the K-th and (K-1)-th heaviest MST
edges). At mu = L - beta the root edges cost a_i, which is at least the depot travel when t1 is the depot's opening,
so 0.1's rooted variants are contained as well (a test checks the whole-day case).
N / mu is quasi-concave in mu (N is concave), so mu is searched by a scan and a ternary search; lam by subgradient
steps. Every reported bound is re-checked exactly by verify() (integral instances only: all weights are integers).

  python stfleet.py --data-dir /data --out-dir /out
"""
import argparse
import json
import os
import sys
import time
import traceback

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import mstfleet as M  # noqa: E402  (mstfleet 0.1.0: Inst, interval_set, grid_points, profile, travel_lb, ...)

VERSION = "0.2.0"
BIG = 1.0e15
GRID = 16                       # interval end points per side in the scan
MU_SCAN = (0.35, 0.6, 1.0, 1.6)  # multiples of mu0 = L - beta tried per interval and side in the scan
TOP = 4                         # intervals refined (ternary search on mu, then Lagrangian lam)
MU_ITERS = 14
HK_ITERS = 80
PER_1000 = 50.0
BASE_S = 40.0
CAP_S = 480.0
SIDES = ("start", "end")
T0 = time.time()


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


# ---------------------------------------------------------------- one interval

class Sub:
    """The customers S of one interval [t1, t2] and the root-edge weights c for one side."""

    def __init__(self, I, t1, t2, side):
        if side not in SIDES:
            raise ValueError("side must be one of %s" % (SIDES,))
        S = M.interval_set(I, t1, t2)
        self.t1, self.t2, self.side = float(t1), float(t2), side
        self.S = S
        self.m = int(len(S))
        self.xy = I.xy[S]
        self.e = I.e[S]
        self.l = I.l[S]
        self.s = I.s[S]
        self.f = I.f[S]
        self.es = self.e + self.s
        self.L = float(t2) - float(t1)
        self.W = int(round(float(self.s.sum())))
        if self.m:
            a = self.e - float(t1)
            b = float(t2) - self.f
            if side == "start":
                beta = float(b.min())
                self.c = a + beta - self.L
            else:
                beta = float(a.min())
                self.c = b + beta - self.L
            self.mu0 = max(1, int(round(self.L - beta)))
        else:
            self.c = np.zeros(0)
            self.mu0 = 1


def st_prim(sub, mu, lam=None):
    """Minimum spanning tree of S + root. Customer-customer weight: w_ij + lam_i + lam_j; root-customer weight:
    c_i + mu + lam_i. Returns (total as a python int, root degree, customer degrees). Exact for integral data."""
    m = sub.m
    if m == 0:
        return 0, 0, np.zeros(0, dtype=np.int64)
    lv = np.zeros(m) if lam is None else np.asarray(lam, dtype=np.float64)
    px, py = sub.xy[:, 0], sub.xy[:, 1]
    e, l, f, es = sub.e, sub.l, sub.f, sub.es
    key = sub.c + float(mu) + lv
    par = np.full(m, -1, dtype=np.int64)
    done = np.zeros(m, dtype=bool)
    total = 0
    for _ in range(m):
        u = int(np.argmin(np.where(done, np.inf, key)))
        done[u] = True
        total += int(round(float(key[u])))
        t = M.travel_lb(px - px[u], py - py[u])
        fwd = np.where(es[u] + t <= l, np.maximum(t, e - f[u]), BIG)      # u, then v
        bwd = np.where(es + t <= l[u], np.maximum(t, e[u] - f), BIG)      # v, then u
        w = np.minimum(fwd, bwd) + lv + lv[u]
        better = (w < key) & ~done
        key[better] = w[better]
        par[better] = u
    root = par < 0
    deg = np.zeros(m, dtype=np.int64)
    deg[root] += 1
    ch = np.flatnonzero(~root)
    deg[ch] += 1
    np.add.at(deg, par[ch], 1)
    return total, int(root.sum()), deg


def fleet_from(N, mu):
    """fleet >= ceil(N / mu), and at least 1."""
    return max(1, -(-int(N) // int(mu)))


def evaluate(sub, mu, lam=None):
    mu = max(1, int(mu))
    tot, rd, deg = st_prim(sub, mu, lam)
    sl = 0 if lam is None else int(round(float(np.sum(lam))))
    N = tot - 2 * sl + sub.W
    return {"mu": mu, "N": int(N), "K": fleet_from(N, mu), "root_deg": rd, "deg": deg}


def better(x, y):
    """Is evaluation x better than y (higher fleet bound, then higher N / mu)?"""
    if y is None:
        return True
    return (x["K"], x["N"] / x["mu"]) > (y["K"], y["N"] / y["mu"])


def refine_mu(sub, mu_c, deadline, iters=MU_ITERS, clock=time.monotonic, lam=None):
    """Ternary search of the integer mu in [mu_c / 2, 2 mu_c] maximising N / mu (quasi-concave). Every evaluated mu
    gives a valid bound; returns the best evaluation."""
    cache = {}

    def ev(mu):
        mu = max(1, int(mu))
        if mu not in cache:
            cache[mu] = evaluate(sub, mu, lam)
        return cache[mu]

    best = ev(mu_c)
    lo, hi = max(1, mu_c // 2), max(2, 2 * mu_c)
    for _ in range(iters):
        if hi - lo < 3 or clock() > deadline:
            break
        m1 = lo + (hi - lo) // 3
        m2 = hi - (hi - lo) // 3
        r1, r2 = ev(m1), ev(m2)
        s1, s2 = r1["N"] / r1["mu"], r2["N"] / r2["mu"]
        if s1 < s2:
            lo = m1
        elif s1 > s2:
            hi = m2
        else:
            lo, hi = m1, m2
    if hi - lo < 3 and clock() <= deadline:
        for mu in range(lo, hi + 1):
            ev(mu)
    for r in cache.values():
        if better(r, best):
            best = r
    return best


def hk(sub, mu, K0, deadline, iters=HK_ITERS, clock=time.monotonic):
    """Subgradient search of integer lam >= 0 at fixed mu. Returns (K proven, lam of the proof or None, iterations)."""
    m = sub.m
    lam = np.zeros(m)
    K, best_lam = int(K0), None
    theta, best_gap, stall, it = 1.0, None, 0, 0
    while it < iters and clock() < deadline:
        it += 1
        li = np.rint(lam)
        r = evaluate(sub, mu, li)
        if r["K"] > K:
            K, best_lam = r["K"], [int(x) for x in li]
            best_gap, stall = None, 0
            continue
        gap = K * mu - r["N"] + 1          # N must exceed K mu to prove K + 1
        if best_gap is None or gap < best_gap:
            best_gap, stall = gap, 0
        else:
            stall += 1
            if stall >= 8:
                theta, stall = theta / 2.0, 0
                if theta < 1e-3:
                    break
        g = (r["deg"] - 2).astype(np.float64)
        g[(lam <= 0) & (g < 0)] = 0.0
        nrm = float((g * g).sum())
        if nrm == 0:
            break
        lam = np.maximum(0.0, lam + theta * max(gap, 1) / nrm * g)
    return K, best_lam, it


def verify(I, cert):
    """Exact re-check of one certificate {t1, t2, side, mu, lam, K}: True if fleet >= K is proven."""
    try:
        if not I.integral:
            return False
        K = int(cert["K"])
        if K <= 1:
            return True
        sub = Sub(I, cert["t1"], cert["t2"], cert["side"])
        if sub.m == 0:
            return False
        mu = cert["mu"]
        if isinstance(mu, bool) or not isinstance(mu, int) or mu < 1:
            return False
        lam = cert.get("lam")
        li = np.zeros(sub.m) if lam is None else np.asarray(lam, dtype=np.float64)
        if li.shape != (sub.m,) or np.any(li < 0) or np.any(li != np.rint(li)):
            return False
        tot, _, _ = st_prim(sub, mu, li)
        N = tot - 2 * sum(int(x) for x in li) + sub.W
        return (K - 1) * mu < N
    except (KeyError, ValueError, TypeError):
        return False


# ---------------------------------------------------------------- whole instance

def bound_instance(I, budget, grid=GRID, clock=time.monotonic, say=log):
    t_start = clock()
    dl_scan = t_start + 0.5 * budget
    dl_all = t_start + budget
    T1 = M.grid_points(I.e, grid, [I.D0])
    T2 = M.grid_points(I.f, grid, [I.B0])
    pairs = [(a, b) for a in T1 for b in T2 if b > a]
    seen, res = set(), []
    cut = False

    def scan(a, b):
        if (a, b) in seen:
            return
        seen.add((a, b))
        for side in SIDES:
            sub = Sub(I, a, b, side)
            if sub.m == 0:
                return
            best = None
            for r in MU_SCAN:
                if best is not None and clock() > dl_scan:
                    break
                ev = evaluate(sub, max(1, int(round(sub.mu0 * r))))
                if better(ev, best):
                    best = ev
            res.append({"t1": a, "t2": b, "side": side, "m": sub.m, "K": best["K"], "mu": best["mu"],
                        "N": best["N"], "root_deg": best["root_deg"]})

    scan(I.D0, I.B0)
    whole = [dict(r) for r in res]
    order = np.random.default_rng(20261117).permutation(len(pairs)) if pairs else []
    for j in order:
        if clock() > dl_scan:
            cut = True
            break
        scan(*pairs[int(j)])
    res.sort(key=lambda r: (-r["K"], -r["N"] / r["mu"]))
    out = {"intervals": len(seen), "scan_cut": cut, "whole_day": whole, "scan_best": res[0] if res else None,
           "refined": [], "best_K": res[0]["K"] if res else 0, "best_source": "scan", "cert": None}
    if not res:
        return out
    r0 = res[0]
    out["cert"] = {"t1": r0["t1"], "t2": r0["t2"], "side": r0["side"], "mu": int(r0["mu"]), "lam": None,
                   "K": int(r0["K"]), "m": r0["m"]}
    tops = res[:TOP]
    for j, r in enumerate(tops):
        now = clock()
        if now > dl_all:
            break
        share = (dl_all - now) / float(len(tops) - j)
        sub = Sub(I, r["t1"], r["t2"], r["side"])
        ev = refine_mu(sub, int(r["mu"]), now + 0.35 * share, clock=clock)
        K_mu = ev["K"]
        K_hk, lam, its = hk(sub, ev["mu"], K_mu, now + share, clock=clock)
        row = {"t1": r["t1"], "t2": r["t2"], "side": r["side"], "m": r["m"], "K_scan": r["K"], "mu_scan": r["mu"],
               "K_mu": K_mu, "mu": ev["mu"], "root_deg": ev["root_deg"], "K_hk": K_hk, "hk_iterations": its}
        out["refined"].append(row)
        if K_mu > out["best_K"]:
            out["best_K"], out["best_source"] = K_mu, "mu"
            out["cert"] = {"t1": r["t1"], "t2": r["t2"], "side": r["side"], "mu": int(ev["mu"]), "lam": None,
                           "K": int(K_mu), "m": r["m"]}
        if K_hk > out["best_K"] and lam is not None:
            out["best_K"], out["best_source"] = K_hk, "hk"
            out["cert"] = {"t1": r["t1"], "t2": r["t2"], "side": r["side"], "mu": int(ev["mu"]), "lam": lam,
                           "K": int(K_hk), "m": r["m"]}
    out["verified"] = bool(verify(I, out["cert"]))
    if not out["verified"]:
        # never report what the exact re-check does not confirm
        out["failed_cert"] = out["cert"]
        c0 = {"t1": r0["t1"], "t2": r0["t2"], "side": r0["side"], "mu": int(r0["mu"]), "lam": None,
              "K": int(r0["K"]), "m": r0["m"]}
        ok0 = verify(I, c0)
        out["best_K"], out["best_source"] = (r0["K"] if ok0 else 1), "scan-after-failed-check"
        c0["K"] = int(out["best_K"])
        out["cert"] = c0
    out["seconds"] = round(clock() - t_start, 1)
    say("%s: best %s (%s), scan %s, whole day %s, intervals %d%s" % (
        I.name, out["best_K"], out["best_source"], r0["K"], max(w["K"] for w in whole) if whole else None,
        len(seen), " (scan cut)" if cut else ""))
    return out


# ---------------------------------------------------------------- study harness

def v01_whole_day(I):
    """mstfleet 0.1's plain bound on the whole day (all its variants), for comparison."""
    r = M.plain_bound(I, I.D0, I.B0)
    return int(r["K"]) if r else None


def one(path, name, ref, cert_dir):
    import xltwlb as X
    with open(path, encoding="utf-8") as fh:
        inst = X.parse_any(fh.read())
    inst.setdefault("name", name)
    I = M.Inst(inst)
    I.name = name
    rf = ref.get(name) or {}
    ubs = [x for x in (rf.get("vehicles_a"), M.BEST.get(name)) if x is not None]
    ub = min(ubs) if ubs else None
    rec = {"instance": name, "customers": I.n, "capfree": I.capfree, "kstar": rf.get("kstar"), "ub": ub,
           "integral": I.integral, "unservable": I.unservable, "profile": M.profile(I)}
    if I.unservable:
        rec["error"] = "instance has customers no route can serve"
        return rec
    if I.service_min < 1:
        rec["error"] = "a service time is below 1: the via-customer step is not proven"
        return rec
    if not I.integral:
        rec["error"] = "non-integral data: the exact check needs integers"
        return rec
    budget = min(CAP_S, BASE_S + PER_1000 * I.n / 1000.0)
    res = bound_instance(I, budget)
    v01 = v01_whole_day(I)
    sb = res["scan_best"] or {}
    rec.update({"budget_s": round(budget, 1), "bound": int(res["best_K"]), "source": res["best_source"],
                "verified": res.get("verified"), "scan_best": sb, "whole_day": res["whole_day"],
                "refined": res["refined"], "intervals": res["intervals"], "scan_cut": res["scan_cut"],
                "seconds": res.get("seconds"), "v01_whole_day": v01})
    best_mu_K = max([r["K_mu"] for r in res["refined"]] + [sb.get("K", 0)])
    rec["K_before_lam"] = int(best_mu_K)
    c = res["cert"] or {}
    rec["best_is_whole_day"] = bool(c and c.get("t1") == I.D0 and c.get("t2") == I.B0)
    rec["best_side"] = c.get("side")
    k = rec["kstar"]
    rec["above_kstar"] = bool(k is not None and rec["bound"] > k)
    rec["above_ub"] = bool(ub is not None and rec["bound"] > ub)
    rec["proved"] = bool(ub is not None and rec["bound"] >= ub)
    rec["above_v01_whole_day"] = bool(v01 is not None and rec["bound"] > v01)
    rec["gap_closed"] = (round((max(rec["bound"], k) - k) / float(ub - k), 4)
                         if (k is not None and ub is not None and ub > k) else None)
    if res["cert"] is not None:
        os.makedirs(cert_dir, exist_ok=True)
        cc = dict(res["cert"])
        cc.update({"instance": name, "fleet_at_least": rec["bound"], "verified": rec["verified"],
                   "rule": "fleet >= ceil(N / mu), N = MST(S + root; min over orders of max(travel, e_j - f_i) "
                           "+ lam_i + lam_j, root edge a_i + min b - L + mu + lam_i [side start; b, a swapped for "
                           "side end]) - 2 sum lam + service(S); travel floor(d + 0.5 - 1e-9)",
                   "solver": "stfleet " + VERSION})
        with open(os.path.join(cert_dir, name + ".json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(cc, fh)
    rec["peak_gb"] = M.peak_gb()
    return rec


def tally(recs):
    ok = [r for r in recs if not r.get("error")]
    sk = [r for r in ok if r.get("kstar") is not None]
    return {
        "instances_done": len(ok),
        "errors": [r["instance"] for r in recs if r.get("error")],
        "unverified": [r["instance"] for r in ok if r.get("verified") is False],
        "above_ub": [r["instance"] for r in ok if r.get("above_ub")],
        "above_kstar": [r["instance"] for r in ok if r.get("above_kstar")],
        "service1_above_kstar": [r["instance"] for r in ok
                                 if r.get("above_kstar") and r["instance"] in M.SERVICE1_GAP],
        "proved": [r["instance"] for r in ok if r.get("proved")],
        "hk_gain": [r["instance"] for r in ok if r["bound"] > r.get("K_before_lam", r["bound"])],
        "above_v01_whole_day": [r["instance"] for r in ok if r.get("above_v01_whole_day")],
        "best_not_whole_day": [r["instance"] for r in ok if not r.get("best_is_whole_day")],
        "best_side_end": [r["instance"] for r in ok if r.get("best_side") == "end"],
        "n1048_bound": next((r["bound"] for r in ok if r["instance"] == "XLTW-Test-n1048"), None),
        "sum_kstar": sum(r["kstar"] for r in sk),
        "sum_max": sum(max(r["kstar"], r["bound"]) for r in sk),
        "sum_v01_whole_day": sum(r["v01_whole_day"] or 0 for r in ok),
        "sum_bound": sum(r["bound"] for r in ok),
        "peak_gb": max([r["peak_gb"] for r in ok if r.get("peak_gb") is not None] or [None]) if ok else None,
    }


def write_md(path, res):
    t = res["tally"]
    L = ["# stfleet (mstfleet 0.2) on XLTW-Test: space-time spanning-tree fleet bounds", "",
         "Pre-registered in PREREG.md. Solver %s. Certificates in cert/." % VERSION, "",
         "Tally: `%s`" % json.dumps(t), "",
         "| instance | n | K* | stfleet | source | 0.1 whole day | side | interval | customers in it | mu | "
         "best known fleet | gap closed | s |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["instances"]:
        if r.get("error"):
            L.append("| %s | error: %s ||||||||||||" % (r["instance"], str(r["error"]).strip().splitlines()[-1]))
            continue
        c = r.get("cert") or {}
        L.append("| %s | %d | %s | %d | %s | %s | %s | [%s, %s] | %s | %s | %s | %s | %s |" % (
            r["instance"], r["customers"], r["kstar"], r["bound"], r["source"], r.get("v01_whole_day"),
            c.get("side"), c.get("t1"), c.get("t2"), c.get("m"), c.get("mu"), r["ub"], r["gap_closed"],
            r.get("seconds")))
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    out = os.path.join(a.out_dir, "stfleet")
    os.makedirs(out, exist_ok=True)
    ref = M.load_ref(os.path.join(HERE, "xltwen-results.json"))
    files = M.find_files(a.data_dir)
    names = [x for x in a.only.split(",") if x] or M.plan(ref, files)
    res = {"solver": "stfleet " + VERSION, "mstfleet": M.VERSION, "python": sys.version.split()[0],
           "numpy": np.__version__,
           "settings": {"grid": GRID, "mu_scan": list(MU_SCAN), "top": TOP, "mu_iters": MU_ITERS,
                        "hk_iters": HK_ITERS, "per_1000": PER_1000, "base_s": BASE_S, "cap_s": CAP_S},
           "ref_instances": len(ref), "files_found": len(files), "plan": names, "instances": []}
    log("plan: %d instances, %d files, %d reference rows" % (len(names), len(files), len(ref)))
    res_path = os.path.join(out, "results.json")
    cert_dir = os.path.join(out, "cert")
    for name in names:
        if name not in files:
            rec = {"instance": name, "error": "instance file not found"}
        else:
            try:
                rec = one(files[name], name, ref, cert_dir)
            except Exception:  # noqa: BLE001 - recorded
                rec = {"instance": name, "error": traceback.format_exc()}
        cp = os.path.join(cert_dir, name + ".json")
        if not rec.get("error") and os.path.exists(cp):
            with open(cp, encoding="utf-8") as fh:
                c = json.load(fh)
            rec["cert"] = {k: c.get(k) for k in ("t1", "t2", "side", "mu", "m")}
        res["instances"].append(rec)
        res["tally"] = tally(res["instances"])
        with open(res_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(res, fh, indent=1)
        log(json.dumps({k: rec.get(k) for k in ("instance", "customers", "kstar", "bound", "source",
                                               "v01_whole_day", "ub", "seconds", "peak_gb", "error")}))
    res["tally"] = tally(res["instances"])
    with open(res_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(res, fh, indent=1)
    write_md(os.path.join(out, "results.md"), res)
    log("TALLY " + json.dumps(res["tally"]))


if __name__ == "__main__":
    main()
