"""include/kairn/gen/bounds.hpp and selftest.hpp: what the public headers read from the generator.

The constants of bounds.hpp are checked here against exact rational arithmetic, independently of
how library.py rounds them: each printed literal must be a number of its format, at least the exact
value, and its predecessor in the format (found by stepping the bit pattern) must be below it.
"""
import copy
import json
import math
import os
import re
import struct
import subprocess
import unittest
from fractions import Fraction

import common
import test_cxx
from kairn_gen import consts, expr, interp, ir, library

TYPES = {'double': ('binary64', 53, -1074), 'float': ('binary32', 24, -149)}


def structs(text):
    """{(kernel, type): body} of the specializations in bounds.hpp, the body as one string."""
    out = {}
    for m in re.finditer(r'^template <> struct (\w+)<(double|float)> \{(.*?)\};', text, re.M | re.S):
        out[(m.group(1), m.group(2))] = m.group(3)
    return out


def members(body):
    return dict(re.findall(r'static constexpr (?:double|float|bool|Form) (\w+) = ([^;]+);', body))


def literal_value(text, ctype):
    """The exact value of a printed literal, which must be a number of the limb type."""
    if ctype == 'float':
        if not text.endswith('f'):
            raise AssertionError(f'{text} is not a float literal')
        text = text[:-1]
    v = float.fromhex(text) if text.startswith(('0x', '-0x')) else float(text)
    if ctype == 'float' and struct.unpack('<f', struct.pack('<f', v))[0] != v:
        raise AssertionError(f'{text} is not a binary32 number')
    return v


def pred(v, ctype):
    """The next number of the format below v > 0, by stepping the bit pattern."""
    if ctype == 'double':
        bits = struct.unpack('<Q', struct.pack('<d', v))[0]
        return struct.unpack('<d', struct.pack('<Q', bits - 1))[0]
    bits = struct.unpack('<I', struct.pack('<f', v))[0]
    return struct.unpack('<f', struct.pack('<I', bits - 1))[0]


def exact(entry, ctype):
    """unit, tiny, unit/(1 - unit), tiny/(1 - unit) of an error entry, as exact fractions."""
    _, p, qmin = TYPES[ctype]
    u = Fraction(1, 2 ** p)
    unit = expr.evaluate(expr.parse(entry['c']), {'u': u}) * u ** entry['k']
    tiny = expr.evaluate(expr.parse(entry['t']), {}) * Fraction(2) ** qmin
    return {'unit': unit, 'tiny': tiny, 'unit_computed': unit / (1 - unit),
            'tiny_computed': tiny / (1 - unit)}


