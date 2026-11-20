"""The checks every kernel passes before anything is generated (architecture.md, "The kernel IR").

Each rule is a short traversal of the kernel's dataflow graph and refuses with a message that
names the kernel, the value and the rule. Nothing is printed for any kernel while one is refused.
"""
from fractions import Fraction

from . import consts, cpp, expr, ieee, ir, rocq, simd

RULE1 = 'rule 1 (static single assignment)'
RULE_R1 = 'rule 2 (R1: products)'
RULE_R2 = 'rule 3 (R2: outputs)'
RULE_CONE = 'rule 4 (non-finite cone)'
RULE_THEOREM = 'rule 5 (theorem or unverified)'
RULE_R3 = 'rule 6 (R3: values that enter from the program)'
WELL_FORMED = 'well-formed'
CLAIMS = 'claims'
DOMAIN = 'domain'
CONSTEVAL = 'constant-evaluation variant'
COMPUTED = 'computed constants'

STATUSES = ('unverified', 'proved')

# Operand positions where a product could be contracted into an addition.
ADDITIVE = {'add': (0, 1), 'sub': (0, 1), 'fma': (2,), 'fms': (2,), 'fnma': (2,), 'muladd': (2,)}
# Operations whose result is (up to sign) one of these operands: a product passes through them.
FORWARDING = {'neg': (0,), 'abs': (0,), 'select': (1, 2), 'copy': (0,)}
# R2: what a kernel output may be the result of. Never muladd. A mask cannot be contracted into
# anything, so a mask output may be the result of any operation that makes a mask.
OUTPUT_OPS = frozenset({'add', 'sub', 'fma', 'fms', 'fnma', 'prod', 'select', 'neg', 'abs',
                        'succ', 'pred', 'copy', 'guard'})
MASK_OPS = frozenset(op for op, (_, result) in ir.OPS.items() if result == ir.MASK)
# Rule 4: operations that map any non-finite operand to a non-finite result. Not select (it may
# drop the operand), not succ/pred (succ(-inf) is finite), not comparisons.
PROPAGATING = frozenset({'add', 'sub', 'fma', 'fms', 'fnma', 'prod', 'muladd', 'neg', 'abs', 'mul',
                         'copy', 'guard', 'times_inf'})
# R1: the result of times_inf, a plain multiplication (exact), may only be compared or selected.
TIMES_INF_USES = {'lt': (0, 1), 'le': (0, 1), 'eq': (0, 1), 'select': (1, 2)}
# The closed vocabulary of the claims (architecture.md, "Claims", "Claims of the second wave" and
# "Claims of the non-finite layer"): requirements and their number of operands.
REQUIRES = {'normalized': 1, 'abs_ge': 2, 'power_of_two': 1, 'nonneg': 1, 'canonical': 1, 'ball': 2, 'count': 1}
REQUIRES_FINITE = ('normalized', 'abs_ge', 'power_of_two', 'nonneg', 'count')
REQUIRES_EXTENDED = ('canonical', 'ball', 'power_of_two', 'nonneg')
# Requirements about the format rather than an input (milestone2.md, "Additions to the claims"):
# format half, the format contains 1/2.
FORMAT_REQUIRES = ('half',)
# The expressions of the claims of Milestone 2 that name inputs and constants of the format: an
# upper entry's own value, the operands of holds. Those of up(EXPR), with names.
CONSTANT_TREES = {'int', 'name', 'add', 'sub', 'mul', 'div', 'neg', 'pow', 'call'}
ROUNDING_MODES = ('nearest', 'down', 'up')
RELATIONS = ('lt', 'le', 'eq')
LEADS = ('add', 'sub', 'mul')
SIDES = {'neighbor': ('up', 'down'), 'bound': ('below', 'above')}
# The conditions of `when` (error, rounded): a closed vocabulary.
WHEN = ('product_large',)
VALUE_TREES = {'name', 'add', 'sub', 'mul', 'neg', 'abs'}
# The expression of a condition of exact_when: a value expression that may also name limbs; and
# its threshold, an exact expression over u, eta and integers.
EXACT_TREES = VALUE_TREES | {'limb'}
THRESHOLD_TREES = {'int', 'name', 'add', 'sub', 'mul', 'div', 'neg', 'pow'}
# The kinds of ensures entries in each domain.
ENSURES_FINITE = ('normalized', 'leading_rounded', 'error', 'rounded', 'upper', 'predicate', 'encloses',
                  'neighbor', 'bound', 'holds')
ENSURES_EXTENDED = ('normalized', 'error', 'rounded', 'upper', 'predicate', 'encloses', 'extends',
                    'represents', 'makes_ball', 'neighbor', 'bound', 'finite_or_nan')
# Entries that say something about the value: a kernel needs at least one.
ABOUT_THE_VALUE = ('error', 'leading_rounded', 'rounded', 'upper', 'predicate', 'encloses', 'extends',
                   'represents', 'makes_ball', 'neighbor', 'bound', 'holds', 'finite_or_nan')
# The forms of an error entry: relative to |value| (R), to the sum of the magnitudes of the inputs
# (A), to the sum of the magnitudes of the terms of value (T: s+x*y gives |s| + |x*y|).
ERROR_FORMS = ('R', 'A', 'T')


class RuleError(Exception):
    def __init__(self, kernel, value, rule, message):
        super().__init__(f'kernel {kernel}, value {value}: {rule}: {message}')
        self.kernel, self.value, self.rule = kernel, value, rule


def check_all(kernels):
    """Every refusal for a set of kernels, as a list of RuleError (empty: all accepted)."""
    errors = []
    for k in kernels.values():
        errors += well_formed(k, kernels)
    if errors:
        return errors   # the other rules flatten calls, which needs well-formed callees
    for k in kernels.values():
        for rule in (products, outputs, nonfinite_cone, theorem, entry_values, claims, domains,
                     consteval_variant, computed_constants):
            errors += rule(k, kernels)
    if not errors:
        errors += ieee_printable(kernels)
    if not errors:
        for fd in getattr(kernels, 'folds', {}).values():
            errors += fold_rules(fd, kernels)
    return errors


def ieee_printable(kernels):
    """What the IEEE-model printer refuses (ieee.PrintError): a constant without a real-model
    definition, claims with no IEEE-model statement; and a kernel that needs an IEEE-model
    statement (of the extended domain, or with ieee:) but uses an operation the IEEE model has not.
    Any other kernel with such an operation (fnma, muladd, mul) is left out of the IEEE model."""
    errs = []
    try:
        ieee.model(kernels)
    except ieee.PrintError as e:
        errs.append(RuleError('-', '-', DOMAIN, str(e)))
    for k in kernels.values():
        missing = ieee.missing_operations(k, kernels)
        if missing:
            if k.extended or k.ieee or k.ieee_finite or k.ieee_finite_result:
                errs.append(RuleError(k.name, '-', DOMAIN, f'the IEEE model has no {", ".join(missing)}, '
                                      'and this kernel needs an IEEE-model statement'))
            continue
        try:
            ieee.kernel_statements(k, kernels)
        except ieee.PrintError as e:
            errs.append(RuleError(k.name, '-', DOMAIN, str(e)))
    return errs


