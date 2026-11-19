"""The interpreter: against the host's arithmetic, against rounding by enumeration on toy
formats, and as a runner of the line protocol."""
import bisect
import itertools
import math
import os
import random
import struct
import subprocess
import sys
import unittest
from fractions import Fraction

import common
import hwfloat
from kairn_gen import consts, expr, interp, ir

KAIRN_GEN = os.path.join(common.GEN, 'kairn-gen')


class Limbs(unittest.TestCase):
    def test_round_trip_with_python(self):
        rng = random.Random(1)
        xs = [struct.unpack('<d', struct.pack('<Q', rng.getrandbits(64)))[0] for _ in range(20000)]
        xs += [struct.unpack('<d', struct.pack('<Q', rng.getrandbits(52) | (rng.getrandbits(1) << 63)))[0]
               for _ in range(5000)]                          # subnormals
        xs += common.edges('binary64') + common.edges('binary32')
        for x in xs:
            text = interp.format_limb(common.to_value(x))
            self.assertTrue(common.same(float.fromhex(text), x), (x, text))
            self.assertEqual(interp.parse_limb(text), common.to_value(x))

    def test_printf_and_python_spellings(self):
        for text, x in (('0x1p-1074', 5e-324), ('0x0.0000000000001p-1022', 5e-324), ('0x1.8p+1', 3.0),
                        ('0X1.8P1', 3.0), ('-0x0p+0', -0.0), ('0x0.0p+0', 0.0), ('0x.8p1', 1.0),
                        ('0x10p-4', 1.0), ('inf', math.inf), ('-inf', -math.inf)):
            self.assertTrue(common.same(common.to_float(interp.parse_limb(text)), x), text)
        self.assertEqual(interp.parse_limb('nan'), interp.NaN)
        f = interp.parse_format('binary64')
        self.assertFalse(interp.member(f, interp.parse_limb('0x1p-999999999999')))
        self.assertFalse(interp.member(f, interp.parse_limb('-0x1p+999999999999')))
        for bad in ('1.5', '0x1.8', '0xp+1', 'Infinity', '+inf', '-nan', '0x1p', '', '1e5', '0x1.8p+1 '):
            with self.assertRaises(interp.InterpError, msg=bad):
                interp.parse_limb(bad)

    def test_canonical_spelling(self):
        self.assertEqual(interp.format_limb(common.to_value(1.0)), '0x1p+0')
        self.assertEqual(interp.format_limb(common.to_value(-0.75)), '-0x1.8p-1')
        self.assertEqual(interp.format_limb(common.to_value(5e-324)), '0x1p-1074')
        self.assertEqual(interp.format_limb(common.to_value(-0.0)), '-0x0p+0')
        self.assertEqual(interp.format_limb(interp.canon(False, 2 ** 70 + 1, 2000)), '0x1.000000000000000004p+2070')


