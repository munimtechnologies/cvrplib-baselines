"""kmatch pilot: a path-cover (bipartite matching) fleet lower bound on CVRPLib's XLTW-Test, compared with K*.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

Exploratory pilot, NOT a pre-registered study (see pilot.md). Customer j may directly follow customer i on a route
only if  max(a_j, e_i + s_i + t_ij) <= lat_j , with e and lat as in xltwlb.py (earliest start reachable from the
depot; latest start that still meets the due time and the trip back to the depot) and t the challenge's
nearest-integer travel time. Every route is a path in this arc graph, so the vehicles needed are at least the
minimum number of vertex-disjoint paths that cover it, which is at least n - M (M = a maximum matching between
out-copies and in-copies of the customers) and at least 1. This is the classical assignment relaxation of fleet
sizing (Dantzig & Fulkerson's tanker scheduling, 1954); it ignores capacity and lets the matching close cycles.
Only the numbers on XLTW-Test are new.

Checks run on every instance: (1) every consecutive pair of every route of the exactly checked part-a solutions of
xltwrun/ must be an arc of the graph (otherwise the relaxation is wrong for that instance and it is flagged); (2) the
bound must not exceed the number of routes of that solution.

  python kmatch.py --data-dir /data --out-dir /out
"""
import argparse
import glob
import json
import os
import sys
import time
import traceback
import urllib.request

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

EPS = 1e-6
BLOCK = 512
SOLS_URL = ("https://raw.githubusercontent.com/munimtechnologies/cvrplib-baselines/"
            "56b4e6e1928066c7bb23bca3d7848895a3e239ac/xltwrun/sols/%s.sol")
REF_FILE = "xltwen-results.json"
UA = "kmatch pilot - MV2 of Munim, Inc. (mv2@munimtech.com)"
# best valid fleets found so far on the four capacity-free instances used by xltwfull/, xltwff/ and nbrm/ (whole T(n))
BEST = {"XLTW-Test-n1234": 33, "XLTW-Test-n1421": 65, "XLTW-Test-n1608": 108, "XLTW-Test-n1841": 25}
T0 = time.time()


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def travel(dx, dy):
    """Nearest-integer Euclidean travel time (CVRPLib's rule, xltwlb's 'round')."""
    return np.floor(np.hypot(dx, dy) + 0.5)


def windows(inst):
    rows = inst["rows"]
    xy = np.array([(r[0], r[1]) for r in rows], dtype=np.float64)
    a = np.array([r[3] for r in rows], dtype=np.float64)
    b = np.array([r[4] for r in rows], dtype=np.float64)
    s = np.array([r[5] for r in rows], dtype=np.float64)
    t0 = travel(xy[:, 0] - xy[0, 0], xy[:, 1] - xy[0, 1])
    e = np.maximum(a, a[0] + t0)
    lat = np.minimum(b, b[0] - s - t0)
    return xy, a, s, e, lat


def integer_coords(inst):
    """True if every coordinate token is a plain integer. Then dx^2 + dy^2 is exact in float64 and the rounded
    travel time cannot be off by one (sqrt of an integer is never within 1e-5 of k - 0.5 for k < 15,000)."""
    for r in inst["raw"]:
        for tok in r[:2]:
            try:
                int(tok)
            except ValueError:
                return False
    return True


