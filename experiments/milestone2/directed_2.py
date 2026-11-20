#!/usr/bin/env python3
"""The directed sums and products of two limbs: the finite cores of Interval<T, 2>.

Statements judged (milestone2.md, "Bounds of two limbs"), for normalized x and y, with v the
exact x + y or x y, in a format with room above so that nothing overflows (the real model):

  add_ball_2_2, mul_ball_2_2
      (z, d) is bit for bit what ball_add_2 / ball_mul_2 return for radii zero; |z - v| <= d;
  add_down_2_2, add_up_2_2, mul_dir_2_2
      the result is a normalized pair; l <= v <= h;
      tightness, in the kernel's own values:    v - l <= 2 d + max(eta, 2u (u |z0| + d))
      tightness, in the exact value (closed form):
          v - l <= A |v| + B,   A = (2 (1+u)^3 G E + 2 u^2) (1 + rel) / (1 - u),
                                B = 2 (1+u)^2 (G eta / 2 + H) + eta + A' tiny
      with E, G, H the constants of the ball kernel, rel and tiny those of the center's bound,
      and A' = (2 (1+u)^3 G E + 2 u^2) / (1 - u).
  Fast2Sum on (z0, w) without ordering: how often its requirement |z0| >= |w| fails, and whether
      its result is then still exact and normalized.

Reported: the largest observed (v - l) / (u^2 |v|) away from the underflow range, to compare
with 2c + 2 (c the constant of the center kernel) and with the target 2c + 3 of Phase 0.
"""
import random
import sys
from fractions import Fraction

from common import (ZERO, const, eta, ext, fmt, normalized, normalized_pairs, num, rn, run, u_of,
                    val)

CONSTS = {
    'add': dict(E='unit(add_2_2)/(1-unit(add_2_2))*(1+u)', G='(1+u)^3',
                H='(1+u)*((1+u)^2*eta+eta/2)+eta/(2*u)'),
    'mul': dict(E='unit(mul_2_2)/(1-unit(mul_2_2))', G='(1+u)^6',
                H='(1+u)*(2*(1+u)^5*eta+tiny(mul_2_2)/(1-unit(mul_2_2))+eta/2)+eta/(2*u)'),
}


def bound_parts(f, op):
    u, e = u_of(f), eta(f)
    E, G, H = (const(f, CONSTS[op][k]) for k in 'EGH')
    rel = 3 * u * u / (1 - 4 * u) if op == 'add' else 4 * u * u
    tiny = 0 if op == 'add' else Fraction(3, 2) * e
    a1 = (2 * (1 + u) ** 3 * G * E + 2 * u * u) / (1 - u)
    A = a1 * (1 + rel)
    B = 2 * (1 + u) ** 2 * (G * e / 2 + H) + e + a1 * tiny
    return E, G, H, A, B


def pair(x):
    return num(x[0]), num(x[1])


def check_ball(f, op, x, y, v):
    z0, z1, d = run(f'{op}_ball_2_2', f, *pair(x), *pair(y))
    ref = run(f'ball_{op}_2', f, *pair(x), ZERO, *pair(y), ZERO)
    assert (z0, z1, d) == tuple(ref), (f.name, op, x, y)
    assert abs(val(z0) + val(z1) - v) <= val(d), (f.name, op, x, y)
    return val(z0), val(z1), val(d)


def check_dir(f, op, x, y, st, A, B):
    u, e = u_of(f), eta(f)
    v = x[0] + x[1] + y[0] + y[1] if op == 'add' else (x[0] + x[1]) * (y[0] + y[1])
    z0, z1, d = check_ball(f, op, x, y, v)
    if op == 'add':
        l = run('add_down_2_2', f, *pair(x), *pair(y))
        h = run('add_up_2_2', f, *pair(x), *pair(y))
    else:
        l0, l1, h0, h1 = run('mul_dir_2_2', f, *pair(x), *pair(y))
        l, h = (l0, l1), (h0, h1)
    lv, hv = [val(t) for t in l], [val(t) for t in h]
    assert normalized(f, *lv) and normalized(f, *hv), (f.name, op, x, y, lv, hv)
    lo, hi = sum(lv), sum(hv)
    assert lo <= v <= hi, (f.name, op, x, y, lo, hi)
    inner = 2 * d + max(e, 2 * u * (u * abs(z0) + d))
    closed = A * abs(v) + B
    for gap in (v - lo, hi - v):
        assert gap <= inner, (f.name, op, x, y, gap, inner)
        assert gap <= closed, (f.name, op, x, y, gap, closed)
        st['inner'] = max(st['inner'], gap / inner)
        st['closed'] = max(st['closed'], gap / closed)
        if v != 0 and abs(v) >= st['far']:
            st['const'] = max(st['const'], gap / (u * u * abs(v)))
    # Fast2Sum without ordering, on the lower bound's operands.
    w = run('sub_down_1', f, num(z1), num(d))
    if abs(z0) < abs(val(w)):
        st['unordered'] += 1
        s, t = run('fast_two_sum', f, num(z0), w)
        got = val(s) + val(t)
        exact = got == z0 + val(w) and rn(f, got) == val(s)
        st['unordered_wrong'] += not exact
        st['unordered_above'] += got > v           # a "lower bound" above the exact value
        st['unordered_max'] = max(st['unordered_max'], abs(z0))
    st['n'] += 1