def well_formed(k, kernels):
    """Rule 1 (single assignment, use after definition, no unused value), names, kinds, arity."""
    errs = []

    def err(value, rule, msg):
        errs.append(RuleError(k.name, value, rule, msg))

    reserved = rocq.RESERVED | cpp.RESERVED | simd.RESERVED
    if k.name in reserved:
        err('-', WELL_FORMED, f'{k.name} is a name the printers use')
    if k.name.endswith(('_spec', '_correct', '_audit')) or k.name.startswith(('fuse_', 'up_') + ir.COMPUTED):
        err('-', WELL_FORMED, f'{k.name}: the Rocq printer makes names ending in _spec, _correct and '
                              '_audit, and starting with fuse_, up_, unit_computed and tiny_computed')
    groups = [g.name for g in k.inputs + k.outputs]
    for g in set(groups):
        if groups.count(g) > 1:
            err(g, WELL_FORMED, f'group {g} is declared twice')
    defined = {}   # value -> (kind, line or 'input')
    for v, kind in zip(k.input_limbs, k.input_kinds):
        if v in defined:
            err(v, RULE1, f'{v} is assigned twice (as two input limbs)')
        defined[v] = (kind, 'input')
    later = {d: st.line for st in k.body for d in st.dsts}
    used = set()
    for st in k.body:
        if st.is_call:
            if st.op not in kernels:
                err(st.dsts[0], WELL_FORMED, f'line {st.line}: unknown operation or kernel {st.op!r}')
                for d in st.dsts:
                    defined.setdefault(d, (ir.LIMB, st.line))
                used.update(a.name for a in st.args)
                continue
            callee = kernels[st.op]
            want = callee.input_kinds
            results = callee.output_kinds
        else:
            want, result = ir.OPS[st.op]
            results = [result]
        if len(st.args) != len(want):
            err(st.dsts[0], WELL_FORMED,
                f'line {st.line}: {st.op} takes {len(want)} operands, not {len(st.args)}')
        if len(st.dsts) != len(results):
            err(st.dsts[0], WELL_FORMED,
                f'line {st.line}: {st.op} defines {len(results)} values, not {len(st.dsts)}')
        for a, kind in zip(st.args, want):
            if a.const:
                if a.name != ir.ZERO and a.name not in ir.CONSTANTS and a.name not in ir.SPECIAL \
                        and not ir.computed(a.name) and ir.up(a.name) is None:
                    err(a.name, WELL_FORMED, f'line {st.line}: unknown constant {a.name!r}')
                elif kind != ir.LIMB:
                    err(a.name, WELL_FORMED, f'line {st.line}: a constant is a limb, not a mask')
                continue
            if a.name not in defined:
                if a.name in later:
                    used.add(a.name)
                    err(a.name, RULE1, f'{a.name} is used on line {st.line} before its definition '
                                       f'on line {later[a.name]}')
                else:
                    err(a.name, RULE1, f'{a.name} is used on line {st.line} and never defined')
                continue
            used.add(a.name)
            if defined[a.name][0] != kind:
                err(a.name, WELL_FORMED, f'line {st.line}: {st.op} wants a {kind} here, and '
                                         f'{a.name} is a {defined[a.name][0]}')
        for d, kind in zip(st.dsts, results):
            if not ir.VALUE_NAME.match(d):
                err(d, WELL_FORMED, f'line {st.line}: a value name is [a-z][a-z0-9]*')
            elif d in reserved or d in kernels:
                err(d, WELL_FORMED, f'line {st.line}: {d} is a name the printers use')
            if d in defined:
                where = defined[d][1]
                where = 'as an input' if where == 'input' else f'on line {where}'
                err(d, RULE1, f'{d} is assigned twice ({where} and on line {st.line})')
            defined[d] = (kind, st.line)
    for v in k.input_limbs:
        if not ir.VALUE_NAME.match(v):
            err(v, WELL_FORMED, 'a value name is [a-z][a-z0-9]*')
        elif v in reserved or v in kernels:
            err(v, WELL_FORMED, f'{v} is a name the printers use')
    outs = k.output_limbs
    for v, kind in zip(outs, k.output_kinds):
        if outs.count(v) > 1:
            err(v, WELL_FORMED, f'{v} is returned twice')
        if v not in defined:
            err(v, RULE1, f'output {v} is never defined')
        elif defined[v][0] != kind:
            err(v, WELL_FORMED, f'output {v} is a {defined[v][0]}, and its group is declared as a '
                                f'{kind} group ("output: mask NAME" declares a mask)')
        used.add(v)
    for v, why in k.unused.items():
        if v not in k.input_limbs:
            err(v, RULE1, f'unused: {v} is not an input')
        elif v in used:
            err(v, RULE1, f'unused: {v} is used; remove the declaration')
        used.add(v)
    for v in defined:
        if v not in used:
            err(v, RULE1, f'{v} is never used (an input the computation does not need is declared '
                          'with "unused:")' if defined[v][1] == 'input' else f'{v} is never used')
    return errs


def products(k, kernels):
    """R1: no plain multiplication, so that no compiler can contract a product into an addition.

    times_inf is a plain multiplication too, by +infinity, and exact. Its result is only compared
    or selected, and never an output as it is: there is then no addition for a compiler to fuse it
    into, and one that pushed an addition through the select would compute the same value."""
    errs = []
    uses = {}
    for st in k.body:
        for i, a in enumerate(st.args):
            if not a.const:
                uses.setdefault(a.name, []).append((st, i))
    for st in k.body:
        if st.op != 'times_inf':
            continue
        v = st.dsts[0]
        for use, i in uses.get(v, ()):
            if use.is_call or i not in TIMES_INF_USES.get(use.op, ()):
                what = f'an operand of {use.op}' if not use.is_call else f'passed to {use.op}'
                errs.append(RuleError(k.name, v, RULE_R1,
                                      f'line {st.line}: {v} = times_inf(...) is a plain multiplication and is '
                                      f'{what} at {use.dsts[0]} (line {use.line}); it may only be an operand of '
                                      'a comparison or of select'))
        if v in k.output_limbs:
            errs.append(RuleError(k.name, v, RULE_R1,
                                  f'line {st.line}: {v} = times_inf(...) is a plain multiplication and an output '
                                  'as it is; an output may take it only through select'))

    def route(v, path):
        for st, i in uses.get(v, ()):
            if i in ADDITIVE.get(st.op, ()):
                return path + [f'an operand of {st.op} at {st.dsts[0]}']
            if i in FORWARDING.get(st.op, ()):
                found = route(st.dsts[0], path + [f'{st.op} at {st.dsts[0]}'])
                if found:
                    return found
        return None

    for st in k.body:
        if st.op == 'mul':
            r = route(st.dsts[0], [])
            how = f'it reaches {" then ".join(r)}' if r else 'there is none in the run-time IR'
            errs.append(RuleError(k.name, st.dsts[0], RULE_R1,
                                  f'line {st.line}: {st.dsts[0]} is a plain multiplication, and {how}; '
                                  'a rounded product is written prod(a, b), which no compiler can '
                                  'contract'))
    return errs


def outputs(k, kernels):
    """R2: no output is an expression the compiler could fuse into the caller."""
    errs = []
    defs = {d: st for st in k.body for d in st.dsts}
    for v in k.output_limbs:
        st = defs.get(v)
        if st is None:
            errs.append(RuleError(k.name, v, RULE_R2, f'output {v} is an input; an output must be '
                                                      'computed by an operation (copy, for an input)'))
        elif not st.is_call and st.op not in OUTPUT_OPS | MASK_OPS:
            errs.append(RuleError(k.name, v, RULE_R2,
                                  f'output {v} is the result of {st.op} (line {st.line}); outputs are '
                                  f'results of {", ".join(sorted(OUTPUT_OPS))}, never of muladd'))
    return errs


def nonfinite_cone(k, kernels):
    """Rule 4: a non-finite value anywhere shows in output limb 0.

    Every limb value must reach output limb 0 through operations that keep a non-finite operand
    non-finite. Values computed from output limb 0 itself cannot reach it and are exempt: whether
    they can overflow while it is finite is a property of the algorithm, for its proof.
    """
    flat = ir.prims(k, kernels)
    kinds = ir.kinds(k, kernels)
    z0 = k.outputs[0].limbs[0]
    feeds, consumers = {}, {}
    for p in flat:
        for a in p.args:
            if not a.const:
                consumers.setdefault(a.name, []).append(p.dst)
                if p.op in PROPAGATING:
                    feeds.setdefault(p.dst, []).append(a.name)
    reach, todo = {z0}, [z0]
    while todo:
        for a in feeds.get(todo.pop(), ()):
            if a not in reach:
                reach.add(a)
                todo.append(a)
    after, todo = set(), [z0]
    while todo:
        for c in consumers.get(todo.pop(), ()):
            if c not in after:
                after.add(c)
                todo.append(c)
    bad = [v for v in kinds if kinds[v] == ir.LIMB and v not in reach and v not in after]
    if k.cone_exempt:
        if not bad:
            return [RuleError(k.name, '-', RULE_CONE, 'declares cone_exempt but satisfies the rule; '
                                                     'remove the declaration')]
        return []
    if not bad:
        return []
    more = f' (and {len(bad) - 1} more: {", ".join(bad[1:])})' if len(bad) > 1 else ''
    return [RuleError(k.name, bad[0], RULE_CONE,
                      f'{bad[0]} does not reach output limb {z0} through operations that keep a '
                      f'non-finite value non-finite, and is not computed from {z0}{more}; a kernel '
                      'that cannot satisfy this declares cone_exempt with its finiteness test')]


