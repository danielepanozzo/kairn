"""The two printers: what their text says, read independently of how they produce it."""
import copy
import re
import unittest

import common
from kairn_gen import cpp, ir, rocq

# The Phase 0 tracer's model of these three kernels, which Rocq 9.0.1 with Flocq 4.2.2 accepted
# (experiments/phase0/tracer/gen.py).
TRACER = {
    'two_sum': '''Definition two_sum (a b : R) : R * R :=
  let s := rnd (a + b) in
  let bb := rnd (s - a) in
  let t0 := rnd (s - bb) in
  let t1 := rnd (a - t0) in
  let t2 := rnd (b - bb) in
  let e := rnd (t1 + t2) in
  (s, e).''',
    'fast_two_sum': '''Definition fast_two_sum (a b : R) : R * R :=
  let s := rnd (a + b) in
  let z := rnd (s - a) in
  let e := rnd (b - z) in
  (s, e).''',
    'two_prod': '''Definition two_prod (a b : R) : R * R :=
  let p := rnd (a * b + 0) in
  let e := rnd (a * b + - p) in
  (p, e).''',
}
TRACER_PREAMBLE = '''From Stdlib Require Import Reals ZArith.
From Flocq Require Import Core.
Open Scope R_scope.

Section Kernels.
Variable emin prec : Z.
Variable choice : Z -> bool.
Notation rnd := (round radix2 (FLT_exp emin prec) (Znearest choice)).'''


def functions(text):
    """{(name, limb type): body lines} of a generated header."""
    out, current = {}, None
    for line in text.splitlines():
        m = re.match(r'KAIRN_GEN_FORCEINLINE (constexpr )?void (\w+)\((double|float) ', line) or \
            re.match(r'inline (constexpr )?void (\w+)\((double|float) ', line)
        if m:
            current = out.setdefault((m.group(2), m.group(3)), {'constexpr': bool(m.group(1)), 'lines': [],
                                                                 'head': line})
        elif line == '}':
            current = None
        elif current is not None:
            current['lines'].append(line)
    return out


ATOM = r'(?:[a-z][a-z0-9_]*|0x1(?:\.[0-9a-f]+)?p\+[0-9]+f?|0\.0f?)'
# One operation, written over atoms: what "one operation per statement" allows.
ONE_OPERATION = re.compile(
    rf'(?:-{ATOM}|!{ATOM}|{ATOM} (?:[-+*<&|]|<=|==) {ATOM}|{ATOM} \? {ATOM} : {ATOM}|'
    rf'fma_rn\(-?{ATOM}, {ATOM}, -?{ATOM}\)|(?:abs_bits|next_up|next_down)\({ATOM}\)|'
    rf'{ATOM} \* {ATOM} \+ {ATOM})')


