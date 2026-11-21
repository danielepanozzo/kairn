"""The oracle's own tests for stage B of Milestone 2 (architecture.md, "Maps", "Folds of maxima",
"Convolutions", "Claims of Milestone 2", "The line protocol"): the maps and their steps, the folds
of maxima and their kernels (`maximum`, `finite_or_nan` with `if` and `steps`, a fold's `upper`),
the convolutions (`coefficients`).

As for the earlier waves, each test compares the oracle with something it does not share code
with: the reference runner (written from the listings of architecture.md and milestone2.md) on
random streams and on every array of tiny formats; planted faults that must be caught in the entry
where they belong and nowhere else; hand-written lines whose verdicts are worked out by hand.  The
fixture, oracle/selftest/claims-wave7.json, holds the maps, the folds of maxima, the convolutions,
their kernels and the kernels and folds they name, frozen from the claims of 2026-11-20.
"""

import copy
import json
import os
import random
from fractions import Fraction as Q

from . import check as C
from . import fmt as F
from . import gen as G
from . import gen2 as G2
from . import genmap as GM
from . import refrun
from .claims import Claims, load_claims
from .selftest import test, expect, judge, totals, ORACLE_DIR
from .selftest7 import entry_stats

FIXTURE7 = os.path.join(ORACLE_DIR, "selftest", "claims-wave7.json")
MAPS = ("add_1", "add_1_entry", "add_2", "add_2_entry", "sub_1", "sub_1_entry", "sub_2",
        "sub_2_entry", "axpy_1", "axpy_1_entry", "axpy_2", "axpy_2_entry", "axpy_2_1",
        "axpy_2_1_entry", "scale_1", "scale_2", "mul_pow2_map_1", "mul_pow2_map_2")
MAXIMA = ("norm_upper_1", "norm_upper_2")
CONVS = ("conv_1", "conv_2")
STEPS = ("add_entry_step_1", "add_entry_step_2", "sub_1_1", "sub_entry_step_1",
         "sub_entry_step_2", "axpy_step_1", "axpy_step_2", "axpy_step_2_1", "axpy_entry_step_1",
         "axpy_entry_step_2", "axpy_entry_step_2_1", "scale_step_1", "scale_step_2",
         "mul_pow2_step_1", "mul_pow2_step_2")
NORM_KERNELS = ("norm_combine", "norm_step_1", "norm_step_2", "norm_finish_1", "norm_finish_2")
# A toy format per object, at least its min_precision (4 for axpy_2 and conv_2), with exponents
# enough for the literature's tight cases of two limbs not to matter.
TOY6 = "fp:5:-12:6"


def claims7(ctx):
    if not hasattr(ctx, "claims7"):
        ctx.claims7 = load_claims(FIXTURE7)
    return ctx.claims7


def raw6():
    with open(FIXTURE7, encoding="utf-8") as fh:
        return json.load(fh)


def run6(lines, variant="correct"):
    r = refrun.Runner(variant, bound_claims=FIXTURE7)
    out = []
    for ln in lines:
        out.extend(r.complete(ln))
    return out


def stream6(ctx, name, fmtname, count, max_length=32, seed="selftest8"):
    key = ("w6", name, fmtname, count, max_length, seed)
    s = ctx._streams.get(key)
    if s is None:
        cl = claims7(ctx)
        fmt = F.parse_format(fmtname)
        if cl.get_fold(name) is not None:
            g = GM.random_gen(cl.get_fold(name), fmt, seed, None, None, max_length)
        else:
            g = G.RandomGen(cl.get(name), fmt, seed)
        s = ctx._streams[key] = list(g.lines(0, count))
    return s


def failed_entries(summary, name):
    return {lab: d[2] for lab, d in entry_stats(summary, name).items() if d[2]}


def counts_of(summary, name, kind):
    """The counts of the entries of a kind, summed."""
    out = {}
    for _lab, d in entry_stats(summary, name).items():
        if d[0] == kind:
            for c, n in d[3].items():
                out[c] = out.get(c, 0) + n
    return out


# ---------------------------------------------------------------------------

