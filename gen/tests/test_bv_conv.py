"""The product of two polynomials whose coefficients are BallVectors (docs/developer/design/milestone2.md,
"The product of polynomials"; docs/developer/architecture.md, "Ball vectors"): bv_conv_1, bv_conv_2.

- Their rules: the products of gen/kernels are accepted, and each way of getting one wrong is refused
  (rules.bv_conv_rules).
- The interpreter, on formats of the shape of IEEE 754 of a few bits and in binary64 and binary32, on
  canonical BallVectors (finite ones and the whole space) of lengths 0 to 6: V1 (canonical, n_x + n_y - 1
  coefficients), the flag, V2 (containment coefficient by coefficient, every entry ranging independently
  over its ball, in exact arithmetic), V3 (the coefficients are the convolution's, the radius conv_radius on
  the maxima, the radii, the count and the bound), V4 with its conditions (finite_when, radii_when,
  count_when), at random and near the limits of the conditions, empty operands included; the count's
  condition makes the bound given in every format tried.
- The compiled C++: F_seq of every build of the runner, bit for bit against the interpreter.
- The line protocol, the models and the statements, the claims, the C++ text and the counts.
"""
import random
import unittest
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F

import common
import test_bv as bvt
import test_cxx as cxx
import test_ieee_writers as writers
import test_statements as st
from kairn_gen import claims, consts, cpp, expr, interp, ir, objcode, rocq, rules

PRODUCTS = ('bv_conv_1', 'bv_conv_2')
ZERO = (interp.NUM, False, 0, 0)
PINF = (interp.INF, False)
exact, finite = writers.exact, writers.finite


def limbs_of(fd):
    return len(fd.arrays[0].limbs)


def case(fd, f, rng, nx, ny, whole=0.1):
    """(scalars, xs, ys) of one case: each operand a canonical BallVector, the whole space with probability
    `whole`; the entries lists of limbs."""
    fin = bvt.FiniteDraw(f, rng)
    k = limbs_of(fd)
    wx, wy = rng.random() < whole, rng.random() < whole
    xs = [[ZERO] * k if wx else fin.group(k) for _ in range(nx)]
    ys = [[ZERO] * k if wy else fin.group(k) for _ in range(ny)]
    radii = []
    for w in (wx, wy):
        x = fin.one()
        radii.append(PINF if w else (interp.NUM, False, x[2], x[3]))
    return radii, xs, ys


def arrays_of(fd, xs, ys):
    k = limbs_of(fd)
    return [[x[j] for x in xs] for j in range(k)] + [[y[j] for y in ys] for j in range(k)]


def run(m, fd, f, scalars, xs, ys):
    """(coefficients, radius, flag) of the interpreter."""
    out = m.run_fold(fd.name, f, 'sequential', 0, arrays_of(fd, xs, ys), scalars)
    nz = len(out[0])
    return [[a[i] for a in out[:-2]] for i in range(nz)], out[-2], out[-1]


def value(g):
    return sum(exact(v) for v in g)


def conditions(fd, f, scalars, xs, ys):
    """Whether the conditions of V4 hold: count_when, radii_when, and finite_when at every entry of each
    array (a condition naming one array) and every pair of entries (naming both), in exact arithmetic."""
    e = fd.ensures[0]
    x, y = (g.name for g in fd.arrays)
    n = min(len(xs), len(ys))
    env = {g.name: exact(v) for g, v in zip(fd.scalars, scalars)}
    env[rules.COUNT_NAME] = F(n)
    top = F(2) ** (f.qmax + f.p)
    for c in e['count_when']:
        if consts.evaluate(expr.parse(c['le']), common.kernels(), f.p, f.qmin, {rules.COUNT_NAME: F(n)}) > \
                expr.evaluate(expr.parse(c['than']), {}):
            return False
    for c in e['finite_when'] + e['radii_when']:
        tree = expr.parse(c['abs_le'])
        names = expr.names(tree)
        lim = top * F(2) ** c['exp']
        if x in names and y in names:
            envs = [dict(env, **{x: value(a), y: value(b)}) for a in xs for b in ys]
        elif x in names:
            envs = [dict(env, **{x: value(a)}) for a in xs]
        elif y in names:
            envs = [dict(env, **{y: value(b)}) for b in ys]
        else:
            envs = [env]
        if any(abs(expr.evaluate(tree, v)) > lim for v in envs):
            return False
    return True


