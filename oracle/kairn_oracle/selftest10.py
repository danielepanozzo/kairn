"""The oracle's own tests for the ball vectors and the accumulator (architecture.md, "Ball vectors",
"The accumulator", "Claims of Milestone 2"): the kernels of the radii (upper with a value of its
own and no if, with unless, with exact_when and mask( ), at_most), the steps of the scalings
(exact_flag), the copies and constructors, the finishes (finite_or_nan with nonneg, if_all), the
accumulator (rounded with a value of its own, the radius under its mask).

As for the earlier waves, each test compares the oracle with something it does not share code
with: the reference runner (refbv.py, written from the listings of gen/kernels/) on random streams
and on every operand of tiny formats; planted faults that must be caught in the entry where they
belong and nowhere else; hand-written lines whose verdicts are worked out by hand.  The fixture,
oracle/selftest/claims-wave8.json, holds the kernels and folds of the family and the kernels and
folds they name, frozen from the claims of 2026-11-21 (the joined tree of 5247eff), with the
count_when of bv_conv_2 as it was restated after it, n*(unit(mul_2_2)+eta/(2*u)) <= 1/16 (it
was n*(unit(mul_2_2)+eta) <= 1/16).
"""

import copy
import json
import os

from . import check as C
from . import fmt as F
from . import gen as G
from . import gen8 as G8
from . import refbv
from . import refrun
from .claims import Claims
from .selftest import test, expect, judge, totals, ORACLE_DIR
from .selftest7 import entry_stats

FIXTURE8 = os.path.join(ORACLE_DIR, "selftest", "claims-wave8.json")
RADII = ("bv_add_radius_1", "bv_add_radius_2", "bv_scale_radius_1", "bv_scale_radius_2",
         "bv_mul_pow2_radius", "conv_radius")
STEPS8 = ("bv_mul_pow2_step_1", "bv_mul_pow2_step_2")
COPIES = ("bv_center_entry_1", "bv_center_2", "neg_1", "bv_neg_radius", "bv_make_radius")
FINISHES = ("bv_make_finish", "bv_conv_finish")
ACC = ("acc_add_1", "acc_add_2", "acc_mul_1", "acc_mul_2", "acc_merge_1", "acc_merge_2")
ACC_RADII = ("acc_radius_1", "acc_radius_2")
KERNELS8 = RADII + STEPS8 + COPIES + FINISHES + ACC + ACC_RADII
# A toy format with exponents enough for every constant of the radii (precision 5 is at least
# every minimum precision but bv_conv_k's).
TOY8 = "fp:5:-12:6"


def raw8():
    with open(FIXTURE8, encoding="utf-8") as fh:
        return json.load(fh)


def claims8(ctx):
    """The fixture's claims (the kernels, and the folds that the oracle reads)."""
    if not hasattr(ctx, "claims8"):
        ctx.claims8 = Claims(raw8(), FIXTURE8)
    return ctx.claims8


def run8(lines, variant="correct"):
    r = refrun.Runner(variant, bound_claims=FIXTURE8, bv_claims=FIXTURE8)
    out = []
    for ln in lines:
        out.extend(r.complete(ln))
    return out


def stream8(ctx, name, fmtname, count, seed="selftest10", strata=None):
    key = ("w8", name, fmtname, count, seed, strata)
    s = ctx._streams.get(key)
    if s is None:
        cl = claims8(ctx)
        fmt = F.parse_format(fmtname)
        g = G.RandomGen(cl.get(name), fmt, seed, strata)
        s = ctx._streams[key] = list(g.lines(0, count))
    return s


def counts8(summary, name, kind=None):
    out = {}
    for _lab, d in entry_stats(summary, name).items():
        if kind is None or d[0] == kind:
            for c, n in d[3].items():
                out[c] = out.get(c, 0) + n
    return out


def failed8(summary, name):
    return {lab: d[2] for lab, d in entry_stats(summary, name).items() if d[2]}


# ---------------------------------------------------------------------------

