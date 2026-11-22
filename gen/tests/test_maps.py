"""The maps (docs/developer/design/milestone2.md, "Folds, the extension of the IR": a fold with
writes; docs/developer/architecture.md, "Maps").

- Their rules: each way of getting a map wrong is refused (rules.map_rules).
- The interpreter: every written element is the step on its element and the scalars; the lane
  order writes the same elements and gives the same mask as the sequential one, for every number
  of lanes; an element that is not finite gives the canonical NaN and a false mask, the others are
  kept; the line protocol of written arrays.
- The compiled C++: F_seq and F_lanes of every build of the runner, and F_packed of every packed
  build, bit for bit against the interpreter, on lengths 0, 1, W - 1, W, W + 1, 2 W and random ones,
  non-finite elements among them.
- Aliasing: each map in place (the array written is one of the arrays read, z = x or z = y) writes
  what it writes into an array of its own, in each of its three forms.
- Rule R3 on the arrays the program supplies: a program that stores a product into the array y of
  add, sub or axpy gets from the _entry maps the result on the rounded product, whatever the
  compiler fuses; the maps of stored arrays, which do not guard, are the control.
- The model and the statement of a map in Rocq, its C++ text and the counts of its loops.
The claims of the steps themselves, entry by entry, are those of their kernels: test_statements
checks them in exact arithmetic like every kernel's.
"""
import math
import os
import random
import subprocess
import unittest
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import common
import test_cxx as cxx
import test_folds as folds_tests
import test_simd as simd_tests
from kairn_gen import cpp, interp, ir, objcode, rocq, rules

MAPS = sorted(folds_tests.MAPS)

# A map to start from: axpy_1.
BASE = '''
fold:          tm
arrays:        supplied x, stored y
scalars:       supplied a
state:         mask finite
step:          z = axpy_step_1(a, x, y)
combine:       finite = and(finite, finite)
orders:        sequential, lanes
writes:        z
check:         fold_finish_1
finish:        none
value:         a*x+y
ensures:       entries z
ensures:       finite_or_nan z flag=finite
min_precision: 1
status:        unverified
domain:        extended
'''


def refusals(text):
    ks = dict(common.kernels())
    fd = ir.parse_fold(text, 'tm.fold')
    return [str(e) for e in rules.fold_rules(fd, ir.ordered(ks, {fd.name: fd}))]


