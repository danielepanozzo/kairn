"""Random operands for the predicates, comparisons and set operations of a ball of the enclosure
interface (architecture.md, "Claims of the enclosure interface: predicates and comparisons" and
"... the set operations of a ball"; enclosure.py judges them).

Each kernel gets a family from its claims, chosen before the families of gen6.py:

    ivpred     certain or trit over intervals (the predicates, comparisons and relations of
               IEEE 1788 of an interval, one limb and two)
    ballpred   certain or trit over balls
    ballset    ball_set (the hull and the intersection of balls)
    ballsplit  ball_splits (the split of a ball)

Every family has the strata every family has (uniform, underflow, overflow, zero, pow2, extreme),
read for its operands, and strata of its own, which come round twice per cycle; which of them a
kernel gets depends on its operands (one set or two, a point, one limb or two):

    ivpred     special    each interval the empty set, the whole line, a half-line, [0, 0], a
                          point or bounded, at least one of them the empty set or the whole line
               nearzero   intervals at and around zero: [0, 0], [-eta, 0], [0, eta], bounds of
                          both signs, half-lines ending at zero, points next to zero
               point      points and intervals one step wide (one interval)
               member     (a point) the point a bound, one step inside or outside, infinite or NaN
               touch      (two) one common bound: [a, b] and [b, c], in either order
               equal      (two) the same interval, the same point, or the same lower or the same
                          upper bound
               nested     (two) one inside the other, with equal ends or not, half-lines
               disjoint   (two) apart by one step or more
               tails      (two limbs) bounds with the same leading limb and other second limbs,
                          so that the comparison of two limbs decides
    ballpred   ballstates each ball finite, the whole line or the empty set, at least one not
                          finite; a point infinite or NaN a third of the time
               nearzero   (one ball) c = +-r exactly, one unit off, c = 0 and r = 0, [0 +- eta]
               boundary   (a point or two balls) exactly on the boundary of the relation: the
                          point c +- r; the balls touching (cy - ry = cx + rx), one inside the
                          other with an equal end, the same point
               near       as boundary, one to three units of the last limb off on either side
               huge       radii in the top binades (rx + ry beyond Omega), centers of opposite
                          signs near Omega (their difference beyond Omega)
               points     zero radii: equal centers and not
               wide       (two balls) one radius much wider than the other, or than the distance
    ballset    ballstates the states of the two balls, both special an eighth of the time
               bothspecial both empty, both the whole line (centers zeros of either sign, so
                          of different signs half the time), one empty and one the whole line
               disjoint, touch, nested, overlap: finite balls so placed
               wide       huge radii and centers near Omega (the bounds of the intervals beyond
                          Omega)
               point      zero radii
    ballsplit  ballstates the empty set and the whole line
               radii      zero, eta, an odd multiple of eta, a subnormal radius, Omega and its
                          predecessor, a radius much wider than the center
               top        centers near +-Omega with radii of every size

Every case is checked against the requirements before it is written (gen6.valid6).  A zero is
written with a sign at random ("-0x0p+0").  A NaN is written nan: the line protocol has no other
spelling of it (architecture.md, "The line protocol"), so two empty balls whose NaNs differ in sign
or payload cannot be written; two whole lines whose centers are zeros of different signs can.
"""

from . import fmt as F
from . import gen as G
from . import gen2 as G2
from . import gen6 as G6

INF, NINF, NAN = F.POS_INF, F.NEG_INF, F.NAN
COMMON = G2.COMMON
FAMILIES = ("ivpred", "ballpred", "ballset", "ballsplit")


def family_of(kernel):
    """The family of a kernel of the enclosure interface, or None."""
    for e in kernel.ensures:
        if e.kind in ("certain", "trit"):
            return "ivpred" if e.over == "intervals" else "ballpred"
        if e.kind == "ball_set":
            return "ballset"
        if e.kind == "ball_splits":
            return "ballsplit"
    return None


def own_strata(family, nsets, point, k):
    if family == "ivpred":
        s = ["special", "nearzero"]
        if point:
            s.append("member")
        elif nsets == 1:
            s.append("point")
        else:
            s += ["touch", "equal", "nested", "disjoint"]
        if k == 2:
            s.append("tails")
        return tuple(s)
    if family == "ballpred":
        s = ["ballstates"]
        if nsets == 1 and not point:
            s.append("nearzero")
        else:
            s += ["boundary", "near"]
        s += ["huge", "points"]
        if nsets == 2:
            s.append("wide")
        return tuple(s)
    if family == "ballset":
        return ("ballstates", "bothspecial", "disjoint", "touch", "nested", "overlap", "wide",
                "point")
    return ("ballstates", "radii", "top")


