"""The rules refuse wrong kernels with a message naming the kernel, the value and the rule."""
import unittest

import common
from kairn_gen import ir, rules

# A valid kernel to start from: Fast2Sum.
HEAD = '''
kernel:  bad
input:   a
input:   b
output:  r = s e
value:   a+b
ensures: error r R c=0 k=2 t=0
status:  unverified
'''
GOOD = '''
s = add(a, b)
z = sub(s, a)
e = sub(b, z)
'''


def check(*texts):
    kernels = {}
    for text in texts:
        k = ir.parse_kernel(text, 'test')
        kernels[k.name] = k
    return rules.check_all(ir.ordered(kernels))


class Refusals(unittest.TestCase):
    def refused(self, errors, kernel, value, rule, words):
        for e in errors:
            text = str(e)
            if e.kernel == kernel and e.value == value and e.rule == rule and words in text:
                self.assertIn(f'kernel {kernel}', text)
                self.assertIn(f'value {value}', text)
                self.assertIn(rule, text)
                return
        self.fail(f'no refusal of {kernel}, {value}, {rule} mentioning {words!r} in:\n' +
                  '\n'.join(map(str, errors)))

    def test_the_starting_kernel_is_accepted(self):
        self.assertEqual(check(HEAD + GOOD), [])

    def test_value_assigned_twice(self):
        errors = check(HEAD + 's = add(a, b)\ns = sub(s, a)\nz = sub(s, a)\ne = sub(b, z)\n')
        self.refused(errors, 'bad', 's', rules.RULE1, 'assigned twice')

    def test_input_assigned_again(self):
        errors = check(HEAD + 'a = add(a, b)\ns = add(a, b)\nz = sub(s, a)\ne = sub(b, z)\n')
        self.refused(errors, 'bad', 'a', rules.RULE1, 'assigned twice')

    def test_use_before_definition(self):
        errors = check(HEAD + 's = add(a, b)\ne = sub(b, z)\nz = sub(s, a)\n')
        self.refused(errors, 'bad', 'z', rules.RULE1, 'before its definition')

    def test_use_of_a_value_never_defined(self):
        errors = check(HEAD + 's = add(a, b)\ne = sub(b, q)\n')
        self.refused(errors, 'bad', 'q', rules.RULE1, 'never defined')

    def test_unused_value(self):
        errors = check(HEAD + GOOD + 'w = add(a, s)\n')
        self.refused(errors, 'bad', 'w', rules.RULE1, 'never used')

    def test_unused_input(self):
        errors = check(HEAD.replace('input:   b', 'input:   b\ninput:   c') + GOOD)
        self.refused(errors, 'bad', 'c', rules.RULE1, 'never used')

    def test_output_never_defined(self):
        errors = check(HEAD + 's = add(a, b)\nz = sub(s, a)\n')
        self.refused(errors, 'bad', 'e', rules.RULE1, 'never defined')

    def test_product_feeding_an_addition(self):
        errors = check(HEAD + 't = mul(a, b)\ns = add(t, b)\nz = sub(s, a)\ne = sub(b, z)\n')
        self.refused(errors, 'bad', 't', rules.RULE_R1, 'an operand of add at s')

    def test_product_feeding_an_addition_through_a_negation(self):
        errors = check(HEAD + 't = mul(a, b)\nn = neg(t)\ns = add(n, b)\nz = sub(s, a)\ne = sub(b, z)\n')
        self.refused(errors, 'bad', 't', rules.RULE_R1, 'neg at n then an operand of add at s')

    def test_product_reaching_an_fma_addend_through_a_select(self):
        errors = check(HEAD + 't = mul(a, b)\nm = lt(a, b)\nw = select(m, b, t)\n'
                              's = fma(a, b, w)\nz = sub(s, a)\ne = sub(b, z)\n')
        self.refused(errors, 'bad', 't', rules.RULE_R1, 'select at w then an operand of fma at s')

    def test_product_anywhere(self):
        errors = check(HEAD + 't = mul(a, b)\ns = fma(t, a, b)\nz = sub(s, a)\ne = sub(b, z)\n')
        self.refused(errors, 'bad', 't', rules.RULE_R1, 'none in the run-time IR')

    def test_muladd_as_an_output(self):
        errors = check(HEAD + 's = muladd(a, b, a)\nz = sub(s, a)\ne = sub(b, z)\n')
        self.refused(errors, 'bad', 's', rules.RULE_R2, 'result of muladd')

    def test_input_as_an_output(self):
        errors = check(HEAD.replace('output:  r = s e', 'output:  r = a e') + 'e = add(a, b)\n')
        self.refused(errors, 'bad', 'a', rules.RULE_R2, 'is an input')

    def test_value_that_cannot_reach_output_limb_0(self):
        # w reaches the outputs only through a select, and is not computed from s.
        errors = check(HEAD + 's = add(a, b)\nm = lt(a, b)\nd = sub(a, b)\nw = select(m, d, b)\n'
                              'e = sub(s, w)\n')
        self.refused(errors, 'bad', 'd', rules.RULE_CONE, 'does not reach output limb s')

    def test_input_that_cannot_reach_output_limb_0(self):
        head = HEAD.replace('input:   b', 'input:   b\ninput:   c')
        errors = check(head + 's = add(a, b)\ne = add(s, c)\n')
        self.refused(errors, 'bad', 'c', rules.RULE_CONE, 'does not reach output limb s')

    def test_succ_does_not_carry_a_non_finite_value(self):
        # succ(-inf) is finite: what reaches output limb 0 only through succ is outside the cone.
        errors = check(HEAD + 'n = succ(b)\ns = add(a, a)\ne = sub(n, s)\n')
        self.refused(errors, 'bad', 'b', rules.RULE_CONE, 'does not reach output limb s')

    def test_cone_through_an_inlined_call(self):
        callee = '''
kernel:  half
input:   a
input:   b
output:  r = s e
value:   a+b
ensures: error r R c=0 k=2 t=0
status:  unverified
s = add(a, a)
e = sub(s, b)
'''
        caller = HEAD + '(s, e) = half(a, b)\n'
        errors = check(callee, caller)
        self.refused(errors, 'half', 'b', rules.RULE_CONE, 'does not reach output limb s')
        self.refused(errors, 'bad', 'b', rules.RULE_CONE, 'does not reach output limb s')

    def test_stale_cone_exemption(self):
        errors = check(HEAD + 'cone_exempt: no reason\n' + GOOD)
        self.refused(errors, 'bad', '-', rules.RULE_CONE, 'satisfies the rule')

    def test_no_theorem_and_not_unverified(self):
        head = HEAD.replace('status:  unverified', 'status:  proved\nsource: x\nlicense: MIT')
        errors = check(head + GOOD)
        self.refused(errors, 'bad', '-', rules.RULE_THEOREM, 'names no theorem')

    def test_no_status(self):
        errors = check(HEAD.replace('status:  unverified', '') + GOOD)
        self.refused(errors, 'bad', '-', rules.RULE_THEOREM, 'status is None')

    def test_theorem_name(self):
        head = HEAD + 'theorem: proofs/theories/X.v something_else\n'
        self.refused(check(head + GOOD), 'bad', '-', rules.RULE_THEOREM, 'must be named bad_correct')

    def test_a_proved_kernel_with_everything_is_accepted(self):
        head = HEAD.replace('status:  unverified', 'status:  proved\nsource: x\nlicense: MIT\n'
                                                   'theorem: proofs/theories/X.v bad_correct')
        self.assertEqual(check(head + GOOD), [])

    # The second wave.

    def test_unused_input_declared(self):
        head = HEAD.replace('input:   b', 'input:   b\ninput:   c') + 'unused: c not needed here\n'
        errors = check(head + GOOD)
        self.assertEqual([e for e in errors if e.rule == rules.RULE1], [])

    def test_unused_declaration_of_a_used_input(self):
        errors = check(HEAD + 'unused: b it is used\n' + GOOD)
        self.refused(errors, 'bad', 'b', rules.RULE1, 'is used; remove the declaration')

    def test_unused_declaration_of_a_value_that_is_not_an_input(self):
        errors = check(HEAD + 'unused: q no such input\n' + GOOD)
        self.refused(errors, 'bad', 'q', rules.RULE1, 'is not an input')

    def test_unused_input_names_the_declaration(self):
        errors = check(HEAD.replace('input:   b', 'input:   b\ninput:   c') + GOOD)
        self.refused(errors, 'bad', 'c', rules.RULE1, 'declared with "unused:"')

    def test_product_through_a_copy(self):
        errors = check(HEAD + 't = mul(a, b)\nc = copy(t)\ns = add(c, b)\nz = sub(s, a)\ne = sub(b, z)\n')
        self.refused(errors, 'bad', 't', rules.RULE_R1, 'copy at c then an operand of add at s')

    def test_copy_as_an_output_is_accepted(self):
        self.assertEqual(check(HEAD + 's = add(a, b)\nz = sub(s, a)\nw = sub(b, z)\ne = copy(w)\n'), [])

    def test_copy_keeps_a_value_in_the_cone(self):
        # b reaches s only through the copy, which keeps a non-finite value non-finite.
        self.assertEqual(check(HEAD + 'c = copy(b)\ns = add(a, c)\nz = sub(s, a)\ne = sub(b, z)\n'), [])

    def test_mask_output_through_a_comparison_is_accepted(self):
        head = HEAD.replace('output:  r = s e', 'output:  r = s e\noutput:  mask m')
        self.assertEqual(check(head + GOOD + 'h = lt(a, 0)\nl = eq(0, b)\nm = and(h, l)\n'), [])

    def test_mask_output_that_is_a_limb(self):
        head = HEAD.replace('output:  r = s e', 'output:  r = s e\noutput:  mask m')
        errors = check(head + GOOD + 'm = add(a, b)\n')
        self.refused(errors, 'bad', 'm', rules.WELL_FORMED, 'is a limb, and its group is declared as a mask')

    def test_mask_input_used_as_a_limb(self):
        head = HEAD.replace('input:   b', 'input:   b\ninput:   mask w')
        errors = check(head + 's = add(a, w)\nz = sub(s, a)\ne = sub(b, z)\n')
        self.refused(errors, 'bad', 'w', rules.WELL_FORMED, 'wants a limb here, and w is a mask')

    def test_mask_input_as_an_operand_of_select_is_accepted(self):
        head = HEAD.replace('input:   b', 'input:   b\ninput:   mask w')
        self.assertEqual(check(head + 'c = select(w, a, b)\nt = add(a, b)\ns = add(t, c)\n'
                                      'z = sub(s, a)\ne = sub(b, z)\n'), [])

    def test_zero_is_a_limb(self):
        errors = check(HEAD + GOOD.replace('e = sub(b, z)', 'e = sub(b, z)\nh = lt(a, 0)\nw = and(0, h)\n'
                                                            'q = select(w, a, b)\nr0 = add(q, s)'))
        self.assertTrue(any(e.value == '0' and 'a constant is a limb, not a mask' in str(e) for e in errors),
                        errors)


