#!/usr/bin/env python3
"""Exact scaling of a ball by a power of two, the public steps on every input, and the two
executions of an opaque product.

Statements judged (milestone2.md, "Scaling a ball by a power of two", "Building blocks"):

  ball_mul_pow2_1, ball_mul_pow2_2 (c a positive power of two, cx normalized, rx >= 0)
      containment: c x is within rz of cz for every x within rx of cx;
      exactness: when the scaled last nonzero limb of the center is above N = eta / (2u) (or the
      center is zero) and c rx is above N (or rx is zero), then cz = c cx and rz = c rx exactly;
      otherwise rz <= c rx + (what the two steps add), reported in units of eta.
  next_up, next_down on every value of a format: the table of the page.
  The opaque product prod(a, b) is fma(a, b, +0) at run time and a * b in constant evaluation:
      the two differ only in the sign of an exactly zero product. Counted, for rmul, mul_pow2_2
      and ball_mul_pow2_k: operands on which the two executions give different bits.
"""
import sys
from fractions import Fraction

from common import (KERNELS, MACHINE, NINF, NaN, PINF, ZERO, eta, ext, finite_numbers, fmt, ieee_shape,
                    is_nan, normalized, normalized_pairs, num, omega, run, u_of, val)

INF = float('inf')
NZERO = ('num', True, 0, 0)


def both(name, f, *args):
    """A kernel as at run time and with every prod a plain product (constant evaluation)."""
    k = KERNELS[name]
    return MACHINE._eval(k, f, list(args), False), MACHINE._eval(k, f, list(args), True)


def powers(f):
    return [Fraction(2) ** e for e in range(f.qmin, f.qmax + f.p)]


def ball_scaling(f, k):
    N = eta(f) / (2 * u_of(f))
    centers = normalized_pairs(f) if k == 2 else [(x, Fraction(0)) for x in finite_numbers(f)]
    radii = finite_numbers(f, nonneg=True)
    if len(centers) * len(radii) * len(powers(f)) > 600000:
        step = len(centers) * len(radii) * len(powers(f)) // 600000 + 1
        centers = centers[::step]
    st = dict(n=0, exact=0, added=Fraction(0), differ=0, zero_sign=0)
    for (c0, c1) in centers:
        for r in radii:
            for c in powers(f):
                args = [num(c0), num(c1), num(r), num(c)] if k == 2 else [num(c0), num(r), num(c)]
                rt, ce = both(f'ball_mul_pow2_{k}', f, *args)
                if rt != ce:
                    st['differ'] += 1
                    same_values = all(ext(a) == ext(b) for a, b in zip(rt, ce))
                    assert same_values, (f.name, c0, c1, r, c)
                    st['zero_sign'] += 1
                if any(t[0] != 'num' for t in rt):
                    continue                                   # an overflow: the full kernel's business
                cz = sum(val(t) for t in rt[:-1])
                rz = val(rt[-1])
                cx = c0 + c1
                if k == 2:
                    assert normalized(f, val(rt[0]), val(rt[1])), (f.name, c0, c1, c)
                assert cz - rz <= c * (cx - r) and c * (cx + r) <= cz + rz, (f.name, c0, c1, r, c)
                last = c1 if c1 != 0 else c0
                clean = (c0 == 0 or abs(c * last) > N) and (r == 0 or c * r > N)
                if clean:
                    assert cz == c * cx and rz == c * r, (f.name, c0, c1, r, c, cz, rz)
                    st['exact'] += 1
                else:
                    st['added'] = max(st['added'], (rz - c * r) / eta(f))
                st['n'] += 1
    return st


