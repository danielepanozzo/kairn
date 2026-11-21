#!/usr/bin/env python3
"""The predicates and comparisons of a ball (milestone2.md, "One enclosure interface"): how far from
exact the certain answers of two limbs are, and when the exact ones of one limb are exact.

Statements judged, on the kernels of gen/kernels:

  two limbs (certain): ball_contains_point_2, ball_contains_ball_2, ball_less_2, ball_less_equal_2,
      ball_equal_2. Every answer that is given is right. An answer that is not given (yes false
      although the relation holds, no false although it fails for every pair) is within this band
      of the boundary, with e the error bound of add_ball_2_2 of the difference of the centers (of
      the point and the center) and G the gap of the format at the largest of the radii and the
      distance:
          contains a point     r - |t - c| < 2e + 3G (yes),    |t - c| - r <= 2e + 3G (no)
          contains a ball      r_x - (|c_y - c_x| + r_y) < 2e + 4G
          less, less_equal     (c_y - c_x) - (r_x + r_y) < 2e + 4G (yes),
                               (c_x - c_y) - (r_x + r_y) < 2e + 4G (no)
          equal                |c_y - c_x| - (r_x + r_y) < 2e + 4G (no; yes is exact)
      Reasoning, in exact arithmetic: |d - z| <= e for the difference d and the computed pair z;
      each rounding of a bound to one limb (abs_upper_2, to_down_2, to_up_2) moves it by less than
      G, radd adds at most 3/2 G, and the directed difference with e at most G more; so a bound of
      a distance is within 2e + 2.5G of the distance, and a sum of radii within 1.5G of the sum.
      Measured: how many answers are not given, and the largest margin in units of 2e + G.
  one limb (exact pairs): ball_less_1, ball_less_equal_1, ball_equal_1 are exact unless the sum of
      the radii and the difference of the centers both overflow (then unknown; counted), and
      ball_contains_point_1, ball_contains_ball_1 always.
"""
import random
import sys
from fractions import Fraction

from common import (ZERO, eta, fmt, ieee_shape, is_fin, normalized_pairs, num, omega, quantum, run, val)

INF = float('inf')


def gap(f, x):
    x = abs(Fraction(x))
    return quantum(f, x) if x else eta(f)


def pair(x):
    return num(x[0]), num(x[1])


def two_limb(f, g, rng, cases):
    """Balls and points of the pairs of the format g, computed in f, which has the precision and
    the smallest number of g and a range wide enough that nothing overflows."""
    pairs = normalized_pairs(g)
    radii = sorted({abs(p[0]) for p in pairs})
    st = {name: [0, 0, Fraction(0)] for name in ('contains_point', 'contains_ball', 'less', 'less_equal', 'equal')}
    e_of = {}

    def error_bound(a, b):
        """e of add_ball_2_2(a, -b), the bound of |(a - b) - z|."""
        key = (a, b)
        if key not in e_of:
            na = run('neg_2', f, *pair(b))
            out = run('add_ball_2_2', f, *pair(a), *na)
            e_of[key] = val(out[2])
        return e_of[key]

    def note(name, decided, margin, unit, bound):
        s = st[name]
        s[0] += 1
        if not decided:
            s[1] += 1
            assert margin < bound, (f.name, name, margin, bound)
            s[2] = max(s[2], margin / unit)

    for _ in range(cases):
        c, t, c2 = rng.choice(pairs), rng.choice(pairs), rng.choice(pairs)
        if rng.random() < 0.5:                 # points and centers close to each other
            i = pairs.index(c)
            t = pairs[min(len(pairs) - 1, i + rng.randint(0, 6))]
            c2 = pairs[max(0, i - rng.randint(0, 6))]
        r, r2 = rng.choice(radii), rng.choice(radii)
        cv, tv, c2v = sum(c), sum(t), sum(c2)
        # contains a point: |t - c| <= r
        yes, no = run('ball_contains_point_2', f, *pair(c), num(r), *pair(t))
        dist, e = abs(tv - cv), error_bound(t, c)
        g = gap(f, max(r, dist))
        assert not (yes and no)
        assert (not yes or dist <= r) and (not no or dist > r), (f.name, c, r, t)
        if dist <= r:
            note('contains_point', yes, r - dist, 2 * e + g, 2 * e + 3 * g)
        else:
            note('contains_point', no, dist - r, 2 * e + g, 2 * e + 3 * g)
        # contains a ball: |c2 - c| + r2 <= r
        m = run('ball_contains_ball_2', f, *pair(c), num(r), *pair(c2), num(r2))
        dist, e = abs(c2v - cv), error_bound(c2, c)
        g = gap(f, max(r, r2, dist))
        assert not m or dist + r2 <= r, (f.name, c, r, c2, r2)
        if dist + r2 <= r:
            note('contains_ball', m, r - dist - r2, 2 * e + g, 2 * e + 4 * g)
        # the comparisons of X = (c, r) and Y = (c2, r2): d = c2 - c
        d, s = c2v - cv, r + r2
        g = gap(f, max(r, r2, s, abs(d)))
        for name, holds, fails, margin_yes, margin_no in (
                ('less', s < d, s <= -d, d - s, -d - s),
                ('less_equal', s <= d, s < -d, d - s, -d - s)):
            yes, no = run(f'ball_{name}_2', f, *pair(c), num(r), *pair(c2), num(r2))
            assert not (yes and no)
            assert (not yes or holds) and (not no or fails), (f.name, name, c, r, c2, r2)
            if holds:
                note(name, yes, margin_yes, 2 * e + g, 2 * e + 4 * g)
            if fails:
                note(name, no, margin_no, 2 * e + g, 2 * e + 4 * g)
        yes, no = run('ball_equal_2', f, *pair(c), num(r), *pair(c2), num(r2))
        same, apart = r == r2 == 0 and d == 0, s < abs(d)
        assert yes == same, (f.name, c, r, c2, r2)            # the yes of equal is exact
        assert not no or apart, (f.name, c, r, c2, r2)
        if apart:
            note('equal', no, abs(d) - s, 2 * e + g, 2 * e + 4 * g)
    return st


