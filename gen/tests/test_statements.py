"""The claims of every kernel, checked in exact arithmetic on the operands of small formats.

This is the first step of "When an operation is done" (architecture.md) for the statements the
generator prints: the interpreter is the runner, and the judge here shares nothing with it but the
expression parser. Rounding is Flocq's definition (round with Znearest, Zfloor, Zceil in FLT_exp)
written out over fractions, and neighbors are read from the sorted list of every number of the
format. The oracle is the independent judge of the same claims; this is the generator's own check
that the statements it prints are not false before anyone tries to prove them.

Two readings of a claim, because the formats here have a largest number and the statements do not:
- the statement's (the Rocq model): no operation overflows. The kernel runs in the same precision
  and underflow threshold with the exponent range widened far enough that nothing overflows. A
  statement also says that every output limb is a number of the format; that is judged here too.
- the claims file's (what the oracle checks): in the format itself, whenever output limb 0 is
  finite. The two agree when output limb 0 finite means that nothing overflowed. That is what
  the non-finite cone gives, except for values computed from output limb 0 (two_sum's error at
  an operand of magnitude Omega, the open point of milestone1.md) and for the kernels exempt
  from the cone (see KNOWN_OVERFLOW_CORNERS).

Judged: every kernel that has a real-model statement in the first reading, from its minimum
precision on (split and two_prod_dekker are not even defined at precision 1, where the splitter is
not a number of the format); the second wave in the second reading. A kernel of the extended domain
is judged here on finite operands, its requirement canonical read as normalized, as its real-model
statement reads it; what it does with non-finite operands, and the full kernels and constructors,
which have no real-model statement, are judged in test_nonfinite.py.
"""
import bisect
import itertools
import os
import random
import re
import unittest
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F

import common
from kairn_gen import consts, expr, interp, ir, rocq

# (p, qmin, qmax): every precision from 1, with subnormals and a top within a few binades.
FORMATS = [(1, -3, 3), (2, -4, 3), (3, -5, 4), (4, -6, 4), (5, -8, 5), (6, -8, 5)]
EXHAUSTIVE = common.size(20000, 300000)   # all operand combinations up to this many
SAMPLE = common.size(3000, 60000)         # otherwise a random sample of this many


def mag(x):
    """e with 2^(e-1) <= x < 2^e, for x > 0."""
    e = x.numerator.bit_length() - x.denominator.bit_length()
    while F(2) ** e <= x:
        e += 1
    while F(2) ** (e - 1) > x:
        e -= 1
    return e


def floor(x):
    return x.numerator // x.denominator


class Format:
    def __init__(self, p, qmin, qmax):
        self.p, self.qmin, self.qmax = p, qmin, qmax
        pos = sorted({F(m) * F(2) ** q for q in range(qmin, qmax + 1) for m in range(2 ** p)})
        self.top = pos[-1]
        self.line = sorted(set(pos) | {-x for x in pos})
        self.members = set(self.line)
        self.u, self.eta = F(1, 2 ** p), F(2) ** qmin
        self.name = f'fp:{p}:{qmin}:{qmax}'

    def round(self, x, mode):
        """Flocq's round radix2 (FLT_exp qmin p) with Znearest tie_even, Zfloor or Zceil, with no
        overflow: the format's exponent range is unbounded above here."""
        if x == 0:
            return F(0)
        q = F(2) ** max(mag(abs(x)) - self.p, self.qmin)
        s = x / q
        n = floor(s)
        if mode == 'up' and n != s:
            n += 1
        elif mode == 'nearest':
            d = s - n
            if d > F(1, 2) or (d == F(1, 2) and n % 2 == 1):
                n += 1
        return n * q

    def pred(self, x):
        """The largest number of the format below x, which is -top or above; below -top as if
        the exponent range went on, -2^(qmax + p)."""
        i = bisect.bisect_left(self.line, x)
        if i == 0:
            assert x == -self.top, (self.name, x)
            return x - F(2) ** self.qmax
        return self.line[i - 1]

    def succ(self, x):
        """The smallest number of the format above x, which is top or below; above top as if the
        exponent range went on, 2^(qmax + p)."""
        return -self.pred(-x)

    def directed(self, x, mode):
        """x rounded down or up in the format with overflow (milestone2.md, "Notation and
        vocabulary"): RD of a value above top is top, RU of one below -top is -top. (RD of one
        below -top is -infinity, which no finite output equals.) To nearest: round."""
        r = self.round(x, mode)
        if mode == 'down' and x > self.top:
            return self.top
        if mode == 'up' and x < -self.top:
            return -self.top
        return r


