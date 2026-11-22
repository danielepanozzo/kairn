"""The kernels for the emulated limb type (emulated.py, tests/emulated/gen/kernels.hpp) are the
kernels of scalar.hpp, printed by the same printer: the emulated listing, with the type's name
replaced by double, is the double listing token for token, outside the literals (each a constant
of the format, which must be the same constant in the same place) and the test of constant
evaluation. And the comparison sees a printer that writes anything else."""
import re
import unittest
from fractions import Fraction

import common
from kairn_gen import build, consts, cpp, emulated

TOKEN = re.compile(r'''
    0[xX][0-9a-fA-F]*\.?[0-9a-fA-F]*[pP][+-]?[0-9]+[fF]?    # a hexadecimal floating literal
  | [0-9]+\.[0-9]*(?:[eE][+-]?[0-9]+)?[fF]?                  # a decimal one (0.0, 0.0f)
  | [0-9]+[uU]?                                              # an integer
  | [A-Za-z_][A-Za-z_0-9]*                                   # a name
  | "(?:[^"\\]|\\.)*"                                        # a string
  | ::|->|==|!=|>=|<=|&&|\|\||\+\+|--|<<|>>|\[\[|\]\]        # operators of two characters
  | [^\sA-Za-z_0-9]                                          # any other character
''', re.X)
FLOAT = re.compile(r'0[xX][0-9a-fA-F.]*[pP][+-]?[0-9]+[fF]?|[0-9]+\.[0-9]*[fF]?')


def code(text):
    """The text from the namespace of the kernels on, without comments and preprocessor lines (the
    header's comment and include say which type they are for)."""
    text = text[text.index('namespace kairn::gen {'):]
    text = text[:text.index('}  // namespace kairn::gen')]
    lines = [re.sub(r'//.*', '', line) for line in text.split('\n') if not line.lstrip().startswith('#')]
    return '\n'.join(lines)


def tokens(text):
    return TOKEN.findall(code(text))


def normalized_double(toks):
    """('LIT', value) for each literal, 'CE' for the test of constant evaluation, no constexpr."""
    out, i = [], 0
    while i < len(toks):
        t = toks[i]
        if t == '__builtin_is_constant_evaluated' and toks[i + 1:i + 3] == ['(', ')']:
            out.append('CE')
            i += 3
            continue
        if t == 'constexpr':
            i += 1
            continue
        if FLOAT.fullmatch(t):
            out.append(('LIT', Fraction(float.fromhex(t.rstrip('fF'))) if 'p' in t.lower() else Fraction(t.rstrip('fF'))))
        else:
            out.append(t)
        i += 1
    return out


def normalized_emulated(toks, names, fmt):
    """The same for the emulated listing: kairn::emulated::Number is double, constant(i) the value
    in `fmt` of the i-th constant (names), pow2(64) the value 2^64, constant_evaluation() CE."""
    out, i = [], 0
    while i < len(toks):
        t = toks[i]
        if toks[i:i + 5] == ['kairn', '::', 'emulated', '::', 'Number']:
            out.append('double')
            i += 5
            continue
        if toks[i:i + 4] == ['kairn', '::', 'emulated', '::'] and i + 5 < len(toks):
            what = toks[i + 4]
            if what == 'constant' and toks[i + 5] == '(' and toks[i + 7] == ')':
                out.append(('LIT', consts.value(names[int(toks[i + 6])], common.kernels(), *fmt)))
                i += 8
                continue
            if what == 'constant_evaluation' and toks[i + 5:i + 7] == ['(', ')']:
                out.append('CE')
                i += 7
                continue
            if what == 'pow2' and toks[i + 5:i + 8] == ['(', '64', ')']:
                out.append(('LIT', Fraction(2) ** 64))
                i += 8
                continue
        if t == 'constexpr':
            i += 1
            continue
        out.append(t)
        i += 1
    return out


def first_difference(a, b):
    """The index of the first token where the two lists differ, or None."""
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return None if len(a) == len(b) else min(len(a), len(b))


