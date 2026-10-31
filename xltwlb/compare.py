"""Regression check: xltwlb.py on CVRPLib's 356 VRPTW instances against the published vrptwlb/ results.

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.

Runs xltwlb.bound_one on ids 380-735 (Solomon and Gehring-Homberger) in the double, DIMACS and round conventions,
then downloads vrptwlb/bounds.csv and vrptwlb/cliques.json from munimtechnologies/cvrplib-baselines and compares.
Predictions: expectations.md, scored by score_c() below.
"""
import argparse
import csv
import io
import json
import os
import time
import traceback
import urllib.request

import xltwlb as X

BASE = "https://galgos.inf.puc-rio.br/cvrplib/en/download"
RAW = "https://raw.githubusercontent.com/munimtechnologies/cvrplib-baselines/main/vrptwlb/"
UA = "CVRPLib VRPTW fleet bounds cross-check - MV2 of Munim, Inc. (mv2@munimtech.com)"
EXPECTED = 356


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8")


def load_instance(src, i):
    path = os.path.join(src, "%s.txt" % i)
    if not (os.path.exists(path) and os.path.getsize(path) > 0):
        text = get("%s/instance/%s" % (BASE, i))
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        time.sleep(2)
    with open(path, encoding="utf-8") as f:
        return X.parse_any(f.read())


def parse_published(bounds_csv, cliques_json):
    """{instance: {kc, kt_double, kt_dimacs, k_double, k_dimacs}}, {instance: {conv: clique}}."""
    rows = {}
    for r in csv.DictReader(io.StringIO(bounds_csv)):
        rows[r["instance"]] = {"kc": int(r["KC"]), "kt_double": int(r["KT_double"]),
                               "kt_dimacs": int(r["KT_dimacs"]) if r["KT_dimacs"] else None,
                               "k_double": int(r["K_double"]),
                               "k_dimacs": int(r["K_dimacs"]) if r["K_dimacs"] else None}
    return rows, json.loads(cliques_json)


def fetch_published(tries, wait):
    for k in range(tries):
        try:
            return parse_published(get(RAW + "bounds.csv"), get(RAW + "cliques.json"))
        except Exception as e:  # noqa: BLE001 - not published yet, or a network hiccup
            X.log("published vrptwlb/ not readable yet (%s), try %d of %d" % (e, k + 1, tries))
            if k + 1 < tries:
                time.sleep(wait)
    return None, None


def compare(recs, cliques, pub, pub_cliques):
    """Tally of agreements and differences between this run and the published vrptwlb/ results."""
    ok = [r for r in recs if r.get("bounds")]
    t = {"instances": len(recs),
         "run_errors": [r["instance"] for r in recs if r.get("error")],
         "missing_conv": [r["instance"] + "/" + c for r in ok for c in X.CONVS if not r["bounds"].get(c)],
         "clique_unverified": [r["instance"] + "/" + c for r in ok for c in X.CONVS
                               if r["bounds"].get(c) and not r["bounds"][c]["verified"]],
         "unservable": sorted({r["instance"] for r in ok for c in X.CONVS
                               if r["bounds"].get(c) and r["bounds"][c]["unservable"]}),
         "not_published": [r["instance"] for r in ok if r["instance"] not in pub],
         "kc_diff": [], "kt_diff": [], "clique_diff": [], "kb_above_kc": [],
         "round_vs_double": [], "round_vs_dimacs": []}
    for r in ok:
        name, b = r["instance"], r["bounds"]
        if b["kb"] != b["kc"]:
            t["kb_above_kc"].append([name, b["kc"], b["kb"]])
        if b.get("round") and b.get("double") and b["round"]["k"] != b["double"]["k"]:
            t["round_vs_double"].append([name, b["double"]["k"], b["round"]["k"]])
        if b.get("round") and b.get("dimacs") and b["round"]["k"] != b["dimacs"]["k"]:
            t["round_vs_dimacs"].append([name, b["dimacs"]["k"], b["round"]["k"]])
        p = pub.get(name)
        if not p:
            continue
        if b["kc"] != p["kc"]:
            t["kc_diff"].append([name, p["kc"], b["kc"]])
        for c in ("double", "dimacs"):
            mine = b[c]["kt"] if b.get(c) else None
            if mine != p["kt_" + c]:
                t["kt_diff"].append([name, c, p["kt_" + c], mine])
            if cliques.get(name, {}).get(c) != pub_cliques.get(name, {}).get(c):
                t["clique_diff"].append([name, c])
    secs = [sum(b[c]["seconds"]) for r in ok for b in [r["bounds"]] for c in X.CONVS if b.get(c)]
    t["bound_seconds_total"] = round(sum(secs), 1)
    t["peak_gb"] = max((r.get("peak_gb") or 0) for r in recs) if recs else None
    t["published_read"] = bool(pub)
    t["predictions"] = score_c(t)
    return t


