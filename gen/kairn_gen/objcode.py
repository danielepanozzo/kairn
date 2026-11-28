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
- `consteval_mul`: the plain multiplications of what a kernel computes only in constant
  evaluation: for a kernel with a constant-evaluation variant, the branch
  `if (__builtin_is_constant_evaluated())`, the variant's body with each prod a plain product
  (two_prod's Dekker product); for a kernel constexpr by the rule of the product, the first arm of
  each `__builtin_is_constant_evaluated() ? a * b : fma_rn(a, b, 0)`, one per prod. Neither is
  taken at run time, but a compiler that does not optimize may still emit it. Such a branch has no
  fused operation (the generator refuses a variant that has one). Zero in packed code, which has no
  constant evaluation.
- `muladd`: the declared contractable multiply-adds (`muladd`), printed `a * b + c`, which a
  compiler may emit fused or not; none so far, and the check has no rule for them yet.

The listings of double and float differ only in their constants, which can make `fma_distinct`
differ (two constants of different expressions may be the same number in one format and not in the
other): every count is given per limb type.

The kernels of the round-up interval (ir.KernelSet.upward) have a section of their own after the
folds, "upward" (upward_lines, below), which no other kernel's entry changes.
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
    input, or a parameter of a fix-up) is numbered by its name.

    A number is an integer, given to each distinct key the first time it is seen, and a key holds
    the numbers of its operands, not their keys: two values have the same number exactly when
    their keys, written out in full, would be equal, and a key stays small. Written out in full, the
    key of a value repeats the keys of its operands at every use, which for a listing whose values
    are used many times over (a ball of two limbs through its interval and back, ball_hull_2) grows
    exponentially with its depth, and so does the time to hash it where Python does not cache the
    hash of a tuple (before 3.14)."""
    number = {}
    numbers = {}                         # key -> number
    keys = []                            # number -> key

    def intern(key):
        n = numbers.get(key)
        if n is None:
            n = numbers[key] = len(keys)
            keys.append(key)
        return n

    zero = intern(('const', cpp.literal(ir.ZERO, kernels, ctype)))

    def operand(a):
        if a.const:
            return intern(('const', cpp.literal(a.name, kernels, ctype)))
        return number[a.name] if a.name in number else intern(('value', a.name))

    def negate(n):
        key = keys[n]
        return key[1] if key[0] == 'neg' else intern(('neg', n))

    def unsigned(n):
        key = keys[n]
        return (key[1], True) if key[0] == 'neg' else (n, False)

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
            n = intern(('fma', tuple(sorted((a, b))), na != nb, c))
        elif p.op == 'copy':
            n = args[0]
        elif p.op == 'neg':
            n = negate(args[0])
        elif p.op == 'guard':
            n = intern(('add', tuple(sorted((args[0], zero)))))
        elif p.op in COMMUTATIVE:
            n = intern((p.op, tuple(sorted(args))))
        else:
            n = intern((p.op, tuple(args)))
        number[p.dst] = n
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
    """(plain multiplications, muladds) of what a kernel's scalar C++ computes only in constant
    evaluation (cpp.function): the variant's body, spelled with cpp.SPELL_CONSTEVAL, where prod is a
    plain product, times_inf a comparison and guard no operation; or, for a kernel constexpr by the
    rule of the product (cpp.SPELL_PLAIN), the plain product of the first arm of each prod."""
    if cpp.product_rule(k, kernels):
        return sum(1 for p in ir.prims(k, kernels) if p.op == 'prod'), 0
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


# The functions of a fold (cpp.py, simd.py): F_seq and F_lanes of scalar.hpp, F_packed of the
# packed headers. Each is a loop, which a compiler may unroll, peel or duplicate: what its code
# asks for is given part by part, each part an inlined kernel (the step, the combination, the
# finish) with the least number of times it is in the printed function (the step twice in F_lanes,
# its loop over the lanes and its loop over the rest; the scalar and the packed step in F_packed).
# The check (tests/objcode/objcode.py) accepts the counts of a function that are a sum of each
# part's counts taken at least that many times: the fused instructions of one iteration are
# those of the step, and nothing else is fused anywhere.
FOLD_FORMS = ('seq', 'lanes', 'packed')


def _part(name, k, minimum, kernels, ctype):
    items, _ = ir.inline_call(k, kernels, [ir.Operand(v) for v in k.input_limbs], 'p')
    counts = _counts([it for it in items if isinstance(it, ir.Prim)], kernels, ctype)
    return [name, minimum] + [counts[c] for c in COUNTS]


def fold_counts(fd, kernels):
    """{form: {limb type: [[part, least number of times, counts...], ...]}} of one fold. A map
    has its step and its check (the first pass and the second; the and of the masks is no
    kernel): F_seq the step once and the check twice, F_lanes the step twice (the lanes and the
    rest) and the check three times, F_packed the packed step and check once, and the scalar step
    once and check twice."""
    if fd.is_conv:
        # A convolution: the step of the fold of its coefficients in the loop over the terms, and the
        # check in the first pass and the second; the sequential order only.
        step, check = kernels[kernels.folds[fd.coefficients].step[0]], kernels[fd.check]
        return {'seq': {t: [_part('step', step, 1, kernels, t), _part('check', check, 2, kernels, t)]
                        for t in LIMB_TYPES}}
    if fd.is_bv_conv:
        # The product of two BallVectors: the records in the two loops of the maxima (one kernel, or two,
        # each at least once per array), the step of the fold of the coefficients in the loop over the
        # terms, the check of the convolution once (the first pass; the whole space computes nothing),
        # and the bound, the radius and the finish once, in F_end.
        conv = kernels.folds[fd.centers]
        step, check = kernels[kernels.folds[conv.coefficients].step[0]], kernels[conv.check]
        recs = {}
        for r in fd.records:
            recs[r[0]] = recs.get(r[0], 0) + 1
        parts = [('record', kernels[name], n) for name, n in recs.items()] + \
            [('step', step, 1), ('check', check, 1), ('bound', kernels[fd.bound[0]], 1),
             ('radius', kernels[fd.radius[0]], 1), ('finish', kernels[fd.finish[0]], 1)]
        return {'seq': {t: [_part(name, k, m, kernels, t) for name, k, m in parts] for t in LIMB_TYPES}}
    if fd.is_bv:
        # A ball vector: the step and the record per element (the scalar step and record twice in
        # F_lanes, the lanes and the rest), the combination of the lanes, the radius and the finish
        # once; the second pass computes nothing.
        step, record, combine = (kernels[c[0]] for c in (fd.step, fd.record, fd.combine))
        radius, finish = kernels[fd.radius[0]], kernels[fd.finish[0]]
        end = [('radius', radius, 1), ('finish', finish, 1)]
        forms = {'seq': [('step', step, 1), ('record', record, 1)] + end,
                 'lanes': [('step', step, 2), ('record', record, 2), ('combine', combine, 1)] + end,
                 'packed': [('packed step', step, 1), ('packed record', record, 1), ('combine', combine, 1),
                            ('step', step, 1), ('record', record, 1)] + end}
        return {form: {t: [_part(name, k, m, kernels, t) for name, k, m in parts] for t in LIMB_TYPES}
                for form, parts in forms.items()}
    if fd.is_map:
        step, check = kernels[fd.step[0]], kernels[fd.check]
        forms = {'seq': [('step', step, 1), ('check', check, 2)],
                 'lanes': [('step', step, 2), ('check', check, 3)],
                 'packed': [('packed step', step, 1), ('packed check', check, 1), ('step', step, 1),
                            ('check', check, 2)]}
        return {form: {t: [_part(name, k, m, kernels, t) for name, k, m in parts] for t in LIMB_TYPES}
                for form, parts in forms.items()}
    step, combine, finish = cpp.fold_kernels(fd, kernels)
    forms = {}
    if 'sequential' in fd.orders:
        forms['seq'] = [('step', step, 1)]
    if 'lanes' in fd.orders:
        forms['lanes'] = [('step', step, 2), ('combine', combine, 1)]
        forms['packed'] = [('packed step', step, 1), ('combine', combine, 1), ('step', step, 1)]
    out = {}
    for form, parts in forms.items():
        if finish is not None:
            parts = parts + [('finish', finish, 1)]
        out[form] = {t: [_part(name, k, m, kernels, t) for name, k, m in parts] for t in LIMB_TYPES}
    return out


def objcode(kernels):
    """The text of gen/objcode.json: for each kernel, one line per form, and in it, for each limb
    type, the counts in the order of COUNTS (the file's "counts"); then, when there are folds,
    for each fold one line per form with its parts (FOLD_FORMS)."""
    folds = getattr(kernels, 'folds', {})
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
    lines.append(' }' + (',' if folds else ''))
    if folds:
        lines += [f' "fold_forms": {json.dumps(list(FOLD_FORMS))},',
                  ' "fold_parts": ["part", "least", ' + ', '.join(json.dumps(c) for c in COUNTS) + '],',
                  ' "folds": {']
        names = list(folds)
        for i, name in enumerate(names):
            counts = fold_counts(folds[name], kernels)
            lines.append(f'  {json.dumps(name)}: {{')
            forms = list(counts)
            for j, form in enumerate(forms):
                row = ', '.join(f'{json.dumps(t)}: {json.dumps(counts[form][t])}' for t in LIMB_TYPES)
                lines.append(f'   {json.dumps(form)}: {{{row}}}{"," if j + 1 < len(forms) else ""}')
            lines.append(f'  }}{"," if i + 1 < len(names) else ""}')
        lines.append(' }')
    family = getattr(kernels, 'upward', {})
    if family:
        lines[-1] += ','
        lines += upward_lines(family)
    lines.append('}')
    return '\n'.join(lines) + '\n'


# The round-up interval (docs/developer/design/upward.md, "Object code"): its kernels are printed by
# upward_cpp.py in forms of their own, and the check is of other instructions. Per kernel, form and
# limb type, the multiplications and the maxima its code asks for:
#
# - `sse2`, `neon`: the one-register form; one multiplication per pair line of mul_ru, one maximum
#   (MAXPD or VMAXPD, FMAXNM) per pair line of max_nl;
# - `numbers`: the two-number form; one multiplication per mul_ru, and no count of maxima (max_nl is
#   `a > b ? a : b`, which a compiler may emit as a maximum, a selection or a branch): null;
# - `avx2`, `neon_arrays`: the array forms, a loop of registers of W lanes and the rest of the
#   elements by the one-register form, as parts [part, least, mul, max, fmax]: the loop's statement
#   by statement (one multiplication per mul_ru, one maximum per max_nl), and the one-register form's,
#   each at least once in the function (a compiler may unroll either loop);
# - and the maxima that return a NaN (arm64's FMAX): on arm64 (`neon`, `neon_arrays`) one per unord of
#   two operands, the NaN test of their maximum (detail::unord, since version 0.4.1), per pair line in
#   the register form and per statement in the loop of the array form; none elsewhere, and never for
#   a max_nl, whose arm64 form is FMAXNM.
#
# Every form has, whatever the options, no fused multiply-add, no negated multiplication, no other
# maximum that returns a NaN and no call outside the object; the rule is the check's
# (tests/objcode/objcode.py, --upward).
UPWARD_FORMS = ('sse2', 'neon', 'numbers', 'avx2', 'neon_arrays')
UPWARD_COUNTS = ('mul', 'max', 'fmax')
UPWARD_PARTS = ('part', 'least') + UPWARD_COUNTS


def _unord_of_two(st):
    """Whether a statement is unord of two operands, which detail::unord prints as the NaN test of
    their maximum on arm64 (unord(a, a) is the NaN test of a alone)."""
    return st.op == 'unord' and st.args[0] != st.args[1]


def upward_counts(k):
    """{form: counts} of one kernel of the family; the array forms only for those that have one."""
    from . import upward_cpp
    lines = k.pair_lines()
    reg = [sum(1 for s0, _ in lines if s0.op == 'mul_ru'), sum(1 for s0, _ in lines if s0.op == 'max_nl')]
    stmts = [sum(1 for st in k.body if st.op == 'mul_ru'), sum(1 for st in k.body if st.op == 'max_nl')]
    reg_fmax = sum(1 for s0, _ in lines if _unord_of_two(s0))
    stmts_fmax = sum(1 for st in k.body if _unord_of_two(st))
    out = {'sse2': reg + [0], 'neon': reg + [reg_fmax], 'numbers': [stmts[0], None, 0]}
    if k.name in upward_cpp.ARRAYS:
        out['avx2'] = [['packed', 1] + stmts + [0], ['tail', 1] + reg + [0]]
        out['neon_arrays'] = [['packed', 1] + stmts + [stmts_fmax], ['tail', 1] + reg + [reg_fmax]]
    return out


def upward_lines(family):
    """The lines of gen/objcode.json's section of the round-up interval, after the folds."""
    lines = [f' "upward_forms": {json.dumps(list(UPWARD_FORMS))},',
             f' "upward_counts": {json.dumps(list(UPWARD_COUNTS))},',
             f' "upward_parts": {json.dumps(list(UPWARD_PARTS))},',
             ' "upward": {']
    names = list(family)
    for i, name in enumerate(names):
        counts = upward_counts(family[name])
        lines.append(f'  {json.dumps(name)}: {{')
        forms = [f for f in UPWARD_FORMS if f in counts]
        for j, form in enumerate(forms):
            row = ', '.join(f'{json.dumps(t)}: {json.dumps(counts[form])}' for t in LIMB_TYPES)
            lines.append(f'   {json.dumps(form)}: {{{row}}}{"," if j + 1 < len(forms) else ""}')
        lines.append(f'  }}{"," if i + 1 < len(names) else ""}')
    lines.append(' }')
    return lines


def without_family(text):
    """gen/objcode.json as it is without the round-up interval: its section, after the folds, taken
    out (test_upward.py compares it with the file of the other kernels)."""
    at = text.find(',\n "upward_forms"')
    return text if at < 0 else text[:at] + '\n}\n'
