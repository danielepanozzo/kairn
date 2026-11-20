"""Rational expressions: the `c` and `t` of an error claim, a kernel's `value`, the EXPR of a
constant `up(EXPR)`, and the expressions of a condition `exact_when`.

A small explicit parser, so that no claim text is ever evaluated as Python:

    expr  := term (('+' | '-') term)*
    term  := unary (('*' | '/') unary)*
    unary := '-' unary | power
    power := atom ('^' ['-'] INTEGER)?
    atom  := INTEGER | 'abs' '(' expr ')' | ('unit' | 'tiny') '(' NAME ')' | NAME '[' INTEGER ']'
           | NAME | '(' expr ')'

The result is a tree of tuples: ('int', n), ('name', s), ('limb', s, i) for limb i of the input
group s (0 the leading limb), ('neg', a), ('abs', a), ('pow', a, n) with an integer n, ('call', f,
K) for unit(K) and tiny(K), and (op, a, b) for op in add, sub, mul, div. Where each kind of tree may
appear is the rules' business: only constants up(EXPR) have powers and calls, and only the
conditions of exact_when name a limb.
"""
import re
from fractions import Fraction

# Every character that is not white space is part of some token (the last group catches the rest).
_TOKEN = re.compile(r'\s*(?:([0-9]+)|([A-Za-z][A-Za-z0-9_]*)|(\S))')


# The functions of a constant up(EXPR): unit(K) = c u^k and tiny(K) = t eta of K's error claim.
CALLS = ('unit', 'tiny')


class ExprError(Exception):
    pass


def parse(text):
    tokens = []
    for m in _TOKEN.finditer(text):
        if m.group(1):
            tokens.append(('int', int(m.group(1))))
        elif m.group(2):
            tokens.append(('name', m.group(2)))
        elif m.group(3):
            if m.group(3) not in '+-*/()^[]':
                raise ExprError(f'unexpected character {m.group(3)!r} in {text!r}')
            tokens.append(('op', m.group(3)))
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else (None, None)

    def take(op):
        nonlocal pos
        if peek() == ('op', op):
            pos += 1
            return True
        return False

    def expr():
        a = term()
        while True:
            if take('+'):
                a = ('add', a, term())
            elif take('-'):
                a = ('sub', a, term())
            else:
                return a

    def term():
        a = unary()
        while True:
            if take('*'):
                a = ('mul', a, unary())
            elif take('/'):
                a = ('div', a, unary())
            else:
                return a

    def unary():
        return ('neg', unary()) if take('-') else power()

    def power():
        nonlocal pos
        a = atom()
        if not take('^'):
            return a
        sign = -1 if take('-') else 1
        kind, val = peek()
        if kind != 'int':
            raise ExprError(f'an exponent is an integer, in {text!r}')
        pos += 1
        return ('pow', a, sign * val)

    def atom():
        nonlocal pos
        kind, val = peek()
        if kind == 'name' and val in CALLS and pos + 1 < len(tokens) and tokens[pos + 1] == ('op', '('):
            if pos + 3 >= len(tokens) or tokens[pos + 2][0] != 'name' or tokens[pos + 3] != ('op', ')'):
                raise ExprError(f'{val}( ) takes the name of a kernel, in {text!r}')
            pos += 4
            return ('call', val, tokens[pos - 2][1])
        if (kind, val) == ('name', 'abs') and pos + 1 < len(tokens) and tokens[pos + 1] == ('op', '('):
            pos += 2
            a = expr()
            if not take(')'):
                raise ExprError(f'missing ")" in {text!r}')
            return ('abs', a)
        if kind == 'name' and pos + 1 < len(tokens) and tokens[pos + 1] == ('op', '['):
            if pos + 3 >= len(tokens) or tokens[pos + 2][0] != 'int' or tokens[pos + 3] != ('op', ']'):
                raise ExprError(f'{val}[ ] takes the index of a limb, in {text!r}')
            pos += 4
            return ('limb', val, tokens[pos - 2][1])
        if kind in ('int', 'name'):
            pos += 1
            return (kind, val)
        if take('('):
            a = expr()
            if not take(')'):
                raise ExprError(f'missing ")" in {text!r}')
            return a
        raise ExprError(f'expected a number, a name or "(" in {text!r}')

    tree = expr()
    if pos != len(tokens):
        raise ExprError(f'unexpected {tokens[pos][1]!r} in {text!r}')
    return tree


def names(tree):
    """The names a tree uses; a limb counts as the name of its group."""
    if tree[0] in ('name', 'limb'):
        return {tree[1]}
    if tree[0] in ('int', 'call'):
        return set()
    return set().union(*(names(t) for t in tree[1:] if isinstance(t, tuple)))


def limbs(tree):
    """The (group, index) of every limb a tree names."""
    if tree[0] == 'limb':
        return {tree[1:]}
    return set().union(*(limbs(t) for t in tree[1:] if isinstance(t, tuple)))


def limb_key(name, i):
    """The key of limb i of group `name` in the environment of `evaluate`."""
    return f'{name}[{i}]'


def calls(tree):
    """The (f, K) of every unit(K) and tiny(K) in a tree."""
    if tree[0] == 'call':
        return {tree[1:]}
    return set().union(*(calls(t) for t in tree[1:] if isinstance(t, tuple)))


def evaluate(tree, env):
    """The exact value of a tree, with each name bound to a Fraction in env (limb i of group s
    under limb_key(s, i))."""
    kind = tree[0]
    if kind == 'int':
        return Fraction(tree[1])
    if kind == 'name':
        if tree[1] not in env:
            raise ExprError(f'unknown name {tree[1]!r}')
        return env[tree[1]]
    if kind == 'limb':
        key = limb_key(tree[1], tree[2])
        if key not in env:
            raise ExprError(f'unknown limb {key!r}')
        return env[key]
    if kind == 'neg':
        return -evaluate(tree[1], env)
    if kind == 'abs':
        return abs(evaluate(tree[1], env))
    if kind == 'call':
        key = f'{tree[1]}({tree[2]})'
        if key not in env:
            raise ExprError(f'unknown {key}')
        return env[key]
    if kind == 'pow':
        base = evaluate(tree[1], env)
        if base == 0 and tree[2] < 0:
            raise ExprError('division by zero')
        return base ** tree[2]
    a, b = evaluate(tree[1], env), evaluate(tree[2], env)
    if kind == 'add':
        return a + b
    if kind == 'sub':
        return a - b
    if kind == 'mul':
        return a * b
    if b == 0:
        raise ExprError('division by zero')
    return a / b
