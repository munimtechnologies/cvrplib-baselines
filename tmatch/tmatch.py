"""tmatch: a fleet search for the VRPTW built around an exact sub-problem (fixed service times -> maximum matching).

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

Idea. If every customer's service start time tau_i is fixed, a route is a path in the graph with an arc i -> j
whenever tau_i + s_i + t_ij <= tau_j. With no capacity limit, the fewest routes for those times is n - M, where M is a
maximum bipartite matching between out-copies and in-copies of the customers (fleet sizing for fixed schedules,
Dantzig and Fulkerson 1954). The graph is acyclic (ties broken by a fixed order), so every matching is a set of paths,
and every path is a route a vehicle can drive: leave the depot at its opening time, wait where early.

tmatch alternates two steps:
  1. exact maximum matching on the current times (scipy's Hopcroft-Karp), with the customers in a random order so
     that equal-size matchings differ from one round to the next;
  2. for every resulting route, its earliest and latest feasible schedules E and L, and new times
     tau = E + lam * (L - E) with lam = 0 (prob. 0.4), 1 (prob. 0.4) or uniform (prob. 0.2), chosen per route.
Each old route is still a path under its new times (E and L both satisfy every arc, and so does any mix of them), so
on capacity-free instances the number of routes can never go up. Where capacity binds, a route is cut into
consecutive pieces within capacity (a piece of an on-time route is on time), and a round is kept only if it does not
use more routes.

The matching is classical. Searching over service times by re-timing whole routes between matchings is our heuristic;
a search on 2026-11-17 found no description of this loop for the VRPTW, which does not mean none exists.

Study (PREREG.md): the 27 capacity-free XLTW-Test instances that have a PyVRP baseline at T(n)/30
(cvrplib-baselines xltwrun/, part a), at the same time budget, plus two narrow-window instances with capacity
(n1748, n3888), where the kmatch/ matching bound is within 1-2 vehicles of K*. Every counted solution is re-checked
by exact_check(), which shares no code with the search (fractions from the file's own tokens).

  python tmatch.py --data-dir /data --out-dir /out
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
TOL = 1e-7
BLOCK = 512
SEED = 20261117
P_EARLY, P_LATE = 0.4, 0.4
BUDGET_PER_1000 = 60.0  # T(n)/30: the challenge's limit is 1,800 s per 1,000 customers
XLTWEN_FILE = "xltwen-results.json"
KMATCH_FILE = "kmatch-results.json"
# best valid PyVRP fleets at the FULL limit T(n) on the four instances of xltwfull/ and nbrm/
BEST = {"XLTW-Test-n1234": 33, "XLTW-Test-n1421": 65, "XLTW-Test-n1608": 108, "XLTW-Test-n1841": 25}
# narrow windows, capacity applies; kmatch/ found KM close to K* here (142 vs 143, 458 vs 460)
EXTRA = ["XLTW-Test-n1748", "XLTW-Test-n3888"]
T0 = time.time()


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def travel(dx, dy):
    """Nearest-integer Euclidean travel time (TSPLIB EUC_2D, the challenge's rule)."""
    return np.floor(np.hypot(dx, dy) + 0.5)


class Inst:
    """Arrays over customers 0..n-1 (file customer i + 1). e / l: earliest and latest service start that are
    reachable from the depot and still get back before it closes. C[i, j] = s_i + t_ij."""

    def __init__(self, inst):
        rows = inst["rows"]
        self.name = inst["name"]
        self.n = n = len(rows) - 1
        xy = np.array([(r[0], r[1]) for r in rows], dtype=np.float64)
        a = np.array([r[3] for r in rows], dtype=np.float64)
        b = np.array([r[4] for r in rows], dtype=np.float64)
        s = np.array([r[5] for r in rows], dtype=np.float64)
        self.q = np.array([r[2] for r in rows], dtype=np.float64)[1:]
        self.cap = float(inst["capacity"])
        self.capfree = bool(self.q.sum() <= self.cap + 1e-9)
        t0 = travel(xy[:, 0] - xy[0, 0], xy[:, 1] - xy[0, 1])
        self.a0, self.b0 = float(a[0]), float(b[0])
        self.e = np.maximum(a, a[0] + s[0] + t0)[1:]
        self.l = np.minimum(b, b[0] - s - t0)[1:]
        self.s = s[1:]
        self.xy = xy[1:]
        integral = bool(np.all(self.s == np.floor(self.s)))
        self.C = np.empty((n, n), dtype=np.int32 if integral else np.float64)
        for lo in range(0, n, BLOCK):
            hi = min(lo + BLOCK, n)
            d = travel(self.xy[lo:hi, 0, None] - self.xy[None, :, 0], self.xy[lo:hi, 1, None] - self.xy[None, :, 1])
            self.C[lo:hi] = d + self.s[lo:hi, None]
            del d
        self.unservable = int((self.e > self.l).sum())
        self.overweight = int((self.q > self.cap + 1e-9).sum())


def chains_from(succ):
    """Paths of a successor array (-1 = none). Raises if the arcs close a cycle."""
    n = len(succ)
    pred = -np.ones(n, dtype=np.int64)
    idx = np.flatnonzero(succ >= 0)
    pred[succ[idx]] = idx
    sl = [int(x) for x in succ]
    out, seen = [], 0
    for v in np.flatnonzero(pred < 0).tolist():
        ch = []
        while v >= 0:
            ch.append(v)
            if len(ch) > n:
                raise RuntimeError("successor array has a cycle")
            v = sl[v]
        out.append(ch)
        seen += len(ch)
    if seen != n:
        raise RuntimeError("matching left a cycle: %d of %d customers on paths" % (seen, n))
    return out


def match_chains(I, tau, order):
    """Maximum matching in the fixed-time graph; customers taken in `order` (a permutation). Returns (paths, arcs).
    Arc i -> j iff tau_i + C_ij <= tau_j (+TOL); when C_ij = 0, also (tau_i, position) before (tau_j, position)."""
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import maximum_bipartite_matching
    n = I.n
    order = np.asarray(order, dtype=np.int64)
    tp = tau[order]
    pos = np.arange(n)
    parts, counts = [], np.zeros(n, dtype=np.int64)
    for lo in range(0, n, BLOCK):
        hi = min(lo + BLOCK, n)
        Cb = I.C[order[lo:hi]][:, order]
        ti = tp[lo:hi, None]
        ok = ti + Cb <= tp[None, :] + TOL
        z = Cb <= 0
        if z.any():
            later = (tp[None, :] > ti + TOL) | ((np.abs(tp[None, :] - ti) <= TOL) & (pos[None, :] > pos[lo:hi, None]))
            ok &= ~z | later
            del later
        r = np.arange(hi - lo)
        ok[r, r + lo] = False
        counts[lo:hi] = ok.sum(axis=1)
        parts.append(np.nonzero(ok)[1].astype(np.int32))
        del Cb, ok, z
    idx = np.concatenate(parts) if parts else np.zeros(0, dtype=np.int32)
    del parts
    indptr = np.zeros(n + 1, dtype=np.int64)
    np.cumsum(counts, out=indptr[1:])
    if indptr[-1] < 2 ** 31 - 1:
        indptr = indptr.astype(np.int32)
    G = csr_matrix((np.ones(len(idx), dtype=np.int8), idx, indptr), shape=(n, n))
    nnz = int(G.nnz)
    mp = np.asarray(maximum_bipartite_matching(G, perm_type="column"), dtype=np.int64)
    del G, idx
    succ = -np.ones(n, dtype=np.int64)
    rows = np.flatnonzero(mp >= 0)
    succ[order[rows]] = order[mp[rows]]
    return chains_from(succ), nnz


def schedule(I, ch):
    """Earliest (E) and latest (L) service starts along a route, as lists; on time iff E[k] <= L[k] for all k."""
    k = len(ch)
    if k == 1:
        return [float(I.e[ch[0]])], [float(I.l[ch[0]])]
    c = I.C[ch[:-1], ch[1:]].tolist()
    E = [0.0] * k
    E[0] = float(I.e[ch[0]])
    for m in range(1, k):
        x = E[m - 1] + c[m - 1]
        em = float(I.e[ch[m]])
        E[m] = x if x > em else em
    L = [0.0] * k
    L[-1] = float(I.l[ch[-1]])
    for m in range(k - 2, -1, -1):
        x = L[m + 1] - c[m]
        lm = float(I.l[ch[m]])
        L[m] = x if x < lm else lm
    return E, L


def pieces(I, ch):
    """Cut a path into consecutive pieces that are on time (earliest schedule) and within capacity. On an on-time,
    within-capacity path this returns the path itself."""
    out, cur, load, t = [], [], 0.0, 0.0
    for v in ch:
        qv = float(I.q[v])
        if cur:
            arr = t + float(I.C[cur[-1], v])
            start = arr if arr > float(I.e[v]) else float(I.e[v])
            if start <= float(I.l[v]) and load + qv <= I.cap + 1e-9:
                cur.append(v)
                load += qv
                t = start
                continue
            out.append(cur)
        cur, load, t = [v], qv, float(I.e[v])
    if cur:
        out.append(cur)
    return out


def routes_of(I, chains):
    return [p for c in chains for p in pieces(I, c)]


def retime(I, routes, rng):
    """New service times: per route, tau = E + lam (L - E), lam = 0, 1 or uniform."""
    tau = np.empty(I.n, dtype=np.float64)
    for ch in routes:
        E, L = schedule(I, ch)
        u = rng.random()
        if u < P_EARLY:
            tau[ch] = E
        elif u < P_EARLY + P_LATE:
            tau[ch] = L
        else:
            lam = rng.random()
            Ea = np.array(E)
            tau[ch] = Ea + lam * (np.array(L) - Ea)
    return tau


def solve(I, deadline, seed=SEED, lb=None, max_iter=None, clock=time.monotonic, t_start=None):
    """Returns (best routes as lists of customer indices 0..n-1, trajectory, stats). Stops at the deadline, at the
    lower bound lb, or after max_iter re-timing rounds (tests)."""
    rng = np.random.default_rng(seed)
    t_start = clock() if t_start is None else t_start
    stats = {"iterations": 0, "accepted": 0, "improvements": 0, "rejected": 0, "arcs_first": None,
             "arcs_last": None, "start_routes": {}, "stop": None}
    traj = []
    cur = None
    starts = (("early", I.e.copy()), ("late", I.l.copy()), ("middle", 0.5 * (I.e + I.l)))
    for k, (tag, tau) in enumerate(starts):
        if k > 0 and clock() >= deadline:
            break
        order = np.arange(I.n) if k == 0 else rng.permutation(I.n)
        ch, nnz = match_chains(I, tau, order)
        routes = routes_of(I, ch)
        stats["start_routes"][tag] = len(routes)
        if stats["arcs_first"] is None:
            stats["arcs_first"] = nnz
        stats["arcs_last"] = nnz
        if cur is None or len(routes) < len(cur):
            cur = routes
            traj.append([round(clock() - t_start, 2), len(cur), tag])
    while True:
        if clock() >= deadline:
            stats["stop"] = "time"
            break
        if lb is not None and len(cur) <= lb:
            stats["stop"] = "bound"
            break
        if max_iter is not None and stats["iterations"] >= max_iter:
            stats["stop"] = "max_iter"
            break
        tau = retime(I, cur, rng)
        ch, nnz = match_chains(I, tau, rng.permutation(I.n))
        routes = routes_of(I, ch)
        stats["iterations"] += 1
        stats["arcs_last"] = nnz
        if len(routes) <= len(cur):
            stats["accepted"] += 1
            if len(routes) < len(cur):
                stats["improvements"] += 1
                traj.append([round(clock() - t_start, 2), len(routes), "it%d" % stats["iterations"]])
            cur = routes
        else:
            stats["rejected"] += 1
    return cur, traj, stats


# ---------------------------------------------------------------- independent exact check (no numpy, no search code)

def rint_sqrt(d2):
    """floor(sqrt(d2) + 0.5) exactly, for an integer d2 >= 0."""
    k = math.isqrt(d2)
    return k + 1 if d2 > k * k + k else k


def exact_check(inst, routes1):
    """routes1: lists of customers numbered 1..n. Recomputes everything from the file's tokens with fractions:
    every customer exactly once, no service after its due time, back at the depot before it closes, capacity.
    Distance is the challenge's sum of nearest-integer arcs."""
    F = [[Fraction(str(t)) for t in r] for r in inst["raw"]]
    n = len(F) - 1
    ints = all(v.denominator == 1 for r in F for v in r[:2])

    def tt(i, j):
        dx, dy = F[i][0] - F[j][0], F[i][1] - F[j][1]
        if ints:
            return rint_sqrt(int(dx * dx + dy * dy))
        return math.floor(math.hypot(float(dx), float(dy)) + 0.5)

    cap = Fraction(str(inst["capacity"]))
    a0, b0, s0 = F[0][3], F[0][4], F[0][5]
    seen = [0] * (n + 1)
    problems, dist = [], 0
    for k, r in enumerate(routes1):
        if not r:
            problems.append("route %d is empty" % (k + 1))
            continue
        t, prev, sp, load, bad = a0, 0, s0, Fraction(0), False
        for c in r:
            if not (isinstance(c, int) and 1 <= c <= n):
                problems.append("route %d: no customer %r" % (k + 1, c))
                bad = True
                break
            seen[c] += 1
            d = tt(prev, c)
            dist += d
            start = max(t + sp + d, F[c][3])
            if start > F[c][4]:
                problems.append("route %d: customer %d starts at %s after its due time %s" % (k + 1, c, start, F[c][4]))
            t, prev, sp = start, c, F[c][5]
            load += F[c][2]
        if bad:
            continue
        d = tt(prev, 0)
        dist += d
        if t + sp + d > b0:
            problems.append("route %d: back at the depot at %s after %s" % (k + 1, t + sp + d, b0))
        if load > cap:
            problems.append("route %d: load %s above capacity %s" % (k + 1, load, cap))
    missing = sum(1 for c in range(1, n + 1) if seen[c] == 0)
    dups = sum(1 for c in range(1, n + 1) if seen[c] > 1)
    return {"ok": not problems and missing == 0 and dups == 0, "routes": len(routes1), "distance": int(dist),
            "problems": problems[:5], "n_problems": len(problems), "missing": missing, "duplicates": dups,
            "integer_coords": ints}


def sol_text(routes1, cost):
    return "".join("Route #%d: %s\n" % (k + 1, " ".join(str(c) for c in r)) for k, r in enumerate(routes1)) + \
        "Cost: %d\n" % cost


# ---------------------------------------------------------------- study harness

def load_xltwen(path):
    """{instance: {kc, k, e, kstar, vehicles_a, customers}} from xltwen/results.json; {} if missing."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    out = {}
    for r in data.get("instances", []):
        k, e = r.get("k"), r.get("e")
        vals = [x for x in (k, e) if x is not None]
        out[r["instance"]] = {"kc": r.get("kc"), "k": k, "e": e, "kstar": max(vals) if vals else None,
                              "vehicles_a": r.get("vehicles_a"), "customers": r.get("customers")}
    return out


def load_kmatch(path):
    """{instance: KM} from kmatch/results.json; {} if missing."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {r["instance"]: r["km"] for r in data.get("instances", []) if r.get("km") is not None}


def find_files(data_dir):
    by_name = {}
    for p in sorted(glob.glob(os.path.join(data_dir, "xltw-test", "x-*", "**", "*.vrp"), recursive=True)):
        by_name.setdefault(os.path.splitext(os.path.basename(p))[0], p)
    return by_name


def size_of(name):
    try:
        return int(name.rsplit("-n", 1)[1])
    except (IndexError, ValueError):
        return 10 ** 9


def plan(ref):
    """The study's instances in run order: the four of nbrm/ first, then the other capacity-free instances that have
    a part-a baseline (smallest first), then EXTRA."""
    main = [n for n, r in ref.items() if r.get("kc") == 1 and r.get("vehicles_a") is not None]
    first = [n for n in BEST if n in main]
    rest = sorted((n for n in main if n not in BEST), key=size_of)
    return first + rest + [n for n in EXTRA if n not in main]


def peak_gb():
    try:
        import resource
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0 / 1024.0, 3)
    except Exception:  # noqa: BLE001 - not on Linux
        return None