@test
def claims_reading_wave8(ctx):
    """The kernels of the fixture of the ball vectors and the accumulator read whole, each new form
    as architecture.md writes it; malformed kernels are set aside with a reason, without making the
    others unreadable."""
    cl = claims8(ctx)
    for n in KERNELS8:
        expect(cl.get(n) is not None, "%s not read: %s" % (n, cl.broken.get(n)))
    expect(all(cl.get(n).bv_radius for n in RADII), "a radius kernel not read as one")
    expect(all(cl.get(n).acc for n in ACC), "an accumulator not read as one")
    e = cl.get("bv_mul_pow2_radius").ensures
    expect(e[0].uexact[0] == ("mask", "ex") and e[1].unless == "ex", "the radius of the scaling")
    expect(cl.get("bv_mul_pow2_step_2").ensures[1].exact_flag == "e", "exact_flag")
    expect(cl.get("bv_make_finish").ensures[0].nonneg, "nonneg")
    expect(cl.get("bv_conv_finish").ensures[0].if_all == ["okc", "okg"], "if_all")
    expect(("at_most", "g", 1) in cl.get("conv_radius").requires, "at_most")
    expect(cl.get("acc_add_2").ensures[2].own_text == "a+abs(x[0])", "rounded with a value")
    raw = raw8()
    ks = {k["name"]: k for k in raw["kernels"]}

    def kern(name, fn):
        k = copy.deepcopy(ks[name])
        fn(k)
        return k

    def ens(k, i, **kw):
        k["ensures"][i].update(kw)

    def drop(k, i, f):
        k["ensures"][i].pop(f)

    bad = [
        # upper with a value of its own and no if
        kern("bv_add_radius_1", lambda k: ens(k, 0, gaps="1")),
        kern("bv_add_radius_1", lambda k: ens(k, 0, value="rx+qq")),
        kern("bv_add_radius_1", lambda k: ens(k, 0, value="abs(rx+ry)")),
        kern("bv_add_radius_1", lambda k: ens(k, 0, value="rx+unit(no_such)")),
        kern("bv_add_radius_1", lambda k: ens(k, 0, unless="rx")),
        kern("bv_add_radius_1", lambda k: k["ensures"].append({"kind": "normalized",
                                                                "of": "rz"})),
        kern("bv_add_radius_1", lambda k: k.update(domain="extended")),
        kern("bv_mul_pow2_radius", lambda k: ens(k, 1, unless="rz")),
        kern("bv_mul_pow2_radius", lambda k: ens(k, 1, exact_when=[{"mask": "ex"}])),
        kern("bv_mul_pow2_radius", lambda k: ens(k, 0, exact_when=[{"mask": "ex"}])),
        kern("bv_mul_pow2_radius", lambda k: ens(k, 0, exact_when=[{"mask": "rx"},
                                                                   {"zero_or_abs_gt": "rx*c",
                                                                    "than": "eta"}])),
        kern("bv_mul_pow2_radius", lambda k: ens(k, 0, exact_when=[{"mask": "ex", "than": "1"},
                                                                   {"zero_or_abs_gt": "rx*c",
                                                                    "than": "eta"}])),
        kern("bv_mul_pow2_radius", lambda k: ens(k, 0, exact_when=[])),
        kern("bv_mul_pow2_radius", lambda k: ens(k, 0, exact_when=[{"zero_or_abs_gt": "rx*c",
                                                                    "than": "0"}])),
        kern("acc_radius_1", lambda k: ens(k, 0, unless="ok")),
        # at_most
        kern("conv_radius", lambda k: k.update(requires=k["requires"][:6] + ["at_most(g, 0)"]
                                               + k["requires"][7:])),
        kern("conv_radius", lambda k: k.update(requires=k["requires"][:6] + ["at_most(g, x)"]
                                               + k["requires"][7:])),
        kern("conv_radius", lambda k: k.update(requires=k["requires"] + ["at_most(g, 2)"])),
        kern("conv_radius", lambda k: k.update(requires=k["requires"] + ["at_most(zz, 1)"])),
        # exact_flag
        kern("bv_mul_pow2_step_1", lambda k: ens(k, 1, exact_flag="z")),
        kern("bv_mul_pow2_step_1", lambda k: ens(k, 1, exact_flag="x")),
        kern("bv_mul_pow2_step_1", lambda k: drop(k, 1, "exact_when")),
        kern("bv_mul_pow2_step_1", lambda k: ens(k, 0, exact_flag="e")),
        # nonneg, if_all
        kern("bv_make_finish", lambda k: ens(k, 0, nonneg=False)),
        kern("bv_make_finish", lambda k: drop(k, 0, "if")),
        kern("bv_make_finish", lambda k: ens(k, 0, steps=1)),
        kern("bv_conv_finish", lambda k: ens(k, 0, if_all=["okc"])),
        kern("bv_conv_finish", lambda k: ens(k, 0, if_all=["okc", "okc"])),
        kern("bv_conv_finish", lambda k: ens(k, 0, if_all=["okc", "rz"])),
        kern("bv_conv_finish", lambda k: ens(k, 0, **{"if": "okc"})),
        kern("bv_conv_finish", lambda k: ens(k, 0, nonneg=True)),
        # rounded with a value
        kern("acc_add_2", lambda k: ens(k, 2, value="a+abs(x[2])")),
        kern("acc_add_2", lambda k: ens(k, 2, value="a+abs(q)")),
        kern("acc_add_2", lambda k: ens(k, 2, value="a+")),
        kern("acc_add_1", lambda k: ens(k, 2, when="product_large")),
        kern("acc_add_1", lambda k: ens(k, 2, value=3)),
    ]
    data = copy.deepcopy(raw)
    data.pop("folds", None)
    for i, k in enumerate(bad):
        k["name"] = "bad_kernel_%d" % i
        data["kernels"].append(k)
    cl2 = Claims(data, "<malformed>")
    for i in range(len(bad)):
        expect("bad_kernel_%d" % i in cl2.broken, "malformed kernel %d read: %s %s" % (
            i, json.dumps(bad[i]["ensures"])[:300], bad[i]["requires"]))
    for n in KERNELS8:
        expect(cl2.get(n) is not None, "%s became unreadable: %s" % (n, cl2.broken.get(n)))
    return "%d malformed kernels set aside" % len(bad)


# What each kernel must meet in a stream through the reference runner (the classes the guards ask
# for), by kernel: (kind of entry, counts).
NEEDS8 = {
    "bv_mul_pow2_radius": [("upper", ("exact_when holds", "exact_when fails: ex true",
                                      "output the stated value exactly", "ex true: nothing claimed",
                                      "output +inf"))],
    "bv_mul_pow2_step_1": [("error", ("exact_flag true", "exact_flag false", "exact_when holds"))],
    "bv_mul_pow2_step_2": [("error", ("exact_flag true", "exact_flag false", "exact_when holds"))],
    "bv_make_finish": [("finite_or_nan", ("every mask true", "a mask false: ok", "value zero",
                                          "value finite, below zero", "value finite, above zero",
                                          "value: NaN", "value: +inf", "value: -inf"))],
    "bv_conv_finish": [("finite_or_nan", ("every mask true", "a mask false: okc",
                                          "a mask false: okg", "value: NaN", "value: +inf",
                                          "value finite, above zero"))],
    # The ruling of 2026-11-21: a result that is not finite, +inf or a NaN, is counted.
    "conv_radius": [("upper", ("output +inf", "output finite, at least the stated value",
                               "output a NaN",
                               "output not finite (+inf or a NaN): nothing more claimed"))],
}
for _k in ACC:
    NEEDS8[_k] = [("rounded", ("inexact", "the leading limb of its output is not finite: nothing "
                               "claimed"))]
for _k in ACC_RADII:
    NEEDS8[_k] = [("upper", ("ok false: nothing claimed",)), ("holds", ("holds",))]
for _k in RADII:
    NEEDS8.setdefault(_k, [("upper", ("output +inf", "output finite, at least the stated value"))])


