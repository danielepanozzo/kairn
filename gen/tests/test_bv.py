"""The ball vectors (docs/developer/design/milestone2.md, "BallVector"; docs/developer/architecture.md,
"Ball vectors"): bv_add_k, bv_sub_k, bv_scale_k.

- Their rules: the ball vectors of gen/kernels are accepted, and each way of getting one wrong is
  refused (rules.bv_rules).
- The interpreter, on formats of the shape of IEEE 754 of a few bits, where overflow is near, and in
  binary64 and binary32, on canonical BallVectors (finite ones and the whole space) and any value of
  a scalar that is not a radius, in the sequential order and with 0 to 4 lanes: V1 to V4 of the page
  and the flag, as the claim encloses_entries and the IEEE-model statements say them (containment in
  exact arithmetic), every order the same result; and, on finite operands, the one radius equals the
  largest of the radii that the entrywise Ball kernel returns (the page's "equal", tested, not
  claimed).
- The compiled C++: F_seq and F_lanes of every build of the runner, and F_packed of every packed
  build, bit for bit against the interpreter, on the lengths of the folds, the whole space among the
  operands.
- The line protocol, the model and the statements in Rocq, the claims, the C++ text and the counts.
"""
import math
import random
import unittest
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F

import common
import test_cxx as cxx
import test_folds as folds_tests
import test_ieee_writers as writers
import test_simd as simd_tests
import test_statements as st
from kairn_gen import claims, cpp, expr, interp, ir, objcode, rocq, rules

BVS = ('bv_add_1', 'bv_add_2', 'bv_sub_1', 'bv_sub_2', 'bv_scale_1', 'bv_scale_2', 'bv_neg_1', 'bv_neg_2')
# The Ball kernel each one applies entry by entry, whose radius the one radius is the largest of.
BALL = {'bv_add_1': 'ball_add_1', 'bv_add_2': 'ball_add_2', 'bv_sub_1': 'ball_sub_1', 'bv_sub_2': 'ball_sub_2',
        'bv_scale_1': 'ball_scale_1', 'bv_scale_2': 'ball_scale_2', 'bv_neg_1': 'ball_neg_1', 'bv_neg_2': 'ball_neg_2'}
ZERO = (interp.NUM, False, 0, 0)
PINF = (interp.INF, False)
exact, finite = writers.exact, writers.finite


class FiniteDraw(writers.Draw):
    """Finite numbers only: the centers and the radii of a finite BallVector."""

    def one(self):
        if self.rng.random() < 0.15 and self.big:
            return self.rng.choice(self.big)
        return self.rng.choice(self.nums)


def vectors(fd):
    """{array: its radius scalar} of a ball vector's ball_vector requirements."""
    return {r[1]: r[2] for r in fd.requires if r[0] == 'ball_vector'}


def bv_case(fd, f, rng, n, whole=0.12):
    """(scalars' limbs, elements) of one case: each operand a canonical BallVector, the whole space
    with probability `whole`; a scalar that is not a radius any value of the format."""
    fin, anyv = FiniteDraw(f, rng), writers.Draw(f, rng, special=0.1)
    radius_of = vectors(fd)
    whole_of = {a: rng.random() < whole for a in radius_of}
    els = []
    for _ in range(n):
        e = []
        for g in fd.arrays:
            e += [ZERO] * len(g.limbs) if whole_of[g.name] else fin.group(len(g.limbs))
        els.append(e)
    scalars = []
    for g in fd.scalars:
        owner = [a for a, r in radius_of.items() if r == g.name]
        if owner:
            if whole_of[owner[0]]:
                scalars.append(PINF)
            else:
                x = fin.one()
                scalars.append((interp.NUM, False, x[2], x[3]))     # its magnitude: a radius is nonnegative
        else:
            scalars.append(anyv.one())
    return scalars, els


def radii_within(fd, f, given):
    """Whether the scalars satisfy radii_when, the radii's own condition of V4."""
    top = F(2) ** (f.qmax + f.p)
    env = {s: exact(v) for s, v in given.items()}
    return all(abs(expr.evaluate(expr.parse(c['abs_le']), env)) <= top * F(2) ** c['exp']
               for c in fd.ensures[0].get('radii_when', []))


def judge_bv(m, ks, fd, f, scalars, elements, out):
    """The failures of V1 to V4 and of the flag on one case (`out` from Machine.run_fold)."""
    written, r, flag = out[:-2], out[-2], out[-1]
    wide = writers.widened(f)
    n = len(elements)
    bad = []
    if any(len(a) != n for a in written):
        return ['length']
    given = dict(zip((g.name for g in fd.scalars), scalars))
    radius_of = vectors(fd)
    groups = []
    for e in elements:
        gs, at = {}, 0
        for g in fd.arrays:
            gs[g.name] = e[at:at + len(g.limbs)]
            at += len(g.limbs)
        groups.append(gs)
    zs = [[a[i] for a in written] for i in range(n)]
    # V1: canonical; the flag.
    if finite(r):
        if exact(r) < 0:
            bad.append('V1: a negative radius')
        for z in zs:
            if not all(finite(v) for v in z) or (len(z) == 2 and not interp.eq(interp.add(f, z[0], z[1]), z[0])):
                bad.append('V1: a center not finite and normalized')
                break
    elif r != PINF or not all(v[0] == interp.NUM and v[2] == 0 for z in zs for v in z):
        bad.append(('V1: not the whole space', interp.format_limb(r)))
    if flag != finite(r):
        bad.append('the flag')
    if bad:
        return bad
    operands_finite = all(finite(given[s]) for s in given)
    # V2: containment, entry by entry, in exact arithmetic.
    entry = fd.ensures[0]
    tree = expr.parse(entry['set'])
    if finite(r):
        for i, (gs, z) in enumerate(zip(groups, zs)):
            env = {}
            for b, v in entry['balls'].items():
                c, rad = sum(exact(x) for x in gs[v['center']]), exact(given[v['radius']])
                env[b] = (c - rad, c + rad)
            env.update({s: (exact(v), exact(v)) for s, v in given.items() if s not in radius_of.values()})
            lo, hi = st.interval(tree, env)
            c, rad = sum(exact(x) for x in z), exact(r)
            if not (c - rad <= lo and hi <= c + rad):
                bad.append(('V2', i))
            # exact (bv_neg_k): every real within the radius of the center is a value of the set: the
            # set, an interval, is the ball.
            if 'exact_when' in entry and not entry['exact_when'] and (c - rad, c + rad) != (lo, hi):
                bad.append(('exact', i))
        # V3: every operand finite, the centers the step's, the radius the radius kernel's on the largest
        # magnitude of a leading limb written.
        if not operands_finite:
            bad.append('V3: a finite result from an operand that is not finite')
        else:
            step = ks[fd.step[0]]
            for gs, z in zip(groups, zs):
                args = [v for a in fd.step[1] for v in (gs[a] if a in gs else [given[a]])]
                if [exact(v) for v in m.run(step.name, wide, args)] != [exact(v) for v in z]:
                    bad.append('V3: a center not the step\'s')
                    break
            big = max([abs(exact(z[0])) for z in zs], default=F(0))
            mz = max([z[0] for z in zs], key=lambda v: abs(exact(v)), default=ZERO)
            mz = (interp.NUM, False, mz[2], mz[3])
            assert exact(mz) == big
            want = m.run(fd.radius[0], wide, [mz] + [given[a] for a in fd.radius[1][1:]])
            if exact(want[0]) != exact(r):
                bad.append('V3: the radius is not the radius kernel\'s on the largest center')
    elif operands_finite:
        # V4, of every length: finite operands, the radii within their condition (radii_when), and
        # every entry within the stated fraction of the overflow threshold give a finite result.
        top = F(2) ** (f.qmax + f.p)
        ok = radii_within(fd, f, given)
        for gs in groups:
            env = {a: sum(exact(x) for x in gs[a]) for a in gs}
            env.update({s: exact(v) for s, v in given.items()})
            for c in entry['finite_when']:
                if abs(expr.evaluate(expr.parse(c['abs_le']), env)) > top * F(2) ** c['exp']:
                    ok = False
        if ok:
            bad.append('V4: not finite')
    return bad


