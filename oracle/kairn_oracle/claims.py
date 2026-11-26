"""Reading claims files.

The vocabulary is closed: anything the oracle does not understand is an error, never
ignored, because a requirement or a guarantee that is silently dropped makes the oracle
lenient without anyone noticing.
"""

import json
import re
from fractions import Fraction

from . import cexpr as CX
from . import expr as X
from .fmt import parse_format, FormatError, Format


class ClaimsError(ValueError):
    pass


_NAME = r"[A-Za-z_][A-Za-z0-9_]*"
_VALUE_RE = re.compile(r"\s*(%s)\s*([-+*])\s*(%s)\s*\Z" % (_NAME, _NAME))
_IDENTITY_RE = re.compile(r"\s*(%s)\s*\Z" % _NAME)
_NORMALIZED_RE = re.compile(r"\s*normalized\(\s*(%s)\s*\)\s*\Z" % _NAME)
_ABS_GE_RE = re.compile(r"\s*abs_ge\(\s*(%s)\s*,\s*(%s)\s*\)\s*\Z" % (_NAME, _NAME))
# Requirements on one input, second wave.
_UNARY_REQ_RE = re.compile(r"\s*(power_of_two|nonneg)\(\s*(%s)\s*\)\s*\Z" % _NAME)
# Requirements of the non-finite layer (architecture.md, "Claims of the non-finite layer").
_CANONICAL_RE = re.compile(r"\s*canonical\(\s*(%s)\s*\)\s*\Z" % _NAME)
_BALL_RE = re.compile(r"\s*ball\(\s*(%s)\s*,\s*(%s)\s*\)\s*\Z" % (_NAME, _NAME))
# Requirements of the folds' stage of Milestone 2 (architecture.md, "Claims of Milestone 2"):
# count(NAME), a one-limb input that is 0 or at least 1, and format(half), which names no input.
_COUNT_RE = re.compile(r"\s*count\(\s*(%s)\s*\)\s*\Z" % _NAME)
_FORMAT_RE = re.compile(r"\s*format\(\s*(%s)\s*\)\s*\Z" % _NAME)
FORMAT_PROPERTIES = ("half",)
DOMAINS = ("finite", "extended")
IEEE_STATUSES = ("proved", "unverified")
# The operation of T that `extends` applies to the leading limbs, and the operator the kernel's
# value must have for it.
LEADS = {"add": "+", "sub": "-", "mul": "*"}
# Kinds that exist only in the extended domain, and the kinds a core of `extends` may have.
EXTENDED_KINDS = ("extends", "represents", "makes_ball", "finite_or_nan")
CORE_KINDS = ("normalized", "error", "leading_rounded")
# limb_products_normal is not in architecture.md: it is the condition of the exactness claim of
# mul_pow2_2 ("each of the two products is zero or at least 2^(p-1) eta in magnitude"), which
# the vocabulary cannot otherwise express.  Proposed as an addition.
WHEN_VOCABULARY = ("product_large", "limb_products_normal")
# Milestone 2 (architecture.md, "Claims of Milestone 2"): the condition a `rounded` entry may
# carry, the sides of `neighbor` and `bound`, and the conditions of `exact_when`.
ROUNDED_WHEN = ("product_large",)
NEIGHBOR_SIDES = ("up", "down")
BOUND_SIDES = ("below", "above")
EXACT_CONDITIONS = ("zero_or_abs_gt", "zero_or_abs_ge")
# The forms of an error entry: rho is |value| (R), the sum of the magnitudes of the inputs (A), or
# the sum of the magnitudes of the terms of value (T, the folds' stage: |s| + |x y| for s+x*y).
FORMS = ("R", "A", "T")
ROUNDING_MODES = ("nearest", "down", "up")
RELATIONS = ("lt", "le", "eq")
KERNEL_FIELDS = {"name", "inputs", "outputs", "value", "requires", "ensures", "min_precision",
                 "status", "theorem", "source", "flops", "instances", "domain", "ieee_status",
                 "ieee_theorem", "rounding"}


# ---------------------------------------------------------------------------
# Rational expressions in u

_TOKEN_RE = re.compile(r"\s*(?:(\d+)|(\*\*|[-+*/^()])|(u))")


def eval_rational(expr, u):
    """Exact value of a rational expression in u: integers, u, + - * /, ^ or ** with an
    integer exponent, parentheses.  Used only for formats that `instances` does not list
    and to cross-check the listed numbers."""
    toks = []
    pos = 0
    s = expr.strip()
    while pos < len(s):
        m = _TOKEN_RE.match(s, pos)
        if m is None or m.end() == pos:
            raise ClaimsError("cannot parse rational expression %r at %r" % (expr, s[pos:]))
        pos = m.end()
        if m.group(1) is not None:
            toks.append(("num", Fraction(int(m.group(1)))))
        elif m.group(3) is not None:
            toks.append(("num", u))
        else:
            op = m.group(2)
            toks.append(("op", "^" if op == "**" else op))
    toks.append(("end", None))
    i = [0]

    def peek():
        return toks[i[0]]

    def take():
        t = toks[i[0]]
        i[0] += 1
        return t

    def expr_sum():
        v = expr_prod()
        while peek() in (("op", "+"), ("op", "-")):
            op = take()[1]
            w = expr_prod()
            v = v + w if op == "+" else v - w
        return v

    def expr_prod():
        v = expr_unary()
        while peek() in (("op", "*"), ("op", "/")):
            op = take()[1]
            w = expr_unary()
            if op == "/":
                if w == 0:
                    raise ClaimsError("division by zero in %r" % expr)
                v = v / w
            else:
                v = v * w
        return v

    def expr_unary():
        if peek() == ("op", "-"):
            take()
            return -expr_unary()
        if peek() == ("op", "+"):
            take()
            return expr_unary()
        return expr_pow()

    def expr_pow():
        base = expr_atom()
        if peek() == ("op", "^"):
            take()
            e = expr_unary()
            if e.denominator != 1:
                raise ClaimsError("non-integer exponent in %r" % expr)
            return base ** int(e)
        return base

    def expr_atom():
        t = take()
        if t[0] == "num":
            return t[1]
        if t == ("op", "("):
            v = expr_sum()
            if take() != ("op", ")"):
                raise ClaimsError("unbalanced parentheses in %r" % expr)
            return v
        raise ClaimsError("unexpected token %r in %r" % (t[1], expr))

    v = expr_sum()
    if peek()[0] != "end":
        raise ClaimsError("trailing input in %r" % expr)
    return v


_CONST_TOKEN_RE = re.compile(r"\s*(?:(\d+)|([-+*/^()])|([A-Za-z_][A-Za-z0-9_]*))")


def eval_const(expr, u, eta):
    """Exact value of the threshold K of an exact_when condition (architecture.md, "Claims of
    Milestone 2"): integers, u, eta, + - * /, parentheses and integer powers ^ (possibly
    negative, 2^-3), the language of const up(EXPR) without unit( ), tiny( ) or a rounding.
    A unary minus binds less tightly than ^ (-2^2 is -4), and ^ groups to the right."""
    if isinstance(expr, bool) or not isinstance(expr, (str, int)):
        raise ClaimsError("constant %r is not an expression" % (expr,))
    s = str(expr).strip()
    toks = []
    pos = 0
    while pos < len(s):
        m = _CONST_TOKEN_RE.match(s, pos)
        if m is None or m.end() == pos:
            raise ClaimsError("cannot parse constant %r at %r" % (expr, s[pos:]))
        pos = m.end()
        if m.group(1) is not None:
            toks.append(("num", Fraction(int(m.group(1)))))
        elif m.group(3) is not None:
            if m.group(3) == "u":
                toks.append(("num", u))
            elif m.group(3) == "eta":
                toks.append(("num", eta))
            else:
                raise ClaimsError("constant %r names %r, which is not u or eta" % (expr, m.group(3)))
        else:
            toks.append(("op", m.group(2)))
    toks.append(("end", None))
    i = [0]

    def peek():
        return toks[i[0]]

    def take():
        t = toks[i[0]]
        i[0] += 1
        return t

    def c_sum():
        v = c_prod()
        while peek() in (("op", "+"), ("op", "-")):
            op = take()[1]
            w = c_prod()
            v = v + w if op == "+" else v - w
        return v

    def c_prod():
        v = c_unary()
        while peek() in (("op", "*"), ("op", "/")):
            op = take()[1]
            w = c_unary()
            if op == "/":
                if w == 0:
                    raise ClaimsError("division by zero in constant %r" % expr)
                v = v / w
            else:
                v = v * w
        return v

    def c_unary():
        if peek() == ("op", "-"):
            take()
            return -c_unary()
        return c_pow()

    def c_pow():
        base = c_atom()
        if peek() == ("op", "^"):
            take()
            e = c_unary()
            if e.denominator != 1:
                raise ClaimsError("non-integer exponent in constant %r" % expr)
            if abs(e) > 1 << 16:
                raise ClaimsError("exponent %s too large in constant %r" % (e, expr))
            if base == 0 and e < 0:
                raise ClaimsError("division by zero in constant %r" % expr)
            return base ** int(e)
        return base

    def c_atom():
        t = take()
        if t[0] == "num":
            return t[1]
        if t == ("op", "("):
            v = c_sum()
            if take() != ("op", ")"):
                raise ClaimsError("unbalanced parentheses in constant %r" % expr)
            return v
        raise ClaimsError("unexpected %r in constant %r" % (t[1] if t[1] is not None else "end",
                                                            expr))

    v = c_sum()
    if peek()[0] != "end":
        raise ClaimsError("trailing input in constant %r" % expr)
    return v


