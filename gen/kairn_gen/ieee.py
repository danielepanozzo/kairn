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

def _const_names(kernels, real, every=None):
    """{constant name: the name of its definition}, the same in Model.v and here (inf, nan and 0
    are not here). Each is defined here from its definition in Model.v, which has the constants of
    the kernels with a real-model statement (`real`). A constant up(EXPR) that only kernels without
    one use (Milestone 2: the halves of a ball made from an interval) is defined here from its
    expression (_real_constant); any other such constant is refused."""
    ups = rocq.up_names(every if every is not None else kernels)
    in_model = {a.name for k in real.values() for st in k.body for a in st.args if a.const}
    out = {}
    for k in kernels.values():
        for st in k.body:
            for a in st.args:
                if a.const and a.name not in (ir.ZERO,) + ir.SPECIAL:
                    if a.name not in in_model and ir.up(a.name) is None:
                        raise PrintError(f'kernel {k.name}: const {a.name} is not in the real model, '
                                         'from which the IEEE model takes its value')
                    out[a.name] = rocq._const_name(a.name, ups)
    return out, in_model


def _real_constant(name, rname, in_model, kernels):
    """The real-model term of a constant, at the emin and prec of the IEEE format: the arguments
    of its closed definition in Model.v (prec alone for those of ir.CONSTANTS); for a constant
    up(EXPR) that Model.v has not, EXPR rounded up as Model.v would define it."""
    if name in ir.CONSTANTS:
        return f'Model.{rname} prec'
    if name in in_model:
        return f'Model.{rname} (3 - emax - prec) prec'
    term = rocq.up_term(name, kernels, 'bpow radix2 (- prec)', 'bpow radix2 (3 - emax - prec)')
    return f'round radix2 (FLT_exp (3 - emax - prec) prec) Zceil {rocq._paren(term)}'


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
    every = kernels
    kernels = in_model(kernels)
    cnames, defined = _const_names(kernels, real, every)
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
                  f'Definition {rname} : float := const_of ({_real_constant(name, rname, defined, every)}).']
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
    value = t.value() if k.value is not None else None     # the bound kernels have none
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
                # A one-limb input's value is an application, `val a`: in parentheses under Rabs.
                rho = '(' + ' + '.join(f'Rabs {_paren(_val_sum(g.limbs))}' for g in k.inputs) + ')'
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
        if 'exact_flag' in e:
            bound += f' /\\\n  ({e["exact_flag"]} = true <-> {t.exact_condition(e["exact_when"])})'
        return bound
    if kind == 'rounded' and 'when' not in e:
        # The rounding of the kernel's value, or of a value of its own over the inputs and their
        # limbs (the accumulator's sum of magnitudes), as in the real model.
        rounding = {'nearest': 'RN', 'down': 'RD', 'up': 'RU'}[e['mode']]
        if 'value' in e:
            value = _paren(rocq._term(expr.parse(e['value']), t.name,
                                      limb=lambda g, i: f'val {t.ins[g].limbs[i]}'))
        return f'val {outs[e["of"]][0]} = {rounding} {EMIN} prec {value}'
    if kind == 'upper' and ('unless' in e or 'exact_when' in e):
        raise PrintError(f'kernel {k.name}: no IEEE reading of an upper entry with unless= or exact_when= yet')
    if kind == 'upper' and 'value' in e and 'gaps' not in e:
        # The bound kernels' own value, under its mask when it has one, as in the real model.
        claim = f'{_paren(_constant_term(e["value"], k, t))} <= val {outs[e["of"]][0]}'
        return f'({e["if"]} = true -> {claim})' if 'if' in e else claim
    if kind == 'holds':
        a, b = (_constant_term(x, k, t) for x in e['args'])
        return f'({e["if"]} = true -> {a} {({"lt": "<", "le": "<=", "eq": "="})[e["rel"]]} {b})'
    raise PrintError(f'kernel {k.name}: no IEEE reading of {kind}')


def _constant_term(text, k, t):
    """An expression of the claims of Milestone 2 over the IEEE model: the values of the inputs, u
    and eta at the IEEE format's emin; no unit(K) or tiny(K) (none is needed yet)."""
    def name(n):
        if n == 'u':
            return 'u prec'
        if n == 'eta':
            return f'eta {EMIN}'
        return t.name(n)

    def call(fn, kname):
        raise PrintError(f'kernel {k.name}: {fn}({kname}) has no IEEE reading yet')
    return rocq._term(expr.parse(text), name, call)


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
        elif r[0] == 'count':
            lines.append(f'  (val {r[1]} = 0 \\/ 1 <= val {r[1]}) ->')
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
    outs = {g.name: g.limbs for g in k.outputs}
    first = k.outputs[0].name
    # Entries about an output group other than the first hold where that group's leading limb is
    # finite (architecture.md, "An output group other than the first"): the accumulator's sum of
    # magnitudes. A kernel without them has the statement it had: every claim under output limb 0.
    own = [g for g in k.outputs[1:] if g.kind == ir.LIMB and any(e.get('of') == g.name for e in k.ensures)]
    if not own:
        lines.append(f'  finite {out[0]} ->')
        claims = [f'finite {v}' for v, kind in zip(k.output_limbs, k.output_kinds) if kind == ir.LIMB][1:]
        claims += [_claim(e, k, t, outs) for e in k.ensures]
        lines.append('  ' + ' /\\\n  '.join(claims) + '.')
        return _statement(f'{k.name}_ieee_spec', _comment(k, k.ieee_spec_theorem), lines)
    mine = {g.name for g in own}
    parts = []
    for g in [k.outputs[0]] + own:
        claims = [f'finite {v}' for v in g.limbs[1:]]
        if g.name == first:
            claims += [f'finite {v}' for h in k.outputs[1:] if h.kind == ir.LIMB and h.name not in mine
                       for v in h.limbs]
        claims += [_claim(e, k, t, outs) for e in k.ensures
                   if (e.get('of') == g.name) or (g.name == first and e.get('of') not in mine)]
        parts.append(f'  (finite {g.limbs[0]} ->\n   ' + ' /\\\n   '.join(claims) + ')')
    lines.append(' /\\\n'.join(parts) + '.')
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
        elif r[0] == 'interval':
            lo, hi = t.ins[r[1]].limbs, t.ins[r[2]].limbs
            lines.append(f'  interval_{len(lo)} {" ".join(lo + hi)} ->')
        elif r[0] == 'not_nan':
            # A canonical value of several limbs is a NaN exactly when its leading limb is.
            lines.append(f'  ~ nan {t.ins[r[1]].limbs[0]} ->')
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
    # The empty set for a negative radius, -infinity included; the whole line for a radius that is
    # a NaN or +infinity, or a center that is not finite (a NaN radius: the owner's decision of
    # 2026-11-20, as for a NaN bound given to an interval); otherwise the ball given.
    lines += [f'  ball_{n} {out} /\\',
              f'  ({r_in} = infinity prec emax true \\/ (finite {r_in} /\\ val {r_in} < 0) -> '
              f'ball_empty_{n} {out}) /\\',
              f'  (finite {r_in} -> 0 <= val {r_in} -> finite {c_in[0]} ->\n'
              f'   ball_finite_{n} {out} /\\ {same} /\\ val {r_out} = val {r_in}) /\\',
              f'  (nan {r_in} \\/ {r_in} = infinity prec emax false \\/ (finite {r_in} /\\ 0 <= val {r_in} /\\ '
              f'~ finite {c_in[0]}) -> ball_whole_{n} {out}).']
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
    if e.get('nonneg'):
        # The finish of a constructor of a BallVector: the value is also not negative.
        finite = f'{finite} /\\ 0 <= val {src[0]}'
    if 'if' in e:
        finite = f'{e["if"]} = true /\\ {finite}'
    lines += [f'  ({flag} = true <-> {finite}) /\\',
              f'  ({flag} = true -> ' + ' /\\ '.join(f'{o} = {i}' for o, i in zip(out, src)) + ') /\\',
              f'  ({flag} = false -> ' + ' /\\ '.join(f'nan {o}' for o in out) + ').']
    return _statement(f'{k.name}_spec', _comment(k), lines)


# ---------------------------------------------------------------------------------------------
# Intervals and the bounds of a set (Milestone 2), in the vocabulary of
# proofs/theories/IeeeIntervalVocabulary.v and in the shapes of the theorems of IeeeInterval1.v.

def _interval_precision(k):
    """A statement about intervals has a hypothesis on the precision only when its kernel has a
    minimum above 1: the theorems of interval_make_1, interval_neg_1 and interval_mul_1 are for
    every precision and have none."""
    return (k.min_precision or 1) > 1


def _strip(term):
    """A term without its outer parentheses (the body of a fun, as the theorems write it)."""
    if term.startswith('(') and term.endswith(')'):
        depth = 0
        for i, ch in enumerate(term):
            depth += {'(': 1, ')': -1}.get(ch, 0)
            if depth == 0 and i < len(term) - 1:
                return term
        return term[1:-1]
    return term


def _set_of(k, e, groups, member):
    """The set of an interval or ball claim as a predicate on R: the members of one operand when
    the set is its name, otherwise range_1 or range_2 (IeeeIntervalVocabulary.v) of the operation
    over the operands' members. `groups` maps each name of the claim to its limbs, `member` gives
    the membership predicate of a name, partially applied."""
    tree = expr.parse(e['set'])
    names = list(groups)
    if tree[0] == 'name':
        return f'({member(tree[1])})'
    used = [n for n in names if n in expr.names(tree)]
    if len(used) not in (1, 2):
        raise PrintError(f'kernel {k.name}: a set over {len(used)} names has no range_N in the vocabulary')
    body = _strip(rocq._term(tree, lambda n: n))
    return (f'(range_{len(used)} (fun {" ".join(used)} : R => {body}) '
            + ' '.join(f'({member(n)})' for n in used) + ')')


def _interval_bounds(k, e, t):
    """The limbs of the result and of each interval of the claim, and their word size N."""
    lo, hi = t.outs[e['lower']].limbs, t.outs[e['upper']].limbs
    n = len(_limbs(k, lo, e['lower'], (1, 2)))
    groups = {name: t.ins[b['lower']].limbs + t.ins[b['upper']].limbs for name, b in e['intervals'].items()}
    return lo, hi, n, groups


def _xv(limbs):
    return f'xval_2 {" ".join(limbs)}' if len(limbs) == 2 else f'xval {limbs[0]}'


def _product_large(a, b):
    """The condition product_large of two bounds of one limb, as the theorems of IeeeInterval1.v
    state it (its definition product_large there, unfolded): for finite bounds, their product is
    zero or at least 2^(2 prec - 1) eta in magnitude."""
    return (f'(finite {a} /\\ finite {b} ->\n    val {a} * val {b} = 0 \\/ bpow radix2 (2 * prec - 1) * eta {EMIN} '
            f'<= Rabs (val {a} * val {b}))')


def _interval_spec(k, kernels, e):
    """I1 to I5 of milestone2.md, "What is stated of an interval kernel", for canonical operands, in
    the shapes of the theorems of IeeeInterval1.v (interval_add_1_correct, and for a tightness
    of steps, interval_mul_1_tight_range)."""
    t = _Terms(k)
    nans = _used_nans(k, kernels)
    lines = _head(k, nans, precision=_interval_precision(k)) + _hyps_extended(k, t) + [_let(k, kernels)]
    zlo, zhi, n, groups = _interval_bounds(k, e, t)
    z = ' '.join(zlo + zhi)

    def member(name):
        return f'in_interval_{n} {" ".join(groups[name])}'
    names = list(groups)
    S = _set_of(k, e, groups, member)
    tree = expr.parse(e['set'])
    empties = ' \\/ '.join(f'interval_empty_{n} {" ".join(groups[x])}' for x in names)
    claims = [f'interval_{n} {z}', f'(interval_empty_{n} {z} <-> {empties})']
    target = rocq._term(tree, lambda x: x)
    claims.append(f'(forall {" ".join(names)} : R, ' + ' '.join(f'{member(x)} {x} ->' for x in names) +
                  f'\n   in_interval_{n} {z} {target})')
    nonempty = ' '.join(f'interval_nonempty_{n} {" ".join(groups[x])} ->' for x in names)
    bounded = ' '.join(f'interval_bounded_{n} {" ".join(groups[x])} ->' for x in names)
    ranges = f'range_lower {S} lo ->\n   range_upper {S} hi ->'
    tight = e['tight']
    if tight['kind'] in ('rounded', 'exact'):
        if tight['kind'] == 'exact':
            body = f'{_xv(zlo)} = lo /\\ {_xv(zhi)} = hi'
        else:
            down, up = 'xrd prec emax lo', 'xru prec emax hi'
            exact = f'{_xv(zlo)} = {down} /\\ {_xv(zhi)} = {up}'
            steps = tight.get('steps', 0)
            parts = []
            if steps:
                ld, hu = down, up
                for _ in range(steps):
                    ld, hu = f'xpred prec emax ({ld})', f'xsucc prec emax ({hu})'
                parts += [f'xle ({ld}) ({_xv(zlo)}) = true', f'xle ({_xv(zlo)}) ({down}) = true',
                          f'xle ({up}) ({_xv(zhi)}) = true', f'xle ({_xv(zhi)}) ({hu}) = true']
            if tight.get('when') == 'product_large':
                a, b = (groups[x[1]] for x in tree[1:])
                pairs = [(a[0], b[0]), (a[0], b[1]), (a[1], b[0]), (a[1], b[1])]
                parts.append('(' + ' ->\n   '.join(_product_large(p, q) for p, q in pairs) + f' ->\n   {exact})')
            elif not steps:
                parts.append(exact)
            body = ' /\\\n   '.join(parts)
        claims.append(f'({nonempty}\n   forall lo hi : xreal,\n   {ranges}\n   {body})')
    else:
        # The outward tightness (two limbs): for bounded operands, each finite bound of the exact range
        # within rel |v| + abs of the bound of the result, when the result is bounded; that bound
        # itself under the conditions of exact_when (zero, for the sums); and an infinite bound of the
        # exact range returned as that infinity.
        rel = rocq.claim_constant_term(tight['rel'], kernels, EMIN)
        absolute = rocq.claim_constant_term(tight['abs'], kernels, EMIN)
        vl, vh = _val_sum(zlo), _val_sum(zhi)
        inner = [f'(interval_bounded_{n} {z} ->\n    lo - {vl} <= {rel} * Rabs lo + {absolute} /\\\n'
                 f'    {vh} - hi <= {rel} * Rabs hi + {absolute})']
        for side, var, limbs in (('lower', 'lo', zlo), ('upper', 'hi', zhi)):
            conds = tight.get('exact_when', {}).get(side)
            if conds:
                inner.append(f'({t.exact_condition(conds)} -> {_xv(limbs)} = XFin {var})')
        claims.append(f'({bounded}\n   forall lo hi : R,\n   range_lower {S} (XFin lo) ->\n'
                      f'   range_upper {S} (XFin hi) ->\n   ' + ' /\\\n   '.join(inner) + ')')
        claims.append(f'({nonempty}\n   (range_lower {S} (XInf true) -> {_xv(zlo)} = XInf true) /\\\n'
                      f'   (range_upper {S} (XInf false) -> {_xv(zhi)} = XInf false))')
    if e.get('zero_factor'):
        zero = ' \\/\n   '.join('(' + ' /\\ '.join(f'zero {groups[x][i]}' for i in (0, n)) + ')' for x in names)
        claims.append(f'({nonempty}\n   {zero} ->\n   ' + ' /\\ '.join(f'zero {v}' for v in zlo + zhi) + ')')
    conds = []
    for c in e['bounded_when']:
        limit = 'omega prec emax' if c.get('omega') else \
            'bpow radix2 ' + ('emax' if c['exp'] == 0 else f'(emax {"-" if c["exp"] < 0 else "+"} {abs(c["exp"])})')
        conds.append(f'forall z : R,\n    {_strip(S)} z ->\n    Rabs z <= {limit}')
    if conds:
        if e.get('bounded_exactly'):
            conds_text = ' /\\\n    '.join(conds if len(conds) == 1 else [f'({c})' for c in conds])
            claims.append(f'({bounded}\n   (interval_bounded_{n} {z} <->\n    {conds_text}))')
        else:
            claims.append(f'({bounded}\n   ' + ' ->\n   '.join(f'({c})' for c in conds) +
                          f' ->\n   interval_bounded_{n} {z})')
    lines.append('  ' + ' /\\\n  '.join(claims) + '.')
    return _statement(f'{k.name}_spec', _comment(k), lines)


