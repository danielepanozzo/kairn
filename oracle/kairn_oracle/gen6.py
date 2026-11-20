"""Random operands and enumerations for the interval kernels (architecture.md, "Claims of the
interval kernels" and "... two limbs and the enclosure interface"; milestone2.md, "Interval kernels"
and "One enclosure interface").

Each kernel gets a family from its claims, chosen before the families of the earlier waves:

    ivop       an encloses_interval entry (interval_neg_k, interval_add_k, interval_sub_k,
               interval_mul_k): operands are canonical intervals
    ivset      an interval_set entry (interval_hull_k, interval_intersection_k)
    ivmake     makes_interval, or makes_ball from the bounds of an interval (interval_make_k,
               ball_from_interval_2): the given bounds are any values
    ivmid      ball_of_interval or splits (interval_mid_rad_1, interval_to_ball_1,
               interval_split_1)
    ballbound  set_bound or interval_of_ball (ball_lower_as_k, ball_upper_as_k,
               ball_to_interval_1): a ball operand
    outward    outward, or encloses with no ball (add_ball_2_2, mul_ball_2_2, the bounds of two
               limbs add_down_2_2 ... mul_dir_2_2, and mul_ext_2_2 in the extended domain)
    dirmul     bound and rounded with zero_factor (mul_dir_1): the strata of gen4's dirprod for
               finite operands, and its own for infinite and zero ones (never a NaN: not_nan)

ball_narrow_2_1, an encloses of a ball of the extended domain, keeps the family of gen3.py.

Every family has the strata every family has (uniform, underflow, overflow, zero, pow2,
extreme), read for its operands, and strata of its own, which come round twice per cycle:

    ivop       special    each operand the empty set, the whole line, a half-line on either
                          side, [0, 0], a point, or bounded (at least one of them special)
               point      points and intervals whose bounds are one step apart
               threshold  bounded operands whose exact range reaches the limit of bounded_when
                          (Omega, or 2^(qmax+p+E)) just inside or just outside, on either side
               cancel     (sums) bounds that nearly cancel: the bound of the range tiny
               zerosum    (sums) a bound of the range exactly zero (exact_when true)
               zeroinf    (products) [0, 0] or a zero bound against an unbounded operand
               aroundp    (products) products of bounds around P = 2^(2p-1) eta (product_large
                          true and false)
    ivset      special, point (equal intervals and points), disjoint, touch (one common point),
               nested
    ivmake     nanbound (a NaN bound, the other any value), reversed (lo > hi), infinities
               (each bound infinite or finite: half-lines, the whole line, equal infinities),
               point; for a ball from an interval also oddeta (bounds odd multiples of eta below
               2N, where halving is not exact) and top (bounds at and near +-Omega)
    ivmid      special, point, step (bounds one step apart), oddeta, top ([-Omega, Omega],
               [Omega, Omega] and their neighbours)
    ballbound  ballstates (the whole line and the empty set), radii (radii of every size against
               the center), cross (a radius about the magnitude of the center: c - r or c + r
               small, zero or of the other sign), beyond (c - r below -Omega or c + r above
               Omega), exactend (c - r and c + r numbers of the format, or not, by one bit)
    outward    sums: cancel, zerosum (x + y = 0 exactly, x - y = 0), close, apart, tiny (values
               near the underflow range, where the absolute term is most of the bound);
               products: close, tiny, aroundp, exactprod; in the extended domain also nonfinite
               (an infinite operand), zeroinf (a zero against an infinite operand) and edge
               (products near the overflow threshold)
    dirmul     gen4's aroundp, tiny, exactprod, beyond, and nonfinite (an infinite operand, the
               other finite, zero or infinite), zeroinf (a zero against an infinity), zerofactor
               (a zero against any number)

Every case is checked against the requirements before it is written (valid6, written from the
definitions), and the selftest checks that no stratum produces an invalid case.  The enumeration
of a kernel of the extended domain (IvExhaustiveGen) takes an interval as one operand, as gen3
takes a ball: every canonical interval of its bounds (the empty set, the bounded intervals, the
half-lines and the whole line), restrictions on its lower and upper input applying to the finite
lower and upper bounds.
"""

from . import fmt as F
from . import gen as G
from . import gen2 as G2
from . import gen3 as G3
from . import gen4 as G4

INF, NINF, NAN = F.POS_INF, F.NEG_INF, F.NAN
COMMON = G2.COMMON

STRATA_OWN = {
    ("ivop", "+"): ("special", "point", "threshold", "cancel", "zerosum"),
    ("ivop", "-"): ("special", "point", "threshold", "cancel", "zerosum"),
    ("ivop", "*"): ("special", "point", "threshold", "zeroinf", "aroundp"),
    ("ivop", "neg"): ("special", "point"),
    ("ivset", None): ("special", "point", "disjoint", "touch", "nested"),
    ("ivmake", "interval"): ("nanbound", "reversed", "infinities", "point"),
    ("ivmake", "ball"): ("nanbound", "reversed", "infinities", "point", "oddeta", "top"),
    ("ivmid", None): ("special", "point", "step", "oddeta", "top"),
    ("ballbound", None): ("ballstates", "radii", "cross", "beyond", "exactend"),
    ("outward", "+"): ("cancel", "zerosum", "close", "apart", "tiny"),
    ("outward", "-"): ("cancel", "zerosum", "close", "apart", "tiny"),
    ("outward", "*"): ("close", "tiny", "aroundp", "exactprod"),
    ("dirmul", None): ("aroundp", "tiny", "exactprod", "beyond", "nonfinite", "zeroinf",
                       "zerofactor"),
}
# The strata of the extended domain added to the outward family's for mul_ext_2_2.
OUTWARD_EXTENDED = ("nonfinite", "zeroinf", "edge")
FAMILIES = ("ivop", "ivset", "ivmake", "ivmid", "ballbound", "outward", "dirmul")