def score_c(t):
    """Verdicts for C0-C4 (expectations.md) from the tally."""
    def verdict(ok):
        return "untestable" if ok is None else ("held" if ok else "did not hold")
    pub = t["published_read"]
    return {
        "C0": verdict(t["instances"] == EXPECTED and not t["run_errors"] and not t["missing_conv"]
                      and not t["clique_unverified"] and not t["unservable"]),
        "C1": verdict(None if not pub or t["not_published"] else
                      not t["kc_diff"] and not t["kt_diff"] and not t["clique_diff"]),
        "C2": verdict(not t["kb_above_kc"]),
        "C3": verdict(len(t["round_vs_double"]) <= 10),
        "C4": verdict(None if t["peak_gb"] is None else t["bound_seconds_total"] < 1200 and t["peak_gb"] < 0.5),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="380-735")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--tries", type=int, default=24)
    ap.add_argument("--wait", type=int, default=300)
    args = ap.parse_args()
    src = os.path.join(args.data_dir, "cvrplib-vrptw")
    out = os.path.join(args.out_dir, "xcheck")
    for d in (src, out):
        os.makedirs(d, exist_ok=True)

    a, b = (int(v) for v in args.ids.split("-"))
    recs, cliques = [], {}
    for i in range(a, b + 1):
        rec = {"id": i}
        try:
            inst = load_instance(src, i)
            rec["instance"] = inst["name"]
            rec["bounds"] = X.bound_one(inst)
            cliques[inst["name"]] = {c: rec["bounds"][c].pop("clique") for c in X.CONVS if rec["bounds"][c]}
        except Exception:
            rec.setdefault("instance", "id%d" % i)
            rec["error"] = traceback.format_exc()
        rec["peak_gb"] = X.peak_gb()
        recs.append(rec)
        bd = rec.get("bounds") or {}
        X.log("%s: KC %s KB %s K double/dimacs/round %s" % (
            rec["instance"], bd.get("kc"), bd.get("kb"),
            [bd[c]["k"] if bd.get(c) else None for c in X.CONVS]) + (" ERROR " + rec["error"] if rec.get("error")
                                                                      else ""))
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump({"eps": X.EPS, "seed": X.SEED, "instances": recs}, f, indent=1)
    with open(os.path.join(out, "cliques.json"), "w", encoding="utf-8") as f:
        json.dump(cliques, f)

    pub, pub_cliques = fetch_published(args.tries, args.wait)
    tally = compare(recs, cliques, pub or {}, pub_cliques or {})
    with open(os.path.join(out, "tally.json"), "w", encoding="utf-8") as f:
        json.dump(tally, f, indent=1)
    head = ["id", "instance", "KC", "KB", "KT_double", "KT_dimacs", "KT_round", "K_double", "K_dimacs", "K_round"]
    lines = ["# xltwlb.py against the published vrptwlb/ results", "",
             "Predictions: `%s`" % json.dumps(tally["predictions"]), "",
             "Tally: `%s`" % json.dumps({k: v for k, v in tally.items() if k != "predictions"}), "",
             "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in recs:
        bd = r.get("bounds")
        if not bd:
            lines.append("| %s | %s | error |" % (r["id"], r["instance"]))
            continue
        kt = [bd[c]["kt"] if bd.get(c) else "" for c in X.CONVS]
        k = [bd[c]["k"] if bd.get(c) else "" for c in X.CONVS]
        lines.append("| " + " | ".join(str(v) for v in [r["id"], r["instance"], bd["kc"], bd["kb"]] + kt + k) + " |")
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps(tally), flush=True)


if __name__ == "__main__":
    main()
