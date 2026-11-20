#!/usr/bin/env python3
"""Two kernels of BallVector (milestone2.md, "BallVector") that a ball vector of gen/kernels cannot be
yet, proposed in kernels/ and run here by composing their kernels with the generator's interpreter, as
the generated code would run them (architecture.md, "Ball vectors": the step on each entry, the
record of the state on what the step returns, the lane order of the state, the radius at the end, the
finish, the whole space when its flag is false):

  bv_mul_pow2_k (bv_mul_pow2_2.fold): the centers by mul_pow2_k and, from the step, the mask that the
      entry was scaled exactly (ec of ball_mul_pow2_k), and-ed over the entries into a third group of
      the state; the radius bv_mul_pow2_radius(m, ex, rx, c): c rx when every entry and the radius
      were scaled exactly, otherwise the second number after RN(c rx).
  bv_axpy_k (bv_axpy_2.fold): the centers by axpy_k and, from the step, the scaled center p, whose
      largest leading magnitude M' a second fold of maxima records; the radius
      bv_add_radius_k(M, bv_scale_radius_k(M', rx, a), ry), the page's.

Statements judged, in exact arithmetic, on canonical BallVectors (finite ones and the whole space),
in toy formats of the IEEE shape of two to four bits and in binary64 and binary32:

  P1  V1 (canonical), the flag (true exactly when the radius is finite), V2 (containment entry by
      entry), V3 (a finite result has finite operands, and its centers are those of the map), V4 of
      every length with the proposed finite_when and radii_when; every order the same (sequential,
      and the lane order with 0 to 4 lanes, the lanes' states combined by norm_combine and `and`);
  P2  bv_mul_pow2_k: when every entry satisfies the conditions of exact_when (each limb of the center
      times c zero or above the smallest normal number N, and so the radius), the result is exactly
      c X: the centers c x_i and the radius c rx; and the one radius equals the largest of the radii
      that ball_mul_pow2_k returns entry by entry (the page's "equal");
  P3  bv_axpy_k: the result is, bit for bit, bv_add_k(bv_scale_k(X, a), Y), two ball vectors of
      gen/kernels in two passes: centers, radius and flag; its radius is at least the largest of the
      entrywise radii of ball_add_k(ball_scale_k(x_i, rx, a), y_i, ry), and equal when one entry has
      both maxima.
"""
import os
import random
import sys
from fractions import Fraction

from common import KERNELS, ROOT, NaN, NINF, PINF, ZERO, interp, ir, is_fin, num, val

FOLDS = {}
for fn in ('bv_add_1.fold', 'bv_add_2.fold', 'bv_scale_1.fold', 'bv_scale_2.fold'):
    with open(os.path.join(ROOT, 'gen', 'kernels', fn), encoding='utf-8') as f:
        fd = ir.parse_fold(f.read(), fn)
    FOLDS[fd.name] = fd
KS = ir.KernelSet(dict(KERNELS), folds=FOLDS)
M = interp.Machine(KS)
ORDERS = [('sequential', 0)] + [('lanes', w) for w in range(5)]
N_OF = {}


def ieee_format(p, emax):
    return interp.Format(f'fp:{p}:{3 - emax - p}:{emax - p}', p, 3 - emax - p, emax - p)


