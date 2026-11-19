"""Random operands for the kernels of the second wave.

The first-wave generator (gen.py) builds two operands around a value of the form NAME op NAME.
The kernels of the second wave have other shapes: one expansion converted or compared, two
limbs stepped up, an expansion scaled by a power of two, balls.  Each input gets a role from
its limbs and requirements (an expansion, a limb, a radius for nonneg(), a power of two for
power_of_two(), a mask), each kernel a family from its claims, and each family its strata.
Every case is checked against the requirements by gen.valid before it is written, as in the
first wave, and the selftest checks that no stratum produces an invalid case.
"""

from . import fmt as F
from .gen import (GenError, in_binade, tail_for, even_lead, extreme_lead, _split_exponent, _mid)

COMMON = ("uniform", "underflow", "overflow", "zero", "pow2", "extreme")
FAMILY_STRATA = {
    "unary": COMMON + ("halfgap",),
    "compare": COMMON + ("equal", "lastplace", "leadequal", "neighbor", "straddle", "halfgap"),
    "step": COMMON + ("nonneg", "tie", "close"),
    "scale": COMMON + ("into", "outof", "halfscaled"),
    "ball": COMMON + ("radii", "wide", "exact", "centerpow2", "cancel"),
}
# Strata that reach the corner each family is about come round twice per cycle.
FAMILY_SCHEDULE = {
    "unary": ("uniform", "halfgap", "pow2", "underflow", "halfgap", "overflow", "extreme",
              "zero"),
    "compare": ("uniform", "equal", "lastplace", "leadequal", "neighbor", "straddle", "halfgap",
                "equal", "lastplace", "underflow", "overflow", "pow2", "extreme", "zero"),
    "step": ("uniform", "tie", "nonneg", "close", "tie", "pow2", "underflow", "nonneg", "overflow",
             "extreme", "zero"),
    "scale": ("uniform", "into", "halfscaled", "outof", "into", "halfscaled", "pow2", "underflow",
              "overflow", "extreme", "zero"),
    "ball": ("uniform", "radii", "wide", "exact", "centerpow2", "radii", "cancel", "underflow",
             "centerpow2", "overflow", "pow2", "extreme", "zero"),
}

TAILS = ("near", "any", "half+", "half-", "quarter-", "max", "eta", "tiny", "zero")
HALF_TAILS = ("half+", "half-", "quarter-")
EXTREME_TAILS = ("half+", "half-", "quarter-", "max", "eta", "tiny", "zero")


class Shape2:
    def __init__(self, kernel):
        self.kernel = kernel
        req = kernel.requires
        self.roles = {}
        for n, l in kernel.inputs:
            if n in kernel.masks:
                role = "mask"
            elif l == 2:
                if ("normalized", n) not in req:
                    raise GenError("%s: a 2-limb input without normalized() is not generated"
                                   % kernel.name)
                role = "x2"
            elif l > 2:
                raise GenError("%s: inputs of more than two limbs are not generated yet" % kernel.name)
            elif ("power_of_two", n) in req:
                role = "pow2"
            elif ("nonneg", n) in req:
                role = "radius"
            else:
                role = "limb"
            self.roles[n] = role
        self.names = [n for n, _ in kernel.inputs]
        kinds = {e.kind for e in kernel.ensures}
        self.op = kernel.value_tree[0] if kernel.value_tree is not None else None
        if "encloses" in kinds:
            self.family = "ball"
            enc = next(e for e in kernel.ensures if e.kind == "encloses")
            self.balls = list(enc.balls.values())
            inball = {n for b in self.balls for n in b}
            self.scalars = [n for n in self.names if n not in inball]
            self.set_op = enc.set_tree[0]
        elif "predicate" in kinds:
            self.family = "compare"
        elif "pow2" in self.roles.values():
            self.family = "scale"
        elif "upper" in kinds:
            self.family = "step"
        else:
            self.family = "unary"
        if self.family == "compare":
            args = next(e for e in kernel.ensures if e.kind == "predicate").args
            if all(a[0] == "name" for a in args) and args[0][1] != args[1][1]:
                self.pair = (args[0][1], args[1][1])
            else:
                self.pair = tuple(n for n in self.names if self.roles[n] != "mask")[:2]
        self.strata = FAMILY_STRATA[self.family]
        self.schedule = FAMILY_SCHEDULE[self.family]


