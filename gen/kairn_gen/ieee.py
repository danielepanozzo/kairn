"""The IEEE-model Rocq printer: proofs/gen/IeeeModel.v, IeeeStatements.v and IeeeAudit.v.

The IEEE model defines each kernel over Flocq's binary_float prec emax, with the operations of
proofs/theories/IeeeOperations.v (Bplus, Bfma, Bmult, ... rounded to nearest, ties to even), which are
not kernel-specific and are imported, not printed. The section declares the same variables, in
the same order, as IeeeOperations.v's: prec, emax, the two instances Flocq needs, and one NaN-choice
function per operation (nan_plus, nan_minus, nan_opp, nan_abs, nan_fma, nan_mult) and the NaN of
`const nan` (nan_const). Closing the section abstracts each definition over the variables it uses,
in that order: that is the list of binders of every statement. A kernel with an operation the IEEE
model has not (fnma, muladd, mul: no kernel of gen/kernels) is left out. After the section come
the kernels with a statement of the finite domain (below), and their callees, as straight-line
programs of Program.v.

The statements are printed from the claims in the shapes described in
proofs/theories/IeeeVocabulary.v, whose vocabulary (finite, val, ieee_emin, nan2, canonical_2, xval,
xround, ball_1, in_ball_1, ...) is imported from there:
- a kernel of the extended domain has one statement: F1 to F5 for a full kernel (extends); B1 to B3,
  B4 when the claim has finite_when conditions, and containment for a ball (encloses); represents
  (the constructors, neg_2, abs_2, for which it implies their normalized and exact error) and
  makes_ball; and, for the other kernels that need no fix-up, their claims read over extended real
  numbers. It is named K_spec when the kernel has no real-model statement, K_ieee_spec otherwise;
- a kernel of the finite domain has the statements its description asks for (`ieee:` spec,
  bridge; `ieee_finite:`, `ieee_finite_result:` thresholds): K_ieee_spec (finite operands and a
  finite output limb 0 give the claims), K_ieee_bridge_spec (every value of its program is finite
  and the outputs are those of the real model), K_ieee_finite_spec and
  K_ieee_finite_result_spec (under a threshold every value is finite).

Like the real-model printer, this one is trusted. Before the hand-written drafts of this
model were retired, a Rocq file checked by conversion alone that what it prints was the drafts'
text, kernel by kernel and statement by statement; the theorems are now about the printed text.
"""
import re

from . import expr, ir, rocq

THEORIES_PATH = 'Kairn'
GEN_PATH = 'Kairn.Gen'
HEADER = rocq.HEADER

# The NaN-choice variables of the section, in order, and their types in the statements.
NANS = (('nan_plus', 'nan2'), ('nan_minus', 'nan2'), ('nan_opp', 'nan1'), ('nan_abs', 'nan1'),
        ('nan_fma', 'nan3'), ('nan_mult', 'nan2'), ('nan_const', None))
CONST_NAN_TYPE = '{x : binary_float prec emax | is_nan prec emax x = true}'
# The NaN-choice variables each operation of IeeeOperations.v takes.
OP_NANS = {'add': ('nan_plus',), 'sub': ('nan_minus',), 'neg': ('nan_opp',), 'abs': ('nan_abs',),
           'fma': ('nan_fma',), 'fms': ('nan_opp', 'nan_fma'), 'prod': ('nan_fma',),
           'times_inf': ('nan_mult',), 'guard': ('nan_plus',)}
# Each operation as a term of the IEEE model, over the section's local notations.
SPELL = {
    'add': 'add {0} {1}', 'sub': 'sub {0} {1}', 'neg': 'neg {0}', 'abs': 'abs {0}',
    'fma': 'fma {0} {1} {2}', 'fms': 'fms {0} {1} {2}', 'prod': 'prod {0} {1}',
    'times_inf': 'times_inf {0}', 'lt': 'lt {0} {1}', 'le': 'le {0} {1}', 'eq': 'eq {0} {1}',
    'and': 'andb {0} {1}', 'or': 'orb {0} {1}', 'not': 'negb {0}',
    'select': 'if {0} then {1} else {2}', 'succ': 'succ {0}', 'pred': 'pred {0}', 'copy': '{0}',
    'guard': 'guard {0}',
}
# The operations a straight-line program of Program.v has (Kairn.Program.instr).
INSTR = {'add': 'Iadd', 'sub': 'Isub', 'neg': 'Ineg', 'fma': 'Ifma', 'fms': 'Ifms', 'prod': 'Iprod',
         'guard': 'Iguard'}


class PrintError(Exception):
    pass


def missing_operations(k, kernels):
    """The operations of k (calls inlined) that the IEEE model has not: fnma, muladd and mul,
    which no kernel of gen/kernels uses."""
    return sorted({p.op for p in ir.prims(k, kernels) if p.op not in SPELL})


def in_model(kernels):
    """The kernels the IEEE model defines: all but those with an operation it has not (rules.py
    refuses that for a kernel that needs an IEEE-model statement)."""
    return {name: k for name, k in kernels.items() if not missing_operations(k, kernels)}


def _used_nans(k, kernels):
    """The NaN-choice variables the closed definition of k takes, in section order."""
    used = set()
    for p in ir.prims(k, kernels):
        if p.op not in SPELL:
            raise PrintError(f'kernel {k.name}: the IEEE model has no {p.op}')
        used.update(OP_NANS.get(p.op, ()))
        for a in p.args:
            if a.const and a.name == 'nan':
                used.add('nan_const')
    return [n for n, _ in NANS if n in used]


def _binders(names):
    """(nan_plus nan_minus : nan2 prec emax) (nan_opp : nan1 prec emax): consecutive variables of
    one type share a binder."""
    out = []
    for n in names:
        t = dict(NANS)[n]
        t = f'{t} prec emax' if t else CONST_NAN_TYPE
        if out and out[-1][1] == t:
            out[-1][0].append(n)
        else:
            out.append(([n], t))
    return ' '.join(f'({" ".join(ns)} : {t})' for ns, t in out)


# ---------------------------------------------------------------------------------------------
# IeeeModel.v

def _const_names(kernels, real):
    """{constant name: the name of its definition}, the same in Model.v and here (inf, nan and 0
    are not here). Each is defined here from its definition in Model.v, which has the constants of
    the kernels with a real-model statement (`real`): a constant only a full kernel or a
    constructor uses has none, and is refused."""
    ups = rocq.up_names(real)
    in_model = {a.name for k in real.values() for st in k.body for a in st.args if a.const}
    out = {}
    for k in kernels.values():
        for st in k.body:
            for a in st.args:
                if a.const and a.name not in (ir.ZERO,) + ir.SPECIAL:
                    if a.name not in in_model:
                        raise PrintError(f'kernel {k.name}: const {a.name} is not in the real model, '
                                         'from which the IEEE model takes its value')
                    out[a.name] = rocq._const_name(a.name, ups)
    return out


def _real_constant(name, rname):
    """The real-model term of a constant, at the emin and prec of the IEEE format: the arguments
    of its closed definition in Model.v (prec alone for those of ir.CONSTANTS)."""
    if name in ir.CONSTANTS:
        return f'Model.{rname} prec'
    return f'Model.{rname} (3 - emax - prec) prec'


def _operand(a, cnames):
    if not a.const:
        return a.name
    if a.name == ir.ZERO:
        return 'pzero'
    if a.name == 'inf':
        return 'pinf'
    if a.name == 'nan':
        return 'cnan'
    return cnames[a.name]


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


def definition(k, kernels, cnames):
    lines = [f'(* {k.name}: {k.source or "no source given"}. *)',
             f'Definition {k.name}{_params(k.input_limbs, k.input_kinds)} : '
             f'{" * ".join(map(_type, k.output_kinds))} :=']
    for st in k.body:
        args = [_operand(a, cnames) for a in st.args]
        if st.is_call:
            pattern = st.dsts[0] if len(st.dsts) == 1 else "'(" + ', '.join(st.dsts) + ')'
            lines.append(f'  let {pattern} := {" ".join([st.op] + args)} in')
        else:
            if st.op not in SPELL:
                raise PrintError(f'kernel {k.name}: the IEEE model has no {st.op}')
            lines.append(f'  let {st.dsts[0]} := {SPELL[st.op].format(*args)} in')
    outs = k.output_limbs
    lines.append(f'  {outs[0]}.' if len(outs) == 1 else f'  ({", ".join(outs)}).')
    return lines


