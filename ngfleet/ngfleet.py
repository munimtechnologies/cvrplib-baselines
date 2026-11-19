"""ngfleet: a stronger column-generation fleet bound for VRPTW (time windows only), with ng-route pricing.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

Why. cgfleet (cvrplib-baselines main/cgfleet) bounds the fleet by Farley's argument over "R2 walks": walks that may
revisit customers, only never twice in a row and never as i -> j -> i. On instances with wide time windows (XTW,
XLTW), an R2 walk can circle round a cluster of close customers again and again, so its best profit P* is inflated
and the bound sum(pi) / P* is weak. ngfleet replaces R2 with ng-routes (Baldacci, Mingozzi and Roberti 2011) plus the
same 2-cycle rule: every customer j has a neighbourhood N(j) of its g closest customers; a partial route remembers which
of the customers it visited are still "close" and may not return to them. Every elementary route is an ng-route, so
the bound stays valid, and short cycles through close customers -- the cheap way to inflate P* -- are gone.

Exact pricing. P*(pi) = max over ng-routes (restricted to customers with integer dual pi_j >= 1) of the sum of pi, by
the same dynamic programme over integer profit levels as cgfleet: a label at (level k, customer j) is a partial route
ending at j with profit >= k, its earliest service start t at j, its memory M (a subset of N(j), held as a bitmask)
and its predecessor v (kept only when v is not in N(j); otherwise v is already in M). A route may go on to j' unless
j' == j, j' == v or j' is in M. Labels at (k, j) are kept on a Pareto front (earlier time, smaller memory, no or the
same predecessor). When the front holds B labels, a new label is MERGED into the closest one: earliest time,
intersection of memories, predecessor dropped unless equal. A merged label dominates both parts, so the computed P* is
still at least the profit of every ng-route (the proof is in PREREG.md and in test_ngfleet.py's brute-force checks).
Zero-profit customers are skipped as in cgfleet; that needs every service time >= 1 and nearest-integer travel times.

Column generation. Phase R2: cgfleet's own pricing until it converges (fast, numpy). Phase NG: the columns are cut to
elementary routes (removing a repeated visit never makes a route late, for the same reason as above), and column
generation goes on with ng pricing. Every pricing round gives an exact Farley bound; the reported bound is the best of
both phases, each with a certificate (pi_int, P*, ng size g, front size B) that one more pricing run re-checks.

  python ngfleet.py --help            (the probe harness is xtwprobe.py)
"""
import math
import os
import sys
import time
from fractions import Fraction

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

VERSION = "0.1.0"
TOL = 1e-6
NG = 8              # neighbourhood size g (customers remembered besides the current one)
BSLOTS = 4          # Pareto front size B per (level, customer)
Q_PRICE = 300
Q_FINAL = 1500
ALPHA = 0.5
WANT = 300
T0 = time.time()

try:  # numba is optional: the same kernel runs as plain Python (slow, but fine for the tests)
    from numba import njit as _njit
    HAVE_NUMBA = True
