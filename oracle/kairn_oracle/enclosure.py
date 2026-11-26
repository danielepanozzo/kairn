"""The claims of the enclosure interface's predicates, comparisons and set operations of a ball:
their reading and their judges.

architecture.md, "Claims of the enclosure interface: predicates and comparisons" and "... the set
operations of a ball", read with milestone2.md, "One enclosure interface" ("The empty set and the
whole line", "Comparisons", "Hull, intersection and split of balls") and "IEEE 1788".  The kinds:

- certain (of: a mask; rel, args; intervals or balls; exact or exact_when): the mask is true only
  if the relation holds; exactly when it holds when an operand is not finite (the empty set or the
  whole line, a point that is not a finite number), with exact always, and with exact_when when
  every operand is finite and every condition holds;
- trit (yes, no: two masks; the same fields): yes only if the relation holds for every choice of
  members, no only if it fails for every choice, never both; exactly so where certain is exact;
- ball_set (center, radius; set union or intersection; balls: two): a canonical ball that contains
  every member of X or Y (of both); for union empty exactly when both are, Y as it is when X is
  empty, X as it is when Y is empty and X is not; for intersection empty when an operand is, Y as
  it is when X is the whole line, X as it is when Y is the whole line and X is not;
- ball_splits (parts: two balls; from: a ball): both canonical, the empty set twice, the whole
  line twice, and for a finite ball [c - r, c] in the first part and [c, c + r] in the second.

"As it is" is the operand's limbs, read from the line's text: the sign of a zero is compared (the
one place where it is), a NaN matches a NaN (the line protocol prints every NaN as nan).

Members of a set are real numbers: those between the bounds of an interval ([1, +inf] does not
contain +inf), those within the radius of a finite ball's center, every real number for the whole
line, none for the empty set.  A set is written here as EMPTY or ("nonempty", L, U), L and U
integers at scale qmin or the infinities of fmt.py, so that every relation is a comparison of
extended reals: lt holds for every choice exactly when every set named is nonempty and the upper
bound of the first is below the lower bound of the second (an infinite bound makes it false: the
members are unbounded), and so on (relation()).
"""

from . import expr as X
from . import extended as XT
from . import fmt as F
from . import intervals as IV

INF, NINF, NAN = F.POS_INF, F.NEG_INF, F.NAN
EMPTY = ("empty",)


def _error(msg):
    from .claims import ClaimsError
    return ClaimsError(msg)


KNOWN = {
    "certain": {"kind", "of", "rel", "args", "intervals", "balls", "exact", "exact_when"},
    "trit": {"kind", "yes", "no", "rel", "args", "intervals", "balls", "exact", "exact_when"},
    "ball_set": {"kind", "center", "radius", "set", "balls"},
    "ball_splits": {"kind", "parts", "from"},
}
# The relations and their arguments (architecture.md, the table of "rel"): two of a set or the
# integer 0, a point and a set, two sets, one set.  trit has the first four only.
ORDER_RELS = ("lt", "le", "eq")
SET_RELS = ("subset", "equal", "interior", "disjoint")
ONE_RELS = ("empty", "entire")
RELS = ORDER_RELS + ("member",) + SET_RELS + ONE_RELS
TRIT_RELS = ORDER_RELS + ("member",)
SET_OPS = ("union", "intersection")


# ---------------------------------------------------------------------------
# Count names (the statistics the cross-checks' guards read, tests/crosscheck_guards.py)

HOLDS = "the relation holds"
FAILS_ALL = "the relation fails for every choice"
NEITHER = "the relation neither holds nor fails for every choice"
NOT_HOLDS = "the relation does not hold"
MASK_TRUE = "mask true"
MASK_FALSE = "mask false"
ANS_YES = "answer yes"
ANS_NO = "answer no"
ANS_UNKNOWN = "answer unknown"
SPECIAL = "an operand not finite: exact (claimed)"
ALL_FINITE = "every operand finite"
EW_HOLDS = "exact_when holds"
EW_FAILS = "exact_when fails: "
# An answer not given (not claimed: certain and trit without exact, and exact_when failing): how far
# from the boundary of the relation it was, relative to the largest radius and to u^2 times the
# distance of the centers (architecture.md: "The band is not claimed").
UNDECIDED_HOLDS = "unknown although the relation holds (not claimed)"
UNDECIDED_FAILS = "unknown although the relation fails for every choice (not claimed)"
FALSE_HOLDS = "mask false although the relation holds (not claimed)"
BAND_RADIUS = "an answer not given: largest margin / largest radius"
BAND_DISTANCE = "an answer not given: largest margin / (u^2 * distance)"
BAND_UNITS = ("an answer not given: largest margin / (2e + G), e = 3 u^2 distance + 2 lambda, G the "
              "gap at max(radius, distance), both below Omega/4")
