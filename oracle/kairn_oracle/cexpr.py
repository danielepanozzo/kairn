"""Exact expressions of the claims of the folds' stage (architecture.md, "Claims of Milestone 2"):
the `value` of an `upper` entry that carries one, the `args` of `holds`, and the constants `eps`,
`term` and `tau` of `fold_error`.

Grammar: integers, `u`, `eta`, names (inputs and one-limb outputs of a kernel, where the caller
allows them), `unit(K)` and `tiny(K)` (the constants c u^k and t eta of the error entry of kernel
K), binary `+`, `-`, `*`, `/`, unary minus, parentheses, and integer powers `^` whose exponent is
a constant (possibly negative, `2^-3`).  A unary minus binds less tightly than `^` (`-2^2` is -4)
and `^` groups to the right, as in claims.eval_const.  The value is a Fraction, computed exactly;
these expressions are few per line (the bound kernels) or per format (the folds' constants), so
Fractions cost nothing here, and the verdicts that compare with limbs still clear denominators
with integers.
"""

import re
from fractions import Fraction

FUNCTIONS = ("unit", "tiny")
RESERVED = ("u", "eta") + FUNCTIONS


class CExprError(ValueError):
    pass


_TOKEN = re.compile(r"\s*(?:(\d+)|([-+*/^()])|([A-Za-z_][A-Za-z0-9_]*))")


def parse(text):
    """The syntax tree of an expression: ("int", n), ("u",), ("eta",), ("name", s),
    ("unit", K), ("tiny", K), ("neg", a), and (op, a, b) for op in + - * / ^."""
    if isinstance(text, bool) or not isinstance(text, (str, int)):
        raise CExprError("expression %r is not a string" % (text,))
    s = str(text).strip()
    toks = []
    pos = 0
    while pos < len(s):
        m = _TOKEN.match(s, pos)
        if m is None or m.end() == pos:
            raise CExprError("cannot read expression %r at %r" % (text, s[pos:]))
        pos = m.end()
        if m.group(1) is not None:
            toks.append(("int", int(m.group(1))))
        elif m.group(2) is not None:
            toks.append(("op", m.group(2)))
        else:
            toks.append(("word", m.group(3)))
    toks.append(("end", None))
    i = [0]

    def peek():
        return toks[i[0]]

    def take():
        t = toks[i[0]]
        i[0] += 1
        return t

    def sum_():
        a = prod_()
        while peek() in (("op", "+"), ("op", "-")):
            op = take()[1]
            a = (op, a, prod_())
        return a

    def prod_():
        a = unary_()
        while peek() in (("op", "*"), ("op", "/")):
            op = take()[1]
            a = (op, a, unary_())
        return a

    def unary_():
        if peek() == ("op", "-"):
            take()
            return ("neg", unary_())
        if peek() == ("op", "+"):
            take()
            return unary_()
        return pow_()

    def pow_():
        base = atom_()
        if peek() == ("op", "^"):
            take()
            e = unary_()
            if names(e) or calls(e):
                raise CExprError("the exponent of a power must be a constant integer in %r" % text)
            return ("^", base, e)
        return base

    def atom_():
        t = take()
        if t[0] == "int":
            return ("int", t[1])
        if t[0] == "word":
            w = t[1]
            if w == "u":
                return ("u",)
            if w == "eta":
                return ("eta",)
            if w in FUNCTIONS:
                if take() != ("op", "("):
                    raise CExprError("%s must be followed by '(' in %r" % (w, text))
                k = take()
                if k[0] != "word" or k[1] in RESERVED:
                    raise CExprError("%s( ) takes the name of a kernel in %r" % (w, text))
                if take() != ("op", ")"):
                    raise CExprError("unbalanced parentheses in %r" % text)
                return (w, k[1])
            return ("name", w)
        if t == ("op", "("):
            a = sum_()
            if take() != ("op", ")"):
                raise CExprError("unbalanced parentheses in %r" % text)
            return a
        raise CExprError("unexpected %r in %r" % (t[1] if t[1] is not None else "end", text))

    if peek()[0] == "end":
        raise CExprError("empty expression")
    tree = sum_()
    if peek()[0] != "end":
        raise CExprError("trailing input in %r" % text)
    return tree


def names(tree, out=None):
    """The names of a tree (inputs and outputs), in order, with repetitions."""
    out = [] if out is None else out
    if tree[0] == "name":
        out.append(tree[1])
    elif tree[0] in ("neg", "+", "-", "*", "/", "^"):
        for sub in tree[1:]:
            names(sub, out)
    return out


def calls(tree, out=None):
    """The (function, kernel) pairs of a tree: unit(K), tiny(K)."""
    out = [] if out is None else out
    if tree[0] in FUNCTIONS:
        out.append((tree[0], tree[1]))
    elif tree[0] in ("neg", "+", "-", "*", "/", "^"):
        for sub in tree[1:]:
            calls(sub, out)
    return out


def evaluate(tree, env):
    """The exact value of a tree.  env: "u" and "eta" (Fractions), "names" (a dict of Fractions),
    "unit" and "tiny" (functions of a kernel's name).  Raises CExprError on a division by zero
    or a power that does not exist."""
    k = tree[0]
    if k == "int":
        return Fraction(tree[1])
    if k == "u":
        return env["u"]
    if k == "eta":
        return env["eta"]
    if k == "name":
        return env["names"][tree[1]]
    if k in FUNCTIONS:
        return env[k](tree[1])
    if k == "neg":
        return -evaluate(tree[1], env)
    a = evaluate(tree[1], env)
    b = evaluate(tree[2], env)
    if k == "+":
        return a + b
    if k == "-":
        return a - b
    if k == "*":
        return a * b
    if k == "/":
        if b == 0:
            raise CExprError("division by zero")
        return a / b
    if b.denominator != 1:
        raise CExprError("a power with an exponent that is not an integer")
    e = int(b)
    if abs(e) > 1 << 16:
        raise CExprError("exponent %d too large" % e)
    if a == 0 and e < 0:
        raise CExprError("division by zero (0^%d)" % e)
    return a ** e


def to_text(tree):
    k = tree[0]
    if k == "int":
        return str(tree[1])
    if k in ("u", "eta"):
        return k
    if k == "name":
        return tree[1]
    if k in FUNCTIONS:
        return "%s(%s)" % (k, tree[1])
    if k == "neg":
        return "-(%s)" % to_text(tree[1])
    return "(%s %s %s)" % (to_text(tree[1]), k, to_text(tree[2]))