def one_limb(f):
    """The exact pairs of one limb: exact unless the sum of the radii and the difference of the
    centers both overflow, on balls of the whole format, those near the top included."""
    from common import finite_numbers
    nums = finite_numbers(f)
    balls = [(c, r) for c in nums for r in nums if r >= 0]
    step = max(1, len(balls) // 200)
    sample = balls[::step] + [(c, r) for c in nums[-3:] + nums[:3] for r in nums[-3:] if r >= 0]
    unknown = {'less': 0, 'less_equal': 0, 'equal': 0}
    count = 0
    for cx, rx in sample:
        for cy, ry in sample:
            count += 1
            d, s = cy - cx, rx + ry
            both = abs(s) > omega(f) and abs(d) > omega(f)
            for name, holds, fails in (('less', s < d, s <= -d), ('less_equal', s <= d, s < -d),
                                       ('equal', rx == ry == 0 and d == 0, s < abs(d))):
                yes, no = run(f'ball_{name}_1', f, num(cx), num(rx), num(cy), num(ry))
                assert (not yes or holds) and (not no or fails) and not (yes and no), (f.name, name, cx, rx, cy, ry)
                if (yes, no) != (holds, fails):
                    assert both, (f.name, name, cx, rx, cy, ry)
                    unknown[name] += 1
            m = run('ball_contains_ball_1', f, num(cx), num(rx), num(cy), num(ry))
            assert m == (abs(cy - cx) + ry <= rx), (f.name, cx, rx, cy, ry)
    for c, r in balls[::max(1, len(balls) // 400)]:
        for t in nums:
            m = run('ball_contains_point_1', f, num(c), num(r), num(t))
            assert m == (abs(t - c) <= r), (f.name, c, r, t)
    return count, unknown


def main():
    rng = random.Random(20261120)
    print('two limbs: answers not given (yes or no false although the relation holds, or fails for every pair) '
          'and the largest margin to the boundary in units of 2e + G')
    for p, qmin, qtop in ((3, -8, -2), (4, -11, -4), (5, -14, -6)):
        g = fmt(p, qmin, qtop)
        f = fmt(p, qmin, 2 * (qtop + p) + 8 - qmin)
        st = two_limb(f, g, rng, 20000)
        print(f'  p={p} eta=2^{qmin}: ' + '; '.join(
            f'{name} {s[1]} of {s[0]} not given, largest margin {float(s[2]):.2f}' for name, s in st.items()))
    print('one limb: answers that are unknown although decidable, all where both sums overflow')
    for f in (ieee_shape(2, 1), ieee_shape(3, 1), fmt(3, -6, 0)):
        count, unknown = one_limb(f)
        print(f'  {f.name}: {count} pairs of balls; ' + ', '.join(f'{n} {u}' for n, u in unknown.items()))
    print('every statement held')


if __name__ == '__main__':
    sys.exit(main())
