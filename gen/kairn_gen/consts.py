"""The exact value of every constant a kernel can name, in a format (p, qmin, qmax).

- `splitter`: ir.CONSTANTS, a function of p.
- `0`: the literal zero, +0.
- `unit_computed(K)`, `tiny_computed(K)` (architecture.md, "Claims of the second wave"): K's bound
  |output - value| <= unit |value| + tiny, with unit = c u^k and tiny = t eta from K's error entry,
  turned into one relative to the computed output: unit / (1 - unit) and tiny / (1 - unit), each
  rounded up to a number of the format. A ball kernel's radius adds them to cover the error of its
  center. They are computed here with integers and fractions only, for any format, so that the
  C++ literals, the interpreter and the tests use the same numbers; the Rocq model states the same
  definition over the reals (rocq.py).
- `up(EXPR)`: the smallest number of the format not below EXPR > 0, an exact rational expression
  over u, eta, integers, unit(K) and tiny(K) (c u^k and t eta of K's error entry), with + - * /,
  parentheses and integer powers.
"""
from fractions import Fraction

from . import expr, ir


class ConstError(Exception):
    pass


def source_bound(k):
    """The error entry of K that its computed constants come from: the only one, of form R and
    without a condition. Raises ConstError otherwise."""
    errors = [e for e in k.ensures if e['kind'] == 'error']
    if len(errors) != 1:
        raise ConstError(f'{k.name} has {len(errors)} error entries; its computed constants need '
                         'exactly one')
    e = errors[0]
    if e['form'] != 'R' or e['when'] is not None:
        raise ConstError(f'the error entry of {k.name} must be of form R and unconditional to give '
                         'computed constants')
    return e


