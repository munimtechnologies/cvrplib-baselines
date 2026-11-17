"""cgfleet: a column-generation lower bound on the number of vehicles for capacity-free VRPTW instances (XLTW-Test).

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

Why. On the capacity-free XLTW-Test instances the best fleets we can find are 1.3 to 9 times the best lower bound we
have (K*, energetic reasoning, `xltwen/`): n2867 needs 29 vehicles in PyVRP against K* = 4. Either the searches are
weak or K* is. A stronger bound answers that, and where it meets a known fleet it proves that fleet minimal.

Bound. Minimum fleet >= the LP  min sum_r x_r  s.t.  sum_r a_ir x_r >= 1 (every customer i),  x >= 0, over any set of
"routes" that contains every feasible route. For any duals pi >= 0 (Farley's bound),

    fleet >= LP >= sum_i pi_i / P*(pi),   P*(pi) = max over the route set of sum_{i in r} a_ir pi_i.

We use integer duals pi_int, so the bound is an exact fraction, and the route set R2 = walks that may revisit a
customer but never twice in a row and never as i -> j -> i (2-cycle elimination), restricted to customers with
pi_int >= 1. Restricting is safe: removing a zero-profit customer from a route never makes the rest late, because travel
times are nearest-integer Euclidean (t_ik + t_kj >= t_ij - 1) and every service time is at least 1; the harness checks
the service times and refuses an instance otherwise.

P*(pi_int) is computed exactly by a dynamic programme over integer profit levels: T[k][j] = earliest service start at
j of an R2 walk ending at j with profit >= k, with the best and second-best predecessor kept for the 2-cycle rule. The
duals come from column generation (HiGHS via scipy, Wentges smoothing); the walks the DP finds are the new columns.
The certificate (pi_int and P*) is written out, so anyone can re-check a bound with one more DP run.

The method is classical (set-covering LP / column generation for fleet minimisation; Farley 1990 bound;
2-cycle elimination, Houck et al. 1980, Kolen et al. 1987). What is new is only the numbers on XLTW-Test.

  python cgfleet.py --data-dir /data --out-dir /out
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
TOL = 1e-6
Q_PRICE = 300       # profit levels per unit of route profit while pricing
Q_FINAL = 1500      # ... for the final, reported bound
ALPHA = 0.5         # Wentges smoothing weight of the stability centre
WANT = 300          # walks recovered per pricing round
PER_1000 = 450.0    # seconds per 1,000 customers for column generation + final bound
CAP_S = 1500.0
FINAL_EXTRA = 300.0
PLAN = ["XLTW-Test-n1048", "XLTW-Test-n1234", "XLTW-Test-n1421", "XLTW-Test-n1514", "XLTW-Test-n1608",
        "XLTW-Test-n1841", "XLTW-Test-n1934", "XLTW-Test-n2028", "XLTW-Test-n2214", "XLTW-Test-n2867"]
# best valid PyVRP fleets at the full limit T(n) (xltwfull/, nbrm/); others use xltwen vehicles_a (T(n)/30)
BEST = {"XLTW-Test-n1234": 33, "XLTW-Test-n1421": 65, "XLTW-Test-n1608": 108, "XLTW-Test-n1841": 25}
T0 = time.time()


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def fceil(x):
    """ceil of a Fraction, exactly."""
    return -((-x.numerator) // x.denominator)


# ---------------------------------------------------------------- pricing: exact P* over R2 walks by profit levels

def price(C, e_all, l_all, pi_int, L_max, deadline=None, want=WANT, clock=time.monotonic):
    """C: n x n array, C[i, j] = s_i + t_ij. e_all / l_all: earliest / latest service start of each customer (depot legs
    included). pi_int: integer duals >= 0. Returns {"pstar": exact max profit of an R2 walk, or None if the DP was
    stopped by L_max or the deadline, "levels", "m", "capped", "timeout", "walks": up to `want` walks (lists of
    customer indices), best first}."""
    pi_int = np.asarray(pi_int, dtype=np.int64)
    S = np.flatnonzero(pi_int >= 1)
    m = len(S)
    out = {"pstar": None, "levels": 0, "m": int(m), "capped": False, "timeout": False, "walks": []}
    if m == 0:
        out["pstar"] = 0
        return out
    p = pi_int[S]
    e = np.asarray(e_all, dtype=np.float64)[S]
    l = np.asarray(l_all, dtype=np.float64)[S]
    CS = np.asarray(C)[np.ix_(S, S)].astype(np.float64)
    np.fill_diagonal(CS, np.inf)  # never the same customer twice in a row
    ar = np.arange(m)
    Ab = np.full((L_max + 1, m), np.inf)
    Abi = np.full((L_max + 1, m), -1, dtype=np.int32)
    As = np.full((L_max + 1, m), np.inf)
    Asi = np.full((L_max + 1, m), -1, dtype=np.int32)
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
        idx = k - p
        start = idx <= 0
        ii = np.where(start, 0, idx)
        T1 = np.where(start, e, np.maximum(Ab[ii, ar], e))
        T2 = np.where(start, np.inf, np.maximum(As[ii, ar], e))
        P1 = np.where(start, -1, Abi[ii, ar])
        T1[T1 > l + TOL] = np.inf
        T2[T2 > l + TOL] = np.inf
        F = np.flatnonzero(np.isfinite(T1))
        if len(F) == 0:
            out["pstar"] = int(k - 1)
            break
        best_level[F] = k
        # label of i offered to j: the best one, unless its predecessor is j (then the best with another predecessor)
        src = np.where(P1[F][:, None] == ar[None, :], T2[F][:, None], T1[F][:, None])
        M = src + CS[F]
        del src
        b = np.argmin(M, axis=0)
        Ab[k] = M[b, ar]
        Abi[k] = F[b]
        M[b, ar] = np.inf
        s = np.argmin(M, axis=0)
        As[k] = M[s, ar]
        Asi[k] = F[s]
        del M
    out["levels"] = int(k - 1)

    def pred1(kk, j):
        return -1 if kk <= p[j] else int(Abi[kk - p[j], j])

    order = np.argsort(-best_level, kind="stable")
    seen = set()
    for j in order[:max(0, want)].tolist():
        kk = int(best_level[j])
        if kk <= 0:
            break
        walk, w, jj = [j], 1, j
        while kk > p[jj]:
            kp = kk - int(p[jj])
            i = int(Abi[kp, jj] if w == 1 else Asi[kp, jj])
            if i < 0:
                raise RuntimeError("walk recovery hit an empty label")
            w = 2 if pred1(kp, i) == jj else 1
            walk.append(i)
            kk, jj = kp, i
        if w != 1:
            raise RuntimeError("walk recovery ended on a second-best start label")
        g = tuple(int(S[x]) for x in reversed(walk))
        if g not in seen:
            seen.add(g)
            out["walks"].append(list(g))
    return out


def walk_ok(C, e, l, walk):
    """Plain check that a walk keeps every time window (waiting allowed) and is in R2."""
    for a, b in zip(walk, walk[1:]):
        if a == b:
            return False
    for a, c in zip(walk, walk[2:]):
        if a == c:
            return False
    t = float(e[walk[0]])
    if t > l[walk[0]] + TOL:
        return False
    for a, b in zip(walk, walk[1:]):
        t = max(t + float(C[a, b]), float(e[b]))
        if t > l[b] + TOL:
            return False
    return True


# ---------------------------------------------------------------- column generation

def solve_rmp(cols, n):
    from scipy.optimize import linprog
    from scipy.sparse import csc_matrix
    indptr = np.zeros(len(cols) + 1, dtype=np.int64)
    np.cumsum([len(c[0]) for c in cols], out=indptr[1:])
    ind = np.concatenate([c[0] for c in cols])
    val = np.concatenate([c[1] for c in cols]).astype(np.float64)
    A = csc_matrix((val, ind, indptr), shape=(n, len(cols)))
    res = linprog(np.ones(len(cols)), A_ub=-A, b_ub=-np.ones(n), bounds=(0, None), method="highs")
    if res.status != 0:
        raise RuntimeError("RMP: " + str(res.message))
    pi = np.maximum(-np.asarray(res.ineqlin.marginals, dtype=np.float64), 0.0)
    return float(res.fun), pi


def cg_bound(C, e, l, n, deadline, final_deadline, ub=None, init=(), q_price=Q_PRICE, q_final=Q_FINAL,
             alpha=ALPHA, want=WANT, clock=time.monotonic, say=log):
    """Column generation on the covering LP; returns a dict with the best exact Farley bound and its certificate."""
    cols, keys = [], set()

    def add(walk):
        key = tuple(sorted(walk))
        if key in keys:
            return False
        keys.add(key)
        idx, cnt = np.unique(np.asarray(walk, dtype=np.int64), return_counts=True)
        cols.append((idx, cnt))
        return True

    for i in range(n):
        add([i])
    for r in init:
        if r:
            add(list(r))
    best, cert, centre, p_centre = Fraction(0), None, None, None
    pest, z, it, stop, pure, finer = 1.0, None, 0, "time", False, 1
    hist = []
    pi_rmp = None

    def consider(pi, q, L_max, dl, tag, w):
        nonlocal best, cert
        qs = q / max(pest_of[tag], 1e-9)
        pi_int = np.floor(pi * qs).astype(np.int64)
        r = price(C, e, l, pi_int, L_max, deadline=dl, want=w, clock=clock)
        lb = None
        if r["pstar"]:
            lb = Fraction(int(pi_int.sum()), int(r["pstar"]))
            if lb > best:
                best = lb
                cert = {"pi_int": pi_int.tolist(), "pstar": int(r["pstar"]), "sum": int(pi_int.sum()),
                        "scale": qs, "source": tag}
        return r, lb, qs

    pest_of = {}
    while clock() < deadline:
        it += 1
        z, pi_rmp = solve_rmp(cols, n)
        if ub is not None and fceil(best) >= ub:
            stop = "proved"
            break
        if best > 0 and fceil(best) >= math.ceil(z - 1e-6):
            stop = "lp_closed"
            break
        if centre is None or pure:
            pi_sep, tag = pi_rmp, "rmp"
        else:
            pi_sep, tag = alpha * centre + (1 - alpha) * pi_rmp, "sep"
        pest_of[tag] = pest
        r, lb, qs = consider(pi_sep, q_price * finer, 4 * q_price * finer, deadline, tag, want)
        if r["pstar"]:
            pest = r["pstar"] / qs
            if lb is not None and lb >= best and (centre is None or lb == best):
                centre, p_centre = pi_sep.copy(), pest
        elif r["capped"] and not r["timeout"]:
            pest *= 4.0
        added = 0
        for w in r["walks"]:
            if float(pi_rmp[w].sum()) > 1 + 1e-9 and add(w):
                added += 1
        hist.append([it, round(z, 4), None if lb is None else round(float(lb), 4), round(float(best), 4), added,
                     r["m"], r["levels"], tag, round(clock(), 1)])
        if it % 10 == 1 or added == 0:
            say("it %d z %.3f lb %s best %.3f cols +%d (%d) m %d levels %d %s" % (
                it, z, None if lb is None else round(float(lb), 3), float(best), added, len(cols), r["m"],
                r["levels"], tag))
        if added == 0:
            if r["timeout"]:
                break
            if tag == "sep":
                pure = True          # mispricing: price at the RMP duals themselves next
                continue
            if finer == 1:
                finer = 4            # rounding may hide a column: price once on a 4x finer scale
                continue
            stop = "converged"
            break
        pure, finer = False, 1
    # final, finer bound at the centre and at the last RMP duals
    final = []
    for tag, pi, pe in (("final_centre", centre, p_centre), ("final_rmp", pi_rmp, pest)):
        if pi is None or clock() > final_deadline:
            continue
        pest_of[tag] = pe if pe else pest
        r, lb, qs = consider(pi, q_final, int(3 * q_final) + 10, final_deadline, tag, 0)
        final.append({"tag": tag, "pstar": r["pstar"], "levels": r["levels"], "m": r["m"],
                      "lb": None if lb is None else float(lb), "timeout": r["timeout"], "capped": r["capped"]})
    return {"lb": best, "lb_int": fceil(best) if best > 0 else 0, "z_rmp": z, "iterations": it, "columns": len(cols),
            "stop": stop, "history": hist, "final": final, "cert": cert}


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


def one(path, name, ref, cert_dir, per_1000=PER_1000, cap_s=CAP_S, final_extra=FINAL_EXTRA):
    import tmatch as TM
    import xltwlb as X
    t_start = time.monotonic()
    with open(path, encoding="utf-8") as f:
        inst = X.parse_any(f.read())
    I = TM.Inst(inst)
    n = I.n
    rf = ref.get(name) or {}
    ubs = [x for x in (rf.get("vehicles_a"), BEST.get(name)) if x is not None]
    ub = min(ubs) if ubs else None
    budget = min(cap_s, per_1000 * n / 1000.0)
    rec = {"instance": name, "customers": n, "capfree": I.capfree, "kstar": rf.get("kstar"), "ub": ub,
           "budget_s": round(budget, 1), "service_min": float(I.s.min()), "unservable": I.unservable}
    if not I.capfree:
        rec["error"] = "capacity binds: not in this study"
        return rec
    if I.unservable:
        rec["error"] = "instance has customers no route can serve"
        return rec
    if float(I.s.min()) < 1:
        rec["error"] = "a service time is below 1: skipping zero-profit customers is not proven safe"
        return rec
    ch, _ = TM.match_chains(I, I.e.copy(), np.arange(n))
    init = TM.routes_of(I, ch)
    ch2, _ = TM.match_chains(I, I.l.copy(), np.arange(n))
    init2 = TM.routes_of(I, ch2)
    rec["init_routes"] = [len(init), len(init2)]
    deadline = t_start + 0.75 * budget
    res = cg_bound(I.C, I.e, I.l, n, deadline, t_start + budget + final_extra, ub=ub, init=init + init2)
    rec.update({k: res[k] for k in ("lb_int", "z_rmp", "iterations", "columns", "stop", "final")})
    rec["lb"] = float(res["lb"])
    rec["lb_fraction"] = "%d/%d" % (res["lb"].numerator, res["lb"].denominator)
    rec["history"] = res["history"]
    k = rec["kstar"]
    rec["above_kstar"] = bool(k is not None and rec["lb_int"] > k)
    rec["gap_closed"] = (round((rec["lb_int"] - k) / float(ub - k), 4)
                         if (k is not None and ub is not None and ub > k) else None)
    rec["proved"] = bool(ub is not None and rec["lb_int"] >= ub)
    rec["above_ub"] = bool(ub is not None and rec["lb_int"] > ub)
    rec["converged"] = bool(res["z_rmp"] is not None and rec["lb_int"] >= math.ceil(res["z_rmp"] - 1e-6))
    if res["cert"] is not None:
        os.makedirs(cert_dir, exist_ok=True)
        c = dict(res["cert"])
        c.update({"instance": name, "bound": rec["lb_fraction"], "fleet_at_least": rec["lb_int"],
                  "route_set": "R2 walks over customers with pi_int >= 1 (no immediate repeat, no i-j-i)",
                  "solver": "cgfleet " + VERSION})
        with open(os.path.join(cert_dir, name + ".json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(c, f)
    rec["seconds"] = round(time.monotonic() - t_start, 1)
    rec["peak_gb"] = peak_gb()
    return rec


def tally(recs):
    ok = [r for r in recs if not r.get("error")]
    return {
        "instances_done": len(ok),
        "errors": [r["instance"] for r in recs if r.get("error")],
        "above_ub": [r["instance"] for r in ok if r.get("above_ub")],
        "above_kstar": [r["instance"] for r in ok if r.get("above_kstar")],
        "half_gap": [r["instance"] for r in ok if (r.get("gap_closed") or 0) >= 0.5],
        "proved": [r["instance"] for r in ok if r.get("proved")],
        "converged": [r["instance"] for r in ok if r.get("converged")],
        "service1_above_kstar": [r["instance"] for r in ok if r.get("above_kstar") and r["service_min"] == 1.0
                                 and r["instance"] in ("XLTW-Test-n1048", "XLTW-Test-n1514", "XLTW-Test-n2867")],
        "sum_lb": sum(r["lb_int"] for r in ok),
        "sum_kstar": sum(r["kstar"] for r in ok if r.get("kstar") is not None),
        "sum_ub": sum(r["ub"] for r in ok if r.get("ub") is not None),
        "peak_gb": max([r["peak_gb"] for r in ok if r.get("peak_gb") is not None] or [None]) if ok else None,
    }


def write_md(path, res):
    t = res["tally"]
    L = ["# cgfleet on XLTW-Test: column-generation fleet bounds on capacity-free instances", "",
         "Pre-registered in PREREG.md. Solver %s. Bound = ceil(sum pi_int / P*), certificates in cert/." % VERSION, "",
         "Tally: `%s`" % json.dumps(t), "",
         "| instance | n | K* | cgfleet bound | LP bound (fraction) | RMP value | best known fleet | gap closed | "
         "proved | stop | iterations | columns | s | peak GB |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["instances"]:
        if r.get("error"):
            L.append("| %s | error: %s |||||||||||||" % (r["instance"], r["error"].strip().splitlines()[-1]))
            continue
        L.append("| %s | %d | %s | %d | %.3f | %s | %s | %s | %s | %s | %d | %d | %s | %s |" % (
            r["instance"], r["customers"], r["kstar"], r["lb_int"], r["lb"],
            None if r["z_rmp"] is None else round(r["z_rmp"], 3), r["ub"], r["gap_closed"], r["proved"], r["stop"],
            r["iterations"], r["columns"], r["seconds"], r["peak_gb"]))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    out = os.path.join(a.out_dir, "cgfleet")
    os.makedirs(out, exist_ok=True)
    ref = load_ref(os.path.join(HERE, "xltwen-results.json"))
    files = find_files(a.data_dir)
    names = [x for x in a.only.split(",") if x] or PLAN
    res = {"solver": "cgfleet " + VERSION, "python": sys.version.split()[0], "numpy": np.__version__,
           "settings": {"q_price": Q_PRICE, "q_final": Q_FINAL, "alpha": ALPHA, "want": WANT, "per_1000": PER_1000,
                        "cap_s": CAP_S, "final_extra": FINAL_EXTRA},
           "ref_instances": len(ref), "files_found": len(files), "plan": names, "instances": []}
    try:
        import scipy
        res["scipy"] = scipy.__version__
    except ImportError:
        res["scipy"] = None
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
        log(json.dumps({k: rec.get(k) for k in ("instance", "customers", "kstar", "lb_int", "lb", "z_rmp", "ub",
                                               "stop", "iterations", "seconds", "peak_gb", "error")}))
    res["tally"] = tally(res["instances"])
    with open(res_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1)
    write_md(os.path.join(out, "results.md"), res)
    log("TALLY " + json.dumps(res["tally"]))


if __name__ == "__main__":
    main()
