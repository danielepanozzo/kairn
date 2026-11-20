#!/usr/bin/env python3
"""The constants of the page in binary64 and binary32, computed exactly.

For the directed sums and products of two limbs: A and B of the closed form
    v - l <= A |v| + B      (directed_2.py),
with E, G, H the constants of ball_add_2 and ball_mul_2 as the generator rounds them up. Also
the threshold of the underflow band of the one-limb directed products, 2^(2p-1) eta.
"""
import sys
from fractions import Fraction

from common import eta, interp, u_of
from directed_2 import bound_parts


def log2(x):
    """log2 of a positive rational, as a float (exact for the powers of two that matter)."""
    n, d = x.numerator, x.denominator
    shift = n.bit_length() - d.bit_length()
    y = x / Fraction(2) ** shift
    import math
    return shift + math.log2(float(y))


def main():
    for name in ('binary64', 'binary32'):
        f = interp.parse_format(name)
        u, e = u_of(f), eta(f)
        N = e / (2 * u)
        print(f'{name}: u = 2^{-f.p}, eta = 2^{f.qmin}, smallest normal N = 2^{f.qmin + f.p - 1}, '
              f'band of the directed products below 2^{2 * f.p - 1 + f.qmin}')
        for op, c in (('add', 3), ('mul', 4)):
            E, G, H, A, B = bound_parts(f, op)
            print(f'  {op}: E = {float(E / u ** 2):.15f} u^2, G = 1 + {float((G - 1) / u):.1f} u, '
                  f'H = N + {float((H - N) / e):.1f} eta')
            print(f'       A = {float(A / u ** 2):.15f} u^2 (2c + 2 = {2 * c + 2}; A / u^2 - (2c + 2) = '
                  f'{float(A / u ** 2 - (2 * c + 2)):.3e}),  B = {float(B / N):.15f} N = 2^{log2(B):.4f}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