def format_u_eta(fmt):
    """u = 2^-p and eta = 2^qmin of a format, as Fractions."""
    eta = Fraction(1, 1 << -fmt.qmin) if fmt.qmin < 0 else Fraction(1 << fmt.qmin)
    return Fraction(1, 1 << fmt.p), eta


def parse_fraction(s, what):
    try:
        if isinstance(s, bool):
            raise ValueError
        if isinstance(s, int):
            return Fraction(s)
        if not isinstance(s, str):
            raise ValueError
        return Fraction(s.strip())
    except (ValueError, ZeroDivisionError):
        raise ClaimsError("%s: not an exact rational: %r" % (what, s))


def _fw_text(fw):
    if not fw:
        return "nothing (no condition claimed)"
    return " and ".join("|%s| <= 2^(qmax+p%+d)" % (text, e) if e else "|%s| <= 2^(qmax+p)" % text
                        for _t, text, e in fw)


def ew_condition_text(text, op, k):
    return "%s = 0 or |%s| %s %s" % (text, text, ">" if op == "zero_or_abs_gt" else ">=", k)


def _ew_text(ew):
    return " and ".join("(%s)" % ew_condition_text(text, op, k) for _t, text, op, k in ew)


# ---------------------------------------------------------------------------

class Entry:
    """One `ensures` entry."""

    KNOWN = {"normalized": {"kind", "of"},
             "error": {"kind", "of", "form", "c", "k", "t", "when", "instances", "exact_when"},
             "leading_rounded": {"kind", "of"},
             "rounded": {"kind", "of", "mode", "when"},
             # gaps; or, the folds' stage, a value of its own and the mask it holds under.
             "upper": {"kind", "of", "gaps", "value", "if"},
             "predicate": {"kind", "of", "rel", "args"},
             "encloses": {"kind", "center", "radius", "set", "balls", "finite_when", "exact_when"},
             # The non-finite layer.
             "extends": {"kind", "of", "core", "lead", "finite_when"},
             "represents": {"kind", "of"},
             "makes_ball": {"kind", "center", "radius", "from"},
             # Milestone 2 (architecture.md, "Claims of Milestone 2").
             "neighbor": {"kind", "of", "side"},
             "bound": {"kind", "of", "side", "steps"},
             # The folds' stage of Milestone 2.
             "holds": {"kind", "rel", "args", "if"},
             # The folds' stage; `if` (a mask input) and `steps` for the finishes of the folds of
             # maxima.
             "finite_or_nan": {"kind", "of", "flag", "if", "steps"},
             # The folds of maxima: the larger of two exact values.
             "maximum": {"kind", "of", "args"}}

    def __init__(self, kernel, raw, index, error_index):
        self.raw = raw
        self.index = index
        if not isinstance(raw, dict) or "kind" not in raw:
            raise ClaimsError("%s: ensures entry %d has no kind" % (kernel.name, index))
        self.kind = raw["kind"]
        where = "%s: ensures entry %d (%s)" % (kernel.name, index, self.kind)
        known = self.KNOWN
        if self.kind not in known:
            raise ClaimsError("%s: unknown kind" % where)
        extra = set(raw) - known[self.kind]
        if extra:
            raise ClaimsError("%s: unknown fields %s" % (where, sorted(extra)))
        self.error_index = None
        self.finite_when = None
        # exact_when of error and encloses: [(tree, text, op, K text)], or None when absent.
        self.exact_when = None
        # The condition of a rounded entry (product_large), or None.
        self.when = None
        # The mask output an `upper` with a value of its own or a `holds` entry holds under, and
        # its expressions (cexpr trees); None for every other entry.
        self.cond = None
        self.cvalue = None
        if self.kind in EXTENDED_KINDS and not kernel.extended:
            raise ClaimsError("%s: this kind belongs to the extended domain, and the kernel has "
                              "no \"domain\": \"extended\"" % where)
        # same_set, of the round-up interval (upward.py).
        if self.kind in UP.KNOWN:
            UP.read_entry(self, kernel, raw, where)
            return
        # The predicates, comparisons and set operations of a ball (enclosure.py).
        if self.kind in EN.KNOWN:
            EN.read_entry(self, kernel, raw, where)
            return
        # The kinds of the interval kernels, and makes_ball from the bounds of an interval
        # (intervals.py).
        if self.kind in IV.KNOWN:
            IV.read_entry(self, kernel, raw, where)
            return
        if self.kind == "makes_ball" and isinstance(raw.get("from"), dict) \
                and set(raw["from"]) == {"lower", "upper"}:
            IV.read_makes_ball_interval(self, kernel, raw, where)
            return
        if self.kind == "makes_ball" and "midpoint_when" in raw:
            raise ClaimsError("%s: midpoint_when is for a ball made from the bounds of an "
                              "interval" % where)
        if self.kind == "makes_ball" and {"rel", "abs", "smallest_radius"} & set(raw):
            raise ClaimsError("%s: rel, abs and smallest_radius are for a ball made from the "
                              "bounds of an interval" % where)
        if self.kind == "holds":
            self._read_holds(kernel, raw, where)
            self.of = []
            self.label = self._label()
            return
        if self.kind == "encloses":
            self._read_encloses(kernel, raw, where)
            self.of = [self.center, self.radius]
            if "exact_when" in raw:
                self.exact_when = self._read_exact_when(kernel, raw, where)
            if kernel.extended:
                self.finite_when = self._read_finite_when(kernel, raw, where)
                # Every ball of the set is a ball operand of the kernel: its states (finite,
                # whole line, empty) come from a ball() requirement on the same two inputs.
                for b, (c, r) in self.balls.items():
                    if (c, r) not in kernel.ball_requires:
                        raise ClaimsError("%s: ball %s over (%s, %s) has no requirement "
                                          "ball(%s, %s)" % (where, b, c, r, c, r))
            elif "finite_when" in raw:
                raise ClaimsError("%s: finite_when belongs to the extended domain" % where)
            self.label = self._label()
            return
        if self.kind == "makes_ball":
            self._read_makes_ball(kernel, raw, where)
            self.of = [self.center, self.radius]
            self.label = self._label()
            return
        self.of = kernel.resolve_outputs(raw.get("of"), where)
        masks = [n for n in self.of if n in kernel.masks]
        if self.kind == "predicate":
            if len(self.of) != 1 or not masks:
                raise ClaimsError("%s: 'of' must name one mask output" % where)
        elif masks:
            raise ClaimsError("%s: 'of' names the mask %s" % (where, masks[0]))
        # An upper entry with a value of its own does not use the kernel's.
        own_value = self.kind == "upper" and ("value" in raw or "if" in raw)
        if self.kind == "upper":
            # unless and exact_when: the radius kernels of the ball vectors (bvec.py).
            BV.check_upper_fields(raw, where)
        if (self.kind in ("error", "leading_rounded", "rounded", "upper", "extends", "represents",
                          "neighbor", "bound", "finite_or_nan")
                and kernel.value_tree is None and not own_value):
            raise ClaimsError("%s: the kernel has no value" % where)
        if self.kind == "finite_or_nan":
            self._read_finite_or_nan(kernel, raw, where)
        if self.kind == "extends":
            self._read_extends(kernel, raw, where)
        if self.kind in ("rounded", "upper", "neighbor", "bound", "maximum"):
            if len(self.of) != 1 or kernel.limbs_of(self.of[0]) != 1:
                raise ClaimsError("%s: 'of' must name one 1-limb output" % where)
        if self.kind == "maximum":
            self._read_maximum(kernel, raw, where)
        if self.kind == "rounded":
            self.mode = raw.get("mode")
            if self.mode not in ROUNDING_MODES:
                raise ClaimsError("%s: mode must be nearest, down or up, got %r" % (where, self.mode))
            # Absent when there is no condition (architecture.md); null is read the same way.
            self.when = raw.get("when")
            if self.when is not None and self.when not in ROUNDED_WHEN:
                raise ClaimsError("%s: unknown condition when=%r (a rounded entry takes "
                                  "product_large)" % (where, self.when))
            if self.when is not None and self.mode == "nearest":
                raise ClaimsError("%s: a condition on a rounding to nearest is not in the "
                                  "vocabulary" % where)
            if "value" in raw:
                # A value of its own (the accumulator's sum of magnitudes, bvec.py).
                BV.read_rounded_value(self, kernel, raw, where)
        elif self.kind == "neighbor":
            self.side = raw.get("side")
            if self.side not in NEIGHBOR_SIDES:
                raise ClaimsError("%s: side must be up or down, got %r" % (where, self.side))
            t = kernel.value_tree
            if t[0] != "name" or kernel.limbs_of(t[1]) != 1:
                raise ClaimsError("%s: the value must be the name of a one-limb input, not %r"
                                  % (where, kernel.value_text))
            self.operand = t[1]
        elif self.kind == "bound":
            self.side = raw.get("side")
            if self.side not in BOUND_SIDES:
                raise ClaimsError("%s: side must be below or above, got %r" % (where, self.side))
            self.steps = raw.get("steps")
            if (not isinstance(self.steps, int) or isinstance(self.steps, bool)
                    or self.steps < 0):
                raise ClaimsError("%s: steps must be an integer >= 0, got %r" % (where, self.steps))
        elif self.kind == "upper" and own_value and "if" not in raw:
            # A value of its own and no mask: the radius kernels of the ball vectors (bvec.py).
            BV.read_upper(self, kernel, raw, where)
        elif self.kind == "upper" and own_value:
            # The folds' stage: value and if in place of gaps.  When the mask is true the output
            # is at least the exact value of value; nothing else is said.
            if "gaps" in raw:
                raise ClaimsError("%s: an upper entry has gaps, or value and if, not both" % where)
            if "value" not in raw or "if" not in raw:
                raise ClaimsError("%s: an upper entry with a value of its own needs both value "
                                  "and if" % where)
            self.gaps = None
            self.cond = self._read_mask_name(kernel, raw["if"], where)
            self.cvalue = self._read_cexpr(kernel, raw["value"], where + " value")
            self.cvalue_text = str(raw["value"]).strip()
        elif self.kind == "upper":
            self.gaps = parse_fraction(raw.get("gaps"), where + " gaps")
            if self.gaps < 0:
                raise ClaimsError("%s: gaps is negative" % where)
        elif self.kind == "predicate":
            self.rel = raw.get("rel")
            if self.rel not in RELATIONS:
                raise ClaimsError("%s: rel must be lt, le or eq, got %r" % (where, self.rel))
            args = raw.get("args")
            if not isinstance(args, list) or len(args) != 2:
                raise ClaimsError("%s: args must be a list of two expressions" % where)
            self.args = [kernel.input_expression(a, where) for a in args]
            self.args_text = [a.strip() for a in args]
        if self.kind == "error":
            self.error_index = error_index
            self.form = raw.get("form")
            if self.form not in FORMS:
                raise ClaimsError("%s: form must be R, A or T, got %r" % (where, self.form))
            self.c = raw.get("c")
            if not isinstance(self.c, (str, int)) or isinstance(self.c, bool):
                raise ClaimsError("%s: c must be a string" % where)
            self.c = str(self.c)
            self.k = raw.get("k")
            if not isinstance(self.k, int) or isinstance(self.k, bool) or self.k < 0:
                raise ClaimsError("%s: k must be a nonnegative integer" % where)
            self.t = parse_fraction(raw.get("t"), where + " t")
            if self.t < 0:
                raise ClaimsError("%s: t is negative" % where)
            self.when = raw.get("when")
            if self.when is not None and self.when not in WHEN_VOCABULARY:
                raise ClaimsError("%s: unknown condition when=%r" % (where, self.when))
            if self.when == "limb_products_normal" and kernel.limb_products is None:
                raise ClaimsError("%s: limb_products_normal needs a value that is one input "
                                  "times another" % where)
            self.entry_instances = raw.get("instances")
            if "exact_when" in raw:
                self.exact_when = self._read_exact_when(kernel, raw, where)
            if "exact_flag" in raw:
                # The steps of the scalings of a ball vector (bvec.py).
                BV.read_exact_flag(self, kernel, raw, where)
        self.label = self._label()
        if self.kind in ("bound", "rounded"):
            # zero_factor (the interval kernels): a zero operand gives a zero output.
            IV.read_zero_factor(self, kernel, raw, where)

    def _read_mask_name(self, kernel, name, where):
        """The name of a mask output (the `if` of the folds' stage)."""
        if not isinstance(name, str) or name not in dict(kernel.outputs) or name not in kernel.masks:
            raise ClaimsError("%s: if must name a mask output, got %r" % (where, name))
        return name

    def _read_cexpr(self, kernel, text, where):
        """An exact expression over the limb inputs, the one-limb outputs, u, eta, integers and
        unit(K), tiny(K) (cexpr.py); unit and tiny are resolved by Claims.link_constants."""
        try:
            tree = CX.parse(text)
        except CX.CExprError as ex:
            raise ClaimsError("%s: %s" % (where, ex))
        outs = dict(kernel.outputs)
        ins = dict(kernel.inputs)
        clash = [n for n in list(ins) + list(outs) if n in CX.RESERVED]
        if clash:
            raise ClaimsError("%s: the kernel has an input or output named %s, which these "
                              "expressions read as a constant" % (where, clash[0]))
        for n in CX.names(tree):
            if n in kernel.masks:
                raise ClaimsError("%s: %r is a mask, not a value" % (where, n))
            if n in ins:
                continue
            if n in outs and outs[n] == 1:
                continue
            raise ClaimsError("%s: %r is not a limb input or a one-limb output" % (where, n))
        return tree

    def _read_holds(self, kernel, raw, where):
        """{"kind": "holds", "rel": REL, "args": [A, B], "if": MASK}: when the mask output is true,
        the relation holds between the exact values of A and B."""
        for f in ("rel", "args", "if"):
            if f not in raw:
                raise ClaimsError("%s: missing %s" % (where, f))
        self.rel = raw["rel"]
        if self.rel not in RELATIONS:
            raise ClaimsError("%s: rel must be lt, le or eq, got %r" % (where, self.rel))
        args = raw["args"]
        if not isinstance(args, list) or len(args) != 2:
            raise ClaimsError("%s: args must be a list of two expressions" % where)
        self.cargs = [self._read_cexpr(kernel, a, where + " args") for a in args]
        self.args_text = [str(a).strip() for a in args]
        self.cond = self._read_mask_name(kernel, raw["if"], where)

    def _read_maximum(self, kernel, raw, where):
        """{"kind": "maximum", "of": R, "args": [A, B]}: R is the larger of the exact values of A
        and B, expressions of the language of value in which NAME[I] is limb I of an input."""
        args = raw.get("args")
        if not isinstance(args, list) or len(args) != 2 or not all(isinstance(a, str) for a in args):
            raise ClaimsError("%s: args must be a list of two expressions" % where)
        ins = dict(kernel.inputs)
        self.margs = []
        for a in args:
            try:
                tree = X.parse(a, limbs=True)
            except X.ExprError as ex:
                raise ClaimsError("%s: %s" % (where, ex))
            for n in X.names(tree):
                if n not in ins or n in kernel.masks:
                    raise ClaimsError("%s: %r is not a limb input" % (where, n))
            for n, i in X.limb_refs(tree):
                if i >= ins[n]:
                    raise ClaimsError("%s: %s[%d] is not a limb of %s, which has %d" % (
                        where, n, i, n, ins[n]))
            self.margs.append(tree)
        self.args_text = [a.strip() for a in args]

    def _read_finite_or_nan(self, kernel, raw, where):
        """{"kind": "finite_or_nan", "of": R, "flag": F}: F is true exactly when limb 0 of value
        (an input) is finite, and R is then value, limb for limb; otherwise every limb of R is a
        NaN.  With "if": M (a mask input) and "steps": S (an integer >= 1), the finishes of the
        folds of maxima: with t the value stepped up S times (IEEE 754's nextUp; S = 0 without
        steps), F is true exactly when M is true and t is finite, and R is then t; otherwise every
        limb of R is a NaN."""
        if "flag" not in raw:
            raise ClaimsError("%s: missing flag" % where)
        self.flag = self._read_mask_name(kernel, raw["flag"], where)
        self.cond_in = None
        self.steps = 0
        if "if" in raw:
            m = raw["if"]
            if not isinstance(m, str) or m not in kernel.input_names or m not in kernel.masks:
                raise ClaimsError("%s: if must name a mask input, got %r" % (where, m))
            self.cond_in = m
        if "steps" in raw:
            st = raw["steps"]
            if not isinstance(st, int) or isinstance(st, bool) or st < 1:
                raise ClaimsError("%s: steps must be an integer >= 1 (absent for none), got %r"
                                  % (where, st))
            self.steps = st
        t = kernel.value_tree
        if t[0] != "name":
            raise ClaimsError("%s: the value must be the name of an input, not %r"
                              % (where, kernel.value_text))
        self.operand = t[1]
        limbs = sum(kernel.limbs_of(n) for n in self.of)
        if kernel.limbs_of(self.operand) != limbs:
            raise ClaimsError("%s: the output %s has %d limbs and the value %s %d" % (
                where, "+".join(self.of), limbs, self.operand, kernel.limbs_of(self.operand)))
        if self.steps and limbs != 1:
            raise ClaimsError("%s: steps of a value of %d limbs (a step is of one number)"
                              % (where, limbs))
        # nonneg and if_all: the finishes of the ball vectors (bvec.py).
        BV.read_finish_fields(self, kernel, raw, where)

    def _read_exact_when(self, kernel, raw, where):
        """[(tree, text, op, K)]: each condition {"zero_or_abs_gt": EXPR, "than": K} or
        {"zero_or_abs_ge": EXPR, "than": K} means EXPR = 0 or |EXPR| > K (>= K), EXPR over the
        limb inputs and their limbs NAME[I], K an exact expression over u, eta and integers that
        is positive in every format (checked for each format the plan is made for).  The list
        holds when every condition does; absent when there is none, so an empty list is refused."""
        ew = raw["exact_when"]
        if not isinstance(ew, list) or not ew:
            raise ClaimsError("%s: exact_when must be a nonempty list of conditions (absent when "
                              "there is none)" % where)
        out = []
        ins = dict(kernel.inputs)
        for j, cond in enumerate(ew):
            w = "%s: exact_when[%d]" % (where, j)
            ops = [k for k in EXACT_CONDITIONS if isinstance(cond, dict) and k in cond]
            if len(ops) != 1 or set(cond) != {ops[0], "than"}:
                raise ClaimsError("%s must be {\"zero_or_abs_gt\": EXPR, \"than\": K} or "
                                  "{\"zero_or_abs_ge\": EXPR, \"than\": K}, got %r" % (w, cond))
            op = ops[0]
            text = cond[op]
            if not isinstance(text, str):
                raise ClaimsError("%s: %s must be an expression" % (w, op))
            try:
                tree = X.parse(text, limbs=True)
            except X.ExprError as ex:
                raise ClaimsError("%s: %s" % (w, ex))
            for n in X.names(tree):
                if n not in ins or n in kernel.masks:
                    raise ClaimsError("%s: %r is not a limb input" % (w, n))
            for n, i in X.limb_refs(tree):
                if i >= ins[n]:
                    raise ClaimsError("%s: %s[%d] is not a limb of %s, which has %d" % (
                        w, n, i, n, ins[n]))
            k = cond["than"]
            # Read now, in the units of binary64, so that a malformed constant is refused with the
            # claims; its value is computed exactly for each format the plan is made for.
            u, eta = format_u_eta(Format(53, -1074, 971))
            if eval_const(k, u, eta) <= 0:
                raise ClaimsError("%s: than %r is not positive" % (w, k))
            out.append((tree, text.strip(), op, k))
        return out

    def exact_threshold(self, fmt, j):
        """K of condition j of exact_when, exactly, in format fmt; a K that is not positive there
        is an error of the claims."""
        tree, text, op, k = self.exact_when[j]
        u, eta = format_u_eta(fmt)
        v = eval_const(k, u, eta)
        if v <= 0:
            raise ClaimsError("%s: exact_when %s: than %r is not positive in %s" % (
                self.label, text, k, fmt.name))
        return v

    def _read_encloses(self, kernel, raw, where):
        """center and radius name outputs; balls maps each ball name to its center and radius
        inputs; set is an expression over ball names and the other limb inputs (scalars)."""
        for f in ("center", "radius", "set", "balls"):
            if f not in raw:
                raise ClaimsError("%s: missing %s" % (where, f))
        outs = dict(kernel.outputs)
        self.center, self.radius = raw["center"], raw["radius"]
        for what, n in (("center", self.center), ("radius", self.radius)):
            if not isinstance(n, str) or n not in outs or n in kernel.masks:
                raise ClaimsError("%s: %s %r is not a limb output" % (where, what, n))
        if self.center == self.radius:
            raise ClaimsError("%s: center and radius are the same output" % where)
        if outs[self.radius] != 1:
            raise ClaimsError("%s: the radius %s must be one limb" % (where, self.radius))
        balls = raw["balls"]
        # "balls": {} is an encloses of points (the interval kernels' add_ball_2_2), in the finite
        # domain only.
        if not isinstance(balls, dict) or (not balls and kernel.extended):
            raise ClaimsError("%s: balls must be a nonempty object" % where)
        ins = dict(kernel.inputs)
        self.balls = {}
        used = set()
        for b, spec in balls.items():
            if isinstance(spec, list) and len(spec) == 2:
                c, r = spec
            elif isinstance(spec, dict) and set(spec) == {"center", "radius"}:
                c, r = spec["center"], spec["radius"]
            else:
                raise ClaimsError("%s: ball %r must be {center, radius}" % (where, b))
            if not re.fullmatch(_NAME, b) or b in ins or b in X.FUNCTIONS:
                raise ClaimsError("%s: bad ball name %r (it must not be an input name)" % (where, b))
            for what, n in (("center", c), ("radius", r)):
                if not isinstance(n, str) or n not in ins or n in kernel.masks:
                    raise ClaimsError("%s: ball %s: %s %r is not a limb input" % (where, b, what, n))
            if ins[r] != 1:
                raise ClaimsError("%s: ball %s: the radius %s must be one limb" % (where, b, r))
            if c == r or c in used or r in used:
                raise ClaimsError("%s: ball %s shares an input with another ball" % (where, b))
            used.update((c, r))
            self.balls[b] = (c, r)
        try:
            self.set_tree = X.parse(raw["set"])
        except X.ExprError as ex:
            raise ClaimsError("%s: set: %s" % (where, ex))
        self.set_text = raw["set"].strip()
        nm = X.names(self.set_tree)
        for n in nm:
            if n in self.balls:
                continue
            if n not in ins or n in kernel.masks or n in used:
                raise ClaimsError("%s: set names %r, which is neither a ball nor a scalar input"
                                  % (where, n))
        # A sum or product in which every ball occurs once is multilinear, so its range over
        # the box of the balls is attained at the corners; with abs or a repeated ball it is
        # not, the corners would not give the exact set, and the verdict could be wrong.
        for b in self.balls:
            if nm.count(b) != 1:
                raise ClaimsError("%s: ball %s must occur exactly once in set" % (where, b))
        if X.uses(self.set_tree, "abs"):
            raise ClaimsError("%s: abs() is not allowed in set" % where)

    def _read_finite_when(self, kernel, raw, where):
        """[(tree, text, E)]: each condition {"abs_le": EXPR, "exp": E} means
        |EXPR| <= 2^(qmax + p + E).  Required in the extended domain; empty when no condition
        is claimed (and then nothing is claimed: F3 and B4 do not apply)."""
        if "finite_when" not in raw:
            raise ClaimsError("%s: missing finite_when (an empty list when no condition is "
                              "claimed)" % where)
        fw = raw["finite_when"]
        if not isinstance(fw, list):
            raise ClaimsError("%s: finite_when must be a list" % where)
        out = []
        for j, cond in enumerate(fw):
            w = "%s: finite_when[%d]" % (where, j)
            if not isinstance(cond, dict) or set(cond) != {"abs_le", "exp"}:
                raise ClaimsError("%s must be {\"abs_le\": EXPR, \"exp\": E}, got %r" % (w, cond))
            e = cond["exp"]
            if not isinstance(e, int) or isinstance(e, bool):
                raise ClaimsError("%s: exp must be an integer, got %r" % (w, e))
            if not isinstance(cond["abs_le"], str):
                raise ClaimsError("%s: abs_le must be an expression" % w)
            tree = kernel.input_expression(cond["abs_le"], w.split(": ", 1)[1])
            out.append((tree, cond["abs_le"].strip(), e))
        return out

    def _read_extends(self, kernel, raw, where):
        """F1 to F5 of milestone1.md.  The core is resolved by Claims.link_cores, once every
        kernel is read: it must exist, be of the finite domain, and have the same inputs and
        outputs (by position) and the same value."""
        self.core_name = raw.get("core")
        if not isinstance(self.core_name, str) or not self.core_name:
            raise ClaimsError("%s: core must name a kernel" % where)
        if self.core_name == kernel.name:
            raise ClaimsError("%s: a kernel cannot be its own core" % where)
        self.lead = raw.get("lead")
        if self.lead not in LEADS:
            raise ClaimsError("%s: lead must be add, sub or mul, got %r" % (where, self.lead))
        self.finite_when = self._read_finite_when(kernel, raw, where)
        # lead is applied to the leading limbs of the inputs, in order; F4 takes the sign of
        # value.  Both describe one operation, so the value must be that operation of the two
        # operands, in input order for a sum or a difference.
        ops = [n for n in kernel.input_names if n not in kernel.masks]
        t = kernel.value_tree
        if len(ops) != 2:
            raise ClaimsError("%s: lead applies to two operands; the kernel has %d" % (where, len(ops)))
        if (t[0] != LEADS[self.lead] or t[1][0] != "name" or t[2][0] != "name"
                or ([t[1][1], t[2][1]] != ops if t[0] != "*" else
                    sorted([t[1][1], t[2][1]]) != sorted(ops))):
            raise ClaimsError("%s: value %r is not %s of the operands %s" % (
                where, kernel.value_text, self.lead, ", ".join(ops)))
        self.core = None

    def _read_makes_ball(self, kernel, raw, where):
        for f in ("center", "radius", "from"):
            if f not in raw:
                raise ClaimsError("%s: missing %s" % (where, f))
        outs = dict(kernel.outputs)
        ins = dict(kernel.inputs)
        self.center, self.radius = raw["center"], raw["radius"]
        for what, n in (("center", self.center), ("radius", self.radius)):
            if not isinstance(n, str) or n not in outs or n in kernel.masks:
                raise ClaimsError("%s: %s %r is not a limb output" % (where, what, n))
        if self.center == self.radius:
            raise ClaimsError("%s: center and radius are the same output" % where)
        if outs[self.radius] != 1:
            raise ClaimsError("%s: the radius %s must be one limb" % (where, self.radius))
        fr = raw["from"]
        if not isinstance(fr, dict) or set(fr) != {"center", "radius"}:
            raise ClaimsError("%s: from must be {\"center\": INPUT, \"radius\": INPUT}" % where)
        self.from_center, self.from_radius = fr["center"], fr["radius"]
        for what, n in (("center", self.from_center), ("radius", self.from_radius)):
            if not isinstance(n, str) or n not in ins or n in kernel.masks:
                raise ClaimsError("%s: from %s %r is not a limb input" % (where, what, n))
        if self.from_center == self.from_radius:
            raise ClaimsError("%s: the given center and radius are the same input" % where)
        if ins[self.from_radius] != 1:
            raise ClaimsError("%s: the given radius %s must be one limb" % (where, self.from_radius))
        if ins[self.from_center] != outs[self.center]:
            raise ClaimsError("%s: the given center has %d limbs, the output center %d" % (
                where, ins[self.from_center], outs[self.center]))

    def _label(self):
        if self.kind == "encloses":
            s = "encloses(%s, %s) %s over %s" % (
                self.center, self.radius, self.set_text,
                ", ".join("%s=[%s +- %s]" % (b, c, r) for b, (c, r) in self.balls.items()))
            if self.finite_when is not None:
                s += ", B1-B4, finite when %s" % _fw_text(self.finite_when)
            if self.exact_when is not None:
                s += ", exactly the set when %s" % _ew_text(self.exact_when)
            return s
        if self.kind == "makes_ball":
            return "makes_ball(%s, %s) from center %s, radius %s" % (
                self.center, self.radius, self.from_center, self.from_radius)
        of = "+".join(self.of)
        if self.kind == "extends":
            return "extends(%s) F1-F5, core %s, lead %s, finite when %s" % (
                of, self.core_name, self.lead, _fw_text(self.finite_when))
        if self.kind == "error":
            s = "error(%s) form %s, c=%s, k=%d, t=%s" % (of, self.form, self.c, self.k, self.t)
            if self.when:
                s += ", when %s" % self.when
            if self.exact_when is not None:
                s += ", exact when %s" % _ew_text(self.exact_when)
            return s + BV.label_suffix(self)
        if self.kind == "rounded":
            if self.when:
                return "rounded(%s) %s, when %s" % (of, self.mode, self.when)
            return "rounded(%s) %s" % (of, self.mode) + BV.label_suffix(self)
        if self.kind == "neighbor":
            return "neighbor(%s) %s of %s" % (of, self.side, self.operand)
        if self.kind == "bound":
            return "bound(%s) %s, steps=%d" % (of, self.side, self.steps)
        if self.kind == "upper" and self.cond is not None:
            return "upper(%s) >= %s if %s" % (of, self.cvalue_text, self.cond)
        if self.kind == "upper" and getattr(self, "bv", False):
            return BV.label(self)
        if self.kind == "upper":
            return "upper(%s) gaps=%s" % (of, self.gaps)
        if self.kind == "holds":
            return "holds %s(%s, %s) if %s" % (self.rel, self.args_text[0], self.args_text[1],
                                               self.cond)
        if self.kind == "finite_or_nan":
            s = "finite_or_nan(%s) flag %s" % (of, self.flag)
            if self.cond_in is not None:
                s += " if %s" % self.cond_in
            if self.steps:
                s += ", stepped up %d" % self.steps
            return s + BV.label_suffix(self)
        if self.kind == "maximum":
            return "maximum(%s) of %s, %s" % (of, self.args_text[0], self.args_text[1])
        if self.kind == "predicate":
            return "predicate(%s) %s(%s, %s)" % (of, self.rel, self.args_text[0], self.args_text[1])
        return "%s(%s)" % (self.kind, of)