def program(k, kernels):
    """The kernel as a straight-line program of Program.v (calls inlined), or None when one of its
    operations is not an instruction or an operand is a constant."""
    items = ir.flatten(k, kernels)
    position = {v: i for i, v in enumerate(k.input_limbs)}
    instrs = []
    for it in items:
        if isinstance(it, ir.CallMark):
            continue
        if it.op not in INSTR or any(a.const for a in it.args):
            return None
        args = ' '.join(str(position[a.name]) for a in it.args)
        position[it.dst] = len(position)
        instrs.append((f'{INSTR[it.op]} {args}', position[it.dst], it.dst))
    if any(k.output_kinds[i] != ir.LIMB for i in range(len(k.output_kinds))):
        return None
    return instrs


def has_program(k, kernels):
    return program(k, kernels) is not None


def program_kernels(kernels):
    """The kernels printed as programs: those with an IEEE-model statement of the finite domain
    (ieee:, ieee_finite:, ieee_finite_result:), and the kernels they call, in order."""
    wanted = set()

    def visit(k):
        if k.name not in wanted:
            wanted.add(k.name)
            for st in k.body:
                if st.is_call:
                    visit(kernels[st.op])
    for k in kernels.values():
        if k.ieee or k.ieee_finite or k.ieee_finite_result:
            visit(k)
    return [k for k in kernels.values() if k.name in wanted and has_program(k, kernels)]


def model(kernels):
    real = rocq.real(kernels)
    kernels = in_model(kernels)
    cnames = _const_names(kernels, real)
    lines = [HEADER, '',
             '(* The IEEE model of every kernel: one function over Flocq\'s binary_float prec emax, with',
             '   the operations of IeeeOperations.v (rounded to nearest, ties to even, overflow included), in',
             '   a section whose variables are those of IeeeOperations.v, in the same order: closing it',
             '   abstracts each definition over the variables it uses. A call stays a call, and the',
             '   names of the values are those of the kernel descriptions. A constant of the format is',
             '   the number of the format whose value is the constant of the real model (Model.v). Then',
             '   the kernels that are straight-line programs of Program.v (calls inlined), for the',
             '   statements that relate the two models. *)',
             'From Stdlib Require Import Reals ZArith List.',
             'From Flocq Require Import Core Binary.',
             f'From {GEN_PATH} Require Model.',
             f'From {THEORIES_PATH} Require Import Program.',
             f'From {THEORIES_PATH} Require IeeeOperations.',
             'Import ListNotations.',
             '',
             'Section IeeeKernels.',
             'Variable prec emax : Z.',
             'Context {prec_gt_0_ : Prec_gt_0 prec}.',
             'Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.',
             '',
             'Notation float := (binary_float prec emax).',
             'Notation nan_of := {x : float | is_nan prec emax x = true}.',
             '',
             'Variable nan_plus : float -> float -> nan_of.',
             'Variable nan_minus : float -> float -> nan_of.',
             'Variable nan_opp : float -> nan_of.',
             'Variable nan_abs : float -> nan_of.',
             'Variable nan_fma : float -> float -> float -> nan_of.',
             'Variable nan_mult : float -> float -> nan_of.',
             'Variable nan_const : nan_of.',
             '',
             '(* The operations of IeeeOperations.v, applied to the variables of this section. *)',
             'Local Notation pzero := (IeeeOperations.pzero prec emax).',
             'Local Notation pinf := (IeeeOperations.pinf prec emax).',
             'Local Notation cnan := (IeeeOperations.cnan prec emax nan_const).',
             'Local Notation add := (IeeeOperations.add prec emax nan_plus).',
             'Local Notation sub := (IeeeOperations.sub prec emax nan_minus).',
             'Local Notation neg := (IeeeOperations.neg prec emax nan_opp).',
             'Local Notation abs := (IeeeOperations.abs prec emax nan_abs).',
             'Local Notation fma := (IeeeOperations.fma prec emax nan_fma).',
             'Local Notation fms := (IeeeOperations.fms prec emax nan_opp nan_fma).',
             'Local Notation prod := (IeeeOperations.prod prec emax nan_fma).',
             'Local Notation times_inf := (IeeeOperations.times_inf prec emax nan_mult).',
             'Local Notation lt := (IeeeOperations.lt prec emax).',
             'Local Notation le := (IeeeOperations.le prec emax).',
             'Local Notation eq := (IeeeOperations.eq prec emax).',
             'Local Notation succ := (IeeeOperations.succ prec emax).',
             'Local Notation pred := (IeeeOperations.pred prec emax).',
             'Local Notation guard := (IeeeOperations.guard prec emax nan_plus).',
             'Local Notation const_of := (IeeeOperations.const_of prec emax).']
    done = set()
    for name, rname in sorted(cnames.items(), key=lambda kv: kv[1]):
        if rname in done:
            continue
        done.add(rname)
        lines += ['', f'(* {name}, as a number of the format. *)',
                  f'Definition {rname} : float := const_of ({_real_constant(name, rname)}).']
    for k in kernels.values():
        lines += [''] + definition(k, kernels, cnames)
    lines += ['', 'End IeeeKernels.']
    progs = [(k, program(k, kernels)) for k in program_kernels(kernels)]
    if progs:
        lines += ['', '(** * The kernels that are straight-line programs *)', '',
                  '(* The inputs are numbered from 0 in the order of the kernel\'s arguments, and each',
                  '   instruction defines the next position (Program.v). *)']
    for k, p in progs:
        lines += ['', f'(* inputs: {", ".join(f"{i} {v}" for i, v in enumerate(k.input_limbs))} *)',
                  f'Definition {k.name}_prog : list instr :=']
        width = max(len(i) for i, _, _ in p)
        for n, (instr, pos, dst) in enumerate(p):
            lines.append(f'  {"[" if n == 0 else ";"} {instr:<{width}}  (* {pos:>2} {dst} *)')
        lines.append('  ].')
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------------------------------------
# Terms of the statements

def _val_sum(limbs, f='val'):
    return f'{f} {limbs[0]}' if len(limbs) == 1 else '(' + ' + '.join(f'{f} {v}' for v in limbs) + ')'


def _paren(t):
    return t if t.startswith('(') or ' ' not in t else f'({t})'


class _Terms:
    """The terms of a kernel's claims over the IEEE model: `val` of limbs, the real-model
    vocabulary at emin = ieee_emin prec emax."""

    def __init__(self, k):
        self.k = k
        self.ins = {g.name: g for g in k.inputs}
        self.outs = {g.name: g for g in k.outputs}
        self.limbs = set(k.input_limbs)

    def name(self, n):
        if n in self.ins:
            return _val_sum(self.ins[n].limbs)
        if n in self.limbs:
            return f'val {n}'
        raise PrintError(f'kernel {self.k.name}: unknown name {n}')

    def term(self, text, name=None):
        return rocq._term(expr.parse(text), name or self.name)

    def value(self):
        return self.term(self.k.value)

    def xterm(self, text, top=False):
        """An expression of the claims over extended real numbers (names, neg, abs, and the sum,
        difference and product of IEEE 754 on the values), in parentheses unless `top`."""
        def x(t):
            if t[0] == 'name':
                g = _limbs(self.k, self.ins[t[1]].limbs, f'the value of {t[1]}', (1, 2))
                return f'xval_2 {" ".join(g)}' if len(g) == 2 else f'xval {g[0]}'
            if t[0] == 'neg':
                return f'xopp ({x(t[1])})'
            if t[0] == 'abs':
                return f'xabs ({x(t[1])})'
            if t[0] == 'add':
                return f'xadd ({x(t[1])}) ({x(t[2])})'
            if t[0] == 'sub':
                return f'xadd ({x(t[1])}) (xopp ({x(t[2])}))'
            if t[0] == 'mul':
                return f'xmul ({x(t[1])}) ({x(t[2])})'
            raise PrintError(f'kernel {self.k.name}: {t[0]} has no extended reading')
        term = x(expr.parse(text))
        return term if top else f'({term})'

    def exact_condition(self, conditions):
        """The conditions of an exact_when over the values of finite operands."""
        return rocq.exact_condition(
            conditions,
            lambda text: rocq._term(expr.parse(text), self.name, limb=lambda g, i: f'val {self.ins[g].limbs[i]}'),
            lambda text: rocq._term(expr.parse(text), lambda n: {'u': 'u prec', 'eta': f'eta {EMIN}'}[n]))


