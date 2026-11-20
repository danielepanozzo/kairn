"""The oracle's own tests of rational_1 and rational_2, kairn::rational<X>(num, den) (rational.py).

The judge compares for equality, so a wrong expected answer would fail a correct library or pass a
wrong one. Each test compares it with something that does not share its code: a brute-force search
over every number and every pair of numbers of toy formats, written from the definitions; CPython's
correctly rounded division of integers and the machine's binary64 addition; answers worked out by
hand; and the reference runner (refrun.py), which rounds by comparing the two neighbours of a value
and finds the pair among three candidates instead of dividing. Planted faults of that runner must
each fail, in the field where they are.
"""

import json
import math
import os
import subprocess
import sys
from bisect import bisect_left
from fractions import Fraction as Q

from . import check as C
from . import fmt as F
from . import rational as R
from . import refrun
from .selftest import test, expect, judge, py_run, totals, BruteRN, SCRIPT, FIXTURE
from .selftest3 import rn_definition

FORMATS = ("binary64", "binary32", "fp:4:-6:4", "fp:1:-3:3")


def _stream(kname, fname, count, seed="selftest", strata=None):
    g = R.RationalGen(kname, F.parse_format(fname), seed, strata.split(",") if strata else None)
    return list(g.lines(0, count))


def _entry_failures(summary, kname=None):
    """Failures of the three entries (value, error, exact), summed over formats and tags."""
    n = [0, 0, 0]
    for (k, _f, _t), s in summary.keys.items():
        if kname is None or k == kname:
            for i, e in enumerate(s.entries):
                n[i] += e.failures
    return n


def _counts(summary, entry=0):
    out = {}
    for s in summary.keys.values():
        if s.entries:
            for name, v in s.entries[entry].counts.items():
                out[name] = out.get(name, 0) + v
    return out


# ---------------------------------------------------------------------------

@test
def rational_rounding(ctx):
    """The roundings of rationals of the judge (to nearest and up) and of the reference runner
    (to nearest) against a brute-force search over every number of six toy formats (precision 1
    included), on every multiple of eta/d for d = 3, 5 and 7 across the whole range and beyond
    the overflow threshold."""
    pts = 0
    ref = refrun.Runner()
    for p, qmin, qmax in ((1, -3, 3), (2, -2, 2), (3, -3, 2), (3, -4, 3), (5, -4, 1), (4, 2, 5)):
        f = F.Format(p, qmin, qmax)
        ar = refrun.Arith((p, qmin, qmax))
        br = BruteRN(p, qmin, qmax)
        eta = Q(2) ** qmin
        for d in (3, 5, 7):
            step = eta / d
            lim = int((br.big + 4 * eta) / step)
            for j in range(-lim, lim + 1):
                x = j * step
                want = rn_definition(br, p, qmin, x)
                got, how = R.round_fraction(f, x)
                got = (math.inf if got == F.POS_INF else -math.inf) if type(got) is str \
                    else R.as_fraction(f, got)
                expect(got == want, "RN(%s) = %s, want %s in %s" % (x, got, want, f.name))
                r = ref._nearest(ar, x / eta)
                expect((r if type(r) is float else r * eta) == want,
                       "the reference runner's RN(%s) = %s, want %s in %s" % (x, r, want, f.name))
                if br.vals[0] <= x <= br.vals[-1]:
                    i = bisect_left(br.vals, x)
                    exact = br.vals[i] == x
                    tie = not exact and 2 * x == br.vals[i] + br.vals[i - 1]
                    expect(how == ("exact" if exact else "tie" if tie else "inexact"),
                           "RN(%s) said %s in %s" % (x, how, f.name))
                if x > 0:
                    i = bisect_left(br.vals, x)
                    up = br.vals[i] if i < len(br.vals) else math.inf
                    got, _ = R.round_fraction(f, x, up=True)
                    got = math.inf if got == F.POS_INF else R.as_fraction(f, got)
                    expect(got == up, "RU(%s) = %s, want %s in %s" % (x, got, up, f.name))
                pts += 1
    return "%d points" % pts


