"""The cross-checks' guards must fail the runs they are there to fail (tests/crosscheck_guards.py).

    python3 tests/test_crosscheck_guards.py [CMAKE [API_RUNNER]]

Each test runs a real pipeline, gen | kairn-gen interp | check --json, on a tiny toy format, whose
stream the oracle passes but which did not check what a cross-check sets out to check (a
partial or restricted enumeration, strata missing, nothing judged, a comparison seen one way
only; in the extended domain, a class of results never seen: no overflow, no non-finite operand,
finite_when never put to the test, a ball result or a constructor's outcome missing, the strata
of the layer missing), or alters the summary of a good run where no stream can produce the fault;
and requires the guards to fail it, with their reason. It also runs the driver of the compiled
runners' cross-checks, tests/crosscheck.py, with the interpreter as its runner, on such runs,
which it must fail with the guards' reason, and on good ones, and with a runner that changes an
operand, whose invalid case must fail the run. With CMAKE, the path of cmake, it
runs crosscheck.cmake, the driver of the interpreter's enumerations, likewise; with API_RUNNER,
the public interface's runner (tests/api/runner.cpp), crosscheck.py api on a good run, on one
whose cases miss a stratum, and on a kernel the runner maps no form to.
"""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

TESTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TESTS)
PY = sys.executable
CMAKE = None
API_RUNNER = None


def pipeline(kernel, fmt, *gen_args, fail_on_suspicious=True):
    """The oracle's summary of gen KERNEL FMT GEN_ARGS | interp | check, which must pass."""
    with tempfile.TemporaryDirectory() as d:
        js = os.path.join(d, "s.json")
        gen = subprocess.run([PY, os.path.join(ROOT, "oracle", "kairn-oracle"), "gen", kernel, fmt]
                             + list(gen_args), capture_output=True, text=True, cwd=ROOT)
        assert gen.returncode == 0, gen.stderr
        run = subprocess.run([PY, os.path.join(ROOT, "gen", "kairn-gen"), "interp"],
                             input=gen.stdout, capture_output=True, text=True, cwd=ROOT)
        assert run.returncode == 0, run.stderr
        check = [PY, os.path.join(ROOT, "oracle", "kairn-oracle"), "check", "--json", js]
        if fail_on_suspicious:
            check.append("--fail-on-suspicious")
        ok = subprocess.run(check, input=run.stdout, capture_output=True, text=True, cwd=ROOT)
        assert ok.returncode == 0, ok.stdout + ok.stderr
        with open(js, encoding="utf-8") as f:
            return json.load(f)


