"""The oracle's own tests for the non-finite layer (architecture.md, "Claims of the non-finite
layer"; milestone1.md, "IEEE-like results", "Values that enter from the program", "Ball
kernels").

As for the first two waves, each test compares the oracle with something it does not share code
with: Python's own IEEE arithmetic on floats for the extended reals, brute-force definitions of
canonical values and balls, brute-force counts of the enumerations, the reference runners
(Python and C++, written from milestone1.md's listings), planted bugs that must be caught in the
statement where they belong and nowhere else, and hand-written lines whose verdicts are worked
out by hand.
"""

import concurrent.futures as cf
import copy
from bisect import bisect_left
import json
import math
import os
import random
from fractions import Fraction as Q

from . import check as C
from . import expr as EX
from . import extended as XT
from . import fmt as F
from . import gen as G
from . import refrun
from .claims import Claims, load_claims
from .selftest import (test, expect, Skip, judge, totals, cxx_run, build_cxx, _value,
                       ORACLE_DIR, BruteRN, brute_values, FIXTURE, FIXTURE2)

FIXTURE3 = os.path.join(ORACLE_DIR, "selftest", "claims-wave3.json")
FULL = ("add_2_2_full", "add_fast_2_2_full", "sub_2_2_full", "add_2_1_full", "sub_2_1_full",
        "sub_1_2_full", "mul_2_2_full", "mul_2_1_full", "mul_pow2_2_full")
FULL22 = ("add_2_2_full", "add_fast_2_2_full", "sub_2_2_full", "mul_2_2_full")
BALLF = ("ball_add_1_full", "ball_add_2_full", "ball_sub_1_full", "ball_sub_2_full",
         "ball_mul_1_full", "ball_mul_2_full", "ball_scale_1_full", "ball_scale_2_full")
MAKE = ("make_2", "make_2_limbs", "ball_make_1", "ball_make_2")
BALLNEG = ("ball_neg_1", "ball_neg_2")
GAINED = ("neg_2", "abs_2", "lt_2_2", "le_2_2", "eq_2_2", "lt_2_1", "le_2_1", "eq_2_1", "lt_1_2",
          "le_1_2", "to_nearest_2", "to_down_2", "to_up_2", "abs_upper_2", "radd", "rmul")
CORES = ("add_2_2", "add_fast_2_2", "sub_2_2", "add_2_1", "sub_2_1", "sub_1_2", "mul_2_2",
         "mul_2_1", "mul_pow2_2")
ONE_OPS = ("add_1_1", "mul_1_1")
EXTENDED = FULL + BALLF + BALLNEG + MAKE + GAINED
# The kernels of the fixture whose minimum precision is 1.
PRECISION_ONE = ("neg_2", "abs_2", "lt_2_2", "le_2_2", "eq_2_2", "lt_2_1", "le_2_1", "eq_2_1",
                 "lt_1_2", "le_1_2", "to_nearest_2", "to_down_2", "to_up_2", "abs_upper_2",
                 "add_1_1", "mul_1_1", "ball_neg_1", "ball_neg_2") + MAKE
# The Ball kernels of this layer are run with the cores of the second radius design (the design
# their IEEE-model statements are proved with); the second wave's tests run the first.
RADIUS = "second"
# Formats: two named ones, a toy format, and toy formats of the shape of Flocq's IEEE formats
# (qmin + qmax = 3 - 2p), as the IEEE-model statements require.
FORMATS3 = ("binary64", "binary32", "fp:5:-10:5", "fp:4:-6:1")
IEEE_TOYS = ("fp:3:-4:1", "fp:3:-3:0", "fp:4:-4:-1", "fp:2:-2:1")


def claims3(ctx):
    if not hasattr(ctx, "claims3"):
        ctx.claims3 = load_claims(FIXTURE3)
    return ctx.claims3


def run3(lines, variant="correct", radius=RADIUS):
    r = refrun.Runner(variant, radius=radius)
    out = []
    for ln in lines:
        out.extend(r.complete(ln))
    return out


def stream3(ctx, kernel, fmtname, count, strata=None, seed="selftest3"):
    key = ("w3", kernel, fmtname, count, strata, seed)
    s = ctx._streams.get(key)
    if s is None:
        g = G.RandomGen(claims3(ctx).get(kernel), F.parse_format(fmtname), seed,
                        strata.split(",") if strata else None)
        s = ctx._streams[key] = list(g.lines(0, count))
    return s


def exhaustive3(ctx, kernel, fmtname, restrict=(), variant="correct", ignore_mp=False,
                chunk=20000, claims_path=FIXTURE3, radius=RADIUS):
    """The summary of every case of an enumeration through the Python runner, in parallel, by
    the pipeline of `brute --runner refrun`."""
    from . import brute
    cl = claims3(ctx) if claims_path == FIXTURE3 else load_claims(claims_path)
    g = G.ExhaustiveGen(cl.get(kernel), F.parse_format(fmtname), list(restrict))
    tasks = [dict(claims=claims_path, kernel=kernel, format=fmtname, exhaustive=True,
                  restrict=list(restrict), seed=None, strata=None, variant=variant,
                  max_examples=5, ignore_min_precision=ignore_mp, start=s, radius=radius,
                  count=min(chunk, g.total - s)) for s in range(0, g.total, chunk)]
    if len(tasks) == 1:
        parts = [brute.run_inprocess(tasks[0])]
    else:
        with cf.ProcessPoolExecutor(max_workers=min(ctx.jobs, len(tasks))) as ex:
            parts = list(ex.map(brute.run_inprocess, tasks))
    s = C.Summary()
    for p in parts:
        s.merge(C.Summary.from_json(p))
    return s


def failures(summary, kernels=None, kind="failure"):
    return [e for (k, _f, _t), st in summary.keys.items() if kernels is None or k in kernels
            for e in st.examples[kind]]


def counts(summary, kernel, tag=None, prefix=""):
    """The counts of the entries of a kernel (not those of its core), summed over formats and
    tags (or for one tag), keys starting with prefix."""
    out = {}
    for (k, _f, t), st in summary.keys.items():
        if k != kernel or (tag is not None and t != tag):
            continue
        for e in st.entries:
            if e.label.startswith("F2, core"):
                continue
            for key, n in e.counts.items():
                if key.startswith(prefix):
                    out[key] = out.get(key, 0) + n
    return out


def minima(summary, kernel):
    out = {}
    for (k, _f, _t), st in summary.keys.items():
        if k == kernel:
            for e in st.entries:
                for name, (r, line) in e.minima.items():
                    if name not in out or Q(*r) < Q(*out[name][0]):
                        out[name] = (r, line)
    return out


# ---------------------------------------------------------------------------

