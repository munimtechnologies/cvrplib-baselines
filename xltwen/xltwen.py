"""xltwen: time-based ("energetic reasoning") fleet lower bounds for CVRPLib's XLTW-Test, in the challenge's
convention, scored against xltwen/expectations.md (written before any of these bounds was computed).

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

Method (energetic reasoning for the VRPTW fleet is published prior art: Afifi, Guibadj & Moukrim, "New Lower Bounds
on the Number of Vehicles for the Vehicle Routing Problem with Time Windows", CPAIOR 2014, LNCS 8451, 422-437; time-
window fleet bounds go back to Kontoravdis & Bard 1995). What is new here is only its use on XLTW-Test, exact
integer arithmetic, and a check of every bound against exactly verified solutions.

A vehicle is a machine. Customer i becomes a job that keeps its vehicle busy over [S_i - pre_i, S_i + s_i + post_i],
where S_i is its service start. With tau_i = the shortest arc into i from any customer that can precede it in some
time-feasible route (or from the depot) and sig_i = the shortest arc out of i to any customer that can follow it (or
to the depot), three choices keep the busy periods of one vehicle disjoint (for an arc i -> j, post_i + pre_j <= t_ij):
  'in':   pre = tau, post = 0
  'out':  pre = 0,   post = sig
  'half': pre = tau/2, post = sig/2
S_i lies in [e_i, lat_i] (e = max(ready, depot open + t_0i), lat = min(due, depot close - s_i - t_i0), as in xltwlb),
so job i has release r_i = e_i - pre_i, length p_i = pre_i + s_i + post_i and deadline d_i = lat_i + s_i + post_i.
m vehicles then need, for every interval [t1, t2], sum_i W_i(t1, t2) <= m (t2 - t1) with the usual mandatory overlap
W_i = max(0, min(t2 - t1, p_i, r_i + p_i - t1, t2 - d_i + p_i)); and at every instant t, every job whose latest
start d_i - p_i <= t < r_i + p_i is running. Both give lower bounds on m; this script reports the best it finds over
a grid of intervals with two passes of coordinate refinement (a search, so a better interval may exist).

Travel time is the challenge's 'round' convention, floor(d + 0.5), computed exactly in integers when the coordinates
are integers; the slack argument that makes direct depot arcs valid needs every service time >= 1 (xltwlb.tw_ok).
"""
import argparse
import hashlib
import json
import os
import statistics
import sys
import time
import traceback
import urllib.request

import numpy as np

import xltwlb as X
import xltwrun as R

VARIANTS = ("in", "out", "half")
GRID = 128
REFINE = 2048
EPS = 1e-6
MAX_SECONDS = 3600.0
MAX_GB = 1.5
SOLS_URL = ("https://raw.githubusercontent.com/munimtechnologies/cvrplib-baselines/"
            "56b4e6e1928066c7bb23bca3d7848895a3e239ac/xltwrun/sols/%s.sol")
UA = "CVRPLib XLTW fleet bounds - MV2 of Munim, Inc. (mv2@munimtech.com)"
T0 = time.time()

