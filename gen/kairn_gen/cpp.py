"""The C++ printer: include/kairn/gen/prelude.hpp and scalar.hpp, for double and float limbs.

This printer and the Rocq printer are the trusted part of the generator: nothing proves that the
code printed here and the model printed there describe the same computation. Both are therefore a
table of spellings plus a loop over the kernel's statements.

The emission rules come from Phase 0 measurements (docs/developer/design/phase0/environment.md and
library.md):
- One non-template function per kernel and limb type: MSVC parses a long network written as a
  function template in super-linear time.
- One operation per statement, and calls inlined (ir.flatten): Clang's default contraction fuses
  within one expression, so an expression must never hold two operations.
- A rounded product is fma(a, b, +0.0): an FMA's result is not a multiplication, so no compiler
  can contract it into a later addition. The zero is +0.0 because fma(a, b, -0.0) equals a * b
  exactly and may be folded back into one.
- A kernel is constexpr when its only fused operations are prod, or when it names a
  constant-evaluation variant: it then dispatches on __builtin_is_constant_evaluated()
  (std::is_constant_evaluated is host-only to nvcc). With a variant, the constant-evaluation branch
  is the variant's body with each prod a plain product, since constant evaluation has neither FMA
  nor contraction. Without one, each prod is the plain product in constant evaluation and the FMA
  with a +0 addend otherwise (the rule of the product, docs/developer/design/milestone2.md, "The
  two executions of a product"): as real numbers both are RN(a b), and as values of T they differ
  only in the sign of an exactly zero product. A kernel with another fused operation (fma, fms,
  fnma) and no variant is not constexpr.
- Kernels of at most two limbs are force-inlined, but one that says `ordinary_inline:` (the largest
  listings: milestone2.md, "Inlining and compile time"), which is an ordinary inline function.
- A mask is a bool, and select a conditional expression on values already computed, which
  compilers turn into a conditional move or a blend; succ and pred step the bit pattern
  (std::bit_cast is constexpr), so that kernels that use them stay constexpr.
- guard is a + 0 at run time and the operand itself in constant evaluation, where nothing is fused
  and Clang refuses NaN + 0; times_inf, exact, is a plain multiplication by infinity, so that the
  full kernels are constexpr wherever their cores are.
- The fix-up of a full kernel or a constructor is behind a branch (branch()): as selects, it puts a
  comparison and a select on the critical path of a chain of dependent operations
  (docs/developer/design/milestone1.md, "Emission", has the measurements). With Clang on AArch64,
  which turns an inline branch back into selects, the fix-up is a cold function that is never
  inlined (KAIRN_GEN_FIXUP_CALL in prelude.hpp); elsewhere it is inline. Packed code keeps the
  blends (simd.py).
"""
from dataclasses import dataclass
from fractions import Fraction

from . import consts, ir

# The limb types: precision, the literal suffix, and the format (p, qmin, qmax).
TYPES = {'double': (53, ''), 'float': (24, 'f')}
FORMATS = {'double': (53, -1074, 971), 'float': (24, -149, 104)}

# Each operation as a C++ expression of exactly one operation. {0} {1} {2} are operands (names or
# literals, never expressions) and {zero} is +0 of the limb type.
SPELL = {
    'add': '{0} + {1}',
    'sub': '{0} - {1}',
    'neg': '-{0}',
    'abs': 'abs_bits({0})',              # clears the sign bit
    'fma': 'fma_rn({0}, {1}, {2})',
    'fms': 'fma_rn({0}, {1}, -{2})',
    'fnma': 'fma_rn(-{0}, {1}, {2})',
    'prod': 'fma_rn({0}, {1}, {zero})',   # the opaque product
    'muladd': '{0} * {1} + {2}',         # the compiler may fuse it: the theorem covers both
    # a < b written b > a, a <= b written b >= a: the same in IEEE 754, NaN included, but MSVC's
    # constant evaluator (19.52) takes < and <= with a NaN operand for true, and > and >= right.
    'lt': '{1} > {0}',
    'le': '{1} >= {0}',
    'eq': '{0} == {1}',
    'and': '{0} & {1}',                  # not &&: no short circuit, no branch
    'or': '{0} | {1}',
    'not': '!{0}',
    'select': '{0} ? {1} : {2}',
    'succ': 'next_up_bits({0})',
    'pred': 'next_down_bits({0})',
    'copy': '{0}',
    # RN(a + 0). Never a - 0 or a + (-0), which are identities that compilers fold away; a + 0
    # turns -0 into +0, so a compiler that honors signed zeros keeps it.
    'guard': '{0} + {zero}',
    # t times +infinity: exact, so a plain multiplication (its result is only compared or
    # selected, rule R1).
    'times_inf': '{0} * {inf}',
}
# In constant evaluation: prod is a plain product (there is no FMA, and no contraction either),
# and guard is not evaluated (nothing is fused there, and Clang's constant evaluator refuses
# NaN + 0, which would make a NaN operand non-constant).
# times_inf there is times_inf_ce (prelude.hpp), which compares instead of multiplying: GCC and
# Clang refuse an operation that produces a NaN in constant evaluation, 0 times infinity among
# them, even where its result is not selected.
SPELL_CONSTEVAL = dict(SPELL, prod='{0} * {1}', guard='{0}', times_inf='times_inf_ce({0})')
# In a kernel that is constexpr without a variant, guard and times_inf dispatch on constant
# evaluation, as the hand-written detail::guard of include/kairn/expansion.hpp does, and so does
# prod (the rule of the product): the plain product there, the opaque product at run time.
SPELL_PLAIN = dict(SPELL, guard='__builtin_is_constant_evaluated() ? {0} : {0} + {zero}',
                   times_inf='__builtin_is_constant_evaluated() ? times_inf_ce({0}) : {0} * {inf}',
                   prod='__builtin_is_constant_evaluated() ? {0} * {1} : fma_rn({0}, {1}, {zero})')

# Names a value or a kernel must not take: keywords, alternative tokens, what the printed text
# uses, and lowercase macros that common compilers and C libraries predefine.
RESERVED = frozenset('''
    alignas alignof and and_eq asm auto bitand bitor bool break case catch char char8_t char16_t
    char32_t class compl concept const consteval constexpr constinit const_cast continue co_await
    co_return co_yield decltype default delete do double dynamic_cast else enum explicit export
    extern false float for friend goto if inline int long mutable namespace new noexcept not
    not_eq nullptr operator or or_eq private protected public register reinterpret_cast requires
    return short signed sizeof static static_assert static_cast struct switch template this
    thread_local throw true try typedef typeid typename union unsigned using virtual void volatile
    wchar_t while xor xor_eq final override import module
    kairn gen std fma_rn abs_bits next_up_bits next_down_bits times_inf_ce in out fixup result
    linux unix i386 major minor errno stdin stdout stderr assert
'''.split())

HEADER = ('// Generated by gen/kairn-gen from gen/kernels/*.kernel. Do not edit: change the\n'
          '// descriptions or gen/kairn_gen/cpp.py, then run python3 gen/kairn-gen build.')

