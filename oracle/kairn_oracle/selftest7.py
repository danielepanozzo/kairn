"""The oracle's own tests for the folds' stage of Milestone 2 (architecture.md, "Folds", "Claims of
Milestone 2", "The line protocol"; milestone2.md, "Batch kernels"): the folds and their requests
of arrays, `fold_error`, `finite_or_nan`, the bound kernels' `upper` with a value of its own and
`holds` under a mask, the error form `T`, the requirements `count()` and `format(half)`.

As for the earlier waves, each test compares the oracle with something it does not share code with:
the expressions of the claims against Python's own arithmetic on Fractions; the brackets of the
powers against the exact powers; the reference runner (written from the listings of
architecture.md and milestone2.md) on random streams and on every array of tiny formats; planted
faults that must be caught in the entry where they belong and nowhere else; hand-written lines
whose verdicts are worked out by hand.  The fixture, oracle/selftest/claims-wave5.json, holds the
kernels and folds of the stage and the kernels whose bounds they name, frozen.
"""

import concurrent.futures as cf
import copy
import json
import os
import random
from fractions import Fraction as Q

from . import cexpr as CX
from . import check as C
from . import fmt as F
from . import folds as FO
from . import gen as G
from . import genfold as GF
from . import refrun
from .claims import Claims, ClaimsError, load_claims
from .selftest import test, expect, judge, totals, ORACLE_DIR

FIXTURE5 = os.path.join(ORACLE_DIR, "selftest", "claims-wave5.json")
FOLDS = ("sum_1", "sum_1_entry", "sum_2", "sum_2_entry", "sum_fast_2", "sum_fast_2_entry", "dot_1",
         "dot_2")
ONE_LIMB = ("sum_1", "sum_1_entry", "dot_1")
BOUNDS = ("bound_sum_1", "bound_sum_2", "bound_dot_1", "bound_dot_2")
STEPS = ("dot_step_1", "dot_step_2", "sum_entry_step_1", "sum_entry_step_2", "sum_fast_entry_step_2")
FINISHES = ("fold_finish_1", "fold_finish_2")
# Toy formats of the shape of the extended domain, and at least each fold's min_precision; for two
# limbs with exponents enough to hold the literature's tight cases (3p binades).
TOY_FOLD = {"sum_1": "fp:4:-6:1", "sum_1_entry": "fp:4:-6:1", "dot_1": "fp:4:-6:1",
            "sum_2": "fp:4:-10:5", "sum_2_entry": "fp:4:-10:5", "sum_fast_2": "fp:4:-10:5",
            "sum_fast_2_entry": "fp:4:-10:5", "dot_2": "fp:5:-12:5"}


def claims5(ctx):
    if not hasattr(ctx, "claims5"):
        ctx.claims5 = load_claims(FIXTURE5)
    return ctx.claims5


def raw5():
    with open(FIXTURE5, encoding="utf-8") as fh:
        return json.load(fh)


def run5(lines, variant="correct"):
    r = refrun.Runner(variant, bound_claims=FIXTURE5)
    out = []
    for ln in lines:
        out.extend(r.complete(ln))
    return out


def fold_stream(ctx, fold, fmtname, count, orders=None, max_length=64, strata=None,
                seed="selftest7"):
    key = ("w5", fold, fmtname, count, orders, max_length, strata, seed)
    s = ctx._streams.get(key)
    if s is None:
        g = GF.RandomFoldGen(claims5(ctx).get_fold(fold), F.parse_format(fmtname), seed,
                             strata.split(",") if strata else None,
                             orders.split(",") if orders else None, max_length)
        s = ctx._streams[key] = list(g.lines(0, count))
    return s


def kernel_stream(ctx, kernel, fmtname, count, seed="selftest7"):
    key = ("w5k", kernel, fmtname, count, seed)
    s = ctx._streams.get(key)
    if s is None:
        g = G.RandomGen(claims5(ctx).get(kernel), F.parse_format(fmtname), seed)
        s = ctx._streams[key] = list(g.lines(0, count))
    return s


def entry_stats(summary, name):
    """{label: (kind, applicable, failures, counts, max ratio)} of a kernel or fold, summed."""
    out = {}
    for (k, _f, _t), st in summary.keys.items():
        if k != name:
            continue
        for e in st.entries:
            d = out.setdefault(e.label, [e.kind, 0, 0, {}, None, {}, {}])
            d[1] += e.applicable
            d[2] += e.failures
            for c, n in e.counts.items():
                d[3][c] = d[3].get(c, 0) + n
            if e.max_ratio is not None and e.max_ratio[1] and (
                    d[4] is None or Q(*e.max_ratio) > d[4]):
                d[4] = Q(*e.max_ratio)
            for c, (r, _l) in e.maxima.items():
                if r[1] and (c not in d[5] or Q(*r) > d[5][c]):
                    d[5][c] = Q(*r)
            for c, (r, _l) in e.minima.items():
                if r[1] and (c not in d[6] or Q(*r) < d[6][c]):
                    d[6][c] = Q(*r)
    return out


def failed_kinds(summary, name):
    return {lab.split("(")[0].split(" ")[0]: d[2] for lab, d in entry_stats(summary, name).items()
            if d[2]}


def one_line(ctx, line, ignore=False):
    s = judge([line], claims5(ctx), ignore_min_precision=ignore)
    return s, totals(s)


# ---------------------------------------------------------------------------

