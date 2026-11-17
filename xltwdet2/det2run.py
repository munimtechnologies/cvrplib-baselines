"""xltwdet2: is xltw-solver 0.2.0 (per-phase work budgets, the new default) deterministic for its seed at the
challenge's full limit T(n), even with two copies running side by side, and how much of the limit does it use?

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

Two XLTW-Test instances (n1234, n2028), seed 20261104 (the seed of `xltwfull/`), limit T(n) = 1.8 s per customer.
On each instance two runs, X1 and X2, start at the same moment and run side by side on the job's two CPUs. Every
run goes through xltwfull's harness as published (cvrplib-baselines commit 876bd94, `run_one`, unchanged): one process
per run, SIGTERM at the limit, SIGKILL 5 s later, the last complete solution printed before the limit counts and is
re-checked exactly. If either run of a pair is frozen (a harness poll gap above 1 s), the pair is re-run once; the
second pair counts. Before the study, two smoke runs on n1234: S1 work mode 60 s, S2 clock mode 30 s; if S1 is not a
valid run, the study runs are skipped (then G0 fails). Predictions G0-G7 are in PREREG.md, published before any run;
this script scores them at the end of the same job.

  python det2run.py --data-dir /data --out-dir /out
"""
import argparse
import hashlib
import json
import os
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import fullrun as FR  # noqa: E402  xltwfull/fullrun.py at commit 876bd94

SEED = 20261104
PAIRS = [("A", "XLTW-Test-n1234", 1233), ("B", "XLTW-Test-n2028", 2027)]
SMOKE = [("S1", "work", 60.0), ("S2", "clock", 30.0)]
REF_VEHICLES = {"XLTW-Test-n1234": 34, "XLTW-Test-n2028": 103}  # xltwfull F1 at T(n); xltwen vehicles_a (T(n)/30)
G3_RANGE = (0.35, 0.85)
HEADROOM = 1.2


def limit_for(customers):
    return round(1.8 * customers, 1)


def reexec_under_build_python():
    import lock
    exe = lock.build_python(HERE)
    if not exe or os.environ.get("XLTW_DET2_REEXEC"):
        return
    if os.path.realpath(exe) == os.path.realpath(sys.executable):
        return
    print("det2run.py: re-running under the build's interpreter %s (was %s)" % (exe, sys.executable), flush=True)
    os.environ["XLTW_DET2_REEXEC"] = "1"
    os.execv(exe, [exe, os.path.abspath(__file__)] + sys.argv[1:])


def solution_sha(sol_dir, instance):
    path = os.path.join(sol_dir, "%s.sol" % instance)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def rates(rec):
    """Measured iterations per second of each phase, and the model's, from the solver's stats line."""
    st = rec.get("solver_stats") or {}
    out = {}
    for ph, it_key, s_key, m_key in (("fleet", "fleet_iterations", "fleet_seconds", "model_fleet_rate"),
                                     ("distance", "distance_iterations", "distance_seconds", "model_distance_rate")):
        it, s, m = st.get(it_key), st.get(s_key), st.get(m_key)
        out[ph] = round(it / s, 1) if (it and s) else None
        out[ph + "_model"] = m
        out[ph + "_headroom"] = round(it / s / m, 3) if (it and s and m) else None
    return out


def one(rid, path, limit, seed, logs, out, mode="work"):
    sol_dir = os.path.join(out, "sols", rid)
    os.environ["XLTW_MODE"] = mode  # inherited by the solver process (same value for both runs of a pair)
    try:
        rec = FR.run_one(rid, path, limit, seed, logs, sol_dir)
        rec["mode"] = mode
        rec["solution_sha256"] = solution_sha(sol_dir, rec["instance"])
        rec["rates"] = rates(rec)
    except Exception as e:  # noqa: BLE001 - recorded
        rec = {"id": rid, "error": repr(e), "mode": mode}
    return rec


