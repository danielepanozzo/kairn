"""The two printers: what their text says, read independently of how they produce it."""
import copy
import hashlib
import os
import re
import unittest

import common
from kairn_gen import cpp, expr, ir, rocq, simd

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


def functions(text, fixups=False):
    """{(name, limb type): body lines} of a generated header: of the kernels, or with fixups, of
    the fix-ups that are functions of their own (namespace fixup)."""
    out, current = {}, None
    for line in text.splitlines():
        if fixups:
            m = re.match(r'KAIRN_GEN_COLD (constexpr )?result<(double|float), [0-9]+> (\w+)\(', line)
            key = (m.group(3), m.group(2)) if m else None
        else:
            m = re.match(r'KAIRN_GEN_FORCEINLINE (constexpr )?void (\w+)\((double|float) ', line) or \
                re.match(r'inline (constexpr )?void (\w+)\((double|float) ', line)
            key = (m.group(2), m.group(3)) if m else None
        if m:
            current = out.setdefault(key, {'constexpr': bool(m.group(1)), 'lines': [], 'head': line})
        elif line == '}':
            current = None
        elif current is not None:
            current['lines'].append(line)
    return out


def form(lines, call):
    """The lines of a kernel body that the compiler sees with KAIRN_GEN_FIXUP_CALL 1 (call: the
    fix-up is a function of its own) or 0 (inline)."""
    out, keep = [], []
    for line in lines:
        if line == '#if KAIRN_GEN_FIXUP_CALL':
            keep.append(call)
        elif line == '#else':
            keep[-1] = not keep[-1]
        elif line == '#endif':
            keep.pop()
        elif all(keep):
            out.append(line)
    return out


ATOM = r'(?:[a-z][a-z0-9_]*|0x1(?:\.[0-9a-f]+)?p[-+][0-9]+f?|0\.0f?|' \
       r'std::numeric_limits<(?:double|float)>::(?:infinity|quiet_NaN)\(\))'
# One operation, written over atoms: what "one operation per statement" allows (a bare atom is a
# copy, which is none).
ONE_OPERATION = re.compile(
    rf'(?:-{ATOM}|!{ATOM}|{ATOM} (?:[-+*<>&|]|<=|>=|==) {ATOM}|{ATOM} \? {ATOM} : {ATOM}|'
    rf'fma_rn\(-?{ATOM}, {ATOM}, -?{ATOM}\)|(?:abs_bits|next_up_bits|next_down_bits)\({ATOM}\)|'
    rf'{ATOM} \* {ATOM} \+ {ATOM}|{ATOM}|'
    # guard in a constexpr kernel: its operand in constant evaluation, one addition at run time;
    # times_inf: comparisons in constant evaluation (times_inf_ce), one multiplication at run time;
    # prod in a kernel constexpr by the rule of the product: the plain product in constant
    # evaluation, the opaque product at run time.
    rf'__builtin_is_constant_evaluated\(\) \? (?P<g>{ATOM}) : (?P=g) \+ 0\.0f?|'
    rf'__builtin_is_constant_evaluated\(\) \? times_inf_ce\((?P<t>{ATOM})\) : (?P=t) \* {ATOM}|'
    rf'__builtin_is_constant_evaluated\(\) \? (?P<pa>{ATOM}) \* (?P<pb>{ATOM}) : '
    rf'fma_rn\((?P=pa), (?P=pb), 0\.0f?\))')
# The constant-evaluation arm of a statement that dispatches on constant evaluation (guard,
# times_inf, and prod by the rule of the product), which run time never takes.
CONSTEVAL_ARM = re.compile(r'__builtin_is_constant_evaluated\(\) \? .*? : ')
# The spelling of times_inf: a plain multiplication by +infinity.
TIMES_INF = r' \* std::numeric_limits<(?:double|float)>::infinity\(\);$'

# The kernels whose fix-up the scalar printer puts behind a branch (cpp.branch), and the masks it
# tests: the full kernels on f; the full Ball kernels and the constructors of balls on e & f.
FULL = {f'{core}_full' for core in ('add_2_2', 'add_fast_2_2', 'sub_2_2', 'add_2_1', 'sub_2_1', 'sub_1_2',
                                    'mul_2_2', 'mul_2_1', 'mul_pow2_2')}
FULL_BALL = {f'ball_{op}_{k}_full' for op in ('add', 'sub', 'mul', 'scale', 'mul_pow2') for k in (1, 2)}
BRANCHED = dict({k: ('f',) for k in FULL}, **{k: ('e', 'f') for k in FULL_BALL | {'ball_make_1', 'ball_make_2'}})


