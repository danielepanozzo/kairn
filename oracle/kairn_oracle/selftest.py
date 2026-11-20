"""The oracle's own tests.

They have to be able to catch a broken oracle, so most of them are comparisons with
something independent of the code under test: rounding against a brute-force search over
all numbers of a toy format and against the hardware; the Python reference runner against
the C++ one; injected errors that `check` must flag in the entry where they belong; claims
scaled by known factors whose ratios must scale exactly.
"""

import bisect
import copy
import json
import math
import os
import random
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from fractions import Fraction as Q

from . import fmt as F
from . import gen as G
from . import check as C
from . import refrun
from .claims import Claims, ClaimsError, load_claims, eval_rational

ORACLE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(ORACLE_DIR, "selftest", "claims-wave1.json")
FIXTURE2 = os.path.join(ORACLE_DIR, "selftest", "claims-wave2.json")
CXX_SOURCE = os.path.join(ORACLE_DIR, "selftest", "refrun.cpp")
SCRIPT = os.path.join(ORACLE_DIR, "kairn-oracle")

FIRST_WAVE = ("two_sum", "fast_two_sum", "two_prod", "two_prod_dekker", "add_2_2", "add_2_1",
              "mul_2_2", "mul_2_1", "add_fast_2_2")
TOY = "fp:5:-10:5"


class Skip(Exception):
    pass


TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


class Ctx:
    def __init__(self, workdir, quick, cxx, jobs=None):
        self.workdir = workdir
        self.quick = quick
        self.cxx = cxx
        env = os.environ.get("KAIRN_ORACLE_JOBS", "")
        self.jobs = max(1, jobs or (int(env) if env.isdigit() else 0) or os.cpu_count() or 1)
        self.claims = load_claims(FIXTURE)
        self.claims2 = load_claims(FIXTURE2)
        self.cxx_bin = None
        self.cxx_error = None
        self._streams = {}

    def n(self, full, quick):
        return quick if self.quick else full

    def stream(self, kernel, fmtname, count, strata=None, seed="selftest"):
        key = (kernel, fmtname, count, strata, seed)
        s = self._streams.get(key)
        if s is None:
            claims = self.claims if self.claims.get(kernel) else self.claims2
            g = G.RandomGen(claims.get(kernel), F.parse_format(fmtname), seed,
                            strata.split(",") if strata else None)
            s = self._streams[key] = list(g.lines(0, count))
        return s


def py_run(lines, variant="correct"):
    r = refrun.Runner(variant)
    out = []
    for ln in lines:
        out.extend(r.complete(ln))
    return out


def judge(lines, claims, ignore_min_precision=False, max_examples=5):
    ck = C.Checker(claims, ignore_min_precision, max_examples)
    for ln in lines:
        ck.line(ln)
    return ck.finish()


def entry_failures(summary, kernel, kind=None, label_part=None):
    """Failures per ensures entry of a kernel, summed over formats and tags."""
    n = 0
    for (k, _f, _t), s in summary.keys.items():
        if k != kernel:
            continue
        for e in s.entries:
            if (kind is None or e.kind == kind) and (label_part is None or label_part in e.label):
                n += e.failures
    return n


def totals(summary, kernel=None):
    t = dict.fromkeys(C.COUNTERS, 0)
    for (k, _f, _t), s in summary.keys.items():
        if kernel is None or k == kernel:
            for c in C.COUNTERS:
                t[c] += s.c[c]
    return t


def expect(cond, msg):
    if not cond:
        raise AssertionError(msg)


# ---------------------------------------------------------------------------
# Brute-force references, written from the definitions

def brute_values(p, qmin, qmax):
    s = set()
    for q in range(qmin, qmax + 1):
        for m in range(-(2 ** p - 1), 2 ** p):
            s.add(Q(m) * Q(2) ** q)
    return sorted(s)


def brute_even(x, p, qmin):
    """The significand of x in its canonical representation is even."""
    if x == 0:
        return True
    a, e = abs(x), 0
    while a >= 2:
        a /= 2
        e += 1
    while a < 1:
        a *= 2
        e -= 1
    m = abs(x) / Q(2) ** max(e - p + 1, qmin)
    return m.numerator % 2 == 0


class BruteRN:
    def __init__(self, p, qmin, qmax):
        self.p, self.qmin, self.qmax = p, qmin, qmax
        self.vals = brute_values(p, qmin, qmax)
        self.big = Q(2) ** (qmax + p)       # rounds to infinity; its significand is even
        self.ext = [-self.big] + self.vals + [self.big]

    def __call__(self, t):
        if t <= -self.big:
            return -math.inf
        if t >= self.big:
            return math.inf
        i = bisect.bisect_left(self.ext, t)
        if self.ext[i] == t:
            r = t
        else:
            lo, hi = self.ext[i - 1], self.ext[i]
            if t - lo != hi - t:
                r = lo if t - lo < hi - t else hi
            else:
                ev_lo = abs(lo) == self.big or brute_even(lo, self.p, self.qmin)
                r = lo if ev_lo else hi
        if abs(r) == self.big:
            return math.inf if r > 0 else -math.inf
        return r


TOY_ROUNDING_FORMATS = [(2, -2, 2), (3, -3, 2), (4, -6, 3), (5, -4, 1), (4, 2, 5), (3, -1, 6)]


# ---------------------------------------------------------------------------

