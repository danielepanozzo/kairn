"""The C++ of the round-up interval (docs/developer/design/upward.md, "The pair form", "The printers",
"Barriers", "The interpreter and the emulated formats", "Tests and CI"): include/kairn/gen/upward.hpp
compiled in every form, bit for bit the interpreter's, and the kernels of the emulated limb type
(tests/emulated/gen/upward.hpp) the same bytes as the interpreter on every pair of canonical states of
small formats. The kernels it tests require the rounding mode upward set by kairn::upward::Scope and
the options of docs/concepts/upward.md (GCC and Clang -frounding-math, MSVC /fp:strict); the runner,
gen/tests/upward_runner.cpp, holds a scope around each evaluation.

- The compiled runner, built with each compiler of $KAIRN_GEN_CXX (default: c++ and g++-16, those that
  exist) at -O0 and -O2, with -ffp-contract=off, on and fast, with -frounding-math (the option of the
  CMake target kairn::upward), a checked build (KAIRN_CHECKS 1), in the form the target chooses (one register: SSE2 on x86-64, NEON on
  arm64) and in the two-number form forced (KAIRN_UPWARD_FORM_NUMBERS), on x86-64 with and without
  -mavx2 (the array form AVX2, or the loop); and once at -O2 without -frounding-math with Clang, a release
  build (the barriers alone: the design page, "The full tier"). Every build runs each request one by one and,
  with --arrays, the six kernels that have an array form through it, in chunks of every length of a
  remainder, in place and not. Its lines must be those of the interpreter with the build's form of
  max_nl (--max nm for NEON, sel otherwise), byte for byte: on random cases of every stratum (below)
  and on the special operands (every pair of the special states, every special number).
- The emulated runner (the same file with -DKAIRN_UPWARD_RUNNER_EMULATED), on every canonical state
  (and every value of a number) of the quick formats of test_upward.py, in both forms of max_nl for
  the kernels that compute one: the interpreter's bytes.
- The printers: the PIN on the first input exactly in the kernels that round, a barrier on every
  register and number given and returned, the operations of each pair line once in the register
  form, and the emulated listing the two-number listing of double with the type's operations.
"""
import itertools
import os
import platform
import random
import re
import shutil
import subprocess
import unittest
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import common
from kairn_gen import interp, ir, upward, upward_cpp

import test_upward

ENV = os.environ.get('KAIRN_GEN_CXX')
COMPILERS = ENV.split() if ENV is not None else [c for c in ('c++', 'g++-16') if shutil.which(c)]
X86 = platform.machine().lower() in ('x86_64', 'amd64')
BASE = ['-std=c++20', '-Wall', '-Wextra', '-Wpedantic', '-Wstrict-aliasing', '-Wshadow', '-Werror'] + (['-mfma'] if X86 else [])
RUNNER = os.path.join(common.TESTS, 'upward_runner.cpp')
INCLUDE = os.path.join(common.ROOT, 'include')
EMULATED_NUMBER = os.path.join(common.ROOT, 'tests', 'emulated', 'number.cpp')
N = common.size(400, 20000)          # random requests per kernel and format
NAMES = test_upward.NAMES
NUM, INF_, NAN_ = interp.NUM, interp.INF, interp.NAN
NaN = interp.NaN
INF, NINF = (INF_, False), (INF_, True)
PZ, NZ = (NUM, False, 0, 0), (NUM, True, 0, 0)


def family():
    return common.kernels().upward


# ---------------------------------------------------------------------------------------------
# The requests: random cases of every stratum, and the special operands.