class Bounds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()
        cls.text = library.bounds(cls.ks)
        cls.structs = structs(cls.text)
        with open(os.path.join(common.GEN, 'claims.json'), encoding='utf-8') as f:
            cls.claims = {k['name']: k for k in json.load(f)['kernels']}

    def test_every_kernel_and_type(self):
        self.assertEqual(set(self.structs), {(k, t) for k in self.ks for t in TYPES})
        for name in self.ks:
            self.assertIn(f'template <class T> struct {name};', self.text)

    def test_status_comes_from_the_claims(self):
        for (name, t), body in self.structs.items():
            c = self.claims[name]
            proved = c['status'] == 'proved' and (c['min_precision'] is None or
                                                  c['min_precision'] <= TYPES[t][1])
            self.assertEqual(members(body)['proved'], 'true' if proved else 'false', (name, t))

    def test_unverified_kernels_have_no_constants(self):
        for (name, t), body in self.structs.items():
            if self.claims[name]['status'] != 'proved':
                self.assertEqual(body.strip(), 'static constexpr bool proved = false;', (name, t))
        # Whatever the claims say today, a kernel made unverified loses its constants.
        ks = copy.deepcopy(dict(self.ks))
        ks['mul_2_2'].status = 'unverified'
        ks['mul_2_2'].theorem = None
        self.assertEqual(members(structs(library.bounds(ks))[('mul_2_2', 'double')]), {'proved': 'false'})

    def test_constants_against_exact_arithmetic(self):
        checked = 0
        for (name, t), body in self.structs.items():
            m = members(body)
            if m['proved'] != 'true':
                continue
            entries = [e for e in self.claims[name]['ensures'] if e['kind'] == 'error' and e['when'] is None]
            if not entries:
                self.assertEqual(set(m), {'proved'}, name)
                continue
            self.assertEqual(len(entries), 1, name)
            e = entries[0]
            self.assertEqual(m['form'], 'Form::result' if e['form'] == 'R' else 'Form::operands', name)
            want = exact(e, t)
            names = ['unit', 'tiny'] + (['unit_computed', 'tiny_computed'] if e['form'] == 'R' else [])
            self.assertEqual(set(m), {'proved', 'form'} | set(names), name)
            for c in names:
                v = literal_value(m[c], t)
                x = want[c]
                self.assertGreaterEqual(Fraction(v), x, (name, t, c))
                if x == 0:
                    self.assertEqual(v, 0.0, (name, t, c))
                else:
                    self.assertLess(Fraction(pred(v, t)), x, (name, t, c, 'not the smallest'))
                checked += 1
        # At least the four first-wave arithmetic kernels, for both types and four constants.
        self.assertGreaterEqual(checked, 4 * 2 * 4)

    def test_known_values(self):
        # 3u^2/(1 - 4u) with u = 2^-53 is 3 2^-106 (1 + 4u + ...): rounded up, 1.5 (1 + 2^-50) 2^-105.
        add = members(self.structs[('add_2_2', 'double')])
        self.assertEqual(add['unit'], '0x1.8000000000004p-105')
        # 3/2 eta rounds up to 2 eta, the next number of the format.
        mul = members(self.structs[('mul_2_2', 'double')])
        self.assertEqual((mul['unit'], mul['tiny']), ('0x1p-104', '0x1p-1073'))
        self.assertEqual(members(self.structs[('mul_2_1', 'float')])['tiny_computed'], '0x1p-148f')
        # two_prod: only its unconditional claim (|p + e - ab| <= eta/2) is exported.
        self.assertEqual(members(self.structs[('two_prod', 'double')])['tiny'], '0x1p-1074')

    def test_the_ball_kernels_use_the_same_constants(self):
        for name in ('add_2_2', 'mul_2_2', 'mul_2_1'):
            for t in TYPES:
                m = members(self.structs[(name, t)])
                for c in ('unit_computed', 'tiny_computed'):
                    v = consts.value(f'{c}({name})', self.ks, *common.FORMATS[TYPES[t][0]])
                    self.assertEqual(Fraction(literal_value(m[c], t)), v, (name, t, c))

    def test_a_proof_landing_exports_its_constants(self):
        ks = copy.deepcopy(dict(self.ks))
        ks['sub_2_2'].status = 'proved'
        ks['sub_2_2'].theorem = ('proofs/theories/Sub22.v', 'sub_2_2_correct')
        s = structs(library.bounds(ks))
        self.assertEqual(members(s[('sub_2_2', 'double')]), members(self.structs[('add_2_2', 'double')]))

    def test_minimum_precision_above_the_type(self):
        ks = copy.deepcopy(dict(self.ks))
        ks['mul_2_2'].min_precision = 30
        s = structs(library.bounds(ks))
        self.assertEqual(members(s[('mul_2_2', 'float')]), {'proved': 'false'})
        self.assertEqual(members(s[('mul_2_2', 'double')])['proved'], 'true')

    def test_form_operands_has_no_computed_constants(self):
        ks = copy.deepcopy(dict(self.ks))
        ks['add_fast_2_2'].status = 'proved'
        ks['add_fast_2_2'].theorem = ('proofs/theories/AddFast22.v', 'add_fast_2_2_correct')
        m = members(structs(library.bounds(ks))[('add_fast_2_2', 'double')])
        self.assertEqual(m['form'], 'Form::operands')
        self.assertEqual(set(m), {'proved', 'form', 'unit', 'tiny'})

    def test_refusals(self):
        ks = copy.deepcopy(dict(self.ks))
        e = dict(ks['add_2_2'].ensures[1])
        ks['add_2_2'].ensures = list(ks['add_2_2'].ensures) + [dict(e, c='4')]
        with self.assertRaisesRegex(library.LibraryError, 'add_2_2 has 2 error claims without a condition'):
            library.bounds(ks)


def parse_selftest(text):
    """{function: (kernel, type, inputs, expected outputs)} of selftest.hpp, values as text."""
    out = {}
    for m in re.finditer(r'^inline const char\* (\w+)_(double|float)\(\) noexcept \{\n(.*?)^\}', text, re.M | re.S):
        body = m.group(3)
        ins = re.findall(r'volatile (?:double|float|bool) i\d+ = ([^;]+);', body)
        call = re.search(r'    (\w+)\((.*)\);', body)
        outs = re.findall(r'!same\(o\d+, ((?:[^()]|\(\))+)\)', body)
        out[f'{m.group(1)}_{m.group(2)}'] = (call.group(1), m.group(2), ins, outs)
    return out


def to_value(text, ctype):
    if text in ('true', 'false'):
        return text == 'true'
    special = re.fullmatch(rf'(-?)std::numeric_limits<{ctype}>::(infinity|quiet_NaN)\(\)', text)
    if special:
        return (interp.INF, special.group(1) == '-') if special.group(2) == 'infinity' else interp.NaN
    if ctype == 'float':
        text = text[:-1]
    return interp.parse_limb('0x0p+0' if text == '0.0' else text)