def one(path, name, ref, km, sols_dir, seed=SEED, per_1000=BUDGET_PER_1000):
    import xltwlb as X
    t_start = time.monotonic()
    with open(path, encoding="utf-8") as f:
        inst = X.parse_any(f.read())
    n = len(inst["rows"]) - 1
    budget = per_1000 * n / 1000.0
    deadline = t_start + budget
    I = Inst(inst)
    rf = ref.get(name) or {}
    bounds = [x for x in (rf.get("kstar"), km.get(name), 1) if x is not None]
    lb = max(bounds)
    rec = {"instance": name, "customers": n, "capfree": I.capfree, "kc": rf.get("kc"), "kstar": rf.get("kstar"),
           "km": km.get(name), "lb": lb, "vehicles_a": rf.get("vehicles_a"), "best_full": BEST.get(name),
           "budget_s": round(budget, 1), "unservable": I.unservable, "overweight": I.overweight}
    width = I.l - I.e
    horizon = max(I.b0 - I.a0, 1.0)
    rec["window_median"] = float(np.median(width))
    rec["window_median_rel"] = round(float(np.median(width)) / horizon, 5)
    rec["service_median"] = float(np.median(I.s))
    rec["seconds_setup"] = round(time.monotonic() - t_start, 2)
    if I.unservable or I.overweight:
        rec["error"] = "instance has customers no route can serve"
        return rec
    best, traj, st = solve(I, deadline, seed=seed, lb=lb, t_start=t_start)
    rec["seconds_search"] = round(time.monotonic() - t_start, 2)
    routes1 = [[v + 1 for v in r] for r in best]
    del I
    chk = exact_check(inst, routes1)
    rec["routes"] = len(routes1)
    rec["exact"] = chk
    rec["trajectory"] = traj
    rec.update({k: st[k] for k in ("iterations", "accepted", "improvements", "rejected", "arcs_first", "arcs_last",
                                   "start_routes", "stop")})
    if rec["vehicles_a"] is not None:
        rec["minus_pyvrp_a"] = rec["routes"] - rec["vehicles_a"]
    if rec["best_full"] is not None:
        rec["minus_best_full"] = rec["routes"] - rec["best_full"]
    rec["at_lb"] = rec["routes"] == lb
    os.makedirs(sols_dir, exist_ok=True)
    with open(os.path.join(sols_dir, name + ".sol"), "w", encoding="utf-8", newline="\n") as f:
        f.write(sol_text(routes1, chk["distance"]))
    rec["seconds"] = round(time.monotonic() - t_start, 2)
    rec["peak_gb"] = peak_gb()
    return rec


