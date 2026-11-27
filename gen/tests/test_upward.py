"""The round-up interval in the generator (docs/developer/design/upward.md, "Tests and CI", the
generator's suite): its 24 kernel descriptions, the rules U1 to U7 and P1 to P5, the interpreter's
operations rounded upward and both machine forms of max_nl, the claims, the Rocq printer, and every
kernel on every pair of canonical states of small formats. The kernels it tests require the
rounding mode upward set by kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and
Clang -frounding-math, MSVC /fp:strict); this file runs the generator and its interpreter, which need
neither.

The exhaustive runs (Exhaustive) judge each result by a reading of the claims of its own, in exact
arithmetic, below, on every canonical state (and every value of a number) of formats of the
statements (architecture.md, "Number formats"): three of precision 1 and 2 in the quick suite, four
of precision 2 and 3 with --full (some 20 minutes of four processes), two of precision 4 when
$KAIRN_GEN_UPWARD_PRECISION is 4 (some 10^8 pairs a kernel: a run on the Linux machine, not CI).
The same lines go to the oracle's command line (`kairn-oracle check`), the gate of the design page:
in pieces (oracle_jobs, oracle_piece), each a range of the first operand's cases judged by a process
of the oracle of its own, side by side, on the quick formats in the quick suite and those of
precision 3 with --full; precision 4 is a run of tests/brute/upward.py, which keeps every piece's
summary, resumes, and merges them (docs/developer/testing.md, "The round-up interval").
"""
import hashlib
import itertools
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import unittest
from bisect import bisect_left, bisect_right
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction

import common
from kairn_gen import build, claims, expr, interp, ir, objcode, rules, upward

NAMES = sorted(f'upward_{n}_1' for n in (
    'add', 'sub', 'neg', 'mul', 'add_num', 'mul_num', 'hull', 'intersection', 'make', 'from_interval',
    'to_interval', 'empty', 'entire', 'contains', 'subset', 'positive', 'negative', 'zero', 'less',
    'less_equal', 'equal', 'rel_equal', 'rel_interior', 'rel_disjoint'))
PAGE = os.path.join(common.ROOT, 'docs', 'developer', 'design', 'upward.md')
INF, NUM, NAN = interp.INF, interp.NUM, interp.NAN
NaN = interp.NaN


def family():
    return common.kernels().upward


# ---------------------------------------------------------------------------------------------
# The descriptions

def page_listings():
    """{kernel: [(dsts, op, args, lane)]} of the listings of the design page, as its code blocks
    write them: a pair line is two statements with ` | ` between them, the rest of a line is a
    comment; the predicates are statements separated by `;`, and `upward_less_equal_1` is "the same
    with" the statements it gives."""
    text = open(PAGE, encoding='utf-8').read()
    statement = re.compile(r'([a-z][a-z0-9]*)\s*=\s*([a-z_]+)\(([^()]*)\)')
    out, current, same = {}, None, {}
    for block in re.findall(r'```[a-z]*\n(.*?)```', text, re.S):
        for line in block.split('\n'):
            head = re.match(r'(upward_[a-z_]+_1)\b', line)
            if head:
                current = head.group(1)
                out[current] = []
                line = line[head.end():]
                if 'the same with' in line:
                    same[current] = line
                    continue
            elif not line.startswith(' ') or current is None:
                continue
            found = list(statement.finditer(line))
            pair = len(found) == 2 and '|' in line[found[0].end():found[1].start()]
            for lane, m in enumerate(found):
                args = tuple(a.strip() for a in m.group(3).split(','))
                out[current].append(((m.group(1),), m.group(2), args, lane if pair else None))
    for name, line in same.items():
        base = name.replace('_equal_1', '_1')      # upward_less_equal_1 is upward_less_1 with ...
        changed = {m.group(1): m for m in statement.finditer(line)}
        out[name] = [((d[0],), changed[d[0]].group(2), tuple(a.strip() for a in changed[d[0]].group(3).split(',')),
                      lane) if d[0] in changed else (d, op, args, lane) for d, op, args, lane in out[base]]
    return out


class Descriptions(unittest.TestCase):
    def test_the_family(self):
        ks = common.kernels()
        self.assertEqual(sorted(ks.upward), NAMES)
        self.assertFalse(set(ks) & set(NAMES), 'the family is kept apart from the other kernels')
        for name, k in ks.upward.items():
            self.assertTrue(k.upward and k.ieee_only and k.extended and k.entry, name)
            self.assertEqual((k.status, k.ieee_status, k.min_precision), ('unverified', 'unverified', 1), name)
            self.assertTrue(k.source and k.license and k.cone_exempt, name)
            self.assertIsNone(k.value, name)
        # The pairs: every state is the two lanes of one register.
        self.assertEqual(ks.upward['upward_mul_1'].pair_inputs, {'x': ('xu', 'xn'), 'y': ('yu', 'yn')})
        self.assertEqual(ks.upward['upward_mul_1'].pair_outputs, {'z': ('zu', 'zn')})
        self.assertEqual(ks.upward['upward_mul_1'].input_limbs, ['xu', 'xn', 'yu', 'yn'])
        self.assertEqual(ks.upward['upward_to_interval_1'].pair_outputs, {})
        self.assertEqual(ks.upward['upward_make_1'].pair_inputs, {})

    def test_the_mark(self):
        # Every description says in its first paragraph that it requires the mode upward and the
        # options (the design page, "The marks").
        for name in NAMES:
            with open(os.path.join(common.GEN, 'kernels', f'{name}.kernel'), encoding='utf-8') as f:
                lines = f.read().split('\n')
            first = []
            for line in lines:
                if not line.startswith('#') or line.strip() == '#':
                    break
                first.append(line[1:].strip())
            self.assertIn(upward.MARK, ' '.join(first), name)

    def test_the_listings_are_the_pages(self):
        # Each description holds the listing of the page, statement for statement, its pair lines
        # included; and the statements of each pair line are its two lanes, lane 0 first.
        page = page_listings()
        self.assertEqual(sorted(page), NAMES)
        for name, k in family().items():
            own = [(st.dsts, st.op, tuple(str(a) for a in st.args), st.lane) for st in k.body]
            self.assertEqual(own, page[name], name)
            for s0, s1 in k.pair_lines():
                self.assertEqual((s0.lane, s1.lane, s0.line), (0, 1, s1.line), name)


# ---------------------------------------------------------------------------------------------
# The refusals

HEAD = '''kernel:        toy_up
rounding:      upward
input:         pair stored x = xu xn
input:         pair stored y = yu yn
output:        pair z = zu zn
requires:      upward xu xn
requires:      upward yu yn
ensures:       encloses_interval zu zn x+y x=xu,xn y=yu,yn tight=rounded bounded_when=abs_le(x+y,omega) bounded_exactly
min_precision: 1
status:        unverified
domain:        extended
ieee_only:     yes
ieee_status:   unverified
entry:         yes
cone_exempt:   each lane a bound of its own
'''
SUM = 'zu = add_ru(xu, yu) | zn = add_ru(xn, yn)\n'
DEFAULT = '''kernel:        toy_default
input:         a
input:         b
output:        s
value:         a+b
ensures:       rounded s nearest
status:        unverified
'''


def refusals(*texts):
    """The refusals of the kernels given as descriptions, as strings; the family's apart by their
    `rounding: upward`, as load_kernels sets them."""
    ks = [ir.parse_kernel(t, f'{i}.kernel') for i, t in enumerate(texts)]
    every = ir.KernelSet({k.name: k for k in ks if not k.upward}, upward={k.name: k for k in ks if k.upward})
    return [str(e) for e in rules.check_all(every)]


