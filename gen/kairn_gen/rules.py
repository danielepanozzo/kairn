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
WELL_FORMED = 'well-formed'
CLAIMS = 'claims'
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
                        'succ', 'pred', 'copy'})
MASK_OPS = frozenset(op for op, (_, result) in ir.OPS.items() if result == ir.MASK)
# Rule 4: operations that map any non-finite operand to a non-finite result. Not select (it may
# drop the operand), not succ/pred (succ(-inf) is finite), not comparisons.
PROPAGATING = frozenset({'add', 'sub', 'fma', 'fms', 'fnma', 'prod', 'muladd', 'neg', 'abs', 'mul',
                         'copy'})
# The closed vocabulary of the claims (architecture.md, "Claims" and "Claims of the second wave").
REQUIRES = {'normalized': 1, 'abs_ge': 2, 'power_of_two': 1, 'nonneg': 1}
ROUNDING_MODES = ('nearest', 'down', 'up')
RELATIONS = ('lt', 'le', 'eq')
VALUE_TREES = {'name', 'add', 'sub', 'mul', 'neg', 'abs'}
# Entries that say something about the value: a kernel needs at least one.
ABOUT_THE_VALUE = ('error', 'leading_rounded', 'rounded', 'upper', 'predicate', 'encloses')


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
        for rule in (products, outputs, nonfinite_cone, theorem, claims, consteval_variant,
                     computed_constants):
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
                if a.name != ir.ZERO and a.name not in ir.CONSTANTS and not ir.computed(a.name):
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
    """Rule 5: every kernel names its theorem, its source and the source's license, or is unverified."""
    errs = []
    if k.status not in STATUSES:
        return [RuleError(k.name, '-', RULE_THEOREM,
                          f'status is {k.status!r}; it must be one of {", ".join(STATUSES)}')]
    if k.status != 'unverified':
        for what, have in (('theorem', k.theorem), ('source', k.source), ('license', k.license)):
            if not have:
                errs.append(RuleError(k.name, '-', RULE_THEOREM,
                                      f'the kernel is not marked unverified and names no {what}'))
    if k.theorem:
        path, name = k.theorem
        if name != f'{k.name}_correct':
            errs.append(RuleError(k.name, '-', RULE_THEOREM,
                                  f'the theorem must be named {k.name}_correct, not {name}'))
        if not (path.startswith('proofs/theories/') and path.endswith('.v')):
            errs.append(RuleError(k.name, '-', RULE_THEOREM,
                                  f'the theorem file must be proofs/theories/*.v, not {path}'))
    return errs


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

    if not k.value:
        err('no value')
    else:
        parsed(k.value, limb_ins, 'value', VALUE_TREES)
    for req in k.requires:
        n = REQUIRES.get(req[0])
        names = req[1:]
        if n is not None and len(names) == n and all(x in limb_ins for x in names):
            if req[0] in ('power_of_two', 'nonneg') and names[0] not in one_limb_ins:
                err(f'requires {" ".join(req)!r}: {req[0]} is about a one-limb input')
            continue
        err(f'requires {" ".join(req)!r}: the vocabulary is "normalized INPUT", "abs_ge INPUT INPUT", '
            '"power_of_two INPUT", "nonneg INPUT"')
    if not any(e['kind'] in ABOUT_THE_VALUE for e in k.ensures):
        err(f'ensures says nothing about the value: it needs an entry of kind {", ".join(ABOUT_THE_VALUE)}')
    for e in k.ensures:
        kind = e['kind']
        if kind in ('normalized', 'leading_rounded'):
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
    if k.min_precision is not None and k.min_precision < 1:
        err('min_precision must be at least 1')
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