def guards(summary, kernel, fmt, *args):
    """(exit status, output) of the guards on a summary."""
    with tempfile.TemporaryDirectory() as d:
        js = os.path.join(d, "s.json")
        with open(js, "w", encoding="utf-8") as f:
            json.dump(summary, f)
        r = subprocess.run([PY, os.path.join(TESTS, "crosscheck_guards.py"), js, "--kernel", kernel,
                            "--format", fmt] + list(args), capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr


class Guards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.good_exhaustive = pipeline("two_sum", "fp:3:-3:2", "--exhaustive")
        cls.good_random = pipeline("lt_2_2", "fp:4:-6:4", "--seed", "0", "--count", "200")
        cls.good_down = pipeline("to_down_2", "fp:4:-6:4", "--seed", "0", "--count", "200")

    def passes(self, summary, kernel, fmt, *args):
        status, out = guards(summary, kernel, fmt, *args)
        self.assertEqual(status, 0, out)
        return out

    def fails(self, summary, kernel, fmt, *args, reason):
        status, out = guards(summary, kernel, fmt, *args)
        self.assertEqual(status, 1, out)
        self.assertIn(reason, out)

    def test_good_runs_pass(self):
        out = self.passes(self.good_exhaustive, "two_sum", "fp:3:-3:2", "--exhaustive")
        self.assertIn("every operand, 3025 cases", out)
        self.passes(self.good_random, "lt_2_2", "fp:4:-6:4", "--seed", "0", "--count", "200")
        self.passes(self.good_down, "to_down_2", "fp:4:-6:4", "--seed", "0", "--count", "200")

    # The enumeration is what it claims.
    def test_partial_enumeration(self):
        s = pipeline("two_sum", "fp:3:-3:2", "--exhaustive", "--count", "3000")
        self.fails(s, "two_sum", "fp:3:-3:2", "--exhaustive", reason="was not covered")

    def test_restricted_enumeration_passed_off_as_complete(self):
        s = pipeline("two_sum", "fp:3:-3:2", "--exhaustive", "--restrict", "a.sign=+")
        self.fails(s, "two_sum", "fp:3:-3:2", "--exhaustive", reason="restricted by 'a.sign=+'")
        self.passes(s, "two_sum", "fp:3:-3:2", "--exhaustive", "--restrict", "a.sign=+")
        self.fails(s, "two_sum", "fp:3:-3:2", "--exhaustive", "--restrict", "a.sign=-",
                   reason="not by 'a.sign=-'")

    def test_another_stream(self):
        self.fails(self.good_exhaustive, "two_prod", "fp:3:-3:2", "--exhaustive",
                   reason="the stream is of two_sum")
        self.fails(self.good_exhaustive, "two_sum", "fp:3:-3:2", "--seed", "0", "--count", "3025",
                   reason="in mode exhaustive")
        self.fails(self.good_random, "lt_2_2", "fp:4:-6:4", "--seed", "1", "--count", "200",
                   reason="of seed 0, not cases 0 to 200 of seed 1")
        s = copy.deepcopy(self.good_exhaustive)
        s["coverage"].append(s["coverage"][0])
        self.fails(s, "two_sum", "fp:3:-3:2", "--exhaustive", reason="2 generator headers")

    # A random run has every stratum its generator promised.
    def test_a_stratum_missing(self):
        s = pipeline("lt_2_2", "fp:4:-6:4", "--seed", "0", "--count", "5")
        self.fails(s, "lt_2_2", "fp:4:-6:4", "--seed", "0", "--count", "5",
                   reason="no case of stratum")
        s = copy.deepcopy(self.good_random)
        s["keys"] = [k for k in s["keys"] if k["tag"] != "neighbor"]
        self.fails(s, "lt_2_2", "fp:4:-6:4", "--seed", "0", "--count", "200",
                   reason="no case of stratum neighbor")

    def test_strata_not_promised(self):
        s = pipeline("lt_2_2", "fp:4:-6:4", "--seed", "0", "--count", "200", "--strata",
                     "uniform,equal")
        self.fails(s, "lt_2_2", "fp:4:-6:4", "--seed", "0", "--count", "200",
                   reason="without underflow, which every family of kernels has")
        s = copy.deepcopy(self.good_random)
        s["keys"][0]["tag"] = "elsewhere"
        self.fails(s, "lt_2_2", "fp:4:-6:4", "--seed", "0", "--count", "200",
                   reason="lines tagged elsewhere")

    # Something was judged, every claim applied, and where it tells.
    def test_nothing_judged(self):
        s = pipeline("mul_2_2", "fp:3:-3:2", "--exhaustive")      # below its min_precision 4
        self.fails(s, "mul_2_2", "fp:3:-3:2", "--exhaustive", reason="judged no case")

    def test_a_claim_never_applied(self):
        s = copy.deepcopy(self.good_exhaustive)
        for k in s["keys"]:
            k["stats"]["entries"][1]["applicable"] = 0
        self.fails(s, "two_sum", "fp:3:-3:2", "--exhaustive", reason="applied to no judged case")

    def test_a_comparison_seen_one_way(self):
        # Every comparison is of the extended domain, whose enumerations always include the
        # infinities (-inf < y is true), so this is a random run of one stratum: equality of
        # random operands never holds.
        s = pipeline("eq_2_2", "fp:4:-6:1", "--seed", "0", "--count", "100", "--strata", "uniform")
        self.fails(s, "eq_2_2", "fp:4:-6:1", "--seed", "0", "--count", "100",
                   reason="was never true")

    def test_a_directed_rounding_that_never_steps(self):
        s = copy.deepcopy(self.good_down)
        for k in s["keys"]:
            k["stats"]["entries"][0]["counts"].pop("inexact, != RN", None)
        self.fails(s, "to_down_2", "fp:4:-6:4", "--seed", "0", "--count", "200",
                   reason="never differed from the rounding to nearest")


# The extended domain (the non-finite layer): toy formats of the shape qmin + qmax = 3 - 2p, as
# in the interpreter's enumerations. fp:3:-3:0 has the overflow threshold 2^3 and Omega = 7; add_2_2_full's
# finite_when bounds both operands by 2^(qmax+p-2) = 2 there (when its exponent is -2).
ADD = ("add_2_2_full", "fp:3:-3:0")
BALL = ("ball_add_1_full", "fp:2:-2:1")         # Omega = 6 = 0x1.8p+2


class ExtendedGuards(unittest.TestCase):
    def passes(self, summary, kernel, fmt, *args):
        status, out = guards(summary, kernel, fmt, *args)
        self.assertEqual(status, 0, out)
        return out

    def fails(self, summary, kernel, fmt, *args, reason):
        status, out = guards(summary, kernel, fmt, *args)
        self.assertEqual(status, 1, out)
        self.assertIn(reason, out)

    def test_good_runs_pass(self):
        s = pipeline(*ADD, "--exhaustive")
        out = self.passes(s, *ADD, "--exhaustive")
        self.assertIn("extended domain: F2 finite", out)
        self.assertIn("F3 applies", out)
        s = pipeline(*BALL, "--seed", "0", "--count", "400")
        self.passes(s, *BALL, "--seed", "0", "--count", "400")
        for kernel in ("make_2_limbs", "ball_make_2", "radd", "neg_2"):
            s = pipeline(kernel, "fp:3:-3:0", "--exhaustive")
            self.passes(s, kernel, "fp:3:-3:0", "--exhaustive")

    # extends: a finite result, an overflow, a non-finite operand, and F3 put to the test.
    def test_extends_without_an_overflow(self):
        s = pipeline(*ADD, "--exhaustive", "--restrict", "x.lead=-3:-2",
                     "--restrict", "y.lead=-3:-2")
        self.fails(s, *ADD, "--exhaustive", "--restrict", "x.lead=-3:-2,y.lead=-3:-2",
                   reason='saw no case of "class F4: finite operands, non-finite result"')

    def test_extends_without_a_nonfinite_operand(self):
        s = pipeline(*ADD, "--seed", "0", "--count", "200", "--strata", "uniform,edge")
        self.fails(s, *ADD, "--seed", "0", "--count", "200",
                   reason='saw no case of "class F5: a non-finite operand"')

    def test_extends_without_its_finite_when(self):
        # x0 = Omega: |x| > 2^(qmax+p+e) for every e < 0, so F3 never applies; F2, F4 and F5 do.
        s = pipeline(*ADD, "--exhaustive", "--restrict", "x.in=0x1.cp+2")
        self.fails(s, *ADD, "--exhaustive", "--restrict", "x.in=0x1.cp+2",
                   reason="saw no case where every finite_when condition holds")

    # encloses: each of the three results.
    def test_encloses_without_a_finite_ball(self):
        # A radius of Omega makes every result from finite operands the whole line.
        s = pipeline(*BALL, "--exhaustive", "--restrict", "rx.in=0x1.8p+2")
        self.fails(s, *BALL, "--exhaustive", "--restrict", "rx.in=0x1.8p+2",
                   reason='saw no case of "result: finite ball"')

    def test_encloses_without_the_empty_set(self):
        s = pipeline(*BALL, "--seed", "0", "--count", "200", "--strata", "uniform,hugeradius")
        self.fails(s, *BALL, "--seed", "0", "--count", "200",
                   reason='saw no case of "result: empty set"')

    # The constructors: each outcome.
    def test_constructors_without_every_outcome(self):
        s = pipeline("ball_make_1", "fp:3:-3:0", "--seed", "0", "--count", "100",
                     "--strata", "uniform")
        self.fails(s, "ball_make_1", "fp:3:-3:0", "--seed", "0", "--count", "100",
                   reason='saw no case of "given: whole line"')
        s = pipeline("make_2", "fp:3:-3:0", "--seed", "0", "--count", "100", "--strata", "uniform")
        self.fails(s, "make_2", "fp:3:-3:0", "--seed", "0", "--count", "100",
                   reason='saw no case of "value NaN"')

    # The kernels that gained the extended domain: non-finite operands.
    def test_existing_kinds_without_nonfinite_operands(self):
        for kernel, reason in (
                ("lt_2_2", '"a non-finite operand, true"'),
                ("to_down_2", '"a non-finite operand"'),
                ("radd", '"output +inf on a non-finite operand"'),
                ("neg_2", '"a non-finite operand"')):
            s = pipeline(kernel, "fp:3:-3:0", "--seed", "0", "--count", "100",
                         "--strata", "uniform")
            self.fails(s, kernel, "fp:3:-3:0", "--seed", "0", "--count", "100",
                       reason="saw no case of " + reason)

    # The strata of the layer, in a random run's header.
    def test_strata_of_the_layer_not_promised(self):
        common = "uniform,underflow,overflow,zero,pow2,extreme"
        s = pipeline("neg_2", "fp:3:-3:0", "--seed", "0", "--count", "100",
                     "--strata", common + ",halfgap")
        self.fails(s, "neg_2", "fp:3:-3:0", "--seed", "0", "--count", "100",
                   reason="without nonfinite, which it adds for neg_2 in the extended domain")
        s = pipeline(*ADD, "--seed", "0", "--count", "100", "--strata", common + ",nonfinite")
        self.fails(s, *ADD, "--seed", "0", "--count", "100", reason="without edge")
        self.fails(s, *ADD, "--seed", "0", "--count", "100", reason="without threshold")

    # Summaries altered where no stream can produce the fault.
    def test_claims_not_those_judged(self):
        good = pipeline("make_2_limbs", "fp:3:-3:0", "--exhaustive")
        s = copy.deepcopy(good)
        for k in s["keys"]:
            k["stats"]["entries"][0]["kind"] = "normalized"
        self.fails(s, "make_2_limbs", "fp:3:-3:0", "--exhaustive",
                   reason="are not those of the claims of make_2_limbs")
        s = copy.deepcopy(good)
        s["claims"] = os.path.join(ROOT, "no-such-claims.json")
        self.fails(s, "make_2_limbs", "fp:3:-3:0", "--exhaustive",
                   reason="cannot read the claims")

    # The driver of the compiled runners, crosscheck.py, passes the guards' verdict on: the
    # interpreter as its runner (--interp), on the enumerations above.
    def test_the_one_process_driver(self):
        with tempfile.TemporaryDirectory() as d:
            def drive(kernel, fmt, *args):
                return subprocess.run(
                    [PY, os.path.join(TESTS, "crosscheck.py"), "compiled", "--kernel", kernel,
                     "--format", fmt, "--summary", os.path.join(d, kernel + ".json"),
                     "--fail-on-suspicious", "--interp"] + list(args),
                    capture_output=True, text=True)
            bad = drive("mul_2_2", "fp:3:-3:2", "--exhaustive")
            self.assertEqual(bad.returncode, 1, bad.stdout + bad.stderr)
            self.assertIn("did not check what it set out to", bad.stdout)
            self.assertIn("judged no case", bad.stdout)
            self.assertTrue(os.path.isdir(os.path.join(d, "mul_2_2.work")))
            good = drive("two_sum", "fp:3:-3:2", "--exhaustive")
            self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
            self.assertIn("with interp: passed, 2903 cases judged (every operand, 3025 cases)",
                          good.stdout)
            self.assertIn("kairn-oracle check: PASS", good.stdout)
            self.assertFalse(os.path.exists(os.path.join(d, "two_sum.work")))
            self.assertTrue(os.path.exists(os.path.join(d, "two_sum.interp.json")))
            bad = drive(*ADD, "--exhaustive", "--restrict", "x.lead=-3:-2,y.lead=-3:-2")
            self.assertEqual(bad.returncode, 1, bad.stdout + bad.stderr)
            self.assertIn("class F4", bad.stdout)
            bad = drive("lt_2_2", "fp:4:-6:4", "--seed", "0", "--count", "5")
            self.assertEqual(bad.returncode, 1, bad.stdout + bad.stderr)
            self.assertIn("no case of stratum", bad.stdout)
            good = drive(*ADD, "--exhaustive")
            self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
            self.assertIn("extended domain: F2 finite", good.stdout)

    # A runner that changes an operand, so that a case is outside the kernel's requirements: the
    # oracle does not judge such a case (it is invalid), and the cross-check fails on it (check
    # --expect-valid). The runner is the interpreter behind a script; the same script without the
    # change passes.
    def test_a_runner_that_changes_an_operand(self):
        body = """import subprocess, sys
out = subprocess.run([sys.executable, %r, "interp"], stdin=sys.stdin.buffer,
                     stdout=subprocess.PIPE, check=True).stdout.decode("ascii")
lines = out.split("\\n")
for i, line in enumerate(lines):
    w = line.split(" ")
    if CHANGE and not line.startswith("#") and len(w) > 4 and w[2].lstrip("-").startswith("0x1"):
        w[3] = w[2]     # the second limb of x as large as its first: x is not normalized
        lines[i] = " ".join(w)
        break
sys.stdout.write("\\n".join(lines))
""" % os.path.join(ROOT, "gen", "kairn-gen")
        with tempfile.TemporaryDirectory() as d:
            def runner(name, change):
                script = os.path.join(d, name + ".py")
                with open(script, "w", encoding="utf-8") as f:
                    f.write("CHANGE = %r\n" % change + body)
                if os.name == "nt":
                    exe = os.path.join(d, name + ".cmd")
                    with open(exe, "w", encoding="utf-8") as f:
                        f.write('@"%s" "%s"\n' % (PY, script))
                else:
                    exe = os.path.join(d, name)
                    with open(exe, "w", encoding="utf-8") as f:
                        f.write('#!/bin/sh\nexec "%s" "%s"\n' % (PY, script))
                    os.chmod(exe, 0o755)
                return exe

            def drive(name, change):
                return subprocess.run(
                    [PY, os.path.join(TESTS, "crosscheck.py"), "compiled", "--kernel", "add_2_2",
                     "--format", "binary64", "--seed", "1", "--count", "1000",
                     "--summary", os.path.join(d, name + ".json"), "--fail-on-suspicious",
                     "--runner", name, runner(name, change)],
                    capture_output=True, text=True)
            good = drive("same", False)
            self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
            self.assertIn("with same: passed, ", good.stdout)
            bad = drive("changed", True)
            self.assertEqual(bad.returncode, 1, bad.stdout + bad.stderr)
            self.assertIn("kairn-oracle check: FAIL", bad.stdout)
            self.assertIn("1 invalid", bad.stdout)
            self.assertIn("requires normalized(x)", bad.stdout)
            self.assertIn("changed: oracle check 1", bad.stdout)

    # The same driver for the public interface: with the API runner, a pass, a stratum the cases
    # missed, and a kernel the runner maps no form to.
    def test_the_one_process_driver_of_the_public_interface(self):
        if not API_RUNNER:
            self.skipTest("needs the path of the API runner (tests/api/runner.cpp)")
        with tempfile.TemporaryDirectory() as d:
            def drive(kernel, count):
                return subprocess.run(
                    [PY, os.path.join(TESTS, "crosscheck.py"), "api", "--kernel", kernel,
                     "--format", "binary64", "--seed", "1", "--count", str(count),
                     "--summary-dir", d, "--runner", "build", API_RUNNER],
                    capture_output=True, text=True)
            good = drive("add_2_2", 1000)
            self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
            self.assertIn("forms of the public interface passed", good.stdout)
            bad = drive("add_2_2", 5)
            self.assertEqual(bad.returncode, 1, bad.stdout + bad.stderr)
            self.assertIn("no case of stratum", bad.stdout)
            self.assertIn("To rerun case INDEX of form F", bad.stdout)
            bad = drive("two_sum", 1000)
            self.assertEqual(bad.returncode, 1, bad.stdout + bad.stderr)
            self.assertIn("no public operation of the API runner build maps to two_sum", bad.stdout)

    # The driver of the interpreter's enumerations, crosscheck.cmake, passes the guards' verdict on.
    def test_the_driver(self):
        if not CMAKE:
            self.skipTest("needs the path of cmake")
        with tempfile.TemporaryDirectory() as d:
            def drive(kernel, fmt, restrict=""):
                return subprocess.run(
                    [CMAKE, "-DPYTHON=" + PY, "-DSOURCE_DIR=" + ROOT, "-DKERNEL=" + kernel,
                     "-DFORMAT=" + fmt, "-DRUNNER=interp", "-DEXHAUSTIVE=ON",
                     "-DRESTRICT=" + restrict,
                     "-DSUMMARY=" + os.path.join(d, kernel + ".json"), "-DFAIL_ON_SUSPICIOUS=ON",
                     "-P", os.path.join(TESTS, "crosscheck.cmake")],
                    capture_output=True, text=True)
            bad = drive("mul_2_2", "fp:3:-3:2")
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("judged no case", bad.stdout + bad.stderr)
            good = drive("two_sum", "fp:3:-3:2")
            self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
            self.assertIn("passed, ", good.stdout + good.stderr)
            # CMake wraps the lines of its messages.
            bad = drive(*ADD, restrict="x.lead=-3:-2,y.lead=-3:-2")
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("class F4", " ".join((bad.stdout + bad.stderr).split()))
            good = drive(*ADD)
            self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
            self.assertIn("extended domain: F2 finite", " ".join((good.stdout + good.stderr).split()))


if __name__ == "__main__":
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        CMAKE = sys.argv.pop(1)
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        API_RUNNER = sys.argv.pop(1)
    unittest.main()
