"""The Rocq printer of the round-up interval: proofs/gen/UpwardModel.v, UpwardStatements.v and
UpwardAudit.v (docs/developer/design/upward.md, "Statements").

The kernels of the upward family (`rounding: upward`, ir.KernelSet.upward) have generated files of
their own, so that every file of the other kernels stays what it was. UpwardModel.v defines each
kernel over Flocq's binary_float prec emax, with add_ru and mul_ru of
proofs/theories/IeeeUpwardOperations.v (Bplus and Bmult with mode_UP), its unord, and the exact
operations of IeeeOperations.v (neg, abs, the comparisons, the constants), in a section whose
variables are the NaN functions of those operations and max_nl, the greatest of two values in which
a NaN first operand loses. max_nl is a variable, not a definition: the statements quantify over
every max_nl with the property max_nl_ok (IeeeUpwardOperations.v), which x86's MAXPD and arm64's
FMAXNM both have, so that one listing and one statement cover both machine forms ("The maximum").
Closing the section abstracts each definition over the variables it uses, in the section's order:
nan_plus, nan_mult, nan_opp, nan_abs, nan_const, max_nl. A pair line is printed as its two
statements, lane 0 first; a call stays a call.

UpwardStatements.v has one statement K_spec per kernel, from its claims, in the vocabulary of
IeeeUpwardVocabulary.v (upward_1, upward_empty_1, upward_nonempty_1, in_upward_1, upward_bounded_1,
in_number_1) and of IeeeVocabulary.v and IeeeIntervalVocabulary.v; UpwardAudit.v checks the theorem
of each kernel whose ieee_status is proved against its statement and prints its assumptions. Like
the other Rocq printers, this one is trusted.
"""
from . import expr, ir, rocq

THEORIES_PATH = 'Kairn'
GEN_PATH = 'Kairn.Gen'
HEADER = rocq.HEADER

# The mark every file of the feature carries in its first paragraph (docs/developer/design/upward.md,
# "The marks"): the kernel descriptions here, and the generated header that the C++ printers write.
MARK = ('Requires the rounding mode upward set by kairn::upward::Scope and the options of '
        'docs/concepts/upward.md (GCC and Clang -frounding-math, MSVC /fp:strict).')

# The variables of the section of UpwardModel.v, in order, and their types in the statements; max_nl
# comes last, and its property max_nl_ok after it, in the statements.
NANS = (('nan_plus', 'nan2'), ('nan_mult', 'nan2'), ('nan_opp', 'nan1'), ('nan_abs', 'nan1'),
        ('nan_const', None))
MAX_NL = 'max_nl'
CONST_NAN_TYPE = '{x : binary_float prec emax | is_nan prec emax x = true}'
MAX_NL_TYPE = 'binary_float prec emax -> binary_float prec emax -> binary_float prec emax'
# The variables each operation takes.
OP_VARIABLES = {'add_ru': ('nan_plus',), 'mul_ru': ('nan_mult',), 'neg': ('nan_opp',), 'abs': ('nan_abs',),
                'max_nl': (MAX_NL,)}
# Each operation as a term of the model, over the section's local notations.
SPELL = {
    'add_ru': 'add_ru {0} {1}', 'mul_ru': 'mul_ru {0} {1}', 'unord': 'unord {0} {1}', 'max_nl': 'max_nl {0} {1}',
    'neg': 'neg {0}', 'abs': 'abs {0}', 'lt': 'lt {0} {1}', 'le': 'le {0} {1}', 'eq': 'eq {0} {1}',
    'and': 'andb {0} {1}', 'or': 'orb {0} {1}', 'not': 'negb {0}', 'select': 'if {0} then {1} else {2}',
    'copy': '{0}',
}
# Names the model and the statements give a meaning to: no value of an upward kernel may have one
# (rules.py checks it with the names of the other printers). The binders of the statements are
# checked for each statement (_bound).
RESERVED = frozenset({'pzero', 'pinf', 'cnan', 'neg', 'abs', 'lt', 'le', 'eq', 'unord', 'float',
                      'xval', 'xopp', 'xreal', 'nan', 'finite', 'val', 'omega', 'infinity'})


class PrintError(Exception):
    pass


def _kernels(kernels):
    """The kernels of the family: the set's `upward` (a plain dict of them is taken as it is)."""
    return getattr(kernels, 'upward', kernels)