@test
def claims_reading_wave7(ctx):
    """The fixture of stage B reads whole; malformed maps, convolutions, folds of maxima and
    kernels are set aside with a reason, without making the others unreadable."""
    cl = claims7(ctx)
    expect(not cl.broken, "the fixture has unreadable claims: %s" % cl.errors()[:3])
    for n in MAPS + MAXIMA + CONVS:
        expect(cl.get_fold(n) is not None, "%s not read" % n)
    from . import maps as MP
    expect(all(isinstance(cl.get_fold(n), MP.Map) for n in MAPS), "a map not read as a map")
    expect(all(isinstance(cl.get_fold(n), MP.Conv) for n in CONVS), "a convolution not read")
    expect(all(cl.get_fold(n).maxima for n in MAXIMA), "a fold of maxima not read as one")
    raw = raw6()
    ks = {k["name"]: k for k in raw["kernels"]}
    fs = {f["name"]: f for f in raw["folds"]}

    def kern(name, fn):
        k = copy.deepcopy(ks[name])
        fn(k)
        return k

    def fold(name, fn):
        f = copy.deepcopy(fs[name])
        fn(f)
        return f

    def ens(x, i, **kw):
        x["ensures"][i].update(kw)

    bad_kernels = [
        kern("norm_combine", lambda k: ens(k, 0, args=["m"])),
        kern("norm_combine", lambda k: ens(k, 0, args=["m", "q"])),
        kern("norm_combine", lambda k: ens(k, 0, args=["m", "ok"])),
        kern("norm_step_2", lambda k: ens(k, 0, args=["m", "abs(x[2])"])),
        kern("norm_combine", lambda k: ens(k, 0, of="okr")),
        kern("norm_combine", lambda k: ens(k, 0, extra=1)),
        kern("norm_finish_2", lambda k: ens(k, 0, steps=0)),
        kern("norm_finish_2", lambda k: ens(k, 0, steps=True)),
        kern("norm_finish_2", lambda k: ens(k, 0, **{"if": "flag"})),
        kern("norm_finish_2", lambda k: ens(k, 0, **{"if": "m"})),
        kern("norm_finish_2", lambda k: k.pop("domain")),
    ]
    bad_folds = [
        fold("axpy_2", lambda f: f.pop("map")),
        fold("axpy_2", lambda f: f.update(domain="finite")),
        fold("axpy_2", lambda f: f.update(step="no_such_kernel")),
        fold("axpy_2", lambda f: ens(f, 0, kernel="axpy_step_1")),
        fold("axpy_2", lambda f: f.update(step_args=["y", "x", "a"])),
        fold("axpy_2", lambda f: f.update(step_args=["a", "x"])),
        fold("axpy_2", lambda f: f.update(value="a*x-y")),
        fold("axpy_2", lambda f: f.update(requires=["canonical(x)", "canonical(y)"])),
        fold("axpy_2", lambda f: f.update(requires=f["requires"] + ["nonneg(a)"])),
        fold("axpy_2", lambda f: f.update(writes=[{"name": "z", "limbs": 1}])),
        fold("axpy_2", lambda f: f.update(writes=[])),
        fold("axpy_2", lambda f: f.update(outputs=[{"name": "finite", "limbs": 2}])),
        fold("axpy_2", lambda f: ens(f, 1, flag="z")),
        fold("axpy_2", lambda f: ens(f, 0, of="x")),
        fold("axpy_2", lambda f: f["ensures"].pop(1)),
        fold("axpy_2", lambda f: f.update(check="axpy_step_2")),
        fold("axpy_2", lambda f: f.update(min_precision=3)),
        fold("mul_pow2_map_1", lambda f: f.update(requires=[])),
        fold("mul_pow2_map_1", lambda f: f.update(requires=["power_of_two(x)"])),
        fold("conv_2", lambda f: f.update(coefficients="sum_2")),
        fold("conv_2", lambda f: f.update(orders=["sequential", "lanes"])),
        fold("conv_2", lambda f: ens(f, 0, fold="dot_1")),
        fold("conv_2", lambda f: f["arrays"].pop()),
        fold("conv_2", lambda f: f.update(value="x+y")),
        fold("conv_2", lambda f: f.update(scalars=[])),
        fold("norm_upper_2", lambda f: ens(f, 0, over="sum")),
        fold("norm_upper_2", lambda f: ens(f, 0, steps=-1)),
        fold("norm_upper_2", lambda f: ens(f, 0, of="flag")),
        fold("norm_upper_2", lambda f: f["ensures"].append(dict(fs["dot_2"]["ensures"][1]))),
    ]
    data = copy.deepcopy(raw)
    for i, k in enumerate(bad_kernels):
        k["name"] = "bad_kernel_%d" % i
        data["kernels"].append(k)
    for i, f in enumerate(bad_folds):
        f["name"] = "bad_fold_%d" % i
        data["folds"].append(f)
    cl2 = Claims(data, "<malformed>")
    for i in range(len(bad_kernels)):
        expect("bad_kernel_%d" % i in cl2.broken, "malformed kernel %d read: %s" % (
            i, json.dumps(bad_kernels[i]["ensures"])[:200]))
    for i in range(len(bad_folds)):
        expect("bad_fold_%d" % i in cl2.broken, "malformed fold %d read: %s" % (
            i, json.dumps(bad_folds[i])[:300]))
    for n in MAPS + MAXIMA + CONVS:
        expect(cl2.get_fold(n) is not None, "%s became unreadable: %s" % (n, cl2.broken.get(n)))
    # A map whose step cannot be read is set aside with it; a convolution read before the fold of
    # its coefficients in the list is read all the same.
    data = copy.deepcopy(raw)
    for k in data["kernels"]:
        if k["name"] == "axpy_step_2":
            k["ensures"][1]["form"] = "Z"
    data["folds"].sort(key=lambda f: f["name"])
    cl3 = Claims(data, "<axpy_step_2 broken>")
    expect("axpy_2" in cl3.broken and cl3.get_fold("axpy_2_entry") is not None
           and cl3.get_fold("conv_2") is not None, "a broken step: %s" % sorted(cl3.broken))
    return "%d malformed kernels and %d malformed folds set aside" % (len(bad_kernels),
                                                                      len(bad_folds))


@test
def gen_shapes(ctx):
    """Every family of the kernels' generator writes valid cases for every stratum of every
    kernel of the fixtures, and of each with a two-limb input made one limb (its normalized()
    dropped): a family that assumes a shape (the scale family's two-limb operand beside the power
    of two, which crashed the search on mul_pow2_step_1) refuses the kernel with a GenError or
    serves it, and never fails otherwise."""
    from .selftest import FIXTURE, FIXTURE2
    fixtures = [FIXTURE, FIXTURE2] + [os.path.join(ORACLE_DIR, "selftest", "claims-wave%d.json" % w)
                                      for w in (3, 4, 5, 6)]
    variants = 0
    served = 0
    fmt = F.parse_format("binary64")
    for path in fixtures:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
        for k in raw["kernels"]:
            if k.get("domain") == "extended":
                continue
            kinds = [copy.deepcopy(k)]
            for i, inp in enumerate(k["inputs"]):
                if inp.get("limbs") == 2:
                    v = copy.deepcopy(k)
                    v["name"] = k["name"] + "_one_%d" % i
                    v["inputs"][i]["limbs"] = 1
                    v["requires"] = [r for r in v["requires"]
                                     if r.replace(" ", "") != "normalized(%s)" % inp["name"]]
                    v["instances"] = {}
                    kinds.append(v)
            for v in kinds:
                cl = Claims({"schema": 1, "kernels": [v] + [x for x in raw["kernels"]
                                                             if x["name"] != v["name"]]},
                            "<shape>")
                kern = cl.get(v["name"])
                if kern is None:
                    continue
                variants += 1
                try:
                    g = G.RandomGen(kern, fmt, "shapes")
                except G.GenError:
                    continue
                for s in g.strata:
                    gs = G.RandomGen(kern, fmt, "shapes", [s])
                    try:
                        for i in range(4):
                            gs.case(i)
                    except G.GenError:
                        continue
                served += 1
    expect(variants > 100, "only %d kernels and variants" % variants)
    # The case that crashed: mul_pow2_step_1, a one-limb x beside a power of two.
    k = claims7(ctx).get("mul_pow2_step_1")
    g = G.RandomGen(k, fmt, "shapes")
    expect(isinstance(g.shape, G2.Shape2) and g.shape.family == "scale",
           "mul_pow2_step_1 is not of the scale family")
    for i in range(40):
        g.case(i)
    return "%d kernels and variants, %d served by a family" % (variants, served)


