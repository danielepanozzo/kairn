"""The expression parser and gen/claims.json."""
import json
import os
import unittest
from fractions import Fraction

import common
from kairn_gen import claims, expr


class Parser(unittest.TestCase):
    def value(self, text, **env):
        return expr.evaluate(expr.parse(text), {k: Fraction(v) for k, v in env.items()})

    def test_arithmetic(self):
        self.assertEqual(self.value('1+2*3'), 7)
        self.assertEqual(self.value('(1+2)*3'), 9)
        self.assertEqual(self.value('1-2-3'), -4)
        self.assertEqual(self.value('8/2/2'), 2)
        self.assertEqual(self.value('-3/-(2)'), Fraction(3, 2))
        self.assertEqual(self.value(' 7 / 2 '), Fraction(7, 2))
        u = Fraction(1, 2 ** 53)
        self.assertEqual(self.value('3/(1-4*u)', u=u), 3 / (1 - 4 * u))

    def test_refusals(self):
        for text in ('', '1+', '(1', '1)', '2**3', '1e5', '0x10', '1.5', 'u u', "__import__('os')",
                     'eval(1)', '1;2', '2^3', '[1]'):
            with self.assertRaises(expr.ExprError, msg=text):
                self.value(text, u=1)
        with self.assertRaises(expr.ExprError):
            self.value('1/(1-1)')
        with self.assertRaises(expr.ExprError):
            self.value('v')

    def test_names(self):
        self.assertEqual(expr.names(expr.parse('x*y+x')), {'x', 'y'})
        self.assertEqual(expr.names(expr.parse('3/(1-4*u)')), {'u'})


class Claims(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ks = common.kernels()
        cls.doc = json.loads(claims.claims(ks))
        cls.by = {k['name']: k for k in cls.doc['kernels']}

    def test_committed_claims_are_these(self):
        with open(os.path.join(common.GEN, 'claims.json'), encoding='utf-8') as f:
            self.assertEqual(json.load(f), self.doc)

    def test_schema(self):
        self.assertEqual(self.doc['schema'], 1)
        keys = {'name', 'inputs', 'outputs', 'value', 'requires', 'ensures', 'min_precision', 'status',
                'theorem', 'source', 'flops', 'instances'}
        for k in self.doc['kernels']:
            self.assertEqual(set(k), keys, k['name'])
            self.assertEqual(set(k['instances']), {'binary64', 'binary32'})
            for r in k['requires']:
                self.assertRegex(r, r'^(normalized\(\w+\)|abs_ge\(\w+, \w+\))$')
            errors = [e for e in k['ensures'] if e['kind'] == 'error']
            for e in k['ensures']:
                self.assertIn(e['kind'], ('normalized', 'error', 'leading_rounded'))
                if e['kind'] == 'error':
                    self.assertEqual(list(e), ['kind', 'of', 'form', 'c', 'k', 't', 'when'])
            for inst in k['instances'].values():
                entries = inst if isinstance(inst, list) else [inst]
                self.assertEqual(len(entries), len(errors))
                if len(errors) == 1:
                    self.assertIsInstance(inst, dict)
                for x in entries:
                    self.assertEqual(set(x), {'rel', 'abs'})
                    Fraction(x['rel']), Fraction(x['abs'])

    def test_the_example_of_architecture_md(self):
        k = self.by['mul_2_2']
        self.assertEqual(k['inputs'], [{'name': 'x', 'limbs': 2}, {'name': 'y', 'limbs': 2}])
        self.assertEqual(k['outputs'], [{'name': 'z', 'limbs': 2}])
        self.assertEqual(k['value'], 'x*y')
        self.assertEqual(k['requires'], ['normalized(x)', 'normalized(y)'])
        self.assertEqual(k['ensures'], [{'kind': 'normalized', 'of': 'z'},
                                        {'kind': 'error', 'of': 'z', 'form': 'R', 'c': '4', 'k': 2,
                                         't': '4', 'when': None}])
        self.assertEqual(k['min_precision'], 5)
        self.assertEqual(k['flops'], 9)
        self.assertEqual(k['theorem'], {'file': 'proofs/theories/Mul22.v', 'name': 'mul_2_2_correct'})
        self.assertEqual(k['instances']['binary64']['rel'], '1/20282409603651670423947251286016')
        self.assertEqual(Fraction(k['instances']['binary64']['abs']), Fraction(4, 2 ** 1074))
        self.assertEqual(Fraction(k['instances']['binary32']['rel']), Fraction(4, 2 ** 48))
        self.assertEqual(Fraction(k['instances']['binary32']['abs']), Fraction(4, 2 ** 149))

    def test_instances(self):
        u = Fraction(1, 2 ** 53)
        self.assertEqual(Fraction(self.by['add_2_2']['instances']['binary64']['rel']), 3 / (1 - 4 * u) * u * u)
        u = Fraction(1, 2 ** 24)
        self.assertEqual(Fraction(self.by['add_2_2']['instances']['binary32']['rel']), 3 / (1 - 4 * u) * u * u)
        tp = self.by['two_prod']['instances']['binary64']
        self.assertEqual([Fraction(x['abs']) for x in tp], [Fraction(1, 2 ** 1075), 0])
        self.assertEqual(Fraction(self.by['two_prod_dekker']['instances']['binary32'][0]['abs']),
                         Fraction(7, 2 ** 150))
        self.assertEqual(Fraction(self.by['mul_2_1']['instances']['binary64']['abs']), Fraction(2, 2 ** 1074))
        self.assertEqual(Fraction(self.by['two_sum']['instances']['binary64']['rel']), 0)


if __name__ == '__main__':
    unittest.main()