EMIN = '(ieee_emin prec emax)'


def _limbs(k, limbs, what, sizes=(2,)):
    """The limbs of a group, refused when the vocabulary of the statements has no word for that
    many (canonical_2, normalized_2, xval_2, ball_2 are about two limbs; xval and ball_1 one)."""
    if len(limbs) not in sizes:
        raise PrintError(f'kernel {k.name}: {what} has {len(limbs)} limbs, and the IEEE-model statements '
                         f'have words for {" or ".join(map(str, sizes))}')
    return limbs


def _normalized_ieee(limbs, k=None):
    if len(limbs) != 2:
        raise PrintError(f'kernel {k.name if k else "?"}: normalized of {len(limbs)} limbs in the IEEE model')
    return f'normalized_2 {EMIN} prec (val {limbs[0]}) (val {limbs[1]})'


def _claim(e, k, t, outs):
    """One ensures entry of a kernel's real-model claims, over the IEEE model, with the output
    groups `outs` (name -> limbs, the core's names mapped to the full kernel's)."""
    kind = e['kind']
    if kind == 'normalized':
        return _normalized_ieee(outs[e['of']], k)
    value = t.value()
    if kind == 'leading_rounded':
        return f'val {outs[e["of"]][0]} = RN {EMIN} prec {value}'
    if kind == 'error':
        limbs = outs[e['of']]
        c, tt = expr.parse(e['c']), expr.parse(e['t'])
        zero = ('int', 0)
        if c == zero and tt == zero:
            bound = f'{_val_sum(limbs)} = {value}'
        else:
            if e['form'] == 'R':
                rho = f'Rabs {value}'
            elif e['form'] == 'A':
                rho = '(' + ' + '.join(f'Rabs {_val_sum(g.limbs)}' for g in k.inputs) + ')'
            else:
                # Relative to the terms of the value, as in the real model: s+x*y gives |s| + |x*y|.
                rho = '(' + ' + '.join(f'Rabs {_paren(rocq._term(x, t.name))}'
                                       for x in rocq.terms(expr.parse(k.value))) + ')'
            terms = []
            if c != zero:
                terms.append(f'{rocq._term(c, lambda n: "u prec")} * u prec ^ {e["k"]} * {rho}')
            if tt != zero:
                terms.append(f'{rocq._term(tt, None)} * eta {EMIN}')
            bound = f'Rabs ({_val_sum(limbs)} - {value}) <= {" + ".join(terms)}'
        if e['when'] == 'product_large':
            bound = (f'(({value} = 0 \\/ bpow radix2 (2 * prec - 1) * eta {EMIN} <= Rabs {value}) ->'
                     f' {bound})')
        if 'exact_when' in e:
            bound += f' /\\\n  ({t.exact_condition(e["exact_when"])} ->\n   {_val_sum(limbs)} = {value})'
        return bound
    raise PrintError(f'kernel {k.name}: no IEEE reading of {kind}')


def _head(k, nans, precision=True):
    """The binders common to every statement: the format, its instances, the NaN choices, the
    precision, the inputs."""
    lines = ['  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)',
             '         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)' +
             (f'\n         {_binders(nans)},' if nans else ',')]
    if precision:
        lines.append(f'  ({k.min_precision or 1} <= prec)%Z ->')
    limbs = [v for v, kind in zip(k.input_limbs, k.input_kinds) if kind == ir.LIMB]
    masks = [v for v, kind in zip(k.input_limbs, k.input_kinds) if kind == ir.MASK]
    lines.append(f'  forall {" ".join(limbs)} : binary_float prec emax,')
    if masks:
        lines.append(f'  forall {" ".join(masks)} : bool,')
    return lines


def _call(k, kernels):
    nans = _used_nans(k, kernels)
    return f'IeeeModel.{k.name} prec emax {" ".join(nans + k.input_limbs)}'.replace('  ', ' ')


def _let(k, kernels):
    outs = k.output_limbs
    pattern = outs[0] if len(outs) == 1 else "'(" + ', '.join(outs) + ')'
    return f'  let {pattern} := {_call(k, kernels)} in'


def _requires_finite(k, t):
    """Hypotheses of a statement on finite operands: finite inputs, then the requirements."""
    lines = ['  ' + ' -> '.join(f'finite {v}' for v in k.input_limbs) + ' ->']
    for r in k.requires:
        if r[0] == 'normalized':
            lines.append(f'  {_normalized_ieee(t.ins[r[1]].limbs, k)} ->')
        elif r[0] == 'abs_ge':
            lines.append(f'  Rabs {_paren(_val_sum(t.ins[r[2]].limbs))} <= Rabs {_paren(_val_sum(t.ins[r[1]].limbs))} ->')
        elif r[0] == 'power_of_two':
            lines.append(f'  (exists n : Z, val {r[1]} = bpow radix2 n) ->')
        elif r[0] == 'nonneg':
            lines.append(f'  0 <= val {r[1]} ->')
        else:
            raise PrintError(f'kernel {k.name}: no finite reading of {r[0]}')
    return lines


def _condition(c, t, abs_le_names=None):
    tree = expr.parse(c['abs_le'])
    term = rocq._term(tree, t.name)
    e = c['exp']
    bound = 'emax' if e == 0 else f'(emax {"-" if e < 0 else "+"} {abs(e)})'
    return f'Rabs {_paren(term)} <= bpow radix2 {bound}'


def _all_nans():
    return ['nan_plus', 'nan_minus', 'nan_opp', 'nan_fma']


def _run(k):
    return (f'  Forall finite (run (stepB prec emax nan_plus nan_minus nan_opp nan_fma)\n'
            f'                     IeeeModel.{k.name}_prog [{"; ".join(k.input_limbs)}])')


def _statement(name, comment, lines):
    return [f'(* {comment} *)', f'Definition {name} : Prop :='] + lines


def _comment(k, theorem=None):
    """The comment above a statement of kernel k: its status is that of the kernel's IEEE-model
    statement (ieee_status), or, for a statement of the finite domain whose theorem the kernel
    names (`theorem`, one of ir.IEEE_THEOREM_KEYS), proved."""
    status = 'proved' if theorem else (k.ieee_status or 'unverified')
    return f'{k.name}: {k.source or "no source given"}. IEEE-model status: {status}.'


def _finite_ieee_spec(k, kernels):
    t = _Terms(k)
    lines = _head(k, _used_nans(k, kernels)) + _requires_finite(k, t) + [_let(k, kernels)]
    out = k.outputs[0].limbs
    lines.append(f'  finite {out[0]} ->')
    outs = {g.name: g.limbs for g in k.outputs}
    claims = [f'finite {v}' for v in k.output_limbs[1:]] + [_claim(e, k, t, outs) for e in k.ensures]
    lines.append('  ' + ' /\\\n  '.join(claims) + '.')
    return _statement(f'{k.name}_ieee_spec', _comment(k, k.ieee_spec_theorem), lines)


def _bridge_spec(k, kernels):
    t = _Terms(k)
    lines = _head(k, _all_nans()) + _requires_finite(k, t) + [_let(k, kernels)]
    out = k.output_limbs
    args = rocq.section_args(k, kernels)
    real = ' '.join([k.name] + [{'emin': EMIN, 'prec': 'prec', 'choice': 'tie_even'}[v] for v in args] +
                    [f'(val {v})' for v in k.input_limbs])
    lines += [f'  finite {out[0]} ->', _run(k) + ' /\\']
    lines += [f'  finite {v} /\\' for v in out[1:]]
    lines += [f'  ({", ".join(f"val {v}" for v in out)})', f'  = {real}.']
    return _statement(f'{k.name}_ieee_bridge_spec', _comment(k, k.ieee_bridge_theorem), lines)


def _threshold_spec(k, kernels, conditions, suffix):
    t = _Terms(k)
    lines = _head(k, _all_nans()) + _requires_finite(k, t)
    lines += [f'  {_condition(c, t)} ->' for c in conditions]
    out = k.output_limbs
    lines += [_run(k) + ' /\\', _let(k, kernels), '  ' + ' /\\ '.join(f'finite {v}' for v in out) + '.']
    return _statement(f'{k.name}_ieee_{suffix}_spec', _comment(k), lines)