def theorem(k, kernels):
    """Rule 5: every kernel names its theorem, its source and the source's license, or is unverified.

    A kernel of the extended domain has a second statement, in the IEEE model, with its own status
    (ieee_status) and, once proved, its own theorem (ieee_theorem). A kernel with no real-model
    statement (a full kernel or a constructor) has the IEEE-model one only: its status is its
    ieee_status, and its theorem is the ieee_theorem.
    """
    errs = []

    def err(msg):
        errs.append(RuleError(k.name, '-', RULE_THEOREM, msg))

    if k.status not in STATUSES:
        return [RuleError(k.name, '-', RULE_THEOREM,
                          f'status is {k.status!r}; it must be one of {", ".join(STATUSES)}')]
    if k.extended and k.ieee_status not in STATUSES:
        return [RuleError(k.name, '-', RULE_THEOREM, f'ieee_status is {k.ieee_status!r}; a kernel of the '
                                                     f'extended domain gives one of {", ".join(STATUSES)}')]
    if not k.extended and (k.ieee_status or k.ieee_theorem):
        err('ieee_status and ieee_theorem belong to kernels of the extended domain')
    main = k.theorem if k.real_model else k.ieee_theorem
    if k.status != 'unverified':
        for what, have in (('theorem' if k.real_model else 'ieee_theorem', main), ('source', k.source),
                           ('license', k.license)):
            if not have:
                err(f'the kernel is not marked unverified and names no {what}')
    if k.extended and k.ieee_status == 'proved' and not k.ieee_theorem:
        err('ieee_status is proved and the kernel names no ieee_theorem')
    if k.ieee_theorem and k.ieee_status != 'proved':
        err('an ieee_theorem is named only once the IEEE-model statement is proved (ieee_status: proved)')
    if not k.real_model:
        if k.theorem:
            err('the kernel has no real-model statement, so no theorem: its proof is the ieee_theorem')
        if k.status != k.ieee_status:
            err(f'the kernel has no real-model statement, so its status is its ieee_status '
                f'({k.ieee_status}), not {k.status}')
    for what, have, want in (('theorem', k.theorem, f'{k.name}_correct'), ('ieee_theorem', k.ieee_theorem, None)):
        if not have:
            continue
        path, name = have
        if want and name != want:
            err(f'the theorem must be named {want}, not {name}')
        if not (path.startswith('proofs/theories/') and path.endswith('.v')):
            err(f'the {what} file must be proofs/theories/*.v, not {path}')
    return errs


def r3_analysis(k, kernels, tainted):
    """What rule R3 finds in kernel k when its input values `tainted` enter from the program.

    A value enters from the program, and so does what neg, abs, select or copy make of it alone.
    Such a value may be a factor of a product or an FMA, compared, or passed to guard, whose
    result is clean; passed to another kernel, it is followed into that kernel's body. Returns
    (hits, relied, out):
    - hits: [(where, origins)], one for each operand of add or sub and each FMA addend that is
      such a value, with the route to it and the inputs of k it comes from; a hit that comes only
      from inputs that k declares guard_pending is left out;
    - relied: {kernel name: its inputs} whose guard_pending declarations left out a hit, in k or
      in a kernel it calls;
    - out: {output value of k: origins} for the outputs that are such a value.
    """
    origin = {v: frozenset([v]) for v in tainted}
    hits, relied = [], {}
    for st in k.body:
        args = [None if a.const else origin.get(a.name) for a in st.args]
        if st.is_call:
            callee = kernels[st.op]
            passed = {callee.input_limbs[i]: o for i, o in enumerate(args) if o}
            if not passed:
                continue
            sub_hits, sub_relied, sub_out = r3_analysis(callee, kernels, frozenset(passed))
            for name, vs in sub_relied.items():
                relied.setdefault(name, set()).update(vs)
            for where, o in sub_hits:
                hits.append((f'{where} in {st.op} (called for {st.dsts[0]})',
                             frozenset().union(*(passed[x] for x in o))))
            for d, v in zip(st.dsts, callee.output_limbs):
                if v in sub_out:
                    origin[d] = frozenset().union(*(passed[x] for x in sub_out[v]))
            continue
        for i in ADDITIVE.get(st.op, ()):
            if args[i]:
                what = 'an operand' if st.op in ('add', 'sub') else 'the addend'
                hits.append((f'{what} of {st.op} at {st.dsts[0]}', args[i]))
        forwarded = [args[i] for i in FORWARDING.get(st.op, ()) if args[i]]
        if forwarded:
            origin[st.dsts[0]] = frozenset().union(*forwarded)
    kept = []
    for where, o in hits:
        if o <= set(k.guard_pending):
            relied.setdefault(k.name, set()).update(o)
        else:
            kept.append((where, o))
    return kept, relied, {v: origin[v] for v in k.output_limbs if v in origin}


def entry_values(k, kernels):
    """Rule R3: in an entry kernel, no value that enters from the program, nor what neg, abs or
    select alone make of it, is an operand of add or sub or the addend of an FMA before it has
    passed through guard; a value passed to another kernel must be treated so there too. Nor is
    such a value an output of the entry kernel as it is.

    A one-limb input enters from the program unless declared stored (a limb of an object); the
    limbs of a multi-limb input are stored unless declared supplied. guard_pending names an input
    whose guard is not written yet, with the reason; the kernel and every kernel that passes such
    a value into that input are accepted because of it (`r3_report` lists them)."""
    errs = []

    def err(value, msg):
        errs.append(RuleError(k.name, value, RULE_R3, msg))

    ins = {g.name: g for g in k.inputs}
    for cls, names in (('stored', k.stored), ('supplied', k.supplied)):
        for name in sorted(names):
            g = ins[name]
            if not k.entry:
                err(name, f'{cls} {name}: only an entry kernel says where its inputs come from')
            elif cls == 'stored' and (g.kind != ir.LIMB or len(g.limbs) != 1):
                err(name, 'stored is said of a one-limb input; the limbs of a multi-limb input are '
                          'stored unless it is declared supplied')
            elif cls == 'supplied' and (g.kind != ir.LIMB or len(g.limbs) < 2):
                err(name, 'supplied is said of a multi-limb input; a one-limb input is supplied by '
                          'the program unless it is declared stored')
    program = k.program_values()
    for v in k.guard_pending:
        if not k.entry:
            err(v, f'guard_pending {v}: only an entry kernel has values that enter from the program')
        elif v not in program:
            err(v, f'guard_pending {v}: {v} is not an input that enters from the program')
    if errs or not k.entry:
        return errs
    hits, relied, out = r3_analysis(k, kernels, frozenset(program))
    for v, origins in out.items():
        # An output becomes a limb of an object, which later kernels add unguarded (it is stored).
        o = sorted(origins)[0]
        err(o, f'{o} enters from the program and is the output {v} as it is (through neg, abs, select or '
               'copy alone, or a callee that returns it so); an entry kernel returns it only after guard')
    if hits:
        where, origins = hits[0]
        more = f' (and {len(hits) - 1} more)' if len(hits) > 1 else ''
        v = sorted(origins)[0]
        err(v, f'{v} enters from the program and reaches {where} without passing through guard{more}; '
               'write g = guard(' + v + ') and use g there, or declare the input stored if it is a '
               'limb of an object')
    for v in sorted(set(k.guard_pending) - relied.get(k.name, set())):
        err(v, f'declares guard_pending {v}, but {v} is never added unguarded; remove the declaration')
    return errs


def r3_report(kernels):
    """(pending, through): the kernels that declare guard_pending, as {kernel: {input: reason}},
    and the entry kernels that rule R3 accepts only because of another kernel's declaration, as
    {kernel: sorted names of the kernels whose declarations they rely on}."""
    pending = {k.name: dict(k.guard_pending) for k in kernels.values() if k.guard_pending}
    through = {}
    for k in kernels.values():
        if k.entry:
            _, relied, _ = r3_analysis(k, kernels, frozenset(k.program_values()))
            others = sorted(set(relied) - {k.name})
            if others:
                through[k.name] = others
    return pending, through