class ShapeEnc:
    def __init__(self, kernel):
        self.kernel = kernel
        self.family = family_of(kernel)
        if self.family is None:
            raise G.GenError("%s: not a kernel of the enclosure interface" % kernel.name)
        self.names = [n for n, _ in kernel.inputs]
        self.limbs = dict(kernel.inputs)
        self.extended = kernel.extended
        e = next(e for e in kernel.ensures if e.kind in ("certain", "trit", "ball_set",
                                                         "ball_splits"))
        self.entry = e
        self.point = None
        if e.kind in ("certain", "trit"):
            # The sets in the order of the arguments (x then y), a point first for member.
            order = [a for a in e.args if a in e.sets]
            self.sets = [e.sets[n] for n in order]
            self.point = e.point
            self.rel = e.rel
        elif e.kind == "ball_set":
            self.sets = list(e.balls.values())
            self.rel = e.op
        else:
            self.sets = [e.from_ball]
            self.rel = None
        self.k = self.limbs[self.sets[0][0]]
        own = own_strata(self.family, len(self.sets), self.point is not None, self.k)
        self.strata = COMMON + own
        self.schedule = ("uniform",) + tuple(s for s in own for _ in range(2)) + COMMON[1:]


# ---------------------------------------------------------------------------
# Numbers

def _num(fmt, rng, k, stratum="uniform"):
    return G6._number(fmt, rng, k, stratum)


def _value(v):
    return G6._value(v)


def _exact(fmt, k, v):
    """The k-limb number whose value is exactly the fixed value v, or None."""
    if k == 1:
        return [v] if F.is_member(fmt, v) else None
    c = G6._from_value(fmt, 2, v)
    return c if c is not None and sum(c) == v else None


def _short(fmt, rng, e):
    """A number of one to three set bits at exponent e, of a random sign."""
    return rng.sign() * G.in_binade(fmt, rng, e, "short")


def _units(fmt, k, v):
    """The unit of the last limb of a k-limb value: the gap at a one-limb number, or the unit of
    the second limb (eta at least) of a pair."""
    if k == 1:
        return F.ulp(fmt, v[0])
    return max(F.ulp(fmt, v[1]) if v[1] else F.ulp(fmt, v[0]) >> fmt.p, 1)


def _moved(fmt, k, v, n):
    """v moved by n units of its last limb (as a k-limb number), or v."""
    if k == 1:
        t = v[0]
        for _ in range(abs(n)):
            t2 = F.succ(fmt, t) if n > 0 else F.pred(fmt, t)
            if type(t2) is not int:
                break
            t = t2
        return [t]
    c = _exact(fmt, 2, sum(v) + n * _units(fmt, 2, v))
    return c or v


# ---------------------------------------------------------------------------
# Intervals

def _interval(fmt, rng, k, stratum="uniform"):
    return G6._interval(fmt, rng, k, stratum)


def _special_iv(fmt, rng, k, kind=None):
    return G6._special(fmt, rng, k, kind)


def _zero_iv(fmt, rng, k):
    z = [0] * k
    eta = [1] + [0] * (k - 1)
    meta = [-1] + [0] * (k - 1)
    j = rng.below(8)
    if j == 0:
        return z, list(z)
    if j == 1:
        return meta, list(z)
    if j == 2:
        return list(z), eta
    if j == 3:
        a = _num(fmt, rng, k, "uniform")
        return G6._sorted2([-abs(a[0])] + [-t for t in a[1:]] if a[0] > 0 else a, list(z))
    if j == 4:
        return G6._inf(k, -1), list(z) if rng.bits(1) else meta
    if j == 5:
        return list(z) if rng.bits(1) else eta, G6._inf(k, 1)
    if j == 6:
        a = _num(fmt, rng, k, ("uniform", "underflow")[rng.below(2)])
        return G6._sorted2(a, [-t for t in a])
    p = eta if rng.bits(1) else meta
    return p, list(p)