def family_of(kernel):
    """The family of an interval kernel, or None."""
    kinds = {e.kind for e in kernel.ensures}
    if "encloses_interval" in kinds:
        return "ivop"
    if "interval_set" in kinds:
        return "ivset"
    if "makes_interval" in kinds or any(e.kind == "makes_ball" and getattr(e, "iv", False)
                                        for e in kernel.ensures):
        return "ivmake"
    if kinds & {"ball_of_interval", "splits"}:
        return "ivmid"
    if kinds & {"set_bound", "interval_of_ball"}:
        return "ballbound"
    if "outward" in kinds or any(e.kind == "encloses" and not e.balls for e in kernel.ensures):
        return "outward"
    if any(getattr(e, "zero_factor", False) and e.kind in ("bound", "rounded")
           for e in kernel.ensures):
        return "dirmul"
    return None


def strata_of(family, op, extended):
    """(strata, schedule) of a family: the common strata, then those of its own twice."""
    own = STRATA_OWN[(family, op)]
    if family == "outward" and extended:
        own = own + OUTWARD_EXTENDED
    strata = COMMON + own
    schedule = ("uniform",) + tuple(s for s in own for _ in range(2)) + COMMON[1:]
    return strata, schedule


class Shape6:
    def __init__(self, kernel):
        self.kernel = kernel
        self.family = family_of(kernel)
        if self.family is None:
            raise G.GenError("%s: not an interval kernel" % kernel.name)
        self.names = [n for n, _ in kernel.inputs]
        self.limbs = dict(kernel.inputs)
        self.extended = kernel.extended
        self.not_nan = {r[1] for r in kernel.requires if r[0] == "not_nan"}
        self.intervals = list(kernel.interval_requires)
        self.balls = list(kernel.ball_requires)
        op = None
        fam = self.family
        if fam == "ivop":
            e = next(e for e in kernel.ensures if e.kind == "encloses_interval")
            self.ivnames = list(e.intervals)
            self.pairs = [e.intervals[n] for n in self.ivnames]
            t = e.set_tree
            op = "neg" if t[0] == "neg" else t[0]
            if t[0] in ("+", "-", "*"):
                # The interval names in the order of the set (x then y).
                order = [t[1][1], t[2][1]] if t[1][0] == "name" and t[2][0] == "name" else None
                if order:
                    self.pairs = [e.intervals[n] for n in order]
            self.bw = list(e.bounded_when)
            self.k = self.limbs[self.pairs[0][0]]
        elif fam == "ivset":
            e = next(e for e in kernel.ensures if e.kind == "interval_set")
            self.pairs = list(e.intervals.values())
            self.k = self.limbs[self.pairs[0][0]]
        elif fam == "ivmake":
            e = next(e for e in kernel.ensures if e.kind in ("makes_interval", "makes_ball"))
            self.given = (e.from_lower, e.from_upper)
            self.k = self.limbs[e.from_lower]
            op = "ball" if e.kind == "makes_ball" else "interval"
        elif fam == "ivmid":
            e = next(e for e in kernel.ensures if e.kind in ("ball_of_interval", "splits"))
            self.pairs = [e.from_pair]
            self.k = self.limbs[e.from_pair[0]]
        elif fam == "ballbound":
            (self.center, self.radius), = self.balls
            self.k = self.limbs[self.center]
        elif fam == "outward":
            t = kernel.value_tree
            op = t[0]
            self.pair = (t[1][1], t[2][1])
            self.k = self.limbs[self.pair[0]]
        else:
            t = kernel.value_tree
            self.pair = (t[1][1], t[2][1])
            self.k = 1
            # A finite view for gen4's dirprod strata (finite operands, no requirement).
            view = _FiniteView(kernel)
            self.dirprod = G2.Shape2(view)
        self.op = op
        self.strata, self.schedule = strata_of(fam, op, self.extended)


class _FiniteView:
    """The kernel as gen2 and gen4 see its finite operands: no interval() or not_nan()."""

    def __init__(self, k):
        self.name = k.name
        self.inputs = k.inputs
        self.outputs = k.outputs
        self.masks = k.masks
        self.input_names = k.input_names
        self.value = k.value
        self.value_tree = k.value_tree
        self.requires = [r for r in k.requires if r[0] not in ("interval", "not_nan")]
        self.ensures = k.ensures


# ---------------------------------------------------------------------------
# Numbers and bounds

def _inf(k, sign):
    return [INF if sign > 0 else NINF] + [0] * (k - 1)


def _nan(k):
    return [NAN] * k