def _same_infinity(lo, hi):
    """Both given bounds are the same infinity, [+inf, +inf] or [-inf, -inf], as extended real
    numbers (a canonical 2-limb value stands for an infinity exactly when its leading limb is one)."""
    return f'(exists s : bool, {_xv(lo)} = XInf s /\\ {_xv(hi)} = XInf s)'


def _makes_interval_spec(k, kernels, e):
    """The constructor of an interval (milestone2.md, "Values of an interval"), in the shape of
    interval_make_1_correct: the result is canonical; the whole line when a bound is a NaN or both
    are the same infinity (the owner's decision of 2026-11-20: a value from the program that is not
    finite never makes the empty set); the empty set when the bounds are reversed, lo > hi as
    extended real numbers; the interval of the given bounds when they describe a nonempty one. The
    three conditions are disjoint and cover every pair of values."""
    t = _Terms(k)
    lines = _head(k, _used_nans(k, kernels), precision=_interval_precision(k)) + _hyps_extended(k, t) + \
        [_let(k, kernels)]
    zl, zu = _limbs(k, t.outs[e['lower']].limbs, e['lower'], (1, 2)), t.outs[e['upper']].limbs
    n = len(zl)
    lo, hi = t.ins[e['from']['lower']].limbs, t.ins[e['from']['upper']].limbs
    nonempty = f'xnonempty ({_xv(lo)}) ({_xv(hi)})'
    z = ' '.join(zl + zu)
    # For two limbs an infinite bound is followed by a zero: the second limbs of the whole line.
    zeros = ''.join(f' /\\ zero {v}' for v in (zl[1:], zu[1:]) for v in v)
    whole = (f'{zl[0]} = infinity prec emax true /\\ {zu[0]} = infinity prec emax false' if n == 1 else
             f'{zl[0]} = infinity prec emax true /\\ {zu[0]} = infinity prec emax false{zeros}')
    claims = [f'interval_{n} {z}',
              f'({nonempty} -> {_xv(zl)} = {_xv(lo)} /\\ {_xv(zu)} = {_xv(hi)})',
              f'(nan {lo[0]} \\/ nan {hi[0]} \\/ {_same_infinity(lo, hi)} ->\n   {whole})',
              f'(xlt ({_xv(hi)}) ({_xv(lo)}) = true -> interval_empty_{n} {z})']
    lines.append('  ' + ' /\\\n  '.join(claims) + '.')
    return _statement(f'{k.name}_spec', _comment(k), lines)


def _makes_ball_interval_spec(k, kernels, e):
    """A ball from the bounds of an interval (milestone2.md, "A ball from an interval of two T"):
    canonical; for finite lo <= hi a finite ball that contains [lo, hi], with the exact midpoint
    for center and the radius rounded up when the conditions of midpoint_when hold; the whole line
    for an interval that is not empty with an infinite bound, for a NaN bound and for two bounds
    that are the same infinity (the owner's decision of 2026-11-20, as for makes_interval); the
    empty set for reversed bounds, lo > hi as extended real numbers."""
    t = _Terms(k)
    lines = _head(k, _used_nans(k, kernels)) + _hyps_extended(k, t) + [_let(k, kernels)]
    c_out, r_out = _limbs(k, t.outs[e['center']].limbs, e['center'], (1, 2)), e['radius']
    n = len(c_out)
    out = _ball_args(c_out, r_out)
    lo, hi = e['from']['lower'], e['from']['upper']
    nonempty = f'xnonempty (xval {lo}) (xval {hi})'
    claims = [f'ball_{n} {out}',
              f'({nonempty} -> finite {lo} -> finite {hi} ->\n   ball_finite_{n} {out} /\\\n'
              f'   (forall x : R, val {lo} <= x <= val {hi} -> in_ball_{n} {out} x))']
    conds = e.get('midpoint_when', [])
    if conds:
        halves = ' -> '.join(f'fmt {EMIN} prec (val {c["half_in_format"]} / 2)' for c in conds)
        claims.append(f'({nonempty} -> finite {lo} -> finite {hi} -> {halves} ->\n'
                      f'   {_val_sum(c_out)} = (val {lo} + val {hi}) / 2 /\\\n'
                      f'   val {r_out} = RU {EMIN} prec ((val {hi} - val {lo}) / 2))')
    if 'rel' in e:
        # Stage B2 (ball_from_interval_1): the center near the midpoint, and the smallest radius.
        vc, mid = _val_sum(c_out), f'(val {lo} + val {hi}) / 2'
        rel = rocq.claim_constant_term(e['rel'], kernels, EMIN)
        absolute = rocq.claim_constant_term(e['abs'], kernels, EMIN)
        near = [f'val {lo} <= {vc} <= val {hi}', f'Rabs ({vc} - {mid}) <= {rel} * Rabs ({mid}) + {absolute}']
        if e.get('smallest_radius'):
            near.append(f'val {r_out} = RU {EMIN} prec (Rmax ({vc} - val {lo}) (val {hi} - {vc}))')
        claims.append(f'({nonempty} -> finite {lo} -> finite {hi} ->\n   ' + ' /\\\n   '.join(near) + ')')
    claims += [f'({nonempty} -> ~ (finite {lo} /\\ finite {hi}) -> ball_whole_{n} {out})',
               f'(nan {lo} \\/ nan {hi} \\/ {_same_infinity([lo], [hi])} ->\n   ball_whole_{n} {out})',
               f'(xlt (xval {hi}) (xval {lo}) = true -> ball_empty_{n} {out})']
    lines.append('  ' + ' /\\\n  '.join(claims) + '.')
    return _statement(f'{k.name}_spec', _comment(k), lines)


def _interval_set_spec(k, kernels, e):
    """The hull or the intersection of two intervals (Milestone 2, "One enclosure interface"):
    canonical; empty exactly when the set operation's rule says (union: when both operands are;
    intersection: when no real number is a member of both); the members of the set are members of
    the result; and a nonempty result has the bounds of the set, as extended real numbers."""
    t = _Terms(k)
    lines = _head(k, _used_nans(k, kernels), precision=_interval_precision(k)) + _hyps_extended(k, t) + \
        [_let(k, kernels)]
    zlo, zhi, n, groups = _interval_bounds(k, e, t)
    z = ' '.join(zlo + zhi)
    names = list(groups)
    ins = [f'in_interval_{n} {" ".join(groups[x])} z' for x in names]
    union = e['set'] == 'union'
    S = '(fun z : R => ' + (' \\/ ' if union else ' /\\ ').join(ins) + ')'
    both = ' /\\ '.join(ins)
    empty = (' /\\ '.join(f'interval_empty_{n} {" ".join(groups[x])}' for x in names) if union else
             f'~ (exists z : R, {both})')
    claims = [f'interval_{n} {z}',
              f'(interval_empty_{n} {z} <-> {empty})',
              f'(forall z : R, {_strip(S)[len("fun z : R => "):]} -> in_interval_{n} {z} z)',
              f'(~ interval_empty_{n} {z} ->\n   forall lo hi : xreal,\n   range_lower {S} lo ->\n'
              f'   range_upper {S} hi ->\n   {_xv(zlo)} = lo /\\ {_xv(zhi)} = hi)']
    lines.append('  ' + ' /\\\n  '.join(claims) + '.')
    return _statement(f'{k.name}_spec', _comment(k), lines)


def _ball_of_interval_spec(k, kernels, e):
    """A ball made from an interval (Milestone 2, "Midpoint, radius and the conversions"): for a
    bounded interval, a finite center between the bounds and within rel |mid| + abs of the midpoint
    mid, a finite radius with which it contains the interval, and with smallest_radius the smallest
    such radius of the format, RU of the larger distance to a bound; the special values of IEEE
    1788's mid and rad (ieee1788) or of a canonical ball (ball) for the other intervals."""
    t = _Terms(k)
    lines = _head(k, _used_nans(k, kernels), precision=_interval_precision(k)) + _hyps_extended(k, t) + \
        [_let(k, kernels)]
    c, r = _limbs(k, t.outs[e['center']].limbs, e['center'], (1, 2)), e['radius']
    lo, hi = t.ins[e['from']['lower']].limbs, t.ins[e['from']['upper']].limbs
    n = len(lo)
    x = ' '.join(lo + hi)
    vl, vh, vc = _val_sum(lo), _val_sum(hi), _val_sum(c)
    mid = f'({vl} + {vh}) / 2'
    rel = rocq.claim_constant_term(e['rel'], kernels, EMIN)
    absolute = rocq.claim_constant_term(e['abs'], kernels, EMIN)
    bounded = [f'{vl} <= {vc} <= {vh}',
               f'Rabs ({vc} - {mid}) <= {rel} * Rabs ({mid}) + {absolute}',
               f'(forall z : R, in_interval_{n} {x} z -> Rabs (z - {vc}) <= val {r})']
    if 'finite_when' in e:
        return _ball_of_interval_finite_when(k, e, lines, c, r, lo, hi, n, x, bounded, mid, rel, absolute)
    if e.get('smallest_radius'):
        bounded.append(f'val {r} = RU {EMIN} prec (Rmax ({vc} - {vl}) ({vh} - {vc}))')
    finite = ' /\\ '.join(f'finite {v}' for v in list(c) + [r])
    claims = []
    if e['special'] == 'ball':
        b = _ball_args(c, r)
        claims += [f'ball_{len(c)} {b}',
                   f'(ball_empty_{len(c)} {b} <-> interval_empty_{n} {x})',
                   f'(interval_nonempty_{n} {x} -> ~ interval_bounded_{n} {x} -> ball_whole_{len(c)} {b})',
                   f'(interval_bounded_{n} {x} ->\n   ball_finite_{len(c)} {b} /\\\n   ' +
                   ' /\\\n   '.join(bounded) + ')']
    else:
        zero = ' /\\ '.join(f'zero {v}' for v in c)
        inf = f'{r} = infinity prec emax false'
        claims += [f'(interval_empty_{n} {x} -> ' + ' /\\ '.join(f'nan {v}' for v in list(c) + [r]) + ')',
                   f'({_xv(lo)} = XInf true -> {_xv(hi)} = XInf false -> {zero} /\\ {inf})',
                   f'(finite {lo[0]} -> {_xv(hi)} = XInf false -> {_xv(c)} = XFin (omega prec emax) /\\ {inf})',
                   f'({_xv(lo)} = XInf true -> finite {hi[0]} -> {_xv(c)} = XFin (- omega prec emax) /\\ {inf})',
                   f'(interval_bounded_{n} {x} ->\n   {finite} /\\\n   ' + ' /\\\n   '.join(bounded) + ')']
    lines.append('  ' + ' /\\\n  '.join(claims) + '.')
    return _statement(f'{k.name}_spec', _comment(k), lines)


