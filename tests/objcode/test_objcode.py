#!/usr/bin/env python3
"""The object-code check's own tests (objcode.py, disasm.py), on stored disassemblies: run on every
platform, with no compiler and no disassembler.

    python3 tests/objcode/test_objcode.py

samples/ holds excerpts of real disassemblies of unit.cpp and fixture.cpp, each a few kernels'
functions and every function they call, cut out of the whole output with nothing changed but the
object file's name in the first lines:

    gnu-x86-64-O0.txt, -O2.txt, -fixture.txt   GNU objdump 2.42, ELF x86-64, GCC 13 (-O2: the
                                                fix-ups as calls, with GCC's F.cold parts; fixture
                                                at -O2 -ffp-contract=fast)
    gnu-aarch64-O0.txt, -O2.txt, -fixture.txt   GNU objdump 2.42, ELF AArch64, GCC 13
    llvm-macho-arm64.txt                        LLVM objdump of Apple clang 21, Mach-O arm64, -O2
    llvm-macho-arm64-O0.txt                     the same at -O0 -ffp-contract=fast: a packed kernel
                                                whose frame is above a page, which calls Darwin's
                                                stack probe through the GOT
    llvm-coff-x64.txt                           LLVM objdump 21, COFF x64, an object of MSVC 19.52 at
                                                /Od (the format of the objects of clang-cl)
    dumpbin-x64-Od.txt, -O2.txt                 dumpbin of MSVC 19.52, COFF x64

Each sample's functions are checked against what the real check found in the whole object, and
against gen/objcode.json by the check's rule.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import disasm  # noqa: E402
import objcode  # noqa: E402

SAMPLES = os.path.join(HERE, 'samples')
EXPECTED, LIMB_TYPES = objcode.load_expected(os.path.join(objcode.ROOT, 'gen', 'objcode.json'))


def program(name):
    with open(os.path.join(SAMPLES, name), encoding='utf-8') as f:
        return disasm.Program(f.read())


# sample: [(function, kernel, form, limb type, fused, multiplications, calls other functions)]
FOUND = {
    'gnu-x86-64-O0.txt': [
        ('kairn_objcode_scalar_double_mul_1_1', 'mul_1_1', 'scalar', 'double', 1, 0, False),
        ('kairn_objcode_scalar_float_ball_add_1', 'ball_add_1', 'scalar', 'float', 2, 0, True),
        ('kairn_objcode_packed_double_mul_pow2_2', 'mul_pow2_2', 'packed', 'double', 2, 0, False)],
    'gnu-x86-64-O2.txt': [
        ('kairn_objcode_scalar_double_mul_2_2_full', 'mul_2_2_full', 'scalar_call', 'double', 6, 1, True),
        ('kairn_objcode_scalar_double_two_prod', 'two_prod', 'scalar_call', 'double', 2, 0, False)],
    'gnu-aarch64-O0.txt': [
        ('kairn_objcode_scalar_double_ball_add_1', 'ball_add_1', 'scalar', 'double', 2, 0, True),
        ('kairn_objcode_packed_float_rmul', 'rmul', 'packed', 'float', 1, 0, False),
        ('kairn_objcode_packed_double_abs_2', 'abs_2', 'packed', 'double', 0, 0, False)],
    'gnu-aarch64-O2.txt': [
        ('kairn_objcode_scalar_double_mul_2_2_full', 'mul_2_2_full', 'scalar_call', 'double', 6, 1, True),
        ('kairn_objcode_scalar_float_to_up_2', 'to_up_2', 'scalar_call', 'float', 0, 0, False)],
    'llvm-macho-arm64.txt': [
        ('kairn_objcode_scalar_double_add_1_1', 'add_1_1', 'scalar_call', 'double', 0, 0, False),
        ('kairn_objcode_scalar_double_mul_2_2_full', 'mul_2_2_full', 'scalar_call', 'double', 6, 1, True),
        ('kairn_objcode_packed_double_mul_2_2_full', 'mul_2_2_full', 'packed', 'double', 5, 1, False),
        ('kairn_objcode_packed_float_abs_2', 'abs_2', 'packed', 'float', 0, 0, False)],
    'llvm-macho-arm64-O0.txt': [
        ('kairn_objcode_packed_double_ball_mul_pow2_1', 'ball_mul_pow2_1', 'packed', 'double', 2, 0, False)],
    'llvm-coff-x64.txt': [
        # /Od: the kernel and fma_rn are functions of their own, and the branch that only constant
        # evaluation takes is compiled: Dekker's product, seven plain multiplications.
        ('kairn_objcode_scalar_double_two_prod', 'two_prod', 'scalar', 'double', 2, 7, True),
        ('kairn_objcode_scalar_float_mul_1_1', 'mul_1_1', 'scalar', 'float', 1, 0, True)],
    'dumpbin-x64-Od.txt': [
        ('kairn_objcode_scalar_double_two_prod', 'two_prod', 'scalar', 'double', 2, 7, True)],
    'dumpbin-x64-O2.txt': [
        ('kairn_objcode_scalar_double_mul_2_2_full', 'mul_2_2_full', 'scalar', 'double', 5, 1, False),
        ('kairn_objcode_packed_float_mul_2_2_full', 'mul_2_2_full', 'packed', 'float', 5, 1, False)],
}
FORMS = {'gnu-x86-64-O0.txt': 'scalar', 'gnu-x86-64-O2.txt': 'scalar_call', 'gnu-aarch64-O0.txt': 'scalar',
         'gnu-aarch64-O2.txt': 'scalar_call', 'llvm-macho-arm64.txt': 'scalar_call',
         'llvm-macho-arm64-O0.txt': 'scalar_call',
         'llvm-coff-x64.txt': 'scalar', 'dumpbin-x64-Od.txt': 'scalar', 'dumpbin-x64-O2.txt': 'scalar'}
FIXTURES = {
    'gnu-x86-64-fixture.txt': ['kairn_objcode_fixture_scalar_double_statements',
                               'kairn_objcode_fixture_scalar_float_expression',
                               'kairn_objcode_fixture_packed_double_statements'],
    'gnu-aarch64-fixture.txt': ['kairn_objcode_fixture_scalar_double_statements',
                                'kairn_objcode_fixture_packed_float_statements'],
}


class Samples(unittest.TestCase):
    def test_every_sample_is_used(self):
        self.assertEqual(sorted(os.listdir(SAMPLES)), sorted(list(FOUND) + list(FIXTURES)))

    def test_counts_of_each_format(self):
        for sample, rows in FOUND.items():
            p = program(sample)
            for name, kernel, form, t, fused, muls, calls in rows:
                with self.subTest(sample=sample, function=name):
                    f = p.find(name)
                    self.assertIsNotNone(f)
                    c = p.count(f)
                    self.assertEqual((len(c.fma), len(c.mul)), (fused, muls))
                    self.assertEqual(bool(c.calls), calls)
                    self.assertEqual((c.external, c.unknown), ([], []))

    def test_the_samples_pass_the_rule(self):
        for sample, rows in FOUND.items():
            p = program(sample)
            self.assertEqual(objcode.unit_form(p), FORMS[sample], sample)
            for name, kernel, form, t, *_ in rows:
                with self.subTest(sample=sample, function=name):
                    text, _ = objcode.judge(p.count(p.find(name)), EXPECTED[kernel][form][t])
                    self.assertIsNone(text)

    def test_a_wrong_count_fails(self):
        p = program('dumpbin-x64-O2.txt')
        e = dict(EXPECTED['mul_2_2_full']['scalar']['double'])
        e['fma'] += 1
        e['fma_distinct'] += 1
        text, _ = objcode.judge(p.count(p.find('kairn_objcode_scalar_double_mul_2_2_full')), e)
        self.assertIn('5 fused multiply-adds, expected 7 or 6 (identical ones once)', text)
        self.assertIn('vfmadd', text)       # what was found is listed
        e = dict(EXPECTED['mul_2_2_full']['scalar']['double'])
        e['mul'] = e['mul_distinct'] = 0
        text, _ = objcode.judge(p.count(p.find('kairn_objcode_scalar_double_mul_2_2_full')), e)
        self.assertIn('1 plain multiplications, expected 0', text)
        self.assertIn('vmulsd', text)

    def test_a_contraction_fails(self):
        for sample, names in FIXTURES.items():
            p = program(sample)
            for name in names:
                with self.subTest(sample=sample, function=name):
                    c = p.count(p.find(name))
                    self.assertEqual((len(c.fma), len(c.mul)), (1, 0))
                    text, _ = objcode.judge(c, objcode.FIXTURE_COUNTS)
                    self.assertIn('1 fused multiply-adds, expected 0', text)
                    self.assertIn('0 plain multiplications, expected 1', text)

    def test_the_kernels_without_contraction_pass_and_with_it_fail(self):
        # mul_2_2_full of the -O2 sample, with one of its FMAs counted as the product and the sum
        # it would be without the opaque product: a multiplication more, an FMA fewer.
        p = program('gnu-x86-64-O2.txt')
        c = p.count(p.find('kairn_objcode_scalar_double_mul_2_2_full'))
        e = EXPECTED['mul_2_2_full']['scalar_call']['double']
        self.assertIsNone(objcode.judge(c, e)[0])
        c.fma.pop()
        c.mul.append(('f', 'vmulsd'))
        self.assertIsNotNone(objcode.judge(c, e)[0])

    def test_cold_parts_and_relocations_against_a_section(self):
        # GCC moved the call of the fix-up to F.cold, and jumps there through a relocation
        # against .text.unlikely: the part is F's, its call is followed.
        p = program('gnu-x86-64-O2.txt')
        f = p.find('kairn_objcode_scalar_double_mul_2_2_full')
        cold = p.find('kairn_objcode_scalar_double_mul_2_2_full.cold')
        self.assertIs(p.owner(cold), f)
        self.assertEqual(p.count(f).calls, ['_ZN5kairn3gen5fixup12mul_2_2_fullEddddb'])
        jump = next(i for i in f.insns if i.relocs and i.mnemonic.startswith('j'))
        self.assertEqual(p.target(f, jump), ('internal', None))

    def test_aliases_and_local_labels(self):
        # Mach-O: ltmp0 at the address of the first function; COFF: $LN and .text$mn labels at
        # the address of every function, in sections that all have one name.
        p = program('llvm-macho-arm64.txt')
        self.assertIsNotNone(p.find('kairn_objcode_fixups_call'))
        self.assertNotIn('ltmp0', p.by_name)
        p = program('llvm-coff-x64.txt')
        self.assertFalse([n for n in p.by_name if n.startswith(('$LN', '.text'))])
        self.assertGreater(len(p.segments['.text$mn']), 1)

    def test_external_calls(self):
        # The stack protector's routine may be called (Ubuntu's GCC at -O0); nothing else.
        p = program('gnu-x86-64-O0.txt')
        f = p.find('kairn_objcode_scalar_float_ball_add_1')
        self.assertTrue(any(r.startswith('__stack_chk_fail') for i in f.insns for r in i.relocs))
        self.assertEqual(p.count(f).external, [])
        self.assertTrue(disasm.allowed_external('___stack_chk_fail'))
        self.assertFalse(disasm.allowed_external('fma'))
        # Darwin's stack probe, called through a register loaded from the GOT (adrp, ldr, blr x16):
        # the call is to that symbol, and the probe computes nothing.
        p = program('llvm-macho-arm64-O0.txt')
        f = p.find('kairn_objcode_packed_double_ball_mul_pow2_1')
        call = next(i for i in f.insns if i.mnemonic == 'blr')
        self.assertEqual(p.target(f, call), ('external', '___chkstk_darwin'))
        self.assertTrue(disasm.allowed_external('___chkstk_darwin'))
        self.assertEqual((p.count(f).external, p.count(f).unknown), ([], []))
        # A register written after its load, or never loaded from the GOT, leaves the call indirect.
        for between in ('   8:\tmov\tx16, x0\n', ''):
            text = ('Disassembly of section __TEXT,__text:\n\n0000000000000000 <_f>:\n'
                    '   0:\tadrp\tx16, 0x0 <_f>\n\t\t0000000000000000:  ARM64_RELOC_GOT_LOAD_PAGE21\t___chkstk_darwin\n'
                    + ('   4:\tldr\tx16, [x16]\n\t\t0000000000000004:  ARM64_RELOC_GOT_LOAD_PAGEOFF12\t___chkstk_darwin\n'
                       if between else '   4:\tldr\tx16, [x16]\n')
                    + between + '   c:\tblr\tx16\n  10:\tret\n')
            q = disasm.Program(text)
            self.assertEqual(q.count(q.find('_f')).unknown, [('_f', 'blr x16')], between)

    def test_constant_evaluation_branch(self):
        p = program('dumpbin-x64-Od.txt')
        c = p.count(p.find('kairn_objcode_scalar_double_two_prod'))
        e = EXPECTED['two_prod']['scalar']['double']
        self.assertEqual((e['mul'], e['consteval_mul']), (0, 7))
        text, how = objcode.judge(c, e)
        self.assertIsNone(text)
        self.assertEqual(how, {'consteval'})
        # The packed code has no such branch: the same seven multiplications there fail.
        self.assertIsNotNone(objcode.judge(c, EXPECTED['two_prod']['packed']['double'])[0])


class Rule(unittest.TestCase):
    def count(self, fused, muls, external=(), unknown=()):
        c = disasm.Count()
        c.fma = [('f', 'fma')] * fused
        c.mul = [('f', 'mul')] * muls
        c.external = list(external)
        c.unknown = list(unknown)
        return c

    def counts(self, **kw):
        e = dict(fma=6, fma_distinct=5, mul=1, mul_distinct=1, consteval_mul=0, muladd=0)
        e.update(kw)
        return e

    def test_each_or_distinct(self):
        e = self.counts()
        self.assertEqual(objcode.judge(self.count(6, 1), e), (None, {'each'}))
        self.assertEqual(objcode.judge(self.count(5, 1), e), (None, {'distinct'}))
        for fused in (4, 7):
            self.assertIn(f'{fused} fused multiply-adds, expected 6 or 5 (identical ones once)',
                          objcode.judge(self.count(fused, 1), e)[0])

    def test_multiplications(self):
        e = self.counts(consteval_mul=7)
        self.assertIsNone(objcode.judge(self.count(6, 1), e)[0])
        self.assertEqual(objcode.judge(self.count(6, 8), e), (None, {'each', 'consteval'}))
        for muls in (0, 2, 7, 9):
            self.assertIn(f'{muls} plain multiplications, expected 1 or 8 (with the branch of constant '
                          f'evaluation)', objcode.judge(self.count(6, muls), e)[0])

    def test_what_cannot_be_counted_fails(self):
        e = self.counts()
        self.assertIn('calls fma outside the object', objcode.judge(self.count(6, 1, [('f', 'fma')]), e)[0])
        self.assertIn('not known', objcode.judge(self.count(6, 1, unknown=[('f', 'call *%rax')]), e)[0])
        self.assertIn('no rule yet', objcode.judge(self.count(6, 1), self.counts(muladd=1))[0])

    def test_recursion(self):
        p = disasm.Program('Disassembly of section .text:\n\n0000000000000000 <a>:\n'
                           '   0:\tcall   6 <b>\n   5:\tret\n\n0000000000000006 <b>:\n'
                           '   6:\tjmp    0 <a>\n')
        with self.assertRaises(ValueError):
            p.count(p.find('a'))


class Mnemonics(unittest.TestCase):
    def test_kinds(self):
        table = {
            'fma': ['vfmadd231sd', 'vfmadd132ss', 'vfmsub213pd', 'vfnmadd231ps', 'vfnmsub132sd',
                    'vfmaddsub231pd', 'fmadd', 'fmsub', 'fnmadd', 'fnmsub', 'fmla', 'fmls', 'fmla.2d',
                    'fmls.4s'],
            'mul': ['mulsd', 'vmulsd', 'vmulpd', 'mulps', 'vmulss', 'fmul', 'fnmul', 'fmulx',
                    'fmul.2d'],
            'call': ['call', 'callq', 'bl', 'blr'],
            'jump': ['jmp', 'jbe', 'jne', 'jp', 'b', 'b.ge', 'b.eq', 'cbz', 'cbnz', 'tbz', 'tbnz', 'br'],
            None: ['madd', 'msub', 'mul', 'imul', 'mulx', 'vpmuludq', 'pmulld', 'bit', 'bif', 'bsl',
                   'bic', 'vaddsd', 'fadd', 'fadd.2d', 'vblendvpd', 'vandpd', 'fcsel', 'ret', 'movi.2d'],
        }
        for kind, mnemonics in table.items():
            for m in mnemonics:
                with self.subTest(mnemonic=m):
                    self.assertEqual(disasm.kind(m), kind)

    def test_prefixes(self):
        self.assertEqual(disasm._split('notrack jmp *%rax'), ('jmp', '*%rax'))
        self.assertEqual(disasm._split('{vex} vfmadd231sd %xmm1,%xmm2,%xmm3'),
                         ('vfmadd231sd', '%xmm1,%xmm2,%xmm3'))


class Upward(unittest.TestCase):
    """The rule of the round-up interval (objcode.py --upward, judge_upward) and its expectations."""

    def count(self, muls=0, maxima=0, fused=0, fmax=0, negmul=0, calls=()):
        c = disasm.Count()
        c.mul = [('f', 'mul')] * muls
        c.maximum = [('f', 'maxpd')] * maxima
        c.fma = [('f', 'fma')] * fused
        c.fmax = [('f', 'fmax')] * fmax
        c.negmul = [('f', 'fnmul')] * negmul
        c.calls = list(calls)
        return c

    def test_the_mnemonics(self):
        for m, want in (('maxpd', True), ('vmaxpd', True), ('vmaxps', True), ('fmaxnm', True), ('fmaxnm.2d', True),
                        ('maxsd', False), ('vmaxsd', False), ('fmax', False), ('fminnm', False)):
            self.assertEqual(bool(disasm.MAXIMUM.match(m)), want, m)
        for m, want in (('fmax', True), ('fmax.2d', True), ('fmaxnm', False), ('fmaxnm.2s', False)):
            self.assertEqual(bool(disasm.NAN_MAXIMUM.match(m)), want, m)
        self.assertTrue(disasm.NEGATED_MUL.match('fnmul.2d') and disasm.NEGATED_MUL.match('fnmul'))
        self.assertFalse(disasm.NEGATED_MUL.match('fmul'))
        p = disasm.Program('Disassembly of section .text:\n\n0000000000000000 <a>:\n'
                           '   0:\tfmaxnm.2d\tv0, v1, v2\n   4:\tfnmul\td0, d1, d2\n   8:\tfmax\td0, d0, d1\n'
                           '   c:\tret\n')
        c = p.count(p.find('a'))
        self.assertEqual((len(c.maximum), len(c.negmul), len(c.fmax), len(c.mul)), (1, 1, 1, 1))

    def test_one_function(self):
        e = {'mul': 4, 'max': 3}
        self.assertIsNone(objcode.judge_upward(self.count(4, 3), e, False))
        self.assertIn('5 multiplications, expected 4', objcode.judge_upward(self.count(5, 3), e, False))
        self.assertIn('2 maxima, expected 3', objcode.judge_upward(self.count(4, 2), e, False))
        self.assertIn('fused multiply-adds', objcode.judge_upward(self.count(4, 3, fused=1), e, False))
        self.assertIn('negated multiplications', objcode.judge_upward(self.count(4, 3, negmul=1), e, False))
        self.assertIn('fmax', objcode.judge_upward(self.count(4, 3, fmax=1), e, False))
        # The two-number form does not count its maxima.
        self.assertIsNone(objcode.judge_upward(self.count(8, 7), {'mul': 8, 'max': None}, False))

    def test_calls(self):
        e = {'mul': 0, 'max': 0}
        kernel = '__ZN5kairn3gen6upward12_GLOBAL__N_112upward_add_1EDv2_dS2_RS2_'
        arrays = '__ZN5kairn3gen6upward12_GLOBAL__N_119upward_add_1_arraysEPKdS4_S4_S4_PdS5_m'
        msvc = '?upward_hull_1@upward@gen@kairn@@YAXT__m128d@@0AEAT1@@Z'
        self.assertIn('a kernel is not inlined', objcode.judge_upward(self.count(calls=[kernel]), e, False))
        self.assertIn('a kernel is not inlined', objcode.judge_upward(self.count(calls=[msvc]), e, False))
        self.assertIsNone(objcode.judge_upward(self.count(calls=[kernel]), e, True))
        self.assertIsNone(objcode.judge_upward(self.count(calls=[arrays, '__ZNSt3__18bit_castB9']), e, False))

    def test_parts(self):
        parts = [{'part': 'packed', 'least': 1, 'mul': 4, 'max': 3}, {'part': 'tail', 'least': 1, 'mul': 4, 'max': 3}]
        for muls, maxima in ((8, 6), (12, 9), (16, 12)):
            self.assertIsNone(objcode.judge_upward(self.count(muls, maxima), parts, False))
        self.assertIn('which no number of copies', objcode.judge_upward(self.count(4, 3), parts, False))
        self.assertIn('which no number of copies', objcode.judge_upward(self.count(9, 6), parts, False))

    def test_the_expectations(self):
        expected = objcode.load_upward_expected(os.path.join(objcode.ROOT, 'gen', 'objcode.json'))
        self.assertEqual(len(expected), 24)
        arrays = {'upward_add_1', 'upward_sub_1', 'upward_mul_1', 'upward_neg_1', 'upward_add_num_1', 'upward_mul_num_1'}
        for k, forms in expected.items():
            want = {'sse2', 'neon', 'numbers'} | ({'avx2', 'neon_arrays'} if k in arrays else set())
            self.assertEqual(set(forms), want, k)
        self.assertEqual(expected['upward_mul_1']['sse2']['double'], {'mul': 4, 'max': 3})
        self.assertEqual(expected['upward_mul_1']['numbers']['float'], {'mul': 8, 'max': None})
        self.assertEqual(expected['upward_mul_num_1']['avx2']['double'],
                         [{'part': 'packed', 'least': 1, 'mul': 4, 'max': 2},
                          {'part': 'tail', 'least': 1, 'mul': 2, 'max': 1}])
        for family in ('gnu', 'msvc', 'clang-cl'):
            full = objcode.upward_configurations(family, 'full')
            for c in objcode.upward_configurations(family, 'quick'):
                self.assertIn(c, full, (family, c))


class Matrix(unittest.TestCase):
    def test_tiers(self):
        for family, size in (('gnu', 24), ('msvc', 9), ('clang-cl', 24)):
            full = objcode.configurations(family, 'full')
            self.assertEqual(len(full), size)
            keys = {c[:3] for c in full}
            for c in objcode.configurations(family, 'quick'):
                self.assertIn(c[:3], keys, (family, c))

    def test_a_missing_disassembler_fails(self):
        with self.assertRaises(objcode.Failure) as e:
            objcode.find_disassembler(os.path.join(SAMPLES, 'no-such-objdump'), 'gnu', 'c++')
        self.assertIn('no disassembler', str(e.exception))


if __name__ == '__main__':
    unittest.main()
