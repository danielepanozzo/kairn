"""The packed kernels (AVX2, NEON), lane by lane against the scalar kernels and the interpreter.

gen/tests/packed_runner.cpp evaluates the requests for one kernel and format W at a time, one per
lane, with the lanes assigned by a seeded permutation (the default) or consecutively (--lanes
consecutive). The requests mix ordinary operands with special ones (signed zeros, subnormals, the
extremes of the format, infinities and NaN), placed in one lane of a register at a time (with the
consecutive assignment) as well as at random, and every build of the packed runner, with each
assignment, must print exactly what the scalar runner built with the same compiler and flags
prints, and be bit-identical to the interpreter.

The assignment itself (Lanes): the plan the runner reports is the one this file computes again
from the same requests and seed (the permutation is integer arithmetic only, so every compiler
and target must agree); the registers of the permuted assignment mix requests with a non-finite
limb and finite ones, and every lane holds every kind; the guard refuses the consecutive
assignment of a stream whose registers never mix; and a last register that is not full is padded
with a finite request whose results are dropped.

Where: NEON natively on AArch64; AVX2 natively on x86-64 (with -mavx2 -mfma), and on macOS on
Apple silicon under Rosetta (-arch x86_64 -mavx2 -mfma) when it runs AVX2 code.
"""
import hashlib
import json
import math
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
    (so that they are aligned with the registers of the consecutive assignment), then random and
    edge cases in random order."""
    def extra(fmt, k):
        rng = random.Random(f'{seed}:{fmt}:{k.name}:packed')
        mixed = common.edge_cases(fmt, k, 400) + common.requests(fmt, k, N, f'{seed}:packed') + \
            common.nonfinite_cases(fmt, k, N // 4, f'{seed}:packed')
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

    def run(self, i, runner, text, args=()):
        r = subprocess.run([os.path.join(self.dir, f'{runner}{i}')] + list(args), input=text, capture_output=True,
                           text=True)
        return r.returncode, r.stdout, r.stderr


# The two assignments of requests to lanes, as the packed runner's options.
ASSIGNMENTS = (('permuted', ()), ('consecutive', ('--lanes', 'consecutive')))


def no_packed_backend():
    if not cxx.COMPILERS:
        return 'no C++ compiler (set KAIRN_GEN_CXX)'
    if not configs():
        return 'no packed backend to build and run here'
    return None


_shared = None


def shared_builds():
    """The packed and the scalar runner in every packed configuration, once per run of the suite:
    the kernels' tests here and the folds' (test_folds.py) use the same builds."""
    global _shared
    if _shared is None:
        _shared = Builds('packed', ['-I', cxx.INCLUDE, '-I', common.TESTS])
    return _shared


class Kernels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        why = no_packed_backend()
        if why:
            raise unittest.SkipTest(why)
        cls.ks = common.kernels()
        cls.builds = shared_builds()
        cls.cases = packed_cases(cls.ks, list(cls.ks), 'packed')
        cls.want = cxx.expect(None, cls.cases)
        cls.text = ''.join(c[3] + '\n' for c in cls.cases)

    def test_lane_by_lane(self):
        """Every packed build, with each assignment of the lanes, prints what the scalar build with
        the same flags prints, and that is bit-identical to the interpreter."""
        checked = set()
        for i, (label, _) in enumerate(self.builds.configs):
            for assignment, args in ASSIGNMENTS:
                with self.subTest(build=label, lanes=assignment):
                    for (status, err) in self.builds.results[i]:
                        self.assertEqual(status, 0, err)
                    code, packed, err = self.builds.run(i, 'packed', self.text, args)
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

    def test_runner_non_finite_limbs(self):
        """inf, -inf and nan as input limbs, and non-finite outputs printed exactly inf, -inf and
        nan, never -nan, in every packed build: what the scalar runner and the interpreter print."""
        lines = cxx.NON_FINITE_LINES
        text = ''.join(f'{x}\n' for x in lines)
        want = ''.join(f'{x} -> {y}\n' for x, y in lines.items())
        for i, (label, _) in enumerate(self.builds.configs):
            with self.subTest(build=label):
                self.assertEqual(self.builds.results[i][0][0], 0, self.builds.results[i][0][1])
                code, out, err = self.builds.run(i, 'packed', text)
                self.assertEqual((code, out), (0, want), err)

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


# The assignment of a segment's requests to the slots of its registers, as packed_runner.cpp
# computes it (its comment at the top), written again: SplitMix64, an integer below m by rejection,
# Fisher-Yates, the requests grouped by kind in the order the kinds appear.
_MASK = (1 << 64) - 1


class SplitMix64:
    def __init__(self, state):
        self.state = state & _MASK

    def next(self):
        self.state = (self.state + 0x9e3779b97f4a7c15) & _MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xbf58476d1ce4e5b9) & _MASK
        z = ((z ^ (z >> 27)) * 0x94d049bb133111eb) & _MASK
        return z ^ (z >> 31)

    def below(self, m):
        low = (1 << 64) % m
        while True:
            r = self.next()
            if r >= low:
                return r % m

    def shuffle(self, v):
        for i in range(len(v), 1, -1):
            j = self.below(i)
            v[i - 1], v[j] = v[j], v[i - 1]


def lane_slots(kinds, lanes, seed, segment, permuted=True):
    """The slots of the registers of a segment whose requests have the kinds KINDS (in order), W =
    LANES, the runner's segment number SEGMENT: the index of a request in each, or None."""
    n = len(kinds)
    registers = -(-n // lanes)
    if not permuted:
        return list(range(n)) + [None] * (registers * lanes - n)
    random_ = SplitMix64(seed + 0x632be59bd9b4e019 * (segment + 1))
    groups = {}
    for i, k in enumerate(kinds):
        groups.setdefault(k, []).append(i)
    order = []
    for g in groups.values():
        random_.shuffle(g)
        order += g
    order += [None] * (registers * lanes - n)
    slots = [None] * (registers * lanes)
    for lane in range(lanes):
        rows = list(range(registers))
        random_.shuffle(rows)
        for r in range(registers):
            slots[r * lanes + lane] = order[rows[r] * lanes + lane]
    return slots


def kind_of(case, stratum):
    """The kind of a request as the runner reads it: its stratum, and whether a limb is not finite."""
    return (stratum, any(not isinstance(x, bool) and not math.isfinite(x) for x in case))


def lane_stream(kernel, fmt, n, seed, first_nonfinite=False, nonfinite_only=False):
    """n requests shaped as the oracle's stream: tags #STRATUM:INDEX, the strata taking turns, every
    fortieth block of eight requests (a multiple of every W) with a non-finite limb, so that the
    consecutive assignment never mixes; (cases with their strata, the text)."""
    rng = random.Random(f'{seed}:{fmt}:{kernel.name}:lanes')
    out = []
    for i in range(n):
        case = common.operands(rng, fmt, kernel)
        nonfinite = nonfinite_only or (i % 40 >= 32) or (first_nonfinite and i == 0)
        limbs = [j for j, x in enumerate(case) if not isinstance(x, bool)]
        if nonfinite:
            case[rng.choice(limbs)] = rng.choice((math.inf, -math.inf, math.nan))
        else:
            case = [x if isinstance(x, bool) or math.isfinite(x) else 0.0 for x in case]
        out.append((case, 'nonfinite' if nonfinite else f'f{i % 8}'))
    text = ''.join(f'{kernel.name} {fmt} {" ".join(map(common.token, c))} #{s}:{i}\n' for i, (c, s) in enumerate(out))
    return out, text


class Lanes(unittest.TestCase):
    """The assignment of the requests to the lanes (packed_runner.cpp): its plan, its mixing, the
    guard, the padding of a register that is not full, and its options."""
    KERNELS = ('mul_2_2_full', 'neg_2', 'lt_2_2', 'norm_step_1')

    @classmethod
    def setUpClass(cls):
        why = no_packed_backend()
        if why:
            raise unittest.SkipTest(why)
        cls.ks = common.kernels()
        cls.builds = shared_builds()
        cls.dir = common.scratch('lanes')

    def run_packed(self, i, text, *args):
        """(exit status, output, standard error, the report of the lanes, the plan: {(segment,
        register, lane): line number or None})."""
        report, plan = os.path.join(self.dir, f'report{i}.json'), os.path.join(self.dir, f'plan{i}.txt')
        for f in (report, plan):
            if os.path.exists(f):
                os.remove(f)
        code, out, err = self.builds.run(i, 'packed', text, list(args) + ['--lane-report', report, '--lane-plan', plan])
        rep = slots = None
        if os.path.exists(report):
            with open(report) as f:
                rep = json.load(f)
        if os.path.exists(plan):
            slots = {}
            with open(plan) as f:
                for line in f:
                    s, r, lane, where = line.split()
                    slots[(int(s), int(r), int(lane))] = None if where == 'pad' else int(where)
        return code, out, err, rep, slots

    def test_plan_mixing_and_guard(self):
        """On a stream shaped as the oracle's, of a length that leaves the last register partial:
        both assignments print what the scalar runner prints; the plan of each is the one computed
        here (seeds 0 and 7); the permuted one mixes and holds every kind in every lane, the
        consecutive one never mixes, and the guard refuses it."""
        for i, (label, _) in enumerate(self.builds.configs):
            for name in self.KERNELS:
                for fmt in ('binary64', 'binary32'):
                    with self.subTest(build=label, kernel=name, format=fmt):
                        cases, text = lane_stream(self.ks[name], fmt, 1003, 'plan')
                        kinds = [kind_of(c, s) for c, s in cases]
                        code, scalar, err = self.builds.run(i, 'scalar', text)
                        self.assertEqual(code, 0, err)
                        plans = []
                        for permuted, seed, args in ((True, 0, []), (True, 7, ['--lane-seed', '7']),
                                                     (False, 0, ['--lanes', 'consecutive'])):
                            code, out, err, rep, plan = self.run_packed(i, text, *args)
                            self.assertEqual((code, out), (0, scalar), err)
                            seg, = rep['segments']
                            w = seg['lanes']
                            want = lane_slots(kinds, w, seed, 0, permuted)
                            got = [plan[(0, k // w, k % w)] for k in range(len(want))]
                            self.assertEqual(got, [None if j is None else j + 1 for j in want])
                            self.assertEqual(sorted(j for j in got if j is not None), list(range(1, 1004)))
                            self.assertEqual((seg['requests'], seg['padding']), (1003, len(want) - 1003))
                            plans.append(got)
                            if permuted:
                                self.assertGreater(seg['mixed'], 0)
                                self.assertEqual(seg['guard'], 'passed')
                                for k in seg['kinds']:
                                    self.assertTrue(k['requests'] < w or min(k['lanes']) > 0, k)
                            else:
                                self.assertEqual(seg['mixed'], 0)
                        self.assertNotEqual(plans[0], plans[1], 'seeds 0 and 7 gave the same plan')
                        # The guard on the consecutive assignment: refused, with 3, after the lines.
                        code, out, err, rep, _ = self.run_packed(i, text, '--lanes', 'consecutive', '--lane-guard')
                        self.assertEqual((code, out), (3, scalar), err)
                        self.assertIn('the lanes did not mix', err)
                        self.assertTrue(rep['segments'][0]['guard'].startswith('failed: '), rep)

    def test_padding(self):
        """A last register that is not full: lengths 1, W - 1, W + 1, 2W + 1 and 257 with each
        assignment, the first request non-finite: every line completed as the scalar runner
        completes it, the padding a copy of the first finite request, its results dropped; and a
        segment with no finite request padded with its first."""
        for i, (label, _) in enumerate(self.builds.configs):
            for fmt in ('binary64', 'binary32'):
                code, _, err, rep, _ = self.run_packed(i, lane_stream(self.ks['mul_2_2_full'], fmt, 1, 'w')[1])
                self.assertEqual(code, 0, err)
                w = rep['segments'][0]['lanes']
                for n in sorted({1, w - 1, w + 1, 2 * w + 1, 257} - {0}):
                    for assignment, args in ASSIGNMENTS:
                        with self.subTest(build=label, format=fmt, length=n, lanes=assignment):
                            cases, text = lane_stream(self.ks['mul_2_2_full'], fmt, n, f'pad{n}', first_nonfinite=True)
                            text = '# a comment\n' + text + '# the end\n'
                            code, scalar, err = self.builds.run(i, 'scalar', text)
                            self.assertEqual(code, 0, err)
                            code, out, err, rep, plan = self.run_packed(i, text, *args)
                            self.assertEqual((code, out), (0, scalar), err)
                            seg, = rep['segments']
                            pad = -(-n // w) * w - n
                            self.assertEqual(seg['padding'], pad)
                            self.assertEqual(sum(1 for v in plan.values() if v is None), pad)
                            # Line 1 is the comment, line 2 the non-finite request, line 3 the first
                            # finite one, if there is one.
                            if pad:
                                self.assertEqual((seg['padding_line'], seg['padding_finite']),
                                                 (3, True) if n > 1 else (2, False))
                            else:
                                self.assertIsNone(seg['padding_line'])
                with self.subTest(build=label, format=fmt, nonfinite_only=True):
                    _, text = lane_stream(self.ks['mul_2_2_full'], fmt, w + 1, 'nf', nonfinite_only=True)
                    code, scalar, err = self.builds.run(i, 'scalar', text)
                    code, out, err, rep, _ = self.run_packed(i, text)
                    self.assertEqual((code, out), (0, scalar), err)
                    self.assertEqual((rep['segments'][0]['padding_line'], rep['segments'][0]['padding_finite']),
                                     (1, False))

    def test_segments_and_options(self):
        """Segments end at a comment, another kernel or format and a fold, each with its own plan
        and in the order of the lines; the options are refused when malformed."""
        k = self.ks['mul_2_2_full']
        _, a = lane_stream(k, 'binary64', 300, 'a')
        _, b = lane_stream(k, 'binary32', 300, 'b')
        _, c = lane_stream(self.ks['neg_2'], 'binary64', 5, 'c')
        text = a + b + '# here\n' + a + c + 'sum_1 binary64 lanes:W 0\n' + a
        for i, (label, _) in enumerate(self.builds.configs):
            with self.subTest(build=label):
                code, _, err, rep, _ = self.run_packed(i, 'two_sum binary64 0x1p+0 0x1p+0\n')
                self.assertEqual(code, 0, err)
                t = text.replace('lanes:W', 'lanes:%d' % rep['segments'][0]['lanes'])
                code, scalar, err = self.builds.run(i, 'scalar', t)
                self.assertEqual(code, 0, err)
                code, out, err, rep, plan = self.run_packed(i, t)
                self.assertEqual((code, out), (0, scalar), err)
                self.assertEqual([s['requests'] for s in rep['segments']], [300, 300, 300, 5, 300])
                self.assertEqual({s for s, _, _ in plan}, set(range(5)))
                for args, words in ((['--lanes', 'sideways'], 'permuted or consecutive'),
                                    (['--lane-seed', '-1'], 'decimal integer'), (['--lanes'], 'incomplete'),
                                    (['--frobnicate'], 'unknown')):
                    code, out, err = self.builds.run(i, 'packed', a, args)
                    self.assertEqual((code, out), (2, ''), args)
                    self.assertIn(words, err)


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
            outputs = []
            for assignment, args in ASSIGNMENTS:
                with self.subTest(build=label, lanes=assignment):
                    (status, err), = self.builds.results[i]
                    self.assertEqual(status, 0, err)
                    code, out, err = self.builds.run(i, 'packed', text, args)
                    self.assertEqual(code, 0, err)
                    outputs.append(out)
            with self.subTest(build=label):
                self.assertEqual(len(outputs), 2)
                self.assertEqual(outputs[0], outputs[1], 'the two assignments of the lanes print different lines')
                out = outputs[0]
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