def _hyps_extended(k, t):
    """Hypotheses in the extended domain: canonical operands, balls, nonneg_ext, powers of two."""
    lines = []
    for r in k.requires:
        if r[0] == 'canonical':
            lines.append(f'  canonical_2 {" ".join(_limbs(k, t.ins[r[1]].limbs, r[1]))} ->')
        elif r[0] == 'ball':
            c = t.ins[r[1]].limbs
            lines.append(f'  ball_{len(c)} {" ".join(_limbs(k, c, r[1], (1, 2)))} {r[2]} ->')
        elif r[0] == 'nonneg':
            lines.append(f'  nonneg_ext {r[1]} ->')
        elif r[0] == 'power_of_two':
            lines += [f'  finite {r[1]} ->', f'  (exists n : Z, val {r[1]} = bpow radix2 n) ->']
        else:
            raise PrintError(f'kernel {k.name}: no extended reading of {r[0]}')
    return lines


def _ieee_op(op, args):
    nans = ' '.join(OP_NANS.get(op, ()))
    return f'IeeeOperations.{op} prec emax {nans} {" ".join(args)}'.replace('  ', ' ')


def _full_spec(k, kernels, e):
    """F1 to F5 of milestone1.md for a full kernel (extends)."""
    core = kernels[e['core']]
    t = _Terms(k)
    nans = _used_nans(k, kernels)
    lines = _head(k, nans) + _hyps_extended(k, t)
    # t, as the kernel computes it, with the values it is computed from written out.
    defs = {st.dsts[0]: st for st in k.body if not st.is_call}

    def term(name, top=False):
        st = defs.get(name)
        if st is None:
            return name
        inner = _ieee_op(st.op, [term(a.name) for a in st.args])
        return inner if top else f'({inner})'
    lines.append(f'  let t := {term("t", top=True)} in')
    lines.append(_let(k, kernels))
    w = k.outputs[0].limbs
    assumed = {r[1] for r in k.requires if r[0] == 'power_of_two'}
    leads = [g.limbs[0] for g in k.inputs if g.name not in assumed]
    outs = {core.outputs[0].name: w}
    f2 = [f'finite {v}' for v in k.input_limbs if v not in assumed] + [f'finite {v}' for v in w[1:]]
    f2 += [_claim(c, core, _Terms(core), outs) for c in core.ensures]
    fin = ' -> '.join(f'finite {v}' for v in leads)
    lines.append(f'  canonical_2 {" ".join(w)} /\\')
    lines.append(f'  (finite {w[0]} ->\n   ' + ' /\\\n   '.join(f2) + ') /\\')
    conds = [_condition(c, t) for c in e['finite_when']]
    lines.append(f'  ({fin} ->\n   ' + ' ->\n   '.join(conds + [f'finite {w[0]}']) + ') /\\')
    lines.append(f'  ({fin} -> ~ finite {w[0]} ->\n   {w[0]} = infinity prec emax (Rlt_bool {t.value()} 0) /\\ '
                 f'{w[1]} = pos_zero prec emax) /\\')
    conj = ' /\\ '.join(f'finite {v}' for v in leads)
    notfin = f'~ ({conj})' if len(leads) > 1 else f'~ finite {leads[0]}'
    lines.append(f'  ({notfin} -> canonical_of t {" ".join(w)}).')
    return _statement(f'{k.name}_spec', _comment(k), lines)


def _ball_args(limbs, r):
    return f'{" ".join(limbs)} {r}'


def _ball_spec(k, kernels, e):
    """B1 to B3 and containment in every case, for a ball kernel of the extended domain; and B4,
    between B3 and containment, when the claim has conditions (finite_when): finite operands
    under these conditions give a finite ball. An empty list claims nothing, and prints nothing."""
    t = _Terms(k)
    lines = _head(k, _used_nans(k, kernels)) + _hyps_extended(k, t) + [_let(k, kernels)]
    c_out, r_out = _limbs(k, t.outs[e['center']].limbs, e['center'], (1, 2)), e['radius']
    n = len(c_out)
    out = _ball_args(c_out, r_out)
    balls = [(b, t.ins[cr['center']].limbs, cr['radius']) for b, cr in e['balls'].items()]
    taken = {x for _, c, r in balls for x in list(c) + [r]}
    scalars = [v for v in k.input_limbs if v not in taken]
    lines.append(f'  ball_{n} {out} /\\')
    empties = ' \\/ '.join(f'ball_empty_{len(c)} {_ball_args(c, r)}' for _, c, r in balls)
    lines.append(f'  (ball_empty_{n} {out} <-> {empties}) /\\')
    names = ' '.join(b for b, _, _ in balls)

    def set_term():
        return rocq._term(expr.parse(e['set']), lambda x: x if x in e['balls'] else t.name(x))
    inside = ' '.join(f'Rabs ({b} - {_val_sum(c)}) <= val {r} ->' for b, c, r in balls)
    finite_ops = [f'ball_finite_{len(c)} {_ball_args(c, r)}' for _, c, r in balls] + [f'finite {v}' for v in scalars]
    lines.append(f'  (ball_finite_{n} {out} ->\n   ' + ' /\\ '.join(finite_ops) + ' /\\\n'
                 f'   (forall {names} : R, {inside}\n    Rabs ({set_term()} - {_val_sum(c_out)}) <= val {r_out})) /\\')
    if 'exact_when' in e:
        # A finite result under the conditions is the set exactly: it contains nothing else.
        member = rocq.MEMBER
        within = ' /\\ '.join(f'Rabs ({b} - {_val_sum(c)}) <= val {r}' for b, c, r in balls)
        lines.append(f'  (ball_finite_{n} {out} -> {t.exact_condition(e["exact_when"])} ->\n'
                     f'   forall {member} : R, Rabs ({member} - {_val_sum(c_out)}) <= val {r_out} ->\n'
                     f'   exists {names} : R, {within} /\\ {member} = {set_term()}) /\\')
    conds = [_condition(c, t) for c in e.get('finite_when', [])]
    if conds:
        lines.append('  (' + ' -> '.join(finite_ops) + ' ->\n   ' +
                     ' ->\n   '.join(conds + [f'ball_finite_{n} {out}']) + ') /\\')
    ins = ' '.join(f'in_ball_{len(c)} {_ball_args(c, r)} {b} ->' for b, c, r in balls)
    pre = ''.join(f'finite {v} -> ' for v in scalars)
    lines.append(f'  ({pre}forall {names} : R, {ins} in_ball_{n} {out} {set_term()}).')
    return _statement(f'{k.name}_spec' if not k.real_model else f'{k.name}_ieee_spec', _comment(k), lines)


def _represents_spec(k, kernels, e):
    """The output is canonical and stands for `value` as an extended real number. When `value` is
    a multi-limb input (make_2_limbs), a finite one also keeps the value of each limb. A
    constructor has no minimum precision in this statement; neg_2 and abs_2, which also claim
    `normalized` and an exact `error` (implied by `represents`), have theirs."""
    others = [x for x in k.ensures if x is not e]
    for x in others:
        exact = x['kind'] == 'error' and x['c'] == '0' and x['t'] == '0'
        if x.get('of') != e['of'] or not (x['kind'] == 'normalized' or exact):
            raise PrintError(f'kernel {k.name}: represents goes with nothing but normalized and an exact '
                             'error of the same output')
    t = _Terms(k)
    lines = (_head(k, _used_nans(k, kernels), precision=bool(others)) + _hyps_extended(k, t) +
             [_let(k, kernels)])
    out = t.outs[e['of']].limbs
    claims = [f'canonical_2 {" ".join(_limbs(k, out, e["of"]))}', f'xval_2 {" ".join(out)} = {t.xterm(k.value, top=True)}']
    g = t.ins[k.value].limbs if k.value in t.ins else ()
    if len(g) == 2:
        claims.append(f'(finite {g[0]} -> ' + ' /\\ '.join(f'val {o} = val {i}' for o, i in zip(out, g)) + ')')
    lines.append('  ' + ' /\\\n  '.join(claims) + '.')
    return _statement(statement_names(k)[0], _comment(k), lines)


