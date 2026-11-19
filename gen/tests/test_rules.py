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
        self.refused(HEAD.replace('ensures: error r R c=0 k=2 t=0', 'ensures: normalized r'), 'no error entry')


class TheKernels(unittest.TestCase):
    def test_first_wave_and_test_kernels_are_accepted(self):
        for d in (None, common.TEST_KERNELS):
            self.assertTrue(common.kernels(d))

    def test_first_wave_names_are_those_of_architecture_md(self):
        ks = common.kernels()
        self.assertEqual(set(ks), {'two_sum', 'fast_two_sum', 'two_prod', 'split', 'two_prod_dekker',
                                   'add_2_2', 'add_2_1', 'mul_2_2', 'mul_2_1', 'add_fast_2_2',
                                   'add_fast_2_2_ts'})
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
        self.assertEqual(body['add_fast_2_2'][-1], (('z0', 'z1'), 'fast_two_sum', ('sh', 'w')))
        self.assertEqual(body['add_fast_2_2_ts'][-1], (('z0', 'z1'), 'two_sum', ('sh', 'w')))
        self.assertEqual(body['add_fast_2_2'][:-1], body['add_fast_2_2_ts'][:-1])
        self.assertTrue(all(k.status == 'unverified' for k in ks.values()))
        self.assertEqual(ks['two_prod'].ce_variant, 'two_prod_dekker')

    def test_flops(self):
        # The operation counts of docs/developer/design/phase0/operations.md.
        ks = common.kernels()
        self.assertEqual({n: ir.flops(ks[n], ks) for n in ('add_2_2', 'add_fast_2_2', 'add_2_1', 'mul_2_2', 'mul_2_1')},
                         {'add_2_2': 20, 'add_fast_2_2': 11, 'add_2_1': 10, 'mul_2_2': 9, 'mul_2_1': 6})


if __name__ == '__main__':
    unittest.main()
