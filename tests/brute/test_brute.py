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


class FixupForms(unittest.TestCase):
    def test_default_form(self):
        with mock.patch.object(brute.platform, "machine", return_value="arm64"):
            self.assertEqual(brute.default_fixup_call("AppleClang 21.0.0"), 1)
            self.assertEqual(brute.default_fixup_call("GNU 16.2.0"), 0)
        with mock.patch.object(brute.platform, "machine", return_value="x86_64"):
            self.assertEqual(brute.default_fixup_call("Clang 18.1.3"), 0)
            self.assertEqual(brute.default_fixup_call("MSVC 19.52"), 0)

    def test_flags_keep_the_form(self):
        cmd = "/usr/bin/g++ -DKAIRN_GEN_FIXUP_CALL=1 -O3 -I/home/x/include -o a.o -c b.cpp"
        self.assertEqual(brute.build_flags(cmd), "-DKAIRN_GEN_FIXUP_CALL=1 -O3")


if __name__ == "__main__":
    unittest.main()
