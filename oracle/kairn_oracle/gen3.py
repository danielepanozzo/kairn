"""Operands for the kernels of the extended domain (the non-finite layer).

A kernel with "domain": "extended" takes operands that may be infinite or NaN.  Its finite
operands are drawn by the generators of the first two waves, from a *finite view* of the kernel
(canonical() read as normalized(), ball(c, r) as a normalized center and nonneg(r), the core's
entries in place of `extends`), so that the extended kernel keeps every stratum of its family.
Strata of this layer come on top: non-finite operands in every position and combination, the
0 * inf corners, finite operands that overflow, operands at the finite_when thresholds, balls in
each state, and the radii of the constructors.

Exhaustive mode enumerates the non-finite values of each operand as part of its domain: +inf,
-inf and NaN for a one-limb operand, (+inf, 0), (-inf, 0) and (NaN, NaN) for a canonical one, the
whole line and the empty set for a ball, +inf and NaN for nonneg().  Restrictions shrink the
finite part of a domain only.

Every case is checked against the requirements before it is written (valid_ext), and the
selftest checks that no stratum produces an invalid case.
"""

from . import expr as EX
from . import fmt as F
from . import gen as G
from . import gen2 as G2

INF, NINF, NAN = F.POS_INF, F.NEG_INF, F.NAN
NONFINITE = (INF, NINF, NAN)


class FiniteView:
    """The kernel as the finite generators see it."""

    def __init__(self, k):
        self.name = k.name
        self.inputs = k.inputs
        self.outputs = k.outputs
        self.masks = k.masks
        self.input_names = k.input_names
        self.value = k.value
        self.value_tree = k.value_tree
        limbs = dict(k.inputs)
        req = []
        for r in k.requires:
            if r[0] == "canonical":
                req.append(("normalized", r[1]))
            elif r[0] == "ball":
                if limbs[r[1]] > 1:
                    req.append(("normalized", r[1]))
                req.append(("nonneg", r[2]))
            else:
                req.append(r)
        self.requires = req
        ens = []
        for e in k.ensures:
            ens.extend(e.core.ensures if e.kind == "extends" else [e])
        self.ensures = ens


class ExtShape:
    def __init__(self, kernel):
        self.kernel = kernel
        view = FiniteView(kernel)
        if G.first_wave_shape(view):
            self.fshape = G.Shape(view)
            self.fmake = G.make_case
            fstrata, fsched = G.STRATA, G.SCHEDULE
        else:
            self.fshape = G2.Shape2(view)
            self.fmake = G2.make_case
            fstrata, fsched = self.fshape.strata, self.fshape.schedule
        self.fstrata = tuple(fstrata)
        self.limbs = dict(kernel.inputs)
        req = kernel.requires
        self.balls = list(kernel.ball_requires)
        inball = {n for b in self.balls for n in b}
        # Units: an operand that can be replaced by a non-finite value as a whole.
        self.roles = {}
        self.units = []
        for n, l in kernel.inputs:
            if n in kernel.masks:
                self.roles[n] = "mask"
                continue
            if n in inball:
                self.roles[n] = "center" if any(n == c for c, _ in self.balls) else "radius"
                if self.roles[n] == "center":
                    self.units.append(("ball", n, next(r for c, r in self.balls if c == n)))
                continue
            if ("power_of_two", n) in req:
                self.roles[n] = "pow2"
                continue
            if l > 1:
                self.roles[n] = "canonical"
            elif ("nonneg", n) in req:
                self.roles[n] = "nonneg"
            else:
                self.roles[n] = "any"
            self.units.append((self.roles[n], n, None))
        kinds = {e.kind for e in kernel.ensures}
        self.conds = []
        for e in kernel.ensures:
            if e.finite_when:
                self.conds.extend(e.finite_when)
        self.lead = next((e.lead for e in kernel.ensures if e.kind == "extends"), None)
        mul = (self.lead == "mul" or (kernel.value_tree is not None
                                      and EX.uses(kernel.value_tree, "*"))
               or any(e.kind == "encloses" and EX.uses(e.set_tree, "*") for e in kernel.ensures))
        ext = ["nonfinite"]
        if mul:
            ext.append("zeroinf")
        if "extends" in kinds:
            ext.append("edge")
        if self.conds:
            ext.append("threshold")
        if "encloses" in kinds:
            ext += ["ballstates", "zerowhole", "hugeradius"]
        if "makes_ball" in kinds:
            ext.append("badradius")
        self.ext_strata = tuple(ext)
        self.strata = self.fstrata + self.ext_strata
        # The strata of this layer come round twice per cycle of the finite schedule.
        self.schedule = tuple(fsched) + tuple(s for s in ext for _ in range(2))


