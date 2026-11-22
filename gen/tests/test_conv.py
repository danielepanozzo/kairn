"""The convolutions (docs/developer/design/milestone2.md, "sum, dot, axpy, convolution": conv_k;
docs/developer/architecture.md, "Convolutions").

- Their rules: each way of getting a convolution wrong is refused (rules.conv_rules).
- The interpreter: coefficient j is the fold of the coefficients (dot_k) in its sequential order on
  the terms (x_i, y_(j-i)), i increasing, as the interpreter runs that fold on those terms; there are
  n_x + n_y - 1 of them, none when a length is 0; a term that is not finite gives the canonical NaN
  for every coefficient that has it and a false mask, the others are kept; the line protocol with
  two lengths.
- The claims in exact arithmetic on toy formats: every coefficient within the bound of the fold of
  the coefficients for its own number of terms, which is at most min(n_x, n_y).
- The compiled C++: F_seq of every build of the runner bit for bit against the interpreter, on
  lengths 0, 1, 2, ... and random ones, the two lengths different, non-finite terms among them.
- The model and the statement in Rocq, the claims, the C++ text and the counts of the loop.
"""
import json
import math
import os
import random
import unittest
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F

import common
import test_cxx as cxx
import test_folds as folds_tests
from kairn_gen import claims, consts, cpp, expr, interp, ir, objcode, rocq, rules

CONVS = ('conv_1', 'conv_2', 'conv_1_entry', 'conv_2_entry')

BASE = '''
fold:          tc
arrays:        stored x = x0 x1, stored y = y0 y1
coefficients:  dot_2
state:         mask finite
combine:       finite = and(finite, finite)
orders:        sequential
writes:        z = z0 z1
check:         fold_finish_2
finish:        none
value:         x*y
requires:      canonical x
requires:      canonical y
ensures:       coefficients z
ensures:       finite_or_nan z flag=finite
min_precision: 4
status:        unverified
domain:        extended
'''


def refusals(text):
    ks = dict(common.kernels())
    fd = ir.parse_fold(text, 'tc.fold')
    return [str(e) for e in rules.fold_rules(fd, ir.ordered(ks, dict(common.kernels().folds, tc=fd)))]


class Rules(unittest.TestCase):
    def test_the_convolutions_are_accepted(self):
        ks = common.kernels()
        self.assertEqual({n for n, fd in ks.folds.items() if fd.is_conv}, set(CONVS))
        for name in CONVS:
            self.assertFalse(ks.folds[name].is_map, name)
            self.assertEqual(rules.fold_rules(ks.folds[name], ks), [], name)
        self.assertEqual(refusals(BASE), [])

    def refused(self, text, words):
        errors = refusals(text)
        self.assertTrue(any(words in e for e in errors), (words, errors))

    def test_the_parts(self):
        self.refused(BASE.replace('coefficients:  dot_2', 'coefficients:  sum_2'), 'arrays: two, those of sum_2')
        self.refused(BASE.replace('coefficients:  dot_2', 'coefficients:  axpy_2'), 'is not a fold of a sum')
        self.refused(BASE.replace('coefficients:  dot_2', 'coefficients:  norm_upper_2'), 'is not a fold of a sum')
        self.refused(BASE.replace('orders:        sequential', 'orders:        sequential, lanes'),
                     'orders: sequential: each coefficient')
        self.refused(BASE.replace('check:         fold_finish_2', 'check:         fold_finish_1'),
                     'check: fold_finish_2, the finish of dot_2')
        self.refused(BASE.replace('orders:', 'step:          s = dot_step_2(s, x, y)\norders:'),
                     'a convolution has no step of its own')
        self.refused(BASE.replace('writes:        z = z0 z1', 'writes:        z'), 'of the shape of the state of dot_2')
        self.refused(BASE.replace('mask finite', 'finite').replace('flag=finite', 'flag=finite'),
                     'the state of a convolution is one mask')
        self.refused(BASE.replace('stored y = y0 y1', 'supplied y = y0 y1'), 'with their names, limbs and roles')
        self.refused(BASE.replace('z = z0 z1', 's = z0 z1'), 'a name of the state of dot_2')
        with self.assertRaises(ir.DescriptionError):            # without coefficients, a step is needed
            ir.parse_fold(BASE.replace('coefficients:  dot_2\n', ''), 'tc.fold')

    def test_claims(self):
        self.refused(BASE.replace('value:         x*y', 'value:         x+y'), 'that of a term of dot_2')
        self.refused(BASE.replace('requires:      canonical y\n', ''), 'requires: those of dot_2')
        self.refused(BASE.replace('ensures:       coefficients z\n', ''), 'ensures: coefficients z')
        self.refused(BASE.replace('domain:        extended\n', ''), 'a convolution is of the extended domain')
        self.refused(BASE.replace('min_precision: 4', 'min_precision: 3'), 'at least that of dot_2')
        self.refused(BASE.replace('status:        unverified', 'status:        proved'), 'names no theorem')


