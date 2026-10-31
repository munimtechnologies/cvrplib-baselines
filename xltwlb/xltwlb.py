"""Fleet lower bounds for large VRPTW instances (VRPLIB or Solomon format), built for CVRPLib's XLTW-Test set.

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.

Extends vrptwlb/bounds.py (classical bounds after Kontoravdis & Bard 1995; Afifi, Guibadj and Moukrim, CPAIOR 2014,
give stronger ones) to instances of up to 10,000 customers:

- KC = ceil(total demand / vehicle capacity);
- KB = Martello-Toth L2 bin-packing bound on the demands (Discrete Applied Mathematics 28, 1990), never below KC;
- KT = size of a clique of pairwise incompatible customers (no route can serve both, in either order, because of
  time windows or because their demands together exceed the capacity), found by greedy search. The incompatibility
  matrix is built in row blocks, so 10,000 customers need about 0.3 GB. Every clique is re-checked pair by pair in
  50-digit decimals from the file's own tokens.

K = max(KB, KT) vehicles are needed. Travel time = distance under one of three conventions: 'double' (Euclidean),
'dimacs' (truncated to 0.1) or 'round' (nearest integer, CVRPLib's CVRP rule). Under 'dimacs' and 'round' a detour
can be shorter than the direct arc, so the time-window part is computed only when every service time covers the
largest possible saving (SLACK).
"""
import argparse
import glob
import json
import math
import os
import time
import traceback
from decimal import Decimal, ROUND_FLOOR, getcontext

import numpy as np

EPS = 1e-6
SEED = 20261031
STARTS = 32
SHUFFLES = 64
BLOCK = 512
CONVS = ("double", "dimacs", "round")
SLACK = {"double": 0.0, "dimacs": 0.2, "round": 1.0}
SECTIONS = ("NODE_COORD_SECTION", "DEMAND_SECTION", "TIME_WINDOW_SECTION", "SERVICE_TIME_SECTION")
T0 = time.time()
getcontext().prec = 50


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def _num(tok):
    v = float(tok)
    return int(v) if v.is_integer() else v


def _is_num(tok):
    try:
        float(tok)
        return True
    except ValueError:
        return False


