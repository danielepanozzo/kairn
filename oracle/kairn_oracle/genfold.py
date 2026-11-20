"""Request lines of the folds (architecture.md, "The line protocol", "Folds"): random arrays in
strata, and every array of a tiny format up to a small length.

    FOLD FORMAT ORDER N LIMB ... #STRATUM:INDEX

ORDER is seq or lanes:W; then, for each array of the fold and each of its limbs, the N entries
of that limb.  The folds of this stage are sums (the value is one array) and dot products (the
value is the product of two arrays); a fold with another value is not generated.

Random mode is counter-based, as for the kernels: case i depends only on (fold, format, seed,
strata, orders, maximum length) and i.  Each case has a stratum (the schedule below), a length
(the length schedule: 0, 1, 2, around each lane count of the packed forms, W - 1, W, W + 1, 2W,
2W + 1 for W = 2, 4, 8, and random lengths from 18 to the maximum, log-uniform) and an order (one
of the orders asked for, drawn per case: seq, lanes:0, lanes:1, 2, 3, 4, 5, 8, and lanes:big, a
number of lanes above the length).  Strata, of the elements' values v_i (the products x_i y_i
for a dot product):

    one        one magnitude: every v_i in two adjacent binades, random signs
    wide       magnitudes over the whole range, random signs
    sign       all of one sign (one or several magnitudes): no cancellation
    cancel     an element (or a factor of one) chosen so that the exact sum is far smaller than
               the sum of magnitudes: the nearest number to minus the sum of the others, a few
               units away, or pairs v, -v' of nearly equal magnitudes
    zeros      zeros of both signs among the elements, or every element zero
    underflow  subnormal and low normal values; for a dot product products from below eta to past
               2^(2p) eta, where the term tau of the bound is the larger part
    overflow   partial sums that overflow although the exact sum does not (large values of one
               sign, then of the other); exact sums just beyond Omega that round to it; sums that
               overflow; products near Omega
    nonfinite  one to three elements replaced by an infinity or a NaN (for two limbs, the
               canonical (+-inf, 0) and (NaN, NaN)); for a dot product also 0 * inf
    tight      cases close to the bound: a first element and others just below half a unit of the
               running sum, which each addition drops; for two limbs, the literature's cases of
               add_2_2, add_fast_2_2 and mul_2_2 (tight.py) as the first elements
    pow2       short significands at nearby exponents: exact sums and ties
    tail       (arrays of two limbs) leading limbs that cancel in pairs, so that the second limbs
               make the sum; second limbs at the extremes of the invariant

Exhaustive mode (--exhaustive --max-length L) enumerates every array of every length up to L,
each element any value of the elements' domain (every number of the format, the infinities and
NaN for one limb; every canonical pair for two), in every order that differs: seq, and lanes:W for
W = 2 to the length.  Case i is decoded from i.
"""

import hashlib

from . import fmt as F
from . import gen as G
from . import gen3 as G3
from . import gen5 as G5
from . import tight as TI
from .claims import format_u_eta

INF, NINF, NAN = F.POS_INF, F.NEG_INF, F.NAN
STRATA = ("one", "wide", "sign", "cancel", "zeros", "underflow", "overflow", "nonfinite", "tight",
          "pow2", "tail")
SCHEDULE = ("one", "cancel", "tight", "wide", "underflow", "sign", "cancel", "overflow", "tight",
            "nonfinite", "zeros", "pow2", "tail")
# The lengths take turns by this schedule, of 17 places (a prime, so that over 17 turns of the
# strata every stratum meets every length class): "r" is a random length.
LENGTH_SCHEDULE = (0, 1, "r", 2, 3, "r", 4, 5, "r", 7, 8, "r", 9, 16, "r", 17, "r")
DEFAULT_ORDERS = ("seq", "seq", "lanes:0", "lanes:1", "lanes:2", "lanes:3", "lanes:4", "lanes:5",
                  "lanes:8", "lanes:big")
DEFAULT_MAX_LENGTH = 256


