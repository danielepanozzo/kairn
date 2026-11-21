"""The oracle's own tests for the folds of the ball vectors (architecture.md, "Ball vectors"): the ball
vectors bv_add_k, bv_sub_k, bv_scale_k, bv_neg_k and bv_mul_pow2_k (encloses_entries, V1 to V4,
finite_from, exact_when), the constructors bv_make_k (makes_ball_vector), the products bv_conv_k
(encloses_coefficients, count_when), and the requests in place (inplace=I) of every loop that has
them.

As for the earlier waves, each test compares the oracle with something it does not share code
with: the reference runner (refbv.py, written from the listings of gen/kernels/) on random streams
and on every operand of tiny formats; planted faults that must be caught in the class where they
belong and nowhere else; hand-written lines whose verdicts are worked out by hand.  The fixture is
that of the kernels of the ball vectors (oracle/selftest/claims-wave8.json, selftest10.py).
"""

import copy
import json

from . import bvfolds as BF
from . import fmt as F
from . import genbv as GB
from . import genmap as GM
from . import refbv
from .claims import Claims
from .selftest import test, expect, judge, totals
from .selftest7 import entry_stats
from .selftest10 import FIXTURE8, claims8, raw8, run8

ADD = ("bv_add_1", "bv_add_2", "bv_sub_1", "bv_sub_2")
SCALE = ("bv_scale_1", "bv_scale_2")
NEG = ("bv_neg_1", "bv_neg_2")
MULP = ("bv_mul_pow2_1", "bv_mul_pow2_2")
MAKE = ("bv_make_1", "bv_make_2")
CONV = ("bv_conv_1", "bv_conv_2")
BVS = ADD + SCALE + NEG + MULP
FOLDS11 = BVS + MAKE + CONV
# The toy formats of the random runs: one limb and two (precision 4 or more for the products),
# binary_float's (bvfolds.v4_range).
TOYS11 = {1: "fp:5:-11:4", 2: "fp:4:-7:2"}
TOY_CONV = "fp:5:-12:5"


def fold11(ctx, name):
    return claims8(ctx).get_fold(name)


def stream11(ctx, name, fmtname, count, seed="selftest11", strata=None, inplace=False,
             max_length=12):
    key = ("w11", name, fmtname, count, seed, strata, inplace, max_length)
    s = ctx._streams.get(key)
    if s is None:
        g = GM.random_gen(fold11(ctx, name), F.parse_format(fmtname), seed, strata, None,
                          max_length, inplace=inplace)
        s = ctx._streams[key] = list(g.lines(0, count))
    return s


def counts11(summary, name):
    """The counts of a fold's first entry (its claim), summed over formats and tags."""
    for _lab, d in entry_stats(summary, name).items():
        if d[0] in ("encloses_entries", "makes_ball_vector", "encloses_coefficients"):
            return d[3]
    return {}


def classes11(summary, name):
    """The classes of failure of a fold's claim (failed V1, V2, ..., flag, exact)."""
    return {c[7:] for c in counts11(summary, name) if c.startswith("failed ")}


def formats11(ctx, name):
    f = fold11(ctx, name)
    toy = TOY_CONV if name in CONV else TOYS11[f.wlimbs]
    return [x for x in ("binary64", "binary32", toy) if F.parse_format(x).p >= f.min_precision]


# ---------------------------------------------------------------------------

def _fold_raw(raw, name):
    return next(f for f in raw["folds"] if f["name"] == name)


# Malformed folds: (fold, the change, a text of the refusal).
def _set(path, value):
    def change(f):
        d = f
        for k in path[:-1]:
            d = d[k]
        if value is _DROP:
            del d[path[-1]]
        else:
            d[path[-1]] = value
    return change


