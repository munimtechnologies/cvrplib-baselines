"""Fleet lower bounds for CVRPLib's XLTW-Test set, scored against xltwlb/predictions-xltw-test.md (fixed 2026-10-31).

MV2 of Munim, Inc. Made with AI agents working in MV2's name. Apache-2.0.

Downloads XLTW-Test.7z from CVRPLib once, extracts it, describes every file (size, SHA-256, header keys and section
names; no instance data is copied out), parses each instance with `xltwlb.parse_any` (VRPLIB or Solomon), and runs
the unchanged `xltwlb.bound_one` (imported from tag v0.3.3) in the challenge's convention ('round': each arc
floor(d + 0.5), travel time = distance, as the rules published on 2026-11-02 say) and in 'double' and 'dimacs'.
Instances run smallest first and each result is logged as it finishes, so a run stopped from outside keeps them.
"""
import argparse
import hashlib
import json
import os
import re
import statistics
import time
import traceback
import urllib.request

import xltwlb as X

URL = "https://galgos.inf.puc-rio.br/cvrplib/uploads/files/vrptw_challenge/XLTW-Test.7z"
UA = "CVRPLib XLTW fleet bounds - MV2 of Munim, Inc. (mv2@munimtech.com)"
CHALLENGE = "round"
CONVS = ("round", "double", "dimacs")
MAX_GB = 1.0
MAX_SECONDS = 1800.0
T0 = time.time()