@test
def literals(ctx):
    """Hexadecimal literals parse exactly and print exactly."""
    cases = {
        "0x1p+0": (1, 0), "0x1.8p-1": (24, -5), "-0x0p+0": (0, 0), "0x0p+0": (0, 0),
        "0x0.0000000000001p-1022": (1, -1074), "0x1P-1074": (1, -1074), "0x.8p1": (8, -3),
        "0x1.p0": (1, 0), "+0x1.fffffffffffffp+1023": (0x1fffffffffffff, 1023 - 52),
        "0X1.Ap+2": (0x1a, 2 - 4),
    }
    for tok, (m, e) in cases.items():
        got = F.parse_dyadic(tok)
        expect(type(got) is tuple and Q(got[0]) * Q(2) ** got[1] == Q(m) * Q(2) ** e,
               "parse %r gave %r" % (tok, got))
    for tok in ("1.0", "0x1", "0xp1", "", "0x1.8", "0x1p", "0x1p+1.5", "0x1 p+0", "1e5", "0x1g",
                "--0x1p+0"):
        try:
            F.parse_dyadic(tok)
        except F.LimbError:
            continue
        raise AssertionError("malformed literal %r accepted" % tok)
    for tok, v in (("inf", F.POS_INF), ("-inf", F.NEG_INF), ("nan", F.NAN), ("-nan", F.NAN),
                   ("+inf", F.POS_INF), ("INF", F.POS_INF)):
        expect(F.parse_dyadic(tok) == v, "non-finite %r" % tok)
    rnd = random.Random(1)
    f64 = F.parse_format("binary64")
    xs = [5e-324, 2.2250738585072014e-308, 1.7976931348623157e308, 1.0, -0.1, 2.0 ** -1060 * 3]
    xs += [rnd.choice([-1, 1]) * math.ldexp(rnd.random(), rnd.randint(-1080, 1024))
           for _ in range(ctx.n(20000, 2000))]
    for x in xs:
        if not math.isfinite(x):
            continue
        d = F.parse_dyadic(x.hex())
        expect(Q(d[0]) * Q(2) ** d[1] == Q(x), "parse(float.hex(%r))" % x)
        n = F.to_fixed(f64, d)
        expect(float.fromhex(F.to_hex(n, f64.qmin)) == x, "to_hex(%r)" % x)
        expect(F.parse_limb(f64, F.to_hex(n, f64.qmin)) == n, "round trip %r" % x)
    # Guards against hostile exponents.
    expect(F.parse_limb(f64, "0x1p+999999999") == F.OUTSIDE, "huge exponent")
    expect(F.parse_limb(f64, "0x1p-999999999") == F.OUTSIDE, "tiny exponent")
    return "%d literals" % len(xs)


@test
def exact_compare(ctx):
    """The checker's comparison of fractions, against Fraction, zeros, signs and infinity
    included."""
    rnd = random.Random(5)
    n = ctx.n(200000, 20000)
    for _ in range(n):
        a = (rnd.getrandbits(rnd.randint(0, 300)) * rnd.choice([1, 1, -1]),
             rnd.getrandbits(rnd.randint(0, 300)) or 1)
        b = (rnd.getrandbits(rnd.randint(0, 300)) * rnd.choice([1, 1, -1]),
             rnd.getrandbits(rnd.randint(0, 300)) or 1)
        expect(C._gt(a, b) == (Q(*a) > Q(*b)), "_gt%r" % ((a, b),))
    inf = (1, 0)
    expect(C._gt(inf, (5, 3)) and not C._gt((5, 3), inf) and not C._gt(inf, inf), "infinity")
    expect(C._gt((1, 3), (0, 1)) and not C._gt((0, 1), (0, 7)), "zeros")
    # The decimals of the report, against Fraction's own formatting where it exists (3.12+).
    try:
        format(Q(1, 3), ".6g")
        for _ in range(ctx.n(20000, 2000)):
            a = (rnd.getrandbits(rnd.randint(1, 200)) * rnd.choice([1, -1]),
                 rnd.getrandbits(rnd.randint(1, 200)) or 1)
            expect(float(C.frac_dec(a)) == float(format(Q(*a), ".6g")), "frac_dec%r" % (a,))
    except (TypeError, ValueError):
        pass
    return "%d comparisons" % n


@test
def membership(ctx):
    """Membership in a format, against the brute-force set of all its numbers."""
    f64 = F.parse_format("binary64")
    om = f64.omega
    expect(F.is_member(f64, om) and not F.is_member(f64, om + (1 << 971 + 1074)), "Omega")
    expect(F.fixed_hex(f64, om) == "0x1.fffffffffffffp+1023", "Omega literal")
    expect(F.is_member(f64, 1) and F.parse_limb(f64, "0x1p-1075") == F.OUTSIDE, "eta")
    expect(not F.is_member(f64, (1 << 53) + 1) and F.is_member(f64, (1 << 53) - 1), "54 bits")
    expect(f64.lam == 1 << 52 and F.fixed_hex(f64, f64.lam) == "0x1p-1022", "lambda")
    n = 0
    for p, qmin, qmax in TOY_ROUNDING_FORMATS:
        f = F.Format(p, qmin, qmax)
        vals = brute_values(p, qmin, qmax)
        eta = Q(2) ** qmin
        expect([Q(v) * eta for v in F.all_values(f)] == vals, "all_values %s" % f.name)
        fixed = set(F.all_values(f))
        top = max(fixed)
        for v in range(-top - 3, top + 4):
            expect(F.is_member(f, v) == (v in fixed), "is_member(%d) in %s" % (v, f.name))
            n += 1
    return "%d membership tests" % n


@test
def rounding_toy(ctx):
    """Both rounding implementations (checker and reference runner) against a brute-force
    nearest search on every multiple of eta/8 across the whole range of toy formats,
    overflow included."""
    pts = 0
    for p, qmin, qmax in TOY_ROUNDING_FORMATS:
        f = F.Format(p, qmin, qmax)
        ar = refrun.Arith((p, qmin, qmax))
        br = BruteRN(p, qmin, qmax)
        eta = Q(2) ** qmin
        step = eta / 8
        lim = int((br.big + 4 * eta) / step)
        for j in range(-lim, lim + 1):
            r = br(j * step)
            want = r if isinstance(r, float) else int(r / eta)
            got = F.rn(f, j, qmin - 3)
            got = got if type(got) is int else (math.inf if got == F.POS_INF else -math.inf)
            got2 = ar.round(j, 3)
            expect(got == want, "checker RN(%s) = %r, want %r in %s" % (j * step, got, want, f.name))
            expect(got2 == want, "runner RN(%s) = %r, want %r in %s" % (j * step, got2, want, f.name))
            pts += 1
    return "%d points in %d formats" % (pts, len(TOY_ROUNDING_FORMATS))


