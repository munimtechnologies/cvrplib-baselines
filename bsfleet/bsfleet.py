"""bsfleet: route-level fleet lower bounds on the busy stretches of XLTW-Test (ng-route column generation).

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

Why. stfleet (../stfleet/) showed that on every capacity-free XLTW-Test instance the binding part of the day is a busy
stretch [t1, t2], never the whole day, and that its spanning-tree bound closes at most 1/6 of the gap between the
best lower bound and the best fleet we know. Route-level bounds (column generation over whole feasible routes) are
much stronger in general, but on 1,000-10,000 customers their dense pricing does not fit. Restricting them to the
customers of a busy stretch makes them small enough to run.

Bound. Let S be the customers whose whole service must lie inside [t1, t2] (stfleet's set: e_i >= t1 and
l_i + s_i <= t2, windows tightened by the depot's hours). Every vehicle of a feasible solution visits some customers
of S in some order; dropping the customers outside S never makes it late (travel times are nearest-integer Euclidean,
so t_ij <= t_ik + 1 + t_kj, and every service time is at least 1, checked per instance). So the solution's routes,
cut to S, are elementary time-feasible routes over S that cover S, and

    fleet >= min number of such routes covering S >= sum_i pi_i / P*(pi)   for any duals pi >= 0 (Farley),

where P* is the best profit of an ng-route (a relaxation that contains every elementary route). ngfleet 0.1.0 computes
P* exactly for integer duals and runs the column generation (R2 walks first, then ng-routes); this module only builds
S, the sub-instance and a greedy cover of S (an upper bound for the S-problem, used as start columns and as a sanity
check: no bound may exceed it). Every certificate (t1, t2, S, pi_int, P*) is re-checked by one more exact pricing run.

  python bsfleet.py --data-dir /data --out-dir /out
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

import mstfleet as M  # noqa: E402  (mstfleet 0.1.0: Inst, interval_set, travel_lb, find_files, peak_gb)
import ngfleet as N   # noqa: E402  (ngfleet 0.1.0: cg_two_phase, recheck, route_profit_ok, walk_time_ok, fceil)

VERSION = "0.1.0"
TOL = 1e-6
M_MAX = 1500                 # largest stretch (customers) priced
MAX_STRETCHES = 2            # per instance: stfleet's certificate stretch, then the whole day, then refined ones
BASE_S, PER_1000, CAP_S = 60.0, 500.0, 900.0   # column-generation seconds per stretch
R2_SHARE = 0.35
FINAL_S = 120.0
GLOBAL_S = 4.5 * 3600.0
T0 = time.time()


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def budget(m):
    return min(CAP_S, BASE_S + PER_1000 * m / 1000.0)


# ---------------------------------------------------------------- the sub-instance of one stretch

def sub_arrays(I, S):
    """C[i, j] = s_i + t_ij (t = mstfleet.travel_lb, never above the challenge's rounding), e, l of the customers S."""
    S = np.asarray(S, dtype=np.int64)
    xy = I.xy[S]
    dx = xy[:, 0][:, None] - xy[:, 0][None, :]
    dy = xy[:, 1][:, None] - xy[:, 1][None, :]
    C = np.asarray(I.s[S], dtype=np.float64)[:, None] + M.travel_lb(dx, dy)
    del dx, dy
    np.fill_diagonal(C, 0.0)  # never used: the pricing forbids a customer twice in a row
    return C, np.asarray(I.e[S], dtype=np.float64).copy(), np.asarray(I.l[S], dtype=np.float64).copy()


def greedy_routes(C, e, l):
    """A cover of the sub-instance by elementary time-feasible routes (customers by earliest start; each joins the open
    route where it can start earliest, else opens a new one). Its size is an upper bound for the S-problem."""
    m = len(e)
    if m == 0:
        return []
    order = np.lexsort((l, e))
    routes, ends, times = [], [], []
    for j in order.tolist():
        if ends:
            ea = np.asarray(ends, dtype=np.int64)
            a = np.maximum(np.asarray(times) + C[ea, j], e[j])
            ok = a <= l[j] + TOL
            if ok.any():
                r = int(np.flatnonzero(ok)[np.argmin(a[ok])])
                routes[r].append(j)
                ends[r] = j
                times[r] = float(a[r])
                continue
        routes.append([j])
        ends.append(j)
        times.append(float(e[j]))
    return routes


def stretches(rec, I, m_max=M_MAX, k=MAX_STRETCHES):
    """Candidate stretches from one stfleet record: its certificate stretch, its other refined stretches (largest
    first), then the whole day; each with stfleet's own K there. Duplicates and stretches above m_max dropped."""
    out, seen = [], set()

    def add(t1, t2, m, K, src):
        key = (float(t1), float(t2))
        if key in seen or m is None or m < 2 or m > m_max:
            return
        seen.add(key)
        out.append({"t1": float(t1), "t2": float(t2), "m_stfleet": int(m), "K_stfleet": K, "from": src})

    c = rec.get("cert") or {}
    if c:
        add(c.get("t1"), c.get("t2"), c.get("m"), rec.get("bound"), "cert")
    wd = rec.get("whole_day") or []
    if wd:
        add(I.D0, I.B0, I.n, max(int(w["K"]) for w in wd), "whole_day")
    ref = sorted(rec.get("refined") or [], key=lambda r: -int(r.get("m") or 0))
    for r in ref:
        Ks = [x for x in (r.get("K_scan"), r.get("K_mu"), r.get("K_hk")) if x is not None]
        add(r["t1"], r["t2"], r.get("m"), max(Ks) if Ks else None, "refined")
    return out[:k]


def bound_stretch(I, t1, t2, ub=None, budget_fn=budget, final_s=FINAL_S, q_price=N.Q_PRICE, q_final=N.Q_FINAL,
                  clock=time.monotonic):
    """Route-level fleet bound over the customers of [t1, t2]. Returns a record with the certificate (or none)."""
    t0 = clock()
    S = M.interval_set(I, t1, t2)
    m = int(len(S))
    rec = {"t1": float(t1), "t2": float(t2), "m": m}
    if m < 2:
        rec["error"] = "fewer than 2 customers in the stretch"
        return rec, None
    C, e, l = sub_arrays(I, S)
    routes = greedy_routes(C, e, l)
    rec["greedy"] = len(routes)
    rec["greedy_ok"] = bool(all(N.walk_time_ok(C, e, l, r) for r in routes)
                            and sorted(x for r in routes for x in r) == list(range(m)))
    b = budget_fn(m)
    rec["budget_s"] = round(b, 1)
    res = N.cg_two_phase(C, e, l, m, t0 + R2_SHARE * b, t0 + b, t0 + b + final_s, ub=ub, init=routes,
                         q_price=q_price, q_final=q_final, say=lambda s: None)
    rec["lb_r2"] = float(res["lb_r2"])
    rec["lb_ng"] = float(res["lb_ng"])
    rec["z_rmp"] = res["z_rmp"]
    rec["stop"] = res["stop"]
    rec["iterations"] = res["iterations"]
    rec["columns"] = res["columns"]
    rec["final"] = res["final"]
    ints, best_cert = {}, None
    for ph in ("r2", "ng"):
        c = res["cert"][ph]
        if c is None:
            ints[ph] = None
            rec["recheck_" + ph] = None
            continue
        rc = N.recheck(C, e, l, c)
        rp = N.route_profit_ok(c, routes)
        good = bool(rc and rp is not None and rp["ok"])
        rec["recheck_" + ph] = rc
        rec["route_check_" + ph] = rp
        ints[ph] = N.fceil(res["lb_" + ph]) if good else None
        if good and (best_cert is None or ints[ph] > best_cert["fleet_at_least"]):
            lb = res["lb_" + ph]
            best_cert = dict(c)
            best_cert.update({"t1": float(t1), "t2": float(t2), "m": m,
                              "customers_1based": [int(x) + 1 for x in S.tolist()],
                              "fleet_at_least": int(ints[ph]), "bound": "%d/%d" % (lb.numerator, lb.denominator)})
    rec["bound_r2"], rec["bound_ng"] = ints["r2"], ints["ng"]
    vals = [v for v in ints.values() if v is not None]
    rec["bound"] = max(vals) if vals else None
    rec["unverified"] = bool(any(rec.get("recheck_" + ph) is False for ph in ("r2", "ng"))
                             or any((rec.get("route_check_" + ph) or {}).get("ok") is False for ph in ("r2", "ng")))
    rec["above_greedy"] = bool(rec["bound"] is not None and rec["bound"] > rec["greedy"])
    rec["solved"] = bool(rec["bound"] is not None and rec["bound"] == rec["greedy"])
    rec["seconds"] = round(clock() - t0, 1)
    return rec, best_cert


# ---------------------------------------------------------------- study harness

def one(path, name, strec, cert_dir, m_max=M_MAX, deadline=None, budget_fn=budget, final_s=FINAL_S,
        q_price=N.Q_PRICE, q_final=N.Q_FINAL):
    import xltwlb as X
    with open(path, encoding="utf-8") as fh:
        inst = X.parse_any(fh.read())
    inst.setdefault("name", name)
    I = M.Inst(inst)
    I.name = name
    k, st, ub = strec.get("kstar"), strec.get("bound"), strec.get("ub")
    rec = {"instance": name, "customers": I.n, "capfree": I.capfree, "kstar": k, "stfleet": st, "ub": ub}
    if not I.capfree:
        rec["error"] = "capacity binds: not in this study"
        return rec
    if I.unservable:
        rec["error"] = "instance has customers no route can serve"
        return rec
    if I.service_min < 1:
        rec["error"] = "a service time is below 1: dropping customers from a route is not proven safe"
        return rec
    if not I.integral:
        rec["error"] = "non-integral data"
        return rec
    cands = stretches(strec, I, m_max=m_max)
    rec["stretches"] = []
    certs = []
    for c in cands:
        if deadline is not None and time.monotonic() > deadline:
            c["error"] = "global time budget used"
            rec["stretches"].append(c)
            continue
        try:
            r, cert = bound_stretch(I, c["t1"], c["t2"], ub=ub, budget_fn=budget_fn, final_s=final_s,
                                    q_price=q_price, q_final=q_final)
        except Exception:  # noqa: BLE001 - recorded
            r, cert = {"error": traceback.format_exc()}, None
        c.update(r)
        c["m_match"] = bool(c.get("m") == c["m_stfleet"]) if c.get("m") is not None else None
        c["above_stfleet"] = bool(c.get("bound") is not None and c.get("K_stfleet") is not None
                                  and c["bound"] > c["K_stfleet"])
        rec["stretches"].append(c)
        if cert is not None:
            certs.append(cert)
        log("%s [%g, %g] m %s: greedy %s, R2 %s, ng %s, bound %s (stfleet %s), %ss" % (
            name, c["t1"], c["t2"], c.get("m"), c.get("greedy"), c.get("bound_r2"), c.get("bound_ng"),
            c.get("bound"), c.get("K_stfleet"), c.get("seconds")))
    done = [s for s in rec["stretches"] if not s.get("error") and s.get("bound") is not None]
    rec["bs"] = max([s["bound"] for s in done] or [None]) if done else None
    before = max([x for x in (k, st) if x is not None] or [0])
    rec["best_before"] = before
    rec["best_after"] = max(before, rec["bs"] or 0)
    rec["above_best"] = bool(rec["bs"] is not None and rec["bs"] > before)
    rec["above_ub"] = bool(ub is not None and rec["best_after"] > ub)
    rec["proved"] = bool(ub is not None and rec["best_after"] >= ub)
    rec["gap_closed"] = (round((rec["best_after"] - before) / float(ub - before), 4)
                         if (ub is not None and ub > before) else None)
    if certs:
        best = max(certs, key=lambda c: c["fleet_at_least"])
        best.update({"instance": name, "solver": "bsfleet %s on ngfleet %s" % (VERSION, N.VERSION),
                     "rule": "fleet >= ceil(sum(pi_int) / pstar); pstar = exact max profit of an ng-route (route_set "
                             "'ng', neighbourhood ng, front B) or R2 walk (route_set 'r2') over the customers listed, "
                             "C[i, j] = s_i + floor(d_ij + 0.5 - 1e-9), windows tightened by the depot's hours"})
        os.makedirs(cert_dir, exist_ok=True)
        with open(os.path.join(cert_dir, name + ".json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(best, fh)
    rec["peak_gb"] = M.peak_gb()
    return rec


def plan(st_res, m_max=M_MAX):
    """stfleet instances (no error) with at least one stretch of at most m_max customers, smallest stretch first."""
    rows = []
    for r in st_res.get("instances", []):
        if r.get("error"):
            continue
        ms = [x.get("m") for x in (r.get("refined") or []) if x.get("m")]
        c = r.get("cert") or {}
        if c.get("m"):
            ms.append(c["m"])
        if r.get("customers") and r["customers"] <= m_max:
            ms.append(r["customers"])
        ms = [int(x) for x in ms if 2 <= int(x) <= m_max]
        if ms:
            rows.append((min(ms), r["instance"]))
    return [n for _, n in sorted(rows)]


def tally(recs):
    ok = [r for r in recs if not r.get("error") and r.get("bs") is not None]
    sts = [s for r in recs for s in (r.get("stretches") or []) if not s.get("error") and s.get("bound") is not None]
    with_ub = [r for r in ok if r.get("ub") is not None]
    gaps = [r["gap_closed"] for r in ok if r.get("gap_closed") is not None]
    return {
        "instances": len(recs),
        "done": len(ok),
        "errors": [r["instance"] for r in recs if r.get("error")],
        "stretch_errors": sum(1 for r in recs for s in (r.get("stretches") or []) if s.get("error")),
        "stretches_done": len(sts),
        "unverified": [r["instance"] for r in recs for s in (r.get("stretches") or []) if s.get("unverified")],
        "greedy_bad": [r["instance"] for r in recs for s in (r.get("stretches") or [])
                       if s.get("greedy_ok") is False],
        "above_greedy": [r["instance"] for r in recs for s in (r.get("stretches") or []) if s.get("above_greedy")],
        "above_ub": [r["instance"] for r in ok if r.get("above_ub")],
        "m_mismatch": [r["instance"] for r in recs for s in (r.get("stretches") or []) if s.get("m_match") is False],
        "stretch_above_stfleet": sum(1 for s in sts if s.get("above_stfleet")),
        "stretch_solved": sum(1 for s in sts if s.get("solved")),
        "ng_int_gain": sum(1 for s in sts if s.get("bound_ng") is not None and s.get("bound_r2") is not None
                           and s["bound_ng"] > s["bound_r2"]),
        "above_best": [r["instance"] for r in ok if r.get("above_best")],
        "proved": [r["instance"] for r in ok if r.get("proved")],
        "n1048_bs": next((r["bs"] for r in ok if r["instance"] == "XLTW-Test-n1048"), None),
        "sum_before": sum(r["best_before"] for r in with_ub),
        "sum_after": sum(r["best_after"] for r in with_ub),
        "sum_ub": sum(r["ub"] for r in with_ub),
        "gap_closed_max": max(gaps) if gaps else None,
        "numba": N.HAVE_NUMBA,
        "peak_gb": max([r["peak_gb"] for r in recs if r.get("peak_gb") is not None] or [None]),
    }


def write_md(path, res):
    t = res["tally"]
    L = ["# bsfleet on XLTW-Test: route-level fleet bounds on the busy stretches", "",
         "Pre-registered in PREREG.md. bsfleet %s on ngfleet %s. Certificates in cert/." % (VERSION, N.VERSION), "",
         "Tally: `%s`" % json.dumps(t), "",
         "| instance | n | K* | stfleet | best known fleet | stretch | from | customers | greedy cover | stfleet K "
         "there | R2 bound | ng bound | z_rmp (ng) | s |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["instances"]:
        if r.get("error"):
            L.append("| %s | error: %s ||||||||||||" % (r["instance"], str(r["error"]).strip().splitlines()[-1]))
            continue
        for s in r.get("stretches") or []:
            if s.get("error"):
                L.append("| %s | %s | | | | [%g, %g] | %s | error: %s ||||||" % (
                    r["instance"], r["customers"], s["t1"], s["t2"], s.get("from"),
                    str(s["error"]).strip().splitlines()[-1]))
                continue
            z = (s.get("z_rmp") or {}).get("ng")
            L.append("| %s | %s | %s | %s | %s | [%g, %g] | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                r["instance"], r["customers"], r["kstar"], r["stfleet"], r["ub"], s["t1"], s["t2"], s.get("from"),
                s.get("m"), s.get("greedy"), s.get("K_stfleet"), s.get("bound_r2"), s.get("bound_ng"),
                None if z is None else round(z, 2), s.get("seconds")))
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--stfleet", default=os.path.join(HERE, "stfleet-results.json"))
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    start = time.monotonic()
    out = os.path.join(a.out_dir, "bsfleet")
    cert_dir = os.path.join(out, "cert")
    os.makedirs(out, exist_ok=True)
    with open(a.stfleet, encoding="utf-8") as fh:
        st_res = json.load(fh)
    by = {r["instance"]: r for r in st_res.get("instances", [])}
    files = M.find_files(a.data_dir)
    names = [x for x in a.only.split(",") if x] or plan(st_res)
    man = {}
    mp = os.path.join(HERE, "manifest.json")
    if os.path.exists(mp):
        with open(mp, encoding="utf-8") as fh:
            man = json.load(fh)
    res = {"solver": "bsfleet " + VERSION, "ngfleet": N.VERSION, "mstfleet": M.VERSION,
           "python": sys.version.split()[0], "numpy": np.__version__, "numba": N.HAVE_NUMBA,
           "settings": {"m_max": M_MAX, "max_stretches": MAX_STRETCHES, "budget": [BASE_S, PER_1000, CAP_S],
                        "r2_share": R2_SHARE, "final_s": FINAL_S, "global_s": GLOBAL_S, "ng": N.NG, "B": N.BSLOTS,
                        "q_price": N.Q_PRICE, "q_final": N.Q_FINAL},
           "manifest": man, "files_found": len(files), "plan": names, "instances": []}
    res_path = os.path.join(out, "results.json")
    log("plan: %d instances (numba %s): %s" % (len(names), N.HAVE_NUMBA, ", ".join(names)))
    for name in names:
        if name not in files or name not in by:
            rec = {"instance": name, "error": "instance file or stfleet record not found"}
        elif time.monotonic() - start > GLOBAL_S:
            rec = {"instance": name, "error": "global time budget used"}
        else:
            try:
                rec = one(files[name], name, by[name], cert_dir, deadline=start + GLOBAL_S)
            except Exception:  # noqa: BLE001 - recorded
                rec = {"instance": name, "error": traceback.format_exc()}
        res["instances"].append(rec)
        res["tally"] = tally(res["instances"])
        with open(res_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(res, fh, indent=1)
        log(json.dumps({k: rec.get(k) for k in ("instance", "customers", "kstar", "stfleet", "bs", "ub",
                                               "peak_gb", "error")}))
    res["tally"] = tally(res["instances"])
    with open(res_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(res, fh, indent=1)
    write_md(os.path.join(out, "results.md"), res)
    log("TALLY " + json.dumps(res["tally"]))


if __name__ == "__main__":
    main()