def _brute_answer(br, p, qmin, by_sum, k, num, den):
    """rational_k from the definitions alone: RN by rn_definition, the pair as the one normalized
    pair (by brute force over every pair of the format) whose value is RN(q) + RN(q - RN(q)), the
    error as the smallest number not below |value - q|. Limbs and error as Fractions, or
    +-math.inf."""
    eta = Q(2) ** qmin
    q = Q(num, den)
    a = rn_definition(br, p, qmin, q)
    if isinstance(a, float):
        return [a] + [Q(0)] * (k - 1), math.inf, 0
    if k == 1:
        limbs = [a]
    else:
        b = rn_definition(br, p, qmin, q - a)
        v = a + b
        pairs = by_sum.get(int(v / eta), [])
        if not pairs:
            expect(isinstance(rn_definition(br, p, qmin, v), float),
                   "no normalized pair of the finite value %s" % v)
            return [math.inf if v > 0 else -math.inf, Q(0)], math.inf, 0
        expect(len(pairs) == 1, "%d normalized pairs of value %s" % (len(pairs), v))
        limbs = [Q(pairs[0][0]) * eta, Q(pairs[0][1]) * eta]
    d = abs(sum(limbs) - q)
    if d == 0:
        return limbs, Q(0), 1
    i = bisect_left(br.vals, d)
    return limbs, (br.vals[i] if i < len(br.vals) else math.inf), 0


@test
def rational_toy_brute(ctx):
    """Every pair of terms with |num|, |den| <= 24 (40 without --quick), in six toy formats of
    precision 1 to 5: the answer of both rational_1 and rational_2 against one computed from the
    definitions alone, the pair of rational_2 found by enumerating every pair of numbers of the
    format and keeping the normalized ones, which must be exactly one for every finite value."""
    bound = ctx.n(40, 24)
    cases = 0
    seen = {}
    for p, qmin, qmax in ((1, -3, 3), (2, -3, 2), (3, -4, 3), (3, -2, 1), (4, -6, 4),
                          (5, -8, 4)):
        f = F.Format(p, qmin, qmax)
        br = BruteRN(p, qmin, qmax)
        eta = Q(2) ** qmin
        vals = [int(v / eta) for v in br.vals]
        rn_memo = {}
        by_sum = {}
        for z0 in vals:
            for z1 in vals:
                s = z0 + z1
                r = rn_memo.get(s)
                if r is None:
                    r = rn_memo[s] = rn_definition(br, p, qmin, s * eta)
                if r == z0 * eta:
                    by_sum.setdefault(s, []).append((z0, z1))
        for num in range(-bound, bound + 1):
            for den in range(-bound, bound + 1):
                if den == 0:
                    continue
                for k in (1, 2):
                    limbs, err, exact = _brute_answer(br, p, qmin, by_sum, k, num, den)
                    ans = R.answer(f, k, num, den)
                    got = [math.inf if v == F.POS_INF else -math.inf if v == F.NEG_INF
                           else R.as_fraction(f, v) for v in ans.limbs]
                    gerr = math.inf if ans.error == F.POS_INF else R.as_fraction(f, ans.error)
                    expect(got == limbs and gerr == err and ans.exact == exact,
                           "rational_%d %s %d %d: %s %s %s, by brute force %s %s %s"
                           % (k, f.name, num, den, got, gerr, ans.exact, limbs, err, exact))
                    for c in ans.classes:
                        seen[c] = seen.get(c, 0) + 1
                    cases += 1
    for c in (R.RENORMALIZED, R.TIE1, R.TIE2, R.BEYOND, R.UNDERFLOW, R.SUBNORMAL2, R.EXACT):
        expect(seen.get(c), "no case of %r among the small terms of the toy formats" % c)
    return "%d answers, terms up to %d; %d naive pairs not normalized, %d beyond the range" % (
        cases, bound, seen[R.RENORMALIZED], seen[R.BEYOND])