class Rules(unittest.TestCase):
    def test_the_maps_are_accepted(self):
        ks = common.kernels()
        self.assertEqual({n for n, fd in ks.folds.items() if fd.is_map}, set(MAPS))
        for name in MAPS:
            self.assertEqual(rules.fold_rules(ks.folds[name], ks), [], name)
        self.assertEqual(refusals(BASE), [])

    def refused(self, text, words):
        errors = refusals(text)
        self.assertTrue(any(words in e for e in errors), (words, errors))

    def test_the_parts(self):
        self.refused(BASE.replace('mask finite', 'finite'), 'the state of a map is one mask')
        self.refused(BASE.replace('step:          z = axpy_step_1(a, x, y)', 'step:          z = axpy_step_1(a, x, x)'),
                     'its arguments are every scalar and every array once')
        self.refused(BASE.replace('step:          z = axpy_step_1(a, x, y)',
                                  'step:          finite = axpy_step_1(a, x, y)'), 'a map\'s step takes no state')
        self.refused(BASE.replace('and(finite, finite)', 'or(finite, finite)'), 'combined by and')
        self.refused(BASE.replace('check:         fold_finish_1\n', ''), 'check: (none) is not a kernel')
        self.refused(BASE.replace('fold_finish_1', 'fold_finish_2'), 'check: fold_finish_2 takes an element of z')
        self.refused(BASE.replace('writes:        z', 'writes:        z, w'), 'a map writes one array')
        self.refused(BASE.replace('finish:        none', 'finish:        (r, flag) = fold_finish_1(finite)'),
                     'finish: none')
        self.refused(BASE.replace('axpy_step_1', 'add_2_2'), 'add_2_2 takes 2 groups, not 3')

    def test_r3(self):
        # axpy_step_1 adds y unguarded: y supplied by the program is refused; the entry step guards it.
        self.refused(BASE.replace('stored y', 'supplied y'),
                     'y is supplied by the program, and the step axpy_step_1 does not take y as a value')
        self.assertEqual(refusals(BASE.replace('stored y', 'supplied y').replace('axpy_step_1',
                                                                                 'axpy_entry_step_1')), [])
        # add_1_1 is no entry kernel: its operands cannot come from the program.
        add = BASE.replace('supplied x, stored y', 'supplied x, supplied y').replace('scalars:       supplied a\n', '')
        add = add.replace('z = axpy_step_1(a, x, y)', 'z = add_1_1(x, y)').replace('a*x+y', 'x+y')
        self.refused(add, 'x is supplied by the program, and the step add_1_1 does not take a')

    def test_claims(self):
        self.refused(BASE.replace('value:         a*x+y', 'value:         a*y+x'), 'not the value of the step')
        self.refused(BASE.replace('ensures:       entries z\n', ''), 'a map claims, of the array it writes, entries')
        self.refused(BASE.replace('flag=finite', 'flag=z'), 'the flag of a map is its state')
        self.refused(BASE.replace('domain:        extended\n', ''), 'a map is of the extended domain')
        self.refused(BASE.replace('min_precision: 1', 'min_precision: 1\nrequires:      canonical x'),
                     'canonical ARRAY or SCALAR of more than one limb')
        self.refused(BASE.replace('status:        unverified', 'status:        proved'),
                     'not marked unverified and names no theorem')
        # (axpy_step_2 is the step of axpy_2, on a stored scalar and stored arrays: rule R3, the
        # factors of a fused operation.)
        two = BASE.replace('supplied x, stored y', 'stored x = x0 x1, stored y = y0 y1').replace(
            'supplied a', 'stored a = a0 a1').replace('axpy_step_1', 'axpy_step_2').replace(
            'writes:        z', 'writes:        z = z0 z1').replace('fold_finish_1', 'fold_finish_2')
        self.refused(two.replace('min_precision: 1', 'min_precision: 4'),
                     'the step axpy_step_2 requires normalized a, so the map requires canonical a')
        two = two.replace('min_precision: 1', 'min_precision: 1\nrequires:      canonical a\n'
                          'requires:      canonical x\nrequires:      canonical y')
        self.assertEqual(refusals(two.replace('min_precision: 1', 'min_precision: 4')), [])
        self.refused(two.replace('min_precision: 1', 'min_precision: 3'),
                     'the claims of axpy_step_2 hold from precision 4 on')


# ---------------------------------------------------------------------------------------------
# The interpreter.

def scalars_for(rng, fd, fmt):
    """The scalars' limbs: a normalized pair for two limbs, a power of two where the map requires
    one."""
    pow2 = {r[1] for r in fd.requires if r[0] == 'power_of_two'}
    out = []
    for g in fd.scalars:
        if g.name in pow2:
            out.append(2.0 ** rng.randrange(-8, 9))
            continue
        x0 = common.near(rng, fmt, rng.choice((-3, 0, 3)), 6)
        out += [x0] + [common.tail(rng, fmt, x0) for _ in g.limbs[1:]]
    return out


def request(fd, fmt, order, lanes, scalars, elements):
    o = 'seq' if order == 'sequential' else f'lanes:{lanes}'
    limbs = list(scalars) + [x for arr in folds_tests.arrays_of(elements, fd) for x in arr]
    return f'{fd.name} {fmt} {o} {len(elements)}' + ''.join(' ' + common.token(x) for x in limbs)


_machines = {}


def _run_map(job):
    name, fmt, order, lanes, scalars, arrays = job
    if 'm' not in _machines:
        _machines['m'] = interp.Machine(common.kernels())
    f = interp.parse_format(fmt)
    out = _machines['m'].run_fold(name, f, order, lanes, [[common.to_value(x) for x in a] for a in arrays],
                                  [common.to_value(x) for x in scalars])
    return [common.to_float(v) for a in out[:-1] for v in a] + [out[-1]]