def round_up(x, p, qmin, qmax):
    """The smallest number of the format not below x >= 0, or None when there is none (overflow)."""
    if x == 0:
        return Fraction(0)
    e = x.numerator.bit_length() - x.denominator.bit_length()   # 2^(e-1) < x < 2^(e+1)
    if Fraction(2) ** e > x:
        e -= 1                                                 # now 2^e <= x < 2^(e+1)
    q = max(e - p + 1, qmin)                                   # the quantum of numbers near x
    scale = Fraction(2) ** q
    t = x / scale
    m = -((-t.numerator) // t.denominator)                     # ceil: a carry to 2^p is still exact
    if m * scale > (2 ** p - 1) * Fraction(2) ** qmax:
        return None
    return m * scale


def computed(fn, k, p, qmin, qmax):
    """unit_computed(K) or tiny_computed(K) in format (p, qmin, qmax), as a Fraction."""
    e = source_bound(k)
    if k.min_precision is not None and p < k.min_precision:
        raise ConstError(f'{fn}({k.name}) is not defined for precision {p}: the claims of '
                         f'{k.name} hold from precision {k.min_precision} on')
    u = Fraction(1, 2 ** p)
    try:
        unit = expr.evaluate(expr.parse(e['c']), {'u': u}) * u ** e['k']
        tiny = expr.evaluate(expr.parse(e['t']), {}) * Fraction(2) ** qmin
    except expr.ExprError as err:
        raise ConstError(f'{fn}({k.name}) at precision {p}: {err}')
    if not 0 <= unit < 1 or tiny < 0:
        raise ConstError(f'{fn}({k.name}) at precision {p}: needs 0 <= unit < 1 and tiny >= 0')
    v = round_up((unit if fn == 'unit_computed' else tiny) / (1 - unit), p, qmin, qmax)
    if v is None:
        raise ConstError(f'{fn}({k.name}) overflows the format ({p}, {qmin}, {qmax})')
    return v


UP_TREES = {'int', 'name', 'add', 'sub', 'mul', 'div', 'neg', 'pow', 'call'}
UP_NAMES = {'u', 'eta'}


def up_tree(text):
    """The parsed EXPR of a constant up(EXPR), checked for its vocabulary: u, eta, integers,
    unit(K) and tiny(K), + - * /, parentheses and integer powers. Raises ConstError."""
    try:
        tree = expr.parse(text)
    except expr.ExprError as e:
        raise ConstError(f'up({text}): {e}')

    def walk(t):
        if t[0] not in UP_TREES:
            raise ConstError(f'up({text}): {t[0]} is not allowed (only + - * /, ^ INTEGER, u, eta, '
                             'integers, unit(K) and tiny(K))')
        for x in t[1:]:
            if isinstance(x, tuple):
                walk(x)
    walk(tree)
    extra = expr.names(tree) - UP_NAMES
    if extra:
        raise ConstError(f'up({text}): unknown name {", ".join(sorted(extra))}')
    return tree


def up_exact(text, kernels, p, qmin):
    """The exact value of EXPR in up(EXPR), for precision p and underflow threshold 2^qmin."""
    tree = up_tree(text)
    u, eta = Fraction(1, 2 ** p), Fraction(2) ** qmin
    env = {'u': u, 'eta': eta}
    for fn, kname in expr.calls(tree):
        k = kernels.get(kname)
        if k is None:
            raise ConstError(f'up({text}): {kname} is not a kernel')
        e = source_bound(k)
        if k.min_precision is not None and p < k.min_precision:
            raise ConstError(f'up({text}) is not defined for precision {p}: the claims of {kname} hold '
                             f'from precision {k.min_precision} on')
        try:
            env[f'unit({kname})'] = expr.evaluate(expr.parse(e['c']), {'u': u}) * u ** e['k']
            env[f'tiny({kname})'] = expr.evaluate(expr.parse(e['t']), {}) * eta
        except expr.ExprError as err:
            raise ConstError(f'up({text}): the bound of {kname}: {err}')
    try:
        return expr.evaluate(tree, env)
    except expr.ExprError as err:
        raise ConstError(f'up({text}): {err}')


# The constants of a claim (rel and abs of outward, Milestone 2): the language of up(EXPR), and up( )
# itself inside, a constant as the format rounds it.
CLAIM_TREES = UP_TREES | {'up'}


def claim_tree(text):
    """The parsed constant of a claim, checked for its vocabulary. Raises ConstError."""
    try:
        tree = expr.parse(text)
    except expr.ExprError as e:
        raise ConstError(f'{text}: {e}')

    def walk(t, inside):
        if t[0] not in (UP_TREES if inside else CLAIM_TREES):
            raise ConstError(f'{text}: {t[0]} is not allowed (only + - * /, ^ INTEGER, u, eta, integers, '
                             'unit(K), tiny(K), and up(EXPR) of those)')
        for x in t[1:]:
            if isinstance(x, tuple):
                walk(x, inside or t[0] == 'up')
    walk(tree, False)
    extra = expr.names(tree) - UP_NAMES
    if extra:
        raise ConstError(f'{text}: unknown name {", ".join(sorted(extra))}')
    return tree


def ups(tree):
    """The parsed EXPR of every up(EXPR) inside a claim's constant. A constant of a kernel, const
    up(EXPR), is the same constant when its EXPR parses to the same tree (up_tree)."""
    if tree[0] == 'up':
        return [tree[1]]
    return [x for t in tree[1:] if isinstance(t, tuple) for x in ups(t)]


def claim_constant(text, kernels, p, qmin, qmax):
    """The exact value of a constant of a claim in format (p, qmin, qmax): its expression with each
    up(EXPR) rounded up to the format (consts.value), unit(K) and tiny(K) from K's error claim."""
    tree = claim_tree(text)
    u, eta = Fraction(1, 2 ** p), Fraction(2) ** qmin
    env = {'u': u, 'eta': eta}
    for fn, kname in expr.calls(tree):
        k = kernels.get(kname)
        if k is None:
            raise ConstError(f'{text}: {kname} is not a kernel')
        e = source_bound(k)
        env[f'unit({kname})'] = expr.evaluate(expr.parse(e['c']), {'u': u}) * u ** e['k']
        env[f'tiny({kname})'] = expr.evaluate(expr.parse(e['t']), {}) * eta

    def up(x):
        if not x > 0:
            raise ConstError(f'{text}: an up( ) inside it is {x} in the format ({p}, {qmin}, {qmax}); it must be positive')
        v = round_up(x, p, qmin, qmax)
        if v is None:
            raise ConstError(f'{text}: an up( ) inside it overflows the format ({p}, {qmin}, {qmax})')
        return v
    try:
        return expr.evaluate(tree, env, up)
    except expr.ExprError as err:
        raise ConstError(f'{text}: {err}')


def value(name, kernels, p, qmin, qmax):
    """The exact value of constant `name` in format (p, qmin, qmax), as a Fraction."""
    if name == ir.ZERO:
        return Fraction(0)
    text = ir.up(name)
    if text is not None:
        x = up_exact(text, kernels, p, qmin)
        if not x > 0:
            raise ConstError(f'{name} is {x} in the format ({p}, {qmin}, {qmax}); it must be positive')
        v = round_up(x, p, qmin, qmax)
        if v is None:
            raise ConstError(f'{name} overflows the format ({p}, {qmin}, {qmax})')
        return v
    if name in ir.CONSTANTS:
        v = Fraction(ir.CONSTANTS[name](p))
        if round_up(v, p, qmin, qmax) != v:
            raise ConstError(f'constant {name} = {v} is not a number of the format ({p}, {qmin}, {qmax})')
        return v
    c = ir.computed(name)
    if c is None or c[1] not in kernels:
        raise ConstError(f'unknown constant {name!r}')
    return computed(c[0], kernels[c[1]], p, qmin, qmax)
