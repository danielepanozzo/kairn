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

    def test_up_inside_an_expression(self):
        # A constant of a claim names a constant as the format rounds it (Milestone 2, outward).
        tree = expr.parse('2*up((1+u)^3)*eta')
        self.assertEqual(tree, ('mul', ('mul', ('int', 2), ('up', ('pow', ('add', ('int', 1), ('name', 'u')), 3))),
                                ('name', 'eta')))
        self.assertEqual(expr.names(tree), {'u', 'eta'})
        env = {'u': Fraction(1, 4), 'eta': Fraction(1, 8)}
        self.assertEqual(expr.evaluate(tree, env, lambda x: Fraction(2)), Fraction(1, 2))
        with self.assertRaises(expr.ExprError):
            expr.evaluate(tree, env)                       # no format to round in
        for text in ('up(', 'up()', 'up(1'):
            with self.assertRaises(expr.ExprError, msg=text):
                expr.parse(text)
        self.assertEqual(expr.parse('up'), ('name', 'up'))  # a name when no ( follows

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
              'neighbor': ['kind', 'of', 'side'], 'bound': ['kind', 'of', 'side', 'steps'],
              'holds': ['kind', 'rel', 'args', 'if'], 'finite_or_nan': ['kind', 'of', 'flag'],
              'maximum': ['kind', 'of', 'args'],
              # The interval kernels and the bounds of two limbs (Milestone 2).
              'outward': ['kind', 'of', 'side', 'rel', 'abs'],
              'makes_interval': ['kind', 'lower', 'upper', 'from'],
              'encloses_interval': ['kind', 'lower', 'upper', 'set', 'intervals', 'tight', 'bounded_when'],
              'set_bound': ['kind', 'of', 'side', 'set', 'balls'],
              # Stage B1 of the intervals: the set operations, the conversions and the split.
              'interval_set': ['kind', 'lower', 'upper', 'set', 'intervals'],
              'ball_of_interval': ['kind', 'center', 'radius', 'from', 'special', 'rel', 'abs'],
              'interval_of_ball': ['kind', 'lower', 'upper', 'set', 'balls', 'tight'],
              'splits': ['kind', 'parts', 'from'],
              # Stage B2: the predicates and the three-valued comparisons of the enclosure interface.
              'certain': ['kind', 'of', 'rel', 'args'], 'trit': ['kind', 'yes', 'no', 'rel', 'args'],
              # and the set operations of a ball
              'ball_set': ['kind', 'center', 'radius', 'set', 'balls'], 'ball_splits': ['kind', 'parts', 'from']}
    # The fields that some entries of a kind have, after the others, and only when they say
    # something: a rounding under a condition, an exactness condition, the zero of a product of
    # bounds, the midpoint of a ball made from an interval, an equivalence for the bounded result,
    # a tightness (Milestone 2); the zero of a product of intervals or of bounds of two limbs, the
    # smallest radius of a ball made from an interval (stage B1); the mask and the steps of the
    # finish of a fold of maxima; a value of its own (the accumulator's sum of magnitudes). Every
    # entry without them has the shape it had before.
    # exact_flag (of error) and unless, exact_when (of an upper entry with a value of its own): the
    # steps and the radius of the scaling of a BallVector by a power of two.
    OPTIONAL = {'rounded': ['when', 'zero_factor', 'value'], 'error': ['exact_when', 'exact_flag'],
                'encloses': ['exact_when'], 'upper': ['unless', 'exact_when'],
                'bound': ['zero_factor'], 'outward': ['exact_when', 'zero_factor'],
                'encloses_interval': ['bounded_exactly', 'zero_factor'], 'set_bound': ['tight'],
                'finite_or_nan': ['if', 'steps', 'nonneg', 'if_all'],   # the finish of a fold of maxima; of a constructor; of a product of BallVectors
                # the sets of a predicate (one of the two), and its exactness (stage B2)
                'certain': ['intervals', 'balls', 'exact', 'exact_when'],
                'trit': ['intervals', 'balls', 'exact', 'exact_when'],
                # the conversions of two limbs and the ball from an interval of one limb (stage B2)
                'makes_ball': ['midpoint_when', 'rel', 'abs', 'smallest_radius'],
                'ball_of_interval': ['smallest_radius', 'finite_when'],
                'interval_of_ball': ['bounded_when']}
    # The bound kernels of Milestone 2 (the folds' stage): an upper entry with a value of its own
    # under a mask, and no gaps.
    UPPER_OWN = ['kind', 'of', 'value', 'if']
    # The kinds whose entries name their own set or make a value from the inputs: a kernel whose
    # every entry is one of them has no value.
    OWN_SET = ('makes_ball', 'makes_interval', 'encloses_interval', 'set_bound', 'interval_set', 'ball_of_interval',
               'interval_of_ball', 'splits', 'certain', 'trit', 'ball_set', 'ball_splits')

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
            if all(e['kind'] in self.OWN_SET for e in k['ensures']):
                want.remove('value')          # a ball or an interval made from its inputs, or a set
            if all(e['kind'] in ('holds', 'maximum') or (e['kind'] == 'upper' and 'value' in e) for e in k['ensures']):
                want.remove('value')          # a bound kernel, a maximum: every entry has its own value
            self.assertEqual(list(k), want, k['name'])
            if extended:
                self.assertIn(k['ieee_status'], ('proved', 'unverified'))
            self.assertEqual(set(k['instances']), {'binary64', 'binary32'})
            for g in k['inputs'] + k['outputs']:
                self.assertIn(g, ({'name': g['name'], 'limbs': g['limbs']},
                                  {'name': g['name'], 'limbs': 1, 'type': 'mask'}))
            for r in k['requires']:
                if extended:
                    self.assertRegex(r, r'^(canonical\(\w+\)|ball\(\w+, \w+\)|power_of_two\(\w+\)|nonneg\(\w+\)'
                                        r'|interval\(\w+, \w+\)|not_nan\(\w+\))$')
                else:
                    self.assertRegex(r, r'^(normalized\(\w+\)|abs_ge\(\w+, \w+\)|power_of_two\(\w+\)|nonneg\(\w+\)'
                                        r'|count\(\w+\)|format\(half\)|at_most\(\w+, [1-9][0-9]*\))$')
            errors = [e for e in k['ensures'] if e['kind'] == 'error']
            for e in k['ensures']:
                fields = self.FIELDS[e['kind']] + (['finite_when'] if e['kind'] == 'encloses' and extended else [])
                if e['kind'] == 'upper' and 'value' in e:
                    # Its mask only when it has one (the radius kernels of BallVector have none).
                    fields = [f for f in self.UPPER_OWN if f != 'if' or 'if' in e]
                fields += [f for f in self.OPTIONAL.get(e['kind'], []) if f in e]
                self.assertEqual(list(e), fields, k['name'])
                for c in e.get('finite_when', []):
                    self.assertEqual(list(c), ['abs_le', 'exp'], k['name'])
                    self.assertIsInstance(c['exp'], int)
                for c in e.get('exact_when', []):
                    allowed = (['zero_or_abs_gt', 'than'], ['zero_or_abs_ge', 'than'])
                    if e['kind'] in ('certain', 'trit'):
                        # Stage B2: |EXPR| <= Omega, and only that.
                        self.assertEqual(c, {'abs_le': c.get('abs_le'), 'omega': True}, k['name'])
                        self.assertEqual(list(c), ['abs_le', 'omega'], k['name'])
                        continue
                    self.assertIn(list(c), allowed + ((['zero'],) if e['kind'] == 'outward' else ()) +
                                  ((['mask'],) if e['kind'] == 'upper' else ()), k['name'])
                if 'exact_flag' in e:
                    # A mask output, named after the conditions of exactness it says hold.
                    self.assertIn({'name': e['exact_flag'], 'limbs': 1, 'type': 'mask'}, k['outputs'], k['name'])
                    self.assertIn('exact_when', e, k['name'])
                if 'unless' in e:
                    self.assertIn({'name': e['unless'], 'limbs': 1, 'type': 'mask'}, k['inputs'], k['name'])
                if 'when' in e and e['kind'] == 'rounded':
                    self.assertEqual(e['when'], 'product_large', k['name'])
                if e['kind'] == 'bound':
                    self.assertIsInstance(e['steps'], int)
                if e['kind'] in ('certain', 'trit'):
                    # Stage B2: the sets are intervals or balls, one of the two; exact, when given, is
                    # true and excludes exact_when.
                    self.assertEqual(len([key for key in ('intervals', 'balls') if key in e]), 1, k['name'])
                    self.assertFalse('exact' in e and 'exact_when' in e, k['name'])
                    for b in e.get('intervals', e.get('balls', {})).values():
                        self.assertIn(list(b), (['lower', 'upper'], ['center', 'radius']), k['name'])
                for flag in ('zero_factor', 'bounded_exactly', 'smallest_radius', 'exact'):
                    if flag in e:
                        self.assertIs(e[flag], True, k['name'])
                if e['kind'] == 'makes_ball':
                    self.assertIn(list(e['from']), (['center', 'radius'], ['lower', 'upper']), k['name'])
                    for c in e.get('midpoint_when', []):
                        self.assertEqual(list(c), ['half_in_format'], k['name'])
                if e['kind'] == 'interval_set':
                    self.assertIn(e['set'], ('union', 'intersection'), k['name'])
                if e['kind'] == 'ball_of_interval':
                    self.assertIn(e['special'], ('ieee1788', 'ball'), k['name'])
                if e['kind'] in ('ball_of_interval', 'splits'):
                    self.assertEqual(list(e['from']), ['lower', 'upper'], k['name'])
                if e['kind'] == 'ball_set':
                    self.assertIn(e['set'], ('union', 'intersection'), k['name'])
                    self.assertEqual([list(b) for b in e['balls'].values()], [['center', 'radius']] * 2, k['name'])
                if e['kind'] == 'ball_splits':
                    self.assertEqual(list(e['from']), ['center', 'radius'], k['name'])
                    self.assertEqual([list(q) for q in e['parts']], [['center', 'radius']] * 2, k['name'])
                if e['kind'] == 'splits':
                    self.assertEqual([list(q) for q in e['parts']], [['lower', 'upper']] * 2, k['name'])
                if e['kind'] in ('encloses_interval', 'set_bound', 'interval_set', 'interval_of_ball'):
                    t = e.get('tight')
                    if t is not None:
                        self.assertIn(list(t), (['kind'], ['kind', 'steps'], ['kind', 'steps', 'when'],
                                                ['kind', 'rel', 'abs'], ['kind', 'rel', 'abs', 'exact_when']), k['name'])
                        for side, conds in t.get('exact_when', {}).items():
                            self.assertIn(side, ('lower', 'upper'))
                            self.assertTrue(all(list(c) == ['zero'] for c in conds), k['name'])
                    for c in e.get('bounded_when', []):
                        self.assertIn(list(c), (['abs_le', 'omega'], ['abs_le', 'exp']), k['name'])
                    names = e.get('intervals', e.get('balls'))
                    for b in names.values():
                        self.assertIn(list(b), (['lower', 'upper'], ['center', 'radius']), k['name'])
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
                'mul_pow2_2_full': [bound('x*c', -1)],
                # Milestone 2: a ball of two limbs narrowed to one, finite while no member exceeds a
                # quarter of the threshold (its radius plus the second limb then stays below it).
                'ball_narrow_2_1': [bound('abs(c)+r', -2)],
                # Stage B2: the midpoint and radius of an interval of two limbs, and its ball, whose
                # radius is finite while both bounds are within a quarter of the threshold
                # (ball_of_interval with finite_when).
                'interval_mid_rad_2': [bound('xl', -2), bound('xu', -2)],
                'interval_to_ball_2': [bound('xl', -2), bound('xu', -2)]}
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

    def test_the_entries_of_the_interval_kernels_in_architecture_md(self):
        # The entries that architecture.md writes out ("Claims of the interval kernels"), field for
        # field and in order, and the ensures of three more.
        with open(os.path.join(common.ROOT, 'docs', 'developer', 'architecture.md'), encoding='utf-8') as f:
            text = f.read()
        section = text.split('### Claims of the interval kernels')[1].split('\n## ')[0]
        blocks = re.findall(r'```json\n(.*?)```', section, re.S)
        shown = json.loads('[' + blocks[0] + ']')
        self.assertEqual([e['name'] for e in shown], ['interval_add_1', 'interval_make_1', 'mul_dir_1', 'add_ball_2_2',
                                                     'ball_lower_as_1'])
        for e in shown:
            want = [(key, v) for key, v in self.by[e['name']].items()
                    if key not in ('source', 'flops', 'theorem', 'ieee_theorem')]
            self.assertEqual(list(e.items()), want, e['name'])
        ensures = json.loads('[' + blocks[1] + ']')
        for name, e in zip(('add_down_2_2', 'interval_mul_1', 'interval_add_2'), ensures):
            self.assertEqual(e, self.by[name]['ensures'], name)
        # What the text says of the others.
        self.assertEqual(self.by['interval_sub_1']['ensures'][0]['set'], 'x-y')
        self.assertEqual(self.by['interval_neg_1']['ensures'][0]['tight'], {'kind': 'exact'})
        self.assertEqual(self.by['ball_lower_as_2']['ensures'][1],
                         {'kind': 'error', 'of': 'l', 'form': 'A', 'c': '5', 'k': 1, 't': '3', 'when': None})
        self.assertEqual(self.by['ball_narrow_2_1']['ensures'][0]['finite_when'], [{'abs_le': 'abs(c)+r', 'exp': -2}])
        for name in ('add_up_2_2', 'sub_down_2_2', 'sub_up_2_2'):
            e = self.by[name]['ensures'][1]
            self.assertEqual((e['rel'], e['abs']), (ensures[0][1]['rel'], ensures[0][1]['abs']), name)
            self.assertEqual(e['exact_when'], [{'zero': self.by[name]['value']}], name)
        self.assertNotIn('exact_when', self.by['mul_dir_2_2']['ensures'][2])
        self.assertEqual(self.by['ball_from_interval_2']['ensures'],
                         [{'kind': 'makes_ball', 'center': 'cw', 'radius': 'rw', 'from': {'lower': 'lo', 'upper': 'hi'},
                           'midpoint_when': [{'half_in_format': 'lo'}, {'half_in_format': 'hi'}]}])
        self.assertNotIn('value', self.by['ball_from_interval_2'])

    def test_the_entries_of_stage_b1_in_architecture_md(self):
        # The entries that architecture.md writes out ("Claims of the interval kernels: two limbs and
        # the enclosure interface"), field for field and in order, the ensures of four more, and what
        # the text says of the others.
        with open(os.path.join(common.ROOT, 'docs', 'developer', 'architecture.md'), encoding='utf-8') as f:
            text = f.read()
        section = text.split('### Claims of the interval kernels: two limbs and the enclosure interface')[1] \
            .split('\n## ')[0]
        blocks = re.findall(r'```json\n(.*?)```', section, re.S)
        shown = json.loads('[' + blocks[0] + ']')
        self.assertEqual([e['name'] for e in shown], ['interval_hull_1', 'interval_mid_rad_1', 'ball_to_interval_1',
                                                     'interval_split_1', 'interval_make_2', 'mul_ext_2_2'])
        for e in shown:
            want = [(key, v) for key, v in self.by[e['name']].items()
                    if key not in ('source', 'flops', 'theorem', 'ieee_theorem')]
            self.assertEqual(list(e.items()), want, e['name'])
        ensures = json.loads('[' + blocks[1] + ']')
        names = ('interval_intersection_2', 'interval_to_ball_1', 'interval_neg_2', 'interval_mul_2')
        self.assertEqual(len(ensures), len(names))
        for name, e in zip(names, ensures):
            self.assertEqual(e, self.by[name]['ensures'], name)
        hull, inter = self.by['interval_hull_2']['ensures'], self.by['interval_intersection_1']['ensures']
        self.assertEqual(hull, [dict(self.by['interval_hull_1']['ensures'][0])])
        self.assertEqual(inter, [dict(self.by['interval_intersection_2']['ensures'][0])])
        sub, add = self.by['interval_sub_2']['ensures'][0], self.by['interval_add_2']['ensures'][0]
        self.assertEqual(sub, dict(add, set='x-y', tight=dict(add['tight'], exact_when={
            'lower': [{'zero': 'xl-yu'}], 'upper': [{'zero': 'xu-yl'}]}), bounded_when=[{'abs_le': 'x-y', 'exp': -2}]))
        mul = self.by['interval_mul_2']['ensures'][0]
        dirs = self.by['mul_dir_2_2']['ensures'][2]
        self.assertEqual((mul['tight']['rel'], mul['tight']['abs']), (dirs['rel'], dirs['abs']))
        for e in self.by['mul_ext_2_2']['ensures'][2:]:
            self.assertEqual((e['rel'], e['abs']), (dirs['rel'], dirs['abs']))

    def test_the_entries_of_stage_b2_in_architecture_md(self):
        # The entries that architecture.md writes out ("Claims of the enclosure interface: predicates
        # and comparisons"), field for field and in order, the ensures of six more, and what the text
        # says of the others.
        with open(os.path.join(common.ROOT, 'docs', 'developer', 'architecture.md'), encoding='utf-8') as f:
            text = f.read()
        section = text.split('### Claims of the enclosure interface: predicates and comparisons')[1] \
            .split('\n## ')[0].split('\n### ')[0]
        blocks = re.findall(r'```json\n(.*?)```', section, re.S)
        shown = json.loads('[' + blocks[0] + ']')
        self.assertEqual([e['name'] for e in shown], ['interval_contains_1', 'interval_less_2'])
        for e in shown:
            want = [(key, v) for key, v in self.by[e['name']].items()
                    if key not in ('source', 'flops', 'theorem', 'ieee_theorem')]
            self.assertEqual(list(e.items()), want, e['name'])
        ensures = json.loads('[' + blocks[1] + ']')
        names = ('interval_positive_1', 'interval_zero_1', 'interval_empty_2', 'interval_subset_1',
                 'interval_rel_interior_2', 'interval_equal_1')
        self.assertEqual(len(ensures), len(names))
        for name, e in zip(names, ensures):
            self.assertEqual(e, self.by[name]['ensures'], name)
        x = {'x': {'lower': 'xl', 'upper': 'xu'}}
        xy = dict(x, y={'lower': 'yl', 'upper': 'yu'})
        for k in (1, 2):
            self.assertEqual(self.by[f'interval_negative_{k}']['ensures'], [
                {'kind': 'certain', 'of': 'm', 'rel': 'lt', 'args': ['x', '0'], 'intervals': x, 'exact': True}])
            self.assertEqual(self.by[f'interval_entire_{k}']['ensures'], [
                {'kind': 'certain', 'of': 'm', 'rel': 'entire', 'args': ['x'], 'intervals': x, 'exact': True}])
            for name, rel in (('rel_equal', 'equal'), ('rel_disjoint', 'disjoint')):
                self.assertEqual(self.by[f'interval_{name}_{k}']['ensures'], [
                    {'kind': 'certain', 'of': 'm', 'rel': rel, 'args': ['x', 'y'], 'intervals': xy, 'exact': True}])
            self.assertEqual(self.by[f'interval_less_equal_{k}']['ensures'],
                             [dict(self.by['interval_less_2']['ensures'][0], rel='le')])
        for name in ('empty', 'entire', 'contains', 'subset', 'positive', 'negative', 'zero', 'less', 'less_equal',
                     'equal', 'rel_equal', 'rel_interior', 'rel_disjoint'):
            self.assertEqual(self.by[f'interval_{name}_2']['ensures'], self.by[f'interval_{name}_1']['ensures'], name)
        self.assertEqual(self.by['interval_contains_2']['requires'], ['interval(xl, xu)', 'canonical(t)'])
        # The predicates and comparisons of a ball: two entries in full, the ensures of four more.
        shown = json.loads('[' + blocks[2] + ']')
        self.assertEqual([e['name'] for e in shown], ['ball_less_1', 'ball_contains_point_2'])
        for e in shown:
            want = [(key, v) for key, v in self.by[e['name']].items()
                    if key not in ('source', 'flops', 'theorem', 'ieee_theorem')]
            self.assertEqual(list(e.items()), want, e['name'])
        ensures = json.loads('[' + blocks[3] + ']')
        names = ('ball_contains_point_1', 'ball_contains_ball_2', 'ball_positive_2', 'ball_equal_2')
        self.assertEqual(len(ensures), len(names))
        for name, e in zip(names, ensures):
            self.assertEqual(e, self.by[name]['ensures'], name)
        by = {n: self.by[n]['ensures'][0] for n in self.by if n.startswith('ball_')}
        self.assertEqual(by['ball_contains_ball_1'], dict(by['ball_contains_ball_2'], exact=True))
        b1 = {'x': {'center': 'c', 'radius': 'r'}}
        for k in (1, 2):
            self.assertEqual(by[f'ball_negative_{k}'], {'kind': 'certain', 'of': 'm', 'rel': 'lt', 'args': ['x', '0'],
                                                        'balls': b1, 'exact': True})
            self.assertEqual(by[f'ball_zero_{k}'], {'kind': 'certain', 'of': 'm', 'rel': 'eq', 'args': ['x', '0'],
                                                    'balls': b1, 'exact': True})
        self.assertEqual(by['ball_positive_1'], by['ball_positive_2'])
        for name, rel in (('ball_less_equal_1', 'le'), ('ball_equal_1', 'eq')):
            self.assertEqual(by[name], dict(by['ball_less_1'], rel=rel))
        for name, rel in (('ball_less_2', 'lt'), ('ball_less_equal_2', 'le')):
            self.assertEqual(by[name], dict(by['ball_equal_2'], rel=rel))

    def test_the_entries_of_the_set_operations_of_a_ball_in_architecture_md(self):
        # The entries that architecture.md writes out ("Claims of the enclosure interface: the set
        # operations of a ball"), field for field and in order, and what the text says of the others.
        with open(os.path.join(common.ROOT, 'docs', 'developer', 'architecture.md'), encoding='utf-8') as f:
            text = f.read()
        section = text.split('### Claims of the enclosure interface: the set operations of a ball')[1] \
            .split('\n## ')[0].split('\n### ')[0]
        blocks = re.findall(r'```json\n(.*?)```', section, re.S)
        shown = json.loads('[' + blocks[0] + ']')
        self.assertEqual([e['name'] for e in shown], ['ball_hull_1', 'ball_split_2'])
        for e in shown:
            want = [(key, v) for key, v in self.by[e['name']].items()
                    if key not in ('source', 'flops', 'theorem', 'ieee_theorem')]
            self.assertEqual(list(e.items()), want, e['name'])
        self.assertEqual(self.by['ball_intersection_1']['ensures'],
                         [dict(self.by['ball_hull_1']['ensures'][0], set='intersection')])
        self.assertEqual(self.by['ball_split_1']['ensures'], self.by['ball_split_2']['ensures'])
        self.assertEqual(self.by['ball_hull_2']['ensures'], self.by['ball_hull_1']['ensures'])
        self.assertEqual(self.by['ball_intersection_2']['ensures'], self.by['ball_intersection_1']['ensures'])
        self.assertEqual(self.by['ball_split_1']['min_precision'], 2)
        self.assertEqual([g['limbs'] for g in self.by['ball_split_1']['outputs']], [1, 1, 1, 1])

    def test_the_entries_of_the_conversions_of_two_limbs_in_architecture_md(self):
        # The entries that architecture.md writes out ("Claims of the enclosure interface: the
        # conversions of two limbs"), field for field and in order, and what the text says of the others.
        with open(os.path.join(common.ROOT, 'docs', 'developer', 'architecture.md'), encoding='utf-8') as f:
            text = f.read()
        section = text.split('### Claims of the enclosure interface: the conversions of two limbs')[1] \
            .split('\n## ')[0].split('\n### ')[0]
        blocks = re.findall(r'```json\n(.*?)```', section, re.S)
        shown = json.loads('[' + blocks[0] + ']')
        self.assertEqual([e['name'] for e in shown], ['interval_mid_rad_2', 'ball_from_interval_1'])
        for e in shown:
            want = [(key, v) for key, v in self.by[e['name']].items()
                    if key not in ('source', 'flops', 'theorem', 'ieee_theorem')]
            self.assertEqual(list(e.items()), want, e['name'])
        ensures = json.loads('[' + blocks[1] + ']')
        names = ('ball_to_interval_2', 'interval_to_ball_2')
        self.assertEqual(len(ensures), len(names))
        for name, e in zip(names, ensures):
            self.assertEqual(e, self.by[name]['ensures'], name)
        self.assertEqual(self.by['interval_split_2']['ensures'], self.by['interval_split_1']['ensures'])
        add = self.by['interval_add_2']['ensures'][0]['tight']
        conv = self.by['ball_to_interval_2']['ensures'][0]['tight']
        self.assertEqual((conv['rel'], conv['abs']), (add['rel'], add['abs']))

    def test_ieee_only(self):
        # Exactly the kernels without a real-model statement say so: the nine full kernels, the
        # ten full Ball kernels and the four constructors; ball_neg_k, which also requires a ball
        # and claims encloses, has a real-model statement and no such field.
        full = {f'{op}_full' for op in ('add_2_2', 'add_fast_2_2', 'sub_2_2', 'add_2_1', 'sub_2_1', 'sub_1_2',
                                        'mul_2_2', 'mul_2_1', 'mul_pow2_2')}
        full_ball = {f'ball_{op}_{k}_full' for op in ('add', 'sub', 'mul', 'scale', 'mul_pow2') for k in (1, 2)}
        constructors = {'make_2', 'make_2_limbs', 'ball_make_1', 'ball_make_2'}
        # and the finishes of the folds, which say what comes out when the state is not finite
        finishes = {'fold_finish_1', 'fold_finish_2', 'norm_finish_1', 'norm_finish_2'}
        # and the finish of the constructors of a BallVector (finite_or_nan with nonneg)
        finishes |= {'bv_make_finish'}
        # and the finish of the product of two BallVectors (finite_or_nan with if_all)
        finishes |= {'bv_conv_finish'}
        # Milestone 2: the interval kernels, stated in the IEEE model only (an interval has infinite
        # bounds as ordinary values), the constructors of an interval and of a ball from an interval,
        # the bounds of a ball as numbers of T and the narrowing of a ball.
        milestone2 = {'interval_make_1', 'interval_neg_1', 'interval_add_1', 'interval_sub_1', 'interval_mul_1',
                      'interval_add_2', 'ball_from_interval_2', 'ball_lower_as_1', 'ball_upper_as_1',
                      'ball_lower_as_2', 'ball_upper_as_2', 'ball_narrow_2_1'}
        # Stage B1: the interval kernels of two limbs, mul_ext_2_2 (a bound of two limbs over
        # extended reals), the set operations, the conversions and the split.
        milestone2 |= {'interval_neg_2', 'interval_sub_2', 'interval_make_2', 'mul_ext_2_2', 'interval_mul_2',
                       'interval_hull_1', 'interval_intersection_1', 'interval_hull_2', 'interval_intersection_2',
                       'interval_mid_rad_1', 'interval_to_ball_1', 'ball_to_interval_1', 'interval_split_1'}
        # Stage B2: the predicates and the three-valued comparisons of the enclosure interface.
        milestone2 |= {f'interval_{name}_{k}' for k in (1, 2) for name in (
            'empty', 'entire', 'contains', 'subset', 'positive', 'negative', 'zero', 'less', 'less_equal', 'equal',
            'rel_equal', 'rel_interior', 'rel_disjoint')}
        milestone2 |= {f'ball_{name}_{k}' for k in (1, 2) for name in (
            'contains_point', 'contains_ball', 'positive', 'negative', 'zero', 'less', 'less_equal', 'equal')}
        milestone2 |= {'ball_hull_1', 'ball_intersection_1', 'ball_split_1', 'ball_split_2'}
        milestone2 |= {'interval_mid_rad_2', 'interval_to_ball_2', 'ball_to_interval_2', 'interval_split_2',
                       'ball_from_interval_1', 'ball_hull_2', 'ball_intersection_2'}
        self.assertEqual({k['name'] for k in self.doc['kernels'] if 'ieee_only' in k},
                         full | full_ball | constructors | finishes | milestone2)
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


