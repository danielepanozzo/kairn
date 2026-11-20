"""Random operands for the first kernels of Milestone 2 (milestone2.md, "Building blocks on T" and
"Scaling a ball by a power of two"), whose claims use the kinds of architecture.md, "Claims of
Milestone 2".

Each kernel gets a family from its claims, chosen from the claims alone, before the families of
the second wave (gen2.Shape2):

    neighbor   a `neighbor` entry (next_up, next_down)
    dirprod    a `bound` entry, or a directed `rounded` entry of a value NAME * NAME
               (mul_down_1, mul_up_1)
    dirsum     a directed `rounded` entry of a value NAME + NAME or NAME - NAME (add_down_1,
               add_up_1, sub_down_1, sub_up_1 and their entry forms)
    ballpow2   an `encloses` entry whose set multiplies a ball by a power_of_two() input
               (ball_mul_pow2_k and its full form)

No kernel of the first two waves or of the non-finite layer has such claims, so their families and
strata are as before.  Each family has the strata every family has (uniform, underflow, overflow,
zero, pow2, extreme), read for its shape, and strata of its own, chosen from the statements:

    neighbor   special   zeros, +-eta, +-2 eta, the smallest normal number N and its neighbours,
                         2N, +-Omega and its predecessor, 2^emax
               binade    powers of two of the whole range and their two neighbours
               subnormal the boundary of the subnormal range: N, pred(N), succ(N), 2N, pred(2N),
                         random subnormal numbers
    dirsum     apart     operands of very different magnitude: the smaller below half an ulp of
                         the larger, or around it
               cancel    b within three ulps of -a (of a for a difference): exact differences
               exact     short significands at nearby exponents: sums that are numbers of the
                         format
               close     exponents within p + 2 of each other
               beyond    sums beyond the overflow threshold on each side, Omega plus a little
               omega     +-Omega as either operand, with every kind of other operand
    dirprod    aroundp   products around P = 2^(2p-1) eta: exactly P, just below and just above,
                         exact and inexact, and products below P whose rounding reaches P
               tiny      products that underflow to zero or to eta: around eta/2, eta, 2 eta,
                         ties at eta/2
               exactprod short significands anywhere, the subnormal range included
               beyond    products beyond the overflow threshold on each side, Omega times about
                         one
    ballpow2   atnormal  a scaled leading limb, second limb or radius exactly N, just above or
                         just below it
               sides     powers of two on both sides of 1: 1/4, 1/2, 1, 2, 4 and up to 2^(+-p)
               into      normal centers and radii scaled into the subnormal range
               outof     subnormal centers and radii scaled out of it

and, for a kernel of the extended domain, the strata of the non-finite layer (gen3.py) on top.
Every case is checked against the requirements before it is written, as for the other families.
"""

from . import fmt as F
from . import gen as G
from . import gen2 as G2

COMMON = G2.COMMON
FAMILY_STRATA = {
    "neighbor": COMMON + ("special", "binade", "subnormal"),
    "dirsum": COMMON + ("apart", "cancel", "exact", "close", "beyond", "omega"),
    "dirprod": COMMON + ("aroundp", "tiny", "exactprod", "beyond"),
    "ballpow2": COMMON + ("atnormal", "sides", "into", "outof"),
}
# The strata at the corners each statement is about come round two or three times per cycle.
FAMILY_SCHEDULE = {
    "neighbor": ("uniform", "special", "binade", "subnormal", "special", "binade", "underflow",
                 "special", "overflow", "pow2", "extreme", "subnormal", "zero"),
    "dirsum": ("uniform", "apart", "cancel", "exact", "close", "beyond", "omega", "apart",
               "beyond", "cancel", "underflow", "omega", "overflow", "pow2", "extreme", "zero"),
    "dirprod": ("uniform", "aroundp", "tiny", "exactprod", "aroundp", "beyond", "underflow",
                "aroundp", "tiny", "overflow", "pow2", "extreme", "zero"),
    "ballpow2": ("uniform", "atnormal", "sides", "into", "atnormal", "outof", "underflow",
                 "atnormal", "overflow", "pow2", "extreme", "zero"),
}
FAMILIES = tuple(FAMILY_STRATA)


