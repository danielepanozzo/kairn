"""Random operands for the kernels of the ball vectors and of the accumulator (architecture.md, "Ball
vectors", "The accumulator"), chosen from claims that no earlier kernel has, before every earlier
family:

    radius    every entry an upper with a value of its own and no if (bv_add_radius_k,
              bv_scale_radius_k, bv_mul_pow2_radius, conv_radius): nonnegative operands, a count, a
              bound at_most(g, K), a power of two, a mask
    acc       a rounded entry with a value of its own (acc_add_k, acc_mul_k, acc_merge_k): the
              running sum, the sum of magnitudes and what is added
    accradius a count() input under entries that hold under a mask and name no unit( ) (the radius
              of an accumulator, acc_radius_k)
    bvfinish  finite_or_nan with nonneg or if_all (bv_make_finish, bv_conv_finish), the extended
              domain: the value any value of the format, the masks both ways

The other kernels of the ball vectors keep the families of the kernels whose claims they have: the
copies and negations (bv_center_entry_1, neg_1, bv_neg_radius, bv_make_radius) the unary family of
gen2.py, bv_center_2 that of the non-finite layer (gen3.py), the steps of the scalings
(bv_mul_pow2_step_k) gen2.py's scale family.  Each family has the strata every family has (uniform,
underflow, overflow, zero, pow2, extreme), read for its shape, and strata of its own:

    radius    huge      operands in the top binades: the radius overflows to +inf, or nearly
              zeros     most operands zero, the count zero
              mixed     operands of very different magnitudes (one dominates the stated value)
              atnormal  a power of two that brings the radius to the smallest normal number N,
                        just below or just above it, or zero; the mask both ways (the exact_when
                        of bv_mul_pow2_radius)
    acc       cancel    the element within a few units of minus the running sum
              tie       the sum of magnitudes a tie: |x| (|x0| |y0|) an odd multiple of half a unit
                        of a
              apart     a far above or far below what is added
              atop      a in the top binades: the sum of magnitudes overflows to +inf while the
                        running sum stays finite (A4 of experiments/milestone2/accumulator.py)
              exactprod short significands
    accradius integer   m an integer from 1 up, g and t of the size of the bound of a dot product
                        of m terms
              limit     m u around 1/2, the limit of the mask
              beyond    m u above 1/2: the mask false
              abig      a large, the stated value below Omega/8
    bvfinish  nonfinite the value +inf, -inf or a NaN
              negative  a negative value: -eta, -lambda, -Omega, random
              zeros     a zero of either sign
              top       Omega and its predecessor
              masks     a positive finite value, each mask both ways

Every case is checked against the requirements before it is written (valid8), and the selftest
checks that no stratum produces an invalid case.
"""

from fractions import Fraction

from . import cexpr as CX
from . import fmt as F
from . import gen as G
from . import gen2 as G2

INF, NINF, NAN = F.POS_INF, F.NEG_INF, F.NAN
COMMON = G2.COMMON
FAMILY_STRATA = {
    "radius": COMMON + ("huge", "zeros", "mixed", "atnormal"),
    "acc": COMMON + ("cancel", "tie", "apart", "atop", "exactprod"),
    "accradius": COMMON + ("integer", "limit", "beyond", "abig"),
    "bvfinish": COMMON + ("nonfinite", "negative", "zeros", "top", "masks"),
}
FAMILY_SCHEDULE = {
    "radius": ("uniform", "mixed", "huge", "atnormal", "zeros", "mixed", "underflow", "atnormal",
               "overflow", "huge", "zero", "pow2", "extreme", "mixed"),
    "acc": ("uniform", "cancel", "tie", "atop", "apart", "cancel", "underflow", "tie", "atop",
            "overflow", "exactprod", "zero", "pow2", "extreme", "apart"),
    "accradius": ("uniform", "integer", "limit", "beyond", "integer", "limit", "abig", "underflow",
                  "limit", "overflow", "zero", "pow2", "extreme", "integer"),
    "bvfinish": ("uniform", "nonfinite", "negative", "zeros", "masks", "nonfinite", "top",
                 "negative", "underflow", "masks", "overflow", "zero", "pow2", "extreme"),
}
FAMILIES = tuple(FAMILY_STRATA)