def _makes_ball_spec(k, kernels, e):
    t = _Terms(k)
    lines = _head(k, _used_nans(k, kernels), precision=False) + _hyps_extended(k, t) + [_let(k, kernels)]
    c_in, r_in = t.ins[e['from']['center']].limbs, e['from']['radius']
    c_out, r_out = _limbs(k, t.outs[e['center']].limbs, e['center'], (1, 2)), e['radius']
    n = len(c_out)
    out = _ball_args(c_out, r_out)
    guarded = e['from']['center'] in k.program_values() or c_in[0] in k.program_values()
    same = (' /\\ '.join(f'val {o} = val {i}' for o, i in zip(c_out, c_in)) if guarded else
            ' /\\ '.join(f'{o} = {i}' for o, i in zip(c_out, c_in)))
    lines += [f'  ball_{n} {out} /\\',
              f'  (nan {r_in} \\/ {r_in} = infinity prec emax true \\/ (finite {r_in} /\\ val {r_in} < 0) -> '
              f'ball_empty_{n} {out}) /\\',
              f'  (finite {r_in} -> 0 <= val {r_in} -> finite {c_in[0]} ->\n'
              f'   ball_finite_{n} {out} /\\ {same} /\\ val {r_out} = val {r_in}) /\\',
              f'  ({r_in} = infinity prec emax false \\/ (finite {r_in} /\\ 0 <= val {r_in} /\\ ~ finite {c_in[0]}) -> '
              f'ball_whole_{n} {out}).']
    return _statement(f'{k.name}_spec', _comment(k), lines)


def _finite_or_nan_spec(k, kernels, e):
    """The finish of a fold (milestone2.md, "When something is not finite"): the flag is true
    exactly when limb 0 of the value is finite; the output is then the value, limb for limb, and
    otherwise every limb of it is a NaN. For every input: the statement has no hypothesis."""
    t = _Terms(k)
    lines = _head(k, _used_nans(k, kernels), precision=False) + _hyps_extended(k, t) + [_let(k, kernels)]
    src, out, flag = list(t.ins[k.value].limbs), t.outs[e['of']].limbs, e['flag']
    # The finish of a fold of maxima: the value stepped up (steps), under a mask (if).
    for _ in range(e.get('steps', 0)):
        src = [f'({_ieee_op("succ", src)})']
    finite = f'finite {src[0]}'
    if 'if' in e:
        finite = f'{e["if"]} = true /\\ {finite}'
    lines += [f'  ({flag} = true <-> {finite}) /\\',
              f'  ({flag} = true -> ' + ' /\\ '.join(f'{o} = {i}' for o, i in zip(out, src)) + ') /\\',
              f'  ({flag} = false -> ' + ' /\\ '.join(f'nan {o}' for o in out) + ').']
    return _statement(f'{k.name}_spec', _comment(k), lines)


ROUNDING = {'nearest': 'RN', 'down': 'RD', 'up': 'RU'}
RELATION = {'lt': 'xlt', 'le': 'xle', 'eq': 'xeq'}


def _binary(tree):
    """Whether an expression has a sum, a difference or a product: the value of two operands."""
    return tree[0] in ('add', 'sub', 'mul') or any(_binary(x) for x in tree[1:] if isinstance(x, tuple))


def _operands_finite(k):
    """That every operand is finite, as one proposition."""
    return ' /\\ '.join(f'finite {v}' for v in k.input_limbs)


def _extended_claim(e, k, t):
    """One claim of a kernel that needs no fix-up, read over extended real numbers."""
    kind = e['kind']
    if kind == 'predicate':
        a, b = (t.xterm(x) for x in e['args'])
        return f'{e["of"]} = {RELATION[e["rel"]]} {a} {b}'
    if kind == 'rounded':
        value = t.xterm(k.value)
        if not _binary(expr.parse(k.value)) or e['mode'] == 'nearest':
            # A one-operand value (a canonical number, below 2^emax in magnitude), or a rounding to
            # nearest, whose overflow overflow_of says.
            claim = f'xval {e["of"]} = xround emax ({ROUNDING[e["mode"]]} {EMIN} prec) {value}'
        else:
            # The value of two operands, rounded in the format with overflow: RD of a result
            # beyond the largest number is that number, RU of one below the most negative that
            # number (xrd, xru).
            claim = f'xval {e["of"]} = {"xrd" if e["mode"] == "down" else "xru"} prec emax {value}'
        if e.get('when') == 'product_large':
            v = t.value()
            claim = (f'(({_operands_finite(k)} ->\n    {v} = 0 \\/ bpow radix2 (2 * prec - 1) * eta {EMIN} '
                     f'<= Rabs {v}) ->\n   {claim})')
        return claim
    if kind == 'upper':
        r = e['of']
        value = t.value()
        gaps = rocq._term(expr.parse(e['gaps']), None)
        ops = _operands_finite(k)
        return (f'nonneg_ext {r} /\\\n  (finite {r} ->\n   {ops} /\\\n   {value} <= val {r} /\\\n'
                f'   val {r} - {value}\n   <= {gaps} * (val {r} - Ulp.pred radix2 (FLT_exp {EMIN} prec) '
                f'(val {r})))')
    if kind == 'neighbor':
        return f'xval {e["of"]} = {"xsucc" if e["side"] == "up" else "xpred"} prec emax {t.xterm(k.value)}'
    if kind == 'bound':
        # On its side of the value and at most `steps` steps beyond its directed rounding, for
        # finite operands; the value of IEEE 754 otherwise.
        r, value = e['of'], t.xterm(k.value)
        below = e['side'] == 'below'
        limit = f'{"xrd" if below else "xru"} prec emax {value}'
        for _ in range(e['steps']):
            limit = f'{"xpred" if below else "xsucc"} prec emax ({limit})'
        side = (f'xle (xval {r}) {value} = true /\\ xle ({limit}) (xval {r}) = true' if below else
                f'xle {value} (xval {r}) = true /\\ xle (xval {r}) ({limit}) = true')
        ops = _operands_finite(k)
        return f'({ops} ->\n   {side}) /\\\n  (~ ({ops}) -> xval {r} = {value})'
    raise PrintError(f'kernel {k.name}: no IEEE-model statement for the claim {kind}')


def _no_fix_up_spec(k, kernels):
    """A kernel of the extended domain that needs no fix-up: its claims over extended reals."""
    t = _Terms(k)
    lines = _head(k, _used_nans(k, kernels)) + _hyps_extended(k, t) + [_let(k, kernels)]
    lines.append('  ' + ' /\\\n  '.join(_extended_claim(e, k, t) for e in k.ensures) + '.')
    return _statement(f'{k.name}_ieee_spec', _comment(k), lines)


def statement_names(k):
    """The names of the IEEE-model statements of a kernel, in the order they are printed."""
    if k.extended:
        return [f'{k.name}_spec' if not k.real_model else f'{k.name}_ieee_spec']
    out = []
    if 'bridge' in k.ieee:
        out.append(f'{k.name}_ieee_bridge_spec')
    if 'spec' in k.ieee:
        out.append(f'{k.name}_ieee_spec')
    if k.ieee_finite:
        out.append(f'{k.name}_ieee_finite_spec')
    if k.ieee_finite_result:
        out.append(f'{k.name}_ieee_finite_result_spec')
    return out


def kernel_statements(k, kernels):
    """The IEEE-model statements of one kernel, as lists of lines."""
    if k.extended:
        kinds = {e['kind'] for e in k.ensures}
        if 'extends' in kinds:
            return [_full_spec(k, kernels, k.ensures[0])]
        if 'makes_ball' in kinds:
            return [_makes_ball_spec(k, kernels, k.ensures[0])]
        if 'represents' in kinds:
            return [_represents_spec(k, kernels, next(e for e in k.ensures if e['kind'] == 'represents'))]
        if kinds == {'finite_or_nan'}:
            return [_finite_or_nan_spec(k, kernels, k.ensures[0])]
        enc = [e for e in k.ensures if e['kind'] == 'encloses']
        if enc:
            return [_ball_spec(k, kernels, enc[0])]
        return [_no_fix_up_spec(k, kernels)]
    out = []
    if 'bridge' in k.ieee:
        out.append(_bridge_spec(k, kernels))
    if 'spec' in k.ieee:
        out.append(_finite_ieee_spec(k, kernels))
    if k.ieee_finite:
        out.append(_threshold_spec(k, kernels, k.ieee_finite, 'finite'))
    if k.ieee_finite_result:
        out.append(_threshold_spec(k, kernels, k.ieee_finite_result, 'finite_result'))
    return out


