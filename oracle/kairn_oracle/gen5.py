"""Random operands for the kernels of the folds' stage of Milestone 2 (milestone2.md, "Batch
kernels"; architecture.md, "Claims of Milestone 2"), chosen from claims that no earlier kernel
has, before the families of the earlier waves:

    count    a count() input (the bounds bound_sum_k and bound_dot_k): the count m
    dotstep  a value NAME + NAME * NAME (the steps of the dot products, dot_step_1, dot_step_2)
    finish   a finite_or_nan entry (the finishes fold_finish_k), in the extended domain: the state
             of a fold, any limbs

The steps of the sums of supplied arrays (sum_entry_step_k, sum_fast_entry_step_2) claim what
add_1_1, add_2_2 and add_fast_2_2 claim, and keep the families those kernels have.  Each family
has the strata every family has (uniform, underflow, overflow, zero, pow2, extreme), read for its
shape, and strata of its own, which come round two or three times per cycle:

    count    integer   integers from 1 to 2^p, log-uniform: the counts of real arrays
             fraction  counts that are not integers, which count() allows (m = 0 or m >= 1)
             limit     m around the limit of the listing, m * unit(K) from 1/16 to 1, log-uniform,
                       and the numbers next to m * unit(K) = 1/5, 1/4, 1/2 and 1
             beyond    m * unit(K) from 1 to the largest count of the format
    dotstep  cancel    s within a few units of -(x y) rounded to the format: the state cancels
             state     |s| far above or below |x y|: a long sum and one more term
             zerostate s = 0, the first step of a fold
             tie       x y exact and s at an odd multiple of half its unit: s + x y a tie
             exactprod short significands: x y a number of the format
    finish   nonfinite the leading limb infinite or a NaN, with any lower limb
             tails     a finite leading limb with a lower limb that is not finite, or with a
                       finite lower limb that does not normalize it (the state is passed on as it
                       is)

`count` takes unit(K) of the kernel K that the bound is for from the claims (the kernel's entries
name it), so that the limit is placed in every format.  Every case is checked against the
requirements before it is written (valid5), and the selftest checks that no stratum produces an
invalid case.
"""

from fractions import Fraction

from . import cexpr as CX
from . import fmt as F
from . import gen as G
from . import gen2 as G2

INF, NINF, NAN = F.POS_INF, F.NEG_INF, F.NAN
COMMON = G2.COMMON
FAMILY_STRATA = {
    "count": COMMON + ("integer", "fraction", "limit", "beyond"),
    "dotstep": COMMON + ("cancel", "state", "zerostate", "tie", "exactprod"),
    "finish": COMMON + ("nonfinite", "tails"),
}
FAMILY_SCHEDULE = {
    "count": ("uniform", "integer", "limit", "fraction", "integer", "limit", "beyond", "underflow",
              "limit", "overflow", "zero", "pow2", "extreme", "integer"),
    "dotstep": ("uniform", "cancel", "state", "zerostate", "cancel", "tie", "exactprod",
                "underflow", "cancel", "state", "overflow", "pow2", "extreme", "zero"),
    "finish": ("uniform", "nonfinite", "tails", "nonfinite", "underflow", "tails", "overflow",
               "nonfinite", "zero", "pow2", "extreme"),
}
FAMILIES = tuple(FAMILY_STRATA)


def family_of(kernel):
    """The family of a kernel of the folds' stage, or None."""
    if any(r[0] == "count" for r in kernel.requires):
        return "count"
    if any(e.kind == "finite_or_nan" for e in kernel.ensures):
        return "finish"
    t = kernel.value_tree
    if t is not None and t[0] == "+":
        a, b = t[1], t[2]
        if b[0] == "*" and a[0] == "name" and b[1][0] == "name" and b[2][0] == "name":
            names = [a[1], b[1][1], b[2][1]]
            limbs = {kernel.limbs_of(n) for n in names}
            if len(set(names)) == 3 and len(limbs) == 1 and not set(names) & kernel.masks:
                return "dotstep"
    return None