MAKES = ('bv_make_1', 'bv_make_2')


def make_case(fd, f, rng, n, special=0.06):
    """(scalars, elements) of one case of a constructor: the radius any value of the format (negative
    ones, zeros of either sign, infinities and NaN among them), each center any value (one limb) or a
    canonical pair (two limbs), specials with probability `special` each."""
    draw = writers.Draw(f, rng, special=special)
    elements = [draw.group(len(fd.arrays[0].limbs)) for _ in range(n)]
    x = rng.random()
    r = (rng.choice([PINF, (interp.INF, True), interp.NaN, (interp.NUM, True, 0, 0), ZERO]) if x < 0.15 else
         draw.one())
    return [r], elements


def judge_make(fd, f, scalars, elements, out):
    """The failures of makes_ball_vector on one case (milestone2.md, "BallVector", "Values"): the result
    is canonical; the flag is true exactly when the radius is finite; it is the whole space exactly when
    the radius given is negative, a NaN or +infinity, or a center given is not finite; otherwise the
    centers and the radius are those given, as values (the sign of a zero is not part of the claim)."""
    written, r, flag = out[:-2], out[-2], out[-1]
    n = len(elements)
    if any(len(a) != n for a in written):
        return ['length']
    zs = [[a[i] for a in written] for i in range(n)]
    bad = []
    if finite(r):
        if exact(r) < 0:
            bad.append('B1: a negative radius')
        for z in zs:
            if not all(finite(v) for v in z) or (len(z) == 2 and not interp.eq(interp.add(f, z[0], z[1]), z[0])):
                bad.append('B1: a center not finite and normalized')
                break
    elif r != PINF or not all(v[0] == interp.NUM and v[2] == 0 for z in zs for v in z):
        bad.append('B1: not the whole space')
    if flag != finite(r):
        bad.append('the flag')
    given = scalars[0]
    whole = not finite(given) or exact(given) < 0 or any(not finite(e[0]) for e in elements)
    if flag == whole:
        bad.append(('B2: the whole space', whole))
    if flag:
        if exact(r) != exact(given):
            bad.append('B3: not the radius given')
        if any([exact(v) for v in z] != [exact(v) for v in e] for z, e in zip(zs, elements)):
            bad.append('B3: not the centers given')
    return bad


def _judge_make(job):
    name, p, emax, rounds = job
    ks = common.kernels()
    fd = ks.folds[name]
    m = interp.Machine(ks)
    f = writers.ieee_format(p, emax) if p else interp.parse_format(emax)
    rng = random.Random(f'make:{name}:{f.name}')
    bad, count, whole = [], 0, 0
    for r in range(rounds):
        n = r % 6
        scalars, elements = make_case(fd, f, rng, n)
        arrays = [[e[j] for e in elements] for j in range(len(fd.array_limbs()))]
        outs = [m.run_fold(name, f, order, w, arrays, scalars)
                for order, w in [('sequential', 0)] + [('lanes', x) for x in (0, 1, 2, 3, 4)]]
        if any(o != outs[0] for o in outs):
            bad.append((name, f.name, n, 'not the sequential order\'s'))
        bad += [(name, f.name, n, x) for x in judge_make(fd, f, scalars, elements, outs[0])]
        count += 1
        whole += not outs[0][-1]
    return name, f.name, count, whole, bad[:5]


def empty_cases(fd, f):
    """[(scalars, within)] of the vector with no entry, the radii (and the other scalars) on each side of
    the limit of radii_when, which is then the whole of V4: a radius of 2^(L-1) and its neighbors, 2^L
    and the next number, the largest number and zero, with L the exponent of the limit, and each other
    scalar 1, 2, -2, the number after 2 or 4."""
    c = fd.ensures[0]['radii_when'][0]
    L = f.qmax + f.p + c['exp']
    big = [interp.canon(False, 1, L - 1), interp.canon(False, 1, L)]
    radii = [ZERO, interp.largest(f, False)]
    for v in big:
        if v[2].bit_length() + v[3] <= f.qmax + f.p:          # a number of the format
            radii += [v, interp.pred(f, v), interp.succ(f, v)]
    radii = [v for v in radii if finite(v)]
    two = interp.canon(False, 1, 1)
    others = [interp.canon(False, 1, 0), two, interp.neg(two), interp.succ(f, two), interp.canon(False, 1, 2)]
    radius_names = set(vectors(fd).values())
    choices = [radii if g.name in radius_names else others for g in fd.scalars]
    import itertools
    out = []
    for scalars in itertools.product(*choices):
        out.append((list(scalars), radii_within(fd, f, dict(zip((g.name for g in fd.scalars), scalars)))))
    return out