def statements(kernels):
    lines = [HEADER, '',
             '(* The statements about the IEEE model (IeeeModel.v), built from the claims in the shapes',
             '   described in proofs/theories/IeeeVocabulary.v, whose vocabulary',
             '   they use: for all precisions from the kernel\'s minimum on and all emax with prec < emax,',
             '   for every choice of the NaN each operation returns, with rounding to nearest, ties to',
             '   even; emin = 3 - emax - prec. A hand-written proof of statement S is a theorem whose type',
             '   is exactly S. *)',
             'From Stdlib Require Import Reals ZArith List.',
             'From Flocq Require Import Core Binary.',
             f'From {GEN_PATH} Require Import Model Statements.',
             f'From {THEORIES_PATH} Require Import Program IeeeBridge IeeeVocabulary.',
             f'From {THEORIES_PATH} Require IeeeOperations.',
             f'From {GEN_PATH} Require IeeeModel.',
             'Import ListNotations.',
             'Open Scope R_scope.']
    for k in in_model(kernels).values():
        for st in kernel_statements(k, kernels):
            lines += [''] + st
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------------------------------------
# IeeeWith.v: the kernels of the rule of the product, with the product as an argument

def with_kernels(kernels):
    """The kernels constexpr by the rule of the product (cpp.product_rule) that the IEEE model
    defines, callees first."""
    from . import cpp
    return [k for k in in_model(kernels).values() if cpp.product_rule(k, kernels)]


def _with_definition(k, kernels, cnames, rule):
    """K_with: the definition of IeeeModel.K with every prod the argument p_, and every call of a
    kernel of `rule` that kernel's K_with p_; any other call stays a call of IeeeModel. The
    argument's name has an underscore, which no value of a listing has (ir.py), so that no value
    hides it (mul_1_1, rmul and two_prod_dekker have a value p)."""
    lines = [f'(* {k.name}: {k.source or "no source given"}. *)',
             f'Definition {k.name}_with (p_ : float -> float -> float)'
             f'{_params(k.input_limbs, k.input_kinds)} : {" * ".join(map(_type, k.output_kinds))} :=']
    for st in k.body:
        args = [_operand(a, cnames) for a in st.args]
        if st.is_call:
            callee = f'{st.op}_with p_' if st.op in rule else st.op
            pattern = st.dsts[0] if len(st.dsts) == 1 else "'(" + ', '.join(st.dsts) + ')'
            lines.append(f'  let {pattern} := {" ".join([callee] + args)} in')
        elif st.op == 'prod':
            lines.append(f'  let {st.dsts[0]} := p_ {args[0]} {args[1]} in')
        else:
            if st.op not in SPELL:
                raise PrintError(f'kernel {k.name}: the IEEE model has no {st.op}')
            lines.append(f'  let {st.dsts[0]} := {SPELL[st.op].format(*args)} in')
    outs = k.output_limbs
    lines.append(f'  {outs[0]}.' if len(outs) == 1 else f'  ({", ".join(outs)}).')
    return lines


def with_model(kernels):
    """proofs/gen/IeeeWith.v (docs/developer/architecture.md, "The formal model")."""
    real = rocq.real(kernels)
    model_kernels = in_model(kernels)
    cnames = _const_names(model_kernels, real)
    rule = with_kernels(kernels)
    names = {k.name for k in rule}
    lines = [HEADER, '',
             '(* The kernels constexpr by the rule of the product (docs/developer/design/milestone2.md, "The',
             '   two executions of a product"), in the IEEE model, with the product as an argument: K_with p_',
             '   is the definition of IeeeModel.K with every `prod a b` written p_ a b, and every call of',
             '   another such kernel written as its K_with p_. With p_ the fused product IeeeOperations.prod',
             '   it is IeeeModel.K, by conversion; with the plain product of constant evaluation it is the',
             '   listing that constant evaluation runs. The section has the variables of IeeeModel.v, in',
             '   the same order, and the names of the values are those of the kernel descriptions. *)',
             'From Stdlib Require Import Reals ZArith.',
             'From Flocq Require Import Core Binary.',
             f'From {THEORIES_PATH} Require IeeeOperations.',
             f'From {GEN_PATH} Require IeeeModel.',
             '',
             'Section IeeeWith.',
             'Variable prec emax : Z.',
             'Context {prec_gt_0_ : Prec_gt_0 prec}.',
             'Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.',
             '',
             'Notation float := (binary_float prec emax).',
             'Notation nan_of := {x : float | is_nan prec emax x = true}.',
             '']
    lines += [f'Variable {n} : {t}.' for n, t in (
        ('nan_plus', 'float -> float -> nan_of'), ('nan_minus', 'float -> float -> nan_of'),
        ('nan_opp', 'float -> nan_of'), ('nan_abs', 'float -> nan_of'),
        ('nan_fma', 'float -> float -> float -> nan_of'), ('nan_mult', 'float -> float -> nan_of'),
        ('nan_const', 'nan_of'))]
    lines += ['',
              '(* The operations of IeeeOperations.v, applied to the variables of this section, as in',
              '   IeeeModel.v. *)',
              'Local Notation pzero := (IeeeOperations.pzero prec emax).',
              'Local Notation pinf := (IeeeOperations.pinf prec emax).',
              'Local Notation cnan := (IeeeOperations.cnan prec emax nan_const).',
              'Local Notation add := (IeeeOperations.add prec emax nan_plus).',
              'Local Notation sub := (IeeeOperations.sub prec emax nan_minus).',
              'Local Notation neg := (IeeeOperations.neg prec emax nan_opp).',
              'Local Notation abs := (IeeeOperations.abs prec emax nan_abs).',
              'Local Notation fma := (IeeeOperations.fma prec emax nan_fma).',
              'Local Notation fms := (IeeeOperations.fms prec emax nan_opp nan_fma).',
              'Local Notation times_inf := (IeeeOperations.times_inf prec emax nan_mult).',
              'Local Notation lt := (IeeeOperations.lt prec emax).',
              'Local Notation le := (IeeeOperations.le prec emax).',
              'Local Notation eq := (IeeeOperations.eq prec emax).',
              'Local Notation succ := (IeeeOperations.succ prec emax).',
              'Local Notation pred := (IeeeOperations.pred prec emax).',
              'Local Notation guard := (IeeeOperations.guard prec emax nan_plus).']
    # The constants and the kernels of IeeeModel.v that these listings use, as there.
    consts, callees = [], []
    for k in rule:
        for st in k.body:
            for a in st.args:
                if a.const and a.name not in (ir.ZERO,) + ir.SPECIAL and cnames[a.name] not in consts:
                    consts.append(cnames[a.name])
            if st.is_call and st.op not in names and st.op not in callees:
                callees.append(st.op)
    if consts or callees:
        lines += ['', '(* The constants and the other kernels of IeeeModel.v that the listings use. *)']
    lines += [f'Local Notation {c} := (IeeeModel.{c} prec emax).' for c in consts]
    for c in callees:
        lines.append(f'Local Notation {c} := (IeeeModel.{c} prec emax{"".join(" " + n for n in _used_nans(kernels[c], kernels))}).')
    for k in rule:
        lines += [''] + _with_definition(k, kernels, cnames, names)
    lines += ['', 'End IeeeWith.']
    return '\n'.join(lines) + '\n'


def proved_statements(kernels):
    """[(statement, theorem file, theorem name, generated file)] of the IEEE-model statements of the finite domain
    and of the folds whose theorems are named: K_ieee_bridge_spec and K_ieee_spec of
    IeeeStatements.v (ieee_bridge_theorem, ieee_spec_theorem), K_ieee_lead_spec (ieee_lead_theorem)
    and F_O_ieee_spec (a fold's ieee_theorem) of IeeeFoldStatements.v; the first two, then the
    others, each in the order of their file."""
    model = in_model(kernels)
    out = []
    for k in model.values():
        if k.extended:
            continue
        for key, spec in (('ieee_bridge_theorem', f'{k.name}_ieee_bridge_spec'), ('ieee_spec_theorem', f'{k.name}_ieee_spec')):
            have = getattr(k, key)
            if have and spec in statement_names(k):
                out.append((spec, have[0], have[1], 'IeeeStatements'))
    for k in lead_kernels(kernels):
        if k.ieee_lead_theorem:
            out.append((f'{k.name}_ieee_lead_spec', k.ieee_lead_theorem[0], k.ieee_lead_theorem[1], 'IeeeFoldStatements'))
    for fd in getattr(kernels, 'folds', {}).values():
        if getattr(fd, 'is_map', False) or not fd.ieee_theorem:
            continue
        for order in ir.ORDERS:
            if order in fd.orders:
                suffix = ir.ORDER_SUFFIX[order]
                out.append((f'{fd.name}_{suffix}_ieee_spec', fd.ieee_theorem, fd.ieee_theorem_name(order),
                            'IeeeFoldStatements'))
    return out


