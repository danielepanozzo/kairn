"""The generated C++, compiled with every compiler and flag set at hand, against the interpreter.

For kernels without muladd there is exactly one correct result per request, so every build must
be bit-identical to the interpreter. The compilers are $KAIRN_GEN_CXX (space-separated; empty to
skip), by default those of `c++` and `g++-16` that exist.
"""
import hashlib
import math
import os
import platform
import random
import shutil
import struct
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import common
from kairn_gen import cpp, interp, ir

ENV = os.environ.get('KAIRN_GEN_CXX')
COMPILERS = ENV.split() if ENV is not None else [c for c in ('c++', 'g++-16') if shutil.which(c)]
X86 = platform.machine().lower() in ('x86_64', 'amd64')
BASE = ['-std=c++20', '-Wall', '-Wextra', '-Wpedantic', '-Werror'] + (['-mfma'] if X86 else [])
MATRIX = [[opt, f'-ffp-contract={c}'] + rm
          for opt in ('-O0', '-O2') for c in ('off', 'on', 'fast') for rm in ([], ['-frounding-math'])]
# Each compiler builds the fix-ups of the scalar kernels in both forms, whichever is its own
# (KAIRN_GEN_FIXUP_CALL, prelude.hpp): inline behind the branch, and as a function of its own.
FORMS = [['-O2', '-ffp-contract=fast', f'-DKAIRN_GEN_FIXUP_CALL={c}'] for c in (0, 1)] + \
        [['-O0', '-ffp-contract=off', '-DKAIRN_GEN_FIXUP_CALL=1']]
N = common.size(2000, 150000)       # requests per kernel and format
JOBS = common.JOBS

RUNNER = os.path.join(common.TESTS, 'runner.cpp')
INCLUDE = os.path.join(common.ROOT, 'include')


# Requests with non-finite limbs and their completions, the same from the interpreter and from every
# compiled runner, scalar and packed (test_interp checks the interpreter's by hand).
NON_FINITE_LINES = {
    'make_2 binary64 nan': 'nan nan',
    'make_2 binary32 -inf': '-inf 0x0p+0',
    'make_2 binary64 -0x0p+0': '0x0p+0 0x0p+0',
    'add_2_2_full binary64 inf 0x0p+0 -inf 0x0p+0': 'nan nan',
    'add_2_2_full binary32 0x1.fffffep+127 0x0p+0 0x1.fffffep+127 0x0p+0': 'inf 0x0p+0',
    'sub_2_2_full binary64 -0x1.fffffffffffffp+1023 0x0p+0 0x1.fffffffffffffp+1023 0x0p+0': '-inf 0x0p+0',
    'mul_2_1_full binary64 -0x1p+0 0x0p+0 inf': '-inf 0x0p+0',
    'mul_2_2_full binary32 0x0p+0 0x0p+0 -inf 0x0p+0': 'nan nan',
    'sub_1_2_full binary64 inf nan nan': 'nan nan',
    'ball_make_1 binary32 0x1p+0 -0x1p+0': 'nan nan',
    'ball_make_2 binary64 nan nan 0x1p+0': '0x0p+0 0x0p+0 inf',
    'ball_mul_1_full binary64 0x0p+0 0x0p+0 0x0p+0 inf': '0x0p+0 inf',
    'ball_scale_2_full binary32 0x1p+0 0x0p+0 0x0p+0 nan': '0x0p+0 0x0p+0 inf',
    'to_up_2 binary64 0x1.fffffffffffffp+1023 0x1p+969': 'inf',
    'to_down_2 binary32 -0x1.fffffep+127 -0x1p+102': '-inf',
    'rmul binary64 0x0p+0 inf': 'nan',
    'neg_2 binary64 inf 0x0p+0': '-inf -0x0p+0',
    'le_2_2 binary64 inf 0x0p+0 inf -0x0p+0': '1',
    'lt_2_1 binary32 nan nan 0x1p+0': '0',
}


# The full kernels and the constructors in constant evaluation: (kernel, type, operands), finite
# operands for the full kernels (an exact cancellation among them, where t = 0 and times_inf(t)
# would be a NaN), non-finite ones for the constructors, whose results may be infinite or NaN.
NONFINITE_CE_CASES = [
    ('add_2_2_full', 'double', [1.0, 2.0 ** -60, 2.0, 0.0]),
    ('add_2_2_full', 'double', [1.0, 0.0, -1.0, 0.0]),
    ('add_2_2_full', 'float', [3.0, 2.0 ** -30, -0.5, 2.0 ** -28]),
    ('add_fast_2_2_full', 'double', [1.5, 2.0 ** -55, 0.25, 0.0]),
    ('sub_2_2_full', 'float', [1.0, 2.0 ** -26, 1.0, 0.0]),
    ('add_2_1_full', 'double', [1.0, 2.0 ** -60, 0.75]),
    ('sub_2_1_full', 'double', [1.0, 2.0 ** -60, 1.0]),
    ('sub_1_2_full', 'float', [2.0, 1.0, -2.0 ** -25]),
    # constexpr by the rule of the product (milestone2.md): the scalings by a power of two, of a
    # number and of a ball, on finite operands, exactly and in the underflow range.
    ('mul_pow2_2_full', 'double', [1.5, 2.0 ** -60, 0.5]),
    ('mul_pow2_2_full', 'float', [-0.0, 0.0, 2.0]),
    ('ball_mul_pow2_1_full', 'double', [1.0, 2.0 ** -60, 0.5]),
    ('ball_mul_pow2_1_full', 'float', [3.0, 2.0 ** -140, 2.0 ** -8]),
    ('ball_mul_pow2_2_full', 'float', [1.0, 2.0 ** -30, 2.0 ** -40, 4.0]),
    ('ball_mul_pow2_2_full', 'double', [2.0 ** -1060, 0.0, 0.0, 0.5]),
    ('make_2', 'double', [math.nan]),
    ('make_2', 'float', [-math.inf]),
    ('make_2', 'double', [-0.0]),
    ('make_2_limbs', 'double', [math.inf, -0.0]),
    ('ball_make_1', 'double', [1.0, math.nan]),
    ('ball_make_1', 'float', [math.nan, 1.0]),
    ('ball_make_1', 'double', [-0.0, -0.0]),
    ('ball_make_2', 'double', [1.0, 2.0 ** -60, -1.0]),
    ('ball_make_2', 'float', [math.inf, 0.0, 0.5]),
    ('ball_make_2', 'double', [1.0, 2.0 ** -60, math.inf]),
]