def family_of(kernel):
    """The family of a kernel of the ball vectors or of the accumulator, or None."""
    ens = kernel.ensures
    if ens and all(getattr(e, "bv", False) for e in ens):
        return "radius"
    if any(getattr(e, "own_tree", None) is not None for e in ens):
        return "acc"
    if any(e.kind == "finite_or_nan" and (getattr(e, "nonneg", False) or getattr(e, "if_all", None))
           for e in ens):
        return "bvfinish"
    if (getattr(kernel, "conditional", False) and any(r[0] == "count" for r in kernel.requires)
            and not any(CX.calls(t) for e in ens
                        for t in ([e.cvalue] if e.cvalue is not None else [])
                        + list(getattr(e, "cargs", [])))):
        return "accradius"
    return None


class Shape8:
    def __init__(self, kernel):
        self.kernel = kernel
        self.family = family_of(kernel)
        if self.family is None:
            raise G.GenError("%s: not a kernel of the ball vectors or the accumulator" % kernel.name)
        self.names = [n for n, _ in kernel.inputs]
        self.limbs = dict(kernel.inputs)
        req = {(r[0], r[1]) for r in kernel.requires}
        self.at_most = {r[1]: r[2] for r in kernel.requires if r[0] == "at_most"}
        self.roles = {}
        for n, l in kernel.inputs:
            if n in kernel.masks:
                role = "mask"
            elif l == 2:
                if ("normalized", n) not in req and not kernel.extended:
                    raise G.GenError("%s: a 2-limb input without normalized() is not generated"
                                     % kernel.name)
                role = "x2"
            elif l > 2:
                raise G.GenError("%s: inputs of more than two limbs are not generated" % kernel.name)
            elif n in self.at_most:
                role = "atmost"
            elif ("count", n) in req:
                role = "count"
            elif ("power_of_two", n) in req:
                role = "pow2"
            elif ("nonneg", n) in req:
                role = "radius"
            else:
                role = "limb"
            self.roles[n] = role
        self.strata = FAMILY_STRATA[self.family]
        self.schedule = FAMILY_SCHEDULE[self.family]
        # A radius kernel whose claim is of finite results (bvec.FINITE_RESULTS, conv_radius):
        # its entry's value, the stated value, scaled below Omega/8 (see _within).
        self.finite_results = self.family == "radius" and any(
            getattr(e, "finite_results", False) for e in kernel.ensures)
        if self.family == "acc":
            # s, a, then what is added: x (and y), or v and c (a merge).
            self.s = self.names[0]
            self.a = self.names[1]
            self.rest = self.names[2:]
            self.k = self.limbs[self.s]


# ---------------------------------------------------------------------------
# Numbers

def _one(fmt):
    return (1 << -fmt.qmin) if fmt.qmin < 0 else 1


def _per_eta(fmt):
    return Fraction(1 << -fmt.qmin) if fmt.qmin < 0 else Fraction(1, 1 << fmt.qmin)


def _fixed_down(fmt, f):
    """The rational f (a value) rounded down to a number of the format, as a fixed value."""
    q = f * _per_eta(fmt)
    n = q.numerator // q.denominator
    return min(F.rdir(fmt, n, fmt.qmin, False), fmt.omega)


def _pos(fmt, rng, e, style="uniform"):
    return G.in_binade(fmt, rng, max(fmt.qmin, min(fmt.emax, e)), style)


def _common_limb(fmt, rng, stratum):
    return G2.limb(fmt, rng, stratum)


def _count(fmt, rng, stratum):
    """A count: 0, or a number of the format at least 1."""
    one = _one(fmt)
    e1 = fmt.binade(one)
    if stratum == "zero" or (stratum == "zeros" and rng.chance(3, 4)):
        return 0
    if stratum == "overflow" or stratum == "huge":
        return abs(G2._top(fmt, rng))
    if stratum == "underflow":
        return one if rng.bits(1) else max(one, min(fmt.omega, one * rng.between(1, 8)))
    if stratum == "pow2":
        return 1 << (rng.between(e1, fmt.emax) - fmt.qmin)
    if stratum == "integer" or rng.chance(1, 2):
        e = rng.between(0, max(0, min(fmt.p, fmt.emax - e1 + 1) - 1))
        v = rng.between(1 << e, (2 << e) - 1)
        while v > 1 and not F.is_member(fmt, v * one):
            v >>= 1
        return max(v, 1) * one
    return _pos(fmt, rng, rng.between(e1, fmt.emax))


