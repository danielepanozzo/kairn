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
        infinity of that sign (architecture.md, "Number formats")."""
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
        """The finite values whose leading limb is in the top two binades."""
        return [v for v in self.finite if finite(v[0]) and abs(fr(v[0])) >= fmt.top / 4] or self.finite


def operands(k, fmt):
    req = {}
    for r in k.requires:
        req.setdefault(r[1], []).append(r)
    radii = {r[2]: r[1] for r in k.requires if r[0] == 'ball'}
    groups = {g.name: g for g in k.inputs}
    out = []
    nonneg_finite = [v for v in fmt.values if not v[1] or v[2] == 0]
    for g in k.inputs:
        if g.name in radii:
            continue
        kinds = {r[0] for r in req.get(g.name, [])}
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
            got = {e['center']: [fr(v) for v in outs[e['center']]], e['radius']: [fr(outs[e['radius']][0])]}
            if not ts.holds(e, k, fmt, exact, got):
                bad.append('B3 (containment)')
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


def judge_makes_ball(k, ks, fmt, e, ins, outs, values):
    center, radius = ins[e['from']['center']], ins[e['from']['radius']][0]
    oc, orad = outs[e['center']], outs[e['radius']][0]
    state = ball_state(fmt, oc, orad)
    if state is None:
        return ['makes_ball (canonical)']
    if radius[0] == NAN or radius == NINF or (finite(radius) and radius[1] and radius[2] != 0):
        want = 'empty'                  # a NaN or negative radius, -inf included
    elif not all(finite(v) for v in center) or radius == PINF:
        want = 'line'
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
        else:
            want = fmt.ieee_round(x, e['mode'])
            ok = t == want if not finite(want) else (finite(t) and fr(t) == fr(want))
        return [] if ok else ['rounded']
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


JUDGES = {'extends': judge_extends, 'encloses': judge_ball, 'represents': judge_represents,
          'makes_ball': judge_makes_ball}


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
                (' '.join(show(v) for v in values), ' '.join(interp.format_mask(v) if isinstance(v, bool)
                                                            else show(v) for v in got)))
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
        # (ball_neg_k among them).
        self.assertEqual(len(self.names), 39)

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