_DROP = object()
MALFORMED11 = [
    ("bv_add_1", _set(("ensures", 0, "kind"), "encloses"), "unknown kind"),
    ("bv_add_1", _set(("requires",), ["ball_vector(x, rx)"]), ""),
    ("bv_add_1", _set(("requires",), ["ball_vector(x, rx)", "ball_vector(y, rx)"]), ""),
    ("bv_add_1", _set(("ensures", 0, "finite_when"), "abs_le(x,-2)"), "must be a list"),
    ("bv_add_1", _set(("ensures", 0, "finite_when", 0, "exp"), "two"), "exp must be an integer"),
    ("bv_add_1", _set(("ensures", 0, "finite_when", 0, "abs_le"), "abs(x+"), "unexpected"),
    ("bv_add_1", _set(("ensures", 0, "finite_when", 0, "abs_le"), "abs(q)+rx"), "not a name"),
    ("bv_add_1", _set(("ensures", 0, "radii_when"), [{"abs_le": "rx", "exp": 1.5}]),
     "exp must be an integer"),
    ("bv_add_1", _set(("ensures", 0, "finite_from"), "two"), ""),
    ("bv_add_1", _set(("radius",), "no_such_kernel"), "not a kernel of the claims"),
    ("bv_add_1", _set(("step",), "no_such_kernel"), "not a kernel of the claims"),
    ("bv_add_1", _set(("writes",), [{"name": "z", "limbs": 1}, {"name": "w", "limbs": 1}]),
     "writes one array"),
    ("bv_add_1", _set(("outputs",), [{"name": "r", "limbs": 1}]), "outputs must be"),
    ("bv_add_1", _set(("scalars", 0, "limbs"), 2), "limbs"),
    ("bv_add_2", _set(("arrays", 0, "limbs"), 1), "other limbs"),
    ("bv_add_1", _set(("orders",), ["diagonal"]), "orders must be"),
    ("bv_add_1", _set(("status",), "maybe"), "status must be"),
    ("bv_add_1", _set(("min_precision",), "four"), "min_precision must be an integer"),
    ("bv_add_1", _set(("ensures",), []), "ensures must be one entry"),
    ("bv_mul_pow2_1", _set(("requires",), ["ball_vector(x, rx)", "power_of_two(rx)"]),
     "power_of_two"),
    ("bv_mul_pow2_2", _set(("ensures", 0, "exact_when", 0),
                           {"zero_or_abs_gt": "x[2]*c", "than": "eta/(2*u)"}), "not a limb"),
    ("bv_mul_pow2_2", _set(("ensures", 0, "exact_when", 0),
                           {"zero_or_abs_gt": "x[0]*c", "than": "-1"}), "not positive"),
    ("bv_mul_pow2_2", _set(("ensures", 0, "exact_when"), "x"), "exact_when must be a list"),
    ("bv_conv_2", _set(("ensures", 0, "count_when"), "le(n,1)"), "count_when must be a list"),
    ("bv_conv_2", _set(("ensures", 0, "count_when", 0, "le"), "n*("), "unexpected"),
    ("bv_conv_2", _set(("ensures", 0, "count_when", 0, "le"), "q*eta"), "EXPR is over"),
    ("bv_conv_2", _set(("ensures", 0, "count_when", 0, "than"), "x"), ""),
    ("bv_conv_2", _set(("ensures", 0, "kind"), "encloses_entries"), ""),
    ("bv_conv_2", _set(("radius",), "no_such_kernel"), "not a kernel of the claims"),
    ("bv_conv_2", _set(("orders",), ["sequential", "lanes"]), ""),
    ("bv_make_1", _set(("ensures", 0, "from"), {"center": "c"}), ""),
    ("bv_make_1", _set(("ensures", 0, "flag"), "nope"), ""),
    ("bv_make_2", _set(("requires",), []), ""),
]


@test
def claims_reading_bv_folds(ctx):
    """The folds of the fixture's ball vectors read whole; each malformed variant of one of them is
    refused, that fold alone, with the reason (a kind, a requirement of a BallVector missing or
    shared, a condition that is not a list, an exponent, an expression or a name, a radius or step
    kernel not of the claims, the arrays written and the outputs, the limbs, the orders, the
    status, the minimum precision, a radius required to be a power of two, a limb of exact_when,
    a threshold, count_when, the shape of a constructor)."""
    cl = claims8(ctx)
    for name in FOLDS11:
        f = cl.get_fold(name)
        expect(isinstance(f, (BF.BallVector, BF.BvConv)), "%s: %r" % (name, f))
    raw = raw8()
    for i, (name, change, text) in enumerate(MALFORMED11):
        r = copy.deepcopy(raw)
        change(_fold_raw(r, name))
        c = Claims(r, FIXTURE8)
        why = c.broken.get(name)
        expect(why is not None and text in why, "malformed %d (%s): %r" % (i, name, why))
        others = [k for k in c.broken if k != name]
        expect(not others, "malformed %d (%s) broke others too: %s" % (i, name, others))
    return "%d folds, %d malformed" % (len(FOLDS11), len(MALFORMED11))


# The classes each fold must have met in its random runs (bvfolds.py statistics).
def _needs11(f, fmt):
    need = [BF.RES_FINITE, BF.RES_WHOLE]
    if isinstance(f, BF.BvConv):
        need += [BF.OP_WHOLE, BF.OP_FINITE, BF.V4_APPLIES, "V3: the radius at least conv_radius's "
                 "stated value", "n_x = 0", "n_y = 0", "n_x = 1", "n_y = 1", "n_x != n_y"]
    elif f.kind == "makes_ball_vector":
        need += ["given radius %s, centers finite" % c for c in ("negative", "NaN", "+inf",
                                                                  "positive", "+0", "-0")]
        need.append("given radius positive, centers not all finite")
    else:
        need += [BF.OP_WHOLE, BF.OP_FINITE, "length 0", "length 1", "order: sequential"]
        if f.finite_from is not None and fmt.p < f.finite_from:
            need.append(BF.V4_BELOW)
        else:
            need += [BF.V4_APPLIES, BF.V4_EMPTY]
        if f.exact_when is not None:
            need.append(BF.EXACT_HOLDS)
    return need


@test
def bv_folds_reference(ctx):
    """The folds of the ball vectors through the reference runner on random cases of binary64,
    binary32 and a toy format, and in place: nothing fails, nothing is invalid or suspicious, and
    every class the guards ask for is met (both results, an operand that is the whole space, V4
    applying, with no entry too, exactness, every class of a radius given, the lengths 0 and 1 on
    each side of a product, every array written in place)."""
    cl = claims8(ctx)
    n = ctx.n(400, 150)
    names = FOLDS11 if not ctx.quick else ("bv_add_2", "bv_sub_1", "bv_scale_1", "bv_neg_2",
                                           "bv_mul_pow2_2", "bv_make_1", "bv_conv_2")
    runs = 0
    for name in names:
        f = fold11(ctx, name)
        for fmtname in formats11(ctx, name)[: 3 if not ctx.quick else 2]:
            fmt = F.parse_format(fmtname)
            for inplace in ((False, True) if name not in CONV else (False,)):
                s = judge(run8(stream11(ctx, name, fmtname, n, inplace=inplace)), cl)
                t = totals(s)
                runs += 1
                expect(t["failed"] == 0 and t["invalid"] == 0 and t["suspicious"] == 0,
                       "%s %s%s: %s %s" % (name, fmtname, " in place" if inplace else "", t,
                                           [r for st in s.keys.values() for r in st.reasons][:3]))
                c = counts11(s, name)
                for x in _needs11(f, fmt) + ([BF.INPLACE % i for i, (_a, l) in
                                              enumerate(f.arrays) if l == f.wlimbs]
                                             if inplace else []):
                    expect(c.get(x), "%s %s: no case %r (%s)" % (name, fmtname, x, sorted(c)))
                if inplace:
                    expect(stream11(ctx, name, fmtname, n, inplace=True)[0].endswith(
                        " inplace=yes"), "%s: the header of a run in place" % name)
    return "%d runs" % runs


