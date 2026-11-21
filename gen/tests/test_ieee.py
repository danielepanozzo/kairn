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
# And the kernels of the accumulator with an IEEE-model statement whose listing is a program of
# Program.v (acc_merge_k: additions; the others guard or take an absolute value).
PROGRAMS += ['acc_merge_1', 'acc_merge_2']
# And the steps of the maps, with their bridge statements (ieee: bridge), and mul_1_1, which
# axpy_step_1 and its entry form call; the steps add_2_2 and sub_2_2 had theirs already.
PROGRAMS += ['add_1_1', 'sub_1_1', 'add_entry_step_1', 'sub_entry_step_1', 'scale_step_1', 'mul_pow2_step_1',
             'axpy_step_1', 'axpy_entry_step_1', 'mul_1_1', 'add_entry_step_2', 'sub_entry_step_2', 'scale_step_2',
             'mul_pow2_step_2', 'axpy_step_2', 'axpy_entry_step_2', 'axpy_step_2_1', 'axpy_entry_step_2_1']
# And the step of the constructor of a BallVector of one limb (ieee: bridge).
PROGRAMS += ['bv_center_entry_1']
# And the step of the negation of a BallVector of one limb.
PROGRAMS += ['neg_1']


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
        # 1 shared); the one above; and the three of acc_radius_1 that no other kernel has
        # ((1+u) u + N, (1+u)^8, (1+u)^7 eta/2 + N); and the two of conv_radius (4 (1+u)^8 eta + eta/(2u),
        # (1+u)^7).
        self.assertEqual(len(ups), 35)
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
                      # The same infinity twice is the whole line, as a NaN bound is (decided on
                      # 2026-11-20); reversed bounds are the empty set.
                      '  (nan lo \\/ nan hi \\/ (exists s : bool, xval lo = XInf s /\\ xval hi = XInf s) ->\n'
                      '   ball_whole_2 cw0 cw1 rw) /\\\n'
                      '  (xlt (xval hi) (xval lo) = true -> ball_empty_2 cw0 cw1 rw)', s)
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
        self.assertIn('  (nan lo0 \\/ nan hi0 \\/ (exists s : bool, xval_2 lo0 lo1 = XInf s /\\ xval_2 hi0 hi1 = XInf s) ->\n'
                      '   zl0 = infinity prec emax true /\\ zu0 = infinity prec emax false '
                      '/\\ zero zl1 /\\ zero zu1) /\\\n'
                      '  (xlt (xval_2 hi0 hi1) (xval_2 lo0 lo1) = true -> interval_empty_2 zl0 zl1 zu0 zu1)', s)
        # One limb: the same, the whole line for the same infinity twice (decided on 2026-11-20).
        s = spec('interval_make_1')
        self.assertIn('  (nan lo \\/ nan hi \\/ (exists s : bool, xval lo = XInf s /\\ xval hi = XInf s) ->\n'
                      '   zl = infinity prec emax true /\\ zu = infinity prec emax false) /\\\n'
                      '  (xlt (xval hi) (xval lo) = true -> interval_empty_1 zl zu)', s)
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
        # An operand returned as it is, the limbs themselves: Y when X is special, X when Y is
        # and X is not (when both are, the result is Y, and need not be X: two NaNs of different
        # signs, two whole lines of centers +0 and -0).
        s = spec('ball_hull_1')
        self.assertIn('  (ball_empty_1 cz rz <-> ball_empty_1 cx rx /\\ ball_empty_1 cy ry) /\\\n'
                      '  (ball_empty_1 cx rx -> cz = cy /\\ rz = ry) /\\\n'
                      '  (ball_empty_1 cy ry /\\ ~ ball_empty_1 cx rx -> cz = cx /\\ rz = rx) /\\\n', s)
        self.assertIn('  (forall z : R, in_ball_1 cx rx z \\/ in_ball_1 cy ry z -> in_ball_1 cz rz z)', s)
        s = spec('ball_intersection_1')
        self.assertIn('  (ball_whole_1 cx rx -> cz = cy /\\ rz = ry) /\\\n'
                      '  (ball_whole_1 cy ry /\\ ~ ball_whole_1 cx rx -> cz = cx /\\ rz = rx) /\\\n', s)
        self.assertIn('  (ball_whole_2 cy0 cy1 ry /\\ ~ ball_whole_2 cx0 cx1 rx -> cz0 = cx0 /\\ cz1 = cx1 /\\ rz = rx)',
                      spec('ball_intersection_2'))
        self.assertIn('  (ball_empty_2 cy0 cy1 ry /\\ ~ ball_empty_2 cx0 cx1 rx -> cz0 = cx0 /\\ cz1 = cx1 /\\ rz = rx)',
                      spec('ball_hull_2'))
        # The conversions of two limbs. The midpoint of two limbs is a number, canonical for every
        # canonical interval; a midpoint of one limb has no such clause, and the center of a ball
        # (interval_to_ball_2) is canonical as part of ball_2.
        self.assertIn(' xl0 xl1 xu0 xu1 in\n  canonical_2 m0 m1 /\\\n  (interval_empty_2 xl0 xl1 xu0 xu1 -> nan m0',
                      spec('interval_mid_rad_2'))
        self.assertNotIn('canonical_2', spec('interval_mid_rad_1'))
        self.assertNotIn('canonical_2', spec('interval_to_ball_2'))
        s = spec('interval_mid_rad_2')
        self.assertIn('   (r = infinity prec emax false \\/ (finite r /\\ (forall z : R, in_interval_2 xl0 xl1 xu0 xu1 z -> '
                      'Rabs (z - (val m0 + val m1)) <= val r))) /\\\n', s)
        self.assertIn('-> finite r))', s)
        s = spec('ball_to_interval_2')
        self.assertIn('   (((val c0 + val c1) - val r) = 0 -> xval_2 zl0 zl1 = XFin lo) /\\\n', s)
        self.assertIn('   interval_bounded_2 zl0 zl1 zu0 zu1)', s)
        s = spec('ball_from_interval_1')
        self.assertIn('   val rw = RU (ieee_emin prec emax) prec (Rmax (val cw - val lo) (val hi - val cw))) /\\\n', s)
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
        # their two orders (32); and the two folds of maxima in their two orders (4); and the
        # IEEE-model statements of the eight kernels of the accumulator (8); and those of the
        # 16 steps of the maps, 16 bridges, 8 correctness statements and 16 leading limbs (40),
        # of the 18 maps in their two orders (36) and of the two convolutions (2): 206. Then the 26
        # predicates, comparisons and relations of an interval of stage B2 (232), and the eight
        # predicates and comparisons of a ball of one limb (240), and ball_split_1 (241), and the
        # signs and the split of a ball of two limbs and ball_to_interval_2 (246), and four
        # comparisons of balls of two limbs (250), and interval_mid_rad_2 and interval_split_2
        # (252), and ball_contains_point_2 (253), and interval_to_ball_2 (254), and the hull and
        # the intersection of balls of one limb and of two (258); and ball_from_interval_1, proved
        # again for the rule of 2026-11-20 with its listing corrected (259). And of the six ball
        # vectors bv_add_k, bv_sub_k and bv_scale_k in their two orders (12); and of the negation and the
        # constructor of a BallVector: bv_center_2 and bv_make_finish (2), the bridges and the leading
        # limbs of neg_1 and bv_center_entry_1 (4), and bv_neg_k and bv_make_k in their two orders (8); and of
        # the scaling by a power of two: the claims and the leading limbs of its two steps (4), and
        # bv_mul_pow2_k in its two orders (4); and the finish of the product of two BallVectors,
        # bv_conv_finish (1), and the products bv_conv_1 and bv_conv_2 (2: one statement each, as a
        # convolution's); and the leading limbs of neg_2 and bv_center_2, steps of the extended domain
        # (2), and the two statements more of the two folds of maxima, F_orders_ieee_spec and
        # F_flag_ieee_spec (4): 302. Then the statements of the two executions of the thirty
        # kernels of IeeeWith.v, K_two_executions_spec, whose theorems no description names (30):
        # 332.
        self.assertEqual(text.count('Print Assumptions'), 332)
        self.assertEqual(text.count('Print Assumptions IeeeTwoExecutions.'), len(ieee.with_kernels(self.ks)))
        self.assertIn('Definition ball_from_interval_1_audit : ball_from_interval_1_spec := '
                      'ball_from_interval_1_correct.\nPrint Assumptions ball_from_interval_1_correct.', text)
        self.assertIn('Definition ball_hull_2_audit : ball_hull_2_spec := ball_hull_2_correct.\n'
                      'Print Assumptions ball_hull_2_correct.', text)
        self.assertIn('From Kairn Require Import IeeeBallHull.', text)
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
    # On another line, the kernels of the accumulator (unverified): their definitions, the programs
    # of acc_merge_k and their statements (ieee: spec, each output group's claims under its own
    # leading limb) were added, every earlier line kept; add_2_2, mul_2_2 and dot_step_2, which
    # they call, are printed earlier, before them. Merged here: the regeneration of the merged
    # descriptions, and make -C proofs passed on these files. Then the six state kernels were
    # proved in the IEEE model (IeeeAccKernels.v): the comments above their six statements say
    # proved, and nothing else changed. Then the two radii: two words more.
    # On another line, the steps of the maps got their bridges (ieee: bridge, and spec for those of
    # two limbs): the programs of sixteen steps and of mul_1_1, and their statements, were added,
    # every earlier line kept. Then the radius kernels of BallVector (unverified): their definitions
    # were added, every earlier line kept. Merged here: the regeneration of the merged descriptions,
    # and make -C proofs passed on these files. Then the descriptions of the sixteen steps of the
    # maps named the theorems of their bridges and, for those of two limbs, of their claims
    # (IeeeMapSteps.v): the comments above those twenty-four statements say proved, and nothing
    # else changed.
    # On the same line, after the radius kernels: the four kernels of the constructor of BallVector
    # (unverified): their definitions, the program of bv_center_entry_1 and their statements were
    # added, every earlier line kept. Then neg_1 and bv_neg_radius, of the negation of a BallVector
    # (unverified), in the same way. Then the two steps and the radius of the scaling of a BallVector
    # by a power of two (unverified): their definitions and the statements of the steps (ieee: spec,
    # with the mask of exact_flag) were added, every earlier line kept. Then conv_radius and
    # bv_conv_finish, of the product of two BallVectors (unverified): their definitions, the two
    # constants of conv_radius and the statement of bv_conv_finish (finite_or_nan with if_all) were
    # added, every earlier line kept. Merged here: the regeneration of the merged descriptions.
    # On that line, after that merge: the kernels of the negation and of the constructor
    # were proved (IeeeBvNegMake.v): the comments above the statements of neg_1, bv_center_entry_1,
    # bv_center_2 and bv_make_finish say proved, and nothing else changed. Then the two steps of the
    # scaling by a power of two (IeeeBvPow2.v): two comments more.
    # On another line, from the joined tree of stage B1 (a35501e): the 26 predicates and three-valued comparisons of an interval of stage B2, unverified,
    # were added: their definitions and statements (certain and trit), every earlier definition
    # and statement the same, byte for byte, some printed earlier (le_2_2 before lt_2_2, callees
    # before callers); make -C proofs passed on these files.
    # Then the 20 predicates, comparisons and set operations of a ball (unverified): their
    # definitions and statements added, every earlier one the same, byte for byte, some printed
    # earlier; make -C proofs passed on these files.
    # Then the conversions of two limbs, the ball from an interval of one limb and the hull and the
    # intersection of balls of two limbs (seven, unverified): their definitions and statements
    # added, every earlier one the same, byte for byte; make -C proofs passed on these files.
    # Then ball_intersection_1 and ball_from_interval_1 rewritten (the same values, the special
    # results selected after the halving): their definitions and the source line of their
    # statements' comments; make -C proofs passed on these files. Merged here: the regeneration of
    # the merged descriptions.
    # On the line of main, from the same base (f7c86be): the same infinity twice, given to the
    # constructors of an interval or to the ball from an
    # interval of two T, became the whole line (decided on 2026-11-20): the definitions and
    # statements of interval_make_1, interval_make_2 and ball_from_interval_2 changed, and nothing
    # else; their theorems were proved again on the new definitions for the new statements
    # (theories/IeeeInterval1.v, IeeeIntervalExact.v, IeeeBallConvert.v), the statements file
    # prints their status, proved, and make -C proofs passed on these files.
    # Merged here: the regeneration of the merged descriptions; the statement of
    # ball_from_interval_1 (unverified) was printed under the same rule.
    # On the line of stage B2, after ball_intersection_1 and ball_from_interval_1 were rewritten:
    # the statements print "proved" for the 26 predicates, comparisons and relations of an
    # interval (IeeeIntervalPredicates.v): 26 words, and nothing else, changed. Then for the eight
    # predicates and comparisons of a ball of one limb (IeeeBallPredicates.v): eight words more.
    # Then for ball_from_interval_1 and ball_split_1 (IeeeBallSets.v): two words more. Then for
    # the signs and the split of a ball of two limbs (IeeeBallPredicates2.v) and
    # ball_to_interval_2 (IeeeBallConvert2.v): five words more. Then for four comparisons of
    # balls of two limbs (IeeeBallCompare2.v): four words more. Then for interval_mid_rad_2 and
    # interval_split_2 (IeeeIntervalConvert2.v): two words more. Then for ball_contains_point_2
    # (IeeeBallContains2.v): one word more. Then for interval_to_ball_2 (IeeeIntervalConvert2.v):
    # one word more.
    # Then the statements of ball_set were corrected (the proof of the other kernels of the stage
    # refuted them): an empty X still gives Y as it is (the whole line X, for the intersection),
    # and an empty Y gives X as it is only when X is not empty (the whole line Y when X is not the
    # whole line); and ball_of_interval with ieee1788 and a center of two limbs says first that
    # the center is canonical (interval_mid_rad_2, proved again). Five lines changed, the four
    # kernels of ball_set still unverified; make -C proofs passed on these files. Then the
    # statements print "proved" for those four (IeeeBallHull.v): four words more.
    # Merged here: the regeneration of the merged descriptions. ball_from_interval_1 is printed
    # unverified: the theorem of that line is of its statement before the rule of the same
    # infinity twice, which its listing does not follow yet.
    # Then the listing of ball_from_interval_1 was corrected for that rule (the owner's ruling of
    # 2026-11-21: rv = lt(gu, gl) selects the empty ball where it tested for a NaN): its
    # definition and the source line of its comments changed, and nothing else. Then its theorem
    # was proved again for that listing and its statement (IeeeBallSets.v): the statements file
    # prints its status, proved, one word more, and make -C proofs passed on these files.
    # Then the proofs of the ball vectors met them in a merge: the regeneration of the merged
    # descriptions.
    # On the line of the ball vectors, meanwhile:
    # Then the printer of finite_or_nan wrote the masks of if_all, which it had left out: the first
    # clause of the statement of bv_conv_finish, the only kernel with if_all, says
    # flag = true <-> okc = true /\ okg = true /\ finite rz (it said flag = true <-> finite rz, which
    # was false), and nothing else changed; then that statement was proved (IeeeBvConv.v): one
    # comment more. make -C proofs passed on these files.
    # Merged here: the regeneration of the merged descriptions.
    DIGESTS = {'proofs/gen/IeeeModel.v': 'c1dafcb503776af9a0ccc273cbb68029dad60d53ea214bf104cd6b2e826968aa',
               'proofs/gen/IeeeStatements.v': '035b64a9e30a0b1f9cdb778af45831f4d8d74267d9298331ff8662a74b6d0208'}


    def test_the_checked_files(self):
        for path, digest in self.DIGESTS.items():
            text = read(path)
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), digest, path)


