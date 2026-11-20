"""gen/objcode.json (kairn_gen/objcode.py): what the object-code check expects of each kernel's
compiled code (tests/objcode/), counted from the same flattened IR the printers print."""
import json
import os
import unittest

import common
from kairn_gen import cpp, ir, objcode

# A kernel that computes some things twice in other words: the same product with its factors
# swapped, an fms and the FMA of the negated addend, an fnma and the FMA of a negated factor, two
# constants that are different numbers in binary64 and the same in binary32 (1 + 2^-40 and
# 1 + 2^-30 both round up to 1 + 2^-23), and the product with infinity of two equal values.
TOY = '''
kernel:   toy_numbering
input:    a
input:    b
input:    c
output:   r = r0 r1 r2 r3 r4
value:    a*b+c
ensures:  error r R c=1 k=1 t=0
status:   unverified

p  = prod(a, b)
q  = prod(b, a)
n  = neg(c)
f  = fms(a, b, c)
g  = fma(a, b, n)
m  = neg(a)
h  = fnma(a, b, c)
k  = fma(m, b, c)
d1 = prod(const up(1+2^-40), a)
d2 = prod(const up(1+2^-30), a)
i  = times_inf(p)
j  = times_inf(q)
e  = eq(i, j)
s1 = add(p, q)
s2 = add(f, g)
s3 = add(h, k)
r0 = add(s1, s2)
r1 = add(s3, d1)
r2 = add(d2, 0)
r3 = select(e, i, j)
r4 = copy(c)
'''


def counts(name, form, ctype, kernels=None):
    ks = kernels or common.kernels()
    return objcode.kernel_counts(ks[name], ks)[form][ctype]