def _variables(k, family):
    """The variables of the section that the closed definition of k takes, in section order."""
    used = set()
    for p in ir.prims(k, family):
        if p.op not in SPELL:
            raise PrintError(f'kernel {k.name}: the model of the round-up interval has no {p.op}')
        used.update(OP_VARIABLES.get(p.op, ()))
        for a in p.args:
            if a.const and a.name == 'nan':
                used.add('nan_const')
    return [n for n, _ in NANS if n in used] + ([MAX_NL] if MAX_NL in used else [])


def _binders(names):
    """(nan_plus nan_mult : nan2 prec emax) (nan_opp : nan1 prec emax) ... (max_nl : ...)
    (max_nl_ok_ : max_nl_ok prec emax max_nl): consecutive variables of one type share a binder."""
    types = dict(NANS)
    out = []
    for n in names:
        if n == MAX_NL:
            out.append(([n], MAX_NL_TYPE))
            continue
        t = f'{types[n]} prec emax' if types[n] else CONST_NAN_TYPE
        if out and out[-1][1] == t:
            out[-1][0].append(n)
        else:
            out.append(([n], t))
    text = ' '.join(f'({" ".join(ns)} : {t})' for ns, t in out if ns != [MAX_NL])
    if MAX_NL in names:
        text += (f'\n         ({MAX_NL} : {MAX_NL_TYPE}) ({MAX_NL}_ok_ : max_nl_ok prec emax {MAX_NL})')
    return text.strip()


# ---------------------------------------------------------------------------------------------
# UpwardModel.v

def _operand(a):
    if not a.const:
        return a.name
    if a.name == ir.ZERO:
        return 'pzero'
    if a.name == 'inf':
        return 'pinf'
    if a.name == 'nan':
        return 'cnan'
    raise PrintError(f'const {a.name} is no constant of the round-up interval')


def _type(kind):
    return 'bool' if kind == ir.MASK else 'float'


def _params(names, kinds):
    out = []
    for v, kind in zip(names, kinds):
        if out and out[-1][1] == kind:
            out[-1][0].append(v)
        else:
            out.append(([v], kind))
    return ''.join(f' ({" ".join(vs)} : {_type(kind)})' for vs, kind in out)


def definition(k):
    """One kernel as a Rocq definition: each statement a let, a pair line its two statements."""
    lines = [f'(* {k.name}: {k.source or "no source given"}. *)',
             f'Definition {k.name}{_params(k.input_limbs, k.input_kinds)} : '
             f'{" * ".join(map(_type, k.output_kinds))} :=']
    for st in k.body:
        args = [_operand(a) for a in st.args]
        if st.is_call:
            pattern = st.dsts[0] if len(st.dsts) == 1 else "'(" + ', '.join(st.dsts) + ')'
            lines.append(f'  let {pattern} := {" ".join([st.op] + args)} in')
        else:
            if st.op not in SPELL:
                raise PrintError(f'kernel {k.name}: the model of the round-up interval has no {st.op}')
            lines.append(f'  let {st.dsts[0]} := {SPELL[st.op].format(*args)} in')
    outs = k.output_limbs
    lines.append(f'  {outs[0]}.' if len(outs) == 1 else f'  ({", ".join(outs)}).')
    return lines


def model(kernels):
    family = _kernels(kernels)
    lines = [HEADER, '',
             '(* The IEEE model of the kernels of the round-up interval (docs/developer/design/upward.md,',
             '   "Statements"): one function per kernel over Flocq\'s binary_float prec emax, with add_ru and',
             '   mul_ru of IeeeUpwardOperations.v (Bplus and Bmult rounded toward +infinity), its unord, and',
             '   the exact operations of IeeeOperations.v, in a section whose variables are the NaN functions',
             '   of those operations and max_nl, the greatest of two values in which a NaN first operand',
             '   loses: a variable, since the statements are about every max_nl with the property',
             '   max_nl_ok, which both machine forms have. Closing the section abstracts each definition',
             '   over the variables it uses. A pair line is its two statements, lane 0 first; a call stays',
             '   a call; the names of the values are those of the kernel descriptions. *)',
             'From Stdlib Require Import Reals ZArith.',
             'From Flocq Require Import Core Binary.',
             f'From {THEORIES_PATH} Require IeeeOperations IeeeUpwardOperations.',
             '',
             'Section UpwardKernels.',
             'Variable prec emax : Z.',
             'Context {prec_gt_0_ : Prec_gt_0 prec}.',
             'Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.',
             '',
             'Notation float := (binary_float prec emax).',
             'Notation nan_of := {x : float | is_nan prec emax x = true}.',
             '',
             'Variable nan_plus : float -> float -> nan_of.',
             'Variable nan_mult : float -> float -> nan_of.',
             'Variable nan_opp : float -> nan_of.',
             'Variable nan_abs : float -> nan_of.',
             'Variable nan_const : nan_of.',
             f'Variable {MAX_NL} : float -> float -> float.',
             '',
             '(* The operations, applied to the variables of this section. *)',
             'Local Notation pzero := (IeeeOperations.pzero prec emax).',
             'Local Notation pinf := (IeeeOperations.pinf prec emax).',
             'Local Notation cnan := (IeeeOperations.cnan prec emax nan_const).',
             'Local Notation neg := (IeeeOperations.neg prec emax nan_opp).',
             'Local Notation abs := (IeeeOperations.abs prec emax nan_abs).',
             'Local Notation lt := (IeeeOperations.lt prec emax).',
             'Local Notation le := (IeeeOperations.le prec emax).',
             'Local Notation eq := (IeeeOperations.eq prec emax).',
             'Local Notation add_ru := (IeeeUpwardOperations.add_ru prec emax nan_plus).',
             'Local Notation mul_ru := (IeeeUpwardOperations.mul_ru prec emax nan_mult).',
             'Local Notation unord := (IeeeUpwardOperations.unord prec emax).']
    for k in family.values():
        lines += [''] + definition(k)
    lines += ['', 'End UpwardKernels.']
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------------------------------------
# UpwardStatements.v