# The prelude's macros that every header of Kairn, generated or not, puts around its own
# declarations (docs/developer/testing.md, "The program's names").
WARNINGS = [
    "// A program's global variables may have the name of any parameter or local variable of",
    "// Kairn's headers. MSVC reports each such declaration of a header at /W4 (C4459, \"declaration",
    "// hides global declaration\") and under /analyze (C6244), and GCC's -Wshadow (GCC 11 and 13, not",
    '// GCC 16) the parameters of a constructor of a class template and of a lambda. Every header of',
    '// Kairn turns these warnings off for its own declarations, from KAIRN_GEN_PUSH_WARNINGS to',
    '// KAIRN_GEN_POP_WARNINGS, and the compiler keeps that state for the templates it instantiates',
    "// later. Clang's -Wshadow, clang-cl's included, reports no declaration in a namespace that",
    '// hides a global one, so Clang gets nothing. tests/api/shadow.py defines',
    "// KAIRN_GEN_KEEP_SHADOW_WARNINGS to see the warnings for Kairn's own names.",
    '#if defined(KAIRN_GEN_KEEP_SHADOW_WARNINGS)',
    '#define KAIRN_GEN_PUSH_WARNINGS',
    '#define KAIRN_GEN_POP_WARNINGS',
    '#elif defined(_MSC_VER) && !defined(__clang__)',
    '#define KAIRN_GEN_PUSH_WARNINGS __pragma(warning(push)) __pragma(warning(disable : 4459 6244))',
    '#define KAIRN_GEN_POP_WARNINGS __pragma(warning(pop))',
    '#elif defined(__GNUC__) && !defined(__clang__)',
    '#define KAIRN_GEN_PUSH_WARNINGS _Pragma("GCC diagnostic push") _Pragma("GCC diagnostic ignored \\"-Wshadow\\"")',
    '#define KAIRN_GEN_POP_WARNINGS _Pragma("GCC diagnostic pop")',
    '#else',
    '#define KAIRN_GEN_PUSH_WARNINGS',
    '#define KAIRN_GEN_POP_WARNINGS',
    '#endif',
]


class PrintError(Exception):
    pass


def constexpr_kind(k, kernels):
    """'variant', 'plain', or None when the kernel cannot be constexpr: it has a fused operation
    other than prod and no variant. A 'plain' kernel may have prods (the rule of the product)."""
    if k.ce_variant:
        return 'variant'
    if any(p.op in ir.FUSED - {'prod'} for p in ir.prims(k, kernels)):
        return None
    return 'plain'


def product_rule(k, kernels):
    """Whether the kernel is constexpr by the rule of the product: plain, with at least one prod."""
    return constexpr_kind(k, kernels) == 'plain' and any(p.op == 'prod' for p in ir.prims(k, kernels))


def hex_literal(v, suffix):
    """A positive dyadic rational as a C99 hexadecimal literal, 0x1.8p-3."""
    m, d = v.numerator, v.denominator
    if m <= 0 or d & (d - 1):
        raise PrintError(f'{v} is not a positive dyadic rational')
    e = -(d.bit_length() - 1)
    while m % 2 == 0:
        m, e = m // 2, e + 1
    bits = m.bit_length() - 1
    digits = (bits + 3) // 4
    frac = (m - (1 << bits)) << (4 * digits - bits)
    mantissa = f'0x1.{frac:0{digits}x}' if bits else '0x1'
    return f'{mantissa}p{e + bits:+d}{suffix}'


def literal(name, kernels, ctype):
    """A constant of the format as a literal of the limb type: its exact value (consts.py), or
    +infinity and a quiet NaN from <limits> (constant expressions; there is no literal for them)."""
    if name == 'inf':
        return f'std::numeric_limits<{ctype}>::infinity()'
    if name == 'nan':
        return f'std::numeric_limits<{ctype}>::quiet_NaN()'
    suffix = TYPES[ctype][1]
    try:
        v = consts.value(name, kernels, *FORMATS[ctype])
    except consts.ConstError as e:
        raise PrintError(f'constant {name}: {e}')
    return f'0.0{suffix}' if v == 0 else hex_literal(Fraction(v), suffix)


@dataclass(frozen=True)
class Branch:
    """A kernel's fix-up behind a branch (branch()): the flattened listing split in two."""
    masks: tuple     # the masks whose conjunction the branch tests, outermost first
    arms: tuple      # per output limb, the Operand that the output equals when every mask is true
    before: list     # the items (Prim, CallMark) that the masks and the arms need, in listing order
    after: list      # every other item, in listing order: the fix-up


def branch(k, kernels):
    """How the scalar printer branches over the kernel's fix-up, or None: emitted as listed.

    The rule (docs/developer/design/milestone1.md, "Emission"). It applies to a kernel without a
    real-model statement (a full kernel, a full Ball kernel, a constructor: the kernels whose
    selects are the fix-up of the non-finite layer, written with the ordinary case as the first
    arm) whose every output is a limb defined by a select of its own listing (not of a callee's) on
    one same mask m1. The first arms are the outputs when m1 is true. While the arms are all such
    selects on one same mask m2, m2 joins the masks and the arms become their first arms. Before the branch: the operations that the masks
    and the final arms need. When every mask is true: the outputs are the final arms. Otherwise:
    every other operation, in the listing's order, and the outputs as listed. Both paths compute
    the listing's outputs: the first because every select on the way takes its first arm, the
    second because it is the listing; an operation left out of a path is one whose value that
    path does not use, and the operations have no side effects.
    """
    if k.real_model or any(kind == ir.MASK for kind in k.output_kinds):
        return None
    items = ir.flatten(k, kernels)
    defs = {it.dst: it for it in items if isinstance(it, ir.Prim)}
    # Only the kernel's own selects are a fix-up: a select inside a callee whose output is an arm
    # (the directed sum of ball_lower_as_1, Milestone 2) chooses on the data, and is computed.
    own = {st.dsts[0] for st in k.body if not st.is_call}

    def select(a):
        p = None if a.const else defs.get(a.name)
        return p if p is not None and p.op == 'select' and p.dst in own else None

    level = [select(ir.Operand(v)) for v in k.output_limbs]
    masks, arms = [], ()
    while all(level) and len({p.args[0].name for p in level}) == 1 and level[0].args[0].name not in masks:
        masks.append(level[0].args[0].name)
        arms = tuple(p.args[1] for p in level)
        level = [select(a) for a in arms]
    if not masks:
        return None
    needed = set(masks) | {a.name for a in arms if not a.const}
    for it in reversed(items):
        if isinstance(it, ir.Prim) and it.dst in needed:
            needed |= {a.name for a in it.args if not a.const}
    before, after = [], []
    for i, it in enumerate(items):
        # The comment of a call goes where the first operation of the call goes.
        first = it if isinstance(it, ir.Prim) else next(x for x in items[i:] if isinstance(x, ir.Prim))
        (before if first.dst in needed else after).append(it)
    return Branch(tuple(masks), arms, before, after)


