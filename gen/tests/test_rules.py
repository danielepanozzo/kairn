"""The rules refuse wrong kernels with a message naming the kernel, the value and the rule."""
import copy
import dataclasses
import os
import re
import unittest

import common
from kairn_gen import build, ir, rules

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


# The steps of the maps (stage B): sub_1_1, and the steps that guard or only multiply what the
# program supplies.
MAP_STEPS = {'sub_1_1', 'add_entry_step_1', 'sub_entry_step_1', 'add_entry_step_2', 'sub_entry_step_2',
             'scale_step_1', 'scale_step_2', 'mul_pow2_step_1', 'mul_pow2_step_2', 'axpy_step_1',
             'axpy_entry_step_1', 'axpy_step_2', 'axpy_entry_step_2', 'axpy_step_2_1', 'axpy_entry_step_2_1'}
# The maps (stage B).
MAPS = {'add_1', 'add_1_entry', 'add_2', 'add_2_entry', 'sub_1', 'sub_1_entry', 'sub_2', 'sub_2_entry', 'axpy_1',
        'axpy_1_entry', 'axpy_2', 'axpy_2_entry', 'axpy_2_1', 'axpy_2_1_entry', 'scale_1', 'scale_2',
        'mul_pow2_map_1', 'mul_pow2_map_2'}


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

    def test_a_negated_fused_result(self):
        # Compilers fold the negation into the fused instruction (gen/README.md): refused, with
        # what to write instead; also through a call, the callee inlined.
        errors = check(HEAD + 'p = prod(a, b)\nq = neg(p)\ns = add(a, b)\nz = sub(s, a)\ne = sub(q, z)\n')
        self.refused(errors, 'bad', 'q', rules.NEGATED_FUSED, 'q = neg(p) negates the result of prod')
        self.refused(errors, 'bad', 'q', rules.NEGATED_FUSED, 'prod(neg(a), b)')
        errors = check(HEAD + 'p = fma(a, b, a)\nq = neg(p)\ns = add(a, b)\nz = sub(s, a)\ne = sub(q, z)\n')
        self.refused(errors, 'bad', 'q', rules.NEGATED_FUSED, 'negates the result of fma')
        negate = ('kernel:  negate\ninput:   x\noutput:  n\nvalue:   -x\nensures: error n R c=0 k=1 t=0\n'
                  'status:  unverified\n\nn = neg(x)\n')
        errors = check(negate, HEAD + 'p = prod(a, b)\nm = negate(p)\ns = add(a, b)\nz = sub(s, a)\ne = sub(m, z)\n')
        negated = [e for e in errors if e.rule == rules.NEGATED_FUSED]
        self.assertEqual([e.kernel for e in negated], ['bad'])
        self.assertIn('negates the result of prod', str(negated[0]))
        # A negated operand is not a negated result.
        self.assertEqual(check(HEAD + 'n = neg(a)\np = prod(n, b)\ns = add(p, b)\nz = sub(s, p)\ne = sub(b, z)\n'), [])

    def test_a_negated_select_of_a_fused_result(self):
        # Compilers push a negation through a select into its arms (Apple clang and GCC 13 on the
        # radius of add_down_2_2 as first written): a select one of whose arms is a fused result,
        # in either arm, through selects of selects and copies, and through a call, is refused.
        tail = 's = add(q, b)\nz = sub(s, q)\ne = sub(b, z)\n'
        head = HEAD + 'cone_exempt: selected\n'
        for arms in ('a, p', 'p, a', 'p, 0'):
            errors = check(head + f'p = prod(a, b)\nc = eq(a, 0)\nt = select(c, {arms})\nq = neg(t)\n' + tail)
            self.refused(errors, 'bad', 'q', rules.NEGATED_FUSED,
                         'q = neg(t) negates a select one of whose arms, p, is the result of prod')
            self.refused(errors, 'bad', 'q', rules.NEGATED_FUSED, 'push a negation through a select')
        errors = check(head + 'p = fma(a, b, a)\nc = eq(a, 0)\nd = lt(a, b)\nt = select(c, a, p)\n'
                       'w = select(d, b, t)\nq = neg(w)\n' + tail)
        self.refused(errors, 'bad', 'q', rules.NEGATED_FUSED, 'arms, p, is the result of fma')
        errors = check(head + 'p = prod(a, b)\nc = eq(a, 0)\nt = select(c, 0, p)\nw = copy(t)\nq = neg(w)\n' + tail)
        self.refused(errors, 'bad', 'q', rules.NEGATED_FUSED, 'negates a copy one of whose arms, p')
        # Through a call: the callee negates its operand, as sub_down_1 negates its second.
        minus = ('kernel:  minus\ninput:   x\ninput:   y\noutput:  r\nvalue:   x-y\nensures: error r R c=1 k=1 t=0\n'
                 'status:  unverified\n\nny = neg(y)\nr  = add(x, ny)\n')
        errors = check(minus, head + 'p = prod(a, b)\nc = eq(a, 0)\nt = select(c, 0, p)\nq = minus(b, t)\n' + tail)
        negated = [e for e in errors if e.rule == rules.NEGATED_FUSED]
        self.assertEqual([(e.kernel, e.value) for e in negated], [('bad', 'q_ny')])
        self.assertIn('negates a select one of whose arms, p, is the result of prod (inside a call', str(negated[0]))
        # A select of values none of which is a fused result is not refused, nor a select of a
        # fused result whose operand was negated, nor a fused result selected and not negated.
        self.assertEqual(check(head + 'p = add(a, b)\nc = eq(a, 0)\nt = select(c, 0, p)\nq = neg(t)\n' + tail), [])
        self.assertEqual(check(head + 'n = neg(a)\np = prod(n, b)\nc = eq(a, 0)\nq = select(c, 0, p)\n' + tail), [])

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

    def test_a_value_added_to_itself(self):
        # GCC writes a + a as a * 2 and contracts it into the addition that follows.
        errors = check(HEAD + 'd = add(a, a)\ns = add(d, b)\nz = sub(s, d)\ne = sub(b, z)\n')
        self.refused(errors, 'bad', 'd', rules.RULE_R1, 'adds a value to itself')

    def test_a_value_added_to_its_copy(self):
        errors = check(HEAD + 'c = copy(a)\nd = add(a, c)\ns = add(d, b)\nz = sub(s, d)\ne = sub(b, z)\n')
        self.refused(errors, 'bad', 'd', rules.RULE_R1, 'd = add(a, a) adds a value to itself')

    def test_a_value_passed_twice_to_an_addition(self):
        # Through a call: the callee adds its two inputs, the caller gives it one value twice.
        callee = HEAD.replace('kernel:  bad', 'kernel:  callee') + GOOD
        self.assertEqual(check(callee), [])
        caller = HEAD.replace('kernel:  bad', 'kernel:  caller') + '(p, q) = callee(a, a)\ns = add(p, b)\ne = add(q, b)\n'
        errors = check(callee, caller)
        self.refused(errors, 'caller', 'p', rules.RULE_R1, 'p = add(a, a) adds a value to itself')
        self.assertEqual([e for e in errors if e.kernel == 'callee'], [])

    def test_a_doubling_as_an_opaque_product_is_accepted(self):
        self.assertEqual(check(HEAD + 'd = prod(a, const up(2))\ns = add(d, b)\nz = sub(s, d)\ne = sub(b, z)\n'), [])

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


class R3(unittest.TestCase):
    """Rule R3 (architecture.md, "The kernel IR"): in an entry kernel, a value that enters from the
    program, or what neg, abs, select or copy alone make of it, is never an operand of add or sub
    nor the addend of an FMA before it has passed through guard."""
    ENTRY = '''
kernel:   k
input:    x = x0 x1
input:    a
output:   z = z0 z1
value:    x+a
requires: normalized x
ensures:  error z R c=0 k=2 t=0
status:   unverified
entry:    yes
cone_exempt: only rule R3 is judged here
'''
    # A callee that adds its second operand, one that only multiplies it, and one that returns it.
    ADDS = '''
kernel:  adds
input:   p
input:   q
output:  s
value:   p+q
ensures: error s R c=0 k=1 t=0
status:  unverified
s = add(p, q)
'''
    MULTIPLIES = ADDS.replace('kernel:  adds', 'kernel:  multiplies').replace('p+q', 'p*q') \
                     .replace('s = add(p, q)', 's = prod(p, q)')
    RETURNS = '''
kernel:  returns
input:   p
output:  r
value:   -p
ensures: error r R c=0 k=1 t=0
status:  unverified
r = neg(p)
'''

    def r3(self, body, *more, head=None):
        errors = check((head or self.ENTRY) + body, self.ADDS, self.MULTIPLIES, self.RETURNS, *more)
        others = [e for e in errors if e.rule not in (rules.RULE_R3, rules.RULE_CONE)]
        self.assertEqual(others, [], body)
        return [e for e in errors if e.rule == rules.RULE_R3]

    def refused(self, body, value, words, *more, head=None, kernel='k'):
        errors = self.r3(body, *more, head=head)
        self.assertTrue(any(e.kernel == kernel and e.value == value and words in str(e) for e in errors),
                        f'no refusal of {kernel}, {value} mentioning {words!r} in:\n' +
                        ('\n'.join(map(str, errors)) or 'accepted'))

    END = 'z0 = add(s, x1)\nz1 = sub(z0, s)\n'

    # Each way of breaking the rule is caught.

    def test_direct_addition(self):
        self.refused('s = add(x0, a)\n' + self.END, 'a', 'reaches an operand of add at s without passing '
                                                         'through guard')
        self.refused('s = sub(a, x0)\n' + self.END, 'a', 'an operand of sub at s')

    def test_through_a_negation_and_an_absolute_value(self):
        self.refused('n = neg(a)\ns = add(x0, n)\n' + self.END, 'a', 'an operand of add at s')
        self.refused('n = abs(a)\nm = neg(n)\ns = sub(x0, m)\n' + self.END, 'a', 'an operand of sub at s')

    def test_through_a_select_and_a_copy(self):
        self.refused('m = lt(x0, x1)\nq = select(m, x1, a)\ns = add(x0, q)\n' + self.END, 'a',
                     'an operand of add at s')
        self.refused('c = copy(a)\ns = add(x0, c)\n' + self.END, 'a', 'an operand of add at s')

    def test_as_the_addend_of_an_fma(self):
        for op in ('fma', 'fms', 'fnma', 'muladd'):
            self.refused(f'p = {op}(x0, x1, a)\ns = add(p, x0)\n' + self.END, 'a', f'the addend of {op} at p')

    def test_through_a_call_into_an_input_the_callee_adds(self):
        self.refused('s = adds(x0, a)\n' + self.END, 'a', 'an operand of add at s in adds (called for s)')
        self.refused('n = neg(a)\ns = adds(n, x0)\n' + self.END, 'a', 'in adds (called for s)')

    def test_through_a_value_a_callee_returns(self):
        self.refused('r = returns(a)\ns = add(x0, r)\n' + self.END, 'a', 'an operand of add at s')

    def test_limbs_the_program_supplies(self):
        head = self.ENTRY.replace('input:    x = x0 x1', 'input:    supplied x = x0 x1')
        self.refused('g = guard(a)\ns = add(x0, g)\n' + self.END, 'x0', 'an operand of add at s', head=head)

    # Each allowed use passes.

    def test_factor_and_comparison(self):
        self.assertEqual(self.r3('p = prod(x0, a)\nq = fma(a, x1, x0)\nm = lt(a, x0)\nw = select(m, p, q)\n'
                                 's = add(w, p)\n' + self.END), [])

    def test_through_a_call_into_an_input_the_callee_multiplies(self):
        self.assertEqual(self.r3('n = abs(a)\np = multiplies(x0, n)\ns = add(p, x0)\n' + self.END), [])

    def test_guarded(self):
        self.assertEqual(self.r3('g = guard(a)\ns = add(x0, g)\n' + self.END), [])
        self.assertEqual(self.r3('n = neg(a)\ng = guard(n)\ns = adds(x0, g)\n' + self.END), [])
        self.assertEqual(self.r3('g = guard(a)\nr = returns(g)\ns = add(x0, r)\n' + self.END), [])

    def test_stored(self):
        head = self.ENTRY.replace('input:    a', 'input:    stored a')
        self.assertEqual(self.r3('s = add(x0, a)\n' + self.END, head=head), [])
        self.assertEqual(self.r3('s = adds(x0, a)\n' + self.END, head=head), [])

    def test_the_limbs_of_a_multi_limb_input_are_stored(self):
        self.assertEqual(self.r3('g = guard(a)\ns = add(x0, x1)\nt = add(s, g)\nz0 = add(t, x1)\n'
                                 'z1 = sub(z0, t)\n'), [])

    def test_only_entry_kernels(self):
        head = self.ENTRY.replace('entry:    yes\n', '')
        self.assertEqual(self.r3('s = add(x0, a)\n' + self.END, head=head), [])

    def test_declarations(self):
        self.refused('g = guard(a)\ns = add(x0, g)\n' + self.END, 'x', 'stored is said of a one-limb input',
                     head=self.ENTRY.replace('input:    x = x0 x1', 'input:    stored x = x0 x1'))
        self.refused('s = add(x0, a)\n' + self.END, 'a', 'supplied is said of a multi-limb input',
                     head=self.ENTRY.replace('input:    a', 'input:    supplied a'))
        self.refused('s = add(x0, a)\n' + self.END, 'a', 'only an entry kernel says where its inputs come from',
                     head=self.ENTRY.replace('entry:    yes\n', '').replace('input:    a', 'input:    stored a'))
        with self.assertRaises(ir.DescriptionError):
            check(self.ENTRY.replace('entry:    yes', 'entry:    no') + 's = add(x0, a)\n' + self.END)

    # The pending guard.

    def test_pending(self):
        head = self.ENTRY + 'guard_pending: a the reason\n'
        self.assertEqual(self.r3('s = add(x0, a)\n' + self.END, head=head), [])
        self.assertEqual(self.r3('s = adds(x0, a)\n' + self.END, head=head), [])
        self.refused('g = guard(a)\ns = add(x0, g)\n' + self.END, 'a', 'is never added unguarded; remove the '
                     'declaration', head=head)
        self.refused('s = add(x0, a)\n' + self.END, 'a', 'not an input that enters from the program',
                     head=head.replace('input:    a', 'input:    stored a'))
        self.refused('s = add(x0, a)\n' + self.END, 'a', 'only an entry kernel has values that enter',
                     head=head.replace('entry:    yes\n', ''))
        with self.assertRaises(ir.DescriptionError):
            check(self.ENTRY + 'guard_pending: a\n' + 's = add(x0, a)\n' + self.END)

    def test_accepted_through_the_pending_guard_of_a_callee(self):
        callee = self.ENTRY.replace('kernel:   k', 'kernel:   inner') + 'guard_pending: a the reason\n' + \
            's = add(x0, a)\n' + self.END
        caller = self.ENTRY.replace('kernel:   k', 'kernel:   outer')
        body = 'n = neg(a)\n(z0, z1) = inner(x0, x1, n)\n'
        kernels = {}
        for text in (callee, caller + body):
            k = ir.parse_kernel(text, 'test')
            kernels[k.name] = k
        kernels = ir.ordered(kernels)
        self.assertEqual([e for e in rules.check_all(kernels) if e.rule == rules.RULE_R3], [])
        pending, through = rules.r3_report(kernels)
        self.assertEqual(pending, {'inner': {'a': 'the reason'}})
        self.assertEqual(through, {'outer': ['inner']})
        # Without the declaration, both are refused: the caller for the callee's addition.
        kernels['inner'].guard_pending = {}
        errors = [e for e in rules.check_all(kernels) if e.rule == rules.RULE_R3]
        self.assertEqual({(e.kernel, e.value) for e in errors}, {('inner', 'a'), ('outer', 'a')})
        self.assertIn('an operand of add at s in inner (called for z0)',
                      str([e for e in errors if e.kernel == 'outer'][0]))