def arc_matrix(inst, block=BLOCK):
    """CSR matrix over customers (row/column i = customer i + 1): entry (i, j) present if j can directly follow i."""
    from scipy.sparse import csr_matrix
    xy, a, s, e, lat = windows(inst)
    n = len(xy) - 1
    cx, cy = xy[1:, 0], xy[1:, 1]
    parts, counts = [], np.zeros(n, dtype=np.int64)
    for lo in range(1, n + 1, block):
        hi = min(lo + block, n + 1)
        d = travel(xy[lo:hi, 0, None] - cx[None, :], xy[lo:hi, 1, None] - cy[None, :])
        ok = np.maximum(a[None, 1:], (e[lo:hi] + s[lo:hi])[:, None] + d) <= lat[None, 1:] + EPS
        r = np.arange(hi - lo)
        ok[r, r + lo - 1] = False
        counts[lo - 1:hi - 1] = ok.sum(axis=1)
        parts.append(np.nonzero(ok)[1].astype(np.int32))
        del d, ok
    indices = np.concatenate(parts) if parts else np.zeros(0, dtype=np.int32)
    del parts
    indptr = np.zeros(n + 1, dtype=np.int64)
    np.cumsum(counts, out=indptr[1:])
    if indptr[-1] < 2 ** 31 - 1:
        indptr = indptr.astype(np.int32)
    return csr_matrix((np.ones(len(indices), dtype=np.int8), indices, indptr), shape=(n, n))


def unservable(inst):
    _, _, _, e, lat = windows(inst)
    return int((e[1:] > lat[1:] + EPS).sum())


def has_arc(G, i, j):
    lo, hi = int(G.indptr[i]), int(G.indptr[i + 1])
    k = int(np.searchsorted(G.indices[lo:hi], j))
    return k < hi - lo and int(G.indices[lo + k]) == j


def path_cover_bound(G):
    """km = max(n - M, 1); also how the matched arcs split into paths and cycles."""
    from scipy.sparse.csgraph import maximum_bipartite_matching
    n = G.shape[0]
    if n == 0:
        return {"km": 0, "matched": 0, "paths": 0, "cycles": 0, "cycle_vertices": 0, "matching_arcs_ok": True}
    succ = np.asarray(maximum_bipartite_matching(G, perm_type="column"), dtype=np.int64)
    idx = np.flatnonzero(succ >= 0)
    M = int(len(idx))
    arcs_ok = all(has_arc(G, int(i), int(succ[i])) for i in idx)
    pred = -np.ones(n, dtype=np.int64)
    pred[succ[idx]] = idx
    seen = np.zeros(n, dtype=bool)
    paths = 0
    for v in np.flatnonzero(pred < 0):
        paths += 1
        v = int(v)
        while v >= 0 and not seen[v]:
            seen[v] = True
            v = int(succ[v])
    cyc_v = int((~seen).sum())
    cycles = 0
    for v in np.flatnonzero(~seen):
        v = int(v)
        if seen[v]:
            continue
        cycles += 1
        while not seen[v]:
            seen[v] = True
            v = int(succ[v])
    return {"km": max(n - M, 1), "matched": M, "paths": paths, "cycles": cycles, "cycle_vertices": cyc_v,
            "matching_arcs_ok": bool(arcs_ok)}


def parse_sol(text):
    """CVRPLib solution text: 'Route #k: c1 c2 ...' lines; customers numbered 1..n."""
    routes = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("Route #"):
            routes.append([int(z) for z in s.partition(":")[2].split()])
    return routes


def route_check(routes, G):
    """Is every consecutive pair of every route an arc of G, and is every customer served exactly once?"""
    n = G.shape[0]
    count = np.zeros(n + 1, dtype=np.int64)
    in_range = True
    pairs, missing, examples = 0, 0, []
    for rt in routes:
        for c in rt:
            if 1 <= c <= n:
                count[c] += 1
            else:
                in_range = False
        for i, j in zip(rt, rt[1:]):
            pairs += 1
            if not (1 <= i <= n and 1 <= j <= n and has_arc(G, i - 1, j - 1)):
                missing += 1
                if len(examples) < 5:
                    examples.append([i, j])
    return {"routes": len(routes), "pairs": pairs, "missing_arcs": missing, "examples": examples,
            "covers_each_once": bool(in_range and (count[1:] == 1).all())}


