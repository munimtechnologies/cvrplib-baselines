"""Replace frozen first runs by their re-runs before xltwrun's pre-registered merge (G0-G5).

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

Rule fixed in xltwrun/part-b-note.md before any re-run result was known: a run whose SIGTERM was sent more than 1 s
after its limit is invalid and is re-run once, unchanged; the final score uses the re-runs. So every instance that
appears in a re-run file (b1ra, b1rb, b2r, b3ra, b3rb) is dropped from its original part (b1, b2, b3), and the
dropped records are listed. Nothing else is changed.

(Unchanged copy of the filt.py used by job xltwmerge-v1, 2026-11-06.)

  python filt.py IN_DIR OUT_DIR
"""
import json
import os
import sys

ORIG = ["b1", "b2", "b3"]
RERUN = ["b1ra", "b1rb", "b2r", "b3ra", "b3rb"]


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def filt(in_dir, out_dir):
    rerun = {}
    for p in RERUN:
        for r in load(os.path.join(in_dir, "results-%s.json" % p))["runs"]:
            rerun[r["instance"]] = p
    report = {"replaced": [], "kept_frozen_by_rule": []}
    os.makedirs(out_dir, exist_ok=True)
    for p in ORIG:
        doc = load(os.path.join(in_dir, "results-%s.json" % p))
        keep = []
        for r in doc["runs"]:
            if r["instance"] in rerun:
                late = (r.get("sigterm_at") is not None and r["sigterm_at"] > r["limit"] + 1.0)
                if not late:
                    raise SystemExit("%s in %s was re-run but its SIGTERM was not late" % (r["instance"], p))
                report["replaced"].append({"instance": r["instance"], "from": p, "by": rerun[r["instance"]],
                                           "limit": r["limit"], "sigterm_at": r["sigterm_at"]})
            else:
                if r.get("sigterm_at") is not None and r["sigterm_at"] > r["limit"] + 1.0:
                    raise SystemExit("%s in %s has a late SIGTERM but no re-run" % (r["instance"], p))
                keep.append(r)
        doc["runs"] = keep
        doc["filtered_from"] = "results-%s.json" % p
        with open(os.path.join(out_dir, "results-%sf.json" % p), "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, indent=1)
    for p in RERUN:
        for r in load(os.path.join(in_dir, "results-%s.json" % p))["runs"]:
            if r.get("sigterm_at") is not None and r["sigterm_at"] > r["limit"] + 1.0:
                report["kept_frozen_by_rule"].append({"instance": r["instance"], "part": p, "limit": r["limit"],
                                                      "sigterm_at": r["sigterm_at"]})
    with open(os.path.join(out_dir, "filter-report.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, indent=1)
    print(json.dumps(report), flush=True)
    return report


if __name__ == "__main__":
    filt(sys.argv[1], sys.argv[2])
