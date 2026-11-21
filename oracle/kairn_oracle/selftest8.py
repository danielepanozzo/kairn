"""The oracle's own tests for the interval kernels (architecture.md, "Claims of the interval kernels"
and "... two limbs and the enclosure interface"; milestone2.md, "Interval kernels" and "One
enclosure interface"): the requirements interval() and not_nan(), the kinds outward,
makes_interval, encloses_interval, set_bound, interval_set, ball_of_interval, interval_of_ball and
splits, encloses with no ball, makes_ball from an interval, zero_factor, the constants of a claim
with up( ), and the reading of an entry about an output group other than the first.

As for the earlier waves, each test compares the oracle with something it does not share code
with: the constants against the reference runner's own constants E, G, H (refrun.radius2_exact) and
the closed forms of milestone2.md; the reference runner, written from the listings of
milestone2.md, on random streams and on every case of tiny formats; planted faults that must be
caught in the entry where they belong and in no kernel that does not use them; hand-written lines
whose verdicts are worked out by hand.  The fixture, oracle/selftest/claims-wave6.json, holds the
33 kernels and add_2_2 and mul_2_2, whose bounds their constants name, frozen from the claims of
2026-11-20.
"""

import concurrent.futures as cf
import copy
import json
import os
import random
from fractions import Fraction as Q

from . import check as C
from . import fmt as F
from . import gen as G
from . import gen6
from . import intervals as IV
from . import refrun
from .claims import Claims, ClaimsError, load_claims
from .selftest import test, expect, judge, totals, ORACLE_DIR

FIXTURE6 = os.path.join(ORACLE_DIR, "selftest", "claims-wave6.json")
KERNELS = ("mul_dir_1", "interval_make_1", "interval_neg_1", "interval_add_1", "interval_sub_1",
           "interval_mul_1", "add_ball_2_2", "mul_ball_2_2", "add_down_2_2", "add_up_2_2",
           "sub_down_2_2", "sub_up_2_2", "mul_dir_2_2", "ball_lower_as_1", "ball_upper_as_1",
           "ball_lower_as_2", "ball_upper_as_2", "ball_narrow_2_1", "ball_from_interval_2",
           "interval_add_2", "interval_neg_2", "interval_sub_2", "interval_make_2", "mul_ext_2_2",
           "interval_mul_2", "interval_hull_1", "interval_hull_2", "interval_intersection_1",
           "interval_intersection_2", "interval_mid_rad_1", "interval_to_ball_1",
           "ball_to_interval_1", "interval_split_1")
# Formats of the shape of the extended domain, and at least each kernel's min_precision (4).
FORMATS = ("binary64", "binary32", "fp:4:-6:1")
SUMS = ("add_down_2_2", "add_up_2_2", "sub_down_2_2", "sub_up_2_2")
TWO_LIMB_BOUNDS = SUMS + ("mul_dir_2_2", "interval_add_2", "interval_sub_2", "mul_ext_2_2",
                          "interval_mul_2")
BALL_BOUNDS = ("ball_lower_as_1", "ball_upper_as_1", "ball_lower_as_2", "ball_upper_as_2")
# The planted faults of refrun (VARIANTS "iv-..."): the kernels where each must be caught, with the
# kinds of the entries it may fail there (and nowhere else), and the formats where it must be
# caught (the others: it may go unseen, never flagged elsewhere).
PLANTED = {
    "iv-sum-nearest": ({"interval_add_1": {"encloses_interval"},
                        "interval_sub_1": {"encloses_interval"}}, FORMATS),
    "iv-empty-whole": ({k: {"encloses_interval"} for k in ("interval_add_1", "interval_sub_1",
                                                          "interval_mul_1")}, FORMATS),
    "iv-mul-zero-nan": ({"mul_dir_1": {"bound", "rounded"},
                         "interval_mul_1": {"encloses_interval"}}, FORMATS),
    "iv-mul-step-large": ({"mul_dir_1": {"rounded"}, "interval_mul_1": {"encloses_interval"}},
                          FORMATS),
    "iv-neg-not-swapped": ({"interval_neg_1": {"encloses_interval"},
                            "interval_neg_2": {"encloses_interval"}}, FORMATS),
    # The constructors under the rule of 2026-11-20: a NaN bound or the same infinity twice gives
    # the whole line, reversed bounds the empty set.
    "iv-make-nan-empty": ({"interval_make_1": {"makes_interval"},
                           "interval_make_2": {"makes_interval"}}, FORMATS),
    "iv-make-inf-empty": ({"interval_make_1": {"makes_interval"},
                           "interval_make_2": {"makes_interval"}}, FORMATS),
    "iv-make-reversed": ({"interval_make_1": {"makes_interval"},
                          "interval_make_2": {"makes_interval"}}, FORMATS),
    "iv-make-reversed-whole": ({"interval_make_1": {"makes_interval"},
                                "interval_make_2": {"makes_interval"}}, FORMATS),
    "iv2-make-reversed-lead": ({"interval_make_2": {"makes_interval"}}, FORMATS),
    "iv2-no-zero-rule": (dict({k: {"outward"} for k in SUMS},
                              interval_add_2={"encloses_interval"},
                              interval_sub_2={"encloses_interval"}), FORMATS),
    "iv2-wrong-side": (dict({k: {"outward"} for k in SUMS + ("mul_dir_2_2", "mul_ext_2_2")},
                            **{k: {"encloses_interval"} for k in ("interval_add_2",
                                                                  "interval_sub_2",
                                                                  "interval_mul_2")}), FORMATS),
    "iv2-wide": (dict({k: {"outward"} for k in SUMS + ("mul_dir_2_2", "mul_ext_2_2")},
                      **{k: {"encloses_interval"} for k in ("interval_add_2", "interval_sub_2",
                                                            "interval_mul_2")}), FORMATS),
    "iv2-keep-nonfinite": ({"interval_add_2": {"encloses_interval"},
                            "interval_sub_2": {"encloses_interval"}}, FORMATS),
    "iv-mulext-inf-sign": ({"mul_ext_2_2": {"outward"}, "interval_mul_2": {"encloses_interval"}},
                           FORMATS),
    "iv-hull-as-intersection": ({"interval_hull_1": {"interval_set"},
                                 "interval_hull_2": {"interval_set"}}, FORMATS),
    "iv-intersection-no-empty": ({"interval_intersection_1": {"interval_set"},
                                  "interval_intersection_2": {"interval_set"}}, FORMATS),
    "iv-mid-no-move": ({"interval_mid_rad_1": {"ball_of_interval"},
                        "interval_to_ball_1": {"ball_of_interval"},
                        "interval_split_1": {"splits"}}, FORMATS),
    "iv-mid-radius-small": ({"interval_mid_rad_1": {"ball_of_interval"},
                             "interval_to_ball_1": {"ball_of_interval"}}, FORMATS),
    "iv-mid-radius-large": ({"interval_mid_rad_1": {"ball_of_interval"},
                             "interval_to_ball_1": {"ball_of_interval"}}, FORMATS),
    "iv-tball-halfline": ({"interval_to_ball_1": {"ball_of_interval"}}, FORMATS),
    "iv-split-gap": ({"interval_split_1": {"splits"}}, FORMATS),
    "iv-ballbound-nearest": ({k: {"set_bound"} for k in BALL_BOUNDS}, FORMATS),
    "iv-ballbound-empty-nan": ({k: {"set_bound"} for k in BALL_BOUNDS}, FORMATS),
    "iv-fromint-no-step": ({"ball_from_interval_2": {"makes_ball"}}, FORMATS),
    "iv-fromint-nan-empty": ({"ball_from_interval_2": {"makes_ball"}}, FORMATS),
    "iv-fromint-inf-empty": ({"ball_from_interval_2": {"makes_ball"}}, FORMATS),
    "iv-fromint-reversed-whole": ({"ball_from_interval_2": {"makes_ball"}}, FORMATS),
    "iv-narrow-no-tail": ({"ball_narrow_2_1": {"encloses"}}, FORMATS),
    # d = H is enough for a sum whose error is below the smallest normal number: in a format of
    # few exponents (fp:4:-6:1) every sum is so; the two-limb bounds built on it may fail too.
    "iv-ball-no-term": (dict({"add_ball_2_2": {"encloses"}, "mul_ball_2_2": {"encloses"}},
                             **{k: {"outward", "encloses_interval"} for k in TWO_LIMB_BOUNDS}),
                        ("binary64", "binary32")),
    "iv-to-interval-nearest": ({"ball_to_interval_1": {"interval_of_ball"}}, FORMATS),
}
# Where a fault is rare in the default strata, the strata that reach it (still from the
# generator's own families).
PLANTED_STRATA = {"iv-mid-no-move": "point,step,oddeta", "iv-tball-halfline": "special",
                  "iv-fromint-no-step": "oddeta", "iv-ballbound-empty-nan": "ballstates"}


def claims6(ctx):
    if not hasattr(ctx, "claims6"):
        ctx.claims6 = load_claims(FIXTURE6)
    return ctx.claims6


def raw6():
    with open(FIXTURE6, encoding="utf-8") as fh:
        return json.load(fh)


def run6(lines, variant="correct"):
    r = refrun.Runner(variant)
    out = []
    for ln in lines:
        out.extend(r.complete(ln))
    return out


def stream6(ctx, kernel, fmtname, count, strata=None, seed="selftest8"):
    key = ("w6", kernel, fmtname, count, strata, seed)
    s = ctx._streams.get(key)
    if s is None:
        g = G.RandomGen(claims6(ctx).get(kernel), F.parse_format(fmtname), seed,
                        strata.split(",") if strata else None)
        s = ctx._streams[key] = list(g.lines(0, count))
    return s


def entry_stats(summary, name):
    """{label: [kind, applicable, failures, counts, maxima]} of a kernel, summed over its keys."""
    out = {}
    for (k, _f, _t), st in summary.keys.items():
        if k != name:
            continue
        for e in st.entries:
            d = out.setdefault(e.label, [e.kind, 0, 0, {}, {}])
            d[1] += e.applicable
            d[2] += e.failures
            for c, n in e.counts.items():
                d[3][c] = d[3].get(c, 0) + n
            for c, (r, _l) in e.maxima.items():
                if r[1] and (c not in d[4] or Q(*r) > d[4][c]):
                    d[4][c] = Q(*r)
    return out


def failing_kinds(summary, name):
    return {d[0] for d in entry_stats(summary, name).values() if d[2]}


# ---------------------------------------------------------------------------