@test
def claims_reading_wave5(ctx):
    """The fixture of the folds' stage reads whole; malformed kernels and folds are set aside
    with a reason, without making the others unreadable."""
    cl = claims5(ctx)
    expect(not cl.broken, "the fixture does not read: %s" % cl.broken)
    expect(sorted(cl.folds) == sorted(FOLDS), "folds read: %s" % sorted(cl.folds))
    for k in BOUNDS:
        expect(cl.get(k).conditional, "%s is not read as conditional" % k)
    expect(cl.get("dot_step_2").ensures[1].form == "T", "form T")
    expect(cl.get("bound_sum_2").format_requires == ["half"], "format(half)")
    expect(("count", "m") in cl.get("bound_dot_2").requires, "count(m)")
    raw = raw5()
    ks = {k["name"]: k for k in raw["kernels"]}
    fs = {f["name"]: f for f in raw["folds"]}

    def kern(name, f):
        k = copy.deepcopy(ks[name])
        f(k)
        return k

    def fold(name, f):
        k = copy.deepcopy(fs[name])
        f(k)
        return k

    def ens(k, i, **kw):
        k["ensures"][i].update(kw)

    def drop(k, i, key):
        del k["ensures"][i][key]

    bad_kernels = [
        kern("dot_step_2", lambda k: ens(k, 1, form="S")),
        kern("dot_step_2", lambda k: k["requires"].append("count(s)")),
        kern("bound_sum_1", lambda k: k.update(requires=["count(g)", "format(half)"])),
        kern("bound_sum_1", lambda k: k.update(requires=["count(m)", "format(full)"])),
        kern("bound_sum_1", lambda k: k.update(requires=["count(m)", "format(half)", "format(half)"])),
        kern("bound_sum_1", lambda k: drop(k, 1, "if")),
        kern("bound_sum_1", lambda k: ens(k, 1, gaps="1")),
        kern("bound_sum_1", lambda k: ens(k, 1, **{"if": "g"})),
        kern("bound_sum_1", lambda k: ens(k, 0, args=["m*unit(add_1_1)"])),
        kern("bound_sum_1", lambda k: ens(k, 0, rel="ge")),
        kern("bound_sum_1", lambda k: ens(k, 1, value="m*unit(nothing)/(1-m)")),
        kern("bound_sum_1", lambda k: ens(k, 1, value="m*unit(dot_step_1)")),
        kern("bound_sum_1", lambda k: ens(k, 1, value="m*unit(add_1_1)^m")),
        kern("bound_sum_1", lambda k: ens(k, 1, value="m*unit(add_1_1)/(1-ok)")),
        kern("bound_sum_1", lambda k: ens(k, 1, value="m*(unit(add_1_1)")),
        kern("bound_sum_1", lambda k: k["ensures"].append({"kind": "normalized", "of": "g"})),
        kern("bound_sum_1", lambda k: k.update(domain="extended")),
        kern("fold_finish_2", lambda k: k.pop("domain")),
        kern("fold_finish_2", lambda k: ens(k, 0, flag="r")),
        kern("fold_finish_2", lambda k: ens(k, 0, of="flag")),
        kern("fold_finish_2", lambda k: k["ensures"].append({"kind": "normalized", "of": "r"})),
        kern("fold_finish_2", lambda k: k.update(value="-s")),
        kern("fold_finish_1", lambda k: drop(k, 0, "flag")),
    ]
    bad_folds = [
        fold("sum_2", lambda f: f.update(domain="finite")),
        fold("sum_2", lambda f: f.update(requires=[])),
        fold("sum_2", lambda f: f.update(requires=["normalized(x)"])),
        fold("sum_2", lambda f: f.update(orders=["sequential", "tree"])),
        fold("sum_2", lambda f: f.update(orders=[])),
        fold("sum_2", lambda f: f.update(step="no_such_kernel")),
        fold("sum_2", lambda f: f.update(combine=None)),
        fold("sum_2", lambda f: f.update(value="abs(x)+")),
        fold("sum_2", lambda f: f.update(value="z")),
        fold("sum_2", lambda f: f["ensures"].pop(2)),
        fold("sum_2", lambda f: f["ensures"].append({"kind": "error", "of": "r"})),
        fold("sum_2", lambda f: ens(f, 1, eps="0")),
        fold("sum_2", lambda f: ens(f, 1, eps="u^2/(1-2*u)")),
        fold("sum_2", lambda f: ens(f, 1, tau="-eta")),
        fold("sum_2", lambda f: ens(f, 1, eps="x*u")),
        fold("sum_2", lambda f: ens(f, 1, heights={"sequential": {"rel": "n-1", "abs": "n-1"}})),
        fold("sum_2", lambda f: ens(f, 1, heights={"sequential": {"rel": "n-2", "abs": "n-1"},
                                                   "lanes": {"rel": "n-1", "abs": "n-1"}})),
        fold("sum_2", lambda f: ens(f, 2, flag="r")),
        fold("sum_2", lambda f: ens(f, 1, of="flag")),
        fold("sum_2", lambda f: f["arrays"][0].update(role="borrowed")),
        fold("sum_2", lambda f: f["arrays"][0].update(limbs=0)),
        fold("sum_2", lambda f: f.update(packed_lanes={"binary64": {"neon": 0}})),
        fold("sum_2", lambda f: f.update(status="maybe")),
        fold("sum_2", lambda f: f["instances"]["binary64"][0].update(eps="1/3")),
        fold("sum_2", lambda f: f.update(name="add_2_2")),
    ]
    data = copy.deepcopy(raw)
    for i, k in enumerate(bad_kernels):
        k["name"] = "bad_kernel_%d" % i
        data["kernels"].append(k)
    for i, f in enumerate(bad_folds):
        if f["name"] != "add_2_2":
            f["name"] = "bad_fold_%d" % i
        data["folds"].append(f)
    cl2 = Claims(data, "<malformed>")
    for i in range(len(bad_kernels)):
        expect("bad_kernel_%d" % i in cl2.broken, "malformed kernel %d read: %s" % (
            i, json.dumps(bad_kernels[i]["ensures"])[:200]))
    for i, f in enumerate(bad_folds):
        name = f["name"] if f["name"] == "add_2_2" else "bad_fold_%d" % i
        expect(name in cl2.broken, "malformed fold %d read" % i)
    for k in list(ks):
        if k != "add_2_2":
            expect(cl2.get(k) is not None, "%s became unreadable: %s" % (k, cl2.broken.get(k)))
    for f in FOLDS:
        expect(cl2.get_fold(f) is not None, "%s became unreadable" % f)
    # A kernel whose expressions name a kernel that cannot be read is set aside with it.
    data = copy.deepcopy(raw)
    for k in data["kernels"]:
        if k["name"] == "add_1_1":
            k["ensures"][1]["form"] = "Z"
    cl3 = Claims(data, "<add_1_1 broken>")
    expect("bound_sum_1" in cl3.broken and cl3.get_fold("sum_1") is not None,
           "unit(add_1_1) of a broken add_1_1 read, or sum_1 (whose step it is) set aside: %s"
           % sorted(cl3.broken))
    # No folds at all: the reader of the kernels sees nothing new.
    data = copy.deepcopy(raw)
    del data["folds"]
    expect(not Claims(data, "<no folds>").folds, "a file without folds has folds")
    return "%d malformed kernels and %d malformed folds set aside" % (len(bad_kernels), len(bad_folds))