class Values:
    """Numbers of a format, as the interpreter's values."""

    def __init__(self, f, rng):
        self.f, self.rng = f, rng
        self.omega = interp.largest(f, False)
        self.eta = (NUM, False, 1, f.qmin)

    def num(self, q, neg=None):
        f, rng = self.f, self.rng
        neg = rng.random() < 0.5 if neg is None else neg
        if q <= f.qmin:
            return interp.canon(neg, rng.randrange(0, 1 << f.p) if f.p > 0 else 0, f.qmin)
        return interp.canon(neg, rng.randrange(1 << (f.p - 1), 1 << f.p), q)

    def moderate(self, neg=None):
        f = self.f
        return self.num(max(f.qmin + 1, min(f.qmax, self.rng.randint(-12, 12) - f.p + 1)), neg)

    def wide(self, neg=None):
        return self.num(self.rng.randint(self.f.qmin, self.f.qmax), neg)

    def subnormal(self, neg=None):
        neg = self.rng.random() < 0.5 if neg is None else neg
        return interp.canon(neg, self.rng.randrange(1, 1 << max(self.f.p - 1, 1)), self.f.qmin)

    def near_omega(self, neg=None):
        v = self.rng.choice([self.omega, interp.pred(self.f, self.omega),
                             interp.pred(self.f, interp.pred(self.f, self.omega))])
        neg = self.rng.random() < 0.5 if neg is None else neg
        return interp.neg(v) if neg else v

    def tiny(self, neg=None):
        """A few eta from zero."""
        neg = self.rng.random() < 0.5 if neg is None else neg
        return interp.canon(neg, self.rng.randint(1, 4), self.f.qmin)

    def zero(self):
        return self.rng.choice([PZ, NZ])

    def special_number(self):
        return self.rng.choice([PZ, NZ, INF, NINF, NaN, self.omega, interp.neg(self.omega), self.eta,
                                interp.neg(self.eta), (NUM, False, 1, 0), (NUM, True, 1, 0)])


def state(lo, hi):
    """The stored pair (u, n) = (hi, -lo) of the interval [lo, hi]."""
    return (hi, interp.neg(lo))


def ordered(a, b):
    return (a, b) if interp.le(a, b) else (b, a)


STRATA = ('uniform', 'wide', 'empty', 'whole', 'halfline', 'point', 'zerobound', 'omega', 'subnormal',
          'crossnear')
MAKE_STRATA = ('uniform', 'wide', 'reversed', 'nanbound', 'infinities', 'point', 'zerobound', 'omega',
               'subnormal')


def random_state(V, stratum):
    """A canonical state of the stratum."""
    r = V.rng
    if stratum == 'empty':
        return (NaN, NaN)
    if stratum == 'whole':
        return (INF, INF)
    if stratum == 'halfline':
        a = V.moderate()
        return state(a, INF) if r.random() < 0.5 else state(NINF, a)
    if stratum == 'point':
        a = r.choice([V.moderate(), V.zero(), V.wide()])
        if a[0] == NUM and a[2] == 0:
            return (V.zero(), V.zero())
        return state(a, a)
    if stratum == 'zerobound':
        z = V.zero()
        other = r.choice([V.moderate(neg=False), INF, V.wide(neg=False)])
        if r.random() < 0.5:
            return state(z, other)
        return state(interp.neg(other), z)
    if stratum == 'omega':
        a, b = V.near_omega(neg=True), r.choice([V.near_omega(neg=False), INF, V.moderate()])
        return state(*ordered(a, b)) if r.random() < 0.7 else state(r.choice([NINF, V.moderate()]), V.near_omega(False))
    if stratum == 'subnormal':
        return state(*ordered(V.subnormal(), r.choice([V.subnormal(), V.moderate()])))
    if stratum == 'crossnear':
        return state(V.tiny(neg=True), V.tiny(neg=False))
    if stratum == 'wide':
        return state(*ordered(V.wide(), V.wide()))
    return state(*ordered(V.moderate(), V.moderate()))


def random_default(V, stratum):
    """A canonical default interval of one limb (xl, xu) for upward_from_interval_1."""
    if stratum == 'empty':
        return (INF, NINF)
    if stratum == 'whole':
        return (NINF, INF)
    u, n = random_state(V, stratum)
    return (interp.neg(n), u)


def random_make(V, stratum):
    """Two values for upward_make_1: any, NaN and the infinities included."""
    r = V.rng
    if stratum == 'reversed':
        a, b = ordered(V.moderate(), V.moderate())
        return (b, a) if a != b else (V.omega, a)
    if stratum == 'nanbound':
        a = r.choice([V.moderate(), INF, NINF, NaN])
        return (NaN, a) if r.random() < 0.5 else (a, NaN)
    if stratum == 'infinities':
        return (r.choice([INF, NINF, V.moderate()]), r.choice([INF, NINF, V.moderate()]))
    if stratum == 'point':
        a = V.moderate()
        return (a, a)
    if stratum == 'zerobound':
        return (V.zero(), r.choice([V.zero(), V.moderate()]))
    if stratum == 'omega':
        return (V.near_omega(), V.near_omega())
    if stratum == 'subnormal':
        return (V.subnormal(), V.subnormal())
    if stratum == 'wide':
        return (V.wide(), V.wide())
    return ordered(V.moderate(), V.moderate())


