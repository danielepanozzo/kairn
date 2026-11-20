"""Shared by the experiments of this directory.

The kernels proposed in docs/developer/design/milestone2.md are written as kernel descriptions in
kernels/, in the generator's own format, and evaluated by the generator's exact interpreter
(gen/kairn_gen/interp.py) together with the kernels of gen/kernels. Every statement is then judged
here with Python's exact rationals, by code that shares nothing with the interpreter but the
representation of a value.

Nothing in this directory is library code, and nothing here is generated into the library.
"""
import itertools
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(ROOT, 'gen'))

from kairn_gen import consts, interp, ir, rules  # noqa: E402

NUM, INF, NAN = interp.NUM, interp.INF, interp.NAN
PINF, NINF, NaN = (INF, False), (INF, True), (NAN,)
ZERO = (NUM, False, 0, 0)


def load():
    """The kernels of gen/kernels and those of this directory's kernels/, as one set."""
    kernels = {}
    for directory in (os.path.join(ROOT, 'gen', 'kernels'), os.path.join(HERE, 'kernels')):
        for fn in sorted(os.listdir(directory)):
            if fn.endswith('.kernel'):
                with open(os.path.join(directory, fn), encoding='utf-8') as f:
                    k = ir.parse_kernel(f.read(), fn)
                if k.name in kernels:
                    raise SystemExit(f'{fn}: kernel {k.name} is defined twice')
                kernels[k.name] = k
    return ir.ordered(kernels)


KERNELS = load()
MACHINE = interp.Machine(KERNELS)


def fmt(p, qmin, qmax):
    return interp.Format(f'fp:{p}:{qmin}:{qmax}', p, qmin, qmax)


def ieee_shape(p, qmax):
    """The format of precision p and largest exponent qmax with qmin + qmax = 3 - 2p, the shape of
    binary32 and binary64, which the IEEE-model theorems are about."""
    return fmt(p, 3 - 2 * p - qmax, qmax)


def run(name, f, *args):
    """A kernel on values; a 2-limb operand is passed as its two limbs."""
    out = MACHINE.run(name, f, list(args))
    return out[0] if len(out) == 1 else tuple(out)


# ---------------------------------------------------------------------------------------------
# Values and exact rationals.

def val(v):
    """The exact value of a finite number."""
    assert v[0] == NUM, v
    x = Fraction(v[2]) * Fraction(2) ** v[3]
    return -x if v[1] else x


def is_fin(v):
    return v[0] == NUM


def is_nan(v):
    return v[0] == NAN


def ext(v):
    """A value as an extended real: a Fraction, or float('inf'), float('-inf'); None for a NaN."""
    if v[0] == NAN:
        return None
    if v[0] == INF:
        return float('-inf') if v[1] else float('inf')
    return val(v)


def num(x):
    """The interpreter's value of an exact dyadic rational."""
    x = Fraction(x)
    if x == 0:
        return ZERO
    d = x.denominator
    assert d & (d - 1) == 0, x
    return interp.canon(x < 0, abs(x.numerator), -(d.bit_length() - 1))


def finite_numbers(f, nonneg=False):
    """Every finite number of the format, as exact rationals, in increasing order."""
    out = {Fraction(0)}
    for q in range(f.qmin, f.qmax + 1):
        for m in range(1, 2 ** f.p):
            out.add(Fraction(m) * Fraction(2) ** q)
    pos = sorted(out)
    return pos if nonneg else sorted([-x for x in pos if x] + pos)


def eta(f):
    return Fraction(2) ** f.qmin


def u_of(f):
    return Fraction(1, 2 ** f.p)


def omega(f):
    return (2 ** f.p - 1) * Fraction(2) ** f.qmax