def _tails_pair(fmt, rng):
    """Two pairs with the same leading limb and second limbs that differ (or not)."""
    a = G2.expansion(fmt, rng, ("uniform", "extreme", "pow2")[rng.below(3)])
    t = G.tail_for(fmt, rng, a[0], ("near", "any", "half+", "half-", "max", "eta",
                                    "zero")[rng.below(7)])
    b = [a[0], t] if F.normalized_limbs(fmt, [a[0], t]) else list(a)
    return G6._sorted2(a, b)


def _ivpred(fmt, sh, rng, stratum):
    """The intervals (and the point) of a case: {'sets': [(lo, hi), ...], 'point': limbs}."""
    k = sh.k
    n = len(sh.sets)
    point = None
    if stratum in COMMON:
        ivs = [_interval(fmt, rng, k, stratum) for _ in range(n)]
        if sh.point is not None:
            point = _num(fmt, rng, k, stratum)
    elif stratum == "special":
        ivs = [_special_iv(fmt, rng, k) if rng.bits(1) else _interval(fmt, rng, k)
               for _ in range(n)]
        j = rng.below(n)
        ivs[j] = _special_iv(fmt, rng, k, ("empty", "whole")[rng.below(2)])
        if sh.point is not None:
            point = _point_any(fmt, rng, k, ivs[0])
    elif stratum == "nearzero":
        ivs = [_zero_iv(fmt, rng, k) for _ in range(n)]
        if n == 2 and rng.bits(1):
            ivs[rng.below(2)] = _interval(fmt, rng, k, ("uniform", "underflow")[rng.below(2)])
        if sh.point is not None:
            point = [0] * k if rng.bits(1) else _point_any(fmt, rng, k, ivs[0])
    elif stratum == "point":
        ivs = [G6._point(fmt, rng, k)]
    elif stratum == "member":
        x = _special_iv(fmt, rng, k) if rng.chance(1, 4) else _interval(fmt, rng, k)
        ivs = [x]
        point = _point_any(fmt, rng, k, x)
    elif stratum == "tails":
        ivs = []
        for _ in range(n):
            ivs.append(_tails_pair(fmt, rng) if rng.bits(1) else _interval(fmt, rng, k))
        if n == 2:
            # A bound of one interval with the leading limb of a bound of the other.
            (a, b), (c, d) = ivs
            j = rng.below(5)

            def retail(src):
                t = G.tail_for(fmt, rng, src[0], ("near", "any", "max", "eta",
                                                  "zero")[rng.below(5)])
                return [src[0], t] if F.normalized_limbs(fmt, [src[0], t]) else list(src)
            if j == 4:
                # Both bounds with the leading limbs of the other interval's.
                ivs[1] = G6._sorted2(retail(a), retail(b))
            else:
                ivs[1] = G6._sorted2(retail([a, b][j % 2]), d if j < 2 else c)
        if sh.point is not None:
            x = ivs[0]
            b = x[rng.below(2)]
            t = G.tail_for(fmt, rng, b[0], ("near", "any", "max", "eta", "zero")[rng.below(5)])
            point = [b[0], t] if F.normalized_limbs(fmt, [b[0], t]) else list(b)
    else:
        a, b, c, d = sorted((_num(fmt, rng, k, "uniform" if rng.bits(1) else "extreme")
                             for _ in range(4)), key=G6._key)
        if stratum == "touch":
            ivs = [(a, b), (list(b), d)]
        elif stratum == "equal":
            j = rng.below(4)
            ivs = [(a, d), (list(a), list(d))] if j == 0 else \
                [(a, c), (list(a), d)] if j == 1 else [(b, d), (a, list(d))] if j == 2 else \
                [(a, list(a)), (list(a), list(a))]
            if rng.chance(1, 4):
                inf = G6._inf(k, -1) if rng.bits(1) else G6._inf(k, 1)
                ivs = [(inf, d), (list(inf), list(d))] if inf[0] == NINF else \
                    [(a, inf), (list(a), list(inf))]
        elif stratum == "nested":
            j = rng.below(4)
            if j == 0:
                ivs = [(a, d), (b, c)]
            elif j == 1:
                ivs = [(a, d), (list(a), c)]
            elif j == 2:
                ivs = [(G6._inf(k, -1), d), (b, c)]
            else:
                ivs = [(G6._inf(k, -1), G6._inf(k, 1)), (b, G6._inf(k, 1))]
        else:
            if G6._key(b) < G6._key(c):
                ivs = [(a, b), (c, d)]
            else:
                ivs = [(a, a), (d, d)]
            if rng.bits(1):
                # One step apart.
                st = G6._step(fmt, k, b, True)
                if st and G6._key(st) <= G6._key(d):
                    ivs = [(a, b), (st, d)]
        if rng.bits(1):
            ivs.reverse()
    return {"sets": ivs, "point": point}