def _statements(items, kernels, ctype, spell, pad):
    zero = '0.0' + TYPES[ctype][1]
    inf = literal('inf', kernels, ctype)
    lines = []
    for it in items:
        if isinstance(it, ir.CallMark):
            lines.append(f'{pad}// ({", ".join(it.dsts)}) = {it.callee}({", ".join(map(str, it.args))})')
            continue
        args = [literal(a.name, kernels, ctype) if a.const else a.name for a in it.args]
        vtype = ctype if ir.OPS[it.op][1] == ir.LIMB else 'bool'
        lines.append(f'{pad}const {vtype} {it.dst} = {spell[it.op].format(*args, zero=zero, inf=inf)};')
    return lines


def _operand(a, kernels, ctype):
    return literal(a.name, kernels, ctype) if a.const else a.name


def fixup_inputs(k, b):
    """The values the fix-up uses and does not compute, in the order they are defined: the
    parameters of the fix-up when it is a function of its own."""
    after = [it for it in b.after if isinstance(it, ir.Prim)]
    used = {a.name for it in after for a in it.args if not a.const} - {it.dst for it in after}
    order = list(k.input_limbs) + [it.dst for it in b.before if isinstance(it, ir.Prim)]
    return [v for v in order if v in used]


def _body(k, kernels, ctype, spell, indent):
    """The statements of the flattened kernel, one operation each; the fix-up, if the kernel has
    one, behind a branch (branch()), and with KAIRN_GEN_FIXUP_CALL a call of its function."""
    pad = ' ' * indent
    b = branch(k, kernels)
    if b is None:
        lines = _statements(ir.flatten(k, kernels), kernels, ctype, spell, pad)
        return lines + [f'{pad}{v}_out = {v};' for v in k.output_limbs]
    lines = _statements(b.before, kernels, ctype, spell, pad)
    lines.append(f'{pad}if ({" & ".join(b.masks)}) [[likely]] {{')
    lines += [f'{pad}    {v}_out = {_operand(a, kernels, ctype)};' for v, a in zip(k.output_limbs, b.arms)]
    lines.append(f'{pad}}} else {{')
    n = len(k.output_limbs)
    lines += ['#if KAIRN_GEN_FIXUP_CALL',
              f'{pad}    const fixup::result<{ctype}, {n}> fixed_ = fixup::{k.name}({", ".join(fixup_inputs(k, b))});']
    lines += [f'{pad}    {v}_out = fixed_.limb[{i}];' for i, v in enumerate(k.output_limbs)]
    lines.append('#else')
    lines += _statements(b.after, kernels, ctype, spell, pad + '    ')
    lines += [f'{pad}    {v}_out = {v};' for v in k.output_limbs]
    lines += ['#endif', f'{pad}}}']
    return lines


def fixup_function(k, kernels, ctype):
    """The fix-up as a function of its own (namespace fixup), for KAIRN_GEN_FIXUP_CALL: the
    statements of the fix-up, from the values it uses, returning the outputs."""
    b = branch(k, kernels)
    kinds = ir.kinds(k, kernels)
    kind = constexpr_kind(k, kernels)
    params = [f'{ctype if kinds[v] == ir.LIMB else "bool"} {v}' for v in fixup_inputs(k, b)]
    lines = [f'KAIRN_GEN_COLD {"constexpr " if kind == "plain" else ""}result<{ctype}, {len(k.output_limbs)}> '
             f'{k.name}({", ".join(params)}) noexcept {{']
    lines += _statements(b.after, kernels, ctype, SPELL_PLAIN if kind == 'plain' else SPELL, '    ')
    lines += [f'    return {{{{{", ".join(k.output_limbs)}}}}};', '}']
    return lines


def _check_names(k, kernels):
    names = list(k.input_limbs) + [f'{v}_out' for v in k.output_limbs]
    for kk in [k] + ([kernels[k.ce_variant]] if k.ce_variant else []):
        local = names + [p.dst for p in ir.prims(kk, kernels)]
        clash = {n for n in local if local.count(n) > 1} | (set(local) & RESERVED)
        if clash:
            raise PrintError(f'kernel {k.name}: C++ name clash: {", ".join(sorted(clash))}')


def parameters(k, limb, mask):
    """Inputs by value, outputs by reference; an input the computation ignores is marked so."""
    def vtype(kind):
        return mask if kind == ir.MASK else limb
    ins = [f'{"[[maybe_unused]] " if v in k.unused else ""}{vtype(kind)} {v}'
           for v, kind in zip(k.input_limbs, k.input_kinds)]
    return ins + [f'{vtype(kind)}& {v}_out' for v, kind in zip(k.output_limbs, k.output_kinds)]


def function(k, kernels, ctype):
    _check_names(k, kernels)
    kind = constexpr_kind(k, kernels)
    params = parameters(k, ctype, 'bool')
    inline = 'KAIRN_GEN_FORCEINLINE' if k.forced_inline else 'inline'
    lines = [f'{inline} {"constexpr " if kind else ""}void {k.name}({", ".join(params)}) noexcept {{']
    if kind == 'variant':
        v = kernels[k.ce_variant]
        lines += ['    if (__builtin_is_constant_evaluated()) {',
                  f'        // {v.name}, with each prod a plain product.']
        lines += _body(v, kernels, ctype, SPELL_CONSTEVAL, 8)
        lines += ['        return;', '    }']
    lines += _body(k, kernels, ctype, SPELL_PLAIN if kind == 'plain' else SPELL, 4)
    lines.append('}')
    return lines


def _group(g):
    if g.kind == ir.MASK:
        return f'mask {g.name}'
    return g.name if g.limbs == (g.name,) else f'{g.name} = ({", ".join(g.limbs)})'


def _description(k, kernels):
    sig = f'{k.name}({", ".join(map(_group, k.inputs))}) -> {", ".join(map(_group, k.outputs))}'
    kind = constexpr_kind(k, kernels)
    when = {'variant': f'constexpr through {k.ce_variant}', 'plain': 'constexpr',
            None: 'not constexpr: it has fused operations other than prod and no constant-evaluation '
                  'variant'}[kind]
    if product_rule(k, kernels):
        when = 'constexpr, each prod a plain product in constant evaluation'
    if not k.extended:
        status = f'Status: {k.status}'
    elif k.real_model:
        status = f'Status: {k.status} (real model), {k.ieee_status} (IEEE model)'
    else:
        status = f'Status: {k.ieee_status} (IEEE model only)'
    return [f'// {sig}', f'// {k.source or "no source given"}. {status}; {when}.']


def _helpers(kernels):
    used = {p.op for k in kernels.values() for p in ir.prims(k, kernels)}
    return used & {'abs', 'succ', 'pred', 'times_inf'}


def uses_special(kernels):
    """Whether a kernel names +infinity or NaN, or multiplies by infinity: they come from <limits>."""
    return any((a.const and a.name in ir.SPECIAL) or st.op == 'times_inf'
               for k in kernels.values() for st in k.body for a in st.args)


