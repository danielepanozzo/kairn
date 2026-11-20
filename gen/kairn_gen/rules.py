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
NEGATED_FUSED = 'negated fused result'

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
REQUIRES = {'normalized': 1, 'abs_ge': 2, 'power_of_two': 1, 'nonneg': 1, 'canonical': 1, 'ball': 2,
            'interval': 2, 'not_nan': 1}
REQUIRES_FINITE = ('normalized', 'abs_ge', 'power_of_two', 'nonneg')
REQUIRES_EXTENDED = ('canonical', 'ball', 'power_of_two', 'nonneg', 'interval', 'not_nan')
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
                  'neighbor', 'bound', 'outward')
ENSURES_EXTENDED = ('normalized', 'error', 'rounded', 'upper', 'predicate', 'encloses', 'extends',
                    'represents', 'makes_ball', 'neighbor', 'bound', 'makes_interval', 'encloses_interval',
                    'set_bound')
# Entries that say something about the value: a kernel needs at least one.
ABOUT_THE_VALUE = ('error', 'leading_rounded', 'rounded', 'upper', 'predicate', 'encloses', 'extends',
                   'represents', 'makes_ball', 'neighbor', 'bound', 'outward', 'makes_interval',
                   'encloses_interval', 'set_bound')
# Entries that name their own set or make a value from the inputs: a kernel whose every entry is one
# of them has no value (Milestone 2: the interval kernels, the one-limb bounds of a ball).
OWN_SET = ('makes_ball', 'makes_interval', 'encloses_interval', 'set_bound')
SIDES_OUTWARD = ('below', 'above')


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
                     consteval_variant, computed_constants, negated_fused):
            errors += rule(k, kernels)
    if not errors:
        errors += ieee_printable(kernels)
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

    def exact_when(e, conds=None, zero=False):
        """The conditions of an exact_when: each EXPR = 0 or |EXPR| > K (or >= K), EXPR over the
        input names and their limbs, K an exact positive expression over u, eta and integers; and,
        where `zero` (outward, and the outward tightness of an interval), EXPR = 0."""
        conds = e.get('exact_when') if conds is None else conds
        if conds is None:
            return
        if not conds:
            err(f'ensures {e["kind"]}: exact_when needs at least one condition')
        for c in conds:
            if set(c) == {ir.ZERO_CONDITION}:
                if not zero:
                    err(f'exact_when {c!r}: zero(EXPR) is a condition of outward and of the outward tightness of '
                        'an interval only')
                    continue
                parsed(c[ir.ZERO_CONDITION], limb_ins, 'exact_when zero', EXACT_TREES)
                continue
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

    def zero_factor(e):
        """zero_factor: the value is the product of two one-limb inputs, and the domain extended."""
        if not e.get('zero_factor'):
            return
        try:
            tree = expr.parse(k.value or '')
        except expr.ExprError:
            return
        if not k.extended or tree[0] != 'mul' or any(t[0] != 'name' or t[1] not in one_limb_ins for t in tree[1:]):
            err(f'{e["kind"]} zero_factor: the value is the product of two one-limb inputs, in the extended domain')

    def claim_constants(e, keys):
        """The constants of a claim (rel and abs): the language of up(EXPR), unit(K) and tiny(K) of a
        kernel with one unconditional relative bound (proved unless this kernel is unverified, its
        minimum precision at most this kernel's), and up(EXPR) of a constant of a kernel with a
        real-model statement, which Model.v defines and both models' statements name; nonnegative in
        binary64 and binary32."""
        model = set()
        for kk in kernels.values():
            for name in ir.constants(kk) if kk.real_model else ():
                if ir.up(name) is not None:
                    try:
                        model.add(consts.up_tree(ir.up(name)))
                    except consts.ConstError:
                        pass
        for key in keys:
            text, before = e[key], len(errs)
            try:
                tree = consts.claim_tree(text)
            except consts.ConstError as x:
                err(f'{e["kind"]} {key}: {x}')
                continue
            for sub in consts.ups(tree):
                if sub not in model:
                    err(f'{e["kind"]} {key}: an up( ) inside it is no constant of a kernel with a real-model '
                        'statement, so Model.v has no definition of it')
            for fn, kname in sorted(expr.calls(tree)):
                callee = kernels.get(kname)
                if callee is None:
                    err(f'{e["kind"]} {key}: {fn}({kname}): {kname} is not a kernel')
                    continue
                try:
                    consts.source_bound(callee)
                except consts.ConstError as x:
                    err(f'{e["kind"]} {key}: {x}')
                    continue
                if callee.status != 'proved' and k.status != 'unverified':
                    err(f'{e["kind"]} {key}: {kname} is {callee.status}: only an unverified kernel may use the '
                        'constants of a bound that is not proved')
                if callee.min_precision and (k.min_precision or 1) < callee.min_precision:
                    err(f'{e["kind"]} {key}: the claims of {kname} hold from precision {callee.min_precision} on, '
                        f'so min_precision must be at least {callee.min_precision}')
            if len(errs) > before:
                continue
            for fmt in ((53, -1074, 971), (24, -149, 104)):
                try:
                    v = consts.claim_constant(text, kernels, *fmt)
                except consts.ConstError as x:
                    err(f'{e["kind"]} {key}: {x}')
                    break
                if v < 0:
                    err(f'{e["kind"]} {key}: {text} is negative in the format {fmt}')
                    break

    makes_balls = bool(k.ensures) and all(e['kind'] in OWN_SET for e in k.ensures)
    if makes_balls:
        if k.value:
            err('a kernel that makes a ball from its inputs has no value' if all(e['kind'] == 'makes_ball' for e in k.ensures)
                else 'a kernel whose claims make an interval from its inputs, or name their own sets, has no value')
    elif not k.value:
        err('no value')
    else:
        parsed(k.value, limb_ins, 'value', VALUE_TREES)
    allowed = REQUIRES_EXTENDED if k.extended else REQUIRES_FINITE
    for req in k.requires:
        n = REQUIRES.get(req[0])
        names = req[1:]
        if n is not None and len(names) == n and all(x in limb_ins for x in names):
            if req[0] not in allowed:
                err(f'requires {" ".join(req)!r}: {req[0]} is not a requirement of the '
                    f'{"extended" if k.extended else "finite"} domain'
                    + (' (canonical stands for normalized there)' if req[0] == 'normalized' else ''))
            elif req[0] in ('power_of_two', 'nonneg') and names[0] not in one_limb_ins:
                err(f'requires {" ".join(req)!r}: {req[0]} is about a one-limb input')
            elif req[0] == 'canonical' and len(ins[names[0]].limbs) < 2:
                err(f'requires {" ".join(req)!r}: canonical is about a multi-limb input (a one-limb '
                    'input is any value)')
            elif req[0] == 'ball' and names[1] not in one_limb_ins:
                err(f'requires {" ".join(req)!r}: the radius of a ball is a one-limb input')
            elif req[0] == 'interval' and (len(ins[names[0]].limbs) != len(ins[names[1]].limbs) or
                                           len(ins[names[0]].limbs) not in (1, 2) or names[0] == names[1]):
                err(f'requires {" ".join(req)!r}: the bounds of an interval are two inputs of one limb each, or '
                    'of two each')
            elif req[0] == 'not_nan' and names[0] not in one_limb_ins:
                err(f'requires {" ".join(req)!r}: not_nan is about a one-limb input')
            continue
        err(f'requires {" ".join(req)!r}: the vocabulary is "normalized INPUT", "abs_ge INPUT INPUT", '
            '"power_of_two INPUT", "nonneg INPUT", and in the extended domain "canonical INPUT", '
            '"ball CENTER RADIUS", "interval LOWER UPPER", "not_nan INPUT"')
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
            if e['form'] not in ('R', 'A'):
                err(f'error form {e["form"]!r}: it is R or A')
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
            zero_factor(e)
        elif kind in SIDES:
            output(e['of'], kind, one=True)
            if e['side'] not in SIDES[kind]:
                err(f'{kind} side {e["side"]!r}: it is {" or ".join(SIDES[kind])}')
            if kind == 'neighbor' and k.value not in one_limb_ins:
                err(f'neighbor: the value is the one-limb operand whose neighbor is the output, not {k.value!r}')
            zero_factor(e)
        elif kind == 'outward':
            output(e['of'], kind)
            if e['of'] in outs and len(outs[e['of']].limbs) != 2:
                err(f'ensures outward of {e["of"]!r}: the output has two limbs')
            if e['side'] not in SIDES_OUTWARD:
                err(f'outward side {e["side"]!r}: it is {" or ".join(SIDES_OUTWARD)}')
            claim_constants(e, ('rel', 'abs'))
            exact_when(e, zero=True)
        elif kind == 'makes_interval':
            _makes_interval(e, k, ins, outs, err)
        elif kind == 'encloses_interval':
            _encloses_interval(e, k, ins, outs, parsed, err, claim_constants, exact_when)
        elif kind == 'set_bound':
            output(e['of'], kind, one=True)
            if e['side'] not in SIDES_OUTWARD:
                err(f'set_bound side {e["side"]!r}: it is {" or ".join(SIDES_OUTWARD)}')
            _encloses(dict(e, center=e['of'], radius=e['of']), k, ins, outs, lambda *a, **kw: None, parsed, err)
            for b, cr in e['balls'].items():
                if ('ball', cr['center'], cr['radius']) not in k.requires:
                    err(f'ball {b}: its operand is required to be a ball: "requires: ball {cr["center"]} '
                        f'{cr["radius"]}"')
            t = e.get('tight')
            if t is not None and (t['kind'] != 'rounded' or set(t) - {'kind', 'steps'}):
                err('set_bound: tight is rounded, with optional steps')
        elif kind == 'upper':
            output(e['of'], kind, one=True)
            tree = parsed(e['gaps'], set(), 'gaps')
            if tree is not None and not expr.evaluate(tree, {}) > 0:
                err(f'gaps={e["gaps"]}: the number of gaps is positive')
        elif kind == 'predicate':
            output(e['of'], kind, kind=ir.MASK)
            if e['rel'] not in RELATIONS:
                err(f'predicate relation {e["rel"]!r}: it is {", ".join(RELATIONS)}')
            for a in e['args']:
                parsed(a, limb_ins, 'predicate argument', VALUE_TREES)
        elif kind == 'encloses':
            _encloses(e, k, ins, outs, output, parsed, err)
            if not e['balls'] and k.extended:
                err('encloses names no ball: in the extended domain the special states are those of balls')
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
            if 'lower' in e['from']:
                # A ball from the bounds of an interval (Milestone 2): two one-limb inputs, any values.
                for what in ('lower', 'upper'):
                    g = ins.get(e['from'][what])
                    if g is None or g.kind != ir.LIMB or len(g.limbs) != 1:
                        err(f'makes_ball from {what} {e["from"][what]!r}: not a one-limb limb input')
                for c in e.get('midpoint_when', []):
                    if c.get('half_in_format') not in e['from'].values():
                        err(f'midpoint_when {c!r}: half_in_format names a bound the ball is made from')
                continue
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
    # Without a ball the operands are points, and the claim is an error bound by an output
    # (add_ball_2_2, mul_ball_2_2): allowed in the finite domain only (claims()).
    points = {n for n, g in ins.items() if g.kind == ir.LIMB and n not in taken}
    parsed(e['set'], set(e['balls']) | points, 'encloses set', VALUE_TREES)