class Counts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()

    def test_file_matches_the_counts(self):
        doc = json.loads(objcode.objcode(self.ks))
        self.assertEqual(doc['forms'], list(objcode.FORMS))
        self.assertEqual(doc['counts'], list(objcode.COUNTS))
        self.assertEqual(list(doc['kernels']), list(self.ks))
        for name, k in self.ks.items():
            c = objcode.kernel_counts(k, self.ks)
            for form in objcode.FORMS:
                for t in objcode.LIMB_TYPES:
                    self.assertEqual(doc['kernels'][name][form][t], [c[form][t][x] for x in objcode.COUNTS])

    def test_every_form_has_every_operation_once(self):
        for name, k in self.ks.items():
            prims = ir.prims(k, self.ks)
            fused = sum(1 for p in prims if p.op in ir.FUSED)
            muls = sum(1 for p in prims if p.op == 'times_inf')
            for form in objcode.FORMS:
                for t in objcode.LIMB_TYPES:
                    c = counts(name, form, t, self.ks)
                    with self.subTest(kernel=name, form=form, type=t):
                        self.assertEqual((c['fma'], c['mul']), (fused, muls))
                        self.assertLessEqual(c['fma_distinct'], c['fma'])
                        self.assertLessEqual(c['mul_distinct'], c['mul'])
                        self.assertEqual(c['muladd'], 0)

    def test_known_kernels(self):
        # (form, fma, fma_distinct, mul, consteval_mul), the same for double and float
        known = {
            'mul_2_2': [('scalar', 5, 5, 0, 0), ('scalar_call', 5, 5, 0, 0), ('packed', 5, 5, 0, 0)],
            'add_2_2': [('scalar', 0, 0, 0, 0), ('packed', 0, 0, 0, 0)],
            # The fix-up recomputes the core's leading product, prod(x0, y0): once more in the
            # inline form and in packed code, in the fix-up function's own in the other form.
            'mul_2_2_full': [('scalar', 6, 5, 1, 0), ('scalar_call', 6, 6, 1, 0), ('packed', 6, 5, 1, 0)],
            'mul_2_1_full': [('scalar', 4, 3, 1, 0), ('scalar_call', 4, 4, 1, 0), ('packed', 4, 3, 1, 0)],
            # constexpr by the rule of the product: each of its three prods has a plain product in
            # the arm that only constant evaluation takes, in the scalar forms.
            'mul_pow2_2_full': [('scalar', 3, 2, 1, 3), ('scalar_call', 3, 3, 1, 3), ('packed', 3, 2, 1, 0)],
            'add_2_2_full': [('scalar', 0, 0, 1, 0), ('scalar_call', 0, 0, 1, 0), ('packed', 0, 0, 1, 0)],
            # Dekker's product in the branch of constant evaluation: two splits by a plain product
            # with the splitter, and five products.
            'two_prod': [('scalar', 2, 2, 0, 7), ('scalar_call', 2, 2, 0, 7), ('packed', 2, 2, 0, 0)],
            # The variant itself is constexpr by the rule of the product: its seven prods.
            'two_prod_dekker': [('scalar', 7, 7, 0, 7), ('packed', 7, 7, 0, 0)],
            'ball_mul_2_full': [('scalar', 10, 10, 0, 0), ('scalar_call', 10, 10, 0, 0)],
            'rmul': [('scalar', 1, 1, 0, 1), ('packed', 1, 1, 0, 0)],
            'mul_pow2_2': [('scalar', 2, 2, 0, 2), ('packed', 2, 2, 0, 0)],
            'ball_mul_pow2_1': [('scalar', 2, 2, 0, 2), ('packed', 2, 2, 0, 0)],
            'ball_mul_pow2_2_full': [('scalar', 3, 3, 0, 3), ('scalar_call', 3, 3, 0, 3), ('packed', 3, 3, 0, 0)],
            # The directed products are not constexpr: two_prod's fms, and no plain product.
            'mul_down_1': [('scalar', 2, 2, 0, 0), ('packed', 2, 2, 0, 0)],
            'next_up': [('scalar', 0, 0, 0, 0), ('packed', 0, 0, 0, 0)],
        }
        for name, rows in known.items():
            for form, fma, distinct, mul, ce in rows:
                for t in objcode.LIMB_TYPES:
                    c = counts(name, form, t, self.ks)
                    self.assertEqual((c['fma'], c['fma_distinct'], c['mul'], c['consteval_mul']),
                                     (fma, distinct, mul, ce), (name, form, t))

    def test_where_the_counts_differ(self):
        """The generator says where the forms or the limb types differ: today the three kernels
        whose fix-up recomputes the core's product, two_prod's branch of constant evaluation, and
        the kernels constexpr by the rule of the product, whose scalar forms have a plain product
        for constant evaluation per prod and whose packed form has none."""
        differ = set()
        for name in self.ks:
            rows = {(f, t): tuple(counts(name, f, t, self.ks).values())
                    for f in objcode.FORMS for t in objcode.LIMB_TYPES}
            if len(set(rows.values())) > 1:
                differ.add(name)
        product_rule = {n for n, k in self.ks.items() if cpp.product_rule(k, self.ks)}
        self.assertEqual(product_rule, {'rmul', 'mul_1_1', 'split', 'two_prod_dekker', 'mul_pow2_2', 'mul_pow2_2_full',
                                        'ball_mul_pow2_1', 'ball_mul_pow2_2', 'ball_mul_pow2_1_full',
                                        'ball_mul_pow2_2_full', 'bound_sum_1', 'bound_sum_2', 'bound_dot_1',
                                        'bound_dot_2', 'scale_step_1', 'mul_pow2_step_1', 'mul_pow2_step_2',
                                        'axpy_step_1', 'axpy_entry_step_1'})
        self.assertEqual(differ, {'mul_2_1_full', 'mul_2_2_full', 'mul_pow2_2_full', 'two_prod'} | product_rule)
        for name in product_rule:
            prods = sum(1 for p in ir.prims(self.ks[name], self.ks) if p.op == 'prod')
            for t in objcode.LIMB_TYPES:
                self.assertEqual([counts(name, f, t, self.ks)['consteval_mul'] for f in objcode.FORMS],
                                 [prods, prods, 0], name)

    def test_numbering(self):
        k = ir.parse_kernel(TOY, 'toy_numbering.kernel')
        ks = {k.name: k}
        d = objcode.kernel_counts(k, ks)['packed']
        self.assertEqual(cpp.literal('up(1+2^-40)', ks, 'float'), cpp.literal('up(1+2^-30)', ks, 'float'))
        self.assertNotEqual(cpp.literal('up(1+2^-40)', ks, 'double'), cpp.literal('up(1+2^-30)', ks, 'double'))
        # p and q, f and g, h and k are one each; d1 and d2 two in double and one in float.
        self.assertEqual((d['double']['fma'], d['double']['fma_distinct']), (8, 5))
        self.assertEqual((d['float']['fma'], d['float']['fma_distinct']), (8, 4))
        self.assertEqual((d['double']['mul'], d['double']['mul_distinct']), (2, 1))

    def test_the_fixup_function_is_numbered_apart(self):
        b = cpp.branch(self.ks['mul_2_2_full'], self.ks)
        self.assertIn('x0', cpp.fixup_inputs(self.ks['mul_2_2_full'], b))
        after = [it for it in b.after if isinstance(it, ir.Prim)]
        self.assertEqual([p.op for p in after if p.op in ir.FUSED], ['prod'])


class File(unittest.TestCase):
    def test_committed(self):
        with open(os.path.join(common.ROOT, 'gen', 'objcode.json'), encoding='utf-8') as f:
            self.assertEqual(f.read(), objcode.objcode(common.kernels()))


if __name__ == '__main__':
    unittest.main()