def spearman(x, y):
    try:
        from scipy.stats import spearmanr
        if len(x) < 3:
            return None
        r = spearmanr(x, y)
        return round(float(r[0]), 4)
    except Exception:  # noqa: BLE001 - reported as missing
        return None


def tally(recs):
    ok = [r for r in recs if not r.get("error")]
    main = [r for r in ok if r.get("capfree") and r.get("vehicles_a") is not None]
    t = {
        "instances_done": len(ok),
        "errors": [r["instance"] for r in recs if r.get("error")],
        "invalid": [r["instance"] for r in ok if not r["exact"]["ok"]],
        "below_lb": [r["instance"] for r in ok if r["routes"] < r["lb"]],
        "over_budget_30s": [r["instance"] for r in ok if r["seconds_search"] > r["budget_s"] + 30],
        "main_instances": len(main),
        "wins": [r["instance"] for r in main if r["routes"] < r["vehicles_a"]],
        "ties": [r["instance"] for r in main if r["routes"] == r["vehicles_a"]],
        "losses": [r["instance"] for r in main if r["routes"] > r["vehicles_a"]],
        "sum_tmatch": sum(r["routes"] for r in main),
        "sum_pyvrp_a": sum(r["vehicles_a"] for r in main),
        "sum_lb": sum(r["lb"] for r in main),
        "named": {r["instance"]: [r["routes"], r["best_full"]] for r in ok if r.get("best_full") is not None},
        "at_lb": [r["instance"] for r in ok if r.get("at_lb")],
        "extra": {r["instance"]: [r["routes"], r["lb"], r.get("vehicles_a")] for r in ok if r["instance"] in EXTRA},
        "peak_gb": max([r["peak_gb"] for r in ok if r.get("peak_gb") is not None] or [None]) if ok else None,
    }
    adv = [(r["vehicles_a"] - r["routes"]) / float(r["vehicles_a"]) for r in main]
    t["spearman_window_vs_advantage"] = spearman([r["window_median_rel"] for r in main], adv)
    t["ratio_tmatch_to_pyvrp_a"] = round(t["sum_tmatch"] / float(t["sum_pyvrp_a"]), 4) if t["sum_pyvrp_a"] else None
    return t


