#!/usr/bin/env python3
"""The accumulator (milestone2.md, "The accumulator"): the kernels acc_add_k, acc_mul_k and
acc_merge_k and the radius acc_radius proposed in kernels/, judged in exact arithmetic.

The page gives acc_radius_k no listing: it says only that it "has the form of conv_radius" and that
the radius rests on the inequality below. The listing of kernels/acc_radius.kernel is the one
proposed for it, one kernel for both numbers of limbs (the magnitudes are summed in T in both), and
this script is its check. It is not in gen/kernels: there its constants, shared with those of
ball_mul_pow2_1 and bound_dot_1 and named after the first kernel in the order of the names, would
rename up_ball_mul_pow2_1_0 and up_bound_dot_1_2, which proofs/theories names.

The six others are proposals too, not in gen/kernels, because of A4: each claims of its second
output b (the sum of magnitudes) that it is the rounding to nearest of a value of its own (a claim
rounded b nearest value=..., which the generator does not have either), and in the format itself b
is +inf in some cases where the running sum, output limb 0, is finite. The claims file is read
whenever output limb 0 is finite, so there that claim is false; in the real model, where nothing
overflows, it holds. Each description carries the claims proposed for it as comments. Statements
judged:

  A1  the inequality the radius rests on: after any sequence of add(x), add_product(x, y) and
      merge(other) with valid operands, with n the number of terms (a merge adds the counts, a sum
      x is the product x * 1) and a the running sum of the magnitudes of the leading limbs that the
      kernels compute (a = RN(a + |x0|), RN(|x0| |y0| + a), RN(a + a')),
          sum_i |x_i y_i| <= (1 + u)^(n+2) (a + n eta / 2);
  A2  acc_radius(a, m, g, t) = (r, ok), for every a, g, t >= 0 and m = 0 or m >= 1 of the format:
          r >= g (1 + u)^2 (1 + m u + 2 m^2 u^2) (a + m eta / 2) + t,
      and ok implies m u <= 1/2 (the claims upper and holds proposed for it);
  A3  the chain of the page: with (g, t, ok) = bound_dot_k(n) and (r, ok') = acc_radius(a, n, g, t),
      when ok and ok' are true,
          |s - Sigma| <= g sum_i |x_i y_i| + t <= r,
      s the running k-number and Sigma the exact sum of what was added: the first inequality is the
      statement of dot for n terms in any tree (a merge is a node of the tree), the second A1 with
      (1 + u)^n <= 1 + n u (1 + 2 n u) for n u <= 1/2 (pow_minus_1_le_gamma and gamma_le_poly of
      proofs/theories/Summation.v, with eps = u) and A2;
  A4  in the format itself, with no room above: b is the rounding to nearest of its value (a + |x0|,
      a + |x0| |y0|, a + c) with the overflow rule, +inf when it rounds to 2^(qmax+p) or above
      (common.rn, which shares nothing with the interpreter), for nonnegative a and c; and the
      cases where b is +inf while output limb 0 is finite, counted for each kernel: there are some
      for each of the six.

Run on toy formats with room above (nothing overflows: the real model), in binary64 and binary32
for A2, and on formats of 1 to 3 bits for A2; A4 on the toy formats without the room.
"""
import random
import sys
from fractions import Fraction

from common import ZERO, ext, finite_numbers, fmt, interp, is_fin, normalized_pairs, num, rn, run, u_of, eta, val


def v2(x):
    return num(x[0]), num(x[1])