# ---------------------------------------------------------------------------
# Numbers

def _limb(fmt, rng, e, style="uniform"):
    return rng.sign() * in_binade(fmt, rng, e, style)


def _e_any(fmt, rng):
    return rng.between(fmt.qmin, fmt.emax)


def _e_mid(fmt, rng, margin=None):
    m = 2 * fmt.p + 2 if margin is None else margin
    return rng.between(*_mid(fmt, m, 2))


def _e_low(fmt, rng):
    return rng.between(fmt.qmin, min(fmt.emax, fmt.emin_normal + 2 * fmt.p))


def _pow2(fmt, e):
    e = max(fmt.qmin, min(fmt.emax, e))
    return 1 << (e - fmt.qmin)


def _top(fmt, rng):
    """A leading limb in the top binades: Omega, its predecessor, 2^emax, or random."""
    k = rng.below(4)
    if k == 0:
        v = fmt.omega
    elif k == 1:
        v = F.pred(fmt, fmt.omega)
    elif k == 2:
        v = _pow2(fmt, fmt.emax)
    else:
        v = in_binade(fmt, rng, rng.between(max(fmt.qmin, fmt.emax - 2), fmt.emax),
                      "high" if rng.bits(1) else "uniform")
    return rng.sign() * v


def _small(fmt, rng):
    """Zero, eta, lambda or their neighbours, or a subnormal."""
    k = rng.below(6)
    if k == 0:
        return 0
    if k == 1:
        v = 1
    elif k == 2:
        v = fmt.lam
    elif k == 3:
        v = fmt.lam - 1
    else:
        v = in_binade(fmt, rng, _e_low(fmt, rng))
    return rng.sign() * v


def _x2(fmt, rng, x0, mode):
    return [x0, tail_for(fmt, rng, x0, mode)]


def _x2_even(fmt, rng, x0, mode):
    """An expansion whose tail is at the half-gap corner; a tie toward x0 is allowed only
    when x0's significand is even, so x0 is moved to an even neighbour first."""
    if mode in ("half+", "half-") and x0:
        e = even_lead(fmt, x0)
        x0 = e if type(e) is int else x0
    return _x2(fmt, rng, x0, mode)


def expansion(fmt, rng, stratum):
    """One normalized 2-limb operand for a stratum common to the families."""
    p = fmt.p
    if stratum == "uniform":
        return _x2(fmt, rng, _limb(fmt, rng, _e_any(fmt, rng)), "near" if rng.bits(1) else "any")
    if stratum == "halfgap":
        k = rng.below(3)
        if k == 0:
            x0 = rng.sign() * _pow2(fmt, _e_any(fmt, rng))
        elif k == 1:
            x0 = _limb(fmt, rng, _e_mid(fmt, rng), "short" if rng.bits(1) else "uniform")
        else:
            x0 = extreme_lead(fmt, rng)
        return _x2_even(fmt, rng, x0, HALF_TAILS[rng.below(3)])
    if stratum == "pow2":
        x0 = rng.sign() * _pow2(fmt, _e_any(fmt, rng))
        return _x2_even(fmt, rng, x0, TAILS[rng.below(len(TAILS))])
    if stratum == "underflow":
        x0 = _limb(fmt, rng, _e_low(fmt, rng))
        return _x2_even(fmt, rng, x0, ("any", "near", "half+", "half-", "eta")[rng.below(5)])
    if stratum == "overflow":
        return _x2_even(fmt, rng, _top(fmt, rng), ("near", "any", "half+", "half-", "quarter-",
                                                   "max")[rng.below(6)])
    if stratum == "zero":
        k = rng.below(3)
        if k == 0:
            return [0, 0]
        x0 = rng.sign() * (1 if k == 1 else fmt.lam)
        return _x2(fmt, rng, x0, "zero" if rng.bits(1) else "near")
    if stratum == "extreme":
        x0 = extreme_lead(fmt, rng) if rng.bits(1) else _limb(
            fmt, rng, _e_mid(fmt, rng, p + 2), "short" if rng.bits(1) else "uniform")
        return _x2_even(fmt, rng, x0, EXTREME_TAILS[rng.below(len(EXTREME_TAILS))])
    raise GenError("no expansion for stratum %r" % stratum)