@test
def claims_reading_wave3(ctx):
    """The fixture of the non-finite layer loads, its cores are linked; a domain written out as
    finite changes nothing; malformed claims of the layer are set aside without making the
    others unreadable."""
    cl = claims3(ctx)
    expect(not cl.broken, "fixture3 kernels set aside: %s" % cl.errors())
    expect(set(cl.kernels) == set(EXTENDED + CORES + ONE_OPS), "fixture3 kernels")
    for k in EXTENDED:
        expect(cl.get(k).extended, "%s is not of the extended domain" % k)
    for k in CORES + ONE_OPS:
        expect(not cl.get(k).extended, "%s is not finite" % k)
    for k in FULL:
        e = cl.get(k).ensures[0]
        expect(e.kind == "extends" and e.core is cl.get(e.core_name), "%s: core not linked" % k)
    raw = json.load(open(FIXTURE3))
    # Order does not matter: a full kernel listed before its core is linked as well.
    d = copy.deepcopy(raw)
    d["kernels"].reverse()
    expect(not Claims(d).broken, "a full kernel before its core is not read")
    # "domain": "finite" written out is the absent domain: the same summary on the same lines.
    for path, kname in ((FIXTURE, "add_2_2"), (FIXTURE2, "ball_mul_2")):
        d = json.load(open(path))
        for k in d["kernels"]:
            k["domain"] = "finite"
        lines = run3(list(G.RandomGen(load_claims(path).get(kname), F.parse_format("fp:5:-10:5"),
                                      "d").lines(0, 300)))
        a, b = judge(lines, load_claims(path)).to_json(), judge(lines, Claims(d, path)).to_json()
        expect(a == b, "%s: an explicit finite domain changed the summary" % kname)

    tried = []

    def rename_y(k):
        # The same shapes as the core, another name for the second input.
        k["inputs"][1]["name"] = "v"
        k["value"] = "x+v"
        k["requires"] = ["canonical(x)", "canonical(v)"]
        k["ensures"][0]["finite_when"] = [{"abs_le": "x", "exp": -2}, {"abs_le": "v", "exp": -2}]

    def must_fail(kernel, mutate, what, also=()):
        tried.append(what)
        d = copy.deepcopy(raw)
        mutate(next(x for x in d["kernels"] if x["name"] == kernel))
        c = Claims(d)
        expect(kernel in c.broken and c.get(kernel) is None, "claims with %s accepted" % what)
        gone = {kernel} | set(also)
        expect(len(c.kernels) == len(raw["kernels"]) - len(gone),
               "%s made other kernels unreadable: %s" % (what, sorted(set(c.broken) - gone)))

    def ext(**kw):
        return lambda k: k["ensures"][0].update(**kw)

    def fw(v):
        return ext(finite_when=v)

    must_fail("add_2_2_full", ext(core="add_9_9"), "a core that does not exist")
    must_fail("add_2_2_full", ext(core="add_2_2_full"), "a kernel as its own core")
    must_fail("add_2_1_full", ext(core="add_2_2"), "a core with other inputs")
    must_fail("sub_1_2_full", ext(core="add_2_1"), "a core with its inputs in another order")
    must_fail("add_2_2_full", rename_y, "a core with other input names")

    def rename_a(k):
        # Only the name differs: the scalar has no requirement and the value is the same
        # polynomial by position.
        k["inputs"][1]["name"] = "b"
        k["value"] = "x+b"

    must_fail("add_2_1_full", rename_a, "a core with another name for an unconstrained input")
    must_fail("add_2_2_full", lambda k: k["outputs"][0].update(limbs=1), "a core with other outputs")
    must_fail("add_2_2_full", ext(core="neg_2"), "a core of the extended domain")
    must_fail("sub_2_2_full", ext(core="add_2_2"), "a core with another value")
    must_fail("add_2_2_full", lambda k: k.update(min_precision=4), "another min_precision")
    must_fail("mul_pow2_2_full", lambda k: k["requires"].pop(), "requirements not the core's")
    must_fail("add_2_2_full", ext(lead="div"), "an unknown lead")
    must_fail("add_2_2_full", ext(lead="sub"), "a lead that is not the value's operation")
    must_fail("sub_1_2_full", lambda k: k.update(value="y-a"), "a difference in the wrong order")
    must_fail("add_2_2_full", lambda k: k["ensures"][0].pop("finite_when"), "no finite_when")
    must_fail("add_2_2_full", fw({"abs_le": "x", "exp": -2}), "finite_when not a list")
    must_fail("add_2_2_full", fw([{"abs_le": "q", "exp": -2}]), "finite_when over an unknown name")
    must_fail("add_2_2_full", fw([{"abs_le": "w", "exp": -2}]), "finite_when over an output")
    must_fail("add_2_2_full", fw([{"abs_le": "x/y", "exp": -2}]), "a malformed finite_when")
    must_fail("add_2_2_full", fw([{"abs_le": "x"}]), "finite_when without exp")
    must_fail("add_2_2_full", fw([{"abs_le": "x", "exp": "-2"}]), "exp as a string")
    must_fail("add_2_2_full", fw([{"abs_le": "x", "exp": True}]), "exp as a boolean")
    must_fail("add_2_2_full", fw([{"abs_le": "x", "exp": -2, "rel": "le"}]), "an extra field")
    must_fail("add_2_2_full", ext(extra=1), "an unknown field of extends")
    must_fail("add_2_2_full", lambda k: k.pop("domain"), "extends in the finite domain")
    must_fail("add_2_2_full", lambda k: k.update(domain="infinite"), "an unknown domain")
    must_fail("add_2_2_full", lambda k: k.update(requires=["normalized(x)", "canonical(y)"]),
              "normalized() in the extended domain")
    must_fail("add_2_2_full", lambda k: k.update(requires=["canonical(x)"]),
              "a 2-limb input without canonical()")
    must_fail("add_2_1_full", lambda k: k["requires"].append("canonical(a)"),
              "canonical() of a one-limb input")
    must_fail("add_2_2", lambda k: k.update(requires=["canonical(x)", "normalized(y)"]),
              "canonical() in the finite domain", also=("add_2_2_full",))
    must_fail("add_2_1", lambda k: k["requires"].append("finite(a)"),
              "an unreadable core", also=("add_2_1_full",))
    must_fail("ball_add_2_full", lambda k: k.update(requires=["ball(cx, cy)", "ball(rx, ry)"]),
              "a ball with a 2-limb radius")
    must_fail("ball_add_1_full", lambda k: k.update(requires=["ball(cx, rx)", "ball(cy, rx)"]),
              "two balls sharing a radius")
    must_fail("ball_add_1_full", lambda k: k.update(requires=["ball(cx, rx)", "nonneg(ry)"]),
              "a ball of the set without ball()")
    must_fail("ball_add_1_full", lambda k: k.pop("domain"), "ball() in the finite domain")
    must_fail("ball_mul_1_full", lambda k: k["ensures"][0].pop("finite_when"),
              "encloses of the extended domain without finite_when")
    must_fail("ball_mul_1_full", lambda k: k["ensures"][0].update(
        finite_when=[{"abs_le": "x", "exp": -2}]), "finite_when over a ball name")
    must_fail("make_2", lambda k: k.pop("value"), "represents without a value")
    must_fail("make_2", lambda k: k["ensures"][0].update(of="q"), "represents of no output")
    must_fail("ball_make_2", lambda k: k["ensures"][0].pop("from"), "makes_ball without from")
    must_fail("ball_make_2", lambda k: k["ensures"][0].update(from_={}), "makes_ball, unknown field")
    must_fail("ball_make_2", lambda k: k["ensures"][0].update(
        **{"from": {"center": "r", "radius": "c"}}), "a 2-limb given radius")
    must_fail("ball_make_2", lambda k: k["ensures"][0].update(
        **{"from": {"center": "c", "radius": "c"}}), "one input as center and radius")
    must_fail("ball_make_1", lambda k: k["ensures"][0].update(
        **{"from": {"center": "c", "radius": "q"}}), "a given radius that is not an input")
    must_fail("ball_make_2", lambda k: k["ensures"][0].update(center="rw", radius="cw"),
              "a 2-limb output radius")
    must_fail("ball_make_1", lambda k: k.update(outputs=[{"name": "cw", "limbs": 2},
                                                         {"name": "rw", "limbs": 1}]),
              "a 2-limb center made from one limb")
    must_fail("neg_2", lambda k: k.update(ieee_status="maybe"), "an unknown ieee_status")
    must_fail("neg_2", lambda k: k.update(ieee_theorem="Neg.v"), "an ieee_theorem not an object")
    # Statuses are read, never used: none, or proved without a theorem, is a warning only.
    d = copy.deepcopy(raw)
    next(x for x in d["kernels"] if x["name"] == "neg_2").pop("ieee_status")
    next(x for x in d["kernels"] if x["name"] == "abs_2")["ieee_status"] = "proved"
    c = Claims(d)
    ck = C.Checker(c)
    expect(not c.broken and len(ck.summary.claims_warnings) == 2,
           "status warnings: %s %s" % (c.errors(), ck.summary.claims_warnings))
    return "fixture consistent; %d malformed variants set aside" % len(tried)


def _float_of(v, s):
    """A limb value of the extended reals as Python's float arithmetic sees it."""
    if type(v) is int:
        return Q(v) * Q(2) ** s
    return {F.POS_INF: math.inf, F.NEG_INF: -math.inf, F.NAN: math.nan}[v]


def _ref_eval(tree, env):
    """The expression in Python's own arithmetic: Fractions for finite values, IEEE floats for
    the infinities and NaN (inf - inf and 0 * inf are NaN there too)."""
    k = tree[0]
    if k == "name":
        return env[tree[1]]
    if k == "neg":
        return -_ref_eval(tree[1], env)
    if k == "abs":
        return abs(_ref_eval(tree[1], env))
    a, b = _ref_eval(tree[1], env), _ref_eval(tree[2], env)
    if isinstance(a, float) != isinstance(b, float):
        # Against an infinity or a NaN only the sign of a finite value matters; converting it
        # to a float could underflow to zero.
        a, b = (x if isinstance(x, float) else float((x > 0) - (x < 0)) for x in (a, b))
    return a + b if k == "+" else a - b if k == "-" else a * b


def _same(got, want):
    if isinstance(want, float):
        if math.isnan(want):
            return got == F.NAN
        return got == (F.POS_INF if want > 0 else F.NEG_INF)
    return got == want