class Emission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()
        cls.double = cpp.scalar(cls.ks, types=('double',))
        cls.emulated = build.outputs(cls.ks)[emulated.PATH]
        cls.names = emulated.constant_names(cls.ks)

    def compare(self, emulated_text):
        a = normalized_double(tokens(self.double))
        b = normalized_emulated(tokens(emulated_text), self.names, cpp.FORMATS['double'])
        return a, b, first_difference(a, b)

    def test_the_emulated_listing_is_the_double_listing(self):
        a, b, i = self.compare(self.emulated)
        self.assertIsNone(i, None if i is None else 'the listings differ at token %d: %r against %r, after %r'
                          % (i, a[i:i + 8], b[i:i + 8], a[max(0, i - 12):i]))
        # Every kernel and fold is in it, each function once.
        for k in self.ks.values():
            self.assertEqual(len(re.findall(r'\bvoid %s\(' % k.name, code(self.emulated))), 1, k.name)
        for fd in self.ks.folds.values():
            self.assertIn('void %s_seq(' % fd.name, self.emulated)
        n = sum(1 for t in a if isinstance(t, tuple))
        self.assertGreater(n, 1000)

    def test_the_literals_are_the_constants_of_the_format(self):
        # At binary64 the constants of the emulated listing are the double listing's literals (the
        # comparison above, with fmt binary64); at float's format, the float listing's.
        flt = normalized_double(tokens(cpp.scalar(self.ks, types=('float',))))
        emu = normalized_emulated(tokens(self.emulated), self.names, cpp.FORMATS['float'])
        flt = ['double' if t == 'float' else t for t in flt]
        self.assertIsNone(first_difference(flt, emu))

    def test_a_different_listing_is_seen(self):
        # The arms of the first select swapped, a value inlined from the wrong call, a constant in
        # place of another, an operation of the fix-up moved before the branch: each is a difference.
        text = self.emulated
        m = re.search(r'= (\w+) \? (\w+) : (\w+);', text)
        swapped = text[:m.start()] + f'= {m.group(1)} ? {m.group(3)} : {m.group(2)};' + text[m.end():]
        self.assertIsNotNone(self.compare(swapped)[2])
        m = re.search(r'kairn::emulated::constant\((\d+)\)', text[text.index('namespace kairn::gen {'):])
        i = int(m.group(1))
        other = text.replace(f'kairn::emulated::constant({i})', f'kairn::emulated::constant({i + 1})', 1)
        self.assertIsNotNone(self.compare(other)[2])
        m = re.search(r'const kairn::emulated::Number (\w+)_(\w+) = (\w+) \+ (\w+);', text)
        renamed = text[:m.start()] + m.group(0).replace(f'= {m.group(3)} +', f'= {m.group(4)} +') + text[m.end():]
        self.assertIsNotNone(self.compare(renamed)[2])
        self.assertIsNotNone(self.compare(text.replace('[[likely]] {', '[[likely]] { ;', 1))[2])

    def test_the_formats(self):
        # binary64 and binary32, then formats of the statements of precision 8 to 11, and every
        # constant of every kernel a number of each (header() refuses a format where one is not).
        fs = emulated.formats()
        self.assertEqual([f[0] for f in fs[:2]], ['binary64', 'binary32'])
        for name, p, qmin, qmax in fs[2:]:
            self.assertTrue(8 <= p <= 11 and qmax >= 1 and qmin == 3 - qmax - 2 * p, name)
            self.assertEqual(name, f'fp:{p}:{qmin}:{qmax}')
        self.assertIn('fp:8:-14:1', [f[0] for f in fs])
        self.assertEqual(self.names[0], '0')
        for n in self.names:
            self.assertIn(f'"{n}"', self.emulated)

    def test_a_constant_that_is_not_a_number_of_a_format_is_refused(self):
        saved = emulated.QMAX
        try:
            emulated.QMAX = (-3,)        # fp:8:-10:-3: no 1, and no format of the statements
            with self.assertRaises(cpp.PrintError):
                emulated.header(self.ks)
        finally:
            emulated.QMAX = saved


if __name__ == '__main__':
    unittest.main()