def _makes_interval(e, k, ins, outs, err):
    """An interval made from two bounds (Milestone 2): two limb outputs and two limb inputs of one
    limb each (or of two, canonical, for interval_make_2)."""
    n = None
    for side in ('lower', 'upper'):
        o, i = outs.get(e[side]), ins.get(e['from'][side])
        if o is None or o.kind != ir.LIMB:
            err(f'makes_interval {side} {e[side]!r}: not a limb output')
            return
        if i is None or i.kind != ir.LIMB:
            err(f'makes_interval from {side} {e["from"][side]!r}: not a limb input')
            return
        n = n or len(o.limbs)
        if len(o.limbs) != n or len(i.limbs) != n or n not in (1, 2):
            err('makes_interval: the bounds given and returned have one limb each, or two each')
            return
    if n == 2:
        for side in ('lower', 'upper'):
            if ('canonical', e['from'][side]) not in k.requires:
                err(f'makes_interval: a bound of two limbs is required to be canonical: '
                    f'"requires: canonical {e["from"][side]}"')


def _encloses_interval(e, k, ins, outs, parsed, err, claim_constants, exact_when):
    """I1 to I5 of an interval kernel (Milestone 2): the result's bounds are limb outputs of the
    same number of limbs, each interval name is an `interval` requirement, the set an expression over
    those names, the tightness one of the vocabulary, and the conditions of bounded_when are on the
    members of the exact range (abs_le(SET, ...))."""
    lo, hi = outs.get(e['lower']), outs.get(e['upper'])
    if lo is None or hi is None or lo.kind != ir.LIMB or hi.kind != ir.LIMB or len(lo.limbs) != len(hi.limbs) \
            or len(lo.limbs) not in (1, 2):
        err('encloses_interval: lower and upper are limb outputs of one limb each, or of two each')
        return
    taken = set()
    for name, b in e['intervals'].items():
        if name in ins or name in outs or name in k.input_limbs + k.output_limbs or not ir.VALUE_NAME.match(name):
            err(f'interval name {name!r} is the name of a group, a limb, or not a value name')
        if ('interval', b['lower'], b['upper']) not in k.requires:
            err(f'interval {name}: its operand is required to be an interval: "requires: interval {b["lower"]} '
                f'{b["upper"]}"')
        elif len(ins[b['lower']].limbs) != len(lo.limbs):
            err(f'interval {name}: its bounds have as many limbs as those of the result')
        if taken & {b['lower'], b['upper']}:
            err(f'interval {name}: a bound belongs to two intervals')
        taken |= {b['lower'], b['upper']}
    if not 1 <= len(e['intervals']) <= 2:
        err('encloses_interval names one or two intervals (range_1 and range_2 of the statements)')
    tree = parsed(e['set'], set(e['intervals']), 'encloses_interval set', VALUE_TREES)
    t = e['tight']
    if t['kind'] == 'rounded':
        if len(lo.limbs) != 1:
            err('tight=rounded is about bounds of one limb')
        if 'when' in t:
            if t['when'] not in WHEN:
                err(f'tight when={t["when"]!r}: the vocabulary is {", ".join(WHEN)}')
            elif tree is not None and (tree[0] != 'mul' or any(x[0] != 'name' for x in tree[1:])):
                err('tight when=product_large: the set is the product of two intervals')
    elif t['kind'] == 'outward':
        claim_constants(t, ('rel', 'abs'))
        for conds in t.get('exact_when', {}).values():
            exact_when(e, conds, zero=True)
    for c in e['bounded_when']:
        try:
            same = expr.parse(c['abs_le']) == expr.parse(e['set'])
        except expr.ExprError:
            same = False
        if not same:
            err(f'bounded_when {c["abs_le"]!r}: a condition is on the members of the exact range: abs_le(SET, ...) '
                'with the set of the claim')
    if e.get('bounded_exactly') and not e['bounded_when']:
        err('bounded_exactly needs a condition of bounded_when')


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


