"""The checks every kernel passes before anything is generated (architecture.md, "The kernel IR").

Each rule is a short traversal of the kernel's dataflow graph and refuses with a message that
names the kernel, the value and the rule. Nothing is printed for any kernel while one is refused.
"""
import re
from dataclasses import dataclass
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
REQUIRES = {'normalized': 1, 'abs_ge': 2, 'power_of_two': 1, 'nonneg': 1, 'canonical': 1, 'ball': 2, 'count': 1,
            'interval': 2, 'not_nan': 1}
REQUIRES_FINITE = ('normalized', 'abs_ge', 'power_of_two', 'nonneg', 'count')
REQUIRES_EXTENDED = ('canonical', 'ball', 'power_of_two', 'nonneg', 'interval', 'not_nan')
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
                  'neighbor', 'bound', 'holds', 'maximum', 'outward')
ENSURES_EXTENDED = ('normalized', 'error', 'rounded', 'upper', 'predicate', 'encloses', 'extends',
                    'represents', 'makes_ball', 'neighbor', 'bound', 'finite_or_nan', 'makes_interval',
                    'encloses_interval', 'set_bound', 'outward', 'interval_set', 'ball_of_interval', 'interval_of_ball',
                    'splits', 'certain', 'trit', 'ball_set', 'ball_splits')
# Entries that say something about the value: a kernel needs at least one.
ABOUT_THE_VALUE = ('error', 'leading_rounded', 'rounded', 'upper', 'predicate', 'encloses', 'extends',
                   'represents', 'makes_ball', 'neighbor', 'bound', 'holds', 'finite_or_nan', 'maximum', 'outward',
                   'makes_interval', 'encloses_interval', 'set_bound', 'interval_set', 'ball_of_interval',
                   'interval_of_ball', 'splits', 'certain', 'trit', 'ball_set', 'ball_splits')
# The forms of an error entry: relative to |value| (R), to the sum of the magnitudes of the inputs
# (A), to the sum of the magnitudes of the terms of value (T: s+x*y gives |s| + |x*y|).
ERROR_FORMS = ('R', 'A', 'T')
# Entries that name their own set or make a value from the inputs: a kernel whose every entry is one
# of them has no value (Milestone 2: the interval kernels, the one-limb bounds of a ball, and the
# set operations, the conversions and the split of the enclosure interface).
OWN_SET = ('makes_ball', 'makes_interval', 'encloses_interval', 'set_bound', 'interval_set', 'ball_of_interval',
           'interval_of_ball', 'splits', 'certain', 'trit', 'ball_set', 'ball_splits')
SIDES_OUTWARD = ('below', 'above')
# The set operations of interval_set, and the special values of ball_of_interval (Milestone 2).
SET_OPERATIONS = ('union', 'intersection')
BALL_SPECIALS = ('ieee1788', 'ball')
# The relations of the predicates of sets (Milestone 2, the enclosure interface): certain takes all
# of them, trit those that have a three-valued reading, of every choice of members.
CERTAIN_RELATIONS = tuple(ir.SET_RELATION_ARITY)
TRIT_RELATIONS = ('lt', 'le', 'eq', 'member')
ORDER_RELATIONS = ('lt', 'le', 'eq')


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
    if not errors:
        for fd in getattr(kernels, 'folds', {}).values():
            errors += fold_rules(fd, kernels)
    if not errors:
        errors += factor_rule(kernels)
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
    errs += doubling(k, kernels)
    return errs


def doubling(k, kernels):
    """R1, for a product that the compiler writes itself: an addition of a value to itself. GCC 13
    writes a + a as a * 2 and, under -ffp-contract=fast, contracts that product into the addition
    that follows (measured by the object-code check on the first listings of bound_sum_2 and
    bound_dot_2, at -O2 and -O3, scalar code). Checked on the listing with its calls inlined and
    through copies, so that a callee given one value twice is seen. A doubling is written
    prod(a, const up(2)): exact, and the opaque product."""
    errs, alias = [], {}
    for it in ir.flatten(k, kernels):
        if not isinstance(it, ir.Prim):
            continue
        args = [('const', a.name) if a.const else alias.get(a.name, a.name) for a in it.args]
        if it.op == 'copy':
            alias[it.dst] = args[0]
        elif it.op == 'add' and args[0] == args[1] and not isinstance(args[0], tuple):
            errs.append(RuleError(k.name, it.dst, RULE_R1,
                                  f'{it.dst} = add({args[0]}, {args[0]}) adds a value to itself, which a '
                                  'compiler writes as a product by 2 and may contract into an addition that '
                                  'follows (GCC 13 under -ffp-contract=fast); write prod(a, const up(2)), '
                                  'exact and the opaque product'))
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
    # The theorems of the IEEE-model statements of a kernel of the finite domain: each names the
    # statement it proves by its name, and only a statement the kernel has.
    named = [(key, getattr(k, key), ir.IEEE_THEOREM_NAMES[key].format(k.name)) for key in ir.IEEE_THEOREM_KEYS]
    # A kernel of the extended domain names the theorem of its IEEE-model statement as its
    # ieee_theorem; it has no bridge or spec statement, but a step of a fold of the extended domain
    # has a leading-limb statement, whose theorem is its ieee_lead_theorem.
    if k.extended and (k.ieee_bridge_theorem or k.ieee_spec_theorem):
        err('ieee_bridge_theorem and ieee_spec_theorem belong to kernels of the finite domain (one of the '
            'extended domain names its ieee_theorem)')
    if k.ieee_bridge_theorem and 'bridge' not in k.ieee:
        err('an ieee_bridge_theorem proves K_ieee_bridge_spec, which the kernel has only with "ieee: bridge"')
    if k.ieee_spec_theorem and 'spec' not in k.ieee:
        err('an ieee_spec_theorem proves K_ieee_spec, which the kernel has only with "ieee: spec"')
    if k.ieee_lead_theorem and k.name not in {x.name for x in ieee.lead_kernels(kernels)}:
        err('an ieee_lead_theorem proves K_ieee_lead_spec, which only the step or the combination of '
            'a fold has')
    for what, have, want in [('theorem', k.theorem, f'{k.name}_correct'), ('ieee_theorem', k.ieee_theorem, None)] + named:
        if not have:
            continue
        path, name = have
        if want and name != want:
            err(f'the {what} must be named {want}, not {name}')
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


# --- R3 and the factors of a fused operation (a report, not a refusal) ----------------------------
#
# R3 asks no guard of a value of the program that is only multiplied: nothing can be fused into a
# product. That holds of the product alone, and not of a fused operation whose other factor the
# compiler sees to be 1 or -1 after inlining: LLVM rewrites fma(x, 1, s) as x + s, and a product
# x = a * b of the program is then fused into that addition (architecture.md, "R3", the factors).
# The sound criterion: a value of the program is EXPOSED where it is a factor of a fused operation
# (fma, fms, fnma, muladd) whose addend is not the literal zero of the listing, on a path that has
# not passed through guard. A factor of prod, emitted fma(a, b, +0), is safe: whatever a compiler
# does with the product a * b inside it, fma(a * b, 1, +0) fused is RN(a b + 0), the rounding of the
# product itself, which is what the program's product is. These functions list the exposed
# operands; they refuse nothing, and the decision to guard them is the owner's.
FACTORS = {'fma': (0, 1), 'fms': (0, 1), 'fnma': (0, 1), 'muladd': (0, 1)}
ADDEND = {'fma': 2, 'fms': 2, 'fnma': 2, 'muladd': 2}


def exposed_analysis(k, kernels, tainted):
    """The factors of fused operations that the values `tainted` of kernel k reach unguarded:
    (hits, out), hits [(where, origins)], one per factor, with the route to it and the inputs of k
    it comes from; out {output value of k: origins} for the outputs that are such a value (as in
    r3_analysis: neg, abs, select and copy forward a value, guard ends it, a call is followed into
    the callee)."""
    origin = {v: frozenset([v]) for v in tainted}
    hits = []
    for st in k.body:
        args = [None if a.const else origin.get(a.name) for a in st.args]
        if st.is_call:
            callee = kernels[st.op]
            passed = {callee.input_limbs[i]: o for i, o in enumerate(args) if o}
            if not passed:
                continue
            sub_hits, sub_out = exposed_analysis(callee, kernels, frozenset(passed))
            for where, o in sub_hits:
                hits.append((f'{where} in {st.op} (called for {st.dsts[0]})',
                             frozenset().union(*(passed[x] for x in o))))
            for d, v in zip(st.dsts, callee.output_limbs):
                if v in sub_out:
                    origin[d] = frozenset().union(*(passed[x] for x in sub_out[v]))
            continue
        if st.op in FACTORS:
            addend = st.args[ADDEND[st.op]]
            if not (addend.const and addend.name == ir.ZERO):
                for i in FACTORS[st.op]:
                    if args[i]:
                        hits.append((f'a factor of {st.op} at {st.dsts[0]}', args[i]))
        forwarded = [args[i] for i in FORWARDING.get(st.op, ()) if args[i]]
        if forwarded:
            origin[st.dsts[0]] = frozenset().union(*forwarded)
    return hits, {v: origin[v] for v in k.output_limbs if v in origin}


@dataclass
class Exposed:
    """One object with exposed operands: an entry kernel, or a loop (a fold, a map, a convolution, a
    ball vector) through the kernel that takes what the program supplies. operands: {input limb of
    that kernel: [where, ...]}; ops: the operations of that kernel today (ir.flops, an element of a
    loop); guarded: with a guard on each exposed operand that is not guarded already."""
    kind: str        # 'kernel' or 'loop'
    name: str        # the kernel's or the loop's
    kernel: str      # the kernel analyzed: the kernel itself, or the loop's step (radius, ...)
    role: str        # '' for a kernel; 'step', 'radius', 'step of the coefficients (dot_1)', ...
    operands: dict
    ops: int
    guarded: int


def _exposed_of(kind, name, k, role, tainted, kernels):
    hits, _ = exposed_analysis(k, kernels, frozenset(tainted))
    if not hits:
        return None
    operands = {}
    for where, origins in hits:
        for v in sorted(origins):
            operands.setdefault(v, [])
            if where not in operands[v]:
                operands[v].append(where)
    already = {st.args[0].name for st in k.body if st.op == 'guard' and not st.args[0].const}
    ops = ir.flops(k, kernels)
    return Exposed(kind, name, k.name, role, dict(sorted(operands.items())), ops,
                   ops + len(set(operands) - already))


def _supplied_limbs(fd, call, kernel):
    """The input limbs of `kernel`, called by the line `call` of fold fd, that receive a supplied
    array or a supplied scalar."""
    _, args, _ = call
    by = dict(zip(args, kernel.inputs))
    return [v for a in args if fd.roles.get(a) == 'supplied' and a in by for v in by[a].limbs]


def exposed_operands(kernels):
    """Every exposed operand (the criterion above) of every entry kernel, with what it takes from
    the program (program_values), and of every loop, with what its supplied arrays and scalars give
    its step, its radius (a ball vector) and the step of its coefficients (a convolution): a list
    of Exposed, kernels first, in the order of the kernels and of the folds."""
    out = []
    for k in kernels.values():
        if k.entry:
            e = _exposed_of('kernel', k.name, k, '', k.program_values(), kernels)
            if e:
                out.append(e)
    for fd in getattr(kernels, 'folds', {}).values():
        parts = []
        if fd.step and fd.step[0] in kernels:
            parts.append(('step', kernels[fd.step[0]], _supplied_limbs(fd, fd.step, kernels[fd.step[0]])))
        if fd.radius and fd.radius[0] in kernels:
            parts.append(('radius', kernels[fd.radius[0]], _supplied_limbs(fd, fd.radius, kernels[fd.radius[0]])))
        for key in ('coefficients', 'centers'):
            inner = kernels.folds.get(getattr(fd, key)) if getattr(fd, key) else None
            if inner is None:
                continue
            if inner.coefficients:      # the centers of a product of ball vectors: a convolution
                inner = kernels.folds.get(inner.coefficients)
            if inner is None or not inner.step:
                continue
            step = kernels[inner.step[0]]
            # The arrays of fd are those of the inner fold, in order.
            supplied = {ig.name for g, ig in zip(fd.arrays, inner.arrays) if fd.roles.get(g.name) == 'supplied'}
            by = dict(zip(inner.step[1], step.inputs))
            tainted = [v for a in inner.step[1] if a in supplied for v in by[a].limbs]
            parts.append((f'step of {inner.name}', step, tainted))
        for role, k, tainted in parts:
            e = _exposed_of('loop', fd.name, k, role, tainted, kernels)
            if e:
                out.append(e)
    return out


def fold_kernels(fd, kernels):
    """The kernels a loop runs: its step, combination, record, check, radius, bound and finish, and
    those of the fold of its coefficients or centers."""
    names = set()
    for call in [fd.step, fd.combine, fd.finish, fd.radius, fd.bound] + list(fd.records):
        if call and call[0] in kernels:
            names.add(call[0])
    if fd.check:
        names.add(fd.check)
    for key in ('coefficients', 'centers'):
        inner = getattr(fd, key)
        if inner and inner in kernels.folds:
            names |= fold_kernels(kernels.folds[inner], kernels)
    return names


# The objects of gen/kernels whose exposed operands are not closed yet, each with its reason (the
# owner's decision of 2026-11-21: the strict rule, every exposed operand guarded). R3 refuses an
# exposed operand of any other object, and an entry here that has none; `build` prints the list.
# What is left are the loops over arrays of two limbs and the convolutions, with their steps; no
# compiler was measured to fuse a product of the program into any of them (architecture.md, R3, the
# factors of a fused operation), and each needs new loops with their theorems in both models.
_DOT = ('the step of the dot product and of the coefficients of the convolution of two limbs: closing it '
        'takes the loops dot_2_entry (step dot_entry_step_2, the twin guarding x and y) and conv_2_entry (the '
        'coefficients by dot_2_entry, as conv_1_entry), with their theorems; conv_2 itself is also the loop '
        'of the centers of bv_conv_2, on stored arrays, which must not pay for guards')
_SCALE = ('the step of bv_scale_2 (x stored, a supplied; kairn::scale calls scale_2_entry): closing it '
          'takes a step guarding a only (or a guard of a once, outside the loop, which a fold cannot express '
          'yet), with the theorems of the ball vector; bv_scale_2 is not public on this branch')
