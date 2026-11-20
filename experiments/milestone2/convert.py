#!/usr/bin/env python3
"""Conversions between limbs of a wide format W and of a narrow format N (double and float in
the library), on toy formats in which every number of N is a number of W.

The IR has one format per kernel, so these are not kernel descriptions: each conversion is
written here with the interpreter's operations in the two formats and a conversion that rounds
to nearest (what a C++ cast does). u and eta are those of N; uw is the u of W.

Statements judged (milestone2.md, "Limbs of another type"):

  N1  wide, one limb -> narrow, two limbs:   f0 = RN_N(x); r = x - f0 is exact in W; f1 = RN_N(r);
      z = Fast2Sum_N(f0, f1) is normalized and |x - z| <= u^2 |x| + eta / 2;
  N2  wide, two limbs -> narrow, two limbs:  f0 = RN_N(x0); r = RN_W((x0 - f0) + x1); f1 = RN_N(r);
      z = Fast2Sum_N(f0, f1) is normalized and |x - z| <= (u + uw)^2 / (1 - uw) |x| + eta / 2;
      a value beyond the range of N gives an infinite f0 (the full form returns (+-inf, 0));
  W1  narrow, two limbs -> wide, two limbs:  Fast2Sum_W(f0, f1) is normalized in W, and exact;
  B1  a ball: the center by N2, the radius rounded up to N and grown by the bound of N2 in its
      computed-value form, evaluated in N as a Ball radius of the second design:
      the narrow ball contains the wide one.
"""
import random
import sys
from fractions import Fraction

from common import (eta, ext, fmt, interp, normalized, normalized_pairs, num, omega, rn, ru, u_of, val)


def narrow(n, v):
    """RN to the narrow format of a finite wide value (an interpreter value)."""
    x = rn(n, val(v))
    if abs(x) == float('inf'):
        return (interp.INF, x < 0)
    return num(x)


def fast_two_sum(f, a, b):
    s = interp.add(f, a, b)
    z = interp.sub(f, s, a)
    return s, interp.sub(f, b, z)


def to_narrow_2(w, n, x0, x1):
    f0 = narrow(n, x0)
    if f0[0] != 'num':
        return (f0, None), None
    d = interp.sub(w, x0, f0)                      # exact: checked by the caller
    r = interp.add(w, d, x1)
    f1 = narrow(n, r)
    return fast_two_sum(n, f0, f1), d


def up_const(n, x):
    return num(ru(n, x))


def main():
    rng = random.Random(20261119)
    for (pw, qw, tw), (pn, qn, tn) in (((7, -22, 2), (3, -8, 1)), ((9, -24, 0), (4, -10, 0)),
                                       ((6, -18, 2), (3, -8, 2))):
        w, n = fmt(pw, qw, tw + 8), fmt(pn, qn, tn)
        src = fmt(pw, qw, tw)
        u, uw, e = u_of(n), u_of(w), eta(n)
        pairs = normalized_pairs(src)
        if len(pairs) > 60000:
            pairs = rng.sample(pairs, 60000)
        rel2 = (u + uw) ** 2 / (1 - uw)
        st = dict(n=0, over=0, n1=Fraction(0), n2=Fraction(0), balls=0)
        # The constants of the radius, in N: E turns the relative part into a multiple of |z0|
        # (with 1 + u for the second limb), G and H are those of ball_scale_2's form.
        V = e / 2 / (1 - rel2)
        E = up_const(n, rel2 / (1 - rel2) * (1 + u))
        G = up_const(n, (1 + u) ** 3)
        H = up_const(n, (1 + u) * ((1 + u) ** 2 * e + V + e / 2) + e / (2 * u))
        for x0, x1 in pairs:
            x = x0 + x1
            (z0, z1), d = to_narrow_2(w, n, num(x0), num(x1))
            if z1 is None:
                assert abs(x0) >= omega(n), (w.name, n.name, x0)
                st['over'] += 1
                continue
            assert val(d) == x0 - val(narrow(n, num(x0))), (w.name, n.name, x0)          # exact
            if z0[0] != 'num':
                # The renormalization itself overflowed: f0 is the largest number of N and the
                # second limb reaches half its gap. The value is beyond the range of N.
                assert abs(x) > omega(n), (w.name, n.name, x0, x1)
                st['over'] += 1
                continue
            z = val(z0) + val(z1)
            assert normalized(n, val(z0), val(z1)), (w.name, n.name, x0, x1)
            bound = rel2 * abs(x) + e / 2
            assert abs(x - z) <= bound, (w.name, n.name, x0, x1, z)
            st['n2'] = max(st['n2'], abs(x - z) / bound)
            if x1 == 0:
                b1 = u * u * abs(x) + e / 2
                assert abs(x - z) <= b1, (w.name, n.name, x0)
                st['n1'] = max(st['n1'], abs(x - z) / b1)
            # W1: back to the wide format, exactly.
            s, t = fast_two_sum(w, z0, z1)
            assert val(s) + val(t) == z and normalized(w, val(s), val(t)), (w.name, n.name, x0, x1)
            # B1: a ball of center x and a radius of W.
            if st['n'] % 7 == 0:
                r = abs(rng.choice(pairs)[0]) * rng.choice((Fraction(0), uw, u, Fraction(1, 4)))
                rup = ru(n, r)
                if rup == float('inf'):
                    continue
                t1 = interp.fma(n, interp.absolute(z0), E, num(rup))
                rz = interp.fma(n, t1, G, H)
                if rz[0] != 'num':
                    continue
                assert z - val(rz) <= x - r and x + r <= z + val(rz), (w.name, n.name, x0, x1, r)
                st['balls'] += 1
            st['n'] += 1
        print(f'W = {src.name}, N = {n.name}: {st["n"]} conversions of two limbs ({st["over"]} beyond the '
              f'range of N); largest error over the bound: one wide limb {float(st["n1"]):.3f}, two wide '
              f'limbs {float(st["n2"]):.3f}; {st["balls"]} balls contained')
    print('every statement held')


if __name__ == '__main__':
    sys.exit(main())