class Refusals(unittest.TestCase):
    def refused(self, rule, value, *texts):
        errs = refusals(*texts)
        self.assertTrue(any(f'value {value}: {rule}' in e for e in errs), f'{rule} of {value} not in {errs}')
        return errs

    def test_the_accepted_forms(self):
        self.assertEqual(refusals(HEAD + SUM), [])
        # neg | copy, a sign change of one lane; a constant register; a make of two scalars; a
        # broadcast of a lane and of a scalar mask; a swapped pair.
        body = ('a = neg(xu) | b = copy(xn)\n'
                'm = lt(xu, yu)\n'
                'c = select(m, a, 0) | d = select(m, b, const inf)\n'
                'e = add_ru(c, yu) | f = add_ru(d, yu)\n'
                'g = add_ru(f, yu) | h = add_ru(e, yn)\n'
                'zu = copy(g) | zn = copy(h)\n')
        self.assertEqual(refusals(HEAD + body), [])

    def test_u1(self):
        self.refused(rules.RULE_U1, 'zu', HEAD + 'zu = add(xu, yu) | zn = add(xn, yn)\n')
        self.refused(rules.RULE_U1, 'up(2)', HEAD + 'su = add_ru(xu, const up(2)) | sn = add_ru(xn, const up(2))\n'
                     'zu = add_ru(su, yu) | zn = add_ru(sn, yn)\n')
        self.refused(rules.RULE_U1, 'su', HEAD + 'su = succ(xu) | sn = succ(xn)\nzu = add_ru(su, yu) | zn = add_ru(sn, yn)\n')
        self.refused(rules.RULE_U1, '-', HEAD.replace('ieee_only:     yes\n', '') + SUM)
        self.refused(rules.RULE_U1, '-', HEAD + 'ce_variant:    toy_up\n' + SUM)
        # Nothing outside the family uses what is its own: the operations, a call of a kernel of
        # the family, a pair, a pair line, the vocabulary of its claims.
        self.refused(rules.RULE_U1, 's', DEFAULT + 's = add_ru(a, b)\n')
        self.refused(rules.RULE_U1, 'r', DEFAULT + '(r, q) = toy_up(a, b, a, b)\ns = add(r, q)\n', HEAD + SUM)
        self.refused(rules.RULE_U1, 'p', DEFAULT.replace('input:         a\n', 'input:         pair p = a c\n')
                     + 's = add(a, b)\n')
        self.refused(rules.RULE_U1, 's', DEFAULT + 's = add(a, b) | t = add(b, a)\n')
        self.refused(rules.RULE_U1, '-', DEFAULT + 'requires:      upward a b\ns = add(a, b)\n')
        # A kernel of the family calls only kernels of the family.
        self.refused(rules.RULE_U1, 'r', DEFAULT + 's = add(a, b)\n',
                     HEAD + 'r = toy_default(xu, yu)\nzu = add_ru(r, yu) | zn = add_ru(xn, yn)\n')
        # No fold runs one.
        fd = ir.Fold(name='toy_fold', path='-', step=('toy_up', ('s', 'x'), ('s',)))
        ks = ir.KernelSet(upward={'toy_up': ir.parse_kernel(HEAD + SUM, '-')})
        self.assertIn(rules.RULE_U1, str(rules.fold_outside_family(fd, ks)[0]))

    def test_u2_p1(self):
        self.refused(rules.RULE_P1, 'zu', HEAD + 'zu = add_ru(xu, yu) | zn = mul_ru(xn, yn)\n')
        self.refused(rules.RULE_P1, 'a', HEAD + 'a = neg(xu) | b = abs(xn)\nzu = add_ru(a, yu) | zn = add_ru(b, yn)\n')
        self.refused(rules.RULE_P1, 'su', 'kernel:        toy_callee\n' + HEAD.split('\n', 1)[1] + SUM,
                     HEAD + '(su, sn) = toy_callee(xu, xn, yu, yn) | (a, b) = toy_callee(xu, xn, yu, yn)\n'
                     'zu = add_ru(su, a) | zn = add_ru(sn, b)\n')

    def test_u2_p2(self):
        self.refused(rules.RULE_P2, 'zu', HEAD + 'zu = add_ru(xu, yu) | zn = add_ru(yn, xn)\n')
        self.refused(rules.RULE_P2, 'zu', HEAD + 'zu = add_ru(xu, yn) | zn = add_ru(yu, xn)\n')

    def test_u2_p3(self):
        self.refused(rules.RULE_P3, 'x', HEAD.replace('pair stored x = xu xn', 'pair stored x = xu') +
                     'zu = add_ru(xu, yu) | zn = add_ru(xu, yn)\n')
        self.refused(rules.RULE_P3, 'z', HEAD.replace('pair z = zu zn', 'pair z = zu zn zw') + SUM + 'zw = copy(xu)\n')
        self.refused(rules.RULE_P3, 'zu', HEAD.replace('pair z = zu zn', 'pair zu = zv zn').replace(
            'encloses_interval zu zn', 'encloses_interval zv zn') + 'zu = copy(xu)\nzv = add_ru(zu, yu) | zn = add_ru(xn, yn)\n')

    def test_u2_p4(self):
        # A scalar beside a lane of a pair, in either lane.
        text = HEAD.replace('input:         pair stored y = yu yn\n', 'input:         pair stored y = yu yn\ninput:         t\n')
        self.refused(rules.RULE_P4, 'zu', text + 'unused:        xu not read\nzu = add_ru(t, yu) | zn = add_ru(xn, yn)\n')
        self.refused(rules.RULE_P4, 'zu', text + 'unused:        yn not read\nzu = add_ru(xu, yu) | zn = add_ru(xn, t)\n')

    def test_u2_p5(self):
        self.refused(rules.RULE_P5, 'zu', HEAD + 'm = lt(xu, yu)\nn = lt(xn, yn)\n'
                     'zu = select(m, xu, yu) | zn = select(n, xn, yn)\n')

    def test_u3(self):
        self.refused(rules.RULE_U3, 'nu', HEAD + 'su = add_ru(xu, yu) | sn = add_ru(xn, yn)\n'
                     'nu = neg(sn) | nn = neg(su)\nzu = copy(nu) | zn = copy(nn)\n')
        # through select, copy and max_nl
        self.refused(rules.RULE_U3, 'b', HEAD + 'p = mul_ru(xu, yu) | q = mul_ru(xn, yn)\n'
                     'm = lt(xu, yu)\na = select(m, p, xu)\nc = copy(a)\nd = max_nl(q, c)\nb = neg(d)\n'
                     'zu = add_ru(b, xu) | zn = add_ru(b, xn)\n')

    def test_u4(self):
        self.refused(rules.RULE_U4, 'g', HEAD + 'g = guard(xu)\nzu = add_ru(g, yu) | zn = add_ru(xn, yn)\n')

    def test_u5(self):
        self.refused(rules.RULE_U5, 'zu', HEAD + 'su = add_ru(xu, yu) | sn = add_ru(xn, yn)\n'
                     'zu = max_nl(su, xu) | zn = max_nl(sn, xn)\n')
        text = HEAD.replace('input:         pair stored y = yu yn\n', 'input:         pair stored y = yu yn\ninput:         t\n')
        self.refused(rules.RULE_U5, 'a', text + 'a = max_nl(t, xu)\nzu = add_ru(a, yu) | zn = add_ru(xn, yn)\n')
        # a lane of a pair input and a result of mul_ru are accepted
        self.assertEqual(refusals(HEAD + 'p = mul_ru(xu, yu) | q = mul_ru(xn, yn)\n'
                                  'zu = max_nl(p, yu) | zn = max_nl(q, yn)\n'), [])
        self.assertEqual(refusals(HEAD + 'zu = max_nl(xu, yu) | zn = max_nl(xn, yn)\n'), [])

    def test_u6(self):
        self.refused(rules.RULE_U6, 'su', HEAD + 'su = add_ru(yu, yn) | sn = add_ru(yn, yu)\n'
                     'zu = add_ru(xu, su) | zn = add_ru(xn, sn)\n')
        text = ('kernel:        toy_up\nrounding:      upward\ninput:         a\ninput:         b\n'
                'output:        pair z = zu zn\nensures:       makes_interval zu zn from=a,b\nmin_precision: 1\n'
                'status:        unverified\ndomain:        extended\nieee_only:     yes\nieee_status:   unverified\n'
                'cone_exempt:   selected\n')
        self.refused(rules.RULE_U6, 'zu', text + 'zu = add_ru(a, b) | zn = add_ru(b, a)\n')

    def test_u7(self):
        self.refused(rules.RULE_U7, 'z', HEAD + 'zu = add_ru(xu, yu)\nzn = add_ru(xn, yn)\n')
        self.refused(rules.RULE_U7, 'z', HEAD + 'zn = add_ru(xu, yu) | zu = add_ru(xn, yn)\n')
        # Mask outputs that are the lanes of a pair line.
        text = HEAD.replace('output:        pair z = zu zn\n', 'output:        mask yes\noutput:        mask no\n').replace(
            'ensures:       encloses_interval zu zn x+y x=xu,xn y=yu,yn tight=rounded bounded_when=abs_le(x+y,omega) '
            'bounded_exactly', 'ensures:       trit yes no le x y x=xu,xn y=yu,yn exact')
        errs = self.refused(rules.RULE_U7, 'yes', text + 'yes = le(xu, yu) | no = le(xn, yn)\n')
        self.assertTrue(any(f'value no: {rules.RULE_U7}' in e for e in errs), errs)

    def test_names(self):
        self.refused(rules.WELL_FORMED, 'pinf', HEAD + 'pinf = copy(xu)\nzu = add_ru(pinf, yu) | zn = add_ru(xn, yn)\n')

    def test_claims(self):
        def claim(text):
            return any(rules.CLAIMS in e for e in refusals(text))
        self.assertTrue(claim(HEAD.replace('requires:      upward yu yn\n', '') + SUM))
        self.assertTrue(claim(HEAD.replace('requires:      upward yu yn', 'requires:      upward yn yu') + SUM))
        self.assertTrue(claim(HEAD.replace('tight=rounded', 'tight=rounded;steps=1') + SUM))
        self.assertTrue(claim(HEAD.replace('bounded_exactly', '') + SUM))
        self.assertTrue(claim(HEAD.replace('ensures:', 'value:         x+y\nensures:') + SUM))
        self.assertTrue(claim(HEAD.replace('x+y x=xu,xn y=yu,yn', 'x+y x=xu,xn y=yu,yn numbers=yu') + SUM))
        self.assertTrue(claim(HEAD.replace('x+y x=xu,xn', 'x*y+x x=xu,xn') + SUM))
        self.assertTrue(claim(HEAD.replace('ensures:', 'ensures:       interval_set zu zn union x=xu,xn y=yu,yn\nensures:')
                              + SUM))
        # a predicate that is not exact
        self.assertTrue(claim(HEAD.replace('ensures:       encloses_interval zu zn x+y x=xu,xn y=yu,yn tight=rounded '
                                           'bounded_when=abs_le(x+y,omega) bounded_exactly',
                                           'ensures:       certain m subset x y x=xu,xn y=yu,yn')
                              .replace('output:        pair z = zu zn', 'output:        mask m') +
                              'a = le(xu, yu)\nb = le(yn, xn)\nm = and(a, b)\n'))
        # same_set of two default intervals
        self.assertTrue(claim('kernel:        toy_up\nrounding:      upward\ninput:         stored xl\n'
                              'input:         stored xu\noutput:        zl\noutput:        zu\n'
                              'requires:      interval xl xu\nensures:       same_set zl zu from=xl,xu\n'
                              'min_precision: 1\nstatus:        unverified\ndomain:        extended\n'
                              'ieee_only:     yes\nieee_status:   unverified\ncone_exempt:   copies\n'
                              'zl = copy(xl)\nzu = copy(xu)\n'))

    def test_the_parser(self):
        for text in (HEAD.replace('rounding:      upward', 'rounding:      nearest'),
                     HEAD.replace('pair stored x = xu xn', 'pair mask x'),
                     HEAD + 'zu = add_ru(xu, yu) | zn = add_ru(xn, yn) | zw = add_ru(xn, yn)\n',
                     HEAD.replace('x=xu,xn y=yu,yn', 'x=xu,xn y=yu,yn numbers=a,a')):
            with self.assertRaises(ir.DescriptionError, msg=text[-80:]):
                ir.parse_kernel(text, 'toy.kernel')


