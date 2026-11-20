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
import test_cxx
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

    def test_non_finite_semantics(self):
        """IEEE 754 for non-finite values, on a toy format of the IEEE shape (qmin + qmax = 3 - 2p)
        and on the two hardware formats: overflow to infinity with the sign of the exact result,
        NaN propagation, comparisons false on NaN, the neighbors at the ends of the format, 0 inf,
        and guard."""
        m = interp.Machine(common.kernels())
        inf, ninf, nan = (interp.INF, False), (interp.INF, True), interp.NaN
        zero, nzero = interp.canon(False, 0, 0), interp.canon(True, 0, 0)
        one, none = interp.canon(False, 1, 0), interp.canon(True, 1, 0)
        for name in ('fp:3:-4:1', 'binary64', 'binary32'):
            f = interp.parse_format(name)

            def op(o, *a):
                return m._op(o, f, list(a), False)
            top, ntop = interp.largest(f, False), interp.largest(f, True)
            eta, neta = interp.canon(False, 1, f.qmin), interp.canon(True, 1, f.qmin)
            # Overflow: an infinity with the sign of the exact result.
            self.assertEqual(op('add', top, top), inf, name)
            self.assertEqual(op('sub', ntop, top), ninf, name)
            self.assertEqual(op('prod', top, ntop), ninf, name)
            self.assertEqual(op('fma', ntop, top, top), ninf, name)
            self.assertEqual(op('prod', neta, inf), ninf, name)     # a tiny t made into its infinity
            # Underflow keeps the sign; an exact cancellation is +0; -0 + -0 is -0.
            self.assertEqual(op('prod', neta, eta), nzero, name)
            self.assertEqual(op('add', top, ntop), zero, name)
            self.assertEqual(op('add', nzero, nzero), nzero, name)
            # NaN propagates through every arithmetic operation, guard and the steps included.
            for o in ('add', 'sub', 'prod'):
                self.assertEqual((op(o, nan, one), op(o, one, nan), op(o, nan, inf)), (nan, nan, nan), (name, o))
            for o in ('guard', 'neg', 'abs', 'succ', 'pred', 'copy'):
                self.assertEqual(op(o, nan), nan, (name, o))
            for args in ((nan, one, one), (one, nan, one), (one, one, nan)):
                for o in ('fma', 'fms', 'fnma'):
                    self.assertEqual(op(o, *args), nan, (name, o, args))
            # Invalid operations.
            self.assertEqual((op('add', inf, ninf), op('sub', inf, inf), op('prod', zero, inf),
                              op('prod', ninf, nzero), op('fma', zero, inf, one), op('fma', inf, one, ninf)),
                             (nan,) * 6, name)
            # Comparisons: false whenever an operand is a NaN; the infinities at the ends.
            for o in ('lt', 'le', 'eq'):
                for x, y in ((nan, one), (one, nan), (nan, nan), (nan, inf)):
                    self.assertFalse(op(o, x, y), (name, o, x, y))
            self.assertTrue(op('lt', ninf, ntop) and op('lt', top, inf) and op('le', inf, inf) and op('eq', ninf, ninf))
            self.assertFalse(op('lt', inf, inf) or op('eq', inf, ninf))
            # The neighbors at the ends: succ of the largest number is +inf, succ(-inf) the most
            # negative number, and the infinities stay where there is nothing further.
            self.assertEqual((op('succ', top), op('succ', ninf), op('succ', inf)), (inf, ntop, inf), name)
            self.assertEqual((op('pred', ntop), op('pred', inf), op('pred', ninf)), (ninf, top, ninf), name)
            self.assertEqual((op('succ', nzero), op('pred', zero)), (eta, neta), name)
            # guard: the value itself, a zero made positive.
            for x in (one, none, top, ntop, eta, neta, inf, ninf, zero):
                self.assertEqual(op('guard', x), x, (name, x))
            self.assertEqual(op('guard', nzero), zero, name)
            self.assertEqual((m._const(f, 'inf'), m._const(f, 'nan')), (inf, nan), name)
            self.assertEqual((op('neg', inf), op('abs', ninf)), (ninf, inf), name)
            # times_inf: a NaN for a NaN or a zero, otherwise the infinity with the sign of t.
            for x, want in ((one, inf), (none, ninf), (eta, inf), (neta, ninf), (top, inf), (ntop, ninf),
                            (inf, inf), (ninf, ninf), (zero, nan), (nzero, nan), (nan, nan)):
                self.assertEqual(op('times_inf', x), want, (name, x))
            # In constant evaluation guard returns its operand, -0 included.
            ce = interp.Machine(common.kernels(), consteval=True)
            self.assertEqual([ce._op('guard', f, [x], False) for x in (nzero, nan, ninf, one)], [nzero, nan, ninf, one])
            self.assertEqual(ce._op('times_inf', f, [nzero], False), nan)

    def test_up_constants(self):
        """const up(EXPR), against exact fractions computed here: the smallest number of the format
        not below the expression (at least it, and its predecessor in the format below it), in the
        two hardware formats and toy formats, one of them where the expression is below eta."""
        ks = common.kernels()
        F = Fraction
        forms = {
            'up((1+u)^6)': lambda u, eta, U, T: (1 + u) ** 6,
            'up(unit(mul_2_2)/(1-unit(mul_2_2))*(1+u))': lambda u, eta, U, T: U / (1 - U) * (1 + u),
            'up((1+u)*((1+u)^5*2*eta+tiny(mul_2_2)/(1-unit(mul_2_2))+eta/2))':
                lambda u, eta, U, T: (1 + u) * ((1 + u) ** 5 * 2 * eta + T / (1 - U) + eta / 2),
            # H of ball_mul_2, as its description writes it: the same plus the smallest normal number.
            'up((1+u)*(2*(1+u)^5*eta+tiny(mul_2_2)/(1-unit(mul_2_2))+eta/2)+eta/(2*u))':
                lambda u, eta, U, T: (1 + u) * (2 * (1 + u) ** 5 * eta + T / (1 - U) + eta / 2) + eta / (2 * u),
        }
        self.assertIn(list(forms)[-1], ir.constants(ks['ball_mul_2']))
        below_eta = 0
        for p, qmin, qmax in ((53, -1074, 971), (24, -149, 104), (4, -6, 3), (5, -12, 6), (4, -2, 3), (6, -9, 0)):
            f = interp.Format(f'fp:{p}:{qmin}:{qmax}', p, qmin, qmax)
            u, eta = F(1, 2 ** p), F(2) ** qmin
            U, T = 4 * u ** 2, F(3, 2) * eta          # mul_2_2: c = 4, k = 2, t = 3/2
            for name, form in forms.items():
                exact = form(u, eta, U, T)
                v = consts.value(name, ks, p, qmin, qmax)
                value = interp.canon(False, v.numerator, -(v.denominator.bit_length() - 1))
                self.assertTrue(interp.member(f, value), (name, p))
                self.assertGreaterEqual(v, exact, (name, p))
                down = interp.pred(f, value)
                below = Fraction(down[2]) * Fraction(2) ** down[3] * (-1 if down[1] else 1) if down[2] else Fraction(0)
                self.assertLess(below, exact, (name, p))
                if exact < eta:
                    self.assertEqual(v, eta, (name, p))
                    below_eta += 1
        self.assertGreater(below_eta, 0)
        # The interpreter computes the same constants, in any format; the expression is checked.
        m = interp.Machine(common.kernels(common.TEST_KERNELS))
        f = interp.parse_format('fp:5:-12:6')
        self.assertEqual(m._const(f, 'up((1+u)^6)'), interp.canon(False, 5, -2))      # (33/32)^6 = 1.2028 up: 5/4
        with self.assertRaises(interp.InterpError):
            m._const(interp.parse_format('fp:3:-4:3'), 'up(unit(ops_mul))')               # below its precision 4
        with self.assertRaises(consts.ConstError):
            consts.value('up(u-1)', ks, 53, -1074, 971)

    def test_no_subnormal_constant(self):
        """No constant that a kernel computes with is subnormal in the two hardware formats: a fused
        operation with a subnormal operand is slow on some processors, and H of the Ball cores was
        one until the smallest normal number was added to it. H is normal in every format, by its
        expression; the radius of a Ball core is RN(t G + H) with t >= 0 and G >= 1, so it is at
        least H, and normal too. (In a toy format with few exponents the other constants need not
        be: u itself is below the smallest normal number of fp:4:-6:3.)"""
        ks = common.kernels()
        seen, subnormal = 0, []
        for p, qmin, qmax in ((53, -1074, 971), (24, -149, 104)):
            normal = Fraction(2) ** (qmin + p - 1)
            for name, k in ks.items():
                for c in ir.constants(k):
                    if c not in (ir.ZERO, 'inf', 'nan'):
                        if consts.value(c, ks, p, qmin, qmax) < normal:
                            subnormal.append((name, c, p))
                        seen += 1
        self.assertEqual(subnormal, [])
        # E, G, H of the six cores, and the splitter; P of the two directed products, and N of the
        # two scalings of a ball by a power of two. Milestone 2: E, G, H of add_ball_2_2 and
        # mul_ball_2_2, and P of mul_dir_1.
        self.assertEqual(seen, 2 * (3 * 6 + 1 + 2 + 2 + 3 * 2 + 1))
        cores = {'ball_add_1': 2, 'ball_add_2': 2, 'ball_scale_1': 3, 'ball_scale_2': 3, 'ball_mul_1': 4,
                 'ball_mul_2': 5}
        for name, more in cores.items():
            h = [c for c in ir.constants(ks[name]) if 'eta' in c]
            self.assertEqual(len(h), 1, name)
            self.assertTrue(h[0].endswith('+eta/(2*u))'), name)
            # In binary64: the smallest normal number plus 2 to 5 eta.
            self.assertEqual(consts.value(h[0], ks, 53, -1074, 971),
                             Fraction(2) ** -1022 + more * Fraction(2) ** -1074, name)
            for p, qmin, qmax in ((24, -149, 104), (4, -6, 3), (5, -12, 6), (6, -9, 0), (4, -5, 1)):
                self.assertGreaterEqual(consts.value(h[0], ks, p, qmin, qmax), Fraction(2) ** (qmin + p - 1),
                                        (name, p))

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
                cases = common.requests(fmt, k, self.N, 'hw') + edge_cases(fmt, k, 2000) + \
                    common.nonfinite_cases(fmt, k, self.N // 4, 'hw')
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


class TwoExecutionsOfAProduct(unittest.TestCase):
    """The rule of the product (milestone2.md, "The two executions of a product"): a kernel whose
    only fused operations are prod is constexpr, and runs in constant evaluation with each prod a
    plain product. There it gives the bits it gives at run time; or, for the kernels whose outputs
    can be an exact zero product (mul_pow2_2 and the exact scalings of a ball, as the page says;
    mul_1_1 and two_prod_dekker, whose first output is the product, which the page does not name),
    the same values, a zero possibly of the other sign. On the corpus of the interpreter's tests
    against the host: random cases of every stratum, the edge values in every limb, and the
    non-finite operands of the extended domain (all NaNs being the same). The C++ is tied to these
    results by test_cxx (constant evaluation: ConstantEvaluation; run time: Kernels.test_matrix)."""
    N = common.size(4000, 100000)
    ZERO_SIGN = {'mul_pow2_2', 'mul_pow2_2_full', 'ball_mul_pow2_1', 'ball_mul_pow2_2', 'ball_mul_pow2_1_full',
                 'ball_mul_pow2_2_full', 'mul_1_1', 'two_prod_dekker'}

    def test_the_kernels(self):
        from kairn_gen import cpp
        ks = common.kernels()
        names = [n for n, k in ks.items() if cpp.product_rule(k, ks)]
        self.assertEqual(set(names), self.ZERO_SIGN | {'rmul', 'split'})
        for name in names:
            k = ks[name]
            differ = 0
            for fmt in ('binary64', 'binary32'):
                cases = common.requests(fmt, k, self.N, 'two') + edge_cases(fmt, k, 2000) + \
                    common.nonfinite_cases(fmt, k, self.N // 4, 'two')
                ce = common.interpret(None, name, fmt, cases, consteval=True)
                rt = common.interpret(None, name, fmt, cases)
                bits = [(c, a, b) for c, a, b in zip(cases, ce, rt) if not all(map(common.same, a, b))]
                values = [(c, a, b) for c, a, b in bits
                          if not all(common.same(x, y) or x == y == 0 for x, y in zip(a, b))]
                with self.subTest(kernel=name, fmt=fmt):
                    self.assertEqual(values[:3], [], f'{len(values)} of {len(cases)} differ in value')
                    if name not in self.ZERO_SIGN:
                        self.assertEqual(bits[:3], [], f'{len(bits)} of {len(cases)} differ in bits')
                differ += len(bits)
            # Every kernel allowed a zero of the other sign has one somewhere in the corpus.
            self.assertEqual(differ > 0, name in self.ZERO_SIGN, name)


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
        # mul_down_1 and mul_up_1 trust the sign of two_prod's error term, which only its FMA
        # computes: they have no constant-evaluation path (milestone2.md, "Building blocks on T").
        for name in ('mul_down_1', 'mul_up_1'):
            with self.assertRaises(interp.InterpError):
                m.run(name, f, [one] * 2)
        # two_prod runs Dekker's product with plain products: -0 * 1 is -0 there, +0 at run time.
        nzero = common.to_value(-0.0)
        self.assertEqual(m.run('two_prod', f, [nzero, one])[0], nzero)
        self.assertEqual(interp.Machine(common.kernels()).run('two_prod', f, [nzero, one])[0],
                         common.to_value(0.0))
        # A kernel whose only fused operations are prod runs with plain products (the rule of the
        # product): mul_1_1 gives -0 for -0 * 1 there, +0 at run time; split computes the same.
        self.assertEqual(m.run('mul_1_1', f, [nzero, one]), [nzero])
        self.assertEqual(interp.Machine(common.kernels()).run('mul_1_1', f, [nzero, one]), [common.to_value(0.0)])
        self.assertEqual(m.run('split', f, [one]), interp.Machine(common.kernels()).run('split', f, [one]))

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

    def test_non_finite_limbs(self):
        """The kernels of the non-finite layer on non-finite operands, written inf, -inf and nan,
        and on finite ones that overflow; worked out by hand from milestone1.md."""
        cases = {
            'make_2 binary64 -0x0p+0': '0x0p+0 0x0p+0',            # guard: the zero made positive
            'make_2 binary32 -inf': '-inf 0x0p+0',
            'make_2 fp:3:-4:1 nan': 'nan nan',
            'make_2_limbs binary64 0x1p+0 -0x1p-60': '0x1p+0 -0x1p-60',
            'make_2_limbs binary64 -inf -0x0p+0': '-inf 0x0p+0',
            # inf - inf is NaN; 14 + 14 overflows the toy format, whose largest number is 14.
            'add_2_2_full binary64 inf 0x0p+0 -inf 0x0p+0': 'nan nan',
            'add_2_2_full fp:3:-4:1 0x1.cp+3 0x0p+0 0x1.cp+3 0x0p+0': 'inf 0x0p+0',
            'sub_2_2_full fp:3:-4:1 -0x1.cp+3 0x0p+0 0x1.cp+3 0x0p+0': '-inf 0x0p+0',
            'add_2_1_full binary32 0x1p+0 0x0p+0 -inf': '-inf 0x0p+0',
            'sub_1_2_full binary64 inf nan nan': 'nan nan',
            'mul_2_2_full binary64 0x0p+0 0x0p+0 inf 0x0p+0': 'nan nan',      # 0 inf
            'mul_2_1_full binary32 -0x1p+0 0x0p+0 inf': '-inf 0x0p+0',
            'mul_pow2_2_full binary64 -inf 0x0p+0 0x1p-3': '-inf 0x0p+0',
            'add_2_2_full binary64 0x1p+0 0x1p-60 0x1p+1 0x0p+0': '0x1.8p+1 0x1p-60',
            # Balls: an empty operand gives the empty set; the whole line, a non-finite scalar, and
            # an exact zero ball times the whole line give the whole line (center 0, radius inf).
            'ball_add_1_full binary64 0x1p+0 nan 0x1p+0 0x0p+0': 'nan nan',
            'ball_add_1_full binary64 0x0p+0 inf 0x1p+0 0x0p+0': '0x0p+0 inf',
            'ball_mul_1_full binary64 0x0p+0 0x0p+0 0x0p+0 inf': '0x0p+0 inf',
            'ball_scale_1_full binary64 0x1p+0 0x0p+0 nan': '0x0p+0 inf',
            'ball_scale_2_full binary32 nan nan nan -inf': 'nan nan nan',
            'ball_mul_2_full binary64 0x0p+0 0x0p+0 inf 0x1p+0 0x0p+0 0x0p+0': '0x0p+0 0x0p+0 inf',
            'ball_make_1 binary64 0x1p+0 -0x1p+0': 'nan nan',                  # a negative radius
            'ball_make_1 binary64 inf 0x1p+0': '0x0p+0 inf',
            'ball_make_1 binary64 -0x0p+0 -0x0p+0': '0x0p+0 0x0p+0',
            'ball_make_2 binary32 0x1p+0 0x0p+0 nan': 'nan nan nan',
            'ball_make_2 binary32 nan nan 0x1p+0': '0x0p+0 0x0p+0 inf',
            'ball_make_2 binary64 0x1p+0 0x1p-60 inf': '0x0p+0 0x0p+0 inf',
            # The kernels that need no fix-up, at the ends of the range and on non-finite operands.
            'to_up_2 binary64 0x1.fffffffffffffp+1023 0x1p+969': 'inf',
            'to_down_2 binary64 -0x1.fffffffffffffp+1023 -0x1p+969': '-inf',
            'abs_upper_2 binary32 -inf 0x0p+0': 'inf',
            'radd binary64 inf 0x1p+0': 'inf',
            'rmul binary64 0x0p+0 inf': 'nan',
            'rmul fp:3:-4:1 0x1.cp+3 0x1p+1': 'inf',
            'lt_2_1 binary64 nan nan 0x1p+0': '0',
            'le_2_2 binary64 inf 0x0p+0 inf -0x0p+0': '1',
            'eq_2_1 binary64 -inf 0x0p+0 -inf': '1',
            'lt_1_2 binary32 -inf 0x1p+0 0x0p+0': '1',
            'neg_2 binary64 inf 0x0p+0': '-inf -0x0p+0',
        }
        # And those that the compiled runners must complete the same way (test_cxx, test_simd).
        for line, want in test_cxx.NON_FINITE_LINES.items():
            self.assertEqual(cases.setdefault(line, want), want, line)
        r = self.run_interp(''.join(f'{line}\n' for line in cases))
        self.assertEqual(r.returncode, 0, r.stderr)
        got = dict(line.split(' -> ') for line in r.stdout.splitlines())
        self.assertEqual(got, cases)

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
