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

    def test_the_lengths_of_the_compiled_folds(self):
        # The random arrays of the compiled part: up to FOLD_LENGTH, but the products of
        # BallVectors up to PRODUCT_LENGTH, in the stream a unit asks of gen and in the length the
        # guards of collect hold it to (the same function).
        folds = brute.load_folds()
        products = {f["name"] for f in folds if f.get("bv_conv")}
        self.assertTrue(products)
        self.assertIn("bv_conv_1", products)
        for f in folds:
            want = brute.PRODUCT_LENGTH if f["name"] in products else brute.FOLD_LENGTH
            self.assertEqual(brute.fold_length(f["name"]), want, f["name"])
            unit = brute.Unit("/w", f["name"], "binary64", 0, 10, True, "scalar")
            args = brute.fold_stream_args(unit)
            self.assertEqual(args[args.index("--max-length") + 1], str(want), f["name"])
        self.assertEqual(brute.fold_length("conv_2"), brute.FOLD_LENGTH)
        self.assertLess(brute.PRODUCT_LENGTH, brute.FOLD_LENGTH)
        packed = brute.Unit("/w", "sum_2", "binary64", 0, 10, True, "avx2", "lanes:4")
        self.assertEqual(brute.fold_stream_args(packed),
                         ["--orders", "lanes:4", "--max-length", str(brute.FOLD_LENGTH)])

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
            if shape.startswith("kernel_"):
                self.assertEqual(brute.fold_shape(folds[shape[7:]]), shape, shape)
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


class EmulatedPlan(unittest.TestCase):
    """The emulated part (brute.py, "The plan of the emulated part"), with the sizes of the oracle's
    gen --total stood in for: one limb a few thousand, two limbs at precision 8 19 million, beyond
    it more than the threshold."""

    @classmethod
    def setUpClass(cls):
        cls.kernels = brute.load_claims()
        cls.folds = brute.load_folds()
        cls.limbs = {k["name"]: brute.input_limbs(k) for k in cls.kernels}
        cls.asked = []

        def total(e):
            cls.asked.append(e)
            p = brute.parse_fmt(e["format"])[0]
            return 5000 if cls.limbs[e["kernel"]] == 1 else 19_000_000 if p == 8 else 95_000_000
        with mock.patch.object(brute, "gen_total", total):
            cls.plan = brute.emulated_plan(cls.kernels, cls.folds)

    def test_every_kernel_and_fold_at_every_precision(self):
        want = {(k["name"], p) for k in self.kernels + self.folds for p in brute.EMULATED_PRECISIONS
                if (k.get("min_precision") or 1) <= p}
        got = {(e["kernel"], brute.parse_fmt(e["format"])[0]) for e in self.plan}
        self.assertEqual(got, want)
        self.assertEqual(len(got), len(self.plan))

    def test_formats_of_the_statements_that_the_runner_has(self):
        # Every format is one of the statements (qmax >= 1, qmin = 3 - qmax - 2p), qmax 1 but for the
        # bounds of two-limb folds, and one whose constants the emulated kernels have.
        with open(os.path.join(brute.REPO, "tests", "emulated", "gen", "kernels.hpp"), encoding="utf-8") as f:
            known = set(brute.re.findall(r'\{"(fp:[0-9:-]+)", ', f.read()))
        for e in self.plan:
            p, qmin, qmax = brute.parse_fmt(e["format"])
            self.assertEqual(qmax, brute.EMULATED_QMAX.get(e["kernel"], 1), e)
            self.assertEqual(qmin, 3 - qmax - 2 * p, e)
            self.assertIn(e["format"], known, e)

    def test_what_is_enumerated(self):
        # Every kernel of one limb at every precision, of two at precision 8, none of three or more,
        # and no fold; the sizes asked of the oracle for kernels of at most two limbs only.
        for e in self.plan:
            limbs = self.limbs.get(e["kernel"])
            p = brute.parse_fmt(e["format"])[0]
            exhaustive = limbs is not None and (limbs == 1 or (limbs == 2 and p == 8))
            self.assertEqual(e["mode"], "exhaustive" if exhaustive else "random", e)
            if e["mode"] == "random":
                self.assertEqual(e["total"], brute.EMULATED_FOLD_CASES if limbs is None else brute.EMULATED_CASES)
            self.assertEqual("maxlen" in e, limbs is None, e)
        self.assertTrue(all(self.limbs[e["kernel"]] <= 2 for e in self.asked))
        self.assertTrue(self.asked)

    def test_keys_and_commands(self):
        keys = [brute.emu_key(e) for e in self.plan]
        self.assertEqual(len(set(keys)), len(keys))
        e = next(x for x in self.plan if x["mode"] == "exhaustive")
        cmd = brute.emulated_gen(e, "s", 10, 5)
        self.assertIn("--exhaustive", cmd)
        self.assertNotIn("--seed", cmd)
        self.assertEqual(cmd[-4:], ["--start", "10", "--count", "5"])
        f = next(x for x in self.plan if "maxlen" in x)
        cmd = brute.emulated_gen(f, "s", 0, 5)
        self.assertEqual(cmd[cmd.index("--seed") + 1], "s")
        self.assertEqual(cmd[-2:], ["--max-length", str(brute.EMULATED_FOLD_LENGTH)])