class Kernel:
    def __init__(self, raw):
        if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
            raise ClaimsError("kernel entry without a name")
        self.name = raw["name"]
        self.raw = raw
        # "domain": "extended" (the non-finite layer): operands may be infinite or NaN and every
        # completed line is judged.  Absent means finite, the domain of the first two waves.
        self.domain = raw.get("domain", "finite")
        if self.domain not in DOMAINS:
            raise ClaimsError("%s: unknown domain %r (finite or extended)" % (self.name, self.domain))
        self.extended = self.domain == "extended"
        # "rounding": "upward", the kernels of the round-up interval (upward.py): read for its form;
        # it changes no verdict.
        self.rounding = UP.read_rounding(self, raw)
        self.masks = set()
        self.inputs = self._io(raw.get("inputs"), "inputs")
        self.outputs = self._io(raw.get("outputs"), "outputs")
        names = [n for n, _ in self.inputs] + [n for n, _ in self.outputs]
        if len(set(names)) != len(names):
            raise ClaimsError("%s: input and output names must be distinct" % self.name)
        self.input_names = [n for n, _ in self.inputs]
        v = raw.get("value")
        # The first-wave forms keep their tuple, which gen.py reads; every value also has its
        # syntax tree.  A value may be absent when no entry needs it (comparisons, balls).
        self.value = None
        self.value_tree = None
        self.value_text = None
        self.limb_products = None
        if v is not None:
            m = _VALUE_RE.match(v) if isinstance(v, str) else None
            mi = _IDENTITY_RE.match(v) if isinstance(v, str) else None
            if m is not None and m.group(1) in self.input_names and m.group(3) in self.input_names:
                self.value = (m.group(2), m.group(1), m.group(3))
            elif mi is not None and mi.group(1) in self.input_names:
                # A bare input name: the outputs approximate that input itself (split).  Not
                # in architecture.md's list; proposed as an addition.
                self.value = ("=", mi.group(1), mi.group(1))
            try:
                self.value_tree = self.input_expression(v, "value")
            except ClaimsError:
                raise ClaimsError("%s: value %r is not an expression over the limb inputs "
                                  "(names, + - *, unary minus, abs( ), parentheses)" % (self.name, v))
            self.value_text = v.strip()
            t = self.value_tree
            if t[0] == "*" and t[1][0] == "name" and t[2][0] == "name":
                self.limb_products = (t[1][1], t[2][1])
        self.requires = []
        self.ball_requires = []
        self.interval_requires = []
        # upward(U, N): the stored pairs of the round-up interval (upward.py).
        self.upward_requires = []
        # format(PROPERTY): requirements on the format, not on an input (format(half): the format
        # contains 1/2, eta <= 1/2).  A format without the property is outside the claims.
        self.format_requires = []
        limbs = dict(self.inputs)
        reqs = raw.get("requires", [])
        if not isinstance(reqs, list):
            raise ClaimsError("%s: requires must be a list" % self.name)
        for r in reqs:
            if not isinstance(r, str):
                raise ClaimsError("%s: requirement %r is not a string" % (self.name, r))
            m = _COUNT_RE.match(r)
            if m and m.group(1) in self.input_names and m.group(1) not in self.masks:
                if self.extended:
                    raise ClaimsError("%s: requirement %r: count() is read in the finite domain "
                                      "only" % (self.name, r))
                if limbs[m.group(1)] != 1:
                    raise ClaimsError("%s: requirement %r: count() is for a one-limb input"
                                      % (self.name, r))
                self.requires.append(("count", m.group(1)))
                continue
            m = _FORMAT_RE.match(r)
            if m:
                if m.group(1) not in FORMAT_PROPERTIES:
                    raise ClaimsError("%s: requirement %r: the format property %r is not in the "
                                      "vocabulary (half)" % (self.name, r, m.group(1)))
                if m.group(1) in self.format_requires:
                    raise ClaimsError("%s: requirement %r is listed twice" % (self.name, r))
                self.format_requires.append(m.group(1))
                continue
            m = _NORMALIZED_RE.match(r)
            if m and m.group(1) in self.input_names and m.group(1) not in self.masks:
                if self.extended:
                    raise ClaimsError("%s: requirement %r: in the extended domain a 2-limb operand "
                                      "is canonical(), not normalized()" % (self.name, r))
                self.requires.append(("normalized", m.group(1)))
                continue
            m = _ABS_GE_RE.match(r)
            if (m and m.group(1) in self.input_names and m.group(2) in self.input_names
                    and not {m.group(1), m.group(2)} & self.masks):
                if self.extended:
                    raise ClaimsError("%s: requirement %r has no meaning in the extended domain"
                                      % (self.name, r))
                self.requires.append(("abs_ge", m.group(1), m.group(2)))
                continue
            m = _UNARY_REQ_RE.match(r)
            if m and m.group(2) in self.input_names and m.group(2) not in self.masks:
                self.requires.append((m.group(1), m.group(2)))
                continue
            m = _CANONICAL_RE.match(r)
            if m and m.group(1) in self.input_names and m.group(1) not in self.masks:
                if not self.extended:
                    raise ClaimsError("%s: requirement %r belongs to the extended domain"
                                      % (self.name, r))
                if limbs[m.group(1)] < 2:
                    raise ClaimsError("%s: requirement %r: canonical() is for an operand of two "
                                      "limbs (a one-limb operand is any value)" % (self.name, r))
                self.requires.append(("canonical", m.group(1)))
                continue
            m = _BALL_RE.match(r)
            if (m and m.group(1) in self.input_names and m.group(2) in self.input_names
                    and not {m.group(1), m.group(2)} & self.masks):
                c, rr = m.group(1), m.group(2)
                if not self.extended:
                    raise ClaimsError("%s: requirement %r belongs to the extended domain"
                                      % (self.name, r))
                if c == rr or limbs[rr] != 1:
                    raise ClaimsError("%s: requirement %r: a ball is a center and a one-limb "
                                      "radius, two different inputs" % (self.name, r))
                used = {n for b in self.ball_requires for n in b}
                if c in used or rr in used:
                    raise ClaimsError("%s: requirement %r shares an input with another ball"
                                      % (self.name, r))
                self.requires.append(("ball", c, rr))
                self.ball_requires.append((c, rr))
                continue
            if IV.read_requirement(self, r, limbs):
                continue
            if UP.read_requirement(self, r, limbs):
                continue
            if BV.read_requirement(self, r, limbs):
                # at_most(NAME, K): conv_radius (bvec.py).
                continue
            raise ClaimsError("%s: requirement %r is outside the vocabulary "
                              "(normalized(NAME), abs_ge(NAME, NAME), power_of_two(NAME), "
                              "nonneg(NAME), count(NAME), format(half), at_most(NAME, K); in the "
                              "extended domain canonical(NAME), ball(CENTER, RADIUS))"
                              % (self.name, r))
        IV.finish_requirements(self)
        UP.finish_requirements(self)
        ens = raw.get("ensures")
        if not isinstance(ens, list):
            raise ClaimsError("%s: ensures must be a list" % self.name)
        self.ensures = []
        nerr = 0
        for i, e in enumerate(ens):
            ent = Entry(self, e, i, nerr)
            if ent.kind == "error":
                nerr += 1
            self.ensures.append(ent)
        if self.extended:
            # An operand of several limbs is canonical or the center of a ball: nothing else
            # says what its limbs may be once they need not be finite.  The one exception is a
            # kernel whose every entry is finite_or_nan, whose reading covers any limbs (the
            # finish of a fold takes the fold's state, whatever it is).
            covered = {r[1] for r in self.requires if r[0] == "canonical"}
            covered |= {c for c, _ in self.ball_requires}
            # The bounds of an interval() of two limbs are canonical by that requirement.
            covered |= {n for pair in self.interval_requires for n in pair}
            any_limbs = bool(self.ensures) and all(e.kind == "finite_or_nan" for e in self.ensures)
            for n, l in self.inputs:
                if l > 1 and n not in self.masks and n not in covered and not any_limbs:
                    raise ClaimsError("%s: the %d-limb input %s has neither canonical(%s) nor a "
                                      "ball() requirement" % (self.name, l, n, n))
        # The entries that hold under a mask (upper with a value of its own, holds): a kernel has
        # all of its entries so, or none, and only in the finite domain, where they are read
        # (check.py, "conditional").
        conditional = [e for e in self.ensures if e.cond is not None]
        if conditional and (len(conditional) != len(self.ensures) or self.extended):
            raise ClaimsError("%s: entries that hold under a mask (if) are read in a kernel of "
                              "the finite domain whose every entry has one" % self.name)
        self.conditional = bool(conditional)
        # The radius kernels and the accumulator (bvec.py).
        BV.finish_kernel(self)
        # null means that the smallest precision for which the claims hold is not known yet
        # (an unproved kernel): every format is then in scope, which is the strict reading.
        mp = raw.get("min_precision", 2)
        if mp is None:
            mp = 1
        if not isinstance(mp, int) or isinstance(mp, bool):
            raise ClaimsError("%s: min_precision must be an integer" % self.name)
        self.min_precision = mp
        self.status = raw.get("status")
        # The status of the IEEE-model statement.  Read and checked for form, never used for a
        # verdict: the oracle judges the claims whatever the statuses say.
        self.warnings = []
        self.ieee_status = raw.get("ieee_status")
        if self.ieee_status is not None and self.ieee_status not in IEEE_STATUSES:
            raise ClaimsError("%s: ieee_status must be proved or unverified, got %r"
                              % (self.name, self.ieee_status))
        it = raw.get("ieee_theorem")
        if it is not None and not isinstance(it, dict):
            raise ClaimsError("%s: ieee_theorem must be an object" % self.name)
        if self.extended and self.ieee_status is None:
            self.warnings.append("%s: a kernel of the extended domain without ieee_status"
                                 % self.name)
        if self.ieee_status == "proved" and it is None:
            self.warnings.append("%s: ieee_status is proved but there is no ieee_theorem"
                                 % self.name)
        self._instances = self._read_instances(raw.get("instances", {}))
        self._bounds = {}
        # Descriptive fields carry no semantics for the oracle; anything else is reported,
        # so that a field added later with a meaning is noticed rather than ignored.
        self.unknown_fields = sorted(set(raw) - KERNEL_FIELDS)

    def _io(self, lst, what):
        """[(name, limbs)].  A mask ("type": "mask") takes one slot of the line, written 0
        or 1; its name also goes into self.masks."""
        if not isinstance(lst, list) or not lst:
            raise ClaimsError("%s: %s must be a nonempty list" % (self.name, what))
        out = []
        for d in lst:
            if not isinstance(d, dict) or not isinstance(d.get("name"), str):
                raise ClaimsError("%s: bad %s entry %r" % (self.name, what, d))
            ty = d.get("type", "limbs")
            if ty == "mask":
                n = d.get("limbs", 1)
                if n != 1 or isinstance(n, bool):
                    raise ClaimsError("%s: mask %s has limbs %r" % (self.name, d["name"], n))
                self.masks.add(d["name"])
                out.append((d["name"], 1))
                continue
            if ty != "limbs":
                raise ClaimsError("%s: %s entry %s has unknown type %r"
                                  % (self.name, what, d["name"], ty))
            if (not isinstance(d.get("limbs"), int) or isinstance(d.get("limbs"), bool)
                    or d["limbs"] < 1):
                raise ClaimsError("%s: bad %s entry %r" % (self.name, what, d))
            out.append((d["name"], d["limbs"]))
        return out

    def limbs_of(self, name):
        return dict(self.inputs + self.outputs).get(name)

    def input_expression(self, text, where):
        """The syntax tree of an expression over the limb inputs."""
        try:
            tree = X.parse(text)
        except X.ExprError as ex:
            raise ClaimsError("%s: %s: %s" % (self.name, where, ex))
        for n in X.names(tree):
            if n not in self.input_names or n in self.masks:
                raise ClaimsError("%s: %s: %r is not a limb input" % (self.name, where, n))
        return tree

    def resolve_outputs(self, of, where):
        """`of` names one output; a list of names or "s+e" concatenates outputs in that
        order, which is how a pair of one-limb results such as (s, e) is read as one
        2-limb number.  Absent means every output."""
        outs = [n for n, _ in self.outputs]
        if of is None:
            return outs
        if isinstance(of, str):
            names = [x.strip() for x in of.split("+")]
        elif isinstance(of, list) and all(isinstance(x, str) for x in of):
            names = of
        else:
            raise ClaimsError("%s: bad 'of' %r" % (where, of))
        for n in names:
            if n not in outs:
                raise ClaimsError("%s: 'of' names %r, which is not an output" % (where, n))
        return names

    def _read_instances(self, inst):
        """{(p, qmin, qmax): [(rel, abs) per error entry]} from any placement: under the
        kernel as a list with one object per error entry, each mapping formats to {rel, abs}
        (second wave); under the kernel as an object mapping formats to one {rel, abs} or to
        a list in the order of the error entries (first wave); or under each error entry."""
        errs = [e for e in self.ensures if e.kind == "error"]
        out = {}
        if not isinstance(inst, (dict, list)):
            raise ClaimsError("%s: instances must be a list or an object" % self.name)

        def put(fmtname, idx, d):
            try:
                f = parse_format(fmtname)
            except FormatError as ex:
                raise ClaimsError("%s: instances: %s" % (self.name, ex))
            if not isinstance(d, dict) or set(d) - {"rel", "abs"} or not {"rel", "abs"} <= set(d):
                raise ClaimsError("%s: instances[%s] entry must have rel and abs" %
                                  (self.name, fmtname))
            lst = out.setdefault(f.triple, [None] * len(errs))
            if lst[idx] is not None:
                raise ClaimsError("%s: instances for %s given twice" % (self.name, fmtname))
            lst[idx] = (parse_fraction(d["rel"], "%s %s rel" % (self.name, fmtname)),
                        parse_fraction(d["abs"], "%s %s abs" % (self.name, fmtname)))

        if isinstance(inst, list):
            # The second-wave form: one object per error entry, in their order, each mapping
            # a format to its {rel, abs}.
            if len(inst) != len(errs):
                raise ClaimsError("%s: instances has %d items for %d error entries" %
                                  (self.name, len(inst), len(errs)))
            for j, per in enumerate(inst):
                if not isinstance(per, dict):
                    raise ClaimsError("%s: instances[%d] must map formats to {rel, abs}"
                                      % (self.name, j))
                for fmtname, d in per.items():
                    put(fmtname, j, d)
            inst = {}
        for fmtname, v in inst.items():
            if isinstance(v, dict):
                if len(errs) != 1:
                    raise ClaimsError("%s: instances[%s] is one object but the kernel has %d "
                                      "error entries; give a list" % (self.name, fmtname, len(errs)))
                put(fmtname, 0, v)
            elif isinstance(v, list):
                if len(v) != len(errs):
                    raise ClaimsError("%s: instances[%s] has %d items for %d error entries" %
                                      (self.name, fmtname, len(v), len(errs)))
                for j, d in enumerate(v):
                    put(fmtname, j, d)
            else:
                raise ClaimsError("%s: bad instances[%s]" % (self.name, fmtname))
        for e in errs:
            if e.entry_instances is None:
                continue
            if not isinstance(e.entry_instances, dict):
                raise ClaimsError("%s: bad instances in error entry" % self.name)
            for fmtname, d in e.entry_instances.items():
                put(fmtname, e.error_index, d)
        return out

    def bound(self, fmt, entry):
        """(rel, abs, source) of an error entry for a format.  The listed instance is what
        the generator exported and is what the verdict uses; c and t are evaluated only for
        formats that are not listed.  Where both exist they must agree."""
        key = (fmt.triple, entry.index)
        b = self._bounds.get(key)
        if b is not None:
            return b
        u = Fraction(1, 1 << fmt.p)
        eta = Fraction(1, 1 << -fmt.qmin) if fmt.qmin < 0 else Fraction(1 << fmt.qmin)
        listed = self._instances.get(fmt.triple)
        listed = listed[entry.error_index] if listed else None
        try:
            ev = (eval_rational(entry.c, u) * u ** entry.k, entry.t * eta)
            ev_err = None
        except ClaimsError as ex:
            ev, ev_err = None, str(ex)
        if listed is not None:
            if ev is not None and ev != listed:
                raise ClaimsError(
                    "%s, %s, %s: instances give rel=%s abs=%s but c=%s, k=%d, t=%s give rel=%s abs=%s"
                    % (self.name, fmt.name, entry.label, listed[0], listed[1], entry.c, entry.k,
                       entry.t, ev[0], ev[1]))
            b = (listed[0], listed[1], "instances")
        elif ev is not None:
            b = (ev[0], ev[1], "evaluated from c and t (format not in instances)")
        else:
            raise ClaimsError("%s: no instance for %s and c cannot be evaluated: %s"
                              % (self.name, fmt.name, ev_err))
        if b[0] < 0 or b[1] < 0:
            raise ClaimsError("%s, %s: negative bound" % (self.name, fmt.name))
        self._bounds[key] = b
        return b