def pair(key, path, limit, logs, out, tag=""):
    """X1 and X2 side by side; returns both records."""
    recs = {}

    def go(x):
        recs[x] = one("%s-%s%s" % (key, x, tag), path, limit, SEED, logs, out)
    ths = [threading.Thread(target=go, args=(x,)) for x in ("X1", "X2")]
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    return [recs["X1"], recs["X2"]]


def clock_stopped(r):
    st = r.get("solver_stats") or {}
    return bool(st.get("clock_stop")) or bool(st.get("term_stop"))


def verdict(ok):
    return "held" if ok else "did not hold"


def score(build, net, runs):
    """G0-G7 of PREREG.md on the counted runs A-X1, A-X2, B-X1, B-X2."""
    by = {r["id"]: r for r in runs}
    ids = ["%s-%s" % (k, x) for k, _, _ in PAIRS for x in ("X1", "X2")]
    gate = (all(i in by for i in ids) and not net and build.get("tag") is not None and build.get("pins_ok") is True
            and all(FR.valid(by[i]) for i in ids)
            and all((by[i].get("solver_stats") or {}).get("solver") == "xltw-solver 0.2.0" for i in ids))
    p = {"G0": verdict(gate)}
    if not gate:
        for k in ("G1", "G2", "G3", "G4", "G5", "G6", "G7"):
            p[k] = "untestable (G0 failed)"
        return p
    keys = [k for k, _, _ in PAIRS]
    p["G1"] = verdict(all(by[k + "-X1"]["solution_sha256"] is not None
                          and by[k + "-X1"]["solution_sha256"] == by[k + "-X2"]["solution_sha256"] for k in keys))
    p["G2"] = verdict(not any(clock_stopped(by[i]) for i in ids)
                      and all((by[i].get("solver_stats") or {}).get("deterministic") is True for i in ids))
    lo, hi = G3_RANGE
    p["G3"] = verdict(all(lo * by[i]["limit"] <= (by[i].get("solver_stats") or {}).get("elapsed", -1) <= hi * by[i]["limit"]
                          for i in ids))
    a = [by["A-X1"], by["A-X2"]]
    b = [by["B-X1"], by["B-X2"]]
    p["G4"] = verdict(all(r["vehicles"] <= REF_VEHICLES[PAIRS[0][1]] for r in a))
    p["G5"] = verdict(all(r["vehicles"] < REF_VEHICLES[PAIRS[1][1]] for r in b))
    p["G6"] = verdict(all(by[i]["peak_gb"] is not None and by[i]["peak_gb"] <= 0.6 and not by[i].get("watchdog")
                          for i in ids))
    p["G7"] = verdict(all((by[i]["rates"].get("fleet_headroom") or 0) >= HEADROOM
                          and (by[i]["rates"].get("distance_headroom") or 0) >= HEADROOM for i in ids))
    return p


