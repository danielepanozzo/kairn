"""The IEEE-model printer (ieee.py): proofs/gen/IeeeModel.v, IeeeStatements.v and IeeeAudit.v.

The theorems of proofs/theories are about the printed definitions and have the printed statements
as their types (make -C proofs, with its audit); the digests below pin the files that build passed
on, and the tests read what the printer does with the claims. Before the hand-written drafts of
this model were retired, a Rocq file checked by conversion alone that the printed text was the
drafts'."""
import copy
import hashlib
import json
import os
import re
import unittest

import common
from kairn_gen import claims, expr, ieee, ir, rocq, rules

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
        self.assertIn('  let cw := if ok then k0 else cnan in\n', m)
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
        # Those of Model.v, and the two that only a kernel without a real-model statement uses (the
        # halving and the doubling of ball_from_interval_2, Milestone 2), defined here from their
        # expressions, as Model.v would define them.
        only_here = {'up_ball_from_interval_2_0', 'up_ball_from_interval_2_1'}
        self.assertEqual(ups, {n for n in definitions(read('proofs/gen/Model.v')) if n.startswith('up_')} | only_here)
        self.assertIn('Definition up_ball_from_interval_2_0 : float := const_of (round radix2 '
                      '(FLT_exp (3 - emax - prec) prec) Zceil (1 / 2)).', m)
        self.assertIn('Definition up_ball_from_interval_2_1 : float := const_of (round radix2 '
                      '(FLT_exp (3 - emax - prec) prec) Zceil 2).', m)
        # The thirteen of the Ball cores, N and P of Milestone 2 (eta / (2u), eta / (2u^2): the
        # scalings of a ball and the directed products), and the two above.
        self.assertEqual(len(ups), 17)
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

    def test_the_interval_kernels(self):
        # Statements of Milestone 2's interval work in their shapes (architecture.md, "Claims of the
        # interval kernels"), and the entry of ball_from_interval_2 that architecture.md writes out.
        ks = self.ks
        entry = claims.kernel_claims(ks['ball_from_interval_2'], ks)
        self.assertTrue(entry['ieee_only'])
        with open(os.path.join(common.ROOT, 'docs', 'developer', 'architecture.md'), encoding='utf-8') as f:
            self.assertIn(json.dumps(entry['ensures'][0]).replace('\n', ' '), ' '.join(f.read().split('\n')))
        text = ieee.statements(ks)

        def spec(name, statements=text):
            return re.search(rf'^Definition {name}_spec : Prop :=\n(.*?)\.\n', statements, flags=re.M | re.S).group(1)
        # I4 of the product in the shape of interval_mul_1_tight_range, product_large unfolded.
        s = spec('interval_mul_1')
        self.assertIn('   xle (xpred prec emax (xrd prec emax lo)) (xval zl) = true /\\\n'
                      '   xle (xval zl) (xrd prec emax lo) = true /\\\n', s)
        self.assertIn('   ((finite xl /\\ finite yl ->\n'
                      '    val xl * val yl = 0 \\/ bpow radix2 (2 * prec - 1) * eta (ieee_emin prec emax) '
                      '<= Rabs (val xl * val yl)) ->\n', s)
        # I4 of the sum of two limbs: the outward constants of add_2_2 in the forms of Directed2.v,
        # and the bound itself for a zero bound of the exact range.
        s = spec('interval_add_2')
        self.assertIn('   (((val xl0 + val xl1) + (val yl0 + val yl1)) = 0 -> xval_2 zl0 zl1 = XFin lo) /\\\n', s)
        self.assertIn('((((/ 2) * up_ball_add_1_1 (ieee_emin prec emax) prec) * eta (ieee_emin prec emax))', s)
        # mul_dir_2_2 in the real model: both bounds, each outward of the product.
        s = spec('mul_dir_2_2', rocq.statements(ks))
        self.assertIn("  let '(l0, l1, h0, h1) := mul_dir_2_2 emin prec tie_even x0 x1 y0 y1 in\n", s)
        self.assertIn('  (l0 + l1) <= ((x0 + x1) * (y0 + y1)) /\\\n', s)
        self.assertIn('  ((x0 + x1) * (y0 + y1)) <= (h0 + h1) /\\\n', s)
        s = spec('ball_from_interval_2')
        self.assertIn('  ball_2 cw0 cw1 rw /\\\n'
                      '  (xnonempty (xval lo) (xval hi) -> finite lo -> finite hi ->\n'
                      '   ball_finite_2 cw0 cw1 rw /\\\n'
                      '   (forall x : R, val lo <= x <= val hi -> in_ball_2 cw0 cw1 rw x)) /\\\n'
                      '  (xnonempty (xval lo) (xval hi) -> finite lo -> finite hi -> '
                      'fmt (ieee_emin prec emax) prec (val lo / 2) -> fmt (ieee_emin prec emax) prec (val hi / 2) ->\n'
                      '   (val cw0 + val cw1) = (val lo + val hi) / 2 /\\\n'
                      '   val rw = RU (ieee_emin prec emax) prec ((val hi - val lo) / 2)) /\\\n'
                      '  (xnonempty (xval lo) (xval hi) -> ~ (finite lo /\\ finite hi) -> ball_whole_2 cw0 cw1 rw) /\\\n'
                      '  (nan lo \\/ nan hi -> ball_whole_2 cw0 cw1 rw) /\\\n'
                      '  (~ nan lo -> ~ nan hi -> ~ xnonempty (xval lo) (xval hi) -> ball_empty_2 cw0 cw1 rw)', s)
        m = ieee.model(ks)
        self.assertNotIn('up_ball_from_interval_2', rocq.model(ks))
        self.assertIn('Definition up_ball_from_interval_2_0 : float := const_of (round radix2 '
                      '(FLT_exp (3 - emax - prec) prec) Zceil (1 / 2)).', m)
        self.assertIn('Definition up_ball_from_interval_2_1 : float := const_of (round radix2 '
                      '(FLT_exp (3 - emax - prec) prec) Zceil 2).', m)

    def test_the_kernels_of_stage_b1(self):
        # The statements of the claims of stage B1 (architecture.md, "Claims of the interval kernels:
        # two limbs and the enclosure interface"), in their shapes.
        text = ieee.statements(self.ks)

        def spec(name):
            return re.search(rf'^Definition {name}_spec : Prop :=\n(.*?)\.\n', text, flags=re.M | re.S).group(1)
        s = spec('interval_hull_1')
        self.assertIn('  (interval_empty_1 zl zu <-> interval_empty_1 xl xu /\\ interval_empty_1 yl yu) /\\\n', s)
        self.assertIn('   range_lower (fun z : R => in_interval_1 xl xu z \\/ in_interval_1 yl yu z) lo ->\n', s)
        s = spec('interval_intersection_1')
        self.assertIn('  (interval_empty_1 zl zu <-> ~ (exists z : R, in_interval_1 xl xu z /\\ in_interval_1 yl yu z))',
                      s)
        s = spec('interval_mid_rad_1')
        self.assertIn('  (interval_empty_1 xl xu -> nan m /\\ nan r) /\\\n', s)
        self.assertIn('  (finite xl -> xval xu = XInf false -> xval m = XFin (omega prec emax) /\\ '
                      'r = infinity prec emax false) /\\\n', s)
        self.assertIn('   val r = RU (ieee_emin prec emax) prec (Rmax (val m - val xl) (val xu - val m))', s)
        s = spec('interval_to_ball_1')
        self.assertIn('  (ball_empty_1 c r <-> interval_empty_1 xl xu) /\\\n', s)
        self.assertIn('  (interval_nonempty_1 xl xu -> ~ interval_bounded_1 xl xu -> ball_whole_1 c r) /\\\n', s)
        s = spec('ball_to_interval_1')
        self.assertIn('   xval zl = xrd prec emax lo /\\ xval zu = xru prec emax hi', s)
        s = spec('interval_split_1')
        self.assertIn('   xval al = xval xl /\\ xval bu = xval xu /\\ xval au = xval bl', s)
        s = spec('interval_make_2')
        self.assertIn('  (nan lo0 \\/ nan hi0 -> zl0 = infinity prec emax true /\\ zu0 = infinity prec emax false '
                      '/\\ zero zl1 /\\ zero zu1) /\\\n', s)
        s = spec('mul_ext_2_2')
        self.assertIn('  ~ nan x0 ->\n  ~ nan y0 ->\n', s)
        self.assertIn('  (zero x0 \\/ zero y0 -> zero l0 /\\ zero l1) /\\\n', s)
        self.assertIn('   xle (xval_2 l0 l1) (xmul (xval_2 x0 x1) (xval_2 y0 y1)) = true /\\\n', s)
        s = spec('interval_mul_2')
        self.assertIn('   (zero xl0 /\\ zero xu0) \\/\n   (zero yl0 /\\ zero yu0) ->\n'
                      '   zero zl0 /\\ zero zl1 /\\ zero zu0 /\\ zero zu1) /\\\n', s)
        # mul_dir_1, whose zero_factor is of one-limb operands, is printed as before.
        self.assertIn('  (zero a \\/ zero b -> zero d) /\\\n', spec('mul_dir_1_ieee'))

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
                # ball_narrow_2_1 (Milestone 2) has a condition too: its radius can overflow.
                self.assertEqual(bool(enc[0]['finite_when']), name.endswith('_full') or name == 'ball_narrow_2_1', name)

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
        # A negative radius gives the empty set, a NaN radius the whole line (decided on 2026-11-20).
        self.assertIn('  (r = infinity prec emax true \\/ (finite r /\\ val r < 0) -> ball_empty_1 cw rw) /\\\n', s)
        self.assertIn('  (nan r \\/ r = infinity prec emax false \\/ (finite r /\\ 0 <= val r /\\ ~ finite c) -> '
                      'ball_whole_1 cw rw)', s)
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
        # 54, but the two constructors of a ball, unverified while their proof is redone for a NaN
        # radius that gives the whole line (decided on 2026-11-20).
        self.assertEqual(text.count('Print Assumptions'), 52)
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
    # their proofs landed is those two words). Then the first kernels of the intervals of wave 2,
    # unverified, were added: every earlier definition and statement is the same, byte for byte,
    # some printed earlier (callees before callers), and the statements import
    # IeeeIntervalVocabulary.v; make -C proofs passed on these files. Then the definition of
    # add_down_2_2 changed alone (no fused result negated through a select: the rounding down of
    # z1 - dd as minus the rounding up of dd - z1), and make -C proofs passed on the new model.
    # Then the thirteen kernels of stage B1 of the intervals, unverified, were added: every earlier
    # definition and statement is the same, byte for byte, some printed earlier; make -C proofs passed
    # on these files. Then a NaN radius given to a constructor of a ball became the whole line
    # (decided on 2026-11-20): the definitions and statements of ball_make_1 and ball_make_2 changed,
    # their status is unverified, and make -C proofs builds every file but theories/IeeeMake.v, whose
    # proof of the rule before fails, and the IEEE audit, which needs it; IeeeMake.v is being redone.
    DIGESTS = {'proofs/gen/IeeeModel.v': 'bad9bdbb870aeb2c18b2d6034c54b0d267f823ab0d02de198fb5a1cb08e276e9',
               'proofs/gen/IeeeStatements.v': 'ac755681e1db6c9d5d475876e3026c4593cefa9e01eed3e725da828abeff4ec4'}

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