# ---------------------------------------------------------------------------------------------
# Operands that satisfy the requirements.

def signs(x):
    """A number as (negative, magnitude) operands: both of them for zero."""
    return [(False, F(0)), (True, F(0))] if x == 0 else [(x < 0, abs(x))]


class Space:
    """The operands of one input group that satisfy the requirements: tuples of (negative,
    magnitude), one per limb (a mask is (bool,)). Counted without being listed, so that a large
    space is sampled instead."""

    def __init__(self, fmt, g, want):
        self.fmt, self.g = fmt, g
        if g.kind == ir.MASK:
            self.kind, self.items = 'list', [(False,), (True,)]
        elif len(g.limbs) == 1:
            vals = [v for x in fmt.line for v in signs(x)]
            if 'nonneg' in want:
                vals = [v for v in vals if not v[0] or v[1] == 0]
            if 'count' in want:          # a number of terms or of additions: zero, or at least 1
                vals = [v for v in vals if v[1] == 0 or (not v[0] and v[1] >= 1)]
            if 'power_of_two' in want:   # a reduced fraction of two powers of two is one
                vals = [v for v in vals if not v[0] and v[1] > 0 and v[1].numerator & (v[1].numerator - 1) == 0
                        and v[1].denominator & (v[1].denominator - 1) == 0]
            for w in want:
                if w.startswith('at_most:'):
                    vals = [v for v in vals if signed(v) <= int(w[len('at_most:'):])]
            self.kind, self.items = 'list', [(v,) for v in vals]
        elif len(g.limbs) == 2 and want & {'normalized', 'canonical'}:
            # x1 lies within half a gap of x0 on either side: a range of the sorted numbers.
            self.kind, self.ranges = 'pairs', []
            line = fmt.line
            for i, x0 in enumerate(line):
                # Beyond the largest number, the next one is 2^(qmax + p): a gap of 2^qmax.
                up = line[i + 1] - x0 if i + 1 < len(line) else F(2) ** fmt.qmax
                down = x0 - line[i - 1] if i > 0 else F(2) ** fmt.qmax
                lo = bisect.bisect_left(fmt.line, -down / 2)
                hi = bisect.bisect_right(fmt.line, up / 2)
                self.ranges.append((x0, lo, hi))
        else:
            raise AssertionError(f'group {g.name}: {len(g.limbs)} limbs without normalized')

    def count(self):
        if self.kind == 'list':
            return len(self.items)
        return sum(hi - lo for _, lo, hi in self.ranges) * 2

    def _pairs(self, x0, x1):
        if self.fmt.round(x0 + x1, 'nearest') != x0:
            return []
        return [(a, b) for a in signs(x0) for b in signs(x1)]

    def all(self):
        if self.kind == 'list':
            return self.items
        return [p for x0, lo, hi in self.ranges for x1 in self.fmt.line[lo:hi] for p in self._pairs(x0, x1)]

    def sample(self, rng):
        if self.kind == 'list':
            return rng.choice(self.items)
        while True:
            x0, lo, hi = rng.choice(self.ranges)
            found = self._pairs(x0, self.fmt.line[rng.randrange(lo, hi)])
            if found:
                return rng.choice(found)


def cases(fmt, kernel, seed):
    """Operands that satisfy the requirements: the one-group ones by construction, abs_ge after."""
    req = {}
    for r in kernel.requires:
        if r[0] == 'format':    # format half: every format here contains 1/2 (qmin <= -1)
            assert r[1] == 'half' and fmt.qmin <= -1, (kernel.name, r)
            continue
        if r[0] == 'ball':      # in the real model: a normalized center and a nonnegative radius
            req.setdefault(r[1], set()).add('normalized')
            req.setdefault(r[2], set()).add('nonneg')
            continue
        if r[0] == 'at_most':   # at most a positive integer (g of conv_radius)
            req.setdefault(r[1], set()).add(f'at_most:{r[2]}')
            continue
        for n in r[1:]:
            req.setdefault(n, set()).add(r[0])
    spaces = [Space(fmt, g, req.get(g.name, set())) for g in kernel.inputs]
    position = {g.name: i for i, g in enumerate(kernel.inputs)}
    pairs = [(position[r[1]], position[r[2]]) for r in kernel.requires if r[0] == 'abs_ge']

    def ok(case):
        return all(abs(sum(map(signed, case[i]))) >= abs(sum(map(signed, case[j]))) for i, j in pairs)

    total = 1
    for s in spaces:
        total *= s.count()
    if total <= EXHAUSTIVE:
        return [c for c in itertools.product(*(s.all() for s in spaces)) if ok(c)]
    rng = random.Random(f'{seed}:{fmt.name}:{kernel.name}')
    out = []
    while len(out) < SAMPLE:
        c = tuple(s.sample(rng) for s in spaces)
        if ok(c):
            out.append(c)
    return out


