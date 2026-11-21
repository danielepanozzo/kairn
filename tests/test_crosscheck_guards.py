"""The cross-checks' guards must fail the runs they are there to fail (tests/crosscheck_guards.py).

    python3 tests/test_crosscheck_guards.py [CMAKE [API_RUNNER]]

Each test runs a real pipeline, gen | kairn-gen interp | check --json, on a tiny toy format, whose
stream the oracle passes but which did not check what a cross-check sets out to check (a
partial or restricted enumeration, strata missing, nothing judged, a comparison seen one way
only; in the extended domain, a class of results never seen: no overflow, no non-finite operand,
finite_when never put to the test, a ball result or a constructor's outcome missing, the strata
of the layer missing; for rational_1 and rational_2, kairn::rational, which the interpreter does
not know, the oracle's reference runner in its place, and a stratum, an exact or inexact case,
den = 0 or a pair the naive way does not normalize missing), or alters the summary of a good run
where no stream can produce the fault; and requires the guards to fail it, with their reason. It
also runs the driver of the compiled runners' cross-checks, tests/crosscheck.py, with the
interpreter (and for rational_2 the reference runner) as its runner, on such runs, which it must
fail with the guards' reason, and on good ones, and with a runner that changes an operand, whose
invalid case must fail the run. With CMAKE, the path of cmake, it
runs crosscheck.cmake, the driver of the interpreter's enumerations, likewise; with API_RUNNER,
the public interface's runner (tests/api/runner.cpp), crosscheck.py api on a good run, on one
whose cases miss a stratum, and on a kernel the runner maps no form to.

The oracle reads gen/claims.json, or the claims file named by the environment variable
KAIRN_ORACLE_CLAIMS (which the full tier sets from the CMake variable of that name), passed to
every run of the oracle and of the drivers as --claims FILE (-DCLAIMS=FILE for crosscheck.cmake).
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
CLAIMS = os.environ.get("KAIRN_ORACLE_CLAIMS") or os.path.join(ROOT, "gen", "claims.json")
CLAIMS_ARGS = ["--claims", CLAIMS] if os.environ.get("KAIRN_ORACLE_CLAIMS") else []
# crosscheck.py MODE ...: its mode first, then --claims (both modes take it).
CLAIMS_DRIVER = [PY, os.path.join(TESTS, "crosscheck.py")]


def pipeline(kernel, fmt, *gen_args, fail_on_suspicious=True):
    """The oracle's summary of gen KERNEL FMT GEN_ARGS | interp | check, which must pass; for
    rational_1 and rational_2, which the interpreter does not know, the oracle's reference runner
    (refrun) in its place."""
    with tempfile.TemporaryDirectory() as d:
        js = os.path.join(d, "s.json")
        gen = subprocess.run([PY, os.path.join(ROOT, "oracle", "kairn-oracle"), "gen", kernel, fmt]
                             + list(gen_args) + CLAIMS_ARGS, capture_output=True, text=True,
                             cwd=ROOT)
        assert gen.returncode == 0, gen.stderr
        runner = ([PY, os.path.join(ROOT, "oracle", "kairn-oracle"), "refrun"]
                  if kernel.startswith("rational_") else
                  [PY, os.path.join(ROOT, "gen", "kairn-gen"), "interp"])
        run = subprocess.run(runner, input=gen.stdout, capture_output=True, text=True, cwd=ROOT)
        assert run.returncode == 0, run.stderr
        check = ([PY, os.path.join(ROOT, "oracle", "kairn-oracle"), "check", "--json", js]
                 + CLAIMS_ARGS)
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


# kairn::rational<X>(num, den), which the oracle judges for equality without claims, through its
# reference runner.
R2 = ("rational_2", "binary32", "--seed", "0", "--count", "400")
R1 = ("rational_1", "fp:4:-6:4", "--seed", "0", "--count", "200")


class RationalGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.good2 = pipeline(*R2)
        cls.good1 = pipeline(*R1)

    def passes(self, summary, kernel, fmt, *args):
        status, out = guards(summary, kernel, fmt, *args)
        self.assertEqual(status, 0, out)
        return out

    def fails(self, summary, kernel, fmt, *args, reason):
        status, out = guards(summary, kernel, fmt, *args)
        self.assertEqual(status, 1, out)
        self.assertIn(reason, out)

    def test_good_runs_pass(self):
        out = self.passes(self.good2, *R2)
        self.assertIn("400 cases judged (400 random cases, seed 0", out)
        self.assertIn("naive pair not normalized", out)
        self.passes(self.good1, *R1)

    def test_another_stream(self):
        for kernel, fmt in (("rational_1", "binary32"), ("rational_2", "binary64")):
            self.fails(self.good2, kernel, fmt, *R2[2:], reason="the stream is of rational_2")
        self.fails(self.good2, "rational_2", "binary32", "--seed", "1", "--count", "400",
                   reason="of seed 0, not cases 0 to 400 of seed 1")
        self.fails(self.good2, "rational_2", "binary32", "--exhaustive", reason="in mode random")

    def test_a_stratum_missing(self):
        s = pipeline("rational_2", "binary32", "--seed", "0", "--count", "5")
        self.fails(s, "rational_2", "binary32", "--seed", "0", "--count", "5",
                   reason="no case of stratum tail")
        s = pipeline("rational_2", "binary32", "--seed", "0", "--count", "100",
                     "--strata", "small,random,pow2,extreme,exact,tie1,tie2,tail")
        self.fails(s, "rational_2", "binary32", "--seed", "0", "--count", "100",
                   reason="without den0, which it writes for rational_2")
        s = copy.deepcopy(self.good2)
        for k in s["keys"]:
            if k["tag"] == "tail":
                k["stats"]["counts"]["judged"] = 0
        self.fails(s, *R2, reason="no case of stratum tail was judged")
        s = copy.deepcopy(self.good2)
        s["keys"][0]["tag"] = "elsewhere"
        self.fails(s, *R2, reason="lines tagged elsewhere")

    def test_no_renormalized_pair(self):
        s = copy.deepcopy(self.good2)
        for k in s["keys"]:
            k["stats"]["entries"][0]["counts"].pop("naive pair not normalized", None)
        self.fails(s, *R2, reason="the renormalization of the pair was not checked")
        # rational_1 has no pair: no such case is asked of it.
        counts = [k["stats"]["entries"][0]["counts"] for k in self.good1["keys"]]
        self.assertNotIn("naive pair not normalized", json.dumps(counts))

    def test_cases_missing(self):
        for name in ("exact", "inexact", "den = 0"):
            s = copy.deepcopy(self.good1)
            for k in s["keys"]:
                k["stats"]["entries"][0]["counts"].pop(name, None)
            self.fails(s, *R1, reason='no judged case "%s"' % name)

    def test_invalid_requests_and_other_lines(self):
        s = copy.deepcopy(self.good2)
        s["keys"][0]["stats"]["counts"]["invalid"] = 1
        self.fails(s, *R2, reason="the runner did not echo them")
        s = copy.deepcopy(self.good2)
        s["keys"].append(dict(copy.deepcopy(s["keys"][0]), kernel="add_2_2"))
        self.fails(s, *R2, reason="lines of other kernels or formats")

    # The driver of the compiled runners, crosscheck.py, as the tests api.rational.K.F run it, with
    # the oracle's reference runner as its runner.
    def test_the_one_process_driver(self):
        with tempfile.TemporaryDirectory() as d:
            def drive(*args):
                return subprocess.run(
                    CLAIMS_DRIVER + ["compiled"] + CLAIMS_ARGS + ["--kernel", "rational_2",
                     "--format", "binary32", "--summary", os.path.join(d, "r.json"),
                     "--fail-on-suspicious", "--refrun"] + list(args),
                    capture_output=True, text=True)
            good = drive("--seed", "0", "--count", "400")
            self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
            self.assertIn("with refrun: passed, 400 cases judged", good.stdout)
            self.assertTrue(os.path.exists(os.path.join(d, "r.refrun.json")))
            self.assertFalse(os.path.exists(os.path.join(d, "r.work")))
            bad = drive("--seed", "0", "--count", "5")
            self.assertEqual(bad.returncode, 1, bad.stdout + bad.stderr)
            self.assertIn("did not check what it set out to", bad.stdout)
            self.assertIn("no case of stratum", bad.stdout)
            self.assertTrue(os.path.isdir(os.path.join(d, "r.work")))


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

    # The constructors under the rule of 2026-11-20: each class of radius with a finite center
    # and with one that is not, -0 in a random run only (an enumeration has one zero).
    def test_constructors_without_a_class_of_radius(self):
        sys.path.insert(0, TESTS)
        import crosscheck_guards as CG
        for kernel in ("ball_make_1", "ball_make_2"):
            args = ("--seed", "0", "--count", "1200")
            good = pipeline(kernel, "fp:3:-3:0", *args)
            self.passes(good, kernel, "fp:3:-3:0", *args)
            names = CG.make_radius_needs(False)
            self.assertEqual(len(names), 14)
            for name in names:
                s = edited(good, 0, lambda e: e["counts"].pop(name, None))
                self.fails(s, kernel, "fp:3:-3:0", *args, reason='saw no case of "%s"' % name)
            ex = pipeline(kernel, "fp:2:-2:1", "--exhaustive")
            self.passes(ex, kernel, "fp:2:-2:1", "--exhaustive")
            self.assertEqual(len(CG.make_radius_needs(True)), 12)
            for name in CG.make_radius_needs(True):
                s = edited(ex, 0, lambda e: e["counts"].pop(name, None))
                self.fails(s, kernel, "fp:2:-2:1", "--exhaustive",
                           reason='saw no case of "%s"' % name)

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
                    CLAIMS_DRIVER + ["compiled"] + CLAIMS_ARGS + ["--kernel", kernel,
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
                    CLAIMS_DRIVER + ["compiled"] + CLAIMS_ARGS + ["--kernel", "add_2_2",
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
                    CLAIMS_DRIVER + ["api"] + CLAIMS_ARGS + ["--kernel", kernel,
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
                     "-DSUMMARY=" + os.path.join(d, kernel + ".json"), "-DFAIL_ON_SUSPICIOUS=ON"]
                    + ["-DCLAIMS=" + c for c in CLAIMS_ARGS[1:]]
                    + ["-P", os.path.join(TESTS, "crosscheck.cmake")],
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


# The kinds of Milestone 2 (architecture.md, "Claims of Milestone 2"), on fp:3:-3:0, of the shape of
# the IEEE-model statements: Omega = 7 = 0x1.cp+2, N = 1/2, P = 2^(2p-1) eta = 4.
M2 = "fp:3:-3:0"
M2_COMMON = "uniform,underflow,overflow,zero,pow2,extreme"


class Milestone2Guards(unittest.TestCase):
    def passes(self, summary, kernel, fmt, *args):
        status, out = guards(summary, kernel, fmt, *args)
        self.assertEqual(status, 0, out)
        return out

    def fails(self, summary, kernel, fmt, *args, reason):
        status, out = guards(summary, kernel, fmt, *args)
        self.assertEqual(status, 1, out)
        self.assertIn(reason, out)

    def test_good_runs_pass(self):
        for kernel in ("next_up", "add_down_1", "sub_up_1", "mul_down_1", "ball_mul_pow2_1",
                       "ball_mul_pow2_2_full"):
            s = pipeline(kernel, M2, "--exhaustive")
            out = self.passes(s, kernel, M2, "--exhaustive")
            self.assertIn("Milestone 2, ", out)
        s = pipeline("next_down", M2, "--seed", "0", "--count", "400")
        self.passes(s, "next_down", M2, "--seed", "0", "--count", "400")

    # neighbor: every row of the table, and the steps where the spacing changes.
    def test_neighbor_without_the_infinities(self):
        s = pipeline("next_up", M2, "--seed", "0", "--count", "200", "--strata",
                     M2_COMMON + ",special,binade,subnormal")
        self.fails(s, "next_up", M2, "--seed", "0", "--count", "200",
                   reason='saw no case of "row: -inf"')

    def test_neighbor_without_a_row_or_a_step(self):
        good = pipeline("next_down", M2, "--exhaustive")
        for name in ("row: eta", "row: -Omega",
                     "a step toward zero from a power of two above the smallest normal number",
                     "a step between the subnormal and the normal range"):
            s = copy.deepcopy(good)
            for k in s["keys"]:
                k["stats"]["entries"][0]["counts"].pop(name, None)
            self.fails(s, "next_down", M2, "--exhaustive", reason='saw no case of "%s"' % name)

    # rounded of two operands: exact and inexact, an overflow on each side, NaN and infinities.
    def test_directed_sum_without_an_overflow(self):
        # Operands in [1/2, 2): their sums stay below Omega = 7.
        s = pipeline("add_down_1", M2, "--exhaustive", "--restrict", "a.lead=-1:0",
                     "--restrict", "b.lead=-1:0")
        self.fails(s, "add_down_1", M2, "--exhaustive", "--restrict", "a.lead=-1:0,b.lead=-1:0",
                   reason='saw no case of "overflow: value above Omega"')

    def test_directed_sum_without_a_nan_operand(self):
        s = pipeline("sub_down_1", M2, "--seed", "0", "--count", "300", "--strata",
                     M2_COMMON + ",apart,cancel,exact,close,beyond,omega")
        self.fails(s, "sub_down_1", M2, "--seed", "0", "--count", "300",
                   reason='saw no case of "a NaN operand"')
        self.fails(s, "sub_down_1", M2, "--seed", "0", "--count", "300",
                   reason="without nonfinite")

    # rounded with when and bound: the condition both ways, results at the rounding and beyond.
    def test_directed_product_whose_condition_always_holds(self):
        # Factors of at least 2: every product of finite operands is at least P = 4.
        s = pipeline("mul_down_1", M2, "--exhaustive", "--restrict", "a.lead=1:2",
                     "--restrict", "b.lead=1:2")
        args = ("--exhaustive", "--restrict", "a.lead=1:2,b.lead=1:2")
        self.fails(s, "mul_down_1", M2, *args,
                   reason='saw no case of "product_large does not hold (nothing claimed)"')
        self.fails(s, "mul_down_1", M2, *args,
                   reason='saw no case of "one step beyond the directed rounding"')

    def test_directed_product_never_at_the_rounding(self):
        s = copy.deepcopy(pipeline("mul_up_1", M2, "--exhaustive"))
        for k in s["keys"]:
            k["stats"]["entries"][0]["counts"].pop("at the directed rounding", None)
            k["stats"]["entries"][1]["counts"].pop("product_large holds", None)
        self.fails(s, "mul_up_1", M2, "--exhaustive",
                   reason='saw no case of "at the directed rounding"')
        self.fails(s, "mul_up_1", M2, "--exhaustive",
                   reason='saw no case of "product_large holds"')

    # exact_when: the conditions hold, and each fails.
    def test_exact_when_whose_condition_never_fails(self):
        # Centers and powers of two of at least 1: |cx c| >= 1 > N; radius 0.
        args = ("--exhaustive", "--restrict", "cx.lead=0:2,c.lead=0:2,rx.in=0x0p+0")
        s = pipeline("ball_mul_pow2_1", M2, "--exhaustive", "--restrict", "cx.lead=0:2",
                     "--restrict", "c.lead=0:2", "--restrict", "rx.in=0x0p+0")
        self.fails(s, "ball_mul_pow2_1", M2, *args,
                   reason='saw no case of "exact_when fails: rx*c = 0 or |rx*c| > eta/(2*u)"')
        self.fails(s, "ball_mul_pow2_1", M2, *args,
                   reason='saw no case of "exact_when fails: cx*c = 0 or |cx*c| > eta/(2*u)"')

    def test_exact_when_that_never_holds(self):
        s = copy.deepcopy(pipeline("ball_mul_pow2_2_full", M2, "--exhaustive"))
        for k in s["keys"]:
            k["stats"]["entries"][0]["counts"].pop("exact_when holds", None)
        self.fails(s, "ball_mul_pow2_2_full", M2, "--exhaustive",
                   reason='saw no case of "exact_when holds"')

    # The strata of the families of Milestone 2, in a random run's header.
    def test_strata_of_the_families_not_promised(self):
        s = pipeline("mul_up_1", M2, "--seed", "0", "--count", "200", "--strata",
                     M2_COMMON + ",nonfinite,zeroinf,tiny,exactprod,beyond")
        self.fails(s, "mul_up_1", M2, "--seed", "0", "--count", "200",
                   reason="without aroundp, which its family dirprod has")


def edited(summary, j, f):
    """A copy of a summary whose entry j of every key is changed by f(entry)."""
    s = copy.deepcopy(summary)
    for k in s["keys"]:
        f(k["stats"]["entries"][j])
    return s


class FoldGuards(unittest.TestCase):
    """The folds' stage of Milestone 2: the folds (lengths, orders, flags, cancellation, the
    fraction of the bound reached, the term tau), the bound kernels (the classes of m*unit(K)
    against the limit, g close to its stated value), the finishes and the steps."""

    @classmethod
    def setUpClass(cls):
        cls.args = ("--seed", "0", "--count", "300", "--max-length", "64")
        cls.dot = pipeline("dot_2", "fp:5:-12:5", *cls.args)
        cls.sum = pipeline("sum_1", "fp:4:-6:1", *cls.args)
        cls.bound = pipeline("bound_dot_2", "binary64", "--seed", "0", "--count", "400")

    def passes(self, summary, kernel, fmt, *args):
        status, out = guards(summary, kernel, fmt, *args)
        self.assertEqual(status, 0, out)
        return out

    def fails(self, summary, kernel, fmt, *args, reason):
        status, out = guards(summary, kernel, fmt, *args)
        self.assertEqual(status, 1, out)
        self.assertIn(reason, out)

    def test_good_runs_pass(self):
        out = self.passes(self.dot, "dot_2", "fp:5:-12:5", *self.args)
        self.assertIn("fold: largest error/allowed", out)
        self.passes(self.sum, "sum_1", "fp:4:-6:1", *self.args)
        self.passes(self.bound, "bound_dot_2", "binary64", "--seed", "0", "--count", "400")
        s = pipeline("sum_2", "fp:3:-3:0", "--exhaustive", "--max-length", "2")
        self.passes(s, "sum_2", "fp:3:-3:0", "--exhaustive", "--max-length", "2")
        s = pipeline("fold_finish_2", "fp:3:-3:0", "--exhaustive")
        self.passes(s, "fold_finish_2", "fp:3:-3:0", "--exhaustive")

    def test_another_stream(self):
        self.fails(self.sum, "sum_1", "fp:4:-6:1", "--seed", "0", "--count", "300",
                   "--max-length", "65", reason="largest length is 64, not 65")
        self.fails(self.sum, "sum_1", "fp:4:-6:1", *self.args, "--orders", "seq",
                   reason="orders are seq,seq,lanes:0")
        self.fails(self.sum, "sum_1", "fp:4:-6:1", "--seed", "0", "--count", "300",
                   reason="largest length is 64, not 256")
        self.fails(self.sum, "sum_1", "fp:4:-6:1", "--exhaustive", "--max-length", "64",
                   reason="mode random")

    def test_a_length_or_an_order_missing(self):
        for name in ("length 0", "length 9", "length 17"):
            s = edited(self.sum, 0, lambda e: e["counts"].pop(name, None))
            self.fails(s, "sum_1", "fp:4:-6:1", *self.args,
                       reason="saw no judged array of length %s" % name.split()[1])
        s = edited(self.sum, 0, lambda e: [e["counts"].pop(c) for c in list(e["counts"])
                                           if c.startswith("length ") and " to " in c])
        self.fails(s, "sum_1", "fp:4:-6:1", *self.args, reason="random length above 17")
        for name in ("order: sequential", "order: lanes, W = 4",
                     "order: lanes, more lanes than elements (W > n >= 1)"):
            s = edited(self.sum, 0, lambda e: e["counts"].pop(name, None))
            self.fails(s, "sum_1", "fp:4:-6:1", *self.args, reason='no judged case of "%s"' % name)
        # A run of the lane order of a packed register only asks for that order.
        s = pipeline("sum_1", "fp:4:-6:1", *self.args, "--orders", "lanes:4")
        self.passes(s, "sum_1", "fp:4:-6:1", *self.args, "--orders", "lanes:4")

    def test_a_flag_outcome_missing(self):
        s = pipeline("sum_1", "fp:4:-6:1", *self.args, "--strata",
                     "one,wide,sign,cancel,zeros,underflow,tight,pow2")
        self.fails(s, "sum_1", "fp:4:-6:1", *self.args,
                   reason='saw no case "flag false: a non-finite element"')
        self.fails(s, "sum_1", "fp:4:-6:1", *self.args,
                   reason='saw no case "flag false: finite elements, near overflow"')
        self.fails(s, "sum_1", "fp:4:-6:1", *self.args, reason="without overflow")
        far = edited(self.sum, 1, lambda e: e["counts"].update(
            {"flag false: finite elements far from overflow": 1}))
        self.fails(far, "sum_1", "fp:4:-6:1", *self.args,
                   reason="false flags from finite elements far from overflow")

    def test_no_cancellation_or_a_bound_far_from_reached(self):
        s = edited(self.sum, 0, lambda e: e["counts"].pop(
            "heavy cancellation: |sum| <= u * sum of magnitudes", None))
        self.fails(s, "sum_1", "fp:4:-6:1", *self.args, reason='no judged case of "heavy cancellation')
        # A bound a thousand times too loose: the largest ratio a thousand times smaller.
        s = edited(self.dot, 1, lambda e: e.update(max_ratio=[e["max_ratio"][0], str(
            1000 * int(e["max_ratio"][1]))]))
        self.fails(s, "dot_2", "fp:5:-12:5", *self.args, reason="below 1/16: a bound far too loose")
        s = edited(self.sum, 0, lambda e: e.update(max_ratio=["1", "3"]))
        self.fails(s, "sum_1", "fp:4:-6:1", *self.args, reason="below 1/2")

    def test_a_ratio_beyond_the_floats(self):
        # As StageBGuards.test_a_ratio_beyond_the_floats, for a fold: the ratio is printed.
        s = edited(self.sum, 0, lambda e: e.update(max_ratio=[str(25 * 10 ** 399), "1"]))
        out = self.passes(s, "sum_1", "fp:4:-6:1", *self.args)
        self.assertIn("fold: largest error/allowed 2.5e+400", out)

    def test_an_enumeration_where_every_sum_is_exact(self):
        # Four binades: every sum of two pairs is a pair, so the run puts nothing of the bound to
        # the test.
        args = ("--exhaustive", "--max-length", "2")
        s = pipeline("sum_2", "fp:3:-2:-1", *args)
        self.fails(s, "sum_2", "fp:3:-2:-1", *args, reason="came to at most 0 of its bound")

    def test_a_dot_product_whose_tau_never_matters(self):
        for name in ("error above the relative term alone",
                     "absolute term larger than the relative term"):
            s = edited(self.dot, 1, lambda e: e["counts"].pop(name, None))
            self.fails(s, "dot_2", "fp:5:-12:5", *self.args, reason='no judged case of "%s"' % name)

    def test_bounds_on_one_side_of_the_limit(self):
        args = ("--seed", "0", "--count", "400")
        s = pipeline("bound_dot_2", "binary64", *args, "--strata", "uniform,underflow,overflow,zero,"
                     "pow2,extreme,integer,fraction")
        self.fails(s, "bound_dot_2", "binary64", *args, reason="without limit")
        for name in ("ok true, 1/5 < m*unit(mul_2_2) <= 1/4", "ok false, 1/4 < m*unit(mul_2_2) <= 1/2",
                     "ok true, m*unit(mul_2_2) = 0"):
            s = edited(self.bound, 1, lambda e: e["counts"].pop(name, None))
            self.fails(s, "bound_dot_2", "binary64", *args, reason='saw no case "%s"' % name)
        s = edited(self.bound, 1, lambda e: [e["counts"].pop(c, None) for c in (
            "ok false, 1/2 < m*unit(mul_2_2) < 1", "ok false, m*unit(mul_2_2) >= 1")])
        self.fails(s, "bound_dot_2", "binary64", *args, reason="no count beyond")
        s = edited(self.bound, 1, lambda e: e["counts"].update(
            {"ok false, 0 < m*unit(mul_2_2) <= 1/5": 3}))
        self.fails(s, "bound_dot_2", "binary64", *args, reason="is true for every m with")
        s = edited(self.bound, 1, lambda e: e["counts"].pop("m not an integer", None))
        self.fails(s, "bound_dot_2", "binary64", *args, reason="not an integer")
        # g never close to its stated value: a g twice as large would be.
        s = edited(self.bound, 1, lambda e: e["minima"].update(
            {"excess over a positive stated value, in gaps of the output": [["9", "1"], ""]}))
        self.fails(s, "bound_dot_2", "binary64", *args, reason="never came within 8 gaps")

    def test_a_bound_in_a_format_of_one_bit(self):
        # At p = 1 the mask is true at m = 0 only, where the stated value is zero: no case has a
        # positive stated value to come close to, and the enumeration passes on the mask both
        # ways (the brute-force driver plans this enumeration for every bound kernel of one
        # limb). A positive stated value that was met and missed by 9 gaps still fails there.
        for kernel in ("bound_dot_1", "bound_sum_1"):
            good = pipeline(kernel, "fp:1:-30:12", "--exhaustive")
            out = self.passes(good, kernel, "fp:1:-30:12", "--exhaustive")
            close = "excess over a positive stated value, in gaps of the output"
            self.assertFalse(any(close in e.get("minima", {}) for k in good["keys"]
                                 for e in k["stats"]["entries"]), out)
            j = next(i for i, e in enumerate(good["keys"][0]["stats"]["entries"])
                     if e["label"].startswith("upper(g)"))
            s = edited(good, j, lambda e: e.setdefault("minima", {}).update({close: [["9", "1"], ""]}))
            self.fails(s, kernel, "fp:1:-30:12", "--exhaustive", reason="never came within 8 gaps")

    def test_a_finish_without_a_state(self):
        good = pipeline("fold_finish_2", "fp:3:-3:0", "--exhaustive")
        for name in ("value: leading limb NaN", "value: finite leading limb, a lower limb not finite"):
            s = edited(good, 0, lambda e: e["counts"].pop(name, None))
            self.fails(s, "fold_finish_2", "fp:3:-3:0", "--exhaustive",
                       reason='saw no case of "%s"' % name)

    def test_strata_of_the_families_not_promised(self):
        args = ("--seed", "0", "--count", "200")
        s = pipeline("dot_step_1", "binary64", *args, "--strata",
                     "uniform,underflow,overflow,zero,pow2,extreme,cancel,state,zerostate,tie")
        self.fails(s, "dot_step_1", "binary64", *args, reason="without exactprod, which its family "
                   "dotstep has")
        s = pipeline("sum_2", "fp:4:-6:1", *self.args, "--strata",
                     "one,wide,sign,cancel,zeros,underflow,overflow,nonfinite,tight,pow2")
        self.fails(s, "sum_2", "fp:4:-6:1", *self.args, reason="without tail")

    def test_the_one_process_driver(self):
        with tempfile.TemporaryDirectory() as d:
            def drive(fold, fmt, *args):
                return subprocess.run(
                    CLAIMS_DRIVER + ["compiled"] + CLAIMS_ARGS + ["--kernel", fold,
                     "--format", fmt, "--summary", os.path.join(d, fold + ".json"),
                     "--fail-on-suspicious", "--interp", "--seed", "0"] + list(args),
                    capture_output=True, text=True)
            good = drive("dot_1", "fp:4:-6:1", "--count", "300", "--max-length", "64")
            self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
            self.assertIn("fold: largest error/allowed", good.stdout)
            bad = drive("dot_1", "fp:4:-6:1", "--count", "12", "--max-length", "64")
            self.assertEqual(bad.returncode, 1, bad.stdout + bad.stderr)
            self.assertIn("did not check what it set out to", bad.stdout)


IV = "fp:4:-6:1"


class IntervalGuards(unittest.TestCase):
    """The interval kernels: the classes of each statement (I1 to I6 and the kinds of the
    enclosure interface), results near the limit of bounded_when on each side, the fraction of
    the bounds of two limbs and of the midpoint reached, and the strata of their families."""

    @classmethod
    def setUpClass(cls):
        cls.args = ("--seed", "0", "--count", "500")
        cls.add1 = pipeline("interval_add_1", IV, *cls.args)
        cls.mul1 = pipeline("interval_mul_1", IV, *cls.args)
        cls.add2 = pipeline("interval_add_2", IV, *cls.args)
        cls.mul2 = pipeline("interval_mul_2", IV, *cls.args)
        cls.mid = pipeline("interval_mid_rad_1", IV, *cls.args)
        cls.down = pipeline("add_down_2_2", IV, *cls.args)

    def passes(self, summary, kernel, fmt, *args):
        status, out = guards(summary, kernel, fmt, *args)
        self.assertEqual(status, 0, out)
        return out

    def fails(self, summary, kernel, fmt, *args, reason):
        status, out = guards(summary, kernel, fmt, *args)
        self.assertEqual(status, 1, out)
        self.assertIn(reason, out)

    def test_good_runs_pass(self):
        for name, s in (("interval_add_1", self.add1), ("interval_mul_1", self.mul1),
                        ("interval_add_2", self.add2), ("interval_mul_2", self.mul2),
                        ("interval_mid_rad_1", self.mid), ("add_down_2_2", self.down)):
            self.passes(s, name, IV, *self.args)
        for name in ("mul_dir_1", "interval_make_1", "ball_lower_as_2", "interval_hull_2",
                     "interval_split_1", "mul_ext_2_2", "ball_from_interval_2", "ball_to_interval_1",
                     "interval_make_2"):
            s = pipeline(name, IV, *self.args)
            self.passes(s, name, IV, *self.args)
        s = pipeline("interval_neg_1", "fp:2:-2:1", "--exhaustive")
        self.passes(s, "interval_neg_1", "fp:2:-2:1", "--exhaustive")

    # The constructors under the rule of 2026-11-20 (a NaN bound or the same infinity twice gives
    # the whole line, reversed bounds the empty set): every cell of the table of architecture.md,
    # "The constructors on every pair of values", in a random run and in an enumeration; for two
    # limbs reversed bounds of equal leading limbs, and in a random run the same infinity with zeros
    # of opposite signs as second limbs. A run without the same infinity twice fails.
    def test_constructors_without_a_cell(self):
        sys.path.insert(0, TESTS)
        import crosscheck_guards as CG
        self.assertEqual(len(CG.IV_MAKE_CELLS), 17)
        for kernel, tiny in (("interval_make_1", "fp:2:-2:1"), ("interval_make_2", "fp:2:-2:1"),
                             ("ball_from_interval_2", "fp:2:-2:1")):
            with open(CLAIMS, encoding="utf-8") as f:
                k = next(k for k in json.load(f)["kernels"] if k["name"] == kernel)
            two = kernel == "interval_make_2"
            good = pipeline(kernel, IV, *self.args)
            names = CG.iv_make_needs(k, k["ensures"][0], False)
            self.assertEqual(len(names), 6 + 17 + (2 if two else 0))
            for name in names:
                s = edited(good, 0, lambda e: e["counts"].pop(name, None))
                self.fails(s, kernel, IV, *self.args, reason='saw no case of "%s"' % name)
            ex = pipeline(kernel, tiny, "--exhaustive")
            self.passes(ex, kernel, tiny, "--exhaustive")
            names = CG.iv_make_needs(k, k["ensures"][0], True)
            self.assertEqual(len(names), 6 + 17 + (1 if two else 0))
            for name in names:
                s = edited(ex, 0, lambda e: e["counts"].pop(name, None))
                self.fails(s, kernel, tiny, "--exhaustive", reason='saw no case of "%s"' % name)
            strata = M2_COMMON + ",nanbound,reversed,point" + (",oddeta,top" if "ball" in kernel
                                                                 else "")
            s = pipeline(kernel, IV, *self.args, "--strata", strata)
            for name in ("given: equal infinities", "given lo +inf, hi +inf",
                         "given lo -inf, hi -inf"):
                self.fails(s, kernel, IV, *self.args, reason='saw no case of "%s"' % name)

    # encloses_interval: every class of operands and results, I5 both ways and near its limit.
    def test_encloses_interval_without_an_empty_operand(self):
        s = pipeline("interval_add_1", IV, *self.args, "--strata",
                     M2_COMMON + ",point,threshold,cancel,zerosum")
        self.fails(s, "interval_add_1", IV, *self.args,
                   reason='saw no case of "operands: an empty operand"')
        self.fails(s, "interval_add_1", IV, *self.args, reason="without special")

    def test_bounded_when_that_never_fails(self):
        # Bounds of magnitude at most 1: every sum stays below Omega = 6.
        args = ("--exhaustive", "--restrict", "xl.lead=-2:-1,xu.lead=-2:-1,yl.lead=-2:-1,yu.lead=-2:-1")
        s = pipeline("interval_add_1", "fp:2:-2:1", "--exhaustive", "--restrict", "xl.lead=-2:-1",
                     "--restrict", "xu.lead=-2:-1", "--restrict", "yl.lead=-2:-1", "--restrict",
                     "yu.lead=-2:-1")
        self.fails(s, "interval_add_1", "fp:2:-2:1", *args,
                   reason='saw no case of "bounded operands, bounded_when fails"')
        self.fails(s, "interval_add_1", "fp:2:-2:1", *args,
                   reason="within a factor 2 below the limit")

    def test_never_near_the_limit(self):
        s = edited(self.add1, 0, lambda e: e["minima"].update(
            {"bounded_when fails: smallest max|member| / limit": [["3", "1"], ""]}))
        self.fails(s, "interval_add_1", IV, *self.args, reason="within a factor 2 above the limit")

    def test_rounded_without_a_step_or_a_condition(self):
        for name in ("lower: one step beyond the directed rounding",
                     "upper: product_large does not hold (within the steps)",
                     "lower: range bound not a number of the format"):
            s = edited(self.mul1, 0, lambda e: e["counts"].pop(name, None))
            self.fails(s, "interval_mul_1", IV, *self.args, reason='saw no case of "%s"' % name)

    def test_outward_far_from_its_bound(self):
        name = "lower: distance from the range bound / (rel*|bound| + abs)"
        s = edited(self.add2, 0, lambda e: e["maxima"].update(
            {name: [[e["maxima"][name][0][0], str(1000 * int(e["maxima"][name][0][1]))], ""]}))
        self.fails(s, "interval_add_2", IV, *self.args, reason="below 1/4")
        name = "|output - value| / (rel*|value| + abs)"
        s = edited(self.down, 1, lambda e: e["maxima"].update({name: [["1", "5"], ""]}))
        self.fails(s, "add_down_2_2", IV, *self.args, reason="below 1/4")

    def test_exact_when_that_never_holds_or_never_fails(self):
        s = edited(self.add2, 0, lambda e: e["counts"].pop("lower: exact_when holds", None))
        self.fails(s, "interval_add_2", IV, *self.args, reason='saw no case of "lower: exact_when '
                   'holds"')
        s = edited(self.add2, 0, lambda e: e["counts"].pop("upper: exact_when fails: xu+yu = 0",
                                                           None))
        self.fails(s, "interval_add_2", IV, *self.args, reason="exact_when fails: xu+yu = 0")
        s = edited(self.down, 1, lambda e: e["counts"].pop("exact_when holds", None))
        self.fails(s, "add_down_2_2", IV, *self.args, reason='saw no case of "exact_when holds"')

    def test_zero_factor_never_applied(self):
        s = edited(self.mul2, 0, lambda e: e["counts"].pop(
            "I6 applies: [0, 0] against an unbounded operand", None))
        self.fails(s, "interval_mul_2", IV, *self.args, reason="I6 applies")
        args = ("--seed", "0", "--count", "400")
        s = pipeline("mul_dir_1", IV, *args, "--strata", M2_COMMON + ",aroundp,tiny,exactprod,"
                     "beyond")
        self.fails(s, "mul_dir_1", IV, *args,
                   reason='saw no case of "zero_factor: a zero against an infinite operand"')

    def test_the_other_kinds_without_a_class(self):
        args = ("--seed", "0", "--count", "400")
        s = pipeline("interval_make_1", IV, *args, "--strata", M2_COMMON + ",reversed,infinities,"
                     "point")
        self.fails(s, "interval_make_1", IV, *args, reason='saw no case of "given: a NaN bound"')
        s = pipeline("ball_lower_as_1", IV, *args, "--strata", M2_COMMON + ",radii,cross,beyond,"
                     "exactend")
        self.fails(s, "ball_lower_as_1", IV, *args, reason='saw no case of "ball: empty"')
        s = pipeline("interval_intersection_1", IV, *args)
        s = edited(s, 0, lambda e: e["counts"].pop("nonempty operands, disjoint", None))
        self.fails(s, "interval_intersection_1", IV, *args, reason="disjoint")
        s = edited(self.mid, 0, lambda e: e["counts"].pop(
            "X: a bound an odd multiple of eta below 2N", None))
        self.fails(s, "interval_mid_rad_1", IV, *self.args, reason="odd multiple of eta")
        s = pipeline("interval_split_1", IV, *args)
        s = edited(s, 0, lambda e: e["counts"].pop("X: half-line [-inf, h]", None))
        self.fails(s, "interval_split_1", IV, *args, reason="half-line [-inf, h]")

    def test_every_class_is_asked_for(self):
        # For every kind of the interval kernels: each class the guards ask of an entry, taken out
        # of a good run's summary, fails the run, with that class as the reason.
        sys.path.insert(0, TESTS)
        import crosscheck_guards as CG
        runs = {"interval_add_1": self.add1, "interval_mul_1": self.mul1,
                "interval_add_2": self.add2, "interval_mul_2": self.mul2,
                "interval_mid_rad_1": self.mid, "add_down_2_2": self.down}
        for name in ("mul_ext_2_2", "interval_make_1", "ball_from_interval_2", "ball_lower_as_2",
                     "ball_to_interval_1", "interval_hull_1", "interval_split_1", "mul_dir_1",
                     "interval_neg_2", "interval_make_2"):
            runs[name] = pipeline(name, IV, *self.args)
        asked = 0
        for name, good in runs.items():
            with open(good["claims"], encoding="utf-8") as f:
                kernel = next(k for k in json.load(f)["kernels"] if k["name"] == name)
            for j, e in enumerate(kernel["ensures"]):
                for need in CG.iv_needs(kernel, e, None):
                    s = edited(good, j, lambda x: x["counts"].pop(need, None))
                    self.fails(s, name, IV, *self.args, reason='saw no case of "%s"' % need)
                    asked += 1
        self.assertGreater(asked, 100)

    def test_the_midpoint_far_from_its_bound(self):
        name = "|center - midpoint| / (rel*|midpoint| + abs)"
        s = edited(self.mid, 0, lambda e: e["maxima"].update({name: [["1", "3"], ""]}))
        self.fails(s, "interval_mid_rad_1", IV, *self.args, reason="below 1/2")

    def test_strata_of_the_families_not_promised(self):
        s = pipeline("interval_add_2", IV, *self.args, "--strata",
                     M2_COMMON + ",special,point,threshold,cancel")
        self.fails(s, "interval_add_2", IV, *self.args, reason="without zerosum, which its family "
                   "ivop has")
        s = pipeline("add_down_2_2", IV, *self.args, "--strata", M2_COMMON + ",cancel,zerosum,"
                     "close,apart")
        self.fails(s, "add_down_2_2", IV, *self.args, reason="without tiny")

    def test_the_one_process_driver(self):
        with tempfile.TemporaryDirectory() as d:
            def drive(kernel, *args):
                return subprocess.run(
                    CLAIMS_DRIVER + ["compiled"] + CLAIMS_ARGS + ["--kernel", kernel,
                     "--format", IV, "--summary", os.path.join(d, kernel + ".json"),
                     "--fail-on-suspicious", "--interp", "--seed", "0"] + list(args),
                    capture_output=True, text=True)
            good = drive("interval_sub_1", "--count", "500")
            self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
            bad = drive("interval_sub_1", "--count", "12")
            self.assertEqual(bad.returncode, 1, bad.stdout + bad.stderr)
            self.assertIn("did not check what it set out to", bad.stdout)


class StageBGuards(unittest.TestCase):
    """Stage B of Milestone 2: the maps (lengths, orders, the classes of the elements and of the
    flag, the step's entries and how close its error comes to its bound), the folds of maxima (where
    the largest is, the result at and one step above RU(V), the bound's top beyond Omega), the
    convolutions (lengths 0 and 1 on either side, unequal lengths, the classes of the coefficients,
    the fold's error), and the kernels: the steps of axpy (their strata, the fraction of their
    bound), the maximum and the finishes of the folds of maxima."""

    @classmethod
    def setUpClass(cls):
        cls.args = ("--seed", "0", "--count", "120", "--max-length", "24")
        cls.toy = "fp:5:-12:6"
        cls.map = pipeline("add_1", cls.toy, *cls.args)
        cls.map2 = pipeline("axpy_2_1", "binary64", *cls.args)
        cls.max = pipeline("norm_upper_2", cls.toy, *cls.args)
        cls.conv = pipeline("conv_1", cls.toy, "--seed", "0", "--count", "120", "--max-length", "12")
        cls.cargs = ("--seed", "0", "--count", "120", "--max-length", "12")
        cls.kargs = ("--seed", "0", "--count", "600")
        cls.axpy = pipeline("axpy_step_1", "binary64", *cls.kargs)
        cls.finish = pipeline("norm_finish_2", "binary64", *cls.kargs)
        cls.comb = pipeline("norm_combine", "binary64", *cls.kargs)

    def passes(self, summary, kernel, fmt, *args):
        status, out = guards(summary, kernel, fmt, *args)
        self.assertEqual(status, 0, out)
        return out

    def fails(self, summary, kernel, fmt, *args, reason):
        status, out = guards(summary, kernel, fmt, *args)
        self.assertEqual(status, 1, out)
        self.assertIn(reason, out)

    def test_good_runs_pass(self):
        out = self.passes(self.map, "add_1", self.toy, *self.args)
        self.assertIn("largest error/allowed", out)
        self.passes(self.map2, "axpy_2_1", "binary64", *self.args)
        self.passes(self.max, "norm_upper_2", self.toy, *self.args)
        self.passes(self.conv, "conv_1", self.toy, *self.cargs)
        self.passes(self.axpy, "axpy_step_1", "binary64", *self.kargs)
        self.passes(self.finish, "norm_finish_2", "binary64", *self.kargs)
        self.passes(self.comb, "norm_combine", "binary64", *self.kargs)
        for name, fmt, L in (("add_1", "fp:2:-1:0", "1"), ("norm_upper_2", "fp:2:-2:1", "1"),
                             ("conv_1", "fp:2:-1:0", "1")):
            e = pipeline(name, fmt, "--exhaustive", "--max-length", L)
            self.passes(e, name, fmt, "--exhaustive", "--max-length", L)

    def test_a_map_without_a_class_of_elements_or_of_the_flag(self):
        for name in ("element: finite operands, not finite (an overflow)",
                     "element: a non-finite operand", "length 5", "order: lanes, W = 3"):
            s = edited(self.map, 0, lambda e: e["counts"].pop(name, None))
            self.fails(s, "add_1", self.toy, *self.args, reason=name.split(":")[-1].strip()
                       if name.startswith("order") else name.replace("length ", "length "))
        for name in ("flag true", "flag false: a non-finite operand",
                     "flag false: finite operands, an overflow"):
            s = edited(self.map, 1, lambda e: e["counts"].pop(name, None))
            self.fails(s, "add_1", self.toy, *self.args, reason='saw no case "%s"' % name)
        s = pipeline("add_1", self.toy, *self.args, "--strata",
                     "one,wide,cancel,tie,exact,underflow,zeros,nonfinite,tight")
        self.fails(s, "add_1", self.toy, *self.args, reason="without overflow")

    def test_a_map_whose_step_is_far_from_its_bound(self):
        # The step's error entry is the summary's entry 3 (after the map's two and its rounded).
        s = edited(self.map, 3, lambda e: e.update(max_ratio=["1", "3"]))
        self.fails(s, "add_1", self.toy, *self.args, reason="below 1/2: a bound far too loose")
        s = edited(self.map2, 3, lambda e: e.update(max_ratio=["1", "17"]))
        self.fails(s, "axpy_2_1", "binary64", *self.args, reason="below 1/16")
        s = edited(self.map, 2, lambda e: e["counts"].pop("inexact", None) and
                   e["counts"].pop("tie", None))
        self.fails(s, "add_1", self.toy, *self.args, reason="saw only exact cases")
        # Entries that are not those of the step.
        s = copy.deepcopy(self.map)
        for k in s["keys"]:
            k["stats"]["entries"].pop()
        self.fails(s, "add_1", self.toy, *self.args, reason="are not those of the claims")

    def test_a_fold_of_maxima_without_its_classes(self):
        for name in ("the largest at another element", "result 1 step above RU(V)",
                     "result at RU(V)", "V not a number of the format",
                     "the largest attained more than once", "no element: V = 0"):
            s = edited(self.max, 0, lambda e: e["counts"].pop(name, None))
            self.fails(s, "norm_upper_2", self.toy, *self.args, reason='saw no case "%s"' % name)
        s = edited(self.max, 1, lambda e: e["counts"].pop(
            "flag false: finite elements, the bound's top beyond Omega", None))
        self.fails(s, "norm_upper_2", self.toy, *self.args, reason="the bound's top beyond Omega")
        s = pipeline("norm_upper_2", self.toy, *self.args, "--strata",
                     "one,wide,ties,position,zeros,underflow,nonfinite,tail")
        self.fails(s, "norm_upper_2", self.toy, *self.args, reason="without top")

    def test_a_convolution_without_its_lengths(self):
        for name in ("n_x = 0", "n_y = 1", "n_x != n_y", "coefficient: a non-finite term",
                     "coefficient: finite terms, not finite (an overflow)", "n_y above 2"):
            s = edited(self.conv, 0, lambda e: e["counts"].pop(name, None))
            self.fails(s, "conv_1", self.toy, *self.cargs, reason='saw no case "%s"' % name)
        s = edited(self.conv, 2, lambda e: e["counts"].pop("length 2", None))
        self.fails(s, "conv_1", self.toy, *self.cargs, reason="saw no coefficient of 2 terms")
        s = edited(self.conv, 2, lambda e: e["counts"].pop(
            "heavy cancellation: |sum| <= u * sum of magnitudes", None))
        self.fails(s, "conv_1", self.toy, *self.cargs, reason="heavy cancellation")
        s = edited(self.conv, 2, lambda e: e.update(max_ratio=["1", "3"]))
        self.fails(s, "conv_1", self.toy, *self.cargs, reason="below 1/2")
        self.fails(self.conv, "conv_1", self.toy, *self.cargs, "--orders", "seq,seq",
                   reason="orders are seq, not seq,seq")

    def test_the_kernels_of_stage_b(self):
        s = edited(self.axpy, 0, lambda e: e.update(max_ratio=["1", "3"]))
        self.fails(s, "axpy_step_1", "binary64", *self.kargs, reason="below 1/2")
        s = pipeline("axpy_step_1", "binary64", *self.kargs, "--strata",
                     "uniform,underflow,overflow,zero,pow2,extreme,cancel,state,tie,exactprod")
        self.fails(s, "axpy_step_1", "binary64", *self.kargs,
                   reason="without tight, which its family axpy has")
        for name in ("value finite, stepped up +inf", "mask false", "value: infinite"):
            s = edited(self.finish, 0, lambda e: e["counts"].pop(name, None))
            self.fails(s, "norm_finish_2", "binary64", *self.kargs, reason='"%s"' % name)
        for name in ("arguments equal", "second argument larger"):
            s = edited(self.comb, 0, lambda e: e["counts"].pop(name, None))
            self.fails(s, "norm_combine", "binary64", *self.kargs, reason='"%s"' % name)
        s = pipeline("norm_combine", "binary64", *self.kargs, "--strata",
                     "uniform,underflow,overflow,zero,pow2,extreme,equal,neighbor")
        self.fails(s, "norm_combine", "binary64", *self.kargs, reason="without negative")

    def test_the_size_of_a_summary(self):
        # What a summary keeps does not grow with the lines judged: the step's entries of a map
        # keep the line of the element of the step that attains a statistic, not the map's line,
        # and only the records of the profile; a summary above the bound fails whatever it holds.
        sys.path.insert(0, TESTS)
        import crosscheck_guards
        bound = crosscheck_guards.SUMMARY_BYTES
        self.passes(self.map2, "axpy_2_1", "binary64", *self.args)
        self.assertLess(len(json.dumps(self.map2)), bound // 16)
        cases = 0
        for k in self.map2["keys"]:
            for e in k["stats"]["entries"][2:]:
                kept = [e["max_ratio_case"], e["b_case"]]
                kept += [c for _, c in e["profile"].values()]
                kept += [c for _, c in list(e["maxima"].values()) + list(e["minima"].values())]
                for c in kept:
                    if c is not None:
                        cases += 1
                        self.assertIn(":element:", c)
                        self.assertLess(len(c.split(" ")), 16, c)
        self.assertGreater(cases, 0)
        s = copy.deepcopy(self.map2)
        s["padding"] = "x" * bound
        self.fails(s, "axpy_2_1", "binary64", *self.args,
                   reason="bytes, above the %d a summary may take" % bound)

    def test_a_ratio_beyond_the_floats(self):
        # What the guards print of a ratio beyond the range of a float, a planted fault's (which
        # the oracle fails, so that the drivers do not run the guards on it): the ratio itself.
        s = edited(self.map2, 3, lambda e: e.update(max_ratio=[str(25 * 10 ** 399), "1"]))
        out = self.passes(s, "axpy_2_1", "binary64", *self.args)
        self.assertIn("largest error/allowed 2.5e+400", out)

    def test_the_one_process_driver(self):
        with tempfile.TemporaryDirectory() as d:
            def drive(name, fmt, *args):
                return subprocess.run(
                    CLAIMS_DRIVER + ["compiled"] + CLAIMS_ARGS + ["--kernel", name,
                     "--format", fmt, "--summary", os.path.join(d, name + ".json"),
                     "--fail-on-suspicious", "--interp", "--seed", "0"] + list(args),
                    capture_output=True, text=True)
            good = drive("scale_1", self.toy, "--count", "120", "--max-length", "24")
            self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
            self.assertIn("largest error/allowed", good.stdout)
            bad = drive("scale_1", self.toy, "--count", "12", "--max-length", "24")
            self.assertEqual(bad.returncode, 1, bad.stdout + bad.stderr)
            self.assertIn("did not check what it set out to", bad.stdout)


# The kernels of the ball vectors and of the accumulator (crosscheck_guards.py, bv_problems):
# random runs of the interpreter on toy formats of tests/CMakeLists.txt.
BV_ARGS = ("--seed", "0", "--count", "400")


class BallVectorKernelGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = {}
        for kernel, fmt in (("bv_mul_pow2_radius", "fp:4:-4:2"), ("bv_add_radius_2", "fp:3:-5:3"),
                            ("bv_mul_pow2_step_1", "fp:7:-14:6"), ("bv_conv_finish", "fp:10:-27:9"),
                            ("bv_make_finish", "fp:11:-29:10"), ("acc_add_2", "fp:3:-2:0"),
                            ("acc_radius_1", "fp:3:-2:0"), ("neg_1", "fp:11:-30:10"),
                            ("conv_radius", "fp:3:-4:4")):
            cls.runs[kernel] = (pipeline(kernel, fmt, *BV_ARGS), fmt)

    def passes(self, summary, kernel, fmt, *args):
        status, out = guards(summary, kernel, fmt, *args)
        self.assertEqual(status, 0, out)
        return out

    def fails(self, summary, kernel, fmt, *args, reason):
        status, out = guards(summary, kernel, fmt, *args)
        self.assertEqual(status, 1, out)
        self.assertIn(reason, out)

    def without(self, kernel, entry, name):
        """The good run of KERNEL with the count NAME of entry ENTRY taken out."""
        s, fmt = self.runs[kernel]
        s = copy.deepcopy(s)
        for k in s["keys"]:
            k["stats"]["entries"][entry]["counts"].pop(name, None)
        return s, fmt

    def test_good_runs_pass(self):
        for kernel, (s, fmt) in self.runs.items():
            self.passes(s, kernel, fmt, *BV_ARGS)

    # A copy or a negation is exact on every operand: no inexact case is asked of it.
    def test_identity_rounded_exact_only(self):
        s, fmt = self.runs["neg_1"]
        counts = {}
        for k in s["keys"]:
            for name, n in k["stats"]["entries"][0]["counts"].items():
                counts[name] = counts.get(name, 0) + n
        self.assertEqual(set(counts), {"exact"})
        self.passes(s, "neg_1", fmt, *BV_ARGS)

    def test_radius_without_a_class(self):
        for entry, name in ((0, "exact_when holds"), (0, "exact_when fails: ex true"),
                            (0, "exact_when fails: rx*c = 0 or |rx*c| > eta/(2*u)"),
                            (1, "ex true: nothing claimed"), (0, "output +inf"),
                            (1, "output finite, at least the stated value")):
            s, fmt = self.without("bv_mul_pow2_radius", entry, name)
            self.fails(s, "bv_mul_pow2_radius", fmt, *BV_ARGS, reason='saw no case of "%s"' % name)

    # conv_radius's claim is of finite results (the ruling of 2026-11-21): +inf and a NaN pass and
    # are counted, and the finite results must be at least three quarters of those judged.
    def test_conv_radius_finite_results_the_great_majority(self):
        import crosscheck_guards as CG
        s, fmt = self.runs["conv_radius"]
        counts = {}
        for k in s["keys"]:
            for name, n in k["stats"]["entries"][0]["counts"].items():
                counts[name] = counts.get(name, 0) + n
        nonfinite = counts.get(CG.BV_UP_NONFINITE, 0)
        finite = counts.get(CG.BV_UP_FINITE, 0)
        self.assertGreater(nonfinite, 0, counts)
        self.assertGreater(counts.get("output a NaN", 0), 0, counts)
        self.assertGreaterEqual(4 * finite, 3 * (finite + nonfinite), counts)
        self.passes(s, "conv_radius", fmt, *BV_ARGS)
        # The same run with most of its finite results taken away, then with one too few.
        for keep in (finite // 4, 3 * nonfinite - 1):
            bad = copy.deepcopy(s)
            left = keep
            for k in bad["keys"]:
                c = k["stats"]["entries"][0]["counts"]
                if CG.BV_UP_FINITE in c:
                    c[CG.BV_UP_FINITE] = min(c[CG.BV_UP_FINITE], left)
                    left -= c[CG.BV_UP_FINITE]
                    if not c[CG.BV_UP_FINITE]:
                        del c[CG.BV_UP_FINITE]
            self.fails(bad, "conv_radius", fmt, *BV_ARGS, reason="is of finite results")
        # At exactly three quarters it passes.
        ok = copy.deepcopy(s)
        left = 3 * nonfinite
        for k in ok["keys"]:
            c = k["stats"]["entries"][0]["counts"]
            if CG.BV_UP_FINITE in c:
                c[CG.BV_UP_FINITE] = min(c[CG.BV_UP_FINITE], left)
                left -= c[CG.BV_UP_FINITE]
                if not c[CG.BV_UP_FINITE]:
                    del c[CG.BV_UP_FINITE]
        self.passes(ok, "conv_radius", fmt, *BV_ARGS)

    def test_radius_without_a_stratum(self):
        for stratum in ("atnormal", "huge", "zeros", "mixed"):
            s, fmt = self.runs["bv_add_radius_2"]
            s = copy.deepcopy(s)
            d = s["coverage"][0]["desc"]
            d["strata"] = ",".join(x for x in d["strata"].split(",") if x != stratum)
            s["keys"] = [k for k in s["keys"] if k["tag"] != stratum]
            self.fails(s, "bv_add_radius_2", fmt, *BV_ARGS, reason="without %s" % stratum)

    def test_step_without_a_false_mask(self):
        s, fmt = self.without("bv_mul_pow2_step_1", 1, "exact_flag false")
        self.fails(s, "bv_mul_pow2_step_1", fmt, *BV_ARGS, reason='saw no case of "exact_flag false"')

    def test_finish_without_a_cell(self):
        for kernel, name in (("bv_conv_finish", "a mask false: okg"), ("bv_conv_finish", "value: NaN"),
                             ("bv_conv_finish", "value: -inf"), ("bv_conv_finish", "value zero"),
                             ("bv_make_finish", "value finite, below zero"),
                             ("bv_make_finish", "a mask false: ok")):
            s, fmt = self.without(kernel, 0, name)
            self.fails(s, kernel, fmt, *BV_ARGS, reason='saw no case of "%s"' % name)

    def test_accumulator_without_a_class(self):
        for entry, name in ((2, "inexact"), (2, "exact"),
                            (2, "the leading limb of its output is not finite: nothing claimed")):
            s, fmt = self.without("acc_add_2", entry, name)
            self.fails(s, "acc_add_2", fmt, *BV_ARGS, reason='saw no case of "%s"' % name)
        s, fmt = self.without("acc_radius_1", 0, "ok false: nothing claimed")
        self.fails(s, "acc_radius_1", fmt, *BV_ARGS, reason='saw no case of "ok false: nothing claimed"')
        s, fmt = self.without("acc_radius_1", 1, "holds")
        self.fails(s, "acc_radius_1", fmt, *BV_ARGS, reason='saw no case of "holds"')


class BallVectorFoldGuards(unittest.TestCase):
    """The folds of the ball vectors: both results, an operand that is the whole space, V4 applying
    (with no entry too, and the format's scope and finite_from said where it does not), the
    conditions of exactness each failing and all holding, every class of a radius given of a
    constructor, the lengths 0 and 1 on each side of a product and count_when failing in a toy
    format, the strata of the shape, a stream in place and its arrays."""

    @classmethod
    def setUpClass(cls):
        cls.args = ("--seed", "0", "--count", "300", "--max-length", "24")
        cls.cargs = ("--seed", "0", "--count", "200", "--max-length", "64")
        cls.iargs = cls.args + ("--inplace",)
        cls.add = pipeline("bv_add_2", "fp:4:-7:2", *cls.args)
        cls.add_in = pipeline("bv_add_2", "fp:4:-7:2", *cls.iargs)
        cls.pow2 = pipeline("bv_mul_pow2_1", "binary64", *cls.args)
        cls.make = pipeline("bv_make_2", "binary64", *cls.args)
        cls.conv = pipeline("bv_conv_2", "fp:5:-12:5", *cls.cargs)
        cls.narrow = pipeline("bv_scale_1", "fp:4:-4:-1", *cls.args)

    def passes(self, summary, kernel, fmt, *args):
        status, out = guards(summary, kernel, fmt, *args)
        self.assertEqual(status, 0, out)
        return out

    def fails(self, summary, kernel, fmt, *args, reason):
        status, out = guards(summary, kernel, fmt, *args)
        self.assertEqual(status, 1, out)
        self.assertIn(reason, out)

    def test_good_runs_pass(self):
        out = self.passes(self.add, "bv_add_2", "fp:4:-7:2", *self.args)
        self.assertIn("ball vector: ", out)
        self.passes(self.add_in, "bv_add_2", "fp:4:-7:2", *self.iargs)
        self.passes(self.pow2, "bv_mul_pow2_1", "binary64", *self.args)
        self.passes(self.make, "bv_make_2", "binary64", *self.args)
        self.passes(self.conv, "bv_conv_2", "fp:5:-12:5", *self.cargs)
        self.passes(self.narrow, "bv_scale_1", "fp:4:-4:-1", *self.args)
        for name, fmt, L in (("bv_neg_1", "fp:2:-2:1", "2"), ("bv_make_1", "fp:2:-2:1", "1"),
                             ("bv_add_1", "fp:2:-1:0", "1")):
            e = pipeline(name, fmt, "--exhaustive", "--max-length", L)
            self.passes(e, name, fmt, "--exhaustive", "--max-length", L)

    def test_a_ball_vector_without_a_class(self):
        for name in ("result: whole space", "result: finite ball vector",
                     "operands: a whole-space operand", "V4 applies", "V4 applies, no entry",
                     "length 0", "order: lanes, W = 3"):
            s = edited(self.add, 0, lambda e: e["counts"].pop(name, None))
            self.fails(s, "bv_add_2", "fp:4:-7:2", *self.args,
                       reason=name.split(": ", 1)[1] if name.startswith("order") else
                       "length 0" if name == "length 0" else 'saw no case "%s"' % name)

    def test_exactness_without_a_condition(self):
        for name in ("exact: every condition holds",
                     "exact_when fails: rx*c = 0 or |rx*c| > eta/(2*u)",
                     "exact_when fails: x*c = 0 or |x*c| > eta/(2*u)"):
            s = edited(self.pow2, 0, lambda e: e["counts"].pop(name, None))
            self.fails(s, "bv_mul_pow2_1", "binary64", *self.args, reason='saw no case "%s"' % name)

    def test_a_constructor_without_a_radius(self):
        for name in ("given radius negative, centers finite", "given radius NaN, centers finite",
                     "given radius -0, centers finite", "given radius -inf, centers finite",
                     "given radius positive, centers not all finite"):
            s = edited(self.make, 0, lambda e: e["counts"].pop(name, None))
            self.fails(s, "bv_make_2", "binary64", *self.args, reason='saw no case "%s"' % name)

    def test_a_product_without_a_class(self):
        # The condition on the count as the claims judged against write it (restated on
        # 2026-11-21: n*(unit(mul_2_2)+eta/(2*u)) <= 1/16, which was n*(unit(mul_2_2)+eta)).
        with open(CLAIMS, encoding="utf-8") as f:
            fold = [x for x in json.load(f)["folds"] if x["name"] == "bv_conv_2"][0]
        cw = fold["ensures"][0]["count_when"]
        self.assertEqual(len(cw), 1, cw)
        for name in ("n_x = 0", "n_y = 1", "n_x != n_y",
                     "V3: the radius at least conv_radius's stated value",
                     "count_when fails: %s <= %s" % (cw[0]["le"], cw[0]["than"]), "V4 applies"):
            s = edited(self.conv, 0, lambda e: e["counts"].pop(name, None))
            self.fails(s, "bv_conv_2", "fp:5:-12:5", *self.cargs, reason='saw no case "%s"' % name)

    def test_v4_outside_its_formats_or_below_finite_from(self):
        name = "V4 not claimed: a format of no statement (e_max <= p, or eta above binary_float's)"
        s = edited(self.narrow, 0, lambda e: e["counts"].pop(name, None))
        self.fails(s, "bv_scale_1", "fp:4:-4:-1", *self.args, reason='saw no case "%s"' % name)
        # Below finite_from (precision 1, where the interpreter refuses bv_add_1's constants): the
        # summary of a run at precision 2 read as one of precision 1 must show the count.
        s = pipeline("bv_add_1", "fp:2:-2:1", *self.args)
        self.passes(s, "bv_add_1", "fp:2:-2:1", *self.args)
        for k in s["keys"]:
            k["stats"]["p"] = 1
        self.fails(s, "bv_add_1", "fp:2:-2:1", *self.args, reason="below finite_from")

    def test_in_place(self):
        s = edited(self.add_in, 0, lambda e: e["counts"].pop("in place: array 1", None))
        self.fails(s, "bv_add_2", "fp:4:-7:2", *self.iargs, reason='saw no case "in place: array 1"')
        self.fails(self.add, "bv_add_2", "fp:4:-7:2", *self.iargs,
                   reason="the stream is not in place, though --inplace was asked")
        self.fails(self.add_in, "bv_add_2", "fp:4:-7:2", *self.args,
                   reason="the stream is in place, though --inplace was not asked")

    def test_strata_of_the_shape_not_promised(self):
        s = pipeline("bv_add_2", "fp:4:-7:2", *self.args, "--strata",
                     "one,wide,zeroradius,whole,overflow,threshold,cancel,underflow,tail")
        self.fails(s, "bv_add_2", "fp:4:-7:2", *self.args, reason="without zeros")
        s = pipeline("bv_mul_pow2_1", "binary64", *self.args, "--strata",
                     "one,wide,zeroradius,whole,overflow,threshold,cancel,underflow,zeros")
        self.fails(s, "bv_mul_pow2_1", "binary64", *self.args, reason="without exact")


class MapInPlaceGuards(unittest.TestCase):
    """A map's stream in place: every array of the limbs of the array written seen in place, and
    the stream in place exactly when --inplace was asked."""

    @classmethod
    def setUpClass(cls):
        cls.args = ("--seed", "0", "--count", "120", "--max-length", "24")
        cls.iargs = cls.args + ("--inplace",)
        cls.map = pipeline("add_1", "fp:5:-12:6", *cls.iargs)

    def test_in_place(self):
        status, out = guards(self.map, "add_1", "fp:5:-12:6", *self.iargs)
        self.assertEqual(status, 0, out)
        s = edited(self.map, 0, lambda e: e["counts"].pop("in place: array 0", None))
        status, out = guards(s, "add_1", "fp:5:-12:6", *self.iargs)
        self.assertEqual(status, 1, out)
        self.assertIn("saw no request in place of array 0", out)
        status, out = guards(self.map, "add_1", "fp:5:-12:6", *self.args)
        self.assertEqual(status, 1, out)
        self.assertIn("the stream is in place, though --inplace was not asked", out)


class LaneReports(unittest.TestCase):
    """crosscheck.py's reading of a packed runner's report of its lanes (--packed-kernels): a run
    passes only with one segment of every request, the assignment asked for, and for the permuted
    one the guard passed (gen/tests/packed_runner.cpp; docs/developer/testing.md, "Packed
    kernels"). The runner's own guard, and these reports as it writes them, are tested by the
    generator's tests (gen/tests/test_simd.py, Lanes) and by tests/lanes/lane_fault.py."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, TESTS)
        import crosscheck
        cls.cc = crosscheck

    def report(self, d, **changes):
        segment = {"kernel": "mul_2_2_full", "format": "binary64", "first_line": 2, "requests": 6000,
                   "lanes": 2, "registers": 3000, "padding": 0, "padding_line": None,
                   "padding_finite": True, "with_nonfinite": 1200, "with_finite": 4800, "mixed": 942,
                   "mixed_strata": 2703, "guard": "passed",
                   "kinds": [{"stratum": "close", "nonfinite": False, "requests": 900, "lanes": [450, 450]},
                             {"stratum": "nonfinite", "nonfinite": True, "requests": 600, "lanes": [300, 300]}]}
        r = {"runner": "packed", "assignment": "permuted", "seed": 0,
             "guard": {"applied": True, "lines": 256, "cases": 16}, "segments": [segment]}
        for key, value in changes.items():
            if key in ("assignment", "seed", "segments"):
                r[key] = value
            else:
                segment[key] = value
        path = os.path.join(d, "r.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(r, f)
        return path

    def check(self, d, asked="permuted", **changes):
        return self.cc.check_lanes(self.report(d, **changes), asked, "mul_2_2_full", "binary64", 6000)

    def test_a_good_report(self):
        with tempfile.TemporaryDirectory() as d:
            why, line = self.check(d)
            self.assertEqual(why, "")
            self.assertIn("942 of them mixing a non-finite limb with finite ones", line)
            self.assertIn("each of at least 2 requests in every lane", line)
            why, line = self.check(d, "consecutive", assignment="consecutive", mixed=0,
                                   guard="not applied: the consecutive assignment",
                                   kinds=[{"stratum": "uniform", "nonfinite": False, "requests": 300,
                                           "lanes": [0, 300]}])
            self.assertEqual(why, "")
            self.assertIn("1 of at least 2 requests missing from a lane", line)
            # A stream too short for the guard is not a failure of the permuted assignment.
            why, _ = self.check(d, guard="not applied: fewer than 256 requests")
            self.assertEqual(why, "")

    def test_reports_that_fail(self):
        with tempfile.TemporaryDirectory() as d:
            for changes, words in (({"assignment": "consecutive"}, "consecutive assignment, not permuted"),
                                   ({"segments": []}, "0 segments"),
                                   ({"requests": 5999}, "5999 requests"),
                                   ({"kernel": "mul_2_2"}, "of mul_2_2 binary64"),
                                   ({"guard": "failed: no register held"}, "guard: failed")):
                why, _ = self.check(d, **changes)
                self.assertIn(words, why, changes)
            why, _ = self.cc.check_lanes(os.path.join(d, "none.json"), "permuted", "mul_2_2_full",
                                         "binary64", 6000)
            self.assertIn("no report of its lanes", why)
            with open(os.path.join(d, "bad.json"), "w") as f:
                f.write("{")
            why, _ = self.cc.check_lanes(os.path.join(d, "bad.json"), "permuted", "mul_2_2_full",
                                         "binary64", 6000)
            self.assertIn("no report of its lanes", why)

    def test_runs_and_options(self):
        class A:
            seed = "0"
            packed_kernels = [["neon", "/p", "permuted,consecutive"], ["neon-x", "/q", "permuted"]]
        runs = self.cc.packed_kernel_runs(A, "/w")
        self.assertEqual([r[0] for r in runs], ["neon", "neon.consecutive", "neon-x"])
        self.assertEqual(runs[1][1][:5], ["/p", "--lanes", "consecutive", "--lane-seed", "0"])
        self.assertEqual(self.cc.lane_seed("12"), "12")
        self.assertEqual(self.cc.lane_seed(None), "0")
        self.assertTrue(self.cc.lane_seed("a seed").isdigit())
        self.assertEqual(self.cc.lane_seed("a seed"), self.cc.lane_seed("a seed"))
        with tempfile.TemporaryDirectory() as d:
            for assignments in ("sideways", "permuted,permuted", ""):
                r = subprocess.run([PY, os.path.join(TESTS, "crosscheck.py"), "compiled", "--kernel",
                                    "two_sum", "--format", "binary64", "--seed", "0", "--count", "10",
                                    "--summary", os.path.join(d, "s.json"), "--packed-kernels", "p",
                                    "/p", assignments], capture_output=True, text=True)
                self.assertEqual(r.returncode, 2, assignments)
                self.assertIn("ASSIGNMENTS is permuted, consecutive or both", r.stderr)


class LaneFaultVerdicts(unittest.TestCase):
    """tests/lanes/lane_fault.py takes the oracle's verdict on an output from the summary of its
    check, and tells it from a refusal of the claims: the check exits with 1 in both cases, and a
    refusal is an error of the test, never the failure the planted fault must cause."""

    def test_a_refusal_is_not_a_verdict(self):
        sys.path.insert(0, os.path.join(TESTS, "lanes"))
        import lane_fault as LF
        oracle = [PY, os.path.join(ROOT, "oracle", "kairn-oracle")]
        with tempfile.TemporaryDirectory() as d:
            gen = subprocess.run(oracle + ["gen", "mul_2_2_full", "binary64", "--seed", "0",
                                           "--count", "200"] + CLAIMS_ARGS,
                                 capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(gen.returncode, 0, gen.stderr)
            done = subprocess.run([PY, os.path.join(ROOT, "gen", "kairn-gen"), "interp"],
                                  input=gen.stdout, capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(done.returncode, 0, done.stderr)
            good = done.stdout
            # A wrong output: one result's first limb negated.
            lines = good.splitlines(True)
            j = next(i for i, ln in enumerate(lines) if " -> 0x1" in ln)
            head, _, tail = lines[j].partition(" -> ")
            lines[j] = head + " -> -" + tail
            wrong = "".join(lines)
            # Claims the oracle refuses: an entry of another kernel of an unknown kind.
            with open(CLAIMS, encoding="utf-8") as f:
                claims = json.load(f)
            k = next(k for k in claims["kernels"] if k["name"] == "two_sum")
            k["ensures"][0]["kind"] = "not_a_kind"
            refused = os.path.join(d, "claims-refused.json")
            with open(refused, "w", encoding="utf-8") as f:
                json.dump(claims, f)

            def check(name, claims_args, output):
                js = os.path.join(d, name + ".json")
                r = subprocess.run(oracle + ["check", "--quiet", "--json", js] + claims_args,
                                   input=output, capture_output=True, text=True, cwd=ROOT)
                return r.returncode, LF.oracle_outcome(js)

            self.assertEqual(check("pass", CLAIMS_ARGS, good), (0, ("passed", 0)))
            self.assertEqual(check("verdict", CLAIMS_ARGS, wrong), (1, ("failed", 1)))
            for name, output in (("refused", good), ("refused-wrong", wrong)):
                status, outcome = check(name, ["--claims", refused], output)
                self.assertEqual(status, 1, name)
                self.assertEqual(outcome[0], "refused", name)
                self.assertIn("two_sum", outcome[1][0])
                self.assertIn("the oracle refused the claims", LF.refusal(outcome))
            self.assertIsNone(LF.refusal(("failed", 1)))
            self.assertEqual(LF.oracle_outcome(os.path.join(d, "none.json"))[0], "unread")


class EnclosureGuards(unittest.TestCase):
    """The enclosure interface of stage B2: the predicates and comparisons of an interval and a ball
    (the relation both ways, every answer, every class of each set and point, the special states,
    exact_when both ways), the set operations of a ball (every pair of states, the operands as they
    are, the finite operands placed every way, in a random run the zeros of different signs), the
    split, the conversions of two limbs (finite_when both ways and an infinite radius, exact_when
    of each side, bounded_when both ways, the center of the ball from an interval), the fractions of
    their bounds, and the strata of their families."""

    KERNELS = ("interval_less_2", "interval_contains_1", "interval_rel_interior_1",
               "interval_empty_2", "ball_less_1", "ball_contains_point_2", "ball_contains_ball_2",
               "ball_positive_1", "ball_hull_1", "ball_intersection_2", "ball_split_2",
               "interval_mid_rad_2", "interval_to_ball_2", "interval_split_2",
               "ball_to_interval_2", "ball_from_interval_1")

    @classmethod
    def setUpClass(cls):
        # The quick tier's count of these kernels (KAIRN_CROSSCHECK_INTERVAL_QUICK_CASES): with 600
        # the table of the constructors of ball_from_interval_1 misses a cell in this format.
        cls.args = ("--seed", "0", "--count", "2000")
        cls.runs = {k: pipeline(k, IV, *cls.args) for k in cls.KERNELS}

    def passes(self, summary, kernel, fmt, *args):
        status, out = guards(summary, kernel, fmt, *args)
        self.assertEqual(status, 0, out)
        return out

    def fails(self, summary, kernel, fmt, *args, reason):
        status, out = guards(summary, kernel, fmt, *args)
        self.assertEqual(status, 1, out)
        self.assertIn(reason, out)

    def test_good_runs_pass(self):
        for k, s in self.runs.items():
            self.passes(s, k, IV, *self.args)
        for k, fmt in (("interval_less_1", "fp:2:-2:1"), ("ball_hull_1", "fp:2:-2:1"),
                       ("ball_from_interval_1", "fp:2:-2:1")):
            s = pipeline(k, fmt, "--exhaustive")
            self.passes(s, k, fmt, "--exhaustive")

    def test_every_class_is_asked_for(self):
        # Each class the guards ask of an entry, taken out of a good run's summary, fails the run,
        # with that class as the reason.
        sys.path.insert(0, TESTS)
        import crosscheck_guards as CG
        asked = 0
        for name, good in self.runs.items():
            with open(good["claims"], encoding="utf-8") as f:
                kernel = next(k for k in json.load(f)["kernels"] if k["name"] == name)
            for j, e in enumerate(kernel["ensures"]):
                for need in CG.enc_needs(kernel, e, None) + CG.iv_needs(kernel, e, None):
                    s = edited(good, j, lambda x: x["counts"].pop(need, None))
                    self.fails(s, name, IV, *self.args, reason='saw no case of "%s"' % need)
                    asked += 1
        self.assertGreater(asked, 200)

    def test_zero_signs_asked_of_a_random_run_only(self):
        # An enumeration has one zero: no whole lines of zeros of different signs there.
        s = pipeline("ball_hull_1", "fp:2:-2:1", "--exhaustive")
        self.passes(s, "ball_hull_1", "fp:2:-2:1", "--exhaustive")
        name = "both the whole line, centers zeros of different signs in the line"
        s = edited(self.runs["ball_hull_1"], 0, lambda e: e["counts"].pop(name, None))
        self.fails(s, "ball_hull_1", IV, *self.args, reason=name)

    def test_strata_of_the_families_not_promised(self):
        for k, strata, missing in (
                ("ball_less_1", M2_COMMON + ",ballstates,boundary,near,huge,points", "wide"),
                ("interval_less_2", M2_COMMON + ",special,nearzero,touch,equal,nested,disjoint",
                 "tails"),
                ("ball_hull_1", M2_COMMON + ",ballstates,disjoint,touch,nested,overlap,wide,point",
                 "bothspecial"),
                ("interval_mid_rad_2", M2_COMMON + ",special,point,step,oddeta,top,beyond",
                 "threshold"),
                ("ball_to_interval_2", M2_COMMON + ",ballstates,radii,cross,beyond,exactend,"
                 "threshold", "zeroend")):
            s = pipeline(k, IV, *self.args, "--strata", strata)
            self.fails(s, k, IV, *self.args, reason="without %s, which its family" % missing)

    def test_an_answer_not_given_far_from_the_boundary(self):
        # The band of the answers not given held to architecture.md's 2e + 4G: an answer left five
        # units of 2e + G from the boundary fails the run; one of three units passes.
        sys.path.insert(0, TESTS)
        import crosscheck_guards as CG
        for k in ("ball_contains_ball_2", "ball_contains_point_2"):
            good = self.runs[k]
            s = edited(good, 0, lambda e: e["maxima"].update({CG.ENC_BAND_UNITS: [["5", "1"], ""]}))
            self.fails(s, k, IV, *self.args, reason="beyond the 4 of architecture.md's band")
            s = edited(good, 0, lambda e: e["maxima"].update({CG.ENC_BAND_UNITS: [["3", "1"], ""]}))
            self.passes(s, k, IV, *self.args)

    def test_the_bounds_far_from_reached(self):
        name = "lower: distance from the range bound / (rel*|bound| + abs)"
        s = edited(self.runs["ball_to_interval_2"], 0, lambda e: e["maxima"].update(
            {name: [["1", "5"], ""]}))
        self.fails(s, "ball_to_interval_2", IV, *self.args, reason="below 1/4")
        name = "|center - midpoint| / (rel*|midpoint| + abs)"
        s = edited(self.runs["ball_from_interval_1"], 0, lambda e: e["maxima"].update(
            {name: [["1", "5"], ""]}))
        self.fails(s, "ball_from_interval_1", IV, *self.args, reason="below 1/4")
        # The center of two limbs has no floor (its bound is not claimed tight).
        s = edited(self.runs["interval_mid_rad_2"], 0, lambda e: e["maxima"].update(
            {name: [["1", "100"], ""]}))
        self.passes(s, "interval_mid_rad_2", IV, *self.args)

    def test_the_one_process_driver(self):
        with tempfile.TemporaryDirectory() as d:
            def drive(kernel, *args):
                return subprocess.run(
                    CLAIMS_DRIVER + ["compiled"] + CLAIMS_ARGS
                    + ["--kernel", kernel, "--format", IV, "--summary",
                       os.path.join(d, kernel + ".json"), "--fail-on-suspicious", "--interp",
                       "--seed", "0"] + list(args),
                    capture_output=True, text=True)
            good = drive("ball_intersection_1", "--count", "600")
            self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
            bad = drive("ball_intersection_1", "--count", "12")
            self.assertEqual(bad.returncode, 1, bad.stdout + bad.stderr)
            self.assertIn("did not check what it set out to", bad.stdout)


if __name__ == "__main__":
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        CMAKE = sys.argv.pop(1)
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        API_RUNNER = sys.argv.pop(1)
    unittest.main()