# The planted faults of the folds (refbv.FOLD_VARIANTS): (folds, the class each must fail).  A fold
# not listed must not fail at all.
PLANTED11 = {
    "bv-radius-no-m": [(ADD + SCALE, "V3"), (MULP, "V1"), (MAKE, "makes_ball_vector")],
    "bv-whole-omega": [(BVS, "V3"), (MAKE, "makes_ball_vector")],
    "bv-flag-true": [(BVS + MAKE, "flag")],
    "bv-no-second-pass": [(ADD + SCALE + MULP, "V1"), (MAKE, "makes_ball_vector")],
    "bv-drop-last": [(BVS, "V2"), (MAKE, "makes_ball_vector")],
    "bv-lanes-swap": [(BVS, "V2"), (MAKE, "makes_ball_vector")],
    "bv-spurious-whole": [(BVS, "V4"), (MAKE, "makes_ball_vector")],
    "bv-not-exact": [(NEG + MULP, "exact")],
    "bv-make-negative": [(MAKE, "makes_ball_vector")],
    "bv-make-nan-finite": [(MAKE, "makes_ball_vector")],
    "bvc-drop-term": [(CONV, "V2")],
    "bvc-radius-no-rr": [(CONV, "V3")],
    "bvc-bound-false": [(CONV, "V4")],
    "bvc-flag-true": [(CONV, "flag")],
}


@test
def bv_folds_planted(ctx):
    """Each planted fault of the folds fails, in binary64, in the class where it belongs (a radius
    at the largest magnitude +0: V3, or V1 where the record also gives the flag; the whole space as
    zero centers and the radius Omega: V3; the flag always true: flag; the second pass skipped:
    V1; the last center dropped, two lanes swapped: V2; a spurious whole space: V4; an exact
    radius one step up: exact; a constructor that keeps a negative or a NaN radius:
    makes_ball_vector; a product without its last term or its radius without ry: V2, V3; the
    bound's mask false: V4; the flag of a product always true: flag) and in no fold it does not
    touch."""
    cl = claims8(ctx)
    n = ctx.n(300, 120)
    names = FOLDS11 if not ctx.quick else ("bv_add_1", "bv_sub_2", "bv_scale_2", "bv_neg_1",
                                           "bv_mul_pow2_2", "bv_make_2", "bv_conv_1")
    for variant, groups in PLANTED11.items():
        want = {k: c for folds, c in groups for k in folds}
        for name in names:
            s = judge(run8(stream11(ctx, name, "binary64", n), variant), cl)
            got = classes11(s, name)
            if name in want:
                expect(want[name] in got, "%s on %s fails %s, not %s" % (
                    variant, name, sorted(got) or "nothing", want[name]))
            else:
                expect(not got and totals(s)["failed"] == 0,
                       "%s fails %s, which it does not touch: %s" % (variant, name, sorted(got)))
    expect(set(PLANTED11) == set(refbv.FOLD_VARIANTS), "planted faults without a test: %s"
           % (set(refbv.FOLD_VARIANTS) ^ set(PLANTED11)))
    return "%d faults" % len(PLANTED11)


# Every request of tiny formats: (fold, format, largest length).
# fp:2:-2:1 is binary_float's smallest format of precision 2, where V4 is judged; fp:2:-1:0 and
# fp:3:-2:-1 are of no statement of V4 (bvfolds.v4_range), and V1 to V3 and the flag are judged
# there.
ENUM11 = [("bv_scale_1", "fp:2:-2:1", 1), ("bv_mul_pow2_2", "fp:2:-2:1", 1),
          ("bv_neg_1", "fp:2:-2:1", 2), ("bv_make_2", "fp:2:-2:1", 1),
          ("bv_add_1", "fp:2:-1:0", 1), ("bv_add_2", "fp:3:-2:-1", 0)]
ENUM11_FULL = [("bv_add_1", "fp:2:-2:1", 1), ("bv_sub_1", "fp:2:-2:1", 1),
               ("bv_scale_2", "fp:2:-2:1", 1), ("bv_neg_2", "fp:2:-2:1", 1),
               ("bv_mul_pow2_1", "fp:2:-2:1", 2), ("bv_make_1", "fp:2:-2:1", 2),
               ("bv_neg_2", "fp:2:-2:1", 2), ("bv_add_2", "fp:3:-2:-1", 1)]