class Formats(unittest.TestCase):
    def test_names(self):
        for name, want in (('binary64', (53, -1074, 971)), ('binary32', (24, -149, 104)),
                           ('fp:5:-12:6', (5, -12, 6))):
            f = interp.parse_format(name)
            self.assertEqual((f.p, f.qmin, f.qmax), want)
        for bad in ('binary16', 'fp:0:-1:1', 'fp:3:2:1', 'fp:3:-1', 'fp:a:1:2'):
            with self.assertRaises(interp.InterpError, msg=bad):
                interp.parse_format(bad)

    def test_largest_and_smallest(self):
        f = interp.parse_format('binary64')
        self.assertTrue(common.same(common.to_float(interp.largest(f, False)), sys.float_info.max))
        f = interp.parse_format('binary32')
        self.assertEqual(common.to_float(interp.largest(f, True)), -struct.unpack('<f', b'\xff\xff\x7f\x7f')[0])

    def test_constants(self):
        # Veltkamp's multiplier, written out for the two hardware formats.
        self.assertEqual(ir.CONSTANTS['splitter'](53), 2 ** 27 + 1)
        self.assertEqual(ir.CONSTANTS['splitter'](24), 2 ** 12 + 1)
        self.assertEqual(ir.CONSTANTS['splitter'](5), 2 ** 3 + 1)

    def test_computed_constants(self):
        # Worked out by hand: for one rounding, unit = u/(1+u) gives unit/(1 - unit) = u exactly,
        # and tiny/(1 - unit) = (eta/2)(1 + u), which rounds up to eta; for mul_2_2, unit = 4u^2 =
        # 2^-104 gives 2^-104/(1 - 2^-104), just above 2^-104, and (3/2) eta/(1 - 2^-104) rounds
        # up to 2 eta; for add_2_2, tiny = 0.
        ks = common.kernels()
        F = Fraction
        for name, fmt, want in (('unit_computed(add_1_1)', (53, -1074, 971), F(1, 2 ** 53)),
                                ('unit_computed(add_1_1)', (24, -149, 104), F(1, 2 ** 24)),
                                ('unit_computed(add_1_1)', (5, -12, 6), F(1, 2 ** 5)),
                                ('tiny_computed(mul_1_1)', (53, -1074, 971), F(1, 2 ** 1074)),
                                ('tiny_computed(mul_1_1)', (3, -4, 3), F(1, 2 ** 4)),
                                ('unit_computed(mul_2_2)', (53, -1074, 971), F(2 ** 52 + 1, 2 ** 156)),
                                ('tiny_computed(mul_2_2)', (53, -1074, 971), F(2, 2 ** 1074)),
                                ('tiny_computed(mul_2_2)', (24, -149, 104), F(2, 2 ** 149)),
                                ('tiny_computed(add_2_2)', (53, -1074, 971), F(0)),
                                ('tiny_computed(mul_2_1)', (4, -6, 3), F(2, 2 ** 6)),
                                ('0', (5, -12, 6), F(0))):
            self.assertEqual(consts.value(name, ks, *fmt), want, (name, fmt))
        # In a format whose numbers are all multiples of 4, u rounds up to 4.
        self.assertEqual(consts.value('unit_computed(add_1_1)', ks, 3, 2, 4), 4)

    def test_computed_constants_are_rounded_up_values(self):
        # On every small format: the smallest number of the format not below the exact quotient.
        ks = common.kernels()
        for name in TOY:
            toy = Toy(name)
            f = toy.f
            for c in ('unit_computed(add_1_1)', 'unit_computed(mul_1_1)', 'tiny_computed(mul_1_1)',
                      'unit_computed(mul_2_1)', 'tiny_computed(mul_2_1)'):
                fn, k = ir.computed(c)
                e = consts.source_bound(ks[k])
                u = Fraction(1, 2 ** f.p)
                unit = expr.evaluate(expr.parse(e['c']), {'u': u}) * u ** e['k']
                tiny = expr.evaluate(expr.parse(e['t']), {}) * Fraction(2) ** f.qmin
                exact = (unit if fn == 'unit_computed' else tiny) / (1 - unit)
                if ks[k].min_precision and f.p < ks[k].min_precision:
                    with self.assertRaises(consts.ConstError):
                        consts.value(c, ks, f.p, f.qmin, f.qmax)
                    continue
                if not unit < 1:
                    continue
                above = [x for x in [Fraction(0)] + toy.pos[:-1] if x >= exact]
                if not above:
                    with self.assertRaises(consts.ConstError, msg=(name, c)):
                        consts.value(c, ks, f.p, f.qmin, f.qmax)
                    continue
                self.assertEqual(consts.value(c, ks, f.p, f.qmin, f.qmax), above[0], (name, c))

    def test_constants_below_the_minimum_precision(self):
        ks = common.kernels()
        with self.assertRaises(consts.ConstError):     # add_2_2's claims hold from precision 3
            consts.value('unit_computed(add_2_2)', ks, 2, -4, 4)
        m = interp.Machine(ks)
        x = interp.parse_limb('0x1p+0')
        with self.assertRaises(interp.InterpError):
            m.run('ball_add_2', interp.parse_format('fp:2:-4:4'), [x, interp.canon(False, 0, 0), x, x,
                                                                    interp.canon(False, 0, 0), x])


# ---------------------------------------------------------------------------------------------
# Rounding by enumeration: on a toy format, RN of an exact value is found by looking through
# every number of the format. Consecutive positive numbers alternate between even and odd
# significands (the binade boundaries go from 2^p - 1 to 2^(p-1)), so the even neighbor of a tie
# is the one at an even position. 2^(qmax + p) stands for overflow.

TOY = ('fp:2:-3:2', 'fp:3:-4:3', 'fp:4:-6:3', 'fp:5:-12:6', 'fp:3:2:4', 'fp:4:0:0')