def claims(k, kernels):
    """The claims use the closed vocabulary of architecture.md, "Claims" and its second wave."""
    errs = []

    def err(msg):
        errs.append(RuleError(k.name, '-', CLAIMS, msg))

    ins = {g.name: g for g in k.inputs}
    outs = {g.name: g for g in k.outputs}
    limb_ins = {n for n, g in ins.items() if g.kind == ir.LIMB}
    one_limb_ins = {n for n in limb_ins if len(ins[n].limbs) == 1}

    def parsed(text, allowed_names, what, trees=None):
        try:
            tree = expr.parse(text)
        except expr.ExprError as e:
            err(f'{what}: {e}')
            return None
        extra = expr.names(tree) - allowed_names
        if extra:
            err(f'{what}: unknown name {", ".join(sorted(extra))} in {text!r}')
            return None
        if trees is not None and not _only(tree, trees):
            err(f'{what} {text!r}: only + - *, unary minus and abs( ) of names')
            return None
        if trees is None and not _only(tree, {'int', 'name', 'add', 'sub', 'mul', 'div', 'neg'}):
            err(f'{what} {text!r}: a rational expression has no abs( )')
            return None
        return tree

    def output(name, what, kind=ir.LIMB, one=False):
        g = outs.get(name)
        if g is None:
            err(f'ensures {what} of {name!r}: not an output')
        elif g.kind != kind:
            err(f'ensures {what} of {name!r}: the output must be a {kind}')
        elif one and len(g.limbs) != 1:
            err(f'ensures {what} of {name!r}: the output must have one limb')

    def exact_when(e):
        """The conditions of an exact_when: each EXPR = 0 or |EXPR| > K (or >= K), EXPR over the
        input names and their limbs, K an exact positive expression over u, eta and integers."""
        conds = e.get('exact_when')
        if conds is None:
            return
        if not conds:
            err(f'ensures {e["kind"]}: exact_when needs at least one condition')
        for c in conds:
            keys = set(c) - {'than'}
            if 'than' not in c or len(keys) != 1 or not keys <= set(ir.EXACT_CONDITIONS):
                err(f'exact_when {c!r}: a condition is {{"zero_or_abs_gt" or "zero_or_abs_ge": EXPR, "than": K}}')
                continue
            text = c[keys.pop()]
            try:
                tree = expr.parse(text)
            except expr.ExprError as x:
                err(f'exact_when: {x}')
                continue
            extra = expr.names(tree) - limb_ins
            if extra:
                err(f'exact_when: unknown name {", ".join(sorted(extra))} in {text!r}')
                continue
            if not _only(tree, EXACT_TREES):
                err(f'exact_when {text!r}: only + - *, unary minus, abs( ), names and limbs NAME[I]')
                continue
            for g, i in sorted(expr.limbs(tree)):
                if i >= len(ins[g].limbs):
                    err(f'exact_when {text!r}: {g} has {len(ins[g].limbs)} limbs, so no limb {g}[{i}]')
            try:
                bound = expr.parse(c['than'])
            except expr.ExprError as x:
                err(f'exact_when: {x}')
                continue
            if expr.names(bound) - {'u', 'eta'} or not _only(bound, THRESHOLD_TREES):
                err(f'exact_when than={c["than"]!r}: an exact expression over u, eta and integers')
                continue
            for p, qmin in ((53, -1074), (24, -149)):
                try:
                    positive = expr.evaluate(bound, {'u': Fraction(1, 2 ** p), 'eta': Fraction(2) ** qmin}) > 0
                except expr.ExprError as x:
                    err(f'exact_when than={c["than"]!r}: {x}')
                    break
                if not positive:
                    err(f'exact_when than={c["than"]!r}: the threshold is positive')
                    break

    makes_balls = bool(k.ensures) and all(e['kind'] == 'makes_ball' for e in k.ensures)
    # The bound kernels of Milestone 2: every entry says what it bounds, and the kernel has no value.
    own_values = bool(k.ensures) and all(e['kind'] == 'holds' or (e['kind'] == 'upper' and 'value' in e)
                                         for e in k.ensures)
    if makes_balls:
        if k.value:
            err('a kernel that makes a ball from its inputs has no value')
    elif own_values:
        if k.value:
            err('every claim of the kernel has its own value (upper value=, holds): the kernel has none')
    elif not k.value:
        err('no value')
    else:
        parsed(k.value, limb_ins, 'value', VALUE_TREES)
    one_limb_outs = {n for n, g in outs.items() if g.kind == ir.LIMB and len(g.limbs) == 1}
    mask_outs = {n for n, g in outs.items() if g.kind == ir.MASK}
    allowed = REQUIRES_EXTENDED if k.extended else REQUIRES_FINITE
    for req in k.requires:
        if req[0] == 'format':
            if len(req) != 2 or req[1] not in FORMAT_REQUIRES:
                err(f'requires {" ".join(req)!r}: the requirement on the format is "format half"')
            elif k.extended:
                err('requires format half: a requirement of the finite domain')
            continue
        n = REQUIRES.get(req[0])
        names = req[1:]
        if n is not None and len(names) == n and all(x in limb_ins for x in names):
            if req[0] not in allowed:
                err(f'requires {" ".join(req)!r}: {req[0]} is not a requirement of the '
                    f'{"extended" if k.extended else "finite"} domain'
                    + (' (canonical stands for normalized there)' if req[0] == 'normalized' else ''))
            elif req[0] in ('power_of_two', 'nonneg', 'count') and names[0] not in one_limb_ins:
                err(f'requires {" ".join(req)!r}: {req[0]} is about a one-limb input')
            elif req[0] == 'canonical' and len(ins[names[0]].limbs) < 2:
                err(f'requires {" ".join(req)!r}: canonical is about a multi-limb input (a one-limb '
                    'input is any value)')
            elif req[0] == 'ball' and names[1] not in one_limb_ins:
                err(f'requires {" ".join(req)!r}: the radius of a ball is a one-limb input')
            continue
        err(f'requires {" ".join(req)!r}: the vocabulary is "normalized INPUT", "abs_ge INPUT INPUT", '
            '"power_of_two INPUT", "nonneg INPUT", "count INPUT", "format half", and in the extended '
            'domain "canonical INPUT", "ball CENTER RADIUS"')
    if not any(e['kind'] in ABOUT_THE_VALUE for e in k.ensures):
        err(f'ensures says nothing about the value: it needs an entry of kind {", ".join(ABOUT_THE_VALUE)}')
    kinds = ENSURES_EXTENDED if k.extended else ENSURES_FINITE
    for e in k.ensures:
        kind = e['kind']
        if kind not in kinds:
            err(f'ensures {kind}: not a claim of the {"extended" if k.extended else "finite"} domain')
            continue
        if kind in ('normalized', 'leading_rounded', 'represents'):
            output(e['of'], kind)
        elif kind == 'error':
            output(e['of'], kind)
            if e['form'] not in ERROR_FORMS:
                err(f'error form {e["form"]!r}: it is R, A or T')
            for key in ('c', 'k', 't'):
                if e[key] is None:
                    err(f'error entry without {key}')
            if e['c'] is not None:
                parsed(e['c'], {'u'}, 'c')
            if e['t'] is not None:
                parsed(e['t'], set(), 't')
            if e['when'] is not None and e['when'] not in WHEN:
                err(f'when={e["when"]!r}: the vocabulary is {", ".join(WHEN)}')
            exact_when(e)
        elif kind == 'rounded':
            output(e['of'], kind, one=True)
            if e['mode'] not in ROUNDING_MODES:
                err(f'rounded mode {e["mode"]!r}: it is {", ".join(ROUNDING_MODES)}')
            if 'when' in e and e['when'] not in WHEN:
                err(f'when={e["when"]!r}: the vocabulary is {", ".join(WHEN)}')
        elif kind in SIDES:
            output(e['of'], kind, one=True)
            if e['side'] not in SIDES[kind]:
                err(f'{kind} side {e["side"]!r}: it is {" or ".join(SIDES[kind])}')
            if kind == 'neighbor' and k.value not in one_limb_ins:
                err(f'neighbor: the value is the one-limb operand whose neighbor is the output, not {k.value!r}')
        elif kind == 'upper':
            output(e['of'], kind, one=True)
            if 'gaps' not in e and 'value' not in e:
                err('upper: an entry says how far above (gaps=) or what it bounds (value=), or both')
            if 'gaps' in e:
                tree = parsed(e['gaps'], set(), 'gaps')
                if tree is not None and not expr.evaluate(tree, {}) > 0:
                    err(f'gaps={e["gaps"]}: the number of gaps is positive')
            if 'value' in e:
                _constant_expression(e['value'], limb_ins | (one_limb_outs - {e['of']}), k, kernels, err,
                                     'upper value')
            if 'if' in e and e['if'] not in mask_outs:
                err(f'upper if={e["if"]}: the condition is a mask output')
        elif kind == 'holds':
            if e['rel'] not in RELATIONS:
                err(f'holds relation {e["rel"]!r}: it is {", ".join(RELATIONS)}')
            for a in e['args']:
                _constant_expression(a, limb_ins | one_limb_outs, k, kernels, err, 'holds')
            if e['if'] not in mask_outs:
                err(f'holds if={e["if"]}: the condition is a mask output')
        elif kind == 'finite_or_nan':
            output(e['of'], kind)
            if e['flag'] not in mask_outs:
                err(f'finite_or_nan flag={e["flag"]}: the flag is a mask output')
            g = ins.get(k.value)
            if g is None or g.kind != ir.LIMB or len(g.limbs) != len(outs.get(e['of'], ir.Group('', ())).limbs):
                err(f'finite_or_nan: the value is an input of as many limbs as {e["of"]}, not {k.value!r}')
        elif kind == 'predicate':
            output(e['of'], kind, kind=ir.MASK)
            if e['rel'] not in RELATIONS:
                err(f'predicate relation {e["rel"]!r}: it is {", ".join(RELATIONS)}')
            for a in e['args']:
                parsed(a, limb_ins, 'predicate argument', VALUE_TREES)
        elif kind == 'encloses':
            _encloses(e, k, ins, outs, output, parsed, err)
            exact_when(e)
            if 'finite_when' in e:
                for c in e['finite_when']:
                    parsed(c['abs_le'], limb_ins, 'finite_when', VALUE_TREES)
                for b, cr in e['balls'].items():
                    if ('ball', cr['center'], cr['radius']) not in k.requires:
                        err(f'ball {b}: in the extended domain its operand is required to be a ball: '
                            f'"requires: ball {cr["center"]} {cr["radius"]}"')
        elif kind == 'extends':
            _extends(e, k, kernels, ins, outs, parsed, err)
        elif kind == 'makes_ball':
            output(e['center'], 'makes_ball (center)')
            output(e['radius'], 'makes_ball (radius)', one=True)
            for what, n in (('center', e['from']['center']), ('radius', e['from']['radius'])):
                g = ins.get(n)
                if g is None or g.kind != ir.LIMB or (what == 'radius' and len(g.limbs) != 1):
                    err(f'makes_ball from {what} {n!r}: not a{" one-limb" if what == "radius" else ""} '
                        'limb input')
    if k.min_precision is not None and k.min_precision < 1:
        err('min_precision must be at least 1')
    return errs