@test
def extended_arithmetic(ctx):
    """Expressions in the extended reals against Python's IEEE floats and Fractions on random
    operands, infinities and NaN included; canonical values and ball states against their
    definitions on every pair of limbs of a tiny format."""
    rnd = random.Random(31)
    texts = ["x+y", "x-y", "x*y", "-x", "abs(x)", "c*x", "-(x+y)*z", "abs(x-y)*-z", "x*y*z",
             "x - -y", "a*b+c*z-x", "(abs(x)+y)*(abs(z)+a)"]
    vals = [F.POS_INF, F.NEG_INF, F.NAN, 0, 0, 1, -1, 3, -7, 1 << 20, -(1 << 33)]
    n = 0
    for text in texts:
        tree = EX.parse(text)
        names = sorted(set(EX.names(tree)))
        for q in (-1074, -10, 3):
            for _ in range(ctx.n(400, 100)):
                env = {nm: rnd.choice(vals) for nm in names}
                v, s = XT.ext_eval(tree, lambda nm: (env[nm], q))
                want = _ref_eval(tree, {nm: _float_of(env[nm], q) for nm in names})
                got = Q(v) * Q(2) ** s if type(v) is int else v
                expect(_same(got, want), "%s at %r: %r, want %r" % (text, env, got, want))
                if all(type(x) is int for x in env.values()):
                    src, sc = EX.compile_tree(tree, lambda nm: ("v[%d]" % names.index(nm), q))
                    fn = EX.make_function(["v"], src)
                    expect(sc == s and fn([env[nm] for nm in names]) == v, "%s: scales" % text)
                n += 1
    # Comparisons in the extended reals, against floats.
    for _ in range(ctx.n(4000, 1000)):
        a, b = rnd.choice(vals), rnd.choice(vals)
        d = XT.x_cmp(a, 0, b, 0)
        fa, fb = _float_of(a, 0), _float_of(b, 0)
        want = None if (isinstance(fa, float) and math.isnan(fa)) or (
            isinstance(fb, float) and math.isnan(fb)) else (fa > fb) - (fa < fb)
        expect(d == want, "x_cmp(%r, %r) = %r" % (a, b, d))
    # canonical() and ball states by definition, on every pair of limbs of fp:2:-2:1.
    p, qmin, qmax = 2, -2, 1
    f = F.Format(p, qmin, qmax)
    br = BruteRN(p, qmin, qmax)
    eta = Q(2) ** qmin
    limbs = F.all_values(f) + [F.POS_INF, F.NEG_INF, F.NAN]
    m = 0
    for a in limbs:
        for b in limbs:
            fin = type(a) is int and type(b) is int
            normal = fin and br(Q(a + b) * eta) == Q(a) * eta
            want = normal or (a in (F.POS_INF, F.NEG_INF) and b == 0) or (a == b == F.NAN)
            expect(XT.canonical(f, [a, b]) == want, "canonical(%r, %r)" % (a, b))
            st = XT.ball_state(f, [a], b)
            wst = ("finite" if fin and b >= 0 else "whole" if a == 0 and b == F.POS_INF else
                   "empty" if a == b == F.NAN else None)
            expect(st == wst, "ball_state(%r, %r) = %r, want %r" % (a, b, st, wst))
            for c in limbs:
                st = XT.ball_state(f, [a, b], c)
                wst = ("finite" if normal and type(c) is int and c >= 0 else
                       "whole" if a == 0 and b == 0 and c == F.POS_INF else
                       "empty" if a == b == c == F.NAN else None)
                expect(st == wst, "ball_state(%r, %r, %r) = %r" % (a, b, c, st))
                m += 1
    return "%d evaluations, %d canonical and ball tests" % (n, m)


def _class_checks(s, fname):
    """The classes every random stream of the layer must reach."""
    for k in FULL:
        c = counts(s, k)
        for cl in ("class F2", "class F4", "class F5"):
            expect(sum(v for key, v in c.items() if key.startswith(cl)) > 0,
                   "%s %s: no case of %s (%s)" % (k, fname, cl, c))
    for k in ("add_2_2_full", "mul_2_2_full"):
        th = counts(s, k, "threshold")
        total = sum(v for key, v in th.items() if key.startswith("class"))
        inside = th.get("F3 applies: finite operands, every finite_when condition holds", 0)
        expect(total and 0.5 <= inside / total < 1, "%s %s: threshold stratum inside %d of %d"
               % (k, fname, inside, total))
    for k in BALLF:
        c = counts(s, k)
        for key in ("result: finite ball", "result: whole line", "result: empty set",
                    "whole line on finite operands"):
            expect(c.get(key, 0) > 0, "%s %s: no %s (%s)" % (k, fname, key, c))
    for k in BALLNEG:
        c = counts(s, k)
        for key in ("result: finite ball", "result: whole line", "result: empty set"):
            expect(c.get(key, 0) > 0, "%s %s: no %s (%s)" % (k, fname, key, c))
    for k in ("ball_make_1", "ball_make_2"):
        c = counts(s, k)
        for key in ("given: empty set", "given: whole line", "given: finite ball"):
            expect(c.get(key, 0) > 0, "%s %s: no %s" % (k, fname, key))
    for k in ("make_2", "make_2_limbs"):
        c = counts(s, k)
        for key in ("value NaN", "value infinite", "value finite"):
            expect(c.get(key, 0) > 0, "%s %s: no %s" % (k, fname, key))
    for k in GAINED:
        c = counts(s, k)
        if k.startswith(("lt", "le", "eq")):
            for key in ("a non-finite operand, true", "a non-finite operand, false"):
                expect(c.get(key, 0) > 0, "%s %s: no %s (%s)" % (k, fname, key, c))
        elif k in ("radd", "rmul"):
            expect(c.get("value NaN (a NaN operand, or 0 * inf)", 0) > 0, "%s %s: no NaN value"
                   % (k, fname))
        else:
            expect(c.get("a non-finite operand", 0) > 0, "%s %s: no non-finite operand"
                   % (k, fname))


@test
def gen_wave3(ctx):
    """Every generated case of every kernel of the layer and every stratum satisfies the
    requirements; the correct runner passes, with nothing suspicious; every stratum and every
    class of every statement occurs; the threshold stratum is mostly inside the finite_when
    conditions; case i alone equals case i of a run."""
    cl = claims3(ctx)
    n = 0
    for fname in FORMATS3:
        lines = []
        for k in EXTENDED:
            lines += stream3(ctx, k, fname, ctx.n(1500, 500))
        s = judge(run3(lines), cl, ignore_min_precision=True)
        t = totals(s)
        expect(t["invalid"] == 0, "%s: %d invalid generated cases: %s" % (
            fname, t["invalid"], failures(s, kind="invalid")[:2]))
        expect(t["failed"] == 0 and not s.stream_errors and t["suspicious"] == 0,
               "%s: correct runner flagged: %s %s" % (fname, failures(s)[:2],
                                                      failures(s, kind="suspicious")[:1]))
        for k in EXTENDED:
            known = G.RandomGen(cl.get(k), F.parse_format(fname), "x").strata
            tags = {key[2] for key in s.keys if key[0] == k}
            expect(tags == set(known), "%s %s: strata %s, want %s" % (k, fname, sorted(tags),
                                                                      sorted(known)))
        _class_checks(s, fname)
        n += t["cases"]
    rnd = random.Random(8)
    for k in ("add_2_2_full", "mul_2_2_full", "mul_pow2_2_full", "ball_mul_2_full",
              "ball_scale_1_full", "ball_make_1", "lt_1_2", "rmul"):
        g = G.RandomGen(cl.get(k), F.parse_format("binary64"), "cb")
        run = list(g.lines(40, 160))[1:-1]
        for _ in range(6):
            i = rnd.randrange(40, 200)
            alone = list(G.RandomGen(cl.get(k), F.parse_format("binary64"), "cb").lines(i, 1))[1]
            expect(alone == run[i - 40], "case %d of %s" % (i, k))
        other = list(G.RandomGen(cl.get(k), F.parse_format("binary64"), "cb2").lines(40, 160))
        expect(sum(a != b for a, b in zip(run, other[1:-1])) > 100, "%s: seed has no effect" % k)
    return "%d cases in %d formats" % (n, len(FORMATS3))