def prelude(kernels):
    helpers = _helpers(kernels)
    lines = [HEADER, '//',
             '// What the generated kernels need, and nothing else.',
             '#pragma once', '',
             '#if defined(_MSC_VER) && !defined(__clang__) && (defined(_M_X64) || defined(_M_IX86))',
             '#include <immintrin.h>',
             '#endif']
    if helpers & {'abs', 'succ', 'pred'}:
        lines += ['#include <bit>', '#include <cstdint>']
    if uses_special(kernels):
        lines += ['#include <limits>']
    lines += ['',
              '// Kernels of at most two limbs are a few dozen flops and must disappear into the caller.',
              '#if defined(_MSC_VER) && !defined(__clang__)',
              '#define KAIRN_GEN_FORCEINLINE __forceinline',
              '#else',
              '#define KAIRN_GEN_FORCEINLINE inline __attribute__((always_inline))',
              '#endif',
              ''] + WARNINGS + ['']
    fixups = any(branch(k, kernels) for k in kernels.values())
    if fixups:
        lines += ['// Where a scalar kernel puts the fix-up that it runs behind a branch',
                  '// (docs/developer/design/milestone1.md, "Emission"): inline, except with Clang on AArch64,',
                  '// which turns an inline branch back into selects; there the fix-up is a function of its own',
                  '// that is never inlined. The tests set KAIRN_GEN_FIXUP_CALL to build either form anywhere.',
                  '#if !defined(KAIRN_GEN_FIXUP_CALL)',
                  '#if defined(__clang__) && defined(__aarch64__)',
                  '#define KAIRN_GEN_FIXUP_CALL 1',
                  '#else',
                  '#define KAIRN_GEN_FIXUP_CALL 0',
                  '#endif',
                  '#endif',
                  '#if KAIRN_GEN_FIXUP_CALL',
                  '#if defined(_MSC_VER) && !defined(__clang__)',
                  '#define KAIRN_GEN_COLD inline __declspec(noinline)',
                  '#else',
                  '#define KAIRN_GEN_COLD inline __attribute__((noinline, cold))',
                  '#endif',
                  '#endif',
                  '']
    lines += ['// Every theorem assumes that fma_rn is one rounding, done by the hardware. Without the',
              '// instruction the builtin becomes a library call, and the intrinsic an illegal instruction.',
              '#if (defined(__x86_64__) || defined(__i386__)) && !defined(__FMA__)',
              '#error "Kairn needs hardware FMA: compile for an x86 CPU that has it (-mfma, -march=haswell or later)"',
              '#endif',
              '#if defined(_MSC_VER) && !defined(__clang__) && (defined(_M_X64) || defined(_M_IX86)) && !defined(__AVX2__)',
              '#error "Kairn needs hardware FMA: compile with /arch:AVX2 or later"',
              '#endif',
              '#if defined(_MSC_VER) && !defined(__clang__) && !defined(_M_X64) && !defined(_M_IX86)',
              '#error "Kairn: no FMA primitive has been chosen and measured for MSVC on this architecture"',
              '#endif',
              '',
              'KAIRN_GEN_PUSH_WARNINGS',
              'namespace kairn::gen {',
              '']
    if fixups:
        lines += ['#if KAIRN_GEN_FIXUP_CALL',
                  '// The outputs of a fix-up that is a function of its own, returned by value: through a',
                  '// reference, the caller\'s variables would have their address taken.',
                  'namespace fixup {',
                  'template <class T, int N>',
                  'struct result {',
                  '    T limb[N];',
                  '};',
                  '}  // namespace fixup',
                  '#endif',
                  '']
    lines += ['// RN(a b + c) with one rounding. Not std::fma: MSVC compiles it to a library call under',
              '// /fp:strict and /Od. GCC and Clang lower the builtin to the instruction. Never called in',
              '// constant evaluation.']
    for ctype, sd, cvt, builtin in (('double', 'sd', '_mm_cvtsd_f64', '__builtin_fma'),
                                    ('float', 'ss', '_mm_cvtss_f32', '__builtin_fmaf')):
        lines += [f'KAIRN_GEN_FORCEINLINE {ctype} fma_rn({ctype} a, {ctype} b, {ctype} c) noexcept {{',
                  '#if defined(_MSC_VER) && !defined(__clang__)',
                  f'    return {cvt}(_mm_fmadd_{sd}(_mm_set_{sd}(a), _mm_set_{sd}(b), _mm_set_{sd}(c)));',
                  '#else',
                  f'    return {builtin}(a, b, c);',
                  '#endif',
                  '}']
    for ctype, utype, sign, inf, bits, neg_eta in (
            ('double', 'std::uint64_t', '0x7fffffffffffffffu', '0x7ff0000000000000u', 64, '0x8000000000000001u'),
            ('float', 'std::uint32_t', '0x7fffffffu', '0x7f800000u', 32, '0x80000001u')):
        if 'abs' in helpers:
            lines += ['',
                      '// |a|, exactly, by clearing the sign bit (std::fabs is not constexpr in C++20).',
                      f'KAIRN_GEN_FORCEINLINE constexpr {ctype} abs_bits({ctype} a) noexcept {{',
                      f'    return std::bit_cast<{ctype}>(std::bit_cast<{utype}>(a) & {sign});',
                      '}']
        if helpers & {'succ', 'pred'}:
            lines += ['',
                      '// IEEE 754 nextUp and nextDown, by stepping the bit pattern: nextafter is not',
                      '// constexpr in C++20, and not usable in CUDA device code. The pattern of a',
                      '// positive number moves up, that of a negative one towards zero; either zero',
                      '// becomes the smallest subnormal; NaN and +inf stay. The choices are masks of',
                      '// all ones or all zeros, each from one comparison: written with ?: or ||, GCC',
                      '// and Clang emit branches on the data. m + (s ^ 1) exceeds inf exactly for NaN',
                      '// and +inf (it is m + 1 for a positive pattern, m for a negative one).',
                      f'KAIRN_GEN_FORCEINLINE constexpr {ctype} next_up_bits({ctype} a) noexcept {{',
                      f'    const {utype} b = std::bit_cast<{utype}>(a);',
                      f'    const {utype} m = b & {sign};',
                      f'    const {utype} s = b >> {bits - 1};',
                      f'    const {utype} step = b + 1 - (s << 1);  // b + 1, or b - 1 for a negative pattern',
                      f'    const {utype} zero = {utype}{{0}} - {utype}(m == 0);',
                      f'    const {utype} keep = {utype}{{0}} - {utype}(m + (s ^ 1) > {inf});',
                      f'    const {utype} r = (zero & 1) | (~zero & step);',
                      f'    return std::bit_cast<{ctype}>((keep & b) | (~keep & r));',
                      '}',
                      '// nextDown mirrors it, with no negation of a value of the type: written as',
                      '// -next_up_bits(-a), a compiler folds the negation of an FMA result into a negated',
                      '// FMA (fnmadd), one fused operation more than the listing has (pred(p) in',
                      '// mul_down_1). The pattern of a positive number moves towards zero, that of a',
                      '// negative one down; either zero becomes -eta; NaN and -inf stay (m + s exceeds inf',
                      '// exactly for them).',
                      f'KAIRN_GEN_FORCEINLINE constexpr {ctype} next_down_bits({ctype} a) noexcept {{',
                      f'    const {utype} b = std::bit_cast<{utype}>(a);',
                      f'    const {utype} m = b & {sign};',
                      f'    const {utype} s = b >> {bits - 1};',
                      f'    const {utype} step = b - 1 + (s << 1);  // b - 1, or b + 1 for a negative pattern',
                      f'    const {utype} zero = {utype}{{0}} - {utype}(m == 0);',
                      f'    const {utype} keep = {utype}{{0}} - {utype}(m + s > {inf});',
                      f'    const {utype} r = (zero & {neg_eta}) | (~zero & step);',
                      f'    return std::bit_cast<{ctype}>((keep & b) | (~keep & r));',
                      '}']
        if 'times_inf' in helpers:
            limits = f'std::numeric_limits<{ctype}>'
            lines += ['',
                      '// t times +infinity in constant evaluation, from comparisons alone: GCC and Clang',
                      '// refuse an operation that produces a NaN there, 0 times infinity among them, even',
                      '// where its result is not selected. At run time a kernel multiplies (times_inf).',
                      '// Only > compares: MSVC\'s constant evaluator takes < with a NaN for true.',
                      f'KAIRN_GEN_FORCEINLINE constexpr {ctype} times_inf_ce({ctype} t) noexcept {{',
                      f'    return t > 0 ? {limits}::infinity() : 0 > t ? -{limits}::infinity() : {limits}::quiet_NaN();',
                      '}']
    lines += ['', '}  // namespace kairn::gen', 'KAIRN_GEN_POP_WARNINGS']
    return '\n'.join(lines) + '\n'