@test
def claims_reading_wave6(ctx):
    """The fixture of the interval kernels reads whole, its new requirements and kinds as
    architecture.md writes them; malformed kernels are set aside with a reason, without making the
    others unreadable."""
    cl = claims6(ctx)
    expect(not cl.broken, "the fixture does not read: %s" % cl.broken)
    expect(sorted(cl.kernels) == sorted(KERNELS + ("add_2_2", "mul_2_2")), "kernels read")
    expect(cl.get("interval_add_2").interval_requires == [("xl", "xu"), ("yl", "yu")],
           "interval() of interval_add_2")
    expect(("not_nan", "x") in cl.get("mul_ext_2_2").requires, "not_nan() of mul_ext_2_2")
    e = cl.get("interval_mul_1").ensures[0]
    expect((e.tight, e.steps, e.when, e.bounded_exactly) == ("rounded", 1, "product_large", True),
           "tight of interval_mul_1")
    e = cl.get("interval_add_2").ensures[0]
    expect(e.tight == "outward" and sorted(e.tight_exact) == ["lower", "upper"]
           and e.bounded_when == [("exp", -2)] and not e.bounded_exactly,
           "tight outward and bounded_when of interval_add_2")
    expect(cl.get("interval_mul_2").ensures[0].zero_factor, "zero_factor of interval_mul_2")
    expect(cl.get("mul_dir_1").ensures[0].zero_factor and cl.get("mul_dir_1").ensures[1].zero_factor,
           "zero_factor of mul_dir_1")
    expect(cl.get("ball_from_interval_2").ensures[0].midpoint_when == ["lo", "hi"],
           "midpoint_when")
    expect(cl.get("add_ball_2_2").ensures[2].balls == {}, "encloses with no ball")
    raw = raw6()
    ks = {k["name"]: k for k in raw["kernels"]}

    def kern(name, f):
        k = copy.deepcopy(ks[name])
        f(k)
        return k

    def ens(i, **kw):
        return lambda k: k["ensures"][i].update(kw)

    def drop(i, key):
        return lambda k: k["ensures"][i].pop(key)

    def tight(i, **kw):
        return lambda k: k["ensures"][i]["tight"].update(kw)

    bad = [
        # Requirements.
        kern("interval_add_1", lambda k: k.update(requires=["interval(xl, xl)", "interval(yl, yu)"])),
        kern("interval_add_1", lambda k: k.update(requires=["interval(xl, yl)", "interval(yl, yu)"])),
        kern("interval_add_1", lambda k: k.update(requires=["interval(xl, xu)"])),
        kern("interval_add_1", lambda k: k.update(domain="finite")),
        kern("interval_add_2", lambda k: k["inputs"][1].update(limbs=1)),
        kern("mul_ext_2_2", lambda k: k.update(requires=["canonical(x)", "canonical(y)",
                                                          "not_nan(x)", "not_nan(x)"])),
        kern("mul_ext_2_2", lambda k: k.update(requires=["canonical(y)", "not_nan(x)",
                                                          "not_nan(y)"])),
        kern("mul_dir_1", lambda k: k.update(requires=["not_nan(a)", "not_nan(q)"])),
        kern("ball_to_interval_1", lambda k: k["requires"].append("interval(c, r)")),
        # outward.
        kern("add_down_2_2", ens(1, side="inward")),
        kern("add_down_2_2", ens(1, of="z")),
        kern("add_down_2_2", ens(1, rel="up(u")),
        kern("add_down_2_2", ens(1, rel="up(x)")),
        kern("add_down_2_2", ens(1, rel="unit(no_kernel)")),
        kern("add_down_2_2", ens(1, rel="2^(1/2)")),
        kern("add_down_2_2", ens(1, abs="-eta")),
        kern("add_down_2_2", ens(1, exact_when=[])),
        kern("add_down_2_2", ens(1, exact_when=[{"zero": "x+q"}])),
        kern("add_down_2_2", ens(1, exact_when=[{"zero": "x", "than": "1"}])),
        kern("add_down_2_2", ens(1, zero_factor=True)),
        kern("add_down_2_2", drop(1, "abs")),
        kern("mul_ext_2_2", ens(2, zero_factor=False)),
        # encloses_interval.
        kern("interval_add_1", ens(0, set="x+x")),
        kern("interval_add_1", ens(0, set="abs(x)+y")),
        kern("interval_add_1", ens(0, set="x+y+xl")),
        kern("interval_add_1", ens(0, intervals={"x": {"lower": "xl", "upper": "yu"},
                                                 "y": {"lower": "yl", "upper": "yu"}})),
        kern("interval_add_1", ens(0, intervals={"xl": {"lower": "xl", "upper": "xu"},
                                                 "y": {"lower": "yl", "upper": "yu"}})),
        kern("interval_add_1", tight(0, kind="tightest")),
        kern("interval_add_1", tight(0, steps=-1)),
        kern("interval_add_1", tight(0, when="product_large")),
        kern("interval_add_1", ens(0, bounded_when=[{"abs_le": "x-y", "omega": True}])),
        kern("interval_add_1", ens(0, bounded_when=[{"abs_le": "x+y", "omega": False}])),
        kern("interval_add_1", ens(0, bounded_when=[{"abs_le": "x+y", "exp": 1.5}])),
        kern("interval_add_1", ens(0, bounded_exactly=False)),
        kern("interval_add_1", ens(0, zero_factor=True)),
        kern("interval_add_1", ens(0, lower="zu")),
        kern("interval_add_1", drop(0, "bounded_when")),
        kern("interval_add_2", tight(0, kind="rounded")),
        kern("interval_add_2", tight(0, exact_when={"lower": [{"zero": "xl+yl"}],
                                                    "middle": []})),
        kern("interval_add_2", tight(0, exact_when=[{"zero": "xl+yl"}])),
        # The other kinds.
        kern("interval_make_1", ens(0, **{"from": {"lower": "lo", "upper": "lo"}})),
        kern("interval_make_2", lambda k: k.update(requires=["canonical(lo)"])),
        kern("ball_lower_as_1", ens(0, side="left")),
        kern("ball_lower_as_1", ens(0, balls={"x": {"center": "c", "radius": "q"}})),
        kern("ball_lower_as_1", ens(0, tight={"kind": "outward"})),
        kern("interval_hull_1", ens(0, set="join")),
        kern("interval_hull_1", ens(0, intervals={"x": {"lower": "xl", "upper": "xu"}})),
        kern("interval_mid_rad_1", ens(0, special="1788")),
        kern("interval_mid_rad_1", ens(0, rel="v")),
        kern("interval_mid_rad_1", ens(0, smallest_radius="yes")),
        kern("interval_mid_rad_1", ens(0, radius="m")),
        kern("ball_to_interval_1", drop(0, "tight")),
        kern("interval_split_1", ens(0, parts=[{"lower": "al", "upper": "au"}])),
        kern("interval_split_1", ens(0, parts=[{"lower": "al", "upper": "au"},
                                               {"lower": "al", "upper": "bu"}])),
        kern("ball_from_interval_2", ens(0, midpoint_when=[{"half_in_format": "r"}])),
        kern("ball_from_interval_2", ens(0, midpoint_when=[])),
        kern("mul_dir_1", ens(0, zero_factor="true")),
        kern("mul_dir_1", lambda k: k.update(domain="finite", requires=[])),
        kern("add_ball_2_2", lambda k: k.update(domain="extended", requires=["canonical(x)",
                                                                              "canonical(y)"])),
        # The same with the finite_when the extended domain asks of encloses: refused for the
        # balls {} alone.
        kern("add_ball_2_2", lambda k: (k.update(domain="extended",
                                                 requires=["canonical(x)", "canonical(y)"]),
                                        k["ensures"][2].update(finite_when=[]))),
    ]
    data = copy.deepcopy(raw)
    for i, k in enumerate(bad):
        k["name"] = "bad_kernel_%d" % i
        data["kernels"].append(k)
    cl2 = Claims(data, "<malformed>")
    for i in range(len(bad)):
        expect("bad_kernel_%d" % i in cl2.broken, "malformed kernel %d read: %s %s" % (
            i, json.dumps(bad[i]["requires"]), json.dumps(bad[i]["ensures"])[:300]))
    for k in ks:
        expect(cl2.get(k) is not None, "%s became unreadable: %s" % (k, cl2.broken.get(k)))
    # A constant whose unit( ) names a kernel that cannot be read sets its kernel aside with it.
    data = copy.deepcopy(raw)
    for k in data["kernels"]:
        if k["name"] == "add_2_2":
            k["ensures"][1]["form"] = "Z"
    cl3 = Claims(data, "<add_2_2 broken>")
    expect(all(k in cl3.broken for k in SUMS + ("interval_add_2",))
           and cl3.get("mul_dir_2_2") is not None,
           "unit(add_2_2) of a broken add_2_2 read: %s" % sorted(cl3.broken))
    # midpoint_when on a ball made from a center and a radius is refused.
    data = {"schema": 1, "kernels": [{
        "name": "m", "domain": "extended", "inputs": [{"name": "c", "limbs": 1},
                                                      {"name": "r", "limbs": 1}],
        "outputs": [{"name": "cw", "limbs": 1}, {"name": "rw", "limbs": 1}], "requires": [],
        "ensures": [{"kind": "makes_ball", "center": "cw", "radius": "rw",
                     "from": {"center": "c", "radius": "r"}, "midpoint_when": [
                         {"half_in_format": "c"}]}], "ieee_status": "unverified"}]}
    expect("m" in Claims(data, "<m>").broken, "midpoint_when of a ball from c and r read")
    return "%d malformed kernels set aside" % len(bad)


def _closed_form(p, qmin, kname):
    """A and B of milestone2.md, "Bounds of two limbs", from refrun's own E, G, H (exact, rounded
    up to the format by refrun) and the center's rel and tiny."""
    A_ = refrun.Arith((p, qmin, 1024))
    E, G, H = (Q(v) for v in refrun.radius2_constants(A_, kname))
    eta = Q(1, 1 << -qmin) if qmin < 0 else Q(1 << qmin)
    u = Q(1, 1 << p)
    E, G, H = E * eta, G * eta, H * eta
    if kname == "ball_add_2":
        rel, tiny = 3 * u * u / (1 - 4 * u), Q(0)
    else:
        rel, tiny = 4 * u * u, Q(3, 2) * eta
    k = 2 * (1 + u) ** 3 * G * E + 2 * u * u
    return k * (1 + rel) / (1 - u), 2 * (1 + u) ** 2 * (G * eta / 2 + H) + eta + k / (1 - u) * tiny