# ---------------------------------------------------------------------------
# Values

def _nonfinite(rng, role):
    if role == "nonneg":
        return [(INF, NAN)[rng.below(2)]]
    if role == "canonical":
        v = NONFINITE[rng.below(3)]
        return [v, NAN] if v == NAN else [v, 0]
    return [NONFINITE[rng.below(3)]]


def _whole(sh, c):
    return [0] * sh.limbs[c], [INF]


def _empty(sh, c):
    return [NAN] * sh.limbs[c], [NAN]


def _set_unit(vals, sh, u, kind):
    """Replace unit u: a ball by the 'whole' line, the 'empty' set or the exact 'zeroball'; any
    other operand by a 'zero' (a power of two stays as it is)."""
    role, n, r = u
    if role == "ball":
        if kind == "whole":
            vals[n], vals[r] = _whole(sh, n)
        elif kind == "empty":
            vals[n], vals[r] = _empty(sh, n)
        else:
            vals[n], vals[r] = [0] * sh.limbs[n], [0]
    elif role != "pow2":
        vals[n] = [0] * sh.limbs[n]


def _finite_case(fmt, sh, rng, stratum=None):
    if stratum is None:
        stratum = sh.fstrata[rng.below(len(sh.fstrata))]
    return sh.fmake(fmt, sh.fshape, rng, stratum)


def _random_negz(rng, vals, names):
    """Zero limbs of the named operands written as -0 at random."""
    out = set()
    for n in names:
        for i, v in enumerate(vals[n]):
            if v == 0 and rng.bits(1):
                out.add((n, i))
    return out


def _unit_names(u):
    return [u[1]] if u[2] is None else [u[1], u[2]]


def make_case(fmt, sh, rng, stratum):
    """Operand limbs {name: [fixed or non-finite, ...]} and the set of (name, limb) that are -0."""
    if stratum in sh.fstrata:
        return _finite_case(fmt, sh, rng, stratum)
    if stratum == "nonfinite":
        return _nonfinite_case(fmt, sh, rng)
    if stratum == "zeroinf":
        return _zeroinf(fmt, sh, rng)
    if stratum == "edge":
        return _edge(fmt, sh, rng)
    if stratum == "threshold":
        return _threshold(fmt, sh, rng)
    if stratum == "ballstates":
        return _ballstates(fmt, sh, rng)
    if stratum == "zerowhole":
        return _zerowhole(fmt, sh, rng)
    if stratum == "hugeradius":
        return _hugeradius(fmt, sh, rng)
    if stratum == "badradius":
        return _badradius(fmt, sh, rng)
    raise G.GenError("unknown stratum %r" % stratum)


def _replaceable(sh):
    return [u for u in sh.units if u[0] != "pow2"]


def _nonfinite_case(fmt, sh, rng):
    """A finite case of any stratum with a random nonempty set of operands replaced by
    non-finite values: infinities of both signs and NaN, canonical pairs, whole lines and empty
    sets, the rest left finite."""
    vals, negz = _finite_case(fmt, sh, rng)
    units = _replaceable(sh)
    pick = [u for u in units if rng.bits(1)] or [units[rng.below(len(units))]]
    for u in pick:
        if u[0] == "ball":
            _set_unit(vals, sh, u, "whole" if rng.bits(1) else "empty")
        else:
            vals[u[1]] = _nonfinite(rng, u[0])
        negz = {(n, i) for n, i in negz if n not in _unit_names(u)}
    negz |= _random_negz(rng, vals, [n for u in pick for n in _unit_names(u)])
    return vals, negz