def _extends(e, k, kernels, ins, outs, parsed, err):
    """A full kernel (milestone1.md, "IEEE-like results"): its core has the same inputs, the same
    shape of outputs, the same value and minimum precision, and the core's requirements with
    canonical for normalized; the output is the first, of two limbs; the leading operation applies
    to the leading limbs of the two operands; the conditions are expressions over the inputs."""
    limb_ins = {n for n, g in ins.items() if g.kind == ir.LIMB}
    if len(k.ensures) != 1:
        err('a kernel that extends a core claims nothing else: its core\'s claims are part of extends')
    if e['of'] != k.outputs[0].name or len(outs.get(e['of'], ir.Group('', ())).limbs) != 2:
        err(f'extends {e["of"]!r}: the output of a full kernel is its first, of two limbs')
    if e['lead'] not in LEADS:
        err(f'extends lead={e["lead"]!r}: it is {", ".join(LEADS)}')
    if len([g for g in k.inputs if g.kind == ir.LIMB]) != 2:
        err('extends: the leading operation takes the leading limbs of exactly two operands')
    for c in e['finite_when']:
        parsed(c['abs_le'], limb_ins, 'finite_when', VALUE_TREES)
    core = kernels.get(e['core'])
    if core is None or core is k:
        err(f'extends core={e["core"]!r}: not another kernel')
        return
    if core.extended:
        err(f'extends core={core.name}: a core is of the finite domain (it keeps its real-model statement)')
    if [(g.name, len(g.limbs), g.kind) for g in core.inputs] != [(g.name, len(g.limbs), g.kind) for g in k.inputs]:
        err(f'extends core={core.name}: the core must have the same inputs, names included')
    if [(len(g.limbs), g.kind) for g in core.outputs] != [(len(g.limbs), g.kind) for g in k.outputs]:
        err(f'extends core={core.name}: the core\'s outputs must have the same limbs')
    if core.value != k.value:
        err(f'extends core={core.name}: the value must be the core\'s, {core.value}')
    if core.min_precision != k.min_precision:
        err(f'extends core={core.name}: the minimum precision is the core\'s, {core.min_precision}')
    want = [('canonical',) + r[1:] if r[0] == 'normalized' else r for r in core.requires]
    if want != k.requires:
        err(f'extends core={core.name}: the requirements are the core\'s with canonical for normalized: '
            + ', '.join(' '.join(r) for r in want))


def domains(k, kernels):
    """The two models. A kernel has a real-model statement unless it is a full kernel or a
    constructor (ir.Kernel.real_model); those are of the extended domain. What the real model
    prints must have a meaning there: no infinity or NaN constant, no call of a kernel that has
    no real-model statement."""
    errs = []

    def err(value, msg):
        errs.append(RuleError(k.name, value, DOMAIN, msg))

    if k.domain not in (None, 'extended'):
        err('-', f'domain {k.domain!r}: it is extended, or the line is left out (the domain finite)')
    if not k.real_model and not k.extended:
        err('-', 'a full kernel or a constructor (extends, represents, makes_ball, or ieee_only) is of the '
                 'extended domain')
    for e in k.ensures:
        if 'finite_when' in e and e['kind'] == 'encloses' and not k.extended:
            err('-', 'finite_when belongs to the extended domain')
    # The IEEE-model statements of a core (ieee.py): of the finite domain only (a kernel of the
    # extended domain has its own); a threshold or a bridge is about the values of the kernel's
    # straight-line program, so the kernel must be one.
    if (k.ieee or k.ieee_finite or k.ieee_finite_result) and k.extended:
        err('-', 'ieee, ieee_finite and ieee_finite_result are about a kernel of the finite domain; one '
                 'of the extended domain has its IEEE-model statement from its claims')
    if ('bridge' in k.ieee or k.ieee_finite or k.ieee_finite_result) and not ieee.has_program(k, kernels):
        err('-', 'a bridge or a threshold is about the values of a straight-line program, and this kernel '
                 'is not one (an operation or a constant that Program.v has not)')
    names = {g.name for g in k.inputs if g.kind == ir.LIMB} | set(k.input_limbs)
    for key in ('ieee_finite', 'ieee_finite_result'):
        for c in getattr(k, key):
            try:
                tree = expr.parse(c['abs_le'])
            except expr.ExprError as e:
                err('-', f'{key}: {e}')
                continue
            extra = expr.names(tree) - names
            if extra:
                err('-', f'{key}: unknown name {", ".join(sorted(extra))} in {c["abs_le"]!r}')
            elif not _only(tree, VALUE_TREES):
                err('-', f'{key} {c["abs_le"]!r}: only + - *, unary minus and abs( ) of names')
    if k.real_model:
        for st in k.body:
            if st.op == 'times_inf':
                err(st.dsts[0], f'line {st.line}: times_inf has no meaning in the real model, which has '
                                'no infinity; only a kernel without a real-model statement uses it')
            for a in st.args:
                if a.const and a.name in ir.SPECIAL:
                    err(a.name, f'line {st.line}: const {a.name} has no meaning in the real model; '
                                'only a kernel without a real-model statement (a full kernel or a '
                                'constructor) names it')
            if st.is_call and st.op in kernels and not kernels[st.op].real_model:
                err(st.dsts[0], f'line {st.line}: {st.op} has no real-model statement, so a kernel '
                                'that has one cannot call it')
    return errs


def _encloses(e, k, ins, outs, output, parsed, err):
    """A ball claim: its center and radius are outputs, each ball a center and a radius input,
    and the set an expression over the ball names and the inputs no ball uses."""
    output(e['center'], 'encloses (center)')
    output(e['radius'], 'encloses (radius)', one=True)
    taken = set()
    for b, cr in e['balls'].items():
        c, r = cr['center'], cr['radius']
        clash = b in ins or b in outs or b in k.input_limbs + k.output_limbs or \
            b in rocq.RESERVED or not ir.VALUE_NAME.match(b)
        if clash:
            err(f'ball name {b!r} is the name of a group, a limb, or a name the printers use')
        for what, n in (('center', c), ('radius', r)):
            g = ins.get(n)
            if g is None or g.kind != ir.LIMB or (what == 'radius' and len(g.limbs) != 1):
                err(f'ball {b}: its {what} {n!r} is not a{" one-limb" if what == "radius" else ""} '
                    'limb input')
            if n in taken:
                err(f'ball {b}: {n} belongs to two balls')
            taken.add(n)
    if not e['balls']:
        err('encloses names no ball')
    points = {n for n, g in ins.items() if g.kind == ir.LIMB and n not in taken}
    parsed(e['set'], set(e['balls']) | points, 'encloses set', VALUE_TREES)


def _only(tree, allowed):
    return tree[0] in allowed and all(_only(t, allowed) for t in tree[1:] if isinstance(t, tuple))


def computed_constants(k, kernels):
    """unit_computed(K) and tiny_computed(K) name a kernel with one unconditional relative bound,
    and come from a proved bound unless the kernel that uses them is itself unverified."""
    errs = []
    for name in ir.constants(k):
        if ir.up(name) is not None:
            errs += _up_constant(k, kernels, name)
            continue
        c = ir.computed(name)
        if c is None:
            continue
        callee = kernels.get(c[1])
        if callee is None:
            errs.append(RuleError(k.name, name, COMPUTED, f'{c[1]} is not a kernel'))
            continue
        try:
            consts.source_bound(callee)
        except consts.ConstError as e:
            errs.append(RuleError(k.name, name, COMPUTED, str(e)))
        if callee.status != 'proved' and k.status != 'unverified':
            errs.append(RuleError(k.name, name, COMPUTED,
                                  f'{c[1]} is {callee.status}: only an unverified kernel may use the '
                                  'constants of a bound that is not proved'))
        # Below K's minimum precision its bound, and so the constant, does not exist.
        if callee.min_precision and (k.min_precision or 1) < callee.min_precision:
            errs.append(RuleError(k.name, name, COMPUTED,
                                  f'the claims of {c[1]} hold from precision {callee.min_precision} on, '
                                  f'so min_precision must be at least {callee.min_precision}'))
    return errs


