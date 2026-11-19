"""The packed kernels (AVX2, NEON), lane by lane against the scalar kernels and the interpreter.

gen/tests/packed_runner.cpp evaluates consecutive requests for one kernel and format together, one
per lane. The requests mix ordinary operands with special ones (signed zeros, subnormals, the
extremes of the format, infinities and NaN), placed in one lane of a register at a time as well as
at random, and every build of the packed runner must print exactly what the scalar runner built
with the same compiler and flags prints, and be bit-identical to the interpreter.

Where: NEON natively on AArch64; AVX2 natively on x86-64 (with -mavx2 -mfma), and on macOS on
Apple silicon under Rosetta (-arch x86_64 -mavx2 -mfma) when it runs AVX2 code.
"""
import hashlib
import os
import platform
import random
import shutil
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor

import common
import test_cxx as cxx
from kairn_gen import cpp, simd

ARM64 = platform.machine().lower() in ('arm64', 'aarch64')
PACKED_RUNNER = os.path.join(common.TESTS, 'packed_runner.cpp')
LANES = 8                    # the most lanes of any backend (8 floats in AVX2): groups of this size
N = common.size(1500, 100000)


def configs():
    """(label, command prefix) for every packed build to test here."""
    out = []
    native = [] if ARM64 else ['-mavx2'] if cxx.X86 else None
    if native is not None:
        for c in cxx.COMPILERS:
            for flags in cxx.MATRIX:
                out.append((f'{c} {" ".join(native + flags)} ({"NEON" if ARM64 else "AVX2"})',
                            [c] + cxx.BASE + native + flags))
    if rosetta_avx2():
        for flags in (['-O2', '-ffp-contract=fast'], ['-O0', '-ffp-contract=off'],
                      ['-O2', '-ffp-contract=on', '-frounding-math']):
            out.append((f'c++ -arch x86_64 -mavx2 -mfma {" ".join(flags)} (AVX2, Rosetta)',
                        ['c++', '-arch', 'x86_64', '-mavx2', '-mfma'] + cxx.BASE + flags))
    return out


_rosetta = None


def rosetta_avx2():
    """Whether AVX2 code built for x86-64 runs here under Rosetta (macOS 15 and later)."""
    global _rosetta
    if _rosetta is None:
        _rosetta = False
        if cxx.rosetta():
            d = common.scratch('rosetta')
            src, exe = os.path.join(d, 'p.cpp'), os.path.join(d, 'p')
            with open(src, 'w') as f:
                f.write('#include <immintrin.h>\nint main() { volatile double a = 2; __m256d x = _mm256_set1_pd(a);\n'
                        '__m256i i = _mm256_add_epi64(_mm256_castpd_si256(_mm256_fmadd_pd(x, x, x)), _mm256_set1_epi64x(1));\n'
                        'return _mm256_extract_epi64(i, 3) == 0x4018000000000001 ? 0 : 1; }\n')
            built = subprocess.run(['c++', '-arch', 'x86_64', '-mavx2', '-mfma', '-O1', src, '-o', exe],
                                   capture_output=True).returncode == 0
            _rosetta = built and subprocess.run([exe], capture_output=True).returncode == 0
    return _rosetta


def special_groups(fmt, kernel, rng, n):
    """n groups of LANES requests, each with one special operand in one lane, the others ordinary."""
    specials = [x for x in common.edges(fmt)]
    out = []
    for g in range(n):
        lane = g % LANES
        group = [common.operands(rng, fmt, kernel) for _ in range(LANES)]
        limbs = [i for i, x in enumerate(group[lane]) if not isinstance(x, bool)]
        if limbs:
            group[lane][rng.choice(limbs)] = rng.choice(specials)
        out += group
    return out