@test
def exhaustive_wave3(ctx):
    """The domains of the layer, non-finite values included, against brute-force counts; and the
    correct runner on every case of tiny formats (of the IEEE shape qmin + qmax = 3 - 2p and
    others) for every kernel of the layer, the 2-limb balls on restricted radii."""
    cl = claims3(ctx)
    p, qmin, qmax = 3, -3, 2
    f = F.Format(p, qmin, qmax)
    br = BruteRN(p, qmin, qmax)
    vals = br.vals
    eta = Q(2) ** qmin
    pairs = len({(a, b) for a in vals for b in vals if br(a + b) == a and (a != 0 or b == 0)})
    nv, nn = len(vals), sum(1 for v in vals if v >= 0)
    pow2 = sum(1 for v in vals if v > 0 and (int(v / eta) & (int(v / eta) - 1)) == 0)
    one, two, nonneg = nv + 3, pairs + 3, nn + 2              # with their non-finite values
    want = {"make_2": one, "make_2_limbs": two, "ball_make_1": one * one, "ball_make_2": two * one,
            "radd": nonneg * nonneg, "mul_pow2_2_full": two * pow2, "add_2_2_full": two * two,
            "add_2_1_full": two * one, "sub_1_2_full": one * two,
            "ball_add_1_full": (nv * nn + 2) ** 2, "ball_scale_1_full": (nv * nn + 2) * one,
            "ball_scale_2_full": (pairs * nn + 2) * one, "lt_2_2": two * two, "neg_2": two}
    for k, w in want.items():
        g = G.ExhaustiveGen(cl.get(k), f)
        expect(g.total == w, "%s total %d, want %d" % (k, g.total, w))
    # Restrictions shrink the finite part of a domain; the non-finite values stay.
    g = G.ExhaustiveGen(cl.get("ball_add_1_full"), f, ["rx.in=0x0p+0/0x1p-1", "cx.lead=0:0"])
    infin = sum(1 for v in vals if 1 <= abs(v) < 2)
    expect(g.total == (infin * 2 + 2) * (nv * nn + 2), "restricted ball total %d" % g.total)
    g = G.ExhaustiveGen(cl.get("make_2"), f, ["a.sign=+"])
    expect(g.total == nn + 3, "restricted make_2 total %d" % g.total)
    lines = list(g.lines(0, g.total))[1:-1]
    expect({ln.split()[2] for ln in lines} >= {"inf", "-inf", "nan"}, "non-finite values dropped")
    g = G.ExhaustiveGen(cl.get("ball_make_2"), F.parse_format("fp:2:-2:1"))
    full = list(g.lines(0, g.total))
    expect(len(set(full)) == g.total + 2 and list(g.lines(57, 1))[1] == full[58],
           "exhaustive lines not unique or case 57 not reproducible")
    # The correct runner on every case.
    plan = [("fp:3:-4:1", k, ()) for k in FULL if k not in FULL22]
    plan += [("fp:2:-2:1", "ball_neg_1", ()), ("fp:3:-3:0", "ball_neg_2", ())]
    plan += [("fp:3:-4:1", k, ()) for k in ONE_OPS]
    plan += [("fp:3:-3:0", k, ()) for k in FULL22 if k != "mul_2_2_full"]
    plan += [("fp:4:-4:-1", "mul_2_2_full", ())]
    plan += [("fp:3:-4:1", k, ()) for k in MAKE + GAINED if k not in ("lt_2_2", "le_2_2", "eq_2_2")]
    plan += [("fp:3:-3:0", k, ()) for k in ("lt_2_2", "le_2_2", "eq_2_2")]
    plan += [("fp:2:-2:1", k, ()) for k in ("ball_add_1_full", "ball_sub_1_full", "ball_mul_1_full",
                                            "ball_scale_1_full", "ball_scale_2_full")]
    radii = "0x0p+0/0x1p-3/0x1p-1/0x1.cp+0"
    plan += [("fp:3:-3:0", k, ("rx.in=" + radii, "ry.in=" + radii, "cx.lead=-1:-1"))
             for k in ("ball_add_2_full", "ball_sub_2_full")]
    plan += [("fp:4:-4:-1", "ball_mul_2_full", ("rx.in=0x0p+0/0x1p-4/0x1.ep-1",
                                                "ry.in=0x0p+0/0x1p-4/0x1.ep-1", "cx.lead=-2:-2",
                                                "cy.lead=-1:-1"))]
    if not ctx.quick:
        plan += [("fp:3:-4:1", k, ()) for k in FULL22 if k != "mul_2_2_full"]
        plan += [("fp:3:-3:2", k, ()) for k in FULL if k not in FULL22]
        plan += [("fp:3:-3:0", k, ()) for k in ("ball_add_1_full", "ball_mul_1_full",
                                                "ball_scale_1_full")]
    out = []
    for fname, k, restrict in plan:
        s = exhaustive3(ctx, k, fname, restrict)
        t = totals(s)
        expect(t["failed"] == 0 and not s.stream_errors and t["invalid"] == 0
               and t["suspicious"] == 0 and t["out_of_scope"] == 0,
               "correct runner flagged on %s %s: %r %s" % (k, fname, t, failures(s)[:2]))
        # Every line of a kernel of the extended domain is judged; a finite kernel's overflows
        # are not.
        expect(t["judged"] == t["cases"] > 0 if cl.get(k).extended else t["judged"] > 0,
               "not every case judged for %s %s" % (k, fname))
        cov = s.coverage.describe()
        expect(cov and ("COMPLETE" in cov[0]) == (not restrict), "coverage of %s: %s" % (k, cov))
        out.append(t["cases"])
    return "%d enumerations, %d cases" % (len(out), sum(out))


@test
def cxx_wave3(ctx):
    """The C++ runner (hardware) passes on every kernel of the layer, and its results equal the
    Python runner's on every case (signs of zero aside)."""
    n = 0
    cl = claims3(ctx)
    for fname in ("binary64", "binary32"):
        lines = []
        for k in EXTENDED:
            lines += stream3(ctx, k, fname, ctx.n(1500, 500))
        hw = cxx_run(ctx, lines, radius=RADIUS)
        py = run3(lines)
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
        s = judge(hw, cl)
        expect(totals(s)["failed"] == 0 and not s.stream_errors and totals(s)["suspicious"] == 0,
               "C++ correct runner flagged on %s: %s" % (fname, failures(s)[:2]))
    return "%d cases identical" % n


# The planted bugs: (variant, kernels it must be caught in, statements whose failures are
# required there, statements whose failures are allowed there, kernels that must stay clean).
# The statements are the count keys "failed F1" ... "failed B4" of extends and encloses, and the
# "failed: ..." keys of represents and makes_ball.
# Kernels of the other families, which a planted bug must leave alone.
REST = ("ball_mul_2_full", "ball_scale_1_full", "ball_make_2", "make_2", "neg_2", "radd")
NOT_BALL = ("add_2_2_full", "mul_2_1_full", "make_2", "ball_make_1", "ball_neg_2")
NOT_MAKE = ("add_2_1_full", "ball_add_2_full", "ball_scale_2_full")
INJECTED3 = (
    ("full-no-fixup", FULL, ("F4", "F5"), ("F1", "F2", "F4", "F5"), REST),
    ("full-overflow-sign", FULL, ("F4",), ("F4",), REST),
    ("full-overflow-nan", FULL, ("F4",), ("F4",), REST),
    ("full-overflow-finite", FULL, ("F2",), ("F2",), REST),
    ("full-spurious-overflow", ("add_2_2_full", "mul_2_2_full"), ("F3",), ("F3",),
     tuple(k for k in FULL if k not in ("add_2_2_full", "mul_2_2_full"))),
    ("full-inf-tail-nan", FULL, ("F1",), ("F1", "F4", "F5"), REST),
    ("full-inf-tail-eta", FULL, ("F1",), ("F1", "F4", "F5"), REST),
    ("full-nan-one-limb", FULL, ("F1",), ("F1", "F5"), REST),
    ("full-nan-to-zero", FULL, ("F2", "F5"), ("F2", "F5"), REST),
    ("ball-full-swap", BALLF, ("B2",), ("B2",), NOT_BALL),
    ("ball-full-zero-inf-empty", ("ball_mul_1_full", "ball_mul_2_full", "ball_scale_1_full",
                                  "ball_scale_2_full"), ("B2",), ("B2",), NOT_BALL),
    ("ball-full-finite-whole", BALLF, ("B3",), ("B3",), NOT_BALL),
    # The second radius design: without E the center's error is not covered; without H what
    # underflow loses is not, which the products and scalings need (the sums may not).
    # (Required in the one-limb kernels: at p = 4, G rounded up to 1.25 has room for the small
    # error of a 2-limb center, which binary64 and binary32 streams still show.)
    ("ball2-no-E", ("ball_add_1_full", "ball_sub_1_full", "ball_mul_1_full",
                    "ball_scale_1_full"), ("B3",), ("B3",), NOT_BALL),
    ("ball2-no-H", ("ball_mul_1_full", "ball_mul_2_full", "ball_scale_1_full",
                    "ball_scale_2_full"), ("B3",), ("B3",), NOT_BALL),
    ("make-negative-radius", ("ball_make_1", "ball_make_2"), (": not canonical",),
     (": not canonical", ": whole line instead of empty set"),
     ("make_2", "make_2_limbs") + NOT_MAKE),
    ("make-nan-radius", ("ball_make_1", "ball_make_2"), (": whole line instead of empty set",),
     (": not canonical", ": whole line instead of empty set"),
     ("make_2", "make_2_limbs") + NOT_MAKE),
    ("make2-inf-nan-tail", ("make_2",), (": not canonical",), (": not canonical",),
     ("make_2_limbs", "ball_make_1", "ball_make_2") + NOT_MAKE),
)


def _key(st):
    """The count key of a statement's failures: "failed F4", or "failed: not canonical"."""
    return "failed" + (st if st.startswith(":") else " " + st)


def _check_injected(s, variant, flagged, need, allowed, clean, label):
    for k in flagged:
        c = counts(s, k, prefix="failed")
        for st in need:
            expect(c.get(_key(st), 0) > 0,
                   "%s %s: %s not caught in %s (%s)" % (label, variant, k, st, c))
        extra = set(c) - {_key(a) for a in allowed}
        expect(not extra, "%s %s: %s caught in other statements %s" % (label, variant, k, extra))
    for k in clean:
        expect(totals(s, k)["failed"] == 0, "%s %s: %s flagged although it does not use the "
               "error: %s" % (label, variant, k, failures(s, (k,))[:1]))


def _injected3(ctx, run, fname, label):
    res = []
    for variant, flagged, need, allowed, clean in INJECTED3:
        lines = []
        for k in flagged + clean:
            lines += stream3(ctx, k, fname, ctx.n(1500, 300))
        s = judge(run(lines, variant), claims3(ctx))
        _check_injected(s, variant, flagged, need, allowed, clean, label)
        if variant == "full-spurious-overflow":
            # Where no condition is claimed the overflow is not a failure; on small operands it
            # is shown as suspicious, which the cross-checks fail on.
            sus = sum(totals(s, k)["suspicious"] for k in clean if k in FULL)
            expect(sus > 0, "%s %s: no suspicious case where no condition is claimed"
                   % (label, variant))
        res.append("%s %d" % (variant, totals(s)["failed"]))
    return res