def _constant_expression(text, names, k, kernels, err, what):
    """An expression of the claims of Milestone 2 over `names` and the constants of the format: u,
    eta, integers, unit(K) and tiny(K) of a kernel K with one unconditional error entry, proved
    unless the kernel that claims it is unverified, with + - * /, integer powers and parentheses.
    Returns the tree, or None after reporting through err. `k` is a kernel or a fold (it has
    status and min_precision)."""
    try:
        tree = expr.parse(text)
    except expr.ExprError as e:
        err(f'{what}: {e}')
        return None
    if not _only(tree, CONSTANT_TREES):
        err(f'{what} {text!r}: only + - * /, integer powers, names, u, eta, integers, unit(K) and tiny(K)')
        return None
    extra = expr.names(tree) - set(names) - {'u', 'eta'}
    if extra:
        err(f'{what}: unknown name {", ".join(sorted(extra))} in {text!r}')
        return None
    for fn, kname in sorted(expr.calls(tree)):
        callee = kernels.get(kname)
        if callee is None:
            err(f'{what}: {fn}({kname}): {kname} is not a kernel')
            continue
        try:
            consts.source_bound(callee)
        except consts.ConstError as e:
            err(f'{what}: {e}')
            continue
        if callee.status != 'proved' and k.status != 'unverified':
            err(f'{what}: {kname} is {callee.status}: only an unverified claim may use the constants of a '
                'bound that is not proved')
        if callee.min_precision and (k.min_precision or 1) < callee.min_precision:
            err(f'{what}: the claims of {kname} hold from precision {callee.min_precision} on, so '
                f'min_precision must be at least {callee.min_precision}')
    return tree


def _up_constant(k, kernels, name):
    """A constant up(EXPR): its vocabulary; each unit(K) and tiny(K) names a kernel with one
    unconditional relative bound, proved unless k is unverified, and k's minimum precision is at
    least K's; and the expression is positive in binary64 and binary32 (in another format it is
    checked when the constant is computed)."""
    errs = []

    def err(msg):
        errs.append(RuleError(k.name, name, COMPUTED, msg))

    try:
        tree = consts.up_tree(ir.up(name))
    except consts.ConstError as e:
        return [RuleError(k.name, name, COMPUTED, str(e))]
    for fn, kname in sorted(expr.calls(tree)):
        callee = kernels.get(kname)
        if callee is None:
            err(f'{fn}({kname}): {kname} is not a kernel')
            continue
        try:
            consts.source_bound(callee)
        except consts.ConstError as e:
            err(str(e))
            continue
        if callee.status != 'proved' and k.status != 'unverified':
            err(f'{kname} is {callee.status}: only an unverified kernel may use the constants of a bound '
                'that is not proved')
        if callee.min_precision and (k.min_precision or 1) < callee.min_precision:
            err(f'the claims of {kname} hold from precision {callee.min_precision} on, so min_precision must '
                f'be at least {callee.min_precision}')
    if not errs:
        for fmt in ((53, -1074, 971), (24, -149, 104)):
            try:
                consts.value(name, kernels, *fmt)
            except consts.ConstError as e:
                err(str(e))
    return errs


def consteval_variant(k, kernels):
    """A constant-evaluation variant computes without FMA and has the kernel's signature."""
    if not k.ce_variant:
        return []

    def err(value, msg):
        return [RuleError(k.name, value, CONSTEVAL, msg)]

    v = kernels.get(k.ce_variant)
    if v is None or v is k:
        return err('-', f'ce_variant {k.ce_variant!r} is not another kernel')
    if v.ce_variant:
        return err('-', f'its variant {v.name} has a variant of its own')
    if v.inputs != k.inputs or v.outputs != k.outputs:
        return err('-', f'its variant {v.name} must have the same inputs and outputs, limb names '
                        'included (its body is emitted in place of the kernel\'s)')
    for p in ir.prims(v, kernels):
        if p.op in ir.FUSED - {'prod'}:
            return err(p.dst, f'its variant {v.name} computes {p.dst} with {p.op}, and constant '
                              'evaluation has no FMA (only prod, as a plain product)')
    return []


# ---------------------------------------------------------------------------------------------
# Folds (milestone2.md, "Folds, the extension of the IR").

FOLD = 'fold'
# The kinds of a fold's claims (architecture.md, "Claims of Milestone 2", "Folds").
FOLD_ENSURES = ('normalized', 'fold_error', 'finite_or_nan')
# The heights of a fold's bound: n or n - 1, natural numbers (0 - 1 is 0, as in Rocq's nat).
FOLD_HEIGHTS = ('n', 'n-1')
# Names a fold's groups and limbs must not take: the parameters of its C++ functions and the
# section variables of its Rocq model. (The binders of the model and the statements are the name
# of the state, the element, the arrays' names joined, and the list, that and s: fold_binders.)
FOLD_RESERVED = frozenset({'n', 'lanes', 'emin', 'prec', 'choice'})


def fold_binders(fd):
    """The binders of a fold's Rocq model and statements: the state, one element (the arrays'
    names joined: x, or xy for x and y) and the list of elements (xs, xys)."""
    element = ''.join(g.name for g in fd.arrays)
    return fd.state.name, element, element + 's'
# The combinations whose zero state has the four properties the theorems use (zero_identity of
# proofs/theories/Summation.v), each a lemma of proofs/theories/SummationKernels.v proved once: a
# fold of the lane order whose combination has none is refused.
ZERO_LEMMAS = {'add_1_1': 'add_1_1_zero', 'add_2_2': 'add_2_2_zero', 'add_fast_2_2': 'add_fast_2_2_zero'}
# The formats the generator evaluates the zero state in (zero_state): the two of the library and
# small ones, where every operand can be tried.
ZERO_FORMATS = ((53, -1074, 971), (24, -149, 104)) + tuple((p, -5, 5) for p in range(1, 6))


def fold_names(fd):
    """The names the printers make for a fold: its C++ functions and its Rocq definitions and
    statements. None may be the name of a kernel."""
    out = [f'{fd.name}_{s}' for s in ('step', 'combine', 'packed')]
    for order in fd.orders:
        base = f'{fd.name}_{ir.ORDER_SUFFIX.get(order, order)}'
        out += [base, f'{base}_spec', f'{base}_correct', f'{base}_audit']
    return out


def _shape(g):
    return (len(g.limbs), g.kind)