# The class of an operand, per name: "x: empty", ...
CLASS = "%s: %s"
IV_CLASSES = ("empty", "whole line", "half-line", "bounded", "a point")
BALL_CLASSES = ("empty", "whole line", "finite", "a point")
POINT_CLASSES = ("finite", "infinite", "NaN")
# ball_set
SET_PAIR = "X %s, Y %s"
STATES = ("empty", "whole line", "finite")
SET_PAIRS = tuple(SET_PAIR % (a, b) for a in STATES for b in STATES)
SET_ZERO_SIGNS = "both the whole line, centers zeros of different signs in the line"
SET_Y_AS_IS = "Y as it is (claimed)"
SET_X_AS_IS = "X as it is (claimed)"
SET_DISJOINT = "finite operands, disjoint"
SET_TOUCH = "finite operands, touching (one common point)"
SET_OVERLAP = "finite operands, overlapping"
SET_NESTED = "finite operands, one inside the other"
Z_STATE = "result: %s"
SET_WHOLE_FROM_FINITE = "result the whole line from finite operands"
SET_RATIO = "result radius / smallest radius that contains what is due"
# ball_splits
SPLIT_X = "X: %s"
SPLIT_ZERO = "X: a point (radius 0)"
SPLIT_PART = "%s part: %s"
SPLIT_RATIO = "part radius / (r/2)"


# ---------------------------------------------------------------------------
# Reading

def read_entry(entry, kernel, raw, where):
    """Read one entry of a kind of KNOWN into entry (its fields, of, label)."""
    if not kernel.extended:
        raise _error("%s: this kind belongs to the extended domain, and the kernel has no "
                     "\"domain\": \"extended\"" % where)
    entry.iv = True
    entry.encl = True
    entry.consts = {}
    READERS[entry.kind](entry, kernel, raw, where)
    entry.label = label(entry)


def _mask_output(kernel, n, where, what):
    if not isinstance(n, str) or n not in dict(kernel.outputs) or n not in kernel.masks:
        raise _error("%s: %s must name a mask output, got %r" % (where, what, n))
    return n


def _zero_arg(a):
    return (isinstance(a, str) and a.strip() == "0") or (type(a) is int and a == 0)


def _read_sets(e, kernel, raw, where):
    has_iv, has_ball = "intervals" in raw, "balls" in raw
    if has_iv == has_ball:
        raise _error("%s: the sets are named by intervals or by balls, one of the two" % where)
    if has_iv:
        e.over = "intervals"
        e.sets = IV._interval_names(kernel, raw, where)
    else:
        e.over = "balls"
        e.sets = IV._ball_names(kernel, raw, where)


def _read_relation(e, kernel, raw, where):
    fields = ("yes", "no") if e.kind == "trit" else ("of",)
    IV._require(raw, fields + ("rel", "args"), where)
    if e.kind == "trit":
        e.yes = _mask_output(kernel, raw["yes"], where, "yes")
        e.no = _mask_output(kernel, raw["no"], where, "no")
        if e.yes == e.no:
            raise _error("%s: yes and no must be two mask outputs" % where)
        e.of = [e.yes, e.no]
    else:
        e.of = [_mask_output(kernel, raw["of"], where, "of")]
    _read_sets(e, kernel, raw, where)
    e.rel = raw["rel"]
    allowed = TRIT_RELS if e.kind == "trit" else RELS
    if e.rel not in allowed:
        raise _error("%s: rel must be one of %s, got %r" % (where, ", ".join(allowed), e.rel))
    args = raw["args"]
    arity = 1 if e.rel in ONE_RELS else 2
    if not isinstance(args, list) or len(args) != arity:
        raise _error("%s: %s takes %d argument%s" % (where, e.rel, arity, "s" if arity > 1 else ""))
    e.point = None
    e.args = []
    if e.rel in ORDER_RELS:
        for a in args:
            if _zero_arg(a):
                e.args.append("0")
            elif isinstance(a, str) and a in e.sets:
                e.args.append(a)
            else:
                raise _error("%s: an argument of %s is a set of the entry or the integer 0, got %r"
                             % (where, e.rel, a))
        if e.args == ["0", "0"]:
            raise _error("%s: one argument of %s must be a set" % (where, e.rel))
    elif e.rel == "member":
        t, s = args
        inset = {n for pair in e.sets.values() for n in pair}
        if not isinstance(t, str) or t not in dict(kernel.inputs) or t in kernel.masks \
                or t in inset:
            raise _error("%s: the point of member must be a limb input outside the sets, got %r"
                         % (where, t))
        k = kernel.limbs_of(t)
        if k not in (1, 2) or (k == 2 and ("canonical", t) not in kernel.requires):
            raise _error("%s: the point %s is an input of one limb, or of two required "
                         "canonical()" % (where, t))
        if not isinstance(s, str) or s not in e.sets:
            raise _error("%s: the second argument of member must be a set of the entry, got %r"
                         % (where, s))
        e.point = t
        e.args = [t, s]
    else:
        for a in args:
            if not isinstance(a, str) or a not in e.sets:
                raise _error("%s: an argument of %s must be a set of the entry, got %r"
                             % (where, e.rel, a))
        if len(set(args)) != len(args):
            raise _error("%s: %s names the same set twice" % (where, e.rel))
        e.args = list(args)
    unused = sorted(set(e.sets) - set(e.args))
    if unused:
        raise _error("%s: the set %s is named but is not an argument" % (where, unused[0]))
    e.exact = IV._true_flag(raw, "exact", where)
    e.exact_when_abs = None
    if "exact_when" in raw:
        if e.exact:
            raise _error("%s: exact and exact_when together" % where)
        e.exact_when_abs = _read_abs_le(kernel, raw["exact_when"], where)