def _zeroinf(fmt, sh, rng):
    """One operand infinite (or NaN, or a whole line), every other a zero of random sign (a
    zero ball for a ball): the corners of 0 * inf."""
    vals, _ = _finite_case(fmt, sh, rng, "uniform" if "uniform" in sh.fstrata else None)
    units = _replaceable(sh)
    j = rng.below(len(units))
    for k, u in enumerate(units):
        if k == j:
            if u[0] == "ball":
                _set_unit(vals, sh, u, "whole" if rng.chance(3, 4) else "empty")
            elif rng.chance(3, 4):
                v = INF if rng.bits(1) else NINF
                if u[0] == "nonneg":
                    v = INF
                vals[u[1]] = [v] + [0] * (sh.limbs[u[1]] - 1)
            else:
                vals[u[1]] = _nonfinite(rng, u[0])
        else:
            _set_unit(vals, sh, u, "zero" if u[0] != "ball" else "zeroball")
    return vals, _random_negz(rng, vals, [n for n in vals if sh.roles.get(n) != "mask"])


def _top_limb(fmt, rng):
    """Omega, or a limb in the top two binades."""
    if rng.chance(1, 4):
        return fmt.omega
    return G.in_binade(fmt, rng, rng.between(max(fmt.qmin, fmt.emax - 1), fmt.emax),
                       "high" if rng.bits(1) else "uniform")


TOP_TAILS = ("near", "any", "half+", "half-", "quarter-", "max", "zero")


def _operand_at(fmt, sh, rng, n, x0):
    """The operand n with leading limb x0 (and a tail when it has two limbs)."""
    if sh.limbs[n] == 1:
        return [x0]
    return G2._x2_even(fmt, rng, x0, TOP_TAILS[rng.below(len(TOP_TAILS))])


def _edge(fmt, sh, rng):
    """Finite operands at which the core may overflow: leading limbs in the top two binades with
    random signs (so cancelling and not), Omega as either operand; for products, products near
    the overflow threshold, Omega times about one."""
    vals, negz = _finite_case(fmt, sh, rng, "uniform" if "uniform" in sh.fstrata else None)
    ops = [n for n in sh.kernel.input_names if sh.roles[n] != "mask"]
    a, b = ops[0], ops[1]
    if sh.lead in ("add", "sub"):
        xa, xb = _top_limb(fmt, rng), _top_limb(fmt, rng)
        if rng.chance(1, 4):
            xa = fmt.omega
        elif rng.chance(1, 3):
            xb = fmt.omega
        vals[a] = _operand_at(fmt, sh, rng, a, rng.sign() * xa)
        vals[b] = _operand_at(fmt, sh, rng, b, rng.sign() * xb)
    else:
        if sh.roles[b] == "pow2" or sh.roles[a] == "pow2":
            p2, xn = (b, a) if sh.roles[b] == "pow2" else (a, b)
            e = rng.between(fmt.qmin, fmt.emax)
            x0 = G.in_binade(fmt, rng, e, "high" if rng.bits(1) else "uniform")
            if rng.chance(1, 4):
                x0, e = fmt.omega, fmt.emax
            vals[xn] = _operand_at(fmt, sh, rng, xn, rng.sign() * x0)
            k = fmt.emax - e + rng.between(-1, 1)
            vals[p2] = [G2._pow2(fmt, k)]
        else:
            k = rng.below(4)
            if k == 0:
                xa, xb = fmt.omega, G.in_binade(fmt, rng, rng.between(-1, 0) if fmt.qmin <= -1
                                                else fmt.qmin, "high" if rng.bits(1) else "uniform")
            elif k == 1:
                xb, xa = fmt.omega, G.in_binade(fmt, rng, rng.between(-1, 0) if fmt.qmin <= -1
                                                else fmt.qmin, "high" if rng.bits(1) else "uniform")
            else:
                ea, eb = G._split_exponent(fmt, rng, rng.between(fmt.emax - 2, fmt.emax + 1))
                xa = G.in_binade(fmt, rng, ea, "high" if rng.bits(1) else "uniform")
                xb = G.in_binade(fmt, rng, eb, "high" if rng.bits(1) else "uniform")
            vals[a] = _operand_at(fmt, sh, rng, a, rng.sign() * xa)
            vals[b] = _operand_at(fmt, sh, rng, b, rng.sign() * xb)
    negz = {(n, i) for n, i in negz if n not in (a, b)}
    return vals, negz


