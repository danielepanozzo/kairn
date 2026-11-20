"""The IEEE-model printer (ieee.py): proofs/gen/IeeeModel.v, IeeeStatements.v and IeeeAudit.v.

The theorems of proofs/theories are about the printed definitions and have the printed statements
as their types (make -C proofs, with its audit); the digests below pin the files that build passed
on, and the tests read what the printer does with the claims. Before the hand-written drafts of
this model were retired, a Rocq file checked by conversion alone that the printed text was the
drafts'."""
import copy
import hashlib
import os
import re
import unittest

import common
from kairn_gen import expr, ieee, ir, rocq, rules

# The variables of the section of IeeeOperations.v, in their order.
SECTION = ['Variable prec emax : Z.', 'Context {prec_gt_0_ : Prec_gt_0 prec}.',
           'Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.',
           'Variable nan_plus : float -> float -> nan_of.', 'Variable nan_minus : float -> float -> nan_of.',
           'Variable nan_opp : float -> nan_of.', 'Variable nan_abs : float -> nan_of.',
           'Variable nan_fma : float -> float -> float -> nan_of.', 'Variable nan_mult : float -> float -> nan_of.',
           'Variable nan_const : nan_of.']

# The kernels that the proofs use as programs, and fast_two_sum_entry, which has an IEEE-model
# statement of the finite domain as fast_two_sum has (two_sum_ord has one too, and is no program:
# it selects).
PROGRAMS = ['fast_two_sum', 'two_prod', 'two_sum', 'add_2_2', 'mul_2_2', 'add_2_1', 'mul_2_1', 'add_fast_2_2',
            'sub_2_2', 'sub_2_1', 'sub_1_2', 'mul_pow2_2', 'fast_two_sum_entry']


def read(rel):
    with open(os.path.join(common.ROOT, rel), encoding='utf-8') as f:
        return f.read()


def definitions(text):
    return re.findall(r'^Definition (\w+)', text, flags=re.M)


