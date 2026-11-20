"""Judging the kernels of the extended domain (the non-finite layer).

architecture.md, "Claims of the non-finite layer": a kernel with "domain": "extended" takes
operands that may be infinite or NaN, and every completed line is judged.  The statements are
F1 to F5 of milestone1.md ("IEEE-like results") for `extends`, B1 to B4 ("Ball kernels") for
`encloses`, the constructor kinds `represents` and `makes_ball`, and the extended readings of
`normalized`, `error`, `predicate`, `rounded` and `upper`.

Finite limbs are fixed values (integers N meaning N * eta, see fmt.py) and the non-finite ones
the strings fmt.POS_INF, fmt.NEG_INF and fmt.NAN, so every verdict is still decided with Python
integers.  An exact value is an integer at a scale known in advance, or one of those strings:
the arithmetic of the extended reals with IEEE 754's NaN for the undefined cases (inf - inf,
0 * inf), and nothing else.
"""

from . import directed as D
from . import expr as EX
from . import fmt as F

INF, NINF, NAN = F.POS_INF, F.NEG_INF, F.NAN
MASK_TEXT = {"0": 0, "1": 1}


# ---------------------------------------------------------------------------
# The extended reals

def x_neg(v):
    if type(v) is int:
        return -v
    return NINF if v == INF else INF if v == NINF else NAN


def x_abs(v):
    if type(v) is int:
        return abs(v)
    return NAN if v == NAN else INF


def x_sign(v):
    """-1, 0 or 1, or None for a NaN."""
    if type(v) is int:
        return (v > 0) - (v < 0)
    return None if v == NAN else 1 if v == INF else -1


def x_add(a, b, sa=0, sb=0):
    """a * 2^sa + b * 2^sb, at scale min(sa, sb) when finite."""
    if type(a) is int and type(b) is int:
        s = min(sa, sb)
        return (a << (sa - s)) + (b << (sb - s))
    if a == NAN or b == NAN:
        return NAN
    if type(a) is not int and type(b) is not int and a != b:
        return NAN                   # inf - inf
    return a if type(a) is not int else b


def x_mul(a, b):
    if type(a) is int and type(b) is int:
        return a * b
    sa, sb = x_sign(a), x_sign(b)
    if sa is None or sb is None or sa == 0 or sb == 0:
        return NAN                   # a NaN, or 0 * inf
    return INF if sa == sb else NINF


def group_value(limbs):
    """The value of a group of limbs in the extended reals: their sum when all are finite,
    otherwise the infinity they carry, or NaN (a NaN limb, or infinities of both signs)."""
    if all(type(v) is int for v in limbs):
        return sum(limbs)
    if NAN in limbs or (INF in limbs and NINF in limbs):
        return NAN
    return INF if INF in limbs else NINF


def ext_eval(tree, leaf):
    """(value, scale) of an expression tree, leaf(name) giving (value, scale) of a name.  The
    scale is the one compile_tree computes, whether or not the value is finite."""
    k = tree[0]
    if k == "name":
        return leaf(tree[1])
    if k == "neg":
        v, s = ext_eval(tree[1], leaf)
        return x_neg(v), s
    if k == "abs":
        v, s = ext_eval(tree[1], leaf)
        return x_abs(v), s
    a, sa = ext_eval(tree[1], leaf)
    b, sb = ext_eval(tree[2], leaf)
    if k == "*":
        return x_mul(a, b), sa + sb
    if k == "-":
        b = x_neg(b)
    return x_add(a, b, sa, sb), min(sa, sb)


def x_cmp(a, sa, b, sb):
    """-1, 0 or 1 for a < b, a = b, a > b in the extended reals, or None if either is NaN."""
    if a == NAN or b == NAN:
        return None
    if type(a) is int and type(b) is int:
        s = min(sa, sb)
        d = (a << (sa - s)) - (b << (sb - s))
        return (d > 0) - (d < 0)
    ra = 0 if type(a) is int else x_sign(a)
    rb = 0 if type(b) is int else x_sign(b)
    return (ra > rb) - (ra < rb)


def ieee_op(fmt, op, a, b):
    """The operation of T on two limbs, by the rules of IEEE 754: add, sub or mul, rounded to
    nearest with overflow to the infinities."""
    if type(a) is int and type(b) is int:
        if op == "mul":
            return F.rn(fmt, a * b, 2 * fmt.qmin)
        return F.rn_fixed(fmt, a + b if op == "add" else a - b)
    if op == "mul":
        return x_mul(a, b)
    return x_add(a, b if op == "add" else x_neg(b))