def _rand_cexpr(rnd, depth=0):
    """A random expression and its value, written by Python's Fraction arithmetic directly."""
    k = rnd.randrange(8 if depth < 4 else 3)
    if k == 0:
        n = rnd.randrange(1, 9)
        return str(n), Q(n)
    if k == 1:
        return "u", Q(1, 64)
    if k == 2:
        return "eta", Q(1, 1 << 20)
    a, va = _rand_cexpr(rnd, depth + 1)
    b, vb = _rand_cexpr(rnd, depth + 1)
    if k == 3:
        return "(%s+%s)" % (a, b), va + vb
    if k == 4:
        return "(%s-%s)" % (a, b), va - vb
    if k == 5:
        return "(%s*%s)" % (a, b), va * vb
    if k == 6 and vb != 0:
        return "(%s/%s)" % (a, b), va / vb
    e = rnd.randrange(-3, 4)
    if va == 0 and e < 0:
        e = 2
    return "(%s)^%d" % (a, e) if e >= 0 else "(%s)^-%d" % (a, -e), va ** e


@test
def cexpr_exact(ctx):
    """The expressions of the folds' stage against Fractions computed directly; the precedence of
    unary minus and ^; malformed expressions refused."""
    rnd = random.Random(20261120)
    env = {"u": Q(1, 64), "eta": Q(1, 1 << 20), "names": {"m": Q(3)},
           "unit": lambda k: Q(1, 7), "tiny": lambda k: Q(1, 11)}
    n = ctx.n(3000, 600)
    for _ in range(n):
        text, want = _rand_cexpr(rnd)
        got = CX.evaluate(CX.parse(text), env)
        expect(got == want, "%s = %s, not %s" % (text, got, want))
    for text, want in (("-2^2", Q(-4)), ("2^3^2", Q(512)), ("2^-3", Q(1, 8)), ("1-2-3", Q(-4)),
                       ("8/2/2", Q(2)), ("m*unit(x)/(1-m*unit(x))", Q(3, 7) / (1 - Q(3, 7))),
                       ("m*tiny(x)*(1+m)", Q(3, 11) * 4), ("+u", Q(1, 64))):
        got = CX.evaluate(CX.parse(text), env)
        expect(got == want, "%s = %s, not %s" % (text, got, want))
    for text in ("", "1+", "(1", "1)", "unit(1)", "unit(u)", "2^m", "2^(1+m)", "1 2", "u.5",
                 "tiny x", "3 % 2"):
        try:
            CX.parse(text)
        except CX.CExprError:
            continue
        raise AssertionError("%r parsed" % text)
    for text in ("1/(1-1)", "0^-1", "2^(1/2)"):
        try:
            CX.evaluate(CX.parse(text), env)
        except CX.CExprError:
            continue
        raise AssertionError("%r evaluated" % text)
    return "%d random expressions" % n


@test
def fold_brackets(ctx):
    """The brackets of the powers hold the exact power; the bound decided from them is the bound
    decided exactly, on errors placed at the exact bound and a hair to either side."""
    rnd = random.Random(7)
    n = ctx.n(400, 120)
    for _ in range(n):
        eps = Q(rnd.randrange(1, 9), 1 << rnd.randrange(3, 110)) / rnd.choice((1, 3, 5, 7))
        h = rnd.choice((0, 1, 2, 3, rnd.randrange(4, 100), rnd.randrange(100, 5000)))
        P = eps.denominator.bit_length() + 96 + 2 * max(h, 1).bit_length()
        lo, hi = FO.pow_bracket(eps.numerator + eps.denominator, eps.denominator, h, P)
        x = (1 + eps) ** h
        expect(Q(lo, 1 << P) <= x <= Q(hi, 1 << P), "bracket of (1 + %s)^%d" % (eps, h))
        expect((hi - lo) << 64 <= hi, "a bracket wider than 2^-64 of the power at h=%d" % h)
        term = Q(rnd.randrange(0, 5), 1 << rnd.randrange(3, 110))
        hh = FO.Heights(eps, term, h, max(h - 1, 0))
        Gn, Gd, An, Ad = hh.exact(eps, term)
        G, A = Q(Gn, Gd), Q(An, Ad)
        expect(G == (1 + term) * x - 1 and A == (1 + eps) ** max(h - 1, 0), "exact powers")
        expect(Q(hh.gl, term.denominator << hh.P) <= G <= Q(hh.gh, term.denominator << hh.P),
               "bracket of G")
    # The judge on lines at the exact bound: sum_1 of [1, d, ..., d] where the claim's bound is
    # met with equality would need a result off the format; instead the decision is compared with
    # the exact rule on the judge's own numbers through exact_compare.
    c = {"eps": Q(1, 9007199254740993), "term": Q(0)}
    for _ in range(ctx.n(300, 80)):
        h = rnd.randrange(0, 3000)
        hh = FO.Heights(c["eps"], c["term"], h, h)
        S = rnd.randrange(1, 1 << 200)
        tau = Q(rnd.randrange(0, 3), rnd.randrange(1, 5))
        Gn, Gd, An, Ad = hh.exact(c["eps"], c["term"])
        B = Q(Gn, Gd) * S + Q(An, Ad) * 7 * tau
        for err in (int(B), int(B) + 1, max(int(B) - 1, 0)):
            num, den = FO.exact_compare(hh, c, err, S, 7, tau)
            expect((num > den) == (err > B), "exact_compare at h=%d" % h)
    return "%d brackets" % n