def _float_answer(k, num, den):
    """rational_k in binary64 by CPython and the machine: num / den on integers is correctly
    rounded, so is float() of a Fraction, and the normalized pair of a + b with |b| <= ulp(a)/2 is
    Fast2Sum's (s, b - (s - a)); the error is float() of the exact difference, stepped up with
    math.nextafter when below it."""
    a = num / den
    if k == 1:
        limbs = [a]
    else:
        b = float(Q(num, den) - Q(a))
        s = a + b
        limbs = [s, b - (s - a)]
    d = abs(sum(Q(z) for z in limbs) - Q(num, den))
    e = float(d)
    if Q(e) < d:
        e = math.nextafter(e, math.inf)
    return limbs, e, int(d == 0)


@test
def rational_hardware(ctx):
    """binary64 answers against CPython's correctly rounded division of integers and the
    machine's addition, on every case of the generator's streams of both kernels."""
    fmt = F.parse_format("binary64")
    n = 0
    for k in (1, 2):
        for ln in _stream("rational_%d" % k, "binary64", ctx.n(20000, 6000)):
            if ln.startswith("#"):
                continue
            toks = ln.split()
            num, den = int(toks[2]), int(toks[3])
            if den == 0:
                continue
            ans = R.answer(fmt, k, num, den)
            limbs, err, exact = _float_answer(k, num, den)
            got = [float(R.as_fraction(fmt, v)) for v in ans.limbs]
            expect(got == limbs and float(R.as_fraction(fmt, ans.error)) == err
                   and ans.exact == exact,
                   "%s: %s, by the machine %s %r %d" % (ln, R.answer_text(fmt, ans),
                                                        [z.hex() for z in limbs], err.hex(), exact))
            n += 1
    return "%d cases" % n


@test
def rational_page_bounds(ctx):
    """The consequences the design page states, on every case of the generator's streams of both
    kernels in binary64 and binary32: |value - q| <= u/(1+u) |q| for one limb and <= u^2 |q| for
    two, with no term for underflow; the leading limb never subnormal; the error zero exactly when
    the flag is 1."""
    n = 0
    worst = {}
    for fname in ("binary64", "binary32"):
        fmt = F.parse_format(fname)
        u = Q(1, 1 << fmt.p)
        for k in (1, 2):
            rel = u / (1 + u) if k == 1 else u * u
            for ln in _stream("rational_%d" % k, fname, ctx.n(20000, 6000))[1:-1]:
                num, den = int(ln.split()[2]), int(ln.split()[3])
                if den == 0:
                    continue
                ans = R.answer(fmt, k, num, den)
                q = Q(num, den)
                d = abs(R.as_fraction(fmt, sum(ans.limbs)) - q)
                expect(d <= rel * abs(q), "%s: |value - q| = %s above the page's bound" % (ln, d))
                expect(ans.limbs[0] == 0 or abs(ans.limbs[0]) >= fmt.lam, "%s: a subnormal leading "
                       "limb" % ln)
                expect((ans.error == 0) == (ans.exact == 1), "%s: error and flag disagree" % ln)
                if q:
                    worst[(fname, k)] = max(worst.get((fname, k), 0), d / (rel * abs(q)))
                n += 1
    return "%d cases; largest |value - q| / bound: %s" % (n, ", ".join(
        "%s rational_%d %.3f" % (f, k, float(r)) for (f, k), r in sorted(worst.items())))