class Cpp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()
        cls.text = cpp.scalar(cls.ks)
        cls.fns = functions(cls.text)
        cls.tks = common.kernels(common.TEST_KERNELS)
        cls.tfns = functions(cpp.scalar(cls.tks))

    def run_time(self, lines):
        """The statements after the constant-evaluation branch, if any, with the fix-up inline
        (KAIRN_GEN_FIXUP_CALL 0)."""
        if '    if (__builtin_is_constant_evaluated()) {' in lines:
            lines = lines[lines.index('    }') + 1:]
        return form(lines, call=False)

    def test_every_kernel_twice(self):
        self.assertEqual(set(self.fns), {(k, t) for k in self.ks for t in ('double', 'float')})
        self.assertEqual(set(functions(self.text, fixups=True)), {(k, t) for k in BRANCHED for t in ('double', 'float')})

    def test_one_operation_per_statement(self):
        for fns, ks in ((self.fns, self.ks), (self.tfns, self.tks), (functions(self.text, fixups=True), self.ks),
                        (functions(cpp.scalar(self.tks), fixups=True), self.tks)):
            for (name, t), f in fns.items():
                for line in f['lines']:
                    m = re.fullmatch(rf'\s+const (?:{t}|bool) ([a-z0-9_]+) = (.*);', line)
                    if m:
                        self.assertRegex(m.group(2), rf'\A{ONE_OPERATION.pattern}\Z', (name, line))
                    elif not (re.fullmatch(rf'\s+(//.*|[a-z0-9_]+_out = {ATOM};|return;|}}|'
                                           r'if \(__builtin_is_constant_evaluated\(\)\) \{|'
                                           r'if \([a-z0-9_]+(?: & [a-z0-9_]+)*\) \[\[likely\]\] \{|\} else \{|'
                                           rf'const fixup::result<{t}, [0-9]+> fixed_ = fixup::{name}\([a-z0-9_, ]*\);|'
                                           r'[a-z0-9_]+_out = fixed_\.limb\[[0-9]+\];|'
                                           r'return \{\{[a-z0-9_]+(?:, [a-z0-9_]+)*\}\};)', line) or
                              line in ('#if KAIRN_GEN_FIXUP_CALL', '#else', '#endif')):
                        self.fail((name, line))

    def test_no_plain_product_at_run_time(self):
        # R1 on the printed text: outside constant evaluation nothing is multiplied except in a
        # muladd and in times_inf (by infinity, exact), and every product is an fma_rn whose count
        # is the IR's.
        for fns, ks in ((self.fns, self.ks), (self.tfns, self.tks)):
            for (name, t), f in fns.items():
                body = [CONSTEVAL_ARM.sub('', line) for line in self.run_time(f['lines'])]
                prims = ir.prims(ks[name], ks)
                stars = sum(line.count(' * ') for line in body if not line.strip().startswith('//'))
                self.assertEqual(stars, sum(p.op in ('muladd', 'times_inf') for p in prims), name)
                self.assertEqual(sum(bool(re.search(TIMES_INF, line)) for line in body),
                                 sum(p.op == 'times_inf' for p in prims), name)
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

    # The kernels with a fused operation other than prod (fma, fms) and no constant-evaluation
    # variant: the products of two limbs (fma), the Ball cores of the second radius design (fma),
    # and the directed products of one limb (two_prod's fms, which they must not evaluate through
    # its variant: milestone2.md, "Building blocks on T").
    NOT_CONSTEXPR = {'mul_2_2', 'mul_2_1', 'ball_add_1', 'ball_add_2', 'ball_mul_1', 'ball_mul_2', 'ball_scale_1',
                     'ball_scale_2', 'ball_sub_1', 'ball_sub_2', 'mul_down_1', 'mul_up_1'}
    # The full kernels are constexpr where their cores are: their fix-up turns t into an infinity
    # with times_inf, which is no fused operation. Those of the products of two limbs are not, nor
    # are the full Ball kernels but the scalings by a power of two. The constructors are.
    NOT_CONSTEXPR |= {f'{core}_full' for core in ('mul_2_2', 'mul_2_1')}
    NOT_CONSTEXPR |= {f'ball_{op}_{k}_full' for op in ('add', 'sub', 'mul', 'scale') for k in (1, 2)}
    # The kernels whose only fused operations are prod, constexpr by the rule of the product
    # (milestone2.md, "The two executions of a product").
    PRODUCT_RULE = {'rmul', 'mul_1_1', 'split', 'two_prod_dekker', 'mul_pow2_2', 'mul_pow2_2_full', 'ball_mul_pow2_1',
                    'ball_mul_pow2_2', 'ball_mul_pow2_1_full', 'ball_mul_pow2_2_full'}

    def test_constexpr(self):
        plain = {name for (name, _), f in self.fns.items() if not f['constexpr']}
        self.assertEqual(plain, self.NOT_CONSTEXPR)
        line = [x for x in self.text.splitlines() if x.startswith('// Not constexpr: ')]
        self.assertEqual(set(line[0][len('// Not constexpr: '):-1].split(', ')), self.NOT_CONSTEXPR)
        self.assertTrue(all(f['head'].startswith('KAIRN_GEN_FORCEINLINE') for f in self.fns.values()))

    def test_the_rule_of_the_product(self):
        """A kernel whose only fused operations are prod is constexpr, and prints each prod as the
        plain product under __builtin_is_constant_evaluated() and as the opaque product otherwise;
        its fix-up function too. No other kernel has the dispatch on a product."""
        self.assertEqual({n for n, k in self.ks.items() if cpp.product_rule(k, self.ks)}, self.PRODUCT_RULE)
        dispatch = re.compile(rf'__builtin_is_constant_evaluated\(\) \? ({ATOM}) \* ({ATOM}) : fma_rn\(\1, \2, 0\.0f?\)')
        for fns in (self.fns, functions(self.text, fixups=True)):
            for (name, t), f in fns.items():
                body = form(f['lines'], call=True) + form(f['lines'], call=False)
                with self.subTest(kernel=name, type=t):
                    if name in self.PRODUCT_RULE:
                        self.assertTrue(f['constexpr'])
                        self.assertFalse(any(re.search(r'fma_rn\(', CONSTEVAL_ARM.sub('', x)) and not dispatch.search(x)
                                             for x in body), name)
                    else:
                        self.assertFalse(any(dispatch.search(x) for x in body), name)
        k = self.ks['mul_pow2_2']
        lines = self.fns[('mul_pow2_2', 'double')]['lines']
        self.assertEqual(lines[:2], ['    const double h = __builtin_is_constant_evaluated() ? x0 * c : fma_rn(x0, c, 0.0);',
                                     '    const double l = __builtin_is_constant_evaluated() ? x1 * c : fma_rn(x1, c, 0.0);'])
        self.assertEqual(sum(bool(dispatch.search(x)) for x in lines), sum(p.op == 'prod' for p in ir.prims(k, self.ks)))
        self.assertIn('constexpr, each prod a plain product in constant evaluation.', self.text)
        # two_prod keeps its variant: Dekker's product in constant evaluation, the FMA at run time.
        self.assertFalse(any(dispatch.search(x) for x in self.fns[('two_prod', 'double')]['lines']))

    def test_masks_and_unused_inputs(self):
        self.assertTrue(self.fns[('lt_2_2', 'double')]['head'].endswith('double y1, bool& m_out) noexcept {'))
        # lt(a, b) is written b > a and le(a, b) b >= a (MSVC's constant evaluator takes < and <=
        # with a NaN for true); the C++ never has < or <= between values.
        self.assertIn('    const bool l = 0.0f > x1;', self.fns[('lt_2_1', 'float')]['lines'])
        self.assertIn('    const bool l = y1 > 0.0;', self.fns[('lt_1_2', 'double')]['lines'])
        self.assertIn('    const bool l = y1 >= x1;', self.fns[('le_2_2', 'double')]['lines'])
        for f in list(self.fns.values()) + list(self.tfns.values()):
            self.assertFalse(any(re.search(r' <=? ', line) for line in f['lines'] if not line.strip().startswith('//')))
        self.assertIn('    const bool t = e & l;', self.fns[('lt_2_2', 'double')]['lines'])
        self.assertIn('    const double t = m ? s : x0;', self.fns[('to_up_2', 'double')]['lines'])
        self.assertIn('[[maybe_unused]] double x1', self.fns[('to_nearest_2', 'double')]['head'])
        self.assertIn('    const double t = x0;', self.fns[('to_nearest_2', 'double')]['lines'])
        heads = cpp.scalar(self.tks)
        self.assertIn('void ops_wave2(double a, bool w, double b, double& r0_out, double& c1_out, '
                      'double& k1_out, bool& v_out) noexcept {', heads)

    def test_computed_constants(self):
        # The constants E, G, H of the second radius design, rounded up to the format. For
        # ball_add_1: E = rel / (1 - rel) with rel = u / (1 + u) is u exactly; G = (1 + u)^3 rounds
        # up to 1 + 4u; H = (1 + u) ((1 + u)^2 eta + eta/2) + N, with N = eta/(2u) the smallest
        # normal number (2^-1022, 2^-126), is just above N + (3/2) eta and rounds up to N + 2 eta.
        add = self.fns[('ball_add_1', 'double')]['lines']
        self.assertIn('    const double t = fma_rn(az, 0x1p-53, s);', add)
        self.assertIn('    const double rz = fma_rn(t, 0x1.0000000000002p+0, 0x1.0000000000002p-1022);', add)
        add = self.fns[('ball_add_1', 'float')]['lines']
        self.assertIn('    const float rz = fma_rn(t, 0x1.000004p+0f, 0x1.000004p-126f);', add)
        # ball_mul_1: G = (1 + u)^5 rounds up to 1 + 6u; H, just above N + 3 eta, to N + 4 eta.
        mul = self.fns[('ball_mul_1', 'float')]['lines']
        self.assertIn('    const float t = fma_rn(az, 0x1p-24f, w);', mul)
        self.assertIn('    const float rz = fma_rn(t, 0x1.000006p+0f, 0x1.000008p-126f);', mul)
        # ball_mul_2: 4u^2 / (1 - 4u^2) rounds up to 2^-104 (1 + 2^-52); (1 + u)^6 to 1 + 8u; H,
        # just above N + 4 eta, to N + 5 eta.
        mul2 = self.fns[('ball_mul_2', 'double')]['lines']
        self.assertIn('    const double t = fma_rn(az, 0x1.0000000000001p-104, w);', mul2)
        self.assertIn('    const double rz = fma_rn(t, 0x1.0000000000004p+0, 0x1.0000000000005p-1022);', mul2)

    def test_inlined_names(self):
        add = self.fns[('add_2_2', 'double')]['lines']
        for line in ('    // (sh, sl) = two_sum(x0, y0)', '    const double sh_bb = sh - x0;',
                     '    const double vh_z = vh - sh;', '    const double z1 = w - z0_z;',
                     '    z0_out = z0;'):
            self.assertIn(line, add)

    def test_guard_and_the_non_finite_constants(self):
        # guard(a) is an addition of +0 of the limb type, never a subtraction of 0 or an addition
        # of -0, which compilers fold away; one guard per guard of the IR, and nothing else adds +0.
        # In a constexpr kernel it is the operand itself in constant evaluation.
        for fns, ks in ((self.fns, self.ks), (self.tfns, self.tks)):
            for (name, t), f in fns.items():
                zero = '0.0f' if t == 'float' else '0.0'
                body = self.run_time(f['lines'])
                guards = [p for p in ir.prims(ks[name], ks) if p.op == 'guard']
                added = [x for x in body if x.endswith(f' + {zero};')]
                self.assertEqual(len(added), len(guards), (name, t))
                for p in guards:
                    a = p.args[0].name
                    run_time = f'{a} + {zero}'
                    want = f'__builtin_is_constant_evaluated() ? {a} : {run_time}' if f['constexpr'] else run_time
                    self.assertIn(f'const {t} {p.dst} = {want};', [x.strip() for x in body], name)
                self.assertFalse(any(x.endswith((f' - {zero};', f' + -{zero};')) for x in body), name)
        self.assertTrue(any(p.op == 'guard' for n in self.tks for p in ir.prims(self.tks[n], self.tks)))
        # The core's guard of a comes first; the fix-up's own guard, and t, are behind the branch.
        lines = self.fns[('add_2_1_full', 'double')]['lines']
        full = form(lines, call=False)
        self.assertEqual(full[1], '    const double z0_g = __builtin_is_constant_evaluated() ? a : a + 0.0;')
        self.assertIn('        const double g = __builtin_is_constant_evaluated() ? a : a + 0.0;', full)
        self.assertIn('        const double t = x0 + g;', full)
        self.assertIn('        const double r0 = __builtin_is_constant_evaluated() ? times_inf_ce(t) : '
                      't * std::numeric_limits<double>::infinity();', full)
        fixup = functions(self.text, fixups=True)[('add_2_1_full', 'double')]
        self.assertTrue(fixup['constexpr'])
        self.assertEqual(fixup['lines'][:2], ['    const double g = __builtin_is_constant_evaluated() ? a : a + 0.0;',
                                              '    const double t = x0 + g;'])
        # A kernel that is not constexpr multiplies, with no dispatch.
        self.assertIn('        const double r0 = t * std::numeric_limits<double>::infinity();',
                      self.fns[('mul_2_2_full', 'double')]['lines'])
        self.assertFalse(functions(self.text, fixups=True)[('mul_2_2_full', 'double')]['constexpr'])
        prelude = cpp.prelude(self.ks)
        self.assertIn('KAIRN_GEN_FORCEINLINE constexpr float times_inf_ce(float t) noexcept {\n'
                      '    return t > 0 ? std::numeric_limits<float>::infinity() : 0 > t ? '
                      '-std::numeric_limits<float>::infinity() : std::numeric_limits<float>::quiet_NaN();\n}', prelude)
        self.assertIn('    const bool f = std::numeric_limits<double>::infinity() > az;', full)
        self.assertIn('        const double w1 = f ? z1 : r1;', full)
        make = self.fns[('ball_make_2', 'float')]
        self.assertTrue(make['constexpr'])
        self.assertIn('        const float rw = e ? s : std::numeric_limits<float>::quiet_NaN();', make['lines'])
        self.assertIn('    const bool e = g >= 0.0f;', make['lines'])
        self.assertIn('#include <limits>', cpp.prelude(self.ks))
        self.assertIn('#include <limits>', cpp.prelude(self.tks))         # ops_special, ops_branch
        without = {n: k for n, k in self.tks.items() if n not in ('ops_special', 'ops_branch')}
        self.assertNotIn('#include <limits>', cpp.prelude(without))

    def test_name_clash_is_refused(self):
        ks = copy.deepcopy(dict(self.ks))
        k = ks['fast_two_sum']
        k.body = [ir.Stmt(('s',), 'add', (ir.Operand('a'), ir.Operand('b')), 1),
                  ir.Stmt(('out',), 'sub', (ir.Operand('s'), ir.Operand('a')), 2),
                  ir.Stmt(('e',), 'sub', (ir.Operand('b'), ir.Operand('out')), 3)]
        with self.assertRaises(cpp.PrintError):
            cpp.function(ks['add_2_1'], ks, 'double')    # z0_out is the inlined `out` and an output


