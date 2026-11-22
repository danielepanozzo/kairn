"""The IEEE-model statements of the maps and the convolutions, and the lead statements of the
steps of the maps (proofs/gen/IeeeFoldStatements.v; docs/developer/architecture.md, "Maps",
"Convolutions", "In the formal models"), judged on what the code computes before anyone proves
them: the interpreter on formats of the shape of IEEE 754 (qmin + qmax = 3 - 2p, the formats of
Flocq's binary_float prec emax with emin = 3 - emax - prec) of a few bits, where overflow is near,
and in binary64 and binary32; and the compiled F_seq, F_lanes and conv's F_seq, on the same
requests in binary64 and binary32.

For a map, F_seq_ieee_spec and F_lanes_ieee_spec say, of canonical scalars and elements (any value
for one limb, a finite power of two for a scalar that must be one), element by element: if the
leading limb written is finite, every limb of the scalars, of the element and of what is written is
finite, what is written is the step of the real model on the values given (the interpreter with the
exponent range widened above, where nothing overflows), and the step's claims hold of it in exact
arithmetic; otherwise every limb written is a NaN and the mask is false. And the mask is true exactly
when every leading limb written is finite (on an empty list: true). K_ieee_lead_spec of each step:
for any operands at all (no requirement), a finite leading limb of the result means a finite leading
limb of every operand, scalars included.

For a convolution, conv_k_ieee_spec says, coefficient by coefficient: if its leading limb is finite,
every limb of each of its terms and of it is finite, it is the sequential order of the fold of its
coefficients in the real model on the values of its terms, and that fold's claims hold of it;
otherwise every limb is a NaN. And the mask is true exactly when every leading limb is finite.
"""
import math
import random
import subprocess
import unittest
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F

import common
import test_cxx as cxx
import test_folds as folds_tests
import test_statements as st
from kairn_gen import consts, expr, interp, ir, rules

MAPS = sorted(folds_tests.MAPS)
CONVS = ('conv_1', 'conv_2')
ZERO = (interp.NUM, False, 0, 0)
SPECIALS = [(interp.INF, False), (interp.INF, True), interp.NaN]


def ieee_format(p, emax):
    """The format of binary_float p emax: qmax = emax - p, qmin = 3 - emax - p."""
    return interp.Format(f'fp:{p}:{3 - emax - p}:{emax - p}', p, 3 - emax - p, emax - p)


def widened(f):
    """The same precision and underflow threshold, with room above: the real model."""
    q = 2 * abs(f.qmax) + 4 * f.p + 64
    return interp.Format(f'fp:{f.p}:{f.qmin}:{q}', f.p, f.qmin, q)


def exact(v):
    return F(v[2]) * F(2) ** v[3] * (-1 if v[1] else 1)


def finite(v):
    return v[0] == interp.NUM


def numbers(f):
    """Numbers of the format to draw from: every one of a small format, edges and random ones of a
    large one (every exponent, the top included)."""
    if f.qmax - f.qmin <= 40:
        return sorted({interp.canon(s, m, q) for q in range(f.qmin, f.qmax + 1) for m in range(1, 2 ** f.p)
                       for s in (False, True)}, key=str) + [ZERO, (interp.NUM, True, 0, 0)]
    rng = random.Random(f'numbers:{f.name}')
    qs = list(range(f.qmin, f.qmin + 2 * f.p)) + list(range(f.qmax - 2 * f.p, f.qmax + 1)) + \
        [rng.randint(f.qmin, f.qmax) for _ in range(60)] + list(range(-3 * f.p, 3 * f.p))
    out = [ZERO, (interp.NUM, True, 0, 0)]
    for q in qs:
        for m in (1, 3, 2 ** f.p - 1, 2 ** (f.p - 1) + 1, rng.randrange(1, 2 ** f.p)):
            out += [interp.canon(s, m, q) for s in (False, True)]
    return out