def _point_any(fmt, rng, k, x):
    """A point for member: a bound of x, one step inside or outside it, an infinity, a NaN, or a
    number."""
    j = rng.below(6)
    if j == 0:
        return G6._inf(k, rng.sign())
    if j == 1:
        return G6._nan(k)
    lo, hi = x
    b = lo if rng.bits(1) else hi
    if type(b[0]) is not int:
        return _num(fmt, rng, k)
    if j == 2:
        return list(b)
    if j in (3, 4):
        st = G6._step(fmt, k, b, j == 3)
        return st or list(b)
    return _num(fmt, rng, k)


# ---------------------------------------------------------------------------
# Balls

def _radius(fmt, rng, c0, modes=G2.RADIUS_MODES):
    return G2.radius(fmt, rng, c0, modes[rng.below(len(modes))])


def _ball(fmt, rng, k, stratum="uniform"):
    c = _num(fmt, rng, k, stratum)
    mode = {"underflow": ("zero", "eta", "subnormal", "tiny", "ulp"),
            "overflow": ("huge", "comparable", "wide", "zero"),
            "zero": ("zero", "eta", "uniform")}.get(stratum, G2.RADIUS_MODES)
    return c, [_radius(fmt, rng, c[0], mode)]


def _ball_state(k, which):
    if which == "whole":
        return [0] * k, [INF]
    return G6._nan(k), [NAN]


def _ball_any(fmt, rng, k):
    j = rng.below(4)
    if j == 0:
        return _ball_state(k, "whole")
    if j == 1:
        return _ball_state(k, "empty")
    return _ball(fmt, rng, k)


def _short_ball(fmt, rng, k, e):
    """A finite ball of a short center and a short radius near exponent e (sums exact)."""
    c = _short(fmt, rng, max(fmt.qmin, min(fmt.emax, e)))
    r = abs(_short(fmt, rng, max(fmt.qmin, min(fmt.emax, e - rng.below(3)))))
    return [c] + [0] * (k - 1), [r]


def _boundary_balls(fmt, rng, sh, near):
    """Two balls (or a ball and a point) exactly on the boundary of the relation, or moved by one to
    three units off it (near)."""
    k = sh.k
    lo, hi = G._mid(fmt, 2 * fmt.p + 2, 2)
    e = rng.between(lo, hi)
    cx, rx = _short_ball(fmt, rng, k, e)
    vx, r = sum(cx), rx[0]
    if sh.point is not None:
        v = vx + r if rng.bits(1) else vx - r
        t = _exact(fmt, k, v) or G6._from_value(fmt, k, v) or list(cx)
        if near:
            t = _moved(fmt, k, t, rng.sign() * rng.between(1, 3))
        return [(cx, rx)], t
    cy, ry = _short_ball(fmt, rng, k, e)
    rel = sh.rel
    j = rng.below(3)
    if rel == "subset" or j == 0:
        # One inside the other with an equal end: rx = |cy - cx| + ry.
        need = abs(sum(cy) - vx) + ry[0]
        if F.is_member(fmt, need) and need <= fmt.omega:
            rx = [need]
    elif j == 1:
        # Touching: cy - ry = cx + rx (or cy + ry = cx - rx).
        s = 1 if rng.bits(1) else -1
        c = _exact(fmt, k, vx + s * (r + ry[0]))
        if c is not None:
            cy = c
    else:
        # The same point.
        rx, ry, cy = [0], [0], list(cx)
    if near:
        if rng.bits(1):
            cy = _moved(fmt, k, cy, rng.sign() * rng.between(1, 3))
        else:
            t = _moved(fmt, 1, rx if rng.bits(1) else ry, rng.sign() * rng.between(1, 3))
            if t[0] >= 0:
                if rng.bits(1):
                    rx = t
                else:
                    ry = t
    balls = [(cx, rx), (cy, ry)]
    if rng.bits(1):
        balls.reverse()
    return balls, None


