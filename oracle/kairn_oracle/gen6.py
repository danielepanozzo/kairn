"""Random operands for the kernels of the maps and the folds of maxima (architecture.md, "Maps" and
"Folds of maxima"; milestone2.md, "sum, dot, axpy, convolution"), chosen from claims that no
earlier kernel has, before the families of the earlier waves:

    axpy     a value NAME * NAME + NAME, of any limbs (the steps of axpy, axpy_step_k and their
             entry forms): the product of the scalar and an element, then the sum
    maxof    a `maximum` entry (norm_combine and the steps of the folds of maxima, norm_step_k):
             the larger of two exact values

The other steps of the maps (add_entry_step_k, sub_1_1, sub_entry_step_k, scale_step_k,
mul_pow2_step_k) claim what add_1_1, add_2_2, sub_2_2, mul_1_1, mul_2_1 and mul_pow2_2 claim, and
keep the families those kernels have (gen2.py's scale family has a branch of its own for a one-limb
operand beside the power of two).  Each family has the strata every family has (uniform,
underflow, overflow, zero, pow2, extreme), read for its shape, and strata of its own, which come
round two or three times per cycle:

    axpy     cancel    y within a few units of -(a x) rounded to y's limbs: the sum cancels
             state     |y| far above or below |a x|
             tie       a x exact (short significands) and y an odd multiple of half the unit of a
                       x's binade: the sum a tie
             exactprod short significands everywhere: a x and the sum numbers of the format
             tight     the closest to the bound of form T: for one limb, a = 1 + 2uk, x =
                       1 - (2k - 1)u, y = (4j + 1)u (scaled, of one sign): a x is just below a
                       midpoint and rounds down, and the sum is a tie that rounds down too, so
                       both roundings lose about u in the same direction (2u of the 2u that the
                       bound allows); for two limbs, the literature's tight case of the product
                       (MR22's of mul_2_2, JMP17's of mul_2_1; tight.py) with y = 0 or tiny
    maxof    equal     the two arguments of the same value (zeros of both signs among them)
             neighbor  one argument the number next to the other, above or below
             negative  arguments of both signs (a state below zero, an element of either sign)

Every case is checked against the requirements before it is written (gen.valid), and the
selftest checks that no stratum produces an invalid case.
"""

from fractions import Fraction

from . import fmt as F
from . import gen as G
from . import gen2 as G2
from . import gen5 as G5
from . import tight as TI

COMMON = G2.COMMON
FAMILY_STRATA = {
    "axpy": COMMON + ("cancel", "state", "tie", "exactprod", "tight"),
    "maxof": COMMON + ("equal", "neighbor", "negative"),
}
FAMILY_SCHEDULE = {
    "axpy": ("uniform", "cancel", "tight", "state", "cancel", "tie", "exactprod", "tight",
             "underflow", "cancel", "state", "overflow", "tight", "pow2", "extreme", "zero"),
    "maxof": ("uniform", "equal", "neighbor", "negative", "equal", "underflow", "neighbor",
              "overflow", "zero", "pow2", "extreme"),
}
FAMILIES = tuple(FAMILY_STRATA)


def axpy_names(kernel):
    """(a, x, y) of a value a * x + y over three distinct inputs, or None."""
    t = kernel.value_tree
    if t is None or t[0] != "+":
        return None
    p, y = t[1], t[2]
    if p[0] != "*" or y[0] != "name" or p[1][0] != "name" or p[2][0] != "name":
        return None
    names = (p[1][1], p[2][1], y[1])
    if len(set(names)) != 3 or set(names) & kernel.masks:
        return None
    return names


def family_of(kernel):
    """The family of a kernel of the maps or the folds of maxima, or None."""
    if getattr(kernel, "extended", False):
        return None
    if any(e.kind == "maximum" for e in kernel.ensures):
        return "maxof"
    if axpy_names(kernel) is not None:
        return "axpy"
    return None


class Shape6:
    def __init__(self, kernel):
        self.kernel = kernel
        self.family = family_of(kernel)
        if self.family is None:
            raise G.GenError("%s: not a kernel of the maps or the folds of maxima" % kernel.name)
        self.names = [n for n, _ in kernel.inputs]
        self.limbs = dict(kernel.inputs)
        self.roles = {}
        for n, l in kernel.inputs:
            if n in kernel.masks:
                self.roles[n] = "mask"
            elif l == 2:
                if ("normalized", n) not in kernel.requires:
                    raise G.GenError("%s: a 2-limb input without normalized() is not generated"
                                     % kernel.name)
                self.roles[n] = "x2"
            elif l > 2:
                raise G.GenError("%s: inputs of more than two limbs are not generated" % kernel.name)
            else:
                self.roles[n] = "limb"
        self.strata = FAMILY_STRATA[self.family]
        self.schedule = FAMILY_SCHEDULE[self.family]
        if self.family == "axpy":
            self.a, self.x, self.y = axpy_names(kernel)
        else:
            e = next(e for e in kernel.ensures if e.kind == "maximum")
            self.args = e.margs


