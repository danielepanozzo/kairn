"""The oracle's own tests for the claims of the second wave (masks, value expressions, the
requirements power_of_two and nonneg, and the kinds rounded, upper, predicate, encloses).

As for the first wave, each test compares the oracle with something it does not share code
with: Fraction for expressions, a brute-force search for directed rounding, the reference
runners (Python and C++, written from milestone1.md's listings) for every kernel, injected
errors that must be flagged in the entry where they belong, and hand-written lines whose
verdicts and statistics are worked out by hand.
"""

import concurrent.futures as cf
import copy
import json
import os
import random
from fractions import Fraction as Q

from . import check as C
from . import expr as EX
from . import fmt as F
from . import gen as G
from . import refrun
from .claims import Claims, ClaimsError
from .selftest import (test, expect, Skip, py_run, judge, entry_failures, totals, cxx_run,
                       build_cxx, _value, FIXTURE2, TOY_ROUNDING_FORMATS, brute_values)

COMPARISONS = ("lt_2_2", "le_2_2", "eq_2_2", "lt_2_1", "le_2_1", "eq_2_1", "lt_1_2", "le_1_2")
CONVERSIONS = ("to_nearest_2", "to_down_2", "to_up_2", "abs_upper_2")
BALLS = ("ball_add_1", "ball_add_2", "ball_sub_1", "ball_sub_2", "ball_neg_1", "ball_neg_2",
         "ball_mul_1", "ball_mul_2", "ball_scale_1", "ball_scale_2")
SECOND_WAVE = (("neg_2", "abs_2", "sub_2_2", "sub_2_1", "sub_1_2") + COMPARISONS + CONVERSIONS
               + ("radd", "rmul", "mul_pow2_2") + BALLS)
# Radii for the restricted enumerations of the 2-limb balls: zero, eta, a subnormal, and radii
# around and above the centers of the tiny formats.
RADII = "0x0p+0/0x1p-3/0x1p-1/0x1.4p+1"


def failures(summary, kernels=None):
    return [e for (k, _f, _t), st in summary.keys.items() if kernels is None or k in kernels
            for e in st.examples["failure"]]


def stats(summary, kernel, kind):
    """The merged EntryStats of the first entry of a kind, over formats and tags."""
    out = None
    for (k, _f, _t), st in summary.keys.items():
        if k != kernel:
            continue
        for e in st.entries:
            if e.kind == kind:
                if out is None:
                    out = C.EntryStats(e.label, e.kind)
                out.merge(e)
                break
    return out


def exhaustive(ctx, kernel, fmtname, restrict=(), variant="correct", ignore_mp=False,
               chunk=20000):
    """The summary of every case of an enumeration through the Python runner, computed in
    parallel by the same in-process pipeline as `brute --runner refrun`."""
    from . import brute
    g = G.ExhaustiveGen(ctx.claims2.get(kernel), F.parse_format(fmtname), list(restrict))
    tasks = [dict(claims=FIXTURE2, kernel=kernel, format=fmtname, exhaustive=True,
                  restrict=list(restrict), seed=None, strata=None, variant=variant,
                  max_examples=5, ignore_min_precision=ignore_mp, start=s,
                  count=min(chunk, g.total - s)) for s in range(0, g.total, chunk)]
    if len(tasks) == 1:
        parts = [brute.run_inprocess(tasks[0])]
    else:
        with cf.ProcessPoolExecutor(max_workers=os.cpu_count() or 1) as ex:
            parts = list(ex.map(brute.run_inprocess, tasks))
    s = C.Summary()
    for p in parts:
        s.merge(C.Summary.from_json(p))
    return s


# ---------------------------------------------------------------------------

@test
def expressions(ctx):
    """Value expressions, compiled to integer arithmetic at static scales, against Fraction
    on random inputs; malformed expressions are refused."""
    rnd = random.Random(11)
    texts = ["-x", "abs(x)", "x-y", "c*x", "-(x+y)*z", "abs(x-y)*-z", "x*y*z", "abs(-x)",
             "x - -y", "(x)", "a*b+c*z-x", "-abs(-(a-b))", "x*(y-z)*abs(c)"]
    n = 0
    for text in texts:
        tree = EX.parse(text)
        names = sorted(set(EX.names(tree)))
        for q in (-1074, -10, 0, 3):
            src, scale = EX.compile_tree(tree, lambda nm: ("v[%d]" % names.index(nm), q))
            fn = EX.make_function(["v"], src)
            for _ in range(ctx.n(300, 60)):
                v = [rnd.choice([-1, 1]) * rnd.getrandbits(rnd.randint(0, 70)) for _ in names]
                env = {nm: Q(v[i]) * Q(2) ** q for i, nm in enumerate(names)}
                want = eval(text, {"__builtins__": {}, "abs": abs}, env)
                expect(Q(fn(v)) * Q(2) ** scale == want, "%s at q=%d: %r" % (text, q, v))
                n += 1
    for bad in ("x/y", "x+", "abs x", "(x", "x y", "", "x**y", "+x", "abs(x,y)", "2*x", "x)",
                "abs"):
        try:
            EX.parse(bad)
        except EX.ExprError:
            continue
        raise AssertionError("malformed expression %r accepted" % bad)
    return "%d evaluations of %d expressions" % (n, len(texts))