_AXPY = ('the step of the axpy of two limbs: its own guards on a and x, which change its listing, so its '
         'bridge and its theorems in both models and those of its loop are to be proved again')
_AXPY_STORED = ('the step of a loop that no header calls, whose description says the program supplies a and '
                'x: its own guards on them, with its theorems and its loop\'s proved again')
FACTOR_PENDING = {
    'dot_step_2': 'dot of two limbs calls it; ' + _DOT,
    'scale_step_2': _SCALE, 'axpy_entry_step_2': _AXPY, 'axpy_entry_step_2_1': _AXPY,
    'axpy_step_2': _AXPY_STORED, 'axpy_step_2_1': _AXPY_STORED,
    'loop axpy_2': 'its step: ' + _AXPY_STORED, 'loop axpy_2_1': 'its step: ' + _AXPY_STORED,
    'loop axpy_2_1_entry': 'its step: ' + _AXPY, 'loop axpy_2_entry': 'its step: ' + _AXPY,
    'loop bv_scale_2': 'its step: ' + _SCALE,
    'loop conv_2': 'its coefficients, dot_2: ' + _DOT,
    'loop dot_2': 'its step: ' + _DOT,
}


def _pending_key(e):
    return e.name if e.kind == 'kernel' else f'loop {e.name}'


def factor_rule(kernels, pending=None):
    """Rule R3 on the factors of a fused operation: an exposed operand (exposed_operands) of an
    entry kernel or of a loop is refused, naming the operand, the operation and the route, unless
    the object is in `pending` (FACTOR_PENDING by default); an entry of `pending` without an
    exposed operand is refused too (remove it). Only the objects of `kernels` are judged."""
    pending = FACTOR_PENDING if pending is None else pending
    errs, found = [], set()
    for e in exposed_operands(kernels):
        key = _pending_key(e)
        found.add(key)
        if key in pending:
            continue
        where = f'the step {e.kernel}' if e.kind == 'loop' and e.role == 'step' else \
            (f'the {e.role} {e.kernel}' if e.kind == 'loop' else '')
        for v, ws in e.operands.items():
            errs.append(RuleError(e.name, v, RULE_R3,
                                  f'{v} enters from the program and is {ws[0]}{" in " + where if where else ""}'
                                  f'{" (and " + str(len(ws) - 1) + " more)" if len(ws) > 1 else ""}: a factor of '
                                  'a fused operation whose addend is not the literal zero, unguarded; a compiler '
                                  'that sees the other factor to be 1 fuses a product of the program into it '
                                  '(fma(x, 1, s) is x + s). Write g = guard(' + v + ') and use g there; a factor '
                                  'of prod alone needs no guard'))
    names = set(kernels) | {f'loop {f}' for f in getattr(kernels, 'folds', {})}
    for key in sorted(set(pending) & names - found):
        errs.append(RuleError(key, '-', RULE_R3, 'listed in FACTOR_PENDING, but nothing of it is exposed: '
                                                 'remove the entry'))
    return errs


def callees(name, kernels):
    """A kernel and every kernel it calls, directly or not."""
    seen, todo = set(), [name]
    while todo:
        n = todo.pop()
        if n in seen or n not in kernels:
            continue
        seen.add(n)
        todo += [st.op for st in kernels[n].body if st.is_call]
    return seen


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

    mask_ins = {n for n, g in ins.items() if g.kind == ir.MASK}

    def exact_when(e, conds=None, zero=False, mask=False, abs_le=False):
        """The conditions of an exact_when: each EXPR = 0 or |EXPR| > K (or >= K), EXPR over the
        input names and their limbs, K an exact positive expression over u, eta and integers; and,
        where `zero` (outward, and the outward tightness of an interval), EXPR = 0; and, where `mask`
        (an upper entry: the radius of the scaling of a BallVector), that a mask input is true; where
        `abs_le` (certain and trit, Milestone 2), |EXPR| <= Omega, EXPR over the input names, and
        only that."""
        conds = e.get('exact_when') if conds is None else conds
        if conds is None:
            return
        if not conds:
            err(f'ensures {e["kind"]}: exact_when needs at least one condition')
        for c in conds:
            if abs_le:
                if set(c) != {'abs_le', 'omega'} or c['omega'] is not True:
                    err(f'exact_when {c!r}: a condition of {e["kind"]} is abs_le(EXPR,omega)')
                    continue
                parsed(c['abs_le'], limb_ins, f'{e["kind"]} exact_when abs_le', VALUE_TREES)
                continue
            if 'abs_le' in c:
                err(f'exact_when {c!r}: abs_le(EXPR,omega) is a condition of certain and trit only')
                continue
            if set(c) == {ir.MASK_CONDITION}:
                if not mask:
                    err(f'exact_when {c!r}: mask(NAME) is a condition of an upper entry only')
                elif c[ir.MASK_CONDITION] not in mask_ins:
                    err(f'exact_when {c!r}: mask(NAME) names a mask input')
                continue
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
        """zero_factor: the value is the product of two inputs, each of one limb or required to be
        canonical (so that it is zero exactly when its leading limb is), and the domain extended."""
        if not e.get('zero_factor'):
            return
        try:
            tree = expr.parse(k.value or '')
        except expr.ExprError:
            return
        if not k.extended or tree[0] != 'mul' or any(
                t[0] != 'name' or (t[1] not in one_limb_ins and ('canonical', t[1]) not in k.requires)
                for t in tree[1:]):
            err(f'{e["kind"]} zero_factor: the value is the product of two inputs, each of one limb or required to '
                'be canonical, in the extended domain')

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
    # The bound kernels of Milestone 2: every entry says what it bounds, and the kernel has no value.
    own_values = bool(k.ensures) and all(e['kind'] in ('holds', 'maximum') or (e['kind'] == 'upper' and 'value' in e)
                                         for e in k.ensures)
    if makes_balls:
        if k.value:
            err('a kernel that makes a ball from its inputs has no value' if all(e['kind'] == 'makes_ball' for e in k.ensures)
                else 'a kernel whose claims make an interval from its inputs, or name their own sets, has no value')
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
        if req[0] == 'at_most':
            # A one-limb input at most a positive integer (g of conv_radius, the exported bound of a
            # dot product, which is at most 1 when it is given), in the finite domain.
            if len(req) != 3 or req[1] not in one_limb_ins or not re.fullmatch(r'[1-9][0-9]*', req[2]):
                err(f'requires {" ".join(req)!r}: "at_most INPUT K", a one-limb input and a positive integer')
            elif k.extended:
                err('requires at_most: a requirement of the finite domain')
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
            elif req[0] == 'interval' and (len(ins[names[0]].limbs) != len(ins[names[1]].limbs) or
                                           len(ins[names[0]].limbs) not in (1, 2) or names[0] == names[1]):
                err(f'requires {" ".join(req)!r}: the bounds of an interval are two inputs of one limb each, or '
                    'of two each')
            elif req[0] == 'not_nan' and names[0] not in one_limb_ins and ('canonical', names[0]) not in k.requires:
                err(f'requires {" ".join(req)!r}: not_nan is about a one-limb input, or a multi-limb input required '
                    'to be canonical (whose leading limb is then not a NaN)')
            continue
        err(f'requires {" ".join(req)!r}: the vocabulary is "normalized INPUT", "abs_ge INPUT INPUT", '
            '"power_of_two INPUT", "nonneg INPUT", "count INPUT", "format half", and in the extended '
            'domain "canonical INPUT", "ball CENTER RADIUS", "interval LOWER UPPER", "not_nan INPUT"')
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
            if 'exact_flag' in e:
                # The mask output that says whether the conditions of exact_when hold (the step of
                # the scaling of a BallVector by a power of two), in the finite domain.
                output(e['exact_flag'], 'error exact_flag', kind=ir.MASK)
                if 'exact_when' not in e or k.extended:
                    err('error exact_flag: the mask of the conditions of exact_when, which the entry has, in the '
                        'finite domain')
        elif kind == 'rounded':
            output(e['of'], kind, one=True)
            if e['mode'] not in ROUNDING_MODES:
                err(f'rounded mode {e["mode"]!r}: it is {", ".join(ROUNDING_MODES)}')
            if 'when' in e and e['when'] not in WHEN:
                err(f'when={e["when"]!r}: the vocabulary is {", ".join(WHEN)}')
            zero_factor(e)
            if 'value' in e:
                # A value of its own: an expression of the inputs and their limbs, as in maximum.
                if k.extended:
                    err('rounded value=: a claim of the finite domain')
                try:
                    tree = expr.parse(e['value'])
                except expr.ExprError as x:
                    err(f'rounded value: {x}')
                    tree = None
                if tree is not None and (expr.names(tree) - limb_ins or not _only(tree, EXACT_TREES)):
                    err(f'rounded value {e["value"]!r}: + - *, unary minus, abs( ), the names of limb inputs and '
                        'their limbs NAME[I]')
                elif tree is not None:
                    for gname, i in sorted(expr.limbs(tree)):
                        if i >= len(ins[gname].limbs):
                            err(f'rounded value {e["value"]!r}: {gname} has {len(ins[gname].limbs)} limbs, so no '
                                f'limb {gname}[{i}]')
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
            zero_factor(e)
            if k.extended and any(('not_nan', g) not in k.requires for g in limb_ins if len(ins[g].limbs) > 1):
                # The extended reading (mul_ext_2_2): the operands are bounds of intervals, never NaN.
                err('outward in the extended domain: its operands of several limbs are required not_nan')
        elif kind == 'interval_set':
            _interval_set(e, k, ins, outs, err)
        elif kind == 'ball_of_interval':
            _ball_of_interval(e, k, ins, outs, err, claim_constants)
        elif kind == 'interval_of_ball':
            _interval_of_ball(e, k, ins, outs, parsed, err, claim_constants, exact_when)
        elif kind == 'splits':
            _splits(e, k, ins, outs, err)
        elif kind == 'ball_set':
            _ball_set(e, k, ins, outs, err)
        elif kind == 'ball_splits':
            _ball_splits(e, k, ins, outs, err)
        elif kind in ('certain', 'trit'):
            _certain(e, k, ins, outs, err)
            if 'exact' in e and 'exact_when' in e:
                err(f'{kind}: exact and exact_when exclude each other')
            if 'exact' in e and e['exact'] is not True:
                err(f'{kind}: exact is true or absent')
            exact_when(e, abs_le=True)
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
            if 'gaps' not in e and 'value' not in e:
                err('upper: an entry says how far above (gaps=) or what it bounds (value=), or both')
            if 'gaps' in e:
                tree = parsed(e['gaps'], set(), 'gaps')
                if tree is not None and not expr.evaluate(tree, {}) > 0:
                    err(f'gaps={e["gaps"]}: the number of gaps is positive')
            if 'value' in e:
                # The magnitude of an input too: |a| rx, the radius of a ball times a number of T.
                _constant_expression(e['value'], limb_ins | (one_limb_outs - {e['of']}), k, kernels, err,
                                     'upper value', CONSTANT_TREES | {'abs'})
            if 'if' in e and e['if'] not in mask_outs:
                err(f'upper if={e["if"]}: the condition is a mask output')
            # unless: the bound when a mask input is false; exact_when: the output is the value
            # exactly when the conditions hold, one of them possibly a mask input (mask(NAME)). Of an
            # entry with a value of its own and no other condition, in the finite domain.
            if ('unless' in e or 'exact_when' in e) and ('value' not in e or 'if' in e or 'gaps' in e or k.extended):
                err('upper unless= and exact_when=: of an entry with a value of its own, without if= or gaps=, in the '
                    'finite domain')
            if 'unless' in e and e['unless'] not in mask_ins:
                err(f'upper unless={e["unless"]}: the condition is a mask input')
            if 'unless' in e and 'exact_when' in e:
                err('upper: unless= and exact_when= are two entries')
            exact_when(e, mask=True)
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
            if 'if' in e and (e['if'] not in ins or ins[e['if']].kind != ir.MASK):
                err(f'finite_or_nan if={e["if"]}: the condition is a mask input')
            if 'steps' in e and (e['steps'] < 1 or g is None or len(g.limbs) != 1):
                err(f'finite_or_nan steps={e["steps"]}: a number of steps up, at least 1, from a one-limb value')
            if e.get('nonneg') and ('if' not in e or 'steps' in e or g is None or len(g.limbs) != 1):
                err('finite_or_nan nonneg: the finish of a constructor, of a one-limb value under a mask (if=), '
                    'without steps')
            if 'if_all' in e and (len(set(e['if_all'])) != len(e['if_all']) or len(e['if_all']) < 2 or
                                  any(n not in ins or ins[n].kind != ir.MASK for n in e['if_all']) or
                                  set(e) & {'if', 'steps', 'nonneg'} or g is None or len(g.limbs) != 1):
                err('finite_or_nan if_all: two mask inputs or more, distinct, of a one-limb value, without if, steps '
                    'or nonneg (the finish of the product of two BallVectors)')
        elif kind == 'maximum':
            output(e['of'], kind, one=True)
            for a in e['args']:
                try:
                    tree = expr.parse(a)
                except expr.ExprError as x:
                    err(f'maximum: {x}')
                    continue
                if expr.names(tree) - limb_ins or not _only(tree, EXACT_TREES):
                    err(f'maximum {a!r}: + - *, unary minus, abs( ), the names of limb inputs and their limbs NAME[I]')
                    continue
                for gname, i in sorted(expr.limbs(tree)):
                    if i >= len(ins[gname].limbs):
                        err(f'maximum {a!r}: {gname} has {len(ins[gname].limbs)} limbs, so no limb {gname}[{i}]')
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
                if ('rel' in e) != ('abs' in e) or ('smallest_radius' in e and 'rel' not in e):
                    err('makes_ball from an interval: rel and abs go together, and smallest_radius with them')
                if 'rel' in e:
                    claim_constants(e, ('rel', 'abs'))
                if e.get('smallest_radius') not in (None, True):
                    err('makes_ball smallest_radius: true or left out')
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
    if e.get('zero_factor') and (tree is None or tree[0] != 'mul' or any(x[0] != 'name' for x in tree[1:])):
        err('encloses_interval zero_factor: the set is the product of two intervals')