def judge(m, ks, fd, f, scalars, xs, ys, out):
    """The failures of V1 to V4 and of the flag on one case."""
    zs, r, flag = out
    nx, ny = len(xs), len(ys)
    bad = []
    if len(zs) != (nx + ny - 1 if nx and ny else 0):
        return ['V1: the number of coefficients']
    if finite(r):
        if exact(r) < 0:
            bad.append('V1: a negative radius')
        for z in zs:
            if not all(finite(v) for v in z) or (len(z) == 2 and not interp.eq(interp.add(f, z[0], z[1]), z[0])):
                bad.append('V1: a coefficient not finite and normalized')
                break
    elif r != PINF or not all(v[0] == interp.NUM and v[2] == 0 for z in zs for v in z):
        bad.append('V1: not the whole space')
    if flag != finite(r):
        bad.append('the flag')
    if bad:
        return bad
    rx, ry = scalars
    if finite(r):
        # V2: coefficient j of the exact product of members, each entry independently in its ball: the
        # sum over its terms of the ranges of the products (each the least and greatest of four corners).
        for j, z in enumerate(zs):
            lo = hi = F(0)
            for i in range(max(0, j - ny + 1), min(j, nx - 1) + 1):
                a, b = value(xs[i]), value(ys[j - i])
                ps = [p * q for p in (a - exact(rx), a + exact(rx)) for q in (b - exact(ry), b + exact(ry))]
                lo, hi = lo + min(ps), hi + max(ps)
            c = value(z)
            if not (c - exact(r) <= lo and hi <= c + exact(r)):
                bad.append(('V2', j))
        # V3: finite radii; the coefficients the convolution's, the radius the radius kernel's, in the
        # format widened so that nothing overflows.
        if not (finite(rx) and finite(ry)):
            bad.append('V3: a finite result from an operand that is the whole space')
            return bad
        wide = writers.widened(f)
        conv = ks.folds[fd.centers]
        want = m.run_fold(conv.name, wide, 'sequential', 0, arrays_of(fd, xs, ys))
        if [[exact(v) for v in z] for z in zs] != [[exact(a[i]) for a in want[:-1]] for i in range(len(zs))]:
            bad.append('V3: the coefficients are not those of the convolution')
        env = {fd.scalars[0].name: rx, fd.scalars[1].name: ry}
        for rec, part in zip(fd.records, (xs, ys)):
            s = [ZERO, True]
            for v in part:
                s = m.run(rec[0], wide, s + list(v))
            env.update(zip(rec[2], s))
        env[fd.count] = interp.count_up(wide, min(nx, ny))
        env.update(zip(fd.bound[2], m.run(fd.bound[0], wide, [env[fd.count]])))
        rz = m.run(fd.radius[0], wide, [env[a] for a in fd.radius[1]])[0]
        if exact(rz) != exact(r):
            bad.append('V3: the radius is not conv_radius on the maxima, the radii, the count and the bound')
    elif finite(rx) and finite(ry) and conditions(fd, f, scalars, xs, ys):
        bad.append('V4: not finite')
    return bad


def _judge(job):
    name, p, emax, rounds, seed = job
    ks = common.kernels()
    fd = ks.folds[name]
    m = interp.Machine(ks)
    f = writers.ieee_format(p, emax) if p else interp.parse_format(emax)
    rng = random.Random(f'bv_conv:{name}:{f.name}:{seed}')
    bad, count, whole, within = [], 0, 0, 0
    for _ in range(rounds):
        scalars, xs, ys = case(fd, f, rng, rng.randint(0, 6), rng.randint(0, 6))
        out = run(m, fd, f, scalars, xs, ys)
        bad += [(name, f.name, len(xs), len(ys), x) for x in judge(m, ks, fd, f, scalars, xs, ys, out)]
        count += 1
        whole += not out[2]
        within += finite(scalars[0]) and finite(scalars[1]) and conditions(fd, f, scalars, xs, ys)
    return name, f.name, count, whole, within, bad[:5]


def near(f, rng, e, k):
    """A canonical group of magnitude about 2^e, at most the largest number."""
    e = min(e, f.qmax + f.p - 1)
    x0 = interp.canon(rng.random() < 0.5, rng.randrange(2 ** (f.p - 1), 2 ** f.p), e - f.p + 1)
    if not interp.member(f, x0):
        x0 = interp.largest(f, x0[1])
    return [x0] + [ZERO] * (k - 1)


def radius_near(f, rng, e):
    if e < f.qmin or rng.random() < 0.15:
        return ZERO
    e = min(e, f.qmax + f.p - 1)
    v = interp.canon(False, rng.randrange(2 ** (f.p - 1), 2 ** f.p), e - f.p + 1)
    return v if interp.member(f, v) else interp.largest(f, False)