@test
def injected_wave3(ctx):
    """The planted bugs of the layer in the Python runner (a toy format of the IEEE shape,
    binary64) and the C++ runner (binary64, binary32): each caught in the statement where it
    belongs, in no other, and in no kernel that does not use it."""
    res = []
    for fname in ("fp:4:-6:1", "binary64"):
        res += _injected3(ctx, run3, fname, "python %s" % fname)
    try:
        build_cxx(ctx)
        for fname in ("binary64", "binary32"):
            res += _injected3(ctx, lambda lines, v: cxx_run(ctx, lines, v, RADIUS), fname,
                              "C++ " + fname)
    except Skip as ex:
        res.append("C++ skipped: %s" % ex)
    return "; ".join(res)


@test
def injected_wave3_exhaustive(ctx):
    """The planted bugs on every case of tiny formats of the IEEE shape: caught where they
    belong and nowhere else."""
    res = []
    small = {"full": ("add_2_1_full", "sub_1_2_full", "mul_2_1_full", "mul_pow2_2_full"),
             "ball": ("ball_add_1_full", "ball_mul_1_full", "ball_scale_1_full"),
             "make": ("make_2", "ball_make_1", "ball_make_2")}
    for variant, flagged, need, allowed, _clean in INJECTED3:
        fam = "make" if variant.startswith("make") else variant.split("-")[0].rstrip("2")
        ks = [k for k in flagged if k in small.get(fam, ())]
        if variant == "full-spurious-overflow":
            ks = ["add_2_2_full"]
        for k in ks if not ctx.quick else ks[:1]:
            fname = "fp:3:-3:0" if k == "add_2_2_full" else "fp:2:-2:1" if k.startswith(
                "ball_") and "scale" not in k else "fp:3:-4:1"
            s = exhaustive3(ctx, k, fname, (), variant)
            _check_injected(s, variant, (k,), need, allowed, (), "exhaustive " + fname)
        res.append("%s (%s)" % (variant, ", ".join(ks if not ctx.quick else ks[:1])))
    return "; ".join(res)


@test
def radius_second(ctx):
    """The constants of the second radius design against values worked out by hand from
    milestone1.md's table; both radius designs pass on the same streams of the full Ball kernels;
    the C++ runner's second design equals the Python one's."""
    eta64 = Q(2) ** -1074
    u64 = Q(1, 2 ** 53)

    def consts(fname, kname):
        ar = refrun.Arith(F.parse_format(fname).triple)
        eta = Q(2) ** ar.qmin
        return tuple(Q(v) * eta if type(v) is int else v
                     for v in refrun.radius2_constants(ar, kname))

    hand = {
        # U_q = u exactly (rel = u/(1+u)); (1+u)^3 = 1+3u+... rounds up to 1+4u; H = 1.5 eta+.
        ("binary64", "ball_add_1"): (u64, 1 + 4 * u64, 2 * eta64),
        # (1+u)^6 rounds up to 1+8u; 4u^2/(1-4u^2) just above 2^-104; H just above 4 eta.
        ("binary64", "ball_mul_2"): (Q(2) ** -104 * (1 + 2 * u64), 1 + 8 * u64, 5 * eta64),
        # (1+u)^5 rounds up to 1+6u; H = (1+u)(2(1+u)^4 + (1+u)/2 + 1/2) eta, just above 3.
        ("binary64", "ball_mul_1"): (u64, 1 + 6 * u64, 4 * eta64),
        # u = 1/8: U_q = 1/8; (9/8)^3 = 1.42 rounds up to 1.5; H = 1.99 eta rounds to 2 eta.
        ("fp:3:-4:1", "ball_add_1"): (Q(1, 8), Q(3, 2), Q(1, 8)),
        # rel = 2u^2 = 1/32, U_q (1+u) = 9/248 is below eta = 1/16.
        ("fp:3:-4:1", "ball_scale_2"): (Q(1, 16), Q(3, 2), Q(1, 4)),
        # (9/8)^6 = 2.03 rounds up to 2.5 (spacing 1/2 in [2, 4)).
        ("fp:3:-4:1", "ball_mul_2"): (Q(1, 8), Q(5, 2), Q(7, 16)),
    }
    for (fname, kname), want in hand.items():
        got = consts(fname, kname)
        expect(got == want, "%s %s: E, G, H = %s, want %s" % (fname, kname, got, want))
    # ball_sub_k takes the constants of ball_add_k.
    expect(consts("binary32", "ball_sub_2") == consts("binary32", "ball_add_2"), "sub constants")
    n = 0
    cl = claims3(ctx)
    for fname in ("binary64", "fp:4:-6:1"):
        lines = []
        for k in BALLF:
            lines += stream3(ctx, k, fname, ctx.n(1200, 300))
        for radius in refrun.RADIUS_DESIGNS:
            s = judge(run3(lines, radius=radius), cl, ignore_min_precision=True)
            t = totals(s)
            expect(t["failed"] == 0 and t["invalid"] == 0, "%s radius %s: %s" % (
                fname, radius, failures(s)[:2]))
            n += t["cases"]
    return "constants of %d kernels by hand; %d cases" % (len(hand), n)


# Precision-1 formats: numbers are zero and the powers of two.
P1_FORMATS = [(1, -3, 2), (1, 0, 4), (1, -5, -1)]


def rn_definition(br, p, qmin, t):
    """RN(t) by the definition the proofs use (Flocq's round to nearest, ties to even): the
    nearest number, and on a tie the one whose integer significand at the exponent of t,
    max(e + 1 - p, qmin) with 2^e <= |t| < 2^(e+1), is even; beyond Omega the infinity.  At
    p = 1 both neighbours of a tie have the significand 1, so 'even significand' alone cannot
    decide, and this is what does (BruteRN assumes p >= 2)."""
    if t <= -br.big or t >= br.big:
        return -math.inf if t < 0 else math.inf
    i = bisect_left(br.ext, t)
    if br.ext[i] == t:
        r = t
    else:
        lo, hi = br.ext[i - 1], br.ext[i]
        if t - lo != hi - t:
            r = lo if t - lo < hi - t else hi
        else:
            e, a = 0, abs(t)
            while a >= 2:
                a /= 2
                e += 1
            while a < 1:
                a *= 2
                e -= 1
            scale = Q(2) ** max(e + 1 - p, qmin)
            m = t / scale
            fl = m.numerator // m.denominator
            r = (fl if fl % 2 == 0 else fl + 1) * scale
    if abs(r) >= br.big:
        return math.inf if r > 0 else -math.inf
    return r


@test
def precision_one(ctx):
    """Formats of precision 1: rounding (ties included), directed rounding, neighbors, membership
    and normalized pairs against brute force; every kernel proved from precision 1 generated,
    run and judged at random and on every operand; precision 0 refused."""
    from .selftest2 import _unbounded_values
    import bisect
    pts = 0
    for p, qmin, qmax in P1_FORMATS:
        f = F.Format(p, qmin, qmax)
        ar = refrun.Arith((p, qmin, qmax))
        br = BruteRN(p, qmin, qmax)
        eta = Q(2) ** qmin
        expect([Q(v) * eta for v in F.all_values(f)] == br.vals, "all_values %s" % f.name)
        step = eta / 8
        for j in range(-int((br.big + 4 * eta) / step), int((br.big + 4 * eta) / step) + 1):
            r = rn_definition(br, p, qmin, j * step)
            want = r if isinstance(r, float) else int(r / eta)
            got = F.rn(f, j, qmin - 3)
            got = got if type(got) is int else (math.inf if got == F.POS_INF else -math.inf)
            expect(got == want and ar.round(j, 3) == want,
                   "RN(%s) = %r / %r, want %r in %s" % (j * step, got, ar.round(j, 3), want, f.name))
            pts += 1
        ext = _unbounded_values(p, qmin, qmax)
        top = Q(2) ** (qmax + p)
        for j in range(-int(top / step), int(top / step) + 1):
            t = j * step
            i = bisect.bisect_right(ext, t)
            down = ext[i - 1]
            up = down if down == t else ext[i]
            expect(Q(F.rdir(f, j, qmin - 3, False)) * eta == down and
                   Q(F.rdir(f, j, qmin - 3, True)) * eta == up, "RD/RU(%s) in %s" % (t, f.name))
        vals = F.all_values(f)
        for i, v in enumerate(vals):
            nxt = vals[i + 1] if i + 1 < len(vals) else F.POS_INF
            prv = vals[i - 1] if i > 0 else F.NEG_INF
            expect(F.succ(f, v) == nxt and F.pred(f, v) == prv, "succ/pred(%d) in %s" % (v, f.name))
            expect(ar.next_up(v) == (nxt if type(nxt) is int else math.inf),
                   "runner next_up(%d) in %s" % (v, f.name))
        pairs = sorted({(a, b) for a in br.vals for b in br.vals
                        if rn_definition(br, p, qmin, a + b) == a and (a != 0 or b == 0)})
        gp = sorted((Q(a) * eta, Q(b) * eta) for a, b in G.normalized_pairs(f))
        expect(gp == pairs, "normalized pairs of %s: %d, want %d" % (f.name, len(gp), len(pairs)))
    try:
        F.Format(0, -3, 2)
        raise AssertionError("precision 0 accepted")
    except F.FormatError:
        pass
    cl = claims3(ctx)
    # Below a kernel's minimum precision its bound need not exist (3/(1 - 4u) is negative at
    # p = 1): the line is out of scope, and the kernel stays readable for the other formats.
    s = judge(["add_2_2 fp:1:-3:2 0x1p+0 0x0p+0 0x1p+0 0x0p+0 -> 0x1p+1 0x0p+0",
               "add_2_2 binary64 0x1p+0 0x0p+0 0x1p+0 0x0p+0 -> 0x1p+1 0x0p+0"], cl)
    t = totals(s)
    expect(t["out_of_scope"] == 1 and t["passed"] == 1 and not s.claims_errors,
           "a format below min_precision set the kernel aside: %r %s" % (t, s.claims_errors))
    n = 0
    for k in PRECISION_ONE:
        expect(cl.get(k).min_precision == 1, "%s: min_precision %s" % (k, cl.get(k).min_precision))
        for fname in ("fp:1:-6:3", "fp:1:-3:0"):
            s = judge(run3(stream3(ctx, k, fname, ctx.n(600, 200))), cl)
            t = totals(s)
            # A finite kernel (add_1_1, mul_1_1) does not judge its overflows.
            expect(t["invalid"] == 0 and t["failed"] == 0 and t["suspicious"] == 0
                   and t["judged"] + t["nonfinite"] == t["cases"] and t["judged"] > 0,
                   "%s %s: %r %s" % (k, fname, t, failures(s)[:2]))
            n += t["cases"]
        s = exhaustive3(ctx, k, "fp:1:-3:2")
        t = totals(s)
        expect(t["failed"] == 0 and t["invalid"] == 0 and t["suspicious"] == 0
               and t["judged"] + t["nonfinite"] == t["cases"] and t["judged"] > 0,
               "%s fp:1:-3:2 exhaustive: %r %s" % (k, t, failures(s)[:2]))
        n += t["cases"]
    return "%d rounding points; %d kernels, %d cases" % (pts, len(PRECISION_ONE), n)