def fold_rules(fd, kernels):
    """Every refusal of one fold: its description, the shapes of its state, R3 on its supplied
    arrays, its zero state, its claims, its theorem."""
    errs = []

    def err(value, rule, msg):
        errs.append(RuleError(fd.name, value, rule, msg))

    reserved = rocq.RESERVED | cpp.RESERVED | simd.RESERVED | FOLD_RESERVED
    for n in fold_names(fd) + [fd.name]:
        if n in kernels:
            err('-', WELL_FORMED, f'{n} is a name the printers make for the fold, and the name of a kernel')
    groups = fd.arrays + ([fd.state] if fd.state else []) + fd.outputs
    names = [g.name for g in groups] + [v for g in groups for v in g.limbs if v != g.name]
    for n in sorted(set(names)):
        if names.count(n) > 1:
            err(n, WELL_FORMED, f'{n} names two groups or limbs of the fold')
        if n in reserved or n in kernels:
            err(n, WELL_FORMED, f'{n} is a name the printers use')
        if not ir.VALUE_NAME.match(n):
            err(n, WELL_FORMED, 'a name of a group or a limb is [a-z][a-z0-9]*')
    if not fd.arrays:
        err('-', WELL_FORMED, 'a fold reads at least one array')
    if fd.state is None or fd.state.kind != ir.LIMB:
        err('-', WELL_FORMED, 'the state is a group of limbs')
        return errs
    binders = fold_binders(fd)
    if len(set(binders)) < 3 or any(b in reserved | {'a', 'b'} for b in binders):
        err('-', WELL_FORMED, f'the binders of the model, {", ".join(binders)} (the state, the arrays\' names '
                              'joined, and that and s), are distinct and none is a name the printers use')
    if not fd.orders or len(set(fd.orders)) < len(fd.orders) or set(fd.orders) - set(ir.ORDERS):
        err('-', WELL_FORMED, f'orders: some of {", ".join(ir.ORDERS)}, each once')
    if fd.writes:
        err('-', WELL_FORMED, 'writes: a map (a step that also returns elements of arrays it writes) is '
                              'not in this stage of the generator; a fold of this stage writes none')
    groups_of = {g.name: g for g in fd.arrays + [fd.state]}

    def kernel_of(what, call):
        if call is None:
            return None
        k = kernels.get(call[0])
        if k is None:
            err('-', WELL_FORMED, f'{what}: {call[0]} is not a kernel')
        return k

    # The step: the state and one element of each array, in the order of the kernel's inputs, to
    # the next state; every group once.
    step = kernel_of('step', fd.step)
    if step is not None:
        _, args, dsts = fd.step
        if dsts != (fd.state.name,):
            err('-', WELL_FORMED, f'step: it gives the next state, {fd.state.name} = {step.name}(...)')
        want = sorted([fd.state.name] + [g.name for g in fd.arrays])
        if sorted(args) != want:
            err('-', WELL_FORMED, f'step: its arguments are the state and every array once: {", ".join(want)}')
        elif len(step.inputs) != len(args):
            err('-', WELL_FORMED, f'step: {step.name} takes {len(step.inputs)} groups, not {len(args)}')
        else:
            for a, g in zip(args, step.inputs):
                if _shape(g) != _shape(groups_of[a]):
                    err(a, WELL_FORMED, f'step: {step.name} takes {g.name} of {len(g.limbs)} limbs where the '
                                        f'fold passes {a} of {len(groups_of[a].limbs)}')
        if len(step.outputs) != 1 or _shape(step.outputs[0]) != _shape(fd.state):
            err('-', WELL_FORMED, f'step: {step.name} returns one group of the shape of the state '
                                  f'({len(fd.state.limbs)} limbs)')
        if not step.real_model:
            err('-', DOMAIN, f'step: {step.name} has no real-model statement, and the step is in the real model')
    elif fd.step is None:
        err('-', WELL_FORMED, 'a fold needs "step:"')
    # The combination: two states into one.
    combine = kernel_of('combine', fd.combine)
    if 'lanes' in fd.orders and fd.combine is None:
        err('-', WELL_FORMED, 'the lane order combines the lanes: the fold needs "combine:"')
    if combine is not None:
        _, args, dsts = fd.combine
        if dsts != (fd.state.name,) or args != (fd.state.name, fd.state.name):
            err('-', WELL_FORMED, f'combine: {fd.state.name} = {combine.name}({fd.state.name}, {fd.state.name})')
        if [_shape(g) for g in combine.inputs] != [_shape(fd.state)] * 2 or \
                [_shape(g) for g in combine.outputs] != [_shape(fd.state)]:
            err('-', WELL_FORMED, f'combine: {combine.name} takes two groups and returns one, each of the shape '
                                  f'of the state ({len(fd.state.limbs)} limbs)')
        if not combine.real_model:
            err('-', DOMAIN, f'combine: {combine.name} has no real-model statement, and the combination is in the '
                             'real model')
    # The finish: the final state to the fold's results.
    finish = kernel_of('finish', fd.finish)
    if finish is not None:
        _, args, dsts = fd.finish
        if args != (fd.state.name,):
            err('-', WELL_FORMED, f'finish: it takes the final state, {finish.name}({fd.state.name})')
        if [_shape(g) for g in finish.inputs] != [_shape(fd.state)]:
            err('-', WELL_FORMED, f'finish: {finish.name} takes one group of the shape of the state')
        if dsts != tuple(g.name for g in fd.outputs):
            err('-', WELL_FORMED, 'finish: its destinations are the fold\'s outputs, in order: '
                                  + ', '.join(g.name for g in fd.outputs))
        elif [_shape(g) for g in finish.outputs] != [_shape(g) for g in fd.outputs]:
            err('-', WELL_FORMED, f'finish: the outputs of {finish.name} do not have the shapes of the fold\'s')
    elif fd.outputs:
        err('-', WELL_FORMED, 'a fold without a finish returns its state: it declares no output')
    if errs:
        return errs
    errs += _fold_r3(fd, step, kernels)
    if combine is not None and 'lanes' in fd.orders:
        errs += zero_state(fd, combine, kernels)
    errs += _fold_claims(fd, kernels, step, combine, finish)
    errs += _fold_theorem(fd)
    return errs


def _fold_r3(fd, step, kernels):
    """Rule R3 on a fold. The elements of a supplied array enter from the program: the step's
    inputs that receive them are values of the program, and nothing the step adds is one before
    guard (r3_analysis, the analysis of an entry kernel, on exactly those inputs). The step is an
    entry kernel that declares them so; the state is a limb of an object (stored). The elements
    of a stored array were written through Kairn, and nothing is asked of them."""
    errs = []
    _, args, _ = fd.step
    by_arg = dict(zip(args, step.inputs))
    program = set(step.program_values())
    tainted = []
    for a in args:
        g = by_arg[a]
        if a == fd.state.name:
            if set(g.limbs) & program:
                errs.append(RuleError(fd.name, a, RULE_R3, f'the step {step.name} takes the state as values of the '
                                                           f'program ({g.name}); the state is stored'))
        elif fd.roles[a] == 'supplied':
            if not set(g.limbs) <= program:
                errs.append(RuleError(fd.name, a, RULE_R3,
                                      f'{a} is supplied by the program, and the step {step.name} does not take '
                                      f'{g.name} as a value of the program (entry: yes, and the input not '
                                      'stored, or supplied for more than one limb)'))
            tainted += list(g.limbs)
    hits, _, out = r3_analysis(step, kernels, frozenset(tainted))
    for where, origins in hits:
        errs.append(RuleError(fd.name, sorted(origins)[0], RULE_R3,
                              f'an element of a supplied array reaches {where} in the step {step.name} without '
                              'passing through guard'))
    for v in out:
        errs.append(RuleError(fd.name, v, RULE_R3, f'an element of a supplied array is the next state ({v}) as '
                                                   'it is; it passes through guard first'))
    return errs


def _is_valid(f, k, group, values):
    """Whether values (interpreter values) are finite numbers of f that satisfy what kernel k
    requires of its input group."""
    from . import interp
    if not all(v[0] == interp.NUM and interp.member(f, v) for v in values):
        return False
    if ('normalized', group.name) in k.requires or ('canonical', group.name) in k.requires:
        return all(interp.eq(values[i], interp.add(f, values[i], values[i + 1])) for i in range(len(values) - 1))
    return True


def _value(values):
    return sum((-1 if v[1] else 1) * Fraction(v[2]) * Fraction(2) ** v[3] for v in values)


_ZERO_CACHE = {}


def zero_state(fd, combine, kernels):
    """The four properties of the zero state that the theorems take as one hypothesis
    (zero_identity, proofs/theories/Summation.v), for the combination of the lane order:
    1. the zero state is valid: checked by evaluation, in ZERO_FORMATS, against the combination's
       requirements on its operands (for two limbs, (0, 0) normalized);
    2. its value is 0: syntactic, every limb of the zero state is the literal +0;
    3. 0 + x has the value of x for every valid x: checked by evaluation, on every valid operand
       of the small formats of ZERO_FORMATS and on edge values of the two others;
    4. 0 + 0 is the zero state, limb for limb: checked by evaluation in ZERO_FORMATS.
    That they hold in every format is the lemma of ZERO_LEMMAS the proof uses: a combination
    without one is refused."""
    from . import interp
    if combine.name not in ZERO_LEMMAS:
        return [RuleError(fd.name, '-', FOLD, f'the combination {combine.name} has no lemma that its zero state '
                                              'has the properties of zero_identity (proofs/theories/'
                                              f'SummationKernels.v: {", ".join(ZERO_LEMMAS.values())})')]
    key = (combine.name, id(kernels))
    if key not in _ZERO_CACHE:
        found = []
        m = interp.Machine(kernels)
        a, b = combine.inputs
        zero = [(interp.NUM, False, 0, 0)] * len(a.limbs)
        for p, qmin, qmax in ZERO_FORMATS:
            if combine.min_precision and p < combine.min_precision:
                continue
            f = interp.Format(f'fp:{p}:{qmin}:{qmax}', p, qmin, qmax)
            if not _is_valid(f, combine, a, zero) or not _is_valid(f, combine, b, zero):
                found.append(f'the zero state is not a valid operand of {combine.name} in {f.name}')
                continue
            zz = m.run(combine.name, f, zero + zero)
            if not all(v[0] == interp.NUM and v[2] == 0 for v in zz):
                found.append(f'{combine.name}(0, 0) is not the zero state in {f.name}: '
                             + ' '.join(interp.format_limb(v) for v in zz))
            for x in _operands(f, len(b.limbs)):
                if not _is_valid(f, combine, b, x):
                    continue
                z = m.run(combine.name, f, zero + x)
                if not all(v[0] == interp.NUM for v in z) or _value(z) != _value(x):
                    found.append(f'{combine.name}(0, x) does not have the value of x in {f.name}, x = '
                                 + ' '.join(interp.format_limb(v) for v in x))
                    break
        _ZERO_CACHE[key] = found
    return [RuleError(fd.name, '-', FOLD, msg) for msg in _ZERO_CACHE[key]]


