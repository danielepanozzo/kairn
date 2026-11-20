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
    where a kernel with a variant runs the variant, prod is a plain product (also in a kernel
    without a variant: the rule of the product), muladd is unfused, guard returns its operand, and
    a kernel without a variant must contain no fused operation but prod."""

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
        # plain: every prod is the plain product, as in constant evaluation.
        plain = False
        if self.consteval:
            if k.ce_variant:
                k = self.kernels[k.ce_variant]
            else:
                fused = [p.dst for p in ir.prims(k, self.kernels) if p.op in ir.FUSED - {'prod'}]
                if fused:
                    raise InterpError(f'{name} has no constant-evaluation path: {fused[0]} is a '
                                      'fused operation other than prod and the kernel names no variant')
            plain = True
        return self._eval(k, f, list(inputs), plain)

    def run_fold(self, name, f, order, lanes, arrays, scalars=()):
        """The outputs of fold `name` on the arrays: `arrays` has one list of n values per limb
        array, in the order of the fold's arrays and of their limbs (x0, x1, y0, y1). `order` is
        'sequential' or 'lanes', with `lanes` the number of lanes W >= 0 (fold_lanes W of
        proofs/theories/Folds.v; W = 0 is the sequential order). A map takes its scalars' limbs
        too, and returns one list of n values per limb array it writes, then its mask."""
        fd = getattr(self.kernels, 'folds', {}).get(name)
        if fd is None:
            raise InterpError(f'unknown fold {name!r}')
        if self.consteval:
            raise InterpError(f'{name} is a fold, which is not evaluated in constant evaluation')
        if order not in fd.orders:
            raise InterpError(f'{name} has no order {order!r}')
        limbs = fd.array_limbs()
        if len(arrays) != len(limbs):
            raise InterpError(f'{name} reads {len(limbs)} limb arrays, not {len(arrays)}')
        if fd.is_conv:
            return self._run_conv(fd, f, arrays)
        n = len(arrays[0]) if arrays else 0
        if any(len(a) != n for a in arrays):
            raise InterpError(f'{name}: the limb arrays have different lengths')
        if len(scalars) != len(fd.scalar_limbs()):
            raise InterpError(f'{name} takes {len(fd.scalar_limbs())} scalar limbs, not {len(scalars)}')
        for a in list(arrays) + [list(scalars)]:
            for v in a:
                if isinstance(v, bool) or not member(f, v):
                    raise InterpError(f'{format_limb(v) if not isinstance(v, bool) else v} is not a number '
                                      f'of format {f.name}')
        # An element is one entry of every limb array, grouped by array: {array: [limbs]}.
        elements = []
        for i in range(n):
            e, at = {}, 0
            for g in fd.arrays:
                e[g.name] = [arrays[at + j][i] for j in range(len(g.limbs))]
                at += len(g.limbs)
            elements.append(e)
        step = self.kernels[fd.step[0]]
        if fd.is_map:
            return self._run_map(fd, f, order, lanes, elements, list(scalars))
        # The zero state: every limb +0, every mask true (a fold of maxima has one of each).
        zero = [True if kind == ir.MASK else (NUM, False, 0, 0) for kind in fd.state_kinds()]
        at, parts = 0, {}
        for g in fd.states:
            parts[g.name] = (at, at + len(g.limbs))
            at += len(g.limbs)

        def apply_step(state, e):
            args = []
            for a in fd.step[1]:
                args += state[parts[a][0]:parts[a][1]] if a in parts else e[a]
            return self._eval(step, f, args, False)

        def fold_seq(xs, state):
            for e in xs:
                state = apply_step(state, e)
            return state

        if order == 'sequential':
            state = fold_seq(elements, zero)
        else:
            if lanes < 0:
                raise InterpError('the number of lanes is at least 0')
            combine = self.kernels[fd.combine[0]]
            full = lanes * (n // lanes) if lanes else 0
            # deal W: lane j holds elements j, j + W, j + 2 W, ... of the first W (n / W).
            states = [fold_seq(elements[j:full:lanes], zero) for j in range(lanes)]
            state = states[0] if states else zero
            for s in states[1:]:
                state = self._eval(combine, f, state + s, False)
            state = fold_seq(elements[full:], state)
        if fd.finish is None:
            return state
        return self._eval(self.kernels[fd.finish[0]], f, state, False)

    def _run_map(self, fd, f, order, lanes, elements, scalars):
        """A map (rules.py, "Maps"): every written element is the step on the scalars and one
        element; the mask starts true and is the `and` of the check's flag on each written element,
        in the order given (the same in both, `and` being exact, associative and commutative); when
        it is false, each written element is replaced by what the check returns of it."""
        step, check = self.kernels[fd.step[0]], self.kernels[fd.check]
        given = {}
        at = 0
        for g in fd.scalars:
            given[g.name] = scalars[at:at + len(g.limbs)]
            at += len(g.limbs)
        n = len(elements)
        written = [None] * n

        def one(i):
            e = dict(elements[i], **given)
            args = [v for a in fd.step[1] for v in e[a]]
            written[i] = self._eval(step, f, args, False)
            return self._eval(check, f, written[i], False)[-1]

        if order == 'sequential':
            mask = True
            for i in range(n):
                flag = one(i)                   # every element is written, whatever the mask
                mask = mask and flag
        else:
            if lanes < 0:
                raise InterpError('the number of lanes is at least 0')
            full = lanes * (n // lanes) if lanes else 0
            mask = True
            for j in range(lanes):
                lane = True
                for i in range(j, full, lanes):
                    flag = one(i)
                    lane = lane and flag
                mask = lane if j == 0 else (mask and lane)
            for i in range(full, n):
                flag = one(i)
                mask = mask and flag
        if not mask:
            written = [self._eval(check, f, w, False)[:-1] for w in written]
        width = len(fd.write_limbs())
        return [[w[j] for w in written] for j in range(width)] + [mask]

    def _run_conv(self, fd, f, arrays):
        """A convolution (rules.py, "Convolutions"): `arrays` the limb arrays of x, then of y, each of
        its own array's length. Coefficient j, for 0 <= j < n_x + n_y - 1 (none when an array is
        empty), is the final state of the fold of the coefficients in the sequential order on the
        terms (x_i, y_(j-i)), i from max(0, j - n_y + 1) to min(j, n_x - 1); the mask is the and of
        the check's flag on each, and when it is false each is replaced by what the check returns."""
        cf = self.kernels.folds[fd.coefficients]
        step, check = self.kernels[cf.step[0]], self.kernels[fd.check]
        gx, gy = fd.arrays
        xs, ys = arrays[:len(gx.limbs)], arrays[len(gx.limbs):]
        nx, ny = len(xs[0]), len(ys[0])
        if any(len(a) != nx for a in xs) or any(len(a) != ny for a in ys):
            raise InterpError(f'{fd.name}: the limb arrays of one array have different lengths')
        for a in arrays:
            for v in a:
                if isinstance(v, bool) or not member(f, v):
                    raise InterpError(f'{format_limb(v) if not isinstance(v, bool) else v} is not a number '
                                      f'of format {f.name}')
        nz = 0 if nx == 0 or ny == 0 else nx + ny - 1
        written, mask = [], True
        for j in range(nz):
            state = [True if kind == ir.MASK else (NUM, False, 0, 0) for kind in cf.state_kinds()]
            for i in range(max(0, j - ny + 1), min(j, nx - 1) + 1):
                e = {gx.name: [a[i] for a in xs], gy.name: [a[j - i] for a in ys], cf.state.name: state}
                state = self._eval(step, f, [v for a in cf.step[1] for v in e[a]], False)
            written.append(state)
            flag = self._eval(check, f, state, False)[-1]
            mask = mask and flag
        if not mask:
            written = [self._eval(check, f, w, False)[:-1] for w in written]
        width = len(fd.write_limbs())
        return [[w[k] for w in written] for k in range(width)] + [mask]

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

    def _eval(self, k, f, args, plain):
        """The outputs of kernel k on args; with `plain`, every prod is the plain product a * b
        (constant evaluation) and no other fused operation may occur."""
        env = dict(zip(k.input_limbs, args))
        for st in k.body:
            a = [self._const(f, x.name) if x.const else env[x.name] for x in st.args]
            if st.is_call:
                env.update(zip(st.dsts, self._eval(self.kernels[st.op], f, a, plain)))
            else:
                env[st.dsts[0]] = self._op(st.op, f, a, plain)
        return [env[v] for v in k.output_limbs]

    def _op(self, op, f, a, plain):
        if op == 'add':
            return add(f, a[0], a[1])
        if op == 'sub':
            return sub(f, a[0], a[1])
        if op == 'prod':
            return mul(f, a[0], a[1]) if plain else fma(f, a[0], a[1], (NUM, False, 0, 0))
        if op in ('fma', 'fms', 'fnma') and plain:
            raise InterpError(f'{op} in constant evaluation')
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
            # RN(a + 0): -0 becomes +0. Constant evaluation fuses nothing, and the guard is not
            # evaluated there: the operand comes out unchanged (cpp.py emits it so).
            return a[0] if self.consteval else add(f, a[0], (NUM, False, 0, 0))
        if op == 'times_inf':
            return mul(f, a[0], (INF, False))           # exact: NaN for a NaN or a zero
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
    fd = getattr(machine.kernels, 'folds', {}).get(name)
    if fd is not None:
        return line + ' -> ' + complete_fold(machine, fd, formats[fmt], fields[2:])
    k = machine.kernels.get(name)
    if k is None:
        raise InterpError(f'unknown kernel {name!r}')
    if len(fields) - 2 != len(k.input_limbs):
        raise InterpError(f'{name} takes {len(k.input_limbs)} limbs, not {len(fields) - 2}')
    ins = [parse_mask(t) if kind == ir.MASK else parse_limb(t) for t, kind in zip(fields[2:], k.input_kinds)]
    out = machine.run(name, formats[fmt], ins)
    return line + ' -> ' + ' '.join(format_mask(v) if kind == ir.MASK else format_limb(v)
                                    for v, kind in zip(out, k.output_kinds))