# --- Folds -----------------------------------------------------------------------------------------
#
# A fold (milestone2.md, "Folds, the extension of the IR") is a loop of kernels along arrays, one
# pointer per limb array and a length, no allocation. Its functions are ordinary inline functions,
# not forced inline ("Inlining and compile time"): F_seq, the sequential order; F_lanes, the lane
# order for a number of lanes given at run time, the reference that the packed form F_packed of
# simd.py computes with the lanes of a register. The step, the combination and the finish are
# inlined in the loop as calls are inlined in a kernel (ir.inline_call): every value they define
# is named PREFIX_V, PREFIX being step, comb or fin, and the names of the loop's own variables end
# with an underscore, so that neither can be a name of the fold, which have none. Nothing in them
# is constexpr: a loop over pointers is no constant expression of use, and the packed form cannot
# be one.

STEP, COMB, FIN = 'step', 'comb', 'fin'


def fold_kernels(fd, kernels):
    """The step, the combination and the finish of a fold (None for those it has not)."""
    return tuple(kernels[c[0]] if c else None for c in (fd.step, fd.combine, fd.finish))


def loaded_limbs(fd, kernels):
    """The limb arrays whose entries the step uses: not those passed to an input that the step
    declares unused (norm_step_2's x1: the second limb of a pair, which the finish's step up
    covers). The others are parameters all the same, [[maybe_unused]], and are not loaded."""
    step = kernels[fd.step[0]]
    by_arg = dict(zip(fd.step[1], step.inputs))
    return [v for g in fd.arrays for v, w in zip(g.limbs, by_arg[g.name].limbs) if w not in step.unused]


def fold_parameters(fd, limb, mask, lanes, kernels=None):
    """One pointer per limb array, the length, the number of lanes (F_lanes), the results by
    reference."""
    loaded = loaded_limbs(fd, kernels) if kernels is not None else fd.array_limbs()
    ps = [f'{"" if v in loaded else "[[maybe_unused]] "}const {limb}* {v}_in' for v in fd.array_limbs()] + \
        ['std::size_t n']
    if lanes:
        ps.append('std::size_t lanes')
    return ps + [f'{mask if g.kind == ir.MASK else limb}& {v}_out' for g in fd.results() for v in g.limbs]


def step_arguments(fd, state, elements):
    """The step's operands, value by value: `state` the names of the state's limbs (every group of
    it, in order), `elements` {array: the names of its limbs}, in the order of the step's
    arguments."""
    groups, at = dict(elements), 0
    for g in fd.states:
        groups[g.name] = state[at:at + len(g.limbs)]
        at += len(g.limbs)
    return [v for a in fd.step[1] for v in groups[a]]


def state_declarations(fd, ctype, names, pad):
    """The variables of a state, from the zero state: every limb +0 and every mask true."""
    return [f'{pad}bool {v} = true;' if kind == ir.MASK else f'{pad}{ctype} {v} = {_zero(ctype)};'
            for v, kind in zip(names, fd.state_kinds())]


def _call(k, kernels, ctype, args, prefix, pad):
    """The statements of one inlined call of k on `args` (names), and the names of its outputs."""
    items, outs = ir.inline_call(k, kernels, [ir.Operand(a) for a in args], prefix)
    return _statements(items, kernels, ctype, SPELL, pad), outs


def _assign(names, values, pad):
    return [f'{pad}{n} = {v};' for n, v in zip(names, values)]


def fold_finish_lines(fd, kernels, ctype, state, pad='    '):
    """The finish on the final state, and the results stored."""
    _, _, finish = fold_kernels(fd, kernels)
    outs = [f'{v}_out' for g in fd.results() for v in g.limbs]
    if finish is None:
        return _assign(outs, state, pad)
    lines, vals = _call(finish, kernels, ctype, state, FIN, pad)
    return lines + _assign(outs, vals, pad)


def fold_step_loop(fd, kernels, ctype, state, start, pad='    '):
    """`for (i_ = START; i_ < n; ++i_)` the scalar step on the state variables `state`."""
    step, _, _ = fold_kernels(fd, kernels)
    lines = [f'{pad}for (std::size_t i_ = {start}; i_ < n; ++i_) {{']
    inner = pad + '    '
    lines += [f'{inner}const {ctype} {v} = {v}_in[i_];' for v in loaded_limbs(fd, kernels)]
    body, outs = _call(step, kernels, ctype, step_arguments(fd, state, {g.name: list(g.limbs) for g in fd.arrays}),
                       STEP, inner)
    return lines + body + _assign(state, outs, inner) + [f'{pad}}}']


def _zero(ctype):
    return '0.0' + TYPES[ctype][1]


def fold_description(fd, kernels, order):
    step, combine, finish = fold_kernels(fd, kernels)
    arrays = ', '.join(f'{fd.roles[g.name]} {g.name} = ({", ".join(g.limbs)})' if len(g.limbs) > 1
                       else f'{fd.roles[g.name]} {g.name}' for g in fd.arrays)
    parts = f'step {step.name}' + (f', combination {combine.name}' if combine else '') + \
            (f', finish {finish.name}' if finish else '')
    what = {'seq': 'the sequential order (fold_seq of proofs/theories/Folds.v)',
            'lanes': 'the lane order (fold_lanes) with `lanes` lanes, computed one lane after another',
            'packed': 'the lane order (fold_lanes) with the lanes of a register'}[order]
    return [f'// fold {fd.name}({arrays}), {parts}: {what}. Status: {fd.status}.']


