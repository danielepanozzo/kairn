"""gen/objcode.json: what the compiled code of every kernel may contain, for the object-code check.

The check (tests/objcode/objcode.py; docs/developer/testing.md, "Object code") compiles every
kernel with a client's compiler and flags and counts two kinds of instructions in the object code:
fused multiply-adds and plain floating-point multiplications. This file says, from the IR that the
C++ and the proofs are printed from, how many of each the printed code asks for; the check's rule,
which says how those numbers must relate to what is found, is in objcode.py.

The forms of a kernel's C++, each one function, or two:

- `scalar`: scalar.hpp with the fix-up inline (KAIRN_GEN_FIXUP_CALL 0);
- `scalar_call`: scalar.hpp with KAIRN_GEN_FIXUP_CALL 1: the kernel and, where it has a fix-up
  behind a branch (cpp.branch), the function fixup::K that it calls;
- `packed`: avx2.hpp and neon.hpp, in which every select is a blend.

For each form and limb type:

- `fma`, `mul`: the operations printed as a fused multiply-add (fma, fms, fnma, prod: ir.FUSED)
  and as a plain multiplication (times_inf, a product with +infinity: exact, and only compared or
  selected, rule R1), one per node of the flattened listing. Every form prints every operation of
  the listing exactly once: the two paths of a fix-up split the listing, they do not repeat it.
- `fma_distinct`, `mul_distinct`: the same with the operations of one function that compute the
  same thing from the same operands counted once, as a compiler that eliminates common
  subexpressions may. The same thing means the same operation up to the order of the two factors
  of a product and of the operands of a sum, an `fms` being an FMA of the negated addend, an
  `fnma` one of the negated product, a `prod` one with the addend +0; and constants are the same
  when their literals of the limb type are. In `scalar_call` the kernel and its fix-up are two
  functions, numbered apart: the fix-up receives what it uses as parameters.
- `consteval_mul`: the plain multiplications of the branch that a kernel with a
  constant-evaluation variant takes in constant evaluation (`if (__builtin_is_constant_evaluated())`,
  the variant's body with each prod a plain product: two_prod's Dekker product). That branch is
  never taken at run time, but a compiler that does not optimize may still emit it. Such a branch
  has no fused operation (the generator refuses a variant that has one). Zero in packed code, which
  has no constant evaluation.
- `muladd`: the declared contractable multiply-adds (`muladd`), printed `a * b + c`, which a
  compiler may emit fused or not; none so far, and the check has no rule for them yet.

The listings of double and float differ only in their constants, which can make `fma_distinct`
differ (two constants of different expressions may be the same number in one format and not in the
other): every count is given per limb type.
"""
import json

from . import cpp, ir

SCHEMA = 1
FORMS = ('scalar', 'scalar_call', 'packed')
LIMB_TYPES = tuple(cpp.TYPES)                # double, float
COUNTS = ('fma', 'fma_distinct', 'mul', 'mul_distinct', 'consteval_mul', 'muladd')

COMMUTATIVE = frozenset({'add', 'eq', 'and', 'or'})


def _numbering(prims, kernels, ctype):
    """A value number for every value that prims define: equal for two values that compute the same
    thing from the same operands (the module's docstring). A value that prims do not define (an
    input, or a parameter of a fix-up) is numbered by its name."""
    number = {}
    zero = ('const', cpp.literal(ir.ZERO, kernels, ctype))

    def operand(a):
        if a.const:
            return ('const', cpp.literal(a.name, kernels, ctype))
        return number.get(a.name, ('value', a.name))

    def negate(key):
        return key[1] if key[0] == 'neg' else ('neg', key)

    def unsigned(key):
        return (key[1], True) if key[0] == 'neg' else (key, False)

    for p in prims:
        args = [operand(a) for a in p.args]
        if p.op in ir.FUSED:
            a, b = args[0], args[1]
            c = zero if p.op == 'prod' else args[2]
            if p.op == 'fms':
                c = negate(c)
            if p.op == 'fnma':
                a = negate(a)
            (a, na), (b, nb) = unsigned(a), unsigned(b)
            key = ('fma', tuple(sorted((a, b))), na != nb, c)
        elif p.op == 'copy':
            key = args[0]
        elif p.op == 'neg':
            key = negate(args[0])
        elif p.op == 'guard':
            key = ('add', tuple(sorted((args[0], zero))))
        elif p.op in COMMUTATIVE:
            key = (p.op, tuple(sorted(args)))
        else:
            key = (p.op, tuple(args))
        number[p.dst] = key
    return number


def _counts(prims, kernels, ctype):
    """The counts of one function's operations."""
    number = _numbering(prims, kernels, ctype)
    fused = [number[p.dst] for p in prims if p.op in ir.FUSED]
    muls = [number[p.dst] for p in prims if p.op == 'times_inf']
    return {'fma': len(fused), 'fma_distinct': len(set(fused)),
            'mul': len(muls), 'mul_distinct': len(set(muls)),
            'consteval_mul': 0,
            'muladd': sum(1 for p in prims if p.op == 'muladd')}


def _consteval(k, kernels):
    """(plain multiplications, muladds) of the constant-evaluation branch of a kernel's scalar C++
    (cpp.function: the variant's body, spelled with cpp.SPELL_CONSTEVAL, where prod is a plain
    product, times_inf a comparison and guard no operation)."""
    if not k.ce_variant:
        return 0, 0
    prims = ir.prims(kernels[k.ce_variant], kernels)
    return sum(1 for p in prims if p.op == 'prod'), sum(1 for p in prims if p.op == 'muladd')


def kernel_counts(k, kernels):
    """{form: {limb type: counts}} of one kernel."""
    prims = ir.prims(k, kernels)
    b = cpp.branch(k, kernels)
    ce_mul, ce_muladd = _consteval(k, kernels)
    out = {form: {} for form in FORMS}
    for ctype in LIMB_TYPES:
        whole = _counts(prims, kernels, ctype)
        out['packed'][ctype] = whole
        if b is None:
            call = dict(whole)
        else:
            before = _counts([it for it in b.before if isinstance(it, ir.Prim)], kernels, ctype)
            after = _counts([it for it in b.after if isinstance(it, ir.Prim)], kernels, ctype)
            call = {key: before[key] + after[key] for key in COUNTS}
        for form, counts in (('scalar', dict(whole)), ('scalar_call', call)):
            counts['consteval_mul'] = ce_mul
            counts['muladd'] += ce_muladd
            out[form][ctype] = counts
    return out


def objcode(kernels):
    """The text of gen/objcode.json: for each kernel, one line per form, and in it, for each limb
    type, the counts in the order of COUNTS (the file's "counts")."""
    lines = ['{',
             f' "schema": {SCHEMA},',
             f' "forms": {json.dumps(list(FORMS))},',
             f' "limb_types": {json.dumps(list(LIMB_TYPES))},',
             f' "counts": {json.dumps(list(COUNTS))},',
             ' "kernels": {']
    names = list(kernels)
    for i, name in enumerate(names):
        counts = kernel_counts(kernels[name], kernels)
        lines.append(f'  {json.dumps(name)}: {{')
        for j, form in enumerate(FORMS):
            row = ', '.join(f'{json.dumps(t)}: {json.dumps([counts[form][t][c] for c in COUNTS])}'
                            for t in LIMB_TYPES)
            lines.append(f'   {json.dumps(form)}: {{{row}}}{"," if j + 1 < len(FORMS) else ""}')
        lines.append(f'  }}{"," if i + 1 < len(names) else ""}')
    lines += [' }', '}']
    return '\n'.join(lines) + '\n'
