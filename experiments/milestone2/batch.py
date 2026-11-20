#!/usr/bin/env python3
"""Batch kernels: the summation theorem on trees, the dot product, the exported bounds as
functions of n, and the radii of the BallVector kernels.

Statements judged (milestone2.md, "Batch kernels" and "BallVector"):

  S0  add_2_2 with a zero operand returns the other operand exactly (so a fold may start from
      the zero state without counting an addition);
  S1  for any binary tree of additions, each with relative error at most eps of its exact
      result, of height h (the largest number of additions between a leaf and the root):
          |computed - sum x_i| <= ((1 + eps)^h - 1) sum |x_i| <= gamma_h(eps) sum |x_i|,
      judged for add_1_1 (eps = u / (1 + u)) and add_2_2 (eps = 3u^2 / (1 - 4u)) on sequential,
      lane and random trees;
  S2  dot with mul_2_2 (4u^2, (3/2) eta) and such a tree:
          |computed - sum x_i y_i| <= ((1 + 4u^2)(1 + eps)^h - 1) sum |x_i y_i| + (1 + eps)^h n (3/2) eta;
  S3  bound_sum_2(m) >= gamma_m(eps) and bound_dot_2(m) = (g, t) with g >= gamma_m(4u^2),
      t >= m (3/2) eta (1 + g), for every count m with m eps <= 1/4, in toy formats, binary32 and
      binary64; and the computed dot products are within g sum |x_i y_i| + t;
  S4  BallVector: the radius of a sum and of a scaling equals the largest entrywise Ball radius;
      that of axpy is at least it; conv_radius is at least its stated expression, and the
      product of two polynomials with ball coefficients is contained; norm_upper.
  S5  the dot product of one limb, whose step is one fused operation s <- RN(x y + s), in the
      sequential order and in the lane order of proofs/theories/Folds.v (the lanes combined by
      add_1_1), with eps = u / (1 + u):
          |computed - sum x_i y_i| <= ((1 + eps)^n - 1) sum |x_i y_i| + (1 + eps)^(n-1) n eta / 2
      (the theorems dot_1_seq and dot_1_lanes of proofs/theories/SummationKernels.v), and
      bound_dot_1(n) = (g, t) dominates both terms: g >= gamma_n(eps) >= (1 + eps)^n - 1 and
      t >= n (eta / 2) (1 + g) >= (1 + eps)^(n-1) n eta / 2. Counted: how often a term of
      eta / 2 per rounded addition, the additions that combine the lanes included, would
      exceed what the statement of bound_dot_1 promises, and the values it returns.
"""
import random
import sys
from fractions import Fraction

from common import (KERNELS, MACHINE, PINF, ZERO, consts, eta, ext, fmt, interp, normalized_pairs, num,
                    pred, ru, run, succ, u_of, val)

INF = float('inf')


def v2(x):
    return num(x[0]), num(x[1])


def value(z):
    return sum(val(t) for t in z)


# ---------------------------------------------------------------------------------------------
# Trees: a leaf is an index, a node a pair of trees.

def sequential(n):
    t = 0
    for i in range(1, n):
        t = (t, i)
    return t


def lanes(n, w):
    cols = [[i for i in range(n) if i % w == j] for j in range(w)]
    trees = []
    for col in cols:
        if col:
            t = col[0]
            for i in col[1:]:
                t = (t, i)
            trees.append(t)
    t = trees[0]
    for s in trees[1:]:
        t = (t, s)
    return t


def random_tree(idx, rng):
    if len(idx) == 1:
        return idx[0]
    k = rng.randint(1, len(idx) - 1)
    return random_tree(idx[:k], rng), random_tree(idx[k:], rng)


def height(t):
    return 0 if isinstance(t, int) else 1 + max(height(t[0]), height(t[1]))


def evaluate(f, t, leaves, add):
    if isinstance(t, int):
        return leaves[t]
    return add(f, evaluate(f, t[0], leaves, add), evaluate(f, t[1], leaves, add))


def add1(f, a, b):
    return (run('add_1_1', f, a[0], b[0]),)


def add2(f, a, b):
    return run('add_2_2', f, *a, *b)


def zero_state(f, pairs):
    """S0: add_2_2(0, x) = add_2_2(x, 0) = x, limb for limb (the sign of a zero aside)."""
    for x in pairs:
        for z in (run('add_2_2', f, ZERO, ZERO, *v2(x)), run('add_2_2', f, *v2(x), ZERO, ZERO)):
            assert (val(z[0]), val(z[1])) == x, (f.name, x)