def _comment(k):
    return f'{k.name}: {k.source or "no source given"}. IEEE-model status: {k.ieee_status or "unverified"}.'


def _statement(k, lines):
    return [f'(* {_comment(k)} *)', f'Definition {k.name}_spec : Prop :='] + lines


def _head(k, family):
    """The binders of every statement: the format and its instances, the variables of the kernel's
    definition (and max_nl_ok of max_nl), the precision when its minimum is above 1, the inputs."""
    names = _variables(k, family)
    lines = ['  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)',
             '         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)' +
             (f'\n         {_binders(names)},' if names else ',')]
    if (k.min_precision or 1) > 1:
        lines.append(f'  ({k.min_precision} <= prec)%Z ->')
    limbs = [v for v, kind in zip(k.input_limbs, k.input_kinds) if kind == ir.LIMB]
    masks = [v for v, kind in zip(k.input_limbs, k.input_kinds) if kind == ir.MASK]
    lines.append(f'  forall {" ".join(limbs)} : binary_float prec emax,')
    if masks:
        lines.append(f'  forall {" ".join(masks)} : bool,')
    return lines


def _hypotheses(k):
    lines = []
    for r in k.requires:
        if r[0] == ir.UPWARD:
            lines.append(f'  upward_1 {r[1]} {r[2]} ->')
        elif r[0] == 'interval':
            lines.append(f'  interval_1 {r[1]} {r[2]} ->')
        else:
            raise PrintError(f'kernel {k.name}: no reading of the requirement {r[0]} in the round-up interval')
    return lines


def _let(k, family):
    outs = k.output_limbs
    pattern = outs[0] if len(outs) == 1 else "'(" + ', '.join(outs) + ')'
    call = ' '.join([f'UpwardModel.{k.name} prec emax'] + _variables(k, family) + k.input_limbs)
    return f'  let {pattern} := {call} in'


def _bound(k, names):
    """The names a statement binds must be no input or output of the kernel."""
    taken = set(k.input_limbs) | set(k.output_limbs)
    if taken & set(names):
        raise PrintError(f'kernel {k.name}: {", ".join(sorted(taken & set(names)))} is bound in its statement, '
                         'and is a name of an input or an output')


class _Set:
    """A set of the claims, in the vocabulary of the statements: a stored pair {upper, nlower} of
    the round-up interval, or the bounds {lower, upper} of a default interval of one limb."""

    def __init__(self, names):
        self.stored = 'nlower' in names
        self.limbs = (names['upper'], names['nlower']) if self.stored else (names['lower'], names['upper'])

    @property
    def args(self):
        return ' '.join(self.limbs)

    def canonical(self):
        return f'{"upward" if self.stored else "interval"}_1 {self.args}'

    def empty(self):
        return f'{"upward" if self.stored else "interval"}_empty_1 {self.args}'

    def nonempty(self):
        return f'{"upward" if self.stored else "interval"}_nonempty_1 {self.args}'

    def bounded(self):
        return f'{"upward" if self.stored else "interval"}_bounded_1 {self.args}'

    def member(self, z=None):
        text = f'in_{"upward" if self.stored else "interval"}_1 {self.args}'
        return f'{text} {z}' if z else text

    def lower(self):
        return f'xopp (xval {self.limbs[1]})' if self.stored else f'xval {self.limbs[0]}'

    def upper(self):
        return f'xval {self.limbs[0]}' if self.stored else f'xval {self.limbs[1]}'