@test
def stage_b_kernels(ctx):
    """The steps of the maps and the kernels of the folds of maxima through the reference runner
    on random cases of three formats: nothing fails, nothing is invalid or suspicious; the axpy
    steps of one limb come to within 1e-6 of their bound of form T (the tight stratum), those of
    two to at least 4/7 of it in binary64 (the literature's case of mul_2_2); every class of the
    maximum and of the finishes is met."""
    cl = claims7(ctx)
    n = ctx.n(1500, 500)
    best = {}
    for k in STEPS + NORM_KERNELS:
        for fmtname in ("binary64", "binary32", TOY6):
            if F.parse_format(fmtname).p < cl.get(k).min_precision:
                continue
            s = judge(run6(stream6(ctx, k, fmtname, n)), cl)
            t = totals(s)
            expect(t["failed"] == 0 and t["invalid"] == 0 and t["suspicious"] == 0,
                   "%s %s: %s %s" % (k, fmtname, t, failed_entries(s, k)))
            for lab, d in entry_stats(s, k).items():
                if d[0] == "error" and d[4] is not None:
                    best[(k, fmtname)] = d[4]
                if d[0] == "maximum":
                    for c in ("first argument larger", "second argument larger",
                              "arguments equal"):
                        expect(d[3].get(c), "%s %s: no case %r" % (k, fmtname, c))
                if d[0] == "finite_or_nan":
                    need = ["mask true", "mask false", "value finite, stepped up finite",
                            "value: NaN", "value: infinite"]
                    if k == "norm_finish_2":
                        need.append("value finite, stepped up +inf")
                    for c in need:
                        expect(d[3].get(c), "%s %s: no case %r" % (k, fmtname, c))
    # mul_pow2_step_1: an odd multiple of eta/2 rounds by eta/2, its whole bound (halfscaled).
    expect(best[("mul_pow2_step_1", "binary64")] == 1, "mul_pow2_step_1 came to %s of its bound"
           % float(best[("mul_pow2_step_1", "binary64")]))
    for k in ("axpy_step_1", "axpy_entry_step_1"):
        for f in ("binary64", "binary32"):
            expect(best[(k, f)] > 1 - 1e-6, "%s %s came to %s of its bound" % (k, f,
                                                                              float(best[(k, f)])))
    for k in ("axpy_step_2", "axpy_entry_step_2"):
        expect(best[(k, "binary64")] > 0.57, "%s binary64 came to %s of its bound" % (
            k, float(best[(k, "binary64")])))
    return "axpy_step_1 %.9f, axpy_step_2 %.4f of their bounds in binary64" % (
        float(best[("axpy_step_1", "binary64")]), float(best[("axpy_step_2", "binary64")]))


def _need(s, name, kind, names):
    c = counts_of(s, name, kind)
    for x in names:
        expect(c.get(x), "%s: no case %r of %s (%s)" % (name, x, kind, sorted(c)))


@test
def maps_reference(ctx):
    """The reference runner on random arrays of every map, fold of maxima and convolution, in
    binary64, binary32 and a toy format: nothing fails, nothing is invalid or suspicious; every
    class the guards ask for is met (elements that overflow and that have a non-finite operand,
    both flags, every length and order; the largest at each place, the top of the bound beyond
    Omega; coefficients of each kind, lengths 0 and 1 on each side, unequal lengths)."""
    cl = claims7(ctx)
    n = ctx.n(400, 170)
    for name in MAPS + MAXIMA + CONVS:
        for fmtname in ("binary64", "binary32", TOY6):
            s = judge(run6(stream6(ctx, name, fmtname, n)), cl)
            t = totals(s)
            expect(t["failed"] == 0 and t["invalid"] == 0 and t["suspicious"] == 0 and
                   t["judged"] == n, "%s %s: %s %s" % (name, fmtname, t, failed_entries(s, name)))
            if name in MAPS and fmtname == "binary64":
                # The tight stratum brings a one-limb step to its bound (a tie at 1 + u, a
                # product just below a midpoint, an odd multiple of eta/2).
                r = max((d[4] for d in entry_stats(s, name).values()
                         if d[0] == "error" and d[4] is not None), default=0)
                lim = 0.99 if cl.get_fold(name).wlimbs == 1 else 0.3
                expect(r >= lim, "%s binary64: its step came to %s of its bound" % (name, float(r)))
            if name in MAPS:
                _need(s, name, "entries", ("element: finite operands, finite result",
                                           "element: finite operands, not finite (an overflow)",
                                           "element: a non-finite operand", "length 0",
                                           "length 17", "order: lanes, W = 4"))
                _need(s, name, "finite_or_nan", ("flag true", "flag false: a non-finite operand",
                                                 "flag false: finite operands, an overflow"))
            elif name in MAXIMA:
                need = ["the largest at the first element", "the largest at the last element",
                        "the largest at another element", "the largest attained more than once",
                        "no element: V = 0", "result at RU(V)"]
                if name == "norm_upper_2":
                    need += ["result 1 step above RU(V)", "V not a number of the format"]
                _need(s, name, "upper", need)
                _need(s, name, "finite_or_nan", ("flag true", "flag false: a non-finite element")
                      + (("flag false: finite elements, the bound's top beyond Omega",)
                         if name == "norm_upper_2" else ()))
            else:
                _need(s, name, "coefficients", ("coefficient: finite terms, finite result",
                                                "coefficient: a non-finite term", "n_x = 0",
                                                "n_y = 0", "n_x = 1", "n_y = 1", "n_x != n_y"))
                _need(s, name, "fold_error", ("length 1", "length 2",
                                              "heavy cancellation: |sum| <= u * sum of magnitudes"))
    return "%d objects in 3 formats" % len(MAPS + MAXIMA + CONVS)


