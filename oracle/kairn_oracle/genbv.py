"""Requests for the ball vectors (architecture.md, "Ball vectors", "The line protocol": BV, BV_CONV,
inplace=): random BallVectors of every length class and order, by strata, and every BallVector of
tiny formats up to a small length.

Random mode is the folds' (counter-based, the 17 places of lengths, the orders drawn per case, all
in the header; a product of BallVectors the 13 places of pairs of lengths of the convolutions).
Every operand is a canonical BallVector: a finite one (every center finite, normalized for two
limbs, the radius finite and nonnegative) or the whole space (every center zero, the radius +inf).
The strata:

    one         centers in nearby binades of either sign, radii from zero to about the centers
    wide        radii far above the centers
    zeroradius  every radius zero (and the result exact where the step is)
    whole       an operand the whole space, the other finite (or both, or of no entry)
    overflow    centers in the top binades: the step overflows, the result is the whole space
    threshold   operands scaled so that the largest value of a condition of finite_when (of
                radii_when for no entry) is just below its limit 2^(qmax+p+E), or just above it
    cancel      the centers of the operands cancel entry by entry (x within a few units of -y for
                a sum, of y for a difference)
    underflow   centers and radii in the subnormal range (a power of two into it, for a scaling)
    zeros       centers zero, of either sign
    nonfinite   (a scalar that is not a radius, any value: bv_scale_k) the scalar infinite or a NaN,
                or zero beside the whole space
    exact       (exact_when) the limbs and the radius times c at, just below and just above the
                smallest normal number N, or zero
    tail        (two limbs) second limbs at the extremes of the invariant
    count       (a product) lengths up to the largest, of which count_when holds or just fails in
                formats of few bits
    badradius   (a constructor) each class of the radius given: negative, -inf, NaN, +inf, +0, -0,
                positive
    badcenter   (a constructor) a center given infinite or a NaN

In-place requests (gen --inplace, a ball vector of an array read of the limbs of the array
written): every request carries inplace=I, I in turn over the arrays that can be written.
"""

import hashlib
from fractions import Fraction

from . import expr as EX
from . import fmt as F
from . import gen as G
from . import gen2 as G2
from . import genfold as GF
from . import genmap as GM
from .claims import format_u_eta

INF, NINF, NAN = F.POS_INF, F.NEG_INF, F.NAN
BV_STRATA = ("one", "wide", "zeroradius", "whole", "overflow", "threshold", "cancel", "underflow",
             "zeros", "nonfinite", "exact", "tail")
BV_SCHEDULE = ("one", "threshold", "whole", "wide", "cancel", "overflow", "zeroradius", "threshold",
               "underflow", "exact", "one", "nonfinite", "zeros", "tail", "threshold")
MAKE_STRATA = ("one", "badradius", "badcenter", "zeros", "overflow", "underflow", "tail")
MAKE_SCHEDULE = ("one", "badradius", "badcenter", "badradius", "zeros", "overflow", "underflow",
                 "badradius", "tail")
CONV_STRATA = ("one", "wide", "zeroradius", "whole", "overflow", "threshold", "cancel",
               "underflow", "zeros", "count", "tail")
CONV_SCHEDULE = ("one", "threshold", "whole", "wide", "count", "overflow", "zeroradius",
                 "threshold", "underflow", "cancel", "zeros", "tail")


def strata_of(f):
    """(strata, schedule) of a ball vector or a product: those that apply to its shape."""
    from . import bvfolds as BF
    two = f.wlimbs >= 2
    if isinstance(f, BF.BvConv):
        st, sc = CONV_STRATA, CONV_SCHEDULE
    elif f.kind == "makes_ball_vector":
        st, sc = MAKE_STRATA, MAKE_SCHEDULE
    else:
        st, sc = BV_STRATA, BV_SCHEDULE
        drop = set()
        if not [n for n, _ in f.scalars if n not in f.radii and n not in f.pow2]:
            drop.add("nonfinite")
        if f.exact_when is None:
            drop.add("exact")
        st = tuple(s for s in st if s not in drop)
        sc = tuple(s for s in sc if s not in drop)
    if not two:
        st = tuple(s for s in st if s != "tail")
        sc = tuple(s for s in sc if s != "tail")
    return st, sc


