"""xtwprobe: does ng-route pricing make the fleet bound bite on CVRPLib's XTW instances (up to 400 customers)?

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

For each XTW instance with at most N_MAX customers (smallest first, while the global budget lasts):
  1. read it and its CURRENT best known solution (BKS); check the BKS with xtwfleet's own exact checker;
  2. cap = ceil(total demand / capacity);
  3. column generation from the BKS routes: cgfleet's R2 pricing first, then ngfleet's ng-route pricing
     (ngfleet.cg_two_phase), capacity ignored (a relaxation, so every bound is valid for the real problem);
  4. every certificate is re-checked by one more exact pricing run, and checked against every BKS route
     (no real route may earn more than the certificate's P*);
  5. bound = max(cap, R2 bound, ng bound); proved = BKS passes our check and bound == BKS fleet.
Pre-registered in PREREG.md (predictions P0-P6). Results in /out/ngfleet/.

  python xtwprobe.py --out-dir /out
"""
import argparse
import json
import math
import os
import sys
import time
import traceback

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import ngfleet as N  # noqa: E402

N_MAX = 400
BASE, PER_1000, CAP_S = 40.0, 400.0, 200.0   # column-generation seconds per instance
R2_SHARE = 0.35                              # share of it for the R2 phase
FINAL_S = 60.0                               # final finer ng evaluations
GLOBAL_S = 3.0 * 3600.0
T0 = time.time()


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def budget(n):
    return min(CAP_S, BASE + PER_1000 * n / 1000.0)


def peak_gb():
    try:
        import resource
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0 / 1024.0, 3)
    except Exception:  # noqa: BLE001
        return None


def one(name, path, sol_path, cert_dir, budget_fn=budget, final_s=FINAL_S, q_price=N.Q_PRICE, q_final=N.Q_FINAL):
    import tmatch as TM
    import xltwlb as X
    import xtwfleet as XW
    t0 = time.monotonic()
    with open(path, encoding="utf-8") as f:
        inst = X.parse_any(f.read())
    inst["name"] = name
    rows = inst["rows"]
    n = len(rows) - 1
    rec = {"instance": name, "customers": n, "capacity": inst["capacity"], "cap_lb": XW.cap_lb(inst),
           "capfree": bool(sum(r[2] for r in rows[1:]) <= inst["capacity"])}
    routes = []
    if sol_path:
        with open(sol_path, encoding="utf-8") as f:
            routes, cost = XW.parse_sol(f.read())
        chk = XW.check_sol(inst, routes)
        rec.update({"bks_vehicles": len(routes), "bks_cost_stated": cost, "bks_check": chk,
                    "bks_ok": bool(chk["ok"] and (cost is None or abs(chk["cost"] - cost) < 0.5))})
    else:
        rec.update({"bks_vehicles": None, "bks_ok": False, "bks_check": {"ok": False, "why": "no BKS file"}})
    TI = TM.Inst(inst)
    if TI.unservable or TI.overweight:
        rec["error"] = "instance has customers no route can serve"
        return rec
    if float(TI.s.min()) < 1:
        rec["error"] = "a service time is below 1: skipping zero-profit customers is not proven safe"
        return rec
    ub = rec["bks_vehicles"] if rec["bks_ok"] else None
    init = [[c - 1 for c in r] for r in routes] if rec["bks_ok"] else []
    b = budget_fn(n)
    res = N.cg_two_phase(TI.C, TI.e, TI.l, n, t0 + R2_SHARE * b, t0 + b, t0 + b + final_s, ub=ub, init=init,
                         q_price=q_price, q_final=q_final, say=lambda m: None)
    rec["cg"] = {"lb_r2": float(res["lb_r2"]), "lb_ng": float(res["lb_ng"]), "z_rmp": res["z_rmp"],
                 "stop": res["stop"], "iterations": res["iterations"], "columns": res["columns"],
                 "final": res["final"], "history_tail": res["history"][-12:]}
    bks0 = [[c - 1 for c in r] for r in routes] if rec["bks_ok"] else []
    ints = {}
    for ph in ("r2", "ng"):
        c = res["cert"][ph]
        if c is None:
            ints[ph] = None
            rec["cg"]["recheck_" + ph] = None
            continue
        rc = N.recheck(TI.C, TI.e, TI.l, c)
        rp = N.route_profit_ok(c, bks0) if bks0 else None
        good = bool(rc and (rp is None or rp["ok"]))
        ints[ph] = N.fceil(res["lb_" + ph]) if good else None
        rec["cg"]["recheck_" + ph] = rc
        rec["cg"]["route_check_" + ph] = rp
        os.makedirs(cert_dir, exist_ok=True)
        cc = dict(c)
        cc.update({"instance": name, "fleet_at_least": ints[ph], "recheck": rc, "route_check": rp,
                   "bound": "%d/%d" % (res["lb_" + ph].numerator, res["lb_" + ph].denominator),
                   "solver": "ngfleet " + N.VERSION + (" (R2 walks: cgfleet.price)" if ph == "r2" else
                                                      " (ng-routes + 2-cycle rule)")})
        with open(os.path.join(cert_dir, "%s.%s.json" % (name, ph)), "w", encoding="utf-8", newline="\n") as f:
            json.dump(cc, f)
    rec["bound_r2"], rec["bound_ng"] = ints["r2"], ints["ng"]
    parts = {"cap": rec["cap_lb"], "r2": ints["r2"], "ng": ints["ng"]}
    vals = [v for v in parts.values() if v is not None]
    rec["bound"] = max(vals) if vals else None
    rec["bound_sources"] = sorted(k for k, v in parts.items() if v is not None and v == rec["bound"])
    k = rec["bks_vehicles"]
    good = bool(rec["bks_ok"] and k is not None and rec["bound"] is not None)
    rec["proved"] = bool(good and rec["bound"] >= k)
    rec["above_bks"] = bool(good and rec["bound"] > k)
    base = max([v for v in (parts["cap"], parts["r2"]) if v is not None] or [0])
    rec["ng_only_proof"] = bool(rec["proved"] and ints["ng"] is not None and ints["ng"] >= k and base < k)
    rec["gap"] = (k - rec["bound"]) if good else None
    rec["lp_ratio"] = (round(float(res["lb_ng"]) / float(res["lb_r2"]), 4)
                       if res["lb_r2"] > 0 and res["lb_ng"] > 0 else None)
    rec["unverified"] = bool(any(rec["cg"].get("recheck_" + ph) is False for ph in ("r2", "ng"))
                             or any((rec["cg"].get("route_check_" + ph) or {}).get("ok") is False
                                    for ph in ("r2", "ng")))
    rec["seconds"] = round(time.monotonic() - t0, 1)
    rec["peak_gb"] = peak_gb()
    return rec