def limb(fmt, rng, stratum):
    """One limb for a stratum common to the families."""
    if stratum in ("uniform", "halfgap"):
        return _limb(fmt, rng, _e_any(fmt, rng), "short" if rng.chance(1, 8) else "uniform")
    if stratum == "pow2":
        return rng.sign() * _pow2(fmt, _e_any(fmt, rng))
    if stratum == "underflow":
        return _small(fmt, rng) if rng.bits(1) else _limb(fmt, rng, _e_low(fmt, rng))
    if stratum == "overflow":
        return _top(fmt, rng)
    if stratum == "zero":
        return 0 if rng.chance(2, 3) else _small(fmt, rng)
    if stratum == "extreme":
        return extreme_lead(fmt, rng)
    raise GenError("no limb for stratum %r" % stratum)


def operand(fmt, rng, sh, name, stratum):
    role = sh.roles[name]
    if role == "mask":
        return [rng.bits(1)]
    if role == "x2":
        return expansion(fmt, rng, stratum)
    if role == "pow2":
        return [_pow2(fmt, _e_any(fmt, rng))]
    v = limb(fmt, rng, stratum)
    return [abs(v)] if role == "radius" else [v]


# ---------------------------------------------------------------------------
# Families

def make_case(fmt, sh, rng, stratum):
    """Operand limbs {name: [fixed, ...]} and the set of (name, limb) that are -0."""
    fam = sh.family
    if fam == "compare":
        vals = _compare(fmt, sh, rng, stratum)
    elif fam == "step":
        vals = _step(fmt, sh, rng, stratum)
    elif fam == "scale":
        vals = _scale(fmt, sh, rng, stratum)
    elif fam == "ball":
        vals = _ball(fmt, sh, rng, stratum)
    else:
        vals = {n: operand(fmt, rng, sh, n, stratum) for n in sh.names}
    negz = set()
    if stratum in ("zero", "equal", "straddle"):
        for n, limbs in vals.items():
            if sh.roles[n] == "mask":
                continue
            for i, v in enumerate(limbs):
                if v == 0 and rng.bits(1):
                    negz.add((n, i))
    return vals, negz


def _as(sh, name, x):
    """x (an expansion as a list) as an operand of the input's limb count: a one-limb input
    takes the leading limb only."""
    return list(x) if sh.roles[name] == "x2" else [x[0]]


