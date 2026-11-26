"""Random operands and enumerations for the kernels of the round-up interval (upward.md, "Claims and
the oracle": the requirement upward(U, N) and its strata for the case generator; upward.py).

A kernel is of this family when upward.is_upward_kernel says so (rounding upward, an upward()
requirement, or a set named by its stored pair), and the family is chosen before every other.  Each
input of such a kernel is one of:

    a stored pair (U, N) of an upward() requirement: a canonical state, written as its two lanes as
        stored, the upper bound then the lower bound negated: (NaN, NaN) for the empty set
        (`nan nan`), (+inf, +inf) for the whole line;
    a default interval (L, U) of an interval() requirement (upward_from_interval_1): a canonical
        interval, (+inf, -inf) for the empty set;
    a number, a one-limb input with no requirement (the t of the operations with a number and of
        contains, the bounds given to upward_make_1): any value of the format, an infinity or a NaN.

Strata: the common ones (uniform, underflow, overflow, zero, pow2, extreme), read for the bounds of
an interval and for a number, and those the page asks for, each coming round twice per cycle:

    empty       an operand the empty set
    whole       an operand the whole line
    halfline    an operand a half-line, on either side
    point       an operand a point (u = -n), [0, 0] among them
    zerobound   a bound zero (its lane written +0 or -0 at random), [0, 0], [0, +inf], [-inf, 0]
    omega       bounds at and next to +-Omega, and half-lines from them
    subnormal   bounds that are subnormal numbers (at precision 1, where there is none, eta)
    crossnear   lanes whose sum crosses zero near zero: for a sum, a lane of x and the same lane of
                y about opposite (b + d or a + c an exact zero, or a few units off); for a
                difference the same of a lane and the other lane; for a product, tiny bounds of
                both signs (products below eta); for the hull, the intersection and the
                comparisons, intervals near zero that touch or cross by a step or two; for one
                operand, bounds of opposite signs within a few units of zero
    zeroinf     (products) [0, 0] or a zero bound against an unbounded operand; with a number,
                [0, 0] against t infinite or NaN and an unbounded x against t = 0
    aroundp     (products) products of bounds around P = 2^(2p-1) eta (gen4's), where the default
                product may be one number wider and this one may not
    numspecial  (a number) t = +inf, -inf, NaN or a zero, and for contains a bound of x or a
                number next to one

and for upward_make_1 the strata of the constructors (gen6.py: nanbound, reversed, infinities,
point) beside zerobound, omega and subnormal.

Every case is checked against the requirements before it is written (valid_up, written from the
page's definitions; the checker has its own), and the selftest checks that each stratum produces
what it is for (selftest_up.up_strata).  The enumeration (UpExhaustiveGen) takes a stored pair as
one operand: the empty set and every pair (u, n) of numbers of the format or +inf with -n <= u; a
default interval as gen6 does; a number over every value, the infinities and NaN.
"""

from . import fmt as F
from . import gen as G
from . import gen2 as G2
from . import gen3 as G3
from . import gen4 as G4
from . import gen6 as G6

INF, NINF, NAN = F.POS_INF, F.NEG_INF, F.NAN
COMMON = G2.COMMON
EMPTY = ("empty",)
STATE_STRATA = ("empty", "whole", "halfline", "point", "zerobound", "omega", "subnormal",
                "crossnear")
MAKE_STRATA = ("nanbound", "reversed", "infinities", "point", "zerobound", "omega", "subnormal")
FAMILY = "upward"


def family_of(kernel):
    """FAMILY for a kernel of the round-up interval, or None."""
    from . import upward as UP
    return FAMILY if UP.is_upward_kernel(kernel) else None


def enumerates(kernel):
    return family_of(kernel) is not None