def _interval_bounds(name, outs, err, what):
    """The number of limbs of an output group that is a bound of an interval (1 or 2), or None."""
    g = outs.get(name)
    if g is None or g.kind != ir.LIMB or len(g.limbs) not in (1, 2):
        err(f'{what} {name!r}: not a limb output of one limb or two')
        return None
    return len(g.limbs)


def _interval_operand(b, k, ins, err, what):
    """The number of limbs of an interval operand {lower, upper} of an `interval` requirement, or None."""
    if ('interval', b['lower'], b['upper']) not in k.requires:
        err(f'{what}: its operand is required to be an interval: "requires: interval {b["lower"]} {b["upper"]}"')
        return None
    return len(ins[b['lower']].limbs)


def _interval_set(e, k, ins, outs, err):
    """The hull or the intersection of two intervals (Milestone 2): bounds of the result of as many
    limbs as those of the two interval operands, and a set operation of the vocabulary."""
    if e['set'] not in SET_OPERATIONS:
        err(f'interval_set {e["set"]!r}: the set operation is {" or ".join(SET_OPERATIONS)}')
    n = {_interval_bounds(e[side], outs, err, f'interval_set {side}') for side in ('lower', 'upper')}
    if len(e['intervals']) != 2:
        err('interval_set names two intervals')
    taken = set()
    for name, b in e['intervals'].items():
        if name in ins or name in outs or not ir.VALUE_NAME.match(name):
            err(f'interval name {name!r} is the name of a group, or not a value name')
        n.add(_interval_operand(b, k, ins, err, f'interval {name}'))
        if taken & {b['lower'], b['upper']}:
            err(f'interval {name}: a bound belongs to two intervals')
        taken |= {b['lower'], b['upper']}
    if None not in n and len(n) != 1:
        err('interval_set: the bounds of the result and of the operands have as many limbs each')


def _ball_of_interval(e, k, ins, outs, err, claim_constants):
    """A ball made from an interval (Milestone 2: the midpoint and radius of an interval, and its
    conversion to a ball): a center of one or two limbs and a one-limb radius, from the bounds of an
    `interval` requirement, the special values of IEEE 1788 or of a canonical ball, and the constants
    of the center's distance to the midpoint."""
    c, r = outs.get(e['center']), outs.get(e['radius'])
    if c is None or c.kind != ir.LIMB or len(c.limbs) not in (1, 2):
        err(f'ball_of_interval center {e["center"]!r}: not a limb output of one limb or two')
    if r is None or r.kind != ir.LIMB or len(r.limbs) != 1:
        err(f'ball_of_interval radius {e["radius"]!r}: not a one-limb limb output')
    n = _interval_operand(e['from'], k, ins, err, 'ball_of_interval from')
    if n is not None and c is not None and n != len(c.limbs):
        err('ball_of_interval: the center has as many limbs as the bounds of the interval')
    if e['special'] not in BALL_SPECIALS:
        err(f'ball_of_interval special {e["special"]!r}: it is {" or ".join(BALL_SPECIALS)}')
    claim_constants(e, ('rel', 'abs'))
    for cond in e.get('finite_when', []):
        # Stage B2: a condition on a bound of the interval, |bound| <= 2^(qmax + p + E).
        if cond['abs_le'] not in e['from'].values():
            err(f'ball_of_interval finite_when {cond!r}: the condition is about a bound of the interval')
    if 'finite_when' in e and not e['finite_when']:
        err('ball_of_interval finite_when: at least one condition')


def _interval_of_ball(e, k, ins, outs, parsed, err, claim_constants=None, exact_when=None):
    """An interval that encloses a ball (Milestone 2, the conversion of a ball to an interval):
    bounds of one limb with the tightness rounded, or (stage B2) of two limbs with the tightness
    outward, as many limbs as the ball's center; one ball name of a `ball` requirement, its set an
    expression of the ball name; with bounded_when, conditions on the set."""
    t = e['tight']
    n = {_interval_bounds(e[side], outs, err, f'interval_of_ball {side}') for side in ('lower', 'upper')}
    for b, cr in e['balls'].items():
        if cr['center'] in ins:
            n.add(len(ins[cr['center']].limbs))
    if None not in n and len(n) != 1:
        err('interval_of_ball: the bounds of the result have as many limbs as the center of the ball')
    if t['kind'] == 'outward':
        if n != {2}:
            err('interval_of_ball: an outward tightness is of bounds of two limbs')
        if claim_constants is not None:
            claim_constants(t, ('rel', 'abs'))
        for side, conds in t.get('exact_when', {}).items():
            if exact_when is not None:
                exact_when(dict(e, kind='interval_of_ball'), conds, zero=True)
    elif n - {None} and n != {1}:
        err('interval_of_ball: bounds of two limbs have an outward tightness')
    for c in e.get('bounded_when', []):
        if c.get('abs_le') != e['set'] or 'omega' in c:
            err(f'interval_of_ball bounded_when {c!r}: abs_le(SET,E) of the entry\'s set')
    if len(e['balls']) != 1:
        err('interval_of_ball names one ball')
    for b, cr in e['balls'].items():
        if b in ins or b in outs or not ir.VALUE_NAME.match(b):
            err(f'ball name {b!r} is the name of a group, or not a value name')
        if ('ball', cr['center'], cr['radius']) not in k.requires:
            err(f'ball {b}: its operand is required to be a ball: "requires: ball {cr["center"]} {cr["radius"]}"')
    parsed(e['set'], set(e['balls']), 'interval_of_ball set', VALUE_TREES)
    if t['kind'] == 'rounded' and set(t) - {'kind', 'steps'}:
        err('interval_of_ball: tight rounded has optional steps and nothing else')
    if t['kind'] not in ('rounded', 'outward'):
        err('interval_of_ball: tight is rounded, with optional steps, or outward')


def _ball_output(c, r, outs, err, what):
    """The number of limbs of a center output (1 or 2) whose radius output has one limb, or None."""
    gc, gr = outs.get(c), outs.get(r)
    if gc is None or gc.kind != ir.LIMB or len(gc.limbs) not in (1, 2):
        err(f'{what} center {c!r}: not a limb output of one limb or two')
        return None
    if gr is None or gr.kind != ir.LIMB or len(gr.limbs) != 1:
        err(f'{what} radius {r!r}: not a one-limb limb output')
        return None
    return len(gc.limbs)


def _ball_operand(b, k, ins, err, what):
    """The number of limbs of the center of a ball operand {center, radius} of a `ball` requirement."""
    if ('ball', b['center'], b['radius']) not in k.requires:
        err(f'{what}: its operand is required to be a ball: "requires: ball {b["center"]} {b["radius"]}"')
        return None
    return len(ins[b['center']].limbs)


def _ball_set(e, k, ins, outs, err):
    """A ball that contains the union or the intersection of two balls (Milestone 2, the hull and the
    intersection of balls): a canonical ball of as many limbs as the operands', two balls of `ball`
    requirements, a set operation of the vocabulary."""
    if e['set'] not in SET_OPERATIONS:
        err(f'ball_set {e["set"]!r}: the set operation is {" or ".join(SET_OPERATIONS)}')
    n = {_ball_output(e['center'], e['radius'], outs, err, 'ball_set')}
    if len(e['balls']) != 2:
        err('ball_set names two balls')
    taken = set()
    for name, b in e['balls'].items():
        if name in ins or name in outs or not ir.VALUE_NAME.match(name):
            err(f'ball name {name!r} is the name of a group, or not a value name')
        n.add(_ball_operand(b, k, ins, err, f'ball {name}'))
        if taken & {b['center'], b['radius']}:
            err(f'ball {name}: a center or a radius belongs to two balls')
        taken |= {b['center'], b['radius']}
    if None not in n and len(n) != 1:
        err('ball_set: the centers of the result and of the operands have as many limbs each')


def _ball_splits(e, k, ins, outs, err):
    """Two balls that cover the two halves of a ball operand (Milestone 2, the split of a ball): two
    canonical balls of as many limbs as the operand's, a `ball` requirement."""
    n = {_ball_output(p['center'], p['radius'], outs, err, 'ball_splits') for p in e['parts']}
    names = [p[x] for p in e['parts'] for x in ('center', 'radius')]
    if len(set(names)) != 4:
        err('ball_splits: the centers and radii of the parts are four outputs')
    n.add(_ball_operand(e['from'], k, ins, err, 'ball_splits from'))
    if None not in n and len(n) != 1:
        err('ball_splits: the centers of the parts and of the operand have as many limbs each')


def _certain(e, k, ins, outs, err):
    """A predicate of sets (Milestone 2, the enclosure interface), certain (one mask) or trit (two):
    the masks are mask outputs; the relation is of the vocabulary, with its number of arguments; the
    sets are all intervals (of an `interval` requirement) or all balls (of a `ball` requirement),
    each named in the arguments, their bounds or centers and radii inputs of no other set; an
    argument of lt, le and eq is a set or the integer 0, one of them a set; of member, a point (an
    input of one limb, or of two required canonical, no bound of a set) and a set; of the others,
    sets, two distinct ones for a relation between two sets."""
    kind = e['kind']
    masks = [e['yes'], e['no']] if kind == 'trit' else [e['of']]
    for m in masks:
        g = outs.get(m)
        if g is None or g.kind != ir.MASK:
            err(f'{kind}: {m!r} is not a mask output')
    if len(set(masks)) != len(masks):
        err(f'{kind}: yes and no are two masks')
    rel = e['rel']
    allowed = TRIT_RELATIONS if kind == 'trit' else CERTAIN_RELATIONS
    if rel not in allowed:
        err(f'{kind} relation {rel!r}: it is {", ".join(allowed)}')
        return
    sets = e.get('intervals', e.get('balls', {}))
    sort, req = ('ball', ('center', 'radius')) if 'balls' in e else ('interval', ('lower', 'upper'))
    if not sets:
        err(f'{kind}: names at least one set')
    taken = set()
    for name, b in sets.items():
        if name in ins or name in outs or not ir.VALUE_NAME.match(name):
            err(f'{kind}: set name {name!r} is the name of a group, or not a value name')
        if (sort, b[req[0]], b[req[1]]) not in k.requires:
            err(f'{kind} set {name}: its operand is required to be an interval or a ball: "requires: {sort} '
                f'{b[req[0]]} {b[req[1]]}"')
        if taken & {b[req[0]], b[req[1]]}:
            err(f'{kind} set {name}: a bound, center or radius belongs to two sets')
        taken |= {b[req[0]], b[req[1]]}
    args = e['args']
    if len(args) != ir.SET_RELATION_ARITY[rel]:
        err(f'{kind} {rel}: {ir.SET_RELATION_ARITY[rel]} arguments')
        return
    if rel in ORDER_RELATIONS:
        if any(a not in sets and a != ir.ZERO for a in args) or all(a == ir.ZERO for a in args):
            err(f'{kind} {rel}: each argument is a set or 0, and one is a set')
    elif rel == 'member':
        p, s = args
        g = ins.get(p)
        if g is None or g.kind != ir.LIMB or p in taken or \
                not (len(g.limbs) == 1 or ('canonical', p) in k.requires):
            err(f'{kind} member: the point {p!r} is an input of one limb, or of several required canonical, and no '
                'bound of a set')
        if s not in sets:
            err(f'{kind} member: {s!r} is not a set of the entry')
    else:
        if any(a not in sets for a in args) or len(set(args)) != len(args):
            err(f'{kind} {rel}: the arguments are {"a set" if len(args) == 1 else "two distinct sets"} of the entry')
    named = {a for a in args if a in sets}
    if set(sets) - named:
        err(f'{kind}: set {", ".join(sorted(set(sets) - named))} is named by no argument')
    if not k.extended:
        err(f'{kind}: a claim of the extended domain')


def _splits(e, k, ins, outs, err):
    """Two intervals that together are an interval operand (Milestone 2, the split of an interval):
    four bounds of as many limbs as those of the operand, an `interval` requirement."""
    n = {_interval_bounds(p[side], outs, err, f'splits {side}') for p in e['parts'] for side in ('lower', 'upper')}
    names = [p[side] for p in e['parts'] for side in ('lower', 'upper')]
    if len(set(names)) != 4:
        err('splits: the four bounds of the parts are four outputs')
    n.add(_interval_operand(e['from'], k, ins, err, 'splits from'))
    if None not in n and len(n) != 1:
        err('splits: the bounds of the parts and of the operand have as many limbs each')


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


def _constant_expression(text, names, k, kernels, err, what, trees=None):
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
    if not _only(tree, trees or CONSTANT_TREES):
        err(f'{what} {text!r}: only + - * /, integer powers, names, u, eta, integers, unit(K) and tiny(K)' +
            (', abs( )' if trees and 'abs' in trees else ''))
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


# ---------------------------------------------------------------------------------------------
# Folds (milestone2.md, "Folds, the extension of the IR").

FOLD = 'fold'
# The kinds of a fold's claims (architecture.md, "Claims of Milestone 2", "Folds"), and of a fold of
# maxima's ("Folds of maxima").
FOLD_ENSURES = ('normalized', 'fold_error', 'finite_or_nan')
MAX_ENSURES = ('upper', 'finite_or_nan')
# The heights of a fold's bound: n or n - 1, natural numbers (0 - 1 is 0, as in Rocq's nat).
FOLD_HEIGHTS = ('n', 'n-1')
# Names a fold's groups and limbs must not take: the parameters of its C++ functions and the
# section variables of its Rocq model. (The binders of the model and the statements are the name
# of the state, the element, the arrays' names joined, and the list, that and s: fold_binders.)
FOLD_RESERVED = frozenset({'n', 'lanes', 'emin', 'prec', 'choice'})