def signed(v):
    return -v[1] if v[0] else v[1]


def value_of(v):
    """(negative, magnitude) as an interpreter value."""
    m = v[1]
    return interp.canon(v[0], m.numerator, 0) if m.denominator == 1 else \
        interp.canon(v[0], m.numerator, -(m.denominator.bit_length() - 1))


INF = 'inf'   # an output of +infinity; any other non-finite output is None


def exact(v):
    """An interpreter value as a Fraction, INF for +infinity, None for -infinity and NaN."""
    if v[0] == interp.INF and not v[1]:
        return INF
    if v[0] != interp.NUM:
        return None
    return (-1 if v[1] else 1) * F(v[2]) * F(2) ** v[3]


# ---------------------------------------------------------------------------------------------
# The judge: one function per kind of ensures entry. `ins` maps an input group to its exact value
# (a mask to a bool), `outs` an output group to its limbs as Fractions (None if not finite).

def interval(tree, env):
    """The exact range of an expression in which each name occurs once: env maps a name to (lo, hi)."""
    kind = tree[0]
    if kind == 'name':
        return env[tree[1]]
    if kind == 'neg':
        lo, hi = interval(tree[1], env)
        return -hi, -lo
    if kind == 'abs':
        lo, hi = interval(tree[1], env)
        return (F(0) if lo <= 0 <= hi else min(abs(lo), abs(hi))), max(abs(lo), abs(hi))
    (a, b), (c, d) = interval(tree[1], env), interval(tree[2], env)
    if kind == 'add':
        return a + c, b + d
    if kind == 'sub':
        return a - d, b - c
    if kind == 'mul':
        ps = [a * c, a * d, b * c, b * d]
        return min(ps), max(ps)
    raise AssertionError(kind)


def exact_conditions(e, fmt, ins, limbs, conditions=None):
    """Whether every condition of the entry's exact_when holds: EXPR = 0 or |EXPR| > K (>= K),
    EXPR over the inputs' values and limbs, K over u and eta; or EXPR = 0 (zero, Milestone 2)."""
    env = dict(ins, **limbs)
    for c in e['exact_when'] if conditions is None else conditions:
        if 'mask' in c:
            # mask(NAME): the mask input is true (the radius of the scaling of a BallVector).
            if env[c['mask']] is not True:
                return False
            continue
        if 'zero' in c:
            if expr.evaluate(expr.parse(c['zero']), env) != 0:
                return False
            continue
        kind = next(x for x in ('zero_or_abs_gt', 'zero_or_abs_ge') if x in c)
        x = expr.evaluate(expr.parse(c[kind]), env)
        bound = expr.evaluate(expr.parse(c['than']), {'u': fmt.u, 'eta': fmt.eta})
        if not (x == 0 or (abs(x) > bound if kind == 'zero_or_abs_gt' else abs(x) >= bound)):
            return False
    return True


def product_large(fmt, value):
    return value == 0 or abs(value) >= F(2) ** (2 * fmt.p - 1) * fmt.eta


def constant(text, k, fmt, ins, outs, kernels):
    """An expression of the claims of Milestone 2 (an upper entry's own value, the operands of
    holds): over the inputs, the one-limb outputs, u, eta, unit(K) and tiny(K)."""
    names = dict((n, v) for n, v in ins.items() if not isinstance(v, bool))
    names.update((n, v[0]) for n, v in outs.items() if len(v) == 1 and isinstance(v[0], F))
    return consts.evaluate(expr.parse(text), kernels, fmt.p, fmt.qmin, names)


def claim_constant(text, fmt):
    """A constant of a claim (rel and abs of outward, Milestone 2), evaluated here: u and eta of
    the format, unit(K) and tiny(K) from K's error claim, and each up(EXPR) rounded up by this
    module's own rounding."""
    ks = common.kernels()
    tree = expr.parse(text)
    env = {'u': fmt.u, 'eta': fmt.eta}
    for fn, name in expr.calls(tree):
        e = next(x for x in ks[name].ensures if x['kind'] == 'error')
        env[f'unit({name})'] = expr.evaluate(expr.parse(e['c']), {'u': fmt.u}) * fmt.u ** e['k']
        env[f'tiny({name})'] = expr.evaluate(expr.parse(e['t']), {}) * fmt.eta
    return expr.evaluate(tree, env, lambda x: fmt.round(x, 'up'))