class ReportEmulated(unittest.TestCase):
    """report prints the emulated part of a summary (collect's "emulated"): per precision and mode,
    and every entry, an incomplete one marked."""

    def test_tables(self):
        def entry(kernel, fmt, mode, covered, cases, judged, failed=0, complete=True):
            return {"kernel": kernel, "format": fmt, "mode": mode, "covered": covered,
                    "complete": complete, "guards": "ok" if complete else ["not run"],
                    "seconds": 12.4, "counts": {"cases": cases, "judged": judged,
                                                "failed": failed}}
        doc = {"name": "linux-x86-64-emulated", "emulated": {"entries": [
            entry("two_sum", "fp:8:-14:1", "exhaustive", 18931201, 18931201, 18000000),
            entry("next_up", "fp:9:-16:1", "exhaustive", 9730, 9730, 9730),
            entry("mul_2_2", "fp:9:-16:1", "random", 500000, 500000, 400000, complete=False),
            entry("sum_2", "fp:8:-14:1", "random", 20000, 20000, 15000)]}}
        out = []
        brute.report_emulated([doc, {"name": "none"}], out.append)
        text = "\n".join(out)
        self.assertIn("| 8 | every operand | 1 | 1 | 18 931 201 | 18 931 201 | 18 000 000 | 0 | 0 | 12 |",
                      text)
        self.assertIn("| 9 | random | 1 | 0 | 500 000 |", text)
        self.assertIn("| all | | 4 | 3 | 19 460 931 | 19 460 931 | 18 424 730 | 0 | 0 | 50 |", text)
        self.assertIn("| `mul_2_2` | `fp:9:-16:1` | random (**INCOMPLETE or guard failed**) |", text)
        self.assertIn("| `sum_2` | `fp:8:-14:1` | random | 20 000 | 20 000 | 15 000 | 0.75 | 0 | 12 |",
                      text)
        # Nothing for files without an emulated part.
        out = []
        brute.report_emulated([{"name": "x", "emulated": {"entries": []}}], out.append)
        self.assertEqual(out, [])