def _compare(fmt, sh, rng, stratum):
    a, b = sh.pair
    vals = {n: operand(fmt, rng, sh, n, "uniform") for n in sh.names}
    if stratum in COMMON:
        for n in (a, b):
            vals[n] = operand(fmt, rng, sh, n, stratum)
        if stratum in ("overflow", "zero", "pow2") and rng.bits(1):
            # Both operands at the same corner, so that the leading limbs often coincide.
            vals[b] = _as(sh, b, (vals[a] + [0])[:2])
        return vals
    two_a, two_b = sh.roles[a] == "x2", sh.roles[b] == "x2"
    if stratum == "halfgap":
        x = expansion(fmt, rng, "halfgap")
        y = expansion(fmt, rng, "halfgap")
        if rng.bits(1):
            # Leading limbs one apart and tails at the half gap: values that nearly coincide.
            n = F.succ(fmt, x[0]) if rng.bits(1) else F.pred(fmt, x[0])
            if type(n) is int:
                y = _x2_even(fmt, rng, n, HALF_TAILS[rng.below(3)])
        vals[a], vals[b] = _as(sh, a, x), _as(sh, b, y)
        return vals
    x = expansion(fmt, rng, ("uniform", "pow2", "underflow", "extreme", "overflow")[rng.below(5)]
                  if rng.chance(1, 2) else "uniform")
    if stratum == "straddle":
        x0 = _small(fmt, rng) if rng.bits(1) else _limb(fmt, rng, _e_low(fmt, rng))
        x = _x2(fmt, rng, x0, ("near", "any", "zero", "eta")[rng.below(4)])
        y0 = -x0 if x0 and rng.bits(1) else -(x0 or 1) * (1 + rng.below(3))
        y0 = y0 if F.is_member(fmt, y0) else -x0
        y = _x2(fmt, rng, y0, ("near", "any", "zero", "eta")[rng.below(4)])
        if rng.chance(1, 4):
            y = [0, 0]
        vals[a], vals[b] = _as(sh, a, x), _as(sh, b, y)
        return vals
    if not two_a or not two_b:
        # A one-limb operand is its own leading limb with a zero tail.
        if not two_a:
            x = [x[0], 0]
    if stratum == "equal":
        y = list(x)
        if two_a != two_b:
            # Equal values need the 2-limb side's tail to be zero; half the time keep it, so
            # that the operands differ only below the leading limb.
            if rng.bits(1):
                x = [x[0], 0]
                y = [x[0], 0]
    elif stratum == "lastplace":
        if two_a != two_b:
            # A one-limb operand against the same leading limb with the smallest tail of
            # either sign.
            y = [x[0], _nudge(fmt, [x[0], 0], rng.bits(1))]
            vals[a if two_a else b] = y
            vals[b if two_a else a] = [x[0]]
            return vals
        y = [x[0], _nudge(fmt, x, rng.bits(1))]
    elif stratum == "leadequal":
        y = _x2(fmt, rng, x[0], TAILS[rng.below(len(TAILS))])
    elif stratum == "neighbor":
        n = F.succ(fmt, x[0]) if rng.bits(1) else F.pred(fmt, x[0])
        n = n if type(n) is int else x[0]
        y = _x2_even(fmt, rng, n, TAILS[rng.below(len(TAILS))])
    else:
        raise GenError("unknown stratum %r" % stratum)
    if rng.bits(1):
        x, y = y, x
    vals[a], vals[b] = _as(sh, a, x), _as(sh, b, y)
    return vals


def _nudge(fmt, x, up):
    """The second limb of x moved to a neighbour, up or down (from zero: the smallest number
    of either sign), keeping (x0, x1) normalized; the other direction when that breaks it."""
    t = x[1]
    for d in (up, not up):
        n = F.succ(fmt, t) if d else F.pred(fmt, t)
        if type(n) is int and F.normalized_limbs(fmt, [x[0], n]):
            return n
    return t


def _odd_factors(n):
    """A factorization n = d * (n // d) with d a small odd prime, or None."""
    for d in (3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79,
              83, 89, 97):
        if n % d == 0 and n > d:
            return d, n // d
    return None


def _scaled(fmt, m, e):
    """m * 2^e as a fixed value, or None when it is not a number of the format."""
    sh = e - fmt.qmin
    if sh < 0:
        if m % (1 << -sh):
            return None
        v = m >> -sh
    else:
        v = m << sh
    return v if F.is_member(fmt, v) else None