class ShapeUp:
    """The roles of a kernel's inputs, its operation and its strata."""

    def __init__(self, kernel):
        self.kernel = kernel
        if family_of(kernel) is None:
            raise G.GenError("%s: not a kernel of the round-up interval" % kernel.name)
        self.names = [n for n, _ in kernel.inputs]
        self.limbs = dict(kernel.inputs)
        if kernel.ball_requires or kernel.masks & set(self.names):
            raise G.GenError("%s: a ball or a mask input is not generated for the round-up "
                             "interval" % kernel.name)
        for n, l in kernel.inputs:
            if l != 1:
                raise G.GenError("%s: the input %s has %d limbs; the round-up interval's have one"
                                 % (kernel.name, n, l))
        self.stored = list(kernel.upward_requires)
        self.default = list(kernel.interval_requires)
        inset = {n for p in self.stored + self.default for n in p}
        others = [r for r in kernel.requires if r[0] not in ("upward", "interval")]
        if others:
            raise G.GenError("%s: requirement %s is not generated for the round-up interval"
                             % (kernel.name, others[0][0]))
        self.numbers = [n for n in self.names if n not in inset]
        # The sets in the order of the entry's operation (x then y), stored or default.
        self.sets = [("up", p) for p in self.stored] + [("iv", p) for p in self.default]
        kinds = [e.kind for e in kernel.ensures]
        e = kernel.ensures[0] if kernel.ensures else None
        op = None
        if "makes_interval" in kinds:
            op = "make"
        elif "encloses_interval" in kinds:
            t = e.set_tree
            op = "neg" if t[0] == "neg" else t[0]
            if t[0] in ("+", "-", "*") and t[1][0] == "name" and t[2][0] == "name":
                order = [t[1][1], t[2][1]]
                pairs = [getattr(e, "intervals", {}).get(n) for n in order]
                self.sets = [("up" if isinstance(p, tuple) and p in self.stored else "iv",
                              tuple(p)) for p in pairs if p is not None] or self.sets
        elif "interval_set" in kinds:
            op = "set"
        elif "same_set" in kinds:
            op = "conv"
        else:
            op = "pred"
        self.op = op
        # contains: a number beside one set.
        self.contains = op == "pred" and bool(self.numbers)
        if op == "make":
            own = MAKE_STRATA
        else:
            own = STATE_STRATA
            if op == "*":
                own = own + ("zeroinf", "aroundp")
            if self.numbers:
                own = own + ("numspecial",)
        self.strata = COMMON + own
        self.schedule = ("uniform",) + tuple(s for s in own for _ in range(2)) + COMMON[1:]


# ---------------------------------------------------------------------------
# Numbers and intervals (an interval is EMPTY or (L, U): fixed values or the infinities)

def _number(fmt, rng, stratum):
    return G2.limb(fmt, rng, stratum if stratum in COMMON else "uniform")


def _subnormal(fmt, rng):
    """A positive subnormal number (eta at precision 1, which has none)."""
    if fmt.lam <= 1:
        return 1
    return rng.between(1, fmt.lam - 1)


def _near_omega(fmt, rng):
    om = fmt.omega
    c = [om, F.pred(fmt, om)]
    p2 = F.pred(fmt, c[1])
    if type(p2) is int and p2 > 0:
        c.append(p2)
    c.append(abs(G2._top(fmt, rng)))
    return c[rng.below(len(c))]


def _sorted(a, b):
    return (a, b) if _key(a) <= _key(b) else (b, a)


def _key(v):
    return (-1, 0) if v == NINF else (1, 0) if v == INF else (0, v)


def _bounded(fmt, rng, stratum="uniform"):
    a, b = _number(fmt, rng, stratum), _number(fmt, rng, stratum)
    if stratum == "zero" and rng.bits(1):
        b = 0
    return _sorted(a, b)


def _flavour(fmt, rng):
    """A finite number of a random kind: ordinary, zero, near a power of two, tiny, near Omega."""
    j = rng.below(6)
    if j == 0:
        return 0
    if j == 1:
        return rng.sign() * _subnormal(fmt, rng)
    if j == 2:
        return rng.sign() * _near_omega(fmt, rng)
    return _number(fmt, rng, ("uniform", "extreme", "pow2")[j - 3])


def _special(fmt, rng, kind):
    """An interval of one of the page's kinds."""
    if kind == "empty":
        return EMPTY
    if kind == "whole":
        return (NINF, INF)
    if kind == "halfline":
        v = _flavour(fmt, rng)
        return (NINF, v) if rng.bits(1) else (v, INF)
    if kind == "point":
        v = _flavour(fmt, rng) if rng.chance(3, 4) else 0
        return (v, v)
    if kind == "zerobound":
        j = rng.below(5)
        v = abs(_flavour(fmt, rng)) or 1
        return [(0, v), (-v, 0), (0, 0), (0, INF), (NINF, 0)][j]
    if kind == "omega":
        om = _near_omega(fmt, rng)
        j = rng.below(5)
        if j == 0:
            return (-om, _near_omega(fmt, rng))
        if j == 1:
            return _sorted(om, _flavour(fmt, rng))
        if j == 2:
            return _sorted(-om, _flavour(fmt, rng))
        if j == 3:
            return (om, INF) if rng.bits(1) else (NINF, -om)
        return (om, om) if rng.bits(1) else (-om, -om)
    if kind == "subnormal":
        a = rng.sign() * _subnormal(fmt, rng)
        b = rng.sign() * _subnormal(fmt, rng) if rng.chance(3, 4) else _flavour(fmt, rng)
        return _sorted(a, b)
    return _bounded(fmt, rng, "uniform")