@test
def fold_reference(ctx):
    """The reference runner, written from architecture.md's definition of the two orders, passes
    every fold on random arrays of every stratum, length class and order, in binary64, binary32
    and a toy format, and reaches the classes the cross-checks' guards ask for."""
    cl = claims5(ctx)
    n = ctx.n(500, 260)
    notes = []
    for fold in FOLDS:
        for fmtname in ("binary64", "binary32", TOY_FOLD[fold]):
            lines = run5(fold_stream(ctx, fold, fmtname, n, max_length=200))
            s = judge(lines, cl)
            t = totals(s)
            expect(t["failed"] == 0 and t["invalid"] == 0 and t["suspicious"] == 0
                   and not s.stream_errors, "%s %s: %s" % (fold, fmtname, t))
            st = entry_stats(s, fold)
            fe = next(d for d in st.values() if d[0] == "fold_error")
            fl = next(d for d in st.values() if d[0] == "finite_or_nan")
            for k in ["length %d" % m for m in GF.LENGTH_SCHEDULE if m != "r"] + [
                    "order: sequential", "order: lanes, W = 0", "order: lanes, W = 1",
                    "order: lanes, W = 2", "order: lanes, W = 3", "order: lanes, W = 4",
                    "order: lanes, W = 5", "order: lanes, W = 8",
                    "order: lanes, more lanes than elements (W > n >= 1)",
                    "heavy cancellation: |sum| <= u * sum of magnitudes"]:
                expect(fe[3].get(k), "%s %s: no case of %r" % (fold, fmtname, k))
            for k in ("flag true", "flag false: a non-finite element",
                      "flag false: finite elements, near overflow"):
                expect(fl[3].get(k), "%s %s: no case of %r" % (fold, fmtname, k))
            expect(not fl[3].get("flag false: finite elements far from overflow"), "far")
            if fold.startswith("dot"):
                for k in ("absolute term larger than the relative term",
                          "error above the relative term alone"):
                    expect(fe[3].get(k), "%s %s: no case of %r" % (fold, fmtname, k))
            need = Q(1, 2) if fold in ONE_LIMB else Q(1, 16)
            expect(fe[4] is not None and fe[4] >= need, "%s %s: largest error/allowed %s" % (
                fold, fmtname, fe[4]))
            notes.append("%s %s %.3g" % (fold, fmtname, float(fe[4])))
    return "largest error/allowed: " + ", ".join(notes)


# The planted faults of the folds, each with the entries that must catch it, and those that may
# too: an element left out may be the one that is not finite, and the flag then is true although
# an element is not.
FOLD_PLANTED = {
    "fold-drop-last": (FOLDS, {"fold_error"}, {"finite_or_nan"}),
    "fold-lanes-skip-lane": (FOLDS, {"fold_error"}, {"finite_or_nan"}),
    "dot-single-product": (("dot_2",), {"fold_error"}, set()),
    "flag-true-nan": (FOLDS, {"finite_or_nan"}, set()),
    "flag-false-finite": (FOLDS, {"finite_or_nan"}, set()),
    "fold-not-normalized": (("sum_2", "sum_2_entry", "sum_fast_2", "sum_fast_2_entry", "dot_2"),
                            {"normalized"}, set()),
}


@test
def fold_planted(ctx):
    """Each planted fault of the folds fails in the entry where it belongs and nowhere else, and
    leaves the folds it does not touch alone; the lane order combined from the last lane down
    changes the bits of some results and fails nothing, since the claim is a bound for every
    order, not an order."""
    cl = claims5(ctx)
    n = ctx.n(400, 200)
    notes = []
    for variant, (folds, kinds, also) in FOLD_PLANTED.items():
        for fold in FOLDS:
            for fmtname in ("binary64", TOY_FOLD[fold]):
                s = judge(run5(fold_stream(ctx, fold, fmtname, n, max_length=64), variant), cl)
                fk = failed_kinds(s, fold)
                if fold in folds:
                    expect(kinds <= set(fk) <= kinds | also, "%s on %s %s fails %s, not %s" % (
                        variant, fold, fmtname, fk or "nothing", sorted(kinds)))
                else:
                    expect(not fk, "%s fails %s %s, which it does not touch: %s" % (
                        variant, fold, fmtname, fk))
        notes.append(variant)
    changed = 0
    for fold in FOLDS:
        lines = fold_stream(ctx, fold, "binary64", n, max_length=64)
        good, rev = run5(lines), run5(lines, "fold-lanes-reverse")
        changed += sum(1 for a, b in zip(good, rev) if a != b)
        s = judge(rev, cl)
        expect(totals(s)["failed"] == 0, "the lanes combined in another order fail %s" % fold)
    expect(changed > 0, "the lanes combined from the last one down changed no bits")
    return "%s caught; the reversed combination changed %d results and passed" % (
        ", ".join(notes), changed)


def _fold_exhaustive(ctx, fold, fmtname, L, variant="correct"):
    g = GF.ExhaustiveFoldGen(claims5(ctx).get_fold(fold), F.parse_format(fmtname), L)
    lines = run5(list(g.lines(0, g.total)), variant)
    return judge(lines, claims5(ctx)), g.total


@test
def fold_exhaustive(ctx):
    """Every array of tiny formats up to a small length, in every order that differs, through the
    reference runner: nothing fails; the planted faults are caught there too."""
    cases = [("sum_1", "fp:2:-2:1", 2), ("sum_2", "fp:3:-2:-1", 2),
             ("sum_fast_2", "fp:3:-2:-1", 2), ("dot_1", "fp:2:-1:0", 2), ("dot_2", "fp:4:-3:-2", 1)]
    if not ctx.quick:
        cases += [("sum_1_entry", "fp:2:-2:1", 3), ("dot_1", "fp:1:-2:1", 2),
                  ("sum_2_entry", "fp:3:-2:-1", 2), ("sum_fast_2_entry", "fp:2:-1:0", 3)]
    n = 0
    for fold, fmtname, L in cases:
        s, total = _fold_exhaustive(ctx, fold, fmtname, L)
        t = totals(s)
        n += total
        expect(t["failed"] == 0 and t["invalid"] == 0 and t["suspicious"] == 0 and
               t["judged"] == total, "%s %s up to %d: %s" % (fold, fmtname, L, t))
        cov = s.coverage.describe()
        expect(cov and "COMPLETE" in cov[0], "coverage: %s" % cov)
    for variant, fold, fmtname, L, kind in (("fold-drop-last", "sum_1", "fp:2:-2:1", 2, "fold_error"),
                                            ("flag-false-finite", "dot_1", "fp:2:-1:0", 1,
                                             "finite_or_nan"),
                                            ("fold-not-normalized", "sum_2", "fp:3:-2:-1", 1,
                                             "normalized")):
        s, _ = _fold_exhaustive(ctx, fold, fmtname, L, variant)
        fk = set(failed_kinds(s, fold))
        expect(kind in fk and fk <= {kind, "finite_or_nan"}, "%s on every array: %s" % (
            variant, failed_kinds(s, fold)))
    return "%d arrays" % n


