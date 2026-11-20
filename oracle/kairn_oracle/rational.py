"""kairn::rational<X>(num, den): its requests, its exact answer, and the judge of a runner's.

rational_1 and rational_2 are not kernels of gen/claims.json. The specification fixes every bit of
the result (docs/developer/design/milestone2.md, "Constants at compile time"), so the oracle
computes the answer itself, in exact rationals (Fraction), and compares a runner's for equality.
With q = num/den and RN the rounding of the format to nearest, ties to the even significand, with
gradual underflow:

- rational_1: the limb RN(q);
- rational_2: the normalized pair (z0, z1), z0 = RN(z0 + z1), whose value is
  V = RN(q) + RN(q - RN(q));
- error: the smallest number of the format not below |value - q|, zero when the value is q;
- exact: 1 exactly when the value is q;
- den = 0: every limb NaN, error +inf, exact 0.

The pair of rational_2 is unique. Its leading limb is fixed by the definition of a normalized
pair: z0 = RN(z0 + z1) = RN(V). Its second limb is then z1 = V - RN(V), and that is a number of the
format, because V is the exact sum of two numbers of the format, RN(q) and RN(q - RN(q)), and the
error of rounding such a sum to nearest is a number of the format (with gradual underflow, and when
RN(V) does not overflow). So the pair is computed as (RN(V), V - RN(V)). It is the naive pair
(RN(q), RN(q - RN(q))) except near a midpoint of two neighbours: when q is off the midpoint by at
most ulp(h)/4, h half the gap, on the side of the neighbour with the odd significand, RN(q) is
that neighbour, the remainder rounds to exactly h, V is the midpoint, and RN(V) is the other, even,
neighbour. The value is the same; the leading limb is then not RN(q).

Arguments are signed 64-bit integers, so |q| is zero or between 2^-63 and 2^63: in binary64 and
binary32 the value never overflows. In a toy format it can, and then the answer is the canonical
infinity of the sign of q, (+-inf, 0), with error +inf and exact 0: the design page's rule for a
wider argument type. That is also the answer of rational_2 when RN(q) is finite but RN(V) is not
(no normalized pair has the value V then).

A request is `rational_K FORMAT NUM DEN #STRATUM:INDEX`, a completed line the request followed by
` -> L0 [L1] ERROR EXACT`: K limbs and the error as hexadecimal floating-point literals (`nan`,
`inf`, `-inf`), and EXACT `0` or `1`.
"""

import math
import re
import sys
from fractions import Fraction

from . import fmt as F
from . import gen as G

KERNELS = {"rational_1": 1, "rational_2": 2}
INT64_MIN = -(1 << 63)
INT64_MAX = (1 << 63) - 1
_DECIMAL = re.compile(r"[+-]?[0-9]+\Z")


# ---------------------------------------------------------------------------
# Exact rounding of a rational

def as_fraction(fmt, n):
    """The value of the fixed value n, n * eta, as a Fraction."""
    if fmt.qmin >= 0:
        return Fraction(n << fmt.qmin)
    return Fraction(n, 1 << -fmt.qmin)


def round_fraction(fmt, x, up=False):
    """The rational x rounded to the format, as a fixed value, and how it went: 'exact', 'tie'
    (x a midpoint of two neighbours) or 'inexact'. To nearest, ties to the even integer
    significand at the exponent of x, with gradual underflow, and POS_INF or NEG_INF beyond the
    IEEE overflow threshold; or, with up, for x > 0 only, up, and POS_INF above Omega."""
    n, d = x.numerator, x.denominator
    if n == 0:
        return 0, "exact"
    if up and n < 0:
        raise ValueError("rounding up is for positive values only")
    a = -n if n < 0 else n
    # 2^e <= |x| < 2^(e+1).
    e = a.bit_length() - d.bit_length()
    if (a << max(-e, 0)) < (d << max(e, 0)):
        e -= 1
    # The exponent of the last place: p bits from the leading one, or the subnormal grid.
    last = max(e - fmt.p + 1, fmt.qmin)
    num, den = (a, d << last) if last >= 0 else (a << -last, d)
    m, rem = divmod(num, den)
    how = "exact" if rem == 0 else "tie" if 2 * rem == den else "inexact"
    if up:
        if rem:
            m += 1
    elif 2 * rem > den or (2 * rem == den and m & 1):
        m += 1
    r = m << (last - fmt.qmin)
    if r > fmt.omega:
        return (F.NEG_INF if n < 0 else F.POS_INF), how
    return (-r if n < 0 else r), how