def audit(kernels):
    """For every IEEE-model statement with a theorem (ieee_theorem: of a kernel of the extended
    domain; then those of proved_statements), the check that the theorem has exactly that statement
    as its type, and its assumptions; nothing else is printed. With no theorem of the second kind,
    the file is what it was before they could be named."""
    verified = [k for k in kernels.values() if k.ieee_theorem and k.ieee_status == 'proved']
    more = proved_statements(kernels)
    folds = any(g == 'IeeeFoldStatements' for _, _, _, g in more)
    lines = [HEADER, '',
             '(* For every IEEE-model statement whose theorem is named (ieee_theorem): the theorem has',
             '   exactly the generated statement as its type, and the axioms it depends on are printed,',
             '   for the audit script to compare with the allow-list. Nothing else is printed. *)',
             f'From {GEN_PATH} Require Import IeeeStatements.']
    if folds:
        lines.append(f'From {GEN_PATH} Require Import IeeeFoldStatements.')
    for m in sorted({rocq.theory_module(k.ieee_theorem[0]) for k in verified} | {rocq.theory_module(f) for _, f, _, _ in more}):
        lines.append(f'From {THEORIES_PATH} Require Import {m}.')
    if not verified and not more:
        lines += ['', '(* No IEEE-model statement has a theorem yet. *)']
    for k in verified:
        spec = statement_names(k)[0]
        lines += ['', f'Definition {spec[:-len("_spec")]}_audit : {spec} := {k.ieee_theorem[1]}.',
                  f'Print Assumptions {k.ieee_theorem[1]}.']
    if more:
        lines += ['', '(* The statements of the kernels of the finite domain (IeeeStatements.v), and those of the',
                  '   steps and combinations of the folds and of the folds (IeeeFoldStatements.v), whose',
                  '   theorems are named (ieee_bridge_theorem, ieee_spec_theorem, ieee_lead_theorem; the',
                  '   ieee_theorem of a fold). *)']
    for spec, _, name, _ in more:
        lines += ['', f'Definition {spec[:-len("_spec")]}_audit : {spec} := {name}.',
                  f'Print Assumptions {name}.']
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------------------------------------
# IeeeFoldModel.v and IeeeFoldStatements.v: the folds in the IEEE model

def _ftype(n):
    return rocq.tuple_type(n, 'float')


def _fold_element_ftype(fd):
    types = [_ftype(len(g.limbs)) for g in fd.arrays]
    if len(types) == 1:
        return types[0]
    return ' * '.join(f'({t})' if ' ' in t else t for t in types)


def _kernel_call(k, kernels, args):
    """IeeeModel.K applied to the format, the NaN choices it takes, and `args` (terms)."""
    return ' '.join([f'IeeeModel.{k.name}', 'prec', 'emax'] + _used_nans(k, kernels) + [rocq._paren(a) for a in args])


def _fold_parts(fd, kernels):
    step = kernels[fd.step[0]]
    combine = kernels[fd.combine[0]] if fd.combine else None
    finish = kernels[fd.finish[0]] if fd.finish else None
    return step, combine, finish


def fold_model(kernels):
    """proofs/gen/IeeeFoldModel.v: every fold of the extended domain in the IEEE model, in the shape
    of its real model (FoldModel.v): F_step and F_combine apply the IEEE models of the step and the
    combination (IeeeModel.v) to the limbs of tuples; F_seq is the finish on fold_seq of the step
    from the zero state, every limb +0; F_lanes W the finish on fold_lanes W."""
    folds = [fd for fd in getattr(kernels, 'folds', {}).values()
             if not getattr(fd, 'is_map', False) and not getattr(fd, 'is_conv', False)]
    lines = [HEADER, '',
             '(* The folds in the IEEE model (docs/developer/architecture.md, "Folds"), in the shape of their',
             '   real model (FoldModel.v): the state is a tuple of limbs and an element one entry of every array,',
             '   read with fst and snd; F_step and F_combine apply the IEEE models of the step and the',
             '   combination (IeeeModel.v) to those limbs; the zero state has every limb +0; F_seq is the',
             '   finish of the fold on fold_seq of the step, F_lanes W on fold_lanes with W lanes',
             '   (proofs/theories/Folds.v). The section has the variables of IeeeModel.v, in the same order. *)',
             'From Stdlib Require Import Reals ZArith List.',
             'From Flocq Require Import Core Binary.',
             f'From {THEORIES_PATH} Require Import Folds.',
             f'From {THEORIES_PATH} Require IeeeOperations.',
             f'From {GEN_PATH} Require IeeeModel.',
             '',
             'Section IeeeFolds.',
             'Variable prec emax : Z.',
             'Context {prec_gt_0_ : Prec_gt_0 prec}.',
             'Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.',
             '',
             'Notation float := (binary_float prec emax).',
             'Notation nan_of := {x : float | is_nan prec emax x = true}.',
             '']
    lines += [f'Variable {n} : {t}.' for n, t in (
        ('nan_plus', 'float -> float -> nan_of'), ('nan_minus', 'float -> float -> nan_of'),
        ('nan_opp', 'float -> nan_of'), ('nan_abs', 'float -> nan_of'),
        ('nan_fma', 'float -> float -> float -> nan_of'), ('nan_mult', 'float -> float -> nan_of'),
        ('nan_const', 'nan_of'))]
    lines += ['', 'Local Notation pzero := (IeeeOperations.pzero prec emax).']
    for fd in folds:
        step, combine, finish = _fold_parts(fd, kernels)
        st, el, xs = rocq._fold_binders(fd)
        n = len(fd.state_limbs())
        stype = rocq.state_type(fd, 'float')
        etype = _fold_element_ftype(fd)
        lt = f'list ({etype})' if ' ' in etype else f'list {etype}'
        zero = rocq.state_zero(fd, 'pzero', 'true')
        groups = rocq.fold_groups(fd, el)
        state = rocq.state_groups(fd, st)
        sizes = {g.name: len(g.limbs) for g in fd.arrays}
        args = []
        for a in fd.step[1]:
            args += state[a] if a in state else rocq.tuple_parts(groups[a], sizes[a])
        rtype = ' * '.join(rocq.state_type(fd, 'float').split(' * ') if finish is None else
                           [('bool' if g.kind == ir.MASK else 'float') for g in finish.outputs for _ in g.limbs])
        lines += ['', f'(* {fd.name}: step {step.name}' + (f', combination {combine.name}' if combine else '') +
                  (f', finish {finish.name}' if finish else '') + '. *)',
                  f'Definition {fd.name}_step ({st} : {stype}) ({el} : {etype}) : {stype} :=',
                  f'  {_kernel_call(step, kernels, args)}.']
        if combine is not None:
            lines += ['', f'Definition {fd.name}_combine (a b : {stype}) : {stype} :=',
                      f'  {_kernel_call(combine, kernels, rocq.tuple_parts("a", n) + rocq.tuple_parts("b", n))}.']

        def result(fold):
            if finish is None:
                return [f'  {fold}.']
            return [f'  let s := {fold} in', f'  {_kernel_call(finish, kernels, rocq.tuple_parts("s", n))}.']
        if 'sequential' in fd.orders:
            lines += ['', f'Definition {fd.name}_seq ({xs} : {lt}) : {rtype} :='] + \
                result(f'fold_seq {fd.name}_step {zero} {xs}')
        if 'lanes' in fd.orders:
            lines += ['', f'Definition {fd.name}_lanes (W : nat) ({xs} : {lt}) : {rtype} :='] + \
                result(f'fold_lanes {fd.name}_step {fd.name}_combine {zero} W {xs}')
    lines += ['', 'End IeeeFolds.']
    return '\n'.join(lines) + '\n'


