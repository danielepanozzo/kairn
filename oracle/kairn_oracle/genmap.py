"""Request lines of the maps, the convolutions and the folds of maxima (architecture.md, "The line
protocol": "Maps", "Convolutions", "Folds"): random arrays in strata, and every array of a tiny
format up to a small length.

    MAP FORMAT ORDER N SCALAR... LIMB... #STRATUM:INDEX
    CONV FORMAT seq N_X N_Y LIMB... #STRATUM:INDEX
    FOLD FORMAT ORDER N LIMB... #STRATUM:INDEX            (a fold of maxima, norm_upper_k)

Random mode is counter-based, as for the folds (genfold.py): case i depends only on (name, format,
seed, strata, orders, largest length) and i, all in the header; the lengths take turns by the
folds' schedule of 17 places (0, 1, 2, 3, 4, 5, 7, 8, 9, 16, 17 and random lengths from 18 to the
largest), the orders are drawn from those asked for (seq, lanes:0, 1, 2, 3, 4, 5, 8, lanes:big).

A map's elements are aimed at the corners of its step, element by element: in a case of stratum S
three elements in four take S's corner and the others an ordinary one (`one`), so that a case of
the overflow stratum has finite elements beside those that overflow and the flag and the second
pass are put to the test.  The scalars are drawn once per case, for the stratum (a scalar that
makes the products overflow, a power of two that scales into the subnormal range, ...).  The steps
are read from the value of the map: a sum or a difference of two arrays (add_k, sub_k and their
entry forms), a product of an array by a scalar (scale_k), by a power of two (mul_pow2_map_k), and
a x + y (axpy_k):

    one        operands in nearby binades, random signs
    wide       operands anywhere a result cannot overflow
    cancel     the result cancels: y within a few units of -x (of x for a difference), y of
               -(a x) rounded for axpy; for a scaling, a scalar of one bit and elements that make
               x a an exact zero-free product
    tie        results halfway between two numbers of the format: sums N 2^E with N odd; for a
               scaling of one limb a = 3 2^k and x = m 2^e with 3m odd of p + 1 bits; for axpy a x
               exact and y an odd multiple of half its unit; for two limbs the second limbs at half
               a unit
    exact      short significands: results that are numbers of the format
    overflow   results beyond Omega from finite operands (top binades of one sign, Omega and half
               its unit, a scalar that brings the products past Omega), beside finite ones
    underflow  results in the subnormal range (a power of two or a scalar that scales into it)
    zeros      zeros of both signs, a zero scalar, results that are exactly zero
    nonfinite  one to three elements with an operand infinite or a NaN, or a scalar that is not
               finite, or 0 * inf
    tight      the closest to the step's bound: sums 2^E + u 2^E (a tie: the rounding error is u
               of the result, its whole bound) and, for two limbs, the literature's tight case of
               the step's sum (tight.py); products just below a midpoint (a = 1 + 2u, x = 1 - u);
               for axpy the cases of gen6.py's tight stratum, both roundings losing u the same way;
               for a power of two, products that are odd multiples of eta/2
    tail       (two limbs) leading limbs that cancel, second limbs at the extremes of the invariant

A convolution has two lengths, by a schedule of 13 places that pairs 0 and 1 on either side with
every other length and unequal lengths with each other ((0, 0), (0, n), (n, 0), (1, 1), (1, n),
(n, 1), (2, 3), (3, 2), (n, m) random); its strata are those of the dot products (genfold.py):
one, wide, sign, cancel (one coefficient cancels), zeros, underflow, overflow, nonfinite, tight
(y all ones and x the tight case of a sum, so that every coefficient is a sum at its bound; for
two limbs the literature's case of mul_2_2 in the first term), pow2, tail (two limbs).

A fold of maxima reads one array; its strata place the largest magnitude:

    one, wide  magnitudes in two adjacent binades, or anywhere; random signs
    ties       the largest magnitude attained more than once, with both signs and other tails
    position   the largest at the first, the last, the end of a lane or the start of the remainder
    zeros      zeros of both signs, every element zero half of the time
    underflow  subnormal and low normal magnitudes
    top        Omega and its neighbours: (Omega, a tail below zero), whose step up is +inf; (Omega,
               a tail above zero), beyond Omega; the predecessor of Omega with half a unit above
    nonfinite  one to three elements infinite or a NaN, anywhere (the last, a lane's)
    tail       (two limbs) the largest leading limb with a tail of its sign (the value above it),
               of the other sign, or zero

Exhaustive mode (--exhaustive --max-length L) enumerates every array of every length up to L,
every element any value of its domain (every number of the format, the infinities and NaN for one
limb; every canonical pair for two), and for a map every value of each scalar's domain (a power of
two for power_of_two()), in every order that differs: seq, and lanes:W for W = 2 to the length.
For a convolution every pair of lengths up to L each, every array of those lengths.
"""

import hashlib

from . import fmt as F
from . import gen as G
from . import gen2 as G2
from . import gen5 as G5
from . import gen6 as G6
from . import genfold as GF
from .claims import format_u_eta

INF, NINF, NAN = F.POS_INF, F.NEG_INF, F.NAN
NF = (INF, NINF, NAN)

MAP_STRATA = ("one", "wide", "cancel", "tie", "exact", "overflow", "underflow", "zeros",
              "nonfinite", "tight", "tail")
MAP_SCHEDULE = ("one", "tight", "cancel", "overflow", "tie", "underflow", "nonfinite", "tight",
                "wide", "cancel", "exact", "overflow", "zeros", "tail", "tight")
MAX_STRATA = ("one", "wide", "ties", "position", "zeros", "underflow", "top", "nonfinite", "tail")
MAX_SCHEDULE = ("one", "ties", "position", "top", "nonfinite", "wide", "ties", "underflow",
                "position", "zeros", "top", "nonfinite", "tail")