def _ball_of_interval_finite_when(k, e, lines, c, r, lo, hi, n, x, bounded, mid, rel, absolute):
    """ball_of_interval with finite_when (stage B2, interval_mid_rad_2 and interval_to_ball_2): for a
    bounded interval the radius may be +infinity (a step past Omega near the top of the range), and
    is finite under the conditions. ieee1788: the center as without the field, and the radius +inf
    or a finite one with which the center contains the interval. ball: a canonical ball that contains
    the interval, and under the conditions a finite ball with the center and radius as without the
    field."""
    t = _Terms(k)
    conds = ' -> '.join(_condition(cond, t) for cond in e['finite_when'])
    vc = _val_sum(c)
    contains = f'(forall z : R, in_interval_{n} {x} z -> Rabs (z - {vc}) <= val {r})'
    claims = []
    if e['special'] == 'ball':
        b = _ball_args(c, r)
        claims += [f'ball_{len(c)} {b}',
                   f'(ball_empty_{len(c)} {b} <-> interval_empty_{n} {x})',
                   f'(interval_nonempty_{n} {x} -> ~ interval_bounded_{n} {x} -> ball_whole_{len(c)} {b})',
                   f'(interval_bounded_{n} {x} ->\n   forall z : R, in_interval_{n} {x} z -> in_ball_{len(c)} {b} z)',
                   f'(interval_bounded_{n} {x} -> {conds} ->\n   ball_finite_{len(c)} {b} /\\\n   ' +
                   ' /\\\n   '.join(bounded) + ')']
    else:
        zero = ' /\\ '.join(f'zero {v}' for v in c)
        inf = f'{r} = infinity prec emax false'
        finite = ' /\\ '.join(f'finite {v}' for v in c)
        claims += [f'(interval_empty_{n} {x} -> ' + ' /\\ '.join(f'nan {v}' for v in list(c) + [r]) + ')',
                   f'({_xv(lo)} = XInf true -> {_xv(hi)} = XInf false -> {zero} /\\ {inf})',
                   f'(finite {lo[0]} -> {_xv(hi)} = XInf false -> {_xv(c)} = XFin (omega prec emax) /\\ {inf})',
                   f'({_xv(lo)} = XInf true -> finite {hi[0]} -> {_xv(c)} = XFin (- omega prec emax) /\\ {inf})',
                   f'(interval_bounded_{n} {x} ->\n   {finite} /\\\n   ' + ' /\\\n   '.join(bounded[:2]) +
                   f' /\\\n   ({inf} \\/ (finite {r} /\\ {contains})) /\\\n   ({conds} -> finite {r}))']
    lines.append('  ' + ' /\\\n  '.join(claims) + '.')
    return _statement(f'{k.name}_spec', _comment(k), lines)


def _interval_of_ball_spec(k, kernels, e):
    """An interval that encloses a ball (Milestone 2, "Ball to interval"): canonical; empty
    exactly when the ball is; every value of the set, the ball name ranging over the members of its
    ball, is a member; and with tight=rounded, for a ball that is not empty, the bounds of the set
    rounded down and up in the format with overflow (stepped at most `steps` times beyond)."""
    t = _Terms(k)
    lines = _head(k, _used_nans(k, kernels), precision=_interval_precision(k)) + _hyps_extended(k, t) + \
        [_let(k, kernels)]
    if e['tight']['kind'] == 'outward':
        return _interval_of_ball_outward(k, kernels, e, t, lines)
    zl, zu = _limbs(k, t.outs[e['lower']].limbs, e['lower'], (1,)), _limbs(k, t.outs[e['upper']].limbs, e['upper'], (1,))
    z = ' '.join(zl + zu)
    groups = {b: t.ins[cr['center']].limbs + (cr['radius'],) for b, cr in e['balls'].items()}

    def member(name):
        return f'in_ball_{len(groups[name]) - 1} {" ".join(groups[name])}'
    S = _set_of(k, e, groups, member)
    names = list(groups)
    empty = ' \\/ '.join(f'ball_empty_{len(g) - 1} {" ".join(g)}' for g in groups.values())
    target = rocq._term(expr.parse(e['set']), lambda x: x)
    claims = [f'interval_1 {z}', f'(interval_empty_1 {z} <-> {empty})',
              f'(forall {" ".join(names)} : R, ' + ' '.join(f'{member(x)} {x} ->' for x in names) +
              f'\n   in_interval_1 {z} {target})']
    down, up = 'xrd prec emax lo', 'xru prec emax hi'
    steps = e['tight'].get('steps', 0)
    if steps:
        ld, hu = down, up
        for _ in range(steps):
            ld, hu = f'xpred prec emax ({ld})', f'xsucc prec emax ({hu})'
        body = (f'xle ({ld}) (xval {zl[0]}) = true /\\ xle (xval {zl[0]}) ({down}) = true /\\\n'
                f'   xle ({up}) (xval {zu[0]}) = true /\\ xle (xval {zu[0]}) ({hu}) = true')
    else:
        body = f'xval {zl[0]} = {down} /\\ xval {zu[0]} = {up}'
    claims.append(f'(~ ({empty}) ->\n   forall lo hi : xreal,\n   range_lower {S} lo ->\n   range_upper {S} hi ->\n'
                  f'   {body})')
    lines.append('  ' + ' /\\\n  '.join(claims) + '.')
    return _statement(f'{k.name}_spec', _comment(k), lines)


def _interval_of_ball_outward(k, kernels, e, t, lines):
    """An interval of two limbs that encloses a ball (stage B2, ball_to_interval_2): canonical; empty
    exactly when the ball is; every value of the set a member; for a finite ball and a bounded result,
    each bound within rel |v| + abs of the bound v of the set, outward; the exact bound when its
    condition holds; an infinite bound of the set returned as that infinity; bounded under the
    conditions of bounded_when."""
    zl, zu = _limbs(k, t.outs[e['lower']].limbs, e['lower'], (2,)), _limbs(k, t.outs[e['upper']].limbs, e['upper'], (2,))
    z = ' '.join(zl + zu)
    groups = {b: t.ins[cr['center']].limbs + (cr['radius'],) for b, cr in e['balls'].items()}

    def member(name):
        return f'in_ball_{len(groups[name]) - 1} {" ".join(groups[name])}'
    S = _set_of(k, e, groups, member)
    names = list(groups)
    empty = ' \\/ '.join(f'ball_empty_{len(g) - 1} {" ".join(g)}' for g in groups.values())
    finite = ' -> '.join(f'ball_finite_{len(g) - 1} {" ".join(g)}' for g in groups.values())
    target = rocq._term(expr.parse(e['set']), lambda x: x)
    tight = e['tight']
    rel = rocq.claim_constant_term(tight['rel'], kernels, EMIN)
    absolute = rocq.claim_constant_term(tight['abs'], kernels, EMIN)
    vl, vh = _val_sum(zl), _val_sum(zu)
    inner = [f'(interval_bounded_2 {z} ->\n    lo - {vl} <= {rel} * Rabs lo + {absolute} /\\\n'
             f'    {vh} - hi <= {rel} * Rabs hi + {absolute})']
    for side, var, limbs in (('lower', 'lo', zl), ('upper', 'hi', zu)):
        conds = tight.get('exact_when', {}).get(side)
        if conds:
            inner.append(f'({t.exact_condition(conds)} -> {_xv(limbs)} = XFin {var})')
    claims = [f'interval_2 {z}', f'(interval_empty_2 {z} <-> {empty})',
              f'(forall {" ".join(names)} : R, ' + ' '.join(f'{member(x)} {x} ->' for x in names) +
              f'\n   in_interval_2 {z} {target})',
              f'({finite} ->\n   forall lo hi : R,\n   range_lower {S} (XFin lo) ->\n'
              f'   range_upper {S} (XFin hi) ->\n   ' + ' /\\\n   '.join(inner) + ')',
              f'(~ ({empty}) ->\n   (range_lower {S} (XInf true) -> {_xv(zl)} = XInf true) /\\\n'
              f'   (range_upper {S} (XInf false) -> {_xv(zu)} = XInf false))']
    for c in e.get('bounded_when', []):
        limit = 'bpow radix2 ' + ('emax' if c['exp'] == 0 else f'(emax {"-" if c["exp"] < 0 else "+"} {abs(c["exp"])})')
        claims.append(f'({finite} ->\n   (forall z : R,\n    {_strip(S)} z ->\n    Rabs z <= {limit}) ->\n'
                      f'   interval_bounded_2 {z})')
    lines.append('  ' + ' /\\\n  '.join(claims) + '.')
    return _statement(f'{k.name}_spec', _comment(k), lines)


def _splits_spec(k, kernels, e):
    """Two intervals that together are the operand (Milestone 2, the split of an interval): both
    canonical; both empty when the operand is; otherwise both nonempty, the first from the
    operand's lower bound to a point, the second from that point to the operand's upper bound."""
    t = _Terms(k)
    lines = _head(k, _used_nans(k, kernels), precision=_interval_precision(k)) + _hyps_extended(k, t) + \
        [_let(k, kernels)]
    lo, hi = t.ins[e['from']['lower']].limbs, t.ins[e['from']['upper']].limbs
    n = len(lo)
    x = ' '.join(lo + hi)
    (al, au), (bl, bu) = ((t.outs[q['lower']].limbs, t.outs[q['upper']].limbs) for q in e['parts'])
    a, b = ' '.join(al + au), ' '.join(bl + bu)
    claims = [f'interval_{n} {a}', f'interval_{n} {b}',
              f'(interval_empty_{n} {x} -> interval_empty_{n} {a} /\\ interval_empty_{n} {b})',
              f'(interval_nonempty_{n} {x} ->\n   interval_nonempty_{n} {a} /\\ interval_nonempty_{n} {b} /\\\n'
              f'   {_xv(al)} = {_xv(lo)} /\\ {_xv(bu)} = {_xv(hi)} /\\ {_xv(au)} = {_xv(bl)})']
    lines.append('  ' + ' /\\\n  '.join(claims) + '.')
    return _statement(f'{k.name}_spec', _comment(k), lines)