class Cpp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()
        cls.text = cpp.scalar(cls.ks)
        cls.fns = functions(cls.text)
        cls.tks = common.kernels(common.TEST_KERNELS)
        cls.tfns = functions(cpp.scalar(cls.tks))

    def run_time(self, lines):
        """The statements after the constant-evaluation branch, if any."""
        if '    if (__builtin_is_constant_evaluated()) {' in lines:
            lines = lines[lines.index('    }') + 1:]
        return lines

    def test_every_kernel_twice(self):
        self.assertEqual(set(self.fns), {(k, t) for k in self.ks for t in ('double', 'float')})

    def test_one_operation_per_statement(self):
        for fns, ks in ((self.fns, self.ks), (self.tfns, self.tks)):
            for (name, t), f in fns.items():
                for line in f['lines']:
                    m = re.fullmatch(rf'\s+const (?:{t}|bool) ([a-z0-9_]+) = (.*);', line)
                    if m:
                        self.assertRegex(m.group(2), rf'\A{ONE_OPERATION.pattern}\Z', (name, line))
                    elif not re.fullmatch(r'\s+(//.*|[a-z0-9_]+_out = [a-z0-9_]+;|return;|}|if \(__builtin_is_constant_evaluated\(\)\) \{)', line):
                        self.fail((name, line))

    def test_no_plain_product_at_run_time(self):
        # R1 on the printed text: outside constant evaluation nothing is multiplied except in a
        # muladd, and every product is an fma_rn whose count is the IR's.
        for fns, ks in ((self.fns, self.ks), (self.tfns, self.tks)):
            for (name, t), f in fns.items():
                body = self.run_time(f['lines'])
                prims = ir.prims(ks[name], ks)
                stars = sum(line.count(' * ') for line in body if not line.strip().startswith('//'))
                self.assertEqual(stars, sum(p.op == 'muladd' for p in prims), name)
                fmas = sum(line.count('fma_rn(') for line in body)
                self.assertEqual(fmas, sum(p.op in ir.FUSED for p in prims), name)
                zero = '0.0f' if t == 'float' else '0.0'
                prods = sum(bool(re.search(rf', {re.escape(zero)}\);$', line)) for line in body)
                self.assertEqual(prods, sum(p.op == 'prod' for p in prims), name)

    def test_constant_evaluation_branch(self):
        for t in ('double', 'float'):
            f = self.fns[('two_prod', t)]
            self.assertTrue(f['constexpr'])
            lines = f['lines']
            self.assertEqual(lines[0], '    if (__builtin_is_constant_evaluated()) {')
            ce = lines[1:lines.index('    }')]
            self.assertFalse(any('fma_rn' in line for line in ce))
            dekker = ir.prims(self.ks['two_prod_dekker'], self.ks)
            self.assertEqual(sum(' * ' in line for line in ce), sum(p.op == 'prod' for p in dekker))
            self.assertEqual(sum(' * ' in line for line in ce), 7)
            splitter = '0x1.0000002p+27' if t == 'double' else '0x1.001p+12f'
            self.assertIn(f'        const {t} ah_g = {splitter} * a;', ce)
            self.assertEqual(ce[-3:], ['        p_out = p;', '        e_out = e;', '        return;'])

    def test_constexpr(self):
        plain = {name for (name, _), f in self.fns.items() if not f['constexpr']}
        self.assertEqual(plain, {'mul_2_2', 'mul_2_1', 'split', 'two_prod_dekker'})
        line = [x for x in self.text.splitlines() if x.startswith('// Not constexpr: ')]
        self.assertEqual(sorted(line[0][len('// Not constexpr: '):-1].split(', ')),
                         ['mul_2_1', 'mul_2_2', 'split', 'two_prod_dekker'])
        self.assertTrue(all(f['head'].startswith('KAIRN_GEN_FORCEINLINE') for f in self.fns.values()))

    def test_inlined_names(self):
        add = self.fns[('add_2_2', 'double')]['lines']
        for line in ('    // (sh, sl) = two_sum(x0, y0)', '    const double sh_bb = sh - x0;',
                     '    const double vh_z = vh - sh;', '    const double z1 = w - z0_z;',
                     '    z0_out = z0;'):
            self.assertIn(line, add)

    def test_name_clash_is_refused(self):
        ks = copy.deepcopy(dict(self.ks))
        k = ks['fast_two_sum']
        k.body = [ir.Stmt(('s',), 'add', (ir.Operand('a'), ir.Operand('b')), 1),
                  ir.Stmt(('out',), 'sub', (ir.Operand('s'), ir.Operand('a')), 2),
                  ir.Stmt(('e',), 'sub', (ir.Operand('b'), ir.Operand('out')), 3)]
        with self.assertRaises(cpp.PrintError):
            cpp.function(ks['add_2_1'], ks, 'double')    # z0_out is the inlined `out` and an output