class Draw:
    """Operands of one format: one limb any value (specials included), two limbs a canonical pair
    (a finite normalized pair, (+-inf, +-0) or (NaN, NaN)), a power of two finite."""

    def __init__(self, f, rng, special=0.15):
        self.f, self.rng, self.special = f, rng, special
        self.nums = numbers(f)
        self.big = [v for v in self.nums if finite(v) and v[2] and v[3] + v[2].bit_length() >= f.qmax + f.p - 2]

    def one(self):
        r = self.rng.random()
        if r < self.special:
            return self.rng.choice(SPECIALS)
        if r < self.special + 0.15 and self.big:
            return self.rng.choice(self.big)            # near the top: overflow
        return self.rng.choice(self.nums)

    def pair(self):
        x0 = self.one()
        if not finite(x0):
            return [x0, interp.NaN if x0 == interp.NaN else self.rng.choice([ZERO, (interp.NUM, True, 0, 0)])]
        if x0[2] == 0:
            return [x0, self.rng.choice([ZERO, (interp.NUM, True, 0, 0)])]
        q = max(x0[3] + x0[2].bit_length() - self.f.p, self.f.qmin)     # the gap at x0 is 2^q
        cands = [ZERO]
        for m, e in [(1, self.f.qmin), (1, q - 1), (1, q - 2), (3, q - 3), ((1 << max(q - 1 - self.f.qmin, 0)) - 1,
                                                                            self.f.qmin)]:
            if m and e >= self.f.qmin:
                for s in (False, True):
                    y = interp.canon(s, m, e)
                    if interp.member(self.f, y) and interp.eq(interp.add(self.f, x0, y), x0):
                        cands.append(y)
        return [x0, self.rng.choice(cands)]

    def group(self, n):
        return [self.one()] if n == 1 else self.pair()

    def power_of_two(self):
        q = self.rng.randint(self.f.qmin, self.f.qmax)
        return interp.canon(self.rng.random() < 0.5, 1, q)


def map_case(fd, draw, n):
    """(scalars' limbs, elements: each a list of limbs in the order of the arrays)."""
    pow2 = {r[1] for r in fd.requires if r[0] == 'power_of_two'}
    scalars = []
    for g in fd.scalars:
        scalars += [draw.power_of_two()] if g.name in pow2 else draw.group(len(g.limbs))
    return scalars, [[v for g in fd.arrays for v in draw.group(len(g.limbs))] for _ in range(n)]


def judge_map(m, ks, fd, f, scalars, elements, out, wide, judged):
    """The failures of the IEEE-model statement of map fd on one case: `out` is the list of the
    written limb arrays and the mask (Machine.run_fold), `judged` a test_statements.Format of the
    widened format for the claims in exact arithmetic, or None (a format too large to enumerate)."""
    step = ks[fd.step[0]]
    written, flag = out[:-1], out[-1]
    bad = []
    if any(len(a) != len(elements) for a in written):
        return ['length']
    given, at = {}, 0
    for g in fd.scalars:
        given[g.name] = scalars[at:at + len(g.limbs)]
        at += len(g.limbs)
    for i, e in enumerate(elements):
        groups, at = dict(given), 0
        for g in fd.arrays:
            groups[g.name] = e[at:at + len(g.limbs)]
            at += len(g.limbs)
        args = [v for a in fd.step[1] for v in groups[a]]
        z = [a[i] for a in written]
        if finite(z[0]):
            if not all(finite(v) for v in args + z):
                bad.append((i, 'a limb not finite with a finite leading limb written'))
                continue
            real = m.run(step.name, wide, args)
            if [exact(v) for v in real] != [exact(v) for v in z]:
                bad.append((i, 'not the real model of the step'))
                continue
            if judged is not None:
                ins, limbs, it = {}, {}, iter(args)
                for g in step.inputs:
                    vals = [exact(next(it)) for _ in g.limbs]
                    ins[g.name] = sum(vals)
                    limbs.update({expr.limb_key(g.name, j): v for j, v in enumerate(vals)})
                outs = {step.outputs[0].name: [exact(v) for v in z]}
                failed = [x['kind'] for x in step.ensures if not st.holds(x, step, judged, ins, outs, limbs, ks)]
                if failed:
                    bad.append((i, 'claims', failed))
        else:
            if not all(v == interp.NaN for v in z):
                bad.append((i, 'not every limb a NaN'))
            if flag is not False:
                bad.append((i, 'a mask that is not false'))
    if flag != all(finite(a[i]) for a in written[:1] for i in range(len(elements))):
        bad.append(('mask', flag))
    return bad