@test
def bv_folds_exhaustive(ctx):
    """Every request of tiny formats (every canonical BallVector up to a length, every value of
    the other scalars, every order that differs; every radius and center given of a constructor)
    through the reference runner: nothing fails, nothing is invalid, every index is seen once and
    the count is the generator's; planted faults are caught there too."""
    cl = claims8(ctx)
    cases = ENUM11 + (ENUM11_FULL if not ctx.quick else [])
    n = 0
    for name, fmtname, L in cases:
        g = GM.exhaustive_gen(fold11(ctx, name), F.parse_format(fmtname), L)
        lines = list(g.lines(0, g.total))
        expect(len(lines) == g.total + 2, "%s: %d lines of %d" % (name, len(lines), g.total))
        expect(len(set(lines[1:-1])) == g.total, "%s %s: a request twice" % (name, fmtname))
        s = judge(run8(lines), cl)
        t = totals(s)
        n += g.total
        expect(t["failed"] == 0 and t["invalid"] == 0 and t["suspicious"] == 0
               and t["judged"] == g.total, "%s %s: %s %s" % (
                   name, fmtname, t, [r for st in s.keys.values() for r in st.reasons][:3]))
        c = counts11(s, name)
        f = fold11(ctx, name)
        need = [BF.RES_FINITE, BF.RES_WHOLE] + ([BF.OP_WHOLE] if f.kind != "makes_ball_vector"
                                                else []) + (["order: lanes, W = 2"] if L >= 2
                                                            else [])
        expect(all(c.get(x) for x in need), "%s %s: classes %s" % (name, fmtname, sorted(c)))
        if f.kind != "makes_ball_vector":
            v4 = BF.v4_range(F.parse_format(fmtname))
            expect(bool(c.get(BF.V4_APPLIES)) == v4 and bool(c.get(BF.V4_RANGE)) == (not v4),
                   "%s %s: V4 %s" % (name, fmtname, sorted(k for k in c if "V4" in k)))
    for variant, name, fmtname, L, cls in (("bv-not-exact", "bv_neg_1", "fp:2:-2:1", 1, "exact"),
                                           ("bv-make-negative", "bv_make_1", "fp:2:-2:1", 1,
                                            "makes_ball_vector"),
                                           ("bv-flag-true", "bv_add_1", "fp:2:-1:0", 1, "flag"),
                                           ("bv-drop-last", "bv_scale_1", "fp:2:-2:1", 1, "V2"),
                                           ("bv-spurious-whole", "bv_mul_pow2_2", "fp:2:-2:1", 1,
                                            "V4")):
        g = GM.exhaustive_gen(fold11(ctx, name), F.parse_format(fmtname), L)
        s = judge(run8(list(g.lines(0, g.total)), variant), cl)
        expect(cls in classes11(s, name), "%s on every request of %s: %s" % (
            variant, name, sorted(classes11(s, name))))
    return "%d cases" % n