def _number(fmt, rng, k, stratum):
    """A finite number of k limbs for a common stratum (or uniform)."""
    s = stratum if stratum in COMMON else "uniform"
    if k == 1:
        return [G2.limb(fmt, rng, s)]
    return G2.expansion(fmt, rng, s)


def _value(v):
    """The value of a bound in the extended reals (fixed, or an infinity)."""
    if all(type(t) is int for t in v):
        return sum(v)
    return v[0]


def _key(v):
    x = _value(v)
    return (-1, 0) if x == NINF else (1, 0) if x == INF else (0, x)


def _sorted2(a, b):
    return (a, b) if _key(a) <= _key(b) else (b, a)


def _from_value(fmt, k, v):
    """The k-limb number nearest a fixed value v (for two limbs, its normalized pair when v is
    the sum of two numbers of the format), or None."""
    if k == 1:
        r = F.rn_fixed(fmt, v)
        return [r] if type(r) is int else None
    h = F.rn_fixed(fmt, v)
    if type(h) is not int:
        return None
    t = v - h
    if not F.is_member(fmt, t):
        t = F.rn_fixed(fmt, t)
        if type(t) is not int:
            return None
    pair = [h, t]
    return pair if F.normalized_limbs(fmt, pair) else [h, 0]


def _step(fmt, k, v, up):
    """A bound one step above (up) or below v: the next number for one limb; for two, the second
    limb moved by its unit (eta at least), renormalized."""
    if k == 1:
        n = F.succ(fmt, v[0]) if up else F.pred(fmt, v[0])
        return [n] if type(n) is int else None
    u = max(F.ulp(fmt, v[1]) if v[1] else 1, 1)
    cand = _from_value(fmt, 2, sum(v) + (u if up else -u))
    return cand


def _interval(fmt, rng, k, stratum):
    """A bounded interval of two numbers of a common stratum, sorted."""
    a = _number(fmt, rng, k, stratum)
    b = _number(fmt, rng, k, stratum) if not (stratum == "zero" and rng.bits(1)) else [0] * k
    return _sorted2(a, b)


SPECIALS = ("empty", "whole", "below", "above", "zero", "point", "bounded")


def _special(fmt, rng, k, kind=None):
    kind = kind or SPECIALS[rng.below(len(SPECIALS))]
    if kind == "empty":
        return _inf(k, 1), _inf(k, -1)
    if kind == "whole":
        return _inf(k, -1), _inf(k, 1)
    if kind == "below":
        return _inf(k, -1), _number(fmt, rng, k, ("uniform", "zero", "extreme")[rng.below(3)])
    if kind == "above":
        return _number(fmt, rng, k, ("uniform", "zero", "extreme")[rng.below(3)]), _inf(k, 1)
    if kind == "zero":
        return [0] * k, [0] * k
    if kind == "point":
        a = _number(fmt, rng, k, "uniform")
        return a, list(a)
    return _interval(fmt, rng, k, "uniform")


def _point(fmt, rng, k):
    """A point, an interval whose bounds are one step apart, or [0, 0], or [-eta, eta]-like."""
    j = rng.below(4)
    a = _number(fmt, rng, k, ("uniform", "underflow", "extreme", "pow2")[rng.below(4)])
    if j == 0:
        return a, list(a)
    if j == 1:
        b = _step(fmt, k, a, True)
        return (a, b) if b else (a, list(a))
    if j == 2:
        return [0] * k, [0] * k
    one = [1] + [0] * (k - 1)
    return [-1] + [0] * (k - 1), one


def _near(fmt, rng, v):
    """v (fixed, positive) or a neighbour, one to three steps away."""
    for _ in range(rng.below(4)):
        n = F.succ(fmt, v) if rng.bits(1) else F.pred(fmt, v)
        if type(n) is int and n > 0:
            v = n
    return v


# ---------------------------------------------------------------------------
# ivop

def _limit_fixed(fmt, kind, e):
    """The limit of a bounded_when condition as a fixed value (it may exceed Omega)."""
    if kind == "omega":
        return fmt.omega
    t = fmt.qmax + fmt.p + e - fmt.qmin
    return 1 << t if t >= 0 else 1