def fold_seq(fd, kernels, ctype):
    """The sequential order: the state after element i is the step on the state after element
    i - 1, from the zero state."""
    state = fd.state_limbs()
    lines = fold_description(fd, kernels, 'seq')
    lines.append(f'inline void {fd.name}_seq({", ".join(fold_parameters(fd, ctype, "bool", False, kernels))}) noexcept {{')
    lines += state_declarations(fd, ctype, state, '    ')
    lines += fold_step_loop(fd, kernels, ctype, state, '0')
    return lines + fold_finish_lines(fd, kernels, ctype, state) + ['}']


def fold_lanes(fd, kernels, ctype):
    """The lane order of Folds.v for W = lanes: the first W (n / W) elements, element i to lane
    i mod W; each lane folded sequentially from the zero state; the lanes combined from lane 0
    upward, ((l0 + l1) + l2) + ...; then the remaining elements folded sequentially into the
    result. The lanes are folded one after the other, each combined as soon as it is done, so that
    nothing is stored but the state and one lane's: the same operations, in the same order, as
    the definition. With no lane the result is the sequential order."""
    step, combine, _ = fold_kernels(fd, kernels)
    state = fd.state_limbs()
    lane = [f'{v}_lane_' for v in state]
    elements = {g.name: list(g.limbs) for g in fd.arrays}
    lines = fold_description(fd, kernels, 'lanes')
    lines.append(f'inline void {fd.name}_lanes({", ".join(fold_parameters(fd, ctype, "bool", True, kernels))}) noexcept {{')
    lines.append('    const std::size_t full_ = lanes == 0 ? 0 : n - n % lanes;')
    lines += state_declarations(fd, ctype, state, '    ')
    lines.append('    for (std::size_t j_ = 0; j_ < lanes; ++j_) {')
    lines += state_declarations(fd, ctype, lane, '        ')
    lines.append('        for (std::size_t i_ = j_; i_ < full_; i_ += lanes) {')
    lines += [f'            const {ctype} {v} = {v}_in[i_];' for v in loaded_limbs(fd, kernels)]
    body, outs = _call(step, kernels, ctype, step_arguments(fd, lane, elements), STEP, ' ' * 12)
    lines += body + _assign(lane, outs, ' ' * 12) + ['        }', '        if (j_ == 0) {']
    lines += _assign(state, lane, ' ' * 12) + ['        } else {']
    body, outs = _call(combine, kernels, ctype, state + lane, COMB, ' ' * 12)
    lines += body + _assign(state, outs, ' ' * 12) + ['        }', '    }']
    lines += fold_step_loop(fd, kernels, ctype, state, 'full_')
    return lines + fold_finish_lines(fd, kernels, ctype, state) + ['}']


# --- Maps -----------------------------------------------------------------------------------------
#
# A map (rules.py, "Maps") writes one element of an array per element it reads: z[i] is the step
# on the scalars and element i, whatever the order. The mask starts true and is the and of the
# check's flag on every element written; when it is false at the end, a second pass rewrites every
# element as the check returns it (the canonical NaN for one that is not finite), and the mask is
# returned. Aliasing: each array written may be exactly one of the arrays read (the same pointer:
# z = x or z = y, in place), since an element is read whole before it is written and nothing else
# reads it; otherwise it overlaps no array read or written. An array that partly overlaps another
# is not supported.

CHECK = 'chk'


def needed(items, outs):
    """The items of an inlined call that the values `outs` need, in order: what is computed and not
    used (the canonical NaN of the check, in the first pass) is left out, as an unused value would
    be a warning."""
    need = set(outs)
    keep = []
    for it in reversed(items):
        if isinstance(it, ir.CallMark):
            if set(it.dsts) & need:
                keep.append(it)
            continue
        if it.dst in need:
            keep.append(it)
            need.update(a.name for a in it.args if not a.const)
    return list(reversed(keep))


def map_parameters(fd, limb, mask, lanes):
    """One pointer per limb array read, the length, the number of lanes (F_lanes), the scalars by
    value, one pointer per limb array written, the mask by reference."""
    ps = [f'const {limb}* {v}_in' for v in fd.array_limbs()] + ['std::size_t n']
    if lanes:
        ps.append('std::size_t lanes')
    ps += [f'{limb} {v}' for v in fd.scalar_limbs()]
    ps += [f'{limb}* {v}_out' for v in fd.write_limbs()]
    return ps + [f'{mask}& {v}_out' for v in fd.state.limbs]


def map_arguments(fd, elements):
    """The step's operands, value by value: the scalars' limbs and the elements' (`elements`)."""
    groups = dict(elements)
    groups.update({g.name: list(g.limbs) for g in fd.scalars})
    return [v for a in fd.step[1] for v in groups[a]]


def map_element(fd, kernels, ctype, mask, pad, state):
    """The statements for element i_: its limbs loaded, the step, the element written, the check's
    flag and-ed into the mask variable `state`."""
    step, check = kernels[fd.step[0]], kernels[fd.check]
    lines = [f'{pad}const {ctype} {v} = {v}_in[i_];' for v in fd.array_limbs()]
    body, outs = _call(step, kernels, ctype, map_arguments(fd, {g.name: list(g.limbs) for g in fd.arrays}),
                       STEP, pad)
    lines += body + [f'{pad}{v}_out[i_] = {o};' for v, o in zip(fd.write_limbs(), outs)]
    items, couts = ir.inline_call(check, kernels, [ir.Operand(o) for o in outs], CHECK)
    lines += _statements(needed(items, couts[-1:]), kernels, ctype, SPELL, pad)
    return lines + [f'{pad}{state} = {SPELL["and"].format(state, couts[-1])};']


def map_second_pass(fd, kernels, ctype, pad='    ', length='n'):
    """When the mask is false: every element written, again, as the check returns it."""
    check = kernels[fd.check]
    state = fd.state.limbs[0]
    inner = pad + '        '
    lines = [f'{pad}if (!{state}) {{', f'{pad}    for (std::size_t i_ = 0; i_ < {length}; ++i_) {{']
    lines += [f'{inner}const {ctype} {v} = {v}_out[i_];' for v in fd.write_limbs()]
    body, outs = _call(check, kernels, ctype, fd.write_limbs(), CHECK, inner)
    lines += [x for x in body] + [f'{inner}{v}_out[i_] = {o};' for v, o in zip(fd.write_limbs(), outs[:-1])]
    return lines + [f'{pad}    }}', f'{pad}}}', f'{pad}{state}_out = {state};']


def map_description(fd, kernels, order):
    step, check = kernels[fd.step[0]], kernels[fd.check]
    def part(g):
        return f'{fd.roles[g.name]} {g.name}' + (f' = ({", ".join(g.limbs)})' if len(g.limbs) > 1 else '')
    what = {'seq': 'element after element', 'lanes': 'in the lane order with `lanes` lanes, one lane after '
            'another', 'packed': 'in the lane order with the lanes of a register'}[order]
    reads = ', '.join(part(g) for g in fd.arrays + fd.scalars)
    w = fd.writes[0]
    return [f'// map {fd.name}({reads}) -> {w.name}' + (f' = ({", ".join(w.limbs)})' if len(w.limbs) > 1 else '')
            + f', step {step.name}, check {check.name}: {what}. A written array is exactly one of the',
            '// arrays read (in place) or overlaps none of them, nor another written one. Status: '
            f'{fd.status}.']