def _hx(v):
    return float(v).hex() if v != 0 else "0x0p+0"


@test
def fold_judge(ctx):
    """Hand-written lines of the folds, each verdict worked out by hand."""
    u = 2.0 ** -53
    d = (2 * u) / 2 * (1 - 2 ** -52)            # pred(u): just below half an ulp of 1
    D = _hx(d)
    cases = [
        # (line, ok, invalid, suspicious, failing entry kinds)
        ("sum_2 binary64 seq 0 #h:0 -> 0x0p+0 0x0p+0 1", True, False, False, set()),
        ("sum_2 binary64 seq 0 #h:1 -> 0x1p-1074 0x0p+0 1", False, False, False, {"fold_error"}),
        # [1, d, d] sequential: each addition drops d, error 2d; the bound with h = 2 is
        # ((1 + eps)^2 - 1)(1 + 2d) > 2d; with h = 1 (a height n-1 read as n-2) it would fail.
        ("sum_1 binary64 seq 3 0x1p+0 %s %s #h:2 -> 0x1p+0 1" % (D, D), True, False, False, set()),
        # The same with 1 + 2u: the error 2u - 2d = 2^-104 is within the bound.
        ("sum_1 binary64 seq 3 0x1p+0 %s %s #h:3 -> 0x1.0000000000001p+0 1" % (D, D), True, False,
         False, set()),
        # [1, d] with the result 1 + 2u: error 2u - d ~ u > ((1 + eps) - 1)(1 + d) ~ u (1 - u).
        ("sum_1 binary64 seq 2 0x1p+0 %s #h:4 -> 0x1.0000000000001p+0 1" % D, False, False, False,
         {"fold_error"}),
        # A false flag with a NaN result: right for an infinite element, suspicious for finite ones
        # far from overflow, a failure with a finite limb.
        ("sum_1 binary64 lanes:2 2 inf 0x1p+0 #h:5 -> nan 0", True, False, False, set()),
        ("sum_1 binary64 seq 2 0x1p+0 0x1p+1 #h:6 -> nan 0", True, False, True, set()),
        ("sum_1 binary64 seq 2 inf 0x1p+0 #h:7 -> 0x1p+0 0", False, False, False, {"finite_or_nan"}),
        ("sum_1 binary64 seq 2 inf 0x1p+0 #h:8 -> inf 1", False, False, False, {"finite_or_nan"}),
        ("sum_1 binary64 seq 2 inf 0x1p+0 #h:9 -> 0x1p+0 1", False, False, False, {"finite_or_nan"}),
        ("sum_2 binary64 seq 1 0x1p+0 0x0p+0 #h:10 -> 0x1p+0 nan 1", False, False, False,
         {"finite_or_nan"}),
        ("sum_2 binary64 seq 1 0x1p+0 0x0p+0 #h:11 -> nan 0x0p+0 0", False, False, True,
         {"finite_or_nan"}),
        # Partial sums that overflow although the exact sum does not: a false flag is right.
        ("sum_1 binary64 seq 3 0x1.fffffffffffffp+1023 0x1.fffffffffffffp+1023 "
         "-0x1.fffffffffffffp+1023 #h:12 -> nan 0", True, False, False, set()),
        # An element that is not canonical is invalid; one not a number of the format too.
        ("sum_2 binary64 seq 1 0x1p+0 0x1p+0 #h:13 -> 0x1p+1 0x0p+0 1", True, True, False, set()),
        ("sum_1 binary32 seq 1 0x1.0000000000001p+0 #h:14 -> 0x1p+0 1", True, True, False, set()),
        # A result that is not normalized.
        ("sum_2 binary64 seq 1 0x1p+0 0x1p-53 #h:15 -> 0x1.0000000000001p+0 -0x1p-53 1", False,
         False, False, {"normalized"}),
        # dot_2 of one product below eta: the error 2^-1075 is within tau = 3/2 eta.
        ("dot_2 binary64 seq 1 0x1p-537 0x0p+0 0x1p-538 0x0p+0 #h:16 -> 0x0p+0 0x0p+0 1", True,
         False, False, set()),
        ("dot_2 binary64 seq 1 0x1p-537 0x0p+0 0x1p-537 0x0p+0 #h:17 -> 0x1p-1072 0x0p+0 1", False,
         False, False, {"fold_error"}),
        # dot_1 of 3 * (1 + 2u) = 3 + 6u: RN is 3 + 4u, error 2u, bound ((1 + eps) - 1) |3 + 6u|.
        ("dot_1 binary64 seq 1 0x1.8p+1 0x1.0000000000001p+0 #h:18 -> 0x1.8000000000001p+1 1",
         True, False, False, set()),
        ("dot_1 binary64 seq 1 0x1.8p+1 0x1.0000000000001p+0 #h:19 -> 0x1.8000000000003p+1 1",
         False, False, False, {"fold_error"}),
    ]
    cl = claims5(ctx)
    for line, ok, invalid, sus, kinds in cases:
        s = judge([line], cl)
        t = totals(s)
        fold = line.split()[0]
        expect((t["failed"] == 0) == ok, "%s: failed %d" % (line, t["failed"]))
        expect((t["invalid"] == 1) == invalid, "%s: invalid %d" % (line, t["invalid"]))
        expect((t["suspicious"] == 1) == sus, "%s: suspicious %d" % (line, t["suspicious"]))
        if not invalid:
            expect(set(failed_kinds(s, fold)) == kinds, "%s fails %s" % (line, failed_kinds(s, fold)))
    # The reason says what is wrong: a flag that is not whether limb 0 is finite.
    for line, why in (("sum_1 binary64 seq 2 inf 0x1p+0 -> 0x1p+0 0",
                       "the flag is 0 although limb 0 of the result is finite"),
                      ("sum_1 binary64 seq 2 inf 0x1p+0 -> inf 1",
                       "the flag is 1 although limb 0 of the result is inf")):
        reasons = [r for st in judge([line], cl).keys.values() for r in st.reasons]
        expect(reasons == [why], "%s: %s" % (line, reasons))
    # Malformed lines and orders the fold does not claim fail; a precision below the fold's
    # min_precision is out of scope.
    for line in ("sum_1 binary64 tree 1 0x1p+0 -> 0x1p+0 1", "sum_1 binary64 lanes:02 1 0x1p+0 -> 0x1p+0 1",
                 "sum_1 binary64 seq 2 0x1p+0 -> 0x1p+0 1", "sum_1 binary64 seq 1 0x1p+0 -> 0x1p+0",
                 "sum_1 binary64 seq 1 0x1p+0", "sum_1 binary64 seq 1 0x1p+0 -> 0x1p+0 2",
                 "sum_1 binary64 seq 01 0x1p+0 -> 0x1p+0 1"):
        expect(totals(judge([line], cl))["failed"] == 1, "%r passed" % line)
    data = raw5()
    for f in data["folds"]:
        if f["name"] == "sum_1":
            f["orders"] = ["sequential"]
            f["ensures"][0]["heights"] = {"sequential": {"rel": "n-1", "abs": "n-1"}}
            f.pop("theorems", None)
    expect(totals(judge(["sum_1 binary64 lanes:2 1 0x1p+0 -> 0x1p+0 1"],
                        Claims(data, "<seq only>")))["failed"] == 1, "a lane order not claimed")
    t = totals(judge(["sum_2 fp:2:-3:1 seq 1 0x1p+0 0x0p+0 -> 0x1p+0 0x0p+0 1"], cl))
    expect(t["out_of_scope"] == 1, "below min_precision: %s" % t)
    # Statistics of one line: its length and order classes.
    s = judge(["sum_1 binary64 lanes:9 3 0x1p+0 0x1p+0 0x1p+0 -> 0x1.8p+1 1",
               "sum_1 binary64 lanes:3 3 0x1p+0 0x1p+0 -0x1p+0 -> 0x1p+0 1",
               "sum_1 binary64 lanes:70 20 " + " ".join(["0x1p+0"] * 20) + " -> 0x1.4p+4 1"], cl)
    fe = next(d for d in entry_stats(s, "sum_1").values() if d[0] == "fold_error")
    for k in ("length 18 to 64", "order: lanes, W = 9 to 64", "order: lanes, W above 64",
              "order: lanes, W = 3", "cancellation: |sum| <= sum of magnitudes / 2"):
        expect(fe[3].get(k) == 1, "count %r: %s" % (k, fe[3]))
    expect(fe[3].get("length 3") == 2, "length 3: %s" % fe[3])
    expect(fe[3].get("order: lanes, more lanes than elements (W > n >= 1)") == 2, "W > n")
    expect(not fe[3].get("heavy cancellation: |sum| <= u * sum of magnitudes"), "cancellation")
    return "%d lines" % len(cases)