def _read_abs_le(kernel, lst, where):
    """[(tree, text)]: the conditions {"abs_le": EXPR, "omega": true}, |EXPR| <= Omega, EXPR in the
    language of value over the limb inputs.  A nonempty list (absent when there is none)."""
    if not isinstance(lst, list) or not lst:
        raise _error("%s: exact_when must be a nonempty list of conditions (absent when there is "
                     "none)" % where)
    out = []
    for j, cond in enumerate(lst):
        w = "%s: exact_when[%d]" % (where, j)
        if (not isinstance(cond, dict) or set(cond) != {"abs_le", "omega"}
                or cond["omega"] is not True or not isinstance(cond["abs_le"], str)):
            raise _error("%s must be {\"abs_le\": EXPR, \"omega\": true}, got %r" % (w, cond))
        try:
            tree = X.parse(cond["abs_le"])
        except X.ExprError as ex:
            raise _error("%s: %s" % (w, ex))
        for n in X.names(tree):
            if n not in dict(kernel.inputs) or n in kernel.masks:
                raise _error("%s: %r is not a limb input" % (w, n))
        out.append((tree, cond["abs_le"].strip()))
    return out


def _read_ball_set(e, kernel, raw, where):
    IV._require(raw, ("center", "radius", "set", "balls"), where)
    e.center, e.radius = raw["center"], raw["radius"]
    cl = IV._limb_output(kernel, e.center, where, "center")
    if IV._limb_output(kernel, e.radius, where, "radius") != 1 or e.center == e.radius:
        raise _error("%s: the radius must be another output of one limb" % where)
    e.op = raw["set"]
    if e.op not in SET_OPS:
        raise _error("%s: set must be union or intersection, got %r" % (where, e.op))
    e.balls = IV._ball_names(kernel, raw, where)
    if len(e.balls) != 2:
        raise _error("%s: ball_set takes two balls" % where)
    for b, (c, _r) in e.balls.items():
        if kernel.limbs_of(c) != cl:
            raise _error("%s: the center of %s has %d limbs and the output's %d"
                         % (where, b, kernel.limbs_of(c), cl))
    e.of = [e.center, e.radius]


def _read_ball_splits(e, kernel, raw, where):
    IV._require(raw, ("parts", "from"), where)
    fr = raw["from"]
    if not isinstance(fr, dict) or set(fr) != {"center", "radius"}:
        raise _error("%s: from must be {\"center\": INPUT, \"radius\": INPUT}" % where)
    e.from_ball = (fr["center"], fr["radius"])
    if e.from_ball not in kernel.ball_requires:
        raise _error("%s: from (%s, %s) has no requirement ball(%s, %s)"
                     % ((where,) + e.from_ball + e.from_ball))
    k = kernel.limbs_of(e.from_ball[0])
    parts = raw["parts"]
    if not isinstance(parts, list) or len(parts) != 2:
        raise _error("%s: parts must be a list of two balls" % where)
    e.parts = []
    seen = []
    for j, p in enumerate(parts):
        if not isinstance(p, dict) or set(p) != {"center", "radius"}:
            raise _error("%s: part %d must be {\"center\": OUTPUT, \"radius\": OUTPUT}"
                         % (where, j))
        if IV._limb_output(kernel, p["center"], where, "part %d center" % j) != k:
            raise _error("%s: part %d center must have the limbs of the ball's center (%d)"
                         % (where, j, k))
        if IV._limb_output(kernel, p["radius"], where, "part %d radius" % j) != 1:
            raise _error("%s: part %d radius must be an output of one limb" % (where, j))
        for n in (p["center"], p["radius"]):
            if n in seen:
                raise _error("%s: the output %s is named twice" % (where, n))
            seen.append(n)
        e.parts.append((p["center"], p["radius"]))
    e.of = seen


