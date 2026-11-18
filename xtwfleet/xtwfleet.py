"""xtwfleet: are the best known fleets of CVRPLib's XTW set minimal? Fleet lower bounds against a live leaderboard.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

Why. CVRPLib added XTW on 2026-11-02: 100 VRPTW instances (100-1,000 customers) from the same authors and generator
family as the XLTW challenge set, ranked by fewest vehicles first, then distance. Several strong teams have improved
its best known solutions (BKS) every day since; on XTW-n1001 the fleet went 39 -> 37 -> 36 and has stayed at 36 since
2026-11-07. CVRPLib marks 22 XTW solutions as proven optimal and shows no fleet lower bounds for the rest.

On the capacity-free XLTW-Test instances our own fleets are 1.3-9x the best lower bound we have, and we cannot tell
whether our searches or our bounds are to blame. XTW answers that from the other side: its BKS fleets come from many
strong independent searches. If our bounds reach them, the bounds are tight on this generator family (so the XLTW gap
is our searches') and every match is a certificate that a live BKS fleet is the minimum. If they stay far below,
the bounds are what is weak.

Bounds (each valid for the capacitated VRPTW, because dropping capacity only relaxes the problem):
  * cap:     ceil(total demand / capacity);
  * stfleet: space-time spanning-tree bound (cvrplib-baselines stfleet/, capacity ignored), exact re-check;
  * cgfleet: column-generation (Farley) bound over 2-cycle-free walks (cvrplib-baselines cgfleet/, capacity ignored),
             started from the BKS routes; its certificate is re-checked by one more exact pricing run;
  * cgcap:   NEW here, for instances where capacity can bind. For integer duals pi >= 0 every feasible route r has
             pi(r) <= P_time(pi) (cgfleet's exact walk pricing) and pi(r) <= P_knap(pi) (0/1 knapsack of pi under the
             vehicle capacity), so fleet >= sum(pi) / min(P_time, P_knap) (Farley's argument with both relaxations).
             The time pricing is run with its level cap set to P_knap: if it reaches the cap, min = P_knap. Duals: mixes
             of cgfleet's certificate duals and the demands (lam in CAP_LAMS). Re-checked exactly.
The fleet bound is the largest of these. A BKS fleet is called proven minimal only if our own exact checker accepts
the BKS solution (every customer once, capacity, time windows, nearest-integer travel) and the bound equals its fleet.

  python xtwfleet.py --out-dir /out
"""
import argparse
import glob
import html as htmllib
import json
import math
import os
import re
import shutil
import sys
import time
import traceback
from fractions import Fraction

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

