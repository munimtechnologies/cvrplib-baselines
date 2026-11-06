"""Tests for xltw-solver's packaging: lock.py, the stdout discipline and printer of solver.py, and the built lib/.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name. Apache-2.0.
Standard library only. Tests that need the built package (lib/, ./solver) are skipped until build.sh has run.

0.1.1: every subprocess that imports lib/ runs under the interpreter the build recorded (lib/XLTW_BUILD.json), not
under whatever Python runs the tests. In 0.1.0 these were the same by assumption, and in the python:3.12 image they
were not (build.sh had picked python3.13), so two tests failed on an import error while the build was fine.
"""
import hashlib
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lock  # noqa: E402
import solver  # noqa: E402

BUILT = os.path.exists(os.path.join(HERE, "lib", "XLTW_BUILD.json")) and os.path.exists(os.path.join(HERE, "solver"))
BUILD_PY = lock.build_python() if BUILT else None
PY = BUILD_PY or sys.executable  # the interpreter for subprocesses that may import lib/


def _f(name, sha="0" * 64, kind="bdist_wheel", yanked=False):
    return {"filename": name, "packagetype": kind, "yanked": yanked, "digests": {"sha256": sha},
            "url": "https://files.example/" + name}


class Pick(unittest.TestCase):
    def test_pure_wheel(self):
        got = lock.pick("tqdm", "4.67.1", [_f("tqdm-4.67.1.tar.gz", kind="sdist"), _f("tqdm-4.67.1-py3-none-any.whl")])
        self.assertEqual([(w["tag"], w["filename"]) for w in got], [("any", "tqdm-4.67.1-py3-none-any.whl")])

    def test_one_manylinux_x86_64_per_tag(self):
        files = [_f("numpy-2.3.4-%s-%s-%s.whl" % (t, t, p)) for t in ("cp311", "cp312", "cp313")
                 for p in ("manylinux_2_27_x86_64.manylinux_2_28_x86_64", "musllinux_1_2_x86_64",
                           "manylinux_2_27_aarch64.manylinux_2_28_aarch64", "win_amd64")]
        files.append(_f("numpy-2.3.4-cp313-cp313t-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl"))
        got = lock.pick("numpy", "2.3.4", files)
        self.assertEqual([w["tag"] for w in got], ["cp311", "cp312", "cp313"])
        for w in got:
            self.assertIn("manylinux", w["filename"])
            self.assertTrue(w["filename"].endswith("x86_64.whl"))
            self.assertNotIn("cp313t", w["filename"])

    def test_yanked_and_missing(self):
        files = [_f("x-1-cp311-cp311-manylinux_2_28_x86_64.whl", yanked=True)]
        with self.assertRaises(lock.LockError):
            lock.pick("x", "1", files, tags=("cp311",))

    def test_select_needs_one_per_pin(self):
        doc = {"pins": [{"name": "a", "version": "1"}, {"name": "b", "version": "2"}],
               "wheels": [{"name": "a", "tag": "cp312"}, {"name": "b", "tag": "any"}, {"name": "a", "tag": "cp311"}]}
        self.assertEqual(len(lock.select(doc, "cp312")), 2)
        doc["wheels"].append({"name": "a", "tag": "any"})
        with self.assertRaises(lock.LockError):
            lock.select(doc, "cp312")
        with self.assertRaises(lock.LockError):
            lock.select(doc, "cp310")