def fold_binders(fd):
    """The binders of a fold's Rocq model and statements: the state (its groups' names joined: s,
    or mok for m and ok), one element (the arrays' names joined: x, or xy for x and y) and the list
    of elements (xs, xys)."""
    element = ''.join(g.name for g in fd.arrays)
    return ''.join(fd.state_names()), element, element + 's'
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
    if fd.is_map:
        out += [f'{fd.name}_{s}' for s in ('map', 'spec', 'correct', 'audit', 'check')]
    if fd.is_conv:
        out += [f'{fd.name}_{s}' for s in ('conv', 'spec', 'correct', 'audit', 'check', 'ieee_spec', 'ieee_correct',
                                           'ieee_audit')]
    if fd.is_bv:
        out += [f'{fd.name}_{s}' for s in ('map', 'record', 'radius', 'spec', 'correct', 'audit', 'end', 'packed_end',
                                           'exact')]
    if fd.is_bv_conv:
        out += [f'{fd.name}_{s}' for s in ('conv', 'record', 'count', 'bound', 'ok', 'radius', 'spec', 'correct', 'audit', 'end',
                                           'ieee_spec', 'ieee_correct', 'ieee_audit')]
    for order in fd.orders:
        base = f'{fd.name}_{ir.ORDER_SUFFIX.get(order, order)}'
        out += [base, f'{base}_spec', f'{base}_correct', f'{base}_audit', f'{base}_ieee_spec', f'{base}_ieee_correct',
                f'{base}_ieee_audit']
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
    groups = fd.arrays + fd.scalars + list(fd.states) + fd.outputs + fd.writes
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
    # The state: a group of limbs; a map's, one mask; a fold of maxima's, a value of one limb and a
    # mask (FoldsOfMaxima below).
    shapes = [_shape(g) for g in fd.states]
    if fd.is_bv_conv:
        # The product of two BallVectors: the states of two folds of maxima, of the arrays read.
        return errs + bv_conv_rules(fd, kernels, reserved)
    if fd.is_bv:
        # A ball vector: the state of a fold of maxima, and for one exact under conditions a mask of
        # the exactness of every entry; then its own rules.
        if shapes not in ([(1, ir.LIMB), (1, ir.MASK)], [(1, ir.LIMB), (1, ir.MASK), (1, ir.MASK)]):
            err('-', WELL_FORMED, 'the state of a ball vector is that of a fold of maxima: a limb and a mask '
                                  '(state: m, mask ok), and a mask of exactness for one exact under conditions '
                                  '(state: m, mask ok, mask ex)')
            return errs
        return errs + bv_rules(fd, kernels, reserved)
    if len(fd.records) > 1 or len(fd.combines) > 1:
        err('-', WELL_FORMED, 'one record line and one combine line: only a ball vector exact under conditions has '
                              'a second of each, the and of a mask into its state')
        return errs
    writer = fd.is_map or fd.is_conv
    if not fd.states or (not writer and shapes != [(len(fd.state.limbs), ir.LIMB)] and
                         not (fd.is_max and shapes == [(1, ir.LIMB), (1, ir.MASK)])):
        err('-', WELL_FORMED, 'the state is a group of limbs (a mask, for a map; a limb and a mask, for a fold of '
                              'maxima)')
        return errs
    if writer and len(fd.states) != 1:
        err('-', WELL_FORMED, 'the state of a map is one mask (state: mask NAME), true at the start')
        return errs
    binders = fold_binders(fd)
    if len(set(binders)) < 3 or any(b in reserved | {'a', 'b'} for b in binders):
        err('-', WELL_FORMED, f'the binders of the model, {", ".join(binders)} (the state, the arrays\' names '
                              'joined, and that and s), are distinct and none is a name the printers use')
    if not fd.orders or len(set(fd.orders)) < len(fd.orders) or set(fd.orders) - set(ir.ORDERS):
        err('-', WELL_FORMED, f'orders: some of {", ".join(ir.ORDERS)}, each once')
    if fd.is_conv:
        return errs + conv_rules(fd, kernels, reserved)
    if fd.is_map or fd.scalars or fd.check:
        return errs + map_rules(fd, kernels, reserved)
    groups_of = {g.name: g for g in fd.arrays + list(fd.states)}
    names = fd.state_names()
    shapes = [_shape(g) for g in fd.states]
    # The state as a line of a description names it: s, or (m, ok) for a state of two groups.
    st = names[0] if len(names) == 1 else '(' + ', '.join(names) + ')'
    width = f'{len(fd.state.limbs)} limbs' if len(names) == 1 else ', '.join(
        f'{g.name} of {len(g.limbs)} {"mask" if g.kind == ir.MASK else "limb"}' for g in fd.states)

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
        if dsts != names:
            err('-', WELL_FORMED, f'step: it gives the next state, {st} = {step.name}(...)')
        want = sorted(list(names) + [g.name for g in fd.arrays])
        if sorted(args) != want:
            err('-', WELL_FORMED, f'step: its arguments are the state and every array once: {", ".join(want)}')
        elif len(step.inputs) != len(args):
            err('-', WELL_FORMED, f'step: {step.name} takes {len(step.inputs)} groups, not {len(args)}')
        else:
            for a, g in zip(args, step.inputs):
                if _shape(g) != _shape(groups_of[a]):
                    err(a, WELL_FORMED, f'step: {step.name} takes {g.name} of {len(g.limbs)} limbs where the '
                                        f'fold passes {a} of {len(groups_of[a].limbs)}')
        if [_shape(g) for g in step.outputs] != shapes:
            err('-', WELL_FORMED, f'step: {step.name} returns {"one group" if len(names) == 1 else "groups"} of '
                                  f'the shape of the state ({width})')
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
        if dsts != names or args != names + names:
            err('-', WELL_FORMED, f'combine: {st} = {combine.name}({", ".join(names + names)})')
        if [_shape(g) for g in combine.inputs] != shapes * 2 or [_shape(g) for g in combine.outputs] != shapes:
            err('-', WELL_FORMED, f'combine: {combine.name} takes two {"groups" if len(names) == 1 else "states"} '
                                  f'and returns one, each of the shape of the state ({width})')
        if not combine.real_model:
            err('-', DOMAIN, f'combine: {combine.name} has no real-model statement, and the combination is in the '
                             'real model')
    # The finish: the final state to the fold's results.
    finish = kernel_of('finish', fd.finish)
    if finish is not None:
        _, args, dsts = fd.finish
        if args != names:
            err('-', WELL_FORMED, f'finish: it takes the final state, {finish.name}({", ".join(names)})')
        if [_shape(g) for g in finish.inputs] != shapes:
            err('-', WELL_FORMED, f'finish: {finish.name} takes {"one group" if len(names) == 1 else "the groups"} '
                                  'of the shape of the state')
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
    if fd.is_max:
        errs += max_rules(fd, step, combine, finish, kernels)
    elif combine is not None and 'lanes' in fd.orders:
        errs += zero_state(fd, combine, kernels)
    errs += _fold_claims(fd, kernels, step, combine, finish)
    errs += _fold_theorem(fd)
    return errs


# --- Maps -----------------------------------------------------------------------------------------
#
# A map (milestone2.md, "Folds, the extension of the IR": a fold with writes) applies its step to
# every element and writes what the step returns: the step takes the scalars and one element of
# each array, never the state, so that a written element does not depend on the order. The state is
# one mask, which starts true and is combined by `and`, exact, associative and commutative, with
# the test of each written element by the check kernel (its flag: the leading limb is finite); when
# it is false at the end, a second pass writes each element as the check gives it, the canonical NaN
# for one that is not finite (milestone2.md, "When something is not finite"). The zero state of
# `and` is true, a left identity and its own conjunction: andb_true_l of Rocq's Bool stands for
# zero_identity here.
MAP_ENSURES = ('entries', 'finite_or_nan')
MAP_ZERO_LEMMA = 'Bool.andb_true_l'


def map_rules(fd, kernels, reserved):
    """Every refusal of one map, after the names (fold_rules): its parts and their shapes, R3 on
    its supplied arrays and scalars, its claims, its theorem."""
    errs = []

    def err(value, rule, msg):
        errs.append(RuleError(fd.name, value, rule, msg))

    if len(fd.writes) != 1 or any(g.kind != ir.LIMB for g in fd.writes):
        err('-', WELL_FORMED, 'a map writes one array of limbs (writes: NAME = LIMB ...)')
        return errs
    written = fd.writes[0]
    if fd.state.kind != ir.MASK:
        err('-', WELL_FORMED, 'the state of a map is one mask (state: mask NAME), true at the start')
    if not fd.orders or len(set(fd.orders)) < len(fd.orders) or set(fd.orders) - set(ir.ORDERS):
        err('-', WELL_FORMED, f'orders: some of {", ".join(ir.ORDERS)}, each once')
    if fd.combine != ('and', (fd.state.name, fd.state.name), (fd.state.name,)):
        err('-', WELL_FORMED, f'combine: the states of a map are combined by and: {fd.state.name} = '
                              f'and({fd.state.name}, {fd.state.name})')
    if fd.finish is not None or fd.outputs:
        err('-', WELL_FORMED, 'a map returns its state, the mask, and the array it writes: finish: none, and no '
                              'output line')
    groups_of = {g.name: g for g in fd.arrays + fd.scalars}
    step = kernels.get(fd.step[0]) if fd.step else None
    if step is None:
        err('-', WELL_FORMED, f'step: {fd.step[0] if fd.step else "(none)"} is not a kernel')
    else:
        _, args, dsts = fd.step
        if dsts != (written.name,):
            err('-', WELL_FORMED, f'step: it gives the element written, {written.name} = {step.name}(...); a '
                                  "map's step takes no state, so that no element depends on the order")
        want = sorted(groups_of)
        if sorted(args) != want:
            err('-', WELL_FORMED, f'step: its arguments are every scalar and every array once: {", ".join(want)}')
        elif len(step.inputs) != len(args):
            err('-', WELL_FORMED, f'step: {step.name} takes {len(step.inputs)} groups, not {len(args)}')
        else:
            for a, g in zip(args, step.inputs):
                if _shape(g) != _shape(groups_of[a]):
                    err(a, WELL_FORMED, f'step: {step.name} takes {g.name} of {len(g.limbs)} limbs where the '
                                        f'map passes {a} of {len(groups_of[a].limbs)}')
        if len(step.outputs) != 1 or _shape(step.outputs[0]) != _shape(written):
            err('-', WELL_FORMED, f'step: {step.name} returns one group of the shape of {written.name} '
                                  f'({len(written.limbs)} limbs)')
        if not step.real_model:
            err('-', DOMAIN, f'step: {step.name} has no real-model statement, and the step is in the real model')
    check = kernels.get(fd.check) if fd.check else None
    if check is None:
        err('-', WELL_FORMED, f'check: {fd.check or "(none)"} is not a kernel; a map names the kernel that tests '
                              'a written element and gives its canonical NaN (fold_finish_k)')
    elif [_shape(g) for g in check.inputs] != [_shape(written)] or \
            [_shape(g) for g in check.outputs] != [_shape(written), (1, ir.MASK)] or \
            not any(e['kind'] == 'finite_or_nan' for e in check.ensures):
        err('-', WELL_FORMED, f'check: {check.name} takes an element of {written.name} and returns it, or its '
                              'canonical NaN, and the mask that it is finite (finite_or_nan, as fold_finish_k)')
    if errs:
        return errs
    errs += _map_r3(fd, step, kernels)
    errs += _map_claims(fd, kernels, step, check)
    errs += _fold_theorem(fd)
    return errs


# --- Ball vectors -----------------------------------------------------------------------------------
#
# A ball vector (architecture.md, "Ball vectors"; milestone2.md, "BallVector") is a map of the centers
# of BallVectors: its step writes a center per entry, as a map's; its state is that of a fold of
# maxima (the largest magnitude of a leading limb written, and the mask that none was a NaN), updated
# by `record`, the step of that fold, on each center written, and combined by that fold's
# combination; at the end `radius` gives the one radius from the largest magnitude and the radii (and
# the other scalars), and the finish tests it: the result is a finite ball vector exactly when the
# finish's flag is true, and otherwise every center written is zero and the radius +infinity, the
# whole space, in a second pass.
BV_ENSURES = ('encloses_entries',)