class Selftest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()
        cls.text = library.selftest(cls.ks)
        cls.cases = parse_selftest(cls.text)

    def test_every_kernel_and_type(self):
        self.assertEqual({(k, t) for k, t, _, _ in self.cases.values()}, {(k, t) for k in self.ks for t in TYPES})
        listed = re.findall(r'^        (\w+),$', self.text, re.M)
        self.assertEqual(sorted(listed), sorted(self.cases))

    def test_operands_and_results(self):
        """Every case satisfies its kernel's requirements, and its stored outputs are what the
        interpreter computes (which also checks that the literals are printed exactly)."""
        machine = interp.Machine(self.ks)
        nonfinite = set()
        for fn, (name, t, ins, outs) in self.cases.items():
            k = self.ks[name]
            f = interp.parse_format(TYPES[t][0])
            vals = [to_value(x, t) for x in ins]
            got = machine.run(name, f, vals)
            self.assertEqual([to_value(x, t) for x in outs], got, fn)
            if '_nonfinite_' in fn:
                # The second case of a full kernel or a constructor: its first operand is +inf in
                # double and NaN in float, in canonical form, and so is some output limb.
                self.assertFalse(k.real_model, fn)
                special = (interp.INF, False) if t == 'double' else interp.NaN
                if any(r[0] == 'interval' and r[1] == k.inputs[0].name for r in k.requires):
                    # An interval operand has no NaN bound: the whole line (-inf, +inf) in double and
                    # the empty set (+inf, -inf) in float, both with a bound +inf.
                    special = (interp.INF, False)
                self.assertIn(special, vals, fn)
                self.assertTrue(any(not isinstance(v, bool) and v[0] != interp.NUM for v in got), fn)
                nonfinite.add(name)
                continue
            for v in vals:
                self.assertTrue(isinstance(v, bool) or (v[0] == interp.NUM and interp.member(f, v)), fn)
            env = dict(zip(k.input_limbs, vals))
            g = {g.name: g for g in k.inputs}
            for r in k.requires:
                if r[0] in ('normalized', 'canonical'):
                    limbs = [env[x] for x in g[r[1]].limbs]
                    for a, b in zip(limbs, limbs[1:]):
                        self.assertEqual(interp.add(f, a, b), a, (fn, r))
                elif r[0] == 'nonneg':
                    self.assertFalse(env[r[1]][1], (fn, r))
                elif r[0] == 'ball':
                    for a, b in zip(g[r[1]].limbs, g[r[1]].limbs[1:]):
                        self.assertEqual(interp.add(f, env[a], env[b]), env[a], (fn, r))
                    self.assertFalse(env[r[2]][1], (fn, r))
                elif r[0] == 'power_of_two':
                    self.assertEqual(env[r[1]][2], 1, (fn, r))
                    self.assertFalse(env[r[1]][1], (fn, r))
                elif r[0] == 'abs_ge':
                    self.assertTrue(interp.le(interp.absolute(env[r[2]]), interp.absolute(env[r[1]])), (fn, r))
                elif r[0] == 'interval':
                    # Bounds of a nonempty bounded interval: each normalized, the lower one first.
                    lo, hi = ([env[x] for x in g[n].limbs] for n in r[1:])
                    for limbs in (lo, hi):
                        for a, b in zip(limbs, limbs[1:]):
                            self.assertEqual(interp.add(f, a, b), a, (fn, r))
                    # Normalized values are ordered by their leading limbs, then by the next ones.
                    self.assertTrue(interp.lt(lo[0], hi[0]) or (interp.eq(lo[0], hi[0]) and
                                                                 all(interp.le(a, b) for a, b in zip(lo[1:], hi[1:]))),
                                    (fn, r))
                elif r[0] == 'not_nan':
                    self.assertNotEqual(env[r[1]], interp.NaN, (fn, r))
                else:
                    self.fail((fn, r))
            # Something to check: no case where every limb output is zero.
            self.assertTrue(any(v is True or (not isinstance(v, bool) and v[2] != 0) for v in got) or
                            all(isinstance(v, bool) for v in got), fn)
        # Every full kernel and constructor has its non-finite case, for both types.
        self.assertEqual(nonfinite, {n for n, k in self.ks.items() if not k.real_model})
        self.assertEqual(sum('_nonfinite_' in fn for fn in self.cases), 2 * len(nonfinite))

    def test_deterministic(self):
        self.assertEqual(library.selftest(copy.deepcopy(dict(self.ks))), self.text)