def tally(recs):
    ok = [r for r in recs if not r.get("error") and r.get("bound") is not None]
    both = [r for r in ok if r.get("bound_r2") is not None and r.get("bound_ng") is not None]
    ratios = [r["lp_ratio"] for r in ok if r.get("lp_ratio") is not None]
    stalls = [r for r in ok if (r["cg"]["stop"] or {}).get("ng") == "stalled"]
    return {
        "instances": len(recs),
        "done": len(ok),
        "errors": [r["instance"] for r in recs if r.get("error")],
        "bks_ok": sum(1 for r in ok if r.get("bks_ok")),
        "unverified": [r["instance"] for r in ok if r.get("unverified")],
        "above_bks": [r["instance"] for r in ok if r.get("above_bks")],
        "ng_int_gain": [r["instance"] for r in both if r["bound_ng"] > r["bound_r2"]],
        "ng_int_loss": [r["instance"] for r in both if r["bound_ng"] < r["bound_r2"]],
        "both": len(both),
        "lp_ratio_median": round(float(np.median(ratios)), 4) if ratios else None,
        "lp_ratio_max": round(float(max(ratios)), 4) if ratios else None,
        "proved": [r["instance"] for r in ok if r.get("proved")],
        "ng_only_proof": [r["instance"] for r in ok if r.get("ng_only_proof")],
        "ng_stalled": len(stalls),
        "sum_bound": sum(r["bound"] for r in ok if r.get("bks_ok")),
        "sum_bks": sum(r["bks_vehicles"] for r in ok if r.get("bks_ok")),
        "numba": N.HAVE_NUMBA,
        "peak_gb": max([r["peak_gb"] for r in ok if r.get("peak_gb") is not None] or [None]) if ok else None,
    }