def log(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url, dest, ua=UA):
    """One GET. Returns the response headers that matter for provenance."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=300) as r, open(dest + ".part", "wb") as f:
        head = {k: r.headers.get(k) for k in ("Content-Length", "Last-Modified", "ETag", "Content-Type")}
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
    os.replace(dest + ".part", dest)
    return head


def extract(archive, dest):
    import py7zr
    os.makedirs(dest, exist_ok=True)
    with py7zr.SevenZipFile(archive, mode="r") as z:
        z.extractall(path=dest)
    return dest


def describe(text):
    """Header keys and section names of a VRPLIB-like text (names only), plus a few header values."""
    keys, sections, values = [], [], {}
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        w = s.split()[0].rstrip(":").upper()
        if w.endswith("_SECTION") and w not in sections:
            sections.append(w)
        elif ":" in s and not X._is_num(s.split()[0]):
            k, v = s.split(":", 1)
            k = k.strip().upper()
            if k not in keys:
                keys.append(k)
            if k in ("TYPE", "EDGE_WEIGHT_TYPE", "DIMENSION", "CAPACITY", "VEHICLES", "SERVICE_TIME"):
                values[k] = v.strip()
    return keys, sections, values


def looks_like_instance(path, text):
    return (path.lower().endswith((".vrp", ".vrptw")) or "NODE_COORD_SECTION" in text.upper()
            or re.search(r"CUST(OMER)?\s*NO", text.upper()) is not None)


def stats_of(inst):
    rows = inst["rows"]
    cust = rows[1:]
    horizon = rows[0][4]
    widths = [r[4] - r[3] for r in cust]
    service = [r[5] for r in cust]
    demand = [r[2] for r in cust]
    integer = all(float(r[0]).is_integer() and float(r[1]).is_integer() for r in rows)
    return {"customers": len(cust), "capacity": inst["capacity"], "total_demand": sum(demand),
            "max_demand": max(demand) if demand else None, "horizon": horizon,
            "service_min": min(service) if service else None, "service_max": max(service) if service else None,
            "width_min": min(widths) if widths else None, "width_median": statistics.median(widths) if widths else None,
            "width_max": max(widths) if widths else None,
            "full_horizon_share": round(sum(1 for r in cust if r[3] <= rows[0][3] and r[4] >= horizon)
                                        / max(len(cust), 1), 4),
            "integer_coords": integer, "header_vehicles": inst.get("vehicles")}


def scan(root):
    """Walk the extracted tree. Returns (instances [(path, inst)], manifest rows, parse errors)."""
    insts, manifest, errors = [], [], []
    for dirpath, _, files in os.walk(root):
        for fn in sorted(files):
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            row = {"path": rel, "bytes": os.path.getsize(p), "sha256": sha256(p), "kind": "other"}
            try:
                with open(p, encoding="utf-8") as f:
                    text = f.read()
            except (UnicodeDecodeError, OSError) as e:
                row["note"] = "not text: %s" % type(e).__name__
                manifest.append(row)
                continue
            row["keys"], row["sections"], row["values"] = describe(text)
            if looks_like_instance(rel, text):
                try:
                    inst = X.parse_any(text)
                    row["kind"] = "instance"
                    row["name"] = inst["name"]
                    row["stats"] = stats_of(inst)
                    insts.append((rel, inst))
                except Exception as e:  # noqa: BLE001 - recorded, counts against P1
                    row["kind"] = "instance_unparsed"
                    row["error"] = "%s: %s" % (type(e).__name__, e)
                    errors.append(rel)
            manifest.append(row)
    manifest.sort(key=lambda r: r["path"])
    insts.sort(key=lambda pi: (len(pi[1]["rows"]), pi[0]))
    return insts, manifest, errors


def bound_all(insts, convs, progress_path):
    recs, cliques = [], {}
    t = time.time()
    with open(progress_path, "a", encoding="utf-8") as prog:
        for rel, inst in insts:
            rec = {"path": rel, "instance": inst["name"]}
            try:
                b = X.bound_one(inst, convs)
                cliques[inst["name"]] = {c: b[c].pop("clique") for c in convs if b[c]}
                rec["bounds"] = b
            except Exception:
                rec["error"] = traceback.format_exc()
            rec["peak_gb"] = X.peak_gb()
            rec["elapsed_s"] = round(time.time() - t, 1)
            recs.append(rec)
            prog.write(json.dumps(rec) + "\n")
            prog.flush()
            log("%s %s" % (rel, json.dumps({k: v for k, v in rec.items() if k not in ("error",)})
                           + (" ERROR " + rec["error"] if rec.get("error") else "")))
    return recs, cliques, time.time() - t


def verdict(ok):
    return "untestable" if ok is None else ("held" if ok else "did not hold")


def tally(recs, parse_errors, peak, seconds, conv=CHALLENGE):
    def b(r, c):
        return (r.get("bounds") or {}).get(c)

    n = len(recs)
    errs = [r["path"] for r in recs if r.get("error")] + list(parse_errors)
    unbounded = [r["path"] for r in recs if not r.get("error") and (b(r, conv) is None or b(r, "double") is None)]
    unserv = [r["path"] for r in recs for c in (conv, "double") if b(r, c) and b(r, c)["unservable"]]
    unverified = ["%s/%s" % (r["path"], c) for r in recs for c in CONVS if b(r, c) and not b(r, c)["verified"]]
    kb_gt_kc = [r["path"] for r in recs if r.get("bounds") and r["bounds"]["kb"] > r["bounds"]["kc"]]
    in_conv = [r for r in recs if b(r, conv)]
    kt_binds = [r["path"] for r in in_conv if b(r, conv)["kt"] > r["bounds"]["kb"]]
    both = [r for r in recs if b(r, conv) and b(r, "double")]
    same_k = [r["path"] for r in both if b(r, conv)["k"] == b(r, "double")["k"]]
    t = {"instances": n, "errors": errs, "unbounded": unbounded, "unservable": sorted(set(unserv)),
         "unverified_cliques": unverified, "peak_gb": peak, "bound_seconds": round(seconds, 1),
         "kb_gt_kc": kb_gt_kc, "bounded_in_conv": len(in_conv), "kt_gt_kb_in_conv": kt_binds,
         "compared_conv_double": len(both), "k_conv_eq_double": len(same_k)}
    if n == 0:
        t["predictions"] = {k: "untestable" for k in ("P1", "P2", "P3", "P4")}
        return t
    t["predictions"] = {
        "P1": verdict(not errs and not unbounded and not unserv and peak is not None and peak <= MAX_GB
                      and seconds <= MAX_SECONDS),
        "P2": verdict(len(kb_gt_kc) >= 1),
        "P3": verdict(len(kt_binds) <= 0.25 * len(in_conv) if in_conv else None),
        "P4": verdict(len(same_k) >= 0.75 * len(both) if both else None),
    }
    return t


def write_md(path, head, manifest, recs, t):
    lines = ["# XLTW-Test: fleet lower bounds", "",
             "Archive: `%s`, %s bytes, SHA-256 `%s`, Last-Modified %s." % (
                 head.get("url"), head.get("bytes"), head.get("sha256"), head.get("Last-Modified")), "",
             "Predictions: `%s`" % json.dumps(t["predictions"]), "",
             "Instances %d; bounded in '%s' %d; peak %.3f GB; bounding %.1f s." % (
                 t["instances"], CHALLENGE, t["bounded_in_conv"], t["peak_gb"] or -1, t["bound_seconds"]), "",
             "| instance | n | Q | KC | KB | KT round | K round | KT double | K double | KT dimacs | K dimacs |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in recs:
        bd = r.get("bounds")
        if not bd:
            lines.append("| %s | error | | | | | | | | | |" % r["instance"])
            continue
        row = [r["instance"], str(bd["customers"]), str(bd["capacity"]), str(bd["kc"]), str(bd["kb"])]
        for c in CONVS:
            row += [str(bd[c]["kt"]), str(bd[c]["k"])] if bd.get(c) else ["-", "-"]
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", "Files in the archive:", "", "| path | bytes | kind | sections |", "|---|---|---|---|"]
    for m in manifest:
        lines.append("| %s | %d | %s | %s |" % (m["path"], m["bytes"], m["kind"], " ".join(m.get("sections", []))))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=URL)
    ap.add_argument("--archive", default="", help="use a local archive instead of downloading")
    ap.add_argument("--convs", default=",".join(CONVS))
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    args = ap.parse_args()
    out = os.path.join(args.out_dir, "xltwtest")
    os.makedirs(out, exist_ok=True)
    convs = [c for c in args.convs.split(",") if c]
    if args.archive:
        archive, head = args.archive, {}
    else:
        archive = os.path.join(args.data_dir, "xltw-test", "XLTW-Test.7z")
        head = download(args.url, archive)
    head.update({"url": args.url if not args.archive else args.archive, "bytes": os.path.getsize(archive),
                 "sha256": sha256(archive), "read_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    log("archive %s" % json.dumps(head))
    root = extract(archive, os.path.join(args.data_dir, "xltw-test", "x-" + head["sha256"][:12]))
    insts, manifest, parse_errors = scan(root)
    log("%d files, %d instances, %d unparsed: %s" % (len(manifest), len(insts), len(parse_errors), parse_errors))
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"archive": head, "files": manifest}, f, indent=1)
    recs, cliques, secs = bound_all(insts, convs, os.path.join(out, "progress.jsonl"))
    t = tally(recs, parse_errors, X.peak_gb(), secs)
    print(json.dumps(t["predictions"]), flush=True)
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump({"archive": head, "convs": convs, "challenge_conv": CHALLENGE, "instances": recs, "tally": t},
                  f, indent=1)
    with open(os.path.join(out, "cliques.json"), "w", encoding="utf-8") as f:
        json.dump(cliques, f)
    write_md(os.path.join(out, "results.md"), head, manifest, recs, t)
    if t["errors"]:
        raise SystemExit("%d instance(s) failed" % len(t["errors"]))


if __name__ == "__main__":
    main()