def random_number(V, x):
    """A number t: any value, the special ones, and the bounds of the state x and their neighbors."""
    r = V.rng
    roll = r.random()
    if roll < 0.25:
        return V.special_number()
    if roll < 0.45 and x[0][0] == NUM:
        b = r.choice([x[0], interp.neg(x[1])]) if x[1][0] == NUM else x[0]
        return r.choice([b, interp.succ(V.f, b), interp.pred(V.f, b)])
    return r.choice([V.moderate(), V.wide(), V.subnormal(), V.tiny()])


def inputs_of(k, V, stratum):
    """The input values of one random case of k, in the kernel's order."""
    r = V.rng
    if k.name == 'upward_make_1':
        return list(random_make(V, stratum))
    if any(req[0] == 'interval' for req in k.requires):
        return list(random_default(V, stratum))
    given, first = {}, None
    for name, lanes in k.pair_inputs.items():
        s = random_state(V, stratum if first is None or r.random() < 0.5 else r.choice(STRATA))
        given.update(zip(lanes, s))
        first = first or s
    for v in k.input_limbs:
        if v not in given:
            given[v] = random_number(V, first)
    return [given[v] for v in k.input_limbs]


def special_states(f):
    """The special states: the empty set, the whole line, the zeros of either sign, half-lines from
    zero and from one, a point, the widest bounded interval and the narrowest around zero."""
    omega = interp.largest(f, False)
    eta = (NUM, False, 1, f.qmin)
    one = (NUM, False, 1, 0)
    states = [(NaN, NaN), (INF, INF), (PZ, NZ), (PZ, PZ), (NZ, NZ), (NZ, PZ), (one, interp.neg(one)),
              (INF, interp.neg(one)), (interp.neg(one), INF), (INF, PZ), (INF, NZ), (PZ, INF), (omega, omega),
              (eta, eta), (one, PZ), ((NUM, False, 3, -1), interp.neg((NUM, False, 1, -1)))]
    return [s for s in states if test_upward.canonical(*s)]


def special_numbers(f):
    omega = interp.largest(f, False)
    eta = (NUM, False, 1, f.qmin)
    return [PZ, NZ, (NUM, False, 1, 0), (NUM, True, 1, 0), INF, NINF, NaN, omega, interp.neg(omega), eta,
            (NUM, False, 1, -1)]


def special_inputs(k, f):
    """Every combination of the special operands of k."""
    if k.name == 'upward_make_1':
        vs = special_numbers(f)
        return [[a, b] for a in vs for b in vs]
    if any(req[0] == 'interval' for req in k.requires):
        return [[interp.neg(n), u] if u[0] != NAN_ else [INF, NINF] for u, n in special_states(f)] + [[NINF, INF]]
    groups = []
    for _ in k.pair_inputs:
        groups.append([list(s) for s in special_states(f)])
    rest = [v for v in k.input_limbs if v not in {x for ls in k.pair_inputs.values() for x in ls}]
    for _ in rest:
        groups.append([[t] for t in special_numbers(f)])
    out = []
    for combo in itertools.product(*groups):
        out.append([v for part in combo for v in part])
    return out


def request(name, fmt, values, tag):
    return ' '.join([name, fmt] + [interp.format_limb(v) for v in values]) + f' #{tag}'


def requests(seed):
    """Every request of the comparison: N random cases per kernel and format, the strata in turn,
    then the special operands."""
    ks = family()
    lines = []
    for fmt in ('binary64', 'binary32'):
        f = interp.parse_format(fmt)
        for name in NAMES:
            k = ks[name]
            V = Values(f, random.Random(f'{seed}:{name}:{fmt}'))
            strata = MAKE_STRATA if name == 'upward_make_1' else STRATA
            for i in range(N):
                s = strata[i % len(strata)]
                lines.append(request(name, fmt, inputs_of(k, V, s), f'{s}:{i}'))
            for i, ins in enumerate(special_inputs(k, f)):
                lines.append(request(name, fmt, ins, f'special:{i}'))
    return lines


def _complete(job):
    form, lines = job
    m = interp.Machine(common.kernels(), max_form=form)
    formats = {}
    return [interp.complete(m, line, formats) for line in lines]