def bv_rules(fd, kernels, reserved):
    """Every refusal of one ball vector, after the names (fold_rules)."""
    errs = []

    def err(msg, value='-', rule=WELL_FORMED):
        errs.append(RuleError(fd.name, value, rule, msg))

    if len(fd.writes) != 1 or any(g.kind != ir.LIMB for g in fd.writes):
        err('a ball vector writes one array of centers (writes: NAME = LIMB ...)')
        return errs
    written = fd.writes[0]
    m, ok = fd.states[:2]
    # A ball vector exact under conditions: the state's mask of exactness, and the name the step gives
    # its mask (the second destination of the step line).
    ex = fd.states[2] if len(fd.states) == 3 else None
    binders = fold_binders(fd)
    if len(set(binders)) < 3 or any(b in reserved | {'a', 'b'} for b in binders):
        err(f'the binders of the model, {", ".join(binders)} (the state, the arrays\' names joined, and that and s), '
            'are distinct and none is a name the printers use')
    if fd.check is not None or fd.coefficients is not None:
        err('a ball vector has no check (its finish tests the radius) and no coefficients')
    if not fd.orders or len(set(fd.orders)) < len(fd.orders) or set(fd.orders) - set(ir.ORDERS):
        err(f'orders: some of {", ".join(ir.ORDERS)}, each once')
    # The step: a map's, on the elements and some of the scalars.
    groups_of = {g.name: g for g in fd.arrays + fd.scalars}
    step = kernels.get(fd.step[0]) if fd.step else None
    if step is None:
        err(f'step: {fd.step[0] if fd.step else "(none)"} is not a kernel')
        return errs
    _, args, dsts = fd.step
    emask = None
    if ex is None and dsts != (written.name,):
        err(f'step: it gives the center written, {written.name} = {step.name}(...), and takes no state')
    if ex is not None:
        # Exact under conditions: the step gives the center and the mask that its entry is exact.
        emask = dsts[1] if len(dsts) == 2 else None
        taken = {g.name for g in fd.arrays + fd.scalars + list(fd.states) + fd.outputs + fd.writes} | \
            set(fd.write_limbs())
        if len(dsts) != 2 or dsts[0] != written.name or emask in taken or emask in reserved or emask in kernels:
            err(f'step: it gives the center written and a mask of a name of its own, ({written.name}, E) = '
                f'{step.name}(...)')
            emask = None
    if sorted(a for a in args if a in {g.name for g in fd.arrays}) != sorted(g.name for g in fd.arrays) or \
            len(set(args)) < len(args) or set(args) - set(groups_of):
        err('step: its arguments are every array once, and scalars')
    elif len(step.inputs) != len(args):
        err(f'step: {step.name} takes {len(step.inputs)} groups, not {len(args)}')
    else:
        for a, g in zip(args, step.inputs):
            if _shape(g) != _shape(groups_of[a]):
                err(f'step: {step.name} takes {g.name} of {len(g.limbs)} limbs where the fold passes {a} of '
                    f'{len(groups_of[a].limbs)}', a)
    want_out = [_shape(written)] + ([(1, ir.MASK)] if ex is not None else [])
    if [_shape(g) for g in step.outputs] != want_out:
        err(f'step: {step.name} returns one group of the shape of {written.name}' +
            (', then a mask' if ex is not None else ''))
    if not step.real_model:
        err(f'step: {step.name} has no real-model statement, and the step is in the real model', rule=DOMAIN)
    # The record and the combination: the step and the combination of a fold of maxima of the set
    # whose array has the shape of the centers written (max_rules has checked them there).
    folds = getattr(kernels, 'folds', {})
    want_state = (m.name, ok.name)
    host = [h for h in folds.values() if h.is_max and h.step and fd.record and h.step[0] == fd.record[0] and
            _shape(h.arrays[0]) == _shape(written)]
    if not host:
        err(f'record: {fd.record[0]} is not the step of a fold of maxima of an array of the shape of '
            f'{written.name} (norm_step_k)')
        return errs
    h = host[0]
    if fd.record[1:] != ((m.name, ok.name, written.name), want_state):
        err(f'record: ({m.name}, {ok.name}) = {fd.record[0]}({m.name}, {ok.name}, {written.name})')
    if fd.combine is None or fd.combine[0] != h.combine[0] or \
            fd.combine[1:] != (want_state + want_state, want_state):
        err(f'combine: ({m.name}, {ok.name}) = {h.combine[0]}({m.name}, {ok.name}, {m.name}, {ok.name}), the '
            f'combination of {h.name}')
    # Exact under conditions: the step's mask and-ed into the state's mask of exactness, and two such
    # masks and-ed (exact, associative and commutative, as a map's mask; true is its identity).
    want_records = [fd.record] + ([('and', (ex.name, emask), (ex.name,))] if ex is not None else [])
    want_combines = [fd.combine] + ([('and', (ex.name, ex.name), (ex.name,))] if ex is not None else [])
    if ex is not None and emask is not None and fd.records[1:] != want_records[1:]:
        err(f'record: {ex.name} = and({ex.name}, {emask}), the second record line: the mask of exactness of every '
            'entry')
    elif ex is None and len(fd.records) > 1:
        err('record: one line, the step of a fold of maxima (a second, the and of a mask, only with the mask of '
            'exactness in the state)')
    if fd.combines[1:] != want_combines[1:]:
        err(f'combine: {ex.name} = and({ex.name}, {ex.name}), the second combine line' if ex is not None else
            'combine: one line, the combination of a fold of maxima')
    # The radius: a kernel with a real-model statement, on the state's limb and scalars, to one limb.
    radius = kernels.get(fd.radius[0]) if fd.radius else None
    if radius is None:
        err(f'radius: {fd.radius[0] if fd.radius else "(none)"} is not a kernel')
        return errs
    rname = fd.radius[2]
    if len(rname) != 1 or rname[0] in groups_of or rname[0] in (m.name, ok.name) or rname[0] in reserved or \
            rname[0] in {g.name for g in fd.outputs + fd.writes} or rname[0] in fd.write_limbs() or \
            rname[0] in kernels or not ir.VALUE_NAME.match(rname[0]):
        err('radius: it gives one value of a name of its own, RZ = KERNEL(STATE LIMB, SCALAR, ...)')
    lead = (m.name,) + ((ex.name,) if ex is not None else ())
    if tuple(fd.radius[1][:len(lead)]) != lead or set(fd.radius[1][len(lead):]) - {g.name for g in fd.scalars} or \
            len(set(fd.radius[1])) < len(fd.radius[1]):
        err(f'radius: its arguments are the state\'s limb {m.name}, ' +
            (f'then its mask of exactness {ex.name}, ' if ex is not None else '') + 'then scalars, each once')
        return errs
    if [_shape(g) for g in radius.inputs] != [(1, ir.LIMB)] + [(1, ir.MASK)] * (ex is not None) + \
            [_shape(groups_of[a]) for a in fd.radius[1][len(lead):]] or \
            [_shape(g) for g in radius.outputs] != [(1, ir.LIMB)]:
        err(f'radius: {radius.name} takes one limb for each argument' + (' (a mask for the mask)' if ex else '') +
            ' and returns one')
    if not radius.real_model:
        err(f'radius: {radius.name} has no real-model statement, and the radius is in the real model', rule=DOMAIN)
    if ex is not None and (fd.ensures and fd.ensures[0]['kind'] == 'makes_ball_vector'):
        err('a constructor of a ball vector has no mask of exactness')
    used = set(args) | set(fd.radius[1])
    for g in fd.scalars:
        if g.name not in used:
            err(f'scalar {g.name}: neither the step nor the radius takes it', g.name)
    # The finish: the radius and the state's mask to the radius returned and the flag, finite_or_nan
    # under that mask with no step (norm_finish_1); for a constructor, which is given a radius that may
    # be negative, also the test of its sign (nonneg: bv_make_finish).
    make = bool(fd.ensures) and fd.ensures[0]['kind'] == 'makes_ball_vector'
    finish = kernels.get(fd.finish[0]) if fd.finish else None
    fin = [e for e in finish.ensures if e['kind'] == 'finite_or_nan'] if finish else []
    if finish is None or [_shape(g) for g in finish.inputs] != [(1, ir.LIMB), (1, ir.MASK)] or \
            [_shape(g) for g in finish.outputs] != [(1, ir.LIMB), (1, ir.MASK)] or len(fin) != 1 or \
            fin[0].get('if') != finish.inputs[1].name or fin[0].get('steps', 0) != 0 or \
            fin[0]['of'] != finish.outputs[0].name or fin[0]['flag'] != finish.outputs[1].name or \
            bool(fin[0].get('nonneg')) != make:
        err('finish: a kernel of the radius and a mask to the radius and a flag, finite_or_nan under the mask with no '
            'step (norm_finish_1); for a constructor (makes_ball_vector), and only there, with nonneg '
            '(bv_make_finish)')
    elif fd.finish[1] != (rname[0], ok.name):
        err(f'finish: (R, FLAG) = {finish.name}({rname[0]}, {ok.name}): the radius and the state\'s mask')
    if [_shape(g) for g in fd.outputs] != [(1, ir.LIMB), (1, ir.MASK)] or \
            (fd.finish and fd.finish[2] != tuple(g.name for g in fd.outputs)):
        err('outputs: the radius and the flag, the finish\'s destinations')
    if errs:
        return errs
    errs += _map_r3(fd, step, kernels)
    errs += _bv_radius_r3(fd, radius, kernels)
    errs += (_bv_make_claims if make else _bv_claims)(fd, kernels, step, radius, h)
    errs += _fold_theorem(fd)
    return errs


def _bv_make_claims(fd, kernels, step, radius, host):
    """The claims of a constructor of a BallVector (milestone2.md, "BallVector", "Values"): it reads one
    array, the centers given, and one scalar, the radius the program supplies; its value is the array's
    name, the step's value of what it passes; the centers are required canonical (two limbs) or any
    value (one limb); it claims makes_ball_vector of the centers written, the radius and the flag, from
    the array and the scalar."""
    errs = []

    def err(msg):
        errs.append(RuleError(fd.name, '-', CLAIMS, msg))

    if not fd.extended:
        err('a constructor of a ball vector is of the extended domain: it may return the whole space')
    if len(fd.arrays) != 1 or len(fd.scalars) != 1 or len(fd.scalars[0].limbs) != 1 or \
            fd.roles[fd.scalars[0].name] != 'supplied':
        err('a constructor reads one array, the centers given, and one scalar of one limb, the radius the program '
            'supplies')
        return errs
    c, r = fd.arrays[0], fd.scalars[0]
    written = fd.writes[0]
    if fd.value != c.name:
        err(f'value: the value of a center written is the center given, {c.name}')
    elif step.value is None or _renamed(expr.parse(step.value), {g.name: a for a, g in zip(fd.step[1], step.inputs)}) \
            != expr.parse(fd.value):
        err(f'value {fd.value!r}: not the value of the step {step.name} of what the fold passes it')
    want = [('canonical', c.name)] if len(c.limbs) > 1 else []
    if [tuple(x) for x in fd.requires] != want:
        err(f'requires: a constructor requires {"canonical " + c.name if want else "nothing"} of the centers given '
            '(any value of the format for one limb)')
    passed = dict(zip((g.name for g in step.inputs), fd.step[1]))
    for x in step.requires:
        if x[0] not in ('normalized', 'canonical') or passed.get(x[1]) != c.name or not want:
            err(f'the step {step.name} requires {" ".join(x)}, which no requirement of the fold gives')
    if radius.requires:
        err(f'the radius {radius.name} of a constructor requires nothing: it is given any value')
    if fd.radius[1] != (fd.states[0].name, r.name):
        err(f'radius: RZ = {radius.name}({fd.states[0].name}, {r.name}), the largest magnitude and the radius given')
    outs = [g.name for g in fd.outputs]
    want_e = {'kind': 'makes_ball_vector', 'center': written.name, 'radius': outs[0], 'flag': outs[1],
              'from': {'center': c.name, 'radius': r.name}}
    if fd.ensures != [want_e]:
        err(f'ensures: a constructor claims makes_ball_vector {written.name} {outs[0]} from={c.name},{r.name} '
            f'flag={outs[1]}, and nothing else')
    if fd.min_precision is None or fd.min_precision < 1:
        err('min_precision: an integer, at least 1')
    else:
        for k in (step, radius, kernels[host.step[0]], kernels[fd.finish[0]]):
            if (k.min_precision or 1) > fd.min_precision:
                err(f'min_precision {fd.min_precision}: the claims of {k.name} hold from precision {k.min_precision} on')
    return errs


def _bv_radius_r3(fd, radius, kernels):
    """Rule R3 on the scalars a ball vector passes to its radius: a supplied scalar enters from the
    program, so the radius takes it as a value of the program (an entry kernel) and adds none before
    guard."""
    errs = []
    by_arg = dict(zip(fd.radius[1], radius.inputs))
    program = set(radius.program_values())
    tainted = []
    for a in fd.radius[1][1:]:
        if fd.roles.get(a) == 'supplied':
            g = by_arg[a]
            if not set(g.limbs) <= program:
                errs.append(RuleError(fd.name, a, RULE_R3, f'{a} is supplied by the program, and the radius '
                                                           f'{radius.name} does not take {g.name} as a value of the '
                                                           'program (entry: yes, and the input not stored)'))
            tainted += list(g.limbs)
    hits, _, _ = r3_analysis(radius, kernels, frozenset(tainted))
    for where, origins in hits:
        errs.append(RuleError(fd.name, sorted(origins)[0], RULE_R3,
                              f'a limb the program supplies reaches {where} in the radius {radius.name} without '
                              'passing through guard'))
    return errs


def _renamed_all(tree, rename):
    """An expression tree with its names renamed, the groups of its limbs NAME[I] too."""
    if isinstance(tree, tuple):
        if tree and tree[0] == 'name':
            return ('name', rename.get(tree[1], tree[1]))
        if tree and tree[0] == 'limb':
            return ('limb', rename.get(tree[1], tree[1])) + tuple(tree[2:])
        return tuple(_renamed_all(t, rename) for t in tree)
    return tree


def _condition_key(c, rename):
    """A condition of exact_when as a comparable value: its kind, its expression renamed, its threshold."""
    kind = next(x for x in ir.EXACT_CONDITIONS if x in c)
    return kind, _renamed_all(expr.parse(c[kind]), rename), expr.parse(c['than'])


def _bv_exact(fd, kernels, step, radius, e, arrays, scalars):
    """The exactness of a ball vector under conditions (bv_mul_pow2_k; architecture.md, "Claims of
    Milestone 2", ball vectors): its exact_when lists conditions of an entry (EXPR names an array) and of
    the scalars (EXPR names scalars only), each EXPR = 0 or |EXPR| > K (>= K) over the arrays' names and
    limbs and the scalars' names. The fold has the state's mask of exactness (exact_mask); the conditions
    of an entry are those of the exact_when of the step's error entry whose exact_flag is the step's mask
    (renamed to what the fold passes), and those of the scalars are those of the exact_when of the radius
    kernel's upper entry that names its mask input as a condition, mask(EX), the others renamed. So the
    step's claim says that its mask is true exactly when an entry's conditions hold, and the radius
    kernel's that it is its value (c rx) when the mask and the scalars' conditions hold."""
    errs = []

    def err(msg):
        errs.append(RuleError(fd.name, '-', CLAIMS, msg))

    conds = e.get('exact_when')
    if not conds:
        if fd.exact_mask is not None:
            err('state: a mask of exactness is for a ball vector exact under conditions (exact_when=CONDITIONS)')
        return errs
    if fd.exact_mask is None:
        err('encloses_entries exact_when: conditions need the mask of exactness in the state (state: m, mask ok, '
            'mask EX) and from the step')
        return errs
    entry, scalar = [], []
    for c in conds:
        keys = set(c) - {'than'}
        if 'than' not in c or len(keys) != 1 or not keys <= set(ir.EXACT_CONDITIONS):
            err(f'encloses_entries exact_when {c!r}: a condition is zero_or_abs_gt(EXPR,K) or zero_or_abs_ge(EXPR,K)')
            continue
        try:
            tree, bound = expr.parse(c[next(iter(keys))]), expr.parse(c['than'])
        except expr.ExprError as x:
            err(f'encloses_entries exact_when: {x}')
            continue
        names = expr.names(tree)
        if names - set(arrays) - set(scalars) or not _only(tree, EXACT_TREES) or \
                any(g not in arrays or i >= len(arrays[g].limbs) for g, i in expr.limbs(tree)):
            err(f'encloses_entries exact_when {c!r}: an expression of the arrays\' names and limbs and the scalars\' '
                'names')
            continue
        if expr.names(bound) - {'u', 'eta'} or not _only(bound, THRESHOLD_TREES):
            err(f'encloses_entries exact_when {c!r}: the threshold is an exact expression over u, eta and integers')
            continue
        (entry if names & set(arrays) else scalar).append(c)
    if errs:
        return errs
    mask = step.outputs[1].name if len(step.outputs) == 2 else None
    flagged = [x for x in step.ensures if x['kind'] == 'error' and x.get('exact_flag') == mask and mask]
    srename = {g.name: a for g, a in zip(step.inputs, fd.step[1])}
    if len(flagged) != 1 or sorted((_condition_key(c, srename) for c in flagged[0].get('exact_when', [])), key=repr) != \
            sorted((_condition_key(c, {}) for c in entry), key=repr):
        err(f'encloses_entries exact_when: the conditions of an entry are those of the error entry of the step '
            f'{step.name} whose exact_flag is its mask {mask}, renamed to what the fold passes')
    rmask = radius.inputs[1].name if len(radius.inputs) > 1 and radius.inputs[1].kind == ir.MASK else None
    rrename = {g.name: a for g, a in zip(radius.inputs, fd.radius[1])}
    exacts = [x for x in radius.ensures if x['kind'] == 'upper' and {ir.MASK_CONDITION: rmask} in x.get('exact_when', [])]
    if len(exacts) != 1 or sorted((_condition_key(c, rrename) for c in exacts[0]['exact_when']
                                   if ir.MASK_CONDITION not in c), key=repr) != \
            sorted((_condition_key(c, {}) for c in scalar), key=repr):
        err(f'encloses_entries exact_when: the conditions of the scalars are those of the upper entry of the radius '
            f'{radius.name} whose exact_when holds mask({rmask}), the others renamed to what the fold passes')
    return errs