class NonFiniteLayer(unittest.TestCase):
    """The description format and the rules of the non-finite layer (architecture.md, "Claims of
    the non-finite layer"): a full kernel, a full ball kernel and a constructor, and each misuse."""
    CORE = '''
kernel:  core
input:   x = x0 x1
input:   a
output:  z = z0 z1
value:   x+a
requires: normalized x
ensures: error z R c=0 k=2 t=0
min_precision: 2
status:  unverified
s  = add(x0, a)
z0 = add(s, x1)
z1 = sub(z0, s)
'''
    FULL = '''
kernel:  full
input:   x = x0 x1
input:   a
output:  w = w0 w1
value:   x+a
requires: canonical x
ensures: extends w core=core lead=add finite_when=abs_le(x,-2);abs_le(abs(x)*a,0)
min_precision: 2
status:  unverified
domain:  extended
ieee_status: unverified
cone_exempt: the fix-up selects
(z0, z1) = core(x0, x1, a)
t  = add(x0, a)
m  = abs(z0)
f  = lt(m, const inf)
r0 = prod(t, const inf)
n  = eq(r0, r0)
r1 = select(n, 0, r0)
w0 = select(f, z0, r0)
w1 = select(f, z1, r1)
'''
    BALL = '''
kernel:  ballk
input:   stored c
input:   stored r
output:  cw
output:  rw
value:   c
requires: ball c r
ensures: encloses cw rw x x=c,r finite_when=abs_le(c,-1)
min_precision: 1
status:  unverified
domain:  extended
ieee_status: unverified
entry:   yes
ieee_only: yes
cone_exempt: selects
e  = eq(r, r)
cw = select(e, c, const nan)
rw = copy(r)
'''
    MAKE = '''
kernel:  maker
input:   c
input:   r
output:  cw
output:  rw
ensures: makes_ball cw rw from=c,r
min_precision: 1
status:  unverified
domain:  extended
ieee_status: unverified
entry:   yes
cone_exempt: selects
g  = guard(r)
e  = le(0, g)
h  = guard(c)
cw = select(e, h, const nan)
rw = select(e, g, const nan)
'''

    def errors(self, *texts, rule=None):
        errs = check(*texts)
        return [e for e in errs if rule is None or e.rule == rule]

    def refused(self, words, *texts, rule=None):
        errs = self.errors(*texts, rule=rule)
        self.assertTrue(any(words in str(e) for e in errs), f'nothing mentions {words!r} in:\n' +
                        ('\n'.join(map(str, errs)) or 'accepted'))

    def test_accepted_and_parsed(self):
        self.assertEqual(check(self.CORE, self.FULL, self.BALL, self.MAKE), [])
        full = ir.parse_kernel(self.FULL, 't')
        self.assertTrue(full.extended and not full.real_model)
        self.assertEqual((full.domain, full.ieee_status, full.entry), ('extended', 'unverified', False))
        self.assertEqual(full.requires, [('canonical', 'x')])
        self.assertEqual(full.ensures, [{'kind': 'extends', 'of': 'w', 'core': 'core', 'lead': 'add',
                                         'finite_when': [{'abs_le': 'x', 'exp': -2},
                                                         {'abs_le': 'abs(x)*a', 'exp': 0}]}])
        ball = ir.parse_kernel(self.BALL, 't')
        self.assertEqual((ball.stored, ball.entry, ball.requires), ({'c', 'r'}, True, [('ball', 'c', 'r')]))
        self.assertEqual(ball.ensures[0]['finite_when'], [{'abs_le': 'c', 'exp': -1}])
        self.assertFalse(ball.real_model)
        make = ir.parse_kernel(self.MAKE, 't')
        self.assertEqual(make.ensures, [{'kind': 'makes_ball', 'center': 'cw', 'radius': 'rw',
                                         'from': {'center': 'c', 'radius': 'r'}}])
        self.assertIsNone(make.value)
        self.assertEqual(make.program_values(), ['c', 'r'])
        # In the extended domain an encloses entry without finite_when has an empty one.
        k = ir.parse_kernel(self.BALL.replace(' finite_when=abs_le(c,-1)', ''), 't')
        self.assertEqual(k.ensures[0]['finite_when'], [])
        k = ir.parse_kernel(self.FULL.replace(' finite_when=abs_le(x,-2);abs_le(abs(x)*a,0)', ''), 't')
        self.assertEqual(k.ensures[0]['finite_when'], [])
        rep = ir.parse_kernel('kernel: r\ninput: a\noutput: x = x0 x1\nvalue: a\nensures: represents x\n'
                              'ieee_theorem: proofs/theories/X.v r_ieee\n', 't')
        self.assertEqual((rep.ensures, rep.ieee_theorem), ([{'kind': 'represents', 'of': 'x'}],
                                                           ('proofs/theories/X.v', 'r_ieee')))
        self.assertFalse(rep.real_model)

    def test_malformed_descriptions(self):
        for old, new in (('lead=add', ''), ('core=core', ''), ('lead=add', 'lead=add lead=sub'),
                         ('finite_when=abs_le(x,-2);', 'finite_when=x<-2;'),
                         ('finite_when=abs_le(x,-2);', 'finite_when=abs_le(x);'),
                         ('ieee_status: unverified', 'ieee_status: unverified\nieee_status: proved'),
                         ('ieee_status: unverified', 'ieee_status: unverified\nieee_theorem: X.v'),
                         ('domain:  extended', 'domain:  extended\ndomain:  extended')):
            with self.assertRaises(ir.DescriptionError, msg=new):
                ir.parse_kernel(self.FULL.replace(old, new), 't')
        with self.assertRaises(ir.DescriptionError):
            ir.parse_kernel(self.MAKE.replace('from=c,r', 'c,r'), 't')
        with self.assertRaises(ir.DescriptionError):
            ir.parse_kernel(self.BALL.replace('finite_when=abs_le(c,-1)', 'finite_when=c'), 't')

    def test_domains(self):
        self.refused('it is extended, or the line is left out', self.CORE, self.FULL.replace('extended', 'finite'),
                     rule=rules.DOMAIN)
        self.refused('is of the extended domain', self.CORE,
                     self.FULL.replace('domain:  extended\nieee_status: unverified\n', ''), rule=rules.DOMAIN)
        self.refused('not a claim of the finite domain', self.CORE,
                     self.FULL.replace('domain:  extended\nieee_status: unverified\n', ''), rule=rules.CLAIMS)
        self.refused('finite_when belongs to the extended domain',
                     self.BALL.replace('domain:  extended\nieee_status: unverified\n', '')
                              .replace('requires: ball c r', 'requires: nonneg r'), rule=rules.DOMAIN)
        # The real model has no infinity and cannot call a kernel that is not in it.
        self.refused('const inf has no meaning in the real model',
                     self.CORE.replace('s  = add(x0, a)', 's  = add(x0, a)\nq  = lt(a, const inf)\n'
                                                          'k  = select(q, a, x1)')
                              .replace('z0 = add(s, x1)', 'z0 = add(s, k)'), rule=rules.DOMAIN)
        caller = self.CORE.replace('kernel:  core', 'kernel:  caller').replace(
            's  = add(x0, a)\nz0 = add(s, x1)\nz1 = sub(z0, s)', '(z0, z1) = full(x0, x1, a)')
        self.refused('full has no real-model statement, so a kernel that has one cannot call it',
                     self.CORE, self.FULL, caller, rule=rules.DOMAIN)

    def test_requirements(self):
        self.refused('canonical is not a requirement of the finite domain',
                     self.CORE.replace('normalized x', 'canonical x'), rule=rules.CLAIMS)
        self.refused('canonical stands for normalized there', self.CORE,
                     self.FULL.replace('canonical x', 'normalized x'), rule=rules.CLAIMS)
        self.refused('canonical is about a multi-limb input', self.CORE,
                     self.FULL.replace('requires: canonical x', 'requires: canonical x\nrequires: canonical a'),
                     rule=rules.CLAIMS)
        self.refused('the radius of a ball is a one-limb input',
                     self.BALL.replace('input:   stored r', 'input:   r = r0 r1')
                              .replace('e  = eq(r, r)', 'e  = eq(r0, r1)').replace('rw = copy(r)', 'rw = copy(r0)'),
                     rule=rules.CLAIMS)
        self.refused('is required to be a ball', self.BALL.replace('requires: ball c r', 'requires: nonneg r'),
                     rule=rules.CLAIMS)
        self.refused('a kernel that makes a ball from its inputs has no value',
                     self.MAKE.replace('output:  rw', 'output:  rw\nvalue:   c'), rule=rules.CLAIMS)
        self.refused("makes_ball from radius 'q': not a one-limb limb input",
                     self.MAKE.replace('from=c,r', 'from=c,q'), rule=rules.CLAIMS)

    def test_extends(self):
        for old, new, words in (
                ('lead=add', 'lead=div', 'lead='),
                ('core=core', 'core=full', 'not another kernel'),
                ('core=core', 'core=nope', 'not another kernel'),
                ('value:   x+a', 'value:   x-a', 'the value must be the core\'s'),
                ('min_precision: 2', 'min_precision: 3', 'the minimum precision is the core\'s'),
                ('requires: canonical x\n', '', 'the requirements are the core\'s with canonical for normalized'),
                ('abs_le(x,-2)', 'abs_le(q,-2)', 'unknown name'),
                ('ensures: extends w', 'ensures: error w R c=0 k=2 t=0\nensures: extends w', 'claims nothing else')):
            self.refused(words, self.CORE, self.FULL.replace(old, new), rule=rules.CLAIMS)
        renamed = self.CORE.replace('input:   a', 'input:   b').replace('x+a', 'x+b').replace('add(x0, a)',
                                                                                                'add(x0, b)')
        self.refused('the core must have the same inputs, names included', renamed, self.FULL, rule=rules.CLAIMS)
        extended_core = self.CORE.replace('normalized x', 'canonical x') + \
            'domain: extended\nieee_status: unverified\n'
        self.refused('a core is of the finite domain', extended_core, self.FULL, rule=rules.CLAIMS)

    def test_statuses(self):
        self.refused('a kernel of the extended domain gives one of', self.CORE,
                     self.FULL.replace('ieee_status: unverified\n', ''), rule=rules.RULE_THEOREM)
        self.refused('belong to kernels of the extended domain',
                     self.CORE.replace('status:  unverified', 'status:  unverified\nieee_status: unverified'),
                     rule=rules.RULE_THEOREM)
        self.refused('so its status is its ieee_status', self.CORE,
                     self.FULL.replace('status:  unverified', 'status:  proved\nsource: s\nlicense: l'),
                     rule=rules.RULE_THEOREM)
        self.refused('no real-model statement, so no theorem', self.CORE,
                     self.FULL + 'theorem: proofs/theories/X.v full_correct\n', rule=rules.RULE_THEOREM)
        self.refused('only once the IEEE-model statement is proved', self.CORE,
                     self.FULL + 'ieee_theorem: proofs/theories/X.v full_ieee\n', rule=rules.RULE_THEOREM)
        proved = self.FULL.replace('status:  unverified', 'status:  proved\nsource: s\nlicense: l') \
                          .replace('ieee_status: unverified', 'ieee_status: proved')
        self.refused('names no ieee_theorem', self.CORE, proved, rule=rules.RULE_THEOREM)
        self.assertEqual(self.errors(self.CORE, proved + 'ieee_theorem: proofs/theories/X.v full_ieee\n'), [])