def parse_order(text):
    """('sequential', 0) for `seq`, ('lanes', W) for `lanes:W` (architecture.md, "The line
    protocol", arrays)."""
    if text == 'seq':
        return 'sequential', 0
    m = re.fullmatch(r'lanes:(0|[1-9][0-9]*)', text)
    if not m:
        raise InterpError(f'not an order: {text!r} (seq, or lanes:W with W a decimal number of lanes)')
    return 'lanes', int(m.group(1))


def complete_fold(machine, fd, f, fields):
    """The output fields of a request of a fold: ORDER N, then the limbs of the scalars (a map),
    then for each array of the fold in order, for each of its limbs, the N entries of that limb
    array. A map's result is, for each limb of the array it writes, its N entries, then the mask."""
    if fd.is_conv:
        return complete_conv(machine, fd, f, fields)
    if len(fields) < 2:
        raise InterpError(f'expected "{fd.name} FORMAT ORDER N LIMB ... [#TAG]"')
    order, lanes = parse_order(fields[0])
    if not re.fullmatch(r'0|[1-9][0-9]*', fields[1]):
        raise InterpError(f'not a length: {fields[1]!r} (a decimal number)')
    n = int(fields[1])
    limbs, given = fd.array_limbs(), len(fd.scalar_limbs())
    if len(fields) - 2 != given + n * len(limbs):
        raise InterpError(f'{fd.name} of length {n} takes {given + n * len(limbs)} limbs ({given} of its scalars, '
                          f'{len(limbs)} arrays of {n}), not {len(fields) - 2}')
    values = [parse_limb(t) for t in fields[2:]]
    scalars, values = values[:given], values[given:]
    arrays = [values[i * n:(i + 1) * n] for i in range(len(limbs))]
    out = machine.run_fold(fd.name, f, order, lanes, arrays, scalars)
    if fd.is_map:
        written = [format_limb(v) for a in out[:-1] for v in a]
        return ' '.join(written + [format_mask(out[-1])])
    kinds = [g.kind for g in fd.results() for _ in g.limbs]
    return ' '.join(format_mask(v) if kind == ir.MASK else format_limb(v) for v, kind in zip(out, kinds))