def _bv_claims(fd, kernels, step, radius, host):
    """A ball vector's claims (architecture.md, "Claims of Milestone 2", ball vectors): its value is the
    step's; each array is the centers of a BallVector with a scalar its radius (ball_vector ARRAY
    RADIUS), the other scalars any value of T; it claims encloses_entries of the centers written, the
    radius and the flag it returns, over its value, the ball names its BallVectors."""
    errs = []

    def err(msg):
        errs.append(RuleError(fd.name, '-', CLAIMS, msg))

    arrays = {g.name: g for g in fd.arrays}
    scalars = {g.name: g for g in fd.scalars}
    written = fd.writes[0]
    if not fd.extended:
        err('a ball vector is of the extended domain: its result may be the whole space')
    if not fd.value:
        err("no value: the exact value of one center written, over the arrays' and the scalars' names")
        return errs
    try:
        tree = expr.parse(fd.value)
    except expr.ExprError as e:
        err(f'value: {e}')
        return errs
    if expr.names(tree) - set(arrays) - set(scalars) or not _only(tree, VALUE_TREES):
        err(f"value {fd.value!r}: + - *, unary minus and abs( ) of the arrays' and the scalars' names")
    elif step.value is not None:
        rename = {g.name: a for a, g in zip(fd.step[1], step.inputs)}
        if _renamed(expr.parse(step.value), rename) != tree:
            err(f'value {fd.value!r}: not the value of the step {step.name}, {step.value}, of what the fold passes it')
    vectors, pow2 = {}, set()
    for r in fd.requires:
        if r[0] == 'ball_vector' and len(r) == 3 and r[1] in arrays and r[2] in scalars and \
                len(scalars[r[2]].limbs) == 1 and fd.roles[r[2]] == 'stored' and r[1] not in vectors and \
                r[2] not in vectors.values():
            vectors[r[1]] = r[2]
            continue
        if r[0] == 'power_of_two' and len(r) == 2 and r[1] in scalars and len(scalars[r[1]].limbs) == 1 and \
                fd.roles[r[1]] == 'supplied' and r[1] not in pow2:
            # A scalar the program supplies that is a positive power of two (bv_mul_pow2_k), as for a map.
            pow2.add(r[1])
            continue
        err(f'requires {" ".join(r)!r}: a ball vector requires "ball_vector ARRAY RADIUS", each array once with a '
            'stored scalar of one limb, its radius, and "power_of_two SCALAR" of a scalar of one limb the program '
            'supplies')
    if set(vectors) != set(arrays):
        err('requires: every array is the centers of a BallVector, ball_vector ARRAY RADIUS')
    radii = set(vectors.values())
    if pow2 & radii:
        err('requires: a radius is not a power of two')
    masks = {g.name for g in fd.states[2:]}
    for a in fd.radius[1][1:]:
        if a not in masks and a not in radii and fd.roles[a] != 'supplied':
            err(f'radius: {a} is neither the radius of an operand nor a scalar the program supplies')
    # The step's requirements are what a canonical BallVector gives: a normalized center (two limbs);
    # and the scalars' requirements (power_of_two).
    passed = dict(zip((g.name for g in step.inputs), fd.step[1]))
    for r in step.requires:
        # canonical: a step of the extended domain with a real-model statement (neg_2), where it is
        # normalized; a finite center of a canonical BallVector is either.
        if not ((r[0] in ('normalized', 'canonical') and passed.get(r[1]) in vectors) or
                (r[0] == 'power_of_two' and passed.get(r[1]) in pow2)):
            err(f'the step {step.name} requires {" ".join(r)}, which no requirement of the fold gives')
    rpassed = dict(zip((g.name for g in radius.inputs), fd.radius[1]))
    for r in radius.requires:
        if not ((r[0] == 'nonneg' and (r[1] == radius.inputs[0].name or rpassed.get(r[1]) in radii)) or
                (r[0] == 'power_of_two' and rpassed.get(r[1]) in pow2)):
            err(f'the radius {radius.name} requires {" ".join(r)}: of the largest magnitude and of the radii only '
                '(nonneg), and of a scalar the fold requires power_of_two')
    if len(fd.ensures) != 1 or fd.ensures[0]['kind'] != 'encloses_entries':
        err('ensures: a ball vector claims one encloses_entries, of the centers written, its radius and its flag')
        return errs
    e = fd.ensures[0]
    outs = [g.name for g in fd.outputs]
    if (e['center'], e['radius'], e['flag']) != (written.name, outs[0], outs[1]):
        err(f'encloses_entries: the center is {written.name}, the radius {outs[0]} and the flag {outs[1]}')
    if set(e['balls']) != set(vectors) or any((v['center'], v['radius']) != (b, vectors.get(b))
                                              for b, v in e['balls'].items()):
        err('encloses_entries: one ball name per array, the name of the array, with its radius (x=x,rx)')
    try:
        if expr.parse(e['set']) != tree:
            err(f'encloses_entries: the set {e["set"]!r} is the value of the fold, {fd.value}')
    except expr.ExprError as x:
        err(f'encloses_entries set: {x}')
    for c in e['finite_when']:
        try:
            ctree = expr.parse(c['abs_le'])
            if expr.names(ctree) - set(arrays) - set(scalars) or not _only(ctree, VALUE_TREES):
                err(f'finite_when {c["abs_le"]!r}: an expression of the arrays\' and the scalars\' names')
        except expr.ExprError as x:
            err(f'finite_when: {x}')
    # V4 is a statement of every length: with no entry, finite_when says nothing, and the radius,
    # computed from the radii alone, can overflow; radii_when is the radii's own condition, over the
    # scalars only, which finite_when at any entry implies (the tests check both, in exact arithmetic).
    if bool(e['finite_when']) != bool(e.get('radii_when')):
        err('encloses_entries: finite_when and radii_when come together (V4 for every length, the empty vector '
            'included, needs the condition on the radii alone)')
    for c in e.get('radii_when', []):
        try:
            ctree = expr.parse(c['abs_le'])
            if expr.names(ctree) - set(scalars) or not _only(ctree, VALUE_TREES):
                err(f'radii_when {c["abs_le"]!r}: an expression of the scalars\' names only')
        except expr.ExprError as x:
            err(f'radii_when: {x}')
    # exact_when: the result is exactly the set, entry by entry: always (the empty list, the word
    # exact: bv_neg_k), or under conditions (bv_mul_pow2_k), those of every entry and of the scalars,
    # which must be the conditions under which the step's mask is true and the radius is its value.
    errs += _bv_exact(fd, kernels, step, radius, e, arrays, scalars)
    if fd.min_precision is None or fd.min_precision < 1:
        err('min_precision: an integer, at least 1')
    else:
        for k in (step, radius, kernels[host.step[0]]):
            if (k.min_precision or 1) > fd.min_precision:
                err(f'min_precision {fd.min_precision}: the claims of {k.name} hold from precision {k.min_precision} on')
        parts = [step, kernels[host.step[0]], radius] + ([kernels[fd.finish[0]]] if fd.finish else [])
        errs += _finite_from(fd, e, kernels, parts)
    return errs


def _finite_from(fd, e, kernels, parts):
    """The precision from which V4 is claimed: finite_from when the claim says it, which is then above the
    fold's minimum precision and comes with finite_when; otherwise the minimum precision. V4 promises a
    finite result, so from that precision on every constant of the fold's kernels (PARTS, their callees
    included) must be a finite number of the smallest format the statement admits: that precision, with
    emax = prec + 1 (binary_float asks prec < emax), qmin = 2 - 2 prec, qmax = 1. A constant that
    overflows there (bv_add_radius_1's up((1+u)^3) at precision 1: 27/8 rounded up is 4 = 2^emax) makes
    the radius +infinity or a NaN whatever the operands: V1 to V3 still hold (the whole space), V4 not."""
    errs = []

    def err(msg):
        errs.append(RuleError(fd.name, '-', CLAIMS, msg))

    if 'finite_from' in e:
        if not e['finite_when']:
            err('finite_from: the precision from which V4 is claimed, which needs finite_when')
            return errs
        if fd.min_precision is not None and e['finite_from'] <= fd.min_precision:
            err(f'finite_from={e["finite_from"]}: above the minimum precision {fd.min_precision} (at or below it, '
                'leave it out)')
            return errs
    if not e['finite_when'] or fd.min_precision is None:
        return errs
    p = e.get('finite_from', fd.min_precision)
    names = set()
    for k in parts:
        for prim in ir.prims(k, kernels):
            names |= {a.name for a in prim.args if a.const}
    for c in sorted(names - {ir.ZERO, 'inf', 'nan'}):
        try:
            consts.value(c, kernels, p, 2 - 2 * p, 1)
        except consts.ConstError as x:
            err(f'V4 is claimed from precision {p}, but in the smallest format of that precision (emax {p + 1}) {x}: '
                'claim it from a precision where every constant of the fold is finite (finite_from=P)')
            break
    return errs


# --- Convolutions -----------------------------------------------------------------------------------
#
# A convolution (architecture.md, "Convolutions") writes the n_x + n_y - 1 coefficients of the product
# of two polynomials: coefficient j is the fold of its `coefficients:` (a dot product, accepted by
# fold_rules on its own) in the sequential order on the terms (x_i, y_(j-i)), i increasing, written as
# that fold's final state and tested by its finish, as the elements of a map are by its check.

CONV_ENSURES = ('coefficients', 'finite_or_nan')


def conv_rules(fd, kernels, reserved):
    """Every refusal of one convolution, after the names (fold_rules)."""
    errs = []

    def err(msg, rule=WELL_FORMED):
        errs.append(RuleError(fd.name, '-', rule, msg))

    cf = getattr(kernels, 'folds', {}).get(fd.coefficients)
    if cf is None or cf.is_map or cf.is_conv or cf.is_max or cf.finish is None or cf.combine is None:
        err(f'coefficients: {fd.coefficients} is not a fold of a sum with a finish (a dot product, dot_k)')
        return errs
    if 'sequential' not in cf.orders:
        err(f'coefficients: {cf.name} has no sequential order, in which each coefficient is computed')
    if len(fd.arrays) != 2 or [(g.name, g.limbs, g.kind, fd.roles[g.name]) for g in fd.arrays] != \
            [(g.name, g.limbs, g.kind, cf.roles[g.name]) for g in cf.arrays]:
        err(f'arrays: two, those of {cf.name}, with their names, limbs and roles (stored or supplied)')
    if fd.step is not None:
        err(f'a convolution has no step of its own: its coefficients are folds of {cf.name}, with its step')
    if fd.scalars:
        err('a convolution has no scalar')
    if len(fd.writes) != 1 or [_shape(g) for g in fd.writes] != [_shape(g) for g in cf.states]:
        err(f'writes: one array, of the shape of the state of {cf.name}: each coefficient is its final state')
    if fd.state.kind != ir.MASK:
        err('the state of a convolution is one mask (state: mask NAME), true at the start')
    if fd.combine != ('and', (fd.state.name, fd.state.name), (fd.state.name,)):
        err(f'combine: the masks are combined by and: {fd.state.name} = and({fd.state.name}, {fd.state.name})')
    if fd.orders != ('sequential',):
        err('orders: sequential: each coefficient is its fold in the sequential order of its terms, and there is '
            'no packed form (the coefficients of a register would have terms of different ranges)')
    if fd.check != cf.finish[0]:
        err(f'check: {cf.finish[0]}, the finish of {cf.name}, so that a coefficient is what that fold returns')
    if fd.finish is not None or fd.outputs:
        err('a convolution returns its mask and the array it writes: finish: none, and no output line')
    mine = {g.name for g in fd.arrays + fd.writes + fd.states} | {v for g in fd.arrays + fd.writes + fd.states
                                                                  for v in g.limbs}
    clash = sorted(mine & ({g.name for g in cf.states} | set(cf.state_limbs())))
    if clash:
        err(f'{", ".join(clash)}: a name of the state of {cf.name}, which the loop of each coefficient declares')
    if errs:
        return errs
    # The claims: those of the fold of the coefficients, of each coefficient.
    if fd.value != cf.value:
        err(f'value {fd.value!r}: that of a term of {cf.name}, {cf.value}', CLAIMS)
    if fd.requires != cf.requires:
        err(f'requires: those of {cf.name}, of each term: ' + ', '.join(' '.join(r) for r in cf.requires), CLAIMS)
    written = fd.writes[0].name
    want = [{'kind': 'coefficients', 'of': written}, {'kind': 'finite_or_nan', 'of': written, 'flag': fd.state.name}]
    if sorted(fd.ensures, key=lambda e: e['kind']) != want:
        err(f'ensures: coefficients {written} (each satisfies the claims of {cf.name} on its terms) and '
            f'finite_or_nan {written} flag={fd.state.name}', CLAIMS)
    if not fd.extended:
        err('a convolution is of the extended domain: a coefficient that is not finite gives the canonical NaN and a '
            'false flag', CLAIMS)
    if fd.min_precision is None or fd.min_precision < (cf.min_precision or 1):
        err(f'min_precision: at least that of {cf.name}, {cf.min_precision}', CLAIMS)
    # The statements of conv_terms are printed once, for every convolution: so is the file of their
    # theorems, which the convolutions that name one name alike.
    files = {g.name: g.terms_theorem for g in getattr(kernels, 'folds', {}).values() if g.is_conv and g.terms_theorem}
    if len(set(files.values())) > 1:
        err('terms_theorem: the convolutions that name one name the same file (the statements of conv_terms are '
            'shared): ' + ', '.join(f'{n} {f}' for n, f in sorted(files.items())), RULE_THEOREM)
    errs += _fold_theorem(fd)
    return errs