@test
def fold_scaled(ctx):
    """With the fold's constants multiplied by 1024 the reference runner passes with every largest
    ratio smaller; with eps, term and tau divided by 4 the tight cases fail."""
    data = raw5()
    for f in data["folds"]:
        for e in f["ensures"]:
            if e["kind"] == "fold_error":
                for c in ("eps", "term", "tau"):
                    e[c] = "(%s)*1024" % e[c]
        f["instances"] = {}
    big = Claims(data, "<x1024>")
    data = raw5()
    for f in data["folds"]:
        for e in f["ensures"]:
            if e["kind"] == "fold_error":
                for c in ("eps", "term", "tau"):
                    e[c] = "(%s)/4" % e[c]
        f["instances"] = {}
    small = Claims(data, "<1/4>")
    expect(not big.broken and not small.broken, "scaled claims unreadable")
    n = ctx.n(300, 150)
    for fold in ("sum_1", "sum_2", "dot_1", "dot_2"):
        lines = run5(fold_stream(ctx, fold, "binary64", n, max_length=32, strata="tight"))
        base = entry_stats(judge(lines, claims5(ctx)), fold)
        sb = judge(lines, big)
        expect(totals(sb)["failed"] == 0, "x1024 fails %s" % fold)
        rb = next(d[4] for d in entry_stats(sb, fold).values() if d[0] == "fold_error")
        r0 = next(d[4] for d in base.values() if d[0] == "fold_error")
        expect(rb is not None and r0 is not None and rb * 1000 < r0 * 2,
               "%s: largest ratio %s with x1024, %s without" % (fold, rb, r0))
        expect(totals(judge(lines, small))["failed"] > 0, "%s passes with the bound / 4" % fold)
    return "ok"