def _strip(term):
    """A term without its outer parentheses, when they enclose all of it (ieee._strip)."""
    if term.startswith('(') and term.endswith(')'):
        depth = 0
        for i, ch in enumerate(term):
            depth += {'(': 1, ')': -1}.get(ch, 0)
            if depth == 0 and i < len(term) - 1:
                return term
        return term[1:-1]
    return term


def _output(e):
    """The set of an entry's result: an output pair {upper, nlower}."""
    return _Set({'upper': e['upper'], 'nlower': e['nlower']})


def _interval_spec(k, family, e):
    """encloses_interval: I1 to I5 of the design page, "The statements", over stored pairs and
    numbers: canonical; empty exactly when an operand is; every result of members a member; for
    nonempty operands the lower bound -zn the rounding down of the lower bound of the exact range and
    zu the rounding up of its upper bound (exactly the bounds, for tight=exact); for bounded operands
    (and finite numbers) bounded exactly when the range is within Omega."""
    z = _output(e)
    sets = {x: _Set(b) for x, b in e['intervals'].items()}
    numbers = list(e.get('numbers', []))
    tree = expr.parse(e['set'])
    used = [n for n in list(sets) + numbers if n in expr.names(tree)]
    if len(used) not in (1, 2):
        raise PrintError(f'kernel {k.name}: a set over {len(used)} names has no range_N in the vocabulary')
    real = {n: (f"{n}'" if n in numbers else n) for n in used}
    _bound(k, list(real.values()) + ['lo', 'hi', 'z'])

    def member(n):
        return sets[n].member() if n in sets else f'in_number_1 {n}'
    body = rocq._term(tree, lambda n: real[n])
    inner = _strip(body)
    S = f'(range_{len(used)} (fun {" ".join(real[n] for n in used)} : R => {inner}) ' + \
        ' '.join(f'({member(n)})' for n in used) + ')'
    lines = _head(k, family) + _hypotheses(k) + [_let(k, family)]
    empties = ' \\/ '.join(sets[x].empty() for x in sets)
    claims = [z.canonical(), f'({z.empty()} <-> {empties})',
              f'(forall {" ".join(real[n] for n in used)} : R, ' +
              ' '.join(f'{member(n)} {real[n]} ->' for n in used) + f'\n   {z.member()} {body})']
    nonempty = ' '.join(f'{sets[x].nonempty()} ->' for x in sets)
    tight = e['tight']
    if tight['kind'] == 'exact':
        bounds = f'{z.lower()} = lo /\\ {z.upper()} = hi'
    elif tight['kind'] == 'rounded' and set(tight) == {'kind'}:
        bounds = f'{z.lower()} = xrd prec emax lo /\\ {z.upper()} = xru prec emax hi'
    else:
        raise PrintError(f'kernel {k.name}: the tightness of the round-up interval is exact or rounded')
    claims.append(f'({nonempty}\n   forall lo hi : xreal,\n   range_lower {S} lo ->\n   range_upper {S} hi ->\n'
                  f'   {bounds})')
    if e['bounded_when']:
        if not e.get('bounded_exactly') or len(e['bounded_when']) != 1 or not e['bounded_when'][0].get('omega'):
            raise PrintError(f'kernel {k.name}: the round-up interval claims I5 as bounded_when=abs_le(SET,omega) '
                             'bounded_exactly')
        bounded = ' '.join([f'{sets[x].bounded()} ->' for x in sets] + [f'finite {n} ->' for n in numbers])
        claims.append(f'({bounded}\n   ({z.bounded()} <->\n    forall z : R,\n    {S[1:-1]} z ->\n'
                      f'    Rabs z <= omega prec emax))')
    lines.append('  ' + ' /\\\n  '.join(claims) + '.')
    return _statement(k, lines)