class Shape5:
    def __init__(self, kernel):
        self.kernel = kernel
        self.family = family_of(kernel)
        if self.family is None:
            raise G.GenError("%s: not a kernel of the folds' stage" % kernel.name)
        self.names = [n for n, _ in kernel.inputs]
        self.limbs = dict(kernel.inputs)
        self.roles = {n: "mask" if n in kernel.masks else "limb" for n in self.names}
        self.strata = FAMILY_STRATA[self.family]
        self.schedule = FAMILY_SCHEDULE[self.family]
        if self.family == "count":
            self.m = next(r[1] for r in kernel.requires if r[0] == "count")
            calls = sorted({kn for e in kernel.ensures
                            for t in ([e.cvalue] if e.cvalue is not None else [])
                            + list(getattr(e, "cargs", [])) for _f, kn in CX.calls(t)})
            self.unit_kernel = calls[0] if len(calls) == 1 else None
            self.roles[self.m] = "count"
        elif self.family == "dotstep":
            t = kernel.value_tree
            self.s, self.x, self.y = t[1][1], t[2][1][1], t[2][2][1]
            self.k = self.limbs[self.s]
            for n in (self.s, self.x, self.y):
                if self.k == 2 and ("normalized", n) not in kernel.requires:
                    raise G.GenError("%s: a 2-limb input without normalized() is not generated"
                                     % kernel.name)
        else:
            e = next(e for e in kernel.ensures if e.kind == "finite_or_nan")
            self.state = e.operand
            self.k = self.limbs[self.state]
        self._limits = {}

    def unit(self, fmt):
        """unit(K) of the kernel the bound is for, in a format (a Fraction), or None."""
        if self.unit_kernel is None or not hasattr(self.kernel, "claims_ref"):
            return None
        u = self._limits.get(fmt.triple)
        if u is None:
            u = self._limits[fmt.triple] = self.kernel.claims_ref.unit_tiny(self.unit_kernel,
                                                                            fmt)[0]
        return u


# ---------------------------------------------------------------------------
# count

def _one(fmt):
    return (1 << -fmt.qmin) if fmt.qmin < 0 else 1