def _kernel_runs(ctx, names, variant="correct", formats=("binary64", "binary32", TOY8), n=None):
    cl = claims8(ctx)
    n = n or ctx.n(1200, 400)
    for name in names:
        for fmtname in formats:
            if F.parse_format(fmtname).p < cl.get(name).min_precision:
                continue
            yield name, fmtname, judge(run8(stream8(ctx, name, fmtname, n), variant), cl)


@test
def bv_kernels_reference(ctx):
    """The kernels of the ball vectors and of the accumulator through the reference runner on
    random cases of three formats: nothing fails, nothing is invalid or suspicious (conv_radius
    included: by the ruling of 2026-11-21 its claim is of finite results, and its NaN
    where ma mb overflows and g or m is zero, 0 times infinity, and its +inf from small operands
    are counted, not failed); every class the guards ask for is met, and conv_radius's finite
    results are the great majority (at least three quarters, as the guards ask)."""
    found = 0
    for name, fmtname, s in _kernel_runs(ctx, KERNELS8):
        t = totals(s)
        bad = failed8(s, name)
        expect(t["failed"] == 0 and t["suspicious"] == 0, "%s %s: %s %s" % (name, fmtname, t,
                                                                            bad))
        expect(t["invalid"] == 0, "%s %s: %s" % (name, fmtname, t))
        for kind, names in NEEDS8.get(name, ()):
            c = counts8(s, name, kind)
            for x in names:
                expect(c.get(x), "%s %s: no case %r of %s (%s)" % (name, fmtname, x, kind,
                                                                    sorted(c)))
        if name == "conv_radius":
            c = counts8(s, name, "upper")
            nf = c.get("output not finite (+inf or a NaN): nothing more claimed", 0)
            fin = c.get("output finite, at least the stated value", 0)
            expect(4 * fin >= 3 * (fin + nf), "conv_radius %s: %d finite results of %d" % (
                fmtname, fin, fin + nf))
            found += nf
    return "%d kernels in 3 formats; conv_radius not finite on %d lines" % (len(KERNELS8), found)


# The planted faults of the kernels (refbv.VARIANTS): the kernels they touch and the kinds of the
# entries that must fail there.
PLANTED8 = {
    "bvr-drop-m": (("bv_add_radius_1", "bv_add_radius_2", "bv_scale_radius_1", "bv_scale_radius_2",
                    "conv_radius"), {"upper"}),
    # A NaN for +inf is no fault of conv_radius, whose claim is of finite results (the ruling of
    # 2026-11-21): it touches the other radius kernels only.
    "bvr-nan-overflow": (tuple(k for k in RADII if k != "conv_radius"), {"upper"}),
    "bvr-pow2-grow-exact": (("bv_mul_pow2_radius",), {"upper"}),
    "bvr-pow2-unless": (("bv_mul_pow2_radius",), {"upper"}),
    "bvr-conv-no-g": (("conv_radius",), {"upper"}),
    "bvr-conv-nonfinite-negative": (("conv_radius",), {"upper"}),
    "bvs-flag-inverted": (STEPS8, {"error"}),
    "bvs-flag-true": (STEPS8, {"error"}),
    "bvc-negate-not": (("neg_1",), {"rounded"}),
    "bvc-make-zero": (("bv_make_radius",), {"rounded"}),
    "bvc-center2-tail": (("bv_center_2",), {"error", "represents"}),
    "bvf-nonneg-ignored": (("bv_make_finish",), {"finite_or_nan"}),
    "bvf-one-mask": (("bv_conv_finish",), {"finite_or_nan"}),
    "acc-b-signed": (("acc_add_1", "acc_add_2", "acc_mul_1", "acc_mul_2"), {"rounded"}),
    "acc-b-overflow-omega": (ACC, {"rounded"}),
    "acc-radius-ok-true": (ACC_RADII, {"holds"}),
    "acc-radius-no-t": (ACC_RADII, {"upper"}),
}
# Entries a fault may fail beside its own: a tail dropped is not normalized where the pair was not
# a single limb.
ALSO8 = {"bvc-center2-tail": {"normalized"}, "acc-radius-ok-true": {"upper"}}


@test
def bv_kernels_planted(ctx):
    """Each planted fault of the kernels fails, in binary64, in the entries where it belongs (a
    radius without its largest term or a NaN for an overflow, conv_radius's -inf or negative
    result where it is not finite: upper; the exactness of the radius
    of a scaling grown or its two steps dropped: upper; the mask e of a step inverted or always
    true: error, its exact_flag; a copy, a negation or a constructor wrong: rounded, error and
    represents; the sign or a mask of a finish ignored: finite_or_nan; the sum of magnitudes
    signed or finite at an overflow: rounded; the radius of an accumulator with ok always true or
    without t: holds, upper) and in no kernel it does not touch."""
    notes = []
    expect(set(PLANTED8) == set(refbv.VARIANTS), "planted faults without a test: %s"
           % sorted(set(refbv.VARIANTS) ^ set(PLANTED8)))
    names = KERNELS8 if not ctx.quick else (
        "bv_add_radius_2", "bv_scale_radius_1", "bv_mul_pow2_radius", "conv_radius",
        "bv_mul_pow2_step_2", "neg_1", "bv_make_radius", "bv_center_2", "bv_make_finish",
        "bv_conv_finish", "acc_add_1", "acc_mul_2", "acc_merge_2", "acc_radius_1")
    for variant, (objs, kinds) in PLANTED8.items():
        for name, _f, s in _kernel_runs(ctx, names, variant, ("binary64",), ctx.n(600, 300)):
            fk = {d[0] for d in entry_stats(s, name).values() if d[2]}
            if name in objs:
                expect(kinds <= fk <= kinds | ALSO8.get(variant, set()),
                       "%s on %s fails %s, not %s" % (variant, name, sorted(fk) or "nothing",
                                                      sorted(kinds)))
            else:
                expect(not fk, "%s fails %s, which it does not touch: %s" % (variant, name, fk))
        notes.append(variant)
    return ", ".join(notes)