# Vehicles of the exactly checked part-a solutions (xltwrun/results-a.md, run of 2026-11-05).
_VEH_A = """
n1048 9|n1094 94|n1141 49|n1188 37|n1234 35|n1281 168|n1328 66|n1374 33|n1421 72|n1468 41|n1514 44|n1561 72
n1608 113|n1654 69|n1701 46|n1748 190|n1794 234|n1841 29|n1888 32|n1934 54|n1981 102|n2028 103|n2074 66|n2121 31
n2168 107|n2214 77|n2261 89|n2307 41|n2354 133|n2401 190|n2447 147|n2494 63|n2541 133|n2587 59|n2634 124
n2681 141|n2727 83|n2774 220|n2821 236|n2867 29|n2914 230|n2961 115|n3007 190|n3054 113|n3101 96|n3147 84
n3194 509|n3241 237|n3287 43|n3334 83|n3408 221|n3484 86|n3561 81|n3640 310|n3721 265|n3804 126|n3888 467
n3975 117|n4063 148|n4153 238|n4245 235|n4340 84|n4436 55|n4535 179|n4635 347|n4738 101|n4844 217|n4951 323
n5061 231|n5174 83|n5288 144|n5406 241|n5526 459|n5649 509|n5774 126|n5902 45|n6034 112|n6168 224|n6305 353
n6445 475
"""
VEH_A = {}
for _cell in _VEH_A.replace("\n", "|").split("|"):
    if _cell.strip():
        _name, _v = _cell.split()
        VEH_A["XLTW-Test-" + _name] = int(_v)


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def travel(xa, ya, xb, yb, exact=True):
    """'round' travel time floor(d + 0.5). With integer coordinates it is corrected to be exact:
    k = floor(d + 0.5) iff k - 1/2 <= d < k + 1/2, i.e. (k >= 1 implies (2k - 1)^2 <= 4D) and 4D < (2k + 1)^2."""
    dx = np.asarray(xa, dtype=np.float64) - np.asarray(xb, dtype=np.float64)
    dy = np.asarray(ya, dtype=np.float64) - np.asarray(yb, dtype=np.float64)
    if not exact:
        return np.floor(np.hypot(dx, dy) + 0.5)
    d2 = dx * dx + dy * dy
    k = np.floor(np.sqrt(d2) + 0.5)
    k = np.where((k >= 1) & ((2 * k - 1) ** 2 > 4 * d2), k - 1, k)
    k = np.where((2 * k + 1) ** 2 <= 4 * d2, k + 1, k)
    return k


def prepare(inst, block=512):
    """Arrays for customers 1..n (index 0 = customer 1): e, lat, s, tau, sig; plus the full arrays incl. the depot."""
    rows = inst["rows"]
    A = np.array([r[:6] for r in rows], dtype=np.float64)
    x, y, a, b, s = A[:, 0], A[:, 1], A[:, 3], A[:, 4], A[:, 5]
    vals = A[:, [0, 1, 3, 4, 5]]
    exact = bool(np.all(vals == np.round(vals)) and np.abs(vals).max() < 1e7)
    t0 = travel(x, y, x[0], y[0], exact)
    e = np.maximum(a, a[0] + t0)
    lat = np.minimum(b, b[0] - s - t0)
    n = len(rows) - 1
    tau, sig = t0[1:].copy(), t0[1:].copy()
    cx, cy = x[1:], y[1:]
    for lo in range(1, n + 1, block):
        hi = min(lo + block, n + 1)
        d = travel(x[lo:hi, None], y[lo:hi, None], cx[None, :], cy[None, :], exact)
        ok = np.maximum(a[None, 1:], (e[lo:hi] + s[lo:hi])[:, None] + d) <= lat[None, 1:] + EPS
        idx = np.arange(lo, hi)
        ok[idx - lo, idx - 1] = False  # a customer never precedes itself
        dm = np.where(ok, d, np.inf)
        sig[lo - 1:hi - 1] = np.minimum(sig[lo - 1:hi - 1], dm.min(axis=1))
        tau = np.minimum(tau, dm.min(axis=0))
        del d, ok, dm
    unserv = (np.nonzero(e[1:] > lat[1:] + EPS)[0] + 1).tolist()
    return {"n": n, "exact": exact, "e": e[1:], "lat": lat[1:], "s": s[1:], "tau": tau, "sig": sig,
            "unservable": unserv, "x": x, "y": y, "a": a, "b": b, "sf": s,
            "service_ok": bool(X.tw_ok(inst, "round"))}


def offsets(P, v):
    """(pre, post) per customer, doubled so that 'half' stays integral."""
    tau2, sig2 = 2 * P["tau"], 2 * P["sig"]
    zero = np.zeros_like(tau2)
    if v == "in":
        return tau2, zero
    if v == "out":
        return zero, sig2
    if v == "half":
        return tau2 / 2, sig2 / 2
    raise ValueError(v)


def jobs(P, v):
    """Release, length and deadline of every customer's busy period, all doubled."""
    pre, post = offsets(P, v)
    e, lat, s = 2 * P["e"], 2 * P["lat"], 2 * P["s"]
    return e - pre, pre + s + post, lat + s + post