def fetch(url, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8")
        except Exception:  # noqa: BLE001 - retried, then raised and recorded
            if k == tries - 1:
                raise
            time.sleep(5 * (k + 1))
    raise AssertionError("unreachable")


def load_ref(path):
    """{instance: {kc, k, e, kstar, vehicles_a}} from xltwen/results.json; {} if missing."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    out = {}
    for r in data.get("instances", []):
        k, e = r.get("k"), r.get("e")
        ks = max(x for x in (k, e) if x is not None) if (k is not None or e is not None) else None
        out[r["instance"]] = {"kc": r.get("kc"), "k": k, "e": e, "kstar": ks, "vehicles_a": r.get("vehicles_a")}
    return out


def find_files(data_dir):
    files = sorted(glob.glob(os.path.join(data_dir, "xltw-test", "x-*", "**", "*.vrp"), recursive=True))
    by_name = {}
    for p in files:
        by_name.setdefault(os.path.splitext(os.path.basename(p))[0], p)
    return by_name


def size_of(name):
    try:
        return int(name.rsplit("-n", 1)[1])
    except (IndexError, ValueError):
        return 10 ** 9


def order(names, ref):
    """The four instances of nbrm/ first, then the other capacity-free ones, then the rest; smallest first."""
    first = [n for n in BEST if n in names]
    capfree = sorted((n for n in names if n not in BEST and (ref.get(n) or {}).get("kc") == 1), key=size_of)
    rest = sorted((n for n in names if n not in BEST and n not in capfree), key=size_of)
    return first + capfree + rest


def peak_gb():
    try:
        import resource
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0 / 1024.0, 3)
    except Exception:  # noqa: BLE001 - not on Linux
        return None


def one(path, name, ref, sols_url, with_sol=True):
    import xltwlb as X
    t = time.time()
    with open(path, encoding="utf-8") as f:
        inst = X.parse_any(f.read())
    n = len(inst["rows"]) - 1
    rf = ref.get(name) or {}
    rec = {"instance": name, "customers": n, "kc": X.capacity_bound(inst), "kc_ref": rf.get("kc"), "k": rf.get("k"),
           "e": rf.get("e"), "kstar": rf.get("kstar"), "vehicles_a": rf.get("vehicles_a"), "best": BEST.get(name),
           "integer_coords": integer_coords(inst), "unservable": unservable(inst)}
    G = arc_matrix(inst)
    rec["arcs"] = int(G.nnz)
    rec["arc_density"] = round(G.nnz / float(max(n * (n - 1), 1)), 5)
    t_arcs = time.time() - t
    rec.update(path_cover_bound(G))
    rec["seconds_arcs"] = round(t_arcs, 1)
    rec["seconds_matching"] = round(time.time() - t - t_arcs, 1)
    if rec["kstar"] is not None:
        rec["km_minus_kstar"] = rec["km"] - rec["kstar"]
    if with_sol and rec["vehicles_a"]:
        try:
            rc = route_check(parse_sol(fetch(sols_url % name)), G)
            rc["km_le_routes"] = rec["km"] <= rc["routes"]
            rec["sol"] = rc
        except Exception as ex:  # noqa: BLE001 - recorded
            rec["sol"] = {"error": repr(ex)}
    if rec["best"] is not None:
        rec["km_le_best"] = rec["km"] <= rec["best"]
    del G
    rec["seconds"] = round(time.time() - t, 1)
    rec["peak_gb"] = peak_gb()
    return rec


def invalid(r):
    sol = r.get("sol") or {}
    return bool(sol.get("missing_arcs") or sol.get("km_le_routes") is False or r.get("km_le_best") is False
                or r.get("matching_arcs_ok") is False or r.get("paths") != r.get("customers", 0) - r.get("matched", 0))


def tally(recs):
    ok = [r for r in recs if not r.get("error")]
    withk = [r for r in ok if r.get("kstar") is not None]
    capfree = [r for r in withk if r["kc"] == 1]
    sols = [r for r in ok if (r.get("sol") or {}).get("routes") is not None]
    return {
        "instances_done": len(ok),
        "errors": [r["instance"] for r in recs if r.get("error")],
        "km_above_kstar": [[r["instance"], r["kstar"], r["km"]] for r in withk if r["km"] > r["kstar"]],
        "km_above_kstar_capacity_free": sum(1 for r in capfree if r["km"] > r["kstar"]),
        "capacity_free_with_kstar": len(capfree),
        "sum_kstar": sum(r["kstar"] for r in withk),
        "sum_max_kstar_km": sum(max(r["kstar"], r["km"]) for r in withk),
        "instances_with_cycles": sum(1 for r in ok if r.get("cycles")),
        "solutions_checked": len(sols),
        "solutions_not_covering": [r["instance"] for r in sols if not r["sol"]["covers_each_once"]],
        "invalid": [r["instance"] for r in ok if invalid(r)],
        "non_integer_coords": [r["instance"] for r in ok if not r["integer_coords"]],
        "unservable": [r["instance"] for r in ok if r.get("unservable")],
    }


def write_md(path, res):
    t = res["tally"]
    L = ["# kmatch pilot: path-cover (matching) fleet bound KM on XLTW-Test, against K*", "",
         "Exploratory pilot, not pre-registered (pilot.md). Convention 'round'. KM = max(n - M, 1). K* = max(K, E) "
         "from xltwen/. Part-a solutions from xltwrun/sols at commit 56b4e6e.", "",
         "Tally: `%s`" % json.dumps(t), "",
         "| instance | n | KC | K* | KM | KM - K* | matched | cycles | vertices on cycles | arc density | "
         "part-a routes | missing arcs | best | s | peak GB |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["instances"]:
        if r.get("error"):
            L.append("| %s | error: %s |||||||||||||" % (r["instance"], r["error"].strip().splitlines()[-1]))
            continue
        sol = r.get("sol") or {}
        L.append("| %s | %d | %d | %s | %d | %s | %d | %d | %d | %s | %s | %s | %s | %s | %s |" % (
            r["instance"], r["customers"], r["kc"], r["kstar"], r["km"], r.get("km_minus_kstar"), r["matched"],
            r["cycles"], r["cycle_vertices"], r["arc_density"], sol.get("routes", sol.get("error", "")),
            sol.get("missing_arcs", ""), r.get("best") or "", r["seconds"], r["peak_gb"]))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--only", default="", help="comma-separated instance names")
    ap.add_argument("--sols-url", default=SOLS_URL)
    a = ap.parse_args()
    out = os.path.join(a.out_dir, "kmatch")
    os.makedirs(out, exist_ok=True)
    ref = load_ref(os.path.join(HERE, REF_FILE))
    files = find_files(a.data_dir)
    names = [n for n in a.only.split(",") if n] or list(files)
    res = {"python": sys.version.split()[0], "numpy": np.__version__, "ref_instances": len(ref),
           "files_found": len(files), "instances": []}
    try:
        import scipy
        res["scipy"] = scipy.__version__
    except ImportError:
        res["scipy"] = None
    res_path = os.path.join(out, "results.json")
    for name in order(names, ref):
        if name not in files:
            rec = {"instance": name, "error": "instance file not found"}
        else:
            try:
                rec = one(files[name], name, ref, a.sols_url)
            except Exception:  # noqa: BLE001 - recorded
                rec = {"instance": name, "error": traceback.format_exc()}
        res["instances"].append(rec)
        res["tally"] = tally(res["instances"])
        with open(res_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(res, f, indent=1)
        log(json.dumps({k: rec.get(k) for k in ("instance", "customers", "kc", "kstar", "km", "matched", "cycles",
                                               "cycle_vertices", "arc_density", "seconds", "peak_gb", "error")}))
    res["tally"] = tally(res["instances"])
    with open(res_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1)
    write_md(os.path.join(out, "results.md"), res)
    log("TALLY " + json.dumps(res["tally"]))


if __name__ == "__main__":
    main()