# Every operand of tiny formats (a restriction where the domain is large).  conv_radius's restricted
# domain is that of the full tier (tests/CMakeLists.txt, _toy_kernel_conv_radius): a few values of
# each operand, ma up to Omega (ma mb overflows: +inf, and a NaN where g or m is zero), the others
# small; 23 040 cases, nine tenths of them finite.
CONV_RADIUS_RESTRICT = (
    "ma.in=0x0p+0/0x1p-4/0x1p-1/0x1p+0/0x1.8p+1/0x1.cp+6",
    "mb.in=0x0p+0/0x1p-4/0x1p-1/0x1p+0/0x1.8p+1",
    "rx.in=0x0p+0/0x1p-4/0x1p-2/0x1p+0", "ry.in=0x0p+0/0x1p-4/0x1p-2/0x1p+0",
    "m.in=0x0p+0/0x1p+0/0x1p+1/0x1.8p+1", "g.in=0x0p+0/0x1p-3/0x1p-1/0x1p+0",
    "t.in=0x0p+0/0x1p-4/0x1p+0")
ENUM8 = [("bv_add_radius_1", "fp:2:-2:1", ()), ("bv_scale_radius_1", "fp:2:-2:1", ()),
         ("bv_mul_pow2_radius", "fp:3:-3:1", ()), ("bv_mul_pow2_step_1", "fp:3:-4:2", ()),
         ("bv_mul_pow2_step_2", "fp:3:-4:2", ()), ("bv_make_finish", "fp:3:-4:2", ()),
         ("bv_conv_finish", "fp:3:-4:2", ()), ("acc_add_1", "fp:2:-2:1", ()),
         ("acc_merge_1", "fp:2:-1:0", ()),
         ("neg_1", "fp:3:-4:2", ()), ("bv_make_radius", "fp:3:-4:2", ()),
         ("bv_center_2", "fp:3:-4:2", ())]
ENUM8_FULL = [("bv_add_radius_1", "fp:3:-3:1", ()), ("bv_add_radius_2", "fp:3:-3:1", ()),
              ("bv_scale_radius_2", "fp:2:-2:1", ()), ("acc_add_2", "fp:2:-2:1", ()),
              ("acc_mul_1", "fp:2:-2:1", ()), ("acc_mul_2", "fp:2:-1:0", ()),
              ("conv_radius", "fp:2:-1:0", ()), ("acc_radius_1", "fp:3:-2:0", ()),
              ("conv_radius", "fp:3:-4:4", CONV_RADIUS_RESTRICT)]


@test
def bv_kernels_exhaustive(ctx):
    """Every operand of tiny formats through the reference runner: nothing fails (conv_radius
    included, whose results in fp:2:-1:0 are all +inf or a NaN: its constant up((1+u)^7) is above
    Omega there) and the coverage is complete; the at_most() domain is the numbers up to its
    bound; a planted fault is caught there too."""
    cl = claims8(ctx)
    cases = ENUM8 + (ENUM8_FULL if not ctx.quick else [])
    n = 0
    for name, fmtname, restrict in cases:
        g = G.ExhaustiveGen(cl.get(name), F.parse_format(fmtname), list(restrict))
        s = judge(run8(list(g.lines(0, g.total))), cl)
        t = totals(s)
        n += g.total
        expect(t["failed"] == 0 and t["suspicious"] == 0, "%s %s: %s %s" % (
            name, fmtname, t, failed8(s, name)))
        expect(t["invalid"] == 0, "%s %s: %s" % (name, fmtname, t))
        cov = s.coverage.describe()
        expect(cov and ("COMPLETE" in cov[0] or restrict), "coverage: %s" % cov)
    # at_most(g, 1): every number of the format from 0 to 1, by brute force.
    fmt = F.parse_format("fp:2:-2:1")
    g = G.ExhaustiveGen(cl.get("conv_radius"), fmt, [])
    one = 1 << 2
    want = [v for v in F.all_values(fmt) if 0 <= v <= one]
    expect(sorted(t[0] for t in g.doms[5]) == want, "the domain of at_most(g, 1): %s"
           % g.doms[5])
    for variant, name, fmtname, kind in (("bvs-flag-true", "bv_mul_pow2_step_1", "fp:3:-4:2",
                                          "error"),
                                         ("bvf-nonneg-ignored", "bv_make_finish", "fp:3:-4:2",
                                          "finite_or_nan"),
                                         ("acc-b-signed", "acc_add_1", "fp:3:-4:2", "rounded")):
        g = G.ExhaustiveGen(cl.get(name), F.parse_format(fmtname), [])
        s = judge(run8(list(g.lines(0, g.total)), variant), cl)
        expect(kind in {d[0] for d in entry_stats(s, name).values() if d[2]},
               "%s on every operand: %s" % (variant, failed8(s, name)))
    return "%d cases" % n