# The planted faults of stage B: the objects they touch, the entries that must fail there (kinds),
# the entries that may fail with them.
PLANTED6 = {
    "map-drop-last": (MAPS, {"entries"}, set()),
    # The steps of two limbs give the canonical NaN by themselves where they overflow, but
    # mul_pow2_step_2: no second pass changes nothing there.
    "map-no-second-pass": (("add_1", "add_1_entry", "sub_1", "sub_1_entry", "axpy_1",
                            "axpy_1_entry", "scale_1", "mul_pow2_map_1", "mul_pow2_map_2"),
                           {"finite_or_nan"}, set()),
    "map-flag-true": (MAPS, {"finite_or_nan"}, set()),
    "map-lanes-swap": (MAPS, {"entries"}, {"finite_or_nan"}),
    "max-step-small": (MAXIMA, {"upper"}, set()),
    "max-nan-lost": (MAXIMA, {"finite_or_nan"}, set()),
    "max-two-steps": (MAXIMA, {"upper"}, {"finite_or_nan"}),
    "conv-drop-last-term": (CONVS, {"coefficients"}, {"finite_or_nan"}),
    "conv-neighbor-term": (CONVS, {"coefficients"}, {"finite_or_nan"}),
    "conv-flag-true": (CONVS, {"finite_or_nan"}, set()),
}


def _kinds_failed(summary, name):
    out = set()
    for _lab, d in entry_stats(summary, name).items():
        if d[2]:
            out.add(d[0] if d[0] not in ("error", "rounded", "normalized", "fold_error") else
                    "entries" if name in MAPS else "coefficients")
    return out


@test
def maps_planted(ctx):
    """Each planted fault of stage B fails in the entry where it belongs (a dropped element or
    elements swapped between lanes: entries; no second pass or a flag that lies: finite_or_nan; a
    maximum one step too small or too large: upper; a NaN lost: finite_or_nan; a coefficient that
    drops a term or takes its neighbour's: coefficients) and in no object it does not touch."""
    cl = claims7(ctx)
    n = ctx.n(300, 120)
    notes = []
    names = MAPS + MAXIMA + CONVS if not ctx.quick else (
        "add_1", "add_2", "axpy_1", "axpy_2_1", "scale_2", "mul_pow2_map_1", "sub_1_entry") + \
        MAXIMA + CONVS
    for variant, (objs, kinds, also) in PLANTED6.items():
        for name in names:
            s = judge(run6(stream6(ctx, name, "binary64", n), variant), cl)
            fk = _kinds_failed(s, name)
            if name in objs:
                expect(kinds <= fk <= kinds | also, "%s on %s fails %s, not %s" % (
                    variant, name, sorted(fk) or "nothing", sorted(kinds)))
            else:
                expect(not fk, "%s fails %s, which it does not touch: %s" % (variant, name, fk))
        notes.append(variant)
    return ", ".join(notes)


def _enum6(ctx, name, fmtname, L, variant="correct"):
    g = GM.exhaustive_gen(claims7(ctx).get_fold(name), F.parse_format(fmtname), L)
    return judge(run6(list(g.lines(0, g.total)), variant), claims7(ctx)), g.total


@test
def maps_exhaustive(ctx):
    """Every array (and scalar) of tiny formats up to a small length, in every order that
    differs, through the reference runner: nothing fails, every line is judged and the coverage is
    complete; a planted fault is caught there too."""
    cases = [("add_1", "fp:2:-1:0", 1), ("axpy_1", "fp:2:-1:0", 1), ("mul_pow2_map_1", "fp:3:-3:0", 1),
             ("norm_upper_1", "fp:2:-1:0", 2), ("norm_upper_2", "fp:2:-2:1", 1),
             ("conv_1", "fp:2:-1:0", 1), ("scale_2", "fp:2:-1:0", 1)]
    if not ctx.quick:
        cases += [("add_1", "fp:2:-1:0", 2), ("sub_2", "fp:3:-2:-1", 1), ("axpy_2_1", "fp:3:-2:-1", 1),
                  ("norm_upper_1", "fp:2:-1:0", 3), ("conv_1", "fp:2:-1:0", 2),
                  ("conv_2", "fp:4:-3:-2", 1)]
    n = 0
    for name, fmtname, L in cases:
        s, total = _enum6(ctx, name, fmtname, L)
        t = totals(s)
        n += total
        expect(t["failed"] == 0 and t["invalid"] == 0 and t["suspicious"] == 0 and
               t["judged"] == total, "%s %s up to %d: %s %s" % (name, fmtname, L, t,
                                                                failed_entries(s, name)))
        cov = s.coverage.describe()
        expect(cov and "COMPLETE" in cov[0], "coverage: %s" % cov)
    for variant, name, fmtname, L, kind in (("map-flag-true", "add_1", "fp:2:-1:0", 1,
                                             "finite_or_nan"),
                                            ("max-two-steps", "norm_upper_2", "fp:2:-2:1", 1,
                                             "upper"),
                                            ("conv-drop-last-term", "conv_1", "fp:2:-1:0", 1,
                                             "coefficients")):
        s, _ = _enum6(ctx, name, fmtname, L, variant)
        expect(kind in _kinds_failed(s, name), "%s on every array: %s" % (
            variant, failed_entries(s, name)))
    # The size of an enumeration, by brute force: scalars x elements^n x orders, summed.
    g = GM.exhaustive_gen(claims7(ctx).get_fold("axpy_1"), F.parse_format("fp:2:-1:0"), 2)
    d = len(F.all_values(F.parse_format("fp:2:-1:0"))) + 3
    expect(g.total == d * (1 + d * d + 2 * d ** 4), "axpy_1's enumeration has %d cases" % g.total)
    g = GM.exhaustive_gen(claims7(ctx).get_fold("conv_1"), F.parse_format("fp:2:-1:0"), 2)
    expect(g.total == (1 + d + d * d) ** 2, "conv_1's enumeration has %d cases" % g.total)
    return "%d arrays" % n