# ---------------------------------------------------------------------------
# The answer

# The classes of a case that the judge counts (on its first entry), and that the cross-checks'
# guards read (tests/crosscheck_guards.py).
DEN0 = "den = 0"
EXACT = "exact"
INEXACT = "inexact"
TIE1 = "first rounding a tie"
TIE2 = "second rounding a tie"
RENORMALIZED = "naive pair not normalized"
SUBNORMAL2 = "second limb subnormal"
BEYOND = "value beyond the range"
UNDERFLOW = "value zero, q not zero"


class Answer:
    """The expected answer to one request: limbs (fixed values or non-finite constants), error (a
    fixed value or POS_INF), exact (0 or 1), and the classes of the case."""

    __slots__ = ("limbs", "error", "exact", "classes")

    def __init__(self, limbs, error, exact, classes):
        self.limbs = limbs
        self.error = error
        self.exact = exact
        self.classes = classes


def answer(fmt, k, num, den):
    """What rational_k must return for num/den in the format (k = 1 or 2)."""
    if den == 0:
        return Answer([F.NAN] * k, F.POS_INF, 0, [DEN0])
    q = Fraction(num, den)
    classes = []
    a, how = round_fraction(fmt, q)
    if how == "tie":
        classes.append(TIE1)
    if type(a) is not int:
        return Answer([a] + [0] * (k - 1), F.POS_INF, 0, classes + [BEYOND, INEXACT])
    if k == 1:
        limbs = [a]
    else:
        b, how = round_fraction(fmt, q - as_fraction(fmt, a))
        if how == "tie":
            classes.append(TIE2)
        v = a + b
        z0 = F.rn_fixed(fmt, v)
        if type(z0) is not int:
            return Answer([z0, 0], F.POS_INF, 0, classes + [BEYOND, INEXACT])
        z1 = v - z0
        if not F.is_member(fmt, z1):
            # The error of a rounded sum of two numbers of the format is one of them; the pair is
            # then normalized because z0 = RN(v) = RN(z0 + z1).
            raise AssertionError("no normalized pair of value %s in %s" % (v, fmt.name))
        if z0 != a:
            classes.append(RENORMALIZED)
        if z1 != 0 and abs(z1) < fmt.lam:
            classes.append(SUBNORMAL2)
        limbs = [z0, z1]
    if num != 0 and limbs[0] == 0:
        classes.append(UNDERFLOW)
    d = abs(as_fraction(fmt, sum(limbs)) - q)
    if d == 0:
        return Answer(limbs, 0, 1, classes + [EXACT])
    err, _ = round_fraction(fmt, d, up=True)
    return Answer(limbs, err, 0, classes + [INEXACT])


def answer_text(fmt, ans):
    """The fields a runner must append after ' -> ' (one spelling of them: zeros positive)."""
    return " ".join([F.fixed_hex(fmt, v) for v in ans.limbs] + [F.fixed_hex(fmt, ans.error),
                                                                str(ans.exact)])


# ---------------------------------------------------------------------------
# Request lines

STRATA = ("small", "random", "pow2", "extreme", "den0", "exact", "tie1", "tie2", "tail")
# The near-ties of the first limb, where the naive pair is not normalized, come round most often;
# the second limb's near-ties and the tiny second limbs next.
SCHEDULE = ("small", "tie1", "random", "tie2", "pow2", "tie1", "exact", "tail",
            "small", "tie1", "random", "tie2", "extreme", "tie1", "tail", "den0")
# Terms at the extremes: both ends of the range, their neighbours, small ones, powers of two and
# the first integers that the formats cannot hold.
EXTREME_TERMS = (INT64_MIN, INT64_MIN + 1, INT64_MAX, INT64_MAX - 1, 1, -1, 2, -2, 3, -3,
                 1 << 62, -(1 << 62), (1 << 53) + 1, -((1 << 24) + 1), (1 << 62) + 1)


def small_total(s):
    """The number of pairs (num, den), den != 0, with max(|num|, |den|) <= s."""
    return 4 * s * s + 2 * s