def _limits(job):
    """Cases aimed at the limits of the conditions of V4: the pairs, an operand empty (n = 0, the other
    array with the first's radius), both empty (the radii alone)."""
    name, p, emax, rounds = job
    ks = common.kernels()
    fd = ks.folds[name]
    m = interp.Machine(ks)
    f = writers.ieee_format(p, emax) if p else interp.parse_format(emax)
    rng = random.Random(f'bv_conv limits:{name}:{f.name}')
    k = limbs_of(fd)
    top = f.qmax + f.p
    E = fd.ensures[0]['finite_when'][0]['exp']
    bad, within = [], 0
    for r in range(rounds):
        nx, ny = rng.randint(0, 6), rng.randint(0, 6)
        if r % 4 == 0:
            nx = 0
        elif r % 4 == 1:
            ny = 0
        n = min(nx, ny)
        spread = rng.randint(-3, 3)
        hx = (top + E - (n.bit_length() if n else 0)) // 2 + spread
        hy = top + E - (n.bit_length() if n else 0) - hx
        xs = [near(f, rng, hx - rng.randint(0, 2), k) if rng.random() > 0.1 else [ZERO] * k for _ in range(nx)]
        ys = [near(f, rng, hy - rng.randint(0, 2), k) if rng.random() > 0.1 else [ZERO] * k for _ in range(ny)]
        scalars = [radius_near(f, rng, hx - rng.randint(0, 4)), radius_near(f, rng, hy - rng.randint(0, 4))]
        if not conditions(fd, f, scalars, xs, ys):
            continue
        within += 1
        out = run(m, fd, f, scalars, xs, ys)
        bad += [(name, f.name, nx, ny, x) for x in judge(m, ks, fd, f, scalars, xs, ys, out)]
    return name, f.name, within, bad[:5]


def formats():
    # The smallest format of the precision the statement is printed from (emax = prec + 1: binary_float
    # asks prec < emax), and wider ones.
    return [(p, emax) for p, emax in ((4, 5), (4, 7), (4, 9), (5, 8), (5, 12), (6, 10), (6, 14))]


# The condition on the count as first claimed for bv_conv_2, n (unit(mul_2_2) + eta) <= 1/16: in a format
# of precision p >= 8 with p < emax <= 2p - 7 it admits counts above the largest number, whose count
# rounded up is +infinity, and then the product is the whole space (docs/proofs/index.md). Restated with
# the smallest normal number eta/(2u) in place of eta, which bounds n by 2^(emax - 6).
FIRST_COUNT_WHEN = 'n*(unit(mul_2_2)+eta)'


def count_formats():
    """(p, emax) of formats of the IEEE shape for the count: precisions 4 to 12, each with its smallest
    exponent range (emax = p + 1) and a few more, among them, from p = 8 on, those with emax at most
    2p - 7, where the largest number is below counts that FIRST_COUNT_WHEN admits."""
    return [(p, emax) for p in range(4, 13)
            for emax in sorted({p + 1, p + 2, p + 3, 2 * p - 8, 2 * p - 7, 2 * p - 6, 2 * p, 2 * p + 8}) if emax > p]


def count_limit(fd, f, text=None):
    """The largest n that the condition on the count of fd (or the condition `text`) admits in format f."""
    ks = common.kernels()
    c = fd.ensures[0]['count_when'][0]
    tree, limit = expr.parse(text or c['le']), expr.evaluate(expr.parse(c['than']), {})
    top = int(limit / consts.evaluate(tree, ks, f.p, f.qmin, {rules.COUNT_NAME: F(1)}))
    while consts.evaluate(tree, ks, f.p, f.qmin, {rules.COUNT_NAME: F(top)}) > limit:
        top -= 1
    while consts.evaluate(tree, ks, f.p, f.qmin, {rules.COUNT_NAME: F(top + 1)}) <= limit:
        top += 1
    return top