PROGRAM = r'''
#include <cstdio>
#include "kairn/gen/bounds.hpp"
#include "kairn/gen/selftest.hpp"
namespace b = kairn::gen::bounds;
template <class K> concept has_unit = requires { K::unit; };
static_assert(b::add_2_2<double>::form == b::Form::result);
static_assert(b::add_2_2<double>::unit == 0x1.8000000000004p-105);
static_assert(b::mul_2_2<double>::tiny == 0x1p-1073 && b::mul_2_2<float>::tiny_computed == 0x1p-148f);
@STATUS@
int main() {
    const char* failed = kairn::gen::selftest::run();
    std::printf("%s\n", failed ? failed : "ok");
    return failed ? 1 : 0;
}
'''


def status_asserts(ks):
    """static_asserts that every kernel is proved, and has constants, exactly as its claims say."""
    lines = []
    for k in ks.values():
        for t in TYPES:
            proved = library.proved_for(k, t)
            has = proved and library.error_entry(k) is not None
            lines.append(f'static_assert(b::{k.name}<{t}>::proved == {str(proved).lower()} && '
                         f'has_unit<b::{k.name}<{t}>> == {str(has).lower()});')
    return '\n'.join(lines)


class Cxx(unittest.TestCase):
    """The two headers compiled with each compiler: the static_asserts hold, every stored result
    matches the compiled kernels, and a stored result off by one unit in the last place is caught."""
    FLAGS = [['-O0', '-ffp-contract=off'], ['-O2', '-ffp-contract=fast'], ['-O2', '-ffp-contract=on', '-frounding-math']]

    @classmethod
    def setUpClass(cls):
        if not test_cxx.COMPILERS:
            raise unittest.SkipTest('no C++ compiler (set KAIRN_GEN_CXX)')
        cls.dir = common.scratch('library')
        inc = os.path.join(cls.dir, 'include', 'kairn', 'gen')
        os.makedirs(inc)
        ks = common.kernels()
        texts = {'bounds.hpp': library.bounds(ks), 'selftest.hpp': library.selftest(ks)}
        for name in ('prelude.hpp', 'scalar.hpp'):
            with open(os.path.join(test_cxx.INCLUDE, 'kairn', 'gen', name), encoding='utf-8') as f:
                texts[name] = f.read()
        for name, text in texts.items():
            with open(os.path.join(inc, name), 'w', encoding='utf-8') as f:
                f.write(text)
        # The same headers with one stored output of mul_2_2 (float) one unit in the last place off.
        bad = os.path.join(cls.dir, 'bad', 'kairn', 'gen')
        os.makedirs(bad)
        m = re.search(r'(inline const char\* mul_2_2_float\(\) noexcept \{.*?!same\(o0, )([^)]+)\)',
                      texts['selftest.hpp'], re.S)
        v = float.fromhex(m.group(2)[:-1])
        bits = struct.unpack('<I', struct.pack('<f', abs(v)))[0]
        off = math.copysign(struct.unpack('<f', struct.pack('<I', bits + 1))[0], v)
        doctored = texts['selftest.hpp'][:m.start(2)] + off.hex() + 'f' + texts['selftest.hpp'][m.end(2):]
        for name, text in dict(texts, **{'selftest.hpp': doctored}).items():
            with open(os.path.join(bad, name), 'w', encoding='utf-8') as f:
                f.write(text)
        cls.source = os.path.join(cls.dir, 'program.cpp')
        with open(cls.source, 'w', encoding='utf-8') as f:
            f.write(PROGRAM.replace('@STATUS@', status_asserts(ks)))

    def build(self, cxx, flags, include):
        exe = os.path.join(self.dir, f'p{abs(hash((cxx, tuple(flags), include)))}')
        status, err = test_cxx.compile_([cxx] + test_cxx.BASE + flags + ['-I', include, self.source, '-o', exe])
        self.assertEqual(status, 0, err)
        return subprocess.run([exe], capture_output=True, text=True)

    def test_compiled(self):
        for cxx in test_cxx.COMPILERS:
            for flags in self.FLAGS:
                with self.subTest(compiler=cxx, flags=flags):
                    r = self.build(cxx, flags, os.path.join(self.dir, 'include'))
                    self.assertEqual((r.returncode, r.stdout), (0, 'ok\n'), r.stderr)

    def test_a_wrong_stored_result_is_caught(self):
        for cxx in test_cxx.COMPILERS:
            r = self.build(cxx, ['-O2'], os.path.join(self.dir, 'bad'))
            self.assertEqual((r.returncode, r.stdout), (1, 'mul_2_2 (float)\n'), cxx)


if __name__ == '__main__':
    unittest.main()