@test
def iv_constants(ctx):
    """The constants of a claim with up( ): random expressions against Python's Fractions with an
    up( ) of their own; the rel and abs of the bounds of two limbs against the closed forms built
    from the reference runner's constants E, G, H, and against milestone2.md's table in binary64
    and binary32; malformed constants refused, and an up( ) beyond Omega an error."""
    cl = claims6(ctx)
    rnd = random.Random(20261120)
    fmt = F.parse_format("fp:6:-12:4")
    u, eta = Q(1, 64), Q(1, 1 << 12)

    def up(x):
        # The smallest number of the format not below x, by a walk over its numbers.
        vals = [Q(v) * eta for v in F.all_values(fmt)]
        cands = [v for v in vals if v >= x]
        return min(cands) if cands else None

    def rand(depth=0):
        k = rnd.randrange(7 if depth < 3 else 3)
        if k == 0:
            n = rnd.randrange(1, 9)
            return str(n), Q(n)
        if k == 1:
            return "u", u
        if k == 2:
            return "eta", eta
        a, va = rand(depth + 1)
        b, vb = rand(depth + 1)
        if k == 3:
            return "(%s+%s)" % (a, b), va + vb
        if k == 4:
            return "(%s*%s)" % (a, b), va * vb
        if k == 5 and vb != 0:
            return "(%s/%s)" % (a, b), va / vb
        v = up(abs(va))
        if v is None:
            return a, va
        return "up(%s)" % ("-(%s)" % a if va < 0 else a), v
    n = ctx.n(1500, 300)
    for _ in range(n):
        text, want = rand()
        got = IV.eval_const(IV.parse_const(text), fmt, lambda k: (Q(0), Q(0)), text)
        expect(got == want, "%s = %s, not %s" % (text, got, want))
    for text, want in (("-2^2", Q(-4)), ("2^3^2", Q(512)), ("2^-3", Q(1, 8)), ("up(1/3)", None),
                       ("up(eta/3)", eta), ("up(0)", Q(0))):
        got = IV.eval_const(IV.parse_const(text), fmt, lambda k: (Q(0), Q(0)), text)
        if want is None:
            want = up(Q(1, 3))
        expect(got == want, "%s = %s, not %s" % (text, got, want))
    for text in ("", "up(", "up()", "up(1)(2)", "unit(1)", "x", "2^u", "2^up(1)", "1 2"):
        try:
            IV.parse_const(text)
        except ClaimsError:
            continue
        raise AssertionError("%r parsed" % text)
    for text in ("up(2^100)", "1/(1-1)"):
        try:
            IV.eval_const(IV.parse_const(text), fmt, lambda k: (Q(0), Q(0)), text)
        except ClaimsError:
            continue
        raise AssertionError("%r evaluated" % text)
    # The constants of the claims against the closed forms of the page from refrun's E, G, H.
    checked = 0
    for fname in ("binary64", "binary32", "fp:4:-6:1", "fp:5:-12:5", "fp:3:-3:2"):
        f = F.parse_format(fname)
        for kname, ball in (("add_down_2_2", "ball_add_2"), ("mul_dir_2_2", "ball_mul_2")):
            if f.p < cl.get(kname).min_precision:
                continue
            e = cl.get(kname).ensures[-1]
            got = IV.constants(e, f, cl)
            A, B = _closed_form(f.p, f.qmin, ball)
            expect((got["rel"], got["abs"]) == (A, B), "%s %s: rel, abs = %s, %s; the closed "
                   "form gives %s, %s" % (kname, fname, got["rel"], got["abs"], A, B))
            checked += 1
            if fname in ("binary64", "binary32"):
                uu = Q(1, 1 << f.p) ** 2
                N = Q(1 << (f.p - 1)) * (Q(1, 1 << -f.qmin))
                a, b = float(got["rel"] / uu), float(got["abs"] / N)
                want = {("add_down_2_2", "binary64"): (8.000000000000009, 2.000000000000002),
                        ("mul_dir_2_2", "binary64"): (10.000000000000012, 2.000000000000003),
                        ("add_down_2_2", "binary32"): (8.0000049, None),
                        ("mul_dir_2_2", "binary32"): (10.0000068, None)}[(kname, fname)]
                expect(abs(a - want[0]) < 1e-6 * want[0] and (want[1] is None or
                                                             abs(b - want[1]) < 1e-12),
                       "%s %s: A = %r u^2, B = %r N, the page says %s" % (kname, fname, a, b, want))
    return "%d random constants; the rel and abs of the bounds of two limbs in %d cases" % (n, checked)


def _judge_stream(ctx, kernel, fmtname, count, variant="correct", strata=None):
    lines = stream6(ctx, kernel, fmtname, count, strata)
    return judge(run6(lines, variant), claims6(ctx))


def _ref_one(args):
    kernel, fmtname, count = args
    claims = load_claims(FIXTURE6)
    g = G.RandomGen(claims.get(kernel), F.parse_format(fmtname), "selftest8")
    lines = list(g.lines(0, count))
    s = judge(run6(lines), claims)
    return kernel, fmtname, totals(s), entry_stats(s, kernel)


@test
def iv_reference(ctx):
    """The reference runner (milestone2.md's listings) on random streams of every interval kernel in
    binary64, binary32 and a toy format: no failure, no invalid case, nothing suspicious, a case of
    every stratum the header lists, every entry applied; and in binary64 and binary32 the
    fractions of the bounds of two limbs and of the midpoint reached as the guards ask."""
    n = ctx.n(1200, 300)
    tasks = [(k, f, n) for k in KERNELS for f in FORMATS]
    with cf.ProcessPoolExecutor(ctx.jobs) as ex:
        results = list(ex.map(_ref_one, tasks))
    reached = {}
    for kernel, fname, t, ents in results:
        expect(t["failed"] == 0 and t["invalid"] == 0 and t["suspicious"] == 0,
               "%s %s: %s" % (kernel, fname, t))
        expect(t["judged"] > 0, "%s %s: nothing judged" % (kernel, fname))
        for label, (kind, app, _f, counts, maxima) in ents.items():
            expect(app > 0, "%s %s: %s applied to nothing" % (kernel, fname, label))
            for name in (IV.OUT_RATIO, IV.SIDE_RATIO % "lower", IV.MID_RATIO):
                if name in maxima and fname != "fp:4:-6:1":
                    reached[(kernel, fname, name)] = maxima[name]
    low = {k: v for k, v in reached.items() if v < Q(1, 4)}
    expect(not low, "fractions of the bounds below 1/4: %s" % low)
    # The classes the cross-checks' guards ask for, reached by the generator's strata in binary64
    # and binary32 (tests/crosscheck_guards.py, iv_needs: a selection).
    missing = []
    for kernel, fname, t, ents in results:
        if fname == "fp:4:-6:1":
            continue
        for label, (kind, _app, _f, counts, maxima) in ents.items():
            want = list(NEEDS.get(kind, ()))
            if kind == "encloses_interval":
                want += NEEDS_OP.get(kernel, [])
            if kind == "outward" and "exact when" in label:
                want += [IV.OUT_EW_HOLDS, IV.OUT_EXACT]
            for c in want:
                if not counts.get(c):
                    missing.append("%s %s: %s" % (kernel, fname, c))
            if kind == "encloses_interval" and kernel in NEAR:
                hi = maxima.get(IV.I5_NEAR_HOLDS)
                if hi is None or hi < Q(1, 2):
                    missing.append("%s %s: no range within a factor 2 below the limit (%s)"
                                   % (kernel, fname, hi))
    expect(not missing, "classes never reached: %s" % "; ".join(missing[:12]))
    return "%d streams of %d cases; the fractions reached: %.3g to %.3g" % (
        len(tasks), n, min(reached.values()), max(reached.values()))


# The classes of each kind that the streams of binary64 and binary32 must reach.
NEEDS = {
    "encloses_interval": (IV.OPS_EMPTY, IV.OPS_UNBOUNDED, IV.OPS_BOUNDED, IV.RES_EMPTY,
                          IV.RES_BOUNDED, IV.RES_UNBOUNDED, IV.I5_HOLDS),
    "outward": (IV.OUT_INEXACT,),
    "makes_interval": (IV.MAKE_INTERVAL, IV.MAKE_POINT, IV.MAKE_UNBOUNDED, IV.MAKE_NAN,
                       IV.MAKE_REVERSED, IV.MAKE_EQUAL_INF),
    "makes_ball": (IV.MAKE_INTERVAL, IV.MAKE_NAN, IV.MAKE_REVERSED, IV.MAKE_EQUAL_INF,
                   IV.MID_HOLDS, IV.MID_FAILS),
    "set_bound": (IV.BALL_EMPTY, IV.BALL_WHOLE, IV.BALL_FINITE),
    "interval_of_ball": (IV.BALL_EMPTY, IV.BALL_WHOLE, IV.BALL_FINITE),
    "interval_set": (IV.SET_EMPTY_OPERAND, IV.SET_BOTH_EMPTY, IV.SET_DISJOINT, IV.SET_TOUCH,
                     IV.SET_OVERLAP),
    "ball_of_interval": (IV.X_EMPTY, IV.X_WHOLE, IV.X_ABOVE, IV.X_BELOW, IV.X_BOUNDED,
                         IV.X_POINT, IV.X_ODD),
    "splits": (IV.X_EMPTY, IV.X_WHOLE, IV.X_ABOVE, IV.X_BELOW, IV.X_BOUNDED, IV.X_POINT),
    "bound": (IV.ZF_ZERO, IV.ZF_ZERO_INF),
}
NEEDS_OP = {
    "interval_add_1": [IV.I5_FAILS, IV.SIDE_INEXACT % "lower", IV.SIDE_EXACT % "upper"],
    "interval_sub_1": [IV.I5_FAILS, IV.SIDE_INEXACT % "upper"],
    "interval_mul_1": [IV.I5_FAILS, IV.SIDE_PL_HOLDS % "lower", IV.SIDE_PL_FAILS % "lower",
                       IV.SIDE_ONE % "lower", IV.SIDE_ONE % "upper"],
    "interval_add_2": [IV.I5_FAILS, IV.SIDE_EW_HOLDS % "lower", IV.SIDE_EW_HOLDS % "upper"],
    "interval_sub_2": [IV.I5_FAILS, IV.SIDE_EW_HOLDS % "lower", IV.SIDE_EW_HOLDS % "upper"],
    "interval_mul_2": [IV.I5_FAILS, IV.I6_APPLIES, IV.I6_UNBOUNDED],
}
NEAR = ("interval_add_1", "interval_sub_1", "interval_mul_1", "interval_add_2", "interval_sub_2",
        "interval_mul_2")