# ---------------------------------------------------------------------------
# axpy

def _value(fmt, vs):
    """The exact value of fixed limbs, as a Fraction (not in units of eta)."""
    s = sum(vs)
    return Fraction(s, 1 << -fmt.qmin) if fmt.qmin < 0 else Fraction(s << fmt.qmin)


def _per_eta(fmt):
    return Fraction(1 << -fmt.qmin) if fmt.qmin < 0 else Fraction(1, 1 << fmt.qmin)


def _common(fmt, sh, rng, n, stratum):
    if sh.roles[n] == "x2":
        return G2.expansion(fmt, rng, stratum)
    return [G2.limb(fmt, rng, stratum)]


def _operand(fmt, rng, k, e, mode="near", style="uniform"):
    x0 = rng.sign() * G.in_binade(fmt, rng, max(fmt.qmin, min(fmt.emax, e)), style)
    return [x0] if k == 1 else [x0, G.tail_for(fmt, rng, x0, mode)]


def _scaled_exact(fmt, v, e):
    """The rational v * 2^e as a fixed value when it is a number of the format, else None."""
    w = v * _per_eta(fmt) * (Fraction(2) ** e)
    if w.denominator != 1 or not F.is_member(fmt, int(w)):
        return None
    return int(w)


def _tight1(fmt, rng):
    """One limb: a = 1 + 2uk, x = 1 - (2k - 1)u, y = (4j + 1)u, scaled by 2^ea, 2^ex and
    2^(ea + ex), with one sign for a x and y.  a x = 1 + u - 2u^2 k (2k - 1) rounds down to 1, and
    1 + (4j + 1)u is a tie that rounds down to the even 1 + 4ju: both roundings lose about u."""
    p = fmt.p
    if p < 2:
        return None
    u = Fraction(1, 1 << p)
    kmax = min(4, 1 << max(p - 2, 0))
    k = 1 + rng.below(kmax)
    j = rng.below(min(3, 1 << max(p - 3, 0))) if rng.chance(3, 4) else 0
    lo, hi = G._mid(fmt, 2 * p + 4, 4)
    for _ in range(8):
        ea = rng.between(lo, hi) // 2 if rng.bits(1) else rng.between(-p, p)
        E = rng.between(lo, hi)
        ex = E - ea
        a = _scaled_exact(fmt, 1 + 2 * u * k, ea)
        x = _scaled_exact(fmt, 1 - (2 * k - 1) * u, ex)
        y = _scaled_exact(fmt, (4 * j + 1) * u, E)
        if a is None or x is None or y is None:
            continue
        # a x and y of the sign s; a of either sign.
        s, sa = rng.sign(), rng.sign()
        return [sa * a], [sa * s * x], [s * y]
    return None


def _tight2(fmt, rng, sh, k):
    """Two limbs: the literature's tight case of the product, scaled into the format, with y = 0
    or tiny; None when there is none for this precision or none fits."""
    ka, kx = sh.limbs[sh.a], sh.limbs[sh.x]
    if ka == 2 and kx == 2:
        alg, kn = "dw*dw", "mul_2_2"
    elif ka == 1 and kx == 2:
        alg, kn = "dw*fp", "mul_2_1"
    else:
        return None
    from . import genfold as GF
    lit = GF._literature(fmt, rng, (kn,))
    if lit is None:
        return None
    # The paper's (x, y) is (the two-limb factor, the other): a is the other for mul_2_1.
    f0, f1 = lit
    if alg == "dw*fp":
        a, x = f1, f0
    else:
        a, x = (f0, f1) if rng.bits(1) else (f1, f0)
    a = [rng.sign() * v for v in a]
    x = [rng.sign() * v for v in x]
    if rng.chance(1, 3) and x[0] and a[0]:
        # A tiny y of the product's sign, far below its last limb: the sum loses nothing more.
        e = fmt.binade(x[0]) + fmt.binade(a[0]) - fmt.qmin - 3 * fmt.p
        if e >= fmt.qmin:
            s = 1 if (x[0] > 0) == (a[0] > 0) else -1
            y = [s * G.in_binade(fmt, rng, e)] + [0] * (k - 1)
            return a, x, y
    return a, x, [0] * k