def _unbounded_values(p, qmin, qmax):
    """All numbers of the format and those of the next two binades above it (the format with
    its exponent range extended upward), as sorted Fractions."""
    vals = set(brute_values(p, qmin, qmax))
    for q in (qmax + 1, qmax + 2):
        for m in range(1 << (p - 1), 1 << p):
            vals.add(Q(m) * Q(2) ** q)
            vals.add(-Q(m) * Q(2) ** q)
    return sorted(vals)


@test
def rounding_directed(ctx):
    """Rounding down and up, and the gap below a number, against a brute-force search over
    the numbers of toy formats (range unbounded above), every multiple of eta/8."""
    import bisect
    pts = 0
    for p, qmin, qmax in TOY_ROUNDING_FORMATS:
        f = F.Format(p, qmin, qmax)
        vals = _unbounded_values(p, qmin, qmax)
        eta = Q(2) ** qmin
        step = eta / 8
        top = Q(2) ** (qmax + p)          # beyond Omega, still inside the extended list
        lim = int(top / step)
        for j in range(-lim, lim + 1):
            t = j * step
            i = bisect.bisect_right(vals, t)
            down = vals[i - 1]
            up = down if down == t else vals[i]
            got_d = F.rdir(f, j, qmin - 3, False)
            got_u = F.rdir(f, j, qmin - 3, True)
            expect(Q(got_d) * eta == down, "RD(%s) = %s, want %s in %s" % (t, got_d * eta, down, f.name))
            expect(Q(got_u) * eta == up, "RU(%s) = %s, want %s in %s" % (t, got_u * eta, up, f.name))
            pts += 1
        for v in vals:
            if abs(v) > Q(f.omega) * eta:
                continue
            i = bisect.bisect_left(vals, v)
            n = int(v / eta)
            expect(Q(F.gap_below(f, n)) * eta == v - vals[i - 1],
                   "gap below %s in %s" % (v, f.name))
    return "%d points in %d formats" % (pts, len(TOY_ROUNDING_FORMATS))


@test
def claims_reading_wave2(ctx):
    """The second-wave fixture loads and its instances (the list form) agree with c and t;
    malformed second-wave claims are set aside without making the others unreadable."""
    expect(not ctx.claims2.broken, "fixture2 kernels set aside: %s" % ctx.claims2.errors())
    expect(set(ctx.claims2.kernels) == set(SECOND_WAVE), "fixture2 kernels")
    raw = json.load(open(FIXTURE2))
    # The list form and the first-wave object form give the same bounds.
    d = copy.deepcopy(raw)
    k = next(x for x in d["kernels"] if x["name"] == "mul_pow2_2")
    per = {}
    for j, item in enumerate(k["instances"]):
        for fmtname, b in item.items():
            per.setdefault(fmtname, []).append(b)
    k["instances"] = per
    c1, c2 = Claims(raw).get("mul_pow2_2"), Claims(d).get("mul_pow2_2")
    f64 = F.parse_format("binary64")
    for e1, e2 in zip(c1.ensures, c2.ensures):
        if e1.kind == "error":
            expect(c1.bound(f64, e1) == c2.bound(f64, e2), "instance forms disagree")

    def must_fail(kernel, mutate, what):
        d = copy.deepcopy(raw)
        mutate(next(x for x in d["kernels"] if x["name"] == kernel))
        c = Claims(d)
        expect(kernel in c.broken and c.get(kernel) is None, "claims with %s accepted" % what)
        expect(len(c.kernels) == len(SECOND_WAVE) - 1, "%s made other kernels unreadable" % what)

    def ens(i, **kw):
        return lambda k: k["ensures"][i].update(**kw)

    must_fail("to_down_2", ens(0, mode="toward"), "an unknown rounding mode")
    must_fail("radd", ens(0, gaps="-1"), "negative gaps")
    must_fail("radd", ens(0, gaps="two"), "gaps that are not a rational")
    must_fail("lt_2_2", ens(0, rel="gt"), "an unknown relation")
    must_fail("lt_2_2", ens(0, args=["x"]), "one argument")
    must_fail("lt_2_2", ens(0, args=["x", "y/x"]), "a malformed argument")
    must_fail("lt_2_2", ens(0, args=["x", "m"]), "an argument naming an output")
    must_fail("lt_2_2", lambda k: k["outputs"].__setitem__(0, {"name": "m", "limbs": 1}),
              "a predicate of a limb output")
    must_fail("to_down_2", lambda k: k["outputs"][0].update(type="mask"), "a mask rounded")
    must_fail("mul_pow2_2", lambda k: k["ensures"].append({"kind": "rounded", "of": "z",
                                                           "mode": "up"}),
              "rounded of a 2-limb output")
    must_fail("lt_2_2", lambda k: k.update(value="m"), "a value naming a mask")
    must_fail("neg_2", lambda k: k["inputs"][0].update(type="bits"), "an unknown type")
    must_fail("ball_mul_1", lambda k: k["requires"].append("nonneg(q)"), "a requirement on no input")
    must_fail("ball_mul_1", lambda k: k["requires"].append("positive(rx)"), "an unknown requirement")
    must_fail("ball_mul_1", ens(0, set="X*X"), "a ball used twice")
    must_fail("ball_mul_1", ens(0, set="X"), "a ball not used")
    must_fail("ball_mul_1", ens(0, set="abs(X)*Y"), "abs in a set")
    must_fail("ball_mul_1", ens(0, set="X*Z"), "an unknown name in a set")
    must_fail("ball_mul_1", ens(0, set="X*cx"), "a ball's center used as a scalar")
    must_fail("ball_mul_1", ens(0, balls={"cx": {"center": "cx", "radius": "rx"},
                                          "Y": {"center": "cy", "radius": "ry"}}),
              "a ball named like an input")
    must_fail("ball_mul_1", ens(0, balls={"X": {"center": "cq", "radius": "rx"},
                                          "Y": {"center": "cy", "radius": "ry"}}),
              "a ball over an unknown input")
    must_fail("ball_mul_1", ens(0, balls={"X": {"center": "cx", "radius": "rx"},
                                          "Y": {"center": "cy", "radius": "rx"}}),
              "two balls sharing a radius")
    must_fail("ball_add_2", ens(1, radius="cz"), "a 2-limb radius")
    must_fail("ball_add_2", ens(1, center="rq"), "an unknown center")
    must_fail("mul_pow2_2", lambda k: k["instances"].pop(), "instances of the wrong length")
    must_fail("sub_2_2", ens(1, when="limb_products_normal"), "limb_products_normal on a sum")
    must_fail("mul_pow2_2", lambda k: k["instances"][0]["binary64"].update(abs="0"),
              "a listed instance that disagrees with t")
    return "fixture consistent; 27 malformed variants set aside"


