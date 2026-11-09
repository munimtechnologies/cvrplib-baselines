"""Run the pinned, pre-registered `xltwrun.py --merge` on the list written by swap.py.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.

  python merge2.py /out/m2in/merge-list.txt /out/m2
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main(list_path, out_dir):
    with open(list_path, encoding="utf-8") as f:
        paths = f.read().strip()
    if len(paths.split(",")) != 16:
        raise SystemExit("expected 9 xltwmerge-v1 parts + 7 re-run files, got %d" % len(paths.split(",")))
    cmd = [sys.executable, os.path.join(HERE, "xltwrun.py"), "--merge", paths, "--out-dir", out_dir]
    print(" ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=HERE)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