class Interp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()
        cls.m = interp.Machine(cls.ks)

    def run_map(self, name, fmt, order, lanes, scalars, els):
        fd = self.ks.folds[name]
        f = interp.parse_format(fmt)
        return self.m.run_fold(name, f, order, lanes,
                               [[common.to_value(x) for x in a] for a in folds_tests.arrays_of(els, fd)],
                               [common.to_value(x) for x in scalars])

    def test_each_element_is_the_step_and_every_order_the_same(self):
        rng = random.Random('maps')
        for name in MAPS:
            fd = self.ks.folds[name]
            for fmt in ('binary64', 'binary32'):
                for n in (0, 1, 3, 7, 12):
                    sc = scalars_for(rng, fd, fmt)
                    els = folds_tests.elements_for(rng, fd, fmt, n)
                    seq = self.run_map(name, fmt, 'sequential', 0, sc, els)
                    f = interp.parse_format(fmt)
                    given = [common.to_value(x) for x in sc]
                    for i, e in enumerate(els):
                        groups, at = {}, 0
                        for g in fd.arrays:
                            groups[g.name] = [common.to_value(x) for x in e[at:at + len(g.limbs)]]
                            at += len(g.limbs)
                        at = 0
                        for g in fd.scalars:
                            groups[g.name] = given[at:at + len(g.limbs)]
                            at += len(g.limbs)
                        want = self.m.run(fd.step[0], f, [v for a in fd.step[1] for v in groups[a]])
                        if seq[-1]:
                            self.assertEqual([a[i] for a in seq[:-1]], want, (name, fmt, n, i))
                    for w in (0, 1, 2, 3, 4, 5, 8, 13):
                        self.assertEqual(self.run_map(name, fmt, 'lanes', w, sc, els), seq, (name, fmt, n, w))

    def test_empty_and_non_finite(self):
        f = 'binary64'
        for name in MAPS:
            fd = self.ks.folds[name]
            width = len(fd.write_limbs())
            sc = [2.0 if r == 'c' else 1.5 for r in fd.scalar_limbs()]
            sc = [x if i == 0 or len(fd.scalars[0].limbs) == 1 else 0.0 for i, x in enumerate(sc)]
            self.assertEqual(self.run_map(name, f, 'sequential', 0, sc, []), [[]] * width + [True])
            one = []
            for g in fd.arrays:
                one += [1.0] + [0.0] * (len(g.limbs) - 1)
            bad = list(one)
            bad[0] = math.inf
            out = self.run_map(name, f, 'sequential', 0, sc, [one, bad, one])
            self.assertIs(out[-1], False, name)
            self.assertTrue(all(a[1] == interp.NaN for a in out[:-1]), (name, out))
            # The elements that are finite are kept.
            self.assertTrue(all(a[0][0] == interp.NUM and a[2][0] == interp.NUM for a in out[:-1]), (name, out))

    def test_the_line_protocol(self):
        formats = {}
        line = 'axpy_1 fp:5:-12:6 lanes:2 3 0x1p+1 0x1p+0 0x1p+1 0x1p+2 0x1p-1 0x1p-1 0x1p-1 #t'
        self.assertEqual(interp.complete(self.m, line, formats), line + ' -> 0x1.4p+1 0x1.2p+2 0x1.1p+3 1')
        self.assertEqual(interp.complete(self.m, 'add_2 binary64 seq 0', formats), 'add_2 binary64 seq 0 -> 1')
        with self.assertRaises(interp.InterpError) as e:
            interp.complete(self.m, 'axpy_1 binary64 seq 1 0x1p+0 0x1p+0', formats)
        self.assertIn('takes 3 limbs (1 of its scalars, 2 arrays of 1)', str(e.exception))


# ---------------------------------------------------------------------------------------------
# The compiled C++.

def map_corpus(fmt, orders, seed):
    """[(map, format, order, lanes, scalars, elements, request line)] for every map."""
    ks = common.kernels()
    rng = random.Random(f'{seed}:{fmt}')
    out = []
    for name in MAPS:
        fd = ks.folds[name]
        for n in folds_tests.lengths(rng):
            for special in (0.0, 0.0, 0.02 if n else 0.0):
                sc = scalars_for(rng, fd, fmt)
                els = folds_tests.elements_for(rng, fd, fmt, n, special)
                for order, w in orders:
                    out.append((name, fmt, order, w, sc, els, request(fd, fmt, order, w, sc, els)))
    return out


def expected(cases):
    ks = common.kernels()
    jobs = [(c[0], c[1], c[2], c[3], c[4], folds_tests.arrays_of(c[5], ks.folds[c[0]])) for c in cases]
    with ProcessPoolExecutor(max_workers=common.JOBS) as ex:
        return list(ex.map(_run_map, jobs, chunksize=4))