class FoldShape:
    def __init__(self, fold):
        self.fold = fold
        t = fold.value_tree
        lim = dict(fold.arrays)
        if t[0] == "name":
            self.kind = "sum"
            self.a, self.b = t[1], None
        elif t[0] == "*" and t[1][0] == "name" and t[2][0] == "name" and t[1][1] != t[2][1]:
            self.kind = "dot"
            self.a, self.b = t[1][1], t[2][1]
        else:
            raise G.GenError("%s: the generator writes folds whose value is one array (a sum) or "
                             "the product of two (a dot product), not %r" % (fold.name,
                                                                            fold.value_text))
        if set(n for n, _ in fold.arrays) != {self.a} | ({self.b} if self.b else set()):
            raise G.GenError("%s: an array that the value does not name" % fold.name)
        self.ka = lim[self.a]
        self.kb = lim[self.b] if self.b else None
        if self.ka > 2 or (self.kb or 1) > 2:
            raise G.GenError("%s: arrays of more than two limbs are not generated" % fold.name)
        self.two = self.ka == 2 or self.kb == 2


def order_specs(fold, orders):
    """The orders a run draws from, checked against the fold's claims."""
    specs = list(orders) if orders else [o for o in DEFAULT_ORDERS
                                         if o == "seq" or "lanes" in fold.orders]
    for o in specs:
        if o == "seq":
            if "sequential" not in fold.orders:
                raise G.GenError("%s claims no sequential order" % fold.name)
        elif o == "lanes:big" or (o.startswith("lanes:") and o[6:].isdigit()
                                  and (o[6:] == "0" or not o[6:].startswith("0"))):
            if "lanes" not in fold.orders:
                raise G.GenError("%s claims no lane order" % fold.name)
        else:
            raise G.GenError("unknown order %r (seq, lanes:W, lanes:big)" % o)
    if not specs:
        raise G.GenError("no order")
    return specs


class RandomFoldGen:
    def __init__(self, fold, fmt, seed, strata=None, orders=None, max_length=None,
                 index_tags=True):
        self.fold = fold
        self.fmt = fmt
        self.shape = FoldShape(fold)
        known = STRATA if self.shape.two else tuple(s for s in STRATA if s != "tail")
        schedule = SCHEDULE if self.shape.two else tuple(s for s in SCHEDULE if s != "tail")
        if strata:
            for s in strata:
                if s not in known:
                    raise G.GenError("unknown stratum %r for %s (known: %s)"
                                     % (s, fold.name, ", ".join(known)))
            self.schedule = tuple(s for s in schedule if s in strata) or tuple(strata)
            self.strata = list(strata)
        else:
            self.schedule = schedule
            self.strata = list(known)
        self.orders = order_specs(fold, orders)
        self.max_length = DEFAULT_MAX_LENGTH if max_length is None else max_length
        if self.max_length < 0:
            raise G.GenError("the maximum length is negative")
        self.seed = seed
        self.key = hashlib.blake2b(("kairn-oracle/fold|%s|%s|%s|%s|%s|%d" % (
            seed, fold.name, fmt.name, ",".join(self.strata), ",".join(self.orders),
            self.max_length)).encode(), digest_size=32).digest()
        self.index_tags = index_tags
        self.u, self.eta = format_u_eta(fmt)

    def header(self, start, count):
        return ("# kairn-oracle gen event=begin kernel=%s format=%s mode=random seed=%s strata=%s "
                "orders=%s maxlen=%d start=%d count=%d" % (
                    self.fold.name, self.fmt.name, self.seed, ",".join(self.strata),
                    ",".join(self.orders), self.max_length, start, count))

    def lines(self, start, count):
        yield self.header(start, count)
        for i in range(start, start + count):
            yield self.case(i)
        yield "# kairn-oracle gen event=end lines=%d" % count

    def length(self, rng, i):
        c = LENGTH_SCHEDULE[i % len(LENGTH_SCHEDULE)]
        L = self.max_length
        if c != "r":
            return min(c, L)
        if L < 18:
            return rng.between(0, L)
        b = rng.between((18).bit_length(), L.bit_length())
        return rng.between(max(18, 1 << (b - 1)), min(L, (1 << b) - 1))

    def case(self, i):
        stratum = self.schedule[i % len(self.schedule)]
        rng = G.CaseRandom(self.key, i)
        n = self.length(rng, i)
        o = self.orders[rng.below(len(self.orders))]
        if o == "lanes:big":
            o = "lanes:%d" % (n + 1 + rng.below(8))
        for _attempt in range(16):
            elems, negz = make_elements(self, rng, stratum, n)
            if valid_elements(self.fmt, self.fold, elems):
                break
        else:
            raise G.GenError("could not generate a valid case %d (%s)" % (i, stratum))
        return line_text(self.fold, self.fmt, o, elems, negz,
                         "#%s:%d" % (stratum, i) if self.index_tags else "#" + stratum)