@test
def rounding_hardware(ctx):
    """binary64 rounding of sums, products and FMAs against the machine's own arithmetic."""
    if not hasattr(math, "fma"):
        raise Skip("math.fma needs Python 3.13")
    f = F.parse_format("binary64")
    ar = refrun.Arith(f.triple)
    rnd = random.Random(7)

    def draw():
        k = rnd.randrange(6)
        if k == 0:
            return rnd.choice([-1, 1]) * math.ldexp(rnd.getrandbits(53), rnd.randint(-1126, -1074))
        if k == 1:
            return rnd.choice([-1, 1]) * math.ldexp(1 + rnd.random(), rnd.randint(-1022, -900))
        if k == 2:
            return rnd.choice([-1, 1]) * math.ldexp(1 + rnd.random(), rnd.randint(900, 1023))
        if k == 3:
            return rnd.choice([-1, 1]) * math.ldexp(rnd.getrandbits(rnd.randint(1, 53)) | 1,
                                                    rnd.randint(-80, 60))
        return rnd.choice([-1, 1]) * math.ldexp(1 + rnd.random(), rnd.randint(-1074, 1023))

    def fx(x):
        return F.to_fixed(f, F.parse_dyadic(x.hex()))

    def same(r, x):
        if math.isinf(x):
            return r == (F.POS_INF if x > 0 else F.NEG_INF) or r == x
        return r == fx(x)

    n = ctx.n(30000, 3000)
    for _ in range(n):
        a, b, c = draw(), draw(), draw()
        A, B, Cc = fx(a), fx(b), fx(c)
        fused = A * B + (Cc << 1074)
        try:
            hwf = math.fma(a, b, c)
        except OverflowError:
            # Python raises where IEEE returns an infinity with the sign of the exact value.
            hwf = math.inf if fused > 0 else -math.inf
        for exact_n, s, hw in ((A + B, f.qmin, a + b), (A * B, 2 * f.qmin, a * b),
                               (fused, 2 * f.qmin, hwf)):
            r = F.rn(f, exact_n, s)
            expect(same(r, hw), "checker RN differs from hardware for %r %r %r" % (a, b, c))
            r2 = ar.round(exact_n, f.qmin - s)
            expect(same(r2, hw), "runner RN differs from hardware for %r %r %r" % (a, b, c))
    # The overflow threshold: Omega + ulp(Omega)/2 is infinite, just below it is Omega.
    half = 1 << (971 - 1 + 1074)
    expect(F.rn(f, f.omega + half, f.qmin) == F.POS_INF, "overflow at the threshold")
    expect(F.rn(f, 2 * (f.omega + half) - 1, f.qmin - 1) == f.omega, "just below the threshold")
    return "%d triples" % n


@test
def neighbors(ctx):
    """succ, pred and ulp against the sorted list of all numbers of toy formats."""
    for p, qmin, qmax in TOY_ROUNDING_FORMATS:
        f = F.Format(p, qmin, qmax)
        vals = F.all_values(f)
        for i, v in enumerate(vals):
            nxt = vals[i + 1] if i + 1 < len(vals) else F.POS_INF
            prv = vals[i - 1] if i > 0 else F.NEG_INF
            expect(F.succ(f, v) == nxt, "succ(%d) in %s" % (v, f.name))
            expect(F.pred(f, v) == prv, "pred(%d) in %s" % (v, f.name))
            if v > 0 and type(nxt) is int:
                expect(F.ulp(f, v) == nxt - v, "ulp(%d) in %s" % (v, f.name))
    return "%d formats" % len(TOY_ROUNDING_FORMATS)


@test
def claims_reading(ctx):
    """The fixture loads and its instances agree with c and t; the vocabulary is closed."""
    ctx.claims.check_instances()
    expect(set(ctx.claims.kernels) == set(FIRST_WAVE), "fixture kernels")
    u = Q(1, 2 ** 53)
    expect(eval_rational("3/(1-4*u)", u) == 3 / (1 - 4 * u), "eval 3/(1-4u)")
    expect(eval_rational("2^-3 + u**2", u) == Q(1, 8) + u * u, "eval powers")
    expect(eval_rational("-(1/2)", u) == Q(-1, 2), "eval unary")
    raw = json.load(open(FIXTURE))

    def must_fail(mutate, what, kernel="add_2_2"):
        # A malformed kernel is set aside with its reason; the others stay readable.
        d = copy.deepcopy(raw)
        mutate(d)
        try:
            c = Claims(d)
        except ClaimsError:
            return
        expect(kernel in c.broken and c.get(kernel) is None, "claims with %s accepted" % what)
        expect(c.get("mul_2_2") is not None or kernel == "mul_2_2",
               "one malformed kernel made the others unreadable")

    def k(d, name):
        return next(x for x in d["kernels"] if x["name"] == name)

    must_fail(lambda d: k(d, "add_2_2")["instances"]["binary64"].update(rel="3/81129638414606645666991986180095"),
              "a listed instance that disagrees with c")
    must_fail(lambda d: k(d, "add_2_2")["requires"].append("finite(x)"), "an unknown requirement")
    must_fail(lambda d: k(d, "add_2_2")["ensures"].append({"kind": "monotone", "of": "z"}),
              "an unknown ensures kind")
    must_fail(lambda d: k(d, "add_2_2")["ensures"][1].update(when="sometimes"), "an unknown condition")
    must_fail(lambda d: k(d, "add_2_2")["ensures"][1].update(form="Q"), "an unknown form")
    must_fail(lambda d: k(d, "add_2_2").update(value="x/y"), "an unknown value")
    must_fail(lambda d: k(d, "add_2_2")["ensures"][0].update(of="w"), "an unknown output")
    must_fail(lambda d: k(d, "add_2_2")["ensures"][1].update(extra=1), "an unknown entry field")
    must_fail(lambda d: d.update(schema=2), "another schema")
    must_fail(lambda d: d["kernels"].append(copy.deepcopy(k(d, "add_2_2"))), "a kernel listed twice")
    # A bare input name is the identity (the value split approximates).
    d = copy.deepcopy(raw)
    d["kernels"].append({"name": "split", "inputs": [{"name": "a", "limbs": 1}],
                         "outputs": [{"name": "ah", "limbs": 1}, {"name": "al", "limbs": 1}],
                         "value": "a", "requires": [],
                         "ensures": [{"kind": "error", "of": ["ah", "al"], "form": "R", "c": "0",
                                      "k": 1, "t": "0", "when": None}]})
    c = Claims(d)
    expect(c.get("split") is not None and c.get("split").value == ("=", "a", "a"), "identity value")
    lines = list(G.RandomGen(c.get("split"), F.parse_format("binary64"), "s").lines(0, 400))
    s = judge(py_run(lines), c)
    expect(not s.failed() and totals(s)["judged"] > 300, "split: %r" % totals(s))
    s = judge(["split binary64 0x1.8p+0 -> 0x1p+0 0x1p-2"], c)
    expect(s.failed(), "a wrong split result passed")
    return "fixture consistent; 10 malformed variants set aside; identity value read"