# Tiny formats for the enumerations of the reference runner (each at least the min_precision of
# the kernels it is used for, of the shape of the extended domain, and with every constant of the
# kernels a number of the format: P = 2^(2p-1) eta of the products is not, at fp:2:-1:0, and the
# interpreter refuses interval_mul_1 there): every case of each kernel.
TINY = {1: "fp:2:-2:1", 2: "fp:2:-2:1", 3: "fp:3:-2:-1", 4: "fp:4:-3:-2"}


def _enum_one(args):
    kernel, fmtname, restrict, variant = args
    claims = load_claims(FIXTURE6)
    g = G.ExhaustiveGen(claims.get(kernel), F.parse_format(fmtname), restrict)
    s = judge(run6(g.lines(0, g.total), variant), claims)
    return kernel, variant, g.total, totals(s), failing_kinds(s, kernel)


@test
def iv_exhaustive(ctx):
    """The reference runner on every case of tiny formats for every interval kernel (the two-limb
    products of two intervals on a restricted domain): no failure, invalid or suspicious case; and
    the planted faults that a tiny format can show caught there, in their entries only (of the
    constructors: a NaN bound, the same infinity twice and reversed bounds each read the old or
    a wrong way, and reversed bounds of two limbs told by their leading limbs alone)."""
    cl = claims6(ctx)
    tasks = []
    for k in KERNELS:
        p = max(cl.get(k).min_precision, 1)
        fmt = TINY[p]
        restrict = ()
        if k == "interval_mul_2" or (ctx.quick and k in ("interval_add_2", "interval_sub_2",
                                                         "interval_hull_2",
                                                         "interval_intersection_2")):
            restrict = ("xl.in=0x0p+0/0x1p+0/-0x1p-1", "xu.in=0x0p+0/0x1p+0/0x1.8p+0")
        tasks.append((k, fmt, restrict, "correct"))
    faults = {"iv-neg-not-swapped": "interval_neg_1", "iv-make-nan-empty": "interval_make_1",
              "iv-make-inf-empty": "interval_make_2", "iv-fromint-inf-empty": "ball_from_interval_2",
              "iv-make-reversed-whole": "interval_make_1",
              "iv2-make-reversed-lead": "interval_make_2",
              "iv-empty-whole": "interval_add_1", "iv-hull-as-intersection": "interval_hull_1",
              "iv-split-gap": "interval_split_1", "iv2-no-zero-rule": "add_down_2_2",
              "iv-ballbound-empty-nan": "ball_lower_as_1", "iv-mul-zero-nan": "mul_dir_1"}
    for v, k in faults.items():
        p = max(cl.get(k).min_precision, 1)
        tasks.append((k, TINY[p], (), v))
    with cf.ProcessPoolExecutor(ctx.jobs) as ex:
        results = list(ex.map(_enum_one, tasks))
    cases = 0
    for kernel, variant, total, t, kinds in results:
        cases += total
        if variant == "correct":
            expect(t["failed"] == 0 and t["invalid"] == 0 and t["suspicious"] == 0,
                   "%s: %s" % (kernel, t))
            # Every line of the extended domain is judged; in the finite domain the lines whose
            # result is not finite are not.
            ext = cl.get(kernel).extended
            expect(t["judged"] == t["cases"] > 0 if ext else t["judged"] > t["cases"] // 2,
                   "%s: %d of %d judged" % (kernel, t["judged"], t["cases"]))
        else:
            allowed = PLANTED[variant][0][kernel]
            expect(t["failed"] > 0 and kinds <= allowed,
                   "%s on %s: failed %d, in %s" % (variant, kernel, t["failed"], kinds))
    return "%d enumerations, %d cases" % (len(results), cases)


def _inputs(line):
    return [t for t in line.partition(" -> ")[0].split()[2:] if not t.startswith("#")]


def _opposite_inf_tails(fmt, line):
    """The same infinity twice with second limbs that are zeros of opposite signs, as (+inf, 0)
    and (+inf, -0)."""
    lo0, lo1, hi0, hi1 = _inputs(line)
    return lo0 == hi0 and lo0 in ("inf", "-inf") and lo1.startswith("-") != hi1.startswith("-")


def _reversed_equal_leads(fmt, line):
    """Finite bounds of two limbs with equal leading limbs and lo > hi, as (1, 2^-4) and (1, 0)."""
    lo0, lo1, hi0, hi1 = (F.parse_limb(fmt, t) for t in _inputs(line))
    return (all(type(v) is int for v in (lo0, lo1, hi0, hi1)) and lo0 == hi0 and lo1 > hi1)


# The lines a planted fault of the constructors of two limbs is about: each fault's streams of the
# kernel must have such lines in every format, and each must fail.
TARGETED = {"iv-make-inf-empty": ("interval_make_2", _opposite_inf_tails),
            "iv2-make-reversed-lead": ("interval_make_2", _reversed_equal_leads)}


def _planted_one(args):
    variant, fname, count = args
    claims = load_claims(FIXTURE6)
    expected, formats = PLANTED[variant]
    strata = PLANTED_STRATA.get(variant)
    fmt = F.parse_format(fname)
    out = []
    targeted = None
    for k in KERNELS:
        g = G.RandomGen(claims.get(k), fmt, "selftest8",
                        strata.split(",") if strata and k in expected else None)
        lines = list(g.lines(0, count))
        s = judge(run6(lines, variant), claims)
        t = totals(s)
        out.append((k, t["failed"] + t["invalid"] + t["suspicious"], t["invalid"],
                    t["suspicious"], failing_kinds(s, k)))
        if TARGETED.get(variant, ("",))[0] == k:
            aimed = [ln for ln in lines if not ln.startswith("#") and TARGETED[variant][1](fmt, ln)]
            targeted = (len(aimed), totals(judge(run6(aimed, variant), claims))["failed"])
    return variant, fname, out, targeted


@test
def iv_planted(ctx):
    """Every planted fault of the interval kernels (refrun VARIANTS iv-...) caught in the kernels
    and entries where it belongs, in every format where it must be (PLANTED), and in no other
    kernel; never as an invalid or a suspicious case. The faults of the constructors of two limbs
    that are about particular lines (TARGETED: the same infinity with zeros of opposite signs,
    reversed bounds with equal leading limbs) fail on every such line of their streams, and the
    streams have some in every format."""
    n = ctx.n(1200, 400)
    tasks = [(v, f, n) for v in PLANTED for f in FORMATS]
    with cf.ProcessPoolExecutor(ctx.jobs) as ex:
        results = list(ex.map(_planted_one, tasks))
    aimed = []
    for variant, fname, out, targeted in results:
        if targeted is not None:
            expect(targeted[0] > 0 and targeted[1] == targeted[0],
                   "%s %s: %d of the %d lines it is about failed" % (variant, fname, targeted[1],
                                                                    targeted[0]))
            aimed.append("%s %s %d" % (variant, fname, targeted[0]))
        expected, formats = PLANTED[variant]
        for k, bad, inv, sus, kinds in out:
            expect(not inv and not sus, "%s %s: %s gave %d invalid, %d suspicious"
                   % (variant, fname, k, inv, sus))
            if k not in expected:
                expect(not bad, "%s %s: %s, which does not use it, failed %d (%s)"
                       % (variant, fname, k, bad, kinds))
                continue
            expect(kinds <= expected[k], "%s %s: %s failed in %s, not only %s"
                   % (variant, fname, k, kinds, expected[k]))
        caught = {k for k, bad, _i, _s, _k in out if bad}
        if fname in formats:
            need = set(expected) if variant != "iv-ball-no-term" else {"add_ball_2_2",
                                                                        "mul_ball_2_2"}
            expect(need <= caught, "%s %s: not caught in %s" % (variant, fname,
                                                                sorted(need - caught)))
    return "%d planted faults in %d formats; the lines aimed at: %s" % (
        len(PLANTED), len(FORMATS), ", ".join(aimed))