def _any(fmt, rng):
    """An interval of any kind, bounded half of the time."""
    if rng.bits(1):
        return _bounded(fmt, rng, ("uniform", "extreme", "pow2", "underflow")[rng.below(4)])
    return _special(fmt, rng, STATE_STRATA[rng.below(len(STATE_STRATA) - 1)])


def _steps(fmt, v, k):
    """v (finite) moved k steps (up for k > 0), or None past the format."""
    for _ in range(abs(k)):
        v = F.succ(fmt, v) if k > 0 else F.pred(fmt, v)
        if type(v) is not int:
            return None
    return v


def _tiny(fmt, rng):
    """A number within a few units of zero: zero, +-eta, +-2 eta, or a subnormal."""
    j = rng.below(4)
    if j == 0:
        return 0
    if j == 3:
        return rng.sign() * _subnormal(fmt, rng)
    return rng.sign() * j


def _crossnear(fmt, sh, rng):
    """The operands of the stratum crossnear (see the module's docstring)."""
    n = len(sh.sets)
    op = sh.op
    if n == 1:
        a = -abs(_tiny(fmt, rng))
        b = abs(_tiny(fmt, rng))
        return [(a, b)]
    if op in ("+", "-"):
        x = _bounded(fmt, rng, ("uniform", "underflow", "extreme")[rng.below(3)])
        a, b = x
        k = rng.between(-2, 2)
        # x + y: zu = RU(b + d), zn = RU(-a - c); x - y: zu = RU(b - c), zn = RU(d - a).
        if rng.bits(1):
            # The upper lane: d about -b (a sum), c about b (a difference).
            v = _steps(fmt, -b if op == "+" else b, k)
            v = (-b if op == "+" else b) if v is None else v
            w = _number(fmt, rng, "uniform")
            y = (min(w, v), v) if op == "+" else (v, max(w, v))
        else:
            v = _steps(fmt, -a if op == "+" else a, k)
            v = (-a if op == "+" else a) if v is None else v
            w = _number(fmt, rng, "uniform")
            y = (v, max(w, v)) if op == "+" else (min(w, v), v)
        return [x, y]
    if op == "*":
        out = []
        for _ in range(2):
            a, b = -abs(_tiny(fmt, rng)), abs(_tiny(fmt, rng))
            out.append((a, b) if rng.chance(3, 4) else _sorted(_tiny(fmt, rng), _tiny(fmt, rng)))
        return out
    # The set operations and the comparisons: intervals near zero that touch, or cross by a step
    # or two.
    a = -abs(_tiny(fmt, rng))
    b = abs(_tiny(fmt, rng))
    k = rng.between(-2, 2)
    if rng.bits(1):
        lo = _steps(fmt, b, k)
        lo = b if lo is None else lo
        y = (lo, max(lo, abs(_tiny(fmt, rng)) + max(lo, 0)))
    else:
        hi = _steps(fmt, a, k)
        hi = a if hi is None else hi
        y = (min(hi, -abs(_tiny(fmt, rng)) + min(hi, 0)), hi)
    xs = [(a, b), y]
    if rng.bits(1):
        xs.reverse()
    return xs


def _zeroinf(fmt, sh, rng):
    z = [(0, 0), (0, abs(_flavour(fmt, rng)) or 1), (-(abs(_flavour(fmt, rng)) or 1), 0)]
    zero = z[rng.below(3)]
    unb = _special(fmt, rng, ("whole", "halfline")[rng.below(2)])
    return [zero, unb] if rng.bits(1) else [unb, zero]


def _aroundp(fmt, rng):
    A, B = G4._prod_operands(fmt, rng, "aroundp")
    out = []
    for v in (A, B):
        j = rng.below(3)
        other = v if j == 0 else 0 if j == 1 else _number(fmt, rng, "underflow")
        out.append(_sorted(v, other))
    return out