def line_text(fold, fmt, order, elems, negz, tag):
    """The request: elems are tuples of limbs (the arrays' limbs in order), negz the (element,
    limb) positions written as -0."""
    toks = [fold.name, fmt.name, order, str(len(elems))]
    width = sum(l for _, l in fold.arrays)
    for j in range(width):
        for i, e in enumerate(elems):
            v = e[j]
            if type(v) is int:
                toks.append("-0x0p+0" if v == 0 and (i, j) in negz else
                            "0x0p+0" if v == 0 else F.to_hex(v, fmt.qmin))
            else:
                toks.append(v)
    toks.append(tag)
    return " ".join(toks)


def valid_elements(fmt, fold, elems):
    """Every limb a number of the format or a non-finite value, every element of a multi-limb
    array canonical (written from the definitions: gen3's own test)."""
    width = sum(l for _, l in fold.arrays)
    pos = {}
    k = 0
    for n, l in fold.arrays:
        pos[n] = (k, k + l)
        k += l
    for e in elems:
        if len(e) != width:
            return False
        for v in e:
            if type(v) is int:
                if not F.is_member(fmt, v):
                    return False
            elif v not in (INF, NINF, NAN):
                return False
        for n in fold.requires:
            lo, hi = pos[n]
            if not G3._canonical(fmt, list(e[lo:hi])):
                return False
    return True


# ---------------------------------------------------------------------------
# Values

def _clamp(fmt, e):
    return max(fmt.qmin, min(fmt.emax, e))


def _between(rng, lo, hi):
    return rng.between(lo, hi) if lo <= hi else hi


def _num(fmt, rng, e, style="uniform", sign=None):
    v = G.in_binade(fmt, rng, _clamp(fmt, e), style)
    s = rng.sign() if sign is None else sign
    return s * v


def _elem(fmt, rng, x0, k, mode=None):
    """An element of k limbs led by x0."""
    if k == 1:
        return (x0,)
    if mode is None:
        mode = "near" if rng.chance(3, 4) else "any"
    return (x0, G.tail_for(fmt, rng, x0, mode))


def _safe_top(fmt, n):
    """The largest binade of an element such that no sum of n of them overflows."""
    return fmt.emax - max(n, 1).bit_length() - 2


def _value_frac(limbs, fmt):
    from fractions import Fraction
    s = sum(limbs)
    return Fraction(s, 1 << -fmt.qmin) if fmt.qmin < 0 else Fraction(s << fmt.qmin)


def _nearest(fmt, rng, v, k):
    """The k-limb canonical number nearest to the rational v (a value, not in units of eta)."""
    from fractions import Fraction
    vq = v * (Fraction(1 << -fmt.qmin) if fmt.qmin < 0 else Fraction(1, 1 << fmt.qmin))
    t = G5._expansion_near(fmt, rng, vq, k)
    return tuple(t) if t is not None else None


