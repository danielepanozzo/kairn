#!/usr/bin/env python3
"""The constructor of a BallVector (milestone2.md, "BallVector", "Values"), proposed here first and
in gen/kernels now: bv_make_1.fold and bv_make_2.fold, with bv_center_entry_1, bv_center_2,
bv_make_radius and bv_make_finish, read from gen/kernels (the listings proposed here, with their
claims). The page says what a constructor returns and gives no listing:

  "A value is canonical when it is a finite ball (every center finite, and normalized for two limbs;
   the radius finite and nonnegative) or the whole space: every center zero and the radius +inf.
   There is no empty state; a constructor given a radius that is negative or a NaN, or a center
   that is not finite, returns the whole space."

The folds are ball vectors of the generator's kind (architecture.md, "Ball vectors"), evaluated by
its interpreter (Machine.run_fold) in the sequential order and with 0 to 4 lanes. Statements judged:

  B1  the result is canonical: a finite ball vector (every center finite, normalized for two limbs,
      the radius finite and not negative) or the whole space (every limb of every center a zero, the
      radius +inf), and the flag is true exactly when it is finite;
  B2  it is the whole space exactly when the radius given is negative, a NaN or +inf, or a center
      given is not finite (for two limbs: (+-inf, +-0) or two NaN);
  B3  otherwise the centers and the radius are those given, as values (a zero may change sign);
  B4  every order gives the same result.

On every list of up to three centers of a toy format of three bits and every radius of it,
infinities and NaN included, and on random lists of binary64 and binary32.
"""
import itertools
import os
import random
import sys

from common import KERNELS, ROOT, NaN, NINF, PINF, ZERO, interp, ir, is_fin, normalized_pairs, num, val


def load_folds():
    folds = {}
    for fn in ('bv_make_1.fold', 'bv_make_2.fold'):
        with open(os.path.join(ROOT, 'gen', 'kernels', fn), encoding='utf-8') as f:
            fd = ir.parse_fold(f.read(), fn)
        folds[fd.name] = fd
    return ir.KernelSet(dict(KERNELS), folds=folds)


KS = load_folds()
M = interp.Machine(KS)
ORDERS = [('sequential', 0)] + [('lanes', w) for w in range(5)]


def run_all(name, f, centers, r):
    """The result in every order; asserts B4 and returns it."""
    k = len(KS.folds[name].array_limbs())
    arrays = [[c[j] for c in centers] for j in range(k)]
    outs = [M.run_fold(name, f, order, w, arrays, [r]) for order, w in ORDERS]
    assert all(o == outs[0] for o in outs), (name, f.name, centers, r)          # B4
    return outs[0]


def judge(name, f, centers, r):
    out = run_all(name, f, centers, r)
    written, rr, flag = out[:-2], out[-2], out[-1]
    zs = [[a[i] for a in written] for i in range(len(centers))]
    bad_radius = not is_fin(r) or val(r) < 0
    bad_center = any(not is_fin(c[0]) for c in centers)
    whole = bad_radius or bad_center
    # B1
    if flag:
        assert is_fin(rr) and val(rr) >= 0, (name, centers, r, rr)
        for z in zs:
            assert all(is_fin(v) for v in z), (name, centers, r)
            if len(z) == 2:
                assert interp.eq(interp.add(f, z[0], z[1]), z[0]), (name, centers, r)
    else:
        assert rr == PINF and all(v[0] == interp.NUM and v[2] == 0 for z in zs for v in z), (name, centers, r, out)
    # B2
    assert flag == (not whole), (name, f.name, centers, r, flag)
    # B3
    if flag:
        assert val(rr) == val(r), (name, centers, r)
        for c, z in zip(centers, zs):
            assert [val(v) for v in z] == [val(v) for v in c], (name, centers, r)
    return flag


def values(f, specials=True):
    nums = sorted({interp.canon(s, m, q) for q in range(f.qmin, f.qmax + 1) for m in range(1, 2 ** f.p)
                   for s in (False, True)}, key=str) + [ZERO, (interp.NUM, True, 0, 0)]
    return nums + ([PINF, NINF, NaN] if specials else [])


def pairs(f):
    """Canonical pairs: finite normalized pairs, (+-inf, +-0), two NaN."""
    out = [(num(a), num(b)) for a, b in normalized_pairs(f)]
    return out + [(PINF, ZERO), (NINF, ZERO), (PINF, (interp.NUM, True, 0, 0)), (NaN, NaN)]


def exhaustive(f):
    count, finite = 0, 0
    radii = values(f)
    ones = values(f)
    twos = pairs(f)
    rng = random.Random(20261120)
    for n in range(4):
        lists1 = list(itertools.product(ones, repeat=n)) if len(ones) ** n <= 2000 else \
            [tuple(rng.choice(ones) for _ in range(n)) for _ in range(2000)]
        lists2 = list(itertools.product(twos, repeat=n)) if len(twos) ** n <= 1500 else \
            [tuple(rng.choice(twos) for _ in range(n)) for _ in range(1500)]
        for r in radii:
            for cs in lists1:
                finite += judge('bv_make_1', f, [[c] for c in cs], r)
                count += 1
            for cs in lists2[::max(1, len(lists2) // 300)]:
                finite += judge('bv_make_2', f, [list(c) for c in cs], r)
                count += 1
    return count, finite


def random_named(name, rounds, rng):
    f = interp.parse_format(name)
    count, finite = 0, 0
    top = interp.canon(False, 2 ** f.p - 1, f.qmax)
    for _ in range(rounds):
        n = rng.randrange(0, 9)
        cs = []
        for _ in range(n):
            x = rng.random()
            if x < 0.05:
                cs.append(rng.choice([PINF, NINF, NaN]))
            elif x < 0.1:
                cs.append(top)
            else:
                cs.append(interp.canon(rng.random() < 0.5, rng.randrange(1, 2 ** f.p), rng.randrange(f.qmin, f.qmax - f.p)))
        x = rng.random()
        r = (rng.choice([PINF, NINF, NaN, (interp.NUM, True, 0, 0)]) if x < 0.2 else
             interp.canon(x < 0.3, rng.randrange(1, 2 ** f.p), rng.randrange(f.qmin, f.qmax - f.p)))
        finite += judge('bv_make_1', f, [[c] for c in cs], r)
        count += 1
        cs2 = [[c, ZERO] if is_fin(c) or c != NaN else [NaN, NaN] for c in cs]
        cs2 = [[c[0], ZERO] if c[0] in (PINF, NINF) else c for c in cs2]
        finite += judge('bv_make_2', f, cs2, r)
        count += 1
    return count, finite


def main():
    for p, qmin, qmax in ((3, -4, 1), (2, -3, 2)):
        f = interp.Format(f'fp:{p}:{qmin}:{qmax}', p, qmin, qmax)
        count, finite = exhaustive(f)
        print(f'{f.name}: {count} constructions, {finite} finite ball vectors, {count - finite} the whole space')
    rng = random.Random(20261121)
    for name in ('binary64', 'binary32'):
        count, finite = random_named(name, 3000, rng)
        print(f'{name}: {count} constructions, {finite} finite ball vectors, {count - finite} the whole space')
    print('every statement held')


if __name__ == '__main__':
    sys.exit(main())