class Rocq(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()
        cls.model = rocq.model(cls.ks)
        cls.statements = rocq.statements(cls.ks)

    def test_the_tracer_model(self):
        self.assertIn(TRACER_PREAMBLE, self.model)
        for text in TRACER.values():
            self.assertIn(text, self.model)

    def test_one_let_per_statement_and_calls_kept(self):
        for name, k in self.ks.items():
            block = self.model.split(f'Definition {name} ')[1].split('.\n')[0]
            lets = [line for line in block.splitlines() if line.startswith('  let ')]
            self.assertEqual(len(lets), len(k.body), name)
            for st, line in zip(k.body, lets):
                if st.is_call:
                    self.assertTrue(line.startswith(f"  let '({', '.join(st.dsts)}) := {st.op} "), line)
                else:
                    self.assertTrue(line.startswith(f'  let {st.dsts[0]} := '), line)
        self.assertIn("  let '(ah, al) := split a in", self.model)
        self.assertIn('Definition splitter : R := bpow radix2 (Z.div (prec + 1) 2) + 1.', self.model)

    def test_statements(self):
        s = self.statements
        self.assertIn('From Kairn.Gen Require Import Model.', s)
        self.assertIn('Definition tie_even (n : Z) : bool := negb (Z.even n).', s)
        self.assertIn('''Definition two_sum_spec : Prop :=
  forall emin prec : Z, (2 <= prec)%Z ->
  forall a b : R,
  fmt emin prec a ->
  fmt emin prec b ->
  let '(s, e) := two_sum emin prec tie_even a b in
  s = RN emin prec (a + b) /\\
  (s + e) = (a + b).''', s)
        self.assertIn('  Rabs b <= Rabs a ->\n', s)
        self.assertIn('  (((a * b) = 0 \\/ bpow radix2 (2 * prec - 1) * eta emin <= Rabs (a * b)) -> (p + e) = (a * b)).', s)
        self.assertIn('  Rabs ((z0 + z1) - ((x0 + x1) + (y0 + y1))) <= (3 / (1 - (4 * u prec))) * u prec ^ 2 * '
                      'Rabs ((x0 + x1) + (y0 + y1)).', s)
        self.assertIn('<= 4 * u prec ^ 2 * (Rabs (x0 + x1) + Rabs (y0 + y1)).', s)
        self.assertIn('<= 4 * u prec ^ 2 * Rabs ((x0 + x1) * (y0 + y1)) + 4 * eta emin.', s)
        self.assertEqual(s.count('_spec : Prop :='), len(self.ks))

    def test_muladd_choices(self):
        tks = common.kernels(common.TEST_KERNELS)
        model = rocq.model(tks)
        self.assertIn('Definition ops_muladd (fuse_t : bool) (a b c : R) : R * R :=', model)
        self.assertIn('  let t := if fuse_t then rnd (a * b + c) else rnd (rnd (a * b) + c) in', model)
        self.assertIn('Definition ops_call (fuse_u0_t : bool) (x0 x1 a : R) : R * R :=', model)
        self.assertIn("  let '(u0, u1) := ops_muladd fuse_u0_t x0 x1 a in", model)
        self.assertIn('  let v := ops_one u0 u1 in', model)
        st = rocq.statements(tks)
        self.assertIn('  forall fuse_u0_t : bool,\n', st)
        self.assertIn('ops_call emin prec tie_even fuse_u0_t x0 x1 a in', st)

    def test_audit(self):
        self.assertIn('(* No kernel is verified yet. *)', rocq.audit(self.ks))
        ks = copy.deepcopy(dict(self.ks))
        ks['mul_2_2'].status = 'proved'
        ks['add_2_2'].status = 'proved'
        audit = rocq.audit(ks)
        self.assertIn('From Kairn Require Import Add22.\nFrom Kairn Require Import Mul22.', audit)
        self.assertIn('Definition mul_2_2_audit : mul_2_2_spec := mul_2_2_correct.\n'
                      'Print Assumptions mul_2_2_correct.', audit)
        self.assertNotIn('Check', audit)       # the audit prints nothing but assumptions


if __name__ == '__main__':
    unittest.main()