def _sum_values(gen, rng, stratum, n, k):
    """n elements of k limbs for a sum."""
    fmt = gen.fmt
    p = fmt.p
    top = _safe_top(fmt, n)
    lo_mid = min(fmt.emin_normal + k * p + 2, top)
    if stratum in ("one", "sign", "pow2"):
        e0 = _between(rng, lo_mid, top)
        sign = rng.sign() if stratum == "sign" else None
        style = "short" if stratum == "pow2" else "uniform"
        spread = rng.between(0, p + 2) if stratum == "pow2" else 1
        return [_elem(fmt, rng, _num(fmt, rng, e0 - rng.between(0, spread), style, sign), k)
                for _ in range(n)]
    if stratum == "wide":
        return [_elem(fmt, rng, _num(fmt, rng, _between(rng, fmt.qmin, top)), k) for _ in range(n)]
    if stratum == "underflow":
        # Subnormal and low normal values, near one another in each case.
        hi = _between(rng, fmt.qmin, min(fmt.emin_normal + k * p + 1, top))
        return [_elem(fmt, rng, _num(fmt, rng, _between(rng, max(fmt.qmin, hi - p), hi)), k)
                for _ in range(n)]
    if stratum == "zeros":
        e0 = _between(rng, lo_mid, top)
        allz = rng.chance(1, 4)
        out = []
        for _ in range(n):
            if allz or rng.bits(1):
                out.append((0,) * k)
            else:
                out.append(_elem(fmt, rng, _num(fmt, rng, e0), k))
        return out
    if stratum == "cancel":
        e0 = _between(rng, lo_mid, top)
        if n >= 2 and rng.bits(1):
            # Pairs v, -v' a few units apart, in random positions.
            out = []
            while len(out) < n:
                x = _elem(fmt, rng, _num(fmt, rng, e0 - rng.below(3)), k)
                out.append(x)
                if len(out) < n:
                    y = [-t for t in x]
                    for _ in range(rng.below(3)):
                        j = k - 1 if rng.bits(1) else 0
                        nb = F.succ(fmt, y[j]) if rng.bits(1) else F.pred(fmt, y[j])
                        if type(nb) is int:
                            y2 = list(y)
                            y2[j] = nb
                            if k == 1 or F.normalized_limbs(fmt, y2):
                                y = y2
                    out.append(tuple(y))
            _shuffle(rng, out)
            return out
        out = [_elem(fmt, rng, _num(fmt, rng, e0 - rng.below(2)), k) for _ in range(n)]
        if n >= 2:
            j = rng.below(n)
            rest = sum(_value_frac(e, fmt) for i, e in enumerate(out) if i != j)
            t = _nearest(fmt, rng, -rest, k)
            if t is not None:
                out[j] = t
        return out
    if stratum == "overflow":
        return _overflow_sum(fmt, rng, n, k)
    if stratum == "tight":
        return _tight_sum(gen, rng, n, k)
    if stratum == "tail":
        e0 = _between(rng, lo_mid, top)
        modes = ("half+", "half-", "quarter-", "max", "eta", "tiny", "near")
        out = []
        while len(out) < n:
            a0 = _num(fmt, rng, e0 - rng.below(3))
            x = _elem(fmt, rng, a0, k, modes[rng.below(len(modes))])
            out.append(x)
            if len(out) < n:
                out.append(_elem(fmt, rng, -a0, k, modes[rng.below(len(modes))]))
        _shuffle(rng, out)
        return out
    raise G.GenError("unknown stratum %r" % stratum)


def _shuffle(rng, xs):
    for i in range(len(xs) - 1, 0, -1):
        j = rng.below(i + 1)
        xs[i], xs[j] = xs[j], xs[i]