@test
def gen_counter_based(ctx):
    """Case i is the same whether generated alone or in a run, and seeds matter."""
    rnd = random.Random(3)
    n = 0
    for kname in FIRST_WAVE:
        for fname in ("binary64", TOY):
            g = G.RandomGen(ctx.claims.get(kname), F.parse_format(fname), "cb")
            run = list(g.lines(100, 200))[1:-1]
            for _ in range(8):
                i = rnd.randrange(100, 300)
                alone = list(G.RandomGen(ctx.claims.get(kname), F.parse_format(fname), "cb")
                             .lines(i, 1))[1]
                expect(alone == run[i - 100], "case %d of %s %s" % (i, kname, fname))
                n += 1
            other = list(G.RandomGen(ctx.claims.get(kname), F.parse_format(fname), "cb2")
                         .lines(100, 200))[1:-1]
            expect(sum(a != b for a, b in zip(run, other)) > 150, "seed has no effect")
    ex = G.ExhaustiveGen(ctx.claims.get("add_2_1"), F.parse_format("fp:3:-3:2"))
    full = list(ex.lines(0, ex.total))
    expect(list(ex.lines(57, 1))[1] == full[58], "exhaustive case 57")
    return "%d cases regenerated" % n


@test
def gen_valid(ctx):
    """Every generated case satisfies its kernel's requirements, in every stratum."""
    n = 0
    for fname in ("binary64", "binary32", TOY, "fp:4:-6:3"):
        for kname in FIRST_WAVE:
            lines = ctx.stream(kname, fname, ctx.n(2400, 480))
            s = judge(py_run(lines), ctx.claims, ignore_min_precision=True)
            t = totals(s)
            expect(t["invalid"] == 0, "%s %s: %d invalid generated cases: %s" % (
                kname, fname, t["invalid"],
                [ex for st in s.keys.values() for ex in st.examples["invalid"]][:2]))
            tags = {k[2] for k in s.keys}
            expect(tags == set(G.STRATA), "%s %s: strata %s" % (kname, fname, sorted(tags)))
            n += t["cases"]
    return "%d cases" % n


@test
def exhaustive_counts(ctx):
    """The enumeration of a tiny format against a brute-force count from the definition."""
    p, qmin, qmax = 3, -3, 2
    f = F.Format(p, qmin, qmax)
    br = BruteRN(p, qmin, qmax)
    vals = br.vals
    eta = Q(2) ** qmin
    pairs = [(a, b) for a in vals for b in vals if br(a + b) == a and (a != 0 or b == 0)]
    pairs = sorted({(a, b if b != 0 else Q(0)) for a, b in pairs})
    gp = sorted((Q(a) * eta, Q(b) * eta) for a, b in G.normalized_pairs(f))
    expect(gp == pairs, "normalized pairs: %d enumerated, %d by brute force" % (len(gp), len(pairs)))
    for kname, want in (("add_2_2", len(pairs) ** 2), ("add_2_1", len(pairs) * len(vals)),
                        ("two_sum", len(vals) ** 2)):
        g = G.ExhaustiveGen(ctx.claims.get(kname), f)
        expect(g.total == want, "%s total %d, want %d" % (kname, g.total, want))
        lines = list(g.lines(0, g.total))[1:-1]
        expect(len(set(lines)) == want, "%s: duplicate or missing lines" % kname)
    g = G.ExhaustiveGen(ctx.claims.get("fast_two_sum"), f)
    lines = list(g.lines(0, g.total))[1:-1]
    want = sum(1 for a in vals for b in vals if abs(a) >= abs(b))
    expect(len(lines) == want, "fast_two_sum emits %d, want %d" % (len(lines), want))
    g = G.ExhaustiveGen(ctx.claims.get("add_2_2"), f, ["x.lead=0:1", "x.sign=+"])
    want = sum(1 for a, b in pairs if a > 0 and 1 <= a < 4) * len(pairs)
    expect(g.total == want, "restricted total %d, want %d" % (g.total, want))
    return "%d normalized pairs in %s" % (len(pairs), f.name)


@test
def correct_runner_toy_exhaustive(ctx):
    """The correct reference runner passes on every case of two tiny formats.  The products
    of two 2-limb numbers are below their min_precision there and are covered by the random
    tests instead."""
    out = []
    for fname, kernels in (("fp:3:-3:2", ("two_sum", "fast_two_sum", "two_prod",
                                         "two_prod_dekker", "add_2_2", "add_2_1",
                                         "add_fast_2_2")),
                           ("fp:4:-4:2", ("two_sum", "fast_two_sum", "two_prod",
                                         "two_prod_dekker", "add_2_1", "mul_2_1"))):
        f = F.parse_format(fname)
        for kname in kernels:
            g = G.ExhaustiveGen(ctx.claims.get(kname), f)
            s = judge(py_run(g.lines(0, g.total)), ctx.claims)
            t = totals(s)
            expect(t["failed"] == 0 and not s.stream_errors,
                   "correct runner flagged on %s %s: %s" % (
                       kname, fname, [e for st in s.keys.values() for e in st.examples["failure"]][:2]))
            expect(t["judged"] > 0, "nothing judged for %s %s" % (kname, fname))
            out.append(t["cases"])
    return "%d cases" % sum(out)


