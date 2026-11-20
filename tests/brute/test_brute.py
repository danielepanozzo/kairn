#!/usr/bin/env python3
"""The driver's own tests: the plan of the enumerations and the forms of the fix-ups. Python 3
standard library only; a few seconds (no enumeration is sized or run).

    python3 tests/brute/test_brute.py
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brute  # noqa: E402


class Plan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kernels = brute.load_claims()
        cls.plan, cls.errors = brute.interp_plan(cls.kernels)

    def test_every_kernel_is_planned(self):
        self.assertEqual(self.errors, [])
        self.assertEqual({e["kernel"] for e in self.plan}, {k["name"] for k in self.kernels})

    def test_every_fold_is_planned(self):
        # Every fold of the claims, in the formats of its arrays, each enumeration up to a length
        # (gen --max-length), at or above the fold's min_precision.
        folds = brute.load_folds()
        plan, errors = brute.fold_plan(folds)
        self.assertEqual(errors, [])
        self.assertEqual({e["kernel"] for e in plan}, {f["name"] for f in folds})
        mp = {f["name"]: f.get("min_precision") or 1 for f in folds}
        for e in plan:
            self.assertGreaterEqual(brute.parse_fmt(e["format"])[0], mp[e["kernel"]], e)
            self.assertIn("--max-length", brute.gen_extra(e))
            self.assertTrue(brute.enum_key(e).endswith("__L%d" % e["maxlen"]))

    def test_the_shapes_of_folds(self):
        # The maps, the convolutions and the folds of maxima have shapes of their own, those of
        # tests/CMakeLists.txt (_fold_toy_SHAPE), and the first format of each is the full tier's.
        folds = {f["name"]: f for f in brute.load_folds()}
        want = {"add_1": "map_1_1", "sub_2_entry": "map_2_2", "axpy_1": "map_s1_1_1",
                "axpy_2": "map_s2_2_2", "axpy_2_1_entry": "map_s1_2_2", "scale_1": "map_s1_1",
                "scale_2": "map_s1_2", "mul_pow2_map_1": "map_sc_1", "mul_pow2_map_2": "map_sc_2",
                "norm_upper_1": "max_1", "norm_upper_2": "max_2", "conv_1": "conv_1_1",
                "conv_2": "conv_2_2", "sum_2": "2", "dot_1": "1_1"}
        for name, shape in want.items():
            if name in folds:
                self.assertEqual(brute.fold_shape(folds[name]), shape, name)
        with open(os.path.join(brute.REPO, "tests", "CMakeLists.txt"), encoding="utf-8") as f:
            cm = f.read()
        for shape, formats in brute.FOLD_SHAPES.items():
            m = brute.re.search(r"^set\(_fold_toy_%s (\S+) (\d+) " % shape, cm, brute.re.M)
            self.assertIsNotNone(m, shape)
            self.assertEqual((m.group(1), int(m.group(2))), formats[0], shape)

    def test_the_interpreter_accepts_every_format(self):
        # Every constant of every kernel (the splitter, the constants of the Ball radii) is a
        # number of each format the plan gives it.
        for e in self.plan:
            self.assertIsNone(brute.refusal(e["kernel"], e["format"]), e)

    def test_a_refused_format_is_replaced(self):
        # The splitter 17 of precision 7 is above 127/64, the largest number of fp:7:-20:-6.
        self.assertIn("splitter", brute.refusal("two_prod_dekker", "fp:7:-20:-6"))
        self.assertIsNone(brute.refusal("two_prod", "fp:7:-20:-6"))
        mine = [e for e in self.plan if e["kernel"] == "two_prod_dekker"]
        self.assertNotIn("fp:7:-20:-6", [e["format"] for e in mine])
        moved = [e for e in mine if e["format"] == "fp:7:-16:-2"]
        self.assertEqual(len(moved), 1)
        self.assertIn("replaces fp:7:-20:-6", moved[0]["why"])
        # The same precision and number of exponents, moved up; in the extended domain, two
        # exponents more at a time in the shape qmin + qmax = 3 - 2p.
        self.assertEqual(brute.fitting_format("two_prod_dekker", "fp:7:-20:-6", False),
                         "fp:7:-16:-2")
        self.assertEqual(brute.fitting_format("two_prod_dekker", "fp:7:-6:-5", True),
                         "fp:7:-9:-2")

    def test_precision_one_is_planned(self):
        # The oracle reads formats of precision 1: a kernel whose claims hold from precision 1
        # gets an enumeration of precision 1, then 2 and 3.
        for k in self.kernels:
            if k.get("min_precision") == 1:
                ps = {brute.parse_fmt(e["format"])[0] for e in self.plan if e["kernel"] == k["name"]}
                self.assertTrue({1, 2, 3} <= ps, (k["name"], ps))

    def test_precision_one_of_the_one_limb_balls(self):
        # Their own exponent range at precision 1 (PRECISION_ONE), and the product alone is not
        # failed there on a suspicious non-finite result (RADIUS_OVERFLOW).
        fmt = {e["kernel"]: e["format"] for e in self.plan if brute.parse_fmt(e["format"])[0] == 1}
        self.assertEqual(fmt["ball_add_1"], "fp:1:-5:5")
        self.assertEqual(fmt["ball_sub_1"], "fp:1:-5:5")
        self.assertEqual(fmt["ball_mul_1"], "fp:1:-6:5")
        self.assertFalse(brute.fails_on_suspicious("ball_mul_1", "fp:1:-6:5"))
        self.assertTrue(brute.fails_on_suspicious("ball_mul_1", "fp:2:-4:1"))
        self.assertTrue(brute.fails_on_suspicious("ball_mul_1", "binary64"))
        self.assertTrue(brute.fails_on_suspicious("ball_add_1", "fp:1:-5:5"))
        self.assertFalse(brute.fails_on_suspicious("split", "binary32"))
        self.assertFalse(brute.fails_on_suspicious("two_prod_dekker", "fp:7:-16:-2"))

    def test_extended_formats_have_the_ieee_shape(self):
        for e in self.plan:
            if e["domain"] == "extended":
                p, qmin, qmax = brute.parse_fmt(e["format"])
                self.assertEqual(qmin + qmax, 3 - 2 * p, e)

    def test_every_ball_kernel_with_a_claim_of_containment_has_a_complete_enumeration(self):
        balls = {k["name"] for k in self.kernels if any(x["kind"] == "encloses"
                                                         for x in k.get("ensures", []))}
        complete = {e["kernel"] for e in self.plan if not e["restrict"]}
        self.assertEqual(balls - complete, set())


class Widen(unittest.TestCase):
    def test_non_finite_results_are_overflows(self):
        # A small format of the kernel the oracle's suspicious test does not apply to: every
        # infinite radius is that of a computation that exceeds the largest number.
        import widen
        cases, equal, nonfinite, wide, bad = widen.compare("ball_mul_1", "fp:1:-2:3", 15)
        self.assertEqual((cases, wide, bad), (8281, "fp:1:-2:18", []))
        self.assertEqual(equal + nonfinite, cases)
        self.assertGreater(equal, 0)
        self.assertGreater(nonfinite, 0)


class FixupForms(unittest.TestCase):
    def test_default_form(self):
        with mock.patch.object(brute.platform, "machine", return_value="arm64"):
            self.assertEqual(brute.default_fixup_call("AppleClang 21.0.0"), 1)
            self.assertEqual(brute.default_fixup_call("GNU 16.2.0"), 0)
        with mock.patch.object(brute.platform, "machine", return_value="x86_64"):
            self.assertEqual(brute.default_fixup_call("Clang 18.1.3"), 0)
            self.assertEqual(brute.default_fixup_call("MSVC 19.52"), 0)

    def test_flags_keep_the_form(self):
        cmd = "/usr/bin/g++ -DKAIRN_GEN_FIXUP_CALL=1 -O3 -I/opt/src/include -o a.o -c b.cpp"
        self.assertEqual(brute.build_flags(cmd), "-DKAIRN_GEN_FIXUP_CALL=1 -O3")


if __name__ == "__main__":
    unittest.main()