# Hand-worked answers (oracle/README.md, "rational"): 1/3, ties of 2^53 + 1 and 2^53 + 3, the
# pair renormalized at q = (2^62 + 511)/(2^62 - 1) = 1 + 2^-53 + 2^-115 + ..., the extremes, 1/3 in
# binary32, and fp:3:-4:3 (eta = 2^-4, Omega = 56, overflow from 60 on): an error below eta, an
# overflow, a finite RN(q) whose pair overflows, a renormalized pair (q = 5.49, RN(q) = 5, the
# remainder 0.49 rounds to 1/2, 5.5 to the even 6).
HAND = (
    ("rational_1 binary64 1 3", "0x1.5555555555555p-2 0x1.5555555555556p-56 0"),
    ("rational_2 binary64 1 3",
     "0x1.5555555555555p-2 0x1.5555555555555p-56 0x1.5555555555556p-110 0"),
    ("rational_1 binary64 1 2", "0x1p-1 0x0p+0 1"),
    ("rational_2 binary64 -3 -12", "0x1p-2 0x0p+0 0x0p+0 1"),
    ("rational_1 binary64 9007199254740993 1", "0x1p+53 0x1p+0 0"),
    ("rational_2 binary64 9007199254740993 1", "0x1p+53 0x1p+0 0x0p+0 1"),
    ("rational_1 binary64 9007199254740995 1", "0x1.0000000000002p+53 0x1p+0 0"),
    ("rational_2 binary64 4611686018427388415 4611686018427387903",
     "0x1p+0 0x1p-53 0x1.0000000000001p-115 0"),
    ("rational_1 binary64 4611686018427388415 4611686018427387903",
     "0x1.0000000000001p+0 0x1p-53 0"),
    ("rational_1 binary64 -9223372036854775808 -1", "0x1p+63 0x0p+0 1"),
    ("rational_2 binary32 9223372036854775807 1", "0x1p+63 -0x1p+0 0x0p+0 1"),
    ("rational_1 binary32 9223372036854775807 1", "0x1p+63 0x1p+0 0"),
    ("rational_2 binary32 1 -9223372036854775808", "-0x1p-63 0x0p+0 0x0p+0 1"),
    ("rational_2 binary32 1 3", "0x1.555556p-2 -0x1.555556p-27 0x1.555556p-52 0"),
    ("rational_1 fp:3:-4:3 1 3", "0x1.4p-2 0x1p-4 0"),
    ("rational_2 fp:3:-4:3 1 3", "0x1.4p-2 0x0p+0 0x1p-4 0"),
    ("rational_1 fp:3:-4:3 60 1", "inf inf 0"),
    ("rational_1 fp:3:-4:3 59 1", "0x1.cp+5 0x1.8p+1 0"),
    ("rational_2 fp:3:-4:3 59 1", "0x1.cp+5 0x1.8p+1 0x0p+0 1"),
    ("rational_2 fp:3:-4:3 -60 1", "-inf 0x0p+0 inf 0"),
    ("rational_2 fp:3:-4:3 299 5", "inf 0x0p+0 inf 0"),
    ("rational_1 fp:3:-4:3 299 5", "0x1.cp+5 0x1p+2 0"),
    ("rational_2 fp:3:-4:3 549 100", "0x1.8p+2 -0x1p-1 0x1p-4 0"),
    ("rational_1 fp:3:-4:3 549 100", "0x1.4p+2 0x1p-1 0"),
    ("rational_2 binary64 5 0", "nan nan inf 0"),
    # Other spellings of the same answers: zeros of either sign, NaN with a sign, +inf.
    ("rational_2 binary64 0 5", "-0x0p+0 0x0p+0 -0x0p+0 1"),
    ("rational_2 binary64 0 -5", "0x0p+0 -0x0p+0 0x0p+0 1"),
    ("rational_1 binary64 -7 0", "-nan +inf 0"),
    ("rational_2 binary32 0 0", "nan -nan infinity 0"),
)
# Wrong answers, each with the entry that must fail (0 the limbs, 1 the error, 2 exact).
WRONG = (
    ("rational_1 binary64 1 3", "0x1.5555555555554p-2 0x1.5555555555556p-56 0", 0),
    ("rational_2 binary64 1 3",
     "0x1.5555555555555p-2 0x1.5555555555556p-56 0x1.5555555555556p-110 0", 0),
    # The naive pair where it is not normalized.
    ("rational_2 binary64 4611686018427388415 4611686018427387903",
     "0x1.0000000000001p+0 -0x1p-53 0x1.0000000000001p-115 0", 0),
    # The error rounded to nearest (one step too small), and one step too large.
    ("rational_1 binary64 1 3", "0x1.5555555555555p-2 0x1.5555555555555p-56 0", 1),
    ("rational_1 binary64 1 3", "0x1.5555555555555p-2 0x1.5555555555557p-56 0", 1),
    ("rational_2 binary64 4611686018427388415 4611686018427387903",
     "0x1p+0 0x1p-53 0x1p-115 0", 1),
    ("rational_1 binary64 1 2", "0x1p-1 0x0p+0 0", 2),
    ("rational_1 binary64 1 3", "0x1.5555555555555p-2 0x1.5555555555556p-56 1", 2),
    ("rational_2 binary64 5 0", "0x0p+0 0x0p+0 inf 0", 0),
    ("rational_2 binary64 5 0", "nan nan 0x0p+0 0", 1),
    ("rational_2 binary64 5 0", "nan nan -inf 0", 1),
    ("rational_2 binary64 5 0", "nan nan inf 1", 2),
    ("rational_2 binary64 5 0", "nan 0x0p+0 inf 0", 0),
    # A tie rounded away from even; truncation (1/3 in binary32 rounds up).
    ("rational_1 binary64 9007199254740993 1", "0x1.0000000000001p+53 0x1p+0 0", 0),
    ("rational_1 binary32 1 3", "0x1.555554p-2 0x1.555556p-27 0", 0),
    ("rational_1 fp:3:-4:3 1 3", "0x1.4p-2 0x0p+0 0", 1),
    ("rational_1 fp:3:-4:3 60 1", "0x1.cp+5 inf 0", 0),
    ("rational_2 fp:3:-4:3 299 5", "0x1.cp+5 0x1p+2 inf 0", 0),
    ("rational_2 fp:3:-4:3 549 100", "0x1.4p+2 0x1p-1 0x1p-4 0", 0),
    ("rational_1 binary64 1 2", "nan 0x0p+0 1", 0),
)
# Lines that are not judged: malformed (failures) and invalid requests (invalid).
MALFORMED = (
    "rational_1 binary64 1 3",
    "rational_1 binary64 1 3 -> 0x1.5555555555555p-2 0x1.5555555555556p-56",
    "rational_1 binary64 1 3 -> 0x1.5555555555555p-2 0x1.5555555555556p-56 0 0",
    "rational_1 binary64 1 3 -> 0x1.5555555555555p-2  0x1.5555555555556p-56 0",
    "rational_1 binary64 1 3 -> 0x1.5555555555555p-2 0x1.5555555555556p-56 2",
    "rational_1 binary64 1 3 -> 0x1.5555555555555p-2 0x1.5555555555556p-56 true",
    "rational_1 binary64 1 3 -> 0x1.8 0x1.5555555555556p-56 0",
    "rational_1 binary64 1 3 -> 0x1.55555555555554p-2 0x1.5555555555556p-56 0",
    "rational_1 binary64 1 3 -> 0x1p-1075 0x1.5555555555556p-56 0",
    "rational_1 binary64 1 3 7 -> 0x1.5555555555555p-2 0x1.5555555555556p-56 0",
    "rational_1 binary64 1 -> 0x1p+0 0x0p+0 1",
    "rational_1 binary65 1 3 -> 0x1.5555555555555p-2 0x1.5555555555556p-56 0",
    "rational_2 binary64 1 3 -> 0x1.5555555555555p-2 0x1.5555555555556p-56 0",
)
INVALID = (
    "rational_1 binary64 1.5 3 -> 0x1p-1 0x0p+0 1",
    "rational_1 binary64 9223372036854775808 1 -> 0x1p+63 0x0p+0 1",
    "rational_1 binary64 1 -9223372036854775809 -> -0x1p-63 0x0p+0 1",
    "rational_1 binary64 0x10 1 -> 0x1p+4 0x0p+0 1",
    "rational_1 binary64 1e3 1 -> 0x1.f4p+9 0x0p+0 1",
    "rational_1 binary64 1_000 1 -> 0x1.f4p+9 0x0p+0 1",
    "rational_2 binary64 3 x",
)