class Cxx(unittest.TestCase):
    """F_seq and F_lanes of every build of the runner, bit for bit against the interpreter."""

    @classmethod
    def setUpClass(cls):
        if not cxx.COMPILERS:
            raise unittest.SkipTest('no C++ compiler (set KAIRN_GEN_CXX)')
        cls.builds = cxx.shared_builds()
        orders = [('sequential', 0)] + [('lanes', w) for w in (0, 1, 2, 3, 4, 8)]
        cls.cases = map_corpus('binary64', orders, 'cxx') + map_corpus('binary32', orders, 'cxx')
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

    def test_the_corpus(self):
        ns = {len(c[5]) for c in self.cases}
        self.assertTrue({0, 1, 2, 3, 4, 5, 7, 8, 9, 16} <= ns)
        self.assertTrue(any(not math.isfinite(x) for c in self.cases for e in c[5] for x in e))
        self.assertTrue(any(w[-1] is False for w in self.want) and any(w[-1] is True for w in self.want))

    def test_runner_protocol(self):
        code, out, err = self.builds.run(0, 'add_1 binary64 seq 2 0x1p+0 0x1p+1 0x1p+2 inf\n')
        self.assertEqual(code, 0, err)
        self.assertEqual(out, 'add_1 binary64 seq 2 0x1p+0 0x1p+1 0x1p+2 inf -> 0x1.4p+2 nan 0\n')
        code, out, err = self.builds.run(0, '# fine\naxpy_1 binary64 seq 1 0x1p+0 0x1p+0\n')
        self.assertEqual(code, 2)
        self.assertIn('takes 3 limbs', err)


class Packed(unittest.TestCase):
    """F_packed of every packed build: what F_lanes of the scalar build with the same flags prints
    with the lanes of the register, and the interpreter's, bit for bit."""

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
                    cases += map_corpus(fmt, [('lanes', w)], 'packed')
                cls.cases[key] = (cases, expected(cases))

    @staticmethod
    def native(label):
        return {'binary64': 2, 'binary32': 4} if simd_tests.ARM64 and 'x86_64' not in label else \
            {'binary64': 4, 'binary32': 8}

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
# Aliasing: a map in place.

def aliasing_program(ks):
    """For every map and limb type, on fixed pseudo-random elements: F_seq, F_lanes with 3 lanes and
    F_packed (where a packed header is included) into arrays of their own, and in place, with the
    array written each of the arrays read of its shape (z = x, z = y). Prints a line per map, form
    and array overwritten, with 0 when the two wrote the same bytes and gave the same mask."""
    lines = ['#include <cstdio>', '#include <cstring>', '#include <vector>', '#include "kairn/gen/scalar.hpp"',
             '#if defined(__AVX2__) && defined(__FMA__)', '#include "kairn/gen/avx2.hpp"', '#define PACKED 1',
             '#elif defined(__aarch64__)', '#include "kairn/gen/neon.hpp"', '#define PACKED 1', '#else',
             '#define PACKED 0', '#endif',
             'static unsigned long long seed = 7;',
             'template <class T> T draw() {',
             '    seed = seed * 6364136223846793005ull + 1442695040888963407ull;',
             '    return T((long long)((seed >> 20) & 0xfffff) - 0x80000) / T(1 << 12);',
             '}',
             'int main() {',
             '    const std::size_t n = 37;']
    for ctype in ('double', 'float'):
        for name in MAPS:
            fd = ks.folds[name]
            w = len(fd.writes[0].limbs)
            nin = len(fd.array_limbs())
            lines.append('    {')
            lines.append(f'        std::vector<std::vector<{ctype}>> in({nin}, std::vector<{ctype}>(n));')
            # Elements: a leading limb drawn, a second limb small enough to keep the pair normalized.
            at = 0
            for g in fd.arrays:
                lines.append(f'        for (std::size_t i = 0; i < n; ++i) {{ in[{at}][i] = draw<{ctype}>();'
                             + (f' in[{at + 1}][i] = in[{at}][i] * {ctype}(1.0 / (1 << 30)) * {ctype}(1.0 / (1 << 30));'
                                if len(g.limbs) > 1 else '') + ' }')
                at += len(g.limbs)
            sc = ', '.join(['(' + ctype + ')0.75' if i == 0 else '(' + ctype + ')0'
                            for i in range(len(fd.scalar_limbs()))])
            if any(r[0] == 'power_of_two' for r in fd.requires):
                sc = f'({ctype})0.5'
            ins = ', '.join(f'in[{i}].data()' for i in range(nin))
            forms = [('seq', ''), ('lanes', ', 3')]
            for form, lanes in forms + [('packed', '')]:
                guard = form == 'packed'
                if guard:
                    lines.append('#if PACKED')
                lines.append('        {')
                lines.append(f'            std::vector<std::vector<{ctype}>> out({w}, std::vector<{ctype}>(n));')
                outs = ', '.join(f'out[{i}].data()' for i in range(w))
                lines.append('            bool f0 = false;')
                lines.append(f'            kairn::gen::{name}_{form}({ins}, n{lanes}{", " + sc if sc else ""}, {outs}, f0);')
                at = 0
                for g in fd.arrays:
                    if len(g.limbs) == w:
                        lines.append('            {')
                        lines.append(f'                std::vector<std::vector<{ctype}>> io(in);')
                        place = ', '.join(f'io[{i}].data()' for i in range(nin))
                        over = ', '.join(f'io[{at + i}].data()' for i in range(w))
                        lines.append('                bool f1 = true;')
                        lines.append(f'                kairn::gen::{name}_{form}({place}, n{lanes}{", " + sc if sc else ""}, '
                                     f'{over}, f1);')
                        same = ' && '.join(f'std::memcmp(io[{at + i}].data(), out[{i}].data(), n * sizeof({ctype})) == 0'
                                           for i in range(w))
                        lines.append(f'                std::printf("{name} {ctype} {form} {g.name} %d\\n", '
                                     f'({same} && f0 == f1) ? 0 : 1);')
                        lines.append('            }')
                    at += len(g.limbs)
                lines.append('        }')
                if guard:
                    lines.append('#endif')
            lines.append('    }')
    lines += ['    return 0;', '}']
    return '\n'.join(lines) + '\n'