def fold_order(record, combine, zero, items, order, lanes):
    """fold_seq or fold_lanes (proofs/theories/Folds.v) of `record` over items."""
    def seq(xs, s):
        for x in xs:
            s = record(s, x)
        return s
    if order == 'sequential' or lanes == 0:
        return seq(items, zero)
    full = lanes * (len(items) // lanes)
    states = [seq(items[j:full:lanes], zero) for j in range(lanes)]
    s = states[0]
    for t in states[1:]:
        s = combine(s, t)
    return seq(items[full:], s)


def run_mul_pow2(k, f, xs, rx, c, order, lanes):
    """bv_mul_pow2_k as proposed: (centers, radius, flag)."""
    outs = [M.run(f'bv_mul_pow2_step_{k}', f, list(x) + [c]) for x in xs]
    zs = [o[:k] for o in outs]
    es = [o[k] for o in outs]
    rec = lambda s, g: tuple(M.run(f'norm_step_{k}', f, list(s[:2]) + list(g[0]))) + (s[2] and g[1],)
    comb = lambda s, t: tuple(M.run('norm_combine', f, list(s[:2]) + list(t[:2]))) + (s[2] and t[2],)
    m, ok, ex = fold_order(rec, comb, (ZERO, True, True), list(zip(zs, es)), order, lanes)
    rz = M.run('bv_mul_pow2_radius', f, [m, ex, rx, c])[0]
    r, flag = M.run('norm_finish_1', f, [rz, ok])
    if not flag:
        return [[ZERO] * k for _ in zs], PINF, False
    return zs, r, True


def run_axpy(k, f, xs, ys, rx, ry, a, order, lanes):
    """bv_axpy_k as proposed: (centers, radius, flag)."""
    outs = [M.run(f'bv_axpy_step_{k}', f, list(x) + list(y) + [a]) for x, y in zip(xs, ys)]
    zs = [o[:k] for o in outs]
    ps = [o[k:] for o in outs]
    rec = lambda s, g: tuple(M.run(f'norm_step_{k}', f, list(s[:2]) + list(g[0]))) + \
        tuple(M.run(f'norm_step_{k}', f, list(s[2:]) + list(g[1])))
    comb = lambda s, t: tuple(M.run('norm_combine', f, list(s[:2]) + list(t[:2]))) + \
        tuple(M.run('norm_combine', f, list(s[2:]) + list(t[2:])))
    m, ok, mp, okp = fold_order(rec, comb, (ZERO, True, ZERO, True), list(zip(zs, ps)), order, lanes)
    rz = M.run(f'bv_axpy_radius_{k}', f, [m, mp, rx, ry, a])[0]
    r, flag = M.run('norm_finish_1', f, [rz, ok])
    if not flag:
        return [[ZERO] * k for _ in zs], PINF, False
    return zs, r, True


def same_in_every_order(fn, *args):
    outs = [fn(*args, order, w) for order, w in ORDERS]
    assert all(o == outs[0] for o in outs), args
    return outs[0]


def value(g):
    return sum(val(v) for v in g)


def canonical(f, zs, r, flag):
    """V1 and the flag."""
    if flag:
        assert is_fin(r) and val(r) >= 0
        for z in zs:
            assert all(is_fin(v) for v in z)
            if len(z) == 2:
                assert interp.eq(interp.add(f, z[0], z[1]), z[0])
    else:
        assert r == PINF and all(v[0] == interp.NUM and v[2] == 0 for z in zs for v in z)


def top(f, e):
    return Fraction(2) ** (f.qmax + f.p + e)


class Draw:
    """Finite numbers of a format, near the top of it with some probability, and canonical pairs."""

    def __init__(self, f, rng):
        self.f, self.rng = f, rng

    def one(self, lo=None):
        f, rng = self.f, self.rng
        x = rng.random()
        if x < 0.08:
            return ZERO
        if x < 0.25:
            q = rng.randint(f.qmax - 2, f.qmax)
        elif x < 0.4:
            q = rng.randint(f.qmin, f.qmin + f.p)
        else:
            q = rng.randint(max(f.qmin, -3 * f.p), min(f.qmax, 2 * f.p))
        return interp.canon(rng.random() < 0.5, rng.randrange(1, 2 ** f.p), q)

    def pair(self):
        x0 = self.one()
        if x0[2] == 0:
            return [x0, ZERO]
        q = max(x0[3] + x0[2].bit_length() - self.f.p, self.f.qmin)
        cands = [ZERO]
        for m, e in ((1, self.f.qmin), (1, q - 1), (1, q - 2), (3, q - 3)):
            if e >= self.f.qmin:
                for s in (False, True):
                    y = interp.canon(s, m, e)
                    if interp.member(self.f, y) and interp.eq(interp.add(self.f, x0, y), x0):
                        cands.append(y)
        return [x0, self.rng.choice(cands)]

    def group(self, k):
        return [self.one()] if k == 1 else self.pair()

    def radius(self):
        v = self.one()
        return (interp.NUM, False, v[2], v[3])


def mul_pow2_cases(k, f, rng, rounds):
    draw = Draw(f, rng)
    nn = interp.canon(False, 1, f.qmin + f.p - 1)        # N, the smallest normal number
    count = whole = exact = equal = 0
    for i in range(rounds):
        n = i % 6
        is_whole = rng.random() < 0.1
        xs = [[ZERO] * k if is_whole else draw.group(k) for _ in range(n)]
        rx = PINF if is_whole else draw.radius()
        c = interp.canon(False, 1, rng.randint(f.qmin, f.qmax + f.p - 1))
        zs, r, flag = same_in_every_order(run_mul_pow2, k, f, xs, rx, c)
        canonical(f, zs, r, flag)
        count += 1
        whole += not flag
        cv = val(c)
        if flag:
            assert not is_whole
            for x, z in zip(xs, zs):
                assert [val(v) for v in z] == [val(v) for v in M.run(f'mul_pow2_step_{k}', f, list(x) + [c])]
                lo, hi = (value(x) - val(rx)) * cv, (value(x) + val(rx)) * cv
                assert value(z) - val(r) <= lo and hi <= value(z) + val(r), (x, rx, c)          # V2
            # P2: exact when every entry satisfies the conditions.
            conds = all(all(val(v) == 0 or abs(val(v) * cv) > val(nn) for v in x) for x in xs) and \
                (val(rx) == 0 or val(rx) * cv > val(nn))
            if conds:
                assert val(r) == val(rx) * cv and all(value(z) == value(x) * cv for x, z in zip(xs, zs)), (xs, rx, c)
                exact += 1
            if n:
                radii = [val(M.run(f'ball_mul_pow2_{k}', f, list(x) + [rx, c])[-1]) for x in xs]
                assert max(radii) == val(r), (xs, rx, c)
                equal += 1
        elif not is_whole:
            # V4, of every length: within the stated fractions of the overflow threshold, finite.
            if val(rx) * cv <= top(f, -2) and all((abs(value(x)) + val(rx)) * cv <= top(f, -2) for x in xs):
                raise AssertionError(('V4', xs, rx, c))
    return count, whole, exact, equal


def axpy_cases(k, f, rng, rounds):
    draw = Draw(f, rng)
    count = whole = equal = both = composed = 0
    for i in range(rounds):
        n = i % 6
        wx, wy = rng.random() < 0.08, rng.random() < 0.08
        xs = [[ZERO] * k if wx else draw.group(k) for _ in range(n)]
        ys = [[ZERO] * k if wy else draw.group(k) for _ in range(n)]
        rx = PINF if wx else draw.radius()
        ry = PINF if wy else draw.radius()
        x = rng.random()
        a = rng.choice([PINF, NINF, NaN]) if x < 0.05 else draw.one()
        zs, r, flag = same_in_every_order(run_axpy, k, f, xs, ys, rx, ry, a)
        canonical(f, zs, r, flag)
        count += 1
        whole += not flag
        # P3: the composition of two ball vectors of gen/kernels, bit for bit.
        arrays = [[x[j] for x in xs] for j in range(k)]
        sc = M.run_fold(f'bv_scale_{k}', f, 'sequential', 0, arrays, [rx, a])
        ad = M.run_fold(f'bv_add_{k}', f, 'sequential', 0, sc[:-2] + [[y[j] for y in ys] for j in range(k)],
                        [sc[-2], ry])
        assert ad[-1] == flag and ad[-2] == r and ad[:-2] == [[z[j] for z in zs] for j in range(k)], (xs, ys, rx, ry, a)
        composed += 1
        if flag:
            assert not (wx or wy) and is_fin(a)
            av = val(a)
            for x, y, z in zip(xs, ys, zs):
                assert [val(v) for v in z] == [val(v) for v in M.run(
                    f'axpy_step_{k}' if k == 1 else 'axpy_step_2_1', f, [a] + list(x) + list(y))]     # V3
                ends = [av * (value(x) - val(rx)), av * (value(x) + val(rx))]
                lo, hi = min(ends) + value(y) - val(ry), max(ends) + value(y) + val(ry)
                assert value(z) - val(r) <= lo and hi <= value(z) + val(r), (x, y, rx, ry, a)          # V2
            if n:
                radii, mz, mp = [], [], []
                for x, y in zip(xs, ys):
                    s = M.run(f'ball_scale_{k}', f, list(x) + [rx, a])
                    t = M.run(f'ball_add_{k}', f, list(s[:k]) + [s[k]] + list(y) + [ry])
                    radii.append(val(t[-1]))
                    mz.append(abs(val(t[0])))
                    mp.append(abs(val(s[0])))
                assert val(r) >= max(radii), (xs, ys, rx, ry, a)
                one = any(mz[i] == max(mz) and mp[i] == max(mp) for i in range(n))
                if one:
                    assert val(r) == max(radii), (xs, ys, rx, ry, a)
                    both += 1
                equal += val(r) == max(radii)
        elif not (wx or wy) and is_fin(a):
            av = abs(val(a))
            within = av * val(rx) <= top(f, -2) and av * val(rx) + val(ry) <= top(f, -3) and all(
                (abs(value(x)) + val(rx)) * av <= top(f, -2) and
                abs(val(a) * value(x) + value(y)) + av * val(rx) + val(ry) <= top(f, -3) for x, y in zip(xs, ys))
            if within:
                raise AssertionError(('V4', xs, ys, rx, ry, a))
    return count, whole, equal, both, composed


def main():
    rng = random.Random(20261121)
    formats = [ieee_format(p, emax) for p, emax in ((2, 4), (3, 5), (4, 6))] + \
        [interp.parse_format('binary64'), interp.parse_format('binary32')]
    for f in formats:
        rounds = 1500 if f.p < 10 else 400
        for k in (1, 2):
            if k == 2 and f.p < 2:
                continue
            count, whole, exact, equal = mul_pow2_cases(k, f, rng, rounds)
            print(f'{f.name} bv_mul_pow2_{k}: {count} cases, {whole} the whole space, {exact} exact as claimed, '
                  f'the radius the largest entrywise one in {equal} of {equal}')
            if k == 2 and f.p < 3:
                continue
            count, whole, equal, both, composed = axpy_cases(k, f, rng, rounds)
            print(f'{f.name} bv_axpy_{k}: {count} cases, {whole} the whole space, the composition bit for bit in '
                  f'{composed} of {count}, the radius the largest entrywise one in {equal} (and in {both} of {both} '
                  'where one entry has both maxima)')
    print('every statement held')
    return 0


if __name__ == '__main__':
    sys.exit(main())
