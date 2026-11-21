"""The non-finite layer judged on the operands of small formats, non-finite operands included.

A reading of docs/developer/design/milestone1.md written for this test: "IEEE-like results" (the
canonical values, statements F1 to F5 of the full kernels, the kernels that need no fix-up), "Values
that enter from the program" (the constructors) and "Ball kernels" (the special states of a ball,
statements B1 to B4), with the meanings of architecture.md, "Claims of the non-finite layer". The
interpreter is the runner; the judge shares with it only the expression parser, and, for the
claims of a core that F2 refers to, the real-model judge of test_statements.py.

The formats have the shape of Flocq's IEEE formats, q_min + q_max = 3 - 2p, as milestone1.md asks
of the toy formats that test IEEE-model statements. Every case with a non-finite operand is
judged against a sample of the other operand (every one when they are few), and finite operands
exhaustively when they are few, otherwise on a sample of which half has leading limbs in the top
two binades, where overflow happens.

What fails is not hidden by changing a statement: KNOWN pins the (kernel, statement) pairs that
fail, with their first cases, so that a change shows (see the report printed by the test).
"""
import itertools
import random
import sys
import unittest
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F

import common
import test_statements as ts
from kairn_gen import expr, interp, ir

# (p, qmin, qmax) with qmin + qmax = 3 - 2p: largest numbers 6, 14, 15, 31 (and 63).
FORMATS = [(2, -2, 1), (3, -4, 1), (4, -5, 0), (5, -7, 0)] + ([(6, -9, 0)] if common.FULL else [])
LIMIT = common.size(12000, 250000)        # finite cases per kernel and format, at most
PARTNERS = common.size(400, 6000)         # finite partners of each non-finite operand, at most

NUM, INF, NAN = interp.NUM, interp.INF, interp.NAN
NaN = interp.NaN
ZERO, NZERO = interp.canon(False, 0, 0), interp.canon(True, 0, 0)
PINF, NINF = (INF, False), (INF, True)


def finite(v):
    return v[0] == NUM


def fr(v):
    """A finite interpreter value as a Fraction."""
    return (-1 if v[1] else 1) * F(v[2]) * F(2) ** v[3]


def make(x, neg=None):
    """A Fraction as an interpreter value; a zero gets the sign `neg`."""
    if x == 0:
        return NZERO if neg else ZERO
    n = x < 0
    x = abs(x)
    return interp.canon(n, x.numerator, 0) if x.denominator == 1 else \
        interp.canon(n, x.numerator, -(x.denominator.bit_length() - 1))


def show(v):
    return interp.format_limb(v)


class Fmt(ts.Format):
    """A toy format, with its finite values (both zeros) as interpreter values."""

    def __init__(self, p, qmin, qmax):
        super().__init__(p, qmin, qmax)
        self.f = interp.Format(self.name, p, qmin, qmax)
        self.values = [make(x, neg) for x in self.line for neg in ((False, True) if x == 0 else (None,))]
        self.threshold = F(2) ** (qmax + p)

    def ieee_round(self, x, mode):
        """x rounded in the format with overflow: a result beyond the largest number is the
        infinity of that sign (architecture.md, "Number formats"), except toward zero: rounded down,
        a value above the largest number is that number, and rounded up, a value below the most
        negative one is that one (milestone2.md, "Notation and vocabulary")."""
        if mode == 'down' and x > self.top:
            return make(self.top)
        if mode == 'up' and x < -self.top:
            return make(-self.top)
        r = self.round(x, mode)
        if abs(r) > self.top:
            return PINF if r > 0 else NINF
        return make(r, neg=x < 0)

    def normalized(self, limbs):
        """Finite limbs of the format, each the rounding of itself plus the next."""
        if not all(finite(v) for v in limbs):
            return False
        xs = [fr(v) for v in limbs]
        return all(x in self.members for x in xs) and \
            all(xs[i] == self.round(xs[i] + xs[i + 1], 'nearest') for i in range(len(xs) - 1))

    def canonical(self, limbs):
        """milestone1.md: finite and normalized, or (inf, 0) of either sign with a zero of either
        sign after it, or every limb a NaN. A one-limb value is any value."""
        if len(limbs) == 1:
            return True
        if all(v[0] == NAN for v in limbs):
            return True
        if limbs[0][0] == INF:
            return all(finite(v) and v[2] == 0 for v in limbs[1:])
        return self.normalized(limbs)

    def pairs(self):
        """Every normalized pair, zeros of both signs: x1 within half a gap of x0 (the ranges
        of test_statements.Space), kept when x0 is the rounding of the sum."""
        if not hasattr(self, '_pairs'):
            space = ts.Space(self, ir.Group('x', ('x0', 'x1')), {'normalized'})
            self._pairs = [(make(x0, n0), make(x1, n1)) for x0, lo, hi in space.ranges
                           for x1 in self.line[lo:hi] for n0 in ((False, True) if x0 == 0 else (None,))
                           for n1 in ((False, True) if x1 == 0 else (None,))
                           if self.round(x0 + x1, 'nearest') == x0]
        return self._pairs


# ---------------------------------------------------------------------------------------------
# Operands: each a tuple of limbs (a ball is its center limbs then its radius), finite or special.

def powers_of_two(fmt):
    return [v for v in fmt.values if finite(v) and not v[1] and v[2] == 1]


class Operand:
    """The values of one operand of a kernel: `finite` ones and `special` (non-finite) ones, and
    the input groups it fills."""

    def __init__(self, groups, finite_values, special):
        self.groups, self.finite, self.special = groups, finite_values, special

    def top(self, fmt):
        """The finite values whose leading limb is in the top two binades (a mask: both values)."""
        return [v for v in self.finite if not isinstance(v[0], bool) and finite(v[0]) and
                abs(fr(v[0])) >= fmt.top / 4] or self.finite


def bound_values(fmt, n):
    """The values of a bound of n limbs, finite then infinite: every value of the format (both
    zeros) or every normalized pair, and the infinities ((+-inf, 0) for two limbs)."""
    if n == 1:
        return [(v,) for v in fmt.values], [(PINF,), (NINF,)]
    return list(fmt.pairs()), [(PINF, ZERO), (NINF, ZERO)]


def bound_value(limbs):
    """The value of a bound: a Fraction, PINF or NINF."""
    return limbs[0] if limbs[0][0] == INF else sum(fr(v) for v in limbs)