# --- The product of two BallVectors ------------------------------------------------------------------
#
# The product of two polynomials whose coefficients are BallVectors (architecture.md, "Ball vectors";
# milestone2.md, "The product of polynomials"): the convolution `centers` of the centers, its mask
# included; the maxima of the operands' centers, by two records, the steps of folds of maxima, one on
# each array read; the count min(n_x, n_y) as a number of T; the kernel of the bound of dot for that
# many terms, on the count; the radius kernel on the maxima, the radii, the count and the bound; and
# the finish on the radius, the convolution's mask and the bound's. When the finish's flag is false,
# every coefficient written is zero and the radius +infinity, the whole space.
BV_CONV_ENSURES = ('encloses_coefficients',)
# The name of the count in the conditions of V4 (finite_when, count_when): n = min(n_x, n_y), an integer.
COUNT_NAME = 'n'


def bv_conv_rules(fd, kernels, reserved):
    """Every refusal of one product of two BallVectors, after the names (fold_rules)."""
    errs = []

    def err(msg, rule=WELL_FORMED):
        errs.append(RuleError(fd.name, '-', rule, msg))

    folds = getattr(kernels, 'folds', {})
    conv = folds.get(fd.centers)
    if conv is None or not conv.is_conv:
        err(f'centers: {fd.centers} is not a convolution (a fold with coefficients:)')
        return errs
    cf = folds[conv.coefficients]
    if fd.step is not None or fd.coefficients is not None or fd.check is not None or fd.combine is not None:
        err(f'the product of two BallVectors has no step, coefficients, check or combination of its own: its centers '
            f'are those of {conv.name}')
    if fd.orders != ('sequential',):
        err(f'orders: sequential, the order of {conv.name}')
    if [(g.name, g.limbs) for g in fd.arrays] != [(g.name, g.limbs) for g in conv.arrays] or \
            any(fd.roles[g.name] != 'stored' for g in fd.arrays):
        err(f'arrays: those of {conv.name}, names and limbs, stored (the centers of BallVectors)')
        return errs
    if [(g.name, g.limbs) for g in fd.writes] != [(g.name, g.limbs) for g in conv.writes]:
        err(f'writes: the array {conv.name} writes')
    if [_shape(g) for g in fd.states] != [(1, ir.LIMB), (1, ir.MASK)] * 2:
        err('state: those of two folds of maxima, one of each array read (state: ma, mask oka, mb, mask okb)')
        return errs
    names = fd.state_names()
    host = []
    for i, (g, rec) in enumerate(zip(fd.arrays, fd.records)):
        want = (names[2 * i], names[2 * i + 1])
        hs = [h for h in folds.values() if h.is_max and h.step and h.step[0] == rec[0] and
              _shape(h.arrays[0]) == _shape(g)]
        if not hs or rec[1:] != (want + (g.name,), want):
            err(f'record: ({want[0]}, {want[1]}) = NORM_STEP({want[0]}, {want[1]}, {g.name}), the step of a fold of '
                f'maxima of an array of the shape of {g.name}, in the order of the arrays')
        else:
            host.append(hs[0])
    if len(fd.records) != 2:
        err('record: two lines, the maxima of the centers of each operand')
    elif fd.records[0][0] != fd.records[1][0]:
        # The models have one F_record, of both operands (rocq.bv_conv_model, ieee.bv_conv_model).
        err('record: the same step of a fold of maxima for both operands')
    if errs:
        return errs
    # The count, the bound, the radius, the finish: names of their own.
    taken = {g.name for g in fd.arrays + fd.scalars + list(fd.states) + fd.outputs + fd.writes} | \
        set(fd.write_limbs()) | {conv.state.name} | {g.name for g in cf.states} | set(cf.state_limbs())
    bound = kernels.get(fd.bound[0]) if fd.bound else None
    radius = kernels.get(fd.radius[0]) if fd.radius else None
    finish = kernels.get(fd.finish[0]) if fd.finish else None
    if not fd.count or bound is None or radius is None or finish is None:
        err('count:, bound:, radius: and finish: name a count, and kernels')
        return errs
    own = [fd.count] + list(fd.bound[2]) + list(fd.radius[2])
    if len(set(own)) < len(own) or set(own) & (taken | reserved | set(kernels)) or \
            not all(ir.VALUE_NAME.match(n) for n in own):
        err('count:, bound: and radius: give values of names of their own')
    # The bound of dot for the count: one limb in, g and t and a mask out, the claims of bound_dot_k
    # (holds and upper under its mask), covering the products of the fold of the coefficients (unit and tiny
    # of its kernel at least the term, or eps, and the tau of that fold's fold_error).
    if [_shape(g) for g in bound.inputs] != [(1, ir.LIMB)] or \
            [_shape(g) for g in bound.outputs] != [(1, ir.LIMB), (1, ir.LIMB), (1, ir.MASK)] or \
            fd.bound[1] != (fd.count,) or ('count', bound.inputs[0].name) not in bound.requires:
        err(f'bound: (G, T, OK) = {bound.name}({fd.count}): a kernel of the count, required count, to two limbs and '
            'a mask')
        return errs
    errs += _bv_conv_bound(fd, bound, cf, kernels)
    # The radius: the maxima, the radii, the count and the bound's limbs, each once, to one limb.
    allowed = {names[0], names[2], fd.count, fd.bound[2][0], fd.bound[2][1]} | {g.name for g in fd.scalars}
    if len(fd.radius[2]) != 1 or set(fd.radius[1]) - allowed or len(set(fd.radius[1])) < len(fd.radius[1]) or \
            [_shape(g) for g in radius.inputs] != [(1, ir.LIMB)] * len(fd.radius[1]) or \
            [_shape(g) for g in radius.outputs] != [(1, ir.LIMB)]:
        err(f'radius: RZ = {radius.name}(...) on the maxima, the radii, the count and the bound\'s two limbs, each '
            'once, to one limb')
    if not radius.real_model:
        err(f'radius: {radius.name} has no real-model statement, and the radius is in the real model', rule=DOMAIN)
    used = set(fd.radius[1])
    for g in fd.scalars:
        if g.name not in used or len(g.limbs) != 1 or fd.roles[g.name] != 'stored':
            err(f'scalar {g.name}: a radius, stored, of one limb, which the radius takes', g.name)
    # The finish: the radius, the convolution's mask and the bound's, to the radius returned and the flag,
    # finite_or_nan under the two masks (if_all), with no step.
    fin = [e for e in finish.ensures if e['kind'] == 'finite_or_nan']
    if [_shape(g) for g in finish.inputs] != [(1, ir.LIMB), (1, ir.MASK), (1, ir.MASK)] or \
            [_shape(g) for g in finish.outputs] != [(1, ir.LIMB), (1, ir.MASK)] or len(fin) != 1 or \
            fin[0].get('if_all') != [finish.inputs[1].name, finish.inputs[2].name] or \
            fd.finish[1] != (fd.radius[2][0], conv.state.name, fd.bound[2][2]) or \
            fd.finish[2] != tuple(g.name for g in fd.outputs) or \
            [_shape(g) for g in fd.outputs] != [(1, ir.LIMB), (1, ir.MASK)]:
        err(f'finish: (R, FLAG) = {finish.name}(RZ, {conv.state.name}, OK), the radius, the mask of {conv.name} and '
            'the bound\'s, claiming finite_or_nan under both (if_all); the outputs the radius and the flag')
    if errs:
        return errs
    errs += _bv_radius_r3(fd, radius, kernels)
    errs += _bv_conv_claims(fd, kernels, conv, [radius, finish, bound] + [kernels[h.step[0]] for h in host])
    if not errs and fd.ensures and fd.ensures[0].get('kind') == 'encloses_coefficients':
        # V4 from its precision: the constants of every part, the coefficients' step and check included.
        parts = [radius, finish, bound, kernels[cf.step[0]]] + [kernels[h.step[0]] for h in host] + \
            ([kernels[conv.check]] if conv.check in kernels else [])
        errs += _finite_from(fd, fd.ensures[0], kernels, parts)
    errs += _fold_theorem(fd)
    return errs


def _bv_conv_bound(fd, bound, cf, kernels):
    """The bound kernel covers the fold of the coefficients: unit(X) and tiny(X) of its upper entries are
    at least the constants of that fold's fold_error (term, or eps when term is 0, and tau), in binary64
    and binary32. Its g and t grow with both, so a bound of larger constants still bounds the error of
    every coefficient; equal constants are the bound of exactly that fold (bound_dot_k for dot_k)."""
    e = next((x for x in cf.ensures if x['kind'] == 'fold_error'), None)
    calls = set()
    for x in bound.ensures:
        for key in ('value',) if x['kind'] == 'upper' else ('args',) if x['kind'] == 'holds' else ():
            for text in ([x[key]] if key == 'value' else x[key]):
                calls |= {kname for _, kname in expr.calls(expr.parse(text))}
    if e is None or len(calls) != 1:
        return [RuleError(fd.name, '-', CLAIMS, f'bound: {bound.name} claims a bound of one kernel\'s products, and '
                                                f'the fold of the coefficients a fold_error')]
    x = calls.pop()
    unit = e['term'] if e['term'] != '0' else e['eps']
    for p, qmin in ((53, -1074), (24, -149)):
        try:
            ours = [consts.evaluate(expr.parse(f'{fn}({x})'), kernels, p, qmin) for fn in ('unit', 'tiny')]
            theirs = [consts.evaluate(expr.parse(t), kernels, p, qmin) for t in (unit, e['tau'])]
        except (expr.ExprError, consts.ConstError) as err:
            return [RuleError(fd.name, '-', CLAIMS, f'bound: {err}')]
        if any(o < t for o, t in zip(ours, theirs)):
            return [RuleError(fd.name, '-', CLAIMS, f'bound: {bound.name} bounds the products of {x}, whose unit and '
                                                    f'tiny are below the term and tau of the fold of the coefficients '
                                                    f'{cf.name}')]
    return []


def _bv_conv_claims(fd, kernels, conv, parts):
    """The claims of the product of two BallVectors (architecture.md, "Claims of Milestone 2"): its value
    and requirements those of the convolution, each array required ball_vector with its radius; one
    encloses_coefficients of the coefficients written, the radius and the flag, over that value, one ball
    name per array; finite_when over the arrays' names, the scalars' and the count n; radii_when over the
    scalars alone, present exactly when finite_when is; count_when over n and the constants of the
    format; the extended domain; the minimum precision."""
    errs = []

    def err(msg):
        errs.append(RuleError(fd.name, '-', CLAIMS, msg))

    arrays = {g.name: g for g in fd.arrays}
    scalars = {g.name: g for g in fd.scalars}
    if not fd.extended:
        err('the product of two BallVectors is of the extended domain: its result may be the whole space')
    if fd.value != conv.value:
        err(f'value {fd.value!r}: that of a term of {conv.name}, {conv.value}')
    vectors = {}
    for r in fd.requires:
        if r[0] == 'ball_vector' and len(r) == 3 and r[1] in arrays and r[2] in scalars and r[1] not in vectors and \
                r[2] not in vectors.values():
            vectors[r[1]] = r[2]
            continue
        err(f'requires {" ".join(r)!r}: the product requires "ball_vector ARRAY RADIUS", each array once')
    if set(vectors) != set(arrays):
        err('requires: every array is the centers of a BallVector, ball_vector ARRAY RADIUS')
    if len(fd.ensures) != 1 or fd.ensures[0]['kind'] != 'encloses_coefficients':
        err('ensures: one encloses_coefficients, of the coefficients written, its radius and its flag')
        return errs
    e = fd.ensures[0]
    outs = [g.name for g in fd.outputs]
    if (e['center'], e['radius'], e['flag']) != (fd.writes[0].name, outs[0], outs[1]):
        err(f'encloses_coefficients: the center is {fd.writes[0].name}, the radius {outs[0]} and the flag {outs[1]}')
    if set(e['balls']) != set(vectors) or any((v['center'], v['radius']) != (b, vectors.get(b))
                                              for b, v in e['balls'].items()):
        err('encloses_coefficients: one ball name per array, the name of the array, with its radius (x=x,rx)')
    try:
        if expr.parse(e['set']) != expr.parse(fd.value):
            err(f'encloses_coefficients: the set {e["set"]!r} is the value of the fold, {fd.value}')
    except expr.ExprError as x:
        err(f'encloses_coefficients set: {x}')
    for key, allowed in (('finite_when', set(arrays) | set(scalars) | {COUNT_NAME}), ('radii_when', set(scalars))):
        for c in e.get(key, []):
            try:
                ctree = expr.parse(c['abs_le'])
                if expr.names(ctree) - allowed or not _only(ctree, VALUE_TREES):
                    err(f'{key} {c["abs_le"]!r}: an expression of ' +
                        ("the arrays' names, the scalars' and the count n" if key == 'finite_when' else
                         "the scalars' names only"))
            except expr.ExprError as x:
                err(f'{key}: {x}')
    if bool(e['finite_when']) != bool(e.get('radii_when')):
        err('encloses_coefficients: finite_when and radii_when come together (V4 for every length, an empty operand '
            'included)')
    if bool(e['finite_when']) != bool(e.get('count_when')):
        err('encloses_coefficients: count_when comes with finite_when (V4 needs the bound of dot for n terms)')
    for c in e.get('count_when', []):
        try:
            tree = expr.parse(c['le'])
            if expr.names(tree) - {COUNT_NAME, 'u', 'eta'} or not _only(tree, CONSTANT_TREES) or \
                    any(kname not in kernels for _, kname in expr.calls(tree)):
                err(f'count_when {c["le"]!r}: an expression of the count n, u, eta, unit(K) and tiny(K)')
            bound = expr.parse(c['than'])
            if expr.names(bound) or not expr.evaluate(bound, {}) > 0:
                err(f'count_when than={c["than"]!r}: a positive rational')
        except (expr.ExprError, consts.ConstError) as x:
            err(f'count_when: {x}')
    if fd.min_precision is None or fd.min_precision < (conv.min_precision or 1) or \
            any((k.min_precision or 1) > fd.min_precision for k in parts):
        err(f'min_precision: at least that of {conv.name} and of every part')
    return errs


