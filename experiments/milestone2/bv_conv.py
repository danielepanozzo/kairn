#!/usr/bin/env python3
"""The product of two polynomials whose coefficients are BallVectors (milestone2.md, "The product of
polynomials": bv_conv_k with conv_radius), first proposed in kernels/ (bv_conv_2.fold, conv_radius,
bv_conv_finish) and now in gen/kernels (bv_conv_1.fold, bv_conv_2.fold, with the same listings), run
here as the generated descriptions: the centers are the convolution conv_k; ma and mb the largest
leading magnitudes of the centers of the operands (norm_step_k, sequentially); m = min(n_x, n_y), the
largest number of terms of a coefficient, rounded up to the format; (g, t, okg) = bound_dot_k(m), one
call for every coefficient; the radius conv_radius(ma, mb, rx, ry, m, g, t); the finish
bv_conv_finish(rz, the mask of conv_k, okg); the whole space when its flag is false.

Statements judged, in exact arithmetic, on canonical BallVectors of lengths 0 to 4 (finite ones and
the whole space), in toy formats of the IEEE shape of four and five bits and in binary64 and binary32:

  C1  V1: the result is canonical (a finite ball vector of n_x + n_y - 1 coefficients, none when a
      length is 0, or the whole space), and the flag is true exactly when the radius is finite;
  C2  V2, coefficient by coefficient: every value of sum_i x_i y_(j-i), each x_i and y_k ranging
      independently over its ball, is within the radius of coefficient j (the range of the sum is the
      sum of the ranges of the products, each the least and greatest of four corners);
  C3  V3: a finite result has finite operands; its coefficients are those of conv_k;
  and counted: how often the result is finite, and the largest needed radius over the radius, as in
  batch.py. V4 is not judged here: the generator states it (finite_when, radii_when and count_when of
  encloses_coefficients), and gen/tests/test_bv_conv.py judges it.
"""
import os
import random
import sys
from fractions import Fraction

from common import KERNELS, ROOT, PINF, ZERO, interp, ir, is_fin, val

FOLDS = {}
for fn in sorted(os.listdir(os.path.join(ROOT, 'gen', 'kernels'))):
    if fn.endswith('.fold'):
        with open(os.path.join(ROOT, 'gen', 'kernels', fn), encoding='utf-8') as f:
            fd = ir.parse_fold(f.read(), fn)
        FOLDS[fd.name] = fd
KS = ir.KernelSet(dict(KERNELS), folds=FOLDS)
M = interp.Machine(KS)


def ieee_format(p, emax):
    return interp.Format(f'fp:{p}:{3 - emax - p}:{emax - p}', p, 3 - emax - p, emax - p)


def run(k, f, xs, ys, rx, ry):
    """bv_conv_k as generated (gen/kernels/bv_conv_k.fold, Machine.run_fold): the coefficients, the radius
    and the flag. The proposal of this directory composed the same kernels (conv_k, norm_step_k on each
    operand, the count, bound_dot_k, conv_radius, bv_conv_finish), and gave the same results."""
    arrays = [[x[j] for x in xs] for j in range(k)] + [[y[j] for y in ys] for j in range(k)]
    out = M.run_fold(f'bv_conv_{k}', f, 'sequential', 0, arrays, [rx, ry])
    nz = len(out[0])
    zs = [[a[i] for a in out[:-2]] for i in range(nz)]
    return zs, out[-2], out[-1], zs


class Draw:
    def __init__(self, f, rng):
        self.f, self.rng = f, rng

    def one(self):
        f, rng = self.f, self.rng
        x = rng.random()
        if x < 0.1:
            return ZERO
        q = rng.randint(f.qmax - 2, f.qmax) if x < 0.2 else rng.randint(max(f.qmin, -2 * f.p), min(f.qmax, f.p))
        return interp.canon(rng.random() < 0.5, rng.randrange(1, 2 ** f.p), q)

    def group(self, k):
        x0 = self.one()
        if k == 1:
            return [x0]
        if x0[2] == 0:
            return [x0, ZERO]
        q = max(x0[3] + x0[2].bit_length() - self.f.p, self.f.qmin)
        cands = [ZERO] + [interp.canon(s, 1, e) for e in (q - 2, q - 3) for s in (False, True)
                          if e >= self.f.qmin]
        cands = [y for y in cands if interp.member(self.f, y) and interp.eq(interp.add(self.f, x0, y), x0)]
        return [x0, self.rng.choice(cands)]

    def radius(self):
        v = self.one()
        if self.rng.random() < 0.3:
            v = interp.canon(False, self.rng.randrange(1, 2 ** self.f.p), self.f.qmin + self.rng.randrange(4))
        return (interp.NUM, False, v[2], v[3])


def products(a, b):
    corners = [a[0] * b[0], a[0] * b[1], a[1] * b[0], a[1] * b[1]]
    return min(corners), max(corners)


def judge(k, f, rng, rounds):
    draw = Draw(f, rng)
    count = finite = 0
    tight = Fraction(0)
    for i in range(rounds):
        nx, ny = rng.randint(0, 4), rng.randint(0, 4)
        wx, wy = rng.random() < 0.08, rng.random() < 0.08
        xs = [[ZERO] * k if wx else draw.group(k) for _ in range(nx)]
        ys = [[ZERO] * k if wy else draw.group(k) for _ in range(ny)]
        rx = PINF if wx else draw.radius()
        ry = PINF if wy else draw.radius()
        zs, r, flag, computed = run(k, f, xs, ys, rx, ry)
        count += 1
        assert len(zs) == (nx + ny - 1 if nx and ny else 0), (nx, ny)                     # C1
        if flag:
            assert is_fin(r) and val(r) >= 0
            for z in zs:
                assert all(is_fin(v) for v in z)
                if k == 2:
                    assert interp.eq(interp.add(f, z[0], z[1]), z[0])
            assert not (wx or wy)                                                       # C3
            finite += 1
            for j, z in enumerate(zs):
                lo = hi = Fraction(0)
                for i2 in range(nx):
                    if 0 <= j - i2 < ny:
                        cx, cy = sum(val(v) for v in xs[i2]), sum(val(v) for v in ys[j - i2])
                        a, b = products((cx - val(rx), cx + val(rx)), (cy - val(ry), cy + val(ry)))
                        lo, hi = lo + a, hi + b
                c = sum(val(v) for v in z)
                assert c - val(r) <= lo and hi <= c + val(r), (xs, ys, rx, ry, j)            # C2
                if val(r):
                    tight = max(tight, max(c - lo, hi - c) / val(r))
        else:
            assert r == PINF and all(v[0] == interp.NUM and v[2] == 0 for z in zs for v in z)
    return count, finite, tight


def main():
    rng = random.Random(20261122)
    for f in [ieee_format(4, 9), ieee_format(5, 12), interp.parse_format('binary64'), interp.parse_format('binary32')]:
        for k in (1, 2):
            count, finite, tight = judge(k, f, rng, 1500 if f.p < 10 else 400)
            print(f'{f.name} bv_conv_{k}: {count} products, {finite} finite ball vectors, {count - finite} the whole '
                  f'space; the largest needed radius over the radius {float(tight):.3f}')
    print('every statement held')
    return 0


if __name__ == '__main__':
    sys.exit(main())