CONV_STRATA = GF.STRATA
CONV_SCHEDULE = GF.SCHEDULE
# The lengths of a convolution, (n_x, n_y): "r" a random length (18 to the largest, log-uniform
# as the folds' schedule), "s" a short one (2 to 9).
CONV_LENGTHS = ((0, 0), (0, "s"), ("s", 0), (1, 1), (1, "s"), ("s", 1), (2, 3), (3, 2),
                ("s", "s"), (1, "r"), ("r", 1), ("r", "s"), ("s", "r"))


def kind_of(obj):
    from . import maps as MP
    if isinstance(obj, MP.Map):
        return "map"
    if isinstance(obj, MP.Conv):
        return "conv"
    if getattr(obj, "maxima", False):
        return "max"
    return None


class MapShape:
    """The step of a map read from its value: sum (x + y, x - y), scale (x a), pow2 (x c, c a power
    of two), axpy (a x + y); the limbs of each group."""

    def __init__(self, m):
        self.m = m
        t = m.value_tree
        lim = m.limbs
        self.k = m.wlimbs
        self.scalar = m.scalars[0][0] if m.scalars else None
        if t[0] in ("+", "-") and t[1][0] == "name" and t[2][0] == "name" and not m.scalars:
            self.kind = "sum"
            self.sign = 1 if t[0] == "+" else -1
            self.x, self.y = t[1][1], t[2][1]
        elif t[0] == "*" and t[1][0] == "name" and t[2][0] == "name" and len(m.scalars) == 1:
            self.kind = "pow2" if self.scalar in m.pow2 else "scale"
            self.x = t[1][1] if t[1][1] != self.scalar else t[2][1]
            self.y = None
        elif (t[0] == "+" and t[1][0] == "*" and t[2][0] == "name" and len(m.scalars) == 1
              and self.scalar in (t[1][1][1], t[1][2][1])):
            self.kind = "axpy"
            self.x = t[1][2][1] if t[1][1][1] == self.scalar else t[1][1][1]
            self.y = t[2][1]
        else:
            raise G.GenError("%s: the generator writes maps whose value is x + y, x - y, x a or "
                             "a x + y, not %r" % (m.name, m.value_text))
        self.kx = lim[self.x]
        self.ky = lim[self.y] if self.y else None
        self.ka = lim[self.scalar] if self.scalar else None
        if max(lim.values()) > 2:
            raise G.GenError("%s: groups of more than two limbs are not generated" % m.name)
        self.two = max(lim.values()) == 2


# ---------------------------------------------------------------------------
# Numbers

def _num(fmt, rng, e, style="uniform", sign=None):
    v = G.in_binade(fmt, rng, max(fmt.qmin, min(fmt.emax, e)), style)
    return (rng.sign() if sign is None else sign) * v


def _grp(fmt, rng, x0, k, mode=None):
    """A group of k limbs led by the number x0 (a tail by mode, or near / any)."""
    if k == 1:
        return [x0]
    if mode is None:
        mode = "near" if rng.chance(3, 4) else "any"
    return [x0, G.tail_for(fmt, rng, x0, mode)]


def _nonfinite(rng, k):
    v = NF[rng.below(3)]
    return [v] + ([NAN] * (k - 1) if v == NAN else [0] * (k - 1))


def _scaled(fmt, q, e):
    """The rational q 2^e as a fixed value when it is a number of the format, else None."""
    return G6._scaled_exact(fmt, q, e)


def _mid(fmt, k):
    return G._mid(fmt, (k + 1) * fmt.p + 2, 3)


def _nearest(fmt, rng, vq, k):
    """The k-limb canonical number nearest to vq, given in units of eta (a Fraction)."""
    t = G5._expansion_near(fmt, rng, vq, k)
    return list(t) if t is not None else None


def _frac(fmt, limbs):
    return G6._value(fmt, limbs) * G6._per_eta(fmt)


def _jitter(fmt, rng, g):
    """g moved by a unit or two in one of its limbs, kept normalized."""
    g = list(g)
    for _ in range(rng.below(3)):
        j = len(g) - 1 if rng.bits(1) else 0
        nb = F.succ(fmt, g[j]) if rng.bits(1) else F.pred(fmt, g[j])
        if type(nb) is int:
            g2 = list(g)
            g2[j] = nb
            if len(g) == 1 or F.normalized_limbs(fmt, g2):
                g = g2
    return g


# ---------------------------------------------------------------------------
# Maps: the scalars, then each element by its mode