@test
def bound_kernels(ctx):
    """The bound kernels through the reference runner (milestone2.md's listing) on random counts
    and on every count of a toy format: nothing fails; the classes of m * unit(K) on both sides of
    the limit are reached; g one number too small fails only where g is zero (m = 0: elsewhere
    the listing's g exceeds its stated value by more than a gap); ok true beyond the limit fails
    holds; hand-written lines."""
    cl = claims5(ctx)
    n = ctx.n(3000, 1200)
    notes = []
    for k in BOUNDS:
        for fmtname in ("binary64", "binary32", "fp:12:-30:12"):
            s = judge(run5(kernel_stream(ctx, k, fmtname, n)), cl)
            t = totals(s)
            expect(t["failed"] == 0 and t["invalid"] == 0 and t["suspicious"] == 0,
                   "%s %s: %s" % (k, fmtname, t))
            st = entry_stats(s, k)
            first = next(d for d in st.values() if d[0] == "upper")
            unit = {"bound_sum_1": "add_1_1", "bound_sum_2": "add_2_2", "bound_dot_1": "mul_1_1",
                    "bound_dot_2": "mul_2_2"}[k]
            for c in ("ok true, m*unit(%s) = 0", "ok true, 0 < m*unit(%s) <= 1/5",
                      "ok true, 1/5 < m*unit(%s) <= 1/4", "ok false, 1/4 < m*unit(%s) <= 1/2",
                      "ok false, m*unit(%s) >= 1"):
                expect(first[3].get(c % unit), "%s %s: no %r" % (k, fmtname, c % unit))
            expect(not first[3].get("ok false, 0 < m*unit(%s) <= 1/5" % unit), "ok false early")
            close = first[6].get("excess over a positive stated value, in gaps of the output")
            expect(close is not None and close <= 8, "%s %s: g never close: %s" % (k, fmtname, close))
            notes.append("%s %s %.3g" % (k, fmtname, float(close)))
            for variant, kinds in (("bound-g-pred", {"upper"}), ("bound-ok-beyond", {"holds", "upper"})):
                sv = judge(run5(kernel_stream(ctx, k, fmtname, n), variant), cl)
                expect(set(failed_kinds(sv, k)) == kinds, "%s on %s: %s" % (
                    variant, k, failed_kinds(sv, k)))
                if variant == "bound-g-pred":
                    for (_k, _f, _t), stt in sv.keys.items():
                        for line, _why in stt.examples["failure"]:
                            expect(F.parse_limb(F.parse_format(fmtname), line.split()[2]) == 0,
                                   "g one number smaller fails at m != 0: %s" % line)
    g = G.ExhaustiveGen(cl.get("bound_dot_2"), F.parse_format("fp:8:-12:10"))
    s = judge(run5(list(g.lines(0, g.total))), cl)
    expect(totals(s)["failed"] == 0 and totals(s)["judged"] == g.total, "every count")
    hand = [
        # (line, failed, invalid, suspicious, out of scope)
        ("bound_sum_1 binary64 0x1p-1 -> 0x0p+0 1", 0, 1, 0, 0),         # count(m): 1/2
        ("bound_sum_1 binary64 -0x1p+0 -> 0x0p+0 1", 0, 1, 0, 0),
        ("bound_sum_1 fp:4:0:4 0x1p+0 -> 0x1p+0 1", 0, 0, 0, 1),          # no 1/2: format(half)
        ("bound_sum_1 binary64 0x1p+60 -> -inf 0", 0, 0, 0, 0),           # ok false: nothing
        ("bound_sum_1 binary64 0x1p+0 -> inf 1", 0, 0, 1, 0),             # ok true, g not finite
        # m = 1: unit/(1 - unit) with unit = u/(1+u) is u = 2^-53 exactly.
        ("bound_sum_1 binary64 0x1p+0 -> 0x1.fffffffffffffp-54 1", 1, 0, 0, 0),
        ("bound_sum_1 binary64 0x1p+0 -> 0x1p-53 1", 0, 0, 0, 0),
        ("bound_sum_1 binary64 0x1p+53 -> 0x1p+0 1", 1, 0, 0, 0),         # holds fails: m u > 1/2
        ("bound_dot_1 binary64 0x1p+53 -> 0x1p+0 0x1p+0 1", 1, 0, 0, 0),  # m unit(mul_1_1) ~ 1
        ("bound_dot_2 binary64 0x0p+0 -> 0x0p+0 0x0p+0 1", 0, 0, 0, 0),
        ("bound_dot_2 binary64 0x0p+0 -> 0x0p+0 -0x1p-1074 1", 1, 0, 0, 0),
    ]
    for line, nf, ni, ns, no in hand:
        t = totals(judge([line], cl))
        expect((t["failed"], t["invalid"], t["suspicious"], t["out_of_scope"]) == (nf, ni, ns, no),
               "%s: %s" % (line, t))
    return "g within %s gaps of its stated value at best" % ", ".join(notes)