def _h(v):
    return float(v).hex() if v != 0 else "0x0p+0"


OM = "0x1.fffffffffffffp+1023"
JUDGE6 = [
    # Maps (MAP FORMAT ORDER N SCALAR... LIMB... -> Z... MASK).
    ("add_1 binary64 seq 2 0x1p+0 0x1p+1 0x1p+0 0x1p+0 -> 0x1p+1 0x1.8p+1 1", "pass", None),
    ("add_1 binary64 seq 2 0x1p+0 0x1p+1 0x1p+0 0x1p+0 -> 0x1p+1 0x1p+1 1", "fail", "entries"),
    ("add_1 binary64 lanes:2 3 0x1p+0 0x1p+1 0x1p+2 0x1p+0 0x1p+0 0x1p+0 -> 0x1p+1 0x1.8p+1 "
     "0x1.4p+2 1", "pass", None),
    ("add_1 binary64 seq 1 inf 0x1p+0 -> nan 1", "fail", "finite_or_nan"),
    ("add_1 binary64 seq 2 inf 0x1p+0 0x1p+0 0x1p+0 -> inf 0x1p+1 0", "fail", "finite_or_nan"),
    ("add_1 binary64 seq 2 inf 0x1p+0 0x1p+0 0x1p+0 -> nan 0x1p+1 0", "pass", None),
    ("add_1 binary64 seq 2 inf 0x1p+0 0x1p+0 0x1p+0 -> nan 0x1p+1 1", "fail", "finite_or_nan"),
    ("add_1 binary64 seq 1 %s %s -> nan 0" % (OM, OM), "pass", None),
    ("add_1 binary64 seq 1 %s %s -> nan 1" % (OM, OM), "fail", "finite_or_nan"),
    ("add_1 binary64 seq 2 0x1p+0 0x1p+0 0x1p+0 0x1p+0 -> 0x1p+1 0x1p+1 0", "fail",
     "finite_or_nan"),
    ("add_1 binary64 seq 1 inf -inf -> 0x0p+0 1", "fail", "entries"),
    # Omega + half its unit rounds to +inf: a finite element is not the step's rounding.
    ("add_1 binary64 seq 1 %s 0x1p+970 -> %s 1" % (OM, OM), "fail", "entries"),
    ("add_1 binary64 seq 0 -> 1", "pass", None),
    ("add_1 binary64 seq 0 -> 0", "fail", "finite_or_nan"),
    ("add_1 binary64 seq 1 0x1p+0 -> 0x1p+0 1", "malformed", None),
    ("add_1 binary64 seq 1 0x1p+0 0x1p+0 -> 0x1p+1", "malformed", None),
    ("add_1 binary64 tree 1 0x1p+0 0x1p+0 -> 0x1p+1 1", "malformed", None),
    ("add_1 binary64 seq 1 0x1p+0 0x1p+0 -> 0x1p+1 2", "malformed", None),
    ("add_2 binary64 seq 1 0x1p+0 0x1p+0 0x0p+0 0x0p+0 -> 0x1p+1 0x0p+0 1", "invalid", None),
    ("add_2 binary64 seq 1 0x1p+0 0x1p-60 0x1p+0 0x0p+0 -> 0x1p+1 0x1p-60 1", "pass", None),
    ("add_2 binary64 seq 1 0x1p+0 0x1p-60 0x1p+0 0x0p+0 -> 0x1p+1 0x0p+0 1", "fail", "entries"),
    ("add_2 binary64 seq 1 0x1p+0 0x1p-60 0x1p+0 0x0p+0 -> 0x1p+1 inf 1", "fail", "entries"),
    ("sub_1 binary64 seq 1 0x1p+0 0x1p+0 -> -0x0p+0 1", "pass", None),
    ("scale_1 binary64 seq 0 nan -> 1", "pass", None),
    ("scale_1 binary64 seq 0 nan -> 0", "fail", "finite_or_nan"),
    ("scale_1 binary64 seq 2 0x1p+1 0x1p+0 0x1.8p+0 -> 0x1p+1 0x1.8p+1 1", "pass", None),
    ("scale_1 binary64 seq 1 0x0p+0 inf -> nan 0", "pass", None),
    ("mul_pow2_map_1 binary64 seq 1 0x1.8p+0 0x1p+0 -> 0x1.8p+0 1", "invalid", None),
    ("mul_pow2_map_1 binary64 seq 1 inf 0x1p+0 -> inf 0", "invalid", None),
    ("mul_pow2_map_1 binary64 seq 1 0x1p-1 0x1p-1074 -> 0x0p+0 1", "pass", None),
    ("mul_pow2_map_1 binary64 seq 1 0x1p-1 0x1p-1074 -> 0x1p-1074 1", "fail", "entries"),
    ("axpy_1 binary64 seq 1 0x1.0000000000001p+0 0x1.fffffffffffffp-1 0x1p-53 -> 0x1p+0 1",
     "pass", None),
    ("axpy_1 binary64 seq 1 0x1.0000000000001p+0 0x1.fffffffffffffp-1 0x1p-53 -> "
     "0x1.0000000000001p+0 1", "pass", None),
    # 1 + 6u is 4u from the exact 1 + 2u - 2u^2, above the bound of about 2u.
    ("axpy_1 binary64 seq 1 0x1.0000000000001p+0 0x1.fffffffffffffp-1 0x1p-53 -> "
     "0x1.0000000000003p+0 1", "fail", "entries"),
    # Folds of maxima.
    ("norm_upper_1 binary64 seq 3 0x1p+0 -0x1p+1 0x1p-1 -> 0x1p+1 1", "pass", None),
    ("norm_upper_1 binary64 lanes:2 3 0x1p+0 -0x1p+1 0x1p-1 -> 0x1p+1 1", "pass", None),
    ("norm_upper_1 binary64 seq 3 0x1p+0 -0x1p+1 0x1p-1 -> 0x1.fffffffffffffp+0 1", "fail",
     "upper", "below the largest value of an element"),
    ("norm_upper_1 binary64 seq 3 0x1p+0 -0x1p+1 0x1p-1 -> 0x1.0000000000001p+1 1", "fail",
     "upper"),
    ("norm_upper_1 binary64 seq 2 0x1p+0 nan -> 0x1p+0 1", "fail", "finite_or_nan"),
    ("norm_upper_1 binary64 seq 2 0x1p+0 nan -> nan 0", "pass", None),
    ("norm_upper_1 binary64 seq 2 0x1p+0 -inf -> nan 0", "pass", None),
    ("norm_upper_1 binary64 seq 2 0x1p+0 -inf -> inf 0", "fail", "finite_or_nan"),
    ("norm_upper_1 binary64 seq 0 -> 0x0p+0 1", "pass", None),
    ("norm_upper_1 binary64 seq 0 -> 0x1p-1074 1", "fail", "upper"),
    ("norm_upper_1 binary64 seq 1 %s -> %s 1" % (OM, OM), "pass", None),
    ("norm_upper_1 binary64 seq 1 %s -> nan 0" % OM, "fail", "finite_or_nan"),
    ("norm_upper_2 binary64 seq 1 0x1p+0 0x1p-60 -> 0x1.0000000000001p+0 1", "pass", None),
    ("norm_upper_2 binary64 seq 1 0x1p+0 0x1p-60 -> 0x1p+0 1", "fail", "upper"),
    ("norm_upper_2 binary64 seq 1 0x1p+0 -0x1p-60 -> 0x1.0000000000001p+0 1", "pass", None),
    ("norm_upper_2 binary64 seq 1 0x1p+0 -0x1p-60 -> 0x1p+0 1", "pass", None),
    ("norm_upper_2 binary64 seq 1 0x1p+0 -0x1p-60 -> 0x1.0000000000002p+0 1", "fail", "upper"),
    ("norm_upper_2 binary64 seq 1 %s -0x1p+960 -> nan 0" % OM, "pass", None),
    ("norm_upper_2 binary64 seq 1 %s -0x1p+960 -> %s 1" % (OM, OM), "pass", None),
    ("norm_upper_2 binary64 seq 1 %s 0x1p+960 -> %s 1" % (OM, OM), "fail", "upper"),
    ("norm_upper_2 binary64 seq 1 %s 0x1p+960 -> nan 0" % OM, "pass", None),
    ("norm_upper_2 binary64 seq 1 0x1p+0 0x1p+0 -> 0x1.0000000000001p+0 1", "invalid", None),
    # Convolutions (CONV FORMAT seq N_X N_Y LIMB... -> Z... MASK).
    ("conv_1 binary64 seq 3 2 0x1p+0 0x1p+1 0x1p+2 0x1p+0 0x1p-1 -> 0x1p+0 0x1.4p+1 0x1.4p+2 "
     "0x1p+1 1", "pass", None),
    ("conv_1 binary64 seq 3 2 0x1p+0 0x1p+1 0x1p+2 0x1p+0 0x1p-1 -> 0x1p+0 0x1p+1 0x1.4p+2 "
     "0x1p+1 1", "fail", "coefficients"),
    ("conv_1 binary64 seq 2 2 0x1p+0 0x1p+0 0x1p+0 -0x1p+0 -> 0x1p+0 0x0p+0 -0x1p+0 1", "pass",
     None),
    ("conv_2 binary64 seq 0 1 0x1p+0 0x0p+0 -> 1", "pass", None),
    ("conv_2 binary64 seq 0 1 0x1p+0 0x0p+0 -> 0x0p+0 0x0p+0 1", "malformed", None),
    ("conv_1 binary64 seq 1 1 inf 0x0p+0 -> nan 0", "pass", None),
    ("conv_1 binary64 seq 1 1 inf 0x0p+0 -> nan 1", "fail", "finite_or_nan"),
    ("conv_1 binary64 seq 1 1 inf 0x0p+0 -> 0x0p+0 1", "fail", "coefficients"),
    ("conv_1 binary64 seq 1 1 inf 0x1p+0 -> inf 0", "fail", "finite_or_nan",
     "not the canonical NaN"),
    ("conv_2 binary64 seq 1 1 0x1p+0 0x1p+0 0x1p+0 0x0p+0 -> 0x1p+0 0x1p+0 1", "invalid", None),
    ("conv_2 binary64 seq 1 1 0x1p+0 0x0p+0 0x1p+0 0x1p-60 -> 0x1p+0 0x1p-60 1", "pass", None),
    ("conv_1 binary64 seq 2 1 0x1p+0 0x1p+0 -> 0x1p+0 1", "malformed", None),
    ("conv_1 binary64 lanes:2 1 1 0x1p+0 0x1p+0 -> 0x1p+0 1", "malformed", None),
    ("conv_1 binary64 seq 2 1 0x1p+0 inf 0x1p+0 -> 0x1p+0 nan 0", "pass", None),
    # A coefficient of finite terms far below Omega that is not finite: suspicious (a map's or a
    # fold's reading of a false flag from finite operands), which the cross-checks fail.
    ("conv_1 binary64 seq 2 1 0x1p+0 inf 0x1p+0 -> nan nan 0", "suspicious", None),
    ("add_1 binary64 seq 2 inf 0x1p+0 0x1p+0 0x1p+0 -> nan nan 0", "suspicious", None),
    # Kernels of the folds of maxima, and steps.
    ("norm_combine binary64 0x1p+0 1 0x1p+1 1 -> 0x1p+1 1", "pass", None),
    ("norm_combine binary64 0x1p+0 1 0x1p+1 1 -> 0x1p+0 1", "fail", "maximum"),
    ("norm_combine binary64 -0x1p+3 0 -0x1p+1 1 -> -0x1p+1 0", "pass", None),
    ("norm_step_2 binary64 0x1p+0 1 -0x1p+1 0x0p+0 -> 0x1p+1 1", "pass", None),
    ("norm_step_2 binary64 0x1p+1 1 -0x1p+1 -0x1p-60 -> 0x1p+1 1", "pass", None),
    ("norm_finish_2 binary64 0x1p+0 1 -> 0x1.0000000000001p+0 1", "pass", None),
    ("norm_finish_2 binary64 0x1p+0 1 -> 0x1p+0 1", "fail", "finite_or_nan"),
    ("norm_finish_2 binary64 0x1p+0 0 -> nan 0", "pass", None),
    ("norm_finish_2 binary64 0x1p+0 0 -> 0x1.0000000000001p+0 1", "fail", "finite_or_nan"),
    ("norm_finish_2 binary64 %s 1 -> nan 0" % OM, "pass", None),
    ("norm_finish_2 binary64 %s 1 -> inf 1" % OM, "fail", "finite_or_nan"),
    ("norm_finish_2 binary64 -0x1p-1074 1 -> 0x0p+0 1", "pass", None),
    # nextUp(-inf) is -Omega, finite: the claim says flag true and -Omega (a state the fold never
    # has: its maximum is a magnitude).
    ("norm_finish_2 binary64 -inf 1 -> -%s 1" % OM, "pass", None),
    ("norm_finish_2 binary64 -inf 1 -> nan 0", "fail", "finite_or_nan"),
    ("norm_finish_1 binary64 -inf 1 -> nan 0", "pass", None),
    ("norm_finish_2 binary64 nan 1 -> nan 0", "pass", None),
    ("norm_finish_1 binary64 0x1p+0 1 -> 0x1p+0 1", "pass", None),
    ("norm_finish_1 binary64 0x1p+0 0 -> 0x1p+0 1", "fail", "finite_or_nan"),
    ("norm_finish_1 binary64 %s 1 -> %s 1" % (OM, OM), "pass", None),
    ("mul_pow2_step_1 binary64 0x1p-1074 0x1p-1 -> 0x0p+0", "pass", None),
    ("mul_pow2_step_1 binary64 0x1p-1074 0x1p-1 -> 0x1p-1074", "fail", "rounded"),
    ("axpy_step_1 binary64 0x1.0000000000001p+0 0x1.fffffffffffffp-1 0x1p-53 -> 0x1p+0", "pass",
     None),
]