class Aliasing(unittest.TestCase):
    def test_in_place(self):
        if not cxx.COMPILERS:
            self.skipTest('no C++ compiler (set KAIRN_GEN_CXX)')
        ks = common.kernels()
        d = common.scratch('aliasing')
        src = os.path.join(d, 'aliasing.cpp')
        with open(src, 'w') as f:
            f.write(aliasing_program(ks))
        jobs = []
        for c in cxx.COMPILERS:
            for opt in ('-O0', '-O2'):
                exe = os.path.join(d, f'aliasing_{len(jobs)}')
                jobs.append((c, opt, [c, '-std=c++20', opt] + (['-mavx2', '-mfma'] if cxx.X86 else []) +
                             ['-I', cxx.INCLUDE, src, '-o', exe], exe))
        with ThreadPoolExecutor(common.JOBS) as ex:
            built = list(ex.map(cxx.compile_, [j[2] for j in jobs]))
        for (c, opt, _, exe), (status, err) in zip(jobs, built):
            with self.subTest(compiler=c, opt=opt):
                self.assertEqual(status, 0, err)
                out = subprocess.run([exe], capture_output=True, text=True, check=True).stdout.splitlines()
                # Every map has an array of the shape it writes: each form in place at least once.
                self.assertGreaterEqual(len(out), 2 * len(MAPS) * 2)
                self.assertEqual([x for x in out if not x.endswith(' 0')], [])


# ---------------------------------------------------------------------------------------------
# Rule R3: arrays the program fills.

R3_MAPS = (('add_1', 'add_1_entry', 'x+y'), ('sub_1', 'sub_1_entry', 'x-y'), ('axpy_1', 'axpy_1_entry', 'a*x+y'))


