"""The kernel IR: operations, kernels, the description format, and flattening.

A kernel is a straight-line program in static single assignment form over two kinds of values,
limbs (numbers of the format) and masks (docs/developer/architecture.md, "The kernel IR"). Each
kernel is described in one file, gen/kernels/NAME.kernel:

    # comment
    kernel:        NAME
    input:         x = x0 x1          a group and its limbs, most significant first
    input:         a                  a one-limb group: the limb has the group's name
    input:         mask m             a mask: one value, true or false
    input:         stored rx          entry kernels: a one-limb input that is a limb of an object
    input:         supplied y = h l   entry kernels: a multi-limb input whose limbs the program gives
    output:        z = z0 z1          (outputs likewise)
    value:         x+y                the exact real function the output approximates: names,
                                      + - *, unary minus, abs( ), parentheses
    requires:      normalized x       or: abs_ge a b, power_of_two c, nonneg r
    requires:      canonical x        (domain extended) or: ball cx rx
    ensures:       normalized z       or: leading_rounded z
    ensures:       error z R c=3/(1-4*u) k=2 t=0 [when=product_large]
    ensures:       rounded t down     the mode: nearest, down or up
    ensures:       upper r gaps=2
    ensures:       predicate m lt x y the relation lt, le or eq between two expressions
    ensures:       encloses cz rz x+y x=cx,rx y=cy,ry [finite_when=CONDITIONS]
                                      center, radius, the set, and each ball's center and radius
    ensures:       extends w core=add_2_2 lead=add [finite_when=abs_le(x,-2);abs_le(y,-2)]
                                      a full kernel: its core, the operation of T on the leading
                                      limbs, and the conditions under which the output is finite
    ensures:       represents x       a constructor: the output is the value, canonical
    ensures:       makes_ball cw rw from=c,r
                                      a constructor of a ball: center and radius outputs, from
                                      the center and radius inputs
    min_precision: 3                  optional
    theorem:       proofs/theories/Add22.v add_2_2_correct
    source:        free text
    license:       free text
    status:        unverified         or: proved
    domain:        extended           optional (default finite): operands may be infinite or NaN
    ieee_status:   unverified         the domain extended only: the IEEE-model statement's status
    ieee_theorem:  FILE NAME          the domain extended only, once that statement is proved
    entry:         yes                optional: the public headers may call it (rule R3)
    ieee_only:     yes                optional: no real-model statement (a full Ball kernel; the
                                      other full kernels and the constructors are recognized
                                      by their claims)
    ieee:          bridge spec        optional, the finite domain only: the IEEE-model statements
                                      of the kernel (proofs/gen/IeeeStatements.v): `spec`, its
                                      claims for finite operands and a finite output limb 0;
                                      `bridge`, that every value it computes is then finite and
                                      its outputs are the real model's
    ieee_finite:   abs_le(x0,-2);abs_le(y0,-2)
                                      optional, the finite domain only: conditions as in
                                      finite_when (over input names and limb names) under which
                                      every value the kernel computes is finite
    ieee_finite_result: abs_le(x+y,-2)
                                      optional: another such set of conditions
    guard_pending: a free text       optional: an entry kernel's input that is not guarded yet,
                                      and why (rule R3)
    ce_variant:    KERNEL             optional: its constant-evaluation variant
    cone_exempt:   free text          optional: why rule 4 cannot hold, and what stands in for it
    unused:        x1 free text       optional: an input the computation does not need, and why

    sh = add(x0, y0)                  one operation per line
    (s, e) = two_sum(a, b)            a call of another kernel
    g = prod(const splitter, a)       a format-dependent constant as an operand
    d = rmul(const unit_computed(add_2_2), mz)
                                      a constant computed from another kernel's claims
    m = lt(x1, 0)                     the literal zero (+0) as an operand
    f = lt(a, const inf)              +infinity; `const nan` is a quiet NaN
    g = guard(a)                      RN(a + 0): a value that enters from the program (R3)
    r0 = times_inf(t)                 t times +infinity, exact: compared or selected only (R1)
    k = prod(const up((1+u)^6), a)    an exact expression rounded up to the format: over u,
                                      eta, integers, unit(K) and tiny(K) (the constants c u^k
                                      and t eta of K's error claim), + - * / ^ and parentheses

Expressions in `ensures` are written without spaces. A condition of finite_when is
abs_le(EXPR,E), meaning |EXPR| <= 2^(qmax + p + E); several are separated by `;`, and none is
written by leaving finite_when out. This module only reads and represents descriptions; rules.py
decides whether they are acceptable.
"""
import os
import re
from dataclasses import dataclass, field