class TimesInf(unittest.TestCase):
    """times_inf is a plain multiplication (by infinity, exact): its result may only be an
    operand of a comparison or of select, and an output only through select (rule R1)."""
    FULL = NonFiniteLayer.FULL.replace('r0 = prod(t, const inf)', 'r0 = times_inf(t)')

    def refused(self, old, new, words, rule=rules.RULE_R1):
        errors = check(NonFiniteLayer.CORE, self.FULL.replace(old, new))
        self.assertTrue(any(e.rule == rule and e.value == 'r0' and words in str(e) for e in errors),
                        f'nothing mentions {words!r} in:\n' + ('\n'.join(map(str, errors)) or 'accepted'))

    def test_compared_and_selected_is_accepted(self):
        self.assertEqual(check(NonFiniteLayer.CORE, self.FULL), [])
        self.assertIn('r0 = times_inf(t)', self.FULL)

    def test_each_forbidden_use(self):
        tail = 'w1 = select(f, z1, r1)'
        for use, words in (('q = add(r0, x0)', 'an operand of add at q'), ('q = sub(x0, r0)', 'an operand of sub at q'),
                           ('q = fma(r0, x0, x1)', 'an operand of fma at q'), ('q = fma(x0, x1, r0)', 'an operand of fma at q'),
                           ('q = fms(x0, x1, r0)', 'an operand of fms at q'), ('q = prod(r0, x0)', 'an operand of prod at q'),
                           ('q = muladd(x0, x1, r0)', 'an operand of muladd at q'), ('q = neg(r0)', 'an operand of neg at q'),
                           ('q = abs(r0)', 'an operand of abs at q'), ('q = copy(r0)', 'an operand of copy at q'),
                           ('q = guard(r0)', 'an operand of guard at q'), ('q = succ(r0)', 'an operand of succ at q'),
                           ('q = times_inf(r0)', 'an operand of times_inf at q'),
                           ('(q, e) = two(r0, x0)', 'passed to two at q')):
            body = f'{tail}\n{use}\nm2 = lt(q, x0)\n'
            callee = ('kernel: two\ninput: a\ninput: b\noutput: s = s0 s1\nvalue: a+b\nensures: error s R c=0 k=2 t=0\n'
                      'status: unverified\ns0 = add(a, b)\ns1 = sub(s0, a)\n')
            # q must be used: an extra output w2 selected from it.
            text = self.FULL.replace(tail, body).replace('output:  w = w0 w1', 'output:  w = w0 w1\noutput:  mask m2')
            if use.startswith('(q, e)'):
                text = text.replace('m2 = lt(q, x0)', 'm2 = lt(q, e)')
            errors = check(NonFiniteLayer.CORE, text, callee)
            self.assertTrue(any(e.rule == rules.RULE_R1 and e.value == 'r0' and words in str(e) for e in errors),
                            f'{use}: ' + ('\n'.join(map(str, errors)) or 'accepted'))

    def test_an_output_as_it_is(self):
        text = self.FULL.replace('output:  w = w0 w1', 'output:  w = w0 w1\noutput:  r0')
        errors = check(NonFiniteLayer.CORE, text)
        self.assertTrue(any(e.rule == rules.RULE_R1 and e.value == 'r0' and 'an output as it is' in str(e)
                            for e in errors), '\n'.join(map(str, errors)) or 'accepted')

    def test_not_in_the_real_model(self):
        core = NonFiniteLayer.CORE.replace('z1 = sub(z0, s)', 'z1 = sub(z0, s)\nq = times_inf(s)\nm = lt(q, s)\n'
                                                                'k = select(m, s, x1)\nz2 = add(z1, k)') \
                                  .replace('output:  z = z0 z1', 'output:  z = z0 z1 z2')
        errors = check(core)
        self.assertTrue(any(e.rule == rules.DOMAIN and 'times_inf has no meaning in the real model' in str(e)
                            for e in errors), '\n'.join(map(str, errors)) or 'accepted')

    def test_the_full_kernels_use_it(self):
        ks = common.kernels()
        for name in TheKernels.FULL:
            body = [f'{", ".join(st.dsts)} = {st.op}({", ".join(map(str, st.args))})' for st in ks[name].body]
            self.assertIn('r0 = times_inf(t)', body, name)
            self.assertFalse(any(st.op == 'prod' and any(a.name == 'inf' for a in st.args) for st in ks[name].body))


class R3Outputs(unittest.TestCase):
    """Rule R3: an entry kernel never returns a value that enters from the program as it is."""
    HEAD = R3.ENTRY.replace('output:   z = z0 z1', 'output:   z = z0 z1\noutput:   r')

    def errors(self, body, head=None):
        errs = check((head or self.HEAD) + 's = add(x0, x1)\nz0 = add(s, x0)\nz1 = sub(z0, s)\n' + body,
                     R3.RETURNS)
        return [e for e in errs if e.rule == rules.RULE_R3]

    def test_refused(self):
        for body in ('r = copy(a)', 'r = neg(a)', 'n = abs(a)\nr = neg(n)', 'm = lt(a, x0)\nr = select(m, a, x0)',
                     'r = returns(a)'):
            errs = self.errors(body + '\n')
            self.assertTrue(any(e.value == 'a' and 'is the output r as it is' in str(e) for e in errs),
                            f'{body}: ' + ('\n'.join(map(str, errs)) or 'accepted'))

    def test_accepted(self):
        for body in ('g = guard(a)\nr = copy(g)', 'r = prod(a, x0)', 'r = succ(a)', 'g = guard(a)\nr = returns(g)'):
            self.assertEqual(self.errors(body + '\n'), [], body)
        stored = self.HEAD.replace('input:    a', 'input:    stored a')
        self.assertEqual(self.errors('r = copy(a)\n', head=stored), [])
        self.assertEqual(self.errors('r = copy(a)\n', head=self.HEAD.replace('entry:    yes\n', '')), [])

    def test_no_kernel_returns_a_program_value(self):
        ks = common.kernels()
        self.assertFalse(any('as it is' in str(e) for e in rules.check_all(ks)))
        for k in ks.values():
            if k.entry:
                _, _, out = rules.r3_analysis(k, ks, frozenset(k.program_values()))
                self.assertEqual(out, {}, k.name)