VERSION = "0.1.0"
ST_BASE, ST_PER_1000 = 10.0, 30.0          # stfleet seconds per instance
CG_BASE, CG_PER_1000, CG_CAP = 20.0, 150.0, 170.0
CG_FINAL = 40.0
CAP_LEVELS = 1500
CAP_LAMS = (1.0, 0.75, 0.5, 0.25, 0.0)
CAP_SECONDS = 45.0
GLOBAL_S = 4.5 * 3600.0                   # no new cgfleet instance is started after this (from main's start)
T0 = time.time()


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def fceil(x):
    x = Fraction(x)
    return -((-x.numerator) // x.denominator)


# ---------------------------------------------------------------- solutions

def rint_dist(x1, y1, x2, y2):
    """TSPLIB EUC_2D nint distance, exact for integer coordinates."""
    dx, dy = x1 - x2, y1 - y2
    if float(dx).is_integer() and float(dy).is_integer():
        D = int(dx) * int(dx) + int(dy) * int(dy)
        r = math.isqrt(D)
        return r + (1 if D > r * r + r else 0)
    return int(math.floor(math.hypot(dx, dy) + 0.5))


ROUTE = re.compile(r"^\s*Route\s*#?\s*\d+\s*:(.*)$", re.I)


def parse_sol(text):
    """CVRPLib solution text -> (routes as lists of 1-based customers, stated cost or None). Empty routes dropped."""
    routes, cost = [], None
    for line in text.splitlines():
        m = ROUTE.match(line)
        if m:
            r = [int(t) for t in m.group(1).split()]
            if r:
                routes.append(r)
            continue
        p = line.split()
        if len(p) >= 2 and p[0].lower() == "cost":
            try:
                cost = float(p[1])
            except ValueError:
                pass
    return routes, cost


def check_sol(inst, routes):
    """Our own exact check: customers 1..n each exactly once, capacity, time windows (wait if early), return in time.
    Vehicles leave the depot at its ready time; travel = nint Euclidean; service at each customer."""
    rows = inst["rows"]
    n = len(rows) - 1
    Q = inst["capacity"]
    x0, y0, _, a0, b0, s0 = rows[0]
    seen = [0] * (n + 1)
    cost = 0
    for k, r in enumerate(routes):
        t, prev, sp, load = a0, 0, s0, 0
        for c in r:
            if not 1 <= c <= n:
                return {"ok": False, "why": "route %d: customer %s out of range" % (k + 1, c)}
            seen[c] += 1
            d = rint_dist(rows[prev][0], rows[prev][1], rows[c][0], rows[c][1])
            cost += d
            t = max(t + sp + d, rows[c][3])
            if t > rows[c][4]:
                return {"ok": False, "why": "route %d: customer %d starts at %s after %s" % (k + 1, c, t, rows[c][4])}
            load += rows[c][2]
            prev, sp = c, rows[c][5]
        d = rint_dist(rows[prev][0], rows[prev][1], x0, y0)
        cost += d
        if t + sp + d > b0:
            return {"ok": False, "why": "route %d: back at %s after %s" % (k + 1, t + sp + d, b0)}
        if load > Q:
            return {"ok": False, "why": "route %d: load %s above %s" % (k + 1, load, Q)}
    missing = [c for c in range(1, n + 1) if seen[c] == 0]
    dup = [c for c in range(1, n + 1) if seen[c] > 1]
    if missing or dup:
        return {"ok": False, "why": "missing %s, repeated %s" % (missing[:5], dup[:5])}
    return {"ok": True, "vehicles": len(routes), "cost": cost}


# ---------------------------------------------------------------- capacity pieces

def cap_lb(inst):
    tot = sum(Fraction(r[2]) for r in inst["rows"][1:])
    Q = Fraction(inst["capacity"])
    return max(1, fceil(tot / Q)) if Q > 0 else None


def knap_max(p, w, cap):
    """Exact 0/1 knapsack: the largest sum of integer profits p >= 0 whose weights w fit in cap."""
    p = np.asarray(p, dtype=np.int64)
    w = np.asarray(w, dtype=np.float64)
    P = int(p.sum())
    best = np.full(P + 1, np.inf)
    best[0] = 0.0
    for pi, wi in zip(p.tolist(), w.tolist()):
        if pi <= 0 or wi > cap:
            continue
        cand = best[:-pi] + wi
        np.minimum(best[pi:], cand, out=best[pi:])
    ok = np.flatnonzero(best <= cap + 1e-9)
    return int(ok.max())


def frac_knap(w, q, cap):
    """Fractional knapsack value (an upper bound of the 0/1 value), used only to scale the duals."""
    w = np.asarray(w, dtype=np.float64)
    q = np.asarray(q, dtype=np.float64)
    free = q <= 0
    val = float(w[free].sum())
    idx = np.flatnonzero(~free & (w > 0))
    order = idx[np.argsort(-(w[idx] / q[idx]), kind="stable")]
    room = float(cap)
    for i in order.tolist():
        if q[i] <= room:
            val += float(w[i])
            room -= float(q[i])
        else:
            val += float(w[i]) * room / float(q[i])
            break
    return val


def cap_eval(TI, pi, deadline=None, clock=time.monotonic):
    """fleet >= sum(pi) / min(P_time, P_knap). Returns (Fraction or None, P, P_knap, time_capped, timeout)."""
    import cgfleet as G
    pi = np.asarray(pi, dtype=np.int64)
    if int(pi.sum()) <= 0:
        return None, None, None, False, False
    pk = knap_max(pi, TI.q, TI.cap)
    if pk <= 0:
        return None, None, pk, False, False
    r = G.price(TI.C, TI.e, TI.l, pi, L_max=pk, deadline=deadline, want=0, clock=clock)
    if r["timeout"]:
        return None, None, pk, True, True
    P = pk if r["capped"] else min(int(r["pstar"]), pk)
    if P <= 0:
        return None, None, pk, r["capped"], False
    return Fraction(int(pi.sum()), P), P, pk, r["capped"], False


def cap_bound(TI, u, deadline, lams=CAP_LAMS, levels=CAP_LEVELS, clock=time.monotonic):
    """Best cgcap bound over dual mixes lam * u + (1 - lam) * demand. Returns (Fraction, cert or None, rows)."""
    v = np.asarray(TI.q, dtype=np.float64)
    best, cert, rows = Fraction(0), None, []
    for lam in lams:
        if clock() > deadline:
            break
        if lam > 0 and (u is None or float(np.sum(u)) <= 0):
            continue
        if lam < 1 and float(v.sum()) <= 0:
            continue
        w = np.zeros(TI.n)
        if lam > 0:
            w += lam * np.asarray(u, dtype=np.float64) / float(np.sum(u))
        if lam < 1:
            w += (1.0 - lam) * v / float(v.sum())
        F = frac_knap(w, v, TI.cap)
        if F <= 0:
            continue
        pi = np.floor(w * (levels / F)).astype(np.int64)
        if int(pi.sum()) <= 0 or int(pi.sum()) > 5_000_000:
            continue
        lb, P, pk, capped, timeout = cap_eval(TI, pi, deadline=deadline, clock=clock)
        rows.append({"lam": lam, "sum": int(pi.sum()), "p_knap": pk, "p": P, "time_capped": capped,
                     "timeout": timeout, "lb": None if lb is None else round(float(lb), 4)})
        if timeout:
            break
        if lb is not None and lb > best:
            best, cert = lb, {"lam": lam, "pi_int": [int(x) for x in pi], "p": int(P), "p_knap": int(pk),
                              "sum": int(pi.sum())}
    return best, cert, rows


def cap_verify(TI, cert):
    if not cert:
        return False
    lb, P, pk, _, timeout = cap_eval(TI, cert["pi_int"])
    return (not timeout) and lb is not None and P == cert["p"] and pk == cert["p_knap"]


# ---------------------------------------------------------------- CVRPLib pages (raw HTML kept; parsing is best effort)

NAME = re.compile(r"\bXTW-n\d+\b")
PAIR = re.compile(r"(?<![\d/])(\d{1,4})\s+/\s+(\d[\d,]*(?:\.\d+)?)(?![\d/])")


def strip(html):
    return htmllib.unescape(re.sub(r"<[^>]+>", " ", html))


def parse_history(html):
    """Bound-history page -> name, every 'vehicles / distance' pair in page order (newest first on CVRPLib)."""
    text = strip(html)
    names = NAME.findall(text)
    pairs = [(int(a), float(b.replace(",", ""))) for a, b in PAIR.findall(text)]
    return {"name": names[0] if names else None, "pairs": len(pairs),
            "newest": list(pairs[0]) if pairs else None, "oldest": list(pairs[-1]) if pairs else None,
            "fleets": sorted(set(p[0] for p in pairs))}


def parse_opt_table(html):
    """VRPTW instance list -> {XTW name: True (Opt yes) / False (no) / None (not found)}."""
    text = strip(html)
    ms = list(NAME.finditer(text))
    out = {}
    for k, m in enumerate(ms):
        name = m.group(0)
        if name in out:
            continue
        end = len(text)
        for m2 in ms[k + 1:]:
            if m2.group(0) != name:
                end = m2.start()
                break
        y = re.search(r"\b(yes|no)\b", text[m.end():end], re.I)
        out[name] = None if y is None else (y.group(1).lower() == "yes")
    return out


# ---------------------------------------------------------------- per instance

def files_by_stem(folder, exts):
    out = {}
    for p in sorted(glob.glob(os.path.join(folder, "**", "*"), recursive=True)):
        if os.path.isfile(p) and os.path.splitext(p)[1].lower() in exts:
            out.setdefault(os.path.splitext(os.path.basename(p))[0], p)
    return out


def st_budget(n):
    return ST_BASE + ST_PER_1000 * n / 1000.0


def cg_budget(n):
    return min(CG_CAP, CG_BASE + CG_PER_1000 * n / 1000.0)


def phase1(name, path, sol_path, cert_dir, st_fn=st_budget):
    """Parse, check the BKS, capacity bound, stfleet. Returns (record, instance dict, BKS routes)."""
    import mstfleet as M
    import stfleet as S
    import xltwlb as X
    with open(path, encoding="utf-8") as f:
        inst = X.parse_any(f.read())
    inst["name"] = name
    rows = inst["rows"]
    n = len(rows) - 1
    q = [r[2] for r in rows[1:]]
    Q = inst["capacity"]
    rec = {"instance": name, "customers": n, "capacity": Q, "total_demand": sum(q), "capfree": bool(sum(q) <= Q),
           "cap_lb": cap_lb(inst)}
    routes = []
    if sol_path:
        with open(sol_path, encoding="utf-8") as f:
            routes, cost = parse_sol(f.read())
        chk = check_sol(inst, routes)
        rec.update({"bks_vehicles": len(routes), "bks_cost_stated": cost, "bks_check": chk,
                    "bks_ok": bool(chk["ok"] and (cost is None or abs(chk["cost"] - cost) < 0.5))})
    else:
        rec.update({"bks_vehicles": None, "bks_ok": False, "bks_check": {"ok": False, "why": "no BKS file"}})
    I = M.Inst(inst)
    I.name = name
    rec.update({"profile": M.profile(I), "service_min": I.service_min, "integral": I.integral,
                "unservable": I.unservable, "overweight": int(sum(1 for x in q if x > Q))})
    if I.unservable or rec["overweight"]:
        rec["error"] = "instance has customers no route can serve"
        return rec, inst, routes
    if I.service_min < 1 or not I.integral:
        rec["st_skip"] = "service time below 1 or non-integral data"
        return rec, inst, routes
    res = S.bound_instance(I, st_fn(n), say=log)
    ok = res.get("verified") is True
    rec["st"] = {"bound": int(res["best_K"]) if ok else None, "source": res.get("best_source"),
                 "verified": res.get("verified"), "intervals": res.get("intervals"), "seconds": res.get("seconds"),
                 "whole_day_max": max([w["K"] for w in res.get("whole_day") or []] or [None]),
                 "cert": res.get("cert")}
    if res.get("cert") is not None:
        os.makedirs(cert_dir, exist_ok=True)
        c = dict(res["cert"])
        c.update({"instance": name, "fleet_at_least": rec["st"]["bound"], "verified": res.get("verified"),
                  "solver": "stfleet (cvrplib-baselines main/stfleet)", "study": "xtwfleet " + VERSION})
        with open(os.path.join(cert_dir, name + ".stfleet.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(c, f)
    return rec, inst, routes


def phase2(rec, inst, routes, cert_dir, cg_fn=cg_budget, cap_s=CAP_SECONDS, final_s=CG_FINAL):
    """cgfleet from the BKS routes, then cgcap where capacity can bind. Fills rec in place."""
    import cgfleet as G
    import tmatch as TM
    t0 = time.monotonic()
    TI = TM.Inst(inst)
    if TI.unservable or TI.overweight or float(TI.s.min()) < 1:
        rec["cg_skip"] = "unservable customer or service time below 1"
        return
    ub = rec["bks_vehicles"] if rec.get("bks_ok") else None
    init = [[c - 1 for c in r] for r in routes] if rec.get("bks_ok") else []
    b = cg_fn(TI.n)
    res = G.cg_bound(TI.C, TI.e, TI.l, TI.n, t0 + b, t0 + b + final_s, ub=ub, init=init, say=lambda m: None)
    c = res["cert"]
    recheck = None
    if c is not None:
        r = G.price(TI.C, TI.e, TI.l, np.array(c["pi_int"], dtype=np.int64), L_max=int(c["pstar"]) + 1, want=0)
        recheck = bool(r["pstar"] == c["pstar"] and Fraction(int(c["sum"]), int(c["pstar"])) == res["lb"])
    rec["cg"] = {"bound": int(res["lb_int"]) if recheck else None, "lb": float(res["lb"]),
                 "z_rmp": res["z_rmp"], "stop": res["stop"], "iterations": res["iterations"],
                 "columns": res["columns"], "recheck": recheck, "seconds": round(time.monotonic() - t0, 1)}
    if c is not None:
        os.makedirs(cert_dir, exist_ok=True)
        cc = dict(c)
        cc.update({"instance": rec["instance"], "fleet_at_least": rec["cg"]["bound"], "recheck": recheck,
                   "bound": "%d/%d" % (res["lb"].numerator, res["lb"].denominator),
                   "solver": "cgfleet (cvrplib-baselines main/cgfleet)", "study": "xtwfleet " + VERSION})
        with open(os.path.join(cert_dir, rec["instance"] + ".cgfleet.json"), "w", encoding="utf-8",
                  newline="\n") as f:
            json.dump(cc, f)
    if TI.capfree:
        return
    t1 = time.monotonic()
    u = c["pi_int"] if (c is not None and recheck) else None
    best, cert, rows = cap_bound(TI, u, t1 + cap_s)
    ver = cap_verify(TI, cert) if cert else None
    rec["cgcap"] = {"bound": fceil(best) if (cert and ver) else None, "lb": float(best), "verified": ver,
                    "rows": rows, "seconds": round(time.monotonic() - t1, 1)}
    if cert:
        cc = dict(cert)
        cc.update({"instance": rec["instance"], "fleet_at_least": rec["cgcap"]["bound"], "verified": ver,
                   "rule": "fleet >= sum(pi) / min(P_time, P_knap); P_time = cgfleet price(pi) (2-cycle-free walks, "
                           "customers with pi >= 1), P_knap = 0/1 knapsack of pi under the capacity",
                   "study": "xtwfleet " + VERSION})
        with open(os.path.join(cert_dir, rec["instance"] + ".cgcap.json"), "w", encoding="utf-8",
                  newline="\n") as f:
            json.dump(cc, f)


def finish(rec, opt=None, hist=None):
    """Combine the bounds and compare them with the BKS fleet."""
    parts = {"cap": rec.get("cap_lb"), "stfleet": (rec.get("st") or {}).get("bound"),
             "cgfleet": (rec.get("cg") or {}).get("bound"), "cgcap": (rec.get("cgcap") or {}).get("bound")}
    vals = {k: v for k, v in parts.items() if v is not None}
    final = max(vals.values()) if vals else None
    rec["bounds"] = parts
    rec["final"] = final
    rec["final_sources"] = sorted(k for k, v in vals.items() if v == final)
    k = rec.get("bks_vehicles")
    good = bool(rec.get("bks_ok")) and k is not None and final is not None
    rec["proved"] = bool(good and final >= k)
    rec["above_bks"] = bool(good and final > k)
    rec["tw_needed"] = bool(rec["proved"] and (rec.get("cap_lb") or 0) < k)
    rec["gap"] = (k - final) if good else None
    rec["ratio"] = round(k / float(final), 4) if good and final else None
    rec["opt"] = opt
    rec["history"] = hist
    rec["unverified"] = bool((rec.get("st") or {}).get("verified") is False
                             or (rec.get("cg") or {}).get("recheck") is False
                             or (rec.get("cgcap") or {}).get("verified") is False)
    return rec


def tally(recs):
    ok = [r for r in recs if not r.get("error") and r.get("final") is not None]
    good = [r for r in ok if r.get("bks_ok")]
    capfree = [r for r in good if r.get("capfree")]
    both = [r for r in ok if (r.get("st") or {}).get("bound") is not None
            and (r.get("cg") or {}).get("bound") is not None]
    opt = [r for r in good if r.get("opt") is True]
    hist = [r for r in recs if (r.get("history") or {}).get("oldest") and r.get("bks_vehicles")]
    ratios = [r["ratio"] for r in capfree if r.get("ratio") is not None]
    try:
        import mstfleet as M
        peak = M.peak_gb()
    except Exception:  # noqa: BLE001
        peak = None
    return {
        "instances": len(recs),
        "done": len(ok),
        "errors": [r["instance"] for r in recs if r.get("error")],
        "bks_read": sum(1 for r in recs if r.get("bks_vehicles")),
        "bks_ok": len(good),
        "bks_feasible": sum(1 for r in recs if (r.get("bks_check") or {}).get("ok")),
        "bks_check_failed": [r["instance"] for r in recs if r.get("bks_vehicles") and not r.get("bks_ok")],
        "capfree": len([r for r in ok if r.get("capfree")]),
        "unverified": [r["instance"] for r in ok if r.get("unverified")],
        "above_bks": [r["instance"] for r in ok if r.get("above_bks")],
        "proved": [r["instance"] for r in ok if r.get("proved")],
        "proved_tw_needed": [r["instance"] for r in ok if r.get("tw_needed")],
        "proved_not_opt": [r["instance"] for r in ok if r.get("proved") and r.get("opt") is not True],
        "proved_capfree": [r["instance"] for r in capfree if r.get("proved")],
        "opt_marked": len(opt),
        "opt_bound_equal": [r["instance"] for r in opt if r.get("proved")],
        "capfree_ratio_median": round(float(np.median(ratios)), 4) if ratios else None,
        "capfree_ratio_max": round(float(max(ratios)), 4) if ratios else None,
        "sum_final_good": sum(r["final"] for r in good),
        "sum_bks_good": sum(r["bks_vehicles"] for r in good),
        "cg_runs": sum(1 for r in ok if r.get("cg")),
        "cg_ge_st": sum(1 for r in both if r["cg"]["bound"] >= r["st"]["bound"]),
        "cg_and_st": len(both),
        "cgcap_gain": [r["instance"] for r in ok if (r.get("cgcap") or {}).get("bound") is not None
                       and r["cgcap"]["bound"] > max(r.get("cap_lb") or 0, (r.get("st") or {}).get("bound") or 0,
                                                     (r.get("cg") or {}).get("bound") or 0)],
        "history_rows": len(hist),
        "history_fleet_cut": sum(1 for r in hist if r["history"]["oldest"][0] > r["bks_vehicles"]),
        "history_vehicles_saved": sum(r["history"]["oldest"][0] - r["bks_vehicles"] for r in hist),
        "peak_gb": peak,
    }


def write_md(path, res):
    t = res["tally"]
    L = ["# xtwfleet: fleet lower bounds against CVRPLib's XTW best known solutions", "",
         "Pre-registered in PREREG.md. Study %s. BKS downloaded %s. Certificates in cert/." % (
             VERSION, (res.get("manifest") or {}).get("bks_downloaded_utc")), "",
         "Tally: `%s`" % json.dumps(t), "",
         "| instance | n | capacity free | BKS fleet | BKS check | cap | stfleet | cgfleet | cgcap | bound | proved | "
         "CVRPLib opt | first fleet on page |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["instances"]:
        if r.get("error"):
            L.append("| %s | error: %s ||||||||||||" % (r["instance"], str(r["error"]).strip().splitlines()[-1]))
            continue
        b = r.get("bounds") or {}
        h = r.get("history") or {}
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["instance"], r.get("customers"), r.get("capfree"), r.get("bks_vehicles"),
            "ok" if r.get("bks_ok") else "no", b.get("cap"), b.get("stfleet"), b.get("cgfleet"), b.get("cgcap"),
            r.get("final"), "yes" if r.get("proved") else "", r.get("opt"), (h.get("oldest") or [None])[0]))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


def size_of(name):
    m = re.search(r"n(\d+)", name)
    return int(m.group(1)) if m else 0


def run_all(man, out_dir, only=(), global_s=GLOBAL_S, st_fn=st_budget, cg_fn=cg_budget, cap_s=CAP_SECONDS,
            final_s=CG_FINAL):
    start = time.monotonic()
    out = os.path.join(out_dir, "xtwfleet")
    cert_dir = os.path.join(out, "cert")
    os.makedirs(out, exist_ok=True)
    insts = files_by_stem(man["instances"]["dir"], {".vrp", ".txt", ".vrptw"})
    sols = files_by_stem(man["bks"]["dir"], {".sol", ".txt"})
    pages = man.get("pages") or {}
    opt_tab, hist_by_name = {}, {}
    raw_dir = os.path.join(out, "pages")
    os.makedirs(raw_dir, exist_ok=True)
    for p in [pages.get("list")] + list((pages.get("bounds") or {}).values()):
        if p and os.path.exists(p):
            shutil.copy(p, os.path.join(raw_dir, os.path.basename(p)))
    if pages.get("list") and os.path.exists(pages["list"]):
        with open(pages["list"], encoding="utf-8", errors="replace") as f:
            opt_tab = parse_opt_table(f.read())
    for _, p in sorted((pages.get("bounds") or {}).items()):
        if os.path.exists(p):
            with open(p, encoding="utf-8", errors="replace") as f:
                h = parse_history(f.read())
            if h["name"]:
                hist_by_name[h["name"]] = h
    names = [x for x in only if x] or sorted(insts, key=lambda k: (size_of(k), k))
    res = {"study": "xtwfleet " + VERSION, "python": sys.version.split()[0], "numpy": np.__version__,
           "settings": {"st": [ST_BASE, ST_PER_1000], "cg": [CG_BASE, CG_PER_1000, CG_CAP, CG_FINAL],
                        "cap_levels": CAP_LEVELS, "cap_lams": list(CAP_LAMS), "cap_s": CAP_SECONDS,
                        "global_s": global_s},
           "manifest": {"code": man.get("code"), "instances_sha256": man["instances"].get("sha256"),
                        "bks_sha256": man["bks"].get("sha256"), "bks_downloaded_utc": man["bks"].get("downloaded_utc"),
                        "pages_utc": pages.get("downloaded_utc"), "pages_failed": pages.get("failed"),
                        "prereg_sha256": man.get("prereg_sha256")},
           "files": {"instances": len(insts), "bks": len(sols), "opt_rows": len(opt_tab),
                     "opt_yes": sum(1 for v in opt_tab.values() if v), "history_pages": len(hist_by_name)},
           "instances": []}
    res_path = os.path.join(out, "results.json")

    def save():
        res["tally"] = tally(res["instances"])
        with open(res_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(res, f, indent=1)

    log("plan: %d instances, %d BKS files, %d opt rows, %d history pages" % (
        len(names), len(sols), len(opt_tab), len(hist_by_name)))
    keep = {}
    for name in names:
        try:
            rec, inst, routes = phase1(name, insts[name], sols.get(name), cert_dir, st_fn=st_fn)
            keep[name] = (inst, routes)
        except Exception:  # noqa: BLE001 - recorded
            rec = {"instance": name, "error": traceback.format_exc()}
        if not rec.get("error"):
            finish(rec, opt_tab.get(name), hist_by_name.get(name))
        res["instances"].append(rec)
        save()
        log(json.dumps({k: rec.get(k) for k in ("instance", "customers", "capfree", "bks_vehicles", "bks_ok",
                                               "cap_lb", "final", "proved", "error")}))
    # phase 2: column generation on the instances not yet proved, smallest first, while time remains
    for rec in sorted(res["instances"], key=lambda r: (r.get("customers") or 0, r["instance"])):
        if rec.get("error") or rec.get("proved") or rec["instance"] not in keep:
            continue
        if time.monotonic() - start > global_s:
            rec["cg_skip"] = "global time budget used"
            continue
        try:
            phase2(rec, keep[rec["instance"]][0], keep[rec["instance"]][1], cert_dir, cg_fn=cg_fn, cap_s=cap_s,
                   final_s=final_s)
        except Exception:  # noqa: BLE001 - recorded
            rec["cg_error"] = traceback.format_exc()
        finish(rec, rec.get("opt"), rec.get("history"))
        save()
        log(json.dumps({k: rec.get(k) for k in ("instance", "customers", "bks_vehicles", "bounds", "final",
                                               "proved", "cg_error")}))
    save()
    write_md(os.path.join(out, "results.md"), res)
    log("TALLY " + json.dumps(res["tally"]))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--manifest", default=os.path.join(HERE, "manifest.json"))
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    with open(a.manifest) as f:
        man = json.load(f)
    run_all(man, a.out_dir, only=a.only.split(","))


if __name__ == "__main__":
    main()
