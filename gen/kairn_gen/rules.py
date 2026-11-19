"""The checks every kernel passes before anything is generated (architecture.md, "The kernel IR").

Each rule is a short traversal of the kernel's dataflow graph and refuses with a message that
names the kernel, the value and the rule. Nothing is printed for any kernel while one is refused.
"""
from . import consts, cpp, expr, ir, rocq, simd

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
                         'copy', 'guard'})
# The closed vocabulary of the claims (architecture.md, "Claims", "Claims of the second wave" and
# "Claims of the non-finite layer"): requirements and their number of operands.
REQUIRES = {'normalized': 1, 'abs_ge': 2, 'power_of_two': 1, 'nonneg': 1, 'canonical': 1, 'ball': 2}
REQUIRES_FINITE = ('normalized', 'abs_ge', 'power_of_two', 'nonneg')
REQUIRES_EXTENDED = ('canonical', 'ball', 'power_of_two', 'nonneg')
ROUNDING_MODES = ('nearest', 'down', 'up')
RELATIONS = ('lt', 'le', 'eq')
LEADS = ('add', 'sub', 'mul')
VALUE_TREES = {'name', 'add', 'sub', 'mul', 'neg', 'abs'}
# The kinds of ensures entries in each domain.
ENSURES_FINITE = ('normalized', 'leading_rounded', 'error', 'rounded', 'upper', 'predicate', 'encloses')
ENSURES_EXTENDED = ('normalized', 'error', 'rounded', 'upper', 'predicate', 'encloses', 'extends',
                    'represents', 'makes_ball')
# Entries that say something about the value: a kernel needs at least one.
ABOUT_THE_VALUE = ('error', 'leading_rounded', 'rounded', 'upper', 'predicate', 'encloses', 'extends',
                   'represents', 'makes_ball')


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
    return errors


def well_formed(k, kernels):
    """Rule 1 (single assignment, use after definition, no unused value), names, kinds, arity."""
    errs = []

    def err(value, rule, msg):
        errs.append(RuleError(k.name, value, rule, msg))

    reserved = rocq.RESERVED | cpp.RESERVED | simd.RESERVED
    if k.name in reserved:
        err('-', WELL_FORMED, f'{k.name} is a name the printers use')
    if k.name.endswith(('_spec', '_correct', '_audit')) or k.name.startswith(('fuse_',) + ir.COMPUTED):
        err('-', WELL_FORMED, f'{k.name}: the Rocq printer makes names ending in _spec, _correct and '
                              '_audit, and starting with fuse_, unit_computed and tiny_computed')
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
                        and not ir.computed(a.name):
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
    """R1: no plain multiplication, so that no compiler can contract a product into an addition."""
    errs = []
    uses = {}
    for st in k.body:
        for i, a in enumerate(st.args):
            if not a.const:
                uses.setdefault(a.name, []).append((st, i))

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
    passed through guard; a value passed to another kernel must be treated so there too.

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
    hits, relied, _ = r3_analysis(k, kernels, frozenset(program))
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

    makes_balls = bool(k.ensures) and all(e['kind'] == 'makes_ball' for e in k.ensures)
    if makes_balls:
        if k.value:
            err('a kernel that makes a ball from its inputs has no value')
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
            continue
        err(f'requires {" ".join(req)!r}: the vocabulary is "normalized INPUT", "abs_ge INPUT INPUT", '
            '"power_of_two INPUT", "nonneg INPUT", and in the extended domain "canonical INPUT", '
            '"ball CENTER RADIUS"')
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
            if e['when'] not in (None, 'product_large'):
                err(f'when={e["when"]!r}: the vocabulary is product_large')
        elif kind == 'rounded':
            output(e['of'], kind, one=True)
            if e['mode'] not in ROUNDING_MODES:
                err(f'rounded mode {e["mode"]!r}: it is {", ".join(ROUNDING_MODES)}')
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
        err('-', 'a full kernel or a constructor (extends, represents, makes_ball, or a ball requirement) '
                 'is of the extended domain')
    for e in k.ensures:
        if 'finite_when' in e and e['kind'] == 'encloses' and not k.extended:
            err('-', 'finite_when belongs to the extended domain')
    if k.real_model:
        for st in k.body:
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