LIMB, MASK = 'limb', 'mask'

# Every operation: the kinds of its operands and of its result. Their meaning is in the
# interpreter, and their spelling in the two printers, each in one table.
OPS = {
    'add': ((LIMB, LIMB), LIMB),
    'sub': ((LIMB, LIMB), LIMB),
    'neg': ((LIMB,), LIMB),
    'abs': ((LIMB,), LIMB),
    'fma': ((LIMB, LIMB, LIMB), LIMB),
    'fms': ((LIMB, LIMB, LIMB), LIMB),
    'fnma': ((LIMB, LIMB, LIMB), LIMB),
    'prod': ((LIMB, LIMB), LIMB),
    'muladd': ((LIMB, LIMB, LIMB), LIMB),
    'lt': ((LIMB, LIMB), MASK),
    'le': ((LIMB, LIMB), MASK),
    'eq': ((LIMB, LIMB), MASK),
    'and': ((MASK, MASK), MASK),
    'or': ((MASK, MASK), MASK),
    'not': ((MASK,), MASK),
    'select': ((MASK, LIMB, LIMB), LIMB),
    'succ': ((LIMB,), LIMB),
    'pred': ((LIMB,), LIMB),
    # The value itself, under another name: how a kernel returns one of its inputs (to_nearest_2
    # returns x0), since an output must be computed by an operation (rule 3).
    'copy': ((LIMB,), LIMB),
    # RN(a + 0): the value of a, a zero made positive. A value that enters from the program passes
    # through it before any addition (rule R3); its result is an addition, which nothing can fuse.
    'guard': ((LIMB,), LIMB),
    # t times +infinity, which is exact: a NaN when t is a NaN or a zero, otherwise the infinity
    # with the sign of t. A plain multiplication, so its result may only be compared or selected
    # (rule R1); the fix-ups of the non-finite layer turn t into its infinity with it.
    'times_inf': ((LIMB,), LIMB),
    # A plain multiplication. It is accepted by the parser only so that rule R1 refuses it with a
    # reason; no printer and no interpreter knows it.
    'mul': ((LIMB, LIMB), LIMB),
}

# Operations emitted as a fused multiply-add instruction, which constant evaluation does not have.
FUSED = frozenset({'fma', 'fms', 'fnma', 'prod'})