class Toy:
    def __init__(self, name):
        self.f = interp.parse_format(name)
        p, qmin, qmax = self.f.p, self.f.qmin, self.f.qmax
        self.pos = sorted({Fraction(m) * Fraction(2) ** q for q in range(qmin, qmax + 1) for m in range(2 ** p)})
        self.pos.append(Fraction(2) ** (qmax + p))
        self.values = [(neg, x) for x in self.pos[:-1] for neg in (False, True)]

    def rn(self, t, neg_zero=False):
        """(neg, magnitude or 'inf') for an exact t; the sign of a zero given by the caller."""
        a = abs(t)
        if a == 0:
            return (neg_zero, Fraction(0))
        i = bisect.bisect_left(self.pos, a)
        if i == len(self.pos):
            return (t < 0, 'inf')
        if self.pos[i] != a:
            lo, hi = i - 1, i
            dl, dh = a - self.pos[lo], self.pos[hi] - a
            i = lo if dl < dh else hi if dh < dl else (lo if lo % 2 == 0 else hi)
        return (t < 0, 'inf' if i == len(self.pos) - 1 else self.pos[i])

    @staticmethod
    def value(v):
        """An interpreter value as (neg, magnitude or 'inf' or 'nan')."""
        if v[0] == interp.NAN:
            return (False, 'nan')
        if v[0] == interp.INF:
            return (v[1], 'inf')
        return (v[1], Fraction(v[2]) * Fraction(2) ** v[3])

    @staticmethod
    def make(neg, x):
        return interp.canon(neg, x.numerator, 0) if x.denominator == 1 else \
            interp.canon(neg, x.numerator, -(x.denominator.bit_length() - 1))


def signed(neg, x):
    return -x if neg else x


class ToyRounding(unittest.TestCase):
    def test_add_sub_mul(self):
        for name in TOY:
            toy = Toy(name)
            vals = [(n, x, Toy.make(n, x)) for n, x in toy.values]
            for (an, ax, a), (bn, bx, b) in itertools.product(vals, repeat=2):
                ea, eb = signed(an, ax), signed(bn, bx)
                self.assertEqual(Toy.value(interp.add(toy.f, a, b)), toy.rn(ea + eb, an and bn), (name, ea, eb))
                self.assertEqual(Toy.value(interp.sub(toy.f, a, b)), toy.rn(ea - eb, an and not bn), (name, ea, eb))
                self.assertEqual(Toy.value(interp.mul(toy.f, a, b)), toy.rn(ea * eb, an != bn), (name, ea, eb))
                prod = interp.fma(toy.f, a, b, interp.canon(False, 0, 0))
                self.assertEqual(Toy.value(prod), toy.rn(ea * eb, False), (name, ea, eb))

    def test_fma(self):
        rng = random.Random(2)
        for name in TOY:
            toy = Toy(name)
            vals = [(n, x, Toy.make(n, x)) for n, x in toy.values]
            triples = itertools.product(vals, repeat=3) if len(vals) ** 3 < 60000 else \
                ([rng.choice(vals) for _ in range(3)] for _ in range(60000))
            for (an, ax, a), (bn, bx, b), (cn, cx, c) in triples:
                exact = signed(an, ax) * signed(bn, bx) + signed(cn, cx)
                product_zero = ax == 0 or bx == 0
                # An exact zero: -0 only from -0 + -0 (a zero product has the sign of a*b);
                # a nonzero result rounded to zero keeps its sign, which rn gives.
                zero_neg = product_zero and (an != bn) and cn
                self.assertEqual(Toy.value(interp.fma(toy.f, a, b, c)), toy.rn(exact, zero_neg),
                                 (name, a, b, c))

    def test_succ_pred_member(self):
        for name in TOY:
            toy = Toy(name)
            line = sorted({signed(n, x) for n, x in toy.values})
            for i, x in enumerate(line):
                for neg in ((False, True) if x == 0 else (x < 0,)):
                    v = Toy.make(neg, abs(x))
                    up = Toy.value(interp.succ(toy.f, v))
                    down = Toy.value(interp.pred(toy.f, v))
                    want_up = (False, 'inf') if i + 1 == len(line) else \
                        (line[i + 1] <= 0, abs(line[i + 1])) if line[i + 1] != 0 else (True, Fraction(0))
                    want_down = (True, 'inf') if i == 0 else \
                        (line[i - 1] < 0, abs(line[i - 1]))
                    self.assertEqual(up, want_up, (name, x, neg))
                    self.assertEqual(down, want_down, (name, x, neg))
                    self.assertTrue(interp.member(toy.f, v))
            f = toy.f
            self.assertEqual(Toy.value(interp.succ(f, (interp.INF, True))), (True, toy.pos[-2]))
            self.assertEqual(Toy.value(interp.pred(f, (interp.INF, False))), (False, toy.pos[-2]))
            self.assertEqual(interp.succ(f, interp.NaN), interp.NaN)
            self.assertFalse(interp.member(f, interp.canon(False, 2 ** f.p + 1, f.qmin)))
            self.assertFalse(interp.member(f, interp.canon(False, 1, f.qmin - 1)))
            self.assertFalse(interp.member(f, interp.canon(False, 1, f.qmax + f.p)))

    def test_two_sum_on_every_pair(self):
        # The interpreter as a runner of a whole kernel on a toy format: TwoSum is exact.
        toy = Toy('fp:5:-12:6')
        m = interp.Machine(common.kernels())
        vals = [Toy.make(n, x) for n, x in toy.values]
        for a, b in itertools.product(vals, repeat=2):
            s, e = m.run('two_sum', toy.f, [a, b])
            exact = signed(*Toy.value(a)) + signed(*Toy.value(b))
            want = toy.rn(exact, a[1] and b[1])
            self.assertEqual(Toy.value(s), want)
            if want[1] != 'inf' and all(x[0] == interp.NUM for x in (s, e)):
                self.assertEqual(signed(*Toy.value(s)) + signed(*Toy.value(e)), exact)