class Acc:
    """An accumulator of k limbs: the running k-number s (interpreter values), the running sum a of
    magnitudes, the count n, and what was added, exactly: the list of terms (x, y) (y = 1 for a
    sum)."""

    def __init__(self, f, k):
        self.f, self.k = f, k
        self.s = [ZERO] * k
        self.a = ZERO
        self.n = 0
        self.terms = []

    def add(self, x):
        x = list(x)
        out = run(f'acc_add_{self.k}', self.f, *self.s, self.a, *x)
        self.s, self.a = list(out[:-1]), out[-1]
        self.n += 1
        self.terms.append((sum(val(v) for v in x), Fraction(1)))

    def add_product(self, x, y):
        x, y = list(x), list(y)
        out = run(f'acc_mul_{self.k}', self.f, *self.s, self.a, *x, *y)
        self.s, self.a = list(out[:-1]), out[-1]
        self.n += 1
        self.terms.append((sum(val(v) for v in x), sum(val(v) for v in y)))

    def merge(self, other):
        out = run(f'acc_merge_{self.k}', self.f, *self.s, self.a, *other.s, other.a)
        self.s, self.a = list(out[:-1]), out[-1]
        self.n += other.n
        self.terms += other.terms


def build(f, k, pool, rng, depth=0):
    """An accumulator after a random sequence of add, add_product and merge (of accumulators built
    the same way, two levels deep at most)."""
    acc = Acc(f, k)
    for _ in range(rng.randint(0, 7)):
        r = rng.random()
        if r < 0.15 and depth < 2:
            acc.merge(build(f, k, pool, rng, depth + 1))
        elif r < 0.45:
            acc.add(rng.choice(pool))
        else:
            acc.add_product(rng.choice(pool), rng.choice(pool))
    return acc


def radius_claim(f, a, m, g, t):
    u, e = u_of(f), eta(f)
    return g * (1 + u) ** 2 * (1 + m * u + 2 * m * m * u * u) * (a + m * e / 2) + t


def accumulators(f, k, pool, rng, rounds):
    """A1 and A3 on random accumulators; returns (largest A1 ratio, largest error over the radius,
    cases where the radius was finite, cases)."""
    u, e = u_of(f), eta(f)
    worst_a1 = worst_r = Fraction(0)
    judged = 0
    for _ in range(rounds):
        acc = build(f, k, pool, rng)
        n, a = acc.n, val(acc.a)
        total = sum(abs(x * y) for x, y in acc.terms)
        exact = sum(x * y for x, y in acc.terms)
        rhs = (1 + u) ** (n + 2) * (a + n * e / 2)
        assert total <= rhs, (f.name, k, acc.terms, a)                                   # A1
        if rhs:
            worst_a1 = max(worst_a1, total / rhs)
        mv = num(Fraction(n))
        if not interp.member(f, mv):
            continue
        g, t, ok = run(f'bound_dot_{k}', f, mv)
        r, ok2 = run('acc_radius', f, acc.a, mv, g, t)
        if not (ok and ok2):
            continue
        judged += 1
        err = abs(sum(val(v) for v in acc.s) - exact)
        chain = val(g) * total + val(t)
        assert err <= chain, (f.name, k, acc.terms)                                      # dot
        assert chain <= val(r), (f.name, k, acc.terms, val(r))                           # A3
        if val(r):
            worst_r = max(worst_r, err / val(r))
    return worst_a1, worst_r, judged


def radii(f, rng, rounds, counts):
    """A2 on random nonnegative a, g, t of the format (subnormal ones among them) and counts m."""
    u = u_of(f)
    nums = sorted({abs(val(interp.canon(False, m, q))) for q in range(f.qmin, min(f.qmax, f.qmin + 3 * f.p + 40) + 1)
                   for m in (1, 3, 2 ** f.p - 1, 2 ** (f.p - 1) + 1) if m < 2 ** f.p})
    nums = [Fraction(0)] + nums
    worst, accepted = Fraction(0), 0
    for i in range(rounds):
        a, g, t = rng.choice(nums), rng.choice(nums), rng.choice(nums)
        m = Fraction(counts[i % len(counts)])
        mv = num(m)
        if not interp.member(f, mv):
            continue
        r, ok = run('acc_radius', f, num(a), mv, num(g), num(t))
        if r[0] != interp.NUM:
            continue                    # an overflow: the real model has none
        need = radius_claim(f, a, m, g, t)
        assert val(r) >= need, (f.name, a, m, g, t, val(r), need)                       # A2
        if ok:
            accepted += 1
            assert m * u <= Fraction(1, 2), (f.name, m)
        if val(r):
            worst = max(worst, need / val(r))
    return worst, accepted