@test
def stage_kernels(ctx):
    """The steps and finishes through the reference runner on random cases of their families; the
    error of form T judged against |s| + |x y|; finite_or_nan on hand-written lines and on every
    state of a tiny format, two limbs of any values included; the planted faults of the finishes
    and of dot_step_2 caught where they belong."""
    cl = claims5(ctx)
    n = ctx.n(3000, 1000)
    for k in STEPS + FINISHES:
        for fmtname in ("binary64", "binary32", "fp:5:-7:0"):
            s = judge(run5(kernel_stream(ctx, k, fmtname, n)), cl)
            t = totals(s)
            expect(t["failed"] == 0 and t["invalid"] == 0 and t["suspicious"] == 0
                   and t["judged"] > n // 2, "%s %s: %s" % (k, fmtname, t))
    for k in FINISHES:
        st = entry_stats(judge(run5(kernel_stream(ctx, k, "binary64", n)), cl), k)
        (d,) = st.values()
        for c in ("value: finite leading limb, every limb finite", "value: leading limb infinite",
                  "value: leading limb NaN") + (
                ("value: finite leading limb, a lower limb not finite",) if k.endswith("2") else ()):
            expect(d[3].get(c), "%s: no %r" % (k, c))
        for variant in ("flag-true-nan", "flag-false-finite"):
            sv = judge(run5(kernel_stream(ctx, k, "binary64", n), variant), cl)
            expect(set(failed_kinds(sv, k)) == {"finite_or_nan"}, "%s on %s" % (variant, k))
        g = G.ExhaustiveGen(cl.get(k), F.parse_format("fp:3:-3:0"))
        s = judge(run5(list(g.lines(0, g.total))), cl)
        expect(totals(s)["failed"] == 0 and totals(s)["judged"] == g.total, "every state of %s" % k)
    sv = judge(run5(kernel_stream(ctx, "dot_step_2", "binary64", n), "dot-single-product"), cl)
    expect(set(failed_kinds(sv, "dot_step_2")) == {"error"}, "dot-single-product on dot_step_2")
    hand = [
        ("fold_finish_2 binary64 0x1p+0 nan -> 0x1p+0 nan 1", 0),
        ("fold_finish_2 binary64 0x1p+0 0x1p+0 -> 0x1p+0 0x1p+0 1", 0),   # not normalized: passed on
        ("fold_finish_2 binary64 0x1p+0 0x1p+0 -> 0x1p+1 0x0p+0 1", 1),   # same value, other limbs
        ("fold_finish_2 binary64 -inf 0x1p+0 -> nan nan 0", 0),
        ("fold_finish_2 binary64 -inf 0x1p+0 -> -inf nan 0", 1),
        ("fold_finish_2 binary64 0x1p+0 inf -> 0x1p+0 inf 0", 1),
        ("fold_finish_1 binary64 -0x0p+0 -> 0x0p+0 1", 0),
        ("fold_finish_1 binary64 nan -> nan 1", 1),
        # s + x y = 2^60 + 1: error 1 is within c u^2 (|s| + |x y|) + 2 eta of form T, though far
        # beyond the bound relative to |s + x y| ... (here the same: one term) ...
        ("dot_step_2 binary64 0x1p+60 0x0p+0 0x1p+0 0x0p+0 0x1p+0 0x0p+0 -> 0x1p+60 0x1p+0", 0),
        # ... and s = 2^60, x y = -2^60 + 2^-40: the exact value 2^-40; an error of 2^-46 is within
        # c u^2 2^61 (form T) and beyond c u^2 2^-40 (what form R would allow).
        ("dot_step_2 binary64 0x1p+60 0x0p+0 -0x1p+60 0x1p-40 0x1p+0 0x0p+0 -> 0x1.04p-40 0x0p+0", 0),
        ("dot_step_2 binary64 0x1p+60 0x0p+0 -0x1p+60 0x1p-40 0x1p+0 0x0p+0 -> 0x1p-30 0x0p+0", 1),
        # fma(1, 2^-60, 1) rounds to 1.
        ("dot_step_1 binary64 0x1p+0 0x1p+0 0x1p-60 -> 0x1p+0", 0),
        ("dot_step_1 binary64 0x1p+0 0x1p+0 0x1p-60 -> 0x1.0000000000001p+0", 1),
    ]
    for line, nf in hand:
        t = totals(judge([line], cl))
        expect(t["failed"] == nf and t["invalid"] == 0, "%s: %s" % (line, t))
    return "ok"


@test
def gen_folds(ctx):
    """The fold generator: case i alone is case i of its run; the seed, the orders and the length
    matter; every case is valid; the strata and orders asked for are those written; lanes:big
    writes more lanes than elements; the enumeration's size is the brute-force count."""
    cl = claims5(ctx)
    for fold in FOLDS:
        f = cl.get_fold(fold)
        fm = F.parse_format("binary64")
        g = GF.RandomFoldGen(f, fm, "s", None, None, 40)
        run = list(g.lines(0, 60))[1:-1]
        for i in (0, 7, 33, 59):
            expect(g.case(i) == run[i], "case %d of %s alone" % (i, fold))
        expect(GF.RandomFoldGen(f, fm, "t", None, None, 40).case(5) != run[5], "seed")
        expect(GF.RandomFoldGen(f, fm, "s", None, ["seq"], 40).case(5) != run[5], "orders")
        expect(GF.RandomFoldGen(f, fm, "s", None, None, 41).case(2) != run[2], "max length")
        for ln in run:
            toks = ln.split()
            nn = int(toks[3])
            expect(nn <= 40, "length %d above 40" % nn)
        tags = {ln.split("#")[1].split(":")[0] for ln in run}
        want = set(GF.STRATA) if f.arrays[0][1] == 2 else set(GF.STRATA) - {"tail"}
        expect(tags == want, "%s strata %s" % (fold, sorted(tags)))
        g2 = GF.RandomFoldGen(f, fm, "s", ["tight"], ["lanes:big"], 9)
        for ln in list(g2.lines(0, 40))[1:-1]:
            toks = ln.split()
            expect(toks[2].startswith("lanes:") and int(toks[2][6:]) > int(toks[3]), "big: " + ln)
            expect(ln.split("#")[1].startswith("tight:"), "strata asked for: " + ln)
        s = judge(run5(fold_stream(ctx, fold, "fp:5:-7:0", ctx.n(400, 150))), cl)
        expect(totals(s)["invalid"] == 0, "invalid cases of %s" % fold)
    for fold, fmtname, L, D in (("sum_1", "fp:2:-2:1", 3, 22), ("dot_1", "fp:2:-1:0", 2, 14 * 14)):
        g = GF.ExhaustiveFoldGen(cl.get_fold(fold), F.parse_format(fmtname), L)
        want = 1 + D + sum(D ** m * m for m in range(2, L + 1))
        expect(g.total == want, "%s %s total %d, not %d" % (fold, fmtname, g.total, want))
        lines = list(g.lines(0, g.total))
        expect(len(set(lines)) == len(lines), "repeated lines")
    for bad in (["tree"], ["lanes:02"], ["lanes:x"]):
        try:
            GF.RandomFoldGen(cl.get_fold("sum_1"), F.parse_format("binary64"), "s", None, bad, 9)
        except G.GenError:
            continue
        raise AssertionError("orders %s accepted" % bad)
    return "ok"


@test
def merging_wave5(ctx):
    """Summaries of two halves of a stream of folds and bound kernels merge into the whole."""
    lines = []
    for fold in ("sum_2", "dot_1"):
        lines += run5(fold_stream(ctx, fold, "binary64", ctx.n(300, 120)))
    lines += run5(kernel_stream(ctx, "bound_dot_2", "binary64", ctx.n(600, 200)))
    cl = claims5(ctx)
    whole = judge(lines, cl, max_examples=100000)
    cut = len(lines) // 2
    while not lines[cut].startswith("# kairn-oracle gen event=begin"):
        cut += 1
    m = C.Summary(100000)
    for part in (judge(lines[:cut], cl, max_examples=100000), judge(lines[cut:], cl,
                                                                     max_examples=100000)):
        m.merge(C.Summary.from_json(json.loads(json.dumps(part.to_json())), 100000))
    ja, jb = whole.to_json(), m.to_json()
    for j in (ja, jb):
        for e in j["keys"]:
            e["stats"]["examples"] = None
            for en in e["stats"]["entries"]:
                en["max_ratio_case"] = en["b_case"] = None
                for fld in ("maxima", "minima"):
                    en[fld] = {d: v[0] for d, v in en[fld].items()}
    expect(ja == jb, "merged summary differs from the whole")
    return "%d lines" % len(lines)
