"""The interpreter: a runner that evaluates kernels exactly, on any binary format.

A format is (p, qmin, qmax): its numbers are m 2^q with integers |m| < 2^p and qmin <= q <= qmax
(architecture.md, "Number formats"). Every operation is computed exactly on integers and rounded
once, to nearest with ties to even, with gradual underflow, and to infinity when the rounding in
unbounded range exceeds the largest finite number. Signed zeros, infinities and NaN follow IEEE 754.

A value is one of
    (NUM, neg, m, e)   (-1)^neg m 2^e, with m odd, or m = e = 0 for a zero
    (INF, neg)
    (NAN,)
A mask is a Python bool.

Kernels are evaluated as written, calls included, as the Rocq model reads them; the C++ printer
inlines calls, so comparing the two also tests the inlining.
"""
import re
from dataclasses import dataclass

from . import consts, ir

NUM, INF, NAN = 'num', 'inf', 'nan'
NaN = (NAN,)


class InterpError(Exception):
    pass


@dataclass(frozen=True)
class Format:
    name: str
    p: int
    qmin: int
    qmax: int


NAMED_FORMATS = {'binary64': (53, -1074, 971), 'binary32': (24, -149, 104)}


def parse_format(name):
    if name in NAMED_FORMATS:
        return Format(name, *NAMED_FORMATS[name])
    m = re.fullmatch(r'fp:([0-9]+):(-?[0-9]+):(-?[0-9]+)', name)
    if not m:
        raise InterpError(f'unknown format {name!r}: binary64, binary32 or fp:P:QMIN:QMAX')
    p, qmin, qmax = (int(g) for g in m.groups())
    if p < 1 or qmin > qmax:
        raise InterpError(f'format {name!r}: needs P >= 1 and QMIN <= QMAX')
    return Format(name, p, qmin, qmax)


def canon(neg, m, e):
    if m == 0:
        return (NUM, neg, 0, 0)
    tz = (m & -m).bit_length() - 1
    return (NUM, neg, m >> tz, e + tz)


def rnd(f, neg, m, e):
    """RN((-1)^neg m 2^e) in format f, for an integer m > 0."""
    q = max(e + m.bit_length() - f.p, f.qmin)   # exponent of the last bit that can be kept
    if q > e:
        s = q - e
        if s > m.bit_length() + 1:
            return (NUM, neg, 0, 0)   # below a quarter of the quantum (and no huge shift)
        rest = m & ((1 << s) - 1)
        m >>= s
        half = 1 << (s - 1)
        if rest > half or (rest == half and m & 1):
            m += 1
        e = q
        if m == 0:
            return (NUM, neg, 0, 0)   # underflow to zero keeps the sign of the exact result
    # m now has at most p bits (a carry gives 2^p, still at most p significant bits), so it
    # exceeds the largest finite (2^p - 1) 2^qmax exactly when it reaches 2^(qmax + p).
    if e + m.bit_length() > f.qmax + f.p:
        return (INF, neg)
    return canon(neg, m, e)


def member(f, v):
    """Whether v is a number of format f (infinities and NaN count as members)."""
    if v[0] != NUM or v[2] == 0:
        return True
    return rnd(f, v[1], v[2], v[3]) == v


def _sum(f, xn, xm, xe, yn, ym, ye):
    """RN(x + y) of exact finite x and y, with IEEE 754's signs for zero results."""
    if xm == 0 and ym == 0:
        return (NUM, xn and yn, 0, 0)   # -0 + -0 = -0; every other sum of zeros is +0
    if xm == 0:
        return rnd(f, yn, ym, ye)
    if ym == 0:
        return rnd(f, xn, xm, xe)
    e = min(xe, ye)
    s = ((-xm if xn else xm) << (xe - e)) + ((-ym if yn else ym) << (ye - e))
    if s == 0:
        return (NUM, False, 0, 0)   # an exact cancellation is +0 in round to nearest
    return rnd(f, s < 0, -s if s < 0 else s, e)