# ---------------------------------------------------------------------------------------------
# The interpreter.

def operands(rng, fd, fmt, n, special=0.0):
    """n entries of one array of the convolution: limb lists (normalized pairs for two limbs)."""
    g = fd.arrays[0]
    sub = ir.Fold(name='one', path='', arrays=[g], roles={g.name: 'supplied'})
    return folds_tests.elements_for(rng, sub, fmt, n, special)


def limb_arrays(fd, xs, ys):
    """The limb arrays of a request: those of x, then those of y."""
    lx, ly = len(fd.arrays[0].limbs), len(fd.arrays[1].limbs)
    return [[e[i] for e in xs] for i in range(lx)] + [[e[i] for e in ys] for i in range(ly)]


def request(fd, fmt, xs, ys):
    limbs = [x for a in limb_arrays(fd, xs, ys) for x in a]
    return f'{fd.name} {fmt} seq {len(xs)} {len(ys)}' + ''.join(' ' + common.token(x) for x in limbs)


_machines = {}


def _run_conv(job):
    name, fmt, arrays = job
    if 'm' not in _machines:
        _machines['m'] = interp.Machine(common.kernels())
    f = interp.parse_format(fmt)
    out = _machines['m'].run_fold(name, f, 'sequential', 0, [[common.to_value(x) for x in a] for a in arrays])
    return [common.to_float(v) for a in out[:-1] for v in a] + [out[-1]]


class Interp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()
        cls.m = interp.Machine(cls.ks)

    def test_each_coefficient_is_the_dot_of_its_terms(self):
        rng = random.Random('conv')
        for name in CONVS:
            fd = self.ks.folds[name]
            cf = self.ks.folds[fd.coefficients]
            for fmt in ('binary64', 'binary32'):
                f = interp.parse_format(fmt)
                for nx, ny in ((1, 1), (1, 4), (4, 1), (3, 5), (6, 2), (7, 7), (0, 3), (3, 0), (0, 0)):
                    xs, ys = operands(rng, fd, fmt, nx), operands(rng, fd, fmt, ny)
                    arrays = [[common.to_value(v) for v in a] for a in limb_arrays(fd, xs, ys)]
                    out = self.m.run_fold(name, f, 'sequential', 0, arrays)
                    nz = 0 if nx == 0 or ny == 0 else nx + ny - 1
                    self.assertEqual([len(a) for a in out[:-1]], [nz] * len(fd.write_limbs()), (name, nx, ny))
                    for j in range(nz):
                        terms = [(i, j - i) for i in range(nx) if 0 <= j - i < ny]
                        self.assertLessEqual(len(terms), min(nx, ny))
                        tx = [[common.to_value(xs[i][k]) for i, _ in terms] for k in range(len(fd.arrays[0].limbs))]
                        ty = [[common.to_value(ys[i][k]) for _, i in terms] for k in range(len(fd.arrays[1].limbs))]
                        want = self.m.run_fold(cf.name, f, 'sequential', 0, tx + ty)
                        if out[-1]:
                            self.assertEqual([a[j] for a in out[:-1]], want[:-1], (name, fmt, nx, ny, j))

    def test_non_finite_terms(self):
        f = interp.parse_format('binary64')
        one, zero = interp.canon(False, 1, 0), (interp.NUM, False, 0, 0)
        for name in CONVS:
            fd = self.ks.folds[name]
            lx = len(fd.arrays[0].limbs)
            for bad in ((interp.INF, False), interp.NaN):
                x = [[one, one, one]] + [[zero] * 3 for _ in range(lx - 1)]
                y = [[one, one]] + [[zero] * 2 for _ in range(lx - 1)]
                x[0][2] = bad
                if lx == 2 and bad == interp.NaN:
                    x[1][2] = interp.NaN
                out = self.m.run_fold(name, f, 'sequential', 0, x + y)
                # x2 is in coefficients 2 and 3 only: they are the canonical NaN, the others kept.
                self.assertIs(out[-1], False, name)
                for a in out[:-1]:
                    self.assertEqual([v[0] for v in a], [interp.NUM, interp.NUM, interp.NAN, interp.NAN], name)

    def test_the_line_protocol(self):
        formats = {}
        line = 'conv_1 fp:5:-12:6 seq 3 2 0x1p+0 0x1p+1 0x1p+2 0x1p+0 0x1p-1 #t'
        self.assertEqual(interp.complete(self.m, line, formats), line + ' -> 0x1p+0 0x1.4p+1 0x1.4p+2 0x1p+1 1')
        self.assertEqual(interp.complete(self.m, 'conv_2 binary64 seq 0 2 0x1p+0 0x1p+0 0x0p+0 0x0p+0', formats),
                         'conv_2 binary64 seq 0 2 0x1p+0 0x1p+0 0x0p+0 0x0p+0 -> 1')
        for bad, words in (('conv_1 binary64 lanes:2 1 1 0x1p+0 0x1p+0', 'the sequential order only'),
                           ('conv_1 binary64 seq 2 1 0x1p+0 0x1p+0', 'takes 3 limbs'),
                           ('conv_1 binary64 seq 1', 'N_X N_Y'),
                           ('conv_2 binary64 seq x 1 0x1p+0 0x1p+0', 'not a length')):
            with self.assertRaises(interp.InterpError, msg=bad) as e:
                interp.complete(self.m, bad, formats)
            self.assertIn(words, str(e.exception), bad)

    def test_the_claims_in_exact_arithmetic(self):
        """On toy formats of precision 3 to 6: every coefficient, with the exponent range widened (the
        Rocq statement), satisfies the bound of fold_error of the fold of its coefficients in the
        sequential order with n its own number of terms; in the format itself, the flag is true
        exactly when every coefficient is finite, and the bound holds then."""
        doc = {fd['name']: fd for fd in json.loads(open(os.path.join(common.GEN, 'claims.json')).read())['folds']}
        jobs = [(name, fmt, doc[self.ks.folds[name].coefficients]) for name in CONVS
                for fmt in ((3, -8, 4), (4, -10, 4), (5, -12, 5), (6, -12, 5))
                if fmt[0] >= self.ks.folds[name].min_precision]
        with ProcessPoolExecutor(max_workers=common.JOBS) as ex:
            results = list(ex.map(_judge_conv, jobs))
        self.assertEqual([r for r in results if r[2]], [])
        self.assertGreater(sum(r[1] for r in results), 3000)


