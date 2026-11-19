"""The kernel IR: operations, kernels, the description format, and flattening.

A kernel is a straight-line program in static single assignment form over two kinds of values,
limbs (numbers of the format) and masks (docs/developer/architecture.md, "The kernel IR"). Each
kernel is described in one file, gen/kernels/NAME.kernel:

    # comment
    kernel:        NAME
    input:         x = x0 x1          a group and its limbs, most significant first
    input:         a                  a one-limb group: the limb has the group's name
    output:        z = z0 z1
    value:         x+y                the exact real function the output approximates
    requires:      normalized x       or: abs_ge a b
    ensures:       normalized z       or: leading_rounded z
    ensures:       error z R c=3/(1-4*u) k=2 t=0 [when=product_large]
    min_precision: 3                  optional
    theorem:       proofs/theories/Add22.v add_2_2_correct
    source:        free text
    license:       free text
    status:        unverified         or: proved
    ce_variant:    KERNEL             optional: its constant-evaluation variant
    cone_exempt:   free text          optional: why rule 4 cannot hold, and what stands in for it

    sh = add(x0, y0)                  one operation per line
    (s, e) = two_sum(a, b)            a call of another kernel
    g = prod(const splitter, a)       a format-dependent constant as an operand

This module only reads and represents descriptions; rules.py decides whether they are acceptable.
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

KERNEL_NAME = re.compile(r'[a-z][a-z0-9_]*\Z')
# Value names have no underscore: flattening names an inlined value CALLER_CALLEE, which can then
# never collide with a name written in a description.
VALUE_NAME = re.compile(r'[a-z][a-z0-9]*\Z')


class DescriptionError(Exception):
    pass


@dataclass(frozen=True)
class Operand:
    name: str
    const: bool = False

    def __str__(self):
        return f'const {self.name}' if self.const else self.name


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


@dataclass
class Kernel:
    name: str
    path: str
    inputs: list = field(default_factory=list)     # Groups
    outputs: list = field(default_factory=list)    # Groups
    body: list = field(default_factory=list)       # Stmts
    value: str = None
    requires: list = field(default_factory=list)   # ('normalized', g) or ('abs_ge', g, h)
    ensures: list = field(default_factory=list)    # dicts in the claims schema's shape
    min_precision: int = None
    theorem: tuple = None                          # (file, name)
    source: str = None
    license: str = None
    status: str = None
    ce_variant: str = None
    cone_exempt: str = None

    @property
    def input_limbs(self):
        return [v for g in self.inputs for v in g.limbs]

    @property
    def output_limbs(self):
        return [v for g in self.outputs for v in g.limbs]

    @property
    def limbs(self):
        return max(len(g.limbs) for g in self.inputs + self.outputs)


def _group(text, where):
    m = re.fullmatch(r'([a-z][a-z0-9]*)(?:\s*=\s*([a-z0-9 ]+))?', text.strip())
    if not m:
        raise DescriptionError(f'{where}: expected "NAME" or "NAME = LIMB LIMB ...", got {text!r}')
    limbs = tuple(m.group(2).split()) if m.group(2) else (m.group(1),)
    return Group(m.group(1), limbs)


def _ensures(words, where):
    kind = words[0] if words else None
    if kind in ('normalized', 'leading_rounded') and len(words) == 2:
        return {'kind': kind, 'of': words[1]}
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


_STMT = re.compile(r'(?:\(\s*(?P<many>[^()]*)\)|(?P<one>\S+))\s*=\s*(?P<op>[a-z][a-z0-9_]*)\((?P<args>[^()]*)\)')


def _stmt(text, where, lineno):
    m = _STMT.fullmatch(text)
    if not m:
        raise DescriptionError(f'{where}: expected "DST = OP(ARGS)" or "(DST, ...) = KERNEL(ARGS)", got {text!r}')
    dsts = tuple(d.strip() for d in (m.group('many') or m.group('one')).split(','))
    args = []
    for a in (x.strip() for x in m.group('args').split(',')) if m.group('args').strip() else ():
        words = a.split()
        if len(words) == 2 and words[0] == 'const':
            args.append(Operand(words[1], const=True))
        elif len(words) == 1:
            args.append(Operand(words[0]))
        else:
            raise DescriptionError(f'{where}: bad operand {a!r}')
    return Stmt(dsts, m.group('op'), tuple(args), lineno)


def parse_kernel(text, path):
    k = Kernel(name=None, path=path)
    single = {'kernel', 'value', 'min_precision', 'theorem', 'source', 'license', 'status',
              'ce_variant', 'cone_exempt'}
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
            k.inputs.append(_group(val, where))
        elif key == 'output':
            k.outputs.append(_group(val, where))
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
        elif key == 'theorem':
            parts = val.split()
            if len(parts) != 2:
                raise DescriptionError(f'{where}: expected "theorem: FILE NAME"')
            k.theorem = tuple(parts)
        elif key in ('source', 'license', 'status', 'ce_variant', 'cone_exempt'):
            setattr(k, key, val)
        else:
            raise DescriptionError(f'{where}: unknown key {key!r}')
    if k.name is None:
        raise DescriptionError(f'{path}: no "kernel:" line')
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
    out = {v: LIMB for v in kernel.input_limbs}
    for p in prims(kernel, kernels):
        out[p.dst] = OPS[p.op][1]
    return out


def flops(kernel, kernels):
    """Floating-point operations after inlining; an FMA counts as one."""
    arith = {'add', 'sub', 'fma', 'fms', 'fnma', 'prod', 'muladd'}
    return sum(1 for p in prims(kernel, kernels) if p.op in arith)