class Rules(unittest.TestCase):
    BASE = open(f'{common.GEN}/kernels/bv_conv_2.fold', encoding='utf-8').read().replace(
        'fold:          bv_conv_2', 'fold:          tb')

    def refusals(self, text):
        ks = common.kernels()
        fd = ir.parse_fold(text, 'tb.fold')
        return [str(e) for e in rules.fold_rules(fd, ir.ordered(dict(ks), dict(ks.folds, tb=fd)))]

    def test_the_products_are_accepted(self):
        ks = common.kernels()
        for name in PRODUCTS:
            fd = ks.folds[name]
            self.assertTrue(fd.is_bv_conv and not (fd.is_bv or fd.is_conv or fd.is_map), name)
            self.assertEqual([str(e) for e in rules.fold_rules(fd, ks)], [], name)
        self.assertEqual(self.refusals(self.BASE), [])

    def test_refused(self):
        for old, new, words in (
                ('centers:       conv_2', 'centers:       dot_2', 'is not a convolution'),
                ('arrays:        stored x = x0 x1, stored y = y0 y1', 'arrays:        stored x = x0 x1, supplied y = y0 y1',
                 'stored (the centers of BallVectors)'),
                ('record:        (mb, okb) = norm_step_2(mb, okb, y)', 'record:        (mb, okb) = norm_step_2(mb, okb, x)',
                 'the step of a fold of maxima'),
                ('record:        (mb, okb) = norm_step_2(mb, okb, y)\n', '', 'two lines'),
                ('state:         ma, mask oka, mb, mask okb', 'state:         ma, mask oka', 'two folds of maxima'),
                ('bound:         (g, t, okg) = bound_dot_2(m)', 'bound:         (g, t, okg) = bound_dot_1(m)',
                 'bounds the products of mul_1_1'),
                ('bound:         (g, t, okg) = bound_dot_2(m)', 'bound:         (g, t, okg) = bound_sum_2(m)',
                 'to two limbs and a mask'),
                ('finish:        (r, flag) = bv_conv_finish(rz, finite, okg)',
                 'finish:        (r, flag) = bv_conv_finish(rz, okg, finite)', 'finish:'),
                ('finish:        (r, flag) = bv_conv_finish(rz, finite, okg)',
                 'finish:        (r, flag) = norm_finish_1(rz, finite)', 'finish:'),
                ('radius:        rz = conv_radius(ma, mb, rx, ry, m, g, t)',
                 'radius:        rz = conv_radius(ma, oka, rx, ry, m, g, t)', 'radius:'),
                ('count:         m = min(n_x, n_y)', 'count:         ma = min(n_x, n_y)', 'names of their own'),
                ('requires:      ball_vector y ry\n', '', 'every array is the centers of a BallVector'),
                (' count_when=le(n*(unit(mul_2_2)+eta/(2*u)),1/16)', '', 'count_when comes with finite_when'),
                (' radii_when=abs_le(rx*ry,-2)', '', 'finite_when and radii_when come together'),
                ('radii_when=abs_le(rx*ry,-2)', 'radii_when=abs_le(x*ry,-2)', "the scalars' names only"),
                ('flag=flag', 'flag=finite', 'the flag flag'),
                ('orders:        sequential', 'orders:        sequential, lanes', 'orders: sequential'),
                ('domain:        extended\n', '', 'extended domain'),
                ('min_precision: 4', 'min_precision: 3', 'min_precision')):
            text = self.BASE.replace(old, new)
            self.assertNotEqual(text, self.BASE, old)
            errs = self.refusals(text)
            self.assertTrue(any(words in e for e in errs), (old, words, errs))

    def test_the_kernels_claims(self):
        """at_most of conv_radius and if_all of bv_conv_finish, refused where they do not belong."""
        ks = common.kernels()
        for name, old, new, words in (
                ('conv_radius', 'requires:      at_most g 1', 'requires:      at_most g 1/2', 'a positive integer'),
                ('conv_radius', 'requires:      at_most g 1', 'requires:      at_most q 1', 'a positive integer'),
                ('bv_conv_finish', 'if_all=okc,okg', 'if_all=okc,rz', 'two mask inputs or more'),
                ('bv_conv_finish', 'if_all=okc,okg', 'if_all=okc,okc', 'two mask inputs or more')):
            with open(f'{common.GEN}/kernels/{name}.kernel', encoding='utf-8') as fh:
                text = fh.read()
            self.assertIn(old, text)
            k = ir.parse_kernel(text.replace(old, new), f'{name}.kernel')
            errs = [str(e) for e in rules.claims(k, ks)]
            self.assertTrue(any(words in e for e in errs), (name, new, errs))


