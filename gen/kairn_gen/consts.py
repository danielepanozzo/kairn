"""The exact value of every constant a kernel can name, in a format (p, qmin, qmax).

- `splitter`: ir.CONSTANTS, a function of p.
- `0`: the literal zero, +0.
- `unit_computed(K)`, `tiny_computed(K)` (architecture.md, "Claims of the second wave"): K's bound
  |output - value| <= unit |value| + tiny, with unit = c u^k and tiny = t eta from K's error entry,
  turned into one relative to the computed output: unit / (1 - unit) and tiny / (1 - unit), each
  rounded up to a number of the format. A ball kernel's radius adds them to cover the error of its
  center. They are computed here with integers and fractions only, for any format, so that the
  C++ literals, the interpreter and the tests use the same numbers; the Rocq model states the same
  definition over the reals (rocq.py).
"""
from fractions import Fraction

from . import expr, ir


class ConstError(Exception):
    pass


def source_bound(k):
    """The error entry of K that its computed constants come from: the only one, of form R and
    without a condition. Raises ConstError otherwise."""
    errors = [e for e in k.ensures if e['kind'] == 'error']
    if len(errors) != 1:
        raise ConstError(f'{k.name} has {len(errors)} error entries; its computed constants need '
                         'exactly one')
    e = errors[0]
    if e['form'] != 'R' or e['when'] is not None:
        raise ConstError(f'the error entry of {k.name} must be of form R and unconditional to give '
                         'computed constants')
    return e


def round_up(x, p, qmin, qmax):
    """The smallest number of the format not below x >= 0, or None when there is none (overflow)."""
    if x == 0:
        return Fraction(0)
    e = x.numerator.bit_length() - x.denominator.bit_length()   # 2^(e-1) < x < 2^(e+1)
    if Fraction(2) ** e > x:
        e -= 1                                                 # now 2^e <= x < 2^(e+1)
    q = max(e - p + 1, qmin)                                   # the quantum of numbers near x
    scale = Fraction(2) ** q
    t = x / scale
    m = -((-t.numerator) // t.denominator)                     # ceil: a carry to 2^p is still exact
    if m * scale > (2 ** p - 1) * Fraction(2) ** qmax:
        return None
    return m * scale


def computed(fn, k, p, qmin, qmax):
    """unit_computed(K) or tiny_computed(K) in format (p, qmin, qmax), as a Fraction."""
    e = source_bound(k)
    if k.min_precision is not None and p < k.min_precision:
        raise ConstError(f'{fn}({k.name}) is not defined for precision {p}: the claims of '
                         f'{k.name} hold from precision {k.min_precision} on')
    u = Fraction(1, 2 ** p)
    try:
        unit = expr.evaluate(expr.parse(e['c']), {'u': u}) * u ** e['k']
        tiny = expr.evaluate(expr.parse(e['t']), {}) * Fraction(2) ** qmin
    except expr.ExprError as err:
        raise ConstError(f'{fn}({k.name}) at precision {p}: {err}')
    if not 0 <= unit < 1 or tiny < 0:
        raise ConstError(f'{fn}({k.name}) at precision {p}: needs 0 <= unit < 1 and tiny >= 0')
    v = round_up((unit if fn == 'unit_computed' else tiny) / (1 - unit), p, qmin, qmax)
    if v is None:
        raise ConstError(f'{fn}({k.name}) overflows the format ({p}, {qmin}, {qmax})')
    return v


def value(name, kernels, p, qmin, qmax):
    """The exact value of constant `name` in format (p, qmin, qmax), as a Fraction."""
    if name == ir.ZERO:
        return Fraction(0)
    if name in ir.CONSTANTS:
        v = Fraction(ir.CONSTANTS[name](p))
        if round_up(v, p, qmin, qmax) != v:
            raise ConstError(f'constant {name} = {v} is not a number of the format ({p}, {qmin}, {qmax})')
        return v
    c = ir.computed(name)
    if c is None or c[1] not in kernels:
        raise ConstError(f'unknown constant {name!r}')
    return computed(c[0], kernels[c[1]], p, qmin, qmax)