except Exception:  # noqa: BLE001
    _njit = None
    HAVE_NUMBA = False


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def fceil(x):
    x = Fraction(x)
    return -((-x.numerator) // x.denominator)


# ---------------------------------------------------------------- the level kernel

def _level_impl(k, CS, e, l, p, NB, posin, pptr, pidx, B, LT, LM, LV, LI, LS, CNT):
    """Build every label of profit level k. Returns the number of customers with at least one label at level k.

    CS[i, j] = s_i + t_ij (float). p: integer profits >= 1. NB[j, :g]: neighbours of j. posin[j, u]: position of u in
    NB[j] or -1. pptr/pidx: CSR lists of the customers i with e_i + CS[i, j] <= l_j (i != j). Labels of level k at j
    live in LT/LM/LV/LI/LS[k, j, :CNT[k, j]]; LI/LS point to the label (level k - p_j, i, slot) it extends, -1 = start.
    """
    m = CS.shape[0]
    g = NB.shape[1]
    alive = 0
    for j in range(m):
        if e[j] > l[j] + TOL:
            CNT[k, j] = 0
            continue
        if k <= p[j]:
            LT[k, j, 0] = e[j]
            LM[k, j, 0] = 0
            LV[k, j, 0] = -1
            LI[k, j, 0] = -1
            LS[k, j, 0] = -1
            CNT[k, j] = 1
            alive += 1
            continue
        kp = k - p[j]
        c = 0
        ej = e[j]
        lj = l[j]
        for a in range(pptr[j], pptr[j + 1]):
            i = pidx[a]
            ni = CNT[kp, i]
            if ni == 0:
                continue
            cij = CS[i, j]
            pij = int(posin[i, j])
            pji = int(posin[j, i])
            for b in range(ni):
                if LV[kp, i, b] == j:
                    continue
                mi = int(LM[kp, i, b])
                if pij >= 0 and ((mi >> pij) & 1) == 1:
                    continue
                t = LT[kp, i, b] + cij
                if t < ej:
                    t = ej
                if t > lj + TOL:
                    continue
                nm = 0
                if pji >= 0:
                    nm = nm | (1 << pji)
                    nv = -1
                else:
                    nv = i
                for bb in range(g):
                    if ((mi >> bb) & 1) == 1:
                        q = int(posin[j, NB[i, bb]])
                        if q >= 0:
                            nm = nm | (1 << q)
                # dominated by a label already on the front?
                dom = False
                for s in range(c):
                    if LT[k, j, s] <= t and (LM[k, j, s] & ~nm) == 0 and (LV[k, j, s] == -1 or LV[k, j, s] == nv):
                        dom = True
                        break
                if dom:
                    continue
                # drop the labels the new one dominates
                s = 0
                while s < c:
                    if t <= LT[k, j, s] and (nm & ~LM[k, j, s]) == 0 and (nv == -1 or nv == LV[k, j, s]):
                        c -= 1
                        LT[k, j, s] = LT[k, j, c]
                        LM[k, j, s] = LM[k, j, c]
                        LV[k, j, s] = LV[k, j, c]
                        LI[k, j, s] = LI[k, j, c]
                        LS[k, j, s] = LS[k, j, c]
                    else:
                        s += 1
                if c < B:
                    LT[k, j, c] = t
                    LM[k, j, c] = nm
                    LV[k, j, c] = nv
                    LI[k, j, c] = i
                    LS[k, j, c] = b
                    c += 1
                    continue
                # front full: merge into the label sharing the most memory (ties: the first)
                best_s = 0
                best_sh = -1
                for s in range(c):
                    sh = 0
                    x = int(LM[k, j, s]) & nm
                    for bb in range(g):
                        sh += (x >> bb) & 1
                    if LV[k, j, s] == nv:
                        sh += 1
                    if sh > best_sh:
                        best_sh = sh
                        best_s = s
                if t < LT[k, j, best_s]:
                    LT[k, j, best_s] = t
                    LI[k, j, best_s] = i
                    LS[k, j, best_s] = b
                LM[k, j, best_s] = int(LM[k, j, best_s]) & nm
                if LV[k, j, best_s] != nv:
                    LV[k, j, best_s] = -1
        CNT[k, j] = c
        if c > 0:
            alive += 1
    return alive


_level_jit = _njit(cache=False)(_level_impl) if HAVE_NUMBA else None


def neighbourhoods(CS, g):
    """NB[j] = the g customers closest to j by CS[i, j] + CS[j, i]; posin[j, u] = position of u in NB[j] or -1."""
    m = CS.shape[0]
    g = max(0, min(int(g), m - 1, 30))
    if g == 0:
        return np.zeros((m, 0), dtype=np.int32), np.full((m, m), -1, dtype=np.int8)
    D = np.asarray(CS, dtype=np.float64) + np.asarray(CS, dtype=np.float64).T
    np.fill_diagonal(D, np.inf)
    NB = np.argsort(D, axis=1, kind="stable")[:, :g].astype(np.int32)
    posin = np.full((m, m), -1, dtype=np.int8)
    posin[np.arange(m)[:, None], NB] = np.arange(g, dtype=np.int8)[None, :]
    return NB, posin


def price_ng(C, e_all, l_all, pi_int, L_max, ng=NG, B=BSLOTS, deadline=None, want=WANT, clock=time.monotonic,
             use_jit=True, chunk=256):
    """Exact max profit over ng-routes (+ 2-cycle rule) on customers with pi_int >= 1, or None if stopped by L_max or
    the deadline. Same return dict as cgfleet.price, plus "ng" and "B"."""
    pi_int = np.asarray(pi_int, dtype=np.int64)
    S = np.flatnonzero(pi_int >= 1)
    m = len(S)
    out = {"pstar": None, "levels": 0, "m": int(m), "capped": False, "timeout": False, "walks": [], "ng": int(ng),
           "B": int(B)}
    if m == 0:
        out["pstar"] = 0
        return out
    p = pi_int[S].astype(np.int64)
    e = np.asarray(e_all, dtype=np.float64)[S].copy()
    l = np.asarray(l_all, dtype=np.float64)[S].copy()
    CS = np.asarray(C)[np.ix_(S, S)].astype(np.float64)
    np.fill_diagonal(CS, np.inf)
    NB, posin = neighbourhoods(np.where(np.isfinite(CS), CS, 0.0), ng)
    ok = (e[:, None] + CS) <= (l[None, :] + TOL)
    np.fill_diagonal(ok, False)
    cnt = ok.sum(axis=0)
    pptr = np.zeros(m + 1, dtype=np.int64)
    np.cumsum(cnt, out=pptr[1:])
    pidx = np.ascontiguousarray(np.nonzero(ok.T)[1].astype(np.int32))  # row j of ok.T lists the i with ok[i, j]
    del ok
    kern = _level_jit if (use_jit and HAVE_NUMBA) else _level_impl
    B = int(B)
    cap = min(int(L_max) + 1, max(int(chunk), 2))

    def alloc(nl):
        return (np.full((nl, m, B), np.inf), np.zeros((nl, m, B), dtype=np.int32),
                np.full((nl, m, B), -1, dtype=np.int32), np.full((nl, m, B), -1, dtype=np.int32),
                np.full((nl, m, B), -1, dtype=np.int32), np.zeros((nl, m), dtype=np.int32))

    LT, LM, LV, LI, LS, CNT = alloc(cap)
    best_level = np.zeros(m, dtype=np.int64)
    k = 0
    while True:
        k += 1
        if k > L_max:
            out["capped"] = True
            break
        if deadline is not None and clock() > deadline:
            out["capped"] = out["timeout"] = True
            break
        if k >= cap:
            extra = min(cap, int(L_max) + 1 - cap)
            ext = alloc(extra)
            LT, LM, LV, LI, LS, CNT = [np.concatenate([a, b_], axis=0) for a, b_ in zip((LT, LM, LV, LI, LS, CNT),
                                                                                         ext)]
            cap += extra
        alive = kern(k, CS, e, l, p, NB, posin, pptr, pidx, B, LT, LM, LV, LI, LS, CNT)
        if alive == 0:
            out["pstar"] = int(k - 1)
            break
        best_level[CNT[k] > 0] = k
    out["levels"] = int(k - 1)
    order = np.argsort(-best_level, kind="stable")
    seen = set()
    for j in order[:max(0, want)].tolist():
        kk = int(best_level[j])
        if kk <= 0:
            break
        walk, jj, s = [], j, 0
        while True:
            walk.append(jj)
            i, ss = int(LI[kk, jj, s]), int(LS[kk, jj, s])
            if i < 0:
                break
            kk, jj, s = kk - int(p[jj]), i, ss
        g_ = tuple(int(S[x]) for x in reversed(walk))
        if g_ not in seen:
            seen.add(g_)
            out["walks"].append(list(g_))
    return out


def walk_time_ok(C, e, l, walk):
    """A walk keeps every time window (waiting allowed) and never repeats a customer twice in a row."""
    if not walk:
        return False
    t = float(e[walk[0]])
    if t > l[walk[0]] + TOL:
        return False
    for a, b in zip(walk, walk[1:]):
        if a == b:
            return False
        t = max(t + float(C[a, b]), float(e[b]))
        if t > l[b] + TOL:
            return False
    return True


def elementary(walk):
    """Keep the first visit of every customer (never makes a route late when services are >= 1)."""
    seen, out = set(), []
    for c in walk:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


# ---------------------------------------------------------------- column generation, R2 then NG

def cg_two_phase(C, e, l, n, t_r2, t_ng, t_final, ub=None, init=(), ng=NG, B=BSLOTS, q_price=Q_PRICE,
                 q_final=Q_FINAL, alpha=ALPHA, want=WANT, clock=time.monotonic, say=log, use_jit=True):
    """Farley bounds from column generation: cgfleet's R2 pricing until t_r2 (or convergence), then ng pricing until
    t_ng (or convergence), then final ng evaluations at a finer scale until t_final. Returns best bound per phase with
    certificates."""
    import cgfleet as G
    cols, keys = [], set()

    def add(walk, elem):
        w = elementary(walk) if elem else list(walk)
        key = tuple(sorted(w)) if elem else tuple(sorted(walk))
        if not w or key in keys:
            return False
        keys.add(key)
        idx, cnt = np.unique(np.asarray(w, dtype=np.int64), return_counts=True)
        cols.append((idx, cnt))
        return True

    for i in range(n):
        add([i], False)
    for r in init:
        if r:
            add(list(r), False)
    best = {"r2": Fraction(0), "ng": Fraction(0)}
    cert = {"r2": None, "ng": None}
    stop = {"r2": "time", "ng": "time"}
    phase = "r2"
    centre, p_centre, pest, pure, finer = None, None, 1.0, False, 1
    z_last = {"r2": None, "ng": None}
    pi_rmp, it, hist = None, 0, []
    pest_of = {}

    def pricer(pi_int, L_max, dl, w, ph):
        if ph == "r2":
            return G.price(C, e, l, pi_int, L_max, deadline=dl, want=w, clock=clock)
        return price_ng(C, e, l, pi_int, L_max, ng=ng, B=B, deadline=dl, want=w, clock=clock, use_jit=use_jit)

    def consider(pi, q, L_max, dl, tag, w, ph):
        qs = q / max(pest_of[tag], 1e-9)
        pi_int = np.floor(np.maximum(pi, 0.0) * qs).astype(np.int64)
        r = pricer(pi_int, L_max, dl, w, ph)
        lb = None
        if r["pstar"]:
            lb = Fraction(int(pi_int.sum()), int(r["pstar"]))
            if lb > best[ph]:
                best[ph] = lb
                cert[ph] = {"pi_int": pi_int.tolist(), "pstar": int(r["pstar"]), "sum": int(pi_int.sum()),
                            "scale": qs, "source": tag, "route_set": ph, "ng": int(ng) if ph == "ng" else None,
                            "B": int(B) if ph == "ng" else None}
        return r, lb, qs

    def switch():
        nonlocal phase, centre, p_centre, pest, pure, finer, cols, keys
        phase = "ng"
        centre, p_centre, pure, finer = None, None, False, 1
        old = cols
        cols, keys = [], set()
        for idx, cnt in old:
            add(idx.tolist(), True)
        for i in range(n):
            add([i], True)

    while True:
        lim = t_r2 if phase == "r2" else t_ng
        if clock() >= lim:
            if phase == "r2":
                switch()
                continue
            break
        it += 1
        z, pi_rmp = G.solve_rmp(cols, n)
        z_last[phase] = z
        top = max(best.values())
        if ub is not None and top > 0 and fceil(top) >= ub:
            stop[phase] = "proved"
            break
        if top > 0 and fceil(top) >= math.ceil(z - 1e-6):
            stop[phase] = "lp_closed"
            if phase == "r2":
                switch()
                continue
            break
        if centre is None or pure:
            pi_sep, tag = pi_rmp, phase + "_rmp"
        else:
            pi_sep, tag = alpha * centre + (1 - alpha) * pi_rmp, phase + "_sep"
        pest_of[tag] = pest
        r, lb, qs = consider(pi_sep, q_price * finer, 4 * q_price * finer, lim, tag, want, phase)
        if r["pstar"]:
            pest = r["pstar"] / qs
            if lb is not None and lb >= best[phase] and (centre is None or lb == best[phase]):
                centre, p_centre = pi_sep.copy(), pest
        elif r["capped"] and not r["timeout"]:
            pest *= 4.0
        added = 0
        for w in r["walks"]:
            ww = elementary(w) if phase == "ng" else w
            if float(pi_rmp[ww].sum()) > 1 + 1e-9 and add(w, phase == "ng"):
                added += 1
        hist.append([it, phase, round(z, 4), None if lb is None else round(float(lb), 4),
                     round(float(best[phase]), 4), added, r["m"], r["levels"], tag, round(clock(), 1)])
        if it % 10 == 1 or added == 0:
            say("it %d %s z %.3f lb %s best %.3f cols +%d (%d) m %d levels %d %s" % (
                it, phase, z, None if lb is None else round(float(lb), 3), float(best[phase]), added, len(cols),
                r["m"], r["levels"], tag))
        if added == 0:
            if r["timeout"]:
                if phase == "r2":
                    switch()
                    continue
                break
            if tag.endswith("_sep"):
                pure = True
                continue
            if finer == 1:
                finer = 4
                continue
            stop[phase] = "converged" if phase == "r2" else "stalled"
            if phase == "r2":
                switch()
                continue
            break
        pure, finer = False, 1
    final = []
    cands = [("final_centre", centre, p_centre), ("final_rmp", pi_rmp if phase == "ng" else None, pest)]
    if cert["r2"] is not None:
        pr2 = np.asarray(cert["r2"]["pi_int"], dtype=np.float64)
        cands.append(("final_r2cert", pr2, cert["r2"]["pstar"]))
    for tag, pi, pe in cands:
        if pi is None or clock() > t_final:
            continue
        pest_of[tag] = pe if pe else pest
        r, lb, qs = consider(np.asarray(pi, dtype=np.float64), q_final, int(3 * q_final) + 10, t_final, tag, 0, "ng")
        final.append({"tag": tag, "pstar": r["pstar"], "levels": r["levels"], "m": r["m"],
                      "lb": None if lb is None else float(lb), "timeout": r["timeout"], "capped": r["capped"]})
    top = max(best.values())
    return {"lb": top, "lb_int": fceil(top) if top > 0 else 0, "lb_r2": best["r2"], "lb_ng": best["ng"],
            "z_rmp": z_last, "iterations": it, "columns": len(cols), "stop": stop, "history": hist, "final": final,
            "cert": cert}


def recheck(C, e, l, c, use_jit=True):
    """Re-run the pricing of a certificate; True if P* and the bound reproduce exactly."""
    import cgfleet as G
    if not c:
        return None
    pi = np.asarray(c["pi_int"], dtype=np.int64)
    if c["route_set"] == "r2":
        r = G.price(C, e, l, pi, L_max=int(c["pstar"]) + 1, want=0)
    else:
        r = price_ng(C, e, l, pi, L_max=int(c["pstar"]) + 1, ng=c["ng"], B=c["B"], want=0, use_jit=use_jit)
    return bool(r["pstar"] == c["pstar"] and int(pi.sum()) == c["sum"])


def route_profit_ok(c, routes):
    """Sanity: no real route (0-based customers) may earn more than the certificate's P*."""
    if not c:
        return None
    pi = np.asarray(c["pi_int"], dtype=np.int64)
    worst = max([int(pi[np.asarray(r, dtype=np.int64)].sum()) for r in routes if r] or [0])
    return {"ok": bool(worst <= c["pstar"]), "max_route_profit": worst, "pstar": int(c["pstar"])}