def parse_solomon(text):
    """Return {name, vehicles, capacity, rows, raw}; rows[i] = (x, y, demand, ready, due, service), depot first.
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


def parse_vrplib(text):
    """Same dict as parse_solomon from a VRPLIB file with NODE_COORD, DEMAND, TIME_WINDOW and (optional)
    SERVICE_TIME sections. The depot comes first; customers follow in id order. Explicit matrices are refused."""
    head, sec, data, depots = {}, None, {s: {} for s in SECTIONS}, []
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        word = parts[0].rstrip(":").upper()
        if word == "EOF":
            break
        if not _is_num(parts[0]):
            if word.endswith("_SECTION"):
                sec = word
            elif ":" in line:
                k, v = line.split(":", 1)
                head[k.strip().upper()] = v.strip()
                sec = None
            continue
        if sec == "DEPOT_SECTION":
            if int(float(parts[0])) >= 0:  # -1 ends the section
                depots.append(int(float(parts[0])))
        elif sec in data:
            data[sec][int(float(parts[0]))] = parts[1:]
        else:
            raise ValueError("unsupported section %s" % sec)
    coords, tw = data["NODE_COORD_SECTION"], data["TIME_WINDOW_SECTION"]
    if not coords or not tw:
        raise ValueError("needs NODE_COORD_SECTION and TIME_WINDOW_SECTION")
    if len(depots) > 1:
        raise ValueError("more than one depot")
    ids = sorted(coords)
    depot = depots[0] if depots else ids[0]
    service = head.get("SERVICE_TIME", "0")
    rows, raw = [], []
    for i in [depot] + [i for i in ids if i != depot]:
        tok = (coords[i][0], coords[i][1], data["DEMAND_SECTION"].get(i, ["0"])[0], tw[i][0], tw[i][1],
               data["SERVICE_TIME_SECTION"].get(i, [service])[0])
        raw.append(tok)
        rows.append(tuple(_num(t) for t in tok))
    vehicles = head.get("VEHICLES")
    return {"name": head.get("NAME", "?"), "vehicles": _num(vehicles) if vehicles else None,
            "capacity": _num(head["CAPACITY"]), "rows": rows, "raw": raw}


def parse_any(text):
    return parse_vrplib(text) if "_SECTION" in text.upper() else parse_solomon(text)


def write_vrplib(inst):
    """VRPLIB text for an instance dict (depot = node 1)."""
    rows = inst["rows"]
    out = ["NAME : %s" % inst["name"], "TYPE : VRPTW", "DIMENSION : %d" % len(rows),
           "EDGE_WEIGHT_TYPE : EUC_2D", "CAPACITY : %s" % inst["capacity"], "NODE_COORD_SECTION"]
    out += ["%d %s %s" % (i + 1, r[0], r[1]) for i, r in enumerate(rows)]
    out.append("DEMAND_SECTION")
    out += ["%d %s" % (i + 1, r[2]) for i, r in enumerate(rows)]
    out.append("TIME_WINDOW_SECTION")
    out += ["%d %s %s" % (i + 1, r[3], r[4]) for i, r in enumerate(rows)]
    out.append("SERVICE_TIME_SECTION")
    out += ["%d %s" % (i + 1, r[5]) for i, r in enumerate(rows)]
    out += ["DEPOT_SECTION", "1", "-1", "EOF"]
    return "\n".join(out) + "\n"


def synthetic(n, seed=SEED):
    """Random instance for sizing runs: integer coordinates, every customer servable, half the windows narrow."""
    rng = np.random.default_rng(seed)
    xy = rng.integers(0, 1001, size=(n, 2))
    q = rng.integers(1, 101, size=n)
    horizon, service = 10000, 10
    cap = int(math.ceil(q.sum() / max(n // 10, 1)))
    rows = [(500, 500, 0, 0, horizon, 0)]
    for (x, y), d, narrow in zip(xy.tolist(), q.tolist(), (rng.random(n) < 0.5).tolist()):
        t0 = int(math.ceil(math.hypot(x - 500, y - 500))) + 1
        c = int(rng.integers(t0 + 1, horizon - t0 - service - 1))
        w = 60 if narrow else 2000
        rows.append((x, y, d, max(0, c - w // 2), c + w // 2, service))
    raw = [tuple(str(v) for v in r) for r in rows]
    return {"name": "SYN-n%d" % n, "vehicles": None, "capacity": cap, "rows": rows, "raw": raw}


def conv_time(d, conv):
    if conv == "dimacs":
        return np.floor(d * 10.0) / 10.0
    if conv == "round":
        return np.floor(d + 0.5)
    return d


def capacity_bound(inst):
    total = sum(r[2] for r in inst["rows"][1:])
    return int(math.ceil(total / inst["capacity"] - 1e-9))


def bin_packing_bound(demands, cap):
    """Martello-Toth L2: for each alpha in [0, cap/2], items above cap - alpha and items above cap/2 each need
    their own bin, and items in [alpha, cap/2] must fit into what those bins leave over plus new bins."""
    w = np.array([x for x in demands if x > 0], dtype=np.float64)
    best = int(math.ceil(w.sum() / cap - 1e-9)) if len(w) else 0
    for alpha in sorted({0.0} | set(w[w <= cap / 2.0].tolist())):
        j1 = w > cap - alpha
        j2 = (w <= cap - alpha) & (w > cap / 2.0)
        j3 = (w <= cap / 2.0) & (w >= alpha)
        rest = w[j3].sum() - (j2.sum() * cap - w[j2].sum())
        lb = int(j1.sum() + j2.sum()) + max(0, int(math.ceil(rest / cap - 1e-9)))
        best = max(best, lb)
    return best


def tw_ok(inst, conv):
    return min(r[5] for r in inst["rows"][1:]) >= SLACK[conv]


def incompatible(inst, conv, block=BLOCK):
    """n x n bool matrix over customers 1..n (index 0 = customer 1): True if no route can serve both.
    e = earliest service start, lat = latest start that still meets the due time and the depot's closing time."""
    rows = inst["rows"]
    xy = np.array([(r[0], r[1]) for r in rows], dtype=np.float64)
    a = np.array([r[3] for r in rows], dtype=np.float64)
    b = np.array([r[4] for r in rows], dtype=np.float64)
    s = np.array([r[5] for r in rows], dtype=np.float64)
    q = np.array([r[2] for r in rows[1:]], dtype=np.float64)
    t0 = conv_time(np.hypot(xy[:, 0] - xy[0, 0], xy[:, 1] - xy[0, 1]), conv)
    e = np.maximum(a, a[0] + t0)
    lat = np.minimum(b, b[0] - s - t0)
    n = len(rows) - 1
    ok = np.empty((n, n), dtype=bool)
    cx, cy = xy[1:, 0], xy[1:, 1]
    for lo in range(1, n + 1, block):
        hi = min(lo + block, n + 1)
        d = conv_time(np.hypot(xy[lo:hi, 0, None] - cx[None, :], xy[lo:hi, 1, None] - cy[None, :]), conv)
        ok[lo - 1:hi - 1] = np.maximum(a[None, 1:], (e[lo:hi] + s[lo:hi])[:, None] + d) <= lat[None, 1:] + EPS
    inc = ok | ok.T
    del ok
    np.logical_not(inc, out=inc)
    for lo in range(0, n, block):
        inc[lo:lo + block] |= (q[lo:lo + block, None] + q[None, :]) > inst["capacity"] + EPS
    np.fill_diagonal(inc, False)
    unservable = [i for i in range(1, n + 1) if e[i] > lat[i] + EPS]
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