class ComputedConstants(unittest.TestCase):
    BOUND = '''
kernel:  bound
input:   a
input:   b
output:  p
value:   a*b
ensures: error p R c=1 k=1 t=1/2
status:  {status}
source:  x
license: MIT
theorem: proofs/theories/X.v bound_correct
p = prod(a, b)
'''
    USER = HEAD.replace('kernel:  bad', 'kernel:  user')

    def user(self, status='unverified', const='unit_computed(bound)'):
        head = self.USER.replace('status:  unverified', f'status:  {status}')
        if status == 'proved':
            head += 'source: x\nlicense: MIT\ntheorem: proofs/theories/X.v user_correct\n'
        return head + f'k = prod(const {const}, a)\ns = add(k, b)\nz = sub(s, k)\ne = sub(b, z)\n'

    def refused(self, errors, words):
        self.assertTrue(any(e.rule == rules.COMPUTED and words in str(e) for e in errors),
                        '\n'.join(map(str, errors)) or 'accepted')

    def test_accepted(self):
        for status in ('unverified', 'proved'):
            self.assertEqual(check(self.BOUND.format(status='proved'), self.user(status)), [])
        self.assertEqual(check(self.BOUND.format(status='unverified'), self.user('unverified')), [])

    def test_a_proved_kernel_needs_a_proved_bound(self):
        errors = check(self.BOUND.format(status='unverified'), self.user('proved'))
        self.refused(errors, 'only an unverified kernel may use the constants of a bound that is not proved')
        errors = check(self.BOUND.format(status='unverified'), self.user('proved', 'tiny_computed(bound)'))
        self.refused(errors, 'bound is unverified')

    def test_unknown_kernel(self):
        self.refused(check(self.BOUND.format(status='proved'), self.user(const='unit_computed(nope)')),
                     'nope is not a kernel')

    def test_the_bound_must_be_one_relative_unconditional_error_entry(self):
        for change, words in (('ensures: error p R c=1 k=1 t=1/2\nensures: error p R c=2 k=1 t=0', '2 error entries'),
                              ('ensures: error p R c=1 k=1 t=1/2\nensures: leading_rounded p', None),
                              ('ensures: error p A c=1 k=1 t=1/2', 'form R and unconditional'),
                              ('ensures: error p R c=1 k=1 t=1/2 when=product_large', 'form R and unconditional'),
                              ('ensures: leading_rounded p', '0 error entries')):
            bound = self.BOUND.format(status='proved').replace('ensures: error p R c=1 k=1 t=1/2', change)
            errors = check(bound, self.user())
            if words is None:
                self.assertEqual(errors, [])
            else:
                self.refused(errors, words)

    def test_minimum_precision_of_the_bound(self):
        bound = self.BOUND.format(status='proved').replace('p = prod', 'min_precision: 3\np = prod')
        self.refused(check(bound, self.user()), 'min_precision must be at least 3')
        user = self.user().replace('status:  unverified', 'status:  unverified\nmin_precision: 3')
        self.assertEqual(check(bound, user), [])

    def test_unknown_function(self):
        errors = check(self.BOUND.format(status='proved'), self.user(const='half_computed(bound)'))
        self.assertTrue(any('unknown constant' in str(e) for e in errors), errors)

    def test_kernel_names_the_constants_would_shadow(self):
        for name in ('unit_computed_x', 'tiny_computed_y'):
            errors = check(HEAD.replace('kernel:  bad', f'kernel:  {name}') + GOOD)
            self.assertTrue(any(e.kernel == name and e.rule == rules.WELL_FORMED for e in errors), name)