def add(f, x, y):
    if x[0] == NAN or y[0] == NAN:
        return NaN
    if x[0] == INF:
        return NaN if y[0] == INF and y[1] != x[1] else x
    if y[0] == INF:
        return y
    return _sum(f, x[1], x[2], x[3], y[1], y[2], y[3])


def neg(x):
    return x if x[0] == NAN else (x[0], not x[1]) + x[2:]


def sub(f, x, y):
    return add(f, x, neg(y))


def _is_zero(x):
    return x[0] == NUM and x[2] == 0


def fma(f, a, b, c):
    """RN(ab + c) with one rounding."""
    if a[0] == NAN or b[0] == NAN or c[0] == NAN:
        return NaN
    pn = a[1] != b[1]
    if a[0] == INF or b[0] == INF:
        if _is_zero(a) or _is_zero(b):
            return NaN
        if c[0] == INF and c[1] != pn:
            return NaN
        return (INF, pn)
    if c[0] == INF:
        return c
    return _sum(f, pn, a[2] * b[2], a[3] + b[3], c[1], c[2], c[3])


def mul(f, a, b):
    """RN(ab): the plain product, which only constant evaluation computes."""
    if a[0] == NAN or b[0] == NAN:
        return NaN
    n = a[1] != b[1]
    if a[0] == INF or b[0] == INF:
        return NaN if _is_zero(a) or _is_zero(b) else (INF, n)
    m = a[2] * b[2]
    return (NUM, n, 0, 0) if m == 0 else rnd(f, n, m, a[3] + b[3])


def absolute(x):
    return x if x[0] == NAN else (x[0], False) + x[2:]


def _compare(x, y):
    """-1, 0 or 1 for values that are not NaN; the two zeros are equal."""
    rx = (-2 if x[1] else 2) if x[0] == INF else 0
    ry = (-2 if y[1] else 2) if y[0] == INF else 0
    if rx or ry:
        return (rx > ry) - (rx < ry)
    sx = 0 if x[2] == 0 else (-1 if x[1] else 1)
    sy = 0 if y[2] == 0 else (-1 if y[1] else 1)
    if sx != sy or sx == 0:
        return (sx > sy) - (sx < sy)
    a, b = (x[2] << (x[3] - y[3]), y[2]) if x[3] >= y[3] else (x[2], y[2] << (y[3] - x[3]))
    return ((a > b) - (a < b)) * sx


def lt(x, y):
    return x[0] != NAN and y[0] != NAN and _compare(x, y) < 0


def le(x, y):
    return x[0] != NAN and y[0] != NAN and _compare(x, y) <= 0


def eq(x, y):
    return x[0] != NAN and y[0] != NAN and _compare(x, y) == 0


def largest(f, n):
    return canon(n, (1 << f.p) - 1, f.qmax)


def succ(f, x):
    """The next number of the format above x (IEEE 754 nextUp)."""
    if x[0] == NAN:
        return x
    if x[0] == INF:
        return largest(f, True) if x[1] else x
    if x[2] == 0:
        return (NUM, False, 1, f.qmin)
    if x[1]:
        return neg(_pred_positive(f, x[2], x[3]))
    q = max(x[3] + x[2].bit_length() - f.p, f.qmin)   # exponent of ulp(x)
    m = (x[2] << (x[3] - q)) + 1
    return (INF, False) if q + m.bit_length() > f.qmax + f.p else canon(False, m, q)


def _pred_positive(f, m, e):
    q = max(e + m.bit_length() - f.p, f.qmin)
    m <<= e - q
    if m == 1 << (f.p - 1) and q > f.qmin:
        return canon(False, 2 * m - 1, q - 1)   # below a power of two the gap is half as wide
    return canon(False, m - 1, q)


def pred(f, x):
    return neg(succ(f, neg(x)))


# ---------------------------------------------------------------------------------------------
# Limbs as text: C99 hexadecimal floating-point literals, inf, -inf, nan.