class FetchAndExtract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _wheel(self, name, members):
        path = os.path.join(self.d, name)
        with zipfile.ZipFile(path, "w") as z:
            for arc, body, mode in members:
                info = zipfile.ZipInfo(arc)
                info.external_attr = mode << 16
                z.writestr(info, body)
        return path

    def test_offline_missing_is_an_error(self):
        w = {"filename": "a.whl", "sha256": "0" * 64, "url": "http://unused"}

        def boom(url):
            raise AssertionError("network used")
        with self.assertRaises(lock.LockError):
            lock.fetch_one(w, True, vendor=self.d, getter=boom)

    def test_download_is_checked(self):
        body = b"wheel bytes"
        w = {"filename": "a.whl", "sha256": hashlib.sha256(body).hexdigest(), "url": "http://x"}
        path = lock.fetch_one(w, False, vendor=self.d, getter=lambda url: body)
        with open(path, "rb") as f:
            self.assertEqual(f.read(), body)
        self.assertEqual(lock.fetch_one(w, True, vendor=self.d), path)  # now served offline
        bad = dict(w, filename="b.whl")
        with self.assertRaises(lock.LockError):
            lock.fetch_one(bad, False, vendor=self.d, getter=lambda url: b"tampered")
        self.assertFalse(os.path.exists(os.path.join(self.d, "b.whl")))

    def test_tampered_vendor_file_is_refused(self):
        with open(os.path.join(self.d, "c.whl"), "wb") as f:
            f.write(b"changed")
        w = {"filename": "c.whl", "sha256": hashlib.sha256(b"original").hexdigest(), "url": "http://x"}
        with self.assertRaises(lock.LockError):
            lock.fetch_one(w, True, vendor=self.d)

    def test_extract_refuses_escape(self):
        wh = self._wheel("evil.whl", [("../evil.txt", b"x", 0o644)])
        dest = os.path.join(self.d, "lib")
        os.makedirs(dest)
        with self.assertRaises(lock.LockError):
            lock.safe_extract(wh, dest)
        self.assertFalse(os.path.exists(os.path.join(self.d, "evil.txt")))

    @unittest.skipIf(os.name != "posix", "permission bits are POSIX")
    def test_extract_keeps_modes(self):
        wh = self._wheel("ok.whl", [("pkg/__init__.py", b"", 0o644), ("pkg/_ext.so", b"\x7fELF", 0o755)])
        dest = os.path.join(self.d, "lib")
        os.makedirs(dest)
        lock.safe_extract(wh, dest)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(dest, "pkg", "_ext.so")).st_mode), 0o755)
        self.assertTrue(os.path.exists(os.path.join(dest, "pkg", "__init__.py")))

    def test_install_refuses_a_tag_of_another_python(self):
        running = "cp%d%d" % sys.version_info[:2]
        other = [t for t in lock.TAGS if t != running][0]
        path = os.path.join(self.d, "wheels.lock")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"pins": [{"name": "a", "version": "1"}],
                       "wheels": [{"name": "a", "version": "1", "tag": t, "filename": "a-%s.whl" % t,
                                   "sha256": "0" * 64, "url": "http://unused"} for t in lock.TAGS]}, f)
        with self.assertRaises(lock.LockError) as cm:
            lock.install(other, os.path.join(HERE, "lib-test-unused"), True, lock=path, vendor=self.d)
        self.assertIn("does not match the interpreter", str(cm.exception))
        self.assertFalse(os.path.exists(os.path.join(HERE, "lib-test-unused")))


class FakeSol:
    def __init__(self, routes, dist, feasible=True):
        self.r, self.d, self.f = routes, dist, feasible

    def is_feasible(self):
        return self.f

    def num_routes(self):
        return len(self.r)

    def distance(self):
        return self.d


class PrinterTests(unittest.TestCase):
    def setUp(self):
        self.now = [0.0]
        self.buf = io.StringIO()
        self.p = solver.Printer(50.0, out=self.buf, convert=lambda s: s.r, clock=lambda: self.now[0])

    def test_format(self):
        self.assertEqual(solver.format_solution([[3, 1], [2]], 17), "Route #1: 3 1\nRoute #2: 2\nCost: 17\n")

    def test_better_only_and_vehicles_first(self):
        self.assertFalse(self.p.offer(FakeSol([[1, 2]], 10, feasible=False)))
        self.assertTrue(self.p.offer(FakeSol([[1], [2]], 10)))
        self.assertFalse(self.p.offer(FakeSol([[2], [1]], 10)))          # equal: not printed again
        self.now[0] = 5.0
        self.assertTrue(self.p.offer(FakeSol([[1, 2]], 99)))             # fewer routes wins over distance
        self.assertEqual(self.buf.getvalue(), "Route #1: 1\nRoute #2: 2\nCost: 10\nRoute #1: 1 2\nCost: 99\n")

    def test_throttle_holds_then_flushes(self):
        self.p.offer(FakeSol([[1], [2]], 10))
        self.now[0] = 0.2                                                # gap is max(1, 0.5) = 1 s
        self.p.offer(FakeSol([[1], [2]], 9))
        self.assertEqual(self.p.prints, 1)
        self.assertEqual(self.p.best_key(), (2, 9))
        self.assertTrue(self.p.flush(True))
        self.assertTrue(self.buf.getvalue().endswith("Cost: 9\n"))
        self.assertFalse(self.p.flush(True))

    def test_margin(self):
        self.assertAlmostEqual(solver.margin(60.0), 1.62)
        self.assertAlmostEqual(solver.margin(18000.0), 30.0)