def holds(e, k, fmt, ins, outs, limbs=None, kernels=None):
    """Whether the entry holds; `limbs` gives each input limb's value under expr.limb_key, for the
    conditions of exact_when; `kernels`, the constants unit(K) and tiny(K) of the claims of the
    bound kernels."""
    value = expr.evaluate(expr.parse(k.value), ins) if k.value is not None else None
    kind = e['kind']
    if kind == 'holds':
        # Under its mask: the relation between the two expressions, exactly.
        if not outs[e['if']][0]:
            return True
        a, b = (constant(x, k, fmt, ins, outs, kernels) for x in e['args'])
        return {'lt': a < b, 'le': a <= b, 'eq': a == b}[e['rel']]
    if kind == 'upper' and 'if' in e and not outs[e['if']][0]:
        return True
    if kind == 'upper' and 'unless' in e and ins[e['unless']]:
        return True          # unless: the bound holds when the mask input is false
    if kind == 'encloses':
        c, r = outs[e['center']], outs[e['radius']][0]
        if not all(isinstance(x, F) for x in c) or r is None:
            return False
        if r == INF:
            return True          # the whole line encloses everything
        env = {b: (ins[cr['center']] - ins[cr['radius']], ins[cr['center']] + ins[cr['radius']])
               for b, cr in e['balls'].items()}
        env.update({n: (v, v) for n, v in ins.items() if n not in env and not isinstance(v, bool)})
        lo, hi = interval(expr.parse(e['set']), env)
        if not (sum(c) - r <= lo and hi <= sum(c) + r):
            return False
        # Exact: the ball is the set, which contains it as well.
        return 'exact_when' not in e or not exact_conditions(e, fmt, ins, limbs) or \
            (sum(c) - r == lo and hi == sum(c) + r)
    out = outs[e['of']]
    if kind == 'predicate':
        a, b = (expr.evaluate(expr.parse(x), ins) for x in e['args'])
        return out[0] == {'lt': a < b, 'le': a <= b, 'eq': a == b}[e['rel']]
    if not all(isinstance(x, F) for x in out):
        return False
    if kind in ('normalized', 'represents'):
        # represents (neg_2, abs_2), read over finite values: normalized and exactly the value.
        return all(x in fmt.members for x in out) and \
            all(out[i] == fmt.round(out[i] + out[i + 1], 'nearest') for i in range(len(out) - 1)) and \
            (kind == 'normalized' or sum(out) == value)
    if kind == 'leading_rounded':
        return out[0] == fmt.round(value, 'nearest')
    if kind == 'rounded':
        if 'value' in e:              # a value of its own, over the inputs and their limbs
            value = expr.evaluate(expr.parse(e['value']), dict(ins, **(limbs or {})))
        if e.get('when') == 'product_large' and not product_large(fmt, value):
            return True
        return out[0] == fmt.directed(value, e['mode'])
    if kind == 'neighbor':
        return out[0] == (fmt.succ(value) if e['side'] == 'up' else fmt.pred(value))
    if kind == 'maximum':
        # The larger of two expressions of the inputs and their limbs (the folds of maxima).
        env = dict(ins, **(limbs or {}))
        return out[0] == max(expr.evaluate(expr.parse(x), env) for x in e['args'])
    if kind == 'bound':
        r, below = out[0], e['side'] == 'below'
        limit = fmt.directed(value, 'down' if below else 'up')
        for _ in range(e['steps']):
            limit = fmt.pred(limit) if below else fmt.succ(limit)
        return limit <= r <= value if below else value <= r <= limit
    if kind == 'upper':
        r = out[0]
        if 'value' in e:
            value = constant(e['value'], k, fmt, ins, outs, kernels)
        if not value <= r:
            return False
        if 'exact_when' in e and exact_conditions(e, fmt, ins, limbs or {}) and r != value:
            return False     # the value itself when the conditions hold, a mask input among them
        if 'gaps' not in e:
            return True
        gaps = expr.evaluate(expr.parse(e['gaps']), {})
        return r - value <= gaps * (r - fmt.pred(r))
    if kind == 'outward':
        # On its side of the value, within rel |value| + abs, and the value itself when the
        # conditions of exact_when hold (Milestone 2).
        z = sum(out)
        if not (z <= value if e['side'] == 'below' else value <= z):
            return False
        if 'exact_when' in e and exact_conditions(e, fmt, ins, limbs) and z != value:
            return False
        return abs(z - value) <= claim_constant(e['rel'], fmt) * abs(value) + claim_constant(e['abs'], fmt)
    if kind == 'error':
        if 'exact_when' in e and exact_conditions(e, fmt, ins, limbs) and sum(out) != value:
            return False
        if 'exact_flag' in e and outs[e['exact_flag']][0] != exact_conditions(e, fmt, ins, limbs):
            return False     # the mask output is true exactly when the conditions hold
        if e['when'] == 'product_large' and not product_large(fmt, value):
            return True
        c = expr.evaluate(expr.parse(e['c']), {'u': fmt.u}) * fmt.u ** e['k']
        t = expr.evaluate(expr.parse(e['t']), {}) * fmt.eta
        if e['form'] == 'R':
            rho = abs(value)
        elif e['form'] == 'A':
            rho = sum(abs(v) for v in ins.values() if not isinstance(v, bool))
        else:           # T: the magnitudes of the terms of the value (s+x*y: |s| + |x*y|)
            rho = sum(abs(expr.evaluate(t, ins)) for t in rocq.terms(expr.parse(k.value)))
        return abs(sum(out) - value) <= c * rho + t
    raise AssertionError(kind)