def map_seq(fd, kernels, ctype):
    state = fd.state.limbs[0]
    lines = map_description(fd, kernels, 'seq')
    lines.append(f'inline void {fd.name}_seq({", ".join(map_parameters(fd, ctype, "bool", False))}) noexcept {{')
    lines += [f'    bool {state} = true;', '    for (std::size_t i_ = 0; i_ < n; ++i_) {']
    lines += map_element(fd, kernels, ctype, 'bool', ' ' * 8, state) + ['    }']
    return lines + map_second_pass(fd, kernels, ctype) + ['}']


def map_lanes(fd, kernels, ctype):
    """The lane order, as fold_lanes: lane j_ the elements j_, j_ + lanes, ... of the first
    lanes (n / lanes), its mask from true; the masks of the lanes and-ed from lane 0 upward; then
    the rest. The elements written are those of the sequential order, and so is the mask."""
    state = fd.state.limbs[0]
    lane = f'{state}_lane_'
    lines = map_description(fd, kernels, 'lanes')
    lines.append(f'inline void {fd.name}_lanes({", ".join(map_parameters(fd, ctype, "bool", True))}) noexcept {{')
    lines += ['    const std::size_t full_ = lanes == 0 ? 0 : n - n % lanes;',
              f'    bool {state} = true;',
              '    for (std::size_t j_ = 0; j_ < lanes; ++j_) {',
              f'        bool {lane} = true;',
              '        for (std::size_t i_ = j_; i_ < full_; i_ += lanes) {']
    lines += map_element(fd, kernels, ctype, 'bool', ' ' * 12, lane)
    lines += ['        }', f'        {state} = j_ == 0 ? {lane} : {SPELL["and"].format(state, lane)};', '    }',
              '    for (std::size_t i_ = full_; i_ < n; ++i_) {']
    lines += map_element(fd, kernels, ctype, 'bool', ' ' * 8, state) + ['    }']
    return lines + map_second_pass(fd, kernels, ctype) + ['}']


# --- Convolutions -----------------------------------------------------------------------------------
#
# A convolution (rules.py, "Convolutions") writes the n_x + n_y - 1 coefficients of the product of
# two polynomials: for each j, the state of the fold of its coefficients from the zero state, its
# step on the terms (x_i, y_(j-i)) for i from max(0, j - n_y + 1) to min(j, n_x - 1) in increasing
# order, written as the coefficient and tested by the check, the flags and-ed into the mask; then the
# second pass of a map. Each array has its length, n_ and its name. Aliasing: the array written
# overlaps neither array read (a coefficient reads several entries of each), nor itself.

def conv_parameters(fd, limb, mask):
    """Each array read, one pointer per limb and its length; one pointer per limb array written;
    the mask by reference."""
    ps = []
    for g in fd.arrays:
        ps += [f'const {limb}* {v}_in' for v in g.limbs] + [f'std::size_t n_{g.name}']
    ps += [f'{limb}* {v}_out' for v in fd.write_limbs()]
    return ps + [f'{mask}& {v}_out' for v in fd.state.limbs]


def conv_description(fd, kernels):
    cf = kernels.folds[fd.coefficients]
    x, y = fd.arrays
    w = fd.writes[0]

    def part(g):
        return f'{fd.roles[g.name]} {g.name}' + (f' = ({", ".join(g.limbs)})' if len(g.limbs) > 1 else '')
    return [f'// convolution {fd.name}({part(x)}, {part(y)}) -> {w.name}' +
            (f' = ({", ".join(w.limbs)})' if len(w.limbs) > 1 else '') +
            f': coefficient j, of n_{x.name} + n_{y.name} - 1 (none when a length is 0), is the fold {cf.name} in its',
            f'// sequential order on the terms ({x.name}_i, {y.name}_(j-i)), i increasing, checked by {fd.check}. '
            f'The array written',
            f'// overlaps neither {x.name} nor {y.name}. Status: {fd.status}.']


def conv_seq(fd, kernels, ctype):
    cf = kernels.folds[fd.coefficients]
    step, check = kernels[cf.step[0]], kernels[fd.check]
    x, y = fd.arrays
    state = cf.state_limbs()
    mask = fd.state.limbs[0]
    lines = conv_description(fd, kernels)
    lines.append(f'inline void {fd.name}_seq({", ".join(conv_parameters(fd, ctype, "bool"))}) noexcept {{')
    lines += [f'    const std::size_t nz_ = n_{x.name} == 0 || n_{y.name} == 0 ? 0 : n_{x.name} + n_{y.name} - 1;',
              f'    bool {mask} = true;',
              '    for (std::size_t j_ = 0; j_ < nz_; ++j_) {']
    lines += state_declarations(cf, ctype, state, ' ' * 8)
    lines += [f'        const std::size_t lo_ = j_ < n_{y.name} ? 0 : j_ - (n_{y.name} - 1);',
              f'        const std::size_t hi_ = j_ < n_{x.name} ? j_ : n_{x.name} - 1;',
              '        for (std::size_t i_ = lo_; i_ <= hi_; ++i_) {']
    lines += [f'            const {ctype} {v} = {v}_in[i_];' for v in x.limbs]
    lines += [f'            const {ctype} {v} = {v}_in[j_ - i_];' for v in y.limbs]
    body, outs = _call(step, kernels, ctype, step_arguments(cf, state, {g.name: list(g.limbs) for g in fd.arrays}),
                       STEP, ' ' * 12)
    lines += body + _assign(state, outs, ' ' * 12) + ['        }']
    lines += [f'        {v}_out[j_] = {s};' for v, s in zip(fd.write_limbs(), state)]
    items, couts = ir.inline_call(check, kernels, [ir.Operand(s) for s in state], CHECK)
    lines += _statements(needed(items, couts[-1:]), kernels, ctype, SPELL, ' ' * 8)
    lines += [f'        {mask} = {SPELL["and"].format(mask, couts[-1])};', '    }']
    return lines + map_second_pass(fd, kernels, ctype, length='nz_') + ['}']


def folds(kernels):
    """The scalar functions of every fold, for both limb types."""
    lines = []
    for fd in getattr(kernels, 'folds', {}).values():
        printers = ((('sequential', map_seq), ('lanes', map_lanes)) if fd.is_map else
                    (('sequential', conv_seq),) if fd.is_conv else
                    (('sequential', fold_seq), ('lanes', fold_lanes)))
        for order, printer in printers:
            if order in fd.orders:
                lines.append('')
                for i, ctype in enumerate(TYPES):
                    lines += printer(fd, kernels, ctype)[(1 if i else 0):]   # the description once
    return lines