def _step(fmt, sh, rng, stratum):
    a, b = sh.names[:2]
    p = fmt.p
    mul = sh.op == "*"
    vals = {}
    if stratum in ("uniform", "nonneg"):
        if mul and rng.bits(1):
            ea, eb = _split_exponent(fmt, rng, rng.between(fmt.qmin - p, fmt.emax))
        else:
            ea, eb = _e_any(fmt, rng), _e_any(fmt, rng)
        x, y = _limb(fmt, rng, ea), _limb(fmt, rng, eb)
        if stratum == "nonneg":
            x, y = abs(x), abs(y)
            if rng.chance(1, 4):
                x, y = _tie(fmt, rng, mul)
                x, y = abs(x), abs(y)
    elif stratum == "close":
        if mul:
            ea, eb = _split_exponent(fmt, rng, _e_mid(fmt, rng, 3 * p))
        else:
            ea = _e_mid(fmt, rng)
            eb = ea - rng.between(-(p + 2), p + 2)
        x, y = _limb(fmt, rng, ea), _limb(fmt, rng, eb)
    elif stratum == "tie":
        x, y = _tie(fmt, rng, mul)
    elif stratum == "pow2":
        e = _e_mid(fmt, rng)
        x = rng.sign() * _pow2(fmt, e)
        if mul:
            y = _limb(fmt, rng, _e_mid(fmt, rng, 3 * p), "short" if rng.bits(1) else "uniform")
        else:
            # Sums that land just below, on, or just above a power of two.
            g = F.ulp(fmt, x)
            y = -(x // abs(x)) * (g >> rng.below(3) if g > 1 else 1) * (1 + rng.below(2))
            if rng.bits(1):
                y = -y
            if not F.is_member(fmt, y):
                y = rng.sign() * g
    elif stratum == "underflow":
        if mul:
            ea, eb = _split_exponent(fmt, rng, rng.between(fmt.qmin - p - 1, fmt.emin_normal + p))
            x, y = _limb(fmt, rng, ea), _limb(fmt, rng, eb)
        else:
            x, y = limb(fmt, rng, "underflow"), limb(fmt, rng, "underflow")
    elif stratum == "overflow":
        if mul:
            ea, eb = _split_exponent(fmt, rng, rng.between(fmt.emax - 2, fmt.emax + 1))
            x, y = _limb(fmt, rng, ea, "high"), _limb(fmt, rng, eb, "high")
        else:
            x, y = _top(fmt, rng), limb(fmt, rng, "overflow" if rng.bits(1) else "uniform")
    else:
        x, y = limb(fmt, rng, stratum), limb(fmt, rng, stratum)
    if rng.bits(1):
        x, y = y, x
    # An operand required to be nonnegative keeps its magnitude and loses its sign, so that
    # every stratum still reaches its corner (a tie, a power of two, the two ends of the range).
    if sh.roles[a] == "radius":
        x = abs(x)
    if sh.roles[b] == "radius":
        y = abs(y)
    vals[a], vals[b] = [x], [y]
    return vals


def _tie(fmt, rng, mul):
    """Two limbs whose exact sum or product lies halfway between two numbers of the format:
    N * 2^E with N odd and the rounding unit 2^(E+1), so RN rounds to even and the step that
    follows it is at its furthest from the exact value."""
    p = fmt.p
    for _ in range(8):
        k = rng.below(4)
        if k == 0:
            n = (1 << p) + 1                       # just above a power of two
        elif k == 1:
            n = (1 << (p + 1)) - 1                 # just below one
        else:
            n = (1 << p) | (rng.bits(p) | 1)
        s = rng.sign()
        if not mul:
            # (N - 1)/2 has p bits: x = (N - 1) 2^E and y = 2^E add up to N 2^E.
            e = rng.between(fmt.qmin, max(fmt.qmin, fmt.emax - p - 1))
            x, y = _scaled(fmt, n - 1, e), _scaled(fmt, 1, e)
            if x is not None and y is not None:
                return s * x, s * y if rng.chance(3, 4) else -s * y
            continue
        if rng.chance(1, 4):
            # Below the normal range the unit is eta: any odd N with fewer than p bits.
            n = rng.bits(p - 1) | 1
            e = fmt.qmin - 1
        else:
            e = _e_mid(fmt, rng, 3 * p) - p
        f = _odd_factors(n)
        if f is None or f[1] >= 1 << p:
            continue
        d, c = f
        # Both factors are odd, so neither exponent may be below qmin.
        ea = rng.between(fmt.qmin, max(fmt.qmin, e - fmt.qmin))
        x, y = _scaled(fmt, d, ea), _scaled(fmt, c, e - ea)
        if x is not None and y is not None:
            return s * x, rng.sign() * y
    return _limb(fmt, rng, _e_mid(fmt, rng)), _limb(fmt, rng, _e_mid(fmt, rng))


def _scale(fmt, sh, rng, stratum):
    xn = next(n for n in sh.names if sh.roles[n] == "x2")
    cn = next(n for n in sh.names if sh.roles[n] == "pow2")
    vals = {n: operand(fmt, rng, sh, n, "uniform") for n in sh.names}
    p = fmt.p
    if stratum in ("uniform", "underflow", "overflow", "zero", "pow2", "extreme"):
        x = expansion(fmt, rng, stratum)
        if stratum == "overflow" and x[0]:
            # Products near Omega and beyond.
            n = fmt.emax - fmt.binade(x[0]) + rng.between(-1, 1)
        elif stratum == "underflow":
            # Small operands scaled a little: the products stay around the subnormal range.
            n = rng.between(-2 * p, 2 * p)
        else:
            n = _e_any(fmt, rng)
    elif stratum in ("into", "outof"):
        if stratum == "into":
            x = expansion(fmt, rng, "uniform" if rng.bits(1) else "pow2")
        else:
            x = expansion(fmt, rng, "underflow")
        if stratum == "into":
            target = rng.between(fmt.qmin - p - 1, fmt.emin_normal + p)
        else:
            target = _e_mid(fmt, rng)
        n = target - fmt.binade(x[0]) if x[0] else _e_any(fmt, rng)
    elif stratum == "halfscaled":
        # x1 just below half an ulp of x0, and c so that half an ulp of h = c x0 is 2^j eta
        # for a small j: c x1 then rounds to exactly half a gap of h.
        x0 = _limb(fmt, rng, _e_mid(fmt, rng, 2 * p + 2), "short" if rng.bits(1) else "uniform")
        h = F.ulp(fmt, x0) >> 1
        t = h
        for _ in range(rng.below(3)):
            t = F.pred(fmt, t)
        x1 = (1 if x0 > 0 else -1) * t * (1 if rng.bits(1) else -1)
        x = [x0, x1] if F.normalized_limbs(fmt, [x0, x1]) else _x2_even(fmt, rng, x0, "half+")
        j = rng.between(0, p)
        n = fmt.qmin + j + 1 - fmt.binade(F.ulp(fmt, x0))
    else:
        raise GenError("unknown stratum %r" % stratum)
    vals[xn] = x
    vals[cn] = [_pow2(fmt, n)]
    return vals


# -- balls -----------------------------------------------------------------------

RADIUS_MODES = ("zero", "eta", "subnormal", "tiny", "ulp", "comparable", "wide", "huge", "uniform")


def radius(fmt, rng, c0, mode):
    """A nonnegative radius for a ball whose center has leading limb c0."""
    p = fmt.p
    ec = fmt.binade(c0) if c0 else fmt.emin_normal
    if mode == "zero":
        return 0
    if mode == "eta":
        return 1
    if mode == "subnormal":
        return in_binade(fmt, rng, rng.between(fmt.qmin, fmt.emin_normal - 1)) if \
            fmt.emin_normal > fmt.qmin else 1
    if mode == "tiny":
        e = ec - rng.between(p, 3 * p)
    elif mode == "ulp":
        e = ec - p + 1 + rng.between(-2, 1)
    elif mode == "comparable":
        e = ec - rng.between(0, 4)
    elif mode == "wide":
        e = ec + rng.between(1, p + 2)
    elif mode == "huge":
        return abs(_top(fmt, rng)) >> rng.below(3)
    else:
        e = _e_any(fmt, rng)
    if e < fmt.qmin:
        return 0 if rng.bits(1) else 1
    return in_binade(fmt, rng, min(e, fmt.emax), "short" if rng.chance(1, 4) else "uniform")


def _center(fmt, rng, sh, name, stratum):
    if sh.roles[name] == "x2":
        return expansion(fmt, rng, stratum)
    return [limb(fmt, rng, stratum)]


def _ball(fmt, sh, rng, stratum):
    p = fmt.p
    vals = {}
    sub = "uniform" if stratum in ("radii", "wide", "exact", "centerpow2", "cancel") else stratum
    for cn, rn in sh.balls:
        if stratum in ("radii", "exact", "cancel"):
            vals[cn] = _center(fmt, rng, sh, cn, "uniform" if rng.bits(1) else "extreme")
            if sh.roles[cn] == "x2" and stratum != "exact":
                vals[cn] = _x2(fmt, rng, _limb(fmt, rng, _e_mid(fmt, rng)), "near")
        elif stratum == "wide":
            vals[cn] = _center(fmt, rng, sh, cn, ("zero", "underflow", "uniform")[rng.below(3)])
        elif stratum == "centerpow2" and len(sh.balls) == 2 and sh.set_op in ("+", "-"):
            # A random center; the other is chosen below so that the sum is a power of two.
            x0 = _limb(fmt, rng, _e_mid(fmt, rng))
            vals[cn] = _x2(fmt, rng, x0, "near") if sh.roles[cn] == "x2" else [x0]
        elif stratum == "centerpow2":
            x0 = rng.sign() * _pow2(fmt, _e_mid(fmt, rng))
            vals[cn] = _x2_even(fmt, rng, x0, TAILS[rng.below(len(TAILS))]) \
                if sh.roles[cn] == "x2" else [x0]
        else:
            vals[cn] = _center(fmt, rng, sh, cn, sub)
        c0 = vals[cn][0]
        if stratum == "exact":
            mode = "zero"
        elif stratum == "wide":
            mode = ("wide", "huge", "comparable", "uniform")[rng.below(4)]
        elif stratum == "centerpow2":
            mode = ("zero", "eta", "tiny", "ulp")[rng.below(4)]
        elif stratum == "underflow":
            mode = ("zero", "eta", "subnormal", "tiny", "ulp")[rng.below(5)]
        elif stratum == "overflow":
            mode = ("huge", "comparable", "wide", "zero")[rng.below(4)]
        elif stratum == "zero":
            mode = ("zero", "eta", "uniform")[rng.below(3)]
        else:
            mode = RADIUS_MODES[rng.below(len(RADIUS_MODES))]
        vals[rn] = [radius(fmt, rng, c0, mode)]
    for n in sh.scalars:
        if stratum in ("centerpow2",):
            vals[n] = [rng.sign() * _pow2(fmt, _e_mid(fmt, rng))]
        elif stratum in ("radii", "wide", "exact", "cancel"):
            vals[n] = [_limb(fmt, rng, _e_mid(fmt, rng), "short" if rng.bits(1) else "uniform")]
        else:
            vals[n] = [limb(fmt, rng, sub)]
    if len(sh.balls) == 2:
        (cx, _), (cy, _) = sh.balls
        x = vals[cx]
        if stratum == "cancel" and sh.set_op in ("+", "-"):
            # The centers cancel up to a few units: the result is small, its error relative.
            s = -1 if sh.set_op == "+" else 1
            y0 = s * x[0]
            for _ in range(rng.below(3)):
                n = F.succ(fmt, y0) if rng.bits(1) else F.pred(fmt, y0)
                y0 = n if type(n) is int else y0
            vals[cy] = _x2(fmt, rng, y0, "near") if sh.roles[cy] == "x2" else [y0]
        elif stratum == "centerpow2" and sh.set_op in ("+", "-") and x[0]:
            # A sum that is exactly a power of two, or within a tail of one.
            e = fmt.binade(x[0]) + rng.between(0, 1)
            target = (1 if x[0] > 0 else -1) * _pow2(fmt, e)
            y0 = target - x[0]
            if sh.set_op == "-":
                y0 = -y0
            if F.is_member(fmt, y0):
                vals[cy] = _x2(fmt, rng, y0, ("zero", "near", "tiny")[rng.below(3)]) \
                    if sh.roles[cy] == "x2" else [y0]
        elif stratum == "overflow" and sh.set_op == "*" and x[0]:
            # Products near Omega.
            e = fmt.emax - fmt.binade(x[0]) + rng.between(-1, 0)
            y0 = rng.sign() * in_binade(fmt, rng, max(fmt.qmin, min(fmt.emax, e)), "high")
            vals[cy] = _x2(fmt, rng, y0, "near") if sh.roles[cy] == "x2" else [y0]
    return vals