class RandomBVGen:
    def __init__(self, f, fmt, seed, strata=None, orders=None, max_length=None, index_tags=True,
                 inplace=False):
        from . import bvfolds as BF
        self.fold = self.f = f
        self.fmt = fmt
        self.conv = isinstance(f, BF.BvConv)
        known, schedule = strata_of(f)
        GM._setup(self, f, seed, strata, orders, max_length, index_tags, known, schedule,
                  "conv" if self.conv else "bv")
        self.inplace = [i for i, (_n, l) in enumerate(f.arrays) if l == f.wlimbs] if inplace else []
        if inplace and (self.conv or not self.inplace):
            raise G.GenError("%s has no in-place form" % f.name)
        if inplace:
            self.key = hashlib.blake2b(self.key + b"|inplace", digest_size=32).digest()
        self.k = f.wlimbs

    def header(self, start, count):
        return GM._header(self, start, count)

    def lines(self, start, count):
        yield self.header(start, count)
        for i in range(start, start + count):
            yield self.case(i)
        yield "# kairn-oracle gen event=end lines=%d" % count

    length = GF.RandomFoldGen.length

    def case(self, i):
        stratum = self.schedule[i % len(self.schedule)]
        rng = G.CaseRandom(self.key, i)
        tag = "#%s:%d" % (stratum, i) if self.index_tags else "#" + stratum
        if self.conv:
            nx, ny = _conv_lengths(self, rng, i, stratum)
            vals = _conv_case(self, rng, stratum, nx, ny)
            return conv_text(self.f, self.fmt, nx, ny, vals, rng, tag)
        n = self.length(rng, i)
        o = self.orders[rng.below(len(self.orders))]
        if o == "lanes:big":
            o = "lanes:%d" % (n + 1 + rng.below(8))
        if self.f.kind == "makes_ball_vector":
            vals = _make_case(self, rng, stratum, n)
        else:
            vals = _bv_case(self, rng, stratum, n)
        ip = self.inplace[i % len(self.inplace)] if self.inplace else None
        return bv_text(self.f, self.fmt, o, n, vals, rng, tag, ip)


# ---------------------------------------------------------------------------
# Numbers

def _num(fmt, rng, e, style="uniform"):
    return rng.sign() * G.in_binade(fmt, rng, max(fmt.qmin, min(fmt.emax, e)), style)


def _center(fmt, rng, k, e, mode="near", style="uniform"):
    x0 = _num(fmt, rng, e, style)
    return [x0] if k == 1 else [x0, G.tail_for(fmt, rng, x0, mode)]


def _common_center(fmt, rng, k, stratum):
    if k == 1:
        return [G2.limb(fmt, rng, stratum)]
    return G2.expansion(fmt, rng, stratum)


def _mid_e(fmt, rng, k):
    return rng.between(*G._mid(fmt, (k + 1) * fmt.p + 2, 2 * fmt.p + 4))


def _radius_near(fmt, rng, c, d):
    """A radius about |c| 2^d (zero when that is below eta), a number of the format."""
    m = abs(c) or (1 << max(0, fmt.emin_normal - fmt.qmin))
    e = fmt.binade(m) + d
    if e < fmt.qmin:
        return 0
    return G.in_binade(fmt, rng, min(fmt.emax, e))