class Model(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()
        cls.model = ieee.model(cls.ks)

    def test_the_section_is_that_of_the_draft(self):
        lines = [x for x in self.model.splitlines() if x.startswith(('Variable ', 'Context '))]
        self.assertEqual(lines, SECTION)

    def test_every_kernel(self):
        self.assertEqual(set(ieee.in_model(self.ks)), set(self.ks))
        names = definitions(self.model.split('End IeeeKernels.')[0])
        self.assertEqual([n for n in names if n in self.ks], list(self.ks))     # callees first

    def test_definitions(self):
        m = self.model
        self.assertIn('Definition add_2_1 (x0 x1 a : float) : float * float :=\n'
                      '  let g := guard a in\n'
                      "  let '(sh, sl) := two_sum x0 g in\n"
                      '  let v := add x1 sl in\n'
                      "  let '(z0, z1) := fast_two_sum sh v in\n"
                      '  (z0, z1).', m)
        self.assertIn('Definition ball_add_2 (cx0 cx1 rx cy0 cy1 ry : float) : float * float * float :=\n'
                      "  let '(cz0, cz1) := add_2_2 cx0 cx1 cy0 cy1 in\n"
                      '  let az := abs cz0 in\n'
                      '  let s := add rx ry in\n'
                      '  let t := fma az up_ball_add_2_0 s in\n'
                      '  let rz := fma t up_ball_add_1_1 up_ball_add_1_2 in\n'
                      '  (cz0, cz1, rz).', m)
        self.assertIn('  let r0 := times_inf t in\n  let n := eq r0 r0 in\n  let r1 := if n then pzero else r0 in\n', m)
        self.assertIn('  let cw := if e then k0 else cnan in\n', m)
        self.assertIn('Definition to_nearest_2 (x0 x1 : float) : float :=\n  let t := x0 in\n  t.', m)
        self.assertIn('Definition lt_2_2 (x0 x1 y0 y1 : float) : bool :=', m)
        # Every operation is that of IeeeOperations.v, applied to the variables of this section.
        self.assertIn('Local Notation fms := (IeeeOperations.fms prec emax nan_opp nan_fma).', m)
        self.assertIn('Local Notation guard := (IeeeOperations.guard prec emax nan_plus).', m)

    def test_constants(self):
        # A constant of the format is the number of the format whose value is the constant of the
        # real model: up(EXPR) at emin = 3 - emax - prec, the splitter at prec.
        m = self.model
        self.assertIn('Definition up_ball_add_1_0 : float := const_of (Model.up_ball_add_1_0 (3 - emax - prec) prec).', m)
        self.assertIn('Definition splitter : float := const_of (Model.splitter prec).', m)
        ups = {n for n in definitions(m) if n.startswith('up_')}
        self.assertEqual(ups, {n for n in definitions(read('proofs/gen/Model.v')) if n.startswith('up_')})
        # The thirteen of the Ball cores, and N and P of Milestone 2 (eta / (2u), eta / (2u^2): the
        # scalings of a ball and the directed products); and the fourteen distinct ones of the four
        # bound kernels of the folds (bound_sum_k: 4 and 2; bound_dot_k: 4 and 3, 2, 1 + 2u, 1/4 and
        # 1 shared).
        self.assertEqual(len(ups), 29)
        self.assertIn('Definition up_ball_mul_pow2_1_0 : float := const_of (Model.up_ball_mul_pow2_1_0 (3 - emax - prec) prec).', m)

    def test_programs(self):
        self.assertEqual([k.name for k in ieee.program_kernels(self.ks)], [n for n in self.ks if n in PROGRAMS])
        self.assertEqual(sorted(n[:-len('_prog')] for n in definitions(self.model) if n.endswith('_prog')),
                         sorted(PROGRAMS))
        # The positions: the inputs from 0, then one per instruction, calls inlined.
        self.assertIn('Definition sub_2_1_prog : list instr :=\n'
                      '  [ Ineg 2      (*  3 n *)\n'
                      '  ; Iguard 3    (*  4 z0_g *)\n'
                      '  ; Iadd 0 4    (*  5 z0_sh *)\n', self.model)
        self.assertIsNone(ieee.program(self.ks['ball_add_1'], self.ks))        # abs
        self.assertIsNone(ieee.program(self.ks['split'], self.ks))             # a constant

    def test_operations_the_model_has_not(self):
        # fnma, muladd and mul: a kernel that uses one (a test kernel) is left out, unless it
        # needs an IEEE-model statement.
        tks = common.kernels(common.TEST_KERNELS)
        left_out = set(tks) - set(ieee.in_model(tks))
        self.assertEqual(left_out, {'ops_fused', 'ops_muladd', 'ops_call'})
        self.assertNotIn('ops_fused', ieee.model(tks))
        self.assertEqual(rules.check_all(tks), [])
        ks = copy.deepcopy(dict(tks))
        ks['ops_fused'].ieee = ('spec',)
        errors = [str(e) for e in rules.check_all(ks)]
        self.assertTrue(any('the IEEE model has no fnma' in e for e in errors), errors)


class Statements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()
        cls.text = ieee.statements(cls.ks)

    def test_names(self):
        names = definitions(self.text)
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(names, [n for k in self.ks.values() for n in ieee.statement_names(k)])
        by = {k.name: ieee.statement_names(k) for k in self.ks.values()}
        self.assertEqual(by['add_2_2'], ['add_2_2_ieee_bridge_spec', 'add_2_2_ieee_spec', 'add_2_2_ieee_finite_spec',
                                         'add_2_2_ieee_finite_result_spec'])
        self.assertEqual(by['mul_2_1'], ['mul_2_1_ieee_bridge_spec', 'mul_2_1_ieee_spec', 'mul_2_1_ieee_finite_spec'])
        self.assertEqual(by['fast_two_sum'], ['fast_two_sum_ieee_spec'])
        self.assertEqual(by['two_sum'], [])          # its statement in the draft is written by hand
        self.assertEqual(by['add_2_2_full'], ['add_2_2_full_spec'])
        self.assertEqual(by['ball_neg_2'], ['ball_neg_2_ieee_spec'])
        self.assertEqual(by['neg_2'], ['neg_2_ieee_spec'])
        self.assertEqual(by['make_2'], ['make_2_spec'])
        self.assertEqual(by['ball_add_1'], [])

    def statement(self, name):
        m = re.search(rf'^Definition {name} : Prop :=\n(.*?)\.\n', self.text, flags=re.M | re.S)
        return m.group(1)

    def test_the_full_kernels(self):
        s = self.statement('add_2_1_full_spec')
        self.assertIn('  let t := IeeeOperations.add prec emax nan_plus x0 (IeeeOperations.guard prec emax nan_plus a) in\n', s)
        self.assertIn('  (finite x0 -> finite a ->\n   Rabs (val x0 + val x1) <= bpow radix2 (emax - 2) ->\n'
                      '   Rabs (val a) <= bpow radix2 (emax - 2) ->\n   finite w0) /\\', s)
        self.assertIn('  (~ (finite x0 /\\ finite a) -> canonical_of t w0 w1)', s)
        s = self.statement('mul_pow2_2_full_spec')
        self.assertIn('  canonical_2 x0 x1 ->\n  finite c ->\n  (exists n : Z, val c = bpow radix2 n) ->\n', s)
        self.assertIn('  (~ finite x0 -> canonical_of t w0 w1)', s)
        self.assertIn('Rabs ((val x0 + val x1) * val c) <= bpow radix2 (emax - 1) ->', s)

    def test_represents(self):
        # neg_2 and abs_2 say it next to normalized and an exact error, which it implies.
        self.assertTrue(self.statement('neg_2_ieee_spec').endswith(
            '  canonical_2 z0 z1 /\\\n  xval_2 z0 z1 = xopp (xval_2 x0 x1)'))
        self.assertIn('  (1 <= prec)%Z ->\n', self.statement('abs_2_ieee_spec'))
        s = self.statement('make_2_limbs_spec')
        self.assertNotIn('<= prec)%Z', s)
        self.assertTrue(s.endswith('  xval_2 x0 x1 = xval_2 h l /\\\n  (finite h -> val x0 = val h /\\ val x1 = val l)'))

    def test_balls(self):
        s = self.statement('ball_scale_1_full_spec')
        self.assertIn('   ball_finite_1 cx rx /\\ finite a /\\\n', s)
        self.assertTrue(s.endswith('  (finite a -> forall x : R, in_ball_1 cx rx x -> in_ball_1 cw rw (x * val a))'))
        # B4, between B3 and containment, when the claim has conditions: finite operands (and a
        # finite scalar) under each condition give a finite ball, as F3 is printed for a full
        # kernel. A one-limb name under abs( ) is an application, `val cx`, and is put in
        # parentheses.
        self.assertIn('    Rabs ((x * val a) - val cw) <= val rw)) /\\\n'
                      '  (ball_finite_1 cx rx -> finite a ->\n'
                      '   Rabs (((Rabs (val cx)) + val rx) * val a) <= bpow radix2 (emax - 2) ->\n'
                      '   ball_finite_1 cw rw) /\\\n'
                      '  (finite a -> forall x : R,', s)
        s = self.statement('ball_sub_2_full_spec')
        self.assertIn('  (ball_finite_2 cx0 cx1 rx -> ball_finite_2 cy0 cy1 ry ->\n'
                      '   Rabs (((Rabs ((val cx0 + val cx1) - (val cy0 + val cy1))) + val rx) + val ry)'
                      ' <= bpow radix2 (emax - 2) ->\n'
                      '   ball_finite_2 cw0 cw1 rw) /\\\n'
                      '  (forall x y : R, in_ball_2 cx0 cx1 rx x ->', s)
        s = self.statement('ball_mul_1_full_spec')
        self.assertIn('   Rabs (((Rabs (val cx)) + val rx) * ((Rabs (val cy)) + val ry)) <= bpow radix2 (emax - 4) ->\n'
                      '   ball_finite_1 cw rw) /\\\n', s)
        # Every full Ball kernel has the clause. ball_neg_k, whose claim has no condition, has
        # none: an empty finite_when claims nothing, and prints nothing.
        for name, k in self.ks.items():
            enc = [e for e in k.ensures if e['kind'] == 'encloses']
            if k.extended and enc:
                s = self.statement(ieee.statement_names(k)[0])
                out = ' '.join(k.output_limbs)
                clause = f'->\n   ball_finite_{len(k.outputs[0].limbs)} {out}) /\\\n'
                self.assertEqual(s.count(clause), 1 if enc[0]['finite_when'] else 0, name)
                self.assertEqual(bool(enc[0]['finite_when']), name.endswith('_full'), name)

    def test_the_finite_when_of_a_ball(self):
        # The same kernel with its conditions taken away, and with two of them.
        ks = copy.deepcopy(dict(self.ks))
        k = ks['ball_add_1_full']
        k.ensures[0]['finite_when'] = []
        without = '\n'.join(ieee.kernel_statements(k, ks)[0])
        self.assertNotIn('->\n   ball_finite_1 cw rw)', without)
        self.assertIn('  (ball_finite_1 cw rw ->\n', without)                  # B3 is still there
        self.assertIn('    Rabs ((x + y) - val cw) <= val rw)) /\\\n  (forall x y : R, in_ball_1 cx rx x ->', without)
        k.ensures[0]['finite_when'] = [{'abs_le': 'cx', 'exp': -3}, {'abs_le': 'rx+ry', 'exp': 0}]
        both = '\n'.join(ieee.kernel_statements(k, ks)[0])
        self.assertIn('  (ball_finite_1 cx rx -> ball_finite_1 cy ry ->\n'
                      '   Rabs (val cx) <= bpow radix2 (emax - 3) ->\n'
                      '   Rabs (val rx + val ry) <= bpow radix2 emax ->\n'
                      '   ball_finite_1 cw rw) /\\\n'
                      '  (forall x y : R, in_ball_1 cx rx x ->', both)

    def test_abs_of_a_name_in_a_condition(self):
        # rocq._term puts the operand of Rabs in parentheses when it is an application: `val a`
        # for a one-limb name of the IEEE model. A 2-limb name, a sum in parentheses, and the
        # names of the real model, which are single words, are printed as before.
        tree = expr.parse('abs(a)*abs(x)+abs(a+x)')
        ieee_names = {'a': 'val a', 'x': '(val x0 + val x1)'}
        self.assertEqual(rocq._term(tree, ieee_names.get),
                         '(((Rabs (val a)) * (Rabs (val x0 + val x1))) + (Rabs (val a + (val x0 + val x1))))')
        real_names = {'a': 'a', 'x': '(x0 + x1)'}
        self.assertEqual(rocq._term(tree, real_names.get),
                         '(((Rabs a) * (Rabs (x0 + x1))) + (Rabs (a + (x0 + x1))))')

    def test_milestone2(self):
        # The claims of Milestone 2 over extended reals (IeeeVocabulary.v: xsucc, xpred, xrd, xru,
        # xadd, xmul), and the exactness of a full scaling of a ball, between B3 and B4.
        self.assertTrue(self.statement('next_up_ieee_spec').endswith('  xval r = xsucc prec emax (xval a)'))
        self.assertTrue(self.statement('next_down_ieee_spec').endswith('  xval r = xpred prec emax (xval a)'))
        self.assertTrue(self.statement('add_down_1_ieee_spec').endswith(
            '  xval r = xrd prec emax (xadd (xval a) (xval b))'))
        self.assertTrue(self.statement('sub_up_1_ieee_spec').endswith(
            '  xval r = xru prec emax (xadd (xval a) (xopp (xval b)))'))
        s = self.statement('mul_down_1_ieee_spec')
        self.assertIn('  (finite a /\\ finite b ->\n   xle (xval r) (xmul (xval a) (xval b)) = true /\\ '
                      'xle (xpred prec emax (xrd prec emax (xmul (xval a) (xval b)))) (xval r) = true) /\\\n'
                      '  (~ (finite a /\\ finite b) -> xval r = (xmul (xval a) (xval b))) /\\\n', s)
        self.assertTrue(s.endswith('<= Rabs (val a * val b)) ->\n   xval r = xrd prec emax (xmul (xval a) (xval b)))'))
        s = self.statement('ball_mul_pow2_1_full_spec')
        b3 = s.index('  (ball_finite_1 cw rw ->\n   ball_finite_1 cx rx')
        exact = s.index('  (ball_finite_1 cw rw -> ((val cx * val c) = 0 \\/ (eta (ieee_emin prec emax) / (2 * u prec)) '
                        '< Rabs (val cx * val c)) /\\ ((val rx * val c) = 0 \\/')
        b4 = s.index('  (ball_finite_1 cx rx -> finite c ->\n   Rabs (((Rabs (val cx)) + val rx) * val c)')
        self.assertLess(b3, exact)
        self.assertLess(exact, b4)
        self.assertIn('   forall s_ : R, Rabs (s_ - val cw) <= val rw ->\n'
                      '   exists x : R, Rabs (x - val cx) <= val rx /\\ s_ = (x * val c)) /\\\n', s)
        # The rounding of a value of one operand is printed as before.
        self.assertTrue(self.statement('to_down_2_ieee_spec').endswith(
            '  xval t = xround emax (RD (ieee_emin prec emax) prec) (xval_2 x0 x1)'))

    def test_constructors(self):
        s = self.statement('ball_make_1_spec')
        self.assertIn('ball_finite_1 cw rw /\\ val cw = val c /\\ val rw = val r', s)
        s = self.statement('ball_make_2_spec')
        self.assertIn('ball_finite_2 cw0 cw1 rw /\\ cw0 = c0 /\\ cw1 = c1 /\\ val rw = val r', s)

    def test_the_finite_domain(self):
        s = self.statement('sub_1_2_ieee_finite_result_spec')
        self.assertIn('  Rabs (val a - (val y0 + val y1)) <= bpow radix2 (emax - 2) ->\n', s)
        self.assertIn('IeeeModel.sub_1_2_prog [a; y0; y1]', s)
        s = self.statement('add_2_2_ieee_bridge_spec')
        self.assertIn('  = add_2_2 (ieee_emin prec emax) prec tie_even (val x0) (val x1) (val y0) (val y1)', s)

    def test_audit(self):
        text = ieee.audit(self.ks)
        # Every kernel of the extended domain names its theorem.
        self.assertEqual(text.count('Print Assumptions'), 54)
        self.assertIn('Definition add_2_2_full_audit : add_2_2_full_spec := add_2_2_full_correct.\n'
                      'Print Assumptions add_2_2_full_correct.', text)
        self.assertIn('From Kairn Require Import IeeeFull.', text)


class CheckedFiles(unittest.TestCase):
    # The generated files that make -C proofs passed on: every theorem of the IEEE model is about
    # these definitions and has one of these statements as its type. A change of either file needs
    # that build again, and new digests here.
    # With the kernels of wave 1 of Milestone 2, whose definitions and statements were added
    # (every earlier one is the same, byte for byte) and whose statuses the statements file
    # prints: proved, the two full scalings of a ball included (the only change of the file when
    # their proofs landed is those two words). Then the kernels of the folds' stage (unverified):
    # their definitions, the constants of the bound kernels, and the statements of the two
    # finishes were added, and every earlier one is the same, byte for byte.
    DIGESTS = {'proofs/gen/IeeeModel.v': '9a2adeb31a19e09f9d9cc8b0cc1e27dc76080535bf4275445f59b3098b42aee6',
               'proofs/gen/IeeeStatements.v': '743d04d20c50b4cb1e58383045466e514b9b6e23463239c470d13ca330ad941e'}

    def test_the_checked_files(self):
        for path, digest in self.DIGESTS.items():
            text = read(path)
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), digest, path)