def _overflow_sum(fmt, rng, n, k):
    big = fmt.emax
    om = fmt.omega
    kind = rng.below(4)
    if kind == 0 and n >= 2:
        # Large values of one sign, then of the other: the partial sums of the sequential order
        # overflow although the exact sum is within the range.
        s = rng.sign()
        h = max(1, n // 2)
        out = []
        for i in range(n):
            sg = s if i < h else -s
            out.append(_elem(fmt, rng, sg * G.in_binade(fmt, rng, big - rng.below(2),
                                                         "high" if rng.bits(1) else "uniform"), k))
        return out
    if kind == 1:
        # Omega and a little more: the exact sum is beyond Omega and rounds to it (a quarter of
        # its unit, or less), or one that rounds beyond it.
        s = rng.sign()
        ulp = F.ulp(fmt, om)
        out = [(s * om,) + ((0,) * (k - 1))]
        for _ in range(n - 1):
            q = ulp >> rng.between(2, 4) if rng.chance(3, 4) else ulp >> 1
            out.append((s * max(q, 1),) + ((0,) * (k - 1)))
        return out[:n]
    if kind == 2:
        s = rng.sign()
        return [_elem(fmt, rng, s * G.in_binade(fmt, rng, big - rng.below(3)), k) for _ in range(n)]
    return [_elem(fmt, rng, rng.sign() * G.in_binade(fmt, rng, big - rng.below(3),
                                                       "high" if rng.bits(1) else "uniform"), k)
            for _ in range(n)]


def _tight_sum(gen, rng, n, k):
    """A first element a and others of a's sign just below half a unit of a (for two limbs, of
    a's second limb): each addition drops one; for two limbs, sometimes the literature's tight
    case of the kernel of the fold's step as the first two elements."""
    fmt = gen.fmt
    p = fmt.p
    top = _safe_top(fmt, n)
    e0 = _between(rng, min(fmt.emin_normal + 2 * k * p + 4, top), top)
    s = rng.sign()
    if k == 2 and n >= 2 and rng.bits(1):
        lit = _literature(fmt, rng, (gen.fold.step, gen.fold.combine))
        if lit is not None:
            x, y = lit
            return [tuple(s * v for v in x), tuple(s * v for v in y)] + [(0, 0)] * (n - 2)
    e0 = _clamp(fmt, e0)
    a0 = s * (1 << (e0 - fmt.qmin) if rng.bits(1) else G.in_binade(fmt, rng, e0))
    if k == 1:
        h = F.ulp(fmt, a0) >> 1
        d = F.pred(fmt, h) if h > 1 else 0
        return [(a0,)] + [(s * d,)] * (n - 1)
    a = (a0, G.tail_for(fmt, rng, a0, "max"))
    h = F.ulp(fmt, a[1]) >> 1 if a[1] else 0
    d = F.pred(fmt, h) if h > 1 else 0
    # Of the second limb's sign, below half its unit: the sum of the second limbs drops it.
    t = d if a[1] > 0 else -d
    return [a] + [(t, 0)] * (n - 1)


def _literature(fmt, rng, kernels):
    """The operands of a tight case of the literature (tight.py) for one of the kernels, scaled by
    a power of two into the format (a scaling keeps its relative error, away from underflow), as
    lists of fixed values; or None when there is none or none fits."""
    from fractions import Fraction
    found = []
    for _name, alg, x, y in TI._cases(fmt.p):
        for kn in kernels:
            f = TI.KERNELS[alg].get(kn)
            if f is not None:
                found.append(f(x, y))
                break
    if not found:
        return None
    ops = found[rng.below(len(found))]
    vals = [v for t in ops for v in t if v]
    eta = Fraction(1 << -fmt.qmin) if fmt.qmin < 0 else Fraction(1, 1 << fmt.qmin)
    # The smallest power of two making every limb a multiple of eta, then the largest keeping the
    # leading limbs below an eighth of the overflow threshold.
    kmin = max(max(0, (v * eta).denominator.bit_length() - 1) for v in vals)
    top = max(abs(v) for v in vals) * eta
    kmax = kmin
    while top * (1 << (kmax + 1 - kmin)) * (1 << kmin) <= Fraction(fmt.omega, 8):
        kmax += 1
        if kmax > kmin + 2 * fmt.p + 8:
            break
    if top * (1 << kmin) > Fraction(fmt.omega, 8):
        return None
    k = rng.between(kmin, kmax)
    out = []
    for t in ops:
        limbs = []
        for v in t:
            w = v * eta * (1 << k)
            if w.denominator != 1 or not F.is_member(fmt, int(w)):
                return None
            limbs.append(int(w))
        if len(limbs) > 1 and not F.normalized_limbs(fmt, limbs):
            return None
        out.append(limbs)
    return out


def _scale(fmt, v, d):
    """v * 2^d if that is exact and in the format, else None."""
    if v == 0:
        return 0
    w = v << d if d >= 0 else (v >> -d if v % (1 << -d) == 0 else None)
    return w if w is not None and F.is_member(fmt, w) else None


def _dot_values(gen, rng, stratum, n, ka, kb):
    """n elements (x_i, y_i) for a dot product."""
    fmt = gen.fmt
    p = fmt.p
    top = _safe_top(fmt, n)
    k = max(ka, kb)

    def pair(ep, mode_a=None, mode_b=None, sign=None, style="uniform"):
        ea, eb = G._split_exponent(fmt, rng, ep)
        x0 = _num(fmt, rng, ea, style)
        y0 = _num(fmt, rng, eb, style)
        # All products of one sign: the product's sign is that of x0 y0.
        if sign is not None and ((x0 > 0) == (y0 > 0)) != (sign > 0):
            y0 = -y0
        return _elem(fmt, rng, x0, ka, mode_a) + _elem(fmt, rng, y0, kb, mode_b)

    lo_mid = min(fmt.emin_normal + 2 * k * p + 4, top)
    if stratum in ("one", "sign", "pow2"):
        e0 = _between(rng, lo_mid, top)
        sign = rng.sign() if stratum == "sign" else None
        style = "short" if stratum == "pow2" else "uniform"
        return [pair(e0 - rng.below(2), sign=sign, style=style) for _ in range(n)]
    if stratum == "wide":
        return [pair(_between(rng, fmt.qmin + p, top)) for _ in range(n)]
    if stratum == "underflow":
        # Products from below eta to past 2^(2kp) eta, near one another in each case, so that
        # their sum is small too and the term tau of the bound can be the larger part.
        e0 = rng.between(fmt.qmin - p - 1, fmt.emin_normal + 2 * k * p + 2)
        return [pair(e0 - rng.below(p)) for _ in range(n)]
    if stratum == "zeros":
        e0 = _between(rng, lo_mid, top)
        out = []
        allz = rng.chance(1, 4)
        for _ in range(n):
            e = pair(e0)
            if allz or rng.bits(1):
                if rng.bits(1):
                    e = (0,) * ka + e[ka:]
                else:
                    e = e[:ka] + (0,) * kb
            out.append(e)
        return out
    if stratum == "cancel":
        e0 = _between(rng, lo_mid, top)
        out = [pair(e0 - rng.below(2)) for _ in range(n)]
        if n >= 2:
            j = rng.below(n)
            rest = sum(_value_frac(e[:ka], fmt) * _value_frac(e[ka:], fmt)
                       for i, e in enumerate(out) if i != j)
            x = _value_frac(out[j][:ka], fmt)
            if x:
                t = _nearest(fmt, rng, -rest / x, kb)
                if t is not None:
                    out[j] = out[j][:ka] + t
        return out
    if stratum == "overflow":
        kind = rng.below(3)
        s = rng.sign()
        out = []
        for i in range(n):
            e = pair(fmt.emax + 1 - rng.below(3))
            if kind == 0 and n >= 2:
                prod_pos = (e[0] > 0) == (e[ka] > 0)
                want = s if i < max(1, n // 2) else -s
                if prod_pos != (want > 0):
                    e = tuple(-t for t in e[:ka]) + e[ka:]
            out.append(e)
        return out
    if stratum == "tight":
        return _tight_dot(gen, rng, n, ka, kb)
    if stratum == "tail":
        e0 = _between(rng, lo_mid, top)
        modes = ("half+", "half-", "quarter-", "max", "eta", "tiny", "near")
        out = []
        while len(out) < n:
            e = pair(e0 - rng.below(2), modes[rng.below(len(modes))], modes[rng.below(len(modes))])
            out.append(e)
            if len(out) < n:
                # The same leading product with the other sign, other second limbs.
                x0, y0 = e[0], e[ka]
                out.append(_elem(fmt, rng, -x0, ka, modes[rng.below(len(modes))])
                           + _elem(fmt, rng, y0, kb, modes[rng.below(len(modes))]))
        _shuffle(rng, out)
        return out
    raise G.GenError("unknown stratum %r" % stratum)


def _tight_dot(gen, rng, n, ka, kb):
    """A first product a = x_0 y_0 and products just below half a unit of a (for two limbs, of a's
    second limb) as x_i y_i = d * 1; for two limbs, sometimes the literature's tight case of
    mul_2_2 as the only element."""
    fmt = gen.fmt
    p = fmt.p
    k = max(ka, kb)
    top = _safe_top(fmt, n)
    e0 = _between(rng, min(fmt.emin_normal + 2 * k * p + 4, top), top)
    s = rng.sign()
    if k == 2 and rng.bits(1):
        lit = _literature(fmt, rng, ("mul_2_2",))
        if lit is not None:
            x, y = lit
            x = [s * v for v in x]
            return [tuple(x) + tuple(y)] + [(0,) * ka + (0,) * kb] * max(0, n - 1)
    one = (1 << -fmt.qmin) if fmt.qmin < 0 else None
    if one is None or not F.is_member(fmt, one):
        one = 1 << (fmt.emin_normal - fmt.qmin)
    e0 = _clamp(fmt, e0)
    a0 = s * (1 << (e0 - fmt.qmin) if rng.bits(1) else G.in_binade(fmt, rng, e0))
    unit_y = (one,) + (0,) * (kb - 1)
    if ka == 1:
        h = F.ulp(fmt, a0) >> 1
        d = F.pred(fmt, h) if h > 1 else 0
        first = (a0,) + unit_y
        return [first] + [(s * d,) + unit_y] * (n - 1)
    a = (a0, G.tail_for(fmt, rng, a0, "max"))
    h = F.ulp(fmt, a[1]) >> 1 if a[1] else 0
    d = F.pred(fmt, h) if h > 1 else 0
    t = d if a[1] > 0 else -d
    first = a + unit_y
    return [first] + [(t, 0) + unit_y] * (n - 1)


def make_elements(gen, rng, stratum, n):
    """(elements, negz) of one case."""
    sh = gen.shape
    base = stratum
    if stratum == "nonfinite":
        base = ("one", "wide", "cancel")[rng.below(3)]
    if sh.kind == "sum":
        elems = _sum_values(gen, rng, base, n, sh.ka)
    else:
        elems = _dot_values(gen, rng, base, n, sh.ka, sh.kb)
    # (A construction with a first element writes it even for n = 0.)
    elems = list(elems)[:n]
    if len(elems) != n:
        raise G.GenError("stratum %s wrote %d elements for %d" % (stratum, len(elems), n))
    if stratum == "nonfinite" and n:
        elems = list(elems)
        width = len(elems[0])
        for _ in range(1 + rng.below(3)):
            i = rng.below(n)
            e = list(elems[i])
            groups = [(0, sh.ka)] + ([(sh.ka, sh.ka + sh.kb)] if sh.kind == "dot" else [])
            lo, hi = groups[rng.below(len(groups))]
            v = (INF, NINF, NAN)[rng.below(3)]
            e[lo:hi] = [v] * (hi - lo) if v == NAN else [v] + [0] * (hi - lo - 1)
            if sh.kind == "dot" and rng.chance(1, 3):
                # 0 * inf: the other factor zero.
                olo, ohi = groups[1] if lo == 0 else groups[0]
                e[olo:ohi] = [0] * (ohi - olo)
            elems[i] = tuple(e)
            assert len(e) == width
    negz = set()
    for i, e in enumerate(elems):
        for j, v in enumerate(e):
            if v == 0 and rng.chance(1, 4):
                negz.add((i, j))
    return list(elems), negz


# ---------------------------------------------------------------------------
# Every array of a tiny format

class ExhaustiveFoldGen:
    def __init__(self, fold, fmt, max_length, index_tags=True):
        self.fold = fold
        self.fmt = fmt
        if max_length is None or max_length < 0:
            raise G.GenError("an enumeration of %s needs --max-length L >= 0" % fold.name)
        self.max_length = max_length
        doms = []
        for n, l in fold.arrays:
            if l == 1:
                doms.append([(v,) for v in F.all_values(fmt)] + [(INF,), (NINF,), (NAN,)])
            elif l == 2:
                doms.append(list(G.normalized_pairs(fmt)) + [(INF, 0), (NINF, 0), (NAN, NAN)])
            else:
                raise G.GenError("%s: an enumeration of arrays of %d limbs" % (fold.name, l))
        dom = [()]
        for d in doms:
            dom = [a + b for a in dom for b in d]
        self.dom = dom
        self.lanes = "lanes" in fold.orders
        self.seq = "sequential" in fold.orders
        self.blocks = []
        total = 0
        D = len(dom)
        for n in range(max_length + 1):
            orders = (["seq"] if self.seq else []) + (
                ["lanes:%d" % W for W in range(2, n + 1)] if self.lanes else [])
            if not orders:
                orders = ["lanes:1"]
            size = D ** n * len(orders)
            self.blocks.append((total, n, orders))
            total += size
        self.total = total
        self.index_tags = index_tags
        self.restrict_text = "none"
        self.texts = [[F.to_hex(v, fmt.qmin) if type(v) is int else v for v in e] for e in dom]

    def header(self, start, count):
        return ("# kairn-oracle gen event=begin kernel=%s format=%s mode=exhaustive total=%d "
                "maxlen=%d restrict=none skip=none start=%d count=%d" % (
                    self.fold.name, self.fmt.name, self.total, self.max_length, start, count))

    def case(self, i):
        for base, n, orders in reversed(self.blocks):
            if i >= base:
                break
        r = i - base
        o = orders[r % len(orders)]
        a = r // len(orders)
        D = len(self.dom)
        idx = []
        for _ in range(n):
            a, d = divmod(a, D)
            idx.append(d)
        idx.reverse()
        width = len(self.dom[0])
        toks = [self.fold.name, self.fmt.name, o, str(n)]
        for j in range(width):
            toks.extend(self.texts[d][j] for d in idx)
        toks.append("#exhaustive:%d" % i if self.index_tags else "#exhaustive")
        return " ".join(toks)

    def lines(self, start, count):
        count = max(0, min(count, self.total - start))
        yield self.header(start, count)
        for i in range(start, start + count):
            yield self.case(i)
        yield "# kairn-oracle gen event=end lines=%d" % count