class Specials(unittest.TestCase):
    def test_ieee_rules(self):
        f = interp.parse_format('binary64')
        inf, ninf, nan = (interp.INF, False), (interp.INF, True), interp.NaN
        one, zero, nzero = common.to_value(1.0), common.to_value(0.0), common.to_value(-0.0)
        self.assertEqual(interp.add(f, inf, ninf), nan)
        self.assertEqual(interp.add(f, inf, one), inf)
        self.assertEqual(interp.fma(f, inf, zero, one), nan)
        self.assertEqual(interp.fma(f, inf, one, ninf), nan)
        self.assertEqual(interp.fma(f, one, one, ninf), ninf)
        self.assertEqual(interp.fma(f, nzero, one, nzero), nzero)
        self.assertEqual(interp.fma(f, nzero, one, zero), zero)
        self.assertEqual(interp.add(f, nzero, nzero), nzero)
        self.assertEqual(interp.sub(f, one, one), zero)
        top = interp.largest(f, False)
        self.assertEqual(interp.add(f, top, top), inf)
        self.assertEqual(interp.mul(f, nzero, one), nzero)
        self.assertFalse(interp.lt(nan, one) or interp.le(nan, nan) or interp.eq(nan, nan))
        self.assertTrue(interp.eq(zero, nzero) and interp.le(nzero, zero) and not interp.lt(nzero, zero))
        # The overflow threshold is a tie, broken to even: to infinity.
        half_ulp = interp.canon(False, 1, 970)
        self.assertEqual(interp.add(f, top, half_ulp), inf)
        self.assertEqual(interp.add(f, top, interp.canon(False, 1, 969)), top)

    def test_copy_and_zero(self):
        m = interp.Machine(common.kernels())
        f = interp.parse_format('binary64')
        for x in (interp.NaN, (interp.INF, True), common.to_value(-0.0), common.to_value(5e-324)):
            self.assertEqual(m._op('copy', f, [x], False), x)
        self.assertEqual(m._const(f, '0'), common.to_value(0.0))
        # lt(x1, 0) compares with +0: -0 is not below it.
        self.assertEqual(m.run('lt_2_1', f, [common.to_value(1.0), common.to_value(-0.0), common.to_value(1.0)]),
                         [False])
        with self.assertRaises(interp.InterpError):
            m.run('lt_2_1', f, [common.to_value(1.0), True, common.to_value(1.0)])
        with self.assertRaises(interp.InterpError):
            interp.Machine(common.kernels(common.TEST_KERNELS)).run('ops_wave2', f, [common.to_value(1.0)] * 3)


# ---------------------------------------------------------------------------------------------
# The interpreter against the host.

edge_cases = common.edge_cases


