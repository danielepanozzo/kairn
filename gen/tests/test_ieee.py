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
# And the steps of the folds, whose bridge statements the IEEE model of a fold uses.
PROGRAMS += ['dot_step_1', 'dot_step_2', 'sum_entry_step_1', 'sum_entry_step_2', 'sum_fast_entry_step_2']


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
        # Those of Model.v, and the one that only kernels without a real-model statement use (the
        # halving of ball_from_interval_2 and interval_mid_rad_1, Milestone 2), defined here from its
        # expression, as Model.v would define it. The doubling of ball_from_interval_2, up(2), is a
        # constant of bound_dot_1 too, so Model.v defines it, under the name the proofs of the bound
        # kernels use (BoundKernels.v; gen/constant_names.json).
        only_here = {'up_ball_from_interval_2_0'}
        self.assertEqual(ups, {n for n in definitions(read('proofs/gen/Model.v')) if n.startswith('up_')} | only_here)
        self.assertIn('Definition up_ball_from_interval_2_0 : float := const_of (round radix2 '
                      '(FLT_exp (3 - emax - prec) prec) Zceil (1 / 2)).', m)
        self.assertIn('Definition up_bound_dot_1_2 : float := const_of (Model.up_bound_dot_1_2 (3 - emax - prec) '
                      'prec).', m)
        # The thirteen of the Ball cores, N and P of Milestone 2 (eta / (2u), eta / (2u^2): the
        # scalings of a ball and the directed products); the fourteen distinct ones of the four
        # bound kernels of the folds (bound_sum_k: 4 and 2; bound_dot_k: 4 and 3, 2, 1 + 2u, 1/4 and
        # 1 shared); and the one above.
        self.assertEqual(len(ups), 30)
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
        # The doubling, up(2), is also a constant of bound_dot_1, which has a real-model statement:
        # Model.v defines it, under the name the proofs of the bound kernels use, and so does this
        # model, from Model.v (gen/constant_names.json).
        self.assertIn('Definition up_bound_dot_1_2 : float := const_of (Model.up_bound_dot_1_2 (3 - emax - prec) '
                      'prec).', m)
        self.assertIn('  let bl := prod hl up_bound_dot_1_2 in\n', m)

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

    def test_the_kernels_of_stage_b2(self):
        # The statements of certain and trit (architecture.md, "Claims of the enclosure interface:
        # predicates and comparisons"), in their shapes: an exact predicate is one equivalence, a
        # three-valued comparison two and the exclusion of both.
        text = ieee.statements(self.ks)

        def spec(name):
            return re.search(rf'^Definition {name}_spec : Prop :=\n(.*?)\.\n', text, flags=re.M | re.S).group(1)
        self.assertTrue(spec('interval_empty_1').endswith('  (m = true <->\n    interval_empty_1 xl xu)'))
        self.assertIn('  (m = true <->\n    finite t0 /\\ in_interval_2 xl0 xl1 xu0 xu1 (val t0 + val t1))',
                      spec('interval_contains_2'))
        self.assertIn('  (m = true <->\n    interval_nonempty_1 xl xu /\\\n'
                      '    (forall x : R, in_interval_1 xl xu x -> 0 < x))', spec('interval_positive_1'))
        self.assertIn('  (m = true <->\n    (forall z : R, in_interval_1 xl xu z -> in_interval_1 yl yu z))',
                      spec('interval_subset_1'))
        self.assertIn('exists d : R, 0 < d /\\ (forall w : R, Rabs (w - z) < d -> in_interval_1 yl yu w)',
                      spec('interval_rel_interior_1'))
        s = spec('interval_less_2')
        self.assertIn('  (yes = true <->\n    interval_nonempty_2 xl0 xl1 xu0 xu1 /\\ interval_nonempty_2 yl0 yl1 yu0 yu1 /\\\n'
                      '    (forall x y : R, in_interval_2 xl0 xl1 xu0 xu1 x -> in_interval_2 yl0 yl1 yu0 yu1 y -> x < y)) /\\\n',
                      s)
        self.assertIn('-> ~ (x < y))) /\\\n  ~ (yes = true /\\ no = true)', s)
        # No hypothesis on the precision: comparisons and selects, for every precision.
        self.assertNotIn('<= prec)%Z', s)
        # Of a ball: certain, exact on the special states and a point that is not finite, and for
        # one limb exact for finite balls under the condition of exact_when.
        s = spec('ball_contains_point_2')
        self.assertIn('  (no = true ->\n    ~ (finite t0 /\\ in_ball_2 c0 c1 r (val t0 + val t1))) /\\\n', s)
        self.assertIn('  (ball_empty_2 c0 c1 r \\/ ball_whole_2 c0 c1 r \\/ ~ finite t0 ->\n   (yes = true <->\n', s)
        s = spec('ball_less_1')
        self.assertIn('  (ball_finite_1 cx rx /\\ ball_finite_1 cy ry -> Rabs (val rx + val ry) <= omega prec emax ->\n',
                      s)
        self.assertIn('    ~ ball_empty_1 cx rx /\\ ~ ball_empty_1 cy ry /\\\n', s)
        s = spec('ball_contains_ball_2')
        self.assertIn('  (m = true ->\n    (forall z : R, in_ball_2 cy0 cy1 ry z -> in_ball_2 cx0 cx1 rx z)) /\\\n', s)
        # The set operations of a ball.
        s = spec('ball_hull_1')
        self.assertIn('  (ball_empty_1 cz rz <-> ball_empty_1 cx rx /\\ ball_empty_1 cy ry) /\\\n'
                      '  (ball_empty_1 cx rx -> cz = cy /\\ rz = ry) /\\\n', s)
        self.assertIn('  (forall z : R, in_ball_1 cx rx z \\/ in_ball_1 cy ry z -> in_ball_1 cz rz z)', s)
        s = spec('ball_intersection_1')
        self.assertIn('  (ball_whole_1 cy ry -> cz = cx /\\ rz = rx) /\\\n', s)
        s = spec('ball_split_2')
        self.assertIn('   (forall z : R, (val c0 + val c1) - val r <= z <= (val c0 + val c1) -> in_ball_2 ca0 ca1 ra z)', s)

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
        # Every kernel of the extended domain names its theorem, the finishes of the folds and
        # of the folds of maxima and the interval kernels of the extended domain among them
        # (84); then the theorems that the descriptions of the folds' first stage name: 5
        # bridges and 3 correctness statements of the steps, 8 leading limbs, and the 8 folds in
        # their two orders (32); and the two folds of maxima in their two orders (4).
        self.assertEqual(text.count('Print Assumptions'), 120)
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
    # finishes were added, and every earlier one is the same, byte for byte. Then the programs of
    # the steps of the folds and their bridge statements (and the spec of those of two limbs) were
    # added, every earlier one the same, byte for byte. Then the two finishes were proved: the
    # comments above their statements say so, and nothing else changed. Then the steps of the maps
    # (unverified): their definitions were added, every earlier one the same, byte for byte, and
    # mul_1_1, which axpy_step_1 calls, is printed earlier, before the first kernel that calls it.
    # (The two lines of work met in a merge: the files are the regeneration of the merged
    # descriptions, IeeeModel.v that of the maps' side, byte for byte.) Then the kernels of the
    # folds of maxima (unverified): their definitions and the statements of their two finishes were
    # added, every earlier line kept, in its order. (Merged with the proofs of the folds and the
    # maps: the regeneration of the merged descriptions.)
    # Then the two lines of work met: the first kernels of the intervals of wave 2 and the thirteen
    # of stage B1 (unverified) joined the folds, the maps and the folds of maxima in a merge (on
    # their own line every earlier definition and statement stayed the same, byte for byte, some
    # printed earlier, callees before callers; the statements import IeeeIntervalVocabulary.v; and
    # add_down_2_2 negates no fused result through a select). The files are the regeneration of
    # the merged descriptions; up(2), which ball_from_interval_2 shares with bound_dot_1, is
    # up_bound_dot_1_2 in both (gen/constant_names.json).
    # Then the descriptions of the steps of the folds named the theorems of their bridge and
    # correctness statements (IeeeSteps.v): the comments above those eight statements say proved,
    # and nothing else changed. Then the two finishes of the folds of maxima were proved
    # (IeeeFoldNorm.v): the two comments above their statements say so, and nothing else changed.
    # Then the proofs of the intervals met them in a merge (on their own line: the statements
    # print "proved" for the interval kernels of one limb and for mul_dir_1,
    # whose theorems passed the audit: six words, and nothing else, changed in the statements.
    # Then for interval_add_2: one word more. Then for the six conversions of a ball. Then the
    # thirteen kernels of stage B1 of the intervals, unverified, were added: every earlier
    # definition and statement is the same, byte for byte, some printed earlier; make -C proofs
    # passed on these files. Then the statements print "proved" for the six exact kernels of
    # stage B1 (IeeeIntervalExact.v): six words, and nothing else, changed. Then for
    # interval_sub_2 (IeeeIntervalSub2.v): one word more. Then for the four conversions of
    # stage B1 (IeeeIntervalConvert.v): four words more. Then for mul_ext_2_2 and
    # interval_mul_2 (IeeeIntervalMul2.v): two words more.)
    # The files are the regeneration of the merged descriptions.
    # Then a NaN radius given to a constructor of a ball became the whole line (decided on
    # 2026-11-20), on the line of the intervals' generator: the definitions and statements of
    # ball_make_1 and ball_make_2 changed, and nothing else; their theorems were proved again on
    # the new definitions for the new statements (theories/IeeeMake.v), the statements file prints
    # their status, proved, and make -C proofs passed on these files. Merged here: the
    # regeneration of the merged descriptions.
    # Then the 26 predicates and three-valued comparisons of an interval of stage B2, unverified,
    # were added: their definitions and statements (certain and trit), every earlier definition
    # and statement the same, byte for byte, some printed earlier (le_2_2 before lt_2_2, callees
    # before callers); make -C proofs passed on these files.
    # Then the 20 predicates, comparisons and set operations of a ball (unverified): their
    # definitions and statements added, every earlier one the same, byte for byte, some printed
    # earlier; make -C proofs passed on these files.
    DIGESTS = {'proofs/gen/IeeeModel.v': 'e21a83a273a7c53ded5c6436673b6d09dbad18f4c336102a18bdc3eddc292fa5',
               'proofs/gen/IeeeStatements.v': 'ad4387ff91fe5fad7500384faf3d1f5a98a449c23eb6dfcf7d9e153e218acf89'}


    def test_the_checked_files(self):
        for path, digest in self.DIGESTS.items():
            text = read(path)
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), digest, path)