READERS = {"certain": _read_relation, "trit": _read_relation, "ball_set": _read_ball_set,
           "ball_splits": _read_ball_splits}


def _sets_text(e):
    if e.over == "intervals":
        return IV._iv_text(e.sets)
    return ", ".join("%s=[%s +- %s]" % (n, c, r) for n, (c, r) in e.sets.items())


def label(e):
    k = e.kind
    if k in ("certain", "trit"):
        out = ", ".join(e.of) if k == "certain" else "yes %s, no %s" % (e.yes, e.no)
        s = "%s(%s) %s(%s) over %s" % (k, out, e.rel, ", ".join(e.args), _sets_text(e))
        if e.exact:
            s += ", exact"
        if e.exact_when_abs:
            s += ", exact when %s" % " and ".join("|%s| <= Omega" % t for _tr, t in e.exact_when_abs)
        return s
    if k == "ball_set":
        return "ball_set(%s, %s) %s of %s" % (e.center, e.radius, e.op, ", ".join(
            "%s=[%s +- %s]" % (b, c, r) for b, (c, r) in e.balls.items()))
    if k == "ball_splits":
        return "ball_splits [%s +- %s], [%s +- %s] of [%s +- %s]" % (
            e.parts[0] + e.parts[1] + e.from_ball)
    raise _error("no label for %s" % k)


# ---------------------------------------------------------------------------
# Plans

def plan_entry(pl, e, claims):
    """The fields of the plan entry of e (check.Plan) in pl's format."""
    sl, os_ = pl.in_slices, pl.out_slices
    c = {}
    if e.kind in ("certain", "trit"):
        sets = {}
        for n, (a, b) in e.sets.items():
            if isinstance(e.sets[n], IV.Stored):
                # A set named by its stored pair, the round-up interval's (upward.py).
                sets[n] = ("up", sl[a], sl[b])
                continue
            sets[n] = ("iv", sl[a], sl[b]) if e.over == "intervals" else ("ball", sl[a], sl[b][0])
        c.update(rel=e.rel, args=list(e.args), sets=sets, exact=e.exact,
                 point=sl[e.point] if e.point else None)
        if e.kind == "trit":
            c.update(yes=os_[e.yes][0], no=os_[e.no][0])
        else:
            c["out"] = os_[e.of[0]][0]
        c["conds"] = _compile_abs_le(pl, e.exact_when_abs) if e.exact_when_abs else None
    elif e.kind == "ball_set":
        c.update(op=e.op, center=os_[e.center], radius=os_[e.radius][0],
                 balls=[(sl[cn], sl[rn][0]) for cn, rn in e.balls.values()])
    elif e.kind == "ball_splits":
        c.update(given=(sl[e.from_ball[0]], sl[e.from_ball[1]][0]),
                 parts=[(os_[a], os_[b][0]) for a, b in e.parts])
    return c


def _compile_abs_le(pl, conds):
    """[(holds(x), text)]: |EXPR| <= Omega on finite input limbs, decided with integers."""
    out = []
    fmt = pl.fmt
    for tree, text in conds:
        src, s = X.compile_tree(tree, pl._leaf)
        fn = X.make_function(["x"], src)
        d = s - fmt.qmin
        if d >= 0:
            holds = (lambda x, fn=fn, d=d: (abs(fn(x)) << d) <= fmt.omega)
        else:
            holds = (lambda x, fn=fn, d=-d: abs(fn(x)) <= (fmt.omega << d))
        out.append((holds, "|%s| <= Omega" % text))
    return out


# ---------------------------------------------------------------------------
# The sets of a line

def _lt(a, b):
    return XT.x_cmp(a, 0, b, 0) < 0


def _le(a, b):
    return XT.x_cmp(a, 0, b, 0) <= 0