def _at_most(fmt, rng, k, stratum):
    """A number of the format in [0, K]: K itself, 1, numbers below, zero."""
    one = _one(fmt)
    kk = k * one
    t = rng.below(5)
    if stratum in ("zero", "zeros") or t == 0:
        return 0
    if t == 1 and F.is_member(fmt, kk):
        return kk
    e1 = fmt.binade(one)
    lo = max(fmt.qmin, e1 - 3 * fmt.p) if stratum != "underflow" else fmt.qmin
    v = _pos(fmt, rng, rng.between(lo, e1 - 1 if e1 > fmt.qmin else e1))
    return min(v, kk) if F.is_member(fmt, min(v, kk)) else v if v <= kk else 0


def _pow2(fmt, rng):
    return 1 << (rng.between(fmt.qmin, fmt.emax) - fmt.qmin)


def _radius_operand(fmt, sh, rng, n, stratum):
    role = sh.roles[n]
    if role == "mask":
        return [rng.bits(1)]
    if role == "count":
        return [_count(fmt, rng, stratum)]
    if role == "atmost":
        return [_at_most(fmt, rng, sh.at_most[n], stratum)]
    if role == "pow2":
        return [_pow2(fmt, rng)]
    if stratum in COMMON:
        v = _common_limb(fmt, rng, stratum)
    elif stratum == "huge":
        v = G2._top(fmt, rng) if rng.chance(2, 3) else _pos(fmt, rng, rng.between(
            max(fmt.qmin, fmt.emax - fmt.p), fmt.emax))
    elif stratum == "zeros":
        v = 0 if rng.chance(3, 4) else _pos(fmt, rng, G2._e_any(fmt, rng))
    else:
        v = _pos(fmt, rng, G2._e_any(fmt, rng), "short" if rng.chance(1, 4) else "uniform")
    return [abs(v) if role == "radius" else rng.sign() * abs(v)]


def _radius(fmt, sh, rng, stratum):
    vals = {n: _radius_operand(fmt, sh, rng, n, stratum) for n in sh.names}
    limbs = [n for n in sh.names if sh.roles[n] in ("radius", "limb")]
    if stratum == "mixed" and limbs:
        # One operand far above the others (or the count large against small operands).
        big = limbs[rng.below(len(limbs))]
        e = rng.between(*G._mid(fmt, 2 * fmt.p, fmt.p + 4))
        for n in limbs:
            d = 0 if n == big else rng.between(fmt.p, 3 * fmt.p + 4)
            v = _pos(fmt, rng, e - d) if rng.chance(7, 8) else 0
            vals[n] = [v if sh.roles[n] == "radius" else rng.sign() * v]
    if stratum == "atnormal":
        pw = [n for n in sh.names if sh.roles[n] == "pow2"]
        rad = [n for n in sh.names if sh.roles[n] == "radius" and n != sh.names[0]]
        if pw and rad:
            # rx c = N exactly, or rx just below or just above N / c, or rx = 0.
            c, rx = pw[0], rad[0]
            k = rng.between(-fmt.p, fmt.p)
            ec = max(fmt.qmin, min(fmt.emax, k))
            cv = 1 << (ec - fmt.qmin)
            N = fmt.lam
            # rx = N / c (a number of the format when it is in range).
            target = Fraction(N) / (Fraction(cv) * format_eta(fmt))
            base = _fixed_down(fmt, target * format_eta(fmt)) if target > 0 else 0
            t = rng.below(4)
            if t == 0:
                r = 0
            elif t == 1:
                r = F.succ(fmt, base) if type(F.succ(fmt, base)) is int else base
            elif t == 2:
                r = F.pred(fmt, base) if base > 0 else base
            else:
                r = base
            vals[c] = [cv]
            vals[rx] = [max(0, r)]
    if sh.finite_results and stratum != "overflow" and (stratum != "huge" or rng.bits(1)):
        _within(fmt, sh, vals, 2 if stratum == "huge" else 8)
    return vals