def _sum_elem(gen, rng, mode):
    fmt, sh = gen.fmt, gen.shape
    k, s, p = sh.k, sh.sign, fmt.p
    lo, hi = _mid(fmt, k)
    if mode == "one":
        e = rng.between(lo, hi)
        x = _grp(fmt, rng, _num(fmt, rng, e), k)
        y = _grp(fmt, rng, _num(fmt, rng, e - rng.between(-(p + 2), p + 2)), k)
    elif mode == "wide":
        x = _grp(fmt, rng, _num(fmt, rng, rng.between(fmt.qmin, fmt.emax - 2)), k)
        y = _grp(fmt, rng, _num(fmt, rng, rng.between(fmt.qmin, fmt.emax - 2)), k)
    elif mode == "cancel":
        x = _grp(fmt, rng, _num(fmt, rng, rng.between(lo, hi)), k)
        y = _jitter(fmt, rng, [-s * v for v in x])
    elif mode == "tie" and k == 1:
        a, b = G2._tie(fmt, rng, False)
        x, y = [a], [s * b]
    elif mode == "exact":
        e = rng.between(lo, hi)
        x = _grp(fmt, rng, _num(fmt, rng, e, "short"), k, "zero")
        y = _grp(fmt, rng, _num(fmt, rng, e - rng.between(0, p), "short"), k, "zero")
    elif mode == "overflow":
        t = rng.below(3)
        sg = rng.sign()
        if t == 0:
            x = _grp(fmt, rng, sg * fmt.omega, k, "zero")
            q = F.ulp(fmt, fmt.omega) >> rng.between(1, 3)
            y = _grp(fmt, rng, s * sg * max(q, 1), k, "zero")
        else:
            x = _grp(fmt, rng, sg * G.in_binade(fmt, rng, fmt.emax - rng.below(2), "high"), k)
            y = _grp(fmt, rng, s * sg * G.in_binade(fmt, rng, fmt.emax - rng.below(2), "high"), k)
    elif mode == "underflow":
        x = [G2.limb(fmt, rng, "underflow")]
        y = [G2.limb(fmt, rng, "underflow")]
        x, y = _grp(fmt, rng, x[0], k), _grp(fmt, rng, y[0], k)
    elif mode == "zeros":
        # Both zero; x and a zero; or y = -x (x for a difference): an exact zero.
        t = rng.below(3)
        x = [0] * k if t == 0 else _grp(fmt, rng, _num(fmt, rng, rng.between(lo, hi)), k)
        y = [0] * k if t < 2 else [-s * v for v in x]
        if rng.bits(1):
            x, y = [s * v for v in y], [s * v for v in x]
    elif mode == "tight":
        if k == 1:
            # 2^E + u 2^E: a tie that rounds to the even 2^E, an error of u 2^E = u/(1+u) of the
            # sum.
            E = rng.between(lo, hi)
            sg = rng.sign()
            x = [sg * (1 << (E - fmt.qmin))] if E >= fmt.qmin else [sg]
            yv = _scaled(fmt, G6.Fraction(1, 1 << p), E)
            y = [s * sg * yv] if yv is not None else [0]
            if rng.bits(1):
                x, y = [s * v for v in y], [s * v for v in x]
        else:
            lit = GF._literature(fmt, rng, ("add_2_2" if s > 0 else "sub_2_2",))
            if lit is None:
                return _sum_elem(gen, rng, "tail")
            sg = rng.sign()
            x, y = [sg * v for v in lit[0]], [sg * v for v in lit[1]]
    else:                                            # tail (two limbs), tie of two limbs
        x0 = _num(fmt, rng, rng.between(lo, hi))
        modes = ("half+", "half-", "quarter-", "max", "eta", "tiny", "near")
        x = _grp(fmt, rng, x0, k, modes[rng.below(len(modes))])
        y = _grp(fmt, rng, -s * x0, k, modes[rng.below(len(modes))])
    return {sh.x: x, sh.y: y}