def _fold_nans(fd, kernels, order):
    step, combine, finish = _fold_parts(fd, kernels)
    used = set()
    for k in [step, finish] + ([combine] if order == 'lanes' else []):
        if k is not None:
            used.update(_used_nans(k, kernels))
    return [n for n, _ in NANS if n in used]


def fold_statement(fd, kernels, order):
    """F_seq_ieee_spec or F_lanes_ieee_spec: for every list of elements, with the requirements of
    the fold (canonical_2 of an array of two limbs; any value, for one limb), and (r, flag) the
    result: if flag is true, every limb of every element is finite, every limb of the result is,
    the values of the result are those of the real model of the fold (FoldModel.v) on the values
    of the elements, and these are valid and within the bound of the fold's claims; if it is false,
    every limb of the result is a NaN (milestone2.md, "When something is not finite")."""
    st, el, xs = rocq._fold_binders(fd)
    suffix = ir.ORDER_SUFFIX[order]
    step, combine, _ = _fold_parts(fd, kernels)
    nans = _fold_nans(fd, kernels, order)
    etype = _fold_element_ftype(fd).replace('float', 'binary_float prec emax')
    lt = f'list ({etype})'
    groups = rocq.fold_groups(fd, el)
    sizes = {g.name: len(g.limbs) for g in fd.arrays}
    canonical = {r[1] for r in fd.requires if r[0] == 'canonical'}
    hyps = []
    for g in fd.arrays:
        if g.name in canonical:
            limbs = rocq.tuple_parts(groups[g.name], sizes[g.name])
            hyps.append(f'canonical_2 {" ".join(rocq._paren(x) for x in limbs)}')
    finite = [f'finite {rocq._paren(x)}' for g in fd.arrays for x in rocq.tuple_parts(groups[g.name], sizes[g.name])]
    values = []
    for g in fd.arrays:
        parts = [f'val {rocq._paren(x)}' for x in rocq.tuple_parts(groups[g.name], sizes[g.name])]
        values.append(parts[0] if len(parts) == 1 else '(' + ', '.join(parts) + ')')
    value = values[0] if len(values) == 1 else '(' + ', '.join(values) + ')'
    results = [v for g in fd.results() for v in g.limbs]
    limbs = [v for g in fd.results() if g.kind == ir.LIMB for v in g.limbs]
    flags = [v for g in fd.results() if g.kind == ir.MASK for v in g.limbs]
    flag = flags[0]
    pattern = results[0] if len(results) == 1 else "'(" + ', '.join(results) + ')'
    parts = [step] + ([combine] if order == 'lanes' else [])
    section = [{'emin': EMIN, 'prec': 'prec', 'choice': 'tie_even'}[v] for v in rocq.fold_section_args(parts, kernels)]
    real = ' '.join([f'FoldModel.{fd.name}_{suffix}'] + section + (['W'] if order == 'lanes' else []) + ['vs'])
    vals = f'val {limbs[0]}' if len(limbs) == 1 else '(' + ', '.join(f'val {v}' for v in limbs) + ')'
    if fd.is_max:
        # A fold of maxima: the result is the limb of the final state stepped up as the finish
        # does (rocq.max_result), and its claims are those of rocq.max_conclusion.
        lets, claims = rocq.max_conclusion(fd, rocq.max_result(fd, 's', EMIN), el, 'vs', EMIN)
        middle = [f'   {x}' for x in lets] + [f'   {vals} = r_ /\\']
    else:
        claims = [re.sub(r'\bemin\b', EMIN, c) for c in rocq.fold_conclusion(fd, 's', el, 'vs', indent='      ')]
        middle = [f'   {vals} = s /\\']
    binders = f'forall (W : nat) ({xs} : {lt}),' if order == 'lanes' else f'forall {xs} : {lt},'
    call = ' '.join([f'IeeeFoldModel.{fd.name}_{suffix}', 'prec', 'emax'] + nans +
                    (['W'] if order == 'lanes' else []) + [xs])
    what = {'sequential': 'the sequential order', 'lanes': 'the lane order, for every number of lanes W'}[order]
    lines = [f'(* {fd.name}, {what}, in the IEEE model. Status: {"proved" if fd.ieee_theorem else "unverified"}. *)',
             f'Definition {fd.name}_{suffix}_ieee_spec : Prop :=',
             '  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)',
             '         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)' +
             (f'\n         {_binders(nans)},' if nans else ','),
             f'  ({fd.min_precision} <= prec)%Z ->',
             f'  {binders}']
    if hyps:
        lines.append(f'  Forall (fun {el} => {" /\\ ".join(hyps)}) {xs} ->')
    lines += [f'  let {pattern} := {call} in',
              f'  ({flag} = true ->',
              f'   Forall (fun {el} => {" /\\ ".join(finite)}) {xs} /\\',
              '   ' + ' /\\ '.join(f'finite {v}' for v in limbs) + ' /\\',
              f'   let vs := map (fun {el} => {value}) {xs} in',
              f'   let s := {real} in'] + middle + [
              '   ' + ' /\\\n   '.join(claims) + ') /\\',
              f'  ({flag} = false -> ' + ' /\\ '.join(f'nan {v}' for v in limbs) + ').']
    return lines


# The kernels that are the steps or the combinations of the folds: each has a statement that its
# result's leading limb is finite only if that of each of its operands is (lead_statement). Not
# those of a fold of maxima, whose maximum keeps a finite state when the element is a NaN (the
# mask of its state says so instead): the statement would be false of them.
def lead_kernels(kernels):
    names = set()
    for fd in getattr(kernels, 'folds', {}).values():
        if getattr(fd, 'is_map', False) or getattr(fd, 'is_max', False) or getattr(fd, 'is_conv', False):
            continue
        names.add(fd.step[0])
        if fd.combine:
            names.add(fd.combine[0])
    return [k for k in in_model(kernels).values() if k.name in names]


def lead_statement(k, kernels):
    """K_ieee_lead_spec: if limb 0 of the output is finite, so is limb 0 of every operand. This is
    the non-finite cone of rules.py (every limb reaches output limb 0 through operations that keep a
    value that is not finite so) as a statement, for the kernels whose results a fold carries."""
    out = k.outputs[0].limbs[0]
    leads = [g.limbs[0] for g in k.inputs if g.kind == ir.LIMB]
    lines = _head(k, _used_nans(k, kernels), precision=False) + [_let(k, kernels)]
    lines.append(f'  finite {out} -> ' + ' /\\ '.join(f'finite {v}' for v in leads) + '.')
    status = ' IEEE-model status: proved.' if k.ieee_lead_theorem else ''
    return _statement(f'{k.name}_ieee_lead_spec', f'{k.name}, the leading limb of its result: finite only if those of '
                      f'its operands are.{status}', lines)


def fold_statements(kernels):
    lines = [HEADER, '',
             '(* The statements of the folds in the IEEE model (IeeeFoldModel.v), one per fold and order: for',
             '   every precision from the fold\'s minimum on, every emax with prec < emax and every choice of',
             '   the NaN each operation returns, with rounding to nearest, ties to even; emin = 3 - emax - prec',
             '   (docs/developer/design/milestone2.md, "When something is not finite"). And, for each kernel',
             '   that is the step or the combination of a fold, that the leading limb of its result is finite',
             '   only if those of its operands are. A hand-written proof of statement S is a theorem whose type',
             '   is exactly S. *)',
             'From Stdlib Require Import Reals ZArith List.',
             'From Flocq Require Import Core Binary.',
             f'From {GEN_PATH} Require Import Model Statements FoldModel.',
             f'From {THEORIES_PATH} Require Import IeeeVocabulary Folds Summation.',
             f'From {THEORIES_PATH} Require IeeeOperations.',
             f'From {GEN_PATH} Require IeeeModel IeeeFoldModel.',
             'Open Scope R_scope.']
    for k in lead_kernels(kernels):
        lines += [''] + lead_statement(k, kernels)
    for fd in getattr(kernels, 'folds', {}).values():
        if getattr(fd, 'is_map', False) or getattr(fd, 'is_conv', False):
            continue
        for order in ir.ORDERS:
            if order in fd.orders:
                lines += [''] + fold_statement(fd, kernels, order)
    return '\n'.join(lines) + '\n'