def set_of(fmt, x, spec):
    """(set, class, finite, special, ball) of a set operand: EMPTY or ("nonempty", L, U); its
    class for the statistics; finite: a bounded interval or a finite ball; special: the empty set
    or the whole line; ball: (center value, radius) of a finite ball, else None."""
    if spec[0] in ("iv", "up"):
        _k, (alo, ahi), (blo, bhi) = spec
        # "up": the stored pair (u, n) of the round-up interval (upward.py), [-n, u] or empty.
        st = (IV.interval_state(fmt, x[alo:ahi], x[blo:bhi]) if spec[0] == "iv"
              else IV.upward_state(x[alo], x[blo]))
        if st[0] == "empty":
            return EMPTY, "empty", False, True, None
        L, U = st[1], st[2]
        if L == NINF and U == INF:
            return ("nonempty", L, U), "whole line", False, True, None
        if type(L) is not int or type(U) is not int:
            return ("nonempty", L, U), "half-line", False, False, None
        return ("nonempty", L, U), ("a point" if L == U else "bounded"), True, False, None
    _k, (clo, chi), ri = spec
    stt = XT.ball_state(fmt, x[clo:chi], x[ri])
    if stt == "empty":
        return EMPTY, "empty", False, True, None
    if stt == "whole":
        return ("nonempty", NINF, INF), "whole line", False, True, None
    cv, r = sum(x[clo:chi]), x[ri]
    return ("nonempty", cv - r, cv + r), ("a point" if r == 0 else "finite"), True, False, (cv, r)


def point_of(fmt, x, sl):
    """The value of a point (one limb, or a canonical pair): an integer at scale qmin, or INF,
    NINF, NAN."""
    lo, hi = sl
    return IV.bound_value(fmt, x[lo:hi])


def relation(rel, vals):
    """(R, N): whether the relation holds of the sets (for every choice of members, for lt, le
    and eq), and, for lt, le, eq and member, whether it fails for every choice (None for the
    others).  vals: the arguments, each a set (EMPTY or ("nonempty", L, U)) or, for member, the
    point's value first."""
    if rel in ORDER_RELS:
        A, B = vals
        if A[0] == "empty" or B[0] == "empty":
            return False, False
        La, Ua, Lb, Ub = A[1], A[2], B[1], B[2]
        if rel == "lt":
            return _lt(Ua, Lb), _le(Ub, La)
        if rel == "le":
            return _le(Ua, Lb), _lt(Ub, La)
        # eq: every member of A equals every member of B: both the same point; fails for every
        # choice: no common member.
        same = La == Ua == Lb == Ub
        return same, _lt(Ua, Lb) or _lt(Ub, La)
    if rel == "member":
        t, A = vals
        r = type(t) is int and A[0] != "empty" and _le(A[1], t) and _le(t, A[2])
        return r, not r
    if rel in ONE_RELS:
        (A,) = vals
        if rel == "empty":
            return A[0] == "empty", None
        return A[0] != "empty" and A[1] == NINF and A[2] == INF, None
    A, B = vals
    if rel == "subset":
        if A[0] == "empty":
            return True, None
        return B[0] != "empty" and _le(B[1], A[1]) and _le(A[2], B[2]), None
    if rel == "equal":
        if A[0] == "empty" or B[0] == "empty":
            return A[0] == B[0], None
        return A[1] == B[1] and A[2] == B[2], None
    if rel == "interior":
        if A[0] == "empty":
            return True, None
        if B[0] == "empty":
            return False, None
        lo = B[1] == NINF or _lt(B[1], A[1])
        hi = B[2] == INF or _lt(A[2], B[2])
        return lo and hi, None
    # disjoint
    if A[0] == "empty" or B[0] == "empty":
        return True, None
    return _lt(A[2], B[1]) or _lt(B[2], A[1]), None


def _margin(rel, vals, holds):
    """The distance of the line from the boundary of the relation (an integer at scale qmin), for
    an answer not given: of the side that holds (holds True) or that fails for every choice."""
    if rel == "member":
        t, A = vals
        return min(abs(t - A[1]), abs(A[2] - t))
    if rel in ORDER_RELS:
        A, B = vals
        if rel == "eq" and not holds:
            return max(B[1] - A[2], A[1] - B[2])
        return (B[1] - A[2]) if holds else (A[1] - B[2])
    if rel == "subset":
        A, B = vals
        return min(A[1] - B[1], B[2] - A[2])
    return None