def write_md(path, res):
    t = res["tally"]
    L = ["# ngfleet on XTW (n <= %d): R2 walks vs ng-routes in the fleet bound" % N_MAX, "",
         "Pre-registered in PREREG.md. ngfleet %s. BKS downloaded %s. Certificates in cert/." % (
             N.VERSION, (res.get("manifest") or {}).get("bks_downloaded_utc")), "",
         "Tally: `%s`" % json.dumps(t), "",
         "| instance | n | BKS fleet | BKS check | cap | R2 LP bound | ng LP bound | R2 | ng | bound | proved | "
         "R2 stop | ng stop | s |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["instances"]:
        if r.get("error"):
            L.append("| %s | error: %s |||||||||||||" % (r["instance"], str(r["error"]).strip().splitlines()[-1]))
            continue
        cg = r.get("cg") or {}
        st = cg.get("stop") or {}
        L.append("| %s | %s | %s | %s | %s | %.3f | %.3f | %s | %s | %s | %s | %s | %s | %s |" % (
            r["instance"], r["customers"], r.get("bks_vehicles"), "ok" if r.get("bks_ok") else "no", r.get("cap_lb"),
            cg.get("lb_r2", 0.0), cg.get("lb_ng", 0.0), r.get("bound_r2"), r.get("bound_ng"), r.get("bound"),
            "yes" if r.get("proved") else "", st.get("r2"), st.get("ng"), r.get("seconds")))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


def run_all(man, out_dir, only=(), n_max=N_MAX, global_s=GLOBAL_S, budget_fn=budget, final_s=FINAL_S,
            q_price=N.Q_PRICE, q_final=N.Q_FINAL):
    import xtwfleet as XW
    start = time.monotonic()
    out = os.path.join(out_dir, "ngfleet")
    cert_dir = os.path.join(out, "cert")
    os.makedirs(out, exist_ok=True)
    insts = XW.files_by_stem(man["instances"]["dir"], {".vrp", ".txt", ".vrptw"})
    sols = XW.files_by_stem(man["bks"]["dir"], {".sol", ".txt"})
    names = [x for x in only if x] or [k for k in sorted(insts, key=lambda k: (XW.size_of(k), k))
                                       if k.upper().startswith("XTW") and XW.size_of(k) <= n_max]
    res = {"study": "ngfleet xtwprobe " + N.VERSION, "python": sys.version.split()[0], "numpy": np.__version__,
           "numba": N.HAVE_NUMBA,
           "settings": {"n_max": n_max, "budget": [BASE, PER_1000, CAP_S], "r2_share": R2_SHARE, "final_s": final_s,
                        "global_s": global_s, "ng": N.NG, "B": N.BSLOTS, "q_price": q_price, "q_final": q_final},
           "manifest": {"code": man.get("code"), "instances_sha256": man["instances"].get("sha256"),
                        "bks_sha256": man["bks"].get("sha256"), "bks_downloaded_utc": man["bks"].get("downloaded_utc"),
                        "prereg_sha256": man.get("prereg_sha256")},
           "files": {"instances": len(insts), "bks": len(sols)}, "plan": names, "instances": []}
    res_path = os.path.join(out, "results.json")
    log("plan: %d instances (numba %s)" % (len(names), N.HAVE_NUMBA))
    for name in names:
        if time.monotonic() - start > global_s:
            res["instances"].append({"instance": name, "error": "global time budget used"})
            continue
        try:
            rec = one(name, insts[name], sols.get(name), cert_dir, budget_fn=budget_fn, final_s=final_s,
                      q_price=q_price, q_final=q_final)
        except Exception:  # noqa: BLE001 - recorded
            rec = {"instance": name, "error": traceback.format_exc()}
        res["instances"].append(rec)
        res["tally"] = tally(res["instances"])
        with open(res_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(res, f, indent=1)
        log(json.dumps({k: rec.get(k) for k in ("instance", "customers", "bks_vehicles", "bks_ok", "cap_lb",
                                               "bound_r2", "bound_ng", "proved", "seconds", "error")}))
    res["tally"] = tally(res["instances"])
    with open(res_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1)
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