class WithProduct(unittest.TestCase):
    """proofs/gen/IeeeWith.v: the kernels constexpr by the rule of the product with the operations
    that constant evaluation runs differently as arguments. Each K_with is the definition of
    IeeeModel.v with `prod a b` written `p_ a b`, `guard a` written `g_ a` and `times_inf t` written
    `t_ t`, for those of the three the kernel computes, and a call of another such kernel written as
    its K_with on the arguments it takes, line for line; the section has the variables of
    IeeeModel.v; the kernels are those build lists as constexpr by the rule."""
    # Each argument, and the operation of IeeeModel.v it stands for.
    OPERATION = {'p_': 'prod', 'g_': 'guard', 't_': 'times_inf'}

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
        section = self.text.split('\nEnd IeeeWith.\n', 1)[0]
        self.assertEqual(definitions(section), ['prod_ce', 'guard_ce', 'times_inf_ce'] + [f'{n}_with' for n in rule])
        line = next(x for x in build.summary(self.ks) if x.startswith('constexpr by the rule of the product'))
        self.assertEqual(sorted(line.split(': ', 1)[1].split(', ')), sorted(rule))
        self.assertGreaterEqual(set(rule), {'split', 'two_prod_dekker', 'mul_pow2_2', 'mul_pow2_2_full',
                                            'ball_mul_pow2_1', 'ball_mul_pow2_1_full', 'ball_mul_pow2_2',
                                            'ball_mul_pow2_2_full'})

    def test_each_is_the_model_with_the_operations_as_arguments(self):
        rule = {k.name: k for k in ieee.with_kernels(self.ks)}
        for name, k in rule.items():
            with self.subTest(kernel=name):
                mine = self.block(self.text, f'{name}_with')
                model = self.block(self.model, name)
                self.assertIsNotNone(mine)
                self.assertIsNotNone(model)
                args = ieee.with_arguments(k, self.ks)
                binders = ''.join(f' ({arg} : {t})' for _, arg, t, _ in args)
                back = mine.replace(f'Definition {name}_with{binders} (', f'Definition {name} (')
                for arg, op in self.OPERATION.items():
                    back = re.sub(f':= {arg} ', f':= {op} ', back)
                for callee in rule:
                    back = re.sub(rf' {callee}_with(?: [pgt]_)* ', f' {callee} ', back)
                self.assertIsNone(re.search(r'\b[pgt]_\b', back))
                self.assertEqual(back, model)

    def test_the_operations_of_constant_evaluation_are_arguments(self):
        """The arguments are the operations whose C++ dispatches on constant evaluation in a kernel
        constexpr without a variant (cpp.SPELL_PLAIN), and a kernel takes those it computes, in its
        listing or in a callee's: a kernel with a guard has the guard as an argument (and its C++
        dispatches there), and no listing of IeeeWith.v names the run-time guard or times_inf."""
        from kairn_gen import cpp
        dispatched = {op for op, s in cpp.SPELL_PLAIN.items() if '__builtin_is_constant_evaluated()' in s}
        self.assertEqual(dispatched, {'prod', 'guard', 'times_inf'})
        self.assertEqual({op for op, _, _, _ in ieee.CE_OPERATIONS}, dispatched)
        scalar = read('include/kairn/gen/scalar.hpp')
        took = {}
        for k in ieee.with_kernels(self.ks):
            ops = {p.op for p in ir.prims(k, self.ks)}
            head = self.block(self.text, f'{k.name}_with').split('\n', 1)[0]
            for op, arg, t, _ in ieee.CE_OPERATIONS:
                self.assertEqual(f'({arg} : {t})' in head, op in ops, (k.name, op))
                if op in ops:
                    took.setdefault(op, []).append(k.name)
            fn = scalar.split(f' void {k.name}(double ', 1)[1].split('\n}\n', 1)[0]
            if 'guard' in ops:
                self.assertRegex(fn, r'const double \w+ = __builtin_is_constant_evaluated\(\) \? (\w+) : \1 \+ 0\.0;')
        self.assertEqual(took['guard'], ['axpy_entry_step_1', 'ball_from_interval_1', 'ball_from_interval_2'])
        self.assertEqual(took['times_inf'], ['mul_pow2_2_full'])
        self.assertEqual(len(took['prod']), len(ieee.with_kernels(self.ks)))
        section = self.text.split('Section IeeeWith.\n', 1)[1].split('\nEnd IeeeWith.\n', 1)[0]
        self.assertIsNone(re.search(r':= (guard|times_inf) ', section))
        self.assertNotIn('Local Notation guard ', section)
        self.assertNotIn('Local Notation times_inf ', section)
        # The definitions of constant evaluation, as the C++ computes them (prelude.hpp).
        self.assertIn('Definition guard_ce (a : float) : float := a.\n', section)
        self.assertIn('Definition times_inf_ce (t : float) : float :=\n'
                      '  if lt pzero t then pinf else if lt t pzero then B754_infinity prec emax true else cnan.\n',
                      section)
        self.assertIn('return t > 0 ? std::numeric_limits<double>::infinity() : 0 > t ? '
                      '-std::numeric_limits<double>::infinity() : std::numeric_limits<double>::quiet_NaN();',
                      read('include/kairn/gen/prelude.hpp'))
        self.assertIn('Definition prod_ce (a b : float) : float :=\n'
                      '  Bmult prec emax prec_gt_0_ prec_lt_emax_ nan_mult BinarySingleNaN.mode_NE a b.\n', section)
        # A kernel of the rule that calls a kernel outside it which computes a guard is refused: its
        # listing would keep the guard of run time where constant evaluation runs another.
        ks = dict(self.ks)
        k = ir.parse_kernel('kernel: rule_guarded\ninput: a\ninput: b\noutput: z\nvalue: a*b+b\n'
                            'status: unverified\n\np = prod(a, b)\nz = add_entry_step_1(p, b)\n', 'k.kernel')
        ks['rule_guarded'] = k
        ks = ir.ordered(ks, self.ks.folds)
        self.assertTrue(cpp.product_rule(ks['rule_guarded'], ks))
        with self.assertRaisesRegex(ieee.PrintError, 'it calls add_entry_step_1, which is not a listing of '
                                    'IeeeWith.v and computes guard'):
            ieee.with_model(ks)

    def test_the_statements_of_the_two_executions(self):
        """After the section, one statement K_two_executions_spec per kernel of the rule, in its order,
        and the IEEE audit checks each theorem K_two_executions of IeeeTwoExecutions.v against it: a
        kernel that joins the rule without its theorem, or with a theorem of another statement, fails
        the proofs build."""
        rule = [k.name for k in ieee.with_kernels(self.ks)]
        after = self.text.split('\nEnd IeeeWith.\n', 1)[1]
        self.assertEqual(re.findall(r'^Definition (\w+)_two_executions_spec : Prop :=$', after, flags=re.M), rule)
        self.assertEqual(definitions(after), [f'{n}_two_executions_spec' for n in rule])
        audit = read('proofs/gen/IeeeAudit.v')
        self.assertEqual(audit, ieee.audit(self.ks))
        checked = re.findall(r'^Definition (\w+)_two_executions_audit : (\w+)_two_executions_spec := '
                             r'IeeeTwoExecutions\.(\w+)_two_executions\.\nPrint Assumptions '
                             r'IeeeTwoExecutions\.(\w+)_two_executions\.$', audit, flags=re.M)
        self.assertEqual(checked, [(n, n, n, n) for n in rule])
        self.assertIn('From Kairn.Gen Require Import IeeeWith.\nFrom Kairn Require IeeeTwoExecutions.\n', audit)
        # The checks come last, after those of the statements the descriptions name.
        self.assertTrue(audit.endswith(f'Print Assumptions IeeeTwoExecutions.{rule[-1]}_two_executions.\n'))
        self.assertGreater(audit.index('_two_executions_audit'), audit.index('ball_hull_2_correct'))
        # A kernel that joins the rule gets its statement and its check, with no field to write.
        ks = dict(self.ks)
        ks['rule_toy'] = ir.parse_kernel('kernel: rule_toy\ninput: a\ninput: b\noutput: z\nvalue: a*b\n'
                                         'status: unverified\n\nz = prod(a, b)\n', 'k.kernel')
        ks = ir.ordered(ks, self.ks.folds)
        self.assertIn('Definition rule_toy_two_executions_spec : Prop :=', ieee.with_model(ks))
        self.assertIn('Definition rule_toy_two_executions_audit : rule_toy_two_executions_spec := '
                      'IeeeTwoExecutions.rule_toy_two_executions.\n'
                      'Print Assumptions IeeeTwoExecutions.rule_toy_two_executions.\n', ieee.audit(ks))

    def test_the_shape_of_a_statement(self):
        """The binders in the order of the theorems: the format, its two instances, the NaN functions,
        each followed by its primed copy, of each side only (here nan_mult for the plain product,
        nan_const for times_inf_ce, nan_mult' for the run-time times_inf), then the operands; the
        listing at prod_ce and times_inf_ce, the generated kernel with the primed functions."""
        self.assertIn("""(* mul_pow2_2_full: mul_pow2_2, then the fix-up of IEEE-like results (Milestone 1 listing). The two executions. *)
Definition mul_pow2_2_full_two_executions_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_plus' nan_minus nan_minus' : nan2 prec emax) (nan_abs nan_abs' : nan1 prec emax) (nan_fma' : nan3 prec emax) (nan_mult nan_mult' : nan2 prec emax) (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  forall x0 x1 c : binary_float prec emax,
  let '(w0, w1) := mul_pow2_2_full_with prec emax nan_plus nan_minus nan_abs (prod_ce prec emax nan_mult) (times_inf_ce prec emax nan_const) x0 x1 c in
  let '(w0', w1') := IeeeModel.mul_pow2_2_full prec emax nan_plus' nan_minus' nan_abs' nan_fma' nan_mult' x0 x1 c in
  xval w0 = xval w0' /\\ xval w1 = xval w1'.
""", self.text)
        # The guard of constant evaluation, one output: the outputs' values without a let.
        self.assertIn("""  forall a x y : binary_float prec emax,
  xval (axpy_entry_step_1_with prec emax nan_plus (prod_ce prec emax nan_mult) (guard_ce prec emax) a x y) = xval (IeeeModel.axpy_entry_step_1 prec emax nan_plus' nan_fma' a x y).
""", self.text)
        # A mask among the operands, in its place; a mask among the outputs, compared by equality.
        self.assertIn('  forall (m : binary_float prec emax) (ex : bool) (rx c : binary_float prec emax),\n', self.text)
        self.assertIn("  xval g = xval g' /\\ xval t = xval t' /\\ ok = ok'.\n", self.text)

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
        # The C++ headers too, since the comment of a fold's function gives the status of each model
        # (cpp.fold_status): only the comments of dot_2's functions, from unverified to proved.
        self.assertEqual(changed, ['include/kairn/gen/avx2.hpp', 'include/kairn/gen/neon.hpp',
                                   'include/kairn/gen/scalar.hpp', 'proofs/gen/IeeeAudit.v',
                                   'proofs/gen/IeeeFoldStatements.v', 'proofs/gen/IeeeStatements.v'])

        def diff(rel):
            old, new = before[rel].splitlines(), after[rel].splitlines()
            return [a for a in new if a not in old], [a for a in old if a not in new]

        for rel in changed[:3]:
            added, gone = diff(rel)
            self.assertEqual(len(added), len(gone), rel)
            self.assertTrue(added, rel)
            self.assertEqual(sorted(a.replace('proved (IEEE model)', 'unverified (IEEE model)') for a in added),
                             sorted(gone), rel)
            self.assertTrue(all(a.startswith('// fold dot_2(') and a.endswith('(real model), proved (IEEE model).')
                                for a in added), (rel, added))

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
        # A map names F_seq_ieee_correct and F_lanes_ieee_correct, a convolution F_ieee_correct; the
        # comments of their statements say proved, and the audit checks each, after the folds'.
        ks = self.kernels_with(folds={'axpy_2': self.FOLD, 'conv_1': self.FOLD})
        self.assertEqual(rules.check_all(ks), [])
        out = build.outputs(ks)
        added, gone = [a for a in out['proofs/gen/IeeeFoldStatements.v'].splitlines()
                       if a not in before['proofs/gen/IeeeFoldStatements.v'].splitlines()], None
        self.assertEqual(sorted(added), sorted([
            '(* axpy_2, the sequential order, in the IEEE model: each element it writes, and its mask. Status: proved. *)',
            '(* axpy_2, the lane order, for every number of lanes W, in the IEEE model: each element it writes, and '
            'its mask. Status: proved. *)',
            '(* conv_1, each coefficient it writes, and its mask, in the IEEE model. Status: proved. *)']))
        audit = out['proofs/gen/IeeeAudit.v']
        for line in ('Definition axpy_2_seq_ieee_audit : axpy_2_seq_ieee_spec := axpy_2_seq_ieee_correct.',
                     'Definition axpy_2_lanes_ieee_audit : axpy_2_lanes_ieee_spec := axpy_2_lanes_ieee_correct.',
                     'Definition conv_1_ieee_audit : conv_1_ieee_spec := conv_1_ieee_correct.',
                     'Print Assumptions conv_1_ieee_correct.'):
            self.assertIn(line + '\n', audit)
        self.assertLess(audit.index('axpy_2_lanes_ieee_audit'), audit.index('conv_1_ieee_audit'))
        # Only a bridge: IeeeFoldStatements.v is not imported.
        ks = self.kernels_with({'dot_step_2': self.STEP[:1]})
        self.assertFalse('Require Import IeeeFoldStatements.' in build.outputs(ks)['proofs/gen/IeeeAudit.v'])

    @staticmethod
    def comment(text, spec):
        """The comment printed above the statement spec."""
        return text.split(f'Definition {spec} : Prop :=', 1)[0].rsplit('(*', 1)[1].rstrip()

    def test_the_two_statements_of_a_fold_of_maxima(self):
        """A fold of maxima in both orders has F_orders_ieee_spec and F_flag_ieee_spec besides the
        statements of its orders: its ieee_theorem names their theorems too, F_orders_ieee_correct and
        F_flag_ieee_correct, in the same file. The comments of its four statements say proved, those of
        the other fold of maxima unverified, and the audit checks the four, in the order of the file."""
        from kairn_gen import build
        ks = self.kernels_with(folds={'norm_upper_2': ['ieee_theorem: proofs/theories/IeeeFoldNorm.v']})
        self.assertEqual(rules.check_all(ks), [])
        out = build.outputs(ks)
        audit, s = out['proofs/gen/IeeeAudit.v'], out['proofs/gen/IeeeFoldStatements.v']
        self.assertEqual([n for n in re.findall(r'^Definition (\w+)_audit :', audit, flags=re.M)
                          if n.startswith('norm_upper')],
                         ['norm_upper_2_seq_ieee', 'norm_upper_2_lanes_ieee', 'norm_upper_2_orders_ieee',
                          'norm_upper_2_flag_ieee'])
        for what in ('orders', 'flag'):
            self.assertIn(f'Definition norm_upper_2_{what}_ieee_audit : norm_upper_2_{what}_ieee_spec := '
                          f'norm_upper_2_{what}_ieee_correct.\nPrint Assumptions norm_upper_2_{what}_ieee_correct.\n',
                          audit)
            self.assertTrue(self.comment(s, f'norm_upper_2_{what}_ieee_spec').endswith('Status: proved. *)'))
            self.assertTrue(self.comment(s, f'norm_upper_1_{what}_ieee_spec').endswith('Status: unverified. *)'))
        self.assertIn(('norm_upper_2_flag_ieee_spec', 'proofs/theories/IeeeFoldNorm.v', 'norm_upper_2_flag_ieee_correct',
                       'IeeeFoldStatements'), ieee.proved_statements(ks))

    def test_the_leading_limbs_of_the_extended_domain(self):
        """neg_2 and bv_center_2, the steps of two limbs of folds of the extended domain, have leading-limb
        statements: an ieee_lead_theorem names their theorems, the comments of the statements say proved
        and the audit checks them. A kernel of the extended domain still names no bridge or spec theorem,
        nor a lead theorem when it has no lead statement."""
        from kairn_gen import build
        lead = {'neg_2': ['ieee_lead_theorem: proofs/theories/IeeeBvNegMake.v neg_2_ieee_lead'],
                'bv_center_2': ['ieee_lead_theorem: proofs/theories/IeeeBvNegMake.v bv_center_2_ieee_lead']}
        ks = self.kernels_with(lead)
        self.assertEqual(rules.check_all(ks), [])
        out = build.outputs(ks)
        audit, s = out['proofs/gen/IeeeAudit.v'], out['proofs/gen/IeeeFoldStatements.v']
        for name in lead:
            self.assertTrue(ks[name].extended, name)
            self.assertIn(f'Definition {name}_ieee_lead_audit : {name}_ieee_lead_spec := {name}_ieee_lead.\n'
                          f'Print Assumptions {name}_ieee_lead.\n', audit)
            self.assertTrue(self.comment(s, f'{name}_ieee_lead_spec').endswith('IEEE-model status: proved. *)'))
        self.assertIn('From Kairn Require Import IeeeBvNegMake.', audit)
        self.assertTrue(any('belong to kernels of the finite domain' in e for e in self.errors(
            'neg_2', {'neg_2': ['ieee_bridge_theorem: proofs/theories/IeeeBvNegMake.v neg_2_ieee_bridge']})))
        self.assertTrue(any('belong to kernels of the finite domain' in e for e in self.errors(
            'neg_2', {'neg_2': ['ieee_spec_theorem: proofs/theories/IeeeBvNegMake.v neg_2_ieee_correct']})))
        self.assertTrue(ks['bv_make_finish'].extended)
        self.assertTrue(any('only the step or the combination of a fold has' in e for e in self.errors(
            'bv_make_finish',
            {'bv_make_finish': ['ieee_lead_theorem: proofs/theories/IeeeBvNegMake.v bv_make_finish_ieee_lead']})))

    def test_a_product_of_ball_vectors(self):
        """A product of two BallVectors has one IEEE-model statement, F_ieee_spec, as a convolution has, not
        one per order: its ieee_theorem names F_ieee_correct, and the audit checks that theorem against
        F_ieee_spec (it once printed F_seq_ieee_spec, a statement that does not exist). And with every fold
        naming its file, every statement the audit names is one the statements file defines."""
        from kairn_gen import build
        before = build.outputs(self.kernels_with())
        ks = self.kernels_with(folds={'bv_conv_1': ['ieee_theorem: proofs/theories/IeeeBvConvFinite.v']})
        self.assertEqual(rules.check_all(ks), [])
        self.assertIn(('bv_conv_1_ieee_spec', 'proofs/theories/IeeeBvConvFinite.v', 'bv_conv_1_ieee_correct',
                       'IeeeFoldStatements'), ieee.proved_statements(ks))
        out = build.outputs(ks)
        audit = out['proofs/gen/IeeeAudit.v']
        self.assertEqual([a for a in audit.splitlines() if ('BvConv' in a or 'bv_conv' in a) and 'finish' not in a
                          and not a.endswith('Import IeeeBvConv.')],
                         ['From Kairn Require Import IeeeBvConvFinite.',
                          'Definition bv_conv_1_ieee_audit : bv_conv_1_ieee_spec := bv_conv_1_ieee_correct.',
                          'Print Assumptions bv_conv_1_ieee_correct.'])
        added = [a for a in out['proofs/gen/IeeeFoldStatements.v'].splitlines()
                 if a not in before['proofs/gen/IeeeFoldStatements.v'].splitlines()]
        self.assertEqual(added, ['(* bv_conv_1, in the IEEE model: V1 to V4 and the flag. Status: proved. *)'])
        # Every fold naming a file: the audit names only statements that exist.
        ks = self.kernels_with(folds={name: self.FOLD for name in common.kernels().folds})
        out = build.outputs(ks)
        defined = set(re.findall(r'^Definition (\w+) : Prop :=', out['proofs/gen/IeeeFoldStatements.v'], flags=re.M))
        named = re.findall(r'^Definition \w+_audit : (\w+) := \w+\.$', out['proofs/gen/IeeeAudit.v'], flags=re.M)
        folds = [spec for spec, _, _, gen in ieee.proved_statements(ks) if gen == 'IeeeFoldStatements']
        self.assertTrue(set(folds) <= set(named), sorted(set(folds) - set(named)))
        self.assertEqual(sorted(set(folds) - defined), [])
        for name in ('bv_conv_1', 'bv_conv_2', 'conv_1', 'conv_2'):
            self.assertIn(f'{name}_ieee_spec', folds)
            self.assertNotIn(f'{name}_seq_ieee_spec', folds)

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
        # A map and a convolution have statements in the IEEE model and name their file like a fold.
        self.assertEqual(self.errors('axpy_2', folds={'axpy_2': self.FOLD}), [])
        self.assertEqual(self.errors('conv_2', folds={'conv_2': self.FOLD}), [])
        self.assertTrue(any('the ieee_theorem file must be proofs/theories/*.v' in e for e in self.errors(
            'dot_2', folds={'dot_2': ['ieee_theorem: IeeeFolds.v']})))


if __name__ == '__main__':
    unittest.main()