def supplied_program(ctype):
    """For each map of R3_MAPS, stored and supplied: element 0 of the result where the program
    writes y[0] = a * b in the same function and x[0] = c (with a = 1 for axpy), against the same
    with the product rounded by a function that is not inlined; c = -RN(a b), so that a product
    fused into the addition shows. Prints, per map, in how many cases the two differ."""
    lines = ['#include <cstdio>', '#include "kairn/gen/scalar.hpp"',
             '#if defined(_MSC_VER) && !defined(__clang__)', '#define NOINLINE __declspec(noinline)', '#else',
             '#define NOINLINE __attribute__((noinline))', '#endif',
             f'NOINLINE {ctype} rounded({ctype} a, {ctype} b) {{ volatile {ctype} p = a * b; return p; }}']
    names = [n for pair in R3_MAPS for n in pair[:2]]
    for stored, entry, value in R3_MAPS:
        for name in (stored, entry):
            sign = '-' if value == 'x-y' else ''
            for form, product in (('inline', 'a * b'), ('ref', 'rounded(a, b)')):
                lines += [f'NOINLINE {ctype} {name}_{form}({ctype} a, {ctype} b, {ctype} c) {{',
                          f'    {ctype} x[1], y[1], z[1];',
                          f'    x[0] = {sign}c;' if value == 'x-y' else '    x[0] = c;',
                          f'    y[0] = {product};',
                          '    bool f = false;',
                          f'    kairn::gen::{name}_seq(x, y, 1, ' + (f'({ctype})1, ' if value == 'a*x+y' else '')
                          + 'z, f);',
                          '    return z[0];', '}']
    utype = 'unsigned long long' if ctype == 'double' else 'unsigned'
    p = 53 if ctype == 'double' else 24
    lines += ['int main() {', f'    {ctype} a = 1, b = 1, c = 0;', '    unsigned long long seed = 12345;']
    lines += [f'    long differ_{n} = 0;' for n in names]
    lines += ['    for (int i = 0; i < 20000; ++i) {',
              '        seed = seed * 6364136223846793005ull + 1442695040888963407ull;',
              f'        const {utype} m = ({utype})((seed >> 11) & ((1ull << {p - 1}) - 1)) | (({utype})1 << {p - 1});',
              f'        a = ({ctype})m / ({ctype})(1ull << {p - 1});',
              f'        b = ({ctype})1 + ({ctype})((seed >> 7) & 1023) / ({ctype})(1 << 10);',
              '        c = -rounded(a, b);']
    lines += [f'        differ_{n} += {n}_inline(a, b, c) != {n}_ref(a, b, c);' for n in names]
    lines.append('    }')
    lines += [f'    std::printf("{n} %ld\\n", differ_{n});' for n in names]
    lines += ['    return 0;', '}']
    return '\n'.join(lines) + '\n'


class Supplied(unittest.TestCase):
    """Rule R3 on the arrays the program supplies: with every compiler and contraction setting at
    -O2 the _entry maps compute on the rounded product in every case; the maps of stored arrays,
    which do not guard y, are the control."""

    def test_a_product_stored_into_a_supplied_array(self):
        if not cxx.COMPILERS:
            self.skipTest('no C++ compiler (set KAIRN_GEN_CXX)')
        d = common.scratch('supplied_maps')
        jobs = []
        for ctype in ('double', 'float'):
            src = os.path.join(d, f'supplied_{ctype}.cpp')
            with open(src, 'w') as f:
                f.write(supplied_program(ctype))
            for c in cxx.COMPILERS:
                for contract in ('off', 'on', 'fast'):
                    exe = os.path.join(d, f'supplied_{ctype}_{len(jobs)}')
                    jobs.append((c, ctype, contract, [c, '-std=c++20', '-O2', f'-ffp-contract={contract}'] +
                                 (['-mfma'] if cxx.X86 else []) + ['-I', cxx.INCLUDE, src, '-o', exe], exe))
        with ThreadPoolExecutor(common.JOBS) as ex:
            built = list(ex.map(cxx.compile_, [j[3] for j in jobs]))
        controls = {}
        for (c, ctype, contract, _, exe), (status, err) in zip(jobs, built):
            with self.subTest(compiler=c, type=ctype, contract=contract):
                self.assertEqual(status, 0, err)
                out = subprocess.run([exe], capture_output=True, text=True, check=True).stdout
                differ = dict((line.split()[0], int(line.split()[1])) for line in out.splitlines())
                for _, entry, _ in R3_MAPS:
                    self.assertEqual(differ[entry], 0, (entry, out))
                controls[(c, ctype, contract)] = sum(differ[s] for s, _, _ in R3_MAPS)
        fused = sorted(k for k, v in controls.items() if v)
        print(f'\n  maps of stored arrays (no guard) fused by: {fused or "none"}', flush=True)
        if any('fast' in k for k in controls) and any(('clang' in c or c == 'c++' or 'g++' in c) for c, _, _ in controls):
            self.assertTrue(fused, controls)