def _judge_maps(job):
    name, p, emax, rounds = job
    ks = common.kernels()
    fd = ks.folds[name]
    m = interp.Machine(ks)
    f = ieee_format(p, emax) if p else interp.parse_format(emax)
    wide = widened(f)
    judged = st.Format(wide.p, wide.qmin, wide.qmax) if f.p <= 8 else None
    rng = random.Random(f'ieee-writers:{name}:{f.name}')
    draw = Draw(f, rng)
    bad, count, written_not_finite, finite_with_special = [], 0, 0, 0
    orders = [('sequential', 0)] + [('lanes', w) for w in (0, 1, 2, 3, 4)]
    for r in range(rounds):
        n = r % 7
        scalars, elements = map_case(fd, draw, n)
        arrays = [[e[j] for e in elements] for j in range(len(fd.array_limbs()))]
        first = None
        for order, w in orders:
            if order not in fd.orders:
                continue
            out = m.run_fold(name, f, order, w, arrays, scalars)
            if first is None:
                first = out
                for x in judge_map(m, ks, fd, f, scalars, elements, out, wide, judged):
                    bad.append((name, f.name, order, w, n, x))
                count += n
                written_not_finite += sum(1 for i in range(n) if not finite(out[0][i]))
            elif out != first:
                bad.append((name, f.name, order, w, n, 'not the sequential order\'s'))
    return name, f.name, count, written_not_finite, bad[:5]


def lead_failures(m, ks, step, f, rng, rounds):
    """The cases of K_ieee_lead_spec of a step that fail: any value of every limb (no requirement),
    the leading limb of the result finite and that of an operand not."""
    draw = Draw(f, rng, special=0.0)
    bad, seen = [], 0
    for _ in range(rounds):
        # Finite limbs, some near the top, and in most cases one or two limbs, of any position, an
        # infinity or a NaN.
        args = [draw.one() for _ in step.input_limbs]
        for _ in range(rng.choice((0, 1, 1, 1, 2))):
            args[rng.randrange(len(args))] = rng.choice(SPECIALS)
        out = m.run(step.name, f, args)
        leads = [g.limbs[0] for g in step.inputs if g.kind == ir.LIMB]
        position = {v: i for i, v in enumerate(step.input_limbs)}
        if finite(out[0]):
            seen += 1
            if not all(finite(args[position[v]]) for v in leads):
                bad.append((step.name, f.name, [interp.format_limb(a) for a in args]))
    return bad, seen


def _judge_leads(job):
    name, p, emax = job
    ks = common.kernels()
    m = interp.Machine(ks)
    f = ieee_format(p, emax) if p else interp.parse_format(emax)
    rng = random.Random(f'lead:{name}:{f.name}')
    bad, seen = lead_failures(m, ks, ks[name], f, rng, common.size(1500, 20000))
    return name, f.name, seen, bad[:3]


def conv_case(fd, draw, nx, ny):
    gx, gy = fd.arrays
    return [draw.group(len(gx.limbs)) for _ in range(nx)], [draw.group(len(gy.limbs)) for _ in range(ny)]