def _ballpred(fmt, sh, rng, stratum):
    k = sh.k
    n = len(sh.sets)
    point = None
    if stratum in COMMON:
        balls = [_ball(fmt, rng, k, stratum) for _ in range(n)]
        if sh.point is not None:
            point = _num(fmt, rng, k, stratum)
    elif stratum == "ballstates":
        balls = [_ball_any(fmt, rng, k) for _ in range(n)]
        j = rng.below(n)
        balls[j] = _ball_state(k, ("whole", "empty")[rng.below(2)])
        if sh.point is not None:
            j = rng.below(3)
            point = G6._inf(k, rng.sign()) if j == 0 else G6._nan(k) if j == 1 else \
                _num(fmt, rng, k)
    elif stratum == "nearzero":
        c, r = _ball(fmt, rng, k, ("uniform", "underflow", "extreme")[rng.below(3)])
        j = rng.below(5)
        if j == 0:
            c, r = [0] * k, [0]
        elif j == 1:
            c, r = [0] * k, [1]
        elif j in (2, 3):
            # c = +-r exactly, or one unit off.
            r = [abs(c[0])]
            if k == 2 and c[1]:
                c = [c[0], 0]
            if j == 3:
                c = _moved(fmt, k, c, rng.sign())
        balls = [(c, r)]
    elif stratum in ("boundary", "near"):
        balls, point = _boundary_balls(fmt, rng, sh, stratum == "near")
    elif stratum == "huge":
        balls = []
        for _ in range(n):
            c = [G2._top(fmt, rng)] + [0] * (k - 1) if rng.bits(1) else _num(fmt, rng, k)
            r = [abs(G2._top(fmt, rng)) >> rng.below(3)] if rng.bits(1) else [
                _radius(fmt, rng, c[0])]
            balls.append((c, r))
        # At least one radius in the top binades.
        j = rng.below(n)
        balls[j] = (balls[j][0], [abs(G2._top(fmt, rng)) >> rng.below(3)])
        if n == 2 and rng.bits(1):
            # Centers of opposite signs near Omega: their difference is beyond Omega.
            t = abs(G2._top(fmt, rng))
            balls[0] = ([t] + [0] * (k - 1), balls[0][1])
            balls[1] = ([-abs(G2._top(fmt, rng))] + [0] * (k - 1), balls[1][1])
        if sh.point is not None:
            point = [G2._top(fmt, rng)] + [0] * (k - 1)
    elif stratum == "points":
        c = _num(fmt, rng, k)
        balls = [(c, [0])] + [((list(c) if rng.bits(1) else _num(fmt, rng, k)), [0])
                              for _ in range(n - 1)]
        if sh.point is not None:
            point = list(c) if rng.bits(1) else _num(fmt, rng, k)
    else:
        # wide: one radius much wider than the other or than the distance.
        cx, rx = _ball(fmt, rng, k)
        cy = _num(fmt, rng, k) if rng.bits(1) else list(cx)
        ry = [_radius(fmt, rng, cy[0], ("wide", "huge", "tiny", "zero"))]
        balls = [(cx, rx), (cy, ry)]
        if rng.bits(1):
            balls.reverse()
    return {"sets": balls, "point": point}


