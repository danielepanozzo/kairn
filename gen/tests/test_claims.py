"""The expression parser and gen/claims.json."""
import json
import os
import re
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
                     'eval(1)', '1;2', '2^u', '2^1.5', '2^(3)', '[1]', 'unit(1)', 'unit(a+b)', 'tiny()'):
            with self.assertRaises(expr.ExprError, msg=text):
                self.value(text, u=1)
        with self.assertRaises(expr.ExprError):
            self.value('1/(1-1)')
        with self.assertRaises(expr.ExprError):
            self.value('0^-1')
        with self.assertRaises(expr.ExprError):
            self.value('v')
        with self.assertRaises(expr.ExprError):
            self.value('unit(k)')

    def test_powers_and_bounds(self):
        # What a constant up(EXPR) may say: integer powers, and unit(K), tiny(K) of a kernel K.
        self.assertEqual(self.value('2^3'), 8)
        self.assertEqual(self.value('2^-3'), Fraction(1, 8))
        self.assertEqual(self.value('-2^2'), -4)                 # the power binds tighter
        self.assertEqual(self.value('(1+u)^6', u=Fraction(1, 2)), Fraction(3, 2) ** 6)
        self.assertEqual(self.value('2*3^2'), 18)
        tree = expr.parse('unit(mul_2_2)/(1-unit(mul_2_2))*(1+u) + tiny(add_1_1)')
        self.assertEqual(expr.calls(tree), {('unit', 'mul_2_2'), ('tiny', 'add_1_1')})
        self.assertEqual(expr.names(tree), {'u'})
        env = {'unit(mul_2_2)': Fraction(1, 4), 'tiny(add_1_1)': Fraction(1, 8), 'u': Fraction(1, 2)}
        self.assertEqual(expr.evaluate(tree, env), Fraction(1, 4) / Fraction(3, 4) * Fraction(3, 2) + Fraction(1, 8))
        self.assertEqual(expr.parse('unit'), ('name', 'unit'))     # a name when no ( follows

    def test_names(self):
        self.assertEqual(expr.names(expr.parse('x*y+x')), {'x', 'y'})
        self.assertEqual(expr.names(expr.parse('3/(1-4*u)')), {'u'})
        self.assertEqual(expr.names(expr.parse('abs(x-y)')), {'x', 'y'})

    def test_limbs(self):
        # A limb of a group, in the conditions of exact_when: cx[1] is the second limb of cx.
        self.assertEqual(expr.parse('cx[1]*c'), ('mul', ('limb', 'cx', 1), ('name', 'c')))
        self.assertEqual(expr.names(expr.parse('cx[0]*c+rx')), {'cx', 'c', 'rx'})
        self.assertEqual(expr.limbs(expr.parse('abs(cx[0])+cx[1]')), {('cx', 0), ('cx', 1)})
        self.assertEqual(expr.evaluate(expr.parse('cx[1]*2'), {'cx[1]': Fraction(3)}), 6)
        for text in ('cx[]', 'cx[a]', 'cx[1', 'cx]', '[0]', 'cx[-1]'):
            with self.assertRaises(expr.ExprError, msg=text):
                expr.parse(text)
        with self.assertRaises(expr.ExprError):
            expr.evaluate(expr.parse('cx[2]'), {'cx[1]': Fraction(1)})

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
    # second wave", "Claims of the non-finite layer" and "Claims of Milestone 2").
    FIELDS = {'normalized': ['kind', 'of'], 'leading_rounded': ['kind', 'of'],
              'error': ['kind', 'of', 'form', 'c', 'k', 't', 'when'], 'rounded': ['kind', 'of', 'mode'],
              'upper': ['kind', 'of', 'gaps'], 'predicate': ['kind', 'of', 'rel', 'args'],
              'encloses': ['kind', 'center', 'radius', 'set', 'balls'],
              'extends': ['kind', 'of', 'core', 'lead', 'finite_when'], 'represents': ['kind', 'of'],
              'makes_ball': ['kind', 'center', 'radius', 'from'],
              'neighbor': ['kind', 'of', 'side'], 'bound': ['kind', 'of', 'side', 'steps']}
    # The fields that some entries of a kind have, after the others, and only when they say
    # something: a rounding under a condition, and an exactness condition (Milestone 2). Every
    # entry without them has the shape it had before.
    OPTIONAL = {'rounded': ['when'], 'error': ['exact_when'], 'encloses': ['exact_when']}

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
            if 'ieee_only' in k:  # no real-model statement: right after the domain, and only true
                want.insert(2, 'ieee_only')
                self.assertIs(k['ieee_only'], True, k['name'])
            if 'ieee_theorem' in k:          # the IEEE-model theorem after the real-model one
                want.insert(want.index('theorem') + 1, 'ieee_theorem')
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
                fields += [f for f in self.OPTIONAL.get(e['kind'], []) if f in e]
                self.assertEqual(list(e), fields, k['name'])
                for c in e.get('finite_when', []):
                    self.assertEqual(list(c), ['abs_le', 'exp'], k['name'])
                    self.assertIsInstance(c['exp'], int)
                for c in e.get('exact_when', []):
                    self.assertIn(list(c), (['zero_or_abs_gt', 'than'], ['zero_or_abs_ge', 'than']), k['name'])
                if 'when' in e and e['kind'] == 'rounded':
                    self.assertEqual(e['when'], 'product_large', k['name'])
                if e['kind'] == 'bound':
                    self.assertIsInstance(e['steps'], int)
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
            return [(key, v) for key, v in self.by[name].items() if key not in ('source', 'flops', 'theorem', 'ieee_theorem')]
        self.assertEqual(shown('add_2_1_full'), list({
            'name': 'add_2_1_full', 'domain': 'extended', 'ieee_only': True,
            'inputs': [{'name': 'x', 'limbs': 2}, {'name': 'a', 'limbs': 1}],
            'outputs': [{'name': 'w', 'limbs': 2}],
            'value': 'x+a',
            'requires': ['canonical(x)'],
            'ensures': [{'kind': 'extends', 'of': 'w', 'core': 'add_2_1', 'lead': 'add',
                         'finite_when': [{'abs_le': 'x', 'exp': -2}, {'abs_le': 'a', 'exp': -2}]}],
            'min_precision': 3, 'status': 'proved', 'ieee_status': 'proved',
            'instances': {'binary64': [], 'binary32': []}}.items()))
        self.assertEqual(shown('ball_mul_2_full'), list({
            'name': 'ball_mul_2_full', 'domain': 'extended', 'ieee_only': True,
            'inputs': [{'name': 'cx', 'limbs': 2}, {'name': 'rx', 'limbs': 1},
                       {'name': 'cy', 'limbs': 2}, {'name': 'ry', 'limbs': 1}],
            'outputs': [{'name': 'cw', 'limbs': 2}, {'name': 'rw', 'limbs': 1}],
            'value': 'cx*cy',
            'requires': ['ball(cx, rx)', 'ball(cy, ry)'],
            'ensures': [{'kind': 'encloses', 'center': 'cw', 'radius': 'rw', 'set': 'x*y',
                         'balls': {'x': {'center': 'cx', 'radius': 'rx'}, 'y': {'center': 'cy', 'radius': 'ry'}},
                         'finite_when': [{'abs_le': '(abs(cx)+rx)*(abs(cy)+ry)', 'exp': -2}]}],
            'min_precision': 4, 'status': 'proved', 'ieee_status': 'proved',
            'instances': {'binary64': [], 'binary32': []}}.items()))
        self.assertEqual(shown('ball_make_2'), list({
            'name': 'ball_make_2', 'domain': 'extended', 'ieee_only': True,
            'inputs': [{'name': 'c', 'limbs': 2}, {'name': 'r', 'limbs': 1}],
            'outputs': [{'name': 'cw', 'limbs': 2}, {'name': 'rw', 'limbs': 1}],
            'requires': ['canonical(c)'],
            'ensures': [{'kind': 'makes_ball', 'center': 'cw', 'radius': 'rw',
                         'from': {'center': 'c', 'radius': 'r'}}],
            'min_precision': 1, 'status': 'proved', 'ieee_status': 'proved',
            'instances': {'binary64': [], 'binary32': []}}.items()))
        # The conditions of finite_when: those that architecture.md gives, and the thresholds
        # proved for the other full kernels (IeeeFull.v; IeeeBallFinite.v for the balls: the
        # largest magnitude of a member of the exact result, at most a quarter of the overflow
        # threshold, a sixteenth for ball_mul_1_full); none for ball_neg_k, which has no fix-up.
        def bound(text, e):
            return {'abs_le': text, 'exp': e}
        want = {'ball_add_1_full': [bound('abs(cx+cy)+rx+ry', -2)],
                'ball_add_2_full': [bound('abs(cx+cy)+rx+ry', -2)],
                'ball_sub_1_full': [bound('abs(cx-cy)+rx+ry', -2)],
                'ball_sub_2_full': [bound('abs(cx-cy)+rx+ry', -2)],
                'ball_mul_1_full': [bound('(abs(cx)+rx)*(abs(cy)+ry)', -4)],
                'ball_mul_2_full': [bound('(abs(cx)+rx)*(abs(cy)+ry)', -2)],
                'ball_scale_1_full': [bound('(abs(cx)+rx)*a', -2)],
                'ball_scale_2_full': [bound('(abs(cx)+rx)*a', -2)],
                'ball_mul_pow2_1_full': [bound('(abs(cx)+rx)*c', -2)],
                'ball_mul_pow2_2_full': [bound('(abs(cx)+rx)*c', -2)],
                'add_2_2_full': [bound('x', -2), bound('y', -2)],
                'sub_2_2_full': [bound('x', -2), bound('y', -2)],
                'add_fast_2_2_full': [bound('x', -2), bound('y', -2)],
                'add_2_1_full': [bound('x', -2), bound('a', -2)],
                'sub_2_1_full': [bound('x', -2), bound('a', -2)],
                'sub_1_2_full': [bound('a', -2), bound('y', -2)],
                'mul_2_2_full': [bound('x*y', -1)],
                'mul_2_1_full': [bound('x*a', -1)],
                'mul_pow2_2_full': [bound('x*c', -1)]}
        for k in self.doc['kernels']:
            for e in k['ensures']:
                self.assertEqual(e.get('finite_when', []), want.get(k['name'], []), k['name'])
        self.assertEqual(self.by['make_2']['ensures'], [{'kind': 'represents', 'of': 'x'}])
        self.assertEqual(self.by['make_2']['value'], 'a')
        self.assertEqual(self.by['make_2_limbs']['inputs'], [{'name': 'y', 'limbs': 2}])
        self.assertEqual(self.by['make_2_limbs']['requires'], ['canonical(y)'])
        self.assertEqual(self.by['ball_scale_1_full']['requires'], ['ball(cx, rx)'])
        self.assertEqual(self.by['mul_pow2_2_full']['requires'], ['canonical(x)', 'power_of_two(c)'])

    def test_the_kernels_that_need_no_fix_up(self):
        # Their real-model claims and theorems as before, canonical where normalized was.
        for name in ('neg_2', 'abs_2', 'lt_2_2', 'le_2_2', 'eq_2_2', 'lt_2_1', 'le_2_1', 'eq_2_1', 'lt_1_2',
                     'le_1_2', 'to_nearest_2', 'to_down_2', 'to_up_2', 'abs_upper_2', 'radd', 'rmul',
                     'ball_neg_1', 'ball_neg_2'):
            k = self.by[name]
            self.assertEqual((k['domain'], k['status'], k['ieee_status']), ('extended', 'proved', 'proved'))
            self.assertIsNotNone(k['theorem'], name)
            self.assertIsNotNone(k['ieee_theorem'], name)
            self.assertFalse(any(r.startswith('normalized') for r in k['requires']), name)
        self.assertEqual(self.by['lt_2_1']['requires'], ['canonical(x)'])
        self.assertEqual(self.by['radd']['requires'], ['nonneg(a)', 'nonneg(b)'])
        # neg_2 and abs_2 say with represents which non-finite value comes out; ball_neg_k reads
        # its encloses in the extended domain, from a ball.
        self.assertEqual(self.by['neg_2']['ensures'][2], {'kind': 'represents', 'of': 'z'})
        self.assertEqual(self.by['abs_2']['ensures'][2], {'kind': 'represents', 'of': 'z'})
        self.assertEqual(self.by['ball_neg_2']['requires'], ['ball(cx, rx)'])
        self.assertEqual(self.by['ball_neg_2']['ensures'][-1]['finite_when'], [])
        # The cores keep the domain finite.
        for name in ('add_2_2', 'mul_2_1', 'ball_mul_2', 'ball_add_1'):
            self.assertNotIn('domain', self.by[name])
            self.assertNotIn('ieee_status', self.by[name])

    def test_the_entries_of_milestone2_in_architecture_md(self):
        # The entries of the claims of Milestone 2, wave 1, as architecture.md writes them out
        # ("Claims of Milestone 2"), field for field.
        self.assertEqual(self.by['next_up']['ensures'], [{'kind': 'neighbor', 'of': 'r', 'side': 'up'}])
        self.assertEqual(self.by['next_down']['ensures'], [{'kind': 'neighbor', 'of': 'r', 'side': 'down'}])
        self.assertEqual(self.by['next_up']['value'], 'a')
        self.assertEqual(self.by['add_down_1']['ensures'], [{'kind': 'rounded', 'of': 'r', 'mode': 'down'}])
        self.assertEqual((self.by['add_down_1']['domain'], self.by['sub_up_1']['value']), ('extended', 'a-b'))
        self.assertEqual(self.by['mul_down_1']['ensures'], [
            {'kind': 'bound', 'of': 'r', 'side': 'below', 'steps': 1},
            {'kind': 'rounded', 'of': 'r', 'mode': 'down', 'when': 'product_large'}])
        self.assertEqual(self.by['mul_up_1']['ensures'], [
            {'kind': 'bound', 'of': 'r', 'side': 'above', 'steps': 1},
            {'kind': 'rounded', 'of': 'r', 'mode': 'up', 'when': 'product_large'}])
        n = 'eta/(2*u)'
        self.assertEqual(self.by['ball_mul_pow2_2']['ensures'], [
            {'kind': 'normalized', 'of': 'cz'},
            {'kind': 'encloses', 'center': 'cz', 'radius': 'rz', 'set': 'x*c',
             'balls': {'x': {'center': 'cx', 'radius': 'rx'}},
             'exact_when': [{'zero_or_abs_gt': 'cx[0]*c', 'than': n}, {'zero_or_abs_gt': 'cx[1]*c', 'than': n},
                            {'zero_or_abs_gt': 'rx*c', 'than': n}]}])
        self.assertEqual(self.by['ball_mul_pow2_1_full']['ensures'], [
            {'kind': 'encloses', 'center': 'cw', 'radius': 'rw', 'set': 'x*c',
             'balls': {'x': {'center': 'cx', 'radius': 'rx'}},
             'finite_when': [{'abs_le': '(abs(cx)+rx)*c', 'exp': -2}],
             'exact_when': [{'zero_or_abs_gt': 'cx*c', 'than': n}, {'zero_or_abs_gt': 'rx*c', 'than': n}]}])
        # The entry forms claim what the kernel they call claims.
        for entry, core in (('two_sum_entry', 'two_sum'), ('fast_two_sum_entry', 'fast_two_sum'),
                            ('radd_entry', 'radd'), ('add_down_entry', 'add_down_1'), ('add_up_entry', 'add_up_1'),
                            ('sub_down_entry', 'sub_down_1'), ('sub_up_entry', 'sub_up_1')):
            for key in ('inputs', 'outputs', 'value', 'requires', 'ensures', 'min_precision', 'instances'):
                self.assertEqual(self.by[entry][key], self.by[core][key], (entry, key))
            self.assertEqual(self.by[entry].get('domain'), self.by[core].get('domain'), entry)
        # An error entry without exact_when, and a rounded entry without when, are as before.
        self.assertNotIn('exact_when', self.by['mul_pow2_2']['ensures'][1])
        self.assertEqual(self.by['to_down_2']['ensures'], [{'kind': 'rounded', 'of': 't', 'mode': 'down'}])
        # The four entries that architecture.md writes out in full are these, field for field.
        with open(os.path.join(common.ROOT, 'docs', 'developer', 'architecture.md'), encoding='utf-8') as f:
            text = f.read()
        section = text.split('### Claims of Milestone 2')[1].split('\n## ')[0]
        blocks = re.findall(r'```json\n(.*?)```', section, re.S)
        shown = json.loads('[' + blocks[1] + ']')
        self.assertEqual([e['name'] for e in shown], ['next_up', 'mul_down_1', 'ball_mul_pow2_2', 'ball_mul_pow2_1_full'])
        for e in shown:
            want = [(key, v) for key, v in self.by[e['name']].items()
                    if key not in ('source', 'flops', 'theorem', 'ieee_theorem')]
            self.assertEqual(list(e.items()), want, e['name'])

    def test_ieee_only(self):
        # Exactly the kernels without a real-model statement say so: the nine full kernels, the
        # ten full Ball kernels and the four constructors; ball_neg_k, which also requires a ball
        # and claims encloses, has a real-model statement and no such field.
        full = {f'{op}_full' for op in ('add_2_2', 'add_fast_2_2', 'sub_2_2', 'add_2_1', 'sub_2_1', 'sub_1_2',
                                        'mul_2_2', 'mul_2_1', 'mul_pow2_2')}
        full_ball = {f'ball_{op}_{k}_full' for op in ('add', 'sub', 'mul', 'scale', 'mul_pow2') for k in (1, 2)}
        constructors = {'make_2', 'make_2_limbs', 'ball_make_1', 'ball_make_2'}
        self.assertEqual({k['name'] for k in self.doc['kernels'] if 'ieee_only' in k}, full | full_ball | constructors)
        self.assertTrue(all(k['ieee_only'] is True for k in self.doc['kernels'] if 'ieee_only' in k))
        self.assertEqual(list(self.by['ball_add_1_full'])[:3], ['name', 'domain', 'ieee_only'])
        for name in ('ball_neg_1', 'ball_neg_2', 'neg_2', 'ball_add_1'):
            self.assertNotIn('ieee_only', self.by[name])

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