def overflow_corner(f, k, pool, rng, rounds):
    """A4 in the format f itself; returns {kernel: (cases, cases with b = +inf and output limb 0
    finite)}."""
    mags = [num(x) for x in finite_numbers(f, nonneg=True)]
    out = {}
    for op in ('add', 'mul', 'merge'):
        name = f'acc_{op}_{k}'
        corner = 0
        for _ in range(rounds):
            s, a = rng.choice(pool), rng.choice(mags)
            if op == 'add':
                x = rng.choice(pool)
                args, value = (*s, a, *x), val(a) + abs(val(x[0]))
            elif op == 'mul':
                x, y = rng.choice(pool), rng.choice(pool)
                args, value = (*s, a, *x, *y), val(a) + abs(val(x[0])) * abs(val(y[0]))
            else:
                v, c = rng.choice(pool), rng.choice(mags)
                args, value = (*s, a, *v, c), val(a) + val(c)
            got = run(name, f, *args)
            assert ext(got[-1]) == rn(f, value), (name, f.name, args, got)                      # A4
            if is_fin(got[0]) and not is_fin(got[-1]):
                corner += 1
        assert corner, (name, f.name)
        out[name] = (rounds, corner)
    return out


def main():
    rng = random.Random(20261121)
    for p, qmin, qtop in ((4, -10, -4), (5, -14, -6), (6, -18, -8)):
        g = fmt(p, qmin, qtop)
        f = fmt(p, qmin, 3 * (qtop + p) + 12 - qmin)
        pairs = normalized_pairs(g)
        pool2 = pairs if len(pairs) < 3000 else rng.sample(pairs, 3000)
        pool1 = [(x[0],) for x in pool2]
        for k, pool in ((1, [tuple(num(t) for t in x) for x in pool1]), (2, [v2(x) for x in pool2])):
            a1, wr, judged = accumulators(f, k, pool, rng, 4000)
            print(f'p={p} eta=2^{qmin} k={k}: sum|x y| over (1+u)^(n+2) (a + n eta/2) at most {float(a1):.3f}; '
                  f'{judged} accumulators with a finite radius, error over the radius at most {float(wr):.3f}')
        counts = [0, 1, 2, 3, 5, 8, 13] + [2 ** j for j in range(4, p + 3)]
        worst, accepted = radii(f, rng, 10000, counts)
        print(f'     acc_radius: its claimed expression over r at most {float(worst):.3f}; ok true in {accepted} cases')
        # A4 in the format g itself, its pairs the operands.
        small = pairs if len(pairs) < 1500 else rng.sample(pairs, 1500)
        for k, pool in ((1, [(num(x[0]),) for x in small]), (2, [v2(x) for x in small])):
            found = overflow_corner(g, k, pool, rng, 3000)
            print(f'     in the format itself, k={k}: b the rounding with overflow in every case; b = +inf with '
                  'output limb 0 finite in ' + ', '.join(f'{c} of {n} ({name})' for name, (n, c) in found.items()))
    for p, qmin, qmax in ((1, -6, 8), (2, -6, 8), (3, -8, 8)):
        f = fmt(p, qmin, qmax)
        worst, accepted = radii(f, rng, 3000, [0, 1, 2, 3, 4, 6, 8])
        print(f'p={p} eta=2^{qmin}: acc_radius: its claimed expression over r at most {float(worst):.3f}; '
              f'ok true in {accepted} cases')
    for name in ('binary32', 'binary64'):
        f = interp.parse_format(name)
        counts = [0, 1, 2, 3, 7, 100, 1000] + [2 ** j for j in range(10, f.p + 1, 3)]
        worst, accepted = radii(f, rng, 10000, counts)
        print(f'{name}: acc_radius: its claimed expression over r at most {float(worst):.6f}; ok true in '
              f'{accepted} cases')
    print('every statement held')


if __name__ == '__main__':
    sys.exit(main())
