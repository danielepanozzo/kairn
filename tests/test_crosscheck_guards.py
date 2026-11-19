"""The cross-checks' guards must fail the runs they are there to fail (tests/crosscheck_guards.py).

    python3 tests/test_crosscheck_guards.py [CMAKE]

Each test runs a real pipeline, gen | kairn-gen interp | check --json, on a tiny toy format, whose
stream the oracle passes but which did not check what a cross-check sets out to check (a
partial or restricted enumeration, strata missing, nothing judged, a comparison seen one way
only), or alters the summary of a good run where no stream can produce the fault; and requires
the guards to fail it, with their reason. With CMAKE, the path of cmake, it also runs
crosscheck.cmake on such a run, which must fail with the guards' reason, and on a good one.
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
        s = pipeline("lt_2_2", "fp:3:-3:2", "--exhaustive", "--restrict", "x.sign=+",
                     "--restrict", "y.sign=-")
        self.fails(s, "lt_2_2", "fp:3:-3:2", "--exhaustive", "--restrict", "x.sign=+,y.sign=-",
                   reason="was never true")

    def test_a_directed_rounding_that_never_steps(self):
        s = copy.deepcopy(self.good_down)
        for k in s["keys"]:
            k["stats"]["entries"][0]["counts"].pop("inexact, != RN", None)
        self.fails(s, "to_down_2", "fp:4:-6:4", "--seed", "0", "--count", "200",
                   reason="never differed from the rounding to nearest")

    # The driver passes the guards' verdict on.
    def test_the_driver(self):
        if not CMAKE:
            self.skipTest("needs the path of cmake")
        with tempfile.TemporaryDirectory() as d:
            def drive(kernel, fmt):
                return subprocess.run(
                    [CMAKE, "-DPYTHON=" + PY, "-DSOURCE_DIR=" + ROOT, "-DKERNEL=" + kernel,
                     "-DFORMAT=" + fmt, "-DRUNNER=interp", "-DEXHAUSTIVE=ON",
                     "-DSUMMARY=" + os.path.join(d, kernel + ".json"), "-DFAIL_ON_SUSPICIOUS=ON",
                     "-P", os.path.join(TESTS, "crosscheck.cmake")],
                    capture_output=True, text=True)
            bad = drive("mul_2_2", "fp:3:-3:2")
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("judged no case", bad.stdout + bad.stderr)
            good = drive("two_sum", "fp:3:-3:2")
            self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
            self.assertIn("passed, ", good.stdout + good.stderr)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        CMAKE = sys.argv.pop(1)
    unittest.main()