@test
def maps_judge(ctx):
    """Hand-written lines of stage B, each verdict worked out by hand: right answers in each
    spelling, a written element or a coefficient off, a flag that lies, a missing second pass, a
    finite element from a non-finite operand or beyond Omega, the empty array, malformed lines and
    invalid requests; the maxima at, one step above and two steps above RU(V), a lost NaN, the top
    of the bound beyond Omega; the kernels' maximum and finishes."""
    cl = claims7(ctx)
    n = 0
    for case in JUDGE6:
        line, want, kind = case[:3]
        name = line.split(" ", 1)[0]
        s = judge([line], cl)
        t = totals(s)
        if len(case) > 3:
            # The reason of the failure, where another check would fail the line too.
            reasons = " ".join(r for st in s.keys.values() for r in st.reasons)
            expect(case[3] in reasons, "%s: failed for %s, not %r" % (line, reasons, case[3]))
        if want == "pass":
            ok = t["passed"] == 1 and t["failed"] == 0
        elif want == "invalid":
            ok = t["invalid"] == 1
        elif want == "suspicious":
            ok = t["suspicious"] == 1 and t["failed"] == 0
        elif want == "malformed":
            ok = t["failed"] == 1 and not any(d[2] for d in entry_stats(s, name).values())
        else:
            ok = t["failed"] == 1 and kind in {d[0] if d[0] not in ("error", "rounded",
                                                                     "normalized", "fold_error")
                                               or name in NORM_KERNELS + STEPS else
                                               "entries" if name in MAPS else "coefficients"
                                               for d in entry_stats(s, name).values() if d[2]}
        expect(ok, "%s: %s, expected %s%s (%s; failing entries %s)" % (
            line, t, want, " in " + kind if kind else "", s.keys and
            list(s.keys.values())[0].reasons, failed_entries(s, name)))
        n += 1
    # The counts of a maximum, by hand: which argument is the larger.
    for line, name in (("norm_combine binary64 0x1p+0 1 0x1p+1 1 -> 0x1p+1 1", "second argument larger"),
                       ("norm_combine binary64 0x1p+2 1 0x1p+1 1 -> 0x1p+2 1", "first argument larger"),
                       ("norm_combine binary64 0x1p+1 1 -0x1p+1 1 -> 0x1p+1 1", "first argument larger"),
                       ("norm_step_1 binary64 0x1p+1 1 -0x1p+1 -> 0x1p+1 1", "arguments equal")):
        c = counts_of(judge([line], cl), line.split(" ", 1)[0], "maximum")
        expect(c.get(name) == 1, "%s: counted %s, not %r" % (line, c, name))
    return "%d lines" % n


