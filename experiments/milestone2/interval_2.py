#!/usr/bin/env python3
"""Interval<T, 2>: sum and product on samples of canonical intervals with 2-limb bounds, in
formats of the shape of binary64 (bounded, unbounded and empty operands; overflow included).

Statements judged (milestone2.md, "Interval kernels"), for canonical operands X and Y:

  I1  the result is canonical: each bound is a finite normalized pair or (+-inf, 0); it is the
      empty set ((+inf, 0), (-inf, 0)) or zl <= zu with zl < +inf and zu > -inf;
  I2  it is empty exactly when an operand is;
  I3  it contains x o y for every real x in X and y in Y, unbounded operands included;
  I4  for bounded operands and a bounded result, with [lo, hi] the exact range:
      lo - zl <= A |lo| + B and zu - hi <= A |hi| + B, the closed form of directed_2.py;
  I5  for bounded operands, the result is bounded when no member of the exact range exceeds
      2^(emax - 2) in magnitude (a quarter of the overflow threshold). Measured as well: the
      smallest magnitude of the exact range at which a bound was infinite.
"""
import random
import sys
from fractions import Fraction

from common import (NINF, PINF, ZERO, eta, ext, ieee_shape, is_nan, normalized, normalized_pairs, num,
                    run, val)
from directed_2 import bound_parts

INF = float('inf')
EMPTY = (INF, -INF)


def value2(x):
    """A bound (a normalized pair of rationals, or an infinity) as two interpreter values."""
    if x == INF:
        return PINF, ZERO
    if x == -INF:
        return NINF, ZERO
    return num(x[0]), num(x[1])


def exact(x):
    return x if x in (INF, -INF) else x[0] + x[1]


def canonical_bound(f, z0, z1):
    if is_nan(z0) or is_nan(z1):
        return False
    if z0[0] == 'inf':
        return ext(z1) == 0
    return z1[0] == 'num' and normalized(f, val(z0), val(z1))


def bound_value(z0, z1):
    return ext(z0) if z0[0] == 'inf' else val(z0) + val(z1)


def hull_product(f, X, Y):
    big = Fraction(2) ** (4 * (f.qmax + f.p) - 4 * f.qmin + 8)
    far = big * eta(f) ** 2 / 2

    def proxy(t):
        return big if t == INF else -big if t == -INF else t
    corners = [proxy(a) * proxy(b) for a in X for b in Y]
    lo, hi = min(corners), max(corners)
    return (-INF if lo < -far else lo), (INF if hi > far else hi)


def check(f, op, X, Y, A, B, st):
    args = value2(X[0]) + value2(X[1]) + value2(Y[0]) + value2(Y[1])
    zl0, zl1, zu0, zu1 = run(f'interval_{op}_2', f, *args)
    assert canonical_bound(f, zl0, zl1) and canonical_bound(f, zu0, zu1), (f.name, op, X, Y)
    Z = (bound_value(zl0, zl1), bound_value(zu0, zu1))
    assert Z == EMPTY or (Z[0] <= Z[1] and Z[0] < INF and Z[1] > -INF), (f.name, op, X, Y, Z)   # I1
    ex = (exact(X[0]), exact(X[1]))
    ey = (exact(Y[0]), exact(Y[1]))
    empty = ex == EMPTY or ey == EMPTY
    assert (Z == EMPTY) == empty, (f.name, op, X, Y, Z)                                        # I2
    if empty:
        return
    lo, hi = (ex[0] + ey[0], ex[1] + ey[1]) if op == 'add' else hull_product(f, ex, ey)
    assert Z[0] <= lo and hi <= Z[1], (f.name, op, X, Y, Z, lo, hi)                             # I3
    st['n'] += 1
    if any(abs(t) == INF for t in ex + ey):
        # The infinite bounds of the exact range are returned as such.
        assert (lo != -INF or Z[0] == -INF) and (hi != INF or Z[1] == INF)
        st['unbounded_operands'] += 1
        return
    mag = max(abs(lo), abs(hi))
    quarter = Fraction(2) ** (f.qmax + f.p - 2)
    if abs(Z[0]) == INF or abs(Z[1]) == INF:
        assert mag > quarter, (f.name, op, X, Y, Z)                                            # I5
        st['first_unbounded'] = min(st['first_unbounded'], mag / (4 * quarter))
        st['overflow'] += 1
        return
    assert lo - Z[0] <= A * abs(lo) + B and Z[1] - hi <= A * abs(hi) + B, (f.name, op, X, Y, Z)   # I4
    for gap, ref in ((lo - Z[0], lo), (Z[1] - hi, hi)):
        st['tight'] = max(st['tight'], gap / (A * abs(ref) + B))
    st['zero_kept'] += (lo, hi) == (0, 0) and Z == (0, 0)
    st['zero_lost'] += (lo, hi) == (0, 0) and Z != (0, 0)


def sample(f, pairs, rng, count):
    """Canonical intervals: bounded, unbounded, degenerate, around zero, and the empty set."""
    zero = (Fraction(0), Fraction(0))
    special = [EMPTY, (-INF, INF), (zero, zero), (zero, INF), (-INF, zero)]
    out = []
    for _ in range(count):
        r = rng.random()
        a, b = rng.choice(pairs), rng.choice(pairs)
        if exact(a) > exact(b):
            a, b = b, a
        if r < 0.05:
            out.append(rng.choice(special))
        elif r < 0.12:
            out.append((-INF, b))
        elif r < 0.19:
            out.append((a, INF))
        elif r < 0.29:
            out.append((a, a))
        else:
            out.append((a, b))
    return out


def main():
    rng = random.Random(20261119)
    for f, ops, count in ((ieee_shape(3, 1), ('add',), 40000), (ieee_shape(4, 1), ('add', 'mul'), 30000),
                          (ieee_shape(5, 2), ('add', 'mul'), 12000)):
        pairs = normalized_pairs(f)
        for op in ops:
            _, _, _, A, B = bound_parts(f, op)
            st = dict(n=0, tight=Fraction(0), overflow=0, first_unbounded=Fraction(10), unbounded_operands=0,
                      zero_kept=0, zero_lost=0)
            xs, ys = sample(f, pairs, rng, count), sample(f, pairs, rng, count)
            for X, Y in zip(xs, ys):
                check(f, op, X, Y, A, B, st)
            first = '-' if st['overflow'] == 0 else f'{float(st["first_unbounded"]):.3f} of the threshold'
            print(f'{f.name:12} {op}: {st["n"]} nonempty pairs ({st["unbounded_operands"]} with an unbounded '
                  f'operand, {st["overflow"]} unbounded from bounded operands, first at {first}); '
                  f'largest gap over A|v|+B: {float(st["tight"]):.3f}; exact range [0,0] returned as '
                  f'[0,0] in {st["zero_kept"]}, widened in {st["zero_lost"]}')
    print('every statement held')


if __name__ == '__main__':
    sys.exit(main())