class ReportKinds(unittest.TestCase):
    """report on the entries of Milestone 2: an upper bound without gaps= (the radius of a ball
    vector, the bounds of the folds), the steps of a fold of maxima, a fold's error per order, the
    worst entry of a ball vector; the runners of a fold compared within their streams; the long
    lines of a fold shortened."""

    def test_headlines(self):
        h = brute.entry_headlines
        self.assertEqual(h({"kind": "upper", "label": "upper(r) gaps=3/2", "maxima": {}})[0][:2],
                         ("upper", "largest excess, gaps (claim 3/2)"))
        self.assertEqual(h({"kind": "upper", "label": "upper(r) over max, steps=0",
                            "maxima": {brute.STEPS_ABOVE: ["0", "l"]}})[0][3], brute.STEPS_ABOVE)
        self.assertEqual(h({"kind": "upper", "label": "V3, radius bv_add_radius_2: upper(rz) >= rx",
                            "minima": {brute.STATED_EXCESS: ["1.5", "l"]}})[0][0], "stated")
        self.assertEqual(h({"kind": "upper", "label": "upper(g) >= gamma", "maxima": {}}), [])
        fe = h({"kind": "fold_error", "label": "fold_error(r)", "maxima": {
            "error / allowed, order lanes": ["0.1", "l"], "error / allowed, order sequential": ["0.2", "l"]}})
        self.assertEqual([x[1] for x in fe], ["largest error / bound, order lanes",
                                              "largest error / bound, order sequential"])
        self.assertEqual(h({"kind": "encloses_entries", "label": "encloses_entries(z, r)",
                            "minima": {brute.SLACK_WORST: ["1.5", "l"]}})[0][0], "encloses")
        self.assertEqual(h({"kind": "certain", "label": "certain(m)"}), [])
        iv = h({"kind": "encloses_interval", "label": "encloses_interval(zl, zu) x+y", "maxima": {
            brute.TIGHT % "lower": ["0.6", "l"], brute.TIGHT % "upper": ["0.7", "l"]}})
        self.assertEqual([(x[0], x[3]) for x in iv], [("tight", brute.TIGHT % "lower"),
                                                      ("tight", brute.TIGHT % "upper")])
        self.assertEqual(h({"kind": "outward", "label": "outward(l) below",
                            "maxima": {brute.OUTWARD: ["0.6", "l"]}})[0][0], "tight")
        self.assertEqual(h({"kind": "makes_ball", "label": "makes_ball(c, r)",
                            "maxima": {brute.MIDPOINT: ["1", "l"]}})[0][0], "tight")
        self.assertEqual(h({"kind": "holds", "label": "holds le(m*unit(add_1_1), 1/2) if ok",
                            "maxima": {"m*unit(add_1_1) where ok true": ["0.25", "l"]}})[0][:2],
                         ("holds", "largest m*unit(add_1_1) where ok"))

    def test_fold_streams_are_compared_apart(self):
        # Scalar and packed runners of a fold judged different streams: no disagreement; two
        # scalar runners that differ are reported.
        fold = brute.load_folds()[0]["name"]
        head = [None, None]
        doc = {"name": "m", "runners": {"a/cxx": {"kind": "scalar", "backend": "scalar"},
                                        "b/cxx": {"kind": "scalar", "backend": "scalar"},
                                        "a/avx2": {"kind": "packed", "backend": "avx2"}},
               "compiled": {"kernels": {fold: {"binary64": {"runners": {
                   "a/cxx": [100, 100, 0, 0, 0, 0, head], "b/cxx": [100, 100, 0, 0, 0, 0, head],
                   "a/avx2": [100, 99, 0, 0, 1, 0, head]}}}}}}
        out = []
        brute.report_agreement([doc], out.append)
        self.assertIn("every runner gave the same counts", "\n".join(out))
        doc["compiled"]["kernels"][fold]["binary64"]["runners"]["b/cxx"][1] = 98
        out = []
        brute.report_agreement([doc], out.append)
        self.assertIn("disagree", "\n".join(out))

    def test_short_line(self):
        self.assertEqual(brute.short_line("a b #t:1 -> c"), "a b #t:1 -> c")
        long = "sum_2 binary64 seq 4096 " + " ".join(["0x1.fffffffffffffp+1023"] * 8192) + \
            " #one:7 -> " + " ".join(["0x1p+0"] * 3)
        s = brute.short_line(long)
        self.assertLess(len(s), brute.LINE_SHOWN)
        self.assertIn("#one:7 -> 0x1p+0 0x1p+0 0x1p+0", s)
        self.assertTrue(s.startswith("sum_2 binary64 seq 4096 0x1.f"))
        self.assertIn("more) #one:7", s)


