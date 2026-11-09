"""Second xltwrun merge: put the clean re-runs of the 7 paused instances in place of their paused results.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

Rule: xltwrun/rerun-2026-11-08.md (fixed before any re-run ran). A re-run is clean when the harness calls it valid
and the runner log shows no pause or resume while it ran (audits: xltwrun/rerun-attempt-1.md,
xltwrun/rerun-attempt-2.md). Clean re-runs replace the old results; everything else is exactly as in xltwmerge-v1.

Inputs: the nine part files of xltwmerge-v1 (results-a.json from the repo, results-b1f/b2f/b3f.json made by the
unchanged filt.py, and the five first-round re-run files), plus one single-instance file per clean re-run. Output:
the same nine files with the seven instances removed, and the seven clean re-run files, in OUT_DIR, plus
swap-report.json. Refuses (SystemExit) if a clean re-run is not valid, is missing, or does not replace exactly one
old record.

  python swap.py --in-dir in/xltwrun --filtered /out/m1f --out /out/m2in
"""
import argparse
import json
import os
import shutil

V1_PARTS = [("in", "results-a.json"), ("filtered", "results-b1f.json"), ("filtered", "results-b2f.json"),
            ("filtered", "results-b3f.json"), ("in", "results-b1ra.json"), ("in", "results-b1rb.json"),
            ("in", "results-b2r.json"), ("in", "results-b3ra.json"), ("in", "results-b3rb.json")]
CLEAN = {  # instance -> re-run file (path below --in-dir), from the two pause audits
    "XLTW-Test-n7037": "rerun-v1/results-r7037.json",
    "XLTW-Test-n9571": "rerun-v1/results-r9571.json",
    "XLTW-Test-n10001": "rerun-v1/results-r10001.json",
    "XLTW-Test-n8389": "rerun-v2/results-r8389.json",
    "XLTW-Test-n8575": "rerun-v2/results-r8575.json",
    "XLTW-Test-n9160": "rerun-v2/results-r9160.json",
    "XLTW-Test-n9363": "rerun-v2/results-r9363.json",
}
SCALE = 30.0
SEED = 20261104


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check_rerun(name, doc):
    """A clean re-run file: same scale and seed, exactly one run, the right instance, valid, no signals."""
    if doc.get("scale") != SCALE:
        raise SystemExit("%s: scale %r, expected %r" % (name, doc.get("scale"), SCALE))
    runs = doc.get("runs") or []
    if len(runs) != 1 or runs[0].get("instance") != name:
        raise SystemExit("%s: expected exactly one run of this instance, got %r"
                         % (name, [r.get("instance") for r in runs]))
    r = runs[0]
    bad = []
    if r.get("error"):
        bad.append("error")
    if not r.get("exact_ok"):
        bad.append("not exact_ok")
    if not r.get("cost_line_ok"):
        bad.append("cost line wrong")
    if r.get("other_stdout_lines"):
        bad.append("other stdout")
    if r.get("sigterm_at") is not None or r.get("sigkill_at") is not None:
        bad.append("signal")
    if r.get("seed") != SEED:
        bad.append("seed %r" % r.get("seed"))
    if bad:
        raise SystemExit("%s: re-run not valid (%s)" % (name, ", ".join(bad)))
    return r


def swap(in_dir, filtered, out, clean=None):
    clean = CLEAN if clean is None else clean
    os.makedirs(out, exist_ok=True)
    report = {"replaced": [], "parts": [], "rerun_files": []}
    dropped = {}
    for where, fname in V1_PARTS:
        src = os.path.join(in_dir if where == "in" else filtered, fname)
        doc = load(src)
        keep = []
        for r in doc["runs"]:
            if r["instance"] in clean:
                if r["instance"] in dropped:
                    raise SystemExit("%s appears twice in the xltwmerge-v1 parts" % r["instance"])
                dropped[r["instance"]] = {"from": fname, "vehicles": r.get("vehicles"),
                                          "distance": r.get("distance"), "sigterm_at": r.get("sigterm_at")}
            else:
                keep.append(r)
        doc["runs"] = keep
        doc["swapped_from"] = fname
        with open(os.path.join(out, fname), "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, indent=1)
        report["parts"].append({"file": fname, "runs": len(keep)})
    missing = sorted(set(clean) - set(dropped))
    if missing:
        raise SystemExit("clean re-runs with no old record to replace: %s" % missing)
    for name in sorted(clean, key=lambda s: int(s.rsplit("n", 1)[1])):
        rel = clean[name]
        doc = load(os.path.join(in_dir, rel))
        r = check_rerun(name, doc)
        dest = os.path.basename(rel)
        shutil.copyfile(os.path.join(in_dir, rel), os.path.join(out, dest))
        report["rerun_files"].append(dest)
        old = dropped[name]
        report["replaced"].append({"instance": name, "old_part": old["from"], "old_vehicles": old["vehicles"],
                                   "old_distance": old["distance"], "old_sigterm_at": old["sigterm_at"],
                                   "new_file": rel, "new_vehicles": r["vehicles"], "new_distance": r["distance"]})
    report["merge_list"] = [os.path.join(out, f) for _, f in V1_PARTS] + \
        [os.path.join(out, f) for f in report["rerun_files"]]
    with open(os.path.join(out, "swap-report.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, indent=1)
    with open(os.path.join(out, "merge-list.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(",".join(report["merge_list"]))
    print(json.dumps(report["replaced"]), flush=True)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", required=True)
    ap.add_argument("--filtered", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    swap(a.in_dir, a.filtered, a.out)


if __name__ == "__main__":
    main()