# Kernels of the extended domain with a real-model statement, on NaN and infinite operands, in
# constant evaluation: comparisons are false on a NaN (MSVC's constant evaluator takes < and <=
# with a NaN for true, which is why the C++ writes them > and >=).
NAN_CE_CASES = [
    ('lt_2_2', 'double', [math.nan, math.nan, 1.0, 0.0]),
    ('le_2_2', 'float', [1.0, 0.0, math.nan, math.nan]),
    ('lt_2_1', 'double', [1.0, 0.0, math.nan]),
    ('le_1_2', 'double', [math.nan, 1.0, 0.0]),
    ('eq_2_1', 'float', [math.nan, math.nan, math.nan]),
    ('le_2_1', 'double', [math.inf, 0.0, math.inf]),
    ('to_up_2', 'double', [math.nan, math.nan]),
    ('to_down_2', 'float', [-math.inf, 0.0]),
    ('abs_2', 'double', [math.nan, math.nan]),
    ('abs_upper_2', 'double', [-math.inf, 0.0]),
]


def _ce_literal(x, ctype):
    if x != x:
        return f'std::numeric_limits<{ctype}>::quiet_NaN()'
    if math.isinf(x):
        return f'{"-" if x < 0 else ""}std::numeric_limits<{ctype}>::infinity()'
    return literal(x, ctype)


def nonfinite_ce_source(ks):
    """static_asserts that the full kernels and the constructors in NONFINITE_CE_CASES are constant
    expressions with the values the interpreter computes in constant evaluation: equal values, a
    NaN where it gives a NaN (zeros of either sign are equal)."""
    ce = interp.Machine(ks, consteval=True)
    lines = ['#include <limits>', '#include "kairn/gen/scalar.hpp"', '']
    for name, ctype, case in NONFINITE_CE_CASES + NAN_CE_CASES:
        fmt = interp.parse_format('binary64' if ctype == 'double' else 'binary32')
        got = ce.run(name, fmt, [common.to_value(x) for x in case])
        outs = [common.to_float(v) for v in got]
        masks = [isinstance(v, bool) for v in got]
        decl = ' '.join(f'{"bool" if m else ctype} o{i} = {"false" if m else "0"};' for i, m in enumerate(masks))
        args = ', '.join([_ce_literal(x, ctype) for x in case] + [f'o{i}' for i in range(len(outs))])
        check = ' && '.join(f'o{i} == {"true" if x else "false"}' if m else
                            f'o{i} != o{i}' if x != x else f'o{i} == {_ce_literal(x, ctype)}'
                            for i, (x, m) in enumerate(zip(outs, masks)))
        lines.append(f'static_assert([] {{ {decl} kairn::gen::{name}({args}); return {check}; }}());')
    lines.append('int main() {}')
    return '\n'.join(lines) + '\n'


# An overflow on finite operands, which gives (inf, 0) at run time. In constant evaluation the core
# stops first: GCC refuses the overflow itself (the largest double times 2), Clang the NaN that
# TwoSum then computes (inf - inf).
OVERFLOW_CE = ('#include <limits>\n#include "kairn/gen/scalar.hpp"\n'
               'static_assert([] { double w0 = 0, w1 = 0; kairn::gen::add_2_2_full(0x1.fffffffffffffp+1023, 0.0, '
               '0x1.fffffffffffffp+1023, 0.0, w0, w1); return w0 == std::numeric_limits<double>::infinity(); }());\n'
               'int main() {}\n')