class WithProduct(unittest.TestCase):
    """proofs/gen/IeeeWith.v: the kernels constexpr by the rule of the product with the product as
    an argument. Each K_with is the definition of IeeeModel.v with `prod a b` written `p_ a b` and
    a call of another such kernel written as its K_with p_, line for line; the section has the
    variables of IeeeModel.v; the kernels are those build lists as constexpr by the rule."""

    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()
        cls.text = read('proofs/gen/IeeeWith.v')
        cls.model = read('proofs/gen/IeeeModel.v')

    @staticmethod
    def block(text, name):
        m = re.search(r'^Definition ' + re.escape(name) + r'\b.*?\.\n(?=\n|End )', text, flags=re.M | re.S)
        return m.group(0) if m else None

    def test_the_kernels(self):
        from kairn_gen import build, cpp
        rule = [k.name for k in self.ks.values() if cpp.product_rule(k, self.ks)]
        self.assertEqual(definitions(self.text), [f'{n}_with' for n in rule])
        line = next(x for x in build.summary(self.ks) if x.startswith('constexpr by the rule of the product'))
        self.assertEqual(sorted(line.split(': ', 1)[1].split(', ')), sorted(rule))
        self.assertGreaterEqual(set(rule), {'split', 'two_prod_dekker', 'mul_pow2_2', 'mul_pow2_2_full',
                                            'ball_mul_pow2_1', 'ball_mul_pow2_1_full', 'ball_mul_pow2_2',
                                            'ball_mul_pow2_2_full'})

    def test_each_is_the_model_with_the_product_as_argument(self):
        rule = {k.name for k in ieee.with_kernels(self.ks)}
        for name in rule:
            with self.subTest(kernel=name):
                mine = self.block(self.text, f'{name}_with')
                model = self.block(self.model, name)
                self.assertIsNotNone(mine)
                self.assertIsNotNone(model)
                back = mine.replace(f'Definition {name}_with (p_ : float -> float -> float)', f'Definition {name}')
                back = re.sub(r':= p_ ', ':= prod ', back)
                for callee in rule:
                    back = back.replace(f' {callee}_with p_ ', f' {callee} ')
                self.assertIsNone(re.search(r'\bp_\b', back))
                self.assertEqual(back, model)

    def test_the_section(self):
        section = self.text.split('Section IeeeWith.\n', 1)[1].split('\n\n(*', 1)[0]
        self.assertEqual([x for x in section.splitlines() if x.startswith(('Variable', 'Context'))], SECTION)
        self.assertIn('From Kairn.Gen Require IeeeModel.', self.text)
        # The constants and the other kernels are IeeeModel's, by local notations.
        for m in re.finditer(r'^Local Notation (\w+) := \(IeeeModel\.(\w+) prec emax', self.text, flags=re.M):
            self.assertEqual(m.group(1), m.group(2))
            self.assertIn(f'Definition {m.group(2)} ', self.model)


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