def _band(es, fmt, rel, vals, holds, balls, point, line):
    """The statistics of an answer not given (not claimed): its margin relative to the largest
    radius and to u^2 times the distance of the centers (or of the point and the center)."""
    for s in vals:
        if s == EMPTY or any(type(v) is not int for v in (s[1:] if isinstance(s, tuple) else (s,))):
            return
    m = _margin(rel, vals, holds)
    if m is None:
        return
    m = abs(m)
    rmax = max((b[1] for b in balls if b is not None), default=0)
    if rmax:
        es.track_max(BAND_RADIUS, (m, rmax), line)
    cs = [b[0] for b in balls if b is not None]
    if point is not None:
        cs.append(point)
    if len(cs) == 2:
        d = abs(cs[0] - cs[1])
        if d:
            # u^2 = 2^(2 - 2p): margin / (u^2 d) = margin 2^(2p - 2) / d.
            es.track_max(BAND_DISTANCE, (m << (2 * fmt.p - 2), d), line)
        # In the units of architecture.md's band, 2e + G, with its estimate of e (3 u^2 d plus
        # twice the smallest normal number) and G the gap of T at the larger of the radius and the
        # distance: m / (6 u^2 d + 4 lambda + G), times 2^(2p - 2) above and below. Near the top
        # of the range the radius e of add_ball_2_2 (or the difference itself) overflows and the
        # band is the whole line: measured where the distance and the radius are below Omega/4,
        # the bound of the suspicious cases.
        if 4 * d <= fmt.omega and 4 * rmax <= fmt.omega:
            g = F.ulp(fmt, min(max(rmax, d, 1), fmt.omega))
            sh = 2 * fmt.p - 2
            es.track_max(BAND_UNITS, (m << sh, 6 * d + ((4 * fmt.lam + g) << sh)), line)


# ---------------------------------------------------------------------------
# The judges (extended.KINDS)

def _relation_line(pl, c, es, x):
    """(R, N, vals, special, all_finite, balls, point) of a line, with the classes counted."""
    fmt = pl.fmt
    vals, balls = [], []
    special = False
    all_finite = True
    infos = {}
    for n, spec in c["sets"].items():
        s, cls, fin, sp, ball = set_of(fmt, x, spec)
        infos[n] = s
        es.count(CLASS % (n, cls))
        special = special or sp
        all_finite = all_finite and fin
        balls.append(ball)
    point = None
    for a in c["args"]:
        if a == "0":
            vals.append(("nonempty", 0, 0))
        elif a in infos:
            vals.append(infos[a])
        else:
            point = point_of(fmt, x, c["point"])
            es.count(CLASS % (a, "finite" if type(point) is int else
                              "NaN" if point == NAN else "infinite"))
            if type(point) is not int:
                special = True
                all_finite = False
            vals.append(point)
    R, N = relation(c["rel"], vals)
    if special:
        es.count(SPECIAL)
    if all_finite:
        es.count(ALL_FINITE)
    return R, N, vals, special, all_finite, balls, (point if type(point) is int else None)


def _exactness(c, es, x, special, all_finite):
    """Where the answer is claimed exact: 'exact', 'special' or 'exact_when', or None."""
    if c["exact"]:
        return "exact"
    if special:
        return "special"
    if c["conds"] is not None and all_finite:
        bad = [t for h, t in c["conds"] if not h(x)]
        for t in bad:
            es.count(EW_FAILS + t)
        if not bad:
            es.count(EW_HOLDS)
            return "exact_when"
    return None