class WellFormed(unittest.TestCase):
    def refused(self, text, value, words, *more):
        errors = check(text, *more)
        self.assertTrue(any(e.value == value and words in str(e) for e in errors),
                        '\n'.join(map(str, errors)) or 'accepted')

    def test_unknown_operation(self):
        self.refused(HEAD + 's = plus(a, b)\nz = sub(s, a)\ne = sub(b, z)\n', 's', 'unknown operation')

    def test_arity(self):
        self.refused(HEAD + 's = add(a, b, a)\nz = sub(s, a)\ne = sub(b, z)\n', 's', 'takes 2 operands')

    def test_mask_as_a_limb(self):
        self.refused(HEAD + 'm = lt(a, b)\ns = add(m, b)\nz = sub(s, a)\ne = sub(b, z)\n', 'm', 'is a mask')

    def test_limb_as_a_mask(self):
        self.refused(HEAD + 'w = select(a, a, b)\ns = add(w, b)\nz = sub(s, a)\ne = sub(b, z)\n',
                     'a', 'wants a mask')

    def test_reserved_names(self):
        for name in ('prec', 'rnd', 'double', 'and', 'linux'):
            self.refused(HEAD + f'{name} = add(a, b)\ns = add({name}, b)\nz = sub(s, a)\ne = sub(b, z)\n',
                         name, 'name the printers use')

    def test_kernel_names_the_printers_make(self):
        for name in ('two_sum_spec', 'x_correct', 'y_audit', 'fuse_t', 'kairn', 'fma_rn'):
            errors = check(HEAD.replace('kernel:  bad', f'kernel:  {name}') + GOOD)
            self.assertTrue(any(e.kernel == name and e.rule == rules.WELL_FORMED for e in errors), name)

    def test_value_named_like_a_kernel(self):
        other = HEAD.replace('kernel:  bad', 'kernel:  w') + GOOD
        self.refused(HEAD + 'w = add(a, b)\ns = add(w, b)\nz = sub(s, a)\ne = sub(b, z)\n', 'w',
                     'name the printers use', other)

    def test_unknown_constant(self):
        self.refused(HEAD + 's = add(const pi, b)\nz = sub(s, a)\ne = sub(b, z)\n', 'pi', 'unknown constant')

    def test_mask_output(self):
        self.refused(HEAD.replace('r = s e', 'r = s m') + 's = add(a, b)\nm = lt(s, b)\n', 'm', 'is a mask')

    def test_recursion(self):
        with self.assertRaises(ir.DescriptionError):
            check(HEAD + '(s, e) = bad(a, b)\n')

    def test_value_names_have_no_underscore(self):
        with self.assertRaises(ir.DescriptionError):
            check(HEAD.replace('r = s e', 'r = s_1 e') + GOOD)