def family_of(kernel, roles):
    """The family of a kernel of Milestone 2, or None (a kernel of the earlier waves)."""
    t = kernel.value_tree
    two = (t is not None and t[0] in ("+", "-", "*") and t[1][0] == "name" and t[2][0] == "name"
           and t[1][1] != t[2][1] and all(roles.get(n) == "limb" for n in (t[1][1], t[2][1])))
    kinds = {e.kind for e in kernel.ensures}
    if "neighbor" in kinds:
        return "neighbor"
    directed = any(e.kind == "rounded" and e.mode != "nearest" for e in kernel.ensures)
    if two and t[0] == "*" and ("bound" in kinds or directed):
        return "dirprod"
    if two and t[0] in ("+", "-") and directed:
        return "dirsum"
    for e in kernel.ensures:
        if e.kind == "encloses":
            inball = {n for b in e.balls.values() for n in b}
            from . import expr as EX
            if any(roles.get(n) == "pow2" for n in EX.names(e.set_tree) if n not in inball
                   and n not in e.balls):
                return "ballpow2"
    return None


def setup(sh):
    """The fields of a Shape2 of a Milestone 2 family."""
    k = sh.kernel
    fam = sh.family
    if fam == "neighbor":
        e = next(e for e in k.ensures if e.kind == "neighbor")
        sh.operand = e.operand
    elif fam in ("dirsum", "dirprod"):
        t = k.value_tree
        sh.pair = (t[1][1], t[2][1])
    else:
        e = next(e for e in k.ensures if e.kind == "encloses")
        (sh.center, sh.radius), = e.balls.values()
        sh.scale = next(n for n in sh.names if sh.roles[n] == "pow2")
    sh.strata = FAMILY_STRATA[fam]
    sh.schedule = FAMILY_SCHEDULE[fam]


def make_case(fmt, sh, rng, stratum):
    """Operand limbs {name: [fixed, ...]} and the set of (name, limb) that are -0."""
    fam = sh.family
    if fam == "neighbor":
        vals = {sh.operand: [_neighbor_operand(fmt, rng, stratum)]}
    elif fam == "dirsum":
        vals = _dirsum(fmt, sh, rng, stratum)
    elif fam == "dirprod":
        vals = _dirprod(fmt, sh, rng, stratum)
    else:
        vals = _ballpow2(fmt, sh, rng, stratum)
    for n in sh.names:
        if n not in vals:
            vals[n] = G2.operand(fmt, rng, sh, n, "uniform")
    negz = set()
    # Zeros of either sign wherever they occur: the sign of a zero is never judged, and a kernel
    # must not depend on it.
    for n, limbs in vals.items():
        if sh.roles[n] == "mask":
            continue
        for i, v in enumerate(limbs):
            if v == 0 and rng.bits(1):
                negz.add((n, i))
    return vals, negz


# ---------------------------------------------------------------------------
# Numbers

def _pick(rng, seq):
    return seq[rng.below(len(seq))]


def _pow2_fixed(fmt, e):
    """2^e as a fixed value, or None outside the format."""
    if e < fmt.qmin or e > fmt.emax:
        return None
    return 1 << (e - fmt.qmin)


def _finite(v):
    return type(v) is int


def _succ(fmt, v):
    n = F.succ(fmt, v)
    return n if _finite(n) else v


def _pred(fmt, v):
    n = F.pred(fmt, v)
    return n if _finite(n) else v


def _specials(fmt):
    """Positive special values: eta, 2 eta, 3 eta, N and its neighbours, 2N and its predecessor,
    Omega and its predecessor, 2^emax, 1 when it is a number of the format."""
    lam, om = fmt.lam, fmt.omega
    out = [1, 2, 3, lam, lam - 1, lam + 1, 2 * lam, 2 * lam - 1, om, F.pred(fmt, om),
           _pow2_fixed(fmt, fmt.emax)]
    one = _pow2_fixed(fmt, 0)
    if one:
        out.append(one)
    return [v for v in out if _finite(v) and v > 0 and F.is_member(fmt, v)]


# ---------------------------------------------------------------------------
# neighbor: next_up and next_down