def run_format(p, qmin, qtop, op, limit, rng, lead_min=None):
    g = fmt(p, qmin, qtop)                         # the operands
    f = fmt(p, qmin, 2 * qtop + 3 * p + 8 - qmin)   # the same format with room above
    pairs = normalized_pairs(g, lead_min=None if lead_min is None else Fraction(2) ** lead_min)
    E, G, H, A, B = bound_parts(f, op)
    st = dict(n=0, inner=Fraction(0), closed=Fraction(0), const=Fraction(0), unordered=0,
              unordered_wrong=0, unordered_above=0, unordered_max=Fraction(0),
              far=Fraction(2) ** (2 * p + 2) * H)
    if limit is None or len(pairs) ** 2 <= limit:
        todo = ((x, y) for x in pairs for y in pairs)
    else:
        zero = [(Fraction(0), Fraction(0))]
        todo = [(x, y) for x in zero for y in pairs] + [(y, x) for x in zero for y in pairs]
        todo += [(rng.choice(pairs), rng.choice(pairs)) for _ in range(limit)]
        # Cancellation, which random pairs rarely give: y close to -x.
        for _ in range(limit // 4):
            x = rng.choice(pairs)
            i = pairs.index(x)
            y = pairs[max(0, min(len(pairs) - 1, i + rng.randint(-3, 3)))]
            todo.append((x, (-y[0], -y[1])))
    for x, y in todo:
        check_dir(f, op, x, y, st, A, B)
    c = 3 / (1 - 4 * u_of(f)) if op == 'add' else Fraction(4)
    where = '' if lead_min is None else f', leading limbs from 2^{lead_min}'
    print(f'{op}  p={p} eta=2^{qmin} operands up to 2^{qtop + p}{where}: {len(pairs)} pairs, {st["n"]} cases'
          f'{"" if limit is None else " (sample)"}')
    print(f'     E = {E}, G = {G}, H = {H} = {H / eta(f)} eta;  A = {float(A / u_of(f) ** 2):.3f} u^2, '
          f'B = {float(B / eta(f)):.2f} eta')
    print(f'     largest gap over the bound: in the kernel\'s values {float(st["inner"]):.4f}, '
          f'closed form {float(st["closed"]):.4f}')
    print(f'     largest gap / (u^2 |v|) for |v| >= 2^(2p+2) H: {float(st["const"]):.3f}   '
          f'(A = {float(A / u_of(f) ** 2):.3f} u^2 here, 2c + 2 = {float(2 * c + 2):.3f} with this '
          f'precision\'s c; in the limit of a large precision {8 if op == "add" else 10})')
    print(f'     Fast2Sum(z0, w) without ordering: |z0| < |w| in {st["unordered"]} cases, the largest '
          f'|z0| among them {st["unordered_max"] / eta(f)} eta; result not exact or not normalized in '
          f'{st["unordered_wrong"]}, above the exact value in {st["unordered_above"]}')
    return st


def main():
    rng = random.Random(20261119)
    run_format(3, -5, -2, 'add', None, rng)
    run_format(3, -9, -3, 'add', 150000, rng)
    run_format(4, -8, -4, 'add', 150000, rng)
    run_format(5, -14, -6, 'add', 100000, rng)
    run_format(4, -6, -3, 'mul', None, rng)
    run_format(4, -12, -5, 'mul', 150000, rng)
    run_format(5, -16, -8, 'mul', 100000, rng)
    run_format(6, -20, -12, 'mul', 60000, rng)
    # Away from the underflow range, where the absolute term does not count: the relative constant.
    run_format(4, -26, -5, 'add', 150000, rng, lead_min=-4)
    run_format(5, -32, -6, 'add', 100000, rng, lead_min=-4)
    run_format(4, -26, -5, 'mul', 150000, rng, lead_min=-4)
    run_format(5, -32, -6, 'mul', 100000, rng, lead_min=-4)
    print('every statement held')


if __name__ == '__main__':
    sys.exit(main())