class Interp(unittest.TestCase):
    def test_v1_to_v4(self):
        jobs = []
        for name in PRODUCTS:
            jobs += [(name, p, emax, common.size(250, 2500), 'r') for p, emax in formats()]
            jobs += [(name, None, fmt, common.size(100, 800), 'r') for fmt in ('binary64', 'binary32')]
        with ProcessPoolExecutor(max_workers=common.JOBS) as ex:
            results = list(ex.map(_judge, jobs))
        self.assertEqual([r[5] for r in results if r[5]], [])
        for name in PRODUCTS:
            mine = [r for r in results if r[0] == name]
            self.assertGreater(sum(r[2] for r in mine), 1000, name)
            self.assertGreater(sum(r[3] for r in mine), 100, name)      # the whole space, often
            self.assertGreater(sum(r[2] - r[3] for r in mine), 200, name)  # a finite product
            self.assertGreater(sum(r[4] for r in mine), 200, name)      # within the conditions of V4

    def test_v4_at_its_limits(self):
        jobs = [(name, p, emax, common.size(600, 6000)) for name in PRODUCTS for p, emax in formats()]
        jobs += [(name, None, fmt, common.size(200, 1500)) for name in PRODUCTS for fmt in ('binary64', 'binary32')]
        with ProcessPoolExecutor(max_workers=common.JOBS) as ex:
            results = list(ex.map(_limits, jobs))
        self.assertEqual([r[3] for r in results if r[3]], [])
        for name in PRODUCTS:
            self.assertGreater(sum(r[2] for r in results if r[0] == name), 1000, name)

    def test_the_count_gives_the_bound(self):
        """count_when gives the bound: for every n it admits, the count rounded up is a number of the format
        (not +infinity) and bound_dot_k of it is ok. In 36 formats of precisions 4 to 9 with room above and
        many exponent ranges, and in formats of the IEEE shape of precisions 4 to 12 (count_formats), each
        with its smallest exponent range and, from p = 8 on, those with p < emax <= 2p - 7, where
        FIRST_COUNT_WHEN admitted counts above the largest number (checked here too); every n up to the
        limit, or 3000 of them and the limit. binary32 and binary64 admit the same counts as with
        FIRST_COUNT_WHEN."""
        ks = common.kernels()
        m = interp.Machine(ks)
        tried, ieee_shaped, overflowed = 0, 0, set()
        for name in PRODUCTS:
            fd = ks.folds[name]
            c = fd.ensures[0]['count_when'][0]
            limit = expr.evaluate(expr.parse(c['than']), {})
            fmts = [interp.Format(f'fp:{p}:{qmin}:{20}', p, qmin, 20)
                    for p in range(4, 10) for qmin in (-1, -2, -4, -8, -16, -40)]
            fmts += [writers.ieee_format(p, emax) for p, emax in count_formats()]
            for f in fmts:
                top = count_limit(fd, f)
                for n in sorted(set(range(0, min(top, 3000) + 1)) | {top}):
                    self.assertLessEqual(consts.evaluate(expr.parse(c['le']), ks, f.p, f.qmin,
                                                         {rules.COUNT_NAME: F(n)}), limit)
                    count = interp.count_up(f, n)
                    self.assertTrue(finite(count), (name, f.name, n))
                    g, t, ok = m.run(fd.bound[0], f, [count])
                    self.assertTrue(ok, (name, f.name, n))
                    tried += 1
                    ieee_shaped += f.qmax + f.p + f.qmin + f.p == 3
                if name == 'bv_conv_2' and f.qmax + f.p + f.qmin + f.p == 3:
                    first = count_limit(fd, f, FIRST_COUNT_WHEN)
                    if not finite(interp.count_up(f, first)):
                        overflowed.add((f.p, f.qmax + f.p))
            for fmt in ('binary32', 'binary64'):
                f = interp.parse_format(fmt)
                if name == 'bv_conv_2':
                    self.assertEqual(count_limit(fd, f), count_limit(fd, f, FIRST_COUNT_WHEN), fmt)
        self.assertGreater(tried, 5000)
        self.assertGreater(ieee_shaped, 1000)
        want = {(p, emax) for p, emax in count_formats() if p >= 8 and emax <= 2 * p - 7}
        self.assertGreaterEqual(len(want), 10)
        self.assertEqual(overflowed, want)

    def test_the_count_overflowed(self):
        """The counterexample to V4 of bv_conv_2 with FIRST_COUNT_WHEN, a regression case: precision 8,
        emax 9 (the largest number 510), both operands 511 entries (+0, +0) with radii +0, which met every
        condition as first stated, and the product is the whole space (the count rounded up is +infinity).
        The condition as restated is not met there; at the largest n it admits in that format, 7, the
        product of those operands is finite, and so are the products of operands at the limits of the
        other conditions."""
        ks = common.kernels()
        m = interp.Machine(ks)
        fd = ks.folds['bv_conv_2']
        f = writers.ieee_format(8, 9)
        self.assertEqual(exact(interp.largest(f, False)), 510)
        zeros = [[ZERO, ZERO]] * 511
        self.assertLessEqual(consts.evaluate(expr.parse(FIRST_COUNT_WHEN), ks, f.p, f.qmin,
                                             {rules.COUNT_NAME: F(511)}), F(1, 16))
        self.assertEqual(interp.count_up(f, 511), PINF)
        zs, r, flag = run(m, fd, f, [ZERO, ZERO], zeros, zeros)
        self.assertEqual((len(zs), r, flag), (1021, PINF, False))
        self.assertFalse(conditions(fd, f, [ZERO, ZERO], zeros, zeros))
        self.assertEqual(judge(m, ks, fd, f, [ZERO, ZERO], zeros, zeros, (zs, r, flag)), [])
        top = count_limit(fd, f)
        self.assertEqual(top, 7)
        zeros = [[ZERO, ZERO]] * top
        self.assertTrue(conditions(fd, f, [ZERO, ZERO], zeros, zeros))
        zs, r, flag = run(m, fd, f, [ZERO, ZERO], zeros, zeros)
        self.assertEqual((len(zs), flag), (13, True))
        self.assertTrue(finite(r))
        self.assertEqual(judge(m, ks, fd, f, [ZERO, ZERO], zeros, zeros, (zs, r, flag)), [])
        self.assertFalse(conditions(fd, f, [ZERO, ZERO], [[ZERO, ZERO]] * (top + 1), [[ZERO, ZERO]] * (top + 1)))
        # At the largest count, operands at the limits of the conditions of the pairs, the entries and the radii.
        rng = random.Random('bv_conv the count overflowed')
        e = f.qmax + f.p + fd.ensures[0]['finite_when'][0]['exp'] - top.bit_length()
        within = 0
        for _ in range(400):
            hx = e // 2 + rng.randint(-2, 2)
            xs = [near(f, rng, hx - rng.randint(1, 3), 2) for _ in range(top)]
            ys = [near(f, rng, e - hx - rng.randint(1, 3), 2) for _ in range(top + rng.randint(0, 2))]
            scalars = [radius_near(f, rng, hx - rng.randint(2, 6)), radius_near(f, rng, e - hx - rng.randint(2, 6))]
            if not conditions(fd, f, scalars, xs, ys):
                continue
            within += 1
            out = run(m, fd, f, scalars, xs, ys)
            self.assertTrue(finite(out[1]), (xs, ys, scalars))
            self.assertEqual(judge(m, ks, fd, f, scalars, xs, ys, out), [])
        self.assertGreater(within, 50)

    def test_the_count_rounded_up(self):
        f = writers.ieee_format(4, 9)
        for n in range(0, 200):
            v = interp.count_up(f, n)
            self.assertGreaterEqual(exact(v), n)
            self.assertTrue(n == 0 or exact(interp.pred(f, v)) < n, n)

    def test_the_line_protocol(self):
        m = interp.Machine(common.kernels())
        line = 'bv_conv_1 binary64 seq 3 2 0x1p-4 0x1p-3 0x1p+0 0x1p+1 0x1p+2 0x1p+0 0x1p-1'
        got = interp.complete(m, line, {})
        self.assertTrue(got.startswith(line + ' -> 0x1p+0 0x1.4p+1 0x1.4p+2 0x1p+1 0x1.'), got)
        self.assertTrue(got.endswith(' 1'), got)
        # An empty operand: no coefficient, a radius from the radii alone.
        got = interp.complete(m, 'bv_conv_2 binary64 seq 0 1 0x1p-4 0x1p-3 0x1p+0 0x0p+0', {})
        self.assertEqual(got.split(' -> ')[1], '0x0p+0 1')
        # The whole space.
        got = interp.complete(m, 'bv_conv_1 binary64 seq 1 1 inf 0x0p+0 0x0p+0 0x1p+0', {})
        self.assertEqual(got.split(' -> ')[1], '0x0p+0 inf 0')
        for bad in ('bv_conv_1 binary64 lanes:2 1 1 0x0p+0 0x0p+0 0x1p+0 0x1p+0',
                    'bv_conv_1 binary64 seq 1 1 0x0p+0 0x1p+0 0x1p+0'):
            with self.assertRaises(interp.InterpError, msg=bad):
                interp.complete(m, bad, {})

    def test_an_empty_operand_with_a_large_radius(self):
        """The case that makes the conditions of each array alone necessary: x empty, so n = 0 and there is
        no coefficient, and yet mb rx overflows inside conv_radius (0 times infinity is a NaN): the whole
        space, and the condition (abs(y)+ry)*rx of finite_when is not met."""
        ks = common.kernels()
        m = interp.Machine(ks)
        f = interp.parse_format('binary64')
        fd = ks.folds['bv_conv_1']
        big = interp.canon(False, 1, 600)
        scalars, xs, ys = [big, ZERO], [], [[big]]
        zs, r, flag = run(m, fd, f, scalars, xs, ys)
        self.assertEqual((zs, r, flag), ([], PINF, False))
        self.assertFalse(conditions(fd, f, scalars, xs, ys))
        self.assertEqual(judge(m, ks, fd, f, scalars, xs, ys, (zs, r, flag)), [])