def build_cxx(ctx):
    if ctx.cxx_bin or ctx.cxx_error:
        return ctx.cxx_bin
    cands = [ctx.cxx] if ctx.cxx else [os.environ.get("CXX"), "c++", "clang++", "g++"]
    cxx = next((shutil.which(c) for c in cands if c and shutil.which(c)), None)
    if cxx is None:
        ctx.cxx_error = "no C++ compiler found (tried %s); set CXX or pass --cxx" % ", ".join(
            c for c in cands if c)
        return None
    exe = os.path.join(ctx.workdir, "refrun-cxx" + (".exe" if os.name == "nt" else ""))
    base = os.path.basename(cxx).lower()
    if base in ("cl", "cl.exe", "clang-cl", "clang-cl.exe"):
        # MSVC does not contract under /fp:precise unless /fp:contract is given.
        cmd = [cxx, "/nologo", "/std:c++17", "/O2", "/fp:precise", "/EHsc", "/Fe" + exe,
               "/Fo" + os.path.join(ctx.workdir, "refrun-cxx.obj"), CXX_SOURCE]
    else:
        cmd = [cxx, "-std=c++17", "-O2", "-ffp-contract=off", "-fno-fast-math", "-o", exe,
               CXX_SOURCE]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        ctx.cxx_error = "compiling the C++ runner failed: %s\n%s" % (" ".join(cmd), r.stderr[-2000:])
        return None
    ctx.cxx_bin = exe
    return exe


def cxx_constants():
    """--const arguments for the Ball kernels of the C++ runner, computed by the Python one."""
    args = []
    for fname in ("binary64", "binary32"):
        ar = refrun.Arith(F.parse_format(fname).triple)
        for center in sorted(set(refrun.CENTER_KERNEL.values())):
            U, V = refrun.ball_constants(ar, center, refrun.DEFAULT_CENTER_CLAIMS)
            args += ["--const", "%s.%s.U=%s" % (fname, center, ar.write(U)),
                     "--const", "%s.%s.V=%s" % (fname, center, ar.write(V))]
        # E, G and H of the second radius design, per Ball kernel.
        for kname in sorted(refrun.RADIUS2):
            for which, v in zip("EGH", refrun.radius2_constants(ar, kname)):
                args += ["--const", "%s.%s.%s=%s" % (fname, kname, which, ar.write(v))]
    return args