class TheoremFields(unittest.TestCase):
    """The theorems of the IEEE-model statements of the finite domain and of the folds
    (ieee_bridge_theorem, ieee_spec_theorem, ieee_lead_theorem; the ieee_theorem of a fold): the
    statements they prove are printed as proved, and IeeeAudit.v checks each theorem against its
    statement; without them, nothing changes. Judged from the descriptions with every such field
    removed (kernels_with), so that it means the same whether the committed ones have none, as
    now, or some."""
    STEP = ['ieee_bridge_theorem: proofs/theories/IeeeSteps.v dot_step_2_ieee_bridge',
            'ieee_spec_theorem: proofs/theories/IeeeSteps.v dot_step_2_ieee_correct',
            'ieee_lead_theorem: proofs/theories/IeeeSteps.v dot_step_2_ieee_lead']
    FOLD = ['ieee_theorem: proofs/theories/IeeeFolds.v']
    # The theorem fields: those of a kernel (its ieee_theorem, of the extended domain, is another
    # field and stays), and that of a fold.
    KERNEL_FIELDS = ('ieee_bridge_theorem:', 'ieee_spec_theorem:', 'ieee_lead_theorem:')
    FOLD_FIELDS = ('ieee_theorem:',)

    def kernels_with(self, kernels=None, folds=None):
        """The descriptions of gen/kernels with every theorem field removed, then those given added:
        the test means the same whether or not the committed descriptions have such fields."""
        ks = common.kernels()

        def text(path, fields, extra):
            with open(os.path.join(common.GEN, 'kernels', path), encoding='utf-8') as f:
                lines = [line for line in f.read().rstrip('\n').split('\n') if not line.startswith(fields)]
            return '\n'.join(lines) + '\n' + '\n'.join(extra) + '\n'

        new = {name: ir.parse_kernel(text(k.path, self.KERNEL_FIELDS, (kernels or {}).get(name, [])), k.path)
               for name, k in ks.items()}
        fds = {name: ir.parse_fold(text(fd.path, self.FOLD_FIELDS, (folds or {}).get(name, [])), fd.path)
               for name, fd in ks.folds.items()}
        return ir.ordered(new, fds)

    def errors(self, name, kernels=None, folds=None):
        return [str(e) for e in rules.check_all(self.kernels_with(kernels, folds)) if e.kernel == name]

    def test_printed_and_audited(self):
        from kairn_gen import build
        ks = self.kernels_with({'dot_step_2': self.STEP}, {'dot_2': self.FOLD})
        self.assertEqual(rules.check_all(ks), [])
        before, after = build.outputs(self.kernels_with()), build.outputs(ks)
        changed = sorted(rel for rel in after if after[rel] != before[rel])
        self.assertEqual(changed, ['proofs/gen/IeeeAudit.v', 'proofs/gen/IeeeFoldStatements.v',
                                   'proofs/gen/IeeeStatements.v'])

        def diff(rel):
            old, new = before[rel].splitlines(), after[rel].splitlines()
            return [a for a in new if a not in old], [a for a in old if a not in new]

        added, gone = diff('proofs/gen/IeeeStatements.v')
        self.assertEqual(len(added), 2)
        self.assertEqual(len(gone), 2)      # the comment of both statements, then unverified
        self.assertTrue(all(g.endswith('IEEE-model status: unverified. *)') for g in gone), gone)
        self.assertTrue(all(a.startswith('(* dot_step_2: ') and a.endswith('IEEE-model status: proved. *)')
                            for a in added), added)
        added, gone = diff('proofs/gen/IeeeFoldStatements.v')
        self.assertEqual(sorted(added), sorted([
            '(* dot_step_2, the leading limb of its result: finite only if those of its operands are. '
            'IEEE-model status: proved. *)',
            '(* dot_2, the sequential order, in the IEEE model. Status: proved. *)',
            '(* dot_2, the lane order, for every number of lanes W, in the IEEE model. Status: proved. *)']))
        self.assertEqual(len(gone), 3)
        added, gone = diff('proofs/gen/IeeeAudit.v')
        self.assertEqual(gone, [])
        audit = after['proofs/gen/IeeeAudit.v']
        for line in ('From Kairn.Gen Require Import IeeeFoldStatements.',
                     'From Kairn Require Import IeeeFolds.',
                     'From Kairn Require Import IeeeSteps.',
                     'Definition dot_step_2_ieee_bridge_audit : dot_step_2_ieee_bridge_spec := dot_step_2_ieee_bridge.',
                     'Print Assumptions dot_step_2_ieee_bridge.',
                     'Definition dot_step_2_ieee_audit : dot_step_2_ieee_spec := dot_step_2_ieee_correct.',
                     'Print Assumptions dot_step_2_ieee_correct.',
                     'Definition dot_step_2_ieee_lead_audit : dot_step_2_ieee_lead_spec := dot_step_2_ieee_lead.',
                     'Print Assumptions dot_step_2_ieee_lead.',
                     'Definition dot_2_seq_ieee_audit : dot_2_seq_ieee_spec := dot_2_seq_ieee_correct.',
                     'Print Assumptions dot_2_seq_ieee_correct.',
                     'Definition dot_2_lanes_ieee_audit : dot_2_lanes_ieee_spec := dot_2_lanes_ieee_correct.',
                     'Print Assumptions dot_2_lanes_ieee_correct.'):
            self.assertIn(line + '\n', audit)
        # Only a bridge: IeeeFoldStatements.v is not imported.
        ks = self.kernels_with({'dot_step_2': self.STEP[:1]})
        self.assertFalse('Require Import IeeeFoldStatements.' in build.outputs(ks)['proofs/gen/IeeeAudit.v'])

    def test_refused(self):
        self.assertTrue(any('must be named dot_step_2_ieee_correct, not dot_step_2_correct' in e for e in self.errors(
            'dot_step_2', {'dot_step_2': ['ieee_spec_theorem: proofs/theories/IeeeSteps.v dot_step_2_correct']})))
        self.assertTrue(any('only with "ieee: spec"' in e for e in self.errors(
            'dot_step_1', {'dot_step_1': ['ieee_spec_theorem: proofs/theories/IeeeSteps.v dot_step_1_ieee_correct']})))
        self.assertTrue(any('only the step or the combination of a fold has' in e for e in self.errors(
            'mul_2_2', {'mul_2_2': ['ieee_lead_theorem: proofs/theories/IeeeSteps.v mul_2_2_ieee_lead']})))
        self.assertTrue(any('belong to kernels of the finite domain' in e for e in self.errors(
            'abs_2', {'abs_2': ['ieee_bridge_theorem: proofs/theories/IeeeExt.v abs_2_ieee_bridge']})))
        self.assertTrue(any('file must be proofs/theories/*.v' in e for e in self.errors(
            'dot_step_2', {'dot_step_2': ['ieee_lead_theorem: theories/IeeeSteps.v dot_step_2_ieee_lead']})))
        self.assertTrue(any('a map has no statement in the IEEE model' in e for e in self.errors(
            'axpy_2', folds={'axpy_2': self.FOLD})))
        self.assertTrue(any('the ieee_theorem file must be proofs/theories/*.v' in e for e in self.errors(
            'dot_2', folds={'dot_2': ['ieee_theorem: IeeeFolds.v']})))


if __name__ == '__main__':
    unittest.main()
