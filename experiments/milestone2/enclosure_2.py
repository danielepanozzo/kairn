#!/usr/bin/env python3
"""The enclosure interface on two limbs, composed from kernels that exist or are proposed, on
samples of normalized pairs.

Statements judged (milestone2.md, "One enclosure interface"):

  midpoint and radius of [l, u] with 2-limb bounds
      m = add_2_2(l/2, u/2) moved into [l, u] by the comparisons of two limbs; l <= m <= u;
      r = max over the two sides of radd(to_up_2(d), e), with (d, e) the difference by
      add_ball_2_2 and its error bound; [m - r, m + r] contains [l, u];
  ball -> interval with 2-limb bounds
      l = add_down_2_2(c, (-r, 0)), h = add_up_2_2(c, (r, 0)): l <= c - r and c + r <= h;
  Ball<T, 2> contains a 2-limb point t, as a three-valued answer
      yes when radd(abs_upper_2(d), e) <= r, no when r < sub_down_1(to_down_2(|d|), e), with
      (d, e) = add_ball_2_2(t, -c): yes implies |t - c| <= r and no implies |t - c| > r.
      Reported: how often neither holds.
"""
import random
import sys
from fractions import Fraction

from common import ZERO, fmt, normalized, normalized_pairs, num, run, val


def v2(x):
    return num(x[0]), num(x[1])


def value(z):
    return val(z[0]) + val(z[1])


def lt2(f, a, b):
    return run('lt_2_2', f, *a, *b)


def mid_rad(f, l, u):
    half = num(Fraction(1, 2))
    hl = run('mul_pow2_2', f, *l, half)
    hu = run('mul_pow2_2', f, *u, half)
    m = run('add_2_2', f, *hl, *hu)
    if lt2(f, m, l):
        m = l
    if lt2(f, u, m):
        m = u
    radii = []
    for a, b in ((m, l), (u, m)):
        nb = run('neg_2', f, *b)
        z0, z1, e = run('add_ball_2_2', f, *a, *nb)
        top = run('to_up_2', f, z0, z1)
        assert val(top) >= 0
        radii.append(run('radd', f, top, e))
    r = radii[0] if val(radii[0]) >= val(radii[1]) else radii[1]
    return m, r


def main():
    rng = random.Random(20261119)
    for p, qmin, qtop in ((3, -8, -2), (4, -11, -4), (5, -14, -6)):
        g = fmt(p, qmin, qtop)
        f = fmt(p, qmin, 2 * (qtop + p) + 8 - qmin)
        pairs = normalized_pairs(g)
        st = dict(mid=0, ball=0, contains=0, unknown=0)
        radii = sorted({abs(x[0]) for x in pairs[::5]})
        for _ in range(40000):
            a, b = rng.choice(pairs), rng.choice(pairs)
            if sum(a) > sum(b):
                a, b = b, a
            if rng.random() < 0.25:                      # close bounds
                i = pairs.index(a)
                b = pairs[min(len(pairs) - 1, i + rng.randint(0, 4))]
                if sum(a) > sum(b):
                    a, b = b, a
            lo, hi = sum(a), sum(b)
            m, r = mid_rad(f, v2(a), v2(b))
            mv, rv = value(m), val(r)
            assert normalized(f, val(m[0]), val(m[1])) and lo <= mv <= hi, (f.name, a, b, mv)
            assert mv - rv <= lo and hi <= mv + rv, (f.name, a, b, mv, rv)
            st['mid'] += 1
            # ball -> interval
            c, rr = a, rng.choice(radii)
            l = run('add_down_2_2', f, *v2(c), num(-rr), ZERO)
            h = run('add_up_2_2', f, *v2(c), num(rr), ZERO)
            assert value(l) <= sum(c) - rr and sum(c) + rr <= value(h), (f.name, c, rr)
            st['ball'] += 1
            # contains(point)
            t = b
            nc = run('neg_2', f, *v2(c))
            z0, z1, e = run('add_ball_2_2', f, *v2(t), *nc)
            up = run('radd', f, run('abs_upper_2', f, z0, z1), e)
            a0, a1 = run('abs_2', f, z0, z1)
            down = run('sub_down_1', f, run('to_down_2', f, a0, a1), e)
            yes, no = val(up) <= rr, rr < val(down)
            dist = abs(sum(t) - sum(c))
            assert not (yes and no)
            assert (not yes or dist <= rr) and (not no or dist > rr), (f.name, c, rr, t)
            st['contains'] += 1
            if not yes and not no:
                st['unknown'] += 1
        print(f'p={p} eta=2^{qmin}: {st["mid"]} midpoints and radii; {st["ball"]} balls to intervals; '
              f'{st["contains"]} tests of a point, of which {st["unknown"]} undecided (neither yes nor no)')
    print('every statement held')


if __name__ == '__main__':
    sys.exit(main())