OM = "0x1.fffffffffffffp+1023"
# Hand-written lines: (line, verdict, class of the failure, [a text of the reason]).  binary64:
# u = 2^-53, the radius of bv_add_1 at least rx + ry + m u (unit(add_1_1)/(1 - unit(add_1_1)) =
# u), V4 claimed where |abs(x+y)+rx+ry| <= 2^(qmax+p-2) = 2^1022.
JUDGE11 = [
    ("bv_add_1 binary64 seq 1 0x1p+0 0x1p+0 0x1p+0 0x1p+0 -> 0x1p+1 0x1.0000000000001p+1 1", "pass",
     None),
    # r = 2 covers [0, 4], but is below rx + ry + 2u.
    ("bv_add_1 binary64 seq 1 0x1p+0 0x1p+0 0x1p+0 0x1p+0 -> 0x1p+1 0x1p+1 1", "fail", "V3"),
    ("bv_add_1 binary64 seq 1 0x1p+0 0x1p+0 0x1p+0 0x1p+0 -> 0x1p+1 0x1p+0 1", "fail", "V2"),
    # A center written that is not RN(x + y), within the radius: the step's claim (V3).
    ("bv_add_1 binary64 seq 1 0x1p+0 0x1p+0 0x1p+0 0x1p+0 -> 0x1.0000000000001p+1 "
     "0x1.0000000000004p+1 1", "fail", "V3"),
    # A center written off the middle: the set [0, 4] reaches 3 below the center 3.
    ("bv_add_1 binary64 seq 1 0x1p+0 0x1p+0 0x1p+0 0x1p+0 -> 0x1.8p+1 0x1p+1 1", "fail", "V2"),
    ("bv_add_1 binary64 seq 1 0x1p+0 0x1p+0 0x1p+0 0x1p+0 -> 0x1p+1 0x1.0000000000001p+1 0", "fail",
     "flag"),
    ("bv_add_1 binary64 seq 1 0x1p+0 0x1p+0 0x1p+0 0x1p+0 -> 0x0p+0 inf 0", "fail", "V4"),
    ("bv_add_1 binary64 seq 1 0x1p+0 0x1p+0 0x1p+0 0x1p+0 -> 0x1p+0 inf 0", "fail", "V1"),
    ("bv_add_1 binary64 seq 1 0x1p+0 inf 0x1p+0 0x0p+0 -> 0x0p+0 inf 0", "pass", None),
    ("bv_add_1 binary64 seq 1 0x1p+0 inf 0x1p+0 0x0p+0 -> 0x1p+0 0x1.0000000000001p+1 1", "fail",
     "V3"),
    # Beyond V4: |2^1022 + 2^1022| = 2^1023 > 2^1022, the whole space claims nothing.
    ("bv_add_1 binary64 seq 1 0x0p+0 0x0p+0 0x1p+1022 0x1p+1022 -> 0x0p+0 inf 0", "pass", None),
    ("bv_add_1 binary64 seq 1 0x0p+0 0x0p+0 0x1p+1021 0x1p+1021 -> 0x0p+0 inf 0", "fail", "V4"),
    # radii_when: rx + ry = 2^1023 > 2^1022, nothing claimed even of no entry.
    ("bv_add_1 binary64 seq 0 0x1p+1022 0x1p+1022 -> inf 0", "pass", None),
    # Below finite_from: bv_add_1 of one entry (+0, +0), radii +0, at precision 1 (fp:1:0:1,
    # binary_float's smallest), whose constant up((1+u)^3) is 4 = 2^emax: the whole space
    # (architecture.md, "From which precision each clause holds").
    ("bv_add_1 fp:1:0:1 seq 1 0x0p+0 0x0p+0 0x0p+0 0x0p+0 -> 0x0p+0 inf 0", "pass", None),
    # No entry: the radius rx + ry at m = +0.
    ("bv_add_1 binary64 seq 0 0x1p+0 0x1p+0 -> 0x1p+1 1", "pass", None),
    ("bv_add_1 binary64 seq 0 0x1p+0 0x1p+0 -> 0x1p+0 1", "fail", "V3"),
    ("bv_add_1 binary64 seq 0 0x1p+0 0x1p+0 -> inf 0", "fail", "V4"),
    # m = 4: the radius at least 4u = 2^-51, exactly.
    ("bv_add_1 binary64 lanes:2 2 0x0p+0 0x0p+0 0x1p+0 0x1p+1 0x1p+0 0x1p+1 -> 0x1p+1 0x1p+2 "
     "0x1p-51 1", "pass", None),
    ("bv_add_1 binary64 lanes:2 2 0x0p+0 0x0p+0 0x1p+0 0x1p+1 0x1p+0 0x1p+1 -> 0x1p+1 0x1p+2 "
     "0x1.fffffffffffffp-52 1", "fail", "V3"),
    # In place: the same verdicts.
    ("bv_add_1 binary64 seq 1 inplace=1 0x1p+0 0x1p+0 0x1p+0 0x1p+0 -> 0x1p+1 "
     "0x1.0000000000001p+1 1", "pass", None),
    ("bv_add_1 binary64 seq 1 inplace=0 0x1p+0 0x1p+0 0x1p+0 0x1p+0 -> 0x1p+1 0x1p+0 1", "fail",
     "V2"),
    # An inplace= that names no array read of the limbs of the array written.
    ("bv_add_1 binary64 seq 1 inplace=2 0x1p+0 0x1p+0 0x1p+0 0x1p+0 -> 0x1p+1 0x1p+2 1", "fail",
     "malformed"),
    ("bv_add_1 binary64 seq 1 inplace=01 0x1p+0 0x1p+0 0x1p+0 0x1p+0 -> 0x1p+1 0x1p+2 1", "fail",
     "malformed"),
    # Operands that are not BallVectors.
    ("bv_add_1 binary64 seq 1 0x1p+0 0x1p+0 inf 0x1p+0 -> 0x0p+0 inf 0", "invalid", None),
    ("bv_add_1 binary64 seq 1 -0x1p+0 0x1p+0 0x1p+0 0x1p+0 -> 0x1p+1 0x1p+2 1", "invalid", None),
    # The negation is exact: the radius rx itself.
    ("bv_neg_1 binary64 seq 1 0x1p+0 0x1p+0 -> -0x1p+0 0x1p+0 1", "pass", None),
    ("bv_neg_1 binary64 seq 1 0x1p+0 0x1p+0 -> -0x1p+0 0x1.0000000000001p+0 1", "fail", "exact"),
    ("bv_neg_1 binary64 seq 1 0x1p+0 0x1p+0 -> 0x1p+0 0x1p+0 1", "fail", "V2"),
    ("bv_neg_2 binary64 seq 1 0x1p+0 0x1p+0 0x1p-60 -> -0x1p+0 -0x1p-60 0x1p+0 1", "pass", None),
    ("bv_neg_1 binary64 seq 1 %s %s -> -%s %s 1" % (OM, OM, OM, OM), "pass", None),
    # A scaling by 2^-1, exact where x c and rx c are zero or above eta/(2u) = 2^-1022.
    ("bv_mul_pow2_1 binary64 seq 1 0x1p+0 0x1p-1 0x1p+0 -> 0x1p-1 0x1p-1 1", "pass", None),
    ("bv_mul_pow2_1 binary64 seq 1 0x1p+0 0x1p-1 0x1p+0 -> 0x1p-1 0x1.0000000000001p-1 1", "fail",
     "exact"),
    ("bv_mul_pow2_1 binary64 seq 1 0x1p+0 0x1.8p+0 0x1p+0 -> 0x1.8p+0 0x1.8p+0 1", "invalid",
     None),
    # The constructors: the radius and the centers given, or the whole space.
    ("bv_make_1 binary64 seq 1 0x1p+0 0x1p+0 -> 0x1p+0 0x1p+0 1", "pass", None),
    ("bv_make_1 binary64 seq 1 -0x1p+0 0x1p+0 -> 0x0p+0 inf 0", "pass", None),
    ("bv_make_1 binary64 seq 1 -0x1p+0 0x1p+0 -> 0x1p+0 0x1p+0 1", "fail", "makes_ball_vector"),
    ("bv_make_1 binary64 seq 1 0x1p+0 inf -> 0x0p+0 inf 0", "pass", None),
    ("bv_make_1 binary64 seq 1 0x1p+0 0x1p+0 -> 0x1p+0 0x1.0000000000001p+0 1", "fail",
     "makes_ball_vector"),
    ("bv_make_1 binary64 seq 1 -0x0p+0 0x1p+0 -> 0x1p+0 0x0p+0 1", "pass", None),
    ("bv_make_1 binary64 seq 1 nan 0x1p+0 -> 0x0p+0 inf 0", "pass", None),
    ("bv_make_1 binary64 seq 1 inf 0x1p+0 -> 0x0p+0 inf 0", "pass", None),
    ("bv_make_1 binary64 seq 1 -inf 0x1p+0 -> 0x0p+0 inf 0", "pass", None),
    ("bv_make_2 binary64 seq 1 0x1p+0 0x1p+0 0x1p-60 -> 0x1p+0 0x1p-60 0x1p+0 1", "pass", None),
    ("bv_make_2 binary64 seq 1 0x1p+0 0x1p+0 0x1p-60 -> 0x1p+0 0x0p+0 0x1p+0 1", "fail",
     "makes_ball_vector"),
    # A product of one entry each: the radius at least g (1+u)^2 + t, g = u for one term.
    ("bv_conv_1 binary64 seq 1 1 0x0p+0 0x0p+0 0x1p+0 0x1p+0 -> 0x1p+0 0x1p-52 1", "pass", None),
    ("bv_conv_1 binary64 seq 1 1 0x0p+0 0x0p+0 0x1p+0 0x1p+0 -> 0x1p+0 0x1p-53 1", "fail", "V3"),
    ("bv_conv_1 binary64 seq 1 1 0x0p+0 0x0p+0 0x1p+0 0x1p+0 -> 0x1p+1 0x1p-52 1", "fail", "V2"),
    ("bv_conv_1 binary64 seq 1 1 0x0p+0 0x0p+0 0x1p+0 0x1p+0 -> 0x0p+0 inf 0", "fail", "V4"),
    ("bv_conv_1 binary64 seq 1 1 0x0p+0 0x0p+0 0x1p+0 0x1p+0 -> 0x1p+0 inf 0", "fail", "V1"),
    ("bv_conv_1 binary64 seq 1 1 0x0p+0 0x0p+0 0x1p+0 0x1p+0 -> 0x1p+0 -0x1p-52 1", "fail", "V1"),
    ("bv_conv_1 binary64 seq 1 1 0x0p+0 inf 0x1p+0 0x0p+0 -> 0x0p+0 inf 0", "pass", None),
    ("bv_conv_1 binary64 seq 0 1 0x0p+0 0x0p+0 0x1p+0 -> 0x0p+0 1", "pass", None),
    # V4 outside the formats its statements quantify over (bvfolds.v4_range): fp:2:-1:0 (e_max =
    # 1 < p), whose radius kernel's constant up((1+u)((1+u)^2 eta + eta/2) + eta/(2u)) is 3 =
    # Omega: rx = 1/2 gives RN(1/2 * 2 + 3) = +inf, the whole space, which V4 does not forbid
    # there; fp:2:-1:1 (eta = 1/2, above binary_float's 1/4): the constant 3, RN(1 + 3) = 4 finite,
    # nothing claimed either.  In fp:2:-2:1, binary_float's smallest format of precision 2, the
    # constant is up(1.14...) = 3/2, RN(1/2 * 2 + 3/2) = 2 (a tie, to even), and the whole space
    # fails V4 (1/2 <= 2^(q_max+p-2) = 2).
    ("bv_add_1 fp:2:-1:0 seq 0 0x1p-1 0x0p+0 -> inf 0", "pass", None),
    ("bv_add_1 fp:2:-1:1 seq 0 0x1p-1 0x0p+0 -> inf 0", "pass", None),
    ("bv_add_1 fp:2:-2:1 seq 0 0x1p-1 0x0p+0 -> 0x1p+1 1", "pass", None),
    ("bv_add_1 fp:2:-2:1 seq 0 0x1p-1 0x0p+0 -> inf 0", "fail", "V4"),
    # fp:2:-3:1, a wider subnormal range than binary_float's (q_min = -3 < 3 - 1 - 4): V4 is
    # judged there, and its failure says that it is a finding, not a violated claim (the owner's
    # ruling of 2026-11-21); in fp:2:-2:1, of binary_float's shape, it does not.  The
    # interpreter's line is 0x1p+1 1 in both.
    ("bv_add_1 fp:2:-3:1 seq 0 0x1p-1 0x0p+0 -> 0x1p+1 1", "pass", None),
    ("bv_add_1 fp:2:-3:1 seq 0 0x1p-1 0x0p+0 -> inf 0", "fail", "V4", "a finding to report"),
]