def _judge(job):
    name, p, emax, rounds = job
    ks = common.kernels()
    fd = ks.folds[name]
    m = interp.Machine(ks)
    f = writers.ieee_format(p, emax) if p else interp.parse_format(emax)
    rng = random.Random(f'bv:{name}:{f.name}')
    bad, count, whole, equal, compared = [], 0, 0, 0, 0
    ball = ks[BALL[name]]
    for r in range(rounds):
        n = r % 7
        scalars, elements = bv_case(fd, f, rng, n)
        arrays = [[e[j] for e in elements] for j in range(len(fd.array_limbs()))]
        first = None
        for order, w in [('sequential', 0)] + [('lanes', x) for x in (0, 1, 2, 3, 4)]:
            out = m.run_fold(name, f, order, w, arrays, scalars)
            if first is None:
                first = out
                for x in judge_bv(m, ks, fd, f, scalars, elements, out):
                    bad.append((name, f.name, n, x))
                count += 1
                whole += not out[-1]
            elif out != first:
                bad.append((name, f.name, order, w, n, 'not the sequential order\'s'))
        # The page's equality: the one radius is the largest of the entrywise radii.
        if first[-1] and n:
            given = dict(zip((g.name for g in fd.scalars), scalars))
            radii = []
            for e in elements:
                gs, at = {}, 0
                for g in fd.arrays:
                    gs[g.name] = e[at:at + len(g.limbs)]
                    at += len(g.limbs)
                args = []
                for g in ball.inputs:
                    if g.name in ('cx', 'cy'):
                        args += gs[fd.arrays[0 if g.name == 'cx' else 1].name]
                    elif g.name == 'rx':
                        args.append(given[vectors(fd)[fd.arrays[0].name]])
                    elif g.name == 'ry':
                        args.append(given[vectors(fd)[fd.arrays[1].name]])
                    else:
                        args.append(given[g.name])
                radii.append(exact(m.run(ball.name, f, args)[-1]))
            compared += 1
            equal += max(radii) == exact(first[-2])
    return name, f.name, count, whole, bad[:5], equal, compared


class Rules(unittest.TestCase):
    BASE = '''
fold:          tb
arrays:        stored x = x0 x1, stored y = y0 y1
scalars:       stored rx, stored ry
state:         m, mask ok
step:          z = add_2_2(x, y)
record:        (m, ok) = norm_step_2(m, ok, z)
combine:       (m, ok) = norm_combine(m, ok, m, ok)
radius:        rz = bv_add_radius_2(m, rx, ry)
finish:        (r, finite) = norm_finish_1(rz, ok)
orders:        sequential, lanes
writes:        z = z0 z1
output:        r
output:        mask finite
value:         x+y
requires:      ball_vector x rx
requires:      ball_vector y ry
ensures:       encloses_entries z r x+y x=x,rx y=y,ry flag=finite finite_when=abs_le(abs(x+y)+rx+ry,-2) radii_when=abs_le(rx+ry,-2)
min_precision: 3
status:        unverified
domain:        extended
'''

    def refusals(self, text):
        ks = common.kernels()
        fd = ir.parse_fold(text, 'tb.fold')
        return [str(e) for e in rules.fold_rules(fd, ir.ordered(dict(ks), dict(ks.folds, tb=fd)))]

    MAKE = '''
fold:          tm
arrays:        supplied c
scalars:       supplied r
state:         m, mask ok
step:          z = bv_center_entry_1(c)
record:        (m, ok) = norm_step_1(m, ok, z)
combine:       (m, ok) = norm_combine(m, ok, m, ok)
radius:        rz = bv_make_radius(m, r)
finish:        (rr, finite) = bv_make_finish(rz, ok)
orders:        sequential, lanes
writes:        z
output:        rr
output:        mask finite
value:         c
ensures:       makes_ball_vector z rr from=c,r flag=finite
min_precision: 1
status:        unverified
domain:        extended
'''

    def test_the_constructor_is_refused(self):
        self.assertEqual(self.refusals(self.MAKE.replace('fold:          tm', 'fold:          tb')), [])
        for old, new, words in (
                ('finish:        (rr, finite) = bv_make_finish(rz, ok)',
                 'finish:        (rr, finite) = norm_finish_1(rz, ok)', 'with nonneg'),
                ('scalars:       supplied r', 'scalars:       stored r', 'the radius the program supplies'),
                ('value:         c', 'value:         -c', 'the center given'),
                ('ensures:       makes_ball_vector z rr from=c,r flag=finite',
                 'ensures:       makes_ball_vector z rr from=c,r flag=ok', 'and nothing else'),
                ('step:          z = bv_center_entry_1(c)', 'step:          z = fold_finish_1(c)', 'step'),
                ('domain:        extended\n', '', 'extended domain')):
            text = self.MAKE.replace('fold:          tm', 'fold:          tb').replace(old, new)
            self.assertNotEqual(text, self.MAKE.replace('fold:          tm', 'fold:          tb'), old)
            errs = self.refusals(text)
            self.assertTrue(any(words in e for e in errs), (old, words, errs))
        # The finish of a constructor is no other ball vector's.
        errs = self.refusals(self.BASE.replace('norm_finish_1(rz, ok)', 'bv_make_finish(rz, ok)'))
        self.assertTrue(any('with nonneg' in e for e in errs), errs)

    def test_the_ball_vectors_are_accepted(self):
        ks = common.kernels()
        for name in BVS + MAKES:
            self.assertTrue(ks.folds[name].is_bv and not ks.folds[name].is_map, name)
            self.assertEqual([str(e) for e in rules.fold_rules(ks.folds[name], ks)], [], name)
        self.assertEqual(self.refusals(self.BASE), [])

    def test_refused(self):
        for old, new, words in (
                ('record:        (m, ok) = norm_step_2(m, ok, z)', 'record:        (m, ok) = norm_combine(m, ok, m, ok)',
                 'is not the step of a fold of maxima'),
                ('radius:        rz = bv_add_radius_2(m, rx, ry)', 'radius:        rz = bv_add_radius_2(rx, m, ry)',
                 "its arguments are the state's limb m"),
                ('finish:        (r, finite) = norm_finish_1(rz, ok)', 'finish:        (r, finite) = fold_finish_1(rz)',
                 'finish: a kernel of the radius and a mask'),
                ('requires:      ball_vector y ry\n', '', 'every array is the centers of a BallVector'),
                ('flag=finite', 'flag=ok', 'the flag finite'),
                ('ensures:       encloses_entries z r x+y', 'ensures:       encloses_entries z r x-y',
                 'is the value of the fold'),
                ('scalars:       stored rx, stored ry', 'scalars:       stored rx, supplied ry',
                 'requires \'ball_vector y ry\''),
                ('combine:       (m, ok) = norm_combine(m, ok, m, ok)', 'combine:       (m, ok) = norm_combine(ok, m, m, ok)',
                 'the combination of norm_upper_2'),
                ('state:         m, mask ok', 'state:         mask ok', 'the state of a ball vector'),
                (' radii_when=abs_le(rx+ry,-2)', '', 'finite_when and radii_when come together'),
                ('radii_when=abs_le(rx+ry,-2)', 'radii_when=abs_le(x+rx+ry,-2)', "the scalars' names only")):
            text = self.BASE.replace(old, new)
            self.assertNotEqual(text, self.BASE, old)
            errs = self.refusals(text)
            self.assertTrue(any(words in e for e in errs), (old, words, errs))