def _neighbor_operand(fmt, rng, stratum):
    if stratum in COMMON:
        return G2.limb(fmt, rng, stratum)
    s = rng.sign()
    if stratum == "special":
        if rng.chance(1, 6):
            return 0
        return s * _pick(rng, _specials(fmt))
    if stratum == "binade":
        p2 = _pow2_fixed(fmt, rng.between(fmt.qmin, fmt.emax))
        return s * _pick(rng, (p2, p2, _succ(fmt, p2), _pred(fmt, p2) or p2))
    if stratum == "subnormal":
        lam = fmt.lam
        k = rng.below(7)
        if k < 5:
            v = (lam, lam - 1, lam + 1, 2 * lam, 2 * lam - 1)[k]
        elif lam > 1:
            v = 1 + rng.below(lam - 1)              # a subnormal number
        else:
            v = lam
        return s * v if F.is_member(fmt, v) and v > 0 else s * lam
    raise G.GenError("unknown stratum %r" % stratum)


# ---------------------------------------------------------------------------
# dirsum: the directed sums and differences of two limbs

def _dirsum(fmt, sh, rng, stratum):
    """A pair (A, B) whose sum A + B is the value: b is B for a sum and -B for a difference."""
    a_name, b_name = sh.pair
    A, B = _sum_operands(fmt, rng, stratum)
    if rng.bits(1):
        A, B = B, A
    if sh.kernel.value_tree[0] == "-":
        B = -B
    return {a_name: [A], b_name: [B]}


def _sum_operands(fmt, rng, stratum):
    p = fmt.p
    om = fmt.omega
    if stratum == "uniform":
        return G2._limb(fmt, rng, G2._e_any(fmt, rng)), G2._limb(fmt, rng, G2._e_any(fmt, rng))
    if stratum == "underflow":
        return G2.limb(fmt, rng, "underflow"), G2.limb(fmt, rng, "underflow")
    if stratum == "overflow":
        return G2._top(fmt, rng), G2.limb(fmt, rng, "overflow" if rng.bits(1) else "uniform")
    if stratum == "zero":
        other = _pick(rng, (0, 1, om, fmt.lam, G2._limb(fmt, rng, G2._e_any(fmt, rng))))
        return 0, rng.sign() * abs(other)
    if stratum == "pow2":
        x = rng.sign() * G2._pow2(fmt, G2._e_any(fmt, rng))
        g = F.ulp(fmt, x)
        # Sums that land just below, on, or just above a power of two.
        y = -(1 if x > 0 else -1) * (g >> rng.below(3) if g > 1 else 1) * (1 + rng.below(2))
        if rng.bits(1):
            y = -y
        if not F.is_member(fmt, y):
            y = rng.sign() * g
        return x, y
    if stratum == "extreme":
        return G.extreme_lead(fmt, rng), (G.extreme_lead(fmt, rng) if rng.bits(1)
                                          else G2.limb(fmt, rng, "uniform"))
    if stratum == "apart":
        x = G2._limb(fmt, rng, G2._e_mid(fmt, rng, p + 2), "short" if rng.chance(1, 4) else "uniform")
        ex = fmt.binade(x)
        # Below half an ulp of x, around it, or far below.
        k = rng.below(4)
        if k == 0:
            ey = ex - p - 1
        elif k == 1:
            ey = ex - p - rng.between(-1, 1)
        else:
            ey = ex - rng.between(p + 1, 3 * p)
        y = G2._limb(fmt, rng, max(fmt.qmin, ey), "short" if rng.chance(1, 4) else "uniform")
        return x, y
    if stratum == "cancel":
        if rng.chance(1, 3):
            x = rng.sign() * G2._pow2(fmt, G2._e_mid(fmt, rng, 2))
        else:
            x = G2._limb(fmt, rng, G2._e_mid(fmt, rng, 2))
        y = -x
        for _ in range(rng.below(4)):
            n = F.succ(fmt, y) if rng.bits(1) else F.pred(fmt, y)
            y = n if _finite(n) else y
        return x, y
    if stratum == "exact":
        e = G2._e_mid(fmt, rng, 2)
        x = G2._limb(fmt, rng, e, "short")
        y = G2._limb(fmt, rng, max(fmt.qmin, e - rng.between(0, max(0, p - 2))), "short")
        return x, y
    if stratum == "close":
        e = G2._e_mid(fmt, rng, p + 2)
        return (G2._limb(fmt, rng, e),
                G2._limb(fmt, rng, max(fmt.qmin, min(fmt.emax, e - rng.between(-(p + 2), p + 2)))))
    if stratum == "beyond":
        s = rng.sign()
        k = rng.below(4)
        if k == 0:
            # Omega plus half an ulp of Omega (a tie that rounds to nearest beyond it), or a bit
            # less, or the smallest number.
            g = F.ulp(fmt, om)
            y = _pick(rng, (g >> 1 if g > 1 else 1, max(1, g >> 2), 1, g))
            return s * om, s * y if F.is_member(fmt, y) else s * g
        x = G.in_binade(fmt, rng, fmt.emax, "high" if rng.bits(1) else "uniform")
        y = G.in_binade(fmt, rng, rng.between(max(fmt.qmin, fmt.emax - 2), fmt.emax),
                        "high" if rng.bits(1) else "uniform")
        return s * x, s * y
    if stratum == "omega":
        s = rng.sign()
        other = _pick(rng, ("omega", "pred", "ulp", "small", "uniform", "top", "zero", "eta"))
        if other == "omega":
            y = om
        elif other == "pred":
            y = F.pred(fmt, om)
        elif other == "ulp":
            y = F.ulp(fmt, om)
        elif other == "small":
            y = abs(G2._small(fmt, rng)) or 1
        elif other == "top":
            y = abs(G2._top(fmt, rng))
        elif other == "zero":
            y = 0
        elif other == "eta":
            y = 1
        else:
            y = abs(G2._limb(fmt, rng, G2._e_any(fmt, rng)))
        y = y if F.is_member(fmt, y) else om
        return s * om, rng.sign() * y
    raise G.GenError("unknown stratum %r" % stratum)