_HEX = re.compile(r'([+-]?)0[xX]([0-9a-fA-F]*)(?:\.([0-9a-fA-F]*))?[pP]([+-]?[0-9]+)')


def parse_limb(text):
    if text == 'inf':
        return (INF, False)
    if text == '-inf':
        return (INF, True)
    if text == 'nan':
        return NaN
    m = _HEX.fullmatch(text)
    if not m or not (m.group(2) or m.group(3)):
        raise InterpError(f'not a limb: {text!r}')
    digits = m.group(2) + (m.group(3) or '')
    return canon(m.group(1) == '-', int(digits, 16), int(m.group(4)) - 4 * len(m.group(3) or ''))


def parse_mask(text):
    if text not in ('0', '1'):
        raise InterpError(f'not a mask: {text!r} (a mask is 0 or 1)')
    return text == '1'


def format_mask(m):
    return '1' if m else '0'


def format_limb(v):
    if v[0] == NAN:
        return 'nan'
    if v[0] == INF:
        return '-inf' if v[1] else 'inf'
    sign = '-' if v[1] else ''
    m, e = v[2], v[3]
    if m == 0:
        return sign + '0x0p+0'
    bits = m.bit_length() - 1             # bits after the leading one
    if bits == 0:
        return f'{sign}0x1p{e:+d}'
    digits = (bits + 3) // 4
    frac = (m - (1 << bits)) << (4 * digits - bits)
    return f'{sign}0x1.{frac:0{digits}x}p{e + bits:+d}'


# ---------------------------------------------------------------------------------------------
# Kernels.

class Machine:
    """Evaluates kernels. fused: how muladd executes. consteval: as in C++ constant evaluation,
    where a kernel with a variant runs the variant, prod is a plain product, muladd is unfused,
    and a kernel without a variant must contain no fused operation at all."""

    def __init__(self, kernels, fused=True, consteval=False):
        self.kernels, self.fused, self.consteval = kernels, fused and not consteval, consteval
        self._consts = {}

    def run(self, name, f, inputs):
        k = self.kernels.get(name)
        if k is None:
            raise InterpError(f'unknown kernel {name!r}')
        if len(inputs) != len(k.input_limbs):
            raise InterpError(f'{name} takes {len(k.input_limbs)} limbs, not {len(inputs)}')
        for v, kind in zip(inputs, k.input_kinds):
            if kind == ir.MASK:
                if not isinstance(v, bool):
                    raise InterpError(f'{name}: a mask operand is true or false, not {v!r}')
            elif isinstance(v, bool) or not member(f, v):
                raise InterpError(f'{format_limb(v) if not isinstance(v, bool) else v} is not a '
                                  f'number of format {f.name}')
        in_variant = False
        if self.consteval:
            if k.ce_variant:
                k, in_variant = self.kernels[k.ce_variant], True
            else:
                fused = [p.dst for p in ir.prims(k, self.kernels) if p.op in ir.FUSED]
                if fused:
                    raise InterpError(f'{name} has no constant-evaluation path: {fused[0]} is a '
                                      'fused operation and the kernel names no variant')
        return self._eval(k, f, list(inputs), in_variant)

    def _const(self, f, name):
        if name == 'inf':
            return (INF, False)
        if name == 'nan':
            return NaN
        key = (f, name)
        if key not in self._consts:
            try:
                x = consts.value(name, self.kernels, f.p, f.qmin, f.qmax)
            except consts.ConstError as e:
                raise InterpError(f'constant {name} in format {f.name}: {e}')
            v = canon(False, x.numerator, 0) if x.denominator == 1 else \
                canon(False, x.numerator, -(x.denominator.bit_length() - 1))
            if not member(f, v):
                raise InterpError(f'constant {name} is not a number of format {f.name}')
            self._consts[key] = v
        return self._consts[key]

    def _eval(self, k, f, args, in_variant):
        env = dict(zip(k.input_limbs, args))
        for st in k.body:
            a = [self._const(f, x.name) if x.const else env[x.name] for x in st.args]
            if st.is_call:
                env.update(zip(st.dsts, self._eval(self.kernels[st.op], f, a, in_variant)))
            else:
                env[st.dsts[0]] = self._op(st.op, f, a, in_variant)
        return [env[v] for v in k.output_limbs]

    def _op(self, op, f, a, in_variant):
        if op == 'add':
            return add(f, a[0], a[1])
        if op == 'sub':
            return sub(f, a[0], a[1])
        if op == 'prod':
            return mul(f, a[0], a[1]) if in_variant else fma(f, a[0], a[1], (NUM, False, 0, 0))
        if op in ('fma', 'fms', 'fnma') and in_variant:
            raise InterpError(f'{op} in a constant-evaluation variant')
        if op == 'fma':
            return fma(f, a[0], a[1], a[2])
        if op == 'fms':
            return fma(f, a[0], a[1], neg(a[2]))
        if op == 'fnma':
            return fma(f, neg(a[0]), a[1], a[2])
        if op == 'muladd':
            return fma(f, a[0], a[1], a[2]) if self.fused else add(f, mul(f, a[0], a[1]), a[2])
        if op == 'neg':
            return neg(a[0])
        if op == 'abs':
            return absolute(a[0])
        if op == 'lt':
            return lt(a[0], a[1])
        if op == 'le':
            return le(a[0], a[1])
        if op == 'eq':
            return eq(a[0], a[1])
        if op == 'and':
            return a[0] and a[1]
        if op == 'or':
            return a[0] or a[1]
        if op == 'not':
            return not a[0]
        if op == 'select':
            return a[1] if a[0] else a[2]
        if op == 'succ':
            return succ(f, a[0])
        if op == 'pred':
            return pred(f, a[0])
        if op == 'copy':
            return a[0]
        if op == 'guard':
            return add(f, a[0], (NUM, False, 0, 0))    # RN(a + 0): -0 becomes +0
        raise InterpError(f'the interpreter does not evaluate {op}')