def _sets(fmt, sh, rng, stratum):
    """The intervals of the sets of a case, in the order of sh.sets."""
    n = len(sh.sets)
    if stratum in COMMON:
        ivs = [_bounded(fmt, rng, stratum) for _ in range(n)]
        if stratum in ("overflow", "zero") and rng.chance(1, 4):
            ivs[rng.below(n)] = _special(fmt, rng, "omega" if stratum == "overflow"
                                         else "zerobound")
        return ivs
    if stratum == "crossnear":
        return _crossnear(fmt, sh, rng)
    if stratum == "zeroinf" and n == 2:
        return _zeroinf(fmt, sh, rng)
    if stratum == "aroundp" and n == 2:
        return _aroundp(fmt, rng)
    if stratum in ("zeroinf", "aroundp", "numspecial"):
        # One set and a number (upward_mul_num_1, upward_add_num_1, upward_contains_1): the
        # number is drawn by _number_for to go with it.
        if stratum == "zeroinf":
            if rng.bits(1):
                v = abs(_flavour(fmt, rng)) or 1
                return [[(0, 0), (0, v), (-v, 0)][rng.below(3)]]
            return [_special(fmt, rng, ("whole", "halfline")[rng.below(2)])]
        if stratum == "aroundp":
            A, B = G4._prod_operands(fmt, rng, "aroundp")
            j = rng.below(3)
            other = A if j == 0 else 0 if j == 1 else _number(fmt, rng, "underflow")
            sh.carry = B
            return [_sorted(A, other)]
        return [_any(fmt, rng) for _ in range(n)]
    ivs = [_special(fmt, rng, stratum) if rng.bits(1) else _any(fmt, rng) for _ in range(n)]
    ivs[rng.below(n)] = _special(fmt, rng, stratum)
    return ivs


def _number_for(fmt, sh, rng, stratum, ivs):
    """A number of a case (t of the operations with a number and of contains)."""
    if stratum == "numspecial":
        j = rng.below(6 if sh.contains else 4)
        if j < 4:
            return [INF, NINF, NAN, 0][j]
        x = ivs[0]
        if x == EMPTY or type(x[0]) is not int and type(x[1]) is not int:
            return _number(fmt, rng, "uniform")
        v = x[0] if type(x[0]) is int and (type(x[1]) is not int or rng.bits(1)) else x[1]
        w = _steps(fmt, v, rng.between(-1, 1)) if j == 5 else v
        return v if w is None else w
    if stratum == "zeroinf":
        # A zero bound against t infinite or NaN, an unbounded x against t = 0.
        x = ivs[0]
        if x != EMPTY and (type(x[0]) is not int or type(x[1]) is not int):
            return 0
        return [INF, NINF, NAN][rng.below(3)]
    if stratum == "aroundp":
        # The second factor of the product that _sets drew about P.
        return sh.carry
    if stratum in COMMON:
        return _number(fmt, rng, stratum)
    if rng.chance(1, 6):
        return [INF, NINF, NAN, 0][rng.below(4)]
    return _flavour(fmt, rng)


class _OneLimb:
    k = 1


def _make(fmt, rng, stratum):
    """The bounds given to upward_make_1, in the order (lo, hi)."""
    if stratum in ("nanbound", "reversed", "infinities", "point"):
        lo, hi = G6._ivmake(fmt, _OneLimb, rng, stratum)
        return lo[0], hi[0]
    if stratum == "zerobound":
        v = _flavour(fmt, rng)
        return (0, v) if rng.bits(1) else (v, 0)
    if stratum == "omega":
        a = rng.sign() * _near_omega(fmt, rng)
        b = rng.sign() * _near_omega(fmt, rng) if rng.bits(1) else _flavour(fmt, rng)
        return (a, b) if rng.bits(1) else (b, a)
    if stratum == "subnormal":
        a = rng.sign() * _subnormal(fmt, rng)
        b = rng.sign() * _subnormal(fmt, rng)
        return (a, b)
    return _number(fmt, rng, stratum), _number(fmt, rng, stratum)


def _neg(v):
    return -v if type(v) is int else NINF if v == INF else INF if v == NINF else NAN


def make_case(fmt, sh, rng, stratum):
    """Operand limbs {name: [value]} and the set of (name, 0) whose zero is written -0."""
    vals = {}
    if sh.op == "make":
        lo, hi = _make(fmt, rng, stratum)
        names = sh.numbers
        vals[names[0]], vals[names[1]] = [lo], [hi]
    else:
        ivs = _sets(fmt, sh, rng, stratum)
        for (kind, (a, b)), iv in zip(sh.sets, ivs):
            if kind == "up":
                vals[a], vals[b] = ([NAN], [NAN]) if iv == EMPTY else ([iv[1]], [_neg(iv[0])])
            else:
                vals[a], vals[b] = ([INF], [NINF]) if iv == EMPTY else ([iv[0]], [iv[1]])
        for n in sh.numbers:
            vals[n] = [_number_for(fmt, sh, rng, stratum, ivs)]
    negz = set()
    for n, limbs in vals.items():
        if limbs[0] == 0 and rng.bits(1):
            negz.add((n, 0))
    return vals, negz