class AgainstHardware(unittest.TestCase):
    """Bit identity with Python's float (binary64) and with struct-rounded doubles (binary32)."""
    N = common.size(4000, 100000)

    @classmethod
    def setUpClass(cls):
        if not hasattr(math, 'fma'):
            raise unittest.SkipTest('the host arithmetic needs math.fma (Python 3.13 or later)')

    def compare(self, directory, fused=True, consteval=False, only=None):
        ks = common.kernels(directory)
        for name, k in ks.items():
            if only and not only(k):
                continue
            for fmt in ('binary64', 'binary32'):
                cases = common.requests(fmt, k, self.N, 'hw') + edge_cases(fmt, k, 2000)
                got = common.interpret(directory, name, fmt, cases, fused=fused, consteval=consteval)
                bad = []
                for case, g in zip(cases, got):
                    h = hwfloat.run(ks, name, fmt, case, fused=fused, consteval=consteval)
                    if not all(common.same(x, y) for x, y in zip(g, h)):
                        bad.append((case, g, h))
                with self.subTest(kernel=name, fmt=fmt, fused=fused, consteval=consteval):
                    self.assertEqual(bad[:3], [], f'{len(bad)} of {len(cases)} differ')

    def test_kernels(self):
        self.compare(None)

    def test_kernels_constant_evaluation(self):
        ks = common.kernels()
        from kairn_gen import cpp
        self.compare(None, consteval=True, only=lambda k: cpp.constexpr_kind(k, ks) is not None)

    def test_every_operation(self):
        for fused in (True, False):
            self.compare(common.TEST_KERNELS, fused=fused)

    def test_every_operation_constant_evaluation(self):
        self.compare(common.TEST_KERNELS, consteval=True, only=lambda k: k.name in ('ops_muladd', 'ops_one'))


class Machine(unittest.TestCase):
    def test_structured_and_inlined_evaluation_agree(self):
        # The interpreter keeps calls, as the Rocq model does; ir.flatten inlines them, as the
        # C++ printer does. Both must compute the same values.
        rng = random.Random(3)
        for directory in (None, common.TEST_KERNELS):
            ks = common.kernels(directory)
            m = interp.Machine(ks)
            for name, k in ks.items():
                flat = ir.prims(k, ks)
                for fmt in ('binary64', 'binary32'):
                    f = interp.parse_format(fmt)
                    for case in common.requests(fmt, k, 300, 'flat'):
                        ins = [common.to_value(x) for x in case]
                        env = dict(zip(k.input_limbs, ins))
                        for p in flat:
                            args = [m._const(f, a.name) if a.const else env[a.name] for a in p.args]
                            env[p.dst] = m._op(p.op, f, args, False)
                        self.assertEqual([env[v] for v in k.output_limbs], m.run(name, f, ins))
                self.assertTrue(rng)

    def test_consteval_needs_a_path(self):
        m = interp.Machine(common.kernels(), consteval=True)
        f = interp.parse_format('binary64')
        one = common.to_value(1.0)
        with self.assertRaises(interp.InterpError):
            m.run('mul_2_2', f, [one] * 4)
        with self.assertRaises(interp.InterpError):
            m.run('split', f, [one])
        # two_prod runs Dekker's product with plain products: -0 * 1 is -0 there, +0 at run time.
        nzero = common.to_value(-0.0)
        self.assertEqual(m.run('two_prod', f, [nzero, one])[0], nzero)
        self.assertEqual(interp.Machine(common.kernels()).run('two_prod', f, [nzero, one])[0],
                         common.to_value(0.0))

    def test_inputs_must_be_numbers_of_the_format(self):
        m = interp.Machine(common.kernels())
        f = interp.parse_format('fp:3:-4:2')
        with self.assertRaises(interp.InterpError):
            m.run('two_sum', f, [interp.parse_limb('0x1.2p+0'), interp.parse_limb('0x1p+0')])
        with self.assertRaises(interp.InterpError):
            m.run('two_sum', f, [interp.parse_limb('0x1p+0')])
        with self.assertRaises(interp.InterpError):
            m.run('nope', f, [])

    def test_splitter_must_exist_in_the_format(self):
        m = interp.Machine(common.kernels())
        with self.assertRaises(interp.InterpError):   # 2^1 + 1 has two bits
            m.run('split', interp.parse_format('fp:1:-4:4'), [interp.parse_limb('0x1p+0')])


