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
        self.assertEqual(expr.names(expr.parse('abs(x-y)')), {'x', 'y'})

    def test_abs(self):
        self.assertEqual(expr.parse('abs(x)'), ('abs', ('name', 'x')))
        self.assertEqual(expr.parse('-abs(-x)*y'), ('mul', ('neg', ('abs', ('neg', ('name', 'x')))), ('name', 'y')))
        self.assertEqual(self.value('abs(1-3)*2'), 4)
        self.assertEqual(expr.parse('abs'), ('name', 'abs'))   # a name, as any other
        for text in ('abs(', 'abs()', 'abs(1', 'abs 1'):
            with self.assertRaises(expr.ExprError, msg=text):
                expr.parse(text)


class Claims(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ks = common.kernels()
        cls.doc = json.loads(claims.claims(ks))
        cls.by = {k['name']: k for k in cls.doc['kernels']}

    def test_committed_claims_are_these(self):
        with open(os.path.join(common.GEN, 'claims.json'), encoding='utf-8') as f:
            self.assertEqual(json.load(f), self.doc)

    # The fields of each kind of ensures entry, in order (architecture.md, "Claims", "Claims of the
    # second wave" and "Claims of the non-finite layer").
    FIELDS = {'normalized': ['kind', 'of'], 'leading_rounded': ['kind', 'of'],
              'error': ['kind', 'of', 'form', 'c', 'k', 't', 'when'], 'rounded': ['kind', 'of', 'mode'],
              'upper': ['kind', 'of', 'gaps'], 'predicate': ['kind', 'of', 'rel', 'args'],
              'encloses': ['kind', 'center', 'radius', 'set', 'balls'],
              'extends': ['kind', 'of', 'core', 'lead', 'finite_when'], 'represents': ['kind', 'of'],
              'makes_ball': ['kind', 'center', 'radius', 'from']}

    def test_schema(self):
        self.assertEqual(self.doc['schema'], 1)
        keys = ['name', 'inputs', 'outputs', 'value', 'requires', 'ensures', 'min_precision', 'status',
                'theorem', 'source', 'flops', 'instances']
        for k in self.doc['kernels']:
            extended = k.get('domain') == 'extended'
            want = list(keys)
            if extended:          # the domain after the name, the IEEE-model status after the status
                want.insert(1, 'domain')
                want.insert(want.index('status') + 1, 'ieee_status')
            if all(e['kind'] == 'makes_ball' for e in k['ensures']):
                want.remove('value')          # a ball made from its inputs has no value
            self.assertEqual(list(k), want, k['name'])
            if extended:
                self.assertIn(k['ieee_status'], ('proved', 'unverified'))
            self.assertEqual(set(k['instances']), {'binary64', 'binary32'})
            for g in k['inputs'] + k['outputs']:
                self.assertIn(g, ({'name': g['name'], 'limbs': g['limbs']},
                                  {'name': g['name'], 'limbs': 1, 'type': 'mask'}))
            for r in k['requires']:
                if extended:
                    self.assertRegex(r, r'^(canonical\(\w+\)|ball\(\w+, \w+\)|power_of_two\(\w+\)|nonneg\(\w+\))$')
                else:
                    self.assertRegex(r, r'^(normalized\(\w+\)|abs_ge\(\w+, \w+\)|power_of_two\(\w+\)|nonneg\(\w+\))$')
            errors = [e for e in k['ensures'] if e['kind'] == 'error']
            for e in k['ensures']:
                fields = self.FIELDS[e['kind']] + (['finite_when'] if e['kind'] == 'encloses' and extended else [])
                self.assertEqual(list(e), fields, k['name'])
                for c in e.get('finite_when', []):
                    self.assertEqual(list(c), ['abs_le', 'exp'], k['name'])
                    self.assertIsInstance(c['exp'], int)
            for inst in k['instances'].values():
                # Always a list, one object per error entry (second wave; it was an object when
                # there was one entry).
                self.assertIsInstance(inst, list)
                self.assertEqual(len(inst), len(errors))
                for x in inst:
                    self.assertEqual(set(x), {'rel', 'abs'})
                    Fraction(x['rel']), Fraction(x['abs'])

    def test_second_wave_entries(self):
        self.assertEqual(self.by['lt_2_1']['outputs'], [{'name': 'm', 'limbs': 1, 'type': 'mask'}])
        self.assertEqual(self.by['lt_2_1']['ensures'],
                         [{'kind': 'predicate', 'of': 'm', 'rel': 'lt', 'args': ['x', 'a']}])
        self.assertEqual(self.by['lt_2_1']['instances'], {'binary64': [], 'binary32': []})
        self.assertEqual(self.by['abs_upper_2']['value'], 'abs(x)')
        self.assertEqual(self.by['abs_upper_2']['ensures'], [{'kind': 'rounded', 'of': 't', 'mode': 'up'}])
        self.assertEqual(self.by['radd']['ensures'], [{'kind': 'upper', 'of': 'r', 'gaps': '3/2'}])
        self.assertEqual(self.by['radd']['requires'], ['nonneg(a)', 'nonneg(b)'])
        self.assertEqual(self.by['mul_pow2_2']['requires'], ['normalized(x)', 'power_of_two(c)'])
        b = self.by['ball_mul_2']
        self.assertEqual(b['inputs'], [{'name': 'cx', 'limbs': 2}, {'name': 'rx', 'limbs': 1},
                                       {'name': 'cy', 'limbs': 2}, {'name': 'ry', 'limbs': 1}])
        self.assertEqual(b['outputs'], [{'name': 'cz', 'limbs': 2}, {'name': 'rz', 'limbs': 1}])
        self.assertEqual(b['requires'], ['normalized(cx)', 'nonneg(rx)', 'normalized(cy)', 'nonneg(ry)'])
        self.assertEqual(b['ensures'][1], {'kind': 'encloses', 'center': 'cz', 'radius': 'rz', 'set': 'x*y',
                                           'balls': {'x': {'center': 'cx', 'radius': 'rx'},
                                                     'y': {'center': 'cy', 'radius': 'ry'}}})
        self.assertEqual(self.by['ball_scale_1']['ensures'][0]['set'], 'x*a')
        self.assertEqual(self.by['neg_2']['value'], '-x')

    def test_the_example_of_architecture_md(self):
        k = self.by['mul_2_2']
        self.assertEqual(k['inputs'], [{'name': 'x', 'limbs': 2}, {'name': 'y', 'limbs': 2}])
        self.assertEqual(k['outputs'], [{'name': 'z', 'limbs': 2}])
        self.assertEqual(k['value'], 'x*y')
        self.assertEqual(k['requires'], ['normalized(x)', 'normalized(y)'])
        self.assertEqual(k['ensures'], [{'kind': 'normalized', 'of': 'z'},
                                        {'kind': 'error', 'of': 'z', 'form': 'R', 'c': '4', 'k': 2,
                                         't': '3/2', 'when': None}])
        self.assertEqual(k['min_precision'], 4)
        self.assertEqual(k['flops'], 9)
        self.assertEqual(k['theorem'], {'file': 'proofs/theories/Mul22.v', 'name': 'mul_2_2_correct'})
        self.assertEqual(k['instances']['binary64'][0]['rel'], '1/20282409603651670423947251286016')
        self.assertEqual(Fraction(k['instances']['binary64'][0]['abs']), Fraction(3, 2 ** 1075))
        self.assertEqual(Fraction(k['instances']['binary32'][0]['rel']), Fraction(4, 2 ** 48))
        self.assertEqual(Fraction(k['instances']['binary32'][0]['abs']), Fraction(3, 2 ** 150))

    def test_the_entries_of_the_non_finite_layer_in_architecture_md(self):
        # The three entries written out in full there, with source, flops and the theorem fields
        # left out; field for field, in that order.
        def shown(name):
            return [(key, v) for key, v in self.by[name].items() if key not in ('source', 'flops', 'theorem')]
        self.assertEqual(shown('add_2_1_full'), list({
            'name': 'add_2_1_full', 'domain': 'extended',
            'inputs': [{'name': 'x', 'limbs': 2}, {'name': 'a', 'limbs': 1}],
            'outputs': [{'name': 'w', 'limbs': 2}],
            'value': 'x+a',
            'requires': ['canonical(x)'],
            'ensures': [{'kind': 'extends', 'of': 'w', 'core': 'add_2_1', 'lead': 'add', 'finite_when': []}],
            'min_precision': 3, 'status': 'unverified', 'ieee_status': 'unverified',
            'instances': {'binary64': [], 'binary32': []}}.items()))
        self.assertEqual(shown('ball_mul_2_full'), list({
            'name': 'ball_mul_2_full', 'domain': 'extended',
            'inputs': [{'name': 'cx', 'limbs': 2}, {'name': 'rx', 'limbs': 1},
                       {'name': 'cy', 'limbs': 2}, {'name': 'ry', 'limbs': 1}],
            'outputs': [{'name': 'cw', 'limbs': 2}, {'name': 'rw', 'limbs': 1}],
            'value': 'cx*cy',
            'requires': ['ball(cx, rx)', 'ball(cy, ry)'],
            'ensures': [{'kind': 'encloses', 'center': 'cw', 'radius': 'rw', 'set': 'x*y',
                         'balls': {'x': {'center': 'cx', 'radius': 'rx'}, 'y': {'center': 'cy', 'radius': 'ry'}},
                         'finite_when': []}],
            'min_precision': 4, 'status': 'unverified', 'ieee_status': 'unverified',
            'instances': {'binary64': [], 'binary32': []}}.items()))
        self.assertEqual(shown('ball_make_2'), list({
            'name': 'ball_make_2', 'domain': 'extended',
            'inputs': [{'name': 'c', 'limbs': 2}, {'name': 'r', 'limbs': 1}],
            'outputs': [{'name': 'cw', 'limbs': 2}, {'name': 'rw', 'limbs': 1}],
            'requires': ['canonical(c)'],
            'ensures': [{'kind': 'makes_ball', 'center': 'cw', 'radius': 'rw',
                         'from': {'center': 'c', 'radius': 'r'}}],
            'min_precision': 1, 'status': 'unverified', 'ieee_status': 'unverified',
            'instances': {'binary64': [], 'binary32': []}}.items()))
        # The two conditions of finite_when that architecture.md gives, and no other.
        self.assertEqual(self.by['add_2_2_full']['ensures'][0]['finite_when'],
                         [{'abs_le': 'x', 'exp': -2}, {'abs_le': 'y', 'exp': -2}])
        self.assertEqual(self.by['mul_2_2_full']['ensures'][0]['finite_when'], [{'abs_le': 'x*y', 'exp': -1}])
        for k in self.doc['kernels']:
            if k['name'] not in ('add_2_2_full', 'mul_2_2_full'):
                for e in k['ensures']:
                    self.assertEqual(e.get('finite_when', []), [], k['name'])
        self.assertEqual(self.by['make_2']['ensures'], [{'kind': 'represents', 'of': 'x'}])
        self.assertEqual(self.by['make_2']['value'], 'a')
        self.assertEqual(self.by['make_2_limbs']['inputs'], [{'name': 'y', 'limbs': 2}])
        self.assertEqual(self.by['make_2_limbs']['requires'], ['canonical(y)'])
        self.assertEqual(self.by['ball_scale_1_full']['requires'], ['ball(cx, rx)'])
        self.assertEqual(self.by['mul_pow2_2_full']['requires'], ['canonical(x)', 'power_of_two(c)'])

    def test_the_kernels_that_need_no_fix_up(self):
        # Their real-model claims and theorems as before, canonical where normalized was.
        for name in ('neg_2', 'abs_2', 'lt_2_2', 'le_2_2', 'eq_2_2', 'lt_2_1', 'le_2_1', 'eq_2_1', 'lt_1_2',
                     'le_1_2', 'to_nearest_2', 'to_down_2', 'to_up_2', 'abs_upper_2', 'radd', 'rmul'):
            k = self.by[name]
            self.assertEqual((k['domain'], k['status'], k['ieee_status']), ('extended', 'proved', 'unverified'))
            self.assertIsNotNone(k['theorem'], name)
            self.assertNotIn('ieee_theorem', k)
            self.assertFalse(any(r.startswith('normalized') for r in k['requires']), name)
        self.assertEqual(self.by['lt_2_1']['requires'], ['canonical(x)'])
        self.assertEqual(self.by['radd']['requires'], ['nonneg(a)', 'nonneg(b)'])
        # The cores keep the domain finite.
        for name in ('add_2_2', 'mul_2_1', 'ball_mul_2', 'ball_neg_1'):
            self.assertNotIn('domain', self.by[name])
            self.assertNotIn('ieee_status', self.by[name])

    def test_instances(self):
        u = Fraction(1, 2 ** 53)
        self.assertEqual(Fraction(self.by['add_2_2']['instances']['binary64'][0]['rel']), 3 / (1 - 4 * u) * u * u)
        u = Fraction(1, 2 ** 24)
        self.assertEqual(Fraction(self.by['add_2_2']['instances']['binary32'][0]['rel']), 3 / (1 - 4 * u) * u * u)
        tp = self.by['two_prod']['instances']['binary64']
        self.assertEqual([Fraction(x['abs']) for x in tp], [Fraction(1, 2 ** 1075), 0])
        self.assertEqual(Fraction(self.by['two_prod_dekker']['instances']['binary32'][0]['abs']),
                         Fraction(13, 2 ** 152))       # (13/8) eta, eta = 2^-149
        self.assertEqual(Fraction(self.by['mul_2_1']['instances']['binary64'][0]['abs']), Fraction(1, 2 ** 1074))
        self.assertEqual(Fraction(self.by['two_sum']['instances']['binary64'][0]['rel']), 0)
        u = Fraction(1, 2 ** 53)
        self.assertEqual(Fraction(self.by['mul_1_1']['instances']['binary64'][0]['rel']), u / (1 + u))


if __name__ == '__main__':
    unittest.main()