@test
def gen_wave2(ctx):
    """Every generated case of every second-wave kernel and stratum satisfies the requirements;
    the correct runner passes on them; every stratum and both outcomes of every comparison
    occur; case i alone equals case i of a run."""
    n = 0
    for fname in ("binary64", "binary32", "fp:5:-10:5", "fp:4:-6:3"):
        lines = []
        for kname in SECOND_WAVE:
            lines += ctx.stream(kname, fname, ctx.n(1300, 260))
        s = judge(py_run(lines), ctx.claims2, ignore_min_precision=True)
        t = totals(s)
        expect(t["invalid"] == 0, "%s: %d invalid generated cases: %s" % (
            fname, t["invalid"], [e for st in s.keys.values() for e in st.examples["invalid"]][:2]))
        expect(t["failed"] == 0 and not s.stream_errors, "%s: correct runner flagged: %s"
               % (fname, failures(s)[:2]))
        for kname in SECOND_WAVE:
            known = G.RandomGen(ctx.claims2.get(kname), F.parse_format(fname), "x").strata
            tags = {k[2] for k in s.keys if k[0] == kname}
            expect(tags == set(known), "%s %s: strata %s" % (kname, fname, sorted(tags)))
        for kname in COMPARISONS:
            es = stats(s, kname, "predicate")
            expect(es.counts.get("true", 0) > 20 and es.counts.get("false", 0) > 20,
                   "%s %s: outcomes %s" % (kname, fname, es.counts))
        for kname in ("to_down_2", "to_up_2"):
            es = stats(s, kname, "rounded")
            expect(es.counts.get("inexact, != RN", 0) > 10 and es.counts.get("exact", 0) > 10,
                   "%s %s: outcomes %s" % (kname, fname, es.counts))
        n += t["cases"]
    rnd = random.Random(4)
    for kname in ("lt_2_1", "to_down_2", "rmul", "mul_pow2_2", "ball_mul_2", "ball_scale_1"):
        g = G.RandomGen(ctx.claims2.get(kname), F.parse_format("binary64"), "cb")
        run = list(g.lines(50, 100))[1:-1]
        for _ in range(5):
            i = rnd.randrange(50, 150)
            alone = list(G.RandomGen(ctx.claims2.get(kname), F.parse_format("binary64"), "cb")
                         .lines(i, 1))[1]
            expect(alone == run[i - 50], "case %d of %s" % (i, kname))
    return "%d cases" % n