# -- finite_when thresholds ---------------------------------------------------------------

def _strip(tree):
    while tree[0] in ("neg", "abs"):
        tree = tree[1]
    return tree


def _sum(vals, n):
    return sum(vals[n])


def _threshold(fmt, sh, rng):
    """Finite operands just inside each finite_when condition, |EXPR| <= 2^(qmax+p+E), and a
    quarter of the time just outside one of them: at a power-of-two threshold, the threshold
    itself with a tail toward zero, its predecessor, and beyond them the successor or a tail
    away from zero."""
    vals, negz = _finite_case(fmt, sh, rng, "uniform" if "uniform" in sh.fstrata else None)
    out_at = rng.below(len(sh.conds)) if rng.chance(1, 4) else -1
    touched = set()
    for j, (tree, _text, e) in enumerate(sh.conds):
        t = _strip(tree)
        T = fmt.qmax + fmt.p + e                # the threshold is 2^T
        inside = j != out_at
        if t[0] == "name" and sh.roles.get(t[1]) not in (None, "mask", "pow2"):
            n = t[1]
            vals[n] = _near_power(fmt, sh, rng, n, T, inside)
            touched.add(n)
        elif t[0] == "*" and t[1][0] == "name" and t[2][0] == "name" and t[1][1] != t[2][1]:
            n1, n2 = t[1][1], t[2][1]
            if sh.roles.get(n1) == "pow2":
                n1, n2 = n2, n1
            if sh.roles.get(n1) in (None, "mask", "pow2") or sh.roles.get(n2) in (None, "mask"):
                continue
            _near_product(fmt, sh, rng, vals, n1, n2, T, inside)
            touched.update((n1, n2))
        elif t[0] == "*" and any(u[0] == "name" and sh.roles.get(u[1]) == "pow2" for u in t[1:]):
            # An expression times a power of two, (abs(cx)+rx)*c for the scaling of a ball by a
            # power of two (Milestone 2): c chosen for the operands drawn.
            pn, other = (t[1][1], t[2]) if t[1][0] == "name" and sh.roles.get(t[1][1]) == "pow2" \
                else (t[2][1], t[1])
            if _scale_to(fmt, vals, other, pn, T, inside):
                touched.add(pn)
    negz = {(n, i) for n, i in negz if n not in touched}
    return vals, negz


def _fixed_pow2(fmt, T):
    return 1 << (T - fmt.qmin) if T >= fmt.qmin else None


def _scale_to(fmt, vals, tree, pn, T, inside):
    """The power of two pn set to the largest c with |tree| c <= 2^T (inside), or to twice it,
    for the finite operands in vals; False when no such power of two is a number of the format
    (or tree is zero there)."""
    if any(type(v) is not int for vs in vals.values() for v in vs):
        return False
    src, s = EX.compile_tree(tree, lambda n: ("(%d)" % sum(vals[n]), fmt.qmin))
    e = abs(EX.make_function([], src)())
    if e == 0:
        return False
    # |tree| = e 2^s; the largest k with e 2^(s+k) <= 2^T.
    k = T - s - (e - 1).bit_length() + (0 if inside else 1)
    if not fmt.qmin <= k <= fmt.emax:
        return False
    vals[pn] = [1 << (k - fmt.qmin)]
    return True