def complete_conv(machine, fd, f, fields):
    """The output fields of a request of a convolution (architecture.md, "The line protocol"):
    ORDER (seq), N_X, N_Y, then the N_X entries of each limb array of x and the N_Y entries of each
    of y; the result, the n_x + n_y - 1 entries (none when a length is 0) of each limb array
    written, then the mask."""
    if len(fields) < 3:
        raise InterpError(f'expected "{fd.name} FORMAT seq N_X N_Y LIMB ... [#TAG]"')
    order, _ = parse_order(fields[0])
    if order != 'sequential':
        raise InterpError(f'{fd.name} has the sequential order only (seq)')
    for t in fields[1:3]:
        if not re.fullmatch(r'0|[1-9][0-9]*', t):
            raise InterpError(f'not a length: {t!r} (a decimal number)')
    nx, ny = int(fields[1]), int(fields[2])
    gx, gy = fd.arrays
    want = nx * len(gx.limbs) + ny * len(gy.limbs)
    if len(fields) - 3 != want:
        raise InterpError(f'{fd.name} of lengths {nx} and {ny} takes {want} limbs, not {len(fields) - 3}')
    values = [parse_limb(t) for t in fields[3:]]
    arrays = [values[i * nx:(i + 1) * nx] for i in range(len(gx.limbs))]
    rest = values[nx * len(gx.limbs):]
    arrays += [rest[i * ny:(i + 1) * ny] for i in range(len(gy.limbs))]
    out = machine.run_fold(fd.name, f, 'sequential', 0, arrays)
    return ' '.join([format_limb(v) for a in out[:-1] for v in a] + [format_mask(out[-1])])


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