# ---------------------------------------------------------------------------
# Canonical values

def canonical(fmt, limbs):
    """milestone1.md: finite and normalized, or (+-inf, 0, ...), or every limb a NaN.  A
    one-limb value is any value.  Signs of zeros are not read (the parser drops them)."""
    h = limbs[0]
    if type(h) is int:
        return all(type(v) is int for v in limbs) and F.normalized_limbs(fmt, limbs)
    if h == NAN:
        return all(v == NAN for v in limbs)
    return all(v == 0 for v in limbs[1:])


def ball_state(fmt, c, r):
    """'finite', 'whole' or 'empty' for a canonical ball (center limbs c, radius r), else
    None: a finite ball has a canonical finite center and a finite radius >= 0; the whole line
    is center 0 and radius +inf; the empty set has every limb a NaN."""
    if type(r) is int and all(type(v) is int for v in c):
        return "finite" if r >= 0 and F.normalized_limbs(fmt, c) else None
    if r == INF and all(v == 0 for v in c):
        return "whole"
    if r == NAN and all(v == NAN for v in c):
        return "empty"
    return None


STATE_TEXT = {"finite": "finite ball", "whole": "whole line", "empty": "empty set"}


def _gather(z, ranges):
    w = []
    for lo, hi in ranges:
        w.extend(z[lo:hi])
    return w


# ---------------------------------------------------------------------------