class ConstantEvaluation(unittest.TestCase):
    VARIANT = '''
kernel:  bad_ce
input:   a
input:   b
output:  r = s e
value:   a+b
ensures: error r R c=0 k=2 t=0
status:  unverified
'''

    def test_variant_with_an_fma(self):
        errors = check(HEAD + 'ce_variant: bad_ce\n' + GOOD,
                       self.VARIANT + 's = add(a, b)\nz = fms(a, b, s)\ne = sub(b, z)\n')
        self.assertTrue(any(e.rule == rules.CONSTEVAL and e.value == 'z' for e in errors), errors)

    def test_variant_with_another_signature(self):
        errors = check(HEAD + 'ce_variant: bad_ce\n' + GOOD,
                       self.VARIANT.replace('r = s e', 'r = s f') + 's = add(a, b)\nz = sub(s, a)\nf = sub(b, z)\n')
        self.assertTrue(any(e.rule == rules.CONSTEVAL and 'same inputs and outputs' in str(e) for e in errors))

    def test_variant_with_prod_is_accepted(self):
        self.assertEqual(check(HEAD + 'ce_variant: bad_ce\n' + GOOD,
                               self.VARIANT + 's = prod(a, b)\nz = sub(s, a)\ne = sub(b, z)\n'), [])