# Format-dependent constants, as a function of the precision p. The Rocq printer spells the same
# definition in Rocq (rocq.py, CONSTANTS); the two must be read side by side.
CONSTANTS = {
    'splitter': lambda p: 2 ** ((p + 1) // 2) + 1,   # Veltkamp's multiplier 2^ceil(p/2) + 1
}
# The literal zero of a description (`lt(x1, 0)`) is the constant of this name, +0 in every format.
ZERO = '0'
# The constants that are not numbers: +infinity and a quiet NaN, which only the fix-ups of the
# non-finite layer use (docs/developer/design/milestone1.md, "IEEE-like results"). The real model
# has neither, so a kernel that names one has no real-model statement.
SPECIAL = ('inf', 'nan')
# Constants computed from the claims of another kernel K (consts.py): written `const F(K)`.
COMPUTED = ('unit_computed', 'tiny_computed')
_COMPUTED = re.compile(r'(unit_computed|tiny_computed)\(([a-z][a-z0-9_]*)\)\Z')


def computed(name):
    """(F, K) for the name of a computed constant F(K), or None."""
    m = _COMPUTED.match(name)
    return (m.group(1), m.group(2)) if m else None


# A constant defined by an exact expression, rounded up to the format: written `const up(EXPR)`,
# EXPR over u, eta, integers, unit(K) and tiny(K), with + - * /, parentheses and integer powers
# (consts.py computes it; expr.py parses EXPR).
_UP = re.compile(r'up\((.+)\)\Z')


def up(name):
    """The expression of a constant up(EXPR), or None."""
    m = _UP.match(name)
    return m.group(1) if m else None


KERNEL_NAME = re.compile(r'[a-z][a-z0-9_]*\Z')
# Value names have no underscore: flattening names an inlined value CALLER_CALLEE, which can then
# never collide with a name written in a description.
VALUE_NAME = re.compile(r'[a-z][a-z0-9]*\Z')


class DescriptionError(Exception):
    pass


@dataclass(frozen=True)
class Operand:
    name: str
    const: bool = False   # a constant of the format: a name of CONSTANTS, ZERO, or computed

    def __str__(self):
        if self.const and self.name != ZERO:
            return f'const {self.name}'
        return self.name


@dataclass(frozen=True)
class Stmt:
    dsts: tuple   # names it defines: one for an operation, one per callee output limb for a call
    op: str       # a key of OPS, or the name of the called kernel
    args: tuple   # Operands
    line: int

    @property
    def is_call(self):
        return self.op not in OPS


@dataclass(frozen=True)
class Group:
    name: str
    limbs: tuple
    kind: str = LIMB     # MASK: one value, the group's name


@dataclass
class Kernel:
    name: str
    path: str
    inputs: list = field(default_factory=list)     # Groups
    outputs: list = field(default_factory=list)    # Groups
    body: list = field(default_factory=list)       # Stmts
    value: str = None
    requires: list = field(default_factory=list)   # tuples: ('normalized', g), ('abs_ge', g, h), ...
    ensures: list = field(default_factory=list)    # dicts in the claims schema's shape
    min_precision: int = None
    theorem: tuple = None                          # (file, name)
    source: str = None
    license: str = None
    status: str = None
    ce_variant: str = None
    cone_exempt: str = None
    unused: dict = field(default_factory=dict)     # input value -> why the computation ignores it
    # The non-finite layer (architecture.md, "Claims of the non-finite layer").
    domain: str = None                             # None (finite) or 'extended', as written
    ieee_status: str = None
    ieee_theorem: tuple = None                     # (file, name)
    ieee_only: bool = False                        # no real-model statement (a full Ball kernel)
    # The IEEE-model statements of a kernel of the finite domain (ieee.py): which of `bridge` and
    # `spec`, and the thresholds under which every value it computes is finite.
    ieee: tuple = ()
    ieee_finite: list = field(default_factory=list)          # conditions, as in finite_when
    ieee_finite_result: list = field(default_factory=list)
    # Rule R3 (architecture.md, "The kernel IR").
    entry: bool = False
    stored: set = field(default_factory=set)       # one-limb input groups that are limbs of objects
    supplied: set = field(default_factory=set)     # multi-limb input groups the program gives
    guard_pending: dict = field(default_factory=dict)   # input value -> why it is not guarded yet

    @property
    def extended(self):
        return self.domain == 'extended'

    @property
    def real_model(self):
        """Whether the kernel has a statement in the real model. A full kernel or a constructor
        (architecture.md, "Claims of the non-finite layer") has the IEEE-model statement only: it
        says how non-finite values come out, which the real model cannot. They are recognized by
        what they claim: nothing but `extends`, `represents` and `makes_ball` (neg_2 and abs_2
        claim `represents` next to `normalized` and `error`, and keep their real-model
        statement), or, for the full Ball kernels, whose claims have the shape of ball_neg_k's,
        by `ieee_only: yes`."""
        return not (self.ieee_only or (bool(self.ensures) and
                                       all(e['kind'] in NON_FINITE_ONLY for e in self.ensures)))

    def program_values(self):
        """The input values that enter from the program, for rule R3: in an entry kernel, every
        one-limb limb input not declared stored, and the limbs of multi-limb inputs declared
        supplied. Empty for a kernel that is not an entry kernel."""
        if not self.entry:
            return []
        out = []
        for g in self.inputs:
            if g.kind != LIMB:
                continue
            if (len(g.limbs) == 1 and g.name not in self.stored) or g.name in self.supplied:
                out += list(g.limbs)
        return out

    @property
    def input_limbs(self):
        """Every input value, masks included, in order: the kernel's parameters."""
        return [v for g in self.inputs for v in g.limbs]

    @property
    def output_limbs(self):
        return [v for g in self.outputs for v in g.limbs]

    @property
    def input_kinds(self):
        return [g.kind for g in self.inputs for _ in g.limbs]

    @property
    def output_kinds(self):
        return [g.kind for g in self.outputs for _ in g.limbs]

    @property
    def limbs(self):
        return max(len(g.limbs) for g in self.inputs + self.outputs)


# The IEEE-model statements a kernel of the finite domain may ask for (ieee.py, `ieee:`).
IEEE_STATEMENTS = ('bridge', 'spec')

# The claims that only the non-finite layer has: a kernel that claims nothing else has no
# real-model statement (Kernel.real_model).
NON_FINITE_ONLY = ('extends', 'represents', 'makes_ball')

INPUT_CLASSES = ('stored', 'supplied')   # rule R3: where an entry kernel's input comes from


def _group(text, where, classes=()):
    """A group, and the class written before it (one of `classes`, or None)."""
    words = text.split()
    if len(words) == 2 and words[0] == 'mask' and VALUE_NAME.match(words[1]):
        return Group(words[1], (words[1],), MASK), None
    cls = None
    if len(words) > 1 and words[0] in classes:
        cls, text = words[0], text.strip()[len(words[0]):]
    m = re.fullmatch(r'([a-z][a-z0-9]*)(?:\s*=\s*([a-z0-9 ]+))?', text.strip())
    if not m:
        raise DescriptionError(f'{where}: expected "NAME", "NAME = LIMB LIMB ..." or "mask NAME"'
                               f'{", after stored or supplied" if classes else ""}, got {text!r}')
    limbs = tuple(m.group(2).split()) if m.group(2) else (m.group(1),)
    return Group(m.group(1), limbs), cls


def _finite_when(text, where):
    """abs_le(EXPR,E);abs_le(EXPR,E) as [{'abs_le': EXPR, 'exp': E}, ...]."""
    out = []
    for part in text.split(';') if text else ():
        m = re.fullmatch(r'abs_le\((.+),(-?[0-9]+)\)', part)
        if not m:
            raise DescriptionError(f'{where}: a condition of finite_when is abs_le(EXPR,E), got {part!r}')
        out.append({'abs_le': m.group(1), 'exp': int(m.group(2))})
    return out


def _ensures(words, where):
    kind = words[0] if words else None
    if kind in ('normalized', 'leading_rounded', 'represents') and len(words) == 2:
        return {'kind': kind, 'of': words[1]}
    if kind == 'extends' and len(words) >= 2:
        entry = {'kind': kind, 'of': words[1], 'core': None, 'lead': None, 'finite_when': None}
        for w in words[2:]:
            key, eq, val = w.partition('=')
            if not eq or key not in ('core', 'lead', 'finite_when') or entry[key] is not None:
                raise DescriptionError(f'{where}: bad or repeated field {w!r} in extends entry')
            entry[key] = _finite_when(val, where) if key == 'finite_when' else val
        for key in ('core', 'lead'):
            if not entry[key]:
                raise DescriptionError(f'{where}: an extends entry needs {key}=')
        if entry['finite_when'] is None:
            entry['finite_when'] = []
        return entry
    if kind == 'makes_ball' and len(words) == 4:
        m = re.fullmatch(r'from=([a-z][a-z0-9]*),([a-z][a-z0-9]*)', words[3])
        if not m:
            raise DescriptionError(f'{where}: expected "makes_ball CENTER RADIUS from=CENTER,RADIUS"')
        return {'kind': kind, 'center': words[1], 'radius': words[2],
                'from': {'center': m.group(1), 'radius': m.group(2)}}
    if kind == 'rounded' and len(words) == 3:
        return {'kind': kind, 'of': words[1], 'mode': words[2]}
    if kind == 'upper' and len(words) == 3 and words[2].startswith('gaps='):
        return {'kind': kind, 'of': words[1], 'gaps': words[2][len('gaps='):]}
    if kind == 'predicate' and len(words) == 5:
        return {'kind': kind, 'of': words[1], 'rel': words[2], 'args': words[3:5]}
    if kind == 'encloses' and len(words) >= 5:
        balls, finite_when = {}, None
        for w in words[4:]:
            if w.startswith('finite_when=') and finite_when is None:
                finite_when = _finite_when(w[len('finite_when='):], where)
                continue
            m = re.fullmatch(r'([a-z][a-z0-9]*)=([a-z][a-z0-9]*),([a-z][a-z0-9]*)', w)
            if not m or m.group(1) in balls:
                raise DescriptionError(f'{where}: bad or repeated ball {w!r}: NAME=CENTER,RADIUS')
            balls[m.group(1)] = {'center': m.group(2), 'radius': m.group(3)}
        entry = {'kind': kind, 'center': words[1], 'radius': words[2], 'set': words[3], 'balls': balls}
        if finite_when is not None:
            entry['finite_when'] = finite_when
        return entry
    if kind == 'error' and len(words) >= 3:
        entry = {'kind': 'error', 'of': words[1], 'form': words[2],
                 'c': None, 'k': None, 't': None, 'when': None}
        for w in words[3:]:
            key, eq, val = w.partition('=')
            if not eq or key not in ('c', 'k', 't', 'when') or entry[key] is not None:
                raise DescriptionError(f'{where}: bad or repeated field {w!r} in error entry')
            entry[key] = val
        if entry['k'] is not None:
            if not re.fullmatch(r'[0-9]+', entry['k']):
                raise DescriptionError(f'{where}: k must be an integer, got {entry["k"]!r}')
            entry['k'] = int(entry['k'])
        return entry
    raise DescriptionError(f'{where}: cannot read ensures entry {" ".join(words)!r}')


# The operands may hold one level of parentheses, for `const unit_computed(K)`.
_HEAD = re.compile(r'(?:\(\s*(?P<many>[^()]*)\)|(?P<one>\S+))\s*=\s*(?P<op>[a-z][a-z0-9_]*)\(')


def _arguments(text, where):
    """The operands between a call's parentheses, split at the commas outside any parentheses (an
    operand `const up(EXPR)` holds an expression with parentheses of its own)."""
    out, depth, start = [], 0, 0
    for i, ch in enumerate(text):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth < 0:
                raise DescriptionError(f'{where}: unbalanced parentheses in {text!r}')
        elif ch == ',' and depth == 0:
            out.append(text[start:i])
            start = i + 1
    if depth:
        raise DescriptionError(f'{where}: unbalanced parentheses in {text!r}')
    out.append(text[start:])
    return [x.strip() for x in out] if text.strip() else []


def _stmt(text, where, lineno):
    m = _HEAD.match(text)
    if not m or not text.endswith(')'):
        raise DescriptionError(f'{where}: expected "DST = OP(ARGS)" or "(DST, ...) = KERNEL(ARGS)", got {text!r}')
    dsts = tuple(d.strip() for d in (m.group('many') or m.group('one')).split(','))
    args = []
    for a in _arguments(text[m.end():-1], where):
        words = a.split()
        if len(words) >= 2 and words[0] == 'const':
            # A constant's name holds no space: one inside an expression means nothing.
            args.append(Operand(''.join(words[1:]), const=True))
        elif words == [ZERO]:
            args.append(Operand(ZERO, const=True))
        elif len(words) == 1:
            args.append(Operand(words[0]))
        else:
            raise DescriptionError(f'{where}: bad operand {a!r}')
    return Stmt(dsts, m.group('op'), tuple(args), lineno)


def parse_kernel(text, path):
    k = Kernel(name=None, path=path)
    single = {'kernel', 'value', 'min_precision', 'theorem', 'source', 'license', 'status',
              'ce_variant', 'cone_exempt', 'domain', 'ieee_status', 'ieee_theorem', 'entry', 'ieee_only',
              'ieee', 'ieee_finite', 'ieee_finite_result'}
    seen = set()
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split('#', 1)[0].strip()
        where = f'{path}:{lineno}'
        if not line:
            continue
        header = re.fullmatch(r'([a-z_]+):\s*(.*)', line)
        if not header:
            k.body.append(_stmt(line, where, lineno))
            continue
        key, val = header.group(1), header.group(2).strip()
        if key in single:
            if key in seen:
                raise DescriptionError(f'{where}: {key} given twice')
            seen.add(key)
        if key == 'kernel':
            k.name = val
        elif key == 'input':
            g, cls = _group(val, where, INPUT_CLASSES)
            k.inputs.append(g)
            if cls:
                getattr(k, cls).add(g.name)
        elif key == 'output':
            k.outputs.append(_group(val, where)[0])
        elif key == 'value':
            k.value = val
        elif key == 'requires':
            words = val.split()
            if not words:
                raise DescriptionError(f'{where}: empty requires')
            k.requires.append(tuple(words))
        elif key == 'ensures':
            k.ensures.append(_ensures(val.split(), where))
        elif key == 'min_precision':
            if not re.fullmatch(r'[0-9]+', val):
                raise DescriptionError(f'{where}: min_precision must be an integer')
            k.min_precision = int(val)
        elif key in ('theorem', 'ieee_theorem'):
            parts = val.split()
            if len(parts) != 2:
                raise DescriptionError(f'{where}: expected "{key}: FILE NAME"')
            setattr(k, key, tuple(parts))
        elif key in ('source', 'license', 'status', 'ce_variant', 'cone_exempt', 'domain', 'ieee_status'):
            setattr(k, key, val)
        elif key == 'ieee':
            words = val.split()
            if not words or any(w not in IEEE_STATEMENTS for w in words) or len(set(words)) < len(words):
                raise DescriptionError(f'{where}: expected "ieee: " and some of {", ".join(IEEE_STATEMENTS)}')
            k.ieee = tuple(w for w in IEEE_STATEMENTS if w in words)
        elif key in ('ieee_finite', 'ieee_finite_result'):
            conditions = _finite_when(val.replace(' ', ''), where)
            if not conditions:
                raise DescriptionError(f'{where}: {key} needs at least one condition')
            setattr(k, key, conditions)
        elif key in ('entry', 'ieee_only'):
            if val != 'yes':
                raise DescriptionError(f'{where}: expected "{key}: yes" (leave the line out otherwise)')
            setattr(k, key, True)
        elif key in ('unused', 'guard_pending'):
            name, _, why = val.partition(' ')
            table = getattr(k, key)
            if not name or not why.strip() or name in table:
                raise DescriptionError(f'{where}: expected "{key}: INPUT REASON", once per input')
            table[name] = why.strip()
        else:
            raise DescriptionError(f'{where}: unknown key {key!r}')
    if k.name is None:
        raise DescriptionError(f'{path}: no "kernel:" line')
    if k.extended:
        # In the extended domain an encloses entry always says when the ball is finite (an empty
        # list when no condition is proved), as extends does.
        for e in k.ensures:
            if e['kind'] == 'encloses':
                e.setdefault('finite_when', [])
    if not KERNEL_NAME.match(k.name):
        raise DescriptionError(f'{path}: bad kernel name {k.name!r}')
    if not k.inputs or not k.outputs:
        raise DescriptionError(f'{path}: a kernel needs at least one input and one output')
    return k


def load_kernels(directory):
    """Every *.kernel file of a directory, as {name: Kernel} in output order (see `ordered`)."""
    kernels = {}
    for fn in sorted(os.listdir(directory)):
        if not fn.endswith('.kernel'):
            continue
        path = os.path.join(directory, fn)
        with open(path, encoding='utf-8') as f:
            k = parse_kernel(f.read(), fn)
        if k.name in kernels:
            raise DescriptionError(f'{fn}: kernel {k.name} is also defined in {kernels[k.name].path}')
        if fn != k.name + '.kernel':
            raise DescriptionError(f'{fn}: kernel {k.name} must be in {k.name}.kernel')
        kernels[k.name] = k
    return ordered(kernels)


def ordered(kernels):
    """Callees before callers (Rocq needs it), otherwise by input limb count, then by name."""
    out = {}

    def visit(name, path):
        if name in out:
            return
        if name in path:
            raise DescriptionError(f'kernel {name}: calls itself through {" -> ".join(path)}')
        for st in kernels[name].body:
            if st.is_call and st.op in kernels:
                visit(st.op, path + (name,))
        out[name] = kernels[name]

    for name in sorted(kernels, key=lambda n: (max(len(g.limbs) for g in kernels[n].inputs), n)):
        visit(name, ())
    return out


@dataclass(frozen=True)
class Prim:
    """One operation of a flattened kernel."""
    dst: str
    op: str
    args: tuple


@dataclass(frozen=True)
class CallMark:
    """Where an inlined call starts, in flattened names (the C++ printer writes it as a comment)."""
    dsts: tuple
    callee: str
    args: tuple


def flatten(kernel, kernels):
    """The kernel's body with every call replaced by the callee's body, as the C++ is emitted.

    Names the kernel defines are kept. A value defined inside a callee is renamed D_V, where D is
    the first name the call site defines and V the value's name in the callee (recursively), so
    that every name of the result is unique. Returns a list of Prim and CallMark.
    """
    items = []

    def inline(k, env, outnames, prefix):
        local = dict(env)

        def name_of(v):
            return outnames[v] if v in outnames else (f'{prefix}_{v}' if prefix else v)

        for st in k.body:
            args = tuple(a if a.const else local[a.name] for a in st.args)
            names = tuple(name_of(d) for d in st.dsts)
            for d, n in zip(st.dsts, names):
                local[d] = Operand(n)
            if st.is_call:
                callee = kernels[st.op]
                items.append(CallMark(names, st.op, args))
                inline(callee, dict(zip(callee.input_limbs, args)),
                       dict(zip(callee.output_limbs, names)), names[0])
            else:
                items.append(Prim(names[0], st.op, args))

    inline(kernel, {v: Operand(v) for v in kernel.input_limbs},
           {v: v for v in kernel.output_limbs}, '')
    return items


def prims(kernel, kernels):
    return [it for it in flatten(kernel, kernels) if isinstance(it, Prim)]


def muladd_sites(kernel, kernels):
    """Flattened names of the kernel's muladd values: each is a choice the compiler makes."""
    return [p.dst for p in prims(kernel, kernels) if p.op == 'muladd']


def kinds(kernel, kernels):
    """The kind (LIMB or MASK) of every flattened value."""
    out = dict(zip(kernel.input_limbs, kernel.input_kinds))
    for p in prims(kernel, kernels):
        out[p.dst] = OPS[p.op][1]
    return out


def constants(kernel):
    """The names of the constants the kernel's own statements use (not its callees')."""
    return sorted({a.name for st in kernel.body for a in st.args if a.const})


def flops(kernel, kernels):
    """Floating-point operations after inlining; an FMA counts as one, and so do a guard and a
    multiplication by infinity."""
    arith = {'add', 'sub', 'fma', 'fms', 'fnma', 'prod', 'muladd', 'guard', 'times_inf'}
    return sum(1 for p in prims(kernel, kernels) if p.op in arith)