class Protocol(unittest.TestCase):
    def run_interp(self, text, *args):
        return subprocess.run([sys.executable, KAIRN_GEN, 'interp', *args], input=text,
                              capture_output=True, text=True)

    def test_lines(self):
        text = ('# a comment, copied\n'
                'two_sum binary64 0x1p+0 0x1p-60 #edge\n'
                '\n'
                'add_2_1 fp:5:-12:6 0x1.8p+0 0x1p-6 0x1p-1\n'
                'two_prod binary32 0x1.000002p+0 0x1.000002p+0\n'
                'mul_2_2 binary64 inf 0x0p+0 nan 0x0p+0 #special\n')
        r = self.run_interp(text)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines(), [
            '# a comment, copied',
            'two_sum binary64 0x1p+0 0x1p-60 #edge -> 0x1p+0 0x1p-60',
            '',
            'add_2_1 fp:5:-12:6 0x1.8p+0 0x1p-6 0x1p-1 -> 0x1p+1 0x1p-6',
            'two_prod binary32 0x1.000002p+0 0x1.000002p+0 -> 0x1.000004p+0 0x1p-46',
            'mul_2_2 binary64 inf 0x0p+0 nan 0x0p+0 #special -> nan nan'])

    def test_variants_on_the_command_line(self):
        r = self.run_interp('two_prod binary64 -0x0p+0 0x1p+0\n', '--ce')
        self.assertEqual(r.stdout, 'two_prod binary64 -0x0p+0 0x1p+0 -> -0x0p+0 0x0p+0\n')
        # (1 + 2^-27)^2 - 1 is 2^-26 + 2^-54 with one rounding, 2^-26 with two.
        line = 'ops_muladd binary64 0x1.0000002p+0 0x1.0000002p+0 -0x1p+0\n'
        r = self.run_interp(line, '--kernels', common.TEST_KERNELS, '--muladd', 'unfused')
        self.assertEqual(r.stdout.split(' -> ')[1].split()[0], '-0x1p-26')
        r = self.run_interp(line, '--kernels', common.TEST_KERNELS)
        self.assertEqual(r.stdout.split(' -> ')[1].split()[0], '-0x1.0000001p-26')

    def test_masks(self):
        text = ('lt_2_1 binary64 0x1p+0 -0x1p-60 0x1p+0\n'
                'eq_2_2 fp:4:-6:3 0x1p+0 0x0p+0 0x1p+0 -0x0p+0\n'
                'ops_wave2 binary32 -0x1p+0 1 0x1p+0\n'
                'ops_wave2 binary32 -0x1p+0 0 0x1p+0\n')
        r = self.run_interp(text, '--kernels', common.TEST_KERNELS)
        self.assertEqual(r.returncode, 2)        # lt_2_1 is not a test kernel
        r = self.run_interp(text.split('\n', 2)[2], '--kernels', common.TEST_KERNELS)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([x.split(' -> ')[1].split()[-1] for x in r.stdout.splitlines()], ['1', '1'])
        r = self.run_interp(''.join(text.splitlines(True)[:2]))
        self.assertEqual(r.stdout, 'lt_2_1 binary64 0x1p+0 -0x1p-60 0x1p+0 -> 1\n'
                                   'eq_2_2 fp:4:-6:3 0x1p+0 0x0p+0 0x1p+0 -0x0p+0 -> 1\n')
        for bad in ('2', 'true', '0x1p+0', '-0'):
            r = self.run_interp(f'ops_wave2 binary64 0x1p+0 {bad} 0x1p+0\n', '--kernels', common.TEST_KERNELS)
            self.assertEqual(r.returncode, 2, bad)
            self.assertIn('not a mask', r.stderr)
        r = self.run_interp('ops_wave2 binary64 0x1p+0 1 1\n', '--kernels', common.TEST_KERNELS)
        self.assertIn("not a limb: '1'", r.stderr)

    def test_errors_name_the_line(self):
        for line, words in (('nope binary64 0x1p+0', 'unknown kernel'),
                            ('two_sum binary64 0x1p+0', 'takes 2 limbs'),
                            ('two_sum binary64  0x1p+0 0x1p+0', 'single spaces'),
                            ('two_sum binary64 1.0 0x1p+0', 'not a limb'),
                            ('two_sum binary16 0x1p+0 0x1p+0', 'unknown format'),
                            ('two_sum fp:3:-4:2 0x1.2p+0 0x1p+0', 'not a number of format'),
                            ('two_sum binary32 0x1.0000001p+0 0x1p+0', 'not a number of format')):
            r = self.run_interp(f'# fine\n{line}\n')
            self.assertEqual(r.returncode, 2, line)
            self.assertIn('line 2:', r.stderr)
            self.assertIn(words, r.stderr)


if __name__ == '__main__':
    unittest.main()