@unittest.skipIf(os.name != "posix", "fd juggling is checked on Linux, where the challenge runs")
class StdoutDiscipline(unittest.TestCase):
    def _run(self, code):
        p = subprocess.run([PY, "-c", code], cwd=HERE, capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p

    def test_only_solutions_reach_stdout(self):
        p = self._run("import logging, os, sys; sys.path.insert(0, '.'); import solver\n"
                      "out = solver.claim_stdout()\n"
                      "print('stray print'); logging.getLogger('x').addHandler(logging.StreamHandler(sys.stdout))\n"
                      "logging.getLogger('x').warning('log line'); os.write(1, b'c-level write\\n')\n"
                      "out.write(solver.format_solution([[1, 2]], 5)); out.flush()\n")
        self.assertEqual(p.stdout, "Route #1: 1 2\nCost: 5\n")
        for s in ("stray print", "log line", "c-level write"):
            self.assertIn(s, p.stderr)

    @unittest.skipUnless(BUILT, "needs build.sh")
    def test_pyvrp_logger_goes_to_stderr(self):
        p = self._run("import logging, sys; sys.path.insert(0, '.'); import solver\n"
                      "out = solver.claim_stdout(); solver.load_helpers(); import pyvrp\n"
                      "logging.getLogger('pyvrp').info('pyvrp says hello')\n")
        self.assertEqual(p.stdout, "")
        self.assertIn("pyvrp says hello", p.stderr)


STUCK = """
import signal, sys, time
sys.path.insert(0, '.')
import solver
signal.signal(signal.SIGTERM, solver._on_term)
out = solver.claim_stdout()
class S:
    def __init__(self, d): self.d = d
    def is_feasible(self): return True
    def num_routes(self): return 1
    def distance(self): return self.d
pr = solver.Printer(100.0, out=out, convert=lambda s: [[1, 2]])
pr.offer(S(7))   # printed at once
pr.offer(S(5))   # better, but held by the 1 s throttle
solver.Watchdog(pr, time.monotonic() + float(sys.argv[1]), out).start()
time.sleep(60)   # stands in for a long PyVRP call that releases the GIL
print('not reached')
"""


@unittest.skipIf(os.name != "posix", "signals and fd juggling are checked on Linux, where the challenge runs")
class WatchdogTests(unittest.TestCase):
    WANT = "Route #1: 1 2\nCost: 7\nRoute #1: 1 2\nCost: 5\n"

    def test_hard_deadline_ends_a_stuck_call(self):
        t = __import__("time").monotonic()
        p = subprocess.run([PY, "-c", STUCK, "2.0"], cwd=HERE, capture_output=True, text=True, timeout=30)
        took = __import__("time").monotonic() - t
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout, self.WANT)          # the held solution got out too
        self.assertIn("XLTW_WATCHDOG deadline", p.stderr)
        self.assertNotIn("not reached", p.stderr)
        self.assertLess(took, 10.0)

    def test_sigterm_ends_a_stuck_call_at_once(self):
        import signal as sg
        import time as tm
        p = subprocess.Popen([PY, "-c", STUCK, "50.0"], cwd=HERE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True)
        tm.sleep(2.0)
        t = tm.monotonic()
        p.send_signal(sg.SIGTERM)
        out, err = p.communicate(timeout=30)
        self.assertLess(tm.monotonic() - t, 3.0)
        self.assertEqual(p.returncode, 0, err)
        self.assertEqual(out, self.WANT)
        self.assertIn("XLTW_WATCHDOG sigterm", err)


class Built(unittest.TestCase):
    def test_no_crlf(self):
        for name in ("build.sh", "Makefile", "lock.py", "solver.py"):
            with open(os.path.join(HERE, name), "rb") as f:
                self.assertNotIn(b"\r", f.read(), name)

    @unittest.skipUnless(BUILT, "needs build.sh")
    def test_lib_has_the_pins(self):
        with open(os.path.join(HERE, "lib", "XLTW_BUILD.json"), encoding="utf-8") as f:
            info = json.load(f)
        got = {w["name"]: w["version"] for w in info["wheels"]}
        self.assertEqual(got, dict(lock.PINS))
        self.assertTrue(info.get("executable"), "XLTW_BUILD.json records no interpreter")
        code = ("import importlib.metadata as m, os, sys; sys.path.insert(0, os.path.join(sys.argv[1], 'lib'));"
                "import numpy, pyvrp; print(m.version('pyvrp'), numpy.__version__, pyvrp.__file__, "
                "'cp%d%d' % sys.version_info[:2])")
        p = subprocess.run([BUILD_PY, "-I", "-c", code, HERE], capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stderr)
        ver, npv, where, tag = p.stdout.split()
        self.assertEqual((ver, npv), ("0.14.1", "2.3.4"))
        self.assertTrue(where.startswith(os.path.join(HERE, "lib")))
        self.assertEqual(tag, info["tag"])

    @unittest.skipUnless(BUILT and os.name == "posix", "needs build.sh")
    def test_launcher(self):
        path = os.path.join(HERE, "solver")
        self.assertTrue(os.access(path, os.X_OK))
        with open(path, encoding="utf-8") as f:
            self.assertIn('exec "%s" -s -P' % BUILD_PY, f.read())  # the launcher runs the build's interpreter
        p = subprocess.run([path], capture_output=True, text=True, timeout=60)
        self.assertEqual((p.returncode, p.stdout), (2, ""))
        self.assertIn("usage", p.stderr)
        p = subprocess.run([path, "x.vrp", "-1", "3"], capture_output=True, text=True, timeout=60)
        self.assertEqual((p.returncode, p.stdout), (2, ""))


if __name__ == "__main__":
    unittest.main()