def _near_power(fmt, sh, rng, n, T, inside):
    """An operand n with |n| just at or below 2^T (inside), or just above it."""
    lim = _fixed_pow2(fmt, T)
    s = 1 if sh.roles[n] in ("nonneg", "radius") else rng.sign()
    if lim is None or lim > fmt.omega:
        # Every finite operand is inside: the largest ones.
        return _operand_at(fmt, sh, rng, n, s * fmt.omega) if sh.limbs[n] > 1 or inside \
            else [s * fmt.omega]
    two = sh.limbs[n] > 1
    for _ in range(8):
        k = rng.below(3)
        if inside:
            x0 = lim if k else F.pred(fmt, lim)
        else:
            x0 = lim if k == 0 and two else F.succ(fmt, lim)
        if type(x0) is not int:
            x0 = lim
        if not two:
            cand = [s * x0]
        else:
            # Inside: a tail toward zero at the threshold, any tail below it; outside: a tail
            # away from zero at the threshold, any tail above it.
            t1 = G.tail_for(fmt, rng, x0, ("near", "max", "tiny", "zero")[rng.below(4)])
            if x0 == lim:
                t1 = -abs(t1) if inside else abs(t1)
            cand = [s * x0, s * t1]
            if not F.normalized_limbs(fmt, [s * x0, s * t1]):
                cand = [s * x0, 0]
        v = sum(cand)
        if (abs(v) <= lim) == inside:
            return cand
    return [s * lim] + [0] * (sh.limbs[n] - 1) if inside else [s * F.succ(fmt, lim)] + \
        [0] * (sh.limbs[n] - 1)