def _round_fixed(fmt, r, up=False):
    """A positive rational r rounded to the format, down or up, as a fixed value; None when the
    result is below 1 or beyond Omega."""
    num, den = r.numerator, r.denominator
    if fmt.qmin < 0:
        num <<= -fmt.qmin
    else:
        den <<= fmt.qmin
    v = -(-num // den) if up else num // den
    if v <= 0:
        return None
    w = F.rdir(fmt, v, fmt.qmin, up)
    if w > fmt.omega:
        return None
    return w if w >= _one(fmt) else None


def _count(fmt, sh, rng, stratum):
    one = _one(fmt)
    top = fmt.omega
    emax = fmt.emax
    e1 = fmt.binade(one)            # the exponent of 1
    unit = sh.unit(fmt)
    if stratum == "zero":
        return 0
    if stratum == "underflow":
        k = rng.below(5)
        if k == 0:
            return one
        if k == 1:
            n = F.succ(fmt, one)
            return n if type(n) is int else one
        if k == 2:
            return min(top, one * rng.between(1, 16)) if F.is_member(fmt, one * 2) else one
        v = one * rng.between(1, 16)
        while not F.is_member(fmt, v):
            v >>= 1
        return max(v, one)
    if stratum == "overflow":
        return abs(G2._top(fmt, rng))
    if stratum == "pow2":
        return 1 << (rng.between(e1, emax) - fmt.qmin)
    if stratum == "uniform":
        return G.in_binade(fmt, rng, rng.between(e1, emax))
    if stratum == "integer":
        # An integer from 1 to 2^p (or the largest the format holds), log-uniform.
        e = rng.between(0, min(fmt.p, emax - e1 + 1) - 1) if emax >= e1 else 0
        v = rng.between(1 << e, (2 << e) - 1)
        while v > 1 and not F.is_member(fmt, v * one):
            v >>= 1
        return max(v, 1) * one
    if stratum == "fraction":
        # Not an integer: a binade from 1 up to 2^(p-2), with a fractional part.
        for _ in range(8):
            e = rng.between(e1, max(e1, min(emax, e1 + fmt.p - 2)))
            v = G.in_binade(fmt, rng, e)
            if v % one:
                return v
        n = F.succ(fmt, one)
        return n if type(n) is int else one
    if unit is None or unit <= 0:
        return G.in_binade(fmt, rng, rng.between(e1, emax))
    if stratum == "extreme" or (stratum == "limit" and rng.bits(1)):
        # The numbers next to m * unit = 1/5, 1/4, 1/2, 1: rounded down or up, a step or two
        # either way.
        lim = (Fraction(1, 5), Fraction(1, 4), Fraction(1, 2), Fraction(1))[rng.below(4)]
        v = _round_fixed(fmt, lim / unit, rng.bits(1))
        if v is None:
            return top if rng.bits(1) else one
        for _ in range(rng.below(3)):
            n = F.succ(fmt, v) if rng.bits(1) else F.pred(fmt, v)
            v = n if type(n) is int and n >= one else v
        return v
    if stratum == "limit":
        # m * unit from 1/16 to 1, log-uniform in the exponent.
        target = Fraction(1, 16) * Fraction(2) ** rng.between(0, 4) * Fraction(
            rng.between(1 << 20, 2 << 20), 1 << 20)
        v = _round_fixed(fmt, target / unit, rng.bits(1))
        return v if v is not None else top
    # beyond: m * unit from 1 to the largest count.
    lo = _round_fixed(fmt, 1 / unit, True)
    if lo is None:
        return top
    e = rng.between(fmt.binade(lo), emax)
    v = G.in_binade(fmt, rng, e)
    return max(v, lo)


# ---------------------------------------------------------------------------
# dotstep

def _expansion_near(fmt, rng, v, k):
    """The k-limb number nearest to the rational v (in units of eta), normalized: (RN(v)) for
    one limb; (z0, RN(v - z0)) renormalized for two."""
    z0 = _rn_frac(fmt, v)
    if type(z0) is not int:
        return None
    if k == 1:
        return [z0]
    rest = v - z0
    z1 = _rn_frac(fmt, rest) if rest else 0
    if type(z1) is not int:
        return None
    s = F.rn_fixed(fmt, z0 + z1)
    if type(s) is not int:
        return None
    t = z0 + z1 - s
    return [s, t] if F.is_member(fmt, t) and F.normalized_limbs(fmt, [s, t]) else None


def _rn_frac(fmt, v):
    """RN of a rational v given in units of eta."""
    num, den = v.numerator, v.denominator
    sh = den.bit_length() + 2 * fmt.p + 4
    q = (num << sh) // den
    # q / 2^sh <= v < (q + 1) / 2^sh: a sticky bit decides the ties that are not exact.
    if q * den != num << sh:
        q = 2 * q + 1
        sh += 1
    return F.rn(fmt, q, fmt.qmin - sh)


def _operand(fmt, rng, k, e, mode="near"):
    x0 = G2._limb(fmt, rng, max(fmt.qmin, min(fmt.emax, e)))
    return [x0] if k == 1 else [x0, G.tail_for(fmt, rng, x0, mode)]


def _value(vs):
    return sum(vs)


def _dotstep(fmt, sh, rng, stratum):
    k = sh.k
    s, x, y = sh.s, sh.x, sh.y
    p = fmt.p
    if stratum in COMMON:
        vals = {n: G2.operand(fmt, rng, sh_view(sh), n, stratum) if k == 1 else
                G2.expansion(fmt, rng, stratum) for n in (s, x, y)}
        if stratum in ("underflow", "overflow") and rng.bits(1):
            # The product, rather than its factors, at the corner of the stratum.
            et = (rng.between(fmt.qmin - p - 1, fmt.emin_normal + 2 * p + 2) if stratum == "underflow"
                  else rng.between(fmt.emax - 2, fmt.emax + 1))
            ea, eb = G._split_exponent(fmt, rng, et)
            vals[x] = _operand(fmt, rng, k, ea)
            vals[y] = _operand(fmt, rng, k, eb)
            if stratum == "overflow" and rng.bits(1):
                vals[s] = [G2._top(fmt, rng)] + ([0] if k == 2 else [])
        return vals
    lo, hi = G._mid(fmt, (k + 1) * p + 2, 2)
    ea, eb = G._split_exponent(fmt, rng, rng.between(lo, hi))
    style = "short" if stratum in ("tie", "exactprod") else "uniform"
    if stratum in ("tie", "exactprod"):
        x0 = rng.sign() * G.in_binade(fmt, rng, ea, "short")
        y0 = rng.sign() * G.in_binade(fmt, rng, eb, "short")
        vals = {x: [x0] + ([0] if k == 2 else []), y: [y0] + ([0] if k == 2 else [])}
    else:
        vals = {x: _operand(fmt, rng, k, ea), y: _operand(fmt, rng, k, eb)}
    P = _value(vals[x]) * _value(vals[y])          # the exact product, at scale 2 qmin
    Pq = Fraction(P, 1 << -fmt.qmin) if fmt.qmin < 0 else Fraction(P << fmt.qmin)
    if stratum == "zerostate":
        vals[s] = [0] * k
    elif stratum == "cancel":
        t = _expansion_near(fmt, rng, -Pq, k)
        if t is None:
            t = [0] * k
        else:
            for _ in range(rng.below(4)):
                j = (k - 1) if rng.bits(1) else 0
                nb = F.succ(fmt, t[j]) if rng.bits(1) else F.pred(fmt, t[j])
                if type(nb) is int:
                    t2 = list(t)
                    t2[j] = nb
                    if k == 1 or F.normalized_limbs(fmt, t2):
                        t = t2
        vals[s] = t
    elif stratum == "state":
        d = rng.between(p + 1, 2 * k * p + 4) * (1 if rng.bits(1) else -1)
        vals[s] = _operand(fmt, rng, k, ea + eb + d)
    elif stratum == "tie":
        # s an odd multiple of half the unit of x y's binade: s + x y a tie (when exact).
        if P:
            r = _rn_frac(fmt, Pq)
            u0 = F.ulp(fmt, r) if type(r) is int and r else 1
            v = rng.sign() * (2 * rng.below(4) + 1) * u0
            v = v // 2 if u0 > 1 else v
            vals[s] = [v if F.is_member(fmt, v) else rng.sign() * u0] + ([0] if k == 2 else [])
        else:
            vals[s] = _operand(fmt, rng, k, ea)
    else:
        es = ea + eb + rng.between(-p, p)
        vals[s] = [rng.sign() * G.in_binade(fmt, rng, max(fmt.qmin, min(fmt.emax, es)), "short")]
        if k == 2:
            vals[s].append(0)
    return vals


class _View:
    """A Shape2 stand-in for G2.operand: the roles of the inputs."""

    def __init__(self, roles):
        self.roles = roles


def sh_view(sh):
    return _View(sh.roles)


# ---------------------------------------------------------------------------
# finish

def _finish(fmt, sh, rng, stratum):
    k = sh.k
    if stratum in COMMON:
        if k == 1:
            return {sh.state: [G2.limb(fmt, rng, stratum)]}
        return {sh.state: G2.expansion(fmt, rng, stratum)}
    NF = (INF, NINF, NAN)
    if stratum == "nonfinite":
        v = [NF[rng.below(3)]]
        for _ in range(k - 1):
            j = rng.below(4)
            v.append(NF[j] if j < 3 else (0 if rng.bits(1) else G2.limb(fmt, rng, "uniform")))
        return {sh.state: v}
    # tails
    x0 = G2.limb(fmt, rng, "uniform")
    if k == 1:
        return {sh.state: [x0]}
    if rng.bits(1):
        return {sh.state: [x0, NF[rng.below(3)]]}
    # A finite pair that is not normalized: the second limb above half an ulp of the first.
    u0 = F.ulp(fmt, x0) if x0 else 1
    t = rng.sign() * u0 * rng.between(1, 3)
    if not F.is_member(fmt, t):
        t = rng.sign() * u0
    return {sh.state: [x0, t if F.is_member(fmt, t) else 0]}


# ---------------------------------------------------------------------------

def make_case(fmt, sh, rng, stratum):
    if sh.family == "count":
        vals = {sh.m: [_count(fmt, sh, rng, stratum)]}
    elif sh.family == "dotstep":
        vals = _dotstep(fmt, sh, rng, stratum)
    else:
        vals = _finish(fmt, sh, rng, stratum)
    for n in sh.names:
        if n not in vals:
            vals[n] = [rng.bits(1)] if sh.roles[n] == "mask" else [0] * sh.limbs[n]
    negz = set()
    for n, limbs in vals.items():
        if sh.roles[n] == "mask":
            continue
        for i, v in enumerate(limbs):
            if v == 0 and rng.bits(1):
                negz.add((n, i))
    return vals, negz


def valid5(fmt, kernel, vals):
    """The requirements of the kernel, written from the definitions (the checker has its own);
    a one-limb input with no requirement in the extended domain, or a multi-limb one of a kernel
    of finite_or_nan, is any value."""
    if any(not format_ok(fmt, r) for r in kernel.format_requires):
        return False
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
    for r in kernel.requires:
        g = vals[r[1]]
        if r[0] == "normalized":
            if not F.normalized_limbs(fmt, g):
                return False
        elif r[0] == "count":
            v = sum(g)
            if v != 0 and v < one:
                return False
        elif r[0] == "canonical":
            from .gen3 import _canonical
            if not _canonical(fmt, g):
                return False
        else:
            return False
    return True


def format_ok(fmt, prop):
    return prop != "half" or fmt.qmin <= -1