@test
def exhaustive_wave2(ctx):
    """Enumeration domains of the new roles against brute-force counts, and the correct
    runner on every case of tiny formats for every second-wave kernel (the 2-limb balls on
    restricted radii, which the report marks as RESTRICTED)."""
    f = F.parse_format("fp:3:-3:2")
    vals = brute_values(3, -3, 2)
    eta = Q(2) ** -3
    pairs = len(G.normalized_pairs(f))
    nonneg = sum(1 for v in vals if v >= 0)
    fixed = [int(v / eta) for v in vals]
    pow2 = sum(1 for n in fixed if n > 0 and (n & (n - 1)) == 0)
    for kname, want in (("ball_add_1", len(vals) ** 2 * nonneg ** 2),
                        ("mul_pow2_2", pairs * pow2), ("ball_scale_1", len(vals) ** 2 * nonneg),
                        ("lt_2_1", pairs * len(vals)), ("radd", len(vals) ** 2)):
        g = G.ExhaustiveGen(ctx.claims2.get(kname), f)
        expect(g.total == want, "%s total %d, want %d" % (kname, g.total, want))
    g = G.ExhaustiveGen(ctx.claims2.get("ball_add_2"), f, ["rx.in=" + RADII, "ry.in=" + RADII])
    expect(g.total == pairs ** 2 * 16, "restricted ball_add_2 total %d" % g.total)
    # A mask input: domain, text, and the checker's reading of it.
    d = {"schema": 1, "kernels": [{"name": "pick", "inputs": [
        {"name": "m", "type": "mask"}, {"name": "a", "limbs": 1}],
        "outputs": [{"name": "r", "limbs": 1}], "value": "a", "requires": [],
        "ensures": [{"kind": "rounded", "of": "r", "mode": "nearest"}]}]}
    pick = Claims(d)
    g = G.ExhaustiveGen(pick.get("pick"), f)
    lines = list(g.lines(0, g.total))[1:-1]
    expect(g.total == 2 * len(vals) and {ln.split()[2] for ln in lines} == {"0", "1"},
           "mask domain")
    done = [ln.rsplit(" #", 1)[0] + " -> " + ln.split()[3] for ln in lines]
    s = judge(done + ["pick fp:3:-3:2 2 0x1p+0 -> 0x1p+0", "pick fp:3:-3:2 -0 0x1p+0 -> 0x1p+0"],
              pick)
    t = totals(s)
    expect(t["passed"] == len(lines) and t["invalid"] == 2, "mask inputs: %r" % t)
    rl = list(G.RandomGen(pick.get("pick"), f, "m").lines(0, 50))[1:-1]
    expect({ln.split()[2] for ln in rl} == {"0", "1"}, "random mask inputs")
    # The correct runner on every case.
    out = []
    small = [k for k in SECOND_WAVE if ctx.claims2.get(k).min_precision <= 2]
    plan = [("fp:2:-2:2", k, ()) for k in small]
    plan += [("fp:3:-3:2", k, ()) for k in ("neg_2", "abs_2", "sub_2_1", "sub_1_2", "lt_2_1",
                                            "le_2_1", "eq_2_1", "lt_1_2", "le_1_2", "radd", "rmul",
                                            "mul_pow2_2", "ball_neg_2", "ball_scale_1")
             + CONVERSIONS]
    plan += [("fp:3:-3:2", "ball_add_2", ("rx.in=" + RADII, "ry.in=" + RADII, "cx.lead=-1:0")),
             ("fp:3:-3:2", "ball_sub_2", ("rx.in=" + RADII, "ry.in=" + RADII, "cy.lead=-1:0")),
             ("fp:4:-4:2", "ball_scale_2", ("rx.in=0x0p+0/0x1p-4/0x1p+0", "cx.lead=-1:0"))]
    if not ctx.quick:
        plan += [("fp:3:-3:2", k, ()) for k in ("sub_2_2", "lt_2_2", "le_2_2", "eq_2_2",
                                                "ball_add_1", "ball_sub_1", "ball_mul_1")]
        plan += [("fp:3:-3:2", "ball_add_2", ("rx.in=" + RADII, "ry.in=" + RADII)),
                 ("fp:5:-6:3", "ball_mul_2", ("rx.in=0x0p+0/0x1p-6/0x1.8p+0",
                                              "ry.in=0x0p+0/0x1p-6/0x1.8p+0", "cx.lead=0:0",
                                              "cy.lead=-2:1"))]
    for fname, kname, restrict in plan:
        s = exhaustive(ctx, kname, fname, restrict)
        t = totals(s)
        expect(t["failed"] == 0 and not s.stream_errors and t["invalid"] == 0,
               "correct runner flagged on %s %s: %s" % (kname, fname, failures(s)[:2]))
        expect(t["judged"] > 0, "nothing judged for %s %s" % (kname, fname))
        cov = s.coverage.describe()
        expect(cov and ("COMPLETE" in cov[0]) == (not restrict), "coverage of %s: %s" % (kname, cov))
        out.append(t["cases"])
    return "%d enumerations, %d cases" % (len(out), sum(out))


@test
def cxx_wave2(ctx):
    """The C++ runner (hardware) passes on every second-wave kernel, and its results equal the
    Python runner's on every case (signs of zero aside)."""
    n = 0
    for fname in ("binary64", "binary32"):
        lines = []
        for kname in SECOND_WAVE:
            lines += ctx.stream(kname, fname, ctx.n(2000, 400))
        hw = cxx_run(ctx, lines)
        py = py_run(lines)
        expect(len(hw) == len(py), "line counts differ for %s" % fname)
        for a, b in zip(hw, py):
            if a.startswith("#"):
                expect(a == b, "comment not copied")
                continue
            la, _, ra = a.partition(" -> ")
            lb, _, rb = b.partition(" -> ")
            expect(la == lb, "request part changed: %r" % a)
            expect([t if t in "01" else _value(t) for t in ra.split()]
                   == [t if t in "01" else _value(t) for t in rb.split()],
                   "C++ and Python runners differ:\n  %s\n  %s" % (a, b))
            n += 1
        s = judge(hw, ctx.claims2)
        expect(totals(s)["failed"] == 0 and not s.stream_errors,
               "C++ correct runner flagged on %s: %s" % (fname, failures(s)[:2]))
    return "%d cases identical" % n