def judge_conv(m, ks, fd, f, xs, ys, out, wide, eps, term, tau, heights):
    """The failures of the IEEE-model statement of convolution fd on one case."""
    cf = ks.folds[fd.coefficients]
    written, flag = out[:-1], out[-1]
    nx, ny = len(xs), len(ys)
    nz = 0 if nx == 0 or ny == 0 else nx + ny - 1
    bad = []
    if any(len(a) != nz for a in written):
        return ['length']
    for j in range(nz):
        c = [a[j] for a in written]
        terms = [(xs[i], ys[j - i]) for i in range(max(0, j - ny + 1), min(j, nx - 1) + 1)]
        if finite(c[0]):
            if not all(finite(v) for x, y in terms for v in x + y) or not all(finite(v) for v in c):
                bad.append((j, 'a limb not finite with a finite leading limb'))
                continue
            arrays = [[x[k] for x, _ in terms] for k in range(len(fd.arrays[0].limbs))] + \
                [[y[k] for _, y in terms] for k in range(len(fd.arrays[1].limbs))]
            real = m.run_fold(cf.name, wide, 'sequential', 0, arrays)[:-1]     # the finish keeps a finite state
            if [exact(v) for v in real] != [exact(v) for v in c]:
                bad.append((j, 'not the real model of the fold of the coefficients'))
                continue
            vals = [sum(exact(v) for v in x) * sum(exact(v) for v in y) for x, y in terms]
            n = len(vals)
            rel = n if heights['rel'] == 'n' else max(n - 1, 0)
            ab = n if heights['abs'] == 'n' else max(n - 1, 0)
            bound = ((1 + term) * (1 + eps) ** rel - 1) * sum(abs(v) for v in vals) + (1 + eps) ** ab * n * tau
            if abs(sum(exact(v) for v in c) - sum(vals)) > bound:
                bad.append((j, 'bound'))
            if len(c) == 2 and not interp.eq(interp.add(wide, c[0], c[1]), c[0]):
                bad.append((j, 'normalized'))
        elif not all(v == interp.NaN for v in c):
            bad.append((j, 'not every limb a NaN'))
    if flag != all(finite(written[0][j]) for j in range(nz)):
        bad.append(('mask', flag))
    return bad


def _conv_constants(ks, fd, p, qmin):
    import json
    import os
    doc = {x['name']: x for x in json.loads(open(os.path.join(common.GEN, 'claims.json')).read())['folds']}
    err = next(e for e in doc[fd.coefficients]['ensures'] if e['kind'] == 'fold_error')
    return [consts.evaluate(expr.parse(err[k]), ks, p, qmin) for k in ('eps', 'term', 'tau')] + \
        [err['heights']['sequential']]