def names(items):
    return [it.dst if isinstance(it, ir.Prim) else ('call', it.callee) for it in items]


class FixupBranch(unittest.TestCase):
    """The scalar printer's branch over a fix-up (cpp.branch; milestone1.md, "Emission"): which
    kernels it applies to, each case of the rule on toy kernels, and the two emitted forms."""

    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()
        cls.text = cpp.scalar(cls.ks)
        cls.fns = functions(cls.text)
        cls.fixups = functions(cls.text, fixups=True)
        cls.tks = common.kernels(common.TEST_KERNELS)

    def toy(self, edit=None, **changes):
        """ops_branch, with statements replaced ({dst: (op, args...)}) and fields changed."""
        ks = copy.deepcopy(dict(self.tks))
        k = ks['ops_branch']
        for st in list(k.body):
            if edit and st.dsts[0] in edit:
                op, *args = edit[st.dsts[0]]
                operands = tuple(ir.Operand(a, const=True) if a in ('0', 'inf') else ir.Operand(a) for a in args)
                k.body[k.body.index(st)] = ir.Stmt(st.dsts, op, operands, st.line)
        for field, value in changes.items():
            setattr(k, field, value)
        return cpp.branch(k, ks)

    def test_the_kernels_it_applies_to(self):
        got = {n: b.masks for n, k in self.ks.items() for b in [cpp.branch(k, self.ks)] if b}
        self.assertEqual(got, BRANCHED)
        # The constructors of 2-limb numbers have no fix-up of this shape: make_2 returns x0 as it is
        # guarded, make_2_limbs has no select. Kernels with a real-model statement select on their
        # data (to_up_2 on the sign of x1), and are left alone too.
        for name in ('make_2', 'make_2_limbs', 'to_up_2', 'to_down_2', 'abs_2', 'abs_upper_2', 'lt_2_2'):
            self.assertIsNone(cpp.branch(self.ks[name], self.ks), name)
        for name in BRANCHED:
            b = cpp.branch(self.ks[name], self.ks)
            ball = name.startswith('ball_')
            arms = {'ball_make_1': ['c0', 'g'], 'ball_make_2': ['c0', 'c1', 'g']}.get(
                name, (['cz', 'rz'] if name.endswith('_1_full') else ['cz0', 'cz1', 'rz']) if ball else ['z0', 'z1'])
            self.assertEqual([str(a) for a in b.arms], arms, name)
            fixup = names(b.after)
            if not ball:
                # The operation of T on the leading limbs, its canonical form, and the selects.
                self.assertEqual(fixup[-5:], ['r0', 'n', 'r1', 'w0', 'w1'], name)
                self.assertIn(fixup[-6], ('t',), name)
                self.assertIn(fixup[:-6], ([], ['g']), name)
            else:
                # Only selects: the masks and the core need everything else.
                ops = {p.dst: p.op for p in ir.prims(self.ks[name], self.ks)}
                self.assertEqual({ops[v] for v in fixup}, {'select'}, name)

    def test_one_mask_and_two(self):
        # ops_branch: the outputs select on m1, their first arms on m2.
        b = cpp.branch(self.tks['ops_branch'], self.tks)
        self.assertEqual(b.masks, ('m1', 'm2'))
        self.assertEqual([str(a) for a in b.arms], ['s', '0', 'a'])   # a value, the literal zero, an input
        self.assertEqual(names(b.before), ['s', 'm1', 'm2'])
        self.assertEqual(names(b.after), ['d', 'q', 'h', 'k', 'l', 'x0', 'x1', 'y'])
        # One mask: the first arms are not all selects on one mask.
        b = self.toy({'l': ('select', 'm1', 'a', 'b')})
        self.assertEqual(b.masks, ('m1',))
        self.assertEqual([str(a) for a in b.arms], ['h', 'k', 'l'])
        self.assertEqual(names(b.before), ['s', 'm1', 'm2', 'd', 'q', 'h', 'k', 'l'])
        self.assertEqual(names(b.after), ['x0', 'x1', 'y'])
        # An arm that is no select at all stops the descent the same way.
        self.assertEqual(self.toy({'k': ('sub', 'd', 's')}).masks, ('m1',))
        # A second level on the first mask again adds nothing.
        self.assertEqual(self.toy({'h': ('select', 'm1', 's', 'q'), 'k': ('select', 'm1', '0', 'd'),
                                   'l': ('select', 'm1', 'a', 'b')}).masks, ('m1',))

    def test_what_it_leaves_alone(self):
        # Outputs that select on different masks; an output that is no select.
        self.assertIsNone(self.toy({'x1': ('select', 'm2', 'k', 'd')}))
        self.assertIsNone(self.toy({'y': ('add', 'l', 's')}))
        # A kernel with a real-model statement, whatever its shape.
        self.assertIsNone(self.toy(ensures=[{'kind': 'normalized', 'of': 'x'}], domain=None))
        # A mask output.
        ks = copy.deepcopy(dict(self.tks))
        k = ks['ops_branch']
        k.outputs = k.outputs + [ir.Group('m2', ('m2',), ir.MASK)]
        self.assertIsNone(cpp.branch(k, ks))

    def test_the_emitted_branch(self):
        lines = self.fns[('ball_add_2_full', 'double')]['lines']
        inline, call = form(lines, call=False), form(lines, call=True)
        i = inline.index('    if (e & f) [[likely]] {')
        self.assertEqual(inline[i:i + 5], ['    if (e & f) [[likely]] {', '        cw0_out = cz0;', '        cw1_out = cz1;',
                                           '        rw_out = rz;', '    } else {'])
        self.assertEqual(inline[i + 5:], ['        const double c0 = f ? cz0 : 0.0;', '        const double c1 = f ? cz1 : 0.0;',
                                          '        const double r = f ? rz : std::numeric_limits<double>::infinity();',
                                          '        const double cw0 = e ? c0 : q;', '        const double cw1 = e ? c1 : q;',
                                          '        const double rw = e ? r : q;', '        cw0_out = cw0;',
                                          '        cw1_out = cw1;', '        rw_out = rw;', '    }'])
        self.assertEqual(call[i + 5:], ['        const fixup::result<double, 3> fixed_ = '
                                        'fixup::ball_add_2_full(cz0, cz1, rz, q, e, f);',
                                        '        cw0_out = fixed_.limb[0];', '        cw1_out = fixed_.limb[1];',
                                        '        rw_out = fixed_.limb[2];', '    }'])
        self.assertEqual(inline[:i], call[:i])
        self.assertTrue(self.fixups[('ball_add_2_full', 'double')]['head'].startswith(
            'KAIRN_GEN_COLD result<double, 3> ball_add_2_full(double cz0, double cz1, double rz, double q, bool e, bool f)'))
        toy = form(functions(cpp.scalar(self.tks))[('ops_branch', 'float')]['lines'], call=False)
        self.assertEqual(toy[3:8], ['    if (m1 & m2) [[likely]] {', '        x0_out = s;', '        x1_out = 0.0f;',
                                    '        y_out = a;', '    } else {'])

    def test_both_forms_have_the_operations_of_the_listing(self):
        """Inline, every operation of the flattened listing once: in the listing's order, or with
        a branch, those before it and those of the fix-up each in the listing's order. As a call,
        the same statements, split between the kernel and its fix-up function, whose parameters
        are the values the fix-up uses and does not compute."""
        for ks, text in ((self.ks, self.text), (self.tks, cpp.scalar(self.tks))):
            fns, fixups = functions(text), functions(text, fixups=True)
            for (name, t), f in fns.items():
                prims = ir.prims(ks[name], ks)
                b = cpp.branch(ks[name], ks)
                order = [p.dst for p in prims] if b is None else \
                    [n for n in names(b.before) + names(b.after) if isinstance(n, str)]
                self.assertEqual(sorted(order), sorted(p.dst for p in prims), name)
                stmts = [x.strip() for x in Cpp.run_time(None, f['lines']) if x.strip().startswith('const ')]
                self.assertEqual([re.match(r'const \w+ (\w+) = ', x).group(1) for x in stmts], order, (name, t))
                if (name, t) not in fixups:
                    self.assertIsNone(b, name)
                    self.assertNotIn('#if KAIRN_GEN_FIXUP_CALL', f['lines'], name)
                    continue
                fixup = fixups[(name, t)]
                called = [x.strip() for x in form(f['lines'], call=True) if x.strip().startswith('const ')]
                inner = [x.strip() for x in fixup['lines'] if x.strip().startswith('const ')]
                self.assertEqual(called[:-1] + inner, stmts, (name, t))
                self.assertEqual(called[-1], f'const fixup::result<{t}, {len(ks[name].output_limbs)}> fixed_ = '
                                             f'fixup::{name}({", ".join(cpp.fixup_inputs(ks[name], b))});')
                defined = {p.dst for p in prims if p.dst in {it.dst for it in b.after if isinstance(it, ir.Prim)}}
                used = {a.name for p in prims if p.dst in defined for a in p.args if not a.const}
                self.assertEqual(set(cpp.fixup_inputs(ks[name], b)), used - defined, name)
                self.assertEqual(fixup['constexpr'], f['constexpr'], name)

    def test_the_prelude_chooses_the_form(self):
        prelude = cpp.prelude(self.ks)
        self.assertIn('#if !defined(KAIRN_GEN_FIXUP_CALL)\n#if defined(__clang__) && defined(__aarch64__)\n'
                      '#define KAIRN_GEN_FIXUP_CALL 1\n#else\n#define KAIRN_GEN_FIXUP_CALL 0\n#endif\n#endif\n', prelude)
        self.assertIn('#define KAIRN_GEN_COLD inline __attribute__((noinline, cold))', prelude)
        self.assertIn('#define KAIRN_GEN_COLD inline __declspec(noinline)', prelude)
        # Without a kernel that branches, none of it.
        ks = {n: k for n, k in self.tks.items() if n != 'ops_branch'}
        self.assertNotIn('KAIRN_GEN_FIXUP_CALL', cpp.prelude(ks) + cpp.scalar(ks))