def negated_fused(k, kernels):
    """No value is the negation of the result of a fused operation (fma, fms, fnma, prod), the
    callees inlined. Compilers fold such a negation into the fused instruction (fnmadd, vfnmsub):
    where the fused result is also used as it is, that is one fused instruction more than the IR
    asks for, which the object-code check refuses; and where the fused result is an exact zero the
    folded instruction gives +0 where the negation gives -0, so that the kernel has no single
    bit-exact result. The values do not need it: rounding to nearest is symmetric, so the negation
    can be put on an operand (gen/README.md, "The tests").

    The same holds of the negation of a select one of whose arms is a fused result (and of a select
    of such a select, or a copy of one): compilers push the negation through the select into the
    arm, -(m ? d : 0) being (m ? -d : -0), and fold it there (Apple clang's fnmadd and GCC 13's
    vfnmsub on the radius of the directed sums of two limbs, before add_down_2_2 was written
    without it)."""
    prims = ir.prims(k, kernels)
    defs = {p.dst: p for p in prims}
    own = {d for st in k.body for d in st.dsts}

    def fused_arms(name, seen=()):
        """The fused results that `name` is, or that a select or copy makes it, through selects."""
        p = defs.get(name)
        if p is None or name in seen:
            return []
        if p.op in ir.FUSED:
            return [name]
        arms = p.args[1:] if p.op == 'select' else p.args if p.op == 'copy' else ()
        return [f for a in arms if not a.const for f in fused_arms(a.name, seen + (name,))]

    errs = []
    for p in prims:
        if p.op != 'neg' or p.args[0].const:
            continue
        src = p.args[0].name
        fused = fused_arms(src)
        if not fused:
            continue
        where = '' if p.dst in own else ' (inside a call: a callee negates its operand, as sub_down_1 and sub_up_1 ' \
                                        'negate their second)'
        if fused == [src]:
            what = f'negates the result of {defs[src].op}{where}'
        else:
            what = (f'negates a {defs[src].op} one of whose arms, {fused[0]}, is the result of {defs[fused[0]].op}'
                    f'{where}; compilers push a negation through a select into its arms')
        errs.append(RuleError(k.name, p.dst, NEGATED_FUSED,
                              f'{p.dst} = neg({src}) {what}. Negate an operand '
                              'instead: -prod(a, b) is prod(neg(a), b), -fma(a, b, c) is fma(neg(a), b, neg(c)); '
                              'and a rounding down of x - d is minus the rounding up of d - x, so sub_down_1(x, d) '
                              'is neg(add_up_1(d, neg(x))) and sub_up_1(x, d) is neg(add_down_1(d, neg(x)))'))
    return errs


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