# Hand-written lines: (line, kernel, the statements that must fail, or () for a pass).
B64 = "binary64"
OM = "0x1.fffffffffffffp+1023"
HAND = [
    # encloses_interval, tight rounded (interval_add_1).
    ("interval_add_1 binary64 0x1p+0 0x1p+1 0x1.8p+1 0x1p+2 -> 0x1p+2 0x1.8p+2", ()),
    ("interval_add_1 binary64 0x1p+0 0x1p+1 0x1.8p+1 0x1p+2 -> 0x1p+2 0x1.cp+2", ("I4",)),
    ("interval_add_1 binary64 0x1p+0 0x1p+1 0x1.8p+1 0x1p+2 -> 0x1.4p+2 0x1.8p+2", ("I3", "I4")),
    ("interval_add_1 binary64 0x1p+0 0x1p+1 0x1.8p+1 0x1p+2 -> 0x1.8p+2 0x1p+2", ("I1",)),
    ("interval_add_1 binary64 inf -inf 0x1p+0 0x1p+1 -> inf -inf", ()),
    ("interval_add_1 binary64 inf -inf 0x1p+0 0x1p+1 -> 0x1p+0 0x1p+1", ("I2",)),
    ("interval_add_1 binary64 0x1p+0 0x1p+1 0x1p+0 0x1p+1 -> inf -inf", ("I2",)),
    ("interval_add_1 binary64 0x1p+0 inf 0x1p+0 0x1p+1 -> 0x1p+1 inf", ()),
    ("interval_add_1 binary64 0x1p+0 inf 0x1p+0 0x1p+1 -> 0x1p+1 %s" % OM, ("I3", "I4")),
    # RD(2 Omega) = Omega, RU(2 Omega) = +inf; bounded operands beyond Omega: unbounded, exactly.
    ("interval_add_1 binary64 %s %s %s %s -> %s inf" % ((OM,) * 5), ()),
    ("interval_add_1 binary64 %s %s %s %s -> %s %s" % ((OM,) * 6), ("I3", "I4", "I5")),
    # 1 + 2^-60 rounded down is 1 and up is 1 + 2^-52.
    ("interval_add_1 binary64 0x1p+0 0x1p+0 0x1p-60 0x1p-60 -> 0x1p+0 0x1.0000000000001p+0", ()),
    ("interval_add_1 binary64 0x1p+0 0x1p+0 0x1p-60 0x1p-60 -> 0x1p+0 0x1p+0", ("I3", "I4")),
    # interval_sub_1 and interval_neg_1.
    ("interval_sub_1 binary64 0x1p+0 0x1p+1 0x1p+0 0x1p+1 -> -0x1p+0 0x1p+0", ()),
    ("interval_neg_1 binary64 0x1p+0 0x1p+1 -> -0x1p+1 -0x1p+0", ()),
    ("interval_neg_1 binary64 0x1p+0 0x1p+1 -> -0x1p+0 -0x1p+1", ("I1",)),
    ("interval_neg_1 binary64 -inf 0x1p+1 -> -0x1p+1 inf", ()),
    # tight exact: an enclosure one step wider on either side is no longer exact (I4 alone).
    ("interval_neg_1 binary64 0x1p+0 0x1p+1 -> -0x1.0000000000001p+1 -0x1p+0", ("I4",)),
    ("interval_neg_1 binary64 0x1p+0 0x1p+1 -> -0x1p+1 -0x1.fffffffffffffp-1", ("I4",)),
    ("interval_neg_2 binary64 0x1p+0 0x1p-60 0x1p+1 0x0p+0 -> -0x1p+1 -0x1p-104 -0x1p+0 -0x1p-60",
     ("I4",)),
    # interval_mul_1: [0, 0] times the whole line is [0, 0]; [0, 1] [1, +inf] is [0, +inf].
    ("interval_mul_1 binary64 0x0p+0 0x0p+0 -inf inf -> 0x0p+0 0x0p+0", ()),
    ("interval_mul_1 binary64 0x0p+0 0x0p+0 -inf inf -> -inf inf", ("I4",)),
    ("interval_mul_1 binary64 0x0p+0 0x1p+0 0x1p+0 inf -> 0x0p+0 inf", ()),
    ("interval_mul_1 binary64 -0x1p+0 0x1p+1 0x1p+0 0x1.8p+1 -> -0x1.8p+1 0x1.8p+2", ()),
    # Below P one step beyond the rounding is allowed, two are not.
    ("interval_mul_1 binary64 0x1p-1074 0x1p-1074 0x1p-1 0x1p-1 -> 0x0p+0 0x1p-1074", ()),
    ("interval_mul_1 binary64 0x1p-1074 0x1p-1074 0x1p-1 0x1p-1 -> -0x1p-1074 0x1p-1074", ()),
    ("interval_mul_1 binary64 0x1p-1074 0x1p-1074 0x1p-1 0x1p-1 -> -0x1p-1073 0x1p-1074",
     ("I4",)),
    # mul_dir_1: a zero factor gives zero, 0 * inf included.
    ("mul_dir_1 binary64 0x0p+0 inf -> 0x0p+0 -0x0p+0", ()),
    ("mul_dir_1 binary64 0x0p+0 inf -> nan nan", ("bound", "rounded")),
    ("mul_dir_1 binary64 0x1p+1 -inf -> -inf -inf", ()),
    ("mul_dir_1 binary64 0x1p+1 0x1.8p+0 -> 0x1.8p+1 0x1.8p+1", ()),
    ("mul_dir_1 binary64 0x1p+1 0x1.8p+0 -> 0x1.7ffffffffffffp+1 0x1.8p+1", ("rounded",)),
    # interval_hull_1, interval_intersection_1.
    ("interval_hull_1 binary64 0x1p+0 0x1p+1 0x1.4p+2 0x1.8p+2 -> 0x1p+0 0x1.8p+2", ()),
    ("interval_hull_1 binary64 0x1p+0 0x1p+1 0x1.4p+2 0x1.8p+2 -> 0x1p+0 0x1p+1",
     ("interval_set",)),
    ("interval_hull_1 binary64 inf -inf 0x1p+0 0x1p+1 -> 0x1p+0 0x1p+1", ()),
    ("interval_hull_1 binary64 inf -inf inf -inf -> inf -inf", ()),
    ("interval_intersection_1 binary64 0x1p+0 0x1.8p+1 0x1p+1 0x1p+2 -> 0x1p+1 0x1.8p+1", ()),
    ("interval_intersection_1 binary64 0x1p+0 0x1p+1 0x1.8p+1 0x1p+2 -> inf -inf", ()),
    ("interval_intersection_1 binary64 0x1p+0 0x1p+1 0x1.8p+1 0x1p+2 -> 0x1.8p+1 0x1p+1",
     ("interval_set",)),
    ("interval_intersection_1 binary64 0x1p+0 0x1p+1 0x1p+1 0x1p+2 -> 0x1p+1 0x1p+1", ()),
    # interval_mid_rad_1 and interval_to_ball_1.
    ("interval_mid_rad_1 binary64 0x1p+0 0x1.8p+1 -> 0x1p+1 0x1p+0", ()),
    ("interval_mid_rad_1 binary64 0x1p+0 0x1.8p+1 -> 0x1p+1 0x1.0000000000001p+0",
     ("smallest_radius",)),
    ("interval_mid_rad_1 binary64 0x1p+0 0x1.8p+1 -> 0x1p+0 0x1p+1", ("midpoint",)),
    ("interval_mid_rad_1 binary64 0x1p+0 0x1.8p+1 -> 0x1p+1 0x1.fffffffffffffp-1",
     ("containment", "smallest_radius")),
    ("interval_mid_rad_1 binary64 -inf inf -> 0x0p+0 inf", ()),
    ("interval_mid_rad_1 binary64 0x1p+0 inf -> %s inf" % OM, ()),
    ("interval_mid_rad_1 binary64 -inf 0x1p+0 -> -%s inf" % OM, ()),
    ("interval_mid_rad_1 binary64 inf -inf -> nan nan", ()),
    ("interval_mid_rad_1 binary64 inf -inf -> 0x0p+0 inf", ("special",)),
    ("interval_to_ball_1 binary64 0x1p+0 inf -> 0x0p+0 inf", ()),
    ("interval_to_ball_1 binary64 0x1p+0 inf -> %s inf" % OM, ("special",)),
    ("interval_to_ball_1 binary64 inf -inf -> nan nan", ()),
    # [eta, eta]: the midpoint is eta, within u*eta + eta of the center 0 too; 0 is outside it.
    ("interval_mid_rad_1 binary64 0x1p-1074 0x1p-1074 -> 0x1p-1074 0x0p+0", ()),
    ("interval_mid_rad_1 binary64 0x1p-1074 0x1p-1074 -> 0x0p+0 0x1p-1074", ("center",)),
    # interval_split_1.
    ("interval_split_1 binary64 0x1p+0 0x1.8p+1 -> 0x1p+0 0x1p+1 0x1p+1 0x1.8p+1", ()),
    ("interval_split_1 binary64 0x1p+0 0x1.8p+1 -> 0x1p+0 0x1p+1 0x1.4p+1 0x1.8p+1",
     ("splits",)),
    ("interval_split_1 binary64 -inf inf -> -inf 0x0p+0 0x0p+0 inf", ()),
    ("interval_split_1 binary64 inf -inf -> inf -inf inf -inf", ()),
    ("interval_split_1 binary64 -inf inf -> -inf inf inf inf", ("splits",)),
    # The bounds of a ball (one limb, tight rounded; two limbs, a bound).
    ("ball_lower_as_1 binary64 0x1p+0 0x1p-1 -> 0x1p-1", ()),
    ("ball_lower_as_1 binary64 0x1p+0 0x1p-1 -> 0x1p-2", ("set_bound",)),
    ("ball_lower_as_1 binary64 0x1p+0 0x1p-1 -> 0x1.8p-1", ("set_bound",)),
    ("ball_lower_as_1 binary64 nan nan -> inf", ()),
    ("ball_lower_as_1 binary64 nan nan -> nan", ("set_bound",)),
    ("ball_lower_as_1 binary64 0x0p+0 inf -> -inf", ()),
    ("ball_upper_as_1 binary64 0x1p+0 0x1p-60 -> 0x1.0000000000001p+0", ()),
    ("ball_lower_as_2 binary64 0x1p+0 0x0p+0 0x1p-1 -> 0x1p-1", ()),
    ("ball_lower_as_2 binary64 0x1p+0 0x0p+0 0x1p-1 -> 0x1.fffffffffffffp-2", ()),
    ("ball_lower_as_2 binary64 0x1p+0 0x0p+0 0x1p-1 -> 0x1.0000000000001p-1", ("set_bound",)),
    ("ball_lower_as_2 binary64 0x1p+0 0x0p+0 0x1p-1 -> 0x1p-2", ("error",)),
    # ball_to_interval_1.
    ("ball_to_interval_1 binary64 0x1p+0 0x1p-1 -> 0x1p-1 0x1.8p+0", ()),
    ("ball_to_interval_1 binary64 0x0p+0 inf -> -inf inf", ()),
    ("ball_to_interval_1 binary64 nan nan -> inf -inf", ()),
    ("ball_to_interval_1 binary64 nan nan -> -inf inf", ("empty",)),
    ("ball_to_interval_1 binary64 0x1p+0 0x1p-60 -> 0x1p+0 0x1.0000000000001p+0",
     ("containment",)),
    # tight rounded: the roundings of 1 -+ 2^-60 down and up, and one step wider (contains, not
    # tight).
    ("ball_to_interval_1 binary64 0x1p+0 0x1p-60 -> 0x1.fffffffffffffp-1 0x1.0000000000001p+0", ()),
    ("ball_to_interval_1 binary64 0x1p+0 0x1p-60 -> 0x1.ffffffffffffep-1 0x1.0000000000001p+0",
     ("tight",)),
    ("ball_to_interval_1 binary64 0x1p+0 0x1p-60 -> 0x1.fffffffffffffp-1 0x1.0000000000002p+0",
     ("tight",)),
    # The constructors.
    ("interval_make_1 binary64 0x1p+0 0x1p+1 -> 0x1p+0 0x1p+1", ()),
    ("interval_make_1 binary64 nan 0x1p+1 -> -inf inf", ()),
    ("interval_make_1 binary64 nan 0x1p+1 -> inf -inf", ("makes_interval",)),
    ("interval_make_1 binary64 0x1p+1 0x1p+0 -> inf -inf", ()),
    ("interval_make_1 binary64 0x1p+1 0x1p+0 -> 0x1p+1 0x1p+0", ("makes_interval",)),
    # The same infinity twice is the whole line (the owner's decision of 2026-11-20; it was the
    # empty set, as in IEEE 1788); reversed bounds, infinite ones included, the empty set.
    ("interval_make_1 binary64 inf inf -> -inf inf", ()),
    ("interval_make_1 binary64 inf inf -> inf -inf", ("makes_interval",)),
    ("interval_make_1 binary64 -inf -inf -> -inf inf", ()),
    ("interval_make_1 binary64 -inf -inf -> inf -inf", ("makes_interval",)),
    ("interval_make_1 binary64 inf inf -> inf inf", ("makes_interval",)),
    ("interval_make_1 binary64 inf -inf -> inf -inf", ()),
    ("interval_make_1 binary64 inf -inf -> -inf inf", ("makes_interval",)),
    ("interval_make_1 binary64 inf 0x1p+0 -> inf -inf", ()),
    ("interval_make_1 binary64 inf 0x1p+0 -> -inf inf", ("makes_interval",)),
    ("interval_make_1 binary64 0x1p+0 -inf -> inf -inf", ()),
    ("interval_make_1 binary64 0x1p+0 -inf -> -inf inf", ("makes_interval",)),
    ("interval_make_1 binary64 nan inf -> -inf inf", ()),
    ("interval_make_1 binary64 -inf nan -> -inf inf", ()),
    ("interval_make_1 binary64 nan nan -> -inf inf", ()),
    ("interval_make_1 binary64 -inf inf -> -inf inf", ()),
    ("interval_make_1 binary64 0x0p+0 -0x0p+0 -> -0x0p+0 0x0p+0", ()),
    ("interval_make_2 binary64 nan nan 0x1p+0 0x0p+0 -> -inf 0x0p+0 inf 0x0p+0", ()),
    ("interval_make_2 binary64 0x1p+0 0x1p-60 0x1p+0 0x1p-61 -> inf 0x0p+0 -inf 0x0p+0", ()),
    # Two limbs: (+inf, 0) and (+inf, -0) are the same infinity twice; reversed bounds with equal
    # leading limbs are reversed.
    ("interval_make_2 binary64 inf 0x0p+0 inf -0x0p+0 -> -inf 0x0p+0 inf 0x0p+0", ()),
    ("interval_make_2 binary64 inf 0x0p+0 inf -0x0p+0 -> inf 0x0p+0 -inf 0x0p+0",
     ("makes_interval",)),
    ("interval_make_2 binary64 -inf -0x0p+0 -inf 0x0p+0 -> -inf -0x0p+0 inf -0x0p+0", ()),
    ("interval_make_2 binary64 -inf -0x0p+0 -inf 0x0p+0 -> inf 0x0p+0 -inf 0x0p+0",
     ("makes_interval",)),
    ("interval_make_2 binary64 inf 0x0p+0 -inf 0x0p+0 -> inf 0x0p+0 -inf 0x0p+0", ()),
    ("interval_make_2 binary64 inf 0x0p+0 -inf 0x0p+0 -> -inf 0x0p+0 inf 0x0p+0",
     ("makes_interval",)),
    ("interval_make_2 binary64 inf -0x0p+0 0x1p+0 0x0p+0 -> inf 0x0p+0 -inf 0x0p+0", ()),
    ("interval_make_2 binary64 0x1p+0 0x1p-60 0x1p+0 0x0p+0 -> inf 0x0p+0 -inf 0x0p+0", ()),
    ("interval_make_2 binary64 0x1p+0 0x1p-60 0x1p+0 0x0p+0 -> -inf 0x0p+0 inf 0x0p+0",
     ("makes_interval",)),
    ("interval_make_2 binary64 0x1p+0 0x0p+0 0x1p+0 0x1p-60 -> 0x1p+0 0x0p+0 0x1p+0 0x1p-60", ()),
    ("interval_make_2 binary64 -inf 0x0p+0 0x1p+0 -0x1p-60 -> -inf -0x0p+0 0x1p+0 -0x1p-60", ()),
    ("ball_from_interval_2 binary64 0x1p+0 0x1.8p+1 -> 0x1p+1 0x0p+0 0x1p+0", ()),
    ("ball_from_interval_2 binary64 0x1p+0 0x1.8p+1 -> 0x1p+1 0x0p+0 0x1p+1", ("makes_ball",)),
    ("ball_from_interval_2 binary64 0x1p+0 0x1.8p+1 -> 0x1p+1 0x1p-60 0x1.0000000000001p+0",
     ("makes_ball",)),
    # [-1, 2^53]: (hi - lo)/2 = 2^52 + 1/2 is not a number, its rounding up 2^52 + 1 leaves room,
    # so a center off the midpoint 2^52 - 1/2 still contains the interval; midpoint_when holds.
    ("ball_from_interval_2 binary64 -0x1p+0 0x1p+53 -> 0x1.fffffffffffffp+51 0x0p+0 "
     "0x1.0000000000001p+52", ()),
    ("ball_from_interval_2 binary64 -0x1p+0 0x1p+53 -> 0x1p+52 0x0p+0 0x1.0000000000001p+52",
     ("makes_ball",)),
    ("ball_from_interval_2 binary64 nan 0x1p+0 -> 0x0p+0 0x0p+0 inf", ()),
    ("ball_from_interval_2 binary64 nan 0x1p+0 -> nan nan nan", ("makes_ball",)),
    ("ball_from_interval_2 binary64 nan nan -> 0x0p+0 0x0p+0 inf", ()),
    ("ball_from_interval_2 binary64 0x1p+1 0x1p+0 -> nan nan nan", ()),
    ("ball_from_interval_2 binary64 0x1p+1 0x1p+0 -> 0x0p+0 0x0p+0 inf", ("makes_ball",)),
    ("ball_from_interval_2 binary64 0x1p+0 inf -> 0x0p+0 0x0p+0 inf", ()),
    ("ball_from_interval_2 binary64 0x1p+0 inf -> nan nan nan", ("makes_ball",)),
    # The same infinity twice: the whole line (2026-11-20; it was the empty set); reversed bounds,
    # infinite ones included, the empty set.
    ("ball_from_interval_2 binary64 inf inf -> 0x0p+0 0x0p+0 inf", ()),
    ("ball_from_interval_2 binary64 inf inf -> nan nan nan", ("makes_ball",)),
    ("ball_from_interval_2 binary64 -inf -inf -> -0x0p+0 0x0p+0 inf", ()),
    ("ball_from_interval_2 binary64 -inf -inf -> nan nan nan", ("makes_ball",)),
    ("ball_from_interval_2 binary64 inf -inf -> nan nan nan", ()),
    ("ball_from_interval_2 binary64 inf -inf -> 0x0p+0 0x0p+0 inf", ("makes_ball",)),
    ("ball_from_interval_2 binary64 inf 0x1p+0 -> nan nan nan", ()),
    ("ball_from_interval_2 binary64 inf 0x1p+0 -> 0x0p+0 0x0p+0 inf", ("makes_ball",)),
    ("ball_from_interval_2 binary64 0x1p+0 -inf -> nan nan nan", ()),
    ("ball_from_interval_2 binary64 -inf inf -> 0x0p+0 0x0p+0 inf", ()),
    # [eta, 3 eta]: neither half is a number; a ball that contains the interval passes.
    ("ball_from_interval_2 binary64 0x1p-1074 0x1.8p-1073 -> 0x1p-1073 0x0p+0 0x1p-1073", ()),
    ("ball_from_interval_2 binary64 0x1p-1074 0x1.8p-1073 -> 0x1p-1073 0x0p+0 0x0p+0",
     ("makes_ball",)),
    # outward of the finite domain: x + y = 0 gives zero; a bound on the wrong side.
    ("add_down_2_2 binary64 0x1p+0 0x0p+0 -0x1p+0 0x0p+0 -> 0x0p+0 0x0p+0", ()),
    ("add_down_2_2 binary64 0x1p+0 0x0p+0 -0x1p+0 0x0p+0 -> -0x1p-1021 0x0p+0", ("outward",)),
    ("add_down_2_2 binary64 0x1p+0 0x0p+0 0x1p+0 0x0p+0 -> 0x1p+1 0x0p+0", ()),
    ("add_down_2_2 binary64 0x1p+0 0x0p+0 0x1p+0 0x0p+0 -> 0x1p+1 0x1p-1074", ("outward",)),
    ("add_down_2_2 binary64 0x1p+0 0x0p+0 0x1p+0 0x0p+0 -> 0x1.fffffffffffffp+0 0x0p+0",
     ("outward",)),
    # A of the sums is about 8 u^2: 2 + 2^-104 is within 8 u^2 * 2 = 2^-102 of 2, 2 + 2^-100 not.
    ("add_up_2_2 binary64 0x1p+0 0x0p+0 0x1p+0 0x0p+0 -> 0x1p+1 0x1p-104", ()),
    ("add_up_2_2 binary64 0x1p+0 0x0p+0 0x1p+0 0x0p+0 -> 0x1p+1 0x1p-100", ("outward",)),
    # encloses with no ball: |x + y - z| <= d.
    ("add_ball_2_2 binary64 0x1p+0 0x0p+0 0x1p+0 0x0p+0 -> 0x1p+1 0x0p+0 0x0p+0", ()),
    ("add_ball_2_2 binary64 0x1p+0 0x0p+0 0x1p+0 0x0p+0 -> 0x1p+1 0x1p-60 0x1p-60", ("error",)),
    ("add_ball_2_2 binary64 0x1p+0 0x0p+0 0x1p+0 0x0p+0 -> 0x1p+1 0x1p-60 0x1p-61",
     ("error", "encloses")),
    # outward of the extended domain (mul_ext_2_2).
    ("mul_ext_2_2 binary64 0x0p+0 0x0p+0 inf 0x0p+0 -> 0x0p+0 0x0p+0 0x0p+0 0x0p+0", ()),
    ("mul_ext_2_2 binary64 0x0p+0 0x0p+0 inf 0x0p+0 -> -inf 0x0p+0 inf 0x0p+0", ("outward",)),
    ("mul_ext_2_2 binary64 0x1p+1 0x0p+0 -inf 0x0p+0 -> -inf 0x0p+0 -inf 0x0p+0", ()),
    ("mul_ext_2_2 binary64 0x1p+1 0x0p+0 -inf 0x0p+0 -> -inf 0x0p+0 inf 0x0p+0", ("outward",)),
    ("mul_ext_2_2 binary64 0x1p+1 0x0p+0 0x1p+1 0x0p+0 -> -inf 0x0p+0 inf 0x0p+0", ()),
    ("mul_ext_2_2 binary64 0x1p+1 0x0p+0 0x1p+1 0x0p+0 -> inf 0x0p+0 inf 0x0p+0", ("outward",)),
    # A of the product is about 10 u^2: 4 + 2^-104 is within 40 u^2 of 4, 4 + 2^-80 not.
    ("mul_ext_2_2 binary64 0x1p+1 0x0p+0 0x1p+1 0x0p+0 -> 0x1p+2 0x0p+0 0x1p+2 0x1p-104", ()),
    ("mul_ext_2_2 binary64 0x1p+1 0x0p+0 0x1p+1 0x0p+0 -> 0x1p+2 0x0p+0 0x1p+2 0x1p-80",
     ("outward",)),
    # encloses_interval of two limbs, the zero rule and the whole line from an overflow.
    ("interval_add_2 binary64 0x1p+0 0x0p+0 0x1p+1 0x0p+0 -0x1p+0 0x0p+0 0x1p+0 0x0p+0 "
     "-> 0x0p+0 0x0p+0 0x1.8p+1 0x1p-104", ()),
    ("interval_add_2 binary64 0x1p+0 0x0p+0 0x1p+1 0x0p+0 -0x1p+0 0x0p+0 0x1p+0 0x0p+0 "
     "-> 0x0p+0 0x0p+0 0x1.8p+1 0x1p-60", ("I4",)),
    ("interval_add_2 binary64 0x1p+0 0x0p+0 0x1p+1 0x0p+0 -0x1p+0 0x0p+0 0x1p+0 0x0p+0 "
     "-> -0x1p-1021 0x0p+0 0x1.8p+1 0x1p-104", ("I4",)),
    # At the bound: 3 + 2^-102 is within A*3 = 24 u^2 = 1.5 * 2^-102 of 3, 3 + 2^-101 not.
    ("interval_add_2 binary64 0x1p+0 0x0p+0 0x1p+1 0x0p+0 0x1p+0 0x0p+0 0x1p+0 0x0p+0 "
     "-> 0x1p+1 0x0p+0 0x1.8p+1 0x1p-102", ()),
    ("interval_add_2 binary64 0x1p+0 0x0p+0 0x1p+1 0x0p+0 0x1p+0 0x0p+0 0x1p+0 0x0p+0 "
     "-> 0x1p+1 0x0p+0 0x1.8p+1 0x1p-101", ("I4",)),
    ("add_up_2_2 binary64 0x1p+1 0x0p+0 0x1p+0 0x0p+0 -> 0x1.8p+1 0x1p-102", ()),
    ("add_up_2_2 binary64 0x1p+1 0x0p+0 0x1p+0 0x0p+0 -> 0x1.8p+1 0x1p-101", ("outward",)),
    ("mul_ext_2_2 binary64 0x1p+1 0x0p+0 0x1.8p+0 0x0p+0 -> 0x1.8p+1 -0x1p-102 0x1.8p+1 0x0p+0",
     ()),
    ("mul_ext_2_2 binary64 0x1p+1 0x0p+0 0x1.8p+0 0x0p+0 -> 0x1.8p+1 -0x1p-101 0x1.8p+1 0x0p+0",
     ("outward",)),
    ("interval_add_2 binary64 0x1p+0 0x0p+0 0x1p+1 0x0p+0 -0x1p+0 0x0p+0 0x1p+0 0x0p+0 "
     "-> -inf 0x0p+0 inf 0x0p+0", ("I4", "I5")),
    ("interval_neg_2 binary64 0x1p+0 0x1p-60 0x1p+1 0x0p+0 -> -0x1p+1 0x0p+0 -0x1p+0 -0x1p-60", ()),
    ("interval_mul_2 binary64 0x0p+0 0x0p+0 0x0p+0 0x0p+0 -inf 0x0p+0 inf 0x0p+0 "
     "-> 0x0p+0 0x0p+0 0x0p+0 0x0p+0", ()),
    ("interval_mul_2 binary64 0x0p+0 0x0p+0 0x0p+0 0x0p+0 -inf 0x0p+0 inf 0x0p+0 "
     "-> -inf 0x0p+0 inf 0x0p+0", ("I6",)),
    ("interval_hull_2 binary64 0x1p+0 0x1p-60 0x1p+1 0x0p+0 0x1p+0 0x0p+0 0x1p+0 0x0p+0 "
     "-> 0x1p+0 0x0p+0 0x1p+1 0x0p+0", ()),
    ("interval_hull_2 binary64 0x1p+0 0x1p-60 0x1p+1 0x0p+0 0x1p+0 0x0p+0 0x1p+0 0x0p+0 "
     "-> 0x1p+0 0x1p-60 0x1p+1 0x0p+0", ("interval_set",)),
]
INVALID = [
    "interval_add_1 binary64 0x1p+1 0x1p+0 0x1p+0 0x1p+1 -> 0x1p+0 0x1p+0",
    "interval_add_1 binary64 nan 0x1p+0 0x1p+0 0x1p+1 -> 0x1p+0 0x1p+0",
    "interval_add_1 binary64 inf inf 0x1p+0 0x1p+1 -> 0x1p+0 0x1p+0",
    "interval_neg_1 binary64 -inf -inf -> inf inf",
    "mul_dir_1 binary64 nan 0x1p+0 -> nan nan",
    "mul_ext_2_2 binary64 nan nan 0x1p+0 0x0p+0 -> nan nan nan nan",
    "interval_add_2 binary64 0x1p+0 0x1p-52 0x1p+1 0x0p+0 0x1p+0 0x0p+0 0x1p+0 0x0p+0 "
    "-> 0x0p+0 0x0p+0 0x0p+0 0x0p+0",
    "interval_add_2 binary64 inf 0x1p+0 inf 0x0p+0 0x1p+0 0x0p+0 0x1p+0 0x0p+0 "
    "-> 0x0p+0 0x0p+0 0x0p+0 0x0p+0",
]


