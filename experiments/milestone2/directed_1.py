#!/usr/bin/env python3
"""The one-limb directed primitives, on every operand of small formats.

Statements judged (milestone2.md, "Building blocks on T"):

  add_down_1, add_up_1, sub_down_1, sub_up_1
      for all finite a, b: exactly RD / RU of the exact result, in the sense of the format with
      overflow (RD of a value above Omega is Omega, RD of a value below -Omega is -inf);
      for an infinite or NaN operand: the sum of IEEE 754.
  mul_down_1, mul_up_1
      for all finite a, b: a bound on the right side of a b; exactly RD / RU when a b = 0 or
      |a b| >= P = 2^(2p-1) eta; otherwise RD / RU or the number of the format one step beyond.
  the computed error term of two_prod has the sign of the exact error, or is zero; it is zero
      with a nonzero exact error only when that error is at most eta / 2 in magnitude.
  mul_dir_1: the same two bounds, and 0 for a zero factor whatever the other, infinite included.

Also counted: what the same listing does with two_sum in place of two_sum_ord (the reason for
the ordering), and how far up the band the inexact cases reach.
"""
import sys
from fractions import Fraction

from common import (NINF, NaN, PINF, ZERO, eta, ext, finite_numbers, fmt, ieee_shape, is_nan, num,
                    omega, pred, rd, rn, ru, run, succ, u_of)

INF = float('inf')

FORMATS = [ieee_shape(2, 1), ieee_shape(2, 2), ieee_shape(3, 1), ieee_shape(3, 2), ieee_shape(4, 1),
           ieee_shape(4, 2), ieee_shape(5, 1), fmt(3, -6, 0), fmt(4, -3, 3)]


def same(got, want):
    """Equality of a computed value with an extended rational (zeros of either sign are equal)."""
    return ext(got) == want


def sums(f):
    nums = finite_numbers(f)
    vals = [(x, num(x)) for x in nums]
    n = overflow = 0
    for (a, va), (b, vb) in ((x, y) for x in vals for y in vals):
        t = a + b
        for name, want in (('add_down_1', rd(f, t)), ('add_up_1', ru(f, t))):
            got = run(name, f, va, vb)
            assert same(got, want), (f.name, name, a, b, got, want)
        for name, want in (('sub_down_1', rd(f, a - b)), ('sub_up_1', ru(f, a - b))):
            got = run(name, f, va, vb)
            assert same(got, want), (f.name, name, a, b, got, want)
        n += 1
        overflow += abs(t) > omega(f)
    return n, overflow


def sums_nonfinite(f):
    """An infinite or NaN operand: the result is the sum of IEEE 754 (a NaN for inf - inf)."""
    nums = [num(x) for x in finite_numbers(f)]
    for name in ('add_down_1', 'add_up_1'):
        for v in nums:
            for inf in (PINF, NINF):
                assert run(name, f, inf, v) == inf and run(name, f, v, inf) == inf
            assert is_nan(run(name, f, NaN, v)) and is_nan(run(name, f, v, NaN))
        assert run(name, f, PINF, PINF) == PINF and run(name, f, NINF, NINF) == NINF
        assert is_nan(run(name, f, PINF, NINF)) and is_nan(run(name, f, NINF, PINF))
        for inf in (PINF, NINF):
            assert is_nan(run(name, f, NaN, inf)) and is_nan(run(name, f, inf, NaN))


def with_two_sum(f):
    """The same listing with two_sum in place of two_sum_ord: how often the bound is on the wrong
    side because the error term is a NaN although the sum is finite."""
    vals = [(x, num(x)) for x in finite_numbers(f)]
    wrong = 0
    for (a, va), (b, vb) in ((x, y) for x in vals for y in vals):
        s, e = run('two_sum', f, va, vb)
        if s[0] != 'num':
            continue
        if is_nan(e):
            # e < 0 and 0 < e are both false: the listing returns s for both directions.
            wrong += (ext(s) > a + b) + (ext(s) < a + b)
    return wrong