@test
def rational_judge(ctx):
    """Hand-worked lines judged as worked out: right answers (in every spelling of a zero, a NaN
    and an infinity) pass, wrong ones fail in their field only, malformed lines fail, invalid
    requests are counted invalid and never passed."""
    for req, out in HAND:
        s = judge(["%s -> %s" % (req, out)], ctx.claims)
        expect(totals(s)["passed"] == 1, "right answer refused: %s -> %s (%s)" % (
            req, out, [ex[1] for st in s.keys.values() for ex in st.examples["failure"]]))
    for req, out, entry in WRONG:
        s = judge(["%s -> %s" % (req, out)], ctx.claims)
        n = _entry_failures(s)
        expect(totals(s)["failed"] == 1 and n[entry] == 1 and sum(n) == 1,
               "wrong answer judged otherwise (failures per entry %s): %s -> %s" % (n, req, out))
        why = [ex[1] for st in s.keys.values() for ex in st.examples["failure"]][0]
        expect("expected" in why, "a failure without the expected value: %s" % why)
    for ln in MALFORMED:
        s = judge([ln], ctx.claims)
        expect(totals(s)["failed"] == 1 and totals(s)["judged"] == 0, "malformed line: %s" % ln)
    for ln in INVALID:
        s = judge([ln], ctx.claims)
        t = totals(s)
        expect(t["invalid"] == 1 and t["passed"] == 0 and t["failed"] == 0,
               "invalid request not counted invalid: %s" % ln)
    return "%d right, %d wrong, %d malformed, %d invalid" % (len(HAND), len(WRONG), len(MALFORMED),
                                                             len(INVALID))