# Hand-written lines and their verdicts: passed, failed (with the statement that must fail),
# invalid, suspicious (passed, and shown).
OM = "0x1.fffffffffffffp+1023"
HAND3 = [
    # extends, add_2_2_full: F1 to F5.
    ("add_2_2_full binary64 0x1p+0 0x0p+0 0x1p+1 0x0p+0 -> 0x1.8p+1 0x0p+0", "passed"),
    ("add_2_2_full binary64 0x1p+0 0x0p+0 0x1p+1 0x0p+0 -> 0x1.8p+1 0x1p-60", "F2"),
    ("add_2_2_full binary64 0x1p+0 0x0p+0 0x1p+1 0x0p+0 -> 0x1.8p+1 nan", "F1"),
    ("add_2_2_full binary64 inf 0x0p+0 0x1p+1 0x0p+0 -> inf 0x0p+0", "passed"),
    ("add_2_2_full binary64 inf 0x0p+0 0x1p+1 0x0p+0 -> inf -0x0p+0", "passed"),
    ("add_2_2_full binary64 inf -0x0p+0 -0x1p+1 0x0p+0 -> inf 0x0p+0", "passed"),
    ("add_2_2_full binary64 inf 0x0p+0 0x1p+1 0x0p+0 -> inf nan", "F1"),
    ("add_2_2_full binary64 inf 0x0p+0 0x1p+1 0x0p+0 -> inf 0x1p-1074", "F1"),
    ("add_2_2_full binary64 inf 0x0p+0 0x1p+1 0x0p+0 -> nan nan", "F5"),
    ("add_2_2_full binary64 inf 0x0p+0 0x1p+1 0x0p+0 -> -inf 0x0p+0", "F5"),
    ("add_2_2_full binary64 inf 0x0p+0 -inf 0x0p+0 -> nan nan", "passed"),
    ("add_2_2_full binary64 inf 0x0p+0 -inf 0x0p+0 -> nan 0x0p+0", "F1"),
    ("add_2_2_full binary64 nan nan 0x1p+0 0x0p+0 -> nan nan", "passed"),
    ("add_2_2_full binary64 nan nan 0x1p+0 0x0p+0 -> 0x1p+0 0x0p+0", "F2"),
    ("add_2_2_full binary64 nan nan 0x1p+0 0x0p+0 -> 0x1p+0 0x0p+0", "F5"),
    # The core overflows on finite operands: (inf, 0) with the sign of the exact value.
    ("add_2_2_full binary64 %s 0x0p+0 %s 0x0p+0 -> inf 0x0p+0" % (OM, OM), "passed"),
    ("add_2_2_full binary64 -%s 0x0p+0 -%s 0x0p+0 -> -inf -0x0p+0" % (OM, OM), "passed"),
    ("add_2_2_full binary64 %s 0x0p+0 %s 0x0p+0 -> -inf 0x0p+0" % (OM, OM), "F4"),
    ("add_2_2_full binary64 %s 0x0p+0 %s 0x0p+0 -> nan nan" % (OM, OM), "F4"),
    ("add_2_2_full binary64 %s 0x0p+0 %s 0x0p+0 -> inf 0x1p+0" % (OM, OM), "F4"),
    ("add_2_2_full binary64 %s 0x0p+0 %s 0x0p+0 -> %s 0x0p+0" % (OM, OM, OM), "F2"),
    # F3: |x| = |y| = 2^1022 = 2^(qmax+p-2) is inside the condition, 2^1022 + 2^968 is not.
    ("add_2_2_full binary64 0x1p+1022 0x0p+0 0x1p+1022 0x0p+0 -> inf 0x0p+0", "F3"),
    ("add_2_2_full binary64 0x1p+1022 0x1p+968 0x1p+1022 0x0p+0 -> inf 0x0p+0", "passed"),
    ("add_2_2_full binary64 0x1p+1022 0x0p+0 0x1p+1022 0x0p+0 -> 0x1p+1023 0x0p+0", "passed"),
    # Requirements: canonical operands only.
    ("add_2_2_full binary64 inf 0x1p+0 0x1p+0 0x0p+0 -> inf 0x0p+0", "invalid"),
    ("add_2_2_full binary64 nan 0x0p+0 0x1p+0 0x0p+0 -> nan nan", "invalid"),
    ("add_2_2_full binary64 0x1p+0 nan 0x1p+0 0x0p+0 -> nan nan", "invalid"),
    ("add_2_2_full binary64 0x1p+0 0x1p+0 0x1p+0 0x0p+0 -> 0x1.8p+1 0x0p+0", "invalid"),
    ("add_2_2_full binary64 0x1p+0 0x0p+0 0x1p+0 -> 0x1p+1 0x0p+0", "failed"),
    # The other leads: inf - inf and 0 * inf are NaN, a sign times an infinity its sign.
    ("sub_1_2_full binary64 inf inf 0x0p+0 -> nan nan", "passed"),
    ("sub_1_2_full binary64 -inf 0x1p+0 0x0p+0 -> -inf 0x0p+0", "passed"),
    ("sub_1_2_full binary64 -inf 0x1p+0 0x0p+0 -> inf 0x0p+0", "F5"),
    ("sub_1_2_full binary64 0x1p+0 -inf 0x0p+0 -> inf 0x0p+0", "passed"),
    ("mul_2_1_full binary64 0x0p+0 0x0p+0 inf -> nan nan", "passed"),
    ("mul_2_1_full binary64 -0x0p+0 0x0p+0 -inf -> nan nan", "passed"),
    ("mul_2_1_full binary64 0x0p+0 0x0p+0 inf -> inf 0x0p+0", "F5"),
    ("mul_2_1_full binary64 -0x1p-1074 0x0p+0 inf -> -inf 0x0p+0", "passed"),
    ("mul_2_2_full binary64 -0x1p+0 0x0p+0 -inf 0x0p+0 -> inf 0x0p+0", "passed"),
    # mul_2_2_full: |x y| = 2^1022 <= 2^(qmax+p-1) is inside, 2^1024 is not.
    ("mul_2_2_full binary64 0x1p+511 0x0p+0 0x1p+511 0x0p+0 -> inf 0x0p+0", "F3"),
    ("mul_2_2_full binary64 0x1p+512 0x0p+0 0x1p+512 0x0p+0 -> inf 0x0p+0", "passed"),
    ("mul_2_2_full binary64 0x1p+512 0x0p+0 -0x1p+512 0x0p+0 -> inf 0x0p+0", "F4"),
    ("mul_pow2_2_full binary64 0x1p+1023 0x0p+0 0x1p+1 -> inf 0x0p+0", "passed"),
    ("mul_pow2_2_full binary64 0x1p+1023 0x0p+0 0x1p+1 -> 0x1p+1023 0x0p+0", "F2"),
    ("mul_pow2_2_full binary64 inf 0x0p+0 0x1p-1074 -> inf 0x0p+0", "passed"),
    ("mul_pow2_2_full binary64 0x1p+0 0x0p+0 inf -> inf 0x0p+0", "invalid"),
    # A toy format: Omega = 14, and 14 + 1 is a tie that rounds to 16, beyond Omega.
    ("add_2_1_full fp:3:-4:1 0x1.cp+3 0x0p+0 0x1p+0 -> inf 0x0p+0", "passed"),
    ("add_2_1_full fp:3:-4:1 0x1.cp+3 0x0p+0 0x1p+0 -> 0x1.cp+3 0x0p+0", "F2"),
    ("add_2_1_full fp:3:-4:1 0x1.cp+3 0x0p+0 0x1p-1 -> 0x1.cp+3 0x1p-1", "passed"),
    ("add_2_1_full fp:3:-4:1 0x1.cp+3 0x0p+0 0x1p-1 -> inf 0x0p+0", "passed"),
    # encloses: B1 to B4 with the set semantics of the page.
    ("ball_mul_1_full binary64 0x0p+0 0x0p+0 0x0p+0 inf -> 0x0p+0 inf", "passed"),
    ("ball_mul_1_full binary64 0x0p+0 0x0p+0 -0x0p+0 inf -> -0x0p+0 inf", "passed"),
    ("ball_mul_1_full binary64 0x0p+0 0x0p+0 0x0p+0 inf -> nan nan", "B2"),
    ("ball_mul_1_full binary64 0x0p+0 0x0p+0 0x0p+0 inf -> 0x0p+0 0x0p+0", "B3"),
    ("ball_mul_1_full binary64 nan nan 0x1p+0 0x0p+0 -> nan nan", "passed"),
    ("ball_mul_1_full binary64 nan nan 0x0p+0 inf -> nan nan", "passed"),
    ("ball_mul_1_full binary64 nan nan 0x1p+0 0x0p+0 -> 0x0p+0 inf", "B2"),
    ("ball_add_1_full binary64 0x1p+0 0x1p-1 0x1p+1 0x0p+0 -> 0x1.8p+1 0x1p-1", "passed"),
    ("ball_add_1_full binary64 0x1p+0 0x1p-1 0x1p+1 0x0p+0 -> 0x1.8p+1 0x1.fffffffffffffp-2",
     "B3"),
    ("ball_add_1_full binary64 0x1p+0 0x1p-1 0x1p+1 0x0p+0 -> 0x0p+0 inf", "passed"),
    ("ball_add_1_full binary64 0x1p+0 0x1p-1 0x1p+1 0x0p+0 -> 0x1p+0 inf", "B1"),
    ("ball_add_1_full binary64 0x1p+0 0x1p-1 0x1p+1 0x0p+0 -> 0x1p+0 -0x1p+0", "B1"),
    ("ball_add_1_full binary64 0x1p+0 0x1p-1 0x1p+1 0x0p+0 -> nan 0x1p+0", "B1"),
    ("ball_add_1_full binary64 0x0p+0 inf nan nan -> nan nan", "passed"),
    ("ball_add_1_full binary64 0x1p+0 -0x1p+0 0x1p+0 0x0p+0 -> 0x1p+1 0x1p+0", "invalid"),
    ("ball_add_1_full binary64 0x1p+0 inf 0x1p+0 0x0p+0 -> 0x0p+0 inf", "invalid"),
    ("ball_add_1_full binary64 0x1p+0 nan 0x1p+0 0x0p+0 -> nan nan", "invalid"),
    ("ball_add_2_full binary64 0x1p+0 0x1p-60 0x0p+0 0x0p+0 0x0p+0 0x0p+0 "
     "-> 0x1p+0 0x1p-60 0x1p-100", "passed"),
    ("ball_add_2_full binary64 0x1p+0 0x1p-60 0x0p+0 0x0p+0 0x0p+0 0x0p+0 "
     "-> 0x1p+0 0x1p+0 0x1p-100", "B1"),
    ("ball_add_2_full binary64 0x0p+0 0x0p+0 inf nan nan nan -> nan nan nan", "passed"),
    ("ball_add_2_full binary64 0x0p+0 0x1p-60 inf nan nan nan -> nan nan nan", "invalid"),
    ("ball_scale_1_full binary64 0x1p+0 0x1p-1 inf -> 0x0p+0 inf", "passed"),
    ("ball_scale_1_full binary64 0x1p+0 0x1p-1 inf -> nan nan", "B2"),
    ("ball_scale_1_full binary64 0x1p+0 0x1p-1 inf -> 0x1p+0 0x1p+0", "B3"),
    ("ball_scale_1_full binary64 nan nan inf -> nan nan", "passed"),
    ("ball_scale_1_full binary64 0x0p+0 0x0p+0 nan -> 0x0p+0 inf", "passed"),
    ("ball_scale_1_full binary64 0x0p+0 inf 0x0p+0 -> 0x0p+0 0x0p+0", "B3"),
    ("ball_scale_1_full binary64 0x1p+0 0x1p-1 -0x1.8p+0 -> -0x1.8p+0 0x1.8p-1", "passed"),
    # makes_ball.
    ("ball_make_2 binary64 0x1p+0 0x1p-60 0x1p-3 -> 0x1p+0 0x1p-60 0x1p-3", "passed"),
    ("ball_make_2 binary64 0x1p+0 0x1p-60 0x1p-3 -> 0x1p+0 0x0p+0 0x1p-3", "failed"),
    ("ball_make_2 binary64 0x1p+0 0x1p-60 -0x1p-3 -> nan nan nan", "passed"),
    ("ball_make_2 binary64 0x1p+0 0x1p-60 -0x1p-3 -> 0x1p+0 0x1p-60 -0x1p-3", "failed"),
    ("ball_make_2 binary64 0x1p+0 0x1p-60 nan -> 0x0p+0 0x0p+0 inf", "failed"),
    ("ball_make_2 binary64 0x1p+0 0x1p-60 -inf -> nan nan nan", "passed"),
    ("ball_make_2 binary64 nan nan 0x1p+0 -> 0x0p+0 0x0p+0 inf", "passed"),
    ("ball_make_2 binary64 nan nan 0x1p+0 -> nan nan nan", "failed"),
    ("ball_make_2 binary64 -inf 0x0p+0 nan -> nan nan nan", "passed"),
    ("ball_make_2 binary64 0x1p+0 0x0p+0 inf -> 0x0p+0 0x0p+0 inf", "passed"),
    ("ball_make_2 binary64 0x1p+0 0x0p+0 -0x0p+0 -> 0x1p+0 0x0p+0 0x0p+0", "passed"),
    ("ball_make_2 binary64 0x1p+0 0x1p+0 0x1p+0 -> 0x1p+1 0x0p+0 0x1p+0", "invalid"),
    ("ball_make_1 binary64 -inf -inf -> nan nan", "passed"),
    ("ball_make_1 binary64 0x1p+0 0x1p-1 -> 0x1p+0 0x1p-2", "failed"),
    ("ball_make_1 binary64 0x1.8p+0 inf -> 0x0p+0 inf", "passed"),
    # represents.
    ("make_2 binary64 inf -> inf 0x0p+0", "passed"),
    ("make_2 binary64 -inf -> -inf -0x0p+0", "passed"),
    ("make_2 binary64 inf -> inf nan", "failed"),
    ("make_2 binary64 nan -> nan nan", "passed"),
    ("make_2 binary64 nan -> nan 0x0p+0", "failed"),
    ("make_2 binary64 0x1.8p+0 -> 0x1.8p+0 0x0p+0", "passed"),
    ("make_2 binary64 0x1.8p+0 -> 0x1p+0 0x1p-1", "failed"),
    ("make_2 binary64 0x1.8p+0 -> 0x1.4p+0 0x0p+0", "failed"),
    ("make_2_limbs binary64 0x1p+0 0x1p-60 -> 0x1p+0 0x1p-60", "passed"),
    ("make_2_limbs binary64 -inf 0x0p+0 -> -inf 0x0p+0", "passed"),
    ("make_2_limbs binary64 inf 0x1p+0 -> inf 0x0p+0", "invalid"),
    # normalized and error in the extended domain: canonical always, the rest when finite.
    ("neg_2 binary64 inf 0x0p+0 -> -inf 0x0p+0", "passed"),
    ("neg_2 binary64 inf 0x0p+0 -> -inf nan", "failed"),
    # represents pins the value: (inf, 0) gives (-inf, 0), and a finite operand a finite result.
    ("neg_2 binary64 inf 0x0p+0 -> nan nan", "failed"),
    ("neg_2 binary64 0x1p+0 0x1p-60 -> -0x1p+0 -0x1p-60", "passed"),
    ("neg_2 binary64 0x1p+0 0x1p-60 -> -0x1p+0 0x1p-60", "failed"),
    ("neg_2 binary64 0x1p+0 0x1p-60 -> -inf 0x0p+0", "failed"),
    ("neg_2 binary64 nan nan -> nan nan", "passed"),
    ("neg_2 binary64 nan nan -> nan 0x0p+0", "failed"),
    ("abs_2 binary64 -inf 0x0p+0 -> -inf 0x0p+0", "failed"),
    ("abs_2 binary64 -0x1p+0 0x1p-60 -> 0x1p+0 -0x1p-60", "passed"),
    ("abs_2 binary64 -0x1p+0 0x1p-60 -> 0x1p+0 0x1p-60", "failed"),
    # ball_neg_k: no fix-up, the extended-domain encloses.
    ("ball_neg_1 binary64 0x1p+0 0x1p-1 -> -0x1p+0 0x1p-1", "passed"),
    ("ball_neg_1 binary64 0x1p+0 0x1p-1 -> 0x1p+0 0x1p-1", "B3"),
    ("ball_neg_1 binary64 -0x0p+0 inf -> 0x0p+0 inf", "passed"),
    ("ball_neg_1 binary64 nan nan -> nan nan", "passed"),
    ("ball_neg_1 binary64 nan nan -> 0x0p+0 inf", "B2"),
    ("ball_neg_2 binary64 0x1p+0 0x1p-60 0x0p+0 -> -0x1p+0 -0x1p-60 0x0p+0", "passed"),
    ("ball_neg_2 binary64 0x1p+0 0x1p-60 0x0p+0 -> -0x1p+0 0x0p+0 0x0p+0", "B3"),
    ("ball_neg_2 binary64 0x0p+0 0x0p+0 inf -> 0x0p+0 0x0p+0 inf", "passed"),
    ("ball_neg_2 binary64 0x1p+0 0x1p+0 0x0p+0 -> -0x1p+0 -0x1p+0 0x0p+0", "invalid"),
    # the one-limb operations at precision 1: 3 lies halfway between 2 and 4 and rounds to 4.
    ("add_1_1 fp:1:-4:3 0x1p+0 0x1p+1 -> 0x1p+2", "passed"),
    ("add_1_1 fp:1:-4:3 0x1p+0 0x1p+1 -> 0x1p+1", "failed"),
    ("mul_1_1 fp:1:-4:3 0x1p-3 0x1p-3 -> 0x0p+0", "passed"),
    ("make_2 fp:1:-4:3 0x1p+3 -> 0x1p+3 0x0p+0", "passed"),
    ("abs_2 binary64 -inf 0x0p+0 -> inf 0x0p+0", "passed"),
    # predicate: the extended reals; false on a NaN.
    ("lt_2_2 binary64 inf 0x0p+0 inf 0x0p+0 -> 0", "passed"),
    ("lt_2_2 binary64 inf 0x0p+0 inf 0x0p+0 -> 1", "failed"),
    ("le_2_2 binary64 inf 0x0p+0 inf 0x0p+0 -> 1", "passed"),
    ("lt_2_2 binary64 -inf 0x0p+0 %s 0x0p+0 -> 1" % OM, "passed"),
    ("eq_2_2 binary64 nan nan nan nan -> 0", "passed"),
    ("eq_2_2 binary64 nan nan nan nan -> 1", "failed"),
    ("lt_2_1 binary64 0x1p+0 0x0p+0 nan -> 0", "passed"),
    ("le_1_2 binary64 nan 0x1p+0 0x0p+0 -> 1", "failed"),
    ("lt_1_2 binary64 %s inf 0x0p+0 -> 1" % OM, "passed"),
    ("eq_2_1 binary64 -inf 0x0p+0 -inf -> 1", "passed"),
    # rounded: overflow in the direction of rounding is the infinity; non-finite gives itself.
    ("to_up_2 binary64 %s 0x1p+969 -> inf" % OM, "passed"),
    ("to_up_2 binary64 %s 0x1p+969 -> %s" % (OM, OM), "failed"),
    ("to_down_2 binary64 %s 0x1p+969 -> %s" % (OM, OM), "passed"),
    ("to_down_2 binary64 -%s -0x1p+969 -> -inf" % OM, "passed"),
    ("to_down_2 binary64 -%s -0x1p+969 -> -%s" % (OM, OM), "failed"),
    ("to_up_2 binary64 -%s -0x1p+969 -> -%s" % (OM, OM), "passed"),
    ("abs_upper_2 binary64 -inf 0x0p+0 -> inf", "passed"),
    ("abs_upper_2 binary64 -inf 0x0p+0 -> -inf", "failed"),
    ("to_nearest_2 binary64 nan nan -> nan", "passed"),
    ("to_nearest_2 binary64 nan nan -> 0x0p+0", "failed"),
    ("to_down_2 binary64 0x1p+0 -0x1p-60 -> 0x1.fffffffffffffp-1", "passed"),
    # upper: NaN exactly for a NaN operand or 0 * inf; otherwise not below the value.
    ("radd binary64 0x1p+0 inf -> inf", "passed"),
    ("radd binary64 0x1p+0 inf -> nan", "failed"),
    ("rmul binary64 0x0p+0 inf -> nan", "passed"),
    ("rmul binary64 0x0p+0 inf -> inf", "failed"),
    ("rmul binary64 nan 0x1p+0 -> nan", "passed"),
    ("radd binary64 nan inf -> nan", "passed"),
    ("radd binary64 0x1p+0 0x1p-60 -> 0x1.0000000000001p+0", "passed"),
    ("radd binary64 0x1p+0 0x1p-60 -> 0x1.0000000000003p+0", "failed"),
    ("radd binary64 %s %s -> inf" % (OM, OM), "passed"),
    ("radd binary64 0x1p+0 0x1p+0 -> inf", "suspicious"),
    ("radd binary64 0x1p+0 0x1p+0 -> -inf", "failed"),
    ("radd binary64 -0x1p+0 0x1p+0 -> 0x1p-1074", "invalid"),
    ("radd binary64 -inf 0x1p+0 -> -inf", "invalid"),
]