class Claims(unittest.TestCase):
    def refused(self, head, words):
        errors = check(head + GOOD)
        self.assertTrue(any(e.rule == rules.CLAIMS and words in str(e) for e in errors),
                        '\n'.join(map(str, errors)) or 'accepted')

    def test_vocabulary(self):
        self.refused(HEAD + 'requires: finite a\n', 'vocabulary')
        self.refused(HEAD + 'requires: normalized q\n', 'vocabulary')
        self.refused(HEAD.replace('t=0', 't=0 when=tiny'), 'product_large')
        self.refused(HEAD.replace(' R ', ' Q '), 'form')
        self.refused(HEAD.replace('c=0', 'c=1/v'), 'unknown name')
        self.refused(HEAD.replace('t=0', 't=u'), 'unknown name')
        self.refused(HEAD.replace('c=0', 'c=1/0x2'), 'c:')
        self.refused(HEAD.replace('value:   a+b', 'value:   a/b'), 'only + - *')
        self.refused(HEAD.replace('value:   a+b', 'value:   a+q'), 'unknown name')
        # A kernel whose claims say nothing about the value claims nothing (in the first wave
        # this was "no error entry"; the second wave has kernels without one).
        self.refused(HEAD.replace('ensures: error r R c=0 k=2 t=0', 'ensures: normalized r'),
                     'says nothing about the value')

    def test_second_wave_vocabulary_is_accepted(self):
        head = HEAD.replace('output:  r = s e', 'output:  r = s e\noutput:  t\noutput:  mask m')
        body = GOOD + 't = add(a, b)\nh = lt(a, b)\nl = le(0, a)\nm = and(h, l)\n'
        text = (head.replace('value:   a+b', 'value:   abs(a)-b') + 'requires: power_of_two a\nrequires: nonneg b\n'
                'ensures: rounded t down\nensures: rounded t nearest\nensures: upper t gaps=3/2\n'
                'ensures: predicate m le a abs(-b)\nensures: encloses t t -x x=a,b\n' + body)
        # The other outputs do not reach s (rule 4); only the claims matter here.
        self.assertEqual([e for e in check(text) if e.rule == rules.CLAIMS], [])

    def test_second_wave_vocabulary(self):
        head = HEAD.replace('input:   b', 'input:   b\ninput:   x = x0 x1\ninput:   mask w') \
                   .replace('output:  r = s e', 'output:  r = s e\noutput:  t\noutput:  mask m')
        body = ('t = add(x0, x1)\nh = lt(a, b)\nl = and(h, w)\nm = or(l, h)\n'
                'q = select(w, x0, x1)\nk = add(a, q)\ns = add(k, b)\nz = sub(s, a)\ne = sub(b, z)\n')
        accepted = head + body
        self.assertEqual([e for e in check(accepted) if e.rule == rules.CLAIMS], [])
        for extra, words in (
                ('requires: power_of_two x', 'about a one-limb input'),
                ('requires: nonneg w', 'vocabulary'),
                ('requires: nonneg', 'vocabulary'),
                ('requires: power_of_two a b', 'vocabulary'),
                ('ensures: rounded t zero', 'rounded mode'),
                ('ensures: rounded r nearest', 'must have one limb'),
                ('ensures: rounded m up', 'must be a limb'),
                ('ensures: upper t gaps=0', 'positive'),
                ('ensures: upper t gaps=u', 'unknown name'),
                ('ensures: upper t gaps=abs(2)', 'no abs'),
                ('ensures: predicate t lt a b', 'must be a mask'),
                ('ensures: predicate m ne a b', 'predicate relation'),
                ('ensures: predicate m lt a q', 'unknown name'),
                ('ensures: predicate m lt a w', 'unknown name'),
                ('ensures: normalized m', 'must be a limb'),
                ('ensures: error m R c=0 k=2 t=0', 'must be a limb'),
                ('ensures: encloses q t y y=a,b', 'not an output'),
                ('ensures: encloses t r y y=a,b', 'must have one limb'),
                ('ensures: encloses t t y y=q,b', 'not a limb input'),
                ('ensures: encloses t t y y=a,x', 'not a one-limb limb input'),
                ('ensures: encloses t t y y=w,b', 'not a limb input'),
                ('ensures: encloses t t a a=x,b', 'is the name of a group'),
                ('ensures: encloses t t u u=a,b', 'is the name of a group, a limb, or a name the printers use'),
                ('ensures: encloses t t y+z y=a,b z=x,b', 'belongs to two balls'),
                ('ensures: encloses t t y+b y=a,b', 'unknown name'),
                ('ensures: encloses t t y*x y=a,b', None),
                ('value: abs(a)', None),
                ('value: 2*a', 'only + - *')):
            text = (head.replace('value:   a+b', extra) if extra.startswith('value:') else head + extra + '\n') + body
            try:
                errors = check(text)
            except ir.DescriptionError as e:
                self.assertIn(words, str(e), extra)
                continue
            claim_errors = [e for e in errors if e.rule == rules.CLAIMS]
            if words is None:
                self.assertEqual(claim_errors, [], extra)
            else:
                self.assertTrue(any(words in str(e) for e in claim_errors), f'{extra}: {claim_errors}')