# ---------------------------------------------------------------------------
# dirprod: the directed products of two limbs

def _dirprod(fmt, sh, rng, stratum):
    a_name, b_name = sh.pair
    A, B = _prod_operands(fmt, rng, stratum)
    if rng.bits(1):
        A, B = B, A
    return {a_name: [A], b_name: [B]}


def _p_exponent(fmt):
    """The exponent of P = 2^(2p-1) eta."""
    return fmt.qmin + 2 * fmt.p - 1


def _factor_pair(fmt, rng, et, style="uniform"):
    """Two positive factors whose leading bits sum to the exponent et (as far as the range
    allows)."""
    ea, eb = G._split_exponent(fmt, rng, et)
    return G.in_binade(fmt, rng, ea, style), G.in_binade(fmt, rng, eb, style)


def _quotient_down(fmt, num_fixed_scale, a):
    """RD(2^E / a) for the threshold 2^E given as a fixed value at scale 2 qmin (the scale of a
    product of two fixed values), a > 0 fixed: the largest number y of the format with a y <=
    2^E, or None."""
    y = F.rdir(fmt, num_fixed_scale // a, fmt.qmin, False)
    while y > 0 and a * y > num_fixed_scale:
        y = F.pred(fmt, y)
    return y if _finite(y) and 0 < y <= fmt.omega else None


def _prod_operands(fmt, rng, stratum):
    p = fmt.p
    om = fmt.omega
    s1, s2 = rng.sign(), rng.sign()
    if stratum == "uniform":
        if rng.bits(1):
            a, b = _factor_pair(fmt, rng, rng.between(fmt.qmin - p, fmt.emax))
        else:
            a = G.in_binade(fmt, rng, G2._e_any(fmt, rng))
            b = G.in_binade(fmt, rng, G2._e_any(fmt, rng))
        return s1 * a, s2 * b
    if stratum == "underflow":
        # From below eta through the smallest normal number to past P.
        a, b = _factor_pair(fmt, rng, rng.between(fmt.qmin - p - 1, _p_exponent(fmt) + 2))
        return s1 * a, s2 * b
    if stratum == "overflow":
        a, b = _factor_pair(fmt, rng, rng.between(fmt.emax - 2, fmt.emax + 1), "high")
        return s1 * a, s2 * b
    if stratum == "zero":
        other = _pick(rng, ("zero", "eta", "omega", "lam", "uniform", "top", "one"))
        if other == "zero":
            y = 0
        elif other == "eta":
            y = 1
        elif other == "omega":
            y = om
        elif other == "lam":
            y = fmt.lam
        elif other == "top":
            y = abs(G2._top(fmt, rng))
        elif other == "one":
            y = _pow2_fixed(fmt, 0) or 1
        else:
            y = G.in_binade(fmt, rng, G2._e_any(fmt, rng))
        return 0, s2 * y
    if stratum == "pow2":
        a, b = _factor_pair(fmt, rng, rng.between(fmt.qmin - 2, fmt.emax), "short")
        if rng.bits(1):
            a = 1 << (a.bit_length() - 1)
        return s1 * a, s2 * b
    if stratum == "extreme":
        return G.extreme_lead(fmt, rng), (G.extreme_lead(fmt, rng) if rng.bits(1)
                                          else G2.limb(fmt, rng, "uniform"))
    if stratum == "aroundp":
        return _near_p(fmt, rng, s1, s2)
    if stratum == "tiny":
        k = rng.below(3)
        if k == 0:
            # Exactly eta/2, eta or 2 eta: powers of two.
            et = fmt.qmin + rng.between(-1, 1)
            ea, eb = G._split_exponent(fmt, rng, et)
            return s1 * (_pow2_fixed(fmt, ea) or 1), s2 * (_pow2_fixed(fmt, eb) or 1)
        a, b = _factor_pair(fmt, rng, fmt.qmin + rng.between(-3, 1),
                            "short" if rng.bits(1) else "uniform")
        return s1 * a, s2 * b
    if stratum == "exactprod":
        a, b = _factor_pair(fmt, rng, rng.between(fmt.qmin, fmt.emax), "short")
        return s1 * a, s2 * b
    if stratum == "beyond":
        one = _pow2_fixed(fmt, 0)
        if one and rng.chance(1, 3):
            # Omega times about one.
            return s1 * om, s2 * _pick(rng, (one, _succ(fmt, one), _pred(fmt, one) or one))
        a, b = _factor_pair(fmt, rng, rng.between(fmt.emax, fmt.emax + 2),
                            "high" if rng.bits(1) else "uniform")
        return s1 * a, s2 * b
    raise G.GenError("unknown stratum %r" % stratum)


def _near_p(fmt, rng, s1, s2):
    """Products around P = 2^(2p-1) eta."""
    q = fmt.qmin
    ep = _p_exponent(fmt)
    P2 = 1 << (ep - 2 * q)            # P at the scale of a product of two fixed values
    k = rng.below(5)
    if k == 0:
        # Exactly P, as a product of two powers of two.
        ea, eb = G._split_exponent(fmt, rng, ep)
        a, b = _pow2_fixed(fmt, ea), _pow2_fixed(fmt, eb)
        if a and b:
            return s1 * a, s2 * b
    ea = rng.between(max(q, ep - fmt.emax), min(fmt.emax, ep - q))
    a = G.in_binade(fmt, rng, ea, "short" if k == 1 else "uniform")
    if k == 1 and rng.bits(1):
        a = 1 << (a.bit_length() - 1)
    y = _quotient_down(fmt, P2, a)
    if y is None:
        return s1 * a, s2 * G.in_binade(fmt, rng, ep - ea)
    cands = [y, _succ(fmt, y), _pred(fmt, y) or y, _succ(fmt, _succ(fmt, y))]
    if k == 4:
        # Below P, rounded to P or above.
        for b in (y, _pred(fmt, y)):
            prod = a * b
            if 0 < prod < P2 and F.rn(fmt, prod, 2 * q) == _pow2_fixed(fmt, ep):
                return s1 * a, s2 * b
    return s1 * a, s2 * _pick(rng, cands)


# ---------------------------------------------------------------------------
# ballpow2: the scaling of a ball by a power of two

def _ballpow2(fmt, sh, rng, stratum):
    p = fmt.p
    cn, rn, pn = sh.center, sh.radius, sh.scale
    two = sh.roles[cn] == "x2"
    vals = {}
    sub = {"sides": "uniform", "atnormal": "uniform", "into": "uniform",
           "outof": "underflow"}.get(stratum, stratum)
    vals[cn] = _center(fmt, rng, sh, sub)
    c0 = vals[cn][0]
    if stratum == "underflow":
        mode = _pick(rng, ("zero", "eta", "subnormal", "tiny", "ulp"))
    elif stratum == "overflow":
        mode = _pick(rng, ("huge", "comparable", "wide", "zero"))
    elif stratum == "outof":
        mode = _pick(rng, ("eta", "subnormal", "zero", "tiny"))
    else:
        mode = _pick(rng, G2.RADIUS_MODES)
    vals[rn] = [G2.radius(fmt, rng, c0, mode)]
    n = G2._e_any(fmt, rng)
    if stratum == "zero":
        k = rng.below(3)
        if k != 1:
            vals[cn] = [0] * len(vals[cn])
        if k != 0:
            vals[rn] = [0]
    elif stratum == "overflow":
        big = max(abs(c0), vals[rn][0])
        if big:
            n = fmt.emax - fmt.binade(big) + rng.between(-1, 1)
    elif stratum == "underflow":
        n = rng.between(-2 * p, 2 * p)
    elif stratum == "sides":
        n = _pick(rng, (-2, -1, 0, 1, 2, -rng.between(1, p), rng.between(1, p)))
    elif stratum == "into":
        big = max(abs(c0), vals[rn][0])
        if big:
            target = rng.between(fmt.qmin - 1, fmt.emin_normal)
            n = target - fmt.binade(big)
    elif stratum == "outof":
        big = max(abs(c0), vals[rn][0])
        if big:
            n = G2._e_mid(fmt, rng) - fmt.binade(big)
    elif stratum == "atnormal":
        n = _at_threshold(fmt, sh, rng, vals, two)
    vals[pn] = [G2._pow2(fmt, n)]
    return vals


def _center(fmt, rng, sh, stratum):
    if sh.roles[sh.center] == "x2":
        return G2.expansion(fmt, rng, stratum)
    return [G2.limb(fmt, rng, stratum)]


def _at_threshold(fmt, sh, rng, vals, two):
    """The exponent of c, with one of the scaled leading limb, the scaled second limb (two limbs)
    or the scaled radius set to exactly N, just above it or just below it; vals is changed in
    place."""
    p = fmt.p
    lam = fmt.lam
    # c = 2^k: the operand X0 = N / c is 2^(qmin+p-1-k), a number of the format when
    # qmin + p - 1 - emax <= k <= p - 1.
    lo, hi = max(fmt.qmin, fmt.qmin + p - 1 - fmt.emax), min(fmt.emax, p - 1)
    if lo > hi:
        return G2._e_any(fmt, rng)
    k = rng.between(lo, hi)
    x0 = lam >> k if k >= 0 else lam << -k
    if x0 <= 0 or not F.is_member(fmt, x0):
        return G2._e_any(fmt, rng)
    x = _pick(rng, (x0, x0, _succ(fmt, x0), _pred(fmt, x0) or x0))
    which = _pick(rng, ("lead", "tail", "radius") if two else ("lead", "radius"))
    s = rng.sign()
    cn, rn = sh.center, sh.radius
    if which == "radius":
        vals[rn] = [x]
    elif which == "lead":
        vals[cn] = [s * x] + ([G.tail_for(fmt, rng, s * x, _pick(rng, ("near", "any", "zero")))]
                              if two else [])
    else:
        # A second limb x under a leading limb whose ulp is more than twice x.
        e1 = fmt.binade(x)
        for _ in range(4):
            lead = G.in_binade(fmt, rng, min(fmt.emax, e1 + p + 1 + rng.below(3)))
            t = s * x if rng.bits(1) else -s * x
            if F.normalized_limbs(fmt, [s * lead, t]):
                vals[cn] = [s * lead, t]
                break
    return k
