#!/usr/bin/env python3
"""The enclosure interface on one limb, on every canonical interval and ball of small formats.

Statements judged (milestone2.md, "One enclosure interface"):

  interval_mid_rad_1   bounded X = [l, u]: l <= m <= u, m within eta and one rounding of
                       (l + u) / 2, r the smallest number of T with [m - r, m + r] containing X;
                       whole line: (0, +inf); [l, +inf]: (Omega, +inf); [-inf, u]: (-Omega, +inf);
                       empty: (NaN, NaN)
  ball_to_interval_1   the smallest interval of T containing the ball: [RD(c - r), RU(c + r)];
                       whole line -> [-inf, +inf]; empty -> empty
  ball_split_1         two canonical balls, the first containing [c - r, c], the second [c, c + r]
  ball_from_interval_2 from two values of T: the exact midpoint as a normalized pair and the
                       smallest radius when both halvings are exact; otherwise a center within
                       eta of the midpoint and the number after RU(hu - hl) as the radius, hl
                       and hu the rounded halves; containment always; the whole line for an
                       infinite bound, for a NaN bound and for the same infinity twice (both
                       decided on 2026-11-20); the empty set for lo > hi
  Ball<T, 1> predicates computed with exact pairs (two_sum_ord, abs_2, the comparisons of two
  limbs): contains(point), contains(ball), and the three-valued X < Y: its "yes" by a strict
  comparison of pairs, its "no" by a comparison that is not strict and a test that both pairs
  are finite. Counted: how often the "no" would be wrong without that test.
"""
import sys
from fractions import Fraction

from common import (NINF, NaN, PINF, ZERO, eta, ext, finite_numbers, fmt, ieee_shape, is_nan, normalized,
                    num, omega, rd, rn, ru, run, succ, val)

INF = float('inf')
EMPTY = (INF, -INF)


def value(x):
    return PINF if x == INF else NINF if x == -INF else NaN if x is None else num(x)


def intervals(f):
    nums = finite_numbers(f)
    out = [EMPTY, (-INF, INF)]
    out += [(-INF, u) for u in nums] + [(l, INF) for l in nums]
    out += [(l, u) for i, l in enumerate(nums) for u in nums[i:]]
    return out


def balls(f):
    nums = finite_numbers(f)
    return [(c, r) for c in nums for r in nums if r >= 0]


def mid_rad(f):
    worst = Fraction(0)
    for l, u in intervals(f):
        m, r = run('interval_mid_rad_1', f, value(l), value(u))
        if (l, u) == EMPTY:
            assert is_nan(m) and is_nan(r)
        elif l == -INF and u == INF:
            assert ext(m) == 0 and ext(r) == INF
        elif u == INF:
            assert ext(m) == omega(f) and ext(r) == INF
        elif l == -INF:
            assert ext(m) == -omega(f) and ext(r) == INF
        else:
            mm, rr = ext(m), ext(r)
            assert l <= mm <= u, (f.name, l, u, mm)
            need = max(mm - l, u - mm)
            assert rr == ru(f, need), (f.name, l, u, mm, rr)
            mid = (l + u) / 2
            # one rounding of the sum of the halves, each within eta / 2 of its exact value
            assert abs(mm - mid) <= eta(f) + abs(mid) * Fraction(1, 2 ** f.p), (f.name, l, u, mm)
            worst = max(worst, abs(mm - rn(f, mid)) / eta(f))
    return worst


def to_interval(f):
    for c, r in balls(f):
        zl, zu = run('ball_to_interval_1', f, num(c), num(r))
        assert (ext(zl), ext(zu)) == (rd(f, c - r), ru(f, c + r)), (f.name, c, r)
    zl, zu = run('ball_to_interval_1', f, ZERO, PINF)
    assert (ext(zl), ext(zu)) == (-INF, INF)
    zl, zu = run('ball_to_interval_1', f, NaN, NaN)
    assert (ext(zl), ext(zu)) == EMPTY


def split(f):
    worst = Fraction(0)
    for c, r in balls(f):
        ca, ra, cb, rb = run('ball_split_1', f, num(c), num(r))
        left, right = (ext(ca), ext(ra)), (ext(cb), ext(rb))
        for (cc, rr), (lo, hi) in ((left, (c - r, c)), (right, (c, c + r))):
            if rr == INF:
                assert cc == 0                      # the whole line, canonical
                continue
            assert rr >= 0 and cc - rr <= lo and hi <= cc + rr, (f.name, c, r, cc, rr)
            if r > 0:
                worst = max(worst, rr / (r / 2))
    for whole in ((ZERO, PINF),):
        assert run('ball_split_1', f, *whole) == whole + whole
    assert all(is_nan(t) for t in run('ball_split_1', f, NaN, NaN))
    return worst