OM8 = "0x1.fffffffffffffp+1023"
# Hand-written lines: (line, verdict, kind of the entry that fails, [a text of the reason]).
JUDGE8 = [
    # bv_add_radius_1 in binary64: U = unit(add_1_1)/(1-unit(add_1_1)) = u, the value rx+ry+m u.
    ("bv_add_radius_1 binary64 0x1p+0 0x1p+0 0x1p+0 -> 0x1.0000000000001p+1", "pass", None),
    ("bv_add_radius_1 binary64 0x1p+0 0x1p+0 0x1p+0 -> 0x1p+1", "fail", "upper", "below"),
    ("bv_add_radius_1 binary64 0x1p+0 0x1p+0 0x1p+0 -> inf", "suspicious", None),
    ("bv_add_radius_1 binary64 %s %s 0x1p+0 -> inf" % (OM8, OM8), "pass", None),
    ("bv_add_radius_1 binary64 0x1p+0 0x1p+0 0x1p+0 -> nan", "fail", "upper", "is a NaN"),
    ("bv_add_radius_1 binary64 0x1p+0 0x1p+0 0x1p+0 -> -inf", "fail", "upper", "-inf"),
    ("bv_add_radius_1 binary64 0x0p+0 0x0p+0 0x0p+0 -> 0x0p+0", "pass", None),
    ("bv_add_radius_1 binary64 -0x1p+0 0x1p+0 0x1p+0 -> 0x1p+2", "invalid", None),
    # bv_scale_radius_1: abs(a) rx + m u + tiny(mul_1_1)/(1-u/(1+u)); a negative.
    ("bv_scale_radius_1 binary64 0x0p+0 0x1p+0 -0x1p+1 -> 0x1p+1", "fail", "upper", "below"),
    ("bv_scale_radius_1 binary64 0x0p+0 0x1p+0 -0x1p+1 -> 0x1.0000000000001p+1", "pass", None),
    # conv_radius: at_most(g, 1).  Its claim is of finite results (the ruling of
    # 2026-11-21): a result that is not finite passes when it is +inf or a NaN, from any operands
    # (never suspicious), and fails when it is -inf or negative.  The interpreter's lines: a NaN
    # from 0 times infinity (ma mb overflows, g or m zero; the value is 0), +inf where ma mb
    # overflows and g is the smallest number (the value about 2^926), and the value 4 + 4u of
    # operands 1 (0x1.0000000000004p+2).
    ("conv_radius binary64 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x1p+1 0x0p+0 -> 0x1p+4", "invalid",
     None),
    ("conv_radius binary64 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x0p+0 -> 0x1.8p+2", "pass",
     None),
    ("conv_radius binary64 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x0p+0 -> 0x1p+2", "fail",
     "upper", "below"),
    ("conv_radius binary64 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x0p+0 -> "
     "0x1.0000000000004p+2", "pass", None),
    ("conv_radius binary64 0x1p+1000 0x1p+1000 0x0p+0 0x0p+0 0x0p+0 0x0p+0 0x0p+0 -> nan", "pass",
     None),
    ("conv_radius binary64 0x1p+1000 0x1p+1000 0x0p+0 0x0p+0 0x1p+0 0x0p+0 0x0p+0 -> nan", "pass",
     None),
    ("conv_radius binary64 0x1p+1000 0x1p+1000 0x0p+0 0x0p+0 0x1p+0 0x0.0000000000001p-1022 "
     "0x0p+0 -> inf", "pass", None),
    ("conv_radius binary64 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x0p+0 -> inf", "pass", None),
    ("conv_radius binary64 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x0p+0 -> nan", "pass", None),
    ("conv_radius binary64 0x1p+0 0x1p+0 0x1p+0 0x1p+0 %s 0x1p+0 0x0p+0 -> inf" % OM8, "pass",
     None),
    ("conv_radius binary64 0x1p+1000 0x1p+1000 0x0p+0 0x0p+0 0x0p+0 0x0p+0 0x0p+0 -> -inf",
     "fail", "upper", "+inf or a NaN"),
    ("conv_radius binary64 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x0p+0 -> -inf", "fail",
     "upper", "+inf or a NaN"),
    ("conv_radius binary64 0x1p+1000 0x1p+1000 0x0p+0 0x0p+0 0x0p+0 0x0p+0 0x0p+0 -> -0x1p+0",
     "fail", "upper", "below"),
    ("conv_radius binary64 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x0p+0 -> -%s" % OM8, "fail",
     "upper", "below"),
    ("conv_radius binary64 0x1p+0 0x1p+0 0x1p+0 0x1p+0 -0x0p+0 0x1p+0 0x0p+0 -> 0x0p+0", "pass",
     None),
    ("conv_radius binary64 0x1p+0 0x1p+0 0x1p+0 0x1p+0 0x1p-1 0x1p+0 0x0p+0 -> 0x1p+0", "invalid",
     None),
    # bv_mul_pow2_radius (m, ex, rx, c): rz >= rx c, = rx c when ex and rx c = 0 or > N; rz >= rx c
    # + eta when ex is false.
    ("bv_mul_pow2_radius binary64 0x1p+0 1 0x1p+0 0x1p+1 -> 0x1p+1", "pass", None),
    ("bv_mul_pow2_radius binary64 0x1p+0 1 0x1p+0 0x1p+1 -> 0x1.0000000000001p+1", "fail", "upper",
     "exact_when holds"),
    ("bv_mul_pow2_radius binary64 0x1p+0 1 0x1p+0 0x1p+1 -> inf", "fail", "upper",
     "exact_when holds"),
    ("bv_mul_pow2_radius binary64 0x1p+0 0 0x1p+0 0x1p+1 -> 0x1p+1", "fail", "upper", "below"),
    ("bv_mul_pow2_radius binary64 0x1p+0 0 0x1p+0 0x1p+1 -> 0x1.0000000000002p+1", "pass", None),
    ("bv_mul_pow2_radius binary64 0x1p+0 1 0x0.0000000000001p-1022 0x1p+0 -> "
     "0x0.0000000000003p-1022", "pass", None),
    ("bv_mul_pow2_radius binary64 0x1p+0 1 %s 0x1p+1 -> inf" % OM8, "pass", None),
    ("bv_mul_pow2_radius binary64 0x1p+0 1 0x0p+0 0x1p+1 -> 0x0p+0", "pass", None),
    ("bv_mul_pow2_radius binary64 0x1p+0 1 0x0p+0 0x1.8p+1 -> 0x0p+0", "invalid", None),
    # The steps: the mask e true exactly when x c (each limb times c) is zero or above N.
    ("bv_mul_pow2_step_1 binary64 0x1p+0 0x1p+1 -> 0x1p+1 1", "pass", None),
    ("bv_mul_pow2_step_1 binary64 0x1p+0 0x1p+1 -> 0x1p+1 0", "fail", "error", "exact_flag"),
    ("bv_mul_pow2_step_1 binary64 0x0.0000000000001p-1022 0x1p+0 -> 0x0.0000000000001p-1022 0",
     "pass", None),
    ("bv_mul_pow2_step_1 binary64 0x0.0000000000001p-1022 0x1p+0 -> 0x0.0000000000001p-1022 1",
     "fail", "error", "exact_flag"),
    ("bv_mul_pow2_step_1 binary64 -0x0p+0 0x1p+0 -> 0x0p+0 1", "pass", None),
    ("bv_mul_pow2_step_2 binary64 0x1p+0 0x1p-60 0x1p-1 -> 0x1p-1 0x1p-61 1", "pass", None),
    ("bv_mul_pow2_step_2 binary64 0x1p+0 0x1p-1060 0x1p-1 -> 0x1p-1 0x1p-1061 0", "pass", None),
    ("bv_mul_pow2_step_2 binary64 0x1p+0 0x1p-1060 0x1p-1 -> 0x1p-1 0x1p-1061 1", "fail", "error",
     "exact_flag"),
    # The finishes (the extended domain).
    ("bv_make_finish binary64 0x1p+0 1 -> 0x1p+0 1", "pass", None),
    ("bv_make_finish binary64 -0x1p+0 1 -> nan 0", "pass", None),
    ("bv_make_finish binary64 -0x1p+0 1 -> -0x1p+0 1", "fail", "finite_or_nan", "flag"),
    ("bv_make_finish binary64 -0x0p+0 1 -> 0x0p+0 1", "pass", None),
    ("bv_make_finish binary64 0x1p+0 0 -> nan 0", "pass", None),
    ("bv_make_finish binary64 inf 1 -> nan 0", "pass", None),
    ("bv_make_finish binary64 -inf 1 -> nan 0", "pass", None),
    ("bv_make_finish binary64 nan 1 -> nan 0", "pass", None),
    ("bv_make_finish binary64 0x1p+0 1 -> nan 0", "fail", "finite_or_nan", "flag"),
    ("bv_make_finish binary64 0x1p+0 1 -> 0x1p+1 1", "fail", "finite_or_nan", "not the value"),
    ("bv_conv_finish binary64 0x1p+0 1 1 -> 0x0p+0 1", "fail", "finite_or_nan", "not the value"),
    ("bv_make_finish binary64 -0x1p+0 1 -> 0x0p+0 0", "fail", "finite_or_nan", "not a NaN"),
    ("bv_conv_finish binary64 0x1p+0 1 1 -> 0x1p+0 1", "pass", None),
    ("bv_conv_finish binary64 0x1p+0 1 0 -> nan 0", "pass", None),
    ("bv_conv_finish binary64 0x1p+0 0 1 -> nan 0", "pass", None),
    ("bv_conv_finish binary64 0x1p+0 1 0 -> 0x1p+0 1", "fail", "finite_or_nan", "okg"),
    ("bv_conv_finish binary64 -0x1p+0 1 1 -> -0x1p+0 1", "pass", None),
    ("bv_conv_finish binary64 inf 1 1 -> nan 0", "pass", None),
    # The copies.
    ("neg_1 binary64 0x1p+0 -> -0x1p+0", "pass", None),
    ("neg_1 binary64 0x1p+0 -> 0x1p+0", "fail", "rounded"),
    ("bv_make_radius binary64 0x1p+0 -0x1p+0 -> -0x1p+0", "pass", None),
    ("bv_make_radius binary64 0x1p+0 -0x1p+0 -> 0x0p+0", "fail", "rounded"),
    ("bv_center_2 binary64 0x1p+0 0x1p-60 -> 0x1p+0 0x1p-60", "pass", None),
    ("bv_center_2 binary64 0x1p+0 0x1p-60 -> 0x1p+0 0x0p+0", "fail", "represents"),
    ("bv_center_2 binary64 inf 0x0p+0 -> inf 0x0p+0", "pass", None),
    ("bv_center_2 binary64 nan nan -> nan nan", "pass", None),
    # The accumulator: t the running sum, b = RN(a + |x|) where b is finite.
    ("acc_add_1 binary64 0x1p+0 0x1p+0 -0x1p+0 -> 0x0p+0 0x1p+1", "pass", None),
    ("acc_add_1 binary64 0x1p+0 0x1p+0 -0x1p+0 -> 0x0p+0 0x0p+0", "fail", "rounded"),
    ("acc_add_1 binary64 0x0p+0 0x1p+0 0x1p-53 -> 0x1p-53 0x1p+0", "pass", None),
    ("acc_add_1 binary64 0x0p+0 0x1p+0 0x1p-53 -> 0x1p-53 0x1.0000000000001p+0", "fail",
     "rounded"),
    ("acc_add_1 binary64 0x1p+0 %s %s -> %s inf" % (OM8, OM8, OM8), "pass", None),
    ("acc_add_1 binary64 0x1p+0 %s %s -> %s %s" % (OM8, OM8, OM8, OM8), "fail", "rounded",
     "beyond Omega"),
    ("acc_add_1 binary64 %s 0x1p+0 %s -> inf 0x1p+0" % (OM8, OM8), "fail", "rounded"),
    ("acc_add_1 binary64 %s 0x1p+0 %s -> inf %s" % (OM8, OM8, OM8), "pass", None),
    ("acc_add_1 binary64 0x1p+0 -0x1p+0 0x1p+0 -> 0x1p+1 0x0p+0", "invalid", None),
    ("acc_add_2 binary64 0x1p+0 0x0p+0 0x0p+0 -0x1p+0 -0x1p-60 -> -0x1p-60 0x0p+0 0x1p+0", "pass",
     None),
    ("acc_mul_1 binary64 0x0p+0 0x1p+0 -0x1p+0 0x1p+0 -> -0x1p+0 0x1p+1", "pass", None),
    ("acc_mul_1 binary64 0x0p+0 0x1p+0 -0x1p+0 0x1p+0 -> -0x1p+0 0x0p+0", "fail", "rounded"),
    ("acc_merge_1 binary64 0x1p+0 0x1p+0 0x1p+0 0x1p+1 -> 0x1p+1 0x1.8p+1", "pass", None),
    # The radius of an accumulator: m = 0 gives the constant C (about N), ok true; m u > 1/2 with
    # ok true fails holds; ok false claims nothing.
    ("acc_radius_1 binary64 0x0p+0 0x0p+0 0x0p+0 0x0p+0 -> 0x1p-1022 1", "pass", None),
    ("acc_radius_1 binary64 0x0p+0 0x1p+53 0x0p+0 0x0p+0 -> 0x1p+0 1", "fail", "holds"),
    ("acc_radius_1 binary64 0x0p+0 0x1p+53 0x0p+0 0x0p+0 -> 0x1p+0 0", "pass", None),
    ("acc_radius_1 binary64 0x1p+0 0x1p+0 0x1p+0 0x0p+0 -> 0x1p+0 1", "fail", "upper"),
    ("acc_radius_1 binary64 %s 0x1p+0 0x1p-1022 0x0p+0 -> inf 1" % OM8, "pass", None),
    ("acc_radius_1 binary64 0x1p+0 0x1p+0 0x1p-1022 0x0p+0 -> inf 1", "suspicious", None),
]


