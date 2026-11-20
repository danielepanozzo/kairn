"""The oracle's own tests for the kinds of Milestone 2 (architecture.md, "Claims of Milestone 2";
milestone2.md, "Building blocks on T" and "Scaling a ball by a power of two"): `neighbor`,
`bound`, `rounded` with `when` and with a value of two operands, `exact_when` on `error` and on
`encloses`.

As for the earlier waves, each test compares the oracle with something it does not share code
with: the neighbors, the directed roundings in the format with overflow and the steps of the
format against sorted lists of every number of toy formats; the thresholds of exact_when against
Fractions; the reference runner (written from milestone2.md's listings) on random streams and on
every case of tiny formats; planted faults that must be caught in the entry or statement where
they belong and nowhere else; and hand-written lines whose verdicts are worked out by hand.  The
fixture, oracle/selftest/claims-wave4.json, is written from architecture.md, not by the generator;
it has the kernels of the wave, and the same claims in the finite domain (`next_up_real`,
`mul_down_real`, ...) for the finite judge, and `mul_pow2_2` with an exact_when on its error.
"""

import concurrent.futures as cf
import copy
import json
import math
import os
import random
from bisect import bisect_left, bisect_right
from fractions import Fraction as Q

from . import check as C
from . import directed as D
from . import fmt as F
from . import gen as G
from . import gen2 as G2
from . import refrun
from .claims import Claims, ClaimsError, eval_const, ew_condition_text, load_claims
from .selftest import test, expect, judge, totals, brute_values, BruteRN, ORACLE_DIR
from .selftest2 import _unbounded_values
from .selftest3 import counts, failures

FIXTURE4 = os.path.join(ORACLE_DIR, "selftest", "claims-wave4.json")
NEIGHBOR = ("next_up", "next_down")
NEIGHBOR_REAL = ("next_up_real", "next_down_real")
DIRSUM = ("add_down_1", "add_up_1", "sub_down_1", "sub_up_1")
DIRPROD = ("mul_down_1", "mul_up_1")
DIRPROD_REAL = ("mul_down_real", "mul_up_real")
POW2 = ("ball_mul_pow2_1", "ball_mul_pow2_2")
POW2_FULL = ("ball_mul_pow2_1_full", "ball_mul_pow2_2_full")
OTHER = ("two_sum_ord", "mul_pow2_2")
ALL4 = NEIGHBOR + NEIGHBOR_REAL + DIRSUM + DIRPROD + DIRPROD_REAL + POW2 + POW2_FULL + OTHER
FORMATS4 = ("binary64", "binary32", "fp:5:-10:5", "fp:4:-6:1")
# The families of the generator (gen4.py) by kernel.
FAMILY4 = {"next_up": "neighbor", "next_down": "neighbor", "next_up_real": "neighbor",
           "next_down_real": "neighbor", "add_down_1": "dirsum", "add_up_1": "dirsum",
           "sub_down_1": "dirsum", "sub_up_1": "dirsum", "mul_down_1": "dirprod",
           "mul_up_1": "dirprod", "mul_down_real": "dirprod", "mul_up_real": "dirprod",
           "ball_mul_pow2_1": "ballpow2", "ball_mul_pow2_2": "ballpow2",
           "ball_mul_pow2_1_full": "ballpow2", "ball_mul_pow2_2_full": "ballpow2"}


def claims4(ctx):
    if not hasattr(ctx, "claims4"):
        ctx.claims4 = load_claims(FIXTURE4)
    return ctx.claims4


def run4(lines, variant="correct"):
    r = refrun.Runner(variant)
    out = []
    for ln in lines:
        out.extend(r.complete(ln))
    return out


def stream4(ctx, kernel, fmtname, count, strata=None, seed="selftest6"):
    key = ("w4", kernel, fmtname, count, strata, seed)
    s = ctx._streams.get(key)
    if s is None:
        g = G.RandomGen(claims4(ctx).get(kernel), F.parse_format(fmtname), seed,
                        strata.split(",") if strata else None)
        s = ctx._streams[key] = list(g.lines(0, count))
    return s