def _conv_zero_line(n, radius, ny=None, fmtname="fp:8:-14:1"):
    """bv_conv_2 on two operands of n (and ny) entries (+0, +0), radii +0, and the output given:
    the whole space for radius None, otherwise zero coefficients, that radius and the flag true.
    fp:8:-14:1 is precision 8 with e_max = 9 (q_max = e_max - p = 1, q_min = 3 - e_max - p = -14),
    whose largest number is 510 (oracle/README.md, "Ball vectors and the accumulator")."""
    ny = n if ny is None else ny
    req = ["bv_conv_2", fmtname, "seq", str(n), str(ny), "0x0p+0", "0x0p+0"] + ["0x0p+0"] * (
        2 * (n + ny))
    coeff = max(0, n + ny - 1) if n and ny else 0
    out = ["0x0p+0"] * (2 * coeff) + (["inf", "0"] if radius is None else [radius, "1"])
    return " ".join(req + ["->"] + out)


@test
def bv_folds_judge(ctx):
    """Hand-written lines of the folds of the ball vectors, each verdict worked out by hand: the
    radius at and below its kernel's stated value, below the set, the flag false beside a finite
    radius, the whole space where V4 claims a finite result and beyond it, a whole space with a
    center, a whole-space operand, no entry, the lanes, in place, operands that are not
    BallVectors; the exactness of a negation and of a scaling; each case of a constructor; a
    product of one entry each.  And count_when as an expression, the regression of its
    restatement: in fp:8:-14:1 (precision 8, e_max = 9: the largest number is 510), with both
    operands of n entries (+0, +0) and radii +0, unit(mul_2_2) = 4u^2 = 2^-14 and eta/(2u) = 2^-7.
    The claim as it stands, n (unit(mul_2_2) + eta/(2u)) <= 1/16, admits n up to 7; the old
    expression, n (unit(mul_2_2) + eta) <= 1/16, up to 512, beyond the largest number.  The
    interpreter gives the whole space at 511 (the count 511 rounds up to 512, beyond 510, and the
    bound of dot is not given) and at 512, the radius 0x1.18p+3 at 510 and 0x1.d8p-4 at 7: the
    whole space at 511 fails V4 under the old expression and passes under the claim as it stands;
    a finite result passes under both; the whole space at 7, which both admit, fails under both,
    and at 8 only under the old."""
    cl = claims8(ctx)
    n = 0
    for case in JUDGE11:
        line, want, cls = case[:3]
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
        elif cls == "malformed":
            ok = t["failed"] == 1 and "malformed" in reasons
        else:
            ok = t["failed"] == 1 and cls in classes11(s, name)
        expect(ok, "%s: %s, expected %s%s (%s; classes %s)" % (
            line, t, want, " in " + cls if cls else "", reasons, sorted(classes11(s, name))))
        n += 1
    raw = raw8()
    cw = _fold_raw(raw, "bv_conv_2")["ensures"][0]["count_when"]
    expect(cw == [{"le": "n*(unit(mul_2_2)+eta/(2*u))", "than": "1/16"}],
           "the fixture's count_when is not the claim as it stands: %s" % cw)
    old = copy.deepcopy(raw)
    _fold_raw(old, "bv_conv_2")["ensures"][0]["count_when"] = [
        {"le": "n*(unit(mul_2_2)+eta)", "than": "1/16"}]
    alt = Claims(old, FIXTURE8)
    expect(not alt.broken, "the claims with the old count_when: %s" % alt.broken)
    # (line, passes under the claim as it stands, passes under the old expression).  The count
    # is min(n_x, n_y): 511 and 1 entries give the count 1, of which both hold.
    for line, base_ok, alt_ok in ((_conv_zero_line(511, None), True, False),
                                  (_conv_zero_line(512, None), True, False),
                                  (_conv_zero_line(510, "0x1.18p+3"), True, True),
                                  (_conv_zero_line(510, None), True, False),
                                  (_conv_zero_line(7, "0x1.d8p-4"), True, True),
                                  (_conv_zero_line(7, None), False, False),
                                  (_conv_zero_line(8, None), True, False),
                                  (_conv_zero_line(511, None, 1), False, False)):
        for c, ok in ((cl, base_ok), (alt, alt_ok)):
            s = judge([line], c)
            t = totals(s)
            got = t["passed"] == 1 if ok else (t["failed"] == 1 and
                                               "V4" in classes11(s, "bv_conv_2"))
            expect(got, "bv_conv_2 of %s entries, %s, under %s: %s %s" % (
                line.split()[3], "whole" if line.endswith("inf 0") else "finite",
                "the claim as it stands" if c is cl else "the old count_when", t,
                sorted(classes11(s, "bv_conv_2"))))
            n += 1
    return "%d lines" % n