# ---------------------------------------------------------------------------------------------
# The interpreter's operations

def values(f):
    """Every value of format f: NaN, the two infinities, the two zeros, every finite number."""
    mags = [(m, f.qmin) for m in range(1, 1 << (f.p - 1))]                   # the subnormal numbers
    mags += [(m, q) for q in range(f.qmin, f.qmax + 1) for m in range(1 << (f.p - 1), 1 << f.p)]
    out = [NaN, (INF, False), (INF, True), (NUM, False, 0, 0), (NUM, True, 0, 0)]
    out += [interp.canon(neg, m, q) for m, q in mags for neg in (False, True)]
    return out


def exact(v):
    """The extended real of a value: a Fraction, +-inf as floats; None for a NaN."""
    if v[0] == NAN:
        return None
    if v[0] == INF:
        return -math.inf if v[1] else math.inf
    r = Fraction(v[2]) * (Fraction(2) ** v[3])
    return -r if v[1] else r


class Format:
    """The finite numbers of a format, sorted, for the roundings of the readings below: by search, not
    by the interpreter's rnd_up."""

    def __init__(self, f):
        self.f = f
        fin = sorted({exact(v) for v in values(f) if v[0] == NUM})
        self.fin, self.omega = fin, fin[-1]

    def ru(self, r):
        """RU in the format with overflow: an infinity stays, above Omega +inf, below -Omega -Omega."""
        if r in (math.inf, -math.inf):
            return r
        if r > self.omega:
            return math.inf
        return self.fin[bisect_left(self.fin, r)]

    def rd(self, r):
        return -self.ru(-r)


FORMATS_SMALL = [interp.parse_format(f) for f in ('fp:1:0:1', 'fp:1:-1:2', 'fp:2:-2:1', 'fp:2:-3:2', 'fp:3:-4:1',
                                                   'fp:3:-1:-1', 'fp:2:-4:4')]


def _zero(v):
    return v[0] == NUM and v[2] == 0