def steps(f):
    """next_up and next_down (the IR's succ and pred) on every value of the format."""
    nums = finite_numbers(f)
    e, om = eta(f), omega(f)
    for i, x in enumerate(nums):
        up, down = run('add_up_1', f, num(x), ZERO), None
        got = MACHINE._op('succ', f, [num(x)], False)
        want = INF if x == om else nums[i + 1]
        assert ext(got) == want, (f.name, x)
        got = MACHINE._op('pred', f, [num(x)], False)
        want = -INF if x == -om else nums[i - 1]
        assert ext(got) == want, (f.name, x)
    table = {
        'next_up(+0)': MACHINE._op('succ', f, [ZERO], False),
        'next_up(-0)': MACHINE._op('succ', f, [NZERO], False),
        'next_up(-eta)': MACHINE._op('succ', f, [num(-e)], False),
        'next_up(Omega)': MACHINE._op('succ', f, [num(om)], False),
        'next_up(+inf)': MACHINE._op('succ', f, [PINF], False),
        'next_up(-inf)': MACHINE._op('succ', f, [NINF], False),
        'next_up(NaN)': MACHINE._op('succ', f, [NaN], False),
        'next_down(+0)': MACHINE._op('pred', f, [ZERO], False),
        'next_down(-0)': MACHINE._op('pred', f, [NZERO], False),
        'next_down(+eta)': MACHINE._op('pred', f, [num(e)], False),
        'next_down(-Omega)': MACHINE._op('pred', f, [num(-om)], False),
        'next_down(+inf)': MACHINE._op('pred', f, [PINF], False),
        'next_down(-inf)': MACHINE._op('pred', f, [NINF], False),
    }
    assert table['next_up(+0)'] == table['next_up(-0)'] == num(e)
    assert table['next_up(-eta)'] == NZERO                    # a zero, with the sign of the operand
    assert table['next_up(Omega)'] == PINF and table['next_up(+inf)'] == PINF
    assert table['next_up(-inf)'] == num(-om) and is_nan(table['next_up(NaN)'])
    assert table['next_down(+0)'] == table['next_down(-0)'] == num(-e)
    assert table['next_down(+eta)'] == ZERO
    assert table['next_down(-Omega)'] == NINF and table['next_down(-inf)'] == NINF
    assert table['next_down(+inf)'] == num(om)


def products(f):
    """The two executions of prod on every pair of values, signed zeros and infinities included,
    and of the kernels whose only fused operation is prod."""
    vals = [num(x) for x in finite_numbers(f)] + [NZERO, PINF, NINF]
    differ = zero_only = rmul_differ = 0
    for a in vals:
        for b in vals:
            rt, ce = both('mul_1_1', f, a, b)
            if rt != ce:
                differ += 1
                x, y = rt[0], ce[0]
                assert not is_nan(x) and not is_nan(y) and ext(x) == ext(y) == 0, (f.name, a, b)
                zero_only += 1
            if a[0] == 'num' and b[0] == 'num' and not a[1] and not b[1] or \
               (ext(a) == 0 or not a[1]) and (ext(b) == 0 or not b[1]):
                # the domain of rmul: nonnegative operands, a zero of either sign included
                rt, ce = both('rmul', f, a, b)
                same = rt == ce or (is_nan(rt[0]) and is_nan(ce[0]))
                rmul_differ += not same
    pow_differ = pow_values = 0
    for (x0, x1) in normalized_pairs(f)[::3]:
        for c in powers(f):
            for s0 in (num(x0), NZERO if x0 == 0 else num(x0)):
                rt, ce = both('mul_pow2_2', f, s0, num(x1), num(c))
                if rt != ce:
                    pow_differ += 1
                    pow_values += any(ext(p) != ext(q) for p, q in zip(rt, ce))
    return differ, zero_only, rmul_differ, pow_differ, pow_values


def main():
    for f in (ieee_shape(2, 1), ieee_shape(3, 1), ieee_shape(4, 1), fmt(3, -6, 0)):
        steps(f)
        d, z, rm, pd, pv = products(f)
        print(f'{f.name:12} prod as fma and as a plain product differ on {d} operand pairs, all of them '
              f'exact zeros of different signs: {z == d}; rmul differs on {rm}; mul_pow2_2 differs on '
              f'{pd} (in a value: {pv})')
        for k in (1, 2):
            if k == 2 and f.p < 2:
                continue
            st = ball_scaling(f, k)
            print(f'             ball_mul_pow2_{k}: {st["n"]} finite cases, {st["exact"]} exact; otherwise '
                  f'rz - c rx <= {float(st["added"]):.2f} eta; the two executions differ on '
                  f'{st["differ"]} (always only in the sign of a zero)')
    print('every statement held')


if __name__ == '__main__':
    sys.exit(main())