def scalar(kernels, prelude_name='prelude.hpp'):
    plain = [k.name for k in kernels.values() if constexpr_kind(k, kernels) is None]
    lines = [HEADER, '//',
             '// Scalar kernels for double and float limbs (docs/developer/architecture.md, "The kernel',
             '// IR"). Inputs are passed by value; outputs by reference, each written once on the path',
             '// taken. Values keep the names of the kernel descriptions; a value inlined from a call is',
             '// named SITE_VALUE, where SITE is the first value the call defines. The fix-up of a full',
             '// kernel or a constructor is behind a branch: the listing\'s operations that its masks and',
             '// the first arms of its selects need come first; when the masks are true the outputs are',
             '// those arms; otherwise the rest of the listing runs (docs/developer/design/milestone1.md,',
             '// "Emission").',
             f'// Not constexpr: {", ".join(plain) if plain else "none"}.',
             '#pragma once', '']
    if getattr(kernels, 'folds', {}):
        lines += ['#include <cstddef>', '']
    lines += [f'#include "{prelude_name}"', '',
              'KAIRN_GEN_PUSH_WARNINGS',
              'namespace kairn::gen {']
    for k in kernels.values():
        lines += [''] + _description(k, kernels)
        if branch(k, kernels):
            lines += ['#if KAIRN_GEN_FIXUP_CALL', 'namespace fixup {']
            for ctype in TYPES:
                lines += fixup_function(k, kernels, ctype)
            lines += ['}  // namespace fixup', '#endif']
        for ctype in TYPES:
            lines += function(k, kernels, ctype)
    if getattr(kernels, 'folds', {}):
        lines += ['', '// --- Folds: loops of the kernels above along arrays (docs/developer/architecture.md, "Folds").',
                  '// One pointer per limb array and a length; nothing is allocated. Ordinary inline functions,',
                  '// the step inlined in the loop: a value of the step is named step_V, of the combination comb_V,',
                  '// of the finish fin_V; the loop\'s own variables end with an underscore.']
        lines += folds(kernels)
    lines += ['', '}  // namespace kairn::gen', 'KAIRN_GEN_POP_WARNINGS']
    return '\n'.join(lines) + '\n'


def runner_table(kernels):
    """One line per kernel for the runners of gen/tests: name, the kind of each input and output
    value (l a limb, m a mask), and the call. Limbs are in[i] and out[i], masks mi[i] and mo[i],
    i being the value's position among the inputs or the outputs."""
    lines = ['// Generated by gen/kairn-gen. Do not edit.',
             '// The kernels the runners of gen/tests can run: name, input and output kinds (l: limb,',
             '// m: mask), the call.']
    for k in kernels.values():
        def kinds(ks):
            return ''.join('m' if kind == ir.MASK else 'l' for kind in ks)
        args = [f'{"mi" if kind == ir.MASK else "in"}[{i}]' for i, kind in enumerate(k.input_kinds)]
        args += [f'{"mo" if kind == ir.MASK else "out"}[{i}]' for i, kind in enumerate(k.output_kinds)]
        lines.append(f'KAIRN_RUNNER_KERNEL({k.name}, "{kinds(k.input_kinds)}", "{kinds(k.output_kinds)}", '
                     f'kairn::gen::{k.name}({", ".join(args)}))')
    folds = getattr(kernels, 'folds', {})
    if folds:
        lines += ['// The folds, for a runner that defines KAIRN_RUNNER_FOLD: name, the limbs of each array, the',
                  '// output kinds, the calls of the sequential order, of the lane order with `lanes` lanes, and of',
                  '// its packed form (avx2.hpp or neon.hpp). in[i] is limb array i (const T*), n the length,',
                  '// out[i] and mo[i] the outputs by position, as above.',
                  '#if defined(KAIRN_RUNNER_FOLD)']
        for fd in folds.values():
            if fd.is_map or fd.is_conv:
                continue
            args = [f'in[{i}]' for i in range(len(fd.array_limbs()))]
            outs = [f'{"mo" if g.kind == ir.MASK else "out"}[{i}]'
                    for i, g in enumerate(g for g in fd.results() for _ in g.limbs)]
            kinds = ''.join('m' if g.kind == ir.MASK else 'l' for g in fd.results() for _ in g.limbs)
            calls = []
            for order, suffix, extra in (('sequential', 'seq', []), ('lanes', 'lanes', ['lanes']),
                                         ('lanes', 'packed', [])):
                calls.append(f'kairn::gen::{fd.name}_{suffix}({", ".join(args + ["n"] + extra + outs)})'
                             if order in fd.orders else '(void)0')
            lines.append(f'KAIRN_RUNNER_FOLD({fd.name}, "{"".join(str(len(g.limbs)) for g in fd.arrays)}", '
                         f'"{kinds}", {", ".join(calls)})')
        lines.append('#endif')
    maps = [fd for fd in folds.values() if fd.is_map]
    if maps:
        lines += ['// The maps, for a runner that defines KAIRN_RUNNER_MAP: name, the limbs of each array read, the',
                  '// number of scalar limbs, the number of limb arrays written, the calls of the sequential order,',
                  '// the lane order and its packed form. in[i] is limb array i read (const T*), n the length, sc[i]',
                  '// scalar limb i (T), w[i] limb array i written (T*), mo[0] the mask.',
                  '#if defined(KAIRN_RUNNER_MAP)']
        for fd in maps:
            args = [f'in[{i}]' for i in range(len(fd.array_limbs()))]
            rest = [f'sc[{i}]' for i in range(len(fd.scalar_limbs()))] + \
                [f'w[{i}]' for i in range(len(fd.write_limbs()))] + ['mo[0]']
            calls = []
            for order, suffix, extra in (('sequential', 'seq', []), ('lanes', 'lanes', ['lanes']),
                                         ('lanes', 'packed', [])):
                calls.append(f'kairn::gen::{fd.name}_{suffix}({", ".join(args + ["n"] + extra + rest)})'
                             if order in fd.orders else '(void)0')
            lines.append(f'KAIRN_RUNNER_MAP({fd.name}, "{"".join(str(len(g.limbs)) for g in fd.arrays)}", '
                         f'{len(fd.scalar_limbs())}, {len(fd.write_limbs())}, {", ".join(calls)})')
        lines.append('#endif')
    convs = [fd for fd in folds.values() if fd.is_conv]
    if convs:
        lines += ['// The convolutions, for a runner that defines KAIRN_RUNNER_CONV: name, the limbs of each array',
                  '// read, the number of limb arrays written, the call of the sequential order. in[i] is limb array',
                  '// i read (const T*), the limbs of the first array before those of the second, nx and ny their',
                  '// lengths, w[i] limb array i written (T*), mo[0] the mask.',
                  '#if defined(KAIRN_RUNNER_CONV)']
        for fd in convs:
            x, y = fd.arrays
            args = [f'in[{i}]' for i in range(len(x.limbs))] + ['nx']
            args += [f'in[{len(x.limbs) + i}]' for i in range(len(y.limbs))] + ['ny']
            args += [f'w[{i}]' for i in range(len(fd.write_limbs()))] + ['mo[0]']
            lines.append(f'KAIRN_RUNNER_CONV({fd.name}, "{"".join(str(len(g.limbs)) for g in fd.arrays)}", '
                         f'{len(fd.write_limbs())}, kairn::gen::{fd.name}_seq({", ".join(args)}))')
        lines.append('#endif')
    return '\n'.join(lines) + '\n'