def _judge_convs(job):
    name, p, emax, rounds = job
    ks = common.kernels()
    fd = ks.folds[name]
    m = interp.Machine(ks)
    f = ieee_format(p, emax) if p else interp.parse_format(emax)
    wide = widened(f)
    eps, term, tau, heights = _conv_constants(ks, fd, f.p, f.qmin)
    rng = random.Random(f'ieee-conv:{name}:{f.name}')
    draw = Draw(f, rng, special=0.08)
    bad, count, not_finite = [], 0, 0
    for r in range(rounds):
        nx, ny = r % 5, (r // 5) % 5
        xs, ys = conv_case(fd, draw, nx, ny)
        arrays = [[x[k] for x in xs] for k in range(len(fd.arrays[0].limbs))] + \
            [[y[k] for y in ys] for k in range(len(fd.arrays[1].limbs))]
        out = m.run_fold(name, f, 'sequential', 0, arrays)
        for x in judge_conv(m, ks, fd, f, xs, ys, out, wide, eps, term, tau, heights):
            bad.append((name, f.name, nx, ny, x))
        count += len(out[0])
        not_finite += sum(1 for v in out[0] if not finite(v))
    return name, f.name, count, not_finite, bad[:5]


# The formats: of the shape of IEEE 754, a few bits, overflow near (emax = p + 3: the largest number
# is below 2^(p+3)); and the two of the library.
def toy_formats(min_precision):
    return [(p, p + 3) for p in range(max(min_precision, 2), 6)]


class Maps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()

    def test_the_ieee_reading(self):
        jobs = []
        for name in MAPS:
            fd = self.ks.folds[name]
            jobs += [(name, p, emax, common.size(120, 1200)) for p, emax in toy_formats(fd.min_precision)]
            jobs += [(name, None, fmt, common.size(60, 600)) for fmt in ('binary64', 'binary32')]
        with ProcessPoolExecutor(max_workers=common.JOBS) as ex:
            results = list(ex.map(_judge_maps, jobs))
        self.assertEqual([r[4] for r in results if r[4]], [])
        # The cases include elements written that are not finite, from an operand that is not or
        # from an overflow, for every map.
        for name in MAPS:
            mine = [r for r in results if r[0] == name]
            self.assertGreater(sum(r[2] for r in mine), 300, name)
            self.assertGreater(sum(r[3] for r in mine), 20, name)

    def test_the_lead_statements(self):
        names = sorted({self.ks.folds[n].step[0] for n in MAPS})
        # (and scale_entry_step_2, the step of scale_2_entry: rule R3)
        self.assertEqual(len(names), 19)
        jobs = [(name, p, p + 3) for name in names for p in range(max(self.ks[name].min_precision or 1, 2), 6)]
        jobs += [(name, None, fmt) for name in names for fmt in ('binary64', 'binary32')]
        with ProcessPoolExecutor(max_workers=common.JOBS) as ex:
            results = list(ex.map(_judge_leads, jobs))
        self.assertEqual([r[3] for r in results if r[3]], [])
        for name in names:
            self.assertGreater(sum(r[2] for r in results if r[0] == name), 100, name)

    def test_an_overflow_in_a_finite_array(self):
        """Finite operands whose step overflows: the element written is the canonical NaN, the mask is
        false, and the other elements are kept as computed."""
        m = interp.Machine(self.ks)
        f = interp.parse_format('binary64')
        top = interp.canon(False, 2 ** 53 - 1, 971)
        one = interp.canon(False, 1, 0)
        out = m.run_fold('add_1', f, 'sequential', 0, [[one, top, one], [one, top, one]])
        self.assertEqual(out[0][1], interp.NaN)
        self.assertEqual([exact(out[0][0]), exact(out[0][2])], [2, 2])
        self.assertIs(out[-1], False)
        out = m.run_fold('add_2', f, 'lanes', 2, [[one, top], [ZERO, ZERO], [one, top], [ZERO, ZERO]])
        self.assertEqual([out[0][1], out[1][1]], [interp.NaN, interp.NaN])
        self.assertEqual([exact(out[0][0]), exact(out[1][0])], [2, 0])
        self.assertIs(out[-1], False)
        # An empty list: the mask is true, and nothing is said of the scalars (a NaN one here).
        self.assertEqual(m.run_fold('axpy_1', f, 'sequential', 0, [[], []], [interp.NaN]), [[], True])


class Convs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()

    def test_the_ieee_reading(self):
        jobs = []
        for name in CONVS:
            fd = self.ks.folds[name]
            jobs += [(name, p, emax, common.size(150, 1500)) for p, emax in toy_formats(fd.min_precision)]
            jobs += [(name, None, fmt, common.size(100, 800)) for fmt in ('binary64', 'binary32')]
        with ProcessPoolExecutor(max_workers=common.JOBS) as ex:
            results = list(ex.map(_judge_convs, jobs))
        self.assertEqual([r[4] for r in results if r[4]], [])
        for name in CONVS:
            mine = [r for r in results if r[0] == name]
            self.assertGreater(sum(r[2] for r in mine), 500, name)
            self.assertGreater(sum(r[3] for r in mine), 30, name)


# ---------------------------------------------------------------------------------------------
# The compiled code, on the same statements.

def cxx_corpus(seed):
    """[(kind, fold, format, request line, the case)] in binary64 and binary32."""
    ks = common.kernels()
    out = []
    for fmt in ('binary64', 'binary32'):
        f = interp.parse_format(fmt)
        rng = random.Random(f'{seed}:{fmt}')
        draw = Draw(f, rng)
        for name in MAPS:
            fd = ks.folds[name]
            for r in range(common.size(40, 300)):
                n = r % 9
                scalars, elements = map_case(fd, draw, n)
                for order, w in [('sequential', 0)] + [('lanes', x) for x in (0, 2, 3, 4)]:
                    o = 'seq' if order == 'sequential' else f'lanes:{w}'
                    limbs = scalars + [e[j] for j in range(len(fd.array_limbs())) for e in elements]
                    line = f'{name} {fmt} {o} {n}' + ''.join(' ' + interp.format_limb(v) for v in limbs)
                    out.append(('map', name, fmt, line, (scalars, elements)))
        draw = Draw(f, rng, special=0.08)
        for name in CONVS:
            fd = ks.folds[name]
            for r in range(common.size(60, 400)):
                nx, ny = r % 6, (r // 6) % 6
                xs, ys = conv_case(fd, draw, nx, ny)
                limbs = [x[k] for k in range(len(fd.arrays[0].limbs)) for x in xs] + \
                    [y[k] for k in range(len(fd.arrays[1].limbs)) for y in ys]
                line = f'{name} {fmt} seq {nx} {ny}' + ''.join(' ' + interp.format_limb(v) for v in limbs)
                out.append(('conv', name, fmt, line, (xs, ys)))
    return out


class Cxx(unittest.TestCase):
    """Every build of the runner, on the requests above: what it prints satisfies the statements."""

    @classmethod
    def setUpClass(cls):
        if not cxx.COMPILERS:
            raise unittest.SkipTest('no C++ compiler (set KAIRN_GEN_CXX)')
        cls.ks = common.kernels()
        cls.builds = cxx.shared_builds()
        cls.cases = cxx_corpus('ieee-writers')

    def judge(self, out):
        m = interp.Machine(self.ks)
        lines = out.splitlines()
        self.assertEqual(len(lines), len(self.cases))
        bad = []
        for (kind, name, fmt, request, case), line in zip(self.cases, lines):
            self.assertTrue(line.startswith(request + ' -> '), line[:200])
            tokens = line.split(' -> ')[1].split()
            flag = tokens[-1] == '1'
            values = [interp.parse_limb(t) for t in tokens[:-1]]
            fd = self.ks.folds[name]
            f = interp.parse_format(fmt)
            width = len(fd.write_limbs())
            n = len(values) // width if width else 0
            out_ = [values[k * n:(k + 1) * n] for k in range(width)] + [flag]
            if kind == 'map':
                failures = judge_map(m, self.ks, fd, f, case[0], case[1], out_, widened(f), None)
            else:
                eps, term, tau, heights = _conv_constants(self.ks, fd, f.p, f.qmin)
                failures = judge_conv(m, self.ks, fd, f, case[0], case[1], out_, widened(f), eps, term, tau, heights)
            if failures:
                bad.append((request[:120], failures[:2]))
        return bad

    def test_every_build(self):
        text = ''.join(c[3] + '\n' for c in self.cases)
        judged = None
        for i, (label, _) in enumerate(self.builds.configs):
            with self.subTest(build=label):
                status, err = self.builds.results[i]
                self.assertEqual(status, 0, err)
                code, out, err = self.builds.run(i, text)
                self.assertEqual(code, 0, err)
                if out == judged:
                    continue
                self.assertEqual(self.judge(out)[:3], [])
                judged = out
        self.assertTrue(any(c[0] == 'map' for c in self.cases) and any(c[0] == 'conv' for c in self.cases))


if __name__ == '__main__':
    unittest.main()