# ---------------------------------------------------------------------------------------------
# The line protocol (architecture.md, "The line protocol").

def complete(machine, line, formats):
    """The completed line for one request line (without its line terminator)."""
    fields = line.split(' ')
    if fields and fields[-1].startswith('#'):
        fields = fields[:-1]
    if len(fields) < 2 or '' in fields:
        raise InterpError('expected "KERNEL FORMAT LIMB ... [#TAG]", fields separated by single spaces')
    name, fmt = fields[0], fields[1]
    if fmt not in formats:
        formats[fmt] = parse_format(fmt)
    k = machine.kernels.get(name)
    if k is None:
        raise InterpError(f'unknown kernel {name!r}')
    if len(fields) - 2 != len(k.input_limbs):
        raise InterpError(f'{name} takes {len(k.input_limbs)} limbs, not {len(fields) - 2}')
    ins = [parse_mask(t) if kind == ir.MASK else parse_limb(t) for t, kind in zip(fields[2:], k.input_kinds)]
    out = machine.run(name, formats[fmt], ins)
    return line + ' -> ' + ' '.join(format_mask(v) if kind == ir.MASK else format_limb(v)
                                    for v, kind in zip(out, k.output_kinds))


def serve(machine, infile, outfile, errfile):
    """Completes every request of infile; copies comments and empty lines. Returns an exit status."""
    formats = {}
    for lineno, raw in enumerate(infile, 1):
        line = raw[:-1] if raw.endswith('\n') else raw
        line = line[:-1] if line.endswith('\r') else line
        if not line or line.startswith('#'):
            outfile.write(line + '\n')
            continue
        try:
            outfile.write(complete(machine, line, formats) + '\n')
        except InterpError as e:
            outfile.flush()
            errfile.write(f'kairn-gen interp: line {lineno}: {e}\n')
            return 2
    return 0