def _near_product(fmt, sh, rng, vals, n1, n2, T, inside):
    """Operands n1, n2 with |n1 * n2| just at or below 2^T (inside), or just above it."""
    q = fmt.qmin
    # In units of eta^2: |n1 n2| <= 2^(T - 2q).
    lim = T - 2 * q
    e1 = rng.between(max(fmt.qmin, T - fmt.emax - 1), min(fmt.emax, T - fmt.qmin))
    x = _operand_at(fmt, sh, rng, n1, rng.sign() * G.in_binade(fmt, rng, e1))
    vals[n1] = x
    xv = abs(sum(x))
    if xv == 0:
        return
    if sh.roles[n2] == "pow2":
        # The largest power of two c with |x| c <= 2^T, or twice it.
        k = lim - xv.bit_length()
        c = 1 << k if k >= 0 else None
        while c and xv * c > (1 << lim):
            c >>= 1
        if c is None or c == 0:
            return
        if not inside:
            c <<= 1
        if F.is_member(fmt, c):
            vals[n2] = [c]
        return
    # y0 = RD(2^T / |x|) as a number of the format, then steps toward the inside or outside.
    num = 1 << lim if lim >= 0 else 0
    y = F.rdir(fmt, num // xv, fmt.qmin, False) if num else 0
    if y <= 0:
        return
    y = min(y, fmt.omega)
    s = rng.sign()
    for _ in range(6):
        cand = _operand_at(fmt, sh, rng, n2, s * y)
        prod = xv * abs(sum(cand))
        if (prod <= (1 << lim)) == inside:
            vals[n2] = cand
            return
        y2 = F.pred(fmt, y) if inside else F.succ(fmt, y)
        if type(y2) is not int or y2 <= 0:
            return
        y = y2


# -- balls --------------------------------------------------------------------------------

def _ballstates(fmt, sh, rng):
    """Each ball a finite ball, the whole line or the empty set; scalars not finite a third of
    the time."""
    vals, negz = _finite_case(fmt, sh, rng)
    for u in sh.units:
        if u[0] == "ball":
            k = rng.below(4)
            if k == 1:
                _set_unit(vals, sh, u, "whole")
            elif k == 2:
                _set_unit(vals, sh, u, "empty")
        elif u[0] in ("any", "nonneg", "canonical") and rng.chance(1, 3):
            vals[u[1]] = _nonfinite(rng, u[0])
    return vals, _random_negz(rng, vals, [n for n in vals if sh.roles.get(n) != "mask"])


def _zerowhole(fmt, sh, rng):
    """The corner where an exact zero ball meets the whole line, or a zero scalar a whole line,
    or a zero ball a scalar that is not finite."""
    vals, _ = _finite_case(fmt, sh, rng)
    balls = [u for u in sh.units if u[0] == "ball"]
    scalars = [u for u in sh.units if u[0] in ("any", "nonneg", "canonical")]
    if len(balls) >= 2:
        i = rng.below(len(balls))
        for k, u in enumerate(balls):
            _set_unit(vals, sh, u, "whole" if k == i else "zeroball")
            if k != i and rng.chance(1, 4):
                # A ball around zero that is not exact: center 0, a positive radius.
                vals[u[2]] = [G2.radius(fmt, rng, 0, ("eta", "tiny", "uniform")[rng.below(3)])]
    elif balls:
        u = balls[0]
        k = rng.below(3)
        if k == 0:
            _set_unit(vals, sh, u, "zeroball")
            for s in scalars:
                vals[s[1]] = _nonfinite(rng, s[0])
        elif k == 1:
            _set_unit(vals, sh, u, "whole")
            for s in scalars:
                vals[s[1]] = [0] * sh.limbs[s[1]]
        else:
            _set_unit(vals, sh, u, "whole")
    return vals, _random_negz(rng, vals, [n for n in vals if sh.roles.get(n) != "mask"])


def _hugeradius(fmt, sh, rng):
    """Finite balls with radii in the top binades (Omega, its predecessor, 2^emax), with centers
    small or large: the radius computation overflows."""
    vals, negz = _finite_case(fmt, sh, rng, "overflow" if rng.bits(1) else "uniform")
    for u in sh.units:
        if u[0] == "ball" and rng.chance(2, 3):
            vals[u[2]] = [abs(G2._top(fmt, rng)) >> rng.below(2)]
    return vals, negz


def _badradius(fmt, sh, rng):
    """The constructors of balls: radii negative, -inf, NaN, +inf, zero, huge or tiny; centers
    finite, or not finite a quarter of the time."""
    vals, negz = _finite_case(fmt, sh, rng)
    for e in sh.kernel.ensures:
        if e.kind != "makes_ball":
            continue
        c, r = e.from_center, e.from_radius
        if rng.chance(1, 4):
            vals[c] = _nonfinite(rng, sh.roles[c] if sh.roles[c] != "center" else "any")
            if sh.limbs[c] > 1 and len(vals[c]) == 1:
                vals[c] = [vals[c][0], NAN if vals[c][0] == NAN else 0]
        k = rng.below(9)
        if k == 0:
            v = -abs(G2.limb(fmt, rng, "uniform")) or -1
        elif k == 1:
            v = -abs(G2.limb(fmt, rng, "underflow")) or -1
        elif k == 2:
            v = NINF
        elif k == 3:
            v = NAN
        elif k == 4:
            v = INF
        elif k == 5:
            v = 0
        elif k == 6:
            v = abs(G2._top(fmt, rng))
        elif k == 7:
            v = 1
        else:
            v = abs(G2.limb(fmt, rng, "uniform"))
        vals[r] = [v]
        negz = {(n, i) for n, i in negz if n not in (c, r)}
        negz |= _random_negz(rng, vals, [c, r])
    return vals, negz


# ---------------------------------------------------------------------------
# Validity, written from the definitions (the checker has its own)

def _canonical(fmt, limbs):
    if all(type(v) is int for v in limbs):
        return F.normalized_limbs(fmt, limbs)
    if limbs[0] == NAN:
        return all(v == NAN for v in limbs)
    return limbs[0] in (INF, NINF) and all(v == 0 for v in limbs[1:])


def valid_ext(fmt, kernel, vals):
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
            elif v not in NONFINITE:
                return False
    for r in kernel.requires:
        if r[0] == "canonical":
            if not _canonical(fmt, vals[r[1]]):
                return False
        elif r[0] == "ball":
            c, rr = vals[r[1]], vals[r[2]][0]
            if type(rr) is int and all(type(v) is int for v in c):
                if rr < 0 or not F.normalized_limbs(fmt, c):
                    return False
            elif not ((rr == INF and all(v == 0 for v in c))
                      or (rr == NAN and all(v == NAN for v in c))):
                return False
        elif r[0] == "nonneg":
            g = vals[r[1]]
            if any(v == NINF for v in g) or (all(type(v) is int for v in g) and sum(g) < 0):
                return False
        elif r[0] == "power_of_two":
            g = vals[r[1]]
            if not all(type(v) is int for v in g):
                return False
            v = sum(g)
            if v <= 0 or v & (v - 1):
                return False
    return True


# ---------------------------------------------------------------------------
# Exhaustive enumeration

class ExtExhaustiveGen(G.ExhaustiveGen):
    """Every operand combination of an extended kernel, the non-finite values of each operand
    included.  A ball (its center and radius together) is one operand of the enumeration."""

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
        balls = {c: r for c, r in kernel.ball_requires}
        radii = set(balls.values())
        self.slots = []                 # (input names, domain of limb tuples, texts)
        for n, l in kernel.inputs:
            if n in radii:
                continue
            keep = lambda t, nm=n: all(r.keep(fmt, t[0]) for r in self.restrictions if r.name == nm)
            if n in kernel.masks:
                dom = [(0,), (1,)]
                self.slots.append(((n,), dom))
                continue
            if n in balls:
                rn = balls[n]
                keep_r = lambda t: all(r.keep(fmt, t[0]) for r in self.restrictions if r.name == rn)
                centers = [t for t in _finite_domain(fmt, l) if keep(t)]
                rads = [t for t in _finite_domain(fmt, 1) if t[0] >= 0 and keep_r(t)]
                dom = [c + r for c in centers for r in rads]
                dom.append((0,) * l + (INF,))
                dom.append((NAN,) * l + (NAN,))
                self.slots.append(((n, rn), dom))
                continue
            fin = [t for t in _finite_domain(fmt, l) if keep(t)]
            if ("power_of_two", n) in req:
                dom = [t for t in fin if t[0] > 0 and t[0] & (t[0] - 1) == 0]
            elif ("nonneg", n) in req:
                dom = [t for t in fin if sum(t) >= 0] + [(INF,), (NAN,)]
            elif l == 2:
                dom = fin + [(INF, 0), (NINF, 0), (NAN, NAN)]
            else:
                dom = fin + [(INF,), (NINF,), (NAN,)]
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
                txt.append([" ".join(_text(fmt, v) for v in p) for p in parts])
            self.texts.append(txt)
        self.total = 1
        for d in self.doms:
            self.total *= len(d)
        self.coupled = []
        self.index_tags = index_tags
        self.restrict_text = ",".join(r.spec for r in self.restrictions) or "none"

    def case(self, i):
        idx = self.decode(i)
        per = {}
        for (nms, _), txt, k in zip(self.slots, self.texts, idx):
            for m, s in zip(nms, txt[k]):
                per[m] = s
        parts = [self.kernel.name, self.fmt.name]
        parts.extend(per[n] for n, _ in self.kernel.inputs)
        parts.append("#exhaustive:%d" % i if self.index_tags else "#exhaustive")
        return " ".join(parts)


def _finite_domain(fmt, limbs):
    if limbs == 1:
        return [(v,) for v in F.all_values(fmt)]
    return G.normalized_pairs(fmt)


def _text(fmt, v):
    return F.to_hex(v, fmt.qmin) if type(v) is int else v