_pool = None


def interpret(lines, form):
    """The interpreter's completions of the lines with max_nl in `form`, in parallel."""
    global _pool
    if _pool is None:
        _pool = ProcessPoolExecutor(max_workers=common.JOBS)
    step = max(1, len(lines) // (4 * common.JOBS) + 1)
    parts = [lines[i:i + step] for i in range(0, len(lines), step)]
    return [x for part in _pool.map(_complete, [(form, p) for p in parts]) for x in part]


# ---------------------------------------------------------------------------------------------
# The builds.

def compile_(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stderr


def is_clang(cxx):
    r = subprocess.run([cxx, '--version'], capture_output=True, text=True)
    return 'clang' in r.stdout.lower()


def configurations(compilers):
    """(label, command without the source) of every build of the comparison."""
    out = []
    forms = [[], ['-DKAIRN_UPWARD_FORM=KAIRN_UPWARD_FORM_NUMBERS']]
    isas = [[], ['-mavx2']] if X86 else [[]]
    for cxx in compilers:
        for level in ('-O0', '-O2'):
            for c in ('off', 'on', 'fast'):
                for form in forms:
                    for isa in (isas if not form else [[]]):
                        flags = [level, f'-ffp-contract={c}', '-frounding-math'] + form + isa
                        out.append((f'{cxx} {" ".join(flags)}', [cxx] + BASE + flags))
        if is_clang(cxx):
            # A release build: a checked build's scope reports a file built without the option.
            flags = ['-O2', '-ffp-contract=fast', '-DNDEBUG']
            out.append((f'{cxx} {" ".join(flags)} (no -frounding-math: the barriers alone)', [cxx] + BASE + flags))
    return out


class Builds:
    """Every configuration, built in parallel."""

    def __init__(self, tag, configs, sources, extra=()):
        self.dir = common.scratch(tag)
        self.configs = configs
        jobs = []
        for i, (_, cmd) in enumerate(configs):
            jobs.append(cmd + ['-I', INCLUDE, '-I', common.TESTS] + list(extra) + list(sources) +
                        ['-o', os.path.join(self.dir, f'runner{i}')])
        with ThreadPoolExecutor(common.JOBS) as ex:
            self.results = list(ex.map(compile_, jobs))
        self.exes = [os.path.join(self.dir, f'runner{i}') for i in range(len(configs))]

    def run(self, i, text, args=()):
        r = subprocess.run([self.exes[i]] + list(args), input=text, capture_output=True, text=True)
        return r.returncode, r.stdout, r.stderr


def differences(want, got, limit=5):
    got_lines = got.split('\n')
    if got_lines and got_lines[-1] == '':
        got_lines.pop()
    out = []
    if len(got_lines) != len(want):
        out.append(f'{len(got_lines)} lines, expected {len(want)}')
    for w, g in zip(want, got_lines):
        if w != g:
            out.append(f'want {w}\n         got  {g}')
            if len(out) >= limit:
                break
    return out


@unittest.skipUnless(COMPILERS, 'no C++ compiler (set KAIRN_GEN_CXX)')
class Compiled(unittest.TestCase):
    """Every form of every kernel, bit for bit the interpreter's."""

    @classmethod
    def setUpClass(cls):
        cls.lines = requests(0)
        cls.want = {form: interpret(cls.lines, form) for form in ('sel', 'nm')}
        cls.builds = Builds('upward-runner', configurations(COMPILERS), [RUNNER])

    def test_the_builds_compile(self):
        failed = [f'{label}:\n{err[-3000:]}' for (label, _), (status, err) in zip(self.builds.configs,
                                                                                 self.builds.results) if status]
        self.assertEqual(failed, [])

    def test_every_form_is_the_interpreters(self):
        text = '\n'.join(self.lines) + '\n'
        failures, seen = [], set()
        for i, (label, _) in enumerate(self.builds.configs):
            if self.builds.results[i][0]:
                continue
            status, out, err = self.builds.run(i, '', ['--describe'])
            self.assertEqual(status, 0, err)
            words = out.split()
            desc = dict(zip(words[0::2], words[1::2]))
            for args in ([], ['--arrays']):
                status, out, err = self.builds.run(i, text, args)
                if status:
                    failures.append(f'{label} {" ".join(args)}: exit {status}: {err[-2000:]}')
                    continue
                seen.add((desc['form'], desc['arrays'] if args else 'none'))
                diff = differences(self.want[desc['max']], out)
                if diff:
                    failures.append(f'{label} {" ".join(args)} (form {desc["form"]}, arrays {desc["arrays"]}, '
                                    f'max {desc["max"]}):\n         ' + '\n         '.join(diff))
        self.assertEqual(failures, [], '\n'.join(failures[:10]))
        # Each form of the target was run: one register and two numbers, and the arrays in a
        # registers' form and as the loop.
        native = 'SSE2' if X86 else 'NEON' if platform.machine().lower() in ('arm64', 'aarch64') else None
        if native:
            self.assertIn((native, 'none'), seen)
            self.assertIn(('NUMBERS', 'none'), seen)
            self.assertIn(('NUMBERS', 'LOOP'), seen)
            self.assertIn((native, 'AVX2' if X86 else 'NEON'), seen)
            if X86:
                self.assertIn(('SSE2', 'LOOP'), seen)

    def test_the_requests_reach_every_stratum(self):
        tags = {line.rsplit('#', 1)[1].split(':')[0] for line in self.lines}
        self.assertEqual(tags, set(STRATA) | set(MAKE_STRATA) | {'special'})
        # Both forms of max_nl answer the same but for the sign of a zero, and they differ somewhere:
        # the comparison tells the forms apart.
        differ = [(a, b) for a, b in zip(self.want['sel'], self.want['nm']) if a != b]
        self.assertTrue(differ)
        for a, b in differ:
            self.assertEqual(a.replace('-0x0p+0', '0x0p+0'), b.replace('-0x0p+0', '0x0p+0'))


# The accesses to memory of the header: pair_load and pair_store, and the array forms, beside
# accesses of the same arrays by the program, in functions that are not inlined, so that an access
# through a pointer of another type (which a compiler that applies the rules of aliasing reorders or
# drops: GCC's _mm_load_sd and _mm_store_sd, an access of a double) shows. Each check prints a line;
# the program fails when one is wrong.
ALIASING = r'''
#include <cstdio>
#include "kairn/upward.hpp"
#include "kairn/gen/upward.hpp"
using namespace kairn::gen::upward;
#if defined(_MSC_VER) && !defined(__clang__)
#define NOINLINE __declspec(noinline)
#else
#define NOINLINE __attribute__((noinline))
#endif

template <class T>
NOINLINE T store_then_read(T* buf, pair<T> v) {
    buf[0] = T(7);
    buf[1] = T(8);
    pair_store(buf, v);
    return buf[0] + 10 * buf[1];
}
template <class T>
NOINLINE T write_then_load(T* buf) {
    buf[0] = T(3);
    buf[1] = T(4);
    const pair<T> v = pair_load(buf);
    buf[0] = T(5);
    return pair_upper(v) + 10 * pair_nlower(v);
}
template <class T>
NOINLINE T neg_in_place(T* u, T* n, std::size_t len) {
    for (std::size_t i = 0; i < len; ++i) {
        u[i] = T(i);
        n[i] = T(100);
    }
    upward_neg_1_arrays(u, n, u, n, len);
    return u[len - 1] + n[len - 1];
}
template <class T>
int check(const char* type) {
    int bad = 0;
    T buf[4] = {T(1), T(2), T(-1), T(-1)};
    const T a = store_then_read<T>(buf, pair_make(T(3), T(4)));
    const T b = write_then_load<T>(buf);
    T u[37], n[37];
    const T c = neg_in_place<T>(u, n, 37);
    if (a != T(43) || buf[2] != T(-1)) bad = 1;
    if (b != T(43)) bad = 1;
    if (c != T(136)) bad = 1;
    std::printf("%s %g %g %g %g\n", type, double(a), double(b), double(c), double(buf[2]));
    return bad;
}
int main() { return check<double>("double") + check<float>("float"); }
'''


@unittest.skipUnless(COMPILERS, 'no C++ compiler (set KAIRN_GEN_CXX)')
class Aliasing(unittest.TestCase):
    def test_the_accesses_to_memory(self):
        # pair_load, pair_store and an array form, with each compiler at -O2 and -O3 (where GCC
        # applies the rules of aliasing), in the target's form and in the two-number form, with
        # -Wstrict-aliasing among the warnings that are errors.
        d = common.scratch('upward-aliasing')
        src = os.path.join(d, 'aliasing.cpp')
        with open(src, 'w') as f:
            f.write(ALIASING)
        jobs = []
        for cxx in COMPILERS:
            for level in ('-O2', '-O3'):
                for form in ([], ['-DKAIRN_UPWARD_FORM=KAIRN_UPWARD_FORM_NUMBERS']):
                    for isa in ([[], ['-mavx2']] if X86 and not form else [[]]):
                        exe = os.path.join(d, f'aliasing{len(jobs)}')
                        jobs.append((f'{cxx} {level} {" ".join(form + isa)}',
                                     [cxx] + BASE + [level, '-frounding-math', '-Wstrict-aliasing'] + form + isa +
                                     ['-I', INCLUDE, src, '-o', exe], exe))
        with ThreadPoolExecutor(common.JOBS) as ex:
            results = list(ex.map(compile_, [cmd for _, cmd, _ in jobs]))
        failures = []
        for (label, _, exe), (status, err) in zip(jobs, results):
            if status:
                failures.append(f'{label}: does not compile:\n{err[-2000:]}')
                continue
            r = subprocess.run([exe], capture_output=True, text=True)
            if r.returncode:
                failures.append(f'{label}: {r.stdout}{r.stderr}')
        self.assertEqual(failures, [], '\n'.join(failures))


# ---------------------------------------------------------------------------------------------
# The emulated limb type.

@unittest.skipUnless(COMPILERS, 'no C++ compiler (set KAIRN_GEN_CXX)')
class Emulated(unittest.TestCase):
    """The kernels of tests/emulated/gen/upward.hpp on every canonical state of the quick formats,
    the interpreter's bytes in both forms of max_nl."""

    @classmethod
    def setUpClass(cls):
        cxx = COMPILERS[0]
        cls.builds = Builds('upward-emulated', [(f'{cxx} -O1', [cxx, '-std=c++20', '-O1', '-Wall', '-Wextra',
                                                                '-Werror'])],
                            [RUNNER, EMULATED_NUMBER], ['-DKAIRN_UPWARD_RUNNER_EMULATED'])

    def test_every_pair_of_states(self):
        self.assertEqual(self.builds.results[0][0], 0, self.builds.results[0][1][-3000:])
        ks = common.kernels()
        failures = []
        for fmt in test_upward.QUICK:
            f = interp.parse_format(fmt)
            for form in ('sel', 'nm'):
                lines = []
                for name in NAMES:
                    k = ks.upward[name]
                    has_max = any(p.op == 'max_nl' for p in ir.prims(k, ks.upward))
                    if form == 'nm' and not has_max:
                        continue
                    groups = test_upward.inputs(k, f)
                    for case in itertools.product(*(g[1] for g in groups)):
                        given = {}
                        for (names, _), vals in zip(groups, case):
                            given.update(zip(names, vals))
                        lines.append(' '.join([name, fmt] + [interp.format_limb(given[v]) for v in k.input_limbs]))
                want = interpret(lines, form)
                status, out, err = self.builds.run(0, '\n'.join(lines) + '\n', ['--max', form])
                self.assertEqual(status, 0, err[-2000:])
                diff = differences(want, out)
                if diff:
                    failures.append(f'{fmt} --max {form}:\n         ' + '\n         '.join(diff))
        self.assertEqual(failures, [], '\n'.join(failures))


# ---------------------------------------------------------------------------------------------
# The printers.

class Printers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = upward_cpp.header(common.kernels())
        cls.emulated = upward_cpp.emulated_header(common.kernels())

    def functions(self, name):
        """The bodies of every function named `name` in the header, in order: SSE2, NEON and the two
        numbers, each for double then float."""
        return [b for _, b in self.signed(name)]

    def signed(self, name):
        """(signature, body) of every function named `name`."""
        return re.findall(rf'\nKAIRN_GEN_FORCEINLINE void {name}(\([^\n]*)\n(.*?)\n\}}', self.text, re.S)

    def test_the_mark(self):
        # The generated files say in their first paragraph that the kernels require the mode upward
        # and the options (the design page, "The marks").
        ks = common.kernels()
        for text in (self.text, self.emulated, upward_cpp.runner_table(ks)):
            first = []
            for line in text.split('\n'):
                if not line.startswith('//') or line.strip() == '//':
                    if first:
                        break
                    continue
                first.append(line[2:].strip())
            self.assertIn(upward.MARK, ' '.join(first))

    def test_the_barriers(self):
        # The pin on the first pair input exactly in the kernels that round; a barrier on every other
        # input and on every output that is a number or a register, in every form.
        for name, k in family().items():
            rounds = any(st.op in ir.ROUNDED_UP for st in k.body)
            functions = self.signed(name)
            self.assertEqual(len(functions), 6, name)       # SSE2, NEON, numbers; double and float
            for signature, body in functions:
                numbers = 'numbers<' in signature
                self.assertEqual('KAIRN_DETAIL_UPWARD_PIN' in body, rounds, name)
                for g in k.outputs:
                    lane = any(g.name in ls for ls in k.pair_outputs.values())
                    if g.kind == ir.LIMB and (numbers or not lane):
                        self.assertIn(f'KAIRN_DETAIL_UPWARD_BARRIER({g.name});', body, name)
                for out in k.pair_outputs:
                    if not numbers:
                        self.assertIn(f'KAIRN_DETAIL_UPWARD_BARRIER({out});', body, name)
                for v in k.input_limbs:
                    if not any(v in ls for ls in k.pair_inputs.values()):
                        self.assertIn(f'KAIRN_DETAIL_UPWARD_BARRIER({v});', body, name)
                for p in k.pair_inputs:
                    if not numbers:
                        how = 'PIN' if rounds and p == next(iter(k.pair_inputs)) else 'BARRIER'
                        self.assertIn(f'KAIRN_DETAIL_UPWARD_{how}({p});', body, name)
        # The negation of y in the product, before its products.
        for body in self.functions('upward_mul_1')[:4]:
            self.assertIn('KAIRN_DETAIL_UPWARD_BARRIER(nyu_nyn);', body)

    def test_one_instruction_per_pair_line(self):
        # In the register form each pair line of add_ru, mul_ru and max_nl is one intrinsic.
        ops = {'add_ru': ('_mm_add_', 'vadd'), 'mul_ru': ('_mm_mul_', 'vmul'), 'max_nl': ('_mm_max_', 'vmaxnm')}
        for name, k in family().items():
            bodies = self.functions(name)[:4]
            for op, (x86, arm) in ops.items():
                n = sum(1 for s0, _ in k.pair_lines() if s0.op == op)
                for i, body in enumerate(bodies):
                    spelled = x86 if i < 2 else arm
                    self.assertEqual(len(re.findall(re.escape(spelled), body)), n, (name, op, i))
        # max_nl in the operand order of the listing: the candidate first.
        self.assertIn('_mm_max_pd(q2u_q2n, m1u_m1n)', self.text)
        self.assertIn('vmaxnmq_f64(q2u_q2n, m1u_m1n)', self.text)
        self.assertNotIn('vmaxq_', self.text)
        self.assertNotIn('vmax_f32', self.text)

    def test_the_emulated_listing_is_the_two_number_listing(self):
        # The emulated kernels are the two-number form for double, the type's name for double, its
        # operations for the sums, products and maxima, and no barrier.
        double = {name: self.functions(name)[4] for name in family()}     # numbers, double
        for name in family():
            emulated = re.findall(rf'\ninline void {name}\([^\n]*\n(.*?)\n\}}', self.emulated, re.S)
            self.assertEqual(len(emulated), 1, name)
            e = emulated[0].replace(upward_cpp.EMULATED, 'double')
            a = r'((?:std::numeric_limits<double>::\w+\(\))|[\w.]+)'
            e = re.sub(rf'add_ru\({a}, {a}\)', r'\1 + \2', e)
            e = re.sub(rf'mul_ru\({a}, {a}\)', r'\1 * \2', e)
            e = re.sub(rf'max_nl\({a}, {a}\)', r'\1 > \2 ? \1 : \2', e)
            e = re.sub(r'unord\((\w+), \1\)', r'\1 != \1', e)
            e = re.sub(rf'unord\({a}, {a}\)', r'(\1 != \1) | (\2 != \2)', e)
            e = e.replace('double()', '0.0')
            d = '\n'.join(line for line in double[name].split('\n') if 'KAIRN_DETAIL_UPWARD' not in line)
            d = re.sub(r'^    (double|bool) ', r'    const \1 ', d, flags=re.M)
            self.assertEqual(e, d, name)


if __name__ == '__main__':
    unittest.main()