class ExtPlan:
    """What the extended judge needs about one (kernel, format) beyond the finite Plan."""

    def __init__(self, pl, plan_class):
        k = pl.kernel
        fmt = pl.fmt
        self.pl = pl
        self.limb_slots = [i for i in range(pl.n_in) if i not in pl.in_masks]
        self.heads = [lo for lo, _ in pl.groups]
        # The exponent of the overflow threshold 2^(qmax + p), and as a fixed value.
        self.T = fmt.qmax + fmt.p
        self.T_fixed = 1 << (self.T - fmt.qmin)
        self.req = []
        for r in k.requires:
            if r[0] == "ball":
                self.req.append(("ball", "requires ball(%s, %s)" % (r[1], r[2]),
                                 pl.in_slices[r[1]], pl.in_slices[r[2]][0]))
            elif r[0] == "interval":
                self.req.append(("interval", "requires interval(%s, %s)" % (r[1], r[2]),
                                 pl.in_slices[r[1]], pl.in_slices[r[2]]))
            else:
                self.req.append((r[0], "requires %s(%s)" % (r[0], r[1]), pl.in_slices[r[1]]))
        self.items = []
        # Output limbs whose value a `represents` entry pins on every line (neg_2 and abs_2
        # carry one next to normalized and error): the suspicious heuristic of those kinds is
        # then not needed for them.
        self.pinned = set()
        for e, c in zip(k.ensures, pl.entries):
            # The entries of the interval kernels (outward, set_bound, ...) judge their outputs
            # on every line too.
            if e.kind == "represents" or getattr(e, "iv", False):
                for lo, hi in c["ranges"]:
                    self.pinned.update(range(lo, hi))
        # Statistics entries after those of the kernel's own ensures: one per entry of the core
        # of each `extends` entry (F2 applies them), labelled as such.
        self.extra = []
        n = len(k.ensures)
        for e, c in zip(k.ensures, pl.entries):
            it = {}
            if e.finite_when is not None:
                it["conds"] = [self._condition(tree, ex) for tree, _t, ex in e.finite_when]
            if e.kind == "extends":
                cp = plan_class(e.core, fmt, True)
                it["core"] = cp
                it["core_name"] = e.core.name
                it["offset"] = n + len(self.extra)
                for ce, cc in zip(e.core.ensures, cp.entries):
                    self.extra.append(("F2, core %s: %s" % (e.core.name, ce.label), ce.kind,
                                       cc.get("source")))
                ops = [nm for nm in k.input_names if nm not in k.masks]
                it["lead"] = e.lead
                it["lead_at"] = [pl.in_slices[nm][0] for nm in ops]
            elif e.kind == "encloses":
                inball = {nm for b in e.balls.values() for nm in b}
                it["scalars"] = [i for nm in sorted(set(EX.names(e.set_tree)))
                                 if nm not in e.balls and nm not in inball
                                 for i in range(*pl.in_slices[nm])]
            elif e.kind == "predicate":
                it["args"] = e.args
            elif e.kind == "makes_ball" and not getattr(e, "iv", False):
                it["from_center"] = pl.in_slices[e.from_center]
                it["from_radius"] = pl.in_slices[e.from_radius][0]
            elif e.kind == "neighbor":
                it["at"] = pl.in_slices[e.operand][0]
            self.items.append(it)

    def _condition(self, tree, e):
        """A function of the input limbs (all finite): |EXPR| <= 2^(qmax + p + e)."""
        src, s = EX.compile_tree(tree, self.pl._leaf)
        fn = EX.make_function(["x"], src)
        k = self.T + e - s
        if k >= 0:
            lim = 1 << k
            return lambda x: abs(fn(x)) <= lim
        return lambda x: (abs(fn(x)) << -k) <= 1

    def leaf(self, x):
        q = self.pl.fmt.qmin
        sl = self.pl.in_slices

        def f(name):
            lo, hi = sl[name]
            return group_value(x[lo:hi]), q
        return f

    def value(self, x, fin, tree=None):
        """(value, scale) of the kernel's value (or of another expression over the inputs)."""
        pl = self.pl
        if tree is None:
            if pl.kernel.value_tree is None:
                return None
            if fin:
                return pl.value_fn(x), pl.sv
            tree = pl.kernel.value_tree
        return ext_eval(tree, self.leaf(x))

    def violated(self, x):
        """The first requirement the operands violate, or None."""
        fmt = self.pl.fmt
        for r in self.req:
            kind = r[0]
            if kind == "ball":
                (lo, hi), ri = r[2], r[3]
                if ball_state(fmt, x[lo:hi], x[ri]) is None:
                    return r[1]
                continue
            if kind in ("interval", "not_nan"):
                # The requirements of the interval kernels (intervals.py).
                from . import intervals as IV
                why = IV.requirement_violated(self, x, r)
                if why:
                    return why
                continue
            lo, hi = r[2]
            g = x[lo:hi]
            if kind == "canonical":
                ok = canonical(fmt, g)
            elif kind == "nonneg":
                # In this domain nonneg admits +inf and NaN.
                v = group_value(g)
                ok = v in (INF, NAN) or (type(v) is int and v >= 0)
            else:                      # power_of_two: a finite power of two, as before
                v = group_value(g)
                ok = type(v) is int and v > 0 and v & (v - 1) == 0
            if not ok:
                return r[1]
        return None

    def small(self, x, V=None, ends=()):
        """Every input limb, every input value, the exact value and the given ends of a set are
        below Omega/4 in magnitude (the test of the finite layer's suspicious cases)."""
        pl = self.pl
        fmt = pl.fmt
        q4 = fmt.omega
        for i in self.limb_slots:
            if type(x[i]) is not int or 4 * abs(x[i]) >= q4:
                return False
        if any(4 * abs(sum(x[lo:hi])) >= q4 for lo, hi in pl.groups):
            return False
        if V is not None:
            v, s = V
            if type(v) is not int:
                return False
            d = s - fmt.qmin
            if (((4 * abs(v)) << d) if d >= 0 else 4 * abs(v)) >= (q4 if d >= 0 else q4 << -d):
                return False
        for v, sh in ends:
            if 4 * abs(v) >= (q4 << sh):
                return False
        return True

    def ratio_value(self, V):
        """|value| / 2^(qmax + p) as a fraction."""
        v, s = V
        k = s - self.T
        return (abs(v) << k, 1) if k >= 0 else (abs(v), 1 << -k)

    def ratio_lead(self, x, slots=None):
        """max |leading limb of an input| / 2^(qmax + p) as a fraction."""
        m = max((abs(x[i]) for i in (self.heads if slots is None else slots)), default=0)
        return m, self.T_fixed


# ---------------------------------------------------------------------------
# One completed line