def write_md(path, res):
    L = ["# xltwdet2: xltw-solver 0.2.0 (work budgets) at the full limit T(n), two runs side by side", "",
         "Seed %d. Network reachable during the runs: %s. Build: %s, Python %s; pins ok: %s." % (
             SEED, res["network_reachable"], res["build"].get("tag"), res["build"].get("python"),
             res["build"].get("pins_ok")), "",
         "Predictions (PREREG.md): `%s`" % json.dumps(res.get("predictions")), "",
         "| run | instance | mode | limit s | vehicles | distance | solution sha256 (first 12) | elapsed s | "
         "fleet it (budget) | fleet it/s (model) | distance it (budget+carry) | distance it/s (model) | clock stop | "
         "deterministic | peak GB | valid |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["smoke"] + res["runs"]:
        if r.get("error"):
            L.append("| %s | | %s | | error: %s | | | | | | | | | | | |" % (r["id"], r.get("mode"), r["error"]))
            continue
        st = r.get("solver_stats") or {}
        ra = r.get("rates") or {}
        L.append("| %s | %s | %s | %.1f | %s | %s | %s | %s | %s (%s) | %s (%s) | %s (%s+%s) | %s (%s) | %s | %s | %s | %s |"
                 % (r["id"], r["instance"], r.get("mode"), r["limit"], r.get("vehicles"), r.get("distance"),
                    (r.get("solution_sha256") or "")[:12], st.get("elapsed"), st.get("fleet_iterations"),
                    st.get("fleet_budget"), ra.get("fleet"), ra.get("fleet_model"), st.get("distance_iterations"),
                    st.get("distance_budget"), st.get("carry"), ra.get("distance"), ra.get("distance_model"),
                    st.get("clock_stop"), st.get("deterministic"), r.get("peak_gb"), FR.valid(r)))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


def main():
    import conformance as C
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--smoke-only", action="store_true")
    a = ap.parse_args()
    reexec_under_build_python()
    out = os.path.join(a.out_dir, "xltwdet2")
    logs = os.path.join(out, "logs")
    os.makedirs(logs, exist_ok=True)
    net = C.network_reachable()
    build = C.build_info()
    print("network reachable: %s; build: %s" % (net, json.dumps(build)), flush=True)
    res = {"seed": SEED, "network_reachable": net, "build": build, "smoke": [], "runs": [], "pair_reruns": [],
           "python": sys.version.split()[0], "executable": sys.executable}
    res_path = os.path.join(out, "results.json")
    mpath = os.path.join(HERE, "det2-manifest.json")
    if os.path.exists(mpath):
        with open(mpath, encoding="utf-8") as f:
            res["manifest"] = json.load(f)

    def save():
        with open(res_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(res, f, indent=1)

    ok_to_run = not net and build.get("pins_ok")
    p1234 = C.find(a.data_dir, PAIRS[0][1])
    for rid, mode, limit in SMOKE:
        if p1234 is None or not ok_to_run:
            rec = {"id": rid, "mode": mode, "error": "not run: instance missing, network reachable or pins not ok"}
        else:
            rec = one(rid, p1234, limit, SEED, logs, out, mode=mode)
        res["smoke"].append(rec)
        save()
        print(json.dumps({"id": rid, "vehicles": rec.get("vehicles"), "valid": FR.valid(rec) if not rec.get("error")
                          else False, "stats": rec.get("solver_stats"), "error": rec.get("error")}), flush=True)
    s1 = res["smoke"][0]
    study_ok = ok_to_run and not s1.get("error") and FR.valid(s1)
    if not a.smoke_only:
        for key, name, customers in PAIRS:
            path = C.find(a.data_dir, name)
            limit = limit_for(customers)
            if path is None or not study_ok:
                why = "instance file not found" if path is None else "not run: smoke run S1 not valid (or no clean build)"
                res["runs"].extend({"id": "%s-%s" % (key, x), "instance": name, "error": why} for x in ("X1", "X2"))
                save()
                continue
            recs = pair(key, path, limit, logs, out)
            if any(r.get("harness_frozen") for r in recs):  # pre-registered: re-run the pair once, unchanged
                res["pair_reruns"].append(recs)
                recs = pair(key, path, limit, logs, out, tag="")
            res["runs"].extend(recs)
            save()
            for r in recs:
                print(json.dumps({"id": r["id"], "vehicles": r.get("vehicles"), "distance": r.get("distance"),
                                  "sha": (r.get("solution_sha256") or "")[:12], "rates": r.get("rates"),
                                  "elapsed": (r.get("solver_stats") or {}).get("elapsed"),
                                  "clock_stop": (r.get("solver_stats") or {}).get("clock_stop"),
                                  "frozen": r.get("harness_frozen"), "error": r.get("error")}), flush=True)
    res["predictions"] = score(build, net, res["runs"]) if not a.smoke_only else "not scored (--smoke-only)"
    save()
    write_md(os.path.join(out, "results.md"), res)
    print("PREDICTIONS " + json.dumps(res["predictions"]), flush=True)


if __name__ == "__main__":
    main()