def judge(job):
    """The cases of one kernel on one format, in both readings: [(reading, case, entry, outputs)]."""
    directory, name, (p, qmin, qmax), seed = job
    ks = common.kernels(directory)
    k = ks[name]
    fmt = Format(p, qmin, qmax)
    # The same precision and underflow threshold, and room enough above that nothing overflows.
    wide = Format(p, qmin, 2 * abs(qmax) + 4 * p + 16)
    m = interp.Machine(ks)
    bad = []
    for case in cases(fmt, k, seed):
        values, ins, limbs = [], {}, {}
        for g, group in zip(k.inputs, case):
            values += [group[0]] if g.kind == ir.MASK else [value_of(v) for v in group]
            ins[g.name] = group[0] if g.kind == ir.MASK else sum(signed(v) for v in group)
            if g.kind != ir.MASK:
                limbs.update({expr.limb_key(g.name, i): signed(v) for i, v in enumerate(group)})
        for reading, judged in (('statement', wide), ('claims file', fmt)):
            f = interp.Format(judged.name, judged.p, judged.qmin, judged.qmax)
            try:
                got = m.run(name, f, values)
            except interp.InterpError as err:
                bad.append((reading, case, 'run', str(err)))
                continue
            it = iter(got)
            outs = {}
            for g in k.outputs:
                vals = [next(it) for _ in g.limbs]
                outs[g.name] = vals if g.kind == ir.MASK else [exact(v) for v in vals]
            first = outs[k.outputs[0].name][0]
            if k.outputs[0].kind == ir.LIMB and not isinstance(first, F):
                if reading == 'statement':
                    bad.append((reading, case, 'overflow', 'output limb 0 is not finite'))
                continue    # the claims hold whenever output limb 0 is finite
            # In the format itself an entry about an output group other than the first holds when
            # that group's leading limb is finite (architecture.md, "Claims of the interval
            # kernels"): the two bounds of mul_dir_2_2 and of mul_dir_1 overflow apart.
            failed = [e['kind'] for e in k.ensures
                      if not (reading == 'claims file' and e.get('of') not in (None, k.outputs[0].name)
                              and not isinstance(outs[e['of']][0], F))
                      and not holds(e, k, judged, ins, outs, limbs, ks)]
            # What a statement says of every output limb besides its claims, so that statements
            # compose (rocq.py, _output_formats): it is a number of the format.
            if reading == 'statement' and not all(x in judged.members for g in k.outputs if g.kind == ir.LIMB
                                                  for x in outs[g.name]):
                failed.insert(0, 'format')
            if failed:
                shown = [interp.format_mask(v) if isinstance(v, bool) else interp.format_limb(v) for v in got]
                bad += [(reading, case, kind, shown) for kind in failed]
    return name, fmt.name, bad