class Claims:
    def __init__(self, data, path="<claims>"):
        self.path = path
        if not isinstance(data, dict):
            raise ClaimsError("claims must be a JSON object")
        if data.get("schema") != 1:
            raise ClaimsError("unsupported claims schema %r (this oracle reads schema 1)"
                              % data.get("schema"))
        ks = data.get("kernels")
        if not isinstance(ks, list):
            raise ClaimsError("claims have no kernels list")
        # A kernel whose claims cannot be read is set aside with the reason: its lines fail
        # and the run fails, but the other kernels are still judged.
        self.kernels = {}
        self.broken = {}
        for raw in ks:
            name = raw.get("name") if isinstance(raw, dict) else None
            name = name if isinstance(name, str) else "<kernel without a name>"
            if name in self.kernels or name in self.broken:
                self.kernels.pop(name, None)
                self.broken[name] = "%s: listed twice" % name
                continue
            try:
                self.kernels[name] = Kernel(raw)
            except ClaimsError as ex:
                self.broken[name] = str(ex)
        self.check_instances()
        self.link_cores()
        self.link_constants()
        # The constants of the claims of the interval kernels, rel and abs (intervals.py).
        IV.link_constants(self)
        # The folds (architecture.md, "Claims of Milestone 2", "Folds"): a second list, absent
        # when there is none.  A fold whose claims cannot be read is set aside as a kernel is.
        self.folds = {}
        self.kernel_names = {raw.get("name") for raw in ks if isinstance(raw, dict)}
        if "folds" in data:
            from . import folds as FO
            from . import maps as MP
            fl = data["folds"]
            if not isinstance(fl, list):
                raise ClaimsError("claims: folds must be a list")
            # The convolutions name a fold of the list (their coefficients'): they are read after
            # the others, whatever the order of the list.  A map ("map": true) and a convolution
            # ("conv": true) are read by maps.py, every other fold by folds.py.
            convs = [r for r in fl if isinstance(r, dict) and r.get("conv") is True
                     and "map" not in r]
            # The products of two BallVectors name a convolution (their centers'): after them.
            bvconvs = [r for r in fl if isinstance(r, dict) and "bv_conv" in r]
            later = convs + bvconvs
            for raw in [r for r in fl if not any(r is c for c in later)] + later:
                name = raw.get("name") if isinstance(raw, dict) else None
                name = name if isinstance(name, str) else "<fold without a name>"
                if name in self.kernel_names:
                    self.broken[name] = "%s: a fold has the name of a kernel" % name
                    self.kernels.pop(name, None)
                    continue
                if name in self.folds or name in self.broken:
                    self.folds.pop(name, None)
                    self.broken[name] = "%s: listed twice" % name
                    continue
                try:
                    if "bv" in raw or "bv_conv" in raw:
                        # The ball vectors (bvfolds.py).
                        from . import bvfolds as BF
                        self.folds[name] = (BF.BvConv if "bv_conv" in raw else BF.BallVector)(
                            raw, self)
                    elif raw.get("map") is not None and "conv" not in raw:
                        self.folds[name] = MP.Map(raw, self)
                    elif raw.get("conv") is not None and "map" not in raw:
                        self.folds[name] = MP.Conv(raw, self)
                    else:
                        self.folds[name] = FO.Fold(raw, self)
                except ClaimsError as ex:
                    self.broken[name] = str(ex)

    def get(self, name):
        return self.kernels.get(name)

    def get_fold(self, name):
        return self.folds.get(name)

    def unit_tiny(self, name, fmt):
        """(unit, tiny) of kernel name's error entry in a format: c u^k and t eta, as the bound
        of the entry gives them (the listed instance in a named format)."""
        k = self.kernels.get(name)
        if k is None:
            raise ClaimsError("unit(%s), tiny(%s): %s" % (name, name, self.broken.get(
                name, "no kernel %s in the claims" % name)))
        errs = [e for e in k.ensures if e.kind == "error"]
        if len(errs) != 1:
            raise ClaimsError("unit(%s), tiny(%s): %s has %d error entries, not one"
                              % (name, name, name, len(errs)))
        rel, ab, _ = k.bound(fmt, errs[0])
        return rel, ab

    def link_constants(self):
        """unit(K) and tiny(K) in the expressions of a kernel's entries: K must be a kernel of the
        claims, readable, with exactly one error entry.  A kernel whose expressions name another
        is set aside otherwise."""
        for k in list(self.kernels.values()):
            # The generator's strata of a bound kernel are placed by the unit of the kernel its
            # bound is for (gen5.py), so a kernel whose entries name one knows its claims.
            k.claims_ref = self
            for e in k.ensures:
                trees = ([e.cvalue] if e.cvalue is not None else []) + list(getattr(e, "cargs", []))
                try:
                    for t in trees:
                        for _f, kn in CX.calls(t):
                            self.check_unit_kernel(kn, "%s: %s" % (k.name, e.label))
                except ClaimsError as ex:
                    self.mark_broken(k.name, str(ex))
                    break

    def check_unit_kernel(self, kn, where):
        c = self.kernels.get(kn)
        if c is None:
            raise ClaimsError("%s: unit(%s)/tiny(%s): %s" % (where, kn, kn, self.broken.get(
                kn, "%s is not a kernel of the claims" % kn)))
        if sum(1 for x in c.ensures if x.kind == "error") != 1:
            raise ClaimsError("%s: unit(%s)/tiny(%s): %s has no single error entry"
                              % (where, kn, kn, kn))

    def mark_broken(self, name, why):
        self.kernels.pop(name, None)
        self.broken.setdefault(name, why)

    def errors(self):
        return ["%s" % why for _, why in sorted(self.broken.items())]

    def link_cores(self):
        """Resolve the core of every `extends` entry.  A full kernel whose core is missing,
        unreadable or does not fit is set aside like any other unreadable kernel."""
        for k in list(self.kernels.values()):
            for e in k.ensures:
                if e.kind != "extends":
                    continue
                try:
                    e.core = self._core_of(k, e)
                except ClaimsError as ex:
                    self.mark_broken(k.name, str(ex))
                    break

    def _core_of(self, k, e):
        where = "%s: extends: core %s" % (k.name, e.core_name)
        c = self.kernels.get(e.core_name)
        if c is None:
            if e.core_name in self.broken:
                raise ClaimsError("%s cannot be read (%s)" % (where, self.broken[e.core_name]))
            raise ClaimsError("%s is not in the claims" % where)
        if c.extended:
            raise ClaimsError("%s is of the extended domain; a core is a finite kernel" % where)

        def shape(io, masks, names):
            return [(n if names else None, l, n in masks) for n, l in io]

        # The same inputs, names and limbs; outputs of the same shape, whose names may differ
        # (z in the cores' listings, w in the full kernels'): they are matched by position.
        if shape(c.inputs, c.masks, True) != shape(k.inputs, k.masks, True):
            raise ClaimsError("%s has other inputs (%s) than the kernel (%s)" % (
                where, _io_text(c.inputs), _io_text(k.inputs)))
        if shape(c.outputs, c.masks, False) != shape(k.outputs, k.masks, False):
            raise ClaimsError("%s has other outputs (%s) than the kernel (%s)" % (
                where, _io_text(c.outputs), _io_text(k.outputs)))
        # The core's requirements are the kernel's with normalized for canonical.
        want = {("normalized",) + r[1:] if r[0] == "canonical" else r for r in k.requires}
        if set(c.requires) != want:
            raise ClaimsError("%s requires %s, which is not the kernel's requirements with "
                              "normalized() for canonical()" % (
                                  where, ", ".join("%s(%s)" % (r[0], ", ".join(r[1:]))
                                                   for r in c.requires) or "nothing"))
        bad = [x.kind for x in c.ensures if x.kind not in CORE_KINDS]
        if bad:
            raise ClaimsError("%s has ensures of kind %s; a core of extends may have %s only"
                              % (where, bad[0], ", ".join(CORE_KINDS)))
        if c.min_precision != k.min_precision:
            raise ClaimsError("%s has min_precision %s and the kernel %s; a full kernel's is "
                              "that of its core" % (where, c.min_precision, k.min_precision))
        if c.value_tree is None or not _same_polynomial(c, k):
            raise ClaimsError("%s has the value %r, the kernel %r (inputs matched by position)"
                              % (where, c.value_text, k.value_text))
        return c

    def check_instances(self):
        """Evaluate every listed instance against c and t; a kernel whose numbers disagree
        with its own c and t is set aside."""
        from .fmt import Format
        for k in list(self.kernels.values()):
            try:
                for triple in k._instances:
                    f = Format(*triple)
                    for e in k.ensures:
                        if e.kind == "error":
                            k.bound(f, e)
            except ClaimsError as ex:
                self.mark_broken(k.name, str(ex))