# The given state of the constructors' bounds, counted by the first case that applies: a NaN bound
# (whatever the other: NaN with the same infinity too), the same infinity twice, reversed bounds,
# otherwise a point, an interval or an unbounded interval. Each line as worked out by hand.
GIVEN = [
    ("interval_make_1 binary64 nan nan -> -inf inf", IV.MAKE_NAN),
    ("interval_make_1 binary64 nan -inf -> -inf inf", IV.MAKE_NAN),
    ("interval_make_1 binary64 inf nan -> -inf inf", IV.MAKE_NAN),
    ("interval_make_1 binary64 inf inf -> -inf inf", IV.MAKE_EQUAL_INF),
    ("interval_make_1 binary64 -inf -inf -> -inf inf", IV.MAKE_EQUAL_INF),
    ("interval_make_1 binary64 inf -inf -> inf -inf", IV.MAKE_REVERSED),
    ("interval_make_1 binary64 inf 0x1p+0 -> inf -inf", IV.MAKE_REVERSED),
    ("interval_make_1 binary64 0x1p+0 -inf -> inf -inf", IV.MAKE_REVERSED),
    ("interval_make_1 binary64 0x1p+1 0x1p+0 -> inf -inf", IV.MAKE_REVERSED),
    ("interval_make_1 binary64 0x1p+0 0x1p+0 -> 0x1p+0 0x1p+0", IV.MAKE_POINT),
    ("interval_make_1 binary64 0x0p+0 -0x0p+0 -> 0x0p+0 0x0p+0", IV.MAKE_POINT),
    ("interval_make_1 binary64 0x1p+0 0x1p+1 -> 0x1p+0 0x1p+1", IV.MAKE_INTERVAL),
    ("interval_make_1 binary64 -inf inf -> -inf inf", IV.MAKE_UNBOUNDED),
    ("interval_make_1 binary64 0x1p+0 inf -> 0x1p+0 inf", IV.MAKE_UNBOUNDED),
    ("interval_make_2 binary64 nan nan inf 0x0p+0 -> -inf 0x0p+0 inf 0x0p+0", IV.MAKE_NAN),
    ("interval_make_2 binary64 inf 0x0p+0 inf -0x0p+0 -> -inf 0x0p+0 inf 0x0p+0",
     IV.MAKE_EQUAL_INF),
    ("interval_make_2 binary64 0x1p+0 0x1p-60 0x1p+0 0x0p+0 -> inf 0x0p+0 -inf 0x0p+0",
     IV.MAKE_REVERSED),
    ("interval_make_2 binary64 0x1p+0 0x1p-60 0x1p+0 0x1p-60 -> 0x1p+0 0x1p-60 0x1p+0 0x1p-60",
     IV.MAKE_POINT),
    ("interval_make_2 binary64 0x1p+0 0x0p+0 0x1p+0 0x1p-60 -> 0x1p+0 0x0p+0 0x1p+0 0x1p-60",
     IV.MAKE_INTERVAL),
    ("ball_from_interval_2 binary64 nan inf -> 0x0p+0 0x0p+0 inf", IV.MAKE_NAN),
    ("ball_from_interval_2 binary64 -inf -inf -> 0x0p+0 0x0p+0 inf", IV.MAKE_EQUAL_INF),
    ("ball_from_interval_2 binary64 inf 0x1p+0 -> nan nan nan", IV.MAKE_REVERSED),
    ("ball_from_interval_2 binary64 0x1p+0 0x1p+0 -> 0x1p+0 0x0p+0 0x0p+0", IV.MAKE_POINT),
    ("ball_from_interval_2 binary64 -inf 0x1p+0 -> 0x0p+0 0x0p+0 inf", IV.MAKE_UNBOUNDED),
]
GIVEN_STATES = (IV.MAKE_NAN, IV.MAKE_EQUAL_INF, IV.MAKE_REVERSED, IV.MAKE_POINT, IV.MAKE_INTERVAL,
                IV.MAKE_UNBOUNDED)