class Interp(unittest.TestCase):
    def test_v1_to_v4(self):
        jobs = []
        ks = common.kernels()
        for name in BVS:
            fd = ks.folds[name]
            jobs += [(name, p, emax, common.size(150, 1500)) for p, emax in writers.toy_formats(fd.min_precision)]
            jobs += [(name, None, fmt, common.size(80, 600)) for fmt in ('binary64', 'binary32')]
        with ProcessPoolExecutor(max_workers=common.JOBS) as ex:
            results = list(ex.map(_judge, jobs))
        self.assertEqual([r[4] for r in results if r[4]], [])
        for name in BVS:
            mine = [r for r in results if r[0] == name]
            self.assertGreater(sum(r[2] for r in mine), 500, name)
            self.assertGreater(sum(r[3] for r in mine), 50, name)          # the whole space, often
            # The radius is the largest entrywise radius of the Ball kernel in every case compared.
            self.assertEqual(sum(r[5] for r in mine), sum(r[6] for r in mine), name)
            self.assertGreater(sum(r[6] for r in mine), 200, name)

    def test_the_norm_of_a_ball_vector(self):
        """bv_norm_upper_k is two calls (architecture.md, "Ball vectors"): (n, ok) = norm_upper_k(c) and
        b = add_up_1(n, r) when ok, +infinity otherwise. On canonical BallVectors (the whole space among
        them, leading limbs at the largest number), in toy formats of the IEEE shape and in binary64 and
        binary32, in exact arithmetic: every member is at most b in magnitude, and b is at most the
        rounding up of RU(V) stepped up S times plus r (V the largest magnitude of a center)."""
        ks = common.kernels()
        m = interp.Machine(ks)
        for k in (1, 2):
            fd = ks.folds[f'bv_neg_{k}']             # its operand: one BallVector of k limbs
            formats = [writers.ieee_format(p, emax) for p, emax in writers.toy_formats(1)] + \
                [interp.parse_format('binary64'), interp.parse_format('binary32')]
            infinite = clamped = 0
            for f in formats:
                rng = random.Random(f'norm:{k}:{f.name}')
                for i in range(common.size(300, 2000)):
                    scalars, elements = bv_case(fd, f, rng, i % 6)
                    if k == 2 and elements and rng.random() < 0.1:
                        elements[0] = [interp.largest(f, rng.random() < 0.5), ZERO]
                    r = scalars[0]
                    out = m.run_fold(f'norm_upper_{k}', f, 'sequential', 0,
                                     [[e[j] for e in elements] for j in range(k)])
                    n, ok = out[0], out[-1]
                    b = m.run('add_up_1', f, [n, r])[0] if ok else PINF
                    if not finite(b):
                        self.assertEqual(b, PINF, (k, f.name, elements, r))
                        infinite += 1
                        clamped += ok and finite(r)
                        continue
                    big = max([abs(sum(exact(v) for v in e)) for e in elements], default=F(0))
                    self.assertLessEqual(big + exact(r), exact(b), (k, f.name, elements, r))
                    # At most the rounding up of RU(V) stepped up S times plus r (V, the largest
                    # leading magnitude, is a number of the format, its own RU).
                    w = max([e[0] for e in elements], key=lambda x: abs(exact(x)), default=ZERO)
                    w = (interp.NUM, False, w[2], w[3])
                    for _ in range(k - 1):
                        w = interp.succ(f, w)
                    q = exact(w) + exact(r)
                    ru = interp.rnd(f, False, q.numerator, -(q.denominator.bit_length() - 1)) if q else ZERO
                    if finite(ru) and exact(ru) < q:
                        ru = interp.succ(f, ru)
                    self.assertTrue(not finite(ru) or exact(b) <= exact(ru), (k, f.name, elements, r))
            self.assertGreater(infinite, 0, k)
            if k == 2:
                self.assertGreater(clamped, 0)       # finite centers and radius, the step up from Omega infinite

        """makes_ball_vector of bv_make_1 and bv_make_2 on the interpreter, in toy formats of the IEEE
        shape and in binary64 and binary32, every order the same: B1 to B3 of judge_make, the radius given
        and the centers given any value, with negative radii, zeros of either sign, infinities and NaN."""
        ks = common.kernels()
        jobs = []
        for name in MAKES:
            fd = ks.folds[name]
            jobs += [(name, p, emax, common.size(300, 3000)) for p, emax in writers.toy_formats(fd.min_precision)]
            jobs += [(name, None, fmt, common.size(200, 1500)) for fmt in ('binary64', 'binary32')]
        with ProcessPoolExecutor(max_workers=common.JOBS) as ex:
            results = list(ex.map(_judge_make, jobs))
        self.assertEqual([r[4] for r in results if r[4]], [])
        for name in MAKES:
            mine = [r for r in results if r[0] == name]
            self.assertGreater(sum(r[2] for r in mine), 1000, name)
            self.assertGreater(sum(r[3] for r in mine), 200, name)                      # the whole space
            self.assertGreater(sum(r[2] - r[3] for r in mine), 200, name)               # a finite ball vector

    def test_the_constructors_on_every_small_case(self):
        """Every radius and every list of up to two centers of a format of three bits (one limb: every
        value, specials included; two limbs: canonical pairs, a sample), in the sequential order and
        with 2 lanes."""
        ks = common.kernels()
        m = interp.Machine(ks)
        f = writers.ieee_format(3, 3)
        values = writers.numbers(f) + list(writers.SPECIALS)
        import itertools
        for name in MAKES:
            fd = ks.folds[name]
            rng = random.Random(f'small:{name}')
            draw = writers.Draw(f, rng, special=0.2)
            groups = ([[v] for v in values] if len(fd.arrays[0].limbs) == 1 else
                      [draw.pair() for _ in range(40)])
            count = 0
            for r in values:
                for n in range(3):
                    for cs in itertools.product(groups[::max(1, len(groups) // 12)], repeat=n):
                        arrays = [[e[j] for e in cs] for j in range(len(fd.array_limbs()))]
                        outs = [m.run_fold(name, f, o, w, arrays, [r]) for o, w in (('sequential', 0), ('lanes', 2))]
                        self.assertEqual(outs[0], outs[1], (name, r, cs))
                        self.assertEqual(judge_make(fd, f, [r], list(cs), outs[0]), [], (name, r, cs))
                        count += 1
            self.assertGreater(count, 1000, name)

    def test_v4_of_the_empty_vector(self):
        """V4 for every length: with no entry, the radius comes from the radii (and the other scalars)
        alone, and radii_when is the whole condition. On each side of its limit, in toy formats of the
        IEEE shape and in binary64 and binary32, in every order: within the limit the result is finite;
        beyond it nothing is claimed, and far beyond (the largest radius) it is the whole space."""
        ks = common.kernels()
        m = interp.Machine(ks)
        for name in BVS:
            fd = ks.folds[name]
            formats = [writers.ieee_format(p, emax) for p, emax in writers.toy_formats(fd.min_precision)] + \
                [interp.parse_format('binary64'), interp.parse_format('binary32')]
            at_limit, beyond, whole = 0, 0, 0
            for f in formats:
                top = F(2) ** (f.qmax + f.p + fd.ensures[0]['radii_when'][0]['exp'])
                for scalars, within in empty_cases(fd, f):
                    outs = [m.run_fold(name, f, order, w, [[] for _ in fd.array_limbs()], scalars)
                            for order, w in [('sequential', 0), ('lanes', 0), ('lanes', 3)]]
                    self.assertTrue(all(o == outs[0] for o in outs), (name, f.name, scalars))
                    self.assertEqual(judge_bv(m, ks, fd, f, scalars, [], outs[0]), [], (name, f.name, scalars))
                    env = {g.name: exact(v) for g, v in zip(fd.scalars, scalars)}
                    value = abs(expr.evaluate(expr.parse(fd.ensures[0]['radii_when'][0]['abs_le']), env))
                    at_limit += within and value == top and outs[0][-1]
                    beyond += not within
                    whole += not outs[0][-1]
            if fd.ensures[0]['radii_when'][0]['exp'] < 0:
                self.assertGreater(at_limit, 0, name)       # exactly at the limit, and finite
                self.assertGreater(beyond, 0, name)
                self.assertGreater(whole, 0, name)
            else:
                # bv_neg_k: every finite radius is within the limit, and the result is finite.
                self.assertEqual((beyond, whole), (0, 0), name)

    def test_radii_when_is_implied_by_finite_when(self):
        """At any entry, the conditions of finite_when imply radii_when: V4 of a vector with entries is
        the statement it was, and the new hypothesis adds nothing there. In exact arithmetic, on random
        centers and scalars of binary64 and of a toy format, the condition's values near the limit."""
        ks = common.kernels()
        for name in BVS:
            fd = ks.folds[name]
            e = fd.ensures[0]
            for f in (interp.parse_format('binary64'), writers.ieee_format(4, 5)):
                rng = random.Random(f'implied:{name}:{f.name}')
                top = F(2) ** (f.qmax + f.p)
                tested = 0
                for _ in range(3000):
                    scalars, elements = bv_case(fd, f, rng, 1, whole=0)
                    if not all(finite(v) for v in scalars):
                        continue
                    env = {g.name: exact(v) for g, v in zip(fd.scalars, scalars)}
                    at = 0
                    for g in fd.arrays:
                        env[g.name] = sum(exact(x) for x in elements[0][at:at + len(g.limbs)])
                        at += len(g.limbs)
                    if all(abs(expr.evaluate(expr.parse(c['abs_le']), env)) <= top * F(2) ** c['exp']
                           for c in e['finite_when']):
                        tested += 1
                        self.assertTrue(radii_within(fd, f, dict(zip((g.name for g in fd.scalars), scalars))),
                                        (name, f.name, scalars, elements))
                self.assertGreater(tested, 100, (name, f.name))

    def test_the_whole_space_and_the_empty_vector(self):
        ks = common.kernels()
        m = interp.Machine(ks)
        f = interp.parse_format('binary64')
        one = interp.canon(False, 1, 0)
        # An operand that is the whole space: the result is, its centers zero.
        out = m.run_fold('bv_add_1', f, 'sequential', 0, [[ZERO, ZERO], [one, one]], [PINF, one])
        self.assertEqual(out, [[ZERO, ZERO], PINF, False])
        # No entry: a radius from the radii alone, finite.
        out = m.run_fold('bv_add_2', f, 'lanes', 3, [[], [], [], []], [one, one])
        self.assertTrue(out[-1] and exact(out[-2]) >= 2)
        # An overflow in one center: the whole space.
        top = interp.canon(False, 2 ** 53 - 1, 971)
        out = m.run_fold('bv_add_1', f, 'sequential', 0, [[one, top], [one, top]], [ZERO, ZERO])
        self.assertEqual(out, [[ZERO, ZERO], PINF, False])
        # A scalar that is not finite: the whole space.
        out = m.run_fold('bv_scale_1', f, 'sequential', 0, [[one]], [one, interp.NaN])
        self.assertEqual(out, [[ZERO], PINF, False])

    def test_the_line_protocol(self):
        m = interp.Machine(common.kernels())
        formats = {}
        line = 'bv_add_1 binary64 seq 2 0x1p-4 0x1p-4 0x1p+0 0x1p+1 0x1p+0 0x1p+0 #t'
        got = interp.complete(m, line, formats)
        self.assertTrue(got.startswith(line + ' -> 0x1p+1 0x1.8p+1 0x1.'), got)
        self.assertTrue(got.endswith(' 1'), got)
        # In place (architecture.md's examples): the completion of the request without the field.
        line = 'add_2 binary64 seq 2 inplace=1 0x1p+0 0x1p+1 0x0p+0 0x0p+0 0x1p-1 0x1p-1 0x0p+0 0x0p+0'
        self.assertEqual(interp.complete(m, line, formats), line + ' -> 0x1.8p+0 0x1.4p+1 0x0p+0 0x0p+0 1')
        line = 'bv_add_1 binary64 lanes:2 2 inplace=0 0x1p-4 0x1p-4 0x1p+0 0x1p+1 0x1p+0 0x1p+0'
        self.assertEqual(interp.complete(m, line, formats).split(' -> ')[1],
                         interp.complete(m, line.replace(' inplace=0', ''), formats).split(' -> ')[1])
        for bad in ('add_2 binary64 seq 1 inplace=2 0x1p+0 0x0p+0 0x1p+0 0x0p+0',
                    'sum_2 binary64 seq 1 inplace=0 0x1p+0 0x0p+0',
                    'bv_scale_1 binary64 seq 1 inplace=1 0x1p+0 0x1p+0 0x1p+0'):
            with self.assertRaises(interp.InterpError, msg=bad):
                interp.complete(m, bad, formats)
        # The constructor: the radius, then the centers given; a negative radius gives the whole space.
        self.assertEqual(interp.complete(m, 'bv_make_1 binary64 seq 2 0x1p-4 -0x1p+0 0x1p+1', formats),
                         'bv_make_1 binary64 seq 2 0x1p-4 -0x1p+0 0x1p+1 -> -0x1p+0 0x1p+1 0x1p-4 1')
        self.assertEqual(interp.complete(m, 'bv_make_1 binary64 seq 2 -0x1p-4 -0x1p+0 0x1p+1', formats),
                         'bv_make_1 binary64 seq 2 -0x1p-4 -0x1p+0 0x1p+1 -> 0x0p+0 0x0p+0 inf 0')
        self.assertEqual(interp.complete(m, 'bv_make_2 binary32 lanes:2 1 0x1p+0 inf 0x0p+0', formats),
                         'bv_make_2 binary32 lanes:2 1 0x1p+0 inf 0x0p+0 -> 0x0p+0 0x0p+0 inf 0')
        self.assertEqual(interp.complete(m, 'bv_scale_2 binary32 lanes:4 0 0x1p+0 0x1p+0', formats),
                         'bv_scale_2 binary32 lanes:4 0 0x1p+0 0x1p+0 -> ' +
                         interp.format_limb(m.run('bv_scale_radius_2', interp.parse_format('binary32'),
                                                  [ZERO, interp.canon(False, 1, 0), interp.canon(False, 1, 0)])[0]) +
                         ' 1')


# ---------------------------------------------------------------------------------------------
# The compiled C++.

def request(fd, fmt, order, lanes, scalars, elements):
    o = 'seq' if order == 'sequential' else f'lanes:{lanes}'
    limbs = list(scalars) + [e[j] for j in range(len(fd.array_limbs())) for e in elements]
    return f'{fd.name} {fmt} {o} {len(elements)}' + ''.join(' ' + interp.format_limb(v) for v in limbs)


def corpus(fmt, orders, seed):
    """[(name, format, order, lanes, scalars, elements, line)] of every ball vector."""
    ks = common.kernels()
    f = interp.parse_format(fmt)
    rng = random.Random(f'{seed}:{fmt}')
    out = []
    for name in BVS:
        fd = ks.folds[name]
        for n in folds_tests.lengths(rng):
            for _ in range(2):
                scalars, elements = bv_case(fd, f, rng, n)
                for order, w in orders:
                    out.append((name, fmt, order, w, scalars, elements, request(fd, fmt, order, w, scalars, elements)))
        # The vector with no entry, its radii on each side of the limit of V4 (empty_cases).
        for scalars, _ in empty_cases(fd, f):
            for order, w in orders:
                out.append((name, fmt, order, w, scalars, [], request(fd, fmt, order, w, scalars, [])))
    for name in MAKES:
        fd = ks.folds[name]
        for n in folds_tests.lengths(rng):
            for special in (0.0, 0.03):
                scalars, elements = make_case(fd, f, rng, n, special)
                for order, w in orders:
                    out.append((name, fmt, order, w, scalars, elements, request(fd, fmt, order, w, scalars, elements)))
    return out


def same_completion(a, b):
    """Two completions, the same limbs as values (printf's %a and Python's float.hex may spell a
    subnormal number differently) and the same masks."""
    ta, tb = a.split(' '), b.split(' ')
    if len(ta) != len(tb):
        return False
    for x, y in zip(ta, tb):
        if x != y:
            try:
                if interp.parse_limb(x) != interp.parse_limb(y):
                    return False
            except interp.InterpError:
                return False
    return True


def in_place_corpus(orders=None, formats=('binary64', 'binary32')):
    """([in-place request], [the same request without the field]) of every map and ball vector, for
    each array read with as many limbs as the array written, on random canonical operands of lengths
    0 to 9 (the constructors' and the maps' operands any value, specials among them)."""
    ks = common.kernels()
    lines, plain = [], []
    for fmt in formats:
        f = interp.parse_format(fmt)
        rng = random.Random(f'inplace:{fmt}')
        for name, fd in ks.folds.items():
            if not (fd.is_map or fd.is_bv):
                continue
            places = [i for i, g in enumerate(fd.arrays) if len(g.limbs) == len(fd.write_limbs())]
            for n in (0, 1, 2, 3, 5, 9):
                if fd.is_map:
                    scalars, elements = writers.map_case(fd, writers.Draw(f, rng, special=0.02), n)
                elif fd.ensures[0]['kind'] == 'makes_ball_vector':
                    scalars, elements = make_case(fd, f, rng, n, 0.02)
                else:
                    scalars, elements = bv_case(fd, f, rng, n)
                for order, w in (orders.get(fmt, []) if orders else [('sequential', 0), ('lanes', 3)]):
                    p = request(fd, fmt, order, w, scalars, elements)
                    head = p.split(' ')
                    for i in places:
                        lines.append(' '.join(head[:4] + [f'inplace={i}'] + head[4:]))
                        plain.append(p)
    return lines, plain


_machines = {}


def _run(job):
    name, fmt, order, w, scalars, elements = job
    if 'm' not in _machines:
        _machines['m'] = interp.Machine(common.kernels())
    fd = _machines['m'].kernels.folds[name]
    arrays = [[e[j] for e in elements] for j in range(len(fd.array_limbs()))]
    out = _machines['m'].run_fold(name, interp.parse_format(fmt), order, w, arrays, scalars)
    return [common.to_float(v) for a in out[:-2] for v in a] + [common.to_float(out[-2]), out[-1]]


def expected(cases):
    with ProcessPoolExecutor(max_workers=common.JOBS) as ex:
        return list(ex.map(_run, [c[:6] for c in cases], chunksize=4))


class Cxx(unittest.TestCase):
    """F_seq and F_lanes of every build of the runner, bit for bit against the interpreter."""

    @classmethod
    def setUpClass(cls):
        if not cxx.COMPILERS:
            raise unittest.SkipTest('no C++ compiler (set KAIRN_GEN_CXX)')
        cls.builds = cxx.shared_builds()
        orders = [('sequential', 0)] + [('lanes', w) for w in (0, 1, 2, 3, 4, 8)]
        cls.cases = corpus('binary64', orders, 'cxx') + corpus('binary32', orders, 'cxx')
        cls.want = expected(cls.cases)
        cls.text = ''.join(c[6] + '\n' for c in cls.cases)

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
                bad = cxx.differences([(c[0], c[1], None, c[6]) for c in self.cases], self.want, out)
                self.assertEqual([b[0][:200] for b in bad[:3]], [], f'{len(bad)} of {len(self.cases)} differ')
                reference = out

    def test_in_place(self):
        """The request form inplace=I (architecture.md, "The line protocol"): every map and every ball
        vector with each array read that has the limbs of the array written, through every build of the
        runner, which then passes that array as the one written, completes exactly as the same request
        without the field; the interpreter too."""
        lines, plain = in_place_corpus()
        m = interp.Machine(common.kernels())
        formats = {}
        want = [interp.complete(m, p, formats).split(' -> ', 1)[1] for p in plain]
        self.assertEqual([interp.complete(m, x, formats).split(' -> ', 1)[1] for x in lines], want)
        text = ''.join(x + '\n' for x in lines)
        for i, (label, _) in enumerate(self.builds.configs):
            with self.subTest(build=label):
                code, out, err = self.builds.run(i, text)
                self.assertEqual(code, 0, err)
                got = [x.split(' -> ', 1)[1] for x in out.splitlines() if ' -> ' in x]
                self.assertEqual(len(got), len(want))
                bad = [(lines[j][:120], got[j][:80], want[j][:80]) for j in range(len(want))
                       if not same_completion(got[j], want[j])]
                self.assertEqual(bad[:3], [], f'{len(bad)} of {len(want)} differ')

    def test_the_corpus(self):
        self.assertTrue(any(w[-1] is False for w in self.want) and any(w[-1] is True for w in self.want))
        self.assertTrue({0, 1, 2, 3, 4, 5, 7, 8, 9, 16} <= {len(c[5]) for c in self.cases})


class Packed(unittest.TestCase):
    """F_packed of every packed build: F_lanes with the lanes of the register, and the interpreter."""

    @classmethod
    def setUpClass(cls):
        why = simd_tests.no_packed_backend()
        if why:
            raise unittest.SkipTest(why)
        cls.builds = simd_tests.shared_builds()
        cls.cases = {}
        for label, _ in cls.builds.configs:
            key = tuple(sorted(cls.native(label).items()))
            if key not in cls.cases:
                cases = []
                for fmt, w in cls.native(label).items():
                    cases += corpus(fmt, [('lanes', w)], 'packed')
                cls.cases[key] = (cases, expected(cases))

    @staticmethod
    def native(label):
        return {'binary64': 2, 'binary32': 4} if simd_tests.ARM64 and 'x86_64' not in label else \
            {'binary64': 4, 'binary32': 8}

    def test_in_place(self):
        """inplace=I through every packed build: as the same request without the field."""
        m = interp.Machine(common.kernels())
        for i, (label, _) in enumerate(self.builds.configs):
            native = self.native(label)
            lines, plain = in_place_corpus({fmt: [('lanes', w)] for fmt, w in native.items()}, tuple(native))
            formats = {}
            want = [interp.complete(m, p, formats).split(' -> ', 1)[1] for p in plain]
            with self.subTest(build=label):
                code, out, err = self.builds.run(i, 'packed', ''.join(x + '\n' for x in lines))
                self.assertEqual(code, 0, err)
                got = [x.split(' -> ', 1)[1] for x in out.splitlines() if ' -> ' in x]
                self.assertEqual(len(got), len(want))
                bad = [(lines[j][:120], got[j][:80], want[j][:80]) for j in range(len(want))
                       if not same_completion(got[j], want[j])]
                self.assertEqual(bad[:3], [], f'{len(bad)} of {len(want)} differ')

    def test_lane_by_lane(self):
        for i, (label, _) in enumerate(self.builds.configs):
            cases, want = self.cases[tuple(sorted(self.native(label).items()))]
            text = ''.join(c[6] + '\n' for c in cases)
            with self.subTest(build=label):
                for status, err in self.builds.results[i]:
                    self.assertEqual(status, 0, err)
                code, packed, err = self.builds.run(i, 'packed', text)
                self.assertEqual(code, 0, err)
                code, scalar, err = self.builds.run(i, 'scalar', text)
                self.assertEqual(code, 0, err)
                differ = [(a[:120], b[:120]) for a, b in zip(packed.splitlines(), scalar.splitlines()) if a != b]
                self.assertEqual(differ[:3], [], f'{len(differ)} lines differ from F_lanes')
                bad = cxx.differences([(c[0], c[1], None, c[6]) for c in cases], want, packed)
                self.assertEqual([b[0][:200] for b in bad[:3]], [], f'{len(bad)} of {len(cases)} differ')


# ---------------------------------------------------------------------------------------------
# The printers.

class Printers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()

    def test_the_cxx(self):
        text = cpp.scalar(self.ks)
        self.assertIn('inline void bv_add_2_seq(const double* x0_in, const double* x1_in, const double* y0_in, '
                      'const double* y1_in, std::size_t n, double rx, double ry, double* z0_out, double* z1_out, '
                      'double& r_out, bool& finite_out) noexcept {', text)
        self.assertIn('    r_out = rad_f_ ? rad_r_ : std::numeric_limits<double>::infinity();', text)
        # The end, a function of its own (cpp.bv_end_function), the largest magnitude through a
        # volatile copy; the zeros of the whole space volatile stores.
        self.assertIn('KAIRN_GEN_NOINLINE void bv_add_2_end(double m, bool ok, double rx, double ry, double& rad_out_, '
                      'bool& fin_out_) noexcept {\n    volatile double m_v_ = m;\n    const double m_e_ = m_v_;\n', text)
        self.assertIn('    bv_add_2_end(m, ok, rx, ry, rad_r_, rad_f_);\n', text)
        self.assertIn('            static_cast<volatile double*>(z0_out)[i_] = 0.0;\n', text)
        self.assertIn('inline void bv_scale_1_lanes(const float* x_in, std::size_t n, std::size_t lanes, float rx, '
                      'float a, float* z_out, float& r_out, bool& finite_out) noexcept {', text)
        from kairn_gen import simd
        self.assertIn('inline void bv_sub_2_packed(const double* x0_in', simd.header(simd.AVX2, self.ks))
        self.assertIn('KAIRN_GEN_NOINLINE void bv_sub_2_packed_end(double m', simd.header(simd.AVX2, self.ks))
        self.assertIn('inline void bv_sub_2_packed(const double* x0_in', simd.header(simd.NEON, self.ks))

    def test_the_models_and_statements(self):
        from kairn_gen import ieee
        m, s = rocq.fold_model(self.ks), rocq.fold_statements(self.ks)
        im, ist = ieee.fold_model(self.ks), ieee.fold_statements(self.ks)
        for name in BVS:
            for d in ('step', 'map', 'record', 'radius'):
                self.assertIn(f'Definition {name}_{d} ', m)
            self.assertIn(f'Definition {name}_spec : Prop :=', s)
            for d in ('step', 'map', 'record', 'combine', 'seq', 'lanes'):
                self.assertIn(f'Definition {name}_{d} ', im)
            for o in ('seq', 'lanes'):
                self.assertIn(f'Definition {name}_{o}_ieee_spec : Prop :=', ist)
        self.assertIn('    forall x_ y_ : R, Rabs (x_ - (x0 + x1)) <= rx -> Rabs (y_ - (y0 + y1)) <= ry -> '
                      'Rabs ((x_ + y_) - (z0 + z1)) <= r_)', s)
        self.assertIn('  (if snd f_ then (ws_, fst f_) else (map (fun _ => (pzero, pzero)) ws_, pinf), snd f_).', im)
        # No lead statement of the combination of a fold of maxima, which a ball vector names.
        self.assertNotIn('norm_combine_ieee_lead_spec', ist)

    def test_the_claims(self):
        import json
        doc = json.loads(claims.claims(self.ks))
        e = {x['name']: x for x in doc['folds']}['bv_add_2']
        self.assertEqual([k for k in e], ['name', 'bv', 'domain', 'arrays', 'scalars', 'writes', 'outputs', 'value',
                                          'requires', 'ensures', 'orders', 'packed_lanes', 'step', 'step_args',
                                          'record', 'combine', 'radius', 'radius_args', 'finish', 'min_precision',
                                          'status', 'theorem', 'source'])
        self.assertEqual(e['requires'], ['ball_vector(x, rx)', 'ball_vector(y, ry)'])
        self.assertEqual(e['ensures'], [{'kind': 'encloses_entries', 'center': 'z', 'radius': 'r', 'flag': 'finite',
                                         'set': 'x+y', 'balls': {'x': {'center': 'x', 'radius': 'rx'},
                                                                 'y': {'center': 'y', 'radius': 'ry'}},
                                         'finite_when': [{'abs_le': 'abs(x+y)+rx+ry', 'exp': -2}],
                                         'radii_when': [{'abs_le': 'rx+ry', 'exp': -2}]}])

    def test_the_constructor_printers(self):
        import json
        from kairn_gen import ieee
        s, ist = rocq.fold_statements(self.ks), ieee.fold_statements(self.ks)
        self.assertIn('  bv_make_1_radius emin prec tie_even r cs = r /\\\n'
                      '  Forall2 (fun c w_ => w_ = c) cs (bv_make_1_map emin prec tie_even cs).', s)
        for name in MAKES:
            for o in ('seq', 'lanes'):
                self.assertIn(f'Definition {name}_{o}_ieee_spec : Prop :=', ist)
        self.assertIn('  (flag_ = true <-> finite r /\\ 0 <= val r /\\ Forall (fun c => finite (fst c)) cs) /\\', ist)
        doc = json.loads(claims.claims(self.ks))
        e = {x['name']: x for x in doc['folds']}['bv_make_2']
        self.assertEqual(e['requires'], ['canonical(c)'])
        self.assertEqual(e['ensures'], [{'kind': 'makes_ball_vector', 'center': 'z', 'radius': 'rr', 'flag': 'finite',
                                         'from': {'center': 'c', 'radius': 'r'}}])
        k = {x['name']: x for x in doc['kernels']}['bv_make_finish']
        self.assertEqual(k['ensures'], [{'kind': 'finite_or_nan', 'of': 'r', 'flag': 'flag', 'if': 'ok',
                                         'nonneg': True}])
        self.assertIn('inline void bv_make_1_seq(const double* c_in, std::size_t n, double r, double* z_out, '
                      'double& rr_out, bool& finite_out) noexcept {', cpp.scalar(self.ks))

    def test_the_entries_of_architecture_md(self):
        """The two entries that architecture.md writes out ("Claims of Milestone 2", ball vectors) are
        those of gen/claims.json, field for field, and so are the claims of the radius kernels it
        quotes."""
        import json
        import os
        with open(os.path.join(common.ROOT, 'docs', 'developer', 'architecture.md'), encoding='utf-8') as f:
            text = f.read()
        part = text.split('**Ball vectors** ([Ball vectors](#ball-vectors))', 1)[1]
        block = part.split('```json\n', 1)[1].split('\n```', 1)[0]
        written = json.loads('[' + block + ']')
        with open(os.path.join(common.GEN, 'claims.json'), encoding='utf-8') as f:
            doc = json.load(f)
        by = {x['name']: x for x in doc['folds']}
        self.assertEqual([w['name'] for w in written], ['bv_add_2', 'bv_scale_1'])
        for w in written:
            self.assertEqual(w, by[w['name']], w['name'])
        kernels = {k['name']: k for k in doc['kernels']}
        self.assertEqual(kernels['bv_add_radius_2']['ensures'], [
            {'kind': 'upper', 'of': 'rz', 'value': 'rx+ry+m*unit(add_2_2)/(1-unit(add_2_2))*(1+u)'}])
        self.assertEqual(kernels['bv_scale_radius_1']['ensures'], [
            {'kind': 'upper', 'of': 'rz', 'value': 'abs(a)*rx+m*unit(mul_1_1)/(1-unit(mul_1_1))+tiny(mul_1_1)/(1-unit(mul_1_1))'}])
        self.assertIn('"value": "abs(a)*rx+m*unit(mul_1_1)/(1-unit(mul_1_1))+tiny(mul_1_1)/(1-unit(mul_1_1))"',
                      text.replace('\n', ' ').replace('"value": "abs', '"value": "abs'))

    def test_the_counts_of_the_loops(self):
        import json
        doc = json.loads(objcode.objcode(self.ks))
        names = doc['fold_parts']
        for name in BVS:
            for form, least in (('seq', {'step': 1, 'record': 1, 'radius': 1, 'finish': 1}),
                                ('lanes', {'step': 2, 'record': 2, 'combine': 1, 'radius': 1, 'finish': 1}),
                                ('packed', {'packed step': 1, 'packed record': 1, 'combine': 1, 'step': 1,
                                            'record': 1, 'radius': 1, 'finish': 1})):
                for t in objcode.LIMB_TYPES:
                    parts = {p[0]: dict(zip(names, p)) for p in doc['folds'][name][form][t]}
                    self.assertEqual({k: v['least'] for k, v in parts.items()}, least, (name, form))
                    radius = self.ks[self.ks.folds[name].radius[0]]
                    self.assertEqual(parts['radius']['fma'], objcode.kernel_counts(radius, self.ks)['packed'][t]['fma'])
                    self.assertEqual(parts['radius']['fma'], 3 if 'scale' in name else 0 if 'neg' in name else 2)
                    self.assertEqual(parts['record']['fma'], 0)


if __name__ == '__main__':
    unittest.main()