# Each injected error: (variant, kernels that must be flagged with the kind, strata of the
# streams, kernels that must not be flagged).
INJECTED = (
    ("cmp-lead-equal", COMPARISONS, "predicate", "equal,lastplace,leadequal",
     CONVERSIONS + ("radd", "rmul")),
    ("down-no-neg-step", ("to_down_2",), "rounded", "halfgap,uniform",
     ("to_up_2", "to_nearest_2", "abs_upper_2") + COMPARISONS),
    ("down-pow2-wrong-side", ("to_down_2",), "rounded", "pow2,halfgap",
     ("to_up_2", "to_nearest_2", "abs_upper_2")),
    ("radd-no-step", ("radd",), "upper", "uniform,tie,nonneg", ("rmul",) + CONVERSIONS),
    ("rmul-nearest", ("rmul",), "upper", "uniform,tie,nonneg", ("radd",) + CONVERSIONS),
    ("ball-no-center-error", ("ball_add_1", "ball_add_2", "ball_sub_1", "ball_sub_2",
                              "ball_mul_1", "ball_mul_2", "ball_scale_1", "ball_scale_2"),
     "encloses", "exact,centerpow2", ("ball_neg_1", "ball_neg_2", "radd", "rmul")),
    ("ball-no-rr", ("ball_mul_1", "ball_mul_2"), "encloses", "wide,radii",
     ("ball_add_1", "ball_add_2", "ball_scale_1", "ball_scale_2", "ball_neg_1")),
    ("abs-lead-only", ("abs_2",), "error", "uniform,halfgap,pow2",
     ("neg_2", "to_up_2", "to_down_2") + COMPARISONS),
)


def _injected(ctx, run, fname, label):
    res = []
    for variant, flagged, kind, strata, clean in INJECTED:
        lines = []
        for k in flagged + clean:
            lines += ctx.stream(k, fname, ctx.n(1500, 400), strata if k in flagged else None)
        s = judge(run(lines, variant), ctx.claims2)
        for k in flagged:
            expect(entry_failures(s, k, kind) > 0, "%s %s: %s not flagged in %s"
                   % (label, variant, k, kind))
        for k in clean:
            expect(totals(s, k)["failed"] == 0, "%s %s: %s flagged although it does not use "
                   "the error: %s" % (label, variant, k, failures(s, (k,))[:1]))
        res.append("%s %d" % (variant, totals(s)["failed"]))
    return res


@test
def injected_wave2(ctx):
    """Errors injected into the Python runner (a toy format, binary64) and the C++ runner
    (binary64, binary32), flagged in the entry where they belong and nowhere else."""
    res = []
    for fname in ("fp:5:-10:5", "binary64"):
        res += _injected(ctx, py_run, fname, "python %s" % fname)
    try:
        build_cxx(ctx)
        for fname in ("binary64", "binary32"):
            res += _injected(ctx, lambda lines, v: cxx_run(ctx, lines, v), fname, "C++ %s" % fname)
    except Skip as ex:
        res.append("C++ skipped: %s" % ex)
    return "; ".join(res)


@test
def injected_wave2_exhaustive(ctx):
    """The injected errors on every case of tiny formats; and the radius one unit in the last
    place too small at a power-of-two center, which the listing's slack absorbs: no verdict
    changes, and the smallest slack reported by the oracle drops by at least half a gap."""
    res = []
    for variant, flagged, kind, _strata, _clean in INJECTED:
        for k in flagged:
            if ctx.claims2.get(k).min_precision > 3:
                continue
            fname = "fp:3:-3:2" if k not in COMPARISONS[:3] or not ctx.quick else "fp:2:-2:2"
            restrict = ("rx.in=" + RADII, "ry.in=" + RADII, "cx.lead=-1:0") if k in (
                "ball_add_2", "ball_sub_2") else ("rx.in=" + RADII, "ry.in=" + RADII) if k in (
                "ball_add_1", "ball_sub_1", "ball_mul_1") else ()
            s = exhaustive(ctx, k, fname, restrict, variant)
            expect(entry_failures(s, k, kind) > 0, "%s %s not flagged on every case of %s"
                   % (variant, k, fname))
        res.append(variant)
    for k in ("ball_add_1", "ball_mul_1", "ball_scale_1"):
        good = exhaustive(ctx, k, "fp:2:-2:2")
        bad = exhaustive(ctx, k, "fp:2:-2:2", (), "ball-pow2-ulp")
        expect(totals(bad)["failed"] == 0 and totals(bad)["judged"] == totals(good)["judged"],
               "ball-pow2-ulp on %s: verdicts changed: %s" % (k, failures(bad)[:1]))
        sg = stats(good, k, "encloses").minima["slack in gaps of the radius"][0]
        sb = stats(bad, k, "encloses").minima["slack in gaps of the radius"][0]
        expect(Q(*sb) <= Q(*sg) - Q(1, 2), "ball-pow2-ulp on %s: slack %s -> %s" % (
            k, Q(*sg), Q(*sb)))
        res.append("%s slack %s -> %s" % (k, Q(*sg), Q(*sb)))
    return "; ".join(res)


