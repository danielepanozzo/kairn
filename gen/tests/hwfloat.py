"""Kernels evaluated with the host's floating-point arithmetic, to check the interpreter against.

binary64 is Python's float, with math.fma. binary32 is computed in double and rounded to float by
struct (a C cast): products of two binary32 numbers are exact in double, and the one rounding of
a binary32 sum or FMA is recovered from the double result and its exact error, so that no value is
rounded twice. This shares no arithmetic with the interpreter, which works on integers.
"""
import math
import struct
from fractions import Fraction

from kairn_gen import expr

INF = math.inf


def fma64(a, b, c):
    try:
        return math.fma(a, b, c)
    except OverflowError:
        # Python raises where IEEE returns an infinity, with the sign of ab: ab + c can exceed
        # the largest double only if |ab| does, or if c has the sign of ab.
        return math.copysign(INF, math.copysign(1.0, a) * math.copysign(1.0, b))
    except ValueError:
        return math.nan   # inf * 0, or inf - inf


def next_up64(a):
    return math.nextafter(a, INF)


def r32(x):
    try:
        return struct.unpack('<f', struct.pack('<f', x))[0]
    except OverflowError:
        return math.copysign(INF, x)


def fma32(a, b, c):
    if not (math.isfinite(a) and math.isfinite(b) and math.isfinite(c)):
        return r32(fma64(a, b, c))
    p = a * b                       # exact: 48 bits, and far from the double range's ends
    s = p + c                       # RN64(ab + c), with IEEE's sign when it is zero
    if s == 0:
        return s
    bb = s - p                      # TwoSum: err = (ab + c) - s exactly
    err = (p - (s - bb)) + (c - bb)
    up, down = r32(math.nextafter(s, INF)), r32(math.nextafter(s, -INF))
    if up == down:                  # no binary32 rounding boundary at s
        return r32(s)
    # s is a binary32 midpoint (or the overflow threshold): the error decides, and none is a tie.
    return up if err > 0 else down if err < 0 else r32(s)


def next_up32(a):
    if a != a or a == INF:
        return a
    if a == 0:
        return math.ldexp(1, -149)
    bits = struct.unpack('<I', struct.pack('<f', a))[0]
    return struct.unpack('<f', struct.pack('<I', bits + 1 if bits >> 31 == 0 else bits - 1))[0]


def round_up(q, fmt):
    """The smallest float of the format not below the rational q >= 0, found with the host's
    floats: start from Python's correctly rounded float(q) and step (independent of consts.py)."""
    up = next_up64 if fmt == 'binary64' else next_up32
    rnd = (lambda x: x) if fmt == 'binary64' else r32
    x = rnd(float(q))
    while Fraction(x) < q:
        x = up(x)
    while x > 0 and Fraction(-up(-x)) >= q:
        x = -up(-x)
    return x


def computed_constant(kernels, name, fmt):
    """unit_computed(K) or tiny_computed(K) from K's claims, rounded up with the host's floats."""
    fn, kname = name[:-1].split('(')
    (e,) = [e for e in kernels[kname].ensures if e['kind'] == 'error']
    p, qmin = (53, -1074) if fmt == 'binary64' else (24, -149)
    u = Fraction(1, 2 ** p)
    unit = expr.evaluate(expr.parse(e['c']), {'u': u}) * u ** e['k']
    tiny = expr.evaluate(expr.parse(e['t']), {}) * Fraction(2) ** qmin
    return round_up((unit if fn == 'unit_computed' else tiny) / (1 - unit), fmt)


class Arith:
    def __init__(self, fmt, kernels):
        self.fmt = fmt
        if fmt == 'binary64':
            self.fma, self.round, self.next_up = fma64, (lambda x: x), next_up64
            self.add = lambda x, y: x + y
            self.consts = {'splitter': 134217729.0}   # 2^27 + 1, written here independently
        else:
            self.fma, self.round, self.next_up = fma32, r32, next_up32
            self.add = lambda x, y: fma32(x, 1.0, y)
            self.consts = {'splitter': 4097.0}        # 2^12 + 1
        self.consts['0'] = 0.0
        self.kernels = kernels

    def const(self, name):
        if name not in self.consts:
            self.consts[name] = computed_constant(self.kernels, name, self.fmt)
        return self.consts[name]

    def op(self, op, a, fused, plain_prod):
        f = self.fma
        if op == 'add':
            return self.add(a[0], a[1])
        if op == 'sub':
            return self.add(a[0], -a[1])
        if op == 'prod':
            return self.round(a[0] * a[1]) if plain_prod else f(a[0], a[1], 0.0)
        if op == 'fma':
            return f(a[0], a[1], a[2])
        if op == 'fms':
            return f(a[0], a[1], -a[2])
        if op == 'fnma':
            return f(-a[0], a[1], a[2])
        if op == 'muladd':
            return f(a[0], a[1], a[2]) if fused else self.add(self.round(a[0] * a[1]), a[2])
        if op == 'neg':
            return -a[0]
        if op == 'abs':
            return math.fabs(a[0])
        if op == 'lt':
            return a[0] < a[1]
        if op == 'le':
            return a[0] <= a[1]
        if op == 'eq':
            return a[0] == a[1]
        if op == 'and':
            return a[0] and a[1]
        if op == 'or':
            return a[0] or a[1]
        if op == 'not':
            return not a[0]
        if op == 'select':
            return a[1] if a[0] else a[2]
        if op == 'succ':
            return self.next_up(a[0])
        if op == 'pred':
            return -self.next_up(-a[0])
        if op == 'copy':
            return a[0]
        raise ValueError(op)


def run(kernels, name, fmt, inputs, fused=True, consteval=False):
    """A kernel as written, calls included; consteval runs its variant with plain products.
    Masks are bools, and outputs that are masks come back as 1.0 or 0.0."""
    arith = Arith(fmt, kernels)
    k = kernels[name]
    plain = False
    if consteval:
        fused = False      # constant evaluation never contracts
        if k.ce_variant:
            k, plain = kernels[k.ce_variant], True

    def ev(k, args):
        env = dict(zip(k.input_limbs, args))
        for st in k.body:
            a = [arith.const(x.name) if x.const else env[x.name] for x in st.args]
            if st.op in kernels:
                env.update(zip(st.dsts, ev(kernels[st.op], a)))
            else:
                env[st.dsts[0]] = arith.op(st.op, a, fused, plain)
        return [env[v] for v in k.output_limbs]

    return [float(x) if isinstance(x, bool) else x for x in ev(k, list(inputs))]
