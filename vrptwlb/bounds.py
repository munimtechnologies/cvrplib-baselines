"""Fleet lower bounds for CVRPLib's 356 VRPTW instances, against SINTEF's fewest-vehicles records.

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.

CVRPLib's VRPTW BKS Challenge ranks by vehicles first. For each Solomon and Gehring-Homberger instance this script
computes two classic lower bounds on the number of vehicles and compares them with SINTEF's hierarchical records
(double precision), CVRPLib's BKS route counts (DIMACS) and the vrptwl/ PyVRP runs:

- capacity bound KC = ceil(total demand / vehicle capacity);
- time-window bound KT = size of a clique of pairwise incompatible customers (no route can serve both, in either
  order), found by greedy search. Any such clique is a valid bound, so a heuristic clique is enough.

A record that equals max(KC, KT) cannot use fewer vehicles. KT is computed in double precision (travel time =
Euclidean distance) and under DIMACS (each arc truncated to 0.1); every clique is re-checked pair by pair in exact
50-digit decimal arithmetic. Predictions: expectations.md, scored by score_b() below.
"""
import argparse
import json
import math
import os
import re
import time
import traceback
import urllib.request
from decimal import Decimal, ROUND_FLOOR, getcontext

import numpy as np

BASE = "https://galgos.inf.puc-rio.br/cvrplib/en/download"
SINTEF_URL = "https://www.sintef.no/projectweb/top/vrptw/%d-customers/"
SIZES = (100, 200, 400, 600, 800, 1000)
UA = "CVRPLib VRPTW fleet bounds - MV2 of Munim, Inc. (mv2@munimtech.com)"
EPS = 1e-6
EXPECTED = 356
SEED = 20261031
STARTS = 32
SHUFFLES = 64
FAMILIES = ("C1", "C2", "R1", "R2", "RC1", "RC2")
NAME = r"(?:rc|c|r)[12](?:_\d{1,2}_\d{1,2}|\d{2})"
T0 = time.time()
getcontext().prec = 50


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def fetch(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        body = r.read()
    with open(path, "wb") as f:
        f.write(body)
    time.sleep(2)
    return path


def parse_ids(spec):
    """'676-678,700' -> ['676', '677', '678', '700']"""
    out = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            out.extend(str(i) for i in range(int(a), int(b) + 1))
        elif part:
            out.append(part)
    return out


def _num(tok):
    v = float(tok)
    return int(v) if v.is_integer() else v


def parse_solomon(text):
    """Return {name, vehicles, capacity, rows, raw}; rows[i] = (x, y, demand, ready, due, service).
    raw keeps the tokens as written, for the exact check."""
    name, vehicles, capacity, rows, raw = None, None, None, {}, {}
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        if name is None:
            name = parts[0].upper()
            continue
        try:
            nums = [_num(p) for p in parts]
        except ValueError:
            continue
        if len(nums) == 2 and vehicles is None:
            vehicles, capacity = nums
        elif len(nums) == 7:
            rows[int(nums[0])] = tuple(nums[1:])
            raw[int(nums[0])] = tuple(parts[1:])
    if vehicles is None or not rows:
        raise ValueError("not a Solomon-format file")
    if sorted(rows) != list(range(len(rows))):
        raise ValueError("customer numbers are not 0..n")
    return {"name": name, "vehicles": vehicles, "capacity": capacity,
            "rows": [rows[i] for i in range(len(rows))], "raw": [raw[i] for i in range(len(raw))]}


def parse_sol(text):
    """Return (routes, cost as float or None) from a CVRPLib solution file."""
    routes, cost = [], None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Route #"):
            routes.append([int(x) for x in line.split(":", 1)[1].split()])
        elif line.startswith("Cost"):
            cost = float(line.split()[1])
    return routes, cost


def parse_sintef(html):
    """{NAME: (vehicles, distance)} from a SINTEF TOP VRPTW page (first row per name wins)."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"_ (?=\d)", "_", text)  # a line break inside a link, e.g. 'r2_8_ 1'
    out = {}
    for m in re.finditer(r"\b(%s)\s?(?:[a-z]\s+)?(\d{1,3})\s+(\d+\.\d+)" % NAME, text, re.I):
        out.setdefault(m.group(1).upper(), (int(m.group(2)), float(m.group(3))))
    return out


def family(name):
    """'RC1_10_1' -> 'RC1'; 'RC101' -> 'RC1'; 'C205' -> 'C2'."""
    if "_" in name:
        return name.split("_")[0]
    return name[:-2]


def capacity_bound(inst):
    total = sum(r[2] for r in inst["rows"][1:])
    return int(math.ceil(total / inst["capacity"] - 1e-9))


def travel(inst, conv):
    """Travel-time matrix: 'double' = Euclidean distance, 'dimacs' = truncated to one decimal."""
    xy = np.array([(r[0], r[1]) for r in inst["rows"]], dtype=np.float64)
    d = np.hypot(xy[:, None, 0] - xy[None, :, 0], xy[:, None, 1] - xy[None, :, 1])
    if conv == "dimacs":
        d = np.floor(d * 10.0) / 10.0  # floating error can only shorten an arc here, which keeps the bound valid
    return d


def dimacs_ok(inst):
    """Under truncation the direct arc is the quickest way from i to j only if every service time is at least 0.2
    (each extra arc can save at most 0.1); the bound is computed for DIMACS only then."""
    return min(r[5] for r in inst["rows"][1:]) >= 0.2


def incompatible(inst, conv):
    """n x n bool matrix over customers 1..n: True if no route can serve both, in either order.
    e = earliest service start, l = latest start that still meets the due time and the depot's closing time."""
    rows = inst["rows"]
    t = travel(inst, conv)
    a = np.array([r[3] for r in rows], dtype=np.float64)
    b = np.array([r[4] for r in rows], dtype=np.float64)
    s = np.array([r[5] for r in rows], dtype=np.float64)
    e = np.maximum(a, a[0] + t[0])
    lat = np.minimum(b, b[0] - s - t[:, 0])
    order_ok = np.maximum(a[None, :], (e + s)[:, None] + t) <= lat[None, :] + EPS
    comp = order_ok | order_ok.T
    inc = ~comp[1:, 1:]
    np.fill_diagonal(inc, False)
    unservable = [i for i in range(1, len(rows)) if e[i] > lat[i] + EPS]
    return inc, unservable


def greedy_clique(adj, order):
    clique, cand = [], np.ones(len(adj), dtype=bool)
    for v in order:
        if cand[v]:
            clique.append(int(v))
            cand &= adj[v]
    return clique


def dynamic_clique(adj, start):
    clique, cand = [int(start)], adj[start].copy()
    while cand.any():
        idx = np.flatnonzero(cand)
        deg = adj[np.ix_(idx, idx)].sum(axis=1)
        v = int(idx[int(np.argmax(deg))])
        clique.append(v)
        cand &= adj[v]
    return clique


def best_clique(adj, rows, seed=SEED):
    """Largest clique found by several greedy passes; customer numbers (1..n), sorted."""
    n = len(adj)
    if n == 0 or not adj.any():
        return [1] if n else []
    deg = adj.sum(axis=1)
    by_deg = np.argsort(-deg, kind="stable")
    due = np.array([r[4] for r in rows[1:]])
    ready = np.array([r[3] for r in rows[1:]])
    orders = [by_deg, np.argsort(due, kind="stable"), np.argsort(ready, kind="stable")]
    rng = np.random.default_rng(seed)
    orders += [rng.permutation(n) for _ in range(SHUFFLES)]
    best = []
    for o in orders:
        c = greedy_clique(adj, o)
        if len(c) > len(best):
            best = c
    for v in by_deg[:STARTS]:
        c = dynamic_clique(adj, v)
        if len(c) > len(best):
            best = c
    return sorted(v + 1 for v in best)


def verify_clique_exact(inst, clique, conv):
    """Separate check in 50-digit decimals from the file's own tokens: every pair in the clique is incompatible.
    Returns (ok, first failing pair or None)."""
    raw = inst["raw"]
    x = [Decimal(r[0]) for r in raw]
    y = [Decimal(r[1]) for r in raw]
    a = [Decimal(r[3]) for r in raw]
    b = [Decimal(r[4]) for r in raw]
    s = [Decimal(r[5]) for r in raw]
    eps = Decimal("0.000001")
    cache = {}

    def tt(i, j):
        k = (min(i, j), max(i, j))
        if k not in cache:
            d = ((x[i] - x[j]) ** 2 + (y[i] - y[j]) ** 2).sqrt()
            if conv == "dimacs":
                d = (d * 10).to_integral_value(rounding=ROUND_FLOOR) / 10
            cache[k] = d
        return cache[k]

    def e(i):
        return max(a[i], a[0] + tt(0, i))

    def lat(i):
        return min(b[i], b[0] - s[i] - tt(i, 0))

    def can(i, j):
        return max(a[j], e(i) + s[i] + tt(i, j)) <= lat(j) + eps

    for p in range(len(clique)):
        for q in range(p + 1, len(clique)):
            i, j = clique[p], clique[q]
            if can(i, j) or can(j, i):
                return False, [i, j]
    return True, None


def bound_one(inst):
    kc = capacity_bound(inst)
    out = {"kc": kc}
    for conv in ("double", "dimacs"):
        if conv == "dimacs" and not dimacs_ok(inst):
            out[conv] = None
            continue
        inc, unservable = incompatible(inst, conv)
        clique = best_clique(inc, inst["rows"])
        ok, bad = verify_clique_exact(inst, clique, conv)
        n = len(inc)
        out[conv] = {"kt": len(clique), "k": max(kc, len(clique)), "clique": clique, "verified": ok,
                     "bad_pair": bad, "unservable": unservable,
                     "density": round(float(inc.sum()) / max(n * (n - 1), 1), 4)}
    return out


def score_b(t):
    """Verdicts for B0-B5 (expectations.md) from the tally."""
    def verdict(ok):
        return "untestable" if ok is None else ("held" if ok else "did not hold")
    share = t["sintef_at_bound_share"]
    r101 = t["r101"]
    return {
        "B0": verdict(t["instances"] == EXPECTED and not t["run_errors"] and not t["sintef_missing"]
                      and not t["clique_unverified"] and not t["unservable"]),
        "B1": verdict(not t["sintef_below_bound"] and not t["bks_below_bound"] and not t["vrptwl_below_bound"]),
        "B2": verdict(None if not t["vrptwl_early"] else not t["early_kc_mismatch"]),
        "B3": verdict(None if t["tw_above_kc_1000"] is None else t["tw_above_kc_1000"] <= 5),
        "B4": verdict(None if r101 is None else r101["kt_double"] > r101["kc"]),
        "B5": verdict(None if share is None else 0.40 <= share <= 0.70),
    }


def tally_recs(recs, fleets):
    ok = [r for r in recs if r.get("bounds")]
    with_sintef = [r for r in ok if r.get("sintef")]
    big = [r for r in ok if r["customers"] == 1000]
    early = sorted(k for k, v in fleets.items() if not k.startswith("_") and v[1] < 299)
    by_name = {r["instance"]: r for r in ok}
    r101 = by_name.get("R101")

    def kd(r):
        return r["bounds"]["double"]["k"]

    at = [r for r in with_sintef if r["sintef"][0] == kd(r)]
    t = {
        "instances": len(recs),
        "run_errors": [r["instance"] for r in recs if r.get("error")],
        "sintef_missing": [r["instance"] for r in ok if not r.get("sintef")],
        "clique_unverified": [r["instance"] + "/" + c for r in ok for c in ("double", "dimacs")
                              if r["bounds"][c] and not r["bounds"][c]["verified"]],
        "unservable": [r["instance"] for r in ok if r["bounds"]["double"]["unservable"]],
        "dimacs_skipped": [r["instance"] for r in ok if r["bounds"]["dimacs"] is None],
        "sintef_below_bound": [r["instance"] for r in with_sintef if r["sintef"][0] < kd(r)],
        "bks_below_bound": [r["instance"] for r in ok if r["bounds"]["dimacs"]
                            and r["bks_routes"] < r["bounds"]["dimacs"]["k"]],
        "vrptwl_below_bound": [r["instance"] for r in ok if r.get("vrptwl") and r["vrptwl"][2] < kd(r)],
        "vrptwl_early": early,
        "early_kc_mismatch": [k for k in early if k in by_name and by_name[k]["bounds"]["kc"] != fleets[k][0]],
        "tw_above_kc_1000": (sum(1 for r in big if r["bounds"]["double"]["kt"] > r["bounds"]["kc"])
                             if big else None),
        "r101": None if not r101 else {"kc": r101["bounds"]["kc"], "kt_double": r101["bounds"]["double"]["kt"],
                                       "sintef": r101["sintef"][0] if r101.get("sintef") else None},
        "sintef_at_bound": len(at),
        "sintef_at_bound_share": round(len(at) / len(with_sintef), 4) if with_sintef else None,
        "sintef_at_bound_by_size": {str(n): [sum(1 for r in at if r["customers"] == n),
                                             sum(1 for r in with_sintef if r["customers"] == n)] for n in SIZES},
        "sintef_at_bound_by_family": {f: [sum(1 for r in at if r["family"] == f),
                                          sum(1 for r in with_sintef if r["family"] == f)] for f in FAMILIES},
        "tw_binding": [r["instance"] for r in with_sintef if r["bounds"]["double"]["kt"] > r["bounds"]["kc"]],
        "vehicle_gap_total": sum(r["sintef"][0] - kd(r) for r in with_sintef),
        "open_1000": sorted(([r["instance"], r["sintef"][0] - kd(r)] for r in big
                             if r.get("sintef") and r["sintef"][0] > kd(r)), key=lambda p: (-p[1], p[0])),
    }
    t["predictions"] = score_b(t)
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="380-735")
    ap.add_argument("--fleets", default="vrptwl_fleets.json")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    args = ap.parse_args()

    src = os.path.join(args.data_dir, "cvrplib-vrptw")
    out = os.path.join(args.out_dir, "vrptwlb")
    for d in (src, out):
        os.makedirs(d, exist_ok=True)
    with open(args.fleets, encoding="utf-8") as f:
        fleets = json.load(f)

    sintef, pages = {}, {}
    for n in SIZES:
        try:
            req = urllib.request.Request(SINTEF_URL % n, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                rows = parse_sintef(r.read().decode("utf-8", "replace"))
            pages[str(n)] = len(rows)
            for k, v in rows.items():
                sintef.setdefault(k, v)
        except Exception as e:
            pages[str(n)] = repr(e)
        time.sleep(2)
    log("SINTEF rows per page: %s" % json.dumps(pages))

    recs = []
    for i in parse_ids(args.ids):
        rec = {"id": i}
        try:
            p = fetch("%s/instance/%s" % (BASE, i), os.path.join(src, "%s.txt" % i))
            s = fetch("%s/bks/%s" % (BASE, i), os.path.join(src, "%s.sol" % i))
            with open(p, encoding="utf-8") as f:
                inst = parse_solomon(f.read())
            with open(s, encoding="utf-8") as f:
                bks_routes, _ = parse_sol(f.read())
            name = inst["name"]
            rec.update({"instance": name, "family": family(name), "customers": len(inst["rows"]) - 1,
                        "bks_routes": len(bks_routes), "sintef": list(sintef[name]) if name in sintef else None,
                        "vrptwl": fleets.get(name)})
            rec["bounds"] = bound_one(inst)
        except Exception:
            rec.setdefault("instance", "id%s" % i)
            rec["error"] = traceback.format_exc()
            log("%s ERROR %s" % (rec["instance"], rec["error"]))
        recs.append(rec)
        if rec.get("bounds"):
            bd, bm = rec["bounds"]["double"], rec["bounds"]["dimacs"]
            log("%s: KC %d, KT double %d (verified %s), KT DIMACS %s, SINTEF %s, BKS routes %d" % (
                rec["instance"], rec["bounds"]["kc"], bd["kt"], bd["verified"], bm and bm["kt"],
                rec["sintef"] and rec["sintef"][0], rec["bks_routes"]))

    tally = tally_recs(recs, fleets)
    cliques = {r["instance"]: {c: r["bounds"][c]["clique"] for c in ("double", "dimacs") if r["bounds"][c]}
               for r in recs if r.get("bounds")}
    for r in recs:
        for c in ("double", "dimacs"):
            if r.get("bounds") and r["bounds"][c]:
                del r["bounds"][c]["clique"]
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump({"eps": EPS, "seed": SEED, "sintef_pages": pages, "tally": tally, "instances": recs}, f, indent=1)
    with open(os.path.join(out, "cliques.json"), "w", encoding="utf-8") as f:
        json.dump(cliques, f)
    head = ["id", "instance", "customers", "KC", "KT_double", "K_double", "KT_dimacs", "K_dimacs",
            "SINTEF_vehicles", "SINTEF_minus_K", "CVRPLib_BKS_routes", "PyVRP_vrptwl", "density_double"]
    csv = [",".join(head)]
    md = ["# Fleet lower bounds against SINTEF's fewest-vehicles records", "",
          "KC = ceil(demand / capacity); KT = clique of pairwise incompatible customers (verified exactly); "
          "K = max(KC, KT).", "",
          "Predictions: `%s`" % json.dumps(tally["predictions"]), "",
          "Tally: `%s`" % json.dumps({k: v for k, v in tally.items() if k != "predictions"}), "",
          "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in recs:
        if not r.get("bounds"):
            md.append("| %s | %s | error |" % (r["id"], r["instance"]))
            continue
        bd, bm = r["bounds"]["double"], r["bounds"]["dimacs"]
        sv = r["sintef"][0] if r.get("sintef") else ""
        row = [r["id"], r["instance"], r["customers"], r["bounds"]["kc"], bd["kt"], bd["k"],
               bm["kt"] if bm else "", bm["k"] if bm else "", sv, (sv - bd["k"]) if sv != "" else "",
               r["bks_routes"], r["vrptwl"][2] if r.get("vrptwl") else "", bd["density"]]
        csv.append(",".join(str(v) for v in row))
        md.append("| " + " | ".join(str(v) for v in row) + " |")
    with open(os.path.join(out, "bounds.csv"), "w", encoding="utf-8") as f:
        f.write("\n".join(csv) + "\n")
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(json.dumps(tally), flush=True)


if __name__ == "__main__":
    main()