class UpConstants(unittest.TestCase):
    """const up(EXPR): an exact expression over u, eta, integers, unit(K) and tiny(K), rounded up."""
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

    def user(self, expr_text, status='unverified', extra=''):
        head = self.USER.replace('status:  unverified', f'status:  {status}') + extra
        if status == 'proved':
            head += 'source: x\nlicense: MIT\ntheorem: proofs/theories/X.v user_correct\n'
        return head + f'k = prod(const up({expr_text}), a)\ns = add(k, b)\nz = sub(s, k)\ne = sub(b, z)\n'

    def errors(self, *texts):
        return [e for e in check(*texts) if e.rule in (rules.COMPUTED, rules.WELL_FORMED)]

    def test_accepted(self):
        for text in ('(1+u)^6', 'unit(bound)/(1-unit(bound))*(1+u)',
                     '(1+u) * ((1+u)^5*2*eta + tiny(bound)/(1-unit(bound)) + eta/2)', '2^-3*eta', '1/3'):
            for status in ('unverified', 'proved'):
                self.assertEqual(check(self.BOUND.format(status='proved'), self.user(text, status)), [], text)
        k = ir.parse_kernel(self.user('(1 + u) ^ 6'), 't')
        self.assertEqual(k.body[0].args[0], ir.Operand('up((1+u)^6)', const=True))

    def test_refused(self):
        for text, words in (('abs(u)', 'abs is not allowed'), ('v*u', 'unknown name v'),
                            ('u^u', 'an exponent is an integer'), ('u-1', 'it must be positive'),
                            ('unit(nope)', 'nope is not a kernel'), ('unit(user)', 'it must be positive'),
                            ('2^2000', 'overflows'), ('0', 'it must be positive')):
            errors = self.errors(self.BOUND.format(status='proved'), self.user(text))
            self.assertTrue(any(words in str(e) for e in errors), f'{text}: ' + ('\n'.join(map(str, errors)) or 'accepted'))
        # A proved kernel may use the bound of a proved kernel only; and not below its precision.
        errors = self.errors(self.BOUND.format(status='unverified'), self.user('unit(bound)', 'proved'))
        self.assertTrue(any('only an unverified kernel may use the constants' in str(e) for e in errors), errors)
        bound = self.BOUND.format(status='proved').replace('p = prod', 'min_precision: 3\np = prod')
        errors = self.errors(bound, self.user('tiny(bound)'))
        self.assertTrue(any('min_precision must be at least 3' in str(e) for e in errors), errors)
        self.assertEqual(self.errors(bound, self.user('tiny(bound)', extra='min_precision: 3\n')), [])

    def test_names_the_printers_make(self):
        errors = check(HEAD.replace('kernel:  bad', 'kernel:  up_x') + GOOD)
        self.assertTrue(any(e.kernel == 'up_x' and e.rule == rules.WELL_FORMED for e in errors), errors)

    def test_not_in_the_claims(self):
        # Powers and unit(K), tiny(K) belong to constants: a claim cannot use them.
        for old, new, words in (('c=0', 'c=2^3', 'a rational expression'), ('t=0', 't=tiny(bad)', 'a rational expression'),
                                ('value:   a+b', 'value:   a^2', 'only + - *')):
            errors = check(HEAD.replace(old, new) + GOOD)
            self.assertTrue(any(e.rule == rules.CLAIMS and words in str(e) for e in errors),
                            f'{new}: ' + ('\n'.join(map(str, errors)) or 'accepted'))


class IntervalClaims(unittest.TestCase):
    """The claims of the interval kernels (architecture.md, "Claims of the interval kernels"): a toy
    interval sum and a toy outward bound are accepted and parsed, and each misuse is refused."""
    IADD = '''
kernel:  iadd
input:   stored xl
input:   stored xu
input:   stored yl
input:   stored yu
output:  zl
output:  zu
requires: interval xl xu
requires: interval yl yu
ensures: encloses_interval zl zu x+y x=xl,xu y=yl,yu tight=rounded bounded_when=abs_le(x+y,omega) bounded_exactly
min_precision: 2
status:  unverified
domain:  extended
ieee_status: unverified
entry:   yes
cone_exempt: selects
nx = lt(xl, const inf)
ny = lt(yl, const inf)
ne = and(nx, ny)
l  = add(xl, yl)
h  = add(xu, yu)
mi = neg(const inf)
zl = select(ne, l, const inf)
zu = select(ne, h, mi)
'''
    OUT = '''
kernel:  odown
input:   x = x0 x1
input:   y = y0 y1
output:  l = l0 l1
value:   x+y
requires: normalized x
requires: normalized y
ensures: outward l below rel=2*u^2 abs=eta exact_when=zero(x+y)
status:  unverified
s  = add(x0, y0)
t  = add(x1, y1)
l0 = add(s, t)
l1 = sub(l0, s)
'''

    def refused(self, words, *texts):
        errs = check(*texts)
        self.assertTrue(any(words in str(e) for e in errs), f'nothing mentions {words!r} in:\n' +
                        ('\n'.join(map(str, errs)) or 'accepted'))

    def test_accepted_and_parsed(self):
        self.assertEqual(check(self.IADD, self.OUT), [])
        k = ir.parse_kernel(self.IADD, 't')
        self.assertFalse(k.real_model)
        self.assertEqual(k.requires, [('interval', 'xl', 'xu'), ('interval', 'yl', 'yu')])
        self.assertEqual(k.ensures, [{'kind': 'encloses_interval', 'lower': 'zl', 'upper': 'zu', 'set': 'x+y',
                                      'intervals': {'x': {'lower': 'xl', 'upper': 'xu'},
                                                    'y': {'lower': 'yl', 'upper': 'yu'}},
                                      'tight': {'kind': 'rounded'}, 'bounded_when': [{'abs_le': 'x+y', 'omega': True}],
                                      'bounded_exactly': True}])
        o = ir.parse_kernel(self.OUT, 't')
        self.assertTrue(o.real_model)
        self.assertEqual(o.ensures, [{'kind': 'outward', 'of': 'l', 'side': 'below', 'rel': '2*u^2', 'abs': 'eta',
                                      'exact_when': [{'zero': 'x+y'}]}])
        two = self.IADD.replace('tight=rounded', 'tight=outward;rel=u;abs=eta exact_lower=zero(xl+yl)')
        self.assertEqual(ir.parse_kernel(two, 't').ensures[0]['tight'],
                         {'kind': 'outward', 'rel': 'u', 'abs': 'eta', 'exact_when': {'lower': [{'zero': 'xl+yl'}]}})

    def test_refused(self):
        self.refused('the output has two limbs', self.OUT.replace('output:  l = l0 l1', 'output:  l')
                     .replace('l0 = add(s, t)\nl1 = sub(l0, s)', 'l = add(s, t)'))
        self.refused('no constant of a kernel with a real-model statement', self.OUT.replace('rel=2*u^2', 'rel=up(7*u)'))
        self.refused('unknown name v', self.OUT.replace('abs=eta', 'abs=v'))
        self.refused('is negative', self.OUT.replace('abs=eta', 'abs=-eta'))
        self.refused('zero(EXPR) is a condition of outward',
                     HEAD.replace('t=0', 't=0 exact_when=zero(a+b)') + GOOD)
        self.refused('its operand is required to be an interval', self.IADD.replace('requires: interval yl yu\n', ''))
        self.refused('abs_le(SET', self.IADD.replace('abs_le(x+y,omega)', 'abs_le(x,omega)'))
        self.refused('the set is the product of two intervals',
                     self.IADD.replace('tight=rounded', 'tight=rounded;steps=1;when=product_large'))
        self.refused('not a claim of the finite domain',
                     self.IADD.replace('domain:  extended\nieee_status: unverified\n', ''))
        self.refused('bounded_exactly needs a condition', self.IADD.replace(' bounded_when=abs_le(x+y,omega)', ''))
        self.refused('the bounds of an interval are two inputs',
                     self.IADD.replace('input:   stored yu', 'input:   yu = yu0 yu1')
                     .replace('h  = add(xu, yu)', 'h  = add(xu, yu0)\nq  = add(yu1, h)').replace('zu = select(ne, h, mi)',
                                                                                          'zu = select(ne, q, mi)'))
        self.refused('encloses names no ball',
                     NonFiniteLayer.BALL.replace(' x=c,r finite_when=abs_le(c,-1)', '').replace('requires: ball c r\n', ''))
        self.refused('zero_factor: the value is the product',
                     HEAD.replace('ensures: error r R c=0 k=2 t=0', 'ensures: rounded r down zero_factor')
                     .replace('output:  r = s e', 'output:  r').replace('status:  unverified',
                                                                       'status:  unverified\ndomain:  extended\n'
                                                                       'ieee_status: unverified\ncone_exempt: x')
                     + 's = add(a, b)\nr = succ(s)\n')
        mk = ('kernel:  mk\ninput:   lo\ninput:   hi = h0 h1\noutput:  zl\noutput:  zu\n'
              'ensures: makes_interval zl zu from=lo,hi\nstatus:  unverified\ndomain:  extended\n'
              'ieee_status: unverified\ncone_exempt: x\nq = add(h0, h1)\nm = lt(lo, q)\nzl = select(m, lo, q)\n'
              'zu = copy(q)\n')
        self.refused('makes_interval: the bounds given and returned', mk)


class EnclosureClaims(unittest.TestCase):
    """The claims of stage B1 (architecture.md, "Claims of the interval kernels: two limbs and the
    enclosure interface"): toy kernels of each new kind are accepted and parsed, and each misuse is
    refused."""
    TAIL = 'status:  unverified\ndomain:  extended\nieee_status: unverified\nentry:   yes\ncone_exempt: selects\n'
    HULL = ('kernel:  hull\ninput:   stored xl\ninput:   stored xu\ninput:   stored yl\ninput:   stored yu\n'
            'output:  zl\noutput:  zu\nrequires: interval xl xu\nrequires: interval yl yu\n'
            'ensures: interval_set zl zu union x=xl,xu y=yl,yu\n' + TAIL +
            'ml = lt(yl, xl)\nzl = select(ml, yl, xl)\nmu = lt(xu, yu)\nzu = select(mu, yu, xu)\n')
    MID = ('kernel:  mid\ninput:   stored xl\ninput:   stored xu\noutput:  m\noutput:  r\nrequires: interval xl xu\n'
           'ensures: ball_of_interval m r from=xl,xu special=ieee1788 rel=u abs=eta smallest_radius\n'
           'min_precision: 2\n' + TAIL +
           'hl = prod(xl, const up(1/2))\nhu = prod(xu, const up(1/2))\ns = add(hl, hu)\nd = sub(xu, s)\n'
           'ne = lt(xl, const inf)\nm = select(ne, s, const nan)\nr = select(ne, d, const nan)\n')
    TOI = ('kernel:  toi\ninput:   stored c\ninput:   stored r\noutput:  zl\noutput:  zu\nrequires: ball c r\n'
           'ensures: interval_of_ball zl zu x x=c,r tight=rounded\nmin_precision: 2\n' + TAIL +
           'l = sub(c, r)\nh = add(c, r)\nne = eq(r, r)\nmi = neg(const inf)\nzl = select(ne, l, const inf)\n'
           'zu = select(ne, h, mi)\n')
    SPLIT = ('kernel:  sp\ninput:   stored xl\ninput:   stored xu\noutput:  al\noutput:  au\noutput:  bl\n'
             'output:  bu\nrequires: interval xl xu\nensures: splits al au bl bu from=xl,xu\n' + TAIL +
             's = add(xl, xu)\nal = copy(xl)\nau = copy(s)\nbl = copy(s)\nbu = copy(xu)\n')
    EXT = ('kernel:  ext\ninput:   x = x0 x1\ninput:   y = y0 y1\noutput:  l = l0 l1\nvalue:   x*y\n'
           'requires: canonical x\nrequires: canonical y\nrequires: not_nan x\nrequires: not_nan y\n'
           'ensures: normalized l\nensures: outward l below rel=4*u^2 abs=eta zero_factor\nieee_only: yes\n' + TAIL +
           'p = prod(x0, y0)\nq = add(x1, y1)\nm = lt(p, const inf)\nl0 = select(m, p, 0)\nl1 = select(m, q, 0)\n')

    def refused(self, words, *texts):
        errs = check(*texts)
        self.assertTrue(any(words in str(e) for e in errs), f'nothing mentions {words!r} in:\n' +
                        ('\n'.join(map(str, errs)) or 'accepted'))

    def test_accepted_and_parsed(self):
        self.assertEqual(check(self.HULL), [])
        self.assertEqual(check(self.MID), [])
        self.assertEqual(check(self.TOI), [])
        self.assertEqual(check(self.SPLIT), [])
        self.assertEqual(check(self.EXT), [])
        intervals = {'x': {'lower': 'xl', 'upper': 'xu'}, 'y': {'lower': 'yl', 'upper': 'yu'}}
        self.assertEqual(ir.parse_kernel(self.HULL, 't').ensures, [
            {'kind': 'interval_set', 'lower': 'zl', 'upper': 'zu', 'set': 'union', 'intervals': intervals}])
        self.assertEqual(ir.parse_kernel(self.MID, 't').ensures, [
            {'kind': 'ball_of_interval', 'center': 'm', 'radius': 'r', 'from': {'lower': 'xl', 'upper': 'xu'},
             'special': 'ieee1788', 'rel': 'u', 'abs': 'eta', 'smallest_radius': True}])
        self.assertNotIn('smallest_radius', ir.parse_kernel(self.MID.replace(' smallest_radius', ''), 't').ensures[0])
        self.assertEqual(ir.parse_kernel(self.TOI, 't').ensures, [
            {'kind': 'interval_of_ball', 'lower': 'zl', 'upper': 'zu', 'set': 'x',
             'balls': {'x': {'center': 'c', 'radius': 'r'}}, 'tight': {'kind': 'rounded'}}])
        self.assertEqual(ir.parse_kernel(self.SPLIT, 't').ensures, [
            {'kind': 'splits', 'parts': [{'lower': 'al', 'upper': 'au'}, {'lower': 'bl', 'upper': 'bu'}],
             'from': {'lower': 'xl', 'upper': 'xu'}}])
        self.assertEqual(ir.parse_kernel(self.EXT, 't').ensures[1], {
            'kind': 'outward', 'of': 'l', 'side': 'below', 'rel': '4*u^2', 'abs': 'eta', 'zero_factor': True})
        for text in (self.HULL, self.MID, self.TOI, self.SPLIT, self.EXT):
            self.assertFalse(ir.parse_kernel(text, 't').real_model)
        imul = IntervalClaims.IADD.replace('x+y x=xl,xu', 'x*y x=xl,xu').replace('abs_le(x+y', 'abs_le(x*y') \
            .replace('bounded_exactly', 'zero_factor')
        self.assertEqual(check(imul), [])
        e = ir.parse_kernel(imul, 't').ensures[0]
        self.assertEqual(list(e)[-2:], ['bounded_when', 'zero_factor'])
        self.assertIs(e['zero_factor'], True)

    def test_refused(self):
        self.refused('the set operation is union or intersection', self.HULL.replace(' union ', ' join '))
        with self.assertRaises(ir.DescriptionError):        # two intervals, always
            ir.parse_kernel(self.HULL.replace(' y=yl,yu', ''), 't')
        self.refused('its operand is required to be an interval', self.HULL.replace('requires: interval yl yu\n', ''))
        self.refused('not a claim of the finite domain', self.HULL.replace('domain:  extended\nieee_status: unverified\n', ''))
        self.refused('special \'midpoint\'', self.MID.replace('special=ieee1788', 'special=midpoint'))
        self.refused('unknown name v', self.MID.replace('abs=eta', 'abs=v'))
        self.refused("ball_of_interval radius 'q': not a one-limb limb output",
                     self.MID.replace('ball_of_interval m r', 'ball_of_interval m q'))
        self.refused('tight is rounded', self.TOI.replace('tight=rounded', 'tight=exact'))
        self.refused('its operand is required to be a ball', self.TOI.replace('requires: ball c r\n', ''))
        self.refused('the four bounds of the parts are four outputs', self.SPLIT.replace('splits al au bl bu', 'splits al au al bu'))
        self.refused('its operand is required to be an interval', self.SPLIT.replace('requires: interval xl xu\n', ''))
        self.refused('not_nan is about a one-limb input, or a multi-limb input required to be canonical',
                     self.EXT.replace('requires: canonical x\n', ''))
        self.refused('its operands of several limbs are required not_nan', self.EXT.replace('requires: not_nan y\n', ''))
        self.refused('encloses_interval zero_factor: the set is the product of two intervals',
                     IntervalClaims.IADD.replace('bounded_exactly', 'zero_factor'))