def _threshold_pair(fmt, rng, sh):
    """Bounded operands of x op y whose range reaches the limit of bounded_when just inside or
    just outside, on the side of the upper bound or of the lower bound."""
    k = sh.k
    kind, e = sh.bw[rng.below(len(sh.bw))] if sh.bw else ("omega", None)
    T = _limit_fixed(fmt, kind, e)
    inside = rng.bits(1)
    # The target magnitude: the limit, or one unit of the format beyond it either way.
    t = T if rng.bits(1) else (T - F.ulp(fmt, min(T, fmt.omega)) if inside else
                               T + F.ulp(fmt, min(T, fmt.omega)))
    neg = rng.bits(1)
    op = sh.op
    xs, ys = [], []
    def inner(v, toward):
        # The other bound of an interval whose outer bound is v: on the side `toward` of it (a
        # number of the other sign, zero, or v itself).
        j = rng.below(3)
        if j == 0:
            return list(v)
        if j == 1:
            return [0] * k
        w = _number(fmt, rng, k, "uniform")
        return w if toward * w[0] >= 0 else [-t for t in w]

    if op in ("+", "-"):
        a = rng.between(t // 4 + 1, max(t // 4 + 1, min(fmt.omega, t - 1)))
        av = _from_value(fmt, k, min(a, fmt.omega))
        if av is None:
            return None
        bv = _from_value(fmt, k, max(min(t - sum(av), fmt.omega), 0))
        if bv is None:
            return None
        # The outer bounds: x + y, the upper bounds (or minus the lower bounds) summing to about
        # t; x - y, x's upper bound minus y's lower bound (or x's lower minus y's upper).
        s = -1 if neg else 1
        hx = [s * v for v in av]
        hy = [s * v for v in bv] if op == "+" else [-s * v for v in bv]
        x = (hx, inner(hx, -s))
        y = (hy, inner(hy, -s if op == "+" else s))
        x, y = _sorted2(*x), _sorted2(*y)
        return x, y
    # x * y: the product of two bounds about t.
    ea = rng.between(max(fmt.qmin, fmt.binade(min(t, fmt.omega)) - fmt.emax),
                     min(fmt.emax, fmt.binade(min(t, fmt.omega)) - fmt.qmin))
    a = G.in_binade(fmt, rng, ea)
    # b about t / a, at the scale of fixed values: t eta / (a eta) -> (t / a) units of eta^0...
    num = t << (-fmt.qmin) if fmt.qmin < 0 else t >> fmt.qmin
    b = F.rdir(fmt, max(num // a, 1), fmt.qmin, False) if num // a else 1
    b = min(max(_near(fmt, rng, b), 1), fmt.omega)
    av, bv = _from_value(fmt, k, a), _from_value(fmt, k, b)
    if av is None or bv is None:
        return None
    if neg:
        bv = [-v for v in bv]
    x = _sorted2(av, _number(fmt, rng, k, "underflow") if rng.bits(1) else [0] * k)
    y = _sorted2(bv, _number(fmt, rng, k, "underflow") if rng.bits(1) else [0] * k)
    return x, y


def _ivop(fmt, sh, rng, stratum):
    k = sh.k
    n = len(sh.pairs)
    if stratum in COMMON:
        ivs = [_interval(fmt, rng, k, stratum) for _ in range(n)]
        if stratum == "overflow" and n == 2 and sh.op in ("+", "-", "*") and rng.bits(1):
            # Bounds of one sign in the top binades: the range beyond Omega.
            s = rng.sign()
            for j in range(2):
                a = [s * abs(G2._top(fmt, rng))] + [0] * (k - 1)
                b = _number(fmt, rng, k, "overflow")
                ivs[j] = _sorted2(a, b)
        return ivs
    if stratum == "special":
        ivs = [_special(fmt, rng, k) if rng.bits(1) else _interval(fmt, rng, k, "uniform")
               for _ in range(n)]
        j = rng.below(n)
        ivs[j] = _special(fmt, rng, k, SPECIALS[rng.below(len(SPECIALS) - 1)])
        return ivs
    if stratum == "point":
        return [_point(fmt, rng, k) if rng.chance(3, 4) else _interval(fmt, rng, k, "uniform")
                for _ in range(n)]
    if stratum == "threshold":
        r = _threshold_pair(fmt, rng, sh) if n == 2 else None
        return list(r) if r else [_interval(fmt, rng, k, "overflow") for _ in range(n)]
    if stratum in ("cancel", "zerosum"):
        x = _interval(fmt, rng, k, "uniform" if rng.bits(1) else "extreme")
        y = list(_interval(fmt, rng, k, "uniform"))
        s = -1 if sh.op == "+" else 1
        # x + y: yl about -xl and yu about -xu; x - y: yu about xl, yl about xu.
        sides = [(0, 0), (1, 1)] if sh.op == "+" else [(1, 0), (0, 1)]
        for jy, jx in sides:
            if not rng.chance(3, 4):
                continue
            v = [s * t for t in x[jx]]
            if stratum == "cancel":
                st = _step(fmt, k, v, rng.bits(1))
                v = st or v
                if k == 2 and rng.bits(1):
                    # The leading limbs cancel, the tails do not.
                    v = [v[0], G.tail_for(fmt, rng, v[0], "near")]
                    if not F.normalized_limbs(fmt, v):
                        v = [v[0], 0]
            y[jy] = v
        lo, hi = y
        if _key(lo) > _key(hi):
            lo, hi = hi, lo
        return [x, (lo, hi)]
    if stratum == "zeroinf":
        z = [0] * k
        zero = rng.below(3)
        if zero == 0:
            a = (list(z), list(z))
        elif zero == 1:
            a = (list(z), _number(fmt, rng, k, "uniform"))
            a = _sorted2(*a)
        else:
            a = _sorted2(list(z), [-abs(_number(fmt, rng, k, "uniform")[0])] + [0] * (k - 1))
        b = _special(fmt, rng, k, ("whole", "below", "above")[rng.below(3)])
        return [a, b] if rng.bits(1) else [b, a]
    if stratum == "aroundp":
        A, B = G4._prod_operands(fmt, rng, "aroundp")
        av, bv = [A] + [0] * (k - 1), [B] + [0] * (k - 1)
        x = _sorted2(av, _number(fmt, rng, k, "underflow") if rng.bits(1) else list(av))
        y = _sorted2(bv, _number(fmt, rng, k, "underflow") if rng.bits(1) else list(bv))
        return [x, y]
    raise G.GenError("unknown stratum %r" % stratum)


# ---------------------------------------------------------------------------
# ivset

def _ivset(fmt, sh, rng, stratum):
    k = sh.k
    if stratum in COMMON:
        return [_interval(fmt, rng, k, stratum) for _ in range(2)]
    if stratum == "special":
        if rng.chance(1, 8):
            # Both empty: the union of two empty sets.
            return [_special(fmt, rng, k, "empty"), _special(fmt, rng, k, "empty")]
        return [_special(fmt, rng, k) for _ in range(2)]
    if stratum == "point":
        x = _point(fmt, rng, k) if rng.bits(1) else _interval(fmt, rng, k, "uniform")
        return [x, (list(x[0]), list(x[1]))] if rng.bits(1) else [x, _point(fmt, rng, k)]
    a, b, c, d = sorted((_number(fmt, rng, k, "uniform") for _ in range(4)), key=_key)
    if stratum == "disjoint":
        ivs = [(a, b), (c, d)] if _key(b) < _key(c) else [(a, a), (d, d)]
    elif stratum == "touch":
        ivs = [(a, b), (list(b), d)]
    else:
        ivs = [(a, d), (b, c)]
    if rng.bits(1):
        ivs.reverse()
    return ivs


# ---------------------------------------------------------------------------
# ivmake

def _any_bound(fmt, rng, k, finite_stratum="uniform"):
    j = rng.below(6)
    if j == 0:
        return _nan(k)
    if j == 1:
        return _inf(k, 1)
    if j == 2:
        return _inf(k, -1)
    return _number(fmt, rng, k, finite_stratum)


def _odd_low(fmt, rng, k):
    """A number that is an odd multiple of eta below 2N (its half is not a number), or one that
    is not."""
    v = 2 * rng.below(fmt.lam) + 1
    v = rng.sign() * min(v, 2 * fmt.lam - 1)
    return [v] + [0] * (k - 1)


def _ivmake(fmt, sh, rng, stratum):
    k = sh.k
    if stratum in COMMON:
        a, b = _number(fmt, rng, k, stratum), _number(fmt, rng, k, stratum)
        return [a, b]
    if stratum == "nanbound":
        a = _nan(k)
        b = _any_bound(fmt, rng, k)
        return [a, b] if rng.bits(1) else [b, a]
    if stratum == "reversed":
        j = rng.below(3)
        if j == 0:
            a, b = _sorted2(_number(fmt, rng, k, "uniform"), _number(fmt, rng, k, "uniform"))
            if a == b:
                b = _step(fmt, k, a, True) or b
            return [b, a]
        if j == 1:
            return [_inf(k, 1), _number(fmt, rng, k, "uniform")]
        return [_number(fmt, rng, k, "uniform"), _inf(k, -1)]
    if stratum == "infinities":
        a = _inf(k, rng.sign()) if rng.chance(2, 3) else _number(fmt, rng, k, "uniform")
        b = _inf(k, rng.sign()) if rng.chance(2, 3) else _number(fmt, rng, k, "uniform")
        return [a, b]
    if stratum == "point":
        a = _number(fmt, rng, k, ("uniform", "zero", "extreme", "underflow")[rng.below(4)])
        return [a, list(a)]
    if stratum == "oddeta":
        a = _odd_low(fmt, rng, k) if rng.chance(3, 4) else _number(fmt, rng, k, "underflow")
        b = _odd_low(fmt, rng, k) if rng.chance(3, 4) else _number(fmt, rng, k, "uniform")
        return list(_sorted2(a, b)) if rng.chance(7, 8) else [b, a]
    if stratum == "top":
        om = fmt.omega
        cands = [om, F.pred(fmt, om), -om, -F.pred(fmt, om), abs(G2._top(fmt, rng))]
        a = [cands[rng.below(len(cands))]] + [0] * (k - 1)
        b = [cands[rng.below(len(cands))]] + [0] * (k - 1)
        return list(_sorted2(a, b)) if rng.chance(7, 8) else [b, a]
    raise G.GenError("unknown stratum %r" % stratum)


# ---------------------------------------------------------------------------
# ivmid

def _ivmid(fmt, sh, rng, stratum):
    k = sh.k
    if stratum in COMMON:
        return [_interval(fmt, rng, k, stratum)]
    if stratum == "special":
        return [_special(fmt, rng, k)]
    if stratum == "point":
        return [_point(fmt, rng, k)]
    if stratum == "step":
        a = _number(fmt, rng, k, ("uniform", "underflow", "pow2", "extreme")[rng.below(4)])
        b = _step(fmt, k, a, True)
        if b and rng.bits(1):
            b2 = _step(fmt, k, b, True)
            b = b2 or b
        return [(a, b) if b else (a, list(a))]
    if stratum == "oddeta":
        a = _odd_low(fmt, rng, k) if rng.chance(3, 4) else _number(fmt, rng, k, "underflow")
        b = _odd_low(fmt, rng, k) if rng.chance(3, 4) else _number(fmt, rng, k, "uniform")
        return [_sorted2(a, b)]
    if stratum == "top":
        om = fmt.omega
        pom = F.pred(fmt, om)
        c = [(-om, om), (om, om), (-om, -om), (pom, om), (-om, pom), (-om, -pom),
             (abs(G2._top(fmt, rng)), om), (-om, G2.limb(fmt, rng, "uniform"))]
        lo, hi = c[rng.below(len(c))]
        return [_sorted2([lo] + [0] * (k - 1), [hi] + [0] * (k - 1))]
    raise G.GenError("unknown stratum %r" % stratum)


# ---------------------------------------------------------------------------
# ballbound

def _ball_center(fmt, rng, k, stratum):
    return _number(fmt, rng, k, stratum)


def _ballbound(fmt, sh, rng, stratum):
    k = sh.k
    cn, rn = sh.center, sh.radius
    if stratum in COMMON:
        c = _ball_center(fmt, rng, k, stratum)
        mode = {"underflow": ("zero", "eta", "subnormal", "tiny", "ulp"),
                "overflow": ("huge", "comparable", "wide", "zero"),
                "zero": ("zero", "eta", "uniform")}.get(stratum, G2.RADIUS_MODES)
        r = G2.radius(fmt, rng, c[0], mode[rng.below(len(mode))])
        return {cn: c, rn: [r]}
    if stratum == "ballstates":
        if rng.bits(1):
            return {cn: [0] * k, rn: [INF]}
        return {cn: _nan(k), rn: [NAN]}
    if stratum == "radii":
        c = _ball_center(fmt, rng, k, "uniform" if rng.bits(1) else "extreme")
        r = G2.radius(fmt, rng, c[0], G2.RADIUS_MODES[rng.below(len(G2.RADIUS_MODES))])
        return {cn: c, rn: [r]}
    if stratum in ("cross", "exactend"):
        c = _ball_center(fmt, rng, k, "uniform")
        a = abs(c[0]) or 1
        if stratum == "cross":
            # r about |c|: c - r (or c + r) small, zero or of the other sign.
            r = _near(fmt, rng, a)
        else:
            # A radius with few bits at the exponent of c, so that c +- r is exact, or one with a
            # bit below the last place of c.
            e = fmt.binade(a) - rng.between(0, fmt.p)
            r = G.in_binade(fmt, rng, max(fmt.qmin, e), "short" if rng.bits(1) else "uniform")
        return {cn: c, rn: [min(r, fmt.omega)]}
    if stratum == "beyond":
        s = rng.sign()
        c0 = s * abs(G2._top(fmt, rng)) if rng.chance(3, 4) else G2.limb(fmt, rng, "uniform")
        c = [c0] if k == 1 else G2._x2_even(fmt, rng, c0, ("near", "zero", "max")[rng.below(3)])
        r = abs(G2._top(fmt, rng)) >> rng.below(2)
        return {cn: c, rn: [r]}
    raise G.GenError("unknown stratum %r" % stratum)


# ---------------------------------------------------------------------------
# outward

def _outward(fmt, sh, rng, stratum):
    k = sh.k
    a, b = sh.pair
    op = sh.op
    if stratum in COMMON:
        x, y = G2.expansion(fmt, rng, stratum), G2.expansion(fmt, rng, stratum)
        if stratum == "overflow" and op == "*" and rng.bits(1):
            e = fmt.emax - fmt.binade(x[0] or 1) + rng.between(-1, 0)
            y0 = rng.sign() * G.in_binade(fmt, rng, max(fmt.qmin, min(fmt.emax, e)), "high")
            y = G2._x2(fmt, rng, y0, "near")
        return {a: x, b: y}
    if stratum in ("cancel", "zerosum"):
        x = G2.expansion(fmt, rng, "uniform" if rng.bits(1) else "extreme")
        s = -1 if op == "+" else 1
        y = [s * t for t in x]
        if stratum == "cancel":
            j = rng.below(3)
            if j == 0:
                y = [y[0], G.tail_for(fmt, rng, y[0], "near")]
            elif j == 1:
                st = _step(fmt, 2, y, rng.bits(1))
                y = st or y
            else:
                n = F.succ(fmt, y[0]) if rng.bits(1) else F.pred(fmt, y[0])
                y = [n, G.tail_for(fmt, rng, n, "near")] if type(n) is int else y
            if not F.normalized_limbs(fmt, y):
                y = [y[0], 0]
        return {a: x, b: y}
    if stratum in ("close", "apart"):
        lo, hi = G._mid(fmt, 2 * fmt.p + 2, 2)
        e = rng.between(lo, hi)
        d = rng.between(0, fmt.p + 2) if stratum == "close" else rng.between(fmt.p + 1, 3 * fmt.p)
        e2 = max(fmt.qmin, min(fmt.emax, e - d if rng.bits(1) else e + d))
        if op == "*":
            e2 = max(fmt.qmin, min(fmt.emax, rng.between(-fmt.p, fmt.p)))
        x = G2._x2(fmt, rng, G2._limb(fmt, rng, e), "near")
        y = G2._x2(fmt, rng, G2._limb(fmt, rng, e2), "near")
        return {a: x, b: y}
    if stratum == "tiny":
        # Values near and below the smallest normal number, where the absolute term is most of
        # the bound.
        if op == "*":
            A, B = G4._prod_operands(fmt, rng, "underflow")
            x = G2._x2(fmt, rng, A, "near") if A else [0, 0]
            y = G2._x2(fmt, rng, B, "near") if B else [0, 0]
        else:
            x = G2.expansion(fmt, rng, "underflow")
            y = G2.expansion(fmt, rng, "underflow")
        return {a: x, b: y}
    if stratum in ("aroundp", "exactprod"):
        A, B = G4._prod_operands(fmt, rng, stratum)
        x = G2._x2(fmt, rng, A, ("near", "zero", "tiny")[rng.below(3)]) if A else [0, 0]
        y = G2._x2(fmt, rng, B, ("near", "zero", "tiny")[rng.below(3)]) if B else [0, 0]
        return {a: x, b: y}
    if stratum == "nonfinite":
        x = G2.expansion(fmt, rng, "uniform")
        y = _inf(k, rng.sign())
        if rng.chance(1, 3):
            x = _inf(k, rng.sign())
        return {a: x, b: y} if rng.bits(1) else {a: y, b: x}
    if stratum == "zeroinf":
        return {a: [0] * k, b: _inf(k, rng.sign())} if rng.bits(1) else \
            {a: _inf(k, rng.sign()), b: [0] * k}
    if stratum == "edge":
        A, B = G4._prod_operands(fmt, rng, "beyond" if rng.bits(1) else "overflow")
        return {a: G2._x2(fmt, rng, A, "near") if A else [0, 0],
                b: G2._x2(fmt, rng, B, "near") if B else [0, 0]}
    raise G.GenError("unknown stratum %r" % stratum)


# ---------------------------------------------------------------------------
# dirmul

def _dirmul(fmt, sh, rng, stratum):
    a, b = sh.pair
    if stratum in sh.dirprod.strata:
        vals, _ = G2.make_case(fmt, sh.dirprod, rng, stratum)
        return {a: vals[a], b: vals[b]}
    if stratum == "nonfinite":
        x = [INF if rng.bits(1) else NINF]
        j = rng.below(3)
        y = [G2.limb(fmt, rng, "uniform")] if j == 0 else [0] if j == 1 else \
            [INF if rng.bits(1) else NINF]
        return {a: x, b: y} if rng.bits(1) else {a: y, b: x}
    if stratum == "zeroinf":
        x = [INF if rng.bits(1) else NINF]
        return {a: x, b: [0]} if rng.bits(1) else {a: [0], b: x}
    if stratum == "zerofactor":
        y = [G2.limb(fmt, rng, ("uniform", "overflow", "underflow", "extreme")[rng.below(4)])]
        return {a: [0], b: y} if rng.bits(1) else {a: y, b: [0]}
    raise G.GenError("unknown stratum %r" % stratum)


# ---------------------------------------------------------------------------

def make_case(fmt, sh, rng, stratum):
    """Operand limbs {name: [fixed or non-finite, ...]} and the set of (name, limb) that are -0."""
    fam = sh.family
    vals = {}
    if fam in ("ivop", "ivset", "ivmid"):
        maker = {"ivop": _ivop, "ivset": _ivset, "ivmid": _ivmid}[fam]
        ivs = maker(fmt, sh, rng, stratum)
        for (lo, hi), (L, U) in zip(sh.pairs, ivs):
            vals[lo], vals[hi] = list(L), list(U)
    elif fam == "ivmake":
        L, U = _ivmake(fmt, sh, rng, stratum)
        vals[sh.given[0]], vals[sh.given[1]] = list(L), list(U)
    elif fam == "ballbound":
        vals = _ballbound(fmt, sh, rng, stratum)
    elif fam == "outward":
        vals = _outward(fmt, sh, rng, stratum)
    else:
        vals = _dirmul(fmt, sh, rng, stratum)
    for n in sh.names:
        if n not in vals:
            vals[n] = [rng.bits(1)] if n in sh.kernel.masks else [0] * sh.limbs[n]
    negz = set()
    for n, limbs in vals.items():
        if n in sh.kernel.masks:
            continue
        for i, v in enumerate(limbs):
            if v == 0 and rng.bits(1):
                negz.add((n, i))
    return vals, negz


# ---------------------------------------------------------------------------
# Validity, written from the definitions (the checker has its own)

def _bound(fmt, v):
    """The value of a bound: fixed, an infinity, NAN, or None when not canonical."""
    if len(v) == 1:
        return v[0]
    if all(type(t) is int for t in v):
        return sum(v) if F.normalized_limbs(fmt, v) else None
    if v[0] == NAN:
        return NAN if all(t == NAN for t in v) else None
    return v[0] if v[0] in (INF, NINF) and all(t == 0 for t in v[1:]) else None


def _canonical_interval(fmt, lo, hi):
    L, U = _bound(fmt, lo), _bound(fmt, hi)
    if L is None or U is None or NAN in (L, U):
        return False
    if L == INF and U == NINF:
        return True
    if L == INF or U == NINF:
        return False
    if L == NINF or U == INF:
        return True
    return L <= U


def valid6(fmt, kernel, vals):
    for name, limbs in vals.items():
        if name in kernel.masks:
            if limbs not in ([0], [1]):
                return False
            continue
        if len(limbs) != dict(kernel.inputs)[name]:
            return False
        for v in limbs:
            if type(v) is int:
                if not F.is_member(fmt, v):
                    return False
            elif not kernel.extended or v not in (INF, NINF, NAN):
                return False
    for r in kernel.requires:
        if r[0] == "interval":
            if not _canonical_interval(fmt, vals[r[1]], vals[r[2]]):
                return False
        elif r[0] == "not_nan":
            if vals[r[1]][0] == NAN:
                return False
        elif r[0] == "normalized":
            if not F.normalized_limbs(fmt, vals[r[1]]):
                return False
        elif r[0] in ("canonical", "ball", "nonneg", "power_of_two"):
            if not G3.valid_ext(fmt, _Only(kernel, r), vals):
                return False
        else:
            return False
    return True


class _Only:
    """A kernel with one requirement, for gen3.valid_ext."""

    def __init__(self, k, r):
        self.masks = k.masks
        self.inputs = k.inputs
        self.requires = [r]


# ---------------------------------------------------------------------------
# Exhaustive enumeration of the kernels of the extended domain

def enumerates(kernel):
    """The kernels of the extended domain whose enumeration is IvExhaustiveGen's: an interval()
    or not_nan() requirement."""
    return kernel.extended and any(r[0] in ("interval", "not_nan") for r in kernel.requires)


class IvExhaustiveGen(G.ExhaustiveGen):
    """Every operand combination of an interval kernel of the extended domain.  An interval (its
    two bounds) is one operand, as a ball is (its center and radius); a restriction on its lower
    (upper) input keeps the finite lower (upper) bounds whose leading limb it keeps, and the
    infinite bounds and the empty set are always enumerated."""

    def __init__(self, kernel, fmt, restrictions=(), index_tags=True):
        self.kernel = kernel
        self.fmt = fmt
        self.restrictions = [G.Restriction(r) if isinstance(r, str) else r for r in restrictions]
        names = [n for n, _ in kernel.inputs]
        for r in self.restrictions:
            if r.name not in names:
                raise G.GenError("restriction on %r, which is not an input of %s"
                                 % (r.name, kernel.name))
        limbs = dict(kernel.inputs)
        for n, l in kernel.inputs:
            if l > 2:
                raise G.GenError("%s: exhaustive mode supports operands of at most two limbs"
                                 % kernel.name)
        req = kernel.requires
        not_nan = {r[1] for r in req if r[0] == "not_nan"}
        balls = {c: r for c, r in kernel.ball_requires}
        radii = set(balls.values())
        ivs = {lo: hi for lo, hi in kernel.interval_requires}
        uppers = set(ivs.values())

        def keep(nm):
            rs = [r for r in self.restrictions if r.name == nm]
            return lambda t: type(t[0]) is not int or all(r.keep(fmt, t[0]) for r in rs)

        self.slots = []
        for n, l in kernel.inputs:
            if n in radii or n in uppers:
                continue
            if n in kernel.masks:
                self.slots.append(((n,), [(0,), (1,)]))
                continue
            fin = G3._finite_domain(fmt, l)
            if n in ivs:
                hn = ivs[n]
                lows = [t for t in fin if keep(n)(t)]
                highs = [t for t in fin if keep(hn)(t)]
                ninf, pinf = (NINF,) + (0,) * (l - 1), (INF,) + (0,) * (l - 1)
                dom = [pinf + ninf]
                lows_v = [(t, sum(t)) for t in lows]
                highs_v = [(t, sum(t)) for t in highs]
                for lo_t, lo_v in [(ninf, None)] + lows_v:
                    for hi_t, hi_v in highs_v + [(pinf, None)]:
                        if lo_v is None or hi_v is None or lo_v <= hi_v:
                            dom.append(lo_t + hi_t)
                self.slots.append(((n, hn), dom))
                continue
            if n in balls:
                rn = balls[n]
                centers = [t for t in fin if keep(n)(t)]
                rads = [t for t in G3._finite_domain(fmt, 1) if t[0] >= 0 and keep(rn)(t)]
                dom = [c + r for c in centers for r in rads]
                dom.append((0,) * l + (INF,))
                dom.append((NAN,) * l + (NAN,))
                self.slots.append(((n, rn), dom))
                continue
            dom = [t for t in fin if keep(n)(t)]
            if l == 2:
                dom += [(INF, 0), (NINF, 0)] + ([] if n in not_nan else [(NAN, NAN)])
            else:
                dom += [(INF,), (NINF,)] + ([] if n in not_nan else [(NAN,)])
            self.slots.append(((n,), dom))
        self.doms = [d for _, d in self.slots]
        self.texts = []
        for nms, dom in self.slots:
            widths = [limbs[m] for m in nms]
            txt = []
            for t in dom:
                parts, i = [], 0
                for w in widths:
                    parts.append(t[i:i + w])
                    i += w
                txt.append([" ".join(G3._text(fmt, v) for v in p) for p in parts])
            self.texts.append(txt)
        self.total = 1
        for d in self.doms:
            self.total *= len(d)
        self.coupled = []
        self.index_tags = index_tags
        self.restrict_text = ",".join(r.spec for r in self.restrictions) or "none"

    case = G3.ExtExhaustiveGen.case