def _map_r3(fd, step, kernels):
    """Rule R3 on a map: the elements of a supplied array and the limbs of a supplied scalar enter
    from the program, so the step takes them as values of the program and adds none of them before
    guard (r3_analysis, as for a fold); nothing written is such a limb as it is."""
    errs = []
    _, args, _ = fd.step
    by_arg = dict(zip(args, step.inputs))
    program = set(step.program_values())
    tainted = []
    for a in args:
        g = by_arg[a]
        if fd.roles[a] == 'supplied':
            if not set(g.limbs) <= program:
                errs.append(RuleError(fd.name, a, RULE_R3,
                                      f'{a} is supplied by the program, and the step {step.name} does not take '
                                      f'{g.name} as a value of the program (entry: yes, and the input not '
                                      'stored, or supplied for more than one limb)'))
            tainted += list(g.limbs)
    hits, _, out = r3_analysis(step, kernels, frozenset(tainted))
    for where, origins in hits:
        errs.append(RuleError(fd.name, sorted(origins)[0], RULE_R3,
                              f'a limb the program supplies reaches {where} in the step {step.name} without '
                              'passing through guard'))
    for v in out:
        errs.append(RuleError(fd.name, v, RULE_R3, f'a limb the program supplies is written ({v}) as it is; it '
                                                   'passes through guard first'))
    return errs


def _map_claims(fd, kernels, step, check):
    """A map's claims (architecture.md, "Claims of Milestone 2", maps): its value is the step's, its
    requirements are of an element or a scalar, and it claims the step's claims entry by entry
    (entries) and what its check makes of an element that is not finite (finite_or_nan)."""
    errs = []

    def err(msg):
        errs.append(RuleError(fd.name, '-', CLAIMS, msg))

    groups = {g.name: g for g in fd.arrays + fd.scalars}
    written = fd.writes[0]
    if not fd.value:
        err("no value: the exact value of one written element, over the arrays' and the scalars' names")
    else:
        try:
            tree = expr.parse(fd.value)
            if expr.names(tree) - set(groups) or not _only(tree, VALUE_TREES):
                err(f"value {fd.value!r}: + - *, unary minus and abs( ) of the arrays' and the scalars' names")
            elif step.value is not None:
                # The step's value, its inputs renamed to the groups the map passes them.
                rename = {g.name: a for a, g in zip(fd.step[1], step.inputs)}
                if _renamed(expr.parse(step.value), rename) != tree:
                    err(f'value {fd.value!r}: not the value of the step {step.name}, {step.value}, of what the map '
                        'passes it')
        except expr.ExprError as e:
            err(f'value: {e}')
    if not fd.extended:
        err('a map is of the extended domain: an element that is not finite gives the canonical NaN and a false flag')
    scalars = {g.name for g in fd.scalars}
    for r in fd.requires:
        if len(r) != 2 or r[1] not in groups:
            err(f'requires {" ".join(r)!r}: a requirement of a map is about each element of one array, or a scalar')
            continue
        if r[0] == 'canonical' and len(groups[r[1]].limbs) >= 2:
            continue
        if r[0] == 'power_of_two' and len(groups[r[1]].limbs) == 1 and r[1] in scalars:
            continue
        err(f'requires {" ".join(r)!r}: canonical ARRAY or SCALAR of more than one limb, or power_of_two SCALAR '
            'of one limb')
    # The step's requirements are the map's, on what it passes: a normalized operand is a canonical
    # element or scalar (its finite case), a power of two is one; otherwise the step's claims could
    # not be had of every element.
    passed = dict(zip((g.name for g in step.inputs), fd.step[1]))
    have = {(r[0], r[1]) for r in fd.requires if len(r) == 2}
    for r in step.requires:
        if r[0] in ('normalized', 'power_of_two') and len(r) == 2 and r[1] in passed:
            want = ('canonical' if r[0] == 'normalized' else 'power_of_two', passed[r[1]])
            if want not in have:
                err(f'requires: the step {step.name} requires {" ".join(r)}, so the map requires '
                    f'{want[0]} {want[1]}')
    if sorted(e['kind'] for e in fd.ensures) != sorted(MAP_ENSURES):
        err('ensures: a map claims, of the array it writes, entries (the claims of its step, element by element) '
            'and finite_or_nan with its state as the flag')
    for e in fd.ensures:
        if e['kind'] in MAP_ENSURES and e['of'] != written.name:
            err(f'ensures {e["kind"]} of {e["of"]!r}: of the array the map writes, {written.name}')
        if e['kind'] == 'finite_or_nan' and e['flag'] != fd.state.name:
            err(f'finite_or_nan flag={e["flag"]}: the flag of a map is its state, {fd.state.name}')
    if fd.min_precision is None or fd.min_precision < 1:
        err('min_precision: an integer, at least 1')
    else:
        for k in (step, check):
            if (k.min_precision or 1) > fd.min_precision:
                err(f'min_precision {fd.min_precision}: the claims of {k.name} hold from precision {k.min_precision} on')
    return errs


def _renamed(tree, rename):
    """An expression tree with its names renamed."""
    if isinstance(tree, tuple):
        if tree and tree[0] == 'name':
            return ('name', rename.get(tree[1], tree[1]))
        return tuple(_renamed(t, rename) for t in tree)
    return tree


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
        if a in fd.state_names():
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


# --- Folds of maxima ------------------------------------------------------------------------------
#
# A fold of maxima (norm_upper_k; architecture.md, "Folds of maxima") has a state of a limb, which
# starts at +0, and a mask, which starts true; its combination is a maximum of the limbs and an and
# of the masks, and its step is that combination applied to the state and to a function of the
# element (its magnitude, and the mask that it is not a NaN). The combination is then associative,
# commutative and idempotent on every state, and the result of the fold does not depend on the order
# (fold_lanes_aci, the lemma that proofs/theories/Folds.v needs): no ZERO_LEMMAS entry, which is
# about additions. What the generator checks of it is in max_rules.
MAX_FORMATS = ((2, -3, 3), (3, -2, 2))


def _defining(k, kernels, value):
    """The operation of k's flattened listing that defines `value`, or None."""
    for it in ir.flatten(k, kernels):
        if isinstance(it, ir.Prim) and it.dst == value:
            return it
    return None


def max_rules(fd, step, combine, finish, kernels):
    """A fold of maxima:
    1. its combination claims the maximum of its two limb operands (maximum r m n), and its mask is
       the and of the two masks (the operation that defines it in the listing);
    2. its step is a call of the combination on the state and on values computed from the element,
       whose limbs are the step's outputs (on the listing with its calls inlined), and it claims the
       maximum of the state and of the magnitude of the element's leading limb;
    3. the zero state, +0 and true, is the combination of two zero states, limb for limb, in
       ZERO_FORMATS (what fold_lanes_short needs: the lanes of a list shorter than the lanes are
       zero states); and on the magnitudes of the small formats MAX_FORMATS and both values of each
       mask, the combination is commutative and associative, and idempotent: by evaluation, the
       hypotheses of the order lemma, which the proof has from the claim in every format;
    4. its finish claims finite_or_nan with if= the state's mask (the claim's steps are checked
       against the fold's upper entry in _fold_claims)."""
    errs = []

    def err(msg):
        errs.append(RuleError(fd.name, '-', FOLD, msg))

    if len(fd.arrays) != 1:
        err('a fold of maxima reads one array')
        return errs
    x = fd.arrays[0]
    cm, cok, cn, cokn = combine.input_limbs
    claims = [e for e in combine.ensures if e['kind'] == 'maximum']
    if len(claims) != 1 or claims[0]['of'] != combine.output_limbs[0] or sorted(claims[0]['args']) != sorted([cm, cn]):
        err(f'the combination {combine.name} of a fold of maxima claims the maximum of its two limb operands: '
            f'maximum {combine.output_limbs[0]} {cm} {cn}')
    d = _defining(combine, kernels, combine.output_limbs[1])
    if d is None or d.op != 'and' or sorted(a.name for a in d.args if not a.const) != sorted([cok, cokn]):
        err(f'the combination {combine.name} of a fold of maxima returns the and of its two masks, '
            f'{combine.output_limbs[1]} = and({cok}, {cokn})')
    sm, sok = step.input_limbs[0], step.input_limbs[1]
    by_arg = dict(zip(fd.step[1], step.inputs))
    xg = by_arg[x.name]
    lead = f'abs({xg.name})' if len(xg.limbs) == 1 else f'abs({xg.name}[0])'
    claims = [e for e in step.ensures if e['kind'] == 'maximum']
    if fd.step[1][:2] != fd.state_names() or len(claims) != 1 or claims[0]['of'] != step.output_limbs[0] or \
            sorted(claims[0]['args']) != sorted([sm, lead]):
        err(f'the step {step.name} of a fold of maxima takes the state first and claims the maximum of the state '
            f'and of the magnitude of the leading limb of the element: maximum {step.output_limbs[0]} {sm} {lead}')
    calls = [it for it in ir.flatten(step, kernels) if isinstance(it, ir.CallMark) and it.callee == combine.name]
    if not any(it.dsts == tuple(step.output_limbs) and [a.name for a in it.args[:2]] == [sm, sok] for it in calls):
        err(f'the step {step.name} of a fold of maxima is a call of its combination {combine.name} on the state and '
            'on values of the element, which returns the next state')
    fin = [e for e in finish.ensures if e['kind'] == 'finite_or_nan'] if finish else []
    if not fin or fin[0].get('if') != finish.input_limbs[1]:
        err(f'the finish of a fold of maxima claims finite_or_nan with if= its mask, {finish.input_limbs[1] if finish else "?"}')
    if errs:
        return errs
    key = ('max', combine.name, id(kernels))
    if key not in _ZERO_CACHE:
        _ZERO_CACHE[key] = _max_evaluation(combine, kernels)
    return [RuleError(fd.name, '-', FOLD, msg) for msg in _ZERO_CACHE[key]]


def _max_evaluation(combine, kernels):
    """The zero state and the laws of the combination of a fold of maxima, by evaluation (max_rules, 3)."""
    from . import interp
    found = []
    m = interp.Machine(kernels)
    zero = [(interp.NUM, False, 0, 0), True]
    for p, qmin, qmax in ZERO_FORMATS:
        f = interp.Format(f'fp:{p}:{qmin}:{qmax}', p, qmin, qmax)
        zz = m.run(combine.name, f, zero + zero)
        if zz[1] is not True or zz[0][0] != interp.NUM or zz[0][2] != 0 or zz[0][1]:
            found.append(f'{combine.name}(0, 0) is not the zero state (+0, true) in {f.name}')
    for p, qmin, qmax in MAX_FORMATS:
        f = interp.Format(f'fp:{p}:{qmin}:{qmax}', p, qmin, qmax)
        mags = [(interp.NUM, False, 0, 0)] + sorted({interp.canon(False, mm, q) for q in range(qmin, qmax + 1)
                                                     for mm in range(1, 2 ** p)}, key=str)
        states = [[a, ok] for a in mags for ok in (False, True)]

        table = {(i, j): m.run(combine.name, f, s + t) for i, s in enumerate(states) for j, t in enumerate(states)}
        index = {(v[0], v[1]): i for i, v in enumerate(states)}

        def comb(i, j):
            v = table[(i, j)]
            return index.get((v[0], v[1]))
        n = len(states)
        if any(comb(i, j) is None for i in range(n) for j in range(n)):
            found.append(f'{combine.name} of two states of magnitudes is not one in {f.name}')
            continue
        if any(comb(i, i) != i for i in range(n)):
            found.append(f'{combine.name} is not idempotent in {f.name}')
        if any(comb(i, j) != comb(j, i) for i in range(n) for j in range(n)):
            found.append(f'{combine.name} is not commutative in {f.name}')
        if any(comb(comb(i, j), k) != comb(i, comb(j, k)) for i in range(n) for j in range(n) for k in range(n)):
            found.append(f'{combine.name} is not associative in {f.name}')
    return found


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
    allowed = MAX_ENSURES if fd.is_max else FOLD_ENSURES
    if fd.is_max:
        if len(fd.arrays) != 1 or fd.value != f'abs({fd.arrays[0].name})':
            err(f'value {fd.value!r}: a fold of maxima reads one array, and the value of an element is its magnitude, '
                'abs(ARRAY)')
        fin = [x for x in finish.ensures if x['kind'] == 'finite_or_nan'] if finish else []
        for e in fd.ensures:
            if e['kind'] == 'upper' and fin and e['steps'] != fin[0].get('steps', 0):
                err(f'upper steps={e["steps"]}: the result is the maximum stepped up as many times as the finish '
                    f'{finish.name} steps it ({fin[0].get("steps", 0)})')
    elif 'fold_error' not in [e['kind'] for e in fd.ensures]:
        err('a fold claims its bound: an ensures entry fold_error')
    if fd.min_precision is None or fd.min_precision < 1:
        err('min_precision: an integer, at least 1')
        return errs
    for k in (step, combine, finish if fd.is_max else None):
        if k is not None and (k.min_precision or 1) > fd.min_precision:
            err(f'min_precision {fd.min_precision}: the claims of {k.name} hold from precision {k.min_precision} on')
    for e in fd.ensures:
        kind = e['kind']
        if kind not in allowed or (kind == 'upper' and e.get('over') != 'max'):
            err(f'ensures {kind}: a fold claims {", ".join(allowed)}')
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
    if fd.ieee_theorem and not (fd.ieee_theorem.startswith('proofs/theories/') and fd.ieee_theorem.endswith('.v')):
        err(f'the ieee_theorem file must be proofs/theories/*.v, not {fd.ieee_theorem}')
    if fd.terms_theorem and not fd.is_conv:
        err('a terms_theorem names the theorems of the statements of conv_terms, which only a convolution names')
    if fd.terms_theorem and not (fd.terms_theorem.startswith('proofs/theories/') and fd.terms_theorem.endswith('.v')):
        err(f'the terms_theorem file must be proofs/theories/*.v, not {fd.terms_theorem}')
    return errs