def small_bound(n):
    """The largest s whose pairs the first n cases of the small stratum cover."""
    s = math.isqrt(max(n, 0) // 4)
    while small_total(s + 1) <= n:
        s += 1
    while s > 0 and small_total(s) > n:
        s -= 1
    return s


_SHELL = {}


def small_pair(j):
    """Pair j of the enumeration of every (num, den) with den != 0, by shells s = 1, 2, ... of
    max(|num|, |den|) = s (8s - 2 pairs each), num and then den increasing within a shell."""
    s = max(1, math.isqrt(j // 4))
    while small_total(s) <= j:
        s += 1
    while s > 1 and small_total(s - 1) > j:
        s -= 1
    shell = _SHELL.get(s)
    if shell is None:
        if len(_SHELL) > 64:
            _SHELL.clear()
        shell = _SHELL[s] = [(n, d) for n in range(-s, s + 1) for d in range(-s, s + 1)
                             if d != 0 and max(abs(n), abs(d)) == s]
    return shell[j - small_total(s - 1)]


def farey_neighbours(x, dmax):
    """The fractions closest to the positive rational x from below and from above, with
    denominators at most dmax, when x's own denominator is larger: the last convergent of x and
    the semiconvergent, as Fraction.limit_denominator finds the nearer of the two. As (num, den)
    pairs, the lower first."""
    if x.denominator <= dmax:
        raise ValueError("%s is itself a fraction with denominator at most %d" % (x, dmax))
    p0, q0, p1, q1 = 0, 1, 1, 0
    n, d = x.numerator, x.denominator
    while True:
        a = n // d
        q2 = q0 + a * q1
        if q2 > dmax:
            break
        p0, q0, p1, q1 = p1, q1, p0 + a * p1, q2
        n, d = d, n - a * d
    k = (dmax - q0) // q1
    b1, b2 = (p0 + k * p1, q0 + k * q1), (p1, q1)
    return (b1, b2) if b1[0] * b2[1] < b2[0] * b1[1] else (b2, b1)


class RationalGen:
    """Requests of rational_K in a format: counter-based like the kernels' random mode (gen.py),
    case i a function of (kernel, format, seed, strata) and i alone, the strata in turn."""

    def __init__(self, kname, fmt, seed, strata=None, index_tags=True):
        if kname not in KERNELS:
            raise G.GenError("%s is not one of %s" % (kname, ", ".join(KERNELS)))
        self.kname = kname
        self.k = KERNELS[kname]
        self.fmt = fmt
        self.seed = seed
        if strata:
            for s in strata:
                if s not in STRATA:
                    raise G.GenError("unknown stratum %r for %s (known: %s)"
                                     % (s, kname, ", ".join(STRATA)))
            self.schedule = tuple(s for s in SCHEDULE if s in strata) or tuple(strata)
            self.strata = list(strata)
        else:
            self.schedule = SCHEDULE
            self.strata = list(STRATA)
        self.key = G.seed_key(seed, kname, fmt.name, self.strata)
        self.index_tags = index_tags
        # Case i is case (i // n) * per_cycle + before of its stratum (the small stratum
        # enumerates, the extreme one starts with every pair of extreme terms).
        self.before = []
        self.per_cycle = {}
        for s in self.schedule:
            self.before.append(self.per_cycle.get(s, 0))
            self.per_cycle[s] = self.per_cycle.get(s, 0) + 1
        p = fmt.p
        # Binades of the values: 2^-63 <= |q| < 2^63, within the format's.
        lo, hi = max(-63, fmt.qmin), min(62, fmt.emax)
        if lo > hi:
            lo, hi = fmt.qmin, fmt.emax
        self.binades = (lo, hi)
        # Where a midpoint A/2^j has, for t = +-1, denominators with num 2^j - A den = t that are
        # large enough for the remainder to round to exactly half a gap (den >= 2^(p+2)) and
        # spaced 2^j apart: there the naive pair of a near-tie is not normalized.
        self.window1 = []
        for e in range(lo, hi + 1):
            last = max(e - p + 1, fmt.qmin)
            b = 1 << max(0, 1 - last)
            dmax = INT64_MAX if e < 0 else INT64_MAX >> (e + 1)
            if 2 * b <= dmax and dmax >= 1 << (p + 2):
                self.window1.append(e)
        # Where the closest fractions to a point of about 2p + 2 bits in binade e, about 2^-125
        # away below 1 and 2^(2e - 126) above, are within 2^-6 of a unit in the last place of the
        # second limb, about 2^(e - 2p - 1): there a point that no fraction of 64-bit terms is
        # (binary64) still has fractions near it.
        self.window2 = [e for e in range(lo, hi + 1) if 2 * p - 119 <= e <= 117 - 2 * p] or [lo]

    def header(self, start, count):
        return ("# kairn-oracle gen event=begin kernel=%s format=%s mode=random seed=%s strata=%s "
                "start=%d count=%d" % (self.kname, self.fmt.name, self.seed,
                                       ",".join(self.strata), start, count))

    def lines(self, start, count):
        yield self.header(start, count)
        for i in range(start, start + count):
            yield self.case(i)
        yield "# kairn-oracle gen event=end lines=%d" % count

    def case(self, i, index_tags=None):
        n = len(self.schedule)
        stratum = self.schedule[i % n]
        local = (i // n) * self.per_cycle[stratum] + self.before[i % n]
        rng = G.CaseRandom(self.key, i)
        num, den = getattr(self, "_" + stratum)(rng, local)
        if not (INT64_MIN <= num <= INT64_MAX and INT64_MIN <= den <= INT64_MAX):
            raise G.GenError("case %d (%s): a term outside the 64-bit range" % (i, stratum))
        tags = self.index_tags if index_tags is None else index_tags
        return "%s %s %d %d #%s" % (self.kname, self.fmt.name, num, den,
                                    "%s:%d" % (stratum, i) if tags else stratum)

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _term(rng, min_bits=0):
        """A term of mixed magnitude: a bit length uniform in [min_bits, 63], a random sign."""
        b = rng.between(min_bits, 63)
        v = (1 << (b - 1)) | rng.bits(b - 1) if b else 0
        return -v if rng.bits(1) else v

    @staticmethod
    def _signed(rng, num, den):
        s = rng.below(4)
        return (-num if s & 1 else num), (-den if s & 2 else den)

    def _number(self, rng, e, style=None):
        """A positive number of the format in binade e: random significand, or one near the top
        of the binade, or with one to three bits (a power of two among them)."""
        if style is None:
            style = ("high", "short", "uniform", "uniform", "uniform")[rng.below(5)]
        return G.in_binade(self.fmt, rng, e, style)

    def _near(self, rng, x, t, largest):
        """A fraction num/den, den > 0, at or next to the positive rational x = A/B: when B is
        small enough, num B - A den = t, so num/den - x = t/(den B), with den the largest such
        or a random one; otherwise the closest fraction to x on the side of t (a random side for
        t = 0) among those whose terms fit."""
        a, b = x.numerator, x.denominator
        # num = (A den + t)/B must fit for |t| <= 3.
        dmax = min(INT64_MAX, (INT64_MAX * b - 4) // a)
        if dmax < 1:
            return INT64_MAX, 1
        if b <= dmax:
            # den = d0 (mod B) solves num B - A den = t (A and B are coprime: x is in lowest
            # terms); B <= dmax leaves at least one such den in [1, dmax].
            d0 = 0 if b == 1 else (-t * pow(a, -1, b)) % b
            jmin = 0 if d0 >= 1 else 1
            den = d0 + b * ((dmax - d0) // b if largest else rng.between(jmin, (dmax - d0) // b))
            num, r = divmod(a * den + t, b)
            if r:
                raise G.GenError("no solution of num B - A den = t for %s" % x)
            return num, den
        lo, hi = farey_neighbours(x, dmax)
        side = t if t else (1 if rng.bits(1) else -1)
        return hi if side > 0 else lo

    # -- strata -------------------------------------------------------------

    def _small(self, rng, local):
        return small_pair(local)

    def _random(self, rng, local):
        num = INT64_MIN if rng.chance(1, 32) else self._term(rng)
        den = INT64_MIN if rng.chance(1, 32) else self._term(rng, 1)
        if rng.chance(1, 8):
            # Not in lowest terms.
            c = rng.between(2, 1 << rng.between(1, 20))
            if abs(num) * c <= INT64_MAX and abs(den) * c <= INT64_MAX:
                num, den = num * c, den * c
        return num, den

    def _pow2_term(self, rng):
        v = (1 << rng.between(0, 63)) + rng.between(-3, 3)
        v = abs(v) or 1
        if rng.bits(1):
            return INT64_MIN if v == 1 << 63 else -min(v, INT64_MAX)
        return v if v <= INT64_MAX else INT64_MAX - rng.below(3)

    def _pow2(self, rng, local):
        """Powers of two and their neighbours, one of the terms random a quarter of the time."""
        num, den = self._pow2_term(rng), self._pow2_term(rng)
        k = rng.below(8)
        if k == 0:
            num = self._term(rng)
        elif k == 1:
            den = self._term(rng, 1)
        return num, den

    def _extreme(self, rng, local):
        """Every pair of extreme terms (0 as a numerator too) first; then an extreme term with a
        random one, den = +-1, num = 0."""
        nums = (0,) + EXTREME_TERMS
        m = len(nums) * len(EXTREME_TERMS)
        if local < m:
            return nums[local // len(EXTREME_TERMS)], EXTREME_TERMS[local % len(EXTREME_TERMS)]
        pick = EXTREME_TERMS[rng.below(len(EXTREME_TERMS))]
        mode = rng.below(4)
        if mode == 0:
            return self._term(rng), (1 if rng.bits(1) else -1)
        if mode == 1:
            return 0, (pick if rng.bits(1) else self._term(rng, 1))
        if mode == 2:
            return pick, self._term(rng, 1)
        return self._term(rng), pick

    def _den0(self, rng, local):
        k = rng.below(4)
        num = (0 if k == 0 else EXTREME_TERMS[rng.below(len(EXTREME_TERMS))] if k == 1
               else self._term(rng))
        return num, 0

    def _exact(self, rng, local):
        """q = M 2^E exactly, M odd of at most k p bits (and at most 63; for two limbs sometimes a
        power of two far above M), inside the format where the terms allow, written over a
        common odd factor half of the time."""
        fmt = self.fmt
        nb = rng.between(1, min(self.k * fmt.p, 63))
        m = (1 << (nb - 1)) | rng.bits(nb - 1) | 1 if nb > 1 else 1
        if self.k == 2 and nb < 62 and rng.chance(1, 4):
            m |= 1 << rng.between(nb, 62)
        nb = m.bit_length()
        lo, hi = max(-63, fmt.qmin), min(63 - nb, fmt.emax - nb + 1)
        if lo > hi:
            lo, hi = -63, 63 - nb
        e = rng.between(lo, hi)
        num, den = (m << e, 1) if e >= 0 else (m, 1 << -e)
        room = 63 - max(num.bit_length(), den.bit_length())
        if room > 1 and rng.bits(1):
            c = rng.bits(rng.between(1, room - 1)) | 1
            num, den = num * c, den * c
        num, den = self._signed(rng, num, den)
        if den == 1 << 63 or den == -(1 << 63):
            # 2^63 is a term only as -2^63.
            num, den = (-num if den > 0 else num), INT64_MIN
        return num, den

    def _tie1(self, rng, local):
        """Near a midpoint X of two neighbours L < U: num/den - X = t/(den B) for X = A/B. Half
        the cases aim at a pair the naive way does not normalize: t = +-1 toward the neighbour
        with the odd significand, den as large as the terms allow, in the binades where that
        makes the remainder round to half a gap. The others: either side, t from -3 to 3 (0: q
        is the midpoint, a tie), any binade."""
        fmt = self.fmt
        aim = rng.bits(1) and self.window1
        e = self.window1[rng.below(len(self.window1))] if aim else rng.between(*self.binades)
        lo = self._number(rng, e)
        hi = F.succ(fmt, lo)
        if type(hi) is not int:
            lo, hi = F.pred(fmt, lo), lo
        x = (as_fraction(fmt, lo) + as_fraction(fmt, hi)) / 2
        even = F.rn(fmt, lo + hi, fmt.qmin - 1)
        toward_odd = 1 if even == lo else -1
        if aim:
            t, largest = toward_odd, True
        else:
            t, largest = (0, 1, -1, 1, -1, 2, -2, 3)[rng.below(8)], rng.chance(3, 4)
        return self._signed(rng, *self._near(rng, x, t, largest))

    def _tie2(self, rng, local):
        """Near a + m: a a number of the format, m a midpoint of two neighbours (three times in
        four) or a number (where the error of one limb rounds up to it or to the next) well
        below half a unit of a, of either sign: near a tie of the second rounding, or of the
        rounding up of the error. In binary32 t is from -2 to 2 (0: q is the point itself); in
        binary64 the point has more bits than a term, and q is the closest fraction on a side."""
        fmt = self.fmt
        e = (self.window2[rng.below(len(self.window2))] if rng.chance(3, 4)
             else rng.between(*self.binades))
        a = self._number(rng, e)
        u = F.ulp(fmt, a)
        top = fmt.binade(u) - (3 if a & (a - 1) == 0 else 2)
        e2 = top - (rng.below(3) if rng.chance(3, 4) else rng.below(fmt.p + 2))
        lo = self._number(rng, max(e2, fmt.qmin))
        m = as_fraction(fmt, lo)
        if rng.below(4):
            hi = F.succ(fmt, lo)
            m = (m + as_fraction(fmt, hi)) / 2 if type(hi) is int else m
        x = as_fraction(fmt, a) + (m if rng.bits(1) else -m)
        if x <= 0:
            # A toy format whose lowest binades leave no room below a.
            x = as_fraction(fmt, a) + m
        t = (0, 1, -1, 1, -1, 2, -2, 0)[rng.below(8)]
        return self._signed(rng, *self._near(rng, x, t, rng.chance(3, 4)))

    def _tail(self, rng, local):
        """Next to a number a of the format, mostly in the lowest binades: the closest fraction to
        a, over four candidates for a, so that q - a is as small as 64-bit terms allow, about
        2^-126, and the second limb of a binary32 pair is often subnormal; a quarter of the cases
        q = a where a has few bits, whose second limb is zero."""
        fmt = self.fmt
        lo, hi = self.binades
        e = rng.between(lo, min(hi, lo + 2 * fmt.p)) if rng.chance(3, 4) else rng.between(lo, hi)
        if rng.chance(1, 4):
            nb = rng.between(1, max(1, min(fmt.p, e - fmt.qmin + 1)))
            c = (1 << (nb - 1)) | rng.bits(nb - 1) | 1 if nb > 1 else 1
            x = Fraction(c) * Fraction(2) ** (e - nb + 1)
            return self._signed(rng, *self._near(rng, x, 0, True))
        best = None
        for _ in range(4):
            x = as_fraction(fmt, self._number(rng, e))
            for t in (1, -1):
                num, den = self._near(rng, x, t, True)
                d = abs(Fraction(num, den) - x)
                if best is None or d < best[0]:
                    best = (d, num, den)
        return self._signed(rng, best[1], best[2])


# ---------------------------------------------------------------------------
# gen

def cmd_gen(a):
    """kairn-oracle gen rational_K FORMAT [--seed S] [--start I] [--count N] [--strata ...]."""
    if a.exhaustive or a.restrict or a.total:
        print("kairn-oracle gen: %s has random requests only (the stratum small enumerates every "
              "pair of small terms)" % a.kernel, file=sys.stderr)
        return 2
    try:
        fmt = F.parse_format(a.format)
    except F.FormatError as ex:
        print("kairn-oracle: %s" % ex, file=sys.stderr)
        return 2
    try:
        g = RationalGen(a.kernel, fmt, a.seed, a.strata.split(",") if a.strata else None,
                        index_tags=not a.no_index)
        G.write_lines(g.lines(a.start, 1000 if a.count is None else a.count))
    except G.GenError as ex:
        print("kairn-oracle gen: %s" % ex, file=sys.stderr)
        return 2
    return 0


# ---------------------------------------------------------------------------
# check

LABELS = {
    1: ("limb: RN(q)", "error: the smallest number >= |value - q|", "exact: value = q"),
    2: ("limbs: the normalized pair of value RN(q) + RN(q - RN(q))",
        "error: the smallest number >= |value - q|", "exact: value = q"),
}
KINDS = ("rational value", "rational error", "rational exact")


def _same(found, want):
    """Equality of two limbs: values (the sign of a zero is no part of the statement), the same
    infinity, or NaN and any NaN."""
    if want == F.NAN or found == F.NAN:
        return want == found
    return found == want


class Echo:
    """The requests that a generator header of rational_K announces: each completed line under it
    must begin with the request of its index, so that a line the runner changed, dropped,
    repeated or reordered fails the stream even when the count of lines is right."""

    def __init__(self, gen, start):
        self.gen = gen
        self.start = start
        self.broken = False

    @classmethod
    def for_header(cls, ck, fields, start):
        if fields.get("kernel") not in KERNELS:
            return None
        try:
            if fields.get("mode") != "random":
                raise G.GenError("mode %r" % fields.get("mode"))
            strata = fields.get("strata")
            gen = RationalGen(fields["kernel"], F.parse_format(fields.get("format", "")),
                              fields.get("seed", ""), strata.split(",") if strata else None)
        except (G.GenError, F.FormatError, KeyError) as ex:
            ck.stream_error("a generator header of %s that the oracle cannot regenerate: %s"
                            % (fields.get("kernel"), ex))
            return None
        return cls(gen, start)

    def check(self, ck, request, seen):
        if self.broken:
            return
        i = self.start + seen - 1
        want = self.gen.case(i)
        if request == want or request == self.gen.case(i, index_tags=False):
            return
        self.broken = True
        ck.stream_error("the line of case %d is not the request the generator wrote for it (%s): "
                        "the runner changed it, or dropped, repeated or reordered lines"
                        % (i, want))


def judge_line(ck, line, kname, fname, tag, ins, sep, right):
    """Judge one completed line of rational_K, with the checker ck's statistics and examples.
    Every line is judged: a NaN or an infinity is as much a part of the answer as a number."""
    from .check import EntryStats
    k = KERNELS[kname]
    try:
        fmt = F.parse_format(fname)
    except F.FormatError:
        fmt = None
    st = ck.summary.stats((kname, fmt.name if fmt else fname, tag), fmt.p if fmt else None)
    if fmt is not None and not st.entries:
        st.entries = [EntryStats(label, kind) for label, kind in zip(LABELS[k], KINDS)]
    st.c["cases"] += 1
    if fmt is None:
        ck._fail(st, line, "unknown format %r" % fname)
        return
    if len(ins) != 2 or "" in ins:
        ck._fail(st, line, "malformed: %d terms, %s takes two (NUM DEN)" % (len(ins), kname))
        return
    # The request first: two decimal integers of 64 bits, whatever the runner wrote.
    terms = []
    for t in ins:
        if not _DECIMAL.match(t):
            ck._invalid(st, line, "a term that is not a decimal integer")
            return
        v = int(t)
        if not INT64_MIN <= v <= INT64_MAX:
            ck._invalid(st, line, "a term outside the signed 64-bit range")
            return
        terms.append(v)
    if not sep:
        ck._fail(st, line, "malformed: no ' -> ' (the runner did not complete the line)")
        return
    outs = right.split(" ")
    if len(outs) != k + 2 or "" in outs:
        ck._fail(st, line, "malformed: %d output fields, %s writes %d (limbs, error, exact)"
                 % (len(outs), kname, k + 2))
        return
    found = []
    for t in outs[:k + 1]:
        try:
            v = F.parse_limb(fmt, t)
        except F.LimbError as ex:
            ck._fail(st, line, "output malformed: %s" % ex)
            return
        if v == F.OUTSIDE or (type(v) is int and not F.is_member(fmt, v)):
            ck._fail(st, line, "output %s not a number of the format" % t)
            return
        found.append(v)
    if outs[k + 1] not in ("0", "1"):
        ck._fail(st, line, "the flag exact is %r, not 0 or 1" % outs[k + 1])
        return
    flag = int(outs[k + 1])
    ans = answer(fmt, k, terms[0], terms[1])
    st.c["judged"] += 1
    value, error, exact = st.entries
    for es in st.entries:
        es.applicable += 1
    for c in ans.classes:
        value.count(c)
    e = ans.error
    error.count("+inf" if e == F.POS_INF else "zero" if e == 0 else
                "subnormal" if e < fmt.lam else "normal")
    exact.count("exact %d" % ans.exact)
    reasons, why = [], []
    if not all(_same(z, w) for z, w in zip(found[:k], ans.limbs)):
        value.failures += 1
        reasons.append("limbs differ" if k == 2 else "limb differs")
        why.append("limbs %s, expected %s" % (" ".join(outs[:k]), " ".join(
            F.fixed_hex(fmt, v) for v in ans.limbs)))
    if not _same(found[k], e):
        error.failures += 1
        reasons.append("error differs")
        why.append("error %s, expected %s" % (outs[k], F.fixed_hex(fmt, e)))
    if flag != ans.exact:
        exact.failures += 1
        reasons.append("exact differs")
        why.append("exact %d, expected %d" % (flag, ans.exact))
    if reasons:
        st.c["failed"] += 1
        for r in reasons:
            st.reason(r)
        st.example("failure", line, "; ".join(why), ck.max_examples)
    else:
        st.c["passed"] += 1