@test
def judge_wave2(ctx):
    """Hand-written lines with verdicts and statistics worked out by hand."""
    cl = ctx.claims2
    cases = [
        # Comparisons: masks are 0 or 1, and the truth of the relation of the exact values.
        ("lt_2_2 binary64 0x1p+0 0x0p+0 0x1p+0 0x0p+0 -> 0", "passed"),
        ("lt_2_2 binary64 0x1p+0 0x0p+0 0x1p+0 0x0p+0 -> 1", "failed"),
        ("lt_2_2 binary64 0x1p+0 0x0p+0 0x1p+0 0x0p+0 -> 2", "failed"),
        ("lt_2_2 binary64 0x1p+0 0x0p+0 0x1p+0 0x0p+0 -> 0x0p+0", "failed"),
        ("lt_2_2 binary64 0x1p+0 -0x1p-60 0x1p+0 0x0p+0 -> 1", "passed"),
        ("lt_2_2 binary64 0x1p+0 -0x1p-60 0x1p+0 0x0p+0 -> 2", "failed"),
        ("lt_2_2 binary64 0x1p+1 0x0p+0 0x1p+0 0x0p+0 -> 0", "passed"),
        ("le_2_2 binary64 0x1p+0 -0x1p-60 0x1p+0 -0x1p-60 -> 1", "passed"),
        ("le_2_2 binary64 0x1p+0 -0x1p-60 0x1p+0 -0x1p-60 -> 0", "failed"),
        ("eq_2_1 binary64 0x1p+0 0x1p-60 0x1p+0 -> 0", "passed"),
        ("eq_2_1 binary64 0x1p+0 0x1p-60 0x1p+0 -> 1", "failed"),
        ("eq_2_2 binary64 0x0p+0 -0x0p+0 -0x0p+0 0x0p+0 -> 1", "passed"),
        ("lt_1_2 binary64 0x1p+0 0x1p+0 -0x1p-60 -> 0", "passed"),
        ("le_1_2 binary64 -0x1p-1074 0x0p+0 0x0p+0 -> 1", "passed"),
        ("lt_2_2 binary64 0x1p+0 0x1p+0 0x1p+0 0x0p+0 -> 0", "invalid"),
        # Conversions: the value rounded in the direction claimed.
        ("to_down_2 binary64 0x1p+0 -0x1p-60 -> 0x1.fffffffffffffp-1", "passed"),
        ("to_down_2 binary64 0x1p+0 -0x1p-60 -> 0x1p+0", "failed"),
        ("to_up_2 binary64 0x1p+0 0x1p-60 -> 0x1.0000000000001p+0", "passed"),
        ("to_up_2 binary64 0x1p+0 0x1p-60 -> 0x1p+0", "failed"),
        ("to_up_2 binary64 -0x1p+0 0x1p-60 -> -0x1.fffffffffffffp-1", "passed"),
        ("to_nearest_2 binary64 0x1p+0 0x1p-53 -> 0x1p+0", "passed"),
        ("to_down_2 binary64 0x1p-1022 0x0p+0 -> 0x1p-1022", "passed"),
        ("abs_upper_2 binary64 -0x1p+0 0x1p-60 -> 0x1p+0", "passed"),
        ("abs_upper_2 binary64 -0x1p+0 0x1p-60 -> 0x1.0000000000001p+0", "failed"),
        # Rounding up beyond Omega: outside the statement, counted as non-finite.
        ("to_up_2 binary64 0x1.fffffffffffffp+1023 0x1p+969 -> 0x1.fffffffffffffp+1023", "beyond"),
        ("to_up_2 binary64 0x1.fffffffffffffp+1023 0x1p+969 -> inf", "beyond"),
        # Upper bounds: at least the value, by at most two gaps below the output.
        ("radd binary64 0x1p+0 0x1p-60 -> 0x1.0000000000001p+0", "passed"),
        ("radd binary64 0x1p+0 0x1p-60 -> 0x1.0000000000002p+0", "passed"),
        ("radd binary64 0x1p+0 0x1p-60 -> 0x1.0000000000003p+0", "failed"),
        ("radd binary64 0x1p+0 0x1p-60 -> 0x1p+0", "failed"),
        # -1 - 2^-53 is a tie, RN gives -1 and succ -1 + 2^-53: two gaps exactly.
        ("radd binary64 -0x1p+0 -0x1p-53 -> -0x1.fffffffffffffp-1", "passed"),
        # 2.5 gaps below 1 (half the gap above it): too far.
        ("radd binary64 0x1.ffffffffffffep-1 -0x1p-54 -> 0x1p+0", "failed"),
        ("rmul binary64 0x1p+0 0x1.8p+0 -> 0x1.8p+0", "passed"),
        ("rmul binary64 -0x1p-1074 0x1p-1 -> 0x1p-1074", "passed"),
        ("radd binary64 -0x1.fffffffffffffp+1023 -0x1.fffffffffffffp+1023 "
         "-> -0x1.fffffffffffffp+1023", "beyond"),
        # X = [-1, 2], Y = [-3, 1]: X*Y = [-6, 3], from the corners (2, -3) and (-1, -3).
        ("ball_mul_1 binary64 0x1p-1 0x1.8p+0 -0x1p+0 0x1p+1 -> -0x1p-1 0x1.6p+2", "passed"),
        ("ball_mul_1 binary64 0x1p-1 0x1.8p+0 -0x1p+0 0x1p+1 -> -0x1p-1 0x1.5ffffffffffffp+2",
         "failed"),
        ("ball_mul_1 binary64 0x1p-1 0x1.8p+0 -0x1p+0 0x1p+1 -> -0x1p-1 0x1.cp+1", "failed"),
        ("ball_mul_1 binary64 0x1p-1 0x1.8p+0 -0x1p+0 0x1p+1 -> 0x1p+0 0x1.cp+2", "passed"),
        ("ball_mul_1 binary64 0x1p-1 0x1.8p+0 -0x1p+0 0x1p+1 -> 0x1p+0 0x1.bffffffffffffp+2",
         "failed"),
        # A point: the center's tail counts.
        ("ball_add_2 binary64 0x1p+0 0x1p-60 0x0p+0 0x0p+0 0x0p+0 0x0p+0 "
         "-> 0x1p+0 0x1p-60 0x1p-100", "passed"),
        ("ball_scale_1 binary64 0x1p+0 0x1p-1 -0x1.8p+0 -> -0x1.8p+0 0x1.8p-1", "passed"),
        ("ball_scale_1 binary64 0x1p+0 0x1p-1 -0x1.8p+0 -> -0x1.8p+0 0x1.7ffffffffffffp-1",
         "failed"),
        ("ball_neg_2 binary64 0x1p+0 0x1p-60 0x1p-3 -> -0x1p+0 -0x1p-60 0x1p-3", "passed"),
        ("ball_neg_2 binary64 0x1p+0 0x1p-60 0x1p-3 -> -0x1p+0 0x1p-60 0x1p-3", "failed"),
        # Requirements of the second wave.
        ("ball_add_1 binary64 0x1p+0 -0x1p+0 0x1p+0 0x0p+0 -> 0x1p+1 0x1p+0", "invalid"),
        ("mul_pow2_2 binary64 0x1p+0 0x0p+0 0x1.8p+1 -> 0x1.8p+1 0x0p+0", "invalid"),
        ("mul_pow2_2 binary64 0x1p+0 0x0p+0 -0x1p+1 -> -0x1p+1 0x0p+0", "invalid"),
        ("mul_pow2_2 binary64 0x1p+0 0x0p+0 0x0p+0 -> 0x0p+0 0x0p+0", "invalid"),
        ("mul_pow2_2 binary64 0x1p+0 0x1p-60 0x1p+1 -> 0x1p+1 0x1p-59", "passed"),
        ("mul_pow2_2 binary64 0x1p+0 0x1p-60 0x1p+1 -> 0x1p+1 0x0p+0", "failed"),
        # 3 2^-60 * 2^-1020 is below eta/2: the tail is lost, which only the exactness entry
        # would forbid, and it does not apply (a limb product is below 2^(p-1) eta).
        ("mul_pow2_2 binary64 0x1p+0 0x1.8p-59 0x1p-1020 -> 0x1p-1020 0x0p+0", "passed"),
        ("mul_pow2_2 binary64 0x1p+0 0x1.8p-59 0x1p-1022 -> 0x1p-1022 0x0p+0", "passed"),
        ("mul_pow2_2 binary64 0x1p+0 0x1p-53 0x1p-1000 -> 0x1p-1000 0x0p+0", "failed"),
    ]
    for line, want in cases:
        s = judge([line], cl)
        t = totals(s)
        got = ("beyond" if t["beyond"] == 1 and t["failed"] == 0 else
               "passed" if t["passed"] == 1 else "failed" if t["failed"] == 1 else
               "invalid" if t["invalid"] == 1 else repr(t))
        expect(got == want, "%s: %s, want %s" % (line, got, want))
    # Statistics, over the lines that pass.
    s = judge([c for c, w in cases if w == "passed"], cl)
    up = stats(s, "radd", "upper")
    expect(up.maxima["excess in gaps"][0] == (2, 1) and
           up.maxima["excess in gaps, nonnegative operands"][0] == (511, 256),
           "radd excess %r" % up.maxima)
    expect(up.counts == {"excess in (3/4, 1] gaps": 1, "excess in (7/4, 2] gaps": 2},
           "radd histogram %r" % up.counts)
    um = stats(s, "rmul", "upper")
    expect(um.maxima["excess in gaps"][0] == (3, 2) and
           um.maxima["excess in gaps, nonnegative operands"][0] == (0, 1), "rmul %r" % um.maxima)
    expect(um.counts == {"exact": 1, "excess in (5/4, 3/2] gaps": 1}, "rmul %r" % um.counts)
    pr = stats(s, "lt_2_2", "predicate")
    expect(pr.counts == {"true": 1, "false": 2}, "lt_2_2 outcomes %r" % pr.counts)
    en = stats(s, "ball_mul_1", "encloses")
    expect(en.minima["slack in gaps of the radius"][0] == (0, 1) and
           en.minima["radius / smallest enclosing radius"][0] == (1, 1) and
           en.counts.get("ratio 1") == 2, "ball_mul_1 statistics %r %r" % (en.minima, en.counts))
    ro = stats(s, "to_down_2", "rounded")
    expect(ro.counts == {"inexact, != RN": 1, "exact": 1}, "to_down_2 outcomes %r" % ro.counts)
    return "%d lines" % len(cases)