def run_all(directory, names, seed):
    jobs = []
    ks = common.kernels(directory)
    for name in names:
        for fmt in FORMATS:
            if ks[name].min_precision and fmt[0] < ks[name].min_precision:
                continue
            jobs.append((directory, name, fmt, seed))
    with ProcessPoolExecutor(max_workers=common.JOBS) as ex:
        return list(ex.map(judge, jobs))


def case_text(k, case):
    parts = []
    for g, group in zip(k.inputs, case):
        if g.kind == ir.MASK:
            parts.append(f'{g.name}={int(group[0])}')
        else:
            parts.append(f'{g.name}=({", ".join(interp.format_limb(value_of(v)) for v in group)})')
    return ' '.join(parts)


# The kernels exempt from the cone whose claims are false in the format itself although output
# limb 0 is finite, because an intermediate overflowed. There is none now. radd and rmul were such
# corners while they took operands of any sign: succ(-inf) is -top, a finite upper bound that
# exceeds the exact sum or product by far more than two gaps. They require nonnegative operands
# now, an overflow then gives +inf, and succ(+inf) is +inf. test_overflow_corners pins exactly
# this set, so that a change shows.
KNOWN_OVERFLOW_CORNERS = set()
FIRST_WAVE = {'two_sum', 'fast_two_sum', 'two_prod', 'split', 'two_prod_dekker', 'add_2_2', 'add_2_1',
              'mul_2_2', 'mul_2_1', 'add_fast_2_2'}
# two_sum_entry is two_sum on guarded operands and claims what two_sum claims, so it has the same
# corner: an operand of magnitude Omega gives a NaN error term with a finite sum (milestone2.md,
# "Building blocks on T", "Outside the domain"; milestone1.md, "The error-free transformations at
# the top of the range"). Judged in the first reading like every kernel; in the second, with two_sum.
TWO_SUM_CORNER = {'two_sum_entry'}