# ---------------------------------------------------------------------------
# Validity, written from the page's definitions (the checker has its own)

def _canonical_stored(u, n):
    """upward.md, "States": both lanes a NaN, or neither a NaN nor -inf with -n <= u."""
    if u == NAN or n == NAN:
        return u == n
    if NINF in (u, n):
        return False
    if u == INF or n == INF:
        return True
    return -n <= u


def valid_up(fmt, kernel, vals):
    for name, limbs in vals.items():
        if len(limbs) != dict(kernel.inputs)[name]:
            return False
        for v in limbs:
            if type(v) is int:
                if not F.is_member(fmt, v):
                    return False
            elif v not in (INF, NINF, NAN):
                return False
    for r in kernel.requires:
        if r[0] == "upward":
            if not _canonical_stored(vals[r[1]][0], vals[r[2]][0]):
                return False
        elif r[0] == "interval":
            if not G6._canonical_interval(fmt, vals[r[1]], vals[r[2]]):
                return False
        else:
            return False
    return True


# ---------------------------------------------------------------------------
# Exhaustive enumeration

def _rounding_field(kernel):
    r = getattr(kernel, "rounding", None)
    return " rounding=%s" % r if r else ""


class UpExhaustiveGen(G.ExhaustiveGen):
    """Every operand combination of a kernel of the round-up interval.  A stored pair (its two
    lanes) is one operand: the empty set (NaN, NaN) and every pair (u, n) of numbers of the format
    or +inf with -n <= u; a default interval as gen6.IvExhaustiveGen enumerates it; a number every
    value, +inf, -inf and NaN.  A restriction on an input keeps the finite values (the finite lanes
    of a stored pair) whose leading limb it keeps; the infinities, NaN and the empty set are always
    enumerated."""

    def __init__(self, kernel, fmt, restrictions=(), index_tags=True):
        self.kernel = kernel
        self.fmt = fmt
        G.check_format(kernel, fmt)
        sh = ShapeUp(kernel)
        self.restrictions = [G.Restriction(r) if isinstance(r, str) else r for r in restrictions]
        names = [n for n, _ in kernel.inputs]
        for r in self.restrictions:
            if r.name not in names:
                raise G.GenError("restriction on %r, which is not an input of %s"
                                 % (r.name, kernel.name))

        def keep(nm):
            rs = [r for r in self.restrictions if r.name == nm]
            return lambda v: type(v) is not int or all(r.keep(fmt, v) for r in rs)

        values = [v for (v,) in G3._finite_domain(fmt, 1)]
        self.slots = []
        for kind, (a, b) in sh.sets:
            ka, kb = keep(a), keep(b)
            if kind == "up":
                lanes_u = [v for v in values if ka(v)] + [INF]
                lanes_n = [v for v in values if kb(v)] + [INF]
                dom = [(NAN, NAN)]
                dom += [(u, n) for u in lanes_u for n in lanes_n if _canonical_stored(u, n)]
            else:
                lows = [NINF] + [v for v in values if ka(v)]
                highs = [v for v in values if kb(v)] + [INF]
                dom = [(INF, NINF)]
                dom += [(lo, hi) for lo in lows for hi in highs
                        if _key(lo) <= _key(hi) and lo != INF and hi != NINF]
            self.slots.append(((a, b), dom))
        for n in sh.numbers:
            kn = keep(n)
            self.slots.append(((n,), [(v,) for v in values if kn(v)] + [(INF,), (NINF,), (NAN,)]))
        self.doms = [d for _, d in self.slots]
        self.texts = [[[G3._text(fmt, v) for v in t] for t in dom] for _, dom in self.slots]
        self.total = 1
        for d in self.doms:
            self.total *= len(d)
        self.coupled = []
        self.index_tags = index_tags
        self.restrict_text = ",".join(r.spec for r in self.restrictions) or "none"

    case = G3.ExtExhaustiveGen.case

    def header(self, start, count):
        return ("# kairn-oracle gen event=begin kernel=%s format=%s mode=exhaustive total=%d "
                "restrict=%s skip=none%s start=%d count=%d" % (
                    self.kernel.name, self.fmt.name, self.total, self.restrict_text,
                    _rounding_field(self.kernel), start, count))