class FoldClaims(unittest.TestCase):
    """The folds' entries of gen/claims.json ("folds", architecture.md, "Claims of Milestone 2")."""

    KEYS = ['name', 'domain', 'arrays', 'outputs', 'value', 'requires', 'ensures', 'orders', 'packed_lanes',
            'step', 'combine', 'finish', 'min_precision', 'status', 'theorems', 'source', 'instances']

    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()
        cls.doc = json.loads(claims.claims(cls.ks))
        cls.by = {f['name']: f for f in cls.doc['folds']}

    def test_the_folds(self):
        maps = {name for name, fd in self.ks.folds.items() if fd.is_map}
        convs = {name for name, fd in self.ks.folds.items() if fd.is_conv}
        self.assertEqual(convs, {'conv_1', 'conv_2'})
        self.assertTrue(all(self.by[n]['conv'] is True and 'map' not in self.by[n] for n in convs))
        # The ball vectors (test_bv.py), with "bv": true.
        bvs = {name for name, fd in self.ks.folds.items() if fd.is_bv}
        self.assertEqual(bvs, {'bv_add_1', 'bv_add_2', 'bv_sub_1', 'bv_sub_2', 'bv_scale_1', 'bv_scale_2',
                               'bv_make_1', 'bv_make_2', 'bv_neg_1', 'bv_neg_2', 'bv_mul_pow2_1', 'bv_mul_pow2_2'})
        self.assertTrue(all(self.by[n]['bv'] is True and 'map' not in self.by[n] for n in bvs))
        # The products of two BallVectors (test_bv_conv.py), with "bv_conv": true.
        products = {name for name, fd in self.ks.folds.items() if fd.is_bv_conv}
        self.assertEqual(products, {'bv_conv_1', 'bv_conv_2'})
        self.assertTrue(all(self.by[n]['bv_conv'] is True and not ({'map', 'conv', 'bv'} & set(self.by[n]))
                            for n in products))
        self.assertEqual(set(self.by) - maps - convs - bvs - products, {'sum_1', 'sum_1_entry', 'sum_2', 'sum_2_entry', 'sum_fast_2',
                                                      'sum_fast_2_entry', 'dot_1', 'dot_1_entry', 'dot_2', 'norm_upper_1',
                                                      'norm_upper_2'})
        self.assertEqual(list(self.doc), ['schema', 'kernels', 'folds'])
        # Without folds the file has the shape it had: the test kernels have none.
        self.assertEqual(list(json.loads(claims.claims(common.kernels(common.TEST_KERNELS)))), ['schema', 'kernels'])

    def test_schema(self):
        for f in self.doc['folds']:
            if f.get('map') or f.get('conv') or f.get('bv') or f.get('bv_conv'):
                continue                # MapClaims; the convolutions, test_conv.py; the ball vectors, test_bv.py and test_bv_conv.py
            with self.subTest(fold=f['name']):
                self.assertEqual(list(f), self.KEYS)
                self.assertEqual(f['domain'], 'extended')
                for a in f['arrays']:
                    self.assertEqual(list(a), ['name', 'limbs', 'role'])
                    self.assertIn(a['role'], ('stored', 'supplied'))
                self.assertEqual(f['outputs'][-1], {'name': 'flag', 'limbs': 1, 'type': 'mask'})
                self.assertEqual(f['orders'], ['sequential', 'lanes'])
                self.assertEqual(f['packed_lanes'], {'binary64': {'avx2': 4, 'neon': 2},
                                                     'binary32': {'avx2': 8, 'neon': 4}})
                self.assertIn({'kind': 'finite_or_nan', 'of': f['outputs'][0]['name'], 'flag': 'flag'}, f['ensures'])
                uppers = [e for e in f['ensures'] if e['kind'] == 'upper']
                if uppers:
                    # A fold of maxima: one upper entry over the largest value, the result of one
                    # limb, no fold_error and no constants. Proved (FoldNorm.v).
                    self.assertEqual(f['theorems'], {
                        'sequential': {'file': 'proofs/theories/FoldNorm.v', 'name': f['name'] + '_seq_correct'},
                        'lanes': {'file': 'proofs/theories/FoldNorm.v', 'name': f['name'] + '_lanes_correct'}})
                    self.assertEqual(f['status'], 'proved')
                    self.assertEqual(f['ensures'], [{'kind': 'upper', 'of': 'r', 'over': 'max',
                                                     'steps': f['arrays'][0]['limbs'] - 1},
                                                    {'kind': 'finite_or_nan', 'of': 'r', 'flag': 'flag'}])
                    self.assertEqual(f['value'], f'abs({f["arrays"][0]["name"]})')
                    self.assertEqual(f['instances'], {'binary64': [], 'binary32': []})
                    continue
                errors = [e for e in f['ensures'] if e['kind'] == 'fold_error']
                self.assertEqual(len(errors), 1)
                e = errors[0]
                self.assertEqual(list(e), ['kind', 'of', 'eps', 'term', 'tau', 'heights'])
                self.assertEqual(set(e['heights']), set(f['orders']))
                for h in e['heights'].values():
                    self.assertEqual(list(h), ['rel', 'abs'])
                    self.assertTrue(set(h.values()) <= {'n', 'n-1'})
                self.assertIn({'kind': 'finite_or_nan', 'of': f['outputs'][0]['name'], 'flag': 'flag'}, f['ensures'])
                self.assertEqual(f['theorems'], {
                    'sequential': {'file': 'proofs/theories/FoldSums.v', 'name': f['name'] + '_seq_correct'},
                    'lanes': {'file': 'proofs/theories/FoldSums.v', 'name': f['name'] + '_lanes_correct'}})
                self.assertEqual(f['status'], 'proved')
                for fmt in ('binary64', 'binary32'):
                    self.assertEqual(len(f['instances'][fmt]), 1)
                    self.assertEqual(set(f['instances'][fmt][0]), {'eps', 'term', 'tau'})

    def test_the_example_of_architecture_md(self):
        f = self.by['dot_2']
        self.assertEqual(f['arrays'], [{'name': 'x', 'limbs': 2, 'role': 'supplied'},
                                       {'name': 'y', 'limbs': 2, 'role': 'supplied'}])
        self.assertEqual(f['outputs'], [{'name': 'r', 'limbs': 2}, {'name': 'flag', 'limbs': 1, 'type': 'mask'}])
        self.assertEqual(f['value'], 'x*y')
        self.assertEqual(f['requires'], ['canonical(x)', 'canonical(y)'])
        self.assertEqual(f['ensures'], [
            {'kind': 'normalized', 'of': 'r'},
            {'kind': 'fold_error', 'of': 'r', 'eps': '3*u^2/(1-4*u)', 'term': '4*u^2', 'tau': '3/2*eta',
             'heights': {'sequential': {'rel': 'n-1', 'abs': 'n-1'}, 'lanes': {'rel': 'n-1', 'abs': 'n-1'}}},
            {'kind': 'finite_or_nan', 'of': 'r', 'flag': 'flag'}])
        self.assertEqual((f['step'], f['combine'], f['finish']), ('dot_step_2', 'add_2_2', 'fold_finish_2'))
        self.assertEqual(f['min_precision'], 4)
        u = Fraction(1, 2 ** 53)
        inst = f['instances']['binary64'][0]
        self.assertEqual(Fraction(inst['eps']), 3 * u * u / (1 - 4 * u))
        self.assertEqual(Fraction(inst['term']), 4 * u * u)
        self.assertEqual(Fraction(inst['tau']), Fraction(3, 2) * Fraction(2) ** -1074)
        d1 = self.by['dot_1']
        self.assertEqual(d1['ensures'][0]['heights']['lanes'], {'rel': 'n', 'abs': 'n-1'})
        self.assertEqual(Fraction(d1['instances']['binary32'][0]['tau']), Fraction(2) ** -150)
        self.assertEqual(self.by['sum_2_entry']['arrays'][0]['role'], 'supplied')
        self.assertEqual(self.by['sum_2']['arrays'][0]['role'], 'stored')
        self.assertEqual(Fraction(self.by['sum_fast_2']['instances']['binary32'][0]['eps']), 3 * Fraction(1, 2 ** 24) ** 2)
        self.assertEqual(self.by['sum_1']['ensures'], [
            {'kind': 'fold_error', 'of': 'r', 'eps': 'u/(1+u)', 'term': '0', 'tau': '0',
             'heights': {'sequential': {'rel': 'n-1', 'abs': 'n-1'}, 'lanes': {'rel': 'n-1', 'abs': 'n-1'}}},
            {'kind': 'finite_or_nan', 'of': 'r', 'flag': 'flag'}])

    def test_the_maps(self):
        """The maps' entries (architecture.md, "Claims of Milestone 2", maps): the arrays read, the
        scalars, the array written, the mask; the step's claims entry by entry and finite_or_nan."""
        keys = ['name', 'map', 'domain', 'arrays', 'scalars', 'writes', 'outputs', 'value', 'requires', 'ensures',
                'orders', 'packed_lanes', 'step', 'step_args', 'check', 'min_precision', 'status', 'theorem',
                'source']
        maps = [f for f in self.doc['folds'] if f.get('map')]
        self.assertEqual(len(maps), 18)
        kernels = {k['name']: k for k in self.doc['kernels']}
        for f in maps:
            with self.subTest(map=f['name']):
                self.assertEqual(list(f), keys)
                self.assertIs(f['map'], True)
                self.assertEqual(f['domain'], 'extended')
                self.assertEqual(f['outputs'], [{'name': 'finite', 'limbs': 1, 'type': 'mask'}])
                self.assertEqual(len(f['writes']), 1)
                z = f['writes'][0]['name']
                self.assertEqual(f['ensures'], [{'kind': 'entries', 'of': z, 'kernel': f['step']},
                                                {'kind': 'finite_or_nan', 'of': z, 'flag': 'finite'}])
                step = kernels[f['step']]
                self.assertEqual(len(f['step_args']), len(step['inputs']))
                sizes = {g['name']: g['limbs'] for g in f['arrays'] + f['scalars']}
                self.assertEqual([sizes[a] for a in f['step_args']], [g['limbs'] for g in step['inputs']])
                self.assertEqual(step['outputs'][0]['limbs'], f['writes'][0]['limbs'])
                self.assertEqual(f['check'], f'fold_finish_{f["writes"][0]["limbs"]}')
                self.assertEqual(f['status'], 'proved')
                self.assertEqual(f['theorem'], {'file': 'proofs/theories/FoldMaps.v',
                                                'name': f['name'] + '_correct'})
        by = {f['name']: f for f in maps}
        a = by['axpy_2']
        self.assertEqual(a['arrays'], [{'name': 'x', 'limbs': 2, 'role': 'supplied'},
                                       {'name': 'y', 'limbs': 2, 'role': 'stored'}])
        self.assertEqual(a['scalars'], [{'name': 'a', 'limbs': 2, 'role': 'supplied'}])
        self.assertEqual(a['writes'], [{'name': 'z', 'limbs': 2}])
        self.assertEqual((a['value'], a['step'], a['step_args']), ('a*x+y', 'axpy_step_2', ['a', 'x', 'y']))
        self.assertEqual(a['requires'], ['canonical(a)', 'canonical(x)', 'canonical(y)'])
        self.assertEqual(by['mul_pow2_map_1']['requires'], ['power_of_two(c)'])
        self.assertEqual(by['axpy_2_entry']['arrays'][1]['role'], 'supplied')

    def test_the_bound_kernels(self):
        by = {k['name']: k for k in self.doc['kernels']}
        b = by['bound_sum_2']
        self.assertNotIn('value', b)
        self.assertEqual(b['requires'], ['count(m)', 'format(half)'])
        self.assertEqual(b['ensures'], [
            {'kind': 'holds', 'rel': 'le', 'args': ['m*unit(add_2_2)', '1/2'], 'if': 'ok'},
            {'kind': 'upper', 'of': 'g', 'value': 'm*unit(add_2_2)/(1-m*unit(add_2_2))', 'if': 'ok'}])
        self.assertEqual(by['bound_dot_1']['ensures'], [
            {'kind': 'holds', 'rel': 'le', 'args': ['m*unit(mul_1_1)', '1/2'], 'if': 'ok'},
            {'kind': 'upper', 'of': 'g', 'value': 'm*unit(mul_1_1)/(1-m*unit(mul_1_1))', 'if': 'ok'},
            {'kind': 'upper', 'of': 't', 'value': 'm*tiny(mul_1_1)*(1+g)', 'if': 'ok'}])
        self.assertEqual(by['dot_step_2']['ensures'][1]['form'], 'T')
        self.assertEqual(by['fold_finish_2']['ensures'], [{'kind': 'finite_or_nan', 'of': 'r', 'flag': 'flag'}])


if __name__ == '__main__':
    unittest.main()