def is_member(f, x):
    """Whether the rational x is a finite number of the format."""
    if x == 0:
        return True
    x = abs(Fraction(x))
    if x > omega(f):
        return False
    t = x / eta(f)
    if t.denominator != 1:
        return False
    n = t.numerator                          # x = n eta
    tz = (n & -n).bit_length() - 1
    return (n >> tz).bit_length() <= f.p and n.bit_length() - f.p <= f.qmax - f.qmin


def quantum(f, x):
    """The spacing of the format's numbers in the binade of |x| (ulp), for x != 0."""
    x = abs(Fraction(x))
    e = x.numerator.bit_length() - x.denominator.bit_length()
    if Fraction(2) ** e > x:
        e -= 1
    return Fraction(2) ** max(e - f.p + 1, f.qmin)


def rd(f, x):
    """The largest finite number of the format <= x, or -inf when x < -Omega (exact rationals)."""
    x = Fraction(x)
    if x < -omega(f):
        return float('-inf')
    if x > omega(f):
        return omega(f)
    if x == 0:
        return Fraction(0)
    q = quantum(f, x)
    m = (x / q).numerator // (x / q).denominator          # floor
    return m * q


def ru(f, x):
    r = rd(f, -Fraction(x))
    return -r


def rn(f, x):
    """Round to nearest, ties to even, with the overflow rule: +-inf when the rounding in
    unbounded range reaches 2^(qmax + p)."""
    x = Fraction(x)
    if x == 0:
        return Fraction(0)
    s = -1 if x < 0 else 1
    a = abs(x)
    q = quantum(f, a)
    t = a / q
    m = t.numerator // t.denominator
    r = t - m
    if r > Fraction(1, 2) or (r == Fraction(1, 2) and m % 2 == 1):
        m += 1
    y = m * q
    if y >= Fraction(2) ** (f.qmax + f.p):
        return s * float('inf')
    return s * y


def succ(f, x):
    """The next number of the format above the format number x (inf above Omega)."""
    if x == omega(f):
        return float('inf')
    if x >= 0:
        return x + (quantum(f, x) if x else eta(f))
    return -pred_pos(f, -x)


def pred_pos(f, x):
    q = quantum(f, x)
    if x == Fraction(2) ** (x.numerator.bit_length() - x.denominator.bit_length()) and q > eta(f):
        if (x / q).numerator == 2 ** (f.p - 1):
            return x - q / 2
    return x - q


def pred(f, x):
    return -succ(f, -x)


def normalized(f, x0, x1):
    """x0 = RN(x0 + x1), for exact rationals of the format."""
    return rn(f, x0 + x1) == x0


def normalized_pairs(f, limit=None, nonneg=False, lead_min=None):
    """Every normalized pair (x0, x1) of the format with x0 finite, as rationals. With a limit, an
    evenly spread sample of about that many. With lead_min, only the pairs whose leading limb is at
    least that large in magnitude."""
    nums = finite_numbers(f)
    pairs = []
    for x0 in nums:
        if nonneg and x0 < 0:
            continue
        if lead_min is not None and abs(x0) < lead_min:
            continue
        if x0 == 0:
            pairs.append((x0, Fraction(0)))
            continue
        h = quantum(f, x0) / 2
        for x1 in nums:
            if abs(x1) <= h and normalized(f, x0, x1):
                pairs.append((x0, x1))
    if limit and len(pairs) > limit:
        step = len(pairs) / limit
        pairs = [pairs[int(i * step)] for i in range(limit)]
    return pairs


def const(f, text):
    """The value of a kernel constant `up(EXPR)` in the format, as a rational."""
    return consts.value(f'up({text})', KERNELS, f.p, f.qmin, f.qmax)


def rule_report(names):
    """What the generator's rules say of the experiment's kernels (they are not required to pass:
    the claims of this milestone need vocabulary the generator does not have yet)."""
    errors = rules.check_all(KERNELS)
    return [str(e) for e in errors if getattr(e, 'kernel', None) in names]


def product(*iterables):
    return itertools.product(*iterables)