def _given_states(ctx):
    """Each line of GIVEN passes and counts its given state, and no other."""
    cl = claims6(ctx)
    for line, want in GIVEN:
        kernel = line.split()[0]
        s = judge([line], cl)
        t = totals(s)
        expect(t["judged"] == 1 and t["failed"] == 0, "%s: %s" % (line, t))
        (counts,) = [d[3] for d in entry_stats(s, kernel).values()]
        got = [c for c in GIVEN_STATES if counts.get(c)]
        expect(got == [want] and counts[want] == 1, "%s: counted %s, not %s" % (line, got, want))
    return len(GIVEN)


def _failed_statements(summary, kernel):
    """What failed: the statements (I1 to I6, the parts of ball_of_interval and interval_of_ball)
    for the kinds that count them, the kind of the entry otherwise."""
    out = set()
    for kind, _app, fails, counts, _m in entry_stats(summary, kernel).values():
        if not fails:
            continue
        stm = {c[len("failed "):] for c in counts if c.startswith("failed ")}
        if kind in ("encloses_interval", "ball_of_interval", "interval_of_ball") and stm:
            out |= stm
        else:
            out.add(kind)
    return out


@test
def iv_judge(ctx):
    """Hand-written lines judged as worked out by hand, each failure in its statement or entry;
    lines outside the requirements invalid; the reading of an entry about an output group other
    than the first (mul_dir_2_2: each bound where its own leading limb is finite)."""
    cl = claims6(ctx)
    n = 0
    for line, want in HAND:
        kernel = line.split()[0]
        s = judge([line], cl)
        t = totals(s)
        expect(t["invalid"] == 0 and t["judged"] == 1, "%s: not judged (%s)" % (line, t))
        got = _failed_statements(s, kernel)
        if not want:
            expect(t["failed"] == 0, "%s failed: %s" % (line, got or s.keys))
        else:
            expect(t["failed"] == 1 and got == set(want),
                   "%s: failed %s, not %s" % (line, sorted(got), list(want)))
        n += 1
    for line in INVALID:
        t = totals(judge([line], cl))
        expect(t["invalid"] == 1, "%s: not invalid (%s)" % (line, t))
    # The groups of mul_dir_2_2: the lower bound not finite claims nothing, the upper is judged.
    s = judge(["mul_dir_2_2 binary64 0x1p+0 0x0p+0 0x1p+0 0x0p+0 -> -inf 0x0p+0 0x1p+0 0x1p-104"],
              cl)
    t = totals(s)
    es = entry_stats(s, "mul_dir_2_2")
    expect(t["judged"] == 1 and t["failed"] == 0 and t["suspicious"] == 1,
           "an infinite lower bound beside a finite upper one: %s" % t)
    expect(es["outward(l) below"][3].get(IV.GROUP_NONFINITE) == 1
           and es["outward(h) above"][1] == 1, "the groups counted otherwise: %s" % es)
    s = judge(["mul_dir_2_2 binary64 0x1p+0 0x0p+0 0x1p+0 0x0p+0 -> -inf 0x0p+0 0x1p-1 0x0p+0"],
              cl)
    expect(totals(s)["failed"] == 1 and _failed_statements(s, "mul_dir_2_2") == {"outward"},
           "an upper bound below the value beside an infinite lower bound passed")
    s = judge(["mul_dir_2_2 binary64 0x1p+0 0x0p+0 0x1p+0 0x0p+0 -> -inf 0x0p+0 inf 0x0p+0"], cl)
    t = totals(s)
    expect(t["judged"] == 0 and t["nonfinite"] == 1 and t["suspicious"] == 1,
           "both bounds infinite on small operands: %s" % t)
    g = _given_states(ctx)
    return "%d hand-written lines, %d invalid ones, three of the groups, %d given states" % (
        n, len(INVALID), g)