def _within(fmt, sh, vals, k):
    """A radius kernel whose claim is of finite results (conv_radius, bvec.FINITE_RESULTS) claims
    nothing of a result that is not finite but that it is +inf or a NaN: a run of such results
    judges little, and the cross-checks' guards ask that finite results be the great majority.
    In every stratum but overflow (and half of huge, which keeps its overflows) the operands of
    the roles radius and limb are scaled down together until the stated value, with each input
    under at_most( ) at its bound and a count at least 1, is at most Omega/k: every product the
    value names is then below the range (Omega/8; Omega/2 in huge, near the top)."""
    tree = sh.kernel.ensures[0].cvalue
    if CX.calls(tree):
        return
    one = _one(fmt)
    eta = format_eta(fmt)
    lim = Fraction(fmt.omega) * eta / k
    ops = [n for n in sh.names if sh.roles[n] in ("radius", "limb")]

    def stated():
        names = {}
        for n in sh.names:
            v = vals[n][0]
            if sh.roles[n] == "atmost":
                v = sh.at_most[n] * one
            elif sh.roles[n] == "count":
                v = max(v, one)
            names[n] = abs(v) * eta
        env = {"u": Fraction(1, 1 << fmt.p), "eta": eta, "names": names}
        return CX.evaluate(tree, env)

    for _ in range(4 * (fmt.emax - fmt.qmin + 2)):
        v = stated()
        if v <= lim:
            break
        d = max(1, (int(v / lim)).bit_length() // 2)
        for n in ops:
            vals[n] = [vals[n][0] >> d if vals[n][0] >= 0 else -((-vals[n][0]) >> d)]
    for n in ops:
        while vals[n][0] and not F.is_member(fmt, vals[n][0]):
            vals[n] = [F.rdir(fmt, vals[n][0], fmt.qmin, vals[n][0] < 0)]


def format_eta(fmt):
    return Fraction(1, 1 << -fmt.qmin) if fmt.qmin < 0 else Fraction(1 << fmt.qmin)


# ---------------------------------------------------------------------------
# The accumulator

def _group(fmt, rng, k, stratum, e=None, mode=None):
    """A limb or a normalized pair of a common stratum, or near the binade e."""
    if e is None:
        return G2.expansion(fmt, rng, stratum) if k == 2 else [G2.limb(fmt, rng, stratum)]
    x0 = rng.sign() * _pos(fmt, rng, e, "short" if mode == "short" else "uniform")
    if k == 1:
        return [x0]
    return [x0, G.tail_for(fmt, rng, x0, "zero" if mode == "short" else
                           ("near", "any", "half+", "half-")[rng.below(4)])]


def _acc(fmt, sh, rng, stratum):
    vals = {}
    k = sh.k
    p = fmt.p
    # One binade for every operand of exactprod and tie, near which each is drawn (short
    # significands at nearby exponents: sums that are numbers of the format, and ties).
    e0 = rng.between(*G._mid(fmt, 2 * p + 2, 2 * p + 4))
    near = stratum in ("exactprod", "tie")
    for n in sh.names:
        role = sh.roles[n]
        if role == "radius":
            continue
        if stratum in COMMON:
            vals[n] = _group(fmt, rng, sh.limbs[n], stratum)
        else:
            e = e0 + rng.between(-2, 2) if near else rng.between(*G._mid(fmt, 2 * p + 2, 2 * p + 4))
            vals[n] = _group(fmt, rng, sh.limbs[n], "uniform", e, "short" if near else None)
    added = [n for n in sh.rest if sh.roles[n] != "radius"]
    mags = [n for n in sh.names if sh.roles[n] == "radius"]
    a = sh.a
    # The magnitude the sum of magnitudes adds: |x0| (|x0| |y0|) or c.
    if stratum in COMMON:
        for n in mags:
            vals[n] = [abs(G2.limb(fmt, rng, stratum))]
    elif stratum == "atop":
        for n in mags:
            vals[n] = [abs(G2._top(fmt, rng))]
        if added and rng.bits(1):
            # What is added in the top binades too (the sum of magnitudes beyond Omega).
            x = added[0]
            vals[x] = _group(fmt, rng, sh.limbs[x], "overflow")
    else:
        for n in mags:
            e = e0 + rng.between(-2, 2) if near else rng.between(*G._mid(fmt, 2 * p + 2, 2 * p + 4))
            vals[n] = [_pos(fmt, rng, e, "short" if stratum in ("exactprod", "tie") else "uniform")]
    if stratum == "cancel" and added:
        # x (the first thing added) within a few units of -s.
        x = added[0]
        if sh.limbs[x] == sh.k and len(added) == 1:
            s = vals[sh.s]
            t = [-v for v in s]
            if t[0] and rng.bits(1):
                j = sh.k - 1
                nb = F.succ(fmt, t[j]) if rng.bits(1) else F.pred(fmt, t[j])
                if type(nb) is int:
                    t2 = list(t)
                    t2[j] = nb
                    if sh.k == 1 or F.normalized_limbs(fmt, t2):
                        t = t2
            vals[x] = t
    if stratum == "apart" and mags:
        # a far above or far below what is added.
        d = rng.between(p + 2, 3 * p + 4) * (1 if rng.bits(1) else -1)
        ref = max((abs(vals[n][0]) for n in added), default=0)
        e = (fmt.binade(ref) if ref else rng.between(*G._mid(fmt, 2 * p, 2 * p))) + d
        vals[mags[0]] = [_pos(fmt, rng, e)]
    if stratum == "tie" and mags and added:
        # |x0| (or the product of the leading limbs, or c) an odd multiple of half a unit of a.
        av = vals[a][0]
        if av:
            u0 = F.ulp(fmt, av)
            if u0 > 1:
                h = (u0 // 2) * (2 * rng.below(3) + 1)
                if len(added) == 1 and sh.roles.get(added[0]) != "radius" and F.is_member(fmt, h):
                    x = added[0]
                    vals[x] = [rng.sign() * h] + [0] * (sh.limbs[x] - 1)
                elif len(mags) == 2 and F.is_member(fmt, h):
                    vals[mags[1]] = [h]
    for n in sh.names:
        if n not in vals:
            vals[n] = [0] * sh.limbs[n]
    return vals


# ---------------------------------------------------------------------------
# The radius of an accumulator

def _accradius(fmt, sh, rng, stratum):
    names = sh.names
    a, m, g, t = names
    one = _one(fmt)
    u = Fraction(1, 1 << fmt.p)
    eta = format_eta(fmt)
    per = _per_eta(fmt)
    vals = {}
    if stratum in COMMON:
        vals[m] = [_count(fmt, rng, stratum)]
        for n in (a, g, t):
            vals[n] = [abs(G2.limb(fmt, rng, stratum))]
    else:
        if stratum == "integer":
            vals[m] = [_count(fmt, rng, "integer")]
        else:
            # m u around 1/2 (limit), or above (beyond): m = x / u.
            if stratum == "limit":
                x = Fraction(1, 2) * (1 + Fraction(rng.between(-64, 64), 256))
            elif stratum == "beyond":
                x = Fraction(1, 2) * (2 ** rng.between(1, max(1, fmt.p)))
            else:
                x = Fraction(rng.between(1, 1 << 10), 1 << 12)
            mv = _fixed_down(fmt, x / u)
            vals[m] = [max(mv, one) if mv else one]
        mval = vals[m][0] * eta
        # g and t of the size of the bound of dot for m terms (g about m u), a anywhere.
        gv = mval * u * (1 + Fraction(rng.below(8), 8))
        vals[g] = [_fixed_down(fmt, gv) if gv * per >= 1 else 0]
        tv = mval * eta * (1 + rng.below(4))
        vals[t] = [_fixed_down(fmt, tv) if tv * per >= 1 else 0]
        if stratum == "abig":
            vals[a] = [_pos(fmt, rng, rng.between(max(fmt.qmin, fmt.emax - fmt.p), fmt.emax - 4))]
        else:
            vals[a] = [_pos(fmt, rng, G2._e_any(fmt, rng))]
    # The stated value below Omega/8, so that a radius exists where the mask is true: a, g and t
    # (and then m) scaled down by the excess.
    for _ in range(16):
        v = _accradius_value(fmt, vals, names) * per
        lim = fmt.omega >> 3
        if v <= lim:
            break
        d = (int(v) // lim).bit_length() + 1
        for n in (a, g, t):
            vals[n] = [vals[n][0] >> d]
        if _accradius_value(fmt, vals, names) * per > lim and vals[m][0] > one:
            vals[m] = [max(one, vals[m][0] >> d)]
    for n in (a, g, t):
        while vals[n][0] and not F.is_member(fmt, vals[n][0]):
            vals[n] = [F.rdir(fmt, vals[n][0], fmt.qmin, False)]
    if vals[m][0] and not F.is_member(fmt, vals[m][0]):
        vals[m] = [max(one, F.rdir(fmt, vals[m][0], fmt.qmin, False))]
    return vals


def _accradius_value(fmt, vals, names):
    a, m, g, t = names
    eta = format_eta(fmt)
    u = Fraction(1, 1 << fmt.p)
    A, M, Gv, T = (vals[n][0] * eta for n in (a, m, g, t))
    return Gv * (1 + u) ** 2 * (1 + M * u + 2 * M * M * u * u) * (A + M * eta / 2) + T


# ---------------------------------------------------------------------------
# The finishes of the ball vectors (the extended domain)

def _bvfinish(fmt, sh, rng, stratum):
    vals = {}
    v = sh.names[0]
    for n in sh.names[1:]:
        vals[n] = [rng.bits(1) if stratum != "masks" else rng.bits(1)]
    if stratum in COMMON:
        x = G2.limb(fmt, rng, stratum)
    elif stratum == "nonfinite":
        x = (INF, NINF, NAN)[rng.below(3)]
    elif stratum == "negative":
        k = rng.below(4)
        x = -(1 if k == 0 else fmt.lam if k == 1 else fmt.omega if k == 2 else
              _pos(fmt, rng, G2._e_any(fmt, rng)))
    elif stratum == "zeros":
        x = 0
    elif stratum == "top":
        x = fmt.omega if rng.bits(1) else F.pred(fmt, fmt.omega)
    else:                                           # masks
        x = _pos(fmt, rng, G2._e_any(fmt, rng))
        for n in sh.names[1:]:
            vals[n] = [1 if rng.chance(2, 3) else 0]
    if stratum not in ("masks",) and rng.chance(1, 2):
        for n in sh.names[1:]:
            vals[n] = [1]
    vals[v] = [x]
    return vals


# ---------------------------------------------------------------------------

def make_case(fmt, sh, rng, stratum):
    if sh.family == "radius":
        vals = _radius(fmt, sh, rng, stratum)
    elif sh.family == "acc":
        vals = _acc(fmt, sh, rng, stratum)
    elif sh.family == "accradius":
        vals = _accradius(fmt, sh, rng, stratum)
    else:
        vals = _bvfinish(fmt, sh, rng, stratum)
    negz = set()
    for n, limbs in vals.items():
        if sh.roles[n] == "mask":
            continue
        for i, v in enumerate(limbs):
            if v == 0 and rng.bits(1):
                negz.add((n, i))
    return vals, negz


def valid8(fmt, kernel, vals):
    """The requirements of the kernel, written from the definitions (the checker has its own): in
    the finite domain every limb a number of the format, nonneg, count, power_of_two, normalized
    and at_most; in the extended domain (the finishes) any value of the format."""
    limbs = dict(kernel.inputs)
    for name, vs in vals.items():
        if name in kernel.masks:
            if vs not in ([0], [1]):
                return False
            continue
        if len(vs) != limbs[name]:
            return False
        for v in vs:
            if type(v) is int:
                if not F.is_member(fmt, v):
                    return False
            elif not kernel.extended or v not in (INF, NINF, NAN):
                return False
    one = _one(fmt)
    q = fmt.qmin
    for r in kernel.requires:
        g = vals[r[1]]
        v = sum(g) if all(type(t) is int for t in g) else None
        if r[0] == "normalized":
            if v is None or not F.normalized_limbs(fmt, g):
                return False
        elif r[0] == "nonneg":
            if v is not None and v < 0:
                return False
        elif r[0] == "count":
            if v is None or (v != 0 and v < one):
                return False
        elif r[0] == "power_of_two":
            if v is None or v <= 0 or v & (v - 1):
                return False
        elif r[0] == "at_most":
            if v is None or v < 0 or ((v << q) > r[2] if q >= 0 else v > (r[2] << -q)):
                return False
        else:
            return False
    return True
