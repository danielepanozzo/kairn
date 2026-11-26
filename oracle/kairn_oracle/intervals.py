"""The claims of the interval kernels: their reading and their judges.

architecture.md, "Claims of the interval kernels" and "Claims of the interval kernels: two limbs
and the enclosure interface", read with milestone2.md, "Notation and vocabulary", "Building blocks
on T", "Interval kernels" and "One enclosure interface".  What is new:

- the requirements interval(L, U) (the groups L and U are the bounds of a canonical interval: the
  empty set (+inf, -inf), or [l, h] with no NaN bound, l <= h, l < +inf, h > -inf, each bound a
  number of the format or an infinity, for two limbs canonical) and not_nan(NAME);
- the kinds outward, makes_interval, encloses_interval (I1 to I6), set_bound, interval_set,
  ball_of_interval, interval_of_ball and splits; encloses with no ball (the operands are points);
  makes_ball from the bounds of an interval (with midpoint_when); zero_factor on bound and rounded;
- the constants of a claim, rel and abs: the language of const up(EXPR) (integers, u, eta,
  unit(K), tiny(K), + - * /, parentheses, integer powers) with up(EXPR) inside, the smallest
  number of the format not below EXPR;
- in the finite domain, an entry about an output group other than the first holds where that
  group's leading limb is finite (judge_by_groups); an entry with if=MASK is read as before;
- the round-up interval (upward.py): a set named by its stored pair {"upper": U, "nlower": N}
  (Stored, upward_state) in intervals and as the outputs of encloses_interval, interval_set and
  makes_interval, and the numbers of encloses_interval.

Members of an interval are real numbers: [1, +inf] does not contain +inf.  The exact range of a
set over intervals (or balls) is computed by interval arithmetic in the extended reals, each name
occurring once: a sum adds lower bounds and upper bounds, a negation exchanges them, a product
takes the least and the greatest of the four products of bounds with 0 * inf = 0
(architecture.md: "the sums and differences of bounds, the opposites of the bounds exchanged for
-x, and for x*y the least and the greatest of the four products of a bound of x and a bound of y
taken with 0 * inf = 0").  Finite values are integers at a known scale, the infinities and NaN
the strings of fmt.py, so every verdict is decided with Python integers; the constants of a claim
are exact Fractions, compared after clearing denominators.  The sign of a zero is never judged.
"""

import re
from fractions import Fraction

from . import directed as D
from . import expr as X
from . import extended as XT
from . import fmt as F

INF, NINF, NAN = F.POS_INF, F.NEG_INF, F.NAN
NAME = r"[A-Za-z_][A-Za-z0-9_]*"
INTERVAL_RE = re.compile(r"\s*interval\(\s*(%s)\s*,\s*(%s)\s*\)\s*\Z" % (NAME, NAME))
NOT_NAN_RE = re.compile(r"\s*not_nan\(\s*(%s)\s*\)\s*\Z" % NAME)
SIDES = ("below", "above")
SPECIALS = ("ieee1788", "ball")
SET_OPS = ("union", "intersection")
TIGHT_KINDS = ("exact", "rounded", "outward")


def _error(msg):
    from .claims import ClaimsError
    return ClaimsError(msg)


# The kinds this module reads, with their fields, and the fields it adds to kinds that exist.
KNOWN = {
    "outward": {"kind", "of", "side", "rel", "abs", "exact_when", "zero_factor"},
    # nlower (and numbers): the round-up interval's outputs named by their stored pair, upper and
    # nlower in place of lower and upper, and its numbers (upward.py).
    "makes_interval": {"kind", "lower", "upper", "nlower", "from"},
    "encloses_interval": {"kind", "lower", "upper", "nlower", "set", "intervals", "numbers",
                          "tight", "bounded_when", "bounded_exactly", "zero_factor"},
    "set_bound": {"kind", "of", "side", "set", "balls", "tight"},
    "interval_set": {"kind", "lower", "upper", "nlower", "set", "intervals"},
    # The conversions of two limbs (architecture.md, "Claims of the enclosure interface: the
    # conversions of two limbs"): finite_when of ball_of_interval, bounded_when (and the outward
    # tight) of interval_of_ball with bounds of two limbs, rel, abs and smallest_radius of makes_ball
    # from an interval.
    "ball_of_interval": {"kind", "center", "radius", "from", "special", "rel", "abs",
                         "smallest_radius", "finite_when"},
    "interval_of_ball": {"kind", "lower", "upper", "set", "balls", "tight", "bounded_when"},
    "splits": {"kind", "parts", "from"},
}
ADDED_FIELDS = {"bound": {"zero_factor"}, "rounded": {"zero_factor"},
                "makes_ball": {"midpoint_when", "rel", "abs", "smallest_radius"}}
EXTENDED_ONLY = tuple(k for k in KNOWN if k != "outward")


# ---------------------------------------------------------------------------
# Count names (the statistics the cross-checks' guards read, tests/crosscheck_guards.py)

OPS_EMPTY = "operands: an empty operand"
OPS_UNBOUNDED = "operands: nonempty, an unbounded operand"
OPS_BOUNDED = "operands: bounded"
RES_EMPTY = "result: empty"
RES_BOUNDED = "result: bounded"
RES_UNBOUNDED = "result: unbounded"
BOUNDED_TO_UNBOUNDED = "bounded operands, unbounded result"
I5_HOLDS = "bounded operands, bounded_when holds"
I5_FAILS = "bounded operands, bounded_when fails"
I5_NEAR_HOLDS = "bounded_when holds: largest max|member| / limit"
I5_NEAR_FAILS = "bounded_when fails: smallest max|member| / limit"
I6_APPLIES = "I6 applies: an operand is [0, 0]"
I6_UNBOUNDED = "I6 applies: [0, 0] against an unbounded operand"
SIDE_AT = "%s: at the directed rounding"
SIDE_ONE = "%s: one step beyond the directed rounding"
SIDE_STEPS = "%s: %d steps beyond the directed rounding"
SIDE_EXACT = "%s: range bound a number of the format"
SIDE_INEXACT = "%s: range bound not a number of the format"
SIDE_INFINITE = "%s: range bound infinite"
SIDE_OVER = "%s: range bound beyond Omega"
SIDE_ZERO = "%s: range bound zero"
SIDE_PL_HOLDS = "%s: product_large holds"
SIDE_PL_FAILS = "%s: product_large does not hold (within the steps)"
SIDE_RATIO = "%s: distance from the range bound / (rel*|bound| + abs)"
SIDE_RATIO_REL = ("%s: distance from the range bound / (rel*|bound| + abs), where the relative "
                  "term is the larger")
SIDE_RATIO_UNCLAIMED = ("%s: distance from the range bound / (rel*|bound| + abs), beside an "
                        "infinite bound (not claimed)")
SIDE_EW_HOLDS = "%s: exact_when holds"
SIDE_EW_FAILS = "%s: exact_when fails: "
OUT_RATIO = "|output - value| / (rel*|value| + abs)"
OUT_RATIO_REL = "|output - value| / (rel*|value| + abs), where the relative term is the larger"
OUT_VALUE_ZERO = "value zero"
OUT_EXACT = "output the value exactly"
OUT_INEXACT = "output not the value"
OUT_ABS_LARGER = "absolute term larger than the relative term"
OUT_EW_HOLDS = "exact_when holds"
OUT_EW_FAILS = "exact_when fails: "
OUT_ZERO_OPERAND = "a zero operand"
OUT_INF_OPERAND = "an infinite operand, none zero"
OUT_FINITE = "finite operands, finite output"
OUT_FINITE_INF = "finite operands, infinite output"
BALL_EMPTY = "ball: empty"
BALL_WHOLE = "ball: whole line"
BALL_FINITE = "ball: finite"
MAKE_INTERVAL = "given: an interval"
MAKE_POINT = "given: a point"
MAKE_UNBOUNDED = "given: an unbounded interval"
MAKE_NAN = "given: a NaN bound"
MAKE_REVERSED = "given: reversed bounds"
MAKE_EQUAL_INF = "given: equal infinities"
# The cells of the table of the constructors (architecture.md, "The constructors on every pair of
# values"), lo the row and hi the column, a and b finite; the guards ask for each (MAKE_CELLS).
MAKE_CELL = "given lo %s, hi %s"
MAKE_CELLS = tuple(MAKE_CELL % (r, c) + t for r in ("NaN", "-inf", "a", "+inf")
                   for c in ("NaN", "-inf", "b", "+inf")
                   for t in ((", a <= b", ", a > b") if (r, c) == ("a", "b") else ("",)))
# Two limbs: the same infinity with second limbs that are zeros of opposite signs ((+inf, 0) and
# (+inf, -0): the same infinity twice, the whole line), read from the line's text; and reversed
# bounds whose leading limbs are equal ((1, 2^-4) and (1, 0): the comparison of two limbs tells
# them, the leading limbs alone do not).
MAKE_INF_TAILS = "given the same infinity, second limbs zeros of opposite signs"
MAKE_REVERSED_LEAD = "given reversed bounds, equal leading limbs"
MID_HOLDS = "midpoint_when holds"
MID_FAILS = "midpoint_when fails"
X_EMPTY = "X: empty"
X_WHOLE = "X: whole line"
X_ABOVE = "X: half-line [l, +inf]"
X_BELOW = "X: half-line [-inf, h]"
X_BOUNDED = "X: bounded"
X_POINT = "X: a point"
X_ODD = "X: a bound an odd multiple of eta below 2N"
MID_RATIO = "|center - midpoint| / (rel*|midpoint| + abs)"
MID_EXACT = "center the midpoint exactly"
MID_INEXACT = "center not the midpoint"
SET_EMPTY_OPERAND = "an operand empty"
SET_BOTH_EMPTY = "both operands empty"
SET_DISJOINT = "nonempty operands, disjoint"
SET_TOUCH = "nonempty operands, touching (one common point)"
SET_OVERLAP = "nonempty operands, overlapping"
ZF_ZERO = "zero_factor: a zero operand"
ZF_ZERO_INF = "zero_factor: a zero against an infinite operand"
GROUP_NONFINITE = "the leading limb of its output is not finite: nothing claimed"
GROUP_TAIL = "a lower limb of its output is not finite: nothing claimed"


# ---------------------------------------------------------------------------
# The constants of a claim: rel and abs

_CTOKEN = re.compile(r"\s*(?:(\d+)|([-+*/^()])|([A-Za-z_][A-Za-z0-9_]*))")


def parse_const(text):
    """The tree of a constant of a claim: ("int", n), ("u",), ("eta",), ("unit", K), ("tiny", K),
    ("up", T), ("neg", T), and (op, A, B) for op in + - * / ^.  A unary minus binds less tightly
    than ^, ^ groups to the right, and the exponent of a power is an expression of integers."""
    if isinstance(text, bool) or not isinstance(text, (str, int)):
        raise _error("constant %r is not an expression" % (text,))
    s = str(text).strip()
    toks = []
    pos = 0
    while pos < len(s):
        m = _CTOKEN.match(s, pos)
        if m is None or m.end() == pos:
            raise _error("cannot read constant %r at %r" % (text, s[pos:]))
        pos = m.end()
        if m.group(1) is not None:
            toks.append(("int", int(m.group(1))))
        elif m.group(2) is not None:
            toks.append(("op", m.group(2)))
        else:
            toks.append(("word", m.group(3)))
    toks.append(("end", None))
    i = [0]

    def peek():
        return toks[i[0]]

    def take():
        t = toks[i[0]]
        i[0] += 1
        return t

    def sum_():
        a = prod_()
        while peek() in (("op", "+"), ("op", "-")):
            a = (take()[1], a, prod_())
        return a

    def prod_():
        a = unary_()
        while peek() in (("op", "*"), ("op", "/")):
            a = (take()[1], a, unary_())
        return a

    def unary_():
        if peek() == ("op", "-"):
            take()
            return ("neg", unary_())
        if peek() == ("op", "+"):
            take()
            return unary_()
        return pow_()

    def pow_():
        base = atom_()
        if peek() == ("op", "^"):
            take()
            e = unary_()
            if not _integers_only(e):
                raise _error("the exponent of a power must be an integer constant in %r" % text)
            return ("^", base, e)
        return base

    def atom_():
        t = take()
        if t[0] == "int":
            return ("int", t[1])
        if t[0] == "word":
            w = t[1]
            if w in ("u", "eta"):
                return (w,)
            if w in ("unit", "tiny"):
                if take() != ("op", "("):
                    raise _error("%s must be followed by '(' in %r" % (w, text))
                k = take()
                if k[0] != "word" or k[1] in ("u", "eta", "unit", "tiny", "up"):
                    raise _error("%s( ) takes the name of a kernel in %r" % (w, text))
                if take() != ("op", ")"):
                    raise _error("unbalanced parentheses in %r" % text)
                return (w, k[1])
            if w == "up":
                if take() != ("op", "("):
                    raise _error("up must be followed by '(' in %r" % text)
                a = sum_()
                if take() != ("op", ")"):
                    raise _error("unbalanced parentheses in %r" % text)
                return ("up", a)
            raise _error("constant %r names %r, which is not u, eta, unit( ), tiny( ) or up( )"
                         % (text, w))
        if t == ("op", "("):
            a = sum_()
            if take() != ("op", ")"):
                raise _error("unbalanced parentheses in %r" % text)
            return a
        raise _error("unexpected %r in constant %r" % (t[1] if t[1] is not None else "end", text))

    if peek()[0] == "end":
        raise _error("empty constant")
    tree = sum_()
    if peek()[0] != "end":
        raise _error("trailing input in constant %r" % text)
    return tree


def _integers_only(t):
    if t[0] == "int":
        return True
    if t[0] == "neg":
        return _integers_only(t[1])
    if t[0] in ("+", "-", "*", "/", "^"):
        return _integers_only(t[1]) and _integers_only(t[2])
    return False


def const_calls(t, out=None):
    """The kernels a constant names in unit( ) and tiny( )."""
    out = [] if out is None else out
    if t[0] in ("unit", "tiny"):
        out.append(t[1])
    elif t[0] in ("up", "neg"):
        const_calls(t[1], out)
    elif t[0] in ("+", "-", "*", "/", "^"):
        const_calls(t[1], out)
        const_calls(t[2], out)
    return out