def cxx_run(ctx, lines, variant="correct", radius="first"):
    exe = build_cxx(ctx)
    if exe is None:
        raise Skip(ctx.cxx_error)
    r = subprocess.run([exe, "--variant", variant, "--radius", radius] + cxx_constants(),
                       input="\n".join(lines) + "\n", capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError("C++ runner failed: %s" % r.stderr[-500:])
    return r.stdout.splitlines()


def _value(tok):
    if tok.lower() in ("nan", "-nan", "+nan"):
        return "nan"
    if tok.lower() in ("inf", "+inf", "-inf"):
        return tok.lower().lstrip("+")
    return float.fromhex(tok) + 0.0


@test
def cxx_agrees(ctx):
    """The C++ runner (hardware, compiled without contraction) passes, and its results equal
    the Python runner's on every case (signs of zero aside)."""
    n = 0
    for fname in ("binary64", "binary32"):
        for kname in FIRST_WAVE:
            lines = ctx.stream(kname, fname, ctx.n(3000, 600))
            hw = cxx_run(ctx, lines)
            py = py_run(lines)
            expect(len(hw) == len(py), "line counts differ for %s %s" % (kname, fname))
            for a, b in zip(hw, py):
                if a.startswith("#"):
                    expect(a == b, "comment not copied")
                    continue
                la, _, ra = a.partition(" -> ")
                lb, _, rb = b.partition(" -> ")
                expect(la == lb, "request part changed: %r" % a)
                expect([_value(t) for t in ra.split()] == [_value(t) for t in rb.split()],
                       "C++ and Python runners differ:\n  %s\n  %s" % (a, b))
                n += 1
            s = judge(hw, ctx.claims)
            expect(totals(s)["failed"] == 0 and not s.stream_errors,
                   "C++ correct runner flagged on %s %s: %s" % (kname, fname, [
                       e for st in s.keys.values() for e in st.examples["failure"]][:2]))
    return "%d cases identical" % n


def _variant_suite(ctx, run, fname, count, label):
    """Inject each error with the given runner and demand that check flags it where it
    belongs, and only there."""
    claims = ctx.claims
    res = []

    def run_judge(kernels, variant, strata=None, n=count):
        lines = []
        for k in kernels:
            lines.extend(ctx.stream(k, fname, n, strata))
        done = run(lines, variant)
        return done, judge(done, claims)

    # Control: the correct runner on the same streams.
    _, s = run_judge(FIRST_WAVE, "correct")
    expect(totals(s)["failed"] == 0, "%s: correct runner flagged: %s" % (label, [
        e for st in s.keys.values() for e in st.examples["failure"]][:2]))

    _, s = run_judge(("two_sum", "fast_two_sum", "two_prod"), "ulp-rare", n=count * 2)
    t = totals(s)
    expect(entry_failures(s, "two_sum", "error") > 0, "%s ulp-rare: two_sum not flagged" % label)
    expect(t["failed"] < t["judged"] / 20, "%s ulp-rare: too many failures for a rare error" % label)
    res.append("ulp-rare %d/%d" % (t["failed"], t["cases"]))

    _, s = run_judge(("add_2_2", "add_2_1", "mul_2_2", "mul_2_1", "add_fast_2_2"), "not-normalized")
    for k in ("add_2_2", "add_2_1", "mul_2_2", "mul_2_1", "add_fast_2_2"):
        expect(entry_failures(s, k, "normalized") > 0, "%s not-normalized: %s not flagged" % (label, k))
        expect(entry_failures(s, k, "error") == 0,
               "%s not-normalized: %s error entry flagged although the value is unchanged" % (label, k))
    res.append("not-normalized %d" % totals(s)["failed"])

    _, s = run_judge(("mul_2_2", "mul_2_1"), "mul-drop-cross")
    for k in ("mul_2_2", "mul_2_1"):
        expect(entry_failures(s, k, "error") > 0, "%s mul-drop-cross: %s not flagged" % (label, k))
    res.append("mul-drop-cross %d" % totals(s)["failed"])

    # In add_2_2 the skipped renormalization breaks the invariant only when the leading
    # limbs cancel and vl sits on a tie; random sampling meets that about once in 5000
    # cases, so add_2_2 is demanded by the exhaustive test below and not here.
    _, s = run_judge(("add_2_1", "add_fast_2_2"), "add-skip-renorm")
    for k in ("add_2_1", "add_fast_2_2"):
        expect(entry_failures(s, k, "normalized") > 0, "%s add-skip-renorm: %s not flagged" % (label, k))
    res.append("add-skip-renorm %d" % totals(s)["failed"])

    _, s = run_judge(("two_sum",), "two-sum-zero")
    expect(entry_failures(s, "two_sum", "error") > 0, "%s two-sum-zero: not flagged" % label)
    expect(entry_failures(s, "two_sum", "leading_rounded") == 0, "%s two-sum-zero: wrong entry" % label)
    res.append("two-sum-zero %d" % totals(s)["failed"])

    done, s = run_judge(FIRST_WAVE, "corrupt-input")
    marked = sum(1 for ln in done if ln == "# refrun: corrupted input")
    t = totals(s)
    expect(marked > 0, "%s corrupt-input: no line corrupted" % label)
    expect(t["invalid"] == marked and t["failed"] == 0,
           "%s corrupt-input: %d lines corrupted, %d invalid, %d failed" % (
               label, marked, t["invalid"], t["failed"]))
    res.append("corrupt-input %d invalid" % marked)
    return res


@test
def injected_python(ctx):
    """Errors injected into the Python runner, on a toy format and on binary64."""
    res = []
    for fname, n in ((TOY, ctx.n(3000, 800)), ("binary64", ctx.n(3000, 800))):
        res += _variant_suite(ctx, py_run, fname, n, "python %s" % fname)
        # An error confined to the subnormal range: caught there, and nowhere else.
        under = ctx.stream("two_prod", fname, n, "underflow")
        s = judge(py_run(under, "subnormal-trunc"), ctx.claims)
        expect(entry_failures(s, "two_prod", "leading_rounded") > 0,
               "subnormal-trunc not flagged on %s" % fname)
        close = ctx.stream("mul_2_2", fname, n, "close") + ctx.stream("two_prod", fname, n, "close")
        s = judge(py_run(close, "subnormal-trunc"), ctx.claims)
        expect(totals(s)["failed"] == 0, "subnormal-trunc flagged outside the subnormal range")
        res.append("subnormal-trunc ok")
    return "; ".join(res)


@test
def injected_cxx(ctx):
    """Errors injected into the C++ runner on binary64 and binary32."""
    res = []
    for fname in ("binary64", "binary32"):
        n = ctx.n(3000, 800)
        res += _variant_suite(ctx, lambda lines, v: cxx_run(ctx, lines, v), fname, n,
                              "C++ %s" % fname)
        under = ctx.stream("two_sum", fname, n, "underflow")
        s = judge(cxx_run(ctx, under, "subnormal-flush"), ctx.claims)
        expect(entry_failures(s, "two_sum", "leading_rounded") > 0, "subnormal-flush not flagged")
        close = ctx.stream("add_2_2", fname, n, "close")
        s = judge(cxx_run(ctx, close, "subnormal-flush"), ctx.claims)
        expect(totals(s)["failed"] == 0, "subnormal-flush flagged outside the subnormal range")
        res.append("subnormal-flush ok")
    return "; ".join(res)


@test
def injected_exhaustive(ctx):
    """Errors that random sampling rarely meets, demanded on every case of a tiny format."""
    f = F.parse_format("fp:3:-3:2")
    res = []
    for kname, variant, kind in (("add_2_2", "add-skip-renorm", "normalized"),
                                 ("add_2_2", "not-normalized", "normalized"),
                                 ("two_sum", "two-sum-zero", "error"),
                                 ("two_prod", "subnormal-trunc", "leading_rounded"),
                                 ("two_sum", "ulp-rare", "error")):
        g = G.ExhaustiveGen(ctx.claims.get(kname), f)
        s = judge(py_run(g.lines(0, g.total), variant), ctx.claims)
        n = entry_failures(s, kname, kind)
        expect(n > 0, "%s %s not flagged on every case of %s" % (variant, kname, f.name))
        res.append("%s/%s %d" % (kname, variant, n))
    return "; ".join(res)


def scaled_claims(factor):
    """The fixture with every error bound multiplied by factor (c, t and instances)."""
    d = json.load(open(FIXTURE))
    for k in d["kernels"]:
        for e in k["ensures"]:
            if e["kind"] == "error":
                e["c"] = "(%s)*%s" % (e["c"], factor)
                e["t"] = str(Q(e["t"]) * factor)
        for fmtname, v in k["instances"].items():
            for it in (v if isinstance(v, list) else [v]):
                it["rel"] = str(Q(it["rel"]) * factor)
                it["abs"] = str(Q(it["abs"]) * factor)
    return Claims(d, "<fixture scaled by %s>" % factor)


@test
def scaled_bounds(ctx):
    """With every bound halved a correct runner must fail; with every bound multiplied by
    1024 it must pass; and every largest ratio must scale by exactly the inverse factor."""
    lines = []
    for fname in (TOY, "binary64"):
        for k in FIRST_WAVE:
            lines += ctx.stream(k, fname, ctx.n(3000, 800))
    for fname in ("fp:5:-6:3",):
        for k in ("add_2_2", "mul_2_2", "add_fast_2_2", "add_2_1", "mul_2_1"):
            lines += ctx.stream(k, fname, ctx.n(6000, 1500), "close,underflow,cancel")
    done = py_run(lines)
    base = judge(done, ctx.claims)
    expect(totals(base)["failed"] == 0, "correct runner flagged")
    half = judge(done, scaled_claims(Q(1, 2)))
    big = judge(done, scaled_claims(1024))
    expect(half.failed(), "bounds halved: a correct runner passed")
    expect(not big.failed(), "bounds times 1024: a correct runner failed")
    flagged = []
    for key, sb in base.keys.items():
        for eb, eh, eg in zip(sb.entries, half.keys[key].entries, big.keys[key].entries):
            if eb.kind != "error" or eb.max_ratio is None or eb.max_ratio[1] == 0:
                continue
            rb = Q(*eb.max_ratio)
            expect(Q(*eh.max_ratio) == 2 * rb, "%s %s: halved ratio %s, base %s" % (
                key, eb.label, Q(*eh.max_ratio), rb))
            expect(Q(*eg.max_ratio) == rb / 1024, "%s %s: enlarged ratio" % (key, eb.label))
            if rb > Q(1, 2):
                expect(eh.failures > 0, "%s %s: ratio %s > 1/2 but halved bound not violated" % (
                    key, eb.label, rb))
                flagged.append(key[0])
    expect(flagged, "no entry reached half of its bound, so halving tested nothing")
    return "halved bounds violated for %s" % ", ".join(sorted(set(flagged)))


@test
def check_robustness(ctx):
    """Malformed, truncated and non-finite streams are reported, not passed."""
    cl = ctx.claims
    good = py_run(ctx.stream("add_2_2", "binary64", 20))
    body = [ln for ln in good if not ln.startswith("#")]
    one = body[0]
    left, _, right = one.partition(" -> ")
    bad = {
        "no arrow": left,
        "too few outputs": left + " -> " + right.split()[0],
        "malformed output": left + " -> 0x1.8 " + right.split()[1],
        "unknown kernel": one.replace("add_2_2", "add_9_9", 1),
        "unknown format": one.replace("binary64", "binary65", 1),
        "double space": left + " ->  " + right,
    }
    for why, ln in bad.items():
        s = judge([ln], cl)
        expect(totals(s)["failed"] == 1, "%s: not a failure" % why)
    # An output limb that is not a number of the format.  A leading limb outside the format
    # also breaks the invariant, so the case only this check can catch is a second limb with
    # one bit too many whose value is within the bound.
    s = judge(["two_sum fp:4:-6:3 0x1p+0 0x1p-5 -> 0x1.08p+0 0x0p+0"], cl)
    expect(totals(s)["failed"] == 1, "output outside the toy format accepted")
    s = judge(["add_2_2 binary64 0x1p+0 0x0p+0 0x1p-60 0x0p+0 -> 0x1p+0 0x1.00000000000008p-60"], cl)
    expect(totals(s)["failed"] == 1, "a 54-bit second limb accepted")
    s = judge(["add_2_1 fp:5:-10:5 0x1p+0 0x0p+0 0x1.1p-6 -> 0x1p+0 0x1.1p-6",
               "add_2_1 fp:5:-10:5 0x1p+0 0x0p+0 0x1.18p-6 -> 0x1p+0 0x1.18p-6"], cl)
    expect(totals(s)["passed"] == 1 and totals(s)["invalid"] == 1, "toy second limb")
    s = judge(["add_2_2 fp:5:-10:5 0x1p+0 0x0p+0 0x1.1p-6 0x0p+0 -> 0x1p+0 0x1.18p-6"], cl)
    expect(totals(s)["failed"] == 1, "a second limb outside the toy format accepted")
    # Wrong but well-formed: two_sum with a wrong error term.
    s = judge(["two_sum binary64 0x1p+0 0x1p-60 -> 0x1p+0 0x1p-61"], cl)
    expect(entry_failures(s, "two_sum", "error") == 1, "wrong error term accepted")
    s = judge(["two_sum binary64 0x1p+0 0x1p-60 -> 0x1p+0 0x1p-60"], cl)
    expect(totals(s)["passed"] == 1, "right answer rejected")
    # Non-finite results: not judged, suspicious when everything is small.
    s = judge(["add_2_2 binary64 0x1p+0 0x0p+0 0x1p+0 0x0p+0 -> inf 0x0p+0"], cl)
    t = totals(s)
    expect(t["nonfinite"] == 1 and t["suspicious"] == 1 and t["failed"] == 0, "suspicious inf")
    s = judge(["add_2_2 binary64 0x1p+0 0x0p+0 0x1p+0 0x0p+0 -> 0x1p+1 nan"], cl)
    t = totals(s)
    expect(t["nonfinite_tail"] == 1 and t["suspicious"] == 1, "suspicious NaN tail")
    s = judge(["add_2_2 binary64 0x1.fffffffffffffp+1023 0x0p+0 0x1.fffffffffffffp+1023 0x0p+0 -> inf 0x0p+0"], cl)
    t = totals(s)
    expect(t["nonfinite"] == 1 and t["suspicious"] == 0, "genuine overflow called suspicious")
    # Invalid inputs are never passed: not normalized, not in the format, not finite.
    for ln in ("add_2_2 binary64 0x1p+0 0x1p+0 0x1p+0 0x0p+0 -> 0x1.8p+1 0x0p+0",
               "add_2_2 binary64 0x1.0000000000001p+0 0x1p-53 0x1p+0 0x0p+0 -> 0x1p+1 0x0p+0",
               "add_2_2 binary64 0x1p+0 0x1p-52 0x1p+0 0x0p+0 -> 0x1p+1 0x1p-52",
               "add_2_2 binary64 0x1p+0 0x1p-1075 0x1p+0 0x0p+0 -> 0x1p+1 0x0p+0",
               "add_2_2 binary64 inf 0x0p+0 0x1p+0 0x0p+0 -> inf 0x0p+0",
               "fast_two_sum binary64 0x1p+0 0x1p+1 -> 0x1.8p+1 0x0p+0",
               "two_sum binary64 0x1.00000000000008p+0 0x0p+0 -> 0x1p+0 0x0p+0"):
        s = judge([ln], cl)
        t = totals(s)
        expect(t["invalid"] == 1 and t["passed"] == 0, "invalid input not reported: %s" % ln)
    # The x1 = +-ulp/2 extremes: allowed toward an even x0, refused toward an odd one.
    s = judge(["add_2_2 binary64 0x1p+0 0x1p-53 0x0p+0 0x0p+0 -> 0x1p+0 0x1p-53"], cl)
    expect(totals(s)["passed"] == 1, "x1 = ulp/2 with even x0 refused")
    s = judge(["add_2_2 binary64 0x1p+0 -0x1p-54 0x0p+0 0x0p+0 -> 0x1p+0 -0x1p-54"], cl)
    expect(totals(s)["passed"] == 1, "x1 = -ulp/4 below a power of two refused")
    # The lines of a kernel whose claims cannot be read fail, and so does the run.
    raw = json.load(open(FIXTURE))
    next(x for x in raw["kernels"] if x["name"] == "two_prod")["requires"] = ["finite(a)"]
    cb = Claims(raw)
    s = judge(["two_prod binary64 0x1p+0 0x1p+0 -> 0x1p+0 0x0p+0",
               "two_sum binary64 0x1p+0 0x1p-60 -> 0x1p+0 0x1p-60"], cb)
    expect(totals(s, "two_prod")["failed"] == 1 and totals(s, "two_sum")["passed"] == 1,
           "unreadable kernel judged")
    expect(judge([], cb).failed(), "a claims error did not fail the run")
    # A runner that drops a line, or stops early, is a stream error.
    s = judge(good[:5] + good[6:], cl)
    expect(s.stream_errors and s.failed(), "dropped line not detected")
    s = judge(good[:-1], cl)
    expect(s.stream_errors and s.failed(), "missing trailer not detected")
    return "%d malformed streams reported" % (len(bad) + 6)


@test
def merging(ctx):
    """Summaries of two halves merge into the summary of the whole."""
    lines = []
    for k in FIRST_WAVE:
        lines += py_run(ctx.stream(k, TOY, ctx.n(1000, 300)))
    whole = judge(lines, ctx.claims, max_examples=100000)
    cut = len(lines) // 2
    while not lines[cut].startswith("# kairn-oracle gen event=begin"):
        cut += 1
    a = judge(lines[:cut], ctx.claims, max_examples=100000)
    b = judge(lines[cut:], ctx.claims, max_examples=100000)
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
    expect(ja == jb, "merged summary differs from the whole")
    return "%d lines" % len(lines)


def _shell_word(arg):
    """arg as one word of a command line for the shell that brute runs the runner with: sh, or
    cmd on Windows, which leaves the quoting to the program (POSIX single quotes mean nothing
    there)."""
    return subprocess.list2cmdline([arg]) if os.name == "nt" else shlex.quote(arg)


@test
def brute_driver(ctx):
    """brute with an external runner and in-process gives the same statistics."""
    out = {}
    for name, runner in (("external", "%s %s refrun" % (_shell_word(sys.executable), _shell_word(SCRIPT))),
                         ("inprocess", "refrun")):
        js = os.path.join(ctx.workdir, "brute-%s.json" % name)
        cmd = [sys.executable, SCRIPT, "brute", "--runner", runner, "--claims", FIXTURE,
               "--kernels", "add_2_1,two_prod", "--formats", "%s,binary64" % TOY,
               "--cases", str(ctx.n(4000, 1000)), "--chunk", "500", "--jobs", "4", "--json", js,
               "--quiet", "--workdir", os.path.join(ctx.workdir, "brute-" + name)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        expect(r.returncode == 0, "brute %s exited %d: %s" % (name, r.returncode, r.stderr[-800:]))
        s = C.load_summary(js)
        out[name] = {k: v.c for k, v in s.keys.items()}
        expect(not s.stream_errors, "brute %s: %s" % (name, s.stream_errors[:2]))
    expect(out["external"] == out["inprocess"], "external and in-process statistics differ")
    return "%d keys" % len(out["external"])


# The tests of the second wave register themselves after the first wave's, those of the
# non-finite layer after them, those of the search and the shrinker next, those of
# rational_1 and rational_2 (kairn::rational) after them, and those of the kinds of Milestone 2
# last.
from . import selftest2  # noqa: E402,F401
from . import selftest3  # noqa: E402,F401
from . import selftest4  # noqa: E402,F401
from . import selftest5  # noqa: E402,F401
from . import selftest6  # noqa: E402,F401
from . import selftest7  # noqa: E402,F401
from . import selftest8  # noqa: E402,F401


# ---------------------------------------------------------------------------

def main(a):
    only = set(a.only.split(",")) if a.only else None
    leave_out = set(a.skip.split(",")) if getattr(a, "skip", None) else set()
    # A name that is not a test's (a test renamed, a typo) would select or leave out nothing.
    unknown = sorted(((only or set()) | leave_out) - {fn.__name__ for fn in TESTS})
    if unknown:
        print("selftest: no test named %s" % ", ".join(unknown))
        return 2
    workdir = a.workdir or tempfile.mkdtemp(prefix="kairn-oracle-selftest-")
    os.makedirs(workdir, exist_ok=True)
    ctx = Ctx(workdir, a.quick, a.cxx, getattr(a, "jobs", None))
    failed = skipped = 0
    t0 = time.time()
    for fn in TESTS:
        if (only and fn.__name__ not in only) or fn.__name__ in leave_out:
            continue
        t = time.time()
        try:
            note = fn(ctx)
            status = "PASS"
        except Skip as ex:
            status, note = "SKIP", str(ex)
            skipped += 1
        except AssertionError as ex:
            status, note = "FAIL", str(ex)
            failed += 1
        except Exception:
            status, note = "FAIL", "unexpected error:\n" + traceback.format_exc()
            failed += 1
        print("%-4s %-30s %6.1fs  %s" % (status, fn.__name__, time.time() - t, note or ""))
        sys.stdout.flush()
    print("selftest: %s (%d failed, %d skipped) in %.0f s" % (
        "FAIL" if failed else "PASS", failed, skipped, time.time() - t0))
    if not a.keep and not a.workdir:
        shutil.rmtree(workdir, ignore_errors=True)
    return 1 if failed else 0