def _value(v):
    return F(v[2]) * F(2) ** v[3] * (-1 if v[1] else 1)


def _judge_conv(job):
    name, (p, qmin, qmax), claim = job
    ks = common.kernels()
    fd = ks.folds[name]
    m = interp.Machine(ks)
    rng = random.Random(f'conv:{name}:{p}')
    tight = interp.Format(f'fp:{p}:{qmin}:{qmax}', p, qmin, qmax)
    wide = interp.Format(f'fp:{p}:{qmin}:{qmax + 200}', p, qmin, qmax + 200)
    err = next(e for e in claim['ensures'] if e['kind'] == 'fold_error')
    eps, term, tau = (consts.evaluate(expr.parse(err[k]), ks, p, qmin) for k in ('eps', 'term', 'tau'))
    h = err['heights']['sequential']
    nums = sorted({interp.canon(s, mm, q) for q in range(qmin, qmax + 1) for mm in range(1, 2 ** p)
                   for s in (False, True)}, key=str)
    tails = {}
    for x0, x1 in rules._operands(tight, 2):
        tails.setdefault(x0, []).append(x1)
    lx = len(fd.arrays[0].limbs)

    def entry():
        x0 = rng.choice(nums)
        if lx == 1:
            return [x0]
        cands = [y for y in tails.get(x0, []) if interp.eq(interp.add(tight, x0, y), x0)]
        return [x0, rng.choice(cands or [(interp.NUM, False, 0, 0)])]

    failures, count = [], 0
    for _ in range(150):
        nx, ny = rng.randrange(0, 7), rng.randrange(0, 7)
        xs, ys = [entry() for _ in range(nx)], [entry() for _ in range(ny)]
        arrays = limb_arrays(fd, xs, ys)
        for f, reading in ((wide, 'statement'), (tight, 'format')):
            out = m.run_fold(name, f, 'sequential', 0, arrays)
            zs, flag = out[:-1], out[-1]
            nz = 0 if nx == 0 or ny == 0 else nx + ny - 1
            if flag != all(a[j][0] == interp.NUM for a in zs for j in range(nz)):
                failures.append((reading, nx, ny, 'flag'))
                continue
            if reading == 'statement' and not flag:
                failures.append((reading, nx, ny, 'not finite'))
                continue
            for j in range(nz):
                count += 1
                c = [a[j] for a in zs]
                if c[0][0] != interp.NUM:
                    if not all(v == interp.NaN for v in c):
                        failures.append((reading, nx, ny, j, 'not the NaN'))
                    continue
                terms = [sum(_value(v) for v in xs[i]) * sum(_value(v) for v in ys[j - i])
                         for i in range(nx) if 0 <= j - i < ny]
                n = len(terms)
                rel = n if h['rel'] == 'n' else max(n - 1, 0)
                ab = n if h['abs'] == 'n' else max(n - 1, 0)
                bound = ((1 + term) * (1 + eps) ** rel - 1) * sum(abs(t) for t in terms) + (1 + eps) ** ab * n * tau
                if abs(sum(_value(v) for v in c) - sum(terms)) > bound:
                    failures.append((reading, nx, ny, j, 'bound'))
                if lx == 2 and not interp.eq(interp.add(f, c[0], c[1]), c[0]):
                    failures.append((reading, nx, ny, j, 'normalized'))
    return name, count, failures[:3]