class TheKernels(unittest.TestCase):
    def test_first_wave_and_test_kernels_are_accepted(self):
        for d in (None, common.TEST_KERNELS):
            self.assertTrue(common.kernels(d))

    FIRST_WAVE = {'two_sum', 'fast_two_sum', 'two_prod', 'split', 'two_prod_dekker', 'add_2_2', 'add_2_1',
                  'mul_2_2', 'mul_2_1', 'add_fast_2_2'}
    # docs/developer/design/milestone1.md, "Second-wave kernels" and "Ball kernels", and the two
    # one-rounding kernels whose claims give the one-limb balls their constants.
    SECOND_WAVE = {'neg_2', 'abs_2', 'sub_2_2', 'sub_2_1', 'sub_1_2', 'lt_2_2', 'le_2_2', 'eq_2_2', 'lt_2_1',
                   'le_2_1', 'eq_2_1', 'lt_1_2', 'le_1_2', 'to_nearest_2', 'to_down_2', 'to_up_2',
                   'abs_upper_2', 'radd', 'rmul', 'mul_pow2_2', 'ball_add_1', 'ball_add_2', 'ball_mul_1',
                   'ball_mul_2', 'ball_scale_1', 'ball_scale_2', 'ball_neg_1', 'ball_neg_2', 'ball_sub_1',
                   'ball_sub_2', 'add_1_1', 'mul_1_1'}

    # docs/developer/design/milestone1.md, "IEEE-like results", "Values that enter from the program"
    # and "Ball kernels": the full kernels and the constructors.
    FULL = {f'{core}_full' for core in ('add_2_2', 'add_fast_2_2', 'sub_2_2', 'add_2_1', 'sub_2_1', 'sub_1_2',
                                        'mul_2_2', 'mul_2_1', 'mul_pow2_2')}
    FULL_BALL = {f'ball_{op}_{k}_full' for op in ('add', 'sub', 'mul', 'scale') for k in (1, 2)}
    CONSTRUCTORS = {'make_2', 'make_2_limbs', 'ball_make_1', 'ball_make_2'}
    NON_FINITE = FULL | FULL_BALL | CONSTRUCTORS
    # The kernels that need no fix-up (milestone1.md): the extended domain, with both statements.
    NO_FIX_UP = {'neg_2', 'abs_2', 'lt_2_2', 'le_2_2', 'eq_2_2', 'lt_2_1', 'le_2_1', 'eq_2_1', 'lt_1_2', 'le_1_2',
                 'to_nearest_2', 'to_down_2', 'to_up_2', 'abs_upper_2', 'radd', 'rmul'}

    def test_kernel_names_are_those_of_the_listings(self):
        ks = common.kernels()
        self.assertEqual(set(ks), self.FIRST_WAVE | self.SECOND_WAVE | self.NON_FINITE)
        body = {name: [(st.dsts, st.op, tuple(map(str, st.args))) for st in k.body] for name, k in ks.items()}
        self.assertEqual(body['two_sum'], [
            (('s',), 'add', ('a', 'b')), (('bb',), 'sub', ('s', 'a')), (('t0',), 'sub', ('s', 'bb')),
            (('t1',), 'sub', ('a', 't0')), (('t2',), 'sub', ('b', 'bb')), (('e',), 'add', ('t1', 't2'))])
        self.assertEqual(body['mul_2_2'], [
            (('ch', 'cl1'), 'two_prod', ('x0', 'y0')), (('tl0',), 'prod', ('x1', 'y1')),
            (('tl1',), 'fma', ('x0', 'y1', 'tl0')), (('cl2',), 'fma', ('x1', 'y0', 'tl1')),
            (('cl3',), 'add', ('cl1', 'cl2')), (('z0', 'z1'), 'fast_two_sum', ('ch', 'cl3'))])
        self.assertEqual(body['split'], [
            (('g',), 'prod', ('const splitter', 'a')), (('d',), 'sub', ('a', 'g')),
            (('ah',), 'add', ('g', 'd')), (('al',), 'sub', ('a', 'ah'))])
        # add_fast_2_2 ends with Fast2Sum: its normalization is proved, so there is no variant
        # ending with TwoSum.
        self.assertEqual(body['add_fast_2_2'][-1], (('z0', 'z1'), 'fast_two_sum', ('sh', 'w')))
        # Proved means: the audit passes for that kernel (make -C proofs). Every kernel of the real
        # model is; the full kernels and the constructors have no real-model statement, and their
        # IEEE-model statements are not proved.
        self.assertEqual({name for name, k in ks.items() if k.status == 'proved'},
                         self.FIRST_WAVE | self.SECOND_WAVE)
        self.assertEqual({name for name, k in ks.items() if k.status == 'unverified'}, self.NON_FINITE)
        self.assertEqual({name for name, k in ks.items() if not k.real_model}, self.NON_FINITE)
        self.assertEqual({name for name, k in ks.items() if k.extended}, self.NON_FINITE | self.NO_FIX_UP)
        self.assertEqual({name: k.ieee_status for name, k in ks.items() if k.extended},
                         dict.fromkeys(self.NON_FINITE | self.NO_FIX_UP, 'unverified'))
        self.assertFalse(any(k.ieee_theorem for k in ks.values()))
        # The minimum precision of a full kernel is that of its core; a constructor's is 1.
        for name in self.FULL | self.FULL_BALL:
            core = name[:-len('_full')]
            self.assertEqual(ks[name].min_precision, ks[core].min_precision, name)
        self.assertEqual({ks[n].min_precision for n in self.CONSTRUCTORS}, {1})
        self.assertEqual(ks['two_prod'].ce_variant, 'two_prod_dekker')
        # The smallest precision from which each proved statement holds.
        self.assertEqual({name: k.min_precision for name, k in ks.items() if k.status == 'proved'}, {
            'two_sum': 2, 'fast_two_sum': 2, 'two_prod': 2, 'split': 4, 'two_prod_dekker': 4,
            'add_2_2': 3, 'add_2_1': 3, 'mul_2_2': 4, 'mul_2_1': 2, 'add_fast_2_2': 2,
            'neg_2': 1, 'abs_2': 1, 'sub_2_2': 3, 'sub_2_1': 3, 'sub_1_2': 3,
            'lt_2_2': 1, 'le_2_2': 1, 'eq_2_2': 1, 'lt_2_1': 1, 'le_2_1': 1, 'eq_2_1': 1, 'lt_1_2': 1,
            'le_1_2': 1, 'to_nearest_2': 1, 'to_down_2': 1, 'to_up_2': 1, 'abs_upper_2': 1,
            'radd': 2, 'rmul': 2, 'mul_pow2_2': 2, 'add_1_1': 1, 'mul_1_1': 1,
            'ball_add_1': 2, 'ball_sub_1': 2, 'ball_neg_1': 1, 'ball_mul_1': 2, 'ball_scale_1': 2,
            'ball_add_2': 3, 'ball_sub_2': 3, 'ball_neg_2': 1, 'ball_mul_2': 4, 'ball_scale_2': 2})

    def test_second_wave_bodies_are_those_of_milestone1_md(self):
        ks = common.kernels()

        def body(name):
            return [f'{", ".join(st.dsts)} = {st.op}({", ".join(map(str, st.args))})' for st in ks[name].body]

        self.assertEqual(body('abs_2'), ['m = lt(x0, 0)', 'n0 = neg(x0)', 'n1 = neg(x1)',
                                         'z0 = select(m, n0, x0)', 'z1 = select(m, n1, x1)'])
        self.assertEqual(body('sub_2_2'), ['n0 = neg(y0)', 'n1 = neg(y1)', 'z0, z1 = add_2_2(x0, x1, n0, n1)'])
        self.assertEqual(body('lt_2_2'), ['h = lt(x0, y0)', 'e = eq(x0, y0)', 'l = lt(x1, y1)', 't = and(e, l)',
                                          'm = or(h, t)'])
        self.assertEqual(body('le_1_2'), ['h = lt(a, y0)', 'e = eq(a, y0)', 'l = le(0, y1)', 't = and(e, l)',
                                          'm = or(h, t)'])
        self.assertEqual(body('eq_2_1'), ['h = eq(x0, a)', 'l = eq(x1, 0)', 'm = and(h, l)'])
        self.assertEqual(body('to_nearest_2'), ['t = copy(x0)'])
        self.assertEqual(body('to_down_2'), ['m = lt(x1, 0)', 'p = pred(x0)', 't = select(m, p, x0)'])
        self.assertEqual(body('to_up_2'), ['m = lt(0, x1)', 's = succ(x0)', 't = select(m, s, x0)'])
        self.assertEqual(body('abs_upper_2'), ['a0, a1 = abs_2(x0, x1)', 't = to_up_2(a0, a1)'])
        self.assertEqual(body('radd'), ['s = add(a, b)', 'r = succ(s)'])
        self.assertEqual(body('rmul'), ['p = prod(a, b)', 'r = succ(p)'])
        self.assertEqual(body('mul_pow2_2'), ['h = prod(x0, c)', 'l = prod(x1, c)', 'z0, z1 = fast_two_sum(h, l)'])
        self.assertEqual(body('ball_add_2'), [
            'cz0, cz1 = add_2_2(cx0, cx1, cy0, cy1)', 'mz = abs_upper_2(cz0, cz1)',
            'd = rmul(const unit_computed(add_2_2), mz)', 'r0 = radd(rx, ry)', 'rz = radd(r0, d)'])
        self.assertEqual(body('ball_mul_1'), [
            'cz = prod(cx, cy)', 'ax = abs(cx)', 'ay = abs(cy)', 't1 = rmul(ax, ry)', 't2 = rmul(ay, rx)',
            't3 = rmul(rx, ry)', 's1 = radd(t1, t2)', 's2 = radd(s1, t3)', 'mz = abs(cz)',
            'd0 = rmul(const unit_computed(mul_1_1), mz)', 'd = radd(d0, const tiny_computed(mul_1_1))',
            'rz = radd(s2, d)'])
        self.assertEqual(body('ball_scale_2'), [
            'cz0, cz1 = mul_2_1(cx0, cx1, a)', 'aa = abs(a)', 't1 = rmul(aa, rx)', 'mz = abs_upper_2(cz0, cz1)',
            'd0 = rmul(const unit_computed(mul_2_1), mz)', 'd = radd(d0, const tiny_computed(mul_2_1))',
            'rz = radd(t1, d)'])
        # The two-limb balls take their constants from the proved kernels of their centers.
        for name, center in (('ball_add_2', 'add_2_2'), ('ball_mul_2', 'mul_2_2'), ('ball_scale_2', 'mul_2_1')):
            self.assertEqual(ks[name].body[0].op, center)
            self.assertEqual({ir.computed(c)[1] for c in ir.constants(ks[name]) if ir.computed(c)}, {center})
            self.assertEqual(ks[center].status, 'proved')

    def test_flops(self):
        # The operation counts of docs/developer/design/phase0/operations.md.
        ks = common.kernels()
        self.assertEqual({n: ir.flops(ks[n], ks) for n in ('add_2_2', 'add_fast_2_2', 'add_2_1', 'mul_2_2', 'mul_2_1')},
                         {'add_2_2': 20, 'add_fast_2_2': 11, 'add_2_1': 10, 'mul_2_2': 9, 'mul_2_1': 6})


if __name__ == '__main__':
    unittest.main()