class Statements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = {name: k for name, k in common.kernels().items() if k.real_model}
        cls.results = run_all(None, list(cls.ks), 'statements')

    def failures(self, reading):
        out = {}
        for name, fmt, bad in self.results:
            for r, case, entry, got in bad:
                if r == reading:
                    out.setdefault(name, []).append((fmt, case_text(self.ks[name], case), entry, got))
        return out

    def test_the_statements_hold(self):
        """No operation overflows: what the Rocq statements say. The proved kernels of the first
        wave are judged too, as a check of the judge."""
        bad = self.failures('statement')
        self.assertEqual({n: v[:3] for n, v in bad.items()}, {})
        judged = {name for name, _, _ in self.results}
        self.assertEqual(judged, set(self.ks))

    def test_the_claims_hold_in_the_format(self):
        """In the format itself, whenever output limb 0 is finite: what the oracle checks."""
        bad = self.failures('claims file')
        unexpected = {n: v[:3] for n, v in bad.items() if n not in KNOWN_OVERFLOW_CORNERS | FIRST_WAVE | TWO_SUM_CORNER}
        self.assertEqual(unexpected, {})
        # two_sum_entry fails there only where two_sum does: an operand of magnitude Omega, a finite
        # sum and a NaN error term.
        for name in TWO_SUM_CORNER:
            for fmt, case, _, out in self.results_of(name):
                f = Format(*[int(x) for x in fmt.split(':')[1:]])
                operands = [abs(F(float.fromhex(x))) for x in re.findall(r'-?0x[0-9a-f.]+p[-+][0-9]+', case)]
                self.assertEqual((max(operands), out[1]), (f.top, 'nan'), (name, fmt, case, out))
                self.assertNotIn(out[0], ('inf', '-inf', 'nan'), (name, fmt, case, out))

    def results_of(self, name):
        return [(fmt, case_text(self.ks[name], case), entry, got) for n, fmt, bad in self.results if n == name
                for r, case, entry, got in bad if r == 'claims file']

    def test_overflow_corners(self):
        bad = self.failures('claims file')
        self.assertEqual(set(bad) & KNOWN_OVERFLOW_CORNERS, KNOWN_OVERFLOW_CORNERS)
        for name in KNOWN_OVERFLOW_CORNERS:
            for fmt, case, entry, got in bad[name]:
                self.assertEqual(entry, 'upper', (name, fmt, case, got))
                f = Format(*[int(x) for x in fmt.split(':')[1:]])
                self.assertEqual(interp.parse_limb(got[0]), value_of((True, f.top)), (name, fmt, case))

    def test_the_judge_rejects_wrong_results(self):
        # The judge itself: claims that must fail on chosen results.
        fmt = Format(3, -4, 3)      # in [1, 2): 1, 5/4, 3/2, 7/4; in [2, 4): 2, 5/2, 3, 7/2
        k = self.ks
        one, half, tiny = F(1), F(1, 2), F(1, 16)
        self.assertFalse(holds(k['to_up_2'].ensures[0], k['to_up_2'], fmt, {'x': one + tiny}, {'t': [one]}))
        self.assertTrue(holds(k['to_up_2'].ensures[0], k['to_up_2'], fmt, {'x': one + tiny}, {'t': [F(5, 4)]}))
        self.assertFalse(holds(k['to_down_2'].ensures[0], k['to_down_2'], fmt, {'x': one - tiny}, {'t': [one]}))
        self.assertTrue(holds(k['to_down_2'].ensures[0], k['to_down_2'], fmt, {'x': one - tiny}, {'t': [F(7, 8)]}))
        self.assertFalse(holds(k['lt_2_2'].ensures[0], k['lt_2_2'], fmt, {'x': one, 'y': one}, {'m': [True]}))
        upper = k['radd'].ensures[0]
        self.assertTrue(holds(upper, k['radd'], fmt, {'a': one, 'b': half}, {'r': [F(7, 4)]}))    # one gap
        self.assertTrue(holds(upper, k['radd'], fmt, {'a': one, 'b': F(3, 8)}, {'r': [F(7, 4)]}))  # 3/2 gaps
        self.assertFalse(holds(upper, k['radd'], fmt, {'a': one, 'b': half}, {'r': [F(5, 2)]}))   # two gaps
        self.assertFalse(holds(upper, k['radd'], fmt, {'a': one, 'b': half}, {'r': [F(5, 4)]}))   # below
        self.assertFalse(holds(upper, k['radd'], fmt, {'a': one, 'b': half}, {'r': [F(3)]}))      # three gaps
        enc = k['ball_add_1'].ensures[0]
        ins = {'cx': one, 'rx': tiny, 'cy': one, 'ry': F(0)}
        self.assertTrue(holds(enc, k['ball_add_1'], fmt, ins, {'cz': [F(2)], 'rz': [tiny]}))
        self.assertFalse(holds(enc, k['ball_add_1'], fmt, ins, {'cz': [F(2)], 'rz': [tiny / 2]}))
        self.assertFalse(holds(enc, k['ball_add_1'], fmt, ins, {'cz': [F(2)], 'rz': [None]}))
        mul = k['ball_mul_1'].ensures[0]
        ins = {'cx': -one, 'rx': half, 'cy': F(2), 'ry': half}   # x y over [-3/2, -1/2] x [3/2, 5/2]
        self.assertTrue(holds(mul, k['ball_mul_1'], fmt, ins, {'cz': [F(-2)], 'rz': [F(7, 4)]}))
        self.assertFalse(holds(mul, k['ball_mul_1'], fmt, ins, {'cz': [F(-2)], 'rz': [F(3, 2)]}))
        # The claims of Milestone 2: a neighbor, a bound one step wide, a rounding under a
        # condition (P = 2^(2p-1) eta = 2 here), and the exactness of a ball.
        nu = k['next_up'].ensures[0]
        self.assertTrue(holds(nu, k['next_up'], fmt, {'a': one}, {'r': [F(5, 4)]}))
        self.assertFalse(holds(nu, k['next_up'], fmt, {'a': one}, {'r': [F(3, 2)]}))
        self.assertTrue(holds(k['next_down'].ensures[0], k['next_down'], fmt, {'a': F(0)}, {'r': [-tiny]}))
        self.assertTrue(holds(k['next_down'].ensures[0], k['next_down'], fmt, {'a': one}, {'r': [F(7, 8)]}))
        md = k['mul_down_1']
        ab = {'a': F(5, 4), 'b': F(5, 4)}                         # 25/16: RD 3/2, and 5/4 before it
        self.assertTrue(holds(md.ensures[0], md, fmt, ab, {'r': [F(3, 2)]}))
        self.assertTrue(holds(md.ensures[0], md, fmt, ab, {'r': [F(5, 4)]}))
        self.assertFalse(holds(md.ensures[0], md, fmt, ab, {'r': [one]}))         # two steps
        self.assertFalse(holds(md.ensures[0], md, fmt, ab, {'r': [F(7, 4)]}))     # above
        self.assertTrue(holds(md.ensures[1], md, fmt, ab, {'r': [F(5, 4)]}))      # below P: no claim
        large = {'a': F(3, 2), 'b': F(3, 2)}                      # 9/4 >= P: exactly RD, 2
        self.assertTrue(holds(md.ensures[1], md, fmt, large, {'r': [F(2)]}))
        self.assertFalse(holds(md.ensures[1], md, fmt, large, {'r': [F(7, 4)]}))
        self.assertEqual(fmt.directed(F(100), 'down'), F(56))         # beyond the top, toward zero
        self.assertEqual(fmt.directed(F(-100), 'up'), F(-56))
        self.assertEqual(fmt.succ(F(56)), F(64))
        bm = k['ball_mul_pow2_1']
        enc = bm.ensures[0]
        ins = {'cx': one, 'rx': F(1, 4), 'c': F(2)}               # N = 1/4: both scalings are above it
        limbs = {'cx[0]': one, 'rx[0]': F(1, 4), 'c[0]': F(2)}
        self.assertTrue(holds(enc, bm, fmt, ins, {'cz': [F(2)], 'rz': [half]}, limbs))
        self.assertFalse(holds(enc, bm, fmt, ins, {'cz': [F(2)], 'rz': [F(3, 4)]}, limbs))  # encloses, not exact
        ins = {'cx': one, 'rx': tiny, 'c': F(2)}                  # rx c = 1/8 is below N: no exactness
        self.assertTrue(holds(enc, bm, fmt, ins, {'cz': [F(2)], 'rz': [half]}, dict(limbs, **{'rx[0]': tiny})))
        # outward (Milestone 2): on its side, within A |v| + B, and v itself when v is zero.
        ad = k['add_down_2_2']
        ow = next(e for e in ad.ensures if e['kind'] == 'outward')
        ins, limbs = {'x': one, 'y': half}, {'x[0]': one, 'x[1]': F(0), 'y[0]': half, 'y[1]': F(0)}
        self.assertTrue(holds(ow, ad, fmt, ins, {'l': [F(3, 2), F(0)]}, limbs))
        self.assertTrue(holds(ow, ad, fmt, ins, {'l': [F(5, 4), F(0)]}, limbs))        # within the bound
        self.assertFalse(holds(ow, ad, fmt, ins, {'l': [F(7, 4), F(0)]}, limbs))       # above
        self.assertFalse(holds(ow, ad, fmt, ins, {'l': [-F(56), F(0)]}, limbs))        # too far below
        zero = {'x': one, 'y': -one}
        zlimbs = {'x[0]': one, 'x[1]': F(0), 'y[0]': -one, 'y[1]': F(0)}
        self.assertTrue(holds(ow, ad, fmt, zero, {'l': [F(0), F(0)]}, zlimbs))
        self.assertFalse(holds(ow, ad, fmt, zero, {'l': [-tiny, F(0)]}, zlimbs))      # not zero
        self.assertGreater(claim_constant(ow['rel'], fmt), 0)
        self.assertEqual(fmt.round(F(9, 8), 'nearest'), one)          # ties to the even significand
        self.assertEqual(fmt.round(F(11, 8), 'nearest'), F(3, 2))
        self.assertEqual(fmt.round(-F(9, 8), 'nearest'), -one)
        self.assertEqual(fmt.round(F(17, 16), 'nearest'), one)
        self.assertEqual(fmt.round(-F(17, 16), 'down'), -F(5, 4))
        self.assertEqual(fmt.round(F(17, 16), 'up'), F(5, 4))
        self.assertEqual(fmt.round(F(1, 32), 'up'), F(1, 16))          # below eta
        self.assertEqual(fmt.round(F(1, 32), 'nearest'), 0)            # half of eta: a tie, to 0
        self.assertIn(F(7, 8), fmt.members)                            # what "a number of the format" is
        self.assertNotIn(F(9, 8), fmt.members)                         # four significant bits
        self.assertNotIn(F(1, 32), fmt.members)                        # below eta
        self.assertNotIn(INF, fmt.members)
        self.assertEqual(fmt.top, F(56))
        self.assertEqual(fmt.round(F(100), 'nearest'), F(96))          # no overflow beyond 56
        self.assertEqual(fmt.pred(one), F(7, 8))
        self.assertEqual(fmt.pred(F(0)), -F(1, 16))
        self.assertEqual(fmt.pred(-fmt.top), -F(64))
        self.assertEqual(Format(1, -3, 3).round(F(3, 2), 'nearest'), F(2))
        self.assertEqual(Format(1, -3, 3).round(F(3, 4), 'nearest'), one)


if __name__ == '__main__':
    unittest.main()