class R3OfTheKernels(unittest.TestCase):
    """Rule R3 on gen/kernels: which kernels are entry kernels; no guard is pending."""
    # What the public headers of Milestone 1 call (include/kairn/expansion.hpp, ball.hpp and
    # ball_operations.hpp): the cores, through kairn::finite and the kernels that need no fix-up,
    # and the full kernels and constructors (milestone1.md). Three of these comparisons, lt_1_2,
    # lt_2_1 and eq_2_1, also decide the signs of a ball of two limbs (ball.hpp, Milestone 2).
    CORES = {'add_2_2', 'add_2_1', 'sub_2_2', 'sub_2_1', 'sub_1_2', 'mul_2_2', 'mul_2_1', 'neg_2', 'abs_2',
             'add_fast_2_2', 'mul_pow2_2', 'lt_2_2', 'le_2_2', 'eq_2_2', 'lt_2_1', 'le_2_1', 'eq_2_1', 'lt_1_2',
             'le_1_2', 'to_nearest_2', 'to_down_2', 'to_up_2', 'abs_upper_2', 'ball_neg_1', 'ball_neg_2'}
    # The cores of the Ball operations are entry kernels (a center or a radius of the program may
    # reach them), but the headers call them only inside the full Ball kernels: they have no
    # kairn::finite form yet.
    BALL_CORES = {f'ball_{op}_{k}' for op in ('add', 'sub', 'mul', 'scale') for k in (1, 2)}
    # environment.hpp runs two_sum on the self-test's own constants, read through volatile objects:
    # no value of the program reaches it, and milestone1.md names it a building block, not an entry
    # kernel.
    NOT_ENTRY_BUT_CALLED = {'two_sum'}
    # The building blocks that milestone2.md makes public ("Building blocks on T"): the entry forms
    # of the blocks that add their operands, the blocks that only multiply, compare or step theirs
    # (entry kernels as they are: two_prod, rmul, the directed products, next_up, next_down), and the
    # scalings of a ball by a power of two, core and full form ("Scaling a ball by a power of two").
    WAVE_1 = {'two_sum_entry', 'fast_two_sum_entry', 'radd_entry', 'add_down_entry', 'add_up_entry', 'sub_down_entry',
              'sub_up_entry', 'two_prod', 'rmul', 'mul_down_1', 'mul_up_1', 'next_up', 'next_down',
              'ball_mul_pow2_1', 'ball_mul_pow2_2', 'ball_mul_pow2_1_full', 'ball_mul_pow2_2_full'}
    # What the public headers of Milestone 2 call of them: each block of include/kairn/blocks.hpp
    # calls its one kernel (two_sum, fast_two_sum, radd and the four directed sums the entry form;
    # two_prod, rmul, mul_down, mul_up, next_up and next_down the kernel as it is), and ldexp and half
    # of a ball call the full scalings, through detail::scale_pow2 (ball_operations.hpp).
    WAVE_1_CALLED = {'two_sum_entry', 'fast_two_sum_entry', 'radd_entry', 'add_down_entry', 'add_up_entry',
                     'sub_down_entry', 'sub_up_entry', 'two_prod', 'rmul', 'mul_down_1', 'mul_up_1', 'next_up',
                     'next_down', 'ball_mul_pow2_1_full', 'ball_mul_pow2_2_full'}
    # The cores of those scalings are entry kernels, but, like BALL_CORES, the headers call them only
    # inside their full form: they have no kairn::finite form yet.
    POW2_CORES = {'ball_mul_pow2_1', 'ball_mul_pow2_2'}

    # The steps of the folds whose arrays the program supplies (milestone2.md, "Arrays that the
    # program fills"): those of the sums guard the element, those of the dot products only multiply
    # it. The functions on arrays of the public headers, which come later, call them through the folds.
    FOLD_STEPS = {'sum_entry_step_1', 'sum_entry_step_2', 'sum_fast_entry_step_2', 'dot_step_1', 'dot_step_2'}
    # And the steps of the maps that read what the program supplies (sub_1_1 reads stored arrays).
    FOLD_STEPS |= MAP_STEPS - {'sub_1_1'}
    # And the kernels of the accumulator that take what the program adds (acc_merge_k takes two
    # accumulators, acc_radius_k a state).
    FOLD_STEPS |= {'acc_add_1', 'acc_add_2', 'acc_mul_1', 'acc_mul_2'}
    # And the radius kernels of BallVector that take the scalar the program gives (bv_scale_radius_k;
    # bv_add_radius_k takes radii, limbs of objects, and the largest magnitude of a center).
    FOLD_STEPS |= {'bv_scale_radius_1', 'bv_scale_radius_2'}
    # And the step and the radius kernel of the constructor of a BallVector, which take the center and
    # the radius the program gives (bv_center_2 copies the limbs of an Expansion<T, 2>, stored).
    FOLD_STEPS |= {'bv_center_entry_1', 'bv_make_radius'}
    # And the steps and the radius of the scaling of a BallVector by a power of two, which take the power
    # of two the program gives (only multiplied).
    FOLD_STEPS |= {'bv_mul_pow2_step_1', 'bv_mul_pow2_step_2', 'bv_mul_pow2_radius'}

    def test_entry_kernels(self):
        ks = common.kernels()
        # The interval kernels and the functions of a Ball of the enclosure interface
        # (milestone2.md, "Interval kernels", "One enclosure interface"), for the public headers of
        # wave 2, which do not call them yet: their inputs are limbs of objects (stored), or bounds
        # the program gives (interval_make_1 and ball_from_interval_2, which guard them).
        wave_2 = TheKernels.WAVE_2_INTERVALS | TheKernels.WAVE_2_BALLS | TheKernels.WAVE_2_B1
        self.assertEqual({n for n, k in ks.items() if k.entry},
                         self.CORES | self.BALL_CORES | TheKernels.NON_FINITE | self.WAVE_1 | self.FOLD_STEPS | wave_2)

    def test_every_kernel_the_public_headers_call_is_an_entry_kernel(self):
        ks = common.kernels()
        called = set()
        include = os.path.join(common.ROOT, 'include', 'kairn')
        for name in os.listdir(include):
            if name.endswith('.hpp'):
                with open(os.path.join(include, name), encoding='utf-8') as f:
                    text = f.read()
                called |= set(re.findall(r'\bgen::(\w+)\(', text)) & set(ks)
                for macro in re.findall(r'gen::NAME##(_\w+)\(', text):        # gen::NAME##_2_2(...)
                    called |= {n for n in ks if n.endswith(macro) and n[:-len(macro)] in ('lt', 'le', 'eq')}
        # Of wave 1, the headers call every kernel but the two cores of the scalings; of the folds'
        # stage, the maps and the intervals, nothing yet (FOLD_STEPS and wave 2 of test_entry_kernels
        # are entry kernels that no header calls).
        self.assertEqual(self.WAVE_1, self.WAVE_1_CALLED | self.POW2_CORES)
        self.assertEqual(called - self.NOT_ENTRY_BUT_CALLED, self.CORES | TheKernels.NON_FINITE | self.WAVE_1_CALLED)
        self.assertTrue(all(ks[n].entry for n in called - self.NOT_ENTRY_BUT_CALLED))
        self.assertFalse(any(ks[n].entry for n in self.NOT_ENTRY_BUT_CALLED))
        # The cores of the Ball operations and of the scalings by a power of two are reached only
        # through their full forms: never called directly.
        self.assertEqual(called & (self.BALL_CORES | self.POW2_CORES), set())

    def test_no_pending_guard(self):
        # add_2_1 guards its scalar in its first line (milestone1.md), and nothing is left pending.
        ks = common.kernels()
        self.assertEqual(ks['add_2_1'].body[0].op, 'guard')
        self.assertEqual(ks['add_2_1'].body[0].args, (ir.Operand('a'),))
        self.assertEqual({n: k.guard_pending for n, k in ks.items() if k.guard_pending}, {})
        pending, through = rules.r3_report(ks)
        self.assertEqual((pending, through), ({}, {}))

    def test_accepted_because_of_the_guard_and_for_no_other_reason(self):
        # Without the guard of add_2_1, exactly add_2_1 and the kernels that pass it their scalar
        # unguarded are refused, each for that scalar: nothing else, the folds and maps judged too.
        ks = copy.deepcopy(common.kernels())
        self.assertEqual(set(ks.folds), set(common.kernels().folds))
        k = ks['add_2_1']
        guard, call = k.body[0], k.body[1]
        self.assertEqual((guard.op, call.op), ('guard', 'two_sum'))
        k.body = [dataclasses.replace(call, args=(call.args[0], ir.Operand('a')))] + k.body[2:]
        errors = [e for e in rules.check_all(ks) if e.rule == rules.RULE_R3]
        self.assertEqual(sorted((e.kernel, e.value) for e in errors),
                         sorted((n, 'a') for n in ('add_2_1', 'sub_2_1', 'sub_1_2', 'add_2_1_full', 'sub_2_1_full',
                                                   'sub_1_2_full')))
        for e in errors:
            self.assertIn('in two_sum (called for sh)', str(e))
        self.assertEqual([e for e in rules.check_all(ks) if e.rule != rules.RULE_R3], [])

    def test_build_prints_the_pending_guards(self):
        lines = build.summary(common.kernels())
        self.assertIn('R3 GUARD PENDING: none', lines)
        self.assertIn('accepted by R3 only through a pending guard: none', lines)

    def test_build_prints_the_folds(self):
        ks = common.kernels()
        lines = build.summary(ks)
        self.assertEqual(set(ks.folds), {'sum_1', 'sum_1_entry', 'sum_2', 'sum_2_entry', 'sum_fast_2',
                                         'sum_fast_2_entry', 'dot_1', 'dot_2', 'norm_upper_1', 'norm_upper_2',
                                         'conv_1', 'conv_2'} | MAPS |
                         {'bv_add_1', 'bv_add_2', 'bv_sub_1', 'bv_sub_2', 'bv_scale_1', 'bv_scale_2',
                          'bv_make_1', 'bv_make_2', 'bv_neg_1', 'bv_neg_2', 'bv_mul_pow2_1', 'bv_mul_pow2_2'} |
                         {'bv_conv_1', 'bv_conv_2'})
        self.assertIn('folds: %d (%s)' % (len(ks.folds), ', '.join(ks.folds)), lines)
        unverified = [n for n, f in ks.folds.items() if f.status == 'unverified']
        self.assertIn('folds UNVERIFIED: %s' % (', '.join(unverified) or 'none'), lines)


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

    def test_milestone2_vocabulary(self):
        # neighbor, bound, rounded with when, exact_when on error and on encloses (architecture.md,
        # "Claims of Milestone 2"), accepted and refused.
        one = ('kernel:  bad\ninput:   a\ninput:   b\ninput:   x = x0 x1\noutput:  r\nvalue:   {value}\n'
               'requires: normalized x\nstatus:  unverified\ncone_exempt: what the claims say\n')
        body = 'h = add(b, x0)\nk = add(h, x1)\nd = succ(a)\nr = select(w, d, k)\n'
        head = one.replace('input:   x = x0 x1', 'input:   x = x0 x1\ninput:   mask w')

        def errors(extra, value='a'):
            return [e for e in check(head.format(value=value) + extra + '\n' + body) if e.rule == rules.CLAIMS]

        for extra, value in (('ensures: neighbor r up', 'a'), ('ensures: neighbor r down', 'a'),
                             ('ensures: bound r below steps=1', 'a*b'), ('ensures: bound r above steps=0', 'a-b'),
                             ('ensures: rounded r down when=product_large', 'a*b'),
                             ('ensures: encloses r r y y=a,b exact_when=zero_or_abs_gt(a*x[1],eta/(2*u))', 'a'),
                             ('ensures: encloses r r y y=a,b exact_when=zero_or_abs_ge(x[0],eta);zero_or_abs_gt(b,1)', 'a'),
                             ('ensures: error r R c=1 k=1 t=0 exact_when=zero_or_abs_ge(a*b,2^-3*eta)', 'a*b')):
            self.assertEqual(errors(extra, value), [], extra)
        for extra, value, words in (
                ('ensures: neighbor r left', 'a', 'neighbor side'),
                ('ensures: neighbor r up', 'a+b', 'the one-limb operand'),
                ('ensures: neighbor r up', 'x', 'the one-limb operand'),
                ('ensures: bound r over steps=1', 'a*b', 'bound side'),
                ('ensures: rounded r down when=tiny', 'a*b', 'product_large'),
                ('ensures: encloses r r y y=a,b exact_when=zero_or_abs_gt(q,eta)', 'a', 'unknown name q'),
                ('ensures: encloses r r y y=a,b exact_when=zero_or_abs_gt(x[2],eta)', 'a', 'no limb x[2]'),
                ('ensures: encloses r r y y=a,b exact_when=zero_or_abs_gt(w,eta)', 'a', 'unknown name w'),
                ('ensures: encloses r r y y=a,b exact_when=zero_or_abs_gt(a,a)', 'a', 'over u, eta and integers'),
                ('ensures: encloses r r y y=a,b exact_when=zero_or_abs_gt(a,unit(two_sum))', 'a', 'over u, eta'),
                ('ensures: encloses r r y y=a,b exact_when=zero_or_abs_gt(a,-eta)', 'a', 'positive'),
                ('ensures: encloses r r y y=a,b exact_when=zero_or_abs_gt(a,0)', 'a', 'positive'),
                ('ensures: error r R c=1 k=1 t=0 exact_when=zero_or_abs_gt(a/b,eta)', 'a*b', 'only + - *')):
            got = errors(extra, value)
            self.assertTrue(any(words in str(e) for e in got), f'{extra}: {got}')
        for extra in ('ensures: bound r below steps=x', 'ensures: bound r below', 'ensures: neighbor r',
                      'ensures: encloses r r y y=a,b exact_when=zero_or_abs(a,eta)',
                      'ensures: encloses r r y y=a,b exact_when=zero_or_abs_gt(a)',
                      'ensures: error r R c=1 k=1 t=0 exact_when=abs_le(a,1)'):
            with self.assertRaises(ir.DescriptionError, msg=extra):
                check(head.format(value='a') + extra + '\n' + body)

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
    # ball_neg_k needs no fix-up either, and reads its encloses from a ball (architecture.md).
    BALL_NEG = {'ball_neg_1', 'ball_neg_2'}
    # The Ball cores of the second radius design, and add_2_1 with its guard: the kernels whose
    # listing changed after their first proof, and whose theorems are those of the new listing.
    BALL_CORES = {f'ball_{op}_{k}' for op in ('add', 'sub', 'mul', 'scale') for k in (1, 2)}
    REPROVE = BALL_CORES | {'add_2_1'}
    MILESTONE1 = FIRST_WAVE | SECOND_WAVE | NON_FINITE
    # docs/developer/design/milestone2.md, "Building blocks on T" and "Scaling a ball by a power of
    # two" (wave 1 of its order of implementation), unverified until their proofs land: the
    # kernels of the extended domain, with both statements; two_sum_ord, two_sum_entry and
    # fast_two_sum_entry, and the cores of the scalings of a ball, of the finite domain; and the
    # full forms of the scalings, with the IEEE-model statement only.
    WAVE_1_EXTENDED = {'next_up', 'next_down', 'add_down_1', 'add_up_1', 'sub_down_1', 'sub_up_1', 'mul_down_1',
                       'mul_up_1', 'radd_entry', 'add_down_entry', 'add_up_entry', 'sub_down_entry', 'sub_up_entry'}
    WAVE_1_FINITE = {'two_sum_ord', 'two_sum_entry', 'fast_two_sum_entry', 'ball_mul_pow2_1', 'ball_mul_pow2_2'}
    WAVE_1_FULL = {'ball_mul_pow2_1_full', 'ball_mul_pow2_2_full'}
    WAVE_1 = WAVE_1_EXTENDED | WAVE_1_FINITE | WAVE_1_FULL
    # milestone2.md, "Batch kernels" (the folds' stage): the steps of the folds and the exported
    # bounds, of the finite domain; and the two finishes, with the IEEE-model statement only.
    # Proved (StepKernels.v, BoundKernels.v, IeeeFoldFinish.v).
    FOLDS_FINITE = {'dot_step_1', 'dot_step_2', 'sum_entry_step_1', 'sum_entry_step_2', 'sum_fast_entry_step_2',
                    'bound_sum_1', 'bound_sum_2', 'bound_dot_1', 'bound_dot_2'}
    FOLDS_FINISH = {'fold_finish_1', 'fold_finish_2'}
    # The folds of maxima, norm_upper_k (stage B, part 2): the combination and the steps, of the
    # finite domain, and the finishes, with the IEEE-model statement only.
    NORM_FINISH = {'norm_finish_1', 'norm_finish_2'}
    # And the finish of the constructors of a BallVector, of the IEEE model only too.
    NORM_FINISH |= {'bv_make_finish'}
    # And the finish of the product of two BallVectors, of the IEEE model only too.
    NORM_FINISH |= {'bv_conv_finish'}
    NORM = {'norm_combine', 'norm_step_1', 'norm_step_2'} | NORM_FINISH
    # The kernels of the accumulator (milestone2.md, "The accumulator"), of the finite domain.
    ACC = {f'acc_{op}_{k}' for op in ('add', 'mul', 'merge', 'radius') for k in (1, 2)}
    # The radius kernels of BallVector (milestone2.md, "BallVector"), of the finite domain.
    BV = {f'bv_{op}_radius_{k}' for op in ('add', 'scale') for k in (1, 2)}
    # And the kernels of the constructor of a BallVector: its steps, its radius (finite domain; the copy
    # bv_center_2 of the extended domain with a real-model statement, as neg_2) and its finish.
    BV |= {'bv_center_entry_1', 'bv_center_2', 'bv_make_radius', 'bv_make_finish'}
    # And the step of one limb and the radius of the negation of a BallVector (finite domain).
    BV |= {'neg_1', 'bv_neg_radius'}
    # And the steps and the radius of the scaling of a BallVector by a power of two (finite domain).
    BV |= {'bv_mul_pow2_step_1', 'bv_mul_pow2_step_2', 'bv_mul_pow2_radius'}
    # And the radius (finite domain) and the finish of the product of two BallVectors.
    BV |= {'conv_radius', 'bv_conv_finish'}
    # Of the kernels of the BallVectors, those that are still unverified, and of those of the extended
    # domain, those whose IEEE-model statement is. (The kernels of the constructor and of the negation
    # are proved: BvNegMake.v, IeeeBvNegMake.v.)
    BV_UNVERIFIED = {'bv_mul_pow2_step_1', 'bv_mul_pow2_step_2', 'bv_mul_pow2_radius', 'conv_radius',
                     'bv_conv_finish'}
    BV_IEEE_UNVERIFIED = {'bv_conv_finish'}
    FOLDS = FOLDS_FINITE | FOLDS_FINISH | MAP_STEPS | NORM | ACC | BV
    # milestone2.md, "Interval kernels" and "One enclosure interface" (wave 2, first stage),
    # which were unverified until their proofs were about the generated text: the interval kernels of one
    # limb and the sum of two, with the IEEE-model statement only; mul_dir_1, of the extended domain
    # with both statements; the bounds of two limbs, finite cores; the bounds of a ball as numbers
    # of T, the ball from an interval of two T and the narrowing of a ball, the IEEE-model statement
    # only.
    WAVE_2_INTERVALS = {'interval_make_1', 'interval_neg_1', 'interval_add_1', 'interval_sub_1', 'interval_mul_1',
                        'interval_add_2'}
    WAVE_2_CORES = {'add_ball_2_2', 'mul_ball_2_2', 'add_down_2_2', 'add_up_2_2', 'sub_down_2_2', 'sub_up_2_2',
                    'mul_dir_2_2'}
    WAVE_2_BALLS = {'ball_lower_as_1', 'ball_upper_as_1', 'ball_lower_as_2', 'ball_upper_as_2',
                    'ball_from_interval_2', 'ball_narrow_2_1'}
    WAVE_2 = WAVE_2_INTERVALS | WAVE_2_CORES | WAVE_2_BALLS | {'mul_dir_1'}
    # Stage B1 of wave 2, unverified, the IEEE-model statement only: the interval kernels of two limbs
    # (negation, difference, constructor, product) and the set operations, conversions and split of
    # the enclosure interface, entry kernels; and mul_ext_2_2, the building block of the product.
    WAVE_2_B1 = {'interval_neg_2', 'interval_sub_2', 'interval_make_2', 'interval_mul_2', 'interval_hull_1',
                 'interval_intersection_1', 'interval_hull_2', 'interval_intersection_2', 'interval_mid_rad_1',
                 'interval_to_ball_1', 'ball_to_interval_1', 'interval_split_1'}
    WAVE_2 |= WAVE_2_B1 | {'mul_ext_2_2'}
    # Of these, the kernels whose theorems are about the generated text and pass the audit: all
    # of the first stage. The interval kernels of one limb (IeeeInterval1.v), mul_dir_1 in both models
    # (DirectedProd.v, IeeeDirectedProd.v), the bounds of two limbs (Directed2.v), the sum of two
    # intervals of two limbs (IeeeInterval2.v) and the conversions of a ball (IeeeBallConvert.v).
    # And of stage B1, all of them: the exact ones (IeeeIntervalExact.v), the difference of two
    # limbs (IeeeIntervalSub2.v), the conversions between an interval and a ball of one limb, with
    # the midpoint and the split (IeeeIntervalConvert.v), and mul_ext_2_2 with the product of two
    # limbs (IeeeIntervalMul2.v).
    WAVE_2_B1_PROVED = WAVE_2_B1 | {'mul_ext_2_2'}
    WAVE_2_PROVED = (WAVE_2 - WAVE_2_B1 - {'mul_ext_2_2'}) | WAVE_2_B1_PROVED

    def test_kernel_names_are_those_of_the_listings(self):
        ks = common.kernels()
        self.assertEqual(set(ks), self.MILESTONE1 | self.WAVE_1 | self.FOLDS | self.WAVE_2)
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
        # Proved means: the audit passes for that kernel (make -C proofs). Every kernel is: those of
        # the real model, the Ball cores of the second radius design and add_2_1 with its guard
        # among them (Ball2.v, Add21.v), by their real-model theorems; the full kernels and the
        # constructors, which have no real-model statement, by their IEEE-model theorems.
        # Of wave 1 of Milestone 2, every kernel is proved too, the two full scalings of a ball by
        # their IEEE-model theorems (IeeeBallPow2.v), and so is every kernel of the folds' stage,
        # every step of the maps (MapSteps.v), those of the folds of maxima (FoldNorm.v; the two
        # finishes by their IEEE-model theorems, IeeeFoldNorm.v) and those of the accumulator, in
        # both models (AccKernels.v, IeeeAccKernels.v).
        # The two constructors of a ball are proved for the rule of 2026-11-20, that a NaN radius
        # gives the whole line (IeeeMake.v).
        # The kernels of the constructor, the negation, the scaling by a power of two and the product
        # of BallVectors are unverified.
        self.assertEqual({name for name, k in ks.items() if k.status == 'proved'},
                         self.MILESTONE1 | self.WAVE_1 | (self.FOLDS - self.BV_UNVERIFIED) | self.WAVE_2_PROVED)
        # No other kernel is unverified: the kernels of wave 2 were, in both models, until their proofs
        # were about the generated text, and so were those of the accumulator and the radius
        # kernels of BallVector (BvRadius.v).
        self.assertEqual({name for name, k in ks.items() if k.status == 'unverified'},
                         (self.WAVE_2 - self.WAVE_2_PROVED) | self.BV_UNVERIFIED)
        self.assertEqual({name: k.theorem for name, k in ks.items() if name in self.BALL_CORES},
                         {name: ('proofs/theories/Ball2.v', f'{name}_correct') for name in self.BALL_CORES})
        self.assertEqual(ks['add_2_1'].theorem, ('proofs/theories/Add21.v', 'add_2_1_correct'))
        wave_2_ieee_only = self.WAVE_2_INTERVALS | self.WAVE_2_BALLS | self.WAVE_2_B1 | {'mul_ext_2_2'}
        self.assertEqual({name for name, k in ks.items() if not k.real_model},
                         self.NON_FINITE | self.WAVE_1_FULL | self.FOLDS_FINISH | self.NORM_FINISH | wave_2_ieee_only)
        self.assertEqual({name for name, k in ks.items() if k.extended},
                         self.NON_FINITE | self.NO_FIX_UP | self.BALL_NEG | self.WAVE_1_EXTENDED | self.WAVE_1_FULL |
                         self.FOLDS_FINISH | self.NORM_FINISH | wave_2_ieee_only | {'mul_dir_1'} | {'bv_center_2'})
        # (bv_center_2, the copy of the constructor of a BallVector, has both statements, as neg_2.)
        self.assertEqual({name: k.ieee_status for name, k in ks.items() if k.extended},
                         dict(dict.fromkeys(self.NON_FINITE | self.NO_FIX_UP | self.BALL_NEG
                                            | self.WAVE_1_EXTENDED | self.WAVE_1_FULL | self.FOLDS_FINISH
                                            | ((self.NORM_FINISH | {'bv_center_2'}) - self.BV_IEEE_UNVERIFIED)
                                            | (self.WAVE_2_PROVED - self.WAVE_2_CORES), 'proved'),
                              **dict.fromkeys(((wave_2_ieee_only | {'mul_dir_1'}) - self.WAVE_2_PROVED)
                                              | self.BV_IEEE_UNVERIFIED,
                                              'unverified')))
        # Every kernel of the extended domain that is proved names its IEEE-model theorem, and no
        # other kernel does.
        self.assertEqual({name for name, k in ks.items() if k.ieee_theorem},
                         self.NON_FINITE | self.NO_FIX_UP | self.BALL_NEG | self.WAVE_1_EXTENDED
                         | self.WAVE_1_FULL | self.FOLDS_FINISH
                         | ((self.NORM_FINISH | {'bv_center_2'}) - self.BV_IEEE_UNVERIFIED)
                         | (self.WAVE_2_PROVED - self.WAVE_2_CORES))
        # The minimum precision of a full kernel is that of its core, and so is a full Ball kernel's
        # with a 2-limb center; with a one-limb center it is 2, from which the constants G and H
        # of the radius are below the overflow threshold (IeeeExtStatementsDraft.v). A
        # constructor's is 1.
        for name in self.FULL | self.FULL_BALL | self.WAVE_1_FULL:
            core = name[:-len('_full')]
            want = 2 if name.endswith('_1_full') and name.startswith('ball_') else ks[core].min_precision
            self.assertEqual(ks[name].min_precision, want, name)
        self.assertEqual({ks[n].min_precision for n in self.CONSTRUCTORS}, {1})
        self.assertEqual(ks['two_prod'].ce_variant, 'two_prod_dekker')
        # The smallest precision from which each real-model statement holds.
        self.assertEqual({name: k.min_precision for name, k in ks.items() if k.real_model}, {
            'two_sum': 2, 'fast_two_sum': 2, 'two_prod': 2, 'split': 4, 'two_prod_dekker': 4,
            'add_2_2': 3, 'add_2_1': 3, 'mul_2_2': 4, 'mul_2_1': 2, 'add_fast_2_2': 2,
            'neg_2': 1, 'abs_2': 1, 'sub_2_2': 3, 'sub_2_1': 3, 'sub_1_2': 3,
            'lt_2_2': 1, 'le_2_2': 1, 'eq_2_2': 1, 'lt_2_1': 1, 'le_2_1': 1, 'eq_2_1': 1, 'lt_1_2': 1,
            'le_1_2': 1, 'to_nearest_2': 1, 'to_down_2': 1, 'to_up_2': 1, 'abs_upper_2': 1,
            'radd': 2, 'rmul': 2, 'mul_pow2_2': 2, 'add_1_1': 1, 'mul_1_1': 1,
            'ball_add_1': 1, 'ball_sub_1': 1, 'ball_neg_1': 1, 'ball_mul_1': 1, 'ball_scale_1': 1,
            'ball_add_2': 3, 'ball_sub_2': 3, 'ball_neg_2': 1, 'ball_mul_2': 4, 'ball_scale_2': 2,
            # milestone2.md, the table "Every new kernel".
            'next_up': 1, 'next_down': 1, 'two_sum_ord': 2, 'add_down_1': 2, 'add_up_1': 2, 'sub_down_1': 2,
            'sub_up_1': 2, 'mul_down_1': 2, 'mul_up_1': 2, 'two_sum_entry': 2, 'fast_two_sum_entry': 2,
            'radd_entry': 2, 'add_down_entry': 2, 'add_up_entry': 2, 'sub_down_entry': 2, 'sub_up_entry': 2,
            'ball_mul_pow2_1': 2, 'ball_mul_pow2_2': 2,
            # the folds' stage: that of the kernels of one limb and of add_2_2, add_fast_2_2, mul_2_2
            'dot_step_1': 1, 'dot_step_2': 4, 'sum_entry_step_1': 1, 'sum_entry_step_2': 3,
            'sum_fast_entry_step_2': 2, 'bound_sum_1': 1, 'bound_sum_2': 3, 'bound_dot_1': 1, 'bound_dot_2': 4,
            # the steps of the maps: that of the kernels they call (axpy_step_2_1: mul_2_1 and add_2_2)
            'sub_1_1': 1, 'add_entry_step_1': 1, 'sub_entry_step_1': 1, 'add_entry_step_2': 3,
            'sub_entry_step_2': 3, 'scale_step_1': 1, 'scale_step_2': 2, 'mul_pow2_step_1': 1,
            'mul_pow2_step_2': 2, 'axpy_step_1': 1, 'axpy_entry_step_1': 1, 'axpy_step_2': 4,
            'axpy_entry_step_2': 4, 'axpy_step_2_1': 3, 'axpy_entry_step_2_1': 3,
            # the folds of maxima: comparisons and selects, from one bit on
            'norm_combine': 1, 'norm_step_1': 1, 'norm_step_2': 1,
            # the accumulator: that of add_1_1, add_2_2 and dot_step_2; the radius's constants are
            # numbers of the toy formats from two bits on ((1+u)^8 above the top of fp:1:-3:3)
            'acc_add_1': 1, 'acc_mul_1': 1, 'acc_merge_1': 1, 'acc_add_2': 3, 'acc_mul_2': 4, 'acc_merge_2': 3,
            'acc_radius_1': 2, 'acc_radius_2': 2,
            # The radius kernels of BallVector, from the precision of the Ball kernel whose radius
            # lines they are.
            'bv_add_radius_1': 1, 'bv_add_radius_2': 3, 'bv_scale_radius_1': 1, 'bv_scale_radius_2': 2,
            # and the kernels of its constructor that have a real-model statement, from 1.
            'bv_center_entry_1': 1, 'bv_center_2': 1, 'bv_make_radius': 1,
            # and of the negation.
            'neg_1': 1, 'bv_neg_radius': 1,
            # and of the scaling by a power of two: the step of one limb from 1 (mul_pow2_step_1's), the
            # others from the precision of ball_mul_pow2_k, 2.
            'bv_mul_pow2_step_1': 1, 'bv_mul_pow2_step_2': 2, 'bv_mul_pow2_radius': 2,
            # and the radius of the product of two BallVectors, from 2 (below, its constant hm is above
            # the largest number of formats of few exponents).
            'conv_radius': 2,
            # Wave 2 (as the proofs found them): mul_dir_1 from 2, the sums of two limbs from 3, the
            # products from 4.
            'mul_dir_1': 2, 'add_ball_2_2': 3, 'add_down_2_2': 3, 'add_up_2_2': 3, 'sub_down_2_2': 3,
            'sub_up_2_2': 3, 'mul_ball_2_2': 4, 'mul_dir_2_2': 4})
        # And of the interval kernels: none for the constructor, the negation and the product of one
        # limb (their theorems are for every precision), 2 for the sum and the difference, 3 for the
        # sum of two limbs; 2 for the bounds of a ball, the ball from an interval and the narrowing.
        self.assertEqual({name: ks[name].min_precision for name in self.WAVE_2_INTERVALS | self.WAVE_2_BALLS}, {
            'interval_make_1': 1, 'interval_neg_1': 1, 'interval_mul_1': 1, 'interval_add_1': 2,
            'interval_sub_1': 2, 'interval_add_2': 3, 'ball_lower_as_1': 2, 'ball_upper_as_1': 2,
            'ball_lower_as_2': 2, 'ball_upper_as_2': 2, 'ball_from_interval_2': 2, 'ball_narrow_2_1': 2})
        # Stage B1: none for the negation and the constructor of two limbs, the hulls and the
        # intersections (comparisons and selects); that of the directed sums for the difference of two
        # limbs, 3, and of mul_dir_2_2 for the product, 4; 2 for the midpoint and radius, which
        # rounds a difference up, and for the conversions and the split.
        self.assertEqual({name: ks[name].min_precision for name in self.WAVE_2_B1 | {'mul_ext_2_2'}}, {
            'interval_neg_2': 1, 'interval_make_2': 1, 'interval_sub_2': 3, 'mul_ext_2_2': 4, 'interval_mul_2': 4,
            'interval_hull_1': 1, 'interval_intersection_1': 1, 'interval_hull_2': 1, 'interval_intersection_2': 1,
            'interval_mid_rad_1': 2, 'interval_to_ball_1': 2, 'ball_to_interval_1': 2, 'interval_split_1': 2})

    def test_milestone2_bodies_are_those_of_milestone2_md(self):
        """The listings of wave 1, line for line as the page writes them ("Building blocks on T",
        "Scaling a ball by a power of two"), with const P = up(eta/(2*u^2)) and const N = up(eta/(2*u))
        spelled out, and one operation per line."""
        ks = common.kernels()

        def body(name):
            return [f'{", ".join(st.dsts)} = {st.op}({", ".join(map(str, st.args))})' for st in ks[name].body]

        self.assertEqual(body('next_up'), ['r = succ(a)'])
        self.assertEqual(body('next_down'), ['r = pred(a)'])
        self.assertEqual(body('two_sum_ord'), ['aa = abs(a)', 'ab = abs(b)', 'm = lt(aa, ab)', 'h = select(m, b, a)',
                                               'l = select(m, a, b)', 's, e = fast_two_sum(h, l)'])
        self.assertEqual(body('add_down_1'), ['s, e = two_sum_ord(a, b)', 'n = lt(e, 0)', 'p = pred(s)',
                                              'r = select(n, p, s)'])
        self.assertEqual(body('add_up_1'), ['s, e = two_sum_ord(a, b)', 'n = lt(0, e)', 'q = succ(s)',
                                            'r = select(n, q, s)'])
        self.assertEqual(body('sub_down_1'), ['nb = neg(b)', 'r = add_down_1(a, nb)'])
        self.assertEqual(body('sub_up_1'), ['nb = neg(b)', 'r = add_up_1(a, nb)'])
        p = 'const up(eta/(2*u^2))'
        common_lines = ['p, e = two_prod(a, b)', 'ap = abs(p)', f'bd = lt(ap, {p})', 'ez = eq(e, 0)', 'un = and(bd, ez)']
        self.assertEqual(body('mul_down_1'), common_lines + [
            'n = lt(e, 0)', 'sd = or(n, un)', 'pp = pred(p)', 'd = select(sd, pp, p)', 'za = eq(a, 0)',
            'zb = eq(b, 0)', 'zz = or(za, zb)', 'r = select(zz, p, d)'])
        self.assertEqual(body('mul_up_1'), common_lines + [
            'n = lt(0, e)', 'su = or(n, un)', 'sp = succ(p)', 'v = select(su, sp, p)', 'za = eq(a, 0)',
            'zb = eq(b, 0)', 'zz = or(za, zb)', 'r = select(zz, p, v)'])
        for name, core in (('two_sum_entry', 'two_sum'), ('fast_two_sum_entry', 'fast_two_sum'), ('radd_entry', 'radd'),
                           ('add_down_entry', 'add_down_1'), ('add_up_entry', 'add_up_1'),
                           ('sub_down_entry', 'sub_down_1'), ('sub_up_entry', 'sub_up_1')):
            outs = ', '.join(ks[core].output_limbs)
            self.assertEqual(body(name), ['ga = guard(a)', 'gb = guard(b)', f'{outs} = {core}(ga, gb)'], name)
        n = 'const up(eta/(2*u))'
        radius = ['su = succ(rr)', 'rw = succ(su)', 'rz = select(ex, rr, rw)']
        self.assertEqual(body('ball_mul_pow2_2'), [
            'h = prod(cx0, c)', 'l = prod(cx1, c)', 'cz0, cz1 = fast_two_sum(h, l)', 'rr = prod(rx, c)',
            'ze = eq(cx1, 0)', 'm = select(ze, h, l)', 'am = abs(m)', f'bc = lt({n}, am)', 'zc = eq(cx0, 0)',
            'ec = or(bc, zc)', f'br = lt({n}, rr)', 'zr = eq(rx, 0)', 'er = or(br, zr)', 'ex = and(ec, er)'] + radius)
        # The same with one product for the center.
        self.assertEqual(body('ball_mul_pow2_1'), [
            'cz = prod(cx, c)', 'rr = prod(rx, c)', 'am = abs(cz)', f'bc = lt({n}, am)', 'zc = eq(cx, 0)',
            'ec = or(bc, zc)', f'br = lt({n}, rr)', 'zr = eq(rx, 0)', 'er = or(br, zr)', 'ex = and(ec, er)'] + radius)
        # The full forms: the fix-up of ball_scale_k_full after the core.
        for k in (1, 2):
            self.assertEqual(body(f'ball_mul_pow2_{k}_full')[1:], body(f'ball_scale_{k}_full')[1:], k)

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
        # The Ball cores of the second radius design (milestone1.md, "The radius, second design").
        # The last constant, H, ends with eta/(2*u), the smallest normal number.
        self.assertEqual(body('ball_add_2'), [
            'cz0, cz1 = add_2_2(cx0, cx1, cy0, cy1)', 'az = abs(cz0)', 's = add(rx, ry)',
            't = fma(az, const up(unit(add_2_2)/(1-unit(add_2_2))*(1+u)), s)',
            'rz = fma(t, const up((1+u)^3), const up((1+u)*((1+u)^2*eta+eta/2)+eta/(2*u)))'])
        self.assertEqual(body('ball_add_1'), [
            'cz = add(cx, cy)', 'az = abs(cz)', 's = add(rx, ry)',
            't = fma(az, const up(unit(add_1_1)/(1-unit(add_1_1))), s)',
            'rz = fma(t, const up((1+u)^3), const up((1+u)*((1+u)^2*eta+eta/2)+eta/(2*u)))'])
        self.assertEqual(body('ball_mul_1'), [
            'cz = prod(cx, cy)', 'ax = abs(cx)', 'ay = abs(cy)', 'az = abs(cz)', 'p = prod(rx, ry)',
            'q = fma(ay, rx, p)', 'w = fma(ax, ry, q)', 't = fma(az, const up(unit(mul_1_1)/(1-unit(mul_1_1))), w)',
            'rz = fma(t, const up((1+u)^5), const up((1+u)*(2*(1+u)^4*eta+tiny(mul_1_1)/(1-unit(mul_1_1))+eta/2)+eta/(2*u)))'])
        self.assertEqual(body('ball_mul_2'), [
            'cz0, cz1 = mul_2_2(cx0, cx1, cy0, cy1)', 'ax = abs(cx0)', 'ay = abs(cy0)', 'az = abs(cz0)',
            'p = prod(rx, ry)', 'q = fma(ay, rx, p)', 'w = fma(ax, ry, q)',
            't = fma(az, const up(unit(mul_2_2)/(1-unit(mul_2_2))), w)',
            'rz = fma(t, const up((1+u)^6), const up((1+u)*(2*(1+u)^5*eta+tiny(mul_2_2)/(1-unit(mul_2_2))+eta/2)+eta/(2*u)))'])
        self.assertEqual(body('ball_scale_1'), [
            'cz = prod(cx, a)', 'aa = abs(a)', 'az = abs(cz)', 'p = prod(aa, rx)',
            't = fma(az, const up(unit(mul_1_1)/(1-unit(mul_1_1))), p)',
            'rz = fma(t, const up((1+u)^3), const up((1+u)*((1+u)^2*eta+tiny(mul_1_1)/(1-unit(mul_1_1))+eta/2)+eta/(2*u)))'])
        self.assertEqual(body('ball_scale_2'), [
            'cz0, cz1 = mul_2_1(cx0, cx1, a)', 'aa = abs(a)', 'az = abs(cz0)', 'p = prod(aa, rx)',
            't = fma(az, const up(unit(mul_2_1)/(1-unit(mul_2_1))*(1+u)), p)',
            'rz = fma(t, const up((1+u)^3), const up((1+u)*((1+u)^2*eta+tiny(mul_2_1)/(1-unit(mul_2_1))+eta/2)+eta/(2*u)))'])
        self.assertEqual(body('ball_sub_1'), ['n = neg(cy)', 'cz, rz = ball_add_1(cx, rx, n, ry)'])
        self.assertEqual(body('ball_sub_2'), ['n0, n1 = neg_2(cy0, cy1)',
                                              'cz0, cz1, rz = ball_add_2(cx0, cx1, rx, n0, n1, ry)'])
        # Each takes its constants from the proved bound of the kernel of its center; radd and rmul
        # are no longer called, and stay kernels.
        for name, center in (('ball_add_1', 'add_1_1'), ('ball_add_2', 'add_2_2'), ('ball_mul_1', 'mul_1_1'),
                             ('ball_mul_2', 'mul_2_2'), ('ball_scale_1', 'mul_1_1'), ('ball_scale_2', 'mul_2_1')):
            called = {k.split('(')[1].rstrip(')') for c in ir.constants(ks[name]) if ir.up(c)
                      for k in re.findall(r'(?:unit|tiny)\([a-z0-9_]+\)', c)}
            self.assertEqual(called, {center}, name)
            self.assertEqual(ks[center].status, 'proved')
        # (Of Milestone 1's Ball kernels: ball_narrow_2_1, of Milestone 2, widens a radius by radd.)
        self.assertTrue(all(st.op not in ('radd', 'rmul', 'abs_upper_2') for k in ks.values() for st in k.body
                            if k.name.startswith('ball_') and k.name in self.MILESTONE1))
        self.assertIn('radd', ks)
        self.assertIn('rmul', ks)

    def test_flops(self):
        # The operation counts of docs/developer/design/phase0/operations.md, and the guard of add_2_1
        # (rule R3), which is one more addition.
        ks = common.kernels()
        self.assertEqual({n: ir.flops(ks[n], ks) for n in ('add_2_2', 'add_fast_2_2', 'add_2_1', 'mul_2_2', 'mul_2_1')},
                         {'add_2_2': 20, 'add_fast_2_2': 11, 'add_2_1': 11, 'mul_2_2': 9, 'mul_2_1': 6})


if __name__ == '__main__':
    unittest.main()