def judge_line(ck, st, pl, line, ins, outs):
    """The extended domain's verdict on one completed line whose header, limb counts and scope
    the checker has already read.  Requirements first: a line whose operands violate them is
    invalid, never passed."""
    fmt = pl.fmt
    ep = pl.ext
    for i in pl.in_masks:
        if ins[i] not in MASK_TEXT:
            ck._invalid(st, line, "mask input %r is not 0 or 1" % ins[i])
            return
    try:
        x = [MASK_TEXT[t] if i in pl.in_masks else F.parse_limb(fmt, t) for i, t in enumerate(ins)]
    except F.LimbError as ex:
        ck._invalid(st, line, "input limb malformed: %s" % ex)
        return
    for i in ep.limb_slots:
        v = x[i]
        if v == F.OUTSIDE or (type(v) is int and not F.is_member(fmt, v)):
            ck._invalid(st, line, "input limb not a number of the format")
            return
    why = ep.violated(x)
    if why:
        ck._invalid(st, line, why)
        return
    for i in pl.out_masks:
        if outs[i] not in MASK_TEXT:
            ck._fail(st, line, "mask output %r is not 0 or 1" % outs[i])
            return
    try:
        z = [MASK_TEXT[t] if i in pl.out_masks else F.parse_limb(fmt, t)
             for i, t in enumerate(outs)]
    except F.LimbError as ex:
        ck._fail(st, line, "output limb malformed: %s" % ex)
        return
    for i, v in enumerate(z):
        if i not in pl.out_masks and (v == F.OUTSIDE or (type(v) is int and not F.is_member(fmt, v))):
            ck._fail(st, line, "output limb not a number of the format")
            return
    st.c["judged"] += 1
    fin = all(type(x[i]) is int for i in ep.limb_slots)
    V = ep.value(x, fin)
    reasons, sus = [], []
    for i, c in enumerate(pl.entries):
        es = st.entries[i]
        before = es.failures
        out = KINDS[c["kind"]](ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus)
        if out:
            # The finite judge counts the failures of the entries it applies itself.
            if es.failures == before:
                es.failures += 1
            reasons.extend(out)
    if sus:
        st.c["suspicious"] += 1
        st.example("suspicious", line, "; ".join(sus), ck.max_examples)
    if reasons:
        st.c["failed"] += 1
        for r in reasons:
            st.reason(r)
        st.example("failure", line, "; ".join(reasons), ck.max_examples)
    else:
        st.c["passed"] += 1


def _failer(es, out):
    """fail(statement, why): the reason, and the statement counted once per line."""
    seen = set()

    def fail(stmt, why):
        if stmt not in seen:
            seen.add(stmt)
            es.count("failed " + stmt)
        out.append("%s: %s" % (stmt, why))
    return fail