def _ballset(fmt, sh, rng, stratum):
    k = sh.k
    if stratum in COMMON:
        return {"sets": [_ball(fmt, rng, k, stratum) for _ in range(2)], "point": None}
    if stratum == "ballstates":
        if rng.chance(1, 8):
            balls = [_ball_state(k, ("whole", "empty")[rng.below(2)]) for _ in range(2)]
        else:
            balls = [_ball_any(fmt, rng, k) for _ in range(2)]
        return {"sets": balls, "point": None}
    if stratum == "bothspecial":
        j = rng.below(3)
        if j == 0:
            balls = [_ball_state(k, "empty"), _ball_state(k, "empty")]
        elif j == 1:
            balls = [_ball_state(k, "whole"), _ball_state(k, "whole")]
        else:
            balls = [_ball_state(k, "empty"), _ball_state(k, "whole")]
            if rng.bits(1):
                balls.reverse()
        return {"sets": balls, "point": None}
    if stratum == "point":
        c = _num(fmt, rng, k)
        d = list(c) if rng.chance(1, 3) else _num(fmt, rng, k)
        return {"sets": [(c, [0]), (d, [0] if rng.bits(1) else [_radius(fmt, rng, d[0])])],
                "point": None}
    if stratum == "wide":
        balls = []
        for _ in range(2):
            c = [G2._top(fmt, rng)] + [0] * (k - 1) if rng.bits(1) else _num(fmt, rng, k)
            balls.append((c, [abs(G2._top(fmt, rng)) >> rng.below(3)]))
        return {"sets": balls, "point": None}
    # Finite balls placed: disjoint, touching, nested, overlapping.
    lo, hi = G._mid(fmt, 2 * fmt.p + 2, 2)
    e = rng.between(lo, hi)
    cx, rx = _short_ball(fmt, rng, k, e)
    vx, r = sum(cx), rx[0]
    if stratum == "touch":
        s = 1 if rng.bits(1) else -1
        ry = [abs(_short(fmt, rng, e - rng.below(3)))]
        cy = _exact(fmt, k, vx + s * (r + ry[0])) or _num(fmt, rng, k)
    elif stratum == "nested":
        ry = [abs(_short(fmt, rng, e - 1 - rng.below(3)))]
        cy = _exact(fmt, k, vx + rng.sign() * (abs(r - ry[0]) >> rng.below(2))) or list(cx)
        if rng.bits(1):
            cy = list(cx)
    elif stratum == "disjoint":
        ry = [abs(_short(fmt, rng, e - rng.below(3)))]
        d = 2 * (r + ry[0]) + abs(_short(fmt, rng, e))
        cy = _exact(fmt, k, vx + rng.sign() * d) or _num(fmt, rng, k)
    else:
        ry = [abs(_short(fmt, rng, e - rng.below(2)))]
        cy = _exact(fmt, k, vx + rng.sign() * (r + ry[0]) // 2) or _num(fmt, rng, k)
    balls = [(cx, rx), (cy, ry)]
    if rng.bits(1):
        balls.reverse()
    return {"sets": balls, "point": None}


def _ballsplit(fmt, sh, rng, stratum):
    k = sh.k
    if stratum in COMMON:
        return {"sets": [_ball(fmt, rng, k, stratum)], "point": None}
    if stratum == "ballstates":
        return {"sets": [_ball_state(k, ("whole", "empty")[rng.below(2)])], "point": None}
    if stratum == "radii":
        c = _num(fmt, rng, k, ("uniform", "extreme", "underflow")[rng.below(3)])
        j = rng.below(7)
        if j == 0:
            r = 0
        elif j == 1:
            r = 1
        elif j == 2:
            r = 2 * rng.below(max(fmt.lam, 1)) + 1
        elif j == 3:
            r = G2.radius(fmt, rng, c[0], "subnormal")
        elif j == 4:
            r = fmt.omega
        elif j == 5:
            r = F.pred(fmt, fmt.omega)
        else:
            r = G2.radius(fmt, rng, c[0], "wide")
        return {"sets": [(c, [min(r, fmt.omega)])], "point": None}
    c = [G2._top(fmt, rng)] + [0] * (k - 1)
    if k == 2 and rng.bits(1):
        t = G.tail_for(fmt, rng, c[0], ("near", "max")[rng.below(2)])
        if F.normalized_limbs(fmt, [c[0], t]):
            c = [c[0], t]
    return {"sets": [(c, [_radius(fmt, rng, c[0])])], "point": None}


MAKERS = {"ivpred": _ivpred, "ballpred": _ballpred, "ballset": _ballset, "ballsplit": _ballsplit}


def make_case(fmt, sh, rng, stratum):
    """Operand limbs {name: [...]} and the set of (name, limb) written with a minus sign: zeros,
    and NaNs (the line protocol's -nan)."""
    case = MAKERS[sh.family](fmt, sh, rng, stratum)
    vals = {}
    for (a, b), (A, B) in zip(sh.sets, case["sets"]):
        vals[a], vals[b] = list(A), list(B)
    if sh.point is not None:
        vals[sh.point] = list(case["point"]) if case["point"] is not None else \
            _num(fmt, rng, sh.limbs[sh.point])
    for n in sh.names:
        if n not in vals:
            vals[n] = [rng.bits(1)] if n in sh.kernel.masks else [0] * sh.limbs[n]
    neg = set()
    for n, limbs in vals.items():
        if n in sh.kernel.masks:
            continue
        for i, v in enumerate(limbs):
            if v == 0 and rng.bits(1):
                neg.add((n, i))
    return vals, neg