@test
def bv_kernels_judge(ctx):
    """Hand-written lines of the kernels of the ball vectors and of the accumulator, each verdict
    worked out by hand: at and one unit below a stated value, +inf (passing, and suspicious from
    small operands), a NaN and -inf; at_most both ways; the radius of a scaling exact and not, its
    unless, beyond Omega; the mask of a step both ways; each cell of the finishes (the masks, a
    negative value, either zero, the infinities, a NaN); the copies; the sum of magnitudes at a tie
    and at an overflow beside a finite running sum, and the reverse; the radius of an accumulator
    under its mask; conv_radius's results that are not finite (+inf and a NaN passing from any
    operands, -inf and a negative number failing: the ruling of 2026-11-21)."""
    cl = claims8(ctx)
    n = 0
    for case in JUDGE8:
        line, want, kind = case[:3]
        name = line.split(" ", 1)[0]
        s = judge([line], cl)
        t = totals(s)
        reasons = " ".join(r for st in s.keys.values() for r in st.reasons)
        if len(case) > 3:
            expect(case[3] in reasons, "%s: failed for %r, not %r" % (line, reasons, case[3]))
        if want == "pass":
            ok = t["passed"] == 1 and t["failed"] == 0 and t["suspicious"] == 0
        elif want == "invalid":
            ok = t["invalid"] == 1
        elif want == "suspicious":
            ok = t["suspicious"] == 1 and t["failed"] == 0
        else:
            ok = t["failed"] == 1 and kind in {d[0] for d in entry_stats(s, name).values() if d[2]}
        expect(ok, "%s: %s, expected %s%s (%s; failing entries %s)" % (
            line, t, want, " in " + kind if kind else "", reasons, failed8(s, name)))
        n += 1
    return "%d lines" % n