# ---------------------------------------------------------------------------------------------
# The compiled C++.

def request(fd, fmt, scalars, xs, ys):
    limbs = list(scalars) + [v for a in arrays_of(fd, xs, ys) for v in a]
    return f'{fd.name} {fmt} seq {len(xs)} {len(ys)}' + ''.join(' ' + interp.format_limb(v) for v in limbs)


def corpus(fmt, seed):
    """[(name, format, scalars, xs, ys, line)]: every pair of lengths up to 5, random ones up to a few
    hundred, the whole space among the operands, and cases near the limits of V4."""
    ks = common.kernels()
    f = interp.parse_format(fmt)
    rng = random.Random(f'{seed}:{fmt}')
    out = []
    for name in PRODUCTS:
        fd = ks.folds[name]
        pairs = [(a, b) for a in range(6) for b in range(6)] + \
            [(rng.randrange(6, 60), rng.randrange(1, 60)) for _ in range(6)] + \
            [(rng.randrange(60, common.size(300, 2000)), rng.randrange(1, 40)) for _ in range(2)]
        for nx, ny in pairs:
            for _ in range(2):
                scalars, xs, ys = case(fd, f, rng, nx, ny)
                out.append((name, fmt, scalars, xs, ys, request(fd, fmt, scalars, xs, ys)))
        top = f.qmax + f.p
        for r in range(40):
            nx, ny = rng.randint(0, 5), rng.randint(0, 5)
            k = limbs_of(fd)
            xs = [near(f, rng, top // 2 - rng.randint(0, 3), k) for _ in range(nx)]
            ys = [near(f, rng, top // 2 - rng.randint(0, 3), k) for _ in range(ny)]
            scalars = [radius_near(f, rng, top // 2 - rng.randint(0, 4)), radius_near(f, rng, top // 2 - rng.randint(0, 4))]
            out.append((name, fmt, scalars, xs, ys, request(fd, fmt, scalars, xs, ys)))
    return out


_machines = {}


def _run(job):
    name, fmt, scalars, xs, ys = job
    if 'm' not in _machines:
        _machines['m'] = interp.Machine(common.kernels())
    fd = _machines['m'].kernels.folds[name]
    out = _machines['m'].run_fold(name, interp.parse_format(fmt), 'sequential', 0, arrays_of(fd, xs, ys), scalars)
    return [common.to_float(v) for a in out[:-2] for v in a] + [common.to_float(out[-2]), out[-1]]


class Cxx(unittest.TestCase):
    """F_seq of every build of the runner, bit for bit against the interpreter."""

    @classmethod
    def setUpClass(cls):
        if not cxx.COMPILERS:
            raise unittest.SkipTest('no C++ compiler (set KAIRN_GEN_CXX)')
        cls.builds = cxx.shared_builds()
        cls.cases = corpus('binary64', 'cxx') + corpus('binary32', 'cxx')
        with ProcessPoolExecutor(max_workers=common.JOBS) as ex:
            cls.want = list(ex.map(_run, [c[:5] for c in cls.cases], chunksize=4))
        cls.text = ''.join(c[5] + '\n' for c in cls.cases)

    def test_every_build(self):
        reference = None
        for i, (label, _) in enumerate(self.builds.configs):
            with self.subTest(build=label):
                status, err = self.builds.results[i]
                self.assertEqual(status, 0, err)
                code, out, err = self.builds.run(i, self.text)
                self.assertEqual(code, 0, err)
                if out == reference:
                    continue
                bad = cxx.differences([(c[0], c[1], None, c[5]) for c in self.cases], self.want, out)
                self.assertEqual([b[0][:200] for b in bad[:3]], [], f'{len(bad)} of {len(self.cases)} differ')
                reference = out

    def test_the_corpus(self):
        self.assertTrue(any(w[-1] is False for w in self.want) and any(w[-1] is True for w in self.want))
        self.assertTrue(any(len(c[3]) == 0 for c in self.cases) and any(len(c[4]) == 0 for c in self.cases))

    def test_runner_protocol(self):
        line = 'bv_conv_1 binary64 seq 3 2 0x1p-4 0x1p-3 0x1p+0 0x1p+1 0x1p+2 0x1p+0 0x1p-1'
        code, out, err = self.builds.run(0, line + '\n')
        self.assertEqual(code, 0, err)
        self.assertEqual(out, interp.complete(interp.Machine(common.kernels()), line, {}) + '\n')
        for bad, words in (('bv_conv_1 binary64 seq 1 1 0x1p+0 0x1p+0 0x1p+0', 'takes 4 limbs'),
                           ('bv_conv_2 binary64 lanes:2 0 0 0x0p+0 0x0p+0', 'the sequential order only')):
            code, out, err = self.builds.run(0, '# fine\n' + bad + '\n')
            self.assertEqual(code, 2, bad)
            self.assertIn(words, err)


# ---------------------------------------------------------------------------------------------
# The printers.

class Printers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()

    def test_the_claims(self):
        import json
        doc = json.loads(claims.claims(self.ks))
        e = {x['name']: x for x in doc['folds']}['bv_conv_2']
        self.assertEqual(list(e), ['name', 'bv_conv', 'domain', 'arrays', 'scalars', 'writes', 'outputs', 'value',
                                   'requires', 'ensures', 'orders', 'centers', 'records', 'count', 'bound', 'radius',
                                   'radius_args', 'finish', 'min_precision', 'status', 'theorem', 'source'])
        self.assertNotIn('bv', e)
        self.assertEqual(e['ensures'], [{
            'kind': 'encloses_coefficients', 'center': 'z', 'radius': 'r', 'flag': 'flag', 'set': 'x*y',
            'balls': {'x': {'center': 'x', 'radius': 'rx'}, 'y': {'center': 'y', 'radius': 'ry'}},
            'finite_when': [{'abs_le': 'n*(abs(x)+rx)*(abs(y)+ry)', 'exp': -2}, {'abs_le': '(abs(x)+rx)*ry', 'exp': -2},
                            {'abs_le': '(abs(y)+ry)*rx', 'exp': -2}],
            'radii_when': [{'abs_le': 'rx*ry', 'exp': -2}],
            'count_when': [{'le': 'n*(unit(mul_2_2)+eta/(2*u))', 'than': '1/16'}]}])
        kernels = {k['name']: k for k in doc['kernels']}
        self.assertIn('at_most(g, 1)', kernels['conv_radius']['requires'])
        self.assertEqual(kernels['bv_conv_finish']['ensures'], [
            {'kind': 'finite_or_nan', 'of': 'r', 'flag': 'flag', 'if_all': ['okc', 'okg']}])
        with open(f'{common.ROOT}/docs/developer/architecture.md', encoding='utf-8') as fh:
            text = fh.read()
        self.assertIn('"count_when": [{"le": "n*(unit(mul_2_2)+eta/(2*u))", "than": "1/16"}]', text)

    def test_the_cxx_and_the_counts(self):
        import json
        text = cpp.scalar(self.ks)
        self.assertIn('inline void bv_conv_2_seq(const double* x0_in, const double* x1_in, std::size_t n_x, '
                      'const double* y0_in, const double* y1_in, std::size_t n_y, double rx, double ry, '
                      'double* z0_out, double* z1_out, double& r_out, bool& flag_out) noexcept {', text)
        self.assertIn('KAIRN_GEN_NOINLINE void bv_conv_2_end(double ma, double mb, std::size_t nm_, bool finite, '
                      'double rx, double ry, double& rad_out_, bool& fin_out_) noexcept {', text)
        self.assertIn('    bv_conv_2_end(ma, mb, n_x < n_y ? n_x : n_y, finite, rx, ry, rad_r_, rad_f_);\n', text)
        from kairn_gen import simd
        self.assertNotIn('bv_conv_2_packed', simd.header(simd.AVX2, self.ks))
        doc = json.loads(objcode.objcode(self.ks))
        names = doc['fold_parts']
        for name in PRODUCTS:
            self.assertEqual(list(doc['folds'][name]), ['seq'])
            for t in objcode.LIMB_TYPES:
                parts = {p[0]: dict(zip(names, p)) for p in doc['folds'][name]['seq'][t]}
                self.assertEqual({k: v['least'] for k, v in parts.items()},
                                 {'record': 2, 'step': 1, 'check': 1, 'bound': 1, 'radius': 1, 'finish': 1})
                self.assertEqual(parts['radius']['fma'], 8)

    def test_the_finish_statement_has_the_masks(self):
        """The IEEE-model statement of bv_conv_finish says what its claim finite_or_nan ... if_all=okc,okg
        means: the flag is true exactly when both masks are true and the radius is finite, as the
        statement of norm_finish_1 prints its if=ok. (Printed without the masks, the first clause was
        false: a finite radius under a false mask gives the flag false.)"""
        from kairn_gen import ieee
        text = ieee.statements(self.ks)
        s = text.split('Definition bv_conv_finish_spec : Prop :=\n', 1)[1].split('\n\n', 1)[0]
        self.assertIn('  forall okc okg : bool,\n', s)
        self.assertIn('  (flag = true <-> okc = true /\\ okg = true /\\ finite rz) /\\\n'
                      '  (flag = true -> r = rz) /\\\n'
                      '  (flag = false -> nan r).', s)
        self.assertNotIn('(flag = true <-> finite rz)', s)
        n = text.split('Definition norm_finish_1_spec : Prop :=\n', 1)[1].split('\n\n', 1)[0]
        self.assertIn('  (flag = true <-> ok = true /\\ finite m) /\\\n', n)
        # A list of three masks prints the three, in their order.
        k = self.ks['bv_conv_finish']
        e = dict(k.ensures[0], if_all=['okc', 'okg', 'okc'])
        lines = '\n'.join(ieee._finite_or_nan_spec(k, self.ks, e))
        self.assertIn('(flag = true <-> okc = true /\\ okg = true /\\ okc = true /\\ finite rz)', lines)

    def test_the_models_and_statements(self):
        from kairn_gen import ieee
        m, s = rocq.fold_model(self.ks), rocq.fold_statements(self.ks)
        im, ist = ieee.fold_model(self.ks), ieee.fold_statements(self.ks)
        for name in PRODUCTS:
            for d in ('record', 'count', 'bound', 'ok', 'radius'):
                self.assertIn(f'Definition {name}_{d} ', m)
            self.assertIn(f'Definition {name}_spec : Prop :=', s)
            for d in ('record', 'count', 'conv'):
                self.assertIn(f'Definition {name}_{d} ', im)
            self.assertIn(f'Definition {name}_ieee_spec : Prop :=', ist)
        self.assertIn('  round radix2 (FLT_exp emin prec) Zceil (INR (Nat.min (length xs) (length ys))).', m)
        self.assertIn('   Forall2 (fun j s => Rabs (sumR (map (fun xy => fst xy * snd xy) (conv_terms xs_ ys_ j)) - '
                      '(fst s + snd s)) <= r_)', s)
        self.assertIn('BinarySingleNaN.mode_UP (Z.of_nat (Nat.min (length xs) (length ys))) 0 false.', im)
        self.assertIn('  length ws_ = FoldModel.conv_length (length xs) (length ys) /\\', ist)


if __name__ == '__main__':
    unittest.main()