def interval_operand(fmt, groups, seed):
    """The intervals of one operand (milestone2.md, "Values of an interval"): bounded nonempty
    intervals (every one when they are few, otherwise a sample), and, as the special values, the
    empty set and a sample of the unbounded intervals, the whole line among them."""
    n = len(groups[0].limbs)
    fin, inf = bound_values(fmt, n)
    rng = random.Random(f'{seed}:{fmt.name}:{groups[0].name}:interval')
    key = [bound_value(b) for b in fin]
    if len(fin) ** 2 <= 2 * LIMIT:
        bounded = [a + b for i, a in enumerate(fin) for j, b in enumerate(fin) if key[i] <= key[j]]
    else:
        bounded = []
        while len(bounded) < LIMIT:
            i, j = rng.randrange(len(fin)), rng.randrange(len(fin))
            bounded.append(fin[i] + fin[j] if key[i] <= key[j] else fin[j] + fin[i])
    # Unbounded: (-inf, h) and (l, +inf) for a spread of finite bounds, and the whole line.
    spread = sorted(fin, key=bound_value)
    picks = [spread[i * (len(spread) - 1) // 10] for i in range(11)]
    picks += [b for b in fin if bound_value(b) == 0][:2]
    special = [inf[0] + inf[1]] + [inf[1] + h for h in picks] + [l + inf[0] for l in picks] + [inf[1] + inf[0]]
    return bounded, special


def operands(k, fmt):
    req = {}
    for r in k.requires:
        req.setdefault(r[1], []).append(r)
    radii = {r[2]: r[1] for r in k.requires if r[0] == 'ball'}
    uppers = {r[2]: r[1] for r in k.requires if r[0] == 'interval'}
    groups = {g.name: g for g in k.inputs}
    out = []
    nonneg_finite = [v for v in fmt.values if not v[1] or v[2] == 0]
    for g in k.inputs:
        if g.name in radii or g.name in uppers:
            continue
        kinds = {r[0] for r in req.get(g.name, [])}
        if g.kind == ir.MASK:              # the mask of the state of a fold of maxima: both values
            out.append(Operand([g], [(True,), (False,)], []))
            continue
        if 'interval' in kinds:
            upper = groups[[r[2] for r in req[g.name] if r[0] == 'interval'][0]]
            bounded, special = interval_operand(fmt, [g, upper], k.name)
            out.append(Operand([g, upper], bounded, special))
            continue
        if 'not_nan' in kinds and len(g.limbs) == 2:      # canonical and not NaN (stage B1, mul_ext_2_2)
            out.append(Operand([g], fmt.pairs(), [(PINF, ZERO), (PINF, NZERO), (NINF, ZERO), (NINF, NZERO)]))
            continue
        if 'not_nan' in kinds:
            out.append(Operand([g], [(v,) for v in fmt.values], [(PINF,), (NINF,)]))
            continue
        if 'ball' in kinds:
            radius = [r[2] for r in req[g.name] if r[0] == 'ball'][0]
            centers = fmt.pairs() if len(g.limbs) == 2 else [(v,) for v in fmt.values]
            fin = [c + (r,) for c in centers for r in nonneg_finite]
            zeros = [(ZERO, ZERO), (NZERO, NZERO)] if len(g.limbs) == 2 else [(ZERO,), (NZERO,)]
            special = [z + (PINF,) for z in zeros] + [(NaN,) * (len(g.limbs) + 1)]
            out.append(Operand([g, groups[radius]], fin, special))
        elif len(g.limbs) == 2:
            special = [(PINF, ZERO), (PINF, NZERO), (NINF, ZERO), (NINF, NZERO), (NaN, NaN)]
            out.append(Operand([g], fmt.pairs(), special))
        elif 'power_of_two' in kinds:
            out.append(Operand([g], [(v,) for v in powers_of_two(fmt)], []))
        elif 'nonneg' in kinds:
            out.append(Operand([g], [(v,) for v in nonneg_finite], [(PINF,), (NaN,)]))
        else:
            out.append(Operand([g], [(v,) for v in fmt.values], [(PINF,), (NINF,), (NaN,)]))
    return out


def cases(k, fmt, seed):
    """Tuples of operand values (one entry per Operand), as described in the module's comment."""
    ops = operands(k, fmt)
    rng = random.Random(f'{seed}:{fmt.name}:{k.name}')
    out = []
    # Every combination with a non-finite operand, against a sample of the finite values of the
    # other operand when they are many.
    for i, op in enumerate(ops):
        for s in op.special:
            others = []
            for j, o in enumerate(ops):
                if j < i:
                    others.append(o.finite)                     # specials of earlier ones are done
                elif j > i:
                    others.append(o.finite + o.special)
            combos = list(itertools.product(*others)) if others else [()]
            if len(combos) > PARTNERS:
                combos = rng.sample(combos, PARTNERS)
            # And every combination with the later operands non-finite too, which a sample can miss:
            # the hull of two empty intervals is the empty set only there (stage B1).
            later = [o.special if j > i else o.finite[:1] for j, o in enumerate(ops) if j != i]
            seen_combos = set(combos)
            combos += [c for c in itertools.product(*later) if c not in seen_combos] if others else []
            for c in combos:
                out.append(c[:i] + (s,) + c[i:])
    # The finite cases.
    total = 1
    for op in ops:
        total *= len(op.finite)
    if total <= LIMIT:
        out += list(itertools.product(*(op.finite for op in ops)))
    else:
        tops = [op.top(fmt) for op in ops]
        for n in range(LIMIT):
            out.append(tuple(rng.choice(top if n % 2 else op.finite) for op, top in zip(ops, tops)))
    return ops, out


# ---------------------------------------------------------------------------------------------
# Values of operands and expressions, over the extended reals.

def group_value(limbs):
    """The value of a group of limbs: a Fraction, PINF, NINF or NaN. With a canonical operand a
    non-finite group is (inf, 0) or all NaN."""
    if any(v[0] == NAN for v in limbs):
        return NaN
    if any(v[0] == INF for v in limbs):
        signs = {v[1] for v in limbs if v[0] == INF}
        return NaN if len(signs) > 1 else (PINF if signs == {False} else NINF)
    return sum(fr(v) for v in limbs)


def ieee(op, a, b):
    """The operation of T on two values (Fractions or PINF, NINF, NaN), exactly where an operand is
    not finite: IEEE 754's rules for infinities and NaN. Finite results are returned exact."""
    if NaN in (a, b):
        return NaN
    if op == 'sub':
        b = b if b == NaN else (NINF if b == PINF else PINF if b == NINF else -b)
        op = 'add'
    if op == 'add':
        if a in (PINF, NINF) and b in (PINF, NINF):
            return a if a == b else NaN
        if a in (PINF, NINF):
            return a
        if b in (PINF, NINF):
            return b
        return a + b
    infs = [x for x in (a, b) if x in (PINF, NINF)]
    if infs:
        other = [x for x in (a, b) if x not in (PINF, NINF)]
        if other and other[0] == 0:
            return NaN              # 0 inf; a zero of either sign
        negative = sum(1 for x in (a, b) if x == NINF or (x not in (PINF, NINF) and x < 0)) % 2
        return NINF if negative else PINF
    return a * b


# ---------------------------------------------------------------------------------------------
# The judge. Each function returns the names of the statements that fail on one case.

def judge_extends(k, ks, fmt, e, ins, outs, values):
    """F1 to F5 of milestone1.md, "IEEE-like results"."""
    core = ks[e['core']]
    w = outs[e['of']]
    bad = []
    all_finite = all(finite(v) for g in k.inputs for v in ins[g.name])
    if not fmt.canonical(w):
        bad.append('F1')
    if finite(w[0]):
        if not all_finite:
            bad.append('F2 (operands)')
        else:
            exact = {g.name: sum(fr(v) for v in ins[g.name]) for g in k.inputs}
            mapped = {core.outputs[0].name: [fr(v) if finite(v) else None for v in w]}
            for c in core.ensures:
                if not ts.holds(c, core, fmt, exact, mapped):
                    bad.append(f'F2 ({c["kind"]})')
    if all_finite:
        exact = {g.name: sum(fr(v) for v in ins[g.name]) for g in k.inputs}
        value = expr.evaluate(expr.parse(k.value), exact)
        # F3 claims something only when a condition is proved: an empty finite_when means "none
        # yet" (milestone1.md), not "always finite".
        conditions = bool(e['finite_when']) and all(
            abs(expr.evaluate(expr.parse(c['abs_le']), exact)) <= fmt.threshold * F(2) ** c['exp']
            for c in e['finite_when'])
        if conditions and not finite(w[0]):
            bad.append('F3')
        if not finite(w[0]):
            want = [PINF if value > 0 else NINF, ZERO]
            if value == 0 or w[0] != want[0] or not (finite(w[1]) and w[1][2] == 0):
                bad.append('F4')
    else:
        leads = [group_value(ins[g.name][:1]) for g in k.inputs]
        t = ieee(e['lead'], *leads)
        if t == NaN:
            ok = all(v[0] == NAN for v in w)
        elif t in (PINF, NINF):
            ok = w[0] == t and finite(w[1]) and w[1][2] == 0
        else:
            ok = False                  # a non-finite operand with a finite t: not foreseen
        if not ok:
            bad.append('F5')
    return bad


def ball_state(fmt, center, radius):
    """'finite', 'line', 'empty' for a canonical ball, None otherwise (milestone1.md)."""
    limbs = list(center) + [radius]
    if all(v[0] == NAN for v in limbs):
        return 'empty'
    if radius == PINF and all(finite(v) and v[2] == 0 for v in center):
        return 'line'
    if finite(radius) and (not radius[1] or radius[2] == 0) and all(finite(v) for v in center):
        if len(center) == 1 or fmt.normalized(list(center)):
            return 'finite'
    return None


def judge_ball(k, ks, fmt, e, ins, outs, values):
    """B1 to B4 of milestone1.md, "Ball kernels", with containment (B3)."""
    bad = []
    state = ball_state(fmt, outs[e['center']], outs[e['radius']][0])
    balls = {b: ball_state(fmt, ins[cr['center']], ins[cr['radius']][0]) for b, cr in e['balls'].items()}
    taken = {x for cr in e['balls'].values() for x in (cr['center'], cr['radius'])}
    scalars = [ins[g.name] for g in k.inputs if g.name not in taken]
    if state is None:
        bad.append('B1')
    if (state == 'empty') != ('empty' in balls.values()):
        bad.append('B2')
    every_finite = all(s == 'finite' for s in balls.values()) and all(finite(v) for s in scalars for v in s)
    if state == 'finite':
        if not every_finite:
            bad.append('B3 (operands)')
        else:
            exact = {g.name: sum(fr(v) for v in ins[g.name]) for g in k.inputs}
            limbs = {expr.limb_key(g.name, i): fr(v) for g in k.inputs for i, v in enumerate(ins[g.name])}
            got = {e['center']: [fr(v) for v in outs[e['center']]], e['radius']: [fr(outs[e['radius']][0])]}
            containment = {x: y for x, y in e.items() if x != 'exact_when'}
            if not ts.holds(containment, k, fmt, exact, got):
                bad.append('B3 (containment)')
            elif 'exact_when' in e and not ts.holds(e, k, fmt, exact, got, limbs):
                bad.append('E (exact)')
    # B4 claims something only when the kernel has conditions (the eight full kernels; not
    # ball_neg_k): finite operands under every condition give a finite ball.
    if every_finite and state != 'finite' and e['finite_when']:
        exact = {g.name: sum(fr(v) for v in ins[g.name]) for g in k.inputs}
        if all(abs(expr.evaluate(expr.parse(c['abs_le']), exact)) <= fmt.threshold * F(2) ** c['exp']
               for c in e['finite_when']):
            bad.append('B4')
    return bad


def judge_represents(k, ks, fmt, e, ins, outs, values):
    """The output is canonical and is `value` exactly. `value` is an input (a constructor) or an
    expression over the inputs (neg_2: -x, abs_2: abs(x)), read over extended values."""
    out = outs[e['of']]
    vals = {g.name: group_value(ins[g.name]) for g in k.inputs if g.kind == ir.LIMB}
    value = extended(k.value, vals)
    if not fmt.canonical(out):
        return ['represents (canonical)']
    if value == NaN:
        ok = all(v[0] == NAN for v in out)
    elif value in (PINF, NINF):
        ok = out[0] == value and finite(out[1]) and out[1][2] == 0
    else:
        ok = all(finite(v) for v in out) and sum(fr(v) for v in out) == value
    return [] if ok else ['represents']


# ---------------------------------------------------------------------------------------------
# Intervals (Milestone 2): milestone2.md, "Interval kernels", with the meanings of architecture.md,
# "Claims of Milestone 2". Extended values are Fractions, PINF and NINF.

def xle(a, b):
    """a <= b over extended values that are not NaN."""
    return not less(b, a)


def xneg(a):
    return NINF if a == PINF else PINF if a == NINF else -a


def interval_state(fmt, lo, hi):
    """'empty', 'bounded' or 'unbounded' for a canonical interval with bounds lo and hi (lists of
    limbs), None for a value that is not canonical."""
    n = len(lo)
    if lo[0] == PINF and hi[0] == NINF and all(finite(v) and v[2] == 0 for v in lo[1:] + hi[1:]):
        return 'empty'
    for b in (lo, hi):
        if b[0][0] == NAN or (n == 2 and not fmt.canonical(b)) or (b[0][0] == INF and n == 2 and b[1][2] != 0):
            return None
    a, z = bound_value(lo), bound_value(hi)
    if not xle(a, z) or a == PINF or z == NINF:
        return None
    return 'bounded' if finite(lo[0]) and finite(hi[0]) else 'unbounded'


def xproduct0(a, b):
    """The product of two bounds with 0 * infinity = 0 (the rule of interval arithmetic)."""
    if a == 0 or b == 0:
        return F(0)
    if a in (PINF, NINF) or b in (PINF, NINF):
        neg = (a == NINF or (a not in (PINF, NINF) and a < 0)) != (b == NINF or (b not in (PINF, NINF) and b < 0))
        return NINF if neg else PINF
    return a * b


def xsum(a, b):
    if a in (PINF, NINF):
        return a
    if b in (PINF, NINF):
        return b
    return a + b


def exact_range(tree, env):
    """The bounds (lower, upper) of the exact range of an expression over intervals, each name
    occurring once, env mapping a name to its bounds (extended, nonempty): the sum and the
    difference of bounds, the opposite exchanged, and the least and greatest of the four products
    of bounds with 0 * infinity = 0 (Rectangle.v)."""
    kind = tree[0]
    if kind == 'name':
        return env[tree[1]]
    if kind == 'neg':
        a, b = exact_range(tree[1], env)
        return xneg(b), xneg(a)
    (a, b), (c, d) = exact_range(tree[1], env), exact_range(tree[2], env)
    if kind == 'add':
        return xsum(a, c), xsum(b, d)
    if kind == 'sub':
        return xsum(a, xneg(d)), xsum(b, xneg(c))
    if kind == 'mul':
        ps = [xproduct0(x, y) for x in (a, b) for y in (c, d)]
        lo = ps[0]
        hi = ps[0]
        for p in ps[1:]:
            lo = p if less(p, lo) else lo
            hi = p if less(hi, p) else hi
        return lo, hi
    raise AssertionError(kind)


def stepped(fmt, x, below, steps):
    """x stepped `steps` times down (or up) in the format with overflow, as an extended value."""
    for _ in range(steps):
        if x in (PINF, NINF):
            if (x == PINF) == below:
                x = fmt.top if x == PINF else -fmt.top
            continue
        y = fmt.pred(x) if below else fmt.succ(x)
        x = y if abs(y) <= fmt.top else (NINF if below else PINF)
    return x


def directed(fmt, x, mode):
    """x rounded down or up in the format with overflow, as an extended value."""
    if x in (PINF, NINF):
        return x
    r = fmt.ieee_round(x, mode)
    return r if r in (PINF, NINF) else fr(r)


def judge_interval(k, ks, fmt, e, ins, outs, values):
    """I1 to I5 of milestone2.md, "What is stated of an interval kernel", for canonical operands."""
    zl, zu = outs[e['lower']], outs[e['upper']]
    state = interval_state(fmt, zl, zu)
    names = list(e['intervals'])
    ops = {x: interval_state(fmt, ins[b['lower']], ins[b['upper']]) for x, b in e['intervals'].items()}
    bad = []
    if state is None:
        return ['I1']
    if (state == 'empty') != ('empty' in ops.values()):
        bad.append('I2')
    if 'empty' in ops.values():
        return bad
    env = {x: (bound_value(ins[b['lower']]), bound_value(ins[b['upper']])) for x, b in e['intervals'].items()}
    lo, hi = exact_range(expr.parse(e['set']), env)
    if state == 'empty':
        return bad + ['I3']
    a, z = bound_value(zl), bound_value(zu)
    if not (xle(a, lo) and xle(hi, z)):
        bad.append('I3')
    t = e['tight']
    if t['kind'] == 'exact' and (a != lo or z != hi):
        bad.append('I4 (exact)')
    elif t['kind'] == 'rounded':
        rd, ru = directed(fmt, lo, 'down'), directed(fmt, hi, 'up')
        steps = t.get('steps', 0)
        # Exactly the directed roundings: always without a condition, and under the condition
        # (each product of a bound of x and one of y, both finite, zero or at least P) with one.
        exact = not steps
        if t.get('when') == 'product_large':
            tree = expr.parse(e['set'])
            xs, ys = (env[x[1]] for x in tree[1:])
            exact = all(p in (PINF, NINF) or q in (PINF, NINF) or ts.product_large(fmt, p * q) for p in xs for q in ys)
        if exact and (a != rd or z != ru):
            bad.append('I4 (rounded)')
        if steps and not (xle(stepped(fmt, rd, True, steps), a) and xle(a, rd) and
                          xle(ru, z) and xle(z, stepped(fmt, ru, False, steps))):
            bad.append('I4 (steps)')
    elif t['kind'] == 'outward':
        if lo == NINF and a != NINF or hi == PINF and z != PINF:
            bad.append('I4 (infinite)')
        if all(s == 'bounded' for s in ops.values()):
            exact_env = {g.name: group_value(ins[g.name]) for g in k.inputs}
            for side, v, w in (('lower', lo, a), ('upper', hi, z)):
                conds = t.get('exact_when', {}).get(side)
                if conds and ts.exact_conditions(e, fmt, exact_env, {}, conds) and w != v:
                    bad.append(f'I4 (exact {side})')
            if state == 'bounded':
                rel, absolute = ts.claim_constant(t['rel'], fmt), ts.claim_constant(t['abs'], fmt)
                if lo - a > rel * abs(lo) + absolute or z - hi > rel * abs(hi) + absolute:
                    bad.append('I4 (outward)')
    if e.get('zero_factor'):
        # Stage B1 (interval_mul_2): a nonempty operand [0, 0] gives [0, 0].
        if any(env[x] == (0, 0) for x in names) and (a, z) != (0, 0):
            bad.append('I6 (zero factor)')
    if e['bounded_when'] and all(s == 'bounded' for s in ops.values()):
        within = all(max(abs(lo), abs(hi)) <= (fmt.top if c.get('omega') else fmt.threshold * F(2) ** c['exp'])
                     for c in e['bounded_when'])
        if within and state != 'bounded':
            bad.append('I5')
        if e.get('bounded_exactly') and state == 'bounded' and not within:
            bad.append('I5 (exactly)')
    return bad


def judge_interval_set(k, ks, fmt, e, ins, outs, values):
    """The hull (union) or the intersection of two intervals (stage B1): canonical; empty exactly
    when both operands are (union) or when no real number is a member of both (intersection);
    otherwise the bounds of the set."""
    zl, zu = outs[e['lower']], outs[e['upper']]
    state = interval_state(fmt, zl, zu)
    if state is None:
        return ['interval_set (canonical)']
    bounds = [(bound_value(ins[b['lower']]), bound_value(ins[b['upper']])) for b in e['intervals'].values()]
    nonempty = [b for b, x in zip(bounds, e['intervals'].values())
                if interval_state(fmt, ins[x['lower']], ins[x['upper']]) != 'empty']
    if e['set'] == 'union':
        if not nonempty:
            return [] if state == 'empty' else ['interval_set (empty)']
        lo = min((b[0] for b in nonempty), key=_rank)
        hi = max((b[1] for b in nonempty), key=_rank)
    else:
        lo = max((b[0] for b in bounds), key=_rank) if len(nonempty) == len(bounds) else PINF
        hi = min((b[1] for b in bounds), key=_rank) if len(nonempty) == len(bounds) else NINF
        if lo == PINF or hi == NINF or less(hi, lo):
            return [] if state == 'empty' else ['interval_set (empty)']
    if state == 'empty':
        return ['interval_set (empty)']
    return [] if (bound_value(zl), bound_value(zu)) == (lo, hi) else ['interval_set (bounds)']


def _rank(x):
    """A key that orders extended values that are not NaN."""
    return (-1, 0) if x == NINF else (1, 0) if x == PINF else (0, x)


def judge_ball_of_interval(k, ks, fmt, e, ins, outs, values):
    """A ball made from an interval (stage B1): the special values of IEEE 1788's mid and rad, or of
    a canonical ball, for an interval that is not bounded; for a bounded one a finite center within
    the bounds and within rel |mid| + abs of the midpoint, a finite radius with which it contains
    the interval, and with smallest_radius RU of the larger distance to a bound."""
    lo, hi = ins[e['from']['lower']], ins[e['from']['upper']]
    c, r = outs[e['center']], outs[e['radius']][0]
    state = interval_state(fmt, lo, hi)
    a, z = bound_value(lo), bound_value(hi)
    if e['special'] == 'ball':
        ball = ball_state(fmt, c, r)
        want = {'empty': 'empty', 'unbounded': 'line', 'bounded': 'finite'}[state]
        if ball != want:
            return [f'ball_of_interval ({want} expected)']
    elif state == 'empty':
        return [] if all(v[0] == NAN for v in list(c) + [r]) else ['ball_of_interval (empty)']
    elif state == 'unbounded':
        want = F(0) if (a, z) == (NINF, PINF) else (fmt.top if z == PINF else -fmt.top)
        ok = all(finite(v) for v in c) and sum(fr(v) for v in c) == want and r == PINF
        return [] if ok else ['ball_of_interval (unbounded)']
    if state != 'bounded':
        return []
    if not (all(finite(v) for v in c) and finite(r)):
        return ['ball_of_interval (finite)']
    m, rad = sum(fr(v) for v in c), fr(r)
    mid = (a + z) / 2
    rel, absolute = ts.claim_constant(e['rel'], fmt), ts.claim_constant(e['abs'], fmt)
    if not (a <= m <= z) or abs(m - mid) > rel * abs(mid) + absolute:
        return ['ball_of_interval (center)']
    if max(m - a, z - m) > rad:
        return ['ball_of_interval (containment)']
    if e.get('smallest_radius') and rad != fmt.round(max(m - a, z - m), 'up'):
        return ['ball_of_interval (smallest radius)']
    return []


def judge_interval_of_ball(k, ks, fmt, e, ins, outs, values):
    """An interval that encloses a ball (stage B1): canonical; empty exactly when a ball operand
    is; containing every value of the set; and with tight=rounded the bounds of the set rounded
    down and up in the format with overflow."""
    zl, zu = outs[e['lower']], outs[e['upper']]
    state = interval_state(fmt, zl, zu)
    if state is None:
        return ['interval_of_ball (canonical)']
    states = {b: ball_state(fmt, ins[cr['center']], ins[cr['radius']][0]) for b, cr in e['balls'].items()}
    if 'empty' in states.values():
        return [] if state == 'empty' else ['interval_of_ball (empty)']
    if state == 'empty':
        return ['interval_of_ball (empty)']
    env = {}
    for b, cr in e['balls'].items():
        if states[b] == 'line':
            env[b] = (NINF, PINF)
        else:
            cv, rv = sum(fr(v) for v in ins[cr['center']]), fr(ins[cr['radius']][0])
            env[b] = (cv - rv, cv + rv)
    lo, hi = exact_range(expr.parse(e['set']), env)
    a, z = bound_value(zl), bound_value(zu)
    if not (xle(a, lo) and xle(hi, z)):
        return ['interval_of_ball (containment)']
    rd, ru = directed(fmt, lo, 'down'), directed(fmt, hi, 'up')
    steps = e['tight'].get('steps', 0)
    if not (xle(stepped(fmt, rd, True, steps), a) and xle(a, rd) and xle(ru, z) and xle(z, stepped(fmt, ru, False, steps))):
        return ['interval_of_ball (rounded)']
    return []


def judge_splits(k, ks, fmt, e, ins, outs, values):
    """Two intervals that together are the operand (stage B1): both canonical; both empty for the
    empty set; otherwise both nonempty, from the operand's lower bound to a point and from that
    point to its upper bound."""
    lo, hi = ins[e['from']['lower']], ins[e['from']['upper']]
    (al, au), (bl, bu) = ((outs[q['lower']], outs[q['upper']]) for q in e['parts'])
    sa, sb = interval_state(fmt, al, au), interval_state(fmt, bl, bu)
    if sa is None or sb is None:
        return ['splits (canonical)']
    if interval_state(fmt, lo, hi) == 'empty':
        return [] if sa == sb == 'empty' else ['splits (empty)']
    if 'empty' in (sa, sb):
        return ['splits (empty part)']
    ok = (bound_value(al) == bound_value(lo) and bound_value(bu) == bound_value(hi) and
          bound_value(au) == bound_value(bl))
    return [] if ok else ['splits (cover)']


def judge_makes_interval(k, ks, fmt, e, ins, outs, values):
    """The constructor of an interval: canonical; the interval of the bounds given when they
    describe a nonempty one; the whole line when a bound is a NaN; the empty set otherwise."""
    lo, hi = ins[e['from']['lower']], ins[e['from']['upper']]      # of one limb, or two (stage B1)
    zl, zu = outs[e['lower']], outs[e['upper']]
    state = interval_state(fmt, zl, zu)
    if state is None:
        return ['makes_interval (canonical)']
    if NAN in (lo[0][0], hi[0][0]):
        ok = zl[0] == NINF and zu[0] == PINF and all(finite(v) and v[2] == 0 for v in zl[1:] + zu[1:])
    elif xle(bound_value(lo), bound_value(hi)) and lo[0] != PINF and hi[0] != NINF:
        ok = state != 'empty' and bound_value(zl) == bound_value(lo) and bound_value(zu) == bound_value(hi)
    else:
        ok = state == 'empty'
    return [] if ok else ['makes_interval']


def judge_ball_from_interval(k, ks, fmt, e, ins, outs):
    """A ball from the bounds of an interval of two values of T (milestone2.md, "A ball from an
    interval of two T")."""
    lo, hi = ins[e['from']['lower']][0], ins[e['from']['upper']][0]
    oc, orad = outs[e['center']], outs[e['radius']][0]
    state = ball_state(fmt, oc, orad)
    if state is None:
        return ['makes_ball (canonical)']
    if NAN in (lo[0], hi[0]):
        want = 'line'
    elif xle(bound_value([lo]), bound_value([hi])) and lo != PINF and hi != NINF:
        want = 'finite' if finite(lo) and finite(hi) else 'line'
    else:
        want = 'empty'
    if state != want:
        return [f'makes_ball ({want} expected)']
    if want != 'finite':
        return []
    c, r, a, b = sum(fr(v) for v in oc), fr(orad), fr(lo), fr(hi)
    if not (abs(a - c) <= r and abs(b - c) <= r):
        return ['makes_ball (containment)']
    halves = all(fr(ins[x['half_in_format']][0]) / 2 in fmt.members for x in e.get('midpoint_when', []))
    if e.get('midpoint_when') and halves and (c != (a + b) / 2 or r != fmt.round((b - a) / 2, 'up')):
        return ['makes_ball (midpoint)']
    return []


def judge_set_bound(k, ks, fmt, e, ins, outs, values):
    """A bound of a set over balls as a number of T: +inf below (-inf above) for the empty set, on
    its side of the bound of the set otherwise, and with tight=rounded the directed rounding of it."""
    out = outs[e['of']][0]
    below = e['side'] == 'below'
    states = {b: ball_state(fmt, ins[cr['center']], ins[cr['radius']][0]) for b, cr in e['balls'].items()}
    if out[0] == NAN:
        return ['set_bound (NaN)']
    if 'empty' in states.values():
        return [] if out == (PINF if below else NINF) else ['set_bound (empty)']
    env = {}
    for b, cr in e['balls'].items():
        if states[b] == 'line':
            env[b] = (NINF, PINF)
        else:
            c, r = sum(fr(v) for v in ins[cr['center']]), fr(ins[cr['radius']][0])
            env[b] = (c - r, c + r)
    lo, hi = exact_range(expr.parse(e['set']), env)
    v = lo if below else hi
    t = out if out in (PINF, NINF) else fr(out)
    if not (xle(t, v) if below else xle(v, t)):
        return ['set_bound (side)']
    tight = e.get('tight')
    if tight is not None:
        r = directed(fmt, v, 'down' if below else 'up')
        steps = tight.get('steps', 0)
        limit = stepped(fmt, r, below, steps)
        if not (xle(limit, t) and xle(t, r) if below else xle(r, t) and xle(t, limit)):
            return ['set_bound (rounded)']
    return []


def judge_makes_ball(k, ks, fmt, e, ins, outs, values):
    if 'lower' in e['from']:
        return judge_ball_from_interval(k, ks, fmt, e, ins, outs)
    center, radius = ins[e['from']['center']], ins[e['from']['radius']][0]
    oc, orad = outs[e['center']], outs[e['radius']][0]
    state = ball_state(fmt, oc, orad)
    if state is None:
        return ['makes_ball (canonical)']
    if radius == NINF or (finite(radius) and radius[1] and radius[2] != 0):
        want = 'empty'                  # a negative radius, -inf included
    elif radius[0] == NAN or not all(finite(v) for v in center) or radius == PINF:
        want = 'line'                   # a NaN radius too (decided on 2026-11-20)
    else:
        want = 'finite'
    if state != want:
        return [f'makes_ball ({want} expected)']
    if want == 'finite' and (sum(fr(v) for v in oc) != sum(fr(v) for v in center) or fr(orad) != fr(radius)
                             or [fr(v) for v in oc] != [fr(v) for v in center]):
        return ['makes_ball (not the given ball)']
    return []


def judge_no_fix_up(k, ks, fmt, e, ins, outs, values):
    """The kernels that need no fix-up, in the extended domain (milestone1.md, the table of
    "Kernels that need no fix-up"; architecture.md, the meanings of the extended domain)."""
    kind = e['kind']
    vals = {g.name: group_value(ins[g.name]) for g in k.inputs if g.kind == ir.LIMB}
    all_finite = all(finite(v) for g in k.inputs if g.kind == ir.LIMB for v in ins[g.name])
    if e.get('zero_factor'):
        # A zero operand gives zero (Milestone 2, mul_dir_1: 0 times infinity is 0); otherwise the
        # entry is read as without the field.
        a, b = (vals[x[1]] for x in expr.parse(k.value)[1:])
        if a == 0 or b == 0:
            return [] if all(finite(t) and t[2] == 0 for t in outs[e['of']]) else [f'{kind} (zero factor)']
    if kind in ('normalized', 'error'):
        out = outs[e['of']]
        if not fmt.canonical(out):
            return [f'{kind} (canonical)']
        if all_finite and all(finite(v) for v in out):
            exact = {n: v for n, v in vals.items()}
            if not ts.holds(e, k, fmt, exact, {e['of']: [fr(v) for v in out]}):
                return [kind]
        # Which non-finite value comes out is said by represents (neg_2, abs_2), judged apart.
        return []
    if kind == 'predicate':
        a, b = (extended(x, vals) for x in e['args'])
        if NaN in (a, b):
            want = False
        else:
            want = {'lt': less(a, b), 'le': less(a, b) or a == b, 'eq': a == b}[e['rel']]
        return [] if outs[e['of']][0] == want else ['predicate']
    if kind == 'rounded':
        x = extended(k.value, vals)
        t = outs[e['of']][0]
        if x == NaN:
            ok = t[0] == NAN
        elif x in (PINF, NINF):
            ok = t == x
        elif e.get('when') == 'product_large' and not ts.product_large(fmt, x):
            ok = True                   # no claim on finite operands outside the condition
        else:
            want = fmt.ieee_round(x, e['mode'])
            ok = t == want if not finite(want) else (finite(t) and fr(t) == fr(want))
        return [] if ok else ['rounded']
    if kind == 'neighbor':
        # milestone2.md, the table of "next_up and next_down on every input".
        x, t, up = vals[k.value], outs[e['of']][0], e['side'] == 'up'
        if x == NaN:
            ok = t[0] == NAN
        elif x == (PINF if up else NINF):
            ok = t == x
        elif x in (PINF, NINF):
            ok = finite(t) and fr(t) == (fmt.top if x == PINF else -fmt.top)
        else:
            want = fmt.succ(x) if up else fmt.pred(x)
            ok = (t == (PINF if up else NINF)) if abs(want) > fmt.top else (finite(t) and fr(t) == want)
        return [] if ok else ['neighbor']
    if kind == 'bound':
        x, t, below = extended(k.value, vals), outs[e['of']][0], e['side'] == 'below'
        if not all_finite:              # the value of IEEE 754
            ok = (t[0] == NAN) if x == NaN else (t == x) if x in (PINF, NINF) else \
                (finite(t) and fr(t) == x)
            return [] if ok else ['bound (non-finite operand)']
        # The directed rounding in the format with overflow, then `steps` steps beyond it, as
        # extended reals: a step beyond the largest number is the infinity.
        limit = fmt.ieee_round(x, 'down' if below else 'up')
        for _ in range(e['steps']):
            if finite(limit):
                y = fmt.pred(fr(limit)) if below else fmt.succ(fr(limit))
                limit = make(y) if abs(y) <= fmt.top else (NINF if below else PINF)
        if t[0] == NAN:
            return ['bound']
        rank = {NINF: -1, PINF: 1}

        def le(a, b):           # a <= b over extended values (a Fraction for a finite one)
            ra, rb = rank.get(a, 0), rank.get(b, 0)
            return ra < rb or (ra == rb and (ra != 0 or a <= b))
        tv = t if t in (PINF, NINF) else fr(t)
        lv = limit if limit in (PINF, NINF) else fr(limit)
        ok = le(lv, tv) and le(tv, x) if below else le(x, tv) and le(tv, lv)
        return [] if ok else ['bound']
    if kind == 'outward':
        # Stage B1 (mul_ext_2_2): not a NaN; an infinite operand gives the value of IEEE 754; finite
        # operands an output on its side of the value, within rel |value| + abs when it is finite.
        out = outs[e['of']]
        if out[0][0] == NAN:
            return ['outward (NaN)']
        got = group_value(out)
        if not all_finite:
            return [] if got == extended(k.value, vals) else ['outward (non-finite operand)']
        v = extended(k.value, vals)
        below = e['side'] == 'below'
        if not (xle(got, v) if below else xle(v, got)):
            return ['outward (side)']
        if got in (PINF, NINF):
            return []
        rel, absolute = ts.claim_constant(e['rel'], fmt), ts.claim_constant(e['abs'], fmt)
        if abs(got - v) > rel * abs(v) + absolute:
            return ['outward (bound)']
        return []
    if kind == 'upper':
        a, b = (vals[g.name] for g in k.inputs)
        x = ieee('add' if '+' in k.value else 'mul', a, b)
        r = outs[e['of']][0]
        if (r[0] == NAN) != (x == NaN):
            return ['upper (NaN)']
        if x == NaN:
            return []
        if x == PINF:
            return [] if r == PINF else ['upper']
        if r == PINF:
            return []                   # not below; gaps applies to finite outputs only
        if not finite(r) or fr(r) < x:
            return ['upper']
        gaps = expr.evaluate(expr.parse(e['gaps']), {})
        return [] if fr(r) - x <= gaps * (fr(r) - fmt.pred(fr(r))) else ['upper (gaps)']
    raise AssertionError(kind)


def less(a, b):
    rank = {NINF: -1, PINF: 1}
    ra, rb = rank.get(a, 0), rank.get(b, 0)
    if ra or rb:
        return ra < rb
    return a < b


def extended(text, vals):
    """An expression of a claim over extended values: names, abs, unary minus and one binary
    operation, which is all the kernels that need no fix-up use."""
    tree = expr.parse(text)

    def ev(t):
        if t[0] == 'name':
            return vals[t[1]]
        if t[0] == 'neg':
            x = ev(t[1])
            return NaN if x == NaN else NINF if x == PINF else PINF if x == NINF else -x
        if t[0] == 'abs':
            x = ev(t[1])
            return NaN if x == NaN else PINF if x in (PINF, NINF) else abs(x)
        return ieee(t[0], ev(t[1]), ev(t[2]))
    return ev(tree)


def judge_finite_or_nan(k, ks, fmt, e, ins, outs, values):
    """The finish of a fold (milestone2.md, "When something is not finite"): the flag is true
    exactly when limb 0 of the value is finite; the output is then the value, limb for limb, and
    otherwise every limb of it is a NaN."""
    src, out, flag = ins[k.value], outs[e['of']], outs[e['flag']][0]
    # The finish of a fold of maxima: the value stepped up (steps), and a NaN when the mask (if) is
    # false.
    for _ in range(e.get('steps', 0)):
        src = [interp.succ(fmt.f, v) for v in src]
    # The finish of a constructor of a BallVector (nonneg): the value is also not negative (a zero of
    # either sign is not).
    sign = not e.get('nonneg') or (finite(src[0]) and not (src[0][1] and src[0][2]))
    # The finish of the product of two BallVectors (if_all): every mask true.
    gate = all(ins[n][0] for n in e.get('if_all', [])) and (ins[e['if']][0] if 'if' in e else True)
    if flag != (finite(src[0]) and gate and sign):
        return ['finite_or_nan (flag)']
    if flag:
        return [] if out == src else ['finite_or_nan (not the value)']
    return [] if all(v[0] == NAN for v in out) else ['finite_or_nan (not NaN)']


JUDGES = {'extends': judge_extends, 'encloses': judge_ball, 'represents': judge_represents,
          'makes_ball': judge_makes_ball, 'finite_or_nan': judge_finite_or_nan,
          'encloses_interval': judge_interval,
          'makes_interval': judge_makes_interval, 'set_bound': judge_set_bound,
          'interval_set': judge_interval_set, 'ball_of_interval': judge_ball_of_interval,
          'interval_of_ball': judge_interval_of_ball, 'splits': judge_splits}


def judge(job):
    name, (p, qmin, qmax), seed = job
    ks = common.kernels()
    k = ks[name]
    fmt = Fmt(p, qmin, qmax)
    m = interp.Machine(ks)
    ops, all_cases = cases(k, fmt, seed)
    failures = {}
    seen = set()
    count = 0
    for case in all_cases:
        values = []
        ins = {}
        for op, v in zip(ops, case):
            i = 0
            for g in op.groups:
                ins[g.name] = list(v[i:i + len(g.limbs)])
                i += len(g.limbs)
        values = [x for g in k.inputs for x in ins[g.name]]
        got = m.run(name, fmt.f, values)
        it = iter(got)
        outs = {g.name: [next(it) for _ in g.limbs] for g in k.outputs}
        bad = []
        for e in k.ensures:
            judge_one = JUDGES.get(e['kind'], judge_no_fix_up)
            bad += judge_one(k, ks, fmt, e, ins, outs, values)
            seen.add(situation(k, fmt, e, values, outs))
        count += 1
        for statement in bad:
            failures.setdefault(statement, []).append(
                (' '.join(interp.format_mask(v) if isinstance(v, bool) else show(v) for v in values),
                 ' '.join(interp.format_mask(v) if isinstance(v, bool) else show(v) for v in got)))
    return name, fmt.name, count, {s: (len(v), v[:3]) for s, v in failures.items()}, seen


def situation(k, fmt, e, values, outs):
    """What a case exercised, so that the test can tell that every situation of the statements
    was reached: for a full kernel, a non-finite operand, an overflow on finite operands or a finite
    result; for a ball, the state of the result; for the others, whether an operand was finite."""
    operands_finite = all(isinstance(v, bool) or finite(v) for v in values)
    if e['kind'] == 'extends':
        if not operands_finite:
            return 'non-finite operand'
        return 'finite' if finite(outs[e['of']][0]) else 'overflow'
    if e['kind'] in ('encloses', 'makes_ball'):
        state = ball_state(fmt, outs[e['center']], outs[e['radius']][0])
        return f'{state} from {"finite" if operands_finite else "non-finite"} operands'
    if e['kind'] in ('encloses_interval', 'makes_interval', 'interval_set', 'interval_of_ball'):
        return f'{interval_state(fmt, outs[e["lower"]], outs[e["upper"]])} result'
    if e['kind'] in ('ball_of_interval', 'splits'):
        lo, hi = e['from']['lower'], e['from']['upper']
        it = iter(values)
        ins = {g.name: [next(it) for _ in g.limbs] for g in k.inputs}
        return f'{interval_state(fmt, ins[lo], ins[hi])} operand'
    return 'finite operands' if operands_finite else 'non-finite operand'


def run_all(names, seed):
    ks = common.kernels()
    jobs = [(n, f, seed) for n in names for f in FORMATS if not ks[n].min_precision or f[0] >= ks[n].min_precision]
    with ProcessPoolExecutor(max_workers=common.JOBS) as ex:
        return list(ex.map(judge, jobs))


# The (kernel, statement) pairs that fail somewhere in the enumeration, as findings to report: the
# statements of milestone1.md are targets, and a failing one is a question for the design, not
# something to fix here. Empty when every target holds on every case tried.
KNOWN = set()


class NonFinite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()
        cls.names = [n for n, k in cls.ks.items() if k.extended]
        cls.results = run_all(cls.names, 'nonfinite')

    def test_every_kernel_of_the_extended_domain_is_judged(self):
        judged = {name for name, _, count, _, _ in self.results if count}
        self.assertEqual(judged, set(self.names))
        # Full kernels, full Ball kernels, constructors, and the kernels that need no fix-up
        # (ball_neg_k among them): 39 of Milestone 1, and 15 of wave 1 of Milestone 2 (the steps,
        # the directed sums and products, five entry forms, the full scalings by a power of two),
        # and 13 of wave 2: the interval kernels, mul_dir_1, the bounds of a ball as numbers of T,
        # the ball from an interval and the narrowing of a ball; and 13 of stage B1; and the two
        # finishes of the folds, and the two of the folds of maxima; and the copy and the finish of the
        # constructors of a BallVector, bv_center_2 and bv_make_finish; and the finish of the product of two
        # BallVectors, bv_conv_finish.
        self.assertEqual(len(self.names), 54 + 13 + 13 + 4 + 2 + 1)

    def test_every_situation_is_reached(self):
        """The cases reach what the statements are about: every full kernel overflows on finite
        operands (F4), gets non-finite operands (F5) and finite results (F2); every full Ball
        kernel returns each of the three states, the whole line also from finite balls (but
        ball_neg_k, which keeps a finite ball finite); the
        constructors of balls make each state."""
        seen = {}
        for name, _, _, _, s in self.results:
            seen.setdefault(name, set()).update(s)
        for name in self.names:
            k = self.ks[name]
            kinds = {e['kind'] for e in k.ensures}
            if 'extends' in kinds:
                want = {'finite', 'overflow', 'non-finite operand'}
            elif 'encloses' in kinds:
                want = {'finite from finite operands', 'line from non-finite operands', 'empty from non-finite operands'}
                if not k.real_model:
                    want.add('line from finite operands')      # ball_neg_k keeps a finite ball finite
            elif 'makes_ball' in kinds:
                want = {'finite from finite operands', 'empty from finite operands',
                        'line from non-finite operands', 'empty from non-finite operands'}
            elif kinds & {'encloses_interval', 'makes_interval', 'interval_set', 'interval_of_ball'}:
                # The interval kernels and their constructor return each of the three states.
                want = {'empty result', 'bounded result', 'unbounded result'}
            elif kinds & {'ball_of_interval', 'splits'}:
                # They are given intervals in each of the three states.
                want = {'empty operand', 'bounded operand', 'unbounded operand'}
            else:
                want = {'finite operands', 'non-finite operand'}
            self.assertLessEqual(want, seen[name], name)

    def test_the_targets(self):
        """F1 to F5, B1 to B4, the constructors, and the extended domain of the kernels that need
        no fix-up. Failures are printed with their first cases and compared with KNOWN."""
        found = {}
        for name, fmt, count, failures, _ in self.results:
            for statement, (n, first) in failures.items():
                found.setdefault((name, statement), []).append((fmt, n, count, first))
        if found:
            print('\n  non-finite layer: statements of milestone1.md that fail', file=sys.stderr)
            for (name, statement), where in sorted(found.items()):
                for fmt, n, count, first in where:
                    print(f'  {name} {statement} on {fmt}: {n} of {count} cases, e.g.', file=sys.stderr)
                    for request, got in first:
                        print(f'      {name} {fmt} {request} -> {got}', file=sys.stderr)
        self.assertEqual(set(found), KNOWN)

    def test_the_judge(self):
        """The judge itself, on chosen results that must pass and fail."""
        ks = self.ks
        fmt = Fmt(3, -4, 1)
        one, two = make(F(1)), make(F(2))
        x = {'x': [one, ZERO], 'y': [one, ZERO]}
        e = ks['add_2_2_full'].ensures[0]
        self.assertEqual(judge_extends(ks['add_2_2_full'], ks, fmt, e, x, {'w': [two, ZERO]}, None), [])
        self.assertIn('F2 (error)', judge_extends(ks['add_2_2_full'], ks, fmt, e, x,
                                                  {'w': [make(F(5, 2)), ZERO]}, None))
        self.assertIn('F1', judge_extends(ks['add_2_2_full'], ks, fmt, e, x, {'w': [PINF, one]}, None))
        self.assertEqual(judge_extends(ks['add_2_2_full'], ks, fmt, e, {'x': [PINF, ZERO], 'y': [NINF, NZERO]},
                                       {'w': [NaN, NaN]}, None), [])
        self.assertIn('F5', judge_extends(ks['add_2_2_full'], ks, fmt, e, {'x': [PINF, ZERO], 'y': [NINF, NZERO]},
                                          {'w': [PINF, ZERO]}, None))
        big = {'x': [make(F(14)), ZERO], 'y': [make(F(14)), ZERO]}
        self.assertEqual(judge_extends(ks['add_2_2_full'], ks, fmt, e, big, {'w': [PINF, NZERO]}, None), [])
        self.assertIn('F4', judge_extends(ks['add_2_2_full'], ks, fmt, e, big, {'w': [NINF, ZERO]}, None))
        small = {'x': [make(F(2)), ZERO], 'y': [make(F(2)), ZERO]}       # within a quarter of 16
        self.assertIn('F3', judge_extends(ks['add_2_2_full'], ks, fmt, e, small, {'w': [PINF, ZERO]}, None))
        # No condition proved: F3 claims nothing (an empty list is not "always finite").
        ef = dict(ks['add_fast_2_2_full'].ensures[0], finite_when=[])
        self.assertEqual(judge_extends(ks['add_fast_2_2_full'], ks, fmt, ef, small, {'w': [PINF, ZERO]}, None), [])
        self.assertEqual(ieee('mul', F(0), NINF), NaN)
        self.assertEqual(ieee('sub', NINF, F(-3)), NINF)
        self.assertEqual(ieee('mul', F(-1, 2), PINF), NINF)
        b = ks['ball_add_1_full'].ensures[0]
        ins = {'cx': [one], 'rx': [ZERO], 'cy': [one], 'ry': [make(F(1, 2))]}
        self.assertEqual(judge_ball(ks['ball_add_1_full'], ks, fmt, b, ins, {'cw': [two], 'rw': [make(F(1, 2))]}, None), [])
        self.assertIn('B3 (containment)', judge_ball(ks['ball_add_1_full'], ks, fmt, b, ins,
                                                     {'cw': [two], 'rw': [make(F(1, 4))]}, None))
        self.assertIn('B2', judge_ball(ks['ball_add_1_full'], ks, fmt, b, ins, {'cw': [NaN], 'rw': [NaN]}, None))
        # The whole line on finite operands: a failure of B4 where the condition holds (here
        # |1 + 1| + 0 + 1/2 is within a quarter of 16), accepted beyond it, and accepted
        # everywhere by a claim without conditions (an empty list is not "always finite").
        whole = {'cw': [ZERO], 'rw': [PINF]}
        self.assertEqual(judge_ball(ks['ball_add_1_full'], ks, fmt, b, ins, whole, None), ['B4'])
        far = {'cx': [make(F(3))], 'rx': [one], 'cy': [one], 'ry': [make(F(1, 2))]}     # 5.5 > 4
        self.assertEqual(judge_ball(ks['ball_add_1_full'], ks, fmt, b, far, whole, None), [])
        edge = {'cx': [make(F(3))], 'rx': [ZERO], 'cy': [make(F(1, 2))], 'ry': [make(F(1, 2))]}   # exactly 4
        self.assertEqual(judge_ball(ks['ball_add_1_full'], ks, fmt, b, edge, whole, None), ['B4'])
        bf = dict(b, finite_when=[])
        self.assertEqual(judge_ball(ks['ball_add_1_full'], ks, fmt, bf, ins, whole, None), [])
        self.assertIn('B1', judge_ball(ks['ball_add_1_full'], ks, fmt, b, ins, {'cw': [one], 'rw': [PINF]}, None))
        empty = dict(ins, rx=[NaN], cx=[NaN])
        self.assertEqual(judge_ball(ks['ball_add_1_full'], ks, fmt, b, empty, {'cw': [NaN], 'rw': [NaN]}, None), [])
        self.assertIn('B2', judge_ball(ks['ball_add_1_full'], ks, fmt, b, empty, {'cw': [ZERO], 'rw': [PINF]}, None))
        mb = ks['ball_make_1'].ensures[0]
        self.assertEqual(judge_makes_ball(ks['ball_make_1'], ks, fmt, mb, {'c': [one], 'r': [NZERO]},
                                          {'cw': [one], 'rw': [ZERO]}, None), [])
        self.assertEqual(judge_makes_ball(ks['ball_make_1'], ks, fmt, mb, {'c': [one], 'r': [make(F(-1))]},
                                          {'cw': [ZERO], 'rw': [PINF]}, None), ['makes_ball (empty expected)'])
        self.assertEqual(judge_makes_ball(ks['ball_make_1'], ks, fmt, mb, {'c': [PINF], 'r': [NINF]},
                                          {'cw': [NaN], 'rw': [NaN]}, None), [])
        # Intervals (Milestone 2): [1, 1] + [1, 1] is [2, 2], exactly the rounded range.
        ia = ks['interval_add_1']
        ie = ia.ensures[0]
        x = {'xl': [one], 'xu': [one], 'yl': [one], 'yu': [one]}
        self.assertEqual(judge_interval(ia, ks, fmt, ie, x, {'zl': [two], 'zu': [two]}, None), [])
        self.assertEqual(judge_interval(ia, ks, fmt, ie, x, {'zl': [one], 'zu': [two]}, None), ['I4 (rounded)'])
        self.assertIn('I3', judge_interval(ia, ks, fmt, ie, x, {'zl': [make(F(5, 2))], 'zu': [make(F(3))]}, None))
        self.assertEqual(judge_interval(ia, ks, fmt, ie, x, {'zl': [two], 'zu': [one]}, None), ['I1'])
        empty = {'zl': [PINF], 'zu': [NINF]}
        self.assertIn('I2', judge_interval(ia, ks, fmt, ie, x, empty, None))
        self.assertEqual(judge_interval(ia, ks, fmt, ie, dict(x, xl=[PINF], xu=[NINF]), empty, None), [])
        # [-inf, 1] + [1, +inf] is the whole line; bounded operands whose sum is beyond the largest
        # number (14) give an unbounded result, and within it a bounded one (I5, exactly).
        whole = {'zl': [NINF], 'zu': [PINF]}
        self.assertEqual(judge_interval(ia, ks, fmt, ie, dict(x, xl=[NINF], yu=[PINF]), whole, None), [])
        big = {'xl': [make(F(12))], 'xu': [make(F(12))], 'yl': [make(F(12))], 'yu': [make(F(12))]}
        self.assertEqual(judge_interval(ia, ks, fmt, ie, big, {'zl': [make(F(14))], 'zu': [PINF]}, None), [])
        self.assertEqual(judge_interval(ia, ks, fmt, ie, x, {'zl': [two], 'zu': [PINF]}, None),
                         ['I4 (rounded)', 'I5'])
        # The product: one step beyond the rounding is accepted below P, not at it.
        im = ks['interval_mul_1']
        small = {'xl': [make(F(5, 4))], 'xu': [make(F(5, 4))], 'yl': [make(F(5, 4))], 'yu': [make(F(5, 4))]}
        self.assertEqual(judge_interval(im, ks, fmt, im.ensures[0], small,         # 25/16, below P = 2
                                        {'zl': [make(F(5, 4))], 'zu': [make(F(7, 4))]}, None), [])
        large = {'xl': [make(F(3, 2))], 'xu': [make(F(3, 2))], 'yl': [make(F(3, 2))], 'yu': [make(F(3, 2))]}
        self.assertEqual(judge_interval(im, ks, fmt, im.ensures[0], large,          # 9/4, at least P
                                        {'zl': [make(F(7, 4))], 'zu': [make(F(5, 2))]}, None), ['I4 (rounded)'])
        self.assertEqual(judge_interval(im, ks, fmt, im.ensures[0], large,
                                        {'zl': [two], 'zu': [make(F(5, 2))]}, None), [])
        mk = ks['interval_make_1']
        self.assertEqual(judge_makes_interval(mk, ks, fmt, mk.ensures[0], {'lo': [NaN], 'hi': [one]}, whole, None), [])
        self.assertEqual(judge_makes_interval(mk, ks, fmt, mk.ensures[0], {'lo': [two], 'hi': [one]}, whole, None),
                         ['makes_interval'])
        self.assertEqual(judge_makes_interval(mk, ks, fmt, mk.ensures[0], {'lo': [PINF], 'hi': [PINF]}, empty, None), [])
        # A ball made from an interval (makes_ball with a lower and an upper bound: the claim of
        # ball_from_interval_2).
        fb = ks['ball_from_interval_2'].ensures[0]
        self.assertEqual(fb, {'kind': 'makes_ball', 'center': 'cw', 'radius': 'rw', 'from': {'lower': 'lo', 'upper': 'hi'},
                              'midpoint_when': [{'half_in_format': 'lo'}, {'half_in_format': 'hi'}]})
        lohi = {'lo': [one], 'hi': [two]}
        self.assertEqual(judge_makes_ball(None, ks, fmt, fb, lohi, {'cw': [make(F(3, 2)), ZERO], 'rw': [make(F(1, 2))]},
                                          None), [])
        self.assertEqual(judge_makes_ball(None, ks, fmt, fb, lohi, {'cw': [make(F(3, 2)), ZERO], 'rw': [one]}, None),
                         ['makes_ball (midpoint)'])
        self.assertEqual(judge_makes_ball(None, ks, fmt, fb, lohi, {'cw': [one, one], 'rw': [make(F(1, 2))]}, None),
                         ['makes_ball (canonical)'])
        self.assertEqual(judge_makes_ball(None, ks, fmt, fb, lohi, {'cw': [one, ZERO], 'rw': [make(F(1, 2))]}, None),
                         ['makes_ball (containment)'])
        self.assertEqual(judge_makes_ball(None, ks, fmt, fb, {'lo': [NaN], 'hi': [two]}, {'cw': [ZERO, ZERO], 'rw': [PINF]},
                                          None), [])
        self.assertEqual(judge_makes_ball(None, ks, fmt, fb, {'lo': [two], 'hi': [one]}, {'cw': [NaN, NaN], 'rw': [NaN]},
                                          None), [])
        lb = ks['ball_lower_as_1']
        self.assertEqual(judge_set_bound(lb, ks, fmt, lb.ensures[0], {'c': [two], 'r': [one]}, {'l': [one]}, None), [])
        self.assertEqual(judge_set_bound(lb, ks, fmt, lb.ensures[0], {'c': [NaN], 'r': [NaN]}, {'l': [PINF]}, None), [])
        self.assertEqual(judge_set_bound(lb, ks, fmt, lb.ensures[0], {'c': [two], 'r': [one]}, {'l': [make(F(7, 8))]},
                                         None), ['set_bound (rounded)'])
        # Stage B1: the hull and the intersection, the midpoint and radius, a ball from an interval, an
        # interval from a ball, the split, the zero of a product of intervals, mul_ext_2_2.
        hull, inter = ks['interval_hull_1'], ks['interval_intersection_1']
        xy = {'xl': [one], 'xu': [two], 'yl': [make(F(3))], 'yu': [make(F(4))]}
        self.assertEqual(judge_interval_set(hull, ks, fmt, hull.ensures[0], xy, {'zl': [one], 'zu': [make(F(4))]}, None), [])
        self.assertEqual(judge_interval_set(hull, ks, fmt, hull.ensures[0], xy, {'zl': [one], 'zu': [two]}, None),
                         ['interval_set (bounds)'])
        self.assertEqual(judge_interval_set(inter, ks, fmt, inter.ensures[0], xy, {'zl': [PINF], 'zu': [NINF]}, None), [])
        self.assertEqual(judge_interval_set(inter, ks, fmt, inter.ensures[0], dict(xy, yl=[two]),
                                            {'zl': [PINF], 'zu': [NINF]}, None), ['interval_set (empty)'])
        self.assertEqual(judge_interval_set(inter, ks, fmt, inter.ensures[0], dict(xy, yl=[two]),
                                            {'zl': [two], 'zu': [two]}, None), [])
        empty_x = dict(xy, xl=[PINF], xu=[NINF])
        self.assertEqual(judge_interval_set(hull, ks, fmt, hull.ensures[0], empty_x,
                                            {'zl': [make(F(3))], 'zu': [make(F(4))]}, None), [])
        mr, tb = ks['interval_mid_rad_1'], ks['interval_to_ball_1']
        half = {'xl': [NINF], 'xu': [one]}
        self.assertEqual(judge_ball_of_interval(mr, ks, fmt, mr.ensures[0], half, {'m': [make(-fmt.top)], 'r': [PINF]},
                                                None), [])
        self.assertEqual(judge_ball_of_interval(tb, ks, fmt, tb.ensures[0], half, {'c': [ZERO], 'r': [PINF]}, None), [])
        self.assertEqual(judge_ball_of_interval(tb, ks, fmt, tb.ensures[0], half, {'c': [make(-fmt.top)], 'r': [PINF]},
                                                None), ['ball_of_interval (line expected)'])
        onetwo = {'xl': [one], 'xu': [two]}
        self.assertEqual(judge_ball_of_interval(mr, ks, fmt, mr.ensures[0], onetwo, {'m': [make(F(3, 2))],
                                                                                    'r': [make(F(1, 2))]}, None), [])
        self.assertEqual(judge_ball_of_interval(mr, ks, fmt, mr.ensures[0], onetwo, {'m': [make(F(3, 2))], 'r': [one]},
                                                None), ['ball_of_interval (smallest radius)'])
        bt = ks['ball_to_interval_1']
        self.assertEqual(judge_interval_of_ball(bt, ks, fmt, bt.ensures[0], {'c': [two], 'r': [one]},
                                                {'zl': [one], 'zu': [make(F(3))]}, None), [])
        self.assertEqual(judge_interval_of_ball(bt, ks, fmt, bt.ensures[0], {'c': [two], 'r': [one]},
                                                {'zl': [ZERO], 'zu': [make(F(3))]}, None), ['interval_of_ball (rounded)'])
        self.assertEqual(judge_interval_of_ball(bt, ks, fmt, bt.ensures[0], {'c': [ZERO], 'r': [PINF]},
                                                {'zl': [NINF], 'zu': [PINF]}, None), [])
        sp = ks['interval_split_1']
        self.assertEqual(judge_splits(sp, ks, fmt, sp.ensures[0], onetwo, {'al': [one], 'au': [make(F(3, 2))],
                                                                         'bl': [make(F(3, 2))], 'bu': [two]}, None), [])
        self.assertEqual(judge_splits(sp, ks, fmt, sp.ensures[0], onetwo, {'al': [one], 'au': [make(F(3, 2))],
                                                                         'bl': [make(F(7, 4))], 'bu': [two]}, None),
                         ['splits (cover)'])
        im2 = ks['interval_mul_2']
        zero2 = {'xl': [ZERO, ZERO], 'xu': [ZERO, ZERO], 'yl': [one, ZERO], 'yu': [PINF, ZERO]}
        self.assertEqual(judge_interval(im2, ks, fmt, im2.ensures[0], zero2, {'zl': [ZERO, ZERO], 'zu': [ZERO, ZERO]},
                                        None), [])
        self.assertIn('I6 (zero factor)', judge_interval(im2, ks, fmt, im2.ensures[0], zero2,
                                                         {'zl': [make(F(-1, 8)), ZERO], 'zu': [ZERO, ZERO]}, None))
        me = ks['mul_ext_2_2']
        ext = {'x': [two, ZERO], 'y': [NINF, ZERO]}
        self.assertEqual(judge_no_fix_up(me, ks, fmt, me.ensures[2], ext, {'l': [NINF, ZERO], 'h': [NINF, ZERO]}, None), [])
        self.assertEqual(judge_no_fix_up(me, ks, fmt, me.ensures[2], ext, {'l': [PINF, ZERO], 'h': [NINF, ZERO]}, None),
                         ['outward (non-finite operand)'])
        ext = {'x': [ZERO, ZERO], 'y': [NINF, ZERO]}
        self.assertEqual(judge_no_fix_up(me, ks, fmt, me.ensures[3], ext, {'l': [ZERO, ZERO], 'h': [ZERO, ZERO]}, None), [])
        ext = {'x': [two, ZERO], 'y': [two, ZERO]}
        self.assertEqual(judge_no_fix_up(me, ks, fmt, me.ensures[2], ext, {'l': [make(F(5)), ZERO], 'h': [PINF, ZERO]},
                                         None), ['outward (side)'])
        self.assertEqual(judge_no_fix_up(me, ks, fmt, me.ensures[3], ext, {'l': [NINF, ZERO], 'h': [PINF, ZERO]}, None), [])
        mk2 = ks['interval_make_2']
        self.assertEqual(judge_makes_interval(mk2, ks, fmt, mk2.ensures[0], {'lo': [NaN, NaN], 'hi': [one, ZERO]},
                                              {'zl': [NINF, ZERO], 'zu': [PINF, ZERO]}, None), [])
        self.assertEqual(judge_makes_interval(mk2, ks, fmt, mk2.ensures[0], {'lo': [two, ZERO], 'hi': [one, ZERO]},
                                              {'zl': [NINF, ZERO], 'zu': [PINF, ZERO]}, None), ['makes_interval'])
        rep = ks['make_2'].ensures[0]
        self.assertEqual(judge_represents(ks['make_2'], ks, fmt, rep, {'a': [NINF]}, {'x': [NINF, ZERO]}, None), [])
        self.assertEqual(judge_represents(ks['make_2'], ks, fmt, rep, {'a': [NINF]}, {'x': [NINF, NaN]}, None),
                         ['represents (canonical)'])
        self.assertEqual(fmt.ieee_round(F(15), 'nearest'), PINF)           # 15 is a tie between 14 and 16
        self.assertEqual(fmt.ieee_round(F(29, 2), 'down'), make(F(14)))
        self.assertEqual(fmt.ieee_round(F(-29, 2), 'down'), NINF)
        self.assertTrue(fmt.canonical([PINF, NZERO]) and fmt.canonical([NaN, NaN]))
        self.assertFalse(fmt.canonical([PINF, one]) or fmt.canonical([one, NaN]) or fmt.canonical([one, one]))


if __name__ == '__main__':
    unittest.main()