@test
def scaled_gaps(ctx):
    """With the gaps of radd and rmul halved the correct runner must fail, with them times
    1024 it must pass, and the largest excess in gaps must not move: it measures the data."""
    lines = []
    for fname in ("fp:5:-10:5", "binary64"):
        for k in ("radd", "rmul"):
            lines += ctx.stream(k, fname, ctx.n(3000, 800))
    done = py_run(lines)

    def claims(factor):
        d = json.load(open(FIXTURE2))
        for k in d["kernels"]:
            for e in k["ensures"]:
                if e["kind"] == "upper":
                    e["gaps"] = str(Q(e["gaps"]) * factor)
        return Claims(d)

    base, half, big = (judge(done, claims(f)) for f in (1, Q(1, 2), 1024))
    expect(not base.failed() and half.failed() and not big.failed(), "scaled gaps verdicts")
    for k in ("radd", "rmul"):
        m = [stats(x, k, "upper").maxima["excess in gaps"][0] for x in (base, half, big)]
        expect(m[0] == m[1] == m[2] and Q(*m[0]) > 1, "%s: largest excess %s" % (k, m))
    return "largest excess %s (radd), %s (rmul)" % tuple(
        Q(*stats(base, k, "upper").maxima["excess in gaps"][0]) for k in ("radd", "rmul"))