def _brute_intervals(fmt, limbs):
    """Every canonical interval of a format, from the definition (milestone2.md, "Values of an
    interval"): the empty set, and (l, h) for bounds that are numbers or infinities with l <= h,
    l < +inf, h > -inf."""
    if limbs == 1:
        fin = [(v,) for v in F.all_values(fmt)]
        inf, ninf = (F.POS_INF,), (F.NEG_INF,)
    else:
        fin = G.normalized_pairs(fmt)
        inf, ninf = (F.POS_INF, 0), (F.NEG_INF, 0)
    val = lambda t: t[0] if type(t[0]) is not int else sum(t)
    key = lambda v: (-1, 0) if v == F.NEG_INF else (1, 0) if v == F.POS_INF else (0, v)
    bounds = [ninf] + list(fin) + [inf]
    out = {inf + ninf}
    for a in bounds:
        for b in bounds:
            if val(a) != F.POS_INF and val(b) != F.NEG_INF and key(val(a)) <= key(val(b)):
                out.add(tuple(a) + tuple(b))
    return out


@test
def iv_gen(ctx):
    """The generator of the interval kernels: case i alone is case i of its run; the seed matters;
    every case valid (the checker agrees); every stratum of the header in a run of one cycle, and
    no other; the enumeration of an interval operand is every canonical interval, as counted from
    the definition, and a restriction keeps the infinite bounds and the empty set."""
    cl = claims6(ctx)
    n = ctx.n(400, 150)
    for k in KERNELS:
        kern = cl.get(k)
        for fname in ("binary64", "fp:4:-6:1"):
            fmt = F.parse_format(fname)
            g = G.RandomGen(kern, fmt, "s")
            lines = list(g.lines(0, n))
            expect(g.case(7) == lines[8], "%s %s: case 7 alone is not case 7" % (k, fname))
            g2 = G.RandomGen(kern, fmt, "t")
            expect(g2.case(7) != g.case(7) or g2.case(9) != g.case(9), "%s: the seed does not "
                   "matter" % k)
            s = judge([ln + " -> " + " ".join("0x0p+0" for _ in range(sum(l for _, l in
                                                                              kern.outputs)))
                       for ln in lines[1:-1]], cl)
            expect(totals(s)["invalid"] == 0, "%s %s: an invalid case: %s" % (
                k, fname, [ex for st in s.keys.values() for ex in st.examples["invalid"]][:2]))
            tags = {ln.split("#")[1].split(":")[0] for ln in lines[1:-1]}
            expect(tags == set(g.strata), "%s %s: strata %s, header %s" % (
                k, fname, sorted(tags), g.strata))
            if gen6.family_of(kern) is not None:
                expect(set(gen6.COMMON) <= set(g.strata), "%s: a common stratum missing" % k)
            if k in ("interval_mid_rad_1", "ball_from_interval_2"):
                # oddeta aims at bounds that are odd multiples of eta below 2N, whose halves are
                # not numbers: most of its cases have one (other strata, a subnormal by chance).
                go = G.RandomGen(kern, fmt, "s", strata=["oddeta"])
                odd = 0
                cases = [ln for ln in go.lines(0, 200) if not ln.startswith("#")
                         and "#oddeta" in ln]
                expect(len(cases) >= 150, "%s %s: %d cases of oddeta" % (k, fname, len(cases)))
                for ln in cases:
                    vs = [F.parse_limb(fmt, t) for t in ln.split()[2:4]]
                    odd += any(type(v) is int and v % 2 and abs(v) < 2 * fmt.lam for v in vs)
                expect(odd * 4 >= 3 * len(cases), "%s %s: oddeta gave an odd bound below 2N in "
                       "%d of %d cases" % (k, fname, odd, len(cases)))
    # The enumeration of intervals against the definition, in two tiny formats.
    for fname, k, limbs in (("fp:2:-1:0", "interval_neg_1", 1), ("fp:3:-2:-1", "interval_neg_2", 2),
                            ("fp:2:-1:0", "interval_hull_1", 1)):
        fmt = F.parse_format(fname)
        want = _brute_intervals(fmt, limbs)
        g = G.ExhaustiveGen(cl.get(k), fmt)
        n_ops = 1 if k.startswith("interval_neg") else 2
        expect(g.total == len(want) ** n_ops, "%s %s: %d enumeration indices, the definition "
               "gives %d" % (k, fname, g.total, len(want) ** n_ops))
        got = set()
        for i in range(0, g.total, len(want) ** (n_ops - 1)):
            toks = g.case(i).split()[2:2 + 2 * limbs]
            got.add(tuple(F.parse_limb(fmt, t) for t in toks))
        expect(got == want, "%s %s: the intervals enumerated are not those of the definition"
               % (k, fname))
    g = G.ExhaustiveGen(cl.get("interval_neg_1"), F.parse_format("fp:2:-1:0"),
                        ["xl.in=0x1p+0", "xu.in=0x1p+0"])
    texts = {" ".join(g.case(i).split()[2:4]) for i in range(g.total)}
    expect({"inf -inf", "-inf inf", "0x1p+0 0x1p+0", "-inf 0x1p+0", "0x1p+0 inf"} == texts,
           "a restricted enumeration of intervals: %s" % sorted(texts))
    return "%d kernels in two formats; three enumerations against the definition" % len(KERNELS)


@test
def iv_merging(ctx):
    """The merge of the summaries of two halves of streams of the interval kernels is the summary
    of the whole."""
    cl = claims6(ctx)
    for k in ("interval_mul_1", "interval_add_2", "mul_dir_2_2", "interval_mid_rad_1"):
        lines = run6(stream6(ctx, k, "binary64", ctx.n(600, 200)))
        body = [ln for ln in lines if not ln.startswith("#")]
        whole = judge(body, cl)
        a = judge(body[:len(body) // 2], cl)
        b = judge(body[len(body) // 2:], cl)
        m = C.Summary()
        m.merge(a)
        m.merge(b)
        expect(json.dumps(m.to_json()["keys"], sort_keys=True)
               == json.dumps(whole.to_json()["keys"], sort_keys=True), "%s: merge differs" % k)
    return "four kernels"


def scaled6(factor):
    """The fixture with the constants rel and abs of every outward bound multiplied by factor."""
    data = raw6()
    for k in data["kernels"]:
        for e in k["ensures"]:
            t = e if e.get("kind") == "outward" else e.get("tight") if isinstance(e.get("tight"),
                                                                                  dict) else None
            if t is not None and "rel" in t and t.get("kind", "outward") == "outward":
                t["rel"] = "(%s)*%s" % (t["rel"], factor)
                t["abs"] = "(%s)*%s" % (t["abs"], factor)
    return Claims(data, "<scaled by %s>" % factor)


@test
def iv_scaled(ctx):
    """The bounds of two limbs with rel and abs times 1024 pass, with every largest fraction of the
    bound 1024 times smaller; divided by 8 they fail."""
    cl = claims6(ctx)
    up, down = scaled6("1024"), scaled6("1/8")
    for k in ("add_down_2_2", "mul_dir_2_2", "interval_add_2", "mul_ext_2_2"):
        lines = [ln for ln in run6(stream6(ctx, k, "binary64", ctx.n(800, 300)))
                 if not ln.startswith("#")]
        base, big, small = judge(lines, cl), judge(lines, up), judge(lines, down)
        expect(totals(big)["failed"] == 0, "%s: times 1024 fails" % k)
        expect(totals(small)["failed"] > 0, "%s: divided by 8 passes" % k)
        b0, b1 = entry_stats(base, k), entry_stats(big, k)
        for label, d in b0.items():
            for name, r in d[4].items():
                if "/ (rel" in name:
                    expect(b1[label][4][name] * 1024 == r, "%s %s: %s scaled to %s, not %s/1024"
                           % (k, label, name, b1[label][4][name], r))
    return "four kernels"