def write_md(path, res):
    t = res["tally"]
    L = ["# tmatch on XLTW-Test: fixed-time matching fleet search at T(n)/30, against PyVRP (xltwrun/ part a)", "",
         "Pre-registered in PREREG.md. Convention 'round'. lb = max(K*, KM, 1). Seed %d. Solver %s." % (
             SEED, VERSION), "", "Tally: `%s`" % json.dumps(t), "",
         "| instance | n | capacity-free | window median / horizon | lb | PyVRP T(n)/30 | PyVRP best full T(n) | "
         "tmatch | tmatch - PyVRP | starts e/l/m | rounds | improvements | exact | distance | s | peak GB |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["instances"]:
        if r.get("error"):
            L.append("| %s | error: %s |||||||||||||||" % (r["instance"], r["error"].strip().splitlines()[-1]))
            continue
        sr = r.get("start_routes") or {}
        L.append("| %s | %d | %s | %s | %s | %s | %s | %d | %s | %s/%s/%s | %d | %d | %s | %d | %s | %s |" % (
            r["instance"], r["customers"], r["capfree"], r["window_median_rel"], r["lb"], r["vehicles_a"],
            r["best_full"] or "", r["routes"], r.get("minus_pyvrp_a", ""), sr.get("early"), sr.get("late"),
            sr.get("middle"), r["iterations"], r["improvements"], "ok" if r["exact"]["ok"] else "FAILED",
            r["exact"]["distance"], r["seconds"], r["peak_gb"]))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--only", default="", help="comma-separated instance names (default: the pre-registered plan)")
    a = ap.parse_args()
    out = os.path.join(a.out_dir, "tmatch")
    os.makedirs(out, exist_ok=True)
    ref = load_xltwen(os.path.join(HERE, XLTWEN_FILE))
    km = load_kmatch(os.path.join(HERE, KMATCH_FILE))
    files = find_files(a.data_dir)
    names = [n for n in a.only.split(",") if n] or plan(ref)
    res = {"solver": "tmatch " + VERSION, "seed": SEED, "python": sys.version.split()[0], "numpy": np.__version__,
           "ref_instances": len(ref), "kmatch_instances": len(km), "files_found": len(files), "plan": names,
           "instances": []}
    try:
        import scipy
        res["scipy"] = scipy.__version__
    except ImportError:
        res["scipy"] = None
    log("plan: %d instances, %d files, %d xltwen rows, %d kmatch rows" % (len(names), len(files), len(ref), len(km)))
    res_path = os.path.join(out, "results.json")
    for name in names:
        if name not in files:
            rec = {"instance": name, "error": "instance file not found"}
        else:
            try:
                rec = one(files[name], name, ref, km, os.path.join(out, "sols"))
            except Exception:  # noqa: BLE001 - recorded
                rec = {"instance": name, "error": traceback.format_exc()}
        res["instances"].append(rec)
        res["tally"] = tally(res["instances"])
        with open(res_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(res, f, indent=1)
        log(json.dumps({k: rec.get(k) for k in ("instance", "customers", "lb", "vehicles_a", "routes", "iterations",
                                               "improvements", "stop", "seconds", "peak_gb", "error")}))
    res["tally"] = tally(res["instances"])
    with open(res_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1)
    write_md(os.path.join(out, "results.md"), res)
    log("TALLY " + json.dumps(res["tally"]))


if __name__ == "__main__":
    main()