@test
def nonneg_steps(ctx):
    """radd and rmul as the library claims them, with nonnegative operands and 3/2 gaps: every
    stratum still generates (an operand loses its sign, it is not drawn again), the correct
    runner passes, 3/2 gaps is reached, and with 5/4 the correct runner must fail."""
    def claims(gaps):
        d = json.load(open(FIXTURE2))
        for k in d["kernels"]:
            if k["name"] in ("radd", "rmul"):
                k["requires"] = ["nonneg(a)", "nonneg(b)"]
                for e in k["ensures"]:
                    if e["kind"] == "upper":
                        e["gaps"] = gaps
        return Claims(d)

    cl, tight = claims("3/2"), claims("5/4")
    n = 0
    for fname in ("fp:5:-10:5", "binary64"):
        f = F.parse_format(fname)
        lines = []
        for k in ("radd", "rmul"):
            lines += list(G.RandomGen(cl.get(k), f, "nonneg").lines(0, ctx.n(6000, 1500)))
        done = py_run(lines)
        s = judge(done, cl)
        t = totals(s)
        expect(t["invalid"] == 0 and t["failed"] == 0 and not s.stream_errors,
               "%s: %r %s" % (fname, t, failures(s)[:2]))
        for k in ("radd", "rmul"):
            known = G.RandomGen(cl.get(k), f, "x").strata
            tags = {key[2] for key in s.keys if key[0] == k}
            expect(tags == set(known), "%s %s: strata %s" % (k, fname, sorted(tags)))
            m = stats(s, k, "upper").maxima["excess in gaps"][0]
            expect(Q(*m) == Q(3, 2), "%s %s: largest excess %s" % (k, fname, m))
        expect(judge(done, tight).failed(), "%s: 5/4 gaps must fail" % fname)
        n += t["cases"]
    return "%d cases, largest excess 3/2 gaps" % n


@test
def merging_wave2(ctx):
    """Summaries of two halves of a second-wave stream merge into the summary of the whole."""
    lines = []
    for k in SECOND_WAVE:
        lines += py_run(ctx.stream(k, "fp:5:-10:5", ctx.n(600, 150)))
    whole = judge(lines, ctx.claims2, max_examples=100000)
    cut = len(lines) // 2
    while not lines[cut].startswith("# kairn-oracle gen event=begin"):
        cut += 1
    a = judge(lines[:cut], ctx.claims2, max_examples=100000)
    b = judge(lines[cut:], ctx.claims2, max_examples=100000)
    m = C.Summary(100000)
    for part in (a, b):
        m.merge(C.Summary.from_json(json.loads(json.dumps(part.to_json())), 100000))
    ja, jb = whole.to_json(), m.to_json()
    for j in (ja, jb):
        for e in j["keys"]:
            e["stats"]["examples"] = None
            for en in e["stats"]["entries"]:
                en["max_ratio_case"] = en["b_case"] = None
                en["profile"] = {d: v[0] for d, v in en["profile"].items()}
                for f in ("maxima", "minima"):
                    en[f] = {d: v[0] for d, v in en[f].items()}
    expect(ja == jb, "merged summary differs from the whole")
    return "%d lines" % len(lines)