# ---------------------------------------------------------------------------------------------
# The compiled C++.

def conv_corpus(fmt, seed):
    """[(convolution, format, xs, ys, request line)]: every pair of lengths up to 5, and random
    ones up to a few hundred, with non-finite entries in some."""
    ks = common.kernels()
    rng = random.Random(f'{seed}:{fmt}')
    out = []
    for name in CONVS:
        fd = ks.folds[name]
        pairs = [(a, b) for a in range(6) for b in range(6)] + \
            [(rng.randrange(6, 60), rng.randrange(1, 60)) for _ in range(6)] + \
            [(rng.randrange(60, common.size(300, 2000)), rng.randrange(1, 40)) for _ in range(2)]
        for nx, ny in pairs:
            for special in (0.0, 0.05 if nx and ny else 0.0):
                xs, ys = operands(rng, fd, fmt, nx, special), operands(rng, fd, fmt, ny, special)
                out.append((name, fmt, xs, ys, request(fd, fmt, xs, ys)))
    return out


def expected(cases):
    ks = common.kernels()
    jobs = [(c[0], c[1], limb_arrays(ks.folds[c[0]], c[2], c[3])) for c in cases]
    with ProcessPoolExecutor(max_workers=common.JOBS) as ex:
        return list(ex.map(_run_conv, jobs, chunksize=4))


class Cxx(unittest.TestCase):
    """F_seq of every build of the runner, bit for bit against the interpreter."""

    @classmethod
    def setUpClass(cls):
        if not cxx.COMPILERS:
            raise unittest.SkipTest('no C++ compiler (set KAIRN_GEN_CXX)')
        cls.builds = cxx.shared_builds()
        cls.cases = conv_corpus('binary64', 'cxx') + conv_corpus('binary32', 'cxx')
        cls.want = expected(cls.cases)
        cls.text = ''.join(c[4] + '\n' for c in cls.cases)

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
                bad = cxx.differences([(c[0], c[1], None, c[4]) for c in self.cases], self.want, out)
                self.assertEqual([b[0][:200] for b in bad[:3]], [], f'{len(bad)} of {len(self.cases)} differ')
                reference = out

    def test_the_corpus(self):
        self.assertTrue(any(not math.isfinite(x) for c in self.cases for e in c[2] for x in e))
        self.assertTrue(any(w[-1] is False for w in self.want) and any(w[-1] is True for w in self.want))
        self.assertTrue(any(len(c[2]) == 0 for c in self.cases) and any(len(c[3]) == 0 for c in self.cases))

    def test_runner_protocol(self):
        code, out, err = self.builds.run(0, 'conv_1 binary64 seq 3 2 0x1p+0 0x1p+1 0x1p+2 0x1p+0 0x1p-1\n')
        self.assertEqual(code, 0, err)
        self.assertEqual(out, 'conv_1 binary64 seq 3 2 0x1p+0 0x1p+1 0x1p+2 0x1p+0 0x1p-1 -> '
                              '0x1p+0 0x1.4p+1 0x1.4p+2 0x1p+1 1\n')
        for line, words in (('conv_1 binary64 seq 1 1 0x1p+0', 'takes 2 limbs'),
                            ('conv_2 binary64 lanes:2 1 1 0x1p+0 0x0p+0 0x1p+0 0x0p+0', 'the sequential order only')):
            code, out, err = self.builds.run(0, '# fine\n' + line + '\n')
            self.assertEqual(code, 2, line)
            self.assertIn(words, err)