def _axpy(fmt, sh, rng, stratum):
    a, x, y = sh.a, sh.x, sh.y
    ka, kx, ky = sh.limbs[a], sh.limbs[x], sh.limbs[y]
    kk = max(ka, kx, ky)
    p = fmt.p
    if stratum in COMMON:
        vals = {n: _common(fmt, sh, rng, n, stratum) for n in (a, x, y)}
        if stratum in ("underflow", "overflow") and rng.bits(1):
            # The product, rather than its factors, at the corner of the stratum.
            et = (rng.between(fmt.qmin - p - 1, fmt.emin_normal + 2 * p + 2) if stratum == "underflow"
                  else rng.between(fmt.emax - 2, fmt.emax + 1))
            ea, ex = G._split_exponent(fmt, rng, et)
            vals[a] = _operand(fmt, rng, ka, ea)
            vals[x] = _operand(fmt, rng, kx, ex)
            if stratum == "overflow" and rng.bits(1):
                vals[y] = [G2._top(fmt, rng)] + [0] * (ky - 1)
        return vals
    if stratum == "tight":
        got = _tight1(fmt, rng) if kk == 1 else _tight2(fmt, rng, sh, ky)
        if got is not None:
            return {a: got[0], x: got[1], y: got[2]}
        stratum = "state"
    lo, hi = G._mid(fmt, (kk + 1) * p + 2, 2)
    ea, ex = G._split_exponent(fmt, rng, rng.between(lo, hi))
    if stratum in ("tie", "exactprod"):
        vals = {a: _operand(fmt, rng, ka, ea, "zero", "short"),
                x: _operand(fmt, rng, kx, ex, "zero", "short")}
    else:
        vals = {a: _operand(fmt, rng, ka, ea), x: _operand(fmt, rng, kx, ex)}
    P = _value(fmt, vals[a]) * _value(fmt, vals[x])
    Pq = P * _per_eta(fmt)                         # in units of eta
    if stratum == "cancel":
        t = G5._expansion_near(fmt, rng, -Pq, ky)
        if t is None:
            t = [0] * ky
        else:
            for _ in range(rng.below(4)):
                j = (ky - 1) if rng.bits(1) else 0
                nb = F.succ(fmt, t[j]) if rng.bits(1) else F.pred(fmt, t[j])
                if type(nb) is int:
                    t2 = list(t)
                    t2[j] = nb
                    if ky == 1 or F.normalized_limbs(fmt, t2):
                        t = t2
        vals[y] = t
    elif stratum == "state":
        d = rng.between(p + 1, 2 * kk * p + 4) * (1 if rng.bits(1) else -1)
        vals[y] = _operand(fmt, rng, ky, ea + ex + d)
    elif stratum == "tie":
        # y an odd multiple of half the unit of the rounded product: a x + y a tie (exact).
        if P:
            r = G5._rn_frac(fmt, Pq)
            u0 = F.ulp(fmt, r) if type(r) is int and r else 1
            v = rng.sign() * (2 * rng.below(4) + 1) * u0
            v = v // 2 if u0 > 1 else v
            vals[y] = [v if F.is_member(fmt, v) else rng.sign() * u0] + [0] * (ky - 1)
        else:
            vals[y] = _operand(fmt, rng, ky, ea)
    else:                                           # exactprod
        es = ea + ex + rng.between(-p, p)
        vals[y] = [rng.sign() * G.in_binade(fmt, rng, max(fmt.qmin, min(fmt.emax, es)), "short")]
        vals[y] += [0] * (ky - 1)
    return vals


# ---------------------------------------------------------------------------
# maxof

def _maxof(fmt, sh, rng, stratum):
    """Operands of a maximum: the state m (a limb), its mask, and the other argument (a limb n,
    or an element x of one or two limbs of which the maximum takes abs(x) or abs(x[0]))."""
    names = [n for n in sh.names if sh.roles[n] != "mask"]
    vals = {}
    for n in sh.names:
        if sh.roles[n] == "mask":
            vals[n] = [rng.bits(1)]
    if stratum in COMMON:
        for n in names:
            vals[n] = _common(fmt, sh, rng, n, stratum)
        if rng.bits(1):
            # The state of a fold is a magnitude.
            vals[names[0]] = [abs(vals[names[0]][0])]
        return vals
    m, other = names[0], names[1]
    k = sh.limbs[other]
    e = G2._e_any(fmt, rng)
    base = G.in_binade(fmt, rng, e, "short" if rng.chance(1, 4) else "uniform")
    if stratum == "equal":
        a = base if rng.chance(3, 4) else 0
        mv = a
        ov = a if rng.bits(1) else -a
    elif stratum == "neighbor":
        a = base
        nb = F.succ(fmt, a) if rng.bits(1) else F.pred(fmt, a)
        nb = nb if type(nb) is int else a
        mv, ov = (a, nb) if rng.bits(1) else (nb, a)
        if rng.bits(1):
            ov = -ov
    else:                                           # negative
        mv = -base if rng.bits(1) else base
        ov = rng.sign() * G.in_binade(fmt, rng, G2._e_any(fmt, rng))
    vals[m] = [mv]
    if k == 1:
        vals[other] = [ov]
    else:
        vals[other] = [ov, G.tail_for(fmt, rng, ov, ("near", "any", "half+", "half-", "max",
                                                     "zero")[rng.below(6)])]
    return vals


# ---------------------------------------------------------------------------

def make_case(fmt, sh, rng, stratum):
    if sh.family == "axpy":
        vals = _axpy(fmt, sh, rng, stratum)
    else:
        vals = _maxof(fmt, sh, rng, stratum)
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
