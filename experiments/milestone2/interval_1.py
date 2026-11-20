#!/usr/bin/env python3
"""Interval<T, 1>: the constructor, negation, sum, difference and product, on every canonical
interval of a small format (bounded, unbounded and empty) and on samples of larger ones.

Statements judged (milestone2.md, "Interval kernels"), for canonical operands X and Y:

  I1  the result is canonical: the empty set (+inf, -inf), or zl <= zu with zl < +inf, zu > -inf
      and no NaN;
  I2  it is empty exactly when an operand is;
  I3  it contains x o y for every real x in X and y in Y, unbounded operands included;
  I4  each bound is the exact directed rounding of the exact bound of the range (for a product:
      when each of the four products of bounds is zero or at least P = 2^(2p-1) eta in magnitude,
      and otherwise that rounding or the number one step beyond it);
  I5  for bounded operands the result is bounded exactly when the exact range lies in
      [-Omega, Omega].

The exact range of a product is computed here without the rule "0 times infinity is 0": an
infinite bound is replaced by a number K so large that any product with it leaves every range
of interest, and the hull of the four exact corner products of that bounded rectangle is taken.
"""
import random
import sys
from fractions import Fraction

from common import (NINF, NaN, PINF, eta, ext, finite_numbers, fmt, ieee_shape, is_nan, num, omega, pred,
                    rd, ru, run, succ)

INF = float('inf')
EMPTY = (INF, -INF)


def intervals(f):
    """Every canonical interval of the format, as pairs of extended rationals."""
    nums = finite_numbers(f)
    out = [EMPTY, (-INF, INF)]
    out += [(-INF, u) for u in nums] + [(l, INF) for l in nums]
    out += [(l, u) for i, l in enumerate(nums) for u in nums[i:]]
    return out


def value(x):
    return PINF if x == INF else NINF if x == -INF else num(x)


def canonical(zl, zu):
    if is_nan(zl) or is_nan(zu):
        return False
    l, u = ext(zl), ext(zu)
    return (l, u) == EMPTY or (l <= u and l < INF and u > -INF)


def hull_sum(X, Y, sign=1):
    yl, yu = (Y[0], Y[1]) if sign > 0 else (-Y[1], -Y[0])
    return X[0] + yl, X[1] + yu


def hull_product(f, X, Y):
    big = Fraction(2) ** (4 * (f.qmax + f.p) - 4 * f.qmin + 8)
    far = big * eta(f) / 2                     # beyond every product of two finite numbers

    def proxy(t):
        return big if t == INF else -big if t == -INF else t
    corners = [proxy(a) * proxy(b) for a in X for b in Y]
    lo, hi = min(corners), max(corners)
    return (-INF if lo < -far else lo), (INF if hi > far else hi)


def directed(f, t, down):
    """RD or RU of an extended real, in the sense of the format with overflow."""
    if t in (INF, -INF):
        return t
    return rd(f, t) if down else ru(f, t)


def check(f, name, X, Y, stats):
    zl, zu = run(name, f, value(X[0]), value(X[1]), value(Y[0]), value(Y[1]))
    assert canonical(zl, zu), (f.name, name, X, Y, zl, zu)                              # I1
    Z = (ext(zl), ext(zu))
    empty = X == EMPTY or Y == EMPTY
    assert (Z == EMPTY) == empty, (f.name, name, X, Y, Z)                               # I2
    if empty:
        return
    if name == 'interval_mul_1':
        lo, hi = hull_product(f, X, Y)
    else:
        lo, hi = hull_sum(X, Y, 1 if name == 'interval_add_1' else -1)
    assert Z[0] <= lo and hi <= Z[1], (f.name, name, X, Y, Z, lo, hi)                    # I3
    wl, wu = directed(f, lo, True), directed(f, hi, False)
    if name != 'interval_mul_1':
        assert Z == (wl, wu), (f.name, name, X, Y, Z, wl, wu)                           # I4
    else:
        band = Fraction(2) ** (2 * f.p - 1) * eta(f)
        finite = [a * b for a in X for b in Y if abs(a) != INF and abs(b) != INF]
        clear = all(t == 0 or abs(t) >= band for t in finite)
        if clear:
            assert Z == (wl, wu), (f.name, name, X, Y, Z, wl, wu)
        else:
            okl = Z[0] == wl or (wl != -INF and Z[0] == pred(f, wl))
            oku = Z[1] == wu or (wu != INF and Z[1] == succ(f, wu))
            assert okl and oku, (f.name, name, X, Y, Z, wl, wu)
            stats['beyond'] += Z != (wl, wu)
    bounded = all(abs(t) != INF for t in X + Y)
    if bounded:                                                                         # I5
        inside = -omega(f) <= lo and hi <= omega(f)
        assert (abs(Z[0]) != INF and abs(Z[1]) != INF) == inside, (f.name, name, X, Y, Z)
        stats['unbounded_from_bounded'] += not inside
    stats['n'] += 1


def constructor(f):
    """interval_make_1 on every pair of values, NaN and the infinities included."""
    vals = [(x, num(x)) for x in finite_numbers(f)] + [(INF, PINF), (-INF, NINF), (None, NaN)]
    for l, vl in vals:
        for u, vu in vals:
            zl, zu = run('interval_make_1', f, vl, vu)
            valid = l is not None and u is not None and l <= u and l < INF and u > -INF
            assert (ext(zl), ext(zu)) == ((l, u) if valid else EMPTY), (f.name, l, u, zl, zu)


def negation(f, all_intervals):
    for X in all_intervals:
        zl, zu = run('interval_neg_1', f, value(X[0]), value(X[1]))
        assert canonical(zl, zu) and (ext(zl), ext(zu)) == (-X[1], -X[0]), (f.name, X)


def main():
    rng = random.Random(20261119)
    print('format        intervals  pairs judged per operation   unbounded results of bounded '
          'operands (add, sub, mul)   products one step beyond')
    for f, limit in ((ieee_shape(2, 1), None), (fmt(2, -3, 1), None), (ieee_shape(3, 1), 60000),
                     (ieee_shape(4, 1), 40000), (fmt(3, -6, 0), 40000)):
        ivs = intervals(f)
        constructor(f)
        negation(f, ivs)
        if limit is None:
            pairs = [(X, Y) for X in ivs for Y in ivs]
        else:
            special = [EMPTY, (-INF, INF), (Fraction(0), Fraction(0)), (Fraction(0), INF), (-INF, Fraction(0))]
            pairs = [(X, Y) for X in special for Y in ivs] + [(Y, X) for X in special for Y in ivs]
            pairs += [(rng.choice(ivs), rng.choice(ivs)) for _ in range(limit)]
        out = {}
        for name in ('interval_add_1', 'interval_sub_1', 'interval_mul_1'):
            stats = dict(n=0, beyond=0, unbounded_from_bounded=0)
            for X, Y in pairs:
                check(f, name, X, Y, stats)
            out[name] = stats
        print(f'{f.name:12} {len(ivs):10} {len(pairs):10}{"" if limit is None else " (sample)":9}'
              f'           {out["interval_add_1"]["unbounded_from_bounded"]:6} '
              f'{out["interval_sub_1"]["unbounded_from_bounded"]:6} '
              f'{out["interval_mul_1"]["unbounded_from_bounded"]:6}'
              f'                       {out["interval_mul_1"]["beyond"]:8}')
    print('every statement held')


if __name__ == '__main__':
    sys.exit(main())