def k_certain(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """The mask is true only if the relation holds; exactly when it holds when an operand is not
    finite, with exact, and with exact_when on finite operands whose conditions hold."""
    es.applicable += 1
    out = []
    fail = XT._failer(es, out)
    R, _N, vals, special, all_finite, balls, point = _relation_line(pl, c, es, x)
    m = z[c["out"]]
    es.count(HOLDS if R else NOT_HOLDS)
    es.count(MASK_TRUE if m else MASK_FALSE)
    if m and not R:
        fail("sound", "the mask is true and %s does not hold" % c["rel"])
    how = _exactness(c, es, x, special, all_finite)
    if how is not None:
        if R and not m:
            fail(how, "the mask is false and %s holds (claimed exact: %s)" % (c["rel"], how))
    elif R and not m:
        es.count(FALSE_HOLDS)
        _band(es, pl.fmt, c["rel"], vals, True, balls, point, line)
    return out


def k_trit(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """yes only if the relation holds for every choice, no only if it fails for every choice,
    never both; each exactly so where the claim is exact."""
    es.applicable += 1
    out = []
    fail = XT._failer(es, out)
    R, N, vals, special, all_finite, balls, point = _relation_line(pl, c, es, x)
    yes, no = z[c["yes"]], z[c["no"]]
    es.count(HOLDS if R else FAILS_ALL if N else NEITHER)
    es.count(ANS_YES if yes and not no else ANS_NO if no and not yes else
             ANS_UNKNOWN if not yes and not no else "answer yes and no")
    if yes and no:
        fail("both", "yes and no are both true")
    if yes and not R:
        fail("yes", "yes, and %s does not hold for every choice" % c["rel"])
    if no and not N:
        fail("no", "no, and %s does not fail for every choice" % c["rel"])
    how = _exactness(c, es, x, special, all_finite)
    if how is not None:
        if R and not yes:
            fail(how, "%s holds for every choice and yes is false (claimed exact: %s)"
                 % (c["rel"], how))
        if N and not no:
            fail(how, "%s fails for every choice and no is false (claimed exact: %s)"
                 % (c["rel"], how))
    else:
        if R and not yes:
            es.count(UNDECIDED_HOLDS)
            _band(es, pl.fmt, c["rel"], vals, True, balls, point, line)
        if N and not no:
            es.count(UNDECIDED_FAILS)
            _band(es, pl.fmt, c["rel"], vals, False, balls, point, line)
    return out


def _tokens(line):
    """The input limb tokens and the output tokens of a completed line, as written (they keep
    the signs of zeros)."""
    head, _, tail = line.partition(" -> ")
    return ([t for t in head.split()[2:] if not t.startswith("#")], tail.split())


def same_limb(fmt, a, b):
    """Two limbs written a and b are the same floating-point datum as the line protocol shows it:
    a NaN matches a NaN, any other limb the same value, and a zero the same sign."""
    va, vb = F.parse_limb(fmt, a), F.parse_limb(fmt, b)
    if va == NAN or vb == NAN:
        return va == vb
    if va != vb:
        return False
    return va != 0 or a.startswith("-") == b.startswith("-")


def _ball_info(fmt, limbs, r):
    stt = XT.ball_state(fmt, limbs, r)
    if stt == "finite":
        cv = sum(limbs)
        return stt, ("nonempty", cv - r, cv + r), (cv, r)
    if stt == "whole":
        return stt, ("nonempty", NINF, INF), None
    return stt, (EMPTY if stt == "empty" else None), None


STATE_NAME = {"empty": "empty", "whole": "whole line", "finite": "finite"}


def k_ball_set(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """architecture.md, "Claims of the enclosure interface: the set operations of a ball": Z a
    canonical ball containing every member of X or Y (of both); the empty set, and the operands
    as they are, as the claim says (the clause that gives X when X is not itself special)."""
    fmt = pl.fmt
    es.applicable += 1
    out = []
    fail = XT._failer(es, out)
    (xc, xr), (yc, yr) = c["balls"]
    sx, X_, bx = _ball_info(fmt, x[xc[0]:xc[1]], x[xr])
    sy, Y_, by = _ball_info(fmt, x[yc[0]:yc[1]], x[yr])
    es.count(SET_PAIR % (STATE_NAME[sx], STATE_NAME[sy]))
    ins, outs = _tokens(line)
    cz = c["center"]
    zt = outs[cz[0]:cz[1]] + [outs[c["radius"]]]
    xt = ins[xc[0]:xc[1]] + [ins[xr]]
    yt = ins[yc[0]:yc[1]] + [ins[yr]]
    if sx == sy == "whole" and any(t.startswith("-") for t in xt[:-1]) != any(
            t.startswith("-") for t in yt[:-1]):
        es.count(SET_ZERO_SIGNS)
    if sx == sy == "finite":
        (L1, U1), (L2, U2) = X_[1:], Y_[1:]
        if _lt(U1, L2) or _lt(U2, L1):
            es.count(SET_DISJOINT)
        elif U1 == L2 or U2 == L1:
            es.count(SET_TOUCH)
        elif (_le(L1, L2) and _le(U2, U1)) or (_le(L2, L1) and _le(U1, U2)):
            es.count(SET_NESTED)
        else:
            es.count(SET_OVERLAP)
    sz, Z_, bz = _ball_info(fmt, z[cz[0]:cz[1]], z[c["radius"]])
    if sz is None:
        fail("canonical", "the result is not a canonical ball")
        return out
    es.count(Z_STATE % STATE_NAME[sz])
    union = c["op"] == "union"
    special = "empty" if union else "whole"
    # The operands as they are: Y when X is special; X when Y is special and X is not.
    if sx == special:
        es.count(SET_Y_AS_IS)
        if not all(same_limb(fmt, a, b) for a, b in zip(zt, yt)):
            fail("Y as it is", "X is %s and the result (%s) is not Y as it is (%s)"
                 % (STATE_NAME[special], " ".join(zt), " ".join(yt)))
    elif sy == special:
        es.count(SET_X_AS_IS)
        if not all(same_limb(fmt, a, b) for a, b in zip(zt, xt)):
            fail("X as it is", "Y is %s, X is not, and the result (%s) is not X as it is (%s)"
                 % (STATE_NAME[special], " ".join(zt), " ".join(xt)))
    # Emptiness.
    if union:
        want_empty = sx == "empty" and sy == "empty"
        if (sz == "empty") != want_empty:
            fail("empty", "the result is %sempty, and %s" % (
                "" if sz == "empty" else "not ",
                "both operands are" if want_empty else "an operand is not"))
    elif (sx == "empty" or sy == "empty") and sz != "empty":
        fail("empty", "an operand is empty and the intersection is not")
    # Containment of the members due.
    due = []
    if union:
        due = [s for s in (X_, Y_) if s != EMPTY]
    elif X_ != EMPTY and Y_ != EMPTY:
        lo = X_[1] if _le(Y_[1], X_[1]) else Y_[1]
        hi = X_[2] if _le(X_[2], Y_[2]) else Y_[2]
        if _le(lo, hi):
            due = [("nonempty", lo, hi)]
    if sz == "finite":
        for s in due:
            if not (_le(Z_[1], s[1]) and _le(s[2], Z_[2])):
                fail("containment", "a member of %s is not a member of the result" % (
                    "X or Y" if union else "X and Y"))
                break
        else:
            if due and all(type(v) is int for s in due for v in s[1:]):
                lo = min(s[1] for s in due)
                hi = max(s[2] for s in due)
                need = max(bz[0] - lo, hi - bz[0])
                if need > 0:
                    es.track_max(SET_RATIO, (bz[1], need), line)
    elif sz == "empty" and due:
        fail("containment", "the result is empty and X %s Y has members" % (
            "or" if union else "and"))
    elif sz == "whole" and sx == sy == "finite":
        es.count(SET_WHOLE_FROM_FINITE)
    return out


def k_ball_splits(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """Both parts canonical; the empty set twice, the whole line twice; for a finite ball of
    center c and radius r, [c - r, c] inside the first part and [c, c + r] inside the second."""
    fmt = pl.fmt
    es.applicable += 1
    out = []
    fail = XT._failer(es, out)
    (clo, chi), ri = c["given"]
    sx, _X, bx = _ball_info(fmt, x[clo:chi], x[ri])
    es.count(SPLIT_X % STATE_NAME[sx])
    if sx == "finite" and bx[1] == 0:
        es.count(SPLIT_ZERO)
    parts = []
    for j, ((a, b), rr) in enumerate(c["parts"]):
        s, P, bp = _ball_info(fmt, z[a:b], z[rr])
        parts.append((s, P, bp))
        if s is None:
            fail("canonical", "the %s part is not a canonical ball" % ("first", "second")[j])
    if any(p[0] is None for p in parts):
        return out
    for j, (s, _P, _bp) in enumerate(parts):
        es.count(SPLIT_PART % (("first", "second")[j], STATE_NAME[s]))
    if sx in ("empty", "whole"):
        for j, (s, _P, _bp) in enumerate(parts):
            if s != sx:
                fail(STATE_NAME[sx], "%s gives the %s part %s" % (
                    STATE_NAME[sx], ("first", "second")[j], STATE_NAME[s]))
        return out
    cv, r = bx
    for j, (lo, hi) in enumerate(((cv - r, cv), (cv, cv + r))):
        s, P, bp = parts[j]
        name = ("first", "second")[j]
        if s == "whole":
            continue
        if s == "empty" or not (P[1] <= lo and hi <= P[2]):
            fail("%s part" % name, "the %s part does not contain [%s, %s]" % (
                name, F.to_hex(lo, fmt.qmin), F.to_hex(hi, fmt.qmin)))
        elif r:
            es.track_max(SPLIT_RATIO, (2 * bp[1], r), line)
    return out


EXT_KINDS = {"certain": k_certain, "trit": k_trit, "ball_set": k_ball_set,
             "ball_splits": k_ball_splits}
XT.KINDS.update(EXT_KINDS)
