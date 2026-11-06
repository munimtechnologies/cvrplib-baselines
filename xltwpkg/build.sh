#!/usr/bin/env bash
# xltw-solver build: unpacks pinned, sha256-checked wheels into lib/ and writes the ./solver launcher.
# MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.
#
#   bash build.sh            use vendor/wheels/, downloading a missing wheel from PyPI if the network allows
#   bash build.sh --offline  never touch the network (vendor/wheels/ must hold every wheel)
#
# Needs only bash and CPython 3.11, 3.12 or 3.13 (standard library) on Linux x86-64 with glibc 2.28 or newer.
# No pip, no venv, no root. Set XLTW_PYTHON=/path/to/python3.x to choose the interpreter.
#
# Interpreter choice (0.1.1): XLTW_PYTHON, then the machine's default `python3`, then `python`, and only then
# python3.13 / 3.12 / 3.11. Version 0.1.0 tried python3.13 first; in the python:3.12 Docker image that picked
# Debian's /usr/bin/python3.13 instead of the default /usr/local/bin/python3 (3.12), so lib/ held cp313 wheels
# that the default interpreter could not import. The chosen interpreter is recorded in lib/XLTW_BUILD.json.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

OFFLINE=""
for arg in "$@"; do
  case "$arg" in
    --offline) OFFLINE="--offline" ;;
    *) echo "build.sh: unknown argument $arg" >&2; exit 2 ;;
  esac
done

PY=""
for cand in "${XLTW_PYTHON:-}" python3 python python3.13 python3.12 python3.11; do
  [ -n "$cand" ] || continue
  path="$(command -v "$cand" 2>/dev/null)" || continue
  if "$path" -c 'import sys; sys.exit(0 if sys.implementation.name == "cpython" and (3, 11) <= sys.version_info[:2] <= (3, 13) else 1)' 2>/dev/null; then
    PY="$path"
    break
  fi
done
if [ -z "$PY" ]; then
  echo "build.sh: needs CPython 3.11, 3.12 or 3.13; set XLTW_PYTHON=/path/to/python3.x" >&2
  exit 1
fi
TAG="$("$PY" -c 'import sys; print("cp%d%d" % sys.version_info[:2])')"
echo "build.sh: using $PY ($TAG)"

"$PY" lock.py --install --tag "$TAG" --dest "$HERE/lib" $OFFLINE

cat > "$HERE/solver" <<EOF
#!/usr/bin/env bash
# xltw-solver launcher, written by build.sh. Usage: ./solver INSTANCE SECONDS SEED
# No user site, no script-directory path entry, no outside PYTHON* settings; a fixed hash seed.
unset PYTHONPATH PYTHONHOME PYTHONSTARTUP PYTHONUSERBASE PYTHONINSPECT PYTHONWARNINGS PYTHONSAFEPATH
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0 PYTHONNOUSERSITE=1
exec "$PY" -s -P "$HERE/solver.py" "\$@"
EOF
chmod +x "$HERE/solver"

# Self-check: the solver's dependencies import from lib/, with nothing from the network.
"$PY" -I -c '
import importlib.metadata as m, os, sys
here = sys.argv[1]
sys.path.insert(0, os.path.join(here, "lib"))
import numpy, pyvrp
assert numpy.__file__.startswith(os.path.join(here, "lib")), numpy.__file__
assert pyvrp.__file__.startswith(os.path.join(here, "lib")), pyvrp.__file__
print("build.sh: ok, pyvrp %s and numpy %s from lib/" % (m.version("pyvrp"), numpy.__version__))
' "$HERE"