def _io_text(io):
    return ", ".join("%s:%d" % (n, l) for n, l in io)


def _same_polynomial(a, b):
    """True when the values of kernels a and b are the same function of their inputs matched by
    position.  Both are polynomials in the inputs, so agreement at random integer points (fixed
    seed) decides it with overwhelming probability, and a reordering such as c*x for x*c is
    accepted."""
    import random
    pos_a = {n: i for i, n in enumerate(a.input_names)}
    pos_b = {n: i for i, n in enumerate(b.input_names)}
    fa = X.make_function(["v"], X.compile_tree(a.value_tree, lambda n: ("v[%d]" % pos_a[n], 0))[0])
    fb = X.make_function(["v"], X.compile_tree(b.value_tree, lambda n: ("v[%d]" % pos_b[n], 0))[0])
    rnd = random.Random(20261119)
    for _ in range(12):
        v = [rnd.randrange(-(1 << 80), 1 << 80) for _ in a.input_names]
        if fa(v) != fb(v):
            return False
    return True


def load_claims(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as ex:
        raise ClaimsError("cannot read claims %s: %s" % (path, ex))
    except json.JSONDecodeError as ex:
        raise ClaimsError("claims %s are not valid JSON: %s" % (path, ex))
    return Claims(data, path)


# The interval kernels (intervals.py): their kinds, and the fields they add to kinds that exist.
# Imported last: intervals.py reads this module's ClaimsError and readers.
from . import intervals as IV  # noqa: E402
Entry.KNOWN.update(IV.KNOWN)
for _kind, _fields in IV.ADDED_FIELDS.items():
    Entry.KNOWN[_kind] = Entry.KNOWN[_kind] | _fields
# The kernels of the ball vectors and of the accumulator (bvec.py): the fields they add.
from . import bvec as BV  # noqa: E402
for _kind, _fields in BV.ADDED_FIELDS.items():
    Entry.KNOWN[_kind] = Entry.KNOWN[_kind] | _fields

# The predicates, comparisons and set operations of a ball of the enclosure interface
# (enclosure.py): the kinds certain, trit, ball_set and ball_splits.
from . import enclosure as EN  # noqa: E402
Entry.KNOWN.update(EN.KNOWN)

# The round-up interval (upward.py): the kind same_set; the fields it adds to the kinds of the
# interval kernels are in intervals.KNOWN.
from . import upward as UP  # noqa: E402
Entry.KNOWN.update(UP.KNOWN)