def compile_(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stderr


def rosetta():
    """Whether x86-64 binaries can be built and run here (macOS on Apple silicon)."""
    if sys.platform != 'darwin' or X86 or 'c++' not in COMPILERS:
        return False
    return subprocess.run(['arch', '-x86_64', '/usr/bin/true'], capture_output=True).returncode == 0


def lines_for(kernels, names, seed, extra=None):
    """(kernel, format, operands, request line) for N random cases per kernel and format, and the
    cases extra(fmt, kernel) gives, if any."""
    out = []
    for name in names:
        for fmt in ('binary64', 'binary32'):
            cases = common.requests(fmt, kernels[name], N, seed) + (extra(fmt, kernels[name]) if extra else [])
            for i, case in enumerate(cases):
                out.append((name, fmt, case, f'{name} {fmt} {" ".join(map(common.token, case))} #{i}'))
    return out


def expect(directory, cases, fused=True):
    """Each request's interpreter output limbs, as floats."""
    out = [None] * len(cases)
    groups = {}
    for i, (name, fmt, case, _) in enumerate(cases):
        groups.setdefault((name, fmt), []).append(i)
    for (name, fmt), idx in groups.items():
        for i, o in zip(idx, common.interpret(directory, name, fmt, [cases[i][2] for i in idx], fused=fused)):
            out[i] = o
    return out


def parse_completed(line):
    return [float.fromhex(t) for t in line.split(' -> ')[1].split()]


# Operands that tell a fault planted in a kernel's scalar code from the kernel and that the random
# cases of test_matrix miss (tests/kernel_mutants.py; results/milestone1/mutants/survivors.json),
# each line with the fault it catches. Bit identity holds on any operand, so some are outside the
# kernel's domain (marked "outside"): neither tier sees those faults, by design.
SPECIAL_CASES = {
    'mul_2_2': {
        'binary64': [
            '-0x1p+0 -0x1p-60 0x0p+0 0x0p+0',         # tl0 = x1 * y1: a low limb -0, not +0
            '-0x0p+0 -0x0.0000000000001p-1022 0x1.0659418fbcbb6p-521 0x1.5555555555555p-2',  # outside: ch = x0 * y0
            '0x0p+0 0x0.8p-1022 -0x0p+0 -0x1.0000000000001p-1022',       # outside: tl0 = x1 * y1 + 0.0
        ],
        'binary32': [
            '-0x1p+0 -0x1p-30 0x0p+0 0x0p+0',
            '0x1p-127 0x0p+0 -0x0p+0 -0x1.8f681ep-51',
            '0x0p+0 0x1p-75 -0x0p+0 -0x1p-149',
        ],
    },
    'mul_2_2_full': {
        'binary64': [
            '-0x1p+0 -0x1p-60 0x0p+0 0x0p+0',         # z0_tl0 = x1 * y1
            '-0x0p+0 -0x1.2df1030122b6p-964 0x0p+0 0x1p-537',            # outside: z0_ch = x0 * y0, z0_tl0 + 0.0
        ],
        'binary32': [
            '-0x1p+0 -0x1p-30 0x0p+0 0x0p+0',
            '-0x0p+0 -0x1p-149 0x1p-149 0x1.fffffcp-127',                # outside: z0_ch = x0 * y0
            '0x0p+0 0x1p-149 -0x0p+0 -0x1p-24',                          # outside: z0_tl0 = x1 * y1 + 0.0
        ],
    },
    'ball_mul_2': {
        'binary64': [
            '-0x1p+0 -0x1p-60 0x0p+0 0x0p+0 0x0p+0 0x0p+0',             # cz0_tl0 = cx1 * cy1
            '-0x0p+0 -0x1p-1022 0x1p-53 0x0.fffffffffffffp-1022 -0x1.0000000000001p-1022 0x1.7f7beb3d7addbp-1021',
            # outside: cz0_ch = cx0 * cy0 (above), cz0_tl0 = cx1 * cy1 + 0.0 (below)
            '0x0p+0 0x1.0000000000001p-1022 -0x1.0000004000001p+0 -0x0p+0 -0x0.fffffffffffffp-1022 '
            '-0x1.0000004000001p+0',
        ],
        'binary32': [
            '-0x1p+0 -0x1p-30 0x0p+0 0x0p+0 0x0p+0 0x0p+0',
            '0x1p-126 0x1p-63 -0x1p-63 -0x0p+0 -0x1p-149 -0x1p+103',
            '-0x0p+0 -0x1p-24 0x1.d2ac3p+125 0x0p+0 0x1p-149 -0x0p+0',
        ],
    },
    'ball_mul_2_full': {
        'binary64': [
            '-0x1p+0 -0x1p-60 0x0p+0 0x0p+0 0x0p+0 0x0p+0',             # cz0_tl0 = cx1 * cy1
            '0x0.8p-1022 0x1p-1022 -0x1.ffffffffc259dp+174 -0x0p+0 -0x1p-511 0x1.3faa40413b9d1p-405',
            # outside: cz0_ch = cx0 * cy0 (above), cz0_tl0 = cx1 * cy1 + 0.0 (below)
            '0x0p+0 0x1.f468898dd39bdp-998 0x1.0000004000001p+0 -0x0p+0 -0x1.324a99546b27ep-151 0x1.fffffffffffffp+1',
        ],
        'binary32': [
            '-0x1p+0 -0x1p-30 0x0p+0 0x0p+0 0x0p+0 0x0p+0',
            '0x0p+0 0x1.fffffcp-127 -0x1.eb207ap-46 -0x1.5fdf8ap-122 -0x1p-127 0x1.460d48p-102',
            '0x0p+0 0x1.c2bf6p-91 -0x1p+0 -0x0p+0 -0x1p-127 -0x1.000006p+0',
        ],
    },
    # The splitter 2^s + 1 shortened to 2^s: in binary32 a significand just above 1 gets a 13-bit
    # high half (the claim, a = ah + al exactly, still holds); in binary64 only where the original's
    # g = (2^27 + 1) a overflows and the mutant's does not.
    'split': {
        'binary64': ['0x1.ffffffffff6cap+996'],
        'binary32': ['0x1.00086ap+78'],
    },
    'two_prod_dekker': {
        'binary64': ['-0x1.ffffffff55ceap+996 -0x1.fffffffff3231p-724',    # the splitter of a, as split's
                     '-0x1.000000001107dp-69 0x1.fffffffffc106p+996'],     # and of b
        'binary32': ['0x1.000b28p-116 -0x1.ffffaap-1', '-0x1.00039ap-108 0x1.000a7cp-8'],
    },
    # outside: f = inf > |z0| loosened to >=, which only an infinite z0 tells apart; on canonical
    # operands add_2_2 overflows to a NaN z0 (no search found an infinite one).
    'add_2_2_full': {
        'binary64': ['-0x1.0000000000003p+0 -0x1p+0 0x1.1155c6c8f72dfp+1022 -0x1.fffffffffffffp+1023'],
        'binary32': ['-0x1.10f38ep+124 -0x1.4c086p-88 0x1.80ca52p+126 -0x1.fffffep+127'],
    },
    'sub_2_2_full': {
        'binary64': ['0x1p-1022 -0x1.fffffffffffffp+1023 -0x1.5daaa8af2da63p+1022 0x1p+0'],
        'binary32': ['0x1.f4acbcp+124 0x1.c27462p-95 -0x1.00007ap+124 0x1.fffffep+127'],
    },
}


def special_cases(fmt, kernel):
    return [[float.fromhex(x) for x in case.split()] for case in SPECIAL_CASES.get(kernel.name, {}).get(fmt, ())]


def matrix_cases(kernels, name):
    """The cases of Kernels.test_matrix for one kernel: lines_for's, with non-finite operands in
    the forms of the non-finite layer for its kernels, and SPECIAL_CASES. tests/kernel_mutants.py
    uses them too."""
    return lines_for(kernels, [name], 'cxx',
                     lambda fmt, k: common.nonfinite_cases(fmt, k, N // 4, 'cxx') + special_cases(fmt, k))


def differences(cases, want, out):
    """The lines of a runner's output `out` for `cases` that are not bit-identical to the
    interpreter's limbs `want`, each with those limbs; an AssertionError if `out` is not the
    completion of the cases, line by line."""
    got = out.splitlines()
    if len(got) != len(cases):
        raise AssertionError(f'{len(got)} lines for {len(cases)} requests')
    bad = []
    for (_, _, _, request), w, line in zip(cases, want, got):
        if not line.startswith(request + ' -> '):
            raise AssertionError(line)
        g = parse_completed(line)
        if len(g) != len(w) or not all(common.same(x, y) for x, y in zip(g, w)):
            bad.append((line, [x.hex() for x in w]))
    return bad


def configurations(compilers):
    """(label, command without sources) of every build of the matrix with each compiler."""
    return [(f'{cxx} {" ".join(flags)}', [cxx] + BASE + flags) for cxx in compilers for flags in MATRIX + FORMS]


class Builds:
    """Every configuration of the matrix, built in parallel into one directory."""

    def __init__(self, tag, sources, extra=()):
        self.dir = common.scratch(tag)
        self.configs = configurations(COMPILERS)
        if rosetta():
            for flags in (['-O2', '-ffp-contract=fast'], ['-O0', '-ffp-contract=off'],
                          ['-O2', '-ffp-contract=on', '-frounding-math']):
                self.configs.append((f'c++ -arch x86_64 -mfma {" ".join(flags)} (Rosetta)',
                                     ['c++', '-arch', 'x86_64', '-mfma'] + BASE + flags))
        jobs = []
        for i, (label, cmd) in enumerate(self.configs):
            exe = os.path.join(self.dir, f'runner{i}')
            jobs.append(cmd + list(extra) + list(sources) + ['-o', exe])
        with ThreadPoolExecutor(JOBS) as ex:
            self.results = list(ex.map(compile_, jobs))
        self.exes = [os.path.join(self.dir, f'runner{i}') for i in range(len(self.configs))]

    def run(self, i, text):
        r = subprocess.run([self.exes[i]], input=text, capture_output=True, text=True)
        return r.returncode, r.stdout, r.stderr


class Kernels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not COMPILERS:
            raise unittest.SkipTest('no C++ compiler (set KAIRN_GEN_CXX)')
        cls.ks = common.kernels()
        cls.builds = Builds('cxx', [RUNNER], ['-I', INCLUDE, '-I', common.TESTS])

    def test_matrix(self):
        """Every build, every kernel, both limb types: bit-identical to the interpreter."""
        for name in self.ks:
            cases = matrix_cases(self.ks, name)
            want = expect(None, cases)
            text = ''.join(c[3] + '\n' for c in cases)
            reference = None
            for i, (label, _) in enumerate(self.builds.configs):
                with self.subTest(kernel=name, build=label):
                    status, err = self.builds.results[i]
                    self.assertEqual(status, 0, err)
                    code, out, err = self.builds.run(i, text)
                    self.assertEqual(code, 0, err)
                    if out == reference:            # the same text as an already checked build
                        continue
                    bad = differences(cases, want, out)
                    self.assertEqual(bad[:5], [], f'{len(bad)} of {len(cases)} differ from the interpreter')
                    reference = out

    def test_runner_protocol(self):
        text = '# comment\n\ntwo_sum binary64 0x1p+0 0x1p-60 #tag\nmul_2_1 binary32 0x1p+0 0x0p+0 0x1.8p+1\n'
        code, out, err = self.builds.run(0, text)
        self.assertEqual(code, 0, err)
        self.assertEqual(out, '# comment\n\ntwo_sum binary64 0x1p+0 0x1p-60 #tag -> 0x1p+0 0x1p-60\n'
                              'mul_2_1 binary32 0x1p+0 0x0p+0 0x1.8p+1 -> 0x1.8p+1 0x0p+0\n')
        for line, words in (('nope binary64 0x1p+0', 'unknown kernel'), ('two_sum binary64 1.0 0x1p+0', 'not a limb'),
                            ('two_sum binary32 0x1.0000001p+0 0x1p+0', 'not a binary32'),
                            ('two_sum binary32 0x1p+200 0x1p+0', 'not a binary32'),
                            ('two_sum fp:5:-12:6 0x1p+0 0x1p+0', 'binary64 and binary32'),
                            ('two_sum binary64  0x1p+0', 'single spaces'), ('two_sum binary64 0x1p+0', 'takes 2')):
            code, out, err = self.builds.run(0, '# fine\n' + line + '\n')
            self.assertEqual(code, 2, line)
            self.assertIn('line 2:', err)
            self.assertIn(words, err)

    def test_runner_non_finite_limbs(self):
        """Every build reads inf, -inf and nan as input limbs and prints non-finite outputs as
        exactly inf, -inf and nan: never -nan, whatever the sign bit of the NaN the hardware made
        (x86's default NaN has it set). Zeros keep the sign the kernel gives them."""
        lines = NON_FINITE_LINES
        text = ''.join(f'{x}\n' for x in lines)
        want = ''.join(f'{x} -> {y}\n' for x, y in lines.items())
        for i, (label, _) in enumerate(self.builds.configs):
            with self.subTest(build=label):
                self.assertEqual(self.builds.results[i][0], 0, self.builds.results[i][1])
                code, out, err = self.builds.run(i, text)
                self.assertEqual((code, out), (0, want), err)

    def test_runner_masks(self):
        code, out, err = self.builds.run(0, 'lt_2_1 binary64 0x1p+0 -0x1p-60 0x1p+0\n'
                                            'le_1_2 binary32 0x1p+0 0x1p+0 -0x1p-30\n')
        self.assertEqual(code, 0, err)
        self.assertEqual(out, 'lt_2_1 binary64 0x1p+0 -0x1p-60 0x1p+0 -> 1\n'
                              'le_1_2 binary32 0x1p+0 0x1p+0 -0x1p-30 -> 0\n')


class SpecialCases(unittest.TestCase):
    def test_they_fit_their_kernels(self):
        """Every kernel of SPECIAL_CASES exists, and each case is one operand per input value, each a
        number of its format, so that none drops out of test_matrix unseen."""
        ks = common.kernels()
        for name, by_format in SPECIAL_CASES.items():
            self.assertIn(name, ks)
            self.assertLessEqual(set(by_format), {'binary64', 'binary32'})
            for fmt, cases in by_format.items():
                for case in special_cases(fmt, ks[name]):
                    self.assertEqual(len(case), len(ks[name].input_kinds), (name, case))
                    self.assertEqual([common.rn(fmt, x) for x in case], case, (name, fmt, case))


def negates_a_fused_result(k, kernels):
    """Whether the kernel negates the result of a fused operation or of a muladd.

    On AArch64, GCC and Clang at -O2 turn -fma(a, b, c) into one fnmadd, which computes
    (-ab) + (-c): when ab + c is exactly zero that is +0, where the negation gives -0. Clang does
    it even through a sign-bit flip written with std::bit_cast. Only the sign of a zero changes,
    which Kairn leaves unspecified, but such a kernel has no single bit-exact result.
    """
    prims = ir.prims(k, kernels)
    defs = {p.dst: p.op for p in prims}
    return any(p.op == 'neg' and defs.get(p.args[0].name) in ir.FUSED | {'muladd'}
               for p in prims if not p.args[0].const)


def same_but_zero_signs(x, y):
    return common.same(x, y) or (x == 0 and y == 0)


class EveryOperation(unittest.TestCase):
    """The test kernels, which use every operation of the IR, printed and compiled the same way."""

    @classmethod
    def setUpClass(cls):
        if not COMPILERS:
            raise unittest.SkipTest('no C++ compiler (set KAIRN_GEN_CXX)')
        cls.ks = common.kernels(common.TEST_KERNELS)
        d = common.scratch('ops')
        for name, text in (('prelude.hpp', cpp.prelude(cls.ks)), ('kernels.hpp', cpp.scalar(cls.ks)),
                           ('runner_kernels.inc', cpp.runner_table(cls.ks))):
            with open(os.path.join(d, name), 'w') as f:
                f.write(text)
        shutil.copy(RUNNER, d)     # so that its #include "runner_kernels.inc" finds these kernels
        cls.builds = Builds('ops-build', [os.path.join(d, 'runner.cpp')],
                            ['-I', d, '-DKAIRN_RUNNER_HEADER="kernels.hpp"'])

    def test_negated_fused_results_are_known(self):
        self.assertEqual({n for n, k in self.ks.items() if negates_a_fused_result(k, self.ks)},
                         {'ops_muladd', 'ops_call'})
        ks = common.kernels()
        self.assertEqual({n for n, k in ks.items() if negates_a_fused_result(k, ks)}, set())

    def test_runner_mask_operands(self):
        code, out, err = self.builds.run(0, 'ops_wave2 binary64 -0x1p+0 1 0x1p+0\n')
        self.assertEqual(code, 0, err)
        self.assertTrue(out.endswith(' 1\n'), out)
        for bad in ('2', '0x1p+0', '-0'):
            code, out, err = self.builds.run(0, f'# fine\nops_wave2 binary64 0x1p+0 {bad} 0x1p+0\n')
            self.assertEqual(code, 2, bad)
            self.assertIn('line 2: not a mask', err)

    def test_the_cases_take_both_paths_of_a_branch(self):
        # ops_branch branches on m1 = (a == a) and m2 = (b == b): the cases of test_matrix take the
        # first path, and the fix-up with each mask false alone.
        paths = {(True, True): 0, (False, True): 0, (True, False): 0, (False, False): 0}
        for _, _, (a, b), _ in lines_for(self.ks, ['ops_branch'], 'ops'):
            paths[(a == a, b == b)] += 1
        self.assertTrue(paths[(True, True)] and paths[(False, True)] and paths[(True, False)], paths)

    def test_matrix(self):
        names = list(self.ks)
        cases = lines_for(self.ks, names, 'ops')
        fused = expect(common.TEST_KERNELS, cases, fused=True)
        unfused = expect(common.TEST_KERNELS, cases, fused=False)
        text = ''.join(c[3] + '\n' for c in cases)
        loose = {n for n, k in self.ks.items() if negates_a_fused_result(k, self.ks)}
        checked = {}         # digest of an output already compared line by line: its zero-sign count
        for i, (label, cmd) in enumerate(self.builds.configs):
            with self.subTest(build=label):
                status, err = self.builds.results[i]
                self.assertEqual(status, 0, err)
                code, out, err = self.builds.run(i, text)
                self.assertEqual(code, 0, err)
                contract_off = '-ffp-contract=off' in cmd
                digest = (contract_off, hashlib.sha256(out.encode()).digest())
                if digest in checked:
                    self.note(label, checked[digest])
                    continue
                bad, zero_signs = [], 0
                for (name, _, _, request), f, u, line in zip(cases, fused, unfused, out.splitlines()):
                    g = parse_completed(line)
                    allowed = [u] if contract_off else [u, f]   # without contraction, two roundings
                    if any(all(common.same(x, y) for x, y in zip(g, w)) for w in allowed):
                        continue
                    if name in loose and any(all(same_but_zero_signs(x, y) for x, y in zip(g, w))
                                             for w in allowed):
                        zero_signs += 1
                        continue
                    bad.append((line, [x.hex() for x in u], [x.hex() for x in f]))
                self.note(label, zero_signs)
                self.assertEqual(bad[:5], [], f'{len(bad)} of {len(cases)} differ from the interpreter')
                checked[digest] = zero_signs

    @staticmethod
    def note(label, zero_signs):
        if zero_signs:
            print(f'\n  note: {label}: {zero_signs} results of kernels that negate a fused result differ '
                  'from the interpreter in the sign of a zero only', file=sys.stderr)


def arithmetic_finite(ks, k, fmt, case):
    """Whether every operation of arithmetic of a kernel (calls inlined) gives a finite value in
    constant evaluation, each prod a plain product. GCC refuses an overflow there and Clang a NaN,
    so a case where one occurs is not a constant expression even when the outputs are finite (a sum
    rounded down that overflows is Omega: add_down_1)."""
    m = interp.Machine(ks, consteval=True)
    env = dict(zip(k.input_limbs, (common.to_value(x) for x in case)))
    for p in ir.prims(k, ks):
        args = [m._const(fmt, a.name) if a.const else env[a.name] for a in p.args]
        env[p.dst] = m._op(p.op, fmt, args, True)
        if p.op in ('add', 'sub', 'prod', 'muladd') and env[p.dst][0] != interp.NUM:
            return False
    return True


def bits(x, ctype):
    return struct.unpack('<Q', struct.pack('<d', x))[0] if ctype == 'double' else \
        struct.unpack('<I', struct.pack('<f', x))[0]


def literal(x, ctype):
    if isinstance(x, bool):
        return 'true' if x else 'false'
    return f'{x.hex()}{"f" if ctype == "float" else ""}'


class ConstantEvaluation(unittest.TestCase):
    """two_prod in constant evaluation runs Dekker's product; static_assert checks its bits."""

    H = float.fromhex
    CASES = {
        'double': [(H('0x1.123456789abcdp+3'), H('0x1.fedcba9876543p-7')), (1 + 2 ** -52, 1 - 2 ** -52),
                   (3.0, 1 / 3), (H('0x1.fffffffffffffp+500'), H('0x1.fffffffffffffp+400')),
                   (H('-0x1.5555555555555p-1'), H('0x1.0000000000001p+20')), (-0.0, 1.0),
                   (2.0 ** -500, 2.0 ** -500)],
        'float': [(H('0x1.234568p+3'), H('0x1.fedcbap-7')), (1 + 2 ** -23, 1 - 2 ** -23), (3.0, H('0x1.555556p-2')),
                  (H('0x1.fffffep+40'), H('0x1.fffffep+30')), (-0.0, 1.0), (2.0 ** -70, 2.0 ** -70)],
    }

    @classmethod
    def setUpClass(cls):
        if not COMPILERS:
            raise unittest.SkipTest('no C++ compiler (set KAIRN_GEN_CXX)')
        cls.ks = common.kernels()
        cls.dir = common.scratch('ce')

    def source(self):
        lines = ['#include <bit>', '#include <cstdint>', '#include "kairn/gen/scalar.hpp"', '']
        ce = interp.Machine(self.ks, consteval=True)
        rt = interp.Machine(self.ks)
        utype = {'double': 'std::uint64_t', 'float': 'std::uint32_t'}
        for ctype, cases in self.CASES.items():
            fmt = interp.parse_format('binary64' if ctype == 'double' else 'binary32')
            for a, b in cases:
                p, e = [common.to_float(v) for v in ce.run('two_prod', fmt, [common.to_value(a), common.to_value(b)])]
                # A correct exact product: p = RN(ab), and p + e = ab whenever ab = 0 or
                # |ab| >= 2^(2p-1) eta (checked here with rationals, independently of the kernels).
                exact = Fraction(a) * Fraction(b)
                self.assertEqual(Fraction(p), Fraction(common.rn(fmt.name, float(exact))) if exact else 0)
                if exact == 0 or abs(exact) >= Fraction(2) ** (2 * fmt.p - 1 + fmt.qmin):
                    self.assertEqual(Fraction(p) + Fraction(e), exact, (a, b))
                lines.append(f'static_assert([] {{ {ctype} p = 0, e = 0; kairn::gen::two_prod({literal(a, ctype)}, '
                             f'{literal(b, ctype)}, p, e); return std::bit_cast<{utype[ctype]}>(p) == {bits(p, ctype)}u '
                             f'&& std::bit_cast<{utype[ctype]}>(e) == {bits(e, ctype)}u; }}());')
            # The kernels without fused operations, and those whose only fused operations are prod
            # (the rule of the product: each a plain product here), give in constant evaluation the
            # bits that the interpreter computes there: their run-time values, except that a guard
            # leaves a -0 as it is and a plain product of an exact zero keeps its sign
            # (test_interp.TwoExecutionsOfAProduct says which kernels have the same bits); succ and
            # pred (std::bit_cast) also on zeros of both signs, subnormals and the largest finite
            # numbers; the full kernels of the additions included.
            edge = [x for x in common.edges(fmt.name) if math.isfinite(x)]
            for name, k in self.ks.items():
                if cpp.constexpr_kind(k, self.ks) != 'plain':
                    continue
                rng = random.Random(f'ce:{name}:{fmt.name}')
                cases = common.requests(fmt.name, k, 8, 'ce') + \
                    [[rng.choice((False, True)) if kind == ir.MASK else rng.choice(edge) for kind in k.input_kinds]
                     for _ in range(16)]
                for case in cases:
                    if not all(isinstance(x, bool) or math.isfinite(x) for x in case):
                        continue
                    outs = [common.to_float(v) for v in ce.run(name, fmt, [common.to_value(x) for x in case])]
                    if not all(math.isfinite(x) for x in outs) or not arithmetic_finite(self.ks, k, fmt, case):
                        continue   # not a constant expression: tested apart
                    rt_outs = [common.to_float(v) for v in rt.run(name, fmt, [common.to_value(x) for x in case])]
                    self.assertEqual(outs, rt_outs, (name, case))     # the same values, zeros aside
                    kinds = k.output_kinds
                    decl = ' '.join(f'{"bool" if kind == ir.MASK else ctype} o{i} = 0;' for i, kind in enumerate(kinds))
                    args = ', '.join([literal(x, ctype) for x in case] + [f'o{i}' for i in range(len(outs))])
                    check = ' && '.join(f'o{i} == {"true" if x else "false"}' if kind == ir.MASK else
                                        f'std::bit_cast<{utype[ctype]}>(o{i}) == {bits(x, ctype)}u'
                                        for i, (x, kind) in enumerate(zip(outs, kinds)))
                    lines.append(f'static_assert([] {{ {decl} kairn::gen::{name}({args}); return {check}; }}());')
        lines.append('int main() {}')
        return '\n'.join(lines) + '\n'

    def test_static_asserts(self):
        path = os.path.join(self.dir, 'ce_test.cpp')
        with open(path, 'w') as f:
            f.write(self.source())
        flag_sets = [[], ['-frounding-math'], ['-ffp-contract=fast'], ['-O2', '-ffp-contract=fast', '-frounding-math']]
        flag_sets += [[f'-DKAIRN_GEN_FIXUP_CALL={c}'] for c in (0, 1)]    # both forms of the fix-ups
        jobs = [[cxx] + BASE + flags + ['-I', INCLUDE, '-fsyntax-only', path]
                for cxx in COMPILERS for flags in flag_sets]
        with ThreadPoolExecutor(JOBS) as ex:
            for cmd, (status, err) in zip(jobs, ex.map(compile_, jobs)):
                self.assertEqual(status, 0, f'{" ".join(cmd)}\n{err}')

    def test_overflow_is_not_a_constant_expression(self):
        # Dekker's product overflows in its split near the top of the range; in constant
        # evaluation that is a compile error, never a wrong constant (two_prod_dekker's cone_exempt).
        path = os.path.join(self.dir, 'ce_overflow.cpp')
        with open(path, 'w') as f:
            f.write('#include "kairn/gen/scalar.hpp"\n'
                    'constexpr double e = [] { double p = 0, e = 0; '
                    'kairn::gen::two_prod(0x1.fffffffffffffp+1023, 0x1p-1000, p, e); return e; }();\n'
                    'int main() { return e == 0; }\n')
        for cxx in COMPILERS:
            status, err = compile_([cxx] + BASE + ['-I', INCLUDE, '-fsyntax-only', path])
            self.assertNotEqual(status, 0, cxx)
            self.assertIn('constant', err)

    def test_the_non_finite_layer_in_constant_evaluation(self):
        """The full kernels of the additions are constant expressions on finite operands, also when
        t = 0, where times_inf(t) is a NaN that constant evaluation could not compute (it compares
        instead); the constructors on infinite and NaN operands, where guard returns its operand.
        With every flag set of test_static_asserts."""
        path = os.path.join(self.dir, 'ce_nonfinite.cpp')
        with open(path, 'w') as f:
            f.write(nonfinite_ce_source(self.ks))
        self.assertEqual({n for n, _, _ in NONFINITE_CE_CASES},
                         {n for n, k in self.ks.items() if k.extended and not k.real_model and
                          cpp.constexpr_kind(k, self.ks) == 'plain'})
        flag_sets = [[], ['-frounding-math'], ['-O2', '-ffp-contract=fast', '-frounding-math']]
        flag_sets += [[f'-DKAIRN_GEN_FIXUP_CALL={c}'] for c in (0, 1)]    # both forms of the fix-ups
        jobs = [[cxx] + BASE + flags + ['-I', INCLUDE, '-fsyntax-only', path] for cxx in COMPILERS for flags in flag_sets]
        with ThreadPoolExecutor(JOBS) as ex:
            for cmd, (status, err) in zip(jobs, ex.map(compile_, jobs)):
                self.assertEqual(status, 0, f'{" ".join(cmd)}\n{err}')

    def test_an_overflow_of_a_full_kernel_is_not_a_constant_expression(self):
        # Not a wrong constant: a compile error, from the core (OVERFLOW_CE).
        path = os.path.join(self.dir, 'ce_full_overflow.cpp')
        with open(path, 'w') as f:
            f.write(OVERFLOW_CE)
        for cxx in COMPILERS:
            status, err = compile_([cxx] + BASE + ['-I', INCLUDE, '-fsyntax-only', path])
            self.assertNotEqual(status, 0, cxx)
            self.assertIn('constant', err)

    # Usable in constant evaluation: the controls (two_sum; radd through succ) and the kernels whose
    # only fused operations are prod (the rule of the product).
    CONSTEXPR = ('two_sum', 'radd', 'split', 'two_prod_dekker', 'rmul', 'mul_pow2_2', 'mul_pow2_2_full',
                 'ball_mul_pow2_1', 'ball_mul_pow2_2_full')

    def test_kernels_with_fused_operations_are_not_constexpr(self):
        # Those with a fused operation other than prod and no variant, the directed products of
        # one limb among them (two_prod's fms, never its variant: milestone2.md).
        for name in ('mul_2_2', 'mul_2_1', 'ball_add_1', 'mul_2_2_full', 'mul_2_1_full', 'ball_add_2_full',
                     'mul_down_1', 'mul_up_1') + self.CONSTEXPR:
            k = self.ks[name]
            path = os.path.join(self.dir, f'not_constexpr_{name}.cpp')
            args = ', '.join(['1.0'] * len(k.input_limbs) + [f'o[{i}]' for i in range(len(k.output_limbs))])
            with open(path, 'w') as f:
                f.write('#include "kairn/gen/scalar.hpp"\n'
                        f'constexpr bool ok = [] {{ double o[{len(k.output_limbs)}] = {{}}; '
                        f'kairn::gen::{name}({args}); return o[0] == o[0]; }}();\n'
                        'static_assert(ok);\nint main() {}\n')
            for cxx in COMPILERS:
                status, err = compile_([cxx] + BASE + ['-I', INCLUDE, '-fsyntax-only', path])
                if name in self.CONSTEXPR:
                    self.assertEqual(status, 0, err)
                else:
                    self.assertNotEqual(status, 0, f'{cxx}: {name} is usable in constant evaluation')
                    self.assertIn('constant', err)


class Prelude(unittest.TestCase):
    def test_x86_without_fma_is_refused(self):
        if X86:
            cxx = [COMPILERS[0]] if COMPILERS else None
        elif sys.platform == 'darwin' and 'c++' in COMPILERS:
            cxx = ['c++', '-arch', 'x86_64']
        else:
            cxx = None
        if not cxx:
            self.skipTest('no compiler for x86-64 here')
        d = common.scratch('prelude')
        path = os.path.join(d, 'p.cpp')
        with open(path, 'w') as f:
            f.write('#include "kairn/gen/scalar.hpp"\nint main() {}\n')
        base = [b for b in BASE if b != '-mfma']
        status, err = compile_(cxx + base + ['-mno-fma', '-I', INCLUDE, '-fsyntax-only', path])
        self.assertNotEqual(status, 0)
        self.assertIn('Kairn needs hardware FMA', err)
        status, err = compile_(cxx + base + ['-mfma', '-I', INCLUDE, '-fsyntax-only', path])
        self.assertEqual(status, 0, err)


if __name__ == '__main__':
    unittest.main()