class Lengths(unittest.TestCase):
    """lengths.py: a run's arrays of a fold, judged apart by the oracle's length class."""

    def test_split(self):
        import lengths
        lengths.CONV.update({"conv_2"})
        text = ("# kairn-oracle gen event=begin kernel=sum_2 format=binary64 mode=random seed=s\n"
                "sum_2 binary64 seq 0 #one:0 -> 0x0p+0 0x0p+0 1\n"
                "sum_2 binary64 lanes:2 2 0x1p+0 0x0p+0 0x1p+0 0x0p+0 #wide:1 -> 0x1p+1 0x0p+0 1\n"
                "sum_2 binary64 seq 40 #wide:2 -> 0x0p+0 0x0p+0 1\n"
                "# kairn-oracle gen event=end lines=3\n")
        head, groups = lengths.split(text)
        self.assertEqual(len(head), 1)
        self.assertEqual(sorted(groups), ["length 0", "length 18 to 64", "length 2"])
        self.assertEqual(lengths.length_of("conv_2 binary64 seq 9 3 #x:0"), "length 3")
        self.assertEqual(sorted(["length above 4096", "length 18 to 64", "length 3", "length 17"],
                                key=lengths.class_key),
                         ["length 3", "length 17", "length 18 to 64", "length above 4096"])

    def test_a_run_through_the_interpreter(self):
        # Random arrays of a toy format, the interpreter, every class judged with no problem; the
        # classes together are the arrays asked for.
        import json
        import tempfile
        import lengths
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "l.json")
            rc = lengths.main(["--runner", "interp", "--seed", "t", "--cases", "60",
                               "--folds", "sum_1", "--formats", "fp:5:-7:4", "--out", out,
                               "--jobs", "1"])
            with open(out, encoding="utf-8") as f:
                doc = json.load(f)
            res = doc["folds"]["sum_1"]["fp:5:-7:4"]
            text = lengths.table(doc)
        self.assertEqual(rc, 0)
        # The table: a row per statistic of the fold's error, per order, with the arrays judged.
        rows = [r for r in text.splitlines() if r.startswith("| `sum_1` | `fp:5:-7:4` |")]
        self.assertTrue(rows)
        self.assertTrue(all("largest error / bound" in r and r.endswith("| 60 |") for r in rows))
        self.assertEqual(lengths.class_range("length 18 to 64"), (18, 64))
        self.assertEqual(lengths.class_range("length 3"), (3, 3))
        self.assertEqual(sum(c["lines"] for c in res.values()), 60)
        self.assertTrue(all(c["problems"] == [] and c["counts"]["cases"] == c["lines"]
                            for c in res.values()))
        self.assertIn("length 0", res)