class _Sets:
    """The sets of a certain or trit entry (Milestone 2, the enclosure interface) in the vocabulary
    of IeeeIntervalVocabulary.v and IeeeVocabulary.v: membership, nonempty, empty, the special
    states (the empty set and the whole line), a finite operand; and the relation as a proposition
    of the reals, and its negation of every choice of members."""

    REL = {'lt': '<', 'le': '<=', 'eq': '='}

    def __init__(self, k, e, t):
        self.k, self.e, self.t = k, e, t
        self.balls = 'balls' in e
        sets = e['balls'] if self.balls else e['intervals']
        if self.balls:
            self.groups = {x: t.ins[b['center']].limbs + (b['radius'],) for x, b in sets.items()}
            self.n = {x: len(g) - 1 for x, g in self.groups.items()}
        else:
            self.groups = {x: t.ins[b['lower']].limbs + t.ins[b['upper']].limbs for x, b in sets.items()}
            self.n = {x: len(g) // 2 for x, g in self.groups.items()}
        for x, n in self.n.items():
            _limbs(k, self.groups[x][:n], x, (1, 2))
        # Bound names of the propositions: none may be a name of the kernel's inputs.
        taken = set(k.input_limbs) | {g.name for g in k.inputs} | set(sets)
        if taken & {'z', 'w', 'd'}:
            raise PrintError(f'kernel {k.name}: z, w and d are bound in the statements of a predicate of sets')

    def args(self, x):
        return ' '.join(self.groups[x])

    def member(self, x, z):
        sort = 'ball' if self.balls else 'interval'
        return f'in_{sort}_{self.n[x]} {self.args(x)} {z}'

    def nonempty(self, x):
        n = self.n[x]
        return f'~ ball_empty_{n} {self.args(x)}' if self.balls else f'interval_nonempty_{n} {self.args(x)}'

    def empty(self, x):
        n = self.n[x]
        return f'ball_empty_{n} {self.args(x)}' if self.balls else f'interval_empty_{n} {self.args(x)}'

    def whole(self, x):
        n, g = self.n[x], self.groups[x]
        if self.balls:
            return f'ball_whole_{n} {self.args(x)}'
        return f'{_xv(g[:n])} = XInf true /\\ {_xv(g[n:])} = XInf false'

    def finite(self, x):
        n = self.n[x]
        return f'ball_finite_{n} {self.args(x)}' if self.balls else f'interval_bounded_{n} {self.args(x)}'

    def point(self):
        """The point of a membership: its limbs, and its value as a real."""
        p = self.t.ins[self.e['args'][0]].limbs
        return p, _val_sum(p)

    def special(self):
        """An operand that is not finite: a set that is the empty set or the whole line, a point
        that is not a finite number."""
        parts = [f'{self.empty(x)} \\/ {self.whole(x)}' for x in self.groups]
        if self.e['rel'] == 'member':
            parts.append(f'~ finite {self.point()[0][0]}')
        return ' \\/ '.join(parts)

    def all_finite(self):
        parts = [self.finite(x) for x in self.groups]
        if self.e['rel'] == 'member':
            parts.append(f'finite {self.point()[0][0]}')
        return ' /\\ '.join(parts)

    def holds(self, negated=False):
        """The relation as a proposition; with `negated` (the `no` of a trit), its failure for every
        choice of members: for lt, le, eq of nonempty sets, the negated relation of each pair; for
        member, that the point is not a member."""
        rel, args = self.e['rel'], self.e['args']
        if rel in self.REL:
            sets = [a for a in args if a != ir.ZERO]
            body = f'{args[0]} {self.REL[rel]} {args[1]}'
            if negated:
                body = f'~ ({body})'
            ne = ' /\\ '.join(self.nonempty(x) for x in sets)
            return (f'{ne} /\\\n    (forall {" ".join(sets)} : R, ' + ' '.join(f'{self.member(x, x)} ->' for x in sets) +
                    f' {body})')
        if rel == 'member':
            p, v = self.point()
            inside = f'finite {p[0]} /\\ {self.member(args[1], _paren(v))}'
            return f'~ ({inside})' if negated else inside
        if negated:
            raise PrintError(f'kernel {self.k.name}: {rel} has no three-valued reading')
        x = args[0]
        if rel == 'empty':
            return self.empty(x)
        if rel == 'entire':
            return f'(forall z : R, {self.member(x, "z")})'
        y = args[1]
        if rel == 'subset':
            return f'(forall z : R, {self.member(x, "z")} -> {self.member(y, "z")})'
        if rel == 'equal':
            return f'(forall z : R, {self.member(x, "z")} <-> {self.member(y, "z")})'
        if rel == 'interior':
            return (f'(forall z : R, {self.member(x, "z")} ->\n    exists d : R, 0 < d /\\ '
                    f'(forall w : R, Rabs (w - z) < d -> {self.member(y, "w")}))')
        if rel == 'disjoint':
            return f'~ (exists z : R, {self.member(x, "z")} /\\ {self.member(y, "z")})'
        raise PrintError(f'kernel {self.k.name}: no IEEE reading of the relation {rel}')


def _ball_set_spec(k, kernels, e):
    """A ball that contains the union or the intersection of two balls (Milestone 2, "Hull,
    intersection and split of balls"): canonical; every member of the set a member; for the union,
    empty exactly when both operands are, and an operand that is empty gives the other, limb for
    limb; for the intersection, an empty operand gives the empty set, and an operand that is the
    whole line gives the other, limb for limb."""
    t = _Terms(k)
    lines = _head(k, _used_nans(k, kernels), precision=_interval_precision(k)) + _hyps_extended(k, t) + \
        [_let(k, kernels)]
    c = _limbs(k, t.outs[e['center']].limbs, e['center'], (1, 2))
    n = len(c)
    z = _ball_args(c, e['radius'])
    groups = {x: (t.ins[b['center']].limbs, b['radius']) for x, b in e['balls'].items()}
    (x, (xc, xr)), (y, (yc, yr)) = groups.items()
    bx, by = _ball_args(xc, xr), _ball_args(yc, yr)

    def same(cc, r):
        return ' /\\ '.join(f'{o} = {i}' for o, i in zip(list(c) + [e['radius']], list(cc) + [r]))
    union = e['set'] == 'union'
    ins = [f'in_ball_{n} {bx} z', f'in_ball_{n} {by} z']
    claims = [f'ball_{n} {z}']
    if union:
        claims += [f'(ball_empty_{n} {z} <-> ball_empty_{n} {bx} /\\ ball_empty_{n} {by})',
                   f'(ball_empty_{n} {bx} -> {same(yc, yr)})',
                   f'(ball_empty_{n} {by} -> {same(xc, xr)})',
                   f'(forall z : R, {ins[0]} \\/ {ins[1]} -> in_ball_{n} {z} z)']
    else:
        claims += [f'(ball_empty_{n} {bx} \\/ ball_empty_{n} {by} -> ball_empty_{n} {z})',
                   f'(ball_whole_{n} {bx} -> {same(yc, yr)})',
                   f'(ball_whole_{n} {by} -> {same(xc, xr)})',
                   f'(forall z : R, {ins[0]} /\\ {ins[1]} -> in_ball_{n} {z} z)']
    lines.append('  ' + ' /\\\n  '.join(claims) + '.')
    return _statement(f'{k.name}_spec', _comment(k), lines)


def _ball_splits_spec(k, kernels, e):
    """Two balls that cover the halves of a ball (Milestone 2, "Hull, intersection and split of
    balls"): both canonical; the empty set gives the empty set twice and the whole line the whole
    line twice; for a finite ball (c, r), the first contains [c - r, c] and the second [c, c + r]."""
    t = _Terms(k)
    lines = _head(k, _used_nans(k, kernels), precision=_interval_precision(k)) + _hyps_extended(k, t) + \
        [_let(k, kernels)]
    xc, xr = t.ins[e['from']['center']].limbs, e['from']['radius']
    n = len(_limbs(k, xc, e['from']['center'], (1, 2)))
    x = _ball_args(xc, xr)
    (a, b) = (_ball_args(t.outs[p['center']].limbs, p['radius']) for p in e['parts'])
    vc = _val_sum(xc)
    claims = [f'ball_{n} {a}', f'ball_{n} {b}',
              f'(ball_empty_{n} {x} -> ball_empty_{n} {a} /\\ ball_empty_{n} {b})',
              f'(ball_whole_{n} {x} -> ball_whole_{n} {a} /\\ ball_whole_{n} {b})',
              f'(ball_finite_{n} {x} ->\n   (forall z : R, {vc} - val {xr} <= z <= {vc} -> in_ball_{n} {a} z) /\\\n'
              f'   (forall z : R, {vc} <= z <= {vc} + val {xr} -> in_ball_{n} {b} z))']
    lines.append('  ' + ' /\\\n  '.join(claims) + '.')
    return _statement(f'{k.name}_spec', _comment(k), lines)


def _set_predicate_spec(k, kernels, e):
    """A predicate of sets (Milestone 2, the enclosure interface), certain or trit, in the
    vocabulary of IeeeIntervalVocabulary.v: a mask true only if the relation holds (certain; for
    trit, yes only if it holds for every choice of members and no only if it fails for every one,
    never both); exactly the relation when an operand is not finite (the empty set, the whole line,
    a point that is not a finite number); and exactly it always (exact), or for finite operands
    under the conditions of exact_when."""
    t = _Terms(k)
    lines = _head(k, _used_nans(k, kernels), precision=_interval_precision(k)) + _hyps_extended(k, t) + \
        [_let(k, kernels)]
    s = _Sets(k, e, t)
    held = s.holds()
    if e['kind'] == 'certain':
        m = e['of']
        sound = [f'({m} = true ->\n    {held})']
        exact = [f'({m} = true <->\n    {held})']
    else:
        yes, no = e['yes'], e['no']
        failed = s.holds(negated=True)
        sound = [f'({yes} = true ->\n    {held})', f'({no} = true ->\n    {failed})',
                 f'~ ({yes} = true /\\ {no} = true)']
        exact = [f'({yes} = true <->\n    {held})', f'({no} = true <->\n    {failed})']
    if e.get('exact'):
        claims = exact if e['kind'] == 'certain' else exact + [sound[-1]]
    else:
        both = ' /\\\n   '.join(exact)
        claims = sound + [f'({s.special()} ->\n   {both})']
        if 'exact_when' in e:
            cond = t.exact_condition(e['exact_when'])
            claims.append(f'({s.all_finite()} -> {cond} ->\n   {both})')
    lines.append('  ' + ' /\\\n  '.join(claims) + '.')
    return _statement(f'{k.name}_spec', _comment(k), lines)


def _set_bound_claim(e, k, t):
    """A bound of a set over balls (Milestone 2, the bounds of a ball as numbers of T): the empty
    set gives the infinity beyond it (+inf below, -inf above); otherwise the output is on its side
    of the bound of the set, as an extended real number (range_lower, range_upper), and with
    tight=rounded the directed rounding of that bound, stepped `steps` times at most."""
    out = e['of']
    below = e['side'] == 'below'
    groups = {b: t.ins[cr['center']].limbs + (cr['radius'],) for b, cr in e['balls'].items()}

    def member(name):
        return f'in_ball_{len(groups[name]) - 1} {" ".join(groups[name])}'
    S = _set_of(k, e, groups, member)
    empty = ' \\/ '.join(f'ball_empty_{len(g) - 1} {" ".join(g)}' for g in groups.values())
    empty = f'({empty})' if len(groups) > 1 else empty
    var, rng = ('lo', 'range_lower') if below else ('hi', 'range_upper')
    tight = e.get('tight')
    if tight is None:
        side = f'xle (xval {out}) {var} = true' if below else f'xle {var} (xval {out}) = true'
    else:
        r = f'{"xrd" if below else "xru"} prec emax {var}'
        steps = tight.get('steps', 0)
        if steps:
            limit = r
            for _ in range(steps):
                limit = f'{"xpred" if below else "xsucc"} prec emax ({limit})'
            side = (f'xle ({limit}) (xval {out}) = true /\\ xle (xval {out}) ({r}) = true' if below else
                    f'xle ({r}) (xval {out}) = true /\\ xle (xval {out}) ({limit}) = true')
        else:
            side = f'xval {out} = {r}'
    return (f'({empty} -> {out} = infinity prec emax {"false" if below else "true"}) /\\\n'
            f'  (~ {empty} -> forall {var} : xreal, {rng} {S} {var} -> {side})')


ROUNDING = {'nearest': 'RN', 'down': 'RD', 'up': 'RU'}
RELATION = {'lt': 'xlt', 'le': 'xle', 'eq': 'xeq'}


def _binary(tree):
    """Whether an expression has a sum, a difference or a product: the value of two operands."""
    return tree[0] in ('add', 'sub', 'mul') or any(_binary(x) for x in tree[1:] if isinstance(x, tuple))


def _operands_finite(k):
    """That every operand is finite, as one proposition."""
    return ' /\\ '.join(f'finite {v}' for v in k.input_limbs)


def _extended_claim(e, k, t):
    """One claim of a kernel that needs no fix-up, read over extended real numbers. With
    zero_factor (Milestone 2, mul_dir_1), a zero operand gives zero, and the claim is read as
    without it for the others: 0 times infinity is 0, the product of interval arithmetic."""
    if e.get('zero_factor'):
        # An operand is zero when its leading limb is (it is canonical), an output when every limb is.
        a, b = (t.ins[x[1]].limbs[0] for x in expr.parse(k.value)[1:])
        zo = ' /\\ '.join(f'zero {v}' for v in t.outs[e['of']].limbs)
        inner = _extended_claim({x: y for x, y in e.items() if x != 'zero_factor'}, k, t)
        return (f'(zero {a} \\/ zero {b} -> {zo}) /\\\n'
                f'  (~ (zero {a} \\/ zero {b}) ->\n   {inner})')
    kind = e['kind']
    if kind == 'normalized':
        # Canonical in every case; normalized when every operand and the output are finite.
        out = _limbs(k, t.outs[e['of']].limbs, e['of'])
        return (f'canonical_2 {" ".join(out)} /\\\n  ({_operands_finite(k)} -> '
                + ' -> '.join(f'finite {v}' for v in out) + f' ->\n   {_normalized_ieee(out, k)})')
    if kind == 'outward':
        return _outward_extended(e, k, t)
    if kind == 'set_bound':
        return _set_bound_claim(e, k, t)
    if kind == 'error':
        # As for finite operands (the claim of a core), when every operand and the output are finite.
        out = t.outs[e['of']].limbs
        return (f'({_operands_finite(k)} -> ' + ' -> '.join(f'finite {v}' for v in out) + ' ->\n   '
                + _claim(e, k, t, {g.name: g.limbs for g in k.outputs}) + ')')
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


def _outward_extended(e, k, t):
    """outward in the extended domain (Milestone 2, mul_ext_2_2): the output is not a NaN; an
    infinite operand gives the value of IEEE 754 on the operands; finite operands give an output on
    its side of the value as an extended real number (an infinity on that side is one), and a finite
    output the claim of the finite domain: within rel |value| + abs of it, and equal to it under the
    conditions of exact_when."""
    out = _limbs(k, t.outs[e['of']].limbs, e['of'], (1, 2))
    below = e['side'] == 'below'
    xv, x = _xv(out), t.xterm(k.value)
    ops = _operands_finite(k)
    v = t.value()
    rel = rocq.claim_constant_term(e['rel'], t.kernels, EMIN)
    absolute = rocq.claim_constant_term(e['abs'], t.kernels, EMIN)
    side = f'xle ({xv}) {x} = true' if below else f'xle {x} ({xv}) = true'
    near = f'Rabs ({_val_sum(out)} - {v}) <= {rel} * Rabs {v} + {absolute}'
    if 'exact_when' in e:
        near += f' /\\\n    ({t.exact_condition(e["exact_when"])} -> {_val_sum(out)} = {v})'
    return (f'~ nan {out[0]} /\\\n  (~ ({ops}) -> {xv} = {x}) /\\\n'
            f'  ({ops} ->\n   {side} /\\\n   (finite {out[0]} ->\n    {near}))')


def _no_fix_up_spec(k, kernels):
    """A kernel of the extended domain that needs no fix-up: its claims over extended reals."""
    t = _Terms(k)
    t.kernels = kernels
    lines = _head(k, _used_nans(k, kernels)) + _hyps_extended(k, t) + [_let(k, kernels)]
    lines.append('  ' + ' /\\\n  '.join(_extended_claim(e, k, t) for e in k.ensures) + '.')
    return _statement(statement_names(k)[0], _comment(k), lines)


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
            e = k.ensures[0]
            if 'lower' in e['from']:
                return [_makes_ball_interval_spec(k, kernels, e)]
            return [_makes_ball_spec(k, kernels, e)]
        if 'makes_interval' in kinds:
            return [_makes_interval_spec(k, kernels, k.ensures[0])]
        if 'represents' in kinds:
            return [_represents_spec(k, kernels, next(e for e in k.ensures if e['kind'] == 'represents'))]
        if kinds == {'finite_or_nan'}:
            return [_finite_or_nan_spec(k, kernels, k.ensures[0])]
        enc = [e for e in k.ensures if e['kind'] == 'encloses']
        if enc:
            return [_ball_spec(k, kernels, enc[0])]
        for kind, printer in (('interval_set', _interval_set_spec), ('ball_of_interval', _ball_of_interval_spec),
                              ('interval_of_ball', _interval_of_ball_spec), ('splits', _splits_spec),
                              ('certain', _set_predicate_spec), ('trit', _set_predicate_spec),
                              ('ball_set', _ball_set_spec), ('ball_splits', _ball_splits_spec)):
            if kind in kinds:
                if len(k.ensures) != 1:
                    raise PrintError(f'kernel {k.name}: {kind} goes with no other claim')
                return [printer(k, kernels, k.ensures[0])]
        intervals = [e for e in k.ensures if e['kind'] == 'encloses_interval']
        if intervals:
            if len(k.ensures) != 1:
                raise PrintError(f'kernel {k.name}: encloses_interval goes with no other claim')
            return [_interval_spec(k, kernels, intervals[0])]
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
             '   described in proofs/theories/IeeeVocabulary.v and IeeeIntervalVocabulary.v, whose vocabulary',
             '   they use: for all precisions from the kernel\'s minimum on and all emax with prec < emax,',
             '   for every choice of the NaN each operation returns, with rounding to nearest, ties to',
             '   even; emin = 3 - emax - prec. A hand-written proof of statement S is a theorem whose type',
             '   is exactly S. *)',
             'From Stdlib Require Import Reals ZArith List.',
             'From Flocq Require Import Core Binary.',
             f'From {GEN_PATH} Require Import Model Statements.',
             f'From {THEORIES_PATH} Require Import Program IeeeBridge IeeeVocabulary IeeeIntervalVocabulary.',
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
    cnames, _ = _const_names(model_kernels, real, kernels)     # the names of IeeeModel.v (model)
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
    and F_O_ieee_spec (a fold's or a map's ieee_theorem; F_ieee_spec, a convolution's) of
    IeeeFoldStatements.v; the first two, then the others, each in the order of their file."""
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
    for fd in _folds_in_order(kernels):
        if not fd.ieee_theorem:
            continue
        if getattr(fd, 'is_conv', False):
            # A convolution has one statement, of its one order (F_ieee_spec).
            out.append((f'{fd.name}_ieee_spec', fd.ieee_theorem, f'{fd.name}_ieee_correct', 'IeeeFoldStatements'))
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


def _folds_in_order(kernels):
    """The folds in the order of IeeeFoldModel.v and IeeeFoldStatements.v: those that are neither
    maps nor convolutions, then the maps, then the convolutions (each after the fold of its
    coefficients), each group in the order of the set."""
    folds = list(getattr(kernels, 'folds', {}).values())
    maps = [fd for fd in folds if getattr(fd, 'is_map', False)]
    convs = [fd for fd in folds if getattr(fd, 'is_conv', False)]
    bvs = [fd for fd in folds if getattr(fd, 'is_bv', False)]
    # The products of two BallVectors name convolutions: last.
    products = [fd for fd in folds if getattr(fd, 'is_bv_conv', False)]
    return [fd for fd in folds if fd not in maps + convs + bvs + products] + maps + convs + bvs + products


def fold_model(kernels):
    """proofs/gen/IeeeFoldModel.v: every fold of the extended domain in the IEEE model, in the shape
    of its real model (FoldModel.v): F_step and F_combine apply the IEEE models of the step and the
    combination (IeeeModel.v) to the limbs of tuples; F_seq is the finish on fold_seq of the step
    from the zero state, every limb +0; F_lanes W the finish on fold_lanes W. Then the maps and the
    convolutions (map_model, conv_model)."""
    every = _folds_in_order(kernels)
    products = [fd for fd in every if getattr(fd, 'is_bv_conv', False)]
    folds = [fd for fd in every if not getattr(fd, 'is_map', False) and not getattr(fd, 'is_conv', False)
             and not getattr(fd, 'is_bv', False) and fd not in products]
    writers = [fd for fd in every if fd not in folds and not getattr(fd, 'is_bv', False) and fd not in products]
    bvs = [fd for fd in every if getattr(fd, 'is_bv', False)]
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
             f'From {GEN_PATH} Require IeeeModel.'] + \
        ([f'From {GEN_PATH} Require FoldModel.'] if any(getattr(fd, 'is_conv', False) for fd in writers) else []) + [
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
    if bvs:
        lines.append('Local Notation pinf := (IeeeOperations.pinf prec emax).')
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
    if writers:
        lines += ['', '(* The maps and the convolutions (architecture.md, "Maps", "Convolutions"): F_check is the check',
                  '   of an element written (fold_finish_k), which returns it, or its canonical NaN, and the mask that',
                  '   its leading limb is finite. A map writes ws_, its step on the scalars and each element (map); a',
                  '   convolution writes the final state of the sequential order of the fold of its coefficients on',
                  '   the terms of each coefficient. The mask m_ is the and of the check\'s mask on every element',
                  '   written, by fold_seq (and, for a map, fold_lanes with andb, from true); when it is false, every',
                  '   element written is what the check returns of it (the second pass). F_seq, F_lanes W and F_conv',
                  '   return the list written and the mask. *)']
    for fd in writers:
        lines += map_model(fd, kernels) if getattr(fd, 'is_map', False) else conv_model(fd, kernels)
    if bvs:
        lines += ['', '(* The ball vectors (architecture.md, "Ball vectors"): F_step and F_map are a map\'s, the centers',
                  '   written; F_record, the step of a fold of maxima, updates the state, the largest magnitude of a',
                  '   leading limb written and the mask that none was a NaN, from each center written, and F_combine',
                  '   combines two; F_seq and F_lanes W fold it over the centers written (fold_seq, fold_lanes), give',
                  '   the radius by the radius kernel on the state\'s limb and the scalars, and test it with the',
                  '   finish under the state\'s mask; when the finish\'s flag is false, every center written is zero',
                  '   and the radius +infinity (the whole space). They return the centers, the radius and the flag. *)']
    for fd in bvs:
        lines += bv_model(fd, kernels)
    if products:
        lines += ['', '(* The products of two ball vectors (architecture.md, "Ball vectors"): the coefficients and the',
                  '   mask of the convolution of the centers (F_conv of the convolution named); the maxima of the',
                  '   operands\' centers, fold_seq of F_record over each list; the count min(n_x, n_y) rounded up',
                  '   (F_count, binary_normalize upward); the bound of dot for it; the radius kernel on the maxima,',
                  '   the radii, the count and the bound; the finish on the radius, the convolution\'s mask and the',
                  '   bound\'s; when its flag is false, every coefficient is zero and the radius +infinity (the whole',
                  '   space). F_conv returns the coefficients, the radius and the flag. *)']
    for fd in products:
        lines += bv_conv_model(fd, kernels)
    lines += ['', 'End IeeeFolds.']
    return '\n'.join(lines) + '\n'


def bv_conv_model(fd, kernels):
    """The product of two BallVectors in the IEEE model: F_record, F_count and F_conv (the code of
    cpp.bv_conv_seq and cpp.bv_conv_end_function)."""
    conv = kernels.folds[fd.centers]
    record, bound, radius, finish = (kernels[c[0]] for c in (fd.records[0], fd.bound, fd.radius, fd.finish))
    x, y = fd.arrays
    xs, ys = f'{x.name}s', f'{y.name}s'
    tx = _ftype(len(x.limbs))
    lx = f'list ({tx})' if ' ' in tx else f'list {tx}'
    n = len(fd.writes[0].limbs)
    wtype = _ftype(n)
    lw = f'list ({wtype})' if ' ' in wtype else f'list {wtype}'
    zeros = '(' + ', '.join(['pzero'] * n) + ')' if n > 1 else 'pzero'
    names = fd.state_names()
    env = {names[0]: 'fst sa_', names[2]: 'fst sb_', fd.count: 'm_', fd.bound[2][0]: 'fst (fst b_)',
           fd.bound[2][1]: 'snd (fst b_)'}
    env.update({g.name: g.name for g in fd.scalars})
    rad = _kernel_call(radius, kernels, [env[a] for a in fd.radius[1]])
    fin = _kernel_call(finish, kernels, ['rz_', 'snd c_', 'snd b_'])
    params = ''.join(f' ({g.name} : float)' for g in fd.scalars)
    return ['', f'(* {fd.name}: the product of two ball vectors; centers {conv.name}, records {record.name}, bound '
                f'{bound.name}, radius {radius.name}, finish {finish.name}. *)',
            f'Definition {fd.name}_record (mok : float * bool) (w_ : {tx}) : float * bool :=',
            f'  {_kernel_call(record, kernels, rocq.tuple_parts("mok", 2) + rocq.tuple_parts("w_", len(x.limbs)))}.',
            '',
            f'Definition {fd.name}_count ({xs} {ys} : {lx}) : float :=',
            f'  binary_normalize prec emax prec_gt_0_ prec_lt_emax_ BinarySingleNaN.mode_UP (Z.of_nat (Nat.min (length {xs}) '
            f'(length {ys}))) 0 false.',
            '',
            f'Definition {fd.name}_conv{params} ({xs} {ys} : {lx}) : {lw} * float * bool :=',
            f'  let c_ := {conv.name}_conv {xs} {ys} in',
            f'  let sa_ := fold_seq {fd.name}_record (pzero, true) {xs} in',
            f'  let sb_ := fold_seq {fd.name}_record (pzero, true) {ys} in',
            f'  let m_ := {fd.name}_count {xs} {ys} in',
            f'  let b_ := {_kernel_call(bound, kernels, ["m_"])} in',
            f'  let rz_ := {rad} in',
            f'  let f_ := {fin} in',
            f'  (if snd f_ then (fst c_, fst f_) else (map (fun _ => {zeros}) (fst c_), pinf), snd f_).']


def _check_model(fd, kernels):
    """F_check: the IEEE model of the check of a map or a convolution, on one element written."""
    check = kernels[fd.check]
    n = len(fd.writes[0].limbs)
    rtype = ' * '.join(_type(kind) for kind in check.output_kinds)
    return [f'Definition {fd.name}_check (w_ : {_ftype(n)}) : {rtype} :=',
            f'  {_kernel_call(check, kernels, rocq.tuple_parts("w_", n))}.']


def _second_pass(fd, mask, written='ws_'):
    """The last two lines of F_seq, F_lanes or F_conv: the mask, then the list written, each element
    as the check returns it when the mask is false, and the mask."""
    return [f'  let m_ := {mask} in',
            f'  (if m_ then {written} else map (fun w_ => fst ({fd.name}_check w_)) {written}, m_).']


def _mask_step(fd):
    return f'(fun m_ w_ => andb m_ (snd ({fd.name}_check w_)))'


def map_model(fd, kernels):
    """A map in the IEEE model: F_step on the scalars and one element, from the IEEE model of the
    step (the shape of FoldModel.F_step); F_check; F_seq and F_lanes W, which return the list written
    and the mask (architecture.md, "Maps"; the code of cpp.map_seq, cpp.map_lanes)."""
    step = kernels[fd.step[0]]
    _, el, xs = rocq._fold_binders(fd)
    etype = _fold_element_ftype(fd)
    lt = f'list ({etype})' if ' ' in etype else f'list {etype}'
    groups = rocq.fold_groups(fd, el)
    sizes = {g.name: len(g.limbs) for g in fd.arrays + fd.scalars}
    groups.update({g.name: g.name for g in fd.scalars})
    args = [p for a in fd.step[1] for p in rocq.tuple_parts(groups[a], sizes[a])]
    params = ''.join(f' ({g.name} : {_ftype(len(g.limbs))})' for g in fd.scalars)
    wtype = _ftype(len(fd.writes[0].limbs))
    lw = f'list ({wtype})' if ' ' in wtype else f'list {wtype}'
    scalars = ''.join(' ' + g.name for g in fd.scalars)
    stepped = f'({fd.name}_step{scalars})' if scalars else f'{fd.name}_step'
    lines = ['', f'(* {fd.name}: a map; step {step.name}, check {fd.check}. *)',
             f'Definition {fd.name}_step{params} ({el} : {etype}) : {wtype} :=',
             f'  {_kernel_call(step, kernels, args)}.', ''] + _check_model(fd, kernels)
    if 'sequential' in fd.orders:
        lines += ['', f'Definition {fd.name}_seq{params} ({xs} : {lt}) : {lw} * bool :=',
                  f'  let ws_ := map {stepped} {xs} in'] + _second_pass(fd, f'fold_seq {_mask_step(fd)} true ws_')
    if 'lanes' in fd.orders:
        lines += ['', f'Definition {fd.name}_lanes (W : nat){params} ({xs} : {lt}) : {lw} * bool :=',
                  f'  let ws_ := map {stepped} {xs} in'] + \
            _second_pass(fd, f'fold_lanes {_mask_step(fd)} andb true W ws_')
    return lines


def conv_model(fd, kernels):
    """A convolution in the IEEE model: F_check, and F_conv xs ys, which returns the coefficients and
    the mask: coefficient j is fold_seq of the IEEE step of the fold of its coefficients (F_step of
    that fold, above) from its zero state on FoldModel.conv_terms xs ys j (architecture.md,
    "Convolutions"; the code of cpp.conv_seq)."""
    cf = kernels.folds[fd.coefficients]
    x, y = fd.arrays
    tx, ty = _ftype(len(x.limbs)), _ftype(len(y.limbs))
    lx = f'list ({tx})' if ' ' in tx else f'list {tx}'
    ly = f'list ({ty})' if ' ' in ty else f'list {ty}'
    wtype = _ftype(len(fd.writes[0].limbs))
    lw = f'list ({wtype})' if ' ' in wtype else f'list {wtype}'
    xs, ys = f'{x.name}s', f'{y.name}s'
    zero = rocq.state_zero(cf, 'pzero', 'true')
    return ['', f'(* {fd.name}: a convolution; coefficient j is {cf.name} in the sequential order on the terms '
                f'FoldModel.conv_terms {xs} {ys} j, checked by {fd.check}. *)'] + _check_model(fd, kernels) + [
            '', f'Definition {fd.name}_conv ({xs} : {lx}) ({ys} : {ly}) : {lw} * bool :=',
            f'  let ws_ := map (fun j => fold_seq {cf.name}_step {zero} (FoldModel.conv_terms {xs} {ys} j))',
            f'                 (seq 0 (FoldModel.conv_length (length {xs}) (length {ys}))) in'] + \
        _second_pass(fd, f'fold_seq {_mask_step(fd)} true ws_')


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


# --- Folds of maxima: the two orders, and the flag ----------------------------------------------------
#
# Two statements more for a fold of maxima of both orders, of the IEEE model only (the real model's
# maximum has no flag, and its lane order is its own definition): that the lane order computes the
# state of the sequential order, for every number of lanes and every list, NaNs and infinities among
# the elements; and when exactly the flag of the sequential order is true. With the first, the second
# is the lane order's too. The hand-written theorems of these facts (IeeeFoldNorm.v of the proofs) have
# exactly these types once the section's variables are bound.

def _max_parts(fd, kernels):
    """The step and the combination of a fold of maxima as terms of IeeeFoldModel.v, each with the NaN
    choices it takes; the zero state; and the NaN choices of both, in section order."""
    step, combine, _ = _fold_parts(fd, kernels)
    snans = [n for n, _ in NANS if n in _used_nans(step, kernels)]
    cnans = [n for n, _ in NANS if n in _used_nans(combine, kernels)]
    stp = ' '.join([f'IeeeFoldModel.{fd.name}_step', 'prec', 'emax'] + snans)
    cmb = ' '.join([f'IeeeFoldModel.{fd.name}_combine', 'prec', 'emax'] + cnans)
    zero = rocq.state_zero(fd, 'IeeeOperations.pzero prec emax', 'true')
    return stp, cmb, zero, [n for n, _ in NANS if n in set(snans) | set(cnans)]


def _max_head(nans):
    return ['  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)',
            '         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)' +
            (f'\n         {_binders(nans)},' if nans else ',')]


def max_orders_statement(fd, kernels):
    """F_orders_ieee_spec, of a fold of maxima in both orders: the lane order computes the state of the
    sequential order, for every number of lanes W and every list, whatever its elements; its finish
    then gives the same result and the same flag. For every precision: no minimum."""
    _, el, xs = rocq._fold_binders(fd)
    stp, cmb, zero, nans = _max_parts(fd, kernels)
    etype = _fold_element_ftype(fd).replace('float', 'binary_float prec emax')
    return ([f'(* {fd.name}: the lane order computes the state of the sequential order, for every number of '
             'lanes W and every list, in the IEEE model; its finish then gives the same result and flag. Status: '
             'unverified. *)',
             f'Definition {fd.name}_orders_ieee_spec : Prop :='] + _max_head(nans) +
            [f'  forall (W : nat) ({xs} : list ({etype})),',
             f'  fold_lanes ({stp}) ({cmb}) {zero} W {xs} =',
             f'  fold_seq ({stp}) {zero} {xs}.'])


def max_flag_statement(fd, kernels):
    """F_flag_ieee_spec, of a fold of maxima: the flag of the sequential order is true exactly when the
    leading limb of every element is finite and the limb of the final state, stepped up as the finish
    does (the steps of its finite_or_nan), is finite; with no step, exactly when every leading limb
    is finite (the largest of finite magnitudes is finite). No requirement on the elements: any
    value, canonical or not. The lane order's flag is the same (F_orders_ieee_spec)."""
    _, el, xs = rocq._fold_binders(fd)
    stp, _, zero, _ = _max_parts(fd, kernels)
    _, _, finish = _fold_parts(fd, kernels)
    nans = _fold_nans(fd, kernels, 'sequential')
    etype = _fold_element_ftype(fd).replace('float', 'binary_float prec emax')
    groups = rocq.fold_groups(fd, el)
    g = fd.arrays[0]
    lead = rocq.tuple_parts(groups[g.name], len(g.limbs))[0]
    steps = next(e.get('steps', 0) for e in finish.ensures if e['kind'] == 'finite_or_nan')
    call = ' '.join([f'IeeeFoldModel.{fd.name}_seq', 'prec', 'emax'] + nans + [xs])
    conds = [f'Forall (fun {el} => finite {rocq._paren(lead)}) {xs}']
    what = 'every leading limb is finite'
    if steps:
        m = rocq.state_groups(fd, f'(fold_seq ({stp}) {zero} {xs})')[fd.states[0].name][0]
        for _ in range(steps):
            m = f'IeeeOperations.succ prec emax ({m})'
        conds.append(f'finite ({m})')
        what += (' and the largest magnitude, the limb of the final state, stepped up ' +
                 ('once' if steps == 1 else f'{steps} times') + ' as the finish does, is finite')
    return ([f'(* {fd.name}: the flag of the sequential order is true exactly when {what}, in the IEEE model. '
             'Status: unverified. *)',
             f'Definition {fd.name}_flag_ieee_spec : Prop :='] + _max_head(nans) +
            [f'  forall {xs} : list ({etype}),',
             f'  snd ({call}) = true <->',
             '  ' + ' /\\\n  '.join(conds) + '.'])


def _writer_nans(fd, kernels, parts):
    used = set()
    for k in parts + [kernels[fd.check]]:
        used.update(_used_nans(k, kernels))
    return [n for n, _ in NANS if n in used]


def _writer_head(fd, nans):
    return ['  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)',
            '         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)' +
            (f'\n         {_binders(nans)},' if nans else ','),
            f'  ({fd.min_precision} <= prec)%Z ->']


def _written_limbs(fd, w='w_'):
    return rocq.tuple_parts(w, len(fd.writes[0].limbs))


def map_statement(fd, kernels, order):
    """F_seq_ieee_spec or F_lanes_ieee_spec of a map (the second for every W): for canonical scalars
    and elements (any value, for one limb; a finite power of two for a scalar power_of_two), with
    (ws_, flag_) the list written and the mask, Forall2 of the elements and the elements written of:
    if the leading limb of the element written is finite, every limb of the scalars, of the element
    and of the element written is finite, the values written are those of the real model of the step
    (Model.v, at ieee_emin prec emax) on the values given, and the claims of the step hold of them
    (as in K_ieee_spec); otherwise every limb written is a NaN and the mask is false. And the mask is
    true exactly when the leading limb of every element written is finite. The scalars are said to
    be finite element by element: of an empty list nothing is said of them, and the mask is true."""
    step = kernels[fd.step[0]]
    _, el, xs = rocq._fold_binders(fd)
    suffix = ir.ORDER_SUFFIX[order]
    nans = _writer_nans(fd, kernels, [step])
    etype = _fold_element_ftype(fd).replace('float', 'binary_float prec emax')
    lt = f'list ({etype})'
    # The step's own names for what the map passes it, as in the real model (rocq.map_statement).
    kgroup = dict(zip(fd.step[1], step.inputs))
    canonical = {r[1] for r in fd.requires if r[0] == 'canonical'}
    pow2 = {r[1] for r in fd.requires if r[0] == 'power_of_two'}
    hyps = []
    for g in fd.scalars:
        limbs = list(kgroup[g.name].limbs)
        if g.name in canonical:
            hyps.append(f'canonical_2 {" ".join(_limbs(step, limbs, g.name))}')
        if g.name in pow2:
            hyps += [f'finite {limbs[0]}', f'(exists n : Z, val {limbs[0]} = bpow radix2 n)']
    groups = rocq.fold_groups(fd, el)
    element = [f'canonical_2 {" ".join(rocq._paren(x) for x in _limbs(step, rocq.tuple_parts(groups[g.name], len(g.limbs)), g.name))}'
               for g in fd.arrays if g.name in canonical]
    pattern = rocq._pattern([rocq._pattern(list(kgroup[g.name].limbs)) for g in fd.arrays])
    outs = list(step.outputs[0].limbs)
    t = _Terms(step)
    claims = [_claim(e, step, t, {g.name: g.limbs for g in step.outputs}) for e in step.ensures]
    section = [{'emin': EMIN, 'prec': 'prec', 'choice': 'tie_even'}[v] for v in rocq.section_args(step, kernels)]
    real = ' '.join([step.name] + section + [f'(val {v})' for v in step.input_limbs])
    vals = f'val {outs[0]}' if len(outs) == 1 else '(' + ', '.join(f'val {v}' for v in outs) + ')'
    finite = [f'finite {v}' for v in step.input_limbs] + [f'finite {v}' for v in outs[1:]]
    scalars = ' '.join('(' + ', '.join(kgroup[g.name].limbs) + ')' if len(g.limbs) > 1 else kgroup[g.name].limbs[0]
                       for g in fd.scalars)
    scalar_limbs = [v for g in fd.scalars for v in kgroup[g.name].limbs]
    if order == 'lanes':
        binders = f'forall (W : nat) ({" ".join(scalar_limbs)} : binary_float prec emax) ({xs} : {lt}),' \
            if scalar_limbs else f'forall (W : nat) ({xs} : {lt}),'
    else:
        binders = f'forall ({" ".join(scalar_limbs)} : binary_float prec emax) ({xs} : {lt}),' \
            if scalar_limbs else f'forall {xs} : {lt},'
    call = ' '.join([f'IeeeFoldModel.{fd.name}_{suffix}', 'prec', 'emax'] + nans + (['W'] if order == 'lanes' else []) +
                    ([scalars] if scalars else []) + [xs])
    what = {'sequential': 'the sequential order', 'lanes': 'the lane order, for every number of lanes W'}[order]
    lines = [f'(* {fd.name}, {what}, in the IEEE model: each element it writes, and its mask. Status: '
             f'{"proved" if fd.ieee_theorem else "unverified"}. *)',
             f'Definition {fd.name}_{suffix}_ieee_spec : Prop :='] + _writer_head(fd, nans) + [f'  {binders}']
    lines += [f'  {h} ->' for h in hyps]
    if element:
        lines.append(f'  Forall (fun {el} => {" /\\ ".join(element)}) {xs} ->')
    lines += [f"  let '(ws_, flag_) := {call} in",
              f'  Forall2 (fun {el} w_ =>']
    lines += [f'    {rocq._let(pattern, el)}'] if pattern != el else []
    lines += [f'    {rocq._let(rocq._pattern(outs), "w_")}',
              f'    (finite {outs[0]} ->',
              '     ' + ' /\\ '.join(finite) + (' /\\' if finite else ''),
              f'     {vals} = {real} /\\',
              '     ' + ' /\\\n     '.join(claims) + ') /\\',
              f'    (~ finite {outs[0]} -> ' + ' /\\ '.join(f'nan {v}' for v in outs) + ' /\\ flag_ = false))',
              f'    {xs} ws_ /\\',
              f'  (flag_ = true <-> Forall (fun w_ => finite {rocq._paren(_written_limbs(fd)[0])}) ws_).']
    return lines


def conv_statement(fd, kernels):
    """F_ieee_spec of a convolution: for canonical entries of the two arrays (any value, for one
    limb), with (ws_, flag_) the coefficients written and the mask, Forall2 of the indices of the
    coefficients and the coefficients of: if the leading limb of coefficient j is finite, every limb
    of every term of it (conv_terms xs ys j) and of the coefficient is finite, its values are the
    real model of the sequential order of the fold of its coefficients (FoldModel.v, at ieee_emin
    prec emax) on the values of the terms, and the claims of that fold's statement hold of them;
    otherwise every limb of the coefficient is a NaN. And the mask is true exactly when the leading
    limb of every coefficient is finite."""
    cf = kernels.folds[fd.coefficients]
    step = kernels[cf.step[0]]
    nans = _writer_nans(fd, kernels, [step])
    x, y = fd.arrays
    _, el, txs = rocq._fold_binders(cf)
    xs, ys = f'{x.name}s', f'{y.name}s'
    canonical = {r[1] for r in fd.requires if r[0] == 'canonical'}
    hyps = []
    for g, l in ((x, xs), (y, ys)):
        if g.name in canonical:
            limbs = _limbs(step, rocq.tuple_parts(g.name, len(g.limbs)), g.name)
            hyps.append(f'Forall (fun {g.name} => canonical_2 {" ".join(rocq._paren(v) for v in limbs)}) {l}')
    tx = _ftype(len(x.limbs)).replace('float', 'binary_float prec emax')
    ty = _ftype(len(y.limbs)).replace('float', 'binary_float prec emax')
    binders = f'forall ({xs} : list ({tx})) ({ys} : list ({ty})),' if tx != ty else f'forall {xs} {ys} : list ({tx}),'
    groups = rocq.fold_groups(cf, el)
    sizes = {g.name: len(g.limbs) for g in cf.arrays}
    terms = [f'finite {rocq._paren(v)}' for g in cf.arrays for v in rocq.tuple_parts(groups[g.name], sizes[g.name])]
    values = []
    for g in cf.arrays:
        parts = [f'val {rocq._paren(v)}' for v in rocq.tuple_parts(groups[g.name], sizes[g.name])]
        values.append(parts[0] if len(parts) == 1 else '(' + ', '.join(parts) + ')')
    value = values[0] if len(values) == 1 else '(' + ', '.join(values) + ')'
    section = [{'emin': EMIN, 'prec': 'prec', 'choice': 'tie_even'}[v] for v in rocq.fold_section_args([step], kernels)]
    real = ' '.join([f'FoldModel.{cf.name}_seq'] + section + ['vs'])
    w = [rocq._paren(v) for v in _written_limbs(fd)]
    vals = f'val {w[0]}' if len(w) == 1 else '(' + ', '.join(f'val {v}' for v in w) + ')'
    claims = [re.sub(r'\bemin\b', EMIN, c) for c in rocq.fold_conclusion(cf, 's', el, 'vs', indent='         ')]
    call = ' '.join([f'IeeeFoldModel.{fd.name}_conv', 'prec', 'emax'] + nans + [xs, ys])
    lines = [f'(* {fd.name}, each coefficient it writes, and its mask, in the IEEE model. Status: '
             f'{"proved" if fd.ieee_theorem else "unverified"}. *)',
             f'Definition {fd.name}_ieee_spec : Prop :='] + _writer_head(fd, nans) + [f'  {binders}']
    lines += [f'  {h} ->' for h in hyps]
    lines += [f"  let '(ws_, flag_) := {call} in",
              '  Forall2 (fun j w_ =>',
              f'    let {txs} := conv_terms {xs} {ys} j in',
              f'    (finite {w[0]} ->',
              f'     Forall (fun {el} => {" /\\ ".join(terms)}) {txs} /\\'] + \
        ([f'     ' + ' /\\ '.join(f'finite {v}' for v in w[1:]) + ' /\\'] if len(w) > 1 else []) + [
              f'     let vs := map (fun {el} => {value}) {txs} in',
              f'     let s := {real} in',
              f'     {vals} = s /\\',
              '     ' + ' /\\\n     '.join(claims) + ') /\\',
              # A coefficient that is not finite is a NaN in every limb, and the flag is false, as in a
              # map's statement (map_statement).
              f'    (~ finite {w[0]} -> ' + ' /\\ '.join(f'nan {v}' for v in w) + ' /\\ flag_ = false))',
              f'    (seq 0 (conv_length (length {xs}) (length {ys}))) ws_ /\\',
              f'  (flag_ = true <-> Forall (fun w_ => finite {w[0]}) ws_).']
    return lines


def bv_model(fd, kernels):
    """A ball vector in the IEEE model: F_step, F_map, F_record, F_combine, and F_seq, F_lanes W,
    which return the centers written, the radius and the flag (the code of cpp.bv_seq, cpp.bv_lanes)."""
    step, record, combine, radius, finish = (kernels[c[0]] for c in (fd.step, fd.record, fd.combine, fd.radius,
                                                                       fd.finish))
    _, el, xs = rocq._fold_binders(fd)
    etype = _fold_element_ftype(fd)
    lt = f'list ({etype})' if ' ' in etype else f'list {etype}'
    groups = rocq.fold_groups(fd, el)
    sizes = {g.name: len(g.limbs) for g in fd.arrays + fd.scalars}
    groups.update({g.name: g.name for g in fd.scalars})
    args = [p for a in fd.step[1] for p in rocq.tuple_parts(groups[a], sizes[a])]
    used = [g.name for g in fd.scalars if g.name in fd.step[1]]
    params = rocq.bv_scalar_params(fd, set(used), 'float')
    allp = rocq.bv_scalar_params(fd, {g.name for g in fd.scalars}, 'float')
    n = len(fd.writes[0].limbs)
    wtype = _ftype(n)
    lw = f'list ({wtype})' if ' ' in wtype else f'list {wtype}'
    exact = fd.exact_mask is not None
    # The state of the fold of maxima, m and ok; a ball vector exact under conditions ands the step's
    # masks apart, as a map its check's (ex_ below).
    stype = 'float * bool'
    mok = ''.join(fd.state_names()[:2])
    zero = '(pzero, true)'
    stepped = f'({fd.name}_step{"".join(" " + s for s in used)})' if used else f'{fd.name}_step'
    zeros = '(' + ', '.join(['pzero'] * n) + ')' if n > 1 else 'pzero'
    if exact:
        mapped = [f'Definition {fd.name}_map{params} ({xs} : {lt}) : {lw} :=',
                  f'  map (fun {el} => fst ({fd.name}_step{"".join(" " + s for s in used)} {el})) {xs}.']
    else:
        mapped = [f'Definition {fd.name}_map{params} ({xs} : {lt}) : {lw} :=',
                  f'  map {stepped} {xs}.']
    lines = ['', f'(* {fd.name}: a ball vector; step {step.name}, record {record.name}, combination {combine.name}, '
                 f'radius {radius.name}, finish {finish.name}' +
                 (', the and of the step\'s masks of exactness' if exact else '') + '. *)',
             f'Definition {fd.name}_step{params} ({el} : {etype}) : {wtype}{" * bool" if exact else ""} :=',
             f'  {_kernel_call(step, kernels, args)}.',
             ''] + mapped + [
             '',
             f'Definition {fd.name}_record ({mok} : {stype}) (w_ : {wtype}) : {stype} :=',
             f'  {_kernel_call(record, kernels, rocq.tuple_parts(mok, 2) + rocq.tuple_parts("w_", n))}.',
             '',
             f'Definition {fd.name}_combine (a b : {stype}) : {stype} :=',
             f'  {_kernel_call(combine, kernels, rocq.tuple_parts("a", 2) + rocq.tuple_parts("b", 2))}.']
    rad = _kernel_call(radius, kernels, ['fst s_'] + (['ex_'] if exact else []) + list(fd.radius[1][1 + exact:]))
    fin = _kernel_call(finish, kernels, ['rz_', 'snd s_'])
    for order in ('sequential', 'lanes'):
        if order not in fd.orders:
            continue
        head = f'Definition {fd.name}_seq{allp} ({xs} : {lt})' if order == 'sequential' else \
            f'Definition {fd.name}_lanes (W : nat){allp} ({xs} : {lt})'
        state = (f'fold_seq {fd.name}_record {zero} ws_' if order == 'sequential' else
                 f'fold_lanes {fd.name}_record {fd.name}_combine {zero} W ws_')
        if exact:
            # The centers and the masks of the step; the masks and-ed from true in the order's form, as
            # a map's mask (fold_seq_and, fold_lanes_and of Folds.v).
            mask = ('fold_seq (fun m_ e_ => andb m_ (snd e_)) true es_' if order == 'sequential' else
                    'fold_lanes (fun m_ e_ => andb m_ (snd e_)) andb true W es_')
            lines += ['', f'{head} : {lw} * float * bool :=',
                      f'  let es_ := map {stepped} {xs} in',
                      '  let ws_ := map fst es_ in',
                      f'  let s_ := {state} in',
                      f'  let ex_ := {mask} in',
                      f'  let rz_ := {rad} in',
                      f'  let f_ := {fin} in',
                      f'  (if snd f_ then (ws_, fst f_) else (map (fun _ => {zeros}) ws_, pinf), snd f_).']
            continue
        lines += ['', f'{head} : {lw} * float * bool :=',
                  f'  let ws_ := map {stepped} {xs} in',
                  f'  let s_ := {state} in',
                  f'  let rz_ := {rad} in',
                  f'  let f_ := {fin} in',
                  f'  (if snd f_ then (ws_, fst f_) else (map (fun _ => {zeros}) ws_, pinf), snd f_).']
    return lines


def _bv_vector(name, limbs, radius, xs, el, part):
    """That the centers `part` of the elements and the radius are a canonical BallVector: every center
    a finite ball with the radius, or every center zero with the radius +infinity."""
    n = len(limbs)
    cs = ' '.join(rocq._paren(x) for x in rocq.tuple_parts(part, n))
    k = n
    return (f'(finite {radius} /\\ 0 <= val {radius} /\\ Forall (fun {el} => ball_finite_{k} {cs} {radius}) {xs}) \\/\n'
            f'  ({radius} = infinity prec emax false /\\ Forall (fun {el} => ball_whole_{k} {cs} {radius}) {xs})')


def bv_statement(fd, kernels, order):
    """F_seq_ieee_spec or F_lanes_ieee_spec of a ball vector (the second for every W): V1 to V4 of
    milestone2.md, "BallVector", and the flag, for canonical BallVectors and any value of a scalar that
    is not a radius."""
    if fd.ensures[0]['kind'] == 'makes_ball_vector':
        return bv_make_statement(fd, kernels, order)
    step, radius = kernels[fd.step[0]], kernels[fd.radius[0]]
    parts = [step, kernels[fd.record[0]], radius, kernels[fd.finish[0]]] + \
        ([kernels[fd.combine[0]]] if order == 'lanes' else [])
    used = set()
    for k in parts:
        used.update(_used_nans(k, kernels))
    nans = [x for x, _ in NANS if x in used]
    _, el, xs = rocq._fold_binders(fd)
    suffix = ir.ORDER_SUFFIX[order]
    etype = _fold_element_ftype(fd).replace('float', 'binary_float prec emax')
    lt = f'list ({etype})'
    vectors = {r[1]: r[2] for r in fd.requires if r[0] == 'ball_vector'}
    groups = rocq.fold_groups(fd, el)
    scalar_limbs = [v for g in fd.scalars for v in g.limbs]
    binders = (f'forall (W : nat) ({" ".join(scalar_limbs)} : binary_float prec emax) ({xs} : {lt}),'
               if order == 'lanes' else f'forall ({" ".join(scalar_limbs)} : binary_float prec emax) ({xs} : {lt}),')
    hyps = [_bv_vector(g.name, g.limbs, vectors[g.name], xs, el, groups[g.name]) for g in fd.arrays]
    # A scalar that is a power of two (bv_mul_pow2_k): finite, as for a map.
    pow2 = [r[1] for r in fd.requires if r[0] == 'power_of_two']
    w = list(fd.writes[0].limbs)
    pattern = rocq._pattern([rocq._pattern(list(g.limbs)) for g in fd.arrays])
    wp = rocq._pattern(w)
    entry = fd.ensures[0]
    members = [rocq.bv_member(b) for b in entry['balls']]
    arrays = {g.name: g for g in fd.arrays}
    scalars = {g.name: g for g in fd.scalars}
    k = len(w)
    inb = [f'in_ball_{len(arrays[v["center"]].limbs)} {" ".join(arrays[v["center"]].limbs)} {v["radius"]} '
           f'{rocq.bv_member(b)}' for b, v in entry['balls'].items()]

    def name(nm):
        if nm in entry['balls']:
            return rocq.bv_member(nm)
        return _val_sum(scalars[nm].limbs)
    setv = rocq._term(expr.parse(entry['set']), name)

    def vname(nm):
        g = arrays.get(nm) or scalars[nm]
        return _val_sum(g.limbs)
    conds = []
    for c in entry['finite_when']:
        tree = expr.parse(c['abs_le'])
        term = rocq._term(tree, vname)
        e = c['exp']
        bound = 'emax' if e == 0 else f'(emax {"-" if e < 0 else "+"} {abs(e)})'
        conds.append(f'Rabs {_paren(term)} <= bpow radix2 {bound}')
    # V4 is a statement of every length: the radii's own condition (radii_when, over the scalars) is
    # a hypothesis, which the conditions of finite_when at any entry imply.
    rconds = []
    for c in entry.get('radii_when', []):
        term = rocq._term(expr.parse(c['abs_le']), vname)
        e = c['exp']
        bound = 'emax' if e == 0 else f'(emax {"-" if e < 0 else "+"} {abs(e)})'
        rconds.append(f'Rabs {_paren(term)} <= bpow radix2 {bound}')
    section = [{'emin': EMIN, 'prec': 'prec', 'choice': 'tie_even'}[v] for v in rocq.section_args(step, kernels)]
    real_step = ' '.join([step.name] + section +
                         [f'(val {v})' for a in fd.step[1] for v in (arrays.get(a) or scalars[a]).limbs])
    rsection = [{'emin': EMIN, 'prec': 'prec', 'choice': 'tie_even'}[v]
                for v in rocq.fold_section_args([step, radius, kernels[fd.record[0]]], kernels)]
    values = []
    for g in fd.arrays:
        ps = [f'val {rocq._paren(x)}' for x in rocq.tuple_parts(groups[g.name], len(g.limbs))]
        values.append(ps[0] if len(ps) == 1 else '(' + ', '.join(ps) + ')')
    value = values[0] if len(values) == 1 else '(' + ', '.join(values) + ')'
    real_r = ' '.join([f'FoldModel.{fd.name}_radius'] + rsection + [f'(val {v})' for v in scalar_limbs] +
                      [f'(map (fun {el} => {value}) {xs})'])
    vals = f'val {w[0]}' if k == 1 else '(' + ', '.join(f'val {v}' for v in w) + ')'
    call = ' '.join([f'IeeeFoldModel.{fd.name}_{suffix}', 'prec', 'emax'] + nans + (['W'] if order == 'lanes' else []) +
                    scalar_limbs + [xs])
    what = {'sequential': 'the sequential order', 'lanes': 'the lane order, for every number of lanes W'}[order]
    wcs = ' '.join(rocq._paren(x) for x in rocq.tuple_parts('w_', k))
    lines = [f'(* {fd.name}, {what}, in the IEEE model: V1 to V4 and the flag. Status: '
             f'{"proved" if fd.ieee_theorem else "unverified"}. *)',
             f'Definition {fd.name}_{suffix}_ieee_spec : Prop :=',
             '  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)',
             '         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)' +
             (f'\n         {_binders(nans)},' if nans else ','),
             f'  ({fd.min_precision} <= prec)%Z ->',
             f'  {binders}']
    lines += [f'  ({h}) ->' for h in hyps]
    for s in pow2:
        lines += [f'  finite {s} ->', f'  (exists n : Z, val {s} = bpow radix2 n) ->']
    lines += [f"  let '(ws_, r_, flag_) := {call} in",
              f'  ((finite r_ /\\ 0 <= val r_ /\\ Forall (fun w_ => ball_finite_{k} {wcs} r_) ws_) \\/',
              f'   (r_ = infinity prec emax false /\\ Forall (fun w_ => ball_whole_{k} {wcs} r_) ws_)) /\\',
              '  (flag_ = true <-> finite r_) /\\',
              f'  Forall2 (fun {el} w_ =>']
    lines += [f'    {rocq._let(pattern, el)}'] if pattern != el else []
    lines += [f'    {rocq._let(wp, "w_")}',
              f'    forall {" ".join(members)} : R, ' + ' -> '.join(inb) + f' -> in_ball_{k} {" ".join(w)} r_ {setv})',
              f'    {xs} ws_ /\\']
    if entry.get('exact_when'):
        # Exact under conditions (bv_mul_pow2_k): a finite result whose scalars satisfy their
        # conditions and every entry those of an entry is exactly the set, entry by entry.
        econds = rocq.bv_exact_conditions(fd, entry, groups, pattern, el, xs, lambda nm: _val_sum(scalars[nm].limbs),
                                          lambda v: f'val {v}', EMIN)
        lines += ['  (finite r_ ->', '   ' + econds[0][3:]] + econds[1:] + [f'   Forall2 (fun {el} w_ =>']
        lines += [f'     {rocq._let(pattern, el)}'] if pattern != el else []
        lines += [f'     {rocq._let(wp, "w_")}',
                  f'     forall v_ : R, in_ball_{k} {" ".join(w)} r_ v_ -> exists {" ".join(members)} : R, ' +
                  ' /\\ '.join(inb) + f' /\\ v_ = {setv}) {xs} ws_) /\\']
    elif 'exact_when' in entry:
        # Exact (bv_neg_k): a finite result is exactly the set, entry by entry.
        lines += ['  (finite r_ ->', f'   Forall2 (fun {el} w_ =>']
        lines += [f'     {rocq._let(pattern, el)}'] if pattern != el else []
        lines += [f'     {rocq._let(wp, "w_")}',
                  f'     forall v_ : R, in_ball_{k} {" ".join(w)} r_ v_ -> exists {" ".join(members)} : R, ' +
                  ' /\\ '.join(inb) + f' /\\ v_ = {setv}) {xs} ws_) /\\']
    lines += ['  (finite r_ ->',
              '   ' + ' /\\ '.join(f'finite {v}' for v in scalar_limbs) + ' /\\',
              f'   Forall2 (fun {el} w_ =>']
    lines += [f'     {rocq._let(pattern, el)}'] if pattern != el else []
    # The step of a ball vector exact under conditions returns the center and its mask: the center is
    # the first component of the real model's.
    centers = f'fst ({real_step})' if fd.exact_mask is not None else real_step
    lines += [f'     {rocq._let(wp, "w_")}',
              f'     {vals} = {centers}) {xs} ws_ /\\',
              f'   val r_ = {real_r})' + (' /\\' if conds else '.')]
    if conds:
        # V4, for every length (the empty vector included); from the precision of finite_from when the
        # claim has one (a constant of the radius overflows the smallest formats below it).
        lines += ['  (' + _finite_from(entry) + ' -> '.join(f'finite {v}' for v in scalar_limbs) + ' ->',
                  '   ' + ' /\\ '.join(rconds) + ' ->',
                  f'   Forall (fun {el} =>']
        lines += [f'     {rocq._let(pattern, el)}'] if pattern != el else []
        lines += ['     ' + ' /\\ '.join(conds) + f') {xs} ->',
                  '   finite r_).']
    return lines


def _finite_from(entry):
    """The premise of V4 on the precision, when the claim says from which precision V4 holds
    (finite_from, above the fold's minimum precision): '(P <= prec)%Z -> '; otherwise nothing."""
    return f'({entry["finite_from"]} <= prec)%Z -> ' if 'finite_from' in entry else ''


def bv_conv_statement(fd, kernels):
    """F_ieee_spec of the product of two BallVectors: V1 (canonical, of n_x + n_y - 1 coefficients, none
    when a length is 0), the flag, V2 (containment coefficient by coefficient, for all members of the
    operands' balls, each entry ranging independently over its ball), V3 (a finite result has finite
    radii, the real model's coefficients and radius on the values), V4 (finite radii, the count
    within count_when, the radii within radii_when, every entry of each array and every pair of
    entries within finite_when: a finite result), for canonical BallVectors."""
    conv = kernels.folds[fd.centers]
    cf = kernels.folds[conv.coefficients]
    parts = [kernels[cf.step[0]], kernels[conv.check]] + [kernels[c[0]] for c in (fd.records[0], fd.bound, fd.radius,
                                                                                   fd.finish)]
    used = set()
    for k in parts:
        used.update(_used_nans(k, kernels))
    nans = [x for x, _ in NANS if x in used]
    x, y = fd.arrays
    xs, ys = f'{x.name}s', f'{y.name}s'
    vectors = {r[1]: r[2] for r in fd.requires if r[0] == 'ball_vector'}
    k = len(fd.writes[0].limbs)
    tx = _ftype(len(x.limbs)).replace('float', 'binary_float prec emax')
    scalar_limbs = [v for g in fd.scalars for v in g.limbs]
    hyps = [_bv_vector(g.name, g.limbs, vectors[g.name], l, g.name, g.name) for g, l in ((x, xs), (y, ys))]
    entry = fd.ensures[0]
    wcs = ' '.join(rocq._paren(v) for v in rocq.tuple_parts('w_', k))
    inb = [f'Forall2 (fun {g.name} {rocq.bv_member(g.name)} => in_ball_{len(g.limbs)} '
           f'{" ".join(rocq._paren(v) for v in rocq.tuple_parts(g.name, len(g.limbs)))} {vectors[g.name]} '
           f'{rocq.bv_member(g.name)}) {l} {l}_' for g, l in ((x, xs), (y, ys))]
    product = f'sumR (map (fun xy => fst xy * snd xy) (FoldModel.conv_terms {xs}_ {ys}_ j))'
    count = f'INR (Nat.min (length {xs}) (length {ys}))'

    def value(g):
        ps = [f'val {rocq._paren(v)}' for v in rocq.tuple_parts(g.name, len(g.limbs))]
        return ps[0] if len(ps) == 1 else '(' + ', '.join(ps) + ')'
    vx, vy = (f'(map (fun {g.name} => {value(g)}) {l})' for g, l in ((x, xs), (y, ys)))
    tie = {'emin': EMIN, 'prec': 'prec', 'choice': 'tie_even'}
    sec_c = [tie[v] for v in rocq.fold_section_args([kernels[cf.step[0]]], kernels)]
    sec_r = [tie[v] for v in rocq.fold_section_args([kernels[fd.records[0][0]], kernels[fd.bound[0]],
                                                      kernels[fd.radius[0]]], kernels)]
    wv = f'val {rocq._paren("w_")}' if k == 1 else '(' + ', '.join(f'val {rocq._paren(v)}' for v in rocq.tuple_parts('w_', k)) + ')'

    def term(text, names):
        def name(nm):
            if nm == rules_count():
                return f'({count})'
            if nm in names:
                return names[nm]
            g = next(h for h in fd.scalars if h.name == nm)
            return _val_sum(g.limbs)
        return rocq._term(expr.parse(text), name)

    def bound(e):
        b = 'emax' if e == 0 else f'(emax {"-" if e < 0 else "+"} {abs(e)})'
        return f'bpow radix2 {b}'
    conds = {'x': [], 'y': [], 'both': [], 'none': []}
    for c in entry['finite_when'] + entry.get('radii_when', []):
        names = expr.names(expr.parse(c['abs_le']))
        where = 'both' if {x.name, y.name} <= names else 'x' if x.name in names else 'y' if y.name in names else 'none'
        own = {x.name: _val_sum(x.limbs), y.name: _val_sum(y.limbs)}
        conds[where].append(f'Rabs {_paren(term(c["abs_le"], own))} <= {bound(c["exp"])}')

    def constant(text):
        def name(nm):
            return {'u': 'u prec', 'eta': f'eta {EMIN}', rules_count(): f'({count})'}[nm]
        return rocq._term(expr.parse(text), name,
                          lambda fn, kname: rocq.constant_call(fn, kname, kernels, 'u prec', f'eta {EMIN}'))
    counts = [f'{constant(c["le"])} <= {constant(c["than"])}' for c in entry.get('count_when', [])]
    lets = {g.name: rocq._let(rocq._pattern(list(g.limbs)), g.name) if rocq._pattern(list(g.limbs)) != g.name else ''
            for g in (x, y)}
    call = ' '.join([f'IeeeFoldModel.{fd.name}_conv', 'prec', 'emax'] + nans + scalar_limbs + [xs, ys])
    lines = [f'(* {fd.name}, in the IEEE model: V1 to V4 and the flag. Status: '
             f'{"proved" if fd.ieee_theorem else "unverified"}. *)',
             f'Definition {fd.name}_ieee_spec : Prop :=',
             '  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)',
             '         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)' +
             (f'\n         {_binders(nans)},' if nans else ','),
             f'  ({fd.min_precision} <= prec)%Z ->',
             f'  forall ({" ".join(scalar_limbs)} : binary_float prec emax) ({xs} {ys} : list ({tx})),']
    lines += [f'  ({h}) ->' for h in hyps]
    lines += [f"  let '(ws_, r_, flag_) := {call} in",
              f'  ((finite r_ /\\ 0 <= val r_ /\\ Forall (fun w_ => ball_finite_{k} {wcs} r_) ws_) \\/',
              f'   (r_ = infinity prec emax false /\\ Forall (fun w_ => ball_whole_{k} {wcs} r_) ws_)) /\\',
              f'  length ws_ = FoldModel.conv_length (length {xs}) (length {ys}) /\\',
              '  (flag_ = true <-> finite r_) /\\',
              f'  (forall {xs}_ {ys}_ : list R,',
              f'   {inb[0]} ->',
              f'   {inb[1]} ->',
              f'   Forall2 (fun j w_ => in_ball_{k} {wcs} r_ ({product}))',
              f'     (seq 0 (FoldModel.conv_length (length {xs}) (length {ys}))) ws_) /\\',
              '  (finite r_ ->',
              '   ' + ' /\\ '.join(f'finite {v}' for v in scalar_limbs) + ' /\\',
              f'   Forall2 (fun w_ s_ => {wv} = s_) ws_ ({" ".join([f"FoldModel.{conv.name}_conv"] + sec_c + [vx, vy])}) /\\',
              f'   val r_ = {" ".join([f"FoldModel.{fd.name}_radius"] + sec_r + [f"(val {v})" for v in scalar_limbs] + [vx, vy])})' +
              (' /\\' if entry['finite_when'] else '.')]
    if entry['finite_when']:
        hyp = ['  (' + _finite_from(entry) + ' -> '.join(f'finite {v}' for v in scalar_limbs) + ' ->']
        hyp += [f'   {c} ->' for c in counts + conds['none']]
        for where, g, l in (('x', x, xs), ('y', y, ys)):
            if conds[where]:
                body = ' /\\ '.join(conds[where])
                let = f'{lets[g.name]} ' if lets[g.name] else ''
                hyp.append(f'   Forall (fun {g.name} => {let}{body}) {l} ->')
        if conds['both']:
            body = ' /\\ '.join(conds['both'])
            lx, ly = (f'{lets[g.name]} ' if lets[g.name] else '' for g in (x, y))
            hyp.append(f'   Forall (fun {x.name} => Forall (fun {y.name} => {lx}{ly}{body}) {ys}) {xs} ->')
        lines += hyp + ['   finite r_).']
    return lines


def rules_count():
    """The name of the count in the conditions of V4 of the product of two BallVectors."""
    from . import rules
    return rules.COUNT_NAME


def bv_make_statement(fd, kernels, order):
    """F_seq_ieee_spec or F_lanes_ieee_spec of a constructor of a BallVector (makes_ball_vector;
    milestone2.md, "BallVector", "Values"), for any radius and any centers (canonical pairs for two
    limbs): the result is canonical; the flag is true exactly when the radius is finite; it is true
    exactly when the radius given is finite and not negative and every center given is finite (its
    leading limb); and then the centers written are those given, limb for limb, and the radius the
    radius given, as values."""
    parts = [kernels[fd.step[0]], kernels[fd.record[0]], kernels[fd.radius[0]], kernels[fd.finish[0]]] + \
        ([kernels[fd.combine[0]]] if order == 'lanes' else [])
    used = set()
    for k in parts:
        used.update(_used_nans(k, kernels))
    nans = [x for x, _ in NANS if x in used]
    _, el, xs = rocq._fold_binders(fd)
    suffix = ir.ORDER_SUFFIX[order]
    etype = _fold_element_ftype(fd).replace('float', 'binary_float prec emax')
    c, r = fd.arrays[0], fd.scalars[0]
    n = len(c.limbs)
    w = list(fd.writes[0].limbs)
    binders = (f'forall (W : nat) ({r.name} : binary_float prec emax) ({xs} : list ({etype})),' if order == 'lanes'
               else f'forall ({r.name} : binary_float prec emax) ({xs} : list ({etype})),')
    call = ' '.join([f'IeeeFoldModel.{fd.name}_{suffix}', 'prec', 'emax'] + nans + (['W'] if order == 'lanes' else []) +
                    [r.name, xs])
    parts_c = rocq.tuple_parts(el, n)
    wcs = ' '.join(rocq._paren(x) for x in rocq.tuple_parts('w_', n))
    what = {'sequential': 'the sequential order', 'lanes': 'the lane order, for every number of lanes W'}[order]
    lines = [f'(* {fd.name}, {what}, in the IEEE model: the constructor of a BallVector (a canonical result; the '
             'whole space exactly when the radius given is negative, a NaN or +infinity or a center given is not '
             f'finite; otherwise the centers and the radius given). Status: '
             f'{"proved" if fd.ieee_theorem else "unverified"}. *)',
             f'Definition {fd.name}_{suffix}_ieee_spec : Prop :=',
             '  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)',
             '         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)' +
             (f'\n         {_binders(nans)},' if nans else ','),
             f'  ({fd.min_precision} <= prec)%Z ->',
             f'  {binders}']
    if n > 1:
        lines.append(f'  Forall (fun {el} => canonical_{n} {" ".join(rocq._paren(x) for x in parts_c)}) {xs} ->')
    lines += [f"  let '(ws_, r_, flag_) := {call} in",
              f'  ((finite r_ /\\ 0 <= val r_ /\\ Forall (fun w_ => ball_finite_{n} {wcs} r_) ws_) \\/',
              f'   (r_ = infinity prec emax false /\\ Forall (fun w_ => ball_whole_{n} {wcs} r_) ws_)) /\\',
              '  (flag_ = true <-> finite r_) /\\',
              f'  (flag_ = true <-> finite {r.name} /\\ 0 <= val {r.name} /\\ '
              f'Forall (fun {el} => finite {rocq._paren(parts_c[0])}) {xs}) /\\',
              f'  Forall2 (fun {el} w_ =>']
    pattern = rocq._pattern(list(c.limbs))
    if pattern != el:
        lines.append(f'    {rocq._let(pattern, el)}')
    lines += [f'    {rocq._let(rocq._pattern(w), "w_")}',
              '    flag_ = true -> ' + ' /\\ '.join(f'val {a} = val {b}' for a, b in zip(w, c.limbs)) + f') {xs} ws_ /\\',
              f'  (flag_ = true -> val r_ = val {r.name}).']
    return lines


# The kernels that are the steps or the combinations of the folds: each has a statement that its
# result's leading limb is finite only if that of each of its operands is (lead_statement). Not
# those of a fold of maxima, whose maximum keeps a finite state when the element is a NaN (the
# mask of its state says so instead): the statement would be false of them.
def lead_kernels(kernels):
    names = set()
    for fd in getattr(kernels, 'folds', {}).values():
        if getattr(fd, 'is_max', False) or getattr(fd, 'is_conv', False) or getattr(fd, 'is_bv_conv', False):
            continue
        names.add(fd.step[0])
        # A map's combination is the operation and, not a kernel; its step's operands are the
        # scalars and the element, and the statement is about every one of them.
        if fd.combine and not getattr(fd, 'is_map', False) and not getattr(fd, 'is_bv', False):
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
    for fd in _folds_in_order(kernels):
        if getattr(fd, 'is_conv', False):
            lines += [''] + conv_statement(fd, kernels)
            continue
        if getattr(fd, 'is_bv_conv', False):
            lines += [''] + bv_conv_statement(fd, kernels)
            continue
        if getattr(fd, 'is_bv', False):
            for order in ir.ORDERS:
                if order in fd.orders:
                    lines += [''] + bv_statement(fd, kernels, order)
            continue
        for order in ir.ORDERS:
            if order in fd.orders:
                lines += [''] + (map_statement if getattr(fd, 'is_map', False) else fold_statement)(fd, kernels, order)
        if getattr(fd, 'is_max', False) and set(ir.ORDERS) <= set(fd.orders):
            lines += [''] + max_orders_statement(fd, kernels) + [''] + max_flag_statement(fd, kernels)
    return '\n'.join(lines) + '\n'