def _operands(f, limbs):
    """The operands zero_state tries: every number of a small format, edge values of a large one;
    for two limbs, each of them as a leading limb with the second limbs near the ends of what a
    normalized pair allows (zero, eta, a half and a quarter of the gap, just below the half), of
    either sign. Every normalized pair of small formats is tried by the generator's tests."""
    from . import interp
    if f.qmax - f.qmin <= 12:
        nums = sorted({interp.canon(s, m, q) for q in range(f.qmin, f.qmax + 1) for m in range(1, 2 ** f.p)
                       for s in (False, True)}, key=str)
    else:
        nums = [interp.canon(s, m, q) for q in (f.qmin, f.qmin + f.p, 0, f.qmax - f.p, f.qmax)
                for m in (1, 3, 2 ** f.p - 1, 2 ** (f.p - 1) + 1) for s in (False, True)]
    zeros = [(interp.NUM, False, 0, 0), (interp.NUM, True, 0, 0)]
    nums += zeros
    if limbs == 1:
        return [[x] for x in nums]
    if limbs != 2:
        raise AssertionError(limbs)
    out = []
    for x in nums:
        if x[2] == 0:
            out += [[x, y] for y in zeros]
            continue
        q = max(x[3] + x[2].bit_length() - f.p, f.qmin)     # the gap at x is 2^q
        tails = [(1, f.qmin)] + [(1, e) for e in (q - 1, q - 2) if e >= f.qmin]
        if q - 1 > f.qmin:
            tails.append(((1 << (q - 1 - f.qmin)) - 1, f.qmin))    # just below half the gap
        for m, e in tails:
            for s in (False, True):
                y = interp.canon(s, m, e)
                if interp.member(f, y):
                    out.append([x, y])
        out += [[x, y] for y in zeros]
    return out


def _fold_claims(fd, kernels, step, combine, finish):
    """A fold's claims, in the vocabulary of architecture.md ("Claims of Milestone 2", folds)."""
    errs = []

    def err(msg):
        errs.append(RuleError(fd.name, '-', CLAIMS, msg))

    arrays = {g.name: g for g in fd.arrays}
    results = {g.name: g for g in fd.results()}
    if not fd.value:
        err('no value: the exact value of one element, of which the fold computes the sum')
    else:
        try:
            tree = expr.parse(fd.value)
            if expr.names(tree) - set(arrays) or not _only(tree, VALUE_TREES):
                err(f'value {fd.value!r}: + - *, unary minus and abs( ) of the arrays\' names')
        except expr.ExprError as e:
            err(f'value: {e}')
    if fd.domain not in (None, 'extended'):
        err(f'domain {fd.domain!r}: it is extended, or the line is left out')
    for r in fd.requires:
        if len(r) != 2 or r[1] not in arrays:
            err(f'requires {" ".join(r)!r}: a requirement of a fold is about each element of one array')
            continue
        want = 'canonical' if fd.extended else 'normalized'
        if r[0] != want or len(arrays[r[1]].limbs) < 2:
            err(f'requires {" ".join(r)!r}: a fold of the {"extended" if fd.extended else "finite"} domain requires '
                f'"{want} ARRAY" of an array of more than one limb')
    if 'fold_error' not in [e['kind'] for e in fd.ensures]:
        err('a fold claims its bound: an ensures entry fold_error')
    if fd.min_precision is None or fd.min_precision < 1:
        err('min_precision: an integer, at least 1')
        return errs
    for k in (step, combine):
        if k is not None and (k.min_precision or 1) > fd.min_precision:
            err(f'min_precision {fd.min_precision}: the claims of {k.name} hold from precision {k.min_precision} on')
    for e in fd.ensures:
        kind = e['kind']
        if kind not in FOLD_ENSURES:
            err(f'ensures {kind}: a fold claims {", ".join(FOLD_ENSURES)}')
            continue
        g = results.get(e['of'])
        if g is None or g.kind != ir.LIMB:
            err(f'ensures {kind} of {e["of"]!r}: not a group of limbs that the fold returns')
            continue
        if _shape(g) != _shape(fd.state):
            err(f'ensures {kind} of {e["of"]!r}: the result has the shape of the state')
        if kind == 'normalized' and len(g.limbs) < 2:
            err('normalized: of a result of more than one limb')
        elif kind == 'fold_error':
            for key in ('eps', 'term', 'tau'):
                tree = _constant_expression(e[key], (), fd, kernels, err, f'fold_error {key}')
                if tree is None:
                    continue
                for p, qmin in ((53, -1074), (24, -149)):
                    try:
                        x = consts.evaluate(tree, kernels, p, qmin)
                    except consts.ConstError as x_err:
                        err(f'fold_error {key}={e[key]}: {x_err}')
                        break
                    if x < 0 or (key == 'eps' and x <= 0):
                        err(f'fold_error {key}={e[key]}: it is {"positive" if key == "eps" else "nonnegative"}')
                        break
            for key in ('rel', 'abs'):
                if e[key] not in FOLD_HEIGHTS:
                    err(f'fold_error {key}={e[key]}: a height is {" or ".join(FOLD_HEIGHTS)}')
            if combine is not None and not errs:
                errs += _eps_of_combination(fd, e, combine, kernels)
        elif kind == 'finite_or_nan':
            flag = results.get(e['flag'])
            if flag is None or flag.kind != ir.MASK:
                err(f'finite_or_nan flag={e["flag"]}: the flag is a mask the fold returns')
            if finish is None or not any(x['kind'] == 'finite_or_nan' for x in finish.ensures):
                err('finite_or_nan: what the finish of the fold claims, and its finish claims no such thing')
            elif not fd.extended:
                err('finite_or_nan: about elements that are not finite, a claim of the extended domain')
    return errs


def _unit_of(k):
    """c u^k of the one error entry of a kernel, as a function of the precision, when the entry
    has no absolute term and no condition and is of form R or A (an error relative to |x + y| is
    one relative to |x| + |y| as well); None otherwise."""
    entries = [e for e in k.ensures if e['kind'] == 'error']
    if len(entries) != 1 or entries[0]['when'] is not None or entries[0]['form'] not in ('R', 'A'):
        return None
    e = entries[0]
    if expr.evaluate(expr.parse(e['t']), {}) != 0:
        return None
    return lambda p: expr.evaluate(expr.parse(e['c']), {'u': Fraction(1, 2 ** p)}) * Fraction(1, 2 ** p) ** e['k']


def _eps_of_combination(fd, e, combine, kernels):
    """The eps of a fold's bound is the relative error of its combination, the addition of the
    tree: checked by evaluation at every precision from the fold's minimum to 64, which, for two
    rational functions of u of small degree, shows they are one function."""
    unit = _unit_of(combine)
    if unit is None:
        return [RuleError(fd.name, '-', CLAIMS, f'the combination {combine.name} has no error entry of form R or A '
                                                'without an absolute term: the bound of a sum needs one')]
    tree = expr.parse(e['eps'])
    for p in range(max(fd.min_precision, combine.min_precision or 1), 65):
        try:
            x = consts.evaluate(tree, kernels, p, -1074)
        except consts.ConstError as x_err:
            return [RuleError(fd.name, '-', CLAIMS, f'fold_error eps={e["eps"]}: {x_err}')]
        if x != unit(p):
            return [RuleError(fd.name, '-', CLAIMS, f'fold_error eps={e["eps"]} is not the relative error of the '
                                                    f'combination {combine.name} at precision {p}')]
    return []


def _fold_theorem(fd):
    errs = []

    def err(msg):
        errs.append(RuleError(fd.name, '-', RULE_THEOREM, msg))

    if fd.status not in STATUSES:
        return [RuleError(fd.name, '-', RULE_THEOREM, f'status is {fd.status!r}; it must be one of '
                                                      f'{", ".join(STATUSES)}')]
    if fd.status != 'unverified':
        for what, have in (('theorem', fd.theorem), ('source', fd.source), ('license', fd.license)):
            if not have:
                err(f'the fold is not marked unverified and names no {what}')
    if fd.theorem and not (fd.theorem.startswith('proofs/theories/') and fd.theorem.endswith('.v')):
        err(f'the theorem file must be proofs/theories/*.v, not {fd.theorem}')
    if fd.theorem and fd.status != 'proved':
        err('a theorem file is named only once the fold is proved (status: proved)')
    return errs