class Runners(unittest.TestCase):
    """Which targets of the build are runners of the library (brute.runner_target)."""

    def test_the_runners_and_their_suffixes(self):
        self.assertEqual(brute.runner_target("kairn-gen-runner"), (False, None))
        self.assertEqual(brute.runner_target("kairn-gen-runner-fp-contract"), (False, "fp-contract"))
        self.assertEqual(brute.runner_target("kairn-gen-packed-runner"), (True, None))
        self.assertEqual(brute.runner_target("kairn-gen-packed-runner-contract-off"), (True, "contract-off"))
        self.assertIsNone(brute.runner_target("kairn-api-runner"))
        self.assertIsNone(brute.runner_target("kairn-gen-runnerx"))

    def test_a_planted_fault_is_not_a_runner(self):
        # The packed runner of crosscheck.lanes.fault.*, built with a kernel that is wrong on
        # purpose: an enumeration that took it for the library failed every night.
        self.assertIsNone(brute.runner_target("kairn-gen-packed-runner-lane-fault"))
        self.assertIsNone(brute.runner_target("kairn-gen-runner-fault"))
        self.assertIsNone(brute.runner_target("kairn-gen-packed-runner-o1-fault"))
        self.assertIsNotNone(brute.runner_target("kairn-gen-packed-runner-default"))

    def test_the_runners_found_in_a_build(self):
        # discover() on a build directory with the files a build leaves: the runners of the
        # library with their labels and settings, and not the planted fault's.
        import stat
        import tempfile
        exe = ".exe" if brute.WINDOWS else ""
        with tempfile.TemporaryDirectory() as bdir:
            tests = os.path.join(bdir, "tests")
            os.makedirs(tests)
            for target in ("kairn-gen-runner", "kairn-gen-runner-contract-off", "kairn-gen-packed-runner",
                           "kairn-gen-packed-runner-contract-on", "kairn-gen-packed-runner-lane-fault"):
                path = os.path.join(tests, target + exe)
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write("")
                os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
            with open(os.path.join(bdir, "CMakeCache.txt"), "w", encoding="utf-8") as fh:
                fh.write("KAIRN_TESTS_NEON:BOOL=ON\n")
            found = brute.discover("clang", bdir)
        self.assertEqual(sorted(r["target"] for r in found),
                         ["kairn-gen-packed-runner", "kairn-gen-packed-runner-contract-on",
                          "kairn-gen-runner", "kairn-gen-runner-contract-off"])
        by = {r["target"]: r for r in found}
        self.assertEqual(by["kairn-gen-runner"]["setting"], "the build's flags")
        self.assertEqual(by["kairn-gen-runner"]["kind"], "scalar")
        self.assertEqual(by["kairn-gen-runner-contract-off"]["setting"], "contract-off")
        self.assertEqual(by["kairn-gen-packed-runner-contract-on"]["kind"], "packed")
        self.assertEqual(by["kairn-gen-packed-runner-contract-on"]["setting"], "contract-on")
        self.assertEqual(len({r["id"] for r in found}), 4)

    def test_every_runner_target_of_the_build_is_classified(self):
        # Every target tests/CMakeLists.txt names kairn-gen-...runner...: a runner of the library,
        # or a planted fault, whose name must then end in "fault" so that it is never run as one.
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "CMakeLists.txt"), encoding="utf-8") as fh:
            text = fh.read()
        import re
        names = set(re.findall(r"add_executable\((kairn-gen-[A-Za-z0-9_-]*runner[A-Za-z0-9_-]*)", text))
        self.assertIn("kairn-gen-packed-runner-lane-fault", names)
        planted = {n for n in names if brute.runner_target(n) is None}
        self.assertEqual(planted, {n for n in names if n.endswith("fault")})
        self.assertEqual(planted, {"kairn-gen-packed-runner-lane-fault"})


class Widen(unittest.TestCase):
    def test_non_finite_results_are_overflows(self):
        # A small format of the kernel the oracle's suspicious test does not apply to: every
        # infinite radius is that of a computation that exceeds the largest number.
        import widen
        cases, equal, nonfinite, wide, bad, masked = widen.compare("ball_mul_1", "fp:1:-2:3", 15)
        self.assertEqual((cases, wide, bad, masked), (8281, "fp:1:-2:18", [], 0))
        self.assertEqual(equal + nonfinite, cases)
        self.assertGreater(equal, 0)
        self.assertGreater(nonfinite, 0)

    def test_the_radius_of_an_accumulator_at_precision_2(self):
        # r = RN(s K + C), K = up((1+u)^8) = 6 = the largest number of fp:2:-1:1: every infinite
        # radius where the mask ok is true is an overflow; where ok is false the claim says
        # nothing of r, which is a NaN in some cases (0 times the infinite product of the count).
        import widen
        self.assertEqual(widen.conditional("acc_radius_1"), {0: 1})
        self.assertEqual(widen.conditional("ball_mul_1"), {})
        cases, equal, nonfinite, wide, bad, masked = widen.compare("acc_radius_1", "fp:2:-1:1", 13)
        self.assertEqual((cases, nonfinite, bad, masked), (3584, 478, [], 3072))
        self.assertEqual(equal + nonfinite, cases)
        for k in ("acc_radius_1", "acc_radius_2"):
            self.assertFalse(brute.fails_on_suspicious(k, "fp:2:-1:1"))
            self.assertTrue(brute.fails_on_suspicious(k, "fp:3:-2:0"))
            self.assertTrue(brute.fails_on_suspicious(k, "binary64"))


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