def _scale_scalar(gen, rng, stratum):
    """The scalar of a scaling (x a) or of axpy (a x + y) for a case of the stratum."""
    fmt, sh = gen.fmt, gen.shape
    ka, p = sh.ka, fmt.p
    if stratum == "overflow":
        return _grp(fmt, rng, _num(fmt, rng, fmt.emax - rng.between(0, p)), ka)
    if stratum == "underflow":
        return _grp(fmt, rng, _num(fmt, rng, rng.between(fmt.qmin, fmt.emin_normal + p)), ka)
    if stratum == "zeros" and rng.bits(1):
        return [0] * ka
    if stratum in ("exact", "cancel"):
        return [rng.sign() * (1 << max(0, rng.between(-p, p) - fmt.qmin))] + [0] * (ka - 1)
    if stratum == "tie" and ka == 1 and p >= 2:
        v = _scaled(fmt, G6.Fraction(3), rng.between(-p, p))
        if v is not None:
            return [rng.sign() * v]
    if stratum == "tight":
        # Two-limb elements: the literature's tight case of the product (mul_2_2, or mul_2_1 for
        # a one-limb scalar), the scalar its factor; one limb: a = 1 + 2u, x = 1 - u.
        if sh.kx == 2:
            lit = GF._literature(fmt, rng, ("mul_2_2",) if ka == 2 else ("mul_2_1",))
            if lit is not None:
                gen.tight_lit = lit
                a = lit[0] if ka == 2 else lit[1]
                return [rng.sign() * v for v in a]
        elif ka == 1 and p >= 2:
            v = _scaled(fmt, 1 + G6.Fraction(2, 1 << p), rng.between(-p, p))
            if v is not None:
                gen.tight_a = 1
                return [rng.sign() * v]
    if stratum == "nonfinite" and rng.chance(1, 4):
        return _nonfinite(rng, ka)
    lo, hi = _mid(fmt, max(ka, sh.kx))
    return _grp(fmt, rng, _num(fmt, rng, rng.between(-p, p) if rng.bits(1) else
                               rng.between(lo, hi) // 2), ka)


def _pow2_scalar(gen, rng, stratum):
    fmt, p = gen.fmt, gen.fmt.p
    if stratum in ("underflow", "tight"):
        n = rng.between(fmt.qmin, min(fmt.emax, -p))
    elif stratum == "overflow":
        n = rng.between(max(fmt.qmin, p), fmt.emax)
    else:
        n = rng.between(max(fmt.qmin, -2 * p), min(fmt.emax, 2 * p))
    return [1 << (max(fmt.qmin, min(fmt.emax, n)) - fmt.qmin)]


def _value_of(fmt, g):
    return G6._value(fmt, g)


def _prod_elem(gen, rng, mode, a):
    """x for a scaling x a or x c, aimed by mode at the product's corner."""
    fmt, sh = gen.fmt, gen.shape
    k, p = sh.kx, fmt.p
    av = _value_of(fmt, a) if all(type(v) is int for v in a) else None
    ea = fmt.binade(a[0]) if type(a[0]) is int and a[0] else 0
    lo, hi = _mid(fmt, k)
    if mode == "overflow" and av:
        # Products just below, at and beyond Omega.
        e = fmt.emax - ea + rng.between(-1, 1)
        return _grp(fmt, rng, _num(fmt, rng, e, "high" if rng.bits(1) else "uniform"), k)
    if mode == "underflow" and av:
        e = rng.between(fmt.qmin - p - 1, fmt.emin_normal + p) - ea
        return _grp(fmt, rng, _num(fmt, rng, e), k)
    if mode == "tie" and k == 1 and av:
        # a = 3 2^k: x = m 2^e with m odd and 3m of p + 1 bits, so x a is halfway.
        m = rng.between(-(-(1 << p) // 3), ((2 << p) - 1) // 3) | 1
        if m.bit_length() <= p:
            v = _scaled(fmt, G6.Fraction(m), rng.between(lo, hi) - p - ea)
            if v is not None:
                return [rng.sign() * v]
    if mode == "tight" and av:
        if sh.kind == "pow2":
            # x c an odd multiple of eta/2 (c = 2^ea): a tie in the subnormal range, an error
            # of eta/2; for two limbs a second limb at the extremes, which c brings there.
            if k == 1:
                m = (rng.bits(min(p - 1, 6)) << 1) | 1
                v = _scaled(fmt, G6.Fraction(m), fmt.qmin - 1 - ea)
                if v is not None:
                    return [rng.sign() * v]
            else:
                x0 = _num(fmt, rng, rng.between(lo, hi))
                return _grp(fmt, rng, x0, 2, "half+" if rng.bits(1) else "max")
        elif getattr(gen, "tight_a", None) and k == 1:
            v = _scaled(fmt, 1 - G6.Fraction(1, 1 << p), rng.between(lo, hi) - ea)
            if v is not None:
                return [rng.sign() * v]
        elif getattr(gen, "tight_lit", None) is not None:
            lit = gen.tight_lit
            x = lit[1] if sh.ka == 2 else lit[0]
            d = rng.between(-p, p)
            out = [G6._scaled_exact(fmt, G6._value(fmt, [v]), d) for v in x]
            if all(o is not None for o in out) and (k == 1 or F.normalized_limbs(fmt, out)):
                sg = rng.sign()
                return [sg * o for o in out]
    if mode == "exact":
        return _grp(fmt, rng, _num(fmt, rng, rng.between(lo, hi) - ea, "short"), k, "zero")
    if mode == "zeros":
        return [0] * k
    if mode == "tail" and k == 2:
        modes = ("half+", "half-", "quarter-", "max", "eta", "tiny")
        return _grp(fmt, rng, _num(fmt, rng, rng.between(lo, hi) - ea), 2,
                    modes[rng.below(len(modes))])
    if mode == "wide":
        return _grp(fmt, rng, _num(fmt, rng, rng.between(fmt.qmin, fmt.emax) - ea), k)
    return _grp(fmt, rng, _num(fmt, rng, rng.between(lo, hi) - ea // 2 - rng.between(0, p)), k)


def _axpy_elem(gen, rng, mode, a):
    fmt, sh = gen.fmt, gen.shape
    kx, ky, p = sh.kx, sh.ky, fmt.p
    x = _prod_elem(gen, rng, mode if mode != "cancel" else "one", a)
    fin = all(type(v) is int for v in a) and all(type(v) is int for v in x)
    P = _frac(fmt, a) * _value_of(fmt, x) if fin else None
    lo, hi = _mid(fmt, ky)
    # The binade of RN(a x), when it is a finite number other than zero.
    rp = G5._rn_frac(fmt, P) if P else None
    ep = fmt.binade(rp) if type(rp) is int and rp else None
    if mode == "cancel" and P is not None:
        y = _nearest(fmt, rng, -P, ky)
        y = _jitter(fmt, rng, y) if y is not None else [0] * ky
    elif mode == "tie" and P:
        r = G5._rn_frac(fmt, P)
        u0 = F.ulp(fmt, r) if type(r) is int and r else 1
        v = rng.sign() * (2 * rng.below(4) + 1) * u0
        v = v // 2 if u0 > 1 else v
        y = [v if F.is_member(fmt, v) else rng.sign() * u0] + [0] * (ky - 1)
    elif mode == "tight" and P is not None and getattr(gen, "tight_a", None) and ky == 1:
        # y = u (of a x's binade), of a x's sign: the sum a tie that rounds down.
        v = _scaled(fmt, G6.Fraction(1, 1 << p), ep) if ep is not None else None
        y = [(1 if P > 0 else -1) * v] if v is not None else [0]
    elif mode == "tight" and getattr(gen, "tight_lit", None) is not None:
        y = [0] * ky
    elif mode == "overflow" and rng.bits(1):
        sg = 1 if (P is None or P >= 0) else -1
        y = _grp(fmt, rng, sg * G.in_binade(fmt, rng, fmt.emax - rng.below(2), "high"), ky)
    elif mode == "underflow":
        y = _grp(fmt, rng, G2.limb(fmt, rng, "underflow"), ky)
    elif mode == "zeros":
        y = [0] * ky
    elif mode == "exact":
        y = _grp(fmt, rng, _num(fmt, rng, rng.between(lo, hi), "short"), ky, "zero")
    elif mode == "tail" and ky == 2 and P is not None:
        y = _nearest(fmt, rng, -P, ky) or [0, 0]
        modes = ("half+", "half-", "quarter-", "max", "eta", "tiny")
        y = _grp(fmt, rng, y[0], 2, modes[rng.below(len(modes))])
    else:
        e = ep if ep is not None else rng.between(lo, hi)
        y = _grp(fmt, rng, _num(fmt, rng, e - rng.between(-(p + 2), p + 2)), ky)
    return {sh.x: x, sh.y: y}


def _elem_nonfinite(gen, rng, el):
    """One operand of an element replaced by an infinity or a NaN (for a product sometimes the
    other factor made zero: 0 * inf)."""
    sh = gen.shape
    names = [n for n in (sh.x, sh.y) if n]
    n = names[rng.below(len(names))]
    el[n] = _nonfinite(rng, len(el[n]))
    return el


class RandomMapGen:
    def __init__(self, m, fmt, seed, strata=None, orders=None, max_length=None, index_tags=True):
        self.fold = self.m = m
        self.fmt = fmt
        self.shape = MapShape(m)
        known = MAP_STRATA if self.shape.two else tuple(s for s in MAP_STRATA if s != "tail")
        schedule = MAP_SCHEDULE if self.shape.two else tuple(s for s in MAP_SCHEDULE
                                                              if s != "tail")
        _setup(self, m, seed, strata, orders, max_length, index_tags, known, schedule, "map")

    def make(self, rng, stratum, n):
        sh, fmt = self.shape, self.fmt
        self.tight_a = self.tight_lit = None
        if sh.kind in ("scale", "axpy"):
            a = _scale_scalar(self, rng, stratum)
        elif sh.kind == "pow2":
            a = _pow2_scalar(self, rng, stratum)
        else:
            a = None
        elems = []
        for _ in range(n):
            mode = stratum if rng.chance(3, 4) else "one"
            if mode == "nonfinite":
                mode = ("one", "wide", "cancel")[rng.below(3)]
            if sh.kind == "sum":
                el = _sum_elem(self, rng, mode)
            elif sh.kind == "axpy":
                el = _axpy_elem(self, rng, mode, a)
            else:
                el = {sh.x: _prod_elem(self, rng, mode, a)}
            elems.append(el)
        if stratum == "nonfinite" and n:
            for _ in range(1 + rng.below(3)):
                i = rng.below(n)
                elems[i] = _elem_nonfinite(self, rng, elems[i])
                if sh.kind != "sum" and rng.chance(1, 3) and a is not None:
                    # 0 * inf, when the scalar may be zero (not a power of two).
                    if sh.kind != "pow2":
                        elems[i][sh.x] = _nonfinite(rng, sh.kx)
                        a = [0] * len(a)
        scal = {sh.scalar: a} if sh.scalar else {}
        return scal, elems

    def case(self, i):
        stratum = self.schedule[i % len(self.schedule)]
        rng = G.CaseRandom(self.key, i)
        n = GF.RandomFoldGen.length(self, rng, i)
        o = self.orders[rng.below(len(self.orders))]
        if o == "lanes:big":
            o = "lanes:%d" % (n + 1 + rng.below(8))
        for _attempt in range(16):
            scal, elems = self.make(rng, stratum, n)
            if valid_map(self.fmt, self.m, scal, elems):
                break
        else:
            raise G.GenError("could not generate a valid case %d (%s)" % (i, stratum))
        return map_text(self.m, self.fmt, o, scal, elems, rng,
                        "#%s:%d" % (stratum, i) if self.index_tags else "#" + stratum)


def _setup(g, obj, seed, strata, orders, max_length, index_tags, known, schedule, what):
    if strata:
        for s in strata:
            if s not in known:
                raise G.GenError("unknown stratum %r for %s (known: %s)"
                                 % (s, obj.name, ", ".join(known)))
        g.schedule = tuple(s for s in schedule if s in strata) or tuple(strata)
        g.strata = list(strata)
    else:
        g.schedule = schedule
        g.strata = list(known)
    g.orders = GF.order_specs(obj, orders) if what != "conv" else _conv_orders(obj, orders)
    g.max_length = GF.DEFAULT_MAX_LENGTH if max_length is None else max_length
    if g.max_length < 0:
        raise G.GenError("the maximum length is negative")
    g.seed = seed
    g.key = hashlib.blake2b(("kairn-oracle/%s|%s|%s|%s|%s|%s|%d" % (
        what, seed, obj.name, g.fmt.name, ",".join(g.strata), ",".join(g.orders),
        g.max_length)).encode(), digest_size=32).digest()
    g.index_tags = index_tags
    g.u, g.eta = format_u_eta(g.fmt)


def _conv_orders(c, orders):
    specs = list(orders) if orders else ["seq"]
    if specs != ["seq"] * len(specs):
        raise G.GenError("%s: a convolution has the order seq only" % c.name)
    return ["seq"]


def _header(g, start, count):
    return ("# kairn-oracle gen event=begin kernel=%s format=%s mode=random seed=%s strata=%s "
            "orders=%s maxlen=%d start=%d count=%d" % (
                g.fold.name, g.fmt.name, g.seed, ",".join(g.strata), ",".join(g.orders),
                g.max_length, start, count))


def _lines(g, start, count):
    yield _header(g, start, count)
    for i in range(start, start + count):
        yield g.case(i)
    yield "# kairn-oracle gen event=end lines=%d" % count


RandomMapGen.header = _header
RandomMapGen.lines = _lines


def _tok(fmt, v, neg):
    if type(v) is not int:
        return v
    if v == 0:
        return "-0x0p+0" if neg else "0x0p+0"
    return F.to_hex(v, fmt.qmin)


def map_text(m, fmt, order, scal, elems, rng, tag):
    toks = [m.name, fmt.name, order, str(len(elems))]
    for n, _l in m.scalars:
        toks.extend(_tok(fmt, v, rng.chance(1, 4)) for v in scal[n])
    for n, l in m.arrays:
        for j in range(l):
            toks.extend(_tok(fmt, e[n][j], rng.chance(1, 4)) for e in elems)
    toks.append(tag)
    return " ".join(toks)


def _valid_group(fmt, g, l, pow2=False):
    if len(g) != l:
        return False
    for v in g:
        if type(v) is int:
            if not F.is_member(fmt, v):
                return False
        elif v not in NF:
            return False
    if pow2:
        v = g[0]
        return type(v) is int and v > 0 and v & (v - 1) == 0
    return l == 1 or _canon(fmt, g)


def _canon(fmt, g):
    from .gen3 import _canonical
    return _canonical(fmt, list(g))


def valid_map(fmt, m, scal, elems):
    """Every group a value of its domain, written from the definitions (gen3's canonical): any
    value for one limb, canonical for two, a finite power of two for power_of_two()."""
    lim = m.limbs
    for n, _l in m.scalars:
        if n not in scal or not _valid_group(fmt, scal[n], lim[n], n in m.pow2):
            return False
    for e in elems:
        for n, _l in m.arrays:
            if n not in e or not _valid_group(fmt, e[n], lim[n]):
                return False
    return True


# ---------------------------------------------------------------------------
# Folds of maxima

class RandomMaxGen:
    def __init__(self, fold, fmt, seed, strata=None, orders=None, max_length=None,
                 index_tags=True):
        self.fold = fold
        self.fmt = fmt
        if len(fold.arrays) != 1 or fold.value_tree[0] != "abs":
            raise G.GenError("%s: the generator writes folds of maxima of abs(ARRAY)" % fold.name)
        self.k = fold.arrays[0][1]
        known = MAX_STRATA if self.k == 2 else tuple(s for s in MAX_STRATA if s != "tail")
        schedule = MAX_SCHEDULE if self.k == 2 else tuple(s for s in MAX_SCHEDULE if s != "tail")
        _setup(self, fold, seed, strata, orders, max_length, index_tags, known, schedule, "max")

    header = _header
    lines = _lines

    def make(self, rng, stratum, n, W):
        fmt, k, p = self.fmt, self.k, self.fmt.p
        lo, hi = _mid(fmt, k)
        if stratum == "wide":
            out = [_grp(fmt, rng, _num(fmt, rng, rng.between(fmt.qmin, fmt.emax)), k)
                   for _ in range(n)]
        elif stratum == "underflow":
            out = [_grp(fmt, rng, G2.limb(fmt, rng, "underflow"), k) for _ in range(n)]
        elif stratum == "zeros":
            # Every element zero half of the time (V = 0 from elements, not only from none).
            allz = rng.chance(1, 2)
            e = rng.between(lo, hi)
            out = [[0] * k if allz or rng.bits(1) else _grp(fmt, rng, _num(fmt, rng, e), k)
                   for _ in range(n)]
        else:
            e = rng.between(lo, hi)
            out = [_grp(fmt, rng, _num(fmt, rng, e - rng.below(2)), k) for _ in range(n)]
        if not n:
            return out
        # The largest element, placed.
        top = None
        if stratum in ("ties", "position", "tail", "one", "nonfinite"):
            m0 = max(abs(g[0]) for g in out)
            v = F.succ(fmt, m0) if m0 else 1
            v = v if type(v) is int else m0
            modes = ("half+", "half-", "quarter-", "max", "eta", "zero", "near")
            top = _grp(fmt, rng, rng.sign() * v, k, modes[rng.below(len(modes))])
        elif stratum == "top":
            om = fmt.omega
            t = rng.below(4)
            if t < 2 and k == 2:
                top = [rng.sign() * om, 0]
                tl = G.tail_for(fmt, rng, top[0], "half-" if t == 0 else "half+")
                top[1] = tl
            elif t == 2:
                top = _grp(fmt, rng, rng.sign() * F.pred(fmt, om), k, "half+")
            else:
                top = [rng.sign() * om] + [0] * (k - 1)
        if top is not None:
            if stratum == "position" or rng.bits(1):
                cands = [0, n - 1]
                if W and W > 1:
                    full = W * (n // W)
                    cands += [j for j in (W - 1, W, full - 1, full) if 0 <= j < n]
                pos = cands[rng.below(len(cands))]
            else:
                pos = rng.below(n)
            out[pos] = top
            if stratum == "ties" and n >= 2:
                for _ in range(1 + rng.below(2)):
                    j = rng.below(n)
                    out[j] = _grp(fmt, rng, -top[0] if rng.bits(1) else top[0], k,
                                  ("half+", "half-", "zero", "max")[rng.below(4)])
        if stratum == "nonfinite":
            for _ in range(1 + rng.below(3)):
                j = n - 1 if rng.chance(1, 4) else rng.below(n)
                out[j] = _nonfinite(rng, k)
        return out

    def case(self, i):
        stratum = self.schedule[i % len(self.schedule)]
        rng = G.CaseRandom(self.key, i)
        n = GF.RandomFoldGen.length(self, rng, i)
        o = self.orders[rng.below(len(self.orders))]
        if o == "lanes:big":
            o = "lanes:%d" % (n + 1 + rng.below(8))
        W = int(o[6:]) if o.startswith("lanes:") else 0
        for _attempt in range(16):
            out = self.make(rng, stratum, n, W)
            elems = [tuple(g) for g in out]
            if GF.valid_elements(self.fmt, self.fold, elems):
                break
        else:
            raise G.GenError("could not generate a valid case %d (%s)" % (i, stratum))
        negz = {(i2, j) for i2, e in enumerate(elems) for j, v in enumerate(e)
                if v == 0 and rng.chance(1, 4)}
        return GF.line_text(self.fold, self.fmt, o, elems, negz,
                            "#%s:%d" % (stratum, i) if self.index_tags else "#" + stratum)


# ---------------------------------------------------------------------------
# Convolutions

class RandomConvGen:
    def __init__(self, c, fmt, seed, strata=None, orders=None, max_length=None, index_tags=True):
        self.fold = c
        self.fmt = fmt
        (self.xn, self.kx), (self.yn, self.ky) = c.arrays
        two = max(self.kx, self.ky) == 2
        known = CONV_STRATA if two else tuple(s for s in CONV_STRATA if s != "tail")
        schedule = CONV_SCHEDULE if two else tuple(s for s in CONV_SCHEDULE if s != "tail")
        _setup(self, c, seed, strata, orders, max_length, index_tags, known, schedule, "conv")
        # The dot product's generator makes the pairs of each array's values.
        self.dot = GF.RandomFoldGen(c.fold, fmt, seed, None, None, max_length)

    header = _header
    lines = _lines

    def lengths(self, rng, i):
        L = self.max_length
        out = []
        for c in CONV_LENGTHS[i % len(CONV_LENGTHS)]:
            if c == "s":
                out.append(min(L, rng.between(2, 9)))
            elif c == "r":
                # Index 2 of the folds' schedule is a random length (18 to the largest).
                out.append(GF.RandomFoldGen.length(self, rng, 2))
            else:
                out.append(min(L, c))
        return out

    def make(self, rng, stratum, nx, ny):
        fmt, kx, ky = self.fmt, self.kx, self.ky
        m = max(nx, ny)
        base = stratum if stratum != "nonfinite" else ("one", "wide", "cancel")[rng.below(3)]
        if base == "tight":
            return self._tight(rng, nx, ny)
        pairs = GF._dot_values(self.dot, rng, "one" if base == "cancel" else base, m, kx, ky)
        xs = [tuple(e[:kx]) for e in pairs[:nx]]
        ys = [tuple(e[kx:]) for e in pairs[:ny]]
        if base == "cancel" and nx >= 2 and ny >= 1:
            # Coefficient j cancels: one x_i of its terms made the nearest to minus the others
            # over y_{j - i}.
            j = rng.below(nx + ny - 1)
            from .maps import conv_terms
            terms = conv_terms(nx, ny, j)
            if len(terms) >= 2:
                i0, k0 = terms[rng.below(len(terms))]
                yv = _frac(fmt, ys[k0]) / G6._per_eta(fmt)
                if yv:
                    rest = sum(G6._value(fmt, xs[i]) * G6._value(fmt, ys[k]) for i, k in terms
                               if i != i0)
                    t = _nearest(fmt, rng, -rest / yv * G6._per_eta(fmt), kx)
                    if t is not None:
                        xs[i0] = tuple(t)
        if stratum == "nonfinite" and (nx or ny):
            for _ in range(1 + rng.below(3)):
                if nx and (not ny or rng.bits(1)):
                    i = rng.below(nx)
                    xs[i] = tuple(_nonfinite(rng, kx))
                    if ny and rng.chance(1, 3):
                        ys[rng.below(ny)] = (0,) * ky
                else:
                    i = rng.below(ny)
                    ys[i] = tuple(_nonfinite(rng, ky))
        return xs, ys

    def _tight(self, rng, nx, ny):
        """y all ones and x the tight case of a sum (each addition drops one), so that every
        coefficient is a sum near its bound; or, for two limbs, the literature's case of mul_2_2
        in the first term."""
        fmt, kx, ky = self.fmt, self.kx, self.ky
        one = (1 << -fmt.qmin) if fmt.qmin < 0 else None
        if one is None or not F.is_member(fmt, one):
            one = 1 << (fmt.emin_normal - fmt.qmin)
        if max(kx, ky) == 2 and rng.bits(1):
            lit = GF._literature(fmt, rng, ("mul_2_2",))
            if lit is not None and nx and ny:
                xs = [tuple(lit[0])] + [(0,) * kx] * (nx - 1)
                ys = [tuple(lit[1])] + [(0,) * ky] * (ny - 1)
                return xs, ys
        sums = GF._tight_sum(self.dot, rng, max(nx, 1), kx)
        xs = [tuple(e) for e in sums[:nx]]
        ys = [(one,) + (0,) * (ky - 1)] * ny
        if rng.bits(1):
            # The roles swapped: x all ones, y the tight sum (reversed: the terms in increasing
            # i are y_j down to y_0).
            ys2 = [tuple(e) for e in GF._tight_sum(self.dot, rng, max(ny, 1), ky)[:ny]]
            return [(one,) + (0,) * (kx - 1)] * nx, ys2[::-1]
        return xs, ys

    def case(self, i):
        stratum = self.schedule[i % len(self.schedule)]
        rng = G.CaseRandom(self.key, i)
        nx, ny = self.lengths(rng, i)
        for _attempt in range(16):
            xs, ys = self.make(rng, stratum, nx, ny)
            ok = (GF.valid_elements(self.fmt, _One(self.kx, self.fold.requires, self.xn), xs)
                  and GF.valid_elements(self.fmt, _One(self.ky, self.fold.requires, self.yn), ys))
            if ok and len(xs) == nx and len(ys) == ny:
                break
        else:
            raise G.GenError("could not generate a valid case %d (%s)" % (i, stratum))
        return conv_text(self.fold, self.fmt, xs, ys, rng,
                         "#%s:%d" % (stratum, i) if self.index_tags else "#" + stratum)


class _One:
    """A stand-in fold of one array, for genfold.valid_elements."""

    def __init__(self, k, requires, name):
        self.arrays = [(name, k)]
        self.requires = [name] if name in requires else []


def conv_text(c, fmt, xs, ys, rng, tag):
    toks = [c.name, fmt.name, "seq", str(len(xs)), str(len(ys))]
    for arr, k in ((xs, c.arrays[0][1]), (ys, c.arrays[1][1])):
        for j in range(k):
            toks.extend(_tok(fmt, e[j], rng.chance(1, 4)) for e in arr)
    toks.append(tag)
    return " ".join(toks)


# ---------------------------------------------------------------------------
# Every array of a tiny format

def _domain(fmt, l, pow2=False):
    if pow2:
        return [(v,) for v in F.all_values(fmt) if v > 0 and v & (v - 1) == 0]
    if l == 1:
        return [(v,) for v in F.all_values(fmt)] + [(INF,), (NINF,), (NAN,)]
    if l == 2:
        return list(G.normalized_pairs(fmt)) + [(INF, 0), (NINF, 0), (NAN, NAN)]
    raise G.GenError("an enumeration of groups of %d limbs" % l)


def _texts(fmt, dom):
    return [[F.to_hex(v, fmt.qmin) if type(v) is int else v for v in e] for e in dom]


class ExhaustiveMapGen:
    """Every scalar and every array up to max_length (a map or a fold of maxima), every order
    that differs."""

    def __init__(self, obj, fmt, max_length, index_tags=True):
        self.fold = obj
        self.fmt = fmt
        if max_length is None or max_length < 0:
            raise G.GenError("an enumeration of %s needs --max-length L >= 0" % obj.name)
        self.max_length = max_length
        scalars = getattr(obj, "scalars", [])
        pow2 = getattr(obj, "pow2", [])
        self.sdom = [()]
        for n, l in scalars:
            self.sdom = [a + b for a in self.sdom for b in _domain(fmt, l, n in pow2)]
        dom = [()]
        for _n, l in obj.arrays:
            dom = [a + b for a in dom for b in _domain(fmt, l)]
        self.dom = dom
        self.blocks = []
        total = 0
        lanes = "lanes" in obj.orders
        for n in range(max_length + 1):
            orders = (["seq"] if "sequential" in obj.orders else []) + (
                ["lanes:%d" % W for W in range(2, n + 1)] if lanes else [])
            orders = orders or ["lanes:1"]
            size = len(self.sdom) * len(dom) ** n * len(orders)
            self.blocks.append((total, n, orders))
            total += size
        self.total = total
        self.index_tags = index_tags
        self.restrict_text = "none"
        self.etexts = _texts(fmt, dom)
        self.stexts = _texts(fmt, self.sdom)

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
        r //= len(orders)
        r, s = divmod(r, len(self.sdom))
        D = len(self.dom)
        idx = []
        for _ in range(n):
            r, d = divmod(r, D)
            idx.append(d)
        idx.reverse()
        toks = [self.fold.name, self.fmt.name, o, str(n)] + list(self.stexts[s])
        width = len(self.dom[0])
        for j in range(width):
            toks.extend(self.etexts[d][j] for d in idx)
        toks.append("#exhaustive:%d" % i if self.index_tags else "#exhaustive")
        return " ".join(toks)

    def lines(self, start, count):
        count = max(0, min(count, self.total - start))
        yield self.header(start, count)
        for i in range(start, start + count):
            yield self.case(i)
        yield "# kairn-oracle gen event=end lines=%d" % count


class ExhaustiveConvGen:
    """Every pair of arrays of lengths up to max_length each, each entry any value of its
    domain."""

    def __init__(self, c, fmt, max_length, index_tags=True):
        self.fold = c
        self.fmt = fmt
        if max_length is None or max_length < 0:
            raise G.GenError("an enumeration of %s needs --max-length L >= 0" % c.name)
        self.max_length = max_length
        (_, kx), (_, ky) = c.arrays
        self.dx, self.dy = _domain(fmt, kx), _domain(fmt, ky)
        self.tx, self.ty = _texts(fmt, self.dx), _texts(fmt, self.dy)
        self.kx, self.ky = kx, ky
        self.blocks = []
        total = 0
        for nx in range(max_length + 1):
            for ny in range(max_length + 1):
                size = len(self.dx) ** nx * len(self.dy) ** ny
                self.blocks.append((total, nx, ny))
                total += size
        self.total = total
        self.index_tags = index_tags
        self.restrict_text = "none"

    header = ExhaustiveMapGen.header

    def case(self, i):
        for base, nx, ny in reversed(self.blocks):
            if i >= base:
                break
        r = i - base
        ix, iy = [], []
        for _ in range(ny):
            r, d = divmod(r, len(self.dy))
            iy.append(d)
        for _ in range(nx):
            r, d = divmod(r, len(self.dx))
            ix.append(d)
        ix.reverse()
        iy.reverse()
        toks = [self.fold.name, self.fmt.name, "seq", str(nx), str(ny)]
        for j in range(self.kx):
            toks.extend(self.tx[d][j] for d in ix)
        for j in range(self.ky):
            toks.extend(self.ty[d][j] for d in iy)
        toks.append("#exhaustive:%d" % i if self.index_tags else "#exhaustive")
        return " ".join(toks)

    lines = ExhaustiveMapGen.lines


def random_gen(obj, fmt, seed, strata, orders, max_length, index_tags=True):
    k = kind_of(obj)
    cls = {"map": RandomMapGen, "conv": RandomConvGen, "max": RandomMaxGen}[k]
    return cls(obj, fmt, seed, strata, orders, max_length, index_tags)


def exhaustive_gen(obj, fmt, max_length, index_tags=True):
    if kind_of(obj) == "conv":
        return ExhaustiveConvGen(obj, fmt, max_length, index_tags)
    return ExhaustiveMapGen(obj, fmt, max_length, index_tags)