# ---------------------------------------------------------------------------------------------
# The printers.

class Printers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()

    def test_the_model(self):
        m = rocq.fold_model(self.ks)
        self.assertIn('Definition axpy_2_step (a : R * R) (xy : (R * R) * (R * R)) : R * R :=\n'
                      '  axpy_step_2 emin prec choice (fst a) (snd a) (fst (fst xy)) (snd (fst xy)) (fst (snd xy)) '
                      '(snd (snd xy)).', m)
        self.assertIn('Definition axpy_2_map (a : R * R) (xys : list ((R * R) * (R * R))) : list (R * R) :=\n'
                      '  map (axpy_2_step a) xys.', m)
        self.assertIn('Definition add_1_map (xys : list (R * R)) : list R :=\n  map (add_1_step) xys.', m)

    def test_the_statements(self):
        s = rocq.fold_statements(self.ks)
        self.assertIn('Definition axpy_2_spec : Prop :=\n'
                      '  forall emin prec : Z, (4 <= prec)%Z ->\n'
                      '  forall (a0 a1 : R) (xys : list ((R * R) * (R * R))),\n'
                      '  normalized_2 emin prec a0 a1 ->\n'
                      '  Forall (fun xy => normalized_2 emin prec (fst (fst xy)) (snd (fst xy)) /\\ '
                      'normalized_2 emin prec (fst (snd xy)) (snd (snd xy))) xys ->\n'
                      '  Forall2 (fun xy w_ =>\n'
                      "    let '((x0, x1), (y0, y1)) := xy in\n"
                      "    let '(z0, z1) := w_ in\n"
                      '    normalized_2 emin prec z0 z1 /\\\n', s)
        self.assertIn('    xys (axpy_2_map emin prec tie_even (a0, a1) xys).', s)
        self.assertIn('  (exists n : Z, c = bpow radix2 n) ->\n', s)
        for name in MAPS:
            self.assertIn(f'Definition {name}_spec : Prop :=', s)

    def test_the_cxx(self):
        text = cpp.scalar(self.ks)
        self.assertIn('inline void axpy_2_seq(const double* x0_in, const double* x1_in, const double* y0_in, '
                      'const double* y1_in, std::size_t n, double a0, double a1, double* z0_out, double* z1_out, '
                      'bool& finite_out) noexcept {', text)
        self.assertIn('inline void add_1_lanes(const float* x_in, const float* y_in, std::size_t n, std::size_t lanes, '
                      'float* z_out, bool& finite_out) noexcept {', text)
        self.assertIn('A written array is exactly one of the', text)
        self.assertIn('    if (!finite) {\n        for (std::size_t i_ = 0; i_ < n; ++i_) {', text)
        from kairn_gen import simd
        avx = simd.header(simd.AVX2, self.ks)
        self.assertIn('inline void axpy_2_packed(const double* x0_in', avx)
        self.assertIn('    bool finite = _mm256_movemask_pd(finite_lane_) == 0xF;', avx)
        neon = simd.header(simd.NEON, self.ks)
        self.assertIn('    bool finite = vminvq_u32(finite_lane_) != 0U;', neon)

    def test_the_counts_of_the_loops(self):
        import json
        doc = json.loads(objcode.objcode(self.ks))
        names = doc['fold_parts']
        for name in MAPS:
            step = self.ks[self.ks.folds[name].step[0]]
            want = objcode.kernel_counts(step, self.ks)['packed']
            for form, least in (('seq', {'step': 1, 'check': 2}), ('lanes', {'step': 2, 'check': 3}),
                                ('packed', {'packed step': 1, 'packed check': 1, 'step': 1, 'check': 2})):
                for t in objcode.LIMB_TYPES:
                    parts = {p[0]: dict(zip(names, p)) for p in doc['folds'][name][form][t]}
                    self.assertEqual({k: v['least'] for k, v in parts.items()}, least, (name, form))
                    for part in ('step', 'packed step'):
                        if part in parts:
                            self.assertEqual(parts[part]['fma'], want[t]['fma'], (name, form, t))
                    self.assertEqual(parts['check']['fma'], 0)
        axpy2 = dict(zip(names, doc['folds']['axpy_2']['seq']['double'][0]))
        self.assertEqual(axpy2['fma'], 5)


if __name__ == '__main__':
    unittest.main()