def _interval_set_spec(k, family, e):
    """interval_set: the hull (union) or the intersection, exact, as interval_hull_1_spec and
    interval_intersection_1_spec over stored pairs."""
    z = _output(e)
    sets = [_Set(b) for b in e['intervals'].values()]
    _bound(k, ['lo', 'hi', 'z'])
    union = e['set'] == 'union'
    ins = [s.member('z') for s in sets]
    S = '(fun z : R => ' + (' \\/ ' if union else ' /\\ ').join(ins) + ')'
    both = ' /\\ '.join(ins)
    empty = (' /\\ '.join(s.empty() for s in sets) if union else f'~ (exists z : R, {both})')
    lines = _head(k, family) + _hypotheses(k) + [_let(k, family)]
    claims = [z.canonical(), f'({z.empty()} <-> {empty})',
              f'(forall z : R, {S[len("(fun z : R => "):-1]} -> {z.member("z")})',
              f'(~ {z.empty()} ->\n   forall lo hi : xreal,\n   range_lower {S} lo ->\n   range_upper {S} hi ->\n'
              f'   {z.lower()} = lo /\\ {z.upper()} = hi)']
    lines.append('  ' + ' /\\\n  '.join(claims) + '.')
    return _statement(k, lines)


def _makes_interval_spec(k, family, e):
    """makes_interval: the constructor, as interval_make_1_spec: canonical; the interval of the two
    values when they describe a nonempty one; the whole line (+inf, +inf) for a NaN and for the same
    infinity twice; the empty set for reversed bounds."""
    z = _output(e)
    lo, hi = e['from']['lower'], e['from']['upper']
    _bound(k, ['s'])
    u, n = z.limbs
    lines = _head(k, family) + _hypotheses(k) + [_let(k, family)]
    claims = [z.canonical(),
              f'(xnonempty (xval {lo}) (xval {hi}) -> {z.lower()} = xval {lo} /\\ {z.upper()} = xval {hi})',
              f'(nan {lo} \\/ nan {hi} \\/ (exists s : bool, xval {lo} = XInf s /\\ xval {hi} = XInf s) ->\n'
              f'   {u} = infinity prec emax false /\\ {n} = infinity prec emax false)',
              f'(xlt (xval {hi}) (xval {lo}) = true -> {z.empty()})']
    lines.append('  ' + ' /\\\n  '.join(claims) + '.')
    return _statement(k, lines)


def _same_set_spec(k, family, e):
    """same_set: the output (of) is canonical, empty exactly when the input (from) is, has the same
    members, and for a nonempty input the same bounds as extended real numbers (the signs of zeros
    are not claimed)."""
    of, src = _Set(e['of']), _Set(e['from'])
    _bound(k, ['z'])
    lines = _head(k, family) + _hypotheses(k) + [_let(k, family)]
    claims = [of.canonical(), f'({of.empty()} <-> {src.empty()})',
              f'(forall z : R, {of.member("z")} <-> {src.member("z")})',
              f'({src.nonempty()} -> {of.lower()} = {src.lower()} /\\ {of.upper()} = {src.upper()})']
    lines.append('  ' + ' /\\\n  '.join(claims) + '.')
    return _statement(k, lines)


REL = {'lt': '<', 'le': '<=', 'eq': '='}


def _holds(k, e, sets, negated=False):
    """The relation of a certain or trit entry as a proposition, as the statements of the default
    predicates state it (ieee._Sets.holds), over stored pairs; with `negated` (the `no` of a trit),
    its failure for every choice of members."""
    rel, args = e['rel'], e['args']
    if rel in REL:
        names = [a for a in args if a != ir.ZERO]
        body = f'{args[0]} {REL[rel]} {args[1]}'
        if negated:
            body = f'~ ({body})'
        ne = ' /\\ '.join(sets[x].nonempty() for x in names)
        return (f'{ne} /\\\n    (forall {" ".join(names)} : R, ' + ' '.join(f'{sets[x].member(x)} ->' for x in names) +
                f' {body})')
    if rel == 'member':
        p, s = args
        inside = f'finite {p} /\\ {sets[s].member(f"(val {p})")}'
        return f'~ ({inside})' if negated else inside
    if negated:
        raise PrintError(f'kernel {k.name}: {rel} has no three-valued reading')
    x = args[0]
    if rel == 'empty':
        return sets[x].empty()
    if rel == 'entire':
        return f'(forall z : R, {sets[x].member("z")})'
    y = args[1]
    if rel == 'subset':
        return f'(forall z : R, {sets[x].member("z")} -> {sets[y].member("z")})'
    if rel == 'equal':
        return f'(forall z : R, {sets[x].member("z")} <-> {sets[y].member("z")})'
    if rel == 'interior':
        return (f'(forall z : R, {sets[x].member("z")} ->\n    exists d : R, 0 < d /\\ '
                f'(forall w : R, Rabs (w - z) < d -> {sets[y].member("w")}))')
    if rel == 'disjoint':
        return f'~ (exists z : R, {sets[x].member("z")} /\\ {sets[y].member("z")})'
    raise PrintError(f'kernel {k.name}: no reading of the relation {rel}')