@test
def gen_bv_folds(ctx):
    """The generator of the ball vectors (genbv.py): case i alone is case i of its run, the seed
    matters, every case satisfies the requirements (none invalid), every stratum the header lists
    has cases, its strata are those of the fold's shape; in place, every request carries inplace=I
    over the arrays that can be written, and the folds without an in-place form refuse it; the
    count stratum of a product, in its toy format, reaches count_when on both sides; the stratum
    whole has an operand of radius +inf, zeroradius a radius +0."""
    cl = claims8(ctx)
    n = ctx.n(300, 120)
    for name in FOLDS11:
        f = fold11(ctx, name)
        for fmtname in formats11(ctx, name)[::2]:
            fmt = F.parse_format(fmtname)
            g = GM.random_gen(f, fmt, "genbv", None, None, 12)
            lines = list(g.lines(0, n))
            expect(GM.random_gen(f, fmt, "genbv", None, None, 12).case(n // 2) ==
                   lines[1 + n // 2], "%s: case i alone differs" % name)
            other = GM.random_gen(f, fmt, "other", None, None, 12)
            expect(any(other.case(i) != lines[1 + i] for i in range(20)), "%s: the seed" % name)
            tags = {ln.rsplit("#", 1)[1].split(":")[0] for ln in lines[1:-1]}
            st, _sc = GB.strata_of(f)
            expect(set(st) == tags, "%s %s: strata %s, cases of %s" % (name, fmtname, st, tags))
            s = judge(run8(lines), cl)
            expect(totals(s)["invalid"] == 0, "%s: invalid cases %s" % (name, totals(s)))
            for ln in lines[1:-1]:
                tag = ln.rsplit("#", 1)[1].split(":")[0]
                if tag in ("whole", "zeroradius") and name not in MAKE:
                    toks = ln.split(" #")[0].split(" ")
                    first = 5 if name in CONV else 4
                    radii = [toks[first + j] for j, (sn, _l) in enumerate(f.scalars)
                             if sn in getattr(f, "radii", (sn,))]
                    want = "inf" if tag == "whole" else "0x0p+0"
                    expect(want in radii or (tag == "zeroradius" and "-0x0p+0" in radii),
                           "%s %s: %s" % (name, tag, ln[:120]))
        if name not in CONV:
            g = GM.random_gen(f, F.parse_format("binary64"), "genbv", None, None, 12, inplace=True)
            lines = list(g.lines(0, 60))
            ws = [i for i, (_a, l) in enumerate(f.arrays) if l == f.wlimbs]
            seen = {ln.split(" ")[4] for ln in lines[1:-1]}
            expect(seen == {"inplace=%d" % i for i in ws}, "%s: in place %s" % (name, seen))
        else:
            try:
                GM.random_gen(f, F.parse_format("binary64"), "genbv", None, None, 12,
                              inplace=True)
                expect(False, "%s: a run in place was not refused" % name)
            except Exception as ex:  # noqa: BLE001 (GenError)
                expect("in-place" in str(ex), "%s: %s" % (name, ex))
    s = judge(run8(stream11(ctx, "bv_conv_2", TOY_CONV, ctx.n(300, 150), strata=("count",),
                            max_length=64)), cl)
    c = counts11(s, "bv_conv_2")
    expect(c.get(BF.V4_APPLIES) and any(k.startswith("count_when fails") for k in c),
           "the count stratum: %s" % sorted(c))
    return "%d folds" % len(FOLDS11)


@test
def merging_bv_folds(ctx):
    """The merge of the summaries of two halves of streams of the folds of the ball vectors is the
    summary of the whole."""
    cl = claims8(ctx)
    from . import check as C
    parts = [run8(stream11(ctx, k, "binary64", ctx.n(150, 60)))
             for k in ("bv_add_2", "bv_make_1", "bv_conv_1", "bv_mul_pow2_2")]
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


# Maps in place (architecture.md, "The line protocol": inplace=I), with the fixture of the maps
# (selftest9.py).
MAPS_INPLACE = ("add_2", "axpy_2_1", "scale_1", "mul_pow2_map_2", "add_1_entry", "axpy_1")


@test
def maps_inplace(ctx):
    """The maps' requests in place (gen --inplace): every request carries inplace=I, I in turn over
    the arrays of the limbs of the array written; the reference runner on them passes, every
    array is counted in place; a map without arrays to write refuses nothing it has; inplace= of
    an array beyond the arrays, of other limbs, or not a number, is a malformed line; a fold that
    is not a map or a ball vector refuses --inplace."""
    from . import selftest9 as S9
    from .claims import load_claims
    from . import gen as G
    cl = load_claims(S9.FIXTURE7)
    n = ctx.n(200, 100)
    for name in MAPS_INPLACE if not ctx.quick else MAPS_INPLACE[:3]:
        f = cl.get_fold(name)
        g = GM.random_gen(f, F.parse_format("binary64"), "inplace", None, None, 12, inplace=True)
        lines = list(g.lines(0, n))
        expect(lines[0].endswith(" inplace=yes"), "%s: the header %s" % (name, lines[0]))
        ws = [i for i, (_a, l) in enumerate(f.arrays) if l == f.wlimbs]
        seen = {ln.split(" ")[4] for ln in lines[1:-1]}
        expect(seen == {"inplace=%d" % i for i in ws}, "%s: in place %s" % (name, seen))
        s = judge(S9.run6(lines), cl)
        t = totals(s)
        expect(t["failed"] == 0 and t["invalid"] == 0 and t["judged"] == n, "%s: %s" % (name, t))
        c = {}
        for _lab, d in entry_stats(s, name).items():
            for k, v in d[3].items():
                c[k] = c.get(k, 0) + v
        for i in ws:
            expect(c.get("in place: array %d" % i), "%s: array %d not counted in place (%s)" % (
                name, i, sorted(k for k in c if "place" in k)))
    one = "add_1 binary64 seq 1 %s0x1p+0 0x1p+0 -> 0x1p+1 1"
    s = judge([one % "inplace=1 "], cl)
    expect(totals(s)["passed"] == 1, "add_1 in place: %s" % totals(s))
    for bad in ("inplace=2 ", "inplace=x ", "inplace=-1 "):
        s = judge([one % bad], cl)
        reasons = " ".join(r for st in s.keys.values() for r in st.reasons)
        expect(totals(s)["failed"] == 1 and "malformed" in reasons, "add_1 %s: %s %s" % (
            bad, totals(s), reasons))
    try:
        GM.random_gen(cl.get_fold("norm_upper_1"), F.parse_format("binary64"), "x", None, None,
                      12, inplace=True)
        expect(False, "a fold of maxima in place was not refused")
    except G.GenError as ex:
        expect("in-place" in str(ex), "the refusal: %s" % ex)
    return "%d maps" % len(MAPS_INPLACE)