def _fixed(fmt, f):
    """A positive rational value to the nearest number of the format below it (0 below eta), a
    fixed value; Omega above."""
    per = Fraction(1 << -fmt.qmin) if fmt.qmin < 0 else Fraction(1, 1 << fmt.qmin)
    q = f * per
    return min(F.rdir(fmt, q.numerator // q.denominator, fmt.qmin, False), fmt.omega)


def _scale(fmt, limbs, k):
    """Fixed limbs times 2^k, each rounded toward zero to the format (a pair kept normalized by
    renormalizing its leading limb)."""
    out = []
    for v in limbs:
        if type(v) is not int or v == 0:
            out.append(v)
            continue
        w = v << k if k >= 0 else (abs(v) >> -k) * (1 if v > 0 else -1)
        w = F.rdir(fmt, abs(w), fmt.qmin, False) * (1 if w > 0 else -1) if w else 0
        out.append(max(-fmt.omega, min(fmt.omega, w)))
    if len(out) == 2 and not F.normalized_limbs(fmt, out):
        out = [out[0], 0]
    return out


# ---------------------------------------------------------------------------
# A ball vector

def _arrays_scalars(f):
    radius_of = {a: r for a, r in f.bvs}
    others = [n for n, _ in f.scalars if n not in f.radii]
    return radius_of, others


def _bv_case(g, rng, stratum, n):
    """{array: [entries]}, {scalar: value}: canonical operands of the stratum."""
    f, fmt, k = g.f, g.fmt, g.k
    p = fmt.p
    radius_of, others = _arrays_scalars(f)
    arrays = [a for a, _ in f.arrays]
    vals = {}
    sc = {}
    for a in arrays:
        es = []
        e0 = _mid_e(fmt, rng, k)
        for _i in range(n):
            if stratum in ("overflow",):
                es.append(_common_center(fmt, rng, k, "overflow"))
            elif stratum in ("underflow", "zeros", "tail"):
                es.append(_common_center(fmt, rng, k, {"tail": "extreme"}.get(stratum, stratum)
                                         if stratum != "zeros" else "zero"))
            elif stratum == "wide":
                es.append(_center(fmt, rng, k, e0 + rng.between(-p, p)))
            else:
                es.append(_center(fmt, rng, k, e0 + rng.between(-2, 2)))
        vals[a] = es
        big = max((abs(x[0]) for x in es), default=0)
        if stratum == "zeroradius":
            r = 0
        elif stratum == "wide":
            r = _radius_near(fmt, rng, big, rng.between(p, 3 * p))
        elif stratum == "underflow":
            r = rng.below(1 << min(p, 8)) if rng.bits(1) else _radius_near(fmt, rng, big, -1)
        elif stratum == "zeros":
            r = 0 if rng.bits(1) else _radius_near(fmt, rng, 1, rng.between(-p, p))
        else:
            r = 0 if rng.chance(1, 8) else _radius_near(fmt, rng, big, -rng.between(0, 2 * p))
        sc[radius_of[a]] = r
    for s in others:
        if s in f.pow2:
            kk = rng.between(-p, p) if stratum not in ("underflow", "exact") else rng.between(
                -2 * p, 0)
            if stratum == "overflow":
                kk = rng.between(0, p)
            sc[s] = 1 << max(0, min(fmt.emax, kk) - fmt.qmin)
        elif stratum == "nonfinite":
            sc[s] = (INF, NINF, NAN, 0)[rng.below(4)]
        else:
            t = rng.below(6)
            sc[s] = (0 if t == 0 else rng.sign() * (1 << -fmt.qmin if fmt.qmin < 0 else 1)
                     if t == 1 else _num(fmt, rng, rng.between(-p, p)))
    if stratum == "cancel" and len(arrays) == 2:
        x, y = arrays
        sub = "-" in f.value_text
        for i in range(n):
            t = [v if sub else -v for v in vals[x][i]]
            j = len(t) - 1
            if t[0] and rng.bits(1):
                nb = F.succ(fmt, t[j]) if rng.bits(1) else F.pred(fmt, t[j])
                if type(nb) is int:
                    t2 = list(t)
                    t2[j] = nb
                    if len(t2) == 1 or F.normalized_limbs(fmt, t2):
                        t = t2
            vals[y][i] = t
    if stratum == "exact" and f.pow2:
        _exact_corner(g, rng, vals, sc, n)
    if stratum == "threshold" and f.finite_when:
        _threshold(g, rng, vals, sc, n)
    if stratum == "whole" or (stratum == "nonfinite" and rng.chance(1, 4)):
        for a in arrays if rng.chance(1, 4) else [arrays[rng.below(len(arrays))]]:
            vals[a] = [[0] * k for _ in range(n)]
            sc[radius_of[a]] = INF
    return vals, sc


def _exact_corner(g, rng, vals, sc, n):
    """The limbs and the radius times c at N, just below or just above it, or zero."""
    f, fmt = g.f, g.fmt
    c = sc[f.pow2[0]]
    lam = fmt.lam
    radius_of, _o = _arrays_scalars(f)

    eta = _value(fmt, [1])
    # v with v c = N exactly (c a power of two: N / c is a number of the format in range).
    b = _fixed(fmt, (lam * eta) / (c * eta))

    def at(t):
        if t == 0:
            return 0
        if t == 1 and type(F.succ(fmt, b)) is int:
            return F.succ(fmt, b)
        if t == 2 and b > 0:
            return F.pred(fmt, b)
        return b
    for a, _l in f.arrays:
        for i in range(n):
            if rng.chance(1, 2):
                t = rng.below(4)
                x0 = at(t) * rng.sign()
                vals[a][i] = [x0] + [0] * (g.k - 1)
        sc[radius_of[a]] = at(rng.below(4))


def _value(fmt, limbs):
    s = sum(limbs)
    return Fraction(s, 1 << -fmt.qmin) if fmt.qmin < 0 else Fraction(s << fmt.qmin)


def _cond_value(g, tree, entry, sc):
    """The exact value of a condition's expression at one entry (a dict of array -> limbs) and the
    scalars."""
    fmt = g.fmt

    def ev(t):
        k = t[0]
        if k == "name":
            n = t[1]
            if n in entry:
                return _value(fmt, entry[n])
            v = sc[n]
            return _value(fmt, [v])
        if k == "neg":
            return -ev(t[1])
        if k == "abs":
            return abs(ev(t[1]))
        a, b = ev(t[1]), ev(t[2])
        return a + b if k == "+" else a - b if k == "-" else a * b
    return ev(tree)


def _threshold(g, rng, vals, sc, n):
    """Arrays and radii scaled by a power of two so that the largest value of a condition of
    finite_when over the entries is in (lim/4, lim] (inside), or just above lim (a quarter of the
    time)."""
    f, fmt = g.f, g.fmt
    radius_of, _o = _arrays_scalars(f)
    tree, _t, e = f.finite_when[rng.below(len(f.finite_when))]
    T = fmt.qmax + fmt.p + e
    lim = Fraction(2) ** T
    best = Fraction(0)
    for i in range(n):
        entry = {a: vals[a][i] for a, _l in f.arrays}
        best = max(best, abs(_cond_value(g, tree, entry, sc)))
    if n == 0 and f.radii_when:
        tree, _t, e = f.radii_when[0]
        lim = Fraction(2) ** (fmt.qmax + fmt.p + e)
        best = abs(_cond_value(g, tree, {}, sc))
    if best == 0 or not all(type(v) is int for v in sc.values()):
        return
    k = 0
    while best * Fraction(2) ** k > lim:
        k -= 1
    while best * Fraction(2) ** (k + 1) <= lim:
        k += 1
    if rng.chance(1, 4):
        k += 1
    for a, _l in f.arrays:
        vals[a] = [_scale(fmt, x, k) for x in vals[a]]
        r = radius_of[a]
        sc[r] = abs(_scale(fmt, [sc[r]], k)[0])


# ---------------------------------------------------------------------------
# A constructor

def _make_case(g, rng, stratum, n):
    f, fmt, k = g.f, g.fmt, g.k
    a = f.arrays[0][0]
    r = f.scalars[0][0]
    es = []
    e0 = _mid_e(fmt, rng, k)
    for _i in range(n):
        if stratum in ("overflow", "underflow"):
            es.append(_common_center(fmt, rng, k, stratum))
        elif stratum == "zeros":
            es.append([0] * k)
        elif stratum == "tail":
            es.append(_common_center(fmt, rng, k, "extreme"))
        else:
            es.append(_center(fmt, rng, k, e0 + rng.between(-4, 4)))
    if stratum == "badcenter" and n:
        for _ in range(1 + rng.below(2)):
            i = rng.below(n)
            v = (INF, NINF, NAN)[rng.below(3)]
            es[i] = [v] + ([NAN] if v == NAN else [0]) * (k - 1)
    if stratum == "badradius":
        t = rng.below(7)
        # Each class of the radius given; a -0 written as its literal.
        rv = [-G.in_binade(fmt, rng, rng.between(fmt.qmin, fmt.emax)), NINF, NAN, INF, 0,
              "-0x0p+0", G.in_binade(fmt, rng, rng.between(fmt.qmin, fmt.emax))][t]
    else:
        big = max((abs(x[0]) for x in es if type(x[0]) is int), default=0)
        rv = 0 if rng.chance(1, 6) else _radius_near(fmt, rng, big, -rng.between(0, 2 * fmt.p))
    return {a: es}, {r: rv}


def bv_text(f, fmt, order, n, vals, rng, tag, inplace=None):
    vals, sc = vals
    toks = [f.name, fmt.name, order, str(n)]
    if inplace is not None:
        toks.append("inplace=%d" % inplace)
    for s, _l in f.scalars:
        v = sc[s]
        toks.append(GM._tok(fmt, v, rng.chance(1, 4) and s not in f.radii))
    for a, l in f.arrays:
        for j in range(l):
            toks.extend(GM._tok(fmt, e[j], rng.chance(1, 4)) for e in vals[a])
    toks.append(tag)
    return " ".join(toks)


# ---------------------------------------------------------------------------
# A product of two BallVectors

def _conv_lengths(g, rng, i, stratum):
    if stratum == "count":
        # The count min(n_x, n_y) at the edge of count_when, on either side (from one below to two
        # above the largest count of which it holds), where the edge is within the largest length;
        # otherwise a count in the upper half of the lengths.
        from . import bvfolds as BF
        L = max(1, g.max_length)
        if not hasattr(g, "_edge"):
            g._edge = BF.count_edge(g.f, g.fmt, L) if g.f.count_when else L
        if g._edge < L and rng.chance(3, 4):
            n = min(L, max(1, g._edge + rng.between(-1, 2)))
        else:
            n = rng.between(max(1, L // 2), L)
        return (n, n) if rng.bits(1) else (n, rng.between(n, L))
    return GM.RandomConvGen.lengths(g, rng, i) if hasattr(GM.RandomConvGen, "lengths") else \
        _lengths(g, rng, i)


def _lengths(g, rng, i):
    a, b = GM.CONV_LENGTHS[i % len(GM.CONV_LENGTHS)]
    L = g.max_length

    def one(t):
        if t == "s":
            return rng.between(2, max(2, min(9, L)))
        if t == "r":
            return rng.between(min(18, L), L) if L >= 18 else rng.between(0, L)
        return min(t, L)
    return one(a), one(b)


def _conv_case(g, rng, stratum, nx, ny):
    """({x: entries, y: entries}, {rx, ry}) of the stratum."""
    f, fmt, k = g.f, g.fmt, g.k
    p = fmt.p
    (xn, _l1), (yn, _l2) = f.arrays
    radius_of = {a: r for a, r in f.bvs}
    vals, sc = {}, {}
    for a, n in ((xn, nx), (yn, ny)):
        e0 = _mid_e(fmt, rng, k) // 2
        es = []
        for _i in range(n):
            if stratum in ("overflow", "underflow"):
                es.append(_common_center(fmt, rng, k, stratum))
            elif stratum == "zeros":
                es.append([0] * k)
            elif stratum == "tail":
                es.append(_common_center(fmt, rng, k, "extreme"))
            else:
                es.append(_center(fmt, rng, k, e0 + rng.between(-3, 3)))
        vals[a] = es
        big = max((abs(x[0]) for x in es), default=0)
        if stratum == "zeroradius":
            r = 0
        elif stratum == "wide":
            r = _radius_near(fmt, rng, big, rng.between(p, 2 * p))
        elif stratum == "count":
            r = 0 if rng.bits(1) else _radius_near(fmt, rng, big, -p)
        else:
            r = 0 if rng.chance(1, 8) else _radius_near(fmt, rng, big, -rng.between(0, 2 * p))
        sc[radius_of[a]] = r
    if stratum == "count":
        for a in (xn, yn):
            vals[a] = [[0] * k if rng.bits(1) else x for x in vals[a]]
    if stratum == "cancel" and nx >= 2 and ny >= 2 and vals[xn][0][0]:
        # The two terms of coefficient 1 cancel: y_1 the leading limb nearest -x_1 y_0 / x_0.
        x0, x1, y0 = (_value(fmt, vals[xn][0]), _value(fmt, vals[xn][1]),
                      _value(fmt, vals[yn][0]))
        t = -x1 * y0 / x0
        w = _fixed(fmt, abs(t)) if t else 0
        vals[yn][1] = [w if t > 0 else -w] + [0] * (k - 1)
    if stratum == "threshold" and f.finite_when:
        tree, _t, e = f.finite_when[0]
        lim = Fraction(2) ** (fmt.qmax + fmt.p + e)
        n = min(nx, ny)
        best = Fraction(0)
        for x in vals[xn]:
            for y in vals[yn]:
                v = abs(n * (abs(_value(fmt, x)) + _value(fmt, [sc[radius_of[xn]]])) *
                        (abs(_value(fmt, y)) + _value(fmt, [sc[radius_of[yn]]])))
                best = max(best, v)
        if best:
            kk = 0
            while best * Fraction(4) ** kk > lim:
                kk -= 1
            while best * Fraction(4) ** (kk + 1) <= lim:
                kk += 1
            if rng.chance(1, 4):
                kk += 1
            for a in (xn, yn):
                vals[a] = [_scale(fmt, x, kk) for x in vals[a]]
                r = radius_of[a]
                sc[r] = abs(_scale(fmt, [sc[r]], kk)[0])
    if stratum == "whole":
        for a in ((xn, yn) if rng.chance(1, 4) else ((xn, yn)[rng.below(2)],)):
            vals[a] = [[0] * k for _ in vals[a]]
            sc[radius_of[a]] = INF
    return vals, sc


def conv_text(f, fmt, nx, ny, vals, rng, tag):
    vals, sc = vals
    toks = [f.name, fmt.name, "seq", str(nx), str(ny)]
    for s, _l in f.scalars:
        toks.append(GM._tok(fmt, sc[s], False))
    for a, l in f.arrays:
        for j in range(l):
            toks.extend(GM._tok(fmt, e[j], rng.chance(1, 4)) for e in vals[a])
    toks.append(tag)
    return " ".join(toks)


# ---------------------------------------------------------------------------
# Every BallVector of a tiny format

class ExhaustiveBVGen:
    """Every request of a ball vector (or a product) up to a length: for each length n (each
    length of each array, for a product), every order that differs (seq, and lanes:W for 2 <= W <=
    n), every canonical operand (a finite ball vector: every nonnegative radius with every finite
    entry; the whole space: the radius +inf, every entry zero), every value of the other scalars
    (every power of two for power_of_two(), every value with the infinities and a NaN otherwise);
    for a constructor every value of its radius and of its centers (canonical pairs for two
    limbs).  Case i is decoded from i."""

    def __init__(self, f, fmt, max_length, index_tags=True):
        from . import bvfolds as BF
        self.fold = self.f = f
        self.fmt = fmt
        self.L = max_length
        self.conv = isinstance(f, BF.BvConv)
        self.index_tags = index_tags
        k = f.wlimbs
        nums = F.all_values(fmt)
        finite = [(v,) for v in nums] if k == 1 else G.normalized_pairs(fmt)
        anyv = ([(v,) for v in nums] + [(INF,), (NINF,), (NAN,)] if k == 1 else
                finite + [(INF, 0), (NINF, 0), (NAN, NAN)])
        self.make = not self.conv and f.kind == "makes_ball_vector"
        self.entries = anyv if self.make else finite
        self.radii = [v for v in nums if v >= 0]
        self.scal = []
        for n, _l in f.scalars:
            if self.make or n in f.radii:
                self.scal.append(None)
            elif n in f.pow2:
                self.scal.append([v for v in nums if v > 0 and v & (v - 1) == 0])
            else:
                self.scal.append(nums + [INF, NINF, NAN])
        if self.make:
            self.scal = [nums + [INF, NINF, NAN]]
        self.lengths = ([(a, b) for a in range(self.L + 1) for b in range(self.L + 1)]
                        if self.conv else [(n,) for n in range(self.L + 1)])
        self.blocks = []
        total = 0
        for ln in self.lengths:
            orders = ["seq"] + ([] if self.conv else ["lanes:%d" % W
                                                      for W in range(2, ln[0] + 1)])
            size = self._size(ln)
            self.blocks.append((total, ln, orders, size))
            total += size * len(orders)
        self.total = total

    def _bv_size(self, n):
        """The canonical BallVectors of n entries."""
        return len(self.radii) * len(self.entries) ** n + 1

    def _size(self, ln):
        if self.make:
            return len(self.entries) ** ln[0] * len(self.scal[0])
        out = 1
        if self.conv:
            for n in ln:
                out *= self._bv_size(n)
            return out
        for _a in self.f.arrays:
            out *= self._bv_size(ln[0])
        for d in self.scal:
            if d is not None:
                out *= len(d)
        return out

    def _bv(self, i, n):
        """(radius, entries) of index i of the BallVectors of n entries."""
        if i == len(self.radii) * len(self.entries) ** n:
            return INF, [tuple(0 for _ in self.entries[0])] * n
        i, r = divmod(i, len(self.radii))
        es = []
        for _ in range(n):
            i, j = divmod(i, len(self.entries))
            es.append(self.entries[j])
        return self.radii[r], es

    def case(self, i):
        for start, ln, orders, size in self.blocks:
            if start <= i < start + size * len(orders):
                break
        oi, j = divmod(i - start, size)
        f, fmt = self.f, self.fmt
        tag = "#exhaustive:%d" % i if self.index_tags else "#exhaustive"

        def h(v):
            return GM._tok(fmt, v, False)
        if self.make:
            n = ln[0]
            j, ri = divmod(j, len(self.scal[0]))
            es = []
            for _ in range(n):
                j, e = divmod(j, len(self.entries))
                es.append(self.entries[e])
            toks = [f.name, fmt.name, orders[oi], str(n), h(self.scal[0][ri])]
            for t in range(f.wlimbs):
                toks.extend(h(e[t]) for e in es)
            return " ".join(toks + [tag])
        if self.conv:
            nx, ny = ln
            j, bx = divmod(j, self._bv_size(nx))
            _j, by = divmod(j, self._bv_size(ny))
            rx, xs = self._bv(bx, nx)
            ry, ys = self._bv(by, ny)
            toks = [f.name, fmt.name, "seq", str(nx), str(ny), h(rx), h(ry)]
            for es in (xs, ys):
                for t in range(f.wlimbs):
                    toks.extend(h(e[t]) for e in es)
            return " ".join(toks + [tag])
        n = ln[0]
        ops = {}
        for a, _l in f.arrays:
            j, b = divmod(j, self._bv_size(n))
            ops[a] = self._bv(b, n)
        sc = []
        for (s, _l), d in zip(f.scalars, self.scal):
            if d is None:
                a = next(a for a, r in f.bvs if r == s)
                sc.append(ops[a][0])
            else:
                j, v = divmod(j, len(d))
                sc.append(d[v])
        toks = [f.name, fmt.name, orders[oi], str(n)] + [h(v) for v in sc]
        for a, _l in f.arrays:
            for t in range(f.wlimbs):
                toks.extend(h(e[t]) for e in ops[a][1])
        return " ".join(toks + [tag])

    def header(self, start, count):
        return ("# kairn-oracle gen event=begin kernel=%s format=%s mode=exhaustive total=%d "
                "maxlen=%d start=%d count=%d" % (self.f.name, self.fmt.name, self.total, self.L,
                                                 start, count))

    def lines(self, start, count):
        count = max(0, min(count, self.total - start))
        yield self.header(start, count)
        for i in range(start, start + count):
            yield self.case(i)
        yield "# kairn-oracle gen event=end lines=%d" % count
