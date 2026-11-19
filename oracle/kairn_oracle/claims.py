"""Reading claims files.

The vocabulary is closed: anything the oracle does not understand is an error, never
ignored, because a requirement or a guarantee that is silently dropped makes the oracle
lenient without anyone noticing.
"""

import json
import re
from fractions import Fraction

from .fmt import parse_format, FormatError


class ClaimsError(ValueError):
    pass


_NAME = r"[A-Za-z_][A-Za-z0-9_]*"
_VALUE_RE = re.compile(r"\s*(%s)\s*([-+*])\s*(%s)\s*\Z" % (_NAME, _NAME))
_IDENTITY_RE = re.compile(r"\s*(%s)\s*\Z" % _NAME)
_NORMALIZED_RE = re.compile(r"\s*normalized\(\s*(%s)\s*\)\s*\Z" % _NAME)
_ABS_GE_RE = re.compile(r"\s*abs_ge\(\s*(%s)\s*,\s*(%s)\s*\)\s*\Z" % (_NAME, _NAME))
WHEN_VOCABULARY = ("product_large",)
FORMS = ("R", "A")
KERNEL_FIELDS = {"name", "inputs", "outputs", "value", "requires", "ensures", "min_precision",
                 "status", "theorem", "source", "flops", "instances"}


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


# ---------------------------------------------------------------------------

class Entry:
    """One `ensures` entry."""

    def __init__(self, kernel, raw, index, error_index):
        self.raw = raw
        self.index = index
        if not isinstance(raw, dict) or "kind" not in raw:
            raise ClaimsError("%s: ensures entry %d has no kind" % (kernel.name, index))
        self.kind = raw["kind"]
        where = "%s: ensures entry %d (%s)" % (kernel.name, index, self.kind)
        known = {"normalized": {"kind", "of"},
                 "error": {"kind", "of", "form", "c", "k", "t", "when", "instances"},
                 "leading_rounded": {"kind", "of"}}
        if self.kind not in known:
            raise ClaimsError("%s: unknown kind" % where)
        extra = set(raw) - known[self.kind]
        if extra:
            raise ClaimsError("%s: unknown fields %s" % (where, sorted(extra)))
        self.of = kernel.resolve_outputs(raw.get("of"), where)
        self.error_index = None
        if self.kind == "error":
            self.error_index = error_index
            self.form = raw.get("form")
            if self.form not in FORMS:
                raise ClaimsError("%s: form must be R or A, got %r" % (where, self.form))
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
            self.entry_instances = raw.get("instances")
        self.label = self._label()

    def _label(self):
        of = "+".join(self.of)
        if self.kind == "error":
            s = "error(%s) form %s, c=%s, k=%d, t=%s" % (of, self.form, self.c, self.k, self.t)
            if self.when:
                s += ", when %s" % self.when
            return s
        return "%s(%s)" % (self.kind, of)


class Kernel:
    def __init__(self, raw):
        if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
            raise ClaimsError("kernel entry without a name")
        self.name = raw["name"]
        self.raw = raw
        self.inputs = self._io(raw.get("inputs"), "inputs")
        self.outputs = self._io(raw.get("outputs"), "outputs")
        names = [n for n, _ in self.inputs] + [n for n, _ in self.outputs]
        if len(set(names)) != len(names):
            raise ClaimsError("%s: input and output names must be distinct" % self.name)
        self.input_names = [n for n, _ in self.inputs]
        v = raw.get("value")
        m = _VALUE_RE.match(v) if isinstance(v, str) else None
        mi = _IDENTITY_RE.match(v) if isinstance(v, str) else None
        if m is not None and m.group(1) in self.input_names and m.group(3) in self.input_names:
            self.value = (m.group(2), m.group(1), m.group(3))
        elif mi is not None and mi.group(1) in self.input_names:
            # A bare input name: the outputs approximate that input itself (split).  Not in
            # architecture.md's list; proposed as an addition.
            self.value = ("=", mi.group(1), mi.group(1))
        else:
            raise ClaimsError("%s: value %r is not NAME, NAME+NAME, NAME-NAME or NAME*NAME over "
                              "the inputs" % (self.name, v))
        self.requires = []
        for r in raw.get("requires", []):
            if not isinstance(r, str):
                raise ClaimsError("%s: requirement %r is not a string" % (self.name, r))
            m = _NORMALIZED_RE.match(r)
            if m and m.group(1) in self.input_names:
                self.requires.append(("normalized", m.group(1)))
                continue
            m = _ABS_GE_RE.match(r)
            if m and m.group(1) in self.input_names and m.group(2) in self.input_names:
                self.requires.append(("abs_ge", m.group(1), m.group(2)))
                continue
            raise ClaimsError("%s: requirement %r is outside the vocabulary "
                              "(normalized(NAME), abs_ge(NAME, NAME))" % (self.name, r))
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
        # null means that the smallest precision for which the claims hold is not known yet
        # (an unproved kernel): every format is then in scope, which is the strict reading.
        mp = raw.get("min_precision", 2)
        if mp is None:
            mp = 1
        if not isinstance(mp, int) or isinstance(mp, bool):
            raise ClaimsError("%s: min_precision must be an integer" % self.name)
        self.min_precision = mp
        self.status = raw.get("status")
        self._instances = self._read_instances(raw.get("instances", {}))
        self._bounds = {}
        # Descriptive fields carry no semantics for the oracle; anything else is reported,
        # so that a field added later with a meaning is noticed rather than ignored.
        self.unknown_fields = sorted(set(raw) - KERNEL_FIELDS)

    def _io(self, lst, what):
        if not isinstance(lst, list) or not lst:
            raise ClaimsError("%s: %s must be a nonempty list" % (self.name, what))
        out = []
        for d in lst:
            if (not isinstance(d, dict) or not isinstance(d.get("name"), str)
                    or not isinstance(d.get("limbs"), int) or d["limbs"] < 1):
                raise ClaimsError("%s: bad %s entry %r" % (self.name, what, d))
            out.append((d["name"], d["limbs"]))
        return out

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
        """{(p, qmin, qmax): [(rel, abs) per error entry]} from either placement: under
        the kernel (one object per format when there is one error entry, a list in the
        order of the error entries otherwise) or under each error entry."""
        errs = [e for e in self.ensures if e.kind == "error"]
        out = {}
        if not isinstance(inst, dict):
            raise ClaimsError("%s: instances must be an object" % self.name)

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

    def get(self, name):
        return self.kernels.get(name)

    def mark_broken(self, name, why):
        self.kernels.pop(name, None)
        self.broken.setdefault(name, why)

    def errors(self):
        return ["%s" % why for _, why in sorted(self.broken.items())]

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


def load_claims(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as ex:
        raise ClaimsError("cannot read claims %s: %s" % (path, ex))
    except json.JSONDecodeError as ex:
        raise ClaimsError("claims %s are not valid JSON: %s" % (path, ex))
    return Claims(data, path)