@test
def gen_wave8(ctx):
    """The families of the kernels of the ball vectors and of the accumulator (gen8.py): case i
    alone is case i of its run, the seed matters, every case satisfies the requirements (valid8 and
    the checker), every stratum the header lists has cases, each kernel gets its family."""
    cl = claims8(ctx)
    fam = {k: G8.family_of(cl.get(k)) for k in KERNELS8}
    for k in RADII:
        expect(fam[k] == "radius", "%s: family %s" % (k, fam[k]))
    for k in ACC:
        expect(fam[k] == "acc", "%s: family %s" % (k, fam[k]))
    for k in ACC_RADII:
        expect(fam[k] == "accradius", "%s: family %s" % (k, fam[k]))
    for k in FINISHES:
        expect(fam[k] == "bvfinish", "%s: family %s" % (k, fam[k]))
    for k in COPIES + STEPS8:
        expect(fam[k] is None, "%s: family %s" % (k, fam[k]))
    n = ctx.n(400, 160)
    for k in KERNELS8:
        for fmtname in ("binary64", TOY8):
            fmt = F.parse_format(fmtname)
            if fmt.p < cl.get(k).min_precision:
                continue
            g = G.RandomGen(cl.get(k), fmt, "gen8")
            lines = list(g.lines(0, n))
            expect(G.RandomGen(cl.get(k), fmt, "gen8").case(n // 2) == lines[1 + n // 2],
                   "%s: case i alone differs" % k)
            other = G.RandomGen(cl.get(k), fmt, "other")
            expect(any(other.case(i) != lines[1 + i] for i in range(20)), "%s: the seed" % k)
            tags = {ln.rsplit("#", 1)[1].split(":")[0] for ln in lines[1:-1]}
            expect(set(g.strata) <= tags, "%s %s: strata without cases: %s" % (
                k, fmtname, set(g.strata) - tags))
            ck = C.Checker(cl)
            for ln in lines[1:-1]:
                x = ln.split(" #")[0].split(" ")[2:]
                pl = ck.plan(k, fmtname)
                if pl.ext is None:
                    vals = [C.MASK_TEXT[t] if i in pl.in_masks else F.parse_limb(fmt, t)
                            for i, t in enumerate(x)]
                    expect(all(type(v) is int for v in vals) and ck.violated(pl, vals) is None,
                           "%s: invalid case %s" % (k, ln))
    return "%d kernels" % len(KERNELS8)


@test
def merging_wave8(ctx):
    """The merge of the summaries of two halves of streams of the kernels of the ball vectors and
    of the accumulator is the summary of the whole."""
    cl = claims8(ctx)
    parts = [run8(stream8(ctx, k, "binary64", ctx.n(200, 80)))
             for k in ("bv_mul_pow2_radius", "acc_add_2", "bv_conv_finish", "acc_radius_2")]
    lines = [ln for p in parts for ln in p]
    whole = judge(lines, cl)
    cut = len(parts[0]) + len(parts[1])
    a, b = judge(lines[:cut], cl), judge(lines[cut:], cl)
    m = C.Summary()
    m.merge(a)
    m.merge(b)
    expect(json.dumps(whole.to_json(), sort_keys=True) == json.dumps(m.to_json(), sort_keys=True),
           "the merged summary differs from the whole")
    return "%d lines" % len(lines)


def _vals(fmt, line):
    """The input limbs of a request or completed line, as fixed values (or non-finite ones); a
    mask's 0 or 1 read as a number of the format, as the strata below never look at masks."""
    return [int(t) if t in ("0", "1") else F.parse_limb(fmt, t)
            for t in line.split(" #")[0].split(" ")[2:]]


def _own_counts(summary, name):
    """The counts of the rounded entry with a value of its own (the accumulator's sum of
    magnitudes)."""
    out = {}
    for lab, d in entry_stats(summary, name).items():
        if d[0] == "rounded" and " of " in lab:
            for c, n in d[3].items():
                out[c] = out.get(c, 0) + n
    return out


def _outs(fmt, line):
    return [int(t) if t in ("0", "1") else F.parse_limb(fmt, t)
            for t in line.split(" -> ")[1].split(" ")]


@test
def gen_wave8_strata(ctx):
    """Each stratum of the families of gen8.py reaches the corner it is for: radius huge an output
    +inf, zeros every operand zero but a mask, atnormal r_x c exactly N, mixed operands more than
    2^p apart; acc atop the sum of magnitudes +inf beside a finite running sum, cancel a running sum
    that cancels, tie and exactprod a tie and an exact sum of magnitudes, apart a and what is added
    more than 2^p apart; accradius limit the mask both ways, beyond the mask false, integer an
    integer count, abig a in the top binades; bvfinish negative, nonfinite, zeros and top their
    values, masks a false mask beside a positive value."""
    cl = claims8(ctx)
    n = ctx.n(120, 60)
    fmt = F.parse_format("binary64")
    p = fmt.p
    big = 1 << p
    seen = {}

    def lines_of(k, s):
        out = run8(stream8(ctx, k, "binary64", n, strata=(s,)))
        return [ln for ln in out if not ln.startswith("#")]

    def note(key, cond):
        seen[key] = seen.get(key, False) or bool(cond)

    huge = [_outs(fmt, ln)[0] == F.POS_INF for ln in lines_of("bv_add_radius_2", "huge")]
    note("radius huge", 2 * sum(huge) >= len(huge))
    for ln in lines_of("bv_add_radius_2", "mixed"):
        x = [abs(v) for v in _vals(fmt, ln) if v]
        note("radius mixed", len(x) >= 2 and max(x) > big * min(x))
    for k in ("bv_add_radius_2", "bv_mul_pow2_radius", "conv_radius"):
        masks = C.Checker(cl).plan(k, "binary64").in_masks
        for ln in lines_of(k, "zeros"):
            note("radius zeros", all(v == 0 for i, v in enumerate(_vals(fmt, ln))
                                     if i not in masks))
    for ln in lines_of("bv_mul_pow2_radius", "atnormal"):
        x = _vals(fmt, ln)
        note("radius atnormal", x[2] * x[3] == fmt.lam << -fmt.qmin)
    for k in ("acc_add_1", "acc_mul_2", "acc_merge_1"):
        kern = cl.get(k)
        ks = kern.limbs_of("s")
        for ln in lines_of(k, "atop"):
            z = _outs(fmt, ln)
            note("acc atop", z[ks] == F.POS_INF and type(z[0]) is int)
        if k == "acc_add_1":
            # The sum of magnitudes (the entry with a value of its own): ties in its stratum,
            # exact sums in exactprod.
            ties = [_own_counts(judge([ln], cl), k).get("tie", 0) > 0
                    for ln in lines_of(k, "tie")]
            note("acc tie", 4 * sum(ties) >= 3 * len(ties))
            ex = [_own_counts(judge([ln], cl), k).get("exact", 0) > 0
                  for ln in lines_of(k, "exactprod")]
            note("acc exactprod", 4 * sum(ex) >= 3 * len(ex))
        for ln in lines_of(k, "apart"):
            x = _vals(fmt, ln)
            a = x[ks]
            rest = [abs(v) for v in x[ks + 1:] if v]
            note("acc apart", a and rest and (a > big * max(rest) or big * a < min(rest)))
    for k in ("acc_add_1", "acc_add_2"):
        for ln in lines_of(k, "cancel"):
            x = _vals(fmt, ln)
            z = _outs(fmt, ln)
            note("acc cancel", type(z[0]) is int and x[0] and abs(z[0]) * big < abs(x[0]))
    for k in ACC_RADII:
        oks = {ln.rsplit(" ", 1)[1] for ln in lines_of(k, "limit")}
        note("accradius limit", oks == {"0", "1"})
        for ln in lines_of(k, "beyond"):
            note("accradius beyond", ln.rsplit(" ", 1)[1] == "0")
        ints = [_vals(fmt, ln)[1] for ln in lines_of(k, "integer")]
        one = 1 << -fmt.qmin
        ints = [0 < m <= one << p and m % one == 0 for m in ints]
        note("accradius integer", 10 * sum(ints) >= 9 * len(ints))
        for ln in lines_of(k, "abig"):
            note("accradius abig", _vals(fmt, ln)[0] >= 1 << (fmt.emax - p - fmt.qmin))
    for k in FINISHES:
        for s, cond in (("negative", lambda v: type(v) is int and v < 0),
                        ("nonfinite", lambda v: type(v) is not int),
                        ("zeros", lambda v: v == 0),
                        ("top", lambda v: type(v) is int and v >= F.pred(fmt, fmt.omega))):
            for ln in lines_of(k, s):
                note("bvfinish " + s, cond(_vals(fmt, ln)[0]))
        for ln in lines_of(k, "masks"):
            x = ln.split(" #")[0].split(" ")[2:]
            note("bvfinish masks", "0" in x[1:] and F.parse_limb(fmt, x[0]) > 0)
    missing = sorted(k for k, v in seen.items() if not v)
    expect(not missing and len(seen) == 18, "strata off their corners: %s (%d seen)"
           % (missing, len(seen)))
    return "%d corners" % len(seen)