def packed_functions(text):
    """{(name, vector type): body lines} of a generated packed header."""
    out, current = {}, None
    for line in text.splitlines():
        m = re.match(r'(?:KAIRN_GEN_FORCEINLINE|inline) void (\w+)\((?:\[\[maybe_unused\]\] )?(\w+) ', line)
        if m:
            current = out.setdefault((m.group(1), m.group(2)), [])
        elif line == '}':
            current = None
        elif current is not None:
            current.append(line)
    return out


class Packed(unittest.TestCase):
    """The AVX2 and NEON printers: one intrinsic per statement, products only as FMAs."""
    FUSED = {'avx2.hpp': r'_mm256_fn?m(?:add|sub)_p[sd]\(', 'neon.hpp': r'vfm[as]q_f(?:32|64)\('}
    PLAIN_PRODUCT = {'avx2.hpp': r'_mm256_mul_p[sd]\(', 'neon.hpp': r'vmulq_f(?:32|64)\('}
    SPECIAL = r'std::numeric_limits<(?:double|float)>::(?:infinity|quiet_NaN)\(\)'
    CONSTANT = {'avx2.hpp': rf'_mm256_(?:set1_p[sd]\((?:[-+0-9a-fx.p]+f?|{SPECIAL})\)|setzero_p[sd]\(\))',
                'neon.hpp': rf'vdupq_n_f(?:32|64)\((?:[-+0-9a-fx.p]+f?|{SPECIAL})\)'}
    CALL = r'(?:_mm256_\w+|v\w+q_[fu](?:32|64)|not_mask|next_up_bits|next_down_bits)\('

    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()
        cls.tks = common.kernels(common.TEST_KERNELS)
        cls.texts = {(b['file'], d): simd.header(b, ks) for b in simd.BACKENDS
                     for d, ks in (('kernels', cls.ks), ('test', cls.tks))}

    def test_every_kernel_twice(self):
        for b in simd.BACKENDS:
            fns = packed_functions(self.texts[(b['file'], 'kernels')])
            types = {v for v, *_ in b['types'].values()}
            self.assertEqual(set(fns), {(k, t) for k in self.ks for t in types}, b['file'])

    def test_one_intrinsic_per_statement(self):
        for (file, which), text in self.texts.items():
            ks = self.ks if which == 'kernels' else self.tks
            for (name, vtype), lines in packed_functions(text).items():
                ops = [p.op for p in ir.prims(ks[name], ks)]
                stmts = [ln for ln in lines if re.match(r'\s+const \w+ \w+ = ', ln)]
                self.assertEqual(len(stmts), len(ops), name)
                for line, op in zip(stmts, ops):
                    expr = re.sub(self.CONSTANT[file], 'K', line.split(' = ', 1)[1])
                    calls = len(re.findall(self.CALL, expr))
                    # Two calls only where the spelling composes an exact negation (NEON's fms) or
                    # is the declared contractable multiply-add.
                    want = 0 if op == 'copy' else 2 if (op == 'muladd' or (op == 'fms' and file == 'neon.hpp')) else 1
                    self.assertEqual(calls, want, (file, name, line))
                self.assertTrue(all(re.fullmatch(r'\s+(//.*|\w+_out = \w+;|const \w+ \w+ = .*;)', ln)
                                    for ln in lines), name)

    def test_products_are_fused_operations(self):
        for (file, which), text in self.texts.items():
            ks = self.ks if which == 'kernels' else self.tks
            for (name, vtype), lines in packed_functions(text).items():
                prims = ir.prims(ks[name], ks)
                body = '\n'.join(lines)
                self.assertEqual(len(re.findall(self.FUSED[file], body)), sum(p.op in ir.FUSED for p in prims),
                                 (file, name))
                # Plain products: those of a muladd, and times_inf's, by infinity.
                self.assertEqual(len(re.findall(self.PLAIN_PRODUCT[file], body)),
                                 sum(p.op in ('muladd', 'times_inf') for p in prims), (file, name))
                by_infinity = r'(?:_mm256_mul_p[sd]|vmulq_f(?:32|64))\(\w+, (?:_mm256_set1_p[sd]|vdupq_n_f(?:32|64))' \
                              r'\(std::numeric_limits<(?:double|float)>::infinity\(\)\)\)'
                self.assertEqual(len(re.findall(by_infinity, body)), sum(p.op == 'times_inf' for p in prims),
                                 (file, name))
                zero = '_mm256_setzero_p' if file == 'avx2.hpp' else 'vdupq_n_f'
                stmts = [x for x in lines if re.match(r'\s+const \w+ \w+ = ', x)]
                prods = [ln for ln, p in zip(stmts, prims) if p.op == 'prod']
                self.assertEqual(len(prods), sum(p.op == 'prod' for p in prims))
                self.assertTrue(all(zero in ln for ln in prods), (file, name))

    def test_spellings(self):
        avx2 = packed_functions(self.texts[('avx2.hpp', 'kernels')])
        neon = packed_functions(self.texts[('neon.hpp', 'kernels')])
        self.assertIn('    const __m256d t = _mm256_blendv_pd(x0, s, m);', avx2[('to_up_2', '__m256d')])
        self.assertIn('    const __m256d l = _mm256_cmp_pd(x1, _mm256_setzero_pd(), _CMP_LT_OQ);',
                      avx2[('lt_2_1', '__m256d')])
        self.assertIn('    const __m256 t = _mm256_and_ps(e, l);', avx2[('lt_2_2', '__m256')])
        self.assertIn('    const float64x2_t t = vbslq_f64(m, s, x0);', neon[('to_up_2', 'float64x2_t')])
        self.assertIn('    const uint32x4_t t = vandq_u32(e, l);', neon[('lt_2_2', 'float32x4_t')])
        self.assertIn('    const float64x2_t e = vfmaq_f64(vnegq_f64(p), a, b);', neon[('two_prod', 'float64x2_t')])
        self.assertIn('    const __m256d e = _mm256_fmsub_pd(a, b, p);', avx2[('two_prod', '__m256d')])
        self.assertIn('    const __m256d t = _mm256_fmadd_pd(az, _mm256_set1_pd(0x1p-53), s);',
                      avx2[('ball_add_1', '__m256d')])
        text = self.texts[('neon.hpp', 'kernels')]
        self.assertIn('void lt_2_2(float64x2_t x0, float64x2_t x1, float64x2_t y0, float64x2_t y1, '
                      'uint64x2_t& m_out) noexcept {', text)
        self.assertIn('[[maybe_unused]] __m256d x1', self.texts[('avx2.hpp', 'kernels')])
        self.assertNotIn('constexpr void', text)
        # guard: an addition of a zero vector; the non-finite constants broadcast from <limits>.
        self.assertIn('    const __m256d x0 = _mm256_add_pd(a, _mm256_setzero_pd());', avx2[('make_2', '__m256d')])
        self.assertIn('    const float32x4_t c0 = vaddq_f32(c, vdupq_n_f32(0.0f));', neon[('ball_make_1', 'float32x4_t')])
        self.assertIn('    const __m256 r0 = _mm256_mul_ps(t, _mm256_set1_ps(std::numeric_limits<float>::infinity()));',
                      avx2[('mul_2_2_full', '__m256')])
        self.assertIn('    const float64x2_t r0 = vmulq_f64(t, vdupq_n_f64(std::numeric_limits<double>::infinity()));',
                      neon[('add_2_2_full', 'float64x2_t')])
        self.assertIn('    const float64x2_t rw = vbslq_f64(e, s, vdupq_n_f64(std::numeric_limits<double>::quiet_NaN()));',
                      neon[('ball_make_2', 'float64x2_t')])
        for (file, which), t in self.texts.items():
            ks = self.ks if which == 'kernels' else self.tks
            for (name, vtype), lines in packed_functions(t).items():
                guards = sum(p.op == 'guard' for p in ir.prims(ks[name], ks))
                add_zero = r'(?:_mm256_add_p[sd]\(\w+, _mm256_setzero_p[sd]\(\)\)|vaddq_f(?:32|64)\(\w+, vdupq_n_f(?:32|64)\(0\.0f?\)\))'
                self.assertEqual(sum(bool(re.search(add_zero, x)) for x in lines), guards, (file, name))