@test
def gen_maps(ctx):
    """The generators of maps, convolutions and folds of maxima are counter-based (case i alone
    is case i of its run; a seed, the orders and the largest length matter), write no length above
    the largest, every stratum of the header, and only valid cases; lanes:big is above the
    length."""
    cl = claims7(ctx)
    fmt = F.parse_format("binary64")
    for name in ("axpy_2_1", "norm_upper_2", "conv_2", "mul_pow2_map_1"):
        obj = cl.get_fold(name)
        g = GM.random_gen(obj, fmt, "s", None, None, 40)
        run = list(g.lines(0, 60))[1:-1]
        for i in (0, 7, 33, 59):
            one = list(GM.random_gen(obj, fmt, "s", None, None, 40).lines(i, 1))[1]
            expect(one == run[i], "%s: case %d alone differs" % (name, i))
        expect(run != list(GM.random_gen(obj, fmt, "t", None, None, 40).lines(0, 60))[1:-1],
               "%s: the seed does not matter" % name)
        expect(run != list(GM.random_gen(obj, fmt, "s", None, None, 39).lines(0, 60))[1:-1],
               "%s: the largest length does not matter" % name)
        tags = {ln.rsplit("#", 1)[1].split(":")[0] for ln in run}
        expect(tags == set(g.strata), "%s: strata %s, header %s" % (name, sorted(tags), g.strata))
        for ln in run:
            toks = ln.split(" ")
            lens = [int(toks[3]), int(toks[4])] if name == "conv_2" else [int(toks[3])]
            expect(max(lens) <= 40, "%s: a length above 40" % name)
            if toks[2].startswith("lanes:") and int(toks[2][6:]) > lens[0] >= 1:
                pass
        s = judge(run6(list(g.lines(0, 60))), cl)
        expect(totals(s)["invalid"] == 0, "%s: invalid cases" % name)
        try:
            GM.random_gen(obj, fmt, "s", ["nosuch"], None, 40)
            expect(False, "%s: an unknown stratum accepted" % name)
        except G.GenError:
            pass
    try:
        GM.random_gen(cl.get_fold("conv_1"), fmt, "s", None, ["lanes:2"], 10)
        expect(False, "a convolution accepted the lane order")
    except G.GenError:
        pass
    return "4 generators"