def from_interval(f):
    vals = finite_numbers(f) + [INF, -INF, None]
    inexact = 0
    for lo in vals:
        for hi in vals:
            c0, c1, r = run('ball_from_interval_2', f, value(lo), value(hi))
            if lo is None or hi is None or (lo == hi and abs(lo) == INF):
                # a NaN bound, whatever the other bound, or the same infinity twice: the whole line
                # (both decided on 2026-11-20)
                assert ext(c0) == 0 and ext(c1) == 0 and ext(r) == INF, (f.name, lo, hi)
            elif lo > hi:
                # reversed bounds, [+inf, -inf] among them: the empty set
                assert is_nan(c0) and is_nan(c1) and is_nan(r), (f.name, lo, hi)
            elif abs(lo) == INF or abs(hi) == INF:
                assert ext(c0) == 0 and ext(c1) == 0 and ext(r) == INF, (f.name, lo, hi)
            else:
                c, rr = val(c0) + val(c1), val(r)
                assert normalized(f, val(c0), val(c1))
                assert c - rr <= lo and hi <= c + rr, (f.name, lo, hi, c, rr)
                if c == (lo + hi) / 2:
                    # an exact midpoint: the radius is the smallest of T, or one eta step more when
                    # a halving was not exact but the two errors cancelled
                    assert rr == ru(f, (hi - lo) / 2) or rn(f, lo / 2) != lo / 2 or rn(f, hi / 2) != hi / 2
                else:
                    inexact += 1
                    assert abs(c - (lo + hi) / 2) <= eta(f)
                hl, hu = rn(f, lo / 2), rn(f, hi / 2)
                if hl == lo / 2 and hu == hi / 2:
                    assert c == (lo + hi) / 2 and rr == ru(f, (hi - lo) / 2), (f.name, lo, hi)
                else:
                    # a halving was rounded: the radius is the number after RU(hu - hl), which is
                    # at least eta more, and eta is what the center can be off by
                    d = ru(f, hu - hl)
                    assert rr == succ(f, d) and rr >= d + eta(f), (f.name, lo, hi, rr, d)
    return inexact


def predicates(f):
    """contains(point), contains(ball) and X < Y for balls of one limb, by exact pairs."""
    bs = balls(f)
    nums = finite_numbers(f)
    undecided = unguarded = 0
    for c, r in bs:
        for t in nums:
            s, e = run('two_sum_ord', f, num(t), num(-c))
            a0, a1 = run('abs_2', f, s, e)
            got = run('le_2_1', f, a0, a1, num(r))
            assert got == (abs(t - c) <= r), (f.name, c, r, t)
    step = max(1, len(bs) // 220)
    sample = bs[::step]
    for cx, rx in sample:
        for cy, ry in sample:
            # Y inside X: |cy - cx| <= rx - ry, both sides as exact pairs
            d0, d1 = run('two_sum_ord', f, num(cy), num(-cx))
            a0, a1 = run('abs_2', f, d0, d1)
            g0, g1 = run('two_sum_ord', f, num(rx), num(-ry))
            got = run('le_2_2', f, a0, a1, g0, g1)
            assert got == (abs(cy - cx) + ry <= rx), (f.name, cx, rx, cy, ry)
            # X < Y for all members: rx + ry < cy - cx
            s0, s1 = run('two_sum_ord', f, num(rx), num(ry))
            e0, e1 = run('two_sum_ord', f, num(cy), num(-cx))
            yes = run('lt_2_2', f, s0, s1, e0, e1)
            truth = cx + rx < cy - ry
            assert (not yes) or truth, (f.name, cx, rx, cy, ry)        # yes is always right
            if not (s0 == PINF and e0 == PINF):
                # exact unless the sum of the radii and the difference of the centers both overflow
                assert yes == truth, (f.name, cx, rx, cy, ry)
            undecided += truth and not yes
            # The "no" of X < Y, x >= y for all members: rx + ry <= cx - cy. This comparison is
            # not strict, and two sums that overflow are both (+inf, -inf), which le_2_2 calls
            # equal: the mask also asks for a finite sum of the radii.
            g0, g1 = run('two_sum_ord', f, num(cx), num(-cy))
            bare = run('le_2_2', f, s0, s1, g0, g1)
            no = bare and s0[0] == 'num'
            never = cx - rx >= cy + ry
            assert (not no) or never, (f.name, cx, rx, cy, ry)
            assert not (yes and no)
            if not (s0 == PINF and g0 == PINF):
                assert no == never, (f.name, cx, rx, cy, ry)
            undecided += never and not no
            unguarded += bare and not never
    return undecided, unguarded


def main():
    print('format        midpoint: largest |m - RN((l+u)/2)| in eta   split: largest half radius '
          'over r/2   from_interval: inexact midpoints   X < Y decidable but answered unknown '
          '(both sides overflow)   "no" wrong without the test of finiteness')
    for f in (ieee_shape(2, 1), ieee_shape(2, 2), ieee_shape(3, 1), fmt(3, -6, 0), ieee_shape(4, 1)):
        worst_mid = mid_rad(f)
        to_interval(f)
        worst_split = split(f)
        inexact = from_interval(f)
        undecided, unguarded = predicates(f) if f.p <= 3 else ('-', '-')
        print(f'{f.name:12} {float(worst_mid):30.2f} {float(worst_split):34.3f} {inexact:26} '
              f'{undecided!s:>20} {unguarded!s:>30}')
    print('every statement held')


if __name__ == '__main__':
    sys.exit(main())