def exact_time(xi, yi, xj, yj, conv):
    d = ((xi - xj) ** 2 + (yi - yj) ** 2).sqrt()
    if conv == "dimacs":
        return (d * 10).to_integral_value(rounding=ROUND_FLOOR) / 10
    if conv == "round":
        return (d + Decimal("0.5")).to_integral_value(rounding=ROUND_FLOOR)
    return d


def verify_clique_exact(inst, clique, conv, capacity=None):
    """Separate check in 50-digit decimals from the file's own tokens: every pair in the clique is incompatible.
    Returns (ok, first failing pair or None)."""
    raw = inst["raw"]
    x = [Decimal(r[0]) for r in raw]
    y = [Decimal(r[1]) for r in raw]
    q = [Decimal(r[2]) for r in raw]
    a = [Decimal(r[3]) for r in raw]
    b = [Decimal(r[4]) for r in raw]
    s = [Decimal(r[5]) for r in raw]
    cap = Decimal(str(inst["capacity"] if capacity is None else capacity))
    eps = Decimal("0.000001")
    depot = {}

    def tt(i, j):
        return exact_time(x[i], y[i], x[j], y[j], conv)

    def t0(i):
        if i not in depot:
            depot[i] = tt(0, i)
        return depot[i]

    def e(i):
        return max(a[i], a[0] + t0(i))

    def lat(i):
        return min(b[i], b[0] - s[i] - t0(i))

    def can(i, j):
        return max(a[j], e(i) + s[i] + tt(i, j)) <= lat(j) + eps

    for p in range(len(clique)):
        for k in range(p + 1, len(clique)):
            i, j = clique[p], clique[k]
            if q[i] + q[j] <= cap + eps and (can(i, j) or can(j, i)):
                return False, [i, j]
    return True, None


def bound_one(inst, convs=CONVS):
    kc = capacity_bound(inst)
    kb = bin_packing_bound([r[2] for r in inst["rows"][1:]], inst["capacity"])
    out = {"customers": len(inst["rows"]) - 1, "capacity": inst["capacity"], "kc": kc, "kb": kb}
    for conv in convs:
        if not tw_ok(inst, conv):
            out[conv] = None
            continue
        t = time.time()
        inc, unservable = incompatible(inst, conv)
        t_inc = time.time() - t
        clique = best_clique(inc, inst["rows"])
        t_clq = time.time() - t - t_inc
        ok, bad = verify_clique_exact(inst, clique, conv)
        n = len(inc)
        out[conv] = {"kt": len(clique), "k": max(kb, len(clique)), "clique": clique, "verified": ok,
                     "bad_pair": bad, "unservable": unservable,
                     "density": round(float(inc.sum()) / max(n * (n - 1), 1), 4),
                     "seconds": [round(t_inc, 1), round(t_clq, 1), round(time.time() - t - t_inc - t_clq, 1)]}
        del inc
    return out


def peak_gb():
    try:
        import resource
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0 / 1024.0, 3)
    except Exception:  # noqa: BLE001 - not on Linux
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", default="", help="glob of instance files (VRPLIB or Solomon)")
    ap.add_argument("--synthetic", default="", help="comma-separated sizes, e.g. 1000,10000")
    ap.add_argument("--convs", default=",".join(CONVS))
    ap.add_argument("--out-dir", default="out")
    args = ap.parse_args()
    out = os.path.join(args.out_dir, "xltwlb")
    os.makedirs(out, exist_ok=True)
    convs = [c for c in args.convs.split(",") if c]

    jobs = [("synthetic", int(n)) for n in args.synthetic.split(",") if n]
    jobs += [("file", p) for p in sorted(glob.glob(args.files))] if args.files else []
    recs, cliques = [], {}
    for kind, what in jobs:
        rec = {"source": what if kind == "file" else "synthetic n=%d" % what}
        try:
            if kind == "file":
                with open(what, encoding="utf-8") as f:
                    inst = parse_any(f.read())
            else:
                inst = parse_vrplib(write_vrplib(synthetic(what)))  # the parser is exercised at full size too
            rec["instance"] = inst["name"]
            rec["bounds"] = bound_one(inst, convs)
            cliques[inst["name"]] = {c: rec["bounds"][c].pop("clique") for c in convs if rec["bounds"][c]}
        except Exception:
            rec["error"] = traceback.format_exc()
        rec["peak_gb"] = peak_gb()
        recs.append(rec)
        log(json.dumps({k: v for k, v in rec.items() if k != "error"}) + (" ERROR " + rec["error"]
                                                                          if rec.get("error") else ""))
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump({"eps": EPS, "seed": SEED, "convs": convs, "instances": recs}, f, indent=1)
    with open(os.path.join(out, "cliques.json"), "w", encoding="utf-8") as f:
        json.dump(cliques, f)
    if any(r.get("error") for r in recs):
        raise SystemExit("%d instance(s) failed" % sum(1 for r in recs if r.get("error")))


if __name__ == "__main__":
    main()