@test
def merging_wave7(ctx):
    """The merge of the summaries of two halves of streams of stage B is the summary of the
    whole."""
    cl = claims7(ctx)
    lines = []
    for name in ("axpy_2", "norm_upper_2", "conv_1", "norm_finish_2"):
        lines += run6(stream6(ctx, name, "binary64", ctx.n(200, 80)))
    whole = judge(lines, cl)
    # Halves at a stream boundary: each stream is whole in one half.
    cut = len(run6(stream6(ctx, "axpy_2", "binary64", ctx.n(200, 80)))) + len(
        run6(stream6(ctx, "norm_upper_2", "binary64", ctx.n(200, 80))))
    a, b = judge(lines[:cut], cl), judge(lines[cut:], cl)
    m = C.Summary()
    m.merge(a)
    m.merge(b)
    ja, jb = json.dumps(whole.to_json(), sort_keys=True), json.dumps(m.to_json(), sort_keys=True)
    expect(ja == jb, "the merged summary differs from the whole")
    return "%d lines" % len(lines)



def _old_json(es):
    """An entry's summary as it was before the profile kept only its records: every distance."""
    j = es.to_json()
    j["profile"] = {str(d): [[str(r[0]), str(r[1])], c] for d, (r, c) in sorted(es.profile.items())}
    del j["profile_distances"]
    return j


@test
def summary_bounds(ctx):
    """What a summary keeps does not grow with the lines judged.  The step's entries of a map keep
    the line of the element that attains a statistic (maps.ElementLine), a line of the step that
    runs again with the same verdict, never the map's line; the profile keeps its records
    (check.EntryStats.profile_records), from which (a) at every distance, with its case, is what
    the whole profile gave, also after merges, as the brute-force driver and check --merge do
    them."""
    cl = claims7(ctx)
    kept = []
    for name in ("axpy_2_1", "sub_2_entry", "scale_1"):
        s = judge(run6(stream6(ctx, name, "binary64", ctx.n(60, 25), max_length=1024)), cl)
        j = s.to_json()
        step = cl.get_fold(name).step
        size = len(json.dumps(j))
        expect(size < 1 << 20, "%s: a summary of %d bytes" % (name, size))
        for key in j["keys"]:
            for e in key["stats"]["entries"][2:]:
                cases = [e["max_ratio_case"], e["b_case"]]
                cases += [c for _r, c in e["profile"].values()]
                cases += [c for _r, c in list(e["maxima"].values()) + list(e["minima"].values())]
                for c in cases:
                    if c is None:
                        continue
                    t = c.split(" ")
                    expect(t[0] == step and ":element:" in c and len(t) < 16,
                           "%s: the step's entries keep %r" % (name, c[:200]))
                    kept.append(c)
                recs = sorted((int(d), v[0]) for d, v in e["profile"].items())
                for i, (d, r) in enumerate(recs):
                    expect(all(Q(int(r[0]), int(r[1])) >= Q(int(x[0]), int(x[1]))
                               for _d, x in recs[i + 1:]),
                           "%s: distance %d of the profile is not a record" % (name, d))
    expect(kept, "no case kept")
    # The element lines are lines of the steps: judged again, they pass, each judged once.
    t = totals(judge(sorted(set(kept)), cl))
    expect(t["judged"] == len(set(kept)) and t["failed"] == t["invalid"] == 0,
           "the kept element lines judged again: %s" % t)
    # The records against the whole profile, on random profiles with many equal ratios: (a) for
    # every F, value and case, merged in order from summaries read back, is the same with the
    # records as with every distance, and so is the merged summary.
    rng = random.Random("summary_bounds")
    trials = ctx.n(3000, 800)
    for trial in range(trials):
        parts = []
        for i in range(rng.randrange(1, 5)):
            e = C.EntryStats("e", "error")
            for _ in range(rng.randrange(0, 10)):
                d, r = rng.randrange(-4, 5), C._reduce(rng.randrange(0, 4), rng.choice((1, 2)))
                if d not in e.profile or C._gt(r, e.profile[d][0]):
                    e.profile[d] = (r, "part %d: %d at %d" % (i, trial, d))
            parts.append(e)
        old, new, live = (C.EntryStats("e", "error") for _ in range(3))
        for e in parts:
            old.merge(C.EntryStats.from_json(json.loads(json.dumps(_old_json(e)))))
            new.merge(C.EntryStats.from_json(json.loads(json.dumps(e.to_json()))))
            live.merge(e)
        for far in range(-6, 7):
            expect(old.observed_a(far) == new.observed_a(far),
                   "(a) beyond %d: %s with every distance, %s with the records (%s)"
                   % (far, old.observed_a(far), new.observed_a(far),
                      [_old_json(e)["profile"] for e in parts]))
        expect(old.to_json() == new.to_json() == live.to_json(),
               "the merged records differ: %s" % [_old_json(e)["profile"] for e in parts])
    return "%d element lines kept, judged again; %d random profiles" % (len(set(kept)), trials)