# ---------------------------------------------------------------------------------------------
# Rocq, the claims, the C++ text, the counts.

class Printers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()

    def test_the_model(self):
        m = rocq.fold_model(self.ks)
        self.assertIn('Definition conv_terms {A B : Type} (xs : list A) (ys : list B) (j : nat) : list (A * B) :=\n'
                      '  combine (skipn (j - (length ys - 1)) (firstn (S j) xs)) (rev (firstn (S j) ys)).', m)
        self.assertIn('Definition conv_2_conv (xs : list (R * R)) (ys : list (R * R)) : list (R * R) :=\n'
                      '  map (fun j => dot_2_seq (conv_terms xs ys j)) (seq 0 (conv_length (length xs) (length ys))).',
                      m)
        # After the fold of its coefficients, which it names.
        self.assertLess(m.index('Definition dot_1_seq '), m.index('Definition conv_1_conv '))
        # Without a convolution the lists are not printed.
        self.assertNotIn('conv_terms', rocq.fold_model(common.kernels(common.TEST_KERNELS)))

    def test_conv_terms_is_the_terms(self):
        """conv_terms of the model, written here with Python's lists exactly as the Rocq text has it,
        lists the terms of coefficient j in increasing i, for every pair of lengths up to 7."""
        def conv_terms(xs, ys, j):
            a = xs[:j + 1][max(j - max(len(ys) - 1, 0), 0):]
            return list(zip(a, list(reversed(ys[:j + 1]))))
        for nx in range(8):
            for ny in range(8):
                xs, ys = [f'x{i}' for i in range(nx)], [f'y{i}' for i in range(ny)]
                nz = 0 if nx == 0 or ny == 0 else nx + ny - 1
                for j in range(nz + 2):
                    want = [(f'x{i}', f'y{j - i}') for i in range(nx) if 0 <= j - i < ny]
                    self.assertEqual(conv_terms(xs, ys, j), want, (nx, ny, j))

    def test_the_statement(self):
        s = rocq.fold_statements(self.ks)
        self.assertIn('Definition conv_1_spec : Prop :=\n'
                      '  forall emin prec : Z, (1 <= prec)%Z ->\n'
                      '  forall xs ys : list R,\n'
                      '  Forall (fun x => fmt emin prec x) xs ->\n'
                      '  Forall (fun y => fmt emin prec y) ys ->\n'
                      '  Forall2 (fun j s =>\n'
                      '    let xys := conv_terms xs ys j in\n'
                      '    fmt emin prec s /\\\n'
                      '    Rabs (s - sumR (map (fun xy => (fst xy * snd xy)) xys)) <=\n', s)
        self.assertIn('    (seq 0 (conv_length (length xs) (length ys))) (conv_2_conv emin prec tie_even xs ys).', s)
        # A convolution that is unverified is not in the audit, whatever the descriptions say (the
        # convolutions of the library are proved, FoldConv.v); one that is proved is, once, with
        # its one statement.
        import copy
        ks = copy.deepcopy(self.ks)
        # (and the products of two BallVectors, proved too, BvConv.v, whose names contain conv_1, and
        # conv_1_entry and conv_2_entry, the convolutions on their factors guarded, rule R3)
        for name in ('conv_1', 'conv_2', 'bv_conv_1', 'bv_conv_2', 'conv_1_entry', 'conv_2_entry'):
            ks.folds[name].status, ks.folds[name].theorem = 'unverified', None
        self.assertNotIn('conv_1', rocq.audit(ks))
        ks.folds['conv_1'].status, ks.folds['conv_1'].theorem = 'proved', 'proofs/theories/FoldConv.v'
        self.assertIn('\nDefinition conv_1_audit : conv_1_spec := conv_1_correct.\n'
                      'Print Assumptions conv_1_correct.\n', rocq.audit(ks))

    def test_the_terms_theorem(self):
        """terms_theorem: FILE, of the convolutions: the file of conv_terms_eq_correct,
        conv_terms_count_correct and conv_terms_length_correct, the theorems of the three statements of
        conv_terms that every convolution shares. Named by both convolutions, or by one, the comments of
        the three statements say proved and the real-model audit checks the three theorems, once, after
        those of the folds; named by none, they say unverified and the audit has none. Two different
        files, another path, or a fold that is not a convolution: refused. Judged from the descriptions
        with every terms_theorem removed, so that it means the same whatever they say."""
        def kernels_with(files):
            ks = common.kernels()

            def text(fd):
                with open(os.path.join(common.GEN, 'kernels', fd.path), encoding='utf-8') as f:
                    lines = [x for x in f.read().rstrip('\n').split('\n') if not x.startswith('terms_theorem:')]
                return '\n'.join(lines + ([f'terms_theorem: {files[fd.name]}'] if fd.name in files else [])) + '\n'

            return ir.ordered(dict(ks), {name: ir.parse_fold(text(fd), fd.path) for name, fd in ks.folds.items()})

        def comment(s, name):
            return s.split(f'Definition {name}_spec : Prop :=', 1)[0].rsplit('(*', 1)[1].rstrip()

        theory = 'proofs/theories/FoldConv.v'
        self.assertEqual(rocq.CONV_TERMS, ('conv_terms_eq', 'conv_terms_count', 'conv_terms_length'))
        for files in ({'conv_1': theory, 'conv_2': theory}, {'conv_2': theory}):
            ks = kernels_with(files)
            self.assertEqual(rules.check_all(ks), [])
            s, audit = rocq.fold_statements(ks), rocq.audit(ks)
            for name in rocq.CONV_TERMS:
                self.assertTrue(comment(s, name).endswith('Status:\n   proved. *)') or
                                comment(s, name).endswith('Status: proved. *)'), comment(s, name))
                self.assertEqual(audit.count(f'\nDefinition {name}_audit : {name}_spec := {name}_correct.\n'
                                             f'Print Assumptions {name}_correct.\n'), 1)
                self.assertLess(audit.index('Definition bv_conv_2_audit'), audit.index(f'Definition {name}_audit'))
            self.assertIn('From Kairn Require Import FoldConv.', audit)
        ks = kernels_with({})
        self.assertEqual(rules.check_all(ks), [])
        s, audit = rocq.fold_statements(ks), rocq.audit(ks)
        for name in rocq.CONV_TERMS:
            self.assertTrue(comment(s, name).endswith('unverified. *)'), comment(s, name))
        self.assertNotIn('conv_terms', audit)
        for files, words in (({'conv_1': theory, 'conv_2': 'proofs/theories/Folds.v'},
                              'the convolutions that name one name the same file'),
                             ({'conv_1': 'theories/FoldConv.v', 'conv_2': 'theories/FoldConv.v'},
                              'the terms_theorem file must be proofs/theories/*.v'),
                             ({'conv_1': theory, 'conv_2': theory, 'dot_2': theory}, 'only a convolution names')):
            errs = [str(e) for e in rules.check_all(kernels_with(files))]
            self.assertTrue(any(words in e for e in errs), (files, errs))

    def test_the_claims(self):
        doc = json.loads(claims.claims(self.ks))
        c = {f['name']: f for f in doc['folds']}['conv_2']
        self.assertEqual(list(c), ['name', 'conv', 'domain', 'arrays', 'writes', 'outputs', 'value', 'requires',
                                   'ensures', 'orders', 'coefficients', 'check', 'min_precision', 'status', 'theorem',
                                   'source'])
        self.assertEqual(c['ensures'], [{'kind': 'coefficients', 'of': 'z', 'fold': 'dot_2'},
                                        {'kind': 'finite_or_nan', 'of': 'z', 'flag': 'finite'}])
        self.assertEqual(c['orders'], ['sequential'])

    def test_the_cxx_and_the_counts(self):
        text = cpp.scalar(self.ks)
        self.assertIn('inline void conv_2_seq(const double* x0_in, const double* x1_in, std::size_t n_x, const double* '
                      'y0_in, const double* y1_in, std::size_t n_y, double* z0_out, double* z1_out, bool& finite_out) '
                      'noexcept {', text)
        self.assertIn('            const double y1 = y1_in[j_ - i_];', text)
        from kairn_gen import simd
        self.assertNotIn('conv_1', simd.header(simd.AVX2, self.ks) + simd.header(simd.NEON, self.ks))
        doc = json.loads(objcode.objcode(self.ks))
        names = doc['fold_parts']
        parts = [dict(zip(names, p)) for p in doc['folds']['conv_2']['seq']['double']]
        self.assertEqual(list(doc['folds']['conv_2']), ['seq'])
        self.assertEqual([(p['part'], p['least'], p['fma']) for p in parts], [('step', 1, 5), ('check', 2, 0)])


if __name__ == '__main__':
    unittest.main()