def packed_cases(kernels, names, seed):
    """Request lines for the packed runner, grouped by kernel and format: the special groups first
    (so that they are aligned with the registers), then random and edge cases in random order."""
    def extra(fmt, k):
        rng = random.Random(f'{seed}:{fmt}:{k.name}:packed')
        mixed = common.edge_cases(fmt, k, 400) + common.requests(fmt, k, N, f'{seed}:packed')
        rng.shuffle(mixed)
        return special_groups(fmt, k, rng, 4 * LANES) + mixed
    lines = []
    for name in names:
        for fmt in ('binary64', 'binary32'):
            for i, case in enumerate(extra(fmt, kernels[name])):
                lines.append((name, fmt, case, f'{name} {fmt} {" ".join(map(common.token, case))} #{i}'))
    return lines


class Builds:
    """Each configuration, with the packed runner and, if asked, the scalar runner."""

    def __init__(self, tag, include, scalar=True, packed_runner=PACKED_RUNNER):
        self.dir = common.scratch(tag)
        self.configs = configs()
        jobs = []
        for i, (_, cmd) in enumerate(self.configs):
            for runner, src in (('packed', packed_runner),) + ((('scalar', cxx.RUNNER),) if scalar else ()):
                jobs.append(cmd + include + [src, '-o', os.path.join(self.dir, f'{runner}{i}')])
        with ThreadPoolExecutor(cxx.JOBS) as ex:
            results = list(ex.map(cxx.compile_, jobs))
        per = 2 if scalar else 1
        self.results = [results[i * per:(i + 1) * per] for i in range(len(self.configs))]

    def run(self, i, runner, text):
        r = subprocess.run([os.path.join(self.dir, f'{runner}{i}')], input=text, capture_output=True, text=True)
        return r.returncode, r.stdout, r.stderr


def no_packed_backend():
    if not cxx.COMPILERS:
        return 'no C++ compiler (set KAIRN_GEN_CXX)'
    if not configs():
        return 'no packed backend to build and run here'
    return None


class Kernels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        why = no_packed_backend()
        if why:
            raise unittest.SkipTest(why)
        cls.ks = common.kernels()
        cls.builds = Builds('packed', ['-I', cxx.INCLUDE, '-I', common.TESTS])
        cls.cases = packed_cases(cls.ks, list(cls.ks), 'packed')
        cls.want = cxx.expect(None, cls.cases)
        cls.text = ''.join(c[3] + '\n' for c in cls.cases)

    def test_lane_by_lane(self):
        """Every packed build prints what the scalar build with the same flags prints, and that is
        bit-identical to the interpreter."""
        checked = set()
        for i, (label, _) in enumerate(self.builds.configs):
            with self.subTest(build=label):
                for (status, err) in self.builds.results[i]:
                    self.assertEqual(status, 0, err)
                code, packed, err = self.builds.run(i, 'packed', self.text)
                self.assertEqual(code, 0, err)
                code, scalar, err = self.builds.run(i, 'scalar', self.text)
                self.assertEqual(code, 0, err)
                p, s = packed.splitlines(), scalar.splitlines()
                self.assertEqual(len(p), len(self.cases))
                differ = [(a, b) for a, b in zip(p, s) if a != b]
                self.assertEqual(differ[:5], [], f'{len(differ)} of {len(p)} lines differ from the scalar build')
                digest = hashlib.sha256(packed.encode()).digest()
                if digest in checked:
                    continue
                bad = []
                for (_, _, _, request), w, line in zip(self.cases, self.want, p):
                    self.assertTrue(line.startswith(request + ' -> '), line)
                    g = cxx.parse_completed(line)
                    if len(g) != len(w) or not all(common.same(x, y) for x, y in zip(g, w)):
                        bad.append((line, [x.hex() for x in w]))
                self.assertEqual(bad[:5], [], f'{len(bad)} of {len(p)} differ from the interpreter')
                checked.add(digest)

    def test_runner_protocol(self):
        text = '# c\n\nlt_2_1 binary64 0x1p+0 -0x1p-60 0x1p+0 #t\nlt_2_1 binary64 nan 0x0p+0 0x1p+0\n# d\n' \
               'two_sum binary32 0x1p+0 0x1p-30\n'
        code, out, err = self.builds.run(0, 'packed', text)
        self.assertEqual(code, 0, err)
        self.assertEqual(out, '# c\n\nlt_2_1 binary64 0x1p+0 -0x1p-60 0x1p+0 #t -> 1\n'
                              'lt_2_1 binary64 nan 0x0p+0 0x1p+0 -> 0\n# d\n'
                              'two_sum binary32 0x1p+0 0x1p-30 -> 0x1p+0 0x1p-30\n')
        for line, words in (('nope binary64 0x1p+0', 'unknown kernel'), ('two_sum binary64 1.0 0x1p+0', 'not a limb'),
                            ('two_sum binary32 0x1p+200 0x1p+0', 'not a binary32'),
                            ('two_sum fp:5:-12:6 0x1p+0 0x1p+0', 'binary64 and binary32'),
                            ('two_sum binary64 0x1p+0', 'takes 2')):
            code, out, err = self.builds.run(0, 'packed', '# fine\ntwo_sum binary64 0x1p+0 0x1p+0\n' + line + '\n')
            self.assertEqual(code, 2, line)
            self.assertIn('line 3:', err)
            self.assertIn(words, err)
            self.assertEqual(out, '# fine\ntwo_sum binary64 0x1p+0 0x1p+0 -> 0x1p+1 0x0p+0\n')