def exhaustive4(ctx, kernel, fmtname, restrict=(), variant="correct", chunk=20000):
    """The summary of every case of an enumeration through the Python runner, in parallel."""
    from . import brute
    g = G.ExhaustiveGen(claims4(ctx).get(kernel), F.parse_format(fmtname), list(restrict))
    tasks = [dict(claims=FIXTURE4, kernel=kernel, format=fmtname, exhaustive=True,
                  restrict=list(restrict), seed=None, strata=None, variant=variant,
                  max_examples=5, ignore_min_precision=False, start=s, radius="first",
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


def needed(kernel):
    """{entry index: [count names]}: the classes of the statements of Milestone 2 that a stream
    of the kernel must have reached, as the cross-checks' guards ask for them."""
    out = {}
    for j, e in enumerate(kernel.ensures):
        need = []
        if e.kind == "neighbor":
            if kernel.extended:
                need = list(D.NEIGHBOR_ROWS)
            else:
                beyond = D.ROW_OMEGA if e.side == "up" else D.ROW_NOMEGA
                need = [r for r in D.NEIGHBOR_ROWS
                        if r not in (D.ROW_NAN, D.ROW_PINF, D.ROW_NINF, beyond)]
            need += list(D.NEIGHBOR_STEPS)
        elif e.kind == "rounded":
            if e.when:
                need += [D.WHEN_HOLDS, D.WHEN_FAILS]
            if kernel.extended:
                need += ["exact", "inexact, != RN", D.OVER_ABOVE, D.OVER_BELOW, D.NAN_OPERAND,
                         D.INF_OPERAND]
        elif e.kind == "bound":
            need += [D.BOUND_AT, D.BOUND_ONE, D.BOUND_INEXACT]
            if kernel.extended:
                need += ["a non-finite operand", D.OVER_ABOVE, D.OVER_BELOW, D.NAN_OPERAND,
                         D.INF_OPERAND]
        if e.exact_when:
            need.append(D.EXACT_HOLDS)
            need += [D.EXACT_FAILS + ew_condition_text(t, op, k) for _tr, t, op, k in e.exact_when]
        if need:
            out[j] = need
    return out


def entry_counts(s, kernel):
    """[{count: n}] per entry of the kernel's own claims, summed over formats and tags."""
    out = None
    for (k, _f, _t), st in s.keys.items():
        if k != kernel:
            continue
        if out is None:
            out = [{} for _ in st.entries]
        for d, e in zip(out, st.entries):
            for key, n in e.counts.items():
                d[key] = d.get(key, 0) + n
    return out or []


def missing_classes(s, cl, kernel):
    ec = entry_counts(s, kernel)
    return [(cl.get(kernel).ensures[j].label, name) for j, need in needed(cl.get(kernel)).items()
            for name in need if not (j < len(ec) and ec[j].get(name))]


def caught(s, kernel):
    """The entries of a kernel that failed, as KIND or KIND:STATEMENT (the "failed X" counts of an
    entry that names its statements)."""
    out = set()
    for (k, _f, _t), st in s.keys.items():
        if k != kernel:
            continue
        for e in st.entries:
            if not e.failures:
                continue
            stmts = [c[len("failed "):] for c in e.counts if c.startswith("failed ")]
            out |= {"%s:%s" % (e.kind, x) for x in stmts} if stmts else {e.kind}
    return out


# ---------------------------------------------------------------------------

def _malformed(raw):
    """(kernel, mutation, what) for the claims of the wave that must be set aside."""
    def ens(i=0, **kw):
        def f(k):
            k["ensures"][i].update(kw)
        return f

    def drop(field, i=0):
        def f(k):
            del k["ensures"][i][field]
        return f

    def cond(j=0, **kw):
        def f(k):
            ew = k["ensures"][-1]["exact_when"]
            ew[j] = dict(kw)
        return f

    def value(v):
        def f(k):
            k["value"] = v
        return f

    def outputs2(k):
        k["outputs"][0]["limbs"] = 2

    def fw_limb(k):
        k["ensures"][0]["finite_when"] = [{"abs_le": "cx[0]*c", "exp": -2}]

    return [
        ("next_up", ens(side="left"), "a neighbor side that is not up or down"),
        ("next_up", drop("side"), "a neighbor without its side"),
        ("next_up", ens(steps=1), "a neighbor with a field of bound"),
        ("next_up", value("-a"), "a neighbor whose value is not the name of an input"),
        ("next_up", outputs2, "a neighbor of a two-limb output"),
        ("mul_down_1", ens(side="up"), "a bound side that is not below or above"),
        ("mul_down_1", ens(steps=-1), "a negative number of steps"),
        ("mul_down_1", ens(steps="1"), "steps as a string"),
        ("mul_down_1", ens(steps=True), "steps as a boolean"),
        ("mul_down_1", ens(steps=1.5), "steps not an integer"),
        ("mul_down_1", drop("steps"), "a bound without steps"),
        ("mul_down_1", ens(1, when="limb_products_normal"), "a condition of error on rounded"),
        ("mul_down_1", ens(1, when="sometimes"), "an unknown condition on rounded"),
        ("mul_down_1", ens(1, mode="nearest"), "a condition on a rounding to nearest"),
        ("add_down_1", ens(exact_when=[{"zero_or_abs_gt": "a", "than": "1"}]),
         "exact_when on rounded"),
        ("ball_mul_pow2_1", ens(exact_when=[]), "an empty exact_when"),
        ("ball_mul_pow2_1", ens(exact_when={"zero_or_abs_gt": "cx*c", "than": "eta"}),
         "exact_when not a list"),
        ("ball_mul_pow2_1", cond(zero_or_abs_gt="cx*c", zero_or_abs_ge="cx*c", than="eta"),
         "a condition with two relations"),
        ("ball_mul_pow2_1", cond(zero_or_abs_gt="cx*c"), "a condition without its threshold"),
        ("ball_mul_pow2_1", cond(zero_or_abs_gt="cx*c", than="eta", exp=1),
         "a condition with another field"),
        ("ball_mul_pow2_1", cond(abs_gt="cx*c", than="eta"), "an unknown relation"),
        ("ball_mul_pow2_1", cond(zero_or_abs_gt="cy*c", than="eta"),
         "a condition over an unknown input"),
        ("ball_mul_pow2_1", cond(zero_or_abs_gt="cx[1]*c", than="eta"),
         "a limb a one-limb input does not have"),
        ("ball_mul_pow2_2", cond(zero_or_abs_gt="cx[2]*c", than="eta"),
         "a limb a two-limb input does not have"),
        ("ball_mul_pow2_1", cond(zero_or_abs_gt="abs[0]*c", than="eta"), "a function as a limb"),
        ("ball_mul_pow2_1", cond(zero_or_abs_gt="cx*c", than="-1"), "a negative threshold"),
        ("ball_mul_pow2_1", cond(zero_or_abs_gt="cx*c", than="u-u"), "a zero threshold"),
        ("ball_mul_pow2_1", cond(zero_or_abs_gt="cx*c", than="1/(u-u)"), "a division by zero"),
        ("ball_mul_pow2_1", cond(zero_or_abs_gt="cx*c", than="x"), "a threshold over a name"),
        ("ball_mul_pow2_1", cond(zero_or_abs_gt="cx*c", than="2^(1/2)"), "a fractional power"),
        ("ball_mul_pow2_1", cond(zero_or_abs_gt="cx*c", than="(eta"), "unbalanced parentheses"),
        ("ball_mul_pow2_1", cond(zero_or_abs_gt="cx*c", than=None), "a threshold that is null"),
        ("ball_mul_pow2_2", value("cx[0]*c"), "a limb reference in a value"),
        ("ball_mul_pow2_1_full", fw_limb, "a limb reference in finite_when"),
        ("mul_pow2_2", ens(1, exact_when=[{"zero_or_abs_ge": "x[0]*c"}]),
         "an error's condition without its threshold"),
        ("two_sum_ord", ens(1, exact_when="always"), "an error's exact_when not a list"),
    ]


@test
def claims_reading_wave4(ctx):
    """The fixture of Milestone 2 loads; its labels say what is judged; 36 malformed kernels are
    set aside without making the others unreadable; the thresholds of exact_when are the exact
    values of their expressions, and one positive in binary64 but not in a toy format sets the
    kernel aside for that format only; limb references read the limb they name."""
    cl = claims4(ctx)
    expect(not cl.broken, "fixture4 kernels set aside: %s" % cl.errors())
    expect(set(cl.kernels) == set(ALL4), "fixture4 kernels %s" % sorted(cl.kernels))
    labels = {k: [e.label for e in cl.get(k).ensures] for k in ALL4}
    expect(labels["next_up"] == ["neighbor(r) up of a"], labels["next_up"])
    expect(labels["mul_down_1"] == ["bound(r) below, steps=1",
                                    "rounded(r) down, when product_large"], labels["mul_down_1"])
    expect("exactly the set when (cx[0]*c = 0 or |cx[0]*c| > eta/(2*u))"
           in labels["ball_mul_pow2_2"][1], labels["ball_mul_pow2_2"])
    expect("exact when (x[0]*c = 0 or |x[0]*c| >= eta/(2*u))" in labels["mul_pow2_2"][1],
           labels["mul_pow2_2"])
    raw = json.load(open(FIXTURE4))
    tried = 0
    for kernel, mutate, what in _malformed(raw):
        d = copy.deepcopy(raw)
        mutate(next(x for x in d["kernels"] if x["name"] == kernel))
        c = Claims(d)
        expect(kernel in c.broken and c.get(kernel) is None, "claims with %s accepted" % what)
        expect(len(c.kernels) == len(raw["kernels"]) - 1,
               "%s made other kernels unreadable: %s" % (what, sorted(set(c.broken) - {kernel})))
        tried += 1
    # The thresholds, exactly.
    u, eta = Q(1, 2 ** 53), Q(1, 2 ** 1074)
    for text, want in (("eta/(2*u)", Q(1, 2 ** 1022)), ("2^-3", Q(1, 8)), ("-2^2", Q(-4)),
                       ("2^3^2", Q(512)), ("(1+u)^2", (1 + u) ** 2), ("u^-1", Q(2 ** 53)),
                       ("3*eta - eta/2", Q(5, 2) * eta), ("2 ^ -1", Q(1, 2)), (7, Q(7)),
                       ("eta/(2*u^2)", Q(2 ** 105, 2 ** 1074))):
        got = eval_const(text, u, eta)
        expect(got == want, "eval_const(%r) = %s, want %s" % (text, got, want))
    for text in ("x", "2^(1/2)", "1/0", "(1", "1)", "", "eta eta", "unit(add_2_2)", "up(eta)",
                 None, True, "2^-100000"):
        try:
            eval_const(text, u, eta)
            raise AssertionError("eval_const(%r) accepted" % (text,))
        except ClaimsError:
            pass
    # A threshold positive in binary64 (2^-10 - 2^-53) and negative at p = 4 (2^-10 - 2^-4):
    # the kernel is read, and set aside when a line of that format comes.
    d = copy.deepcopy(raw)
    k = next(x for x in d["kernels"] if x["name"] == "ball_mul_pow2_1")
    k["ensures"][0]["exact_when"][0]["than"] = "2^-10 - u"
    c = Claims(d)
    expect(not c.broken, "a threshold positive in binary64 refused: %s" % c.errors())
    s = judge(["ball_mul_pow2_1 binary64 0x1p+0 0x0p+0 0x1p+0 -> 0x1p+0 0x0p+0",
               "ball_mul_pow2_1 fp:4:-6:1 0x1p+0 0x0p+0 0x1p+0 -> 0x1p+0 0x0p+0"], c)
    expect(s.claims_errors and "not positive in fp:4:-6:1" in s.claims_errors[0]
           and totals(s)["passed"] == 1 and totals(s)["failed"] == 1,
           "a threshold negative in a format: %s %r" % (s.claims_errors, totals(s)))
    # The conditions against Fractions, limb by limb, on random operands of three formats.
    rnd = random.Random(46)
    n = 0
    for fname in ("binary64", "fp:3:-3:2", "fp:6:-10:1"):
        f = F.parse_format(fname)
        pl = C.Plan(cl.get("ball_mul_pow2_2"), f, False)
        conds = pl.entries[1]["exact"]
        Nq = Q(2) ** (f.qmin + f.p - 1)
        etaf = Q(2) ** f.qmin
        vals = F.all_values(f) if f.p < 10 else None
        for _ in range(ctx.n(3000, 800)):
            pick = (lambda: rnd.choice(vals)) if vals else (
                lambda: rnd.choice((-1, 1)) * (G.in_binade(f, G.CaseRandom(b"k", rnd.randrange(1 << 30)),
                                                           rnd.randint(f.qmin, f.emax))))
            x0, x1, r = pick(), rnd.choice((0, pick())), abs(pick())
            c = 1 << rnd.randint(0, min(60, f.emax - f.qmin))
            x = [x0, x1, r, c]
            vq = [Q(v) * etaf for v in x]
            want = [(vq[0] * vq[3] == 0 or abs(vq[0] * vq[3]) > Nq),
                    (vq[1] * vq[3] == 0 or abs(vq[1] * vq[3]) > Nq),
                    (vq[2] * vq[3] == 0 or abs(vq[2] * vq[3]) > Nq)]
            got = [h(x) for h, _t in conds]
            expect(got == want, "%s: conditions at %r: %r, want %r" % (fname, x, got, want))
            n += 1
    return "%d malformed kernels set aside; %d conditions against Fractions" % (tried, n)


@test
def directed_arithmetic(ctx):
    """The helpers of the kinds of Milestone 2 against sorted lists of every number of seven toy
    formats (precision 1 included): the table of next_up and next_down on every value, infinities
    and NaN included, with the rows and the classes of steps from their definitions; the directed
    roundings and the rounding to nearest in the format with overflow on every multiple of eta/8
    up to beyond Omega; the steps of the format unbounded above; the overflow classes."""
    pts = 0
    for p, qmin, qmax in ((2, -2, 2), (3, -3, 2), (4, -6, 3), (5, -4, 1), (1, -3, 2), (3, -3, 0),
                          (4, 2, 5)):
        f = F.Format(p, qmin, qmax)
        eta = Q(2) ** qmin
        Nq = Q(2) ** (qmin + p - 1)
        vals = brute_values(p, qmin, qmax)               # sorted Fractions, one zero
        fixed = [int(v / eta) for v in vals]
        om = max(fixed)
        for i, v in enumerate(fixed):
            up = fixed[i + 1] if i + 1 < len(fixed) else F.POS_INF
            down = fixed[i - 1] if i > 0 else F.NEG_INF
            expect(D.neighbor(f, v, True) == up and D.neighbor(f, v, False) == down,
                   "neighbor of %s in %s" % (vals[i], f.name))
            row = (D.ROW_ZERO if v == 0 else D.ROW_OMEGA if v == om else D.ROW_NOMEGA if v == -om
                   else D.ROW_ETA if vals[i] == eta else D.ROW_NETA if vals[i] == -eta
                   else D.ROW_POS if v > 0 else D.ROW_NEG)
            expect(D.neighbor_row(f, v) == row, "row of %s in %s" % (vals[i], f.name))
            for side, r in ((True, up), (False, down)):
                want = []
                if type(r) is int:
                    a = abs(vals[i])
                    pow2 = a > 0 and (a.numerator & (a.numerator - 1)) == 0 and a.denominator & (
                        a.denominator - 1) == 0
                    toward = v != 0 and (v < 0) == side
                    if toward and pow2 and a > Nq:
                        want.append(D.STEP_POW2)
                    if (a >= Nq) != (abs(Q(r) * eta) >= Nq):
                        want.append(D.STEP_SUBNORMAL)
                expect(D.neighbor_steps(f, v, r, side) == want,
                       "steps from %s %s in %s: %r" % (vals[i], side, f.name,
                                                      D.neighbor_steps(f, v, r, side)))
            pts += 1
        # The rows of the values that are not finite.
        for a, up, down, row in ((F.NAN, F.NAN, F.NAN, D.ROW_NAN), (F.POS_INF, F.POS_INF, om, D.ROW_PINF),
                                 (F.NEG_INF, -om, F.NEG_INF, D.ROW_NINF)):
            expect(D.neighbor(f, a, True) == up and D.neighbor(f, a, False) == down
                   and D.neighbor_row(f, a) == row, "neighbor of %s in %s" % (a, f.name))
        # The roundings with overflow, every multiple of eta/8.
        br = BruteRN(p, qmin, qmax) if p >= 2 else None
        omq = Q(om) * eta
        step = eta / 8
        lim = int((omq * 2 + 8 * eta) / step)
        for j in range(-lim, lim + 1):
            t = j * step
            i = bisect_right(vals, t)
            rd = vals[i - 1] if i > 0 else None
            k = bisect_left(vals, t)
            ru = vals[k] if k < len(vals) else None
            want_d = (F.NEG_INF if t < -omq else om if t > omq else int(rd / eta))
            want_u = (F.POS_INF if t > omq else -om if t < -omq else int(ru / eta))
            expect(D.round_overflow(f, j, qmin - 3, "down") == want_d
                   and D.round_overflow(f, j, qmin - 3, "up") == want_u,
                   "directed roundings of %s in %s" % (t, f.name))
            if br is not None:
                n = br(t)
                want_n = n if isinstance(n, float) else int(n / eta)
                got = D.round_overflow(f, j, qmin - 3, "nearest")
                got = got if type(got) is int else (math.inf if got == F.POS_INF else -math.inf)
                expect(got == want_n, "RN(%s) in %s" % (t, f.name))
            oc = D.overflow_class(f, j, qmin - 3)
            expect(oc == (D.OVER_ABOVE if t > omq else D.OVER_BELOW if t < -omq else None),
                   "overflow class of %s in %s" % (t, f.name))
            pts += 1
        # The steps of the format unbounded above.
        ext = _unbounded_values(p, qmin, qmax)
        for i in range(1, len(ext) - 1):
            v = int(ext[i] / eta)
            expect(D.step_unbounded(f, v, True) == int(ext[i - 1] / eta)
                   and D.step_unbounded(f, v, False) == int(ext[i + 1] / eta),
                   "unbounded steps of %s in %s" % (ext[i], f.name))
    return "%d points" % pts


def _parse_case(fmt, line):
    toks = line.split(" -> ")[0].split()
    return [F.parse_limb(fmt, t) for t in toks[2:] if not t.startswith("#")]


def _corners(ctx, fname):
    """The corners each stratum of the families of Milestone 2 is for, reached in fname: a
    message for each one missed."""
    f = F.parse_format(fname)
    q = f.qmin
    om, lam = f.omega, f.lam
    P2 = 1 << (2 * f.p - 1 - q)                      # P at the scale of a product, eta^2
    ulp = Q(1, 1 << (f.p - 2))
    miss = []
    n = ctx.n(1500, 600)

    def cases(kernel, stratum):
        return [_parse_case(f, ln) for ln in stream4(ctx, kernel, fname, n)
                if ln.endswith(tuple("#%s:%d" % (stratum, i) for i in range(10)))
                or ("#%s:" % stratum) in ln]

    def need(what, cond, rows):
        if not any(cond(r) for r in rows):
            miss.append("%s %s" % (fname, what))
    # neighbor: special values, binade boundaries, the subnormal boundary.
    sp = cases("next_up", "special")
    for v, what in ((0, "zero"), (1, "eta"), (-1, "-eta"), (om, "Omega"), (-om, "-Omega"),
                    (lam, "N"), (lam - 1, "pred(N)")):
        need("special %s" % what, lambda r, v=v: r[0] == v, sp)
    bi = cases("next_down", "binade")
    need("binade: a power of two", lambda r: r[0] > 0 and r[0] & (r[0] - 1) == 0, bi)
    need("binade: a negative power of two", lambda r: r[0] < 0 and -r[0] & (-r[0] - 1) == 0, bi)
    sub = cases("next_up", "subnormal")
    need("subnormal: N", lambda r: abs(r[0]) == lam, sub)
    need("subnormal: a subnormal number", lambda r: 0 < abs(r[0]) < lam, sub)
    # dirsum: beyond each side, Omega as either operand, cancellation, exact sums, apart.
    be = cases("add_down_1", "beyond")
    need("beyond: a sum above Omega", lambda r: r[0] + r[1] > om, be)
    need("beyond: a sum below -Omega", lambda r: r[0] + r[1] < -om, be)
    oo = cases("add_up_1", "omega")
    need("omega: Omega as the first operand", lambda r: abs(r[0]) == om, oo)
    need("omega: Omega as the second operand", lambda r: abs(r[1]) == om, oo)
    ca = cases("add_down_1", "cancel")
    need("cancel: an exact cancellation", lambda r: r[0] + r[1] == 0, ca)
    need("cancel: a near cancellation", lambda r: r[0] + r[1] != 0 and abs(r[0] + r[1]) * 4 <
         F.ulp(f, r[0]) * 16, ca)
    ex = cases("sub_up_1", "exact")
    need("exact: a difference that is a number of the format",
         lambda r: r[0] - r[1] != 0 and F.is_member(f, r[0] - r[1]), ex)
    ap = cases("add_up_1", "apart")
    need("apart: an operand below half an ulp of the other",
         lambda r: 0 < 2 * min(abs(r[0]), abs(r[1])) < F.ulp(f, max(abs(r[0]), abs(r[1]))), ap)
    # dirprod: around P, tiny products, exact products, beyond.
    ar = cases("mul_down_1", "aroundp")
    need("aroundp: a product exactly P", lambda r: abs(r[0] * r[1]) == P2, ar)
    need("aroundp: a product just below P",
         lambda r: P2 * (1 - ulp) <= abs(r[0] * r[1]) < P2, ar)
    need("aroundp: a product just above P",
         lambda r: P2 < abs(r[0] * r[1]) <= P2 * (1 + ulp), ar)
    need("aroundp: a product below P that rounds to P",
         lambda r: 0 < abs(r[0] * r[1]) < P2 and F.rn(f, abs(r[0] * r[1]), 2 * q) == lam << f.p, ar)
    ti = cases("mul_up_1", "tiny")
    need("tiny: a product below eta/2", lambda r: 0 < 2 * abs(r[0] * r[1]) < 1 << -q, ti)
    need("tiny: a product of eta/2", lambda r: 2 * abs(r[0] * r[1]) == 1 << -q, ti)
    need("tiny: a product of eta", lambda r: abs(r[0] * r[1]) == 1 << -q, ti)
    bp = cases("mul_down_1", "beyond")
    need("beyond: a product above Omega", lambda r: r[0] * r[1] > om << -q, bp)
    need("beyond: a product below -Omega", lambda r: r[0] * r[1] < -(om << -q), bp)
    zz = cases("mul_up_1", "zero")
    need("zero: a zero factor with Omega", lambda r: 0 in r and om in map(abs, r), zz)
    # ballpow2: the scaled leading limb, second limb and radius at N, above and below it.
    for k in POW2:
        at = cases(k, "atnormal")
        two = k.endswith("_2")
        sc = (lambda r: (r[0], r[1], r[2], r[3])) if two else (lambda r: (r[0], 0, r[1], r[2]))
        for name, i in (("leading limb", 0), ("radius", 2)) + ((("second limb", 1),) if two else ()):
            need("%s atnormal: the scaled %s exactly N" % (k, name),
                 lambda r, i=i: abs(sc(r)[i] * sc(r)[3]) == lam << -q, at)
            need("%s atnormal: the scaled %s just below N" % (k, name),
                 lambda r, i=i: 0 < abs(sc(r)[i] * sc(r)[3]) < lam << -q
                 and abs(sc(r)[i] * sc(r)[3]) * 4 > (lam << -q) * 3, at)
            need("%s atnormal: the scaled %s just above N" % (k, name),
                 lambda r, i=i: lam << -q < abs(sc(r)[i] * sc(r)[3]) < (lam << -q) * 5 // 4, at)
        si = cases(k, "sides")
        need("%s sides: a power of two below 1" % k, lambda r: r[-1] < 1 << -q, si)
        need("%s sides: a power of two above 1" % k, lambda r: r[-1] > 1 << -q, si)
    return miss


@test
def gen_wave4(ctx):
    """Every generated case of every kernel of the fixture, in every stratum and four formats,
    satisfies the requirements; the reference runner passes, with nothing suspicious; every
    stratum occurs, and each family is the one its claims call for; every class the guards ask
    for occurs (the rows of the table, both classes of steps, both outcomes of when, the
    overflows, the operands that are not finite, a result one step beyond, each condition of
    exact_when failing); the strata reach the corners they are for (products at, just below and
    just above P and below P rounding to P; scaled limbs and radii at N, just above and below;
    sums beyond each side; Omega in either position; ...); case i alone equals case i of a run."""
    cl = claims4(ctx)
    n = 0
    for fname in FORMATS4:
        lines = []
        for k in ALL4:
            lines += stream4(ctx, k, fname, ctx.n(1500, 600))
        s = judge(run4(lines), cl, ignore_min_precision=True)
        t = totals(s)
        expect(t["invalid"] == 0, "%s: %d invalid generated cases: %s" % (
            fname, t["invalid"], failures(s, kind="invalid")[:2]))
        expect(t["failed"] == 0 and not s.stream_errors and t["suspicious"] == 0,
               "%s: correct runner flagged: %s %s" % (fname, failures(s)[:2],
                                                      failures(s, kind="suspicious")[:1]))
        for k in ALL4:
            g = G.RandomGen(cl.get(k), F.parse_format(fname), "x")
            tags = {key[2] for key in s.keys if key[0] == k}
            expect(tags == set(g.strata), "%s %s: strata %s, want %s" % (k, fname, sorted(tags),
                                                                         sorted(g.strata)))
            fam = getattr(g.shape, "fshape", g.shape)
            expect(getattr(fam, "family", None) == FAMILY4.get(k, getattr(fam, "family", None)),
                   "%s: family %s" % (k, getattr(fam, "family", None)))
            if fname != "fp:4:-6:1":
                miss = missing_classes(s, cl, k)
                expect(not miss, "%s %s: classes never reached: %s" % (k, fname, miss))
        miss = _corners(ctx, fname)
        expect(not miss, "corners never reached: %s" % miss)
        n += t["cases"]
    rnd = random.Random(9)
    for k in ("next_up", "add_down_1", "mul_up_1", "ball_mul_pow2_2", "ball_mul_pow2_1_full"):
        g = G.RandomGen(cl.get(k), F.parse_format("binary64"), "cb")
        run = list(g.lines(40, 160))[1:-1]
        for _ in range(6):
            i = rnd.randrange(40, 200)
            alone = list(G.RandomGen(cl.get(k), F.parse_format("binary64"), "cb").lines(i, 1))[1]
            expect(alone == run[i - 40], "case %d of %s" % (i, k))
        other = list(G.RandomGen(cl.get(k), F.parse_format("binary64"), "cb2").lines(40, 160))
        expect(sum(a != b for a, b in zip(run, other[1:-1])) > 100, "%s: seed has no effect" % k)
    return "%d cases in %d formats" % (n, len(FORMATS4))


# The enumerations: (format, kernel); every class the guards ask for must occur in each.
PLAN4 = [("fp:3:-3:2", k) for k in NEIGHBOR + NEIGHBOR_REAL] + [
    ("fp:1:-3:2", "next_up"), ("fp:2:-2:1", "next_down")] + [
    ("fp:3:-3:0", k) for k in DIRSUM + DIRPROD + DIRPROD_REAL + POW2 + POW2_FULL] + [
    ("fp:2:-2:1", "mul_up_1"), ("fp:3:-3:2", "two_sum_ord"), ("fp:3:-3:2", "mul_pow2_2")]
PLAN4_FULL = [("fp:4:-5:0", k) for k in DIRSUM + DIRPROD] + [
    ("fp:4:-6:1", k) for k in ("ball_mul_pow2_1", "ball_mul_pow2_1_full")] + [
    ("fp:5:-7:2", k) for k in NEIGHBOR]


@test
def exhaustive_wave4(ctx):
    """The domains of the kernels of Milestone 2 against brute-force counts; and the reference
    runner on every case of tiny formats for every kernel of the fixture (precision 1 for the
    neighbors): nothing flagged, every line of the extended domain judged, the coverage complete,
    and every class the guards ask for reached in each enumeration."""
    cl = claims4(ctx)
    p, qmin, qmax = 3, -3, 0
    f = F.Format(p, qmin, qmax)
    vals = F.all_values(f)
    nv, nn = len(vals), sum(1 for v in vals if v >= 0)
    pow2 = sum(1 for v in vals if v > 0 and v & (v - 1) == 0)
    pairs = len(G.normalized_pairs(f))
    want = {"next_up": nv + 3, "next_up_real": nv, "add_down_1": (nv + 3) ** 2,
            "mul_up_1": (nv + 3) ** 2, "mul_down_real": nv * nv, "two_sum_ord": nv * nv,
            "ball_mul_pow2_1": nv * nn * pow2, "ball_mul_pow2_2": pairs * nn * pow2,
            "ball_mul_pow2_1_full": (nv * nn + 2) * pow2,
            "ball_mul_pow2_2_full": (pairs * nn + 2) * pow2, "mul_pow2_2": pairs * pow2}
    for k, w in want.items():
        g = G.ExhaustiveGen(cl.get(k), f)
        expect(g.total == w, "%s total %d, want %d" % (k, g.total, w))
    out = []
    for fname, k in PLAN4 + ([] if ctx.quick else PLAN4_FULL):
        s = exhaustive4(ctx, k, fname)
        t = totals(s)
        expect(t["failed"] == 0 and not s.stream_errors and t["invalid"] == 0
               and t["suspicious"] == 0 and t["out_of_scope"] == 0,
               "correct runner flagged on %s %s: %r %s" % (k, fname, t, failures(s)[:2]))
        expect(t["judged"] == t["cases"] > 0 if cl.get(k).extended else t["judged"] > 0,
               "not every case judged for %s %s: %r" % (k, fname, t))
        cov = s.coverage.describe()
        expect(cov and "COMPLETE" in cov[0], "coverage of %s: %s" % (k, cov))
        miss = missing_classes(s, cl, k)
        expect(not miss, "%s %s: classes never reached in the enumeration: %s" % (k, fname, miss))
        out.append(t["cases"])
    return "%d enumerations, %d cases" % (len(out), sum(out))


# The planted faults: (variant, kernels where it must be caught, keys of which one must fail
# there (KIND or KIND:STATEMENT, alternatives separated by |), keys allowed to fail there,
# kernels that must stay clean).
CLEAN_BLOCKS = ("two_sum_ord", "mul_pow2_2")
INJECTED4 = (
    ("next-up-neg-away", ("next_up", "next_up_real"), ("neighbor",), ("neighbor",),
     ("next_down", "next_down_real", "add_up_1")),
    ("next-up-ninf", ("next_up",), ("neighbor",), ("neighbor",),
     ("next_up_real", "next_down", "next_down_real")),
    ("next-down-zero", ("next_down", "next_down_real"), ("neighbor",), ("neighbor",),
     ("next_up", "next_up_real", "sub_down_1")),
    ("dir-sum-nearest", DIRSUM, ("rounded",), ("rounded",), DIRPROD + CLEAN_BLOCKS),
    ("dir-sum-overflow-inf", DIRSUM, ("rounded",), ("rounded",), DIRPROD + CLEAN_BLOCKS),
    ("mul-bound-wrong-side", DIRPROD + DIRPROD_REAL, ("bound",), ("bound", "rounded"),
     DIRSUM + CLEAN_BLOCKS),
    ("mul-bound-two-beyond", DIRPROD + DIRPROD_REAL, ("bound",), ("bound",),
     DIRSUM + CLEAN_BLOCKS),
    ("mul-large-step", DIRPROD + DIRPROD_REAL, ("rounded",), ("rounded",),
     DIRSUM + CLEAN_BLOCKS),
    ("pow2-radius-small", POW2 + POW2_FULL, ("encloses:containment|encloses:B3",),
     ("encloses:containment", "encloses:B3", "encloses:exact_when"), CLEAN_BLOCKS + DIRSUM),
    ("pow2-grow-exact", POW2 + POW2_FULL, ("encloses:exact_when",), ("encloses:exact_when",),
     CLEAN_BLOCKS + DIRSUM),
    ("pow2-zero-radius-grows", POW2 + POW2_FULL, ("encloses:exact_when",),
     ("encloses:exact_when",), CLEAN_BLOCKS + DIRSUM),
    ("pow2-center-off", POW2 + POW2_FULL, ("encloses:exact_when",), ("encloses:exact_when",),
     CLEAN_BLOCKS + DIRSUM),
    ("pow2-scale-eta", ("mul_pow2_2",), ("error:exact_when",), ("error:exact_when",),
     POW2 + POW2_FULL + ("two_sum_ord",)),
)


def _check_injected(s, variant, flagged, need, allowed, clean, label):
    for k in flagged:
        got = caught(s, k)
        for alt in need:
            expect(got & set(alt.split("|")), "%s %s: %s not caught in %s (%s)"
                   % (label, variant, k, alt, sorted(got)))
        extra = got - set(allowed)
        expect(not extra, "%s %s: %s caught in other entries %s" % (label, variant, k,
                                                                    sorted(extra)))
    for k in clean:
        expect(totals(s, k)["failed"] == 0, "%s %s: %s flagged although it does not use the "
               "fault: %s" % (label, variant, k, failures(s, (k,))[:1]))


@test
def injected_wave4(ctx):
    """The planted faults of the wave in the Python reference runner, on binary64, binary32 and a
    toy format: each caught in the entry or statement where it belongs, in no other, and in no
    kernel that does not use it."""
    res = []
    cl = claims4(ctx)
    for fname in ("binary64", "binary32", "fp:4:-6:1"):
        for variant, flagged, need, allowed, clean in INJECTED4:
            lines = []
            for k in flagged + clean:
                lines += stream4(ctx, k, fname, ctx.n(1500, 600))
            s = judge(run4(lines, variant), cl)
            _check_injected(s, variant, flagged, need, allowed, clean, fname)
            res.append("%s %s %d" % (fname, variant, totals(s)["failed"]))
    return "%d runs" % len(res)


# The tiny format where each fault is enumerated, by the kernel it is caught in.
INJECTED4_FORMATS = {"next_up": "fp:3:-3:2", "next_down": "fp:3:-3:2",
                     "next_up_real": "fp:3:-3:2", "next_down_real": "fp:3:-3:2",
                     "mul_pow2_2": "fp:3:-3:2"}


@test
def injected_wave4_exhaustive(ctx):
    """The planted faults on every case of tiny formats: caught where they belong and nowhere
    else (one kernel per fault with --quick, every kernel without)."""
    res = []
    for variant, flagged, need, allowed, _clean in INJECTED4:
        ks = flagged if not ctx.quick else flagged[:1]
        for k in ks:
            fname = INJECTED4_FORMATS.get(k, "fp:3:-3:0")
            s = exhaustive4(ctx, k, fname, variant=variant)
            _check_injected(s, variant, (k,), need, allowed, (), "exhaustive " + fname)
        res.append("%s (%s)" % (variant, ", ".join(ks)))
    return "; ".join(res)


OM = "0x1.fffffffffffffp+1023"
# Hand-written lines and their verdicts: passed; failed, with the keys of caught() that must be
# the failing ones (a tuple), or failed in any way ("failed"); invalid; nonfinite (finite domain,
# not judged).
HAND4 = [
    # neighbor, the table row by row.
    ("next_up binary64 nan -> nan", "passed"),
    ("next_up binary64 -nan -> nan", "passed"),
    ("next_up binary64 nan -> inf", ("neighbor",)),
    ("next_up binary64 inf -> inf", "passed"),
    ("next_down binary64 inf -> %s" % OM, "passed"),
    ("next_down binary64 inf -> inf", ("neighbor",)),
    ("next_up binary64 %s -> inf" % OM, "passed"),
    ("next_up binary64 %s -> %s" % (OM, OM), ("neighbor",)),
    ("next_down binary64 %s -> 0x1.ffffffffffffep+1023" % OM, "passed"),
    ("next_up binary64 0x1p+0 -> 0x1.0000000000001p+0", "passed"),
    ("next_down binary64 0x1p+0 -> 0x1.fffffffffffffp-1", "passed"),
    ("next_down binary64 0x1p+0 -> 0x1.ffffffffffffep-1", ("neighbor",)),
    ("next_up binary64 0x1p-1074 -> 0x1p-1073", "passed"),
    ("next_down binary64 0x1p-1074 -> 0x0p+0", "passed"),
    ("next_down binary64 0x1p-1074 -> -0x0p+0", "passed"),
    ("next_up binary64 0x0p+0 -> 0x1p-1074", "passed"),
    ("next_up binary64 -0x0p+0 -> 0x1p-1074", "passed"),
    ("next_down binary64 0x0p+0 -> -0x1p-1074", "passed"),
    ("next_down binary64 -0x0p+0 -> -0x1p-1074", "passed"),
    # next_down(+0) = -0, a non-step.
    ("next_down binary64 0x0p+0 -> -0x0p+0", ("neighbor",)),
    ("next_up binary64 -0x1p-1074 -> -0x0p+0", "passed"),
    ("next_up binary64 -0x1p-1074 -> 0x0p+0", "passed"),
    ("next_down binary64 -0x1p-1074 -> -0x1p-1073", "passed"),
    # next_up of a negative number moves toward zero.
    ("next_up binary64 -0x1p+0 -> -0x1.fffffffffffffp-1", "passed"),
    ("next_up binary64 -0x1p+0 -> -0x1.0000000000001p+0", ("neighbor",)),
    ("next_down binary64 -0x1p+0 -> -0x1.0000000000001p+0", "passed"),
    ("next_up binary64 -%s -> -0x1.ffffffffffffep+1023" % OM, "passed"),
    ("next_down binary64 -%s -> -inf" % OM, "passed"),
    ("next_down binary64 -%s -> -%s" % (OM, OM), ("neighbor",)),
    # next_up(-inf) = -Omega, not -inf.
    ("next_up binary64 -inf -> -%s" % OM, "passed"),
    ("next_up binary64 -inf -> -inf", ("neighbor",)),
    ("next_down binary64 -inf -> -inf", "passed"),
    # The subnormal boundary: below 2N every step is eta.
    ("next_down binary64 0x1p-1022 -> 0x0.fffffffffffffp-1022", "passed"),
    ("next_up binary64 0x0.fffffffffffffp-1022 -> 0x1p-1022", "passed"),
    ("next_down binary64 0x1p-1021 -> 0x1.fffffffffffffp-1022", "passed"),
    ("next_up binary32 -0x1p-126 -> -0x1.fffffcp-127", "passed"),
    ("next_up fp:3:-3:0 0x1.cp+2 -> inf", "passed"),
    ("next_down fp:3:-3:0 inf -> 0x1.cp+2", "passed"),
    ("next_up binary64 0x1p+0 0x1p+0 -> 0x1p+0", "failed"),
    ("next_up binary64 0x1p+0 -> 0x1.00000000000008p+0", "failed"),
    # The finite domain: no number above Omega there, the line is not judged.
    ("next_up_real binary64 %s -> inf" % OM, "nonfinite"),
    ("next_up_real binary64 %s -> %s" % (OM, OM), "nonfinite"),
    ("next_up_real binary64 -0x1p+0 -> -0x1.fffffffffffffp-1", "passed"),
    ("next_up_real binary64 -0x1p+0 -> -0x1.0000000000001p+0", ("neighbor",)),
    ("next_down_real binary64 -%s -> -inf" % OM, "nonfinite"),
    ("next_down_real binary64 0x0p+0 -> -0x0p+0", ("neighbor",)),
    ("next_up_real binary64 inf -> inf", "invalid"),
    # rounded, two operands: the directed rounding.
    ("add_down_1 binary64 0x1p+0 -0x1p-60 -> 0x1.fffffffffffffp-1", "passed"),
    ("add_down_1 binary64 0x1p+0 -0x1p-60 -> 0x1p+0", ("rounded",)),
    ("add_up_1 binary64 0x1p+0 0x1p-60 -> 0x1.0000000000001p+0", "passed"),
    ("add_up_1 binary64 0x1p+0 0x1p-60 -> 0x1p+0", ("rounded",)),
    ("sub_up_1 binary64 0x1p+0 0x1p-60 -> 0x1p+0", "passed"),
    ("sub_down_1 binary64 0x1p+0 0x1p-60 -> 0x1.fffffffffffffp-1", "passed"),
    ("add_down_1 binary64 0x1p+0 -0x1p+0 -> -0x0p+0", "passed"),
    ("add_up_1 binary64 0x1p+0 -0x1p+0 -> 0x0p+0", "passed"),
    # Overflow, in the format with overflow: Omega for down above Omega, -inf below -Omega.
    ("add_down_1 binary64 %s %s -> %s" % (OM, OM, OM), "passed"),
    ("add_down_1 binary64 %s %s -> inf" % (OM, OM), ("rounded",)),
    ("add_up_1 binary64 %s %s -> inf" % (OM, OM), "passed"),
    ("add_up_1 binary64 %s %s -> %s" % (OM, OM, OM), ("rounded",)),
    ("add_down_1 binary64 -%s -%s -> -inf" % (OM, OM), "passed"),
    ("add_down_1 binary64 -%s -%s -> -%s" % (OM, OM, OM), ("rounded",)),
    ("add_up_1 binary64 -%s -%s -> -%s" % (OM, OM, OM), "passed"),
    ("add_up_1 binary64 -%s -%s -> -inf" % (OM, OM), ("rounded",)),
    # Omega plus half its ulp: to nearest the infinity, rounded down Omega.
    ("add_down_1 binary64 %s 0x1p+970 -> %s" % (OM, OM), "passed"),
    ("add_up_1 binary64 %s 0x1p+970 -> inf" % OM, "passed"),
    # Omega as the second operand, the sum finite: two_sum's NaN error term would mislead here.
    ("add_down_1 binary64 -0x1p+1023 %s -> 0x1.ffffffffffffep+1022" % OM, "passed"),
    ("sub_up_1 binary64 0x1p+1023 %s -> -0x1.ffffffffffffep+1022" % OM, "passed"),
    # Infinite and NaN operands: the value of IEEE 754.
    ("add_down_1 binary64 inf 0x1p+0 -> inf", "passed"),
    ("add_down_1 binary64 inf 0x1p+0 -> %s" % OM, ("rounded",)),
    ("add_down_1 binary64 inf -inf -> nan", "passed"),
    ("add_down_1 binary64 inf -inf -> inf", ("rounded",)),
    ("sub_down_1 binary64 inf inf -> nan", "passed"),
    ("sub_up_1 binary64 inf -inf -> inf", "passed"),
    ("add_up_1 binary64 nan 0x1p+0 -> nan", "passed"),
    ("add_up_1 binary64 0x1p+0 nan -> 0x1p+0", ("rounded",)),
    # bound and rounded with when: mul_down_1, mul_up_1.
    ("mul_down_1 binary64 0x1.8p+1 0x1.4p+2 -> 0x1.ep+3", "passed"),
    ("mul_down_1 binary64 0x1.8p+1 0x1.4p+2 -> 0x1.dffffffffffffp+3", ("rounded",)),
    ("mul_down_1 binary64 0x1.0000000000001p+0 0x1.0000000000001p+0 -> 0x1.0000000000002p+0",
     "passed"),
    ("mul_down_1 binary64 0x1.0000000000001p+0 0x1.0000000000001p+0 -> 0x1.0000000000003p+0",
     ("bound", "rounded")),
    ("mul_up_1 binary64 0x1.0000000000001p+0 0x1.0000000000001p+0 -> 0x1.0000000000003p+0",
     "passed"),
    # Below P = 2^-969: an exact product, one step beyond allowed, two not, the side always.
    ("mul_down_1 binary64 0x1p-1000 0x1p-60 -> 0x1p-1060", "passed"),
    ("mul_down_1 binary64 0x1p-1000 0x1p-60 -> 0x1.fff8p-1061", "passed"),
    ("mul_down_1 binary64 0x1p-1000 0x1p-60 -> 0x1.fffp-1061", ("bound",)),
    ("mul_down_1 binary64 0x1p-1000 0x1p-60 -> 0x1.0004p-1060", ("bound",)),
    ("mul_up_1 binary64 0x1p-1000 0x1p-60 -> 0x1.0004p-1060", "passed"),
    ("mul_up_1 binary64 0x1p-1000 0x1p-60 -> 0x1.0008p-1060", ("bound",)),
    # Underflow to zero: RD of a positive product below eta/2 is 0, one step beyond is -eta.
    ("mul_down_1 binary64 0x1p-600 0x1p-500 -> 0x0p+0", "passed"),
    ("mul_down_1 binary64 0x1p-600 0x1p-500 -> -0x1p-1074", "passed"),
    ("mul_down_1 binary64 0x1p-600 0x1p-500 -> 0x1p-1074", ("bound",)),
    ("mul_up_1 binary64 0x1p-600 0x1p-500 -> 0x1p-1073", "passed"),
    ("mul_up_1 binary64 0x1p-600 -0x1p-500 -> -0x0p+0", "passed"),
    # Exactly P: the condition holds, the exact rounding is required.
    ("mul_down_1 binary64 0x1p-484 0x1p-485 -> 0x1p-969", "passed"),
    ("mul_down_1 binary64 0x1p-484 0x1p-485 -> 0x1.fffffffffffffp-970", ("rounded",)),
    ("mul_down_1 binary64 0x1p-484 0x1.fffffffffffffp-486 -> 0x1.ffffffffffffep-970", "passed"),
    # A zero factor: the product zero, the condition holds.
    ("mul_down_1 binary64 0x0p+0 0x1.8p+1 -> 0x0p+0", "passed"),
    ("mul_down_1 binary64 0x0p+0 0x1.8p+1 -> -0x1p-1074", ("rounded",)),
    ("mul_up_1 binary64 -0x0p+0 %s -> 0x0p+0" % OM, "passed"),
    # 0 * inf, NaN, infinities; overflow on each side.
    ("mul_down_1 binary64 0x0p+0 inf -> nan", "passed"),
    ("mul_down_1 binary64 0x0p+0 inf -> 0x0p+0", ("bound", "rounded")),
    ("mul_down_1 binary64 -0x1p+1 inf -> -inf", "passed"),
    ("mul_up_1 binary64 nan 0x0p+0 -> nan", "passed"),
    ("mul_down_1 binary64 0x1p+600 0x1p+600 -> %s" % OM, "passed"),
    ("mul_down_1 binary64 0x1p+600 0x1p+600 -> inf", ("bound", "rounded")),
    ("mul_up_1 binary64 0x1p+600 0x1p+600 -> inf", "passed"),
    ("mul_up_1 binary64 -0x1p+600 0x1p+600 -> -%s" % OM, "passed"),
    ("mul_up_1 binary64 -0x1p+600 0x1p+600 -> -inf", ("bound", "rounded")),
    ("mul_down_1 binary64 -0x1p+600 0x1p+600 -> -inf", "passed"),
    # The finite domain: an overflow is not judged; below P as above.
    ("mul_down_real binary64 0x1p+600 0x1p+600 -> inf", "nonfinite"),
    ("mul_down_real binary64 0x1p+600 0x1p+600 -> 0x1p+0", "nonfinite"),
    ("mul_down_real binary64 0x1p-1000 0x1p-60 -> 0x1.fff8p-1061", "passed"),
    ("mul_down_real binary64 0x1p-1000 0x1p-60 -> 0x1.fffp-1061", ("bound",)),
    ("mul_up_real binary64 0x1.8p+1 0x1.4p+2 -> 0x1.e000000000001p+3", ("rounded",)),
    ("mul_up_real binary64 0x1p+0 inf -> inf", "invalid"),
    # encloses with exact_when: the scaling of a ball by a power of two.
    ("ball_mul_pow2_1 binary64 0x1p+0 0x1p-3 0x1p-1 -> 0x1p-1 0x1p-4", "passed"),
    ("ball_mul_pow2_1 binary64 0x1p+0 0x1p-3 0x1p-1 -> 0x1p-1 0x1.0000000000002p-4",
     ("encloses:exact_when",)),
    ("ball_mul_pow2_1 binary64 0x1p+0 0x1p-3 0x1p-1 -> 0x1p-1 0x1.fffffffffffffp-5",
     ("encloses:containment", "encloses:exact_when")),
    ("ball_mul_pow2_1 binary64 0x1p+0 0x1p-3 0x1p-1 -> 0x1.0000000000001p-1 0x1.0000000000008p-4",
     ("encloses:exact_when",)),
    # The center 1.5 eta after scaling rounds to 2 eta: not exact, any enclosure passes.
    ("ball_mul_pow2_1 binary64 0x0.0000000000003p-1022 0x0p+0 0x1p-1 -> "
     "0x0.0000000000002p-1022 0x0.0000000000002p-1022", "passed"),
    ("ball_mul_pow2_1 binary64 0x0.0000000000003p-1022 0x0p+0 0x1p-1 -> "
     "0x0.0000000000002p-1022 0x0p+0", ("encloses:containment",)),
    # A zero center, a zero radius: the conditions hold.
    ("ball_mul_pow2_1 binary64 0x0p+0 0x1p-3 0x1p-1 -> 0x0p+0 0x1p-4", "passed"),
    ("ball_mul_pow2_1 binary64 -0x0p+0 0x1p-3 0x1p-1 -> 0x0p+0 0x1.0000000000002p-4",
     ("encloses:exact_when",)),
    ("ball_mul_pow2_1 binary64 0x1p+0 0x0p+0 0x1p+3 -> 0x1p+3 0x0p+0", "passed"),
    ("ball_mul_pow2_1 binary64 0x1p+0 0x0p+0 0x1p+3 -> 0x1p+3 0x0.0000000000002p-1022",
     ("encloses:exact_when",)),
    # The radius scaled to exactly N: the condition is strict, so no exactness is claimed.
    ("ball_mul_pow2_1 binary64 0x1p+0 0x1p-1021 0x1p-1 -> 0x1p-1 0x1.0000000000002p-1022",
     "passed"),
    ("ball_mul_pow2_1 binary64 0x1p+0 0x1.0000000000001p-1021 0x1p-1 -> "
     "0x1p-1 0x1.0000000000003p-1022", ("encloses:exact_when",)),
    ("ball_mul_pow2_1 binary64 0x1p+0 0x1p-3 -0x1p-1 -> -0x1p-1 0x1p-4", "invalid"),
    ("ball_mul_pow2_1 binary64 0x1p+0 -0x1p-3 0x1p-1 -> 0x1p-1 0x1p-4", "invalid"),
    # Two limbs: the second limb scaled to at most N releases the claim of exactness.
    ("ball_mul_pow2_2 binary64 0x1p-900 0x1p-960 0x0p+0 0x1p-50 -> 0x1p-950 0x1p-1010 0x0p+0",
     "passed"),
    ("ball_mul_pow2_2 binary64 0x1p-900 0x1p-960 0x0p+0 0x1p-50 -> "
     "0x1p-950 0x1p-1010 0x0.0000000000002p-1022", ("encloses:exact_when",)),
    ("ball_mul_pow2_2 binary64 0x1p-900 0x1p-960 0x0p+0 0x1p-100 -> "
     "0x1p-1000 0x1p-1060 0x0.0000000000002p-1022", "passed"),
    ("ball_mul_pow2_2 binary64 0x1p-900 0x1p-960 0x0p+0 0x1p-100 -> 0x1p-1000 0x0p+0 0x0p+0",
     ("encloses:containment",)),
    ("ball_mul_pow2_2 binary64 0x1p+0 0x1p-60 0x0p+0 0x1p-1 -> 0x1p-1 0x1p-61 0x0p+0", "passed"),
    ("ball_mul_pow2_2 binary64 0x1p+0 0x1p-60 0x0p+0 0x1p-1 -> 0x1p-1 0x1p-1 0x1p+0",
     ("normalized", "encloses:exact_when")),
    # The full forms: the special states of a ball, and exactness only for a finite ball.
    ("ball_mul_pow2_1_full binary64 0x0p+0 inf 0x1p-1 -> 0x0p+0 inf", "passed"),
    ("ball_mul_pow2_1_full binary64 nan nan 0x1p+1 -> nan nan", "passed"),
    ("ball_mul_pow2_1_full binary64 nan nan 0x1p+1 -> 0x0p+0 inf", ("encloses:B2",)),
    ("ball_mul_pow2_1_full binary64 %s 0x0p+0 0x1p+1 -> 0x0p+0 inf" % OM, "passed"),
    ("ball_mul_pow2_1_full binary64 0x1p+0 0x1p-3 0x1p-1 -> 0x1p-1 0x1p-4", "passed"),
    ("ball_mul_pow2_1_full binary64 0x1p+0 0x1p-3 0x1p-1 -> 0x1p-1 0x1.0000000000002p-4",
     ("encloses:exact_when",)),
    ("ball_mul_pow2_1_full binary64 0x1p+0 0x1p-3 0x1p-1 -> 0x1p-1 0x1.fffffffffffffp-5",
     ("encloses:B3", "encloses:exact_when")),
    # |cx| c <= 2^(qmax+p-2) = 2^1022: B4 asks for a finite ball.
    ("ball_mul_pow2_1_full binary64 0x1p+1021 0x0p+0 0x1p+1 -> 0x0p+0 inf", ("encloses:B4",)),
    ("ball_mul_pow2_1_full binary64 0x1p+1021 0x0p+0 0x1p+1 -> 0x1p+1022 0x0p+0", "passed"),
    ("ball_mul_pow2_2_full binary64 0x1p+0 0x1p-60 0x0p+0 0x1p-1 -> 0x1p-1 0x1p-61 0x0p+0",
     "passed"),
    ("ball_mul_pow2_2_full binary64 0x1p+0 0x1p-60 0x0p+0 0x1p-1 -> 0x1p-1 0x0p+0 0x1p-60",
     ("encloses:exact_when",)),
    ("ball_mul_pow2_2_full binary64 0x0p+0 0x0p+0 inf 0x1p+1 -> 0x0p+0 0x0p+0 inf", "passed"),
    # error with exact_when: mul_pow2_2 within its bound of eta, but not exact.
    ("mul_pow2_2 binary64 0x1p+0 0x1p-60 0x1p-1 -> 0x1p-1 0x1p-61", "passed"),
    ("mul_pow2_2 binary64 0x1p+0 0x0p+0 0x1p-1 -> 0x1p-1 0x0.0000000000001p-1022",
     ("error:exact_when",)),
    ("mul_pow2_2 binary64 0x1p+0 0x1p-60 0x1p-1 -> 0x1p-1 0x1.00000000004p-61",
     ("error:exact_when", "error:bound")),
    # x1 c = 2^-1080 is below N and not zero: no exactness claimed, the error within eta passes.
    ("mul_pow2_2 binary64 0x1p+0 0x1p-60 0x1p-1020 -> 0x1p-1020 0x0p+0", "passed"),
    # two_sum_ord: Omega as an operand, the error term finite.
    ("two_sum_ord binary64 -0x1p+1023 %s -> 0x1.ffffffffffffep+1022 0x0p+0" % OM, "passed"),
    ("two_sum_ord binary64 0x1p+0 0x1p-60 -> 0x1p+0 0x1p-60", "passed"),
    ("two_sum_ord binary64 0x1p-60 0x1p+0 -> 0x1p+0 0x0p+0", "failed"),
]


def _verdict(s):
    t = totals(s)
    if t["invalid"] == 1:
        return "invalid"
    if t["nonfinite"] + t["nonfinite_tail"] == 1:
        return "nonfinite"
    if t["passed"] == 1:
        return "passed"
    return "failed" if t["failed"] == 1 else repr(t)


@test
def judge_wave4(ctx):
    """Hand-written lines with verdicts and statistics worked out by hand: every row of the
    table of next_up and next_down, the planted faults of the wave written out (a negative
    number stepped away from zero, next_up(-inf) = -inf, next_down(+0) = -0, the rounding to
    nearest for a directed sum, the wrong infinity at an overflow, a product on the wrong side,
    two steps beyond, not the exact rounding of a large product, a radius one number too small,
    a radius grown or a center moved where the scaling is exact), each in the entry or the
    statement where it belongs."""
    cl = claims4(ctx)
    for line, want in HAND4:
        s = judge([line], cl)
        got = _verdict(s)
        kname = line.split()[0]
        if isinstance(want, tuple):
            expect(got == "failed" and caught(s, kname) == set(want),
                   "%s: %s %s, want a failure of %s" % (line, got, sorted(caught(s, kname)), want))
            continue
        expect(got == want, "%s: %s, want %s %s" % (line, got, want, failures(s)[:1]))
    # Statistics over the lines that pass, worked out by hand.
    s = judge([ln for ln, w in HAND4 if w == "passed"], cl)
    c = entry_counts(s, "next_up")[0]
    expect(c == {D.ROW_NAN: 2, D.ROW_PINF: 1, D.ROW_OMEGA: 2, D.ROW_POS: 2, D.ROW_ETA: 1,
                 D.ROW_ZERO: 2, D.ROW_NETA: 2, D.ROW_NEG: 2, D.ROW_NOMEGA: 1, D.ROW_NINF: 1,
                 D.STEP_SUBNORMAL: 2, D.STEP_POW2: 1}, "next_up counts %s" % c)
    c = entry_counts(s, "next_down")[0]
    expect(c.get(D.STEP_POW2) == 2 and c.get(D.STEP_SUBNORMAL) == 1, "next_down steps %s" % c)
    c = entry_counts(s, "add_down_1")[0]
    expect(c.get(D.OVER_ABOVE) == 2 and c.get(D.OVER_BELOW) == 1 and c.get(D.NAN_OPERAND) is None
           and c.get(D.INF_OPERAND) == 2 and c.get(D.NAN_FROM_INF) == 1
           and c.get("exact") == 2 and c.get("inexact, != RN") == 3, "add_down_1 counts %s" % c)
    b, r = entry_counts(s, "mul_down_1")
    expect(b.get(D.BOUND_AT) == 8 and b.get(D.BOUND_ONE) == 3 and b.get(D.BOUND_EXACT) == 6
           and b.get(D.BOUND_INEXACT) == 5 and b.get(D.OVER_ABOVE) == 1
           and b.get(D.OVER_BELOW) == 1 and b.get("a non-finite operand") == 2,
           "mul_down_1 bound counts %s" % b)
    expect(r.get(D.WHEN_HOLDS) == 6 and r.get(D.WHEN_FAILS) == 5 and r.get(D.NAN_FROM_INF) == 1
           and r.get(D.INF_OPERAND) == 2, "mul_down_1 rounded counts %s" % r)
    c = entry_counts(s, "ball_mul_pow2_1")[0]
    expect(c.get(D.EXACT_HOLDS) == 3 and sum(v for k, v in c.items()
                                             if k.startswith(D.EXACT_FAILS)) == 2,
           "ball_mul_pow2_1 counts %s" % c)
    return "%d lines" % len(HAND4)


@test
def merging_wave4(ctx):
    """Summaries of two halves of a stream of the wave merge into the summary of the whole."""
    lines = []
    for k in ALL4:
        lines += run4(stream4(ctx, k, "fp:4:-6:1", ctx.n(400, 120)))
    cl = claims4(ctx)
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
                for fld in ("maxima", "minima"):
                    en[fld] = {d: v[0] for d, v in en[fld].items()}
    expect(ja == jb, "merged summary differs from the whole")
    return "%d lines" % len(lines)