def products(f):
    nums = finite_numbers(f)
    vals = [(x, num(x)) for x in nums]
    band = Fraction(2) ** (2 * f.p - 1) * eta(f)
    stats = dict(n=0, band=0, beyond_down=0, beyond_up=0, sign_lost=0, top=Fraction(0))
    for (a, va), (b, vb) in ((x, y) for x in vals for y in vals):
        t = a * b
        stats['n'] += 1
        inband = t != 0 and abs(t) < band
        stats['band'] += inband
        p, e = run('two_prod', f, va, vb)
        if p[0] == 'num':
            err = t - ext(p)
            ce = ext(e)
            # The sign of the computed error is the sign of the exact one, or the computed error
            # is zero; and it is zero for a nonzero exact error only when that is at most eta/2.
            assert ce == 0 or (ce > 0) == (err > 0), (f.name, a, b)
            if ce == 0 and err != 0:
                assert abs(err) <= eta(f) / 2 and inband, (f.name, a, b)
                stats['sign_lost'] += 1
            if not inband:
                assert ce == err, (f.name, a, b)
        down, up = run('mul_down_1', f, va, vb), run('mul_up_1', f, va, vb)
        d2, v2 = run('mul_dir_1', f, va, vb)
        assert ext(d2) == ext(down) and ext(v2) == ext(up), (f.name, a, b)
        wd, wu = rd(f, t), ru(f, t)
        gd, gu = ext(down), ext(up)
        assert gd <= t <= gu, (f.name, a, b, gd, gu)
        if not inband:
            assert gd == wd and gu == wu, (f.name, a, b, gd, wd, gu, wu)
        else:
            assert gd in (wd, pred(f, wd)) and gu in (wu, succ(f, wu)), (f.name, a, b, gd, wd, gu, wu)
            if gd != wd or gu != wu:
                stats['beyond_down'] += gd != wd
                stats['beyond_up'] += gu != wu
                stats['top'] = max(stats['top'], abs(t) / band)
    return stats


def products_nonfinite(f):
    nums = [(x, num(x)) for x in finite_numbers(f)]
    for x, v in nums:
        for inf, s in ((PINF, 1), (NINF, -1)):
            for name in ('mul_down_1', 'mul_up_1'):
                for got in (run(name, f, inf, v), run(name, f, v, inf)):
                    if x == 0:
                        assert is_nan(got)                  # IEEE: 0 times infinity
                    else:
                        assert ext(got) == (INF if (x > 0) == (s > 0) else -INF)
            for d, w in (run('mul_dir_1', f, inf, v), run('mul_dir_1', f, v, inf)):
                want = 0 if x == 0 else (INF if (x > 0) == (s > 0) else -INF)
                assert ext(d) == want and ext(w) == want    # interval rule: 0 times infinity is 0
        for name in ('mul_down_1', 'mul_up_1'):
            assert is_nan(run(name, f, NaN, v)) and is_nan(run(name, f, v, NaN))
    for a, sa in ((PINF, 1), (NINF, -1)):
        for b, sb in ((PINF, 1), (NINF, -1)):
            want = INF if sa == sb else -INF
            assert ext(run('mul_down_1', f, a, b)) == want and ext(run('mul_up_1', f, a, b)) == want
            d, w = run('mul_dir_1', f, a, b)
            assert ext(d) == want and ext(w) == want


def main():
    print('format        sums   overflow | with two_sum: wrong side | products  below P  '
          'one beyond (down, up)  sign lost  highest |ab|/P of a step beyond')
    for f in FORMATS:
        n, over = sums(f)
        sums_nonfinite(f)
        wrong = with_two_sum(f)
        st = products(f)
        products_nonfinite(f)
        print(f'{f.name:12} {n:6} {over:8} | {wrong:24} | {st["n"]:8} {st["band"]:8}  '
              f'{st["beyond_down"]:9} {st["beyond_up"]:9} {st["sign_lost"]:10}  '
              f'{float(st["top"]):.4f} = {st["top"]}')
    print('every statement held')


if __name__ == '__main__':
    sys.exit(main())