def k_extends(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """F1 to F5 of milestone1.md, each counted under its name when it fails."""
    it = ep.items[i]
    fmt = pl.fmt
    w = _gather(z, c["ranges"])
    es.applicable += 1
    out = []
    fail = _failer(es, out)
    if not canonical(fmt, w):
        fail("F1", "the output is not canonical")
    conds_hold = fin and bool(it["conds"]) and all(f(x) for f in it["conds"])
    if conds_hold:
        es.count("F3 applies: finite operands, every finite_when condition holds")
    w0 = w[0]
    if fin:
        if type(w0) is int:
            es.count("class F2: finite operands, finite result")
            if all(type(v) is int for v in z):
                cp = it["core"]
                off = it["offset"]
                for r in ck._judge(cp, st.entries[off:off + len(cp.entries)], x, z,
                                   cp.value_fn(x), {}, line):
                    fail("F2", "core %s: %s" % (it["core_name"], r))
            else:
                fail("F2", "a lower limb of a finite result is not finite")
            es.track_max("finite result on finite operands: max |leading limb| / 2^(qmax+p)",
                         ep.ratio_lead(x), line)
            es.track_max("finite result on finite operands: |value| / 2^(qmax+p)",
                         ep.ratio_value(V), line)
            return out
        es.count("class F4: finite operands, non-finite result")
        if conds_hold:
            fail("F3", "the result is not finite although every finite_when condition holds")
        v = V[0]
        if v == 0:
            fail("F4", "the result is not finite although the exact value is zero")
        else:
            want = INF if v > 0 else NINF
            if w0 != want or any(t != 0 for t in w[1:]):
                fail("F4", "the result is not (%s, 0), the infinity of the exact value's sign" % want)
        es.track_min("overflow on finite operands: max |leading limb| / 2^(qmax+p)",
                     ep.ratio_lead(x), line)
        es.track_min("overflow on finite operands: |value| / 2^(qmax+p)", ep.ratio_value(V), line)
        if ep.small(x, V):
            sus.append("F4: a non-finite result with operands and exact value below Omega/4")
        return out
    es.count("class F5: a non-finite operand")
    a, b = (x[j] for j in it["lead_at"])
    t = ieee_op(fmt, it["lead"], a, b)
    if type(w0) is int:
        fail("F2", "a finite result although an operand is not finite")
    if type(t) is int:
        want = [t] + [0] * (len(w) - 1)
    else:
        want = [t] * len(w) if t == NAN else [t] + [0] * (len(w) - 1)
    if w != want:
        fail("F5", "the result is not the canonical form of %s(%s, %s) = %s" % (
            it["lead"], F.fixed_hex(fmt, a), F.fixed_hex(fmt, b), F.fixed_hex(fmt, t)))
    return out


def k_encloses(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """B1 to B4 of milestone1.md with the set semantics of the page: a NaN radius is the empty
    set, radius +inf the whole line, and a scalar that is not finite gives the whole line unless
    a ball operand is empty."""
    it = ep.items[i]
    fmt = pl.fmt
    clo, chi = c["center"]
    so = ball_state(fmt, z[clo:chi], z[c["radius"]])
    states = [ball_state(fmt, x[lo:hi], x[ri]) for (lo, hi), ri in c["balls"]]
    empty_in = "empty" in states
    fin_ops = all(s == "finite" for s in states) and all(type(x[j]) is int for j in it["scalars"])
    out = []
    fail = _failer(es, out)
    if so is None:
        es.applicable += 1
        fail("B1", "the result is not a canonical ball")
        return out
    es.count("result: %s" % STATE_TEXT[so])
    if (so == "empty") != empty_in:
        fail("B2", "the empty set although no operand is empty" if so == "empty" else
             "an operand is empty but the result is the %s" % STATE_TEXT[so])
    if so == "finite":
        if not fin_ops:
            es.applicable += 1
            fail("B3", "a finite ball although an operand is not a finite ball or a scalar is "
                       "not finite")
        else:
            es.applicable += 1
            r = ck._containment(pl, c, es, x, z, line)
            if r:
                fail("B3", r)
            # exact_when (Milestone 2): with a finite ball from finite operands, the ball is
            # exactly the set when every condition holds; a statement of its own, between B3
            # and B4.
            r = ck._exactness(pl, c, es, x, z, line)
            if r:
                fail("exact_when", r)
            es.track_max("finite result on finite operands: max |leading limb| / 2^(qmax+p)",
                         ep.ratio_lead(x), line)
    else:
        es.applicable += 1
    if it["conds"] and fin_ops and all(f(x) for f in it["conds"]):
        es.count("B4 applies: finite operands, every finite_when condition holds")
        if so != "finite":
            fail("B4", "the %s although every finite_when condition holds" % STATE_TEXT[so])
    if fin_ops and so == "whole":
        es.count("whole line on finite operands")
        sh = c["sh_q"]
        lo, hi = pl.set_range(c, x)
        es.track_min("whole line on finite operands: max |leading limb| / 2^(qmax+p)",
                     ep.ratio_lead(x), line)
        es.track_min("whole line on finite operands: max |end of the set| / 2^(qmax+p)",
                     (max(abs(lo), abs(hi)), ep.T_fixed << sh), line)
        if V is not None:
            es.track_min("whole line on finite operands: |value| / 2^(qmax+p)",
                         ep.ratio_value(V), line)
        # Not shown as suspicious, unlike a non-finite result of the other kinds: the radius
        # computation steps up at every operation and reaches +inf far below Omega on small
        # formats (at p = 2, a set within +-1.25 with Omega = 6), and with no finite_when
        # condition nothing is claimed.
    return out


def k_represents(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """The output is canonical and is value exactly."""
    fmt = pl.fmt
    w = _gather(z, c["ranges"])
    es.applicable += 1
    v, s = V
    if not canonical(fmt, w):
        es.count("failed: not canonical")
        return ["represents: the output is not canonical"]
    if v == NAN:
        es.count("value NaN")
        ok = all(t == NAN for t in w)
    elif type(v) is not int:
        es.count("value infinite")
        ok = w[0] == v and all(t == 0 for t in w[1:])
    else:
        es.count("value finite")
        ok = all(type(t) is int for t in w) and x_cmp(sum(w), fmt.qmin, v, s) == 0
    if not ok:
        es.count("failed: not the value")
        return ["represents: the output is not the value %s exactly" % (
            v if type(v) is not int else "of the operands")]
    return []


def radius_class(r, token):
    """The class of a radius given to a constructor (MAKE_RADIUS_CLASSES); token is its text, for
    the sign of a zero."""
    if r == NAN:
        return "NaN"
    if r == NINF:
        return "-inf"
    if r == INF:
        return "+inf"
    if r == 0:
        return "-0" if token.startswith("-") else "+0"
    return "negative" if r < 0 else "positive"


# The classes of the given radius and center of makes_ball from a center and a radius, counted as
# "given radius R, center C" (the guards ask for each).
MAKE_RADIUS_CLASSES = ("negative", "-inf", "NaN", "+inf", "+0", "-0", "positive")
MAKE_CENTER_CLASSES = ("finite", "not finite")


def k_makes_ball(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """Empty when the given radius is negative, -inf included, whatever the center; otherwise the
    whole line when the radius is a NaN or +inf or the given center is not finite; otherwise the
    given center and radius (a radius -0 is 0). A NaN radius gave the empty set until the
    owner's decision of 2026-11-20 (architecture.md, makes_ball)."""
    it = ep.items[i]
    fmt = pl.fmt
    lo, hi = it["from_center"]
    cin, r = x[lo:hi], x[it["from_radius"]]
    (clo, chi), (ri, _) = c["ranges"]
    cw, rw = z[clo:chi], z[ri]
    es.applicable += 1
    finite_center = all(type(t) is int for t in cin)
    if r == NINF or (type(r) is int and r < 0):
        want = "empty"
    elif r == NAN or r == INF or not finite_center:
        want = "whole"
    else:
        want = "finite"
    es.count("given: %s" % STATE_TEXT[want])
    toks = [t for t in line.partition(" -> ")[0].split(" ")[2:] if not t.startswith("#")]
    token = toks[it["from_radius"]] if it["from_radius"] < len(toks) else ""
    es.count("given radius %s, center %s" % (radius_class(r, token),
                                             MAKE_CENTER_CLASSES[0 if finite_center else 1]))
    so = ball_state(fmt, cw, rw)
    if so is None:
        es.count("failed: not canonical")
        return ["makes_ball: the result is not a canonical ball"]
    if so != want:
        es.count("failed: %s instead of %s" % (STATE_TEXT[so], STATE_TEXT[want]))
        return ["makes_ball: the %s instead of the %s" % (STATE_TEXT[so], STATE_TEXT[want])]
    if want == "finite" and (sum(cw) != sum(cin) or rw != r):
        es.count("failed: not the given ball")
        return ["makes_ball: not the given center and radius"]
    return []


def k_finite_kind(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """normalized, error, leading_rounded: as before when every operand and the output are
    finite; the output is canonical in every case."""
    fmt = pl.fmt
    w = _gather(z, c["ranges"])
    out = []
    if not canonical(fmt, w):
        es.count("failed: not canonical")
        out.append("%s: the output is not canonical" % c["kind"])
    if fin and all(type(t) is int for t in w):
        out.extend(ck._judge(pl, st.entries, x, z, V[0] if V else None, {}, line, only=(i,)))
        return out
    es.applicable += 1
    # Where a `represents` entry pins these outputs, it judges what is shown here otherwise.
    pinned = all(i in ep.pinned for lo, hi in c["ranges"] for i in range(lo, hi))
    if fin:
        es.count("non-finite result on finite operands")
        if not pinned and ep.small(x, V):
            sus.append("%s: a non-finite result with operands and exact value below Omega/4"
                       % c["kind"])
    else:
        es.count("a non-finite operand")
        # Outside the claim, which says only "canonical"; but a result whose value is not the
        # value of the kernel in the extended reals is shown, as the finite layer shows a
        # non-finite result on small operands.
        if not pinned and V is not None and group_value(w) != V[0]:
            sus.append("%s: a non-finite operand and a result whose value is not %s"
                       % (c["kind"], V[0]))
    return out


def k_predicate(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    if fin:
        r = ck._predicate(pl, c, es, x, z, V, None, line)
        return [r] if r else []
    es.applicable += 1
    a, b = (ep.value(x, False, t) for t in ep.items[i]["args"])
    d = x_cmp(a[0], a[1], b[0], b[1])
    rel = c["rel"]
    truth = d is not None and (d < 0 if rel == "lt" else d <= 0 if rel == "le" else d == 0)
    es.count("true" if truth else "false")
    es.count("a non-finite operand, %s" % ("true" if truth else "false"))
    if z[c["first"]] != (1 if truth else 0):
        return ["mask is not the truth of %s in the extended reals" % rel]
    return []


def _operand_classes(pl, x, es, v):
    """The classes of the operands of a value of two operands (NAME op NAME) when one is not
    finite: a NaN operand, or an infinite one and no NaN; and a NaN value from operands that are
    not NaN (inf - inf, 0 * inf)."""
    ops = [group_value(x[lo:hi]) for lo, hi in pl.two]
    if NAN in ops:
        es.count(D.NAN_OPERAND)
    else:
        es.count(D.INF_OPERAND)
        if v == NAN:
            es.count(D.NAN_FROM_INF)


def k_rounded(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """For a finite operand, the rounding of value in the format with overflow (beyond Omega in
    the direction of rounding is the infinity); a non-finite operand gives itself, which for a
    value of two operands is the value IEEE 754 gives the operation (a NaN for a NaN operand,
    inf - inf and 0 * inf).  With `when` (Milestone 2), nothing is claimed on finite operands
    where the condition does not hold."""
    fmt = pl.fmt
    o = z[c["first"]]
    v, s = V
    two = pl.two is not None
    if type(v) is int:
        if c.get("when") == "product_large" and fin:
            # V is (value_fn(x), sv) on finite operands, at the scale of pl_thr.
            if not (v == 0 or abs(v) >= pl.pl_thr):
                es.count(D.WHEN_FAILS)
                return []
        mode = c["mode"]
        om = fmt.omega
        if mode == "nearest":
            r = F.rn(fmt, v, s)
        elif mode == "down":
            r = F.rdir(fmt, v, s, False)
            r = NINF if r < -om else om if r > om else r
        else:
            r = F.rdir(fmt, v, s, True)
            r = INF if r > om else -om if r < -om else r
        if two and fin:
            ov = D.overflow_class(fmt, v, s)
            if ov:
                es.count(ov)
        if fin and type(r) is int:
            why = ck._rounded(pl, c, es, x, z, v, r, line)
            return [why] if why else []
        if c.get("when") == "product_large" and fin:
            es.count(D.WHEN_HOLDS)
    else:
        r = v
    es.applicable += 1
    es.count("a non-finite operand" if not fin else "rounds to %s" % r)
    if two and not fin:
        _operand_classes(pl, x, es, v)
    if o != r:
        return ["output is not the value rounded %s (%s)" % (c["mode"], F.fixed_hex(fmt, r))]
    return []


def k_neighbor(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """The next number of the format above (up) or below the operand, on every value of the
    format: the table of architecture.md, "Claims of Milestone 2"."""
    fmt = pl.fmt
    a = x[ep.items[i]["at"]]
    up = c["side"] == "up"
    r = D.neighbor(fmt, a, up)
    es.applicable += 1
    es.count(D.neighbor_row(fmt, a))
    for cl in D.neighbor_steps(fmt, a, r, up):
        es.count(cl)
    if z[c["first"]] != r:
        return ["neighbor: the output is not the next number of the format %s the operand (%s)"
                % ("above" if up else "below", F.fixed_hex(fmt, r))]
    return []


def k_bound(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """below: on finite operands, value rounded down in the format with overflow and stepped down
    `steps` times <= output <= value (above, symmetrically); the output may be an infinity.  With
    an infinite or NaN operand the output is the value as IEEE 754 defines it."""
    fmt = pl.fmt
    o = z[c["first"]]
    v, s = V
    es.applicable += 1
    below = c["side"] == "below"
    if not fin or type(v) is not int:
        es.count("a non-finite operand")
        if pl.two is not None:
            _operand_classes(pl, x, es, v)
        if o != v:
            return ["bound: the output is not %s, the value of IEEE 754 on the operands" % v]
        return []
    ov = D.overflow_class(fmt, v, s)
    if ov:
        es.count(ov)
    d = D.round_overflow(fmt, v, s, "down" if below else "up")
    exact = type(d) is int and x_cmp(d, fmt.qmin, v, s) == 0
    es.count(D.BOUND_EXACT if exact else D.BOUND_INEXACT)
    if o == NAN:
        return ["bound: a NaN output on finite operands"]
    side = x_cmp(o, fmt.qmin, v, s)
    if (side > 0) if below else (side < 0):
        return ["bound: the output is %s the value" % ("above" if below else "below")]
    k, t = 0, d
    while t != o:
        if k == c["steps"]:
            return ["bound: the output is more than %d steps beyond the value rounded %s (%s)" % (
                c["steps"], "down" if below else "up", F.fixed_hex(fmt, d))]
        t = D.neighbor(fmt, t, not below)
        k += 1
    es.count(D.steps_text(k))
    return []


def k_upper(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """A NaN exactly when an operand is a NaN or the operation is 0 * inf; otherwise not below
    value, and within gaps when the output is finite."""
    o = z[c["first"]]
    v, s = V
    if v == NAN:
        es.applicable += 1
        es.count("value NaN (a NaN operand, or 0 * inf)")
        return [] if o == NAN else ["upper: the output is not a NaN although the value is"]
    if o == NAN:
        es.applicable += 1
        return ["upper: a NaN output although the value is not a NaN"]
    if type(o) is not int:
        es.applicable += 1
        if o == INF:
            es.count("output +inf on %s" % ("finite operands" if fin else "a non-finite operand"))
            if fin and ep.small(x, V):
                sus.append("upper: +inf with operands and exact value below Omega/4")
            return []
        return [] if v == NINF else ["upper: output -inf below the value"]
    if type(v) is not int:
        es.applicable += 1
        return ["upper: a finite output although the value is %s" % v]
    if fin:
        why = ck._upper(pl, c, es, x, z, v, None, line)
        return [why] if why else []
    es.applicable += 1
    return [] if x_cmp(o, pl.fmt.qmin, v, s) >= 0 else ["upper: output below the value"]


def same_limb(a, b):
    """Two limbs are the same value: equal numbers (a zero of either sign), the same infinity, or
    two NaNs (a NaN is any NaN)."""
    return a == b


def k_finite_or_nan(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """architecture.md, "Claims of Milestone 2": the flag is true exactly when limb 0 of value (an
    input, the state of a fold) is finite, and the output is then value, limb for limb; otherwise
    every limb of the output is a NaN.  The input is any limbs: a finite leading limb with a lower
    limb that is not finite is passed on as it is."""
    lo, hi = c["operand"]
    s = x[lo:hi]
    w = _gather(z, c["ranges"])
    f = z[c["flag"]]
    es.applicable += 1
    if "steps" in c:
        return _finite_or_nan_if(pl, c, es, x, s, w, f)
    lead = type(s[0]) is int
    if lead:
        es.count("value: finite leading limb, every limb finite" if all(type(v) is int for v in s)
                 else "value: finite leading limb, a lower limb not finite")
    else:
        es.count("value: leading limb NaN" if s[0] == NAN else "value: leading limb infinite")
    out = []
    if f != (1 if lead else 0):
        out.append("finite_or_nan: the flag is %d although limb 0 of the value is %s" % (
            f, "finite" if lead else s[0]))
    if lead:
        if len(w) != len(s) or not all(same_limb(a, b) for a, b in zip(w, s)):
            out.append("finite_or_nan: the output is not the value, limb for limb")
    elif not all(v == NAN for v in w):
        out.append("finite_or_nan: limb 0 of the value is not finite, and a limb of the output is "
                   "not a NaN")
    return out


def next_up(fmt, v):
    """IEEE 754's nextUp of a limb: a NaN stays a NaN, +inf stays +inf, -inf goes to -Omega,
    Omega to +inf, and a finite number to the next number of the format above it."""
    if v == NAN or v == INF:
        return v
    if v == NINF:
        return -fmt.omega
    return F.succ(fmt, v)


def _finite_or_nan_if(pl, c, es, x, s, w, f):
    """finite_or_nan with `if` (a mask input) and `steps` (the finishes of the folds of maxima):
    with t the value stepped up S times, the flag is true exactly when the mask is true and t is
    finite, and the output is then t; otherwise every limb of the output is a NaN."""
    fmt = pl.fmt
    t = s[0]
    for _ in range(c["steps"]):
        t = next_up(fmt, t)
    on = c["cond_in"] is None or x[c["cond_in"]] == 1
    es.count("mask true" if on else "mask false")
    if type(s[0]) is int:
        es.count("value finite, stepped up finite" if type(t) is int
                 else "value finite, stepped up +inf")
    else:
        es.count("value: NaN" if s[0] == NAN else "value: infinite")
    want = on and type(t) is int
    out = []
    if f != (1 if want else 0):
        out.append("finite_or_nan: the flag is %d although the mask is %s and the value stepped up "
                   "%d times is %s" % (f, "true" if on else "false", c["steps"],
                                       F.fixed_hex(fmt, t)))
    if want:
        if len(w) != 1 or not same_limb(w[0], t):
            out.append("finite_or_nan: the output is not the value stepped up %d times"
                       % c["steps"])
    elif not all(v == NAN for v in w):
        out.append("finite_or_nan: the flag is false, and a limb of the output is not a NaN")
    return out


KINDS = {"extends": k_extends, "encloses": k_encloses, "represents": k_represents,
         "makes_ball": k_makes_ball, "normalized": k_finite_kind, "error": k_finite_kind,
         "leading_rounded": k_finite_kind, "predicate": k_predicate, "rounded": k_rounded,
         "upper": k_upper, "neighbor": k_neighbor, "bound": k_bound,
         "finite_or_nan": k_finite_or_nan}
# intervals.py adds the kinds of the interval kernels in the extended domain to KINDS when it is
# imported (claims.py imports it).