def _predicate_spec(k, family, e):
    """certain and trit, exact: the mask true exactly when the relation holds (trit: yes exactly
    when it holds for every choice of members, no exactly when it fails for every one, never both)."""
    if not e.get('exact'):
        raise PrintError(f'kernel {k.name}: the predicates of the round-up interval are exact')
    sets = {x: _Set(b) for x, b in e['intervals'].items()}
    _bound(k, list(sets) + ['z', 'w', 'd'])
    lines = _head(k, family) + _hypotheses(k) + [_let(k, family)]
    if e['kind'] == 'certain':
        claims = [f'({e["of"]} = true <->\n    {_holds(k, e, sets)})']
    else:
        claims = [f'({e["yes"]} = true <->\n    {_holds(k, e, sets)})',
                  f'({e["no"]} = true <->\n    {_holds(k, e, sets, negated=True)})',
                  f'~ ({e["yes"]} = true /\\ {e["no"]} = true)']
    lines.append('  ' + ' /\\\n  '.join(claims) + '.')
    return _statement(k, lines)


PRINTERS = {'encloses_interval': _interval_spec, 'interval_set': _interval_set_spec,
            'makes_interval': _makes_interval_spec, 'same_set': _same_set_spec,
            'certain': _predicate_spec, 'trit': _predicate_spec}


def kernel_statement(k, kernels):
    """The statement K_spec of one kernel of the family, as a list of lines."""
    family = _kernels(kernels)
    if len(k.ensures) != 1 or k.ensures[0]['kind'] not in PRINTERS:
        raise PrintError(f'kernel {k.name}: a kernel of the round-up interval has one claim, of the kinds '
                         f'{", ".join(PRINTERS)}')
    e = k.ensures[0]
    return PRINTERS[e['kind']](k, family, e)


def statements(kernels):
    family = _kernels(kernels)
    lines = [HEADER, '',
             '(* The statements about the IEEE model of the round-up interval (UpwardModel.v), built from',
             '   the claims in the shapes of docs/developer/design/upward.md, "Statements", in the vocabulary',
             '   of IeeeUpwardVocabulary.v, IeeeIntervalVocabulary.v and IeeeVocabulary.v: for all precisions',
             '   from the kernel\'s minimum on and all emax with prec < emax, for every choice of the NaN each',
             '   operation returns and every max_nl with the property max_nl_ok (IeeeUpwardOperations.v);',
             '   the sums and the products are rounded toward +infinity, and emin = 3 - emax - prec. A',
             '   hand-written proof of statement S is a theorem whose type is exactly S. *)',
             'From Stdlib Require Import Reals ZArith.',
             'From Flocq Require Import Core Binary.',
             f'From {THEORIES_PATH} Require Import IeeeVocabulary IeeeIntervalVocabulary IeeeUpwardOperations '
             'IeeeUpwardVocabulary.',
             f'From {GEN_PATH} Require UpwardModel.',
             'Open Scope R_scope.']
    for k in family.values():
        lines += [''] + kernel_statement(k, family)
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------------------------------------
# UpwardAudit.v

def audit(kernels):
    """For every kernel of the family whose ieee_status is proved, the check that its ieee_theorem has
    exactly the generated statement as its type, and its assumptions. Nothing else is printed."""
    family = _kernels(kernels)
    verified = [k for k in family.values() if k.ieee_theorem and k.ieee_status == 'proved']
    lines = [HEADER, '',
             '(* For every statement of the round-up interval whose theorem is named (ieee_theorem): the',
             '   theorem has exactly the generated statement as its type, and the axioms it depends on are',
             '   printed, for the audit script to compare with the allow-list. Nothing else is printed. *)',
             f'From {GEN_PATH} Require Import UpwardStatements.']
    for m in sorted({rocq.theory_module(k.ieee_theorem[0]) for k in verified}):
        lines.append(f'From {THEORIES_PATH} Require Import {m}.')
    if not verified:
        lines += ['', '(* No statement of the round-up interval has a theorem yet. *)']
    for k in verified:
        lines += ['', f'Definition {k.name}_audit : {k.name}_spec := {k.ieee_theorem[1]}.',
                  f'Print Assumptions {k.ieee_theorem[1]}.']
    return '\n'.join(lines) + '\n'
