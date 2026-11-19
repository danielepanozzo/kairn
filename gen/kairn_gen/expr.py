"""Rational expressions: the `c` and `t` of an error claim, and a kernel's `value`.

A small explicit parser, so that no claim text is ever evaluated as Python:

    expr  := term (('+' | '-') term)*
    term  := unary (('*' | '/') unary)*
    unary := '-' unary | atom
    atom  := INTEGER | 'abs' '(' expr ')' | NAME | '(' expr ')'

The result is a tree of tuples: ('int', n), ('name', s), ('neg', a), ('abs', a), and (op, a, b)
for op in add, sub, mul, div. Where each kind of tree may appear is the rules' business.
"""
import re
from fractions import Fraction

# Every character that is not white space is part of some token (the last group catches the rest).
_TOKEN = re.compile(r'\s*(?:([0-9]+)|([A-Za-z][A-Za-z0-9_]*)|(\S))')


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
            if m.group(3) not in '+-*/()':
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
        return ('neg', unary()) if take('-') else atom()

    def atom():
        nonlocal pos
        kind, val = peek()
        if (kind, val) == ('name', 'abs') and pos + 1 < len(tokens) and tokens[pos + 1] == ('op', '('):
            pos += 2
            a = expr()
            if not take(')'):
                raise ExprError(f'missing ")" in {text!r}')
            return ('abs', a)
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
    if tree[0] == 'name':
        return {tree[1]}
    if tree[0] == 'int':
        return set()
    return set().union(*(names(t) for t in tree[1:]))


def evaluate(tree, env):
    """The exact value of a tree, with each name bound to a Fraction in env."""
    kind = tree[0]
    if kind == 'int':
        return Fraction(tree[1])
    if kind == 'name':
        if tree[1] not in env:
            raise ExprError(f'unknown name {tree[1]!r}')
        return env[tree[1]]
    if kind == 'neg':
        return -evaluate(tree[1], env)
    if kind == 'abs':
        return abs(evaluate(tree[1], env))
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