@test
def judge_wave3(ctx):
    """Hand-written lines with verdicts and statistics worked out by hand."""
    cl = claims3(ctx)
    stmt = ("F1", "F2", "F3", "F4", "F5", "B1", "B2", "B3", "B4")
    for line, want in HAND3:
        s = judge([line], cl)
        t = totals(s)
        got = ("invalid" if t["invalid"] == 1 else "suspicious" if t["passed"] == 1 and
               t["suspicious"] == 1 else "passed" if t["passed"] == 1 else
               "failed" if t["failed"] == 1 else repr(t))
        kname = line.split()[0]
        if want in stmt:
            c = counts(s, kname, prefix="failed")
            expect(got == "failed" and c.get("failed " + want, 0) == 1,
                   "%s: %s %s, want a failure of %s" % (line, got, c, want))
            continue
        expect(got == want, "%s: %s, want %s" % (line, got, want))
    # Where represents pins the result, the suspicious heuristic says nothing more.
    s = judge(["neg_2 binary64 inf 0x0p+0 -> nan nan", "neg_2 binary64 0x1p+0 0x0p+0 -> inf 0x0p+0"],
              cl)
    expect(totals(s)["failed"] == 2 and totals(s)["suspicious"] == 0,
           "neg_2 pinned by represents: %r" % totals(s))
    # Statistics over the lines that pass, worked out by hand.
    s = judge([ln for ln, w in HAND3 if w == "passed"], cl)
    c = counts(s, "add_2_2_full")
    expect(c.get("class F2: finite operands, finite result") == 2
           and c.get("class F4: finite operands, non-finite result") == 3
           and c.get("class F5: a non-finite operand") == 5
           and c.get("F3 applies: finite operands, every finite_when condition holds") == 2,
           "add_2_2_full classes %s" % c)
    m = minima(s, "add_2_2_full")
    # The smallest overflow: (2^1022 + 2^968) + 2^1022 against 2^1024, leading limbs 2^1022.
    expect(Q(*m["overflow on finite operands: |value| / 2^(qmax+p)"][0]) == Q(1, 2) + Q(1, 2 ** 56)
           and Q(*m["overflow on finite operands: max |leading limb| / 2^(qmax+p)"][0]) == Q(1, 4),
           "smallest overflow %s" % m)
    c = counts(s, "ball_mul_1_full")
    expect(c == {"result: whole line": 2, "result: empty set": 2}, "ball_mul_1_full %s" % c)
    c = counts(s, "ball_make_2")
    expect(c == {"given: finite ball": 2, "given: empty set": 3, "given: whole line": 2},
           "ball_make_2 %s" % c)
    # A whole line from finite operands that is not small: its position is reported.
    s = judge(["ball_add_1_full binary64 %s 0x0p+0 %s 0x0p+0 -> 0x0p+0 inf" % (OM, OM)], cl)
    m = minima(s, "ball_add_1_full")
    expect(totals(s)["passed"] == 1 and
           Q(*m["whole line on finite operands: max |end of the set| / 2^(qmax+p)"][0])
           == Q(2 ** 54 - 2, 2 ** 53), "whole line position %s" % m)
    return "%d lines" % len(HAND3)


@test
def merging_wave3(ctx):
    """Summaries of two halves of a stream of the layer merge into the summary of the whole."""
    lines = []
    for k in EXTENDED:
        lines += run3(stream3(ctx, k, "fp:4:-6:1", ctx.n(400, 120)))
    cl = claims3(ctx)
    whole = judge(lines, cl, ignore_min_precision=True, max_examples=100000)
    cut = len(lines) // 2
    while not lines[cut].startswith("# kairn-oracle gen event=begin"):
        cut += 1
    a = judge(lines[:cut], cl, ignore_min_precision=True, max_examples=100000)
    b = judge(lines[cut:], cl, ignore_min_precision=True, max_examples=100000)
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