def summation(f, limbs, pool, eps, rng, rounds):
    """S1 on random operands of the pool; returns the largest error over the bound."""
    add = add1 if limbs == 1 else add2
    worst = Fraction(0)
    for _ in range(rounds):
        n = rng.randint(2, 14)
        xs = [rng.choice(pool) for _ in range(n)]
        if rng.random() < 0.3:                       # cancellation
            xs = xs[:n // 2] + [tuple(-t for t in x) for x in xs[:n // 2]] + xs[n // 2:n - n // 2]
            n = len(xs)
        leaves = [tuple(num(t) for t in x) for x in xs]
        exact = sum(sum(x) for x in xs)
        total = sum(abs(sum(x)) for x in xs)
        for tree in (sequential(n), lanes(n, 2), lanes(n, 4), random_tree(list(range(n)), rng)):
            h = height(tree)
            got = value(evaluate(f, tree, leaves, add))
            bound = ((1 + eps) ** h - 1) * total
            assert abs(got - exact) <= bound, (f.name, limbs, xs, tree)
            assert h * eps >= 1 or bound <= h * eps / (1 - h * eps) * total
            assert h <= n - 1
            if bound:
                worst = max(worst, abs(got - exact) / bound)
    return worst


def dot(f, pool, rng, rounds):
    """S2 and the exported form of S3, with mul_2_2 and add_2_2."""
    u, e = u_of(f), eta(f)
    eps_add, eps_mul, tiny = 3 * u * u / (1 - 4 * u), 4 * u * u, Fraction(3, 2) * e
    worst = worst_exported = Fraction(0)
    for _ in range(rounds):
        n = rng.randint(1, 10)
        xs = [rng.choice(pool) for _ in range(n)]
        ys = [rng.choice(pool) for _ in range(n)]
        prods = [run('mul_2_2', f, *v2(x), *v2(y)) for x, y in zip(xs, ys)]
        exact = sum(sum(x) * sum(y) for x, y in zip(xs, ys))
        total = sum(abs(sum(x) * sum(y)) for x, y in zip(xs, ys))
        g, t, ok = run('bound_dot_2', f, num(Fraction(n)))
        # The accumulator's running magnitude: a = fma(|x0|, |y0|, a), rounded to nearest. The sum
        # of |x_i y_i| is at most (1+u)^(n+2) (a + n eta/2): what its radius is computed from.
        a = ZERO
        for x, y in zip(xs, ys):
            a = interp.fma(f, num(abs(x[0])), num(abs(y[0])), a)
        assert total <= (1 + u) ** (n + 2) * (val(a) + n * e / 2), (f.name, xs, ys)
        for tree in (sequential(n), lanes(n, 2), lanes(n, 4), random_tree(list(range(n)), rng)):
            h = height(tree)
            got = value(evaluate(f, tree, prods, add2))
            bound = ((1 + eps_mul) * (1 + eps_add) ** h - 1) * total + (1 + eps_add) ** h * n * tiny
            assert abs(got - exact) <= bound, (f.name, xs, ys, tree)
            worst = max(worst, abs(got - exact) / bound)
            if ok:
                exported = val(g) * total + val(t)
                assert bound <= exported, (f.name, n)
                worst_exported = max(worst_exported, abs(got - exact) / exported)
    return worst, worst_exported


def fused_lanes(f, xs, ys, w):
    """The fused dot product of one limb in the lane order of proofs/theories/Folds.v
    (fold_lanes): the first w (n // w) elements are dealt to w lanes, each folded from zero by
    s <- RN(x y + s); the lane states are combined from lane 0 upward by add_1_1; the rest is
    folded into the result. With w = 0, and with fewer elements than lanes, it is the
    sequential order (the lanes are then all zero, and zero + zero is zero)."""
    n = len(xs)
    s = ZERO
    full = w * (n // w) if w else 0
    if w:
        states = []
        for j in range(w):
            t = ZERO
            for i in range(j, full, w):
                t = interp.fma(f, xs[i], ys[i], t)
            states.append(t)
        s = states[0]
        for t in states[1:]:
            s = run('add_1_1', f, s, t)
    for i in range(full, n):
        s = interp.fma(f, xs[i], ys[i], s)
    return s


def dot_fused(f, pool, rng, rounds):
    """S5: the fused dot product of one limb, in the sequential order and in the lane order for
    2, 4 and 8 lanes, against the proved bound and against the exported one."""
    u, e = u_of(f), eta(f)
    eps = u / (1 + u)
    worst = worst_exported = Fraction(0)
    beyond_statement = beyond_value = lane_cases = 0
    for _ in range(rounds):
        n = rng.randint(0, 12)
        xv = [rng.choice(pool)[0] for _ in range(n)]
        yv = [rng.choice(pool)[0] for _ in range(n)]
        if n and rng.random() < 0.5:                 # a product that is not a multiple of eta
            k = rng.randrange(n)
            xv[k] = rng.choice((1, -1)) * rng.randint(1, 5) * e
            yv[k] = rng.choice((1, -1)) * Fraction(1, 2)
        xs, ys = [num(t) for t in xv], [num(t) for t in yv]
        assert all(interp.member(f, t) for t in xs + ys)
        exact = sum(a * b for a, b in zip(xv, yv))
        total = sum(abs(a * b) for a, b in zip(xv, yv))
        bound = ((1 + eps) ** n - 1) * total + (1 + eps) ** max(n - 1, 0) * n * e / 2
        g, t, ok = run('bound_dot_1', f, num(Fraction(n)))
        for w in (0, 2, 4, 8):
            got = val(fused_lanes(f, xs, ys, w))
            assert abs(got - exact) <= bound, (f.name, xv, yv, w)
            if bound:
                worst = max(worst, abs(got - exact) / bound)
            if ok:
                exported = val(g) * total + val(t)
                assert bound <= exported, (f.name, n)
                if exported:
                    worst_exported = max(worst_exported, abs(got - exact) / exported)
            # A term eta / 2 per rounded addition, the w - 1 that combine the lanes included,
            # would be (n + w - 1) eta / 2. Counted: how often that exceeds what the statement
            # of bound_dot_1 promises for n terms (g = gamma_n, t = n (eta / 2) (1 + g)), and how
            # often it exceeds the values the listing returns, which are larger.
            if ok and w and n >= w:
                lane_cases += 1
                naive = ((1 + eps) ** n - 1) * total + (1 + eps) ** (n - 1) * (n + w - 1) * e / 2
                gamma = n * eps / (1 - n * eps)
                beyond_statement += naive > gamma * total + n * (e / 2) * (1 + gamma)
                beyond_value += naive > val(g) * total + val(t)
    return worst, worst_exported, (lane_cases, beyond_statement, beyond_value)


def bounds_1(f, counts):
    """bound_dot_1 against the two terms of the fused dot product, for counts m: its statement,
    g >= gamma_m(eps) and t >= m (eta / 2) (1 + g), for every count it accepts; and, for the
    counts small enough for the powers to be computed exactly, the two terms themselves (for
    the others they follow, since gamma_m(eps) >= (1 + eps)^m - 1 is a proved lemma)."""
    u, e = u_of(f), eta(f)
    eps = u / (1 + u)
    last = 0
    for m in counts:
        mv = num(Fraction(m))
        if not interp.member(f, mv):
            continue
        g, t, ok = run('bound_dot_1', f, mv)
        if not ok:                                  # claims nothing; when ok holds is reported
            continue
        assert m * eps < 1 and val(g) >= m * eps / (1 - m * eps), (f.name, m)
        assert val(t) >= m * (e / 2) * (1 + val(g)), (f.name, m)
        if m <= 1000:
            assert val(g) >= (1 + eps) ** m - 1, (f.name, m)
            assert val(t) >= (1 + eps) ** max(m - 1, 0) * m * e / 2, (f.name, m)
        last = max(last, m)
    return last


def bounds(f, counts):
    """S3: the bound kernels against the exact gamma, for counts m."""
    u, e = u_of(f), eta(f)
    eps_add, eps_mul, tiny = 3 * u * u / (1 - 4 * u), 4 * u * u, Fraction(3, 2) * e
    loose = Fraction(0)
    last = 0
    for m in counts:
        mv = num(Fraction(m))
        if not interp.member(f, mv):
            continue
        g, ok = run('bound_sum_2', f, mv)
        if not ok:
            assert m * eps_add > Fraction(1, 5), (f.name, m)     # no bound refused too early
        else:
            gamma = m * eps_add / (1 - m * eps_add)
            assert m * eps_add < 1 and val(g) >= gamma, (f.name, m)
            if m:
                loose = max(loose, val(g) / gamma)
            last = max(last, m)
        gd, td, okd = run('bound_dot_2', f, mv)
        if okd:
            assert m * eps_mul < 1 and val(gd) >= m * eps_mul / (1 - m * eps_mul), (f.name, m)
            assert val(td) >= m * tiny * (1 + val(gd)), (f.name, m)
            if m:                                   # a dot product of m terms: m - 1 additions
                assert val(gd) >= (1 + eps_mul) * (1 + eps_add) ** (m - 1) - 1, (f.name, m)
                assert val(td) >= (1 + eps_add) ** (m - 1) * m * tiny, (f.name, m)
    return loose, last


def ball_vectors(f, pool, rng, rounds):
    """S4."""
    u, e = u_of(f), eta(f)
    radii = sorted({abs(x[1]) for x in pool} | {abs(x[0]) * u for x in pool[::7]})[:40]
    radii = [r for r in radii if interp.member(f, num(r))]
    st = dict(axpy_equal=0, axpy=0, conv=0, conv_tight=Fraction(0))
    for _ in range(rounds):
        n = rng.randint(1, 6)
        cx = [rng.choice(pool) for _ in range(n)]
        cy = [rng.choice(pool) for _ in range(n)]
        rx, ry = rng.choice(radii), rng.choice(radii)
        a = rng.choice(pool)[0]
        # sum
        ent = [run('ball_add_2', f, *v2(x), num(rx), *v2(y), num(ry)) for x, y in zip(cx, cy)]
        mz = max(abs(val(z[0])) for z in ent)
        rz = run('bv_add_radius_2', f, num(mz), num(rx), num(ry))
        assert val(rz) == max(val(z[2]) for z in ent), (f.name, cx, cy, rx, ry)
        # scaling
        sc = [run('ball_scale_2', f, *v2(x), num(rx), num(a)) for x in cx]
        mt = max(abs(val(z[0])) for z in sc)
        rs = run('bv_scale_radius_2', f, num(mt), num(rx), num(a))
        assert val(rs) == max(val(z[2]) for z in sc), (f.name, cx, rx, a)
        # axpy: a X + Y, the radius of the sum computed from the vector radius of the scaling
        ax = [run('ball_add_2', f, z[0], z[1], z[2], *v2(y), num(ry)) for z, y in zip(sc, cy)]
        ctr = [run('add_2_2', f, z[0], z[1], *v2(y)) for z, y in zip(sc, cy)]
        mw = max(abs(val(z[0])) for z in ctr)
        ra = run('bv_add_radius_2', f, num(mw), rs, num(ry))
        assert val(ra) >= max(val(z[2]) for z in ax), (f.name, cx, cy, rx, ry, a)
        st['axpy'] += 1
        st['axpy_equal'] += val(ra) == max(val(z[2]) for z in ax)
        # norm_upper: the step after the largest |leading limb|
        big = max(abs(val(v2(x)[0])) for x in cx)
        nu = succ(f, big)
        true = max(abs(sum(x)) for x in cx)
        assert nu >= true and nu <= succ(f, ru(f, true)), (f.name, cx)
        # convolution of two polynomials with ball coefficients
        na, nb = rng.randint(1, 4), rng.randint(1, 4)
        pa = [rng.choice(pool) for _ in range(na)]
        pb = [rng.choice(pool) for _ in range(nb)]
        m = min(na, nb)
        g, t, ok = run('bound_dot_2', f, num(Fraction(m)))
        if not ok:
            continue
        ma = max(abs(x[0]) for x in pa)
        mb = max(abs(x[0]) for x in pb)
        rc = val(run('conv_radius', f, num(ma), num(mb), num(rx), num(ry), num(Fraction(m)), g, t))
        need = m * ((1 + u) * ma * ry + (1 + u) * mb * rx + rx * ry) + val(g) * m * (1 + u) ** 2 * ma * mb + val(t)
        assert rc >= need, (f.name, pa, pb, rx, ry)
        for k in range(na + nb - 1):
            acc = (ZERO, ZERO)
            lo = hi = Fraction(0)
            for i in range(na):
                j = k - i
                if 0 <= j < nb:
                    acc = run('add_2_2', f, *acc, *run('mul_2_2', f, *v2(pa[i]), *v2(pb[j])))
                    xa, xb = sum(pa[i]), sum(pb[j])
                    corners = [(xa + s * rx) * (xb + q * ry) for s in (-1, 1) for q in (-1, 1)]
                    lo, hi = lo + min(corners), hi + max(corners)
            c = value(acc)
            assert c - rc <= lo and hi <= c + rc, (f.name, pa, pb, rx, ry, k)
            if rc:
                st['conv_tight'] = max(st['conv_tight'], max(c - lo, hi - c) / rc)
        st['conv'] += 1
    return st


def main():
    rng = random.Random(20261119)
    rng_fused = random.Random(20261120)             # its own stream: the other draws are unchanged
    # Formats with room above, so that nothing overflows (the real model).
    for p, qmin, qtop in ((4, -10, -4), (5, -14, -6), (6, -18, -8)):
        g = fmt(p, qmin, qtop)
        f = fmt(p, qmin, 3 * (qtop + p) + 12 - qmin)
        pairs = normalized_pairs(g)
        pool2 = pairs if len(pairs) < 4000 else rng.sample(pairs, 4000)
        pool1 = [(x[0],) for x in pool2]
        u = u_of(f)
        zero_state(f, pool2)
        w1 = summation(f, 1, pool1, u / (1 + u), rng, 4000)
        w2 = summation(f, 2, pool2, 3 * u * u / (1 - 4 * u), rng, 3000)
        wd, we = dot(f, pool2, rng, 2500)
        st = ball_vectors(f, pool2, rng, 1500)
        loose, last = bounds(f, list(range(0, 40)) + [2 ** k for k in range(6, 3 * p)])
        print(f'p={p} eta=2^{qmin}: sum, largest error over ((1+eps)^h - 1) sum|x|: one limb {float(w1):.3f}, '
              f'two limbs {float(w2):.3f}; dot, over its bound {float(wd):.3f}, over the exported bound '
              f'{float(we):.3f}')
        print(f'     bound_sum_2: g / gamma at most {float(loose):.3f}, finite up to m = {last}; '
              f'axpy radius equal to the largest entrywise radius in {st["axpy_equal"]} of {st["axpy"]}; '
              f'{st["conv"]} polynomial products contained, largest needed radius over conv_radius '
              f'{float(st["conv_tight"]):.3f}')
        wf, wfe, naive = dot_fused(f, pool1, rng_fused, 4000)
        last1 = bounds_1(f, list(range(0, 40)) + [2 ** k for k in range(6, 3 * p)])
        print(f'     fused dot of one limb, sequential and 2, 4, 8 lanes: over its bound {float(wf):.3f}, '
              f'over the exported bound {float(wfe):.3f}; bound_dot_1 finite up to m = {last1}; of '
              f'{naive[0]} runs in a lane order with a finite bound, a term eta/2 per rounded addition '
              f'would exceed what the statement of bound_dot_1 promises in {naive[1]}, and the values '
              f'it returns in {naive[2]}')
    for p, qmin, qmax in ((1, -6, 8), (2, -6, 8), (3, -8, 8)):
        f = fmt(p, qmin, qmax)
        last1 = bounds_1(f, list(range(0, 12)))
        print(f'p={p} eta=2^{qmin}: bound_dot_1 dominates the two terms of the fused dot product '
              f'for every count it accepts, up to m = {last1}')
    for name in ('binary32', 'binary64'):
        f = interp.parse_format(name)
        counts = [0, 1, 2, 3, 7, 10, 100, 1000] + [2 ** k for k in range(10, f.p)] + \
                 [3 * 2 ** k for k in range(10, f.p - 2)]
        u = u_of(f)
        eps = 3 * u * u / (1 - 4 * u)
        loose = Fraction(0)
        for m in counts:
            g, ok = run('bound_sum_2', f, num(Fraction(m)))
            assert ok and val(g) >= m * eps / (1 - m * eps)
            if m:
                loose = max(loose, val(g) / (m * eps / (1 - m * eps)) - 1)
            gd, td, okd = run('bound_dot_2', f, num(Fraction(m)))
            assert okd and val(gd) >= m * 4 * u * u / (1 - m * 4 * u * u)
            assert val(td) >= m * Fraction(3, 2) * eta(f) * (1 + val(gd))
        # bound_dot_1: one limb, where m eps reaches 1/4 at about a quarter of 2^p terms.
        last1 = bounds_1(f, [0, 1, 2, 3, 7, 10, 100, 1000] + [2 ** k for k in range(10, f.p - 1)] +
                         [3 * 2 ** k for k in range(10, f.p - 3)])
        print(f'{name}: bound_sum_2 and bound_dot_2 hold for counts up to 2^{f.p - 1}; '
              f'bound_sum_2 exceeds gamma by at most {float(loose):.2e} of it; bound_dot_1 dominates '
              f'the two terms of the fused dot product for counts up to {last1}')
    print('every statement held')


if __name__ == '__main__':
    sys.exit(main())