class EveryOperation(unittest.TestCase):
    """The test kernels, packed: masks as operands and results, every operation of the IR."""

    @classmethod
    def setUpClass(cls):
        why = no_packed_backend()
        if why:
            raise unittest.SkipTest(why)
        cls.ks = common.kernels(common.TEST_KERNELS)
        # The test kernels' headers where the runner looks for the generated ones (kairn/gen/),
        # and their table beside a copy of the runner, which includes it by a relative name.
        d = common.scratch('packed-ops')
        os.makedirs(os.path.join(d, 'kairn', 'gen'))
        files = {'kairn/gen/prelude.hpp': cpp.prelude(cls.ks), 'runner_kernels.inc': cpp.runner_table(cls.ks)}
        files.update({f'kairn/gen/{b["file"]}': simd.header(b, cls.ks) for b in simd.BACKENDS})
        for name, text in files.items():
            with open(os.path.join(d, name), 'w') as f:
                f.write(text)
        shutil.copy(PACKED_RUNNER, d)
        cls.builds = Builds('packed-ops-build', ['-I', d], scalar=False,
                            packed_runner=os.path.join(d, 'packed_runner.cpp'))

    def test_matrix(self):
        names = list(self.ks)
        cases = packed_cases(self.ks, names, 'packed-ops')
        fused = cxx.expect(common.TEST_KERNELS, cases, fused=True)
        unfused = cxx.expect(common.TEST_KERNELS, cases, fused=False)
        text = ''.join(c[3] + '\n' for c in cases)
        loose = {n for n, k in self.ks.items() if cxx.negates_a_fused_result(k, self.ks)}
        for i, (label, cmd) in enumerate(self.builds.configs):
            with self.subTest(build=label):
                (status, err), = self.builds.results[i]
                self.assertEqual(status, 0, err)
                code, out, err = self.builds.run(i, 'packed', text)
                self.assertEqual(code, 0, err)
                contract_off = '-ffp-contract=off' in cmd
                bad, zero_signs = [], 0
                for (name, _, _, request), f, u, line in zip(cases, fused, unfused, out.splitlines()):
                    g = cxx.parse_completed(line)
                    allowed = [u] if contract_off else [u, f]
                    if any(all(common.same(x, y) for x, y in zip(g, w)) for w in allowed):
                        continue
                    if name in loose and any(all(cxx.same_but_zero_signs(x, y) for x, y in zip(g, w))
                                             for w in allowed):
                        zero_signs += 1
                        continue
                    bad.append((line, [x.hex() for x in u], [x.hex() for x in f]))
                cxx.EveryOperation.note(label, zero_signs)
                self.assertEqual(bad[:5], [], f'{len(bad)} of {len(cases)} differ from the interpreter')


if __name__ == '__main__':
    unittest.main()