class Fields(unittest.TestCase):
    HEAD = '''
kernel:  k
input:   x = x0 x1
input:   a
output:  z = z0 z1
value:   x+a
requires: normalized x
ensures: normalized z
ensures: error z R c=2 k=2 t=0
status:  unverified
{fields}
(sh, sl) = two_sum(x0, a)
v        = add(x1, sl)
(z0, z1) = fast_two_sum(sh, v)
'''

    def errors(self, fields):
        ks = dict(common.kernels())
        k = ir.parse_kernel(self.HEAD.format(fields=fields), 'k.kernel')
        ks['k'] = k
        return k, [str(e) for e in rules.check_all(ir.ordered(ks)) if e.kernel == 'k']

    def test_accepted_and_parsed(self):
        k, errors = self.errors('ieee: spec bridge\nieee_finite: abs_le(x0,-2);abs_le(a, -2)\n'
                                'ieee_finite_result: abs_le(x+a,-2)')
        self.assertEqual(errors, [])
        self.assertEqual(k.ieee, ('bridge', 'spec'))
        self.assertEqual(k.ieee_finite, [{'abs_le': 'x0', 'exp': -2}, {'abs_le': 'a', 'exp': -2}])
        self.assertEqual(ieee.statement_names(k), ['k_ieee_bridge_spec', 'k_ieee_spec', 'k_ieee_finite_spec',
                                                   'k_ieee_finite_result_spec'])

    def test_refused(self):
        with self.assertRaises(ir.DescriptionError):
            self.errors('ieee: spec proof')
        _, errors = self.errors('ieee_finite: abs_le(b,-2)')
        self.assertTrue(any('unknown name b' in e for e in errors), errors)
        _, errors = self.errors('domain: extended\nieee: spec')
        self.assertTrue(any('about a kernel of the finite domain' in e for e in errors), errors)

    def test_groups_the_vocabulary_has_no_word_for(self):
        # canonical_2, xval_2, ball_2 are about two limbs: a 4-limb output that claims represents
        # has no IEEE-model statement, and is refused.
        ks = copy.deepcopy(dict(common.kernels(common.TEST_KERNELS)))
        k = ks['ops_special']
        k.outputs = [ir.Group('x', ('x0', 'x1', 'x2', 'x3'))]
        errors = [str(e) for e in rules.check_all(ks) if e.kernel == 'ops_special']
        self.assertTrue(any('x has 4 limbs, and the IEEE-model statements have words for 2' in e for e in errors),
                        errors)


if __name__ == '__main__':
    unittest.main()