@test
def rational_gen(ctx):
    """The generator: case i alone equals case i of a run, seeds matter, every term in the 64-bit
    range, every stratum in one turn of the schedule, the small stratum every pair up to its
    bound and in order, den = 0 only in its stratum, near-ties whose naive pair is not normalized
    in binary64 and binary32 and second limbs that are subnormal in binary32, a restriction of the
    strata, and the command line (header, trailer, --start, an unknown stratum, --exhaustive)."""
    n = ctx.n(6000, 2000)
    for fname in FORMATS:
        for k in (1, 2):
            kname = "rational_%d" % k
            lines = _stream(kname, fname, n)
            expect(lines[0].startswith("# kairn-oracle gen event=begin kernel=%s format=%s "
                                       "mode=random seed=selftest strata=%s start=0 count=%d"
                                       % (kname, F.parse_format(fname).name,
                                          ",".join(R.STRATA), n)), "header: %s" % lines[0])
            expect(lines[-1] == "# kairn-oracle gen event=end lines=%d" % n, "trailer")
            g = R.RationalGen(kname, F.parse_format(fname), "selftest")
            small = []
            for i, ln in enumerate(lines[1:-1]):
                toks = ln.split()
                num, den = int(toks[2]), int(toks[3])
                stratum, idx = toks[4][1:].split(":")
                expect(int(idx) == i and stratum == R.SCHEDULE[i % len(R.SCHEDULE)],
                       "tag of case %d: %s" % (i, toks[4]))
                expect(R.INT64_MIN <= num <= R.INT64_MAX and R.INT64_MIN <= den <= R.INT64_MAX,
                       "term outside the range: %s" % ln)
                expect((den == 0) == (stratum == "den0"), "den = 0 outside its stratum: %s" % ln)
                if stratum == "small":
                    small.append((num, den))
                if i % 97 == 0:
                    expect(g.case(i) == ln, "case %d alone differs from the run" % i)
            expect(small == [R.small_pair(j) for j in range(len(small))], "small out of order")
            b = R.small_bound(len(small))
            want = {(x, y) for x in range(-b, b + 1) for y in range(-b, b + 1) if y}
            expect(want <= set(small) and len(want) == R.small_total(b), "small pairs up to %d" % b)
    a = _stream("rational_2", "binary64", 64, seed="a")
    b = _stream("rational_2", "binary64", 64, seed="b")
    expect(sum(x != y for x, y in zip(a[1:-1], b[1:-1])) > 40, "the seed does not matter")
    # One turn of the schedule has every stratum.
    one = _stream("rational_1", "binary32", len(R.SCHEDULE))
    expect({ln.split()[4][1:].split(":")[0] for ln in one[1:-1]} == set(R.STRATA),
           "a turn of the schedule misses a stratum")
    # The classes the strata are there for.
    rates = []
    for fname, cls, stratum, least in (("binary64", R.RENORMALIZED, "tie1", 0.4),
                                       ("binary32", R.RENORMALIZED, "tie1", 0.5),
                                       ("binary32", R.SUBNORMAL2, "tail", 0.2),
                                       ("binary32", R.TIE2, "tie2", 0.05)):
        fmt = F.parse_format(fname)
        lines = _stream("rational_2", fname, ctx.n(800, 300), strata=stratum)[1:-1]
        hit = sum(cls in R.answer(fmt, 2, int(ln.split()[2]), int(ln.split()[3])).classes
                  for ln in lines)
        expect(hit >= least * len(lines), "%s: %s in only %d of %d cases of %s"
               % (fname, cls, hit, len(lines), stratum))
        rates.append("%s %s %d%%" % (fname, cls, 100 * hit // len(lines)))
    sub = _stream("rational_1", "binary64", 40, strata="tie1,den0")
    expect({ln.split()[4][1:].split(":")[0] for ln in sub[1:-1]} == {"tie1", "den0"}
           and "strata=tie1,den0" in sub[0], "strata not restricted")
    # The command line.
    r = subprocess.run([sys.executable, SCRIPT, "gen", "rational_2", "binary32", "--seed", "3",
                        "--start", "5", "--count", "1"], capture_output=True, text=True)
    expect(r.returncode == 0 and r.stdout.splitlines()[1] ==
           R.RationalGen("rational_2", F.parse_format("binary32"), "3").case(5),
           "gen --start 5 --count 1: %s" % r.stdout + r.stderr)
    for bad in (["rational_2", "binary32", "--strata", "tie3"],
                ["rational_2", "binary32", "--exhaustive"], ["rational_2", "binary66"],
                ["rational_3", "binary64"]):
        r = subprocess.run([sys.executable, SCRIPT, "gen"] + bad, capture_output=True, text=True)
        expect(r.returncode == 2 and not r.stdout, "gen %s accepted" % bad)
    return "; ".join(rates)


@test
def rational_reference(ctx):
    """The reference runner's answers pass, every line judged, on the streams of both kernels in
    binary64, binary32 and toy formats; and the stream checks: a dropped, repeated, altered or
    reordered line and a missing trailer fail the stream; a stream of kernels and of rational_K
    together is judged as each alone."""
    n = ctx.n(6000, 2000)
    judged = 0
    for fname in FORMATS + ("fp:2:-2:2", "fp:6:-14:8"):
        for k in (1, 2):
            s = judge(py_run(_stream("rational_%d" % k, fname, n)), ctx.claims)
            t = totals(s)
            expect(t["passed"] == n and t["judged"] == n and not s.stream_errors,
                   "rational_%d %s: %s %s" % (k, fname, t, s.stream_errors[:2]))
            judged += t["judged"]
    good = py_run(_stream("rational_2", "binary32", 200))
    body = [i for i, ln in enumerate(good) if not ln.startswith("#")]
    first, second = body[3], body[4]
    toks = good[first].split(" ")
    toks[2] = str(int(toks[2]) + 1)
    altered = " ".join(toks)
    for why, lines in (
            ("dropped", good[:first] + good[first + 1:]),
            ("repeated", good[:first + 1] + good[first:]),
            ("dropped and repeated", good[:first] + good[second:second + 1] + good[second:]),
            ("altered", good[:first] + [altered] + good[first + 1:]),
            ("reordered", good[:first] + [good[second], good[first]] + good[second + 1:]),
            ("truncated", good[:-1])):
        s = judge(lines, ctx.claims)
        expect(s.stream_errors and s.failed(), "a %s line not a stream error" % why)
    kernels = py_run(ctx.stream("add_2_2", "binary64", 100))
    s = judge(kernels + good + kernels, ctx.claims)
    alone = totals(judge(kernels, ctx.claims), "add_2_2")
    expect(not s.failed() and totals(s, "add_2_2") == {c: 2 * v for c, v in alone.items()}
           and totals(s, "rational_2") == totals(judge(good, ctx.claims)), "a mixed stream")
    return "%d lines judged" % judged


# The planted faults (refrun.VARIANTS), with the entries that must fail (0 the limbs, 1 the
# error, 2 exact), whether the others must not, and the kernels they apply to.
INJECTED = (
    ("rat-lead-ulp", (0,), True, (1, 2)),
    ("rat-tail-ulp", (0,), True, (2,)),
    ("rat-naive-pair", (0,), True, (2,)),
    ("rat-error-small", (1,), True, (1, 2)),
    ("rat-error-large", (1,), True, (1, 2)),
    ("rat-exact-flip", (2,), True, (1, 2)),
    ("rat-den0-finite", (0,), True, (1, 2)),
    ("rat-tie-away", (0,), False, (1, 2)),
    ("rat-truncate", (0,), False, (1, 2)),
)


@test
def rational_injected(ctx):
    """Every planted fault of the reference runner fails in binary64, binary32 and a toy format,
    for every kernel it applies to, in the field where it is, and in no other where it is the only
    fault; the variants of one kernel leave the other kernel's answers alone."""
    n = ctx.n(4000, 1500)
    out = []
    for variant, entries, only, kernels in INJECTED:
        for fname in ("binary64", "binary32", "fp:4:-6:4"):
            for k in (1, 2):
                lines = _stream("rational_%d" % k, fname, n)
                s = judge(py_run(lines, variant), ctx.claims)
                fails = _entry_failures(s)
                if k not in kernels:
                    expect(not s.failed(), "%s changed rational_%d %s" % (variant, k, fname))
                    continue
                expect(s.failed() and all(fails[e] for e in entries)
                       and (not only or all(not fails[e] for e in range(3) if e not in entries)),
                       "%s on rational_%d %s: failures per entry %s" % (variant, k, fname, fails))
                c = _counts(s)
                if variant == "rat-naive-pair":
                    expect(fails[0] == c.get(R.RENORMALIZED), "naive pairs: %d failures, %s "
                           "lines not normalized" % (fails[0], c.get(R.RENORMALIZED)))
                if variant == "rat-den0-finite":
                    expect(fails[0] == c.get(R.DEN0), "den = 0: %d failures" % fails[0])
                if variant == "rat-error-small":
                    expect(fails[1] == c.get(R.INEXACT) - c.get(R.BEYOND, 0),
                           "error too small: %d failures" % fails[1])
                if variant == "rat-error-large":
                    expect(fails[1] == totals(s)["judged"] - c.get(R.DEN0) - c.get(R.BEYOND, 0),
                           "error too large: %d failures" % fails[1])
        out.append(variant)
    return "%d faults caught" % len(out)


@test
def rational_merging(ctx):
    """The summary of a rational stream judged in two halves and merged is the summary of the
    whole, through JSON, and the command line's check --json and exit status agree."""
    lines = py_run(_stream("rational_2", "binary32", 600)) + py_run(
        _stream("rational_1", "fp:4:-6:4", 600))
    whole = judge(lines, ctx.claims, max_examples=100000)
    cut = len(lines) // 2
    while not lines[cut].startswith("# kairn-oracle gen event=begin"):
        cut += 1
    m = C.Summary(100000)
    for part in (lines[:cut], lines[cut:]):
        half = judge(part, ctx.claims, max_examples=100000)
        m.merge(C.Summary.from_json(json.loads(json.dumps(half.to_json())), 100000))
    expect(whole.to_json() == m.to_json(), "merged summary differs from the whole")
    path = os.path.join(ctx.workdir, "rational.json")
    for variant, status in (("correct", 0), ("rat-error-small", 1)):
        text = "\n".join(py_run(_stream("rational_2", "binary64", 300), variant)) + "\n"
        r = subprocess.run([sys.executable, SCRIPT, "check", "--claims", FIXTURE, "--json", path,
                            "--fail-on-suspicious"], input=text, capture_output=True, text=True)
        expect(r.returncode == status, "check exited %d on %s:\n%s" % (r.returncode, variant,
                                                                       r.stdout[-2000:]))
        js = C.load_summary(path)
        expect(sum(st.c["judged"] for st in js.keys.values()) == 300, "--json summary")
        if status:
            expect("FAILURE: error" in r.stdout and "expected" in r.stdout,
                   "the report shows no failure with its expected value")
    return "%d lines" % len(lines)