class Rocq(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.all = common.kernels()
        # The kernels the real model prints: all but the full kernels and the constructors.
        cls.ks = rocq.real(cls.all)
        cls.model = rocq.model(cls.all)
        cls.statements = rocq.statements(cls.all)

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
                if st.is_call and len(st.dsts) == 1:     # a call with one output binds a name
                    self.assertTrue(line.startswith(f"  let {st.dsts[0]} := {st.op} "), line)
                elif st.is_call:
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
  fmt emin prec s /\\
  fmt emin prec e /\\
  s = RN emin prec (a + b) /\\
  (s + e) = (a + b).''', s)
        self.assertIn('  Rabs b <= Rabs a ->\n', s)
        self.assertIn('  (((a * b) = 0 \\/ bpow radix2 (2 * prec - 1) * eta emin <= Rabs (a * b)) -> (p + e) = (a * b)).', s)
        self.assertIn('  Rabs ((z0 + z1) - ((x0 + x1) + (y0 + y1))) <= (3 / (1 - (4 * u prec))) * u prec ^ 2 * '
                      'Rabs ((x0 + x1) + (y0 + y1)).', s)
        self.assertIn('<= 3 * u prec ^ 2 * (Rabs (x0 + x1) + Rabs (y0 + y1)).', s)
        self.assertIn('<= 4 * u prec ^ 2 * Rabs ((x0 + x1) * (y0 + y1)) + (3 / 2) * eta emin.', s)
        self.assertEqual(s.count('_spec : Prop :='), len(self.ks))

    def test_every_output_limb_is_a_number_of_the_format(self):
        """Statements compose: a conclusion says of every output limb what the hypotheses say of
        every input limb, that it is a number of the format, so that the theorem of one kernel
        gives the hypotheses of the next. It says so by the `normalized` claim on the limb's
        group, or else by a `fmt` conjunct; these come first, in output order, and the claims
        follow unchanged. A mask gets nothing. Read from the printed text."""
        tks = rocq.real(common.kernels(common.TEST_KERNELS))
        uncovered = {}
        for ks in (self.ks, tks):
            for name, k in ks.items():
                head, _, conclusion = '\n'.join(rocq.statement(k, ks)).rpartition(' in\n  ')
                self.assertTrue(head.splitlines()[-1].startswith('  let '), name)
                self.assertTrue(conclusion.endswith('.'), name)
                conjuncts = conclusion[:-1].split(' /\\\n  ')
                normalized = {e['of'] for e in k.ensures if e['kind'] == 'normalized'}
                want = []
                for g in k.outputs:
                    said = [f'fmt emin prec {v}' for v in g.limbs]
                    if g.kind == ir.MASK:
                        self.assertNotIn(said[0], conjuncts, name)
                    elif g.name in normalized:
                        claim = said[0] if len(g.limbs) == 1 else \
                            f'normalized_{len(g.limbs)} emin prec {" ".join(g.limbs)}'
                        self.assertIn(claim, conjuncts, (name, g.name))
                    else:
                        want += said
                self.assertEqual(conjuncts[:len(want)], want, name)
                # represents is not printed next to other claims (neg_2, abs_2): in the real model
                # it says what normalized with an exact error says. An exact_when adds a conjunct
                # after its claim's own (ball_mul_pow2_k).
                printed = [e for e in k.ensures if e['kind'] != 'represents']
                printed += [e for e in printed if 'exact_when' in e]
                self.assertEqual(len(conjuncts), len(want) + len(printed), name)
                uncovered[name] = len(want)
        # The loop has something to read: both ways of saying it occur, also in one statement,
        # and so does an output that says nothing (a mask).
        self.assertEqual([uncovered[n] for n in ('two_sum', 'ball_add_2', 'ops_wave2', 'add_2_2', 'lt_2_2')],
                         [2, 1, 3, 0, 0])
        self.assertEqual(sum(uncovered[n] for n in self.ks), 49)
        self.assertEqual(sum(1 for n in self.ks if uncovered[n]), 38)
        s = self.statements
        self.assertIn("  let '(cz0, cz1, rz) := ball_add_2 emin prec tie_even cx0 cx1 rx cy0 cy1 ry in\n"
                      '  fmt emin prec rz /\\\n  normalized_2 emin prec cz0 cz1 /\\\n  (forall x y : R, ', s)
        self.assertIn('  let r := radd emin prec tie_even a b in\n  fmt emin prec r /\\\n  (a + b) <= r /\\ ', s)
        self.assertIn("  let '(ah, al) := split emin prec tie_even a in\n"
                      '  fmt emin prec ah /\\\n  fmt emin prec al /\\\n  (ah + al) = a.', s)
        self.assertIn('  let m := lt_2_2 x0 x1 y0 y1 in\n  m = Rlt_bool (x0 + x1) (y0 + y1).', s)
        self.assertIn("  let '(r0, c1, k1, v) := ops_wave2 emin prec tie_even a w b in\n"
                      '  fmt emin prec r0 /\\\n  fmt emin prec c1 /\\\n  fmt emin prec k1 /\\\n  Rabs (',
                      rocq.statements(tks))

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

    def test_section_arguments(self):
        # Closing the section abstracts a definition over the section variables it uses, and only
        # those (checked with Rocq 9.0.1); the statements apply each kernel accordingly.
        want = {'lt_2_2': [], 'to_nearest_2': [], 'neg_2': [], 'abs_2': [], 'ball_neg_1': [],
                'to_down_2': ['emin', 'prec'], 'abs_upper_2': ['emin', 'prec'], 'ball_neg_2': [],
                'radd': ['emin', 'prec', 'choice'], 'two_sum': ['emin', 'prec', 'choice'],
                'ball_add_1': ['emin', 'prec', 'choice']}
        for name, args in want.items():
            self.assertEqual(rocq.section_args(self.ks[name], self.ks), args, name)
        self.assertIn('  let m := lt_2_2 x0 x1 y0 y1 in\n', self.statements)
        self.assertIn('  let t := to_down_2 emin prec x0 x1 in\n', self.statements)
        self.assertIn("  let '(cz, rz) := ball_add_1 emin prec tie_even cx rx cy ry in\n", self.statements)
        self.assertIn("  let '(cz, rz) := ball_neg_1 cx rx in\n", self.statements)

    def test_second_wave_model(self):
        m = self.model
        self.assertIn('Definition lt_2_1 (x0 x1 a : R) : bool :=\n  let h := Rlt_bool x0 a in\n'
                      '  let e := Req_bool x0 a in\n  let l := Rlt_bool x1 0 in\n  let t := andb e l in\n'
                      '  let m := orb h t in\n  m.', m)
        self.assertIn('  let t := if m then s else x0 in\n', m)
        self.assertIn('  let s := succ radix2 (FLT_exp emin prec) x0 in\n', m)
        self.assertIn('  let p := pred radix2 (FLT_exp emin prec) x0 in\n', m)
        self.assertIn('Definition to_nearest_2 (x0 x1 : R) : R :=\n  let t := x0 in\n  t.', m)
        # The Ball cores of the second radius design, whose constants are named after the first
        # kernel that uses them and their place there (BallDraft.v names them radius_e_K, ...).
        self.assertIn('Definition ball_add_2 (cx0 cx1 rx cy0 cy1 ry : R) : R * R * R :=\n'
                      "  let '(cz0, cz1) := add_2_2 cx0 cx1 cy0 cy1 in\n"
                      '  let az := Rabs cz0 in\n'
                      '  let s := rnd (rx + ry) in\n'
                      '  let t := rnd (az * up_ball_add_2_0 + s) in\n'
                      '  let rz := rnd (t * up_ball_add_1_1 + up_ball_add_1_2) in\n'
                      '  (cz0, cz1, rz).', m)
        self.assertIn("  let '(cz0, cz1, rz) := ball_add_2 cx0 cx1 rx n0 n1 ry in\n", m)
        self.assertIn('Definition up_ball_add_2_0 : R :=\n  round radix2 (FLT_exp emin prec) Zceil '
                      '((((3 / (1 - (4 * bpow radix2 (- prec)))) * bpow radix2 (- prec) ^ 2) / '
                      '(1 - ((3 / (1 - (4 * bpow radix2 (- prec)))) * bpow radix2 (- prec) ^ 2))) * '
                      '(1 + bpow radix2 (- prec))).', m)
        self.assertIn('Definition up_ball_scale_2_2 : R :=\n  round radix2 (FLT_exp emin prec) Zceil '
                      '(((1 + bpow radix2 (- prec)) * (((((1 + bpow radix2 (- prec)) ^ 2) * bpow radix2 emin) + '
                      '((1 * bpow radix2 emin) / (1 - (2 * bpow radix2 (- prec) ^ 2)))) + '
                      '(bpow radix2 emin / 2))) + (bpow radix2 emin / (2 * bpow radix2 (- prec)))).', m)
        self.assertNotIn('unit_computed', m)
        tks = common.kernels(common.TEST_KERNELS)
        self.assertIn('Definition ops_wave2 (a : R) (w : bool) (b : R) : R * R * R * bool :=', rocq.model(tks))

    def test_second_wave_statements(self):
        s = self.statements
        self.assertIn('Definition RD (x : R) : R := round radix2 (FLT_exp emin prec) Zfloor x.', s)
        self.assertIn('Definition RU (x : R) : R := round radix2 (FLT_exp emin prec) Zceil x.', s)
        for text in (
                '  m = Rlt_bool (x0 + x1) (y0 + y1).',                          # predicate
                '  m = Req_bool (x0 + x1) a.',
                '  m = Rle_bool a (y0 + y1).',
                '  t = RN emin prec (x0 + x1).',                                # rounded
                '  t = RD emin prec (x0 + x1).',
                '  t = RU emin prec (Rabs (x0 + x1)).',
                '  (a + b) <= r /\\ r - (a + b) <= (3 / 2) * (r - pred radix2 (FLT_exp emin prec) r).',   # upper
                '  (a * b) <= r /\\ r - (a * b) <= (3 / 2) * (r - pred radix2 (FLT_exp emin prec) r).',
                '  0 <= a ->\n  0 <= b ->\n  let r := radd emin prec tie_even a b in',
                '  (exists n : Z, c = bpow radix2 n) ->',                       # power_of_two
                '  0 <= rx ->',                                                  # nonneg
                '  (forall x y : R, Rabs (x - (cx0 + cx1)) <= rx -> Rabs (y - (cy0 + cy1)) <= ry -> '
                'Rabs ((x * y) - (cz0 + cz1)) <= rz).',                         # encloses
                '  (forall x : R, Rabs (x - cx) <= rx -> Rabs ((x * a) - cz) <= rz).',
                '  (forall x : R, Rabs (x - cx) <= rx -> Rabs ((- x) - cz) <= rz).',
                '  (z0 + z1) = (Rabs (x0 + x1)).',                              # exact, through abs
                '  (z0 + z1) = (- (x0 + x1)).'):
            self.assertIn(text, s)
        tks = common.kernels(common.TEST_KERNELS)
        self.assertIn('  forall a b : R,\n  forall w : bool,\n  fmt emin prec a ->\n  fmt emin prec b ->\n'
                      "  let '(r0, c1, k1, v) := ops_wave2 emin prec tie_even a w b in\n", rocq.statements(tks))

    # SHA-256 of Model.v, Statements.v and Audit.v as the real model prints them, the same before
    # the non-finite layer (commit f39b066) and after it. Change them only together with a change
    # of the real model that is meant, and with the proofs that go with it. Model.v changed once
    # since: H of the six Ball cores gained the smallest normal number (five definitions
    # up_ball_*_2). Then the kernels of wave 1 of Milestone 2 were added (eighteen with a real-model
    # statement, and the constants N, P and eta): every earlier definition and statement is the
    # same, byte for byte, and fast_two_sum and two_prod are printed earlier, before the new kernels
    # that call them; Audit.v lists the same theorems, those two earlier.
    DIGESTS = {'Model.v': '3f2e3f54b76c21bf6d904880d082677af7821f4830b57d2152ee97618df8bbec',
               'Statements.v': '93ad4903d8fc398325f82f1d55cfcbd59c65d4fb88cf404efdcf6616fb3796fe',
               'Audit.v': '0c93acbf8651ff7bc342d1c9ab1f80d0f98718ddf3d0123dbff0d0547a871f15'}

    def test_the_non_finite_layer_leaves_the_real_model_as_it_was(self):
        """The full kernels and the constructors have no real-model statement and appear nowhere in
        the three files; a kernel of the extended domain that has one is printed exactly as if it
        were of the finite domain with normalized for canonical, a normalized center (a number of
        the format, for one limb) and a nonnegative radius for a ball, and without represents next
        to other claims. And the files are those of f39b066 but for the Ball cores of the second
        radius design and add_2_1 with its guard (and radd, rmul, which no kernel calls any more,
        printed further down), in Model.v for the constant H of those cores, and for the kernels
        of wave 1 of Milestone 2 that were added (DIGESTS)."""
        printers = {'Model.v': rocq.model, 'Statements.v': rocq.statements, 'Audit.v': rocq.audit}
        finite = {}
        for name, k in copy.deepcopy(dict(self.all)).items():
            if not k.real_model:
                continue
            k.domain, k.ieee_status, k.ieee_theorem = None, None, None
            requires = []
            for r in k.requires:
                if r[0] == 'canonical':
                    requires.append(('normalized',) + r[1:])
                elif r[0] == 'ball':
                    center = next(g for g in k.inputs if g.name == r[1])
                    requires += ([('normalized', r[1])] if len(center.limbs) > 1 else []) + [('nonneg', r[2])]
                else:
                    requires.append(r)
            k.requires = requires
            k.ensures = [e for e in k.ensures if e['kind'] != 'represents']
            for e in k.ensures:
                e.pop('finite_when', None)
            finite[name] = k
        self.assertEqual(len(finite), 60)
        self.assertTrue(any(k.extended for k in self.all.values() if k.real_model))
        for file, printer in printers.items():
            text = printer(self.all)
            self.assertEqual(text, printer(finite), file)
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), self.DIGESTS[file], file)
            for name, k in self.all.items():
                if not k.real_model:
                    self.assertIsNone(re.search(rf'\b{name}\b', text), (file, name))

    def test_up_constants_in_the_real_model(self):
        """Each distinct const up(EXPR) is one definition, named after the first kernel that uses
        it: EXPR over the reals, with u, eta, unit(K) and tiny(K) spelled out, rounded up by
        Flocq's round with Zceil. The kernel applies it by name; the section variables follow."""
        tks = common.kernels(common.TEST_KERNELS)
        model = rocq.model(tks)
        u = 'bpow radix2 (- prec)'
        self.assertIn('(* up((1+u)^6): the smallest number of the format not below it. *)\n'
                      'Definition up_ops_up_0 : R :=\n'
                      f'  round radix2 (FLT_exp emin prec) Zceil ((1 + {u}) ^ 6).', model)
        self.assertIn('Definition up_ops_up_1 : R :=\n'
                      f'  round radix2 (FLT_exp emin prec) Zceil (((4 * {u} ^ 2) / (1 - (4 * {u} ^ 2))) * (1 + {u})).',
                      model)
        self.assertIn(f'((3 / 2) * bpow radix2 emin) / (1 - (4 * {u} ^ 2))', model)
        self.assertIn('  let k1 := rnd (up_ops_up_0 * a + 0) in\n', model)
        self.assertIn('  let k3 := rnd (up_ops_up_2 * a + 0) in\n', model)
        self.assertEqual(rocq.section_args(tks['ops_up'], tks), ['emin', 'prec', 'choice'])
        self.assertEqual(model.count('Definition up_'), 3)
        self.assertLess(model.index('Definition up_ops_up_0'), model.index('Definition up_ops_up_1'))
        # A negative power is the inverse of the positive one.
        self.assertEqual(rocq._term(expr.parse('2^-3*u'), lambda n: 'u'), '((/ (2 ^ 3)) * u)')

    def test_guard_in_the_real_model(self):
        # guard is one rounding of a + 0, which a proof reads as a; a test kernel with a constant
        # inf or nan has no real-model statement and is not printed.
        tks = common.kernels(common.TEST_KERNELS)
        model, statements = rocq.model(tks), rocq.statements(tks)
        self.assertIn('Definition ops_guard (a b : R) : R * R * R :=\n  let g1 := rnd (a + 0) in\n'
                      '  let n := - b in\n  let g2 := rnd (n + 0) in\n', model)
        self.assertIn('  let \'(r0, g1, g2) := ops_guard emin prec tie_even a b in\n', statements)
        self.assertNotIn('ops_special', model + statements + rocq.audit(tks))

    def test_audit(self):
        ks = copy.deepcopy(dict(self.ks))
        for k in ks.values():
            k.status = 'unverified'
        self.assertIn('(* No kernel is verified yet. *)', rocq.audit(ks))
        ks['mul_2_2'].status = 'proved'
        ks['add_2_2'].status = 'proved'
        audit = rocq.audit(ks)
        self.assertIn('From Kairn Require Import Add22.\nFrom Kairn Require Import Mul22.', audit)
        self.assertIn('Definition mul_2_2_audit : mul_2_2_spec := mul_2_2_correct.\n'
                      'Print Assumptions mul_2_2_correct.', audit)
        self.assertNotIn('Check', audit)       # the audit prints nothing but assumptions


class ConstantNames(unittest.TestCase):
    """The names of the constants up(EXPR) in the Rocq models are stable: gen/constant_names.json
    records them, the printers take a recorded name before anything else, and build only adds to
    the record. Hand-written proofs name these definitions (Ball2.v, IeeeBallCores.v,
    IeeeBallFinite.v, DirectedProd.v, IeeeDirectedProd.v, Directed2.v, ...)."""

    # Every name recorded so far, by the expression of its constant. A recorded name never changes
    # and never disappears: this list only grows, with the record.
    RECORDED = {
        'unit(add_1_1)/(1-unit(add_1_1))': 'up_ball_add_1_0',
        '(1+u)^3': 'up_ball_add_1_1',
        '(1+u)*((1+u)^2*eta+eta/2)+eta/(2*u)': 'up_ball_add_1_2',
        'unit(add_2_2)/(1-unit(add_2_2))*(1+u)': 'up_ball_add_2_0',
        'unit(mul_1_1)/(1-unit(mul_1_1))': 'up_ball_mul_1_0',
        '(1+u)^5': 'up_ball_mul_1_1',
        '(1+u)*(2*(1+u)^4*eta+tiny(mul_1_1)/(1-unit(mul_1_1))+eta/2)+eta/(2*u)': 'up_ball_mul_1_2',
        'unit(mul_2_2)/(1-unit(mul_2_2))': 'up_ball_mul_2_0',
        '(1+u)^6': 'up_ball_mul_2_1',
        '(1+u)*(2*(1+u)^5*eta+tiny(mul_2_2)/(1-unit(mul_2_2))+eta/2)+eta/(2*u)': 'up_ball_mul_2_2',
        'eta/(2*u)': 'up_ball_mul_pow2_1_0',
        '(1+u)*((1+u)^2*eta+tiny(mul_1_1)/(1-unit(mul_1_1))+eta/2)+eta/(2*u)': 'up_ball_scale_1_2',
        'unit(mul_2_1)/(1-unit(mul_2_1))*(1+u)': 'up_ball_scale_2_0',
        '(1+u)*((1+u)^2*eta+tiny(mul_2_1)/(1-unit(mul_2_1))+eta/2)+eta/(2*u)': 'up_ball_scale_2_2',
        'eta/(2*u^2)': 'up_mul_down_1_0',
    }

    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()
        cls.record = ir.load_constant_names(os.path.join(common.GEN, 'kernels'))

    def test_no_recorded_name_changes_or_disappears(self):
        for text, name in self.RECORDED.items():
            self.assertEqual(self.record.get(text), name, text)
        self.assertEqual(len(set(self.record.values())), len(self.record))

    def test_the_printers_use_the_record(self):
        names = rocq.up_names(rocq.real(self.ks))
        for const, name in names.items():
            self.assertEqual(self.record[ir.up(const)], name, const)
        model = rocq.model(self.ks)
        for const, name in names.items():
            self.assertIn(f'(* up({ir.up(const)}): the smallest number of the format not below it. *)\n'
                          f'Definition {name} : R :=', model)
        # The committed record is what build writes: nothing is missing from it.
        with open(os.path.join(common.GEN, ir.CONSTANT_NAMES), encoding='utf-8') as f:
            self.assertEqual(f.read(), rocq.constant_names_file(self.ks))

    def test_a_kernel_added_first_renames_nothing(self):
        """A kernel that comes first (one limb, a name that sorts early) and uses a recorded
        constant takes the recorded name; its new constant gets up_K_i, i its place among the
        kernel's constants, and is the one entry build adds. Without the record the old rule would
        have renamed the recorded constant after the new kernel."""
        text = ('kernel: aaa_first\ninput: a\noutput: r\nvalue: a\nensures: upper r gaps=4\n'
                'status: unverified\ncone_exempt: test\n'
                'p = prod(a, const up(eta/(2*u^2)))\nr = prod(p, const up(3*eta+u))\n')
        k = ir.parse_kernel(text, 'aaa_first.kernel')
        ks = copy.deepcopy(dict(self.ks))
        k.constant_names = next(iter(ks.values())).constant_names
        ks = ir.ordered(dict(ks, aaa_first=k))
        self.assertEqual(next(iter(ks)), 'aaa_first')
        names = rocq.up_names(rocq.real(ks))
        self.assertEqual(names['up(eta/(2*u^2))'], 'up_mul_down_1_0')
        self.assertEqual(names['up(3*eta+u)'], 'up_aaa_first_1')
        added = ir.constant_names_text(dict(self.record, **{'3*eta+u': 'up_aaa_first_1'}))
        self.assertEqual(rocq.constant_names_file(ks), added)
        for other in ks.values():
            other.constant_names = None
        self.assertEqual(rocq.up_names(rocq.real(ks))['up(eta/(2*u^2))'], 'up_aaa_first_0')

    def test_a_new_name_avoids_the_recorded_ones(self):
        """A new constant whose name up_K_i the record already gives to another constant takes the
        next place."""
        text = ('kernel: ball_add_1x\ninput: a\noutput: r\nvalue: a\nensures: upper r gaps=4\n'
                'status: unverified\ncone_exempt: test\nr = prod(a, const up(5*eta+u))\n')
        k = ir.parse_kernel(text, 'ball_add_1x.kernel')
        k.name = 'ball_add_1'                  # as if the kernel had this name and a new constant
        k.constant_names = {'(1+u)^3': 'up_ball_add_1_0'}
        self.assertEqual(rocq.up_names({'ball_add_1': k}), {'up(5*eta+u)': 'up_ball_add_1_1'})


if __name__ == '__main__':
    unittest.main()