class Operations(unittest.TestCase):
    def test_add_ru_and_mul_ru_on_every_pair(self):
        # Against the least number of the format not below the exact result, found by search, with
        # the overflow and the signs of zeros of the design page ("The operations of the IR").
        for f in FORMATS_SMALL:
            F = Format(f)
            vs = values(f)
            for a, b in itertools.product(vs, vs):
                xa, xb = exact(a), exact(b)
                for op, fn in (('add_ru', interp.add_ru), ('mul_ru', interp.mul_ru)):
                    got = fn(f, a, b)
                    if xa is None or xb is None:
                        want = None
                    elif op == 'add_ru':
                        want = None if {xa, xb} == {math.inf, -math.inf} else (
                            xa + xb if math.inf in (xa, xb) or -math.inf in (xa, xb) else F.ru(xa + xb))
                    else:
                        inf = abs(xa) == math.inf or abs(xb) == math.inf
                        want = None if inf and 0 in (xa, xb) else (
                            (math.inf if (xa > 0) == (xb > 0) else -math.inf) if inf else F.ru(xa * xb))
                    self.assertEqual(exact(got), want, f'{op} {f.name} {a} {b}: {got}')
                    if got[0] == NUM and got[2] == 0:
                        # The sign of a zero: an exact zero sum of operands of opposite signs is +0,
                        # x + x keeps the sign of a zero x; a product has the sign of the product of
                        # the signs; a negative result above -eta is -0.
                        if op == 'add_ru':
                            sign = a[1] and b[1] if _zero(a) and _zero(b) else (
                                False if xa + xb == 0 else xa + xb < 0)
                        else:
                            sign = (a[1] != b[1])
                        self.assertEqual(got[1], sign, f'{op} {f.name} {a} {b}: the sign of {got}')

    def test_the_machine_forms_of_max_nl(self):
        f = FORMATS_SMALL[3]
        vs = values(f)
        for a, b in itertools.product(vs, vs):
            sel, num = interp.max_sel(a, b), interp.max_num(a, b)
            # MAXPD a, b: a when a > b, otherwise b (so b on a NaN and on two zeros).
            self.assertEqual(sel, a if interp.lt(b, a) else b)
            # FMAXNM on quiet NaNs: the other operand for one NaN; +0 on two zeros of different
            # signs; otherwise the greater.
            if a[0] == NAN or b[0] == NAN:
                self.assertEqual(num, b if a[0] == NAN else a)
            elif _zero(a) and _zero(b):
                self.assertEqual(num, (NUM, a[1] and b[1], 0, 0))
            else:
                self.assertEqual(exact(num), max(exact(a), exact(b)))
            # max_nl_ok (IeeeUpwardOperations.v): for every b that is not a NaN, b when a is a NaN,
            # otherwise a or b, at least both.
            if b[0] == NAN:
                continue
            for m in (sel, num):
                if a[0] == NAN:
                    self.assertEqual(m, b)
                else:
                    self.assertIn(m, (a, b))
                    self.assertTrue(interp.le(a, m) and interp.le(b, m))

    def test_the_line_protocol(self):
        # The command line names the machine form of max_nl: they differ on the sign of a zero.
        line = 'upward_hull_1 binary64 -0x0p+0 -0x0p+0 0x0p+0 0x0p+0\n'
        out = {}
        for form in ('sel', 'nm', None):
            args = [sys.executable, os.path.join(common.GEN, 'kairn-gen'), 'interp'] + (['--max', form] if form else [])
            r = subprocess.run(args, input=line, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            out[form] = r.stdout
        self.assertEqual(out['sel'], line[:-1] + ' -> -0x0p+0 -0x0p+0\n')
        self.assertEqual(out['nm'], line[:-1] + ' -> 0x0p+0 0x0p+0\n')
        self.assertEqual(out[None], out['sel'])
        line = 'upward_mul_1 binary64 0x1p+0 -0x1p+0 0x1.8p+0 -0x1p+0 #tag\n'
        r = subprocess.run([sys.executable, os.path.join(common.GEN, 'kairn-gen'), 'interp'], input=line,
                           capture_output=True, text=True)
        self.assertEqual(r.stdout, line[:-1] + ' -> 0x1.8p+0 -0x1p+0\n')    # [1, 1] * [1, 1.5]
        with self.assertRaises(interp.InterpError):
            interp.Machine(common.kernels(), max_form='fmax')
        with self.assertRaises(interp.InterpError):
            interp.Machine(common.kernels(), consteval=True).run('upward_neg_1', interp.parse_format('binary64'),
                                                                 [(NUM, False, 1, 0), (NUM, False, 1, 0)])


# ---------------------------------------------------------------------------------------------
# The claims

class Claims(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(claims.claims(common.kernels()))
        cls.by = {k['name']: k for k in cls.doc['kernels']}

    def test_the_entries(self):
        names = [k['name'] for k in self.doc['kernels']]
        # After every other kernel, in the family's order; only these say "rounding".
        self.assertEqual(names[-len(NAMES):], list(family()))
        self.assertEqual({k['name'] for k in self.doc['kernels'] if 'rounding' in k}, set(NAMES))
        keys = ['name', 'domain', 'ieee_only', 'rounding', 'inputs', 'outputs', 'requires', 'ensures',
                'min_precision', 'status', 'ieee_status', 'theorem', 'source', 'flops', 'instances']
        for name in NAMES:
            k = self.by[name]
            self.assertEqual(list(k), keys, name)
            self.assertEqual((k['domain'], k['ieee_only'], k['rounding']), ('extended', True, 'upward'), name)
            self.assertEqual(k['instances'], {'binary64': [], 'binary32': []}, name)
            for r in k['requires']:
                self.assertRegex(r, r'^(upward\(\w+, \w+\)|interval\(\w+, \w+\))$', name)
            self.assertEqual(len(k['ensures']), 1, name)

    def test_the_pages_samples(self):
        # The two entries the design page writes out ("Claims and the oracle"), on the keys it shows.
        text = open(PAGE, encoding='utf-8').read()
        block = re.search(r'```json\n(.*?)```', text, re.S).group(1)
        for sample in json.loads('[' + block + ']'):
            k = self.by[sample['name']]
            self.assertEqual({key: k[key] for key in sample}, sample, sample['name'])

    def test_the_vocabulary(self):
        e = self.by['upward_add_num_1']['ensures'][0]
        self.assertEqual(list(e), ['kind', 'upper', 'nlower', 'set', 'intervals', 'numbers', 'tight', 'bounded_when',
                                   'bounded_exactly'])
        self.assertEqual((e['numbers'], e['intervals']), (['t'], {'x': {'upper': 'xu', 'nlower': 'xn'}}))
        self.assertEqual(self.by['upward_make_1']['ensures'][0], {
            'kind': 'makes_interval', 'upper': 'zu', 'nlower': 'zn', 'from': {'lower': 'lo', 'upper': 'hi'}})
        self.assertEqual(self.by['upward_from_interval_1']['ensures'][0], {
            'kind': 'same_set', 'of': {'upper': 'zu', 'nlower': 'zn'}, 'from': {'lower': 'xl', 'upper': 'xu'}})
        self.assertEqual(self.by['upward_hull_1']['ensures'][0]['intervals']['y'], {'upper': 'yu', 'nlower': 'yn'})
        self.assertEqual(self.by['upward_less_1']['ensures'][0], {
            'kind': 'trit', 'yes': 'yes', 'no': 'no', 'rel': 'lt', 'args': ['x', 'y'],
            'intervals': {'x': {'upper': 'xu', 'nlower': 'xn'}, 'y': {'upper': 'yu', 'nlower': 'yn'}}, 'exact': True})
        self.assertEqual(self.by['upward_mul_1']['flops'], 8)


# ---------------------------------------------------------------------------------------------
# The Rocq printer, and the files of the other kernels

# The generated files of the other kernels, which the family leaves as they are; gen/claims.json and
# gen/objcode.json are that too, but for the family's entries after the others (test_the_family_
# changes_no_other_file).
UNTOUCHED = ('proofs/gen/Model.v', 'proofs/gen/Statements.v', 'proofs/gen/Audit.v', 'proofs/gen/FoldModel.v',
             'proofs/gen/FoldStatements.v', 'proofs/gen/IeeeModel.v', 'proofs/gen/IeeeStatements.v',
             'proofs/gen/IeeeAudit.v', 'proofs/gen/IeeeFoldModel.v', 'proofs/gen/IeeeFoldStatements.v',
             'proofs/gen/IeeeWith.v', 'include/kairn/gen/prelude.hpp', 'include/kairn/gen/scalar.hpp',
             'include/kairn/gen/avx2.hpp', 'include/kairn/gen/neon.hpp', 'include/kairn/gen/bounds.hpp',
             'include/kairn/gen/selftest.hpp', 'gen/constant_names.json', 'gen/tests/runner_kernels.inc',
             'tests/emulated/gen/kernels.hpp')
# Their SHA-256 when the family was added (and of gen/claims.json and gen/objcode.json without the
# family's entries). A change of the other kernels changes them, and the pins with it; a change of the
# family never does.
PINNED = {
    'proofs/gen/Model.v': 'ba9387f5dddf7286b534e79bdace65db14e81b7c73029f1d4c951060668ab43b',
    'proofs/gen/Statements.v': 'a7b30e41e8c83632303ec5ef808e54ba574b2df381aaf819559ae7ee458fbeb7',
    'proofs/gen/Audit.v': 'c9dc64fc88b4a6b20f4d297f8afd2dc1af4cf94882e1fb066658c98d586b5711',
    'proofs/gen/FoldModel.v': '303faa96059445dea23411f979865cc8bc6dd1cbb90981c68a7fa7f2a60dd604',
    'proofs/gen/FoldStatements.v': '7699e2797ba7aceb81d17a9496b1fb23702b156da221786f97bd129caea9f9bd',
    'proofs/gen/IeeeModel.v': 'c98b89e3d6c4e1895ebc7e7f4f393225e89bf369318d5fdb277fc05c54cd905b',
    'proofs/gen/IeeeStatements.v': 'cc71c4dca419259c698563bebecc8f21fb19f308b63e7fa91387d1b7006137b1',
    'proofs/gen/IeeeAudit.v': 'ee3be9e529287b14e913cef96ebe5b99e4bb5e48d20768a715db005a63fb2fc6',
    'proofs/gen/IeeeFoldModel.v': 'bab1887fd78ec64fdf1ef85acc144a11ece8a91bc3c8b62d64911aaf5cc00283',
    'proofs/gen/IeeeFoldStatements.v': '577bfe8abc47910f8649aabd935164868b762e01bfcc7ca9ef2e97751bed74cf',
    'proofs/gen/IeeeWith.v': '303e9b76ecafa1f7539caf2c09b3be056c815832141f85bc991040923cc45a94',
    'include/kairn/gen/prelude.hpp': '504d94b4e76e890c900f6fdbefb0145092019427d579b7a0390ab72f2faa898a',
    'include/kairn/gen/scalar.hpp': 'e37338fc0a004f22d9277a69a32f4de40a8726bc50ff3aa86cd15dcd433ef6a5',
    'include/kairn/gen/avx2.hpp': 'ec7d448a330a97471c131f2e2ad08cb04a7d8adabfbeb11ca8767c9565cd590f',
    'include/kairn/gen/neon.hpp': '4599efe35b83126f90bdabf44ba0470e29ad8137f4c1cc3fd44a79b4e51291ae',
    'include/kairn/gen/bounds.hpp': '60ab920b08d7429995e49536f2e10815240d4406c265bd587d94aa463848cfe2',
    'include/kairn/gen/selftest.hpp': 'e0a5521ee88554edd94d0c32bf5a4b07d9c612e4f4d3f2944402dbd3b9528934',
    'gen/constant_names.json': 'efd30cf8abc69db7eb52348c97327ad84faeb797d6bbca1373348de6b95a3c9d',
    'gen/objcode.json': '043413fff07254e8c5e5eb009dc1f789b9940dd566485817dfee42f01b4566dc',
    'gen/tests/runner_kernels.inc': 'bdaf366f090f35950e1784cfca057f0c5abf3727584d6f264f0854669c8abc6f',
    'tests/emulated/gen/kernels.hpp': 'fdfde702b5cef701a3b754cf310c8bb47dccb4cc8d97c5c2e722baa1426a81d0',
    'gen/claims.json': '77ee0d2213538ff413c261ca767b1f769679622d70136fbbee4a658a3e220dc7',
}


def _sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _without_family(text):
    """gen/claims.json as it was before the family: its entries taken out, printed as claims.py prints."""
    doc = json.loads(text)
    doc['kernels'] = [k for k in doc['kernels'] if 'rounding' not in k]
    return json.dumps(doc, indent=2) + '\n'


class Files(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ks = common.kernels()
        cls.with_family = build.outputs(ks)
        cls.without = build.outputs(ir.KernelSet(ks, folds=ks.folds, upward={}))

    def test_the_family_changes_no_other_file(self):
        # The files that existed before the family, but for gen/claims.json and gen/objcode.json, are
        # the same with it and without it; claims.json gains the family's entries after the others,
        # objcode.json the family's section after the folds, and nothing else.
        self.assertEqual(sorted(set(self.with_family) - set(self.without)), [])
        for rel in UNTOUCHED:
            self.assertEqual(self.with_family[rel], self.without[rel], rel)
        self.assertEqual(_without_family(self.with_family['gen/claims.json']), self.without['gen/claims.json'])
        self.assertEqual(objcode.without_family(self.with_family['gen/objcode.json']), self.without['gen/objcode.json'])
        self.assertNotEqual(self.with_family['gen/objcode.json'], self.without['gen/objcode.json'])
        self.assertNotEqual(self.with_family['proofs/gen/UpwardModel.v'], self.without['proofs/gen/UpwardModel.v'])

    def test_the_pinned_digests(self):
        got = {rel: _sha(self.with_family[rel]) for rel in UNTOUCHED}
        got['gen/claims.json'] = _sha(_without_family(self.with_family['gen/claims.json']))
        got['gen/objcode.json'] = _sha(objcode.without_family(self.with_family['gen/objcode.json']))
        self.assertEqual(got, PINNED)


def page_statement(name):
    text = open(PAGE, encoding='utf-8').read()
    m = re.search(rf'```coq\n(Definition {name} : Prop :=.*?)```', text, re.S)
    return m.group(1).strip()


class Rocq(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ks = common.kernels()
        cls.model, cls.statements, cls.audit = upward.model(ks), upward.statements(ks), upward.audit(ks)

    def test_the_sum_is_the_pages(self):
        # The page writes the statement of the sum out ("The statements"): the printer's, word for word.
        self.assertIn(page_statement('upward_add_1_spec'), self.statements)

    def test_the_binders_of_max_nl(self):
        # Every statement of a kernel that computes max_nl is about every max_nl with the property
        # max_nl_ok; no other statement names it.
        for name, k in family().items():
            spec = self.statements.split(f'Definition {name}_spec : Prop :=')[1].split('\n\n')[0]
            has = any(p.op == 'max_nl' for p in ir.prims(k, family()))
            self.assertEqual('(max_nl_ok_ : max_nl_ok prec emax max_nl)' in spec, has, name)
            self.assertEqual(has, name in ('upward_mul_1', 'upward_mul_num_1', 'upward_hull_1'), name)
        self.assertIn('(nan_mult : nan2 prec emax) (nan_opp : nan1 prec emax) (nan_const : '
                      '{x : binary_float prec emax | is_nan prec emax x = true})\n         (max_nl : binary_float prec '
                      'emax -> binary_float prec emax -> binary_float prec emax) (max_nl_ok_ : max_nl_ok prec emax '
                      'max_nl),', self.statements.split('Definition upward_mul_1_spec')[1])
        self.assertIn('UpwardModel.upward_mul_1 prec emax nan_mult nan_opp nan_const max_nl xu xn yu yn', self.statements)

    def test_a_pair_line_is_its_two_statements(self):
        body = self.model.split('Definition upward_sub_1 (xu xn yu yn : float) : float * float :=\n')[1]
        self.assertTrue(body.startswith('  let zu := add_ru xu yn in\n  let zn := add_ru xn yu in\n  (zu, zn).\n'))
        self.assertEqual(self.model.count('\nDefinition upward_'), len(NAMES))
        self.assertEqual(self.statements.count('\nDefinition upward_'), len(NAMES))
        for name in ('Axiom', 'Parameter', 'Admitted', 'admit'):
            for text in (self.model, self.statements, self.audit):
                self.assertNotIn(name, text)

    def test_the_audit(self):
        self.assertIn('(* No statement of the round-up interval has a theorem yet. *)', self.audit)
        ks = common.kernels()
        k = ir.parse_kernel(open(os.path.join(common.GEN, 'kernels', 'upward_neg_1.kernel'), encoding='utf-8').read()
                            .replace('status:        unverified', 'status:        proved')
                            .replace('ieee_status:   unverified', 'ieee_status:   proved\n'
                                     'ieee_theorem:  proofs/theories/IeeeUpward.v upward_neg_1_correct'), '-')
        text = upward.audit(ir.KernelSet(upward=dict(ks.upward, upward_neg_1=k)))
        self.assertIn('From Kairn Require Import IeeeUpward.\n', text)
        self.assertIn('Definition upward_neg_1_audit : upward_neg_1_spec := upward_neg_1_correct.\n'
                      'Print Assumptions upward_neg_1_correct.', text)
        self.assertEqual(rules.theorem(k, ks.upward), [])


# ---------------------------------------------------------------------------------------------
# Every kernel on every pair of canonical states, judged by the claims

def formats(*pairs):
    """The formats of the statements (qmax >= 1, qmin = 3 - qmax - 2p) of these (p, qmax)."""
    return [f'fp:{p}:{3 - qmax - 2 * p}:{qmax}' for p, qmax in pairs]


def states(f):
    """Every canonical state of f, (u, n): the empty set (NaN, NaN), and every pair of values neither a
    NaN nor -inf with -n <= u."""
    ok = [v for v in values(f) if v[0] != NAN and v != (INF, True)]
    return [(NaN, NaN)] + [(u, n) for u in ok for n in ok if interp.le(interp.neg(n), u)]


def default_intervals(f):
    """Every canonical default interval of one limb: the empty set (+inf, -inf), and [l, h] with l <= h,
    l < +inf, h > -inf."""
    vs = [v for v in values(f) if v[0] != NAN]
    return [((INF, False), (INF, True))] + [(l, h) for l in vs for h in vs if interp.le(l, h) and
                                             l != (INF, False) and h != (INF, True)]


EMPTY = 'empty'


def meaning(u, n):
    """A state as a set: EMPTY, or its bounds (lower, upper) as extended reals."""
    if u[0] == NAN:
        return EMPTY
    return (-exact(n), exact(u))


def canonical(u, n):
    return (u[0] == NAN and n[0] == NAN) or (u[0] != NAN and n[0] != NAN and u != (INF, True) and n != (INF, True)
                                             and -exact(n) <= exact(u))


def _times(a, b):
    return 0 if a == 0 or b == 0 else a * b


def range_of(tree, env):
    """The bounds of the exact range of a set expression over sets of real numbers [lo, hi], an
    infinite bound meaning unbounded; a product's from its four corners, 0 times infinity being 0."""
    if tree[0] == 'name':
        return env[tree[1]]
    if tree[0] == 'neg':
        lo, hi = range_of(tree[1], env)
        return (-hi, -lo)
    (a, b), (c, d) = range_of(tree[1], env), range_of(tree[2], env)
    if tree[0] == 'add':
        return (a + c, b + d)
    if tree[0] == 'sub':
        return (a - d, b - c)
    if tree[0] == 'mul':
        corners = [_times(x, y) for x in (a, b) for y in (c, d)]
        return (min(corners), max(corners))
    raise AssertionError(tree)


def holds(e, sets, ins):
    """The relation of a certain or trit entry on the meanings: (yes, no), no None for certain."""
    rel, args = e['rel'], e['args']

    def ne(x):
        return sets[x] is not EMPTY
    if rel == 'empty':
        return sets[args[0]] is EMPTY, None
    if rel == 'entire':
        return sets[args[0]] == (-math.inf, math.inf), None
    if rel == 'member':
        t, s = exact(ins[args[0]]), sets[args[1]]
        return (t is not None and abs(t) != math.inf and ne(args[1]) and s[0] <= t <= s[1]), None
    if rel in ('lt', 'le', 'eq'):
        bounds = {a: ((0, 0) if a == ir.ZERO else sets[a]) for a in args}
        if any(b is EMPTY for b in bounds.values()):
            return False, False
        (a, b), (c, d) = bounds[args[0]], bounds[args[1]]
        if rel == 'lt':
            return b < c, a >= d
        if rel == 'le':
            return b <= c, a > d
        return a == b == c == d, b < c or d < a
    x, y = sets[args[0]], sets[args[1]]
    if rel == 'subset':
        return x is EMPTY or (y is not EMPTY and y[0] <= x[0] and x[1] <= y[1]), None
    if rel == 'equal':
        return x == y, None
    if rel == 'interior':
        return x is EMPTY or (y is not EMPTY and (y[0] < x[0] or y[0] == x[0] == -math.inf) and
                              (x[1] < y[1] or x[1] == y[1] == math.inf)), None
    if rel == 'disjoint':
        return x is EMPTY or y is EMPTY or x[1] < y[0] or y[1] < x[0], None
    raise AssertionError(rel)


_TREES = {}


def _tree(text):
    """The parsed set expression of a claim, parsed once."""
    if text not in _TREES:
        _TREES[text] = expr.parse(text)
    return _TREES[text]


def judge(k, e, F, ins, outs):
    """What is wrong with one completed case against the claim e of kernel k, in exact arithmetic, or
    None: I1 to I5 of encloses_interval; interval_set; makes_interval on any two values; same_set;
    certain and trit. The signs of zeros are never judged."""
    kind = e['kind']
    if kind in ('encloses_interval', 'interval_set', 'makes_interval'):
        zu, zn = outs[e['upper']], outs[e['nlower']]
        if not canonical(zu, zn):
            return 'I1: the result is not canonical'
        z = meaning(zu, zn)
    sets = {x: meaning(ins[b['upper']], ins[b['nlower']]) for x, b in e.get('intervals', {}).items()}
    if kind == 'encloses_interval':
        empty = any(s is EMPTY for s in sets.values())
        if (z is EMPTY) != empty:
            return 'I2: empty exactly when an operand is'
        if empty:
            return None
        env = dict(sets)
        for t in e.get('numbers', []):
            v = exact(ins[t])
            env[t] = (v, v) if v is not None and abs(v) != math.inf else (-math.inf, math.inf)
        lo, hi = range_of(_tree(e['set']), env)
        want = (lo, hi) if e['tight']['kind'] == 'exact' else (F.rd(lo), F.ru(hi))
        if z != want:
            return f'I3/I4: the result {z}, the tightest interval of the format around [{lo}, {hi}] is {want}'
        bounded = all(abs(s[0]) != math.inf and abs(s[1]) != math.inf for s in sets.values()) and \
            all(ins[t][0] == NUM for t in e.get('numbers', []))
        if bounded and e.get('bounded_exactly'):
            if (abs(z[0]) != math.inf and abs(z[1]) != math.inf) != (abs(lo) <= F.omega and abs(hi) <= F.omega):
                return 'I5: bounded exactly when the range is within Omega'
        return None
    if kind == 'interval_set':
        x, y = sets.values()
        if e['set'] == 'union':
            want = y if x is EMPTY else x if y is EMPTY else (min(x[0], y[0]), max(x[1], y[1]))
        elif x is EMPTY or y is EMPTY or max(x[0], y[0]) > min(x[1], y[1]):
            want = EMPTY
        else:
            want = (max(x[0], y[0]), min(x[1], y[1]))
        return None if z == want else f'{e["set"]}: {z}, want {want}'
    if kind == 'makes_interval':
        lo, hi = exact(ins[e['from']['lower']]), exact(ins[e['from']['upper']])
        if lo is None or hi is None or (lo == hi and abs(lo) == math.inf):
            if (zu, zn) != ((INF, False), (INF, False)):
                return f'makes_interval: the whole line (+inf, +inf) for {lo}, {hi}'
            return None
        if hi < lo:
            return None if z is EMPTY else f'makes_interval: the empty set for {lo} > {hi}'
        want = (lo, hi)
        return None if z == want else f'makes_interval: {z}, want {want}'
    if kind == 'same_set':
        def side(names, where):
            if 'nlower' in names:
                u, n = where[names['upper']], where[names['nlower']]
                return canonical(u, n), meaning(u, n)
            l, h = where[names['lower']], where[names['upper']]
            if l == (INF, False) and h == (INF, True):
                return True, EMPTY
            ok = l[0] != NAN and h[0] != NAN and interp.le(l, h) and l != (INF, False) and h != (INF, True)
            return ok, (exact(l), exact(h))
        ok, got = side(e['of'], outs)
        _, src = side(e['from'], ins)
        if not ok:
            return 'same_set: the result is not canonical'
        return None if got == src else f'same_set: {got}, want {src}'
    yes, no = holds(e, sets, ins)
    if kind == 'certain':
        return None if outs[e['of']] == yes else f'certain {e["rel"]}: {outs[e["of"]]}, want {yes}'
    if (outs[e['yes']], outs[e['no']]) != (yes, no):
        return f'trit {e["rel"]}: {outs[e["yes"]]}, {outs[e["no"]]}, want {yes}, {no}'
    return None


def inputs(k, f):
    """The operands of k on f: for each pair input every canonical state, for a default interval every
    canonical one, for any other one-limb input every value; as (lists of first-group values, the
    product of the rest), so that the work splits on the first."""
    groups = []
    taken = set()
    for name, lanes in k.pair_inputs.items():
        groups.append((lanes, states(f)))
        taken |= set(lanes)
    for r in k.requires:
        if r[0] == 'interval':
            groups.append(((r[1], r[2]), default_intervals(f)))
            taken |= {r[1], r[2]}
    for v in k.input_limbs:
        if v not in taken:
            groups.append(((v,), [(x,) for x in values(f)]))
    return groups


def _run(job):
    """One part of an exhaustive run: kernel, format, form of max_nl, the indices of the first group's
    cases. Returns (cases, [failures, at most 5])."""
    name, fmt, form, lo, hi = job
    ks = common.kernels()
    k = ks.upward[name]
    f = interp.parse_format(fmt)
    F = Format(f)
    m = interp.Machine(ks, max_form=form)
    groups = inputs(k, f)
    e = k.ensures[0]
    count, failures = 0, []
    for first in groups[0][1][lo:hi]:
        for rest in itertools.product(*(g[1] for g in groups[1:])):
            given = {}
            for (names, _), vals in zip(groups, (first,) + rest):
                given.update(zip(names, vals))
            args = [given[v] for v in k.input_limbs]
            out = m.run(name, f, args)
            count += 1
            why = judge(k, e, F, given, dict(zip(k.output_limbs, out)))
            if why and len(failures) < 5:
                failures.append(f'{name} {fmt} --max {form}: ' +
                                ' '.join(interp.format_limb(a) for a in args) + ' -> ' +
                                ' '.join(interp.format_mask(v) if isinstance(v, bool) else interp.format_limb(v)
                                         for v in out) + f': {why}')
    return count, failures


_pool = None


def exhaustive(names, fmts, forms=('sel', 'nm')):
    """Every kernel of `names` on every case of each format, in each form of max_nl that it computes
    (one for a kernel without one): {(kernel, format, form): (cases, failures)}."""
    global _pool
    ks = common.kernels()
    jobs = []
    for name in names:
        k = ks.upward[name]
        has_max = any(p.op == 'max_nl' for p in ir.prims(k, ks.upward))
        for fmt in fmts:
            n = len(inputs(k, interp.parse_format(fmt))[0][1])
            step = max(1, n // (4 * common.JOBS))
            for form in (forms if has_max else forms[:1]):
                jobs += [(name, fmt, form, i, min(n, i + step)) for i in range(0, n, step)]
    if _pool is None:
        _pool = ProcessPoolExecutor(max_workers=common.JOBS)
    out = {}
    for job, (count, failures) in zip(jobs, _pool.map(_run, jobs)):
        key = job[:3]
        c, fs = out.get(key, (0, []))
        out[key] = (c + count, fs + failures)
    return out


# The formats of the runs: some 70 000 cases of a kernel of two states in the quick suite, 11 million
# with --full, 370 million at precision 4 (36, 78 and 253 canonical states; 465, 741, 1 711 and 2 775;
# 10 731 and 15 931).
QUICK = formats((1, 1), (1, 2), (2, 1))
FULL = formats((2, 2), (2, 3), (3, 1), (3, 2))
FOUR = formats((4, 1), (4, 2))


# ---------------------------------------------------------------------------------------------
# The same cases judged by the oracle, in pieces

ORACLE = os.path.join(common.ROOT, 'oracle', 'kairn-oracle')
# The oracle's check of a piece: a non-finite result of small operands fails, as in the cross-checks,
# and so does an invalid case (a line outside upward() or interval(): a fault of this enumeration).
CHECK = ['check', '--fail-on-suspicious', '--expect-valid']
# Lines per piece: some 40 to 100 seconds of one interpreter and one oracle on the test machines.
PIECE = 2_000_000


def max_forms(name, forms=('sel', 'nm')):
    """The forms of max_nl a kernel is run in: both when it computes a max_nl, otherwise the first."""
    ks = common.kernels()
    return forms if any(p.op == 'max_nl' for p in ir.prims(ks.upward[name], ks.upward)) else forms[:1]


def cases_of(name, fmt):
    """(the first operand's cases, the cases of the others together) of a kernel on a format."""
    groups = inputs(common.kernels().upward[name], interp.parse_format(fmt))
    return len(groups[0][1]), math.prod(len(g[1]) for g in groups[1:])


def oracle_jobs(names, fmts, piece=PIECE):
    """The pieces of the oracle's judgment of the kernels on every case of the formats, in each form
    of max_nl that each computes, format by format: (kernel, format, form, lo, hi, lines), the cases
    whose first operand is one of the first group's lo to hi (inputs()), about `piece` lines each."""
    jobs = []
    for fmt in fmts:
        for name in names:
            first, rest = cases_of(name, fmt)
            step = max(1, piece // rest)
            for form in max_forms(name):
                jobs += [(name, fmt, form, lo, min(first, lo + step), (min(first, lo + step) - lo) * rest)
                         for lo in range(0, first, step)]
    return jobs


def oracle_lines(job):
    """The interpreter's completed lines of a piece, in order, as `kairn-gen interp --max FORM`
    writes them for the request lines of its cases (without a tag)."""
    name, fmt, form, lo, hi = job[:5]
    ks = common.kernels()
    k = ks.upward[name]
    f = interp.parse_format(fmt)
    m = interp.Machine(ks, max_form=form)
    groups = inputs(k, f)
    text = {}

    def limb(v):
        if v not in text:
            text[v] = interp.format_limb(v)
        return text[v]
    head = f'{name} {fmt} '
    kinds = k.output_kinds
    for first in groups[0][1][lo:hi]:
        for rest in itertools.product(*(g[1] for g in groups[1:])):
            given = {}
            for (names, _), vals in zip(groups, (first,) + rest):
                given.update(zip(names, vals))
            args = [given[v] for v in k.input_limbs]
            out = m.run(name, f, args)
            yield head + ' '.join(limb(a) for a in args) + ' -> ' + ' '.join(
                interp.format_mask(v) if kind == ir.MASK else limb(v) for v, kind in zip(out, kinds))


def _die_with_parent():
    import ctypes
    import signal
    ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGKILL)       # PR_SET_PDEATHSIG


def oracle_piece(job, summary=None):
    """One piece judged by the oracle's command line, in a process of its own (and its summary
    written to `summary`, if given): (lines, the oracle's exit status, its report)."""
    cmd = [sys.executable, ORACLE] + CHECK + (['--json', summary] if summary else [])
    kw = {'preexec_fn': _die_with_parent} if sys.platform.startswith('linux') else {}
    n, buf = 0, []
    with tempfile.TemporaryFile() as out:
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=out, stderr=subprocess.STDOUT, **kw)
        try:
            for line in oracle_lines(job):
                buf.append(line)
                n += 1
                if len(buf) == 4096:
                    p.stdin.write(('\n'.join(buf) + '\n').encode('ascii'))
                    buf.clear()
            if buf:
                p.stdin.write(('\n'.join(buf) + '\n').encode('ascii'))
            p.stdin.close()
        except BrokenPipeError:
            pass
        status = p.wait()
        out.seek(0)
        report = out.read().decode('ascii', 'replace')
    return n, status, report


_oracle_pool = None


def oracle_run(names, fmts):
    """Every piece of the kernels on the formats, side by side (two busy processes a piece):
    {(kernel, format, form): lines}, and the reports of the pieces the oracle failed."""
    global _oracle_pool
    if _oracle_pool is None:
        _oracle_pool = ProcessPoolExecutor(max_workers=max(1, common.JOBS // 2))
    jobs = oracle_jobs(names, fmts)
    lines, failed = {}, []
    for job, (n, status, report) in zip(jobs, _oracle_pool.map(oracle_piece, jobs)):
        lines[job[:3]] = lines.get(job[:3], 0) + n
        if status != 0 or n != job[5]:
            failed.append(f'{job[0]} {job[1]} --max {job[2]}, first operand {job[3]} to {job[4]}: {n} lines '
                          f'of {job[5]}, the oracle exits with {status}:\n{report[-3000:]}')
    return lines, failed


class Exhaustive(unittest.TestCase):
    def check(self, fmts):
        found = exhaustive(NAMES, fmts)
        failures = [f for _, fs in found.values() for f in fs]
        self.assertEqual(failures[:20], [], f'{len(failures)} failures')
        # every kernel, every format, and both forms for the kernels with a maximum
        self.assertEqual(len(found), len(fmts) * (len(NAMES) + 3))
        return found

    def test_quick_formats(self):
        self.check(QUICK)

    @unittest.skipUnless(common.FULL, 'the formats of precision 3: with --full')
    def test_formats_of_precision_3(self):
        self.check(FULL)

    @unittest.skipUnless(os.environ.get('KAIRN_GEN_UPWARD_PRECISION') == '4',
                         'the formats of precision 4: $KAIRN_GEN_UPWARD_PRECISION=4 (a run on the Linux machine)')
    def test_formats_of_precision_4(self):
        self.check(FOUR)

    def test_the_readings_catch_faults(self):
        # Each reading fails a wrong answer: a product one step wide, an empty result for nonempty
        # operands, one NaN lane, a lane -inf, crossed lanes, a lower bound read without its
        # negation, a number +inf treated as a point; the sign of a zero is not judged.
        ks = common.kernels()
        f = interp.parse_format('fp:3:-4:1')
        F = Format(f)
        one, two, half = (NUM, False, 1, 0), (NUM, False, 1, 1), (NUM, False, 1, -1)
        mone = (NUM, True, 1, 0)
        mul, add_num = ks.upward['upward_mul_1'], ks.upward['upward_add_num_1']

        def j(k, args, out):
            return judge(k, k.ensures[0], F, dict(zip(k.input_limbs, args)), dict(zip(k.output_limbs, out)))
        x = [one, mone]           # [1, 1]
        y = [(NUM, False, 3, -1), mone]   # [1, 1.5]
        self.assertIsNone(j(mul, x + y, [(NUM, False, 3, -1), mone]))
        self.assertIn('I3/I4', j(mul, x + y, [two, mone]))                       # one step wide
        self.assertIn('I2', j(mul, x + y, [NaN, NaN]))                          # empty
        self.assertIn('I1', j(mul, x + y, [NaN, mone]))                         # one NaN lane
        self.assertIn('I1', j(mul, x + y, [(INF, True), mone]))                  # a lane -inf
        self.assertIn('I1', j(mul, x + y, [half, (NUM, True, 1, 1)]))            # crossed
        self.assertIn('I3/I4', j(mul, x + y, [(NUM, False, 3, -1), one]))        # the lower bound not negated
        self.assertIn('I3/I4', j(add_num, x + [(INF, False)], [two, mone]))      # +inf as a point
        self.assertIsNone(j(add_num, x + [(INF, False)], [(INF, False), (INF, False)]))
        self.assertIsNone(j(mul, [(NUM, False, 0, 0), (NUM, False, 0, 0)] + y,
                            [(NUM, True, 0, 0), (NUM, True, 0, 0)]))              # [0, 0], zero signs

    def test_the_oracle(self):
        # The gate of the design page: the interpreter's lines on every case of the quick formats (and
        # of precision 3 with --full), in each form of max_nl a kernel computes, judged by the oracle's
        # command line, in pieces side by side; every case of every kernel, format and form, and the
        # pieces as `kairn-gen interp` completes the same requests.
        fmts = QUICK + (FULL if common.FULL else [])
        lines, failed = oracle_run(NAMES, fmts)
        self.assertEqual(failed[:3], [], f'{len(failed)} pieces failed')
        self.assertEqual(len(lines), len(fmts) * (len(NAMES) + 3))
        for (name, fmt, _), n in lines.items():
            first, rest = cases_of(name, fmt)
            self.assertEqual(n, first * rest, (name, fmt))
        job = next(j for j in oracle_jobs(['upward_mul_1'], ['fp:2:-2:1']) if j[2] == 'nm')
        done = list(oracle_lines(job))
        requests = '\n'.join(line.split(' -> ')[0] for line in done[::97]) + '\n'
        r = subprocess.run([sys.executable, os.path.join(common.GEN, 'kairn-gen'), 'interp', '--max', 'nm'],
                           input=requests, capture_output=True, text=True)
        self.assertEqual(r.stdout, '\n'.join(done[::97]) + '\n', r.stderr)


if __name__ == '__main__':
    unittest.main()