def compulsory(r, p, d):
    """Most jobs that must all be running at one instant (half-open compulsory parts [d - p, r + p))."""
    ls, ee = d - p, r + p
    m = ls < ee
    k = int(m.sum())
    if k == 0:
        return 0, None
    t = np.concatenate([ls[m], ee[m]])
    w = np.concatenate([np.ones(k), -np.ones(k)])
    order = np.lexsort((w, t))  # by time, ends before starts at equal times
    c = np.cumsum(w[order])
    i = int(np.argmax(c))
    return int(c[i]), float(t[order][i])


def energy_exact(r, p, d, t1, t2):
    """ceil(sum W / (t2 - t1)) in int64 arithmetic (inputs are integers)."""
    ri, pi, di = (np.asarray(z).astype(np.int64) for z in (r, p, d))
    t1, t2 = int(t1), int(t2)
    if t2 <= t1:
        return 0, 0
    w = np.minimum(np.minimum(pi, ri + pi - t1), np.minimum(t2 - t1, t2 - di + pi))
    tot = int(np.maximum(w, 0).sum())
    return -(-tot // (t2 - t1)), tot


def energy_scan(r, p, d, T1, T2, chunk=256):
    """Best (bound, t1, t2) over all pairs t1 in T1, t2 in T2 with t2 > t1."""
    best = (0, None, None)
    ls = d - p
    for t1 in T1:
        A = np.minimum(p, r + p - t1)
        T = T2[T2 > t1]
        for c0 in range(0, len(T), chunk):
            Tc = T[c0:c0 + chunk]
            L = Tc - t1
            W = np.minimum(A[None, :], L[:, None])
            np.minimum(W, Tc[:, None] - ls[None, :], out=W)
            np.maximum(W, 0, out=W)
            lb = np.ceil(W.sum(axis=1) / L - 1e-9)
            j = int(np.argmax(lb))
            if lb[j] > best[0]:
                best = (int(lb[j]), float(t1), float(Tc[j]))
    return best


def pick(c, k):
    c = np.unique(c)
    if len(c) <= k:
        return c
    return np.unique(c[np.linspace(0, len(c) - 1, k).round().astype(int)])


def energy_best(r, p, d, grid=GRID, refine=REFINE, rounds=2):
    C1, C2 = np.unique(np.concatenate([r, d - p])), np.unique(np.concatenate([d, r + p]))
    best = energy_scan(r, p, d, pick(C1, grid), pick(C2, grid))
    R1, R2 = pick(C1, refine), pick(C2, refine)
    for _ in range(rounds):
        if best[1] is None:
            break
        b1 = energy_scan(r, p, d, R1, np.array([best[2]]))
        if b1[0] > best[0]:
            best = b1
        b2 = energy_scan(r, p, d, np.array([best[1]]), R2)
        if b2[0] > best[0]:
            best = b2
    return best


def bound_instance(inst, grid=GRID, refine=REFINE):
    t = time.time()
    P = prepare(inst)
    res = {"customers": P["n"], "exact_inputs": P["exact"], "service_ok": P["service_ok"],
           "unservable": len(P["unservable"]), "tau_mean": round(float(P["tau"].mean()), 3),
           "sig_mean": round(float(P["sig"].mean()), 3), "service_mean": round(float(P["s"].mean()), 3),
           "horizon": [float(inst["rows"][0][3]), float(inst["rows"][0][4])]}
    for v in VARIANTS:
        r, p, d = jobs(P, v)
        comp, ct = compulsory(r, p, d)
        h1, h2 = float(r.min()), float(d.max())
        dur, _ = energy_exact(r, p, d, h1, h2)
        eb, t1, t2 = energy_best(r, p, d, grid, refine)
        ver, tot = energy_exact(r, p, d, t1, t2) if t1 is not None else (0, 0)
        full = t1 is not None and t1 <= h1 and t2 >= h2
        res[v] = {"compulsory": comp, "compulsory_at": None if ct is None else ct / 2, "duration": dur,
                  "energy": eb, "t1": None if t1 is None else t1 / 2, "t2": None if t2 is None else t2 / 2,
                  "energy_exact": ver, "verified": ver == eb, "full_horizon": full,
                  "bound": max(comp, dur, ver)}
    bv = max(VARIANTS, key=lambda v: res[v]["bound"])
    res["e"] = res[bv]["bound"]
    res["best_variant"] = bv
    b = res[bv]
    res["inner_interval_wins"] = (not b["full_horizon"]) and b["energy_exact"] > max(b["duration"], b["compulsory"])
    res["seconds"] = round(time.time() - t, 2)
    return res, P


def parse_sol(text):
    routes = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("Route #"):
            routes.append([int(z) for z in s.partition(":")[2].split()])
    return routes


def check_routes(routes, P):
    """Simulate each route (earliest starts, 'round') and check every variant's busy periods fit and are disjoint."""
    x, y, a, b, sf, ex = P["x"], P["y"], P["a"], P["b"], P["sf"], P["exact"]
    J = {v: (jobs(P, v), offsets(P, v)) for v in VARIANTS}
    out = {"routes": len(routes), "sim_ok": True, "busy_ok": {v: True for v in VARIANTS}, "first_problem": None,
           "customers_seen": 0}
    seen = set()
    for k, rt in enumerate(routes):
        t, prev, starts = float(a[0]), 0, []
        for c in rt:
            t = t + float(travel(x[prev], y[prev], x[c], y[c], ex))
            S = max(t, float(a[c]))
            if S > float(b[c]) + EPS and out["sim_ok"]:
                out["sim_ok"], out["first_problem"] = False, "route %d customer %d late" % (k + 1, c)
            starts.append(S)
            t, prev = S + float(sf[c]), c
            seen.add(c)
        if rt and t + float(travel(x[prev], y[prev], x[0], y[0], ex)) > float(b[0]) + EPS and out["sim_ok"]:
            out["sim_ok"], out["first_problem"] = False, "route %d returns late" % (k + 1)
        for v in VARIANTS:
            (r, p, d), (pre, post) = J[v]
            prev_end = None
            for c, S in zip(rt, starts):
                i = c - 1
                st, en = 2 * S - pre[i], 2 * S + 2 * sf[c] + post[i]
                bad = st < r[i] - EPS or en > d[i] + EPS or (prev_end is not None and st < prev_end - EPS)
                if bad and out["busy_ok"][v]:
                    out["busy_ok"][v] = False
                    out["first_problem"] = out["first_problem"] or "variant %s route %d customer %d" % (v, k + 1, c)
                prev_end = en
    out["customers_seen"] = len(seen)
    out["visits"] = sum(len(rt) for rt in routes)
    return out


def fetch(url, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8")
        except Exception:  # noqa: BLE001 - retried, then recorded
            if k == tries - 1:
                raise
            time.sleep(5 * (k + 1))


def verdict(ok):
    return "untestable" if ok is None else ("held" if ok else "did not hold")


def tally(recs, peak, seconds, expected=100, expected_sols=80):
    ok = [r for r in recs if not r.get("error")]
    full = len(ok) == expected
    errs = [r["instance"] for r in recs if r.get("error")]
    not_exact = [r["instance"] for r in ok if not r["exact_inputs"] or not r["service_ok"]]
    unserv = [r["instance"] for r in ok if r["unservable"]]
    unver = ["%s/%s" % (r["instance"], v) for r in ok for v in VARIANTS if not r[v]["verified"]]
    above = [r["instance"] for r in ok if r.get("vehicles_a") is not None and r["e"] > r["vehicles_a"]]
    sols = [r for r in ok if r.get("sol_check")]
    sol_bad = [r["instance"] for r in sols if not r["sol_check"]["sim_ok"]
               or not all(r["sol_check"]["busy_ok"].values()) or r["sol_check"]["routes"] != r["vehicles_a"]
               or r["sol_check"]["customers_seen"] != r["customers"]
               or r["sol_check"].get("visits") != r["customers"]]
    sol_missing = [r["instance"] for r in ok if r.get("vehicles_a") is not None and not r.get("sol_check")]
    kc1 = [r for r in ok if r["kc"] == 1]
    other = [r for r in ok if r["kc"] not in (None, 1)]
    up_kc1 = [r["instance"] for r in kc1 if r["e"] > r["k"]]
    up_other = [r["instance"] for r in other if r["e"] > r["k"]]
    n3147 = next((r for r in ok if r["instance"] == "XLTW-Test-n3147"), None)
    ratios = [r["vehicles_a"] / max(r["k"], r["e"]) for r in kc1 if r.get("vehicles_a")]
    inner = [r["instance"] for r in ok if r["inner_interval_wins"]]
    a_runs = [r for r in ok if r.get("vehicles_a")]
    gap_k = [(r["vehicles_a"] - r["k"]) / r["k"] for r in a_runs]
    gap_ks = [(r["vehicles_a"] - max(r["k"], r["e"])) / max(r["k"], r["e"]) for r in a_runs]
    t = {"instances": len(recs), "errors": errs, "not_exact_or_service": not_exact, "unservable": unserv,
         "unverified": unver, "e_above_part_a_vehicles": above, "sols_checked": len(sols), "sols_bad": sol_bad,
         "sols_missing": sol_missing, "kc1": len(kc1), "other": len(other), "e_gt_k_kc1": up_kc1,
         "e_gt_k_other": up_other, "n3147_e": n3147["e"] if n3147 else None,
         "median_vehicles_over_kstar_kc1_part_a": round(statistics.median(ratios), 4) if ratios else None,
         "median_vehicles_over_k_kc1_part_a": round(statistics.median(
             [r["vehicles_a"] / r["k"] for r in kc1 if r.get("vehicles_a")]), 4) if ratios else None,
         "inner_interval_wins": inner, "peak_gb": peak, "seconds": round(seconds, 1),
         "part_a_runs": len(a_runs),
         "part_a_median_gap_k": round(statistics.median(gap_k), 4) if gap_k else None,
         "part_a_median_gap_kstar": round(statistics.median(gap_ks), 4) if gap_ks else None,
         "part_a_at_k": sum(1 for r in a_runs if r["vehicles_a"] == r["k"]),
         "part_a_at_kstar": sum(1 for r in a_runs if r["vehicles_a"] == max(r["k"], r["e"])),
         "k_total_part_a": sum(r["k"] for r in a_runs),
         "kstar_total_part_a": sum(max(r["k"], r["e"]) for r in a_runs),
         "kstar_total_all": sum(max(r["k"], r["e"]) for r in ok), "k_total_all": sum(r["k"] for r in ok),
         "best_variant_counts": {v: sum(1 for r in ok if r["best_variant"] == v and r["e"] > 0) for v in VARIANTS}}
    e0 = (full and not errs and not not_exact and not unserv and not unver and not above and not sol_bad
          and len(sols) == expected_sols)
    t["e0_detail"] = "full=%s sols=%d" % (full, len(sols))
    pred = {"E0": verdict(e0 if full else None)}
    g = (lambda c: verdict(c)) if e0 else (lambda c: "not scored (E0)")  # noqa: E731
    pred.update({
        "E1": g(len(up_kc1) >= 10),
        "E2": g(len(up_other) <= 10),
        "E3": g(n3147 is not None and n3147["e"] >= 20),
        "E4": g(bool(ratios) and statistics.median(ratios) <= 3.0),
        "E5": g(len(inner) >= 5),
        "E6": g(peak is not None and peak <= MAX_GB and seconds <= MAX_SECONDS),
    })
    t["predictions"] = pred
    return t


def write_md(path, recs, t, src_sha):
    L = ["# xltwen: time-based fleet lower bounds on XLTW-Test", "",
         "Convention 'round' (the challenge's). K = max(KB, KT) from xltwtest/; E = the best energetic or "
         "compulsory-part bound found here (three busy-period variants); K* = max(K, E). Vehicles = the exactly "
         "checked part-a solutions (xltwrun/, limits T(n)/30). xltwen.py SHA-256 `%s`." % src_sha, "",
         "Predictions: `%s`" % json.dumps(t["predictions"]), "",
         "E > K on %d of %d instances with KC = 1 and %d of %d others. Part a (%d runs): median (vehicles - K)/K %s, "
         "against K* %s; at K %d, at K* %d. Sum of K over all instances %d, of K* %d." % (
             len(t["e_gt_k_kc1"]), t["kc1"], len(t["e_gt_k_other"]), t["other"], t["part_a_runs"],
             t["part_a_median_gap_k"], t["part_a_median_gap_kstar"], t["part_a_at_k"], t["part_a_at_kstar"],
             t["k_total_all"], t["kstar_total_all"]), "",
         "| instance | n | KC | K | E | K* | vehicles (a) | variant | duration | compulsory | energy | t1 | t2 | "
         "sol check | s |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(recs, key=lambda r: r.get("customers", 0)):
        if r.get("error"):
            L.append("| %s | | | | error | | | | | | | | | | |" % r["instance"])
            continue
        b = r[r["best_variant"]]
        sc = r.get("sol_check")
        scs = "" if not sc else ("ok" if sc["sim_ok"] and all(sc["busy_ok"].values()) else "FAIL")
        L.append("| %s | %d | %s | %s | %d | %d | %s | %s | %d | %d | %d | %s | %s | %s | %s |" % (
            r["instance"], r["customers"], r["kc"], r["k"], r["e"], max(r["k"], r["e"]),
            "" if r.get("vehicles_a") is None else r["vehicles_a"], r["best_variant"], b["duration"],
            b["compulsory"], b["energy_exact"], b["t1"], b["t2"], scs, r["seconds"]))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--grid", type=int, default=GRID)
    ap.add_argument("--refine", type=int, default=REFINE)
    ap.add_argument("--sols-url", default=SOLS_URL)
    ap.add_argument("--no-sols", action="store_true")
    args = ap.parse_args()
    out = os.path.join(args.out_dir, "xltwen")
    os.makedirs(out, exist_ok=True)
    src_sha = sha256_file(os.path.abspath(__file__))
    paths, digest = R.find_instances(args.data_dir)
    log("%d instance files; xltwen.py sha256 %s" % (len(paths), src_sha))
    insts = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            insts.append(X.parse_any(f.read()))
    insts.sort(key=lambda i: len(i["rows"]))
    recs, t = [], time.time()
    with open(os.path.join(out, "progress.jsonl"), "a", encoding="utf-8") as prog:
        for inst in insts:
            name = inst["name"]
            b = R.BOUNDS.get(name, {})
            rec = {"instance": name, "kc": b.get("kc"), "k": b.get("k"), "vehicles_a": VEH_A.get(name)}
            try:
                res, P = bound_instance(inst, args.grid, args.refine)
                rec.update(res)
                if rec["vehicles_a"] is not None and not args.no_sols:
                    try:
                        rec["sol_check"] = check_routes(parse_sol(fetch(args.sols_url % name)), P)
                    except Exception as e:  # noqa: BLE001 - recorded; counts against E0
                        rec["sol_error"] = "%s: %s" % (type(e).__name__, e)
                del P
            except Exception:  # noqa: BLE001 - recorded
                rec["error"] = traceback.format_exc()
            rec["peak_gb"] = X.peak_gb()
            recs.append(rec)
            prog.write(json.dumps(rec) + "\n")
            prog.flush()
            log("%s n=%s K=%s E=%s veh=%s %s" % (name, rec.get("customers"), rec["k"], rec.get("e"),
                                                 rec["vehicles_a"], rec.get("error", "")[-300:]))
    secs = time.time() - t
    tl = tally(recs, X.peak_gb(), secs)
    print(json.dumps(tl["predictions"]), flush=True)
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump({"xltwen_sha256": src_sha, "grid": args.grid, "refine": args.refine, "instances": recs,
                   "tally": tl}, f, indent=1)
    write_md(os.path.join(out, "results.md"), recs, tl, src_sha)
    if tl["errors"]:
        raise SystemExit("%d instance(s) failed" % len(tl["errors"]))


if __name__ == "__main__":
    sys.exit(main())