def round_up_format(fmt, q):
    """The smallest number of the format not below the rational q, as a Fraction, or None when it
    is beyond Omega.  The numbers of the format are integers in units of eta, so it is the
    smallest one not below ceil(q / eta)."""
    q = Fraction(q)
    t = q * (Fraction(1 << -fmt.qmin) if fmt.qmin < 0 else Fraction(1, 1 << fmt.qmin))
    n = -((-t.numerator) // t.denominator)
    r = F.rdir(fmt, n, fmt.qmin, True)
    if abs(r) > fmt.omega:
        return None
    eta = Fraction(1, 1 << -fmt.qmin) if fmt.qmin < 0 else Fraction(1 << fmt.qmin)
    return r * eta


def eval_const(tree, fmt, unit_tiny, text=""):
    """The exact value of a constant in format fmt (a Fraction).  unit_tiny(K) gives (unit, tiny)
    of kernel K.  A division by zero, or an up( ) beyond Omega, is an error of the claims."""
    u = Fraction(1, 1 << fmt.p)
    eta = Fraction(1, 1 << -fmt.qmin) if fmt.qmin < 0 else Fraction(1 << fmt.qmin)

    def ev(t):
        k = t[0]
        if k == "int":
            return Fraction(t[1])
        if k == "u":
            return u
        if k == "eta":
            return eta
        if k == "unit":
            return unit_tiny(t[1])[0]
        if k == "tiny":
            return unit_tiny(t[1])[1]
        if k == "neg":
            return -ev(t[1])
        if k == "up":
            r = round_up_format(fmt, ev(t[1]))
            if r is None:
                raise _error("constant %s: up( ) of %s is beyond the overflow threshold of %s"
                             % (text, _short_frac(ev(t[1])), fmt.name))
            return r
        a, b = ev(t[1]), ev(t[2])
        if k == "+":
            return a + b
        if k == "-":
            return a - b
        if k == "*":
            return a * b
        if k == "/":
            if b == 0:
                raise _error("constant %s: division by zero in %s" % (text, fmt.name))
            return a / b
        if b.denominator != 1 or abs(b) > 1 << 16:
            raise _error("constant %s: a power %s that is not a small integer" % (text, b))
        if a == 0 and b < 0:
            raise _error("constant %s: division by zero in %s" % (text, fmt.name))
        return a ** int(b)

    return ev(tree)


def _short_frac(f):
    s = str(f)
    return s if len(s) < 60 else s[:28] + "..." + s[-28:]


# ---------------------------------------------------------------------------
# Requirements

def read_requirement(kernel, r, limbs):
    """interval(L, U) and not_nan(NAME), both of the extended domain: appended to
    kernel.requires as ("interval", L, U) and ("not_nan", NAME); True when r is one of them."""
    m = INTERVAL_RE.match(r)
    if m and m.group(1) in kernel.input_names and m.group(2) in kernel.input_names \
            and not {m.group(1), m.group(2)} & kernel.masks:
        lo, hi = m.group(1), m.group(2)
        if not kernel.extended:
            raise _error("%s: requirement %r belongs to the extended domain" % (kernel.name, r))
        if lo == hi:
            raise _error("%s: requirement %r: the two bounds are the same input" % (kernel.name, r))
        if limbs[lo] != limbs[hi] or limbs[lo] not in (1, 2):
            raise _error("%s: requirement %r: the bounds must have one limb each or two each"
                         % (kernel.name, r))
        used = {n for t in kernel.interval_requires for n in t}
        if lo in used or hi in used:
            raise _error("%s: requirement %r shares an input with another interval"
                         % (kernel.name, r))
        kernel.requires.append(("interval", lo, hi))
        kernel.interval_requires.append((lo, hi))
        return True
    m = NOT_NAN_RE.match(r)
    if m and m.group(1) in kernel.input_names and m.group(1) not in kernel.masks:
        n = m.group(1)
        if not kernel.extended:
            raise _error("%s: requirement %r belongs to the extended domain" % (kernel.name, r))
        if limbs[n] > 2:
            raise _error("%s: requirement %r: not_nan() is for an input of one or two limbs"
                         % (kernel.name, r))
        if ("not_nan", n) in kernel.requires:
            raise _error("%s: requirement %r is listed twice" % (kernel.name, r))
        kernel.requires.append(("not_nan", n))
        return True
    return False


def finish_requirements(kernel):
    """Once every requirement is read: not_nan() of a two-limb input needs canonical() of it, and
    an input of an interval is in no ball."""
    can = {r[1] for r in kernel.requires if r[0] == "canonical"}
    limbs = dict(kernel.inputs)
    for r in kernel.requires:
        if r[0] == "not_nan" and limbs[r[1]] == 2 and r[1] not in can:
            raise _error("%s: requirement not_nan(%s): a two-limb input must also be canonical()"
                         % (kernel.name, r[1]))
    inball = {n for b in kernel.ball_requires for n in b}
    for lo, hi in kernel.interval_requires:
        if lo in inball or hi in inball:
            raise _error("%s: interval(%s, %s) shares an input with a ball" % (kernel.name, lo, hi))


# ---------------------------------------------------------------------------
# Reading the entries

def _limb_output(kernel, n, where, what):
    outs = dict(kernel.outputs)
    if not isinstance(n, str) or n not in outs or n in kernel.masks:
        raise _error("%s: %s %r is not a limb output" % (where, what, n))
    return outs[n]


def _limb_input(kernel, n, where, what):
    ins = dict(kernel.inputs)
    if not isinstance(n, str) or n not in ins or n in kernel.masks:
        raise _error("%s: %s %r is not a limb input" % (where, what, n))
    return ins[n]


def _require(raw, fields, where):
    for f in fields:
        if f not in raw:
            raise _error("%s: missing %s" % (where, f))


def _out_fields(raw):
    """The fields naming the outputs of an interval: lower and upper, or upper and nlower, the
    stored pair of the round-up interval (upward.py)."""
    return ("upper", "nlower") if "nlower" in raw else ("lower", "upper")


def _bound_outputs(e, kernel, raw, where):
    """e.lower, e.upper and e.nlower (None but for a stored pair) of the outputs of an interval,
    and the limbs of the first and of the second."""
    if "nlower" in raw:
        from . import upward as UP
        return UP.stored_outputs(e, kernel, raw, where)
    e.lower, e.upper, e.nlower = raw["lower"], raw["upper"], None
    return (_limb_output(kernel, e.lower, where, "lower"),
            _limb_output(kernel, e.upper, where, "upper"))


def _outs_of(e):
    """The outputs an entry about an interval names, in the order of its fields."""
    return [e.lower, e.upper] if e.nlower is None else [e.upper, e.nlower]


def _outs_text(e):
    return ("%s, %s" % (e.lower, e.upper) if e.nlower is None
            else "upper %s, nlower %s" % (e.upper, e.nlower))


def _true_flag(raw, field, where):
    """A field written only when it is so: absent, or true."""
    if field not in raw:
        return False
    if raw[field] is not True:
        raise _error("%s: %s is written only when it is true, got %r" % (where, field, raw[field]))
    return True


def _interval_of(kernel, spec, where, what="from", stored=False):
    """{lower: L, upper: U}: the inputs of an interval() requirement; with stored, also
    {upper: U, nlower: N}, the inputs of an upward() requirement (a Stored pair, upward.py)."""
    if stored and isinstance(spec, dict) and set(spec) == {"upper", "nlower"}:
        from . import upward as UP
        return UP.stored_pair(kernel, spec, where, what)
    if not isinstance(spec, dict) or set(spec) != {"lower", "upper"}:
        raise _error("%s: %s must be {\"lower\": INPUT, \"upper\": INPUT}" % (where, what))
    pair = (spec["lower"], spec["upper"])
    if pair not in kernel.interval_requires:
        raise _error("%s: %s (%s, %s) is not an interval() requirement of the kernel"
                     % (where, what, pair[0], pair[1]))
    return pair


def _interval_names(kernel, raw, where, count=None):
    iv = raw["intervals"]
    if not isinstance(iv, dict) or not iv:
        raise _error("%s: intervals must be a nonempty object" % where)
    if count is not None and len(iv) != count:
        raise _error("%s: intervals must name %d intervals, got %d" % (where, count, len(iv)))
    ins = dict(kernel.inputs)
    out = {}
    for name, spec in iv.items():
        if not re.fullmatch(NAME, name) or name in ins or name in X.FUNCTIONS:
            raise _error("%s: bad interval name %r (it must not be an input name)" % (where, name))
        pair = _interval_of(kernel, spec, where, "interval %s" % name, stored=True)
        if pair in out.values():
            raise _error("%s: interval %s is another name of the same bounds" % (where, name))
        out[name] = pair
    return out


def _ball_names(kernel, raw, where):
    balls = raw["balls"]
    if not isinstance(balls, dict) or not balls:
        raise _error("%s: balls must be a nonempty object" % where)
    ins = dict(kernel.inputs)
    out = {}
    for b, spec in balls.items():
        if not isinstance(spec, dict) or set(spec) != {"center", "radius"}:
            raise _error("%s: ball %r must be {center, radius}" % (where, b))
        if not re.fullmatch(NAME, b) or b in ins or b in X.FUNCTIONS:
            raise _error("%s: bad ball name %r (it must not be an input name)" % (where, b))
        pair = (spec["center"], spec["radius"])
        if pair not in kernel.ball_requires:
            raise _error("%s: ball %s over (%s, %s) has no requirement ball(%s, %s)"
                         % (where, b, pair[0], pair[1], pair[0], pair[1]))
        if pair in out.values():
            raise _error("%s: ball %s is another name of the same ball" % (where, b))
        out[b] = pair
    return out


def _set_over(text, names, where):
    """The tree of a set over the given names, each exactly once, without abs (the range is then
    that of interval arithmetic, exactly)."""
    if not isinstance(text, str):
        raise _error("%s: set must be an expression" % where)
    try:
        tree = X.parse(text)
    except X.ExprError as ex:
        raise _error("%s: set: %s" % (where, ex))
    nm = X.names(tree)
    for n in nm:
        if n not in names:
            raise _error("%s: set names %r, which is not one of %s" % (where, n, ", ".join(names)))
    for n in names:
        if nm.count(n) != 1:
            raise _error("%s: %s must occur exactly once in set" % (where, n))
    if X.uses(tree, "abs"):
        raise _error("%s: abs() is not allowed in set" % where)
    return tree


def _conditions(kernel, lst, where):
    """[(tree, text, op, K)]: exact_when conditions, {"zero": EXPR} (EXPR = 0),
    {"zero_or_abs_gt": EXPR, "than": K} or {"zero_or_abs_ge": EXPR, "than": K}, EXPR over the
    limb inputs and their limbs NAME[I].  A nonempty list (absent when there is none)."""
    from .claims import eval_const as eval_k, format_u_eta
    if not isinstance(lst, list) or not lst:
        raise _error("%s: exact_when must be a nonempty list of conditions (absent when there is "
                     "none)" % where)
    ins = dict(kernel.inputs)
    out = []
    for j, cond in enumerate(lst):
        w = "%s: exact_when[%d]" % (where, j)
        if isinstance(cond, dict) and set(cond) == {"zero"}:
            op, k = "zero", None
        else:
            ops = [o for o in ("zero_or_abs_gt", "zero_or_abs_ge") if isinstance(cond, dict)
                   and o in cond]
            if len(ops) != 1 or set(cond) != {ops[0], "than"}:
                raise _error("%s must be {\"zero\": EXPR}, {\"zero_or_abs_gt\": EXPR, \"than\": K} "
                             "or {\"zero_or_abs_ge\": EXPR, \"than\": K}, got %r" % (w, cond))
            op, k = ops[0], cond["than"]
            u, eta = format_u_eta(F.Format(53, -1074, 971))
            if eval_k(k, u, eta) <= 0:
                raise _error("%s: than %r is not positive" % (w, k))
        text = cond[op]
        if not isinstance(text, str):
            raise _error("%s: %s must be an expression" % (w, op))
        try:
            tree = X.parse(text, limbs=True)
        except X.ExprError as ex:
            raise _error("%s: %s" % (w, ex))
        for n in X.names(tree):
            if n not in ins or n in kernel.masks:
                raise _error("%s: %r is not a limb input" % (w, n))
        for n, i in X.limb_refs(tree):
            if i >= ins[n]:
                raise _error("%s: %s[%d] is not a limb of %s, which has %d" % (w, n, i, n, ins[n]))
        out.append((tree, text.strip(), op, k))
    return out


def condition_text(text, op, k):
    if op == "zero":
        return "%s = 0" % text
    return "%s = 0 or |%s| %s %s" % (text, text, ">" if op == "zero_or_abs_gt" else ">=", k)


def _const_field(entry, raw, field, where):
    from .claims import ClaimsError
    try:
        tree = parse_const(raw[field])
    except ClaimsError as ex:
        # The reason names the kernel, the entry and the field.
        raise _error("%s: %s: %s" % (where, field, ex))
    entry.consts[field] = (tree, str(raw[field]).strip())


def _tight_rounded(raw, where, extra=()):
    t = raw
    if not isinstance(t, dict) or t.get("kind") != "rounded":
        raise _error("%s: tight must be {\"kind\": \"rounded\"} with an optional steps" % where)
    bad = set(t) - {"kind", "steps"} - set(extra)
    if bad:
        raise _error("%s: tight: unknown fields %s" % (where, sorted(bad)))
    steps = t.get("steps", 0)
    if not isinstance(steps, int) or isinstance(steps, bool) or steps < 0:
        raise _error("%s: tight: steps must be an integer >= 0, got %r" % (where, steps))
    return steps


def read_entry(entry, kernel, raw, where):
    """Read one entry of a kind of KNOWN into entry (its fields, of, label)."""
    kind = entry.kind
    if kind in EXTENDED_ONLY and not kernel.extended:
        raise _error("%s: this kind belongs to the extended domain, and the kernel has no "
                     "\"domain\": \"extended\"" % where)
    entry.iv = True
    entry.consts = {}
    READERS[kind](entry, kernel, raw, where)
    entry.label = label(entry)


def _read_outward(e, kernel, raw, where):
    _require(raw, ("of", "side", "rel", "abs"), where)
    e.of = kernel.resolve_outputs(raw["of"], where)
    if len(e.of) != 1 or e.of[0] in kernel.masks or kernel.limbs_of(e.of[0]) != 2:
        raise _error("%s: 'of' must name one 2-limb output" % where)
    if kernel.value_tree is None:
        raise _error("%s: the kernel has no value" % where)
    e.side = raw["side"]
    if e.side not in SIDES:
        raise _error("%s: side must be below or above, got %r" % (where, e.side))
    _const_field(e, raw, "rel", where)
    _const_field(e, raw, "abs", where)
    e.exact_when = _conditions(kernel, raw["exact_when"], where) if "exact_when" in raw else None
    e.zero_factor = _true_flag(raw, "zero_factor", where)
    t = kernel.value_tree
    if e.zero_factor:
        if not kernel.extended:
            raise _error("%s: zero_factor belongs to the extended domain" % where)
        if not (t[0] == "*" and t[1][0] == "name" and t[2][0] == "name" and t[1][1] != t[2][1]):
            raise _error("%s: zero_factor needs a value that is the product of two inputs" % where)
        e.factors = (t[1][1], t[2][1])
    if kernel.extended:
        # The output is never a NaN: the operands of the value are not NaN.
        for n in set(X.names(t)):
            if ("not_nan", n) not in kernel.requires:
                raise _error("%s: in the extended domain every operand of the value is not_nan(); "
                             "%s is not" % (where, n))


def _read_makes_interval(e, kernel, raw, where):
    _require(raw, _out_fields(raw) + ("from",), where)
    lo_l, hi_l = _bound_outputs(e, kernel, raw, where)
    if e.lower == e.upper:
        raise _error("%s: lower and upper are the same output" % where)
    fr = raw["from"]
    if not isinstance(fr, dict) or set(fr) != {"lower", "upper"}:
        raise _error("%s: from must be {\"lower\": INPUT, \"upper\": INPUT}" % where)
    e.from_lower, e.from_upper = fr["lower"], fr["upper"]
    a = _limb_input(kernel, e.from_lower, where, "from lower")
    b = _limb_input(kernel, e.from_upper, where, "from upper")
    if e.from_lower == e.from_upper:
        raise _error("%s: the given bounds are the same input" % where)
    if not (a == b == lo_l == hi_l) or a not in (1, 2):
        raise _error("%s: the given bounds and the outputs must have one limb each or two each"
                     % where)
    if a == 2:
        for n in (e.from_lower, e.from_upper):
            if ("canonical", n) not in kernel.requires:
                raise _error("%s: the two-limb bound %s must be canonical()" % (where, n))
    e.of = _outs_of(e)


def _read_encloses_interval(e, kernel, raw, where):
    _require(raw, _out_fields(raw) + ("set", "intervals", "tight", "bounded_when"), where)
    lo_l, hi_l = _bound_outputs(e, kernel, raw, where)
    if e.lower == e.upper or lo_l != hi_l or lo_l not in (1, 2):
        raise _error("%s: lower and upper must be two outputs of one limb each or two each" % where)
    e.intervals = _interval_names(kernel, raw, where)
    # numbers (the round-up interval, upward.py): one-limb inputs, each the members of
    # Interval(t), named in the set as the intervals are.
    e.numbers = []
    if "numbers" in raw:
        from . import upward as UP
        e.numbers = UP.read_numbers(kernel, raw["numbers"], e.intervals, where)
    e.set_text = str(raw["set"]).strip()
    e.set_tree = _set_over(raw["set"], list(e.intervals) + e.numbers, where)
    t = raw["tight"]
    if not isinstance(t, dict) or t.get("kind") not in TIGHT_KINDS:
        raise _error("%s: tight must have a kind exact, rounded or outward" % where)
    e.tight = t["kind"]
    e.steps, e.when, e.tight_exact = 0, None, None
    product = (e.set_tree[0] == "*" and e.set_tree[1][0] == "name"
               and e.set_tree[2][0] == "name" and not e.numbers)
    if e.tight == "exact":
        if set(t) != {"kind"}:
            raise _error("%s: tight exact has no other field" % where)
    elif e.tight == "rounded":
        e.steps = _tight_rounded(t, where, ("when",))
        if lo_l != 1:
            raise _error("%s: tight rounded is for bounds of one limb (a two-limb bound has no "
                         "rounding of its own)" % where)
        if "when" in t:
            if t["when"] != "product_large":
                raise _error("%s: tight: when must be product_large, got %r" % (where, t["when"]))
            if not product:
                raise _error("%s: tight: when product_large needs a set that is a product of two "
                             "intervals" % where)
            e.when = "product_large"
    else:
        bad = set(t) - {"kind", "rel", "abs", "exact_when"}
        if bad:
            raise _error("%s: tight: unknown fields %s" % (where, sorted(bad)))
        _require(t, ("rel", "abs"), where + ": tight")
        _const_field(e, t, "rel", where)
        _const_field(e, t, "abs", where)
        if "exact_when" in t:
            ew = t["exact_when"]
            if not isinstance(ew, dict) or not ew or set(ew) - {"lower", "upper"}:
                raise _error("%s: tight: exact_when must be {\"lower\": [...], \"upper\": [...]}"
                             % where)
            e.tight_exact = {side: _conditions(kernel, ew[side], where + ": tight " + side)
                             for side in ew}
    bw = raw["bounded_when"]
    if not isinstance(bw, list):
        raise _error("%s: bounded_when must be a list" % where)
    e.bounded_when = []
    for j, cond in enumerate(bw):
        w = "%s: bounded_when[%d]" % (where, j)
        if not isinstance(cond, dict) or "abs_le" not in cond:
            raise _error("%s must be {\"abs_le\": SET, \"omega\": true} or {\"abs_le\": SET, "
                         "\"exp\": E}" % w)
        try:
            ct = X.parse(cond["abs_le"]) if isinstance(cond["abs_le"], str) else None
        except X.ExprError:
            ct = None
        if ct != e.set_tree:
            raise _error("%s: abs_le must be the entry's set %r, got %r" % (w, e.set_text,
                                                                           cond["abs_le"]))
        if set(cond) == {"abs_le", "omega"} and cond["omega"] is True:
            e.bounded_when.append(("omega", None))
        elif set(cond) == {"abs_le", "exp"} and isinstance(cond["exp"], int) \
                and not isinstance(cond["exp"], bool):
            e.bounded_when.append(("exp", cond["exp"]))
        else:
            raise _error("%s must be {\"abs_le\": SET, \"omega\": true} or {\"abs_le\": SET, "
                         "\"exp\": E}, got %r" % (w, cond))
    e.bounded_exactly = _true_flag(raw, "bounded_exactly", where)
    if e.bounded_exactly and not e.bounded_when:
        raise _error("%s: bounded_exactly with an empty bounded_when" % where)
    e.zero_factor = _true_flag(raw, "zero_factor", where)
    if e.zero_factor and not product:
        raise _error("%s: zero_factor needs a set that is a product of two intervals" % where)
    if e.when and any(isinstance(p, Stored) for p in e.intervals.values()):
        # product_large reads the bounds of the given limbs; a stored pair holds -lower.
        raise _error("%s: tight: when product_large is not read over stored pairs" % where)
    e.of = _outs_of(e)


def _read_set_bound(e, kernel, raw, where):
    _require(raw, ("of", "side", "set", "balls"), where)
    e.of = kernel.resolve_outputs(raw["of"], where)
    if len(e.of) != 1 or e.of[0] in kernel.masks or kernel.limbs_of(e.of[0]) != 1:
        raise _error("%s: 'of' must name one 1-limb output" % where)
    e.side = raw["side"]
    if e.side not in SIDES:
        raise _error("%s: side must be below or above, got %r" % (where, e.side))
    e.balls = _ball_names(kernel, raw, where)
    e.set_text = str(raw["set"]).strip()
    e.set_tree = _set_over(raw["set"], list(e.balls), where)
    e.tight, e.steps = None, 0
    if "tight" in raw:
        e.steps = _tight_rounded(raw["tight"], where)
        e.tight = "rounded"


def _read_interval_set(e, kernel, raw, where):
    _require(raw, _out_fields(raw) + ("set", "intervals"), where)
    lo_l, hi_l = _bound_outputs(e, kernel, raw, where)
    if e.lower == e.upper or lo_l != hi_l:
        raise _error("%s: lower and upper must be two outputs of as many limbs" % where)
    e.op = raw["set"]
    if e.op not in SET_OPS:
        raise _error("%s: set must be union or intersection, got %r" % (where, e.op))
    e.intervals = _interval_names(kernel, raw, where, count=2)
    for lo, _hi in e.intervals.values():
        if kernel.limbs_of(lo) != lo_l:
            raise _error("%s: the outputs have %d limbs and the bounds of %s %d"
                         % (where, lo_l, lo, kernel.limbs_of(lo)))
    e.of = _outs_of(e)


def _read_ball_of_interval(e, kernel, raw, where):
    _require(raw, ("center", "radius", "from", "special", "rel", "abs"), where)
    e.center, e.radius = raw["center"], raw["radius"]
    cl = _limb_output(kernel, e.center, where, "center")
    if _limb_output(kernel, e.radius, where, "radius") != 1 or e.center == e.radius:
        raise _error("%s: the radius must be another output of one limb" % where)
    if cl not in (1, 2):
        raise _error("%s: the center must have one limb or two" % where)
    e.from_pair = _interval_of(kernel, raw["from"], where)
    e.special = raw["special"]
    if e.special not in SPECIALS:
        raise _error("%s: special must be ieee1788 or ball, got %r" % (where, e.special))
    _const_field(e, raw, "rel", where)
    _const_field(e, raw, "abs", where)
    e.smallest_radius = _true_flag(raw, "smallest_radius", where)
    e.of = [e.center, e.radius]
    # The conversions of two limbs: finite_when, [{"abs_le": BOUND, "exp": E}], BOUND an input of
    # from, |BOUND| <= 2^(qmax + p + E); the radius (with ball, the ball) of a bounded interval is
    # finite when every condition holds, and may be +inf (the whole line) otherwise.
    # (Not e.finite_when, which extended.ExtPlan reads as the conditions of extends and encloses.)
    e.radius_finite_when = None
    if "finite_when" in raw:
        e.radius_finite_when = _read_bound_conditions(raw["finite_when"], e.from_pair,
                                                      where + ": finite_when")
        if e.smallest_radius:
            raise _error("%s: finite_when and smallest_radius together (the radius may be +inf, "
                         "which is not the smallest)" % where)


def _read_bound_conditions(lst, names, where):
    """[(NAME, E)] of a list of conditions {"abs_le": NAME, "exp": E}, NAME one of names."""
    if not isinstance(lst, list) or not lst:
        raise _error("%s must be a nonempty list of conditions (absent when there is none)"
                     % where)
    out = []
    for j, cond in enumerate(lst):
        if (not isinstance(cond, dict) or set(cond) != {"abs_le", "exp"}
                or cond["abs_le"] not in names or not isinstance(cond["exp"], int)
                or isinstance(cond["exp"], bool)):
            raise _error("%s[%d] must be {\"abs_le\": BOUND, \"exp\": E}, BOUND one of %s and E "
                         "an integer, got %r" % (where, j, ", ".join(names), cond))
        out.append((cond["abs_le"], cond["exp"]))
    return out


def _read_interval_of_ball(e, kernel, raw, where):
    _require(raw, ("lower", "upper", "set", "balls", "tight"), where)
    e.lower, e.upper = raw["lower"], raw["upper"]
    lo_l = _limb_output(kernel, e.lower, where, "lower")
    if (lo_l not in (1, 2) or _limb_output(kernel, e.upper, where, "upper") != lo_l
            or e.lower == e.upper):
        raise _error("%s: lower and upper must be two outputs of one limb each or two each" % where)
    e.balls = _ball_names(kernel, raw, where)
    if len(e.balls) != 1:
        raise _error("%s: interval_of_ball takes one ball" % where)
    e.set_text = str(raw["set"]).strip()
    e.set_tree = _set_over(raw["set"], list(e.balls), where)
    e.of = [e.lower, e.upper]
    e.two = lo_l == 2
    e.tight_exact, e.bounded_when = None, []
    t = raw["tight"]
    if not e.two:
        # One limb: the rounded tightness, and nothing of the conversions of two limbs.
        e.steps = _tight_rounded(t, where)
        if "bounded_when" in raw:
            raise _error("%s: bounded_when is for bounds of two limbs" % where)
        return
    # Two limbs (architecture.md, "... the conversions of two limbs"): the outward tightness of
    # encloses_interval and an optional bounded_when of {"abs_le": SET, "exp": E}.
    e.steps = 0
    if not isinstance(t, dict) or t.get("kind") != "outward":
        raise _error("%s: tight of bounds of two limbs must be {\"kind\": \"outward\", ...} (a "
                     "two-limb bound has no rounding of its own)" % where)
    bad = set(t) - {"kind", "rel", "abs", "exact_when"}
    if bad:
        raise _error("%s: tight: unknown fields %s" % (where, sorted(bad)))
    _require(t, ("rel", "abs"), where + ": tight")
    _const_field(e, t, "rel", where)
    _const_field(e, t, "abs", where)
    if "exact_when" in t:
        ew = t["exact_when"]
        if not isinstance(ew, dict) or not ew or set(ew) - {"lower", "upper"}:
            raise _error("%s: tight: exact_when must be {\"lower\": [...], \"upper\": [...]}"
                         % where)
        e.tight_exact = {side: _conditions(kernel, ew[side], where + ": tight " + side)
                         for side in ew}
    if "bounded_when" in raw:
        bw = raw["bounded_when"]
        if not isinstance(bw, list) or not bw:
            raise _error("%s: bounded_when must be a nonempty list (absent when there is none)"
                         % where)
        for j, cond in enumerate(bw):
            w = "%s: bounded_when[%d]" % (where, j)
            try:
                ct = X.parse(cond["abs_le"]) if isinstance(cond, dict) and isinstance(
                    cond.get("abs_le"), str) else None
            except X.ExprError:
                ct = None
            if (ct != e.set_tree or set(cond) != {"abs_le", "exp"}
                    or not isinstance(cond["exp"], int) or isinstance(cond["exp"], bool)):
                raise _error("%s must be {\"abs_le\": SET, \"exp\": E}, SET the entry's set %r, "
                             "got %r" % (w, e.set_text, cond))
            e.bounded_when.append(("exp", cond["exp"]))


def _read_splits(e, kernel, raw, where):
    _require(raw, ("parts", "from"), where)
    e.from_pair = _interval_of(kernel, raw["from"], where)
    k = kernel.limbs_of(e.from_pair[0])
    parts = raw["parts"]
    if not isinstance(parts, list) or len(parts) != 2:
        raise _error("%s: parts must be a list of two intervals" % where)
    e.parts = []
    seen = []
    for j, p in enumerate(parts):
        if not isinstance(p, dict) or set(p) != {"lower", "upper"}:
            raise _error("%s: part %d must be {\"lower\": OUTPUT, \"upper\": OUTPUT}" % (where, j))
        for f in ("lower", "upper"):
            if _limb_output(kernel, p[f], where, "part %d %s" % (j, f)) != k:
                raise _error("%s: part %d %s must have the limbs of the bounds (%d)"
                             % (where, j, f, k))
            if p[f] in seen:
                raise _error("%s: the output %s is named twice" % (where, p[f]))
            seen.append(p[f])
        e.parts.append((p["lower"], p["upper"]))
    e.of = seen


def read_makes_ball_interval(e, kernel, raw, where):
    """makes_ball whose from names the bounds of an interval of one limb (ball_from_interval_2),
    with an optional midpoint_when."""
    e.iv = True
    e.consts = {}
    outs = dict(kernel.outputs)
    e.center, e.radius = raw["center"], raw["radius"]
    for what, n in (("center", e.center), ("radius", e.radius)):
        _limb_output(kernel, n, where, what)
    if e.center == e.radius or outs[e.radius] != 1:
        raise _error("%s: the radius must be another output of one limb" % where)
    fr = raw["from"]
    e.from_lower, e.from_upper = fr["lower"], fr["upper"]
    for what, n in (("lower", e.from_lower), ("upper", e.from_upper)):
        if _limb_input(kernel, n, where, "from " + what) != 1:
            raise _error("%s: from %s must be an input of one limb" % (where, what))
    if e.from_lower == e.from_upper:
        raise _error("%s: the given bounds are the same input" % where)
    e.midpoint_when = []
    if "midpoint_when" in raw:
        mw = raw["midpoint_when"]
        if not isinstance(mw, list) or not mw:
            raise _error("%s: midpoint_when must be a nonempty list (absent when there is none)"
                         % where)
        for j, cond in enumerate(mw):
            if (not isinstance(cond, dict) or set(cond) != {"half_in_format"}
                    or cond["half_in_format"] not in (e.from_lower, e.from_upper)):
                raise _error("%s: midpoint_when[%d] must be {\"half_in_format\": BOUND}, BOUND "
                             "one of the given bounds, got %r" % (where, j, cond))
            e.midpoint_when.append(cond["half_in_format"])
    # rel, abs and smallest_radius (the conversions of two limbs, ball_from_interval_1): all three
    # optional, rel and abs together, smallest_radius only with them.
    e.mid_consts = "rel" in raw or "abs" in raw
    if e.mid_consts:
        if "rel" not in raw or "abs" not in raw:
            raise _error("%s: rel and abs come together" % where)
        _const_field(e, raw, "rel", where)
        _const_field(e, raw, "abs", where)
    e.smallest_radius = _true_flag(raw, "smallest_radius", where)
    if e.smallest_radius and not e.mid_consts:
        raise _error("%s: smallest_radius only with rel and abs" % where)
    e.of = [e.center, e.radius]
    e.label = "makes_ball(%s, %s) from the interval of lower %s, upper %s" % (
        e.center, e.radius, e.from_lower, e.from_upper)
    if e.midpoint_when:
        e.label += ", the midpoint when %s" % " and ".join("%s/2 is a number of the format" % n
                                                            for n in e.midpoint_when)
    if e.mid_consts:
        e.label += ", the center within rel %s, abs %s of the midpoint%s" % (
            e.consts["rel"][1], e.consts["abs"][1],
            ", the smallest radius" if e.smallest_radius else "")


def read_zero_factor(e, kernel, raw, where):
    """zero_factor of bound and rounded: the extended domain, value the product of two one-limb
    inputs; a zero operand gives a zero output (0 * inf = 0)."""
    e.zero_factor = _true_flag(raw, "zero_factor", where)
    if not e.zero_factor:
        return
    if not kernel.extended:
        raise _error("%s: zero_factor belongs to the extended domain" % where)
    t = kernel.value_tree
    if not (t[0] == "*" and t[1][0] == "name" and t[2][0] == "name" and t[1][1] != t[2][1]
            and kernel.limbs_of(t[1][1]) == 1 and kernel.limbs_of(t[2][1]) == 1):
        raise _error("%s: zero_factor needs a value that is the product of two one-limb inputs"
                     % where)
    e.iv = True
    e.consts = {}
    e.factors = (t[1][1], t[2][1])
    e.label += ", a zero factor gives zero"


READERS = {"outward": _read_outward, "makes_interval": _read_makes_interval,
           "encloses_interval": _read_encloses_interval, "set_bound": _read_set_bound,
           "interval_set": _read_interval_set, "ball_of_interval": _read_ball_of_interval,
           "interval_of_ball": _read_interval_of_ball, "splits": _read_splits}


def _iv_text(names):
    return ", ".join(("%s=(upper %s, nlower %s)" if isinstance(p, Stored) else "%s=[%s, %s]")
                     % ((n,) + tuple(p)) for n, p in names.items())


def _ball_text(names):
    return ", ".join("%s=[%s +- %s]" % (b, c, r) for b, (c, r) in names.items())


def label(e):
    k = e.kind
    if k == "outward":
        s = "outward(%s) %s" % (e.of[0], e.side)
        if e.exact_when:
            s += ", exact when %s" % " and ".join("(%s)" % condition_text(t, o, c)
                                                  for _tr, t, o, c in e.exact_when)
        if e.zero_factor:
            s += ", a zero factor gives zero"
        return s
    if k == "makes_interval":
        return "makes_interval(%s) from lower %s, upper %s" % (_outs_text(e), e.from_lower,
                                                              e.from_upper)
    if k == "encloses_interval":
        s = "encloses_interval(%s) %s over %s, I1-I5, tight %s" % (
            _outs_text(e), e.set_text, _iv_text(e.intervals), e.tight)
        if e.numbers:
            s += ", numbers %s (each the members of Interval(t))" % ", ".join(e.numbers)
        if e.steps:
            s += ", steps %d" % e.steps
        if e.when:
            s += ", when %s" % e.when
        if e.tight_exact:
            s += ", exact when %s" % "; ".join(
                "%s: %s" % (side, " and ".join(condition_text(t, o, c) for _tr, t, o, c in cs))
                for side, cs in sorted(e.tight_exact.items()))
        if e.bounded_when:
            s += ", bounded %s %s" % ("exactly when" if e.bounded_exactly else "when", " and ".join(
                "|%s| <= %s" % (e.set_text, "Omega" if w == "omega" else
                                "2^(qmax+p%+d)" % x if x else "2^(qmax+p)")
                for w, x in e.bounded_when))
        if e.zero_factor:
            s += ", I6: [0, 0] times anything is [0, 0]"
        return s
    if k == "set_bound":
        s = "set_bound(%s) %s %s over %s" % (e.of[0], e.side, e.set_text, _ball_text(e.balls))
        if e.tight:
            s += ", tight rounded" + (", steps %d" % e.steps if e.steps else "")
        return s
    if k == "interval_set":
        return "interval_set(%s) %s of %s" % (_outs_text(e), e.op, _iv_text(e.intervals))
    if k == "ball_of_interval":
        s = "ball_of_interval(%s, %s) of [%s, %s], special %s, rel %s, abs %s%s" % (
            e.center, e.radius, e.from_pair[0], e.from_pair[1], e.special, e.consts["rel"][1],
            e.consts["abs"][1], ", the smallest radius" if e.smallest_radius else "")
        if e.radius_finite_when:
            s += ", finite when %s" % " and ".join("|%s| <= 2^(qmax+p%+d)" % (n, x) if x else
                                                   "|%s| <= 2^(qmax+p)" % n
                                                   for n, x in e.radius_finite_when)
        return s
    if k == "interval_of_ball":
        if e.two:
            s = "interval_of_ball(%s, %s) %s over %s, tight outward" % (
                e.lower, e.upper, e.set_text, _ball_text(e.balls))
            if e.tight_exact:
                s += ", exact when %s" % "; ".join(
                    "%s: %s" % (side, " and ".join(condition_text(t, o, c) for _tr, t, o, c in cs))
                    for side, cs in sorted(e.tight_exact.items()))
            if e.bounded_when:
                s += ", bounded when %s" % " and ".join(
                    "|%s| <= %s" % (e.set_text, "2^(qmax+p%+d)" % x if x else "2^(qmax+p)")
                    for _w, x in e.bounded_when)
            return s
        return "interval_of_ball(%s, %s) %s over %s, tight rounded%s" % (
            e.lower, e.upper, e.set_text, _ball_text(e.balls),
            ", steps %d" % e.steps if e.steps else "")
    if k == "splits":
        return "splits [%s, %s], [%s, %s] of [%s, %s]" % (e.parts[0] + e.parts[1] + e.from_pair)
    raise _error("no label for %s" % k)


# ---------------------------------------------------------------------------
# Linking: the kernels unit( ) and tiny( ) name, and the constants evaluated per format

def link_constants(claims):
    """Every unit(K) and tiny(K) of a constant of a claim names a readable kernel with one error
    entry, and every constant is finite and nonnegative in binary64; otherwise the kernel is set
    aside."""
    from .claims import ClaimsError
    b64 = F.Format(53, -1074, 971)
    for k in list(claims.kernels.values()):
        try:
            for e in k.ensures:
                for field, (tree, text) in sorted(getattr(e, "consts", {}).items()):
                    for kn in const_calls(tree):
                        claims.check_unit_kernel(kn, "%s: %s %s" % (k.name, e.label, field))
                    v = eval_const(tree, b64, lambda kn: claims.unit_tiny(kn, b64), text)
                    if v < 0:
                        raise ClaimsError("%s: %s: %s = %s is negative in binary64"
                                          % (k.name, e.label, field, _short_frac(v)))
        except ClaimsError as ex:
            claims.mark_broken(k.name, str(ex))


def constants(e, fmt, claims):
    """{field: Fraction} of the constants of entry e in format fmt (a ClaimsError when one does
    not exist there, or is negative)."""
    out = {}
    for field, (tree, text) in e.consts.items():
        v = eval_const(tree, fmt, lambda kn: claims.unit_tiny(kn, fmt), text)
        if v < 0:
            raise _error("%s: %s = %s is negative in %s" % (e.label, field, _short_frac(v),
                                                           fmt.name))
        out[field] = v
    return out


# ---------------------------------------------------------------------------
# Values

def bound_value(fmt, limbs):
    """The value of a bound in the extended reals: an integer at scale qmin, INF, NINF or NAN;
    None for two limbs that are not canonical."""
    if len(limbs) == 1:
        return limbs[0]
    if not XT.canonical(fmt, limbs):
        return None
    h = limbs[0]
    if type(h) is int:
        return sum(limbs)
    return h


def interval_state(fmt, lo, hi):
    """("empty", INF, NINF) or ("nonempty", L, U) for a canonical interval, None otherwise
    (milestone2.md, "Values of an interval")."""
    L, U = bound_value(fmt, lo), bound_value(fmt, hi)
    if L is None or U is None or L == NAN or U == NAN:
        return None
    if L == INF and U == NINF:
        return ("empty", L, U)
    if L == INF or U == NINF:
        return None
    if XT.x_cmp(L, 0, U, 0) > 0:
        return None
    return ("nonempty", L, U)


class Stored(tuple):
    """A set named by its stored pair, the round-up interval's (upward.md, "Claims and the
    oracle"; upward.py): (U, N), the names (or the slices) of its upper bound and of its lower
    bound negated, in that order.  A plain tuple is (L, U), the bounds of an interval()."""
    __slots__ = ()


def upward_state(u, n):
    """("empty", INF, NINF) for the stored pair (NaN, NaN), ("nonempty", -n, u) for that of a
    nonempty interval, None for any other pair: one NaN lane, a lane -inf, crossed lanes (-n > u)
    (upward.md, "States"; upward.defect says which)."""
    if u == NAN and n == NAN:
        return ("empty", INF, NINF)
    if NAN in (u, n) or NINF in (u, n):
        return None
    lo = XT.x_neg(n)
    if XT.x_cmp(lo, 0, u, 0) > 0:
        return None
    return ("nonempty", lo, u)


def _pair_sl(sl, pair):
    """The slices of a pair of names, a Stored pair staying one."""
    out = (sl[pair[0]], sl[pair[1]])
    return Stored(out) if isinstance(pair, Stored) else out


def _out_plan(e, os_):
    """The slices of the outputs of an interval: lower and upper, or the stored pair."""
    if e.nlower is not None:
        return {"stored_out": Stored((os_[e.upper], os_[e.nlower]))}
    return {"lower": os_[e.lower], "upper": os_[e.upper]}


def _out_state(fmt, z, c):
    """The state of the output interval of a plan entry (lower and upper, or a stored pair)."""
    so = c.get("stored_out")
    if so is not None:
        return upward_state(z[so[0][0]], z[so[1][0]])
    return interval_state(fmt, z[c["lower"][0]:c["lower"][1]], z[c["upper"][0]:c["upper"][1]])


def _out_defect(fmt, es, z, c):
    """Why an output stored pair is not canonical (counted), as the end of a reason; "" for an
    output of lower and upper."""
    so = c.get("stored_out")
    if so is None:
        return ""
    from . import upward as UP
    return UP.defect_text(fmt, es, z[so[0][0]], z[so[1][0]])


def interval_class(st):
    """The class of a canonical interval for the statistics."""
    if st[0] == "empty":
        return X_EMPTY
    L, U = st[1], st[2]
    if L == NINF and U == INF:
        return X_WHOLE
    if L == NINF:
        return X_BELOW
    if U == INF:
        return X_ABOVE
    return X_POINT if L == U else X_BOUNDED


def bounded(st):
    return st[0] == "nonempty" and type(st[1]) is int and type(st[2]) is int


def _xadd(a, b):
    if type(a) is int and type(b) is int:
        return a + b
    if a == NAN or b == NAN:
        return NAN
    if type(a) is not int and type(b) is not int and a != b:
        return NAN
    return a if type(a) is not int else b


def _xmul0(a, b):
    """The product of two bounds in interval arithmetic: 0 * inf = 0."""
    if type(a) is int and type(b) is int:
        return a * b
    if a == 0 or b == 0:
        return 0
    if a == NAN or b == NAN:
        return NAN
    return INF if XT.x_sign(a) == XT.x_sign(b) else NINF


def _key(v):
    return (-1, 0) if v == NINF else (1, 0) if v == INF else (0, v)


def _align(v, s, t):
    return v << (s - t) if type(v) is int else v


def range_eval(tree, env):
    """(lo, hi, s): the greatest lower bound and the least upper bound of a set, each name ranging
    over the members of its interval env[name] = (lo, hi, scale); finite values are integers at
    scale s, infinite ones INF and NINF."""
    k = tree[0]
    if k == "name":
        return env[tree[1]]
    if k == "neg":
        lo, hi, s = range_eval(tree[1], env)
        return XT.x_neg(hi), XT.x_neg(lo), s
    a = range_eval(tree[1], env)
    b = range_eval(tree[2], env)
    if k == "*":
        ps = [_xmul0(p, q) for p in a[:2] for q in b[:2]]
        if NAN in ps:
            raise ValueError("a NaN bound in a range")
        return min(ps, key=_key), max(ps, key=_key), a[2] + b[2]
    if k == "-":
        b = (XT.x_neg(b[1]), XT.x_neg(b[0]), b[2])
    s = min(a[2], b[2])
    lo = _xadd(_align(a[0], a[2], s), _align(b[0], b[2], s))
    hi = _xadd(_align(a[1], a[2], s), _align(b[1], b[2], s))
    if NAN in (lo, hi):
        raise ValueError("inf - inf in a range")
    return lo, hi, s


def to_scale(v, s, t):
    """A finite v at scale s as an exact Fraction-free pair at the common scale min(s, t)."""
    m = min(s, t)
    return v << (s - m), m


def ratio_le(dist, mag, rel, ab, scale):
    """(holds, (num, den)): dist <= rel*mag + ab, dist and mag integers at 2^scale, rel and ab
    Fractions; (num, den) is dist / (rel*mag + ab)."""
    a = ab * (Fraction(1 << -scale) if scale < 0 else Fraction(1, 1 << scale))
    rn, rd = rel.numerator, rel.denominator
    an, ad = a.numerator, a.denominator
    num = dist * rd * ad
    den = rn * mag * ad + an * rd
    return num <= den, ((num, den) if den else ((0, 1) if num == 0 else (1, 0)))


def compile_conditions(pl, conds):
    """[(holds(x), text)] of exact_when conditions on finite input limbs, decided with integers."""
    out = []
    for tree, text, op, k in conds:
        src, s = X.compile_tree(tree, pl._leaf)
        fn = X.make_function(["x"], src)
        if op == "zero":
            out.append((lambda x, fn=fn: fn(x) == 0, condition_text(text, op, k)))
            continue
        from .claims import eval_const as eval_k, format_u_eta
        u, eta = format_u_eta(pl.fmt)
        K = eval_k(k, u, eta)
        if K <= 0:
            raise _error("%s: than %r is not positive in %s" % (text, k, pl.fmt.name))
        n, d = K.numerator, K.denominator
        ls, rs = (s, 0) if s >= 0 else (0, -s)

        def holds(x, fn=fn, n=n, d=d, ls=ls, rs=rs, strict=op == "zero_or_abs_gt"):
            v = fn(x)
            if v == 0:
                return True
            a, b = (abs(v) * d) << ls, n << rs
            return a > b if strict else a >= b
        out.append((holds, condition_text(text, op, k)))
    return out


def failing(conds, x, es, prefix, holds_name):
    """The texts of the conditions that do not hold, each counted (prefix + text), or the count
    holds_name when every one holds."""
    bad = [t for h, t in conds if not h(x)]
    for t in bad:
        es.count(prefix + t)
    if not bad:
        es.count(holds_name)
    return bad


# ---------------------------------------------------------------------------
# Plans

PLANNED_KIND = {"bound": "bound_zf", "rounded": "rounded_zf", "makes_ball": "makes_ball_iv"}


def plan_entry(pl, e, claims):
    """The fields of the plan entry of e (check.Plan) in pl's format: slices, the constants, the
    compiled conditions; and, for the kinds that exist, the kind the judge dispatches on."""
    c = {}
    if e.kind in PLANNED_KIND:
        c["kind"] = PLANNED_KIND[e.kind]
    sl = pl.in_slices
    os_ = pl.out_slices
    if not pl.in_scope:
        return c
    if e.consts:
        if claims is None:
            raise _error("%s: the constants need the claims" % e.label)
        c["consts"] = constants(e, pl.fmt, claims)
    k = e.kind
    if k == "outward":
        c["side"] = e.side
        c["conds"] = compile_conditions(pl, e.exact_when) if e.exact_when else None
        c["zero_factor"] = e.zero_factor
        if e.zero_factor:
            c["factors"] = [sl[n] for n in e.factors]
        c["operands"] = [sl[n] for n in sorted(set(X.names(pl.kernel.value_tree)),
                                               key=pl.kernel.input_names.index)]
    elif k == "makes_interval":
        c.update(_out_plan(e, os_), given=(sl[e.from_lower], sl[e.from_upper]))
    elif k == "encloses_interval":
        c.update(_out_plan(e, os_), tree=e.set_tree,
                 ivs={n: _pair_sl(sl, pair) for n, pair in e.intervals.items()},
                 tight=e.tight, steps=e.steps, when=e.when, bw=e.bounded_when,
                 bexact=e.bounded_exactly, zero_factor=e.zero_factor)
        if e.numbers:
            c["nums"] = {n: sl[n][0] for n in e.numbers}
        if e.tight_exact:
            c["texact"] = {side: compile_conditions(pl, cs) for side, cs in e.tight_exact.items()}
        if e.when:
            c["pl_thr"] = 1 << max(2 * pl.fmt.p - 1 + pl.fmt.qmin - 2 * pl.fmt.qmin, 0)
    elif k in ("set_bound", "interval_of_ball"):
        c.update(balls={b: (sl[cn], sl[rn][0]) for b, (cn, rn) in e.balls.items()},
                 tree=e.set_tree, steps=e.steps)
        if k == "set_bound":
            c.update(side=e.side, tight=e.tight, out=os_[e.of[0]][0])
        elif not e.two:
            c.update(lower=os_[e.lower][0], upper=os_[e.upper][0])
        else:
            # Bounds of two limbs, the outward tightness (the conversions of two limbs).
            c.update(two=True, lower_sl=os_[e.lower], upper_sl=os_[e.upper], bw=e.bounded_when)
            if e.tight_exact:
                c["texact"] = {side: compile_conditions(pl, cs)
                               for side, cs in e.tight_exact.items()}
    elif k == "interval_set":
        c.update(_out_plan(e, os_), op=e.op,
                 ivs=[_pair_sl(sl, pair) for pair in e.intervals.values()])
    elif k == "ball_of_interval":
        c.update(center=os_[e.center], radius=os_[e.radius][0], special=e.special,
                 given=(sl[e.from_pair[0]], sl[e.from_pair[1]]), smallest=e.smallest_radius)
        if e.radius_finite_when:
            c["fw"] = [(sl[n], n, x) for n, x in e.radius_finite_when]
    elif k == "splits":
        c.update(given=(sl[e.from_pair[0]], sl[e.from_pair[1]]),
                 parts=[(os_[a], os_[b]) for a, b in e.parts])
    elif k == "makes_ball":
        c.update(center=os_[e.center], radius=os_[e.radius][0],
                 given=(sl[e.from_lower][0], sl[e.from_upper][0]),
                 mid=[sl[n][0] for n in e.midpoint_when])
        if e.mid_consts:
            c.update(mid_consts=True, smallest=e.smallest_radius)
    elif k in ("bound", "rounded"):
        c["factors"] = [sl[n][0] for n in e.factors]
    return c


def by_groups(kernel):
    """True for a kernel of the finite domain with an entry (not under a mask) about an output
    group other than the first: its entries are judged each where its own group's leading limb
    is finite (judge_by_groups)."""
    if kernel.extended or getattr(kernel, "conditional", False):
        return False
    groups = [n for n, _ in kernel.outputs if n not in kernel.masks]
    for e in kernel.ensures:
        if (e.cond is None and e.of and e.of[0] in groups[1:]):
            return True
    return False


# ---------------------------------------------------------------------------
# The finite domain

def _value_scaled(pl, x, z, ranges):
    O = 0
    for lo, hi in ranges:
        O += sum(z[lo:hi])
    return O << pl.sh_out


def finite_outward(ck, pl, e, es, x, z, V, _r, line):
    """outward of the finite domain: the output on its side of the value, within rel*|value| +
    abs of it, and the value itself where every condition of exact_when holds."""
    es.applicable += 1
    rel, ab = e["consts"]["rel"], e["consts"]["abs"]
    Oc = _value_scaled(pl, x, z, e["ranges"])
    Vc = V << pl.sh_val
    return _outward_finite_values(pl, e, es, x, Oc, Vc, rel, ab, pl.sc, line)


def _outward_finite_values(pl, e, es, x, Oc, Vc, rel, ab, scale, line):
    """The judge of an outward entry on a finite output Oc and value Vc (integers at 2^scale)."""
    reasons = []
    below = e["side"] == "below"
    if Vc == 0:
        es.count(OUT_VALUE_ZERO)
    es.count(OUT_EXACT if Oc == Vc else OUT_INEXACT)
    if (Oc > Vc) if below else (Oc < Vc):
        es.count("failed side")
        reasons.append("outward: the output is %s the value" % ("above" if below else "below"))
    ok, r = ratio_le(abs(Oc - Vc), abs(Vc), rel, ab, scale)
    es.track_max(OUT_RATIO, r, line)
    a = ab * (Fraction(1 << -scale) if scale < 0 else Fraction(1, 1 << scale))
    if a > rel * abs(Vc):
        es.count(OUT_ABS_LARGER)
    else:
        # Where the relative term is the larger part of the bound: how close the relative
        # constant is to what the kernel needs.
        es.track_max(OUT_RATIO_REL, r, line)
    if not ok:
        es.count("failed bound")
        reasons.append("outward: the output is farther from the value than rel*|value| + abs")
    if e.get("conds"):
        if not failing(e["conds"], x, es, OUT_EW_FAILS, OUT_EW_HOLDS) and Oc != Vc:
            es.count("failed exact_when")
            reasons.append("outward: exact_when holds but the output is not the value")
    return "; ".join(reasons) or None


def judge_by_groups(ck, pl, st, x, z, line):
    """architecture.md, "An output group other than the first": in the finite domain an entry
    holds where the requirements hold and the leading limb of its own output group is finite.
    Entries whose group is not finite claim nothing (counted); the line is judged when one entry
    is, and non-finite otherwise; a group that is not finite with operands and value far below
    Omega makes it suspicious, as in the finite layer."""
    fmt = pl.fmt
    for v in z:
        if v == F.OUTSIDE or (type(v) is int and not F.is_member(fmt, v)):
            ck._fail(st, line, "output limb not a number of the format")
            return
    V = pl.value_fn(x) if pl.value_fn is not None else None
    judged, lost, tail = [], [], False
    for i, c in enumerate(pl.entries):
        es = st.entries[i]
        rg = c["ranges"]
        lead = rg[0][0]
        if type(z[lead]) is not int:
            es.count(GROUP_NONFINITE)
            lost.append(i)
        elif any(type(z[j]) is not int for lo, hi in rg for j in range(lo, hi)):
            es.count(GROUP_TAIL)
            lost.append(i)
            tail = True
        else:
            judged.append(i)
    if lost:
        q4 = fmt.omega
        small = all(4 * abs(v) < q4 for v in x) and all(4 * abs(sum(x[lo:hi])) < q4
                                                         for lo, hi in pl.groups)
        if small and V is not None:
            d = pl.sv - fmt.qmin
            small = ((4 * abs(V)) << d) < q4 if d >= 0 else 4 * abs(V) < (q4 << -d)
        if small:
            st.c["suspicious"] += 1
            st.example("suspicious", line, "an output group not finite with operands and exact "
                       "value below Omega/4 (%s)" % ", ".join(pl.kernel.ensures[i].label
                                                             for i in lost), ck.max_examples)
    if not judged:
        st.c["nonfinite_tail" if tail and all(type(z[c["ranges"][0][0]]) is int
                                              for c in pl.entries) else "nonfinite"] += 1
        return
    st.c["judged"] += 1
    reasons = ck._judge(pl, st.entries, x, z, V, {}, line, only=set(judged))
    if reasons:
        st.c["failed"] += 1
        for r in reasons:
            st.reason(r)
        st.example("failure", line, "; ".join(reasons), ck.max_examples)
    else:
        st.c["passed"] += 1


# ---------------------------------------------------------------------------
# The extended domain

def _gather(z, ranges):
    w = []
    for lo, hi in ranges:
        w.extend(z[lo:hi])
    return w


def _state_of(fmt, x, pair):
    if isinstance(pair, Stored):
        # The round-up interval's stored pair (u, n): one limb each.
        return upward_state(x[pair[0][0]], x[pair[1][0]])
    (alo, ahi), (blo, bhi) = pair
    return interval_state(fmt, x[alo:ahi], x[blo:bhi])


def _cmp(a, sa, b, sb):
    return XT.x_cmp(a, sa, b, sb)


def _hexv(fmt, v, s):
    """A value at scale s as a literal (for messages)."""
    if type(v) is not int:
        return v
    return F.to_hex(v, s)


def k_outward(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """outward in the extended domain (architecture.md, "... two limbs and the enclosure
    interface"): never a NaN; with zero_factor a zero operand gives every limb zero; otherwise an
    infinite operand gives the infinity of the sign of the product, followed by zeros; with finite
    operands the output is on its side of the value as an extended real number (-inf is always
    below and +inf above), and a finite output is within rel*|value| + abs, exact where exact_when
    holds."""
    fmt = pl.fmt
    w = _gather(z, c["ranges"])
    es.applicable += 1
    out = []
    fail = XT._failer(es, out)
    if any(v == NAN for v in w):
        fail("NaN", "the output is a NaN")
        return out
    leads = [x[lo] for lo, _hi in c["operands"]]
    if c["zero_factor"] and any(x[lo] == 0 for lo, _hi in c["factors"]):
        es.count(OUT_ZERO_OPERAND)
        if any(type(v) is not int for v in leads):
            es.count(ZF_ZERO_INF)
        if not all(v == 0 for v in w):
            fail("zero_factor", "a zero operand, and the output is not zero")
        return out
    if not fin:
        es.count(OUT_INF_OPERAND)
        t = leads[0]
        for v in leads[1:]:
            t = XT.x_mul(t, v)
        want = [t] + [0] * (len(w) - 1)
        if w != want:
            fail("infinite operand", "the output is not (%s, 0), the product of the leading limbs"
                 % t)
        return out
    v, s = V
    below = c["side"] == "below"
    w0 = w[0]
    if type(w0) is not int:
        es.count(OUT_FINITE_INF)
        if w0 != (NINF if below else INF) or any(t != 0 for t in w[1:]):
            fail("side", "a finite operand gives %s, which is not %s the value" % (
                w0, "below" if below else "above"))
        elif ep.small(x, V):
            sus.append("outward: an infinite bound with operands and exact value below Omega/4")
        return out
    if any(type(t) is not int for t in w):
        fail("side", "a finite leading limb with a lower limb that is not finite")
        return out
    es.count(OUT_FINITE)
    m = min(s, fmt.qmin)
    Oc = sum(w) << (fmt.qmin - m)
    Vc = v << (s - m)
    why = _outward_finite_values(pl, c, es, x, Oc, Vc, c["consts"]["rel"], c["consts"]["abs"], m,
                                 line)
    if why:
        out.append(why)
    return out


def _round_side(fmt, v, s, down):
    """A range bound rounded down (or up) in the format with overflow; an infinity stays."""
    if type(v) is not int:
        return v
    return D.round_overflow(fmt, v, s, "down" if down else "up")


def _judge_rounded_side(fmt, es, name, zv, v, s, steps, exact_needed, down):
    """The bound zv (at scale qmin, or an infinity) against the range bound v (at scale s), rounded
    down (lower) or up (upper) and stepped `steps` times outward: the reason of a failure, or None.
    exact_needed: the rounding itself is claimed (steps do not apply)."""
    if type(v) is not int:
        es.count(SIDE_INFINITE % name)
    else:
        if v == 0:
            es.count(SIDE_ZERO % name)
        es.count(D.overflow_class(fmt, v, s) and SIDE_OVER % name or (
            SIDE_EXACT % name if _round_side(fmt, v, s, down) == _round_side(fmt, v, s, not down)
            else SIDE_INEXACT % name))
    d = _round_side(fmt, v, s, down)
    k, t = 0, d
    limit = 0 if exact_needed else steps
    while t != zv:
        if k == limit:
            return ("the %s bound is %s, not the range bound rounded %s%s (%s)" % (
                name, F.fixed_hex(fmt, zv), "down" if down else "up",
                (" or up to %d steps beyond" % limit) if limit else "", F.fixed_hex(fmt, d)))
        if type(t) is not int:
            # An infinity has no step outward.
            return ("the %s bound is %s, beyond the range bound rounded %s (%s)" % (
                name, F.fixed_hex(fmt, zv), "down" if down else "up", F.fixed_hex(fmt, d)))
        t = D.neighbor(fmt, t, not down)
        k += 1
    es.count(SIDE_AT % name if k == 0 else SIDE_ONE % name if k == 1 else SIDE_STEPS % (name, k))
    return None


def _product_large(c, fmt, x, ivs):
    """Each product of a finite bound of x and a finite bound of y is zero or at least
    2^(2p-1) eta in magnitude (fixed values at scale 2 qmin)."""
    (xa, xb), (ya, yb) = ivs
    thr = c["pl_thr"]
    xs = [v for v in (bound_value(fmt, x[xa[0]:xa[1]]), bound_value(fmt, x[xb[0]:xb[1]]))
          if type(v) is int]
    ys = [v for v in (bound_value(fmt, x[ya[0]:ya[1]]), bound_value(fmt, x[yb[0]:yb[1]]))
          if type(v) is int]
    return all(p == 0 or abs(p) >= thr for p in (a * b for a in xs for b in ys))


def _limit_ratio(fmt, kind, e, v, s):
    """max|member| / limit as a fraction, the limit Omega or 2^(qmax+p+E), v at scale s."""
    if kind == "omega":
        lim_n, lim_s = fmt.omega, fmt.qmin
    else:
        lim_n, lim_s = 1, fmt.qmax + fmt.p + e
    m = min(s, lim_s)
    a, b = abs(v) << (s - m), lim_n << (lim_s - m)
    return a, b


def k_encloses_interval(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """I1 to I6 (architecture.md, "Claims of the interval kernels"), each counted under its name
    when it fails."""
    fmt = pl.fmt
    q = fmt.qmin
    es.applicable += 1
    out = []
    fail = XT._failer(es, out)
    zs = _out_state(fmt, z, c)
    if zs is None:
        fail("I1", "the result is not a canonical interval" + _out_defect(fmt, es, z, c))
        return out
    sts = {n: _state_of(fmt, x, pair) for n, pair in c["ivs"].items()}
    # The numbers (the round-up interval, upward.py): each the members of Interval(t), {t} for a
    # finite t and every real number otherwise; never empty; a bounded operand when finite.
    if c.get("nums"):
        from . import upward as UP
        nenv = UP.number_env(es, x, c["nums"], q)
    else:
        nenv = {}
    es.count(RES_EMPTY if zs[0] == "empty" else RES_BOUNDED if bounded(zs) else RES_UNBOUNDED)
    if any(s[0] == "empty" for s in sts.values()):
        es.count(OPS_EMPTY)
        if zs[0] != "empty":
            fail("I2", "an operand is empty and the result is not")
        return out
    if zs[0] == "empty":
        fail("I2", "the empty set from operands that are not empty")
        return out
    bops = all(bounded(s) for s in sts.values())
    bops = bops and all(type(v[0]) is int for v in nenv.values())
    es.count(OPS_BOUNDED if bops else OPS_UNBOUNDED)
    env = {n: (st_[1], st_[2], q) for n, st_ in sts.items()}
    env.update(nenv)
    lo, hi, s = range_eval(c["tree"], env)
    zl, zu = zs[1], zs[2]
    if _cmp(zl, q, lo, s) > 0:
        fail("I3", "the lower bound %s is above the range's greatest lower bound %s"
             % (F.fixed_hex(fmt, zl), _hexv(fmt, lo, s)))
    if _cmp(zu, q, hi, s) < 0:
        fail("I3", "the upper bound %s is below the range's least upper bound %s"
             % (F.fixed_hex(fmt, zu), _hexv(fmt, hi, s)))
    tight = c["tight"]
    if tight == "exact":
        if _cmp(zl, q, lo, s) != 0 or _cmp(zu, q, hi, s) != 0:
            fail("I4", "the bounds are not those of the exact range [%s, %s]"
                 % (_hexv(fmt, lo, s), _hexv(fmt, hi, s)))
    elif tight == "rounded":
        exact = False
        if c["when"]:
            exact = _product_large(c, fmt, x, list(c["ivs"].values()))
            for name in ("lower", "upper"):
                es.count((SIDE_PL_HOLDS if exact else SIDE_PL_FAILS) % name)
        for name, zv, v, down in (("lower", zl, lo, True), ("upper", zu, hi, False)):
            why = _judge_rounded_side(fmt, es, name, zv, v, s, c["steps"], exact, down)
            if why:
                fail("I4", why)
    else:
        rel, ab = c["consts"]["rel"], c["consts"]["abs"]
        for name, zv, v, down in (("lower", zl, lo, True), ("upper", zu, hi, False)):
            if type(v) is not int:
                es.count(SIDE_INFINITE % name)
                if zv != v:
                    fail("I4", "the %s bound of the exact range is %s and the result's is %s"
                         % (name, v, F.fixed_hex(fmt, zv)))
                continue
            if not bops:
                continue
            if v == 0:
                es.count(SIDE_ZERO % name)
            conds = (c.get("texact") or {}).get(name)
            if conds and not failing(conds, x, es, SIDE_EW_FAILS % name + "",
                                     SIDE_EW_HOLDS % name):
                if _cmp(zv, q, v, s) != 0:
                    fail("I4", "exact_when holds for the %s bound, and it is not the range's %s"
                         % (name, _hexv(fmt, v, s)))
            if type(zv) is not int:
                continue
            m = min(s, q)
            Z, Vv = zv << (q - m), v << (s - m)
            dist = (Vv - Z) if down else (Z - Vv)
            ok, r = ratio_le(dist, abs(Vv), rel, ab, m)
            if not bounded(zs):
                # A finite bound beside an infinite one: not claimed (I4 is for a bounded result);
                # its distance is kept, to show what the stricter reading would give.
                es.track_max(SIDE_RATIO_UNCLAIMED % name, r, line)
                continue
            es.track_max(SIDE_RATIO % name, r, line)
            a = ab * (Fraction(1 << -m) if m < 0 else Fraction(1, 1 << m))
            if a <= rel * abs(Vv):
                es.track_max(SIDE_RATIO_REL % name, r, line)
            if not ok:
                fail("I4", "the %s bound is farther from the range than rel*|bound| + abs" % name)
    if bops:
        if not bounded(zs):
            es.count(BOUNDED_TO_UNBOUNDED)
        if c["bw"]:
            holds = True
            for kind, e in c["bw"]:
                a1, b1 = _limit_ratio(fmt, kind, e, lo, s)
                a2, b2 = _limit_ratio(fmt, kind, e, hi, s)
                r = (a1, b1) if a1 * b2 >= a2 * b1 else (a2, b2)
                holds = holds and r[0] <= r[1]
            es.count(I5_HOLDS if holds else I5_FAILS)
            if holds:
                es.track_max(I5_NEAR_HOLDS, r, line)
                if not bounded(zs):
                    fail("I5", "bounded operands whose range is within the limit of bounded_when "
                               "give an unbounded result")
            else:
                es.track_min(I5_NEAR_FAILS, r, line)
                if c["bexact"] and bounded(zs):
                    fail("I5", "bounded operands whose range is beyond the limit of bounded_when "
                               "give a bounded result, and the claim says exactly when")
    if c["zero_factor"]:
        zero = [n for n, st_ in sts.items() if st_[1] == 0 and st_[2] == 0]
        if zero:
            es.count(I6_APPLIES)
            if any(not bounded(st_) for st_ in sts.values()):
                es.count(I6_UNBOUNDED)
            if not (zl == 0 and zu == 0):
                fail("I6", "an operand is [0, 0] and the result is not [0, 0]")
    return out


def make_given(L, U):
    """The given state of a constructor's bounds L and U (values in the extended reals), by the
    first case that applies (architecture.md, "The constructors on every pair of values"):
    MAKE_NAN for a NaN bound, whatever the other; MAKE_EQUAL_INF for the same infinity twice;
    MAKE_REVERSED for L > U; otherwise the state of a nonempty interval (MAKE_POINT,
    MAKE_INTERVAL, MAKE_UNBOUNDED)."""
    if L == NAN or U == NAN:
        return MAKE_NAN
    if L == U and type(L) is not int:
        return MAKE_EQUAL_INF
    if XT.x_cmp(L, 0, U, 0) > 0:
        return MAKE_REVERSED
    if L == U:
        return MAKE_POINT
    return MAKE_INTERVAL if type(L) is int and type(U) is int else MAKE_UNBOUNDED


def make_cell(L, U):
    """The cell of the given bounds in the table of architecture.md, "The constructors on every
    pair of values": lo (row) and hi (column) each a NaN, -inf, a finite number (a, b) or +inf,
    and for two finite bounds whether a <= b."""
    def name(v, finite):
        return "NaN" if v == NAN else "-inf" if v == NINF else "+inf" if v == INF else finite
    s = MAKE_CELL % (name(L, "a"), name(U, "b"))
    if type(L) is int and type(U) is int:
        s += ", a <= b" if L <= U else ", a > b"
    return s


def _input_tokens(line):
    """The texts of the input limbs of a line, in the order of x (they keep the signs of zeros)."""
    return [t for t in line.partition(" -> ")[0].split()[2:] if not t.startswith("#")]


def k_makes_interval(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """The output is canonical, and by the first case that applies: the whole line when a given
    bound is a NaN, whatever the other, or when both are the same infinity; the empty set when
    the bounds are reversed, lo > hi; otherwise the interval of the given bounds (architecture.md,
    "The constructors on every pair of values"). Two limbs: a bound is a NaN or an infinity when
    its leading limb is (canonical inputs: the infinity followed by a zero of either sign), and
    the values are compared. The same infinity twice gave the empty set, as in IEEE 1788, until
    the owner's decision of 2026-11-20."""
    fmt = pl.fmt
    (a0, a1), (b0, b1) = c["given"]
    L, U = bound_value(fmt, x[a0:a1]), bound_value(fmt, x[b0:b1])
    es.applicable += 1
    given = make_given(L, U)
    es.count(given)
    es.count(make_cell(L, U))
    if a1 - a0 == 2:
        if given == MAKE_EQUAL_INF:
            toks = _input_tokens(line)
            if toks[a0 + 1].startswith("-") != toks[b0 + 1].startswith("-"):
                es.count(MAKE_INF_TAILS)
        elif given == MAKE_REVERSED and x[a0] == x[b0]:
            es.count(MAKE_REVERSED_LEAD)
    if given in (MAKE_NAN, MAKE_EQUAL_INF):
        want = ("nonempty", NINF, INF)
    elif given == MAKE_REVERSED:
        want = ("empty", INF, NINF)
    else:
        want = ("nonempty", L, U)
    zs = _out_state(fmt, z, c)
    if zs is None:
        es.count("failed: not canonical")
        return ["makes_interval: the result is not a canonical interval"
                + _out_defect(fmt, es, z, c)]
    if zs != want:
        es.count("failed: not the interval of the given bounds")
        return ["makes_interval: the result is %s, not %s" % (_iv_show(fmt, zs), _iv_show(fmt, want))]
    return []


def _iv_show(fmt, st):
    if st[0] == "empty":
        return "the empty set"
    return "[%s, %s]" % (F.fixed_hex(fmt, st[1]), F.fixed_hex(fmt, st[2]))


def _ball_env(fmt, x, balls):
    """(states, env) of the ball operands: 'finite', 'whole' or 'empty', and each ball name's
    members as an interval at scale qmin."""
    states, env = {}, {}
    for b, ((lo, hi), ri) in balls.items():
        stt = XT.ball_state(fmt, x[lo:hi], x[ri])
        states[b] = stt
        if stt == "finite":
            cv, r = sum(x[lo:hi]), x[ri]
            env[b] = (cv - r, cv + r, fmt.qmin)
        else:
            env[b] = (NINF, INF, fmt.qmin)
    return states, env


def _ball_counts(es, states):
    for stt in states.values():
        es.count(BALL_EMPTY if stt == "empty" else BALL_WHOLE if stt == "whole" else BALL_FINITE)


def k_set_bound(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """+inf (below) or -inf (above) for an empty ball; otherwise at most (at least) every value of
    the set over the members of the balls, and with tight its glb (lub) rounded down (up) in the
    format with overflow, or within steps of it."""
    fmt = pl.fmt
    below = c["side"] == "below"
    o = z[c["out"]]
    es.applicable += 1
    states, env = _ball_env(fmt, x, c["balls"])
    _ball_counts(es, states)
    if "empty" in states.values():
        want = INF if below else NINF
        if o != want:
            es.count("failed: empty ball")
            return ["set_bound: an empty ball gives %s, not %s" % (o, want)]
        return []
    if o == NAN:
        es.count("failed: NaN")
        return ["set_bound: a NaN output"]
    lo, hi, s = range_eval(c["tree"], env)
    t = lo if below else hi
    side = _cmp(o, fmt.qmin, t, s)
    if (side > 0) if below else (side < 0):
        es.count("failed: wrong side")
        return ["set_bound: the output %s is %s the set's %s %s" % (
            F.fixed_hex(fmt, o), "above" if below else "below",
            "greatest lower bound" if below else "least upper bound", _hexv(fmt, t, s))]
    name = "lower" if below else "upper"
    if c["tight"]:
        why = _judge_rounded_side(fmt, es, name, o, t, s, c["steps"], False, below)
        if why:
            es.count("failed: tight")
            return ["set_bound: " + why]
    elif type(t) is int:
        es.count(SIDE_EXACT % name if _round_side(fmt, t, s, True) == _round_side(fmt, t, s, False)
                 else SIDE_INEXACT % name)
    else:
        es.count(SIDE_INFINITE % name)
    return []


def k_interval_of_ball(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """Z canonical, empty exactly when a ball is; every value of the set a member of Z; its bounds
    the set's glb rounded down and lub rounded up in the format with overflow, or within steps."""
    fmt = pl.fmt
    es.applicable += 1
    out = []
    fail = XT._failer(es, out)
    if c.get("two"):
        return _interval_of_ball_two(pl, c, es, x, z, fail, out, line)
    zs = interval_state(fmt, [z[c["lower"]]], [z[c["upper"]]])
    if zs is None:
        fail("canonical", "the result is not a canonical interval")
        return out
    states, env = _ball_env(fmt, x, c["balls"])
    _ball_counts(es, states)
    if "empty" in states.values():
        if zs[0] != "empty":
            fail("empty", "an empty ball gives a result that is not empty")
        return out
    if zs[0] == "empty":
        fail("empty", "the empty set from a ball that is not empty")
        return out
    lo, hi, s = range_eval(c["tree"], env)
    for name, zv, v, down in (("lower", zs[1], lo, True), ("upper", zs[2], hi, False)):
        cmpv = _cmp(zv, fmt.qmin, v, s)
        if (cmpv > 0) if down else (cmpv < 0):
            fail("containment", "the %s bound does not contain the set" % name)
            continue
        why = _judge_rounded_side(fmt, es, name, zv, v, s, c["steps"], False, down)
        if why:
            fail("tight", why)
    return out


def _interval_of_ball_two(pl, c, es, x, z, fail, out, line):
    """interval_of_ball with bounds of two limbs (architecture.md, "... the conversions of two
    limbs"): Z canonical, empty exactly when the ball is, containing every value of the set; for a
    finite ball and a bounded Z each bound within rel*|bound| + abs of the set's on its side; for a
    finite ball, a side whose conditions of exact_when hold the set's bound exactly (whether or not
    Z is bounded: the stricter reading, as for encloses_interval), and Z bounded when every member
    is within the limit of each condition of bounded_when."""
    fmt = pl.fmt
    q = fmt.qmin
    zs = interval_state(fmt, z[c["lower_sl"][0]:c["lower_sl"][1]],
                        z[c["upper_sl"][0]:c["upper_sl"][1]])
    if zs is None:
        fail("canonical", "the result is not a canonical interval")
        return out
    states, env = _ball_env(fmt, x, c["balls"])
    _ball_counts(es, states)
    es.count(RES_EMPTY if zs[0] == "empty" else RES_BOUNDED if bounded(zs) else RES_UNBOUNDED)
    if "empty" in states.values():
        if zs[0] != "empty":
            fail("empty", "an empty ball gives a result that is not empty")
        return out
    if zs[0] == "empty":
        fail("empty", "the empty set from a ball that is not empty")
        return out
    lo, hi, s = range_eval(c["tree"], env)
    zl, zu = zs[1], zs[2]
    if _cmp(zl, q, lo, s) > 0:
        fail("containment", "the lower bound %s is above the set's greatest lower bound %s"
             % (F.fixed_hex(fmt, zl), _hexv(fmt, lo, s)))
    if _cmp(zu, q, hi, s) < 0:
        fail("containment", "the upper bound %s is below the set's least upper bound %s"
             % (F.fixed_hex(fmt, zu), _hexv(fmt, hi, s)))
    if any(st_ != "finite" for st_ in states.values()):
        return out
    rel, ab = c["consts"]["rel"], c["consts"]["abs"]
    for name, zv, v, down in (("lower", zl, lo, True), ("upper", zu, hi, False)):
        if v == 0:
            es.count(SIDE_ZERO % name)
        conds = (c.get("texact") or {}).get(name)
        if conds and not failing(conds, x, es, SIDE_EW_FAILS % name, SIDE_EW_HOLDS % name):
            if _cmp(zv, q, v, s) != 0:
                fail("exact_when", "exact_when holds for the %s bound, and it is not the set's %s"
                     % (name, _hexv(fmt, v, s)))
        if type(zv) is not int:
            continue
        m = min(s, q)
        Z, Vv = zv << (q - m), v << (s - m)
        dist = (Vv - Z) if down else (Z - Vv)
        ok, r = ratio_le(dist, abs(Vv), rel, ab, m)
        if not bounded(zs):
            es.track_max(SIDE_RATIO_UNCLAIMED % name, r, line)
            continue
        es.track_max(SIDE_RATIO % name, r, line)
        a = ab * (Fraction(1 << -m) if m < 0 else Fraction(1, 1 << m))
        if a <= rel * abs(Vv):
            es.track_max(SIDE_RATIO_REL % name, r, line)
        if not ok:
            fail("tight", "the %s bound is farther from the set than rel*|bound| + abs" % name)
    if not bounded(zs):
        es.count(BOUNDED_TO_UNBOUNDED)
    # bounded_when, in the formats of statement_format (counted as not claimed in any other).
    claimed, beyond = statement_format(fmt)
    if c["bw"] and not claimed:
        es.count(I5_RANGE)
    elif c["bw"]:
        holds = True
        for kind, e in c["bw"]:
            a1, b1 = _limit_ratio(fmt, kind, e, lo, s)
            a2, b2 = _limit_ratio(fmt, kind, e, hi, s)
            r = (a1, b1) if a1 * b2 >= a2 * b1 else (a2, b2)
            holds = holds and r[0] <= r[1]
        es.count(I5_HOLDS if holds else I5_FAILS)
        if holds:
            es.track_max(I5_NEAR_HOLDS, r, line)
            if not bounded(zs):
                fail("bounded_when", "a finite ball whose members are within the limit of "
                                     "bounded_when gives an unbounded result" + beyond)
        else:
            es.track_min(I5_NEAR_FAILS, r, line)
    return out


def k_interval_set(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """union: the hull of the nonempty operands, empty when both are; intersection: the larger
    lower bound and the smaller upper bound, empty when an operand is or they cross. Exact."""
    fmt = pl.fmt
    es.applicable += 1
    a, b = (_state_of(fmt, x, pair) for pair in c["ivs"])
    zs = _out_state(fmt, z, c)
    if zs is None:
        es.count("failed: not canonical")
        return ["interval_set: the result is not a canonical interval"
                + _out_defect(fmt, es, z, c)]
    ne = [t for t in (a, b) if t[0] != "empty"]
    if len(ne) < 2:
        es.count(SET_BOTH_EMPTY if not ne else SET_EMPTY_OPERAND)
    else:
        lo2 = max((a[1], b[1]), key=_key)
        hi2 = min((a[2], b[2]), key=_key)
        d = XT.x_cmp(lo2, 0, hi2, 0)
        es.count(SET_DISJOINT if d > 0 else SET_TOUCH if d == 0 else SET_OVERLAP)
    if c["op"] == "union":
        if not ne:
            want = ("empty", INF, NINF)
        else:
            want = ("nonempty", min((t[1] for t in ne), key=_key), max((t[2] for t in ne), key=_key))
    else:
        if len(ne) < 2:
            want = ("empty", INF, NINF)
        else:
            lo2 = max((a[1], b[1]), key=_key)
            hi2 = min((a[2], b[2]), key=_key)
            want = ("empty", INF, NINF) if XT.x_cmp(lo2, 0, hi2, 0) > 0 else ("nonempty", lo2, hi2)
    es.count(RES_EMPTY if zs[0] == "empty" else RES_BOUNDED if bounded(zs) else RES_UNBOUNDED)
    if zs != want:
        es.count("failed: not the %s" % c["op"])
        return ["interval_set: the result is %s, not %s" % (_iv_show(fmt, zs), _iv_show(fmt, want))]
    return []


def _odd_eta_low(fmt, v):
    """v is an odd multiple of eta below 2N: halving it is not exact."""
    return type(v) is int and v & 1 == 1 and abs(v) < 2 * fmt.lam


def k_ball_of_interval(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """For a bounded X = [l, h], m = (l + h)/2: c, r finite, l <= c <= h, |c - m| <= rel*|m| + abs,
    [c - r, c + r] contains X, and with smallest_radius r = RU(max(c - l, h - c)).  Otherwise by
    special: ieee1788, the values of mid and rad of IEEE 1788; ball, a canonical ball (the whole
    line for an unbounded X, the empty ball for the empty set)."""
    fmt = pl.fmt
    q = fmt.qmin
    es.applicable += 1
    out = []
    fail = XT._failer(es, out)
    X_ = _state_of(fmt, x, c["given"])
    cls = interval_class(X_)
    es.count(cls if cls != X_POINT else X_BOUNDED)
    if cls == X_POINT:
        es.count(X_POINT)
    cw = z[c["center"][0]:c["center"][1]]
    r = z[c["radius"]]
    ieee = c["special"] == "ieee1788"
    # With ieee1788 the midpoint of a bounded X is a finite canonical number: a clause that
    # promises a finite result (the sum of the two halves is proved finite where p < e_max), so
    # by the ruling of 2026-11-21 it is claimed in the formats of statement_format, its
    # failure in a wider subnormal range a finding (beyond), and in any other format counted as
    # not claimed (CENTER_RANGE); there a center that is not finite (lost: a limb a NaN or an
    # infinity) is judged by containment alone (_center_lost).
    lost, beyond = False, ""
    if ieee and X_[0] != "empty" and bounded(X_):
        claimed, beyond = statement_format(fmt)
        if not claimed:
            es.count(CENTER_RANGE)
            lost = not all(type(v) is int for v in cw)
    if ieee and len(cw) == 2 and not lost and not XT.canonical(fmt, cw):
        # The midpoint of two limbs is a canonical number, for every X (architecture.md, "... the
        # conversions of two limbs").
        fail("canonical", "the center (%s) is not a canonical number of two limbs%s"
             % (" ".join(F.fixed_hex(fmt, v) for v in cw), beyond))
        return out
    if X_[0] != "empty" and bounded(X_) and c.get("fw"):
        return _ball_of_interval_fw(pl, c, es, x, X_, cw, r, ieee, fail, out, line, lost)
    if X_[0] == "empty" or not bounded(X_):
        if ieee:
            if X_[0] == "empty":
                ok = all(v == NAN for v in cw) and r == NAN
                want = "two NaN"
            else:
                L, U = X_[1], X_[2]
                m = 0 if (L == NINF and U == INF) else fmt.omega if U == INF else -fmt.omega
                ok = cw[0] == m and all(v == 0 for v in cw[1:]) and r == INF
                want = "(%s, +inf)" % F.fixed_hex(fmt, m)
        else:
            stt = XT.ball_state(fmt, cw, r)
            want = "the empty ball" if X_[0] == "empty" else "the whole line"
            ok = stt == ("empty" if X_[0] == "empty" else "whole")
        if not ok:
            fail("special", "%s gives the ball (%s, %s), not %s" % (
                cls, " ".join(F.fixed_hex(fmt, v) for v in cw), F.fixed_hex(fmt, r), want))
        return out
    L, U = X_[1], X_[2]
    if _odd_eta_low(fmt, L) or _odd_eta_low(fmt, U):
        es.count(X_ODD)
    if lost:
        return _center_lost(es, r, fail, out)
    if not all(type(v) is int for v in cw) or type(r) is not int or not F.normalized_limbs(fmt, cw):
        fail("finite", "a bounded interval gives a center or a radius that is not finite (or a "
                       "center that is not normalized)" + beyond)
        return out
    cv = sum(cw)
    if r < 0:
        fail("finite", "a negative radius")
        return out
    if cv < L or cv > U:
        fail("center", "the center is outside the interval")
    # m = (L + U)/2 at scale q - 1; c at scale q.
    M2 = L + U
    C2 = 2 * cv
    ok, rr = ratio_le(abs(C2 - M2), abs(M2), c["consts"]["rel"], c["consts"]["abs"], q - 1)
    es.track_max(MID_RATIO, rr, line)
    es.count(MID_EXACT if C2 == M2 else MID_INEXACT)
    if not ok:
        fail("midpoint", "the center is farther from the midpoint than rel*|m| + abs")
    if cv - r > L or cv + r < U:
        fail("containment", "[c - r, c + r] does not contain the interval")
    if c["smallest"]:
        need = max(cv - L, U - cv)
        rmin = F.rdir(fmt, need, q, True)
        want = INF if rmin > fmt.omega else rmin
        if r != want:
            fail("smallest_radius", "the radius %s is not the smallest, %s" % (
                F.fixed_hex(fmt, r), F.fixed_hex(fmt, want)))
    return out


FW_HOLDS = "finite_when holds"
FW_FAILS = "finite_when fails: "
FW_INFINITE = "bounded X, the radius +inf"
FW_WHOLE = "bounded X, the whole line"
FW_FINITE_FAILS = "finite_when fails and the ball is finite (its center not claimed)"
FW_RATIO_FINITE = "a finite radius: largest max|bound| / 2^(qmax+p)"
FW_RATIO_INFINITE = "the radius +inf: smallest max|bound| / 2^(qmax+p)"
FW_RANGE = "finite_when not claimed: a format of no statement (e_max <= p, or eta above binary_float's)"
I5_RANGE = "bounded_when not claimed: a format of no statement (e_max <= p, or eta above binary_float's)"
# The midpoint of a bounded X (ball_of_interval with ieee1788) and the parts of a split that rest
# on it, by the ruling of 2026-11-21: counted on every bounded X in a format of no
# statement, and the lines where the center (the point of split) is not finite.
CENTER_RANGE = ("a finite center not claimed: a format of no statement (e_max <= p, or eta above "
                "binary_float's)")
CENTER_LOST = "bounded X, the center not finite (not claimed)"
SPLIT_RANGE = ("a split at a point of X not claimed: a format of no statement (e_max <= p, or eta "
               "above binary_float's)")
SPLIT_LOST = "bounded X, the point of split not finite (not claimed)"


def _center_lost(es, r, fail, out):
    """ball_of_interval with ieee1788, a bounded X in a format of no statement whose center is not
    finite (a limb a NaN or an infinity): the clauses that rest on a finite center (finite and
    canonical, between the bounds, near the midpoint, the smallest radius about it) are not
    claimed, and the line is counted; containment, which does not rest on it, is judged: no real
    number is within a finite radius of a center that is not finite, so only the radius +inf
    contains X."""
    es.count(CENTER_LOST)
    if r != INF:
        fail("containment", "the center is not finite and the radius is not +inf: [c - r, c + r] "
                            "does not contain the interval")
    return out


def statement_format(fmt):
    """(claimed, beyond) for a clause that promises a finite or bounded result, by the
    ruling of 2026-11-21 (architecture.md, "The formats of the statements"): claimed in the formats
    of binary_float's shape, and judged in those of a wider subnormal range too, where a failure
    is a finding to report, not a violated claim (beyond, the text its failure carries); not
    claimed in any other toy format. The rule of V4 of the ball vectors, bvfolds.v4_range and
    bvfolds.v4_beyond, for finite_when of ball_of_interval and bounded_when of interval_of_ball
    with bounds of two limbs."""
    from . import bvfolds as BF
    return BF.v4_range(fmt), BF.v4_beyond(fmt)


def _fw_conditions(fmt, c, x, es):
    """Whether every condition of finite_when holds of the bounded interval x (counted, unless es
    is None), and max|bound| / 2^(qmax+p) as a fraction."""
    q = fmt.qmin
    bad = []
    big = 0
    for (lo, hi), n, ex in c["fw"]:
        v = abs(bound_value(fmt, x[lo:hi]))
        big = max(big, v)
        k = fmt.qmax + fmt.p + ex - q
        ok = v <= (1 << k) if k >= 0 else (v << -k) <= 1
        if not ok:
            bad.append("|%s| <= 2^(qmax+p%+d)" % (n, ex) if ex else "|%s| <= 2^(qmax+p)" % n)
    for t in (bad if es is not None else ()):
        es.count(FW_FAILS + t)
    if not bad and es is not None:
        es.count(FW_HOLDS)
    T = fmt.qmax + fmt.p - q
    return not bad, (big, 1 << T) if T >= 0 else (big << -T, 1)


def _ball_of_interval_fw(pl, c, es, x, X_, cw, r, ieee, fail, out, line, lost=False):
    """ball_of_interval with finite_when, for a bounded X = [l, h], m = (l + h)/2 (architecture.md,
    "... the conversions of two limbs"): with ieee1788 the center finite, between the bounds and
    within rel*|m| + abs of m, the radius +inf or a finite number with which the center contains X,
    finite when every condition holds; with ball a canonical ball that contains X, and when every
    condition holds a finite one whose center is as without the field. The clause of the
    conditions is claimed in the formats of statement_format, and counted as not claimed in any
    other (then the radius may be +inf, and with ball the center is not claimed); so is, with
    ieee1788, the finite center (lost: in a format of no statement a center that is not finite,
    judged by containment alone, k_ball_of_interval)."""
    fmt = pl.fmt
    q = fmt.qmin
    L, U = X_[1], X_[2]
    if _odd_eta_low(fmt, L) or _odd_eta_low(fmt, U):
        es.count(X_ODD)
    claimed, beyond = statement_format(fmt)
    holds, ratio = _fw_conditions(fmt, c, x, es if claimed else None)
    if not claimed:
        es.count(FW_RANGE)
        holds = False
    if ieee:
        if lost:
            if r == INF:
                es.count(FW_INFINITE)
            return _center_lost(es, r, fail, out)
        bad_c = not all(type(v) is int for v in cw) or not F.normalized_limbs(fmt, cw)
        if bad_c or not (r == INF or (type(r) is int and r >= 0)):
            fail("finite", "a bounded interval gives a center that is not a finite normalized "
                           "number, or a radius that is neither finite and nonnegative nor +inf"
                 + (beyond if bad_c else ""))
            return out
        finite_center = True
    else:
        stt = XT.ball_state(fmt, cw, r)
        if stt is None:
            fail("canonical", "a bounded interval gives a ball that is not canonical")
            return out
        if stt == "empty":
            fail("containment", "a bounded interval gives the empty set")
            return out
        finite_center = stt == "finite"
    if r == INF:
        es.count(FW_INFINITE if ieee else FW_WHOLE)
        if claimed:
            es.track_min(FW_RATIO_INFINITE, ratio, line)
        if holds:
            fail("finite_when", "every condition of finite_when holds and the radius is +inf"
                 + beyond)
            return out
        if not ieee:
            return out
    else:
        if claimed:
            es.track_max(FW_RATIO_FINITE, ratio, line)
        if not holds and not ieee and claimed:
            es.count(FW_FINITE_FAILS)
    cv = sum(cw)
    if type(r) is int and (cv - r > L or cv + r < U):
        fail("containment", "[c - r, c + r] does not contain the interval")
    if not finite_center or (not ieee and not holds):
        return out
    if cv < L or cv > U:
        fail("center", "the center is outside the interval")
    M2, C2 = L + U, 2 * cv
    ok, rr = ratio_le(abs(C2 - M2), abs(M2), c["consts"]["rel"], c["consts"]["abs"], q - 1)
    es.track_max(MID_RATIO, rr, line)
    es.count(MID_EXACT if C2 == M2 else MID_INEXACT)
    if not ok:   # (worded apart from k_ball_of_interval's, that a mutant finds each once)
        fail("midpoint", "the center is farther from the midpoint than rel*|m| + abs (finite_when)")
    return out


def k_splits(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """Both parts canonical; X empty: both empty; otherwise neither, the first part's lower bound
    X's lower bound, the second part's upper bound X's upper bound, and the first part's upper bound
    the second part's lower bound, a point (a member) of X."""
    fmt = pl.fmt
    es.applicable += 1
    X_ = _state_of(fmt, x, c["given"])
    es.count(interval_class(X_))
    # For a bounded X the point of split is the midpoint, and that the parts are canonical
    # intervals meeting at a point of X rests on it being finite: by the ruling of
    # 2026-11-21 claimed in the formats of statement_format (a failure in a wider subnormal range
    # a finding, beyond), and in any other format counted as not claimed (SPLIT_RANGE), where a
    # point of split that is not finite is judged by the rest of the clause alone (_split_lost).
    beyond = ""
    if X_[0] != "empty" and bounded(X_):
        claimed, beyond = statement_format(fmt)
        if not claimed:
            es.count(SPLIT_RANGE)
            inner = [z[c["parts"][0][1][0]:c["parts"][0][1][1]],
                     z[c["parts"][1][0][0]:c["parts"][1][0][1]]]
            if not all(type(v) is int for v in inner[0] + inner[1]):
                return _split_lost(fmt, c, es, X_, z, inner)
    parts = [interval_state(fmt, z[a[0]:a[1]], z[b[0]:b[1]]) for a, b in c["parts"]]
    if None in parts:
        es.count("failed: a part not canonical")
        return ["splits: a part is not a canonical interval" + beyond]
    A, B = parts
    if X_[0] == "empty":
        if A[0] != "empty" or B[0] != "empty":
            es.count("failed: empty")
            return ["splits: the empty set does not give the empty set twice"]
        return []
    if A[0] == "empty" or B[0] == "empty":
        es.count("failed: empty")
        return ["splits: a part of a nonempty interval is empty"]
    why = []
    if A[1] != X_[1]:
        why.append("the first part's lower bound is not X's")
    if B[2] != X_[2]:
        why.append("the second part's upper bound is not X's")
    if A[2] != B[1]:
        why.append("the first part's upper bound is not the second part's lower bound" + beyond)
    m = A[2]
    if type(m) is not int or XT.x_cmp(m, 0, X_[1], 0) < 0 or XT.x_cmp(m, 0, X_[2], 0) > 0:
        why.append("the split point %s is not a member of X%s" % (F.fixed_hex(fmt, m), beyond))
    if why:
        es.count("failed: not a split")
        return ["splits: " + "; ".join(why)]
    return []


def _split_lost(fmt, c, es, X_, z, inner):
    """splits of a bounded X in a format of no statement whose point of split is not finite (a limb
    of the first part's upper bound or of the second part's lower bound a NaN or an infinity): that
    the parts are canonical intervals meeting at a point of X rests on that point and is not
    claimed, and the line is counted; what does not rest on it is judged: the first part's lower
    bound is X's, the second part's upper bound X's, and the first part ends with the limbs the
    second begins with (a NaN matching a NaN)."""
    es.count(SPLIT_LOST)
    (a0, a1), (b0, b1) = c["parts"][0][0], c["parts"][1][1]
    why = []
    if bound_value(fmt, z[a0:a1]) != X_[1]:
        why.append("the first part's lower bound is not X's")
    if bound_value(fmt, z[b0:b1]) != X_[2]:
        why.append("the second part's upper bound is not X's")
    if inner[0] != inner[1]:
        why.append("the first part's upper bound is not the second part's lower bound")
    if why:
        es.count("failed: not a split")
        return ["splits: " + "; ".join(why)]
    return []


def k_makes_ball_iv(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """makes_ball from the bounds of an interval, by the first case that applies: the whole line
    for a NaN bound, whatever the other, or for the same infinity twice; the empty set for
    reversed bounds, lo > hi; otherwise (lo <= hi) a finite ball that contains [lo, hi] when both
    are finite (with midpoint_when holding: the center (lo + hi)/2 exactly and the radius
    (hi - lo)/2 rounded up), and the whole line when a bound is infinite (architecture.md, "The
    constructors on every pair of values"). The same infinity twice gave the empty set until the
    owner's decision of 2026-11-20."""
    fmt = pl.fmt
    lo, hi = x[c["given"][0]], x[c["given"][1]]
    cw = z[c["center"][0]:c["center"][1]]
    r = z[c["radius"]]
    es.applicable += 1
    given = make_given(lo, hi)
    es.count(given)
    es.count(make_cell(lo, hi))
    if given == MAKE_REVERSED:
        want = "empty"
    elif given in (MAKE_INTERVAL, MAKE_POINT):
        want = "finite"
    else:
        want = "whole"
    stt = XT.ball_state(fmt, cw, r)
    if stt is None:
        es.count("failed: not canonical")
        return ["makes_ball: the result is not a canonical ball"]
    if stt != want:
        es.count("failed: %s instead of %s" % (XT.STATE_TEXT[stt], XT.STATE_TEXT[want]))
        return ["makes_ball: the %s instead of the %s" % (XT.STATE_TEXT[stt], XT.STATE_TEXT[want])]
    if want != "finite":
        return []
    cv = sum(cw)
    if cv - r > lo or cv + r < hi:
        es.count("failed: does not contain the interval")
        return ["makes_ball: the ball does not contain [lo, hi]"]
    if c.get("mid_consts"):
        # rel, abs and smallest_radius (the conversions of two limbs): the center between the
        # bounds and within rel*|m| + abs of m = (lo + hi)/2, the radius RU(max(c - lo, hi - c)).
        why = []
        if cv < lo or cv > hi:
            es.count("failed: center")
            why.append("makes_ball: the center is outside [lo, hi]")
        M2, C2 = lo + hi, 2 * cv
        ok, rr = ratio_le(abs(C2 - M2), abs(M2), c["consts"]["rel"], c["consts"]["abs"],
                          fmt.qmin - 1)
        es.track_max(MID_RATIO, rr, line)
        es.count(MID_EXACT if C2 == M2 else MID_INEXACT)
        if not ok:
            es.count("failed: midpoint")
            why.append("makes_ball: the center is farther from the midpoint than rel*|m| + abs")
        if c["smallest"]:
            rmin = F.rdir(fmt, max(cv - lo, hi - cv), fmt.qmin, True)
            want = INF if rmin > fmt.omega else rmin
            if r != want:
                es.count("failed: smallest_radius")
                why.append("makes_ball: the radius %s is not the smallest, %s" % (
                    F.fixed_hex(fmt, r), F.fixed_hex(fmt, want)))
        if why:
            return why
    if c["mid"]:
        if all(x[j] % 2 == 0 for j in c["mid"]):
            es.count(MID_HOLDS)
            if 2 * cv != lo + hi:
                es.count("failed: midpoint_when")
                return ["makes_ball: midpoint_when holds and the center is not (lo + hi)/2"]
            rw = F.rdir(fmt, hi - lo, fmt.qmin - 1, True)
            if r != rw:
                es.count("failed: midpoint_when")
                return ["makes_ball: midpoint_when holds and the radius is not (hi - lo)/2 rounded "
                        "up (%s)" % F.fixed_hex(fmt, rw)]
        else:
            es.count(MID_FAILS)
    return []


def _zero_factor(c, x, z, es):
    """zero_factor of bound and rounded: (applies, reasons)."""
    a, b = (x[j] for j in c["factors"])
    if a != 0 and b != 0:
        return False, []
    es.applicable += 1
    es.count(ZF_ZERO)
    if type(a) is not int or type(b) is not int:
        es.count(ZF_ZERO_INF)
    if z[c["first"]] != 0:
        return True, ["%s: a zero factor and the output is not zero" % c["kind"][:-3]]
    return True, []


def k_bound_zf(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    done, out = _zero_factor(c, x, z, es)
    return out if done else XT.k_bound(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus)


def k_rounded_zf(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    done, out = _zero_factor(c, x, z, es)
    return out if done else XT.k_rounded(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus)


EXT_KINDS = {"outward": k_outward, "encloses_interval": k_encloses_interval,
             "makes_interval": k_makes_interval, "set_bound": k_set_bound,
             "interval_of_ball": k_interval_of_ball, "interval_set": k_interval_set,
             "ball_of_interval": k_ball_of_interval, "splits": k_splits,
             "makes_ball_iv": k_makes_ball_iv, "bound_zf": k_bound_zf, "rounded_zf": k_rounded_zf}
FINITE_KINDS = {"outward": finite_outward}


def requirement_violated(ep, x, r):
    """The text of the requirement r = ("interval", text, lo slice, hi slice), ("upward", text,
    upper slice, nlower slice) or ("not_nan", text, slice) when the operands violate it, or
    None."""
    fmt = ep.pl.fmt
    if r[0] == "upward":
        # upward(U, N), the round-up interval (upward.py): the stored pair of a canonical state.
        return r[1] if upward_state(x[r[2][0]], x[r[3][0]]) is None else None
    if r[0] == "interval":
        (alo, ahi), (blo, bhi) = r[2], r[3]
        return r[1] if interval_state(fmt, x[alo:ahi], x[blo:bhi]) is None else None
    lo, hi = r[2]
    return r[1] if x[lo] == NAN else None


# The judges of the extended domain dispatch on the kind of a plan entry (extended.KINDS).
XT.KINDS.update(EXT_KINDS)
